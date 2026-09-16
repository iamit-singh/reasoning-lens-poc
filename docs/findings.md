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
be present, and found all four absent or far smaller than expected. W5 added six more
entries — one positive, one correction of this project's own work, one that reads as a
defect and is not, one more phenomenon that turned out absent, and **the first measurement
against human labels, which splits the classifier in two** (§11, §12):

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

## 9. The enriched half of the calibration frame comes up **31 of 60**

**M2-14, and it fires trigger t13.**

C5.1's frame has two parts: a uniform **random-90** that carries the published κ, and an
**enriched-60** over-sampled from the rare classes so per-class F1 has instances to compute
over at all. The enriched half is drawn from the pool *remaining* after the random-90 —
179 of the corpus's 269 labellable steps — taking up to 15 per rare class from what the
**v0** classifier predicted.

| Rare class | Candidates in the remaining pool | Selected | Short |
| --- | --- | --- | --- |
| `verification` | 25 | **15** | — |
| `subgoal_setting` | 16 | **15** | — |
| `backtracking` | **1** | **1** | −14 |
| `backward_chaining` | **0** | **0** | −15 |
| **Total** | | **31 of 60** | **−29** |

Enrichment is **4.26×** on the non-linear classes as a group: they are 23.5% of the
remaining pool and 100% of the draw.

**Two consequences, and the second is the one that matters at G2.**

**`dev-100` cannot contain 100 rows.** C5.1 defines dev as the first 40 of the random-90
plus the enriched half, which is **40 + 31 = 71**. The file keeps its name and the G2
report must quote 71; a file named for a number it does not contain is exactly the kind of
flattering artifact this project has spent three months refusing.

**B4 #2's *"lowest per-class F1 ≥ 0.50"* is now at serious risk on two classes rather than
one.** `backward_chaining` has no instances in the enriched half at all, so its F1 will be
undefined; `backtracking` has one. This is not a statement about the classifier's quality —
it cannot be, at n = 0 and n = 1.

**The shortfall is partly the sampler, not only the corpus — and that is stated rather than
buried.** These predictions are **one pass** of a **non-deterministic** classifier. §4's
amendment measured `backtracking` at 0 on one pass and **2.0% over twelve**, firing between
1 and 15 times per run, with 45 of its 71 rows inside `mb-08.thinking`. So a single pass is
a weak instrument for *finding* rare-class candidates, and a multi-pass union would find
more.

**That option was deliberately not taken here.** The plan's pre-decided action for a class
that cannot reach its target is t13 — *label what exists, publish the actual n with a wide
interval, and never backfill from the random pool* — and changing how the enriched half is
selected is a change to the sampling frame, which is the reviewer's call rather than the
script's. It is recorded in `calibration/sampling.json` under `single_pass_caveat` so the
choice is visible instead of implicit.

**Backfilling is refused in code, not by memory.** `analyzer/tests/test_sampling.py` fails
if the two halves overlap, if any class takes more rows than it had candidates, if a
shortfall is dropped from the record, or if t13 reads *not fired* while a class is short.
All five refusals were negative-tested.

**Re-run:** `make draw-enriched ARGS="--force"` — reproducible from seed `20261014` at
bundle `97667881c779`.

---

## 10. The judge clears B4 #3 on every run. **Which cases it misses moves.**

**M2-6's last clause, and it audits M2-6's own headline.** Building the mutated reports
meant running the ten seeded cases twice more, at the same bundle, through a different code
path. Three runs now exist.

| | run 1 (M2-6) | run 2 | run 3 |
| --- | --- | --- | --- |
| **Recall** | 8 / 10 | 8 / 10 | **9 / 10** |

**B4 #3 is met on all three — 80%, 80%, 90% against a ≥ 70% bar.** The criterion is robust;
that is the first thing to say, and it is the thing that matters at G2.

**What is not robust is the per-case detail**, and it is confined to one place:

| Outcome across 3 runs | Cases | |
| --- | --- | --- |
| **Stable hit** | SE-02, SE-04, SE-06, SE-07, SE-08, SE-09, SE-10 | 7 |
| **Stable miss** | **SE-05** `dropped_constraint` | 1 |
| **Unstable** | **SE-01, SE-03** — *both* `arithmetic_slip` | 2 |

