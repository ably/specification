# Fallback Hosts Tests (RTN17)

Spec points: `RTN17`, `RTN17e`, `RTN17f`, `RTN17f1`, `RTN17g`, `RTN17h`, `RTN17i`, `RTN17j`

## Test Type
Unit test with mocked WebSocket client and HTTP client

## Mock Infrastructure

See `uts/test/realtime/unit/helpers/mock_websocket.md` for the full Mock WebSocket Infrastructure specification.
See `uts/test/rest/unit/helpers/mock_http.md` for Mock HTTP Client specification.

---

## RTN17i - Always prefer primary domain first

**Spec requirement:** By default, every connection attempt is first attempted to the primary domain. The client library must always prefer the primary domain, even if a previous connection attempt to that endpoint has failed.

Tests that the client always tries the primary domain first, even after failures.

### Setup

```pseudo
channel_name = "test-RTN17i-${random_id()}"
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    # Record which host was attempted
    connection_attempts.push({
      host: conn.url.host,
      attempt_number: connection_attempts.length + 1
    })
    
    IF connection_attempts.length == 1:
      # First attempt (to primary): fail
      conn.respond_with_refused()
    ELSE IF connection_attempts.length == 2:
      # Second attempt (to fallback): succeed
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# First connection attempt
client.connect()

# Wait for successful connection (after trying primary then fallback)
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

# Now force a disconnection
mock_ws.active_connection.close()

# Wait for DISCONNECTED
AWAIT_STATE client.connection.state == ConnectionState.disconnected
  WITH timeout: 5 seconds

# Clear previous attempts
connection_attempts.clear()

# Allow next connection to primary to succeed
mock_ws.onConnectionAttempt = (conn) => {
  connection_attempts.push({
    host: conn.url.host,
    attempt_number: connection_attempts.length + 1
  })
  conn.respond_with_success()
  conn.send_to_client(ProtocolMessage(
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

# Wait for automatic reconnection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# The reconnection attempt should have tried primary domain first
ASSERT connection_attempts.length >= 1
ASSERT connection_attempts[0].host == "realtime.ably.io"
  OR connection_attempts[0].host CONTAINS "realtime.ably"  # Primary domain
```

---

## RTN17f - Errors that necessitate fallback host usage

**Spec requirement:** Errors that necessitate use of an alternative host include conditions specified in RSC15l and also DISCONNECTED responses with error.statusCode in range 500-504.

Tests that specific error conditions trigger fallback host usage.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    
    IF connection_attempts.length == 1:
      # Primary domain: unresolvable (simulated)
      conn.respond_with_error("Host unresolvable")
    ELSE:
      # Fallback domain: succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for successful connection via fallback
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Should have tried at least 2 hosts (primary + fallback)
ASSERT connection_attempts.length >= 2

# First attempt was to primary domain
ASSERT connection_attempts[0] CONTAINS "realtime.ably"

# Second attempt was to a fallback domain
ASSERT connection_attempts[1] CONTAINS "fallback"
```

---

## RTN17f1 - DISCONNECTED with 5xx status triggers fallback

**Spec requirement:** A DISCONNECTED response with an error.statusCode in the range 500 <= code <= 504 necessitates use of an alternative host.

Tests that 5xx errors in DISCONNECTED messages trigger fallback.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    
    IF connection_attempts.length == 1:
      # Primary domain: connect then send DISCONNECTED with 503 and close
      conn.respond_with_success()
      conn.send_to_client_and_close(ProtocolMessage(
        action: DISCONNECTED,
        error: ErrorInfo(
          code: 50003,
          statusCode: 503,
          message: "Service temporarily unavailable"
        )
      ))
    ELSE:
      # Fallback domain: succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for successful connection via fallback
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Should have tried at least 2 hosts
ASSERT connection_attempts.length >= 2

# First was primary, second was fallback
ASSERT connection_attempts[0] CONTAINS "realtime.ably"
ASSERT connection_attempts[1] CONTAINS "fallback"
```

---

## RTN17j - Connectivity check before fallback

