"""Deterministic segmentation of a trace into steps. C4.2. **No LLM.**

Owner: M1-8. **This module is frozen at `segmenter-frozen-v1`.**

Why the freeze matters more than the algorithm
---------------------------------------------
`step_id` is `"{strategy}:{span_id}:{ordinal}"` and the ordinal comes from here. Every
label a human writes in Month 2 joins on that id. **Any change to this file after labelling
begins renumbers the ordinals and silently detaches every label from its text** — Hazard 1
in the Month-1 breakdown, and the reason C4.2 insists segmentation be deterministic rather
than merely sensible: κ measured against a moving target is not a measurement.

So the bar here is not "reasonable segmentation". It is **byte-identical output, on every
machine, forever, with no network and no optional dependency.** Two consequences shaped the
code below.

### The token unit is a WORD, and that is a deliberate amendment to C4.2

C4.2 specifies a 15-token merge and a 200-token split cap without naming a tokenizer. The
obvious reading is the model's own encoding — but `tiktoken.get_encoding("o200k_harmony")`
**fetches a remote BPE file** and caches it in a temp directory. A segmenter whose
thresholds depend on whether that download succeeded is not byte-stable, and the failure is
invisible: it does not error, it segments differently, and every `step_id` shifts.

So steps are measured in **whitespace-delimited words**, which needs nothing and cannot
drift. The thresholds are converted rather than reinterpreted — measured over the project's
own committed traces, **7,531 words against 10,890 harmony tokens, a pooled ratio of 1.446
tokens per word**:

| C4.2 | In words, at the measured ratio | Constant |
| --- | --- | --- |
| merge under 15 tokens | 10.4 | `MERGE_UNDER_WORDS = 10` |
| split over 200 tokens | 138.3 | `SPLIT_OVER_WORDS = 138` |

`138` is kept rather than rounded to a tidier number because it is *derived*; a round number
here would be a guess wearing the authority of a constant. See ADR-008.

### Nothing is copied until the end

Every stage works on `(start, end)` index pairs into one normalised source string. Offsets
are therefore exact by construction, and `char_range` indexes something the trace actually
carries (`NormalizedTrace.source_text`) rather than a string that was reconstructed later by
different code.
"""

from __future__ import annotations

import itertools
import re

from rlens.checkers import final_answer_line
from rlens.contracts import NormalizedTrace, Step
from rlens.ingest.otel import LlmCall, ParsedTrace, ToolUse

# ---------------------------------------------------------------- thresholds (see above)
#: C4.2's 15-token merge, converted at the measured 1.446 tokens/word. Kills the one-word
#: steps that poison per-class F1.
MERGE_UNDER_WORDS = 10

#: C4.2's 200-token split cap, converted the same way. S3 (M1-12) measures whether steps
#: this long return well-formed classifier rows; **if they do not, this constant changes
#: BEFORE the freeze tag**, per breakdown §5.3.
SPLIT_OVER_WORDS = 138

#: C4.2's discourse markers, verbatim. Two carry a trailing space in the plan (`"But "`,
#: `"So "`) and that is preserved -- without it `So` matches `Software`. The others get a
#: word boundary for the same reason: `Thus` must not fire on `Thusly`.
DISCOURSE_MARKERS = (
    "Wait",
    "Hmm",
    "Actually",
    "Alternatively",
    "But ",
    "However",
    "Let me",
    "Let's",
    "First",
    "Second",
    "Next",
    "Then",
    "So ",
    "Therefore",
    "Thus",
    "Check",
    "Verify",
    "Now",
    "Instead",
    "Hold on",
    "Recall",
)

_DISCOURSE_RE = re.compile(
    "|".join(re.escape(m) if m.endswith(" ") else re.escape(m) + r"\b" for m in DISCOURSE_MARKERS)
)

#: C4.2's list markers, verbatim.
_LIST_RE = re.compile(r"\s*(\d+[.)]|[-*]|Step \d+)")

#: Provider markup. `llm.py` already strips `<think>` on the way in; this is the second
#: line of defence for a tree that arrived from somewhere else.
_THINK_RE = re.compile(r"</?think>")

#: Regions no split may land inside. C4.2 names fenced code blocks and LaTeX `\[ … \]`;
#: `\( … \)` and `$$ … $$` are the same hazard with different delimiters and were both
#: observed in real answers (`mb-12` closed with `\(\$0.30\)`, `mb-11` with a `\[ … \]`
#: block whose content line carries four numbers).
_FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.DOTALL)

