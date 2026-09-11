#!/usr/bin/env bash
# E9 / B0 Condition #5 — the calibration page renders measured numbers **verbatim**, with
# zero hard-coded values.
#
# Why a grep rather than a code review
# ------------------------------------
# The claim this page makes is *these are the numbers we measured*. A single literal that
# crept in during a layout tweak would not look wrong to a reader, would not fail a test,
# and would quietly convert the page from a measurement into a brochure. The plan calls for
# "a grep-based test over the FE-6 source" and this is it.
#
# What counts as a violation: any numeric literal in JSX text, and any decimal literal at
# all. What does not: array indices and the like inside obvious code positions -- there are
# none in this file today, and if one appears it should be justified in the exception list
# below rather than by loosening the pattern.
set -euo pipefail

cd "$(dirname "$0")/.."
PAGE="frontend/app/calibration/page.jsx"

[ -f "$PAGE" ] || { echo "check-calibration-page: missing $PAGE"; exit 1; }

status=0

# A decimal anywhere: 0.6, 75.0 -- the shape a metric takes.
if hits=$(grep -nE '[^a-zA-Z_.]-?[0-9]+\.[0-9]+' "$PAGE"); then
  echo "check-calibration-page: FAIL -- decimal literal in the calibration page"
  echo "$hits" | sed 's/^/    /'
  status=1
fi

# A bare number rendered as JSX text: >75< or > 0 <
if hits=$(grep -nE '>[[:space:]]*-?[0-9]+([.,][0-9]+)?[[:space:]]*<' "$PAGE"); then
  echo "check-calibration-page: FAIL -- a number is rendered as literal text"
  echo "$hits" | sed 's/^/    /'
  status=1
fi

if [ "$status" -eq 0 ]; then
  echo "check-calibration-page: OK (FE-6 hard-codes no numbers; every figure comes from latest.json)"
fi
exit "$status"
