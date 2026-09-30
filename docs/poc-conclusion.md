# Reasoning Lens — PoC conclusion

**Closed 28 Sep 2026** at commit `ec6fa42`, on what exists. The Lead has no further time to
give, so this is the end of the PoC, not a pause. Nothing below needs further work to be
true. The rows that stay open are listed as **unmet**, each with its reason, and none is
listed as pending.

---

## 1. The answer to the question the PoC asked

[B2](../../poc-reasoning-lens.md) set two thresholds in advance: success at **κ ≥ 0.60 and
judge precision ≥ 0.75**, and falsification at **κ < 0.45 or precision < 0.60**.

| | Measured | n | Success bar | Falsified below | Where it lands |
| --- | --- | --- | --- | --- | --- |
| Behavior classifier κ (held-out), vs annotator 1 | **0.550** [−0.02, 1.00] | 50 | 0.60 | 0.45 | between the two bars |
| Behavior classifier κ (held-out), vs annotator 2 (blind) | **0.401** [−0.02, 0.79] | 50 | 0.60 | 0.45 | **below the falsification bar** |
| Judge precision (pooled) | **0.643** [0.39, 0.84] | 14 | 0.75 | 0.60 | between the two bars |
| Step-soundness κ (held-out) | **0.822 / 0.885** | 50 | 0.60 | — | **clears on both readings** |
| Judge recall (seeded errors) | **0.80** (8 of 10) | 10 | 0.70 | — | clears |

> **The verdict: not confirmed, and split by component.**
>
> - **Judging whether a reasoning step is *sound* works** at the level the plan asked for.
>   Soundness agreement clears the bar on both annotators' readings, and recall on planted
>   errors clears too. The judge's weakness is **precision**: roughly one flag in three is
>   wrong, so a flag means "look here", not "this is wrong".
> - **Classifying *which cognitive behavior* a step shows does not work well enough to
>   publish as a measurement.** The two readings disagree on a single label, and that label
>   decides whether κ lands in the middle band or the falsified one. Against the blind
>   annotator it is falsified. Underneath that: 46 of 50 held-out steps are `linear`, so
>   the taxonomy barely populates on this model ([findings §4](findings.md), [ADR-010](decisions/ADR-010-the-taxonomy-barely-populates.md)) and four steps
>   carry the whole coefficient. **Every interval is wide enough to hold both "useful" and
>   "useless".**
> - **The faithfulness demonstration did not reproduce.** 0 of 48 cue trials flipped the
>   answer ([ADR-009](decisions/ADR-009-cue-injection-does-not-reproduce.md)), so the planned "a fluent
>   trace is not an explanation" moment does not exist on this pin. The panel ships the
>   negative result with its denominator.

So the claim the PoC can make is narrower than the one it set out to make: **an off-the-shelf
LLM judge can score step *soundness* usefully, and cannot yet classify reasoning *behavior*
reliably on a model whose reasoning is mostly linear.** B2 names that outcome as a
publishable result in its own right. The calibration page has published it, shortfall first,
since 16 Sep.

## 2. Did the demo communicate?

**Yes — the one criterion that tests this passed.** Five people outside the team ran the
self-administered walkthrough on 23 Sep. **All five completed it unaided and all five stated
the "fluent ≠ sound" insight**, against pass marks fixed on 18 Sep and not touched since
(bar: 4 of 5). The limits carry the same weight as the result: n = 5, every session
unattended, no pilot, and one insight call is marginal (the reader reached it through cost
rather than soundness). The details are in [walkthrough-notes.md](walkthrough-notes.md).

The testers also found **eleven defects nobody inside the project had caught**. The worst
was every item page saying calibration had not run while `/calibration/` published the
figures. All eleven are now closed or decided. D6's upstream half is filed, see §5.

## 3. Every success criterion, final

| B4 / G3 | Criterion | Final |
| --- | --- | --- |
| B4 #1 | Inter-annotator κ ≥ 0.70 | **Met** — 0.867 behavior, 0.935 soundness, n=50, unadjudicated floor |
| B4 #2 | Classifier κ ≥ 0.60, lowest per-class F1 ≥ 0.50 | **Not met** — see §1. Per-class F1 is 0.000 on dev and 0.500 on held-out at a support of 3 |
| B4 #3 | Judge recall ≥ 70% | **Met** — 0.80. It estimates recall on *the kinds of errors we thought to plant*, a limit one tester named |
| B4 #4 | Judge precision ≥ 0.75; ≤ 1 false flag per good trace | **Not met** — 0.643. The per-trace clause was unmeasurable after amendment 002 |
| B4 #5 | Consistency false-positive rate ≤ 5% | **Met, read as a count** — 0 of 5. At n=5 a 5% bar and a 0% bar are the same bar |
| B4 #6 | Faithfulness reproduces on ≥ 2 of 3 | **Not met** — 0 of 48 trials, published as the finding |
| B4 #7 | Cost of thought visible | **Reported** — median 5.13× reasoning tokens, range 1.22–53.59×, n=14 |
| B4 #8 | p90 latency | **Cached: met** (1.0 ms, n=140). **Live: p90 101.6 s against 120 s, max 252.7 s** — the tail fails, on the featured item |
| B4 #9 | ≥ 4 of 5 testers state the insight | **Met** — 5 of 5 |
| G3 E1–E5, E9–E12, E14–E16 | Launch checklist | **Closed** |
| G3 E6, E7 | Rollback drill; live at a custom domain | **Deleted by [ADR-003](decisions/ADR-003-hosting.md)** — nothing is deployed |
| G3 E8 | B4 #8, both halves | **Closed as measured**, with the tail failure published |
| **G3 E13** | Runbook exercised by another team member | **Unmet at close.** The mechanical half runs as `make runbook-check`. Whether a stranger can *follow* it was never tested |
| B2 | Demo live at a public URL | **Unmet by decision** — ADR-003 deleted hosting. The product is a static export served from one process, plus a fallback video |
| B2 | ≥ 1 client conversation uses the demo | **Unmet.** It did not happen |

