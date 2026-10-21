"""Keep-satisfied feasible moves (`hard.moves.keep_sat: ks | ks2`, src/evo/hard.py moves 7-8).

- config: default none, bad values refused (also by the shard runner, before the run);
- `none` is the old move exactly (same run, same record apart from the new zero counters);
- a ks model is hard-feasible, satisfies the target and keeps every satisfied unit;
- ks2 retries without the core's kept literals: a model that ks cannot find;
- end to end on a hard instance with only unit soft clauses: feasible, counters recorded.
"""
from __future__ import annotations

import json
import os
import random
import time
import sys

import pytest
import yaml

pytest.importorskip("pysat")

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
from evo.hard import HardSAT, HardStats, SoftView, _keep_sat_move, feasible_moves, hard_cfg  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.population import evaluate_assignment  # noqa: E402


def write(tmp_path, name, n, hard, soft):
    """hard: list of literal lists; soft: list of (weight, literal list)."""
    top = sum(w for w, _ in soft) + 1
    lines = [f"{top} " + " ".join(map(str, c)) + " 0" for c in hard]
    lines += [f"{w} " + " ".join(map(str, c)) + " 0" for w, c in soft]
    p = tmp_path / f"{name}.wcnf"
    p.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return WCNF.parse_dimacs(str(p)), str(p)


def unit_instance(tmp_path, seed=0, n=40, m_hard=60, m_soft=30):
    rng = random.Random(seed)
    hard = [[v if rng.random() < 0.5 else -v for v in rng.sample(range(1, n + 1), 3)] for _ in range(m_hard)]
    soft = [(rng.randint(1, 5), [rng.choice([1, -1]) * rng.randint(1, n)]) for _ in range(m_soft)]
    return write(tmp_path, f"u{seed}", n, hard, soft)


def sat_lit(a, l):
    return a[l] if l > 0 else not a[-l]


def test_config_default_and_refusal():
    assert hard_cfg({})["move_keep_sat"] == "none"
    assert hard_cfg({"hard": {"moves": {"keep_sat": "KS2"}}})["move_keep_sat"] == "ks2"
    with pytest.raises(ValueError):
        hard_cfg({"hard": {"moves": {"keep_sat": "yes"}}})


@pytest.mark.parametrize("seed", range(6))
def test_ks_model_keeps_every_satisfied_unit(tmp_path, seed):
    w, _ = unit_instance(tmp_path, seed)
    sat, soft = HardSAT(w), SoftView(w)
    status, cur = sat.model([False] * (w.n_vars + 1))
    assert status == "sat"
    kept = [c[0] for _, c in soft.clauses if sat_lit(cur, c[0])]
    found = 0
    for _, c in soft.clauses:
        if sat_lit(cur, c[0]):
            continue
        st = HardStats()
        y = _keep_sat_move(cur, soft, sat, c[0], "ks", None, None, st)
        if y is None:
            assert st.ks_unsat + st.ks_budget == 1
            continue
        found += 1
        assert evaluate_assignment(w, y)[1] == 0                  # hard-feasible
        assert sat_lit(y, c[0]) and all(sat_lit(y, l) for l in kept)
        assert soft.cost(y) < soft.cost(cur)
    sat.close()


def test_ks2_retries_without_the_core(tmp_path):
    # hard: not(a and b); soft units a (w 1) and b (w 5). From a=1, b=0, keeping a
    # makes b impossible; the core is {a, b}, so ks2 drops a and finds b=1.
    w, _ = write(tmp_path, "core", 2, [[-1, -2]], [(1, [1]), (5, [2])])
    sat, soft = HardSAT(w), SoftView(w)
    cur = [False, True, False]
    st = HardStats()
    assert _keep_sat_move(cur, soft, sat, 2, "ks", None, None, st) is None and st.ks_unsat == 1
    st2 = HardStats()
    y = _keep_sat_move(cur, soft, sat, 2, "ks2", None, None, st2)
    assert y is not None and y[2] and not y[1]
    assert (st2.ks2_retries, st2.ks2_sat) == (1, 1) and st2.ks_core_len_sum >= 2
    assert soft.cost(y) == 1 < soft.cost(cur) == 5
    sat.close()


@pytest.mark.parametrize("mode", ["ks", "ks2"])
def test_feasible_moves_with_keep_sat_never_worse_and_feasible(tmp_path, mode):
    w, _ = unit_instance(tmp_path, 7)
    sat, soft = HardSAT(w), SoftView(w)
    _, x = sat.model([False] * (w.n_vars + 1))
    st = HardStats()
    y = feasible_moves(x, soft, sat, random.Random(1), 50, 0.05, time.time() + 60, st, None, 3, mode)
    assert evaluate_assignment(w, y)[1] == 0 and soft.cost(y) <= soft.cost(x)
    assert st.ks_calls > 0 and st.ks_calls == st.ks_sat + st.ks_unsat + st.ks_budget
    sat.close()


def _cfg(keep=None):
    cfg = {"impl": "v3", "time_limit_s": 1000.0,
           "ea": {"enabled": True, "pop_size": 6, "tournament_k": 3, "pmutate": 0.05,
                  "elitism": True, "max_gens": 3, "deadline_mode": "clip"},
           "ls": {"ls_polish_flips": 150, "flip_budget": 150, "time_limit_s": 3.5, "polish_cap": "flips_only"},
           "hard": {"moves": {"per_polish": 10}}}
    if keep is not None:
        cfg["hard"]["moves"]["keep_sat"] = keep
    return cfg


def test_none_is_the_old_move_exactly(tmp_path):
    w, _ = unit_instance(tmp_path, 3)
    a = run_memetic(w, _cfg(), rng_seed=4)
    w2, _ = unit_instance(tmp_path, 3)
    b = run_memetic(w2, _cfg("none"), rng_seed=4)
    assert a["meta"]["assign_bits"] == b["meta"]["assign_bits"]
    assert a["best_soft_weight"] == b["best_soft_weight"]
    ha, hb = dict(a["hard"]), dict(b["hard"])
    for d in (ha, hb):
        for k in ("glucose_init_s", "repair_s", "move_s"):
            d.pop(k)
    assert ha == hb and ha["ks_calls"] == 0


@pytest.mark.parametrize("mode", ["ks", "ks2"])
def test_end_to_end_keep_sat_feasible_and_recorded(tmp_path, mode):
    from cli import run_memetic_shard as shard
    w, path = unit_instance(tmp_path, 5)
    cp = tmp_path / "k.yaml"
    cp.write_text(yaml.safe_dump(_cfg(mode)))
    out = tmp_path / "o.jsonl"
    assert shard.main(["--instance", path, "--config", str(cp), "--seed", "1", "--budget-s", "20",
                       "--out", str(out)]) == 0
    r = json.loads(out.read_text().strip().splitlines()[-1])
    assert r["status"] == "ok" and r["hard_violations"] == 0 and r["hard"]["ks_calls"] > 0


def test_shard_refuses_bad_keep_sat_before_the_run(tmp_path):
    from cli import run_memetic_shard as shard
    _, path = unit_instance(tmp_path, 5)
    cp = tmp_path / "bad.yaml"
    cp.write_text(yaml.safe_dump(_cfg("always")))
    out = tmp_path / "o.jsonl"
    assert shard.main(["--instance", path, "--config", str(cp), "--seed", "1", "--budget-s", "20",
                       "--out", str(out)]) == 2
    assert not out.exists()