Eight of ten cases return the same answer every time. **All of the movement is in the two
`arithmetic_slip` cases**, which flip independently — SE-01 went miss→hit→hit, SE-03 went
hit→miss→hit — and that is what moved the aggregate from 8 to 9.

**Consequence for the published per-type table.** [ADR-012](decisions/ADR-012-judge-thresholds.md)
publishes hits per mutation type, and most cells have n = 1 or n = 2. The
`arithmetic_slip` cell has n = 2 and has genuinely read **0/2, 1/2 and 2/2** across three
honest runs of the same judge on the same text. **A per-type cell at this n is a coin-flip;
the aggregate is a measurement.** M2-6's DoD already required per-type cells as *hit/miss
with n stated, never bare percentages* — that is now measured rather than anticipated, and
should be read as a hard rule.

**SE-01 can no longer carry the weight ADR-012 put on it.** It is the case where the judge
copied a wrong total and appended *"correct"* — `"yielding 875+50=935 (correct)"` — then
flagged three other steps. As an illustration of *what* a cheap judge does wrong on
arithmetic it stands. As evidence of *how often*, it does not: the same judge caught it on
both later runs.

**SE-05 is the finding that survives.** Missed three times out of three, and it is the more
interesting failure anyway: a constraint the step itself introduced, dropped, and then
graded sound against the rule it had just stated. **The judge checks each line against the
line above, not against the problem.** That is a claim about the judge's shape rather than
its luck, and it is the one per-case result with enough stability to publish.

**This is the third time non-determinism has moved a conclusion here**, after §4's
`backtracking` zero (one run) and §6's confidence pairs (17 rows). Those moved *negative*
results. **This one lands on the single positive result the project has** — which is
exactly where the discipline is hardest to keep.

> It also caught a smaller version of the same error one paragraph deep in this file: the
> two-run version of this finding said the aggregate *"reproduced exactly"*. Run 3 returned
> 9. **Two points looked like a constant.**

**Re-run:** `make replay-reports` (costs spend) or `make replay-reports REPLAY_MOCK=1`
(offline, from the recorded cassettes), then compare
`calibration/seeded/reports/*.report.json` against `docs/spikes/M2-6-raw/m2-6-seeded.json`.

---

## 11. The classifier's two halves are not the same instrument

**The first measurement against human labels, and it splits cleanly down the middle.** 40
dev labels (M1-11), written blind against rubric v1, joined to the committed v0 reports at
bundle `97667881c779`.

| | κ | n | majority baseline | verdict against B4 #2 (κ ≥ 0.60) |
| --- | --- | --- | --- | --- |
| **Soundness** | **0.761** | 40 | 0.625 | **clears it** |
| **Behavior** | **0.126** `[-0.138, 0.421]` | 40 | 0.850 | fails, and fails badly |

**The soundness half works.** κ 0.761 on three classes, `sound` F1 0.897 and `unverifiable`
F1 0.894 — above B4 #2's bar and above even the 0.70 that B4 #1 asks of *two humans*. This
is the first criterion in the project to be met by the classifier rather than by the judge,
and it was not the half anybody was worried about.

**The behavior half agrees with a human less often than a constant would.** Raw agreement is
0.70; answering `linear` to every step scores 0.85. **The classifier is 15 percentage points
below the majority-class baseline** — it is not a weak signal, it is a signal that costs
accuracy to use.

> **κ 0.126 is below G2-C's threshold** (κ < 0.45 → *hypothesis falsified*, B2). It is
> **not** a G2 reading: G2 reads the held-out set at a frozen bundle, and this is the dev
> set against an **un-tuned v0** classifier — the number M2-3's iteration box exists to
> move. Recorded now because the starting point is what the iteration will be measured
> from, and a starting point recorded after the fact is an estimate.

**This is finding 4 arriving from the other side.** ADR-010 measured the taxonomy barely
populating — 81% one class. A baseline of 0.850 on this draw is that same fact, and it is
what makes behavior κ brutal: with 34 of 40 steps `linear`, every non-linear call the
classifier gets wrong costs more than a correct one gains.

