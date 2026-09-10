"""Strategy Runner. Given an item, execute the arms and emit conforming span trees.

**Nothing else. It does no analysis** (I1, C4.1) -- the runner produces spans and the
analyzer consumes them, and the two never share a data structure that is not a span.
That separation is what lets the analyzer be tested entirely on committed trees, ours
and third parties' alike.

Owner: M1-6. Arm 3 (LangGraph ReAct) is M1-7.
"""

from __future__ import annotations

from rlens.runner.arms import ARMS, ArmSpec, Strategy
from rlens.runner.run import ArmResult, run_arm, run_arms

__all__ = ["ARMS", "ArmResult", "ArmSpec", "Strategy", "run_arm", "run_arms"]