**Spec requirement:** In case of an error necessitating fallback, check connectivity by issuing GET to connectivityCheckUrl. If response includes "yes", proceed with fallback hosts in random order.

Tests that connectivity check is performed before trying fallback hosts.

### Setup

```pseudo
channel_name = "test-RTN17j-${random_id()}"
http_requests = []
connection_attempts = []

# Mock HTTP client for connectivity check
mock_http = MockHttpClient(
  onRequest: (req) => {
    http_requests.push({
      url: req.url.toString(),
      method: req.method
    })
    
    IF req.url.toString() CONTAINS "internet-up":
      # Connectivity check succeeds
      req.respond_with(200, "yes", contentType: "text/plain")
    ELSE:
      # Token requests etc
      req.respond_with(200, {
        "token": "test_token",
        "keyName": "appId.keyId",
        "issued": time_now(),
        "expires": time_now() + 3600000,
        "capability": "{\"*\":[\"*\"]}"
      })
  }
)
install_mock(mock_http)

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    
    IF connection_attempts.length == 1:
      # Primary domain fails
      conn.respond_with_timeout()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for successful connection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 15 seconds
```

### Assertions

```pseudo
# Connectivity check should have been performed
connectivity_checks = FILTER http_requests WHERE req.url CONTAINS "internet-up"
ASSERT connectivity_checks.length >= 1

# Connectivity check was a GET request
ASSERT connectivity_checks[0].method == "GET"

# Connection attempts proceeded to fallback after check
ASSERT connection_attempts.length >= 2
```

---

## RTN17g - Empty fallback set results in immediate error

**Spec requirement:** When the set of fallback domains is empty, failing requests that would have qualified for retry should result in an error immediately.

Tests that no fallback is attempted when fallback set is empty.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    # Connection fails
    conn.respond_with_refused()
  }
)
install_mock(mock_ws)

# Use custom endpoint which results in empty fallback set (REC2c2)
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  realtimeHost: "custom.example.com",  # Custom host = no fallbacks
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for DISCONNECTED (should not try fallbacks)
AWAIT_STATE client.connection.state IN [ConnectionState.disconnected, ConnectionState.failed]
  WITH timeout: 5 seconds

# Give it time to potentially try fallbacks (it shouldn't)
WAIT(2000)
```

### Assertions

```pseudo
# Should have only tried the custom host once, no fallbacks
ASSERT connection_attempts.length == 1
ASSERT connection_attempts[0] == "custom.example.com"
```

---

## RTN17h - Fallback domains determined by REC2

**Spec requirement:** When fallbacks apply, the set of fallback domains is determined by REC2.

Tests that correct fallback hosts are used based on configuration.

### Setup

```pseudo
connection_attempts = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    
    IF connection_attempts.length == 1:
      # Primary fails
      conn.respond_with_refused()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

# Use default configuration (should use default fallback hosts)
client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for successful connection
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds
```

### Assertions

```pseudo
# Should have tried primary then fallback
ASSERT connection_attempts.length >= 2

# Second attempt should be a default fallback host
# Default fallback pattern: *.a|b|c|d|e.fallback.ably-realtime.com
fallback_host = connection_attempts[1]
ASSERT fallback_host CONTAINS "fallback.ably-realtime.com"
ASSERT fallback_host MATCHES /\.[abcde]\.fallback\.ably-realtime\.com$/
```

---

## RTN17j - Fallback hosts tried in random order

**Spec requirement:** Retry connection against fallback domains in random order to find an alternative healthy datacenter.

Tests that fallback hosts are not always tried in the same order.

### Setup

```pseudo
# Run multiple test iterations to check randomness
fallback_orders = []