#: An **unterminated** fence opener. A truncated response ends mid-block -- S3 measured
#: `finish_reason: "length"` on this runtime -- and C4.2 says never split inside a fenced
#: block, not "never split inside a fence that happens to close". Verified before the
#: freeze: without this, a 70-word trace ending mid-fence split into four steps, three of
#: them lines of code.
_OPEN_FENCE_RE = re.compile(r"```|~~~")
_MATH_RE = re.compile(r"\\\[.*?\\\]|\\\(.*?\\\)|\$\$.*?\$\$", re.DOTALL)

#: A sentence ends at `.`/`!`/`?` followed by whitespace. Deliberately not a real sentence
#: tokenizer: those carry models, locale data and version-to-version behaviour changes --
#: every one of which is a way for this file's output to move under a frozen tag.
_SENTENCE_END_RE = re.compile(r"[.!?]+\s+")


def normalise_text(raw: str) -> str:
    """Newlines, provider markup, outer whitespace. Idempotent, and offsets follow it.

    Unicode spaces are deliberately **left alone**. The model emits NARROW NO-BREAK SPACE
    (U+202F) between a word and a number -- `Day<U+202F>46` -- and `str.split()` already
    treats it as whitespace, so nothing needs rewriting. Rewriting it would alter text the
    UI highlights and a human annotator reads, for no gain.
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = _THINK_RE.sub("", text)
    return text.strip()


def word_count(text: str) -> int:
    """The segmenter's token unit. See the module docstring."""
    return len(text.split())


# ---------------------------------------------------------------- protected regions
def _protected(text: str) -> list[tuple[int, int]]:
    """Ranges a split may not land inside. Fences win over maths, and they may nest it.

    Order matters: a code fence can *contain* `\\[`, so fences are matched first and maths
    is only matched outside them. Doing it the other way round lets a stray delimiter
    inside a code block protect half the document.
    """
    ranges = [m.span() for m in _FENCE_RE.finditer(text)]
    # An unterminated fence protects to the end of the text. Only the FIRST such opener
    # matters -- everything after it is already inside it.
    for m in _OPEN_FENCE_RE.finditer(text):
        if not any(lo <= m.start() < hi for lo, hi in ranges):
            ranges.append((m.start(), len(text)))
            break
    for m in _MATH_RE.finditer(text):
        if not any(lo <= m.start() < hi for lo, hi in ranges):
            ranges.append(m.span())
    return sorted(ranges)


def _inside(pos: int, ranges: list[tuple[int, int]]) -> bool:
    return any(lo < pos < hi for lo, hi in ranges)


