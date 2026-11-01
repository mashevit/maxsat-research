#!/usr/bin/env python3
"""Exploratory ρ subsets on MSE 2026 (NOT pre-registered; user request 2026-11-01).

Reads the per-instance x, y written by mse26_rho_errors.py (results/mse26_rho_<errors>/
instances.csv, primary and complete rows only) and recomputes ρ with the pre-registered
method (mse26_rho.rho_ci: midranks, BCa, B = 10,000, seed 20261029) on these subsets:

  E1 both solved, all x        x finite, y finite (no 30 s lower bound)
  E2 not both ∞, all x         drop only the instances where both are ∞
  E3 window, y may be ∞        x in (30, 3600] (so x finite), y finite or ∞
  E4 x > 30 s, not both ∞      x in (30, 3600] or x = ∞, both-∞ instances dropped

For reference, sensitivity 1 of the prereg = window and y finite.

    python3 scripts/mse26_rho_explore.py            # both treatments
Output: results/mse26_rho_explore/{summary.json,report.md}.
MSE26_RHO_TAG=<tag> reads results/mse26_rho_<tag><errors>/ and writes
results/mse26_rho_explore_<tag>/ (2026-11-01: tag r3_ = MSE26_RHO_RESULTS_3.md).
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mse26_rho as rho  # noqa: E402

LOW = 30.0
TAG = os.environ.get("MSE26_RHO_TAG", "")
SUBSETS = [
    ("E1", "both solved, all x", lambda x, y: math.isfinite(x) and math.isfinite(y)),
    ("E2", "not both ∞, all x", lambda x, y: math.isfinite(x) or math.isfinite(y)),
    ("E3", "window (30, 3600] s, y may be ∞", lambda x, y: LOW < x <= rho.X_LIMIT),
    ("E4", "x > 30 s (∞ included), not both ∞", lambda x, y: x > LOW and (math.isfinite(x) or math.isfinite(y))),
    ("ref", "prereg sens. 1: window, y finite", lambda x, y: LOW < x <= rho.X_LIMIT and math.isfinite(y)),
]


def cell(r) -> str:
    if r.get("rho") is None or math.isnan(r["rho"]):
        return "n/a"
    ci = f"[{r['lo']:+.3f}, {r['hi']:+.3f}]" if r.get("lo") is not None else "[CI n/a]"
    return f"{r['rho']:+.3f} {ci}"


def load(mode: str):
    path = os.path.join(rho.ROOT, "results", f"mse26_rho_{TAG}{mode}", "instances.csv")
    with open(path, newline="") as f:
        return [(float(r["x"]), float(r["y"])) for r in csv.DictReader(f)
                if r["primary"] == "True" and r["complete"] == "True"]


def main() -> int:
    res = {}
    for mode in ("fail", "exclude"):
        pts = load(mode)
        res[mode] = {}
        for key, _, keep in SUBSETS:
            sel = [(x, y) for x, y in pts if keep(x, y)]
            r = rho.rho_ci([x for x, _ in sel], [y for _, y in sel])
            r["interpretation"] = rho.interpret(r)
            res[mode][key] = r
    out = os.path.join(rho.ROOT, "results", "mse26_rho_explore" + (f"_{TAG.rstrip('_')}" if TAG else ""))
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "summary.json"), "w") as f:
        json.dump(rho.jsonable(res), f, indent=1)
    lines = ["| subset | `fail`: ρ [95 % CI] | N | ∞ x / y / both | `exclude`: ρ [95 % CI] | N | ∞ x / y / both |",
             "|---|---|---:|---|---|---:|---|"]
    for key, label, _ in SUBSETS:
        cells = []
        for mode in ("fail", "exclude"):
            r = res[mode][key]
            cells += [cell(r), str(r["n"]), f"{r['x_inf']} / {r['y_inf']} / {r['both_inf']}"]
        lines.append(f"| {key} {label} | " + " | ".join(cells) + " |")
    text = "\n".join(lines) + "\n"
    with open(os.path.join(out, "report.md"), "w") as f:
        f.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
