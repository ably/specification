# PushDeviceRegistrations Tests

Spec points: `RSH1b`, `RSH1b1`, `RSH1b2`, `RSH1b3`, `RSH1b4`, `RSH1b5`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

See `uts/test/rest/unit/helpers/mock_http.md` for the full Mock HTTP Infrastructure specification.

---

## RSH1b1 — get returns DeviceDetails for known device

**Spec requirement:** RSH1b1 — `#get(deviceId)` performs a request to `/push/deviceRegistrations/:deviceId` and returns a `DeviceDetails` object.

Tests that `get()` sends a GET request with the correct path and returns a parsed `DeviceDetails`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "id": "device-001",
      "clientId": "client-abc",
      "formFactor": "phone",
      "platform": "ios",
      "metadata": { "model": "iPhone 14" },
      "push": {
        "recipient": { "transportType": "apns", "deviceToken": "token-123" },
        "state": "Active"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
device = AWAIT client.push.admin.deviceRegistrations.get("device-001")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component("device-001")

ASSERT device IS DeviceDetails
ASSERT device.id == "device-001"
ASSERT device.clientId == "client-abc"
ASSERT device.formFactor == "phone"
ASSERT device.platform == "ios"
ASSERT device.metadata["model"] == "iPhone 14"
ASSERT device.push.recipient["transportType"] == "apns"
ASSERT device.push.state == "Active"
```

---

## RSH1b1 — get returns error for unknown device

**Spec requirement:** RSH1b1 — Results in a not found error if the device cannot be found.

Tests that `get()` propagates a 404 error when the device does not exist.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(404, {
      "error": {
        "code": 40400,
        "statusCode": 404,
        "message": "Device not found"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
AWAIT client.push.admin.deviceRegistrations.get("nonexistent-device") FAILS WITH error
ASSERT error.code == 40400
ASSERT error.statusCode == 404
```

---

## RSH1b1 — get URL-encodes deviceId

**Spec requirement:** RSH1b1 — `#get(deviceId)` performs a request to `/push/deviceRegistrations/:deviceId`.

Tests that the deviceId is properly URL-encoded in the request path.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "id": "device/with special:chars",
      "platform": "ios",
      "formFactor": "phone",
      "push": {
        "recipient": {},
        "state": "Active"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.deviceRegistrations.get("device/with special:chars")
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.path == "/push/deviceRegistrations/" + encode_uri_component("device/with special:chars")
```

---

## RSH1b2 — list returns paginated DeviceDetails filtered by deviceId

**Spec requirement:** RSH1b2 — `#list(params)` performs a request to `/push/deviceRegistrations` and returns a paginated result with `DeviceDetails` objects filtered by the provided params.

Tests that `list()` sends a GET with `deviceId` filter and returns a `PaginatedResult<DeviceDetails>`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "id": "device-001",
        "clientId": "client-abc",
        "platform": "ios",
        "formFactor": "phone",
        "push": { "recipient": {}, "state": "Active" }
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.deviceRegistrations.list({"deviceId": "device-001"})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "GET"
ASSERT request.url.path == "/push/deviceRegistrations"
ASSERT request.url.queryParams["deviceId"] == "device-001"

ASSERT result IS PaginatedResult
ASSERT result.items.length == 1
ASSERT result.items[0] IS DeviceDetails
ASSERT result.items[0].id == "device-001"
```

---

## RSH1b2 — list returns paginated DeviceDetails filtered by clientId

**Spec requirement:** RSH1b2 — A test should exist filtering by `clientId`.

Tests that `list()` sends a GET with `clientId` filter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "id": "device-001",
        "clientId": "client-abc",
        "platform": "ios",
        "formFactor": "phone",
        "push": { "recipient": {}, "state": "Active" }
      },
      {
        "id": "device-002",
        "clientId": "client-abc",
        "platform": "android",
        "formFactor": "tablet",
        "push": { "recipient": {}, "state": "Active" }
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.deviceRegistrations.list({"clientId": "client-abc"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.queryParams["clientId"] == "client-abc"
ASSERT result.items.length == 2
ASSERT result.items[0].clientId == "client-abc"
ASSERT result.items[1].clientId == "client-abc"
```

---

## RSH1b2 — list supports limit for pagination

**Spec requirement:** RSH1b2 — A test should exist controlling the pagination with the `limit` attribute.

Tests that `list()` forwards the `limit` parameter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, [
      {
        "id": "device-001",
        "platform": "ios",
        "formFactor": "phone",
        "push": { "recipient": {}, "state": "Active" }
      }
    ])
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
result = AWAIT client.push.admin.deviceRegistrations.list({"limit": "2"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].url.queryParams["limit"] == "2"
```

---

## RSH1b3 — save issues PUT with DeviceDetails

**Spec requirement:** RSH1b3 — `#save(device)` issues a `PUT` request to `/push/deviceRegistrations/:deviceId` using the `DeviceDetails` object argument.

Tests that `save()` sends a PUT with the device details in the body and returns the saved `DeviceDetails`.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, {
      "id": "device-001",
      "clientId": "client-abc",
      "platform": "ios",
      "formFactor": "phone",
      "metadata": {},
      "push": {
        "recipient": { "transportType": "apns", "deviceToken": "token-123" },
        "state": "Active"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
device = DeviceDetails(
  id: "device-001",
  clientId: "client-abc",
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "token-123" }
  )
)

result = AWAIT client.push.admin.deviceRegistrations.save(device)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "PUT"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component("device-001")

body = parse_json(request.body)
ASSERT body["id"] == "device-001"
ASSERT body["clientId"] == "client-abc"
ASSERT body["platform"] == "ios"
ASSERT body["formFactor"] == "phone"
ASSERT body["push"]["recipient"]["transportType"] == "apns"

ASSERT result IS DeviceDetails
ASSERT result.id == "device-001"
ASSERT result.push.state == "Active"
```

---

## RSH1b3 — save updates existing device

**Spec requirement:** RSH1b3 — A test should exist for a successful subsequent save with an update.

Tests that `save()` can update an already-registered device.

### Setup
```pseudo
request_count = 0

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    request_count++
    IF request_count == 1:
      # First save — initial registration
      req.respond_with(200, {
        "id": "device-001",
        "platform": "ios",
        "formFactor": "phone",
        "push": {
          "recipient": { "transportType": "apns", "deviceToken": "token-old" },
          "state": "Active"
        }
      })
    ELSE:
      # Second save — update
      req.respond_with(200, {
        "id": "device-001",
        "platform": "ios",
        "formFactor": "phone",
        "push": {
          "recipient": { "transportType": "apns", "deviceToken": "token-new" },
          "state": "Active"
        }
      })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
device = DeviceDetails(
  id: "device-001",
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "token-old" }
  )
)

