# S1 — Provider thinking-trace fidelity

| | |
| --- | --- |
| **Task** | M1-1 · W1 · 1.5 h · **Gate G0** |
| **Status** | Harness written and self-tested; **run pending an API key** |
| **Decision doc** | [`../decisions/ADR-001-provider.md`](../decisions/ADR-001-provider.md) |
| **Harness** | `spikes/s1_provider_fidelity.py` · `make spike-s1` |

## The question, precisely

Does the API return **full, unsummarised** thinking text, and are `reasoning_tokens`
exposed in usage accounting?

## Method

One representative `multi_step` problem, run against each candidate provider tier with
thinking enabled. The probe problem lives in the harness rather than in the problem bank
because the bank (M1-4) does not exist until W2 and S1 must not wait for it. It is a
four-step arithmetic chain with a single checkable integer answer (18678), long enough to
force several reasoning steps and not memorisable as a stock puzzle.

Captured per candidate, verbatim, into `docs/spikes/S1-raw/`:

- the raw response,
- whether thinking text is complete or elided (including any withheld/redacted blocks),
- the usage block verbatim,
- whether the provider documents summarisation,
- the answer's correctness (a sanity check on the probe, not a measure of the provider).

## ⚠️ The trap this spike exists to avoid

**Do not let S1 quietly succeed.** The failure mode is running one prompt, seeing text
that looks like thinking, and moving on.

So the harness does not report "thinking text: present". It reports the **ratio** of
estimated tokens in the returned text to the provider's own `reasoning_tokens`, and G0
check 2 turns on that ratio, not on the presence of text. A large gap is the signature of
summarisation. The harness also refuses to probe a floating model alias, because a fidelity
finding attached to an alias expires silently.

## Findings

*To be filled by the run.*

| Candidate | Check 1 text | Check 2 unsummarised | Check 3 `reasoning_tokens` | Ratio | Verdict |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## What this changes downstream

| If | Then |
| --- | --- |
| G0 passes | `llm.py` (M1-6) is written against this provider; `MODEL_PIN` enters every cache key (C2.3) |
| Thinking is summarised | `trace_quality: "provider_summarised"` becomes a `ReasoningReport` field frozen at G1, and a permanent UI banner (FE-8) — the demo's central artifact is a summary and the reviewer hears it in W1 |
| No `reasoning_tokens` | B4 #7 is estimated, not measured; the calibration page carries the caveat |
| No candidate qualifies | Arm 2 becomes a hosted open-weight R1-class model (B6.5), decided in W1 |
