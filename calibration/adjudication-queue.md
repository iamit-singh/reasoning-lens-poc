# The adjudication queue — rubric questions raised by the v1 pass

**Consumed by M2-2.** Its DoD is *"every adjudication is appended to `rubric.md` as a hard
case"*. This file is the agenda for that session: the questions the 90-step v1 pass could
not answer from the rubric alone, each with the reading the annotator actually applied.

> **Nothing here was resolved during the pass, and that is the point.** M1-11's card says
> it outright: *"Hard cases get a `notes` entry and a rubric hard-case entry; they do not
> get a rubric rule change mid-pass, because a rubric that changes during a labeling pass
> produces labels from two different rubrics in one file."* Every question below was
> therefore decided **once, consistently, for the whole pass** and written down rather than
> argued. v1's labels are internally consistent. Whether they are *right* is M2-2's call.

**These readings are binding on the pass, not on the rubric.** If M2-2 decides a question
the other way, the affected v1 labels are wrong and must be re-labelled — which is why the
blast radius is recorded against each one rather than discovered afterwards.

## Where the pass stands

| | |
| --- | --- |
| Labelled | 90 of the random-90 — positions 1–40 (M1-11) and 41–90 (M2-1a) |
| Annotator | amit, rubric v1, 2026-09-15, one sitting of ~3 h |
| Notes written | 82 of 90 steps |
| Draw composition | 77 `thinking`, 8 `direct`, 5 `react` |
| Soundness spread | 66 `unverifiable`, 23 `sound`, 1 `unsound` |

**73% of the pass is `unverifiable`, and questions 1–4 all move that pool.** That is the
single fact that should order the session: the soundness questions are worth more than the
behavior ones, because they touch two thirds of the labels and the behavior questions touch
a handful each.

---

## A. Soundness — what makes a claim checkable

### A1. Does a hedge change what a step asserts? — **highest blast radius**

A claim hedged into a question (*"…part of the University of Oxford?"*) or into
*"I'm not sure"*. The rubric is silent on interrogative and self-doubting assertions, and
the `thinking` arm under a no-browsing constraint generates them continuously.

- **Reading applied:** the hedge does not change the label. An unsourced factual
  proposition is unavailable to a reader either way.
- **Steps:** `thinking:thinking-mb-09-root-llm-0:3`, `thinking:thinking-mb-08-root-llm-0:40`
- **Blast radius:** large. `mb-08` alone runs the same interrogative assertion sixteen times
  across steps 26–41. A v2 that rules hedged recall out of *asserting* flips a block of this
  corpus at once.
- **The contrast that probably resolves it** (`thinking:thinking-mb-07-root-llm-0:1`):
  hedged *recall of a world fact* is unverifiable because of **what it claims**; hedged
  *arithmetic* is sound or unsound on the arithmetic, hedge notwithstanding. Same surface
  marker, different value — and **the deciding feature is whether the claim is derived on
  the page**, not whether it is hedged. If that holds, A1 is answered by restating §5
  rather than by adding a hedge rule.

### A2. Does common knowledge count as "outside knowledge"?

§5 makes a claim the step neither derives nor cites `unverifiable`. Elementary textbook
facts are asserted rather than derived, but are arguably not the outside knowledge the
clause is aimed at.

- **Reading applied:** `unverifiable`, by the letter of §5, held consistently across the
  pass.
- **Steps:** `react:react-mb-01-root-llm-0:0` (*"the answer is K"*),
  `thinking:thinking-mb-03-root-llm-0:0` (expanding *RGB*, where **the prompt itself supplies
  the acronym** — the sharpest case, since the expansion arguably does follow from the
  problem statement)
- **Note from the pass:** kept `unverifiable` *for consistency*, with the tension recorded.
  This is the question most likely to be decided against v1.

### A3. What does "cites" mean?

A step that gestures at a source the reader cannot reach — *"according to its website"*,
*"according to Wikipedia"*.

- **Reading applied:** an uncheckable gesture is not a citation → `unverifiable`.
- **Proposed v2 wording:** *cites* means **a source the reader can reach**.
- **Steps:** `thinking:thinking-mb-09-root-llm-0:26`, `thinking:thinking-mb-09-root-llm-0:33`

### A4. Is a tool return sound or unverifiable?

A ReAct observation carries a world fact the page cannot check. An annotator who reads the
preceding lookup call as the citation would say `sound`.

