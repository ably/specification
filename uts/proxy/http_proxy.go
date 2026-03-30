package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"time"
)

// HandleHttpProxy handles an HTTP request from the SDK client,
// proxying it to the upstream Ably REST host.
func HandleHttpProxy(session *Session, w http.ResponseWriter, r *http.Request) {
	reqCount := session.IncrementHttpReqCount()
	_ = reqCount

	// Log request headers (subset for readability)
	headers := make(map[string]string)
	for _, key := range []string{"Authorization", "Content-Type", "Accept", "X-Ably-Version", "X-Ably-Lib"} {
		if v := r.Header.Get(key); v != "" {
			headers[key] = v
		}
	}

	// Log http_request event
	session.EventLog.Append(Event{
		Type:      "http_request",
		Direction: "client_to_server",
		Method:    r.Method,
		Path:      r.URL.Path,
		Headers:   headers,
	})

	// Build match event
	matchEvent := MatchEvent{
		Type:   "http_request",
		Action: -1,
		Method: r.Method,
		Path:   r.URL.Path,
	}

	rule, ruleIdx := session.FindMatchingRule(matchEvent)

	if rule != nil {
		session.FireRule(rule)

		switch rule.Action.Type {
		case "http_respond":
			ruleLabel := LogRuleMatch(rule, ruleIdx)
			respondWithRule(w, session, rule, ruleLabel)
			return

		case "http_delay":
			time.Sleep(time.Duration(rule.Action.DelayMs) * time.Millisecond)
			// Fall through to proxy

		case "http_drop":
			ruleLabel := LogRuleMatch(rule, ruleIdx)
			session.EventLog.Append(Event{
				Type:        "http_response",
				Direction:   "server_to_client",
				Status:      0,
				RuleMatched: ruleLabel,
			})
			// Hijack the connection and close it without responding
			hj, ok := w.(http.Hijacker)
			if ok {
				conn, _, err := hj.Hijack()
				if err == nil {
					conn.Close()
				}
			}
			return

		case "http_replace_response":
			// Forward to upstream, discard response, return specified response
			proxyToUpstreamAndDiscard(session, r)
			ruleLabel := LogRuleMatch(rule, ruleIdx)
			respondWithRule(w, session, rule, ruleLabel)
			return

		case "passthrough":
			// Fall through to proxy
		}
	}

	// Proxy to upstream
	if session.Target.RestHost == "" {
		writeError(w, http.StatusBadGateway, "no REST host configured")
		return
	}

	scheme := "https"
	if session.Target.Insecure {
		scheme = "http"
	}
	upstreamURL := &url.URL{
		Scheme: scheme,
		Host:   session.Target.RestHost,
	}

	transport := &http.Transport{
		DialContext: (&net.Dialer{
			Timeout: 10 * time.Second,
		}).DialContext,
	}
	if !session.Target.Insecure {
		transport.TLSClientConfig = &tls.Config{}
	}

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = upstreamURL.Scheme
			req.URL.Host = upstreamURL.Host
			req.Host = upstreamURL.Host
		},
		Transport: transport,
		ModifyResponse: func(resp *http.Response) error {
			ruleLabel := LogRuleMatch(rule, ruleIdx)
			session.EventLog.Append(Event{
				Type:        "http_response",
				Direction:   "server_to_client",
				Status:      resp.StatusCode,
				RuleMatched: ruleLabel,
			})
			return nil
		},
		ErrorHandler: func(w http.ResponseWriter, r *http.Request, err error) {
			log.Printf("session %s: HTTP proxy error: %v", session.ID, err)
			writeError(w, http.StatusBadGateway, fmt.Sprintf("upstream error: %v", err))
		},
	}

	proxy.ServeHTTP(w, r)
}

func respondWithRule(w http.ResponseWriter, session *Session, rule *Rule, ruleLabel *string) {
	status := rule.Action.Status
	if status <= 0 {
		status = 200
	}

	// Set headers
	for k, v := range rule.Action.Headers {
		w.Header().Set(k, v)
	}

	// Default content type
	if w.Header().Get("Content-Type") == "" {
		w.Header().Set("Content-Type", "application/json")
	}

	w.WriteHeader(status)

	if len(rule.Action.Body) > 0 {
		w.Write(rule.Action.Body)
	}

	session.EventLog.Append(Event{
		Type:        "http_response",
		Direction:   "server_to_client",
		Status:      status,
		RuleMatched: ruleLabel,
	})
}

func proxyToUpstreamAndDiscard(session *Session, r *http.Request) {
	if session.Target.RestHost == "" {
		return
	}

	scheme := "https"
	if session.Target.Insecure {
		scheme = "http"
	}
	upstreamURL := fmt.Sprintf("%s://%s%s", scheme, session.Target.RestHost, r.URL.RequestURI())
	req, err := http.NewRequest(r.Method, upstreamURL, r.Body)
	if err != nil {
		return
	}
	req.Header = r.Header.Clone()

	client := &http.Client{Timeout: 10 * time.Second}
	if !session.Target.Insecure {
		client.Transport = &http.Transport{TLSClientConfig: &tls.Config{}}
	}
	resp, err := client.Do(req)
	if err != nil {
		return
	}
	io.ReadAll(resp.Body)
	resp.Body.Close()
}

// WriteJSONResponse writes a JSON response body with the given status and data.
func WriteJSONResponse(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}
