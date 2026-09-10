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

# The digest must be the WEIGHTS FILE digest, not ollama's short manifest id.
# ADR-001 is explicit that an id does not reproduce a number and that the value of a local
# pin is precisely that a file digest cannot change under you. `ollama list` prints a
# 12-char truncated manifest id -- too weak to be the pin. The modelfile's FROM line
# carries the full sha256 of the actual model artifact.
digest=$(ollama show "$MODEL" --modelfile 2>/dev/null \
  | awk '/^FROM/ {print $2; exit}' \
  | sed -n 's|.*/sha256-\([0-9a-f]\{64\}\)$|sha256:\1|p')
short_id=$(ollama list 2>/dev/null | awk -v m="$MODEL" '$1==m {print $2}' | head -1)
quant=$(printf '%s\n' "$INFO" | awk '/quantization/ {print $2; exit}')
runtime="ollama $(ollama --version 2>/dev/null | awk '{print $NF}')"

echo "# generation pin, recorded $(date -u +%Y-%m-%dT%H:%M:%SZ) by scripts/pin_local.sh"
echo "LOCAL_MODEL=$MODEL"
echo "LOCAL_MODEL_DIGEST=${digest:-UNKNOWN}"
echo "LOCAL_MODEL_SHORT_ID=${short_id:-UNKNOWN}"   # convenience only -- NOT the pin
echo "LOCAL_QUANTIZATION=${quant:-UNKNOWN}"
# Quoted: this value contains a space. Unquoted it truncates to "ollama" when .env is
# sourced, and the shell tries to execute the version number -- a pin field that corrupts
# itself on load is worse than a missing one, because it looks recorded.
echo "LOCAL_RUNTIME=\"$runtime\""
echo
echo "# Sampling settings are part of the pin too -- set them explicitly, never by default:"
echo "GEN_TEMPERATURE=${GEN_TEMPERATURE:-0}"
echo "GEN_TOP_P=${GEN_TOP_P:-1.0}"
echo "GEN_SEED=${GEN_SEED:-20260910}"
echo "LOCAL_REASONING_EFFORT=${LOCAL_REASONING_EFFORT:-medium}"
echo
echo "# The tokenizer is part of the pin (G0 check 2): reasoning tokens are counted"
echo "# locally because the runtime does not report them. Counting one model's text with"
echo "# another model's encoding yields a plausible WRONG number, so this travels with"
echo "# the model. gpt-oss = o200k_harmony; the qwen3 fallback would need a different one."
echo "LOCAL_TOKENIZER=${LOCAL_TOKENIZER:-o200k_harmony}"

if [ "${digest:-UNKNOWN}" = "UNKNOWN" ] || [ "${quant:-UNKNOWN}" = "UNKNOWN" ]; then
  echo >&2
  echo "pin-local: WARNING -- could not discover every field. A report built on an" >&2
  echo "incomplete pin is not reproducible; fill the gaps by hand before publishing" >&2
  echo "any number from it." >&2
  exit 1
fi
