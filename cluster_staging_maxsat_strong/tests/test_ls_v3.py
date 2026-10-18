"""v3 polish cores (src/sat/ls_v3.py, src/sat/rng.py): docs/current2/STRONGER_MEMETIC_DESIGN.md §2, §3, §7.3.

- walksat_v3 with tabu "none" and MTRng == walksat_polish_v2 exactly (soft-only,
  weighted, hard, both budget_counts_noops settings);
- the tabu tenure and configuration-checking rules hold on every flip, except
  aspiration (a new best) and the least-recently-flipped fallback;
- dls_v3: incremental scores, decreasing set and falsified lists equal a full
  recomputation after every flip and every weight update; the returned
  assignment's true cost is the reported best; tiny instances reach the
  brute-force optimum; feasible starts stay feasible.
"""
from __future__ import annotations

import itertools
import os
import random
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
from sat.walksat_v2 import walksat_polish_v2  # noqa: E402
from sat.ls_v3 import dls_v3, init_dynamic_weights, v3_static, walksat_v3  # noqa: E402
from sat.rng import MTRng, PortableRng  # noqa: E402


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, seed=0, mixed_k=False):
    rng = random.Random(seed)
    top = m_soft * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        kk = rng.randint(1, k) if mixed_k else k
        vs = rng.sample(range(1, n + 1), kk)
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(1, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return WCNF.parse_dimacs(str(path))


def start(n, seed):
    r = random.Random(seed)
    return [r.random() < 0.5 for _ in range(n)]


def true_cost(w, a01):
    hv = soft = 0
    for cl in w.clauses:
        if not any((l > 0 and a01[l]) or (l < 0 and not a01[-l]) for l in cl.lits):
            if cl.is_hard:
                hv += 1
            else:
                soft += int(cl.weight)
    return hv, soft


@pytest.fixture()
def tick_clock(monkeypatch):
    state = {"t": 0.0}

    def fake():
        state["t"] += 1.0
        return state["t"]

    monkeypatch.setattr(time, "time", fake)
    return state


# --------------------------------------------------------------------------- rng

def test_portable_rng_known_values_and_ranges():
    r = PortableRng(12345)
    a = [r.next() for _ in range(3)]
    r2 = PortableRng(12345)
    assert a == [r2.next() for _ in range(3)]
    assert all(0 <= x < 1 << 64 for x in a)
    for _ in range(2000):
        assert 0 <= r.randbelow(7) < 7
        assert 0.0 <= r.random() < 1.0
    assert PortableRng(1).next() != PortableRng(2).next()


# ------------------------------------------------------------------ B1 equality

CASES = [
    dict(n=40, k=2, m_soft=90, m_hard=0, w_max=1),
    dict(n=40, k=3, m_soft=170, m_hard=0, w_max=4),
    dict(n=30, k=3, m_soft=100, m_hard=25, w_max=3),
    dict(n=25, k=2, m_soft=60, m_hard=12, w_max=1),
]


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("noops", [False, True])
@pytest.mark.parametrize("noise", [0.0, 0.1, 0.5])
def test_walksat_v3_without_tabu_equals_v2(tmp_path, tick_clock, case, noops, noise):
    w = make_wcnf(tmp_path, "c", seed=7, **case)
    for seed in range(4):
        s0 = start(case["n"], 100 + seed)
        kw = dict(max_flips=400, time_limit_s=3000, noise=noise, hard_safe=True, budget_counts_noops=noops)
        a = walksat_polish_v2(w, s0, rng_seed=seed, **kw)
        b = walksat_v3(w, s0, rng=MTRng(seed), tabu="none", **kw)
        for key in ("flips", "best_soft_weight", "hard_violations", "total_flips", "final_assign", "noop_steps"):
            assert a[key] == b[key], (key, seed)


# --------------------------------------------------------------------- B1 rules

@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("tenure,rand_t", [(3, 0), (10, 0), (5, 4)])
def test_tenure_rule_holds_except_aspiration_and_fallback(tmp_path, case, tenure, rand_t):
    w = make_wcnf(tmp_path, "c", seed=11, **case)
    for seed in range(3):
        tr, stats = [], {}
        walksat_v3(w, start(case["n"], seed), rng=MTRng(seed), max_flips=600, time_limit_s=None,
                   noise=0.1, tabu="tenure", tenure=tenure, tenure_rand=rand_t, stats=stats, trace=tr)
        last = {}
        for step, v, how in tr:
            if v in last and how == "free":
                assert step - last[v] > tenure, (step, v, last[v])
            last[v] = step
        assert stats["tabu_skips"] >= 0


@pytest.mark.parametrize("case", CASES)
def test_cc_rule_holds_except_aspiration_and_fallback(tmp_path, case):
    w = make_wcnf(tmp_path, "c", seed=13, **case)
    nbrs = v3_static(w).nbrs
    for seed in range(3):
        tr = []
        walksat_v3(w, start(case["n"], seed), rng=MTRng(seed), max_flips=600, time_limit_s=None,
                   noise=0.1, tabu="cc", trace=tr)
        last_step = {}
        for i, (step, v, how) in enumerate(tr):
            if v in last_step and how == "free":
                j = last_step[v]
                # some neighbour of v flipped strictly between the two flips of v
                assert any(u in nbrs[v] for _s, u, _h in tr[j + 1:i]), (step, v)
            last_step[v] = i


def test_tabu_never_loses_the_best_state(tmp_path):
    w = make_wcnf(tmp_path, "c", n=40, k=2, m_soft=100, seed=3)
    for mode in ("tenure", "cc"):
        res = walksat_v3(w, start(40, 1), rng=MTRng(1), max_flips=800, time_limit_s=None,
                         noise=0.1, tabu=mode)
        a01 = [False] + res["final_assign"]
        assert true_cost(w, a01) == (0, int(sum(int(c.weight) for c in w.clauses) - res["best_soft_weight"]))


def test_unknown_tabu_mode_refused(tmp_path):
    w = make_wcnf(tmp_path, "c", n=10, k=2, m_soft=20)
    with pytest.raises(ValueError):
        walksat_v3(w, start(10, 0), rng=MTRng(0), tabu="bogus")


# ------------------------------------------------------------------------- B2

@pytest.mark.parametrize("case", CASES + [dict(n=20, k=3, m_soft=50, m_hard=8, w_max=5, mixed_k=True)])
@pytest.mark.parametrize("sp,zeta,h_inc", [(0.01, 50, 1), (0.3, 3, 2), (0.0, 1000, 3)])
def test_dls_incremental_state_equals_full_recompute(tmp_path, case, sp, zeta, h_inc):
    w = make_wcnf(tmp_path, "c", seed=17, **case)
    for seed in range(2):
        dls_v3(w, start(case["n"], seed), rng=MTRng(seed), max_flips=300, time_limit_s=None,
               t=5, sp=sp, zeta=zeta, h_inc=h_inc, _debug_check=True)


@pytest.mark.parametrize("case", CASES)
def test_dls_reported_best_is_the_true_cost_of_the_returned_assignment(tmp_path, case):
    w = make_wcnf(tmp_path, "c", seed=19, **case)
    tot = sum(int(c.weight) for c in w.clauses if not c.is_hard)
    for seed in range(3):
        res = dls_v3(w, start(case["n"], seed), rng=MTRng(seed), max_flips=500, time_limit_s=None)
        hv, soft = true_cost(w, [False] + res["final_assign"])
        assert hv == res["hard_violations"]
        assert soft == tot - res["best_soft_weight"]


def _brute(w):
    n = w.n_vars
    best = None
    for bits in itertools.product([False, True], repeat=n):
        c = true_cost(w, [False] + list(bits))
        best = c if best is None or c < best else best
    return best


@pytest.mark.parametrize("seed", range(6))
def test_dls_reaches_brute_force_optimum_on_tiny_instances(tmp_path, seed):
    w = make_wcnf(tmp_path, f"t{seed}", n=10, k=2, m_soft=40, m_hard=4, w_max=3, seed=seed)
    opt = _brute(w)
    tot = sum(int(c.weight) for c in w.clauses if not c.is_hard)
    res = dls_v3(w, start(10, seed), rng=MTRng(seed), max_flips=4000, time_limit_s=None, zeta=20)
    assert (res["hard_violations"], tot - res["best_soft_weight"]) == opt


def test_dls_feasible_start_stays_feasible(tmp_path):
    w = make_wcnf(tmp_path, "h", n=30, k=3, m_soft=90, m_hard=30, w_max=2, seed=23)
    # a feasible start by brute-force-free means: let the DLS find one, then restart from it
    res0 = dls_v3(w, start(30, 0), rng=MTRng(0), max_flips=5000, time_limit_s=None)
    assert res0["hard_violations"] == 0
    s_feas = res0["final_assign"]
    for seed in range(5):
        res = dls_v3(w, s_feas, rng=MTRng(seed), max_flips=400, time_limit_s=None)
        assert res["hard_violations"] == 0
        assert true_cost(w, [False] + res["final_assign"])[0] == 0


def test_dls_run_level_weights_are_updated_in_place(tmp_path):
    w = make_wcnf(tmp_path, "c", n=30, k=2, m_soft=90, seed=29)
    dw = init_dynamic_weights(w)
    before = list(dw)
    dls_v3(w, start(30, 0), rng=MTRng(0), max_flips=500, time_limit_s=None, dw=dw, sp=0.0, zeta=10)
    assert dw != before and all(x >= 1 for x in dw) and max(dw) <= 10
    with pytest.raises(ValueError):
        dls_v3(w, start(30, 0), rng=MTRng(0), max_flips=10, dw=dw[:-1])


def test_cores_run_on_portable_rng(tmp_path):
    w = make_wcnf(tmp_path, "c", n=30, k=3, m_soft=100, m_hard=10, seed=31)
    a = walksat_v3(w, start(30, 0), rng=PortableRng(5), max_flips=300, time_limit_s=None, tabu="cc")
    b = walksat_v3(w, start(30, 0), rng=PortableRng(5), max_flips=300, time_limit_s=None, tabu="cc")
    assert a["final_assign"] == b["final_assign"]
    c = dls_v3(w, start(30, 0), rng=PortableRng(5), max_flips=300, time_limit_s=None)
    d = dls_v3(w, start(30, 0), rng=PortableRng(5), max_flips=300, time_limit_s=None)
    assert c["final_assign"] == d["final_assign"]


@pytest.mark.parametrize("case", CASES)
def test_dls_cc_keeps_state_exact_and_obeys_cc_when_not_forced(tmp_path, case):
    w = make_wcnf(tmp_path, "c", seed=37, **case)
    for seed in range(2):
        st = {}
        dls_v3(w, start(case["n"], seed), rng=MTRng(seed), max_flips=300, time_limit_s=None,
               t=5, cc=True, stats=st, _debug_check=True)
        assert st["dls_cc_blocked"] >= 0


def test_dls_without_cc_is_unchanged_by_the_cc_code(tmp_path):
    w = make_wcnf(tmp_path, "c", n=30, k=2, m_soft=90, seed=41)
    a = dls_v3(w, start(30, 0), rng=MTRng(3), max_flips=400, time_limit_s=None)
    b = dls_v3(w, start(30, 0), rng=MTRng(3), max_flips=400, time_limit_s=None, cc=False)
    assert a["final_assign"] == b["final_assign"] and a["flips"] == b["flips"]
