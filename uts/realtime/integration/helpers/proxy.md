# Proxy Infrastructure for Integration Tests

## Overview

The Ably test proxy is a programmable HTTP/WebSocket proxy (Go, at `uts/test/proxy/`) that sits between the SDK under test and the Ably sandbox. It transparently forwards traffic by default, but can be configured with rules to inject faults — dropped connections, modified responses, injected protocol messages, delayed frames, etc.

Proxy integration tests use this to verify fault-handling behaviour against the real Ably backend, providing higher confidence than unit tests with mocked transports.

## When to Use Proxy Tests vs Unit Tests vs Direct Sandbox Tests

| Test type | When to use |
|-----------|-------------|
| **Unit test** (mock HTTP/WebSocket) | Testing client-side logic, state machines, request formation, error parsing. Fast, deterministic. |
| **Direct sandbox integration** | Testing happy-path behaviour: connect, publish, subscribe, presence. No fault injection needed. |
| **Proxy integration test** | Testing fault behaviour against the real backend: connection failures, resume, heartbeat starvation, token renewal under network errors, channel error injection. |

## Proxy Session Lifecycle

```pseudo
# 1. Create a proxy session with rules
session = create_proxy_session(
  endpoint: "sandbox",
  port: allocated_port,
  rules: [ ...rules... ]
)

# 2. Connect SDK through proxy
client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "localhost",      # REC1b2: sets both restHost and realtimeHost
  port: session.proxy_port,
  tls: false,
  useBinaryProtocol: false,  # Required: Dart SDK doesn't implement msgpack
  autoConnect: false
  # Note: explicit hostname endpoint automatically disables fallback hosts (REC2c2)
))

# 3. Run test scenario
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# 4. (Optional) Add rules dynamically or trigger imperative actions
session.add_rules(new_rules, position: "prepend")
session.trigger_action({ type: "disconnect" })

# 5. (Optional) Verify proxy event log
log = session.get_log()
ASSERT log CONTAINS event WHERE type == "ws_connect" AND queryParams.resume IS NOT null

# 6. Clean up
client.close()
session.close()
```

## Proxy Session Interface

```pseudo
interface ProxySession:
  session_id: String
  proxy_host: String     # Always "localhost"
  proxy_port: Int        # Assigned from port pool

  add_rules(rules: List<Rule>, position?: "append"|"prepend")
  trigger_action(action: ActionRequest)
  get_log(): List<Event>
  close()

function create_proxy_session(
  endpoint: String,       # e.g. "sandbox" → resolves to sandbox-realtime.ably.io / sandbox-rest.ably.io
  port: Int,
  rules?: List<Rule>,
  timeoutMs?: Int         # Session auto-cleanup timeout (default 30000)
): ProxySession
```

## Rule Format

Each rule has a **match** condition, an **action** to perform, and an optional **times** limit:

```json
{
  "match": { ... },
  "action": { ... },
  "times": 1,
  "comment": "human-readable label"
}
```

Rules are evaluated in order. First matching rule wins. Unmatched traffic passes through unchanged. When `times` is specified, the rule auto-removes after that many firings.

### Match Conditions

```json
// WebSocket connection attempt
{ "type": "ws_connect" }
{ "type": "ws_connect", "count": 2 }
{ "type": "ws_connect", "queryContains": { "resume": "*" } }

// WebSocket frame: server → client
{ "type": "ws_frame_to_client", "action": "CONNECTED" }
{ "type": "ws_frame_to_client", "action": "ATTACHED", "channel": "my-channel" }

// WebSocket frame: client → server
{ "type": "ws_frame_to_server", "action": "ATTACH", "channel": "my-channel" }

// HTTP request
{ "type": "http_request", "pathContains": "/channels/" }
{ "type": "http_request", "method": "POST", "pathContains": "/keys/" }

// Temporal trigger (fires once after delay from WS connect)
{ "type": "delay_after_ws_connect", "delayMs": 5000 }
```

**`count`**: 1-based occurrence counter. `count: 2` matches only the 2nd occurrence.

### Actions

