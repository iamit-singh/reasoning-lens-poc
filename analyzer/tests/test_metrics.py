"""The statistics, checked against the reference implementation — C5.5, M2-13.

**`rlens.metrics` hand-implements what C5.5 names `sklearn` for, and this file is the whole
justification for that trade.** scikit-learn stays a dev-only dependency so the analyzer
installs lean (I1); these tests install it anyway and assert agreement to 10 decimal places
on fixed cases *and* on hundreds of randomly generated label sequences. A hand-rolled κ
with a bug would publish a wrong headline number, which is the worst failure available to
this project — so the trade is only defensible if the numbers are checked, and here they
are.

The second half of the file is about the cases sklearn does **not** settle: what to return
when a metric is undefined. Those are judgement calls, they are made in ADR-010, and a
library cannot make them for us.
"""

from __future__ import annotations

import random

import pytest
from rlens import metrics as M

sklearn = pytest.importorskip("sklearn.metrics", reason="dev-only reference implementation")

CLASSES = M.BEHAVIOR_CLASSES


# ------------------------------------------------------------------ against sklearn
@pytest.mark.parametrize(
    "a,b",
    [
        (["a", "a", "b", "b"], ["a", "b", "b", "b"]),
        (["a", "b", "c", "a", "b", "c"], ["a", "b", "c", "a", "b", "c"]),
        (["a", "b", "c", "a", "b", "c"], ["c", "a", "b", "c", "a", "b"]),
        # The sklearn docs' own worked example.
        (
            ["negative", "positive", "negative", "neutral", "positive"],
            ["negative", "positive", "negative", "neutral", "negative"],
        ),
        # The shape this corpus actually has: overwhelmingly one class.
        (
            ["linear"] * 18 + ["verification", "subgoal_setting"],
            ["linear"] * 17 + ["verification", "linear", "subgoal_setting"],
        ),
    ],
)
def test_cohen_kappa_matches_sklearn(a: list[str], b: list[str]) -> None:
    assert M.cohen_kappa(a, b) == pytest.approx(sklearn.cohen_kappa_score(a, b), abs=1e-10)


def test_cohen_kappa_matches_sklearn_on_random_sequences() -> None:
    """**The test that actually earns the hand-implementation.**

    Fixed cases check the cases somebody thought of. 300 random sequences over a skewed
    class distribution check the ones nobody did — and the skew is not decoration, it is
    this corpus: 81% of steps are `linear` (ADR-010).
    """
    rng = random.Random(20261013)
    weights = [1, 1, 2, 2, 20]  # roughly the measured marginal
    mismatches = []
    for _ in range(300):
        n = rng.randrange(2, 60)
        a = rng.choices(CLASSES, weights=weights, k=n)
        b = rng.choices(CLASSES, weights=weights, k=n)
        ours, theirs = M.cohen_kappa(a, b), sklearn.cohen_kappa_score(a, b)
        if ours is None:
            # sklearn returns nan where kappa is undefined; we return None on purpose.
            assert theirs != theirs or theirs == 0.0
            continue
        if abs(ours - theirs) > 1e-10:
            mismatches.append((a, b, ours, theirs))
    assert not mismatches, f"{len(mismatches)} disagreements, first: {mismatches[0]}"


def test_per_class_f1_matches_sklearn() -> None:
    truth = ["linear"] * 12 + ["verification"] * 4 + ["subgoal_setting"] * 4
    pred = ["linear"] * 10 + ["verification"] * 2 + ["verification"] * 4 + ["linear"] * 4
    report = sklearn.classification_report(
        truth, pred, output_dict=True, zero_division=0, labels=list(CLASSES)
    )
    for score in M.per_class_scores(truth, pred, CLASSES):
        if score.support == 0:
            continue  # sklearn reports 0.0; we report None. See below.
        assert score.f1 == pytest.approx(report[score.label]["f1-score"], abs=1e-10)
        assert score.support == report[score.label]["support"]


def test_confusion_matrix_matches_sklearn() -> None:
    truth = ["linear", "linear", "verification", "backtracking", "linear"]
    pred = ["linear", "verification", "verification", "linear", "linear"]
    ours = M.confusion_matrix(truth, pred, CLASSES)
    theirs = sklearn.confusion_matrix(truth, pred, labels=list(CLASSES))
    for i, t in enumerate(CLASSES):
        for j, p in enumerate(CLASSES):
            assert ours[t][p] == theirs[i][j]


# ------------------------------------------------------------------ ADR-010's judgements
def test_f1_is_none_for_a_class_with_no_instances_not_zero() -> None:
    """**ADR-010's first decision, as an assertion.**

    `backtracking` has 0 instances in the entire corpus. Reporting its F1 as `0.00` says
    "the classifier is perfectly bad at this class" — a measurement claim made from no
    measurements, and exactly what I3 exists to prevent. sklearn's `zero_division=0` gives
    0.0 here, which is right for a library and wrong for a published page.
    """
    truth = ["linear"] * 10
    pred = ["linear"] * 10
    scores = {s.label: s for s in M.per_class_scores(truth, pred, CLASSES)}
    assert scores["backtracking"].support == 0
    assert scores["backtracking"].f1 is None
    assert scores["linear"].f1 == pytest.approx(1.0)


