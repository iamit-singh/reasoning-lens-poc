#!/usr/bin/env bash
# C5.4 overfitting control: calibration/labels/heldout-50.jsonl is git-protected.
# Any PR that modifies it after the freeze commit fails the build.
#
# The freeze commit sha lives in calibration/labels/HELDOUT_FREEZE. Until the
# held-out set is labeled and frozen (M2-1), that file is absent and this check
# reports "not yet frozen" and passes -- loudly, so the absence stays visible.
set -euo pipefail

cd "$(dirname "$0")/.."
MARKER="calibration/labels/HELDOUT_FREEZE"
TARGET="calibration/labels/heldout-50.jsonl"
BASE="${1:-origin/main}"

if [ ! -f "$MARKER" ]; then
  echo "check-heldout-freeze: NOT YET FROZEN (no $MARKER) -- expected until M2-1. Skipping."
  exit 0
fi

FREEZE_SHA=$(grep -oE '^[0-9a-f]{7,40}' "$MARKER" | head -1)
if [ -z "$FREEZE_SHA" ]; then
  echo "check-heldout-freeze: FAIL -- $MARKER exists but names no commit sha."
  exit 1
fi

if git diff --quiet "$FREEZE_SHA" -- "$TARGET"; then
  echo "check-heldout-freeze: OK -- $TARGET unchanged since freeze commit $FREEZE_SHA"
  exit 0
fi

echo "check-heldout-freeze: FAIL -- $TARGET was modified after the freeze commit $FREEZE_SHA."
echo "The held-out set carries the published headline kappa (C5.4). It is opened once,"
echo "after the prompt bundle is frozen, and never edited to make a number look better."
git diff --stat "$FREEZE_SHA" -- "$TARGET" | sed 's/^/    /'
exit 1
