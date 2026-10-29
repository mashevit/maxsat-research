"""3b: the target-hit counter (docs/current2/MSE26_RHO_PLAN.md §7).

- the C cores and their Python twins report the same hit step, and the target
  changes no flip (same assignment and counters with and without it);
- the hit step is the FIRST step at which the true cost reached the target: a
  call cut at that step reaches it, a call cut one step earlier does not;
- the memetic's `target_hit` is consistent with its own counters
  (calls_to_target == children, flips_to_target <= total_flips,
  time_to_hit_s <= time_to_target_s);
- the shard record (schema 7) carries the fields and `peak_rss_mb`;
- schema 8 (MSE26_RHO_PLAN.md §9): whole-process CPU / wall fields, and
  `--budget-clock process` changes no decision while the budget does not bind.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
sys.path.insert(0, HERE)

from sat.ls_v3 import dls_v3, walksat_v3  # noqa: E402
from sat.rng import PortableRng  # noqa: E402
from test_native import CASES, KEYS, make_wcnf, pytestmark, start  # noqa: E402,F401


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    d = tmp_path_factory.mktemp("native_build_hit")
    env = dict(os.environ, MAXSAT_NATIVE_BUILD_DIR=str(d))
    subprocess.run(["bash", os.path.join(TREE, "scripts", "build_native.sh")], check=True, env=env,
                   capture_output=True)
    old = os.environ.get("MAXSAT_NATIVE_BUILD_DIR")
    os.environ["MAXSAT_NATIVE_BUILD_DIR"] = str(d)
    import native.native as nat
    nat._LIB = None
    yield nat
    nat._LIB = None
    if old is None:
        os.environ.pop("MAXSAT_NATIVE_BUILD_DIR", None)
    else:
        os.environ["MAXSAT_NATIVE_BUILD_DIR"] = old


def unsat_of(res, total_soft):
    return None if res["hard_violations"] else total_soft - res["best_soft_weight"]


def reached(res, total_soft, target):
    u = unsat_of(res, total_soft)
    return u is not None and u <= target


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("core", ["walksat", "dls"])
def test_hit_step_c_equals_twin_and_search_unchanged(native, tmp_path, case, core):
    w = make_wcnf(tmp_path, "h", seed=11, **case)
    nc = native.NativeCore(w)
    hits = 0
    for seed in range(4):
        s0 = start(case["n"], 90 + seed)
        if core == "dls":
            def py(tgt, mf=700):
                return dls_v3(w, s0, rng=PortableRng(seed), max_flips=mf, time_limit_s=None, cc=True,
                              target_unsat=tgt)

            def c(tgt, mf=700):
                return nc.dls(s0, seed, mf, None, cc=True, target_unsat=tgt)
        else:
            def py(tgt, mf=700):
                return walksat_v3(w, s0, rng=PortableRng(seed), max_flips=mf, time_limit_s=None,
                                  noise=0.15, budget_counts_noops=True, tabu="cc", target_unsat=tgt)

            def c(tgt, mf=700):
                return nc.walksat(s0, seed, mf, None, noise=0.15, budget_counts_noops=True, tabu="cc",
                                  target_unsat=tgt)
        free = c(None)
        assert free["target_hit_step"] == -1 and free["target_hit_wall"] is None
        u = unsat_of(free, nc.total_soft)
        if u is None:
            continue
        for tgt in (int(u), int(u) + 3):   # the call's best (reached), and an easier target
            a, b = py(tgt), c(tgt)
            for k in KEYS:
                assert a[k] == b[k] == free[k], (k, seed, tgt)
            h = b["target_hit_step"]
            assert a["target_hit_step"] == h >= 0
            assert b["target_hit_wall"] is not None
            hits += 1
            # first step: cut at h reaches it, cut at h - 1 does not
            if h > 0:
                assert reached(c(None, h), nc.total_soft, tgt)
                assert not reached(c(None, h - 1), nc.total_soft, tgt)
            else:
                assert reached(c(None, 0), nc.total_soft, tgt)
        # an unreachable target is never hit
        assert c(-5)["target_hit_step"] == -1
    assert hits > 0


def small_cfg(native_on: bool, hard: bool = False):
    return {"impl": "v3", "hard_mode": "auto" if hard else "off",
            "ea": {"pop_size": 6, "max_gens": 400, "deadline_mode": "clip", "crossover": "px",
                   "mutation": "walk", "mutation_k": 4},
            "ls": {"ls_polish_flips": 60, "flip_budget": 60, "time_limit_s": 1.0, "core": "dls",
                   "tabu": "cc", "native": native_on},
            "time_limit_s": 20.0}


def best_known(native, w):
    nc = native.NativeCore(w)
    best = None
    for seed in range(6):
        r = nc.dls(start(w.n_vars, seed), seed, 20000, None, cc=True)
        u = unsat_of(r, nc.total_soft)
        if u is not None and (best is None or u < best):
            best = int(u)
    return best


@pytest.mark.parametrize("native_on", [True, False])
@pytest.mark.parametrize("case", [dict(n=70, k=2, m_soft=260), dict(n=50, k=3, m_soft=240, w_max=4),
                                  dict(n=40, k=3, m_soft=140, m_hard=25, w_max=3)])
def test_memetic_target_hit_is_consistent(native, tmp_path, native_on, case):
    from evo.memetic import run_memetic
    w = make_wcnf(tmp_path, "m", seed=21, **case)
    target = best_known(native, w)
    assert target is not None
    by = set()
    for seed in range(1, 6):
        r = run_memetic(w, small_cfg(native_on, hard=bool(case.get("m_hard"))), rng_seed=seed,
                        target_cost=target)
        if r["stop_reason"] != "target":   # a miss on these small budgets: no hit record
            assert r["target_hit"] is None
            continue
        th = r["target_hit"]
        assert th["resolution"] == "flip" and th["target_by"] in ("init", "pre_polish", "polish")
        by.add(th["target_by"])
        if th["target_by"] == "init":
            assert th["calls_to_target"] == 0 and th["flips_to_target"] == 0
            continue
        assert th["calls_to_target"] == r["meta"]["children"]
        assert 0 <= th["flips_to_target"] <= r["total_flips"]
        assert 0 <= th["time_to_hit_s"] <= r["time_to_target_s"]
    # In hard mode a child can enter its call already at the target (SAT moves), and
    # which happens first depends on timing; either way the hit is flip-resolved.
    assert by & {"polish", "pre_polish"}


def test_memetic_without_target_has_no_hit(native, tmp_path):
    from evo.memetic import run_memetic
    w = make_wcnf(tmp_path, "z", n=40, k=2, m_soft=120, seed=2)
    cfg = small_cfg(True)
    cfg["ea"]["max_gens"] = 3
    r = run_memetic(w, cfg, rng_seed=1, target_cost=None)
    assert r["target_hit"] is None and r["stop_reason"] == "max_gens"


def test_shard_record_schema7(native, tmp_path):
    import yaml
    from cli import run_memetic_shard as shard
    w = make_wcnf(tmp_path, "s", n=60, k=2, m_soft=220, seed=4)
    target = best_known(native, w)
    cp = tmp_path / "c.yaml"
    cp.write_text(yaml.safe_dump(small_cfg(True)))
    path = str(tmp_path / "s.wcnf")
    out = tmp_path / "o.jsonl"
    base = ["--instance", path, "--config", str(cp), "--seed", "2", "--budget-s", "20"]
    assert shard.main(base + ["--oracle-cost", str(target), "--stop-at-oracle", "--out", str(out)]) == 0
    r = json.loads(out.read_text().strip().splitlines()[-1])
    assert r["schema_version"] == 8 and r["status"] == "ok" and r["stop_reason"] == "target"
    assert r["ttt_resolution"] == "flip" and r["target_by"] in ("init", "pre_polish", "polish")
    assert r["flips_to_target"] <= r["total_flips"]
    assert r["time_to_target_hit_s"] <= r["time_to_target_s"] + 1e-3
    assert r["peak_rss_mb"] > 0
    out2 = tmp_path / "o2.jsonl"
    assert shard.main(base + ["--out", str(out2)]) == 0
    r2 = json.loads(out2.read_text().strip().splitlines()[-1])
    for k in ("calls_to_target", "flips_to_target", "target_by", "ttt_resolution", "time_to_target_hit_s"):
        assert r2[k] is None
    assert r2["peak_rss_mb"] > 0


def test_memetic_cpu_at_target(native, tmp_path):
    from evo.memetic import run_memetic
    w = make_wcnf(tmp_path, "c", n=60, k=2, m_soft=220, seed=4)
    target = best_known(native, w)
    r = run_memetic(w, small_cfg(True), rng_seed=2, target_cost=target)
    assert r["stop_reason"] == "target" and 0 < r["cpu_at_target_s"]
    r2 = run_memetic(w, dict(small_cfg(True), ea=dict(small_cfg(True)["ea"], max_gens=2)), rng_seed=2, target_cost=None)
    assert r2["cpu_at_target_s"] is None


def _shard_subprocess(tmp_path, name, extra):
    """The shard as its own process, so the process clocks start with it."""
    out = tmp_path / f"{name}.jsonl"
    subprocess.run([sys.executable, os.path.join(SRC, "cli", "run_memetic_shard.py")] + extra + ["--out", str(out)],
                   check=True, capture_output=True, cwd=TREE)
    return json.loads(out.read_text().strip().splitlines()[-1])


def test_shard_record_schema8_process_clock(native, tmp_path):
    import yaml
    w = make_wcnf(tmp_path, "p", n=60, k=2, m_soft=220, seed=4)
    target = best_known(native, w)
    cp = tmp_path / "c.yaml"
    cp.write_text(yaml.safe_dump(small_cfg(True)))
    base = ["--instance", str(tmp_path / "p.wcnf"), "--config", str(cp), "--seed", "2", "--budget-s", "20",
            "--oracle-cost", str(target), "--stop-at-oracle"]
    run = _shard_subprocess(tmp_path, "run", base)
    proc = _shard_subprocess(tmp_path, "proc", base + ["--budget-clock", "process"])
    for r, clock in ((run, "run"), (proc, "process")):
        assert r["schema_version"] == 8 and r["status"] == "ok" and r["stop_reason"] == "target"
        assert r["budget_clock"] == clock
        assert r["hash_s"] >= 0 and r["parse_s"] >= 0
        assert 0 < r["solver_start_s"] <= r["wall_total_s"]
        assert 0 < r["cpu_to_target_s"] <= r["cpu_total_s"]
        assert r["cpu_to_target_hit_s"] <= r["cpu_to_target_s"]
    # the process clock leaves less for the solver, and decides nothing else here
    assert proc["solver_time_limit_s"] < 20.0
    for k in ("best_assignment_hash", "total_flips", "flips_to_target", "calls_to_target", "target_by", "children"):
        assert run[k] == proc[k], k


def test_shard_process_clock_budget_binds(native, tmp_path):
    """With the process clock the whole run, start-up included, stays within budget + overshoot."""
    import yaml
    w = make_wcnf(tmp_path, "b", n=400, k=3, m_soft=2000, seed=5)
    cp = tmp_path / "c.yaml"
    cp.write_text(yaml.safe_dump(small_cfg(True)))
    r = _shard_subprocess(tmp_path, "b", ["--instance", str(tmp_path / "b.wcnf"), "--config", str(cp),
                                          "--seed", "1", "--budget-s", "3", "--budget-clock", "process"])
    assert r["status"] == "ok" and r["stop_reason"] in ("time_cap", "max_gens")
    assert r["cpu_to_target_s"] is None
    assert r["solver_time_limit_s"] < 3.0 and r["wall_total_s"] < 3.0 + 2.5
