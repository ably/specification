# Error Types Tests

Spec points: `TI1`, `TI2`, `TI3`, `TI4`, `TI5`

## Test Type
Unit test - pure type/model validation

## Mock Configuration
No mocks required - these verify type structure.

---

## TI1-TI5 - ErrorInfo attributes

Tests that `ErrorInfo` (or `AblyException`) has all required attributes.

### Test Cases

| ID | Spec | Attribute | Type | Description |
|----|------|-----------|------|-------------|
| 1 | TI1 | `code` | Integer | Ably-specific error code |
| 2 | TI2 | `statusCode` | Integer | HTTP status code |
| 3 | TI3 | `message` | String | Human-readable error message |
| 4 | TI4 | `href` | String | URL for more information |
| 5 | TI5 | `cause` | Error/Exception | Underlying cause |

### Test Steps
```pseudo
# TI1 - code attribute
error = ErrorInfo(code: 40000)
ASSERT error.code == 40000

# TI2 - statusCode attribute
error = ErrorInfo(code: 40100, statusCode: 401)
ASSERT error.statusCode == 401

# TI3 - message attribute
error = ErrorInfo(
  code: 40000,
  statusCode: 400,
  message: "Bad request: invalid parameter"
)
ASSERT error.message == "Bad request: invalid parameter"

# TI4 - href attribute (optional)
error = ErrorInfo(
  code: 40000,
  href: "https://help.ably.io/error/40000"
)
ASSERT error.href == "https://help.ably.io/error/40000"

# TI5 - cause attribute (optional)
original_error = Exception("Network failure")
error = ErrorInfo(
  code: 50003,
  statusCode: 500,
  message: "Timeout",
  cause: original_error
)
ASSERT error.cause == original_error
```

---

## TI - ErrorInfo from JSON response

Tests that `ErrorInfo` can be deserialized from Ably error response.

### Test Steps
```pseudo
json_response = {
  "error": {
    "code": 40100,
    "statusCode": 401,
    "message": "Token expired",
    "href": "https://help.ably.io/error/40100"
  }
}

error = ErrorInfo.fromJson(json_response["error"])

ASSERT error.code == 40100
ASSERT error.statusCode == 401
ASSERT error.message == "Token expired"
ASSERT error.href == "https://help.ably.io/error/40100"
```

---

## TI - ErrorInfo with nested error

Tests parsing error response with nested error structure.

### Test Steps
```pseudo
json_response = {
  "error": {
    "code": 50000,
    "statusCode": 500,
    "message": "Internal error",
    "cause": {
      "code": 50001,
      "message": "Database connection failed"
    }
  }
}

error = ErrorInfo.fromJson(json_response["error"])

ASSERT error.code == 50000
ASSERT error.cause IS ErrorInfo OR error.cause IS Exception
IF error.cause IS ErrorInfo:
  ASSERT error.cause.code == 50001
  ASSERT error.cause.message == "Database connection failed"
```

---

## TI - AblyException wraps ErrorInfo

Tests that `AblyException` (throwable) wraps `ErrorInfo`.

### Test Steps
```pseudo
error_info = ErrorInfo(
  code: 40000,
  statusCode: 400,
  message: "Bad request"
)

exception = AblyException(errorInfo: error_info)

ASSERT exception.code == 40000
ASSERT exception.statusCode == 400
ASSERT exception.message == "Bad request"
ASSERT exception.errorInfo == error_info
```

---

## TI - Common error codes

Tests that common Ably error codes are handled correctly.

### Test Cases

| ID | Code | Status | Meaning |
|----|------|--------|---------|
| 1 | 40000 | 400 | Bad request |
| 2 | 40100 | 401 | Unauthorized |
| 3 | 40101 | 401 | Invalid credentials |
| 4 | 40140 | 401 | Token error |
| 5 | 40142 | 401 | Token expired |
| 6 | 40160 | 401 | Invalid capability |
| 7 | 40300 | 403 | Forbidden |
| 8 | 40400 | 404 | Not found |
| 9 | 50000 | 500 | Internal server error |
| 10 | 50003 | 500 | Timeout |

### Test Steps
```pseudo
FOR EACH test_case IN test_cases:
  error = ErrorInfo(
    code: test_case.code,
    statusCode: test_case.status,
    message: test_case.meaning
  )

  ASSERT error.code == test_case.code
  ASSERT error.statusCode == test_case.status
```

---

## TI - Error string representation

Tests that errors have a useful string representation.

### Test Steps
```pseudo
error = ErrorInfo(
  code: 40100,
  statusCode: 401,
  message: "Unauthorized: token expired"
)

string_repr = str(error)

# String should include key information
ASSERT "40100" IN string_repr
ASSERT "401" IN string_repr
ASSERT "Unauthorized" IN string_repr OR "token" IN string_repr
```

---

## TI - Error equality

Tests that errors can be compared for equality.

### Test Steps
```pseudo
error1 = ErrorInfo(code: 40000, statusCode: 400, message: "Bad request")
error2 = ErrorInfo(code: 40000, statusCode: 400, message: "Bad request")
error3 = ErrorInfo(code: 40100, statusCode: 401, message: "Unauthorized")

ASSERT error1 == error2  # Same content
ASSERT error1 != error3  # Different code
```
