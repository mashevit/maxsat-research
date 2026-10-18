"""calib_2sat_sc2 memetic assessment preparation (docs/current/CALIB_2SAT_SC.md §13b, repo).

Covers the §6 selection (eligible instances of promising cells only, every other
instance accounted for), the identity of the v2 arm with the pre-registered
primary arm apart from `impl`, the `memetic_impl` check in m2_results.py, and
the reproducibility of the written manifest. Run from inside cluster_staging_maxsat/.
"""
from __future__ import annotations

import os
import sys

import pytest

STAGING = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(STAGING, "scripts"))
import make_calib_2sat_sc_memetic_manifest as sc  # noqa: E402
import make_m2_manifests as m2  # noqa: E402
import m2_results  # noqa: E402


def _inst(cell, seed, cls, s="100.0", c="12"):
    return {"cell_id": cell, "gen_seed": str(seed), "instance": f"data/x_s{seed}.wcnf",
            "instance_sha256": f"{seed:064x}", "m": "19200", "class": cls, "rc2_status": "optimal",
            "solve_s": s, "c_star": c, "lower_bound": ""}


def _cell(cell, outcome, failed="0"):
    return {"cell_id": cell, "outcome": outcome, "failed": failed}


def test_select_runs_only_eligible_of_promising_cells_and_accounts_for_the_rest():
    insts = [_inst("B", 12, "eligible", "171.6", "13"), _inst("B", 11, "eligible", "65.0"),
             _inst("B", 13, "fast", "7.7"), _inst("A", 1, "eligible", "500.0"),  # A is not promising
             _inst("A", 2, "censored", "", "")]
    elig, not_run = sc.select(insts, [_cell("A", "mixed"), _cell("B", "promising")])
    assert [(e["gen_seed"], e["pop_idx"]) for e in elig] == [(11, "sc01"), (12, "sc02")]
    assert elig[1]["oracle_cost"] == 13 and elig[0]["analysis_group"] == "tier2"
    assert sorted(r["gen_seed"] for r in not_run) == ["1", "13", "2"]
    assert len(elig) + len(not_run) == len(insts)


def test_select_refuses_failed_or_incomplete_cells():
    with pytest.raises(SystemExit):
        sc.select([_inst("B", 1, "eligible")], [_cell("B", "incomplete")])
    with pytest.raises(SystemExit):
        sc.select([_inst("B", 1, "eligible")], [_cell("B", "promising", failed="1")])


def test_arms_are_the_primary_arm_plus_impl_and_flip_limit_only(monkeypatch):
    sc.check_arm()  # the real configs
    real = m2.load_config
    f200k = sc.ARMS["p40_ls3p5_f200k_v2"][0]

    def fake(bad):
        def load(path):
            cfg = real(path)
            if path == f200k:
                cfg = dict(cfg, ls=dict(cfg["ls"], **bad))
            return cfg
        return load
    for bad in ({"time_limit_s": 1.0}, {"flip_budget": 12500}, {"ls_polish_flips": 100000}):
        monkeypatch.setattr(m2, "load_config", fake(bad))
        with pytest.raises(SystemExit):
            sc.check_arm()


def test_tasks_pair_both_arms_with_the_pre_registered_settings():
    elig, _ = sc.select([_inst("B", 11, "eligible", "65.0")], [_cell("B", "promising")])
    for e in elig:
        e["rc2_tier"] = "T2a"
    tasks = sc.tasks_for(elig)
    assert [(t["solver_seed"], t["ls_polish_flips"]) for t in tasks] == [
        (1, 12500), (1, 200000), (2, 12500), (2, 200000), (3, 12500), (3, 200000)]
    assert {(t["memetic_impl"], t["budget_s"], t["pop_size"], t["ls_time_limit_s"], t["deadline_mode"])
            for t in tasks} == {("v2", 900, 40, 3.5, "clip")}
    assert len({t["job_id"] for t in tasks}) == 6
    side = sc.render(tasks)[".tasks.csv"].splitlines()
    assert side[0].endswith(",memetic_impl,ls_polish_flips") and side[2].endswith(",v2,200000")


