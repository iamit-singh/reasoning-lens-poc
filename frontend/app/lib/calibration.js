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

const GATE_FILE = path.join(process.cwd(), "..", "calibration", "gate-thresholds.json");

/**
 * C1.3's branch thresholds, read from a committed file rather than typed here.
 *
 * E9's grep forbids a numeric literal in the calibration page source and it is right to: a
 * threshold typed into JSX is a second copy of a plan decision that can drift from the plan
 * without anyone noticing. These are gate CONSTANTS, not measurements -- nothing in that
 * file was measured, and nothing in it may be edited to make a measurement pass.
 */
export function gateThresholds() {
  return JSON.parse(fs.readFileSync(GATE_FILE, "utf8"));
}
