"""The problem bank's own contract. M1-4's DoD.

Every declared checker must accept its declared answer, and the L1 tag floors must hold.

**Why a bank needs a test at all.** Nothing else in the system ever notices a wrong
`known_answer`: the runner does not grade, the analyzer grades against whatever the bank
says, and a mis-declared item quietly reports a correct model answer as wrong for the
rest of the project. That error is invisible in every downstream number and shows up only
as "the model is worse than expected". C3.4 names two specific shapes of it -- the
`numeric_tol` item whose tolerance is zero, and the `set_match` item whose answer is a
string -- and both are asserted below.

Note the bank is read as DATA from `problem-bank/items/`. I1 forbids `rlens` importing
`problem_bank`, and this test respects that boundary rather than working around it.
"""

from __future__ import annotations

import json
import pathlib
from collections import Counter
from typing import Any

import pytest
from rlens.checkers import CHECKERS, CheckerError, check

BANK = pathlib.Path(__file__).parents[2] / "problem-bank/items"

#: Lever L1, applied at kickoff per Appendix D #1's stated default. The floors are what
#: make B4 #7's `tool_required` share computable and keep the picker credible; the item
#: count above the floors is the compressible part.
L1_ITEM_COUNT = 14
#: The trap floor is **withdrawn** by ADR-005 (accepted 11 Sep 2026): 0 of 16 candidates
#: reproduced over 120 runs, and ADR-006 explains why -- arm 1's minimal effort is
#: adaptive, so there is no shallow regime to trap. `easy` and `multi_step` carry the arm
#: contrast instead, and `problem-bank/traps/reproduction-log.md` is the record.
FLOORS = {"tool_required": 5, "easy": 3, "multi_step": 3}

REQUIRED_FIELDS = {"id", "prompt", "tags", "known_answer", "checker", "is_trap", "source"}
OPTIONAL_FIELDS = {"tolerance", "trap_note", "trap_answers"}


def _load() -> list[dict[str, Any]]:
    return [json.loads(p.read_text()) for p in sorted(BANK.glob("*.json"))]


@pytest.fixture(scope="module")
def items() -> list[dict[str, Any]]:
    loaded = _load()
    assert loaded, f"no bank items under {BANK}"
    return loaded


def _ids() -> list[str]:
    return [p.stem for p in sorted(BANK.glob("*.json"))]


def _a_different_number(answer: str) -> str:
    """A wrong answer of the same shape: a number, not the right one."""
    try:
        return f"{float(answer) + 1:g}"
    except ValueError:
        return f"{answer} and also something else entirely"


# ------------------------------------------------------------------ the DoD
@pytest.mark.contract
@pytest.mark.parametrize("item_id", _ids())
def test_every_declared_checker_accepts_its_declared_answer(item_id: str) -> None:
    """M1-4's DoD, stated exactly. An item whose own answer fails its own checker is
    an item that can never be answered correctly by anything."""
    item = json.loads((BANK / f"{item_id}.json").read_text())
    answer = item["known_answer"]
    # A set answer is presented to the checker the way a model would present it: as
    # text. Passing the list back in would test nothing -- the list equals itself.
    actual = ", ".join(answer) if isinstance(answer, list) else answer
    assert check(answer, actual, item["checker"], item.get("tolerance")), (
        f"{item_id}: checker {item['checker']!r} rejects its own known_answer {answer!r}"
    )


@pytest.mark.contract
@pytest.mark.parametrize("item_id", _ids())
def test_item_shape_matches_c3_4(item_id: str) -> None:
    item = json.loads((BANK / f"{item_id}.json").read_text())
    assert item["id"] == item_id, "the id must match the filename; step ids depend on it"
    missing = REQUIRED_FIELDS - set(item)
    assert not missing, f"{item_id} missing {sorted(missing)}"
    unknown = set(item) - REQUIRED_FIELDS - OPTIONAL_FIELDS
    assert not unknown, f"{item_id} has fields C3.4 does not define: {sorted(unknown)}"
    assert item["checker"] in CHECKERS
    assert isinstance(item["tags"], list) and item["tags"]
    assert isinstance(item["is_trap"], bool)
    assert item["prompt"].strip() and item["source"].strip()


