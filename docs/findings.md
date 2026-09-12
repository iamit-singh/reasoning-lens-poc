# Findings

**What this project measured that it did not expect to measure.**

B0 Condition #5 commits this PoC to publishing whatever the numbers turn out to be. This
file is where that commitment is kept: one place for the results that contradicted the
plan, each with its evidence, its consequence, and the ADR that decided what to do about
it. The G2 measurement report reads from here rather than rediscovering them.

Nothing in this file is an apology. Every entry cost less than it would have cost later,
and every one of them was found by measuring something before building on it.

---

## The pattern, stated once

By the end of Month 1 this project had measured **four** phenomena the plan assumed would
be present, and found all four absent or far smaller than expected. W5 added four more
entries — one positive, one correction of this project's own work, one that reads as a
defect and is not, and one more phenomenon that turned out absent:

| # | The plan assumed | Measurement said | ADR |
| - | --- | --- | --- |
| 1 | 3 traps each reproducing a wrong chain in ≥ 3 of 5 runs | **0 of 16 candidates** over 120 runs | [ADR-005](decisions/ADR-005-traps-do-not-reproduce.md) |
| 2 | Extended thinking beats Direct on accuracy somewhere in the bank | **0 of 16 items** separate the two arms | [ADR-006](decisions/ADR-006-arms-1-and-2-do-not-separate.md) |
| 3 | A misleading cue moves the answer and the trace hides it | **0 of 48 trials** flipped, all 4 cue types | [ADR-009](decisions/ADR-009-cue-injection-does-not-reproduce.md) |
| 4 | Five behavior classes occur often enough to score per-class | **81% one class**; `backtracking` 0 of 310 | [ADR-010](decisions/ADR-010-the-taxonomy-barely-populates.md) |

> **This is not four failures. It is one finding, arrived at four times: the instrument
> works, and the effects it was pointed at are smaller than the plan expected.**

That sentence is the honest headline of Month 1, and it is a more interesting result than
the one the plan hoped for — because it is a result *about a model*, produced by an
instrument that was built to produce results about models, and it is falsifiable by anyone
who runs the same commands against a different pin.

**Every one of these is re-runnable in a single command.** A negative result that cannot be
re-measured is an assertion.

| Finding | Re-measure with |
| --- | --- |
| Traps | `make traps` |
| Arm separation | `make arm-contrast` |
| Cue injection | `make spike-s4` |
| Taxonomy coverage | `make taxonomy-coverage` |

---

## 1. Traps do not reproduce on this model

**Measured:** 0 of 16 hand-written trap candidates produced a plausible wrong chain in ≥ 3
of 5 runs, over 120 runs and two rounds of authoring.

**What it means.** There is no shallow regime on `gpt-oss:20b` to trap. The bank's `is_trap`
flag became a *declaration* with nothing behind it, so the floor was withdrawn and the four
claims were retired into `problem-bank/traps/candidates/` with a `retired_from` field — so
the reproduction log still renders them rather than erasing the attempt.

**What guards it:** `test_trap_reproduction.py` carries M1-5's DoD as a strict `xfail`, so
the shortfall cannot be quietly lost *or* quietly drift in either direction, and
`test_the_bank_makes_no_unearned_trap_claim` fails any new unearned claim.

## 2. Arms 1 and 2 do not separate on accuracy

**Measured:** across 14 bank items plus 5 deliberately harder candidates, **0 of 16
separations**. 11 items agreed; 3 were `tool_required` run without tools.

**Why.** Arm 1's `low` reasoning effort is **adaptive, not shallow** — 3 reasoning tokens on
an easy item, **407 on a hard one against arm 2's 423**. Harder items close the cost gap
without opening an accuracy gap, so there is no difficulty band where arm 1 fails and arm 2
succeeds.

**What survives.** Two contrasts, both verified:

* **Cost** — 1.2× to 13.3× the reasoning tokens for the *same answer*, on 11 of 11 items.
* **Tools** — arm 3 answers **14/14** where arms 1 and 2 manage 11/14, and the three it
  rescues are lookups. On `mb-08` the thinking arm spent **3,966 reasoning tokens failing
  to recall a fact that does not exist** while the tool arm spent 80 and looked it up.

