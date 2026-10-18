"""Exact kernel and its gate (src/sat/kernel.py) and the opt-in `preprocess: kernel`
path of run_memetic_shard.py (2026-10-18).

The brute-force tests check the property the shard relies on: for EVERY kernel
assignment the lifted assignment is feasible exactly when the kernel one is, and
then costs exactly the kernel cost plus the constant. Hence the optima agree.
Run from inside cluster_staging_maxsat/.
"""
from __future__ import annotations

import itertools
import json
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from cli import run_memetic_shard as shard  # noqa: E402
from sat import kernel as kern  # noqa: E402
from sat.cnf import WCNF  # noqa: E402


def write_wcnf(path, n, clauses):
    """clauses: (weight or "h", lits). Legacy `p wcnf` with top = soft total + 1."""
    top = sum(w for w, _ in clauses if w != "h") + 1
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"p wcnf {n} {len(clauses)} {top}\n")
        for w, lits in clauses:
            f.write(f"{top if w == 'h' else w} " + " ".join(map(str, lits)) + " 0\n")
    return str(path)


def load(tmp_path, n, clauses, name="f.wcnf"):
    return WCNF.parse_dimacs(write_wcnf(tmp_path / name, n, clauses))


def evaluate(wcnf, val):
    """(feasible, unsatisfied soft weight) of a 1-indexed boolean assignment."""
    hard = soft = 0
    for cl in wcnf.clauses:
        if not any(val[abs(l)] == (l > 0) for l in cl.lits):
            if cl.is_hard:
                hard += 1
            else:
                soft += cl.weight
    return hard == 0, soft


def all_assignments(n):
    for bits in itertools.product((False, True), repeat=n):
        yield [False, *bits]


def optimum(wcnf):
    costs = [c for ok, c in (evaluate(wcnf, v) for v in all_assignments(wcnf.n_vars)) if ok]
    return min(costs) if costs else None


def random_instance(rng):
    n = rng.randint(3, 8)
    clauses = []
    for _ in range(rng.randint(1, 3 * n)):
        k = rng.randint(1, 4)
        vs = [rng.randint(1, n) for _ in range(k)]  # repeats allowed: duplicates, tautologies
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        clauses.append(("h" if rng.random() < 0.25 else rng.randint(1, 3), lits))
    return n, clauses


def test_lift_is_exact_for_every_kernel_assignment_brute_force(tmp_path):
    rng = random.Random(20261018)
    checked = infeasible = 0
    for i in range(600):
        n, clauses = random_instance(rng)
        w = load(tmp_path, n, clauses)
        k, const = kern.build_kernel(w)
        if k is None:  # contradictory hard clauses
            assert optimum(w) is None
            infeasible += 1
            continue
        for kv in all_assignments(k.wcnf.n_vars):
            k_ok, k_cost = evaluate(k.wcnf, kv)
            ok, cost = evaluate(w, kern.lift(k, kv))
            assert ok == k_ok, (i, clauses)
            if ok:
                assert cost == k_cost + k.const, (i, clauses)
        o, ko = optimum(w), optimum(k.wcnf)
        assert (o is None) == (ko is None)
        if o is not None:
            assert o == ko + k.const
        checked += 1
    assert checked > 400 and infeasible > 0


def test_screen_frac_counts_pure_and_one_one_variables(tmp_path):
    # 1: pure; 2: one pos one neg; 3: two pos one neg; 4 never occurs.
    w = load(tmp_path, 4, [(1, [1, 2]), (1, [-2, 3]), (1, [3, 1]), (1, [-3, 1])])
    frac, occurring = kern.screen_frac(w)
    assert occurring == 3 and frac == pytest.approx(2 / 3)


