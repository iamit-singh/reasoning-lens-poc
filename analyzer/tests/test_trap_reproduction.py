"""M1-5's DoD, asserted against committed evidence. No model, no network, no spend.

The measurement itself is `spikes/m1_5_trap_reproduction.py` and needs a served model.
What runs here is the *contract over its output*, so that CI keeps the trap claims honest
forever without a GPU -- the same split M1-4 used, where `rlens.checkers` grades and the
test asserts.

Reads `problem-bank/` as data. I1 forbids `rlens` importing `problem_bank`, and this test
respects the boundary rather than working around it.

Owner: M1-5.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).parents[2]
BANK = ROOT / "problem-bank/items"
CANDIDATES = ROOT / "problem-bank/traps/candidates"
RUNS_PATH = ROOT / "problem-bank/traps/runs.json"
LOG_PATH = ROOT / "problem-bank/traps/reproduction-log.md"

#: M1-5's threshold and floor, mirrored from the harness. Duplicated deliberately: if the
#: harness lowers either one, this test fails rather than agreeing with it. The plan's
#: instruction on failure is "author more candidates -- do NOT lower the threshold", and a
#: threshold imported from the thing it constrains cannot enforce that.
HITS_REQUIRED = 3
SAMPLED_RUNS = 5
TRAPS_REQUIRED = 3


@pytest.fixture(scope="module")
def evidence() -> dict[str, Any]:
    assert RUNS_PATH.exists(), f"no trap evidence at {RUNS_PATH}; run `make traps`"
    payload: dict[str, Any] = json.loads(RUNS_PATH.read_text())
    return payload


@pytest.fixture(scope="module")
def declared() -> list[dict[str, Any]]:
    """Every item claiming to be a trap, in the bank and in the candidate pool."""
    items = [json.loads(p.read_text()) for p in sorted(BANK.glob("*.json"))]
    items += [json.loads(p.read_text()) for p in sorted(CANDIDATES.glob("*.json"))]
    return [i for i in items if i.get("is_trap")]


def _earned(runs: list[dict[str, Any]], item_id: str) -> list[str]:
    """Arms where this candidate fired pinned AND reached the threshold sampled."""
    out = []
    for arm in sorted({r["arm"] for r in runs if r["item"] == item_id}):
        sel = [r for r in runs if r["item"] == item_id and r["arm"] == arm]
        pinned = [r for r in sel if r["regime"] == "pinned" and r["outcome"] == "trap"]
        sampled = [r for r in sel if r["regime"] == "sampled" and r["outcome"] == "trap"]
        if pinned and len(sampled) >= HITS_REQUIRED:
            out.append(arm)
    return out


# ------------------------------------------------------------------ the DoD
@pytest.mark.contract
@pytest.mark.xfail(
    strict=True,
    reason="ADR-005 (Proposed): 0 of 16 candidates reproduce over 120 runs. There is no "
    "shallow regime on gpt-oss:20b to trap -- ADR-004 established that thinking cannot be "
    "switched off and `low` is the floor. STRICT on purpose: if a trap ever does "
    "reproduce, this test passes, the suite fails, and the marker must come off. The "
    "threshold has not been lowered and no tag has been relabelled as passing.",
)
def test_three_traps_reproduce_at_the_threshold(
    evidence: dict[str, Any], declared: list[dict[str, Any]]
) -> None:
    """M1-5's DoD, stated exactly: 3 traps at >= 3 of 5."""
    runs = evidence["runs"]
    earned = [i["id"] for i in declared if _earned(runs, i["id"])]
    assert len(earned) >= TRAPS_REQUIRED, (
        f"{len(earned)} traps earned, floor is {TRAPS_REQUIRED}: {earned or 'none'}"
    )


# ------------------------------------------------------------------ the threshold itself
@pytest.mark.contract
def test_the_threshold_has_not_been_lowered(evidence: dict[str, Any]) -> None:
    """The one thing the plan forbids as a response to failure.

    "A trap that reproduces 2 of 5 times is a trap that fails on stage 60% of the time."
    Recording a weaker threshold would turn M1-5 from a measurement into a formality, and
    it is the cheapest possible way to make this task look finished.
    """
    assert evidence["hits_required"] == HITS_REQUIRED
    assert evidence["sampled_runs"] >= SAMPLED_RUNS