def test_kappa_is_none_rather_than_zero_when_both_raters_used_one_class() -> None:
    """Two raters who agreed on all 40 items must not be reported as "no agreement beyond
    chance". κ is undefined there — the denominator is zero — and on a corpus that is 81%
    one class this is a live case, not a curiosity."""
    assert M.cohen_kappa(["linear"] * 40, ["linear"] * 40) is None


def test_absent_classes_are_named_rather_than_left_to_inference() -> None:
    result = M.agreement(["linear"] * 8, ["linear"] * 8)
    assert set(result.classes_absent) == set(CLASSES) - {"linear"}


# ------------------------------------------------------------------ intervals
def test_wilson_interval_matches_a_published_worked_example() -> None:
    """Wilson, 95%, x=8 n=10 -> roughly (0.490, 0.943). Hand-checkable and standard."""
    low, high = M.wilson_interval(8, 10)
    assert low == pytest.approx(0.4901, abs=5e-4)
    assert high == pytest.approx(0.9433, abs=5e-4)


def test_wilson_stays_inside_zero_and_one_where_the_normal_approximation_does_not() -> None:
    """The reason C5.5 names Wilson. At 0 successes the normal approximation gives a
    symmetric interval straddling zero, which is not a proportion."""
    low, high = M.wilson_interval(0, 12)
    # `== 0.0` is too strict and the first run of this test proved it: the arithmetic
    # leaves 2.8e-17 of floating-point residue. The claim being made is that the interval
    # stays inside [0, 1], not that it lands on a float exactly.
    assert low == pytest.approx(0.0, abs=1e-12) and low >= 0.0
    assert 0 < high < 1
    low, high = M.wilson_interval(12, 12)
    assert high == pytest.approx(1.0, abs=1e-12) and high <= 1.0
    assert 0 < low < 1


def test_every_estimate_carries_its_n() -> None:
    """C5.5: "a metric emitted without n should be impossible, not discouraged"."""
    est = M.proportion(8, 10)
    assert est.n == 10 and est.low is not None and est.high is not None
    assert est.as_dict()["n"] == 10


def test_a_proportion_over_no_observations_is_none_with_a_note() -> None:
    est = M.proportion(0, 0)
    assert est.value is None and est.n == 0 and est.note


# ------------------------------------------------------------------ bootstrap
def test_the_bootstrap_is_seeded_so_a_published_ci_is_reproducible() -> None:
    """I3: a published number is reproducible or it is not published. An unseeded bootstrap
    moves the interval slightly every run and nothing distinguishes that from real drift."""
    rng = random.Random(7)
    a = rng.choices(CLASSES, weights=[1, 1, 2, 2, 20], k=80)
    b = rng.choices(CLASSES, weights=[1, 1, 2, 2, 20], k=80)
    first, second = M.bootstrap_kappa(a, b), M.bootstrap_kappa(a, b)
    assert (first.low, first.high) == (second.low, second.high)
    assert first.value == pytest.approx(sklearn.cohen_kappa_score(a, b), abs=1e-10)


def test_the_bootstrap_ci_brackets_the_point_estimate() -> None:
    rng = random.Random(11)
    a = rng.choices(CLASSES, weights=[3, 3, 3, 3, 8], k=120)
    b = [x if rng.random() > 0.25 else rng.choice(CLASSES) for x in a]
    est = M.bootstrap_kappa(a, b, resamples=400)
    assert est.low is not None and est.high is not None
    assert est.low <= est.value <= est.high


def test_undefined_resamples_are_dropped_and_counted_not_treated_as_zero() -> None:
    """Averaging an undefined resample in as 0.0 would drag the interval down by an amount
    that depends on how skewed the corpus is — biasing the number most on exactly the
    corpora where it matters most."""
    a = ["linear"] * 38 + ["verification", "backtracking"]
    b = ["linear"] * 38 + ["backtracking", "verification"]
    est = M.bootstrap_kappa(a, b, resamples=300)
    assert est.value is not None
    # Some resamples will draw 40 linears and produce an undefined kappa; the note must
    # say so rather than the interval silently absorbing them.
    if est.low is None:
        assert "undefined" in est.note
    else:
        assert est.note == "" or "dropped as undefined" in est.note


# ------------------------------------------------------------------ the whole block
def test_agreement_reports_the_baseline_beside_the_kappa() -> None:
    """**ADR-010's second decision.** A κ published without the majority-class baseline is
    unreadable: at 81% `linear` a rater who labelled everything `linear` scores 81% raw
    agreement."""
    truth = ["linear"] * 81 + ["verification"] * 12 + ["subgoal_setting"] * 7
    pred = ["linear"] * 78 + ["verification"] * 3 + ["verification"] * 12 + ["linear"] * 7
    result = M.agreement(truth, pred, CLASSES)

    assert result.n == 100
    assert result.majority_baseline.value == pytest.approx(0.81)
    assert result.raw_agreement.value is not None
    assert result.agreement_over_baseline_pp is not None
    # And the delta really is agreement minus baseline in percentage points.
    assert result.agreement_over_baseline_pp == pytest.approx(
        100 * (result.raw_agreement.value - 0.81), abs=1e-6
    )
    assert set(result.confusion) == set(CLASSES)


def test_mismatched_sequence_lengths_are_refused() -> None:
    """Silently zipping to the shorter one would drop labels and report a number computed
    over a sample nobody chose."""
    with pytest.raises(ValueError, match="differ in length"):
        M.agreement(["linear"] * 5, ["linear"] * 4)