def _task(impl=None, flips=None):
    t = {"job_id": "j", "config_id": "c", "solver_seed": "1", "instance_sha256": "h", "budget_s": "900",
         "oracle_cost": "12", "pop_size": "40", "ls_time_limit_s": "3.5", "deadline_mode": "clip"}
    if impl is not None:
        t["memetic_impl"] = impl
    if flips is not None:
        t["ls_polish_flips"] = str(flips)
    return t


def _shard(impl=None, cfg_impl=None, flips=12500):
    cfg = {"ea": {"pop_size": 40, "deadline_mode": "clip"}, "ls": {"time_limit_s": 3.5, "ls_polish_flips": flips}}
    if cfg_impl:
        cfg["impl"] = cfg_impl
    r = {"job_id": "j", "config_id": "c", "seed": 1, "instance_sha256": "h", "budget_s": 900.0, "grace_s": 60.0,
         "stop_at_oracle": True, "oracle_cost": 12, "config": cfg}
    if impl is not None:
        r["memetic_impl"] = impl
    return r


@pytest.mark.parametrize("task,shard,ok", [
    (_task("v2"), _shard("v2", "v2"), True),
    (_task("v2"), _shard("v1"), False),          # a v1 run under the v2 manifest
    (_task("v2"), _shard(), False),              # a pre-schema-3 shard cannot claim v2
    (_task(), _shard(), True),                   # historical M2: neither side has impl
    (_task(), _shard("v1"), True),
    (_task(), _shard("v2", "v2"), False),        # a v2 run under a v1 manifest
    (_task("v2", 200000), _shard("v2", "v2", 200000), True),
    (_task("v2", 200000), _shard("v2", "v2"), False),   # 12,500-flip run under the 200k arm
    (_task("v2", 12500), _shard("v2", "v2", 200000), False),
    (_task(), _shard(flips=200000), False),      # historical manifests still require 12,500
])
def test_m2_results_checks_memetic_impl(task, shard, ok):
    assert (m2_results.mismatch(task, shard) is None) == ok


def test_paired_sorts_prefixed_pop_idx():
    rows = [{"pop_idx": p, "instance": "i", "analysis_group": "tier2", "solver_seed": "1", "arm": "a",
             "cls": "success", "success_ttt_s": 1.0} for p in ("sc02", "sc01")]
    assert [r["pop_idx"] for r in m2_results.paired(rows)] == ["sc01", "sc02"]


def test_written_manifest_is_reproducible(monkeypatch):
    monkeypatch.chdir(STAGING)
    if not os.path.isfile(os.path.join("results", sc.BATCH, "instances.csv")):
        pytest.skip("calib_2sat_sc2 readout not present")
    assert sc.main(["--check"]) == 0


# --- HP-1 Stage L1 c grid (--plan cgrid; HYPERPARAMETER_CALIBRATION_PLAN.md §0b/§0c) ---

def test_cgrid_arms_differ_only_in_flips_and_polish_cap(monkeypatch):
    sc.check_arm(sc.CGRID_ARMS)  # the real configs
    real = m2.load_config
    f800k = sc.CGRID_ARMS["p40_f800k_fonly_v2"][0]

    def fake(bad):
        def load(path):
            cfg = real(path)
            if path == f800k:
                cfg = dict(cfg, ls={k: v for k, v in dict(cfg["ls"], **bad).items() if v is not None})
            return cfg
        return load
    for bad in ({"polish_cap": None}, {"polish_cap": "time"}, {"time_limit_s": 60.0}, {"flip_budget": 12500}):
        monkeypatch.setattr(m2, "load_config", fake(bad))
        with pytest.raises(SystemExit):
            sc.check_arm(sc.CGRID_ARMS)


