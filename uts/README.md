# Universal Test Specifications (UTS)

Portable test specifications for Ably client library implementations. Each spec defines what to test in language-neutral pseudocode, which is then translated into runnable tests for each SDK.

## Directory Structure

```
uts/
├── rest/
│   ├── unit/                          # REST unit tests (mocked HTTP)
│   │   ├── helpers/
│   │   │   └── mock_http.md           # Mock HTTP infrastructure spec
│   │   ├── auth/                      # RSA — authentication
│   │   ├── channel/                   # RSL — channel operations
│   │   ├── encoding/                  # RSL4/RSL6 — message encoding
│   │   ├── presence/                  # RSP — REST presence
│   │   ├── push/                      # RSH — push admin
│   │   └── types/                     # T* — type definitions
│   └── integration/                   # REST integration tests (Ably sandbox)
├── realtime/
│   ├── unit/                          # Realtime unit tests (mocked WebSocket)
│   │   ├── helpers/
│   │   │   ├── mock_websocket.md      # Mock WebSocket infrastructure spec
│   │   │   └── mock_vcdiff.md         # Mock VCDiff decoder spec
│   │   ├── auth/                      # RSA/RTC8 — realtime auth
│   │   ├── channels/                  # RTL/RTS — channels and messages
│   │   ├── client/                    # RTC — realtime client
│   │   ├── connection/                # RTN — connection management
│   │   └── presence/                  # RTP — realtime presence
│   └── integration/                   # Realtime integration tests
│       ├── helpers/
│       │   └── proxy.md               # Proxy infrastructure spec
│       ├── proxy/                     # Proxy-based fault injection tests
│       └── *.md                       # Direct sandbox tests
├── proxy/                             # Go test proxy source code
├── docs/                              # Guides and reference
│   ├── writing-test-specs.md          # How to write UTS specs
│   ├── writing-derived-tests.md       # How to translate specs into SDK tests
│   ├── integration-testing.md         # Integration testing policy
│   └── completion-status.md           # Spec coverage matrix
└── README.md                          # This file
```

## Spec File Counts

| Category | Count | Description |
|----------|-------|-------------|
| REST unit | 39 | Mocked HTTP client tests |
| REST integration | 10 | Ably sandbox tests |
| Realtime unit | 48 | Mocked WebSocket tests |
| Realtime integration (direct) | 13 | Direct sandbox tests |
| Realtime integration (proxy) | 7 | Fault injection via Go proxy |
| Helper specs | 4 | Mock infrastructure definitions |
| **Total** | **121** | |

## Three Test Tiers

**Unit tests** use mocked transports (MockHttpClient, MockWebSocket) to verify client-side logic: state machines, request formation, response parsing, timer behaviour, error handling. They are fast and deterministic.

**Integration tests** (direct) run against the Ably sandbox to verify that the SDK interoperates correctly with the real service. No fault injection — these test happy-path behaviour and real error responses.

**Integration tests** (proxy) run against the Ably sandbox through a programmable Go proxy that can inject faults: connection drops, suppressed frames, replaced responses, HTTP error injection. These test behaviour that can't be verified without controlling the network path.

## Pseudocode Conventions

Test specs use a consistent pseudocode syntax:

```pseudo
# Setup
mock_http = MockHttpClient(
  onConnectionAttempt: (conn) => conn.respond_with_success(),
  onRequest: (req) => req.respond_with(200, {"result": "ok"})
)
install_mock(mock_http)
client = Rest(options: ClientOptions(key: "appId.keyId:keySecret"))

# Test
result = AWAIT client.operation()

# Assertions
ASSERT result.field == "ok"
ASSERT request.url.path == "/channels/" + encode_uri_component(name) + "/messages"

# Error testing
AWAIT client.badOperation() FAILS WITH error
ASSERT error.code == 40160

# State transitions
AWAIT_STATE client.connection.state == ConnectionState.connected
```

See [docs/writing-test-specs.md](docs/writing-test-specs.md) for the full pseudocode reference, mock patterns, and conventions.

## Guides

- **[Writing Test Specs](docs/writing-test-specs.md)** — How to author UTS specs: mock patterns, pseudocode conventions, proxy test structure, common mistakes
- **[Writing Derived Tests](docs/writing-derived-tests.md)** — How to translate UTS specs into SDK-specific tests, diagnose failures, and record deviations
- **[Integration Testing Policy](docs/integration-testing.md)** — When to write integration vs unit tests, proxy test design principles, test structure conventions
- **[Completion Status](docs/completion-status.md)** — Coverage matrix tracking which spec items have UTS test specs

## Go Test Proxy

The `proxy/` directory contains a Go-based programmable proxy for integration testing. It sits between the SDK and the Ably sandbox, transparently forwarding traffic while allowing rule-based fault injection.

The proxy is controlled via a REST API on port 9100. Tests create sessions with rules, connect the SDK through the proxy, and verify behaviour via SDK state and proxy event logs.

See `realtime/integration/helpers/proxy.md` for the proxy infrastructure specification.
