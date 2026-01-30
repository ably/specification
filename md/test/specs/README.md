# Test Specifications

Portable test specifications for Ably REST SDK implementation.

## Directory Structure

```
specs/
├── unit/                          # Unit tests (mocked HTTP)
│   ├── auth/
│   │   ├── auth_callback.md       # RSA8c, RSA8d - authCallback/authUrl invocation
│   │   ├── auth_scheme.md         # RSA1-4, RSA4b, RSC18 - auth method selection
│   │   ├── token_renewal.md       # RSA4b4, RSA14 - token expiry and renewal
│   │   └── client_id.md           # RSA7, RSA12 - clientId handling
│   ├── channel/
│   │   ├── history.md             # RSL2 - channel history
│   │   ├── idempotency.md         # RSL1k - idempotent publishing
│   │   └── publish.md             # RSL1 - channel publish
│   ├── client/
│   │   ├── client_options.md      # RSC1 - ClientOptions parsing
│   │   ├── fallback.md            # RSC15, REC - host fallback
│   │   ├── rest_client.md         # RSC7, RSC8, RSC13, RSC18 - client configuration
│   │   ├── time.md                # RSC16 - server time
│   │   └── stats.md               # RSC6 - application statistics
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
│   ├── publish.md                 # RSL1 - channel publish
│   └── time_stats.md              # RSC16, RSC6 - time and stats APIs
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

#### Sandbox App Management

Test apps created using this endpoint should be created **once** in the setup for a test run, and **explicitly deleted** when complete. Multiple tests can run against a single app so long as there is no conflict between the state created between those tests.

```pseudo
BEFORE ALL TESTS:
  app_config = POST https://sandbox.realtime.ably-nonprod.net/apps
    WITH body from ably-common/test-resources/test-app-setup.json
  api_key = app_config.keys[0].key_str

AFTER ALL TESTS:
  DELETE https://sandbox.realtime.ably-nonprod.net/apps/{app_id}
    WITH Authorization: Basic {api_key}
```

#### Unique Channel Names

Any channels created by tests within sandbox apps should be unique for each test. The preferred approach to ensuring uniqueness is to construct channel names as a combination of:
1. A **descriptive part** that refers to the test (e.g., including the name of the test, or the ID of the spec item)
2. A **random part** that's sufficiently large to ensure the risk of collision is negligible (e.g., a base64-encoded 48-bit number)

Example: `test-RSL1-publish-${base64(random_bytes(6))}`

#### Authenticated Endpoints

Do **not** use `time()` for testing authentication because it does not require authentication. Use the **channel status endpoint** instead:

```pseudo
GET /channels/{channel_name}
```

This endpoint requires authentication and returns channel metadata.

## Token Testing

### JWT vs Native Tokens

All relevant token functionality should be integration-tested with **both**:
1. **JWTs** (primary format) - Use a third-party JWT library to generate valid JWTs for integration tests
2. **Ably native tokens** - Obtained using `requestToken()`

JWT should be the primary token format used. Native tokens, and the correct handling of token requests, should be tested in a way that's as independent as possible from testing the mechanisms relating to handling tokens in requests and the token renewal process via `authCallback` and `authUrl`.

### Unit Tests with Tokens

For unit tests, since the token string is opaque to the library, any arbitrary string can be used as a token value.

## Avoiding Flaky Tests

### Polling Instead of Fixed Waits

Do not use fixed `WAIT` durations that may cause flakiness due to timing variations. Instead, use polling:

```pseudo
# Bad - flaky
WAIT 5 seconds
ASSERT condition

# Good - reliable
poll_until(
  condition,
  interval: 500ms,
  timeout: 10s
)
```

### Token Expiry Testing

For tests that need to wait for token expiry:
1. Use a short TTL (e.g., 2 seconds)
2. Wait the TTL duration
3. Poll an endpoint at intervals (e.g., 500ms) until rejection
4. Set a reasonable timeout (e.g., 5 seconds after TTL)

This approach avoids flakes from minor clock skew while minimizing test duration.

## Spec Point Coverage

### REST Client (RSC)
| Spec | Test File | Description |
|------|-----------|-------------|
| RSC1 | unit/client/client_options.md | String argument detection |
| RSC6 | unit/client/stats.md | Application statistics |
| RSC7 | unit/client/rest_client.md | Request headers |
| RSC8 | unit/client/rest_client.md | Protocol selection |
| RSC13 | unit/client/rest_client.md | Request timeouts |
| RSC15 | unit/client/fallback.md | Host fallback |
| RSC16 | unit/client/time.md | Server time |
| RSC18 | unit/client/rest_client.md | TLS configuration |

### REST Authentication (RSA)
| Spec | Test File | Description |
|------|-----------|-------------|
| RSA1-4 | unit/auth/auth_scheme.md | Auth method selection |
| RSA4b4, RSA14 | unit/auth/token_renewal.md | Token expiry and renewal |
| RSA7 | unit/auth/client_id.md | clientId from options |
| RSA8c | unit/auth/auth_callback.md | authUrl queries |
| RSA8d | unit/auth/auth_callback.md | authCallback invocation |
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

### Polling
```pseudo
poll_until(condition, interval, timeout):
  start = now()
  WHILE now() - start < timeout:
    IF condition():
      RETURN success
    WAIT interval
  FAIL("Timeout waiting for condition")
```

## Fixtures

Where applicable, tests reference fixtures from `ably-common`:
- Encoding/decoding test vectors
- Standard test data
- App setup configuration: `test-resources/test-app-setup.json`

## Implementation Notes

When implementing these tests:
1. Use the language's idiomatic testing framework
2. Implement mock HTTP client via appropriate mechanism (dependency injection, HttpOverrides, etc.)
3. Group related tests in the same test file/class
4. Use descriptive test names that reference spec points
5. Consider parameterized/table-driven tests for test cases
6. For JWT generation in integration tests, use a well-established third-party JWT library
