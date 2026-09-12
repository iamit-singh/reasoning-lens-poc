# Reasoning Lens -- developer entry points.
# Targets marked STUB are wired from W1 (M1-0) so CI, the Makefile and the docs all
# address the same names from the start; their bodies land with the task named.

PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
ANALYZER := analyzer

.DEFAULT_GOAL := help
.PHONY: help venv install lint typecheck test unit contract integration-mock \
        boundaries schema-freeze rubric-drift calibration-page backend-tests serve-api wheel seeded-errors trip-breaker reset-breaker label draw-sample fe-install fe-build fe-build-measured fe-dev ci warm-cache calibrate faithfulness faithfulness-check smoke \
        record-cassettes classify-reliability taxonomy-coverage confidence-histogram report spans traps arm-contrast spike-s1 spike-s3 spike-s4 spike-s6 spike-s2 spike-deps models pin-local \
        serve-local demo clean

help:  ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

venv:  ## create the local virtualenv
	$(PY) -m venv $(VENV)

install: venv  ## install the analyzer plus dev tooling
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e "$(ANALYZER)[dev]"

# ---------------------------------------------------------------- every-PR jobs (C7.2)
# ruff.toml says "one source of truth so analyzer, backend, scripts and spikes are held
# to the same rules" -- so lint the repo, not just the analyzer. M1-5 found this checking
# only $(ANALYZER) while claiming otherwise, which meant the spike harnesses were
# unlinted. Verified clean across all 52 files at the point it was widened.
lint:  ## ruff, repo-wide (see ruff.toml)
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

typecheck:  ## mypy (strict)
	cd $(ANALYZER) && ../$(BIN)/mypy

unit:  ## deterministic unit tests, no LLM
	cd $(ANALYZER) && ../$(BIN)/pytest -q -m "not contract and not integration_mock and not measurement"

contract:  ## data-contract tests (span trees, ReasoningReport schema)
	cd $(ANALYZER) && ../$(BIN)/pytest -q -m contract

integration-mock:  ## full pipeline under MOCK_LLM=1, cassette replay only
	MOCK_LLM=1 ./scripts/run_marker.sh integration_mock

boundaries:  ## C2.2 boundary contract: import-linter + provider-symbol grep
	cd $(ANALYZER) && ../$(BIN)/lint-imports --config ../.importlinter
	./scripts/check_provider_symbols.sh

schema-freeze:  ## C5.4 held-out set protection
	./scripts/check_heldout_freeze.sh

rubric-drift:  ## C5.3 -- the taxonomy block must be byte-identical in prompt and rubric
	./scripts/check_rubric_drift.sh

calibration-page:  ## E9 -- the calibration page hard-codes no numbers
	./scripts/check_calibration_page.sh

ci: lint typecheck unit contract backend-tests faithfulness-check integration-mock boundaries schema-freeze rubric-drift calibration-page  ## everything a PR runs

# ---------------------------------------------------------------- measurement & ops
warm-cache:  ## STUB (M3-2) -- run the bank x arms for keys invalidated by C2.3
	@echo "warm-cache: not implemented (owner M3-2). CACHE_KEY inputs: see analyzer/src/rlens/versions.py"; exit 2

calibrate:  ## M2-13 -- kappa, CIs, per-class F1, baseline. --final is C5.4-guarded
	cd $(ANALYZER) && ../$(BIN)/python -m rlens.calibrate $(ARGS)

# M2-9, as ADR-009 re-scoped it: 3.5 h -> ~1.0 h. The panel is BUILT and SHIPPED, and what
# it publishes is the negative result with its denominator. No model call: this reads S4's
# committed trial records, whose adjudication is an INPUT rather than a step.
faithfulness:  ## M2-9 -- build faithfulness/panel.json from S4's records (no network)
	$(BIN)/python scripts/build_faithfulness_panel.py $(ARGS)

