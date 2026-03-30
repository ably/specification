package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"github.com/vmihailenco/msgpack/v5"
)

// -- Test helpers --

// startControlServer starts the control API server on a random port, returns its URL and cleanup func.
func startControlServer(t *testing.T) (string, *SessionStore, func()) {
	t.Helper()
	store := NewSessionStore()
	server := NewServer(store)
	ts := httptest.NewServer(server)
	return ts.URL, store, ts.Close
}

// freePort returns an available TCP port.
func freePort(t *testing.T) int {
	t.Helper()
	l, err := net.Listen("tcp", ":0")
	if err != nil {
		t.Fatalf("failed to get free port: %v", err)
	}
	port := l.Addr().(*net.TCPAddr).Port
	l.Close()
	return port
}

// createSession creates a session via the control API, returns the response.
func createSession(t *testing.T, controlURL string, req CreateSessionRequest) CreateSessionResponse {
	t.Helper()
	body, _ := json.Marshal(req)
	resp, err := http.Post(controlURL+"/sessions", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatalf("failed to create session: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		b, _ := io.ReadAll(resp.Body)
		t.Fatalf("create session returned %d: %s", resp.StatusCode, string(b))
	}

	var result CreateSessionResponse
	json.NewDecoder(resp.Body).Decode(&result)
	return result
}

// deleteSession deletes a session via the control API.
func deleteSession(t *testing.T, controlURL, sessionID string) map[string]interface{} {
	t.Helper()
	req, _ := http.NewRequest("DELETE", controlURL+"/sessions/"+sessionID, nil)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatalf("failed to delete session: %v", err)
	}
	defer resp.Body.Close()
	var result map[string]interface{}
	json.NewDecoder(resp.Body).Decode(&result)
	return result
}

// getLog fetches the event log for a session.
func getLog(t *testing.T, controlURL, sessionID string) []Event {
	t.Helper()
	resp, err := http.Get(controlURL + "/sessions/" + sessionID + "/log")
	if err != nil {
		t.Fatalf("failed to get log: %v", err)
	}
	defer resp.Body.Close()
	var result struct {
		Events []Event `json:"events"`
	}
	json.NewDecoder(resp.Body).Decode(&result)
	return result.Events
}

// triggerAction sends an imperative action.
func triggerAction(t *testing.T, controlURL, sessionID string, action ActionRequest) {
	t.Helper()
	body, _ := json.Marshal(action)
	resp, err := http.Post(controlURL+"/sessions/"+sessionID+"/actions", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatalf("failed to trigger action: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		t.Fatalf("trigger action returned %d: %s", resp.StatusCode, string(b))
	}
}

// addRules adds rules to a session dynamically.
func addRules(t *testing.T, controlURL, sessionID string, rules []json.RawMessage, position string) {
	t.Helper()
	rulesJSON, _ := json.Marshal(rules)
	reqBody, _ := json.Marshal(map[string]interface{}{
		"rules":    json.RawMessage(rulesJSON),
		"position": position,
	})
	resp, err := http.Post(controlURL+"/sessions/"+sessionID+"/rules", "application/json", bytes.NewReader(reqBody))
	if err != nil {
		t.Fatalf("failed to add rules: %v", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		t.Fatalf("add rules returned %d: %s", resp.StatusCode, string(b))
	}
}

// startMockWsServer starts a simple WS server that sends a CONNECTED message then echoes frames.
func startMockWsServer(t *testing.T) (string, func()) {
	t.Helper()
	upgrader := websocket.Upgrader{CheckOrigin: func(r *http.Request) bool { return true }}

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			return
		}
		defer conn.Close()

		// Send CONNECTED
		connected := map[string]interface{}{
			"action":       ActionConnected,
			"connectionId": "mock-conn-1",
			"connectionDetails": map[string]interface{}{
				"connectionKey":    "mock-key-1",
				"maxIdleInterval":  15000,
				"connectionStateTtl": 120000,
			},
		}
		connJSON, _ := json.Marshal(connected)
		conn.WriteMessage(websocket.TextMessage, connJSON)

		// Echo loop
		for {
			msgType, data, err := conn.ReadMessage()
			if err != nil {
				return
			}
			conn.WriteMessage(msgType, data)
		}
	})

	server := httptest.NewServer(handler)

	// Convert http URL to ws host
	host := strings.TrimPrefix(server.URL, "http://")
	return host, server.Close
}

