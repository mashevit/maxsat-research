"""Lean neighbour tables (docs/current2/LONG_CLAUSE_RULE_DESIGN.md).

- the bound sum k(k-1) and the `auto` trigger (full below NBRS_MAX, lean above);
- CC: walksat_v3 and dls_v3, Python and C, give the same run with lean and full
  tables (same flips, counters, assignment);
- PX: lean components equal the BFS components, so the same crossover child;
- walk mutation: the lean neighbour draw is uniform over the distinct neighbours
  (chi-square) and deterministic under a seed;
- end to end: run_memetic with CC + PX + count mutation gives the same run with
  lean and full tables, Python and native, and records the mode;
- ls.nbrs is validated and refused outside impl v3.
Instances include tautological clauses (x and -x), repeated literals and one long
clause, where `occ` (d != 0) and the neighbour definition (every literal) differ.
"""
from __future__ import annotations

import os
import random
import subprocess
import shutil
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
import sat.ls_v3 as lsv3  # noqa: E402
from sat.ls_v3 import dls_v3, set_nbrs_mode, v3_static, walksat_v3  # noqa: E402
from sat.rng import PortableRng  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.v3 import check_cfg, lean_neighbour, px_components, partition_crossover  # noqa: E402
from evo.population import Individual, evaluate_assignment  # noqa: E402


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, seed=0, extra=()):
    """Random clauses of 1..k literals, plus `extra` clauses given as (weight or 'H', lits)."""
    rng = random.Random(seed)
    top = (m_soft + len(extra)) * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        vs = rng.sample(range(1, n + 1), rng.randint(1, k))
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(1, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    for w, lits in extra:
        lines.append(f"{top if w == 'H' else w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return str(path)


# tautology (3, -3), repeated literal (2, 2), a long clause over 25 variables
EDGE = [(1, [1, 3, -3, 5]), (2, [2, 2, -4]), (1, [-6, 6]), (1, list(range(10, 35)))]
CASES = [
    dict(n=40, k=3, m_soft=110, extra=EDGE),
    dict(n=50, k=4, m_soft=150, w_max=4, extra=EDGE),
    dict(n=36, k=3, m_soft=90, m_hard=20, w_max=3, extra=EDGE),
]


def pair(tmp_path, name, **case):
    """The same instance parsed twice, one with full and one with lean tables."""
    p = make_wcnf(tmp_path, name, seed=7, **case)
    wf, wl = WCNF.parse_dimacs(p), WCNF.parse_dimacs(p)
    set_nbrs_mode(wf, "full")
    set_nbrs_mode(wl, "lean")
    assert v3_static(wf).nbrs is not None and v3_static(wl).nbrs is None
    return wf, wl


def start(n, seed):
    r = random.Random(seed)
    return [r.random() < 0.5 for _ in range(n)]


KEYS = ("flips", "total_flips", "best_soft_weight", "hard_violations", "final_assign", "noop_steps")


# ------------------------------------------------------------------ the trigger

def test_bound_and_auto_trigger(tmp_path, monkeypatch):
    p = make_wcnf(tmp_path, "b", n=40, k=3, m_soft=40, seed=1, extra=EDGE)
    w = WCNF.parse_dimacs(p)
    want = 0
    for cl in w.clauses:
        k = len({abs(l) for l in cl.lits})
        want += k * (k - 1)
    x = v3_static(w)
    assert x.bound == want and x.mode == "full" and x.requested == "auto"
    # full tables equal the definition: u, v share a clause (any literal, v != u)
    for v in range(1, w.n_vars + 1):
        nb = {abs(l) for cl in w.clauses if v in {abs(q) for q in cl.lits} for l in cl.lits} - {v}
        assert x.nbrs[v] == sorted(nb)
    w2 = WCNF.parse_dimacs(p)
    monkeypatch.setattr(lsv3, "NBRS_MAX", want - 1)
    x2 = v3_static(w2)
    assert x2.mode == "lean" and x2.nbrs is None and x2.bound == want
    # lean tables: every clause of v, distinct sorted variables per clause
    for ci, cl in enumerate(w2.clauses):
        assert x2.cv[ci] == sorted({abs(l) for l in cl.lits})
    for v in range(1, w2.n_vars + 1):
        assert x2.aocc[v] == [ci for ci, cl in enumerate(w2.clauses) if v in {abs(l) for l in cl.lits}]


def test_set_nbrs_mode_drops_a_table_built_under_another_request(tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "m", n=20, k=3, m_soft=30, seed=2))
    assert v3_static(w).mode == "full"
    set_nbrs_mode(w, "lean")
    assert v3_static(w).mode == "lean"
    set_nbrs_mode(w, "auto")
    assert v3_static(w).mode == "full"
    with pytest.raises(ValueError):
        set_nbrs_mode(w, "half")


# ------------------------------------------------------------------ CC: Python

@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("noops", [False, True])
def test_walksat_cc_lean_equals_full(tmp_path, case, noops):
    if case.get("m_hard") and not noops:
        pytest.skip("hard instance without no-op counting needs a time limit")
    wf, wl = pair(tmp_path, "w", **case)
    for seed in range(4):
        s0 = start(case["n"], 30 + seed)
        sa, sb, ta, tb = {}, {}, [], []
        a = walksat_v3(wf, s0, rng=PortableRng(seed), max_flips=800, time_limit_s=None, noise=0.15,
                       budget_counts_noops=noops, tabu="cc", stats=sa, trace=ta)
        b = walksat_v3(wl, s0, rng=PortableRng(seed), max_flips=800, time_limit_s=None, noise=0.15,
                       budget_counts_noops=noops, tabu="cc", stats=sb, trace=tb)
        assert ta == tb and sa == sb
        for k in KEYS:
            assert a[k] == b[k], (k, seed)


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("sp,zeta,h_inc,t", [(0.01, 50, 1, 15), (0.2, 4, 2, 5)])
def test_dls_cc_lean_equals_full(tmp_path, case, sp, zeta, h_inc, t):
    wf, wl = pair(tmp_path, "d", **case)
    for seed in range(4):
        s0 = start(case["n"], 60 + seed)
        sa, sb = {}, {}
        a = dls_v3(wf, s0, rng=PortableRng(seed), max_flips=800, time_limit_s=None, t=t, sp=sp,
                   zeta=zeta, h_inc=h_inc, cc=True, stats=sa)
        b = dls_v3(wl, s0, rng=PortableRng(seed), max_flips=800, time_limit_s=None, t=t, sp=sp,
                   zeta=zeta, h_inc=h_inc, cc=True, stats=sb)
        assert sa == sb
        for k in KEYS:
            assert a[k] == b[k], (k, seed)


# ------------------------------------------------------------------ CC: C core

needs_cc = pytest.mark.skipif(shutil.which(os.environ.get("CC", "cc")) is None, reason="no C compiler")


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    d = tmp_path_factory.mktemp("native_build_lean")
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


@needs_cc
@pytest.mark.parametrize("case", CASES)
def test_native_cc_lean_equals_full_and_python(native, tmp_path, case):
    wf, wl = pair(tmp_path, "n", **case)
    cf, cl = native.load_native(wf), native.load_native(wl)
    assert cf.inst.nb_off and not cl.inst.nb_off          # NULL pointer = lean in C
    for seed in range(3):
        s0 = start(case["n"], 90 + seed)
        res = []
        for core in (cf, cl):
            st = {}
            r = core.dls(s0, seed, 800, None, t=15, sp=0.05, zeta=50, h_inc=1, cc=True, stats=st)
            res.append((r, st))
        sp = {}
        py = dls_v3(wl, s0, rng=PortableRng(seed), max_flips=800, time_limit_s=None, t=15, sp=0.05,
                    zeta=50, h_inc=1, cc=True, stats=sp)
        for k in KEYS:
            assert res[0][0][k] == res[1][0][k] == py[k], (k, seed)
        assert res[0][1] == res[1][1] == sp
        if not case.get("m_hard"):
            a = cf.walksat(s0, seed, 800, None, noise=0.15, tabu="cc")
            b = cl.walksat(s0, seed, 800, None, noise=0.15, tabu="cc")
            for k in KEYS:
                assert a[k] == b[k], (k, seed)


@needs_cc
def test_load_native_rebuilds_when_the_tables_change(native, tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "r", n=20, k=3, m_soft=30, seed=4))
    c1 = native.load_native(w)
    assert native.load_native(w) is c1
    set_nbrs_mode(w, "lean")
    c2 = native.load_native(w)
    assert c2 is not c1 and not c2.inst.nb_off


