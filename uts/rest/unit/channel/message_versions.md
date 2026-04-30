# REST Channel GetMessageVersions Tests

Spec points: `RSL14`, `RSL14a`, `RSL14a1`, `RSL14b`, `RSL14c`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/test/rest/unit/helpers/mock_http.md`.

---

## RSL14b — getMessageVersions sends GET to correct endpoint

**Spec requirement:** RSL14b — The SDK must send a GET request to the endpoint `/channels/{channelName}/messages/{serial}/versions`.

Tests that `getMessageVersions()` sends a GET to the correct URL.

### Setup
```pseudo
channel_name = "test-RSL14b-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "name": "evt",
        "data": "v2-data",
        "serial": "msg-serial-1",
        "action": 1,
        "version": { "serial": "vs2", "timestamp": 1700000002000 }
      },
      {
        "name": "evt",
        "data": "v1-data",
        "serial": "msg-serial-1",
        "action": 0,
        "version": { "serial": "vs1", "timestamp": 1700000001000 }
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.getMessageVersions("msg-serial-1")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1/versions"
```

---

## RSL14c — getMessageVersions returns PaginatedResult of Messages

**Spec requirement:** RSL14c — Returns a `PaginatedResult<Message>`.

Tests that the response is parsed into a paginated result of decoded messages.

### Setup
```pseudo
channel_name = "test-RSL14c-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [
      {
        "name": "evt",
        "data": "updated-data",
        "serial": "msg-serial-1",
        "action": 1,
        "version": {
          "serial": "vs2",
          "timestamp": 1700000002000,
          "clientId": "user-1",
          "description": "edit"
        }
      },
      {
        "name": "evt",
        "data": "original-data",
        "serial": "msg-serial-1",
        "action": 0,
        "version": {
          "serial": "vs1",
          "timestamp": 1700000001000
        }
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.getMessageVersions("msg-serial-1")
```

### Assertions
```pseudo
ASSERT result IS PaginatedResult
ASSERT result.items.length == 2

ASSERT result.items[0] IS Message
ASSERT result.items[0].data == "updated-data"
ASSERT result.items[0].action == MessageAction.MESSAGE_UPDATE
ASSERT result.items[0].version.serial == "vs2"
ASSERT result.items[0].version.description == "edit"

ASSERT result.items[1].data == "original-data"
ASSERT result.items[1].action == MessageAction.MESSAGE_CREATE
```

---

## RSL14a — getMessageVersions passes params as querystring

**Spec requirement:** RSL14a — Takes an optional second argument of `Dict<string, stringifiable>` params.

Tests that optional params are sent as query parameters.

### Setup
```pseudo
channel_name = "test-RSL14a-params-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.getMessageVersions("msg-serial-1", params: {
  "direction": "backwards",
  "limit": "10"
})
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.query_params["direction"] == "backwards"
ASSERT request.url.query_params["limit"] == "10"
```
