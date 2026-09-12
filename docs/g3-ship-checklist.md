# G3 — the ship checklist, executed

| | |
| --- | --- |
| **Gate** | G3 · launch |
| **Owner** | Amit Singh (sole contributor, [amendment 001](../../plan-amendment-001-local-hybrid.md)) |
| **Checklist** | [month-3-task-breakdown.md §1.2](../../month-3-task-breakdown.md) — E1–E16 |
| **Status** | ⏳ **in progress** — 7 closed, 4 deleted by ADR-003, 5 open |
| **Last executed** | 12 Sep 2026 (W5, ahead of W12) |

> **This file exists because C15.1 lists the rows and no task executed them.** The Month-3
> breakdown's own §1.3 says three rows cannot close and one has no owner at all, and that
> *"discovering that on the last day converts a clean gate into an argument"*. So it is
> executed early and re-executed at G3, and every open row below carries an owner.

**The launch branch is not yet taken.** The reviewer takes it at the end of W10; all three
branches ship, and G3 has no failure outcome.

## The rows

| # | Criterion | State | Evidence |
| - | --- | --- | --- |
| **E1** | Read-only endpoints serve with **zero LLM calls**, key removed | ⏳ **partial** | `make smoke` starts a real server with `OPENAI_API_KEY` stripped and runs 16 checks; `test_the_cached_read_path_makes_no_model_call` replaces both provider entry points with something that raises. **Not green**: the cache holds 2 of 42 reports and both are stale. Closes with E4 |
| **E2** | Live re-run end to end, SSE, every degraded branch reachable | ❌ **not built** | `POST /api/runs` exists, allowlisted, rate-limited and breaker-checked. **There is no SSE and there will not be** — ADR-003 made this a static export with no server to stream from, and M3-1b is marked droppable. Every *degraded branch* is reachable and rendered (FE-8, seven states). See the deviation below |
| **E3** | Redis reachable, and the breaker fails closed without it | ✅ **closed, restated** | [ADR-011](decisions/ADR-011-no-redis.md): there is no Redis, because one process has nothing to coordinate with. The fail-closed *principle* is implemented literally and tested — an unreadable spend file **denies**, a missing one allows. 5 parametrised cases incl. `{"usd": true}` |
| **E4** | Cache warmed **once**, at the shipping pin; every report's `versions` matches the running service | ⏳ **open** | The startup assertion exists and **works** — `assert_fresh` refuses to start on a stale cache and names which version moved; `/readyz` reports `stale_reports`. The warm run itself is queued behind the M1-9 measurement (same tier). **This is one of the two rows that carry the month** |
| **E5** | Spend breaker verified by a **forced trip**, reset procedure in the runbook | ✅ **closed** | `make trip-breaker` / `make reset-breaker` go through the real code path. Runbook procedure **P3**. Test: `test_a_forced_trip_denies_the_live_route` |
| **E6** | Auto-rollback demonstrated by a deliberately failed smoke test | ⛔ **deleted** | ADR-003: nothing is deployed, so there is nothing to roll back to. ~0.7 h released |
| **E7** | Live at the custom domain over TLS, incognito + phone | ⛔ **deleted** | ADR-003: no public hostname, no cloud service. The DNS ticket was drafted and correctly never filed |
| **E8** | B4 #8 measured, **both halves**, with n | ⏳ **open** | The cached half has a floor asserted in smoke (every report under 5 s, measured per request). The live half needs E2, which is not being built — so this closes as **cached-half only, with the other half named as not-applicable**, not as a pass |
| **E9** | Calibration page live, **zero hard-coded numbers** | ✅ **closed** | FE-6 + `make calibration-page`, a grep over the component source that fails the build on a numeric literal that is a metric. Every metric currently renders *not yet measured*, which is correct |
| **E10** | Faithfulness panel live, served from committed JSON | ✅ **closed** | FE-5 + `faithfulness/panel.json`, built by `make faithfulness` from S4's records. `make faithfulness-check` in CI. **It publishes 0 of 48** — see [findings](findings.md) |
| **E11** | Soundness never renders without its precision/recall; flags show escalated state | ✅ **closed** | FE-3 and FE-4 render from the frozen report; the fixture gap that let error bars render from `undefined` was found by the components and fixed. I3 holds |
| **E12** | **5 of 5 testers unaided; ≥ 4 of 5 state "fluent ≠ sound"** | 🚫 **blocked — needs people** | No testers booked. **No fallback exists**: B4 #9 is unmeasurable without them. Owner: tech lead. This is the hardest external dependency left in the project |
| **E13** | Runbook **exercised by another team member** | ⏳ **half closed** | Written, and all six procedures were executed before being written (M3-5a's DoD) — two of them failed on first run and both failures are recorded in the runbook itself. **The peer dry-run has no named peer.** Owner: tech lead |
| **E14** | Wheel installs in a clean venv and runs on third-party spans | ✅ **closed** | `make wheel`. Failed on its first run — the JSON Schema was not packaged — and that defect is the argument for the check existing |
| **E15** | Embed snippet + fallback video. **Not a launch gate** | ⛔ **deleted / open** | Embed deleted by ADR-003 (no host, no hostile input path). **The fallback video is not deleted and is not made.** Owner: Lead |
| **E16** | This checklist executed, every open row with an owner and a date | ✅ **closed by this file** | Re-execute at G3 |

## Deviations, stated rather than smoothed over

### E2 — the live re-run is not a slipped task, it is a deleted one

C10.4 budgets M3-1b and FE-8's SSE half against a hosted service that streams progress
while a model runs. ADR-003 deleted the service. What remains is a **static export served
from a laptop**, and there is no process to stream from — so the SSE sequence test has
nothing to test and the progress UI has nothing to display.

**What the plan actually wanted from E2 survives and is built:** every degraded branch is
reachable and rendered. FE-8 shows seven run-level states — failed arm, unannotated arm,
provider-summarised trace, partial trace, escalation capped, budget bound, cached-only —
and all seven are exercised today by `report_degraded.json`. The states were the point; the
transport was the plan's assumption about how a reader would reach them.

> This should be read as **scope deleted by an accepted ADR**, not as scope missed. The
> distinction matters at a gate: one is a decision with a written reason, the other is a
> shortfall.

### E8 — half a measurement, reported as half

B4 #8 has two halves and only one has a system to measure. Reporting a cached p90 and
leaving the live number blank is correct; reporting "B4 #8 met" on the strength of the half
that exists would be the exact failure this project has spent three months refusing.

### E12 and E13 — the two rows no amount of code closes

Both need a human who is not the Lead. Amendment 001 already converted G1's check 10 from
"walk the frontend owner through the fixtures" into "annotate each fixture with the surface
that consumes it", because **Amit cannot walk himself through them** — and the same
substitution is *not* available here:

- **E12** is a measurement *of people*. A tester who is also the author measures the
  author's memory of the design, not whether the design communicates.
- **E13** is a verification that the runbook works for **someone who did not write it**. A
  peer dry-run by its author is a proofread.

If neither closes, the pre-decided action is the one this project keeps taking: **publish
the shortfall as a finding** and name it on the calibration page, rather than quietly
dropping the criterion or lowering it until it passes.

## Open rows, with owners and dates

| Row | Owner | Needs | By |
| --- | --- | --- | --- |
| E1, E4 | Lead | One `make report` pass at the shipping pin, then `make smoke` green | Queued behind the M1-9 measurement |
| E8 | Lead | The cached p90 with n from a warmed smoke run; the live half recorded as n/a with its reason | With E4 |
| **E12** | **Tech lead** | **Five walkthrough testers booked** | **No default exists** |
| **E13** | **Tech lead** | **One peer named for the runbook dry-run** | **No default exists** |
| E15 | Lead | Fallback video — an unedited screen recording (L4) | Before any live demo |
