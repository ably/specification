# Time and Stats Integration Tests

Spec points: `RSC16`, `RSC6`

## Test Type
Integration test against Ably sandbox

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- API key from provisioned app

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app()
  app_id = app_config.app_id
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RSC16 - time() returns server time

Tests that `time()` returns the current server time.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
before_request = now()
server_time = AWAIT client.time()
after_request = now()
```

### Assertions
```pseudo
# Server time should be a DateTime
ASSERT server_time IS DateTime

# Server time should be reasonably close to client time
# (allowing for network latency and minor clock differences)
ASSERT server_time >= before_request - 5000ms
ASSERT server_time <= after_request + 5000ms
```

---

## RSC6 - stats() returns application statistics

Tests that `stats()` returns stats for the application.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Stats may be empty for a new sandbox app, but the call should succeed
result = AWAIT client.stats()
```

### Assertions
```pseudo
# Result should be a PaginatedResult (may be empty)
ASSERT result IS PaginatedResult
ASSERT result.items IS List

# If there are items, they should have expected structure
IF result.items.length > 0:
  ASSERT result.items[0].intervalId IS String
  ASSERT result.items[0].unit IN ["minute", "hour", "day", "month"]
```

---

## RSC6 - stats() with parameters

Tests that `stats()` correctly applies query parameters.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
```

### Test Steps
```pseudo
# Request stats with specific parameters
result = AWAIT client.stats(
  limit: 5,
  direction: "forwards",
  unit: "hour"
)
```

### Assertions
```pseudo
# Should succeed with parameters applied
ASSERT result IS PaginatedResult
ASSERT result.items.length <= 5
```
