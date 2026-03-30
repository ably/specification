# Ably Test Proxy — Go Implementation Plan

## Project structure

```
uts/test/proxy/
├── PROPOSAL.md              # API and design proposal
├── IMPLEMENTATION.md         # This file
├── go.mod                    # module: ably.io/test-proxy
├── go.sum
├── main.go                   # Entry point, flag parsing, server startup
├── server.go                 # Control API HTTP server, routing
├── session.go                # Session lifecycle (create, get, delete, timeout)
├── session_store.go          # Thread-safe session storage
├── rule.go                   # Rule types, matching logic, action types
├── ws_proxy.go               # WebSocket proxy (client↔server frame relay)
├── http_proxy.go             # HTTP reverse proxy with rule interception
├── protocol.go               # Ably protocol message parsing (JSON + msgpack)
├── log.go                    # Event log (per-session traffic capture)
├── action.go                 # Imperative action dispatch
├── listener.go               # Per-session TCP listener management
└── proxy_test.go             # Tests
```

## Design decisions

1. **Port-per-session routing.** The SDK constructs URLs with standard paths (`/channels/...`, `/?key=...`). It cannot prepend a session path prefix. Therefore, each session gets its own TCP listener on a dedicated port. The test process assigns a port from a pool (e.g., 10000–11023, 1024 ports) and passes it in the session creation request. The proxy binds that port and maps all traffic on it to the session. The SDK connects to `ws://localhost:{sessionPort}/...` and `http://localhost:{sessionPort}/...` with normal paths.

2. **No TLS between client and proxy.** The proxy serves plain HTTP/WS to the SDK. Upstream connections to the Ably sandbox use TLS (`wss://`, `https://`). The SDK is configured with `tls: false`.

3. **Msgpack support.** The proxy decodes both JSON (text frames) and msgpack (binary frames) for rule matching. Go has good msgpack libraries. Both formats are decoded into the same `ProtocolMessage` struct for matching, then the original raw bytes are forwarded unchanged (the proxy never re-encodes).

## Dependencies

| Package | Purpose |
|---------|---------|
| `github.com/gorilla/websocket` | WebSocket client and server |
| `github.com/vmihailenco/msgpack/v5` | Msgpack decoding for binary protocol frames |
| `net/http` | Control API server |
| `net/http/httputil` | `ReverseProxy` for HTTP passthrough |
| `encoding/json` | JSON protocol message parsing, API request/response |
| `sync` | Mutex for session store and rule list |
| `net` | TCP listener management for per-session ports |

## Phases

### Phase 1: Skeleton and control API

Build the control API HTTP server, session CRUD, per-session listener management, and health check. No proxying yet.

**Files:** `main.go`, `server.go`, `session.go`, `session_store.go`, `rule.go`, `log.go`, `listener.go`

#### `main.go`

- Parse `--control-port` flag (default 9100)
- Start the control API HTTP server on the control port
- Handle SIGINT/SIGTERM for graceful shutdown (close all session listeners)

#### `server.go`

Control API mux routing:

| Method | Path | Handler |
|--------|------|---------|
| `GET` | `/health` | Return `{"ok": true}` |
| `POST` | `/sessions` | Create session |
| `GET` | `/sessions/{id}` | Get session metadata |
| `POST` | `/sessions/{id}/rules` | Add rules |
| `POST` | `/sessions/{id}/actions` | Trigger imperative action |
| `GET` | `/sessions/{id}/log` | Get event log |
| `DELETE` | `/sessions/{id}` | Teardown session |

Use `net/http.ServeMux` (Go 1.22 has method-aware routing with `{id}` wildcards). No framework needed.

#### `listener.go`

Per-session TCP listener management:

```go
// StartSessionListener binds to the given port, starts an HTTP server
// that routes all WS and HTTP traffic to the session's handlers.
// Returns an error immediately if the port cannot be bound.
func StartSessionListener(session *Session, port int) error

// StopSessionListener closes the listener and shuts down the HTTP server.
func StopSessionListener(session *Session)
```

