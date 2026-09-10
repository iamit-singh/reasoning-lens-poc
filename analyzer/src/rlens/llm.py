"""Provider abstraction and MOCK_LLM cassette replay.

The ONLY place in the analyzer where provider SDK symbols may appear (C2.2), together
with ``ingest/otel.py``.

Owner: M1-6. This module is a skeleton placed by M1-0 so the C2.2 boundary contract
and the CI job set exist from Week 1; its implementation lands with M1-6.
"""

from __future__ import annotations
