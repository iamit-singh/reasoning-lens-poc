# ADR-003 — Hosting and the DNS delegation

| | |
| --- | --- |
| **Status** | **Ticket drafted — not yet raised.** Needs a human to file it and name an owner. |
| **Date raised** | 2026-09-10 (W1) |
| **Task** | M1-3 (S5) · W1 · 0.5 h |
| **Decision owner** | IT / marketing (Appendix D #4) |
| **Gate** | M3-4 launch gate. Tracked on the **W4 and W8** gate checklists. |

## Context

`reasoning-lens.demos.talentica.com` needs a DNS delegation. Fifteen minutes of work;
**the value is entirely in the calendar time it starts consuming.** C13.1 puts S5 in Week 1
precisely because *the request, not the work, is the risk* — and C13.2 rates the residual
risk "low" **by construction only because the request goes out in W1**. A ticket sitting
unassigned in W6 is a launch-gate risk that has not actually been retired.

Appendix D #4's own stated default is **raise the ticket regardless** of who ends up
creating the record, so nothing here waits on the decision.

## Decision

Prod is a **single AWS App Runner service**, no staging tier, no manual deploy gate
(B0 Condition #2). The frontend is a Next.js static export mounted by FastAPI from one
image (C7.3). The only external dependency is the DNS delegation below.

## The ask — ready to file verbatim

> **Title:** DNS delegation for `demos.talentica.com` — Reasoning Lens PoC demo
>
> **Requested by:** Amit Singh (amit.singh1@talentica.com), Emerging Tech Team
> **Raised:** 2026-09-10 · **Needed by:** 2026-10-30 (six weeks before the M3 launch gate)
>
> **What we need:** delegation of the `demos.talentica.com` zone (or, if delegation is not
> possible, a `CNAME` for `reasoning-lens.demos.talentica.com` plus the ACM validation
> records we will supply), so a public demo can be served over TLS from AWS App Runner.
>
> **Why the subdomain rather than a path on the main site:** the demo is an iframe-embedded
> single service with its own CSP `frame-ancestors: https://talentica.com`. It must not
> share an origin with the marketing site.
>
> **What we will supply:** the App Runner default domain and the ACM DNS validation
> CNAME records, as soon as the service exists (~W9).
>
> **What we need back now:** (1) a **named owner** for this ticket, and (2) a **date** by
> which the delegation will exist. We do not need the record created today — we need to
> know who creates it and when, because the launch gate depends on it and this is the one
> item in the project whose lead time we cannot compress.
>
> **Marketing conversation, same thread:** who signs off on a public
> `*.talentica.com` demo page, and what (if any) branding or disclaimer it must carry.

## DoD, and why the wording matters

**Not "raised" — named and dated.** A ticket without a named owner and a date has not
retired the risk it was filed to retire.

| Field | Value |
| --- | --- |
| Ticket ID | *pending* |
| Named owner | *pending* |
| Committed date | *pending* |
| Marketing sign-off owner | *pending* |

## Chase schedule

Per the risk table: **chase in W3 and W6**, and check this ADR on the **W4 and W8** gate
checklists. If it is still unassigned at W6, escalate — do not simply chase a third time.
