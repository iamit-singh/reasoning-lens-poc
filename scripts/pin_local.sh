#!/usr/bin/env bash
# Record the generation pin tuple (ADR-001).
#
# For a hosted model the pin was an exact dated id. For a local model an id is not enough:
# the same tag can be re-pulled as different weights, and sampling settings change the
# output. So the pin is a tuple, and every field enters the cache key.
#
# Writes the discoverable fields to stdout in .env form. Review, then paste into .env.
set -euo pipefail

MODEL="${LOCAL_MODEL:-gpt-oss:20b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo "pin-local: ollama not found. Install it, then 'make models'." >&2
  exit 2
fi

INFO=$(ollama show "$MODEL" 2>/dev/null) || {
  echo "pin-local: '$MODEL' is not pulled. Run 'make models' first." >&2
  exit 2
}

digest=$(ollama list 2>/dev/null | awk -v m="$MODEL" '$1==m {print $2}' | head -1)
quant=$(printf '%s\n' "$INFO" | awk '/quantization/ {print $2; exit}')
runtime="ollama $(ollama --version 2>/dev/null | awk '{print $NF}')"

echo "# generation pin, recorded $(date -u +%Y-%m-%dT%H:%M:%SZ) by scripts/pin_local.sh"
echo "LOCAL_MODEL=$MODEL"
echo "LOCAL_MODEL_DIGEST=${digest:-UNKNOWN}"
echo "LOCAL_QUANTIZATION=${quant:-UNKNOWN}"
echo "LOCAL_RUNTIME=$runtime"
echo
echo "# Sampling settings are part of the pin too -- set them explicitly, never by default:"
echo "GEN_TEMPERATURE=${GEN_TEMPERATURE:-0}"
echo "GEN_TOP_P=${GEN_TOP_P:-1.0}"
echo "GEN_SEED=${GEN_SEED:-20260910}"
echo "LOCAL_REASONING_EFFORT=${LOCAL_REASONING_EFFORT:-medium}"

if [ "${digest:-UNKNOWN}" = "UNKNOWN" ] || [ "${quant:-UNKNOWN}" = "UNKNOWN" ]; then
  echo >&2
  echo "pin-local: WARNING -- could not discover every field. A report built on an" >&2
  echo "incomplete pin is not reproducible; fill the gaps by hand before publishing" >&2
  echo "any number from it." >&2
  exit 1
fi
