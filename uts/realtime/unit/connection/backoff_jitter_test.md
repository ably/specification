# Backoff and Jitter Tests (RTB1)

Spec points: `RTB1`, `RTB1a`, `RTB1b`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Overview

RTB1 defines how retry delays are calculated for connections in the DISCONNECTED state and channels in the SUSPENDED state. The delay is the product of three factors:

1. **Initial retry timeout** (`disconnectedRetryTimeout` for connections, `channelRetryTimeout` for channels)
2. **Backoff coefficient** (RTB1a): `min((n + 2) / 3, 2)` for the nth retry
3. **Jitter coefficient** (RTB1b): a random number uniformly distributed between 0.8 and 1.0

---

## RTB1a - Backoff coefficient follows min((n+2)/3, 2) for successive retries

**Spec requirement:** The backoff coefficient for the nth retry is calculated as the minimum of `(n + 2) / 3` and `2` (resulting in the sequence `[1, 4/3, 5/3, 2, 2, ...]`).

Tests that the backoff coefficient calculation produces the correct sequence of values for successive retries.

### Setup

```pseudo
# This test verifies the backoff coefficient calculation function directly.
# The function under test takes a retry count (1-indexed) and returns the
# backoff coefficient.

# Expected values:
# n=1: min((1+2)/3, 2) = min(1, 2) = 1.0
# n=2: min((2+2)/3, 2) = min(4/3, 2) = 1.333...
# n=3: min((3+2)/3, 2) = min(5/3, 2) = 1.666...
# n=4: min((4+2)/3, 2) = min(2, 2) = 2.0
# n=5: min((5+2)/3, 2) = min(7/3, 2) = 2.0
# n=10: min((10+2)/3, 2) = min(4, 2) = 2.0
```

### Test Steps

```pseudo
# Calculate backoff coefficients for retries 1 through 10
coefficients = []
FOR n IN 1..10:
  coefficient = get_backoff_coefficient(n)
  coefficients.append(coefficient)
```

### Assertions

```pseudo
# Verify exact values for the first few retries
ASSERT coefficients[0] == 1.0          # n=1: (1+2)/3 = 1
ASSERT coefficients[1] == 4.0 / 3.0    # n=2: (2+2)/3 = 4/3
ASSERT coefficients[2] == 5.0 / 3.0    # n=3: (3+2)/3 = 5/3
ASSERT coefficients[3] == 2.0          # n=4: (4+2)/3 = 2, capped at 2

# Verify all subsequent retries are capped at 2.0
FOR i IN 3..9:
  ASSERT coefficients[i] == 2.0
```

---

## RTB1b - Jitter coefficient is between 0.8 and 1.0

**Spec requirement:** The jitter coefficient is a random number between 0.8 and 1. The randomness of this number doesn't need to be cryptographically secure but should be approximately uniformly distributed.

Tests that the jitter coefficient is always within the valid range and shows reasonable distribution.

### Setup

```pseudo
# This test verifies the jitter coefficient generator.
# We sample it many times and verify range and approximate uniformity.
```

### Test Steps

```pseudo
sample_count = 1000
jitter_values = []

FOR i IN 1..sample_count:
  jitter = get_jitter_coefficient()
  jitter_values.append(jitter)
```

### Assertions

```pseudo
# All values must be within [0.8, 1.0]
FOR jitter IN jitter_values:
  ASSERT jitter >= 0.8
  ASSERT jitter <= 1.0

# Verify approximate uniformity: the mean should be close to 0.9
# (the midpoint of 0.8 and 1.0). Allow some tolerance for randomness.
mean = sum(jitter_values) / sample_count
ASSERT mean >= 0.85
ASSERT mean <= 0.95

# Verify spread: not all values are the same (degenerate case)
min_value = min(jitter_values)
max_value = max(jitter_values)
ASSERT max_value - min_value > 0.05
```

---

## RTB1 - Combined retry delay for DISCONNECTED connections

| Spec | Requirement |
|------|-------------|
| RTB1 | Retry delay = disconnectedRetryTimeout * backoff coefficient * jitter coefficient |
| RTB1a | Backoff coefficient = min((n+2)/3, 2) |
| RTB1b | Jitter coefficient is between 0.8 and 1.0 |

