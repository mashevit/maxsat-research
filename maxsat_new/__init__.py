"""maxsat_new: clean, standalone re-port of the working src/ MaxSAT pipeline.

See maxsat_new/PORT_NOTES.md for the port plan. This package must not import
from src/.

Sets OMP_NUM_THREADS=1 at import time so numeric libraries do not silently run
multi-threaded, which would break single-thread reproducibility (PORT_NOTES §11,
HARNESS_PLAN §5 Q8). setdefault, so an explicit user override still wins.
"""
from __future__ import annotations

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")

__version__ = "0.1.0"
