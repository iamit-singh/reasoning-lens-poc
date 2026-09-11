#!/usr/bin/env bash
# C2.2 rule 2, grep half: no provider-specific payload shapes outside llm.py and
# ingest/otel.py. import-linter catches *imports*; this catches string literals,
# dict keys and comments that encode a provider's response shape.
set -euo pipefail

cd "$(dirname "$0")/.."
TARGETS="analyzer/src/rlens/segment.py analyzer/src/rlens/classify.py analyzer/src/rlens/judge.py analyzer/src/rlens/consistency.py"
# Word-bounded. M1-9 found the unanchored version failing on the English word
# "coherently", which contains `cohere` -- a check that fires on prose is a check people
# start working around, and the next thing worked around is a real hit. The boundaries
# cost nothing: every symbol here is a whole identifier wherever it actually appears.
PATTERN='\b(anthropic|Anthropic|openai|OpenAI|google\.generativeai|mistralai|cohere|ollama|thinking_blocks|redacted_thinking|reasoning_content)\b'

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
