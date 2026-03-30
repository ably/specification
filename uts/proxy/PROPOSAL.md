# Ably Test Proxy — Proposal

## Overview

A programmable HTTP/WebSocket proxy that sits between an Ably SDK under test and the real Ably sandbox backend. The proxy transparently forwards traffic by default, but can be configured with **rules** to inject faults — dropped connections, modified responses, injected protocol messages, delayed frames, etc.

This enables **integration tests for fault behaviour** that would otherwise require mocking. The proxy gives tests the realism of talking to the actual Ably sandbox while retaining the ability to simulate network and protocol faults.

## Motivation

The existing UTS unit tests use mock HTTP/WebSocket clients to test fault handling (connection failures, token expiry, heartbeat starvation, channel errors, etc.). These are valuable but have limitations:

- They test against synthetic responses, not the real server protocol
- They cannot verify that resume actually works end-to-end with a real server
- They require the test to script every server response, including the "happy path" ones

A proxy-based approach lets tests rely on the real sandbox for normal behaviour and only inject specific faults. This increases confidence that the SDK handles real-world failure modes correctly.

## Architecture

```
                     ┌────────────────────────────────────────────┐
                     │          Ably Test Proxy (single process)  │
                     │                                            │
┌──────────┐         │  ┌──────────────────┐                      │      ┌───────────────┐
│  SDK     │────WS──▶│  │ :10042 (session1)│───wss──────────────▶│──────│ Ably Sandbox  │
│  under   │◀───────▶│  │ :10043 (session2)│◀──────────────────▶│  │◀────│ (real backend) │
│  test    │──HTTP──▶│  │ ...              │───https─────────────│──────│               │
└──────────┘         │  └──────────────────┘                      │      └───────────────┘
                     │                                            │
                     │  ┌──────────────────┐                      │
                     │  │ :9100 control API │                      │
                     │  └──────────────────┘                      │
                     └────────────────────────────────────────────┘
                              ▲
                              │ HTTP control API
                     ┌────────┴────────────┐
                     │  Test process        │
                     │  (creates sessions,  │
                     │   assigns ports,     │
                     │   adds rules,        │
                     │   triggers actions)  │
                     └─────────────────────┘
```

- **Single proxy process** serves multiple concurrent test sessions
- **Control API** (HTTP on a dedicated port, e.g. `:9100`) manages sessions and rules
- **Per-session ports** (assigned by the test process from a port pool) handle proxied WS and HTTP traffic. Each session binds its own TCP listener so the SDK can connect with standard URL paths.
- **No TLS between client and proxy.** The proxy serves plain HTTP/WS to the SDK. Upstream connections to the Ably sandbox use TLS (`wss://`, `https://`).
- **Default behaviour** is transparent passthrough to the real Ably sandbox
- **Protocol-aware for both JSON and msgpack.** The proxy decodes frames in both formats for rule matching. Raw bytes are forwarded unchanged (no re-encoding).

## Control API

Base URL: `http://localhost:{CONTROL_PORT}`

### Create session

The test process assigns a port from its port pool and passes it in the request. The proxy binds that port immediately — if the bind fails, the request fails with 409.

```
POST /sessions
Content-Type: application/json

{
  "target": {
    "realtimeHost": "sandbox-realtime.ably.io",
    "restHost": "sandbox-rest.ably.io"
  },
  "rules": [ ...rules... ],
  "timeoutMs": 30000,
  "port": 10042
}

Response 201:
{
  "sessionId": "abc123",
  "proxy": {
    "host": "localhost:10042",
    "port": 10042
  }
}

Response 409 (port unavailable):
{
  "error": "failed to bind port 10042: address already in use"
}
```

The SDK under test connects to the proxy port with standard URLs:
- WebSocket: `ws://localhost:10042/?key=...&heartbeats=true`
- REST: `http://localhost:10042/channels/test/messages`

### Add rules dynamically

```
POST /sessions/{sessionId}/rules
Content-Type: application/json

{
  "rules": [ ...additional rules... ],
  "position": "append"  // or "prepend"
}

Response 200:
{
  "ruleCount": 5
}
```

### Trigger an imperative action

For cases where timed rules are awkward (e.g., "drop the connection NOW"):

```
POST /sessions/{sessionId}/actions
Content-Type: application/json

{ "type": "disconnect" }

Response 200:
{ "ok": true }
```

### Get captured traffic log

```
GET /sessions/{sessionId}/log
Response 200:
{
  "events": [ ...see event format below... ]
}
```

