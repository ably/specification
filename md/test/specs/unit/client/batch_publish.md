# Batch Publish Tests

Tests for `RestClient#batchPublish` (RSC22) and related types (BSP*, BPR*, BPF*).

## RSC22c - batchPublish sends POST to /messages

### RSC22c1 - Single BatchPublishSpec sends POST to /messages

```
Given a REST client
When batchPublish is called with a single BatchPublishSpec:
  - channels: ["channel1", "channel2"]
  - messages: [Message(name: "event", data: "hello")]
Then a POST request is sent to "/messages"
And the request body contains:
  - channels: ["channel1", "channel2"]
  - messages: [{ name: "event", data: "hello" }]
```

### RSC22c2 - Array of BatchPublishSpecs sends POST to /messages

```
Given a REST client
When batchPublish is called with an array of BatchPublishSpecs:
  - BatchPublishSpec(channels: ["ch1"], messages: [Message(name: "e1", data: "d1")])
  - BatchPublishSpec(channels: ["ch2"], messages: [Message(name: "e2", data: "d2")])
Then a POST request is sent to "/messages"
And the request body is an array containing both specs
```

### RSC22c3 - Single spec returns single BatchResult

```
Given a REST client
And the server responds with:
  {
    "channel": "channel1",
    "messageId": "msg123",
    "serials": ["serial1"]
  }
When batchPublish is called with a single BatchPublishSpec
Then a single BatchResult is returned (not an array)
And the result contains the success result for "channel1"
```

### RSC22c4 - Array of specs returns array of BatchResults

```
Given a REST client
And the server responds with an array of results:
  [
    { "channel": "ch1", "messageId": "msg1", "serials": ["s1"] },
    { "channel": "ch2", "messageId": "msg2", "serials": ["s2"] }
  ]
When batchPublish is called with an array of BatchPublishSpecs
Then an array of BatchResults is returned
And each result corresponds to the respective spec
```

### RSC22c5 - Multiple channels in spec produces multiple results

```
Given a REST client
And a BatchPublishSpec with channels: ["ch1", "ch2", "ch3"]
And the server responds with results for each channel
When batchPublish is called
Then the BatchResult contains results for all three channels
```

### RSC22c6 - Messages are encoded according to RSL4

```
Given a REST client
When batchPublish is called with messages containing:
  - String data
  - Binary data (Uint8List/[]byte)
  - JSON object data
Then each message is encoded per RSL4:
  - String: data as-is, no encoding
  - Binary: base64 encoded, encoding: "base64"
  - JSON: JSON stringified, encoding: "json"
```

### RSC22c7 - Request uses correct authentication

```
Given a REST client with token auth
When batchPublish is called
Then the POST request includes Authorization: Bearer <token>
```

```
Given a REST client with basic auth
When batchPublish is called
Then the POST request includes Authorization: Basic <base64(key)>
```

## RSC22d - Idempotent publishing applies RSL1k1

### RSC22d1 - Idempotent IDs generated when enabled

```
Given a REST client with idempotentRestPublishing: true
When batchPublish is called with messages that have no id
Then each message in each BatchPublishSpec has a unique id generated
And the id format follows RSL1k1 (baseId:serial)
```

### RSC22d2 - Each BatchPublishSpec gets separate idempotent base

```
Given a REST client with idempotentRestPublishing: true
When batchPublish is called with multiple BatchPublishSpecs:
  - Spec1: 2 messages
  - Spec2: 3 messages
Then Spec1 messages have ids: "base1:0", "base1:1"
And Spec2 messages have ids: "base2:0", "base2:1", "base2:2"
And base1 != base2
```

### RSC22d3 - Explicit message IDs preserved

```
Given a REST client with idempotentRestPublishing: true
When batchPublish is called with messages that have explicit ids
Then the explicit ids are preserved (not overwritten)
```

### RSC22d4 - Idempotent IDs not generated when disabled

```
Given a REST client with idempotentRestPublishing: false
When batchPublish is called with messages that have no id
Then the messages are sent without id fields
```

## BSP - BatchPublishSpec Structure

### BSP2a - channels is array of strings

```
Given a BatchPublishSpec
When channels is set to ["channel1", "channel2", "channel3"]
Then the serialized spec contains channels as a string array
```

### BSP2b - messages is array of Message objects

```
Given a BatchPublishSpec
When messages contains multiple Message objects with:
  - Message(name: "event1", data: "data1")
  - Message(name: "event2", data: { "key": "value" })
Then the serialized spec contains messages as an array of message objects
And each message is serialized according to TM* rules
```

## BPR - BatchPublishSuccessResult Structure

### BPR2a - channel field contains channel name

```
Given a server response for successful batch publish:
  { "channel": "test-channel", "messageId": "msg123", "serials": ["s1"] }
When the response is parsed into BatchPublishSuccessResult
Then result.channel equals "test-channel"
```

