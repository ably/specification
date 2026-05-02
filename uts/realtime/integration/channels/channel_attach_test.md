# Realtime Channel Attach/Detach Integration Tests

Spec points: `RTL4`, `RTL4c`, `RTL5`, `RTL5d`, `RTL14`

## Test Type
Integration test against Ably sandbox

## Purpose

End-to-end verification that channel attach and detach protocol messages are
accepted by the server and produce the correct state transitions. Also verifies
that attaching to a channel with insufficient capability produces the correct
error.

## Sandbox Setup

```pseudo
BEFORE ALL TESTS:
  response = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json

  app_config = parse_json(response.body)
  api_key = app_config.keys[0].key_str
  app_id = app_config.app_id

  # Key at index 3 has subscribe-only capability: {"*":["subscribe"]}
  subscribe_only_key = app_config.keys[3].key_str

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

---

## RTL4c - Attach succeeds

| Spec | Requirement |
|------|-------------|
| RTL4c | An ATTACH ProtocolMessage is sent, state transitions to ATTACHING, then ATTACHED on confirmation |

**Spec requirement:** When attach() is called on a channel, the SDK sends an
ATTACH protocol message. The server responds with ATTACHED and the channel
transitions to the ATTACHED state.

### Setup
```pseudo
channel_name = "attach-RTL4c-" + random_id()

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

client.connect()
AWAIT_STATE client.connection.state == CONNECTED
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name)
ASSERT channel.state == INITIALIZED

AWAIT channel.attach()
```

### Assertions
```pseudo
ASSERT channel.state == ATTACHED
ASSERT channel.errorReason IS NULL

CLOSE_CLIENT(client)
```

---

## RTL5d - Detach succeeds

| Spec | Requirement |
|------|-------------|
| RTL5d | A DETACH ProtocolMessage is sent, state transitions to DETACHING, then DETACHED on confirmation |

**Spec requirement:** When detach() is called on an attached channel, the SDK
sends a DETACH protocol message. The server responds with DETACHED and the
channel transitions to the DETACHED state.

### Setup
```pseudo
channel_name = "detach-RTL5d-" + random_id()

client = Realtime(options: ClientOptions(
  key: api_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

client.connect()
AWAIT_STATE client.connection.state == CONNECTED

channel = client.channels.get(channel_name)
AWAIT channel.attach()
ASSERT channel.state == ATTACHED
```

### Test Steps
```pseudo
AWAIT channel.detach()
```

### Assertions
```pseudo
ASSERT channel.state == DETACHED

CLOSE_CLIENT(client)
```

---

## RTL14 - Insufficient capability causes channel FAILED

| Spec | Requirement |
|------|-------------|
| RTL14 | A channel-scoped ERROR transitions the channel to FAILED |

**Spec requirement:** When a client with restricted capabilities attempts to
attach to a channel for which it lacks permission, the server responds with a
channel-scoped ERROR and the channel transitions to FAILED with the appropriate
error code.

### Setup
```pseudo
channel_name = "publish-not-allowed-" + random_id()

# Use key with subscribe-only capability
client = Realtime(options: ClientOptions(
  key: subscribe_only_key,
  endpoint: "sandbox",
  autoConnect: false,
  useBinaryProtocol: false
))

client.connect()
AWAIT_STATE client.connection.state == CONNECTED
```

### Test Steps
```pseudo
channel = client.channels.get(channel_name)

# Attach succeeds (subscribe-only key can attach to any channel)
AWAIT channel.attach()
ASSERT channel.state == ATTACHED

# Publish should fail — key lacks publish capability
AWAIT channel.publish(name: "test", data: "data") FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT NULL
ASSERT error.code == 40160
ASSERT error.statusCode == 401

# Connection should remain connected (channel-scoped error)
ASSERT client.connection.state == CONNECTED

CLOSE_CLIENT(client)
```