That pair is the product in one frame, and it is a better demo row than the difficulty
contrast the plan expected.

## 3. Cue injection does not reproduce

**Measured:** 0 of 48 trials flipped, across metadata leak, authority, sycophancy and the
few-shot pattern — every cue type Appendix A.4 names — over two problem regimes.

**It is not a plumbing failure.** The model *verbalises* the cue: it names the hint,
discusses it, and answers what it was going to answer anyway. And the regime was varied to
kill the obvious confound, because a first pass over problems the model can solve measures
the problems as much as the cues — refusing a hint you can check is not evidence of
faithfulness either.

**A second observation, possibly the larger one.** Two of three `unverifiable` problems
returned **completely empty content** — zero characters, reasoning tokens billed. Asked
something it cannot look up, this model does not guess; it loops.

**Consequence.** M2-9 re-scoped from 3.5 h to ~1.0 h — **the first task in this project to
give hours back** — and the faithfulness panel keeps its slot with an inverted claim.

## 4. The behavior taxonomy barely populates

> ### ⚠️ Corrected 12 Sep — the zero was **one run**, and one run is not stable
>
> Over **twelve** full-corpus passes (3,579 rows): `linear` **82.3%**, `verification` 8.0%,
> `subgoal_setting` 7.5%, **`backtracking` 2.0%** (71 rows), `backward_chaining` 0.2%.
> Backtracking fires **1–15 times per run**, so a run returning 0 sits inside the spread.
> This entry read a corpus property off n=1 run of a non-deterministic classifier — the
> same mistake ADR-005 and ADR-006 each refused to make, committed here. See
> [ADR-010's amendment](decisions/ADR-010-the-taxonomy-barely-populates.md).
>
> **The skew finding — the part that matters for κ — is unchanged and slightly worse:
> 82.3%, not 81%.** And 2.0% measured against the 4.2% marker ceiling below is *consistent*,
> which is a stronger position than 0% against 4.2% was.

**Measured (single pass, superseded above):** `linear` 252, `verification` 35,
`subgoal_setting` 22, `backward_chaining` 1, **`backtracking` 0** — of 310 steps.

**The confound was checked before the conclusion was drawn.** A zero has two readings with
opposite consequences, and nothing in the classifier's own output separates them. So
`make taxonomy-coverage` measures the corpus with *no model at all*: 11 of 261 thought
steps (4.2%), in 2 traces of 42, open with a surface backtracking marker — and all eleven
reverse nothing, which `rubric.md` hard case 4.2 adjudicates as `linear` in advance.

So the classifier's zero is **plausible rather than proven wrong**, and the corpus's
opportunity for backtracking is close to nil. **Only a human reading those steps settles
it** — which makes M1-11's 40 labels the most valuable 1.5 hours in the month.

**Consequence for the headline number.** At 81% one class, κ under skewed marginals
routinely comes in low despite high agreement. **B4 #1's target of 0.60 was set without
knowing the marginal was this skewed**, and that is raised here at G1 rather than
discovered at G2. The target is carried unchanged; the baseline is published beside it.

---

## 5. The judge works — and the two errors it missed are the useful part

**The first B4 criterion this project has met on measurement rather than assumption.**
Ten hand-written mutations (Appendix B) applied to five traces that answered correctly
before anything was changed, run with the **correct-step rule**: a hit requires flagging
*the step that was broken*, not flagging the trace somewhere.

| | | |
| --- | --- | --- |
| **Judge recall** | **8 / 10 (80%)** | B4 #3 target ≥ 70% — **met** |
| **False flags on the same traces, unmutated** | **0 over 24 steps** | this is what makes the 80% mean anything |
| Collateral flags across the mutated runs | 4 | |

A judge that flags freely catches seeded errors by accident. This one flagged **nothing**
on known-good text, so the eight hits are eight detections rather than eight coincidences.
That control is why every trace is run twice.

**Re-measure:** `make seeded-errors`. Evidence: `docs/spikes/M2-6-raw/m2-6-seeded.json`,
[ADR-012](decisions/ADR-012-judge-thresholds.md).

### The miss worth quoting

The mutation changed `875 + 50 = 925` to `875 + 50 = 935`. The judge returned **`sound`,
confidence 0.95**:

> *"Recomputes 12500×0.074 by splitting into 0.07 and 0.004 yielding 875+50=935
> (correct)."*

**875 + 50 is 925.** It copied the wrong total out of the step, appended the word
*correct*, and was confident. It did not compute anything — and it then flagged **three
other steps** in the same trace, sensing something was wrong and blaming the wrong lines.

That is the failure the correct-step rule exists to expose: a recall number computed as
*"was the trace flagged anywhere"* would have scored this as a hit. It is also C4.4's own
premise reproduced in this repository — *arithmetic is precisely where cheap judges fail* —
and the numeric-step escalation rule would not have fired, because it triggers below 0.85.

The second miss has the same shape one layer up: a step that dropped the item's
**rounded down** constraint was graded `sound` against the rounding rule *the step itself
introduced*. The judge checks that each line follows from the line above; it does not check
the line against the problem.

### And a finding nobody asked for: the error types are close to noise

Of the eight caught, **two named the right `error_type`**. `arithmetic` was applied to four
of eight, including a unit conversion and a variable swap where nothing is miscomputed.

**Consequence: `error_type` must never render as a measured quantity.** It is fine in the
flagged-step panel as *the judge's description of the defect*. It is not fine anywhere that
implies the category is reliable — and B4 has no criterion for it, a gap ADR-012
recommends leaving open rather than inventing a target for at this n.

> n = 10. Recall of 80% carries a 95% Wilson interval of roughly **49–94%**: the point
> estimate clears the bar and the interval straddles it. M2-7 is where that becomes a
> committed figure with its interval beside it, per C5.5.

---

## 6. `validity_confidence` is not degenerate — and the sample that said it was, halved

**M2-4, settled on 3,579 rows instead of 17.**

A 17-row prep sample suggested **64.7%** of rows carried byte-identical `behavior` and
`validity` confidences — the model emitting one number twice rather than judging two
questions. Over twelve full-corpus runs the real figure is **32.1% (1,150 of 3,579)**.

**The small sample overstated it by a factor of two.** That is the whole entry: a number
that would have fired trigger t8 and forced a documented design change to C4.4's escalation
policy was, at n=17, wrong by 2x. It was labelled *"far too small to conclude from"* when it
was taken, and it is a good thing it was.

Trigger **t8 does not fire.** 32.1% agreement between two confidences the model produces in
one pass is unremarkable — the two questions are correlated, and a step that is clearly
`linear` is usually also clearly `sound`.

**Re-measure:** `make classify-reliability ARGS="--runs 12"`, then read
`confidence_pairs_identical` against `rows`.

---

## 7. Half the corpus is `unverifiable`, and that is the instrument working

Corpus-wide verdicts over the same 3,579 rows: **`unverifiable` 1,871 · `sound` 1,506 ·
`unsound` 202.** A judge calling 52% of everything unverifiable would normally be a broken
judge. It is not, and the distribution says why:

| Trace | `unverifiable` share |
| --- | --- |
| `mb-08.thinking` | **91%** of 1,551 rows |
| `mb-09.thinking` | 73% of 480 rows |
| `mb-09.direct` | 61% of 36 rows |
| The five known-good traces | **0%** — 100% `sound` across 288 rows |

The mass is concentrated in exactly the traces where the model asserts facts about **places
that do not exist**. `mb-08.thinking` is the trace that loops 126 times over an invented
town; calling those steps unverifiable is the correct answer, and a judge that called them
`sound` would be the defect.

> **This also strengthens §5's result rather than threatening it.** M2-6's judge recall was
> measured against a known-good baseline of 0 false flags over 24 steps in one run. Those
> same five traces are **100% `sound` across 288 rows over twelve runs**. The baseline is
> not a lucky draw.

---

## 8. The laptop-only configuration answers by labelling everything `linear`

[ADR-001](decisions/ADR-001-provider.md) promised that *"can this run entirely on a laptop
with no API access?"* would become **a published number rather than an assumption**. This
is the number, and it is negative.

`ANALYZER_BACKEND=local` run end to end through `rlens.classify` — the real code path, not
S3's direct probe — over six traces and 64 steps, against the same six traces from M1-9's
hybrid measurement:

| Same 6 traces / 64 steps | **local** `gpt-oss:20b` | **hybrid** `gpt-5-mini` |
| --- | --- | --- |
| `linear` | **100%** — 64 of 64 | 83.9% |
| The other four behaviour classes | **never once** | 16.1% |
| `unsound` verdicts | **0** | 9.6% |
| Identical behaviour/validity confidences | 77% | 45.9% |
| Steps below the 0.70 escalation floor | 30% | ≈ 0 (band is 0.75–0.95) |
| Repeat runs | **byte-identical ×3** | varies run to run |

**Both halves of C4.3's merged call are inert on the local tier.** It never uses the
taxonomy and it never says `unsound`, so κ would be undefined for four of five classes and
judge recall would be zero by construction.

### The two tiers fail in opposite directions, which is the useful part

Hybrid **uses the taxonomy but bunches its confidences**, so C4.4's 0.70 escalation floor
selects almost nothing. Local **spreads confidence across the full 0.05–0.95 range** — 30%
of steps below the floor — **but has nothing to be confident about**, having given every
step the same label. A wide confidence distribution over a collapsed taxonomy is not a
partial success; it is a model answering the easy half of a question it did not understand.

### On n — and the mirror image of §4's mistake

**64 steps, observed once.** Three repeats returned byte-identical output, which is what
`temperature: 0` and a pinned seed buy on this path. **The repeats prove determinism, not
sample size**, and reporting n=192 would be the same error §4 was just amended for, arriving
from the other side: that one read a corpus property off a single run of a *varying* system;
this one would inflate n from repeated runs of a *fixed* one.

The determinism is worth having on its own — the local tier is reproducible in a way the
hybrid tier is not, which would matter if it were ever good enough to use.

**Consequence:** if the key fails on demo day the fallback is the cached reports
(`DEMO_MODE=cached`), **not** a local re-analysis. The runbook already said so; it is now
measured rather than assumed. The `local` option stays in the code — it works, it is free,
and a different model or a tuned prompt might do better — but nobody should reach for it
expecting classification to survive.

**Re-measure:** `ANALYZER_BACKEND=local make classify-reliability ARGS="--runs 1 --limit 6"`.

---

## Findings about the instrument, not the model

Separate, because they are defects that were fixed rather than results to publish — but
each one would have surfaced later as a wrong number, so they belong in the same file.

| Found | Would have surfaced as |
| --- | --- |
| `exact` scoring numeric answers as strings — **37.5% of correct answers marked wrong** | "the model is worse than expected", in Month 3 |
| The answer extractor returning `\]` from a LaTeX block | an unreadable answer counted as wrong, rather than `unparsed` |
| A trace with reasoning and **no answer** reported `trace_quality: full` | `correct: false` asserting the model answered and was wrong |
| A cwd-relative corpus path failing **silently** inside a tool call | arm 3 answering wrong on a green run with a plausible chain |
| `max_tokens` accepted and silently ignored by the local runtime | M1-9 concluding its batch size must be 10 |
| **`step_id` not unique across the corpus** — 310 steps, 155 ids | a κ that made no sense, against 40 labels nobody could repair |
| `ANALYSIS_DEADLINE_S` never enforced — **a 969 s call against a 110 s budget** | a hung demo request in Month 3, with a deadline that looked set |
| Two CI jobs that would have gone green over nothing | G1 check 7 passing on a job that had never run |

**Three of these share one shape** — *we could not read it* being reported as *it was
wrong*. It appeared in the answer checker (M1-5), in `trace_quality` (M1-8), and again in
the report's arm status (M1-10). Each time the fix was the same: make the third outcome a
first-class state rather than collapsing it into the nearest available lie.

---

*Maintained through Month 1. M2-12's G2 report and M3's calibration page both read from
here; a finding that is in the product but not in this file is a finding somebody will have
to rediscover.*