# ------------------------------------------------------------------ PX

def _ind(a):
    ind = Individual(a)
    return ind


@pytest.mark.parametrize("case", CASES)
def test_px_lean_equals_full(tmp_path, case):
    wf, wl = pair(tmp_path, "p", **case)
    rng = random.Random(5)
    n = case["n"]
    for _ in range(25):
        a = [False] + [rng.random() < 0.5 for _ in range(n)]
        b = list(a)
        for v in rng.sample(range(1, n + 1), rng.randint(1, n // 2)):
            b[v] = not b[v]
        assert px_components(a, b, wf, return_map=True) == px_components(a, b, wl, return_map=True)
        pa, pb = _ind(a), _ind(b)
        for p, w in ((pa, wf), (pb, wf)):
            soft, hv = evaluate_assignment(w, p.assign01)
            p.fitness, p.hard_violations = (soft if hv == 0 else -hv * 1e9 + soft), hv
        assert partition_crossover(pa, pb, wf) == partition_crossover(pa, pb, wl)


# ------------------------------------------------------------------ walk

def test_lean_neighbour_is_uniform_over_distinct_neighbours(tmp_path):
    # N(1) = {2..8}; 3 shares three clauses with 1, 5/6/7 one, 2/4/8 one each
    extra = [(1, [1, 2, 3]), (1, [-1, 3, 4]), (1, [1, -3, 5, 6, 7]), (1, [1, 8]), (1, [9, 10])]
    p = make_wcnf(tmp_path, "u", n=10, k=1, m_soft=0, extra=extra)
    w = WCNF.parse_dimacs(p)
    set_nbrs_mode(w, "lean")
    x = v3_static(w)
    rng = random.Random(11)
    draws = 70_000
    cnt = {}
    for _ in range(draws):
        u = lean_neighbour(x, 1, rng)
        cnt[u] = cnt.get(u, 0) + 1
    assert set(cnt) == set(range(2, 9))
    exp = draws / 7
    chi2 = sum((c - exp) ** 2 / exp for c in cnt.values())
    assert chi2 < 22.46            # 6 degrees of freedom, p = 0.001
    # a variable in no multi-variable clause has no neighbour
    w2 = WCNF.parse_dimacs(make_wcnf(tmp_path, "u2", n=3, k=1, m_soft=0, extra=[(1, [1]), (1, [2, 3])]))
    set_nbrs_mode(w2, "lean")
    assert lean_neighbour(v3_static(w2), 1, random.Random(0)) is None
    # deterministic under a seed
    r1, r2 = random.Random(4), random.Random(4)
    assert [lean_neighbour(x, 1, r1) for _ in range(50)] == [lean_neighbour(x, 1, r2) for _ in range(50)]


# ------------------------------------------------------------------ end to end

def base_cfg(nbrs, native_on=False, mutation="count"):
    return {"impl": "v3", "time_limit_s": 1000.0,
            "ea": {"enabled": True, "pop_size": 8, "tournament_k": 3, "pmutate": 0.05, "elitism": True,
                   "max_gens": 3, "deadline_mode": "clip", "mutation": mutation, "mutation_k": 4,
                   "crossover": "px"},
            "ls": {"ls_polish_flips": 150, "flip_budget": 150, "time_limit_s": 3.5, "polish_cap": "flips_only",
                   "core": "dls", "tabu": "cc", "native": native_on, "nbrs": nbrs}}


def _same_run(r1, r2):
    for k in ("best_soft_weight", "hard_violations", "total_flips", "stop_reason"):
        assert r1[k] == r2[k], k
    assert r1["meta"]["assign_bits"] == r2["meta"]["assign_bits"]
    assert r1["meta"]["children"] == r2["meta"]["children"]
    d1 = {k: v for k, v in r1["v3"].items() if not k.startswith("nbrs_")}
    d2 = {k: v for k, v in r2["v3"].items() if not k.startswith("nbrs_")}
    assert d1 == d2


@pytest.mark.parametrize("native_on", [False, True])
@pytest.mark.parametrize("m_hard", [0, 12])
def test_end_to_end_lean_equals_full_without_walk(tmp_path, native_on, m_hard, request):
    if native_on:
        if shutil.which(os.environ.get("CC", "cc")) is None:
            pytest.skip("no C compiler")
        request.getfixturevalue("native")
    if m_hard:
        pytest.importorskip("pysat")
    p = make_wcnf(tmp_path, "e", n=40, k=3, m_soft=100, m_hard=m_hard, w_max=2, seed=13, extra=EDGE)
    rf = run_memetic(WCNF.parse_dimacs(p), base_cfg("full", native_on), rng_seed=5)
    rl = run_memetic(WCNF.parse_dimacs(p), base_cfg("lean", native_on), rng_seed=5)
    _same_run(rf, rl)
    assert rf["v3"]["nbrs_mode"] == "full" and rl["v3"]["nbrs_mode"] == "lean"
    assert rf["v3"]["nbrs_bound"] == rl["v3"]["nbrs_bound"] > 0
    ra = run_memetic(WCNF.parse_dimacs(p), base_cfg("auto", native_on), rng_seed=5)
    _same_run(rf, ra)
    assert ra["v3"]["nbrs_mode"] == "full"


def test_end_to_end_lean_walk_is_deterministic_and_valid(tmp_path):
    p = make_wcnf(tmp_path, "k", n=40, k=3, m_soft=100, w_max=2, seed=17, extra=EDGE)
    r1 = run_memetic(WCNF.parse_dimacs(p), base_cfg("lean", mutation="walk"), rng_seed=8)
    r2 = run_memetic(WCNF.parse_dimacs(p), base_cfg("lean", mutation="walk"), rng_seed=8)
    _same_run(r1, r2)
    w = WCNF.parse_dimacs(p)
    a01 = [False] + [c == "1" for c in r1["meta"]["assign_bits"]]
    soft, hv = evaluate_assignment(w, a01)
    assert soft == r1["best_soft_weight"] and hv == 0 and r1["v3"]["mutation_flips_sum"] > 0


def test_nbrs_key_is_validated_and_needs_v3():
    assert check_cfg({"impl": "v3", "ls": {"nbrs": "lean"}}, "v3")["nbrs"] == "lean"
    assert check_cfg({"impl": "v3"}, "v3")["nbrs"] == "auto"
    with pytest.raises(ValueError):
        check_cfg({"impl": "v3", "ls": {"nbrs": "half"}}, "v3")
    with pytest.raises(ValueError):
        check_cfg({"impl": "v2", "ls": {"nbrs": "lean"}}, "v2")
