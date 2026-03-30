# RealtimeClient Request Tests

Spec points: `RTC9`

## Test Type
Unit test with mocked HTTP client

---

## RTC9 - RealtimeClient#request proxies to RestClient#request

**Spec requirement:** `RealtimeClient#request` is a wrapper around `RestClient#request` (see RSC19) delivered in an idiomatic way for the realtime library.

`RealtimeClient#request` is a direct proxy to `RestClient#request`. The tests in `uts/test/rest/unit/request.md` (covering RSC19) should be used to test a `RealtimeClient` instance in place of a `RestClient` instance. All the same behaviour, parameters, and return types apply.
