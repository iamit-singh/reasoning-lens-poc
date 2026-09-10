# Reasoning Lens -- developer entry points.
# Targets marked STUB are wired from W1 (M1-0) so CI, the Makefile and the docs all
# address the same names from the start; their bodies land with the task named.

PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin
ANALYZER := analyzer

.DEFAULT_GOAL := help
.PHONY: help venv install lint typecheck test unit contract integration-mock \
        boundaries schema-freeze ci warm-cache calibrate faithfulness smoke \
        record-cassettes spike-s1 clean

help:  ## show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'

venv:  ## create the local virtualenv
	$(PY) -m venv $(VENV)

install: venv  ## install the analyzer plus dev tooling
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -e "$(ANALYZER)[dev]"

# ---------------------------------------------------------------- every-PR jobs (C7.2)
lint:  ## ruff
	$(BIN)/ruff check $(ANALYZER)
	$(BIN)/ruff format --check $(ANALYZER)

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

ci: lint typecheck unit contract integration-mock boundaries schema-freeze  ## everything a PR runs

# ---------------------------------------------------------------- measurement & ops
warm-cache:  ## STUB (M3-2) -- run the bank x arms for keys invalidated by C2.3
	@echo "warm-cache: not implemented (owner M3-2). CACHE_KEY inputs: see analyzer/src/rlens/versions.py"; exit 2

calibrate:  ## STUB (M2-1/M2-3) -- kappa and per-class F1; --dev on PRs, --final pre-release
	@echo "calibrate: not implemented (owner M2-1). Refuses --final unless the prompt bundle is pinned (C5.4)"; exit 2

faithfulness:  ## STUB (M2-9) -- cue-injection batch job and the committed panel
	@echo "faithfulness: not implemented (owner M2-9). See docs/spikes/S4-cues.md"; exit 2

smoke:  ## STUB (M3-4) -- post-deploy: 3 items from cache, panel, calibration, download, breaker trip
	@echo "smoke: not implemented (owner M3-4). Lives in backend/tests/smoke.py"; exit 2

record-cassettes:  ## STUB (M1-14) -- record provider responses once per prompt-bundle version
	@echo "record-cassettes: not implemented (owner M1-14, W4). This is the frontend's W5 unblock (E11)"; exit 2

spike-s1:  ## S1 (M1-1) -- provider thinking-trace fidelity probe; needs a live API key
	$(BIN)/python spikes/s1_provider_fidelity.py $(ARGS)

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
