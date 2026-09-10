# Day-1 unblock list — the four Appendix D decisions due in W1

**Status: all four drafted below, ready to send. None has been sent — each needs a human
to put it in front of its owner.**

All four are asks of other people; none can be decided by the implementer. Each has a
stated default, so **none of them blocks work** — but each one taken by default rather than
by decision is a thing the reviewer should know was taken by default. That is what this
file records.

| # | Decision | Owner | Default if unanswered | Consequence of the default | Status |
| - | -------- | ----- | --------------------- | -------------------------- | ------ |
| 1 | Capacity option 1 / 2 / 3 (C10.1) | Tech lead + DM | **Option 2, L1–L6 applied at kickoff** | L1 and L2 shape M1-4 and M1-7 **this month** — 14 bank items, 12 ReAct facts | **Default taken** (see below) |
| 2 | Provider and `MODEL_PIN` for generation, triage, escalation | Tech lead, *after* S1 | Decided by S1's finding; recorded in ADR-001 | None — S1 produces the input | Awaiting S1 (needs an API key) |
| 4 | DNS delegation for `demos.talentica.com` — who creates the record | IT / marketing | **Raise the ticket regardless** | None in Month 1; it is the launch gate that pays | Ticket drafted, [ADR-003](decisions/ADR-003-hosting.md) — **not yet filed** |
| 7 | Reviewer acknowledgement of the three C0.3 changes (#1, #2, #5) | Reviewer | Plan proceeds as written; change noted in the G2 report | The corrected precision construction and the dev/held-out split are **already assumed** by M1-11's sampling design | Draft ask below — not yet sent |

---

## #1 — Capacity option: **the default has been taken, and it has already changed the code**

The risk table says: *if Appendix D #1 is still undecided at end of W1, proceed on the
stated default — Option 2 with L1–L6 applied at kickoff — and record that the default was
taken.* This file is that record.

Because applying the levers in W10 saves nothing, **L1 and L2 are applied now**, before
the bank is authored and before the ReAct corpus is written:

| Lever | Effect | Lands in | Saving |
| --- | --- | --- | --- |
| **L1** | Problem bank **18 → 14 items**, floors held: ≥ 5 `tool_required`, 3 traps, 3 `easy`, 3 `multi_step` | M1-4 (W2) | −0.8 h |
| **L2** | ReAct corpus **30 → 12 facts**, exact match only | M1-7 (W3) | −0.5 h |

> **⚠️ If the tech lead and DM choose Option 1 or 3 instead, say so before W2 starts.**
> After M1-4 is authored at 14 items, un-applying L1 means authoring four more items *and*
> re-drawing the sampling frame — the second of those is the expensive half.

**The ask to send:**

> Month 1 of the Reasoning Lens PoC needs ~24.7 hours against a Lead allocation of ~12
> (C10.1's finding, localised to Month 1). Appendix D #1 asks you to pick capacity option
> 1, 2 or 3. Its stated default is **Option 2 with cut levers L1–L6 applied at kickoff**,
> and I am proceeding on that default so W2 is not blocked. Concretely, that already means
> a 14-item problem bank and a 12-fact ReAct corpus rather than 18 and 30.
>
> If you want Option 1 or 3, I need to know **before W2 starts (16 Sep)** — after the bank
> is authored, reversing L1 also means re-drawing the calibration sampling frame.
>
> The first real reading on whether the Option-2 bet holds arrives at the **end of W4**, in
> `docs/ledger.md` — four weeks before the G2 trigger point.

## #2 — Provider and `MODEL_PIN`

Not blocked and not blocking: S1 produces the input, the tech lead decides after. What the
owner needs to know **now** is only that it is coming, plus the one thing that gates it.

**The ask to send:**

> S1 (the provider thinking-trace fidelity spike) reports at the end of W1 and produces the
> input for your `MODEL_PIN` decision — see `docs/decisions/ADR-001-provider.md`, which is
> committed as *Proposed* with the six G0 checks and all four consequence branches written
> out in advance, so the gate is a reading and not a discussion.
>
> **One blocker:** the spike needs an API key for each candidate tier (a few cents of
> spend). There is no key in the dev environment. Please point me at one, or approve
> creating one. Everything else in Week 1 is done.

## #4 — DNS delegation

Drafted verbatim and ready to file: [ADR-003](decisions/ADR-003-hosting.md). The ask needs
a **named owner and a date** back, not just an acknowledgement.

## #7 — Reviewer acknowledgement of the three C0.3 changes

**The ask to send:**

> The implementation plan resolves three defects in Part B (C0.3 #1, #2 and #5). Two of
> them are **already assumed by the Month-1 calibration design**, so I would rather you
> object now than at G2:
>
> - **#1 — the corrected judge-precision construction.** Precision is pooled and stated
>   with its construction, not quoted as a bare number.
> - **#2 — the dev / held-out split.** 100 dev steps for prompt iteration, 50 double-labeled
>   held-out steps opened once after the prompt bundle is frozen. The held-out file is
>   git-protected by a CI check (`scripts/check_heldout_freeze.sh`, wired this week) so it
>   cannot be quietly edited to improve a number.
> - **#5 — the two-part sampling frame.** κ on a uniform random-90 draw only; per-class F1
>   on the pooled set with the enrichment factor stated. This replaces "150 stratified
>   steps", which would have produced a subtly biased κ at identical labeling cost.
>
> Default if I hear nothing: the plan proceeds as written and the change is noted in the G2
> report. **Silence is a fine answer** — I just need it to be a knowing one, because the
> first 40 labels are drawn against this design in W4.

---

## Also flag now, though not due until W5 — Appendix D #5

**The second annotator must be named and committed for ~2 hours in W6.** It is a **hard
requirement: B4 #1 (κ ≥ 0.70) is unmeasurable without a second independent labeler.**

> Naming a person in W1 costs one message. Discovering in W6 that nobody is available costs
> the PoC's headline κ.

**The ask to send:**

> I need a second annotator named now for ~2 hours of work in W6 (labeling 50 reasoning
> steps against a written rubric, independently, with no prior discussion). It does not need
> to be a specialist — the rubric is self-contained by design. It does need to be a
> *different person from me*, and it needs to be committed in advance, because Cohen's κ is
> the PoC's headline number and it is unmeasurable without them.

| Field | Value |
| --- | --- |
| Named second annotator | *pending* |
| Confirmed for W6 | *pending* |
