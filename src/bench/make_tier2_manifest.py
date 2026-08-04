# src/bench/make_tier2_manifest.py
"""
Build the tier-2 memetic job manifest from the committed RC2 hardness profiles.

"Tier 2" is an *output* of RC2 profiling, not an input (docs/RC2_STATUS.md §0):
it is the set of instances RC2 solved to optimality in 60-600 s. Those are
exactly the instances that are (a) non-trivial and (b) carry an oracle optimum,
so they are the only ones on which a memetic-vs-exact comparison is meaningful.

Run this on the workstation (it needs `results/hardness/`), then commit the two
outputs into `cluster_staging_maxsat/scripts/` and rsync the staging tree.

    python -m src.bench.make_tier2_manifest \
        --hardness-dir results/hardness \
        --data-root cluster_staging_maxsat \
        --out-dir cluster_staging_maxsat/scripts

Outputs (all under --out-dir):
  manifest_tier2_memetic.tsv  one job per line, no header; line N == SLURM array
                              task N. Columns:
                                job_id instance config config_id seed
                                budget_s oracle_cost tier rc2_run
  tier2_oracle.csv            the RC2 reference table for the combine step
  tier2_skipped.txt           instances excluded, with the reason
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CONFIGS = [
    "configs/tier2/memetic_base.yaml",
    "configs/tier2/memetic_pop150.yaml",
    "configs/tier2/memetic_deeppolish.yaml",
]
DEFAULT_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_BUDGETS = [60.0, 300.0]

MANIFEST_COLUMNS = [
    "job_id", "instance", "config", "config_id",
    "seed", "budget_s", "oracle_cost", "tier", "rc2_run",
]


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_format(path: str) -> str:
    """Mirror of run_memetic_shard.detect_format; kept local so this script
    has no import-time dependency on the solver stack."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("c") or line.startswith("%"):
                continue
            if line.startswith("p "):
                toks = line.split()
                return "wcnf_old" if len(toks) > 1 and toks[1].lower() == "wcnf" else "cnf"
            return "wcnf_new"
    return "unknown"


