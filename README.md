# Reasoning Lens

An instrument that makes a language model's reasoning **measurable** rather than merely
visible: three strategy arms over the same problem bank, span-tree ingest, deterministic
segmentation, behavior classification, and a calibration page that publishes the agreement
numbers whatever they turn out to be.

**Status: CLOSED 28 Sep 2026.** Read [`docs/poc-conclusion.md`](docs/poc-conclusion.md)
first — the answer to the hypothesis, every success criterion's final state, and what is
left for anyone who picks this up. [`docs/technical-documentation.md`](docs/technical-documentation.md)
is the single technical reference behind it: architecture, data contract, method, results.
The notes below are the working record and are kept as they were written.

**To see the demo from a clean clone:**

```
make install PY=python3.12
cp .env.example .env      # carries the shipping pins -- the cassettes were recorded at them
make demo-data            # cassettes -> spans -> 14 reports, stamped. Offline, no key
make fe-build-measured    # the static export
make serve-api            # http://localhost:8000
make smoke                # 26/26, with the provider key stripped
```

See [`docs/ledger.md`](docs/ledger.md) for actuals, [`docs/findings.md`](docs/findings.md)
for the five results that contradicted the plan, and
[`../month-1-task-breakdown.md`](../month-1-task-breakdown.md) for the plan this repo
executes — as amended by [plan amendment 001](../plan-amendment-001-local-hybrid.md).

> **The shortest honest summary of this project so far:** the instrument works, and four of
> the five phenomena it was pointed at are smaller than the plan expected. The fifth — that
> a cheap judge catches seeded errors without crying wolf — is the one that came back
> positive, and even that arrived with a miss worth more than its eight hits.

## The runtime, in one line

**A local model generates the reasoning; OpenAI analyses it.** Generation must hand back its
raw reasoning text, which a hosted reasoning API will not do — and the examiner should be a
different model from the subject, or the analyzer is grading its own homework. Local-only is a
supported configuration behind one switch, and both are measured and reported
([ADR-001](docs/decisions/ADR-001-provider.md)).

**Nothing is deployed.** The demo runs from a laptop ([ADR-003](docs/decisions/ADR-003-hosting.md)).

## Quick start

```
make install PY=python3.12
make ci                  # everything a PR runs -- no model, no key, no network

make models              # pull the local generation model (~13 GB)
make pin-local           # record the pin tuple; paste into .env
make spike-s1            # does the local model hand back raw reasoning?
make spike-s6            # can it call tools? GATES ARM 3 -- run before W3
make traps               # M1-5: which declared traps actually reproduce?
make arm-contrast        # which items separate the arms? (ADR-004's control group)
make spans               # replay every item from cassettes -- no GPU, no network
make spike-s3            # S3: what batch size does the classifier tolerate?
make spike-s4            # S4: do injected cues move the answer? (M2-9's go/no-go)

make report ARGS="--item mb-08"   # span trees -> a ReasoningReport
make record-cassettes             # M1-14: record the analysis tier, once per prompt bundle
make classify-reliability ARGS="--runs 20"   # M1-9's DoD. COSTS SPEND
make draw-sample                  # M1-11: the random-90, drawn ONCE before any label
make label ARGS="--annotator you" # M1-11: the blind labelling tool
```

## What exists today

