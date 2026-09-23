# Time and Stats Integration Tests

Spec points: `RSC16`, `RSC6`

## Test Type
Integration test against Ably sandbox

## Sandbox Setup

Tests run against the Ably Sandbox at `https://sandbox.realtime.ably-nonprod.net`.

### App Provisioning

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RSC16 - time() returns server time

**Test ID**: `rest/integration/RSC16/time-returns-server-time-0`

**Spec requirement:** RSC16 - `time()` obtains the current server time.

Tests that `time()` returns the current server time.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox"
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

**Test ID**: `rest/integration/RSC6/stats-returns-result-0`

**Spec requirement:** RSC6 - `stats()` returns a `PaginatedResult` containing application statistics.

Tests that `stats()` returns stats for the application.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox"
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

**Test ID**: `rest/integration/RSC6/stats-with-parameters-1`

**Spec requirement:** RSC6 - `stats()` supports `limit`, `direction`, and `unit` parameters.

Tests that `stats()` correctly applies query parameters.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox"
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

---

## RSC6 - stats() returns the flattened entries API

**Test ID**: `rest/integration/RSC6/stats-flattened-entries-2`

**Spec requirement:** RSC6, TS12 - a `Stats` datapoint exposes the flattened
API: `intervalId` (TS12a), `unit` (TS12c), `entries` (TS12r), `schema` (TS12s),
and `appId` (TS12t). `entries` is a flat map keyed by dotted metric path.

Known statistics are injected via the sandbox stats-injection endpoint (G3),
then read back and asserted against the flattened shape. This guards against a
client silently falling back to the deprecated deeply-nested Stats structure:
such a client would deserialize the response into empty/absent `entries` and
fail these assertions.

> **Note on the injection shape.** The `POST /stats` body uses the *ingestion*
> form — deeply nested per-type (`inbound.realtime.messages.count`, ...) — which
> is distinct from the flattened `entries` form returned by a read. On read-back
> the ingested `inbound`/`outbound`/`all` groups appear under a `messages.`
> prefix, e.g. ingested `inbound.realtime.messages.count` is read back as the
> entry key `messages.inbound.realtime.messages.count`. The `X-Ably-Version: 6`
> header is required both to inject and, on read, to receive the flattened API.

### Setup
```pseudo
# A dedicated app is not required: the chosen interval is in the previous year,
# so it is complete (never "in progress") and untouched by other tests' traffic.
year = current_utc_year() - 1

# Ingestion-shape fixtures for three consecutive minute intervals.
fixtures = [
  { intervalId: "{year}-02-03:15:03",
    inbound:  { realtime: { messages: { count: 50, data: 5000 } } },
    outbound: { realtime: { messages: { count: 20, data: 2000 } } } },
  { intervalId: "{year}-02-03:15:04",
    inbound:  { realtime: { messages: { count: 60, data: 6000 } } },
    outbound: { realtime: { messages: { count: 10, data: 1000 } } } },
  { intervalId: "{year}-02-03:15:05",
    inbound:  { realtime: { messages: { count: 70, data: 7000 } } },
    outbound: { realtime: { messages: { count: 40, data: 4000 } } } },
]

# Inject via the authenticated stats endpoint (G3).
POST https://sandbox.realtime.ably-nonprod.net/stats
  WITH Authorization: Basic {api_key}
  WITH header X-Ably-Version: 6
  WITH body from fixtures

client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "nonprod:sandbox"
))
```

### Test Steps
```pseudo
# Injected stats can lag briefly; poll until all three intervals appear
# (deadline ~30s).
REPEAT UNTIL result.items.length == 3 OR deadline_reached:
  result = AWAIT client.stats(
    start: "{year}-02-03:15:03",
    end: "{year}-02-03:15:05",
    direction: "forwards"
  )
```

### Assertions
```pseudo
ASSERT result.items.length == 3

FOR i, item IN result.items:
  ASSERT item.intervalId == "{year}-02-03:15:0{i + 3}"
  ASSERT item.unit == "minute"                    # TS12c
  ASSERT item.schema IS String                    # TS12s
  ASSERT item.appId IS String                     # TS12t
  ASSERT item.intervalTime() IS DateTime          # TS12p (parsed from intervalId)

# entries (TS12r) is a flat dotted-path map; sum across the three intervals.
inbound  = SUM(item.entries["messages.inbound.realtime.messages.count"]  FOR item IN result.items)
outbound = SUM(item.entries["messages.outbound.realtime.messages.count"] FOR item IN result.items)
ASSERT inbound  == 50 + 60 + 70
ASSERT outbound == 20 + 10 + 40
```
