#!/usr/bin/env python3
"""Batch U30: the strong solver (configs/strong/auto.yaml, `hparams: auto`) on every
instance whose optimum RC2 or EvalMaxSAT proved in under 30 s -- the instances
batch O900 left out.

docs/current2/UNDER30_HARDMSE_RUN.md (repo). Workstation only (the login node
runs no Python). Two steps, as make_oracle900_manifest.py:

  1. --select   read the RC2 profile rows and the EvalMaxSAT s1 rows in
                ../cluster_staging_maxsat/results, apply the selection below,
                copy the chosen instances into this tree's data/ (same relative
                paths), and write scripts/instances_under30.csv.
  2. (default)  from that CSV write the manifest, sidecar, instance hashes,
                upload hashes and file list; --check regenerates in memory.

Selection (user, 2026-10-21: "manifest for the not-run on memetic under 30s rc2
or EvalMaxSat"):
  * a proven optimum: RC2 certified (completed and final_cost ==
    cost_lower_bound) or EvalMaxSAT `optimal` and verified; every proof of the
    formula agrees on the cost;
  * the fastest proof, RC2 or EvalMaxSAT, is under 30 s;
  * optimum > 0 (a satisfiable formula is not a MaxSAT benchmark);
  * no hard clauses (those belong to batch HMSE, make_hardmse_manifest.py);
  * the formula is not in batch O900 (scripts/instances_oracle900.csv).
Rules apply per FORMULA (o9.formula_key), as in O900.
3 seeds x 900 s, stop at the oracle, kernel on, impl v3 with hparams: auto.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import make_oracle900_manifest as o9  # noqa: E402
from sat.cnf import WCNF  # noqa: E402

STEM = "manifest_under30"
STAGE = "under30"
INSTANCES_CSV = "scripts/instances_under30.csv"
MAX_S = 30.0
INST_COLS = o9.INST_COLS


def select(staging: str):
    rc2, ev = o9.rc2_rows(staging), o9.evalmaxsat_rows(staging)
    with open(os.path.join(ROOT, o9.INSTANCES_CSV), encoding="utf-8") as f:
        in_o900 = {r["instance"] for r in csv.DictReader(f)}
    paths = sorted(p for p in set(rc2) | set(ev) if os.path.isfile(os.path.join(staging, p)))
    groups = {}
    for p in paths:
        groups.setdefault(o9.formula_key(os.path.join(staging, p)), []).append(p)
    rows, skipped = [], {"o900": 0, "slow": 0, "zero": 0}
    for ps in groups.values():
        ps.sort(key=lambda p: (not p.startswith("data/satlib_bench/"), p))
        if any(p in in_o900 for p in ps):
            skipped["o900"] += 1
            continue
        runs = sorted(r for p in ps for r in rc2.get(p, []))
        evs = sorted(ev[p] for p in ps if p in ev)
        costs = {c for _, c, _, _ in runs} | {c for _, c in evs}
        if len(costs) > 1:
            raise SystemExit(f"FATAL: proven optima disagree on {ps}: {sorted(costs)}")
        rc2_t = runs[0][0] if runs else None
        ev_t = evs[0][0] if evs else None
        rc2_fast = rc2_t is not None and rc2_t < MAX_S
        ev_fast = ev_t is not None and ev_t < MAX_S
        if not (rc2_fast or ev_fast):
            skipped["slow"] += 1
            continue
        cost = costs.pop()
        if cost == 0:
            skipped["zero"] += 1
            continue
        inst = ps[0]
        if any(c.is_hard for c in WCNF.parse_dimacs(os.path.join(staging, inst)).clauses):
            raise SystemExit(f"FATAL: {inst} has hard clauses; it belongs to batch HMSE")
        source = "rc2+evalmaxsat" if (rc2_fast and ev_fast) else ("rc2" if rc2_fast else "evalmaxsat")
        rows.append({"instance": inst, "instance_sha256": o9.sha256(os.path.join(staging, inst)),
                     "source": source, "oracle_cost": cost,
                     "rc2_solve_s": rc2_t if rc2_t is not None else "",
                     "evalmaxsat_s": round(ev_t, 3) if ev_t is not None else "",
                     "rc2_tier": runs[0][2] if rc2_fast else "evalmaxsat",
                     "rc2_run": runs[0][3] if rc2_fast else "evalmaxsat_mse_s1",
                     "family": o9.family(inst), "aliases": len(ps) - 1})
    rows.sort(key=lambda r: (r["family"], r["instance"]))
    for i, r in enumerate(rows, 1):
        r["pop_idx"] = f"u{i:03d}"
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
    fam, src = {}, {}
    for r in rows:
        fam[r["family"]] = fam.get(r["family"], 0) + 1
        src[r["source"]] = src.get(r["source"], 0) + 1
    print(f"{len(rows)} instances -> {INSTANCES_CSV}; skipped formulas {skipped}; sources {src}; families {fam}")
    return 0


def build():
    with open(os.path.join(ROOT, INSTANCES_CSV), encoding="utf-8") as f:
        insts = list(csv.DictReader(f))
    files, rows, lines = {}, [], []
    for inst in insts:
        for seed in o9.SEEDS:
            job = f"u3_{inst['pop_idx']}_s{seed}"
            rows.append({
                "task_id": len(rows) + 1, "job_id": job, "stage": STAGE, "config_id": o9.CONFIG_ID,
                "config": o9.CONFIG, "pop_size": 40, "ls_time_limit_s": 3.5, "deadline_mode": "clip",
                "solver_seed": seed, "budget_s": o9.BUDGET, "pop_idx": inst["pop_idx"],
                "instance": inst["instance"], "instance_sha256": inst["instance_sha256"],
                "source": inst["source"], "family": inst["family"], "oracle_cost": inst["oracle_cost"],
                "rc2_solve_s": inst["rc2_solve_s"], "evalmaxsat_s": inst["evalmaxsat_s"],
                "rc2_tier": inst["rc2_tier"], "memetic_impl": "v3", "ls_polish_flips": 12500,
                "ls_polish_cap": "flips", "preprocess": "kernel", "ls_native": "1",
            })
            lines.append("\t".join([job, inst["instance"], o9.CONFIG, o9.CONFIG_ID, str(seed), str(o9.BUDGET),
                                    inst["oracle_cost"], inst["rc2_tier"], inst["rc2_run"]]) + "\n")
    files[f"scripts/{STEM}.tsv"] = "".join(lines)
    files[f"scripts/{STEM}.tasks.csv"] = sidecar_csv(o9.SIDECAR, rows)
    files[f"scripts/{STEM}.sha256"] = "".join(f"{i['instance_sha256']}  {i['instance']}\n" for i in insts)
    return files, insts


def sidecar_csv(cols, rows) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def upload_paths(insts):
    src, cfgs, scripts, _ = o9.upload_paths([])
    scripts = [p for p in scripts if "oracle900" not in p] + [
        "scripts/make_oracle900_manifest.py", o9.INSTANCES_CSV, "scripts/make_under30_manifest.py",
        INSTANCES_CSV, f"scripts/{STEM}.tsv", f"scripts/{STEM}.tasks.csv", f"scripts/{STEM}.sha256"]
    return src, cfgs, scripts, [i["instance"] for i in insts]


def file_list_text(groups, n_tasks):
    src, cfgs, scripts, data = groups
    out = [f"# File list for batch U30 ({n_tasks} tasks; docs/current2/UNDER30_HARDMSE_RUN.md, repo).",
           "# Paths relative to cluster_staging_maxsat_strong/. Destination: ~/cluster_staging_maxsat_strong/.",
           f"# After the upload: sha256sum -c scripts/{STEM}.upload.sha256 on the login node.",
           "#", "# 1. code (src/, including the C core source; the .so is already built on the cluster)"]
    out += src + ["# 2. the one config (hparams: auto)"] + cfgs
    out += ["# 3. driver, submit, build, results, manifest"] + scripts
    out += [f"scripts/{STEM}.upload.sha256", f"scripts/rsync_files_{STAGE}.txt"]
    out += [f"# 4. instances ({len(data)})"] + data
    return "\n".join(out) + "\n"


def write_upload(stem: str, stage: str, groups, text: str) -> int:
    """Write scripts/rsync_files_<stage>.txt and scripts/<stem>.upload.sha256; return the hash count."""
    lst = f"scripts/rsync_files_{stage}.txt"
    with open(os.path.join(ROOT, lst), "w", encoding="utf-8") as f:
        f.write(text)
    every = [p for g in groups for p in g] + [lst]
    with open(os.path.join(ROOT, "scripts", f"{stem}.upload.sha256"), "w", encoding="utf-8") as f:
        f.writelines(f"{o9.sha256(os.path.join(ROOT, p))}  {p}\n" for p in every)
    return len(every)


def check_or_write(files, check: bool) -> int:
    if check:
        bad = [p for p, txt in files.items()
               if not os.path.isfile(os.path.join(ROOT, p)) or open(os.path.join(ROOT, p), encoding="utf-8").read() != txt]
        if bad:
            print("DIFFERS:", *bad, sep="\n  ")
            return 1
        print(f"OK: {len(files)} files reproduce byte for byte")
        return 0
    for p, txt in files.items():
        with open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="") as f:
            f.write(txt)
    return 0


def do_manifest(check: bool) -> int:
    files, insts = build()
    if check:
        return check_or_write(files, True)
    for i in insts:
        if o9.sha256(os.path.join(ROOT, i["instance"])) != i["instance_sha256"]:
            print(f"FATAL: {i['instance']} does not match its recorded sha256 (run --select)", file=sys.stderr)
            return 1
    check_or_write(files, False)
    n = files[f"scripts/{STEM}.tsv"].count("\n")
    groups = upload_paths(insts)
    k = write_upload(STEM, STAGE, groups, file_list_text(groups, n))
    print(f"wrote {len(files)} files + upload list; {len(insts)} instances; {n} tasks; {k} upload hashes")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--select", action="store_true", help="choose the instances (step 1)")
    ap.add_argument("--staging", default=o9.STAGING, help="tree holding the RC2 / EvalMaxSAT results and instances")
    ap.add_argument("--check", action="store_true", help="regenerate the manifest files in memory and compare")
    a = ap.parse_args(argv)
    if a.select:
        return do_select(a.staging)
    return do_manifest(a.check)


if __name__ == "__main__":
    sys.exit(main())