### BPR2b - messageId contains the message ID prefix

```
Given a server response for successful batch publish:
  { "channel": "ch", "messageId": "unique-id-prefix", "serials": ["s1", "s2"] }
When the response is parsed into BatchPublishSuccessResult
Then result.messageId equals "unique-id-prefix"
```

### BPR2c - serials contains array of message serials

```
Given a server response with multiple serials:
  { "channel": "ch", "messageId": "msg", "serials": ["serial1", "serial2", "serial3"] }
When the response is parsed into BatchPublishSuccessResult
Then result.serials equals ["serial1", "serial2", "serial3"]
And serials.length matches the number of messages published
```

### BPR2c1 - serials may contain null for conflated messages

```
Given a server response where some messages were conflated:
  { "channel": "ch", "messageId": "msg", "serials": ["serial1", null, "serial3"] }
When the response is parsed into BatchPublishSuccessResult
Then result.serials equals ["serial1", null, "serial3"]
And the null indicates the second message was discarded due to conflation
```

## BPF - BatchPublishFailureResult Structure

### BPF2a - channel field contains failed channel name

```
Given a server response for failed batch publish:
  {
    "channel": "restricted-channel",
    "error": { "code": 40160, "statusCode": 401, "message": "Not permitted" }
  }
When the response is parsed into BatchPublishFailureResult
Then result.channel equals "restricted-channel"
```

### BPF2b - error contains ErrorInfo for failure reason

```
Given a server response for failed batch publish:
  {
    "channel": "ch",
    "error": {
      "code": 40160,
      "statusCode": 401,
      "message": "Channel operation not permitted",
      "href": "https://help.ably.io/error/40160"
    }
  }
When the response is parsed into BatchPublishFailureResult
Then result.error is an ErrorInfo
And result.error.code equals 40160
And result.error.statusCode equals 401
And result.error.message contains "not permitted"
```

## BatchResult - Mixed Success and Failure

### BatchResult1 - Partial success with mixed results

```
Given a BatchPublishSpec with channels: ["allowed-ch", "restricted-ch"]
And "allowed-ch" succeeds and "restricted-ch" fails
When the server responds with:
  [
    { "channel": "allowed-ch", "messageId": "msg1", "serials": ["s1"] },
    { "channel": "restricted-ch", "error": { "code": 40160, ... } }
  ]
Then the BatchResult contains both results
And result[0] is a BatchPublishSuccessResult
And result[1] is a BatchPublishFailureResult
```

### BatchResult2 - Distinguishing success from failure results

```
Given a BatchResult from batchPublish
When iterating through results
Then each result can be identified as success or failure:
  - Success results have messageId and serials fields
  - Failure results have error field
```

## Error Handling

### RSC22_Error1 - Invalid BatchPublishSpec rejected

```
Given a REST client
When batchPublish is called with an empty channels array
Then an error is returned
And the error indicates invalid request
```

### RSC22_Error2 - Empty messages array rejected

```
Given a REST client
When batchPublish is called with an empty messages array
Then an error is returned
And the error indicates invalid request
```

### RSC22_Error3 - Server error returns AblyException

```
Given a REST client
And the server responds with HTTP 500:
  { "error": { "code": 50000, "statusCode": 500, "message": "Internal error" } }
When batchPublish is called
Then an AblyException is thrown
And exception.code equals 50000
And exception.statusCode equals 500
```

### RSC22_Error4 - Authentication error returns AblyException

```
Given a REST client with invalid credentials
And the server responds with HTTP 401:
  { "error": { "code": 40101, "statusCode": 401, "message": "Invalid credentials" } }
When batchPublish is called
Then an AblyException is thrown
And exception.code equals 40101
And exception.statusCode equals 401
```

## Request Headers

### RSC22_Headers1 - Standard headers included

```
Given a REST client
When batchPublish is called
Then the request includes:
  - X-Ably-Version: 2
  - Ably-Agent: <library-agent-string>
  - Content-Type: application/json
```

### RSC22_Headers2 - Request ID included when enabled

```
Given a REST client with addRequestIds: true
When batchPublish is called
Then the request includes a request_id query parameter
And the request_id is a unique identifier
```

## Large Batch Handling

### RSC22_Batch1 - Multiple messages per channel

```
Given a BatchPublishSpec with:
  - channels: ["ch1"]
  - messages: [100 Message objects]
When batchPublish is called
Then all 100 messages are included in the request body
And the server processes all messages for the channel
```

### RSC22_Batch2 - Multiple channels with multiple messages

```
Given a BatchPublishSpec with:
  - channels: ["ch1", "ch2", "ch3"]
  - messages: [msg1, msg2, msg3]
When batchPublish is called
Then the server publishes all 3 messages to all 3 channels (9 total publications)
And the result contains 3 BatchPublishSuccessResult entries (one per channel)
```