// startMockHttpServer starts a simple HTTP server that returns 200 with a JSON body.
func startMockHttpServer(t *testing.T) (string, func()) {
	t.Helper()
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		json.NewEncoder(w).Encode(map[string]string{"status": "ok", "path": r.URL.Path})
	})
	server := httptest.NewServer(handler)
	host := strings.TrimPrefix(server.URL, "http://")
	return host, server.Close
}

// connectWs connects a WebSocket client to the given host.
func connectWs(t *testing.T, host string, queryParams ...string) *websocket.Conn {
	t.Helper()
	u := fmt.Sprintf("ws://%s/", host)
	if len(queryParams) > 0 {
		u += "?" + strings.Join(queryParams, "&")
	}
	conn, _, err := websocket.DefaultDialer.Dial(u, nil)
	if err != nil {
		t.Fatalf("failed to connect WS to %s: %v", host, err)
	}
	return conn
}

// readWsMessage reads a text message from a WS connection with timeout.
func readWsMessage(t *testing.T, conn *websocket.Conn, timeout time.Duration) map[string]interface{} {
	t.Helper()
	conn.SetReadDeadline(time.Now().Add(timeout))
	_, data, err := conn.ReadMessage()
	if err != nil {
		t.Fatalf("failed to read WS message: %v", err)
	}
	conn.SetReadDeadline(time.Time{})
	var msg map[string]interface{}
	json.Unmarshal(data, &msg)
	return msg
}

// -- Tests --

func TestHealthCheck(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	resp, err := http.Get(controlURL + "/health")
	if err != nil {
		t.Fatalf("health check failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var result map[string]bool
	json.NewDecoder(resp.Body).Decode(&result)
	if !result["ok"] {
		t.Fatal("expected ok: true")
	}
}

func TestSessionLifecycle(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:1234"},
		Port:   port,
	})

	if session.SessionID == "" {
		t.Fatal("expected session ID")
	}
	if session.Proxy.Port != port {
		t.Fatalf("expected port %d, got %d", port, session.Proxy.Port)
	}

	// Get session
	resp, err := http.Get(controlURL + "/sessions/" + session.SessionID)
	if err != nil {
		t.Fatalf("get session failed: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != 200 {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	// Delete session
	result := deleteSession(t, controlURL, session.SessionID)
	if result["events"] == nil {
		t.Fatal("expected events in delete response")
	}

	// Verify port is freed
	l, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		t.Fatalf("port %d should be free after session delete: %v", port, err)
	}
	l.Close()
}

func TestSessionPortConflict(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)

	// Create first session on the port
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:1234"},
		Port:   port,
	})

	// Try to create second session on same port — should fail with 409
	body, _ := json.Marshal(CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:1234"},
		Port:   port,
	})
	resp, err := http.Post(controlURL+"/sessions", "application/json", bytes.NewReader(body))
	if err != nil {
		t.Fatalf("failed to make request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusConflict {
		t.Fatalf("expected 409, got %d", resp.StatusCode)
	}

	deleteSession(t, controlURL, session.SessionID)
}

func TestWsPassthrough(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	// Connect through proxy
	conn := connectWs(t, fmt.Sprintf("localhost:%d", port), "key=test.key:secret")
	defer conn.Close()

	// Should receive CONNECTED from mock upstream
	msg := readWsMessage(t, conn, 2*time.Second)
	action, _ := msg["action"].(float64)
	if int(action) != ActionConnected {
		t.Fatalf("expected CONNECTED (4), got %v", msg["action"])
	}

	// Send a frame — should be echoed back
	testMsg := map[string]interface{}{"action": float64(ActionMessage), "channel": "test"}
	testJSON, _ := json.Marshal(testMsg)
	conn.WriteMessage(websocket.TextMessage, testJSON)

	echo := readWsMessage(t, conn, 2*time.Second)
	echoAction, _ := echo["action"].(float64)
	if int(echoAction) != ActionMessage {
		t.Fatalf("expected echo of MESSAGE, got %v", echo["action"])
	}

	// Check event log
	events := getLog(t, controlURL, session.SessionID)
	hasConnect := false
	frameCount := 0
	for _, e := range events {
		if e.Type == "ws_connect" {
			hasConnect = true
		}
		if e.Type == "ws_frame" {
			frameCount++
		}
	}
	if !hasConnect {
		t.Fatal("expected ws_connect event in log")
	}
	if frameCount < 2 {
		t.Fatalf("expected at least 2 ws_frame events, got %d", frameCount)
	}
}

