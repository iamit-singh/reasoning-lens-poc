// The frontend reads committed ReasoningReport fixtures in dev (C2.1). These names are the
// G1 contract (M1-10): every one of the eight frontend surfaces is built against them, so
// they are referenced here to keep the names fixed.
//
// **There are four, and the plan specified three.** §6.3 asks for `report_nominal` to be
// harvested from a real run covering all five behavior classes; measurement said that is
// not available on this corpus -- the classifier produced `backtracking` 0 times in 310
// steps and no trace carries five classes (ADR-010). So the authored fixture and a real
// one are both committed, and each says which it is rather than leaving a reader to guess.
export const REPORT_FIXTURES = [
  "report_nominal.json", // AUTHORED. All 5 behavior classes -- the only fixture that has them
  "report_flagged.json", // AUTHORED. unsound verdict, error type, escalated: true, rationale
  "report_degraded.json", // AUTHORED. failed arm, classifier_parse_failure, provider_summarised
  "report_measured.json", // MEASURED. A real run -- realistic text lengths and null patterns
];

// Authored fixtures use `fx-NN` item ids and a `model_pin` of "fixture000000000"; the
// measured one uses neither, and a test asserts both. Nothing here should ever be
// mistakable for measured data.
export const AUTHORED_FIXTURES = REPORT_FIXTURES.slice(0, 3);
export const MEASURED_FIXTURE = "report_measured.json";

export const FIXTURE_DIR = "../../analyzer/tests/fixtures/reports";

// Which surface consumes which fixture is documented, and asserted by a test, in
// `analyzer/tests/fixtures/reports/README.md`. That table is G1 check 10 as amendment 001
// redefined it -- read it before building a component against any of these.
