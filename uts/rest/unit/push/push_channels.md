# PushChannel Tests

Spec points: `RSH7`, `RSH7a`, `RSH7a1`, `RSH7a2`, `RSH7a3`, `RSH7b`, `RSH7b1`, `RSH7b2`, `RSH7c`, `RSH7c1`, `RSH7c2`, `RSH7c3`, `RSH7d`, `RSH7d1`, `RSH7d2`, `RSH7e`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

## Notes

These tests cover the `PushChannel` interface (`RSH7`), which is the `push` field on `RestChannel` and `RealtimeChannel`. This is distinct from the `push.admin.channelSubscriptions` API (`RSH1c`) — the `PushChannel` methods operate from the perspective of the local device (the push target), not the admin API.

The `PushChannel` methods require access to a `LocalDevice` (`RSH8`) which represents the current device's push registration state. In unit tests, the `LocalDevice` is configured with test values to simulate a registered device.

Push device authentication (`RSH6`) means adding either an `X-Ably-DeviceToken` header (if the device has a `deviceIdentityToken`, per `RSH6a`) or an `X-Ably-DeviceSecret` header (if the device has a `deviceSecret`, per `RSH6b`).

---

## RSH7a1, RSH7a2, RSH7a3 — subscribeDevice sends POST with deviceId, channel name, and device auth

| Spec | Requirement |
|------|-------------|
| RSH7a1 | Fails if the LocalDevice doesn't have a deviceIdentityToken |
| RSH7a2 | Performs a POST request to /push/channelSubscriptions with the device's id and the channel name |
| RSH7a3 | The request must include push device authentication |

Tests that `subscribeDevice()` sends a POST to `/push/channelSubscriptions` with the device's `id` and the channel name in the request body, and includes the `X-Ably-DeviceToken` header for push device authentication.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "channel": "my-channel",
      "deviceId": "test-device-001"
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device as a registered push target
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
AWAIT channel.push.subscribeDevice()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/channelSubscriptions"

body = parse_json(request.body)
ASSERT body["channel"] == "my-channel"
ASSERT body["deviceId"] == "test-device-001"

# RSH7a3 + RSH6a — push device authentication via deviceIdentityToken
ASSERT request.headers["X-Ably-DeviceToken"] == "test-device-identity-token"
```

---

## RSH7a1 — subscribeDevice fails if no deviceIdentityToken

**Spec requirement:** RSH7a1 — Fails if the LocalDevice doesn't have a `deviceIdentityToken`, ie. it isn't registered yet.

Tests that `subscribeDevice()` fails when the local device has no `deviceIdentityToken`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device WITHOUT a deviceIdentityToken (not registered)
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: null,
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.push.subscribeDevice() FAILS WITH error
ASSERT error.code IS NOT null
ASSERT error.message CONTAINS "deviceIdentityToken"
```

---

## RSH7b1, RSH7b2 — subscribeClient sends POST with clientId and channel name

| Spec | Requirement |
|------|-------------|
| RSH7b1 | Fails if the LocalDevice doesn't have a clientId |
| RSH7b2 | Performs a POST request to /push/channelSubscriptions with the device's clientId and the channel name |

Tests that `subscribeClient()` sends a POST to `/push/channelSubscriptions` with the device's `clientId` and the channel name in the request body.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "channel": "my-channel",
      "clientId": "test-client"
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device with a clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
AWAIT channel.push.subscribeClient()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/channelSubscriptions"

body = parse_json(request.body)
ASSERT body["channel"] == "my-channel"
ASSERT body["clientId"] == "test-client"
```

---

## RSH7b1 — subscribeClient fails if no clientId

**Spec requirement:** RSH7b1 — Fails if the LocalDevice doesn't have a `clientId`.

Tests that `subscribeClient()` fails when the local device has no `clientId`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device WITHOUT a clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: null
)

channel = client.channels.get("my-channel")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.push.subscribeClient() FAILS WITH error
ASSERT error.code IS NOT null
ASSERT error.message CONTAINS "clientId"
```

---

## RSH7c1, RSH7c2, RSH7c3 — unsubscribeDevice sends DELETE with deviceId, channel name, and device auth

| Spec | Requirement |
|------|-------------|
| RSH7c1 | Fails if the LocalDevice doesn't have a deviceIdentityToken |
| RSH7c2 | Performs a DELETE request to /push/channelSubscriptions with the device's id and the channel name |
| RSH7c3 | The request must include push device authentication |

Tests that `unsubscribeDevice()` sends a DELETE to `/push/channelSubscriptions` with the device's `id` and the channel name as query parameters, and includes the `X-Ably-DeviceToken` header for push device authentication.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device as a registered push target
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
AWAIT channel.push.unsubscribeDevice()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/channelSubscriptions"
ASSERT request.url.queryParams["channel"] == "my-channel"
ASSERT request.url.queryParams["deviceId"] == "test-device-001"