def test_cgrid_tasks_pair_six_arms():
    elig, _ = sc.select([_inst("B", 11, "eligible", "65.0")], [_cell("B", "promising")])
    for e in elig:
        e["rc2_tier"] = "T2a"
    stem, arms, extra, prefix = sc.PLANS["cgrid"]
    tasks = sc.tasks_for(elig, arms, prefix)
    assert len(tasks) == 18 and len({t["job_id"] for t in tasks}) == 18
    assert [(t["ls_polish_flips"], t["ls_polish_cap"]) for t in tasks[:6]] == [
        (200000, "flips_only"), (400000, "flips_only"), (800000, "flips_only"),
        (1600000, "flips_only"), (3200000, "flips_only"), (12500, "time")]
    assert {t["solver_seed"] for t in tasks[:6]} == {1}
    side = sc.render(tasks, extra)[".tasks.csv"].splitlines()
    assert side[0].endswith(",memetic_impl,ls_polish_flips,ls_polish_cap")
    assert side[6].endswith(",v2,12500,time")


@pytest.mark.parametrize("cap_task,cap_cfg,ok", [
    (None, None, True),               # every earlier manifest and shard
    ("flips_only", "flips_only", True),
    ("time", "TIME", True),
    ("flips_only", None, False),      # a default-cap run under a flips_only arm
    (None, "flips_only", False),      # a flips_only run under a historical manifest
    ("time", "flips_only", False),
])
def test_m2_results_checks_polish_cap(cap_task, cap_cfg, ok):
    t, r = _task("v2"), _shard("v2", "v2")
    if cap_task:
        t["ls_polish_cap"] = cap_task
    if cap_cfg:
        r["config"]["ls"]["polish_cap"] = cap_cfg
    assert (m2_results.mismatch(t, r) is None) == ok


def test_written_cgrid_manifest_is_reproducible(monkeypatch):
    monkeypatch.chdir(STAGING)
    if not os.path.isfile(os.path.join("results", sc.BATCH, "instances.csv")):
        pytest.skip("calib_2sat_sc2 readout not present")
    assert sc.main(["--plan", "cgrid", "--check"]) == 0


# --- HP-1 Stage L1b time grid (--plan tgrid; HYPERPARAMETER_CALIBRATION_PLAN.md §0d) ---

def test_tgrid_arms_differ_only_in_time_limit(monkeypatch):
    sc.check_arm(sc.TGRID_ARMS)  # the real configs
    real = m2.load_config
    ls10 = sc.TGRID_ARMS["p40_ls10_tcap_v2"][0]

    def fake(bad):
        def load(path):
            cfg = real(path)
            if path == ls10:
                cfg = dict(cfg, ls={k: v for k, v in dict(cfg["ls"], **bad).items() if v is not None})
            return cfg
        return load
    for bad in ({"polish_cap": None}, {"polish_cap": "flips"}, {"time_limit_s": 3.5},
                {"time_limit_s": 15.0}, {"flip_budget": 200000}):
        monkeypatch.setattr(m2, "load_config", fake(bad))
        with pytest.raises(SystemExit):
            sc.check_arm(sc.TGRID_ARMS)


def test_tgrid_tasks_pair_four_time_arms():
    elig, _ = sc.select([_inst("B", 11, "eligible", "65.0")], [_cell("B", "promising")])
    for e in elig:
        e["rc2_tier"] = "T2a"
    stem, arms, extra, prefix = sc.PLANS["tgrid"]
    tasks = sc.tasks_for(elig, arms, prefix)
    assert len(tasks) == 12 and len({t["job_id"] for t in tasks}) == 12
    assert [(t["ls_time_limit_s"], t["ls_polish_cap"]) for t in tasks[:4]] == [
        (6.0, "time"), (8.0, "time"), (10.0, "time"), (15.0, "time")]
    assert [t["job_id"] for t in tasks[:4]] == [
        "sc2tg_t6tc_01_s1", "sc2tg_t8tc_01_s1", "sc2tg_t10tc_01_s1", "sc2tg_t15tc_01_s1"]
    assert {t["deadline_mode"] for t in tasks} == {"clip"}


