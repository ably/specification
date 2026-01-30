# REST Presence Unit Tests

Tests for `RestPresence` (RSP1-5) with mocked HTTP client.

## RSP1 - RestPresence object associated with channel

### RSP1_1 - Presence accessible via RestChannel#presence

```pseudo
Given a REST client with mocked HTTP
And a channel "test-channel"
When accessing channel.presence
Then a RestPresence object is returned
And the presence object is associated with "test-channel"
```

### RSP1_2 - Same presence object returned for same channel

```pseudo
Given a REST client with mocked HTTP
And a channel = client.channels.get("test-channel")
When accessing channel.presence multiple times
Then the same RestPresence instance is returned each time
```

---

## RSP3 - RestPresence#get

### RSP3_1 - Get sends GET request to presence endpoint

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 1, "clientId": "client1", "data": "hello" },
  { "action": 1, "clientId": "client2", "data": "world" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test-channel").presence.get()

Then mock_http.last_request.method == "GET"
And mock_http.last_request.path == "/channels/test-channel/presence"
And result IS PaginatedResult<PresenceMessage>
And result.items.length == 2
```

### RSP3_2 - Get returns PresenceMessage objects

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "user123",
    "connectionId": "conn456",
    "data": "status data",
    "encoding": null,
    "timestamp": 1234567890000
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items.length == 1
And result.items[0] IS PresenceMessage
And result.items[0].action == PresenceAction.present  # action 1
And result.items[0].clientId == "user123"
And result.items[0].connectionId == "conn456"
And result.items[0].data == "status data"
And result.items[0].timestamp == 1234567890000
```

### RSP3_3 - Get with no members returns empty list

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("empty-channel").presence.get()

Then result.items IS List
And result.items.length == 0
And result.hasNext() == false
```

### RSP3a1_1 - Get with limit parameter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 1, "clientId": "client1" },
  { "action": 1, "clientId": "client2" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get(limit: 50)

Then mock_http.last_request.query_params["limit"] == "50"
```

### RSP3a1_2 - Get limit defaults to 100

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get()

Then "limit" NOT IN mock_http.last_request.query_params
  OR mock_http.last_request.query_params["limit"] == "100"
```

### RSP3a1_3 - Get limit maximum is 1000

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get(limit: 1000)

Then mock_http.last_request.query_params["limit"] == "1000"
```

### RSP3a2_1 - Get with clientId filter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 1, "clientId": "specific-client", "data": "filtered" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get(clientId: "specific-client")

Then mock_http.last_request.query_params["clientId"] == "specific-client"
```

### RSP3a3_1 - Get with connectionId filter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 1, "clientId": "client1", "connectionId": "conn123" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get(connectionId: "conn123")

Then mock_http.last_request.query_params["connectionId"] == "conn123"
```

### RSP3_Combined - Get with multiple filters

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get(
  limit: 25,
  clientId: "user1",
  connectionId: "conn1"
)

Then mock_http.last_request.query_params["limit"] == "25"
And mock_http.last_request.query_params["clientId"] == "user1"
And mock_http.last_request.query_params["connectionId"] == "conn1"
```

---

## RSP4 - RestPresence#history

### RSP4_1 - History sends GET request to presence history endpoint

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 2, "clientId": "client1", "data": "entered" },
  { "action": 4, "clientId": "client1", "data": "left" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test-channel").presence.history()

Then mock_http.last_request.method == "GET"
And mock_http.last_request.path == "/channels/test-channel/presence/history"
And result IS PaginatedResult<PresenceMessage>
```

### RSP4a_1 - History returns PaginatedResult of PresenceMessage

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 2, "clientId": "user1", "data": "d1", "timestamp": 1000 },
  { "action": 3, "clientId": "user1", "data": "d2", "timestamp": 2000 },
  { "action": 4, "clientId": "user1", "data": "d3", "timestamp": 3000 }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.history()

Then result IS PaginatedResult<PresenceMessage>
And result.items.length == 3
And result.items[0].action == PresenceAction.enter   # action 2
And result.items[1].action == PresenceAction.update  # action 3
And result.items[2].action == PresenceAction.leave   # action 4
```

### RSP4b1_1 - History with start parameter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

And start_time = 1609459200000  # 2021-01-01 00:00:00 UTC

When AWAIT client.channels.get("test").presence.history(start: start_time)

Then mock_http.last_request.query_params["start"] == "1609459200000"
```

### RSP4b1_2 - History with end parameter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

And end_time = 1609545600000  # 2021-01-02 00:00:00 UTC

When AWAIT client.channels.get("test").presence.history(end: end_time)

Then mock_http.last_request.query_params["end"] == "1609545600000"
```

### RSP4b1_3 - History with start and end parameters

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

And start_time = 1609459200000
And end_time = 1609545600000

When AWAIT client.channels.get("test").presence.history(
  start: start_time,
  end: end_time
)

Then mock_http.last_request.query_params["start"] == "1609459200000"
And mock_http.last_request.query_params["end"] == "1609545600000"
```

