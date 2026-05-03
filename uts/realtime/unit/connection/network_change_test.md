# Network Change Tests (RTN20)

Spec points: `RTN20`, `RTN20a`, `RTN20b`, `RTN20c`

## Test Type
Unit test with mocked WebSocket client

## Mock WebSocket Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.

## Platform Network Connectivity Listener

> **Implementation requirement:** These tests require an abstract network connectivity
> listener interface that can be mocked in tests. The Ably spec (RTN20) states "when
> the client library can subscribe to OS events for network/internet connectivity
> changes" -- this means implementations need a platform-specific abstraction that:
>
> 1. Provides a way for the Ably client to subscribe to network connectivity change events
> 2. Can be injected or replaced in tests with a mock that allows programmatic triggering
>    of "network available" and "network unavailable" events
>
> Example mock interface:
> ```pseudo
> interface MockNetworkListener:
>   simulate_network_lost()      # Triggers "internet connection no longer available"
>   simulate_network_available() # Triggers "internet connection now available"
> ```
>
> The mock should be installed before creating the Realtime client, typically via
> dependency injection or a platform-specific test hook.

## Overview

RTN20 defines how the client should respond to OS-level network connectivity change events:

- **RTN20a**: Network loss while CONNECTED or CONNECTING triggers immediate DISCONNECTED
- **RTN20b**: Network available while DISCONNECTED or SUSPENDED triggers immediate connect attempt
- **RTN20c**: Network available while CONNECTING restarts the pending connection attempt

### Verifying Transient States

These tests use the record-and-verify pattern for state transitions. Network change events may trigger rapid state transitions, so we record all state changes and verify the sequence at the end rather than trying to observe intermediate states.

---

## RTN20a - Network loss while CONNECTED triggers immediate DISCONNECTED transition

| Spec | Requirement |
|------|-------------|
| RTN20 | When the client library can subscribe to OS events for network/internet connectivity changes |
| RTN20a | When CONNECTED, if the OS indicates that the underlying internet connection is no longer available, the client should immediately transition to DISCONNECTED with an appropriate reason |

Tests that losing network connectivity while in the CONNECTED state causes an immediate transition to DISCONNECTED, which then triggers automatic reconnection per RTN15.

### Setup

```pseudo
connection_attempt_count = 0
state_changes = []

mock_network = MockNetworkListener()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    conn.respond_with_success(ProtocolMessage(
      action: CONNECTED,
      connectionId: "connection-id-" + connection_attempt_count,
      connectionKey: "connection-key-" + connection_attempt_count,
      connectionDetails: ConnectionDetails(
        connectionKey: "connection-key-" + connection_attempt_count,
        maxIdleInterval: 15000,
        connectionStateTtl: 120000
      )
    ))
  }
)
install_mock(mock_ws)
install_mock(mock_network)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))

# Record all state changes
client.connection.on((change) => {
  state_changes.append({
    current: change.current,
    previous: change.previous,
    reason: change.reason
  })
})
```

### Test Steps

```pseudo
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

ASSERT connection_attempt_count == 1

# Simulate OS reporting network loss
mock_network.simulate_network_lost()

# The client should transition to DISCONNECTED and then automatically
# attempt to reconnect (per RTN15). Wait for the full cycle to complete.
# The reconnection may succeed immediately since the mock WebSocket
# always accepts connections.
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Verify the state change sequence includes DISCONNECTED transition
ASSERT state_changes CONTAINS_IN_ORDER [
  { current: ConnectionState.connecting },
  { current: ConnectionState.connected },
  { current: ConnectionState.disconnected },
  { current: ConnectionState.connecting },
  { current: ConnectionState.connected }
]

# Verify the DISCONNECTED state change has an appropriate reason
disconnected_change = state_changes.find(s => s.current == ConnectionState.disconnected)
ASSERT disconnected_change.reason IS NOT null

# Verify reconnection happened
ASSERT connection_attempt_count == 2

CLOSE_CLIENT(client)
```

---

## RTN20a - Network loss while CONNECTING triggers DISCONNECTED transition

