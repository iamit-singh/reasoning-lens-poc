# Problem bank

`items/*.json` — 14 items under lever **L1** (down from 18; the L1/L2 decision is recorded
in [`../docs/day-1-unblock.md`](../docs/day-1-unblock.md)). Floors held: **≥ 5
`tool_required`, 3 traps, 3 `easy`, 3 `multi_step`**.

Per-item shape (C3.4):
`{id, prompt, tags[], known_answer, checker, tolerance?, is_trap, trap_note?, source}`

`corpus/facts.json` — the ReAct `lookup` corpus. **12 facts under lever L2**, exact match only.
Owned by M1-7 (W3), but **three items already committed depend on it**, so the facts they
need are specified here rather than left for M1-7 to infer. An item whose lookup returns
nothing is not a `tool_required` item, it is a broken one:

| Fact key | Value | Needed by |
| --- | --- | --- |
| `fairhaven_population` | `128400` | `mb-08` |
| `brightwater_population` | `96750` | `mb-08` |
| `meridian_institute_founded` | `1887` | `mb-09` |
| `meridian_institute_departments` | `metallurgy, hydrology, cartography` | `mb-10` |

The place names are **invented on purpose**. A lookup item about a real city measures
whether the model already knows the answer, not whether it used the tool — the model
answers from memory, the tool is never called, and the `tool_required` tag becomes a
label for something that did not happen. `test_bank_answers.py` cannot catch that; only
M1-7's arm-3 runs can, so it is written down here.

## The traps: declared in M1-4, and **not earned** in M1-5

> **⚠️ `is_trap: true` in `items/` is a DECLARATION, not a verified property.** The
> authority is [`traps/reproduction-log.md`](traps/reproduction-log.md), and it currently
> records **0 of 16 candidates earning the tag over 120 runs**. Do not read the flag as
> evidence that an item traps the model — it does not.

M1-4 declared four traps against a floor of three and wrote down the risk that `mb-12`,
`mb-13` and `mb-14` are famous cognitive-reflection archetypes the model may have
**memorised**, with `mb-11` (geometry, archetype-free) as the hedge. M1-5 measured all
four, then authored twelve more candidates in two rounds — the second abandoning
word-problem arithmetic for inclusion–exclusion, constrained combinatorics and
compounding. **117 of 120 runs were correct and exactly one reproduced a declared wrong
chain.**

The threshold was not lowered and no tag was relabelled as passing. The finding is that
**there is no shallow regime on this model to trap**: ADR-004 established that thinking
cannot be switched off and `low` is the floor, and at `low` the chain still solves every
misdirection we could construct. What the arms *can* be separated by is **difficulty** —
see [ADR-005](../docs/decisions/ADR-005-traps-do-not-reproduce.md) for the four options,
the recommendation, and why the four items keep their flag until someone decides.

`traps/candidates/*.json` — the twelve M1-5 candidates. Outside `items/` on purpose: lever
L1 fixes the bank at exactly 14 items, so "author more candidates" cannot mean growing the
bank. A candidate would be *promoted* into `items/` on earning its tag, replacing a
declared trap that did not.

`traps/runs.json` — every run, with the full response text, so the whole measurement
re-grades offline after a grader change. M1-5 needed that twice.

> **A trap is *declared* in M1-4 and *earned* in M1-5.** An item tagged `is_trap: true` that
> does not reproduce a plausible wrong chain in **≥ 3 of 5 runs** is a normal item with a
> misleading tag. If fewer than 3 traps reach 3/5, author more candidates — **do not lower
> the threshold.**

## The `easy` items are a control group (ADR-004)

The four `easy` items are not filler. ADR-004 found that arm 1 runs at `low` reasoning
effort — thinking cannot be switched off on this model — and that at `low` it got a
multi-step probe wrong while arm 2 got it right.

**If every item separates the arms that cleanly, the bank measures difficulty, not
strategy**, and the cost-of-thought finding collapses into "harder problems need more
thinking". The `easy` items are where arm 1 should **match** arm 2 at a fraction of the
tokens. That contrast is the result; without it there is no baseline worth the name.

`test_bank_answers.py` asserts a structural proxy for this (single step, no chaining
language, not a trap). Whether the arms actually agree is a measurement, and it belongs
to W3 alongside M1-5.

**M1-5 raised the stakes on this control group.** With the trap axis gone, the
`easy`-vs-`multi_step` difficulty contrast is the *only* verified way this bank separates
the arms on accuracy — and it is the contrast ADR-005 recommends FE-1 feature.

## A grading defect M1-5 found, and what it means for this bank

The `exact` checker was a string compare, so a model answering `7 minutes` to `mb-13`
scored **wrong** — 18 of the first 48 runs were affected, 37.5%. `test_bank_answers.py`
cannot catch this class of defect by construction: it feeds each declared answer back into
its own checker, and a string trivially equals itself. `exact` is now numeric-aware
(`analyzer/src/rlens/checkers.py`), and `test_checkers.py` tests the grader against the
shapes a model actually writes rather than against the bank.

**When authoring an item, the `known_answer` is a bare value and the model's answer will
not be.** `315` is matched by `315 square metres`; it is not matched by `not 315`, nor by a
worked line carrying four numbers — the latter reports `unparsed` rather than wrong,
because an unreadable answer counted as wrong understates accuracy for free.

Owners: M1-4 (items, W2) · M1-5 (trap validation, W3 — **DoD not met, see ADR-005**) · M1-7 (corpus, W3).
