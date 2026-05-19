"""
Profile MaxSAT instances against an RC2 (exact) baseline and assign tiers.

RC2 is an exact MaxSAT solver: it either proves an optimum within the
wall-clock cap or it doesn't. The honest hardness signal is therefore
*time-to-solve*, not a ratio. Tiers are time-based:

    T1  — RC2 solves to optimum within 60 s. Regression / smoke tier.
    T2a — solves within 60-300 s. Research zone.
    T2b — solves within 300-600 s. High research interest.
    T3  — does not solve within the cap. Prime LLM-guided target.

If a `--bestknown` CSV is supplied, the ratio (final_cost / best_known)
is recorded as a *secondary annotation* for sanity-checking. For RC2 it
should be ~1.0 when it solves. A later pass with an anytime solver
(NuWLS-c, your memetic_ea, etc.) will compute the ratio that actually
matters for an LLM-guided approach; the schema here is forward-
compatible with that.

JSONL fields overlap deliberately with HARNESS_PLAN.md §2.3.

Usage:
    python -m src.cli.profile_hardness \\
        --instances data/toy/*.wcnf \\
        --cap 10 \\
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


# Tier-boundary constants (seconds). See docs/STRATIFICATION_PLAN.md.
T1_MAX_S = 60.0
T2A_MAX_S = 300.0
T2B_MAX_S = 600.0
DEFAULT_CAP = 600.0


class _Timeout(Exception):
    pass


@contextmanager
def wall_timeout(seconds: float):
    """SIGALRM-based hard timeout. POSIX only."""
    def _handler(signum, frame):
        raise _Timeout()
    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def profile_instance(path: str, cap: float) -> dict:
    """Run RC2.compute() on one instance under a wall-clock cap.

    Returns a dict with the profile signals; tier is assigned later by
    assign_tier(). Never raises — all errors are captured into
    rec['profile']['error'].
    """
    rec: dict = {
        "instance": path,
        "size_mb": round(os.path.getsize(path) / 1e6, 4),
        "profile": {
            "cap_s": cap,
            "solver": "rc2",
            "solve_s": None,
            "final_cost": None,
            "completed": False,
            "error": None,
        },
    }

    try:
        wcnf = WCNF(from_file=path)
    except Exception as e:
        rec["profile"]["error"] = f"parse_failed: {type(e).__name__}: {e}"
        return rec

    t0 = time.monotonic()
    try:
        with wall_timeout(cap):
            solver = RC2(wcnf)
            try:
                model = solver.compute()
                elapsed = time.monotonic() - t0
                if model is not None:
                    rec["profile"]["solve_s"] = round(elapsed, 3)
                    rec["profile"]["final_cost"] = int(solver.cost)
                    rec["profile"]["completed"] = True
                else:
                    rec["profile"]["error"] = "rc2_returned_none"
                    rec["profile"]["solve_s"] = round(elapsed, 3)
            finally:
                solver.delete()
    except _Timeout:
        rec["profile"]["error"] = "timeout"
    except Exception as e:
        rec["profile"]["error"] = f"solver_failed: {type(e).__name__}: {e}"
        rec["profile"]["solve_s"] = round(time.monotonic() - t0, 3)

    return rec


def assign_tier(rec: dict, best_known: Optional[int]) -> dict:
    """Pure function: set `tier`, `ratio`, `tier_reason` on rec, return it."""
    p = rec["profile"]
    final_cost = p["final_cost"]
    solve_s = p["solve_s"]

    # Optional ratio annotation (always computed if best_known is given).
    ratio: Optional[float] = None
    if final_cost is not None and best_known is not None:
        if best_known > 0:
            ratio = final_cost / best_known
        elif best_known == 0 and final_cost == 0:
            ratio = 1.0
    rec["ratio"] = round(ratio, 4) if ratio is not None else None

    if not p["completed"]:
        rec["tier"] = "T3"
        rec["tier_reason"] = p["error"] or "did_not_complete"
        return rec

    if solve_s <= T1_MAX_S:
        rec["tier"] = "T1"
        rec["tier_reason"] = f"solve_s<={T1_MAX_S}"
    elif solve_s <= T2A_MAX_S:
        rec["tier"] = "T2a"
        rec["tier_reason"] = f"{T1_MAX_S}<solve_s<={T2A_MAX_S}"
    elif solve_s <= T2B_MAX_S:
        rec["tier"] = "T2b"
        rec["tier_reason"] = f"{T2A_MAX_S}<solve_s<={T2B_MAX_S}"
    else:
        # Shouldn't happen — cap should have triggered timeout first.
        rec["tier"] = "T3"
        rec["tier_reason"] = f"solve_s>{T2B_MAX_S} (cap misconfigured?)"
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
        description="Profile MaxSAT instances with RC2 and assign tiers."
    )
    ap.add_argument("--instances", nargs="+", required=True,
                    help="Glob(s) for instance files (.wcnf, .cnf).")
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="Per-instance wall-clock cap, seconds.")
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
            rec = profile_instance(path, args.cap)
            bk = best_known.get(os.path.basename(path))
            assign_tier(rec, bk)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            p = rec["profile"]
            print(f"    solve_s={p['solve_s']} final_cost={p['final_cost']}"
                  f" tier={rec.get('tier')} ratio={rec.get('ratio')}"
                  f" err={p['error']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
