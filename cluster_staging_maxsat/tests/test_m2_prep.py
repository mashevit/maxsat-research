"""
M2 modified-deeppolish run preparation (docs/M2_DEEPPOLISH_RUN_PREPARATION.md
in the repo).

These tests pin the four arms' resolved settings, the manifests' counts and
identities, population-10 compatibility of the EA, the opt-in deadline
clipping in src/evo/memetic.py (and that the control path without it is
byte-for-byte the pre-clipping behaviour), and the result classifier's
success / watchdog / resume rules. No test here runs longer than a few
seconds.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
SCRIPTS = os.path.join(ROOT, "scripts")
for p in (SRC, SCRIPTS):
    if p not in sys.path:
        sys.path.insert(0, p)

import make_m2_manifests as mk  # noqa: E402
import m2_results as res  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from sat.cnf import WCNF  # noqa: E402

yaml = pytest.importorskip("yaml")

# sha256 of configs/tier2/memetic_deeppolish.yaml as committed (d5936cd): the
# control arm must be the historical config, byte for byte.
CONTROL_SHA = "cf6c3ad9665a9d64571d009e71f95df6f3ee530d25b7991a5f3c3e169c034990"
MANIFESTS = {"manifest_m2_pilot": 96, "manifest_m2_full_p40_ls2p5": 210,
             "manifest_m2_full_p10_ls2p5": 210}


def _cfg(arm):
    with open(os.path.join(ROOT, mk.ARMS[arm][0]), encoding="utf-8") as f:
        return yaml.safe_load(f)


def _tasks(stem):
    with open(os.path.join(SCRIPTS, stem + ".tasks.csv"), encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- configs
def test_control_config_is_the_historical_file():
    with open(os.path.join(ROOT, "configs/tier2/memetic_deeppolish.yaml"), "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == CONTROL_SHA


@pytest.mark.parametrize("arm,pop,ls_t,children,clip", [
    ("p40_ls0p5", 40, 0.5, 38, False), ("p40_ls2p5", 40, 2.5, 38, True),
    ("p10_ls2p5", 10, 2.5, 9, True), ("p10_ls3p5", 10, 3.5, 9, True)])
def test_arm_resolved_settings(arm, pop, ls_t, children, clip):
    cfg = _cfg(arm)
    assert "time_limit_s" not in cfg  # run budget comes only from --budget-s
    ea = {"enabled": True, "pop_size": pop, "tournament_k": 3,
          "pmutate": 0.02, "elitism": True, "max_gens": 1000000}
    if clip:
        ea["deadline_mode"] = "clip"
    assert cfg["ea"] == ea
    assert cfg["ls"] == {"ls_polish_flips": 12500, "time_limit_s": ls_t, "flip_budget": 12500}
    # memetic.py elite rule, unchanged: max(1, ceil(0.05 * pop_size))
    assert pop - max(1, math.ceil(0.05 * pop)) == children


def test_config_ids_distinct():
    ids = [v[1] for v in mk.ARMS.values()]
    assert len(set(ids)) == len(ids) == 4


# ---------------------------------------------------------------- manifests
def test_manifests_match_a_fresh_build():
    if not os.path.isfile(os.path.join(ROOT, "data/generated/calib_b/manifest.jsonl")):
        pytest.skip("calibration data not staged")
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        assert mk.main(["--check"]) == 0
    finally:
        os.chdir(cwd)


def test_population_counts():
    with open(os.path.join(SCRIPTS, "m2_population.csv"), encoding="utf-8") as f:
        pop = list(csv.DictReader(f))
    assert len(pop) == 70
    assert len({r["instance_sha256"] for r in pop}) == 70
    groups = {g: sum(r["analysis_group"] == g for r in pop) for g in mk.EXPECTED_GROUPS}
    assert groups == {"lower_ext": 16, "tier2": 46, "upper_ext": 8}
    for r in pop:
        assert 30.0 <= float(r["rc2_solve_s"]) <= 900.0
        assert mk.group_of(float(r["rc2_solve_s"])) == r["analysis_group"]


@pytest.mark.parametrize("stem,n", sorted(MANIFESTS.items()))
def test_manifest_rows(stem, n):
    tasks = _tasks(stem)
    with open(os.path.join(SCRIPTS, stem + ".tsv"), encoding="utf-8") as f:
        lines = [l.rstrip("\n").split("\t") for l in f if l.strip()]
    assert len(lines) == len(tasks) == n
    for line, t in zip(lines, tasks):
        assert len(line) == 9
        job_id, inst, cfg, cid, seed, budget, oracle, tier, batch = line
        assert (job_id, inst, cfg, cid, seed) == (t["job_id"], t["instance"], t["config"],
                                                  t["config_id"], t["solver_seed"])
        assert budget == "900" and seed in ("1", "2", "3")
        assert oracle == t["oracle_cost"] and batch == t["batch"] and tier == t["rc2_tier"]
        # the generator seed is the instance's; it is in the filename, never the solver seed column
        assert inst.endswith(f"_s{t['gen_seed']}.wcnf")
        assert os.path.isfile(os.path.join(ROOT, cfg))


def test_job_ids_unique_across_all_manifests():
    ids = [t["job_id"] for s in MANIFESTS for t in _tasks(s)]
    assert len(ids) == len(set(ids)) == 516


def test_pilot_composition():
    tasks = _tasks("manifest_m2_pilot")
    by_arm = {}
    for t in tasks:
        by_arm.setdefault(t["arm"], []).append(t)
    assert {a: len(v) for a, v in by_arm.items()} == {
        "p40_ls0p5": 30, "p40_ls2p5": 30, "p10_ls2p5": 30, "p10_ls3p5": 6}
    assert {t["pilot_idx"] for t in by_arm["p10_ls3p5"]} == {"5", "8"}
    assert {int(t["m"]) for t in by_arm["p10_ls3p5"]} == {920, 1088}
    assert len({t["instance_sha256"] for t in tasks}) == 10
    # every (instance, seed) appears once per main arm: the comparison is paired
    for arm in mk.PILOT_MAIN_ARMS:
        keys = [(t["pilot_idx"], t["solver_seed"]) for t in by_arm[arm]]
        assert len(set(keys)) == 30


def test_full_pool_manifests_cover_population_once_per_seed():
    for stem in ("manifest_m2_full_p40_ls2p5", "manifest_m2_full_p10_ls2p5"):
        tasks = _tasks(stem)
        assert len({(t["instance_sha256"], t["solver_seed"]) for t in tasks}) == 210
        assert len({t["arm"] for t in tasks}) == 1


# ---------------------------------------------------------------- population 10
CNF = """p cnf 12 30
1 2 -3 0
-1 4 5 0
3 -4 6 0
-5 -6 7 0
7 8 -9 0
-7 9 10 0
-8 -10 11 0
11 12 1 0
-11 -12 2 0
-2 3 4 0
5 -7 8 0
-3 -9 12 0
6 10 -12 0
-6 -8 -11 0
1 -5 9 0
-1 -2 -4 0
2 5 -10 0
-3 7 11 0
4 -6 -12 0
8 9 10 0
-9 -10 -11 0
1 6 11 0
-1 -6 -11 0
3 8 12 0
-3 -8 -12 0
2 7 -5 0
-2 -7 5 0
4 9 -1 0
-4 -9 1 0
10 12 6 0
"""


def _tiny(tmp_path):
    p = tmp_path / "tiny.cnf"
    p.write_text(CNF)
    return WCNF.parse_dimacs(str(p))


@pytest.mark.parametrize("arm", ["p10_ls2p5", "p10_ls3p5"])
def test_population_10_runs(tmp_path, arm):
    cfg = _cfg(arm)
    cfg["time_limit_s"] = 0.3            # what --budget-s injects
    cfg["ls"]["time_limit_s"] = 0.005    # shrink the per-call allowance for test speed only
    out = run_memetic(_tiny(tmp_path), cfg, rng_seed=1)
    gens, children = out["meta"]["ea_generations"], out["meta"]["children"]
    assert out["stop_reason"] == "time_cap"
    # 1 elite + 9 children per generation; with deadline clipping the last
    # generation may stop part-way through its fill.
    assert gens >= 1 and 9 * (gens - 1) < children <= 9 * gens


def test_shard_runner_records_population_10(tmp_path):
    import importlib
    shard = importlib.import_module("cli.run_memetic_shard")
    inst = tmp_path / "tiny.cnf"
    inst.write_text(CNF)
    out = tmp_path / "rec.jsonl"
    rc = shard.main(["--instance", str(inst), "--config", os.path.join(ROOT, mk.ARMS["p10_ls2p5"][0]),
                     "--config-id", "memetic_deeppolish_p10_ls2p5", "--seed", "1",
                     "--budget-s", "0.3", "--grace-s", "5", "--oracle-cost", "0",
                     "-D", "ls.time_limit_s=0.005", "--out", str(out)])
    rec = json.loads(out.read_text())
    assert rc == 0 and rec["status"] == "ok"
    assert rec["config"]["ea"]["pop_size"] == 10 and rec["config"]["time_limit_s"] == 0.3
    assert rec["config"]["ea"]["deadline_mode"] == "clip"
    assert 9 * (rec["ea_generations"] - 1) < rec["children"] <= 9 * rec["ea_generations"]


# ---------------------------------------------------------------- classifier
TASK = {"task_id": "1", "job_id": "m2p_x_i01_s1", "config_id": "cfg", "solver_seed": "1",
        "instance_sha256": "ab", "budget_s": "900", "oracle_cost": "3", "pop_size": "10",
        "ls_time_limit_s": "2.5"}


def _rec(**kw):
    r = {"job_id": "m2p_x_i01_s1", "config_id": "cfg", "seed": 1, "instance_sha256": "ab",
         "budget_s": 900.0, "grace_s": 60.0, "stop_at_oracle": True, "oracle_cost": 3,
         "config": {"ea": {"pop_size": 10}, "ls": {"time_limit_s": 2.5, "ls_polish_flips": 12500}},
         "status": "ok", "stop_reason": "target", "time_to_target_s": 12.0}
    r.update(kw)
    return r


@pytest.mark.parametrize("rec,cls", [
    (None, "infra_missing"),
    (_rec(), "success"),
    (_rec(time_to_target_s=900.0), "success"),
    (_rec(time_to_target_s=931.4), "target_after_budget"),
    (_rec(stop_reason="time_cap", time_to_target_s=None), "budget_exhausted"),
    (_rec(status="timeout", stop_reason=None, time_to_target_s=None,
          error="watchdog_fired_at_budget+60s"), "watchdog"),
    (_rec(status="cost_mismatch"), "cost_mismatch"),
    (_rec(status="error", error="MemoryError"), "infra_error"),
    (_rec(status="missing_instance", instance_sha256=None), "infra_error"),
    (_rec(stop_at_oracle=False), "invalid_submission"),
    (_rec(grace_s=30.0), "invalid_submission"),
    (_rec(config={"ea": {"pop_size": 40}, "ls": {"time_limit_s": 2.5, "ls_polish_flips": 12500}}),
     "invalid_submission"),
])
def test_classify(rec, cls):
    assert res.classify(TASK, rec)[0] == cls


def test_pending_excludes_final_outcomes(tmp_path):
    man = tmp_path / "manifest_t.tsv"
    side = tmp_path / "manifest_t.tasks.csv"
    outdir = tmp_path / "tasks"
    outdir.mkdir()
    kinds = [_rec(), _rec(stop_reason="time_cap"), _rec(status="timeout", stop_reason=None),
             None, _rec(status="error"), _rec(time_to_target_s=950.0), _rec(stop_at_oracle=False)]
    rows = []
    for i, k in enumerate(kinds, 1):
        t = dict(TASK, task_id=str(i), job_id=f"j{i}")
        rows.append(t)
        if k is not None:
            (outdir / f"j{i}.jsonl").write_text(json.dumps(dict(k, job_id=f"j{i}")) + "\n")
    man.write_text("".join(f"j{i}\tx\tc\tcfg\t1\t900\t3\tT2a\tb\n" for i in range(1, 8)))
    with open(side, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(TASK))
        w.writeheader()
        w.writerows(rows)
    ev = res.evaluate(str(man), str(outdir))
    pend = [int(r["task_id"]) for r in ev if r["cls"] in res.PENDING_CLASSES]
    assert pend == [4, 5, 7]
    assert res.id_ranges([1, 2, 3, 5, 7, 8]) == "1-3,5,7-8"


def test_median_ttt_counts_failures_as_over_budget():
    assert res.med_ttt([10.0, None, 30.0]) == "30.0"
    assert res.med_ttt([10.0, None, None]) == ">900"
    assert res.med_ttt([10.0, 20.0, 30.0, None]) == "25.0"
    assert res.med_ttt([10.0, None, None, None]) == ">900"


# ---------------------------------------------------------------- deadline clipping
# All 8 sign patterns over 3 variables: every assignment falsifies exactly one
# clause, so walksat never exits early on "all satisfied" and a call runs until
# its flip or time limit -- the regime in which clipping matters.
UNSAT = "p cnf 3 8\n" + "".join(
    f"{a} {b} {c} 0\n" for a in (1, -1) for b in (2, -2) for c in (3, -3))

# run_memetic output on pilot instance #7 with the control config made
# deterministic (flip-limited calls, max_gens 2), recorded with the
# PRE-clipping memetic.py: (assignment sha256[:16], total_flips, children).
CONTROL_REF = {1: ("bd731d7910a70ea7", 22800, 76), 2: ("c73d158a7a6687f7", 22800, 76)}
INST7 = os.path.join(ROOT, "data/generated/calib_b/wksat_v70_k3_sr6.50_hr0.00_w1_uniform_s4.wcnf")


def _deterministic(arm, **ea):
    cfg = _cfg(arm)
    cfg["time_limit_s"] = 1e6
    cfg["ea"].update(max_gens=2, **ea)
    cfg["ls"]["time_limit_s"] = 1e6
    cfg["ls"]["ls_polish_flips"] = 300
    return cfg


@pytest.mark.skipif(not os.path.isfile(INST7), reason="calibration data not staged")
@pytest.mark.parametrize("seed", [1, 2])
def test_control_path_unchanged_by_clipping_code(seed):
    w = WCNF.parse_dimacs(INST7)
    r = run_memetic(w, _deterministic("p40_ls0p5"), rng_seed=seed)
    got = (hashlib.sha256(r["meta"]["assign_bits"].encode()).hexdigest()[:16],
           r["total_flips"], r["meta"]["children"])
    assert got == CONTROL_REF[seed]
    assert r["stop_reason"] == "max_gens"


@pytest.mark.skipif(not os.path.isfile(INST7), reason="calibration data not staged")
def test_clip_is_inert_when_the_budget_never_binds():
    # Same trajectory with clipping on, as long as no call is actually clipped.
    w = WCNF.parse_dimacs(INST7)
    r = run_memetic(w, _deterministic("p40_ls0p5", deadline_mode="clip"), rng_seed=1)
    assert (hashlib.sha256(r["meta"]["assign_bits"].encode()).hexdigest()[:16],
            r["total_flips"], r["meta"]["children"]) == CONTROL_REF[1]


@pytest.mark.parametrize("arm", ["p40_ls2p5", "p10_ls2p5", "p10_ls3p5"])
def test_clipped_run_ends_at_the_budget(tmp_path, arm):
    p = tmp_path / "unsat.cnf"
    p.write_text(UNSAT)
    cfg = _cfg(arm)
    cfg["time_limit_s"] = 0.3
    cfg["ls"]["ls_polish_flips"] = 10 ** 9     # make the time allowance the binding limit
    import time as _t
    t0 = _t.time()
    r = run_memetic(WCNF.parse_dimacs(str(p)), cfg, rng_seed=1)
    wall = _t.time() - t0
    # Unclipped, the first call alone would run its full 2.5 / 3.5 s allowance;
    # the 1 s margin only absorbs scheduler noise on a loaded machine.
    assert wall < 0.3 + 1.0
    assert r["stop_reason"] == "time_cap"
    assert r["meta"]["children"] >= 1 and r["meta"]["ea_generations"] == 1


def test_classifier_checks_deadline_mode():
    t = dict(TASK, deadline_mode="clip")
    assert res.classify(t, _rec())[0] == "invalid_submission"   # shard has no deadline_mode
    ok = _rec(config={"ea": {"pop_size": 10, "deadline_mode": "clip"},
                      "ls": {"time_limit_s": 2.5, "ls_polish_flips": 12500}})
    assert res.classify(t, ok)[0] == "success"
