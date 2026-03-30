# UTS Test Spec Completion Status

This matrix lists all spec items from the [Ably features spec](../../specification/md/features.md) and indicates which have a UTS test specification.

**Legend:**
- **Yes** — UTS test spec exists covering this item
- **Partial** — some sub-items covered, others not
- *blank* — no UTS test spec exists

---

## Specification and Protocol Versions

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| CSV1–CSV2 | Specification & protocol versions | Information only |

## Client Library Endpoint Configuration

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| REC1 | Primary domain determination (REC1a–REC1d2) | Yes — `rest/unit/fallback.md` |
| REC2 | Fallback domains determination (REC2a–REC2c6) | Yes — `rest/unit/fallback.md` |
| REC3 | Connectivity check URL (REC3a–REC3b) | Yes — `rest/unit/fallback.md` |

---

## REST Client Library

### RestClient

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSC1 | Constructor options (RSC1a–RSC1c) | Yes — `realtime/unit/client/client_options.md`, `realtime/unit/client/realtime_client.md` |
| RSC2 | Logger default | Yes — `rest/unit/logging.md` |
| RSC3 | Log level configuration | Yes — `rest/unit/logging.md` |
| RSC4 | Custom logger | Yes — `rest/unit/logging.md` |
| RSC5 | Auth object attribute | Yes — `rest/unit/rest_client.md` |
| RSC6 | Stats function (RSC6a–RSC6b4) | Yes — `rest/unit/stats.md`, `rest/integration/time_stats.md` |
| RSC7 | HTTP request headers (RSC7a–RSC7d7) | Yes — `rest/unit/rest_client.md` |
| RSC8 | Protocol support (RSC8a–RSC8e2) | Yes — `rest/unit/rest_client.md` |
| RSC9 | Auth usage for authentication | Information only |
| RSC10 | Token error retry handling | Yes — `rest/unit/auth/token_renewal.md`, `rest/integration/auth.md` |
| RSC13 | Connection and request timeouts | Yes — `rest/unit/rest_client.md` |
| RSC15 | Host fallback behaviour (RSC15a–RSC15n) | Yes — `rest/unit/fallback.md` |
| RSC16 | Time function | Yes — `rest/unit/time.md`, `rest/integration/time_stats.md` |
| RSC17 | ClientId attribute | Yes — `rest/unit/rest_client.md` |
| RSC18 | TLS configuration | Yes — `rest/unit/rest_client.md`, `rest/unit/time.md` |
| RSC19 | Request function (RSC19a–RSC19f1) | Yes — `rest/unit/request.md` |
| RSC20 | Deprecated exception reporting (RSC20a–RSC20f) |N/A |
| RSC21 | Push object attribute | |
| RSC22 | BatchPublish (RSC22a–RSC22d) | Yes — `rest/unit/batch_publish.md` |
| RSC23 | Deleted | N/A |
| RSC24 | BatchPresence | Yes — `rest/unit/batch_presence.md`, `rest/integration/batch_presence.md` |
| RSC25 | Request endpoint | Yes — `rest/unit/request_endpoint.md` |
| RSC26 | CreateWrapperSDKProxy (RSC26a–RSC26c) | |

