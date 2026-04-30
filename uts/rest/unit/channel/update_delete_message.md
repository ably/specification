# REST Channel UpdateMessage/DeleteMessage/AppendMessage Tests

Spec points: `RSL15`, `RSL15a`, `RSL15b`, `RSL15b1`, `RSL15b7`, `RSL15c`, `RSL15d`, `RSL15e`, `RSL15f`

## Test Type
Unit test with mocked HTTP client

## Mock HTTP Infrastructure

These tests use the mock HTTP infrastructure defined in `uts/test/rest/unit/helpers/mock_http.md`.

---

## RSL15b, RSL15b1 — updateMessage sends PATCH with action MESSAGE_UPDATE

| Spec | Requirement |
|------|-------------|
| RSL15b | The SDK must send a PATCH to `/channels/{channelName}/messages/{serial}` |
| RSL15b1 | `action` set to `MESSAGE_UPDATE` for `updateMessage()` |

Tests that `updateMessage()` sends a PATCH request with the correct action.

### Setup
```pseudo
channel_name = "test-RSL15-update-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.updateMessage(
  Message(serial: "msg-serial-1", name: "updated", data: "new-data")
)
```

### Assertions
```pseudo
ASSERT captured_requests.length == 1

request = captured_requests[0]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1"

body = parse_json(request.body)
ASSERT body["action"] == 1  # MESSAGE_UPDATE numeric value
ASSERT body["name"] == "updated"
ASSERT body["data"] == "new-data"
```

---

## RSL15b, RSL15b1 — deleteMessage sends PATCH with action MESSAGE_DELETE

| Spec | Requirement |
|------|-------------|
| RSL15b | The SDK must send a PATCH to `/channels/{channelName}/messages/{serial}` |
| RSL15b1 | `action` set to `MESSAGE_DELETE` for `deleteMessage()` |

Tests that `deleteMessage()` sends a PATCH request with the correct action.

### Setup
```pseudo
channel_name = "test-RSL15-delete-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.deleteMessage(
  Message(serial: "msg-serial-1")
)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1"

body = parse_json(request.body)
ASSERT body["action"] == 2  # MESSAGE_DELETE numeric value
```

---

## RSL15b, RSL15b1 — appendMessage sends PATCH with action MESSAGE_APPEND

| Spec | Requirement |
|------|-------------|
| RSL15b | The SDK must send a PATCH to `/channels/{channelName}/messages/{serial}` |
| RSL15b1 | `action` set to `MESSAGE_APPEND` for `appendMessage()` |

Tests that `appendMessage()` sends a PATCH request with the correct action.

### Setup
```pseudo
channel_name = "test-RSL15-append-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.appendMessage(
  Message(serial: "msg-serial-1", data: "appended-data")
)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.method == "PATCH"
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/msg-serial-1"

body = parse_json(request.body)
ASSERT body["action"] == 5  # MESSAGE_APPEND numeric value
ASSERT body["data"] == "appended-data"
```

---

## RSL15b7 — version set to MessageOperation when provided

**Spec requirement:** RSL15b7 — `version` is set to the `MessageOperation` object if provided.

Tests that the `version` field in the request body contains the MessageOperation fields.

### Setup
```pseudo
channel_name = "test-RSL15b7-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.updateMessage(
  Message(serial: "s1", data: "updated"),
  operation: MessageOperation(
    clientId: "user1",
    description: "fixed typo",
    metadata: { "reason": "typo" }
  )
)
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
ASSERT "version" IN body
ASSERT body["version"]["clientId"] == "user1"
ASSERT body["version"]["description"] == "fixed typo"
ASSERT body["version"]["metadata"]["reason"] == "typo"
```

---

## RSL15b7 — version absent when no MessageOperation provided

**Spec requirement:** RSL15b7 — `version` is only set when a `MessageOperation` is provided.

Tests that `version` is omitted from the request body when no operation is given.

### Setup
```pseudo
channel_name = "test-RSL15b7-absent-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.updateMessage(
  Message(serial: "s1", data: "updated")
)
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)
ASSERT "version" NOT IN body
```

---

## RSL15c — does not mutate user-supplied Message

**Spec requirement:** RSL15c — The SDK must not mutate the user-supplied `Message` object.

Tests that the original message object is unchanged after calling `updateMessage()`.

### Setup
```pseudo
channel_name = "test-RSL15c-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
original_msg = Message(serial: "s1", name: "orig", data: "original-data")

AWAIT channel.updateMessage(original_msg)
```

