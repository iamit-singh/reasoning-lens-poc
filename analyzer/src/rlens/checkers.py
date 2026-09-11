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


def _as_float(text: str) -> float | None:
    """The first number in the text, or None.

    Tolerant of a model that answers `3237.50 dollars` rather than a bare numeral --
    but NOT of one that answers with a sentence containing several numbers, where
    picking the first would be a guess. That case returns None and scores wrong, which
    is the honest outcome: we cannot tell what it meant.
    """
    found = re.findall(r"-?\d+(?:\.\d+)?", normalise(text).replace(" ", ""))
    if len(found) != 1:
        return None
    return float(found[0])


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
        return normalise(known_answer) == normalise(actual)

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
        want, got = _as_float(known_answer), _as_float(actual)
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
