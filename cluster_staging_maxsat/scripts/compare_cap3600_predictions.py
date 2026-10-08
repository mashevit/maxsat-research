#!/usr/bin/env python3
"""Compare the cap-3600 RC2 rows with the predictions recorded before the run.

Predictions and group definitions: docs/current/RC2_CAP3600_RERUN.md §6
(recorded 2026-10-08, before submission). The groups come from what the
sibling seeds of each cell did at 900 s, so they are fixed here as explicit
cell lists, not recomputed from the new rows.

    python3 scripts/aggregate_rc2_profile.py --batch cap3600 --manifest scripts/manifest_rc2_cap3600.txt
    python3 scripts/compare_cap3600_predictions.py

Run from cluster_staging_maxsat/. Tasks without a row yet are counted as
"no row" and never as censored.
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import OrderedDict

TASKS = "scripts/manifest_rc2_cap3600.tasks.csv"
ROWS = "results/profile_cap3600_all.jsonl"

# (source, k, n, m/n) cells whose sibling seeds certified at 900 s.
BORDERLINE_2SAT = {("calib_b", 2, 100, "4.50"), ("calib_b", 2, 100, "5.00"),
                   ("calib_b", 2, 150, "3.15"), ("calib_b", 2, 150, "3.30"),
                   ("calib_b", 2, 250, "2.35"), ("calib_b", 2, 250, "2.50"),
                   ("calib_b", 2, 400, "2.30"), ("calib_a", 2, 150, "3.00")}
NEAR_EDGE_2SAT = {("calib_a", 2, 100, "6.00")}
BORDERLINE_3SAT = {("calib_a", 3, 150, "5.00"), ("calib_a", 3, 250, "4.26"),
                   ("calib_b", 3, 50, "8.50"), ("calib_b", 3, 50, "9.00"),
                   ("calib_b", 3, 70, "6.50"), ("calib_b", 3, 100, "5.50"),
                   ("calib_b", 3, 150, "4.60"), ("calib_b", 3, 150, "4.80"),
                   ("calib_b", 3, 250, "4.35")}

# group -> (prediction text, test on (certified, total with a row))
PREDICTIONS = OrderedDict([
    ("G1 Max-2-SAT borderline", ("majority certify", lambda c, t: c * 2 > t)),
    ("G2 Max-2-SAT near-edge", (">= 1 of 4 certifies", lambda c, t: c >= 1)),
    ("G3 Max-2-SAT deep", ("<= 10% certify", lambda c, t: c * 10 <= t)),
    ("G4 3-SAT borderline (generated)", ("majority certify", lambda c, t: c * 2 > t)),
    ("G5 3-SAT deep (generated)", ("<= 10% certify", lambda c, t: c * 10 <= t)),
    ("G6 SATLIB uuf200/225 (LB 2)", ("majority certify", lambda c, t: c * 2 > t)),
    ("G7 uuf250 LB 1", ("majority certify (lean)", lambda c, t: c * 2 > t)),
    ("G8 uuf250 LB 2", ("no call; tests C2 of the Max-3-SAT note", None)),
    ("G9 hole10", ("stays censored", lambda c, t: c == 0)),
])


def group_of(row: dict) -> str:
    inst, src, lb = row["instance"], row["source"], row["prior_cost_lower_bound"]
    m = re.search(r"wksat_v(\d+)_k(\d)_sr([\d.]+)_", inst)
    if m:
        cell = (src.split("/")[1], int(m[2]), int(m[1]), m[3])
        if cell[1] == 2:
            if cell in BORDERLINE_2SAT:
                return "G1 Max-2-SAT borderline"
            if cell in NEAR_EDGE_2SAT:
                return "G2 Max-2-SAT near-edge"
            return "G3 Max-2-SAT deep"
        return ("G4 3-SAT borderline (generated)" if cell in BORDERLINE_3SAT
                else "G5 3-SAT deep (generated)")
    if "hole10" in inst:
        return "G9 hole10"
    if src == "satlib_bench":
        return "G6 SATLIB uuf200/225 (LB 2)"
    return "G7 uuf250 LB 1" if lb == "1" else "G8 uuf250 LB 2"


def main() -> int:
    if not os.path.isfile(TASKS):
        sys.exit(f"FATAL: {TASKS} not found; run from cluster_staging_maxsat/")
    tasks = list(csv.DictReader(open(TASKS)))
    rows = {}
    if os.path.isfile(ROWS):
        for line in open(ROWS):
            r = json.loads(line)
            rows[r["instance"]] = r["profile"]
    else:
        print(f"note: {ROWS} not found; every task counts as 'no row'")

    stats = OrderedDict((g, {"n": 0, "row": 0, "cert": 0, "cstar_gt_lb": 0, "times": []})
                        for g in PREDICTIONS)
    for t in tasks:
        g = stats[group_of(t)]
        g["n"] += 1
        p = rows.get(t["instance"])
        if p is None:
            continue
        g["row"] += 1
        if p.get("completed"):
            g["cert"] += 1
            g["times"].append(p["solve_s"])
            if t["prior_cost_lower_bound"] and p["final_cost"] > int(t["prior_cost_lower_bound"]):
                g["cstar_gt_lb"] += 1

    print(f"{'group':34s} {'tasks':>5s} {'rows':>4s} {'cert':>4s} {'c*>oldLB':>8s} "
          f"{'med s':>6s}  prediction -> outcome")
    for name, s in stats.items():
        text, test = PREDICTIONS[name]
        if s["row"] < s["n"]:
            verdict = "pending (rows missing)"
        elif test is None:
            verdict = "recorded only"
        else:
            verdict = "HELD" if test(s["cert"], s["row"]) else "FAILED"
        times = sorted(s["times"])
        med = f"{times[len(times) // 2]:.0f}" if times else "-"
        print(f"{name:34s} {s['n']:5d} {s['row']:4d} {s['cert']:4d} {s['cstar_gt_lb']:8d} "
              f"{med:>6s}  {text} -> {verdict}")
    print(f"total tasks {sum(s['n'] for s in stats.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
