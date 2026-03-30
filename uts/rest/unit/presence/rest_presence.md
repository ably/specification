# REST Presence Unit Tests

Spec points: `RSL3`, `RSP1`, `RSP1a`, `RSP1b`, `RSP3`, `RSP3a1`, `RSP3a2`, `RSP3a3`, `RSP4`, `RSP4a`, `RSP4b1`, `RSP4b2`, `RSP4b3`, `RSP5`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure described in `/Users/paddy/data/worknew/dev/dart-experiments/uts/test/rest/unit/rest_client.md`.

The mock supports:
- Intercepting HTTP requests and capturing details (URL, headers, method, body)
- Queueing responses with configurable status, headers, and body
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Recording requests in `captured_requests` arrays
- Request counting with `request_count` variables

---

## RSP1, RSL3 - RestPresence object associated with channel

### RSP1a, RSL3 - Presence accessible via RestChannel#presence

**Spec requirement:** Each `RestChannel` provides access to a `RestPresence` object via the `presence` property (RSP1a). The `RestChannel#presence` attribute contains a `RestPresence` object for this channel (RSL3).

```pseudo
channel_name = "test-RSP1a-${random_id()}"

Given a REST client with mocked HTTP
And a channel channel_name
When accessing channel.presence
Then a RestPresence object is returned
And the presence object is associated with channel_name
```

### RSP1b - Same presence object returned for same channel

**Spec requirement:** The same `RestPresence` instance must be returned for multiple accesses to the same channel's presence property.

```pseudo
channel_name = "test-RSP1b-${random_id()}"

Given a REST client with mocked HTTP
And a channel = client.channels.get(channel_name)
When accessing channel.presence multiple times
Then the same RestPresence instance is returned each time
```

---

## RSP3 - RestPresence#get

### RSP3a - Get sends GET request to presence endpoint

**Spec requirement:** The `get` method sends a GET request to `/channels/<channel_id>/presence` and returns a `PaginatedResult<PresenceMessage>`.

### Setup
```pseudo
channel_name = "test-RSP3a-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    req.respond_with(200, [
      { "action": 1, "clientId": "client1", "data": "hello" },
      { "action": 1, "clientId": "client2", "data": "world" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT request_count == 1
ASSERT captured_requests[0].method == "GET"
ASSERT captured_requests[0].url.path == "/channels/" + encode_uri_component(channel_name) + "/presence"
ASSERT result IS PaginatedResult<PresenceMessage>
ASSERT result.items.length == 2
```

---

### RSP3b - Get returns PresenceMessage objects

**Spec requirement:** The response items must be decoded into `PresenceMessage` objects with all fields correctly populated.

### Setup
```pseudo
channel_name = "test-RSP3b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "user123",
        "connectionId": "conn456",
        "data": "status data",
        "encoding": null,
        "timestamp": 1234567890000
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items.length == 1
ASSERT result.items[0] IS PresenceMessage
ASSERT result.items[0].action == PresenceAction.present  # action 1
ASSERT result.items[0].clientId == "user123"
ASSERT result.items[0].connectionId == "conn456"
ASSERT result.items[0].data == "status data"
ASSERT result.items[0].timestamp == 1234567890000
```

---

### RSP3c - Get with no members returns empty list

**Spec requirement:** When no presence members exist, `get` returns an empty list in the `PaginatedResult`.

### Setup
```pseudo
channel_name = "test-RSP3c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items IS List
ASSERT result.items.length == 0
ASSERT result.hasNext() == false
```

---

### RSP3a1a - Get with limit parameter

**Spec requirement:** The `limit` parameter must be included in the query string when specified.

### Setup
```pseudo
channel_name = "test-RSP3a1a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 1, "clientId": "client1" },
      { "action": 1, "clientId": "client2" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get(limit: 50)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["limit"] == "50"
```

---

### RSP3a1b - Get limit defaults to 100

**Spec requirement:** When no limit is specified, the default limit of 100 is used (or not explicitly sent).

### Setup
```pseudo
channel_name = "test-RSP3a1b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT "limit" NOT IN captured_requests[0].url.query_params
  OR captured_requests[0].url.query_params["limit"] == "100"
```

