package main

import (
	"encoding/json"
	"fmt"
	"net"
	"net/http"
	"sync"
	"time"
)

// TargetConfig specifies the upstream Ably hosts.
type TargetConfig struct {
	RealtimeHost string `json:"realtimeHost,omitempty"`
	RestHost     string `json:"restHost,omitempty"`
	Insecure     bool   `json:"insecure,omitempty"` // if true, use ws:// and http:// upstream (for testing)
}

// Session represents a single test session with its own port, rules, and state.
type Session struct {
	ID       string       `json:"id"`
	Target   TargetConfig `json:"target"`
	Port     int          `json:"port"`
	Rules    []*Rule      `json:"-"`
	EventLog *EventLog    `json:"-"`

	listener     net.Listener
	Server       *http.Server
	timeoutTimer *time.Timer
	timeoutMs    int

	activeWsConns  []*WsConnection
	wsConnectCount int
	httpReqCount   int

	suppressServerToClient bool
	suppressClientToServer bool

	mu sync.Mutex
}

// WsConnection tracks an active proxied WebSocket connection.
type WsConnection struct {
	ClientConn interface{} // *websocket.Conn — set during ws_proxy
	ServerConn interface{} // *websocket.Conn — set during ws_proxy
	ConnNumber int
	timers     []*time.Timer
	closed     bool
	closeCh    chan struct{} // closed when connection is torn down
	mu         sync.Mutex
}

// NewWsConnection creates a new WsConnection.
func NewWsConnection(connNumber int) *WsConnection {
	return &WsConnection{
		ConnNumber: connNumber,
		closeCh:    make(chan struct{}),
	}
}

// MarkClosed marks this connection as closed and signals the closeCh.
func (wc *WsConnection) MarkClosed() {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	if !wc.closed {
		wc.closed = true
		close(wc.closeCh)
	}
}

// IsClosed returns whether this connection has been closed.
func (wc *WsConnection) IsClosed() bool {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	return wc.closed
}

// CancelTimers stops all pending timers for this connection.
func (wc *WsConnection) CancelTimers() {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	for _, t := range wc.timers {
		t.Stop()
	}
	wc.timers = nil
}

// AddTimer adds a timer to this connection's timer list.
func (wc *WsConnection) AddTimer(t *time.Timer) {
	wc.mu.Lock()
	defer wc.mu.Unlock()
	wc.timers = append(wc.timers, t)
}

// FindMatchingRule iterates rules in order and returns the first match.
// It handles count tracking: increments the rule's matchCount when the
// base condition matches, and only returns the rule if count is satisfied.
// Returns the rule and its index, or nil/-1 if no rule matches.
func (s *Session) FindMatchingRule(event MatchEvent) (*Rule, int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	for i, rule := range s.Rules {
		if !rule.Matches(event) {
			continue
		}

		// Base condition matches — increment match count
		rule.matchCount++

		// Check count constraint
		if rule.Match.Count > 0 && rule.matchCount != rule.Match.Count {
			continue
		}

		return rule, i
	}
	return nil, -1
}

// FireRule records that a rule has fired and removes it if times is exhausted.
func (s *Session) FireRule(rule *Rule) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.fireRuleLocked(rule)
}

func (s *Session) fireRuleLocked(rule *Rule) {
	if rule.Times > 0 {
		rule.Times--
		if rule.Times <= 0 {
			s.removeRuleLocked(rule)
		}
	}
}

func (s *Session) removeRuleLocked(rule *Rule) {
	for i, r := range s.Rules {
		if r == rule {
			s.Rules = append(s.Rules[:i], s.Rules[i+1:]...)
			return
		}
	}
}

// AddRules appends or prepends rules to the session.
func (s *Session) AddRules(rules []*Rule, prepend bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if prepend {
		s.Rules = append(rules, s.Rules...)
	} else {
		s.Rules = append(s.Rules, rules...)
	}
}

// RuleCount returns the current number of rules.
func (s *Session) RuleCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return len(s.Rules)
}

// GetActiveWsConn returns the most recently added active WS connection, or nil.
func (s *Session) GetActiveWsConn() *WsConnection {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i := len(s.activeWsConns) - 1; i >= 0; i-- {
		if !s.activeWsConns[i].IsClosed() {
			return s.activeWsConns[i]
		}
	}
	return nil
}

// AddWsConn registers a new WS connection and increments the connect count.
func (s *Session) AddWsConn(wc *WsConnection) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.wsConnectCount++
	wc.ConnNumber = s.wsConnectCount
	s.activeWsConns = append(s.activeWsConns, wc)
}

// RemoveWsConn removes a WS connection from the active list.
func (s *Session) RemoveWsConn(wc *WsConnection) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for i, c := range s.activeWsConns {
		if c == wc {
			s.activeWsConns = append(s.activeWsConns[:i], s.activeWsConns[i+1:]...)
			return
		}
	}
}

// IncrementHttpReqCount increments and returns the HTTP request count.
func (s *Session) IncrementHttpReqCount() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.httpReqCount++
	return s.httpReqCount
}

// ResetTimeout resets the session's auto-cleanup timer.
func (s *Session) ResetTimeout() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.timeoutTimer != nil {
		s.timeoutTimer.Stop()
	}
	if s.timeoutMs > 0 {
		s.timeoutTimer = time.AfterFunc(time.Duration(s.timeoutMs)*time.Millisecond, func() {
			// Auto-cleanup is handled by the session store
		})
	}
}

// Close shuts down the session: closes all WS connections, cancels timers, closes listener.
func (s *Session) Close() {
	s.mu.Lock()
	defer s.mu.Unlock()

	if s.timeoutTimer != nil {
		s.timeoutTimer.Stop()
		s.timeoutTimer = nil
	}

	for _, wc := range s.activeWsConns {
		wc.CancelTimers()
		wc.MarkClosed()
	}
	s.activeWsConns = nil

	if s.listener != nil {
		s.listener.Close()
		s.listener = nil
	}
}

// LogRuleMatch returns a string pointer for logging which rule matched, or nil.
func LogRuleMatch(rule *Rule, index int) *string {
	if rule == nil {
		return nil
	}
	label := fmt.Sprintf("rule-%d", index)
	if rule.Comment != "" {
		label = rule.Comment
	}
	return &label
}

// -- API request/response types --

// CreateSessionRequest is the JSON body for POST /sessions.
type CreateSessionRequest struct {
	Target    TargetConfig    `json:"target"`
	Rules     json.RawMessage `json:"rules,omitempty"`
	TimeoutMs int            `json:"timeoutMs,omitempty"`
	Port      int            `json:"port"`
}

// CreateSessionResponse is the JSON response for POST /sessions.
type CreateSessionResponse struct {
	SessionID string      `json:"sessionId"`
	Proxy     ProxyConfig `json:"proxy"`
}

// ProxyConfig describes how to connect to the session's proxy.
type ProxyConfig struct {
	Host string `json:"host"`
	Port int    `json:"port"`
}

// AddRulesRequest is the JSON body for POST /sessions/{id}/rules.
type AddRulesRequest struct {
	Rules    json.RawMessage `json:"rules"`
	Position string          `json:"position,omitempty"` // "append" (default) or "prepend"
}

// ActionRequest is the JSON body for POST /sessions/{id}/actions.
type ActionRequest struct {
	Type      string          `json:"type"`
	Message   json.RawMessage `json:"message,omitempty"`
	CloseCode int             `json:"closeCode,omitempty"`
}