# RSH7c3 + RSH6a — push device authentication via deviceIdentityToken
ASSERT request.headers["X-Ably-DeviceToken"] == "test-device-identity-token"
```

---

## RSH7c1 — unsubscribeDevice fails if no deviceIdentityToken

**Spec requirement:** RSH7c1 — Fails if the LocalDevice doesn't have a `deviceIdentityToken`, ie. it isn't registered yet.

Tests that `unsubscribeDevice()` fails when the local device has no `deviceIdentityToken`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device WITHOUT a deviceIdentityToken (not registered)
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: null,
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.push.unsubscribeDevice() FAILS WITH error
ASSERT error.code IS NOT null
ASSERT error.message CONTAINS "deviceIdentityToken"
```

---

## RSH7d1, RSH7d2 — unsubscribeClient sends DELETE with clientId and channel name

| Spec | Requirement |
|------|-------------|
| RSH7d1 | Fails if the LocalDevice doesn't have a clientId |
| RSH7d2 | Performs a DELETE request to /push/channelSubscriptions with the device's clientId and the channel name |

Tests that `unsubscribeClient()` sends a DELETE to `/push/channelSubscriptions` with the device's `clientId` and the channel name as query parameters.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device with a clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
AWAIT channel.push.unsubscribeClient()
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/channelSubscriptions"
ASSERT request.url.queryParams["channel"] == "my-channel"
ASSERT request.url.queryParams["clientId"] == "test-client"
```

---

## RSH7d1 — unsubscribeClient fails if no clientId

**Spec requirement:** RSH7d1 — Fails if the LocalDevice doesn't have a `clientId`.

Tests that `unsubscribeClient()` fails when the local device has no `clientId`.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device WITHOUT a clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: null
)

channel = client.channels.get("my-channel")
```

### Test Steps and Assertions
```pseudo
AWAIT channel.push.unsubscribeClient() FAILS WITH error
ASSERT error.code IS NOT null
ASSERT error.message CONTAINS "clientId"
```

---

## RSH7e — listSubscriptions sends GET with channel, deviceId, clientId, and concatFilters

**Spec requirement:** RSH7e — `#listSubscriptions(params)` performs a GET request to `/push/channelSubscriptions` and returns a paginated result with `PushChannelSubscription` objects filtered by the provided params, the channel name, the device ID, and the client ID if it exists, as supported by the REST API. A `concatFilters` param needs to be set to `true` as well.

Tests that `listSubscriptions()` sends a GET to `/push/channelSubscriptions` with the channel name, device ID, client ID (if present), any user-provided params, and `concatFilters=true`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "channel": "my-channel",
        "deviceId": "test-device-001"
      },
      {
        "channel": "my-channel",
        "clientId": "test-client"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device with both deviceId and clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: "test-client"
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
result = AWAIT channel.push.listSubscriptions({"limit": "10"})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/push/channelSubscriptions"

# Channel name, device ID, and client ID are automatically included
ASSERT request.url.queryParams["channel"] == "my-channel"
ASSERT request.url.queryParams["deviceId"] == "test-device-001"
ASSERT request.url.queryParams["clientId"] == "test-client"

# concatFilters must be set to true
ASSERT request.url.queryParams["concatFilters"] == "true"

# User-provided params are forwarded
ASSERT request.url.queryParams["limit"] == "10"

ASSERT result IS PaginatedResult
ASSERT result.items.length == 2
ASSERT result.items[0] IS PushChannelSubscription
ASSERT result.items[0].channel == "my-channel"
ASSERT result.items[0].deviceId == "test-device-001"
ASSERT result.items[1].clientId == "test-client"
```

---

## RSH7e — listSubscriptions omits clientId when LocalDevice has no clientId

**Spec requirement:** RSH7e — The client ID is included if it exists.

Tests that `listSubscriptions()` does not include `clientId` in the query parameters when the local device has no `clientId`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "channel": "my-channel",
        "deviceId": "test-device-001"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Configure the local device WITHOUT a clientId
client.device = LocalDevice(
  id: "test-device-001",
  deviceIdentityToken: "test-device-identity-token",
  clientId: null
)

channel = client.channels.get("my-channel")
```

### Test Steps
```pseudo
result = AWAIT channel.push.listSubscriptions({})
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.queryParams["channel"] == "my-channel"
ASSERT request.url.queryParams["deviceId"] == "test-device-001"
ASSERT request.url.queryParams["concatFilters"] == "true"
ASSERT "clientId" NOT IN request.url.queryParams

ASSERT result.items.length == 1
```
