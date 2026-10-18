#!/usr/bin/env python3
"""Build the memetic-assessment manifest for the `promising` cells of calib_2sat_sc2.

Plan: docs/current/CALIB_2SAT_SC.md §6 (pre-registered follow-up) and §13b (repo).

SELECTION (§6, unchanged): the `eligible` instances of every `promising` cell,
read from the readout CSVs that scripts/calib_2sat_sc_readout.py writes
(results/<batch>/{instances,cells}.csv). The readout is re-run with --check first,
so stale CSVs stop the build. Instances of other cells are not run; this
script lists them with their class in the .not_run.csv sidecar.

ARMS (user decisions 2026-10-11), paired line by line on the same instances and
seeds:
  p40_ls3p5_v2       the pre-registered primary arm with `impl: v2`
                     (configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml)
  p40_ls3p5_f200k_v2 the same with the per-call flip limit 12,500 -> 200,000
                     (configs/tier2/memetic_deeppolish_p40_ls3p5_f200k_v2.yaml)
The build checks that each config equals memetic_deeppolish_p40_ls3p5.yaml key
for key except `impl: v2` and, for the second arm, ls.ls_polish_flips and
ls.flip_budget. Solver seeds 1-3, 900 s budget, stop at the RC2 optimum,
grace 60.

PLAN `cgrid` (--plan cgrid; HP-1 Stage L1, docs/current/HYPERPARAMETER_CALIBRATION_PLAN.md
§0b/§0c; user decisions 2026-10-14: flips_only, re-run all 90, include tcap): the same
instances and seeds, 6 arms paired line by line:
  p40_f{200k,400k,800k,1p6m,3p2m}_fonly_v2  per-call flip limit 200k ... 3.2M with
                     `ls.polish_cap: flips_only` (the flip limit alone ends a call)
  p40_ls3p5_tcap_v2  reference: `ls.polish_cap: time` (3.5 s per call, no flip limit)
Each config is checked equal to the pre-registered arm except `impl: v2`, the flip
limit and ls.polish_cap. The sidecar adds `ls_polish_cap`. 108 tasks.

PLAN `tgrid` (--plan tgrid; HP-1 Stage L1b, HYPERPARAMETER_CALIBRATION_PLAN.md §0d; user
2026-10-14: "6, 8 10 15 seconds per local search, without stopping on flips budget"): the
same instances and seeds, 4 arms paired line by line:
  p40_ls{6,8,10,15}_tcap_v2  `ls.polish_cap: time` (the time limit alone ends a call;
                     the flip limit is ignored) at ls.time_limit_s 6 / 8 / 10 / 15 s
Each config is the tcap reference with only ls.time_limit_s changed; the sidecar's
ls_time_limit_s carries it. 72 tasks.

PLAN `kern` (--plan kern; direction A, docs/current/RESEARCH_NOTES_SOLVER_DIRECTIONS.md §5 A
and §8, repo; user decision 2026-10-14: kernelise for the sparse Max-2-SAT grid): the same
instances and seeds, 1 arm:
  p40_ls3p5_kern_v2  the pre-registered v2 arm plus `preprocess: kernel` behind the gate
                     (screen_min 0.2, gain_min 0.2; src/sat/kernel.py)
The config is checked equal to memetic_deeppolish_p40_ls3p5_v2.yaml plus those two keys;
the sidecar adds `preprocess`. The raw baseline is the m2v2 arm p40_ls3p5_v2 (same
instances, seeds and budget; results/calib_2sat_sc2_m2v2). 18 tasks.

OUTPUTS (scripts/, the M2 formats plus `memetic_impl` and `ls_polish_flips`
sidecar columns that m2_results.py checks against each shard;
submit_m2_memetic.sh and tier2_memetic_array.sbatch are reused unchanged)

    (stem manifest_<batch>_m2v2, or manifest_<batch>_{cgrid,tgrid,kern} for --plan cgrid/tgrid/kern)
    manifest_<batch>_m2v2.tsv          9 columns read by tier2_memetic_array.sbatch
    manifest_<batch>_m2v2.tasks.csv    sidecar
    manifest_<batch>_m2v2.sha256       `sha256sum -c` list of its instances
    manifest_<batch>_m2v2.not_run.csv  every other instance of the batch + reason

    python3 scripts/make_calib_2sat_sc_memetic_manifest.py          # write
    python3 scripts/make_calib_2sat_sc_memetic_manifest.py --check  # rebuild, diff, exit 3 on drift
    python3 scripts/make_calib_2sat_sc_memetic_manifest.py --plan cgrid [--check]
    python3 scripts/make_calib_2sat_sc_memetic_manifest.py --plan tgrid [--check]
    python3 scripts/make_calib_2sat_sc_memetic_manifest.py --plan kern [--check]
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m2_manifests as m2  # noqa: E402  (ARMS, BUDGET_S, render, sha256_file, group_of)

BATCH = "calib_2sat_sc2"
BASE_ARM = "p40_ls3p5"
IMPL = "v2"
LS_T = m2.ARMS[BASE_ARM][3]  # the pre-registered ls.time_limit_s, 3.5
# arm -> (config path, config_id, job-id tag, per-call flip limit, ls.polish_cap, ls.time_limit_s)
ARMS = {
    "p40_ls3p5_v2": ("configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml",
                     "memetic_deeppolish_p40_ls3p5_v2", "p40ls3p5v2", 12500, "flips", LS_T),
    "p40_ls3p5_f200k_v2": ("configs/tier2/memetic_deeppolish_p40_ls3p5_f200k_v2.yaml",
                           "memetic_deeppolish_p40_ls3p5_f200k_v2", "p40ls3p5f200kv2", 200000, "flips", LS_T),
}
EXTRA_COLS = ["memetic_impl", "ls_polish_flips"]
SOLVER_SEEDS = (1, 2, 3)
STEM = f"manifest_{BATCH}_m2v2"

CGRID_FLIPS = (("200k", 200000), ("400k", 400000), ("800k", 800000), ("1p6m", 1600000), ("3p2m", 3200000))
CGRID_ARMS = {
    **{f"p40_f{t}_fonly_v2": (f"configs/tier2/memetic_deeppolish_p40_f{t}_fonly_v2.yaml",
                              f"memetic_deeppolish_p40_f{t}_fonly_v2", f"f{t}fo", f, "flips_only", LS_T)
       for t, f in CGRID_FLIPS},
    "p40_ls3p5_tcap_v2": ("configs/tier2/memetic_deeppolish_p40_ls3p5_tcap_v2.yaml",
                          "memetic_deeppolish_p40_ls3p5_tcap_v2", "tcap", 12500, "time", LS_T),
}
TGRID_SECONDS = (6.0, 8.0, 10.0, 15.0)
TGRID_ARMS = {
    f"p40_ls{t:g}_tcap_v2": (f"configs/tier2/memetic_deeppolish_p40_ls{t:g}_tcap_v2.yaml",
                             f"memetic_deeppolish_p40_ls{t:g}_tcap_v2", f"t{t:g}tc", 12500, "time", t)
    for t in TGRID_SECONDS
}
KERN_ARMS = {
    "p40_ls3p5_kern_v2": ("configs/tier2/memetic_deeppolish_p40_ls3p5_kern_v2.yaml",
                          "memetic_deeppolish_p40_ls3p5_kern_v2", "ls3p5", 12500, "flips", LS_T),
}
# config path -> top-level keys an arm adds to the pre-registered arm (beyond impl/ls)
ARM_EXTRA_KEYS = {
    KERN_ARMS["p40_ls3p5_kern_v2"][0]: {"preprocess": "kernel",
                                        "preprocess_gate": {"screen_min": 0.2, "gain_min": 0.2}},
}
# plan -> (stem, arms, sidecar extra columns, job-id prefix)
PLANS = {
    "m2v2": (STEM, ARMS, EXTRA_COLS, "sc2"),
    "cgrid": (f"manifest_{BATCH}_cgrid", CGRID_ARMS, EXTRA_COLS + ["ls_polish_cap"], "sc2cg"),
    "tgrid": (f"manifest_{BATCH}_tgrid", TGRID_ARMS, EXTRA_COLS + ["ls_polish_cap"], "sc2tg"),
    "kern": (f"manifest_{BATCH}_kern", KERN_ARMS, EXTRA_COLS + ["ls_polish_cap", "preprocess"], "sc2kn"),
}
NOT_RUN_COLS = ["instance", "instance_sha256", "cell_id", "gen_seed", "cell_outcome", "class",
                "rc2_status", "solve_s", "c_star", "lower_bound"]


def check_arm(arms=ARMS) -> None:
    """Each config is the pre-registered arm plus `impl: v2`, its flip limit, its
    ls.time_limit_s, (if not the default "flips") its ls.polish_cap and its ARM_EXTRA_KEYS,
    nothing else."""
    m2.check_arms()
    base_path = m2.ARMS[BASE_ARM][0]
    for path, _cid, _tag, flips, cap, ls_t in arms.values():
        want = m2.load_config(base_path)
        want["impl"] = IMPL
        want["ls"] = dict(want["ls"], ls_polish_flips=flips, flip_budget=flips, time_limit_s=ls_t)
        if cap != "flips":
            want["ls"]["polish_cap"] = cap
        want.update(ARM_EXTRA_KEYS.get(path, {}))
        if m2.load_config(path) != want:
            raise m2.BuildError(f"{path} differs from {base_path} beyond impl {IMPL}, "
                                f"the flip limit {flips}, time_limit_s {ls_t} and polish_cap {cap}")


def read_csv(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def select(inst_rows: List[Dict[str, str]], cell_rows: List[Dict[str, str]]
           ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Pure selection: (eligible instances of promising cells, every other instance)."""
    outcome = {c["cell_id"]: c["outcome"] for c in cell_rows}
    if any(c["outcome"] == "incomplete" or int(c["failed"]) for c in cell_rows):
        raise m2.BuildError("a cell is incomplete or has failed rows -- re-run RC2 first")
    elig, not_run = [], []
    for r in inst_rows:
        out = outcome.get(r["cell_id"])
        if out is None:
            raise m2.BuildError(f"{r['instance']}: cell {r['cell_id']} not in cells.csv")
        if out == "promising" and r["class"] == "eligible":
            s = float(r["solve_s"])
            elig.append({"instance": r["instance"], "instance_sha256": r["instance_sha256"],
                         "batch": BATCH, "cell_id": r["cell_id"], "gen_seed": int(r["gen_seed"]),
                         "m": int(r["m"]), "oracle_cost": int(r["c_star"]), "rc2_solve_s": s,
                         "rc2_tier": "", "analysis_group": m2.group_of(s)})
        else:
            not_run.append({"instance": r["instance"], "instance_sha256": r["instance_sha256"],
                            "cell_id": r["cell_id"], "gen_seed": r["gen_seed"], "cell_outcome": out,
                            "class": r["class"], "rc2_status": r["rc2_status"], "solve_s": r["solve_s"],
                            "c_star": r["c_star"], "lower_bound": r["lower_bound"]})
    elig.sort(key=lambda e: (e["cell_id"], e["gen_seed"]))
    for i, e in enumerate(elig, 1):
        e["pop_idx"] = f"sc{i:02d}"
    return elig, not_run