### Auth

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSA1 | Basic Auth requires HTTPS | Yes — `rest/unit/auth/auth_scheme.md` |
| RSA2 | Basic Auth default | Yes — `rest/unit/auth/auth_scheme.md` |
| RSA3 | Token Auth support (RSA3a–RSA3d) | Yes — `rest/unit/auth/auth_scheme.md` |
| RSA4 | Token Auth selection logic (RSA4a–RSA4g) | Partial — `rest/unit/auth/auth_scheme.md` covers RSA4, RSA4b; `rest/unit/auth/token_renewal.md` covers RSA4b4; `realtime/unit/auth/connection_auth_test.md` covers RSA4; `realtime/unit/connection/error_reason_test.md` covers RSA4c1, RSA4d |
| RSA5 | TTL for tokens | Yes — `rest/unit/auth/token_request_params.md`, `rest/integration/auth.md` |
| RSA6 | Capability JSON | Yes — `rest/unit/auth/token_request_params.md`, `rest/integration/auth.md` |
| RSA7 | ClientId and authenticated clients (RSA7a–RSA7e2) | Partial — `rest/unit/auth/client_id.md` covers RSA7, RSA7a–RSA7c; `realtime/integration/auth.md` covers RSA7 |
| RSA8 | RequestToken function (RSA8a–RSA8g) | Partial — `rest/unit/auth/auth_callback.md` covers RSA8c, RSA8d; `realtime/unit/auth/connection_auth_test.md` covers RSA8d; `rest/integration/auth.md` covers RSA8; `realtime/integration/auth.md` covers RSA8 |
| RSA9 | CreateTokenRequest (RSA9a–RSA9i) | Partial — `rest/integration/auth.md` covers RSA9 |
| RSA10 | Authorize function (RSA10a–RSA10l) | Yes — `rest/unit/auth/authorize.md` |
| RSA11 | Base64 encoded API key | Yes — `rest/unit/auth/auth_scheme.md` (with RSA2) |
| RSA12 | Auth#clientId attribute (RSA12a–RSA12b) | Yes — `rest/unit/auth/client_id.md` |
| RSA14 | Error when token auth selected without token | Yes — `rest/unit/auth/token_renewal.md`, `rest/integration/auth.md` |
| RSA15 | ClientId validation (RSA15a–RSA15c) | Yes — `rest/unit/auth/client_id.md`, `realtime/integration/auth.md` (RSA15c Realtime case) |
| RSA16 | TokenDetails attribute (RSA16a–RSA16d) | Yes — `rest/unit/auth/token_details.md` |
| RSA17 | RevokeTokens (RSA17a–RSA17g) | Yes — `rest/unit/auth/revoke_tokens.md`, `rest/integration/revoke_tokens.md` |

### Channels (REST)

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSN1–RSN4 | REST channels collection (RSN1–RSN4c) | Yes — `rest/unit/channels_collection.md` |

### RestChannel

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSL1 | Publish function (RSL1a–RSL1n1) | Yes — `rest/unit/channel/publish.md`, `rest/integration/publish.md` |
| RSL1k | Idempotent publishing (RSL1k1–RSL1k5) | Yes — `rest/unit/channel/idempotency.md` |
| RSL2 | History function (RSL2a–RSL2b3) | Yes — `rest/unit/channel/history.md`, `rest/integration/history.md` |
| RSL3 | Presence attribute | Yes — `rest/unit/presence/rest_presence.md` (with RSP1a) |
| RSL4 | Message encoding (RSL4a–RSL4d4) | Yes — `rest/unit/encoding/message_encoding.md` |
| RSL5 | Message encryption (RSL5a–RSL5c) | |
| RSL6 | Message decoding (RSL6a–RSL6b) | Yes — `rest/unit/encoding/message_encoding.md` |
| RSL7 | SetOptions function | Yes — `rest/unit/channel/rest_channel_attributes.md` |
| RSL8 | Status function (RSL8a) | Yes — `rest/unit/channel/rest_channel_attributes.md` |
| RSL9 | Name attribute | Yes — `rest/unit/channel/rest_channel_attributes.md` |
| RSL10 | Annotations attribute | |
| RSL11 | GetMessage function (RSL11a–RSL11c) | |
| RSL14 | GetMessageVersions (RSL14a–RSL14c) | |
| RSL15 | UpdateMessage/DeleteMessage/AppendMessage (RSL15a–RSL15f) | |

### Plugins

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| PC1–PC5 | Plugin architecture, VCDiff, Objects | Partial — `realtime/unit/channels/channel_delta_decoding.md` covers PC3, PC3a; `realtime/integration/delta_decoding_test.md` covers PC3 |
| PT1–PT2 | PluginType enum | |
| VD1–VD2 | VCDiffDecoder | Partial — `realtime/unit/helpers/mock_vcdiff.md` references VD2a |

