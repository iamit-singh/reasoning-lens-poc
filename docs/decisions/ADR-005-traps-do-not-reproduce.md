# ADR-005 — Designed traps do not reproduce on `gpt-oss:20b`

*(This ADR's original subtitle read "…the arm contrast is difficulty, not misdirection". It
is struck: [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md) found no difficulty contrast
in the bank either. The claim is corrected below rather than quietly edited out.)*

| | |
| --- | --- |
| **Status** | **Accepted — option B** · 11 Sep 2026 (W3). **The second half of B did not survive implementation — see [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md).** |
| **Decided by** | Amit Singh (sole contributor) — it touches B6.3's "guaranteed wow moment" and C3.4's trap floor, so it was escalated rather than assumed |
| **Amends** | M1-5's DoD · C3.4's `is_trap` semantics · B6.2/FE-1's featured comparison · the L1 trap floor of 3 |
| **Evidence** | `problem-bank/traps/reproduction-log.md` + `runs.json` — **120 runs, 16 candidates, 1 trap hit** |
| **Depends on** | [ADR-004](ADR-004-direct-arm-minimal-reasoning.md) — this is its second consequence |
| **Blocks** | M1-5 only. **Not** M1-7 or M1-8, and deliberately not the build (see *Why CI stays green*) |

## Context

M1-4 declared four traps against a floor of three, and wrote down the hazard that
`mb-12`/`mb-13`/`mb-14` are cognitive-reflection archetypes a 20B model has very likely
memorised — with `mb-11` (geometry, archetype-free) as the hedge. M1-5 measures which of
them actually reproduce, at **≥ 3 of 5 runs**.

**None of them do. Nor do twelve further candidates authored in response.**

| Round | Candidates | Kind | Runs | Trap hits |
| --- | --- | --- | --- | --- |
| Declared (M1-4) | `mb-11` … `mb-14` | geometry path + 3 CRT archetypes | 48 | **1** |
| M1-5 round 1 | `tc-01` … `tc-06` | single-omission arithmetic mis-steps — weighted mean, compounding discounts, cuts-vs-pieces, percentage base change, two-phase rate, harmonic mean | 36 | **0** |
| M1-5 round 2 | `tc-07` … `tc-12` | inclusion–exclusion, constrained combinatorics, quarterly compounding, work-rate with departure, boundary off-by-one, mean after removal | 36 | **0** |
| | | **total** | **120** | **1** |

117 of 120 runs were correct. The single hit was `mb-13` on arm 1 at one sampled seed —
and it did not fire in the pinned regime, so even a trap that reached 3/5 on that
evidence would not be demo-safe.

The plan's stop rule for this is explicit and was followed: *"this is a content problem,
not a code problem — author more candidates. It is not a reason to lower the threshold."*
Twelve candidates were authored across two rounds, the second deliberately abandoning
word-problem arithmetic for the areas where a 20B genuinely slips. **The threshold has
not been lowered and no tag has been relabelled as passing.** The result is that the
instruction has been carried out and the finding survived it.

## The finding, stated plainly

**There is no shallow regime on this model to trap.** ADR-004 established that thinking
cannot be switched off — `reasoning_effort: "none"` and native `think: false` are both
silently ignored, and `low` is the floor. The trap premise assumed arm 1 would reason
shallowly enough to take an attractive wrong turn. At `low` it still produces a real
chain, and that chain is good enough to solve every misdirection we could construct.

This is ADR-004's second consequence, and the more expensive one. ADR-004 narrowed B4 #7
to *"medium vs minimal effort"*; M1-5 shows the minimal-effort arm is not weak enough to
be fooled **by design**.

~~What it *can* be beaten by is **difficulty**: M1-4's own control run has arm 1 wrong at
144 reasoning tokens on a multi-step probe where arm 2 is right at 1453.~~

> **⚠️ Struck. That was a probe, not a bank item, and it does not generalise.** Measuring
> the contrast across all 14 bank items plus 5 harder candidates found **0 of 16
> separating the arms**, because arm 1's `low` effort is *adaptive* — 3 tokens on an easy
> item, 407 on a hard one. See [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md). The
> generalisation from one probe to "the arm contrast is difficulty" was wrong, and it was
> wrong in the same way the trap premise was: both assumed arm 1 reasons less *and
> therefore fails sooner*.

The cost-of-thought half of B4 #7 is **unaffected** — it is a token-count claim, and the
cost separation holds across all 11 items where both arms answered (1.2x–13.3x). It is the
*accuracy* half of the arm comparison that has lost its instrument entirely.

## Options

