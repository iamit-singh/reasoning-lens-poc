"""Batched behavior classification + triage judge -- one call per strategy (C4.3).

Owner: M1-9. This module is a skeleton placed by M1-0 so the C2.2 boundary contract
and the CI job set exist from Week 1; its implementation lands with M1-9.
"""

from __future__ import annotations

import anthropic  # DELIBERATE C2.2 VIOLATION -- provider SDK outside llm.py. To be reverted.