### RestPresence

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSP1 | Associated with single channel | Yes — `rest/unit/presence/rest_presence.md`, `rest/integration/presence.md` |
| RSP2 | No presence registration via REST | Information only   |
| RSP3 | Get function (RSP3a–RSP3a3) | Yes — `rest/unit/presence/rest_presence.md`, `rest/integration/presence.md` |
| RSP4 | History function (RSP4a–RSP4b3) | Yes — `rest/unit/presence/rest_presence.md`, `rest/integration/presence.md` |
| RSP5 | Presence message decoding | Yes — `rest/unit/presence/rest_presence.md`, `rest/integration/presence.md` |

### Encryption

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSE1 | Crypto::getDefaultParams (RSE1a–RSE1e) | |
| RSE2 | Crypto::generateRandomKey (RSE2a–RSE2b) | |

### RestAnnotations

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSAN1–RSAN3 | Annotations publish/delete/get | |

### Forwards Compatibility (REST)

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSF1 | Robustness principle | |

---

## Realtime Client Library

### RealtimeClient

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTC1 | ClientOptions (RTC1a–RTC1f1) | Yes — `realtime/unit/client/realtime_client.md` |
| RTC2 | Connection object attribute | Yes — `realtime/unit/client/realtime_client.md` |
| RTC3 | Channels object attribute | Yes — `realtime/unit/client/realtime_client.md` |
| RTC4 | Auth object attribute (RTC4a) | Yes — `realtime/unit/client/realtime_client.md` |
| RTC5 | Stats function (RTC5a–RTC5b) | Yes — `realtime/unit/client/realtime_stats.md` (proxies to RSC6 tests) |
| RTC6 | Time function (RTC6a) | Yes — `realtime/unit/client/realtime_time.md` (proxies to RSC16 tests) |
| RTC7 | Uses configured timeouts | Yes — `realtime/unit/client/realtime_timeouts.md` |
| RTC8 | Authorize function for realtime (RTC8a–RTC8c) | Yes — `realtime/unit/auth/realtime_authorize.md`, `realtime/integration/auth.md` |
| RTC9 | Request function | Yes — `realtime/unit/client/realtime_request.md` (proxies to RSC19 tests) |
| RTC10–RTC11 | Deleted | N/A |
| RTC12 | Same constructors as RestClient | Yes — `realtime/unit/client/realtime_client.md` |
| RTC13 | Push object attribute | |
| RTC14 | CreateWrapperSDKProxy (RTC14a–RTC14c) | |
| RTC15 | Connect function (RTC15a) | Yes — `realtime/unit/client/realtime_client.md` |
| RTC16 | Close function (RTC16a) | Yes — `realtime/unit/client/realtime_client.md` |
| RTC17 | ClientId attribute (RTC17a) | Yes — `realtime/unit/client/realtime_client.md` |