| | Option | Cost | Assessment |
| --- | --- | --- | --- |
| **A** | Author more candidates, a third round | ~1.5 h per round, unbounded | 120 runs across three qualitatively different families argue the next round fails too. This is no longer over-provisioning; it is repetition |
| **B** | **Accept that the trap floor cannot be met on this model. Re-point FE-1's featured comparison at the verified difficulty contrast, and drop the trap floor from the L1 bank** | ~0 h now; FE-1 loses nothing it has | **Recommended.** The contrast it would show is already measured and reproducible, and it is the contrast B4 #7 actually claims |
| **C** | Change the generation model to one weak enough to trap | High — breaks the pin, re-runs S1/S6, invalidates every recorded number, and ADR-001's same-model rule means it changes *all three* arms | Buying a demo moment by making the subject worse is measuring the wrong thing |
| **D** | Push candidates to the model's capability ceiling until some fail | ~1 h | Produces **hard items, not traps**. A trap is defined by a *plausible wrong chain*, and an item the model fails through exhaustion has no designed chain to show. It would meet the floor's letter and empty the tag of meaning |

**Recommendation: B** — accepted. It is the only option that neither spends more hours on
a measurement that has answered, nor keeps a tag whose meaning the evidence has withdrawn.

> **⚠️ B's first half held; its second half did not.** Withdrawing the trap floor was
> correct and is implemented. But "re-point FE-1 at the verified difficulty contrast"
> rested on an **ad-hoc probe**, and measuring the contrast across the corpus before
> implementing it found **0 of 16 items separating the arms** — there was no difficulty
> contrast in the bank to point at. [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md)
> carries that finding, its cause (arm 1's `low` effort is adaptive, not shallow) and the
> replacement: the **cost** contrast, verified now, plus the **tool** contrast, pending
> M1-7.

## Consequences if B is accepted

- C3.4's `is_trap` becomes a **declaration with evidence attached**, not a guarantee. The
  authority is `problem-bank/traps/reproduction-log.md`, not the flag.
- The L1 trap floor of 3 is **withdrawn**; `easy` ≥ 3 and `multi_step` ≥ 3 carry the arm
  contrast on their own and are both verified on real runs.
- ~~**FE-1's featured comparison** becomes the difficulty pair~~ — **superseded by
  [ADR-006](ADR-006-arms-1-and-2-do-not-separate.md).** No bank item has arm 1 wrong and
  arm 2 right; the pair does not exist in this corpus.
- **M2-9 (cue injection) is not affected and becomes more load-bearing.** Faithfulness
  under an injected cue is a separate mechanism from a reasoning trap, and B6.3's wow
  moment now rests on it alone. S4 (M1-13, W4) is the early signal for it and should be
  treated as less slippable than C1.2's "safe to slip" list implies.

## Why CI stays green

M1-5 does not block G1 — the plan says so, and says to protect M1-8 over M1-5. So the
shortfall is recorded where it cannot be lost, without red-lighting the critical path:

- ~~The four declared traps **keep `is_trap: true`**~~ — **now flipped, the decision having
  been made.** The bank items stay (they are perfectly good items); their declarations moved
  to `problem-bank/traps/candidates/` with `retired_from` set, so the reproduction log still
  renders them and the record of what was tried is not deleted.
- `test_trap_reproduction.py::test_three_traps_reproduce_at_the_threshold` asserts M1-5's
  DoD and is marked **`xfail(strict=True)`** against this ADR. Strict is the point: the
  suite fails if the test ever *passes*, which forces the marker off the moment a trap
  does reproduce. The number cannot quietly drift in either direction.
- The rest of that file asserts what is true now: every declared trap and candidate has
  evidence on file, the evidence re-grades reproducibly from the stored response text, and
  the threshold is still 3 of 5.

## Two defects this measurement found, fixed in passing

Neither is about traps, and both would have been invisible until Month 3.

1. **`exact` scored 37.5% of correct answers wrong.** Asked for "the final answer on its
   own last line", the model answers `7 minutes`; a string compare against the declared
   `7` calls that wrong. **18 of the first 48 runs** were affected. `test_bank_answers.py`
   is structurally blind to it — it feeds each declared answer back into its own checker,
   and a string trivially equals itself. `exact` is now numeric-aware, with negation and
   multi-number ambiguity both refused, and `test_checkers.py` tests the grader against
   the shapes a model actually writes rather than against the bank.
2. **The answer extractor returned `\]`.** `mb-11`'s thinking arm closed with a LaTeX
   display block, so "the last non-empty line" was the closing delimiter. Trailing
   decoration is now skipped — and because the line above it carries four numbers, that
   run is reported **`unparsed`** rather than wrong. An unreadable answer counted as wrong
   understates accuracy for free, and accuracy is M1-9/M1-10's number to publish.

> **M1-8 should read #2 before freezing the segmenter.** C4.2 already requires the
> segmenter to treat `\[ … \]` as one sentence and never split inside a fence; the same
> delimiters decide where the `answer` step begins, and `_DECORATION` in
> `rlens/runner/run.py` is the list that has been observed in practice.