# ---------------------------------------------------------------- the text path (C4.2 §2)
def _paragraphs(text: str, protected: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """C4.2 2b: split on blank lines -- but not on a blank line inside a code fence."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in re.finditer(r"\n[ \t]*\n\s*", text):
        if _inside(m.start(), protected):
            continue
        if m.start() > start:
            spans.append((start, m.start()))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [_tighten(text, s, e) for s, e in spans if text[s:e].strip()]


def _tighten(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim whitespace off a range without copying it. Keeps `char_range` meaningful."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def _sentence_starts(
    text: str, start: int, end: int, protected: list[tuple[int, int]]
) -> list[int]:
    """Positions inside `(start, end)` where a new sentence or line begins.

    Both kinds are needed: C4.2's discourse markers follow sentence punctuation, while its
    list markers usually follow a bare newline (`1. …\\n2. …`) with no punctuation at all.
    """
    candidates: list[int] = []
    for m in _SENTENCE_END_RE.finditer(text, start, end):
        if m.end() < end and not _inside(m.start(), protected):
            candidates.append(m.end())
    for m in re.finditer(r"\n", text[start:end]):
        pos = start + m.end()
        if pos < end and not _inside(pos - 1, protected):
            candidates.append(pos)
    return sorted(set(candidates))


def _starts_with_marker(text: str, pos: int) -> bool:
    """C4.2 2c: a discourse marker, or a list marker at the start of a line."""
    if _DISCOURSE_RE.match(text, pos):
        return True
    m = _LIST_RE.match(text, pos)
    return bool(m and m.end() > m.start())


def _split_paragraph(
    text: str, start: int, end: int, protected: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """C4.2 2c: split *before* each marker-initial sentence."""
    cuts = [
        p for p in _sentence_starts(text, start, end, protected) if _starts_with_marker(text, p)
    ]
    bounds = [start, *cuts, end]
    out: list[tuple[int, int]] = []
    for lo, hi in itertools.pairwise(bounds):
        s, e = _tighten(text, lo, hi)
        if e > s:
            out.append((s, e))
    return out


def _merge_short(text: str, spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """C4.2 2d: merge any fragment under the threshold into the previous step.

    **The first fragment has no previous, and C4.2 does not say.** It merges FORWARD
    instead. The rule exists to kill one-word steps that poison per-class F1, and a text
    opening with `"Wait."` produces exactly such a step; leaving it because it happens to
    be first would honour the letter of the rule and miss its point. Forward is also the
    only direction available, so there is nothing to choose between.
    """
    if not spans:
        return []
    merged: list[tuple[int, int]] = []
    pending: tuple[int, int] | None = None
    for span in spans:
        if pending is not None:
            span = (pending[0], span[1])
            pending = None
        if word_count(text[span[0] : span[1]]) < MERGE_UNDER_WORDS:
            if merged:
                merged[-1] = (merged[-1][0], span[1])
            else:
                pending = span  # nothing before it: carry it into the next span
            continue
        merged.append(span)
    if pending is not None:
        # A whole trace shorter than the threshold is one step, not zero. The merge rule
        # trims noise; it must never delete the only content there is.
        merged.append(pending)
    return merged


def _split_long(
    text: str, span: tuple[int, int], protected: list[tuple[int, int]]
) -> list[tuple[int, int]]:
    """C4.2 2e: split a step over the cap at the sentence boundary nearest its midpoint,
    repeatedly.

    Two things are pinned down because C4.2 leaves them open and a frozen file cannot have
    open questions:

    * **"Nearest the midpoint" is measured in characters**, not words -- one pass over the
      string rather than a word index, and the two agree closely enough that the difference
      never decides a split.
    * **Ties go to the earlier boundary.** Two candidates equidistant from the midpoint is
      rare and entirely possible; without a stated rule the winner would depend on
      iteration order, which is the kind of thing that changes under a refactor and takes
      every `step_id` with it.

    A step over the cap with **no** interior sentence boundary is left alone. Splitting
    mid-sentence would produce two fragments neither of which can be labelled, which is a
    worse outcome than one long step -- and the classifier's own failure on long steps is
    what S3 measures.
    """
    start, end = span
    if word_count(text[start:end]) <= SPLIT_OVER_WORDS:
        return [span]
    candidates = _sentence_starts(text, start, end, protected)
    if not candidates:
        return [span]
    midpoint = (start + end) / 2
    best = min(candidates, key=lambda p: (abs(p - midpoint), p))
    left = _tighten(text, start, best)
    right = _tighten(text, best, end)
    if left[1] <= left[0] or right[1] <= right[0]:
        return [span]
    return [*_split_long(text, left, protected), *_split_long(text, right, protected)]


def segment_text(text: str) -> list[tuple[int, int]]:
    """C4.2 §2 over one reasoning text. Returns ranges into the **normalised** text.

    Empty thinking yields an empty list -- C4.2's named edge case for the Direct arm. Zero
    thought steps is a valid trace, not an error.
    """
    protected = _protected(text)
    spans: list[tuple[int, int]] = []
    for p_start, p_end in _paragraphs(text, protected):
        spans.extend(_split_paragraph(text, p_start, p_end, protected))
    spans = _merge_short(text, spans)
    out: list[tuple[int, int]] = []
    for span in spans:
        out.extend(_split_long(text, span, protected))
    return out


# ---------------------------------------------------------------- assembly
def _step(
    strategy: str,
    span_id: str,
    ordinal: int,
    kind: str,
    text: str,
    char_range: tuple[int, int] | None,
) -> Step:
    return Step(
        step_id=f"{strategy}:{span_id}:{ordinal}",
        ordinal=ordinal,
        kind=kind,  # type: ignore[arg-type]
        text=text,
        span_id=span_id,
        char_range=char_range,
        # Deliberately None. We have no per-step MODEL token count -- the provider reports
        # one number for the whole completion -- and putting this module's word count in a
        # field named `tokens_out` would be read as BPE tokens by everything downstream.
        tokens_out=None,
    )


def segment(parsed: ParsedTrace) -> NormalizedTrace:
    """A parsed span tree becomes a segmented trace. The one entry point.

    Two paths, per C4.2: the ReAct arm is **structural only** and the other two arms split
    text. The ReAct path is not a simplification -- agent traces arrive already segmented
    (B5's insight), and running the text splitter over them would invent thought boundaries
    the agent's own structure already states.
    """
    if parsed.strategy == "react":
        steps, source = _segment_react(parsed)
    else:
        steps, source = _segment_linear(parsed)

    # Two different things, and conflating them would be a contract bug. The answer STEP
    # carries what the model actually wrote -- that is what a reviewer reads and what the
    # UI highlights. `NormalizedTrace.final_answer` carries the extracted last line, which
    # is what C3.3's report compares against `known_answer` ("final_answer": "42").
    answer_text = parsed.final_answer_source.strip()
    answer = final_answer_line(answer_text)
    if answer_text:
        # C4.2 2f: a single `answer` step, never a `thought`. Its `char_range` indexes the
        # answer text, not `source_text` -- see `Step.char_range`.
        steps.append(
            _step(
                parsed.strategy,
                parsed.calls[-1].span_id if parsed.calls else "answer",
                len(steps),
                "answer",
                answer_text,
                (0, len(answer_text)),
            )
        )

    return NormalizedTrace(
        strategy=parsed.strategy,
        item_id=parsed.item_id,
        steps=steps,
        final_answer=answer,
        usage=parsed.usage,
        timings=parsed.timings,
        trace_quality=parsed.trace_quality,
        model_pin=parsed.model_pin,
        source_text=source,
    )


def _segment_linear(parsed: ParsedTrace) -> tuple[list[Step], str]:
    """Arms 1 and 2: one LLM span, its reasoning text split per C4.2 §2."""
    call = parsed.calls[0] if parsed.calls else None
    if call is None:
        return [], ""
    source = normalise_text(call.reasoning)
    steps = [
        _step(parsed.strategy, call.span_id, i, "thought", source[s:e], (s, e))
        for i, (s, e) in enumerate(segment_text(source))
    ]
    return steps, source


def _segment_react(parsed: ParsedTrace) -> tuple[list[Step], str]:
    """Arm 3: structural only. One `thought` per turn's reasoning, one `tool_call` plus one
    `observation` per TOOL span, interleaved in execution order.

    Execution order comes from `rlens.seq`, assigned by the emitter, because a serialised
    tree has no timestamps. The last turn's reasoning still becomes a `thought` step -- the
    model thought and *then* answered, and the answer step is appended by `segment`.

    `source_text` is the turns' reasoning joined by blank lines, and each thought step's
    `char_range` indexes into that join. Per-turn offsets would each be relative to a
    different string, and a UI cannot highlight against a string it was not given.
    """
    ordered: list[tuple[int, str, LlmCall | ToolUse]] = [
        *((c.seq, "llm", c) for c in parsed.calls),
        *((t.seq, "tool", t) for t in parsed.tools),
    ]
    # Stable on `seq`, then on kind, so a tree that somehow reuses a seq still segments
    # identically every time rather than depending on list order.
    ordered.sort(key=lambda row: (row[0], row[1]))

    steps: list[Step] = []
    chunks: list[str] = []
    cursor = 0
    for _, _kind, obj in ordered:
        if isinstance(obj, LlmCall):
            thought = normalise_text(obj.reasoning)
            if not thought:
                continue
            start = cursor
            chunks.append(thought)
            cursor += len(thought) + 2  # the "\n\n" the join inserts
            steps.append(
                _step(
                    parsed.strategy,
                    obj.span_id,
                    len(steps),
                    "thought",
                    thought,
                    (start, start + len(thought)),
                )
            )
        else:
            call_text = f"{obj.name}({obj.arguments})"
            steps.append(
                _step(
                    parsed.strategy,
                    obj.span_id,
                    len(steps),
                    "tool_call",
                    call_text,
                    (0, len(call_text)),
                )
            )
            observation = obj.observation.strip()
            steps.append(
                _step(
                    parsed.strategy,
                    obj.span_id,
                    len(steps),
                    "observation",
                    observation,
                    (0, len(observation)),
                )
            )
    return steps, "\n\n".join(chunks)
