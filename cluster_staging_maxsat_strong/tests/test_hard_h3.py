"""H3 of the hard-clause solver: SAT-based repair R and feasible move M
(docs/current/HARD_CLAUSE_SOLVER_PLAN.md §6a, repo). Run from this tree's root."""
from __future__ import annotations

import os
import random
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

pytest.importorskip("pysat.solvers")

from evo.hard import HardSAT, HardStats, SoftView, feasible_moves, glucose_init, hard_cfg, repair  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.population import evaluate_assignment  # noqa: E402
from sat.cnf import WCNF  # noqa: E402
from test_hard_h2 import CFG, _planted, _write  # noqa: E402


@pytest.fixture
def partial3(tmp_path):
    hard, soft = _planted(150, 450, 300, seed=7)
    return WCNF.parse_dimacs(_write(tmp_path / "p3.wcnf", hard, soft))


def _hv(w, a):
    return evaluate_assignment(w, a)[1]


def test_hard_cfg_defaults():
    hc = hard_cfg({})
    assert hc["repair"] is True and hc["moves_per_polish"] == 200
    assert hc["move_noise"] == 0.05 and hc["move_conf_budget"] == 5000


def test_repair_returns_a_feasible_assignment_near_the_input(partial3):
    sat = HardSAT(partial3)
    st = HardStats()
    rng = random.Random(0)
    for _ in range(20):
        x = [False] + [rng.random() < 0.5 for _ in range(partial3.n_vars)]
        y = repair(x, sat, time.time() + 30, st)
        assert y is not None and _hv(partial3, y) == 0
    assert st.repair_calls == 20 and st.repair_failed == 0
    # phases steer the model: a feasible input comes back unchanged
    feas, _ = glucose_init(partial3, 1, rng, "jw", time.time() + 30, sat=sat)
    z = repair(feas[0], sat, time.time() + 30, st)
    assert z == feas[0]
    sat.close()


def test_repair_reports_a_passed_deadline(partial3):
    sat = HardSAT(partial3)
    st = HardStats()
    assert repair([False] * (partial3.n_vars + 1), sat, time.time() - 1, st) is None
    assert st.repair_failed == 1
    sat.close()


def test_moves_keep_feasibility_and_never_return_worse(partial3):
    sat = HardSAT(partial3)
    soft = SoftView(partial3)
    st = HardStats()
    rng = random.Random(1)
    members, _ = glucose_init(partial3, 3, rng, "jw", time.time() + 30, sat=sat)
    for x in members:
        y = feasible_moves(x, soft, sat, rng, 300, 0.05, time.time() + 30, st, 5000, 3)
        assert _hv(partial3, y) == 0
        assert soft.cost(y) <= soft.cost(x)
    assert st.moves_tried > 0 and st.moves_improving > 0
    sat.close()


def test_singleton_core_is_proven_and_becomes_a_lower_bound(tmp_path):
    # hard: x1 and x2 forced true; soft (-x1) weight 3 can never be satisfied,
    # soft (x3) weight 1 can
    w = WCNF.parse_dimacs(_write(tmp_path / "h.wcnf", [[1], [2]], [(3, [-1]), (1, [3]), (2, [-2, 3])]))
    sat = HardSAT(w)
    soft = SoftView(w)
    st = HardStats()
    x = [False, True, True, False]
    y = feasible_moves(x, soft, sat, random.Random(0), 50, 0.0, time.time() + 30, st)
    assert soft.cost(y) == 3.0 and _hv(w, y) == 0       # x3 made true, (-x1) impossible
    assert soft.singleton_cores == {0} and st.singleton_core_lb == 3.0
    sat.close()


def test_conflict_budget_sets_a_clause_aside_without_a_bound(partial3, monkeypatch):
    sat = HardSAT(partial3)
    soft = SoftView(partial3)
    st = HardStats()
    rng = random.Random(2)
    x, _ = glucose_init(partial3, 1, rng, "jw", time.time() + 30, sat=sat)
    monkeypatch.setattr(sat, "model", lambda *a, **k: ("budget", None))
    feasible_moves(x[0], soft, sat, rng, 30, 0.05, time.time() + 30, st, 10, 3)
    assert st.move_budget_misses > 0 and st.clauses_set_aside > 0
    assert st.singleton_cores == 0 and st.singleton_core_lb == 0.0   # a budget miss is not a proof
    sat.close()


def test_run_memetic_h3_children_feasible_and_cost_improves(partial3):
    res = run_memetic(partial3, dict(CFG, time_limit_s=8.0), rng_seed=1)
    h = res["hard"]
    assert h["children"] > 0 and h["children_infeasible_after_polish"] == 0
    assert h["repair_calls"] > 0 and h["moves_tried"] > 0
    tot = sum(float(c.weight) for c in partial3.clauses if not c.is_hard)
    assert tot - res["best_soft_weight"] < h["init_best_cost"]
    assert res["hard_violations"] == 0 and h["incumbent_infeasible_events"] == 0


def test_repair_and_moves_can_be_switched_off(partial3):
    cfg = dict(CFG, time_limit_s=3.0, hard={"phases": "jw", "repair": False, "moves": {"per_polish": 0}})
    h = run_memetic(partial3, cfg, rng_seed=1)["hard"]
    assert h["repair_calls"] == 0 and h["moves_tried"] == 0