---

### RSP3a1c - Get limit maximum is 1000

**Spec requirement:** The maximum allowed limit value is 1000.

### Setup
```pseudo
channel_name = "test-RSP3a1c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get(limit: 1000)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["limit"] == "1000"
```

---

### RSP3a2 - Get with clientId filter

**Spec requirement:** The `clientId` parameter filters presence members by client identifier.

### Setup
```pseudo
channel_name = "test-RSP3a2-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 1, "clientId": "specific-client", "data": "filtered" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get(clientId: "specific-client")
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["clientId"] == "specific-client"
```

---

### RSP3a3 - Get with connectionId filter

**Spec requirement:** The `connectionId` parameter filters presence members by connection identifier.

### Setup
```pseudo
channel_name = "test-RSP3a3-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 1, "clientId": "client1", "connectionId": "conn123" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get(connectionId: "conn123")
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["connectionId"] == "conn123"
```

---

### RSP3 - Get with multiple filters

**Spec requirement:** Multiple query parameters can be combined in a single request.

### Setup
```pseudo
channel_name = "test-RSP3-multi-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get(
  limit: 25,
  clientId: "user1",
  connectionId: "conn1"
)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["limit"] == "25"
ASSERT captured_requests[0].url.query_params["clientId"] == "user1"
ASSERT captured_requests[0].url.query_params["connectionId"] == "conn1"
```

---

## RSP4 - RestPresence#history

### RSP4a - History sends GET request to presence history endpoint

| Spec | Requirement |
|------|-------------|
| RSP4 | History method fetches presence event history |
| RSP4a | Returns `PaginatedResult<PresenceMessage>` |

### Setup
```pseudo
channel_name = "test-RSP4a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 2, "clientId": "client1", "data": "entered" },
      { "action": 4, "clientId": "client1", "data": "left" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT captured_requests[0].method == "GET"
ASSERT captured_requests[0].url.path == "/channels/" + encode_uri_component(channel_name) + "/presence/history"
ASSERT result IS PaginatedResult<PresenceMessage>
```

---

### RSP4a - History returns PaginatedResult of PresenceMessage

**Spec requirement:** History responses contain `PresenceMessage` objects with various action types.

### Setup
```pseudo
channel_name = "test-RSP4a-result-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 2, "clientId": "user1", "data": "d1", "timestamp": 1000 },
      { "action": 3, "clientId": "user1", "data": "d2", "timestamp": 2000 },
      { "action": 4, "clientId": "user1", "data": "d3", "timestamp": 3000 }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult<PresenceMessage>
ASSERT result.items.length == 3
ASSERT result.items[0].action == PresenceAction.enter   # action 2
ASSERT result.items[1].action == PresenceAction.leave   # action 3
ASSERT result.items[2].action == PresenceAction.update  # action 4
```

---

### RSP4b1a - History with start parameter

**Spec requirement:** The `start` parameter filters events from a given timestamp (inclusive).

### Setup
```pseudo
channel_name = "test-RSP4b1a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
start_time = 1609459200000  # 2021-01-01 00:00:00 UTC
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(start: start_time)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["start"] == "1609459200000"
```

---

### RSP4b1b - History with end parameter

**Spec requirement:** The `end` parameter filters events up to a given timestamp (inclusive).

### Setup
```pseudo
channel_name = "test-RSP4b1b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
end_time = 1609545600000  # 2021-01-02 00:00:00 UTC
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(end: end_time)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["end"] == "1609545600000"
```

---

### RSP4b1c - History with start and end parameters

**Spec requirement:** Start and end parameters can be combined to define a time range.

### Setup
```pseudo
channel_name = "test-RSP4b1c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
start_time = 1609459200000
end_time = 1609545600000
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(
  start: start_time,
  end: end_time
)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["start"] == "1609459200000"
ASSERT captured_requests[0].url.query_params["end"] == "1609545600000"
```

---

### RSP4b1d - History accepts DateTime objects for start/end

**Spec requirement:** Language-specific DateTime objects should be accepted and converted to milliseconds since epoch.