@pytest.mark.contract
def test_the_sampled_regime_actually_samples(evidence: dict[str, Any]) -> None:
    """Greedy decoding makes "3 of 5" arithmetically impossible.

    The committed pin is `temperature=0` with a fixed seed, and `llm.generate` sends both
    for both arms -- two thinking-arm runs of `mb-13` came back byte-identical. A hit
    count out of 5 measured there can only be 0 or 5. The sampled regime must therefore
    carry a non-zero temperature and distinct seeds, or the denominator is decoration.
    """
    assert evidence["sampled_temperature"] > 0
    sampled = [r for r in evidence["runs"] if r["regime"] == "sampled"]
    assert sampled, "no sampled runs on file"
    assert all(r["temperature"] > 0 for r in sampled)
    assert len({r["seed"] for r in sampled}) >= SAMPLED_RUNS


# ------------------------------------------------------------------ evidence integrity
@pytest.mark.contract
def test_every_declared_trap_has_been_measured(
    evidence: dict[str, Any], declared: list[dict[str, Any]]
) -> None:
    """An unmeasured trap is a claim, not a trap.

    The failure this guards is quiet: a trap added to the bank after the last measurement
    inherits the log's credibility without having been tested.
    """
    measured = {r["item"] for r in evidence["runs"]}
    missing = sorted(i["id"] for i in declared if i["id"] not in measured)
    assert not missing, f"declared but never measured: {missing}. Run `make traps`."


@pytest.mark.contract
def test_every_trap_declares_the_wrong_answers_it_induces(
    declared: list[dict[str, Any]],
) -> None:
    """`trap_note` is the prose; `trap_answers` is the same claim in a countable form.

    Without it "reproduces" rests on whoever reads the run, and any wrong answer counts.
    """
    for item in declared:
        answers = item.get("trap_answers")
        assert isinstance(answers, list) and answers, f"{item['id']}: no trap_answers"
        assert all(isinstance(a, str) and a.strip() for a in answers), item["id"]


@pytest.mark.contract
def test_both_regimes_are_present_for_every_measured_arm(evidence: dict[str, Any]) -> None:
    """Earning a tag requires both regimes on the same arm, so both must be recorded.

    Pinned alone is one point in sampling space; sampled alone does not describe the demo,
    which is greedy-decoded.
    """
    runs = evidence["runs"]
    for item_id in sorted({r["item"] for r in runs}):
        for arm in sorted({r["arm"] for r in runs if r["item"] == item_id}):
            sel = [r for r in runs if r["item"] == item_id and r["arm"] == arm]
            regimes = {r["regime"] for r in sel}
            assert regimes == {"pinned", "sampled"}, f"{item_id}/{arm}: regimes {regimes}"


@pytest.mark.contract
def test_outcomes_distinguish_unreadable_from_wrong(evidence: dict[str, Any]) -> None:
    """`unparsed` must not be folded into `other`.

    A run whose answer could not be read is a different fact from a run that was wrong,
    and counting the first as the second understates accuracy for free. M1-5 hit exactly
    one of these -- a correct answer inside a LaTeX block -- and it is the reason the
    outcome exists at all.
    """
    allowed = {"correct", "trap", "other", "unparsed", "failed"}
    outcomes = {r["outcome"] for r in evidence["runs"]}
    assert outcomes <= allowed, f"unknown outcomes: {outcomes - allowed}"


@pytest.mark.contract
def test_every_run_carries_its_own_provenance(evidence: dict[str, Any]) -> None:
    """A reproduction rate that cannot be re-run is an anecdote (I3).

    The stored response text is what lets the whole measurement be re-graded offline after
    a grader change -- which M1-5 needed twice -- so it is part of the evidence, not a
    convenience.
    """
    assert evidence["pin"]["digest"], "measured against an unpinned model"
    for run in evidence["runs"]:
        assert run["run_id"] and run["item"] and run["arm"] and run["regime"]
        if run["outcome"] != "failed":
            assert "text" in run, f"{run['run_id']}: no response text to re-grade from"
            assert run["pin_fingerprint"]


@pytest.mark.contract
def test_the_committed_log_matches_the_committed_runs(evidence: dict[str, Any]) -> None:
    """The log is what people read; the runs file is what the number comes from.

    They are generated together and must not be committed apart -- a log describing a
    different measurement than the one on file is worse than no log, because it is
    trusted.
    """
    assert LOG_PATH.exists(), f"no log at {LOG_PATH}"
    log = LOG_PATH.read_text()
    assert f"**{len(evidence['runs'])} runs**" in log, "log's run count is stale"
    assert evidence["pin_fingerprint"] in log, "log's pin does not match the runs file"
