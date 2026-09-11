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
| Trap reproduction — **measured, DoD NOT met (0/16 over 120 runs)** | ⚠️ [ADR-005](docs/decisions/ADR-005-traps-do-not-reproduce.md) | M1-5 |
| Runner arm 3 (ReAct), segmenter, classifier, `ReasoningReport` | ⬜ W3–W4 | M1-7 … M1-10 |
| Backend, frontend | ⬜ W5+ (frontend starts after the G1 freeze) | M2/M3 |

Weeks 1 and 2 are closed. **G0 is 5 of 6** — the open check is the analysis tier, blocked
on an OpenAI key (`MODEL_ANALYZE` unset), which is not the implementer's to unblock.

**One open decision is on the critical path for the demo, not for G1:**
[ADR-005](docs/decisions/ADR-005-traps-do-not-reproduce.md) is *Proposed* and asks whether
to withdraw the trap floor and re-point FE-1's featured comparison at the verified
difficulty contrast. M1-5's DoD is recorded as a strict `xfail` so the shortfall cannot be
lost and cannot quietly drift — see `analyzer/tests/test_trap_reproduction.py`.

## The invariants (C0.2)

**I1** — the analyzer is a standalone package whose only input is an OTEL/OpenInference
span tree. It never imports `backend/`, `frontend/` or `problem-bank/`, and provider payload
shapes appear only in `llm.py` and `ingest/otel.py`. This is enforced in CI from Week 1, not
by convention: `.importlinter` plus `scripts/check_provider_symbols.sh`, duplicated in
`analyzer/tests/test_boundaries.py` so a developer finds out before pushing.

**I3** — a published number is reproducible or it is not published. Every version travels
with every report and forms the cache key. Under a local model that is **stricter** than the
plan's original hosted pin: a hosted endpoint can change under a fixed id, but a model file
digest cannot ([ADR-001](docs/decisions/ADR-001-provider.md)).

## Layout

See C2.1 in the implementation plan. Briefly: `analyzer/` is the product; `backend/` serves
it; `frontend/` is a static export mounted by the backend; `problem-bank/`, `calibration/`
and `faithfulness/` hold the data and the measurement; `docs/decisions/` holds the ADRs.
