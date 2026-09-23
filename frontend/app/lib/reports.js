import fs from "node:fs";
import path from "node:path";

// A local binding, because the `export { ARM_LABEL } from "./labels"` below re-exports
// without bringing the name into this module's scope — `startHere()` names the arms.
import { ARM_LABEL } from "./labels";

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

/**
 * Every report available to this build, sorted by item id.
 *
 * **Measured mode keeps the authored fixtures, and FE-9 is why.** The obvious version of
 * this preferred measured reports and dropped the fixtures entirely — and that quietly
 * broke the shipping build, because **the measured corpus is healthy**. All 42 arms
 * succeeded and every step got a label, so `unannotated` and `arm failed` occur nowhere in
 * it. The demo that actually ships could not show a degraded state at all, and FE-8's seven
 * banners and FE-2b's ten trace states were unreachable in the only artifact a visitor
 * sees. `make fe-export-check` caught it on the measured build, having passed on fixtures.
 *
 * This is the mirror image of the note in FE-2b's commit: a check built only on *measured*
 * reports passes while a state is unrenderable, and a build that keeps only measured
 * reports renders a site that cannot show its own failure modes. **`report_degraded.json`
 * was committed at G1 for exactly this** — states the pipeline cannot produce on demand —
 * and dropping it from the shipping build throws away what the gate bought.
 *
 * Keeping both is safe because the ids cannot collide (`fx-` authored, `mb-` measured) and
 * because `Provenance` is loud on every page that shows a number: an authored report reads
 * *"Illustrative fixture — these numbers were authored, not measured."* **Measured wins any
 * collision**, so `report_measured.json` never shadows the real `mb-13`.
 *
 * Fixture mode is unchanged — fixtures only — because CI and local dev depend on it being
 * deterministic and independent of whatever `out/reports` happens to hold (C7.1).
 */
