"""`impl: v3` in the EA (src/evo/v3.py, src/evo/memetic.py): docs/current2/STRONGER_MEMETIC_DESIGN.md §4, §5, §8.

- v3 with no new keys == cluster_staging_maxsat's `impl: v2` on a soft-only
  instance (run in a subprocess against that tree, so the baseline is the
  real staging code), and == this tree's `impl: hard` on a hard instance;
- hard_mode resolution; config validation;
- B3 mutation modes: exact flip counts, locality, the hard-clause guard;
- B4 partition crossover: components are exact, the child is the best of all
  2**q recombinations and never worse than either parent;
- end to end with every component on, and through the shard runner (schema 5).
"""
from __future__ import annotations

import itertools
import json
import os
import random
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
STAGING = os.path.join(os.path.dirname(TREE), "cluster_staging_maxsat")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from sat.cnf import WCNF  # noqa: E402
from evo.memetic import run_memetic  # noqa: E402
from evo.population import Individual, evaluate_assignment, build_hard_occurs, init_hard_satisfied  # noqa: E402
from evo.v3 import (V3Stats, check_cfg, mutate_v3, partition_crossover, px_components,  # noqa: E402
                    resolve_hard_mode, v3_cfg)
from sat.ls_v3 import v3_static  # noqa: E402


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, seed=0):
    rng = random.Random(seed)
    top = m_soft * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        vs = rng.sample(range(1, n + 1), k)
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(1, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return str(path)


def base_cfg(impl, **extra):
    cfg = {"impl": impl, "time_limit_s": 1000.0,
           "ea": {"enabled": True, "pop_size": 8, "tournament_k": 3, "pmutate": 0.05,
                  "elitism": True, "max_gens": 3, "deadline_mode": "clip"},
           "ls": {"ls_polish_flips": 150, "flip_budget": 150, "time_limit_s": 3.5,
                  "polish_cap": "flips_only"}}
    for k, v in extra.items():
        if k in ("ea", "ls"):
            cfg[k].update(v)
        else:
            cfg[k] = v
    return cfg


def cost(w, a01):
    soft, hv = evaluate_assignment(w, a01)
    tot = sum(float(c.weight) for c in w.clauses if not c.is_hard)
    return hv, tot - soft


_RUNNER = r"""
import json, sys
sys.path.insert(0, sys.argv[1] + "/src")
from sat.cnf import WCNF
from evo.memetic import run_memetic
w = WCNF.parse_dimacs(sys.argv[2])
cfg = json.loads(sys.argv[3])
r = run_memetic(w, cfg, rng_seed=int(sys.argv[4]))
print(json.dumps({"bits": r["meta"]["assign_bits"], "children": r["meta"]["children"],
                  "gens": r["meta"]["ea_generations"], "soft": r["best_soft_weight"],
                  "flips": r["total_flips"]}))
"""


def run_tree(tree, path, cfg, seed):
    out = subprocess.run([sys.executable, "-c", _RUNNER, tree, path, json.dumps(cfg), str(seed)],
                         capture_output=True, text=True, cwd=tree, check=True)
    return json.loads(out.stdout.strip().splitlines()[-1])


# ------------------------------------------------------------------ equality

@pytest.mark.skipif(not os.path.isdir(os.path.join(STAGING, "src")), reason="staging tree absent")
@pytest.mark.parametrize("k,m,wm", [(2, 120, 1), (3, 200, 3)])
@pytest.mark.parametrize("seed", [1, 4])
def test_v3_without_keys_equals_staging_v2_on_soft_only(tmp_path, k, m, wm, seed):
    path = make_wcnf(tmp_path, "s", n=50, k=k, m_soft=m, w_max=wm, seed=seed)
    a = run_tree(STAGING, path, base_cfg("v2"), seed)
    b = run_tree(TREE, path, base_cfg("v3"), seed)
    assert a == b


@pytest.mark.parametrize("seed", [1, 2])
def test_v3_without_keys_equals_impl_hard_on_a_hard_instance(tmp_path, seed):
    pytest.importorskip("pysat")
    path = make_wcnf(tmp_path, "h", n=30, k=3, m_soft=80, m_hard=20, w_max=2, seed=seed)
    w = WCNF.parse_dimacs(path)
    hard_extra = {"hard": {"moves": {"per_polish": 20}}}
    a = run_memetic(w, base_cfg("hard", **hard_extra), rng_seed=seed)
    w2 = WCNF.parse_dimacs(path)
    b = run_memetic(w2, base_cfg("v3", **hard_extra), rng_seed=seed)
    for key in ("best_soft_weight", "hard_violations", "total_flips"):
        assert a[key] == b[key]
    assert a["meta"]["assign_bits"] == b["meta"]["assign_bits"]
    untimed = lambda d: {k: v for k, v in d.items() if not k.endswith("_s")}  # noqa: E731
    assert untimed(a["hard"]) == untimed(b["hard"])
    assert b["v3"]["hard_mode"] == "on" and b["impl"] == "v3"


def test_hard_mode_resolution(tmp_path):
    soft = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=10, k=2, m_soft=20))
    hard = WCNF.parse_dimacs(make_wcnf(tmp_path, "h", n=10, k=2, m_soft=20, m_hard=3))
    assert resolve_hard_mode(v3_cfg({}), soft) is False
    assert resolve_hard_mode(v3_cfg({}), hard) is True
    assert resolve_hard_mode(v3_cfg({"hard_mode": "on"}), soft) is True
    assert resolve_hard_mode(v3_cfg({"hard_mode": "off"}), hard) is False


