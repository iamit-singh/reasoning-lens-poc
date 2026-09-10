# ADR-003 — Local-only demo: no deployment, no domain

| | |
| --- | --- |
| **Status** | **Accepted** — 10 Sep 2026 (W1). Supersedes this ADR's own "ticket drafted" state |
| **Decided by** | Amit Singh (sole contributor) |
| **Amends** | Plan §C7.3, §C9.2, §C9.3, §C10.4, Appendix D #4 · see [plan amendment 001](../../../plan-amendment-001-local-hybrid.md) |

## Context and decision

The demo is driven from a local machine. **There is no public URL, no cloud service, and no
anonymous visitor.** Everything the plan built for a hosted public demo is therefore work
without a consumer.

> **The DNS delegation request is cancelled.** It was drafted and ready to file; it was never
> filed, and it should not be. There is no public hostname to delegate. The ~0.4 h spent
> drafting it is sunk — recorded in the ledger rather than quietly dropped.

## Deleted outright — ≈ 6.2 h released

| Work | Hours | Why it is safe |
| --- | --- | --- |
| DNS delegation for `reasoning-lens.demos.talentica.com` | 0.5 *(0.4 sunk)* | no public hostname exists |
| ECR, App Runner, custom domain, CI deploy pipeline | 2.0 | nothing is deployed |
| Automatic rollback + the rollback drill | ~0.7 | nothing to roll back to |
| Per-visitor rate limiting | ~0.7 | the operator is the only caller |
| Abuse controls, CSP `frame-ancestors`, iframe embed handoff | ~0.7 | no embed, no hostile input path |
| Managed Redis provisioning + fail-closed decision | ~0.8 | local Redis via compose, or the filesystem cache tier |

## Retained in reduced form — ≈ 1.2 h

| Work | Why it survives |
| --- | --- |
| **Smoke test** (~0.3 h) | still the acceptance script — it runs against `localhost`. It is the check that the demo works *before* an audience sees it, which was always its point |
| **Kill switch `DEMO_MODE=cached`** (~0.2 h) | now the *demo-safety* switch rather than a spend control: a guaranteed zero-dependency run when the network or a key is unavailable. **More useful than before** |
| Spend guard (~0.1 h) | analysis spend is a few dollars, but a runaway loop is still a runaway loop |
| **Fallback video** (~0.3 h) | a local demo has *more* single points of failure than a hosted one, not fewer |
| Packaging (~0.3 h) | clean-venv install proof + the analyzer wheel. Always the real handover artifact; unaffected by dropping the cloud |

## What the demo is now

`docker compose up` for Redis; the **local model served natively** so it reaches the GPU
(not in Docker — containerised inference on macOS loses Metal); the UI served from the same
process. The three arms replay from cache in seconds. A live re-run exists but is no longer
the happy path.

## Net effect

**≈ 3.7 h released** after the 1.3 h this decision *adds* elsewhere (local runtime setup, the
tool-calling spike, dual calibration reporting — see ADR-001 and the amendment). The saving
is concentrated in Month 3, the month that was most over budget.

**Risk accepted:** the demo now depends on one laptop. That is the trade for deleting the
cloud path, and it is why the fallback video and the cached-only mode are retained rather
than cut as ceremony.
