#!/usr/bin/env python3
"""Readout of calib_2sat_sc (large-n, slightly supercritical random Max-2-SAT).

Plan and pre-registered rules: docs/current/CALIB_2SAT_SC.md §6. Written and
committed before any RC2 row of this batch exists. Every instance is reported;
no row is dropped.

Inputs (staging tree root):
    data/generated/calib_2sat_sc/manifest.jsonl      generator rows (45)
    results/profile_calib_2sat_sc_all.jsonl          aggregate_rc2_profile.py --batch calib_2sat_sc

Outputs:
    results/calib_2sat_sc/instances.csv   one row per instance
    results/calib_2sat_sc/cells.csv       one row per cell, with its outcome

Two quantities are kept apart throughout:
    c_star   the proven optimum: the minimum number of unsatisfied clauses
             (all weights are 1). Filled only when RC2 completed, and then
             final_cost == cost_lower_bound is required. Never an incumbent.
    solve_s  RC2 wall-clock seconds (time.time() in the child, from file load to
             return). A runtime, not a property of the optimum.
On a censored run, `lower_bound` holds RC2's last proven lower bound on c*
(c* >= lower_bound). No upper bound is recorded: RC2 reports no feasible
assignment on timeout, so none is claimed.

INSTANCE CLASS (the (30, 900] s window convention is candidate_cells.rc2_class,
imported, not re-implemented):
    eligible     completed, 30 < solve_s <= 900, c* >= 3
    low_cstar    completed, solve_s <= 900, c* <= 2   (any time)
    fast         completed, solve_s <= 30, c* >= 3
    censored     not completed within 900 s (timeout, SIGKILL, or a completion
                 after 900 s); lower bound reported
    failed       error, missing row, cost != bound, non-positive time, or a cap
                 below 900 s -- re-run before the readout, never counted

CELL OUTCOME (5 instances; any `failed` makes the cell `incomplete`). The three
counts below are over disjoint classes, so with 5 instances at most one can
reach 3:
    promising    >= 3 eligible
    too_easy     >= 3 in low_cstar + fast
    too_hard     >= 3 censored
    mixed        otherwise

FOLLOW-UP (proposals the readout prints; nothing is generated automatically):
    promising -> memetic assessment of its eligible instances (primary arm
                 configs/tier2/memetic_deeppolish_p40_ls3p5.yaml, 3 solver seeds,
                 900 s, effort in seconds) before any corpus decision; a corpus
                 cell is then regenerated with fresh seeds.
    too_easy  -> the same alpha at larger n first.
    too_hard  -> report lower bounds; propose intermediate points (lower alpha at
                 the same n, or an n between the nearest easier n and this one).
    mixed     -> state the split; reinforcement or intermediate points, chosen
                 at the readout with the reason written down.

    python3 scripts/calib_2sat_sc_readout.py
    python3 scripts/calib_2sat_sc_readout.py --check     # rebuild in memory, diff, exit 3 on drift

stdlib only; run from the staging tree root.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from candidate_cells import rc2_class  # noqa: E402  (window convention, shared)

BATCH = "calib_2sat_sc"
MIN_CSTAR = 3
NEED = 3  # of 5

INST_COLS = ["cell_id", "n", "alpha", "m", "n_eps3", "gen_seed", "instance",
             "instance_sha256", "rc2_status", "completed", "solve_s", "c_star",
             "lower_bound", "class", "pysat_version", "host"]
CELL_COLS = ["cell_id", "n", "alpha", "m", "n_eps3", "instances", "eligible",
             "low_cstar", "fast", "censored", "failed", "c_star_values",
             "solve_s_completed (min/med/max)", "censored_lower_bounds", "outcome",
             "follow_up"]

FOLLOW_UP = {
    "promising": "memetic assessment of the eligible instances (primary arm, seconds); "
                 "corpus cell only with fresh seeds",
    "too_easy": "same alpha, larger n",
    "too_hard": "report LBs; intermediate points (lower alpha at this n, or smaller n at this alpha)",
    "mixed": "state the split; reinforcement or intermediate points, reason written at readout",
    "incomplete": "re-run the failed tasks (RESUME=1) before classifying",
}


class Fatal(Exception):
    pass


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise Fatal(f"{path} not found")
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def instance_class(prof: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Class, proven c* (or None), lower bound (or None) and seconds."""
    if prof is None:
        return {"class": "failed", "c_star": None, "lower_bound": None, "solve_s": None}
    window, s = rc2_class(prof)
    proven = (prof.get("completed") is True and window != "failed")
    c_star = prof.get("final_cost") if proven else None
    lb = None if proven else prof.get("cost_lower_bound")
    if window == "failed":
        cls = "failed"
    elif window == "censored":
        cls = "censored"  # includes a completion after 900 s; its c* is still reported
    elif c_star is not None and c_star < MIN_CSTAR:
        cls = "low_cstar"
    elif window == "below":
        cls = "fast"
    else:
        cls = "eligible"
    return {"class": cls, "c_star": c_star, "lower_bound": lb, "solve_s": s}


def cell_outcome(classes: List[str]) -> str:
    c = Counter(classes)
    if c["failed"]:
        return "incomplete"
    if c["eligible"] >= NEED:
        return "promising"
    if c["low_cstar"] + c["fast"] >= NEED:
        return "too_easy"
    if c["censored"] >= NEED:
        return "too_hard"
    return "mixed"


