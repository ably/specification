# RealtimeChannel History Tests

Spec points: `RTL10`, `RTL10a`, `RTL10b`, `RTL10c`

## Test Type
Unit test with mocked HTTP client

---

## RTL10a - RealtimeChannel#history supports all RestChannel#history params

| Spec | Requirement |
|------|-------------|
| RTL10a | Supports all the same params as `RestChannel#history` |
| RTL10c | Returns a `PaginatedResult` page containing the first page of messages |

`RealtimeChannel#history` uses the same underlying REST endpoint as `RestChannel#history`. The tests in `uts/test/rest/unit/channel/history.md` (covering RSL2) should be used to verify that all the same behaviour, parameters, and return types apply when called on a `RealtimeChannel` instance.

---

## RTL10b - untilAttach parameter

**Spec requirement:** Additionally supports the param `untilAttach`, which if true, will only retrieve messages prior to the moment that the channel was attached or emitted an UPDATE indicating loss of continuity. This bound is specified by passing the querystring param `fromSerial` with the `RealtimeChannel#properties.attachSerial` assigned to the channel in the ATTACHED ProtocolMessage (see RTL15a). If the `untilAttach` param is specified when the channel is not attached, it results in an error.

### RTL10b - untilAttach adds fromSerial query parameter

Tests that when `untilAttach` is true and the channel is attached, the history request includes a `fromSerial` query parameter set to the channel's `attachSerial`.

#### Setup
```pseudo
channel_name = "test-RTL10b-${random_id()}"
captured_requests = []
attach_serial = "serial-abc:0"

mock_http = MockHttpClient(
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [])
  }
)

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  },
  onMessageFromClient: (msg) => {
    IF msg.action == ATTACH:
      mock_ws.active_connection.send_to_client(ATTACHED(
        channel: channel_name,
        channelSerial: attach_serial
      ))
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws,
  httpClient: mock_http
)

channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

#### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED
AWAIT channel.attach()
ASSERT channel.state == ATTACHED

AWAIT channel.history(untilAttach: true)
```

#### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.query_params["fromSerial"] == attach_serial
CLOSE_CLIENT(client)
```

### RTL10b - untilAttach errors when not attached

Tests that when `untilAttach` is true and the channel is not attached, the history call results in an error.

#### Setup
```pseudo
channel_name = "test-RTL10b-err-${random_id()}"

mock_ws = MockWebSocketClient(
  onConnectionAttempt: (conn) => {
    conn.respond_with_success(CONNECTED())
  }
)

client = Realtime(
  options: ClientOptions(key: "appId.keyId:keySecret", autoConnect: false),
  webSocketClient: mock_ws
)

channel = client.channels.get(channel_name, RealtimeChannelOptions(attachOnSubscribe: false))
```

#### Test Steps
```pseudo
client.connect()
AWAIT_STATE connection == CONNECTED

ASSERT channel.state == INITIALIZED

error = null
TRY:
  AWAIT channel.history(untilAttach: true)
CATCH e:
  error = e
```

#### Assertions
```pseudo
ASSERT error IS AblyException
CLOSE_CLIENT(client)
```
