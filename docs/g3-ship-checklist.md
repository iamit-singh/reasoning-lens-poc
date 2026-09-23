# G3 — the ship checklist, executed

| | |
| --- | --- |
| **Gate** | G3 · launch |
| **Owner** | Amit Singh (sole contributor, [amendment 001](../../plan-amendment-001-local-hybrid.md)) |
| **Checklist** | [month-3-task-breakdown.md §1.2](../../month-3-task-breakdown.md) — E1–E16 |
| **Status** | ⏳ **in progress** — **11 closed** (E2 and E15 closed 23 Sep), E8 half, 2 deleted by ADR-003, **2 open, plus U3 and U4 — every one of them needing a human who is not the Lead** |
| **Last executed** | **23 Sep 2026 (W7)** — fourth execution. **E15 closed**: its stated condition ("if the demo runs headless") became true and the video is made. E12's queued copy fixes are applied — which changes the page, not the measurement. First execution 12 Sep, re-executed 16 Sep after G2 and 18 Sep with the substitutes |

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
| **E2** | Live re-run end to end, SSE, every degraded branch reachable | ✅ **closed 23 Sep** | **Built.** `POST /api/runs` now runs the pipeline and streams stages over SSE at `/api/runs/{id}/events`; the report it builds is served flagged `live: true`. Verified against a real live run (`MOCK_LLM=0`, ollama + real analysis tier): **mb-01 in 97 s, mb-06 in 42 s**, full stage sequence over the wire, UI driven in a real browser. Degraded branches reachable at the transport, not only in fixtures. **The cached demo is untouched** — `DEMO_MODE=cached` still refuses with 503. See the deviation below, which has been rewritten |
| **E3** | Redis reachable, and the breaker fails closed without it | ✅ **closed, restated** | [ADR-011](decisions/ADR-011-no-redis.md): there is no Redis, because one process has nothing to coordinate with. The fail-closed *principle* is implemented literally and tested — an unreadable spend file **denies**, a missing one allows. 5 parametrised cases incl. `{"usd": true}` |
| **E4** | Cache warmed **once**, at the shipping pin; every report's `versions` matches the running service | ✅ **closed** | The startup assertion exists and **works** — `assert_fresh` refuses to start on a stale cache and names which version moved; `/readyz` reports `stale_reports`. **14 reports, 0 stale.** The run also exposed that an *unconfigured* pin read as a *changed* one — fixed, since re-warming would have cost 14 items of spend to repair a missing env var. **This is one of the two rows that carry the month** |
| **E5** | Spend breaker verified by a **forced trip**, reset procedure in the runbook | ✅ **closed** | `make trip-breaker` / `make reset-breaker` go through the real code path. Runbook procedure **P3**. Test: `test_a_forced_trip_denies_the_live_route` |
| **E6** | Auto-rollback demonstrated by a deliberately failed smoke test | ⛔ **deleted** | ADR-003: nothing is deployed, so there is nothing to roll back to. ~0.7 h released |
| **E7** | Live at the custom domain over TLS, incognito + phone | ⛔ **deleted** | ADR-003: no public hostname, no cloud service. The DNS ticket was drafted and correctly never filed |
| **E8** | B4 #8 measured, **both halves**, with n | ⚠️ **cached half closed; live half now measurable and NOT measured** | **p50 0.9 ms · p90 1.0 ms · p99 1.3 ms over n=140 requests** across all 14 items — 4,800× inside the 5 s budget, because C4.9's cache-first rule makes this a disk read and nothing else. The live half needed E2, and **E2 now exists** — so this stops being *not applicable* and becomes *unmeasured*, which is a worse status honestly stated. Two live runs were observed (97 s and 42 s wall-clock, n=2, uncontrolled) and **that is an observation, not B4 #8's measurement**: no percentiles, no n worth the name. Recorded as **half a measurement** |
| **E9** | Calibration page live, **zero hard-coded numbers** | ✅ **closed, and now with numbers in it** | FE-6 + `make calibration-page`, a grep over the component source that fails the build on a numeric literal that is a metric. **Since M2-17 every metric renders a measured figure with its n and interval** rather than *not yet measured*. The grep **caught a real regression while FE-11's G2 delta was being added** — C1.3's branch thresholds had been typed into the JSX as literals; they now live in `calibration/gate-thresholds.json`, labelled as gate constants fixed before any measurement. **The page leads with the shortfall** (G2-B delta), and that block is *derived* from `measurement_context` against those thresholds, so it cannot claim a branch the numbers do not support |
| **E10** | Faithfulness panel live, served from committed JSON | ✅ **closed** | FE-5 + `faithfulness/panel.json`, built by `make faithfulness` from S4's records. `make faithfulness-check` in CI. **It publishes 0 of 48** — see [findings](findings.md) |
| **E11** | Soundness never renders without its precision/recall; flags show escalated state | ✅ **closed, and now exercised with real bars** | FE-3 and FE-4 render from the frozen report; the fixture gap that let error bars render from `undefined` was found by the components and fixed. **Until M2-17 this held vacuously — there was no precision to render.** It now renders judge **P 64% · R 80%** beside every soundness score, so I3 is satisfied by the path it was written for rather than by the null path. `escalated` renders **false everywhere**, correctly: the tier was measured and shipped off (ADR-012) |
| **E12** | **5 of 5 testers unaided; ≥ 4 of 5 state "fluent ≠ sound"** | 🚫 **NOT CLOSABLE — published as a shortfall** (amendment 002 §4) | No testers booked. **No fallback exists**: B4 #9 is unmeasurable without them. Owner: tech lead. This is the hardest external dependency left in the project. **The protocol, facilitator script and empty record are written** ([walkthrough-notes.md](walkthrough-notes.md)) — fixed in advance so the pass mark cannot be set after watching people struggle. Booking is the only remaining step. **23 Sep: the four queued copy fixes are applied** — that improves the artifact and measures nothing; see the deviation below |
| **E13** | Runbook **exercised by another team member** | ⏳ **half closed, and not closable** (amendment 002 §4) | Written, and all six procedures were executed before being written (M3-5a's DoD) — two of them failed on first run and both failures are recorded in the runbook itself. **The peer dry-run has no named peer.** Owner: tech lead. **Re-run cold 23 Sep at `f9e10a9`: all seven procedures pass first try** — and it still found a ninth defect (a clean clone rewrote its own lockfile), which is the argument *for* the dry-run |
| **E14** | Wheel installs in a clean venv and runs on third-party spans | ✅ **closed** | `make wheel`. Failed on its first run — the JSON Schema was not packaged — and that defect is the argument for the check existing |
| **E15** | Embed snippet + fallback video. **Not a launch gate** | ✅ **closed 23 Sep** | Embed **deleted** by ADR-003 (no host, no hostile input path). **The fallback video is made** — `make demo-video`, [`demo-fallback.webm`](demo-fallback.webm), 49 s, 1280×800, five surfaces in one continuous pass with nothing edited, recorded against the cached read path with `OPENAI_API_KEY` stripped. Amendment 002 §4 made it conditional on the demo running headless; on 18 Sep no driver existed here and it was recorded as unmade, and that condition is now met. Provenance in [`demo-fallback.json`](demo-fallback.json). See the deviation below |
| **E16** | This checklist executed, every open row with an owner and a date | ✅ **closed by this file** | Re-execute at G3 |

## Deviations, stated rather than smoothed over

### E2 — recorded as deleted scope, and the reasoning went one step too far

**This row said "not built, and there will not be" until 23 Sep. That was wrong, and the
error is worth keeping visible rather than quietly editing out.**

C10.4 budgeted M3-1b and FE-8's SSE half against a hosted service. ADR-003 deleted the
hosting, and the conclusion drawn was *"there is no process to stream from"*. That covered
the **deployment** and was then applied one step further than it reached: the backend still
runs — one process on a laptop, serving the page and the API from one origin (FE-9) — and
`POST /api/runs` has existed since M3-1a, allowlisted and breaker-checked. There was always
a process. What was actually missing is that **the route returned `202` and then did
nothing at all**, which is a different and much smaller gap than "the architecture cannot
support this".

> **How a deleted-scope row goes stale.** ADR-003 was right about hosting on the day it was
> written. The row inherited its conclusion and then stopped being re-checked against a
> system that kept changing underneath it — FE-9 added the single origin in W5, and nobody
> revisited what that made possible. A decision with a written reason is still a decision
> about the world at one moment.

**What is built now.** `backend/runs.py`: a bounded in-memory registry (ADR-011 — one
process, one operator, nothing to coordinate with), a staged executor, and an SSE stream
that **replays from the first event**. That last part is load-bearing rather than a nicety:
the early stages are the fast ones, so the common case is a viewer who connects during
`classifying`, and a stream carrying only live events would show them a run that appears to
begin in the middle. It always terminates with an `end` frame, because a progress UI that
never receives one is indistinguishable from one still working.

**Degraded branches are now reachable two ways**, and both are worth having. FE-8's seven
run-level states remain exercised by `report_degraded.json` — that was always the valuable
half — and a live run can now actually *deliver* one over the wire: a failed arm is written
and streamed as degraded, and the other arms still render (C4.1/B6.5).

#### The spend gap this uncovered, which is the real finding

`breaker.record()` is implemented, tested, and **was called from nowhere in production.**
Harmless while nothing spent money; not harmless the moment a live path exists. The obvious
repair — record dollars per run — **cannot be done honestly**, because `analyzer/prices.json`
carries null rates deliberately: *"an invented rate would make `est_cost_usd` look measured
when it was assumed."*

So the dollar breaker is still checked, and it is **supplemented rather than replaced** by a
budget in a unit that is actually countable: **analysis calls**, per run and per process.
`est_cost_usd` is `null` everywhere with its reason attached, and `/readyz` reports the call
budget so nobody reads `spent_usd: 0.0` as *"this ran for free"* when it means *"nothing
here can price it"*.

#### A live report is a fourth provenance category

Not in `out/reports`, no `measurement_context`, never stamped, one unrepeated run — and a
real model really produced it, so it is not an authored fixture either. It is served with
`live: true` **on the payload**, exactly as `/api/replay` flags `illustrative`, because the
object travels to a download and possibly a screenshot. This is not hypothetical: a live
`mb-06` returned `direct` with 2 steps where the cached report has 3, one of them `unsound`.

> **Scope that was deleted by an accepted ADR and later turned out to be buildable is still
> not the same as scope that was missed** — but it is not a closed question either, and a
> gate checklist that never re-opens one is a checklist that can only ratchet one way.

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

**The live half was `null` with a reason, and as of 23 Sep the reason expired.** It read
*"not applicable — the system that would produce it was deleted by ADR-003"*. E2 is built,
so there is now a live path and the honest status is **unmeasured**, which is worse than
not-applicable and is the correct answer.

Two live runs have been observed end to end — **97 s and 42 s** wall-clock, on one laptop,
with the local model warm. **That is not B4 #8's live half** and must not be quoted as it:
n=2, no percentiles, no control over what else the machine was doing, and generation time is
dominated by a 20B model on consumer hardware rather than by anything this service does.
Publishing a p90 from two runs is precisely the single-run inference this project has had to
correct in writing twice.

> **What it would take:** the harness exists now (`POST /api/runs` plus the status route), so
> this is a measurement job rather than a build. It spends real analysis calls per run, which
> is why it has not been run on a whim — and the call budget in `backend/runs.py` is what
> stops a measurement loop from becoming an unbounded one.

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

## Re-executed 18 Sep 2026 (W6) — the three substitutes are now written, and none of them closed anything

Amendment 002 §5 offered three labelled substitutes for the rows no code can close. **All
three have now been produced, and all three rows are still open.** That is the intended
outcome and it is worth stating as a result rather than as an apology: each document gives a
reviewer evidence they did not have, under a name that does not overstate it.

| Row | Substitute | What it changed | What it did not |
| --- | --- | --- | --- |
| **E13** | [`runbook-cold-run.md`](runbook-cold-run.md) | **Eight of the runbook's commands did not work from a clean clone**, including P4's — the procedure E4 and every staleness guarantee rest on — which exited 2. **Re-run 23 Sep: all seven procedures pass first try**, `make smoke` 22/22, and a **ninth** defect surfaced — `npm install` rewrote the lockfile on every clean clone, so the export was always built from a dirty tree | **Not a peer**, and a *second* run by the same agent is less informative than the first — I now know where the document's edges are, which is the knowledge a peer would not have. U2 still owes a peer dry-run |
| **E12** | [`heuristic-walkthrough-review.md`](heuristic-walkthrough-review.md) | A specific, falsifiable hypothesis about **how B4 #9 would have failed**: the arrival screen argues tool-access while the criterion measures fluent-≠-sound, `sound`/`unsound`/`fluent` appear **zero times** on it, and the best counter-example on the page is labelled `unparsed`. Four queued copy fixes, **applied 23 Sep** | **Zero naive readers.** B4 #9 stays **lost**. Applying the fixes improves the artifact and measures nothing; it also spends the diagnostic value of the old wording, and both halves are recorded |
| **U3 / C15.1 #10** | [`lit-survey-part-a-review.md`](lit-survey-part-a-review.md) | Part A's description of the field held up; **its two forward-looking judgements were both falsified by the PoC it recommended** — A9.3's "biggest risk" fired (κ 0.550, precision 0.643) with its stated mitigation unable to discharge it, and A9.1's faithfulness takeaway returned **0 of 48** on the model actually run. Five concrete fixes listed | **Not a sign-off.** Still an em dash where the owner should be. No source was fetched — no citation was checked against the paper it cites |

**E15 was decided rather than pending on 18 Sep, and on 23 Sep the decision reversed
because its stated condition came true.** The embed half stays deleted by ADR-003 — no host,
no hostile input path, nothing to set `frame-ancestors` on. The fallback video's condition —
amendment 002 §4, *"if the demo runs headless; otherwise unmade"* — was **not met** on 18
Sep: no driver on this machine, and installing one for a non-gating artifact was not a
unilateral call. It **is** met now, so the video is made rather than argued about.

## Re-executed 23 Sep 2026 (W7) — E15 closes, and E12's queue is applied without closing E12

### E15 — made, and what it is worth is smaller than it looks

`make demo-video` records **one continuous 1280×800 pass over five surfaces, 49 s, nothing
edited** — unedited being a property of the script rather than a promise: one browser
context, no cuts, no post-processing. It drives the demo the way P1 brings it up (the
backend serving the static export, FE-9's single origin) with **`OPENAI_API_KEY` stripped**,
for the same reason `make smoke` strips it — *we did not call the provider* and *we could
not call the provider* are different claims, and only the second describes what a viewer is
watching.

**It refuses rather than recording something misleading.** If the export is not mounted, or
any report is stale, the recorder exits non-zero: a recording of numbers attributed to a
system that is no longer running is the most dishonest artifact this repo could ship, and it
is *more* dangerous than a live page showing the same thing because a video cannot be
re-checked against `/readyz`. Provenance — commit, browser build, `/readyz` at record time,
every page's status — is written to [`demo-fallback.json`](demo-fallback.json) beside it.

> **The gap this closes is narrow, and overstating it would be the easy mistake.**
> `make fe-export-check` already proves the export renders **with every `<script>` stripped
> and nothing running**, so a dead *backend* is covered by construction (I4) and covered
> more strongly than by any recording. A video additionally survives a dead **laptop**.
> That is the whole of what it adds. Whoever demos this should know which half is covered
> by which artifact.
>
> One honest caveat, recorded rather than buried: the browser is **not** the revision
> Playwright pins — it is the newest build already in this machine's cache, because
> downloading a fifth copy for a non-gating artifact was not worth ~150 MB. Which build it
> was is printed and written into the sidecar, never silently substituted.

### E12 — the queue is applied, and E12 is exactly as unmeasured as before

The four copy-and-ordering changes queued on 18 Sep are **applied**. The reason for holding
them was that the pilot would supply better wording than the author's guesses; the reason
for releasing them is that **the pilot has no date and the demo is being shown meanwhile.**
Withholding a known structural fix to preserve a diagnostic opportunity is right while the
session is coming and becomes simply shipping a worse page once it is not.

**This closes nothing and must not be read as progress on B4 #9.** Zero naive readers have
seen either version of the page. Applying a fix does not measure whether it worked, and the
fixes are unvalidated hypotheses that can be wrong in the same direction as the page they
replaced. What is gained is an arrival screen that gives a reader something to reach the
insight *with*; what is given up is the chance to learn how readers failed on the old
wording, and those four findings are now untestable. Both halves are recorded in
[`heuristic-walkthrough-review.md`](heuristic-walkthrough-review.md).

> **The subtitle deliberately stops short of stating the insight.** A page reading "fluent
> is not the same as sound" would put the scored sentence on the screen and make B4 #9
> unmeasurable by construction. Giving a reader something to reach it with is the fix;
> giving them the sentence would be marking our own exam.

## Open rows, with owners and dates

| Row | Owner | Needs | By |
| --- | --- | --- | --- |
| ~~E1, E4~~ | — | **Closed 12 Sep** — 14 reports, 0 stale, smoke green with the key stripped. **Re-proven from a clean clone 18 Sep**, 22/22 | done |
| ~~E8~~ | — | **Closed** — p50 0.9 / p90 1.0 / p99 1.3 ms over n=140; live half n/a with its reason (ADR-003) | done |
| **E12** | — | **DECLINED, not blocked.** No testers; amendment 002 §2 refuses to substitute the agent for a naive viewer. **B4 #9 is lost and is published as a shortfall.** Heuristic review filed 18 Sep; its four copy fixes **applied 23 Sep**, which improves the page and measures nothing | closed as a gap |
| **E13** | **Tech lead (U2)** | **Not closable by the substitute.** Cold-run filed 18 Sep and it found eight broken commands — which **raises** rather than lowers the odds a peer finds more. A named peer is still owed | open |
| ~~**E15**~~ | — | **Closed 23 Sep.** Video made (`make demo-video`, 49 s, unedited, provenance stamped); embed deleted by ADR-003. Not a launch gate | done |
| **C15.1 #10 / U3** | **Reviewer — still unnamed** | Review report filed 18 Sep with five concrete fixes. **A sign-off is a person; the row needs one name** | open |
| **U4** | **Tech lead + DM** | **The C10.1 contingency conversation. 97.4 h against a 12 h allocation, every C14 lever spent** | **The only row no amount of code advances** |

> **Eleven rows closed, two deleted by ADR-003, E8 half-measured, and two that need a human
> who is not the Lead** — plus U3, which needs one name, and U4, which needs two people.
>
> **Two rows moved on 23 Sep and both moved for the same reason: a machine could do the
> work, and nobody had checked recently whether it could.** E15's condition ("if the demo
> runs headless") had become true. E2 was never blocked on the hosting ADR-003 deleted — it
> was blocked on a route that returned `202` and did nothing, and the single origin FE-9
> added in W5 had quietly made the rest possible.
>
> **E12 and E13 did not move, and cannot.** What they measure is people. Real work landed
> against both — E12's copy queue applied, E13's runbook re-run cold — and **neither moved a
> criterion**. That is the result, not an apology for it.
>
> **One row got worse, and that is the honest consequence of building E2.** E8's live half
> was *not applicable* while no live path existed; now one does, so it is **unmeasured**.
> Building the thing that could produce a number does not produce the number.
