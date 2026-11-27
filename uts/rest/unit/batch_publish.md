# Batch Publish Tests

Tests for `RestClient#batchPublish` (RSC22) and related types (BSP*, BPR*, BPF*).

## Test Type
Unit test with mocked HTTP client

## Mock Configuration

These tests use the mock HTTP infrastructure defined in `rest_client.md`. The mock supports:
- Handler-based configuration with `onConnectionAttempt` and `onRequest`
- Capturing requests via `captured_requests` arrays
- Configurable responses with status codes, bodies, and headers

See `rest_client.md` for detailed mock interface documentation.

## Server Response Format

A client sends the CSV2b protocol version in `X-Ably-Version` (RSC7e). At that version,
as at every version from 3, `POST /messages` returns HTTP 201 and an array holding one
`BatchResult` envelope (BAR2) per `BatchPublishSpec` sent, in the order the specs were sent:

```json
[
  {
    "successCount": 1,
    "failureCount": 1,
    "results": [
      { "channel": "ch-a", "messageId": "msg1", "serials": ["s1"] },
      { "channel": "ch-b", "error": { "code": 40160, "statusCode": 401, "message": "..." } }
    ]
  }
]
```

- **A single spec** sent as a bare object is answered like an array of one: an array holding
  a single envelope. This is the array RSC22b says the REST API still returns; an SDK that
  implements the single-spec overload extracts the envelope from it.
- **All success, mixed and all failure** batches return HTTP 201 with this format.
- **Server-level errors** (HTTP 500, 401, etc.) return an error object: `{"error": {...}}`.
- Each success result (BPR2) carries `serials` (BPR2c), which was added at protocol version 5.

Every batch result fixture in this file is in this format, as the server sends it to a
client sending `X-Ably-Version: 5` or later. A mock described only as responding "with
success" responds with HTTP 201 and one envelope per spec sent, holding a success result
for each channel.

**Legacy format (`X-Ably-Version` 2 or below, or no version header):** the server returns
one flat array of per-channel results across every spec, with nothing marking which spec
each result belongs to, and without `serials`. A batch in which any channel fails is
answered with HTTP 400, error `40020`, and that flat array as `batchResponse`. This format
is not used by current SDKs.

## RSC22c - batchPublish sends POST to /messages

**Spec requirement:** The `batchPublish` method must send a POST request to the `/messages` endpoint with the batch specifications in the request body.

### RSC22c1 - Single BatchPublishSpec sends POST to /messages

**Test ID**: `rest/unit/RSC22c/single-spec-post-messages-0`

**Spec requirement:** A single BatchPublishSpec is sent as a POST to `/messages` with the spec in the request body.

```pseudo
channel_name_1 = "test-RSC22c1-a-${random_id()}"
channel_name_2 = "test-RSC22c1-b-${random_id()}"

Given a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests and respond with success
When batchPublish is called with a single BatchPublishSpec:
  - channels: [channel_name_1, channel_name_2]
  - messages: [Message(name: "event", data: "hello")]
Then a POST request is sent to "/messages"
And the captured request body contains:
  - channels: [channel_name_1, channel_name_2]
  - messages: [{ name: "event", data: "hello" }]
```

### RSC22c2 - Array of BatchPublishSpecs sends POST to /messages

**Test ID**: `rest/unit/RSC22c/array-specs-post-messages-0`

**Spec requirement:** An array of BatchPublishSpecs is sent as a POST to `/messages` with an array of specs in the request body.

```pseudo
channel_name_1 = "test-RSC22c2-a-${random_id()}"
channel_name_2 = "test-RSC22c2-b-${random_id()}"

Given a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests and respond with success
When batchPublish is called with an array of BatchPublishSpecs:
  - BatchPublishSpec(channels: [channel_name_1], messages: [Message(name: "e1", data: "d1")])
  - BatchPublishSpec(channels: [channel_name_2], messages: [Message(name: "e2", data: "d2")])
Then a POST request is sent to "/messages"
And the captured request body is an array containing both specs
```

