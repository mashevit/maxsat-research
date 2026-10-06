#!/usr/bin/env python3
"""Build the calib_c memetic manifest from calib_c's RC2 rows (run AFTER RC2 returns).

Plan: docs/current/CORPUS_FREEZE_PREP.md §5 (repo). This is step 2 of the fixed
reinforcement batch; step 1 is the RC2 array over scripts/manifest_calib_c_rc2.txt.

ELIGIBILITY (the agreed window; boundary convention as in candidate_cells.py)

    eligible  <=>  completed and final_cost == cost_lower_bound and 30 < solve_s <= 900

Only eligible instances get memetic runs. Every other calib_c instance is
written to the not-run list with its reason (below_window / censored), never
dropped. Any RC2 row in class "failed" (error, unsat, missing row, solve_s <= 0,
final_cost != lower bound) stops the build: it is re-run first.

RUNS. Primary configuration only: memetic_deeppolish_p40_ls3p5 (pop 40,
ls.time_limit_s 3.5, 12,500 flips/call, deadline clip), solver seeds 1-3,
900 s budget, stop at the RC2 optimum, grace 60 -- byte-for-byte the a35 arm of
the M2 full pool, so the new instances pool with its rows per cell. The config
is re-checked against make_m2_manifests.ARMS before anything is written.

ENVIRONMENT. calib_a and calib_b ran under PySAT 1.9.dev3 on every task. If
calib_c's env sidecars show anything else, the build stops (--allow-env-drift
overrides, and the drift must then be recorded in the calibration log).

OUTPUTS (scripts/, same formats as the M2 manifests, so submit_m2_memetic.sh,
tier2_memetic_array.sbatch and m2_results.py are reused unchanged)

    manifest_calib_c_m2.tsv         9 columns read by tier2_memetic_array.sbatch
    manifest_calib_c_m2.tasks.csv   sidecar (TASK_COLS of make_m2_manifests)
    manifest_calib_c_m2.sha256      `sha256sum -c` list of its instances
    manifest_calib_c_m2.not_run.csv every non-eligible calib_c instance + reason

    pop_idx is "cc001".. (calib_c-local), never a full-pool number.

    python3 scripts/make_calib_c_memetic_manifest.py          # write
    python3 scripts/make_calib_c_memetic_manifest.py --check  # rebuild, diff, exit 3 on drift
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_m2_manifests as m2  # noqa: E402  (ARMS, check_arms, render, sha256_file)

BATCH = "calib_c"
LO_S, HI_S = 30.0, 900.0
ARM = "p40_ls3p5"
SOLVER_SEEDS = (1, 2, 3)
EXPECTED_PYSAT = "1.9.dev3"
STEM = "manifest_calib_c_m2"
NOT_RUN_COLS = ["instance", "instance_sha256", "cell_id", "gen_seed", "rc2_status",
                "rc2_solve_s", "cost_lower_bound", "reason"]


def classify(prof: Dict[str, Any]) -> Tuple[str, str]:
    """-> (class, reason); class in eligible / below_window / censored / failed."""
    s = prof.get("solve_s")
    s = None if s is None else float(s)
    if prof.get("completed") is True:
        if prof.get("final_cost") != prof.get("cost_lower_bound"):
            return "failed", "completed but final_cost != cost_lower_bound"
        if s is None or s <= 0:
            return "failed", f"non-positive solve_s {s} (wall-clock step)"
        if s <= LO_S:
            return "below_window", f"certified in {s:.3f} s <= {LO_S:g} s"
        if s <= HI_S:
            return "eligible", ""
        return "censored", f"completed only at {s:.3f} s > {HI_S:g} s"
    if prof.get("status") in ("timeout", "subprocess_killed") and float(prof.get("cap_s") or 0) >= HI_S:
        return "censored", f"{prof.get('status')} at cap {prof.get('cap_s')}, LB {prof.get('cost_lower_bound')}"
    return "failed", f"status {prof.get('status')!r}: {prof.get('error')}"


def select(gen_rows: List[Dict[str, Any]], prof_rows: List[Dict[str, Any]]):
    """Pure selection: (eligible rows, not-run rows); raises on failed/missing rows."""
    gen = {r["instance"]: r for r in gen_rows}
    by_inst: Dict[str, Dict[str, Any]] = {}
    for r in prof_rows:
        by_inst[r["instance"]] = r  # aggregate files hold the last row per task
    missing = sorted(set(gen) - set(by_inst))
    if missing:
        raise m2.BuildError(f"{len(missing)} calib_c instances have no RC2 row (re-run first): {missing[:3]}")
    elig, not_run, failed = [], [], []
    for inst in sorted(gen):
        g, r = gen[inst], by_inst[inst]
        prof = r["profile"]
        cls, why = classify(prof)
        if cls == "failed":
            failed.append(f"{inst}: {why}")
        elif cls == "eligible":
            elig.append({"instance": inst, "instance_sha256": g["instance_sha256"], "batch": BATCH,
                         "cell_id": g["cell_id"], "family": g["family"], "k": g["k"], "n": g["n"],
                         "alpha": g["alpha"], "m": g["m"], "gen_seed": g["seed"],
                         "oracle_cost": int(prof["final_cost"]), "rc2_solve_s": float(prof["solve_s"]),
                         "rc2_tier": r.get("tier"), "analysis_group": m2.group_of(float(prof["solve_s"])),
                         "pysat_version": (r.get("env") or {}).get("pysat_version")})
        else:
            not_run.append({"instance": inst, "instance_sha256": g["instance_sha256"], "cell_id": g["cell_id"],
                            "gen_seed": g["seed"], "rc2_status": prof.get("status"),
                            "rc2_solve_s": prof.get("solve_s"), "cost_lower_bound": prof.get("cost_lower_bound"),
                            "reason": f"{cls}: {why}"})
    if failed:
        raise m2.BuildError("RC2 rows in class failed -- re-run before building:\n  " + "\n  ".join(failed))
    for i, r in enumerate(elig, 1):
        r["pop_idx"] = f"cc{i:03d}"
    return elig, not_run


def tasks_for(elig: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    path, cid, pop, ls_t, dmode = m2.ARMS[ARM]
    out = []
    for inst in elig:
        for seed in SOLVER_SEEDS:
            out.append({
                "job_id": f"cc_p40ls3p5_{inst['pop_idx'][2:]}_s{seed}", "stage": "calib_c", "arm": ARM,
                "config_id": cid, "config": path, "pop_size": pop, "ls_time_limit_s": ls_t,
                "deadline_mode": dmode, "solver_seed": seed, "budget_s": m2.BUDGET_S, "pilot_idx": "",
                **{k: inst[k] for k in ("pop_idx", "instance", "instance_sha256", "batch", "cell_id",
                                        "gen_seed", "m", "oracle_cost", "rc2_solve_s", "rc2_tier",
                                        "analysis_group")},
            })
    return out


def build(allow_env_drift: bool = False) -> Dict[str, str]:
    m2.check_arms()
    gen_rows = m2.read_jsonl(os.path.join("data", "generated", BATCH, "manifest.jsonl"))
    prof_path = os.path.join("results", f"profile_{BATCH}_all.jsonl")
    if not os.path.isfile(prof_path):
        raise m2.BuildError(f"{prof_path} missing: run the calib_c RC2 array and "
                            f"scripts/aggregate_rc2_profile.py --batch {BATCH} first")
    prof_rows = m2.read_jsonl(prof_path)
    versions = {(r.get("env") or {}).get("pysat_version") for r in prof_rows}
    if versions != {EXPECTED_PYSAT} and not allow_env_drift:
        raise m2.BuildError(f"PySAT versions {sorted(map(str, versions))} != {{{EXPECTED_PYSAT}}} "
                            f"(calib_a/b); pass --allow-env-drift only after logging the drift")
    elig, not_run = select(gen_rows, prof_rows)
    for r in elig:  # a stale rsync fails the build, not the run
        sha = m2.sha256_file(r["instance"])
        if sha != r["instance_sha256"]:
            raise m2.BuildError(f"{r['instance']}: sha256 {sha} != generator manifest")
    files = {STEM + suf: text for suf, text in m2.render(tasks_for(elig)).items()}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=NOT_RUN_COLS, lineterminator="\n")
    w.writeheader()
    for r in not_run:
        w.writerow(r)
    files[STEM + ".not_run.csv"] = buf.getvalue()
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--allow-env-drift", action="store_true")
    a = ap.parse_args(argv)
    files = build(a.allow_env_drift)
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
    n_tasks = files[STEM + ".tsv"].count("\n")
    n_nr = files[STEM + ".not_run.csv"].count("\n") - 1
    print(f"{STEM}: {n_tasks} tasks ({n_tasks // len(SOLVER_SEEDS)} eligible x {len(SOLVER_SEEDS)} seeds), "
          f"{n_nr} not run (see {STEM}.not_run.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