### Setup
```pseudo
channel_name = "test-RSP4b1d-${random_id()}"
# Language-specific: if the language supports DateTime/Date objects
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
start_datetime = DateTime(2021, 1, 1, 0, 0, 0, UTC)  # language-specific
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(start: start_datetime)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["start"] == "1609459200000"
```

---

### RSP4b2a - History with direction backwards (default)

**Spec requirement:** The default direction is `backwards` (newest first).

### Setup
```pseudo
channel_name = "test-RSP4b2a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT "direction" NOT IN captured_requests[0].url.query_params
  OR captured_requests[0].url.query_params["direction"] == "backwards"
```

---

### RSP4b2b - History with direction forwards

**Spec requirement:** The `direction` parameter can be set to `forwards` (oldest first).

### Setup
```pseudo
channel_name = "test-RSP4b2b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(direction: "forwards")
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["direction"] == "forwards"
```

---

### RSP4b2c - History with direction backwards explicit

**Spec requirement:** The `direction` parameter can be explicitly set to `backwards`.

### Setup
```pseudo
channel_name = "test-RSP4b2c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(direction: "backwards")
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["direction"] == "backwards"
```

---

### RSP4b3a - History with limit parameter

**Spec requirement:** The `limit` parameter controls the maximum number of results per page.

### Setup
```pseudo
channel_name = "test-RSP4b3a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(limit: 50)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["limit"] == "50"
```

---

### RSP4b3b - History limit defaults to 100

**Spec requirement:** When no limit is specified, the default is 100.

### Setup
```pseudo
channel_name = "test-RSP4b3b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT "limit" NOT IN captured_requests[0].url.query_params
  OR captured_requests[0].url.query_params["limit"] == "100"
```

---

### RSP4b3c - History limit maximum is 1000

**Spec requirement:** The maximum allowed limit is 1000.

### Setup
```pseudo
channel_name = "test-RSP4b3c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(limit: 1000)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["limit"] == "1000"
```

---

### RSP4 - History with all parameters

**Spec requirement:** All query parameters can be combined in a single request.

### Setup
```pseudo
channel_name = "test-RSP4-all-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history(
  start: 1609459200000,
  end: 1609545600000,
  direction: "forwards",
  limit: 50
)
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.query_params["start"] == "1609459200000"
ASSERT captured_requests[0].url.query_params["end"] == "1609545600000"
ASSERT captured_requests[0].url.query_params["direction"] == "forwards"
ASSERT captured_requests[0].url.query_params["limit"] == "50"
```

---

## RSP5 - Presence message decoding

### RSP5a - String data decoded as string

**Spec requirement:** Plain string data must be decoded without modification.

### Setup
```pseudo
channel_name = "test-RSP5a-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 1, "clientId": "c1", "data": "plain string data" }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items[0].data == "plain string data"
ASSERT result.items[0].data IS String
```

---

### RSP5b - JSON encoded data decoded to object

**Spec requirement:** Data with `encoding: "json"` must be decoded from JSON string to native object.

### Setup
```pseudo
channel_name = "test-RSP5b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "c1",
        "data": "{\"status\":\"online\",\"count\":42}",
        "encoding": "json"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items[0].data IS Object/Map
ASSERT result.items[0].data["status"] == "online"
ASSERT result.items[0].data["count"] == 42
ASSERT result.items[0].encoding == null  # encoding consumed
```

---

### RSP5c - Base64 encoded data decoded to binary

**Spec requirement:** Data with `encoding: "base64"` must be decoded from base64 to binary.

### Setup
```pseudo
channel_name = "test-RSP5c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "c1",
        "data": "SGVsbG8gV29ybGQ=",  # "Hello World" in base64
        "encoding": "base64"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items[0].data IS Binary/Uint8List/[]byte
ASSERT result.items[0].data == bytes("Hello World")
ASSERT result.items[0].encoding == null  # encoding consumed
```

---

### RSP5d - UTF-8 encoded data decoded correctly

**Spec requirement:** Data with `encoding: "utf-8/base64"` must be decoded through both layers.

