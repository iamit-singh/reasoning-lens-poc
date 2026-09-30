# Literature Survey Part A — review report (U3's substitute)

| | |
| --- | --- |
| **Task** | The substitute offered by [amendment 002 §5](../../plan-amendment-002-no-human-capacity.md) for **U3** |
| **Checklist row** | **C15.1 #10** — *"Literature Survey Part A finalised and reviewed"* · ship-blocking, **"Produced by" is an em dash** |
| **Verdict** | **U3 DOES NOT CLOSE.** A sign-off is a person putting their name to a claim. This is a review report; nobody has signed anything |
| **Run** | 18 Sep 2026 (W6), against [`lit-survey.md`](../../lit-survey.md) §§A1–A9 |
| **Headline** | Part A is sound and its structure holds up. **Its two forward-looking judgements were both falsified by the PoC it recommended** — and nothing in Part A has been updated to say so |

---

## What this is

§1.3.1 named C15.1 #10 as *"a ship-blocking row that no task in any month, in any of the
three breakdowns, owns"*, and said it *"fails only by being forgotten, which is exactly how
it will fail."* U3 was raised to find it an owner. No owner was found.

Amendment 002 §5 offers a **review report** instead — *"claims checked against cited
sources, gaps listed"* — and states what it is not: **"Not a sign-off."** The distinction is
not pedantry. #10 asks for accountability, not a document: somebody with a name accepting
that Part A is fit to ship alongside the PoC. Reading it carefully produces a better
document and **still leaves the row open**.

### Two limits on this review, stated up front

1. **No source was fetched.** This machine has no network access for the purpose, so no
   arXiv ID was resolved, no abstract was read, and no claim was checked *against the paper
   it cites*. What I could do is check each citation against what I already know of the
   literature, and flag the ones I am not confident about. That is a weaker check than #10
   implies and it is labelled as such throughout.
2. **The valuable check is the one nobody else was positioned to run**, and it is not a
   citation check at all: **Part A's claims against the PoC's own measured results.** Part A
   was written in W0 and has not been revisited since; three months of measurement now exist
   to test it against. That is §2 below, and it is where the findings are.

---

## 1 · Citations — what could and could not be verified

Twelve of the fourteen rows in A8 match papers I can identify with high confidence from
title, authors, year and arXiv ID together. **None was opened.**

| # | Citation | Check |
| - | --- | --- |
| 1 | `2201.11903` Wei et al., Chain-of-Thought | ✅ consistent on all four fields |
| 2 | `2210.03629` Yao et al., ReAct | ✅ |
| 3 | `2305.10601` Yao et al., Tree of Thoughts | ✅ |
| 4 | `2305.20050` Lightman et al., Let's Verify Step by Step | ✅ |
| 5 | `2305.04388` Turpin et al., LMs Don't Always Say What They Think | ✅ |
| 6 | `2501.12948` DeepSeek-R1 | ✅ |
| 7 | `2501.19393` Muennighoff et al., s1 | ✅ |
| 8 | `2503.01307` Gandhi et al., Cognitive Behaviors | ✅ — and see §2.3, because this one is load-bearing for the build |
| 9 | Chen et al., Anthropic, *Reasoning Models Don't Always Say What They Think* | ✅ as a work; **no stable identifier given** — a blog/alignment-science post cited by title only. See below |
| 10 | `2507.11473` Korbak et al., CoT Monitorability | ✅ |
| 11 | `2510.27378` Meek et al., Measuring CoT Monitorability | ⚠️ **lower confidence.** Plausible in every field; I cannot place this one from memory with the confidence I can the others. **The single row most worth a reviewer's minute** |
| 12 | transformer-circuits.pub, On the Biology of a Large Language Model | ✅ as a work; URL is a site root, not a document |
| 13 | Shojaee et al., Apple, The Illusion of Thinking | ✅ — and the *"+ published rebuttals"* parenthetical is the right way to cite a contested result |
| 14 | `2505.11831` ARC-AGI-2 | ✅ |

**Two things a real reviewer should push on:**

- **Rows 9 and 12 cite works without resolvable identifiers** — a title and a site root. Row
  9 is not a minor citation: it carries A9.1's second key takeaway (*"the reasoning trace is
  a claim, not a log"*), which is the intellectual foundation of the PoC's faithfulness
  panel. A ship-blocking survey should give it a URL that resolves to the document.
