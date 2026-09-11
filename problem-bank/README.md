# Problem bank

`items/*.json` — 14 items under lever **L1** (down from 18; the L1/L2 decision is recorded
in [`../docs/day-1-unblock.md`](../docs/day-1-unblock.md)). Floors held: **≥ 5
`tool_required`, 3 `easy`, 3 `multi_step`**. ~~3 traps~~ — the trap floor is **withdrawn**
by [ADR-005](../docs/decisions/ADR-005-traps-do-not-reproduce.md).

Per-item shape (C3.4):
`{id, prompt, tags[], known_answer, checker, tolerance?, is_trap, trap_note?, source}`

`corpus/facts.json` — the ReAct `lookup` corpus. **12 facts under lever L2**, exact match
only. Written by M1-7, and the four facts the already-committed items depend on are
specified here rather than left for M1-7 to infer. An item whose lookup returns nothing is
not a `tool_required` item, it is a broken one:

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

**M1-7 ran, and the invented names paid for themselves twice over.** On `mb-08` arm 2 spent
**3,966 reasoning tokens failing to recall a population that does not exist** while arm 3
spent 80 and looked it up. A real city would have been answered from memory and there would
have been nothing to see.

> **⚠️ `lookup` matching is EXACT, and the tool description therefore lists every key.**
> Probed before arm 3 was built: with the keys unlisted the model asks for
> `"population of Fairhaven"` — sensible, and a miss every time. L2 forbids fuzzy matching,
> so discoverability is the only move left inside the lever. This does not scale past a few
> dozen facts and does not have to; L2 fixes the corpus at 12. See
> [ADR-007](../docs/decisions/ADR-007-react-arm-on-the-provider-layer.md).

## The traps: declared in M1-4, and **not earned** in M1-5

> **⚠️ No bank item claims `is_trap` any more.** All four declarations were withdrawn by
> [ADR-005](../docs/decisions/ADR-005-traps-do-not-reproduce.md) (accepted 11 Sep 2026)
> after **0 of 16 candidates earned the tag over 120 runs**. The items themselves stayed —
> they are perfectly good items — and lost only the claim the evidence withdrew. Their
> declarations live on in [`traps/candidates/`](traps/candidates/) with `retired_from` set,
> so the reproduction log still renders them.
>
> **A new `is_trap` claim needs an earned result first.**
> `test_the_bank_makes_no_unearned_trap_claim` enforces that.

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
misdirection we could construct.

**Nor is there a difficulty contrast to fall back on.**
[`arm-contrast.md`](arm-contrast.md) measured all 14 items plus 5 harder candidates on both
arms: **0 separate the arms**, 11 agreed, and the 3 that failed are `tool_required` items
run without tools. Arm 1's `low` effort turns out to be **adaptive** — 3 tokens on an easy
item, 407 on a hard one — so making items harder closes the cost gap without opening an
accuracy gap. See [ADR-006](../docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md).

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

**M1-5 raised the stakes on this control group, then proved it is all there is.**
[`arm-contrast.md`](arm-contrast.md) found no item separating the arms on accuracy, so the
`easy` items are not a control group against a contrast — **they are the contrast.** They
are where the cost ratio is largest and cleanest (arm 1 at 7–24% of arm 2's reasoning
tokens), and per [ADR-006](../docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) that
cost row is half of what FE-1 can feature. The other half is the **tool** contrast —
`mb-08`/`mb-09`/`mb-10` are wrong on both reasoning arms and should be right on arm 3,
which is the one wrong→right row this bank actually contains. **Unverified until M1-7.**

`arm-contrast.md` / `.json` — every item x both arms, pinned. `candidates/hm-*.json` — five
harder multi_step candidates authored to look for a separating item. They did not separate
either, so they have no claim on a bank slot under L1's fixed 14.

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

## `tool_required` is a declaration too

**2 of the 5 items tagged `tool_required` had arm 3 call no tool at all** — `mb-06` and
`mb-07`, both arithmetic — and answered correctly regardless. The floors above say the tag
is *"what makes B4 #7's `tool_required` share computable"*; a share computed from the tag is
wrong by two items out of five. **The measured share is in
[`arm-contrast.md`](arm-contrast.md)'s `tool calls` column.**

`is_trap` claimed 4 and earned 0. `tool_required` claims 5 and measures 3. The rule this
bank has earned: **a tag is a hypothesis until a run confirms it.** Recorded rather than
relabelled — dropping a tag changes an L1 floor, which is a scope decision.

Owners: M1-4 (items, W2) · M1-5 (trap validation + arm contrast, W3 — **trap DoD not met,
see ADR-005**) · M1-7 (corpus, arm 3, W3).
