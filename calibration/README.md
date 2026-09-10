# Calibration — the scientific core

B0 Condition #5: this page ships publicly **with whatever numbers we get**. That only means
something if the procedure is fixed *before* the numbers are seen.

| Path | What | Owner |
| --- | --- | --- |
| `rubric.md` | 5 definitions verbatim from the classifier prompt, the precedence rule, 5 worked examples, 5 adjudicated hard cases, soundness definitions | M1-11 (W4) |
| `sampling.json` | The seed **and the ordered id list**, committed *before the first label is written* | M1-11 (W4) |
| `labels/dev-100.jsonl` | 100 dev steps — what prompt iteration tunes against | M1-11 → M2-1 |
| `labels/heldout-50.jsonl` | 50 double-labeled steps carrying the **published headline κ**. Opened **once**, after the prompt bundle is frozen | M2-1 |
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
