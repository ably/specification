# REST Channel Publish Integration Tests

Spec points: `RSL1d`, `RSL1l1`, `RSL1m4`, `RSL1n`

## Test Type
Integration test against Ably sandbox

## Test Environment

### Prerequisites
- Ably sandbox app provisioned via `POST https://sandbox.realtime.ably-nonprod.net/apps`
- App must include multiple keys with different capabilities (see below)
- Channel names must be unique per test (see README for naming convention)

### App Configuration

The sandbox app must be provisioned with keys that have different capabilities:

```json
{
  "keys": [
    {
      "name": "full-access",
      "capability": "{\"*\":[\"*\"]}"
    },
    {
      "name": "restricted",
      "capability": "{\"allowed-channel\":[\"publish\",\"subscribe\"]}"
    }
  ]
}
```

### Setup Pattern
```pseudo
BEFORE ALL TESTS:
  app_config = provision_sandbox_app(config_with_multiple_keys)
  app_id = app_config.app_id
  full_access_key = app_config.keys[0].key_str
  restricted_key = app_config.keys[1].key_str  # Limited capabilities

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {full_access_key}
```

---

## RSL1d - Error indication on publish failure

Tests that errors are properly indicated when a publish fails due to insufficient permissions.

### Setup
```pseudo
channel_name = "forbidden-channel-" + random_id()  # Not in restricted key's capability

restricted_client = Rest(options: ClientOptions(
  key: restricted_key,  # Key without publish capability for this channel
  endpoint: "sandbox"
))
restricted_channel = restricted_client.channels.get(channel_name)
```

### Test Steps
```pseudo
TRY:
  AWAIT restricted_channel.publish(name: "event", data: "data")
  FAIL("Expected exception not thrown")
CATCH AblyException as e:
  ASSERT e.code == 40160  # Not permitted
  ASSERT e.statusCode == 401
```

---

## RSL1n - PublishResult contains serials

Tests that successful publish returns a result with message serials.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox"
))
channel_name = "test-serials-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# Single message
result1 = AWAIT channel.publish(name: "event1", data: "data1")

ASSERT result1.serials IS List
ASSERT result1.serials.length == 1
ASSERT result1.serials[0] IS String
ASSERT result1.serials[0].length > 0


# Multiple messages
result2 = AWAIT channel.publish(messages: [
  Message(name: "event2", data: "data2"),
  Message(name: "event3", data: "data3"),
  Message(name: "event4", data: "data4")
])

ASSERT result2.serials.length == 3
ASSERT ALL serial IN result2.serials: serial IS String AND serial.length > 0
ASSERT result2.serials ARE all unique
```

---

## RSL1k5 - Idempotent publish with client-supplied IDs

Tests that multiple publishes with the same client-supplied ID result in single message.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox"
))
channel_name = "idempotent-explicit-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
fixed_id = "client-supplied-id-" + random_id()

# Publish same message ID multiple times
FOR i IN 1..3:
  AWAIT channel.publish(
    message: Message(id: fixed_id, name: "event", data: "data-" + str(i))
  )

# Poll history until message appears (avoid fixed wait)
history = poll_until(
  condition: FUNCTION() =>
    result = AWAIT channel.history()
    RETURN result.items.length > 0,
  interval: 500ms,
  timeout: 10s
)

# Verify only one message in history
ASSERT history.items.length == 1
ASSERT history.items[0].id == fixed_id
# The data should be from the first publish (subsequent ones are no-ops)
ASSERT history.items[0].data == "data-1"
```

---

## RSL1l1 - Publish params with _forceNack

Tests that publish params are correctly transmitted by using the `_forceNack` test param.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox"
))
channel_name = "force-nack-test-" + random_id()
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
TRY:
  AWAIT channel.publish(
    message: Message(name: "event", data: "data"),
    params: { "_forceNack": "true" }
  )
  FAIL("Expected exception not thrown")
CATCH AblyException as e:
  ASSERT e.code == 40099  # Specific code for forced nack
```

---

## RSL1m4 - ClientId mismatch rejection

Tests that server rejects message with clientId different from authenticated client.

### Setup
```pseudo
# Create a token with a specific clientId
key_client = Rest(options: ClientOptions(
  key: full_access_key,
  endpoint: "sandbox"
))

token_details = AWAIT key_client.auth.requestToken(
  tokenParams: TokenParams(clientId: "authenticated-client-id")
)

# Client using token with clientId
token_client = Rest(options: ClientOptions(
  token: token_details.token,
  endpoint: "sandbox"
))

channel_name = "clientid-mismatch-" + random_id()
channel = token_client.channels.get(channel_name)
```

### Test Steps
```pseudo
TRY:
  AWAIT channel.publish(
    message: Message(
      name: "event",
      data: "data",
      clientId: "different-client-id"  # Doesn't match authenticated clientId
    )
  )
  FAIL("Expected exception not thrown")
CATCH AblyException as e:
  ASSERT e.code == 40012  # Incompatible clientId
  ASSERT e.statusCode == 400
```

---

## Notes

### Tests moved to unit tests

The following functionality is better tested via unit tests with a mocked HTTP client:

- **RSL1k4 - Idempotent retry verification**: Testing that automatic retry after failure doesn't duplicate messages requires HTTP-level interception. This is better done with a mock that can fail the first request and allow the retry. See `unit/channel/idempotency.md`.
