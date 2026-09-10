# S6 — Local tool-calling reliability

| | |
| --- | --- |
| **Task** | M1-16 · W2 · 0.5 h · **Gate G0 check 3** · *added by [amendment 001](../../../plan-amendment-001-local-hybrid.md)* |
| **Status** | **Run 10 Sep 2026. PASS — 20/20.** Arm 3 is buildable on the local model |
| **Decision doc** | [`../decisions/ADR-001-provider.md`](../decisions/ADR-001-provider.md) |
| **Harness** | `spikes/s6_local_tool_calling.py` · `make spike-s6` |

## The question

Can the local model call a calculator and a lookup function correctly and **repeatably** —
not once, but every time an agent loop needs it?

Arm 3 is a tool-using agent, and ADR-001's same-model rule forbids moving it to OpenAI to
get better tool calling: the three arms compare reasoning *strategies*, so different models
per arm would measure vendors instead and the finding would evaporate. That makes local tool
calling a **hard dependency of arm 3**, not a nice-to-have.

## Method

4 scenarios × 5 runs at temperature 0. A call passes only if the right tool is named **and**
its arguments parse as valid, non-empty JSON — malformed arguments are the characteristic
failure of weaker models (correct tool name, payload that is prose or truncated JSON), and
counting those as passes would make the spike useless.

## Result — pin as run

| | |
| --- | --- |
| Model | `gpt-oss:20b` |
| Digest | `sha256:e7b273f9636059a689e3ddcab3716e4f65abe0143ac978e46673ad0e52d09efb` |
| Quantization | MXFP4 |
| Runtime | ollama 0.33.3, served natively (Metal) |
| Sampling | temperature 0, top_p 1.0, seed 20260910, reasoning effort medium |

| Scenario | Pass rate | What it tests | Representative call |
| --- | --- | --- | --- |
| `calculator-forced` | **5/5 · 100%** | Basic compliance | `calculator{"expression": "(7*90+43)*12"}` |
| `lookup-forced` | **5/5 · 100%** | The second tool, and a string argument | `lookup{"key": "carton_size"}` |
| `tool-choice` | **5/5 · 100%** | The model must **decide** which tool, not just comply | `calculator{"expression": "(90*12)*7"}` |
| `no-tool-needed` | **5/5 · 100%** | False positives — a model that calls tools when none are needed derails the loop just as effectively | no tool called, as required |

**Worst scenario: 100%, against a 90% threshold.** Every one of the 20 attempts produced a
correctly named tool with valid, non-empty JSON arguments. There were no malformed-argument
failures — the specific failure this spike was built to catch.

> **`tool-choice` is the result worth reading.** The other three scenarios can be passed by
> pattern-matching an instruction. This one gives the model a word problem and two tools and
> requires it to pick. It chose `calculator` five times out of five, and expressed the
> arithmetic correctly each time — with a different but equivalent grouping than the forced
> scenario used (`(90*12)*7` vs `(7*90+43)*12`), i.e. it composed the expression from the
> problem rather than echoing a template.

## Consequences

- **Arm 3 proceeds as designed** (M1-7, W3). The approved fallback `qwen3:14b` is **not**
  needed, and the pin does not change.
- **The two-arm contingency is not exercised.** ADR-001's failure ladder ends at "drop to a
  two-arm comparison and say so plainly"; that branch is closed for now.
- **The rejection of the R1-class distill is retrospectively cheap.** The plan named an
  R1 distill for arm 2; those models reason well and fumble the call format. This spike
  cost half an hour and would have cost a rebuilt arm in W3.
- **This is not a licence to skip tool-error handling in M1-7.** 20/20 at temperature 0 on
  four short prompts is evidence about the *format contract*, not about a long agent loop
  with tool results fed back in. The runner still needs a malformed-call path.

## Raw output

`docs/spikes/S6-raw/s6-results.json` — every attempt, with the pass reason recorded per
call. Gitignored (`docs/spikes/*-raw/`): regenerable with `make spike-s6`, and the written
finding above is what gets committed.
