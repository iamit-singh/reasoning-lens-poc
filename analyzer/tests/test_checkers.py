"""The checkers' own contract, independent of any bank.

`test_bank_answers.py` validates the *bank*; this validates the *grader*. The two need
separating, because the bank test's central assertion -- every checker accepts its own
declared answer -- is structurally blind to the defect M1-5 found on live runs: it feeds
the declared answer straight back in, and a string trivially equals itself. The answers a
model actually writes never appear in it.

Owner: M1-4 (checkers), extended by M1-5 (the numeric `exact` case).
"""

from __future__ import annotations

import pytest
from rlens.checkers import CheckerError, check, normalise

# ------------------------------------------------------------------ normalisation


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("  $3,237.50 ", "3237.50"),
        ("315.", "315"),
        ("Chartreuse", "chartreuse"),
        ("0.30", "0.30"),  # a decimal point is not trailing punctuation
    ],
)
def test_normalise_strips_formatting_not_content(raw: str, want: str) -> None:
    assert normalise(raw) == want


# ------------------------------------------------------------------ exact, on real answers


@pytest.mark.parametrize(
    ("known", "actual"),
    [
        ("7", "7"),
        ("7", "7 minutes"),  # M1-5, observed live on mb-13
        ("315", "315 square metres"),
        ("315", "315.0"),
        ("46", "day 46"),
        ("3237.50", "$3,237.50"),
    ],
)
def test_exact_accepts_the_shapes_a_model_actually_writes(known: str, actual: str) -> None:
    """The arms ask for "the final answer on its own last line" -- not for a bare numeral.

    A grader that demands a bare numeral marks correct answers wrong, and because nothing
    downstream re-checks, it deflates accuracy for the rest of the project while looking
    like a weaker model.
    """
    assert check(known, actual, "exact")


@pytest.mark.parametrize(
    ("known", "actual"),
    [
        ("7", "21"),
        ("7", "21 minutes"),
        ("315", "371.25"),
        ("7", "seven"),  # a word is not a number; we do not guess
        ("7", "7 or 21"),  # ambiguous: refused rather than resolved to the first hit
        ("46", "day 12 of 48"),
        ("chartreuse", "magenta"),
        # Negation: the number survives extraction, the claim does not. Scoring these
        # correct would credit the model for an answer it explicitly declined to give.
        ("7", "not 7"),
        ("7", "it isn't 7"),
        ("315", "no, 315 is wrong"),
    ],
)
def test_exact_still_rejects_wrong_and_ambiguous_answers(known: str, actual: str) -> None:
    """The half that matters. Numeric awareness must not become "contains the digit".

    `7 or 21` is the case worth naming: a grader that took the first number would score
    a hedged answer as correct, and a trap's reproduction rate would then count runs
    where the model never committed to the wrong chain at all.
    """
    assert not check(known, actual, "exact")


def test_exact_numeric_is_not_numeric_tol_by_the_back_door() -> None:
    """`numeric_tol` grants MEASUREMENT slack and must be declared per item. The epsilon
    in `exact` is float-REPRESENTATION slack only -- `315` and `315.0` are one number,
    `315` and `315.01` are two."""
    assert check("315", "315.0", "exact")
    assert not check("315", "315.01", "exact")
    assert check("315", "315.01", "numeric_tol", tolerance=0.1)


# ------------------------------------------------------------------ the declared errors


def test_a_list_answer_under_exact_is_a_bank_defect_not_a_wrong_answer() -> None:
    with pytest.raises(CheckerError):
        check(["a", "b"], "a, b", "exact")


def test_numeric_tol_refuses_a_zero_tolerance() -> None:
    with pytest.raises(CheckerError):
        check("315", "315", "numeric_tol", tolerance=0)


def test_set_match_refuses_a_string_answer() -> None:
    with pytest.raises(CheckerError):
        check("a, b", "a, b", "set_match")


def test_unknown_checker_raises() -> None:
    with pytest.raises(CheckerError):
        check("315", "315", "fuzzy")


def test_waffle_around_the_right_number_is_still_the_right_number() -> None:
    """The deliberate boundary of the negation rule.

    A model that pads its answer has still answered; a model that negates it has not.
    Only the second changes what was claimed, which is why the rule is a short list of
    negations rather than a general "does this look like a real assertion" heuristic --
    the latter has no boundary anyone can state, and graders that cannot be stated
    cannot be audited.
    """
    assert check("68", "68, give or take rounding", "exact")
    assert not check("68", "not 68, give or take rounding", "exact")


def test_negation_matches_words_not_substrings() -> None:
    """`not` must not fire inside `another`, `cannot` inside `cannoli`."""
    assert check("3", "3, one after another", "exact")
