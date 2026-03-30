package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"net/url"
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

var wsUpgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// HandleWsProxy handles a WebSocket connection from the SDK client,
// proxying it to the upstream Ably realtime host.
func HandleWsProxy(session *Session, w http.ResponseWriter, r *http.Request) {
	// Build query params map for logging and matching
	queryParams := make(map[string]string)
	for k, v := range r.URL.Query() {
		if len(v) > 0 {
			queryParams[k] = v[0]
		}
	}

	// Create WsConnection and register it
	wc := NewWsConnection(0)
	session.AddWsConn(wc)
	defer func() {
		wc.CancelTimers()
		wc.MarkClosed()
		session.RemoveWsConn(wc)
	}()

	// Log ws_connect event
	connectURL := fmt.Sprintf("ws://%s%s", r.Host, r.URL.String())
	session.EventLog.Append(Event{
		Type:        "ws_connect",
		URL:         connectURL,
		QueryParams: queryParams,
	})

	// Check rules for ws_connect match
	matchEvent := MatchEvent{
		Type:        "ws_connect",
		Action:      -1,
		QueryParams: queryParams,
	}

	rule, ruleIdx := session.FindMatchingRule(matchEvent)
	if rule != nil {
		session.FireRule(rule)

		switch rule.Action.Type {
		case "refuse_connection":
			session.EventLog.Append(Event{
				Type:        "ws_disconnect",
				Initiator:   "proxy",
				RuleMatched: LogRuleMatch(rule, ruleIdx),
			})
			http.Error(w, "connection refused by proxy rule", http.StatusBadGateway)
			return

		case "accept_and_close":
			clientConn, err := wsUpgrader.Upgrade(w, r, nil)
			if err != nil {
				log.Printf("session %s: failed to upgrade WS for accept_and_close: %v", session.ID, err)
				return
			}
			closeCode := rule.Action.CloseCode
			if closeCode <= 0 {
				closeCode = websocket.CloseNormalClosure
			}
			msg := websocket.FormatCloseMessage(closeCode, "")
			clientConn.WriteMessage(websocket.CloseMessage, msg)
			clientConn.Close()
			session.EventLog.Append(Event{
				Type:        "ws_disconnect",
				Initiator:   "proxy",
				CloseCode:   closeCode,
				RuleMatched: LogRuleMatch(rule, ruleIdx),
			})
			return
		}
		// For other action types on ws_connect, fall through to normal proxying
	}

	// Build upstream URL
	if session.Target.RealtimeHost == "" {
		http.Error(w, "no realtime host configured", http.StatusBadGateway)
		return
	}

	scheme := "wss"
	if session.Target.Insecure {
		scheme = "ws"
	}
	upstreamURL := url.URL{
		Scheme:   scheme,
		Host:     session.Target.RealtimeHost,
		Path:     r.URL.Path,
		RawQuery: r.URL.RawQuery,
	}

	// Dial upstream
	dialer := websocket.Dialer{}
	if !session.Target.Insecure {
		dialer.TLSClientConfig = &tls.Config{}
	}
	serverConn, _, err := dialer.Dial(upstreamURL.String(), nil)
	if err != nil {
		log.Printf("session %s: failed to dial upstream %s: %v", session.ID, upstreamURL.String(), err)
		http.Error(w, fmt.Sprintf("failed to connect to upstream: %v", err), http.StatusBadGateway)
		return
	}
	defer serverConn.Close()

	// Accept client WebSocket upgrade
	clientConn, err := wsUpgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("session %s: failed to upgrade WS: %v", session.ID, err)
		return
	}
	defer clientConn.Close()

	// Store connections
	wc.ClientConn = clientConn
	wc.ServerConn = serverConn

	// Schedule temporal triggers
	scheduleTemporalTriggers(session, wc)

	// Relay frames between client and server
	var wg sync.WaitGroup
	wg.Add(2)

	// server → client relay
	go func() {
		defer wg.Done()
		relayFrames(session, wc, serverConn, clientConn, "server_to_client", "ws_frame_to_client")
	}()

	// client → server relay
	go func() {
		defer wg.Done()
		relayFrames(session, wc, clientConn, serverConn, "client_to_server", "ws_frame_to_server")
	}()

	wg.Wait()

	// Log disconnect if not already logged
	if !wc.IsClosed() {
		session.EventLog.Append(Event{
			Type:      "ws_disconnect",
			Initiator: "client",
		})
	}
}

