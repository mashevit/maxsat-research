"""EvalMaxSAT oracle driver: WCNF dialects, cost checks, and the SIGTERM anytime stop.

The live tests need the EvalMaxSAT binary and are skipped without it. The
binary is looked up at the driver's default path, or at $EVALMAXSAT_BIN.
"""
from __future__ import annotations

import os
import textwrap

import pytest

from src.cli import oracle_evalmaxsat as oe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.environ.get("EVALMAXSAT_BIN") or next(
    (p for p in (oe.DEFAULT_BIN,
                 os.path.join(os.path.dirname(ROOT), "solver_EvalMaxSat", "EvalMaxSAT", "build", "main",
                              "EvalMaxSAT_bin"))
     if os.access(p, os.X_OK)), None)
needs_bin = pytest.mark.skipif(BIN is None, reason="EvalMaxSAT binary not found")
MSE23 = os.path.join(ROOT, "data", "raw", "mse_2024", "mse23-uw-small")


def _write(tmp_path, name, body):
    p = tmp_path / name
    p.write_text(textwrap.dedent(body).lstrip())
    return str(p)


# --------------------------------------------------------------------------- dialects

def test_new_dialect_hard_and_weighted_soft(tmp_path):
    p = _write(tmp_path, "a.wcnf", """
        c new format: no p line
        h 1 2 0
        h -1 -2 0
        5 1 0
        3 2 0
        2 -1 3 0
    """)
    f = oe.read_formula(p)
    assert f.fmt == "wcnf_new"
    assert f.hard == [[1, 2], [-1, -2]]
    assert f.soft == [(5, [1]), (3, [2]), (2, [-1, 3])]
    assert f.n_vars == 3


def test_new_dialect_soft_only_is_not_read_as_cnf(tmp_path):
    # 17 of the MSE 2023/2024 files have no hard clause; the weight must not become a literal
    p = _write(tmp_path, "b.wcnf", """
        c soft only
        7 1 -2 0
        4 2 0
    """)
    f = oe.read_formula(p)
    assert f.fmt == "wcnf_new"
    assert f.hard == []
    assert f.soft == [(7, [1, -2]), (4, [2])]
    assert f.n_vars == 2


def test_old_dialects_unchanged(tmp_path):
    w = oe.read_formula(_write(tmp_path, "c.wcnf", """
        p wcnf 3 3 10
        10 1 2 0
        1 -1 0
        2 3 0
    """))
    assert w.fmt == "wcnf" and w.hard == [[1, 2]] and w.soft == [(1, [-1]), (2, [3])]
    c = oe.read_formula(_write(tmp_path, "d.cnf", """
        p cnf 2 2
        1 2 0
        -1 0
    """))
    assert c.fmt == "cnf" and c.hard == [] and c.soft == [(1, [1, 2]), (1, [-1])]


def test_p_line_after_clauses_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        oe.read_formula(_write(tmp_path, "e.wcnf", """
            h 1 0
            p wcnf 1 1 2
        """))


def test_weighted_cost_and_hard_violation():
    f = oe.Formula(n_vars=2, hard=[[1, 2]], soft=[(5, [1]), (3, [2])], fmt="wcnf_new")
    assert oe.cost_of_model(f, [False, True, False]) == (3, 0)
    assert oe.cost_of_model(f, [False, False, False]) == (None, 1)


# --------------------------------------------------------------------------- live

@needs_bin
def test_live_new_dialect_optimum_verified(tmp_path):
    # x1 xor x2 by hard clauses; soft prefers x1 (5) over x2 (3) -> optimum 3
    p = _write(tmp_path, "f.wcnf", """
        h 1 2 0
        h -1 -2 0
        5 1 0
        3 2 0
    """)
    r = oe.solve_one(p, BIN, timeout_s=60, extra_args=[], keep_wcnf=False)
    assert r.status == "optimal" and r.opt_cost == 3 and r.verified is True
    assert r.stopped_by is None and r.exit_code == 30   # MSE: OPTIMUM FOUND


@needs_bin
def test_live_new_dialect_soft_only(tmp_path):
    p = _write(tmp_path, "g.wcnf", """
        7 1 0
        4 -1 0
    """)
    r = oe.solve_one(p, BIN, timeout_s=60, extra_args=[], keep_wcnf=False)
    assert r.status == "optimal" and r.opt_cost == 4 and r.verified is True


@needs_bin
@pytest.mark.skipif(not os.path.isfile(os.path.join(MSE23, "setcover-sts-data.135.wcnf")),
                    reason="MSE 2023 instance not staged (this tree stages only the batch's MSE files)")
def test_live_sigterm_gives_verified_upper_bound():
    # RC2 is 4+ above best-known here after 1800 s; EvalMaxSAT will not prove it in 5 s
    p = os.path.join(MSE23, "setcover-sts-data.135.wcnf")
    r = oe.solve_one(p, BIN, timeout_s=5, extra_args=[], keep_wcnf=False, term_grace_s=60)
    assert r.status == "timeout"
    assert r.stopped_by == "sigterm"
    if r.s_line == "SATISFIABLE":
        assert r.exit_code == 10
        assert r.verified is True and r.best_cost is not None and r.best_cost >= 103  # best-known 103
    else:
        assert r.s_line == "UNKNOWN" and r.best_cost is None