- **A8 #14 contains a live number** — *"frontier <1% on ARC-AGI-3 interactive tasks"*. A
  moving figure in a survey ages into a false statement without anyone editing it. It needs
  an as-of date, which is the same discipline this project applies to every number it
  publishes itself (*"an uptime figure without a window is the same defect as a percentage
  without an n"*, §1.3.1).

**Unverifiable and worth naming:** A9.2's claim that **"nobody has assembled them into one
usable pipeline over standard agent traces"** is the novelty claim the whole PoC rests on,
and it is an assertion about the absence of prior work — the hardest kind to support and the
one most likely to be wrong. It carries no citation. I cannot check it offline, and a
sign-off should not accept it without someone having looked recently.

---

## 2 · Part A against the PoC's measurements — the findings

This is the part of the review that could not have been done in W0, and it is where Part A
has actually gone out of date.

### 2.1 A9.3's "Biggest risk" fired, and its "High" confidence was wrong on the axis that mattered

A9.3 names the risk exactly right:

> **Biggest risk:** *Reliability of LLM-based step classification/judging — noisy labels
> would undermine the "measurement" claim.* **Mitigated by** using the published
> Gandhi-taxonomy prompting approach, calibrating on a small hand-labeled set, and scoping
> v1 to well-posed math/logic/agent tasks.
>
> **Confidence level: High** — *every component is individually proven in the literature
> with open code; the novelty (and the value) is the integration and presentation.*

**All three mitigations were applied in full. The risk fired anyway.**

| What A9.3 predicted | What was measured |
| --- | --- |
| Step classification reliable enough to support a measurement claim | **Held-out behavior κ 0.550** [−0.017, 1.000], n = 50 — **below B4 #2's 0.60 bar**, and 0.401 against the second annotator, which C1.3 scores as G2-C |
| Judging reliable enough to publish | **Judge precision 0.643** [0.388, 0.837], n = 14 — **below B4 #4's 0.75 bar** |
| Calibration on a hand-labelled set as the mitigation | Calibration **detected** the unreliability. It did not prevent it |

That last row is the finding, and it is not a criticism of the plan — it is the distinction
A9.3 does not draw. **Calibration is an instrument, not a mitigation.** It converts an
unknown reliability into a known one; it cannot make an unreliable classifier reliable. The
PoC's genuine achievement is that it *published the numbers that show its own instrument
missing its bars* — but A9.3 promised something different, and "High" confidence was
recorded against a risk whose stated mitigation could not have discharged it.

> **This does not mean Part A should be rewritten to look prescient.** It means a
> ship-blocking survey that recommended this PoC should carry one paragraph saying which of
> its forward-looking judgements survived contact with the measurements. Right now it reads
> as though nothing has been tested.

### 2.2 The survey's headline faithfulness claim did not reproduce on the model the PoC ran

A9.1's second key takeaway is stated as settled:

> **The reasoning trace is a claim, not a log.** *Faithfulness research (cue tests,
> mechanistic tracing) shows stated reasoning frequently omits the real drivers of an
> answer; any client-facing "explainability" story built on raw CoT display alone is
> technically indefensible.*

The PoC ran the cue test — the Turpin/Chen method A8 rows 5 and 9 describe — and measured
**0 of 48 trials flipped**, across all four cue types and both problem regimes
(`faithfulness/panel.json`, ADR-009).

**This is not a contradiction and must not be written up as one.** The published work
measures frontier reasoning models and reports *hint-verbalization rates*; the PoC measured
*answer flips* on `gpt-oss:20b` at one pin, n = 48, and a model that never changes its
answer for a cue cannot produce an unfaithful-about-the-cue trace. Different models,
different quantity.

**What it does mean** is that Part A states as an established general property something the
PoC could not observe on its own subject, and Part A does not say so anywhere. A reader
going from the survey to the demo meets a faithfulness panel publishing a **negative
result** immediately after being told the phenomenon is pervasive and the panel is *"the
guaranteed wow moment"* (B6.3). The demo handles this honestly — the panel leads with its
denominator and its caveat. **The survey is the document that has not caught up.**

### 2.3 The taxonomy Part A calls "the backbone" was nearly degenerate on this corpus

A8 #8 describes the Gandhi et al. behavior taxonomy — verification, backtracking, subgoal
setting, backward chaining — as *"the backbone of this PoC's classifier"*, and it is:
`rubric.md` and the classifier prompt share it byte-for-byte, enforced by
`make rubric-drift` on every PR.

What the corpus turned out to contain:

- **`backward_chaining`: absent from the held-out 50 entirely.**
- **`backtracking`: ~2.0%** (ADR-010, after the correction from an initially measured zero).
- The held-out draw is **46 of 50 `linear`**, giving a majority-class baseline of **0.92**,
  and **four non-`linear` steps carry the entire behavior κ**.

So the four-way taxonomy that motivates the classifier is, on well-posed math and logic
items, **a one-class problem with noise**. That is a real and publishable finding about
*where these behaviors appear* — and it lands directly on A9.3's third mitigation, *"scoping
v1 to well-posed math/logic/agent tasks"*, which is the decision that produced the
degenerate distribution. The mitigation chosen to reduce noise removed the phenomenon.

A reviewer signing off Part A should know that the survey's recommended scope and its
recommended taxonomy were **in tension**, and that the PoC discovered it by measurement.

### 2.4 Where Part A was right, and it is the important half

- **A9.2 (1) — "no trace-native reasoning analytics"** — the PoC built one end to end
  (OTEL span tree → `ReasoningReport`), and the gap was real: nothing existing was reusable.
- **A9.2 (3) — "process evaluation is unreliable at the edges"** — **this is the single
  best-supported claim in Part A.** Judge precision 0.643 and held-out κ 0.550 are exactly
  what A9.2 predicted, measured on this project's own instrument. Part A named the field's
  weak point and then the PoC landed on it.
- **A1.2's commercial framing** and A9.1's *"transparency is a closing window"* are
  unaffected by anything measured here and read as well now as in W0.

> The pattern across §§2.1–2.3 is consistent and worth stating plainly: **Part A's
> description of the field held up; Part A's predictions about this PoC did not.** That is a
> normal and honourable outcome for a survey, and it is only a defect because the document
> still presents the predictions as current.

---

## 3 · What a sign-off should require before ticking C15.1 #10

Five items. None is a rewrite; the largest is a paragraph.

| # | Change | Cost |
| - | --- | --- |
| 1 | **An "as measured" note in A9.3** recording that the named biggest risk fired, with the two numbers, and that calibration detected rather than prevented it | 1 paragraph |
| 2 | **A one-line qualifier on A9.1's faithfulness takeaway** — that the PoC's own cue test returned 0 of 48 on a 20B open-weight model, so the claim is about frontier LRMs and is not general | 1 sentence |
| 3 | **A note on A8 #8** that the taxonomy was measured near-degenerate on well-posed math/logic, with the majority-class baseline of 0.92 | 1 sentence |
| 4 | **Resolvable identifiers for rows 9 and 12**, and an as-of date on row 14's live ARC figure | minutes |
| 5 | **Someone reads row 11** (`2510.27378`) and confirms it, and looks hard at A9.2's uncited "nobody has assembled them" novelty claim | minutes |

---

## What this does to U3 and C15.1 #10

**The row stays open, with the same em dash where the owner should be.**

Amendment 002 §2 is right that a sign-off is *"a person putting their name to a claim"*, and
producing a better document does not produce a person. What has changed is that the row is
no longer *unexamined*: whoever eventually owns it has a list of five concrete items rather
than an instruction to read 650 lines and form a view.

**The honest summary for the G3 checklist:** Part A is a competent survey whose description
of the field held up for three months of measurement, whose **two forward-looking
judgements were both falsified by the PoC it recommended**, and which has not been updated
to record either. It ships as-is unless someone owns it. **It fails only by being
forgotten** — §1.3.1 said so in W0, and that is still the live risk.

## Related

- [`findings.md`](findings.md) · [`g2-measurement-report.md`](g2-measurement-report.md) — the measurements §2 checks against
- [`decisions/ADR-009-cue-injection-does-not-reproduce.md`](decisions/ADR-009-cue-injection-does-not-reproduce.md) · [`decisions/ADR-010-the-taxonomy-barely-populates.md`](decisions/ADR-010-the-taxonomy-barely-populates.md)
