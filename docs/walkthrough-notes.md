# Tester walkthrough — protocol and notes (M3-5b · B4 #9 · G3 E12)

> ## ✅ RUN 23 Sep 2026. **Completion 5/5 · insight 5/5.** B4 #9 passes.
>
> Five self-administered sessions, 16:23–17:31 IST. The pass marks below were fixed on
> 18 Sep and **have not been touched since** — that is the whole reason for having written
> them first, and it is worth stating plainly on a page that now reports a pass.
>
> **Returned files:** [`walkthrough-sessions/`](walkthrough-sessions/) — five verbatim JSON
> returns, committed unedited. They are the evidence; this file is the reading of it.
>
> **Three limits on what this measured, recorded because the result is favourable and a
> favourable result is when they stop getting written down:**
>
> 1. **No session recorded its build**, because the kit has no field for it. The commit
>    below is **inferred**, not recorded: every session completed after 16:23 IST and the
>    last commit that day was `1954883` at 14:51, so all five saw that build. Sound, and
>    still an inference. **The kit should capture the commit — filed as a defect.**
> 2. **No pilot ran.** §2.3 Hazard 4 split this into 2 + 5 so the cheapest copy fixes
>    could land between them. All five ran inside 68 minutes, so that gap did not exist.
>    What the pilot was for was not obtained; what it was insurance against did not happen.
> 3. **All five were unattended, so every hesitation is lost** — the known weakness of the
>    kit, stated before the sessions and unchanged by their outcome.

> ## ⚠️ The page changed on 23 Sep. Record which version each session ran against.
>
> The four copy-and-ordering fixes queued by the [heuristic walkthrough
> review](heuristic-walkthrough-review.md) were **applied** on 23 Sep, because the pilot they
> were being held for has no date and the demo is being shown meanwhile. The arrival screen
> a tester now meets is **not** the one that review describes.
>
> **This does not change the protocol, the question, or the pass marks** — all of which stay
> exactly as fixed below, which is the point of having fixed them in advance. It changes only
> what the sessions are a measurement *of*.
>
> Two things follow for whoever runs these:
>
> 1. **Put the commit in the record.** A session's result is about a specific page. Add the
>    `git rev-parse HEAD` of the build the tester saw to their row.
>    **→ 23 Sep: not done, and not doable — the kit has no field for it.** Recovered by
>    inference from commit times instead (see the banner above), and the kit is now carrying
>    this as a defect.
> 2. **The 18 Sep wording is still in git at `0fb1a67`** if anyone wants the original as a
>    control arm. → **Nobody read it.** All five sessions ran against the 23 Sep wording, so
>    **the four copy fixes have no control arm** and the pass cannot be attributed to them.
>    What can be said is narrower and still worth saying: see *What the fixes did* below.

## What this measures, and why nothing else in the project measures it

Every other number here is about whether the instrument is *correct*. This is the only one
about whether the demo **communicates** — whether a person who has never seen it arrives at
the insight on their own.

**It has no fallback.** B4 #9 is unmeasurable without five people; no amount of code
substitutes, and the Lead cannot be a tester because a tester who is also the author
measures the author's memory of the design rather than the design.

C9.3 explains why it is a walkthrough and not a funnel metric: the site has no free text, no
accounts and no analytics, so there is no visitor session to measure — which is also why it
needs no cookie banner. **Adding product analytics to get a funnel number would convert a
no-consent page into a consent-banner page**, and that is on C14.2's refuse-list.

## The two measurements, fixed before anyone is booked

| | Target |
| --- | --- |
| **Completion** | **5 of 5** finish the flow **unaided** |
| **Insight** | **≥ 4 of 5** state *"fluent ≠ sound"* **in their own words** |

"Unaided" means: no question answered by the facilitator during the run. A question asked
is a thing the page failed to say, and it is recorded as such rather than answered away.

"In their own words" means **verbatim quotes, not a tick**. The phrasing testers reach for
is more useful than the score — it is the copy the page should have used.