### Setup
```pseudo
channel_name = "test-RSP5d-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "c1",
        "data": "SGVsbG8gV29ybGQ=",  # base64 of UTF-8 bytes
        "encoding": "utf-8/base64"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items[0].data == "Hello World"
ASSERT result.items[0].data IS String
```

---

### RSP5e - Chained encoding decoded in order

**Spec requirement:** Chained encodings (e.g., `json/base64`) must be decoded in reverse order (last applied, first removed).

### Setup
```pseudo
channel_name = "test-RSP5e-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "c1",
        "data": "eyJrZXkiOiJ2YWx1ZSJ9",  # base64 of {"key":"value"}
        "encoding": "json/base64"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
# Decoding order: base64 first, then json
ASSERT result.items[0].data IS Object/Map
ASSERT result.items[0].data["key"] == "value"
```

---

### RSP5f - History messages also decoded

**Spec requirement:** Encoding decoding applies to both `get` and `history` methods.

### Setup
```pseudo
channel_name = "test-RSP5f-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 2,
        "clientId": "c1",
        "data": "{\"event\":\"entered\"}",
        "encoding": "json"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT result.items[0].data IS Object/Map
ASSERT result.items[0].data["event"] == "entered"
```

---

### RSP5g - Cipher decoding with channel options

**Spec requirement:** Encrypted data with cipher encoding must be decrypted using channel cipher options.

### Setup
```pseudo
channel_name = "test-RSP5g-${random_id()}"
captured_requests = []
cipher_key = base64_decode("WUP6u0K7MXI5Zeo0VppPwg==")

# Encrypted data for {"secret":"data"}
encrypted_data = "HO4cYSP8LybPYBPZPHQOtuD53yrD3YV3NBoTEYBh4U0="

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      {
        "action": 1,
        "clientId": "c1",
        "data": encrypted_data,
        "encoding": "json/utf-8/cipher+aes-128-cbc/base64"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name, options: RestChannelOptions(
  cipher: CipherParams(key: cipher_key, algorithm: "aes", mode: "cbc")
))
```

### Test Steps
```pseudo
result = AWAIT channel.presence.get()
```

### Assertions
```pseudo
ASSERT result.items[0].data IS Object/Map
# Decryption applied based on cipher+aes-128-cbc encoding
```

---

## Pagination

### RSP_Pagination_1 - Get returns paginated result with Link header

**Spec requirement:** Responses with Link headers must support pagination via `hasNext()` and `next()`.

### Setup
```pseudo
channel_name = "test-RSP-pagination1-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200,
      body: [
        { "action": 1, "clientId": "client1" },
        { "action": 1, "clientId": "client2" }
      ],
      headers: {
        "Link": "</channels/" + channel_name + "/presence?page=2>; rel=\"next\""
      }
    )
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT result.items.length == 2
ASSERT result.hasNext() == true
```

---

### RSP_Pagination_2 - Get next page fetches from Link URL

**Spec requirement:** Calling `next()` must use the URL from the Link header to fetch the next page.

### Setup
```pseudo
channel_name = "test-RSP-pagination2-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "action": 1, "clientId": "client1" }],
        headers: { "Link": "</channels/" + channel_name + "/presence?page=2>; rel=\"next\"" }
      )
    ELSE:
      req.respond_with(200, body: [{ "action": 1, "clientId": "client2" }])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
page1 = AWAIT client.channels.get(channel_name).presence.get()
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
ASSERT page1.items[0].clientId == "client1"
ASSERT page2.items[0].clientId == "client2"
ASSERT page2.hasNext() == false
```

---

### RSP_Pagination_3 - History pagination works the same

**Spec requirement:** History results must support the same pagination behavior as get.

### Setup
```pseudo
channel_name = "test-RSP-pagination3-${random_id()}"
captured_requests = []
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    request_count++
    
    IF request_count == 1:
      req.respond_with(200,
        body: [{ "action": 2, "clientId": "c1", "timestamp": 3000 }],
        headers: { "Link": "</channels/" + channel_name + "/presence/history?page=2>; rel=\"next\"" }
      )
    ELSE:
      req.respond_with(200, body: [{ "action": 4, "clientId": "c1", "timestamp": 1000 }])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
page1 = AWAIT client.channels.get(channel_name).presence.history()
page2 = AWAIT page1.next()
```

