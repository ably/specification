# Connectivity Check Tests (REC3)

Spec points: `REC3`, `REC3a`, `REC3b`

## Test Type
Unit test with mocked WebSocket client and HTTP client

## Mock Infrastructure

See `uts/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.
See `uts/rest/unit/helpers/mock_http.md` for Mock HTTP Client specification.

---

## REC3a - Default connectivity check URL

**Test ID**: `realtime/unit/REC3a/default-connectivity-check-url-0`

Tests that the default connectivity check URL is `https://internet-up.ably-realtime.com/is-the-internet-up.txt`.

### Note
The connectivity check URL is used to verify internet connectivity before attempting to connect.

### Setup
```pseudo
mock_http = MockHttpClient()
# Queue response for connectivity check
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "yes"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
# Trigger connectivity check (implementation-specific)
# Some libraries expose this, others do it internally
result = AWAIT client.connection.checkConnectivity()
# OR: observe that connectivity check request was made during connection
```

### Assertions
```pseudo
connectivity_requests = mock_http.captured_requests.filter(
  r => r.url.path CONTAINS "is-the-internet-up"
)
ASSERT connectivity_requests.length >= 1
ASSERT connectivity_requests[0].url.toString() == "https://internet-up.ably-realtime.com/is-the-internet-up.txt"

CLOSE_CLIENT(client)
```

---

## REC3b - Custom connectivity check URL

**Test ID**: `realtime/unit/REC3b/custom-connectivity-check-url-0`

Tests that the `connectivityCheckUrl` option overrides the default.

### Setup
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://custom.example.com/connectivity",
  200,
  "ok"
)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  connectivityCheckUrl: "https://custom.example.com/connectivity"
))
```

### Test Steps
```pseudo
result = AWAIT client.connection.checkConnectivity()
```

### Assertions
```pseudo
connectivity_requests = mock_http.captured_requests.filter(
  r => r.url.host == "custom.example.com"
)
ASSERT connectivity_requests.length >= 1
ASSERT connectivity_requests[0].url.toString() == "https://custom.example.com/connectivity"

# Should NOT request the default URL
default_requests = mock_http.captured_requests.filter(
  r => r.url.host == "internet-up.ably-realtime.com"
)
ASSERT default_requests.length == 0

CLOSE_CLIENT(client)
```

---

## REC3 - Connectivity check response validation

**Test ID**: `realtime/unit/REC3/connectivity-check-validation-0`

Tests that the connectivity check expects a specific response.

### Test Cases

| ID | Response | Expected Result |
|----|----------|-----------------|
| 1 | HTTP 200 with body "yes" | Connected |
| 2 | HTTP 200 with body "no" | Not connected |
| 3 | HTTP 200 with empty body | Not connected |
| 4 | HTTP 404 | Not connected |
| 5 | Network error | Not connected |

### Setup (Case 1 - Success)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "yes"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == true

CLOSE_CLIENT(client)
```

### Setup (Case 2 - Wrong body)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  200,
  "no"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == false

CLOSE_CLIENT(client)
```

### Setup (Case 4 - HTTP error)
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response_for_url(
  "https://internet-up.ably-realtime.com/is-the-internet-up.txt",
  404,
  "Not Found"
)

client = Realtime(options: ClientOptions(key: "appId.keyId:keySecret"))
result = AWAIT client.connection.checkConnectivity()

ASSERT result == false

CLOSE_CLIENT(client)
```
