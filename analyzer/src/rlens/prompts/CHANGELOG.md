# Prompt bundle changelog — M2-3

One entry per iteration cycle. **One change per cycle**, κ before → after, the bundle
version, and what the change was trying to fix. A cycle that changes three things and
gains 0.03 teaches nothing and cannot be reverted intelligently (M2-3's card).

**Dev set only.** Every number here is measured on `calibration/labels/dev-100.jsonl`
(40 rows — see the note on the dev set below). The held-out 50 are read once, by M2-17,
after the freeze. The CLI refusal is demonstrated at the bottom of this file.

**Stop at whichever comes first** (C6): κ_dev ≥ 0.70 · three consecutive cycles improving
κ by < 0.02 · the 2.5-hour box.

> **This file is not hashed into `PROMPT_BUNDLE_VERSION`.** It lives in `prompts/` because
> M2-3's DoD puts it there, and `versions._NOT_PROMPTS` excludes it by name, because the
> record of what a prompt change did must not itself count as a prompt change. Verified by
> `test_changelog_is_not_hashed_into_the_bundle_version`, with the converse — a real prompt
> edit *does* move the version — asserted next to it. Excluding it did not move the bundle
> version: it was `97667881c779` before the exclusion and after it.

---

## The dev set this is tuned against — read this before reading any κ below

**It is 40 rows, not 100**, and the file keeps its name. Amendment 002 dropped M2-1b (the
enriched 31), so the dev set is the random-90's first 40 and nothing else.

**22 of those 40 rows come from two traces** — `mb-08:thinking` (14) and `mb-09:thinking`
(8), both of which are the degenerate repetition loop ADR-010 and finding 13 describe.
The label distribution is 34 `linear`, 4 `verification`, 1 `backtracking`,
1 `subgoal_setting`, 0 `backward_chaining`.

Two consequences, stated here because they bound every number below:

1. **The majority-class baseline is 0.850.** κ is measured against always answering
   `linear`, so a classifier can agree with a human 70% of the time and score κ 0.126.
2. **Three of five classes have n ≤ 1 and one has n = 0.** Per-class F1 on those cells is
   not a statement about the classifier and is not treated as one here.

Tuning against this set can improve the `linear` / `verification` boundary, which is where
22 of the 40 rows live. It cannot say anything about `backward_chaining`, and this file
never claims otherwise.

---

## Baseline — bundle `97667881c779`

The prompt as frozen at M1-9, unmodified. This is the number every cycle below is
measured against.

| | dev κ | 95% CI | raw agreement | baseline |
| --- | --- | --- | --- | --- |
| **behavior** | **0.126** | [−0.138, 0.421] | 0.700 | 0.850 |
| **soundness** | **0.761** | [0.552, 0.948] | 0.875 | 0.625 |

Per-class F1 (behavior): `linear` 0.812 (n=34) · `verification` 0.364 (n=4) ·
`backtracking` 0.000 (n=1) · `subgoal_setting` 0.000 (n=1) · `backward_chaining` n/a (n=0).

**Soundness is not the problem and is not being tuned.** κ 0.761 already clears B4 #2's
0.60 bar and the 0.70 asked of two *humans*. Every cycle below targets behavior, and each
one reports soundness as a **regression check** — a behavior gain bought by a soundness
loss is not a gain.

### Where the 12 behavior errors actually are

The confusion matrix has one dominant cell and it is not subtle:

| human ↓ / classifier → | linear | verification | subgoal | backtrack |
| --- | --- | --- | --- | --- |
| **linear** (34) | 26 | **5** | **3** | 0 |
| **verification** (4) | **2** | 2 | 0 | 0 |
| **subgoal_setting** (1) | **1** | 0 | 0 | 0 |
| **backtracking** (1) | **1** | 0 | 0 | 0 |

**8 of 12 errors are false positives on `linear` steps** — the classifier calling a move
that is not there. Read step by step they fall into exactly two buckets, which is what
M2-1a's blind note predicted before the κ existed:

- **Bucket A — surface-marker cueing (5 errors).** Every one is a step in mb-08/mb-09's
  repetition loop opening with *"Let's check:"*, *"Let's search memory:"*, *"Let's
  think:"*. The step announces a check and then checks nothing — it repeats the same
  uncertain assertion verbatim. **The classifier's own `rationale` says so**: *"no added
  information"*, *"offers no verification"*, *"repeats the same uncertain assertion"* —
  and it labels the step `verification` anyway. The label is being decided by the opening
  phrase while the rationale reads the content.
- **Bucket B — opening steps that set up and then execute (3 errors).** *"Let pen cost p,
  notebook cost n. n = p + 2.00"* labelled `subgoal_setting`. Naming variables and
  restating the given problem is not naming an *intermediate objective*.

The remaining 4 are misses (human non-linear → classifier `linear`), and two of those are
genuinely contested readings rather than defects. They are addressed in cycle 2, after the
cell carrying 8 errors.

---

## Cycle 1 — carry the rubric's cue rule into the prompt · bundle `14776ac9d56d`

**Hypothesis.** The prompt was never given §4 of `rubric.md`. The annotator had five
adjudicated hard cases; the classifier had the taxonomy and nothing else. §4.3 decides
Bucket A outright — *"a step that repeats an earlier conclusion without checking it is
`linear`. It is not `verification`, because nothing is re-derived"* — and it names this
corpus explicitly: *"one trace repeats a single sentence 126 times. Every one of those
steps is `linear`."*

**The change is therefore a drift *reduction*, not an addition.** The TAXONOMY block is
byte-identical and untouched — `make rubric-drift` passes at 19 identical lines. What was
added sits outside the markers and says in the prompt what the rubric already says to the
human: label the move, not the vocabulary; a cue phrase makes a step `verification` only
if the step then re-derives; and — the sentence aimed at the observed failure — *if the
rationale you are about to write says nothing was checked, the label is not
`verification`.*

| | κ before | κ after | Δ |
| --- | --- | --- | --- |
| **behavior** | 0.126 | **0.083** | **−0.043** |
| soundness (regression check) | 0.761 | 0.761 | 0.000 |

**κ went down. Almost everything else went up.**

| | baseline | cycle 1 |
| --- | --- | --- |
| errors / 40 | 12 | **10** |
| raw agreement | 0.700 | **0.750** |
| `verification` predicted (support 4) | 7 | **1** |
| `verification` F1 | 0.364 | **0.400** |
| `linear` F1 | 0.812 | **0.853** |

Bucket A is gone: all five *"Let's check:"* false positives were fixed, and not one of them
came back. The reason κ fell anyway is in the next section, and it is the most important
thing this file records.

**One regression, and it is instructive.** The change also named *"wait"* and *"actually"*
as backtracking cues while telling the model they were not sufficient. `backtracking`
predictions went 0 → 2 and `backward_chaining` 0 → 1 — on classes with support 1 and 0.
**Naming a cue suppresses over-prediction where over-prediction already exists, and
manufactures it where it does not.** Cycle 2 removes those two words.

---

## Why κ fell while the classifier improved — the finding this task produced

κ = (p_o − p_e) / (1 − p_e). Cycle 1 moved *both* terms, and the denominator moved more.

| | p_o (agreement) | p_e (chance) | κ |
| --- | --- | --- | --- |
| baseline | 0.700 | 0.6569 | 0.1257 |
| cycle 1 | **0.750** | **0.7275** | 0.0826 |

The baseline classifier predicted `linear` 30 times against a human 34. Cycle 1 predicts it
34 times against a human 34. **Matching the human's marginal distribution is what raised
p_e**, and on a set that is 85% one class, p_e rises faster than p_o can follow. The
baseline's κ was partly *earned by being wrong in a differently-shaped way*: predicting 7
`verification`s where there were 4 lowered chance agreement and flattered κ.

**The consequence for B4 #2, stated now rather than at the gate.** At p_e = 0.7275, κ ≥
0.60 requires **35.6 of 40 steps correct — at most 4 errors**. B4 #2's bar was written
without reference to this corpus's class balance, and on a 0.85-majority set it is a
demand for near-perfect agreement, not for a moderately good classifier. This is finding
material for the G2 report, and it is a fact about the *metric on this sample*, not a
defence of the classifier.

---

## Cycle 2 — drop the backtracking cue words, state the residual rule · bundle `e8952d4d3c51`

**Hypothesis.** Cycle 1's own regression says naming a cue makes the class salient. Replace
the two cue words with the rubric's §2 line the prompt also never received — *"`linear` is
the residual, not a judgement of quality. Most steps are `linear`"* — which suppresses
invented non-linear calls without naming any cue at all.

| | κ before | κ after | Δ |
| --- | --- | --- | --- |
| **behavior** | 0.083 | **0.104** | **+0.021** |
| soundness (regression check) | 0.761 | 0.761 | 0.000 |

Errors 10 → **9**. Raw agreement 0.750 → **0.775**. `backward_chaining` false positive
**gone** (1 → 0 predicted), `backtracking` 2 → 1. `linear` F1 0.853 → **0.870**. The
cycle-1 regression is repaired and the cycle-1 gain is kept.

---

## Cycle 3 — the `subgoal_setting` execution rule · bundle `9107b409e1ae` · **REVERTED**

**Hypothesis.** Bucket B is the last multi-error cell: `subgoal_setting` predicted 3
against support 1, F1 0.000. `rubric.md` §3.3 says the deciding feature is that the step
*"states an intention and does not yet execute it"*, and §4.1 supplies a rewrite test.
Neither was in the prompt.

| | κ before | κ after | Δ |
| --- | --- | --- | --- |
| **behavior** | 0.104 | **−0.026** | **−0.130** |

**It collapsed the classifier.** `linear` predicted **39 of 40**. Every other class went to
0 or 1. `verification` F1 0.400 → **0.000** — the four real verifications are all missed
now. Raw agreement reached its **highest value of the whole exercise, 0.825**, and κ went
**below zero**: worse than chance, on a classifier that agrees with the human more often
than any previous bundle.

**This is the majority-class predictor**, arrived at by three cycles of guidance each of
which was individually justified by the rubric. It is exactly the degenerate outcome κ
exists to detect, and κ detected it — the one moment in this exercise where κ was the
right instrument and raw agreement was the misleading one.

**Reverted.** A classifier that answers `linear` 39 times in 40 makes `pattern_profile`
constant, makes the trace renderer show one colour, and would turn the demo into a
demonstration that the taxonomy is unnecessary.

---

## The variance measurement — and why it ends this exercise

ADR-010 is this project's cautionary tale: it published *"backtracking 0 in the whole
corpus"* off **a single run of a non-deterministic classifier**, and twelve runs later the
real figure was 2.0%, firing 1–15 times per run. Every κ above is a single run. So before
choosing a bundle, the same bundle was run three more times with **nothing changed**.

**Bundle `e8952d4d3c51` (cycle 2), four independent passes:**

| pass | n | raw agreement | κ |
| --- | --- | --- | --- |
| original | 40 | 0.775 | **+0.104** |
| A | 32 | 0.8125 | **−0.032** |
| B | 32 | 0.8125 | **+0.186** |
| C | 32 | 0.781 | **−0.052** |

**Range 0.238. Standard deviation 0.132 over the three n = 32 passes.**

The largest difference between *any two cycles in this entire exercise* is **0.130** —
cycle 2 to cycle 3, the one that collapsed the classifier to a majority-class predictor.
**The run-to-run noise is 1.8× the largest signal the tuning produced.**

Passes A and B are the sharpest statement of it: **same n, same 26 of 32 correct, κ 0.218
apart**, entirely because B spread its six errors across three classes while A put them all
in `linear`.

### What this does to the stop rule

M2-3 stops at whichever comes first: **κ_dev ≥ 0.70** · **three consecutive cycles
improving κ by < 0.02** · **the 2.5-hour box**.

- κ_dev ≥ 0.70 was never approached.
- *Three consecutive cycles improving κ by < 0.02* reads Δs of −0.043, +0.021, −0.130
  against a per-run SD of 0.132. **Every one of those deltas is inside one standard
  deviation of doing nothing.** The rule cannot fire meaningfully at this n; it would be
  reading noise.
- **The box expired.** That is the stop rule that fired, and it is named here as M2-3's DoD
  requires.

M2-3's on-failure branch for *"the box expires below κ_dev 0.60"* offers three options in
order. **(a)** — check whether the failure is concentrated in one class — was done first
and drove cycles 1 and 2; it was concentrated, in `verification`, exactly as M2-1a's blind
note predicted. **(b)** — lower the CI dev gate with a recorded justification — is
**declined**: a gate whose metric has a 0.238 run-to-run range does not become useful by
being moved, and lowering it would encode the noise as an expectation. **(c)** — carry the
shortfall into the G2 report — is taken.

### The bundle that ships, and the honest reason

**`e8952d4d3c51` (cycle 2).** Not because its κ is best — the untuned baseline's 0.126 is
nominally higher, and the variance says neither number means anything on its own.

It ships because **the justification is mechanical rather than statistical**: the prompt now
contains the rubric's own §4 adjudications — *"label the move, not the vocabulary"*,
*"a step that repeats an earlier conclusion without checking it is `linear`"*, *"`linear` is
the residual"* — which the **annotator had and the classifier did not**. That is a drift
*reduction* between the two things κ compares, and it is defensible without reference to any
κ at all. The TAXONOMY block is byte-identical throughout; `make rubric-drift` passes at 19
identical lines in every cycle.

The step-level facts that moved are also stable in a way the coefficient is not: the five
*"Let's check:"* false positives on the repetition loop were fixed in cycle 1 and **did not
return in any of the six subsequent runs**.

**What is published for B4 #2 is the range, not a point.** A single κ_dev from this sample
would be a number picked out of a distribution 0.238 wide, and quoting it as *the*
classifier's agreement would be the flattering artifact this project keeps refusing.

### The demonstrated held-out refusal — M2-3's DoD, pasted verbatim

```
$ make calibrate ARGS="--final"
--final refused: calibration/labels/HELDOUT_FREEZE is absent, so the prompt bundle is not
frozen (C5.4). Scoring the held-out set against an unfrozen bundle means the number can be
re-rolled until it is liked, which is the one thing the held-out set exists to prevent.
Freeze first (M2-16).
```

The held-out 50 were not read at any point in this exercise. Every number above is dev-40.

### One thing found by accident, and it changes what M2-17 must do first

Three of the four passes scored **n = 32, not 40**. `mb-09:thinking` fails intermittently
with `classifier_parse_failure` — 26 rows returned for 25 steps, surviving the repair retry
— which nulls **every** label in the arm while the arm's `status` stays `"ok"`. That arm
carries **8 of the 40 dev labels and 10 of the 50 held-out steps**.

`make calibrate` used to score whatever joined and report the smaller n as though it were
the set. It now refuses on `--final` and warns on dev, and `make coverage-check` asks the
question in advance. **M2-17 must run `make coverage-check --final` and see READY before
spending its one read.**
