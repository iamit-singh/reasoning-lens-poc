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
