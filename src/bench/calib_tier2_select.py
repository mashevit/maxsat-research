#!/usr/bin/env python3
"""Tier-2 eligibility over the calibration batches: per instance, deduplicated.

Two different rules live in this repository and this script keeps them apart
(docs/CALIB_B_PLAN.md §2):

  (a) PER-INSTANCE eligibility -- the established rule, `assign_tier()` in
      src/cli/profile_hardness.py: T1_MAX_S = 60, T2A_MAX_S = 300,
      T2B_MAX_S = 600. An instance is Tier 2 iff RC2 COMPLETED (it proved
      c*, so there is an oracle target) and 60 s < solve_s <= 600 s.
      src/bench/make_tier2_manifest.py's `include_solved_t3` rescue extends
      the upper edge to the batch cap, because assign_tier() ignores --cap
      and labels a 600-900 s completion T3. This script computes both, plus a
      LABELLED SENSITIVITY at a lower floor, and changes no threshold.

  (b) CELL-level selection -- goals §5.3: certified fraction >= 4/5 and
      median solve_s >= 10 s. That rule says where to SAMPLE. It never makes
      an instance eligible: a cell with a 200 s median still contributes only
      the seeds that individually land in the window, and a cell that fails
      (b) can still contribute an eligible instance. The cell table is
      printed beside the instance table, and neither is derived from the
      other.

Censoring: a row that hit the cap is right-censored. Its `cost_lower_bound`
is a LOWER BOUND, never an optimum, so a censored instance can never be
eligible (no target for the memetic arm) and is counted, not dropped.

    python -m src.bench.calib_tier2_select --batches calib_a calib_b
    python -m src.bench.calib_tier2_select --batches calib_a --floor 30

Outputs under --out-dir (default results/calibration/):
    tier2_eligible.csv     one row per eligible instance, deduplicated
    tier2_cells.csv        one row per cell, both batches, with the (b) verdict
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Mirrors src/cli/profile_hardness.py; imported as values, not re-defined as
# policy -- if those constants move, this script moves with them.
from src.cli.profile_hardness import T1_MAX_S, T2B_MAX_S

CENSORED = ("timeout", "subprocess_killed")


def load_batch(staging_root: Path, batch: str) -> List[Dict[str, Any]]:
    """Join the RC2 rows of one batch to its generator manifest on the
    instance path, cross-checked on nothing else -- the sha lives in the
    manifest and is carried through so a later stage can verify the file."""
    agg = staging_root / "results" / f"profile_{batch}_all.jsonl"
    man = staging_root / "data" / "generated" / batch / "manifest.jsonl"
    for p in (agg, man):
        if not p.exists():
            raise SystemExit(f"FATAL: not found: {p}")
    manifest = {}
    with open(man, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                manifest[os.path.normpath(r["instance"])] = r
    out = []
    with open(agg, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            key = os.path.normpath(row["instance"])
            m = manifest.get(key)
            if m is None:
                raise SystemExit(f"FATAL: {batch} row has no manifest entry: {key}")
            out.append({"batch": batch, "row": row, "man": m})
    missing = set(manifest) - {os.path.normpath(r["row"]["instance"]) for r in out}
    if missing:
        print(f"NOTE: {batch}: {len(missing)} manifest instances have no RC2 row "
              f"(not run, or the task left no row -- §4.4 class 3)", file=sys.stderr)
    return out


def classify(rec: Dict[str, Any], floor: float, ceiling: Optional[float]) -> str:
    """'eligible' | 'trivial' | 'over_ceiling' | 'censored' | 'failed'.

    `ceiling=None` means "up to the row's own cap" (the include_solved_t3
    reading of rule (a) at a 900 s cap).
    """
    p = rec["row"]["profile"]
    if p.get("completed") is True:
        t = p["solve_s"]
        if t is None or t < 0:
            # A negative duration is a clock step in the child's time.time()
            # timing, not a measurement -- see scripts/aggregate_rc2_profile.py.
            return "failed"
        hi = ceiling if ceiling is not None else float(p["cap_s"])
        if t <= floor:
            return "trivial"
        return "eligible" if t <= hi else "over_ceiling"
    if p.get("status") in CENSORED:
        return "censored"
    return "failed"


def counts(recs: List[Dict[str, Any]], floor: float,
           ceiling: Optional[float]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in recs:
        c = classify(r, floor, ceiling)
        out[c] = out.get(c, 0) + 1
    return out


def dedupe(recs: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Deduplicate on instance_sha256: identical bytes are one instance even if
    two batches generated them. Keeps the first occurrence in batch order and
    records the duplicate."""
    seen: Dict[str, Dict[str, Any]] = {}
    dups: List[str] = []
    for r in recs:
        sha = r["man"]["instance_sha256"]
        if sha in seen:
            dups.append(f"{r['batch']}:{os.path.basename(r['man']['instance'])} "
                        f"== {seen[sha]['batch']}:"
                        f"{os.path.basename(seen[sha]['man']['instance'])}")
            continue
        seen[sha] = r
    return list(seen.values()), dups


