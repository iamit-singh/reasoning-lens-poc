# Month-3 unblock list — every row with a name, a date, and what happens if nobody answers

**M3-0's artifact.** §11 of the Month-3 breakdown lists seven asks and says *fire these in
the first session of W9*. This is that list, executed early and re-read at G3 — the same
reason [`g3-ship-checklist.md`](g3-ship-checklist.md) was run in W5 rather than W12.

> ## The short version
>
> **Two rows are dead**, killed by [ADR-003](decisions/ADR-003-hosting.md) along with the
> deployment they existed for. **Four are open and none of them has a default.** One is
> newly urgent.
>
> **And the row that actually blocks the most is not in §11 at all**: the 40 calibration
> labels. See the bottom of this file.

## The rows

| # | Ask | Owner | State |
| - | --- | --- | --- |
| **D3** | AWS account, region, IAM role, billing-alarm owner | Tech lead / IT | ⛔ **DEAD** |
| **D4** | DNS delegation for `demos.talentica.com` | IT / marketing | ⛔ **DEAD** |
| **U1** | **Five walkthrough testers booked** | Tech lead | 🚫 **OPEN — no default exists** |
| **U2** | **A peer named for the runbook dry-run** | Tech lead | 🚫 **OPEN — no default exists** |
| **U3** | **An owner for C15.1 #10 — lit-survey Part A sign-off** | Reviewer | 🚫 **OPEN — no owner at all** |
| **U4** | **C10.1 Option-2 contingency — released or not** | Tech lead + DM | ⚠️ **OPEN and now urgent** |
| **D6** | Langfuse cloud vs. self-host | Tech lead | 💤 **probably superseded — needs one sentence** |

---

### D3 · D4 — dead, and the plan's scariest row died with them

§11 marks D3 *"blocks M3-4"* and calls it the row where **"the critical path stops at a
task no amount of code advances."** That was true when Month 3 ended at a deployed service.

**ADR-003 deleted the deployment.** The demo runs from a laptop, so there is no AWS account
to name, no region to pick, no IAM role, no billing alarm, no hostname and no TLS
certificate. M3-4a and M3-4b are deleted scope; G3's E6 and E7 are deleted with them.

M1-3's DNS ticket was drafted in W1 and **correctly never filed** — 0.4 h sunk, and the
right 0.4 h to sink.

> **Nothing is owed to anyone on these two.** They are recorded as closed-by-decision rather
> than deleted silently, because a reviewer who remembers §11 will look for them.

### U1 — five walkthrough testers · **the hardest dependency left**

**No fallback. B4 #9 is unmeasurable without five people**, and it is the only criterion
that tests whether the demo *communicates* rather than whether it is correct.

§2.3 Hazard 4: trivially satisfiable in W9, **impossible in W12** — the failure modes are
all copy, and the last week has no capacity to rewrite copy.

**The protocol, facilitator script and empty results sheet are written**
([`walkthrough-notes.md`](walkthrough-notes.md)), with the pass mark fixed in advance so it
cannot be set after watching people struggle. **Booking is the only remaining step.**

Testers must not be from this project, and the Lead cannot be one: a tester who is also the
author measures the author's memory of the design.

### U2 — a peer for the runbook dry-run

Same class of dependency as Month 2's second annotator, and the same fix: **name a person.**
C15.1 #7 requires *another team member* to restart the service, roll it back and trip
`DEMO_MODE`, **working from the document alone**. The Lead watches and writes down every
hesitation.

A dry-run by the runbook's own author is a proofread. All six procedures were executed
before being written and **two failed on first run**, both recorded in the runbook — so the
document is honest, but it has still only ever been read by the person who wrote it.

### U3 — the owner nobody has ever named

**A ship-blocking checklist row with an em dash where the owner should be**, and it appears
in no month's work breakdown. §1.3.1 flagged it; it is still true.

> It fails only by being forgotten, which is exactly how it will fail.

One name is all this needs.

### U4 — the C10.1 contingency · **now urgent, and the numbers have moved**

§11 gives the default as *"C10.5's trigger already fired at G2"*. It fired considerably
earlier and by considerably more:

| | |
| --- | --- |
| Lead hours to date | **92.0 h** ([`ledger.md`](ledger.md)) |
| B9 allocation | **12.0 h** |
| Planned across M1+M2 | 55.3 h |

The C14 cut levers are exhausted — L1, L2, L3, L4 and L6 are all already applied. **The
contingency and the calendar are the only instruments left**, which is what §1.4.1 says and
what the ledger now demonstrates rather than projects.

This one needs a real conversation with the delivery manager, not a default. It is also the
row most likely to be deferred, because nobody enjoys it.

### D6 — Langfuse · probably superseded

C9.1 made Langfuse the only cost dashboard and B4 #10's spend line is reconciled from it.
Since then: generation is local and free, analysis is a few dollars, **nothing is deployed**,
and [ADR-011](decisions/ADR-011-no-redis.md) put the spend total in a file the breaker reads
and `make trip-breaker` exercises.

So the projected-spend figure for C15.1 #13 has a source that exists and is tested, and
standing up a hosted observability product for a laptop demo looks like effort spent against
a shape the project no longer has.

**Recommend recording it as superseded by ADR-011** — but that is the tech lead's call, not
a default to take silently, so it stays open with a recommendation attached.

### Also confirm in W9-a — the G2 branch

§11 asks whether the G2 branch was **recorded, not merely discussed**, because FE-3, FE-6
and FE-11 all read from it.

**It cannot be confirmed yet and that is not a slip.** The branch is decided by the held-out
κ and the pooled judge precision, which come from M2-17's single `--final` run, which is
behind the labels. FE-11's replay half shipped without it; **its G2-delta half is the part
still waiting**, and C1.3 prices that delta at 0–1.5 h precisely so the wait is cheap.

---

## The row that is not in §11, and blocks the most

**M1-11's 40 calibration labels.**

§11 was written assuming Month 2's labelling had happened on schedule. It has not, and the
consequence is larger than any row above:

    M1-11 (40 labels)  ->  M2-1a  ->  M2-1b  ->  M2-2 (needs the second annotator)
                                            ->  M2-3  ->  M2-5 / M2-7 / M2-8 / M2-10a
                                                      ->  M2-16  ->  M2-17  ->  M2-10b
                                                                           ->  M2-12  ->  G2

**Nine tasks and a gate.** It is ~65 minutes at the plan's own rate of 1.6 min/step, it
needs no other person, and it is the single highest-value hour left in the project:

    make label ARGS="--annotator <name>"

**The session is interruptible, and that was verified rather than assumed.** Every label is
appended and flushed the moment you press the key, a `[q]` or a Ctrl-C prints *"everything
labelled so far is already written"*, and a second run skips what is done with no
duplicates. Proven by running the real code path against a redirected output directory —
three labels survived an abrupt kill mid-session and resume picked up cleanly, with
`calibration/labels/` untouched. **So it does not need to be one sitting**, which matters
because this project has twice lost work to a harness that wrote its record only at the
end (M1-9 lost 13 runs that way).

It cannot be delegated to the implementer, and the reason is not squeamishness. The labels
are what the classifier is *measured against*; a set produced by the same system being
measured would make every downstream number circular. The tool is blind by construction —
it never shows a prediction — and that property only means something if a human is the one
reading the step.

## Related

- [`day-1-unblock.md`](day-1-unblock.md) — Month 1's equivalent, and the precedent for
  recording a default *taken* rather than a question unanswered
- [`g3-ship-checklist.md`](g3-ship-checklist.md) — E12 is U1, E13 is U2
- [`ledger.md`](ledger.md) — the figures behind U4