func TestHttpPassthrough(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockHttpServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RestHost: upstreamHost, Insecure: true},
		Port:   port,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	// Make HTTP request through proxy
	resp, err := http.Get(fmt.Sprintf("http://localhost:%d/channels/test/messages", port))
	if err != nil {
		t.Fatalf("HTTP request failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		t.Fatalf("expected 200, got %d", resp.StatusCode)
	}

	var body map[string]string
	json.NewDecoder(resp.Body).Decode(&body)
	if body["path"] != "/channels/test/messages" {
		t.Fatalf("expected path /channels/test/messages, got %s", body["path"])
	}

	// Check event log
	events := getLog(t, controlURL, session.SessionID)
	hasRequest := false
	hasResponse := false
	for _, e := range events {
		if e.Type == "http_request" {
			hasRequest = true
		}
		if e.Type == "http_response" {
			hasResponse = true
		}
	}
	if !hasRequest {
		t.Fatal("expected http_request event in log")
	}
	if !hasResponse {
		t.Fatal("expected http_response event in log")
	}
}

func TestWsConnectionRefusal(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "ws_connect"},
		Action: ActionConfig{Type: "refuse_connection"},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	// First connection should be refused
	u := fmt.Sprintf("ws://localhost:%d/", port)
	_, resp, err := websocket.DefaultDialer.Dial(u, nil)
	if err == nil {
		t.Fatal("expected connection to be refused")
	}
	if resp != nil && resp.StatusCode != http.StatusBadGateway {
		t.Fatalf("expected 502, got %d", resp.StatusCode)
	}

	// Second connection should succeed (rule was one-shot)
	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()
	msg := readWsMessage(t, conn, 2*time.Second)
	action, _ := msg["action"].(float64)
	if int(action) != ActionConnected {
		t.Fatalf("expected CONNECTED on second attempt, got %v", msg["action"])
	}
}

func TestWsFrameSuppression(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "ws_frame_to_server", Action: "MESSAGE"},
		Action: ActionConfig{Type: "suppress"},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()

	// Read CONNECTED
	readWsMessage(t, conn, 2*time.Second)

	// Send MESSAGE — should be suppressed (not echoed)
	msg1 := map[string]interface{}{"action": float64(ActionMessage), "channel": "test"}
	msg1JSON, _ := json.Marshal(msg1)
	conn.WriteMessage(websocket.TextMessage, msg1JSON)

	// Send another MESSAGE — should pass through (rule was one-shot)
	msg2 := map[string]interface{}{"action": float64(ActionMessage), "channel": "test2"}
	msg2JSON, _ := json.Marshal(msg2)
	conn.WriteMessage(websocket.TextMessage, msg2JSON)

	// Should get echo of second message only
	echo := readWsMessage(t, conn, 2*time.Second)
	echoChannel, _ := echo["channel"].(string)
	if echoChannel != "test2" {
		t.Fatalf("expected echo of test2, got channel %s", echoChannel)
	}
}

func TestWsInjectAndClose(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	injectedMsg, _ := json.Marshal(map[string]interface{}{
		"action": ActionDisconnected,
		"error":  map[string]interface{}{"code": 40142, "statusCode": 401, "message": "Token expired"},
	})
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "ws_frame_to_client", Action: "CONNECTED"},
		Action: ActionConfig{Type: "inject_to_client_and_close", Message: injectedMsg},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()

	// Should receive the injected DISCONNECTED message
	msg := readWsMessage(t, conn, 2*time.Second)
	action, _ := msg["action"].(float64)
	if int(action) != ActionDisconnected {
		t.Fatalf("expected DISCONNECTED (6), got %v", msg["action"])
	}

	// Connection should be closed
	conn.SetReadDeadline(time.Now().Add(1 * time.Second))
	_, _, err := conn.ReadMessage()
	if err == nil {
		t.Fatal("expected connection to be closed after inject_to_client_and_close")
	}
}