### RSC22c3 - Single spec returns single BatchResult

**Test ID**: `rest/unit/RSC22c/single-spec-single-result-0`

**Spec requirement:** When a single BatchPublishSpec is sent, batchPublish returns a single BatchResult (not an array). The REST response is still an array of one envelope, from which the SDK extracts the element (RSC22b).

```pseudo
channel_name = "test-RSC22c3-${random_id()}"

Given a REST client with mock HTTP
And the mock is configured to respond with HTTP 201 and:
  [
    {
      "successCount": 1,
      "failureCount": 0,
      "results": [
        { "channel": channel_name, "messageId": "msg123", "serials": ["serial1"] }
      ]
    }
  ]
When batchPublish is called with a single BatchPublishSpec
Then a single BatchResult is returned (not an array)
And the result contains the success result for channel_name
```

### RSC22c4 - Array of specs returns array of BatchResults

**Test ID**: `rest/unit/RSC22c/array-specs-array-results-0`

**Spec requirement:** When an array of BatchPublishSpecs is sent, the response is an array of BatchResults.

```pseudo
channel_name_1 = "test-RSC22c4-a-${random_id()}"
channel_name_2 = "test-RSC22c4-b-${random_id()}"

Given a REST client with mock HTTP
And the mock is configured to respond with HTTP 201 and one envelope per spec:
  [
    {
      "successCount": 1,
      "failureCount": 0,
      "results": [{ "channel": channel_name_1, "messageId": "msg1", "serials": ["s1"] }]
    },
    {
      "successCount": 1,
      "failureCount": 0,
      "results": [{ "channel": channel_name_2, "messageId": "msg2", "serials": ["s2"] }]
    }
  ]
When batchPublish is called with an array of BatchPublishSpecs:
  - BatchPublishSpec(channels: [channel_name_1], messages: [Message(name: "e1", data: "d1")])
  - BatchPublishSpec(channels: [channel_name_2], messages: [Message(name: "e2", data: "d2")])
Then an array of BatchResults is returned
And each result corresponds to the respective spec:
  - result[0].results[0].channel equals channel_name_1
  - result[1].results[0].channel equals channel_name_2
```

### RSC22c5 - Multiple channels in spec produces multiple results

**Test ID**: `rest/unit/RSC22c/multiple-channels-multiple-results-0`

**Spec requirement:** A BatchPublishSpec with multiple channels produces multiple results in the response, one per channel.

```pseudo
channel_name_1 = "test-RSC22c5-a-${random_id()}"
channel_name_2 = "test-RSC22c5-b-${random_id()}"
channel_name_3 = "test-RSC22c5-c-${random_id()}"

Given a REST client with mock HTTP
And a BatchPublishSpec with channels: [channel_name_1, channel_name_2, channel_name_3]
And the mock is configured to respond with HTTP 201 and one envelope holding a result for each channel:
  [
    {
      "successCount": 3,
      "failureCount": 0,
      "results": [
        { "channel": channel_name_1, "messageId": "msg1", "serials": ["s1"] },
        { "channel": channel_name_2, "messageId": "msg2", "serials": ["s2"] },
        { "channel": channel_name_3, "messageId": "msg3", "serials": ["s3"] }
      ]
    }
  ]
When batchPublish is called
Then the BatchResult contains results for all three channels
```

### RSC22c6 - Messages are encoded according to RSL4

**Test ID**: `rest/unit/RSC22c/messages-encoded-per-rsl4-0`

**Spec requirement:** Messages must be encoded according to RSL4 (String, Binary base64, JSON stringified).

```pseudo
channel_name = "test-RSC22c6-${random_id()}"

Given a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests
When batchPublish is called with messages containing:
  - String data
  - Binary data (Uint8List/[]byte)
  - JSON object data
Then the captured request shows each message is encoded per RSL4 (JSON protocol branch):
  - String: data as-is, no encoding
  - Binary: base64 encoded, encoding: "base64"
  - JSON: JSON stringified, encoding: "json"
```

