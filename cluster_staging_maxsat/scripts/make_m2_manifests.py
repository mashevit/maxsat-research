#!/usr/bin/env python3
"""Build the M2 modified-deeppolish population, pilot and full-pool manifests.

Plan: docs/M2_DEEPPOLISH_HANDOUT.md (population §2, pilot instances §7.1).
Run record and cluster commands: docs/M2_DEEPPOLISH_RUN_PREPARATION.md (repo).

POPULATION. Every RC2-certified instance of calib_a and calib_b with
30 s <= solve_s <= 900 s (inclusive both ends), deduplicated on
instance_sha256. Certified means `profile.completed == true` with
`final_cost == cost_lower_bound`; a censored row's lower bound is never used as
a target. Each RC2 row is joined to its generator manifest on the instance
path, and the sha256 of every instance file is RECOMPUTED here and compared
with the generator manifest -- a stale rsync fails the build, not the run.
Expected: 70 instances, groups lower_ext / tier2 / upper_ext = 16 / 46 / 8
(checked; the build exits 3 otherwise).

    lower_ext   30 <= solve_s <= 60
    tier2       60 <  solve_s <= 600
    upper_ext  600 <  solve_s <= 900

TWO SEEDS, KEPT APART. `gen_seed` is the generator seed of the instance (the
`_sN` in its filename, `seed` in data/generated/*/manifest.jsonl). `seed` in
the task manifest is the SOLVER seed passed to run_memetic_shard --seed. The
sidecar CSVs carry both in separately named columns.

ARMS. The watchdog is unchanged. The three new arms opt into deadline
clipping (`ea.deadline_mode: clip`, src/evo/memetic.py); the control is the
historical config and keeps the generation-boundary deadline check:

    arm        config_id                        pop  ls.time_limit_s  deadline_mode
    p40_ls0p5  memetic_deeppolish (control)      40  0.5              (none)
    p40_ls2p5  memetic_deeppolish_p40_ls2p5      40  2.5              clip
    p10_ls2p5  memetic_deeppolish_p10_ls2p5      10  2.5              clip
    p10_ls3p5  memetic_deeppolish_p10_ls3p5      10  3.5              clip

All keep ls_polish_flips = flip_budget = 12500, tournament_k 3, pmutate 0.02,
elitism, max_gens 1e6; every config is loaded and checked against this table.

OUTPUTS (scripts/, paths in the TSVs are relative to the staging root):

    m2_population.csv                  70 rows
    manifest_m2_pilot.tsv              96 tasks: 3 arms x 10 instances x
                                       seeds 1-3, + p10_ls3p5 on pilot #5, #8
    manifest_m2_full_p40_ls2p5.tsv     210 tasks (70 x seeds 1-3)
    manifest_m2_full_p10_ls2p5.tsv     210 tasks
    <manifest>.sha256                  `sha256sum -c` list of its instances
    <manifest>.tasks.csv               per-task sidecar (both seeds, group, ...)

TSV columns are the 9 read by tier2_memetic_array.sbatch:

    job_id instance config config_id seed budget_s oracle_cost tier rc2_run

with tier = the original RC2 tier label and rc2_run = the calibration batch.
Job ids embed the stage (m2p / m2f) and the arm, so shards from different
arms and stages can never share a path even in one OUTDIR.

    python3 scripts/make_m2_manifests.py            # (re)write all outputs
    python3 scripts/make_m2_manifests.py --check    # rebuild in memory, diff
                                                    # against disk, exit 3 on drift
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import sys
from typing import Any, Dict, List, Tuple

BATCHES = ("calib_a", "calib_b")
FLOOR_S, WINDOW_LO_S, WINDOW_HI_S, CEIL_S = 30.0, 60.0, 600.0, 900.0
EXPECTED_GROUPS = {"lower_ext": 16, "tier2": 46, "upper_ext": 8}
BUDGET_S = 900
SOLVER_SEEDS = (1, 2, 3)

# arm -> (config path, config_id, pop_size, ls.time_limit_s, ea.deadline_mode)
ARMS: Dict[str, Tuple[str, str, int, float, str]] = {
    "p40_ls0p5": ("configs/tier2/memetic_deeppolish.yaml", "memetic_deeppolish", 40, 0.5, ""),
    "p40_ls2p5": ("configs/tier2/memetic_deeppolish_p40_ls2p5.yaml", "memetic_deeppolish_p40_ls2p5", 40, 2.5, "clip"),
    "p10_ls2p5": ("configs/tier2/memetic_deeppolish_p10_ls2p5.yaml", "memetic_deeppolish_p10_ls2p5", 10, 2.5, "clip"),
    "p10_ls3p5": ("configs/tier2/memetic_deeppolish_p10_ls3p5.yaml", "memetic_deeppolish_p10_ls3p5", 10, 3.5, "clip"),
}
# Everything but pop_size and ls.time_limit_s must equal the control's values.
SHARED = {
    ("ea", "enabled"): True, ("ea", "tournament_k"): 3, ("ea", "pmutate"): 0.02,
    ("ea", "elitism"): True, ("ea", "max_gens"): 1000000,
    ("ls", "ls_polish_flips"): 12500, ("ls", "flip_budget"): 12500,
}

# Handout §7.1, in its order: (batch, cell_id, gen_seed, group, c*, m, ~solve_s).
PILOT = [
    ("calib_a", "max2sat_n100_a6", 1, "upper_ext", 50, 600, 752.7),
    ("calib_b", "max2sat_n250_a2.35", 3, "upper_ext", 22, 588, 610.3),
    ("calib_b", "max3sat_n50_a9", 5, "upper_ext", 13, 450, 847.3),
    ("calib_a", "max3sat_n150_a5", 3, "upper_ext", 3, 750, 772.2),
    ("calib_b", "max2sat_n400_a2.3", 2, "tier2", 23, 920, 367.2),
    ("calib_b", "max2sat_n150_a3.3", 4, "tier2", 28, 495, 226.6),
    ("calib_b", "max3sat_n70_a6.5", 4, "tier2", 7, 455, 217.8),
    ("calib_b", "max3sat_n250_a4.35", 2, "tier2", 1, 1088, 323.7),
    ("calib_b", "max3sat_n150_a4.8", 3, "lower_ext", 2, 720, 34.9),
    ("calib_b", "max3sat_n100_a5.2", 5, "lower_ext", 4, 520, 46.8),
]
PILOT_MAIN_ARMS = ("p40_ls0p5", "p40_ls2p5", "p10_ls2p5")
PILOT_EXTRA_ARM, PILOT_EXTRA_IDX = "p10_ls3p5", (5, 8)  # the two high-m instances
FULL_ARMS = ("p40_ls2p5", "p10_ls2p5")

POP_COLS = ["pop_idx", "instance", "instance_sha256", "batch", "cell_id", "family",
            "k", "n", "alpha", "m", "gen_seed", "oracle_cost", "rc2_solve_s",
            "rc2_tier", "analysis_group", "pysat_version"]
TASK_COLS = ["task_id", "job_id", "stage", "arm", "config_id", "config", "pop_size",
             "ls_time_limit_s", "deadline_mode", "solver_seed", "budget_s", "pilot_idx", "pop_idx",
             "instance", "instance_sha256", "batch", "cell_id", "gen_seed", "m",
             "oracle_cost", "rc2_solve_s", "rc2_tier", "analysis_group"]


class BuildError(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"FATAL: {msg}")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def group_of(s: float) -> str:
    if FLOOR_S <= s <= WINDOW_LO_S:
        return "lower_ext"
    if WINDOW_LO_S < s <= WINDOW_HI_S:
        return "tier2"
    if WINDOW_HI_S < s <= CEIL_S:
        return "upper_ext"
    return ""


def load_config(path: str) -> Dict[str, Any]:
    import yaml  # PyYAML: the same loader run_memetic_shard uses on the cluster
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def check_arms() -> None:
    for arm, (path, _cid, pop, ls_t, dmode) in ARMS.items():
        cfg = load_config(path)
        if "time_limit_s" in cfg:
            raise BuildError(f"{path}: top-level time_limit_s must not be set")
        want = dict(SHARED)
        want[("ea", "pop_size")] = pop
        want[("ls", "time_limit_s")] = ls_t
        got_mode = (cfg.get("ea") or {}).get("deadline_mode", "")
        if got_mode != dmode:
            raise BuildError(f"{path}: ea.deadline_mode = {got_mode!r}, expected {dmode!r} (arm {arm})")
        for (sec, key), val in want.items():
            got = (cfg.get(sec) or {}).get(key)
            if got != val or type(got) is not type(val):
                raise BuildError(f"{path}: {sec}.{key} = {got!r}, expected {val!r} (arm {arm})")


def build_population() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: Dict[str, str] = {}
    for batch in BATCHES:
        gen = {r["instance"]: r for r in
               read_jsonl(os.path.join("data", "generated", batch, "manifest.jsonl"))}
        for r in read_jsonl(os.path.join("results", f"profile_{batch}_all.jsonl")):
            prof = r.get("profile") or {}
            if prof.get("completed") is not True:
                continue
            s = float(prof["solve_s"])
            grp = group_of(s)
            if not grp:
                continue
            if prof.get("final_cost") != prof.get("cost_lower_bound"):
                raise BuildError(f"{r['instance']}: completed but final_cost != lower bound")
            inst = r["instance"]
            g = gen.get(inst)
            if g is None:
                raise BuildError(f"{inst}: RC2 row has no generator-manifest row")
            if not os.path.isfile(inst):
                raise BuildError(f"{inst}: instance file missing (rsync data/?)")
            sha = sha256_file(inst)
            if sha != g["instance_sha256"]:
                raise BuildError(f"{inst}: sha256 {sha} != generator manifest {g['instance_sha256']}")
            if sha in seen:  # dedup on content, first batch wins
                continue
            seen[sha] = inst
            rows.append({
                "instance": inst, "instance_sha256": sha, "batch": batch,
                "cell_id": g["cell_id"], "family": g["family"], "k": g["k"], "n": g["n"],
                "alpha": g["alpha"], "m": g["m"], "gen_seed": g["seed"],
                "oracle_cost": int(prof["final_cost"]), "rc2_solve_s": s,
                "rc2_tier": r.get("tier"), "analysis_group": grp,
                "pysat_version": (r.get("env") or {}).get("pysat_version"),
            })
    rows.sort(key=lambda r: r["instance"])
    for i, r in enumerate(rows, 1):
        r["pop_idx"] = i
    counts = {g: sum(r["analysis_group"] == g for r in rows) for g in EXPECTED_GROUPS}
    if counts != EXPECTED_GROUPS or len(rows) != sum(EXPECTED_GROUPS.values()):
        raise BuildError(f"population counts {counts} (total {len(rows)}) != {EXPECTED_GROUPS}")
    return rows


def resolve_pilot(pop: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for idx, (batch, cell, gseed, grp, cstar, m, approx_s) in enumerate(PILOT, 1):
        hits = [r for r in pop if (r["batch"], r["cell_id"], r["gen_seed"]) == (batch, cell, gseed)]
        if len(hits) != 1:
            raise BuildError(f"pilot #{idx} {batch}/{cell}/s{gseed}: {len(hits)} population matches")
        r = hits[0]
        if (r["analysis_group"], r["oracle_cost"], r["m"]) != (grp, cstar, m) \
                or abs(r["rc2_solve_s"] - approx_s) > 0.051:
            raise BuildError(f"pilot #{idx} {r['instance']}: resolved (group, c*, m, solve_s) = "
                             f"{(r['analysis_group'], r['oracle_cost'], r['m'], r['rc2_solve_s'])}, "
                             f"handout says {(grp, cstar, m, approx_s)}")
        out.append(dict(r, pilot_idx=idx))
    return out


def task(stage: str, arm: str, inst: Dict[str, Any], seed: int, pilot_idx: Any) -> Dict[str, Any]:
    path, cid, pop, ls_t, dmode = ARMS[arm]
    tag = arm.replace("_", "")
    where = f"i{pilot_idx:02d}" if stage == "pilot" else f"{inst['pop_idx']:03d}"
    return {
        "job_id": f"m2{stage[0]}_{tag}_{where}_s{seed}", "stage": stage, "arm": arm,
        "config_id": cid, "config": path, "pop_size": pop, "ls_time_limit_s": ls_t,
        "deadline_mode": dmode,
        "solver_seed": seed, "budget_s": BUDGET_S, "pilot_idx": pilot_idx,
        "pop_idx": inst["pop_idx"], "instance": inst["instance"],
        "instance_sha256": inst["instance_sha256"], "batch": inst["batch"],
        "cell_id": inst["cell_id"], "gen_seed": inst["gen_seed"], "m": inst["m"],
        "oracle_cost": inst["oracle_cost"], "rc2_solve_s": inst["rc2_solve_s"],
        "rc2_tier": inst["rc2_tier"], "analysis_group": inst["analysis_group"],
    }


def pilot_tasks(pilot: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Instance-major, seed, then arm: the paired runs of one (instance, seed)
    # sit on adjacent lines, so at %30 they run in the same wave on the same
    # cluster load rather than hours apart.
    out = []
    for inst in pilot:
        for seed in SOLVER_SEEDS:
            arms = list(PILOT_MAIN_ARMS)
            if inst["pilot_idx"] in PILOT_EXTRA_IDX:
                arms.append(PILOT_EXTRA_ARM)
            for arm in arms:
                out.append(task("pilot", arm, inst, seed, inst["pilot_idx"]))
    return out


def full_tasks(pop: List[Dict[str, Any]], arm: str) -> List[Dict[str, Any]]:
    return [task("full", arm, inst, seed, "") for inst in pop for seed in SOLVER_SEEDS]


def render(tasks: List[Dict[str, Any]], pop_rows=None) -> Dict[str, str]:
    """Returns {suffix: file text} for one manifest."""
    for i, t in enumerate(tasks, 1):
        t["task_id"] = i
    ids = [t["job_id"] for t in tasks]
    if len(set(ids)) != len(ids):
        raise BuildError("duplicate job_id in a manifest")
    tsv = "".join("\t".join(str(x) for x in (
        t["job_id"], t["instance"], t["config"], t["config_id"], t["solver_seed"],
        t["budget_s"], t["oracle_cost"], t["rc2_tier"], t["batch"])) + "\n" for t in tasks)
    shas = {}
    for t in tasks:
        shas.setdefault(t["instance"], t["instance_sha256"])
    sha = "".join(f"{s}  {p}\n" for p, s in sorted(shas.items()))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=TASK_COLS, lineterminator="\n")
    w.writeheader()
    for t in tasks:
        w.writerow({k: t[k] for k in TASK_COLS})
    return {".tsv": tsv, ".sha256": sha, ".tasks.csv": buf.getvalue()}


def population_csv(pop: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=POP_COLS, lineterminator="\n")
    w.writeheader()
    for r in pop:
        w.writerow({k: r[k] for k in POP_COLS})
    return buf.getvalue()


def build_all() -> Dict[str, str]:
    check_arms()
    pop = build_population()
    pilot = resolve_pilot(pop)
    files = {"scripts/m2_population.csv": population_csv(pop)}
    sets = {"scripts/manifest_m2_pilot": pilot_tasks(pilot)}
    for arm in FULL_ARMS:
        sets[f"scripts/manifest_m2_full_{arm}"] = full_tasks(pop, arm)
    expected = {"scripts/manifest_m2_pilot": 96,
                "scripts/manifest_m2_full_p40_ls2p5": 210,
                "scripts/manifest_m2_full_p10_ls2p5": 210}
    all_ids: List[str] = []
    for stem, tasks in sets.items():
        if len(tasks) != expected[stem]:
            raise BuildError(f"{stem}: {len(tasks)} tasks, expected {expected[stem]}")
        for suf, text in render(tasks).items():
            files[stem + suf] = text
        all_ids += [t["job_id"] for t in tasks]
    if len(set(all_ids)) != len(all_ids):
        raise BuildError("job_id collides across manifests")
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="rebuild in memory and compare with the files on disk; exit 3 on drift")
    args = ap.parse_args(argv)
    if not os.path.isdir("src") or not os.path.isdir("scripts"):
        raise BuildError("run from cluster_staging_maxsat/ (the staging tree root)")
    files = build_all()
    if args.check:
        bad = []
        for p, text in files.items():
            try:
                with open(p, encoding="utf-8") as f:
                    if f.read() != text:
                        bad.append(p)
            except FileNotFoundError:
                bad.append(p)
        for p in bad:
            print(f"DRIFT  {p}", file=sys.stderr)
        print(f"check: {len(files) - len(bad)}/{len(files)} files identical")
        return 3 if bad else 0
    for p, text in files.items():
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        n = text.count("\n") - (1 if p.endswith(".csv") else 0)
        print(f"wrote {p}  ({n} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
