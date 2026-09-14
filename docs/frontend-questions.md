# The frontend questions log (M2-19 · M3-10)

**The headline, and it is the thing G1 was bought for:
`schema_version` never moved.** Eight surfaces were built against the `ReasoningReport`
frozen at G1, and the contract took **one additive fixture extension and zero schema
changes**. The freeze is mechanical rather than a promise — `schema_version` is a `const`
and `additionalProperties: false` is set at every level, so a breaking change cannot happen
without editing the schema file, which is visible in review.

## How this log is kept, given there is one person

C10.3 books M2-19 to *"answer fixture and schema questions as they arise"* and M3-10 to give
*"same-day answers to FE-9's integration questions"*. Both assume a Frontend owner asking a
Lead. [Amendment 001](../../plan-amendment-001-local-hybrid.md) made this solo, so **there
was no question queue and a log of inter-person questions would be a log of nothing.**

This is the same substitution amendment 001 already made for G1 check 10, which asked the
Lead to walk the Frontend owner through the fixtures and became *"annotate each fixture with
the surface that consumes it"* — because Amit cannot walk himself through them.

**The questions still arose; they were just answered by a decision instead of a reply.**
What is recorded here is the decision, its category, and its cost — which is the part a
reviewer or a future maintainer actually needs. A question answered in one head and never
written down is indistinguishable at G3 from a question nobody asked.

## The log

| # | Question | Category | Resolution | Cost if deferred to M3 |
| - | --- | --- | --- | --- |
| 1 | The featured comparison has no true subject — C11.3 says *"featured trap comparison"* and [ADR-005](decisions/ADR-005-traps-do-not-reproduce.md) withdrew traps, then [ADR-006](decisions/ADR-006-arms-1-and-2-do-not-separate.md) withdrew the difficulty contrast | **Content, measured** | Re-pointed **twice**, to the **cost** contrast (1.2×–13.3× for the same answer) plus the **tool** contrast (arm 3 turns 3 wrongs right). Chosen by measured contrast at build time, not a hard-coded item id, so the page keeps leading with the most interesting row after the corpus changes | A landing page built in W9 around a row that does not exist |
| 2 | The five behaviour definitions appear in the classifier prompt, in `rubric.md`, and in the UI legend. Retype them? | **Drift risk** | **Parsed out of `rubric.md` at build time.** Three copies of the same five sentences is three places to drift, and κ measures rubric drift the moment they do. CI (`make rubric-drift`) already pins prompt↔rubric byte-identical | κ silently measuring a legend nobody updated |
| 3 | §6.3 specifies `report_nominal.json` *"harvested from a real W4 run"* — and no trace contains all five behaviour classes | **A state the fixtures cannot reach** | **Authored fixture, labelled as such.** `fx-` ids and a `fixture000000000` pin, asserted by a test, and `Provenance` renders *"Illustrative fixture — these numbers were authored, not measured"* on every page carrying a number | A reviewer shown invented numbers in a real-looking provenance block |
| 4 | Nothing exercised a flagged step **and** a populated `measurement_context`, so the panel rendered error bars from `undefined` | **Fixture gap** | **`report_flagged.json` extended** (`f500377`): +1 step, broader `error_type` coverage. Additive, G1-compatible, schema untouched. Found by the components, which is what building against fixtures is for | A confident number with no caveat — the exact I3 failure |
| 5 | `backtracking` renders only from the **authored** fixture, because ADR-010 measured zero instances in the corpus | **Fixture gap, deliberate** | Kept. A check built only on measured reports would pass **while the class was unrenderable**. (ADR-010's zero has since been corrected to **2.0%**, which strengthens the fixture's case rather than removing it) | An unrenderable behaviour class discovered by whoever opens the one trace that has it |
| 6 | With `NEXT_PUBLIC_USE_FIXTURES=0` the build dropped the authored fixtures entirely — and **the measured corpus is healthy**, so `unannotated` and `arm failed` occur nowhere in it | **Shipping-build gap** | **The shipping demo could not show a degraded state at all.** FE-8's seven banners and FE-2b's ten states were unreachable in the only artifact a visitor sees. Measured mode now keeps both, measured wins any id collision, measured sorts first (FE-9) | A demo that cannot show its own failure modes, found on stage |
| 7 | `error_type` has five enum values; the fixtures exercise **three** (`arithmetic`, `logical`, `unsupported_leap`) | **Fixture gap, low priority** | **Recorded, not fixed.** The renderer is type-agnostic — one chip, `replace(/_/g, " ")` — so there is no per-type branch that can break. And [ADR-012](decisions/ADR-012-judge-thresholds.md) found the types are **close to noise** (2 of 8 named correctly) and ruled that `error_type` must **never render as a measured quantity**. Extending fixtures to cover two more would buy coverage of a field the ADR says not to lean on | Negligible — and over-investing here would contradict ADR-012 |
| 8 | The README claimed the backend mounts the static export; `FRONTEND_OUT` was defined and never read | **Integration (M3-10's actual subject)** | Mounted last so it cannot shadow `/api`, only when the export exists, with traversal asserted on this service. `/readyz` reports `frontend_mounted` (FE-9) | CORS on a backend whose whole posture is that it accepts almost nothing |

## Schema changes since the G1 freeze

**None.** The freeze policy is additive-only until launch, and it was not exercised even
once — no new optional field was needed across eight surfaces.

| | |
| --- | --- |
| `schema_version` | **1.0**, unchanged since `c62ae2f` |
| Breaking changes | **0** |
| Additive fixture extensions | **1** (`f500377`, item 4 above) |
| Fixtures | 4 — one measured (`mb-13`), three authored (`fx-01`…`fx-03`) |

> **That is the result G1 cost W4 dearly to buy**, and it is worth stating plainly because
> the gate is easy to read as ceremony in hindsight. Eight surfaces, six of them built
> under estimate, against an object that did not move — and the one thing that *did* need
> extending was caught by the components in W5 rather than by a reviewer in W12.

## Open at end of W5

**Nothing blocking, and no open schema question carried into Month 3** — which is M2-19's
DoD.

Item 7 is open and deliberately unfixed, with its reason. Everything else is closed.

The one Month-3 frontend item that is *not* a question but a genuine dependency:
**FE-11's replay surface needs the mutated reports M2-6 was to commit and did not** — see
[`g3-ship-checklist.md`](g3-ship-checklist.md). That is a Lead task with a spend cost, not a
frontend question, and it is recorded there rather than here.