### RSC22c7 - Request uses correct authentication

**Test ID**: `rest/unit/RSC22c/uses-configured-auth-0`

**Spec requirement:** Batch publish requests must use the configured authentication mechanism.

```pseudo
channel_name = "test-RSC22c7-${random_id()}"

Given a REST client with token auth and mock HTTP
And the mock is configured to capture requests
When batchPublish is called
Then the captured POST request includes Authorization: Bearer <token>
```

```pseudo
channel_name = "test-RSC22c7-basic-${random_id()}"

Given a REST client with basic auth and mock HTTP
And the mock is configured to capture requests
When batchPublish is called
Then the captured POST request includes Authorization: Basic <base64(key)>
```

## RSC22d - Idempotent publishing applies RSL1k1

**Spec requirement (RSC22d):** "If `idempotentRestPublishing` is enabled, then RSL1k1 should be applied (to each `BatchPublishSpec` separately)."

### RSC22d - Idempotent IDs generated when enabled

**Test ID**: `rest/unit/RSC22d/idempotent-ids-generated-0`

**Spec requirement:** With idempotentRestPublishing enabled, messages without IDs get unique IDs generated in baseId:serial format per RSL1k1, applied to each BatchPublishSpec separately.

```pseudo
Given a REST client with idempotentRestPublishing: true, useBinaryProtocol: false and mock HTTP
And the mock is configured to capture requests
When batchPublish is called with messages that have no id
Then the captured request shows each message in each BatchPublishSpec has a unique id generated
And the id format follows RSL1k1 (baseId:serial)
And each BatchPublishSpec gets a separate base ID
```

### RSC22d - Explicit message IDs preserved

**Test ID**: `rest/unit/RSC22d/explicit-ids-preserved-0`

**Spec requirement:** Per RSL1k3, messages with explicit IDs must have those IDs preserved as-is, even when idempotent publishing is enabled.

```pseudo
Given a REST client with idempotentRestPublishing: true, useBinaryProtocol: false and mock HTTP
And the mock is configured to capture requests
When batchPublish is called with messages that have explicit ids
Then the captured request shows the explicit ids are preserved (not overwritten)
```

### RSC22d - Idempotent IDs not generated when disabled

**Test ID**: `rest/unit/RSC22d/ids-not-generated-disabled-0`

**Spec requirement:** When idempotent REST publishing is disabled, no IDs are generated for messages without IDs.

```pseudo
Given a REST client with idempotentRestPublishing: false, useBinaryProtocol: false and mock HTTP
And the mock is configured to capture requests
When batchPublish is called with messages that have no id
Then the captured request shows messages are sent without id fields
```

## BSP - BatchPublishSpec Structure

**Spec requirement:** BatchPublishSpec defines the structure for specifying channels and messages in a batch publish request (BSP2a, BSP2b).

### BSP2a - channels is array of strings

**Test ID**: `rest/unit/BSP2a/channels-array-strings-0`

**Spec requirement:** The channels field must be an array of channel name strings.

```pseudo
channel_name_1 = "test-BSP2a-a-${random_id()}"
channel_name_2 = "test-BSP2a-b-${random_id()}"
channel_name_3 = "test-BSP2a-c-${random_id()}"

Given a BatchPublishSpec and a REST client with mock HTTP configured with useBinaryProtocol: false
When channels is set to [channel_name_1, channel_name_2, channel_name_3]
Then the serialized spec in the captured request contains channels as a string array
```

### BSP2b - messages is array of Message objects

**Test ID**: `rest/unit/BSP2b/messages-array-objects-0`

**Spec requirement:** The messages field must be an array of Message objects, each serialized according to TM* rules.