def tasks_for(elig: List[Dict[str, Any]], arms=ARMS, prefix: str = "sc2") -> List[Dict[str, Any]]:
    """All arms adjacent for every (instance, seed): paired line by line."""
    _path, _cid, pop, _ls_t, dmode = m2.ARMS[BASE_ARM]
    out = []
    for e in elig:
        for seed in SOLVER_SEEDS:
            for arm, (path, cid, tag, flips, cap, ls_t) in arms.items():
                out.append({
                    "job_id": f"{prefix}_{tag}_{e['pop_idx'][2:]}_s{seed}", "stage": BATCH, "arm": arm,
                    "config_id": cid, "config": path, "pop_size": pop, "ls_time_limit_s": ls_t,
                    "deadline_mode": dmode, "solver_seed": seed, "budget_s": m2.BUDGET_S, "pilot_idx": "",
                    "memetic_impl": IMPL, "ls_polish_flips": flips, "ls_polish_cap": cap,
                    "preprocess": ARM_EXTRA_KEYS.get(path, {}).get("preprocess", ""),
                    **{k: e[k] for k in ("pop_idx", "instance", "instance_sha256", "batch", "cell_id",
                                         "gen_seed", "m", "oracle_cost", "rc2_solve_s", "rc2_tier",
                                         "analysis_group")},
                })
    return out


