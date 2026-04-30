# REST Channel GetMessage Tests

Spec points: `RSL11`, `RSL11a`, `RSL11a1`, `RSL11b`, `RSL11c`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/test/rest/unit/helpers/mock_http.md`.

---

## RSL11b — getMessage sends GET to correct endpoint

**Spec requirement:** RSL11b — The SDK must send a GET request to the endpoint `/channels/{channelName}/messages/{serial}`.

Tests that `getMessage()` sends a GET request to the correct URL.

### Setup
```pseudo
channel_name = "test-RSL11b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "name": "evt",
      "data": "hello",
      "serial": "msg-serial-123",
      "timestamp": 1700000000000
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.getMessage("msg-serial-123")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-123"
ASSERT request.body IS null OR request.body IS empty
```

---

## RSL11c — getMessage returns decoded Message

**Spec requirement:** RSL11c — Returns the decoded `Message` object for the specified message serial.

Tests that `getMessage()` returns a fully decoded `Message` with all fields populated.

### Setup
```pseudo
channel_name = "test-RSL11c-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "id": "msg-id-1",
      "name": "test-event",
      "data": "hello world",
      "serial": "serial-xyz",
      "clientId": "client-1",
      "timestamp": 1700000000000,
      "extras": { "push": { "notification": { "title": "Test" } } },
      "version": {
        "serial": "version-serial-1",
        "timestamp": 1700000000000,
        "clientId": "client-1"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
msg = AWAIT channel.getMessage("serial-xyz")
```

### Assertions
```pseudo
ASSERT msg IS Message
ASSERT msg.id == "msg-id-1"
ASSERT msg.name == "test-event"
ASSERT msg.data == "hello world"
ASSERT msg.serial == "serial-xyz"
ASSERT msg.clientId == "client-1"
ASSERT msg.timestamp == 1700000000000
ASSERT msg.version.serial == "version-serial-1"
```

---

## RSL11b — getMessage URL-encodes serial in path

**Spec requirement:** RSL11b — The serial must be URL-encoded when used in the request path.

Tests that special characters in the serial are properly URL-encoded.

### Setup
```pseudo
channel_name = "test-RSL11b-encode-${random_id()}"
captured_requests = []
serial_with_special_chars = "serial/with:special+chars"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "name": "evt",
      "data": "hello",
      "serial": serial_with_special_chars
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.getMessage(serial_with_special_chars)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/" + encode_uri_component(serial_with_special_chars)
```

---

## RSL11a — getMessage with missing serial throws error

**Spec requirement:** RSL11a — Takes a first argument of a `serial` string of the message to be retrieved. The serial must be present.

Tests that calling `getMessage()` with an empty or missing serial throws an error.

### Setup
```pseudo
channel_name = "test-RSL11a-error-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
# Empty string serial
AWAIT channel.getMessage("") FAILS WITH error
ASSERT error.code == 40003
```