```pseudo
channel_name = "test-BSP2b-${random_id()}"

Given a BatchPublishSpec and a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests
When messages contains multiple Message objects with:
  - Message(name: "event1", data: "data1")
  - Message(name: "event2", data: { "key": "value" })
Then the serialized spec in the captured request contains messages as an array of message objects
And each message is serialized according to TM* rules
```

## BPR - BatchPublishSuccessResult Structure

**Spec requirement:** BatchPublishSuccessResult defines the structure of successful batch publish responses (BPR2a, BPR2b, BPR2c).

### BPR2a - channel field contains channel name

**Test ID**: `rest/unit/BPR2a/success-channel-name-0`

**Spec requirement:** The channel field contains the name of the channel where messages were published.

```pseudo
channel_name = "test-BPR2a-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and:
  [{ "successCount": 1, "failureCount": 0, "results": [
    { "channel": channel_name, "messageId": "msg123", "serials": ["s1"] }
  ] }]
When batchPublish is called with a single BatchPublishSpec for channel_name
And result.results[0] is parsed into BatchPublishSuccessResult
Then result.results[0].channel equals channel_name
```

### BPR2b - messageId contains the message ID prefix

**Test ID**: `rest/unit/BPR2b/success-message-id-prefix-0`

**Spec requirement:** The messageId field contains the unique ID prefix for the published messages.

```pseudo
channel_name = "test-BPR2b-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and:
  [{ "successCount": 1, "failureCount": 0, "results": [
    { "channel": channel_name, "messageId": "unique-id-prefix", "serials": ["s1", "s2"] }
  ] }]
When batchPublish is called with a single BatchPublishSpec for channel_name
And result.results[0] is parsed into BatchPublishSuccessResult
Then result.results[0].messageId equals "unique-id-prefix"
```

### BPR2c - serials contains array of message serials

**Test ID**: `rest/unit/BPR2c/serials-array-0`

**Spec requirement:** The serials field contains an array of serial numbers, one per published message.

```pseudo
channel_name = "test-BPR2c-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and:
  [{ "successCount": 1, "failureCount": 0, "results": [
    { "channel": channel_name, "messageId": "msg", "serials": ["serial1", "serial2", "serial3"] }
  ] }]
When batchPublish is called with a single BatchPublishSpec publishing three messages to channel_name
And result.results[0] is parsed into BatchPublishSuccessResult
Then result.results[0].serials equals ["serial1", "serial2", "serial3"]
And serials.length matches the number of messages published
```

### BPR2c1 - serials may contain null for conflated messages

**Test ID**: `rest/unit/BPR2c/serials-null-conflated-0`

**Spec requirement:** The serials array may contain null values for messages that were conflated (deduplicated).

```pseudo
channel_name = "test-BPR2c1-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and a response where some messages were conflated:
  [{ "successCount": 1, "failureCount": 0, "results": [
    { "channel": channel_name, "messageId": "msg", "serials": ["serial1", null, "serial3"] }
  ] }]
When batchPublish is called with a single BatchPublishSpec publishing three messages to channel_name
And result.results[0] is parsed into BatchPublishSuccessResult
Then result.results[0].serials equals ["serial1", null, "serial3"]
And the null indicates the second message was discarded due to conflation
```

## BPF - BatchPublishFailureResult Structure

**Spec requirement:** BatchPublishFailureResult defines the structure of failed batch publish responses (BPF2a, BPF2b).

### BPF2a - channel field contains failed channel name

**Test ID**: `rest/unit/BPF2a/failure-channel-name-0`

**Spec requirement:** The channel field contains the name of the channel that failed.

```pseudo
channel_name = "test-BPF2a-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and a failure:
  [{ "successCount": 0, "failureCount": 1, "results": [
    {
      "channel": channel_name,
      "error": { "code": 40160, "statusCode": 401, "message": "Not permitted" }
    }
  ] }]
When batchPublish is called with a single BatchPublishSpec for channel_name
And result.results[0] is parsed into BatchPublishFailureResult
Then result.results[0].channel equals channel_name
```

