// The frontend reads committed ReasoningReport fixtures in dev (C2.1). These three
// names are the G1 contract (M1-10): every one of the eight frontend surfaces is
// built against them, so they are referenced here from Week 1 to keep the names fixed.
export const REPORT_FIXTURES = [
  "report_nominal.json", // all 5 behavior classes
  "report_flagged.json", // unsound verdict, error type, escalated: true, rationale
  "report_degraded.json", // failed arm, classifier_parse_failure, provider_summarised
];

export const FIXTURE_DIR = "../../analyzer/tests/fixtures/reports";