```json
// Passthrough (default for unmatched traffic)
{ "type": "passthrough" }

// Connection-level
{ "type": "refuse_connection" }
{ "type": "accept_and_close", "closeCode": 1011 }
{ "type": "disconnect" }
{ "type": "close", "closeCode": 1000 }

// Frame manipulation
{ "type": "suppress" }
{ "type": "delay", "delayMs": 2000 }
{ "type": "inject_to_client", "message": { "action": 6, ... } }
{ "type": "inject_to_client_and_close", "message": { "action": 6, ... }, "closeCode": 1000 }
{ "type": "replace", "message": { "action": 4, ... } }
{ "type": "suppress_onwards" }

// HTTP
{ "type": "http_respond", "status": 401, "body": { ... } }
{ "type": "http_delay", "delayMs": 5000 }
{ "type": "http_drop" }
```

### Imperative Actions

For cases where timed rules are awkward (e.g. "drop the connection NOW"):

```json
{ "type": "disconnect" }
{ "type": "close", "closeCode": 1000 }
{ "type": "inject_to_client", "message": { ... } }
{ "type": "inject_to_client_and_close", "message": { ... } }
```

## Event Log

The proxy records all traffic through a session. The log can be retrieved to verify test assertions.

```json
{
  "events": [
    { "type": "ws_connect", "url": "ws://...", "queryParams": { "key": "..." } },
    { "type": "ws_frame", "direction": "server_to_client", "message": { "action": 4, ... } },
    { "type": "ws_disconnect", "initiator": "proxy", "closeCode": 1006 },
    { "type": "http_request", "method": "GET", "path": "/channels/test/messages" },
    { "type": "http_response", "status": 200 }
  ]
}
```

### Common Log Assertions

```pseudo
# Verify resume was attempted
log = session.get_log()
ws_connects = log.filter(e => e.type == "ws_connect")
ASSERT ws_connects.length >= 2
ASSERT ws_connects[1].queryParams["resume"] IS NOT null

# Verify a specific frame was sent
frames = log.filter(e => e.type == "ws_frame" AND e.direction == "client_to_server")
attach_frames = frames.filter(f => f.message.action == 10)  # ATTACH
ASSERT attach_frames.length == 1
```

## Protocol Message Action Numbers

| Name | Number | Direction |
|------|--------|-----------|
| HEARTBEAT | 0 | Both |
| ACK | 1 | Server → Client |
| NACK | 2 | Server → Client |
| CONNECT | 3 | Client → Server |
| CONNECTED | 4 | Server → Client |
| DISCONNECT | 5 | Client → Server |
| DISCONNECTED | 6 | Server → Client |
| CLOSE | 7 | Client → Server |
| CLOSED | 8 | Server → Client |
| ERROR | 9 | Server → Client |
| ATTACH | 10 | Client → Server |
| ATTACHED | 11 | Server → Client |
| DETACH | 12 | Client → Server |
| DETACHED | 13 | Server → Client |
| PRESENCE | 14 | Both |
| MESSAGE | 15 | Both |
| SYNC | 16 | Server → Client |
| AUTH | 17 | Client → Server |

## SDK ClientOptions for Proxy Tests

All proxy integration tests should configure the SDK with:

```pseudo
ClientOptions(
  key: api_key,
  endpoint: "localhost",      # REC1b2: sets both restHost and realtimeHost to "localhost"
  port: proxy_port,           # The proxy session's assigned port
  tls: false,                 # Proxy serves plain HTTP/WS; TLS only upstream
  useBinaryProtocol: false,   # Required: SDK doesn't implement msgpack
  autoConnect: false          # Explicit connect for test control
  # fallbackHosts: not needed — endpoint="localhost" auto-disables fallbacks (REC2c2)
)
```

## Conventions for Proxy Integration Test Specs

1. Each test references the spec point AND the corresponding unit test
2. Tests use `create_proxy_session()` with rules, then connect SDK through the proxy
3. Tests use `AWAIT_STATE` for state assertions and record state changes for sequence verification
4. Tests verify behaviour via SDK state AND proxy event log where useful
5. All tests use `useBinaryProtocol: false` (SDK doesn't implement msgpack)
6. All tests use `endpoint: "localhost"` which auto-disables fallback hosts (REC2c2)
7. Timeouts are generous (10-30s) since real network is involved
8. Each test file provisions a sandbox app in `BEFORE ALL TESTS` and cleans up in `AFTER ALL TESTS`
9. Each test creates its own proxy session and cleans it up after