## 4. What was built, and what can be picked up

Everything below runs from a clean checkout. That was verified on 28 Sep from a fresh copy
of the tree, not from the working directory.

- **The analyzer** (`analyzer/`): OTEL span ingest → deterministic segmentation → behavior
  classification → step-validity and consistency judging → a schema-frozen
  `ReasoningReport`. It installs as a wheel in a clean venv and runs on third-party
  LangGraph spans (`make wheel`), and it is the handover-grade piece.
- **The demo** (`frontend/`, `backend/`): a static export of the three-strategy comparison,
  annotated traces, calibration page, faithfulness panel and report download. It is served
  by one backend process that also offers a live re-run over SSE. Bring it up with P1 in
  [runbook.md](runbook.md): `cp .env.example .env && make demo-data && make fe-build-measured
  && make serve-api`. `make smoke` gives 26/26 with no provider key.
- **The evidence**: [g2-measurement-report.md](g2-measurement-report.md),
  [findings.md](findings.md) (17 findings; §17 is a lead, not a finding),
  `calibration/results/latest.json`, `faithfulness/panel.json`,
  [b4-8-live-latency.json](b4-8-live-latency.json), and the five walkthrough sessions.
- **The fallback**: [demo-fallback.webm](demo-fallback.webm) is 49 s and unedited, recorded
  at `9a5cf31` against a clean tree.
- **The checks**: `make ci` runs 505 tests and 11 structural checks, all green at close.
  **`pr.yml` has never run, because the repository has no remote.** Every CI claim in these
  documents means `make ci` on the Lead's machine until someone pushes it.

## 5. What is left, and what it would take

None of these block the conclusion. Each would change a number if someone picked it up.

| Item | Why it is open | To close it |
| --- | --- | --- |
| **E13** runbook peer dry-run | Needs a person who did not write the runbook | One peer, about an hour, following P1–P8 cold |
| **Reviewer sign-off** (U3) and the **G2/G3 branch lines** | Both are the reviewer's by the plan, and both are left blank rather than filled in by the author | The reviewer reads §1 and fills them in. The recommendation on file is **G2-B / G3-cached**, and the conclusion above holds under any branch |
| **U4** C10.1 contingency | A conversation between the tech lead and the DM about the overrun | Now a retrospective item — see §6 |
| **Behavior κ disagreement** | One held-out step has two readings and no adjudication | A 10-minute adjudication. It moves κ between 0.550 and 0.401 and nothing else |
| **D6** judge output validation | The judge sometimes emits JSON fragments inside its rationale. The page trims them for display; stored reports are left as the model wrote them | Validate or repair judge output at parse time, then re-record the cassettes |
| **SE-\* seeded reports** at an older prompt bundle | Re-judging them is a re-measurement of M2-6 (10 live calls), not a rebuild | `make seeded-errors` at the shipping bundle. Recall's raw evidence is already at the shipping bundle |
| **Unverifiable items stop answering** | Seen on 3 of 3 items, too few to claim | A pre-registered set of ~20 unverifiable vs matched solvable items, on two pins |

## 6. Cost, reported honestly

**Lead hours: 97.9 h against 48 h planned for the whole PoC** (and a Month-1 allocation of
12 h). The Lead figure has been frozen at 97.4 h since 16 Sep. The only addition is the
0.5 h spent running the five walkthrough sessions. Work executed by the agent after
[amendment 002](../../plan-amendment-002-no-human-capacity.md) is booked at 0.0, as the
amendment specifies. That keeps the Lead figure honest, but it also means the figure
understates the total effort after 16 Sep. Every cut lever (L1–L4, L6) was spent.
The session-by-session ledger was removed from the tree on 30 Sep 2026 and remains in git history.

**The lesson worth carrying into the next PoC is about sequencing, not scope.** The plan
put measurement before UI so that a negative result would arrive while hours remained, and
it did: G2 landed on 16 Sep with the shortfall already visible. What overran was
**labelling and re-measurement**. At least three times, a single run was read as a result and later
corrected ([findings §15](findings.md) and the entries beside it). The instrument's
run-to-run spread is larger than several of the effects it was built to measure, and any
follow-on should budget for repeated runs from the first day.

## 7. Record-keeping

Four defect classes recurred throughout and are worth naming for whoever inherits the
repo. Each one turned up again during this close-out:

1. **Inference from a single run.** A percentile at n=14 rests on one observation, and κ at
   n=50 moves 0.149 on one label.
2. **Works only on the author's machine.** `.env.example` left the shipping pins blank until
   28 Sep, so a clean clone could not rebuild the demo.
3. **Checks that exist but never run.** `stamp-check` never ran until 23 Sep and
   `test_runs.py` never ran until 28 Sep, and `pr.yml` has never run at all.
4. **Deleted scope that goes stale.** E2 was recorded as impossible for 11 days, for 10 of them while the
   architecture already supported it.
