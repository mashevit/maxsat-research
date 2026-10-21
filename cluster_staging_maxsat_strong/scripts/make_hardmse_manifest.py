#!/usr/bin/env python3
"""Batch HMSE: the strong solver (configs/strong/auto.yaml, `hparams: auto` = rule set
auto_hparams/2, so pop 10 and keep_sat ks2) on every MSE 2023/2024 instance with
hard clauses and a best-known cost.

docs/current2/UNDER30_HARDMSE_RUN.md (repo). Workstation only (the login node
runs no Python). Two steps, as make_oracle900_manifest.py:

  1. --select   list data/raw/mse_2024/{mse23-uw-small,mse24-small} in
                ../cluster_staging_maxsat, keep the files with hard clauses and
                a best-known (each file's OWN year's table, never by name across
                years: MSE_EVALMAXSAT_3600.md section 3), copy them into this
                tree's data/ (same relative paths), write scripts/instances_hardmse.csv.
  2. (default)  from that CSV write the manifest, sidecar, instance hashes,
                upload hashes and file list; --check regenerates in memory.

Target (user, 2026-10-21: "write manifest for the hard clauses"): the year's
best-known cost. It is a proven optimum where EvalMaxSAT s1 (3600 s) or RC2
certified it (`oracle_kind` proven), else a best-known (MSE 2024 values are
anytime-track bests, not optima). A run stops when it reaches the target, so a
run under a best-known also stops; the record keeps its cost.
Excluded: the 5 files with best-known -1 (no hard-feasible assignment known),
the soft-only files (no hard clauses; drmx-cryptogen ran in O900), and the 3
setcover rail files (TOO_DENSE): their hard clauses have 7,753-8,919 variables,
so the v3 neighbour lists (src/sat/ls_v3.py _V3Static, ~k^2 per clause) need
0.6-1.1 billion entries; measured 7.3 GB at 34-38 s, still building, MemoryError
(user, 2026-10-21: "drop the 3 rail instances"). The next densest instance has
37M entries and ran under a 2 GB cap.
3 seeds x 900 s, stop at the target, kernel on, impl v3 with hparams: auto.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import make_oracle900_manifest as o9  # noqa: E402
import make_under30_manifest as u3  # noqa: E402  (sidecar_csv, write_upload, check_or_write)
from sat.cnf import WCNF  # noqa: E402

STEM = "manifest_hardmse"
STAGE = "hardmse"
INSTANCES_CSV = "scripts/instances_hardmse.csv"
MSE = "data/raw/mse_2024"
YEARS = {"mse23": ("mse23-uw-small", "bestknown_mse23.csv"), "mse24": ("mse24-small", "bestknown_mse24.csv")}
INST_COLS = ["pop_idx", "instance", "instance_sha256", "year", "family", "oracle_cost", "oracle_kind",
             "proof", "evalmaxsat_s", "evalmaxsat_status", "evalmaxsat_ub", "rc2_solve_s", "n_vars", "n_hard",
             "n_soft", "weighted"]
SIDECAR = ["task_id", "job_id", "stage", "config_id", "config", "pop_size", "ls_time_limit_s", "deadline_mode",
           "solver_seed", "budget_s", "pop_idx", "instance", "instance_sha256", "year", "family", "oracle_cost",
           "oracle_kind", "proof", "evalmaxsat_s", "n_hard", "weighted", "memetic_impl", "ls_polish_flips",
           "ls_polish_cap", "preprocess", "ls_native"]


# Family names that themselves contain the separator '-' (copied from
# ../cluster_staging_maxsat/scripts/make_evalmaxsat_mse_manifest.py, so the families match batch s1).
MULTIWORD = ("judgment-aggregation", "inconsistency-measurement", "decision-tree", "gen-hyper-tw",
             "optimizing-BDDs", "logic-synthesis", "extension-enforcement", "min-fill",
             "quantum-circuit")


# Files left out because the v3 static tables do not fit in memory (see the docstring).
TOO_DENSE = ("setcover_wt-rail507.wcnf", "setcover_wt-rail516.wcnf", "setcover_wt-rail582.wcnf")


def family(name: str) -> str:
    if "_wt-" in name:
        fam = name.split("_wt-")[0]
    else:
        fam = next((m for m in MULTIWORD if name.startswith(m + "-") or name.startswith(m + "_")),
                   name.split("-")[0])
    for suffix in ("_mse20", "_new"):
        if fam.endswith(suffix):
            fam = fam[: -len(suffix)]
    return fam


def select(staging: str):
    rc2 = o9.rc2_rows(staging)
    ev = {}
    for line in open(os.path.join(staging, "results", "evalmaxsat_mse_s1_all.jsonl"), encoding="utf-8"):
        r = json.loads(line)
        ev[r["instance"]] = r["row"]
    rows, skipped = [], {"no_hard": [], "no_bestknown": [], "too_dense": []}
    for year, (sub, table) in YEARS.items():
        with open(os.path.join(staging, MSE, table), encoding="utf-8") as f:
            best = {r["instance"]: int(r["best_cost"]) for r in csv.DictReader(f)}
        for fname in sorted(os.listdir(os.path.join(staging, MSE, sub))):
            inst = f"{MSE}/{sub}/{fname}"
            if fname in TOO_DENSE:
                skipped["too_dense"].append(inst)
                continue
            w = WCNF.parse_dimacs(os.path.join(staging, inst))
            n_hard = sum(1 for c in w.clauses if c.is_hard)
            if n_hard == 0:
                skipped["no_hard"].append(inst)
                continue
            bk = best[fname]                         # KeyError = a file without a row: stop
            if bk < 0:
                skipped["no_bestknown"].append(inst)
                continue
            soft = [c for c in w.clauses if not c.is_hard]
            proofs, e = [], ev.get(inst)
            if e and e["status"] == "optimal" and e.get("verified"):
                proofs.append(("evalmaxsat", int(e["opt_cost"])))
            runs = rc2.get(inst, [])
            if runs:
                proofs.append(("rc2", runs[0][1]))
            for name, cost in proofs:
                if cost != bk:
                    raise SystemExit(f"FATAL: {name} optimum {cost} != best-known {bk}: {inst}")
            ub = int(e["best_cost"]) if e and e.get("verified") and e.get("best_cost") is not None else None
            if ub is not None and ub < bk:
                raise SystemExit(f"FATAL: EvalMaxSAT found {ub} < best-known {bk}: {inst}")
            rows.append({
                "instance": inst, "instance_sha256": o9.sha256(os.path.join(staging, inst)), "year": year,
                "family": family(fname), "oracle_cost": bk,
                "oracle_kind": "proven" if proofs else "best_known",
                "proof": "+".join(n for n, _ in proofs),
                "evalmaxsat_s": round(float(e["time_s"]), 3) if e and e["status"] == "optimal" else "",
                "evalmaxsat_status": e["status"] if e else "",
                "evalmaxsat_ub": ub if ub is not None else "",
                "rc2_solve_s": runs[0][0] if runs else "",
                "n_vars": w.n_vars, "n_hard": n_hard, "n_soft": len(soft),
                "weighted": int(any(c.weight != 1 for c in soft)),
            })
    for i, r in enumerate(rows, 1):
        r["pop_idx"] = f"h{i:03d}"
    return rows, skipped


def do_select(staging: str) -> int:
    rows, skipped = select(staging)
    for r in rows:
        src, dst = os.path.join(staging, r["instance"]), os.path.join(ROOT, r["instance"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.isfile(dst) or o9.sha256(dst) != r["instance_sha256"]:
            shutil.copy2(src, dst)
        if o9.sha256(dst) != r["instance_sha256"]:
            print(f"FATAL: copy of {r['instance']} does not match", file=sys.stderr)
            return 1
    with open(os.path.join(ROOT, INSTANCES_CSV), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=INST_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    kinds = {}
    for r in rows:
        k = (r["year"], r["oracle_kind"])
        kinds[k] = kinds.get(k, 0) + 1
    print(f"{len(rows)} instances -> {INSTANCES_CSV}; {kinds}; skipped no_hard {len(skipped['no_hard'])}, "
          f"no_bestknown {len(skipped['no_bestknown'])}, too_dense {len(skipped['too_dense'])}")
    return 0


def build():
    with open(os.path.join(ROOT, INSTANCES_CSV), encoding="utf-8") as f:
        insts = list(csv.DictReader(f))
    files, rows, lines = {}, [], []
    for inst in insts:
        tier = "evalmaxsat" if "evalmaxsat" in inst["proof"] else ("rc2" if inst["proof"] else "bestknown")
        run = f"bestknown_{inst['year']}" if tier == "bestknown" else (
            "evalmaxsat_mse_s1" if tier == "evalmaxsat" else "rc2_profile")
        for seed in o9.SEEDS:
            job = f"hm_{inst['pop_idx']}_s{seed}"
            rows.append({
                "task_id": len(rows) + 1, "job_id": job, "stage": STAGE, "config_id": o9.CONFIG_ID,
                "config": o9.CONFIG, "pop_size": 40, "ls_time_limit_s": 3.5, "deadline_mode": "clip",
                "solver_seed": seed, "budget_s": o9.BUDGET, "pop_idx": inst["pop_idx"],
                "instance": inst["instance"], "instance_sha256": inst["instance_sha256"], "year": inst["year"],
                "family": inst["family"], "oracle_cost": inst["oracle_cost"], "oracle_kind": inst["oracle_kind"],
                "proof": inst["proof"], "evalmaxsat_s": inst["evalmaxsat_s"], "n_hard": inst["n_hard"],
                "weighted": inst["weighted"], "memetic_impl": "v3", "ls_polish_flips": 12500,
                "ls_polish_cap": "flips", "preprocess": "kernel", "ls_native": "1",
            })
            lines.append("\t".join([job, inst["instance"], o9.CONFIG, o9.CONFIG_ID, str(seed), str(o9.BUDGET),
                                    inst["oracle_cost"], tier, run]) + "\n")
    files[f"scripts/{STEM}.tsv"] = "".join(lines)
    files[f"scripts/{STEM}.tasks.csv"] = u3.sidecar_csv(SIDECAR, rows)
    files[f"scripts/{STEM}.sha256"] = "".join(f"{i['instance_sha256']}  {i['instance']}\n" for i in insts)
    return files, insts


def upload_paths(insts):
    src, cfgs, scripts, _ = o9.upload_paths([])
    scripts = [p for p in scripts if "oracle900" not in p] + [
        "scripts/make_oracle900_manifest.py", "scripts/make_under30_manifest.py", "scripts/make_hardmse_manifest.py",
        INSTANCES_CSV, f"scripts/{STEM}.tsv", f"scripts/{STEM}.tasks.csv", f"scripts/{STEM}.sha256"]
    return src, cfgs, scripts, [i["instance"] for i in insts]


def file_list_text(groups, n_tasks):
    src, cfgs, scripts, data = groups
    out = [f"# File list for batch HMSE ({n_tasks} tasks; docs/current2/UNDER30_HARDMSE_RUN.md, repo).",
           "# Paths relative to cluster_staging_maxsat_strong/. Destination: ~/cluster_staging_maxsat_strong/.",
           f"# After the upload: sha256sum -c scripts/{STEM}.upload.sha256 on the login node.",
           "#", "# 1. code (src/, including the C core source; the .so is already built on the cluster)"]
    out += src + ["# 2. the one config (hparams: auto)"] + cfgs
    out += ["# 3. driver, submit, build, results, manifest"] + scripts
    out += [f"scripts/{STEM}.upload.sha256", f"scripts/rsync_files_{STAGE}.txt"]
    out += [f"# 4. instances ({len(data)})"] + data
    return "\n".join(out) + "\n"


def do_manifest(check: bool) -> int:
    files, insts = build()
    if check:
        return u3.check_or_write(files, True)
    for i in insts:
        if o9.sha256(os.path.join(ROOT, i["instance"])) != i["instance_sha256"]:
            print(f"FATAL: {i['instance']} does not match its recorded sha256 (run --select)", file=sys.stderr)
            return 1
    u3.check_or_write(files, False)
    n = files[f"scripts/{STEM}.tsv"].count("\n")
    groups = upload_paths(insts)
    k = u3.write_upload(STEM, STAGE, groups, file_list_text(groups, n))
    print(f"wrote {len(files)} files + upload list; {len(insts)} instances; {n} tasks; {k} upload hashes")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", action="store_true", help="choose the instances (step 1)")
    ap.add_argument("--staging", default=o9.STAGING, help="tree holding the MSE files, tables and results")
    ap.add_argument("--check", action="store_true", help="regenerate the manifest files in memory and compare")
    a = ap.parse_args(argv)
    if a.select:
        return do_select(a.staging)
    return do_manifest(a.check)


if __name__ == "__main__":
    sys.exit(main())
