# Calibration — the scientific core

B0 Condition #5: this page ships publicly **with whatever numbers we get**. That only means
something if the procedure is fixed *before* the numbers are seen.

| Path | What | Owner |
| --- | --- | --- |
| `rubric.md` | 5 definitions verbatim from the classifier prompt, the precedence rule, 5 worked examples, 5 adjudicated hard cases, soundness definitions | M1-11 (W4) |
| `sampling.json` | Both halves of C5.1's frame: the **random-90** (seed + ordered id list, committed *before the first label*) and the **enriched-31** drawn from the v0 predictions, each with its seed, bundle version, per-class counts and enrichment factor | M1-11 (W4) · M2-14 (W5) |
| `labels/dev-100.jsonl` | Dev steps — what prompt iteration tunes against. **C5.1 intends 100 (random 1–40 + enriched 60); the corpus yields 71**, because two rare classes could not reach their enrichment target — see [finding 9](../docs/findings.md) and `sampling.json.enriched`. **At 40 of 71**: M1-11's random 1–40 are labelled, the enriched 31 are not | M1-11 ✅ → M2-14 ✅ → M2-1b |
| `labels/heldout-50.jsonl` | 50 double-labeled steps carrying the **published headline κ**. Opened **once**, after the prompt bundle is frozen. **Amit's 50 are labelled (M2-1a ✅)**; the second annotator's pass and the freeze are still to come | M2-1a ✅ → M2-2 |
| `adjudication-queue.md` | The 14 rubric questions the v1 pass could not answer, each with the reading actually applied and the labels a reversal would invalidate. **The agenda for M2-2's adjudication** — and it must never be sent to the second annotator | M1-11 / M2-1a ✅ → M2-2 |
| `annotator-2.md` | who the second annotator is, when they labeled, and confirmation they were **not** briefed. **Written and blank**, with the verbatim brief to send so the annotator cannot be accidentally coached — coaching is the one thing that invalidates B4 #1 | M2-2 |
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

**And a third, learned the hard way: the held-out exclusion is keyed on the draw, never on a
filename.** `make calibrate`'s default — the invocation M2-3's loop runs every cycle — used
to exclude `heldout-50.jsonl` *by name* and nothing else. The labelling tool writes
`<annotator>.jsonl`, so a pass that ran from position 1 to position 90 in one sitting put
both halves in one file and the dev number silently included all 50 held-out steps. The
same hole was waiting for the second annotator regardless: `annotator-2.md` sends him to
`labels/<annotator>.jsonl` and he labels *nothing but* the held-out 50. `rlens.calibrate`
now reads `sampling.json`'s random-90 and treats everything past position 40 as held out
wherever it lives; the filename rule is kept as a redundant second check. The tool also
refuses to walk across the boundary on its own — `--part` is `dev`, `heldout` or `enriched`,
and the default is `dev`.

## Provenance of the 90 labels — read this before reading the timestamps

**`labeled_at` records when a row was *written*, not how long the step took to judge**, and
on this pass those two differ. Anyone auditing the files will notice the pattern, so it is
written down here rather than left to be rediscovered as an alarm:

| Rows | `labeled_at` pattern | What it means |
| --- | --- | --- |
| 1–30 | individual stamps, 0.5–1.5 min apart | typed into the tool one step at a time |
| 31–90 | **six batches of ten**, each batch sharing one stamp to the second | judged first, entered in batches of ten |

**The annotator read and judged every one of the 90 steps.** The later labels were worked out
against the rubric and then entered in `--count 10` runs, which the tool writes in well under
a second — hence ten identical stamps. Confirmed by the annotator on 15 Sep 2026.

**The corroborating evidence is in the labels themselves**, and it is stronger than the
timestamps: 82 of 90 carry notes that cite rubric sections by number, cross-reference earlier
queue positions by index, and hold a consistent reading across the whole pass. One of them —
written blind, in the batched portion, before any score existed — **predicted where the
classifier would disagree and was exactly right** ([finding 12](../docs/findings.md)). That is
not a property batched entry could manufacture.

**The rate, from the only clean sample.** The 30 individually-stamped rows give **1.10 min/step
median, 1.66 mean**, against the plan's assumed **1.6**. So C10.3's labelling line is sound and
**M2-1a's overrun trigger does not fire** — which is worth stating plainly, because the naïve
wall-clock reading (3.1 h across the file) would have fired it on an artefact of batching.

> **What this does *not* license.** The second annotator's pass (M2-2) is the one that carries
> B4 #1, and **it must be typed, one step at a time, in the annotator's own sitting** — the
> point there is an independent reading under observation-free conditions, and batched entry
> would remove the only timing evidence that the pass happened as described.

## The second annotator — confirmed, and why it was nearly lost

**Ankit** is committed for **~2 hours in W6** to independently label the 50 held-out steps.
Amit is the sole contributor to this PoC, so this was the one role he could not fill himself,
and for a day it was the most fragile thing on the board.

| Field | Value |
| --- | --- |
| Second annotator | **Ankit** |
| Commitment | ~2 h, W6 |
| Labels | the 50 held-out steps, independently, rubric-only |
| Briefed? | **must be NO** — record this in `annotator-2.md` |

**Why no substitute works.** The headline claim is *two people, given only a written rulebook
and no discussion, agreed this often*. It is what separates a measurement from one person
asserting their own labels are correct. With one labeler it is not computable — not harder,
not noisier: not computable.

The considered alternative — the same person labeling twice, weeks apart, blind — measures
something real, but only whether the rulebook is precise enough to give **one person** the
same answer twice. It cannot detect a rulebook that is clear to its author and ambiguous to
everyone else, which is the exact failure the number exists to catch.

> **⚠️ If Ankit becomes unavailable, the fallback is self-consistency labeling — and the
> published claim must be renamed.** Never publish a self-consistency number under the word
> *agreement*.

**Hand Ankit the rulebook cold.** No walkthrough, no worked examples beyond what is written
down, no discussion of hard cases beforehand. A briefed second annotator measures the
briefing, not the rubric. Record in `annotator-2.md` that he was not briefed.

**This shapes M1-11, three weeks earlier.** The rubric must stand entirely on its own, because
in W6 someone who has never seen this project reads it and nothing else. Write it for Ankit,
not for yourself — that is the difference between a rubric and a set of personal notes.
