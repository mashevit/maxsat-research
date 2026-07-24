"""Step 2 test: walksat_polish is deterministic under a flip-count budget.

Fails before maxsat_new/walksat.py exists (ImportError); passes after.

Per PORT_NOTES §11 Q1, "one seed -> bit-identical run" holds only under a
deterministic bound. `walksat_polish`'s signature makes `time_limit_s` unavoidable
(it defaults to 0.05), so we pass a large `time_limit_s` (1000.0) that never binds
and a small `max_flips` (200) that always binds — the flip cap is the real budget.
Confirmed empirically: total_flips == max_flips, elapsed ~1ms.
"""
from __future__ import annotations

import os

from maxsat_new.cnf import WCNF
from maxsat_new.walksat import walksat_polish

MINI = os.path.join(os.path.dirname(__file__), "data", "mini.wcnf")

# Fixed, feasible start assignment (x1=1,x2=0,x3=0,x4=1,x5=1 -> hard_v=0), 0-based.
START_ASSIGN = [True, False, False, True, True]
SEED = 1
MAX_FLIPS = 200
TIME_LIMIT_S = 1000.0  # large enough that the flip cap always binds first


def test_walksat_polish_deterministic() -> None:
    r1 = walksat_polish(
        WCNF.parse_dimacs(MINI),
        START_ASSIGN,
        rng_seed=SEED,
        max_flips=MAX_FLIPS,
        time_limit_s=TIME_LIMIT_S,
    )
    r2 = walksat_polish(
        WCNF.parse_dimacs(MINI),
        START_ASSIGN,
        rng_seed=SEED,
        max_flips=MAX_FLIPS,
        time_limit_s=TIME_LIMIT_S,
    )

    # The flip cap (not the wall-clock cap) must be what stopped the run, or the
    # result would not be deterministic.
    assert r1["total_flips"] == MAX_FLIPS

    # Two runs from identical start + seed + budget must match bit-for-bit.
    assert r1["final_assign"] == r2["final_assign"]
    assert r1["flips"] == r2["flips"]
    assert r1["total_flips"] == r2["total_flips"]