**Re-run:** `make calibrate`.

---

## 12. The behavior disagreement is two rubric questions — and the annotator named both, blind

The confusion matrix is not diffuse. **All 12 behavior disagreements fall into two buckets**,
and both were flagged in the labelling notes *before any score existed*.

| Human → classifier | n | What it is |
| --- | --- | --- |
| `linear` → `verification` | 5 | **4 of them are `mb-08`'s repetition loop** |
| `linear` → `subgoal_setting` | 3 | first steps that restate the problem |
| non-linear → `linear` | 4 | one each of the real `backtracking`, `subgoal_setting`, and two `verification` |

### The classifier is cueing on the loop prefix

`mb-08` is the trace that says one thing 126 times. Four of the five false `verification`
calls are inside it, and they open `Let's check:`, `Let's search memory:`, `Let's think:` —
**the same sentence, a rotating prefix, nothing recomputed.**

The labelling note on that loop, written blind and before scoring:

> *"A third of this loop opens with `Let's check:`, a likely verification cue for the
> classifier, so disagreement may cluster on this trace."*

**It does. The prediction was exact.** `verification` precision is 0.286 — five of seven
`verification` calls are on steps a human read as linear, and four of those five are one
loop in one trace.

> **This is the 141-step trace earning its keep a second time.** It was the best artifact of
> Month 1 because it showed the model saying one thing 126 times. It is now also the best
> adversarial case in the corpus: a trace that produces a verification *marker* at high rate
> with no verification *behind it* is the exact input that separates a classifier reading
> the surface from one reading the move.

### Goal-restatement versus sub-goal, cutting both ways

The other bucket is first steps. `mb-12:0` and `mb-14:0` restate the problem and set up
variables; the classifier calls them `subgoal_setting`, the human called them `linear`.
`mb-06:0` is the mirror image — the human called it `subgoal_setting` and the classifier
said `linear`.

The note, again blind:

> *"v2 should give a test for 'restates the goal' vs 'names a sub-goal', because nearly
> every first step does one of the two."*

**Consequence — and it is the one M2-3's card already anticipated.** M2-3's failure clause
says to check *"whether the failure is concentrated in one class in the confusion matrix,
which is a rubric-precedence problem rather than a prompt problem and is fixed in the
rubric."* It is concentrated, in two classes, and both are open rubric questions rather than
prompt defects. **So the rubric work in M2-2 comes before the prompt work in M2-3**, which
is the order the plan already sequences them in — now with evidence rather than caution.

The full list is [`calibration/adjudication-queue.md`](../calibration/adjudication-queue.md):
14 questions the pass could not answer from the rubric, each with the reading actually
applied and the labels a reversal would invalidate.

### One more, and it is not a rubric question

**Cross-arm label distributions are confounded by segmentation granularity.** The `direct`
arm packs a full derivation and its conclusion into one step; `thinking` traces split
comparable content across many. Any scoreboard comparing per-step label *rates* across arms
is partly measuring the segmenter. This constrains what M2-10b may claim, and it cannot be
fixed here — the segmenter is frozen and moving it would detach all 90 labels from their
text.

**Re-run:** `make calibrate`, then read `confusion` in `calibration/results/latest.json`.

---

## 13. B4 #1 clears its bar — and the draw that measured it is mostly one repeated sentence

**behavior κ 0.867 · soundness κ 0.935 · n = 50 · amit vs ankit, rubric v1, no discussion.**
Both clear B4 #1's 0.70 target on the point estimate, so C5.3's revision round is not
triggered. Two people working from the same written rubric reproduced **98 of 100** label
decisions. The criterion that separates a measurement from one person asserting their own
labels are correct is met.

**And the behavior interval is [0.495, 1.000].** Its lower bound is below the bar it just
cleared, and that is not a quibble about bootstrap width — it is what κ does on a sample this
lopsided:

