package main

import (
	"encoding/json"
	"sync"
	"time"
)

// Event represents a single logged event in a session's traffic log.
type Event struct {
	Timestamp   time.Time         `json:"timestamp"`
	Type        string            `json:"type"`                  // ws_connect, ws_frame, ws_disconnect, http_request, http_response, action
	Direction   string            `json:"direction,omitempty"`   // client_to_server, server_to_client
	URL         string            `json:"url,omitempty"`
	QueryParams map[string]string `json:"queryParams,omitempty"`
	Message     json.RawMessage   `json:"message,omitempty"`
	Method      string            `json:"method,omitempty"`
	Path        string            `json:"path,omitempty"`
	Status      int               `json:"status,omitempty"`
	Initiator   string            `json:"initiator,omitempty"` // client, server, proxy
	CloseCode   int               `json:"closeCode,omitempty"`
	RuleMatched *string           `json:"ruleMatched"`
	Headers     map[string]string `json:"headers,omitempty"`
}

// EventLog is an append-only, thread-safe event log.
type EventLog struct {
	events []Event
	mu     sync.Mutex
}

// NewEventLog creates a new empty event log.
func NewEventLog() *EventLog {
	return &EventLog{}
}

// Append adds an event to the log.
func (l *EventLog) Append(event Event) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if event.Timestamp.IsZero() {
		event.Timestamp = time.Now().UTC()
	}
	l.events = append(l.events, event)
}

// Events returns a copy of all events.
func (l *EventLog) Events() []Event {
	l.mu.Lock()
	defer l.mu.Unlock()
	out := make([]Event, len(l.events))
	copy(out, l.events)
	return out
}
