# Reasoning Lens

An instrument that makes a language model's reasoning **measurable** rather than merely
visible: three strategy arms over the same problem bank, span-tree ingest, deterministic
segmentation, behavior classification, and a calibration page that publishes the agreement
numbers whatever they turn out to be.

**Status: Month 1, Week 1.** See [`docs/ledger.md`](docs/ledger.md) for actuals and
[`../month-1-task-breakdown.md`](../month-1-task-breakdown.md) for the plan this repo executes.

## Quick start

```
make install PY=python3.12
make ci
```

## What exists today

| Area | State | Owner |
| --- | --- | --- |
| C2.1 repo tree, `reasoning-lens-analyzer` package | ✅ | M1-0 |
| C2.2 boundary contract (import-linter + provider-symbol grep), **proven by a reverted violation** | ✅ | M1-0 |
| C7.2 every-PR CI job set (9 jobs, all green) | ✅ | M1-0 |
| C5.4 held-out label protection | ✅ wired, dormant until the freeze | M1-0 / M2-1 |
| C2.3 version + cache-key discipline | ✅ | M1-0 |
| S1 provider-fidelity harness | ✅ written · ⏳ **run blocked on an API key** | M1-1 |
| S5 DNS delegation | ⏳ **ticket drafted, not filed** | M1-3 |
| Runner arms, segmenter, classifier, `ReasoningReport` | ⬜ W2–W4 | M1-6 … M1-10 |
| Backend, frontend | ⬜ W5+ (frontend starts after the G1 freeze) | M2/M3 |

The two Week-1 items still open are both **asks of other people**, drafted and ready in
[`docs/day-1-unblock.md`](docs/day-1-unblock.md).

## The invariants (C0.2)

**I1** — the analyzer is a standalone package whose only input is an OTEL/OpenInference
span tree. It never imports `backend/`, `frontend/` or `problem-bank/`, and provider payload
shapes appear only in `llm.py` and `ingest/otel.py`. This is enforced in CI from Week 1, not
by convention: `.importlinter` plus `scripts/check_provider_symbols.sh`, duplicated in
`analyzer/tests/test_boundaries.py` so a developer finds out before pushing.

**I3** — a published number is reproducible or it is not published. Four versions travel
with every report and form the cache key (C2.3).

## Layout

See C2.1 in the implementation plan. Briefly: `analyzer/` is the product; `backend/` serves
it; `frontend/` is a static export mounted by the backend; `problem-bank/`, `calibration/`
and `faithfulness/` hold the data and the measurement; `docs/decisions/` holds the ADRs.
