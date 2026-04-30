# Batch Presence Tests

Tests for `RestClient#batchPresence` (RSC24) and related types (BAR*, BGR*, BGF*).

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

These tests use the mock HTTP infrastructure defined in `rest_client.md`. The mock supports:
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Capturing requests via `captured_requests` arrays
- Configurable responses with status codes, bodies, and headers

See `rest_client.md` for detailed mock interface documentation.

## Server Response Format

The server returns different formats depending on the outcome:
- **All success (HTTP 200):** Plain array of per-channel results: `[{channel, presence}, ...]`
- **Mixed/all failure (HTTP 400):** Wrapper with error and batch results:
  `{error: {code: 40020, ...}, batchResponse: [{channel, presence/error}, ...]}`
- **Server error (HTTP 500, 401, etc.):** Error object only: `{error: {code, ...}}`

The SDK normalises both success and mixed/failure formats into a
`BatchPresenceResponse` with computed `successCount`, `failureCount`, and `results`.

---

## RSC24 - batchPresence sends GET to /presence

**Spec requirement:** `RestClient#batchPresence` takes an array of channel name strings
and sends them as a comma separated string in the `channels` query parameter in a GET
request to `/presence`, returning a `BatchPresenceResponse` containing per-channel results.

### RSC24_1 - Sends GET request to /presence with channels query param

**Spec requirement:** batchPresence sends a GET request to `/presence` with channel
names joined as a comma-separated `channels` query parameter.

```pseudo
captured_requests = []
mock_http = MockHTTP(
  onRequest: (request) => {
    captured_requests.append(request)
    RETURN HttpResponse(status: 200, body: [
      { "channel": "channel-a", "presence": [] },
      { "channel": "channel-b", "presence": [] }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["channel-a", "channel-b"])

ASSERT captured_requests.length == 1
ASSERT captured_requests[0].method == "GET"
ASSERT captured_requests[0].url.path == "/presence"
ASSERT captured_requests[0].url.queryParameters["channels"] == "channel-a,channel-b"
```

### RSC24_2 - Single channel sends GET with single channel name

**Spec requirement:** batchPresence with a single channel sends the channel name in
the `channels` query parameter (no trailing comma).

```pseudo
captured_requests = []
mock_http = MockHTTP(
  onRequest: (request) => {
    captured_requests.append(request)
    RETURN HttpResponse(status: 200, body: [
      { "channel": "my-channel", "presence": [] }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["my-channel"])

ASSERT captured_requests[0].url.queryParameters["channels"] == "my-channel"
```

### RSC24_3 - Channel names with special characters are comma-joined

**Spec requirement:** Channel names containing special characters are joined with
commas as-is (the server handles parsing).

```pseudo
captured_requests = []
mock_http = MockHTTP(
  onRequest: (request) => {
    captured_requests.append(request)
    RETURN HttpResponse(status: 200, body: [
      { "channel": "foo:bar", "presence": [] },
      { "channel": "baz/qux", "presence": [] }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["foo:bar", "baz/qux"])

ASSERT captured_requests[0].url.queryParameters["channels"] == "foo:bar,baz/qux"
```

---

## BAR2 - BatchPresenceResponse structure

**Spec requirement:** The response is normalised into a `BatchPresenceResponse` with
computed `successCount`, `failureCount`, and `results` attributes (BAR2).

### BAR2_1 - successCount and failureCount computed from mixed response

The server returns HTTP 400 with `batchResponse` for mixed results. The SDK
computes `successCount` and `failureCount` from the per-channel results.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 400, body: {
      "error": { "code": 40020, "statusCode": 400, "message": "Batched response includes errors" },
      "batchResponse": [
        { "channel": "ch-1", "presence": [] },
        { "channel": "ch-2", "presence": [] },
        { "channel": "ch-3", "presence": [] },
        { "channel": "ch-4", "error": { "code": 40160, "statusCode": 401, "message": "Not permitted" } }
      ]
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["ch-1", "ch-2", "ch-3", "ch-4"])

ASSERT result.successCount == 3
ASSERT result.failureCount == 1
ASSERT result.results.length == 4
```

### BAR2_2 - All success

The server returns HTTP 200 with a plain array when all channels succeed.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 200, body: [
      { "channel": "ch-a", "presence": [] },
      { "channel": "ch-b", "presence": [] }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["ch-a", "ch-b"])

ASSERT result.successCount == 2
ASSERT result.failureCount == 0
ASSERT result.results.length == 2
```

### BAR2_3 - All failure

The server returns HTTP 400 with `batchResponse` when all channels fail.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 400, body: {
      "error": { "code": 40020, "statusCode": 400, "message": "Batched response includes errors" },
      "batchResponse": [
        { "channel": "ch-a", "error": { "code": 40160, "statusCode": 401, "message": "Not permitted" } },
        { "channel": "ch-b", "error": { "code": 40160, "statusCode": 401, "message": "Not permitted" } }
      ]
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["ch-a", "ch-b"])

