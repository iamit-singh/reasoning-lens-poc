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

# Every page that renders a MEASURED figure, not just FE-6's.
#
# The landing page joined this list when E12's queue #4 put judge precision on the arrival
# screen ("the judge that flagged it is right 64% of the time"). That sentence is the same
# kind of claim the calibration page makes -- *this is a number we measured* -- and it was
# sitting outside the only guard that checks such claims, on the one screen every reader is
# guaranteed to see. It is read from `measurement_context.judge_precision` exactly as FE-6
# reads its own figures; this check is what keeps it that way.
#
# FE-11 already made this mistake once in the other direction, typing C1.3's branch
# thresholds into the JSX as numeric literals, and the grep caught it. It only caught it
# because the file was in scope.
PAGES="frontend/app/calibration/page.jsx frontend/app/page.jsx"

status=0

# ------------------------------------------------------------------ what is NOT a metric
#
# Comments are stripped before any pattern runs. These files cite plan clauses constantly --
# `C11.3`, `C4.10`, `B6.2`, `ADR-006` -- and a doc comment saying "C11.3 asks for a
# server-rendered comparison" is prose about the plan, not a figure on a page. Left in, the
# decimal pattern fires on every one of them, and **a check that cries wolf is a check
# people learn to skip** -- the same argument M2-11's kappa comment makes for refusing to
# call "not yet measured" a failure. Nothing is rendered from a comment, so nothing is lost.
#
# The one value-level exception, stated rather than patterned away, as the header requires:
#
#   95% CI -- the CONFIDENCE LEVEL, which is a constant of the method and not a measurement.
#   `latest.json` records `ci_method` and the interval bounds; the level is the thing those
#   bounds are *of*. Moving it into the data file would make the page read its own units
#   from disk, which is ceremony rather than safety. It is exempted HERE, by name, so that
#   the exception is visible in the guard rather than invisible in a looser regex.
#
# Anything else that looks like a measurement is a failure, including in prose.
strip() {
  sed -E -e 's://[^"]*$::' "$1" \
    | sed -E -e 's:/\*+:\n&:g' \
    | awk 'BEGIN{c=0} /\/\*/{c=1} !c{print} /\*\//{c=0; print ""}' \
    | sed -E -e 's/95[[:space:]]*%[[:space:]]*CI/<CI-LEVEL>/g'
}

for PAGE in $PAGES; do
  [ -f "$PAGE" ] || { echo "check-calibration-page: missing $PAGE"; exit 1; }
  body=$(strip "$PAGE")

  # A decimal anywhere: 0.6, 75.0 -- the shape a metric takes.
  if hits=$(printf '%s\n' "$body" | grep -nE '[^a-zA-Z_.]-?[0-9]+\.[0-9]+'); then
    echo "check-calibration-page: FAIL -- decimal literal in $PAGE"
    echo "$hits" | sed 's/^/    /'
    status=1
  fi

  # A bare number rendered as JSX text: >75< or > 0 <
  if hits=$(printf '%s\n' "$body" | grep -nE '>[[:space:]]*-?[0-9]+([.,][0-9]+)?[[:space:]]*<'); then
    echo "check-calibration-page: FAIL -- a number is rendered as literal text in $PAGE"
    echo "$hits" | sed 's/^/    /'
    status=1
  fi

  # A percentage written as prose: "64%", "0.64 %". The landing page's judge-precision
  # caveat is the reason this pattern exists -- a metric in a sentence is how one most
  # naturally gets typed in, and neither pattern above would see it.
  if hits=$(printf '%s\n' "$body" | grep -nE '[^a-zA-Z_.{(]-?[0-9]+([.][0-9]+)?[[:space:]]*%'); then
    echo "check-calibration-page: FAIL -- a percentage is written as literal text in $PAGE"
    echo "$hits" | sed 's/^/    /'
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo "check-calibration-page: OK (no page hard-codes a number; every figure comes from latest.json)"
fi
exit "$status"