// relayFrames reads frames from src and writes to dst, applying rules.
func relayFrames(session *Session, wc *WsConnection, src, dst *websocket.Conn, direction, matchType string) {
	for {
		if wc.IsClosed() {
			return
		}

		msgType, data, err := src.ReadMessage()
		if err != nil {
			if !wc.IsClosed() {
				initiator := "client"
				if direction == "server_to_client" {
					initiator = "server"
				}
				session.EventLog.Append(Event{
					Type:      "ws_disconnect",
					Initiator: initiator,
				})
				wc.MarkClosed()
				// Close the other side
				dst.Close()
			}
			return
		}

		// Check suppress_onwards flag
		session.mu.Lock()
		suppressed := false
		if direction == "server_to_client" && session.suppressServerToClient {
			suppressed = true
		} else if direction == "client_to_server" && session.suppressClientToServer {
			suppressed = true
		}
		session.mu.Unlock()

		if suppressed {
			continue
		}

		// Parse protocol message for rule matching and logging
		pm := ParseProtocolMessage(data, msgType)

		// Log the frame (as JSON for readability, even if binary)
		var logMsg json.RawMessage
		if msgType == websocket.TextMessage {
			logMsg = json.RawMessage(data)
		} else {
			// For binary frames, log the parsed summary
			logMsg = mustMarshal(map[string]interface{}{
				"action":  pm.Action,
				"channel": pm.Channel,
				"_binary": true,
			})
		}

		// Build match event
		matchEvent := MatchEvent{
			Type:    matchType,
			Action:  pm.Action,
			Channel: pm.Channel,
		}

		// Find matching rule
		rule, ruleIdx := session.FindMatchingRule(matchEvent)

		ruleLabel := LogRuleMatch(rule, ruleIdx)

		// Log the frame
		session.EventLog.Append(Event{
			Type:        "ws_frame",
			Direction:   direction,
			Message:     logMsg,
			RuleMatched: ruleLabel,
		})

		if rule == nil {
			// No rule matched — passthrough
			if err := dst.WriteMessage(msgType, data); err != nil {
				wc.MarkClosed()
				return
			}
			continue
		}

		// Execute rule action
		session.FireRule(rule)

		switch rule.Action.Type {
		case "passthrough":
			if err := dst.WriteMessage(msgType, data); err != nil {
				wc.MarkClosed()
				return
			}

		case "suppress":
			// Don't forward

		case "delay":
			time.Sleep(time.Duration(rule.Action.DelayMs) * time.Millisecond)
			if err := dst.WriteMessage(msgType, data); err != nil {
				wc.MarkClosed()
				return
			}

		case "inject_to_client":
			// Send the injected message to client
			if direction == "server_to_client" || direction == "client_to_server" {
				clientConn := wc.ClientConn.(*websocket.Conn)
				clientConn.WriteMessage(websocket.TextMessage, rule.Action.Message)
				session.EventLog.Append(Event{
					Type:      "ws_frame",
					Direction: "server_to_client",
					Message:   rule.Action.Message,
					Initiator: "proxy",
				})
			}
			// Also forward the original
			if err := dst.WriteMessage(msgType, data); err != nil {
				wc.MarkClosed()
				return
			}

		case "inject_to_client_and_close":
			clientConn := wc.ClientConn.(*websocket.Conn)
			clientConn.WriteMessage(websocket.TextMessage, rule.Action.Message)
			session.EventLog.Append(Event{
				Type:      "ws_frame",
				Direction: "server_to_client",
				Message:   rule.Action.Message,
				Initiator: "proxy",
			})
			// Close
			closeCode := rule.Action.CloseCode
			if closeCode <= 0 {
				closeCode = websocket.CloseNormalClosure
			}
			closeMsg := websocket.FormatCloseMessage(closeCode, "")
			clientConn.WriteMessage(websocket.CloseMessage, closeMsg)
			clientConn.UnderlyingConn().Close()
			if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
				serverConn.UnderlyingConn().Close()
			}
			wc.MarkClosed()
			session.EventLog.Append(Event{
				Type:      "ws_disconnect",
				Initiator: "proxy",
				CloseCode: closeCode,
			})
			return

		case "replace":
			// Send replacement message instead of original
			if err := dst.WriteMessage(websocket.TextMessage, rule.Action.Message); err != nil {
				wc.MarkClosed()
				return
			}

		case "disconnect":
			// Abrupt close
			if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
				clientConn.UnderlyingConn().Close()
			}
			if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
				serverConn.UnderlyingConn().Close()
			}
			wc.MarkClosed()
			session.EventLog.Append(Event{
				Type:      "ws_disconnect",
				Initiator: "proxy",
			})
			return

		case "close":
			closeCode := rule.Action.CloseCode
			if closeCode <= 0 {
				closeCode = websocket.CloseNormalClosure
			}
			if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
				closeMsg := websocket.FormatCloseMessage(closeCode, "")
				clientConn.WriteMessage(websocket.CloseMessage, closeMsg)
				clientConn.UnderlyingConn().Close()
			}
			if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
				serverConn.UnderlyingConn().Close()
			}
			wc.MarkClosed()
			session.EventLog.Append(Event{
				Type:      "ws_disconnect",
				Initiator: "proxy",
				CloseCode: closeCode,
			})
			return

		case "suppress_onwards":
			session.mu.Lock()
			if direction == "server_to_client" {
				session.suppressServerToClient = true
			} else {
				session.suppressClientToServer = true
			}
			session.mu.Unlock()
			// Don't forward this frame either

		default:
			// Unknown action — passthrough
			if err := dst.WriteMessage(msgType, data); err != nil {
				wc.MarkClosed()
				return
			}
		}
	}
}

