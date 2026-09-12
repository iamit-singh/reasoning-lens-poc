# ADR-012 — Judge thresholds, and what the seeded errors found

| | |
| --- | --- |
| **Status** | **Proposed** — 12 Sep 2026 (W5, M2-6 run ahead of W7) |
| **Closes** | M2-18, which C10.3 names `ADR-002-thresholds.md` |
| **Evidence** | `docs/spikes/M2-6-raw/m2-6-seeded.json` · re-run with `make seeded-errors` |

> **On the name.** C10.3 calls this file `ADR-002-thresholds.md`, but ADR-002 is already
> *span emission*, filed in W2. Reusing the number would give this repository two ADR-002s
> and make every cross-reference ambiguous. The plan's *intent* — one document holding every
> threshold with the data that chose it — is what matters and is what this is.

## The headline: B4 #3 is met, and it was earned

**Judge recall 8 of 10 (80%) against a ≥ 70% target**, on ten hand-written mutations
(Appendix B) applied to five traces that answered correctly before anything was changed.

The number that makes it worth anything sits underneath it:

| | |
| --- | --- |
| Recall on seeded errors | **8 / 10** |
| **False flags on the same traces, unmutated** | **0 over 24 steps in 5 traces** |
| Collateral flags across the ten mutated runs | 4 |

**A judge that flags freely catches seeded errors by accident.** This one flagged nothing
at all on known-good text, so the eight hits are eight detections rather than eight
coincidences. That control is the reason the harness runs every trace twice.

This is **the first B4 criterion this project has met on measurement rather than
assumption**, after three that came back negative (traps, arm separation, cue flips).

## The two misses, which are more useful than the eight hits

### SE-01 — the judge restated a wrong sum and called it correct

The mutation changed `875 + 50 = 925` to `875 + 50 = 935`. The judge returned
`sound`, confidence **0.95**, with this rationale:

> *"Recomputes 12500\*0.074 by splitting into 0.07 and 0.004 yielding 875+50=935
> (correct)."*

**875 + 50 is 925.** The judge copied the wrong total out of the step, appended the word
*correct*, and expressed high confidence. It did not compute anything.

This matters beyond one case, because C4.4's escalation policy exists on the premise that
*arithmetic is precisely where cheap judges fail* (Part A §A6, ProcessBench) — and here is
that failure, reproduced, in this repository, on this tier. The policy's numeric-step rule
(escalate when a step contains a computation and `validity_confidence < 0.85`) **would not
have fired**: the confidence was 0.95.

> **The sharpest detail is what it did instead.** It flagged **three other steps** in the
> same trace. It sensed the trace was wrong and blamed the wrong steps — which is exactly
> the failure the correct-step rule exists to expose, and exactly what a recall number
> computed as "was the trace flagged anywhere" would have scored as a hit.

### SE-05 — the judge read the chain and not the problem

The item says the total must be **rounded down**. The mutation switched the step to nearest
rounding, 379 → 380. Verdict `sound`, confidence 0.85:

> *"Conversion gives 379.995 kW; rounding to nearest whole gives 380 (correct for nearest
> rounding)."*

The step is internally consistent with the rule *the step itself introduced*, and the judge
graded it against that rule rather than against the constraint in the prompt it was given.
A dropped constraint is invisible to a reader who only checks that each line follows from
the line above — which is a fair description of what this judge does.

## The finding nobody asked for: the error types are close to noise

Of the eight caught, **two named the right `error_type`**.

| Expected | Named | |
| --- | --- | --- |
| `arithmetic` | `arithmetic` | SE-03 ✅ |
| `unsupported_leap` | `unsupported_leap` | SE-10 ✅ |
| `logical` ×3 | `arithmetic` ×3 | SE-02, SE-04, SE-06 |
| `factual` | `unsupported_leap` | SE-07 |
| `unsupported_leap` | `logical` | SE-08 |
| `arithmetic` | `logical` | SE-09 |

`arithmetic` is applied to four of eight, including a unit conversion and a variable swap
where nothing is miscomputed. The taxonomy is not being used; it is being guessed at.

**Consequence: `error_type` must not appear on the calibration page as a measured
quantity.** It is fine in the flagged-step panel as *the judge's description of the
defect*, which is what the UI already calls it. It is not fine anywhere that implies the
category is reliable, and B4 has no criterion for it — a gap this ADR recommends leaving
open rather than inventing a target for at this n.

## Thresholds, with the data that chose them

| Threshold | Value | The data |
| --- | --- | --- |
| `validity_confidence` escalation floor | **0.70** *(unchanged)* | It selected nothing on the M2-4 prep sample (all confidences 0.75–0.95), and it would have selected neither miss here (0.95, 0.85). Kept **only because M2-4's full-corpus histogram has not run** — this is a threshold awaiting evidence, not one chosen by it |
| Numeric-step escalation floor | **0.85** *(unchanged, and now known to be insufficient)* | SE-01 is a numeric step the judge got wrong at 0.95. Raising the floor above 0.95 escalates nearly every numeric step, which C11's latency budget will not carry. **The lever is not this number** — see below |
| Seeded-error recall target | ≥ 0.70 | B4 #3. Met at 0.80 |
| Known-good false-flag rate | ≤ 1.0 per trace | B4 #4. Currently **0.0** |
| `unverifiable` counts as a hit | yes | The seeded step is defective; whether the defect is *wrong* or *uncheckable* is M2-2's adjudication. A judge that stopped and said "I cannot verify this" did not miss it |

### The recommendation the misses actually support

Not a confidence threshold. **Both misses are steps the judge was confident about**, so no
setting of a confidence floor separates them from the eight it got right without escalating
everything.

The two levers that do follow from the evidence:

1. **Escalate every step containing an explicit equality between numbers, regardless of
   confidence** — SE-01's shape. The volume is bounded (24 steps across five traces contain
   perhaps six such lines), and M2-5's cap already exists to hold it.
2. **Put the item's constraints in front of the judge as constraints**, not merely as the
   problem prompt — SE-05's shape. That is a prompt change, so it belongs to M2-3, is
   time-boxed, and runs against the dev set only.

Both are recorded here and **neither is implemented in this ADR**, because implementing a
prompt change on ten cases is how a prompt gets fitted to ten cases.

## What this does not show

n = 10, one pin, one analyzer tier, five traces, all from one arm. Recall of 80% has a 95%
Wilson interval of roughly **49–94%** — the point estimate clears the bar and the interval
straddles it. C5.5 requires that interval to be published beside the number, and M2-7 is
where it becomes a committed figure rather than a line in an ADR.
