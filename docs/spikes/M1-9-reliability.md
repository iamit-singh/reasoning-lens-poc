# M1-9 — the classifier's parse-failure rate, measured

| | |
| --- | --- |
| **DoD** | a valid row for every step across the bank × 3 arms, **parse-failure rate < 2% over 20 consecutive runs** |
| **Result** | **1 failure in 1,058 calls — 0.095%. MET.** |
| **Tier** | `gpt-5-mini-2025-08-07`, hybrid · prompt bundle `97667881c779` · chunk cap 25 |
| **Record** | `docs/spikes/M1-9-raw/m1-9-reliability.full.json` · re-run with `make classify-reliability ARGS="--runs 20"` |

## The numbers

| | |
| --- | --- |
| Runs recorded | **23** — 22 graded, 1 excluded as a network outage |
| Calls | **1,058** |
| Repaired by the retry | 15 (1.42%) — the C4.3 mechanism working, not a failure |
| **Degraded (parse failure)** | **1 → 0.095%** |
| Rows returned | **6,498 for 6,498 steps** in non-degraded traces |

## "20 consecutive" — what actually happened, stated plainly

**It took three attempts, and twice the machine was the reason.** The first attempt lost 13
runs of good data when the laptop slept mid-run and the harness — which wrote its record
only after the loop — was killed at run 15. The second reached run 17 before DNS failed and
every one of 42 traces returned `URLError`. The third added 6 more.

**The outage run is excluded from the rate, and the decision was made before the number was
seen.** The harness stops itself when *every* trace in a run hard-errors, because a
parse-failure rate computed over calls that never reached a model is not a low rate, it is
no rate at all. That guard was written after the first attempt, and it fired on its own at
run 17 rather than being applied retrospectively to make a figure look better.

So: **22 graded runs against a DoD asking for 20**, with one interruption between run 17 and
run 18. A reader who insists on strict consecutiveness has 17 runs and 767 calls with **zero**
failures; a reader who accepts the excluded outage has 22 runs and 1,058 calls with one.
Both are in the record and neither changes the verdict.

## The one failure, which is worth more than the 1,057 successes

    mb-09.thinking, chunk 1 of 2:
    after repair retry: step_id mismatch: 26 rows for 25 steps.
    Missing []; extra ['thinking:thinking-mb-09-root-llm-0:25']

**Nothing was missing. The model returned one row too many** — a label for step 25, which is
the first step of the *next* chunk. It had that step's text, because `render_prompt` sends
the preceding and following context so the "given only the preceding steps" question is
answerable, and it labelled one step past its instruction. The repair retry, handed exactly
that message, did it again.

> **This is the case that makes C4.3's rule worth having, and it is not the case the rule
> was written for.** The plan's example is a *missing* row — the instinct to fill row 17 of
> 25 with `linear`. The symmetrical instinct here is milder and more tempting: an extra row
> is harmless, just drop it. But the extra row is evidence the model was not doing what it
> was told, and a run that silently discarded it would have accepted 25 labels produced by a
> model that had stopped following the instruction — with nothing in the report saying so.

The arm degraded and rendered unannotated, which is the correct outcome: **one visibly
unlabelled trace in 23 runs, rather than 25 labels of unknown provenance.**

## What else the 6,498 rows say

| | |
| --- | --- |
| `linear` | **83.0%** |
| `verification` · `subgoal_setting` | 8.0% · 7.5% |
| `backtracking` | 1.3% |
| `backward_chaining` | **0.2%** |
| `unverifiable` · `sound` · `unsound` | 50.7% · 43.8% · 5.6% |
| Identical behaviour/validity confidences | 29.8% |

Three of these have their own entries in [findings.md](../findings.md): the skew that makes
κ hard to read (§4), the `unverifiable` mass that turns out to be concentrated in the
fabrication traces (§7), and the confidence pairs that a 17-row sample had put at 64.7%
(§6). **The corpus this measurement was run for is not the corpus it ended up measuring** —
it was bought to close one DoD and it settled three other questions on the way.

## What this does not show

One tier, one prompt bundle, one chunk size, 14 bank items. The rate is 1 in 1,058 with a
95% confidence interval of roughly **0.002% – 0.53%** — comfortably under 2% at either end,
which is the only claim being made. It says nothing about whether the labels are *correct*;
that is κ, it needs human labels, and M1-11 is where it starts.
