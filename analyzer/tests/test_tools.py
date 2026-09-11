"""Arm 3's tools. M1-7.

These are the parts of arm 3 that can be wrong *quietly*: a fumbled call fails loudly and
burns a turn, but a calculator returning the wrong number produces a confident wrong answer
with a plausible chain in front of it — the exact artifact this project exists to expose,
arriving from our own code.

So the emphasis here is on **totality and rejection**, not on happy-path arithmetic: every
input must produce a well-formed observation, and every input that should be refused must
actually be refused.
"""

from __future__ import annotations

import json
import pathlib

import pytest
from rlens.runner.tools import (
    ToolError,
    calculator,
    call_tool,
    load_corpus,
    lookup,
    tool_schemas,
)

CORPUS = {
    "fairhaven_population": "128400",
    "brightwater_population": "96750",
    "meridian_institute_departments": "metallurgy, hydrology, cartography",
}


# ------------------------------------------------------------------ calculator
@pytest.mark.parametrize(
    ("expression", "want"),
    [
        ("2+2", "4"),
        ("(47 * 21) * 385 / 1000", "379.995"),
        ("floor((47 * 21) * 385 / 1000)", "379"),  # mb-06's actual shape
        ("12500 * 0.074 * 3.5", "3237.5"),  # mb-07's actual shape
        ("128400 - 96750", "31650"),  # mb-08's actual shape
        ("2 ** 10", "1024"),
        ("round(3.14159, 2)", "3.14"),
        ("-5 + 3", "-2"),
        ("7 // 2", "3"),
        ("10 % 3", "1"),
        ("sqrt(144)", "12"),
        ("max(3, 9, 2)", "9"),
    ],
)
def test_calculator_evaluates_the_shapes_the_bank_needs(expression: str, want: str) -> None:
    assert calculator(expression) == want


def test_an_integral_float_loses_its_trailing_zero() -> None:
    """`379.0` going back to the model invites `379.0` coming back as the answer.

    `checkers.exact` would accept it, so this is not a correctness bug — but the tool
    should not manufacture a formatting decision for the model to get wrong.
    """
    assert calculator("758.0 / 2") == "379"
    assert calculator("1 / 3") == "0.3333333333"


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('echo pwned')",
        "open('/etc/passwd').read()",
        "[1,2,3]",
        "'abc' * 3",
        "x + 1",
        "lambda: 1",
        "2 + ",
        "",
        "   ",
    ],
)
def test_the_calculator_refuses_anything_that_is_not_arithmetic(expression: str) -> None:
    """The expression comes from a language model — an untrusted input channel in exactly
    the sense that matters. `eval` here would be arbitrary code execution in the runner's
    own process, so the whitelist is the security boundary and it is tested as one."""
    with pytest.raises(ToolError):
        calculator(expression)


def test_division_by_zero_is_a_named_rejection_not_a_crash() -> None:
    for expression in ("1/0", "1//0", "1%0"):
        with pytest.raises(ToolError, match="division by zero"):
            calculator(expression)


def test_a_huge_exponent_is_refused_before_it_is_computed() -> None:
    """`9**9**9` is three tokens and would hang the process building an integer with
    hundreds of millions of digits. The cap is checked before the operation, not after —
    checking after is not a cap."""
    with pytest.raises(ToolError, match="exceeds the cap"):
        calculator("9 ** 9 ** 9")


def test_the_two_unicode_operators_a_model_actually_writes_are_normalised() -> None:
    # Escapes, not literals: MULTIPLICATION SIGN and DIVISION SIGN must be
    # distinguishable from `x` and `/` by a reviewer reading the diff.
    assert calculator("6 \u00d7 7") == "42"
    assert calculator("84 \u00f7 2") == "42"
    assert calculator("2+2=") == "4"


# ------------------------------------------------------------------ lookup
def test_lookup_hits_on_an_exact_key() -> None:
    assert lookup("fairhaven_population", CORPUS) == "128400"


def test_lookup_normalises_case_and_spacing_and_nothing_else() -> None:
    """Casefold and space-to-underscore only — the same normalisation `checkers.normalise`
    applies to answers. Substring matching or stopword stripping would reintroduce the
    fuzzy matching lever L2 removed, and would let a lookup succeed against a fact the
    model did not ask for."""
    assert lookup("Fairhaven_Population", CORPUS) == "128400"
    assert lookup("  fairhaven population  ", CORPUS) == "128400"
    # Deliberately a MISS: this is the phrasing the model used before the keys were
    # advertised, and matching it would be fuzzy matching by another name.
    assert lookup("population of Fairhaven", CORPUS).startswith("NOT FOUND:")


def test_a_miss_is_a_well_formed_observation_that_names_the_keys() -> None:
    """C4.1's DoD asks for "a well-formed negative observation rather than an exception".

    It lists the available keys because `max_turns` is 6: a miss that says nothing useful
    spends a turn and leaves the model in the state that caused the miss. Listing the keys
    turns a wasted turn into a recoverable one.
    """
    observation = lookup("population_of_atlantis", CORPUS)
    assert observation.startswith("NOT FOUND:")
    for key in CORPUS:
        assert key in observation


