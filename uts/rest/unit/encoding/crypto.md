# Crypto Tests

Spec points: `RSE1`, `RSE1a`, `RSE1b`, `RSE1c`, `RSE1d`, `RSE1e`, `RSE2`, `RSE2a`, `RSE2b`, `TZ2a`, `TZ2b`, `TZ2c`, `TZ2d`, `CO2`

## Test Type
Unit test — no network or mock transport is involved. `Crypto` here is the SDK's `Crypto` utility (RSE): whatever
the SDK exposes `Crypto::getDefaultParams` and `Crypto::generateRandomKey` on.

## Notes

- **Algorithm and mode names.** TZ2a and TZ2c give the defaults as `AES` and `CBC`. SDKs differ in the case they
  report them in (`AES` / `aes`), and the `encoding` string uses lower case (`cipher+aes-256-cbc`), so these tests
  compare the names case-insensitively with `lowercase(...)`.
- **`base64_decode(s)`** decodes a standard (RFC 4648 §4) base64 string to bytes; **`bytes_of_length(n)`** is any
  `n`-byte binary value.

---

## RSE1a, RSE1b, RSE1d, TZ2 - getDefaultParams fills in the defaults

**Test ID**: `rest/unit/RSE1a/default-params-0`

| Spec | Requirement |
|------|-------------|
| RSE1a | Returns a complete `CipherParams` instance, using the default values for any field not supplied |
| RSE1b | Takes a `CipherParamOptions` instance |
| RSE1d | Calculates a `keyLength` from the key (its size in bits) |
| TZ2a | `algorithm` defaults to `AES` |
| TZ2c | `mode` defaults to `CBC` |

Tests that `getDefaultParams` given only a key returns AES-CBC parameters with the key and its length.

### Setup
```pseudo
key = bytes_of_length(32)
```

### Test Steps
```pseudo
params = Crypto.getDefaultParams(CipherParamOptions(key: key))
```

### Assertions
```pseudo
ASSERT lowercase(params.algorithm) == "aes"
ASSERT lowercase(params.mode) == "cbc"
ASSERT params.keyLength == 256
ASSERT params.key == key
```

---

## RSE1d - keyLength is calculated from a 128-bit key

**Test ID**: `rest/unit/RSE1d/key-length-from-key-0`

**Spec requirement:** Calculates a `keyLength` from the key (its size in bits).

Tests that a 16-byte key gives a `keyLength` of 128.

### Setup
```pseudo
key = bytes_of_length(16)
```

### Test Steps
```pseudo
params = Crypto.getDefaultParams(CipherParamOptions(key: key))
```

### Assertions
```pseudo
ASSERT params.keyLength == 128
ASSERT params.key == key
```

---

## RSE1c - A base64-encoded string key is decoded

**Test ID**: `rest/unit/RSE1c/base64-string-key-0`

**Spec requirement:** The `key` must be either a binary or a base64-encoded string. If the key is a string, the function should base64-decode it into a binary.

Tests that a key given as a base64 string is decoded, and its length calculated from the decoded bytes.

### Setup
```pseudo
key_string = "o9qXZoPGDNla50VnRwH7cGqIrpyagTxGsRgimKJbY40="  # 32 bytes, ably-common crypto-data-256.json
```

### Test Steps
```pseudo
params = Crypto.getDefaultParams(CipherParamOptions(key: key_string))
```

### Assertions
```pseudo
ASSERT params.key == base64_decode(key_string)
ASSERT params.keyLength == 256
```

---

## RSE1c - A base64url string key is decoded leniently

**Test ID**: `rest/unit/RSE1c/base64url-string-key-1`

**Spec requirement:** Since the conversion to base64 is not under Ably control, this should be done leniently --- in particular, it should work with base64url (RFC 4648 s.5, which uses `-` and `_` instead of `+` and `/`) as well as base64 (RFC 4648 s.4).

