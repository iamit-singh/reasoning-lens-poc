"""Arm 3's two tools: `calculator(expression)` and `lookup(query)`. C4.1, lever L2.

Owner: M1-7.

The tools are the only part of arm 3 that can be wrong *quietly*. A loop that fumbles a
call fails loudly and burns a turn; a calculator that returns the wrong number, or a lookup
that misses when the fact is right there, produces a confident wrong answer with a
plausible chain in front of it -- which is exactly the artifact this project exists to make
visible, arriving from our own code instead of the model's.

So both tools are **total**: they return a well-formed observation for every input,
including an input they reject. C4.1's DoD names this for `lookup` ("a lookup miss returns
a well-formed negative observation rather than an exception"), and it is just as true of
the calculator -- an exception out of a tool kills the turn and the model never learns what
it did wrong.

Why the calculator does not use `eval`
--------------------------------------
The expression comes from a language model, which is an untrusted input channel in exactly
the sense that matters: `eval` on it is arbitrary code execution in the runner's process.
`_eval_node` walks an `ast` tree against a whitelist of operators instead. That also makes
the failure modes *nameable* -- `unsupported operation` rather than a stack trace -- which
is what lets the loop recover inside `max_turns`.
"""

from __future__ import annotations

import ast
import json
import math
import operator
import pathlib
from collections.abc import Callable
from typing import Any

from rlens.runner.paths import data_path, missing_data_message

#: Lever L2: 12 facts, **exact match only** -- no fuzzy matching, no embedding lookup.
CORPUS_PATH_DEFAULT = "problem-bank/corpus/facts.json"

