# RealtimeClient Time Tests

Spec points: `RTC6`, `RTC6a`

## Test Type
Unit test with mocked HTTP client

---

## RTC6 - RealtimeClient#time proxies to RestClient#time

| Spec | Requirement |
|------|-------------|
| RTC6a | Proxy to `RestClient#time` presented with an async or threaded interface as appropriate |

`RealtimeClient#time` is a direct proxy to `RestClient#time`. The tests in `uts/test/rest/unit/time.md` (covering RSC16) should be used to test a `RealtimeClient` instance in place of a `RestClient` instance. All the same behaviour, parameters, and return types apply.
