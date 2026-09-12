import fs from "node:fs";
import path from "node:path";

/**
 * The faithfulness panel, read at build time — FE-5's data seam.
 *
 * Same rule as `calibration.js`: **the page renders what the file says and computes
 * nothing.** `faithfulness/panel.json` is produced by `make faithfulness` from S4's
 * committed trial records, and every count, label and caveat on the panel comes out of it
 * verbatim. A page that recomputed a flip rate could disagree with the artifact a reviewer
 * downloads, and there would be no way to tell which was right.
 *
 * A missing panel is a real state, not an error. M2-9 may not have run; before it does,
 * FE-5 renders "not yet measured" the same way the calibration page does. C4.10's
 * fixtures-first rule means this must never throw during a build.
 */

const PANEL = path.join(process.cwd(), "..", "faithfulness", "panel.json");

export function faithfulness() {
  try {
    if (!fs.existsSync(PANEL)) return null;
    return JSON.parse(fs.readFileSync(PANEL, "utf8"));
  } catch {
    // A malformed panel renders as absent rather than failing the build. The build is how
    // the demo gets made, and a demo that cannot be built because one optional measurement
    // file has a trailing comma is a worse failure than a page that says "not yet measured".
    return null;
  }
}