### Connection

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTN1 | Uses websocket connection | Information only |
| RTN2 | Default host and query string params (RTN2a–RTN2g) | Partial — `realtime/unit/auth/connection_auth_test.md` covers RTN2e |
| RTN3 | AutoConnect option | Yes — `realtime/unit/connection/auto_connect_test.md` |
| RTN4 | Connection event emission (RTN4a–RTN4i) | Partial — `realtime/integration/connection_lifecycle_test.md` covers RTN4b, RTN4c; `realtime/unit/connection/update_events_test.md` covers RTN4h |
| RTN5 | Concurrency test (50+ clients) | |
| RTN6 | Successful connection definition | Information only|
| RTN7 | ACK and NACK handling (RTN7a–RTN7e) | Yes — `realtime/unit/channels/channel_publish.md` covers RTN7a, RTN7b (via RTL6j tests), RTN7d, RTN7e |
| RTN8 | Connection#id attribute (RTN8a–RTN8c) | Yes — `realtime/unit/connection/connection_id_key_test.md` |
| RTN9 | Connection#key attribute (RTN9a–RTN9c) | Yes — `realtime/unit/connection/connection_id_key_test.md` |
| RTN11 | Connect function (RTN11a–RTN11f) | Partial — `realtime/integration/connection_lifecycle_test.md` covers RTN11; `realtime/unit/connection/error_reason_test.md` covers RTN11d |
| RTN12 | Close function (RTN12a–RTN12f) | Partial — `realtime/integration/connection_lifecycle_test.md` covers RTN12, RTN12a |
| RTN13 | Ping function (RTN13a–RTN13e) | Yes — `realtime/unit/connection/connection_ping_test.md` |
| RTN14 | Connection opening failures (RTN14a–RTN14g) | Yes — `realtime/unit/connection/connection_open_failures_test.md` |
| RTN15 | Connection failures when CONNECTED (RTN15a–RTN15j) | Yes — `realtime/unit/connection/connection_failures_test.md` |
| RTN16 | Connection recovery (RTN16a–RTN16m1) | Partial — `realtime/unit/connection/error_reason_test.md` covers RTN16e |
| RTN17 | Domain selection and fallback (RTN17a–RTN17j) | Yes — `realtime/unit/connection/fallback_hosts_test.md` |
| RTN19 | Transport state side effects (RTN19a–RTN19b) | Yes — `realtime/unit/channels/channel_publish.md` covers RTN19a, RTN19a2, RTN19b |
| RTN20 | OS network change handling (RTN20a–RTN20c) | |
| RTN21 | ConnectionDetails override defaults | Partial — `realtime/unit/connection/update_events_test.md` covers RTN21; `realtime/integration/connection_lifecycle_test.md` covers RTN21 |
| RTN22 | Re-authentication request handling (RTN22a) | Yes — `realtime/unit/connection/server_initiated_reauth_test.md` |
| RTN23 | Heartbeats (RTN23a–RTN23b) | Yes — `realtime/unit/connection/heartbeat_test.md` |
| RTN24 | UPDATE event on CONNECTED while connected | Yes — `realtime/unit/connection/update_events_test.md` |
| RTN25 | Connection#errorReason attribute | Yes — `realtime/unit/connection/error_reason_test.md` |
| RTN26 | Connection#whenState function (RTN26a–RTN26b) | Yes — `realtime/unit/connection/when_state_test.md` |
| RTN27 | Connection state machine (RTN27a–RTN27h) | Partial — `realtime/unit/auth/connection_auth_test.md` covers RTN27b |

### Channels (Realtime)

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTS1 | Channels collection accessible via RealtimeClient | Yes — `realtime/unit/channels/channels_collection.md` |
| RTS2 | Methods to check existence and iterate | Yes — `realtime/unit/channels/channels_collection.md` |
| RTS3 | Get function (RTS3a–RTS3c1) | Yes — `realtime/unit/channels/channels_collection.md` (RTS3a), `realtime/unit/channels/channel_options.md` (RTS3b, RTS3c, RTS3c1) |
| RTS4 | Release function (RTS4a) | Yes — `realtime/unit/channels/channels_collection.md` |
| RTS5 | GetDerived function (RTS5a–RTS5a2) | Yes — `realtime/unit/channels/channel_options.md` |

