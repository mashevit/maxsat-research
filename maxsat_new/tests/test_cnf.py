"""Step 1 test: parse mini.wcnf and check structure + eval_assignment.

Fails before maxsat_new/cnf.py exists; passes after.
"""
from __future__ import annotations

import os

from maxsat_new.cnf import WCNF

MINI = os.path.join(os.path.dirname(__file__), "data", "mini.wcnf")


def test_parse_and_eval() -> None:
    wcnf = WCNF.parse_dimacs(MINI)

    # Structure.
    assert wcnf.n_vars == 5
    assert len(wcnf.clauses) == 8
    n_hard = sum(1 for cl in wcnf.clauses if cl.is_hard)
    n_soft = sum(1 for cl in wcnf.clauses if not cl.is_hard)
    assert n_hard == 3
    assert n_soft == 5

    # eval_assignment on a known assignment.
    #   x1=1, x2=0, x3=0, x4=1, x5=1  (assign01 is 1-based, index 0 unused)
    #   all 3 hard satisfied (100 each); soft satisfied: w3(x1), w5(~x2), w4(~x4 or x5)
    #   soft unsatisfied: w2(x3), w1(x2 or ~x5)
    #   sat_w = 300 + (3 + 5 + 4) = 312; hard_v = 0; soft_v = 2
    assign01 = [0, 1, 0, 0, 1, 1]
    sat_w, hard_v, soft_v = wcnf.eval_assignment(assign01)
    assert sat_w == 312
    assert hard_v == 0
    assert soft_v == 2