FOR iteration IN [1, 2, 3, 4, 5]:
  connection_attempts = []
  
  mock_ws = MockWebSocket(
    onConnectionAttempt: (conn) => {
      connection_attempts.push(conn.url.host)
      
      IF connection_attempts.length <= 3:
        # Primary and first 2 fallbacks fail
        conn.respond_with_refused()
      ELSE:
        # Third fallback succeeds
        conn.respond_with_success()
        conn.send_to_client(ProtocolMessage(
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
  
  client = Realtime(options: ClientOptions(
    key: "appId.keyId:keySecret",
    autoConnect: false
  ))
  
  client.connect()
  
  AWAIT_STATE client.connection.state == ConnectionState.connected
    WITH timeout: 15 seconds
  
  # Record the order of fallback hosts (skip primary at index 0)
  fallback_order = connection_attempts[1:]
  fallback_orders.push(fallback_order)
  
  await client.close()
```

### Test Steps

```pseudo
# Analyze the collected fallback orders
```

### Assertions

```pseudo
# At least one iteration should have different order than another
# (This is probabilistic - with 5 iterations and 5 fallback hosts, 
# we should see some variation)

unique_orders = COUNT_UNIQUE(fallback_orders)
ASSERT unique_orders >= 2

# Note: This test may occasionally fail due to randomness
# In production, this should use a larger sample size
```

---

## RTN17e - HTTP requests use same fallback host as realtime connection

**Spec requirement:** If the realtime client is connected to a fallback host, HTTP requests should first be attempted to the same datacenter. If the HTTP request fails, follow normal fallback behavior.

Tests that HTTP requests prefer the same host as the active realtime connection.

### Setup

```pseudo
channel_name = "test-RTN17e-${random_id()}"
connection_attempts = []
http_requests = []

mock_ws = MockWebSocket(
  onConnectionAttempt: (conn) => {
    connection_attempts.push(conn.url.host)
    
    IF connection_attempts.length == 1:
      # Primary fails
      conn.respond_with_refused()
    ELSE:
      # Fallback succeeds
      conn.respond_with_success()
      conn.send_to_client(ProtocolMessage(
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

mock_http = MockHttpClient(
  onRequest: (req) => {
    http_requests.push({
      url: req.url.toString(),
      host: req.url.host
    })
    
    # Respond successfully to HTTP requests
    IF req.url.path CONTAINS "/history":
      req.respond_with(200, {
        "items": [],
        "start": 0,
        "end": 0
      })
    ELSE:
      req.respond_with(200, {})
  }
)
install_mock(mock_http)

client = Realtime(options: ClientOptions(
  key: "appId.keyId:keySecret",
  autoConnect: false
))
```

### Test Steps

```pseudo
# Start connection
client.connect()

# Wait for successful connection to fallback
AWAIT_STATE client.connection.state == ConnectionState.connected
  WITH timeout: 10 seconds

# Determine which fallback host we're connected to
connected_fallback_host = connection_attempts[1]

# Make an HTTP request (e.g., channel history)
channel = client.channels.get(channel_name)
await channel.history()

# Wait for HTTP request to complete
WAIT(500)
```

### Assertions

```pseudo
# At least one HTTP request should have been made
history_requests = FILTER http_requests WHERE req.url CONTAINS "/history"
ASSERT history_requests.length >= 1

# HTTP request should have used the same fallback host
# Note: The exact host matching logic may vary by implementation
# Some SDKs may convert WebSocket host to REST host pattern
history_host = history_requests[0].host

# Either:
# A) Exact match
ASSERT history_host == connected_fallback_host

# Or:
# B) Same fallback datacenter (e.g., *.b.fallback.* matches)
ASSERT EXTRACT_FALLBACK_ID(history_host) == EXTRACT_FALLBACK_ID(connected_fallback_host)
```

---

## Implementation Notes

Fallback host behavior involves several complex interactions:

1. **Primary preference (RTN17i)**: Always try primary first, even after previous failures
2. **Error conditions (RTN17f)**: Only specific errors trigger fallback (host unreachable, timeout, 5xx)
3. **Connectivity check (RTN17j)**: Check internet connectivity before blaming Ably
4. **Randomization (RTN17j)**: Use fallbacks in random order to distribute load
5. **Empty fallback set (RTN17g)**: Custom hosts typically have no fallbacks
6. **HTTP coordination (RTN17e)**: REST and realtime should use same datacenter
7. **Configuration (RTN17h)**: Fallback set determined by REC2 rules

Test implementations should verify their SDK correctly implements these behaviors.
