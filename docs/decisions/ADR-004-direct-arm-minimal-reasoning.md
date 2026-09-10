# ADR-004 — Arm 1 is a *minimal*-reasoning baseline, because "off" is not purchasable

| | |
| --- | --- |
| **Status** | **Accepted** — 10 Sep 2026 (W2) |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | Plan §C4.1 (arm 1 — "thinking **off**"), and the wording of B4 #7's cost-of-thought claim |
| **Evidence** | S7 (below), run during M1-6 · `analyzer/tests/test_span_contract.py::test_the_two_arms_ran_in_different_regimes` |
| **Depends on** | [ADR-001](ADR-001-provider.md) — the same-model rule is what forecloses the easy fix |

## Context

C4.1 defines arm 1 as *"Same frontier model, thinking **off**, system prompt forbids
step-by-step. This is the **cost-of-thought baseline**, not an accuracy foil."* The arm's
entire job is to answer the question **what does the thinking buy?** — which requires a
comparison point that did not think.

M1-6's first end-to-end run produced arm 1 with **467 reasoning tokens**. Not a bug in the
runner: the system prompt correctly suppressed *visible* work (the answer was 2 tokens
long), and the model reasoned anyway, out of sight and on the bill.

**`gpt-oss:20b` is a reasoning model. It thinks whether or not you ask it to.** Four ways
of asking it to stop were measured on the same prompt:

| Request | Reasoning returned | Honoured? |
| --- | --- | --- |
| Omit `reasoning_effort` entirely *(what the runner did first)* | 2918 chars | — this is the **default**, and it sits near arm 2's |
| `reasoning_effort: "none"` | **2918 chars** | **no — silently ignored** |
| ollama native `"think": false` | **2918 chars** | **no — silently ignored** |
| `reasoning_effort: "low"` | **131 chars** | **yes** |

> **The two switches that claim to disable thinking do not error, do not warn, and return
> a full trace.** A runner that sent `think: false` and trusted it would have published a
> "no-thinking baseline" that had thought 2918 characters — and every cost-of-thought
> number in the study would have been wrong with nothing visibly broken. This is the same
> failure shape S1 was built to catch (`thinking text: present` is not a measurement) and
> the same shape as the S2 probe defect (an unexercised path reads as a missing one).

Omitting the parameter is the worst of the four, and it is what the plain reading of
"thinking off" produces: the arms then differ only in their system prompt while thinking
almost identically, and arm 1 stops being a baseline for anything.

## Decision

**Arm 1 requests `reasoning_effort: "low"`. It is renamed, in every place a reader meets
it, from a *no*-reasoning baseline to a *minimal*-reasoning baseline.**

Three parts, and the third is the one that makes it safe:

1. **`DIRECT_EFFORT = "low"` lives in `rlens.runner.arms`, not in `.env`.** Arm 1's regime
   is a property of the experiment, not a deployment knob. A cost-of-thought number
   produced under a different arm-1 effort is a different measurement, and it should
   require a code change and a re-read of this ADR, not an environment variable.

2. **Both arms send an explicit effort.** Arm 1 `low`, arm 2 the pin's (`medium`). Neither
   inherits a runtime default, because the default is invisible in the trace and can
   change under us on a runtime upgrade.

3. **The separation is verified from the output, never from the request.**
   `check_regime_separation` fails the run when arm 1's reasoning exceeds 50% of arm 2's,
   and `test_span_contract.py` asserts it every PR. Because the provider silently ignores
   two of the four requests above, **the request is not evidence** — only the token counts
   are. On the probe the arms measure **144 vs 1453 tokens (10%)**, comfortably separated.

### What this changes about the claim the project can make

This is the honest part, and it is a real narrowing:

| Was going to say | Can actually say |
| --- | --- |
| "Thinking costs N tokens over not thinking" | "Thinking at `medium` effort costs N tokens over `minimal` effort" |
| Arm 1 as an absolute floor | Arm 1 as the **cheapest regime this model offers**, which is a floor for *this* model, not for reasoning in general |

**B4 #7's cost-of-thought figure must be reported with the two efforts named.** A reader
who assumes the baseline did not think will over-read every ratio on the page, and they
will be right to, because that is what "direct" implies. The scoreboard and the
calibration page both need the effort labels adjacent to the number — the same rule the
plan already applies to soundness and its measured precision.

## A consequence that is a finding, not a defect

At `low` effort, arm 1 answered the probe **18694**; the correct answer is **18678**, which
arm 2 got. Arm 1 got it *right* at the default effort earlier in the same session.

**This is the study working, not the baseline being rigged.** C4.1's warning is that arm 1
must not be an *accuracy foil* — that its prompt must not induce sloppiness. It does not:
the prompt asks for the best answer it can give without showing work, and the arm answers
in earnest. What changed is the reasoning budget, and a multi-step arithmetic chain is
exactly the shape of problem where less deliberation should cost accuracy.

That is a result worth having on day one. But it raises the stakes on M1-5's trap
engineering and on the bank's `easy` floor: **if every item separates the arms this
cleanly, the bank is measuring difficulty rather than strategy.** The 3 `easy` items are
what should show arm 1 matching arm 2 at a fraction of the cost — that contrast is the
finding, and a bank of nothing but hard items would hide it. Flagged into M1-4.

## Alternatives rejected

| Option | Why not |
| --- | --- |
| **Use a non-reasoning model for arm 1** | Breaks ADR-001's same-model rule. The arms would then compare vendors, not strategies, and the finding evaporates. This is the fix that looks obvious and is fatal. |
| **Keep "thinking off" and send `think: false`** | Measured: silently ignored. This is the option that would have shipped a wrong number quietly, and it is the reason for the output-side check. |
| **Strip the reasoning from arm 1's trace and report 0** | Fabrication. The tokens were generated and billed; a baseline that hides its own cost is worse than no baseline. |
| **Drop arm 1** | It still does its job — `low` vs `medium` is a real and measurable contrast, and the arm is also the accuracy comparison. A narrowed claim beats a deleted one. |
| **Wait for a runtime that supports disabling reasoning** | Not on a 3-month clock, and `low` is available now. Worth re-testing at the next runtime upgrade — the effort table above is cheap to re-run. |

## Consequences

- **`.env.example` documents the three ignored switches**, so the next person to try
  `think: false` finds out in the config file rather than in a wrong number.
- **The regime check is a permanent part of the span contract**, not a one-off spike
  assertion. A runtime upgrade that changes what `low` means fails CI.
- **M1-4 (the bank) gains a requirement**: the `easy` floor exists to produce items where
  the arms should *not* separate on accuracy. Without those, the cost-of-thought story
  collapses into "harder problems need more thinking", which nobody needed this project
  to learn.
- **Re-test at every pin change.** The effort table is four requests and belongs in the
  same session as `make pin-local`.
