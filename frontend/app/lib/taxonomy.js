import fs from "node:fs";
import path from "node:path";

/**
 * The five behavior definitions, parsed out of `calibration/rubric.md` at build time.
 *
 * **FE-2's DoD says the hover definitions must match `rubric.md` verbatim, and the cheapest
 * way to satisfy a "verbatim" requirement is to never write a second copy.** The rubric's
 * taxonomy block is already byte-identical to the classifier prompt — `check_rubric_drift.sh`
 * fails the build otherwise — so parsing it here makes the UI a third reader of one source
 * rather than a third place the wording can drift.
 *
 * The alternative, a hard-coded object with a CI check comparing it to the rubric, was
 * considered and rejected: it is more code, it fails later, and it still lets the two
 * disagree in the window between the edit and the build.
 *
 * If the markers are ever missing this throws rather than falling back to a stub. A tooltip
 * quietly showing a placeholder definition is worse than a failed build, because the failure
 * mode is a reviewer reading the wrong rule off the screen.
 */

const RUBRIC = path.join(process.cwd(), "..", "calibration", "rubric.md");
const BEGIN = "<!-- BEGIN TAXONOMY -->";
const END = "<!-- END TAXONOMY -->";

let cache = null;

export function taxonomy() {
  if (cache) return cache;

  const text = fs.readFileSync(RUBRIC, "utf8");
  const start = text.indexOf(BEGIN);
  const stop = text.indexOf(END);
  if (start === -1 || stop === -1) {
    throw new Error(
      `No taxonomy block in ${RUBRIC}. FE-2's definitions are parsed from it so they cannot ` +
        `drift from the classifier prompt; a stub here would put the wrong rule on screen.`
    );
  }
  const block = text.slice(start + BEGIN.length, stop);

  // Lines look like `  verification       — definition...`, with continuations indented
  // further and carrying no em dash of their own.
  const entries = [];
  for (const line of block.split("\n")) {
    const m = /^ {2}(\w+)\s+—\s+(.*)$/.exec(line);
    if (m) {
      entries.push({ label: m[1], definition: m[2].trim() });
    } else if (entries.length && /^\s{6,}\S/.test(line) && !line.includes("—")) {
      entries[entries.length - 1].definition += " " + line.trim();
    }
  }

  const behaviors = Object.fromEntries(
    entries
      .filter((e) =>
        ["verification", "backtracking", "subgoal_setting", "backward_chaining", "linear"].includes(
          e.label
        )
      )
      .map((e) => [e.label, e.definition])
  );
  const soundness = Object.fromEntries(
    entries
      .filter((e) => ["sound", "unsound", "unverifiable"].includes(e.label))
      .map((e) => [e.label, e.definition])
  );

  if (Object.keys(behaviors).length !== 5) {
    throw new Error(
      `Parsed ${Object.keys(behaviors).length} of 5 behavior definitions from rubric.md. ` +
        `The block's shape changed; fix the parser rather than shipping partial tooltips.`
    );
  }

  cache = { behaviors, soundness };
  return cache;
}
