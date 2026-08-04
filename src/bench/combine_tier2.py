# src/bench/combine_tier2.py
"""
Join tier-2 memetic shards against the RC2 oracle and emit the comparison tables.

Run on the workstation after pulling `results/tier2_memetic/tasks/` back from
the cluster:

    python -m src.bench.combine_tier2 \
        --in-dir results/tier2_memetic/tasks \
        --oracle cluster_staging_maxsat/scripts/tier2_oracle.csv \
        --out-dir results/tier2_memetic

Outputs:
  all_runs.jsonl      every shard, concatenated verbatim (the source of truth)
  runs.csv            one row per (instance, config, budget, seed), flattened
  by_instance.csv     one row per (instance, config, budget), aggregated over seeds
  summary.csv         one row per (config, budget) -- the table for the paper
  integrity.txt       shard/manifest reconciliation and every anomaly found

Join key is `instance_sha256`, with a basename fallback. The RC2 records have no
checksum (docs/RC2_STATUS.md §2.5), so the oracle CSV carries the sha the
manifest generator computed at build time; a mismatch means the corpus moved
between manifest build and run, and is reported rather than silently joined.

Metric guidance is in docs/TIER2_MEMETIC_PLAN.md §6. The short version: on the
SATLIB half of tier 2 the optimum is 1 or 2, so `rel_gap` is a nearly binary
quantity and a poor headline number. Read `hit_rate` (fraction of seeds that
reach the optimum) and `best_cost` spread instead.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import statistics
from collections import defaultdict
from typing import Any, Dict, List, Optional

RUN_COLUMNS = [
    "job_id", "instance", "basename", "instance_sha256", "instance_format",
    "config_id", "config_hash", "seed", "budget_s", "wall_time_s",
    "status", "error", "best_cost", "hard_violations", "unsat_soft_clauses",
    "ea_generations", "children", "total_flips", "best_assignment_hash",
    "oracle_cost", "abs_gap", "rel_gap", "is_optimal", "feasible",
    "rc2_tier", "rc2_run", "rc2_solve_s", "speedup_vs_rc2",
    "n_vars", "n_clauses", "n_hard", "n_soft",
    "git_sha", "host", "slurm_job", "shard",
]


def load_oracle(path: str) -> Dict[str, Dict[str, Any]]:
    """Index the oracle table by sha256 and by basename."""
    idx: Dict[str, Dict[str, Any]] = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["oracle_cost"] = int(row["oracle_cost"])
            row["rc2_solve_s"] = float(row["rc2_solve_s"])
            idx["sha:" + row["sha256"]] = row
            idx["name:" + os.path.basename(row["resolved"])] = row
    return idx


def load_shards(in_dir: str) -> List[Dict[str, Any]]:
    recs = []
    for path in sorted(glob.glob(os.path.join(in_dir, "*.jsonl"))):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                r["_shard"] = os.path.basename(path)
                recs.append(r)
    return recs


def flatten(r: Dict[str, Any], oracle: Dict[str, Dict[str, Any]],
            notes: List[str]) -> Dict[str, Any]:
    basename = os.path.basename(r.get("instance", ""))
    o = oracle.get("sha:" + (r.get("instance_sha256") or ""))
    if o is None:
        o = oracle.get("name:" + basename)
        if o is not None:
            notes.append(
                f"{r.get('job_id')}: sha mismatch on {basename} "
                f"(shard {r.get('instance_sha256','?')[:12]} vs oracle {o['sha256'][:12]}) "
                f"-- joined by basename, the bytes solved differ from the bytes profiled")

    feasible = (r.get("hard_violations") == 0) if r.get("hard_violations") is not None else None
    # The shard computes gap fields itself; recompute here so a manifest with a
    # stale --oracle-cost cannot poison the table.
    abs_gap = rel_gap = is_opt = None
    oracle_cost = o["oracle_cost"] if o else r.get("oracle_cost")
    if oracle_cost is not None and r.get("best_cost") is not None and feasible:
        abs_gap = r["best_cost"] - oracle_cost
        rel_gap = round(abs_gap / oracle_cost, 6) if oracle_cost > 0 else None
        is_opt = abs_gap == 0
        if abs_gap < 0:
            notes.append(
                f"{r.get('job_id')}: best_cost {r['best_cost']} beats the RC2 optimum "
                f"{oracle_cost} on {basename} -- the two solvers disagree on the "
                f"instance semantics; do NOT average this row")

    speedup = None
    if o and is_opt and r.get("wall_time_s"):
        # Coarse: the EA has no anytime curve yet, so time-to-optimum is
        # unknown and wall_time_s is an upper bound (docs/TIER2_MEMETIC_PLAN §6).
        speedup = round(o["rc2_solve_s"] / r["wall_time_s"], 3)

    slurm = r.get("slurm") or {}
    return {
        "job_id": r.get("job_id"), "instance": r.get("instance"), "basename": basename,
        "instance_sha256": r.get("instance_sha256"), "instance_format": r.get("instance_format"),
        "config_id": r.get("config_id"), "config_hash": r.get("config_hash"),
        "seed": r.get("seed"), "budget_s": r.get("budget_s"), "wall_time_s": r.get("wall_time_s"),
        "status": r.get("status"), "error": r.get("error"),
        "best_cost": r.get("best_cost"), "hard_violations": r.get("hard_violations"),
        "unsat_soft_clauses": r.get("unsat_soft_clauses"),
        "ea_generations": r.get("ea_generations"), "children": r.get("children"),
        "total_flips": r.get("total_flips"), "best_assignment_hash": r.get("best_assignment_hash"),
        "oracle_cost": oracle_cost, "abs_gap": abs_gap, "rel_gap": rel_gap,
        "is_optimal": is_opt, "feasible": feasible,
        "rc2_tier": (o or {}).get("tier", r.get("rc2_tier")),
        "rc2_run": (o or {}).get("rc2_run", r.get("rc2_run")),
        "rc2_solve_s": (o or {}).get("rc2_solve_s"),
        "speedup_vs_rc2": speedup,
        "n_vars": r.get("n_vars"), "n_clauses": r.get("n_clauses"),
        "n_hard": r.get("n_hard"), "n_soft": r.get("n_soft"),
        "git_sha": r.get("git_sha"), "host": r.get("host"),
        "slurm_job": f"{slurm.get('slurm_array_job_id')}_{slurm.get('slurm_array_task_id')}",
        "shard": r.get("_shard"),
    }


def _med(xs: List[float]) -> Optional[float]:
    return round(statistics.median(xs), 4) if xs else None


def aggregate_by_instance(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[(r["basename"], r["config_id"], r["budget_s"])].append(r)

    out = []
    for (inst, cfg, budget), g in sorted(groups.items()):
        ok = [r for r in g if r["status"] == "ok" and r["feasible"]]
        costs = [r["best_cost"] for r in ok if r["best_cost"] is not None]
        gaps = [r["abs_gap"] for r in ok if r["abs_gap"] is not None]
        opt_runs = [r for r in ok if r["is_optimal"]]
        out.append({
            "basename": inst, "config_id": cfg, "budget_s": budget,
            "oracle_cost": g[0]["oracle_cost"], "rc2_tier": g[0]["rc2_tier"],
            "rc2_solve_s": g[0]["rc2_solve_s"],
            "n_seeds": len(g), "n_ok": len(ok), "n_failed": len(g) - len(ok),
            "best_cost_min": min(costs) if costs else None,
            "best_cost_median": _med(costs),
            "best_cost_max": max(costs) if costs else None,
            "abs_gap_min": min(gaps) if gaps else None,
            "abs_gap_median": _med(gaps),
            "hit_rate": round(len(opt_runs) / len(ok), 4) if ok else None,
            "any_optimal": bool(opt_runs),
            "wall_time_median": _med([r["wall_time_s"] for r in ok if r["wall_time_s"]]),
            "speedup_vs_rc2_median": _med([r["speedup_vs_rc2"] for r in opt_runs
                                           if r["speedup_vs_rc2"]]),
        })
    return out


def aggregate_summary(rows: List[Dict[str, Any]],
                      by_inst: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[(r["config_id"], r["budget_s"])].append(r)
    inst_groups: Dict[tuple, List[Dict[str, Any]]] = defaultdict(list)
    for r in by_inst:
        inst_groups[(r["config_id"], r["budget_s"])].append(r)

    out = []
    for key, g in sorted(groups.items()):
        cfg, budget = key
        ok = [r for r in g if r["status"] == "ok" and r["feasible"]]
        gaps = [r["abs_gap"] for r in ok if r["abs_gap"] is not None]
        rels = [r["rel_gap"] for r in ok if r["rel_gap"] is not None]
        ig = inst_groups[key]
        out.append({
            "config_id": cfg, "budget_s": budget,
            "n_instances": len(ig), "n_runs": len(g), "n_ok": len(ok),
            "n_failed": len(g) - len(ok),
            "runs_optimal": sum(1 for r in ok if r["is_optimal"]),
            "run_hit_rate": round(sum(1 for r in ok if r["is_optimal"]) / len(ok), 4) if ok else None,
            "instances_solved_any_seed": sum(1 for r in ig if r["any_optimal"]),
            "instance_coverage": round(sum(1 for r in ig if r["any_optimal"]) / len(ig), 4) if ig else None,
            "abs_gap_mean": round(statistics.fmean(gaps), 4) if gaps else None,
            "abs_gap_median": _med(gaps),
            "abs_gap_max": max(gaps) if gaps else None,
            "rel_gap_mean": round(statistics.fmean(rels), 6) if rels else None,
            "rel_gap_median": _med(rels),
            "solver_seconds": round(sum(r["wall_time_s"] or 0 for r in g), 1),
            "rc2_seconds_for_same_instances": round(
                sum(r["rc2_solve_s"] or 0 for r in ig), 1),
        })
    return out


def write_csv(path: str, rows: List[Dict[str, Any]], columns: List[str]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="src.bench.combine_tier2",
        description="Join tier-2 memetic shards with the RC2 oracle.",
    )
    p.add_argument("--in-dir", required=True, help="Directory of memetic JSONL shards")
    p.add_argument("--oracle", required=True, help="tier2_oracle.csv from make_tier2_manifest")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--manifest", default=None,
                   help="Optional manifest to reconcile against (reports missing jobs)")
    args = p.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)
    oracle = load_oracle(args.oracle)
    shards = load_shards(args.in_dir)
    if not shards:
        raise SystemExit(f"No shards found in {args.in_dir}")

    notes: List[str] = []
    rows = [flatten(r, oracle, notes) for r in shards]

    with open(os.path.join(args.out_dir, "all_runs.jsonl"), "w", encoding="utf-8") as f:
        for r in shards:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    by_inst = aggregate_by_instance(rows)
    summary = aggregate_summary(rows, by_inst)

    write_csv(os.path.join(args.out_dir, "runs.csv"), rows, RUN_COLUMNS)
    write_csv(os.path.join(args.out_dir, "by_instance.csv"), by_inst, list(by_inst[0].keys()))
    write_csv(os.path.join(args.out_dir, "summary.csv"), summary, list(summary[0].keys()))

    # ---- integrity -----------------------------------------------------------
    lines = [f"shards read            : {len(shards)}"]
    bad_status = [r for r in rows if r["status"] != "ok"]
    lines.append(f"status != ok           : {len(bad_status)}")
    for r in bad_status:
        lines.append(f"    {r['job_id']} {r['basename']} {r['status']}: {r['error']}")
    infeasible = [r for r in rows if r["feasible"] is False]
    lines.append(f"hard_violations > 0    : {len(infeasible)}")
    unjoined = [r for r in rows if r["oracle_cost"] is None]
    lines.append(f"no oracle match        : {len(unjoined)}")
    for r in unjoined:
        lines.append(f"    {r['job_id']} {r['basename']}")
    dups: Dict[str, int] = defaultdict(int)
    for r in rows:
        dups[r["job_id"] or "<none>"] += 1
    repeated = {k: v for k, v in dups.items() if v > 1}
    lines.append(f"duplicate job_ids      : {len(repeated)} {repeated or ''}")

    if args.manifest:
        want = set()
        with open(args.manifest, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    want.add(line.split("\t")[0])
        have = {r["job_id"] for r in rows}
        missing = sorted(want - have)
        lines.append(f"manifest jobs          : {len(want)}")
        lines.append(f"missing shards         : {len(missing)}")
        if missing:
            lines.append("    " + " ".join(missing[:50]) + (" ..." if len(missing) > 50 else ""))
            lines.append("    resubmit: sbatch --array=" +
                         ",".join(m.rsplit("_", 1)[-1].lstrip("0") for m in missing[:200]) +
                         " scripts/tier2_memetic_array.sbatch")
        lines.append(f"unexpected shards      : {len(sorted(have - want))}")

    if notes:
        lines.append("")
        lines.append("ANOMALIES")
        lines.extend("    " + n for n in notes)

    text = "\n".join(lines) + "\n"
    with open(os.path.join(args.out_dir, "integrity.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"wrote runs.csv / by_instance.csv / summary.csv / integrity.txt to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
