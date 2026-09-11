# Rubric v1 — how to label a reasoning step

**You need nothing except this page.** No walkthrough, no worked session, no conversation
with whoever wrote it. If something here is ambiguous, that is a defect in this page and
not in you — write it in the `notes` field and label your best reading. Do **not** ask.

That is not politeness. The number this project publishes is *two people, given only a
written rulebook and no discussion, agreed this often*. A briefed annotator measures the
briefing. If you have already discussed the labels with someone, say so before you start,
because the number has to be described differently.

---

## 1. What you are doing

You will see one **step** at a time: a short passage from a model's reasoning on a problem,
plus the problem itself. You give it **two labels in the same pass**:

| Label | Question |
| --- | --- |
| **behavior** | What kind of reasoning move is this step? One of five. |
| **soundness** | Is this step correct, *given only what came before it*? One of three. |

You are **not** shown what the machine classifier predicted. That is deliberate and it is
enforced by the tool: it cannot show you a prediction, because a tool that could would
eventually be asked to.

---

## 2. The taxonomy

Everything between the two markers below is **byte-identical to the text the classifier is
given**. A CI check fails the build if the two ever drift apart, because if the human and
the machine are answering differently worded questions, the agreement number measures the
wording rather than the classifier.

<!-- BEGIN TAXONOMY -->
TAXONOMY  (label exactly one per step; if several apply use this precedence:
backtracking > verification > backward_chaining > subgoal_setting > linear)
  verification       — explicitly checks a prior result or claim for correctness:
                       recomputes it, substitutes it back, or sanity-checks units or
                       magnitude
  backtracking       — abandons or revises a previously pursued line: "that's wrong",
                       "let me try a different way"
  subgoal_setting    — names an intermediate objective to be solved before the main one:
                       "first I need X"
  backward_chaining  — reasons from the goal or answer state back toward prerequisites
  linear             — forward derivation exhibiting none of the above

VALIDITY  For each step also judge whether it is `sound`, `unsound` or `unverifiable`
GIVEN ONLY the preceding steps.
  sound         — follows from the problem statement and the preceding steps
  unsound       — contains a definite error: the arithmetic is wrong, the inference does
                  not follow, or it contradicts something already established
  unverifiable  — asserts a claim the step neither derives nor cites, which a reader
                  cannot check without outside knowledge
<!-- END TAXONOMY -->

### The precedence rule, and why it exists

**When more than one behavior label applies, take the leftmost:**

> `backtracking` > `verification` > `backward_chaining` > `subgoal_setting` > `linear`

Many steps genuinely do two things at once. A step that says *"that's wrong — let me
recompute"* is both backtracking and verification, and two careful annotators will split
on it forever unless they are given a tie-break. Multi-label would also make Cohen's κ
inapplicable, so the choice is not between single and multi; it is between single-with-a-rule
and single-by-vibes.

**`linear` is the residual, not a judgement of quality.** Most steps are `linear`. A long
stretch of `linear` steps is not a criticism of the model, and labelling something `linear`
is not giving up — it is the correct answer whenever none of the other four fit.

---

## 3. Five worked examples — one per class

Each shows the step, the label, and *the words that decided it*.

### 3.1 `verification`

> **Step:** *"Let me check that: 42 plus 17 is 59, and 59 delegates at $17 each gives
> 59 × 17 = 1003."*

**Label: `verification`.** It re-does a computation that has already been made, for the
purpose of confirming it. The deciding feature is that the arithmetic is a *re-run of
earlier work*, not new work.

> ⚠️ Note what is **not** required: the check does not have to be correct, or even
> competent. This one confirms an earlier mistake. `verification` describes the *move*;
> whether the move succeeded is the **soundness** label's business, and that separation is
> the whole reason there are two labels.

### 3.2 `backtracking`

> **Step:** *"So the answer is 8 kilometres — wait, that is the distance where they cost
> the same, not where A is cheaper."*

**Label: `backtracking`.** It abandons a conclusion the trace had just reached. The
deciding feature is the *reversal*: something previously asserted is withdrawn.

> Words that often signal it: *wait*, *actually*, *that's wrong*, *hold on*, *no —*,
> *let me try a different way*. The word alone is not enough (see hard case 4.2).

### 3.3 `subgoal_setting`

> **Step:** *"First I need an expression for each courier's total cost as a function of
> distance; once I have both, the comparison is a single inequality."*

**Label: `subgoal_setting`.** It names a smaller problem to solve on the way to the real
one. The deciding feature is that it **states an intention and does not yet execute it**.

### 3.4 `backward_chaining`

> **Step:** *"For the answer to be a whole number of kilometres, what I ultimately need is
> the crossover distance where the two totals are equal; the answer is the first whole
> number above it."*

**Label: `backward_chaining`.** It starts from the *form the answer must take* and reasons
back to what must be computed. The deciding feature is **direction**: from the goal
towards the prerequisites, rather than from the givens towards the goal.

> The commonest confusion is with `subgoal_setting`, and §4.1 is about exactly that.

### 3.5 `linear`

> **Step:** *"Courier A costs 6 + 1.40k and courier B costs 2.15k. Setting them equal:
> 6 + 1.40k = 2.15k, so 6 = 0.75k and k = 8."*

**Label: `linear`.** Forward derivation. It takes what is known and moves one step onward.
Nothing is checked, abandoned, planned or reasoned backwards from.

---

## 4. Five hard cases, with the adjudicated answer

These are the disagreements that actually happen. Each has **one** answer, and it is
binding — including when you disagree with it. Write the disagreement in `notes`; that is
what the notes field is for, and a rubric revision is a deliberate act between labelling
passes, never during one.