faithfulness-check:  ## CI -- fail if the committed panel is out of date with S4's records
	$(BIN)/python scripts/build_faithfulness_panel.py --check

backend-tests:  ## C4.9 route-table posture, the spend breaker, cache staleness. No server
	$(BIN)/python -m pytest backend/tests/test_api.py -q

serve-api:  ## run the API against the local cache (ADR-003: localhost, no deployment)
	@set -a; [ -f .env ] && . ./.env; set +a; \
	$(BIN)/python -m uvicorn backend.app:app --host 127.0.0.1 --port $${PORT:-8000}

# M3-1a's DoD in one command. Starts a REAL server WITH NO PROVIDER KEY, smokes it, stops
# it. The key is stripped rather than merely unused: "we did not call it" and "we could
# not call it" are different claims, and only the second proves the fallback product.
smoke:  ## M3-4/M3-1a -- acceptance against a real server, provider key REMOVED
	@set -a; [ -f .env ] && . ./.env; set +a; \
	unset OPENAI_API_KEY; \
	$(BIN)/python -m uvicorn backend.app:app --host 127.0.0.1 --port 8071 >/dev/null 2>&1 & \
	echo $$! > /tmp/rlens-smoke.pid; \
	$(BIN)/python backend/tests/smoke.py --base-url http://127.0.0.1:8071 --no-key; \
	status=$$?; kill $$(cat /tmp/rlens-smoke.pid) 2>/dev/null; rm -f /tmp/rlens-smoke.pid; \
	exit $$status

wheel:  ## M3-8 -- build the analyzer wheel and prove it runs in a CLEAN venv
	@./scripts/clean_venv_proof.sh

seeded-errors:  ## M2-6 -- judge recall on 10 seeded errors, correct-step rule. COSTS SPEND
	@set -a; [ -f .env ] && . ./.env; set +a; unset MOCK_LLM; \
	$(BIN)/python spikes/m2_6_seeded_errors.py $(ARGS)

trip-breaker:  ## M3-3's DoD -- force the spend breaker through the real code path
	@$(BIN)/python -c "from backend import breaker; breaker.trip('make trip-breaker'); print(breaker.check().reason)"

reset-breaker:  ## clear the spend total
	@$(BIN)/python -c "from backend import breaker; breaker.reset(); print('reset:', breaker.check().reason)"

