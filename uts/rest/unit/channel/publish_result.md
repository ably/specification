# REST Channel Publish Result Tests

Spec points: `RSL1n`, `RSL1n1`, `PBR1`, `PBR2a`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/test/rest/unit/helpers/mock_http.md`.

---

## RSL1n — publish() returns PublishResult with serials (single message)

| Spec | Requirement |
|------|-------------|
| RSL1n | On success, returns a `PublishResult` containing the serials of the published messages |
| PBR2a | `serials` is an array of `String?` corresponding 1:1 to the messages that were published |

Tests that `publish()` returns a `PublishResult` with a serials array matching the published messages.

### Setup
```pseudo
channel_name = "test-RSL1n-single-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["serial-abc"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.publish(name: "event", data: "hello")
```

### Assertions
```pseudo
ASSERT result IS PublishResult
ASSERT result.serials IS List
ASSERT result.serials.length == 1
ASSERT result.serials[0] == "serial-abc"
```

---

## RSL1n — publish() returns PublishResult with serials (batch)

**Spec requirement:** RSL1n — When publishing multiple messages, the returned `PublishResult.serials` array has one entry per message, corresponding 1:1.

Tests that batch publish returns serials matching each published message.

### Setup
```pseudo
channel_name = "test-RSL1n-batch-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "serials": ["s1", "s2", "s3"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
messages = [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3")
]
result = AWAIT channel.publish(messages: messages)
```

### Assertions
```pseudo
ASSERT result IS PublishResult
ASSERT result.serials.length == 3
ASSERT result.serials[0] == "s1"
ASSERT result.serials[1] == "s2"
ASSERT result.serials[2] == "s3"
```

---

## RSL1n — publish() returns PublishResult with null serial (conflated message)

| Spec | Requirement |
|------|-------------|
| PBR2a | A serial may be null if the message was discarded due to a configured conflation rule |

Tests that null serials in the response are preserved in the `PublishResult`.

### Setup
```pseudo
channel_name = "test-RSL1n-null-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(201, { "serials": [null, "s2"] })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
messages = [
  Message(name: "event1", data: "data1"),
  Message(name: "event2", data: "data2")
]
result = AWAIT channel.publish(messages: messages)
```

### Assertions
```pseudo
ASSERT result.serials.length == 2
ASSERT result.serials[0] IS null
ASSERT result.serials[1] == "s2"
```
