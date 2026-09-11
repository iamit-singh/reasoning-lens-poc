"""The statistics the published numbers rest on — C5.5.

Owner: M2-13.

Cohen's κ, a bootstrap CI on it, Wilson intervals on proportions, per-class F1, the
confusion matrix, and the majority-class baseline. Nothing here touches a model or a file;
it takes label sequences in and returns numbers out, which is what makes every one of them
testable against a worked example.

Why these are hand-written rather than `sklearn`
-----------------------------------------------
C5.5 names ``sklearn.metrics.cohen_kappa_score`` and ``classification_report``, and this
module implements both directly. Two reasons, and one guard that makes the trade safe:

* **I1 says the analyzer is a standalone pip package.** scikit-learn brings numpy and scipy
  — on the order of 100 MB — into a package whose declared virtue is that it installs with
  four small dependencies and ingests a span tree. That is a real cost paid on every
  install, every CI job and every container layer, for two textbook formulas.
* **These are textbook formulas.** κ is four counts and a division; F1 is three.

**The guard is the part that matters.** A hand-rolled κ with a bug would publish a wrong
headline number, which is the single worst failure available to this project. So
``scikit-learn`` is a **dev-only** dependency and the test suite asserts agreement with it
to 10 decimal places, on random label sequences as well as on fixed cases. Production stays
lean; the numbers are checked against the reference implementation anyway.

Every function returns its **n** alongside its estimate
-------------------------------------------------------
C5.5: *"a metric emitted without n should be impossible, not discouraged."* At n = 90 an
80% estimate is roughly ±8 pp, and saying so is the difference between a measurement and an
assertion — which is the entire thesis of the demo. So the return types carry n and an
interval rather than a bare float, and it is deliberately awkward to get only the number.
"""

from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

#: C4.3's taxonomy, in a fixed order so a confusion matrix is comparable across runs.
BEHAVIOR_CLASSES: tuple[str, ...] = (
    "verification",
    "backtracking",
    "subgoal_setting",
    "backward_chaining",
    "linear",
)

SOUNDNESS_CLASSES: tuple[str, ...] = ("sound", "unsound", "unverifiable")

#: C5.5. 2000 resamples on κ; fixed here rather than passed, because a CI computed with a
#: different resample count between runs is not comparable and nobody would notice.
BOOTSTRAP_RESAMPLES = 2000

#: The seed for the bootstrap. A CI is a published number, and I3 says a published number
#: is reproducible or it is not published — an unseeded bootstrap gives a slightly
#: different interval every run and there is no way to tell that from drift in the data.
BOOTSTRAP_SEED = 20261013


@dataclass(frozen=True)
class Estimate:
    """A number, its sample size, and its interval. **Never just a number.**

    `low`/`high` are None when n is too small for the interval to mean anything, and that
    is a state a renderer must show rather than hide: "0.71 (n=3, CI not computable)" is
    honest, "0.71" is not.
    """

    value: float | None
    n: int
    low: float | None = None
    high: float | None = None
    method: str = ""
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "n": self.n,
            "ci_low": self.low,
            "ci_high": self.high,
            "ci_method": self.method or None,
            "note": self.note or None,
        }


@dataclass(frozen=True)
class ClassScore:
    """Per-class precision/recall/F1 with its support.

    **`f1` is None when support is zero, never 0.0.** ADR-010: per-class F1 over zero
    instances is undefined, and reporting 0.00 says "the classifier is perfectly bad at
    this class" — a measurement claim made from no measurements. `backtracking` has 0
    instances in the entire corpus, so this is the live case, not a hypothetical.
    """

    label: str
    precision: float | None
    recall: float | None
    f1: float | None
    support: int
    predicted: int

    def as_dict(self) -> dict[str, object]:
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "support": self.support,
            "predicted": self.predicted,
        }


@dataclass
class Agreement:
    """Everything C5.5 asks about one pair of label sequences."""

    kappa: Estimate
    raw_agreement: Estimate
    majority_baseline: Estimate
    agreement_over_baseline_pp: float | None
    per_class: list[ClassScore] = field(default_factory=list)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    n: int = 0
    classes_absent: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "n": self.n,
            "kappa": self.kappa.as_dict(),
            "raw_agreement": self.raw_agreement.as_dict(),
            "majority_class_baseline": self.majority_baseline.as_dict(),
            "agreement_over_baseline_pp": self.agreement_over_baseline_pp,
            "per_class": {c.label: c.as_dict() for c in self.per_class},
            "confusion": self.confusion,
            # Named explicitly so a reader does not have to infer absence from a null.
            # ADR-010 is entirely about what this list means.
            "classes_absent_from_this_sample": self.classes_absent,
        }


# ------------------------------------------------------------------------ intervals
def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """95% Wilson score interval on a proportion.

    Wilson rather than the normal approximation because C5.5 says so and because the
    normal approximation is wrong exactly where this project needs it to be right: at
    small n and at proportions near 0 or 1, where it produces intervals that extend past
    0% or 100%. With `backtracking` at 0 instances, that is not an edge case here.
    """
    if n <= 0:
        raise ValueError("Wilson interval needs n > 0")
    phat = successes / n
    denom = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / denom
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def proportion(successes: int, n: int, note: str = "") -> Estimate:
    if n <= 0:
        return Estimate(None, 0, note=note or "no observations")
    low, high = wilson_interval(successes, n)
    return Estimate(successes / n, n, low, high, "wilson", note)