On session creation:
1. Caller provides `port` in the request body
2. Proxy calls `net.Listen("tcp", fmt.Sprintf(":%d", port))`
3. If listen fails (port in use, permission denied), return HTTP 409 with error message
4. Start `http.Serve` on the listener in a goroutine
5. The per-session HTTP server routes:
   - WebSocket upgrade requests → `ws_proxy` handler
   - All other HTTP requests → `http_proxy` handler

On session deletion:
1. Close the TCP listener (stops accepting new connections)
2. Close all active WS connections
3. Shut down the per-session HTTP server

#### `session.go`

```go
type CreateSessionRequest struct {
    Target    TargetConfig `json:"target"`
    Rules     []Rule       `json:"rules,omitempty"`
    TimeoutMs int          `json:"timeoutMs,omitempty"` // default 30000
    Port      int          `json:"port"`                // required — caller-assigned
}

type CreateSessionResponse struct {
    SessionID string      `json:"sessionId"`
    Proxy     ProxyConfig `json:"proxy"`
}

type ProxyConfig struct {
    Host string `json:"host"` // "localhost:{port}"
    Port int    `json:"port"`
}
```

Session creation flow:
1. Validate request (port is required, target has at least one host)
2. Generate session ID (random 8-char hex)
3. Create `Session` struct with rules, empty event log
4. Attempt to bind the requested port — fail fast with 409 if it can't
5. Start the per-session HTTP server
6. Start timeout timer (`time.AfterFunc`)
7. Store session in `SessionStore`
8. Return session ID and proxy host/port

#### `session_store.go`

Thread-safe `map[string]*Session` with `sync.RWMutex`.

```go
type SessionStore struct {
    sessions map[string]*Session
    mu       sync.RWMutex
}

func (s *SessionStore) Create(session *Session) error
func (s *SessionStore) Get(id string) (*Session, bool)
func (s *SessionStore) Delete(id string) (*Session, bool)
func (s *SessionStore) All() []*Session
```

#### `rule.go`

Rule, MatchConfig, ActionConfig structs with JSON tags. Matching logic is a method on Session:

```go
// FindMatchingRule iterates rules in order and returns the first match.
// Returns nil if no rule matches (passthrough).
func (s *Session) FindMatchingRule(event MatchEvent) *Rule
```

`MatchEvent` is a tagged union representing the thing being matched:

```go
type MatchEvent struct {
    Type        string            // "ws_connect", "ws_frame_to_server", "ws_frame_to_client", "http_request"
    Action      string            // protocol message action name (for frame matches)
    Channel     string            // protocol message channel (for frame matches)
    Method      string            // HTTP method
    Path        string            // HTTP request path
    QueryParams map[string]string // WS connection query params
}
```

#### `log.go`

Append-only event log with mutex.

```go
type EventLog struct {
    events []Event
    mu     sync.Mutex
}

func (l *EventLog) Append(event Event)
func (l *EventLog) Events() []Event // returns a copy
```

### Phase 2: WebSocket proxy — passthrough

Implement transparent WebSocket proxying with no rules applied.

**Files:** `ws_proxy.go`, `protocol.go`

#### WebSocket proxy flow

1. Client connects to `ws://localhost:{sessionPort}/?key=...&heartbeats=true&...`
2. Per-session HTTP server detects WebSocket upgrade, hands off to `WsProxyHandler`
3. Increment `session.WsConnectCount`
4. Log `ws_connect` event with URL and query params
5. Build upstream URL: `wss://{target.realtimeHost}/?key=...&heartbeats=true&...`
   - Copy all query params from client request
   - Scheme is always `wss` (TLS to upstream)