### BPF2b - error contains ErrorInfo for failure reason

**Test ID**: `rest/unit/BPF2b/failure-error-info-0`

**Spec requirement:** The error field contains an ErrorInfo object with code, statusCode, and message.

```pseudo
channel_name = "test-BPF2b-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 201 and a detailed error:
  [{ "successCount": 0, "failureCount": 1, "results": [
    {
      "channel": channel_name,
      "error": {
        "code": 40160,
        "statusCode": 401,
        "message": "Channel operation not permitted",
        "href": "https://help.ably.io/error/40160"
      }
    }
  ] }]
When batchPublish is called with a single BatchPublishSpec for channel_name
And result.results[0] is parsed into BatchPublishFailureResult
Then result.results[0].error is an ErrorInfo
And result.results[0].error.code equals 40160
And result.results[0].error.statusCode equals 401
And result.results[0].error.message contains "not permitted"
```

## BatchResult - Mixed Success and Failure

**Spec requirement:** Batch publish responses can contain a mix of success and failure results, one per channel.

### BatchResult1 - Partial success with mixed results

**Test ID**: `rest/unit/RSC22c/partial-success-mixed-results-0`

**Spec requirement:** A batch publish can succeed for some channels and fail for others.

```pseudo
channel_name_allowed = "test-BatchResult1-allowed-${random_id()}"
channel_name_restricted = "test-BatchResult1-restricted-${random_id()}"

Given a REST client with mock HTTP
And a BatchPublishSpec with channels: [channel_name_allowed, channel_name_restricted]
And the mock responds with HTTP 201 and mixed results in one envelope:
  [
    {
      "successCount": 1,
      "failureCount": 1,
      "results": [
        { "channel": channel_name_allowed, "messageId": "msg1", "serials": ["s1"] },
        { "channel": channel_name_restricted, "error": { "code": 40160, ... } }
      ]
    }
  ]
When batchPublish is called
Then the BatchResult contains both results
And result.results[0] is a BatchPublishSuccessResult
And result.results[1] is a BatchPublishFailureResult
```

### BatchResult2 - Distinguishing success from failure results

**Test ID**: `rest/unit/RSC22c/distinguish-success-failure-0`

**Spec requirement:** Success and failure results can be distinguished by the presence of messageId/serials vs error fields.

```pseudo
channel_name = "test-BatchResult2-${random_id()}"

Given a BatchResult from batchPublish with mock HTTP
When iterating through results
Then each result can be identified as success or failure:
  - Success results have messageId and serials fields
  - Failure results have error field
```

## Error Handling

**Spec requirement:** Batch publish must validate inputs and properly propagate errors from the server.

### RSC22_Error1 - Invalid BatchPublishSpec rejected

**Test ID**: `rest/unit/RSC22/empty-channels-rejected-0`

**Spec requirement:** Empty channels array must be rejected with a validation error.

```pseudo
Given a REST client with mock HTTP
When batchPublish is called with an empty channels array
Then an error is returned
And the error indicates invalid request
```

### RSC22_Error2 - Empty messages array rejected

**Test ID**: `rest/unit/RSC22/empty-messages-rejected-0`

**Spec requirement:** Empty messages array must be rejected with a validation error.

```pseudo
channel_name = "test-RSC22-Error2-${random_id()}"

Given a REST client with mock HTTP
When batchPublish is called with an empty messages array
Then an error is returned
And the error indicates invalid request
```

### RSC22_Error3 - Server error returns AblyException

**Test ID**: `rest/unit/RSC22/server-error-propagated-0`

**Spec requirement:** Server errors (5xx) must be propagated as AblyException with the error code and status.

```pseudo
channel_name = "test-RSC22-Error3-${random_id()}"

Given a REST client with mock HTTP
And the mock responds with HTTP 500:
  { "error": { "code": 50000, "statusCode": 500, "message": "Internal error" } }
When batchPublish is called
Then an AblyException is thrown
And exception.code equals 50000
And exception.statusCode equals 500
```