export function allReports() {
  if (cache) return cache;
  const run = readRunReports();
  const measured = new Set(run.map((r) => r.item.id));
  const reports = run.length
    ? [...run, ...readFixtures().filter((f) => !measured.has(f.item.id))]
    : readFixtures();
  // **Measured first, then authored, each by id.** Sorting on id alone put `fx-01` above
  // `mb-01`, so the first three rows a reviewer met in the picker were hand-authored
  // illustrations. They are labelled, but leading with them buries fourteen real runs
  // underneath three invented ones -- the same "better story over the true one" trade the
  // featured-slot ranking already refuses one section below.
  cache = reports.sort(
    (a, b) => isAuthored(a) - isAuthored(b) || a.item.id.localeCompare(b.item.id)
  );
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

/**
 * Two items worth opening first (E12 queue #4).
 *
 * Finding 6 of the heuristic walkthrough review: **the route to the insight is opt-in.**
 * Soundness verdicts, the flagged-step panel and the escalation state — the places where a
 * step is shown to be fluent and still not hold up — live *inside* an item page, which a
 * reader reaches only by choosing one of 27 problems in id order, led by *"what is the
 * chemical symbol for potassium?"*. A reader who opens `mb-02` (*17 × 4*) meets three arms
 * agreeing on 68, which correctly demonstrates nothing in particular, two clicks from the
 * question they were asked.
 *
 * So the page offers a couple of doors rather than a directory. **Which doors is derived
 * from the judged corpus, never a hand-kept list of ids** — the same argument `featured()`
 * makes one function below: a list typed in today leads with whatever was interesting in
 * October, and this one would additionally be a claim about the evidence that no longer
 * matched it.
 *
 * The ranking is the strength of the demonstration, and the first rank is the whole point:
 *
 *   1. **a correct arm carrying a step the judge called `unsound`** — the right answer with
 *      reasoning that did not hold up, which is the thesis on one row,
 *   2. an arm that got it wrong with unsound steps to show for it,
 *   3. else an item where the arms simply disagree.
 *
 * **The featured item is excluded**, since it is already the largest thing on the page, and
 * authored fixtures are excluded outright: an invented illustration is the last thing that
 * should be recommended as a starting point to someone deciding whether to trust this.
 *
 * Each entry carries `caveat: true` when its reason rests on a judge verdict, because
 * pooled judge precision is **0.643** and the calibration page's instruction — *"treat every
 * flagged step as a prompt to look, not as a finding"* — has to travel with the flag rather
 * than sit on a page the reader may not open.
 */
export function startHere(excludeId = null, limit = 2) {
  const scored = [];
  for (const report of allReports()) {
    if (report.item.id === excludeId || isAuthored(report)) continue;
    const arms = armsOf(report);
    const unsoundOf = (arm) =>
      arm.steps.filter((s) => s.validity?.verdict === "unsound").length;

    const rightButUnsound = arms.find((a) => a.correct === true && unsoundOf(a) > 0);
    const wrongAndUnsound = arms.find((a) => a.correct === false && unsoundOf(a) > 0);
    const splits =
      arms.some((a) => a.correct === true) &&
      arms.some((a) => a.correct === false || a.correct === null);

    if (rightButUnsound) {
      const n = unsoundOf(rightButUnsound);
      scored.push({
        rank: 0,
        id: report.item.id,
        prompt: report.item.prompt,
        caveat: true,
        reason: `${ARM_LABEL[rightButUnsound.strategy] ?? rightButUnsound.strategy} reached the right answer, and the judge marked ${n === 1 ? "a step" : `${n} steps`} of how it got there as not holding up.`,
      });
    } else if (wrongAndUnsound) {
      scored.push({
        rank: 1,
        id: report.item.id,
        prompt: report.item.prompt,
        caveat: true,
        reason: `${ARM_LABEL[wrongAndUnsound.strategy] ?? wrongAndUnsound.strategy} got this wrong, and the trace shows which step it went wrong at.`,
      });
    } else if (splits) {
      scored.push({
        rank: 2,
        id: report.item.id,
        prompt: report.item.prompt,
        caveat: false,
        reason: "The three arms do not agree on this one — the traces show where they part.",
      });
    }
  }
  return scored
    .sort((a, b) => a.rank - b.rank || a.id.localeCompare(b.id))
    .slice(0, limit);
}

/**
 * The seeded-error replay entries (FE-11, L3).
 *
 * **A planted-error trace is a third provenance category**, and the project needed a name
 * for it only once M2-6's mutated reports existed. It is not an authored fixture — a real
 * model really produced these labels, on the pinned tier. It is not a clean measurement
 * either — the text it judged was **deliberately edited by us** before it saw it.
 *
 * **The metadata is deliberately kept OUT of the report object.** `Download` promises the
 * downloaded blob is "the `ReasoningReport` itself, unmodified ... it validates against the
 * committed JSON Schema", and the schema sets `additionalProperties: false` at every level
 * — so hanging a `__replay` marker on the report would quietly break that promise and the
 * download with it. The marker lives on the wrapper; the report stays pristine and still
 * validates.
 *
 * Under **L3** these are *labeled bank entries*, not a separate UI mode: they appear in the
 * picker beside everything else, they are served from committed JSON with no live call
 * (C4.8 — this is the surface that survives a provider outage), and they carry a banner
 * that **cannot be dismissed**. A planted error presented without its label is the one
 * thing on this site that would be actively misleading.
 */
const REPLAY_DIR = path.join(process.cwd(), "..", "calibration", "seeded", "reports");

let replayCache = null;

export function replayEntries() {
  if (replayCache) return replayCache;
  if (!fs.existsSync(REPLAY_DIR)) return (replayCache = []);
  replayCache = fs
    .readdirSync(REPLAY_DIR)
    .filter((f) => f.endsWith(".report.json"))
    .map((f) => JSON.parse(fs.readFileSync(path.join(REPLAY_DIR, f), "utf8")))
    .sort((a, b) => a.case_id.localeCompare(b.case_id));
  return replayCache;
}

/** The replay entry for a route id, or null if this id is an ordinary report. */
export function replayFor(caseId) {
  return replayEntries().find((e) => e.case_id === caseId) ?? null;
}
