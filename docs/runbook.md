# Runbook

## Local development

```
make install PY=python3.12     # venv + analyzer[dev]
make ci                        # everything a PR runs
```

`MOCK_LLM=1` is the default in `docker-compose.yml` and in CI: local dev and CI are
**deterministic and cost-free** by construction (C7.1). Cassettes are recorded once per
prompt-bundle version by `make record-cassettes` (owner: M1-14).

```
docker compose up              # + redis, MOCK_LLM=1, DEMO_MODE=cached
```

## The every-PR job set (C7.2)

| Job | Command | Owner if it fails |
| --- | --- | --- |
| lint (ruff) | `make lint` | whoever pushed |
| lint (mypy, strict) | `make typecheck` | whoever pushed |
| lint (eslint) | `cd frontend && npm run lint` | whoever pushed |
| unit | `make unit` | whoever pushed |
| contract | `make contract` | **stop** — a data contract moved |
| integration-mock | `make integration-mock` | check cassettes are current for `PROMPT_BUNDLE_VERSION` |
| import-linter boundaries | `make boundaries` | **I1 escalation** — not an implementer-level decision |
| schema-freeze | `make schema-freeze` | **stop** — someone edited the held-out labels |
| prompt-bundle version | reported in CI | bump and re-record cassettes |

## The two switches that stop spend

| Switch | Effect |
| --- | --- |
| `DEMO_MODE=cached` | serve cache + faithfulness panel only, **zero LLM spend**. The kill switch (B7.4) |
| `SPEND_BREAKER_USD=150` | hard flip to `cached` (B7.2) |

## Version discipline (C2.3)

`CACHE_KEY = sha256(item_id, strategy, RUNNER_VERSION, MODEL_PIN, ANALYZER_VERSION, PROMPT_BUNDLE_VERSION)`

A change to any of the four invalidates the cache and requires a warm-cache run. **A change
to `MODEL_PIN` additionally requires re-running the calibration harness and the faithfulness
batch job** (B7.4) — κ and hint-verbalisation rates are model-version-specific. `MODEL_PIN`
is always an exact dated id; `rlens.versions.model_pin()` refuses to be absent and the S1
harness refuses to probe an alias.

## Deploy (C7.3)

No manual gate, no staging tier (B0 Condition #2). Merge to main → build → ECR (tag = git
sha) → App Runner → wait healthy → smoke → on failure, automatic redeploy of the previous
image tag + alert. Owner: M3-4.