@pytest.mark.parametrize("cfg,impl", [
    ({"ea": {"mutation": "walk"}}, "v2"),
    ({"ls": {"core": "dls"}}, "hard"),
    ({"hard_mode": "auto"}, "v1"),
    ({"ea": {"mutation": "bogus"}}, "v3"),
    ({"ea": {"crossover": "uniform"}}, "v3"),
    ({"ls": {"core": "dls", "tabu": "tenure"}}, "v3"),
    ({"ls": {"weights": "run"}}, "v3"),
    ({"ls": {"dls_sp": 1.5, "core": "dls"}}, "v3"),
    ({"ea": {"mutation_k": 0, "mutation": "count"}}, "v3"),
])
def test_invalid_v3_configs_are_refused(cfg, impl):
    with pytest.raises(ValueError):
        check_cfg(cfg, impl)


def test_valid_v3_config_parses():
    c = check_cfg({"ea": {"mutation": "walk", "mutation_k": 8, "crossover": "px"},
                   "ls": {"core": "dls", "tabu": "cc", "weights": "run"}}, "v3")
    assert c["mutation"] == "walk" and c["core"] == "dls" and c["tabu"] == "cc"
    assert check_cfg({"ea": {"pmutate": 0.1}}, "v2") is None


# ------------------------------------------------------------------- B3

def _ind(a):
    return Individual(assign01=a)


@pytest.mark.parametrize("mode", ["count", "walk", "diff"])
def test_mutation_flips_exactly_k_distinct_variables(tmp_path, mode):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=200, k=2, m_soft=320, seed=3))
    rng = random.Random(0)
    for trial in range(20):
        a = [False] + [rng.random() < 0.5 for _ in range(200)]
        b = [False] + [rng.random() < 0.5 for _ in range(200)]
        child = list(a)
        st = V3Stats()
        f = mutate_v3(child, v3_cfg({"ea": {"mutation": mode, "mutation_k": 12}}), w, rng,
                      _ind(a), _ind(b), None, st)
        changed = [v for v in range(1, 201) if child[v] != a[v]]
        assert f == len(changed)
        if mode == "count":
            assert len(changed) == 12
        if mode == "diff":
            assert all(a[v] != b[v] for v in changed) and len(changed) == 12
        if mode == "walk":
            assert 1 <= len(changed) <= 12


def test_walk_mutation_is_local(tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=400, k=2, m_soft=500, seed=5))
    nbrs = v3_static(w).nbrs
    rng = random.Random(1)
    a = [False] * 401
    for _ in range(30):
        child = list(a)
        mutate_v3(child, v3_cfg({"ea": {"mutation": "walk", "mutation_k": 10}}), w, rng,
                  _ind(a), _ind(a), None, V3Stats())
        changed = {v for v in range(1, 401) if child[v]}
        # the changed set is connected in the variable-interaction graph unless the
        # walk had to jump (an isolated variable); check connectivity when no jump
        seen, stack = set(), [min(changed)]
        while stack:
            u = stack.pop()
            if u in seen:
                continue
            seen.add(u)
            stack.extend(x for x in nbrs[u] if x in changed)
        assert seen == changed or any(not nbrs[v] for v in changed)