| | |
| --- | --- |
| `linear` | **46 of 50** (majority-class baseline **0.92**) |
| Steps from `mb-08` alone | **27 of 50** |
| …of those, the *same repeated sentence* | **15** |
| Non-`linear` steps carrying the whole behavior κ | **4** |

**The held-out half of the random-90 is a poor instrument for measuring rubric agreement**,
and that is the finding — not the 0.867. The draw is dominated by a degenerate repetition
loop on which any two readers agree trivially, so the number is largely *agreement about a
loop*. [`adjudication-queue.md`](../calibration/adjudication-queue.md) holds 14 open rubric
questions; this pass put an independent reader in front of two of them.

**This matters beyond B4 #1, because M2-17 computes the published classifier κ on these same
50 steps.** A held-out set that is 92% one class will give the classifier the same easy ride
it gave the annotators — and the dev κ already tells us what happens when `linear` dominates
(finding 11: behavior κ 0.126 against a 0.85 baseline). Whatever κ_heldout comes back, it must
be published with its n, its CI **and its composition**, or it will be read as far stronger
than it is.

### The queue called one of the two disagreements in advance, by step id

Of the two disagreements, `thinking:thinking-mb-03-root-llm-0:0` — expanding *RGB* where the
prompt itself supplies the acronym — is the step the adjudication queue had already named as
*"the sharpest case"* under question A2, *"the question most likely to be decided against
v1"*. That was written before anyone else had seen the corpus. **Ankit, cold, decided it
against v1.** The other (`direct:direct-mb-06-root-llm-0:1`, `verification` vs `backtracking`)
is queue question B2, also already logged, and ankit's note resolves it by explicitly invoking
the precedence rule — which means the rubric is ambiguous rather than that either reader was
careless.

A queue of self-identified rubric gaps that predicts, blind, which one an independent reader
will trip on is a queue worth working through. **It raises the prior on the other twelve**,
which this draw did not test.

**Re-run:** `make calibrate ARGS="--iaa"`, then read `inter_annotator` in
`calibration/results/latest.json`.

---

## 14. P1 has already failed, it cannot be repaired, and the live exposure is the adjudication

§8.1 P1: *"Inter-annotator κ was computed before any classifier scoring — commit order in
git: M2-2's κ predates the first classifier κ."* It does not. The first classifier κ was
committed at **`c7e070c`** (15 Sep) with `inter_annotator` null; the IAA κ follows it.

P1 is one of the two checks the breakdown says *"can only be reported"*. So it is reported
here, and it goes in the G2 report as a stated limitation.

**What it does not compromise.** The second annotator's pass is untouched by this: Ankit
labelled from the rubric with no access to any classifier output, and both his labels and
amit's were fixed on disk before the κ was computed. Knowing the dev κ cannot change a
function of two frozen label sets. Neither disagreeing step is in the dev 40, so **no
classifier number computed to date depends on either adjudication.**

**What is genuinely exposed, and it is still ahead of us.** Adjudication has not happened, and
the classifier's call on both disputed steps is sitting in committed reports:

| Step | amit | ankit | **classifier** |
| --- | --- | --- | --- |
| `direct:direct-mb-06-root-llm-0:1` | `verification` | `backtracking` | **`verification`** |
| `thinking:thinking-mb-03-root-llm-0:0` | `unverifiable` | `sound` | **`sound`** |

**The classifier agrees with amit on one and with ankit on the other, and both steps are in
the held-out 50 that carries the published κ.** So each adjudication moves the headline number
in a direction that is now *knowable in advance* — which is precisely the influence P1 exists
to make impossible. It cannot be made impossible any more. It can be made visible, so:

> **Neither adjudicator should look at `out/reports/` for these two steps before the session,
> and the adjudicated call should be written down with its reasoning before the classifier's
> prediction is consulted.** Stated here rather than trusted to memory, because the
> reasoning-shaped version of this failure — deciding on the merits and happening to land on
> the number that helps — is indistinguishable from the honest version afterwards.

---

## 15. Improving the classifier lowered κ — three times, and the third time it hit zero

**Measured (M2-3, dev-40, single passes):**

