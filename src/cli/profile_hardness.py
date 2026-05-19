"""
Profile instance hardness against an RC2 anytime baseline and assign tiers.

Reads MaxSAT instances (.wcnf or .cnf), runs RC2 with a wall-clock cap,
records first-feasible time, last-improvement time, and the cost at
checkpoints, then assigns a tier:

    T1 — RC2 dominant.       Feasible within 60-300s AND ratio <= 1.1.
    T2a — research zone.     1.1 < ratio <= 2.0.
    T2b — prime training.    ratio > 2.0.
    T3 — no signal.          No feasible solution within the cap.

The ratio is `final_cost / best_known_cost`. Without a `--bestknown` CSV,
records are written with tier="T2_prov" or "T3" only (feasibility known,
ratio sub-split deferred until best-known is available).

JSONL output is compatible with HARNESS_PLAN.md §2.3 where fields overlap;
profile-specific signals live under a `profile` key.

Usage:
    python -m src.cli.profile_hardness \\
        --instances data/toy/*.wcnf \\
        --cap 600 \\
        --out results/profile/toy_profile.jsonl

    python -m src.cli.profile_hardness \\
        --instances 'data/raw/mse_2024/**/*.wcnf*' \\
        --cap 600 \\
        --bestknown data/bestknown.csv \\
        --out results/profile/mse_2024_profile.jsonl
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import signal
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from pysat.examples.rc2 import RC2
from pysat.formula import WCNF


# Tier-boundary constants. See docs/STRATIFICATION_PLAN.md for rationale.
T1_RATIO_MAX = 1.1
T2A_RATIO_MAX = 2.0
T1_TIME_MAX = 300.0     # First-feasible by 5 min counts as "fast"
DEFAULT_CAP = 600.0
DEFAULT_CHECKPOINTS = (60.0, 300.0, 600.0)


class _Timeout(Exception):
    pass


@contextmanager
def wall_timeout(seconds: float):
    """SIGALRM-based timeout. Posix only; fine for SLURM and local Linux."""
    def _handler(signum, frame):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def profile_instance(path: str, cap: float,
                     checkpoints: tuple[float, ...]) -> dict:
    """Run RC2 anytime on one instance under a wall-clock cap.

    Returns a dict of raw profile signals. Tier is assigned later by
    assign_tier() once best-known cost is looked up.
    """
    size_mb = os.path.getsize(path) / 1e6
    rec: dict = {
        "instance": path,
        "size_mb": round(size_mb, 4),
        "profile": {
            "cap_s": cap,
            "first_feasible_s": None,
            "last_improve_s": None,
            "final_cost": None,
            "checkpoints": {str(int(c)): None for c in checkpoints},
            "completed": False,
            "wall_s": None,
            "error": None,
        },
    }

    try:
        wcnf = WCNF(from_file=path)
    except Exception as e:
        rec["profile"]["error"] = f"parse_failed: {e}"
        return rec

    t0 = time.monotonic()
    pending_cp = list(checkpoints)
    best: Optional[int] = None

    def _stamp_checkpoints(elapsed: float, current_best: Optional[int]):
        while pending_cp and elapsed >= pending_cp[0]:
            cp = pending_cp.pop(0)
            rec["profile"]["checkpoints"][str(int(cp))] = current_best

    try:
        with wall_timeout(cap + 5.0):           # hard kill 5s past cap
            solver = RC2(wcnf)
            try:
                # RC2.enumerate streams improving models in modern pysat.
                # Older builds expose .compute() returning one model. Try
                # enumerate first; fall back if absent.
                if hasattr(solver, "enumerate"):
                    completed = True
                    for _model in solver.enumerate():
                        elapsed = time.monotonic() - t0
                        cost = solver.cost
                        if rec["profile"]["first_feasible_s"] is None:
                            rec["profile"]["first_feasible_s"] = round(elapsed, 3)
                        if best is None or cost < best:
                            best = cost
                            rec["profile"]["last_improve_s"] = round(elapsed, 3)
                        _stamp_checkpoints(elapsed, best)
                        if elapsed >= cap:
                            completed = False
                            break
                    rec["profile"]["completed"] = completed
                else:
                    model = solver.compute()
                    elapsed = time.monotonic() - t0
                    if model is not None:
                        best = solver.cost
                        rec["profile"]["first_feasible_s"] = round(elapsed, 3)
                        rec["profile"]["last_improve_s"] = round(elapsed, 3)
                    rec["profile"]["completed"] = True
                    _stamp_checkpoints(elapsed, best)
            finally:
                solver.delete()
    except _Timeout:
        rec["profile"]["error"] = "hard_timeout"
    except Exception as e:
        rec["profile"]["error"] = f"solver_failed: {type(e).__name__}: {e}"

    elapsed = time.monotonic() - t0
    _stamp_checkpoints(elapsed, best)
    rec["profile"]["final_cost"] = best
    rec["profile"]["wall_s"] = round(elapsed, 3)
    return rec


def assign_tier(rec: dict, best_known: Optional[int]) -> dict:
    """Pure function: set `tier`, `ratio`, `tier_reason` on rec, return it."""
    p = rec["profile"]
    final_cost = p["final_cost"]
    first_feasible = p["first_feasible_s"]

    if final_cost is None:
        rec["tier"] = "T3"
        rec["ratio"] = None
        rec["tier_reason"] = "no_feasible_within_cap"
        return rec

    ratio: Optional[float] = None
    if best_known is not None:
        if best_known > 0:
            ratio = final_cost / best_known
        elif best_known == 0 and final_cost == 0:
            ratio = 1.0
        # best_known == 0 with final_cost > 0: ratio undefined (skip)
    rec["ratio"] = round(ratio, 4) if ratio is not None else None

    if ratio is None:
        rec["tier"] = "T2_prov"
        rec["tier_reason"] = "feasible_but_ratio_unknown"
        return rec

    if (first_feasible is not None
            and first_feasible <= T1_TIME_MAX
            and ratio <= T1_RATIO_MAX):
        rec["tier"] = "T1"
        rec["tier_reason"] = f"ratio<={T1_RATIO_MAX} and fast"
    elif ratio <= T2A_RATIO_MAX:
        rec["tier"] = "T2a"
        rec["tier_reason"] = f"{T1_RATIO_MAX}<ratio<={T2A_RATIO_MAX}"
    else:
        rec["tier"] = "T2b"
        rec["tier_reason"] = f"ratio>{T2A_RATIO_MAX}"
    return rec


def load_bestknown(path: str) -> dict[str, int]:
    """Read a CSV with columns `instance, best_cost`. Matched by basename."""
    out: dict[str, int] = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[os.path.basename(row["instance"])] = int(row["best_cost"])
    return out


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Profile MaxSAT instances against RC2 and assign tiers."
    )
    ap.add_argument("--instances", nargs="+", required=True,
                    help="Glob(s) for instance files (.wcnf, .cnf).")
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="Per-instance wall-clock cap, seconds.")
    ap.add_argument("--checkpoints", type=float, nargs="+",
                    default=list(DEFAULT_CHECKPOINTS),
                    help="Wall-clock seconds at which to log best-so-far.")
    ap.add_argument("--bestknown", default=None,
                    help="CSV with columns `instance,best_cost`. Optional.")
    ap.add_argument("--out", required=True,
                    help="Output JSONL path. Appended if it exists.")
    args = ap.parse_args(argv)

    paths: list[str] = []
    for pattern in args.instances:
        matched = sorted(glob.glob(pattern, recursive=True))
        if not matched:
            print(f"[warn] no files matched: {pattern}")
        paths.extend(matched)

    best_known: dict[str, int] = {}
    if args.bestknown:
        best_known = load_bestknown(args.bestknown)
        print(f"[info] loaded {len(best_known)} best-known entries")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "a") as f:
        for path in paths:
            print(f"[*] {path}")
            rec = profile_instance(path, args.cap, tuple(args.checkpoints))
            bk = best_known.get(os.path.basename(path))
            assign_tier(rec, bk)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            p = rec["profile"]
            print(f"    first_feasible={p['first_feasible_s']} "
                  f"final_cost={p['final_cost']} "
                  f"wall={p['wall_s']} "
                  f"tier={rec.get('tier')} ratio={rec.get('ratio')}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
