# The second annotator — who, when, and the confirmation that matters

> ## ✅ RUN — 15 Sep 2026. B4 #1 is measured.
>
> **behavior κ 0.867** · **soundness κ 0.935** · n = 50 · amit vs ankit, rubric v1.
> Both clear B4 #1's 0.70 bar on the point estimate. **The behavior interval does not**
> — 95% CI [0.495, 1.000] — and §"What the number does and does not support" below is
> the part of this record that matters more than the headline.
>
> Computed by `make calibrate ARGS="--iaa"` and committed **before** any classifier
> scoring of the held-out set. It is in [`results/latest.json`](results/latest.json)
> under `inter_annotator`.

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

## The record

| | |
| --- | --- |
| **Annotator** | **Ankit** (Appendix D #5) |
| **Role / relationship to the project** | ⚠️ *not recorded — Amit to fill in* |
| **Rubric sent on** | ⚠️ *not recorded — Amit to fill in. Must be **before** the session* |
| **Labelling session** | 2026-09-15 · rows written 13:39:37Z |
| **Time taken** | ⚠️ *not evidenced by the file — Amit to fill in* (see the note below) |
| **Label file** | `labels/heldout-50.jsonl` — 50 rows carrying `"annotator": "ankit"` |
| **Steps labelled** | **50 of 50.** No skips, no duplicates, all `rubric_version: v1` |
| **Notes written** | 14 of 50 |
| **Adjudication session** | ⚠️ **not yet held** — 2 disagreements queued, see below |

**Every one of the 50 is in the held-out half of the draw** (`sampling.json` positions
41–90) and **nothing else is** — verified against the draw, not against the filename,
which is the check M2-13 had to rebuild. The pass did not walk across the dev boundary.

> **On the timestamps, stated rather than left for an auditor to find.** All 50 rows carry
> the same `labeled_at` (13:39:37Z), so **the file evidences no elapsed time at all** and
> cannot corroborate a ~2 h session. This is the same artefact `calibration/README.md`
> already records for rows 31–90 of the first pass — `labeled_at` stamps the *write*, not
> the reading, and a batched entry collapses the spread.
>
> **But `calibration/README.md` drew a line at exactly this pass.** Having excused the
> batching in the first pass, it says the second annotator's pass *"must be typed, one step
> at a time, in the annotator's own sitting"* — because batched entry removes the only
> timing evidence that the pass happened as described. That control was not met. It is not
> evidence of anything wrong; it is evidence of **nothing**, which is why **the signed
> confirmation below is the control that actually carries this claim** — and it is unsigned.

### The confirmation, signed by the annotator

> *I labelled these steps working from `rubric.md` alone. Nobody walked me through it,
> nobody discussed any specific step with me before or during the pass, and I was not shown
> anyone else's labels or the classifier's predictions.*

**Annotator:** ⚠️ **UNSIGNED — Ankit to sign** **Date:** *(date)*

> **This is the one outstanding item on M2-2 that is not a discussion.** The labels are in
> and the κ is computed, but the sentence above is what makes it a *measurement of the
> rubric* rather than a measurement of whatever briefing happened. Until Ankit signs it,
> B4 #1 is reported with that caveat attached. Getting it signed is a two-minute ask.

**If any part of that sentence is not true, say so here rather than signing it.** A κ
computed after a briefing measures how well the brief was delivered. Recording the
deviation costs the claim a caveat; hiding it costs every number in the project its
meaning.

*Deviations, if any:* ⚠️ *not recorded — ask at signing.* One specific question worth
putting to him, because the brief below was wrong when it was sent: **which command did he
run?** `make label ARGS="--annotator ankit"` — the brief's exact text — defaults to
`--part dev` and would have served him **the wrong 50 steps**. His labels are all held-out,
so he did not run that; whatever he did run came from somewhere other than this file.

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
>     make label ARGS="--annotator <your-name> --part heldout"
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

> **`--part heldout` is not optional.** It defaults to `dev`, which is a different 50 steps
> and the wrong task. This line was wrong in the version of the brief that was sent on
> 15 Sep — it read `make label ARGS="--annotator <your-name>"` — and the only reason it cost
> nothing is that the pass landed on the held-out set anyway. C5.3 permits a re-label round
> that would send this file again, so it is fixed here rather than remembered.

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

    make calibrate ARGS="--iaa"        # IAA on the 50 double-labelled steps

> **`make calibrate` on its own does not compute it, and that was a defect, not a
> shorthand.** B4 #1 lives on the held-out 50 — the only half both annotators labelled —
> and C5.4's exclusion correctly drops every held-out step from the default run, so the
> command this file used to name reported *NOT COMPUTABLE* with both passes on disk.
> `--iaa` widens **only** the set human-vs-human reads: the classifier join stays on the
> dev set, `classifier_kappa_heldout` stays null, and no freeze is required, because
> human-vs-human touches no classifier output. `--iaa` and `--final` together are refused.

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

## What the number does and does not support

| | behavior | soundness |
| --- | --- | --- |
| **Cohen's κ** | **0.867** | **0.935** |
| 95% CI (bootstrap-2000) | **[0.495, 1.000]** | [0.766, 1.000] |
| Raw agreement | 0.98 (49/50) | 0.98 (49/50) |
| Majority-class baseline | 0.92 | 0.82 |
| Disagreements | **1** | **1** |

**B4 #1 passes on the point estimate, so C5.3's revision round is not triggered.** Two
people working from the same written rubric, with no discussion, reproduced 98 of 100 label
decisions. That is the thing this criterion exists to establish, and it is established: the
rubric is not one person's private reading.

### The caveat that belongs next to the number, not underneath it

**The behavior CI's lower bound is 0.495 — below the 0.70 bar it just cleared.** That is not
noise to be waved off; it is what a κ means on a sample this lopsided. The held-out 50 is
**46 `linear` out of 50**, a 0.92 majority-class baseline, and **27 of the 50 steps come from
`mb-08` alone** — 15 of them the *same sentence*, the degenerate repetition loop, rotating
its prefix. The entire discriminative content of the behavior κ is **four non-linear steps**.

So, precisely:

- **What the 0.867 supports:** a cold reader applying the written rubric to *this* corpus
  reaches the same call as its author almost always, and the two disagreements are principled
  rather than careless — both annotators wrote notes explaining their reading.
- **What it does not support:** that the rubric resolves its hard cases. The draw barely
  exercised them. [`adjudication-queue.md`](adjudication-queue.md) holds **14 open rubric
  questions**; this pass put a second reader in front of only a handful of them. A κ of 0.867
  on a draw that is half one repeated sentence is **agreement about a degenerate loop**, and
  it should be published with its n, its CI and its composition, never as a bare figure.
- **What it says about the sampling frame, which is a finding in its own right:** the held-out
  half of the random-90 is not a good instrument for measuring rubric agreement. That is worth
  knowing *before* M2-17 computes the published classifier κ on the same 50 steps.

### The two disagreements — the adjudication agenda

Both fall on questions [`adjudication-queue.md`](adjudication-queue.md) had already raised,
and **one of them the queue named in advance, by step id, as "the question most likely to be
decided against v1."** It was.

**1 · `direct:direct-mb-06-root-llm-0:1` — behavior.** amit `verification` · ankit
`backtracking`. The step re-runs a multiplication the previous step botched, by a different
decomposition.

- amit: §3.1's type case — a re-run of earlier work rather than new work.
- ankit: *"Both backtracking and verification apply … Precedence (backtracking > verification)
  settles it."*
- **This is queue question B2, and it is a precedence question, not a judgement gap.** Both
  readings are defensible from the text as written, which means **the rubric is genuinely
  ambiguous here** — the best possible kind of disagreement to find, because it is fixable in
  one sentence.

**2 · `thinking:thinking-mb-03-root-llm-0:0` — soundness.** amit `unverifiable` · ankit
`sound`. The step expands *RGB* into red, green, blue, where **the prompt itself supplies the
acronym**.

- amit labelled `unverifiable` *for consistency with the pass*, and wrote at the time: *"this
  is the sharpest example yet of why v2 must rule on common knowledge."*
- ankit, cold: *"the prompt supplies the acronym RGB, so the expansion is checkable from the
  problem statement. Rubric does not cover common-knowledge facts the prompt itself supplies."*
- **This is queue question A2**, which was logged with this exact step named and this exact
  outcome predicted. An independent reader, given nothing but the rubric, decided it the way
  the queue guessed a second reader would. **That is the adjudication queue working as
  designed** — a question raised before the measurement, and answered by it.

> **Neither is adjudicated here, and that is deliberate.** M2-2's card says *adjudicate every
> disagreement **by discussion***. Two people disagreeing is the input to that conversation,
> not a thing one of them settles alone — and settling A2 unilaterally would be the author of
> the rubric overruling the only independent reading it has ever had. The adjudicated labels
> become ground truth and each adjudication is appended to `rubric.md` as a hard case; until
> the session happens, **v1's labels stand and M2-2 is not closed.**

## If κ < 0.70

C5.3 permits **one revision round only**: revise the rubric, re-label the 50, recompute.
That is +1.5 h Lead and a **second ask of the annotator**, so warn them at booking that it
may be needed.

If the second round is still below 0.70: **stop.** Publish the achieved κ and downgrade the
claim on the calibration page from *"reliable"* to *"indicative, with human agreement at
κ = X"*. **Do not take a third round.** That is B0 Condition #5's own logic, and a third
round is the expired time box wearing a new costume.