def render(tasks: List[Dict[str, Any]], extra_cols=EXTRA_COLS) -> Dict[str, str]:
    """m2.render plus the extra sidecar columns."""
    files = m2.render(tasks)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=m2.TASK_COLS + extra_cols, lineterminator="\n")
    w.writeheader()
    for t in tasks:
        w.writerow({k: t[k] for k in m2.TASK_COLS + extra_cols})
    files[".tasks.csv"] = buf.getvalue()
    return files


def build(plan: str = "m2v2") -> Dict[str, str]:
    stem, arms, extra_cols, prefix = PLANS[plan]
    check_arm(arms)
    rc = subprocess.run([sys.executable, "scripts/calib_2sat_sc_readout.py", "--batch", BATCH, "--check"],
                        capture_output=True, text=True)
    if rc.returncode != 0:
        raise m2.BuildError(f"readout CSVs are stale or missing (calib_2sat_sc_readout.py --batch {BATCH} "
                            f"--check exit {rc.returncode}): {rc.stderr.strip()[-300:]}")
    elig, not_run = select(read_csv(os.path.join("results", BATCH, "instances.csv")),
                           read_csv(os.path.join("results", BATCH, "cells.csv")))
    if not elig:
        raise m2.BuildError("no eligible instance in a promising cell")
    tier = {r["instance"]: r.get("tier") or "" for r in
            m2.read_jsonl(os.path.join("results", f"profile_{BATCH}_all.jsonl"))}
    for e in elig:  # a stale rsync fails the build, not the run
        e["rc2_tier"] = tier.get(e["instance"], "")
        if not e["rc2_tier"]:
            raise m2.BuildError(f"{e['instance']}: no RC2 tier in results/profile_{BATCH}_all.jsonl")
        sha = m2.sha256_file(e["instance"])
        if sha != e["instance_sha256"]:
            raise m2.BuildError(f"{e['instance']}: sha256 {sha} != readout")
    files = {stem + suf: text for suf, text in render(tasks_for(elig, arms, prefix), extra_cols).items()}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=NOT_RUN_COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(not_run)
    files[stem + ".not_run.csv"] = buf.getvalue()
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--plan", choices=sorted(PLANS), default="m2v2")
    a = ap.parse_args(argv)
    stem, arms, _extra, _prefix = PLANS[a.plan]
    files = build(a.plan)
    if a.check:
        bad = [n for n, t in files.items()
               if not os.path.isfile(os.path.join("scripts", n))
               or open(os.path.join("scripts", n), encoding="utf-8").read() != t]
        if bad:
            print("DRIFT: " + ", ".join(bad), file=sys.stderr)
            return 3
        print("CHECK OK")
        return 0
    for n, t in files.items():
        with open(os.path.join("scripts", n), "w", encoding="utf-8", newline="\n") as f:
            f.write(t)
    n_tasks = files[stem + ".tsv"].count("\n")
    n_nr = files[stem + ".not_run.csv"].count("\n") - 1
    print(f"{stem}: {n_tasks} tasks ({n_tasks // len(SOLVER_SEEDS) // len(arms)} eligible x "
          f"{len(SOLVER_SEEDS)} seeds x {len(arms)} arms), "
          f"{n_nr} not run (see {stem}.not_run.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
