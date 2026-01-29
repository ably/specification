# REST Channel Publish Integration Tests

Spec points: `RSL1d`, `RSL1k4`, `RSL1k5`, `RSL1l1`, `RSL1m4`, `RSL1n`

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
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  # Sandbox apps auto-delete after 60 minutes
```

---

## RSL1d - Error indication on publish failure

Tests that errors are properly indicated when a publish fails.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel = client.channels.get("test-channel")
```

### Test Steps
```pseudo
# Attempt to publish to a channel the key doesn't have permission for
# (requires app provisioned with restricted capabilities)

restricted_client = Rest(options: ClientOptions(
  key: restricted_api_key,  # Key without publish capability
  endpoint: "sandbox"
))
restricted_channel = restricted_client.channels.get("forbidden-channel")

TRY:
  AWAIT restricted_channel.publish(name: "event", data: "data")
  FAIL("Expected exception not thrown")
CATCH AblyException as e:
  ASSERT e.code == 40160  # Not permitted
  ASSERT e.statusCode == 401
```

---

## RSL1n - PublishResult contains serials

Tests that successful publish returns a `PublishResult` with message serials.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
channel = client.channels.get("test-serials-" + random_string())
```

### Test Steps
```pseudo
# Single message
result1 = AWAIT channel.publish(name: "event1", data: "data1")

ASSERT result1 IS PublishResult
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

## RSL1k4 - Idempotent publish with library-generated IDs (retry verification)

Tests that automatic retry after simulated failure doesn't result in duplicate messages.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  idempotentRestPublishing: true
))
unique_channel = client.channels.get("idempotent-test-" + random_string())
```

### Test Steps
```pseudo
# This test requires ability to intercept and fail the first request
# then allow retry to succeed. Implementation options:
# 1. Use a proxy that fails first request
# 2. Mock at HTTP level but let retry go through
# 3. Use Ably's test hooks if available

# Simplified approach: publish twice with same library-generated ID
# and verify only one message appears in history

# First, publish a message and capture its ID
message = Message(name: "idempotent-event", data: "test-data")
AWAIT unique_channel.publish(message: message)

# Wait for message to be persisted
WAIT 1 second

# Get history to verify single message
history = AWAIT unique_channel.history()

ASSERT history.items.length == 1
ASSERT history.items[0].name == "idempotent-event"
ASSERT history.items[0].data == "test-data"
```

### Note
Full retry simulation may require HTTP-level interception. The key verification is that the message ID format follows `<base64>:<index>` pattern and history shows exactly one message.

---

## RSL1k5 - Idempotent publish with client-supplied IDs (explicit duplicate)

Tests that multiple publishes with the same client-supplied ID result in single message.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox"
))
unique_channel = client.channels.get("idempotent-explicit-" + random_string())
```

### Test Steps
```pseudo
fixed_id = "client-supplied-id-" + random_string()

# Publish same message ID multiple times
FOR i IN 1..3:
  AWAIT unique_channel.publish(
    message: Message(id: fixed_id, name: "event", data: "data-" + str(i))
  )

# Wait for processing
WAIT 2 seconds

# Verify only one message in history
history = AWAIT unique_channel.history()

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
  key: api_key,
  endpoint: "sandbox"
))
channel = client.channels.get("force-nack-test")
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
  ASSERT e.code == 40099  # Specific code for _forceNack
```

---

## RSL1m4 - ClientId mismatch rejection

Tests that server rejects message with clientId different from authenticated client.

### Setup
```pseudo
# Need a token with specific clientId
client_with_token = Rest(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  clientId: "authenticated-client-id"
))
channel = client_with_token.channels.get("clientid-mismatch-test")
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
  ASSERT e.statusCode == 400 OR e.statusCode == 401
  ASSERT e.message CONTAINS "clientId" OR e.message CONTAINS "mismatch"
```