@pytest.mark.parametrize("t_task,t_cfg,ok", [(10.0, 10.0, True), (10.0, 3.5, False), (3.5, 10.0, False)])
def test_m2_results_checks_time_limit(t_task, t_cfg, ok):
    t, r = _task("v2"), _shard("v2", "v2")
    t["ls_polish_cap"] = "time"
    r["config"]["ls"]["polish_cap"] = "time"
    t["ls_time_limit_s"] = t_task
    r["config"]["ls"]["time_limit_s"] = t_cfg
    assert (m2_results.mismatch(t, r) is None) == ok


def test_written_tgrid_manifest_is_reproducible(monkeypatch):
    monkeypatch.chdir(STAGING)
    if not os.path.isfile(os.path.join("results", sc.BATCH, "instances.csv")):
        pytest.skip("calib_2sat_sc2 readout not present")
    assert sc.main(["--plan", "tgrid", "--check"]) == 0


# --- direction A: kernelised memetic (--plan kern; RESEARCH_NOTES_SOLVER_DIRECTIONS.md §8) ---

def test_kern_arm_is_the_v2_arm_plus_preprocessing_only(monkeypatch):
    sc.check_arm(sc.KERN_ARMS)  # the real config
    real = m2.load_config
    path = sc.KERN_ARMS["p40_ls3p5_kern_v2"][0]

    def fake(change):
        def load(p):
            cfg = real(p)
            if p == path:
                cfg = {k: v for k, v in dict(cfg, **change).items() if v is not None}
            return cfg
        return load
    for change in ({"preprocess": None}, {"preprocess_gate": {"screen_min": 0.1, "gain_min": 0.2}},
                   {"preprocess_gate": None}, {"ls": {"ls_polish_flips": 200000}}):
        monkeypatch.setattr(m2, "load_config", fake(change))
        with pytest.raises(SystemExit):
            sc.check_arm(sc.KERN_ARMS)


def test_kern_tasks_carry_the_preprocess_column():
    elig, _ = sc.select([_inst("B", 11, "eligible", "65.0")], [_cell("B", "promising")])
    for e in elig:
        e["rc2_tier"] = "T2a"
    stem, arms, extra, prefix = sc.PLANS["kern"]
    tasks = sc.tasks_for(elig, arms, prefix)
    assert [t["job_id"] for t in tasks] == ["sc2kn_ls3p5_01_s1", "sc2kn_ls3p5_01_s2", "sc2kn_ls3p5_01_s3"]
    assert {(t["preprocess"], t["ls_polish_flips"], t["ls_polish_cap"]) for t in tasks} == {("kernel", 12500, "flips")}
    side = sc.render(tasks, extra)[".tasks.csv"].splitlines()
    assert side[0].endswith(",ls_polish_cap,preprocess") and side[1].endswith(",v2,12500,flips,kernel")
    # every other plan's tasks leave it empty, and their sidecars do not have the column
    assert {t["preprocess"] for t in sc.tasks_for(elig)} == {""}


@pytest.mark.parametrize("pre_task,pre_cfg,ok", [
    (None, None, True),          # every earlier manifest and shard
    (None, "none", True),
    ("kernel", "kernel", True),
    ("kernel", None, False),     # a raw run under the kernel arm
    (None, "kernel", False),     # a kernel run under a raw manifest
])
def test_m2_results_checks_preprocess(pre_task, pre_cfg, ok):
    t, r = _task("v2"), _shard("v2", "v2")
    if pre_task:
        t["preprocess"] = pre_task
    if pre_cfg:
        r["config"]["preprocess"] = pre_cfg
    assert (m2_results.mismatch(t, r) is None) == ok


def test_written_kern_manifest_is_reproducible(monkeypatch):
    monkeypatch.chdir(STAGING)
    if not os.path.isfile(os.path.join("results", sc.BATCH, "instances.csv")):
        pytest.skip("calib_2sat_sc2 readout not present")
    assert sc.main(["--plan", "kern", "--check"]) == 0