### RSP4b1_4 - History accepts DateTime objects for start/end

```pseudo
# Language-specific: if the language supports DateTime/Date objects,
# they should be accepted and converted to milliseconds since epoch

Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

And start_datetime = DateTime(2021, 1, 1, 0, 0, 0, UTC)  # language-specific

When AWAIT client.channels.get("test").presence.history(start: start_datetime)

Then mock_http.last_request.query_params["start"] == "1609459200000"
```

### RSP4b2_1 - History with direction backwards (default)

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history()

Then "direction" NOT IN mock_http.last_request.query_params
  OR mock_http.last_request.query_params["direction"] == "backwards"
```

### RSP4b2_2 - History with direction forwards

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history(direction: "forwards")

Then mock_http.last_request.query_params["direction"] == "forwards"
```

### RSP4b2_3 - History with direction backwards explicit

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history(direction: "backwards")

Then mock_http.last_request.query_params["direction"] == "backwards"
```

### RSP4b3_1 - History with limit parameter

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history(limit: 50)

Then mock_http.last_request.query_params["limit"] == "50"
```

### RSP4b3_2 - History limit defaults to 100

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history()

Then "limit" NOT IN mock_http.last_request.query_params
  OR mock_http.last_request.query_params["limit"] == "100"
```

### RSP4b3_3 - History limit maximum is 1000

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history(limit: 1000)

Then mock_http.last_request.query_params["limit"] == "1000"
```

### RSP4_Combined - History with all parameters

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history(
  start: 1609459200000,
  end: 1609545600000,
  direction: "forwards",
  limit: 50
)

Then mock_http.last_request.query_params["start"] == "1609459200000"
And mock_http.last_request.query_params["end"] == "1609545600000"
And mock_http.last_request.query_params["direction"] == "forwards"
And mock_http.last_request.query_params["limit"] == "50"
```

---

## RSP5 - Presence message decoding

### RSP5_1 - String data decoded as string

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 1, "clientId": "c1", "data": "plain string data" }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items[0].data == "plain string data"
And result.items[0].data IS String
```

### RSP5_2 - JSON encoded data decoded to object

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "c1",
    "data": "{\"status\":\"online\",\"count\":42}",
    "encoding": "json"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items[0].data IS Object/Map
And result.items[0].data["status"] == "online"
And result.items[0].data["count"] == 42
And result.items[0].encoding == null  # encoding consumed
```

### RSP5_3 - Base64 encoded data decoded to binary

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "c1",
    "data": "SGVsbG8gV29ybGQ=",  # "Hello World" in base64
    "encoding": "base64"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items[0].data IS Binary/Uint8List/[]byte
And result.items[0].data == bytes("Hello World")
And result.items[0].encoding == null  # encoding consumed
```

### RSP5_4 - UTF-8 encoded data decoded correctly

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "c1",
    "data": "SGVsbG8gV29ybGQ=",  # base64 of UTF-8 bytes
    "encoding": "utf-8/base64"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items[0].data == "Hello World"
And result.items[0].data IS String
```

### RSP5_5 - Chained encoding decoded in order

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "c1",
    "data": "eyJrZXkiOiJ2YWx1ZSJ9",  # base64 of {"key":"value"}
    "encoding": "json/base64"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

# Decoding order: base64 first, then json
Then result.items[0].data IS Object/Map
And result.items[0].data["key"] == "value"
```