Tests that the retry delay reported in ConnectionStateChange.retryIn falls within the expected range for successive DISCONNECTED retries, computed as `disconnectedRetryTimeout * backoff * jitter`.

### Setup

```pseudo
connection_attempt_count = 0
retry_delays = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++

    IF connection_attempt_count == 1:
      # Initial connection succeeds
      conn.respond_with_success(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-id",
        connectionKey: "connection-key",
        connectionDetails: ConnectionDetails(
          connectionKey: "connection-key",
          maxIdleInterval: 15000,
          connectionStateTtl: 60000
        )
      ))
    ELSE:
      # All reconnection attempts fail
      conn.respond_with_refused()
  }
)
install_mock(mock_ws)

disconnected_retry_timeout = 2000  # 2 seconds

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: disconnected_retry_timeout,
  autoConnect: false,
  useBinaryProtocol: false
))

# Capture retryIn from DISCONNECTED state changes
client.connection.on((change) => {
  IF change.current == ConnectionState.disconnected:
    retry_delays.append(change.retryIn)
})
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Simulate unexpected disconnect to trigger reconnection cycle
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Advance time in increments to allow multiple retry cycles.
# Each retry fails (respond_with_refused), producing another DISCONNECTED
# state change with a retryIn value.
# We want at least 5 DISCONNECTED events to verify the backoff sequence.
LOOP up to 30 times:
  ADVANCE_TIME(5000)
  IF retry_delays.length >= 5:
    BREAK
```

### Assertions

```pseudo
ASSERT retry_delays.length >= 5

# For each retry, verify retryIn is within the expected range:
# retryIn = disconnectedRetryTimeout * backoff(n) * jitter
# where jitter is in [0.8, 1.0]

# Retry 1: backoff = 1.0, range = [2000*0.8, 2000*1.0] = [1600, 2000]
ASSERT retry_delays[0] >= disconnected_retry_timeout * 1.0 * 0.8
ASSERT retry_delays[0] <= disconnected_retry_timeout * 1.0 * 1.0

# Retry 2: backoff = 4/3, range = [2000*4/3*0.8, 2000*4/3*1.0] = [2133, 2667]
ASSERT retry_delays[1] >= disconnected_retry_timeout * (4.0/3.0) * 0.8
ASSERT retry_delays[1] <= disconnected_retry_timeout * (4.0/3.0) * 1.0

# Retry 3: backoff = 5/3, range = [2000*5/3*0.8, 2000*5/3*1.0] = [2667, 3333]
ASSERT retry_delays[2] >= disconnected_retry_timeout * (5.0/3.0) * 0.8
ASSERT retry_delays[2] <= disconnected_retry_timeout * (5.0/3.0) * 1.0

# Retry 4+: backoff = 2.0 (capped), range = [2000*2*0.8, 2000*2*1.0] = [3200, 4000]
ASSERT retry_delays[3] >= disconnected_retry_timeout * 2.0 * 0.8
ASSERT retry_delays[3] <= disconnected_retry_timeout * 2.0 * 1.0

ASSERT retry_delays[4] >= disconnected_retry_timeout * 2.0 * 0.8
ASSERT retry_delays[4] <= disconnected_retry_timeout * 2.0 * 1.0

# Verify the delays are monotonically non-decreasing (on average),
# accounting for jitter. The max of retry n should be <= max of retry n+1
# when backoff is increasing.
CLOSE_CLIENT(client)
```

---

## RTB1 - Combined retry delay for SUSPENDED channels

| Spec | Requirement |
|------|-------------|
| RTB1 | Retry delay = channelRetryTimeout * backoff coefficient * jitter coefficient |
| RTB1a | Backoff coefficient = min((n+2)/3, 2) |
| RTB1b | Jitter coefficient is between 0.8 and 1.0 |

Tests that the retry delay reported in ChannelStateChange.retryIn falls within the expected range for successive SUSPENDED channel re-attach attempts, computed as `channelRetryTimeout * backoff * jitter`.

### Setup

