#!/usr/bin/env python3
"""Batch O900: the strong solver (configs/strong/auto.yaml, `hparams: auto`) on every
instance with a proven optimum within 900 s, from RC2 or EvalMaxSAT.

docs/current2/ORACLE900_RUN.md (repo). Workstation only (the login node runs
no Python). Two steps:

  1. --select   read the RC2 profile rows and the EvalMaxSAT s1 rows in
                ../cluster_staging_maxsat/results, apply the selection below,
                copy the chosen instances into this tree's data/ (same relative
                paths), and write scripts/instances_oracle900.csv.
  2. (default)  from that CSV write the manifest, sidecar, instance hashes,
                upload hashes and rsync list; --check regenerates in memory.

Selection (user, 2026-10-21: "instances rc2 is above 30s, ... manifest for
instances we have oracle in 900s, from rc2 or evalmaxsat"):
  * RC2: certified (completed and final_cost == cost_lower_bound) with the
    fastest certified run in [30 s, 900 s). Every certified RC2 run of the
    instance must agree on the cost.
  * EvalMaxSAT (MSE s1, 3600 s cap): `optimal` and verified with time_s < 900,
    unless RC2 certified the instance in < 30 s. Where both proved an optimum
    they must agree.
  * Rules apply per FORMULA, not per file: copies are found on the parsed
    clauses (weights and sorted literals), so a normalised SATLIB file and its
    raw original are one instance, and RC2's fastest run on any copy decides
    the 30 s screen. The data/satlib_bench copy is the one run (normalised,
    the one cited), else the lexicographically first path.
3 seeds x 900 s, stop at the oracle, kernel on, impl v3 with hparams: auto.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from sat.cnf import WCNF  # noqa: E402
STAGING = os.path.join(os.path.dirname(ROOT), "cluster_staging_maxsat")
STEM = "manifest_oracle900"
STAGE = "oracle900"
INSTANCES_CSV = "scripts/instances_oracle900.csv"
CONFIG = "configs/strong/auto.yaml"
CONFIG_ID = "strong_auto"
SEEDS = (1, 2, 3)
BUDGET = 900
RC2_MIN_S, CAP_S = 30.0, 900.0

INST_COLS = ["pop_idx", "instance", "instance_sha256", "source", "oracle_cost", "rc2_solve_s",
             "evalmaxsat_s", "rc2_tier", "rc2_run", "family", "aliases"]
SIDECAR = ["task_id", "job_id", "stage", "config_id", "config", "pop_size", "ls_time_limit_s", "deadline_mode",
           "solver_seed", "budget_s", "pop_idx", "instance", "instance_sha256", "source", "family",
           "oracle_cost", "rc2_solve_s", "evalmaxsat_s", "rc2_tier", "memetic_impl", "ls_polish_flips",
           "ls_polish_cap", "preprocess", "ls_native"]


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def formula_key(path: str) -> str:
    """Hash of the parsed formula: n, and the sorted (weight or H, sorted literals) clauses."""
    w = WCNF.parse_dimacs(path)
    canon = sorted((("H" if c.is_hard else str(c.weight)), tuple(sorted(c.lits))) for c in w.clauses)
    return hashlib.sha256(repr((w.n_vars, canon)).encode()).hexdigest()


def family(inst: str) -> str:
    parts = inst.split("/")
    if parts[:2] == ["data", "generated"] or parts[:2] == ["data", "satlib_bench"]:
        return parts[2]
    if parts[:3] == ["data", "raw", "mse_2024"]:
        return parts[3]
    return parts[1]


# ------------------------------------------------------------------ step 1: select

def rc2_rows(staging: str):
    """{instance: [(solve_s, cost, tier, run), ...]} over every certified RC2 profile row."""
    out = {}
    files = glob.glob(os.path.join(staging, "results", "profile*", "**", "*.jsonl"), recursive=True)
    files += glob.glob(os.path.join(staging, "results", "profile*_all.jsonl"))
    for f in sorted(set(files)):
        if f.endswith("_env.jsonl"):
            continue
        run = os.path.relpath(f, os.path.join(staging, "results")).split(os.sep)[0]
        for line in open(f, encoding="utf-8"):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            p = r.get("profile") or {}
            if p.get("solver") != "rc2" or not r.get("instance"):
                continue
            if p.get("completed") and p.get("final_cost") is not None and p["final_cost"] == p.get("cost_lower_bound"):
                out.setdefault(r["instance"], set()).add(
                    (float(p["solve_s"]), int(p["final_cost"]), r.get("tier") or "", run.replace("_all.jsonl", "")))
    return {k: sorted(v) for k, v in out.items()}


def evalmaxsat_rows(staging: str):
    out = {}
    for line in open(os.path.join(staging, "results", "evalmaxsat_mse_s1_all.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        row = r["row"]
        if row["status"] == "optimal" and row.get("verified") and float(row["time_s"]) < CAP_S:
            out[r["instance"]] = (float(row["time_s"]), int(row["opt_cost"]))
    return out


def select(staging: str):
    """Group every RC2 / EvalMaxSAT result by formula, then apply the rules per formula."""
    rc2, ev = rc2_rows(staging), evalmaxsat_rows(staging)
    paths = sorted(p for p in set(rc2) | set(ev) if os.path.isfile(os.path.join(staging, p)))
    groups = {}
    for p in paths:
        groups.setdefault(formula_key(os.path.join(staging, p)), []).append(p)
    rows = []
    for key, ps in groups.items():
        ps.sort(key=lambda p: (not p.startswith("data/satlib_bench/"), p))
        runs = sorted(r for p in ps for r in rc2.get(p, []))
        evs = sorted(ev[p] for p in ps if p in ev)
        costs = {c for _, c, _, _ in runs} | {c for _, c in evs}
        if len(costs) > 1:
            raise SystemExit(f"FATAL: proven optima disagree on {ps}: {sorted(costs)}")
        rc2_t = runs[0][0] if runs else None
        if rc2_t is not None and rc2_t < RC2_MIN_S:
            continue                                   # RC2 needs under 30 s on some copy
        rc2_ok = rc2_t is not None and rc2_t < CAP_S
        if not (rc2_ok or evs):
            continue                                   # no optimum within 900 s
        source = "rc2+evalmaxsat" if (rc2_ok and evs) else ("rc2" if rc2_ok else "evalmaxsat")
        inst = ps[0]
        rows.append({"instance": inst, "instance_sha256": sha256(os.path.join(staging, inst)),
                     "source": source, "oracle_cost": costs.pop(),
                     "rc2_solve_s": rc2_t if rc2_t is not None else "",
                     "evalmaxsat_s": round(evs[0][0], 3) if evs else "",
                     "rc2_tier": runs[0][2] if rc2_ok else "evalmaxsat",
                     "rc2_run": runs[0][3] if rc2_ok else "evalmaxsat_mse_s1",
                     "family": family(inst), "aliases": len(ps) - 1})
    rows.sort(key=lambda r: (r["family"], r["instance"]))
    for i, r in enumerate(rows, 1):
        r["pop_idx"] = f"o{i:03d}"
    return rows


def do_select(staging: str) -> int:
    rows = select(staging)
    for r in rows:
        src, dst = os.path.join(staging, r["instance"]), os.path.join(ROOT, r["instance"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.isfile(dst) or sha256(dst) != r["instance_sha256"]:
            shutil.copy2(src, dst)
        if sha256(dst) != r["instance_sha256"]:
            print(f"FATAL: copy of {r['instance']} does not match", file=sys.stderr)
            return 1
    with open(os.path.join(ROOT, INSTANCES_CSV), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INST_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    fam = {}
    for r in rows:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
    src = {}
    for r in rows:
        src[r["source"]] = src.get(r["source"], 0) + 1
    print(f"{len(rows)} instances -> {INSTANCES_CSV}; sources {src}; families {fam}")
    return 0


# ------------------------------------------------------------------ step 2: manifest

def instances():
    with open(os.path.join(ROOT, INSTANCES_CSV), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build():
    files, rows, lines = {}, [], []
    insts = instances()
    for inst in insts:
        for seed in SEEDS:
            job = f"oa_{inst['pop_idx']}_s{seed}"
            rows.append({
                "task_id": len(rows) + 1, "job_id": job, "stage": STAGE, "config_id": CONFIG_ID, "config": CONFIG,
                "pop_size": 40, "ls_time_limit_s": 3.5, "deadline_mode": "clip", "solver_seed": seed,
                "budget_s": BUDGET, "pop_idx": inst["pop_idx"], "instance": inst["instance"],
                "instance_sha256": inst["instance_sha256"], "source": inst["source"], "family": inst["family"],
                "oracle_cost": inst["oracle_cost"], "rc2_solve_s": inst["rc2_solve_s"],
                "evalmaxsat_s": inst["evalmaxsat_s"], "rc2_tier": inst["rc2_tier"], "memetic_impl": "v3",
                "ls_polish_flips": 12500, "ls_polish_cap": "flips", "preprocess": "kernel", "ls_native": "1",
            })
            lines.append("\t".join([job, inst["instance"], CONFIG, CONFIG_ID, str(seed), str(BUDGET),
                                    inst["oracle_cost"], inst["rc2_tier"], inst["rc2_run"]]) + "\n")
    files[f"scripts/{STEM}.tsv"] = "".join(lines)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=SIDECAR, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    files[f"scripts/{STEM}.tasks.csv"] = buf.getvalue()
    files[f"scripts/{STEM}.sha256"] = "".join(f"{i['instance_sha256']}  {i['instance']}\n" for i in insts)
    return files, insts


def upload_paths(insts):
    src = sorted(p for p in glob.glob("src/**/*.py", root_dir=ROOT, recursive=True) if "__pycache__" not in p)
    src += ["src/native/ls_core.c"]
    scripts = ["scripts/tier2_memetic_array.sbatch", "scripts/submit_m2_memetic.sh", "scripts/build_native.sh",
               "scripts/build_native.sbatch", "scripts/m2_results.py", "scripts/auto_hparams.py",
               "scripts/make_oracle900_manifest.py", INSTANCES_CSV, f"scripts/{STEM}.tsv",
               f"scripts/{STEM}.tasks.csv", f"scripts/{STEM}.sha256"]
    return src, [CONFIG], scripts, [i["instance"] for i in insts]


def rsync_text(groups, n_tasks):
    src, cfgs, scripts, data = groups
    out = [f"# rsync --files-from list for batch O900 ({n_tasks} tasks; docs/current2/ORACLE900_RUN.md, repo).",
           "# Paths relative to cluster_staging_maxsat_strong/. Destination: ~/cluster_staging_maxsat_strong/.",
           f"# After the rsync: sha256sum -c scripts/{STEM}.upload.sha256 on the login node.",
           "#", "# 1. code (src/, including the C core source; build it once with scripts/build_native.sbatch)"]
    out += src
    out += ["# 2. the one config (hparams: auto)"] + cfgs
    out += ["# 3. driver, submit, build, results, manifest"] + scripts
    out += [f"scripts/{STEM}.upload.sha256", f"scripts/rsync_files_{STAGE}.txt"]
    out += [f"# 4. instances ({len(data)})"] + data
    return "\n".join(out) + "\n"


def do_manifest(check: bool) -> int:
    files, insts = build()
    if check:
        bad = [p for p, txt in files.items()
               if not os.path.isfile(os.path.join(ROOT, p)) or open(os.path.join(ROOT, p), encoding="utf-8").read() != txt]
        if bad:
            print("DIFFERS:", *bad, sep="\n  ")
            return 1
        print(f"OK: {len(files)} files reproduce byte for byte")
        return 0
    for i in insts:
        if sha256(os.path.join(ROOT, i["instance"])) != i["instance_sha256"]:
            print(f"FATAL: {i['instance']} does not match its recorded sha256 (run --select)", file=sys.stderr)
            return 1
    for p, txt in files.items():
        with open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    n = files[f"scripts/{STEM}.tsv"].count("\n")
    groups = upload_paths(insts)
    rsync = f"scripts/rsync_files_{STAGE}.txt"
    with open(os.path.join(ROOT, rsync), "w", encoding="utf-8") as f:
        f.write(rsync_text(groups, n))
    every = [p for g in groups for p in g] + [rsync]
    with open(os.path.join(ROOT, "scripts", f"{STEM}.upload.sha256"), "w", encoding="utf-8") as f:
        f.writelines(f"{sha256(os.path.join(ROOT, p))}  {p}\n" for p in every)
    print(f"wrote {len(files)} files + upload list; {n} tasks; {len(every)} upload hashes")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", action="store_true", help="choose the instances (step 1)")
    ap.add_argument("--staging", default=STAGING, help="tree holding the RC2 / EvalMaxSAT results and instances")
    ap.add_argument("--check", action="store_true", help="regenerate the manifest files in memory and compare")
    a = ap.parse_args(argv)
    if a.select:
        return do_select(a.staging)
    return do_manifest(a.check)


if __name__ == "__main__":
    sys.exit(main())
