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

from sat.cnf import WCNF  # noqa: E402
from sat.kernel import HARD, _weight, kernelize, kernelize_reference, screen_frac  # noqa: E402


def same(clauses):
    a, b = kernelize(clauses), kernelize_reference(clauses)
    return list(a[0].items()) == list(b[0].items()) and a[1] == b[1] and a[2] == b[2]


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
