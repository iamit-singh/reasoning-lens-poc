#!/usr/bin/env bash
# C5.3 / §6.4 — the taxonomy block in `calibration/rubric.md` and the one in the classifier
# prompt must be BYTE-IDENTICAL.
#
# Why this is a build failure and not a convention
# ------------------------------------------------
# Cohen's kappa compares a human's labels against the classifier's. If the two were given
# differently worded definitions, kappa measures the difference in wording -- and it
# measures it as though it were classifier quality, which is the single number this PoC
# publishes. The drift would be invisible: both files would read sensibly, the number would
# come out lower, and the obvious explanation ("the classifier is mediocre") would be wrong.
#
# The plan calls this "the cheapest defence" and it is: one diff, on every PR.
#
# **This lives in scripts/ rather than in the analyzer's test suite on purpose.** I1 makes
# the analyzer a standalone pip package whose tests must pass without the rest of the repo;
# a pytest case reaching up to `../../calibration/` would break that the first time somebody
# installed the wheel and ran its tests.
set -euo pipefail

cd "$(dirname "$0")/.."

PROMPT="analyzer/src/rlens/prompts/classify_and_triage.md"
RUBRIC="calibration/rubric.md"
BEGIN="<!-- BEGIN TAXONOMY -->"
END="<!-- END TAXONOMY -->"

extract() {
  # The block BETWEEN the markers, exclusive. `sed` ranges are inclusive, so the markers
  # are dropped explicitly rather than by counting lines -- a line count would silently
  # drift the moment either file gained a line.
  sed -n "/$BEGIN/,/$END/p" "$1" | sed '1d;$d'
}

for f in "$PROMPT" "$RUBRIC"; do
  [ -f "$f" ] || { echo "check-rubric-drift: missing $f"; exit 1; }
  if ! grep -qF "$BEGIN" "$f" || ! grep -qF "$END" "$f"; then
    echo "check-rubric-drift: FAIL $f has no taxonomy block"
    echo "    expected the markers $BEGIN / $END"
    exit 1
  fi
done

a=$(extract "$PROMPT")
b=$(extract "$RUBRIC")

if [ -z "$a" ]; then
  # An empty block on both sides would compare equal and assert nothing. The check has to
  # be able to fail before it is worth passing.
  echo "check-rubric-drift: FAIL the taxonomy block is empty"
  exit 1
fi

if [ "$a" != "$b" ]; then
  echo "check-rubric-drift: FAIL the taxonomy has drifted"
  echo "    $PROMPT (classifier) vs $RUBRIC (human annotator)"
  echo "    Kappa would measure this difference AS classifier quality. Edit both or neither."
  diff <(printf '%s\n' "$a") <(printf '%s\n' "$b") | sed 's/^/    /' || true
  exit 1
fi

lines=$(printf '%s\n' "$a" | wc -l | tr -d ' ')
echo "check-rubric-drift: OK ($lines lines identical in prompt and rubric)"
