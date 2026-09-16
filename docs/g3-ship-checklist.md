# G3 — the ship checklist, executed

| | |
| --- | --- |
| **Gate** | G3 · launch |
| **Owner** | Amit Singh (sole contributor, [amendment 001](../../plan-amendment-001-local-hybrid.md)) |
| **Checklist** | [month-3-task-breakdown.md §1.2](../../month-3-task-breakdown.md) — E1–E16 |
| **Status** | ⏳ **in progress** — 9 closed, 4 deleted by ADR-003, 3 open |
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
| **E1** | Read-only endpoints serve with **zero LLM calls**, key removed | ✅ **closed** | `make smoke` starts a real server with `OPENAI_API_KEY` stripped and runs 18 checks; `test_the_cached_read_path_makes_no_model_call` replaces both provider entry points with something that raises. **18/18 green, 12 Sep**, against a real server with `OPENAI_API_KEY` stripped |
| **E2** | Live re-run end to end, SSE, every degraded branch reachable | ❌ **not built** | `POST /api/runs` exists, allowlisted, rate-limited and breaker-checked. **There is no SSE and there will not be** — ADR-003 made this a static export with no server to stream from, and M3-1b is marked droppable. Every *degraded branch* is reachable and rendered (FE-8, seven states). See the deviation below |
| **E3** | Redis reachable, and the breaker fails closed without it | ✅ **closed, restated** | [ADR-011](decisions/ADR-011-no-redis.md): there is no Redis, because one process has nothing to coordinate with. The fail-closed *principle* is implemented literally and tested — an unreadable spend file **denies**, a missing one allows. 5 parametrised cases incl. `{"usd": true}` |
| **E4** | Cache warmed **once**, at the shipping pin; every report's `versions` matches the running service | ✅ **closed** | The startup assertion exists and **works** — `assert_fresh` refuses to start on a stale cache and names which version moved; `/readyz` reports `stale_reports`. **14 reports, 0 stale.** The run also exposed that an *unconfigured* pin read as a *changed* one — fixed, since re-warming would have cost 14 items of spend to repair a missing env var. **This is one of the two rows that carry the month** |
| **E5** | Spend breaker verified by a **forced trip**, reset procedure in the runbook | ✅ **closed** | `make trip-breaker` / `make reset-breaker` go through the real code path. Runbook procedure **P3**. Test: `test_a_forced_trip_denies_the_live_route` |
| **E6** | Auto-rollback demonstrated by a deliberately failed smoke test | ⛔ **deleted** | ADR-003: nothing is deployed, so there is nothing to roll back to. ~0.7 h released |
| **E7** | Live at the custom domain over TLS, incognito + phone | ⛔ **deleted** | ADR-003: no public hostname, no cloud service. The DNS ticket was drafted and correctly never filed |
| **E8** | B4 #8 measured, **both halves**, with n | ⚠️ **cached half closed; live half not applicable** | **p50 0.9 ms · p90 1.0 ms · p99 1.3 ms over n=140 requests** across all 14 items — 4,800× inside the 5 s budget, because C4.9's cache-first rule makes this a disk read and nothing else. The live half needs E2, which ADR-003 deleted. Recorded as **half a measurement**, not as a pass |
| **E9** | Calibration page live, **zero hard-coded numbers** | ✅ **closed, and now with numbers in it** | FE-6 + `make calibration-page`, a grep over the component source that fails the build on a numeric literal that is a metric. **Since M2-17 every metric renders a measured figure with its n and interval** rather than *not yet measured*. The grep **caught a real regression while FE-11's G2 delta was being added** — C1.3's branch thresholds had been typed into the JSX as literals; they now live in `calibration/gate-thresholds.json`, labelled as gate constants fixed before any measurement. **The page leads with the shortfall** (G2-B delta), and that block is *derived* from `measurement_context` against those thresholds, so it cannot claim a branch the numbers do not support |
| **E10** | Faithfulness panel live, served from committed JSON | ✅ **closed** | FE-5 + `faithfulness/panel.json`, built by `make faithfulness` from S4's records. `make faithfulness-check` in CI. **It publishes 0 of 48** — see [findings](findings.md) |
| **E11** | Soundness never renders without its precision/recall; flags show escalated state | ✅ **closed, and now exercised with real bars** | FE-3 and FE-4 render from the frozen report; the fixture gap that let error bars render from `undefined` was found by the components and fixed. **Until M2-17 this held vacuously — there was no precision to render.** It now renders judge **P 64% · R 80%** beside every soundness score, so I3 is satisfied by the path it was written for rather than by the null path. `escalated` renders **false everywhere**, correctly: the tier was measured and shipped off (ADR-012) |
| **E12** | **5 of 5 testers unaided; ≥ 4 of 5 state "fluent ≠ sound"** | 🚫 **NOT CLOSABLE — published as a shortfall** (amendment 002 §4) | No testers booked. **No fallback exists**: B4 #9 is unmeasurable without them. Owner: tech lead. This is the hardest external dependency left in the project. **The protocol, facilitator script and empty record are written** ([walkthrough-notes.md](walkthrough-notes.md)) — fixed in advance so the pass mark cannot be set after watching people struggle. Booking is the only remaining step |
| **E13** | Runbook **exercised by another team member** | ⏳ **half closed, and not closable** (amendment 002 §4) | Written, and all six procedures were executed before being written (M3-5a's DoD) — two of them failed on first run and both failures are recorded in the runbook itself. **The peer dry-run has no named peer.** Owner: tech lead |
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

**The cached half, measured 12 Sep:** p50 **0.9 ms**, p90 **1.0 ms**, p99 **1.3 ms**, max
1.4 ms, over **n = 140** requests across all 14 items. The budget is 5,000 ms.

> **Two caveats, because a number 4,800× inside its budget invites the wrong reading.**
> This is the *server-side* path — a `GET` that resolves an allowlisted id to a dict entry
> and returns a file already in the page cache, measured over loopback. It is not what a
> viewer experiences, which also includes loading the static export. And it is fast for a
> structural reason rather than an optimisation: **C4.9 forbids a `GET` from triggering a
> model call**, so there is nothing on this path that *can* be slow. The number is
> evidence that the rule holds, not that the service is fast under load — nobody has put
> it under load, and with one operator nobody will.

**The live half is `null`, and stays null.** Not "pending": the system that would produce
it was deleted by ADR-003. A reader should see an explicit not-applicable with a reason,
not an empty cell that looks like an unfinished job.

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

## Re-executed 16 Sep 2026 (W6), after G2

**What moved:** E9 and E11 both closed *vacuously* before M2-17 — there were no measured
numbers for the calibration page to render and no precision for a soundness score to render
beside. **Both are now satisfied by the path they were written for.** E9's grep earned its
keep in the same session by catching gate thresholds typed into the page as literals.

**What the G2 result means for G3:** the branch is **G2-B** (§`g2-measurement-report.md`),
whose entire Month-3 cost is ~0.5 h of UI delta — **already applied**: the calibration page
leads with the shortfall. Nothing in this checklist changes shape.

**What amendment 002 settled, and it is not "blocked":** E12, E13 and E15 were carried as
blocked-on-people. They are now **published shortfalls with a reasoned decline** rather than
rows awaiting a booking. A model cannot supply the human half of a human-vs-model
measurement, and a reader who can open the source is not a naive viewer. The distinction
matters at a gate: *blocked* invites "chase it"; *declined and published* is a decision
somebody can disagree with in writing.

## Open rows, with owners and dates

| Row | Owner | Needs | By |
| --- | --- | --- | --- |
| ~~E1, E4~~ | — | **Closed 12 Sep** — 14 reports, 0 stale, 18/18 smoke with the key stripped | done |
| ~~E8~~ | — | **Closed** — p50 0.9 / p90 1.0 / p99 1.3 ms over n=140; live half n/a with its reason (ADR-003) | done |
| **E12** | — | **DECLINED, not blocked.** No testers; amendment 002 §2 refuses to substitute the agent for a naive viewer. **B4 #9 is lost and is published as a shortfall** | closed as a gap |
| **E13** | — | **Not closable.** An agent cold-run of the runbook is offered as a labelled partial substitute (amendment 002 §5) and is explicitly **not a pass** | closed as a gap |
| E15 | Lead | Fallback video — an unedited screen recording (L4). Recordable by the agent if the demo runs headless; otherwise unmade | Before any live demo |
| **U4** | **Tech lead + DM** | **The C10.1 contingency conversation. 97.4 h against a 12 h allocation, every C14 lever spent** | **The only row no amount of code advances** |
