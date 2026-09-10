#!/usr/bin/env bash
# C2.2 rule 2, grep half: no provider-specific payload shapes outside llm.py and
# ingest/otel.py. import-linter catches *imports*; this catches string literals,
# dict keys and comments that encode a provider's response shape.
set -euo pipefail

cd "$(dirname "$0")/.."
TARGETS="analyzer/src/rlens/segment.py analyzer/src/rlens/classify.py analyzer/src/rlens/judge.py analyzer/src/rlens/consistency.py"
PATTERN='anthropic|Anthropic|openai|OpenAI|google\.generativeai|mistralai|cohere|ollama|thinking_blocks|redacted_thinking|reasoning_content'

status=0
for f in $TARGETS; do
  [ -f "$f" ] || { echo "check-provider-symbols: missing $f"; status=1; continue; }
  if hits=$(grep -nE "$PATTERN" "$f"); then
    echo "check-provider-symbols: FAIL $f"
    echo "$hits" | sed 's/^/    /'
    status=1
  fi
done

if [ "$status" -eq 0 ]; then
  echo "check-provider-symbols: OK (provider shapes confined to llm.py and ingest/otel.py)"
fi
exit "$status"