- **Reading applied:** `unverifiable` — the tool return is a world fact the page cannot
  check.
- **Steps:** `react:react-mb-10-root-tool-0-0:2`, `react:react-mb-08-root-tool-0-0:2`
- **Blast radius — measured, and smaller than the note feared.** The note says *"it will
  recur on every react trace"*. It does, but the corpus holds **8 observation steps in
  total**, 2 of them in this draw. Worth deciding; not worth leading with.

### A5. Does error propagation apply to an *unverifiable* predecessor?

§5's propagation rule is stated for **unsound** predecessors only. This corpus makes the
unverifiable-predecessor case routine, because hedged-recall chains are most of these
traces.

- **Reading applied:** a step that correctly reasons from an unverifiable prior is `sound`.
- **Steps:** `thinking:thinking-mb-09-root-llm-0:36`
- **v2 should say this explicitly** either way — it is currently inferred, not written.

### A6. Partially-emitted numbers

A truncated figure (`380800`, `minus 805=380`) that contradicts the step's own correct
intermediate. Annotators may read these as mid-stream typing rather than assertions.

- **Reading applied:** `unsound` on the contradiction. **This is the only `unsound` label in
  the entire 90-step pass**, so the whole `unsound` cell rests on this one call.
- **Steps:** `direct:direct-mb-06-root-llm-0:0`

---

## B. Behavior — where the label attaches

### B1. Clause-level or step-level? (the missing dominance rule)

The rubric gives a **precedence** rule — which class wins when several apply — but no
**dominance** rule: nothing says what to do when a non-linear move occupies one clause of a
step whose body is linear.

- **Reading applied:** **presence-based precedence**, uniformly. One qualifying clause
  carries the step.
- **Steps:** `thinking:thinking-mb-06-root-llm-0:0` (linear body, trailing unexecuted
  computation → `subgoal_setting`), `thinking:thinking-mb-09-root-llm-0:23` (mirror image →
  `backtracking`)
- **Why it matters beyond these two:** it interacts with segmentation. A dangling fragment
  at a segmentation boundary can carry a whole step's label under a presence-based rule.
- **A v2 sentence on clause-level vs step-level application would settle a recurring class
  of cases** — the annotator's own words, and the single most reusable fix on this list.

### B2. Does `backtracking` cover abandoning an *approach*?

§3.2 is written around withdrawing a claim. The observed case abandons an unproductive
enumeration strategy, having completed nothing.

- **Reading applied:** `backtracking`.
- **Steps:** `thinking:thinking-mb-09-root-llm-0:23`, and the contrasting
  `direct:direct-mb-06-root-llm-0:0` — *three restarts, but nothing completed to abandon* —
  labelled `linear`.

### B3. Must a revision be announced?

Step [1]'s guess is quietly replaced by another, with no clause marking the swap.

- **Reading applied:** an unannounced swap falls short of *"abandons or revises"* → `linear`.
- **Counter-reading:** an annotator applying the revision clause literally labels this
  `backtracking` **and wins on precedence**.
- **Steps:** `direct:direct-mb-10-root-llm-0:2`

### B4. Does expressed doubt alone count as revising?

*"But uncertain. Maybe it's a specific institute…"* casts doubt on a prior guess but
withdraws nothing. Likewise *"but 2015 might be wrong"* — a hedge that impeaches a
just-reached conclusion without retracting it.

- **Reading applied:** `linear`, per §4.2's *"something must be abandoned"* requirement.
- **Steps:** `direct:direct-mb-10-root-llm-0:1` (*"closest call in this batch"*),
  `thinking:thinking-mb-09-root-llm-0:36`

### B5. "Restates the goal" vs "names a sub-goal"

- **Reading applied:** naming an **intermediate** the main goal depends on is
  `subgoal_setting`; naming the main goal itself is `linear`.
- **Steps:** `thinking:thinking-mb-08-root-llm-0:0` (`subgoal_setting` — the asked-for thing
  is the *difference*, the populations are intermediate) vs `mb-14:0` (`linear` — the thing
  named *was* the main goal)
- **v2 should give an explicit test, because nearly every first step does one or the other.**

### B6. Re-derivation inside a repetition loop

A step that re-runs a whole derivation under a *"maybe there's nuance"* qualifier.

- **Reading applied:** `verification` (recompute-to-confirm, §3.1) rather than §4.3 bare
  restatement, because the chain is **re-derived and not merely repeated**.
