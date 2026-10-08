# Harness design: <repo name> @ <sha>

## Gap table
| # | Capability | Guide | Status | Evidence | Approach (reuse / wrap / extend / build / n/a) | Builds on | Blocks (module/tier) | Production change? | Size | Acceptance check |
|---|---|---|---|---|---|---|---|---|---|---|
| G-01 | WebSocket transport factory hook | 2.1 | present / partial / missing / n/a | | | | realtime/unit, objects/unit | yes / no | S/M/L | |
| G-02 | HTTP client hook | 2.1 | | | | | rest/unit | | | |
| G-03 | Clock hook (timers, timed waits, async-runtime timers) | 2.1 | | | | | | | | |
| G-04 | Network-monitor hook | 2.1 | | | | | | | | |
| G-05 | Randomness hooks (jitter, host shuffle) | 2.1 | | | | | | | | |
| G-06 | MockHttpClient (+ legacy queue_*) | 2.2, mock_http.md | | | | | | | | |
| G-07 | MockWebSocket (+ alternative API, undocumented members, raw frames, ping) | 2.2, mock_websocket.md | | | | | | | | |
| G-08 | MockVCDiff encoder/decoders | 2.2, mock_vcdiff.md | | | | | | | | |
| G-09 | MockNetworkListener | 2.2 | | | | | | | | |
| G-10 | standard_test_pool.md implementation; plugin options builder | 2.2, standard_test_pool.md | | | | | | | | |
| G-11 | Wait helpers (AWAIT_STATE, poll_until, poll_until_success, process_pending_events, wall-clock wrapper, fake clock driver) | 2.2, 5.6, 5.7 | | | | | | | | |
| G-12 | Thread-safe capture, log sink, assertContainsInOrder, caller-attributed failures | 2.2 | | | | | | | | |
| G-13 | Placement and recommended harness layout (shared / port-only / module helpers); fixture-helper scope documented in the module notes | 2.2 | | | | | | | | |
| G-14 | Harness README with Known gaps; mapping `harness` entry (root, README, per-tier sources and harness-test commands) | 3.1, 3.2 | | | | | | | | |
| G-15 | SandboxApp; ably-common | 2.3 | | | | | */integration | | | |
| G-16 | ProxyManager (pinned, every OS); ProxySession; rule builders; proxy auth | 2.4 | | | | | */proxy | | | |
| G-17 | UTS test target; per-tier selection and filters; one CI home per suite | 2.5 | | | | | | | | |
| G-18 | Concurrency, time, parallelism and visibility models known | 2.6 | | | | | | | | |
| G-19 | Per-tier smoke tests (permanent, in CI, outside generated dirs) | 2.7 | | | | | | | | |
| G-20 | Helper self-tests (common, unit, fake clock, REST, objects, sandbox, proxy) | 2.7 | | | | | | | | |

## Helper-spec symbol maps (one table per helper spec)
### mock_http.md
| Spec symbol (declared or corpus-only) | Native type.member | Approach | Builds on | Notes |
|---|---|---|---|---|
### mock_websocket.md
### mock_vcdiff.md
### standard_test_pool.md
### MockNetworkListener (no helper spec)

## Wait and assertion helpers
| Helper | Native symbol | Approach | Guarantees checked by |
|---|---|---|---|

## Sandbox and proxy
- Sandbox provisioning: …; client targeting (endpoint or hosts): …; suite fixture mapping: …
- Proxy: version …; binaries per OS …; local override …; auth through the proxy …; platform gating …

## Hook proposals (each needs STOP-4 approval)
| Hook | API | Default behaviour | Visibility | Files touched | Installed how | Per-client? | Approved on |
|---|---|---|---|---|---|---|---|

## Placement
- Shared test-support: <dir/target>; port-only harness: <dir/target>; module helpers: <dir per module>

## Tier feasibility
| Module | unit | integration | proxy |
|---|---|---|---|
| rest | ready / after G-.. / not possible: <why> / n/a | | |
| realtime | | | |
| objects | | | |

## Decision at STOP-3
(a) build now: <rows> | (b) plan only | (c) scope to ready tiers — chosen by <user> on <date>; design changes requested: …

## Build log (Phase 3) / plan (option b)
| Order | Row | Work | Acceptance check | Result | Date |
|---|---|---|---|---|---|

## Confirmation at STOP-7
Smoke tests and self-tests per tier (filter, result, CI job): …; updated tier matrix: …; confirmed on <date>
