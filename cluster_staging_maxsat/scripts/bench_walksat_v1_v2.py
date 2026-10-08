#!/usr/bin/env python3
"""Polish throughput, v1 vs v2 (docs/current/MEMETIC_IMPL_V2.md §3).

For each instance: one random start assignment (seed 1), then one polish call
with v1 (src/sat/walksat.py) and one with v2 (src/sat/walksat_v2.py), both with
the established arm's per-call limits (12 500 flips, 3.5 s), plus a v2 call with
the flip cap lifted to show its uncapped rate. Prints flips, seconds, flips/s
and the unsatisfied soft weight after the call.

    python3 scripts/bench_walksat_v1_v2.py data/generated/calib_2sat_sc_smoke/*.wcnf

Workstation only (it is compute, and the cluster forbids Python on the login
node). Run from the staging tree root. Timings depend on the machine.
"""
from __future__ import annotations

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
from sat.cnf import WCNF  # noqa: E402
from sat.walksat import walksat_polish  # noqa: E402
from sat.walksat_v2 import walksat_polish_v2  # noqa: E402

FLIPS, LIMIT_S = 12_500, 3.5


def main(paths) -> int:
    if not paths:
        print(__doc__)
        return 2
    print(f"{'instance':44s} {'n':>6s} {'m':>6s} {'impl':5s} {'flips':>9s} {'s':>6s} {'flips/s':>9s} {'unsat':>6s}")
    for path in paths:
        cnf = WCNF.parse_dimacs(path)
        n, m = cnf.n_vars, len(cnf.clauses)
        total = sum(cl.weight for cl in cnf.clauses if not cl.is_hard)
        r = random.Random(1)
        s0 = [r.random() < 0.5 for _ in range(n)]
        walksat_polish_v2(cnf, list(s0), rng_seed=2, max_flips=1, time_limit_s=1)  # build v2's per-instance cache
        runs = (("v1", walksat_polish, FLIPS), ("v2", walksat_polish_v2, FLIPS),
                ("v2*", walksat_polish_v2, 10 ** 9))
        for name, fn, flips in runs:
            t0 = time.time()
            res = fn(cnf, list(s0), rng_seed=3, max_flips=flips, time_limit_s=LIMIT_S)
            _ = time.time() - t0
            print(f"{os.path.basename(path)[:44]:44s} {n:6d} {m:6d} {name:5s} {res['total_flips']:9d} "
                  f"{res['elapsed_sec']:6.2f} {res['flips_per_sec']:9.0f} {total - res['best_soft_weight']:6.0f}")
    print("v2* = v2 with the flip cap lifted (3.5 s only)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