6. Dial upstream WebSocket
7. If dial fails, return error to client (502)
8. Accept the client WebSocket upgrade
9. Start two goroutines:
   - **client→server relay**: `readFromClient()` → log → `writeToServer()`
   - **server→client relay**: `readFromServer()` → log → `writeToClient()`
10. When either side closes or errors, close the other side
11. Log `ws_disconnect` event

#### `protocol.go`

Parse protocol messages for rule matching. Support both JSON and msgpack.

```go
// ParseProtocolMessage attempts to decode a WebSocket frame into a ProtocolMessage.
// For text frames, parses as JSON.
// For binary frames, parses as msgpack.
// Returns the parsed message and nil error on success.
// On parse failure, returns a zero ProtocolMessage and error (frame is still forwarded).
func ParseProtocolMessage(data []byte, messageType int) (ProtocolMessage, error)
```

The `ProtocolMessage` struct:

```go
type ProtocolMessage struct {
    Action    int    // numeric action code (always normalized to int)
    Channel   string
    Error     *ErrorInfo
}
```

Action name↔number mapping (subset needed for matching):

| Name | Number |
|------|--------|
| HEARTBEAT | 0 |
| ACK | 1 |
| NACK | 2 |
| CONNECT | 3 |
| CONNECTED | 4 |
| DISCONNECT | 5 |
| DISCONNECTED | 6 |
| CLOSE | 7 |
| CLOSED | 8 |
| ERROR | 9 |
| ATTACH | 10 |
| ATTACHED | 11 |
| DETACH | 12 |
| DETACHED | 13 |
| PRESENCE | 14 |
| MESSAGE | 15 |
| SYNC | 16 |
| AUTH | 17 |

Rule matching accepts either name (`"ATTACH"`) or number (`10`) in the match config. Internally normalized to int.

**Msgpack decoding:**

Ably msgpack protocol messages are arrays where the first element is the action number. Use `github.com/vmihailenco/msgpack/v5` to decode into a `[]interface{}` and extract the action and channel fields by position. The field positions follow the Ably protocol:

| Index | Field |
|-------|-------|
| 0 | action |
| 1 | channel |
| ... | (other fields — not needed for matching) |

Alternatively, decode as a map if the server uses map encoding. Try map first, fall back to array. Log a warning if neither works but still forward the raw frame.

#### Connection tracking

```go
type WsConnection struct {
    ClientConn  *websocket.Conn
    ServerConn  *websocket.Conn
    ConnNumber  int              // which connection attempt this is (1-based)
    timers      []*time.Timer    // for delay_after_ws_connect cleanup
    mu          sync.Mutex
}
```