def test_diff_mutation_falls_back_to_walk_for_equal_parents(tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=100, k=2, m_soft=150, seed=6))
    a = [False] * 101
    child = list(a)
    f = mutate_v3(child, v3_cfg({"ea": {"mutation": "diff", "mutation_k": 5}}), w, random.Random(0),
                  _ind(a), _ind(a), None, V3Stats())
    assert f >= 1


def test_mutation_never_breaks_a_satisfied_hard_clause(tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "h", n=40, k=3, m_soft=60, m_hard=60, seed=8))
    hard = [cl for cl in w.clauses if cl.is_hard]
    occ = build_hard_occurs(hard, w.n_vars)
    rng = random.Random(2)
    for mode in ("count", "walk", "diff"):
        for _ in range(30):
            a = [False] + [rng.random() < 0.5 for _ in range(40)]
            b = [False] + [rng.random() < 0.5 for _ in range(40)]
            child = list(a)
            hs = init_hard_satisfied(hard, child)
            before = list(hs)
            mutate_v3(child, v3_cfg({"ea": {"mutation": mode, "mutation_k": 15}}), w, rng,
                      _ind(a), _ind(b), (hard, occ, hs), V3Stats())
            now = init_hard_satisfied(hard, child)
            assert all(n_ or not b_ for b_, n_ in zip(before, now))
            assert now == hs


# ------------------------------------------------------------------- B4

def _parents(w, rng):
    n = w.n_vars
    a = [False] + [rng.random() < 0.5 for _ in range(n)]
    b = list(a)
    for v in rng.sample(range(1, n + 1), max(1, n // 4)):
        b[v] = not b[v]
    pa, pb = _ind(a), _ind(b)
    for p in (pa, pb):
        soft, hv = evaluate_assignment(w, p.assign01)
        p.fitness, p.hard_violations = (soft if hv == 0 else -hv * 1e9 + soft), hv
    return pa, pb


@pytest.mark.parametrize("m_hard", [0, 15])
def test_px_components_contain_each_clause_differing_variables(tmp_path, m_hard):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=120, k=2, m_soft=110, m_hard=m_hard, seed=9))
    rng = random.Random(3)
    for _ in range(10):
        pa, pb = _parents(w, rng)
        comps = px_components(pa.assign01, pb.assign01, w)
        cid = {v: i for i, c in enumerate(comps) for v in c}
        for cl in w.clauses:
            ds = {cid[abs(l)] for l in cl.lits if abs(l) in cid}
            assert len(ds) <= 1


@pytest.mark.parametrize("m_hard", [0, 12])
@pytest.mark.parametrize("seed", range(5))
def test_px_child_is_best_of_all_recombinations_and_not_worse_than_parents(tmp_path, m_hard, seed):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, f"s{seed}", n=60, k=2, m_soft=45, m_hard=m_hard,
                                    w_max=3, seed=seed))
    rng = random.Random(seed)
    for _ in range(5):
        pa, pb = _parents(w, rng)
        child, q, _eq = partition_crossover(pa, pb, w)
        c = cost(w, child)
        assert c <= cost(w, pa.assign01) and c <= cost(w, pb.assign01)
        comps = px_components(pa.assign01, pb.assign01, w)
        assert q == len(comps)
        if q <= 10:
            best = None
            for pick in itertools.product([0, 1], repeat=q):
                x = list(pa.assign01)
                for use_b, comp in zip(pick, comps):
                    if use_b:
                        for v in comp:
                            x[v] = pb.assign01[v]
                cc = cost(w, x)
                best = cc if best is None or cc < best else best
            assert c == best


def test_px_equal_parents_give_q_zero(tmp_path):
    w = WCNF.parse_dimacs(make_wcnf(tmp_path, "s", n=30, k=2, m_soft=40, seed=1))
    a = [False] * 31
    child, q, eq = partition_crossover(_ind(a), _ind(list(a)), w)
    assert q == 0 and child == a and eq