| bundle | κ behavior | raw agreement | errors / 40 | `linear` predicted |
| --- | --- | --- | --- | --- |
| baseline `97667881c779` | **0.126** | 0.700 | 12 | 30 |
| cycle 1 `14776ac9d56d` | 0.083 | 0.750 | 10 | 34 |
| cycle 2 `e8952d4d3c51` | 0.104 | 0.775 | 9 | 35 |
| cycle 3 `9107b409e1ae` | **−0.026** | **0.825** | **7** | **39** |

**Agreement rose monotonically. Errors fell monotonically. κ did neither.** The best κ in
the table belongs to the *untuned* prompt, and the best raw agreement belongs to the bundle
whose κ is below zero.

**Why, exactly.** κ = (p_o − p_e) / (1 − p_e), and p_e is computed from the *marginals* —
how often each label is used, by each side. The dev set is 34 `linear` in 40. A classifier
that predicts `linear` 30 times has a lower p_e than one that predicts it 34 times, so the
baseline's κ was partly earned **by being wrong in a differently-shaped way**: over-calling
`verification` 7 times against a true 4 depressed chance agreement and flattered the
coefficient. Fixing that over-call moved p_e from 0.657 to 0.728 and took κ down with it,
while the classifier was getting two more steps right.

| | p_o | p_e | κ |
| --- | --- | --- | --- |
| baseline | 0.700 | 0.6569 | 0.1257 |
| cycle 1 | 0.750 | 0.7275 | 0.0826 |

### The same classifier, scored twice, 0.218 apart — with identical accuracy

