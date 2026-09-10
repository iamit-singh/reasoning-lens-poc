# Calibration — the scientific core

B0 Condition #5: this page ships publicly **with whatever numbers we get**. That only means
something if the procedure is fixed *before* the numbers are seen.

| Path | What | Owner |
| --- | --- | --- |
| `rubric.md` | 5 definitions verbatim from the classifier prompt, the precedence rule, 5 worked examples, 5 adjudicated hard cases, soundness definitions | M1-11 (W4) |
| `sampling.json` | The seed **and the ordered id list**, committed *before the first label is written* | M1-11 (W4) |
| `labels/dev-100.jsonl` | 100 dev steps — what prompt iteration tunes against | M1-11 → M2-1 |
| `labels/heldout-50.jsonl` | 50 double-labeled steps carrying the **published headline κ**. Opened **once**, after the prompt bundle is frozen | M2-1 |
| `annotator-2.md` | who the second annotator is, when they labeled, and confirmation they were **not** briefed | M2-1 |
| `labels/HELDOUT_FREEZE` | The freeze commit sha. Absent until M2-1; once present, `scripts/check_heldout_freeze.sh` fails any PR that edits the held-out labels | M2-1 |
| `seeded/` | Mutation definitions + expected flaw step ids | M2-6 |
| `results/latest.json` | The published metrics, served by the calibration page | M2-8 |

## Two rules that cost rework if broken

**The segmenter must be frozen before a single step is labeled.** `step_id` is
`"{strategy}:{span_id}:{ordinal}"` and the ordinal comes from the segmenter — any change
after labeling begins renumbers steps and **silently detaches every label from its text**.
The segmenter is tagged `segmenter-frozen-v1` at the end of W3. Changes to the merge
threshold (15 tokens) and the split cap (200 tokens) are the highest-risk edits: both change
ordinals *globally*. If S3 shows that 25-step batches truncate, that edit lands **before**
the freeze.

**The first 40 labels come from the random-90 part, in seeded order.** κ is reported on the
uniform random draw only. The enriched-60 draw needs the classifier's predictions and so
cannot happen until Month 2 — and drawing early labels from it would bias the very κ the
two-part frame exists to protect (C5.1).

## The second annotator — confirmed, and why it was nearly lost

A colleague is committed for **~2 hours in W6** to independently label the 50 held-out steps.
Amit is the sole contributor to this PoC, so this was the one role he could not fill himself,
and for a day it was the most fragile thing on the board.

**Why no substitute works.** The headline claim is *two people, given only a written rulebook
and no discussion, agreed this often*. It is what separates a measurement from one person
asserting their own labels are correct. With one labeler it is not computable — not harder,
not noisier: not computable.

The considered alternative — the same person labeling twice, weeks apart, blind — measures
something real, but only whether the rulebook is precise enough to give **one person** the
same answer twice. It cannot detect a rulebook that is clear to its author and ambiguous to
everyone else, which is the exact failure the number exists to catch.

> **⚠️ If the colleague falls through, the fallback is self-consistency labeling — and the
> published claim must be renamed.** Never publish a self-consistency number under the word
> *agreement*.

**Hand them the rulebook cold.** No walkthrough, no worked examples beyond what is written
down, no discussion of hard cases beforehand. A briefed second annotator measures the
briefing, not the rubric. Record in `annotator-2.md` that they were not briefed.