def select_records(hardness_dir: str, tiers: List[str],
                   include_solved_t3: bool) -> List[Dict[str, Any]]:
    """
    Collect every RC2 record that qualifies as tier 2, i.e. solved to optimality
    and labelled with one of `tiers` -- plus, when `include_solved_t3`, records
    that are `completed=true` but landed in T3 because `assign_tier()`'s cutoffs
    ignore `--cap` (docs/RC2_STATUS.md §4.6). Those carry a valid oracle optimum
    and would otherwise be silently dropped.
    """
    out: List[Dict[str, Any]] = []
    pattern = os.path.join(hardness_dir, "*", "all_results.jsonl")
    for agg in sorted(glob.glob(pattern)):
        run = Path(agg).parent.name
        for line in open(agg, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            prof = r["profile"]
            if not prof["completed"]:
                continue
            keep = r["tier"] in tiers or (include_solved_t3 and r["tier"] == "T3")
            if not keep:
                continue
            out.append({
                "rc2_run": run,
                "instance": r["instance"],
                "tier": r["tier"],
                "oracle_cost": prof["final_cost"],
                "rc2_solve_s": prof["solve_s"],
                "rc2_cap_s": prof["cap_s"],
                "size_mb": r["size_mb"],
            })
    return out


def dedupe(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    The 75 MSE instances were profiled twice, at cap 600 and cap 1800
    (docs/RC2_STATUS.md §4.2), so an instance can qualify from two runs. Keep
    the fastest RC2 solve as the reference and note every run it came from.
    """
    by_key: Dict[str, Dict[str, Any]] = {}
    for r in sorted(records, key=lambda x: x["rc2_solve_s"]):
        key = os.path.basename(r["instance"])
        if key in by_key:
            by_key[key]["rc2_runs_all"].append(r["rc2_run"])
            if by_key[key]["oracle_cost"] != r["oracle_cost"]:
                by_key[key]["oracle_disagreement"] = True
            continue
        r = dict(r)
        r["rc2_runs_all"] = [r["rc2_run"]]
        r["oracle_disagreement"] = False
        by_key[key] = r
    return sorted(by_key.values(), key=lambda x: x["instance"])


def resolve(instance: str, data_root: str) -> Optional[str]:
    """
    RC2 recorded cluster-relative paths; two of the corpora
    (`data/unsat250_1000c/`, `data/unsat_uuf_diff/`) live only in the staging
    tree and are gitignored. Try the recorded path under --data-root first,
    then the repo-relative path, then a unique basename lookup under
    <data_root>/data.
    """
    for cand in (os.path.join(data_root, instance), instance):
        if os.path.isfile(cand):
            return os.path.normpath(cand)
    name = os.path.basename(instance)
    hits = glob.glob(os.path.join(data_root, "data", "**", name), recursive=True)
    return os.path.normpath(hits[0]) if len(hits) == 1 else None


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="src.bench.make_tier2_manifest",
        description="Build the tier-2 memetic SLURM manifest from the RC2 hardness profiles.",
    )
    p.add_argument("--hardness-dir", default="results/hardness")
    p.add_argument("--data-root", default="cluster_staging_maxsat",
                   help="Tree the instance paths are relative to on the cluster")
    p.add_argument("--out-dir", default="cluster_staging_maxsat/scripts")
    p.add_argument("--tiers", nargs="+", default=["T2a", "T2b"])
    p.add_argument("--no-solved-t3", dest="include_solved_t3", action="store_false",
                   help="Exclude completed-but-T3 records (see RC2_STATUS §4.6)")
    p.add_argument("--configs", nargs="+", default=DEFAULT_CONFIGS)
    p.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    p.add_argument("--budgets", type=float, nargs="+", default=DEFAULT_BUDGETS)
    p.add_argument("--prefix", default="t2m", help="job_id prefix")
    p.set_defaults(include_solved_t3=True)
    args = p.parse_args(argv)

    os.makedirs(args.out_dir, exist_ok=True)

    records = dedupe(select_records(args.hardness_dir, args.tiers, args.include_solved_t3))
    if not records:
        raise SystemExit(f"No tier-2 records found under {args.hardness_dir}")

    kept: List[Dict[str, Any]] = []
    skipped: List[str] = []
    for r in records:
        path = resolve(r["instance"], args.data_root)
        if path is None:
            skipped.append(f"{r['instance']}\tunresolved (not under {args.data_root})")
            continue
        fmt = detect_format(path)
        if fmt == "wcnf_new":
            skipped.append(f"{r['instance']}\tnew-format WCNF, sat.cnf cannot parse it")
            continue
        if fmt == "unknown":
            skipped.append(f"{r['instance']}\tunrecognised DIMACS format")
            continue
        if r["oracle_disagreement"]:
            skipped.append(f"{r['instance']}\tRC2 runs disagree on the optimum")
            continue
        r["resolved"] = os.path.relpath(path, args.data_root)
        r["format"] = fmt
        r["sha256"] = sha256_file(path)
        kept.append(r)

    # ---- manifest: one line per (instance, config, seed, budget) --------------
    man_path = os.path.join(args.out_dir, "manifest_tier2_memetic.tsv")
    n = 0
    with open(man_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        for r in kept:
            for cfg in args.configs:
                cfg_id = os.path.splitext(os.path.basename(cfg))[0]
                for budget in args.budgets:
                    for seed in args.seeds:
                        n += 1
                        w.writerow([
                            f"{args.prefix}_{n:05d}",
                            r["resolved"], cfg, cfg_id,
                            seed, f"{budget:g}",
                            r["oracle_cost"], r["tier"], r["rc2_run"],
                        ])

    # ---- oracle table: one line per instance ---------------------------------
    oracle_path = os.path.join(args.out_dir, "tier2_oracle.csv")
    with open(oracle_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "instance", "resolved", "sha256", "format", "tier", "oracle_cost",
            "rc2_solve_s", "rc2_cap_s", "rc2_run", "rc2_runs_all", "size_mb",
        ])
        w.writeheader()
        for r in kept:
            w.writerow({
                "instance": r["instance"], "resolved": r["resolved"],
                "sha256": r["sha256"], "format": r["format"], "tier": r["tier"],
                "oracle_cost": r["oracle_cost"], "rc2_solve_s": r["rc2_solve_s"],
                "rc2_cap_s": r["rc2_cap_s"], "rc2_run": r["rc2_run"],
                "rc2_runs_all": ";".join(r["rc2_runs_all"]), "size_mb": r["size_mb"],
            })

    skip_path = os.path.join(args.out_dir, "tier2_skipped.txt")
    with open(skip_path, "w", encoding="utf-8") as f:
        f.write("# instance\treason\n")
        for s in skipped:
            f.write(s + "\n")

    print(f"tier-2 candidates : {len(records)}")
    print(f"  usable          : {len(kept)}")
    print(f"  skipped         : {len(skipped)}  -> {skip_path}")
    print(f"jobs              : {n} "
          f"({len(kept)} inst x {len(args.configs)} cfg x {len(args.budgets)} budget "
          f"x {len(args.seeds)} seed)")
    print(f"solver-seconds    : {sum(args.budgets) * len(args.seeds) * len(args.configs) * len(kept):.0f}")
    print(f"manifest          : {man_path}")
    print(f"oracle            : {oracle_path}")
    print(f"\nsubmit with:  sbatch --array=1-{n}%30 scripts/tier2_memetic_array.sbatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
