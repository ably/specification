# RealtimeClient Stats Tests

Spec points: `RTC5`, `RTC5a`, `RTC5b`

## Test Type
Unit test with mocked HTTP client

---

## RTC5 - RealtimeClient#stats proxies to RestClient#stats

| Spec | Requirement |
|------|-------------|
| RTC5a | Proxy to `RestClient#stats` presented with an async or threaded interface as appropriate |
| RTC5b | Accepts all the same params as `RestClient#stats` and provides all the same functionality |

`RealtimeClient#stats` is a direct proxy to `RestClient#stats`. The tests in `uts/test/rest/unit/stats.md` (covering RSC6) should be used to test a `RealtimeClient` instance in place of a `RestClient` instance. All the same behaviour, parameters, and return types apply.