result1 = AWAIT client.push.admin.deviceRegistrations.save(device)

updated_device = DeviceDetails(
  id: "device-001",
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(
    recipient: { "transportType": "apns", "deviceToken": "token-new" }
  )
)

result2 = AWAIT client.push.admin.deviceRegistrations.save(updated_device)
```

### Assertions
```pseudo
ASSERT result1.push.recipient["deviceToken"] == "token-old"
ASSERT result2.push.recipient["deviceToken"] == "token-new"
ASSERT request_count == 2
```

---

## RSH1b3 — save propagates server error

**Spec requirement:** RSH1b3 — A test should exist for a failed save operation.

Tests that a server error during save is propagated to the caller.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(400, {
      "error": {
        "code": 40000,
        "statusCode": 400,
        "message": "Invalid device details"
      }
    })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
device = DeviceDetails(
  id: "device-001",
  platform: "ios",
  formFactor: "phone",
  push: DevicePushDetails(recipient: {})
)

AWAIT client.push.admin.deviceRegistrations.save(device) FAILS WITH error
ASSERT error.code == 40000
ASSERT error.statusCode == 400
```

---

## RSH1b4 — remove issues DELETE for device

**Spec requirement:** RSH1b4 — `#remove(deviceId)` issues a `DELETE` request to `/push/deviceRegistrations/:deviceId`.

Tests that `remove()` sends a DELETE request with the correct path.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.deviceRegistrations.remove("device-001")
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/deviceRegistrations/" + encode_uri_component("device-001")
```

---

## RSH1b4 — remove succeeds for nonexistent device

**Spec requirement:** RSH1b4 — A test should exist that deletes a device that does not exist but still succeeds.

Tests that removing a nonexistent device does not throw an error.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
# Should not throw — server returns success even for nonexistent devices
AWAIT client.push.admin.deviceRegistrations.remove("nonexistent-device")
```

---

## RSH1b5 — removeWhere issues DELETE with clientId param

**Spec requirement:** RSH1b5 — `#removeWhere(params)` issues a `DELETE` request to `/push/deviceRegistrations` and deletes the registered devices matching the provided `params`.

Tests that `removeWhere()` sends a DELETE with `clientId` as a query parameter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.deviceRegistrations.removeWhere({"clientId": "client-abc"})
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "DELETE"
ASSERT request.url.path == "/push/deviceRegistrations"
ASSERT request.url.queryParams["clientId"] == "client-abc"
```

---

## RSH1b5 — removeWhere issues DELETE with deviceId param

**Spec requirement:** RSH1b5 — A test should exist that deletes devices by `deviceId`.

Tests that `removeWhere()` sends a DELETE with `deviceId` as a query parameter.

### Setup
```pseudo
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps
```pseudo
AWAIT client.push.admin.deviceRegistrations.removeWhere({"deviceId": "device-001"})
```

### Assertions
```pseudo
ASSERT captured_requests[0].method == "DELETE"
ASSERT captured_requests[0].url.path == "/push/deviceRegistrations"
ASSERT captured_requests[0].url.queryParams["deviceId"] == "device-001"
```

---

## RSH1b5 — removeWhere succeeds with no matching devices

**Spec requirement:** RSH1b5 — A test should exist that issues a delete for devices with no matching params and checks the operation still succeeds.

Tests that `removeWhere()` succeeds even when no devices match the params.

### Setup
```pseudo
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(204, null)
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
```

### Test Steps and Assertions
```pseudo
# Should not throw — server returns success even with no matching devices
AWAIT client.push.admin.deviceRegistrations.removeWhere({"clientId": "nonexistent-client"})
```