### Assertions
```pseudo
# Original message must not have been mutated
ASSERT original_msg.action IS null  # No action was set on original
ASSERT original_msg.name == "orig"
ASSERT original_msg.data == "original-data"

# But the request body should contain the action
body = parse_json(captured_requests[0].body)
ASSERT body["action"] == 1  # MESSAGE_UPDATE
```

---

## RSL15e — returns UpdateDeleteResult on success

| Spec | Requirement |
|------|-------------|
| RSL15e | On success, returns an `UpdateDeleteResult` object |
| UDR2a | `versionSerial` `String?` — the new version serial of the updated/deleted message |

Tests that the response is parsed into an `UpdateDeleteResult`.

### Setup
```pseudo
channel_name = "test-RSL15e-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "versionSerial": "version-serial-abc" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.updateMessage(
  Message(serial: "s1", data: "updated")
)
```

### Assertions
```pseudo
ASSERT result IS UpdateDeleteResult
ASSERT result.versionSerial == "version-serial-abc"
```

---

## RSL15e — UpdateDeleteResult with null versionSerial

**Spec requirement:** UDR2a — `versionSerial` will be null if the message was superseded by a subsequent update before it could be published.

Tests that a null `versionSerial` in the response is preserved.

### Setup
```pseudo
channel_name = "test-RSL15e-null-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "versionSerial": null })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
result = AWAIT channel.updateMessage(
  Message(serial: "s1", data: "updated")
)
```

### Assertions
```pseudo
ASSERT result IS UpdateDeleteResult
ASSERT result.versionSerial IS null
```

---

## RSL15f — params sent as querystring

**Spec requirement:** RSL15f — Any params provided in the third argument must be sent in the querystring, with values stringified.

Tests that optional params are sent as query parameters.

### Setup
```pseudo
channel_name = "test-RSL15f-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.updateMessage(
  Message(serial: "s1", data: "updated"),
  params: { "key": "value", "num": "42" }
)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.query_params["key"] == "value"
ASSERT request.url.query_params["num"] == "42"
```

---

## RSL15a — serial required, throws error if missing

**Spec requirement:** RSL15a — Takes a first argument of a `Message` object which must contain a populated `serial` field.

Tests that calling update/delete/append without a serial in the message throws an error.

### Setup
```pseudo
channel_name = "test-RSL15a-${random_id()}"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps and Assertions
```pseudo
# updateMessage without serial
AWAIT channel.updateMessage(Message(name: "x", data: "y")) FAILS WITH error
ASSERT error.code == 40003

# deleteMessage without serial
AWAIT channel.deleteMessage(Message(name: "x")) FAILS WITH error
ASSERT error.code == 40003

# appendMessage without serial
AWAIT channel.appendMessage(Message(data: "y")) FAILS WITH error
ASSERT error.code == 40003
```

---

## RSL15d — request body encoded per RSL4 (message data encoding)

| Spec | Requirement |
|------|-------------|
| RSL15d | The request body must be encoded to the appropriate format per RSC8 |
| RSL15b | Request body is a `Message` object encoded per RSL4 |

Tests that message data is encoded following the same rules as regular publish.

### Setup
```pseudo
channel_name = "test-RSL15d-${random_id()}"
captured_requests = []

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
# JSON object data should be encoded per RSL4
AWAIT channel.updateMessage(
  Message(serial: "s1", data: { "key": "value" })
)
```

### Assertions
```pseudo
body = parse_json(captured_requests[0].body)

# JSON data should be JSON-encoded as a string with encoding field
ASSERT body["data"] IS String  # JSON-encoded string
ASSERT body["encoding"] == "json"
ASSERT parse_json(body["data"]) == { "key": "value" }
```

---

## RSL15b — serial URL-encoded in path

**Spec requirement:** RSL15b — The serial in the PATCH URL must be properly URL-encoded.

Tests that special characters in the message serial are URL-encoded in the request path.

### Setup
```pseudo
channel_name = "test-RSL15b-encode-${random_id()}"
captured_requests = []
serial_with_special_chars = "serial/special:chars"

mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => {
    captured_requests.append(req)
    req.respond_with(200, { "versionSerial": "vs1" })
  }
)
install_mock(mock_http)

client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))
channel = client.channels.get(channel_name)
```

### Test Steps
```pseudo
AWAIT channel.updateMessage(
  Message(serial: serial_with_special_chars, data: "updated")
)
```

### Assertions
```pseudo
request = captured_requests[0]
ASSERT request.url.path == "/channels/" + encode_uri_component(channel_name) + "/messages/" + encode_uri_component(serial_with_special_chars)
```
