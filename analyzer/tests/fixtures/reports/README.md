# `ReasoningReport` fixtures — the G1 contract

Three fixtures, frozen at **G1** (end of W4). Every one of the eight frontend surfaces is
built against them, which is what lets 12 frontend hours cover eight surfaces.

| File | Must cover |
| --- | --- |
| `report_nominal.json` | **all 5 behavior classes** |
| `report_flagged.json` | a **flagged step** — unsound verdict, error type, `escalated: true`, rationale |
| `report_degraded.json` | a **degraded run** — failed arm, `classifier_parse_failure`, `provider_summarised`, `escalation_capped`, `budget_bound` |

> **These are hand-authored against the schema, not harvested from a run.** In W4 the
> classifier is v0 and the escalation tier (M2-5) does not exist, so a flagged step and a
> degraded run cannot occur naturally until Month 3. The fixture's job is to pin the
> *contract* so FE-4 (flagged-step side panel) and FE-8 (degraded banners) can be built in
> Month 2 against states that do not yet exist. Budget it as **authoring** work, not capture.

Owner: M1-10 (W4).