### RSP5_6 - History messages also decoded

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  {
    "action": 2,
    "clientId": "c1",
    "data": "{\"event\":\"entered\"}",
    "encoding": "json"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.history()

Then result.items[0].data IS Object/Map
And result.items[0].data["event"] == "entered"
```

### RSP5_7 - Cipher decoding with channel options

```pseudo
Given mock_http = MockHttpClient()
And cipher_key = base64_decode("WUP6u0K7MXI5Zeo0VppPwg==")

# Encrypted data for {"secret":"data"}
And encrypted_data = "HO4cYSP8LybPYBPZPHQOtuD53yrD3YV3NBoTEYBh4U0="

And mock_http.queue_response(200, body: [
  {
    "action": 1,
    "clientId": "c1",
    "data": encrypted_data,
    "encoding": "json/utf-8/cipher+aes-128-cbc/base64"
  }
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

And channel = client.channels.get("encrypted", options: RestChannelOptions(
  cipher: CipherParams(key: cipher_key, algorithm: "aes", mode: "cbc")
))

When result = AWAIT channel.presence.get()

Then result.items[0].data IS Object/Map
# Decryption applied based on cipher+aes-128-cbc encoding
```

---

## Pagination

### RSP_Pagination_1 - Get returns paginated result with Link header

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200,
  body: [
    { "action": 1, "clientId": "client1" },
    { "action": 1, "clientId": "client2" }
  ],
  headers: {
    "Link": "</channels/test/presence?page=2>; rel=\"next\""
  },
  content_type: "application/json"
)

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.get()

Then result.items.length == 2
And result.hasNext() == true
```

### RSP_Pagination_2 - Get next page fetches from Link URL

```pseudo
Given mock_http = MockHttpClient()

# First page response
And mock_http.queue_response(200,
  body: [{ "action": 1, "clientId": "client1" }],
  headers: { "Link": "</channels/test/presence?page=2>; rel=\"next\"" },
  content_type: "application/json"
)

# Second page response
And mock_http.queue_response(200,
  body: [{ "action": 1, "clientId": "client2" }],
  content_type: "application/json"
)

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When page1 = AWAIT client.channels.get("test").presence.get()
And page2 = AWAIT page1.next()

Then page1.items[0].clientId == "client1"
And page2.items[0].clientId == "client2"
And page2.hasNext() == false
```

### RSP_Pagination_3 - History pagination works the same

```pseudo
Given mock_http = MockHttpClient()

# First page response
And mock_http.queue_response(200,
  body: [{ "action": 2, "clientId": "c1", "timestamp": 3000 }],
  headers: { "Link": "</channels/test/presence/history?page=2>; rel=\"next\"" },
  content_type: "application/json"
)

# Second page response
And mock_http.queue_response(200,
  body: [{ "action": 4, "clientId": "c1", "timestamp": 1000 }],
  content_type: "application/json"
)

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When page1 = AWAIT client.channels.get("test").presence.history()
And page2 = AWAIT page1.next()

Then page1.items[0].action == PresenceAction.enter
And page2.items[0].action == PresenceAction.leave
```

---

## Error Handling

### RSP_Error_1 - Get with server error throws AblyException

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(500, body: {
  "error": {
    "code": 50000,
    "statusCode": 500,
    "message": "Internal server error"
  }
}, content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When:
  TRY:
    AWAIT client.channels.get("test").presence.get()
    FAIL("Expected exception")
  CATCH AblyException as e:
    ASSERT e.code == 50000
    ASSERT e.statusCode == 500
```

### RSP_Error_2 - History with invalid auth throws AblyException

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(401, body: {
  "error": {
    "code": 40101,
    "statusCode": 401,
    "message": "Invalid credentials"
  }
}, content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "invalid.key:secret",
  httpClient: mock_http
))

When:
  TRY:
    AWAIT client.channels.get("test").presence.history()
    FAIL("Expected exception")
  CATCH AblyException as e:
    ASSERT e.code == 40101
    ASSERT e.statusCode == 401
```

### RSP_Error_3 - Get with channel not found

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(404, body: {
  "error": {
    "code": 40400,
    "statusCode": 404,
    "message": "Channel not found"
  }
}, content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When:
  TRY:
    AWAIT client.channels.get("nonexistent").presence.get()
    FAIL("Expected exception")
  CATCH AblyException as e:
    ASSERT e.code == 40400
    ASSERT e.statusCode == 404
```

---

## Request Headers

### RSP_Headers_1 - Get includes standard headers

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.get()

Then mock_http.last_request.headers["X-Ably-Version"] == "2"
And mock_http.last_request.headers["Ably-Agent"] contains "ably-"
And mock_http.last_request.headers["Accept"] == "application/json"
```

### RSP_Headers_2 - History includes authorization header

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When AWAIT client.channels.get("test").presence.history()

Then mock_http.last_request.headers["Authorization"] starts with "Basic "
```

### RSP_Headers_3 - Request ID included when enabled

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http,
  addRequestIds: true
))

When AWAIT client.channels.get("test").presence.get()

Then "request_id" IN mock_http.last_request.query_params
And mock_http.last_request.query_params["request_id"] IS NOT empty
```

---

## PresenceAction Values

### RSP_Action_1 - All presence actions correctly mapped

```pseudo
Given mock_http = MockHttpClient()
And mock_http.queue_response(200, body: [
  { "action": 0, "clientId": "c1" },  # absent
  { "action": 1, "clientId": "c2" },  # present
  { "action": 2, "clientId": "c3" },  # enter
  { "action": 3, "clientId": "c4" },  # leave
  { "action": 4, "clientId": "c5" }   # update
], content_type: "application/json")

And client = Rest(options: ClientOptions(
  key: "appId.keyId:keySecret",
  httpClient: mock_http
))

When result = AWAIT client.channels.get("test").presence.history()

Then result.items[0].action == PresenceAction.absent
And result.items[1].action == PresenceAction.present
And result.items[2].action == PresenceAction.enter
And result.items[3].action == PresenceAction.leave
And result.items[4].action == PresenceAction.update
```

Note: Action values may vary by SDK. The wire protocol uses:
- 0 = absent
- 1 = present
- 2 = enter
- 3 = leave (some SDKs use 4)
- 4 = update (some SDKs use 3)

Verify against your SDK's specific mapping.