| Area | State | Owner |
| --- | --- | --- |
| C2.1 repo tree, `reasoning-lens-analyzer` package | ✅ | M1-0 |
| C2.2 boundary contract (import-linter + provider-symbol grep), **proven by a reverted violation** | ✅ | M1-0 |
| C7.2 every-PR CI job set — 10 jobs (`rubric-drift` added in W4) | ✅ | M1-0 / M1-11 |
| C5.4 held-out label protection | ✅ wired, dormant until the freeze | M1-0 / M2-1 |
| C2.3 version + cache-key discipline | ✅ | M1-0 |
| Hybrid runtime decided; pin is a tuple, not an id | ✅ | ADR-001 |
| S1 reasoning-fidelity — local **and** OpenAI, both run | ✅ [S1-provider.md](docs/spikes/S1-provider.md) | M1-1 |
| S6 local tool-calling — **gated arm 3**, 20/20 | ✅ [S6-tools.md](docs/spikes/S6-tools.md) | M1-16 |
| ~~S5 DNS delegation~~ | ❌ **cancelled** — nothing is deployed | ADR-003 |
| Runner arms 1-2, provider abstraction, OTEL emission | ✅ | M1-6 |
| Problem bank, 14 items under L1, checkers + their contract | ✅ | M1-4 |
| Trap reproduction — **measured, DoD not met (0/16 over 120 runs); floor withdrawn** | ✅ [ADR-005](docs/decisions/ADR-005-traps-do-not-reproduce.md) accepted | M1-5 |
| Arm contrast — **0 of 16 items separate arms 1 and 2; arm 3 rescues 3** | ⚠️ [ADR-006](docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) | M1-5 / M1-7 |
| Runner arm 3 — ReAct loop, calculator + lookup, TOOL spans | ✅ **14/14 on the bank** | M1-7 · [ADR-007](docs/decisions/ADR-007-react-arm-on-the-provider-layer.md) |
| `NormalizedTrace` / `Step` contracts (C3.2) + OTEL ingest | ✅ | M1-8 |
| Deterministic segmenter + 12 goldens — **frozen at `segmenter-frozen-v1`** | ✅ [ADR-008](docs/decisions/ADR-008-segmenter-token-unit.md) | M1-8 |
| S3 — batched classification; decides M1-9's batch size | ✅ [S3-batching.md](docs/spikes/S3-batching.md) | M1-12 |
| Analysis tier pinned — `gpt-5-mini` / `gpt-5`, both probed live | ✅ **G0 is 6/6** | M1-1 |
| Behavior classifier v0 — chunked, repair retry, degrade-not-fabricate | ✅ | M1-9 |
| `ReasoningReport` JSON Schema + 4 fixtures — **the G1 freeze** | ✅ | M1-10 |
| `python -m rlens` — span trees → a report, end to end | ✅ | M1-10 |
| Rubric v1, blind labelling tool, the random-90 draw | ✅ tooling · ⛔ **40 labels need a human** | M1-11 |
| Cassette recording + offline replay — **49 analysis cassettes; the whole bank replays with the socket broken** | ✅ | M1-14 |
| S4 — cue injection — **0 of 48 trials flipped, all four cue types** | ✅ [ADR-009](docs/decisions/ADR-009-cue-injection-does-not-reproduce.md) | M1-13 |
| Behavior taxonomy — **82.3% `linear`** over 3,579 rows; `backtracking` **2.0%**, `backward_chaining` **0.2%** | ⚠️ [ADR-010](docs/decisions/ADR-010-the-taxonomy-barely-populates.md) **+ amendment** | M1-9 / M2-4 |
| **Judge recall — 8/10 seeded errors, 0 false flags on 24 known-good steps** | ✅ **B4 #3 met** · [ADR-012](docs/decisions/ADR-012-judge-thresholds.md) | M2-6 |
| Calibration scoring CLI — κ checked against sklearn to 10 dp | ✅ | M2-13 |
| Escalation tier · consistency checker | ⏳ built, off behind flags until their numbers exist | M2-5 / M2-8 |
| Faithfulness panel — **publishes the zero, with its denominator** | ✅ | M2-9 |
| Backend (C4.9) — allowlisted, cache-first, fail-closed breaker | ✅ [ADR-011](docs/decisions/ADR-011-no-redis.md) — **no Redis** | M3-1a / M3-3 / M3-7 |
| Frontend — 8 surfaces, static export, nothing running | ✅ | FE-1…FE-11 |
| **Same-origin serving — the backend mounts the export**, traversal refused, `/api` unshadowed | ✅ | FE-9 |
| Measured-data build — the shipping export, 17 item pages, all 10 trace states | ✅ | FE-9 |
| Analyzer wheel — installs in a clean venv, ingests third-party spans | ✅ | M3-8 |
| Runbook — six procedures, **each executed before being written** | ✅ | M3-5a |
| G3 ship checklist — **13 closed, 2 deleted, E13 unmet at close** | ✅ closed · [g3-ship-checklist.md](docs/g3-ship-checklist.md) | M3-9 |
| Calibration frame — random-90 **and** the enriched draw, **which came up 31 of 60** | ⚠️ t13 fired | M1-11 / M2-14 |

Weeks 1–4 are closed and W5 is well past its budget. **G0 is 6 of 6 and G1 is 10 of 10** —
the last box, offline cassette replay, closed as a by-product of the warm-cache run. **Two
things need a human and no amount of code substitutes for either**: M1-11's 40 labels, and
G3's five walkthrough testers. **Month 2's critical path is blocked behind the first of
them** — M2-3, M2-5, M2-7, M2-8 and M2-10a all sit behind dev labels that only a person can
write.

**G0 is 6 of 6.** The last check — the analysis tier pinned to
an exact dated id — was blocked on a key for three weeks and closed in W4 the day one
arrived. Closing it also turned ADR-001's central premise from an expectation into a
measurement: asked the S1 probe, `gpt-5-mini-2025-08-07` billed **384 reasoning tokens and
returned 0 characters of reasoning text**. The local runtime returns 2,535 for the same
probe. Arm 2 cannot be built on OpenAI — not "should not", cannot.

