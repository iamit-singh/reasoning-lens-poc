# Heuristic walkthrough review — E12's substitute

| | |
| --- | --- |
| **Task** | The substitute offered by [amendment 002 §5](../../plan-amendment-002-no-human-capacity.md) for **M3-5b** |
| **Criterion** | G3 **E12** / **B4 #9** — *5 of 5 testers complete unaided; ≥ 4 of 5 state "fluent ≠ sound"* |
| **Verdict** | **E12 DOES NOT CLOSE, AND CANNOT.** Zero naive readers were involved. This is a review, not a measurement |
| **Run** | 18 Sep 2026 (W6), against the shipping export (`make fe-build-measured`, 21 pages) |
| **Amended** | **23 Sep 2026 — all four queued changes applied.** Findings 1–4 describe the page *as it was on 18 Sep*; see [What changed on 23 Sep](#what-changed-on-23-sep-and-what-it-cost) |
| **Headline** | **The arrival screen argues a different thesis from the one B4 #9 measures**, and the best evidence for the right thesis is on it, unlabelled |

---

## What this is, stated before anything else

Amendment 002 §5 offers *"a heuristic walkthrough review — the eight surfaces read against
the facilitator script's questions, every point of likely confusion written down"*, and puts
the boundary in the same sentence: **"Not a user test. Zero naive readers."**

§2 is blunter about why no substitution exists here: E12 measures whether the demo
*communicates to people who have never seen it*, and **a reader who can read the source is
not a naive viewer.** I have read the source. I know what `unparsed` means, I know which
arm is which, and I know what the page is trying to say — which is precisely the knowledge
B4 #9 is designed to run without.

So this document cannot tell you whether five people would state the insight. What it can
do is name places where the page **relies on knowledge a naive reader does not have**, which
is a structural property of the artifact and readable without being naive. Those are below.
Everything here is a hypothesis about confusion, not an observation of it.

**The measurement is still owed, and B4 #9 is still lost** (amendment 002 §6). U1 is still
the tech lead's.

---

## The method

The facilitator script hands a tester the landing page and exactly one question:

> **What is this page telling you about how this AI reasons?**

…then says nothing. The debrief asks three more:

1. In your own words, what is this page showing?
2. Did anything surprise you?
3. Was there anything you didn't trust, or wanted to check?

So the review question is not *"is this page good"*. It is: **reading only what is on the
screen, in the order a reader meets it, what answer does question 1 most plausibly get?**

I read the exported HTML with every `<script>` stripped — the same view `make
fe-export-check` asserts, and the view a reader gets before hydration.

---

## Finding 1 — the landing page never says the word

`sound`, `unsound` and `fluent` appear **zero times** on the arrival screen.

```
unsound      0        fluent       0        wrong        1
sound        0        plausib      0        correct      1
```

B4 #9 asks whether ≥ 4 of 5 testers state that **fluent ≠ sound**. The concept is not
absent from the product — it is the spine of the item pages, the flagged-step panel and the
calibration page. It is absent from **the one screen every tester is guaranteed to see**,
and it is the screen they are asked the question about.

This is not an argument for pasting the thesis onto the homepage as a slogan; a page that
*tells* the reader the insight has not measured whether the reader *reaches* it, and B4 #9
is specifically about reaching it unprompted. It is an argument that the arrival screen
currently gives them nothing to reach it *with*.

## Finding 2 — the featured contrast teaches a different lesson, and teaches it well

The featured comparison — the largest thing on the page, pre-rendered at build time, the
first thing read — says:

> **ReAct + tools answered it. Direct did not.**
>
> *Same model, same problem, three strategies. One of them looked the fact up; the others
> tried to recall it. The lens shows which, and what it cost.*

That is a clear, well-written argument, and it is an argument about **tool access**. A
tester asked *"what is this page telling you about how this AI reasons?"* and answering
**"that it does better when it can look things up"** has read the page correctly, answered
the question sensibly, and **missed B4 #9 entirely.**

This is the most consequential thing in this review. The featured item is not a neutral
sample — §2.3 Hazard 2 made it a build-time committed choice precisely because it is the
arrival screen — and the choice currently spends the demo's highest-value real estate on
the tool-use story.

> **Worth being careful here.** The tool-use contrast is a genuine measured result and it is
> the cleanest one in the corpus. This finding is not "the featured item is wrong". It is
> that **the surface with the most attention is arguing the thesis B4 #9 does not measure**,
> and the criterion was written knowing which thesis mattered.

## Finding 3 — the best fluent-≠-sound artifact on the site is sitting on the arrival screen, labelled as a parse error

In the same featured block, the extended-thinking arm reads:

| | Direct | **Extended thinking** | ReAct + tools |
| --- | --- | --- | --- |
| verdict | wrong | **`unparsed`** | correct |
| answer | *Fairhaven has roughly 10,800 more…* | **— no answer —** | *…**31,650** more people…* |
| reasoning tokens | 74 | **3,966** | 80 |
| steps | 3 | **141** | 8 |
| trace | full | **partial** | full |

**That row is the entire thesis of the project.** The arm that reasoned fifty times harder
than the others — 3,966 reasoning tokens, 141 steps, the single most elaborate trace in the
corpus — produced **nothing**. The most fluent output is the one with no answer in it.

And it is rendered as **`unparsed`**, which is the tool's word for its own parser, next to
`partial`, which is the tool's word for its own capture. A naive reader has two readings
available:

- *"the model thought for ages and came out with nothing"* — the finding, and
- *"the website failed to read that one"* — a bug in the demo.

Nothing on the screen chooses between them, and the second is the more natural reading of
the word `unparsed`. **The demo's strongest piece of evidence for its own claim is
presented in a vocabulary that invites the reader to discount it as a defect.**

This is the cheapest fix on the list and the highest-value one: it is a copy change on a
committed featured report, and it needs no new measurement.

## Finding 4 — the subtitle describes the instrument, not the finding

> *Three strategy arms over one problem bank, segmented into steps, each step classified and
> judged — with the agreement numbers published beside every claim.*

Every word is accurate and the last clause is the project's integrity in one line. But as an
answer to debrief question 1 — *"in your own words, what is this page showing?"* — it hands
the reader a description of **what was built**, and a tester who paraphrases it has
described a pipeline rather than a result.

"Strategy arms", "problem bank", "segmented into steps" and "classified and judged" are four
pieces of internal vocabulary in a 30-word sentence, and the recruiting rule says testers
are **not** from this project.

## Finding 5 — where the page is very good, which matters for reading the rest of this

Three surfaces are, on this reading, unusually strong, and the review would be dishonest
without saying so at the same volume:

- **The calibration page leads with its own shortfall.** *"What this instrument does not do
  well — measured, published, and put first deliberately."* Then κ 0.55 against a 0.92
  majority-class baseline, with the explanation that *"a high raw agreement and a low kappa
  are the same fact seen twice"*. A reader who gets here is being told the headline missed
  its bar before they are told anything else. This is FE-11's G2-B delta and it works.
- **"Treat every flagged step on this site as a prompt to look, not as a finding."** That is
  judge precision 0.64 converted into an instruction the reader can act on, which is the
  hard half of publishing a weak number.
- **"Consistency is not faithfulness."** The distinction most likely to be collapsed by a
  reader, named and separated explicitly.

These are the parts to protect. The findings above are about the **arrival screen**, and
they are about it specifically because nothing else is guaranteed to be read.

## Finding 6 — the route to the insight is opt-in

The arrival screen offers `Calibration & limitations →`, `Faithfulness →`, and 27 bank items.
The soundness verdicts, the flagged-step panel and the escalation state — where "fluent ≠
sound" is actually demonstrated on a step — live **inside an item page**, which a tester
reaches only by choosing one of 27 problems, most of which are arithmetic with no
interesting failure in them.

A tester who clicks `mb-02` (*"What is 17 multiplied by 4?"*) sees three arms agreeing on 68.
That is a correct demonstration of nothing in particular, and it is two clicks from the
question they were asked.

---

## The four cheapest changes, in the order I would make them

Ordered by value per unit of frontend time, which is the constraint §1.4 says is binding.

| # | Change | Why it is first/last |
| - | --- | --- |
| **1** | **Give the `unparsed` / `— no answer —` cell one sentence of plain framing** on the featured comparison — what happened, in the reader's language, not the parser's | Finding 3. Highest value on the page, a copy change, no new measurement, and it converts the strongest existing evidence from "looks like a bug" to "is the point" |
| **2** | **Add one plain-language line to the featured block's framing** that names what the three arms show about *effort vs. correctness*, alongside the tool story rather than instead of it | Finding 2. The tool contrast is real and should stay; the issue is that it is currently the only reading on offer |
| **3** | **Re-word the subtitle** to say what was found rather than what was built | Finding 4. One sentence |
| **4** | **Surface one or two items on arrival that are interesting**, rather than 27 in id order led by "what is the chemical symbol for potassium?" | Finding 6. More layout work than the others, hence last |

> **None of these is a measurement change**, none touches the frozen surface
> (`prompts/**`, `classify.py`, `judge.py`, `consistency.py`, `MODEL_PIN`), and none alters a
> published number. They are copy and ordering, which is what §2.3 Hazard 4 predicted B4 #9's
> failure modes would be — *"a tag legend nobody notices, a scoreboard whose verdict line
> buries the point"* — and it predicted correctly.

**They were not applied when this review was written (18 Sep).** Hazard 4's whole argument is
that these fixes should be driven by *what testers actually stumble on*, and the pilot exists
so the wording comes from the testers' own phrasing rather than the author's second guess —
`walkthrough-notes.md`: *"if a pilot tester states the insight in better words than the page
uses, those are the words the page should use."* Acting on my guesses would spend the pilot's
budget on changes nobody has evidence for, and would make the eventual sessions a test of my
speculation rather than of the design.

> ### ⚠️ All four were applied on 23 Sep. Read the next section before trusting the page above.
>
> The findings above describe the arrival screen **as it was on 18 Sep**. Four of them no
> longer hold, because they were acted on. What that did and did not buy is
> [below](#what-changed-on-23-sep-and-what-it-cost).

---

## What this does to E12

**Nothing. E12 is unmeasured and stays unmeasured.**

B4 #9 is the only one of the ten criteria that tests whether the demo *communicates*, and it
is lost outright (amendment 002 §6). The pre-decided action for exactly this case is the one
this project keeps taking: **publish the shortfall**, on the calibration page and in the G3
checklist, rather than lowering the criterion until something passes.

What this review adds is smaller and should not be mistaken for more:

- **A named, specific hypothesis about how B4 #9 would have failed** — not the generic "the
  copy might confuse someone", but *the arrival screen argues tool-access while the criterion
  measures fluent-≠-sound, and the best counter-example on the page is labelled `unparsed`*.
  That is falsifiable by two testers in twenty minutes.
- **A queue of four changes** the pilot could confirm or discard, so the booked session
  spends its time on evidence rather than on discovering the obvious.

> If the five sessions ever happen, **read this file afterwards, not before.** A facilitator
> who has read Finding 3 will hear the insight in a tester's hesitation whether it is there
> or not, and that would convert the one remaining human measurement in this project into a
> confirmation of its author's guess — which is the failure mode `walkthrough-notes.md`
> already refuses in a different costume.

---

## What changed on 23 Sep, and what it cost

**All four queued changes are applied.** The reason for holding them was that the pilot would
supply better wording than my guesses; the reason for releasing them is that **the pilot has
no date and the demo is being shown in the meantime.** Withholding a known structural fix to
preserve a diagnostic opportunity is right while the session is coming, and becomes simply
shipping a worse page once it is not.

**This is a trade, not a free win, and the losing side is named here rather than left out:**

| Given up | Gained |
| --- | --- |
| The chance to learn *how* naive readers fail on the 18 Sep wording. Those four findings are now untestable — the page they describe is gone | An arrival screen that gives a reader something to reach the insight *with*, instead of one that argues tool access and labels its best counter-example `unparsed` |

**The four changes, and where they live:**

| # | Change | Where |
| - | --- | --- |
| 1 | The no-answer cell gets one sentence of plain framing, **derived** — "the model never stated an answer, it ran 141 steps and spent 3,966 reasoning tokens" vs. "gave an answer this pipeline could not read". The two are different claims and only the first is a result | `components/ArmPanes.jsx` → `NoAnswerNote` |
| 2 | A second reading beside the tool story: *the arm that reasoned hardest is not the arm that got it right*. Renders **only when that is true of the arms on screen**, and disappears rather than becoming false if the featured item changes | `page.jsx` → `effortNote()` |
| 3 | The subtitle says what was found, not what was built. Four pieces of internal vocabulary removed | `layout.jsx` |
| 4 | Two derived "start here" doors above the 27-item list — ranked by strength of demonstration, first rank being *a correct arm carrying a step the judge called `unsound`* | `lib/reports.js` → `startHere()` |

### Three things worth being uncomfortable about

**1. These are unvalidated hypotheses, and they can be wrong in the same direction as the
page they replaced.** Nothing here has been read by a naive reader either. The argument for
them is structural — the words the criterion measures were absent from the one screen every
reader sees, and the best counter-example was labelled in the tool's own vocabulary — but
*structurally defensible* is a weaker claim than *measured*, and this document should not be
read as having closed the gap it opened.

**2. Change #3 deliberately stops short of stating the insight.** A subtitle reading "fluent
is not the same as sound" would put the scored sentence on the page and make B4 #9
unmeasurable by construction — a tester could read it back. If the sessions ever happen they
must still measure a reader *reaching* it. Giving them something to reach it with is the fix;
giving them the sentence would be marking our own exam.

**3. The 18 Sep wording is recoverable** — it is in git at `0fb1a67`, and the findings above
quote it verbatim. If a facilitator ever wants the original as a control arm, it exists.

> **If the five sessions are ever booked, the record must say they ran against the 23 Sep
> page, not this review's subject.** Otherwise a future reader will match findings 1–4
> against a screen that no longer exists and conclude the testers contradicted them.

### What this does to E12

**Still nothing. E12 is unmeasured and stays unmeasured**, exactly as the section above says.
Zero naive readers have seen either version. Applying a fix does not measure whether it
worked, and B4 #9 remains lost (amendment 002 §6) with the shortfall published rather than
the criterion lowered.

## Related

- [`walkthrough-notes.md`](walkthrough-notes.md) — the protocol, the facilitator script, and the empty record
- [`runbook-cold-run.md`](runbook-cold-run.md) — E13's substitute, same shape, same boundary
- [amendment 002 §§2, 5, 6](../../plan-amendment-002-no-human-capacity.md) — why no substitution closes this
