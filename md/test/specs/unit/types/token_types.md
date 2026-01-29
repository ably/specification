# Token Types Tests

Spec points: `TD1`, `TD2`, `TD3`, `TD4`, `TD5`, `TK1`, `TK2`, `TK3`, `TK4`, `TK5`, `TK6`, `TE1`, `TE2`, `TE3`, `TE4`, `TE5`, `TE6`

## Test Type
Unit test - pure type/model validation

## Mock Configuration
No mocks required for most tests - these verify type structure and serialization.

---

## TD1-TD5 - TokenDetails structure

Tests that `TokenDetails` has all required attributes.

### Test Steps
```pseudo
# TD1 - token attribute
token_details = TokenDetails(
  token: "test-token",
  expires: 1234567890000
)
ASSERT token_details.token == "test-token"

# TD2 - expires attribute (milliseconds since epoch)
ASSERT token_details.expires == 1234567890000

# TD3 - issued attribute
token_with_issued = TokenDetails(
  token: "test-token",
  expires: 1234567890000,
  issued: 1234567800000
)
ASSERT token_with_issued.issued == 1234567800000

# TD4 - capability attribute (JSON string)
token_with_capability = TokenDetails(
  token: "test-token",
  expires: 1234567890000,
  capability: "{\"*\":[\"*\"]}"
)
ASSERT token_with_capability.capability == "{\"*\":[\"*\"]}"

# TD5 - clientId attribute
token_with_client = TokenDetails(
  token: "test-token",
  expires: 1234567890000,
  clientId: "my-client"
)
ASSERT token_with_client.clientId == "my-client"
```

---

## TD - TokenDetails from JSON

Tests that `TokenDetails` can be deserialized from JSON response.

### Test Steps
```pseudo
json_data = {
  "token": "deserialized-token",
  "expires": 1234567890000,
  "issued": 1234567800000,
  "capability": "{\"channel-1\":[\"publish\"]}",
  "clientId": "json-client",
  "keyName": "appId.keyId"
}

token_details = TokenDetails.fromJson(json_data)

ASSERT token_details.token == "deserialized-token"
ASSERT token_details.expires == 1234567890000
ASSERT token_details.issued == 1234567800000
ASSERT token_details.capability == "{\"channel-1\":[\"publish\"]}"
ASSERT token_details.clientId == "json-client"
```

---

## TK1-TK6 - TokenParams structure

Tests that `TokenParams` has all required attributes.

### Test Steps
```pseudo
# TK1 - ttl attribute (milliseconds)
params = TokenParams(ttl: 3600000)
ASSERT params.ttl == 3600000

# TK2 - capability attribute
params = TokenParams(capability: "{\"*\":[\"subscribe\"]}")
ASSERT params.capability == "{\"*\":[\"subscribe\"]}"

# TK3 - clientId attribute
params = TokenParams(clientId: "param-client")
ASSERT params.clientId == "param-client"

# TK4 - timestamp attribute (milliseconds since epoch)
params = TokenParams(timestamp: 1234567890000)
ASSERT params.timestamp == 1234567890000

# TK5 - nonce attribute
params = TokenParams(nonce: "unique-nonce-value")
ASSERT params.nonce == "unique-nonce-value"

# TK6 - All attributes together
params = TokenParams(
  ttl: 7200000,
  capability: "{\"*\":[\"*\"]}",
  clientId: "full-client",
  timestamp: 1234567890000,
  nonce: "full-nonce"
)
ASSERT params.ttl == 7200000
ASSERT params.capability == "{\"*\":[\"*\"]}"
ASSERT params.clientId == "full-client"
ASSERT params.timestamp == 1234567890000
ASSERT params.nonce == "full-nonce"
```

---

## TK - TokenParams to query string

Tests that `TokenParams` are correctly converted to query parameters.