### RealtimeChannel

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTL1 | Message and presence processing | Information only |
| RTL2 | Channel event emission (RTL2a–RTL2i) | Yes — `realtime/unit/channels/channel_state_events.md` |
| RTL3 | Connection state side effects (RTL3a–RTL3e) | Yes — `realtime/unit/channels/channel_connection_state.md` |
| RTL4 | Attach function (RTL4a–RTL4m) | Yes — `realtime/unit/channels/channel_attach.md` |
| RTL5 | Detach function (RTL5a–RTL5l) | Yes — `realtime/unit/channels/channel_detach.md` |
| RTL6 | Publish function (RTL6a–RTL6k) | Yes — `realtime/unit/channels/channel_publish.md` |
| RTL7 | Subscribe function (RTL7a–RTL7h) | Yes — `realtime/unit/channels/channel_subscribe.md` |
| RTL8 | Unsubscribe function (RTL8a–RTL8c) | Yes — `realtime/unit/channels/channel_subscribe.md` |
| RTL9 | Presence attribute (RTL9a) | Yes — `realtime/unit/presence/realtime_presence_channel_state.md` |
| RTL10 | History function (RTL10a–RTL10d) | Yes — `realtime/unit/channels/channel_history.md` covers RTL10a, RTL10b, RTL10c (proxies to RSL2 tests); `realtime/integration/channel_history_test.md` covers RTL10d |
| RTL11 | Channel state effect on presence (RTL11a) | Yes — `realtime/unit/presence/realtime_presence_channel_state.md` |
| RTL12 | Additional ATTACHED message handling | Yes — `realtime/unit/channels/channel_additional_attached.md` |
| RTL13 | Server-initiated DETACHED handling (RTL13a–RTL13c) | Yes — `realtime/unit/channels/channel_server_initiated_detach.md` |
| RTL14 | ERROR message handling | Yes — `realtime/unit/channels/channel_error.md` |
| RTL15 | Channel#properties attribute (RTL15a–RTL15b1) | Yes — `realtime/unit/channels/channel_properties.md` |
| RTL16 | SetOptions function (RTL16a) | Yes — `realtime/unit/channels/channel_options.md` |
| RTL17 | No messages outside ATTACHED state | Yes — `realtime/unit/channels/channel_subscribe.md` |
| RTL18 | Vcdiff decoding failure recovery (RTL18a–RTL18c) | Yes — `realtime/unit/channels/channel_delta_decoding.md`, `realtime/integration/delta_decoding_test.md` |
| RTL19 | Base payload storage for vcdiff (RTL19a–RTL19c) | Yes — `realtime/unit/channels/channel_delta_decoding.md`, `realtime/integration/delta_decoding_test.md` |
| RTL20 | Last message ID storage | Yes — `realtime/unit/channels/channel_delta_decoding.md`, `realtime/integration/delta_decoding_test.md` |
| RTL21 | Message ordering in arrays | Yes — `realtime/unit/channels/channel_delta_decoding.md` |
| RTL22 | Message filtering (RTL22a–RTL22d) | |
| RTL23 | Name attribute | Yes — `realtime/unit/channels/channel_attributes.md` |
| RTL24 | ErrorReason attribute | Yes — `realtime/unit/channels/channel_attributes.md` |
| RTL25 | WhenState function (RTL25a–RTL25b) | Yes — `realtime/unit/channels/channel_when_state_test.md` |
| RTL26 | Annotations attribute | |
| RTL27 | Objects attribute (RTL27a–RTL27b) | |
| RTL28 | GetMessage function | |
| RTL31 | GetMessageVersions function | |
| RTL32 | UpdateMessage/DeleteMessage/AppendMessage (RTL32a–RTL32e) | |