Session tracks `activeWsConn *WsConnection` (most recent). When a new WS connection arrives, any previous one should already be closed (the SDK doesn't multiplex WS connections). But track it as a list for safety.

### Phase 3: WebSocket proxy — rule matching

Apply rules to WebSocket frames and connection events.

**Files:** `ws_proxy.go`, `rule.go`

#### Rule evaluation points

**On WS connection attempt** (before dialing upstream):
1. Build `MatchEvent{Type: "ws_connect", QueryParams: ...}`
2. Find matching rule
3. If rule action is `refuse_connection`: return HTTP 502 to client, don't dial upstream
4. If rule action is `accept_and_close`: accept WS upgrade, send close frame, don't dial upstream
5. Otherwise: proceed to dial upstream

**On frame from client** (before forwarding to server):
1. Parse protocol message
2. Build `MatchEvent{Type: "ws_frame_to_server", Action: ..., Channel: ...}`
3. Check `session.suppressClientToServer` flag — if set, drop frame
4. Find matching rule
5. Execute action (suppress, delay, replace, etc.)
6. If no rule matched: forward frame

**On frame from server** (before forwarding to client):
1. Parse protocol message
2. Build `MatchEvent{Type: "ws_frame_to_client", Action: ..., Channel: ...}`
3. Check `session.suppressServerToClient` flag — if set, drop frame
4. Find matching rule
5. Execute action
6. If no rule matched: forward frame

#### Count tracking

The `count` match field means "only match the Nth occurrence of this event type." Counters are per-session:

- `session.wsConnectCount` — incremented on each WS connection attempt
- `session.wsFrameToServerCount` — incremented on each frame from client
- `session.wsFrameToClientCount` — incremented on each frame from server

A rule with `count: 2` matches when the counter equals 2 at evaluation time.

Optionally, counters can be scoped per-action (e.g., "the 2nd ATTACH frame"). Implementation: the rule's `fired` counter tracks how many times the rule's match condition has been checked against a matching event. If `count` is set, the rule only fires when `fired + 1 == count`.

**Simpler approach (recommended):** `count` is a per-rule occurrence counter. The rule tracks how many times its match condition (type + action + channel) has been satisfied. It only fires when that count equals the specified value. This is more intuitive: `{ "type": "ws_connect", "count": 2 }` means "the 2nd connection attempt that would otherwise match this rule."

#### `times` handling

```go
func (s *Session) FireRule(rule *Rule) {
    rule.fired++
    if rule.Times > 0 && rule.fired >= rule.Times {
        s.removeRule(rule)
    }
}
```

### Phase 4: HTTP proxy — passthrough and rules

Implement HTTP reverse proxying for REST API calls.

**Files:** `http_proxy.go`

#### HTTP proxy flow

1. Client sends HTTP request to `http://localhost:{sessionPort}/channels/test/messages`
2. Per-session HTTP server routes non-WebSocket requests to `HttpProxyHandler`
3. Increment `session.HttpReqCount`
4. Log `http_request` event
5. Build `MatchEvent{Type: "http_request", Method: ..., Path: ...}`
6. Find matching rule
7. Execute action:
   - `passthrough` (or no match): forward to upstream
   - `http_respond`: return specified response immediately
   - `http_delay`: sleep then forward
   - `http_drop`: hijack connection and close
   - `http_replace_response`: forward, discard response, return specified response
8. If forwarding: use `httputil.ReverseProxy` with upstream `https://{target.restHost}`
9. Log `http_response` event

#### Forwarding details

- Copy all request headers, body, query params
- Set `Host` header to target host
- Scheme is `https` (TLS to upstream)
- Response headers and body are copied back to client
- Content-Type, status code, etc. are preserved

#### HTTP count tracking

`session.httpReqCount` increments on each request. Per-rule `count` matching works the same as for WS: per-rule occurrence counter.

### Phase 5: Imperative actions

Implement `POST /sessions/{id}/actions`.

**Files:** `action.go`

```go
type ActionRequest struct {
    Type    string          `json:"type"`
    Message json.RawMessage `json:"message,omitempty"`
    CloseCode int           `json:"closeCode,omitempty"`
}
```

Handler:
1. Parse request body
2. Find session
3. Find active WS connection(s)
4. Execute action on the connection:
   - `disconnect`: `conn.ClientConn.UnderlyingConn().Close()` (raw TCP close)
   - `close`: `conn.ClientConn.WriteMessage(websocket.CloseMessage, ...)`
   - `inject_to_client`: `conn.ClientConn.WriteMessage(websocket.TextMessage, message)`
   - `inject_to_client_and_close`: write message then close
5. Log the action as an event
6. Return 200 OK (or 404/409 on errors)

### Phase 6: Temporal triggers

Implement `delay_after_ws_connect` match type.

**Files:** `ws_proxy.go`

After upstream WS connection is established:

1. Lock session mutex
2. Iterate rules looking for `delay_after_ws_connect` type
3. For each matching rule, schedule `time.AfterFunc`:
   ```go
   timer := time.AfterFunc(time.Duration(rule.Match.DelayMs)*time.Millisecond, func() {
       executeAction(session, wsConn, rule.Action)
       session.FireRule(rule)
   })
   wsConn.timers = append(wsConn.timers, timer)
   ```
4. On WS connection close, cancel all pending timers:
   ```go
   for _, t := range wsConn.timers {
       t.Stop()
   }
   ```
5. On session delete, cancel all timers on all connections

### Phase 7: Tests

**Files:** `proxy_test.go`

Test infrastructure: each test starts a local mock upstream server (HTTP + WS echo/scripted), creates the proxy, creates a session pointing at the mock upstream, and connects a client through the proxy.

```go
// Helper: start a mock upstream WS server that sends CONNECTED then echoes frames
func startMockUpstream(t *testing.T) (wsURL string, httpURL string, cleanup func())

// Helper: start the proxy control API
func startProxy(t *testing.T) (controlURL string, cleanup func())

// Helper: create a session and return proxy host:port
func createSession(t *testing.T, controlURL string, req CreateSessionRequest) CreateSessionResponse
```

#### Test cases

**Control API:**
1. Health check returns 200
2. Create session succeeds, returns valid port
3. Create session with port already in use returns 409
4. Get session returns metadata
5. Delete session returns event log, frees port
6. Session auto-deleted after timeout
7. Add rules dynamically

**WebSocket proxy:**
8. WS passthrough — frames forwarded both directions
9. WS connection refusal — first connection refused, second passes through
10. WS disconnect action — abrupt close mid-stream
11. WS frame suppression — client ATTACH suppressed, server never sees it
12. WS inject_to_client — proxy injects a frame, original also forwarded
13. WS inject_to_client_and_close — proxy injects then closes
14. WS frame replacement — original frame replaced with different one
15. WS suppress_onwards — all subsequent server frames dropped
16. WS count matching — rule only fires on Nth connection/frame
17. WS one-shot rule (times=1) — fires once then removed

**HTTP proxy:**
18. HTTP passthrough — request forwarded, response returned
19. HTTP respond — fake 401 returned for first request, second passes through
20. HTTP delay — response delayed by specified duration
21. HTTP drop — connection dropped, no response
22. HTTP replace_response — upstream response discarded, fake one returned
23. HTTP count matching

**Imperative actions:**
24. Disconnect via actions API
25. Inject message via actions API
26. Action on session with no active WS returns error

**Temporal triggers:**
27. delay_after_ws_connect fires and disconnects
28. delay_after_ws_connect cancelled if connection closes first
29. delay_after_ws_connect cancelled on session delete

**Event log:**
30. Log captures WS connect, frames, disconnect events
31. Log captures HTTP request/response events
32. Log records which rule matched (or null for passthrough)

**Concurrent sessions:**
33. Two sessions on different ports with different rules don't interfere

**Msgpack:**
34. Binary (msgpack) frames parsed and matched by action
35. Binary frames forwarded unchanged (no re-encoding)

## Data types

### Session

```go
type Session struct {
    ID           string
    Target       TargetConfig
    Port         int
    Rules        []*Rule
    EventLog     *EventLog
    TimeoutTimer *time.Timer
    Listener     net.Listener
    Server       *http.Server

    activeWsConns []*WsConnection
    wsConnectCount int
    httpReqCount   int

    suppressServerToClient bool
    suppressClientToServer bool

    mu sync.Mutex
}

type TargetConfig struct {
    RealtimeHost string `json:"realtimeHost"`
    RestHost     string `json:"restHost"`
}
```

### Rule

```go
type Rule struct {
    Match   MatchConfig   `json:"match"`
    Action  ActionConfig  `json:"action"`
    Times   int           `json:"times,omitempty"`   // 0 = unlimited
    Comment string        `json:"comment,omitempty"`

    matchCount int // how many times the match condition was satisfied
}

type MatchConfig struct {
    Type          string            `json:"type"`
    Count         int               `json:"count,omitempty"`
    Action        string            `json:"action,omitempty"`
    Channel       string            `json:"channel,omitempty"`
    Method        string            `json:"method,omitempty"`
    PathContains  string            `json:"pathContains,omitempty"`
    QueryContains map[string]string `json:"queryContains,omitempty"`
    DelayMs       int               `json:"delayMs,omitempty"`
}

type ActionConfig struct {
    Type      string            `json:"type"`
    CloseCode int               `json:"closeCode,omitempty"`
    DelayMs   int               `json:"delayMs,omitempty"`
    Message   json.RawMessage   `json:"message,omitempty"`
    Status    int               `json:"status,omitempty"`
    Body      json.RawMessage   `json:"body,omitempty"`
    Headers   map[string]string `json:"headers,omitempty"`
}
```

### Event log

```go
type Event struct {
    Timestamp   time.Time         `json:"timestamp"`
    Type        string            `json:"type"`
    Direction   string            `json:"direction,omitempty"`
    URL         string            `json:"url,omitempty"`
    QueryParams map[string]string `json:"queryParams,omitempty"`
    Message     json.RawMessage   `json:"message,omitempty"`
    Method      string            `json:"method,omitempty"`
    Path        string            `json:"path,omitempty"`
    Status      int               `json:"status,omitempty"`
    Initiator   string            `json:"initiator,omitempty"`
    CloseCode   int               `json:"closeCode,omitempty"`
    RuleMatched *string           `json:"ruleMatched"`
    Headers     map[string]string `json:"headers,omitempty"`
}

type EventLog struct {
    events []Event
    mu     sync.Mutex
}
```

### Protocol message (minimal parsing)

```go
type ProtocolMessage struct {
    Action  int
    Channel string
    Error   *ErrorInfo
}

type ErrorInfo struct {
    Code       int    `json:"code"`
    StatusCode int    `json:"statusCode"`
    Message    string `json:"message"`
}

// Action name constants
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

// actionNames maps name strings to int for rule matching
var actionNames = map[string]int{
    "HEARTBEAT":    0,
    "ACK":          1,
    // ...
}
```

### WsConnection

```go
type WsConnection struct {
    ClientConn *websocket.Conn
    ServerConn *websocket.Conn
    ConnNumber int
    timers     []*time.Timer
    closed     bool
    mu         sync.Mutex
}
```

## Build and run

```bash
cd uts/test/proxy
go mod init ably.io/test-proxy
go get github.com/gorilla/websocket
go get github.com/vmihailenco/msgpack/v5
go build -o test-proxy .

# Run (control API on port 9100)
./test-proxy --port 9100

# Run tests
go test ./... -v
```

## Integration with Dart test runner

The Dart test harness will:

1. Spawn the proxy process: `Process.start('test-proxy', ['--port', '9100'])`
2. Wait for `GET http://localhost:9100/health` to return 200
3. Maintain a port pool (e.g., 10000–11023)
4. For each test (or test group):
   a. Allocate a port from the pool
   b. Create a session: `POST http://localhost:9100/sessions` with `{"port": 10042, "target": {...}, "rules": [...]}`
   c. If 409 (port conflict), try another port
   d. Configure the SDK:
      ```dart
      ClientOptions(
        realtimeHost: 'localhost:10042',
        restHost: 'localhost:10042',
        tls: false,
        key: sandboxKey,
      )
      ```
   e. Run the test
   f. Delete the session: `DELETE http://localhost:9100/sessions/{id}`
   g. Return port to pool
5. After all tests, kill the proxy process

## Port pool design (Dart side)

```dart
class PortPool {
  final Set<int> _available;
  final Set<int> _inUse = {};

  PortPool({int start = 10000, int count = 1024})
      : _available = Set.from(List.generate(count, (i) => start + i));

  int allocate() {
    if (_available.isEmpty) throw StateError('No ports available');
    final port = _available.first;
    _available.remove(port);
    _inUse.add(port);
    return port;
  }

  void release(int port) {
    _inUse.remove(port);
    _available.add(port);
  }
}
```
