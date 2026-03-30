package main

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"

	"github.com/gorilla/websocket"
	"github.com/vmihailenco/msgpack/v5"
)

// Ably protocol message action constants.
const (
	ActionHeartbeat    = 0
	ActionAck          = 1
	ActionNack         = 2
	ActionConnect      = 3
	ActionConnected    = 4
	ActionDisconnect   = 5
	ActionDisconnected = 6
	ActionClose        = 7
	ActionClosed       = 8
	ActionError        = 9
	ActionAttach       = 10
	ActionAttached     = 11
	ActionDetach       = 12
	ActionDetached     = 13
	ActionPresence     = 14
	ActionMessage      = 15
	ActionSync         = 16
	ActionAuth         = 17
)

var actionNames = map[string]int{
	"HEARTBEAT":    ActionHeartbeat,
	"ACK":          ActionAck,
	"NACK":         ActionNack,
	"CONNECT":      ActionConnect,
	"CONNECTED":    ActionConnected,
	"DISCONNECT":   ActionDisconnect,
	"DISCONNECTED": ActionDisconnected,
	"CLOSE":        ActionClose,
	"CLOSED":       ActionClosed,
	"ERROR":        ActionError,
	"ATTACH":       ActionAttach,
	"ATTACHED":     ActionAttached,
	"DETACH":       ActionDetach,
	"DETACHED":     ActionDetached,
	"PRESENCE":     ActionPresence,
	"MESSAGE":      ActionMessage,
	"SYNC":         ActionSync,
	"AUTH":         ActionAuth,
}

var actionNumbers = map[int]string{}

func init() {
	for name, num := range actionNames {
		actionNumbers[num] = name
	}
}

// ActionFromString converts an action name (e.g. "ATTACH") or numeric string (e.g. "10") to an int.
// Returns -1 if the string is not recognized.
func ActionFromString(s string) int {
	// Try as name first
	if n, ok := actionNames[strings.ToUpper(s)]; ok {
		return n
	}
	// Try as number
	if n, err := strconv.Atoi(s); err == nil {
		return n
	}
	return -1
}

// ActionName returns the name for an action number, or the number as a string.
func ActionName(action int) string {
	if name, ok := actionNumbers[action]; ok {
		return name
	}
	return strconv.Itoa(action)
}

// ProtocolMessage is a minimal representation of an Ably protocol message,
// containing only the fields needed for rule matching.
type ProtocolMessage struct {
	Action  int
	Channel string
	Error   *ErrorInfo
}

// ErrorInfo is a minimal representation of an Ably error.
type ErrorInfo struct {
	Code       int    `json:"code"`
	StatusCode int    `json:"statusCode"`
	Message    string `json:"message"`
}

// ParseProtocolMessage decodes a WebSocket frame into a ProtocolMessage.
// For text frames (JSON) and binary frames (msgpack).
// Returns the parsed message. On failure, returns a message with Action=-1.
func ParseProtocolMessage(data []byte, messageType int) ProtocolMessage {
	if messageType == websocket.TextMessage {
		return parseJSON(data)
	}
	if messageType == websocket.BinaryMessage {
		return parseMsgpack(data)
	}
	return ProtocolMessage{Action: -1}
}

func parseJSON(data []byte) ProtocolMessage {
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		return ProtocolMessage{Action: -1}
	}

	pm := ProtocolMessage{Action: -1}

	if actionRaw, ok := raw["action"]; ok {
		// Action can be int or string
		var actionInt int
		if err := json.Unmarshal(actionRaw, &actionInt); err == nil {
			pm.Action = actionInt
		} else {
			var actionStr string
			if err := json.Unmarshal(actionRaw, &actionStr); err == nil {
				pm.Action = ActionFromString(actionStr)
			}
		}
	}

	if channelRaw, ok := raw["channel"]; ok {
		json.Unmarshal(channelRaw, &pm.Channel)
	}

	if errorRaw, ok := raw["error"]; ok {
		var ei ErrorInfo
		if err := json.Unmarshal(errorRaw, &ei); err == nil {
			pm.Error = &ei
		}
	}

	return pm
}

func parseMsgpack(data []byte) ProtocolMessage {
	// Ably msgpack can be either a map or an array.
	// Try map first (the common wire format).
	var rawMap map[string]interface{}
	if err := msgpack.Unmarshal(data, &rawMap); err == nil {
		return parseMsgpackMap(rawMap)
	}

	// Fall back to array format.
	var rawArray []interface{}
	if err := msgpack.Unmarshal(data, &rawArray); err == nil {
		return parseMsgpackArray(rawArray)
	}

	return ProtocolMessage{Action: -1}
}

func parseMsgpackMap(m map[string]interface{}) ProtocolMessage {
	pm := ProtocolMessage{Action: -1}

	if action, ok := m["action"]; ok {
		pm.Action = toInt(action)
	}
	if channel, ok := m["channel"]; ok {
		if s, ok := channel.(string); ok {
			pm.Channel = s
		}
	}
	if errObj, ok := m["error"]; ok {
		if errMap, ok := errObj.(map[string]interface{}); ok {
			pm.Error = &ErrorInfo{
				Code:       toInt(errMap["code"]),
				StatusCode: toInt(errMap["statusCode"]),
				Message:    fmt.Sprintf("%v", errMap["message"]),
			}
		}
	}

	return pm
}

func parseMsgpackArray(a []interface{}) ProtocolMessage {
	pm := ProtocolMessage{Action: -1}

	if len(a) > 0 {
		pm.Action = toInt(a[0])
	}
	if len(a) > 1 {
		if s, ok := a[1].(string); ok {
			pm.Channel = s
		}
	}

	return pm
}

func toInt(v interface{}) int {
	switch n := v.(type) {
	case int:
		return n
	case int8:
		return int(n)
	case int16:
		return int(n)
	case int32:
		return int(n)
	case int64:
		return int(n)
	case uint:
		return int(n)
	case uint8:
		return int(n)
	case uint16:
		return int(n)
	case uint32:
		return int(n)
	case uint64:
		return int(n)
	case float32:
		return int(n)
	case float64:
		return int(n)
	default:
		return -1
	}
}
