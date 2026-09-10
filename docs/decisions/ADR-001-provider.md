# ADR-001 — Provider choice and model pins

| | |
| --- | --- |
| **Status** | **Proposed — blocked on execution of S1.** Not yet a decision. |
| **Date raised** | 2026-09-10 (W1) |
| **Decision owner** | Tech lead (Appendix D #2) |
| **Gate** | **G0**, end of W1 |
| **Produced by** | M1-1 (S1 spike) |
| **Blocks** | M1-6 (`llm.py` abstraction), `MODEL_PIN` in every cache key (C2.3), B4 #7 cost-of-thought |

## Context

Month 1's first purchase is **a `no` that arrives cheaply**. S1 asks whether the chosen
provider returns full, unsummarised thinking text via API, with token accounting. If it
does not, there is no product in the shape the PoC describes, and the plan's own answer —
fall back to a hosted open-weight R1-class model for arm 2 (B6.5) — is a **Week-1
decision costing 1.5 hours**, not a Month-3 discovery costing the PoC.

Two halves, both load-bearing:

1. **Full, unsummarised thinking text.** This is the product. A provider summary is a
   different artifact with a different claim attached to it.
2. **`reasoning_tokens` in usage accounting.** This is B4 #7. Cost-of-thought is
   unmeasurable without a reasoning-token count, and estimating it from output tokens is
   exactly the kind of assertion this PoC exists to replace with measurement.

## Decision

*Not yet taken.* To be filled by the S1 run.

```
MODEL_PIN       = <exact dated generation-model id>
MODEL_TRIAGE    = <exact dated id>
MODEL_ESCALATE  = <exact dated id>
```

> **Never a floating alias.** G0 check 4. `spikes/s1_provider_fidelity.py` refuses to
> probe an aliased id, so the constraint is enforced at the point of measurement and not
> only asserted here.

## Candidates and what each returned

*Filled from `docs/spikes/S1-raw/s1-results.json`.*

| Provider / tier | Thinking text returned? | Complete or elided? | `reasoning_tokens`? | Returned-vs-billed ratio | Provider documents summarisation? |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

**How the ratio is read.** The probe estimates tokens in the returned thinking text and
divides by the provider's reported `reasoning_tokens`. ≈ 1.0 means the text we received is
the text the model was billed for. Well below 1.0 is the signature of summarisation. The
estimate is ~4 chars/token and deliberately crude; refine with the provider tokenizer
before quoting the ratio to two decimals.

## G0 checklist (§8.1)

| # | Check | Pass condition | Result |
| - | ----- | -------------- | ------ |
| 1 | Thinking text returned via API | present and complete | — |
| 2 | Thinking text is **not** a provider summary | token count ≈ `reasoning_tokens`; provider docs confirm | — |
| 3 | `reasoning_tokens` exposed in usage | present and plausible against a hand count | — |
| 4 | `MODEL_PIN` is an **exact dated model id** | recorded here and in config | — |
| 5 | Triage and escalation tiers identified | `MODEL_TRIAGE`, `MODEL_ESCALATE` recorded | — |
| 6 | This ADR committed | in `docs/decisions/` | ✅ (as *Proposed*) |

## Consequences, branched in advance

The branches are decided now so the gate is a reading rather than a discussion.

| S1 finding | Consequence | Recorded where |
| --- | --- | --- |
| No candidate returns unsummarised thinking | Arm 2 falls back to a **hosted open-weight R1-class model** (B6.5). **Decided in W1.** | This ADR + the reviewer, same week |
| Thinking arrives, `reasoning_tokens` does not | B4 #7 degrades from **measured** to **estimated**. A published caveat and an ADR entry — never a silent substitution | This ADR + the calibration page |
| Thinking arrives only as a provider summary | The PoC continues with `trace_quality: "provider_summarised"` surfaced in the UI throughout, and **the reviewer is told in W1** — it changes what the demo claims | `ReasoningReport` field (G1) + FE-8 banner |
| A candidate passes all six checks | Pin it. Re-run S1 on any `MODEL_PIN` bump — the pin is a cache-key input, and a bump also forces re-calibration and a faithfulness re-run (B7.4) | This ADR |

## Execution status — what is blocking

`spikes/s1_provider_fidelity.py` is written, lint-clean, and self-tested against the
no-key and aliased-id paths. It needs **one thing** to produce the finding:

- **an API key for each candidate tier** (`ANTHROPIC_API_KEY`, etc.) in the local
  environment. No key is present in the dev environment as of 2026-09-10.

Run, once a key exists:

```
make spike-s1 ARGS="--provider anthropic --model <exact-dated-id>"
```

Cost is a few cents per candidate. **This is the only Week-1 item that cannot be closed
without an external input**, and it is the item G0 turns on — so it is the one to chase
first. See [`../spikes/S1-provider.md`](../spikes/S1-provider.md) for the write-up
template and the trap to avoid.
