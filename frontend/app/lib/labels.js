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