def cell_table(recs: List[Dict[str, Any]], floor: float,
               ceiling: Optional[float]) -> List[Dict[str, Any]]:
    """Rule (b): cell-level statistics, with unequal cell sizes made explicit."""
    cells: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in recs:
        cells.setdefault((r["batch"], r["man"]["cell_id"]), []).append(r)
    rows = []
    for (batch, cell_id), members in sorted(cells.items()):
        m0 = members[0]["man"]
        done = [r["row"]["profile"] for r in members
                if r["row"]["profile"].get("completed") is True]
        times = sorted(p["solve_s"] for p in done)
        costs = sorted(p["final_cost"] for p in done)
        elig = sum(1 for r in members if classify(r, floor, ceiling) == "eligible")
        frac = len(done) / len(members)
        med = statistics.median(times) if times else None
        rows.append({
            "batch": batch, "cell_id": cell_id, "family": m0["family"],
            "k": m0["k"], "n": m0["n"], "alpha": m0["alpha"], "m": m0["m"],
            "seeds": len(members),
            "certified": len(done),
            "certified_frac": round(frac, 3),
            "solve_s_min": round(times[0], 3) if times else "",
            "solve_s_med": round(med, 3) if med is not None else "",
            "solve_s_max": round(times[-1], 3) if times else "",
            "cstar_min": costs[0] if costs else "",
            "cstar_max": costs[-1] if costs else "",
            "eligible_instances": elig,
            # Rule (b), reported as a verdict -- it selects cells, not instances.
            "cell_rule_b": "pass" if (frac >= 0.8 and med is not None and med >= 10.0)
                           else "fail",
        })
    return rows


def instance_rows(recs: List[Dict[str, Any]], floor: float,
                  ceiling: Optional[float]) -> List[Dict[str, Any]]:
    out = []
    for r in recs:
        if classify(r, floor, ceiling) != "eligible":
            continue
        p, m = r["row"]["profile"], r["man"]
        out.append({
            "batch": r["batch"], "cell_id": m["cell_id"], "family": m["family"],
            "k": m["k"], "n": m["n"], "alpha": m["alpha"], "m": m["m"],
            "seed": m["seed"], "instance": m["instance"],
            "instance_sha256": m["instance_sha256"],
            "oracle_cost": p["final_cost"], "rc2_solve_s": round(p["solve_s"], 3),
            "rc2_cap_s": p["cap_s"], "tier": r["row"].get("tier", ""),
            "pysat_version": (r["row"].get("env") or {}).get("pysat_version", ""),
        })
    out.sort(key=lambda d: (d["k"], d["n"], d["alpha"], d["seed"]))
    return out


