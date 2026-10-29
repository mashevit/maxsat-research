#!/usr/bin/env python3
"""Batch 3c: the memetic on the 952 MSE 2026 instances with a published optimum,
3 seeds, 1,800 s, stop at the optimum (docs/current2/MSE26_3C_RUN.md, repo).

Workstation only (the login node runs no Python). Reads
scripts/mse26_membins.tsv (instances, sha256, memory bins; COMPILED_MEMETIC_PLAN.md
§15) and the published MSE 2026 metadata (optimal_cost), and writes, from the
tree root, one manifest per array part (one `sbatch --mem` per memory bin; the
8 GB bin in 3 parts of <= 1,000 tasks):

  scripts/manifest_mse26_<part>.tsv / .tasks.csv / .sha256     part in 8a 8b 8c 16 32 64
  scripts/manifest_mse26.upload.sha256, scripts/rsync_files_mse26.txt

    python3 scripts/make_mse26_manifest.py            # write
    python3 scripts/make_mse26_manifest.py --check    # regenerate in memory, compare

Every task: configs/strong/auto.yaml (auto_hparams/3, kernel gate on for all,
user 2026-10-29), budget 1,800 s on the process CPU clock (`--budget-clock
process`, MSE26_RHO_PLAN.md §9), GRACE 300 s, stop at the published optimum.
The `.sha256` files are for the readout (each record carries the sha256 it
read); the login node does not hash the 80 GiB.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import make_under30_manifest as u3  # noqa: E402  (sidecar_csv, write_upload, check_or_write)

STAGE = "mse26"
STEM = "manifest_mse26"
BINS = os.path.join(ROOT, "scripts", "mse26_membins.tsv")
CENSUS = os.path.join(ROOT, "results", "mse26_census", "mse26_census.tsv")   # exact byte sizes
META = os.path.join(REPO, "data", "raw", "mse_results", "mse26", "benchmark-metadata.csv")
CONFIG = "configs/strong/auto.yaml"
CONFIG_ID = "auto"
SEEDS = (1, 2, 3)
BUDGET = 1800
GRACE = 300
PART_MAX = 1000
# auto.yaml as submitted (the record's `config`; auto_hparams changes it in memory only)
FIXED = {"pop_size": 40, "ls_time_limit_s": 3.5, "deadline_mode": "clip", "memetic_impl": "v3",
         "ls_polish_flips": 12500, "ls_polish_cap": "flips", "preprocess": "kernel", "ls_native": "1"}
SIDECAR = ["task_id", "job_id", "stage", "part", "pop_idx", "bin_gb", "config_id", "config", "solver_seed", "budget_s",
           "grace_s", "budget_clock", "set", "hash", "family", "instance", "instance_sha256", "bytes", "type",
           "kernel_status", "oracle_cost", "oracle_kind"] + list(FIXED)


def instances():
    with open(META, newline="", encoding="utf-8") as f:
        meta = {r["hash"]: r for r in csv.DictReader(f)}
    with open(CENSUS, newline="", encoding="utf-8") as f:
        size = {r["hash"]: int(r["bytes"]) for r in csv.DictReader(f, delimiter="\t")}
    out = []
    with open(BINS, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            m = meta[r["hash"]]
            try:
                opt = int(m["optimal_cost"])
            except ValueError:
                raise SystemExit(f"FATAL: {r['hash']} has no published optimum ({m['optimal_cost']!r})")
            if "," in m["family"]:
                raise SystemExit(f"FATAL: family {m['family']!r} has a comma (submit_mse26.sh splits on commas)")
            out.append(dict(r, family=m["family"], oracle_cost=opt, bytes=size[r["hash"]]))
    if len(out) != 952 or len({r["hash"] for r in out}) != 952:
        raise SystemExit(f"FATAL: expected 952 distinct instances, got {len(out)}")
    for i, r in enumerate(sorted(out, key=lambda r: (r["set"], r["hash"])), 1):
        r["pop_idx"] = f"m{i:03d}"              # one id per instance, across the parts
    return out


def parts(insts):
    """{part: [instance rows]}: one part per bin, the 8 GB bin cut into equal parts of <= PART_MAX tasks."""
    by_bin = {}
    for r in sorted(insts, key=lambda r: (int(r["bin_gb"]), r["set"], r["hash"])):
        by_bin.setdefault(int(r["bin_gb"]), []).append(r)
    out = {}
    for g, rows in by_bin.items():
        k = -(-len(rows) * len(SEEDS) // PART_MAX)          # parts needed
        size = -(-len(rows) // k)
        for i in range(k):
            out[f"{g}{'abcdefgh'[i] if k > 1 else ''}"] = rows[i * size:(i + 1) * size]
    return out


def build(insts):
    files = {}
    for part, rows in parts(insts).items():
        tasks, lines = [], []
        for r in rows:
            for seed in SEEDS:
                job = f"m26_{r['hash']}_s{seed}"
                tasks.append({"task_id": len(tasks) + 1, "job_id": job, "stage": STAGE, "part": part,
                              "pop_idx": r["pop_idx"],
                              "bin_gb": r["bin_gb"], "config_id": CONFIG_ID, "config": CONFIG, "solver_seed": seed,
                              "budget_s": BUDGET, "grace_s": GRACE, "budget_clock": "process", "set": r["set"],
                              "hash": r["hash"], "family": r["family"], "instance": r["path"],
                              "instance_sha256": r["sha256"], "bytes": r["bytes"], "type": r["type"],
                              "kernel_status": r["kernel_status"], "oracle_cost": r["oracle_cost"],
                              "oracle_kind": "published_optimum", **FIXED})
                lines.append("\t".join([job, r["path"], CONFIG, CONFIG_ID, str(seed), str(BUDGET),
                                        str(r["oracle_cost"]), "mse26_optimum", "mse26_published"]) + "\n")
        files[f"scripts/{STEM}_{part}.tsv"] = "".join(lines)
        files[f"scripts/{STEM}_{part}.tasks.csv"] = u3.sidecar_csv(SIDECAR, tasks)
        files[f"scripts/{STEM}_{part}.sha256"] = "".join(f"{r['sha256']}  {r['path']}\n" for r in rows)
    return files


def upload_paths(files):
    src = sorted(os.path.relpath(os.path.join(d, f), ROOT) for d, _, fs in os.walk(os.path.join(ROOT, "src"))
                 if "__pycache__" not in d for f in fs if f.endswith(".py"))
    src += ["src/native/ls_core.c"]
    scripts = ["scripts/mse26_memetic_array.sbatch", "scripts/submit_mse26.sh", "scripts/m2_results.py",
               "scripts/build_native.sh", "scripts/build_native.sbatch", "scripts/auto_hparams.py",
               "scripts/make_under30_manifest.py", "scripts/make_mse26_manifest.py", "scripts/mse26_membins.py",
               "scripts/mse26_membins.tsv", "scripts/make_flat_upload.py"] + sorted(files)
    return src, [CONFIG], scripts


def file_list_text(groups, n_tasks):
    src, cfgs, scripts = groups
    out = [f"# File list for batch 3c, MSE 2026 memetic ({n_tasks} tasks; docs/current2/MSE26_3C_RUN.md, repo).",
           "# Paths relative to cluster_staging_maxsat_strong/. Destination: ~/cluster_staging_maxsat_strong/.",
           f"# After the upload: sha256sum -c scripts/{STEM}.upload.sha256 on the login node.",
           "# The instances are NOT in this list: they are on the cluster (data/raw/mse26 -> ~/mse_full26/wcnf).",
           "#", "# 1. code (src/, C core source unchanged since 9ce84ca: no rebuild needed)"]
    out += src + ["# 2. config"] + cfgs + ["# 3. driver, submit, results, builders, manifests"] + scripts
    out += [f"scripts/{STEM}.upload.sha256", f"scripts/rsync_files_{STAGE}.txt"]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="regenerate the manifest files in memory and compare")
    a = ap.parse_args(argv)
    insts = instances()
    files = build(insts)
    if a.check:
        return u3.check_or_write(files, True)
    u3.check_or_write(files, False)
    n = sum(t.count("\n") for p, t in files.items() if p.endswith(".tsv"))
    groups = upload_paths([p for p in files])
    k = u3.write_upload(STEM, STAGE, groups, file_list_text(groups, n))
    for p in sorted(f for f in files if f.endswith(".tsv")):
        print(f"  {p}: {files[p].count(chr(10))} tasks")
    print(f"wrote {len(files)} manifest files + upload list; {len(insts)} instances; {n} tasks; {k} upload hashes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
