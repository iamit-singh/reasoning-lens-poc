# Tester walkthrough — protocol and notes (M3-5b · B4 #9 · G3 E12)

> ## ⛔ NO SESSIONS HAVE BEEN RUN. Every result cell below is empty on purpose.
>
> This is the **protocol and the empty record**, written in advance so that booking people
> is the only remaining step. **There is no measurement here yet.** If this file ever shows
> a score, it is because somebody ran the sessions and typed the result in — not because
> the file was written optimistically.
>
> Writing the sheet before the sessions is deliberate: deciding what counts as a pass
> *after* watching five people struggle is how a communication test becomes a post-hoc
> justification.

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
> 2. **The 18 Sep wording is still in git at `0fb1a67`** if anyone wants the original as a
>    control arm. Nobody has read either version cold.

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

## The record — fill in after each session

| # | Date | Tester (role) | Build (commit) | Mode | Completed unaided? | Stated the insight? | Time |
| - | ---- | ------------- | -------------- | ---- | ------------------ | ------------------- | ---- |
| Pilot 1 | | | | | | | |
| Pilot 2 | | | | | | | |
| 1 | | | | | | | |
| 2 | | | | | | | |
| 3 | | | | | | | |
| 4 | | | | | | | |
| 5 | | | | | | | |

**Result:** *(not yet measured)* — completion _/5 · insight _/5

### Verbatim quotes

> *(One block per tester. Their words, not a paraphrase — a paraphrase is the facilitator's
> reading of what they meant, which is the thing being tested.)*

### Questions asked during a run

> *(Each one is a place the page failed to explain itself. These are the copy backlog.)*

### Hesitations — where they paused, re-read, or scrolled back

> *(Hesitations are cheaper to fix than failures and usually predict them.)*

## If fewer than 4 of 5 state the insight

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

## Related

- [`g3-ship-checklist.md`](g3-ship-checklist.md) — E12 is this, and it is one of the three
  open rows
- [`runbook.md`](runbook.md) — E13's peer dry-run is the other human-dependent row, and it
  needs a different person than these five
