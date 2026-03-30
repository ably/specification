package main

import (
	"encoding/json"
	"strings"
)

// Rule represents a single proxy rule with match condition, action, and optional firing limit.
type Rule struct {
	Match   MatchConfig  `json:"match"`
	Action  ActionConfig `json:"action"`
	Times   int          `json:"times,omitempty"` // 0 = unlimited
	Comment string       `json:"comment,omitempty"`

	matchCount int // how many times the match condition was satisfied (for count matching)
}

// MatchConfig describes when a rule fires.
type MatchConfig struct {
	Type          string            `json:"type"`                    // ws_connect, ws_frame_to_server, ws_frame_to_client, http_request, delay_after_ws_connect
	Count         int               `json:"count,omitempty"`         // only match the Nth occurrence (1-based)
	Action        string            `json:"action,omitempty"`        // protocol message action name or number
	Channel       string            `json:"channel,omitempty"`       // channel name must equal this
	Method        string            `json:"method,omitempty"`        // HTTP method
	PathContains  string            `json:"pathContains,omitempty"`  // request path must contain this
	QueryContains map[string]string `json:"queryContains,omitempty"` // query params that must be present ("*" = any value)
	DelayMs       int               `json:"delayMs,omitempty"`       // for delay_after_ws_connect
}

// ActionConfig describes what happens when a rule fires.
type ActionConfig struct {
	Type      string            `json:"type"` // passthrough, refuse_connection, accept_and_close, disconnect, close, suppress, delay, inject_to_client, inject_to_client_and_close, replace, suppress_onwards, http_respond, http_delay, http_drop, http_replace_response
	CloseCode int               `json:"closeCode,omitempty"`
	DelayMs   int               `json:"delayMs,omitempty"`
	Message   json.RawMessage   `json:"message,omitempty"`
	Status    int               `json:"status,omitempty"`
	Body      json.RawMessage   `json:"body,omitempty"`
	Headers   map[string]string `json:"headers,omitempty"`
}

// MatchEvent is the context passed to rule matching.
type MatchEvent struct {
	Type        string            // ws_connect, ws_frame_to_server, ws_frame_to_client, http_request
	Action      int               // protocol message action (normalized to int), -1 if not applicable
	ActionStr   string            // original action string for logging
	Channel     string            // protocol message channel
	Method      string            // HTTP method
	Path        string            // HTTP request path
	QueryParams map[string]string // WS connection query params
}

// Matches checks whether this rule's match config matches the given event.
// It does NOT check the count — that is handled by FindMatchingRule.
func (r *Rule) Matches(event MatchEvent) bool {
	m := r.Match

	if m.Type != event.Type {
		return false
	}

	// Action filter (for frame matches)
	if m.Action != "" && event.Action >= 0 {
		// Try matching by name or number
		wantAction := ActionFromString(m.Action)
		if wantAction < 0 {
			return false // unknown action name
		}
		if wantAction != event.Action {
			return false
		}
	}

	// Channel filter
	if m.Channel != "" && m.Channel != event.Channel {
		return false
	}

	// HTTP method filter
	if m.Method != "" && !strings.EqualFold(m.Method, event.Method) {
		return false
	}

	// HTTP path filter
	if m.PathContains != "" && !strings.Contains(event.Path, m.PathContains) {
		return false
	}

	// Query param filter (for ws_connect)
	if len(m.QueryContains) > 0 {
		for k, v := range m.QueryContains {
			actual, ok := event.QueryParams[k]
			if !ok {
				return false
			}
			if v != "*" && v != actual {
				return false
			}
		}
	}

	return true
}

// ruleLabel returns a human-readable label for logging which rule matched.
func ruleLabel(rule *Rule, index int) string {
	if rule.Comment != "" {
		return rule.Comment
	}
	return "rule-" + strings.Repeat("0", 1) + string(rune('0'+index))
}