### Assertions
```pseudo
ASSERT page1.items[0].action == PresenceAction.enter
ASSERT page2.items[0].action == PresenceAction.leave
```

---

## Error Handling

### RSP_Error_1 - Get with server error throws AblyException

**Spec requirement:** Server errors must be raised as `AblyException` with appropriate error code and status.

### Setup
```pseudo
channel_name = "test-RSP-error1-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(500, {
      "error": {
        "code": 50000,
        "statusCode": 500,
        "message": "Internal server error"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get() FAILS WITH error
ASSERT error.code == 50000
ASSERT error.statusCode == 500
```

---

### RSP_Error_2 - History with invalid auth throws AblyException

**Spec requirement:** Authentication errors must raise `AblyException` with code 40101.

### Setup
```pseudo
channel_name = "test-RSP-error2-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(401, {
      "error": {
        "code": 40101,
        "statusCode": 401,
        "message": "Invalid credentials"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "invalid.key:secret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history() FAILS WITH error
ASSERT error.code == 40101
ASSERT error.statusCode == 401
```

---

### RSP_Error_3 - Get with channel not found

**Spec requirement:** 404 responses must raise `AblyException` with code 40400.

### Setup
```pseudo
channel_name = "test-RSP-error3-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(404, {
      "error": {
        "code": 40400,
        "statusCode": 404,
        "message": "Channel not found"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get() FAILS WITH error
ASSERT error.code == 40400
ASSERT error.statusCode == 404
```

---

## Request Headers

### RSP_Headers_1 - Get includes standard headers

**Spec requirement:** All REST requests must include standard Ably headers (X-Ably-Version, Ably-Agent, Accept).

### Setup
```pseudo
channel_name = "test-RSP-headers1-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT "X-Ably-Version" IN captured_requests[0].headers
ASSERT captured_requests[0].headers["Ably-Agent"] contains "ably-"
ASSERT "Accept" IN captured_requests[0].headers
```

---

### RSP_Headers_2 - History includes authorization header

**Spec requirement:** Authenticated requests must include the Authorization header.

### Setup
```pseudo
channel_name = "test-RSP-headers2-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT "Authorization" IN captured_requests[0].headers
ASSERT captured_requests[0].headers["Authorization"] starts with "Basic "
```

---

### RSP_Headers_3 - Request ID included when enabled

**Spec requirement:** When `addRequestIds` is enabled, a unique `request_id` query parameter must be included.

### Setup
```pseudo
channel_name = "test-RSP-headers3-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  addRequestIds: true
))
```

### Test Steps
```pseudo
AWAIT client.channels.get(channel_name).presence.get()
```

### Assertions
```pseudo
ASSERT "request_id" IN captured_requests[0].url.query_params
ASSERT captured_requests[0].url.query_params["request_id"] IS NOT empty
```

---

## PresenceAction Values

### RSP_Action_1 - All presence actions correctly mapped

**Spec requirement:** All presence action values must be correctly mapped between wire protocol and SDK types.

### Setup
```pseudo
channel_name = "test-RSP-action1-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.push(req)
    req.respond_with(200, [
      { "action": 0, "clientId": "c1" },  # absent
      { "action": 1, "clientId": "c2" },  # present
      { "action": 2, "clientId": "c3" },  # enter
      { "action": 3, "clientId": "c4" },  # leave
      { "action": 4, "clientId": "c5" }   # update
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.channels.get(channel_name).presence.history()
```

### Assertions
```pseudo
ASSERT result.items[0].action == PresenceAction.absent
ASSERT result.items[1].action == PresenceAction.present
ASSERT result.items[2].action == PresenceAction.enter
ASSERT result.items[3].action == PresenceAction.leave
ASSERT result.items[4].action == PresenceAction.update
```

Note: Action values may vary by SDK. The wire protocol uses:
- 0 = absent
- 1 = present
- 2 = enter
- 3 = leave (some SDKs use 4)
- 4 = update (some SDKs use 3)

Verify against your SDK's specific mapping.