def write_csv(path: Path, rows: List[Dict[str, Any]], cols: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batches", nargs="+", default=["calib_a"],
                    help="calibration batches to pool (default: %(default)s)")
    ap.add_argument("--staging-root", default="cluster_staging_maxsat")
    ap.add_argument("--out-dir", default="results/calibration")
    ap.add_argument("--floor", type=float, default=T1_MAX_S,
                    help="per-instance solve_s floor, s (default: %(default)s = "
                         "T1_MAX_S; a different value is a SENSITIVITY, and the "
                         "reason for changing it belongs in the log)")
    ap.add_argument("--ceiling", default=str(T2B_MAX_S),
                    help="per-instance solve_s ceiling in s, or 'cap' for the "
                         "row's own cap (the include_solved_t3 reading). "
                         "Default: %(default)s = T2B_MAX_S")
    ap.add_argument("--no-write", action="store_true", help="print only")
    args = ap.parse_args(argv)

    ceiling: Optional[float] = None if args.ceiling == "cap" else float(args.ceiling)
    root = Path(args.staging_root)

    recs: List[Dict[str, Any]] = []
    for b in args.batches:
        recs.extend(load_batch(root, b))
    pooled, dups = dedupe(recs)

    print(f"batches        : {', '.join(args.batches)}")
    print(f"rows           : {len(recs)}  ({len(pooled)} after sha256 dedupe, "
          f"{len(dups)} duplicate(s))")
    for d in dups[:10]:
        print(f"  duplicate: {d}")
    print(f"window         : {args.floor:g} s < solve_s <= "
          f"{'cap' if ceiling is None else format(ceiling, 'g') + ' s'}   "
          f"(assign_tier: T1_MAX_S={T1_MAX_S:g}, T2B_MAX_S={T2B_MAX_S:g})")
    print()
    print("per-instance classes (rule a):")
    for b in args.batches:
        sub = [r for r in pooled if r["batch"] == b]
        print(f"  {b:<10} {counts(sub, args.floor, ceiling)}")
    print(f"  {'POOLED':<10} {counts(pooled, args.floor, ceiling)}")
    print()
    print("windows compared (eligible counts, pooled; the first is the "
          "established rule):")
    for lbl, fl, ce in ((f"{T1_MAX_S:g}-{T2B_MAX_S:g} s  (assign_tier T2a+T2b)",
                         T1_MAX_S, T2B_MAX_S),
                        (f"{T1_MAX_S:g} s-cap   (+ include_solved_t3)", T1_MAX_S, None),
                        ("30 s-cap    (SENSITIVITY, not an adopted threshold)",
                         30.0, None)):
        print(f"  {lbl:<52} {counts(pooled, fl, ce).get('eligible', 0)}")
    print()

    cells = cell_table(pooled, args.floor, ceiling)
    inst = instance_rows(pooled, args.floor, ceiling)
    n_pass = sum(1 for c in cells if c["cell_rule_b"] == "pass")
    print(f"cells          : {len(cells)}  ({n_pass} pass the §5.3 cell rule; "
          f"that rule selects cells, not instances)")
    sizes = sorted({c["seeds"] for c in cells})
    if len(sizes) > 1:
        print(f"NOTE: unequal cell sizes {sizes} -- certified_frac is per-cell "
              f"and every downstream table must say so (CALIB_B_PLAN §4b).")
    print(f"eligible       : {len(inst)} instances in "
          f"{len({i['cell_id'] for i in inst})} cells")
    for i in inst:
        print(f"  {i['batch']:<8} k={i['k']} n={i['n']:<4} a={i['alpha']:<5g} "
              f"s{i['seed']:<3} {i['rc2_solve_s']:>8.1f} s  c*={i['oracle_cost']}")

    if args.no_write:
        return 0
    out = Path(args.out_dir)
    write_csv(out / "tier2_eligible.csv", inst, list(inst[0].keys()) if inst else
              ["batch", "cell_id", "instance", "rc2_solve_s"])
    write_csv(out / "tier2_cells.csv", cells, list(cells[0].keys()))
    print(f"\nwrote          : {out / 'tier2_eligible.csv'}  ({len(inst)} rows)")
    print(f"wrote          : {out / 'tier2_cells.csv'}  ({len(cells)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
