"""H2 of the hard-clause solver (docs/current/HARD_CLAUSE_SOLVER_PLAN.md, repo):
Glucose initialisation, the child-correct mutation guard, the no-op-counting
polish, and the feasibility bookkeeping of `impl: hard`.

Run from this tree's root: python -m pytest tests -q
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from evo.hard import glucose_init, hard_cfg, short_polish_hard  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.operators import mutate1  # noqa: E402
from evo.population import build_hard_occurs, evaluate_assignment, init_hard_satisfied  # noqa: E402
from sat.cnf import WCNF  # noqa: E402
from sat.walksat_v2 import walksat_polish_v2  # noqa: E402

pytest.importorskip("pysat.solvers")


def _write(path, hard, soft):
    """New-format WCNF: `h lits 0` hard, `w lits 0` soft."""
    with open(path, "w") as f:
        f.write("c test instance\n")
        for c in hard:
            f.write("h " + " ".join(map(str, c)) + " 0\n")
        for w, c in soft:
            f.write(f"{w} " + " ".join(map(str, c)) + " 0\n")
    return str(path)


def _planted(n, n_hard, n_soft, seed, k=3):
    """Random k-clauses; every hard clause is satisfied by a planted assignment
    (so the hard part is satisfiable), soft clauses are unconstrained."""
    rng = random.Random(seed)
    plant = [None] + [rng.random() < 0.5 for _ in range(n)]

    def clause():
        vs = rng.sample(range(1, n + 1), k)
        return [v if rng.random() < 0.5 else -v for v in vs]

    hard = []
    while len(hard) < n_hard:
        c = clause()
        if any((l > 0) == plant[abs(l)] for l in c):
            hard.append(c)
    soft = [(1, clause()) for _ in range(n_soft)]
    return hard, soft


@pytest.fixture
def partial3(tmp_path):
    # the §8.3 probe's hardest shape: n 150, hard ratio 3.0, soft ratio 2
    hard, soft = _planted(150, 450, 300, seed=7)
    return WCNF.parse_dimacs(_write(tmp_path / "p3.wcnf", hard, soft))


def _hv(wcnf, a):
    return evaluate_assignment(wcnf, a)[1]


# --- 1. Glucose initialisation ---------------------------------------------------

@pytest.mark.parametrize("phases", ["jw", "random"])
def test_glucose_init_members_are_feasible_and_distinct(partial3, phases):
    members, st = glucose_init(partial3, 20, random.Random(1), phases, time.time() + 60)
    assert st.status == "ok" and len(members) == 20 == st.init_members
    assert all(_hv(partial3, a) == 0 for a in members)
    assert st.init_distinct > 1          # phases make the members differ
    assert st.glucose_calls >= 20 and st.glucose_init_s > 0


def test_glucose_init_is_reproducible(partial3):
    a, _ = glucose_init(partial3, 8, random.Random(3), "jw", time.time() + 60)
    b, _ = glucose_init(partial3, 8, random.Random(3), "jw", time.time() + 60)
    assert a == b


def test_soft_only_variables_take_their_phase(tmp_path):
    # x3 occurs in no hard clause: Glucose does not decide it, the drawn phase does
    w = WCNF.parse_dimacs(_write(tmp_path / "s.wcnf", [[1, 2]], [(5, [3]), (1, [-1])]))
    members, st = glucose_init(w, 10, random.Random(0), "jw", time.time() + 30)
    assert st.status == "ok"
    assert all(_hv(w, a) == 0 for a in members)
    assert sum(a[3] for a in members) >= 7   # JW prior for x3 is clipped to 0.95


def test_glucose_init_hard_unsat(tmp_path):
    w = WCNF.parse_dimacs(_write(tmp_path / "u.wcnf", [[1], [-1]], [(1, [2])]))
    members, st = glucose_init(w, 5, random.Random(0), "jw", time.time() + 30)
    assert st.status == "hard_unsat" and members == []


def test_glucose_init_deadline_passed(partial3):
    members, st = glucose_init(partial3, 5, random.Random(0), "jw", time.time() - 1)
    assert st.status == "glucose_timeout" and members == []


def test_hard_cfg_rejects_unknown_phase_mode():
    with pytest.raises(ValueError):
        hard_cfg({"hard": {"phases": "zeros"}})


# --- 2. mutation guard sees the child --------------------------------------------

class _Rng:
    """random() from a fixed list: mutate1 asks it once per variable."""
    def __init__(self, vals):
        self.vals = list(vals)

    def random(self):
        return self.vals.pop(0)


def test_mutation_guard_uses_the_childs_vector(tmp_path):
    # hard (x1 v x2); child x1=T, x2=F satisfies it; flipping x1 would break it
    w = WCNF.parse_dimacs(_write(tmp_path / "m.wcnf", [[1, 2]], [(1, [3])]))
    hard = [cl for cl in w.clauses if cl.is_hard]
    occ = build_hard_occurs(hard, w.n_vars)

    child = [False, True, False, False]
    mutate1(child, 0.5, _Rng([0.0, 0.9, 0.9]), hard, occ, init_hard_satisfied(hard, child))
    assert child[1] is True and _hv(w, child) == 0        # correct vector: flip refused

    stale = [False]                                        # e.g. another member's vector
    child = [False, True, False, False]
    mutate1(child, 0.5, _Rng([0.0, 0.9, 0.9]), hard, occ, stale)
    assert child[1] is False and _hv(w, child) == 1        # the v1/v2 bug, reproduced


# --- 3. polish: no idling, feasibility kept ---------------------------------------

def test_noop_steps_count_against_the_budget(tmp_path):
    # hard units fix x1 = x2 = True; the soft clauses want them False, so from the
    # feasible start every candidate breaks a hard clause: every step is a no-op
    w = WCNF.parse_dimacs(_write(tmp_path / "n.wcnf", [[1], [2]], [(1, [-1]), (1, [-2])]))
    start = [True, True]
    old = walksat_polish_v2(w, start, rng_seed=1, max_flips=50, time_limit_s=0.3)
    assert old["total_flips"] == 0 and old["elapsed_sec"] >= 0.3   # v2 default: idles
    new = walksat_polish_v2(w, start, rng_seed=1, max_flips=50, time_limit_s=0.3,
                            budget_counts_noops=True)
    assert new["flips"] == 50 and new["noop_steps"] == 50 and new["total_flips"] == 0
    assert new["elapsed_sec"] < 0.2 and new["final_assign"] == [True, True]


def test_hard_polish_keeps_feasible_starts_feasible(partial3):
    members, _ = glucose_init(partial3, 6, random.Random(2), "jw", time.time() + 60)
    for i, a in enumerate(members):
        out, steps, noops = short_polish_hard(a, partial3, {"ls_polish_flips": 3000,
                                                            "time_limit_s": 5.0}, rng_seed=i)
        assert _hv(partial3, out) == 0
        assert evaluate_assignment(partial3, out)[0] >= evaluate_assignment(partial3, a)[0]
        assert steps <= 3000 and 0 <= noops <= steps


# --- 4. the whole run ------------------------------------------------------------

CFG = {"impl": "hard", "hard": {"phases": "jw"}, "time_limit_s": 6.0,
       "ea": {"enabled": True, "pop_size": 10, "tournament_k": 3, "pmutate": 0.02,
              "elitism": True, "max_gens": 1000000, "deadline_mode": "clip"},
       "ls": {"ls_polish_flips": 2000, "time_limit_s": 0.5, "flip_budget": 2000}}


def test_run_memetic_hard_end_to_end(partial3):
    t0 = time.time()
    res = run_memetic(partial3, CFG, rng_seed=1)
    h = res["hard"]
    assert res["impl"] == "hard" and h["status"] == "ok"
    assert h["init_members"] == 10 and h["init_infeasible"] == 0 and h["init_distinct"] > 1
    assert h["children"] > 0 and h["polish_calls"] == h["children"]
    assert h["incumbent_infeasible_events"] == 0
    assert h["hard_feasible_final"] is True and res["hard_violations"] == 0
    # Glucose time is inside the 6 s budget (clock starts before the init)
    assert h["glucose_init_s"] < res["elapsed_sec"] <= 6.0 + 1.0
    assert time.time() - t0 < 10


def test_run_memetic_hard_unsat_is_reported(tmp_path):
    w = WCNF.parse_dimacs(_write(tmp_path / "u.wcnf", [[1], [-1]], [(1, [2])]))
    res = run_memetic(w, CFG, rng_seed=1)
    assert res["stop_reason"] == "hard_unsat" and res["hard"]["status"] == "hard_unsat"
    assert res["hard_violations"] == 1 and res["hard"]["hard_feasible_final"] is False


def test_v1_v2_results_carry_no_hard_block(partial3):
    for impl in ("v1", "v2"):
        cfg = dict(CFG, impl=impl, time_limit_s=1.0)
        assert run_memetic(partial3, cfg, rng_seed=1)["hard"] is None


def test_shard_records_the_hard_block(tmp_path):
    hard, soft = _planted(60, 180, 120, seed=11)
    inst = _write(tmp_path / "s.wcnf", hard, soft)
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps(dict(CFG, time_limit_s=3.0)))
    out = tmp_path / "o.jsonl"
    r = subprocess.run([sys.executable, "-m", "src.cli.run_memetic_shard", "--instance", inst,
                        "--config", str(cfg), "--seed", "1", "--budget-s", "3", "--out", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-500:]
    rec = json.loads(out.read_text().splitlines()[-1])
    assert rec["status"] == "ok" and rec["memetic_impl"] == "hard"
    assert rec["hard"]["status"] == "ok" and rec["hard_violations"] == 0
