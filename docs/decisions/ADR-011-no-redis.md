# ADR-011 — No Redis. The cache is the filesystem and the breaker is a file

| | |
| --- | --- |
| **Status** | **Accepted** — 12 Sep 2026 (W5, building M3-7 ahead of W9) |
| **Decided by** | Amit Singh (sole contributor) |
| **Closes** | M3-7 *(Redis topology + fail-closed)* · narrows M3-2a · amends `docker-compose.yml` |
| **Builds on** | [ADR-003](ADR-003-hosting.md), which left this exact choice open |

## Context

M3-7 is budgeted 1.0 h to decide Redis topology and the fail-closed semantics of the spend
breaker. [ADR-003](ADR-003-hosting.md) already deleted the deployment and left one line
open on this question:

> Managed Redis provisioning + fail-closed decision — ~0.8 h — *local Redis via compose, or
> the filesystem cache tier*

So the decision is not *which Redis* but *whether Redis*. That is a smaller question than
C10.4 budgeted, and it has a clear answer.

## Decision

**No Redis. The cache tier is the filesystem, and the spend breaker is a file.**
`docker-compose.yml` drops the service; `REDIS_URL` is removed from the environment.

### Why, in the order the reasons actually weigh

**1. There is one process.** ADR-003 makes the demo a single local process driven by its
operator. Every job Redis was specified to do here — a shared cache, a shared rate-limit
counter, a shared spend total — is *coordination between replicas that do not exist*. The
rate limiter already says this in a comment and is already in-process; this ADR just
extends the same reasoning to the other two.

**2. A dependency that can only fail.** This is the argument that settles it. In this
topology Redis cannot make the demo more reliable, because there is nothing for it to
coordinate — but it can absolutely make it *less* reliable, by being down. C10.4's own
risk register has a fallback-video line item precisely because *"a local demo has more
single points of failure than a hosted one, not fewer"*. Adding a network service to a
laptop demo, for no functional gain, adds one more.

**3. The filesystem is already the source of truth.** `GET /api/report/{id}` serves
`out/reports/{id}.report.json` from disk today. A Redis tier in front of a disk read that
is already sub-millisecond is a cache in front of a cache.

> **What we give up, stated plainly:** the spend total no longer survives a process
> restart *atomically* — two processes racing on the breaker file could interleave a
> write. **On one laptop with one operator there is no second process**, and the failure
> mode if there ever were one is that the breaker trips slightly late. That is a cost
> worth naming and not worth a service.

### The fail-closed semantics, which are the part that matters

C9 asks the spend breaker to fail **closed**. The plan's phrasing assumed a Redis read that
could error; the principle survives the mechanism unchanged, and is implemented literally:

| Condition | Breaker says |
| --- | --- |
| File readable, total under the limit | **allow** |
| File readable, total at or over the limit | **deny** — tripped |
| File missing | **allow** — a fresh install has spent nothing |
| File present but **unreadable, malformed, or holding a non-number** | **DENY** |

The last row is the whole point. *"We could not read the spend total"* must never resolve
to *"so we assume it is zero"* — that is the failure mode where a corrupted file buys an
unbounded run. This project has now written the same sentence about a trace it could not
read, an answer it could not parse, and an arm whose classifier failed: **the third
outcome gets its own branch instead of collapsing into the nearest convenient lie.**

A missing file is genuinely different from an unreadable one and is allowed, because
otherwise a fresh checkout is born tripped and the first thing any operator learns is how
to bypass the breaker.

## Consequences

1. **M3-7 closes at well under its 1.0 h**, because ADR-003 had already done the expensive
   half of the thinking.
2. **M3-2a narrows** to the disk tier and the C2.3 cache key. There is no second tier to
   write, and no "Redis-down read still serves" test to write either — the path that test
   protected no longer exists.
3. **`docker-compose.yml` loses a service and a healthcheck**, so `make demo` has one
   fewer thing to wait for and one fewer thing to fail.
4. **The breaker is testable by a forced trip**, which M3-3's DoD demands — and testing it
   is now writing a file rather than partitioning a network. The Redis-partition test in
   M3-3's DoD is replaced by an **unreadable-file test**, which exercises the same
   fail-closed branch and is the one that can actually happen here.
5. **If this ever runs replicated, this ADR is the thing to revisit** — and the symptom
   will be obvious and benign: limits and spend totals that are per-process.
