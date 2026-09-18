# The runbook, executed cold — M3-5c

| | |
| --- | --- |
| **Task** | M3-5c · the substitute offered by [amendment 002 §5](../../plan-amendment-002-no-human-capacity.md) |
| **Criterion** | G3 **E13** — *"Runbook written and exercised by another team member"* (C15.1 #7) |
| **Verdict** | **E13 DOES NOT CLOSE.** This is not a peer dry-run and does not become one |
| **Run** | 18 Sep 2026 (W6), from `git clone` of `d3073bb` into a directory outside the repo |
| **Result** | **8 of the runbook's commands did not work as written.** All six procedures now execute cold |

---

## What this is, and the one thing it is not

C15.1 #7 asks for **another team member** to drive the runbook while its author watches.
U2 has no named peer, so amendment 002 §5 offers this instead, with the boundary stated in
advance: *"a cold execution of the runbook from a clean checkout and a fresh venv, reading
nothing but the document, recording every hesitation and every step that required knowledge
not in the text — **not a peer. The agent has read the codebase.**"*

That caveat is load-bearing, so it is worth being precise about what it costs. The thing a
peer dry-run measures is whether the document carries enough for someone who cannot fall
back on knowing the system. **I can fall back.** Every repair below I found by reading
source the document does not point at, and a reader without that option would have stopped
at the first one and asked the author — which is the outcome E13 exists to detect.

So what follows is a **lower bound on the document's defects**, not a measurement of its
sufficiency. A real peer would have found everything here and more, and would have found it
by being stuck rather than by reading `pyproject.toml`.

**It is still worth having**, for one reason: eight of these are not judgement calls or
missing context. They are commands that exit non-zero. A document whose stated procedures
do not run is broken for a peer and for its author alike, and that much this run can
establish on its own.

---

## The protocol

1. `git clone` into `/private/tmp/.../coldrun/`, outside the repo. No `.env`, no `.venv`,
   no `node_modules`, no `out/` — exactly what a new operator gets, because all four are
   gitignored.
2. Execute the runbook top to bottom, **typing what it says**, not what works.
3. On each failure: record the command, the verbatim error, and what the repair required.
4. Fix the cause, then re-run from a *fresh* clone to confirm the fix from zero.

Step 4 is why this took four clones rather than one. Repairing a checkout in place proves
the repair worked on a checkout that had already been repaired.

---

## The eight

Ordered as an operator meets them.

### 1 · The first command of the document

```
$ make install PY=python3.12
pyenv: python3.12: command not found
make: *** [venv] Error 127
```

The Makefile defaults `PY` to `python3`; the runbook overrode it with a value that does not
resolve under pyenv when 3.12 is installed but not shimmed. The obvious next move makes it
worse — `pyenv which python3.12` returns empty, and `make install PY=""` gives:

```
make: m: No such file or directory
```

which is `$(PY) -m venv` with the `$(PY)` gone, and names nothing an operator can act on.

**Fixed:** the runbook no longer passes `PY`. Verified on Python 3.14.7.

### 2 · `make ci` could not pass from `make install` — on any machine but one

```
$ make ci
ImportError while importing test module 'backend/tests/test_api.py'
E   ModuleNotFoundError: No module named 'fastapi'
make: *** [backend-tests] Error 2
```

`make install` installs `analyzer[dev]`. `make ci` runs `backend-tests`. **Nothing in the
repository declared FastAPI, uvicorn or httpx** — not `analyzer/pyproject.toml`, not a
requirements file, nowhere. The author's venv had them from an ad-hoc `pip install` months
earlier, and that venv was the only place `make ci` had ever been green.

**This is M3-8's defect, one level up.** M3-8 found the wheel shipping without its JSON
Schema and its note said *"nothing caught it and nothing could have: from a source checkout
the file is right there, so the whole suite stayed green while the artifact we would hand
over was broken."* The same sentence describes this, with "source checkout" replaced by
"the author's laptop".

And it compounds: **`pr.yml` has no backend job**, so the backend's 47 tests — route-table
posture, the breaker's fail-closed semantics, cache staleness — had never run in CI either.
The undeclared dependency and the missing job hid each other. Adding the job without the
file would have turned CI red; declaring the file without the job would have left the tests
still running nowhere.

**Fixed:** `backend/requirements.txt` exists and `make install` installs it; `pr.yml` gains
a `backend` job. Deliberately *not* an `analyzer[dev]` extra — `.importlinter` enforces
`rlens` never importing `backend`, and putting FastAPI in the analyzer's metadata would
express the forbidden dependency direction in the one file import-linter does not read.

### 3 · `faithfulness-check` was unrunnable by anyone verifying it

```
no S4 records under docs/spikes/S4-raw. Run `make spike-s4` first
```

`.gitignore` excludes `docs/spikes/*-raw/`, with a good reason attached: raw spike output is
regenerable self-test noise, and the finding belongs in the `.md`.

**For S4 that reason does not hold.** S4's records are not self-test output — they are the
*measurement input* `build_faithfulness_panel.py` reads to produce `faithfulness/panel.json`,
the committed artifact behind B4 #6's published **0 of 48 trials flipped**, the negative
result ADR-009 rests on.

Two consequences, both bad:

- `make faithfulness-check` — the command E10's evidence line cites as CI's defence against
  the panel drifting from its source — **could not run anywhere but the author's machine.**
  The check that exists to be verified was the one thing nobody could verify.
- A published headline had its denominator on one laptop, regenerable only by spending
  money against a model that may no longer return what it returned in September.

**Fixed:** `docs/spikes/S4-raw/` is un-ignored and committed — 40 KB for a number somebody
can check — plus the `faithfulness-check` job `make ci` had and no workflow ran.

### 4 · `make ci` was not self-sufficient

`out/` is gitignored, correctly: it is derived, and committing derived data is how a
derivation quietly stops being run. But `contract` and `integration-mock` read span trees
from it, so on a fresh checkout `integration-mock` fails by **skipping**, caught only
because `run_marker.sh` treats a skip in that job as a failure.

`pr.yml` already knew — both jobs carry an explicit *"replay span trees from cassettes"*
step. `make ci` did not, so the runbook's opening pair was green only where `out/` happened
to exist.

**Fixed:** `ci: spans …`. Replay is offline, free, and takes seconds. There was never a
reason for the caller to have to know.

### 5 · No document ever said to create `.env`

`.env` is read by `serve-api`, `smoke`, `spans`, `report`, `calibrate` and every spike
target. It is gitignored, because it holds a real `OPENAI_API_KEY`. **Neither the runbook
nor the README ever tells an operator to create it.** Three of the six procedures fail
without it, the first with `RuntimeError: MODEL_ANALYZE is unset`.

`cp .env.example .env` is not sufficient either. `MODEL_ANALYZE` ships empty, and the value
that makes the fully-offline path run is written down **only in `.github/workflows/pr.yml`**
— `gpt-5-mini-2025-08-07`, because cassette replay verifies the (model, prompt) pair, so
`MOCK_LLM=1` still needs the id. `DEMO_MODE` ships as `live`, contradicting every other
statement about how this demo runs.

**Fixed:** a *First-time setup* section, with both values in a table and the reason each is
not already there.

### 6 · P1's first command, again

```
$ make fe-build
sh: next: command not found
```

`fe-build` runs `npm run build` with no `node_modules`. The runbook never mentions
`make fe-install`. **Fixed:** the build targets take a `node_modules` prerequisite. The
build is what an operator wants; the toolchain is how it gets made.

### 7 · P4's command did not run at all — and this is the sharpest one

```
$ make report
rlens: error: one of --item or --all is required
make: *** [report] Error 2
```

P4 is *"re-warm the cache after any pin change"* — the procedure the staleness assertion,
`assert_fresh`, `/readyz`'s `stale_reports` and **E4 itself** all rest on. Its documented
command exits 2. The repair hint `make smoke` prints on an empty cache said the same wrong
thing.

The author always typed `ARGS="--all"`. The document never learned it, and could not have:
nobody who needed to read it had ever run it.

**Fixed:** `--all` is the default; `ARGS="--item mb-01"` still does the single item.

### 8 · P1 brought up the wrong demo

With everything above repaired, `make smoke` came back **21 of 22**:

```
[FAIL] an item page resolves through the mount — status 404
```

P1 said `make fe-build`. That builds against the **committed fixtures** — `fx-` items,
invented to exercise states the measured corpus does not contain. The demo ships
`fe-build-measured`, as the Makefile's own comment says. Following the runbook literally
brought up a site serving **invented data**, and every measured item page 404'd.

The smoke test caught it. That is the system working exactly as designed and the document
being wrong, which is the distinction this whole exercise is for.

**Fixed:** P1 says `fe-build-measured`. **22/22.**

---

## The ninth, which is not a runbook defect

Not a command that failed — a command that succeeded and destroyed a published number.

P5 documents, in this order:

```
make calibrate                 # (dev set; safe, the default)
make calibrate ARGS="--iaa"    # + B4 #1
```

Run the first alone — on a fresh checkout, or for any reason at all — and
`calibration/results/latest.json` becomes:

```json
"inter_annotator": { "annotators": ["amit"], "behavior": null, "soundness": null,
  "note": "... A null here means the second annotator has not labelled yet ..." }
```

**Ankit labelled on 15 Sep and his 50 rows are committed.** B4 #1's headline — behavior κ
**0.867**, soundness κ **0.935**, n = 50 — was replaced by two nulls under a note asserting
a false reason for them. FE-6 renders this file *verbatim*, so the calibration page would
have returned to reading **"not yet measured"**.

That is the failure mode this project has spent three months learning to recognise, arriving
from the modest direction. It is FE-11's finding inverted: there, three measured numbers
were being published as unmeasured, and the note said **understating is not automatically
safe — the page was making a false statement about the evidence.** Same defect here, except
this one *erases* rather than fails to join, and it presents as an honest empty state.
Nothing on screen looks wrong. A reviewer opening the page sees a project that has not
measured its headline yet.

**Fixed, and the rule is "did this run look?" rather than "is the new value null?".** A dev
pass does not read the double-labelled steps, so it carries the measured block forward and
flags it `carried_forward` — kept verbatim, never recomputed, one producer per number.
`--iaa` and `--final` *do* read them, so a null from either is a measurement and is still
written: carrying a stale κ over the top of that would be the same defect pointing the other
way, publishing agreement for labels no longer there.

Both halves are tested. The first is **negative-tested** — with the carry-forward disabled,
the test fails on the nulled κ.

---

## What ran clean

Worth recording, because a list of eight defects is not a verdict on the system.

| Procedure | Cold result |
| --- | --- |
| **P3** — trip and reset the breaker | **Clean, both directions, first try.** `breaker tripped: $11.00 spent against a $10.00 limit` → `reset: ok` |
| **P6** — hand the analyzer over (`make wheel`) | **Clean.** Builds, installs into an empty venv outside the repo, ingests the third-party LangGraph capture, loads its schema and prompt bundle from the wheel, confirms `openai` absent. The real handover artifact is in good shape |
| **P5** — rebuild the measurements | Ran clean and **reproduced B4 #1 from a clean checkout**: behavior κ 0.867 [0.495, 1.000], soundness κ 0.935 [0.766, 1.000], n=50. Independent reproduction of the headline, modulo the ninth finding above |
| **`make ci`**, after the fixes | **Green from an empty clone in 33 s** |
| **`make smoke`**, after the fixes | **22/22**, key stripped |

`make report` also rebuilt all 14 reports offline — no key, no GPU, no network — which is
I4 and the cached-only product holding up under the only test that matters: a machine that
has never seen this project.

---

## What this does to E13

**E13 stays open.** The runbook is materially better than it was this morning and that is
not what E13 asks. C15.1 #7 asks whether it works for *someone who did not write it*, and
the only evidence that answers that question is a person who did not write it, working from
the document alone, while its author stays off the keyboard.

What can be said, with the boundary attached:

- **Every one of the six procedures now executes from a clean checkout.** Before today, four
  of six did not, and P4's did not run at all.
- **Eight failures were exit codes, not confusions** — beyond the reach of the "the agent
  has read the codebase" objection. A command that exits 2 exits 2 for a peer too.
- **The unmeasured part is the whole of what E13 wanted**: whether an operator who cannot
  read `pyproject.toml` to discover an undeclared dependency can get from a clone to a
  running demo. This run cannot answer that, and finding eight broken commands on the way
  raises rather than lowers the odds that a peer would have found more.

Per amendment 002 §4, E13 ships **half closed with a reasoned decline**, not as a pass and
not as a blocked task awaiting a booking. U2 remains open and remains the tech lead's.

> The honest summary: the runbook had never been read by anyone who needed it, and it shows.
> One afternoon against a clean clone found eight broken commands and one silent erasure of
> a published headline. That is an argument for the peer dry-run, not a substitute for it.
