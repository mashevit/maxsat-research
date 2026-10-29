#!/usr/bin/env python3
"""Complementarity of the memetic and EvalMaxSAT on MSE 2026 (not pre-registered).

Reads the instances.csv written by mse26_rho_errors.py (both treatments of the
errored runs) and the published 2026 runs, and prints the numbers of
docs/current2/MSE26_RHO_PRELIM_RESULTS.md section 10:
  coverage (EvalMaxSAT, memetic, union), the two one-sided cells with exact
  Clopper-Pearson 95 % intervals, McNemar exact test, seed robustness of the
  memetic-only cell, memetic reach by EvalMaxSAT band with a Cochran-Armitage
  trend test, runtime on the instances both solve, PAR2 of EvalMaxSAT vs the
  per-instance best of the two, and the published solvers on the memetic-only cell.

    python3 scripts/mse26_complementarity.py     # after both mse26_rho_errors.py runs
"""
import csv
import math
import os
import sys
from collections import Counter

import numpy as np
from scipy.stats import beta, binomtest, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import mse26_rho as rho  # noqa: E402

BANDS = [(0.0, 1.0), (1.0, 30.0), (30.0, 300.0), (300.0, 3600.0)]


def clopper_pearson(k, n, a=0.05):
    return (beta.ppf(a / 2, k, n - k + 1) if k else 0.0, beta.ppf(1 - a / 2, k + 1, n - k) if k < n else 1.0)


def cochran_armitage(k, n):
    """Two-sided trend test over ordered groups (scores 0, 1, ...): z, p."""
    k, n = np.asarray(k), np.asarray(n)
    t = np.arange(len(k))
    N, p = n.sum(), k.sum() / n.sum()
    T = (t * (k - n * p)).sum()
    V = p * (1 - p) * ((n * t * t).sum() - (n * t).sum() ** 2 / N)
    z = T / math.sqrt(V)
    return z, 2 * norm.sf(abs(z))


def par2(v, limit=rho.X_LIMIT):
    return v if math.isfinite(v) else 2 * limit


def report(mode, pop, pub):
    with open(os.path.join(ROOT, "results", f"mse26_rho_{mode}", "instances.csv"), newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["primary"] == "True" and r["complete"] == "True"]
    for r in rows:
        r["x"], r["y"], r["s"] = float(r["x"]), float(r["y"]), int(r["successes"])
    N = len(rows)
    ems = [r for r in rows if math.isfinite(r["x"])]
    mem = [r for r in rows if math.isfinite(r["y"])]
    both = [r for r in ems if math.isfinite(r["y"])]
    ems_only = [r for r in ems if not math.isfinite(r["y"])]
    mem_only = [r for r in mem if not math.isfinite(r["x"])]
    print(f"\n===== --errors {mode}: N = {N}")
    print(f"EvalMaxSAT proved {len(ems)} ({len(ems) / N:.3f}); memetic reached {len(mem)} ({len(mem) / N:.3f}); "
          f"union {len(ems) + len(mem_only)} ({(len(ems) + len(mem_only)) / N:.3f})")
    print(f"both {len(both)}; only EvalMaxSAT {len(ems_only)}; only memetic {len(mem_only)}; "
          f"neither {N - len(ems) - len(mem_only)}")
    lo, hi = clopper_pearson(len(mem_only), N)
    print(f"only memetic / N: {len(mem_only) / N:.4f} [{lo:.4f}, {hi:.4f}]")
    lo, hi = clopper_pearson(len(mem_only), N - len(ems))
    print(f"only memetic / EvalMaxSAT timeouts ({N - len(ems)}): {len(mem_only) / (N - len(ems)):.3f} [{lo:.3f}, {hi:.3f}]")
    lo, hi = clopper_pearson(len(ems_only), len(ems))
    print(f"only EvalMaxSAT / EvalMaxSAT proved: {len(ems_only) / len(ems):.3f} [{lo:.3f}, {hi:.3f}]")
    print(f"McNemar exact: p = {binomtest(len(mem_only), len(mem_only) + len(ems_only), 0.5).pvalue:.1e}")
    print(f"only memetic: seeds succeeded {dict(sorted(Counter(r['s'] for r in mem_only).items()))}; "
          f"{len(set(r['family'] for r in mem_only))} families; "
          f"{dict(Counter(r['set'].rsplit('-', 1)[1] for r in mem_only))}")
    k = [sum(lo < r["x"] <= hi and math.isfinite(r["y"]) for r in ems) for lo, hi in BANDS]
    n = [sum(lo < r["x"] <= hi for r in ems) for lo, hi in BANDS]
    z, p = cochran_armitage(k, n)
    print("memetic reach by EvalMaxSAT band: " + "; ".join(
        f"({lo:g},{hi:g}] {a}/{b} ({a / b:.3f})" for (lo, hi), a, b in zip(BANDS, k, n))
        + f"; Cochran-Armitage z = {z:.2f}, p = {p:.1e}")
    print(f"both solved: memetic faster {sum(r['y'] < r['x'] for r in both)}, "
          f">= 10x faster {sum(10 * r['y'] < r['x'] for r in both)}; "
          f"EvalMaxSAT >= 10x faster {sum(10 * r['x'] < r['y'] for r in both)}")
    print(f"mean PAR2: EvalMaxSAT {sum(par2(r['x']) for r in rows) / N:.0f} s; "
          f"per-instance best of the two {sum(par2(min(r['x'], r['y'])) for r in rows) / N:.0f} s")
    counts, faster = [], 0
    for r in mem_only:
        opt = pop[r["hash"]]["optimal_cost"]
        t = [float(p["cpu.time"]) for p in pub[r["hash"]].values() if rho.solver_status(p, opt) == "proved"]
        counts.append(len(t))
        faster += r["y"] < min(t, default=math.inf)
    print(f"only memetic: published solvers that proved it {sorted(counts)}; "
          f"memetic ERT below the fastest published proof on {faster}/{len(mem_only)}")


def main() -> int:
    pop = rho.load_population(os.path.join(ROOT, "scripts", "mse26_population.tsv"))
    pub = rho.load_published(os.path.join(rho.REPO, "data", "raw", "mse_results", "mse26"))
    for mode in ("fail", "exclude"):
        report(mode, pop, pub)
    return 0


if __name__ == "__main__":
    sys.exit(main())
