# REST Channel Attributes and Methods

Spec points: `RSL7`, `RSL8`, `RSL8a`, `RSL9`, `CHD2`, `CHD2a`, `CHD2b`, `CHS2`, `CHS2a`, `CHS2b`, `CHO2`, `CHO2a`, `CHM2`, `CHM2a`, `CHM2b`, `CHM2c`, `CHM2d`, `CHM2e`, `CHM2f`, `CHM2g`, `CHM2h`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSL9 - RestChannel name attribute

**Spec requirement:** `RestChannel#name` attribute is a string containing the channel's name.

Tests that the channel name attribute returns the name used when getting the channel.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))
```

### Assertions
```pseudo
channel = client.channels.get("my-channel")
ASSERT channel.name == "my-channel"

# Also works with special characters
channel2 = client.channels.get("namespace:channel-name")
ASSERT channel2.name == "namespace:channel-name"
```

---

## RSL7 - setOptions updates channel options

**Spec requirement:** `RestChannel#setOptions` takes a `ChannelOptions` object and sets or updates the stored channel options, then indicates success.

Tests that setOptions updates the stored channel options.

### Setup
```pseudo
client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-RSL7")
```

### Test Steps
```pseudo
AWAIT channel.setOptions(RestChannelOptions())
```

### Assertions
```pseudo
# setOptions completes without error (indicates success)
# No exception thrown
```

---

## RSL7 - setOptions stores new options

**Spec requirement:** `RestChannel#setOptions` sets or updates the stored channel options.

Tests that options set via setOptions are retained and accessible.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, [])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-RSL7-store")
```

### Test Steps
```pseudo
# Set options — the effect of channel options is primarily on encryption
# (RSL5) which is not yet implemented. For now, verify the call succeeds
# and options are stored by observing they can be set without error.
AWAIT channel.setOptions(RestChannelOptions())
```

### Assertions
```pseudo
# setOptions completes without error
# Implementation note: once encryption is supported (RSL5), this test
# should verify that cipher params set via setOptions are applied to
# subsequent publish/history operations.
```

---

## RSL8 - status makes GET request to correct endpoint

**Spec requirement:** `RestChannel#status` function makes an HTTP GET request to `<restHost>/channels/<channelId>`.

Tests that calling status() sends a GET request to the correct URL path.

### Setup
```pseudo
captured_request = null

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_request = req
    req.respond_with(200, {
      "channelId": "test-RSL8",
      "status": {
        "isActive": true,
        "occupancy": {
          "metrics": {
            "connections": 0,
            "publishers": 0,
            "subscribers": 0,
            "presenceConnections": 0,
            "presenceMembers": 0,
            "presenceSubscribers": 0
          }
        }
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-RSL8")
```

### Test Steps
```pseudo
result = AWAIT channel.status()
```

### Assertions
```pseudo
# Correct HTTP method and path
ASSERT captured_request IS NOT null
ASSERT captured_request.method == "GET"
ASSERT captured_request.url.path ENDS_WITH "/channels/test-RSL8"
```

---

## RSL8 - status with special characters in channel name

**Spec requirement:** The channel ID in the URL must be properly encoded.

Tests that channel names with special characters are URL-encoded in the status request.

### Setup
```pseudo
captured_request = null

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_request = req
    req.respond_with(200, {
      "channelId": "namespace:my channel",
      "status": {
        "isActive": true,
        "occupancy": {
          "metrics": {
            "connections": 0,
            "publishers": 0,
            "subscribers": 0,
            "presenceConnections": 0,
            "presenceMembers": 0,
            "presenceSubscribers": 0
          }
        }
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("namespace:my channel")
```

### Test Steps
```pseudo
result = AWAIT channel.status()
```

### Assertions
```pseudo
ASSERT captured_request IS NOT null
ASSERT captured_request.method == "GET"
# Channel name must be URI-encoded in the path
ASSERT captured_request.url.path ENDS_WITH "/channels/" + encode_uri_component("namespace:my channel")
```

---

## RSL8a - status returns ChannelDetails object

**Spec requirement:** `RestChannel#status` returns a `ChannelDetails` object.

