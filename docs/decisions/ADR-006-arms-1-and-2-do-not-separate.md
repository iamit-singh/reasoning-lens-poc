# ADR-006 — Arms 1 and 2 do not separate on accuracy anywhere in the bank, because arm 1's minimal effort is *adaptive*

| | |
| --- | --- |
| **Status** | **Proposed** — 11 Sep 2026 (W3). Needs a call on what FE-1 features and how B4 #7 is worded. **Option A's tool contrast is now MEASURED and confirmed — see the postscript.** |
| **Decided by** | *open* — it narrows a headline claim, so it is not the implementer's call |
| **Supersedes** | the second half of [ADR-005](ADR-005-traps-do-not-reproduce.md)'s option B ("re-point FE-1 at the difficulty contrast"), which turns out not to be satisfiable |
| **Amends** | B4 #7's accuracy claim · B6.2/FE-1's featured comparison · `check_regime_separation`'s warning text |
| **Evidence** | `problem-bank/arm-contrast.md` + `.json` — 14 bank items x **3** arms, pinned · 5 harder candidates x 2 arms · the 120 runs behind ADR-005 |
| **Depends on** | [ADR-004](ADR-004-direct-arm-minimal-reasoning.md) — this is the sharper version of it |

## Context

ADR-005 recommended withdrawing the trap floor and re-pointing FE-1's featured comparison
at the **difficulty** contrast instead: an item where arm 1 is wrong and arm 2 is right.
That recommendation was accepted.

Its evidence was an **ad-hoc probe**, not a bank item. M1-4's control run used `--prompt`
(arm 1 wrong at 144 reasoning tokens, arm 2 right at 1453), and ADR-005's own 120 runs
touched only the four trap items, on which both arms were correct every time. So before
implementing the decision, the contrast was measured across the whole corpus — the
measurement `test_bank_answers.py` already said belonged to W3.

**No item separates the arms.**

| Pattern | Items | |
| --- | --- | --- |
| **separated** — arm 1 wrong, arm 2 right | **0** | the row FE-1 needs, and it is empty |
| **agreed** — both right | **11** | every non-tool item in the bank |
| **both wrong / incomplete** | 3 | `mb-08`, `mb-09`, `mb-10` — all `tool_required`, run without tools. Expected, and arm 3's job |
| **inverted** — arm 1 right, arm 2 wrong | 0 | |

Five further candidates were then authored at the difficulty of the separating probe —
chained four-digit arithmetic with a floor, successive percentages on a seven-figure base,
three-step compound decay, a propagating day-on-day dependency, mixed units across three
phases. **All five agreed as well.** 16 items, 0 separations.

## Why: `low` effort is adaptive, not a shallow budget

The trap premise and the difficulty premise share one assumption — that arm 1 reasons
*less* and will therefore fail *sooner*. It reasons less **only when less is enough**:

| Item | Arm 1 tokens | Arm 2 tokens | Arm 1 / Arm 2 |
| --- | --- | --- | --- |
| `mb-03` (easy, factual) | 3 | 40 | **0.07** |
| `mb-01` (easy, factual) | 5 | 21 | 0.24 |
| `mb-13` (multi_step, logic) | 37 | 259 | 0.14 |
| `mb-07` (multi_step, arithmetic) | 85 | 227 | 0.37 |
| `mb-06` (multi_step, arithmetic) | 169 | 206 | **0.82** ⚠ |
| `hm-02` (7-figure successive percentages) | **407** | 423 | **0.96** ⚠ |

**The ratio rises with difficulty.** Arm 1 spends 3 tokens on an easy factual and 407 on
hard arithmetic — and on the hardest items it spends *almost exactly what arm 2 spends*.
So there is no difficulty band where arm 1 is out of its depth and arm 2 is not: arm 1
simply buys more thinking, out of sight, at the same price. `reasoning_effort: "low"` caps
the *style*, not the budget.

This is ADR-004's finding taken one step further. ADR-004 established that thinking cannot
be turned **off**. ADR-006 establishes that it cannot usefully be turned **down** either —
which is what actually forecloses the accuracy half of the arm comparison.

> **Consequence for the two arms, stated plainly: on this model, arms 1 and 2 differ in
> cost and not in correctness.** Making items harder does not open an accuracy gap; it
> closes the cost gap as well, which is the worse of the two trades.

## What the evidence *does* support

Two contrasts are real, measured and reproducible. Neither is the one the plan expected.

1. **Cost of thought — arms 1 vs 2.** On **11 of 11** items where both arms answered,
   they returned the same answer and arm 2 spent **1.2x to 13.3x** more reasoning tokens.
   That is B4 #7's cost claim, intact and quantified, and it is a stronger headline than
   it first sounds: *deliberation cost up to thirteen times more and changed the answer on
   none of sixteen problems.* For an instrument whose purpose is making reasoning
   measurable rather than impressive, that is a finding, not a disappointment.
2. **Tool use — arm 3 vs arms 1 and 2.** `mb-08`, `mb-09` and `mb-10` are wrong on **both**
   reasoning arms, because the facts they need are in `corpus/facts.json` and neither arm
   can reach it. If arm 3 answers them, that is a genuine **wrong → right** row: the one
   separation this bank actually contains. ~~It is unverified until M1-7 runs~~ —
   **verified, see the postscript. Arm 3 is 14/14.**

