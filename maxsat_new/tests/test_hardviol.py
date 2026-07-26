"""Step 6 test: violated_hard_clauses returns the expected (idx, lits).

Fails before maxsat_new/hardviol.py exists; passes after.

`idx` is the GLOBAL index into wcnf.clauses (hard and soft enumerated together),
not an index into a hard-only sublist. hardmix.wcnf exists to make that
distinguishable: its hard clauses are at global 1, 3, 4 but would be 0, 1, 2
under the sublist convention.
"""
from __future__ import annotations

import os

from maxsat_new.cnf import WCNF
from maxsat_new.hardviol import violated_hard_clauses

DATA = os.path.join(os.path.dirname(__file__), "data")
MINI = os.path.join(DATA, "mini.wcnf")
HARDMIX = os.path.join(DATA, "hardmix.wcnf")


def test_violated_hard_clauses_global_index() -> None:
    """The load-bearing assertion: known instance + known assignment."""
    wcnf = WCNF.parse_dimacs(HARDMIX)

    # Structure the expectation leans on: hard at global 1, 3, 4.
    assert [i for i, cl in enumerate(wcnf.clauses) if cl.is_hard] == [1, 3, 4]

    #   x1=T, x2=F, x3=F, x4=T   (1-based; index 0 unused)
    #   idx1 hard [-1, 3]: -1 false (x1=T), 3 false (x3=F)  -> VIOLATED
    #   idx3 hard [2, 4] : 2 false (x2=F),  4 true  (x4=T)  -> satisfied
    #   idx4 hard [-4]   : -4 false (x4=T)                  -> VIOLATED
    assign01 = [False, True, False, False, True]

    assert violated_hard_clauses(wcnf, assign01) == [(1, (-1, 3)), (4, (-4,))]


def test_agrees_with_eval_assignment() -> None:
    """Cross-check the count against cnf.eval_assignment's separate predicate."""
    wcnf = WCNF.parse_dimacs(HARDMIX)
    assign01 = [False, True, False, False, True]

    sat_w, hard_v, soft_v = wcnf.eval_assignment(assign01)
    assert (sat_w, hard_v, soft_v) == (110, 2, 0)
    assert len(violated_hard_clauses(wcnf, assign01)) == hard_v


def test_no_violations_returns_empty() -> None:
    """All hard satisfied -> empty. Also pins the 0/1-int truthiness contract:
    this is the exact assignment already asserted in test_cnf.py (hard_v == 0)."""
    wcnf = WCNF.parse_dimacs(MINI)
    assign01 = [0, 1, 0, 0, 1, 1]

    assert violated_hard_clauses(wcnf, assign01) == []


def test_first_clause_violated() -> None:
    """Boundary: a violation at global idx 0 must be reported, not skipped."""
    wcnf = WCNF.parse_dimacs(MINI)

    #   x1=F, x2=F, x3=F, x4=F, x5=T
    #   idx0 hard [1, 2]  : both false            -> VIOLATED
    #   idx1 hard [-3, 4] : -3 true (x3=F)        -> satisfied
    #   idx2 hard [5]     : 5 true (x5=T)         -> satisfied
    assign01 = [0, 0, 0, 0, 0, 1]

    assert violated_hard_clauses(wcnf, assign01) == [(0, (1, 2))]


def test_lits_are_tuples_and_not_aliased() -> None:
    """The snapshot must not hand a provider a live reference to clause storage."""
    wcnf = WCNF.parse_dimacs(HARDMIX)
    assign01 = [False, True, False, False, True]

    result = violated_hard_clauses(wcnf, assign01)
    for idx, lits in result:
        assert isinstance(lits, tuple)
        assert lits is not wcnf.clauses[idx].lits
        assert list(lits) == wcnf.clauses[idx].lits
