# PushAdmin createApnsBroadcast Tests

Spec points: `RSH1`, `RSH1d`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSH1d — createApnsBroadcast sends POST to /push/apnsBroadcastChannels

**Test ID**: `rest/unit/RSH1d/create-apns-broadcast-post-0`

**Spec requirement:** RSH1d — `createApnsBroadcast(options)` issues a `POST` request to `/push/apnsBroadcastChannels`.

Tests that `push.admin.createApnsBroadcast()` sends a POST to the correct path.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "id": "broadcast-1", "apnsChannelId": "apns-1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.createApnsBroadcast(
  options: { "messageStoragePolicy": 1 }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/apnsBroadcastChannels"
```

---

## RSH1d — createApnsBroadcast body contains messageStoragePolicy

**Test ID**: `rest/unit/RSH1d/message-storage-policy-1`

**Spec requirement:** RSH1d — the request body contains the `messageStoragePolicy`.

Tests that the supplied `messageStoragePolicy` is serialized into the request body.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "id": "broadcast-1", "apnsChannelId": "apns-1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.createApnsBroadcast(
  options: { "messageStoragePolicy": 0 }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

body = parse_json(captured_requests[0].body)
ASSERT body["messageStoragePolicy"] == 0
```

---

## RSH1d — createApnsBroadcast returns id and apnsChannelId

**Test ID**: `rest/unit/RSH1d/returns-ids-2`

**Spec requirement:** RSH1d — returns the created broadcast as `{ id, apnsChannelId }`.

Tests that the `id` and `apnsChannelId` are parsed from the response body and returned.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(201, {
    "id": "broadcast-xyz",
    "apnsChannelId": "apple-channel-abc"
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.createApnsBroadcast(
  options: { "messageStoragePolicy": 1 }
)
```

### Assertions
```pseudo
ASSERT result.id == "broadcast-xyz"
ASSERT result.apnsChannelId == "apple-channel-abc"
```

---

## RSH1d — createApnsBroadcast request includes an auth header

**Test ID**: `rest/unit/RSH1d/auth-header-3`

**Spec requirement:** RSH1d — the request is authenticated.

Tests that the request carries a Basic authorization header derived from the API key.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(201, { "id": "broadcast-1", "apnsChannelId": "apns-1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.createApnsBroadcast(
  options: { "messageStoragePolicy": 1 }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1
ASSERT captured_requests[0].headers["Authorization"] STARTS_WITH "Basic "
```

---

## RSH1d — createApnsBroadcast propagates server error

**Test ID**: `rest/unit/RSH1d/server-error-4`

**Spec requirement:** RSH1d — a server error response is propagated to the caller.

Tests that an error response from the server is surfaced to the caller.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(400, {
    "error": {
      "code": 40000,
      "statusCode": 400,
      "message": "Invalid request"
    }
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.createApnsBroadcast(
  options: { "messageStoragePolicy": 1 }
) FAILS WITH error
ASSERT error.code == 40000
```