def test_max2sat_at_alpha_2_passes_the_gate_with_binary_kernel_clauses(tmp_path):
    # Like calib_a (alpha 2, about half the variables removed); alpha 1.2 at this n
    # reduces to nothing.
    rng = random.Random(7)
    n = 400
    clauses = []
    while len(clauses) < 800:
        a, b = rng.sample(range(1, n + 1), 2)
        clauses.append((1, [a * rng.choice((1, -1)), b * rng.choice((1, -1))]))
    g = kern.gate(load(tmp_path, n, clauses), {"preprocess": "kernel"})
    assert g.decision == "kernel" and g.fields["screen_frac"] >= 0.2
    assert g.fields["kernel_max_len"] <= 2 and 0.2 <= g.fields["kernel_gain"] < 1
    assert g.kernel.n_hard == 0 and all(cl.weight >= 1 for cl in g.kernel.wcnf.clauses)


def _skip_length_instance():
    # x (=5) resolves (5 1 2), (-5 3 4) into (1 2 3 4); 1..4 have >= 2 occurrences of each sign.
    return 5, [(1, [5, 1, 2]), (1, [-5, 3, 4]), (1, [1, 3]), (1, [-1, -3]), (1, [2, 4]), (1, [-2, -4]),
               (1, [1, -2]), (1, [-1, 2]), (1, [3, -4]), (1, [-3, 4])]


@pytest.mark.parametrize("n,clauses,gate_cfg,decision", [
    (4, [(1, [1, 2, 3]), (1, [-1, -2, 4]), (1, [1, -3, -4]), (1, [-1, 3, 4]),
         (1, [2, 3, -4]), (1, [-2, -3, 4]), (1, [1, 2, -4]), (1, [-2, 3, 4])], {}, "skipped_screen"),
    (*_skip_length_instance(), {"gain_min": 0.0}, "skipped_length"),
    (*_skip_length_instance(), {"gain_min": 0.5}, "skipped_gain"),
    (1, [("h", [1]), ("h", [-1])], {}, "skipped_infeasible"),
    (3, [(1, [1, 2]), (2, [1, -3]), (1, [2, 3])], {}, "kernel_empty"),
])
def test_gate_decisions(tmp_path, n, clauses, gate_cfg, decision):
    g = kern.gate(load(tmp_path, n, clauses), {"preprocess": "kernel", "preprocess_gate": gate_cfg})
    assert g.decision == decision
    assert (g.kernel is not None) == decision.startswith("kernel")
    assert g.fields["preprocess_s"] >= 0


def test_unknown_mode_or_gate_key_is_refused():
    assert kern.preprocess_mode({}) == "none"
    with pytest.raises(ValueError):
        kern.preprocess_mode({"preprocess": "kernel2"})
    with pytest.raises(ValueError):
        kern.gate_params({"preprocess_gate": {"screen": 0.1}})


# --- run_memetic_shard.py --------------------------------------------------------

CFG = {"impl": "v2", "ea": {"enabled": True, "pop_size": 6, "tournament_k": 3, "pmutate": 0.02,
                            "elitism": True, "max_gens": 200, "deadline_mode": "clip"},
       "ls": {"ls_polish_flips": 200, "time_limit_s": 1.0, "flip_budget": 200}}


def sparse_instance(tmp_path):
    """Sparse random Max-2-SAT whose kernel is small enough to brute-force (seed searched)."""
    for seed in range(200):
        rng = random.Random(seed)
        n = 60
        clauses = []
        while len(clauses) < 78:
            a, b = rng.sample(range(1, n + 1), 2)
            clauses.append((1, [a * rng.choice((1, -1)), b * rng.choice((1, -1))]))
        w = load(tmp_path, n, clauses, f"sp{seed}.wcnf")
        k, _ = kern.build_kernel(w)
        if 4 <= k.wcnf.n_vars <= 14:
            opt = optimum(k.wcnf) + k.const
            if opt > 0:
                return str(tmp_path / f"sp{seed}.wcnf"), opt, k.wcnf.n_vars
    raise AssertionError("no suitable seed")


def run(tmp_path, inst, cfg, *extra):
    cpath = tmp_path / "cfg.json"
    cpath.write_text(json.dumps(cfg))
    out = tmp_path / "out.jsonl"
    rc = shard.main(["--instance", inst, "--config", str(cpath), "--seed", "1", "--budget-s", "20",
                     "--out", str(out), *extra])
    return rc, (json.loads(out.read_text()) if out.exists() else None)