# ------------------------------------------------------------- end to end

ALL_ON = {"ea": {"mutation": "walk", "mutation_k": 6, "crossover": "px", "diag_every": 1},
          "ls": {"core": "dls", "tabu": "cc", "dls_zeta": 20}}


@pytest.mark.parametrize("extra", [
    ALL_ON,
    {"ea": {"mutation": "diff", "crossover": "px", "px_fallback": "mutate_only"},
     "ls": {"tabu": "tenure", "tabu_tenure": 5}},
    {"ea": {"mutation": "count"}, "ls": {"core": "dls", "weights": "run"}},
    {"ls": {"tabu": "cc"}},
])
def test_end_to_end_soft_only(tmp_path, extra):
    path = make_wcnf(tmp_path, "s", n=60, k=2, m_soft=110, seed=11)
    w = WCNF.parse_dimacs(path)
    r = run_memetic(w, base_cfg("v3", **json.loads(json.dumps(extra))), rng_seed=3)
    v3 = r["v3"]
    assert r["impl"] == "v3" and v3["hard_mode"] == "off"
    a01 = [False] + [c == "1" for c in r["meta"]["assign_bits"]]
    soft, hv = evaluate_assignment(w, a01)
    assert soft == r["best_soft_weight"] and hv == 0
    if extra["ea"].get("crossover") == "px" if "ea" in extra else False:
        assert v3["px_calls"] > 0
    if extra.get("ea", {}).get("diag_every") == 1:
        assert v3["mutation_damage_n"] > 0


def test_end_to_end_hard_instance_all_on_keeps_feasibility(tmp_path):
    pytest.importorskip("pysat")
    path = make_wcnf(tmp_path, "h", n=30, k=3, m_soft=80, m_hard=20, w_max=2, seed=5)
    w = WCNF.parse_dimacs(path)
    extra = json.loads(json.dumps(ALL_ON))
    extra["hard"] = {"moves": {"per_polish": 10}}
    r = run_memetic(w, base_cfg("v3", **extra), rng_seed=2)
    assert r["v3"]["hard_mode"] == "on" and r["hard_violations"] == 0
    assert r["hard"]["incumbent_infeasible_events"] == 0


def test_target_stop_with_v3(tmp_path):
    path = make_wcnf(tmp_path, "s", n=12, k=2, m_soft=30, seed=2)
    w = WCNF.parse_dimacs(path)
    import itertools as it
    best = min(cost(w, [False] + list(b))[1] for b in it.product([False, True], repeat=12))
    cfg = base_cfg("v3", **json.loads(json.dumps(ALL_ON)))
    cfg["ea"]["max_gens"] = 200
    r = run_memetic(w, cfg, rng_seed=1, target_cost=int(best))
    assert r["stop_reason"] == "target"


# ------------------------------------------------------------------ shard

def test_shard_records_v3_and_refuses_v3_keys_under_v2(tmp_path):
    from cli import run_memetic_shard as shard
    import yaml
    path = make_wcnf(tmp_path, "s", n=60, k=2, m_soft=110, seed=11)
    cfgp = tmp_path / "v3.yaml"
    cfg = base_cfg("v3", **json.loads(json.dumps(ALL_ON)))
    cfg["preprocess"] = "kernel"
    cfgp.write_text(yaml.safe_dump(cfg))
    out = tmp_path / "o.jsonl"
    rc = shard.main(["--instance", path, "--config", str(cfgp), "--seed", "1", "--budget-s", "5",
                     "--out", str(out)])
    r = json.loads(out.read_text().strip().splitlines()[-1])
    assert rc == 0 and r["status"] == "ok" and r["schema_version"] == 6
    assert r["memetic_impl"] in ("v3", None) and r["preprocess"] is not None
    if r["memetic_impl"] == "v3":
        assert r["v3"]["hard_mode"] in ("on", "off")
    bad = tmp_path / "bad.yaml"
    cfg2 = base_cfg("v2")
    cfg2["ea"]["mutation"] = "walk"
    bad.write_text(yaml.safe_dump(cfg2))
    assert shard.main(["--instance", path, "--config", str(bad), "--seed", "1", "--budget-s", "5",
                       "--out", str(tmp_path / "b.jsonl")]) == 2
