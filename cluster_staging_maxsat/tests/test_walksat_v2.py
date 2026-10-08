"""walksat_polish_v2 (src/sat/walksat_v2.py) against v1 (src/sat/walksat.py).

The claim under test: with the same start assignment, seed and flip budget and
no time limit, v2 makes exactly v1's decisions -- same final assignment, same
flip counts, same objective -- on instances whose clauses have no repeated
variable. Covered: soft-only 2-SAT and 3-SAT, weighted soft, hard+soft (the
hard-violation branch and its explore fallback), high noise, hard_safe off,
duplicate clauses. Plus: crossover v2 equals v1, and the memetic EA gives identical
results with `impl: v1` and `impl: v2` when every polish call is flip-limited, and v2 stays internally
consistent on clauses with a repeated variable (where it is exact and v1 is not).

Instances are generated here; nothing under data/ is needed. Run from inside
cluster_staging_maxsat/.
"""
from __future__ import annotations

import os
import random
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
from sat.walksat import walksat_polish  # noqa: E402
from sat.walksat_v2 import walksat_polish_v2  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.impl_v2 import (clause_aware_crossover1_v2, memetic_impl, select_crossover,  # noqa: E402
                         select_polish, short_polish_v2)
from evo.operators import clause_aware_crossover1  # noqa: E402
from evo.population import Individual  # noqa: E402
from evo.operators import short_polish  # noqa: E402


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, seed=0, repeat_var=False):
    rng = random.Random(seed)
    top = m_soft * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        vs = rng.sample(range(1, n + 1), k)
        if repeat_var and i % 7 == 0:
            vs[-1] = vs[0]  # a repeated variable (same or opposite sign)
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(1, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return WCNF.parse_dimacs(str(path))


@pytest.fixture()
def tick_clock(monkeypatch):
    """time.time() advancing by exactly 1 per call. v1 and v2 both read the clock
    once at start, once per loop test and once at the end, so a time limit of L
    "seconds" stops both after the same number of iterations. This also ends the
    runs where no candidate may flip (hard_safe with stuck hard clauses): v1
    counts only applied flips against max_flips and would otherwise loop forever,
    and v2 reproduces that loop condition."""
    state = {"t": 0.0}

    def fake():
        state["t"] += 1.0
        return state["t"]

    monkeypatch.setattr(time, "time", fake)
    return state


def start(n, seed):
    r = random.Random(seed)
    return [r.random() < 0.5 for _ in range(n)]


CASES = [
    # name, n, k, m_soft, m_hard, w_max
    ("2sat_soft", 300, 2, 420, 0, 1),
    ("3sat_soft", 120, 3, 560, 0, 1),
    ("3sat_weighted", 100, 3, 450, 0, 9),
    ("hard_and_soft", 80, 3, 200, 300, 5),
    ("2sat_dense_dups", 30, 2, 400, 0, 1),  # many duplicate clauses
]


@pytest.mark.parametrize("name,n,k,ms,mh,wm", CASES)
@pytest.mark.parametrize("noise,hard_safe", [(0.10, True), (0.5, True), (0.3, False)])
@pytest.mark.parametrize("seed", [1, 7, 12345])
def test_v2_matches_v1(tmp_path, tick_clock, name, n, k, ms, mh, wm, noise, hard_safe, seed):
    cnf = make_wcnf(tmp_path, name, n, k, ms, mh, wm, seed=seed)
    s0 = start(n, seed + 1)
    # flip budget and an iteration budget (1200 ticks); whichever ends first
    kw = dict(rng_seed=seed, max_flips=1000, time_limit_s=1200, noise=noise, hard_safe=hard_safe)
    a = walksat_polish(cnf, list(s0), **kw)
    b = walksat_polish_v2(cnf, list(s0), **kw)
    assert b["final_assign"] == a["final_assign"]
    for key in ("flips", "total_flips", "hard_violations", "best_soft_weight"):
        assert b[key] == a[key], key


def test_v2_matches_v1_when_already_satisfied(tmp_path, tick_clock):
    """No unsatisfied clause at the start: both stop at once (target == -1)."""
    cnf = make_wcnf(tmp_path, "easy", 50, 3, 20, seed=3)
    s0 = start(50, 4)
    # make every clause true by setting each clause's first literal
    for cl in cnf.clauses:
        lit = cl.lits[0]
        s0[abs(lit) - 1] = lit > 0
    kw = dict(rng_seed=5, max_flips=100, time_limit_s=1000)
    a, b = walksat_polish(cnf, list(s0), **kw), walksat_polish_v2(cnf, list(s0), **kw)
    assert b["final_assign"] == a["final_assign"] and b["flips"] == a["flips"] == 1


def _recount(cnf, assign0):
    a = [False] + list(assign0)
    unsat_soft_w, hv = 0, 0
    for cl in cnf.clauses:
        sat = any((l > 0) == a[abs(l)] for l in cl.lits)
        if not sat:
            if cl.is_hard:
                hv += 1
            else:
                unsat_soft_w += cl.weight
    return unsat_soft_w, hv


def test_v2_consistent_with_repeated_variables(tmp_path):
    """Clauses with a repeated variable: v2's reported objective must equal a
    from-scratch recount of the assignment it returns."""
    cnf = make_wcnf(tmp_path, "rep", 60, 3, 300, seed=11, repeat_var=True)
    total = sum(cl.weight for cl in cnf.clauses if not cl.is_hard)
    res = walksat_polish_v2(cnf, start(60, 2), rng_seed=3, max_flips=3000, time_limit_s=None)
    unsat_w, hv = _recount(cnf, res["final_assign"])
    assert hv == res["hard_violations"] == 0
    assert total - unsat_w == res["best_soft_weight"]


def test_short_polish_v2_matches_short_polish(tmp_path, tick_clock):
    cnf = make_wcnf(tmp_path, "sp", 200, 2, 260, seed=21)
    a01 = [False] + start(200, 22)
    ls = {"ls_polish_flips": 800, "time_limit_s": 900, "max_flips": 800}
    assert short_polish_v2(list(a01), cnf, ls, 9) == short_polish(list(a01), cnf, ls, 9)


def test_impl_selection():
    assert memetic_impl({}) == "v1"
    assert select_polish({}) is short_polish and select_crossover({}) is clause_aware_crossover1
    assert memetic_impl({"impl": "V2"}) == "v2"
    assert select_polish({"impl": "v2"}) is short_polish_v2
    assert select_crossover({"impl": "v2"}) is clause_aware_crossover1_v2
    with pytest.raises(ValueError, match="impl must be one of"):
        memetic_impl({"impl": "v3"})


@pytest.mark.parametrize("ms,mh,wm", [(300, 0, 1), (200, 250, 5), (150, 0, 7)])
@pytest.mark.parametrize("seed", [2, 9])
def test_crossover_v2_matches_v1(tmp_path, ms, mh, wm, seed):
    """Same child from the same parents, soft-only and hard+soft; called twice
    so the second call runs on the cached statics."""
    cnf = make_wcnf(tmp_path, f"xo{ms}_{mh}", 120, 3, ms, mh, wm, seed=seed)
    for rep in range(3):
        p1 = Individual(assign01=[False] + start(120, seed * 10 + rep))
        p2 = Individual(assign01=[False] + start(120, seed * 10 + rep + 5))
        p1.fitness, p2.fitness = float(rep), float(2 - rep)  # both orders and a tie
        a = clause_aware_crossover1(p1, p2, cnf, random.Random(1))
        b = clause_aware_crossover1_v2(p1, p2, cnf, random.Random(1))
        assert a == b


@pytest.mark.parametrize("k,ms,mh,wm,clip", [(2, 200, 0, 1, False), (3, 260, 120, 4, True)])
def test_memetic_identical_under_v1_and_v2_when_flip_limited(tmp_path, tick_clock, k, ms, mh, wm, clip):
    """Whole EA, polish limited by flips or by a tick budget, and a huge run cap:
    v1 and v2 runs agree. Second case: hard+soft clauses and the established
    arm's deadline clipping. The tick clock makes the polish's time limit an
    iteration limit, identical in both paths (each makes the same clock calls)."""
    cnf = make_wcnf(tmp_path, f"ea{k}", 150, k, ms, mh, wm, seed=31)
    base = {
        "time_limit_s": 10**9,
        "ea": {"enabled": True, "pop_size": 6, "tournament_k": 3, "pmutate": 0.02,
               "elitism": True, "max_gens": 3, **({"deadline_mode": "clip"} if clip else {})},
        "ls": {"ls_polish_flips": 300, "time_limit_s": 400, "flip_budget": 300},
    }
    v2cfg = {**base, "impl": "v2"}
    r1 = run_memetic(cnf, base, rng_seed=4)
    r2 = run_memetic(cnf, v2cfg, rng_seed=4)
    assert r1["impl"] == "v1" and r2["impl"] == "v2"
    assert r1["meta"]["assign_bits"] == r2["meta"]["assign_bits"]
    assert r1["best_soft_weight"] == r2["best_soft_weight"]
    assert r1["total_flips"] == r2["total_flips"]
    assert r1["hard_violations"] == r2["hard_violations"]
    assert r1["meta"]["ea_generations"] == r2["meta"]["ea_generations"] == 3
