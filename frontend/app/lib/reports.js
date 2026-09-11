import fs from "node:fs";
import path from "node:path";

/**
 * Report loading — the fixtures-first seam (C4.10).
 *
 * **Everything here runs at build time, never in a browser.** `output: "export"` pre-renders
 * every page, so these reads happen once during `next build` and the result is baked into
 * HTML. That is what makes C11.3's "server-rendered featured comparison" a build-time data
 * dependency rather than a runtime one, and it is why the demo's cached path has nothing to
 * wait for.
 *
 * `NEXT_PUBLIC_USE_FIXTURES=1` is the default rather than an opt-in, and deliberately: C4.10
 * makes fixtures-first mandatory, and a frontend that quietly preferred a live backend would
 * stop building the moment the Lead's machine was busy — which is the dependency the whole
 * arrangement exists to remove. FE-9 adds the live seam in Month 3; until then there is
 * nothing to fall back to and nothing to get wrong.
 */

const FIXTURE_DIR = path.join(process.cwd(), "..", "analyzer", "tests", "fixtures", "reports");
const RUN_DIR = path.join(process.cwd(), "..", "out", "reports");

/** Reports from a real `make report` run, if the developer has produced any. */
function readRunReports() {
  if (process.env.NEXT_PUBLIC_USE_FIXTURES === "0" && fs.existsSync(RUN_DIR)) {
    return fs
      .readdirSync(RUN_DIR)
      .filter((f) => f.endsWith(".report.json"))
      .map((f) => JSON.parse(fs.readFileSync(path.join(RUN_DIR, f), "utf8")));
  }
  return [];
}

function readFixtures() {
  if (!fs.existsSync(FIXTURE_DIR)) return [];
  return fs
    .readdirSync(FIXTURE_DIR)
    .filter((f) => f.startsWith("report_") && f.endsWith(".json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(FIXTURE_DIR, f), "utf8")));
}

let cache = null;

/** Every report available to this build, newest source wins, sorted by item id. */
export function allReports() {
  if (cache) return cache;
  const run = readRunReports();
  const reports = run.length ? run : readFixtures();
  cache = reports.sort((a, b) => a.item.id.localeCompare(b.item.id));
  return cache;
}

export function reportFor(itemId) {
  return allReports().find((r) => r.item.id === itemId) ?? null;
}

/**
 * Is this report authored rather than measured?
 *
 * The three authored fixtures carry `fx-` ids and a `model_pin` of "fixture000000000", and
 * a test in the analyzer asserts it. **The UI has to say so.** A page that rendered an
 * authored fixture identically to a measured report would be showing a reviewer invented
 * numbers with a real-looking provenance block, which is the single most damaging thing
 * this frontend could do.
 */
export function isAuthored(report) {
  return report.versions.model_pin === "fixture000000000";
}

/** Every distinct tag across the available reports, with counts. */
export function tagIndex() {
  const counts = new Map();
  for (const report of allReports()) {
    for (const tag of report.item.tags ?? []) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([tag, n]) => ({ tag, n }));
}

export function armsOf(report) {
  const order = ["direct", "thinking", "react"];
  return [...report.arms].sort((a, b) => order.indexOf(a.strategy) - order.indexOf(b.strategy));
}

// Re-exported so server components have one import. The definition lives in `labels.js`,
// which has no Node imports — see the note there.
export { ARM_LABEL } from "./labels";

/**
 * The comparison the landing page leads with (B6.2 step 1, C11.3).
 *
 * **The plan says "featured trap comparison" and there are no traps.**
 * [ADR-005](../../docs/decisions/ADR-005-traps-do-not-reproduce.md) withdrew the category
 * after 0 of 16 candidates reproduced over 120 runs, and
 * [ADR-006](../../docs/decisions/ADR-006-arms-1-and-2-do-not-separate.md) found arms 1 and 2
 * do not separate on accuracy either. What survived measurement is the **cost** contrast —
 * the same answer for many times the reasoning tokens — and the **tool** contrast, where
 * arm 3 turns a wrong answer right.
 *
 * So the featured slot picks, in order of how striking the finding is:
 *   1. an item where one arm is right and another is wrong  (the tool contrast),
 *   2. else the widest cost ratio for an identical answer   (the cost contrast),
 *   3. else the first item, so the page is never empty.
 *
 * Choosing by measured contrast rather than by a hard-coded item id is not tidiness: it
 * means the landing page keeps leading with the most interesting row in the corpus after
 * the corpus changes, instead of leading with whatever was interesting in October.
 */
export function featured() {
  const reports = allReports();
  if (!reports.length) return null;

  const scored = reports.map((report) => {
    const arms = armsOf(report);
    const correct = arms.filter((a) => a.correct === true);
    const wrong = arms.filter((a) => a.correct === false);
    const ratio = report.scoreboard?.cost_of_thought_ratio ?? null;
    const separates = correct.length > 0 && wrong.length > 0;

    // **`tool` only when the arm that got it right is the tool arm.** The first version of
    // this called any right-vs-wrong split a "tool contrast" and the landing page said
    // "one of them looked the fact up" over a report where Direct beat Extended thinking
    // on an arithmetic slip. That is exactly the overclaim ADR-006 exists to stop, made by
    // the page rather than by a person — and it would have been made on arrival, in the
    // headline, to a reviewer.
    const rescuer = separates ? (correct.find((a) => a.strategy === "react") ?? correct[0]) : null;
    const kind = separates
      ? rescuer.strategy === "react"
        ? "tool"
        : "accuracy"
      : ratio
        ? "cost"
        : "plain";

    return {
      report,
      kind,
      ratio,
      rescued: separates ? { correct: rescuer, wrong: wrong[0] } : null,
    };
  });

  // Measured beats authored at equal interest. A landing page that led with an invented
  // comparison while a real one sat one row below would be choosing the better story over
  // the true one, which is the trade this whole project refuses everywhere else.
  const rank = { tool: 0, accuracy: 1, cost: 2, plain: 3 };
  scored.sort(
    (a, b) =>
      rank[a.kind] - rank[b.kind] ||
      isAuthored(a.report) - isAuthored(b.report) ||
      (b.ratio ?? 0) - (a.ratio ?? 0)
  );
  return scored[0];
}