### Teardown session

```
DELETE /sessions/{sessionId}
Response 200:
{
  "events": [ ...final captured traffic log... ]
}
```

Teardown closes all active connections, stops the per-session listener, and frees the port.

### Health check

```
GET /health
Response 200: { "ok": true }
```

## Rule format

Each rule has a **match** condition, an **action** to perform, and an optional **times** limit:

```jsonc
{
  "match": { ... },
  "action": { ... },
  "times": 1,          // optional: remove rule after N matches (default: unlimited)
  "comment": "..."     // optional: for readability
}
```

Rules are evaluated in order. The first matching rule wins. Unmatched traffic is passed through unchanged.

### Match conditions

#### WebSocket connection attempt

```jsonc
{ "type": "ws_connect" }
{ "type": "ws_connect", "count": 2 }          // only the 2nd connection attempt
{ "type": "ws_connect", "queryContains": { "resume": "*" } }  // has resume param
```

#### WebSocket frame from client → server

```jsonc
{ "type": "ws_frame_to_server" }
{ "type": "ws_frame_to_server", "action": "ATTACH" }
{ "type": "ws_frame_to_server", "action": "ATTACH", "channel": "my-channel" }
{ "type": "ws_frame_to_server", "action": "MESSAGE" }
```

#### WebSocket frame from server → client

```jsonc
{ "type": "ws_frame_to_client" }
{ "type": "ws_frame_to_client", "action": "CONNECTED" }
{ "type": "ws_frame_to_client", "action": "ATTACHED", "channel": "my-channel" }
{ "type": "ws_frame_to_client", "action": "HEARTBEAT" }
```

#### HTTP request

```jsonc
{ "type": "http_request" }
{ "type": "http_request", "method": "POST" }
{ "type": "http_request", "pathContains": "/channels/" }
{ "type": "http_request", "pathContains": "/keys/" }
```

#### Temporal trigger

```jsonc
{ "type": "delay_after_ws_connect", "delayMs": 5000 }
```

Fires once, `delayMs` after the WebSocket connection is established. Used for timed fault injection (e.g., heartbeat starvation, timed disconnection).

### Actions

#### Passthrough (default)

```jsonc
{ "type": "passthrough" }
```

Forward unchanged.

#### Connection-level faults

```jsonc
// Refuse the WebSocket connection at TCP level
{ "type": "refuse_connection" }

// Accept WebSocket handshake but immediately close
{ "type": "accept_and_close", "closeCode": 1011 }

// Disconnect abruptly (no close frame)
{ "type": "disconnect" }

// Close cleanly with code
{ "type": "close", "closeCode": 1000 }
```

#### Frame manipulation

```jsonc
// Suppress (swallow) the frame — don't forward it
{ "type": "suppress" }

// Delay before forwarding
{ "type": "delay", "delayMs": 2000 }

// Inject a frame to the client (as if from server), in addition to the matched frame
{ "type": "inject_to_client", "message": { "action": 6, ... } }

// Inject a frame to the client then close the WebSocket
{ "type": "inject_to_client_and_close", "message": { "action": 6, ... }, "closeCode": 1000 }

// Replace the frame with a different one
{ "type": "replace", "message": { "action": 4, ... } }

// Suppress all subsequent frames in the same direction (for heartbeat starvation)
{ "type": "suppress_onwards" }
```

#### HTTP faults

```jsonc
// Return a specific HTTP response instead of forwarding
{ "type": "http_respond", "status": 503, "body": { ... }, "headers": { ... } }

// Delay the HTTP response
{ "type": "http_delay", "delayMs": 5000 }

// Drop the HTTP connection (no response)
{ "type": "http_drop" }

// Forward but replace the response
{ "type": "http_replace_response", "status": 401, "body": { ... } }
```

## Event log format

All traffic through a session is recorded:

```jsonc
{
  "events": [
    {
      "timestamp": "2026-02-23T10:00:00.123Z",
      "type": "ws_connect",
      "url": "ws://...",
      "queryParams": { "key": "...", "heartbeats": "true" }
    },
    {
      "timestamp": "2026-02-23T10:00:00.200Z",
      "type": "ws_frame",
      "direction": "server_to_client",
      "message": { "action": 4, "connectionId": "...", ... },
      "ruleMatched": null
    },
    {
      "timestamp": "2026-02-23T10:00:01.500Z",
      "type": "ws_frame",
      "direction": "client_to_server",
      "message": { "action": 15, "channel": "test", ... },
      "ruleMatched": "rule-2"
    },
    {
      "timestamp": "2026-02-23T10:00:02.000Z",
      "type": "ws_disconnect",
      "initiator": "proxy",
      "closeCode": 1006
    },
    {
      "timestamp": "2026-02-23T10:00:02.100Z",
      "type": "http_request",
      "direction": "client_to_server",
      "method": "GET",
      "path": "/channels/test/messages",
      "headers": { ... }
    },
    {
      "timestamp": "2026-02-23T10:00:02.300Z",
      "type": "http_response",
      "direction": "server_to_client",
      "status": 200,
      "ruleMatched": null
    }
  ]
}
```

