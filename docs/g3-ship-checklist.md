# G3 — the ship checklist, executed

| | |
| --- | --- |
| **Gate** | G3 · launch |
| **Owner** | Amit Singh (sole contributor, [amendment 001](../../plan-amendment-001-local-hybrid.md)) |
| **Checklist** | [month-3-task-breakdown.md §1.2](../../month-3-task-breakdown.md) — E1–E16 |
| **Status** | ✅ **CLOSED 28 Sep 2026 — the PoC ended on what exists.** **13 closed**, **2 deleted** by ADR-003 (E6, E7), **E13 unmet at close** (no peer dry-run). U3 and U4 unowned at close; the launch branch line is left for the reviewer. See [poc-conclusion.md](poc-conclusion.md) |
| **Last executed** | **28 Sep 2026** — sixth and final execution, at close-out. All eleven E12 defects closed or decided (D9 fixed, D11 decided the reversible way). A clean copy of the tree then found four more — blank shipping pins, an unstamped P1, two CI jobs that could not pass on a checkout, and `test_runs.py` running nowhere — all fixed and re-verified from the clean copy. Earlier: **23 Sep (W7)**, fifth execution, E12 closed by measurement |

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
| **E8** | B4 #8 measured, **both halves**, with n | ⚠️ **both halves measured — cached passes, live passes at p90 and FAILS in the tail** | **p50 0.9 ms · p90 1.0 ms · p99 1.3 ms over n=140 requests** across all 14 items — 4,800× inside the 5 s budget, because C4.9's cache-first rule makes this a disk read and nothing else. **Live half measured 23 Sep, n=14/14 over distinct bank items**: p50 **33.2 s**, p90 **101.6 s** against a 120 s budget, max **252.7 s**. The p90 passes. **One run exceeds the budget by 2.1×, and it is `mb-08` — the item the landing page features.** [`b4-8-live-latency.json`](b4-8-live-latency.json). Reported as a pass at p90 **and** a tail failure, because reporting only the first would be the more flattering half of one measurement |
| **E9** | Calibration page live, **zero hard-coded numbers** | ✅ **closed, and now with numbers in it** | FE-6 + `make calibration-page`, a grep over the component source that fails the build on a numeric literal that is a metric. **Since M2-17 every metric renders a measured figure with its n and interval** rather than *not yet measured*. The grep **caught a real regression while FE-11's G2 delta was being added** — C1.3's branch thresholds had been typed into the JSX as literals; they now live in `calibration/gate-thresholds.json`, labelled as gate constants fixed before any measurement. **The page leads with the shortfall** (G2-B delta), and that block is *derived* from `measurement_context` against those thresholds, so it cannot claim a branch the numbers do not support |
| **E10** | Faithfulness panel live, served from committed JSON | ✅ **closed** | FE-5 + `faithfulness/panel.json`, built by `make faithfulness` from S4's records. `make faithfulness-check` in CI. **It publishes 0 of 48** — see [findings](findings.md) |
| **E11** | Soundness never renders without its precision/recall; flags show escalated state | ✅ **closed, and now exercised with real bars** | FE-3 and FE-4 render from the frozen report; the fixture gap that let error bars render from `undefined` was found by the components and fixed. **Until M2-17 this held vacuously — there was no precision to render.** It now renders judge **P 64% · R 80%** beside every soundness score, so I3 is satisfied by the path it was written for rather than by the null path. `escalated` renders **false everywhere**, correctly: the tier was measured and shipped off (ADR-012) |
| **E12** | **5 of 5 testers unaided; ≥ 4 of 5 state "fluent ≠ sound"** | ✅ **CLOSED 23 Sep 2026 — MEASURED, AND IT PASSED** | **Completion 5/5 · insight 5/5**, five self-administered sessions, 16:23–17:31 IST, against `1954883`. [`walkthrough-notes.md`](walkthrough-notes.md) holds the reading; [`walkthrough-sessions/`](walkthrough-sessions/) holds the five returned files unedited. **The pass marks were fixed 18 Sep and were not touched** — which is the only reason this row is worth anything now that it reads as a pass. **Three limits, recorded because the result is favourable:** no session recorded its build (the kit has no field — commit inferred from timestamps, and filed as a kit defect); **no pilot ran**, so §2.3 Hazard 4's 2+5 split did not happen; **all five were unattended, so every hesitation is lost**. **One insight call is marginal** (the ops engineer read the dissociation as cost, not soundness) and is recorded as such — 4/5 also clears the target, so nothing turns on it. **The heuristic review's predicted failure mode (a tool-access reading) occurred in ZERO of five**, with no control arm, so the four copy fixes are un-refuted rather than confirmed. **The sessions also found a real defect the site had been shipping** — see E12-D below
| **E13** | Runbook **exercised by another team member** | ⏳ **half closed, and not closable** (amendment 002 §4) | Written, and all six procedures were executed before being written (M3-5a's DoD) — two of them failed on first run and both failures are recorded in the runbook itself. **The peer dry-run has no named peer.** Owner: tech lead. Re-run cold 23 Sep: all procedures pass, and it still found a ninth defect. **`make runbook-check` now runs on every PR** and asserts every command the runbook prints actually exists — the mechanical half, which is the half that was finding things (8 of 9 defects were exit codes). **It says nothing about whether a stranger can follow the document**, which is what E13 asks |
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

**The live half was `null` with a reason, the reason expired on 23 Sep, and it is now
measured.** It had read *"not applicable — the system that would produce it was deleted by
ADR-003"*. E2 exists, so it became **unmeasured** — worse, and correct — and then it was
measured: `make live-latency`, **n = 14 of 14 successful**, one run per distinct bank item.

| | |
| --- | --- |
| p50 | **33.2 s** |
| **p90** | **101.6 s** — under the 120 s budget |
| max | **252.7 s** — `mb-08`, **2.11× the budget** |
| spread | 24.9 s – 252.7 s, mean 58.9, σ 59.9 |

### The headline passes and the tail does not, and both are the same measurement

Reporting *"B4 #8 live: p90 101.6 s, meets the 120 s budget"* would be true, and would be
the more flattering half of one result. Two things sit behind it:

**1. The p90 at n=14 is a single observation.** Nearest-rank puts it at the 13th of 14
values, so **one run determines the headline** — move it and the number moves. This project
has had to correct single-run inference in writing twice (ADR-010's `backtracking = 0`,
M2-3's cycle-3 "collapse"), and a percentile resting on one sample is the same error wearing
a statistic's clothes. The file records `p90_rank` and `p90_rests_on_observations` so a
reader sees this without recomputing it.

**2. The one run that blows the budget is the one a visitor is most likely to trigger.**
`mb-08` took **252.7 s** — four minutes — and `mb-08` **is the featured comparison on the
arrival screen**, chosen by `featured()` because it is the most striking measured contrast in
the corpus. It is also the item with 4,100 reasoning tokens and no answer, which is *why* it
is both the best evidence on the site and the slowest thing to re-run.

> **So the most likely single live re-run anybody performs is the worst case, not the
> median.** A reviewer who opens the demo, reads the featured comparison and presses
> *"Re-run this item live"* waits **four minutes** against a budget of two, having been told
> by the panel's own copy that it "takes about a minute".
>
> That copy is now wrong on the one item it is most likely to be read on. **Not fixed here**:
> the panel's estimate should come from this measurement rather than from a guess, and
> wiring a measured figure into that sentence is a change to a published number's source,
> not a copy tweak. It is named as an open defect instead of quietly reworded.

**What the number cannot tell you**, and the file repeats these beside the result: one
machine, one operator, **no concurrency** — this is latency, not capacity; **generation
dominates and it is local**, so most of the wall clock is `gpt-oss:20b` on consumer hardware
rather than anything this service does, and different hardware moves the number without the
code changing; the model was **warm**, so a cold ollama load is excluded and would add tens
of seconds.

### E12 and E13 — the two rows no amount of code closes

> **✅ 23 Sep: E12 is closed. A person closed it, exactly as this section said one would have to.**
> The section is kept unedited below because it argued, correctly and for five weeks, that no
> amount of code would close this row — and no amount of code did. What closed it was five
> people and twenty minutes each. **E13 is still open and the argument still holds for it.**

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

### What was done on 23 Sep for the two rows that cannot close

Neither row moved. **Both asks got smaller**, which is the only thing a machine could
contribute, and it is worth separating from progress on the criteria.

| | The ask before | The ask now | What is unchanged |
| --- | --- | --- | --- |
| **E12** | 5 naive testers **+ a facilitator + 5 scheduled 20-minute slots** | 5 naive testers. Send [`walkthrough-kit.html`](walkthrough-kit.html), collect 5 files | **Five people who have never seen the demo.** Unsubstitutable (amendment 002 §2) |
| **E13** | A peer reads the runbook **and discovers whatever has rotted since it was written** | A peer reads a runbook whose commands are CI-verified to exist | **A person who did not write it, driving it.** Unsubstitutable |

**The kit is stricter in one way and weaker in another**, and the weaker way is the one to
weigh: it cannot prompt — no nod, no half-answered question — but an unattended session
loses the *hesitations* the protocol calls *"cheaper to fix than failures and usually
predict them"*. If a facilitator is ever available, the attended protocol is better and the
kit should not be used instead of it.

> **`make runbook-check` does not substitute for the dry-run and the script says so in its
> own docstring.** It removes the class of failure where a peer's scarce hour is spent
> discovering that a target was renamed six weeks ago. E13 asks whether somebody else can
> *follow* the document — whether the steps are in a followable order, whether a procedure
> assumes knowledge it never states, whether the reader gives up. **None of that is
> checkable by a machine**, and this check passing says nothing about it.
>
> Its three branches were negative-tested — a renamed target, a renamed flag and an
> undocumented env var each fail it by name — because a check that has only ever passed is
> not evidence of anything.

## Re-executed 23 Sep 2026 (W7, later the same day) — E12 closes, by five people

**The row this project called its hardest external dependency closed, and nothing a machine
did closed it.** Five naive testers ran [`walkthrough-kit.html`](walkthrough-kit.html)
between 16:23 and 17:31 IST. **Completion 5/5, insight 5/5.** Both targets met, both fixed
on 18 Sep and untouched since.

### What is worth saying about a pass, given how this file talks about failures

**The pass marks were fixed before anyone was booked, and that is now the load-bearing
fact.** Every prior execution of this checklist argued that setting a bar after watching
people struggle turns a communication test into a post-hoc justification. The bar was set
five days early. It has not moved. **That is the only reason 5/5 means anything here**, and
it is worth more than the number.

**Three limits, written down precisely because the result is favourable.** A project that
records its caveats only when the news is bad has not been recording caveats — it has been
managing impressions.

1. **No session recorded its build.** The protocol demanded it in a ⚠️ box added
   specifically for these sessions, because the page changed that morning. **The kit has no
   field for it**, so the demand could not be met. The commit is recovered by inference —
   all five completed after 16:23, the last commit that day was `1954883` at 14:51 — which
   is sound and is still not a record. **Filed as a kit defect below.**
2. **No pilot ran.** §2.3 Hazard 4 split this 2 + 5 so the cheapest copy fixes could land in
   between. All five ran inside 68 minutes. The insurance was not bought; the fire did not
   happen either.
3. **Every hesitation is lost.** All five sessions were unattended. The kit's own
   documentation called this its weakness before anyone used it, and that is exactly what
   it cost.

**One insight call is marginal.** Tester 3 read the dissociation as cost — *"the expensive
setting is not the good setting"* — rather than as fluent-≠-sound. Same axis, different
route. A stricter reader could score it a miss; **4/5 also clears the target**, so the
result does not depend on the call, and the verbatim is in the notes so the call can be
overruled without re-reading the files.

**The heuristic review's prediction did not come true, and that is not the same as the
fixes working.** [It predicted](heuristic-walkthrough-review.md) that a naive tester would
read the featured comparison as a tool-access story and miss B4 #9 entirely. **Zero of five
made that reading.** But nobody read the 18 Sep wording at `0fb1a67`, so **there is no
control arm**, and the four copy fixes are un-refuted rather than confirmed. The strongest
honest statement is: on the shipped wording, the predicted failure did not occur in 5 of 5.

**Two of the four copy fixes have direct evidence of doing work**, which is weaker than
attribution and better than nothing. Three testers reached the insight through the no-answer
cell that fix (1) reframed. And tester 2, on the verge of abandoning the 27-card grid, took
one of the two *start here* doors fix (4) added — **a tester who says they would otherwise
have stopped.**

### E12-D — the sessions found a defect, and that is the real return

**Four of five testers, unaided, found that the site contradicts itself about whether its
own grading has been checked.** Two lost time to it assuming they had misread.

Every item report carries an all-null `measurement_context` — *"calibration has not run,
every field is null"* — while `/calibration/` publishes κ 0.55, precision 0.64 and recall
0.80 from the same repository. **Confirmed at scale: 14 of 14 reports.** It is not one
stale page; it is every item page on the site.

> **This is the defect that matters most on a site whose entire pitch is checkability.** A
> reader who catches it starts discounting the project's honesty rather than crediting it,
> which inverts the design intent exactly. It was found by four strangers in under eleven
> minutes each, and by nobody inside the project in the eleven days since M2-17 landed the
> numbers.

**A second vintage problem sits underneath it, and it is real rather than cosmetic.** The
`SE-*` planted-error pages render prompt bundle `97667881c7`; the `mb-*` pages render
`e8952d4d3c`. The calibration page states every figure belongs to one model pin and one
prompt bundle and **expires if either changes**. So the site serves two bundles while
asserting one, and **nothing fails the build over it**. Two testers found it independently;
one spent their only recorded confusion trying to work out whether it was a deliberate
distinction or undetected drift. **It is drift, and it is systematic** — every SE page, not
a stray.

**Filed as defects, not smoothed over:**

| # | Defect | Found by | Severity |
| - | ------ | -------- | -------- |
| **D1** | All 14 item reports carry a null `measurement_context` while `/calibration/` publishes the figures — the site contradicts its own headline promise | 4 of 5 | ✅ **FIXED** — and the root cause is worse than the symptom, see below |
| **D2** | Two prompt bundles live at once (`e8952d4d3c` on `mb-*`, `97667881c7` on `SE-*`); nothing enforces the stated single-vintage rule at build time | 2 of 5 | ✅ **ENFORCED** — `make bundle-check`, in CI. The drift is real and is **not** a measurement error, see below |
| **D3** | `SE-01`'s judge field renders as an em-dash | 2 of 5 | ✅ **FIXED** — cause found: those reports carry **no `versions` block at all**, so the pin was never captured. Same root as D2. Labelled, not fabricated |
| **D4** | `trace: partial` is undefined, and appears on the one arm the headline rests on | 2 of 5 | ✅ **FIXED, and the old copy was wrong** — it offered "the run timed out" as a cause that **cannot apply** to this list. It is not truncation, and the page now says so |
| **D5** | Home page quotes the judge's precision stripped of its interval and n, which the calibration page would never permit | 2 of 5 | ✅ **FIXED** — renders the interval and n, read from `measurement_context`, never typed. E9's grep caught the fix's own comments and was right to |
| **D6** | A stray `"}` renders in `mb-06`'s ReAct consistency line. **Both finders diagnosed it wrong**: it is inside the *judge's own rationale string* | 2 of 5 | ✅ **FIXED AT THE DISPLAY LAYER ONLY** — the stored report is **not** edited; the real fix is validating judge output upstream, and that is filed, not done |
| **D7** | The 27-card grid mixes 14 measured, 10 planted-error and 3 illustrative items behind badges alone; two testers read it as one dataset | 3 of 5 | ✅ **FIXED** — grouped by provenance with a line of prose each; the per-card provenance chip is gone, so one badge style now means one kind of thing |
| **D8** | Filter chip counts sum to 38 against *"all 27"*, with nothing signalling overlapping tags | 1 of 5 | ✅ **FIXED** — one line saying items carry more than one tag |
| **D9** | `mc-04` is absent between `mc-03` and `mc-05` with no explanation | 1 of 5 | ✅ **FIXED 28 Sep** — the faithfulness panel now lists `mc-04` and `mc-06` under *Not on this panel, and why*, **derived from S4's records** rather than typed; the pattern is recorded as a **lead, not a finding** in [findings §17](findings.md) at its n of 3 |
| **D10** | The walkthrough kit has **no field for the build commit**, so the protocol's own ⚠️ requirement could not be met | this execution | ✅ **FIXED** — the commit rides in the link (`?build=`); the tester is never asked a question they cannot answer |
| **D11** | Annotator names ship in a page footer. Intended? | 1 of 5 | ✅ **DECIDED 28 Sep, the reversible way** — the page states the annotator **count**; the names stay in `latest.json` as repo provenance. Taken at close-out because the Lead has no further time; one line to revert |

### D1 fixed — and the root cause is the part worth keeping

**The assertion that forbids this state already existed, and had never been run.**
`scripts/stamp_reports.py --check` was written at M2-10b for exactly this, and its own
module docstring says it exists so *"the G2 evidence pack can show it green"*. It was in **no workflow, not in `make ci`, and not in the runbook** — a Makefile target
and nothing else. Running it on 23 Sep:

    STALE: 14 of 14 reports do not carry calibration_run_id 'cal-2026-09-16'.

**That is the identical gap the `faithfulness-check` job was added to close** — E10's
evidence line claimed a check ran in CI when it ran only in `make ci`. The same failure, a
second time, on a different check.

> **An assertion that exists and does not run is not a weaker check than one that runs. It
> is worse**, because the project cites it as covered and stops looking. Both times the
> check was correct, present, and silent.

**So the fix is not the stamp.** `make stamp-reports` repaired the data in one command and
all 14 reports now carry κ 0.55, P 0.64 and R 0.80 **with their intervals and n**, which
also gives the item pages the material D5 says the home page is missing. **The fix is the
CI job**, because nothing else stops M2-17's successor re-opening it. Negative-tested: one
deliberately stale report turns it red by name.

### D2 enforced — and the harder possibility was checked and ruled out

The drift is real and systematic: every `SE-*` page renders `97667881c779` against a
shipping bundle of `e8952d4d3c51`. **The question that mattered is whether it reached the
published numbers**, because judge recall 0.80 is measured on those seeded errors, and a
recall attributed to the wrong bundle would be a measurement defect rather than a rendering
one.

**It did not.** M2-6's raw evidence (`docs/spikes/M2-6-raw/m2-6-seeded.json`) is recorded at
`e8952d4d3c51`. **Recall 0.80 is correctly attributed.** The seeded *reports* on disk are
leftovers from an earlier judging run that the frontend kept rendering.

`make bundle-check` now fails the build on any rendered report whose bundle is not the
shipping one **unless it is declared, with its reason, in the script**. The seeded reports
are declared: re-judging them is ten live analysis calls, which would be a **re-measurement
of M2-6 rather than a rebuild**, and that is not a thing to do silently to make a checker
go green. **A second vintage may ship; it may not ship undeclared.** Negative-tested:
removing the declaration turns it red and names all ten files.

### D9 answered — the gap is principled, and what is behind it is a result nobody published

**`mc-04` was not dropped from the experiment.** It is in S4's raw records, and so is
`mc-06`. Both are absent from the panel for one reason, visible in the raw file:

| item | regime | baseline answer |
| --- | --- | --- |
| `mc-01` `mc-02` `mc-03` | solvable | present |
| `mc-05` | unverifiable | present |
| **`mc-04`** | **unverifiable** | **none** |
| **`mc-06`** | **unverifiable** | **none** |

Faithfulness asks whether a planted cue makes the model **change its answer**. An item with
no baseline answer has nothing to change. **The exclusion happened before any cue was
applied and could not depend on a result**, which is precisely what the reviewer wanted to
know when they asked whether the decision was made *"before or after its results were
seen"*. It was before, structurally.

> ### The pattern is the finding, and it is larger than the reviewer could see.
>
> They noticed that `mc-05` — **the only unverifiable item on the panel** — is also the only
> one where the cue was verbalised 12/12, and that it produced 3 no-answer trials, and they
> filed it as an interesting thing buried in a footnote.
>
> **With `mc-04` and `mc-06` restored to view, all three unverifiable items misbehaved.**
> Two produced no answer at all at baseline; the third answered but was the only unstable
> one on the panel. **This model stops answering when the question cannot be verified** — a
> real behavioural result, sitting invisible in a raw file, currently rendered on the site
> as *a gap in the item numbering*.
>
> That reading rests on n=3 items and is a hypothesis, not a measurement. **It is exactly
> the kind of claim this project would normally refuse to make from three observations**,
> and it is recorded as a lead rather than a finding for that reason.

**Not fixed here, deliberately.** The page fix (say why the panel has 4 of 6) is small. The
interesting half is a claim about the unverifiable regime and belongs in
[`findings.md`](findings.md) under its own n, which is a measurement decision rather than a
copy one. Both are open.

**One finding is methodological rather than a defect, and it is the sharpest thing any
tester said.** Judge recall 0.80 is measured against ten errors a human deliberately
planted. Unless the mutation typology was fixed *before* the judge ran, and by someone blind
to its known failure modes, **that figure estimates recall on errors of the kind we thought
to plant** — not recall. It is not fixable by editing a page. It is recorded in
[`findings.md`](findings.md) as a limit on what M2-6 measured.

## Open rows, with owners and dates

| Row | Owner | Needs | By |
| --- | --- | --- | --- |
| ~~E1, E4~~ | — | **Closed 12 Sep** — 14 reports, 0 stale, smoke green with the key stripped. **Re-proven from a clean clone 18 Sep**, 22/22 | done |
| ~~E8~~ | — | **Closed** — p50 0.9 / p90 1.0 / p99 1.3 ms over n=140; live half n/a with its reason (ADR-003) | done |
| ~~**E12**~~ | — | **CLOSED 23 Sep — MEASURED AND PASSED.** Five naive testers, self-administered kit, **5/5 unaided · 5/5 stated the insight** against pass marks fixed 18 Sep and never touched. **Not closed by any of the substitutes** — closed by five people. The sessions found **eleven defects** the project had not caught, one of them high-severity on the site's own central claim (E12-D above) | done |
| **E13** | **Tech lead (U2)** | **Not closable by the substitute.** Cold-run filed 18 Sep and it found eight broken commands — which **raises** rather than lowers the odds a peer finds more. A named peer is still owed | open |
| ~~**E15**~~ | — | **Closed 23 Sep.** Video made (`make demo-video`, 49 s, unedited, provenance stamped); embed deleted by ADR-003. Not a launch gate | done |
| **C15.1 #10 / U3** | **Reviewer — still unnamed** | Review report filed 18 Sep with five concrete fixes. **A sign-off is a person; the row needs one name** | open |
| **U4** | **Tech lead + DM** | **The C10.1 contingency conversation. 97.4 h against a 12 h allocation, every C14 lever spent** | **The only row no amount of code advances** |

> **Twelve rows closed, two deleted by ADR-003, and ONE that needs a human who is not the
> Lead** — E13 — plus U3, which needs one name, and U4, which needs two people.
>
> **E12 is closed, and it was the hardest external dependency in the project.** Of the two
> rows this file has said for five weeks that no code could close, one is now measured.
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
> > **✅ Overtaken by events, later the same day. E12 moved.** Five people ran the kit and
> > B4 #9 passed 5/5 · 5/5. **The paragraph above is kept exactly as written** because it was
> > true when written and because its claim was the right one: no substitute closed this row,
> > and none could have. What closed it was the thing the row always said it needed.
> > **E13 is unchanged and the paragraph still describes it.**
>
> **What E12 returned was not mainly a pass.** Four of five testers independently found that
> every item page on the site says calibration has not run while `/calibration/` publishes
> the figures — **14 of 14 reports**, shipped since M2-17, caught by nobody inside the
> project and by four strangers in under eleven minutes each. **The measurement that was
> hardest to obtain is the one that found the defect**, which is the argument for having
> insisted on it rather than accepting a substitute.
>
> **One row got worse before it got better, and the sequence is the honest part.** E8's live
> half was *not applicable* while no live path existed; building E2 made it **unmeasured**;
> measuring it made it **measured, and mixed** — p90 101.6 s inside a 120 s budget, with one
> run of fourteen at 252.7 s. **The run that blows the budget is `mb-08`, the item the
> landing page features**, so the most likely live re-run anybody performs is the worst case
> rather than the median. Building the thing that can produce a number does not produce the
> number, and producing it does not guarantee you like it.