```pseudo
channel_name = "test-RTB1-channel-${random_id()}"
connection_attempt_count = 0
retry_delays = []
attach_count = 0

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id",
      connectionKey: "connection-key",
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key",
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  },
  onMessage: (msg) => {
    IF msg.action == ATTACH:
      attach_count++
      IF attach_count == 1:
        # First attach succeeds
        mock_ws.active_connection.send_to_client(ProtocolMessage(
          action: ATTACHED,
          channel: msg.channel,
          flags: 0
        ))
      ELSE:
        # All subsequent re-attach attempts fail with DETACHED
        # (per RTL13b, this triggers SUSPENDED state)
        mock_ws.active_connection.send_to_client(ProtocolMessage(
          action: DETACHED,
          channel: msg.channel,
          error: ErrorInfo(
            code: 90001,
            statusCode: 500,
            message: "Channel re-attach failed"
          )
        ))
  }
)
install_mock(mock_ws)

channel_retry_timeout = 3000  # 3 seconds

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  channelRetryTimeout: channel_retry_timeout,
  autoConnect: false,
  useBinaryProtocol: false
))
```

### Test Steps

```pseudo
enable_fake_timers()

client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

channel = client.channels.get(channel_name)

# Capture retryIn from SUSPENDED state changes
channel.on((change) => {
  IF change.current == ChannelState.suspended:
    retry_delays.append(change.retryIn)
})

# Initial attach succeeds
channel.attach()
AWAIT_STATE channel.state == ChannelState.attached

# Server sends ERROR on the channel, triggering re-attach (RTL13b).
# The re-attach will fail (DETACHED response), causing SUSPENDED state.
mock_ws.active_connection.send_to_client(ProtocolMessage(
  action: ERROR,
  channel: channel_name,
  error: ErrorInfo(
    code: 90001,
    statusCode: 500,
    message: "Channel error"
  )
))

# Advance time in increments to allow multiple SUSPENDED -> ATTACHING cycles.
# Each re-attach fails, producing another SUSPENDED with retryIn.
LOOP up to 30 times:
  ADVANCE_TIME(7000)
  IF retry_delays.length >= 4:
    BREAK
```

### Assertions

```pseudo
ASSERT retry_delays.length >= 4

# Retry 1: backoff = 1.0, range = [3000*0.8, 3000*1.0] = [2400, 3000]
ASSERT retry_delays[0] >= channel_retry_timeout * 1.0 * 0.8
ASSERT retry_delays[0] <= channel_retry_timeout * 1.0 * 1.0

# Retry 2: backoff = 4/3, range = [3000*4/3*0.8, 3000*4/3*1.0] = [3200, 4000]
ASSERT retry_delays[1] >= channel_retry_timeout * (4.0/3.0) * 0.8
ASSERT retry_delays[1] <= channel_retry_timeout * (4.0/3.0) * 1.0

# Retry 3: backoff = 5/3, range = [3000*5/3*0.8, 3000*5/3*1.0] = [4000, 5000]
ASSERT retry_delays[2] >= channel_retry_timeout * (5.0/3.0) * 0.8
ASSERT retry_delays[2] <= channel_retry_timeout * (5.0/3.0) * 1.0

# Retry 4: backoff = 2.0 (capped), range = [3000*2*0.8, 3000*2*1.0] = [4800, 6000]
ASSERT retry_delays[3] >= channel_retry_timeout * 2.0 * 0.8
ASSERT retry_delays[3] <= channel_retry_timeout * 2.0 * 1.0

CLOSE_CLIENT(client)
```

---

## Implementation Notes

### Testing the Backoff/Jitter Functions

The first two tests (RTB1a and RTB1b) verify the underlying calculation functions in isolation. Implementations should expose or have testable access to:

- A backoff coefficient function that takes the retry count and returns the coefficient
- A jitter coefficient function/generator

If these functions are private, implementations may test them indirectly through the full retry delay tests (the RTB1 tests), or use language-specific mechanisms to access internal functions (e.g., `@visibleForTesting` in Dart).

### Jitter Seeding

For deterministic tests of the full retry delay (RTB1), implementations may optionally seed or mock the random number generator used for jitter. However, the range-based assertions (`>= min, <= max`) should work without mocking since they account for the full jitter range.