### Test Steps
```pseudo
params = TokenParams(
  ttl: 3600000,
  clientId: "query-client",
  capability: "{\"ch\":[\"pub\"]}"
)

query_map = params.toQueryParams()

ASSERT query_map["ttl"] == "3600000"
ASSERT query_map["clientId"] == "query-client"
ASSERT query_map["capability"] == "{\"ch\":[\"pub\"]}"
```

---

## TE1-TE6 - TokenRequest structure

Tests that `TokenRequest` has all required attributes.

### Test Steps
```pseudo
# TE1 - keyName attribute
request = TokenRequest(
  keyName: "appId.keyId",
  timestamp: 1234567890000,
  nonce: "nonce-1"
)
ASSERT request.keyName == "appId.keyId"

# TE2 - ttl attribute
request = TokenRequest(
  keyName: "appId.keyId",
  ttl: 3600000,
  timestamp: 1234567890000,
  nonce: "nonce-2"
)
ASSERT request.ttl == 3600000

# TE3 - capability attribute
request = TokenRequest(
  keyName: "appId.keyId",
  capability: "{\"*\":[\"*\"]}",
  timestamp: 1234567890000,
  nonce: "nonce-3"
)
ASSERT request.capability == "{\"*\":[\"*\"]}"

# TE4 - clientId attribute
request = TokenRequest(
  keyName: "appId.keyId",
  clientId: "request-client",
  timestamp: 1234567890000,
  nonce: "nonce-4"
)
ASSERT request.clientId == "request-client"

# TE5 - timestamp attribute
request = TokenRequest(
  keyName: "appId.keyId",
  timestamp: 1234567890000,
  nonce: "nonce-5"
)
ASSERT request.timestamp == 1234567890000

# TE6 - nonce attribute
request = TokenRequest(
  keyName: "appId.keyId",
  timestamp: 1234567890000,
  nonce: "unique-nonce"
)
ASSERT request.nonce == "unique-nonce"
```

---

## TE - TokenRequest with mac (signature)

Tests that `TokenRequest` includes the mac signature.

### Test Steps
```pseudo
request = TokenRequest(
  keyName: "appId.keyId",
  timestamp: 1234567890000,
  nonce: "nonce-value",
  mac: "signature-base64"
)

ASSERT request.mac == "signature-base64"
```

---

## TE - TokenRequest to JSON

Tests that `TokenRequest` serializes correctly for transmission.

### Test Steps
```pseudo
request = TokenRequest(
  keyName: "appId.keyId",
  ttl: 3600000,
  capability: "{\"*\":[\"*\"]}",
  clientId: "json-client",
  timestamp: 1234567890000,
  nonce: "json-nonce",
  mac: "json-mac"
)

json_data = request.toJson()

ASSERT json_data["keyName"] == "appId.keyId"
ASSERT json_data["ttl"] == 3600000
ASSERT json_data["capability"] == "{\"*\":[\"*\"]}"
ASSERT json_data["clientId"] == "json-client"
ASSERT json_data["timestamp"] == 1234567890000
ASSERT json_data["nonce"] == "json-nonce"
ASSERT json_data["mac"] == "json-mac"
```

---

## TE - TokenRequest from JSON

Tests that `TokenRequest` can be deserialized from JSON.

### Test Steps
```pseudo
json_data = {
  "keyName": "appId.keyId",
  "ttl": 7200000,
  "capability": "{\"ch\":[\"sub\"]}",
  "clientId": "from-json-client",
  "timestamp": 1234567899999,
  "nonce": "from-json-nonce",
  "mac": "from-json-mac"
}

request = TokenRequest.fromJson(json_data)

ASSERT request.keyName == "appId.keyId"
ASSERT request.ttl == 7200000
ASSERT request.capability == "{\"ch\":[\"sub\"]}"
ASSERT request.clientId == "from-json-client"
ASSERT request.timestamp == 1234567899999
ASSERT request.nonce == "from-json-nonce"
ASSERT request.mac == "from-json-mac"
```