## Options

| | Option | Assessment |
| --- | --- | --- |
| **A** | **FE-1 features the cost contrast (arms 1v2, verified now) plus the tool contrast (arm 3, pending M1-7)** | **Recommended.** Both rest on committed corpus evidence, and M1-7 is next anyway. Re-words B4 #7's accuracy claim from "thinking buys the answer" to "tools buy the answer; thinking buys only cost" |
| **B** | Keep hunting for a separating item | 16 items across three difficulty families found none, and the ratio table explains why. This is not a sampling problem |
| **C** | Widen the arm gap with a weaker model for arm 1 | ADR-001's same-model rule forbids it, and it would measure vendors rather than strategies |
| **D** | Report the arms as non-separating and drop the accuracy claim entirely | Honest but wasteful: option A's tool contrast is very likely to supply a real wrong→right row, and costs nothing extra to check |

**Recommendation: A**, with the tool contrast confirmed or refuted by M1-7 before FE-1 is
specified in W5.

## Consequences

- **B4 #7's accuracy claim is re-worded, not deleted.** Arms 1 and 2 separate on cost;
  accuracy separation, if it exists in this PoC, comes from **tools**.
- **M2-9 (cue injection) carries B6.3's wow moment alone**, as ADR-005 already noted — and
  now with no fallback at all, since the difficulty contrast is gone too. **S4 (M1-13, W4)
  is the early signal and should be treated as un-slippable**, against C1.2's listing of
  it as safe to slip.
- **`check_regime_separation` needs its message re-worded, not its threshold moved.** Its
  0.5 ratio correctly fires on `mb-06` (0.82) and `hm-02` (0.96), but the warning text
  blames the request and points at ADR-004. On a hard item the cause is adaptive effort,
  not misconfiguration, and a guard that cries wolf is a guard someone eventually relaxes
  — the same failure this project has now hit four times.
- **The `easy` items are vindicated and become more load-bearing.** ADR-004 kept them as a
  control group against the risk that the bank measured difficulty rather than strategy.
  They are now the *only* place the cost ratio is large and clean (0.07–0.24), which is
  exactly the contrast option A features.
- `problem-bank/candidates/hm-*.json` stay **candidates**. They did not separate the arms,
  so they have no claim on a bank slot under L1's fixed 14.

---

## Postscript — M1-7 ran, and option A's evidence is now in the corpus (11 Sep 2026)

Arm 3 was built the same day (M1-7, [ADR-007](ADR-007-react-arm-on-the-provider-layer.md))
and the contrast re-measured across all three arms:

| | Arm 1 (minimal) | Arm 2 (thinking) | **Arm 3 (ReAct)** |
| --- | --- | --- | --- |
| Correct, 14 bank items | 11/14 | 11/14 | **14/14** |

**All three of the predicted wrong → right rows landed.** `mb-08`, `mb-09` and `mb-10` are
wrong on both reasoning arms and correct on arm 3. Option A's accuracy claim now rests on
corpus evidence rather than on a probe — which is exactly the standard this ADR was written
to insist on, so it is worth stating plainly that the standard was met rather than assumed.

**And the rows are cheaper, not merely better:**

| Item | Arm 2 (thinking) | Arm 3 (tools) | |
| --- | --- | --- | --- |
| `mb-08` | unparsed, **3,966** reasoning tok | correct, **80** tok | 50× cheaper |
| `mb-09` | wrong, 1,568 tok | correct, 38 tok | 41× cheaper |
| `mb-10` | wrong, 847 tok | correct, 36 tok | 24× cheaper |

> On `mb-08` the thinking arm spent **3,966 reasoning tokens failing to recall a fact that
> does not exist** — every place name in the corpus is invented, on purpose — while the
> tool arm spent 80 and looked it up. **That pair is the product in one frame:** one
> reasoning panel showing confabulation at length, beside one showing two tool calls. It is
> a better demo row than the difficulty contrast the plan originally expected, and unlike
> that one it exists in the corpus.

So **option A is recommended more strongly than when this ADR was filed**, and B4 #7's
re-wording is now specific: *tools* buy the answer; *thinking* buys cost. Both halves are
measured.

### One new finding, and it is the third tag in a row to be a claim rather than a property

**2 of the 5 items tagged `tool_required` had arm 3 call no tool at all** — `mb-06` and
`mb-07`, both arithmetic — and answered correctly regardless. `problem-bank/README.md`
states that the tag floors are *"what make B4 #7's `tool_required` share computable"*, so a
share computed from the tag is wrong by two items out of five. The measured share is in
`arm-contrast.md`'s `tool calls` column.

This is the same shape as `is_trap` before M1-5 measured it, and the pattern is now worth
naming as a rule rather than a recurrence: **in this bank, a tag is a hypothesis until a run
confirms it.** `is_trap` claimed 4 and earned 0; `tool_required` claims 5 and measures 3.
Recorded rather than relabelled, because dropping the tag changes the L1 floor and that is a
scope decision — the same reason ADR-005 escalated rather than flipping the trap flags.