func TestWsImperativeDisconnect(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()

	// Read CONNECTED
	readWsMessage(t, conn, 2*time.Second)

	// Trigger disconnect via control API
	triggerAction(t, controlURL, session.SessionID, ActionRequest{Type: "disconnect"})

	// Connection should be closed
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, _, err := conn.ReadMessage()
	if err == nil {
		t.Fatal("expected connection to be closed after imperative disconnect")
	}
}

func TestHttpRespond(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockHttpServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "http_request", PathContains: "/channels/"},
		Action: ActionConfig{Type: "http_respond", Status: 401, Body: json.RawMessage(`{"error":{"code":40142,"message":"Token expired"}}`)},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RestHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	// First request to /channels/ should get fake 401
	resp, err := http.Get(fmt.Sprintf("http://localhost:%d/channels/test/messages", port))
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	resp.Body.Close()
	if resp.StatusCode != 401 {
		t.Fatalf("expected 401, got %d", resp.StatusCode)
	}

	// Second request should pass through (rule was one-shot)
	resp2, err := http.Get(fmt.Sprintf("http://localhost:%d/channels/test/messages", port))
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	resp2.Body.Close()
	if resp2.StatusCode != 200 {
		t.Fatalf("expected 200 on second request, got %d", resp2.StatusCode)
	}
}

func TestWsTemporalTrigger(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "delay_after_ws_connect", DelayMs: 200},
		Action: ActionConfig{Type: "disconnect"},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()

	// Read CONNECTED
	readWsMessage(t, conn, 2*time.Second)

	// Wait for temporal trigger to fire (200ms + margin)
	conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	_, _, err := conn.ReadMessage()
	if err == nil {
		t.Fatal("expected connection to be closed by temporal trigger")
	}

	// Verify disconnect logged
	time.Sleep(100 * time.Millisecond)
	events := getLog(t, controlURL, session.SessionID)
	hasDisconnect := false
	for _, e := range events {
		if e.Type == "ws_disconnect" && e.Initiator == "proxy" {
			hasDisconnect = true
		}
	}
	if !hasDisconnect {
		t.Fatal("expected ws_disconnect event from proxy in log")
	}
}

func TestWsSuppressOnwards(t *testing.T) {
	upstreamHost, upstreamCleanup := startMockWsServer(t)
	defer upstreamCleanup()

	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	rulesJSON, _ := json.Marshal([]Rule{{
		Match:  MatchConfig{Type: "delay_after_ws_connect", DelayMs: 200},
		Action: ActionConfig{Type: "suppress_onwards"},
		Times:  1,
	}})
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: upstreamHost, Insecure: true},
		Port:   port,
		Rules:  rulesJSON,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	conn := connectWs(t, fmt.Sprintf("localhost:%d", port))
	defer conn.Close()

	// Read CONNECTED (arrives before suppress_onwards fires)
	readWsMessage(t, conn, 2*time.Second)

	// Wait for suppress_onwards to take effect
	time.Sleep(400 * time.Millisecond)

	// Send a MESSAGE — the echo from server should be suppressed
	testMsg := map[string]interface{}{"action": float64(ActionMessage), "channel": "test"}
	testJSON, _ := json.Marshal(testMsg)
	conn.WriteMessage(websocket.TextMessage, testJSON)

	// Should NOT receive a response (server echoes but proxy suppresses)
	conn.SetReadDeadline(time.Now().Add(500 * time.Millisecond))
	_, _, err := conn.ReadMessage()
	if err == nil {
		t.Fatal("expected no message after suppress_onwards")
	}
}

// Tests that exercise the rule matching logic without needing a real upstream.

