package main

import (
	"encoding/json"
	"fmt"

	"github.com/gorilla/websocket"
)

// ExecuteImperativeAction executes an immediate action on the session's active WS connection(s).
func ExecuteImperativeAction(session *Session, req ActionRequest) error {
	session.EventLog.Append(Event{
		Type:      "action",
		Initiator: "proxy",
		Message:   mustMarshal(req),
	})

	switch req.Type {
	case "disconnect":
		return imperativeDisconnect(session)
	case "close":
		return imperativeClose(session, req.CloseCode)
	case "inject_to_client":
		return imperativeInjectToClient(session, req.Message, false)
	case "inject_to_client_and_close":
		return imperativeInjectToClient(session, req.Message, true)
	default:
		return fmt.Errorf("unknown action type: %s", req.Type)
	}
}

func imperativeDisconnect(session *Session) error {
	wc := session.GetActiveWsConn()
	if wc == nil {
		return fmt.Errorf("no active WebSocket connection")
	}

	session.EventLog.Append(Event{
		Type:      "ws_disconnect",
		Initiator: "proxy",
	})

	// Abrupt close — close the underlying TCP connection
	if conn, ok := wc.ClientConn.(*websocket.Conn); ok {
		conn.UnderlyingConn().Close()
	}
	if conn, ok := wc.ServerConn.(*websocket.Conn); ok {
		conn.UnderlyingConn().Close()
	}

	wc.MarkClosed()
	return nil
}

func imperativeClose(session *Session, closeCode int) error {
	wc := session.GetActiveWsConn()
	if wc == nil {
		return fmt.Errorf("no active WebSocket connection")
	}

	if closeCode <= 0 {
		closeCode = websocket.CloseNormalClosure
	}

	session.EventLog.Append(Event{
		Type:      "ws_disconnect",
		Initiator: "proxy",
		CloseCode: closeCode,
	})

	if conn, ok := wc.ClientConn.(*websocket.Conn); ok {
		msg := websocket.FormatCloseMessage(closeCode, "")
		conn.WriteMessage(websocket.CloseMessage, msg)
		conn.UnderlyingConn().Close()
	}
	if conn, ok := wc.ServerConn.(*websocket.Conn); ok {
		conn.UnderlyingConn().Close()
	}

	wc.MarkClosed()
	return nil
}

func imperativeInjectToClient(session *Session, message json.RawMessage, andClose bool) error {
	wc := session.GetActiveWsConn()
	if wc == nil {
		return fmt.Errorf("no active WebSocket connection")
	}

	if conn, ok := wc.ClientConn.(*websocket.Conn); ok {
		if err := conn.WriteMessage(websocket.TextMessage, message); err != nil {
			return fmt.Errorf("failed to inject message: %w", err)
		}

		session.EventLog.Append(Event{
			Type:      "ws_frame",
			Direction: "server_to_client",
			Message:   message,
			Initiator: "proxy",
		})
	}

	if andClose {
		if conn, ok := wc.ClientConn.(*websocket.Conn); ok {
			msg := websocket.FormatCloseMessage(websocket.CloseNormalClosure, "")
			conn.WriteMessage(websocket.CloseMessage, msg)
			conn.UnderlyingConn().Close()
		}
		if conn, ok := wc.ServerConn.(*websocket.Conn); ok {
			conn.UnderlyingConn().Close()
		}
		wc.MarkClosed()

		session.EventLog.Append(Event{
			Type:      "ws_disconnect",
			Initiator: "proxy",
		})
	}

	return nil
}

func mustMarshal(v interface{}) json.RawMessage {
	b, err := json.Marshal(v)
	if err != nil {
		return json.RawMessage(`{}`)
	}
	return b
}
