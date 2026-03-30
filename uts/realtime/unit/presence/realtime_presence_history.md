# RealtimePresence History Tests

Spec points: `RTP12`, `RTP12a`, `RTP12c`, `RTP12d`

## Test Type
Unit test — mock WebSocket required (for channel setup), REST mock for history request.

## Purpose

Tests the `RealtimePresence#history` function which delegates to `RestPresence#history`.
It supports the same parameters as `RestPresence#history` and returns a `PaginatedResult`.

---

## RTP12a - history supports same params as RestPresence#history

**Spec requirement:** Supports all the same params as RestPresence#history.

### Setup
```pseudo
channel_name = "test-RTP12a-${random_id()}"

captured_history_requests = []
mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

# Mock the REST history endpoint
mock_rest = MockRest(
  onRequest: (method, path, params) => {
    captured_history_requests.append({ method: method, path: path, params: params })
    RETURN {
      items: [],
      statusCode: 200
    }
  }
)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

result = AWAIT channel.presence.history(
  start: 1000,
  end: 2000,
  direction: "backwards",
  limit: 50
)
```

### Assertions
```pseudo
ASSERT captured_history_requests.length == 1
ASSERT captured_history_requests[0].path == "/channels/${channel_name}/presence/history"
ASSERT captured_history_requests[0].params.start == 1000
ASSERT captured_history_requests[0].params.end == 2000
ASSERT captured_history_requests[0].params.direction == "backwards"
ASSERT captured_history_requests[0].params.limit == 50
```

---

## RTP12c - history returns PaginatedResult

**Spec requirement:** Returns a PaginatedResult page containing the first page of
messages in the PaginatedResult#items attribute.

### Setup
```pseudo
channel_name = "test-RTP12c-${random_id()}"

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => conn.respond_with_success(CONNECTED_MESSAGE),
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.send_to_client(ProtocolMessage(action: ATTACHED, channel: channel_name))
  }
)
install_mock(mock_ws)

mock_rest = MockRest(
  onRequest: (method, path, params) => {
    RETURN {
      items: [
        PresenceMessage(action: ENTER, clientId: "alice", timestamp: 1000),
        PresenceMessage(action: UPDATE, clientId: "alice", timestamp: 2000),
        PresenceMessage(action: LEAVE, clientId: "alice", timestamp: 3000)
      ],
      statusCode: 200
    }
  }
)

client = Realtime(options: ClientOptions(key: "fake.key:secret", autoConnect: false))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected
AWAIT channel.attach()

result = AWAIT channel.presence.history()
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items.length == 3
ASSERT result.items[0].clientId == "alice"
ASSERT result.items[0].action == ENTER
ASSERT result.items[2].action == LEAVE
```
