"""Post-deploy smoke test (C7.3, B7.3 Step 7).

Owner: M3-4. Checks, against the live URL: 3 bank items served from cache (one per
tag), the faithfulness panel, the calibration endpoint, the report download, and a
forced breaker trip. There is no manual gate and no staging tier (B0 Condition #2),
so this script is the whole of deploy acceptance -- keep it executable and honest.
"""

from __future__ import annotations

import sys


def main() -> int:
    sys.stderr.write("smoke: not implemented (owner M3-4).\n")
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