# The PIN has to come from .env, and that is worth a note rather than a silent source.
# The pin tuple is EVIDENCE (C2.3/I3: a published number is reproducible or it is not
# published) and it lives in a gitignored file, because `.env` mixes it with a real
# OPENAI_API_KEY. M1-15 already hit this and worked around it by duplicating the tuple
# into ADR-001 as prose. The consequence surfaces here: on a fresh checkout `make spans`
# replays the cassettes correctly but stamps an EMPTY pin, and the runner's own warning
# ("traces from this run are NOT publishable") is the only thing that says so. Splitting
# the non-secret pin into a committed file belongs with M1-14, which owns replay.
spans:  ## regenerate out/spans from the committed cassettes -- no GPU, no network
	@rm -rf out/spans && mkdir -p out/spans
	@set -a; [ -f .env ] && . ./.env; set +a; \
	for f in problem-bank/items/*.json; do \
	  id=$$(basename $$f .json); \
	  MOCK_LLM=1 $(BIN)/python -m rlens.runner --item $$id --all-arms --out out/spans \
	    >/dev/null 2>&1 || echo "  regenerate FAILED for $$id"; \
	done
	@echo "out/spans: $$(ls out/spans | wc -l | tr -d ' ') span trees replayed from cassettes"

# ---------------------------------------------------------------- calibration (M1-11)
draw-sample:  ## M1-11 -- draw the random-90. Runs ONCE, before the first label (Hazard 2)
	$(BIN)/python scripts/draw_sample.py $(ARGS)

label:  ## M1-11 -- the BLIND labelling tool. Two labels per step, one pass (C5.2)
	$(BIN)/python scripts/label.py $(ARGS)

confidence-histogram:  ## M2-4 -- is validity_confidence a signal or decoration? (ADR-002)
	$(BIN)/python spikes/m2_4_confidence.py $(ARGS)

taxonomy-coverage:  ## M1-9 -- does the CORPUS contain the behaviours? No model, no network
	$(BIN)/python spikes/m1_9_taxonomy_coverage.py $(ARGS)

traps:  ## M1-5 -- measure which declared traps reproduce. Needs the served model.
	$(BIN)/python spikes/m1_5_trap_reproduction.py $(ARGS)

arm-contrast:  ## ADR-004's control group: which items separate the arms? Needs the model.
	$(BIN)/python spikes/m1_5_arm_contrast.py $(ARGS)

record-cassettes:  ## M1-14 -- record provider responses once per prompt-bundle version
	@set -a; [ -f .env ] && . ./.env; set +a; MOCK_LLM=0 $(BIN)/python scripts/record_cassettes.py $(ARGS)

classify-reliability:  ## M1-9's DoD -- parse-failure rate over N full passes. COSTS SPEND.
	@set -a; [ -f .env ] && . ./.env; set +a; MOCK_LLM=0 $(BIN)/python spikes/m1_9_parse_reliability.py $(ARGS)

report:  ## the end-to-end pipeline: span trees -> ReasoningReport (MOCK_LLM=1 for offline)
	@set -a; [ -f .env ] && . ./.env; set +a; cd $(ANALYZER) && ../$(BIN)/python -m rlens --spans ../out/spans --out ../out/reports $(ARGS)

# ---------------------------------------------------------------- frontend (C4.10)
FRONTEND := frontend

fe-install:  ## install the frontend toolchain
	cd $(FRONTEND) && npm install --no-audit --no-fund

fe-build:  ## FE-1+ -- static export against the COMMITTED FIXTURES. No backend, no network
	cd $(FRONTEND) && npm run build

fe-build-measured:  ## static export against out/reports -- what the demo ships (M3)
	cd $(FRONTEND) && npm run build:measured

fe-dev:  ## the frontend dev server, fixtures-first
	cd $(FRONTEND) && npm run dev

# ---------------------------------------------------------------- local runtime (ADR-001)
models:  ## pull the local generation model
	ollama pull $${LOCAL_MODEL:-gpt-oss:20b}

serve-local:  ## serve the local model natively (Metal). Do NOT containerise it on macOS.
	ollama serve

pin-local:  ## record the generation pin tuple -- an id alone does not reproduce a number
	@./scripts/pin_local.sh

demo:  ## the demo: cached-only, zero external dependency
	DEMO_MODE=cached docker compose up

# ---------------------------------------------------------------- spikes
spike-s1:  ## S1 -- reasoning-trace fidelity: local (gates arm 2) + OpenAI
	$(BIN)/python spikes/s1_reasoning_fidelity.py $(ARGS)

spike-s3:  ## S3 -- batched classification. DECIDES M1-9's batch size; gates the freeze.
	$(BIN)/python spikes/s3_batching.py $(ARGS)

spike-s6:  ## S6 -- local tool-calling reliability. GATES ARM 3; run before W3.
	$(BIN)/python spikes/s6_local_tool_calling.py $(ARGS)

spike-s4:  ## S4 -- cue-injection reproducibility. Go/no-go for M2-9's faithfulness study.
	@set -a; [ -f .env ] && . ./.env; set +a; MOCK_LLM=0 $(BIN)/python spikes/s4_cue_injection.py $(ARGS)

spike-deps:  ## install the spike-only deps (langgraph, instrumentor) -- NOT analyzer deps
	$(BIN)/pip install -q -r spikes/requirements-s2.txt

spike-s2: spike-deps  ## S2 -- OTEL attribute shape from a STOCK LangGraph agent
	$(BIN)/python spikes/s2_otel_shape.py $(ARGS)

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
