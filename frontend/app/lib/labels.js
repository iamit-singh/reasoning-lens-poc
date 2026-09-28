/**
 * Constants shared by server and client components.
 *
 * **Separate from `reports.js` on purpose.** That module reads the filesystem at build time,
 * and a client component importing anything from it drags `node:fs` into the browser bundle
 * — which is exactly how the first build of FE-1 failed. Keeping the values a client needs
 * in a module with no Node imports makes the boundary a property of the file tree rather
 * than something to remember.
 */

export const ARM_LABEL = {
  direct: "Direct",
  thinking: "Extended thinking",
  react: "ReAct + tools",
};

export const BEHAVIOR_CLASSES = [
  "verification",
  "backtracking",
  "subgoal_setting",
  "backward_chaining",
  "linear",
];

/**
 * Trim a JSON-serialisation artifact off the tail of a judge rationale — E12-D6.
 *
 * Two of five naive testers spotted a stray `"}` rendered at the end of mb-06's ReAct
 * consistency line. Both diagnosed it as the page string-concatenating instead of
 * serialising. THEY WERE WRONG, AND THE TRUE CAUSE IS WORSE: the characters are inside the
 * judge model's own `rationale` value, in the stored report. The model emitted a fragment
 * of its own JSON envelope into a prose field and the parser accepted it, so what shipped
 * is a faithful rendering of a malformed measurement.
 *
 * That makes this a display repair over a data defect, and the split is deliberate:
 *
 *   - THE STORED REPORT IS NOT EDITED. It is what the judge returned, and rewriting a
 *     model's recorded output to look tidier is the one thing this project must not do to
 *     its own evidence. `out/reports/` still contains the artifact, and a reader who
 *     downloads the report — which the page offers, byte-identical, by design — gets it.
 *   - THE PAGE STOPS SHOWING PUNCTUATION THE JUDGE DID NOT MEAN. On a surface whose pitch
 *     is "every number renders beside its provenance", one leaked brace does more damage
 *     than its size warrants; one tester said it made them wonder what else was unpolished.
 *
 * Conservative on purpose: it strips only quote/brace/bracket characters that trail a
 * sentence-ending mark, so prose that legitimately ends in a quotation is untouched. The
 * real fix is upstream — the judge's output should be validated so this never reaches a
 * report — and that is filed rather than done here, because it is a pipeline change and
 * this is a rendering one.
 */
export function cleanRationale(text) {
  if (typeof text !== "string") return text;
  return text.replace(/([.!?])["'`]*[}\]]+["'`]*\s*$/u, "$1");
}