func TestRuleMatching(t *testing.T) {
	rule := &Rule{
		Match: MatchConfig{
			Type:   "ws_frame_to_server",
			Action: "ATTACH",
		},
		Action: ActionConfig{Type: "suppress"},
	}

	// Should match
	event := MatchEvent{Type: "ws_frame_to_server", Action: ActionAttach}
	if !rule.Matches(event) {
		t.Fatal("expected rule to match ATTACH frame")
	}

	// Should not match different action
	event2 := MatchEvent{Type: "ws_frame_to_server", Action: ActionDetach}
	if rule.Matches(event2) {
		t.Fatal("expected rule to NOT match DETACH frame")
	}

	// Should not match different type
	event3 := MatchEvent{Type: "ws_frame_to_client", Action: ActionAttach}
	if rule.Matches(event3) {
		t.Fatal("expected rule to NOT match client-direction frame")
	}
}

func TestRuleMatchingWithChannel(t *testing.T) {
	rule := &Rule{
		Match: MatchConfig{
			Type:    "ws_frame_to_server",
			Action:  "ATTACH",
			Channel: "my-channel",
		},
		Action: ActionConfig{Type: "suppress"},
	}

	event := MatchEvent{Type: "ws_frame_to_server", Action: ActionAttach, Channel: "my-channel"}
	if !rule.Matches(event) {
		t.Fatal("expected rule to match")
	}

	event2 := MatchEvent{Type: "ws_frame_to_server", Action: ActionAttach, Channel: "other-channel"}
	if rule.Matches(event2) {
		t.Fatal("expected rule to NOT match different channel")
	}
}

func TestRuleMatchingWsConnect(t *testing.T) {
	rule := &Rule{
		Match: MatchConfig{
			Type:          "ws_connect",
			QueryContains: map[string]string{"resume": "*"},
		},
		Action: ActionConfig{Type: "refuse_connection"},
	}

	// Should match when resume is present
	event := MatchEvent{Type: "ws_connect", Action: -1, QueryParams: map[string]string{"resume": "key-1", "key": "abc"}}
	if !rule.Matches(event) {
		t.Fatal("expected rule to match when resume param present")
	}

	// Should not match when resume is absent
	event2 := MatchEvent{Type: "ws_connect", Action: -1, QueryParams: map[string]string{"key": "abc"}}
	if rule.Matches(event2) {
		t.Fatal("expected rule to NOT match when resume param absent")
	}
}

func TestRuleMatchingHttpRequest(t *testing.T) {
	rule := &Rule{
		Match: MatchConfig{
			Type:         "http_request",
			Method:       "POST",
			PathContains: "/channels/",
		},
		Action: ActionConfig{Type: "http_respond", Status: 401},
	}

	event := MatchEvent{Type: "http_request", Action: -1, Method: "POST", Path: "/channels/test/messages"}
	if !rule.Matches(event) {
		t.Fatal("expected rule to match")
	}

	event2 := MatchEvent{Type: "http_request", Action: -1, Method: "GET", Path: "/channels/test/messages"}
	if rule.Matches(event2) {
		t.Fatal("expected rule to NOT match GET")
	}

	event3 := MatchEvent{Type: "http_request", Action: -1, Method: "POST", Path: "/time"}
	if rule.Matches(event3) {
		t.Fatal("expected rule to NOT match /time")
	}
}

func TestSessionFindMatchingRuleWithCount(t *testing.T) {
	session := &Session{
		Rules: []*Rule{
			{
				Match:  MatchConfig{Type: "ws_connect", Count: 2},
				Action: ActionConfig{Type: "refuse_connection"},
			},
		},
		EventLog: NewEventLog(),
	}

	event := MatchEvent{Type: "ws_connect", Action: -1}

	// First attempt — count=1, rule wants count=2, should not fire
	rule1, _ := session.FindMatchingRule(event)
	if rule1 != nil {
		t.Fatal("expected no match on first ws_connect")
	}

	// Second attempt — count=2, should fire
	rule2, _ := session.FindMatchingRule(event)
	if rule2 == nil {
		t.Fatal("expected match on second ws_connect")
	}
}

func TestRuleTimesLimit(t *testing.T) {
	session := &Session{
		Rules: []*Rule{
			{
				Match:  MatchConfig{Type: "ws_frame_to_server", Action: "ATTACH"},
				Action: ActionConfig{Type: "suppress"},
				Times:  1,
			},
		},
		EventLog: NewEventLog(),
	}

	event := MatchEvent{Type: "ws_frame_to_server", Action: ActionAttach}

	// First match — should fire
	rule, _ := session.FindMatchingRule(event)
	if rule == nil {
		t.Fatal("expected match")
	}
	session.FireRule(rule)

	// Rule should be removed (times=1, fired once)
	if len(session.Rules) != 0 {
		t.Fatalf("expected 0 rules, got %d", len(session.Rules))
	}

	// Second match — no rule
	rule2, _ := session.FindMatchingRule(event)
	if rule2 != nil {
		t.Fatal("expected no match after rule exhausted")
	}
}