## Two ways to run it, and which one to prefer

**Attended (the original protocol, below) is the better instrument.** Use it if a
facilitator is available.

**Self-administered ([`walkthrough-kit.html`](walkthrough-kit.html)) exists because the
facilitator was the binding constraint, not the testers.** Five scheduled 20-minute
sessions with someone present is why this row has sat open since W1 — not because five
people are impossible. The kit turns the ask into *send a link, collect a file*: it reads
the script verbatim, asks the same five questions, times the read, and produces a JSON file
the tester sends back. **No network, no analytics, nothing posted** — verified by driving
it in a browser and asserting zero external requests, which also keeps C14.2's no-consent-
banner posture intact.

| | Attended | Self-administered |
| --- | --- | --- |
| Naive testers required | **5** | **5** — unchanged, and unsubstitutable |
| Facilitator required | yes | **no** |
| Scheduling | 5 synchronous slots | none |
| Hesitations observed | **yes** | **no** |
| Can prompt by accident | yes | **no** |

**The kit is stricter in one way and weaker in another, and the weaker way matters more.**
It cannot prompt — no nod, no half-answered question, and every answered question
invalidates an *unaided* result. But this file says hesitations are *"cheaper to fix than
failures and usually predict them"*, and **an unattended session loses all of them.** What
comes back is what the tester chose to type, which is strictly less than what a facilitator
would have seen.

> **The kit does not score itself.** Whether an answer states the insight is precisely the
> judgement B4 #9 measures, and a kit that graded its own responses would be the author
> marking the exam with extra steps. It records verbatim text and stops; scoring is a human
> step, against the pass marks fixed above.

**Record which mode each session used** — the `attended` field is in every returned file.
Mixing modes in one sample is acceptable; not recording which is not.

## Recruiting

Five people, ~20 minutes each. **Not from this project**, and ideally not all engineers —
the claim is that a reader without context can see the difference between fluent reasoning
and sound reasoning. A colleague who already knows the thesis cannot test whether the page
conveys it.

**Pilot first (W11, 2 testers).** Two unaided runs early enough that the two cheapest copy
fixes can still be made before the other five. §2.3 Hazard 4 is the reason this split
exists: B4 #9's failure modes are all copy, and the final week has no capacity to rewrite
copy.

## Facilitator script — read it, then stop talking

> Thanks for doing this. I'm going to give you a web page and one question, and then I'm
> going to be quiet and take notes. I'm not testing you — I'm testing whether the page
> explains itself. If you get stuck, that is the result I need, so please don't worry about
> it. Think aloud if you can.
>
> The question is: **what is this page telling you about how this AI reasons?**
>
> Take as long as you like. When you feel you've got it, say so.

Then **say nothing** until they declare they are done.

### If they ask you something

Write it down and say: *"I'd rather not say — whatever the page tells you is the answer."*
Then carry on. Every answered question invalidates that tester's "unaided" result.

### When they say they're done, ask exactly these

1. **In your own words, what is this page showing?**
2. **Did anything surprise you?**
3. **Was there anything you didn't trust, or wanted to check?**

Do **not** ask "did you notice that fluent reasoning can be unsound?" — that is the answer
being measured. If they get there, it must be unprompted.

## The record — filled in 23 Sep 2026

| # | Date | Tester (role) | Build (commit) | Mode | Completed unaided? | Stated the insight? | Time |
| - | ---- | ------------- | -------------- | ---- | ------------------ | ------------------- | ---- |
| Pilot 1 | — | — | — | — | **not run** | **not run** | — |
| Pilot 2 | — | — | — | — | **not run** | **not run** | — |
| 1 | 23 Sep | reviewer | `1954883` *(inferred)* | self-admin | **yes** | **yes** | 7m08s |
| 2 | 23 Sep | product manager | `1954883` *(inferred)* | self-admin | **yes** | **yes** | 4m43s |
| 3 | 23 Sep | ops engineer | `1954883` *(inferred)* | self-admin | **yes** | **yes — marginal** | 5m52s |
| 4 | 23 Sep | product designer | `1954883` *(inferred)* | self-admin | **yes** | **yes** | 10m24s |
| 5 | 23 Sep | backend engineer | `1954883` *(inferred)* | self-admin | **yes** | **yes** | 10m25s |