# ------------------------------------------------------------------ C3.4's two named traps
@pytest.mark.contract
def test_numeric_tol_items_declare_a_nonzero_tolerance(items: list[dict[str, Any]]) -> None:
    """A zero tolerance is exact-match wearing a numeric label, and it fails on 34 vs 34.0."""
    for item in items:
        if item["checker"] == "numeric_tol":
            tol = item.get("tolerance")
            assert tol is not None and tol > 0, f"{item['id']}: tolerance {tol!r}"
        else:
            assert "tolerance" not in item, f"{item['id']}: tolerance on a non-numeric checker"


@pytest.mark.contract
def test_set_match_answers_are_lists_not_strings(items: list[dict[str, Any]]) -> None:
    """A set answer written as a string passes `exact` and then accepts one ordering only."""
    for item in items:
        if item["checker"] == "set_match":
            assert isinstance(item["known_answer"], list), item["id"]
            assert len(item["known_answer"]) > 1, f"{item['id']}: a one-element set_match"
        else:
            assert isinstance(item["known_answer"], str), item["id"]


@pytest.mark.contract
def test_the_checkers_actually_reject_a_wrong_answer(items: list[dict[str, Any]]) -> None:
    """The DoD's mirror image, and the more important half.

    "Every checker accepts its own answer" is satisfied by a checker that accepts
    everything. Each item is therefore also shown to REJECT a plausible wrong answer --
    for traps, the specific wrong answer named in the trap_note.
    """
    for item in items:
        answer, checker = item["known_answer"], item["checker"]
        if item["is_trap"]:
            # For a trap the plausible wrong answer is not hypothetical -- it is the one
            # the item was BUILT to induce, and it is declared. Synthesising a wrong
            # answer here instead would test the checker against a strawman while the
            # answer that actually threatens it went unchecked.
            wrongs = list(item["trap_answers"])
        elif checker == "set_match":
            wrongs = [", ".join([*list(answer)[:-1], "chartreuse"])]
        elif checker == "numeric_tol":
            wrongs = [str(float(answer) + 10 * item["tolerance"])]
        else:
            # A plausible wrong answer to a numeric item is a DIFFERENT NUMBER. The
            # earlier form here appended waffle to the right answer -- which M1-5's
            # numeric-aware `exact` correctly accepts, because a model that writes
            # "68 and also something else entirely" has answered 68. That string tested
            # string-containment looseness, which stopped being the risk when `exact`
            # stopped being a string compare; a different number is the risk now.
            # `test_checkers.py` covers the pushover cases this no longer reaches.
            wrongs = [_a_different_number(answer), f"not {answer}"]
        for wrong in wrongs:
            assert not check(answer, wrong, checker, item.get("tolerance")), (
                f"{item['id']}: checker {checker!r} accepted {wrong!r}"
            )


# ------------------------------------------------------------------ L1 floors
@pytest.mark.contract
def test_l1_item_count_and_tag_floors(items: list[dict[str, Any]]) -> None:
    assert len(items) == L1_ITEM_COUNT
    tags = Counter(t for item in items for t in item["tags"])
    observed = {
        "tool_required": tags["tool_required"],
        "easy": tags["easy"],
        "multi_step": tags["multi_step"],
    }
    for name, floor in FLOORS.items():
        assert observed[name] >= floor, f"{name}: {observed[name]} < L1 floor {floor}"


@pytest.mark.contract
def test_ids_are_unique_and_stable(items: list[dict[str, Any]]) -> None:
    """`step_id` embeds the item id. Renaming an item detaches every label written
    against it -- the same hazard the segmenter freeze exists to prevent."""
    ids = [i["id"] for i in items]
    assert len(set(ids)) == len(ids)


