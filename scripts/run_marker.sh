#!/usr/bin/env bash
# Run a pytest marker and refuse to pass on an empty or all-skipped result.
#
# The original version treated "no tests collected" (exit 5) as a pass, so the every-PR
# job set could be wired from W1 while the tests behind a marker were still owned by a
# later task. **That allowance is retired for `integration_mock`**: M1-14 owns the
# cassettes now, and a job that goes green because every test skipped is worse than no job
# -- G1 check 7 reads that green tick as "the pipeline replays offline".
set -uo pipefail
cd "$(dirname "$0")/.."

# `.venv` locally, the environment's own pytest in CI (where `pip install -e` puts it on
# PATH and no .venv exists). The hard-coded venv path made this script fail with 127 in
# every CI run, which exit 5 was never going to rescue.
PYTEST="./.venv/bin/pytest"
[ -x "$PYTEST" ] || PYTEST="pytest"

MARKER="$1"; shift || true
cd analyzer
out=$("$PYTEST" -q -m "$MARKER" -rs "$@" 2>&1)
code=$?
echo "$out"

if [ "$code" -eq 5 ]; then
  case "$MARKER" in
    integration_mock)
      echo "run-marker: FAIL -- 0 tests collected for '$MARKER'. M1-14 owns these; an"
      echo "run-marker: empty job would make G1 check 7 a green tick over nothing."
      exit 1 ;;
    *)
      echo "run-marker: 0 tests collected for '$MARKER' -- no owner recorded, check C7.1."
      exit 0 ;;
  esac
fi
[ "$code" -eq 0 ] || exit "$code"

# Collected AND green, but possibly all skipped. The cassette-dependent tests skip when
# `out/spans` or the analysis cassettes are absent, which is exactly the state a CI job
# forgetting `make spans` would be in -- and it would report success.
if printf '%s' "$out" | grep -qE '^[0-9]+ skipped' ; then
  echo "run-marker: FAIL -- every '$MARKER' test skipped. Run 'make spans' and"
  echo "run-marker: 'make record-cassettes' so the job asserts something."
  exit 1
fi
exit 0
