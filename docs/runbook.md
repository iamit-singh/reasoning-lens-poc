# Runbook

## Local development

```
make install PY=python3.12     # venv + analyzer[dev]
make ci                        # everything a PR runs -- no model, no key, no network
```

## The local generation model

```
make models        # ollama pull gpt-oss:20b  (~13 GB)
make serve-local   # ollama serve
make pin-local     # record the pin tuple -> paste into .env
```

**Serve it natively, never in Docker.** Containerised inference on macOS loses Metal, and a
20B model on CPU is unusable. Compose reaches the host model at `host.docker.internal`.

**If it is too slow to iterate against**, switch to the approved fallback `qwen3:14b`
(~9 GB, roughly twice the speed). Update the pin tuple; nothing structural changes.

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

## `DEMO_MODE=cached` — now the demo-safety switch

It was a spend control. Generation is local and free, so its job changed: it guarantees a
**zero-dependency run** when the network, the key or the model is unavailable. That makes it
more useful than before, not less — a local demo has more single points of failure than a
hosted one, not fewer.

Run the demo with `make demo`. The spend guard survives at a token $5/$10, purely against a
runaway loop.

## Version discipline

The cache key covers the item, the strategy, the runner version, the **generation pin
fingerprint**, the **analyzer pin**, the analyzer version, the prompt bundle version, and the
backend choice (`hybrid` / `local`).

The generation pin is a **tuple**, not an id — model, file digest, quantization, runtime,
temperature, top_p, seed, reasoning effort. An id alone does not reproduce a local number:
the same tag can be re-pulled as different weights, and sampling settings change the output.
Each field invalidates the cache on its own, and there is a test asserting exactly that.

`hybrid` and `local` never share cache entries — they are different analyzers, and both are
reported side by side.

**A change to the generation pin also requires re-running calibration and the faithfulness
batch job** — agreement and hint-verbalisation rates are model-specific.

`rlens.versions.analyzer_pin()` refuses to be absent *and* refuses a floating alias: a number
pinned to an alias expires silently.

## Deploy

**There is none.** The demo runs from a laptop ([ADR-003](decisions/ADR-003-hosting.md)): no
domain, no registry, no cloud service, no rollback, no rate limiting, no iframe embed.

What survives: `make smoke` against `localhost` as the acceptance script, a clean-venv
install proof plus the analyzer wheel as the real handover artifact, and a fallback video —
because one laptop is a single point of failure and pretending otherwise is how demos die.
