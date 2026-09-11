# ADR-008 — The segmenter counts words, not model tokens

| | |
| --- | --- |
| **Status** | **Accepted** — 11 Sep 2026 (W3), with `segmenter-frozen-v1` |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | C4.2 steps 2d and 2e — the thresholds' *unit*, not the algorithm |
| **Evidence** | the ratio measured below over the project's own committed traces · `analyzer/tests/test_segmenter.py::test_the_segmenter_has_no_tokenizer_dependency` |
| **Depends on** | nothing. **Depended on by** every label written in Month 2 |

## Context

C4.2 specifies two thresholds without naming a tokenizer:

> *d. **Merge** any fragment under 15 tokens into the previous step … e. **Split** any step
> over 200 tokens at the sentence boundary nearest its midpoint*

The obvious reading is the model's own encoding — the project already pins
`LOCAL_TOKENIZER=o200k_harmony` and counts reasoning tokens with it (S1, G0 check 2). So
the segmenter would use `tiktoken.get_encoding("o200k_harmony")`.

**It cannot.** `tiktoken` does not vendor its BPE tables; `get_encoding` **fetches a remote
file** and caches it in a temp directory. That makes the thresholds depend on whether a
download succeeded, on a machine whose temp directory has not been cleared, at some point in
the past.

And the failure is silent. `llm.py` already wraps the same call in a `try/except` that
returns *no count* when the encoding is unavailable — the honest behaviour there, because a
missing token count is a reportable state. The segmenter has no such option: absence of a
count does not mean absence of a threshold, it means **a different threshold**, which means
different boundaries, which means **every `step_id` shifts**.

> `step_id` is `"{strategy}:{span_id}:{ordinal}"`. Hazard 1 in the Month-1 breakdown is
> that any change to the segmenter after labelling begins renumbers the ordinals and
> silently detaches every label from its text. A tokenizer that may or may not be there is
> a scheduled instance of Hazard 1, fired by something as ordinary as a cleared `/tmp`.

## Decision

**The segmenter's token unit is the whitespace-delimited word** (`len(text.split())`).
Nothing to install, nothing to fetch, identical on every machine and every Python.

The thresholds are **converted, not reinterpreted.** Keeping the numerals 15 and 200 as
word counts would have silently widened both caps by ~45%, so the ratio was measured over
the project's own corpus rather than assumed:

| | |
| --- | --- |
| Sample | 33 committed reasoning traces of 20+ words |
| Size | **7,531 words / 10,890 harmony tokens** |
| Pooled ratio | **1.446 tokens per word** (median 1.562, range 1.23–3.86) |

| C4.2 | At the measured ratio | Constant |
| --- | --- | --- |
| merge under **15 tokens** | 10.4 words | `MERGE_UNDER_WORDS = 10` |
| split over **200 tokens** | 138.3 words | `SPLIT_OVER_WORDS = 138` |

**`138` is kept rather than rounded to 140.** It is a derived number and it should look
like one; a round constant here would be a guess wearing the authority of a measurement.

## Why this is safe to freeze on

Two things were checked before tagging, because an amendment to a frozen file's thresholds
is only safe if the thresholds are not load-bearing in a way that could later move.

1. **The split cap never fires on the real corpus.** Over all 42 committed span trees and
   261 thought steps: **0 steps exceed 138 words** after segmentation. The longest is 130,
   the median 21. Five traces have reasoning longer than the cap, and C4.2's
   discourse-marker splits had already broken every one of them below it before the cap was
   consulted. So no segmentation that exists today depends on `SPLIT_OVER_WORDS`, and a
   later decision to change it cannot retroactively renumber anything.
2. **S3's verdict lands on M1-9, not here.** Breakdown §5.3 routes the two outcomes
   differently: too many steps per call is a batch-size change in M1-9, steps too *long* is
   a segmenter cap change that must precede the freeze. S3 measured the second and found
   steps are not the problem — see `docs/spikes/S3-batching.md`.

## Consequences

- **`tokens_out` on `Step` stays `None`.** We have no per-step *model* token count — the
  provider reports one number for the whole completion — and putting a word count in a
  field named `tokens_out` would be read as BPE tokens by everything downstream. A field
  that lies is worse than one that is empty.
- **The dependency ban is enforced, not documented.**
  `test_the_segmenter_has_no_tokenizer_dependency` parses `segment.py`'s imports and fails
  on anything outside `{__future__, itertools, re, rlens}`. A future edit reaching for the
  real tokenizer to make the cap "more accurate" fails the suite and has to read this ADR
  first. The same test pins both constants.
- **This is not a licence to use words elsewhere.** Cost, billing and the cost-of-thought
  metric all use the model's encoding via `llm.py`, counted at generation time where the
  optional dependency can honestly report its own absence. Words are a *segmentation* unit
  and nothing else.
- **If the corpus's character changes, the ratio should be re-measured.** 1.446 came from
  `gpt-oss:20b` reasoning traces in English prose with light arithmetic. Heavy LaTeX or
  code would push it up and the caps would effectively tighten. That is a re-measurement,
  and — because it changes `SPLIT_OVER_WORDS` — a freeze-breaking one.