Tests that the same key gives the same `CipherParams` whether it is base64- or base64url-encoded. The key's bytes
are chosen so that its base64 form contains `+` and `/`.

### Setup
```pseudo
base64_key = "+/+/+/+/+/+/+/+/+/+/+w=="     # 16 bytes: fb ff bf fb ff bf … fb
base64url_key = "-_-_-_-_-_-_-_-_-_-_-w=="  # the same bytes, base64url
```

### Test Steps
```pseudo
params_from_base64 = Crypto.getDefaultParams(CipherParamOptions(key: base64_key))
params_from_base64url = Crypto.getDefaultParams(CipherParamOptions(key: base64url_key))
```

### Assertions
```pseudo
ASSERT params_from_base64url.key == base64_decode(base64_key)
ASSERT params_from_base64url.key == params_from_base64.key
ASSERT params_from_base64url.keyLength == 128
```

---

## RSE1e - An invalid key length is rejected

**Test ID**: `rest/unit/RSE1e/invalid-key-length-0`

**Spec requirement:** Checks that the provided options are valid and self-consistent as best it can, raises an exception if not. At a minimum, this should include checking the calculated `keyLength` is a valid key length for the encryption algorithm (for example, 128 or 256 for `AES`).

Tests that a 20-byte (160-bit) key, which AES does not support, is rejected.

### Setup
```pseudo
key = bytes_of_length(20)
```

### Test Steps
```pseudo
Crypto.getDefaultParams(CipherParamOptions(key: key)) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RSE1e - A keyLength inconsistent with the key is rejected

**Test ID**: `rest/unit/RSE1e/inconsistent-key-length-1`

**Spec requirement:** Checks that the provided options are valid and self-consistent as best it can, raises an exception if not.

Tests that a `keyLength` that does not match the key's size (CO2c) is rejected.

### Setup
```pseudo
key = bytes_of_length(32)  # 256 bits
```

### Test Steps
```pseudo
Crypto.getDefaultParams(CipherParamOptions(key: key, keyLength: 128)) FAILS WITH error
```

### Assertions
```pseudo
ASSERT error IS NOT null
```

---

## RSE2a - generateRandomKey defaults to 256 bits

**Test ID**: `rest/unit/RSE2a/default-key-length-0`

**Spec requirement:** Takes an optional `keyLength` parameter, which is the length in bits of the key to be generated. If unspecified, this is equal to the default `keyLength` of the default algorithm: for `AES`, 256 bits.

Tests that a key generated without a `keyLength` is 32 bytes long.

### Test Steps
```pseudo
key = AWAIT Crypto.generateRandomKey()
```

### Assertions
```pseudo
ASSERT length(key) == 32
```

---

## RSE2a - generateRandomKey with an explicit keyLength

**Test ID**: `rest/unit/RSE2a/explicit-key-length-1`

**Spec requirement:** Takes an optional `keyLength` parameter, which is the length in bits of the key to be generated.

Tests that a 128-bit key is 16 bytes long, and is accepted by `getDefaultParams` as a 128-bit key.

### Test Steps
```pseudo
key = AWAIT Crypto.generateRandomKey(keyLength: 128)
params = Crypto.getDefaultParams(CipherParamOptions(key: key))
```

### Assertions
```pseudo
ASSERT length(key) == 16
ASSERT params.keyLength == 128
```

---

## RSE2b - generateRandomKey returns random binary keys

**Test ID**: `rest/unit/RSE2b/random-binary-key-0`

**Spec requirement:** Returns (or calls back with, if the language cryptographic randomness primitives are blocking or async) the key as a binary (e.g. a byte array, depending on the language).

Tests that the key is binary, and that two generated keys differ.

### Test Steps
```pseudo
key1 = AWAIT Crypto.generateRandomKey()
key2 = AWAIT Crypto.generateRandomKey()
```

### Assertions
```pseudo
ASSERT key1 IS Binary
ASSERT key1 != key2
```
