# PushAdmin Publish Tests

Spec points: `RSH1`, `RSH1a`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSH1 — client.push.admin exposes PushAdmin object

**Spec requirement:** RSH1 — `Push#admin` object provides the PushAdmin interface.

Tests that the REST client exposes a `push.admin` object of the correct type.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {})
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Assertions
```pseudo
ASSERT client.push IS Push
ASSERT client.push.admin IS PushAdmin
ASSERT client.push.admin.deviceRegistrations IS PushDeviceRegistrations
ASSERT client.push.admin.channelSubscriptions IS PushChannelSubscriptions
```

---

## RSH1a — publish sends POST to /push/publish

**Spec requirement:** RSH1a — `publish(recipient, data)` performs an HTTP request to `/push/publish`.

Tests that `push.admin.publish()` sends a POST with correct recipient and data.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.publish(
  recipient: {
    "transportType": "apns",
    "deviceToken": "foo"
  },
  data: {
    "notification": {
      "title": "Test",
      "body": "Hello"
    }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/publish"

body = parse_json(request.body)
ASSERT body["recipient"]["transportType"] == "apns"
ASSERT body["recipient"]["deviceToken"] == "foo"
ASSERT body["notification"]["title"] == "Test"
ASSERT body["notification"]["body"] == "Hello"
```

---

## RSH1a — publish with clientId recipient

**Spec requirement:** RSH1a — Tests should exist with valid recipient details.

Tests that publish works with a `clientId` recipient.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.publish(
  recipient: {
    "clientId": "user-123"
  },
  data: {
    "data": {
      "key": "value"
    }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

body = parse_json(captured_requests[0].body)
ASSERT body["recipient"]["clientId"] == "user-123"
ASSERT body["data"]["key"] == "value"
```

---

## RSH1a — publish with deviceId recipient

**Spec requirement:** RSH1a — Tests should exist with valid recipient details.

Tests that publish works with a `deviceId` recipient.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.publish(
  recipient: {
    "deviceId": "device-abc"
  },
  data: {
    "notification": {
      "title": "Device Push"
    }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

body = parse_json(captured_requests[0].body)
ASSERT body["recipient"]["deviceId"] == "device-abc"
ASSERT body["notification"]["title"] == "Device Push"
```

---

## RSH1a — publish rejects empty recipient

**Spec requirement:** RSH1a — Empty values for `recipient` should be immediately rejected.

Tests that calling publish with an empty recipient throws an error without making an HTTP request.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.publish(
  recipient: {},
  data: { "notification": { "title": "Test" } }
) FAILS WITH error
ASSERT error.code == 40000

# No HTTP request should have been made
ASSERT captured_requests.length == 0
```

---

## RSH1a — publish rejects empty data

**Spec requirement:** RSH1a — Empty values for `data` should be immediately rejected.

Tests that calling publish with empty data throws an error without making an HTTP request.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.publish(
  recipient: { "clientId": "user-123" },
  data: {}
) FAILS WITH error
ASSERT error.code == 40000

# No HTTP request should have been made
ASSERT captured_requests.length == 0
```

---

## RSH1a — publish rejects null recipient

**Spec requirement:** RSH1a — Empty values for `recipient` should be immediately rejected.

Tests that calling publish with a null recipient throws an error.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.publish(
  recipient: null,
  data: { "notification": { "title": "Test" } }
) FAILS WITH error
ASSERT error.code == 40000

ASSERT captured_requests.length == 0
```

---

## RSH1a — publish propagates server error

**Spec requirement:** RSH1a — Tests should exist with invalid recipient details.

Tests that a server error response is propagated to the caller.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(400, {
      "error": {
        "code": 40000,
        "statusCode": 400,
        "message": "Invalid recipient"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.publish(
  recipient: { "transportType": "invalid" },
  data: { "notification": { "title": "Test" } }
) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```
