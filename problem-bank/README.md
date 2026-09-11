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

`traps/reproduction-log.md` — M1-5's evidence.

**Four traps are declared against a floor of three.** M1-5's instruction is to
over-provision and expect failures, and the three CRT-archetype traps (`mb-12`, `mb-13`,
`mb-14`) carry a specific risk: **the archetypes are famous, so the model may have
memorised the correct answer** and sail past the trap. Their surfaces are rewritten
(notebook/pen, printers/posters, algae/pond) to blunt that, but rewriting a surface is a
mitigation, not a guarantee. `mb-11` is the hedge — a geometry trap with no archetype
behind it. **If the CRT three all fail M1-5's 3/5 threshold, the cause is most likely
memorisation, and the fix is more non-archetype candidates like `mb-11`, not a lower
threshold.**

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

Owners: M1-4 (items, W2) · M1-5 (trap validation, W3) · M1-7 (corpus, W3).