### 4.1 `subgoal_setting` vs `backward_chaining`

> *"To get the total cost I need the number of delegates first."*

**Adjudicated: `subgoal_setting`.**

Both labels describe reaching backwards from a goal, and the distinction is genuinely thin.
The rule: **`backward_chaining` reasons about the *answer's properties*; `subgoal_setting`
names the *next thing to compute*.** If the step could be rewritten as *"step 1: do X"*
without losing anything, it is `subgoal_setting`. If it argues from what the final answer
must look like, it is `backward_chaining`.

Precedence settles ties anyway: `backward_chaining` outranks `subgoal_setting`, so a step
that is unmistakably both takes `backward_chaining`.

### 4.2 A `wait` that reverses nothing

> *"Wait, let me also compute the second courier's cost."*

**Adjudicated: `linear`.**

The word *wait* is a verbal tic here. Nothing is withdrawn — the step adds work rather than
undoing any. **`backtracking` requires something to be abandoned or revised.** Label the
move, not the vocabulary.

### 4.3 A restatement

> *"So, again, 21 printers, each printing one poster in 7 minutes."*

**Adjudicated: `linear`.**

A step that repeats an earlier conclusion without checking it, changing it or planning from
it is `linear`. It is not `verification`, because nothing is re-derived — the figure is
merely said again.

> This case is common on this corpus and it matters: one trace repeats a single sentence
> **126 times**. Every one of those steps is `linear`. That is not a defect in the rubric;
> it is the rubric correctly describing a model stuck in a loop.

### 4.4 A tool call

> *"calculator(expr="6 / (2.15 - 1.40)")"*

**Adjudicated: `linear`, unless the step's text names an intermediate objective.**

A bare tool invocation is a forward move. But the ReAct arm often puts the *intention* in
the thought immediately before it, and **that** step is usually `subgoal_setting`. Label
each step on its own text. An **observation** (the tool's returned value) is `linear`.

### 4.5 The final answer

> *"1003"*

**Adjudicated: `linear`, and `unverifiable` for soundness** when the answer merely restates
a figure derived above.

The answer step is not excluded from the behavior taxonomy, but it is almost never
interesting. For soundness: if the answer follows arithmetically from the immediately
preceding step, `sound`; if it restates a figure whose derivation is elsewhere and not
re-checked here, `unverifiable`.

---

## 5. Soundness — the three values in detail

The definitions in §2 are binding. What follows is how to apply them.

**The one rule that overrides your instincts: you are judging the step, not the answer.**
You are not told whether the model got the problem right, and you must not try to work it
out. A trace that reaches the right answer through a broken step contains a broken step.

| Value | Use it when | Do **not** use it when |
| --- | --- | --- |
| `sound` | The step follows from the problem and the preceding steps. Terse is fine — a correct step that shows little working is still `sound`. | You merely agree with where the trace ended up. |
| `unsound` | There is a **definite** error you can point to: wrong arithmetic, an inference that does not follow, a contradiction with something already established. | You suspect it is wrong but cannot name the defect. That is `unverifiable`. |
| `unverifiable` | The step asserts something it neither derives nor cites, and you would need outside knowledge to check it. | The step is merely hard to read. Read it again. |

### `unverifiable` is the one that gets misused

It means **"this cannot be checked from what is on the page"** — a claimed population
figure, a named constant, a fact about the world. It does **not** mean "I am unsure". If
you are unsure between `sound` and `unsound`, re-read the preceding steps; if the step
derives what it claims, it is `sound`.

A step that is *summarised* rather than shown — *"verified the product and found it
consistent"* — is `unverifiable`: it reports that reasoning happened without showing it.

### Errors propagate; the labels do not

If step 3 computes `2 × 9 = 17` and step 4 correctly carries 17 forward, **step 3 is
`unsound` and step 4 is `sound`.** Step 4 does its own job correctly. Label each step
against the ones before it, taking those as given. Otherwise a single early slip turns
every later step red and the flagged-step count stops meaning anything.

---

## 6. Mechanics

```
make label                    # opens the next unlabelled step in the queue
make label ARGS="--count 10"  # do ten and stop
```

* The queue order is **fixed by a committed seed** (`calibration/sampling.json`) and drawn
  before any label was written. Do not reorder it, and do not skip ahead to find
  interesting steps — that would bias the very sample the seed exists to protect.
* **Skipping is allowed and is recorded.** If a step is unreadable or you genuinely cannot
  decide, skip it with a note. A skipped step is data; a guessed step is noise wearing
  data's clothes.
* Each label is appended to a JSONL file with your name and a timestamp. Nothing is
  overwritten; a re-labelled step appears twice and the later one wins.

### What goes in `notes`

Anything that made the call hard. Specifically: a case this rubric does not cover, a case
where you followed §4 while disagreeing with it, or a step whose text looks truncated or
mis-segmented. These notes are read between passes and are how v2 gets written.

---

## 7. Provenance

| | |
| --- | --- |
| Version | **v1** — M1-11, W4 |
| Taxonomy source | Gandhi et al., *Cognitive Behaviors that Enable Self-Improving Reasoners* (arXiv:2503.01307), Part A §A3 |
| Binding on | every label in `calibration/labels/` |
| Paired with | `analyzer/src/rlens/prompts/classify_and_triage.md` — the taxonomy blocks are byte-identical and CI enforces it |

**Changing this page invalidates labels written under the previous version.** A rubric edit
mid-pass produces one file containing labels from two different rubrics, which is not a
dataset. If v2 is needed, it lands between passes and the labels record which version they
were written under.