#: Operators the calculator accepts. A whitelist, so anything not listed is a named
#: rejection rather than a surprise. No bitwise ops: they are not arithmetic a word
#: problem needs, and `^` meaning XOR rather than exponentiation is a classic wrong-answer
#: generator when a model writes `2^10`.
_BINOPS: dict[type[ast.AST], Callable[..., Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS: dict[type[ast.AST], Callable[..., Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

#: Functions a word problem plausibly needs. `round` is the one that earns its place:
#: several bank items ask for a figure "rounded down" or "to the nearest", and a model
#: that has to do that in its head is being tested on something other than tool use.
_FUNCS: dict[str, Any] = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "floor": math.floor,
    "ceil": math.ceil,
    "sqrt": math.sqrt,
}

#: Guard against an expression whose *result* is enormous -- `9**9**9` is three tokens and
#: will hang the process computing an integer with hundreds of millions of digits. The
#: exponent cap is checked before the operation, not after.
_MAX_EXPONENT = 64
_MAX_EXPRESSION_CHARS = 500


class ToolError(ValueError):
    """A rejected input. Carried to the model as an observation, never raised past the loop."""


# ------------------------------------------------------------------ calculator
def _eval_node(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ToolError(f"only numbers are allowed, got {node.value!r}")
        return node.value
    if isinstance(node, ast.BinOp):
        op = _BINOPS.get(type(node.op))
        if op is None:
            raise ToolError(f"unsupported operator {type(node.op).__name__}")
        left, right = _eval_node(node.left), _eval_node(node.right)
        if op is operator.pow and abs(right) > _MAX_EXPONENT:
            raise ToolError(f"exponent {right} exceeds the cap of {_MAX_EXPONENT}")
        if op in (operator.truediv, operator.floordiv, operator.mod) and right == 0:
            raise ToolError("division by zero")
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op_u = _UNARYOPS.get(type(node.op))
        if op_u is None:
            raise ToolError(f"unsupported unary operator {type(node.op).__name__}")
        return op_u(_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _FUNCS:
            name = getattr(node.func, "id", type(node.func).__name__)
            raise ToolError(f"unknown function {name!r}; available: {sorted(_FUNCS)}")
        if node.keywords:
            raise ToolError("keyword arguments are not supported")
        return _FUNCS[node.func.id](*(_eval_node(a) for a in node.args))
    raise ToolError(f"unsupported expression element {type(node).__name__}")


def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression. Returns the result, or a named rejection.

    The return is a string because that is what goes back to the model as an observation,
    and because a float formatted by `repr` is the shape a model reads most reliably.
    Integral results are rendered without a trailing `.0`: a model that sees `379.0` has
    a fair chance of answering `379.0` to a question asking for whole kilowatts, and
    `checkers.exact` would accept that -- but a model that sees `379` has no such
    decision to make, and the tool should not create work for the grader.
    """
    if not isinstance(expression, str) or not expression.strip():
        raise ToolError("expression must be a non-empty string")
    if len(expression) > _MAX_EXPRESSION_CHARS:
        raise ToolError(f"expression exceeds {_MAX_EXPRESSION_CHARS} characters")
    # A model sometimes writes the expression the way a person would type it into a
    # calculator. These two are unambiguous and are normalised rather than rejected;
    # anything more would be guessing at intent.
    # Written as escapes, not literals: these are the Unicode MULTIPLICATION and DIVISION
    # SIGNS, and a reviewer must be able to tell them from `x` and `/` at a glance.
    cleaned = expression.strip().replace("\u00d7", "*").replace("\u00f7", "/").rstrip("=")
    try:
        tree = ast.parse(cleaned, mode="eval")
    except SyntaxError as exc:
        raise ToolError(f"could not parse {cleaned!r}: {exc.msg}") from exc
    value = _eval_node(tree)
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.10g}"
    return str(value)


# ------------------------------------------------------------------ lookup
def load_corpus(path: str | None = None) -> dict[str, str]:
    """Read the fact corpus as DATA.

    Read, never imported -- `.importlinter`'s I1 contract forbids `rlens` importing
    `problem_bank`, and the corpus is an input the analyzer happens to be pointed at.
    """
    p = pathlib.Path(path) if path else data_path(CORPUS_PATH_DEFAULT, env_var="CORPUS_PATH")
    if not p.exists():
        # A ToolError here would be swallowed by the loop into a well-formed "no fact
        # corpus" observation, and arm 3 would answer wrong on a green run. The corpus
        # being absent is a configuration failure, not a tool result -- so it is raised
        # as one, loudly, before any turn is spent. See `paths.py`.
        raise FileNotFoundError(missing_data_message(CORPUS_PATH_DEFAULT, "CORPUS_PATH"))
    data = json.loads(p.read_text())
    facts: dict[str, str] = data["facts"]
    return facts


def _normalise_key(query: str) -> str:
    """Casefold and trim. **This is the whole of the matching, deliberately.**

    L2 is explicit: *exact match only, no fuzzy matching, no embedding lookup*. Casefolding
    and trimming are the same normalisation `checkers.normalise` applies to answers -- they
    make `Fairhaven_Population` and `fairhaven_population` one key rather than two
    spellings. Substring matching, stopword stripping or token overlap would each be a
    silent reintroduction of the fuzzy matching L2 removed, and each would let a lookup
    succeed against a fact the model did not ask for.

    The discoverability problem this leaves is solved where it belongs -- in the tool
    DESCRIPTION, which lists every available key. See `tool_schemas`.
    """
    return query.strip().casefold().replace(" ", "_")


def lookup(query: str, corpus: dict[str, str] | None = None) -> str:
    """Look up one fact by key. A miss is an observation, not an exception.

    **The negative observation names the available keys.** C4.1's DoD asks only for it to
    be "well-formed", but a miss that says nothing useful spends a turn and leaves the
    model in exactly the state that caused the miss -- and `max_turns` is 6. Listing the
    keys turns a wasted turn into a recoverable one, which is the difference between a
    `tool_required` item that measures tool use and one that measures luck.
    """
    facts = corpus if corpus is not None else load_corpus()
    if not isinstance(query, str) or not query.strip():
        raise ToolError("query must be a non-empty string")
    key = _normalise_key(query)
    if key in facts:
        return facts[key]
    return (
        f"NOT FOUND: no fact is stored under {query!r}. This corpus is matched EXACTLY, "
        f"so the key must be given verbatim. Available keys: {', '.join(sorted(facts))}"
    )


# ------------------------------------------------------------------ the wire contract
def tool_schemas(corpus: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """The two tool definitions, in the OpenAI function-calling shape both tiers speak.

    **The `lookup` description enumerates the keys, and that is load-bearing.** Probed
    before this was written: asked for the population of Fairhaven with an unlisted
    description, the model called `lookup{"query": "population of Fairhaven"}` -- a
    perfectly sensible phrasing that misses every time under exact match. Under L2 the
    options are to relax the matching or to make the contract discoverable, and only the
    second stays inside the lever.

    This does not scale past a few dozen facts, and it does not have to: L2 fixes the
    corpus at 12. If the corpus grows, the description stops being the right mechanism and
    that is a decision to record, not a limit to paper over.
    """
    facts = corpus if corpus is not None else load_corpus()
    keys = ", ".join(sorted(facts))
    return [
        {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": (
                    "Evaluate an arithmetic expression and return the numeric result. "
                    "Supports + - * / // % ** and the functions "
                    "abs, round, min, max, floor, ceil, sqrt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {
                            "type": "string",
                            "description": "e.g. '(47 * 21) * 385 / 1000'",
                        }
                    },
                    "required": ["expression"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "lookup",
                "description": (
                    "Look up a stored fact by its exact key. The key must be given "
                    f"verbatim; matching is exact. Available keys: {keys}."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "one of the exact keys listed in this description",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
    ]


def tool_descriptions(corpus: dict[str, str] | None = None) -> dict[str, str]:
    """Name -> description, for the TOOL span's `tool.description` attribute.

    The stock LangGraph trace S2 captured carries that attribute, so ours does too --
    same reasoning as ADR-002: converge on the names real instrumentation emits so the
    analyzer has one code path for our trees and for a third-party tree.
    """
    return {s["function"]["name"]: s["function"]["description"] for s in tool_schemas(corpus)}


#: Dispatch table. `lookup` is bound to a corpus by the loop so the file is read once per
#: run rather than once per call -- and so a test can inject one.
TOOL_NAMES = ("calculator", "lookup")


def call_tool(name: str, arguments: dict[str, Any], corpus: dict[str, str]) -> tuple[str, bool]:
    """Execute one tool call. Returns `(observation, ok)`; never raises for bad input.

    `ok` is False for a rejected call and for a `lookup` miss. It is recorded on the span
    rather than inferred from the text, because "did the tool actually answer?" is a
    question the metrics need and a substring search for "NOT FOUND" is not an answer to
    it.
    """
    try:
        if name == "calculator":
            expression = arguments.get("expression")
            if expression is None:
                raise ToolError("calculator requires an 'expression' argument")
            return calculator(str(expression)), True
        if name == "lookup":
            query = arguments.get("query")
            if query is None:
                raise ToolError("lookup requires a 'query' argument")
            observation = lookup(str(query), corpus)
            return observation, not observation.startswith("NOT FOUND:")
        return (
            f"ERROR: no tool named {name!r}. Available tools: {', '.join(TOOL_NAMES)}",
            False,
        )
    except ToolError as exc:
        return f"ERROR: {exc}", False