Three independent passes at the **same bundle** `e8952d4d3c51` (nothing changed between
them but the classifier's non-determinism):

| pass | n | correct | raw agreement | `linear` predicted | p_e | κ |
| --- | --- | --- | --- | --- | --- | --- |
| original | 40 | 28 | 0.775 | 35 | 0.7519 | **+0.104** |
| A | 32 | 26 | 0.8125 | 31 | 0.8184 | **−0.032** |
| B | 32 | 26 | 0.8125 | 29 | 0.7695 | **+0.187** |
| C | 32 | 25 | 0.781 | 30 | 0.7930 | **−0.052** |

**Range 0.238. SD 0.132 over the three n = 32 passes.** Passes A and B are the sharpest
statement of it: **same n, same 26 of 32 correct, κ 0.218 apart**, entirely because B spread
its six errors across three classes while A put them all in `linear`. Pass B did not get one extra step
correct — it spent two of its six errors on `backtracking` and `verification` instead of
answering `linear`, which lowered p_e from 0.818 to 0.770, and κ did the rest.

That is the whole of finding 15 in two rows, and it is a stronger statement than the cycle
table above, because between those cycles the *prompt* changed and here **nothing did**.

**The consequence for M2-3, stated plainly: κ_dev on this sample cannot adjudicate between
prompt bundles.** The run-to-run spread is 0.238 and the per-run SD is 0.132; the largest
difference between any two cycles was 0.130 — **the noise is 1.8× the largest signal the
tuning produced**, and every cycle delta sits inside one standard deviation of doing
nothing. Every cycle delta in this exercise is inside the noise, and M2-3's stop
rule — *three consecutive cycles improving κ by < 0.02* — is asking a question this
instrument cannot answer at n = 32–40. The cycles were still worth running: what justifies
the shipped bundle is **mechanical**, not statistical (the prompt now carries the rubric's
own §4 adjudications, which the annotator had and the classifier did not), and the
diagnostics that moved — `verification` false positives 5 → 0, class coverage — are
step-level facts rather than a coefficient.

**What it means, and it cuts both ways.** This is the prevalence problem — κ is not a
scaled accuracy and must not be read as one on a skewed sample. But the third cycle is the
other half of the argument: it produced a **majority-class predictor**, `linear` 39 times in
40, missing all four real `verification` steps, with the *highest* raw agreement in the
table. κ went below zero and said so. **Raw agreement could not tell cycle 3 from cycle 2;
κ could.** Neither metric is sufficient alone on this corpus, and any published number that
quotes one without the other is quoting the flattering half.

**The consequence for B4 #2, which is not a defence of the classifier.** At p_e ≈ 0.73, κ ≥
0.60 needs **35.6 of 40 correct — at most 4 errors**. The 0.60 bar was set in the plan
without reference to this corpus's class balance, and on an 85%-majority sample it is a
demand for near-perfect agreement. **The bar is not being moved.** It is being reported
against, with the arithmetic that shows what it actually asks for, which is what C7.2's
recorded-justification branch is for.

**What guards it:** `prompts/CHANGELOG.md` carries every cycle with both metrics side by
side, and the baseline row is the untuned prompt, so the comparison cannot be quietly
re-based. `versions._NOT_PROMPTS` keeps that changelog out of the bundle hash, with the
converse asserted — a real prompt edit does move the version.


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
| **C5.4's held-out guard keyed on a *filename*** — the labelling tool writes `<annotator>.jsonl`, so 50 held-out labels sat in a file the default `make calibrate` counted as dev | the published κ tuned against the held-out set, with every guard reporting green |
| **`make calibrate` could not compute B4 #1 at all** — the IAA κ lives on the held-out 50, which the C5.4 exclusion correctly drops, so the command `annotator-2.md` told you to run reported *NOT COMPUTABLE* with both passes on disk | M2-2 blocked, or "unblocked" by running `--final` — scoring the held-out set against the classifier, before the freeze, to obtain a human-vs-human number |
| **The calibration join silently shrank its own denominator** — a degraded classifier call leaves the step in the report with a null label, so `_paired` dropped it and κ was computed over 32 of 40 labels while the same output's header read *"40 labels"* | **the published held-out κ computed over 42 of 50 steps, reporting 42 as though it were the set** — on a read that happens once |
| **The brief in `annotator-2.md` named the wrong labelling command** — `make label ARGS="--annotator <name>"` defaults to `--part dev` | the second annotator labelling the dev 40 instead of the held-out 50, and B4 #1 measured on the wrong half of the frame |

**The held-out one is the worst of these and deserves its sentence.** `make calibrate`'s
default is the *safe* invocation — it is what M2-3's iteration loop runs, every cycle. It
excluded `heldout-50.jsonl` by name, and nothing else. A labelling pass that ran from
position 1 to position 90 in one sitting put both halves in `amit.jsonl`, and every
subsequent dev number would have silently included the 50 steps the published claim depends
on never having been tuned against. **The same hole was waiting for W6 regardless of how the
labelling went**: `annotator-2.md` tells the second annotator his file is
`labels/<annotator>.jsonl`, and he labels *nothing but* the held-out 50 — so `ankit.jsonl`
would have leaked the entire set on its own. The guard is now keyed on the **draw**
(`sampling.json`'s random-90, split at 40), which is where the held-out set is actually
defined; the filename rule is kept as a redundant second check. Both regression tests were
watched to fail before being trusted to pass.

**And the one this session found has the opposite shape — a guard that was entirely correct
and still cost a measurement.** The draw-keyed held-out exclusion did exactly its job: it
dropped every held-out step from the default run. B4 #1 is computed on the held-out 50,
because that is the only half both annotators labelled. So `make calibrate` — the command
`annotator-2.md` printed under the heading *"IAA on the 50 double-labelled steps"* — reported
*NOT COMPUTABLE, one annotator* with 100 labels from two people sitting in the file. **The
dangerous repair was one flag away**: `--final` does read the held-out set, and someone under
time pressure, wanting a human-vs-human number, could have reached for the invocation that
scores the classifier against the published set before the freeze. The fix instead widens
*only* the set human-vs-human reads (`--iaa`), keeps the classifier join on dev, and refuses
`--iaa --final` together so that C5.4's "opened once" stays a count somebody can audit.

**Three of these share one shape** — *we could not read it* being reported as *it was
wrong*. It appeared in the answer checker (M1-5), in `trace_quality` (M1-8), and again in
the report's arm status (M1-10). Each time the fix was the same: make the third outcome a
first-class state rather than collapsing it into the nearest available lie.

---

*Maintained through Month 1. M2-12's G2 report and M3's calibration page both read from
here; a finding that is in the product but not in this file is a finding somebody will have
to rediscover.*
