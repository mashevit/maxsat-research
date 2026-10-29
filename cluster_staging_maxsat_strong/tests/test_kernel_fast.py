"""The fast kernelize equals the reference (docs/current2/COMPILED_MEMETIC_PLAN.md §10).

Same kernel dict in the same order, same constant, same elimination record, on:
random instances (hard and soft clauses, complementary soft units, duplicates,
tautologies, empty and long clauses), hub instances (the quadratic case of the
reference), and every local instance whose screen passes; the fast one is
linear on the hub case.
"""
from __future__ import annotations

import os
import random
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TREE, "src"))

from sat.cnf import WCNF, Clause  # noqa: E402
from sat.kernel import HARD, _weight, build_kernel, kernelize, kernelize_reference, screen_frac  # noqa: E402


def same(clauses):
    """kernelize equals the reference: on the list, and on a one-pass stream with a loose n_vars."""
    b = kernelize_reference(clauses)
    n = max((abs(l) for _, lits in clauses for l in lits), default=0)
    for a in (kernelize(clauses), kernelize(iter(clauses), n + 3)):
        if not (list(a[0].items()) == list(b[0].items()) and a[1] == b[1] and a[2] == b[2]):
            return False
    return True


def kernel_items(k):
    """A Kernel's clauses in original variables, as (lits, weight) in kernel order (HARD for hard)."""
    out = []
    for cl in k.wcnf.clauses:
        lits = tuple(k.var_of[abs(l) - 1] * (1 if l > 0 else -1) for l in cl.lits)
        out.append((lits, HARD if cl.is_hard else cl.weight))
    return out


def same_build(w):
    """build_kernel (streamed input) equals the reference on the materialised clause list."""
    C, const, rec = kernelize_reference([(_weight(cl), tuple(cl.lits)) for cl in w.clauses])
    k, kconst = build_kernel(w)
    if const >= HARD:
        return k is None and kconst == const
    expect = [(lits, HARD if wt >= HARD else wt) for lits, wt in C.items()]   # merged hard + soft is hard
    return kernel_items(k) == expect and k.const == const and k.rec == rec


def random_clauses(seed, n, m, hard_frac, kmax, units=0.2):
    r = random.Random(seed)
    out = []
    for _ in range(m):
        k = 1 if r.random() < units else r.randint(0, kmax)
        lits = [r.choice((1, -1)) * r.randint(1, n) for _ in range(k)]
        if lits and r.random() < 0.1:
            lits.append(lits[0])                      # duplicate
        if lits and r.random() < 0.05:
            lits.append(-lits[0])                     # tautology
        out.append((HARD if r.random() < hard_frac else r.randint(1, 9), tuple(lits)))
    return out


@pytest.mark.parametrize("seed", range(40))
def test_random_equal(seed):
    r = random.Random(seed)
    n = r.choice((5, 12, 30, 80))
    cl = random_clauses(seed, n, m=r.randint(n, 4 * n), hard_frac=r.choice((0.0, 0.2, 0.5)), kmax=r.choice((2, 3, 6)))
    assert same(cl)


@pytest.mark.parametrize("seed", range(10))
def test_sparse_max2sat_equal(seed):
    r = random.Random(seed)
    n = 400
    cl = [(r.randint(1, 3), tuple(r.choice((1, -1)) * v for v in r.sample(range(1, n + 1), 2)))
          for _ in range(int(1.1 * n))]
    assert same(cl)


def test_hub_cases_equal_and_linear():
    for N in (50, 500, 3000):
        hub = [(HARD, (-1, -(i + 2))) for i in range(N)] + [(5, (1,))]
        assert same(hub)
        star = [(HARD, (1, i + 2)) for i in range(N)] + [(3, (-(i + 2),)) for i in range(0, N, 7)] + [(2, (-1,))]
        assert same(star)
    N = 200_000
    t = time.time()
    C, const, rec = kernelize([(HARD, (-1, -(i + 2))) for i in range(N)] + [(5, (1,))])
    assert time.time() - t < 20 and len(rec) == N + 1   # the reference needs hours here


LOCAL = ["data/generated/calib_2sat_sc2", "data/generated/calib_2sat_sc", "data/raw/mse_2024/mse24-small",
         "data/raw/mse_2024/mse23-uw-small"]


def local_screen_passing(limit=40):
    out = []
    for d in LOCAL:
        p = os.path.join(TREE, d)
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if f.endswith(".wcnf") and os.path.getsize(os.path.join(p, f)) < 3_000_000:
                out.append(os.path.join(p, f))
    return out[:limit]


@pytest.mark.parametrize("path", local_screen_passing())
def test_local_instances_equal(path):
    w = WCNF.parse_dimacs(path)
    frac, _ = screen_frac(w)
    if frac < 0.2:
        pytest.skip("screen does not pass (gate would not kernelise)")
    assert same([(_weight(cl), tuple(cl.lits)) for cl in w.clauses])
    assert same_build(w)


@pytest.mark.parametrize("seed", range(10))
def test_build_kernel_streamed_equal(seed):
    r = random.Random(100 + seed)
    n = r.choice((12, 30, 80))
    w = WCNF(n_vars=n + r.randint(0, 3), hard_weight=10_000, is_wcnf=True)   # n_vars may exceed the max variable
    for weight, lits in random_clauses(seed, n, m=r.randint(n, 4 * n), hard_frac=0.3, kmax=4):
        w.clauses.append(Clause(weight=10_000 if weight == HARD else weight, lits=list(lits), is_hard=weight == HARD))
    assert same_build(w)


def test_shared_objects():
    """One int object per literal value and one HARD object across the kernel (the memory saving)."""
    r = random.Random(7)
    n = 40
    cl = [(HARD if r.random() < 0.5 else r.randint(1, 9),
           tuple(r.choice((1, -1)) * v for v in r.sample(range(300, 300 + n), 3))) for _ in range(600)]
    C, _, _ = kernelize(iter(cl), 300 + n)
    assert C and any(wt >= HARD for wt in C.values())
    ids = {}
    for lits in C:
        for l in lits:
            assert ids.setdefault(l, id(l)) == id(l)
    assert all(wt is HARD for wt in C.values() if wt == HARD)   # a merged duplicate (HARD + w) is its own object


def test_literal_above_n_vars_refused():
    for lit in (5, -5):
        with pytest.raises(IndexError):
            kernelize([(1, (1, lit))], 4)
