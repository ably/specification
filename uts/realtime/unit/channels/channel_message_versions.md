# RealtimeChannel GetMessageVersions Tests

Spec points: `RTL31`

## Test Type
Unit test with mocked HTTP client

---

## RTL31 - RealtimeChannel#getMessageVersions is identical to RestChannel#getMessageVersions

**Spec requirement:** `RealtimeChannel#getMessageVersions` function: same as `RestChannel#getMessageVersions`.

`RealtimeChannel#getMessageVersions` uses the same underlying REST endpoint as `RestChannel#getMessageVersions`. The tests in `uts/test/rest/unit/channel/message_versions.md` (covering RSL14) should be used to verify that all the same behaviour, parameters, and return types apply when called on a `RealtimeChannel` instance.