func TestProtocolParseJSON(t *testing.T) {
	msg := `{"action":10,"channel":"test-channel"}`
	pm := ParseProtocolMessage([]byte(msg), websocket.TextMessage)
	if pm.Action != ActionAttach {
		t.Fatalf("expected action %d, got %d", ActionAttach, pm.Action)
	}
	if pm.Channel != "test-channel" {
		t.Fatalf("expected channel test-channel, got %s", pm.Channel)
	}
}

func TestProtocolParseJSONWithError(t *testing.T) {
	msg := `{"action":9,"error":{"code":40142,"statusCode":401,"message":"Token expired"}}`
	pm := ParseProtocolMessage([]byte(msg), websocket.TextMessage)
	if pm.Action != ActionError {
		t.Fatalf("expected action %d, got %d", ActionError, pm.Action)
	}
	if pm.Error == nil {
		t.Fatal("expected error to be parsed")
	}
	if pm.Error.Code != 40142 {
		t.Fatalf("expected error code 40142, got %d", pm.Error.Code)
	}
}

func TestProtocolParseMsgpack(t *testing.T) {
	// Build a msgpack map: {"action": 10, "channel": "test"}
	// Using raw msgpack encoding
	raw := map[string]interface{}{
		"action":  10,
		"channel": "test",
	}
	data := mustMarshalMsgpack(t, raw)
	pm := ParseProtocolMessage(data, websocket.BinaryMessage)
	if pm.Action != ActionAttach {
		t.Fatalf("expected action %d, got %d", ActionAttach, pm.Action)
	}
	if pm.Channel != "test" {
		t.Fatalf("expected channel test, got %s", pm.Channel)
	}
}

func TestActionFromString(t *testing.T) {
	tests := []struct {
		input string
		want  int
	}{
		{"ATTACH", ActionAttach},
		{"attach", ActionAttach},
		{"CONNECTED", ActionConnected},
		{"10", ActionAttach},
		{"4", ActionConnected},
		{"unknown", -1},
	}
	for _, tt := range tests {
		got := ActionFromString(tt.input)
		if got != tt.want {
			t.Errorf("ActionFromString(%q) = %d, want %d", tt.input, got, tt.want)
		}
	}
}

func TestEventLog(t *testing.T) {
	log := NewEventLog()
	log.Append(Event{Type: "ws_connect"})
	log.Append(Event{Type: "ws_frame", Direction: "client_to_server"})

	events := log.Events()
	if len(events) != 2 {
		t.Fatalf("expected 2 events, got %d", len(events))
	}
	if events[0].Type != "ws_connect" {
		t.Fatalf("expected ws_connect, got %s", events[0].Type)
	}
	if events[1].Direction != "client_to_server" {
		t.Fatalf("expected client_to_server, got %s", events[1].Direction)
	}
}

func TestEventLogConcurrency(t *testing.T) {
	el := NewEventLog()
	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			el.Append(Event{Type: fmt.Sprintf("event-%d", i)})
		}(i)
	}
	wg.Wait()

	events := el.Events()
	if len(events) != 100 {
		t.Fatalf("expected 100 events, got %d", len(events))
	}
}

func TestSessionTimeout(t *testing.T) {
	controlURL, store, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target:    TargetConfig{RealtimeHost: "localhost:1234"},
		Port:      port,
		TimeoutMs: 200, // 200ms timeout
	})

	// Session should exist
	_, ok := store.Get(session.SessionID)
	if !ok {
		t.Fatal("expected session to exist")
	}

	// Wait for timeout
	time.Sleep(500 * time.Millisecond)

	// Session should be cleaned up
	_, ok = store.Get(session.SessionID)
	if ok {
		t.Fatal("expected session to be cleaned up after timeout")
	}

	// Port should be free
	l, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		t.Fatalf("port should be free after timeout: %v", err)
	}
	l.Close()
}