Tests that the status() response is parsed into a ChannelDetails object with correct attributes.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "channelId": "test-RSL8a",
      "status": {
        "isActive": true,
        "occupancy": {
          "metrics": {
            "connections": 5,
            "publishers": 2,
            "subscribers": 3,
            "presenceConnections": 1,
            "presenceMembers": 1,
            "presenceSubscribers": 0
          }
        }
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-RSL8a")
```

### Test Steps
```pseudo
result = AWAIT channel.status()
```

### Assertions
```pseudo
# Result is a ChannelDetails object (CHD1)
ASSERT result IS ChannelDetails

# CHD2a: channelId attribute
ASSERT result.channelId == "test-RSL8a"

# CHD2b: status attribute is a ChannelStatus (CHS1)
ASSERT result.status IS NOT null
ASSERT result.status.isActive == true

# CHS2b: occupancy metrics
ASSERT result.status.occupancy IS NOT null
ASSERT result.status.occupancy.metrics.connections == 5
ASSERT result.status.occupancy.metrics.publishers == 2
ASSERT result.status.occupancy.metrics.subscribers == 3
```

---

## CHD2, CHS2, CHO2, CHM2 - status() response parses all ChannelMetrics fields

| Spec | Requirement |
|------|-------------|
| CHD2 | ChannelDetails attributes: channelId (CHD2a), status (CHD2b) |
| CHS2 | ChannelStatus attributes: isActive (CHS2a), occupancy (CHS2b) |
| CHO2 | ChannelOccupancy attributes: metrics (CHO2a) |
| CHM2 | ChannelMetrics attributes: connections (CHM2a), presenceConnections (CHM2b), presenceMembers (CHM2c), presenceSubscribers (CHM2d), publishers (CHM2e), subscribers (CHM2f), objectPublishers (CHM2g), objectSubscribers (CHM2h) |

Tests that status() parses the complete set of ChannelMetrics fields from the response, including the newer objectPublishers and objectSubscribers fields.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, {
      "channelId": "test-CHM2-all-fields",
      "status": {
        "isActive": true,
        "occupancy": {
          "metrics": {
            "connections": 10,
            "presenceConnections": 7,
            "presenceMembers": 4,
            "presenceSubscribers": 3,
            "publishers": 6,
            "subscribers": 8,
            "objectPublishers": 2,
            "objectSubscribers": 5
          }
        }
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-CHM2-all-fields")
```

### Test Steps
```pseudo
result = AWAIT channel.status()
```

### Assertions
```pseudo
# CHD2a: channelId
ASSERT result.channelId == "test-CHM2-all-fields"

# CHD2b + CHS2a: status.isActive
ASSERT result.status IS NOT null
ASSERT result.status.isActive == true

# CHS2b + CHO2a: occupancy.metrics
ASSERT result.status.occupancy IS NOT null
ASSERT result.status.occupancy.metrics IS NOT null

metrics = result.status.occupancy.metrics

# CHM2a: connections
ASSERT metrics.connections == 10

# CHM2b: presenceConnections
ASSERT metrics.presenceConnections == 7

# CHM2c: presenceMembers
ASSERT metrics.presenceMembers == 4

# CHM2d: presenceSubscribers
ASSERT metrics.presenceSubscribers == 3

# CHM2e: publishers
ASSERT metrics.publishers == 6

# CHM2f: subscribers
ASSERT metrics.subscribers == 8

# CHM2g: objectPublishers
ASSERT metrics.objectPublishers == 2

# CHM2h: objectSubscribers
ASSERT metrics.objectSubscribers == 5
```

---

## CHM2 - status() response with zero and missing metric fields

**Spec requirement:** ChannelMetrics fields (CHM2a-h) are integers. When the server response contains zero values or omits newer fields, the parsed result should default missing fields to 0.

Tests that status() handles zero-valued and absent metric fields gracefully, defaulting missing fields to 0.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    # Response omits objectPublishers and objectSubscribers (CHM2g, CHM2h)
    # to simulate an older server that does not include these fields.
    # All other metrics are explicitly zero.
    req.respond_with(200, {
      "channelId": "test-CHM2-defaults",
      "status": {
        "isActive": false,
        "occupancy": {
          "metrics": {
            "connections": 0,
            "presenceConnections": 0,
            "presenceMembers": 0,
            "presenceSubscribers": 0,
            "publishers": 0,
            "subscribers": 0
          }
        }
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret"
))

channel = client.channels.get("test-CHM2-defaults")
```

### Test Steps
```pseudo
result = AWAIT channel.status()
```

### Assertions
```pseudo
# CHD2a: channelId
ASSERT result.channelId == "test-CHM2-defaults"

# CHS2a: isActive can be false
ASSERT result.status.isActive == false

metrics = result.status.occupancy.metrics

# CHM2a-f: explicit zero values are parsed correctly
ASSERT metrics.connections == 0
ASSERT metrics.presenceConnections == 0
ASSERT metrics.presenceMembers == 0
ASSERT metrics.presenceSubscribers == 0
ASSERT metrics.publishers == 0
ASSERT metrics.subscribers == 0

# CHM2g-h: missing fields default to 0
ASSERT metrics.objectPublishers == 0
ASSERT metrics.objectSubscribers == 0
```
