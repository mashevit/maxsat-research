"""Step 1 tests: docs/INSTANCEGEN_PLAN.md §12 test 1, in-memory half.

Fails before instancegen/generate.py exists; passes after. Imports no solver --
that is the point of §7's pure/impure split.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from instancegen.generate import (
    GenParams,
    generate,
    instance_filename,
)

BASE = GenParams(
    n_vars=40,
    k=3,
    soft_ratio=4.0,
    hard_ratio=0.5,
    w_max=16,
    seed=7,
)


# --- §12 test 1 (in-memory half) --------------------------------------------

def test_determinism_in_memory() -> None:
    a = generate(BASE)
    b = generate(BASE)
    assert a == b
    # Dataclass equality is structural, so also compare the clause tuples
    # explicitly: this is the assertion the byte-identity test in
    # test_wcnf_io.py rests on.
    assert a.clauses == b.clauses
    assert a.top == b.top


def test_different_seeds_differ() -> None:
    """Guards a degenerate generator that ignores its seed (§12 test 1)."""
    a = generate(BASE)
    b = generate(replace(BASE, seed=BASE.seed + 1))
    assert a.clauses != b.clauses


def test_derived_seed_paths_differ_from_base() -> None:
    """A resample must actually resample: derived seeds give a new instance."""
    a = generate(BASE)
    b = generate(replace(BASE, seed=123456789))
    assert a.clauses != b.clauses


# --- structure / GenParams contract -----------------------------------------

def test_counts_from_ratios() -> None:
    p = GenParams(n_vars=150, k=3, soft_ratio=3.90, hard_ratio=0.40, w_max=64, seed=7)
    assert p.n_hard == 60
    assert p.n_soft == 585
    assert p.clause_ratio == pytest.approx(4.30)

    inst = generate(p)
    assert inst.n_vars == 150
    assert len(inst.clauses) == 645
    assert len(inst.hard_clauses) == 60
    assert len(inst.soft_clauses) == 585
    # Hard clauses are generated first (§8).
    assert all(c.is_hard for c in inst.clauses[:60])
    assert not any(c.is_hard for c in inst.clauses[60:])


def test_ratios_move_independently() -> None:
    """§8.1: hard_ratio must not change n_soft, soft_ratio must not change n_hard."""
    p = GenParams(n_vars=100, k=3, soft_ratio=4.0, hard_ratio=0.5, w_max=8, seed=1)
    more_hard = replace(p, hard_ratio=2.0)
    more_soft = replace(p, soft_ratio=6.0)
    assert more_hard.n_soft == p.n_soft
    assert more_soft.n_hard == p.n_hard
    assert generate(more_hard).n_vars == generate(more_soft).n_vars


def test_clause_shape_and_weights() -> None:
    inst = generate(BASE)
    for cl in inst.clauses:
        assert len(cl.lits) == BASE.k
        # Distinct variables, so no duplicate literals and no tautology.
        assert len({abs(l) for l in cl.lits}) == BASE.k
        assert all(1 <= abs(l) <= BASE.n_vars for l in cl.lits)
    for cl in inst.soft_clauses:
        # Weight 0 would be silently dropped by maxsat_new/cnf.py:57 (§9.5).
        assert 1 <= cl.weight <= BASE.w_max
    assert inst.top == 1 + inst.total_soft_weight
    assert all(cl.weight == inst.top for cl in inst.hard_clauses)


def test_signs_are_mixed() -> None:
    """Guards a generator that emits only positive literals."""
    lits = [l for cl in generate(BASE).clauses for l in cl.lits]
    assert any(l > 0 for l in lits)
    assert any(l < 0 for l in lits)


# --- weight_dist (D4) --------------------------------------------------------

def test_weight_dist_few_classes() -> None:
    p = replace(BASE, weight_dist="few_classes:4", w_max=64, soft_ratio=10.0)
    inst = generate(p)
    assert inst.n_distinct_weights == 4
    assert all(1 <= c.weight <= 64 for c in inst.soft_clauses)


def test_weight_dist_powerlaw_is_skewed_low() -> None:
    p = replace(BASE, weight_dist="powerlaw:2.0", w_max=64, soft_ratio=25.0)
    inst = generate(p)
    weights = [c.weight for c in inst.soft_clauses]
    assert all(1 <= w <= 64 for w in weights)
    # alpha=2 puts most mass on small weights; a uniform draw would not.
    assert sum(1 for w in weights if w <= 8) > 0.5 * len(weights)


def test_weight_dist_is_deterministic() -> None:
    for spec in ("uniform", "few_classes:5", "powerlaw:1.5"):
        p = replace(BASE, weight_dist=spec)
        assert generate(p).clauses == generate(p).clauses


@pytest.mark.parametrize(
    "spec",
    [
        "gaussian",
        "uniform:3",
        "few_classes",
        "few_classes:0",
        "few_classes:2.5",
        "few_classes:999",   # > w_max
        "powerlaw",
        "powerlaw:0",
        "powerlaw:abc",
    ],
)
def test_bad_weight_dist_raises(spec: str) -> None:
    with pytest.raises(ValueError):
        generate(replace(BASE, weight_dist=spec))


# --- validation --------------------------------------------------------------

@pytest.mark.parametrize(
    "kwargs",
    [
        {"n_vars": 0},
        {"k": 0},
        {"k": 41},            # k > n_vars
        {"w_max": 0},         # weight 0 is banned (§9.5)
        {"soft_ratio": -1.0},
        {"hard_ratio": -1.0},
        {"soft_ratio": 0.0, "hard_ratio": 0.0},
    ],
)
def test_bad_params_raise(kwargs) -> None:
    with pytest.raises(ValueError):
        generate(replace(BASE, **kwargs))


def test_genparams_is_frozen() -> None:
    with pytest.raises(Exception):
        BASE.n_vars = 99  # type: ignore[misc]


# --- filename template (§10.3) ----------------------------------------------

def test_instance_filename() -> None:
    p = GenParams(n_vars=150, k=3, soft_ratio=3.90, hard_ratio=0.40, w_max=64, seed=7)
    assert instance_filename(p) == "wksat_v150_k3_sr3.90_hr0.40_w64_uniform_s7.wcnf"


def test_instance_filename_slugifies_weight_dist() -> None:
    p = replace(BASE, weight_dist="few_classes:5")
    name = instance_filename(p)
    assert "few_classes-5" in name
    assert ":" not in name