# ------------------------------------------------------------------ traps
@pytest.mark.contract
def test_every_trap_names_the_wrong_chain_it_is_meant_to_induce(
    items: list[dict[str, Any]],
) -> None:
    """A trap without a stated wrong chain cannot be validated by M1-5.

    M1-5 measures whether each trap reproduces *a plausible wrong chain* in >= 3 of 5
    runs. "Reproduces" is only checkable against a wrong chain someone wrote down in
    advance -- otherwise any wrong answer counts and the threshold means nothing.
    """
    for item in items:
        if item["is_trap"]:
            note = item.get("trap_note", "")
            assert note.strip(), f"{item['id']}: is_trap with no trap_note"
            assert len(note) > 60, f"{item['id']}: trap_note too thin to validate against"
            # The prose says which chain the trap induces; `trap_answers` is the same
            # claim in a form M1-5 can COUNT. Prose alone leaves "reproduces" to the
            # judgement of whoever reads the run, which is not a measurement.
            answers = item.get("trap_answers")
            assert isinstance(answers, list) and answers, (
                f"{item['id']}: is_trap with no trap_answers. M1-5 counts reproductions "
                f"by checking the model's answer against these."
            )
            assert all(isinstance(a, str) and a.strip() for a in answers), item["id"]
        else:
            assert "trap_note" not in item, f"{item['id']}: trap_note on a non-trap"
            assert "trap_answers" not in item, f"{item['id']}: trap_answers on a non-trap"


@pytest.mark.contract
def test_the_bank_makes_no_unearned_trap_claim(items: list[dict[str, Any]]) -> None:
    """ADR-005, accepted: a trap claim in the bank must have been earned in M1-5.

    Four were declared in M1-4 and none reproduced over 120 runs, so all four had the
    claim withdrawn -- the items themselves are fine and stayed. Their declarations live
    on in `problem-bank/traps/candidates/` with the evidence attached, because deleting
    the prose would delete the record of what was tried.

    This asserts the state ADR-005 leaves behind, and it is the guard that matters going
    forward: **anything re-tagged `is_trap` in the bank must come with a reproduction
    result**, or the tag is back to meaning nothing. `test_trap_reproduction.py` is where
    that result is checked.
    """
    claimed = [i["id"] for i in items if i["is_trap"]]
    assert not claimed, (
        f"{claimed} claim is_trap in the bank. ADR-005 withdrew the floor and every "
        f"declared trap's claim; a new one needs an earned result in "
        f"problem-bank/traps/reproduction-log.md first."
    )


# ------------------------------------------------------------------ ADR-004
@pytest.mark.contract
def test_easy_items_are_single_step_so_the_arms_can_agree(items: list[dict[str, Any]]) -> None:
    """ADR-004 made this a requirement rather than a nicety.

    At `low` effort arm 1 got a multi-step probe wrong while arm 2 got it right. If every
    item separates the arms that cleanly, the bank measures DIFFICULTY, not strategy --
    and the cost-of-thought story collapses into "harder problems need more thinking",
    which nobody needed this project to learn. The `easy` items are the control group:
    they are where arm 1 should MATCH arm 2 at a fraction of the cost.

    A cheap structural proxy for "one step" is asserted here -- a short prompt with no
    chaining language. Whether the arms actually agree is a MEASUREMENT, and it belongs
    to M1-5's sibling work in W3, not to a unit test.
    """
    easy = [i for i in items if "easy" in i["tags"]]
    assert len(easy) >= FLOORS["easy"]
    chaining = ("then", "after that", "remaining", "each of", "in total across")
    for item in easy:
        assert "multi_step" not in item["tags"], f"{item['id']}: easy and multi_step"
        assert not item["is_trap"], f"{item['id']}: an easy item cannot also be a trap"
        assert len(item["prompt"]) < 140, f"{item['id']}: long prompt for an easy item"
        low = item["prompt"].casefold()
        assert not [c for c in chaining if c in low], f"{item['id']}: chaining language"


# ------------------------------------------------------------------ the checker module
@pytest.mark.contract
def test_checker_rejects_the_malformed_declarations_c3_4_warns_about() -> None:
    """The failure modes must raise, not quietly return False -- a bank defect and a
    wrong answer are different things and must not look the same to the caller."""
    with pytest.raises(CheckerError):
        check("34.00", "34.00", "numeric_tol", 0)
    with pytest.raises(CheckerError):
        check("red, green", "red, green", "set_match")
    with pytest.raises(CheckerError):
        check("x", "x", "fuzzy_match")


@pytest.mark.contract
@pytest.mark.parametrize(
    ("known", "actual"),
    [
        ("3237.50", "$3,237.50"),
        ("3237.50", "3237.5"),
        ("34.00", "34"),
    ],
)
def test_normalisation_accepts_the_formats_a_model_actually_emits(known: str, actual: str) -> None:
    """Under-normalising silently deflates every accuracy figure in the study."""
    assert check(known, actual, "numeric_tol", 0.01)
