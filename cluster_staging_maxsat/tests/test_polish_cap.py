"""Opt-in `ls.polish_cap` (src/evo/memetic.py, 2026-10-12).

`flips` (the default; also an absent key) leaves every earlier config unchanged.
`time` ends each polish call only on ls.time_limit_s, ignoring ls_polish_flips
and flip_budget. `flips_only` (2026-10-14) ends each call only on ls_polish_flips,
ignoring ls.time_limit_s. Run from inside cluster_staging_maxsat/.
"""
from __future__ import annotations

import math
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
TESTS = os.path.dirname(os.path.abspath(__file__))
if TESTS not in sys.path:
    sys.path.insert(0, TESTS)

from evo.memetic import _ls_budget, run_memetic  # noqa: E402
from test_walksat_v2 import make_wcnf  # noqa: E402

LS = {"ls_polish_flips": 50, "time_limit_s": 400, "flip_budget": 50}


@pytest.fixture()
def tick_clock(monkeypatch):
    """time.time() advancing by 1 per call: a polish time limit of L becomes an
    iteration limit, so the test is deterministic and fast."""
    state = {"t": 0.0}

    def fake():
        state["t"] += 1.0
        return state["t"]

    monkeypatch.setattr(time, "time", fake)
    return state


def test_default_and_flips_are_unchanged():
    assert _ls_budget({"ls": LS}) == {"ls_polish_flips": 50, "time_limit_s": 400.0, "max_flips": 50}
    assert _ls_budget({"ls": {**LS, "polish_cap": "flips"}}) == _ls_budget({"ls": LS})


def test_time_cap_removes_the_flip_limits():
    b = _ls_budget({"ls": {**LS, "polish_cap": "TIME"}})
    assert b["ls_polish_flips"] == b["max_flips"] == sys.maxsize
    assert b["time_limit_s"] == 400.0


def test_flips_only_removes_the_time_limit():
    b = _ls_budget({"ls": {**LS, "polish_cap": "flips_only"}})
    assert b == {"ls_polish_flips": 50, "time_limit_s": math.inf, "max_flips": 50}


def test_unknown_cap_is_refused():
    with pytest.raises(ValueError):
        _ls_budget({"ls": {**LS, "polish_cap": "both"}})


def _cfg(impl, cap=None):
    ls = dict(LS, **({"polish_cap": cap} if cap else {}))
    return {"impl": impl, "time_limit_s": 10**9,
            "ea": {"enabled": True, "pop_size": 6, "tournament_k": 3, "pmutate": 0.02,
                   "elitism": True, "max_gens": 2, "deadline_mode": "clip"},
            "ls": ls}


@pytest.mark.parametrize("impl", ["v1", "v2"])
def test_flips_cap_matches_absent_key(tmp_path, tick_clock, impl):
    cnf = make_wcnf(tmp_path, "cap", 60, 2, 400, seed=5)  # dense Max-2-SAT: never all satisfied
    r0 = run_memetic(cnf, _cfg(impl), rng_seed=3)
    r1 = run_memetic(cnf, _cfg(impl, "flips"), rng_seed=3)
    assert r0["meta"]["assign_bits"] == r1["meta"]["assign_bits"]
    assert r0["total_flips"] == r1["total_flips"]


@pytest.mark.parametrize("impl", ["v1", "v2"])
def test_time_cap_runs_past_the_flip_limit(tmp_path, tick_clock, impl):
    cnf = make_wcnf(tmp_path, "cap", 60, 2, 400, seed=5)
    rf = run_memetic(cnf, _cfg(impl, "flips"), rng_seed=3)
    rt = run_memetic(cnf, _cfg(impl, "time"), rng_seed=3)
    children = rt["meta"]["children"]
    assert rf["total_flips"] <= 50 * rf["meta"]["children"]
    # Each time-capped call ran to its 400-tick limit, far beyond 50 flips.
    assert rt["total_flips"] > 300 * children


@pytest.mark.parametrize("impl", ["v1", "v2"])
def test_flips_only_runs_past_the_time_limit(tmp_path, tick_clock, impl):
    cnf = make_wcnf(tmp_path, "cap", 60, 2, 400, seed=5)
    ls = {"ls_polish_flips": 300, "flip_budget": 300, "time_limit_s": 5}
    cfg = dict(_cfg(impl), ls=ls)
    rf = run_memetic(cnf, cfg, rng_seed=3)
    ro = run_memetic(cnf, dict(cfg, ls=dict(ls, polish_cap="flips_only")), rng_seed=3)
    # Default: the 5-tick limit ends each call long before 300 flips.
    assert rf["total_flips"] < 10 * rf["meta"]["children"]
    # flips_only: every call runs its full 300 flips (the formula is never satisfied).
    assert ro["total_flips"] == 300 * ro["meta"]["children"]


@pytest.mark.parametrize("impl", ["v1", "v2"])
def test_flips_only_still_respects_the_run_budget(tmp_path, tick_clock, impl):
    cnf = make_wcnf(tmp_path, "cap", 60, 2, 400, seed=5)
    ls = {"ls_polish_flips": 10**9, "flip_budget": 10**9, "time_limit_s": 5,
          "polish_cap": "flips_only"}
    cfg = dict(_cfg(impl), time_limit_s=2000, ls=ls)
    r = run_memetic(cnf, cfg, rng_seed=3)
    # Deadline clipping ends the endless first call on the run budget.
    assert r["stop_reason"] == "time_cap"
    assert r["total_flips"] < 10**9