ASSERT result.successCount == 0
ASSERT result.failureCount == 2
ASSERT result.results.length == 2
```

---

## BGR2 - BatchPresenceSuccessResult structure

**Spec requirement:** A successful per-channel result contains `channel` (string) and
`presence` (array of PresenceMessage).

### BGR2_1 - Success result with members present

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 200, body: [
      {
        "channel": "my-channel",
        "presence": [
          {
            "clientId": "client-1",
            "action": 1,
            "connectionId": "conn-abc",
            "id": "conn-abc:0:0",
            "timestamp": 1700000000000,
            "data": "hello"
          },
          {
            "clientId": "client-2",
            "action": 1,
            "connectionId": "conn-def",
            "id": "conn-def:0:0",
            "timestamp": 1700000000000,
            "data": { "key": "value" }
          }
        ]
      }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["my-channel"])

ASSERT result.results.length == 1

success = result.results[0]
ASSERT success IS BatchPresenceSuccessResult
ASSERT success.channel == "my-channel"
ASSERT success.presence.length == 2

ASSERT success.presence[0].clientId == "client-1"
ASSERT success.presence[0].action == PRESENT
ASSERT success.presence[0].connectionId == "conn-abc"
ASSERT success.presence[0].data == "hello"

ASSERT success.presence[1].clientId == "client-2"
ASSERT success.presence[1].data IS Object/Map
ASSERT success.presence[1].data["key"] == "value"
```

### BGR2_2 - Success result with empty presence (no members)

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 200, body: [
      { "channel": "empty-channel", "presence": [] }
    ])
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["empty-channel"])

success = result.results[0]
ASSERT success IS BatchPresenceSuccessResult
ASSERT success.channel == "empty-channel"
ASSERT success.presence.length == 0
```

---

## BGF2 - BatchPresenceFailureResult structure

**Spec requirement:** A failed per-channel result contains `channel` (string) and
`error` (ErrorInfo).

### BGF2_1 - Failure result with error details

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 400, body: {
      "error": { "code": 40020, "statusCode": 400, "message": "Batched response includes errors" },
      "batchResponse": [
        {
          "channel": "restricted-channel",
          "error": {
            "code": 40160,
            "statusCode": 401,
            "message": "Channel operation not permitted"
          }
        }
      ]
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["restricted-channel"])

ASSERT result.results.length == 1

failure = result.results[0]
ASSERT failure IS BatchPresenceFailureResult
ASSERT failure.channel == "restricted-channel"
ASSERT failure.error IS ErrorInfo
ASSERT failure.error.code == 40160
ASSERT failure.error.statusCode == 401
ASSERT failure.error.message CONTAINS "not permitted"
```

---

## Mixed results

### RSC24_Mixed_1 - Mixed success and failure results

**Spec requirement:** A batch presence request can succeed for some channels and fail
for others. The server returns HTTP 400 with a `batchResponse` containing both
success and failure per-channel results.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 400, body: {
      "error": { "code": 40020, "statusCode": 400, "message": "Batched response includes errors" },
      "batchResponse": [
        {
          "channel": "allowed-channel",
          "presence": [
            {
              "clientId": "user-1",
              "action": 1,
              "connectionId": "conn-1",
              "id": "conn-1:0:0",
              "timestamp": 1700000000000
            }
          ]
        },
        {
          "channel": "restricted-channel",
          "error": {
            "code": 40160,
            "statusCode": 401,
            "message": "Not permitted"
          }
        }
      ]
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

result = AWAIT client.batchPresence(["allowed-channel", "restricted-channel"])

ASSERT result.successCount == 1
ASSERT result.failureCount == 1
ASSERT result.results.length == 2

ASSERT result.results[0] IS BatchPresenceSuccessResult
ASSERT result.results[0].channel == "allowed-channel"
ASSERT result.results[0].presence.length == 1
ASSERT result.results[0].presence[0].clientId == "user-1"

ASSERT result.results[1] IS BatchPresenceFailureResult
ASSERT result.results[1].channel == "restricted-channel"
ASSERT result.results[1].error.code == 40160
```

---

## Error handling

### RSC24_Error_1 - Server error is propagated as an error

**Spec requirement:** A server-level error (e.g. 500) for the entire batch request
is propagated as an error, not a per-channel failure. The response contains only an
`error` field with no `batchResponse`.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 500, body: {
      "error": { "code": 50000, "statusCode": 500, "message": "Internal error" }
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

AWAIT client.batchPresence(["any-channel"]) FAILS WITH error
ASSERT error.code == 50000
ASSERT error.statusCode == 500
```

### RSC24_Error_2 - Authentication error is propagated as an error

**Spec requirement:** An authentication error (401) for the entire request is
propagated as an error.

```pseudo
mock_http = MockHTTP(
  onRequest: (request) => {
    RETURN HttpResponse(status: 401, body: {
      "error": { "code": 40101, "statusCode": 401, "message": "Invalid credentials" }
    })
  }
)

client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)

AWAIT client.batchPresence(["any-channel"]) FAILS WITH error
ASSERT error.code == 40101
ASSERT error.statusCode == 401
```

---

## Request authentication

### RSC24_Auth_1 - Request uses configured authentication

**Spec requirement:** batchPresence requests use the client's configured authentication
mechanism (Basic or Token auth).

```pseudo
captured_requests = []
mock_http = MockHTTP(
  onRequest: (request) => {
    captured_requests.append(request)
    RETURN HttpResponse(status: 200, body: [
      { "channel": "ch", "presence": [] }
    ])
  }
)

# Basic auth
client = Rest(options: ClientOptions(key: "fake.key:secret"), httpClient: mock_http)
AWAIT client.batchPresence(["ch"])

ASSERT captured_requests[0].headers["Authorization"] STARTS_WITH "Basic "
```
