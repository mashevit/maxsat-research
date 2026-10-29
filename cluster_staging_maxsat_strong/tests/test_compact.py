"""C1: the compact instance equals the Python one (docs/current2/COMPILED_MEMETIC_PLAN.md).

- the C parser gives the same clauses, n_vars, hard_weight and is_wcnf as
  WCNF.parse_dimacs on both formats and their edge cases, and refuses what it
  refuses;
- the C tables equal NativeCore's Python-built ones (full and lean), and the
  once-per-run C passes equal the Python functions (scripts/compact_check.py);
- whole memetic runs (max_gens, no binding time limit) are identical on the
  Python instance and the compact one: same best assignment, children, flips,
  target hit; and the shard records agree with MAXSAT_COMPACT=0 and =1.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
for p in (SRC, HERE, os.path.join(TREE, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from sat.cnf import WCNF  # noqa: E402
from test_native import make_wcnf, pytestmark  # noqa: E402,F401
import compact_check as cc  # noqa: E402


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    d = tmp_path_factory.mktemp("native_build_compact")
    env = dict(os.environ, MAXSAT_NATIVE_BUILD_DIR=str(d))
    subprocess.run(["bash", os.path.join(TREE, "scripts", "build_native.sh")], check=True, env=env,
                   capture_output=True)
    old = os.environ.get("MAXSAT_NATIVE_BUILD_DIR")
    os.environ["MAXSAT_NATIVE_BUILD_DIR"] = str(d)
    import native.native as nat
    nat._LIB = None
    yield nat
    nat._LIB = None
    if old is None:
        os.environ.pop("MAXSAT_NATIVE_BUILD_DIR", None)
    else:
        os.environ["MAXSAT_NATIVE_BUILD_DIR"] = old


EDGE = {
    "legacy_top.wcnf": "c comment\n% percent\np wcnf 6 7 100\n100 1 -2 0\n3 2 2 -3 0\n5 4 -4 0\n"
                       "0 5 0\n1 -6 0\n  7 1 6 0\n100 -1 0\n",
    "legacy_notop.wcnf": "p wcnf 4 3\n2 1 -2 0\n1 3 4 0\n9 -4 0\n",
    "legacy_upper.wcnf": "P WCNF 3 2 10\n10 1 2 0\n4 -3 0\n",
    "legacy_cnf.cnf": "c x\np cnf 5 4\n1 -2 0\n2 3 -5 0\n\n4 0\n-1 -1 5 0\n",
    "legacy_crlf.wcnf": "p wcnf 3 2 9\r\n9 1 2 0\r\n2 -3 0\r\n",
    "legacy_empty_clause.wcnf": "p wcnf 3 3 9\n9 1 2 0\n4 0\n2 -3 0\n",
    "legacy_zero_lines.cnf": "p cnf 3 2\n1 2 0\n0\n-3 0\n",
    "legacy_bigtop.wcnf": "p wcnf 3 2 9223372036854775807\n9223372036854775807 1 2 0\n5 -3 0\n",
    "new.wcnf": "c new format\nh 1 -2 0\n3 2 3 0\n0 -1 0\nh -3 -3 0\n7 4 -4 2 0\n  h 2 0\n1 4 0\n",
    "new_tabs.wcnf": "h\t1\t2 0\n5\t-1 0\n",
    "new_weight0_only.wcnf": "0 1 0\n0 -1 2 0\n",
    "new_softless.wcnf": "h 1 2 0\nh -1 0\n",
    "new_plus.wcnf": "+3 1 0\nh -1 +2 0\n",
    "new_no_p_line.cnf": "c only comments\n1 2 0\n",   # no p line = new format: weight 1, literal 2
}
BAD = {
    "bad_unterminated.wcnf": "h 1 2\n",
    "bad_negweight.wcnf": "-3 1 0\n",
    "bad_bare0.wcnf": "h 1 0\n0\n",
    "bad_nonint.wcnf": "h 1 x 0\n",
    "bad_embedded0.wcnf": "3 1 0 2 0\n",
    "bad_weight.wcnf": "w 1 0\n",
    "bad_problem.wcnf": "p wcnf 3\n1 1 0\n",
    "bad_format.wcnf": "p xyz 3 1\n1 1 0\n",
    "bad_empty.wcnf": "c nothing\n\n",
    "bad_var_above_n.cnf": "p cnf 2 1\n1 3 0\n",
}


@pytest.mark.parametrize("name", sorted(EDGE))
def test_parse_edge_cases_equal(native, tmp_path, name):
    p = tmp_path / name
    p.write_bytes(EDGE[name].encode())
    assert cc.check_file(str(p)) == []


@pytest.mark.parametrize("name", sorted(BAD))
def test_both_refuse(native, tmp_path, name):
    from sat import compact as cpt
    p = tmp_path / name
    p.write_bytes(BAD[name].encode())
    with pytest.raises(Exception):
        WCNF.parse_dimacs(str(p))
    with pytest.raises(ValueError):
        cpt.load(str(p))


def write_mixed(tmp_path, name, n, m, seed, hard_frac=0.3, dup=True, new=False, w_max=20):
    """Random clauses with repeated and opposite literals (d == 0 cases)."""
    r = random.Random(seed)
    plant = [None] + [r.random() < 0.5 for _ in range(n)]   # hard clauses satisfied by it
    lines = []
    for _ in range(m):
        k = r.randint(1, 6)
        lits = [r.choice((1, -1)) * r.randint(1, n) for _ in range(k)]
        hard = r.random() < hard_frac
        if hard and not any((l > 0) == plant[abs(l)] for l in lits):
            lits[0] = -lits[0]
        if dup and r.random() < 0.3:
            lits.append(lits[0])
        if dup and r.random() < 0.2:
            lits.append(-lits[0])
        wt = r.randint(0, w_max)
        if new:
            lines.append(("h " if hard else f"{wt} ") + " ".join(map(str, lits)) + " 0")
        else:
            lines.append(f"{10 ** 6 if hard else wt} " + " ".join(map(str, lits)) + " 0")
    body = "\n".join(lines) + "\n"
    p = tmp_path / name
    p.write_text(body if new else f"p wcnf {n} {m} {10 ** 6}\n" + body)
    return str(p)


@pytest.mark.parametrize("new", [False, True])
@pytest.mark.parametrize("seed", [1, 2, 3])
def test_random_instances_tables_and_passes(native, tmp_path, new, seed):
    p = write_mixed(tmp_path, f"r{seed}.wcnf", n=40, m=160, seed=seed, new=new)
    assert cc.check_file(p) == []


SAMPLE = ["data/raw/mse_2024/mse24-small/judgment-aggregation-ja-kemeny-preflib-00049-00000300.wcnf",
          "data/raw/mse_2024/mse23-uw-small/mbd-b14_C-mbd14-0277.wcnf",
          "data/raw/mse_2024/mse24-small/causal-discovery_wt-causal_Bands_6_277.wcnf",
          "data/satlib_bench/bf/bf0432-007.cnf",
          "data/satlib_bench/jnh/jnh10.cnf"]


@pytest.mark.parametrize("rel", SAMPLE)
def test_local_instances(native, rel):
    p = os.path.join(TREE, rel)
    if not os.path.isfile(p):
        pytest.skip("instance not in this tree")
    assert cc.check_file(p) == []


def memetic_cfg(hard: bool):
    cfg = _memetic_cfg(hard)
    if hard:
        cfg["hard"] = {"moves": {"per_polish": 10}}   # fewer SAT moves: same paths, faster test
    return cfg


def _memetic_cfg(hard: bool):
    return {"impl": "v3", "hard_mode": "auto" if hard else "off",
            "ea": {"pop_size": 6, "max_gens": 12, "deadline_mode": "clip", "crossover": "px",
                   "mutation": "walk", "mutation_k": 4},
            "ls": {"ls_polish_flips": 80, "flip_budget": 80, "time_limit_s": 30.0, "core": "dls",
                   "tabu": "cc", "native": True},
            "time_limit_s": 600.0}


def strip_times(r):
    th = dict(r["target_hit"]) if r.get("target_hit") else None
    if th:
        th.pop("time_to_hit_s", None)
    v3 = dict(r["v3"] or {})
    hard = dict(r["hard"] or {})
    for k in [k for k in hard if k.endswith("_s")]:
        hard.pop(k)
    return (r["meta"]["assign_bits"], r["meta"]["children"], r["meta"]["ea_generations"], r["total_flips"],
            r["best_soft_weight"], r["hard_violations"], r["stop_reason"], th, v3, hard)


@pytest.mark.parametrize("case", [dict(n=60, m=240, hard_frac=0.0, w_max=1),
                                  dict(n=50, m=220, hard_frac=0.0, w_max=9),
                                  dict(n=40, m=150, hard_frac=0.25, w_max=5)])
@pytest.mark.parametrize("target", [False, True])
def test_memetic_runs_identical(native, tmp_path, case, target):
    from evo.memetic import run_memetic
    from sat import compact as cpt
    p = write_mixed(tmp_path, "e.wcnf", n=case["n"], m=case["m"], seed=7, hard_frac=case["hard_frac"],
                    w_max=case["w_max"], dup=False)
    for seed in (1, 2):
        w, cw = WCNF.parse_dimacs(p), cpt.load(p)
        tgt = None
        if target:
            r0 = run_memetic(WCNF.parse_dimacs(p), memetic_cfg(case["hard_frac"] > 0), rng_seed=seed)
            tgt = int(round(sum(float(c.weight) for c in w.clauses if not c.is_hard) - r0["best_soft_weight"])) + 1
        a = run_memetic(w, memetic_cfg(case["hard_frac"] > 0), rng_seed=seed, target_cost=tgt)
        b = run_memetic(cw, memetic_cfg(case["hard_frac"] > 0), rng_seed=seed, target_cost=tgt)
        assert strip_times(a) == strip_times(b), seed


def test_shard_records_agree(native, tmp_path):
    import yaml
    from cli import run_memetic_shard as shard
    p = write_mixed(tmp_path, "s.wcnf", n=50, m=200, seed=11, hard_frac=0.0, w_max=4, dup=False)
    cfgp = tmp_path / "c.yaml"
    cfgp.write_text(yaml.safe_dump(memetic_cfg(False)))
    recs = {}
    for flag in ("0", "1"):
        os.environ["MAXSAT_COMPACT"] = flag
        out = tmp_path / f"o{flag}.jsonl"
        assert shard.main(["--instance", p, "--config", str(cfgp), "--seed", "3", "--budget-s", "60",
                           "--out", str(out)]) == 0
        recs[flag] = json.loads(out.read_text().strip().splitlines()[-1])
    os.environ.pop("MAXSAT_COMPACT", None)
    a, b = recs["0"], recs["1"]
    assert a["compact_instance"] is False and b["compact_instance"] is True
    for k in ("n_vars", "n_clauses", "n_hard", "n_soft", "soft_total_weight", "best_cost", "hard_violations",
              "unsat_soft_clauses", "best_assignment_hash", "children", "total_flips", "ea_generations",
              "screen_frac", "preprocess", "hparams"):
        if k == "hparams" and a[k]:
            assert {x: a[k][x] for x in a[k] if x != "hparams_s"} == {x: b[k][x] for x in b[k] if x != "hparams_s"}
            continue
        assert a[k] == b[k], k


# ---------------------------------------------------------------- C2 (per child)

VARIANTS = {
    "lean": {"ls": {"nbrs": "lean"}},
    "px_min_q_99": {"ea": {"px_min_q": 99}},                       # every PX falls back to clause-aware
    "px_mutate_only": {"ea": {"px_min_q": 99, "px_fallback": "mutate_only"}},
    "clause_aware": {"ea": {"crossover": "clause_aware"}},
    "count": {"ea": {"mutation": "count"}},
    "diff": {"ea": {"mutation": "diff"}},
    "weights_run": {"ls": {"weights": "run"}},
    "walksat_tenure": {"ls": {"core": "walksat", "tabu": "tenure", "tabu_tenure": 5}},
    "lean_walk": {"ls": {"nbrs": "lean"}, "ea": {"mutation": "walk"}},
}


def variant_cfg(hard: bool, name: str):
    cfg = memetic_cfg(hard)
    for sec, kv in VARIANTS[name].items():
        cfg[sec] = dict(cfg[sec], **kv)
    return cfg


@pytest.mark.parametrize("name", sorted(VARIANTS))
@pytest.mark.parametrize("hard", [False, True])
def test_memetic_variants_identical(native, tmp_path, name, hard):
    from evo.memetic import run_memetic
    from sat import compact as cpt
    p = write_mixed(tmp_path, "v.wcnf", n=45, m=180, seed=13, hard_frac=0.2 if hard else 0.0, w_max=6, dup=False)
    for seed in (1, 2):
        a = run_memetic(WCNF.parse_dimacs(p), variant_cfg(hard, name), rng_seed=seed)
        b = run_memetic(cpt.load(p), variant_cfg(hard, name), rng_seed=seed)
        assert strip_times(a) == strip_times(b), (name, seed)
        assert b["meta"]["children"] > 0, (name, seed, b["stop_reason"])
        if name.startswith("px_min_q"):
            assert b["v3"]["px_fallbacks"] > 0


class _P:
    def __init__(self, a, fit):
        self.assign01, self.fitness = a, fit


@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("hard_frac", [0.0, 0.3])
def test_unit_twins_px_xo_guard(native, tmp_path, seed, hard_frac):
    """px_cross, xo_cross and the guard against the Python functions on random parents."""
    from evo.v3 import partition_crossover, _guarded_flip
    from evo.impl_v2 import clause_aware_crossover1_v2
    from evo.population import init_hard_satisfied, build_hard_occurs
    from sat import compact as cpt
    from sat.ls_v3 import set_nbrs_mode
    p = write_mixed(tmp_path, "u.wcnf", n=50, m=200, seed=30 + seed, hard_frac=hard_frac, w_max=5)
    w, cw = WCNF.parse_dimacs(p), cpt.load(p)
    r = random.Random(seed)
    hard = [cl for cl in w.clauses if cl.is_hard]
    occ = build_hard_occurs(hard, w.n_vars)
    for mode in ("full", "lean"):
        set_nbrs_mode(w, mode)
        set_nbrs_mode(cw, mode)
        for t in range(15):
            A = [False] + [r.random() < 0.5 for _ in range(w.n_vars)]
            B = [x if r.random() < 0.7 else not x for x in A]
            B[0] = False
            fa, fb = r.choice([(1.0, 2.0), (2.0, 1.0), (1.5, 1.5)])
            ca, qa, ea = partition_crossover(_P(A, fa), _P(B, fb), w)
            cb, qb, eb = partition_crossover(_P(bytearray(A), fa), _P(bytearray(B), fb), cw)
            assert (list(map(bool, ca)), qa, ea) == (list(map(bool, cb)), qb, eb), (mode, t)
            xa = clause_aware_crossover1_v2(_P(A, fa), _P(B, fb), w, r)
            xb = clause_aware_crossover1_v2(_P(bytearray(A), fa), _P(bytearray(B), fb), cw, r)
            assert list(map(bool, xa)) == list(map(bool, xb)), t
    if hard:
        for t in range(20):
            A = [False] + [r.random() < 0.5 for _ in range(w.n_vars)]
            hs_py = init_hard_satisfied(hard, A)
            buf = bytearray(A)
            g = cw.guard(buf)
            assert list(map(bool, g.hsat)) == hs_py
            for _ in range(10):
                v = r.randint(1, w.n_vars)
                assert _guarded_flip(A, v, (hard, occ, hs_py)) == _guarded_flip(buf, v, g)
                assert list(map(bool, buf)) == A and list(map(bool, g.hsat)) == hs_py


# ---------------------------------------------------------------- C3 (hard mode)

@pytest.mark.parametrize("seed", range(3))
def test_softview_and_hard_clauses_twins(native, tmp_path, seed):
    from evo.hard import SoftView, _hard_clause_lists
    from sat import compact as cpt
    p = write_mixed(tmp_path, "h.wcnf", n=40, m=180, seed=50 + seed, hard_frac=0.3, w_max=7)
    w, cw = WCNF.parse_dimacs(p), cpt.load(p)
    assert list(_hard_clause_lists(cw)) == _hard_clause_lists(w)
    assert len(_hard_clause_lists(cw)) == len(_hard_clause_lists(w))
    a, b = SoftView(w), cpt.CSoftView(cw)
    r = random.Random(seed)
    for t in range(20):
        A = [False] + [r.random() < 0.5 for _ in range(w.n_vars)]
        if t == 10:   # exclusion sets as feasible_moves fills them
            for sv in (a, b):
                sv.singleton_cores.update({0, 3, 5})
                sv.set_aside.update({1, 7})
        assert a.cost(A) == b.cost(bytearray(A))
        assert a.unsat(A) == b.unsat(bytearray(A))
        keep_py = tuple(c[0] for _, c in a.clauses if len(c) == 1 and (A[c[0]] if c[0] > 0 else not A[-c[0]]))
        assert keep_py == b.unit_sat_lits(bytearray(A))


@pytest.mark.parametrize("keep_sat", ["none", "ks", "ks2"])
def test_memetic_hard_moves_identical(native, tmp_path, keep_sat):
    from evo.memetic import run_memetic
    from sat import compact as cpt
    p = write_mixed(tmp_path, "k.wcnf", n=45, m=200, seed=61, hard_frac=0.25, w_max=6, dup=False)
    cfg = memetic_cfg(True)
    cfg["hard"] = {"moves": {"per_polish": 25, "keep_sat": keep_sat}}
    for seed in (1, 2, 3):
        a = run_memetic(WCNF.parse_dimacs(p), cfg, rng_seed=seed)
        b = run_memetic(cpt.load(p), cfg, rng_seed=seed)
        assert strip_times(a) == strip_times(b), (keep_sat, seed)
        assert b["hard"]["moves_tried"] > 0 and b["hard"]["glucose_calls"] > 0
        if keep_sat != "none":
            assert b["hard"]["ks_calls"] > 0


@pytest.mark.parametrize("rel", SAMPLE + ["data/generated/calib_2sat_sc2"])
def test_build_kernel_compact_stream_equal(native, rel):
    """build_kernel on the compact instance (clauses streamed from the C arrays) equals the
    reference kernel on the Python instance (COMPILED_MEMETIC_PLAN.md §12)."""
    from sat import compact as cpt
    from test_kernel_fast import same_build, kernel_items
    from sat.kernel import build_kernel
    p = os.path.join(TREE, rel)
    if os.path.isdir(p):
        fs = sorted(f for f in os.listdir(p) if f.endswith(".wcnf") and os.path.getsize(os.path.join(p, f)) < 3_000_000)
        p = os.path.join(p, fs[0]) if fs else ""
    if not os.path.isfile(p):
        pytest.skip("instance not in this tree")
    w = WCNF.parse_dimacs(p)
    assert same_build(w)
    kc, cc_ = build_kernel(cpt.load(p))
    kp, cp = build_kernel(w)
    assert cc_ == cp and (kc is None) == (kp is None)
    if kp is not None:
        assert kernel_items(kc) == kernel_items(kp) and kc.rec == kp.rec and kc.var_of == kp.var_of


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_build_kernel_compact_random(native, tmp_path, seed):
    from sat import compact as cpt
    from test_kernel_fast import kernel_items
    from sat.kernel import build_kernel
    p = write_mixed(tmp_path, f"k{seed}.wcnf", n=40, m=160, seed=seed, new=False)
    kc, cc_ = build_kernel(cpt.load(p))
    kp, cp = build_kernel(WCNF.parse_dimacs(p))
    assert cc_ == cp and (kc is None) == (kp is None)
    if kp is not None:
        assert kernel_items(kc) == kernel_items(kp) and kc.rec == kp.rec
