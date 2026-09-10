#!/usr/bin/env bash
# Run a pytest marker, treating "no tests collected" (exit 5) as a pass with a loud
# notice. Lets the every-PR job set be wired from W1 while the tests behind a marker
# are still owned by a later task -- the job is real, and its emptiness is visible.
set -uo pipefail
cd "$(dirname "$0")/../analyzer"
MARKER="$1"; shift || true
../.venv/bin/pytest -q -m "$MARKER" "$@"
code=$?
if [ "$code" -eq 5 ]; then
  echo "run-marker: 0 tests collected for marker '$MARKER'."
  case "$MARKER" in
    integration_mock) echo "run-marker: expected until M1-6/M1-14 (cassettes). Job is wired, not yet exercised." ;;
    *) echo "run-marker: no owner recorded for this marker -- check C7.1." ;;
  esac
  exit 0
fi
exit "$code"
