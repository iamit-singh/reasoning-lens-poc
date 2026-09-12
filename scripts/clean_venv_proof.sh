#!/usr/bin/env bash
# M3-8 — build the analyzer wheel and prove it installs and runs in a CLEAN venv.
#
# **This is the real handover artifact.** Everything else in this repo is a demo of the
# analyzer; the wheel is the thing another team could actually take. I1 says the analyzer
# is a standalone package whose only input is a span tree, and that claim has been enforced
# all project by import-linter — but import-linter checks the source tree, and a package
# can still fail to install, ship a missing data file, or quietly depend on something the
# developer's venv happened to have.
#
# So the proof is a venv with nothing in it but the wheel, in a temp directory outside the
# repo, ingesting a span tree it did not help produce.
#
# The three failures this catches that a passing test suite does not:
#   1. A data file (the JSON Schema, the prompt bundle) not packaged -- works from a source
#      checkout, ImportError or FileNotFoundError from a wheel.
#   2. A dependency that is real but undeclared, satisfied by the dev venv by accident.
#   3. An import that only resolves because `src/` is on the path during development.
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "M3-8: wheel + clean-venv proof"
echo "  work dir: $WORK  (outside the repo on purpose)"

# ---------------------------------------------------------------- build
echo
echo "1. building the wheel"
.venv/bin/pip install -q --upgrade build >/dev/null 2>&1 || true
( cd analyzer && "$ROOT/.venv/bin/python" -m build --wheel --outdir "$WORK/dist" >"$WORK/build.log" 2>&1 ) || {
  echo "   FAILED — build log:"; tail -20 "$WORK/build.log"; exit 1;
}
WHEEL="$(ls "$WORK"/dist/*.whl)"
echo "   $(basename "$WHEEL")  ($(du -h "$WHEEL" | cut -f1))"

# ---------------------------------------------------------------- clean venv
echo
echo "2. installing into a venv with nothing else in it"
python3 -m venv "$WORK/venv"
"$WORK/venv/bin/pip" install -q --upgrade pip >/dev/null
"$WORK/venv/bin/pip" install -q "$WHEEL" >"$WORK/install.log" 2>&1 || {
  echo "   FAILED — install log:"; tail -20 "$WORK/install.log"; exit 1;
}
echo "   installed: $("$WORK/venv/bin/pip" list --format=freeze | wc -l | tr -d ' ') packages total"
"$WORK/venv/bin/pip" list --format=freeze | sed 's/^/     /'

# ---------------------------------------------------------------- run it on a span tree
# The span tree is copied OUT of the repo first. A path back into the checkout would let a
# packaging gap hide behind a file the wheel did not ship.
echo
echo "3. ingesting a span tree, from outside the repo"
cp analyzer/tests/fixtures/spans/langgraph_react_reference.json "$WORK/third_party.json"

cat > "$WORK/proof.py" <<'PY'
"""Does the wheel do the one thing I1 promises: span tree in, segmented steps out?

Deliberately uses the THIRD-PARTY capture -- a stock LangGraph trace this project did not
emit. B12's claim is that the analyzer ingests someone else's spans, and proving it with
our own output would prove something weaker.
"""
import json, sys, pathlib

from rlens.ingest import otel
from rlens.segment import segment
from rlens.contracts import NormalizedTrace

tree = json.loads(pathlib.Path(sys.argv[1]).read_text())
parsed = otel.parse(tree, strategy="react")
trace = segment(parsed)
assert isinstance(trace, NormalizedTrace)
print(f"   strategy={trace.strategy} steps={len(trace.steps)} quality={trace.trace_quality}")
for s in trace.steps[:3]:
    print(f"     {s.step_id:28s} {s.kind:12s} {s.text[:52]!r}")

# The schema must be PACKAGED, not merely present in the source tree. This is failure
# mode 1, and it is the one a test suite run from the checkout cannot see.
from rlens.pipeline import load_schema
schema = load_schema()
assert schema.get("$schema") or schema.get("properties"), "the JSON Schema did not ship"
print(f"   ReasoningReport schema loaded from the wheel: "
      f"{len(schema.get('properties', {}))} top-level properties")

# So must the prompt bundle -- the version is a content hash over it, so an empty bundle
# silently produces a stable, wrong version rather than an error.
from rlens.versions import PROMPT_BUNDLE_VERSION
import rlens.versions as v
bundle = sorted(p.name for p in v._PROMPTS_DIR.glob("*.md"))
assert bundle, "the prompt bundle did not ship -- PROMPT_BUNDLE_VERSION would hash nothing"
print(f"   prompt bundle shipped: {bundle} -> {PROMPT_BUNDLE_VERSION}")
PY

"$WORK/venv/bin/python" "$WORK/proof.py" "$WORK/third_party.json"

# ---------------------------------------------------------------- what must NOT be there
echo
echo "4. the wheel must not drag in a provider SDK"
if "$WORK/venv/bin/python" -c "import openai" 2>/dev/null; then
  echo "   FAIL — openai is installed in the clean venv. C2.2 keeps provider SDKs in the"
  echo "          [providers] extra; a base install that pulls one makes the analyzer's"
  echo "          standalone claim weaker than it reads."
  exit 1
fi
echo "   openai absent, as intended (it is in the [providers] extra)"

echo
echo "M3-8: PASS — the wheel installs clean and ingests a third-party span tree."
