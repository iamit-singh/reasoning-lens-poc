import fs from "node:fs";
import path from "node:path";

/**
 * The published calibration numbers, read from `calibration/results/latest.json`.
 *
 * **FE-6 renders this verbatim and hard-codes nothing** (C4.10, E9). That is checked by a
 * grep over the component source in Month 3, and it is the reason this module returns the
 * parsed file rather than a tidied view of it: a "helpful" transformation here is a number
 * the page shows that the file does not contain.
 *
 * In Month 3 the backend serves the same bytes at `/api/calibration`. Until FE-9 wires that
 * seam the file is read at build time, which is the same contract with one fewer moving
 * part — and it is why the static export can show real calibration numbers with nothing
 * running.
 */

const LATEST = path.join(process.cwd(), "..", "calibration", "results", "latest.json");

export function calibration() {
  if (!fs.existsSync(LATEST)) return null;
  return JSON.parse(fs.readFileSync(LATEST, "utf8"));
}
