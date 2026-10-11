"""
Profile MaxSAT instances against an RC2 (exact) baseline and assign tiers.

Tiers are time-based:

    T1  — RC2 solves to optimum within 60 s. Regression / smoke tier.
    T2a — solves within 60-300 s. Research zone.
    T2b — solves within 300-600 s. High research interest.
    T3  — does not solve within the cap. Prime LLM-guided target.

For ratio interpretation we record two fields:

  - ``ratio = final_cost / best_known`` is the *validation* ratio. Only
    populated when RC2 actually completed. For an exact solver like RC2
    it should be ≈ 1.0; deviations indicate an out-of-date best-known
    or a bug.

  - ``lb_ratio = cost_lower_bound / best_known`` is the *progress*
    ratio. Populated whenever a running lower bound was captured (which
    is true for status="timeout" with graceful SIGALRM, AND for
    status="subprocess_killed" when the progress-file watchdog managed
    at least one write before SIGKILL). For T3 instances this is the
    primary stratifier: ``lb_ratio ∈ [0, 1]`` tells you how tight a
    lower bound RC2 established. Close to 1.0 means RC2 was near-done;
    close to 0 means RC2 was stuck.

Timeout enforcement
-------------------
By default this module runs RC2 in a subprocess with three layers of
timeout protection:

  1. The child's own SIGALRM at ``cap`` — graceful, records the running
     lower bound in the JSON output. Sets status="timeout".
  2. The child's background progress-file thread — every ~2 s while
     solving, RC2's running lower bound is written to a temp file.
     Survives SIGKILL.
  3. ``subprocess.run(timeout=cap+grace)`` — kernel-level SIGKILL if
     SIGALRM was swallowed inside the C SAT solver. Sets
     status="subprocess_killed", but ``cost_lower_bound`` is still
     recovered from the progress file (layer 2).

The legacy in-process path is retained behind ``--in-process`` for fast
smoke tests where you trust instances won't get stuck.

Usage:
    python -m src.cli.profile_hardness \\
        --instances 'data/raw/mse_2024/mse23-uw-small/*.wcnf' \\
        --cap 600 \\
        --bestknown data/raw/mse_2024/bestknown_mse23.csv \\
        --out results/profile/mse23_full.jsonl
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional


T1_MAX_S = 60.0
T2A_MAX_S = 300.0
T2B_MAX_S = 600.0
DEFAULT_CAP = 600.0
DEFAULT_GRACE_S = 15.0


def _empty_rec(path: str, cap: float) -> dict:
    return {
        "instance": path,
        "size_mb": round(os.path.getsize(path) / 1e6, 4),
        "profile": {
            "cap_s": cap,
            "solver": "rc2",
            "status": None,
            "solve_s": None,
            "final_cost": None,
            "cost_lower_bound": None,
            "completed": False,
            "error": None,
        },
    }


def _populate_from_anytime_dict(rec: dict, data: dict) -> None:
    p = rec["profile"]
    p["status"] = data.get("status")
    p["solve_s"] = round(float(data.get("elapsed_s") or 0.0), 3)
    p["final_cost"] = data.get("cost")
    p["cost_lower_bound"] = data.get("cost_lower_bound")
    p["completed"] = (p["status"] == "optimal")

    if p["status"] == "timeout":
        p["error"] = "timeout"
    elif p["status"] == "unsat":
        p["error"] = "unsat"
    elif p["status"] == "error":
        p["error"] = data.get("error") or "error"


def _read_progress_lb(progress_file: str) -> Optional[int]:
    """Read the last lower bound written by the subprocess's progress thread."""
    try:
        with open(progress_file, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return None


def profile_instance_subprocess(
    path: str, cap: float, grace: float = DEFAULT_GRACE_S
) -> dict:
    """Run RC2 in a subprocess with hard wall-clock enforcement."""
    rec = _empty_rec(path, cap)
    p = rec["profile"]

    fd, progress_file = tempfile.mkstemp(prefix="rc2_progress_", suffix=".txt")
    os.close(fd)

    wall_start = time.monotonic()

    try:
        try:
            proc = subprocess.run(
                [
                    sys.executable, "-m", "src.cli.solve_rc2_anytime",
                    "--path", path,
                    "--timeout-s", str(cap),
                    "--progress-file", progress_file,
                    "--json",
                ],
                capture_output=True,
                text=True,
                timeout=cap + grace,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - wall_start
            recovered_lb = _read_progress_lb(progress_file)
            p["status"] = "subprocess_killed"
            p["solve_s"] = round(elapsed, 3)
            p["cost_lower_bound"] = recovered_lb
            p["error"] = (
                f"subprocess_killed_at_cap+{grace}s"
                + ("" if recovered_lb is None else "; recovered_lb_from_progress_file")
            )
            return rec
        except Exception as e:  # pragma: no cover
            elapsed = time.monotonic() - wall_start
            p["status"] = "error"
            p["solve_s"] = round(elapsed, 3)
            p["error"] = f"subprocess_launch_failed: {type(e).__name__}: {e}"
            return rec

        if not proc.stdout.strip():
            p["status"] = "error"
            p["solve_s"] = round(time.monotonic() - wall_start, 3)
            p["error"] = (
                f"empty_subprocess_output (rc={proc.returncode}); "
                f"stderr={proc.stderr[:200]!r}"
            )
            return rec

        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except json.JSONDecodeError as e:
            p["status"] = "error"
            p["solve_s"] = round(time.monotonic() - wall_start, 3)
            p["error"] = (
                f"bad_subprocess_output: {e}; "
                f"stdout={proc.stdout[:200]!r}; stderr={proc.stderr[:200]!r}"
            )
            return rec

        _populate_from_anytime_dict(rec, data)
        return rec

    finally:
        try:
            os.unlink(progress_file)
        except OSError:
            pass


def profile_instance_inprocess(path: str, cap: float) -> dict:
    """In-process variant; timeouts are best-effort."""
    from dataclasses import asdict
    from src.cli.solve_rc2_anytime import solve_rc2_with_timeout

    rec = _empty_rec(path, cap)
    res = solve_rc2_with_timeout(path, timeout_s=cap)
    _populate_from_anytime_dict(rec, asdict(res))
    return rec


def assign_tier(rec: dict, best_known: Optional[int]) -> dict:
    """Pure function: set `tier`, `ratio`, `lb_ratio`, `tier_reason` on rec.

    Two ratios are recorded:
      - ``ratio = final_cost / best_known``     — validation; ≈ 1.0 when RC2
        completes. None for T3 (no final_cost).
      - ``lb_ratio = cost_lower_bound / best_known`` — progress; ∈ [0, 1]
        whenever a running lower bound exists, even on timeout/SIGKILL.
        This is the primary stratifier inside T3.
    """
    p = rec["profile"]
    final_cost = p["final_cost"]
    lb = p["cost_lower_bound"]
    solve_s = p["solve_s"]

    # Validation ratio (only when RC2 actually finished).
    ratio: Optional[float] = None
    if final_cost is not None and best_known is not None:
        if best_known > 0:
            ratio = final_cost / best_known
        elif best_known == 0 and final_cost == 0:
            ratio = 1.0
    rec["ratio"] = round(ratio, 4) if ratio is not None else None

    # Progress ratio (whenever lb was captured). Skip when best_known is -1
    # (the MSE convention for "unknown") or non-positive.
    lb_ratio: Optional[float] = None
    if lb is not None and best_known is not None and best_known > 0:
        lb_ratio = lb / best_known
    rec["lb_ratio"] = round(lb_ratio, 4) if lb_ratio is not None else None

    # Tier (time-based).
    if not p["completed"]:
        rec["tier"] = "T3"
        rec["tier_reason"] = p["error"] or p["status"] or "did_not_complete"
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
                    help="Glob(s) or paths for instance files (.wcnf, .cnf).")
    ap.add_argument("--cap", type=float, default=DEFAULT_CAP,
                    help="Per-instance wall-clock cap, seconds.")
    ap.add_argument("--grace", type=float, default=DEFAULT_GRACE_S,
                    help="Subprocess grace beyond cap before SIGKILL.")
    ap.add_argument("--in-process", action="store_true",
                    help="Use the in-process path (timeouts best-effort, "
                         "no progress-file lb recovery).")
    ap.add_argument("--bestknown", default=None,
                    help="CSV with columns `instance,best_cost`. Optional.")
    ap.add_argument("--out", required=True,
                    help="Output JSONL path. Appended if it exists.")
    args = ap.parse_args(argv)

    paths: list[str] = []
    for pattern in args.instances:
        matched = sorted(glob.glob(pattern, recursive=True))
        if not matched:
            if os.path.exists(pattern):
                matched = [pattern]
            else:
                print(f"[warn] no files matched: {pattern}")
        paths.extend(matched)

    best_known: dict[str, int] = {}
    if args.bestknown:
        best_known = load_bestknown(args.bestknown)
        print(f"[info] loaded {len(best_known)} best-known entries")

    if args.in_process:
        runner = profile_instance_inprocess
        print(f"[info] runner=in-process cap={args.cap}s")
    else:
        runner = lambda p, c: profile_instance_subprocess(p, c, grace=args.grace)
        print(f"[info] runner=subprocess cap={args.cap}s grace={args.grace}s "
              "(lb recovered from progress-file on SIGKILL)")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "a") as f:
        for path in paths:
            print(f"[*] {path}")
            rec = runner(path, args.cap)
            bk = best_known.get(os.path.basename(path))
            assign_tier(rec, bk)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            p = rec["profile"]
            print(
                f"    status={p['status']} solve_s={p['solve_s']}"
                f" final_cost={p['final_cost']} lb={p['cost_lower_bound']}"
                f" tier={rec.get('tier')} ratio={rec.get('ratio')}"
                f" lb_ratio={rec.get('lb_ratio')}"
                f" err={p['error']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
