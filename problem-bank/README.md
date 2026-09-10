# Problem bank

`items/*.json` — 14 items under lever **L1** (down from 18; the L1/L2 decision is recorded
in [`../docs/day-1-unblock.md`](../docs/day-1-unblock.md)). Floors held: **≥ 5
`tool_required`, 3 traps, 3 `easy`, 3 `multi_step`**.

Per-item shape (C3.4):
`{id, prompt, tags[], known_answer, checker, tolerance?, is_trap, trap_note?, source}`

`corpus/facts.json` — the ReAct `lookup` corpus. **12 facts under lever L2**, exact match only.

`traps/reproduction-log.md` — M1-5's evidence.

> **A trap is *declared* in M1-4 and *earned* in M1-5.** An item tagged `is_trap: true` that
> does not reproduce a plausible wrong chain in **≥ 3 of 5 runs** is a normal item with a
> misleading tag. If fewer than 3 traps reach 3/5, author more candidates — **do not lower
> the threshold.**

Owners: M1-4 (items, W2) · M1-5 (trap validation, W3) · M1-7 (corpus, W3).
