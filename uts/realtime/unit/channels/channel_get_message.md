# RealtimeChannel GetMessage Tests

Spec points: `RTL28`

## Test Type
Unit test with mocked HTTP client

---

## RTL28 - RealtimeChannel#getMessage is identical to RestChannel#getMessage

**Spec requirement:** `RealtimeChannel#getMessage` function: same as `RestChannel#getMessage`.

`RealtimeChannel#getMessage` uses the same underlying REST endpoint as `RestChannel#getMessage`. The tests in `uts/test/rest/unit/channel/get_message.md` (covering RSL11) should be used to verify that all the same behaviour, parameters, and return types apply when called on a `RealtimeChannel` instance.