# ------------------------------------------------------------------------ kappa
def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Cohen's κ for two label sequences over the same items.

    `(observed - expected) / (1 - expected)`, where expected agreement comes from the
    product of each rater's marginals.

    **Returns None when expected agreement is 1.0**, which happens when both raters used
    exactly one class for everything. κ is genuinely undefined there — the denominator is
    zero — and this is not a remote possibility on a corpus that is 81% `linear`. Returning
    0.0 would report "no agreement beyond chance" about two raters who agreed on every
    single item, which is the opposite of what happened.
    """
    if len(a) != len(b):
        raise ValueError(f"label sequences differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    if n == 0:
        return None
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[label] * cb[label] for label in set(ca) | set(cb)) / (n * n)
    if math.isclose(expected, 1.0):
        return None
    return (observed - expected) / (1 - expected)


def bootstrap_kappa(
    a: Sequence[str],
    b: Sequence[str],
    *,
    resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int = BOOTSTRAP_SEED,
) -> Estimate:
    """κ with a percentile bootstrap CI over `resamples` resamples (C5.5).

    Seeded, because a CI is a published number. Resamples that produce an undefined κ
    (every drawn item landing in one class) are **dropped and counted**, not treated as
    zero: a resample that cannot produce an estimate is missing data, and averaging it in
    as 0.0 would drag the interval down by an amount that depends on how skewed the corpus
    is — biasing the number most on exactly the corpora where it matters most.
    """
    point = cohen_kappa(a, b)
    n = len(a)
    if point is None or n < 2:
        return Estimate(
            point,
            n,
            note="kappa is undefined: both raters used a single class" if n else "no labels",
        )

    rng = random.Random(seed)
    draws: list[float] = []
    undefined = 0
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        value = cohen_kappa([a[i] for i in idx], [b[i] for i in idx])
        if value is None:
            undefined += 1
            continue
        draws.append(value)

    if len(draws) < resamples * 0.5:
        return Estimate(
            point,
            n,
            note=(
                f"CI not reported: {undefined} of {resamples} resamples produced an "
                f"undefined kappa, which means the sample is too concentrated in one class "
                f"for a bootstrap to say anything."
            ),
        )
    draws.sort()
    low = draws[int(0.025 * len(draws))]
    high = draws[min(len(draws) - 1, int(0.975 * len(draws)))]
    note = f"{undefined} of {resamples} resamples dropped as undefined" if undefined else ""
    return Estimate(point, n, low, high, f"bootstrap-{resamples}", note)


# ------------------------------------------------------------------------ per class
def per_class_scores(
    truth: Sequence[str], predicted: Sequence[str], classes: Sequence[str]
) -> list[ClassScore]:
    """Precision, recall and F1 per class, with support. See `ClassScore` on the nulls."""
    scores = []
    for label in classes:
        tp = sum(1 for t, p in zip(truth, predicted, strict=True) if t == label and p == label)
        fp = sum(1 for t, p in zip(truth, predicted, strict=True) if t != label and p == label)
        fn = sum(1 for t, p in zip(truth, predicted, strict=True) if t == label and p != label)
        support = tp + fn
        n_predicted = tp + fp
        precision = tp / n_predicted if n_predicted else None
        recall = tp / support if support else None
        if precision is None or recall is None or (precision + recall) == 0:
            # Undefined, not zero. A class nobody labelled and nobody predicted has no
            # F1; a class predicted but never present has no recall to combine.
            f1 = None if support == 0 else 0.0
        else:
            f1 = 2 * precision * recall / (precision + recall)
        scores.append(ClassScore(label, precision, recall, f1, support, n_predicted))
    return scores


def confusion_matrix(
    truth: Sequence[str], predicted: Sequence[str], classes: Sequence[str]
) -> dict[str, dict[str, int]]:
    """`matrix[true_label][predicted_label]`. M2-3's iteration loop reads this every cycle.

    Every class appears as a row and a column even at zero, so the matrix has the same
    shape across runs and a class that vanishes is visible as a row of zeros rather than
    as a missing row.
    """
    matrix = {t: dict.fromkeys(classes, 0) for t in classes}
    for t, p in zip(truth, predicted, strict=True):
        if t in matrix and p in matrix[t]:
            matrix[t][p] += 1
    return matrix


def majority_class_baseline(truth: Sequence[str]) -> Estimate:
    """Share of the sample carrying the most common label (C5.5).

    **A κ published without this is unreadable**, and ADR-010 is the reason it is not a
    footnote: at 81% `linear`, a rater who labelled everything `linear` scores 81% raw
    agreement. κ corrects for that and corrects hard — under skewed marginals, high
    agreement routinely produces low κ.
    """
    n = len(truth)
    if n == 0:
        return Estimate(None, 0, note="no labels")
    label, top = Counter(truth).most_common(1)[0]
    return proportion(top, n, note=f"most common label: {label}")


def agreement(
    truth: Sequence[str], predicted: Sequence[str], classes: Sequence[str] = BEHAVIOR_CLASSES
) -> Agreement:
    """Everything C5.5 asks of one pair of label sequences, computed once."""
    if len(truth) != len(predicted):
        raise ValueError(f"sequences differ in length: {len(truth)} vs {len(predicted)}")
    n = len(truth)
    hits = sum(1 for t, p in zip(truth, predicted, strict=True) if t == p)
    raw = proportion(hits, n)
    baseline = majority_class_baseline(truth)
    delta = (
        round(100 * (raw.value - baseline.value), 2)
        if raw.value is not None and baseline.value is not None
        else None
    )
    present = {label for label in truth} | {label for label in predicted}
    return Agreement(
        kappa=bootstrap_kappa(truth, predicted),
        raw_agreement=raw,
        majority_baseline=baseline,
        agreement_over_baseline_pp=delta,
        per_class=per_class_scores(truth, predicted, classes),
        confusion=confusion_matrix(truth, predicted, classes),
        n=n,
        classes_absent=[label for label in classes if label not in present],
    )
