"""Answer checkers. C3.4's `exact | numeric_tol | set_match`.

Pure functions over two strings. **No bank dependency** -- an item's `checker` name and
`known_answer` are passed in, never read from disk here, so I1's "the analyzer must not
import problem_bank" holds without needing to be argued.

Owner: M1-4. Used by `test_bank_answers.py` now and by `metrics.py` (accuracy) later --
deliberately one implementation, because a bank whose answers are validated by different
code than the code that grades the run is a bank that is validated against nothing.

**Normalisation is the whole design problem here.** The arms are told to put the final
answer on its own last line, and a model will still write `$3,237.50`, `3237.5` or
`The answer is 3237.50.` for the same number. Under-normalising marks correct answers
wrong and silently deflates every accuracy figure in the study; over-normalising marks
wrong answers right. The rules below are deliberately small, listed, and testable.
"""

from __future__ import annotations

import math
import re

CHECKERS = ("exact", "numeric_tol", "set_match")

#: Currency symbols and thousands separators are formatting, not content.
_STRIP_CHARS = "$£€,"
#: A trailing sentence period is punctuation; a decimal point is not, so this only
#: fires at the very end of the string.
_TRAILING_PUNCT = ".!;:"


class CheckerError(ValueError):
    """The item's checker declaration is malformed. A bank defect, not a wrong answer."""


def normalise(text: str) -> str:
    """Lowercase, unpad, drop currency/grouping marks and trailing punctuation."""
    out = text.strip().casefold()
    for ch in _STRIP_CHARS:
        out = out.replace(ch, "")
    return out.strip().rstrip(_TRAILING_PUNCT).strip()


def sole_number(text: str) -> float | None:
    """The one number in the text, or None if there is not exactly one.

    Public because callers outside grading need the same question answered: M1-5's
    harness uses it to tell an answer it could not READ from an answer that was WRONG,
    and counting the first as the second understates accuracy for free.

    Tolerant of a model that answers `3237.50 dollars` rather than a bare numeral --
    but NOT of one that answers with a sentence containing several numbers, where
    picking the first would be a guess. That case returns None and scores wrong, which
    is the honest outcome: we cannot tell what it meant.
    """
    found = re.findall(r"-?\d+(?:\.\d+)?", normalise(text).replace(" ", ""))
    if len(found) != 1:
        return None
    return float(found[0])


#: Words that invert an answer while leaving its number intact. Kept as a short, listed
#: rule rather than a general "is this a real assertion" heuristic, because negation is
#: the one transformation that makes `not 68` and `68` the same string to a number
#: extractor and opposite claims to a reader. Waffle around a number does not change
#: what was answered; a negation does.
_NEGATIONS = (" not ", " no ", "n't ", " neither ", " cannot ", " isn't ", " none ")


def _negated(text: str) -> bool:
    """Does this answer deny its own number?

    Padded on both sides so `not` matches the word and never the inside of `another`.
    """
    return any(word in f" {normalise(text)} " for word in _NEGATIONS)


def _as_set(value: str | list[str]) -> set[str]:
    parts = value if isinstance(value, list) else re.split(r"[,\n;]|\band\b", value)
    return {normalise(p) for p in parts if normalise(p)}


def check(
    known_answer: str | list[str],
    actual: str,
    checker: str,
    tolerance: float | None = None,
) -> bool:
    """Does `actual` satisfy this item's declared answer under this checker?"""
    if checker not in CHECKERS:
        raise CheckerError(f"unknown checker {checker!r}; expected one of {CHECKERS}")

    if checker == "exact":
        if isinstance(known_answer, list):
            raise CheckerError("checker 'exact' needs a string answer, not a list")
        if normalise(known_answer) == normalise(actual):
            return True
        # **A numeric answer is a number, not a string.** M1-5 found this on live runs:
        # asked for "the final answer on its own last line", the model answers
        # `7 minutes`, and a string compare against the declared `7` calls that WRONG.
        # Nothing downstream would have noticed -- it deflates accuracy for every
        # `exact` item for the rest of the project and surfaces only as "the model is
        # worse than expected", which is precisely the failure `test_bank_answers.py`
        # exists to prevent and could not catch, because its own test feeds the declared
        # answer back in and a string trivially equals itself.
        #
        # This is not `numeric_tol` by the back door. `numeric_tol` grants MEASUREMENT
        # slack, which is an item-level claim and must be declared per item; the epsilon
        # below is float-REPRESENTATION slack, so that `315` and `315.0` are the same
        # number rather than two spellings. And it stays strict where it matters:
        # `sole_number` refuses text containing more than one number, so `7 or 21` scores
        # wrong instead of silently resolving to the first thing that looks like a hit.
        want = sole_number(known_answer)
        if want is None:
            return False
        got = sole_number(actual)
        if got is None or _negated(actual):
            return False
        return math.isclose(want, got, rel_tol=1e-9, abs_tol=1e-12)

    if checker == "numeric_tol":
        if tolerance is None or tolerance <= 0:
            # C3.4's own named failure mode. A zero tolerance is not "strict" -- it is
            # exact-match wearing a numeric label, and it will fail on 34 vs 34.0.
            raise CheckerError(
                f"checker 'numeric_tol' needs a tolerance > 0 (got {tolerance!r}). "
                "A zero tolerance is exact-match with a misleading name."
            )
        if isinstance(known_answer, list):
            raise CheckerError("checker 'numeric_tol' needs a string answer, not a list")
        want, got = sole_number(known_answer), sole_number(actual)
        if want is None or got is None:
            return False
        return abs(want - got) <= tolerance

    # set_match
    if not isinstance(known_answer, list):
        # The other named failure mode: a set answer written as a string happens to
        # work under `exact` and then silently accepts only one ordering.
        raise CheckerError(
            f"checker 'set_match' needs a list answer, got {type(known_answer).__name__}"
        )
    return _as_set(known_answer) == _as_set(actual)
