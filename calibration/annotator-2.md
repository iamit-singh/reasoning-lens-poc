# The second annotator — who, when, and the confirmation that matters

> ## ⛔ NOT YET RUN. Every field below is blank on purpose.
>
> This file is the **record** of M2-2's independent labelling pass, written **after** it
> happens. Nothing here is measured yet. If you are reading it looking for an IAA κ, there
> is not one — see [`results/latest.json`](results/latest.json), which currently reports
> *not yet measured*, which is correct.

**B4 #1 is the only criterion in this project that measures whether the rubric works for
somebody who did not write it.** Everything else — the classifier's κ, per-class F1, judge
recall — is measured against labels one person produced. If those labels encode one
person's private reading of the rubric, every downstream number inherits it and none of
them can detect it. That is what a second annotator is for, and it is why the *procedure*
matters as much as the number.

Appendix D #5 names the annotator: **Ankit**, committed for ~2 h in W6
([day-1 unblock](../docs/day-1-unblock.md)). There is no fallback. B4 #1 is unmeasurable
without a second human.

---

## The record — fill this in after the session

| | |
| --- | --- |
| **Annotator** | *(name)* |
| **Role / relationship to the project** | *(e.g. engineer on another team — the more distant from this project, the better the test)* |
| **Rubric sent on** | *(date — must be **before** the session)* |
| **Labelling session** | *(date, start–end)* |
| **Time taken** | *(actual — the estimate is ~2 h for 50 steps)* |
| **Label file** | `labels/<annotator>.jsonl` |
| **Steps labelled** | *(of 50 held-out)* |
| **Adjudication session** | *(date — separate from the labelling session)* |

### The confirmation, signed by the annotator

> *I labelled these steps working from `rubric.md` alone. Nobody walked me through it,
> nobody discussed any specific step with me before or during the pass, and I was not shown
> anyone else's labels or the classifier's predictions.*

**Annotator:** *(name)* **Date:** *(date)*

**If any part of that sentence is not true, say so here rather than signing it.** A κ
computed after a briefing measures how well the brief was delivered. Recording the
deviation costs the claim a caveat; hiding it costs every number in the project its
meaning.

*Deviations, if any:* *(none / describe)*

---

## The brief to send — verbatim, and nothing beyond it

C5.3 step 2 says *rubric-only, no prior discussion*. The failure mode is not malice, it is
helpfulness: the natural instinct when handing someone a task is to explain the tricky
cases, and **the tricky cases are exactly what is being measured.**

Send this, and only this:

> Could you spend about two hours labelling 50 short excerpts of model reasoning for the
> Reasoning Lens PoC?
>
> Everything you need is in `calibration/rubric.md` — five behaviour definitions, a
> precedence rule for when two apply, five worked examples and five adjudicated hard cases.
> Please read it first and keep it open while you work.
>
> Then run:
>
>     make label ARGS="--annotator <your-name>"
>
> It shows you one step at a time with the problem and the preceding steps as context. Two
> keypresses each — a behaviour and a soundness verdict — and an optional note. `[s]` skips
> one you genuinely cannot call, `[q]` quits and it resumes where you left off. Add a note
> whenever you hesitate; those notes are more useful to me than the labels you were sure
> about.
>
> **Please don't ask me about specific steps, and I won't volunteer anything.** We are
> measuring whether the rubric is clear enough to work from on its own, so a question I
> answer is a question the rubric failed to. Write the confusion in the note field instead
> — that is the finding.
>
> If the rubric is unclear in a general way — a definition that reads oddly, a missing case
> — tell me *after* you finish, not during.

### What not to do, stated because the instinct is strong

- **Do not sit with them while they label.** Presence is a brief.
- **Do not answer "is this one verification or linear?"** Point at the precedence rule.
- **Do not show them your labels, the classifier's output, or any report page.** The
  labelling tool is blind by construction; a screen over their shoulder is not.
- **Do not fix the rubric mid-pass.** A rubric that changes between step 12 and step 13
  makes the 50 labels two datasets. Note it and fix it in adjudication.

---

## After the labels: the ordering control

**Compute the IAA κ before the classifier's κ, and keep the commit order in git.**

    make calibrate                     # IAA on the 50 double-labelled steps

> **An IAA κ computed after the classifier's κ is known is not a measurement of annotator
> agreement.** It is a number produced by someone who already knows what it needs to be.
> B4 #1 gates classifier scoring for exactly this reason — the gate costs nothing if it is
> respected in W6 and **cannot be recovered afterwards**. Nothing about the file order
> makes this checkable later; only the commit order does.

Then adjudicate **every** disagreement by discussion, the adjudicated label becomes ground
truth, and **every adjudication is appended to `rubric.md` as a hard case** — that is how
the rubric gets better rather than just getting measured.

⚠️ **After editing `rubric.md`, `make rubric-drift` must still pass.** The taxonomy block is
byte-identical to the classifier prompt's, and CI enforces it. If adjudication changed a
*definition*, the prompt changes too — and that bumps `PROMPT_BUNDLE_VERSION`, which
invalidates the analysis cassettes and requires a re-record. Appending a hard *case* is
free; changing a definition is not.

## If κ < 0.70

C5.3 permits **one revision round only**: revise the rubric, re-label the 50, recompute.
That is +1.5 h Lead and a **second ask of the annotator**, so warn them at booking that it
may be needed.

If the second round is still below 0.70: **stop.** Publish the achieved κ and downgrade the
claim on the calibration page from *"reliable"* to *"indicative, with human agreement at
κ = X"*. **Do not take a third round.** That is B0 Condition #5's own logic, and a third
round is the expired time box wearing a new costume.
