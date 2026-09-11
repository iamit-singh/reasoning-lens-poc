# Reasoning Lens

An instrument that makes a language model's reasoning **measurable** rather than merely
visible: three strategy arms over the same problem bank, span-tree ingest, deterministic
segmentation, behavior classification, and a calibration page that publishes the agreement
numbers whatever they turn out to be.

**Status: Month 1, Week 3.** See [`docs/ledger.md`](docs/ledger.md) for actuals and
[`../month-1-task-breakdown.md`](../month-1-task-breakdown.md) for the plan this repo
executes — as amended by [plan amendment 001](../plan-amendment-001-local-hybrid.md).

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
```

## What exists today

| Area | State | Owner |
| --- | --- | --- |
| C2.1 repo tree, `reasoning-lens-analyzer` package | ✅ | M1-0 |
| C2.2 boundary contract (import-linter + provider-symbol grep), **proven by a reverted violation** | ✅ | M1-0 |
| C7.2 every-PR CI job set (9 jobs, all green) | ✅ | M1-0 |
| C5.4 held-out label protection | ✅ wired, dormant until the freeze | M1-0 / M2-1 |
| C2.3 version + cache-key discipline | ✅ | M1-0 |
| Hybrid runtime decided; pin is a tuple, not an id | ✅ | ADR-001 |
| S1 reasoning-fidelity harness (local + OpenAI) | ✅ written · ⏳ needs the model pulled | M1-1 |
| S6 local tool-calling harness — **gates arm 3** | ✅ written · ⏳ needs the model pulled | new, W2 |
| ~~S5 DNS delegation~~ | ❌ **cancelled** — nothing is deployed | ADR-003 |
| Runner arms 1-2, provider abstraction, OTEL emission | ✅ | M1-6 |
| Problem bank, 14 items under L1, checkers + their contract | ✅ | M1-4 |
| Trap reproduction — **measured, DoD not met (0/16 over 120 runs); floor withdrawn** | ✅ [ADR-005](docs/decisions/ADR-005-traps-do-not-reproduce.md) accepted | M1-5 |
| Arm contrast — **0 of 16 items separate arms 1 and 2; arm 3 rescues 3** | ⚠️ [ADR-006](docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) | M1-5 / M1-7 |
| Runner arm 3 — ReAct loop, calculator + lookup, TOOL spans | ✅ **14/14 on the bank** | M1-7 · [ADR-007](docs/decisions/ADR-007-react-arm-on-the-provider-layer.md) |
| `NormalizedTrace` / `Step` contracts (C3.2) + OTEL ingest | ✅ | M1-8 |
| Deterministic segmenter + 12 goldens — **frozen at `segmenter-frozen-v1`** | ✅ [ADR-008](docs/decisions/ADR-008-segmenter-token-unit.md) | M1-8 |
| S3 — batched classification; decides M1-9's batch size | ✅ [S3-batching.md](docs/spikes/S3-batching.md) | M1-12 |
| Behavior classifier, `ReasoningReport` | ⬜ W4 · **G1** | M1-9, M1-10 |
| Backend, frontend | ⬜ W5+ (frontend starts after the G1 freeze) | M2/M3 |

Weeks 1 and 2 are closed. **G0 is 5 of 6** — the open check is the analysis tier, blocked
on an OpenAI key (`MODEL_ANALYZE` unset), which is not the implementer's to unblock.

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