// scheduleTemporalTriggers sets up delay_after_ws_connect timers.
func scheduleTemporalTriggers(session *Session, wc *WsConnection) {
	session.mu.Lock()
	defer session.mu.Unlock()

	for _, rule := range session.Rules {
		if rule.Match.Type != "delay_after_ws_connect" {
			continue
		}

		r := rule // capture for closure
		delayMs := r.Match.DelayMs
		if delayMs <= 0 {
			delayMs = 0
		}

		timer := time.AfterFunc(time.Duration(delayMs)*time.Millisecond, func() {
			if wc.IsClosed() {
				return
			}
			log.Printf("session %s: temporal trigger fired (delay %dms): %s", session.ID, delayMs, r.Action.Type)
			executeTemporalAction(session, wc, r)
			session.FireRule(r)
		})
		wc.AddTimer(timer)
	}
}

// executeTemporalAction executes an action from a temporal trigger.
func executeTemporalAction(session *Session, wc *WsConnection, rule *Rule) {
	ruleLabel := rule.Comment
	if ruleLabel == "" {
		ruleLabel = "temporal-trigger"
	}

	switch rule.Action.Type {
	case "disconnect":
		if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
			clientConn.UnderlyingConn().Close()
		}
		if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
			serverConn.UnderlyingConn().Close()
		}
		wc.MarkClosed()
		session.EventLog.Append(Event{
			Type:        "ws_disconnect",
			Initiator:   "proxy",
			RuleMatched: &ruleLabel,
		})

	case "close":
		closeCode := rule.Action.CloseCode
		if closeCode <= 0 {
			closeCode = websocket.CloseNormalClosure
		}
		if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
			closeMsg := websocket.FormatCloseMessage(closeCode, "")
			clientConn.WriteMessage(websocket.CloseMessage, closeMsg)
			clientConn.UnderlyingConn().Close()
		}
		if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
			serverConn.UnderlyingConn().Close()
		}
		wc.MarkClosed()
		session.EventLog.Append(Event{
			Type:        "ws_disconnect",
			Initiator:   "proxy",
			CloseCode:   closeCode,
			RuleMatched: &ruleLabel,
		})

	case "inject_to_client":
		if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
			clientConn.WriteMessage(websocket.TextMessage, rule.Action.Message)
			session.EventLog.Append(Event{
				Type:        "ws_frame",
				Direction:   "server_to_client",
				Message:     rule.Action.Message,
				Initiator:   "proxy",
				RuleMatched: &ruleLabel,
			})
		}

	case "inject_to_client_and_close":
		if clientConn, ok := wc.ClientConn.(*websocket.Conn); ok {
			clientConn.WriteMessage(websocket.TextMessage, rule.Action.Message)
			session.EventLog.Append(Event{
				Type:        "ws_frame",
				Direction:   "server_to_client",
				Message:     rule.Action.Message,
				Initiator:   "proxy",
				RuleMatched: &ruleLabel,
			})
			closeCode := rule.Action.CloseCode
			if closeCode <= 0 {
				closeCode = websocket.CloseNormalClosure
			}
			closeMsg := websocket.FormatCloseMessage(closeCode, "")
			clientConn.WriteMessage(websocket.CloseMessage, closeMsg)
			clientConn.UnderlyingConn().Close()
		}
		if serverConn, ok := wc.ServerConn.(*websocket.Conn); ok {
			serverConn.UnderlyingConn().Close()
		}
		wc.MarkClosed()
		session.EventLog.Append(Event{
			Type:        "ws_disconnect",
			Initiator:   "proxy",
			RuleMatched: &ruleLabel,
		})

	case "suppress_onwards":
		session.mu.Lock()
		session.suppressServerToClient = true
		session.mu.Unlock()
		session.EventLog.Append(Event{
			Type:        "action",
			Initiator:   "proxy",
			Message:     mustMarshal(map[string]string{"type": "suppress_onwards", "direction": "server_to_client"}),
			RuleMatched: &ruleLabel,
		})
	}
}