def test_shard_kernel_path_reaches_the_optimum_scored_on_the_original(tmp_path):
    inst, opt, kn = sparse_instance(tmp_path)
    rc, r = run(tmp_path, inst, dict(CFG, preprocess="kernel"), "--oracle-cost", str(opt), "--stop-at-oracle")
    assert rc == 0 and r["status"] == "ok" and r["schema_version"] == 4
    assert r["preprocess"] == "kernel" and r["kernel_n_vars"] == kn and r["n_vars"] == 60
    assert r["stop_reason"] == "target" and r["best_cost"] == opt and r["is_optimal"]
    assert r["best_cost"] == r["kernel_best_cost"] + r["kernel_const"]
    assert r["time_to_target_s"] >= r["preprocess_s"] - 1e-3
    assert r["solver_time_limit_s"] == pytest.approx(20 - r["preprocess_s"], abs=1e-3)
    assert r["config"]["time_limit_s"] == 20.0  # the recorded config keeps the run budget
    w = WCNF.parse_dimacs(inst)
    rc, r2 = run(tmp_path, inst, dict(CFG, preprocess="kernel"), "--oracle-cost", str(opt),
                 "--stop-at-oracle", "--save-assignment")
    val = [False] + [c == "1" for c in r2["best_assignment_bits"]]
    assert len(val) == 61 and evaluate(w, val) == (True, opt)


def test_shard_without_preprocess_key_records_nulls(tmp_path):
    inst, opt, _ = sparse_instance(tmp_path)
    rc, r = run(tmp_path, inst, CFG, "--oracle-cost", str(opt))
    assert rc == 0 and r["preprocess"] is None
    assert all(r[k] is None for k in ("preprocess_s", "screen_frac", "kernel_n_vars", "kernel_best_cost",
                                      "solver_time_limit_s"))
    rc, r_none = run(tmp_path, inst, dict(CFG, preprocess="none"), "--oracle-cost", str(opt))
    assert r_none["preprocess"] is None and r_none["best_assignment_hash"] == r["best_assignment_hash"]


def test_shard_gate_skip_runs_the_original_inside_the_reduced_budget(tmp_path):
    n, clauses = 4, [(1, [1, 2, 3]), (1, [-1, -2, 4]), (1, [1, -3, -4]), (1, [-1, 3, 4]),
                     (1, [2, 3, -4]), (1, [-2, -3, 4]), (1, [1, 2, -4]), (1, [-2, 3, 4])]
    inst = write_wcnf(tmp_path / "dense.wcnf", n, clauses)
    rc, r = run(tmp_path, inst, dict(CFG, preprocess="kernel"))
    assert rc == 0 and r["preprocess"] == "skipped_screen" and r["kernel_n_vars"] is None
    assert r["kernel_best_cost"] is None and r["solver_time_limit_s"] <= 20


def test_shard_empty_kernel_is_solved_by_preprocessing(tmp_path):
    inst = write_wcnf(tmp_path / "pure.wcnf", 3, [(1, [1, 2]), (2, [1, -3]), (1, [2, 3])])
    rc, r = run(tmp_path, inst, dict(CFG, preprocess="kernel"), "--oracle-cost", "0", "--stop-at-oracle")
    assert rc == 0 and r["preprocess"] == "kernel_empty" and r["best_cost"] == 0
    assert r["stop_reason"] == "target" and r["time_to_target_s"] == pytest.approx(r["preprocess_s"], abs=1e-3)
    assert r["children"] == 0 and r["total_flips"] == 0


def test_shard_refuses_an_unknown_preprocess_mode(tmp_path):
    inst = write_wcnf(tmp_path / "pure.wcnf", 3, [(1, [1, 2])])
    rc, r = run(tmp_path, inst, dict(CFG, preprocess="kernel2"))
    assert rc == 2 and r is None
