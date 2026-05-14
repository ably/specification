# ObjectId Generation Tests

Spec points: `RTO14`

## Test Type
Unit test — pure function, no mocks required.

## Purpose

Tests the ObjectId generation procedure. ObjectId format is `{type}:{base64url(SHA-256(initialValue:nonce))}@{timestamp}`. This is a deterministic hash-based scheme that ensures uniqueness across clients.

---

## RTO14 - ObjectId format for counter type

**Test ID**: `objects/unit/RTO14/objectid-format-counter-0`

| Spec | Requirement |
|------|-------------|
| RTO14a1 | type must be "map" or "counter" |
| RTO14b1 | SHA-256 of UTF-8 encoded "[initialValue]:[nonce]" |
| RTO14b2 | Base64URL encode (RFC 4648 s.5) |
| RTO14c | Format: [type]:[hash]@[timestamp] |

### Test Steps
```pseudo
objectId = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":42}}',
  nonce: "test-nonce-12345678",
  timestamp: 1700000000000
)
```

### Assertions
```pseudo
ASSERT objectId STARTS WITH "counter:"
ASSERT objectId CONTAINS "@1700000000000"
parts = objectId.split(":")
type_part = parts[0]
rest = parts[1]
hash_and_ts = rest.split("@")
hash_part = hash_and_ts[0]
ts_part = hash_and_ts[1]
ASSERT type_part == "counter"
ASSERT ts_part == "1700000000000"
ASSERT hash_part IS valid base64url string
ASSERT hash_part does NOT contain "+" or "/" or "="
```

---

## RTO14 - ObjectId format for map type

**Test ID**: `objects/unit/RTO14/objectid-format-map-0`

**Spec requirement:** Same format with "map" type prefix.

### Test Steps
```pseudo
objectId = generateObjectId(
  type: "map",
  initialValue: '{"map":{"semantics":"LWW","entries":{}}}',
  nonce: "test-nonce-12345678",
  timestamp: 1700000000000
)
```

### Assertions
```pseudo
ASSERT objectId STARTS WITH "map:"
ASSERT objectId CONTAINS "@1700000000000"
```

---

## RTO14 - Deterministic output for same inputs

**Test ID**: `objects/unit/RTO14/deterministic-0`

**Spec requirement:** Same type, initialValue, nonce, and timestamp produce the same objectId.

### Test Steps
```pseudo
id1 = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":0}}',
  nonce: "same-nonce-1234567",
  timestamp: 1700000000000
)
id2 = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":0}}',
  nonce: "same-nonce-1234567",
  timestamp: 1700000000000
)
```

### Assertions
```pseudo
ASSERT id1 == id2
```

---

## RTO14 - Different nonce produces different objectId

**Test ID**: `objects/unit/RTO14/different-nonce-0`

**Spec requirement:** Nonce ensures uniqueness across clients.

### Test Steps
```pseudo
id1 = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":0}}',
  nonce: "nonce-aaaaaaaaaaaaa",
  timestamp: 1700000000000
)
id2 = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":0}}',
  nonce: "nonce-bbbbbbbbbbbbb",
  timestamp: 1700000000000
)
```

### Assertions
```pseudo
ASSERT id1 != id2
```

---

## RTO14b - SHA-256 hash is base64url encoded (not standard base64)

**Test ID**: `objects/unit/RTO14b/base64url-encoding-0`

| Spec | Requirement |
|------|-------------|
| RTO14b2 | Must use URL-safe Base64 per RFC 4648 s.5, not standard Base64 |

### Test Steps
```pseudo
objectId = generateObjectId(
  type: "counter",
  initialValue: '{"counter":{"count":0}}',
  nonce: "test-nonce-12345678",
  timestamp: 1700000000000
)
hash_part = objectId.split(":")[1].split("@")[0]
```

### Assertions
```pseudo
ASSERT hash_part does NOT contain "+"
ASSERT hash_part does NOT contain "/"
ASSERT hash_part does NOT end with "="
```
