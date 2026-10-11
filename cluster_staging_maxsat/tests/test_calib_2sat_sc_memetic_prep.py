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
