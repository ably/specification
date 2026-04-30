# PushChannelSubscriptions Tests

Spec points: `RSH1c`, `RSH1c1`, `RSH1c2`, `RSH1c3`, `RSH1c4`, `RSH1c5`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSH1c1 — list returns paginated PushChannelSubscription filtered by channel

**Spec requirement:** RSH1c1 — `#list(params)` performs a request to `/push/channelSubscriptions` and returns a paginated result with `PushChannelSubscription` objects filtered by the provided params.

Tests that `list()` sends a GET with `channel` filter and returns a `PaginatedResult<PushChannelSubscription>`.

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
        "deviceId": "device-001"
      },
      {
        "channel": "my-channel",
        "clientId": "client-abc"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.list({"channel": "my-channel"})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/push/channelSubscriptions"
ASSERT request.url.queryParams["channel"] == "my-channel"

ASSERT result IS PaginatedResult
ASSERT result.items.length == 2
ASSERT result.items[0] IS PushChannelSubscription
ASSERT result.items[0].channel == "my-channel"
ASSERT result.items[0].deviceId == "device-001"
ASSERT result.items[1].clientId == "client-abc"
```

---

## RSH1c1 — list filters by deviceId and clientId

**Spec requirement:** RSH1c1 — A test should exist filtering by `deviceId` and/or `clientId`.

Tests that `list()` forwards `deviceId` and `clientId` as query parameters.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "channel": "notifications",
        "deviceId": "device-001"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.list({
  "deviceId": "device-001",
  "clientId": "client-abc"
})
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.queryParams["deviceId"] == "device-001"
ASSERT captured_requests[0].url.queryParams["clientId"] == "client-abc"
ASSERT result.items.length == 1
```

---

## RSH1c1 — list supports limit for pagination

**Spec requirement:** RSH1c1 — A test should exist controlling the pagination with the `limit` attribute.

Tests that `list()` forwards the `limit` parameter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "channel": "ch-1",
        "deviceId": "device-001"
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.list({"limit": "5"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.queryParams["limit"] == "5"
```

---

## RSH1c2 — listChannels returns paginated channel names

**Spec requirement:** RSH1c2 — `#listChannels(params)` performs a request to `/push/channels` and returns a paginated result with `String` objects.

Tests that `listChannels()` sends a GET to the correct endpoint and returns a paginated list of channel name strings.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, ["channel-1", "channel-2", "channel-3"])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.listChannels({})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/push/channels"

ASSERT result IS PaginatedResult
ASSERT result.items.length == 3
ASSERT result.items[0] == "channel-1"
ASSERT result.items[1] == "channel-2"
ASSERT result.items[2] == "channel-3"
```

---

## RSH1c2 — listChannels supports limit and pagination

**Spec requirement:** RSH1c2 — A test should exist using the `limit` attribute and pagination.

Tests that `listChannels()` forwards the `limit` parameter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, ["channel-1"])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.channelSubscriptions.listChannels({"limit": "1"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.queryParams["limit"] == "1"
ASSERT result.items.length == 1
```

---

## RSH1c3 — save issues POST with PushChannelSubscription

**Spec requirement:** RSH1c3 — `#save(pushChannelSubscription)` issues a `POST` request to `/push/channelSubscriptions` using the `PushChannelSubscription` object argument.

Tests that `save()` sends a POST with the subscription in the body and returns the saved `PushChannelSubscription`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "channel": "my-channel",
      "deviceId": "device-001"
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
subscription = PushChannelSubscription(
  channel: "my-channel",
  deviceId: "device-001"
)

result = AWAIT client.push.admin.channelSubscriptions.save(subscription)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "POST"
ASSERT request.url.path == "/push/channelSubscriptions"

body = parse_json(request.body)
ASSERT body["channel"] == "my-channel"
ASSERT body["deviceId"] == "device-001"

ASSERT result IS PushChannelSubscription
ASSERT result.channel == "my-channel"
ASSERT result.deviceId == "device-001"
```

---

## RSH1c3 — save updates existing subscription

**Spec requirement:** RSH1c3 — A test should exist for a successful subsequent save with an update.

Tests that saving an existing subscription performs an update.

### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      req.respond_with(200, {
        "channel": "my-channel",
        "clientId": "client-abc"
      })
    ELSE:
      req.respond_with(200, {
        "channel": "my-channel",
        "clientId": "client-abc"
      })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
subscription = PushChannelSubscription(
  channel: "my-channel",
  clientId: "client-abc"
)

result1 = AWAIT client.push.admin.channelSubscriptions.save(subscription)
result2 = AWAIT client.push.admin.channelSubscriptions.save(subscription)
```

### Assertions
```pseudo
ASSERT request_count == 2
ASSERT result1.channel == "my-channel"
ASSERT result2.channel == "my-channel"
```

---

## RSH1c3 — save propagates server error

**Spec requirement:** RSH1c3 — A test should exist for a failed save operation.

Tests that a server error during save is propagated to the caller.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(400, {
      "error": {
        "code": 40000,
        "statusCode": 400,
        "message": "Invalid subscription"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
subscription = PushChannelSubscription(
  channel: "my-channel",
  deviceId: "device-001"
)

AWAIT client.push.admin.channelSubscriptions.save(subscription) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```

---

## RSH1c4 — remove issues DELETE with clientId subscription attributes

**Spec requirement:** RSH1c4 — `#remove(push_channel_subscription)` issues a `DELETE` request to `/push/channelSubscriptions` and deletes the channel subscription using the attributes as params to the `DELETE` request.

Tests that `remove()` sends a DELETE with the subscription's attributes as query parameters for a `clientId`-based subscription.

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
```

### Test Steps
```pseudo
subscription = PushChannelSubscription(
  channel: "my-channel",
  clientId: "client-abc"
)

AWAIT client.push.admin.channelSubscriptions.remove(subscription)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/channelSubscriptions"
ASSERT request.url.queryParams["channel"] == "my-channel"
ASSERT request.url.queryParams["clientId"] == "client-abc"
```

---

## RSH1c4 — remove issues DELETE with deviceId subscription attributes

**Spec requirement:** RSH1c4 — A test should exist that deletes a `deviceId` channel subscription.

Tests that `remove()` sends a DELETE with the subscription's attributes as query parameters for a `deviceId`-based subscription.

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
```

### Test Steps
```pseudo
subscription = PushChannelSubscription(
  channel: "my-channel",
  deviceId: "device-001"
)

AWAIT client.push.admin.channelSubscriptions.remove(subscription)
```

### Assertions
```pseudo
ASSERT captured_requests[0].method == "DELETE"
ASSERT captured_requests[0].url.path == "/push/channelSubscriptions"
ASSERT captured_requests[0].url.queryParams["channel"] == "my-channel"
ASSERT captured_requests[0].url.queryParams["deviceId"] == "device-001"
```

---

## RSH1c4 — remove succeeds for nonexistent subscription

**Spec requirement:** RSH1c4 — A test should exist that deletes a subscription that does not exist but still succeeds.

Tests that removing a nonexistent subscription does not throw an error.

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
```

### Test Steps and Assertions
```pseudo
subscription = PushChannelSubscription(
  channel: "nonexistent-channel",
  clientId: "nonexistent-client"
)

# Should not throw — server returns success even for nonexistent subscriptions
AWAIT client.push.admin.channelSubscriptions.remove(subscription)
```

---

## RSH1c5 — removeWhere issues DELETE with clientId param

**Spec requirement:** RSH1c5 — `#removeWhere(params)` issues a `DELETE` request to `/push/channelSubscriptions` and deletes the matching channel subscriptions provided in `params`.

Tests that `removeWhere()` sends a DELETE with `clientId` as a query parameter.

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
```

### Test Steps
```pseudo
AWAIT client.push.admin.channelSubscriptions.removeWhere({"clientId": "client-abc"})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/channelSubscriptions"
ASSERT request.url.queryParams["clientId"] == "client-abc"
```

---

## RSH1c5 — removeWhere issues DELETE with deviceId param

**Spec requirement:** RSH1c5 — A test should exist that deletes channel subscriptions by `deviceId`.

Tests that `removeWhere()` sends a DELETE with `deviceId` as a query parameter.

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
```

### Test Steps
```pseudo
AWAIT client.push.admin.channelSubscriptions.removeWhere({"deviceId": "device-001"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].method == "DELETE"
ASSERT captured_requests[0].url.path == "/push/channelSubscriptions"
ASSERT captured_requests[0].url.queryParams["deviceId"] == "device-001"
```

---

## RSH1c5 — removeWhere succeeds with no matching subscriptions

**Spec requirement:** RSH1c5 — A test should exist that issues a delete for subscriptions with no matching params and checks the operation still succeeds.

Tests that `removeWhere()` succeeds even when no subscriptions match the params.

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
```

### Test Steps and Assertions
```pseudo
# Should not throw — server returns success even with no matching subscriptions
AWAIT client.push.admin.channelSubscriptions.removeWhere({"clientId": "nonexistent-client"})
```