### RSC22_Error4 - Authentication error returns AblyException

**Test ID**: `rest/unit/RSC22/auth-error-propagated-0`

**Spec requirement:** Authentication errors (401) must be propagated as AblyException with the error code and status.

```pseudo
channel_name = "test-RSC22-Error4-${random_id()}"

Given a REST client with invalid credentials and mock HTTP
And the mock responds with HTTP 401:
  { "error": { "code": 40101, "statusCode": 401, "message": "Invalid credentials" } }
When batchPublish is called
Then an AblyException is thrown
And exception.code equals 40101
And exception.statusCode equals 401
```

## Request Headers

**Spec requirement:** Batch publish requests must include standard Ably headers (X-Ably-Version, Ably-Agent, Content-Type).

### RSC22_Headers1 - Standard headers included

**Test ID**: `rest/unit/RSC22/standard-headers-included-0`

**Spec requirement:** All batch publish requests must include standard Ably protocol headers.

```pseudo
channel_name = "test-RSC22-Headers1-${random_id()}"

Given a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests
When batchPublish is called
Then the captured request includes:
  - X-Ably-Version: the CSV2b protocol version (RSC7e), matching pattern "[0-9]+" and at least 5 (see "Server Response Format")
  - Ably-Agent: <library-agent-string>
  - Content-Type: application/json
```

### RSC22_Headers2 - Request ID included when enabled

**Test ID**: `rest/unit/RSC22/request-id-included-0`

**Spec requirement:** When addRequestIds is enabled, a unique request_id query parameter must be included.

```pseudo
channel_name = "test-RSC22-Headers2-${random_id()}"

Given a REST client with addRequestIds: true and mock HTTP
And the mock is configured to capture requests
When batchPublish is called
Then the captured request includes a request_id query parameter
And the request_id is a unique identifier
```

## Large Batch Handling

**Spec requirement:** Batch publish must handle large batches with multiple messages and channels efficiently.

### RSC22_Batch1 - Multiple messages per channel

**Test ID**: `rest/unit/RSC22/multiple-messages-per-channel-0`

**Spec requirement:** A batch can include many messages to be published to a single channel.

```pseudo
channel_name = "test-RSC22-Batch1-${random_id()}"

Given a REST client with mock HTTP configured with useBinaryProtocol: false
And the mock is configured to capture requests
And a BatchPublishSpec with:
  - channels: [channel_name]
  - messages: [100 Message objects]
When batchPublish is called
Then all 100 messages are included in the captured request body
And the mock response confirms all messages were processed
```

### RSC22_Batch2 - Multiple channels with multiple messages

**Test ID**: `rest/unit/RSC22/multiple-channels-multiple-messages-0`

**Spec requirement:** A batch can publish multiple messages to multiple channels (cartesian product).

```pseudo
channel_name_1 = "test-RSC22-Batch2-a-${random_id()}"
channel_name_2 = "test-RSC22-Batch2-b-${random_id()}"
channel_name_3 = "test-RSC22-Batch2-c-${random_id()}"

Given a REST client with mock HTTP
And the mock is configured to respond with HTTP 201 and one envelope holding a result for each channel:
  [
    {
      "successCount": 3,
      "failureCount": 0,
      "results": [
        { "channel": channel_name_1, "messageId": "id1", "serials": ["s1", "s2", "s3"] },
        { "channel": channel_name_2, "messageId": "id2", "serials": ["s4", "s5", "s6"] },
        { "channel": channel_name_3, "messageId": "id3", "serials": ["s7", "s8", "s9"] }
      ]
    }
  ]
And a BatchPublishSpec with:
  - channels: [channel_name_1, channel_name_2, channel_name_3]
  - messages: [msg1, msg2, msg3]
When batchPublish is called
Then the batch publishes all 3 messages to all 3 channels (9 total publications)
And the result contains 3 BatchPublishSuccessResult entries (one per channel)
```