func TestAddRulesDynamically(t *testing.T) {
	controlURL, store, cleanup := startControlServer(t)
	defer cleanup()

	port := freePort(t)
	session := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:1234"},
		Port:   port,
	})
	defer deleteSession(t, controlURL, session.SessionID)

	// Add a rule
	ruleJSON, _ := json.Marshal(Rule{
		Match:  MatchConfig{Type: "ws_connect"},
		Action: ActionConfig{Type: "refuse_connection"},
		Times:  1,
	})
	addRules(t, controlURL, session.SessionID, []json.RawMessage{ruleJSON}, "append")

	// Verify rule count
	sess, _ := store.Get(session.SessionID)
	if sess.RuleCount() != 1 {
		t.Fatalf("expected 1 rule, got %d", sess.RuleCount())
	}
}

func TestMultipleRulesOrder(t *testing.T) {
	session := &Session{
		Rules: []*Rule{
			{
				Match:   MatchConfig{Type: "ws_frame_to_server", Action: "ATTACH"},
				Action:  ActionConfig{Type: "suppress"},
				Comment: "first",
			},
			{
				Match:   MatchConfig{Type: "ws_frame_to_server"},
				Action:  ActionConfig{Type: "passthrough"},
				Comment: "second",
			},
		},
		EventLog: NewEventLog(),
	}

	// ATTACH should match the first rule (more specific)
	event := MatchEvent{Type: "ws_frame_to_server", Action: ActionAttach}
	rule, _ := session.FindMatchingRule(event)
	if rule == nil || rule.Comment != "first" {
		t.Fatal("expected first rule to match")
	}

	// MESSAGE should match the second rule (catch-all)
	event2 := MatchEvent{Type: "ws_frame_to_server", Action: ActionMessage}
	rule2, _ := session.FindMatchingRule(event2)
	if rule2 == nil || rule2.Comment != "second" {
		t.Fatal("expected second rule to match")
	}
}

func TestConcurrentSessions(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	port1 := freePort(t)
	port2 := freePort(t)

	session1 := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:1111"},
		Port:   port1,
	})
	defer deleteSession(t, controlURL, session1.SessionID)

	session2 := createSession(t, controlURL, CreateSessionRequest{
		Target: TargetConfig{RealtimeHost: "localhost:2222"},
		Port:   port2,
	})
	defer deleteSession(t, controlURL, session2.SessionID)

	if session1.SessionID == session2.SessionID {
		t.Fatal("expected different session IDs")
	}
	if session1.Proxy.Port == session2.Proxy.Port {
		t.Fatal("expected different ports")
	}
}

func TestSessionNotFound(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	resp, _ := http.Get(controlURL + "/sessions/nonexistent")
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp.StatusCode)
	}
	resp.Body.Close()

	resp2, _ := http.Get(controlURL + "/sessions/nonexistent/log")
	if resp2.StatusCode != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", resp2.StatusCode)
	}
	resp2.Body.Close()
}

func TestCreateSessionValidation(t *testing.T) {
	controlURL, _, cleanup := startControlServer(t)
	defer cleanup()

	// Missing port
	body, _ := json.Marshal(CreateSessionRequest{Target: TargetConfig{RealtimeHost: "localhost:1234"}})
	resp, _ := http.Post(controlURL+"/sessions", "application/json", bytes.NewReader(body))
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing port, got %d", resp.StatusCode)
	}
	resp.Body.Close()

	// Missing target
	body2, _ := json.Marshal(CreateSessionRequest{Port: 9999})
	resp2, _ := http.Post(controlURL+"/sessions", "application/json", bytes.NewReader(body2))
	if resp2.StatusCode != http.StatusBadRequest {
		t.Fatalf("expected 400 for missing target, got %d", resp2.StatusCode)
	}
	resp2.Body.Close()
}

// -- Msgpack test helper --

func mustMarshalMsgpack(t *testing.T, v interface{}) []byte {
	t.Helper()
	data, err := msgpack.Marshal(v)
	if err != nil {
		t.Fatalf("failed to marshal msgpack: %v", err)
	}
	return data
}