## Usage patterns

### Pattern 1: Imperative disconnect (RTN15a equivalent)

```
# Create passthrough session on port 10042
POST /sessions  {"port": 10042, "target": SANDBOX}

# Connect SDK: Realtime(realtimeHost: "localhost:10042", tls: false)
# Wait for CONNECTED

# Trigger disconnect
POST /sessions/{id}/actions  {"type": "disconnect"}

# SDK reconnects through proxy (passthrough), resumes
# Wait for CONNECTED again

# Verify from log
GET /sessions/{id}/log
→ expect two ws_connect events
→ expect second ws_connect has queryParams.resume
```

### Pattern 2: One-shot connection refusal (RTN14d equivalent)

```json
{
  "port": 10042,
  "target": {"realtimeHost": "sandbox-realtime.ably.io"},
  "rules": [{
    "match": {"type": "ws_connect", "count": 1},
    "action": {"type": "refuse_connection"},
    "times": 1
  }]
}
```

First connection attempt is refused. SDK retries. Second passes through to sandbox.

### Pattern 3: Injected DISCONNECTED with token error (RTN15h1 equivalent)

```json
{
  "port": 10042,
  "target": {"realtimeHost": "sandbox-realtime.ably.io"},
  "rules": [{
    "match": {"type": "delay_after_ws_connect", "delayMs": 1000},
    "action": {
      "type": "inject_to_client_and_close",
      "message": {
        "action": 6,
        "error": {"code": 40142, "statusCode": 401, "message": "Token expired"}
      }
    },
    "times": 1
  }]
}
```

### Pattern 4: REST 401 for token renewal (RSA4b4 equivalent)

```json
{
  "port": 10042,
  "target": {"restHost": "sandbox-rest.ably.io"},
  "rules": [{
    "match": {"type": "http_request", "pathContains": "/channels/"},
    "action": {
      "type": "http_respond",
      "status": 401,
      "body": {"error": {"code": 40142, "statusCode": 401, "message": "Token expired"}}
    },
    "times": 1
  }]
}
```

First channel request gets fake 401. Client renews token, retries. Second request passes through to real sandbox.

### Pattern 5: Heartbeat starvation (RTN23 equivalent)

```json
{
  "port": 10042,
  "target": {"realtimeHost": "sandbox-realtime.ably.io"},
  "rules": [{
    "match": {"type": "delay_after_ws_connect", "delayMs": 2000},
    "action": {"type": "suppress_onwards"},
    "times": 1
  }]
}
```

SDK connects, gets CONNECTED from real server. After 2s, proxy starts swallowing all server→client frames. Client heartbeat timer expires. Client disconnects and reconnects.

### Pattern 6: Channel attach suppression (RTL4f timeout equivalent)

```json
{
  "port": 10042,
  "target": {"realtimeHost": "sandbox-realtime.ably.io"},
  "rules": [{
    "match": {"type": "ws_frame_to_server", "action": "ATTACH", "channel": "test"},
    "action": {"type": "suppress"},
    "times": 1
  }]
}
```

Client sends ATTACH, proxy swallows it. Server never sees it, never responds. Client's attach timeout fires.

## Scope and non-goals

### In scope

- WebSocket proxying with Ably protocol message awareness (JSON and msgpack)
- HTTP proxying for REST API calls
- Rule-based fault injection (connection, frame, and HTTP levels)
- Imperative actions (disconnect, close)
- Traffic capture and logging
- Concurrent sessions on separate ports for parallel tests

### Not in scope

- Fake timers / time advancement (integration tests use real time with short configured timeouts)
- Mock authUrl server (tests can spin up their own if needed)
- TLS between client and proxy (proxy serves plain HTTP/WS; TLS is used only upstream to sandbox)
- Modifying the SDK's internal state

## Implementation

The proxy is implemented in Go. See `IMPLEMENTATION.md` for the implementation plan.
