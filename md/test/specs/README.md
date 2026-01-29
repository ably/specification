# Test Specifications

Portable test specifications for Ably REST SDK implementation.

## Directory Structure

```
specs/
├── unit/                          # Unit tests (mocked HTTP)
│   ├── auth/
│   │   ├── auth_callback.md       # RSA8c, RSA8d - authCallback/authUrl
│   │   ├── auth_scheme.md         # RSA1-4 - authentication method selection
│   │   ├── authorize.md           # RSA10 - Auth.authorize()
│   │   └── client_id.md           # RSA7, RSA12 - clientId handling
│   ├── channel/
│   │   ├── history.md             # RSL2 - channel history
│   │   ├── idempotency.md         # RSL1k - idempotent publishing
│   │   └── publish.md             # RSL1 - channel publish
│   ├── client/
│   │   ├── client_options.md      # RSC1 - ClientOptions parsing
│   │   ├── fallback.md            # RSC15, REC - host fallback
│   │   └── rest_client.md         # RSC7, RSC8, RSC13, RSC18 - client configuration
│   ├── encoding/
│   │   └── message_encoding.md    # RSL4, RSL6 - data encoding/decoding
│   └── types/
│       ├── error_types.md         # TI - ErrorInfo
│       ├── message_types.md       # TM - Message
│       ├── options_types.md       # TO, AO - ClientOptions, AuthOptions
│       ├── paginated_result.md    # TG - PaginatedResult
│       └── token_types.md         # TD, TK, TE - TokenDetails, TokenParams, TokenRequest
├── integration/                   # Integration tests (Ably sandbox)
│   ├── auth.md                    # Authentication against real server
│   ├── history.md                 # History retrieval
│   ├── pagination.md              # TG - pagination navigation
│   └── publish.md                 # RSL1d, RSL1k4, RSL1k5, RSL1l1, RSL1m4, RSL1n
└── README.md                      # This file
```

## Test Types

### Unit Tests

Unit tests use a mocked HTTP client to:
- Verify correct request formation (headers, body, query params)
- Test response parsing
- Test error handling
- Test client-side validation

The mock HTTP client should:
- Capture outgoing requests for inspection
- Return configurable responses
- Support per-host response configuration (for fallback tests)
- Simulate failure conditions (timeout, connection errors)

### Integration Tests

Integration tests run against the Ably sandbox environment:
- `POST https://sandbox.realtime.ably-nonprod.net/apps` to provision app
- Use `endpoint: "sandbox"` in ClientOptions
- Test real server behavior and validation

## Spec Point Coverage

### REST Client (RSC)
| Spec | Test File | Description |
|------|-----------|-------------|
| RSC1 | unit/client/client_options.md | String argument detection |
| RSC7 | unit/client/rest_client.md | Request headers |
| RSC8 | unit/client/rest_client.md | Protocol selection |
| RSC13 | unit/client/rest_client.md | Request timeouts |
| RSC15 | unit/client/fallback.md | Host fallback |
| RSC18 | unit/client/rest_client.md | TLS configuration |

### REST Authentication (RSA)
| Spec | Test File | Description |
|------|-----------|-------------|
| RSA1-4 | unit/auth/auth_scheme.md | Auth method selection |
| RSA7 | unit/auth/client_id.md | clientId from options |
| RSA8c | unit/auth/auth_callback.md | authUrl queries |
| RSA8d | unit/auth/auth_callback.md | authCallback invocation |
| RSA10 | unit/auth/authorize.md | Auth.authorize() |
| RSA12 | unit/auth/client_id.md | clientId in TokenParams |

### REST Channel (RSL)
| Spec | Test File | Description |
|------|-----------|-------------|
| RSL1 | unit/channel/publish.md | Channel publish |
| RSL1k | unit/channel/idempotency.md | Idempotent publishing |
| RSL2 | unit/channel/history.md | Channel history |
| RSL4, RSL6 | unit/encoding/message_encoding.md | Message encoding |

### Types (T*)
| Spec | Test File | Description |
|------|-----------|-------------|
| TD | unit/types/token_types.md | TokenDetails |
| TK | unit/types/token_types.md | TokenParams |
| TE | unit/types/token_types.md | TokenRequest |
| TM | unit/types/message_types.md | Message |
| TO | unit/types/options_types.md | ClientOptions |
| AO | unit/types/options_types.md | AuthOptions |
| TI | unit/types/error_types.md | ErrorInfo |
| TG | unit/types/paginated_result.md | PaginatedResult |

### Environment Configuration (REC)
| Spec | Test File | Description |
|------|-----------|-------------|
| REC1, REC2 | unit/client/fallback.md | Custom endpoints |

## Pseudo-code Conventions

### Setup Blocks
```pseudo
mock_http = MockHttpClient()
mock_http.queue_response(status, body)
mock_http.queue_response_for_host(host, status, body)

client = Rest(options: ClientOptions(...))
```

### Test Steps
```pseudo
result = AWAIT client.operation()
```

### Assertions
```pseudo
ASSERT condition
ASSERT value == expected
ASSERT value IN list
ASSERT value matches pattern "regex"
ASSERT value IS Type
ASSERT "key" IN object
ASSERT "key" NOT IN object
```

### Error Testing
```pseudo
TRY:
  AWAIT operation_that_fails()
  FAIL("Expected exception")
CATCH ExceptionType as e:
  ASSERT e.code == expected_code
```

### Loops
```pseudo
FOR EACH item IN collection:
  # test each item

FOR i IN 1..10:
  # test numbered items
```

## Fixtures

Where applicable, tests reference fixtures from `ably-common`:
- Encoding/decoding test vectors
- Standard test data

## Implementation Notes

When implementing these tests:
1. Use the language's idiomatic testing framework
2. Implement mock HTTP client via appropriate mechanism (dependency injection, HttpOverrides, etc.)
3. Group related tests in the same test file/class
4. Use descriptive test names that reference spec points
5. Consider parameterized/table-driven tests for test cases