### RealtimePresence

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTP1 | HAS_PRESENCE flag and SYNC | Yes — `realtime/unit/presence/realtime_presence_channel_state.md` |
| RTP2 | PresenceMap maintenance (RTP2a–RTP2h2) | Yes — `realtime/unit/presence/presence_map.md` |
| RTP4 | Large member count test | Yes — `realtime/unit/presence/realtime_presence_enter.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP5 | Channel state side effects (RTP5a–RTP5f) | Yes — `realtime/unit/presence/realtime_presence_channel_state.md` |
| RTP6 | Subscribe function (RTP6a–RTP6e) | Yes — `realtime/unit/presence/realtime_presence_subscribe.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP7 | Unsubscribe function (RTP7a–RTP7c) | Yes — `realtime/unit/presence/realtime_presence_subscribe.md` |
| RTP8 | Enter function (RTP8a–RTP8j) | Yes — `realtime/unit/presence/realtime_presence_enter.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP9 | Update function (RTP9a–RTP9e) | Yes — `realtime/unit/presence/realtime_presence_enter.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP10 | Leave function (RTP10a–RTP10e) | Yes — `realtime/unit/presence/realtime_presence_enter.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP11 | Get function (RTP11a–RTP11d) | Yes — `realtime/unit/presence/realtime_presence_get.md`, `realtime/integration/presence_lifecycle_test.md` |
| RTP12 | History function (RTP12a–RTP12d) | Yes — `realtime/unit/presence/realtime_presence_history.md` |
| RTP13 | SyncComplete attribute | Yes — `realtime/unit/presence/realtime_presence_channel_state.md` |
| RTP14 | EnterClient function (RTP14a–RTP14d) | Yes — `realtime/unit/presence/realtime_presence_enter.md` |
| RTP15 | EnterClient/UpdateClient/LeaveClient (RTP15a–RTP15f) | Yes — `realtime/unit/presence/realtime_presence_enter.md` |
| RTP16 | Connection state conditions (RTP16a–RTP16c) | Yes — `realtime/unit/presence/realtime_presence_enter.md` |
| RTP17 | Internal PresenceMap (RTP17a–RTP17j) | Partial — `realtime/unit/presence/local_presence_map.md` covers RTP17, RTP17b, RTP17h; `realtime/unit/presence/realtime_presence_reentry.md` covers RTP17a, RTP17e, RTP17g, RTP17g1, RTP17i |
| RTP18 | Server-initiated sync (RTP18a–RTP18c) | Yes — `realtime/unit/presence/presence_sync.md` |
| RTP19 | PresenceMap cleanup on sync (RTP19a) | Yes — `realtime/unit/presence/presence_sync.md`, `realtime/unit/presence/realtime_presence_channel_state.md` |

### RealtimeAnnotations

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTAN1–RTAN5 | Annotations publish/delete/get/subscribe/unsubscribe | |

### EventEmitter

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTE1–RTE6 | EventEmitter interface (on/once/off/emit) | |

### Incremental Backoff and Jitter

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTB1 | Retry timeout calculation (RTB1a–RTB1b) | |

### Forwards Compatibility (Realtime)

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RTF1 | Robustness principle | |

### Wrapper SDK Proxy Client

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| WP1–WP7 | Wrapper SDK proxy client | |

---

## Push Notifications

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| RSH1 | Push#admin object (RSH1a–RSH1c5) | |
| RSH2 | Platform-specific push operations (RSH2a–RSH2e) | |
| RSH3 | Activation state machine (RSH3a–RSH3g3) | |
| RSH4–RSH5 | Event queueing and sequential handling | |
| RSH6 | Push device authentication (RSH6a–RSH6b) | |
| RSH7 | Push channels (RSH7a–RSH7e) | |
| RSH8 | LocalDevice (RSH8a–RSH8k2) | |

---

## Types

### Data Types

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| TM1–TM8 | Message (TM1–TM8a1) | Partial — `rest/unit/types/message_types.md` covers TM1–TM5; `realtime/unit/channels/message_field_population.md` covers TM2a, TM2c, TM2f (realtime field population) |
| DE1–DE2 | DeltaExtras | |
| TP1–TP5 | PresenceMessage | Yes — `rest/unit/types/presence_message_types.md` |
| OM1–OM5 | ObjectMessage | |
| OOP1–OOP5 | ObjectOperation | |
| OST1–OST3 | ObjectState | |
| OMO1–OMO3 | ObjectsMapOp | |
| OCO1–OCO3 | ObjectsCounterOp | |
| OMP1–OMP4 | ObjectsMap | |
| OCN1–OCN3 | ObjectsCounter | |
| OME1–OME3 | ObjectsMapEntry | |
| OD1–OD5 | ObjectData | |
| TAN1–TAN3 | Annotation | |
| TR1–TR4 | ProtocolMessage | |
| TG1–TG7 | PaginatedResult | Yes — `rest/unit/types/paginated_result.md`, `rest/integration/pagination.md` |
| HP1–HP8 | HttpPaginatedResponse | Yes — `rest/unit/request.md` |
| TE1–TE6 | TokenRequest | Yes — `rest/unit/types/token_types.md` |
| TD1–TD7 | TokenDetails | Yes — `rest/unit/types/token_types.md` |
| TN1–TN3 | Token string | |
| AD1–AD2 | AuthDetails | |
| TS1–TS14 | Stats | |
| TI1–TI5 | ErrorInfo | Yes — `rest/unit/types/error_types.md` |
| TA1–TA5 | ConnectionStateChange | |
| TH1–TH6 | ChannelStateChange | Yes — `realtime/unit/channels/channel_state_events.md` |
| TC1–TC2 | Capability | |
| CD1–CD2 | ConnectionDetails | |
| CP1–CP2 | ChannelProperties | |
| CHD1–CHD2, CHS1–CHS2, CHO1–CHO2, CHM1–CHM2 | Channel status types | |
| BAR1–BAR2 | BatchResult | Partial — `rest/unit/batch_presence.md` covers BAR2 |
| BSP1–BSP2 | BatchPublishSpec | |
| BPR1–BPR2, BPF1–BPF2 | BatchPublish result types | |
| BGR1–BGR2, BGF1–BGF2 | BatchPresence result types | Yes — `rest/unit/batch_presence.md`, `rest/integration/batch_presence.md` |
| PBR1–PBR2 | PublishResult | Yes — `realtime/unit/channels/channel_publish.md` |
| UDR1–UDR2 | UpdateDeleteResult | |
| TRT1–TRT2, TRS1–TRS2, TRF1–TRF2 | TokenRevocation types | Yes — `rest/unit/auth/revoke_tokens.md` |
| MFI1–MFI2 | MessageFilter | |
| REX1–REX2 | ReferenceExtras | |

### Option Types

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| TO1–TO3 | ClientOptions | Yes — `rest/unit/types/options_types.md` |
| TK1–TK6 | TokenParams | Yes — `rest/unit/types/token_types.md` |
| AO1–AO2 | AuthOptions | Yes — `rest/unit/types/options_types.md` |
| TB1–TB4 | ChannelOptions | Yes — `realtime/unit/channels/channel_options.md` |
| DO1–DO2 | DeriveOptions | Yes — `realtime/unit/channels/channel_options.md` |
| TZ1–TZ2 | CipherParams | |
| CO1–CO2 | CipherParamOptions | |
| WPO1–WPO2 | WrapperSDKProxyOptions | |

### Push Notification Types

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| PCS1–PCS5 | PushChannelSubscription | |
| PCD1–PCD7 | DeviceDetails | |
| PCP1–PCP4 | DevicePushDetails | |

### Client Library Introspection

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| CR1–CR3 | ClientInformation | |

### Client Library Defaults

| Spec item | Description | UTS test spec |
|-----------|-------------|---------------|
| DF1 | Default values (DF1a–DF1b) | |

---

## Summary

| Area | Spec groups | With UTS spec | Coverage |
|------|-------------|---------------|----------|
| **Endpoint config** (REC) | 3 | 3 | Full |
| **REST client** (RSC) | 18 | 15 | Partial |
| **REST auth** (RSA) | 15 | 15 | Full |
| **REST channels** (RSN) | 4 | 0 | None |
| **REST channel** (RSL) | 13 | 10 | Partial |
| **REST presence** (RSP) | 5 | 4 | Mostly |
| **REST encryption** (RSE) | 2 | 0 | None |
| **REST annotations** (RSAN) | 3 | 0 | None |
| **Realtime client** (RTC) | 14 | 13 | Partial |
| **Connection** (RTN) | 23 | 18 | Partial |
| **Realtime channels** (RTS) | 5 | 5 | Full |
| **Realtime channel** (RTL) | 24 | 23 | Partial |
| **Realtime presence** (RTP) | 15 | 15 | Full |
| **Realtime annotations** (RTAN) | 5 | 0 | None |
| **EventEmitter** (RTE) | 6 | 0 | None |
| **Backoff/jitter** (RTB) | 1 | 0 | None |
| **Wrapper SDK** (WP) | 7 | 0 | None |
| **Push notifications** (RSH) | 8 | 0 | None |
| **Plugins** (PC/PT/VD) | 3 | 2 | Partial |
| **Data types** | 30 | 9 | Partial |
| **Option types** | 8 | 5 | Partial |
| **Push types** | 3 | 0 | None |
| **Introspection** (CR) | 1 | 0 | None |
| **Defaults** (DF) | 1 | 0 | None |
| **Compatibility** (RSF/RTF) | 2 | 0 | None |