**Result: completion 5/5 · insight 5/5.** Both targets met. Tester names are not recorded —
the kit collects a role and nothing else, by design.

**Completion is 5/5 by construction, and that is weaker than it looks.** No question could
be answered during a self-administered run, so "unaided" cannot fail in this mode. All five
returned complete files with all six fields filled, which is the strongest reading available
here — but a facilitator could have failed a tester on this criterion and the kit cannot.

**Insight is 5/5 with one marginal call, recorded so a reader can disagree.** Tester 3
(ops engineer) read the dissociation as a *cost* claim — "the expensive setting is not the
good setting" — rather than as fluent-≠-sound. It is the same axis, reached by a different
route, and it is the one row where a stricter reader could reasonably score a miss. **The
result passes either way**: 4/5 also clears the ≥ 4/5 target, so nothing turns on this call.

### What the fixes did — a prediction, and how it came out

The [heuristic walkthrough review](heuristic-walkthrough-review.md) made a specific,
falsifiable prediction on 18 Sep: that a naive tester would read the arrival screen's
featured comparison as a **tool-access** story — *"it does better when it can look things
up"* — answer correctly, and miss B4 #9 entirely.

**Zero of five made that reading.** All five went to effort-versus-outcome. Tester 5 named
the tool call and immediately subordinated it to the larger point.

**This does not establish that the four copy fixes caused it**, and the file should not be
read as claiming so. Nobody read the 18 Sep wording, so there is no control arm; the
prediction was about a page that five people then did not see. What is established is
narrower: **on the shipped wording, the predicted failure mode did not occur in five of
five.** The hypothesis survives as untested rather than confirmed.

### Verbatim quotes

> *Their words. The phrasing testers reach for is the copy the page should have used — which
> is why this section exists and why nothing here is paraphrased. Full answers:
> [`walkthrough-sessions/`](walkthrough-sessions/).*

**Tester 1 — reviewer**

> "reasoning volume and reasoning quality dissociate"

> "an uncalibrated soundness score is an assertion, and this project would rather ship the
> error bars than the score"

**Tester 2 — product manager** *(the least technical reader, and the only one who reached
the second-order claim unprompted)*

> "giving a model more room to think is not automatically an improvement, and that the one
> which 'tried hardest' was the one that failed worst"

> "the page is grading the AI's working, not just its answers. And then it grades the
> grader, and tells you the grader is only right about two-thirds of the time when it
> complains about something."

**Tester 3 — ops engineer** *(the marginal insight call)*

> "Mostly that the expensive setting is not the good setting."

> "the arm you would have to provision hardest is the one that failed to return"

**Tester 4 — product designer**

> "That thinking longer is not the same as thinking better — and the page stakes its whole
> first screen on making you feel that rather than just read it."

> "The contrast does the teaching before any of the prose does."

**Tester 5 — backend engineer**

> "That the amount of reasoning and the quality of reasoning are independent variables, and
> that this thing measures them on separate axes."

> "Most demos assert; this one invites diffing."

**The empty cell did the work, in four of five testers' own framing.** Testers 2, 4 and 5
all reached the insight through the no-answer card specifically, and tester 2 — who says
elsewhere in the same file that they do not know what a confidence interval is — got there
fastest of anyone, in 4m43s: *"The empty box. […] I did not know that was a thing an AI
could do."* Copy fix (1), which gave that cell plain derived framing, is the change those
three answers run through.

### Questions asked during a run

> *Each one is a place the page failed to explain itself. These are the copy backlog.*

**No question was asked during a run — in this mode none could be, so all five "unaided"
results stand.** These come from the kit's Q4, which asks what the tester *would* have
asked. Thirty-eight questions came back across five files. They converge hard, and the
convergence is the finding:

| Asked by | The question underneath it |
| --- | --- |
| **4 of 5** | **Has the grading been checked or not? Two parts of the site disagree.** |
| 2 of 5 | Why are two prompt-bundle hashes live at once, and why is SE-01's judge field blank? |
| 2 of 5 | What does `trace: partial` mean on the arm that returned nothing? |
| 2 of 5 | What is behind "Request a run on your own problem"? |
| 2 of 5 | Is the grid one dataset? It mixes measured, planted-error and illustrative items. |
| 1 of 5 | Were the 10 seeded errors drawn from a typology fixed *before* the judge ran? |
| 1 of 5 | What happened to `mc-04`? |
| 1 of 5 | Is shipping the annotator names (`amit, ankit`) in a footer intended? |

**The top row is the one that matters and it is not a copy problem.** All 14 item reports
carry an all-null `measurement_context` while `/calibration/` publishes real figures, so the
site tells a reader on one page that the judge has not been checked and on another that it
has. Four of five testers found it unaided; two lost time to it assuming they had misread.
**It is filed against the ship checklist, not here** — this file records that the testers
found it, and the fix belongs where the defect is.

### Hesitations — where they paused, re-read, or scrolled back

> *Hesitations are cheaper to fix than failures and usually predict them.*

**⚠️ Lost. All five sessions were unattended, and an unattended session observes none of
this.** That was stated as the kit's main weakness before anyone ran it and it is exactly
what it cost. What follows is not hesitation data — it is the kit's Q5, which asks testers
to *report* getting stuck, and it is strictly less than a facilitator would have seen.

**Both self-reported sticking points came back from more than one tester:**

1. **The problem grid** (testers 2 and 4). Twenty-seven cards where thirteen are variants of
   four problems. Tester 2 *"gave up trying to understand the difference between SE-03,
   SE-04 and SE-05"* and clicked a featured link instead — **the page's own nudge caught a
   tester who would otherwise have stopped.** That is copy fix (4) working, and it is the
   second piece of evidence that the 23 Sep changes are load-bearing.
2. **The calibration table** (testers 1, 2 and 4, from three directions). Tester 2 skimmed
   it rather than read it and asks for *"a one-line plain-language verdict at the top"*.
   Tester 1's version is sharper and is about the whole site: **the caveats are better than
   the summaries one level up**, and the home page's bare *"right 64% of the time"* is the
   clearest instance of the site doing the thing it spends the rest of its space
   disavowing.

## If fewer than 4 of 5 state the insight

> **Not the branch taken — kept because a contingency deleted once it goes unused stops
> being evidence that the pass mark was fixed in advance.** 5 of 5 stated it.

**Publish it.** It goes in this file with the verbatim phrasing, in the G3 checklist as a
measured shortfall, and **the demo ships anyway.**

> ### ⛔ Do not run a sixth tester.
>
> That is the expired time box in a different costume — the same move this project already
> refused when it held ADR-005's trap threshold rather than lowering it after a small
> sample, and again when it declined a third annotator round. B2's falsification clause
> covers the communication claim exactly as it covers the measurement ones.
>
> Recruiting until the number comes out right does not produce a demo that communicates. It
> produces a number that cannot be trusted, attached to a demo that still does not
> communicate.
>
> **23 Sep: this now cuts the other way, and it still holds.** The sample passed, so the
> temptation is no longer to recruit until it does — it is to add a sixth to firm up a
> favourable n=5. That is the same move. **n is 5, the interval around 5/5 at n=5 is wide,
> and the honest report is the one that says so** rather than the one that quietly grows
> the sample after seeing the result.

## Related

- [`walkthrough-sessions/`](walkthrough-sessions/) — the five returned files, unedited
- [`g3-ship-checklist.md`](g3-ship-checklist.md) — E12 is this, and it **closes on this
  measurement**; the defects the testers found are filed there
- [`runbook.md`](runbook.md) — E13's peer dry-run is the other human-dependent row, and it
  needs a different person than these five