### Three W4 findings, in the order they will matter to a reader

**1. The behavior taxonomy barely populates — and the first reading of it was wrong.**
One full bank × 3 arms pass produced `linear` 252, `verification` 35, `subgoal_setting` 22,
`backward_chaining` 1, **`backtracking` 0** — of 310 steps. **Twelve passes put
`backtracking` at 2.0%, firing 1–15 times per run: rare, not absent.** ADR-010 had read a
corpus property off n=1 run of a *non-deterministic* classifier, which is the mistake
ADR-005 and ADR-006 each refused. The skew itself stands at **82.3% `linear`**, and that is
the part that matters for κ. No trace contains all five
classes, so §6.3's "harvest `report_nominal` from a real run" is not achievable, and κ's
per-class F1 will be undefined for classes with no instances. This is the third time a
phenomenon the plan assumed has failed to appear on this model, after
[ADR-005](docs/decisions/ADR-005-traps-do-not-reproduce.md) (traps) and
[ADR-006](docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) (arm separation).

**2. `step_id` was not unique across the corpus.** `direct:direct-llm-0:0` named the first
step of all fourteen items; 310 steps collapsed to 155 distinct ids. C3.2 calls it "the
join key for every label ever written" and it was not a key. Found by M1-11's sampling draw
**before a single label existed**, which is exactly what the plan's ordering buys.

**3. The analysis deadline was decorative.** A single call ran **969 seconds against a
110-second `ANALYSIS_DEADLINE_S`**: `urlopen(timeout=…)` bounds socket operations, and the
block was inside the call. Now enforced as a wall-clock budget. C11 budgets 18 s for
classify+triage and this tier does not meet it — a measured fact for the M3 latency
conversation rather than a surprise.

**One open decision is on the critical path for the demo, not for G1.**
[ADR-006](docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) is *Proposed*: arms 1 and
2 do not separate on accuracy anywhere in the bank, because arm 1's `low` effort is
**adaptive** rather than shallow — 3 reasoning tokens on an easy item, 407 on a hard one.
So B4 #7's accuracy claim needs re-wording, and what FE-1 can feature is the **cost**
contrast (verified: 1.2×–13.3× for the same answer on 11 of 11 items) plus the **tool**
contrast (arm 3 vs arms 1–2 on the three `tool_required` items — the one wrong→right row
this bank contains, and unverified until M1-7 lands).

M1-7 then confirmed option A's half of that on corpus evidence: **arm 3 answers 14/14
where arms 1 and 2 manage 11/14**, and the three it rescues are `tool_required` lookups. On
`mb-08` the thinking arm spent **3,966 reasoning tokens failing to recall a fact that does
not exist** while the tool arm spent 80 and looked it up — see
[`problem-bank/arm-contrast.md`](problem-bank/arm-contrast.md).

M1-5's DoD is kept as a strict `xfail` so the shortfall cannot be lost and cannot quietly
drift in either direction — see `analyzer/tests/test_trap_reproduction.py`.

## The invariants (C0.2)

**I1** — the analyzer is a standalone package whose only input is an OTEL/OpenInference
span tree. It never imports `backend/`, `frontend/` or `problem-bank/`, and provider payload
shapes appear only in `llm.py` and `ingest/otel.py`. This is enforced in CI from Week 1, not
by convention: `.importlinter` plus `scripts/check_provider_symbols.sh`, duplicated in
`analyzer/tests/test_boundaries.py` so a developer finds out before pushing.

**The segmenter is frozen.** `step_id` is `"{strategy}:{span_id}:{ordinal}"` and every
label written in Month 2 joins on it, so a change to `analyzer/src/rlens/segment.py` after
labelling begins silently detaches every label from its text. The tag `segmenter-frozen-v1`
marks the frozen state; `analyzer/tests/fixtures/segmenter/` records what it means, and
`test_segmenter_deterministic` asserts each fixture is byte-identical across three runs.
A diff in a golden is a question about whether the freeze is being broken, not a test to
update — see [`calibration/sampling.json`](calibration/sampling.json).

**I3** — a published number is reproducible or it is not published. Every version travels
with every report and forms the cache key. Under a local model that is **stricter** than the
plan's original hosted pin: a hosted endpoint can change under a fixed id, but a model file
digest cannot ([ADR-001](docs/decisions/ADR-001-provider.md)).

## Layout

See C2.1 in the implementation plan. Briefly: `analyzer/` is the product; `backend/` serves
it; `frontend/` is a static export mounted by the backend; `problem-bank/`, `calibration/`
and `faithfulness/` hold the data and the measurement; `docs/decisions/` holds the ADRs.