| Spec | Requirement |
|------|-------------|
| RTN20 | When the client library can subscribe to OS events for network/internet connectivity changes |
| RTN20a | When CONNECTING, if the OS indicates that the underlying internet connection is no longer available, the client should immediately transition to DISCONNECTED |

Tests that losing network connectivity while in the CONNECTING state (before the WebSocket connection completes) causes an immediate transition to DISCONNECTED.

### Setup

```pseudo
connection_attempt_count = 0
state_changes = []

mock_network = MockNetworkListener()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    IF connection_attempt_count == 1:
      # First attempt: don't respond yet - leave in CONNECTING state.
      # The network loss event will fire while we're still connecting.
      # Do NOT call respond_with_success() here.
    ELSE:
      # Subsequent attempts succeed
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
  }
)
install_mock(mock_ws)
install_mock(mock_network)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))

# Record all state changes
client.connection.on((change) => {
  state_changes.append(change.current)
})
```

### Test Steps

```pseudo
# Start connecting - the mock won't respond, so we stay in CONNECTING
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

# Simulate OS reporting network loss while still CONNECTING
mock_network.simulate_network_lost()

# Client should transition to DISCONNECTED, then eventually reconnect
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Verify the state change sequence
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# The first connection attempt was abandoned, second succeeded
ASSERT connection_attempt_count >= 2

CLOSE_CLIENT(client)
```

---

## RTN20b - Network available while DISCONNECTED triggers immediate connect attempt

| Spec | Requirement |
|------|-------------|
| RTN20 | When the client library can subscribe to OS events for network/internet connectivity changes |
| RTN20b | When DISCONNECTED, if the OS indicates that the underlying internet connection is now available, the client should immediately attempt to connect |

Tests that a network-available event while in the DISCONNECTED state triggers an immediate connection attempt, rather than waiting for the scheduled retry timer.

### Setup

```pseudo
connection_attempt_count = 0
state_changes = []

mock_network = MockNetworkListener()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    IF connection_attempt_count == 1:
      # First connection succeeds
      conn.respond_with_success(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-id-1",
        connectionKey: "connection-key-1",
        connectionDetails: ConnectionDetails(
          connectionKey: "connection-key-1",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
    ELSE IF connection_attempt_count == 2:
      # Second attempt (after disconnect) fails - puts client in DISCONNECTED
      conn.respond_with_refused()
    ELSE:
      # Third attempt (triggered by network available) succeeds
      conn.respond_with_success(ProtocolMessage(
        action: CONNECTED,
        connectionId: "connection-id-2",
        connectionKey: "connection-key-2",
        connectionDetails: ConnectionDetails(
          connectionKey: "connection-key-2",
          maxIdleInterval: 15000,
          connectionStateTtl: 120000
        )
      ))
  }
)
install_mock(mock_ws)
install_mock(mock_network)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  disconnectedRetryTimeout: 30000,  # 30 seconds - deliberately long
  autoConnect: false,
  useBinaryProtocol: false
))

# Record all state changes
client.connection.on((change) => {
  state_changes.append(change.current)
})
```

### Test Steps

```pseudo
enable_fake_timers()

# Connect successfully
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connected

# Force disconnect - the reconnection attempt will fail (respond_with_refused),
# putting the client into DISCONNECTED state with a 30-second retry timer.
ws_connection = mock_ws.events.find(e => e.type == CONNECTION_SUCCESS).connection
ws_connection.simulate_disconnect()

# Wait for the client to reach DISCONNECTED after the failed reconnection
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds

# Record the connection attempt count before network event
attempts_before = connection_attempt_count

# Simulate OS reporting network is now available.
# This should trigger an IMMEDIATE connection attempt, bypassing the
# 30-second disconnectedRetryTimeout.
mock_network.simulate_network_available()

# Should connect immediately without needing to advance time
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 5 seconds
```

### Assertions

