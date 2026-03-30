package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"
)

// Server is the control API server.
type Server struct {
	store *SessionStore
	mux   *http.ServeMux
}

// NewServer creates a new control API server.
func NewServer(store *SessionStore) *Server {
	s := &Server{store: store}
	s.mux = http.NewServeMux()
	s.mux.HandleFunc("GET /health", s.handleHealth)
	s.mux.HandleFunc("POST /sessions", s.handleCreateSession)
	s.mux.HandleFunc("GET /sessions/{id}", s.handleGetSession)
	s.mux.HandleFunc("POST /sessions/{id}/rules", s.handleAddRules)
	s.mux.HandleFunc("POST /sessions/{id}/actions", s.handleAction)
	s.mux.HandleFunc("GET /sessions/{id}/log", s.handleGetLog)
	s.mux.HandleFunc("DELETE /sessions/{id}", s.handleDeleteSession)
	return s
}

// ServeHTTP implements http.Handler.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	s.mux.ServeHTTP(w, r)
}

func (s *Server) handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleCreateSession(w http.ResponseWriter, r *http.Request) {
	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeError(w, http.StatusBadRequest, "failed to read request body")
		return
	}

	var req CreateSessionRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	if req.Port <= 0 {
		writeError(w, http.StatusBadRequest, "port is required and must be positive")
		return
	}

	if req.Target.RealtimeHost == "" && req.Target.RestHost == "" {
		writeError(w, http.StatusBadRequest, "target must have at least one of realtimeHost or restHost")
		return
	}

	timeoutMs := req.TimeoutMs
	if timeoutMs <= 0 {
		timeoutMs = 30000
	}

	// Parse rules
	var rules []*Rule
	if len(req.Rules) > 0 {
		if err := json.Unmarshal(req.Rules, &rules); err != nil {
			writeError(w, http.StatusBadRequest, "invalid rules: "+err.Error())
			return
		}
	}

	session := &Session{
		ID:        GenerateID(),
		Target:    req.Target,
		Port:      req.Port,
		Rules:     rules,
		EventLog:  NewEventLog(),
		timeoutMs: timeoutMs,
	}

	// Attempt to bind the port
	if err := StartSessionListener(session, req.Port); err != nil {
		writeError(w, http.StatusConflict, err.Error())
		return
	}

	// Set up auto-cleanup timer
	session.timeoutTimer = time.AfterFunc(time.Duration(timeoutMs)*time.Millisecond, func() {
		log.Printf("session %s timed out after %dms, cleaning up", session.ID, timeoutMs)
		s.cleanupSession(session.ID)
	})

	s.store.Create(session)

	resp := CreateSessionResponse{
		SessionID: session.ID,
		Proxy: ProxyConfig{
			Host: fmt.Sprintf("localhost:%d", req.Port),
			Port: req.Port,
		},
	}

	log.Printf("created session %s on port %d (timeout %dms, %d rules)",
		session.ID, req.Port, timeoutMs, len(rules))

	writeJSON(w, http.StatusCreated, resp)
}

func (s *Server) handleGetSession(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	session, ok := s.store.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "session not found")
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"sessionId": session.ID,
		"port":      session.Port,
		"target":    session.Target,
		"ruleCount": session.RuleCount(),
	})
}

func (s *Server) handleAddRules(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	session, ok := s.store.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "session not found")
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeError(w, http.StatusBadRequest, "failed to read request body")
		return
	}

	var req AddRulesRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	var rules []*Rule
	if err := json.Unmarshal(req.Rules, &rules); err != nil {
		writeError(w, http.StatusBadRequest, "invalid rules: "+err.Error())
		return
	}

	prepend := strings.EqualFold(req.Position, "prepend")
	session.AddRules(rules, prepend)
	session.ResetTimeout()

	writeJSON(w, http.StatusOK, map[string]int{"ruleCount": session.RuleCount()})
}

func (s *Server) handleAction(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	session, ok := s.store.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "session not found")
		return
	}

	body, err := io.ReadAll(r.Body)
	if err != nil {
		writeError(w, http.StatusBadRequest, "failed to read request body")
		return
	}

	var req ActionRequest
	if err := json.Unmarshal(body, &req); err != nil {
		writeError(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	session.ResetTimeout()

	if err := ExecuteImperativeAction(session, req); err != nil {
		writeError(w, http.StatusConflict, err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]bool{"ok": true})
}

func (s *Server) handleGetLog(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	session, ok := s.store.Get(id)
	if !ok {
		writeError(w, http.StatusNotFound, "session not found")
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"events": session.EventLog.Events(),
	})
}

func (s *Server) handleDeleteSession(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	events := s.cleanupSession(id)
	if events == nil {
		writeError(w, http.StatusNotFound, "session not found")
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"events": events,
	})
}

func (s *Server) cleanupSession(id string) []Event {
	session, ok := s.store.Delete(id)
	if !ok {
		return nil
	}

	log.Printf("cleaning up session %s on port %d", session.ID, session.Port)

	StopSessionListener(session)
	session.Close()

	return session.EventLog.Events()
}

// -- helpers --

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}