def test_lookup_refuses_an_empty_query() -> None:
    with pytest.raises(ToolError):
        lookup("", CORPUS)


# ------------------------------------------------------------------ dispatch
def test_call_tool_never_raises_and_reports_whether_the_tool_answered() -> None:
    """`ok` is recorded, not inferred. "Did the tool actually answer?" is a question the
    metrics need, and a substring search for "NOT FOUND" in the output is a
    re-derivation of something the tool already knew."""
    assert call_tool("calculator", {"expression": "2+2"}, CORPUS) == ("4", True)
    assert call_tool("lookup", {"query": "fairhaven_population"}, CORPUS) == ("128400", True)

    for name, args in [
        ("calculator", {"expression": "1/0"}),
        ("calculator", {}),
        ("lookup", {}),
        ("lookup", {"query": "nope"}),
        ("nonexistent_tool", {"anything": 1}),
    ]:
        observation, ok = call_tool(name, args, CORPUS)
        assert not ok, (name, args)
        assert observation.strip(), "an unhelpful observation still has to be an observation"


def test_unparseable_arguments_reach_the_tool_as_a_visible_bad_call() -> None:
    """`llm.py` keeps arguments it could not parse as `{"_raw": ...}` rather than dropping
    them. S6 measured 20/20 well-formed calls — on four short prompts, not a six-turn loop
    with tool results fed back in, and S6's own write-up says so."""
    observation, ok = call_tool("calculator", {"_raw": "not json at all"}, CORPUS)
    assert not ok
    assert "expression" in observation


# ------------------------------------------------------------------ the wire contract
def test_the_lookup_schema_advertises_every_key() -> None:
    """ADR-007: this is load-bearing under L2. Probed before arm 3 was built — with an
    unlisted description the model asked for `"population of Fairhaven"`, which misses
    every time under exact match. L2 forbids fuzzy matching, so making the contract
    discoverable is the only move left inside the lever."""
    schemas = tool_schemas(CORPUS)
    lookup_schema = next(s for s in schemas if s["function"]["name"] == "lookup")
    description = lookup_schema["function"]["description"]
    for key in CORPUS:
        assert key in description, f"{key} is not discoverable by the model"


def test_both_tools_are_declared_in_the_shape_the_wire_expects() -> None:
    schemas = tool_schemas(CORPUS)
    assert {s["function"]["name"] for s in schemas} == {"calculator", "lookup"}
    for schema in schemas:
        fn = schema["function"]
        assert schema["type"] == "function"
        assert fn["description"].strip()
        params = fn["parameters"]
        assert params["type"] == "object"
        assert params["required"], f"{fn['name']} declares no required argument"
        for required in params["required"]:
            assert required in params["properties"]


# ------------------------------------------------------------------ the committed corpus
@pytest.mark.contract
def test_the_committed_corpus_holds_l2s_twelve_facts() -> None:
    facts = load_corpus(str(pathlib.Path(__file__).parents[2] / "problem-bank/corpus/facts.json"))
    assert len(facts) == 12, f"lever L2 fixes the corpus at 12 facts, found {len(facts)}"
    assert all(isinstance(v, str) and v.strip() for v in facts.values())


@pytest.mark.contract
def test_the_corpus_holds_the_four_facts_the_bank_items_already_depend_on() -> None:
    """`mb-08`/`mb-09`/`mb-10` were committed in M1-4, BEFORE this corpus existed, and
    `problem-bank/README.md` specifies the facts they need rather than leaving M1-7 to
    infer them. An item whose lookup returns nothing is not a `tool_required` item, it is
    a broken one — and `test_bank_answers.py` cannot detect that, only arm-3 runs can."""
    root = pathlib.Path(__file__).parents[2]
    facts = load_corpus(str(root / "problem-bank/corpus/facts.json"))
    required = {
        "fairhaven_population": "128400",
        "brightwater_population": "96750",
        "meridian_institute_founded": "1887",
        "meridian_institute_departments": "metallurgy, hydrology, cartography",
    }
    for key, value in required.items():
        assert facts.get(key) == value, (
            f"{key}: corpus says {facts.get(key)!r}, README says {value!r}"
        )

    # And the arithmetic the items assert must follow from the corpus, not merely sit
    # beside it: mb-08 claims the difference is 31650.
    difference = int(facts["fairhaven_population"]) - int(facts["brightwater_population"])
    mb08 = json.loads((root / "problem-bank/items/mb-08.json").read_text())
    assert str(difference) == mb08["known_answer"], (
        f"mb-08 expects {mb08['known_answer']} but the corpus yields {difference}"
    )

    mb09 = json.loads((root / "problem-bank/items/mb-09.json").read_text())
    assert facts["meridian_institute_founded"] == mb09["known_answer"]

    mb10 = json.loads((root / "problem-bank/items/mb-10.json").read_text())
    assert {d.strip() for d in facts["meridian_institute_departments"].split(",")} == set(
        mb10["known_answer"]
    )