- **Steps:** `thinking:thinking-mb-13-root-llm-0:3`
- **Consequence recorded in advance:** `mb-13` re-derives several times, so **`verification`
  will look inflated on that trace**. Expect classifier disagreement to cluster there.

### B7. §4.3's repetition wording is too narrow

§4.3 describes repetition as byte-identical. The observed loop **rotates its prefix** —
*"Let's think:"* / *"Let's check:"* / *"Let's search memory:"* — while repeating the same
proposition.

- **Reading applied:** §4.3's call, widened by judgement to cover rotated prefixes.
- **Steps:** `thinking:thinking-mb-08-root-llm-0:105` and the surrounding loop
- **Consequence:** a third of that loop opens with *"Let's check:"*, **a likely
  `verification` cue for the classifier**, so disagreement should cluster on this trace.

### B8. Meta / policy steps

A step deliberating about whether the **request** is permissible, rather than about the
problem. No prior result is checked; the policy question is raised and settled in one step.

- **Reading applied:** `linear` as the residual class; `unverifiable` because it rests on
  *"according to policy"*, an authority the reader cannot inspect.
- **Counter-reading:** an annotator holding that the step asserts nothing **about the
  problem** would say `sound`.
- **Steps:** `thinking:thinking-mb-10-root-llm-0:0`
- **The rubric has no class for this at all** — it is a gap, not a precedence question.

### B9. Invented continuity between two unsupported guesses

A figure speculatively attached to candidate A is silently reattached to candidate B. Both
endpoints are unverifiable, so the move collapses into one `unverifiable` and the
distinction is lost.

- **Reading applied:** `linear` / `unverifiable`, correct per §4.3, and **the rubric offers
  no way to mark the reattachment**.
- **Steps:** `thinking:thinking-mb-09-root-llm-0:7`
- The arm that hallucinates under a no-browsing constraint produces long runs of these.

---

## C. Not a rubric question — recorded here so it is not mistaken for one

### C1. Cross-arm label distributions are confounded by segmentation granularity

The `direct` arm packs a full derivation and its conclusion into **one** step; `thinking`
traces split comparable content across many. **If per-step label distributions are compared
across arms, some of the difference will be segmentation rather than behaviour.**

- **Steps:** `direct:direct-mb-13-root-llm-0:0`
- This is an instrument property, not a rubric gap. It constrains what M2-10b's scoreboard
  may claim, and it is promoted to [`../docs/findings.md`](../docs/findings.md) rather than
  resolved here.

### C2. Mid-sentence truncation is visible in the labelled steps

Several drawn steps are visibly cut mid-sentence. **The segmenter is frozen
(`segmenter-frozen-v1`) and this must not change it** — every ordinal would move and every
label in this file would detach from its text (Month-1 Hazard 1). Recorded as a known
property of the corpus the labels were written against, and as input to a *post-PoC*
segmenter revision, not this one.

### C3. Known-trap items invite reading ahead

`mb-12` is the bat-and-ball item; a labeller who recognises the trap knows the interesting
label is on a later step. §5's *judge-the-step-not-the-answer* rule covers it and the
annotator recorded not having read ahead — but **the temptation is real enough on a
known-trap item that it may be worth an explicit line in the tool's preamble**, where the
outcome-bias guard already lives as a property of the code.

---

## What M2-2 should do with this

1. **Take A1–A5 first.** They touch 66 of 90 labels; B1–B9 touch a handful each.
2. **Decide each question, then append it to `rubric.md` as a hard case** — that is M2-2's
   DoD, and it is also what makes v2 stand on its own for a reader who was not here.
3. **Re-label what a reversal invalidates.** A1 and A2 are the two that could move a large
   block; the step ids above are the starting list.
4. **Watch the byte-identity check.** `rubric.md`'s taxonomy block is byte-identical to the
   classifier prompt's and CI enforces it. If adjudication changes a **definition** rather
   than adding a hard case, `prompts/classify_and_triage.md` changes in the same commit or
   the build goes red.

## Related

- [`rubric.md`](rubric.md) — v1, the rubric these labels were written against
- [`annotator-2.md`](annotator-2.md) — the second annotator, and the brief that must not
  coach. **Nothing in this file may be sent to them**: it is the author's reasoning about
  the hard cases, and handing it over would measure the briefing rather than the rubric
- [`../docs/findings.md`](../docs/findings.md) — where C1 is promoted to a finding
