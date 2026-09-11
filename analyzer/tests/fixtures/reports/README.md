# `ReasoningReport` fixtures — the G1 contract

Frozen at **G1** (end of W4). Every one of the eight frontend surfaces is built against
these, which is what lets 12 frontend hours cover eight surfaces.

| File | Provenance | Must cover |
| --- | --- | --- |
| `report_nominal.json` | **authored** | **all 5 behavior classes**, `trace_quality: full`, consistency `entails` |
| `report_flagged.json` | **authored** | a **flagged step** — unsound verdict, error type, `escalated: true`, rationale; consistency `contradicts` with citations |
| `report_degraded.json` | **authored** | a **degraded run** — failed arm, `classifier_parse_failure`, `provider_summarised`, `escalation_capped`, `budget_bound` |
| `report_measured.json` | **measured** — a real `make report` run | nothing in particular. It is here to be *real* |

All four validate against `src/rlens/schemas/reasoning_report.schema.json` on every PR, and
**that assertion is the freeze mechanism**. After G1 a fixture that stops validating is not
a test to update; it is a schema change, and a schema change is a plan amendment.

## Why three of them are authored

In W4 the classifier is v0, the escalation tier (M2-5) does not exist and the consistency
checker (M2-8) does not exist. A flagged step and a degraded run therefore **cannot occur
naturally** until Month 3. The fixture's job is to pin the *contract* so FE-4 (flagged-step
side panel) and FE-8 (degraded banners) can be built in Month 2 against states that do not
yet exist. Budget it as **authoring** work, not capture.

An authored fixture uses an `fx-NN` item id and a `model_pin` of `fixture000000000`, and a
test asserts both. Nothing here should ever be mistakable for measured data — including by
somebody reading it in three months.

## Why there is a fourth one the plan did not ask for

§6.3 specifies `report_nominal.json` as *"harvested from a real W4 run, hand-checked"*.
**That turned out not to be possible, and the reason is a finding rather than an
inconvenience.** Over a full pass of the bank × 3 arms, the classifier produced:

| Class | Rows |
| --- | --- |
| `linear` | 252 |
| `verification` | 35 |
| `subgoal_setting` | 22 |
| `backward_chaining` | 1 |
| `backtracking` | **0** |

**No trace on this corpus contains all five classes**, so no harvested report can satisfy
G1 check 3. Rather than quietly hand-authoring a file called "nominal" and letting the
frontend owner assume it came from a run, both exist and both say which they are:

* `report_nominal.json` is authored, covers the five classes, and is what the class legend,
  the distribution bar and the per-class filter are built against.
* `report_measured.json` is a real report from a real run. It is what **realistic text
  lengths, step counts and null-field patterns** look like, and it is the one that will
  look wrong first if the pipeline changes under it.

Regenerate the measured one with `make report ARGS="--item mb-13"` and copy it here. It is
the only fixture that can go stale, and that is the price of being the only real one.

---

## Which surface consumes which fixture — **this section is G1 check 10**

§8.2's check 10 was *"the frontend owner has been walked through the fixtures; no open
questions"*. [Plan amendment 001](../../../../plan-amendment-001-local-hybrid.md) replaced
it, because Amit is now the sole contributor and **cannot walk himself through them**. The
replacement is a written artifact: *the fixtures are committed, schema-validated, and each
is annotated with which UI surface consumes it.* That is this table, and it is the check.

| Surface | What it renders | Fixture it is built against | The state it would otherwise miss |
| --- | --- | --- | --- |
| **FE-1** shell, picker, routing | item picker by tag; featured comparison on arrival | `report_measured` | Real `tags`, real prompt lengths. The authored items are `fx-` and would not appear under a bank tag |
| **FE-2** annotated trace renderer | 3 panes, 5 tag colours, hover definitions | `report_nominal` **and** `report_degraded` | Nominal is the **only** fixture with all five tag colours. Degraded carries `provider_summarised` and the unannotated fallback — `behavior: null` on every step, which is a *different* render from "no steps" |
| **FE-3** scoreboard + verdict line | per-arm metrics; soundness beside its precision/recall; failed-arm column | `report_degraded` | The **failed-arm column**: `status: "failed"`, `metrics: null`, `steps: []`. And `measurement_context` all-null — I3 says soundness never renders without its precision/recall, and null is the state it is in until M2-17, so FE-3 must render "not yet measured" rather than hiding the block |
| **FE-4** flagged-step side panel | rubric verdict, error type, escalated badge, consistency warning | `report_flagged` | The only fixture with `verdict: "unsound"`, a non-null `error_type`, `escalated: true` and a populated `rationale` together — and the only `consistency.verdict: "contradicts"` with citations |
| **FE-5** faithfulness panel | side-by-side hinted/unhinted | *none — `faithfulness/panel.json`, M2-9* | Not part of `ReasoningReport`. Named here so nobody looks for it |
| **FE-6** calibration page | `/api/calibration` verbatim, zero hard-coded numbers | *none — `calibration/results/latest.json`, M2-8* | Same. The `measurement_context` block in a report is the *per-report* copy, not the page |
| **FE-7** report download | blob download; the JSON must validate | any of the four | The download **is** this object. `test_every_fixture_validates` is the same assertion FE-7's DoD makes |
| **FE-8** progress + banners | SSE progress, `degraded` / `cached-only` / `illustrative replay` banners | `report_degraded` | **All of it.** `degraded.reason`, `escalation_capped`, `budget_bound`, `trace_quality: provider_summarised`, and a failed arm. FE-8 is 1.5 h of *unbudgeted* Month-3 work whose every state must be reachable in mock mode |

### Three things worth knowing before writing a component against these

1. **`null` is a state, not an absence.** `consistency`, `metrics.est_cost_usd`,
   `soundness_score` and every field of `measurement_context` are null in Month 1 because
   the code that fills them is Month 2's. A component that renders nothing when they are
   null will look finished and be wrong: I3 requires "not yet measured" to be visible.
2. **A degraded arm has steps and no labels.** `behavior: null` and `validity: null` on
   every step, with the text intact. This is deliberate (C4.3) — a fabricated `linear`
   would render identically to a real one, so the classifier refuses to produce one.
   Anything that assumes `step.behavior.label` exists will throw on a real report.
3. **`correct` is `true | false | null`.** Null means the answer could not be parsed, which
   is a third outcome and not a quiet `false` — `false` asserts the model answered and was
   wrong.
