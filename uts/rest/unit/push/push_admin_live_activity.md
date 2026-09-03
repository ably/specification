# PushAdmin Live Activity Tests

Spec points: `RSH1`, `RSH1e`, `RSH1e1`, `RSH1e2`, `RSH1e3`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSH1e1 — start sends POST to /push/apnsBroadcastChannels/:id/start

**Test ID**: `rest/unit/RSH1e1/start-post-0`

**Spec requirement:** RSH1e1 — `start(params)` issues a `POST` to `/push/apnsBroadcastChannels/:apnsBroadcast/start` with a body carrying the `apns` payload and the recipient `channels`; optional APNs delivery `headers` are included in the request body under a `headers` key.

Tests that `liveActivity.start()` POSTs the channels, apns payload and optional headers to the start endpoint, and does not include a `deviceId` when none is supplied.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.liveActivity.start(
  params: {
    "recipient": { "channels": ["nba:lakers", "nba:celtics"] },
    "apnsBroadcast": "broadcast-1",
    "apns": { "aps": { "event": "start", "attributes-type": "GameAttributes" } },
    "headers": { "apns-priority": "10", "apns-expiration": "1782948701" }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/apnsBroadcastChannels/broadcast-1/start"

body = parse_json(request.body)
ASSERT body["channels"] == ["nba:lakers", "nba:celtics"]
ASSERT body["apns"]["aps"]["event"] == "start"
ASSERT body DOES NOT CONTAIN KEY "deviceId"
ASSERT body["headers"] == { "apns-priority": "10", "apns-expiration": "1782948701" }
ASSERT request.headers["Authorization"] STARTS_WITH "Basic "
```

---

## RSH1e1 — start includes deviceId and url-encodes the broadcast id

**Test ID**: `rest/unit/RSH1e1/start-deviceid-encode-1`

**Spec requirement:** RSH1e1 — the recipient may be a single `deviceId` instead of `channels`; when supplied, the `deviceId` is included in the body (and no `channels` key is sent), and the `apnsBroadcast` id is URL-encoded in the request path.

Tests that a `deviceId`-only recipient is sent without a `channels` key, and that a broadcast id with reserved characters is URL-encoded in the path.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.liveActivity.start(
  params: {
    "recipient": { "deviceId": "device-7" },
    "apnsBroadcast": "broadcast/with space",
    "apns": { "aps": { "event": "start" } }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.url.path == "/push/apnsBroadcastChannels/" + encode_uri_component("broadcast/with space") + "/start"

body = parse_json(request.body)
ASSERT body["deviceId"] == "device-7"
ASSERT body DOES NOT CONTAIN KEY "channels"
```

---

## RSH1e2 — update sends POST to /push/apnsBroadcastChannels/:id/broadcast

**Test ID**: `rest/unit/RSH1e2/update-post-0`

**Spec requirement:** RSH1e2 — `update(params)` issues a `POST` to `/push/apnsBroadcastChannels/:apnsBroadcast/broadcast` with a body carrying the `apns` payload; optional APNs delivery `headers` are included in the request body under a `headers` key.

Tests that `liveActivity.update()` POSTs the apns payload to the broadcast endpoint and includes the supplied APNs delivery headers in the request body.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.liveActivity.update(
  params: {
    "apnsBroadcast": "broadcast-1",
    "apns": { "aps": { "event": "update", "content-state": { "homeScore": 14 } } },
    "headers": { "apns-priority": "10", "apns-expiration": "1782948701" }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/apnsBroadcastChannels/broadcast-1/broadcast"

body = parse_json(request.body)
ASSERT body["apns"]["aps"]["event"] == "update"

# The optional APNs delivery headers are sent in the request body under a "headers" key
ASSERT body["headers"] == { "apns-priority": "10", "apns-expiration": "1782948701" }
ASSERT request.headers["Authorization"] STARTS_WITH "Basic "
```

---

## RSH1e2 — update omits APNs delivery headers when not supplied

**Test ID**: `rest/unit/RSH1e2/update-no-headers-1`

**Spec requirement:** RSH1e2 — the `headers` are optional.

Tests that no `headers` key is included in the body when none are supplied, and the apns payload is still POSTed.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.liveActivity.update(
  params: {
    "apnsBroadcast": "broadcast-1",
    "apns": { "aps": { "event": "update", "content-state": {} } }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
body = parse_json(request.body)
ASSERT body["apns"]["aps"]["event"] == "update"
ASSERT body DOES NOT CONTAIN KEY "headers"
```

---

## RSH1e3 — end sends POST to /push/apnsBroadcastChannels/:id/end

**Test ID**: `rest/unit/RSH1e3/end-post-0`

**Spec requirement:** RSH1e3 — `end(params)` issues a `POST` to `/push/apnsBroadcastChannels/:apnsBroadcast/end` with a body carrying the `apns` payload.

Tests that `liveActivity.end()` POSTs the apns end payload to the end endpoint.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.liveActivity.end(
  params: {
    "apnsBroadcast": "broadcast-1",
    "apns": { "aps": { "event": "end", "content-state": { "homeScore": 112 }, "dismissal-date": 1700000000 } }
  }
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/apnsBroadcastChannels/broadcast-1/end"

body = parse_json(request.body)
ASSERT body["apns"]["aps"]["event"] == "end"
ASSERT body["apns"]["aps"]["dismissal-date"] == 1700000000
ASSERT request.headers["Authorization"] STARTS_WITH "Basic "
```

---

## RSH1e1 — start propagates server error

**Test ID**: `rest/unit/RSH1e1/server-error-2`

**Spec requirement:** RSH1e1 — a server error response is propagated to the caller.

Tests that an error response from the server is surfaced to the caller of `start`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(400, {
    "error": { "code": 40000, "statusCode": 400, "message": "Invalid request" }
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.liveActivity.start(
  params: {
    "recipient": { "channels": ["nba:lakers"] },
    "apnsBroadcast": "broadcast-1",
    "apns": {}
  }
) FAILS WITH error
ASSERT error.code == 40000
```

---

## RSH1e2 — update propagates server error

**Test ID**: `rest/unit/RSH1e2/server-error-2`

**Spec requirement:** RSH1e2 — a server error response is propagated to the caller.

Tests that an error response from the server is surfaced to the caller of `update`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(400, {
    "error": { "code": 40000, "statusCode": 400, "message": "Invalid request" }
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.liveActivity.update(
  params: { "apnsBroadcast": "broadcast-1", "apns": {} }
) FAILS WITH error
ASSERT error.code == 40000
```

---

## RSH1e3 — end propagates server error

**Test ID**: `rest/unit/RSH1e3/server-error-1`

**Spec requirement:** RSH1e3 — a server error response is propagated to the caller.

Tests that an error response from the server is surfaced to the caller of `end`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(400, {
    "error": { "code": 40000, "statusCode": 400, "message": "Invalid request" }
  })
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.liveActivity.end(
  params: { "apnsBroadcast": "broadcast-1", "apns": {} }
) FAILS WITH error
ASSERT error.code == 40000
```