```pseudo
# Verify the state change sequence
ASSERT state_changes CONTAINS_IN_ORDER [
  ConnectionState.connecting,
  ConnectionState.connected,
  ConnectionState.disconnected,
  ConnectionState.connecting,
  ConnectionState.connected
]

# A new connection attempt was made immediately after network available event
ASSERT connection_attempt_count > attempts_before

# Successfully reconnected
ASSERT client.connection.state == ConnectionState.connected

CLOSE_CLIENT(client)
```

> **Implementation note:** The key assertion here is that reconnection happens without
> advancing fake timers past the 30-second `disconnectedRetryTimeout`. If the network
> available event did NOT trigger an immediate attempt, the client would remain
> DISCONNECTED until the 30-second timer fires. The fact that we reach CONNECTED
> without advancing time proves the network event bypassed the retry timer.

---

## RTN20c - Network available while CONNECTING restarts the connection attempt

| Spec | Requirement |
|------|-------------|
| RTN20 | When the client library can subscribe to OS events for network/internet connectivity changes |
| RTN20c | When CONNECTING, if the OS indicates that the underlying internet connection is now available, the client should restart the pending connection attempt |

Tests that a network-available event while in the CONNECTING state causes the client to restart (abandon and retry) the pending connection attempt.

### Setup

```pseudo
connection_attempt_count = 0
state_changes = []

mock_network = MockNetworkListener()

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempt_count++
    IF connection_attempt_count == 1:
      # First attempt: don't respond - leave pending (simulates slow connection)
      # The network-available event will fire while this attempt is pending.
    ELSE:
      # Second attempt (restarted after network event) succeeds
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
  }
)
install_mock(mock_ws)
install_mock(mock_network)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false,
  useBinaryProtocol: false
))

# Record all state changes
client.connection.on((change) => {
  state_changes.append(change.current)
})
```

### Test Steps

```pseudo
# Start connecting - the mock won't respond to the first attempt,
# leaving the client in CONNECTING state
client.connect()
AWAIT_STATE client.connection.state == ConnectionState.connecting

ASSERT connection_attempt_count == 1

# Simulate OS reporting network is now available while still CONNECTING.
# The client should abandon the pending connection and start a new attempt.
mock_network.simulate_network_available()

# The restarted connection attempt should succeed
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# The first connection attempt was abandoned and a new one was made
ASSERT connection_attempt_count >= 2

# Client is now connected
ASSERT client.connection.state == ConnectionState.connected

CLOSE_CLIENT(client)
```

> **Implementation note:** Some implementations may briefly transition through
> DISCONNECTED when restarting the connection attempt (abandon old attempt -> 
> DISCONNECTED -> CONNECTING -> CONNECTED). Others may stay in CONNECTING and
> simply restart the underlying transport. Both approaches satisfy RTN20c.
> The state change assertions use `CONTAINS_IN_ORDER` with minimal requirements
> to accommodate either approach.

---

## Implementation Notes

### Network Connectivity Abstraction

Each platform has different mechanisms for observing network connectivity changes:

| Platform | Mechanism |
|----------|-----------|
| **iOS/macOS** | `NWPathMonitor` (Network framework) or `SCNetworkReachability` |
| **Android** | `ConnectivityManager.NetworkCallback` |
| **Dart/Flutter** | `connectivity_plus` package or platform channels |
| **JavaScript (Browser)** | `navigator.onLine` + `online`/`offline` events on `window` |
| **JavaScript (Node.js)** | Not typically available - RTN20 may not apply |
| **Python** | Not typically available - RTN20 may not apply |

The mock used in these tests should be injected via the same mechanism the SDK uses to receive real network events. For example, if the SDK accepts a `NetworkConnectivityListener` interface in its constructor or options, the mock should implement that interface.

### RTN20 Conditionality

RTN20 begins with "When the client library can subscribe to OS events" -- this means the feature is optional for platforms where network monitoring is not feasible. SDKs that do not implement network monitoring should skip these tests entirely.

### Timer Interaction (RTN20b)

When the client is in DISCONNECTED state, there is typically a retry timer scheduled (per RTB1). When a network-available event triggers an immediate connection attempt (RTN20b), implementations should cancel the pending retry timer to avoid a duplicate connection attempt.