def _fmt(x: Optional[float]) -> str:
    return "" if x is None else f"{x:.3f}"


def build(manifest_path: str, rows_path: str) -> Dict[str, str]:
    gen = read_jsonl(manifest_path)
    if len(gen) != 45:
        raise Fatal(f"{manifest_path}: {len(gen)} rows, expected 45")
    prof_by_inst = {}
    envs = Counter()
    if os.path.isfile(rows_path):
        for r in read_jsonl(rows_path):
            prof_by_inst[r["instance"]] = r
            env = r.get("env") or {}
            envs[(env.get("pysat_version"), env.get("python"))] += 1
    extra = set(prof_by_inst) - {g["instance"] for g in gen}
    if extra:
        raise Fatal(f"{len(extra)} RC2 rows for instances not in the manifest: {sorted(extra)[:3]}")

    inst_rows, by_cell = [], defaultdict(list)
    for g in gen:
        r = prof_by_inst.get(g["instance"])
        prof = r["profile"] if r else None
        ic = instance_class(prof)
        eps = g["alpha"] - 1.0
        row = {
            "cell_id": g["cell_id"], "n": g["n"], "alpha": g["alpha"], "m": g["m"],
            "n_eps3": f"{g['n'] * eps ** 3:.2f}", "gen_seed": g["seed"],
            "instance": g["instance"], "instance_sha256": g["instance_sha256"],
            "rc2_status": (prof or {}).get("status", "missing"),
            "completed": (prof or {}).get("completed", False),
            "solve_s": _fmt(ic["solve_s"]),
            "c_star": "" if ic["c_star"] is None else ic["c_star"],
            "lower_bound": "" if ic["lower_bound"] is None else ic["lower_bound"],
            "class": ic["class"],
            "pysat_version": ((r or {}).get("env") or {}).get("pysat_version", ""),
            "host": ((r or {}).get("env") or {}).get("host", ""),
        }
        inst_rows.append(row)
        by_cell[g["cell_id"]].append((row, ic))

    cell_rows = []
    for cid, items in by_cell.items():
        r0 = items[0][0]
        classes = [ic["class"] for _, ic in items]
        cnt = Counter(classes)
        done = sorted(ic["solve_s"] for _, ic in items
                      if ic["c_star"] is not None and ic["solve_s"] is not None)
        outcome = cell_outcome(classes)
        cell_rows.append({
            "cell_id": cid, "n": r0["n"], "alpha": r0["alpha"], "m": r0["m"],
            "n_eps3": r0["n_eps3"], "instances": len(items),
            "eligible": cnt["eligible"], "low_cstar": cnt["low_cstar"], "fast": cnt["fast"],
            "censored": cnt["censored"], "failed": cnt["failed"],
            "c_star_values": " ".join(str(ic["c_star"]) for _, ic in items if ic["c_star"] is not None),
            "solve_s_completed (min/med/max)": (
                f"{done[0]:.1f}/{statistics.median(done):.1f}/{done[-1]:.1f}" if done else ""),
            "censored_lower_bounds": " ".join(
                "?" if ic["lower_bound"] is None else str(ic["lower_bound"])
                for _, ic in items if ic["class"] == "censored" and ic["c_star"] is None),
            "outcome": outcome, "follow_up": FOLLOW_UP[outcome],
        })

    out = {}
    for name, cols, rows in (("instances.csv", INST_COLS, inst_rows),
                             ("cells.csv", CELL_COLS, cell_rows)):
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        out[name] = buf.getvalue()
    out["_envs"] = json.dumps({f"{k[0]}|{k[1]}": v for k, v in envs.items()})
    out["_cells"] = json.dumps(cell_rows)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=os.path.join("data", "generated", BATCH, "manifest.jsonl"))
    ap.add_argument("--rows", default=os.path.join("results", f"profile_{BATCH}_all.jsonl"))
    ap.add_argument("--out-dir", default=os.path.join("results", BATCH))
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    try:
        out = build(args.manifest, args.rows)
    except Fatal as e:
        print(f"FATAL: {e}", file=sys.stderr)
        return 2
    envs = json.loads(out.pop("_envs"))
    cells = json.loads(out.pop("_cells"))
    if args.check:
        drift = [n for n, t in out.items()
                 if not os.path.isfile(os.path.join(args.out_dir, n))
                 or open(os.path.join(args.out_dir, n), encoding="utf-8").read() != t]
        if drift:
            print(f"DRIFT: {drift}")
            return 3
        print("CHECK OK")
        return 0
    os.makedirs(args.out_dir, exist_ok=True)
    for n, t in out.items():
        with open(os.path.join(args.out_dir, n), "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    print(f"pysat|python across rows: {envs or 'no RC2 rows yet'}")
    if len(envs) > 1:
        print("WARNING: more than one PySAT/python version in this batch")
    print(f"{'cell':32s} {'n*eps^3':>8s} elig low fast cens fail  outcome")
    for c in cells:
        print(f"{c['cell_id']:32s} {c['n_eps3']:>8s} {c['eligible']:4d} {c['low_cstar']:3d} "
              f"{c['fast']:4d} {c['censored']:4d} {c['failed']:4d}  {c['outcome']}")
    print(f"wrote {args.out_dir}/instances.csv, cells.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
