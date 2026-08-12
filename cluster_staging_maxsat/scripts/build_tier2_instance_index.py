#!/usr/bin/env python3
"""Join the tier2 memetic manifest with the RC2 profiling results.

One row per CNF instance in scripts/manifest_tier2_memetic.tsv, carrying the
planned memetic workload (configs / seeds / budget) alongside the RC2 profile
record for that instance (results/profile*/**.jsonl) and the sha256 recorded in
scripts/tier2_oracle.csv.

Usage: python3 scripts/build_tier2_instance_index.py [-o OUT.csv]
Run from cluster_staging_maxsat/.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
from collections import defaultdict

MANIFEST = "scripts/manifest_tier2_memetic.tsv"
ORACLE = "scripts/tier2_oracle.csv"
RESULT_GLOB = "results/*/*.jsonl"
DEFAULT_OUT = "results/tier2_memetic_instance_index.csv"

COLUMNS = [
    "instance",
    "basename",
    "family",
    "tier",
    "group",
    "sha256",
    "size_mb",
    "rc2_status",
    "rc2_final_cost",
    "rc2_cost_lower_bound",
    "rc2_solve_s",
    "rc2_cap_s",
    "rc2_completed",
    "rc2_tier_reason",
    "rc2_source",
    "memetic_runs",
    "memetic_configs",
    "memetic_seeds",
    "memetic_budget_s",
    "memetic_threads",
    "memetic_run_ids",
]


def load_manifest(path):
    """instance -> planned memetic workload, in manifest order."""
    plan = {}
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            run_id, inst, _cfg_path, cfg_name, seed, budget, threads, tier, group = line.split("\t")
            p = plan.setdefault(
                inst,
                {
                    "tier": tier,
                    "group": group,
                    "run_ids": [],
                    "configs": [],
                    "seeds": set(),
                    "budgets": set(),
                    "threads": set(),
                },
            )
            p["run_ids"].append(run_id)
            if cfg_name not in p["configs"]:
                p["configs"].append(cfg_name)
            p["seeds"].add(int(seed))
            p["budgets"].add(budget)
            p["threads"].add(threads)
    return plan


def load_rc2(pattern):
    """instance -> (source label, profile record). Later files do not clobber earlier ones."""
    out = {}
    dupes = defaultdict(list)
    for path in sorted(glob.glob(pattern)):
        with open(path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                inst = rec["instance"]
                src = os.path.relpath(path)
                dupes[inst].append(src)
                out.setdefault(inst, (src, rec))
    return out, {k: v for k, v in dupes.items() if len(v) > 1}


def load_sha(path):
    if not os.path.exists(path):
        return {}
    with open(path, newline="") as fh:
        return {r["instance"]: r.get("sha256", "") for r in csv.DictReader(fh)}


def fmt_range(values):
    """Compact seed list: contiguous ints become 'a-b'."""
    vals = sorted(values)
    if len(vals) > 1 and vals == list(range(vals[0], vals[-1] + 1)):
        return f"{vals[0]}-{vals[-1]}"
    return ";".join(str(v) for v in vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    plan = load_manifest(MANIFEST)
    rc2, dupes = load_rc2(RESULT_GLOB)
    shas = load_sha(ORACLE)

    rows = []
    missing = []
    for inst, p in plan.items():
        hit = rc2.get(inst)
        if hit is None:
            missing.append(inst)
            src, prof = "", {}
        else:
            src, rec = hit
            prof = rec.get("profile", {})
        rows.append(
            {
                "instance": inst,
                "basename": os.path.basename(inst),
                "family": os.path.basename(os.path.dirname(inst)),
                "tier": p["tier"],
                "group": p["group"],
                "sha256": shas.get(inst, ""),
                "size_mb": rec.get("size_mb", "") if hit else "",
                "rc2_status": prof.get("status", ""),
                "rc2_final_cost": prof.get("final_cost", ""),
                "rc2_cost_lower_bound": prof.get("cost_lower_bound", ""),
                "rc2_solve_s": prof.get("solve_s", ""),
                "rc2_cap_s": prof.get("cap_s", ""),
                "rc2_completed": prof.get("completed", ""),
                "rc2_tier_reason": rec.get("tier_reason", "") if hit else "",
                "rc2_source": src,
                "memetic_runs": len(p["run_ids"]),
                "memetic_configs": ";".join(p["configs"]),
                "memetic_seeds": fmt_range(p["seeds"]),
                "memetic_budget_s": ";".join(sorted(p["budgets"])),
                "memetic_threads": ";".join(sorted(p["threads"])),
                "memetic_run_ids": f"{p['run_ids'][0]}..{p['run_ids'][-1]}",
            }
        )

    # Easiest-first within each tier: the RC2 solve time is the hardness proxy.
    rows.sort(key=lambda r: (r["tier"], r["rc2_solve_s"] if r["rc2_solve_s"] != "" else float("inf")))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    print(f"wrote {args.out}: {len(rows)} instances, {sum(r['memetic_runs'] for r in rows)} planned runs")
    if missing:
        print(f"WARNING: {len(missing)} instances have no RC2 result:")
        for m in missing:
            print("  ", m)
    relevant_dupes = {i: s for i, s in dupes.items() if i in plan}
    if relevant_dupes:
        print(f"NOTE: {len(relevant_dupes)} instances appear in >1 result file; kept the first:")
        for inst, srcs in sorted(relevant_dupes.items()):
            print(f"   {inst}: {', '.join(srcs)}")


if __name__ == "__main__":
    main()
