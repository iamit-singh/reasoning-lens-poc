"""The calibration sampling frame — C5.1's two parts, and the rules that keep them apart.

**These assertions exist because the two halves of the frame do different jobs and only
one of them can carry the published number.** The random-90 is a uniform draw whose
sampling is independent of anything the classifier did; the enriched-60 is deliberately
over-sampled from classes the classifier calls rare, so that per-class F1 has instances to
compute over at all. Mixing them silently would make κ a number about a sample chosen by
the thing being measured.

The specific failure this guards against is **backfilling**: a rare class that cannot
reach its enrichment target invites topping it up from the random pool, which takes steps
out of the half that carries the published κ to prop up the half that does not. Trigger
t13 pre-decides the answer — label what exists, publish the actual n — and these tests
make the refusal checkable rather than remembered.
"""

from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SAMPLING = ROOT / "calibration/sampling.json"

#: C5.1's enrichment target per rare class. The draw takes *up to* this many.
PER_CLASS_TARGET = 15

#: C5.1: dev = the first 40 of the random-90, plus the enriched half.
DEV_FROM_RANDOM = 40


@pytest.fixture(scope="module")
def record() -> dict:
    if not SAMPLING.is_file():
        pytest.skip("no calibration/sampling.json")
    return json.loads(SAMPLING.read_text())


def test_the_random_draw_is_recorded_with_its_seed(record: dict) -> None:
    """A draw that cannot be reproduced from its seed is a selection, not a sample."""
    draw = record.get("draw") or {}
    assert draw.get("seed") is not None, "the random-90 has no committed seed"
    assert draw.get("ordered_step_ids"), "the random-90 has no ordered id list"
    ids = draw["ordered_step_ids"]
    assert len(ids) == len(set(ids)), "the random-90 contains a duplicate step_id"


def _enriched(record: dict) -> dict:
    enriched = record.get("enriched")
    if not enriched:
        pytest.skip("no enriched draw yet -- run `make draw-enriched` (M2-14)")
    return enriched


def test_the_enriched_draw_is_recorded_with_its_seed_and_bundle(record: dict) -> None:
    """The bundle version is part of the provenance, not decoration.

    The enriched half is selected *by the classifier's predictions*, so which prompt
    bundle produced them is the difference between a reproducible draw and a draw nobody
    can re-derive.
    """
    enriched = _enriched(record)
    assert enriched.get("seed") is not None
    assert enriched.get("prompt_bundle_version"), "no bundle version on the enriched draw"
    assert enriched.get("enrichment_factor") is not None, "the enrichment factor is the point"


def test_the_two_halves_are_disjoint(record: dict) -> None:
    """**The rule the whole frame rests on.** A step in both halves would be labelled once
    and counted twice, in a dev number and a held-out number that are supposed to be
    independent."""
    enriched = _enriched(record)
    rnd = set(record["draw"]["ordered_step_ids"])
    enr = enriched["ordered_step_ids"]
    assert len(enr) == len(set(enr)), "the enriched draw contains a duplicate step_id"
    overlap = rnd & set(enr)
    assert not overlap, (
        f"{len(overlap)} step(s) are in BOTH halves, e.g. {sorted(overlap)[:3]}. The "
        f"enriched half is drawn from the pool REMAINING after the random-90 precisely so "
        f"this cannot happen."
    )


def test_no_class_was_backfilled_past_its_candidates(record: dict) -> None:
    """t13's refusal, made checkable.

    A class may take *fewer* than the target — that is the shortfall the trigger is about.
    It may never take *more* than the candidates that existed, which is what backfilling
    from the random pool would look like in the record.
    """
    enriched = _enriched(record)
    per_class = enriched["per_class"]
    for cls, row in per_class.items():
        selected, candidates = row["selected"], row["candidates_in_remaining_pool"]
        assert selected <= candidates, (
            f"{cls}: {selected} selected from {candidates} candidates. The extra rows came "
            f"from somewhere, and the only pool available is the one carrying the "
            f"published kappa."
        )
        assert selected == min(candidates, PER_CLASS_TARGET), (
            f"{cls}: took {selected}, expected min({candidates}, {PER_CLASS_TARGET})"
        )
    assert enriched["selected_total"] == sum(r["selected"] for r in per_class.values())
    assert enriched["selected_total"] == len(enriched["ordered_step_ids"])


def test_a_shortfall_is_recorded_rather_than_rounded_away(record: dict) -> None:
    """If a class came up short, the record must say so and t13 must read as fired.

    **The failure mode is silence**, not a wrong number: a draw that quietly returned 31
    where the plan says 60 would be read at G2 as though the frame had been filled.
    """
    enriched = _enriched(record)
    short = [c for c, r in enriched["per_class"].items() if r["short_of_target"]]
    assert sorted(short) == sorted(enriched["classes_that_could_not_reach_target"])
    fired = enriched["trigger_t13"].startswith("FIRED")
    assert fired == bool(short), (
        f"t13 reads {'fired' if fired else 'not fired'} but {len(short)} class(es) are short"
    )
    if short:
        assert "backfill" in enriched["trigger_t13"].lower(), (
            "a fired t13 must carry its pre-decided action, which is the refusal to backfill"
        )


def test_the_dev_split_arithmetic_is_whatever_it_actually_is(record: dict) -> None:
    """C5.1 calls it *dev-100*; the corpus decides whether it is 100.

    This does not assert 100. It asserts the recorded parts add up, so the G2 report
    quotes the real denominator rather than the plan's intended one — `dev-100.jsonl` with
    71 rows is honest, and a file named for a number it does not contain is not.
    """
    enriched = _enriched(record)
    dev_n = DEV_FROM_RANDOM + enriched["selected_total"]
    assert dev_n == DEV_FROM_RANDOM + len(enriched["ordered_step_ids"])
    assert enriched["target"] - enriched["selected_total"] == enriched["short_of_target_total"]
