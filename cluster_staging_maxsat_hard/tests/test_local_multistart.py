"""
`local_multistart_deeppolish` -- the no-EA ablation baseline for the memetic
solver (`src/evo/multistart.py`, dispatched by `src/cli/run_memetic_shard.py`).

What these tests are for: the baseline's scientific value rests entirely on two
claims that are easy to break silently. First, that it contains no evolutionary
machinery -- a stray import or a config default that reintroduces a population
would turn the control into a second copy of the treatment. Second, that its
local search *is* the memetic solver's local search, not a lookalike. Both are
asserted here directly rather than left to code review.

Section 8 covers the second arm, `local_multistart_jw_deeppolish`, which is this
baseline with `multistart.init: jw`. It carries a third claim of the same kind:
that its seeding is the EA's seeding, reused rather than reproduced, and that it
is *stochastic per restart*. A deterministic JW start would leave the arm running
one polish over and over, which would still produce plausible rows -- a failure
that no output inspection catches, so it is asserted directly too.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
# `evo.memetic` imports `llm.advisor` non-relatively, so `src/` itself has to be
# importable -- the same fixup `run_memetic_shard.py` applies at startup.
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from evo import multistart as ms_mod  # noqa: E402
from evo import population as pop_mod  # noqa: E402
from evo.multistart import run_multistart_ls  # noqa: E402
from sat.cnf import WCNF  # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "configs", "tier2", "local_multistart_deeppolish.yaml")
JW_CONFIG_PATH = os.path.join(ROOT, "configs", "tier2", "local_multistart_jw_deeppolish.yaml")
DEEPPOLISH_PATH = os.path.join(ROOT, "configs", "tier2", "memetic_deeppolish.yaml")


# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------
def _write_cnf(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(text).lstrip())
    return str(path)


@pytest.fixture
def tiny_unsat(tmp_path):
    """
    Six clauses over two variables, all soft weight 1. Every assignment leaves
    at least two unsatisfied -- (x1,x2) can only satisfy one of {x1,-x1} and one
    of {x2,-x2} -- so the optimum is 2 and no polish can reach 0. Small enough
    that a restart costs microseconds.
    """
    return _write_cnf(tmp_path / "tiny.cnf", """
        c tiny always-unsat
        p cnf 2 6
        1 0
        -1 0
        2 0
        -2 0
        1 2 0
        -1 -2 0
    """)


@pytest.fixture
def trivial_sat(tmp_path):
    """Satisfiable in one flip from anywhere; optimum cost 0."""
    return _write_cnf(tmp_path / "triv.cnf", """
        p cnf 3 3
        1 2 3 0
        1 -2 0
        1 3 0
    """)


@pytest.fixture
def fast_cfg():
    """Deeppolish-shaped but cheap: same keys, tiny budgets."""
    return {
        "solver": "local_multistart",
        "multistart": {"init": "uniform"},
        "ls": {"ls_polish_flips": 20, "time_limit_s": 0.01, "flip_budget": 20},
        "time_limit_s": 0.5,
    }


def _cfg(fast_cfg, **over):
    out = json.loads(json.dumps(fast_cfg))
    out.update(over)
    return out


# --------------------------------------------------------------------------
# 1. absence of evolutionary operations
# --------------------------------------------------------------------------
def test_config_declares_no_evolutionary_knobs():
    """The shipped config must not carry a single EA parameter."""
    yaml = pytest.importorskip("yaml")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["solver"] == "local_multistart"
    assert "ea" not in cfg, "an `ea:` block in the ablation config defeats its purpose"
    flat = json.dumps(cfg)
    for knob in ("pop_size", "tournament", "pmutate", "elitism", "max_gens", "crossover"):
        assert knob not in flat, f"evolutionary knob {knob!r} present in {CONFIG_PATH}"


def test_polish_budget_matches_memetic_deeppolish():
    """
    The ablation only isolates the EA if the per-restart polish is the
    per-child polish. Compare the two `ls:` blocks directly.
    """
    yaml = pytest.importorskip("yaml")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        ablation = yaml.safe_load(f)
    with open(DEEPPOLISH_PATH, encoding="utf-8") as f:
        memetic = yaml.safe_load(f)

    assert ablation["ls"] == memetic["ls"]
    assert ablation["ls"]["ls_polish_flips"] == 12500, \
        "the deep-polish limit under test is 12500 flips per restart"


def test_module_uses_no_evolutionary_operators():
    """
    `run_multistart_ls` must not reach for selection, crossover or mutation.
    Checked against the module source rather than by inspecting behaviour,
    because a reintroduced operator would still produce plausible-looking runs.
    """
    import ast

    src = open(ms_mod.__file__, encoding="utf-8").read()
    tree = ast.parse(src)

    # The AST, not the raw text: the module docstring legitimately contains the
    # words "no crossover" and "no EA mutation", and the whole point of those
    # lines is that they are claims about the code. Parsing checks the claims
    # instead of colliding with them. It also closes the loophole in scanning
    # only `run_multistart_ls`'s source range -- a helper defined above it would
    # never be looked at -- since every function in the module is walked.
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    called |= {n.func.attr for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}

    for banned in ("Individual", "tournament", "tournament_select", "crossover",
                   "uniform_crossover", "mutate", "mutate_bits", "select_parents"):
        assert banned not in called, f"{banned}() is called in multistart.py"

    # `Population` may be constructed exactly once, in `_jw_seeder`, purely to
    # reuse the EA's JW draw. Anywhere else it would be a real population and
    # this module would stop being a control.
    pop_sites = [fn.name for fn in ast.walk(tree)
                 if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                 for n in ast.walk(fn)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id == "Population"]
    assert pop_sites == ["_jw_seeder"], \
        f"Population() constructed in {pop_sites}, expected only _jw_seeder"

    # ...and with size 0, so it can never hold members.
    seeder = next(fn for fn in tree.body
                  if isinstance(fn, ast.FunctionDef) and fn.name == "_jw_seeder")
    call = next(n for n in ast.walk(seeder)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "Population")
    assert any(isinstance(a, ast.Constant) and a.value == 0 for a in call.args), \
        "the JW seed factory must be built with size 0"

    # It must, however, use the shared polish -- not a private reimplementation.
    body = src[src.index("def run_multistart_ls"):]
    assert "short_polish" in body
    from evo.operators import short_polish as shared_polish
    assert ms_mod.short_polish is shared_polish


def test_shares_the_memetic_polish_entry_point():
    """Both arms bottom out in the same local-search function object."""
    from evo import memetic, operators
    from sat import walksat
    assert memetic.short_polish is operators.short_polish
    assert ms_mod.short_polish is operators.short_polish
    assert operators.walksat_polish is walksat.walksat_polish
    # And the same config->budget resolver, so the budgets cannot drift apart.
    assert ms_mod._ls_budget is memetic._ls_budget


def test_result_reports_no_generations(tiny_unsat, fast_cfg):
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    res = run_multistart_ls(wcnf, fast_cfg, rng_seed=1)
    # None, not 0: there is no evolutionary loop, so a row must not read as an
    # EA that happened to run zero generations.
    assert res["meta"]["ea_generations"] is None
    assert res["meta"]["children"] is None
    assert res["restarts"] >= 1


# --------------------------------------------------------------------------
# 2. determinism
# --------------------------------------------------------------------------
def test_same_seed_reproduces_the_run(tiny_unsat, fast_cfg):
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 12}})
    # Restart-bounded rather than time-bounded: a wall-clock cap makes the
    # restart *count* machine-dependent, which is not what determinism means
    # here. The sequence of assignments explored is what must replay.
    del cfg["time_limit_s"]
    cfg["time_limit_s"] = 60.0

    # The polish here is flip-bound (20 flips), not wall-bound, so the outputs
    # themselves replay too. See test_restart_sequence_is_seed_determined for
    # the weaker guarantee that survives the tier-2 preset's wall-clock cap.
    a = run_multistart_ls(wcnf, cfg, rng_seed=7)
    b = run_multistart_ls(wcnf, cfg, rng_seed=7)
    assert a["meta"]["assign_bits"] == b["meta"]["assign_bits"]
    assert a["restarts"] == b["restarts"] == 12
    assert a["total_flips"] == b["total_flips"]
    assert a["best_soft_weight"] == b["best_soft_weight"]


def test_restart_sequence_is_seed_determined(tiny_unsat, fast_cfg, monkeypatch):
    """
    The guarantee that holds unconditionally: restart k always begins from the
    same assignment and is polished with the same polish seed.

    This is stronger than comparing outputs and it is the claim that survives
    the preset's wall-clock polish cap. Under `ls.time_limit_s`, how far each
    polish gets depends on machine speed -- measured on uuf250-03, 0.5 s buys
    ~5,300 iterations against a 12,500-flip ceiling -- so `total_flips` and the
    returned assignment are not bit-reproducible across machines. The EA arm
    has the identical property, being driven by the identical `ls:` block.
    """
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 20}})
    cfg["time_limit_s"] = 60.0
    real = ms_mod.short_polish

    def record_into(sink):
        def spy(assign01, w, ls_cfg, rng_seed):
            sink.append((tuple(assign01), rng_seed))
            return real(assign01, w, ls_cfg, rng_seed)
        return spy

    a, b = [], []
    monkeypatch.setattr(ms_mod, "short_polish", record_into(a))
    run_multistart_ls(wcnf, cfg, rng_seed=13)
    monkeypatch.setattr(ms_mod, "short_polish", record_into(b))
    run_multistart_ls(wcnf, cfg, rng_seed=13)

    assert len(a) == 20
    assert a == b

    c = []
    monkeypatch.setattr(ms_mod, "short_polish", record_into(c))
    run_multistart_ls(wcnf, cfg, rng_seed=14)
    assert c != a, "a different seed must produce a different restart sequence"


def test_different_seeds_diverge(tiny_unsat, fast_cfg):
    """A seed that changed nothing would silently collapse the 5-seed grid."""
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 8}})
    cfg["time_limit_s"] = 60.0
    seqs = {s: run_multistart_ls(wcnf, cfg, rng_seed=s)["meta"]["dimacs"]
            for s in (1, 2, 3, 4, 5)}
    assert len(set(seqs.values())) > 1


# --------------------------------------------------------------------------
# 3. restart behaviour
# --------------------------------------------------------------------------
def test_performs_many_restarts(tiny_unsat, fast_cfg):
    """
    With an unreachable target the loop must keep restarting until the budget
    is gone -- not stop after one polish.
    """
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 25}})
    cfg["time_limit_s"] = 60.0
    res = run_multistart_ls(wcnf, cfg, rng_seed=3, target_cost=0)  # cost 0 is impossible
    assert res["restarts"] == 25
    assert res["stop_reason"] == "max_restarts"
    assert res["time_to_target_s"] is None
    assert res["flips_in_target_restart"] is None


def test_restarts_are_independent(tiny_unsat, fast_cfg, monkeypatch):
    """
    Each restart must begin from a fresh random assignment, not from the
    previous restart's result -- otherwise this is iterated local search with a
    memory, which is a different algorithm.
    """
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    seen = []
    real = ms_mod.short_polish

    def spy(assign01, w, ls_cfg, rng_seed):
        seen.append(tuple(assign01))
        return real(assign01, w, ls_cfg, rng_seed)

    monkeypatch.setattr(ms_mod, "short_polish", spy)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 30}})
    cfg["time_limit_s"] = 60.0
    run_multistart_ls(wcnf, cfg, rng_seed=11)

    assert len(seen) == 30
    # 2 variables => 4 possible starts; over 30 draws all four should appear,
    # which no carried-over incumbent could produce.
    assert len(set(seen)) == 4


def test_flip_budget_stops_the_run(tiny_unsat, fast_cfg):
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg)
    cfg["time_limit_s"] = 60.0
    res = run_multistart_ls(wcnf, cfg, rng_seed=2, target_cost=0, max_total_flips=50)
    assert res["stop_reason"] == "flip_budget"
    assert res["total_flips"] >= 50
    assert res["restarts"] >= 1


# --------------------------------------------------------------------------
# 4. stopping at the certified target
# --------------------------------------------------------------------------
def test_stops_immediately_when_target_is_reached(trivial_sat, fast_cfg):
    wcnf = WCNF.parse_dimacs(trivial_sat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 500}})
    cfg["time_limit_s"] = 60.0
    res = run_multistart_ls(wcnf, cfg, rng_seed=1, target_cost=0)

    assert res["stop_reason"] == "target"
    assert res["hard_violations"] == 0
    assert res["time_to_target_s"] is not None
    assert res["flips_in_target_restart"] is not None
    assert res["restarts"] < 500, "it stopped at the target, not at the restart cap"
    # The reported cost must actually meet the target: total soft weight minus
    # satisfied weight is the unsatisfied weight the oracle is quoted in.
    total_soft = sum(cl.weight for cl in wcnf.clauses if not cl.is_hard)
    assert total_soft - res["best_soft_weight"] <= 0


def test_no_target_means_no_target_fields(trivial_sat, fast_cfg):
    """`target_cost=None` must never report a time-to-target, even on an
    instance it solves -- the memetic arm behaves the same way."""
    wcnf = WCNF.parse_dimacs(trivial_sat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 5}})
    cfg["time_limit_s"] = 60.0
    res = run_multistart_ls(wcnf, cfg, rng_seed=1)
    assert res["stop_reason"] == "max_restarts"
    assert res["time_to_target_s"] is None
    assert res["flips_in_target_restart"] is None


def test_time_cap_stops_the_run(tiny_unsat, fast_cfg):
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg)
    cfg["time_limit_s"] = 0.2
    res = run_multistart_ls(wcnf, cfg, rng_seed=4, target_cost=0)
    assert res["stop_reason"] == "time_cap"
    assert res["elapsed_sec"] >= 0.2
    assert res["restarts"] >= 1


def test_rejects_unknown_init_mode(tiny_unsat, fast_cfg):
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, multistart={"init": "greedy"})
    with pytest.raises(ValueError, match="multistart.init"):
        run_multistart_ls(wcnf, cfg, rng_seed=1)


# --------------------------------------------------------------------------
# 5. shard records: schema compatibility with the existing pipeline
# --------------------------------------------------------------------------
def _run_shard(tmp_path, instance, extra=(), config=None, budget="2"):
    out = tmp_path / "shard.jsonl"
    cmd = [sys.executable, "-m", "src.cli.run_memetic_shard",
           "--instance", instance,
           "--config", config or CONFIG_PATH,
           "--config-id", "local_multistart_deeppolish",
           "--seed", "1", "--budget-s", budget, "--grace-s", "20",
           "--job-id", "t2lms_00001", "--tier", "T2a", "--rc2-run", "unit_test",
           "--out", str(out), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    rec = json.loads(out.read_text()) if out.exists() else None
    return proc, rec


# The columns `src/bench/combine_tier2.py` reads off every shard. A record that
# drops one of these silently produces an empty CSV cell rather than an error.
COMBINE_FIELDS = [
    "job_id", "instance", "instance_sha256", "instance_format", "config_id",
    "config_hash", "seed", "budget_s", "wall_time_s", "status", "error",
    "best_cost", "hard_violations", "unsat_soft_clauses", "ea_generations",
    "children", "total_flips", "best_assignment_hash", "oracle_cost",
    "rc2_tier", "rc2_run", "n_vars", "n_clauses", "n_hard", "n_soft",
    "git_sha", "host", "slurm",
]


def test_shard_record_is_schema_compatible(tmp_path, tiny_unsat):
    proc, rec = _run_shard(tmp_path, tiny_unsat,
                           extra=["--oracle-cost", "2", "--stop-at-oracle"])
    assert rec is not None, proc.stderr
    assert rec["status"] == "ok", rec["error"]

    for field in COMBINE_FIELDS:
        assert field in rec, f"combine_tier2 reads {field!r}; the shard has no such key"

    assert rec["config_id"] == "local_multistart_deeppolish"
    assert rec["solver"] == "local_multistart"
    assert rec["instance_sha256"] and len(rec["instance_sha256"]) == 64
    assert rec["seed"] == 1
    assert rec["oracle_cost"] == 2
    assert rec["target_cost_used"] == 2

    # New fields the ablation needs.
    assert rec["restarts"] >= 1
    assert rec["total_flips"] >= 0
    assert rec["cpu_time_s"] is not None
    assert rec["target_reached"] is True
    assert rec["time_to_target_s"] is not None
    assert rec["flips_in_target_restart"] is not None
    assert rec["is_optimal"] is True
    assert rec["abs_gap"] == 0

    # No EA fields leak in, including into the resolved config.
    assert rec["ea_generations"] is None
    assert rec["children"] is None
    assert "ea" not in rec["config"]
    assert rec["config"]["time_limit_s"] == 2.0
    assert rec["config"]["ls"]["ls_polish_flips"] == 12500


def test_shard_record_on_failure_to_reach_target(tmp_path, tiny_unsat):
    """Budget expires without the target: a complete record, marked as a miss."""
    proc, rec = _run_shard(
        tmp_path, tiny_unsat, budget="1",
        extra=["--oracle-cost", "0", "--stop-at-oracle",   # cost 0 is unreachable
               "-D", "ls.ls_polish_flips=20", "-D", "ls.time_limit_s=0.01"])
    assert rec is not None, proc.stderr
    assert rec["status"] == "ok"
    assert rec["stop_reason"] == "time_cap"
    assert rec["target_reached"] is False
    assert rec["time_to_target_s"] is None
    assert rec["flips_in_target_restart"] is None
    assert rec["best_cost"] >= 2
    assert rec["restarts"] >= 1
    assert 1.0 <= rec["wall_time_s"] < 21.0


def test_shard_seed_is_reproducible(tmp_path, tiny_unsat):
    a = _run_shard(tmp_path / "a", tiny_unsat, budget="1",
                   extra=["-D", "multistart.max_restarts=15",
                          "-D", "ls.ls_polish_flips=20", "-D", "ls.time_limit_s=0.01"])[1]
    b = _run_shard(tmp_path / "b", tiny_unsat, budget="1",
                   extra=["-D", "multistart.max_restarts=15",
                          "-D", "ls.ls_polish_flips=20", "-D", "ls.time_limit_s=0.01"])[1]
    assert a["best_assignment_hash"] == b["best_assignment_hash"]
    assert a["restarts"] == b["restarts"] == 15
    assert a["total_flips"] == b["total_flips"]
    assert a["config_hash"] == b["config_hash"]


def test_max_total_flips_rejected_for_the_memetic_solver(tmp_path, tiny_unsat):
    proc, rec = _run_shard(
        tmp_path, tiny_unsat, budget="1",
        config=os.path.join(ROOT, "configs", "tier2", "memetic_deeppolish.yaml"),
        extra=["--max-total-flips", "100"])
    assert proc.returncode == 2
    assert "only implemented for solver=local_multistart" in proc.stderr


def test_unknown_solver_is_rejected(tmp_path, tiny_unsat):
    proc, rec = _run_shard(tmp_path, tiny_unsat, budget="1",
                           extra=["-D", "solver=local_multistat"])  # typo
    assert proc.returncode == 2
    assert "unknown solver" in proc.stderr


# --------------------------------------------------------------------------
# 6. the memetic arm is unaffected
# --------------------------------------------------------------------------
def test_memetic_path_still_gets_its_ea_defaults(tmp_path, tiny_unsat):
    """
    The EA-default injection in `run_memetic_shard` was made conditional. A
    config with no `solver:` key must still be treated as the memetic EA and
    still receive `ea.enabled`.
    """
    proc, rec = _run_shard(
        tmp_path, tiny_unsat, budget="1",
        config=os.path.join(ROOT, "configs", "tier2", "memetic_deeppolish.yaml"),
        extra=["--oracle-cost", "2"])
    assert rec is not None, proc.stderr
    assert rec["status"] == "ok", rec["error"]
    assert rec["solver"] == "memetic_ea"
    assert rec["config"]["ea"]["enabled"] is True
    assert rec["config"]["ea"]["pop_size"] == 40
    assert rec["ea_generations"] is not None
    assert rec["children"] is not None
    # EA rows carry no restart accounting.
    assert rec["restarts"] is None
    assert rec["flips_in_target_restart"] is None


def test_memetic_solver_output_is_unchanged(tiny_unsat):
    """
    `run_memetic` itself must not have been touched: same seed, same config,
    same assignment. Guards against a refactor drifting the EA arm, whose
    tier-2 results are already committed.
    """
    from evo.memetic import run_memetic
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = {
        "ea": {"enabled": True, "pop_size": 6, "tournament_k": 3,
               "pmutate": 0.02, "elitism": True, "max_gens": 3},
        "ls": {"ls_polish_flips": 20, "time_limit_s": 0.01, "flip_budget": 20},
        "time_limit_s": 30.0,
    }
    a = run_memetic(wcnf, cfg, rng_seed=5)
    b = run_memetic(wcnf, cfg, rng_seed=5)
    assert a["meta"]["assign_bits"] == b["meta"]["assign_bits"]
    assert a["meta"]["ea_generations"] == b["meta"]["ea_generations"] == 3
    assert a["total_flips"] == b["total_flips"]
    assert a["stop_reason"] == "max_gens"


# --------------------------------------------------------------------------
# 7. the SLURM array's task -> manifest row mapping
# --------------------------------------------------------------------------
MANIFEST = os.path.join(ROOT, "scripts", "manifest_tier2_local_multistart.tsv")


@pytest.mark.skipif(not os.path.exists(MANIFEST), reason="manifest not generated")
def test_manifest_shape():
    rows = [l for l in open(MANIFEST, encoding="utf-8").read().splitlines() if l.strip()]
    assert len(rows) == 130, "26 tier-2 instances x 5 seeds"

    instances, seeds = [], set()
    for row in rows:
        cols = row.split("\t")
        assert len(cols) == 9, "same 9 columns as manifest_tier2_memetic.tsv"
        job_id, inst, cfg, cfg_id, seed, budget, oracle, tier, rc2 = cols
        assert cfg_id == "local_multistart_deeppolish"
        assert cfg.endswith("local_multistart_deeppolish.yaml")
        assert budget == "900"
        assert int(oracle) >= 0
        instances.append(inst)
        seeds.add(int(seed))

    assert seeds == {1, 2, 3, 4, 5}
    assert len(set(instances)) == 26
    # Array task N reads line N+1, so ids 0..129 cover the manifest exactly.
    assert len({r.split("\t")[0] for r in rows}) == 130


# --------------------------------------------------------------------------
# 8. `local_multistart_jw_deeppolish` -- the JW-seeded arm
#
# The three-arm design this completes:
#
#     memetic_deeppolish  - local_multistart_jw   population / crossover / EA
#     local_multistart_jw - local_multistart      JW initialisation
#     memetic_deeppolish  - local_multistart      the whole package
#
# Each difference is only attributable to the named factor if everything else is
# held equal, so these tests check the two arms differ in seeding *and nothing
# else*, and that the seeding is the EA's own.
# --------------------------------------------------------------------------
@pytest.fixture
def jw_biased(tmp_path):
    """
    16 variables whose JW priors are strongly biased but never saturated.

    Each variable gets four positive unit clauses and one negative, so
    `jw_priors` gives p(True) = 4*0.5 / (4*0.5 + 0.5) = 0.8. Two properties are
    wanted at once: far enough from 0.5 that a JW draw is visibly different from
    a uniform one, and far enough from 1.0 that every restart is still a genuine
    coin flip. `tiny_unsat` is useless for this -- its priors work out to exactly
    0.5, so JW and uniform are the same distribution there.
    """
    lines = ["p cnf 16 %d" % (16 * 5)]
    for v in range(1, 17):
        lines += ["%d 0" % v] * 4 + ["-%d 0" % v]
    return _write_cnf(tmp_path / "jwbias.cnf", "\n".join(lines) + "\n")


@pytest.fixture
def jw_cfg(fast_cfg):
    return _cfg(fast_cfg, **{"multistart": {"init": "jw", "max_restarts": 40}},
                time_limit_s=60.0)


def _starts(cfg, wcnf, seed, monkeypatch):
    """The pre-polish assignment handed to each restart, in order."""
    seen = []
    real = ms_mod.short_polish

    def spy(assign01, w, ls_cfg, rng_seed):
        seen.append(tuple(assign01))
        return real(assign01, w, ls_cfg, rng_seed)

    monkeypatch.setattr(ms_mod, "short_polish", spy)
    run_multistart_ls(wcnf, cfg, rng_seed=seed)
    monkeypatch.setattr(ms_mod, "short_polish", real)
    return seen


# --- the seeding is the EA's, reused ---------------------------------------
def test_jw_seeding_delegates_to_population():
    """
    The claim that makes the middle arm meaningful: this arm's initial points
    come from the same code the EA's initial population comes from. A private
    copy of the draw could drift -- a different clip, a `<=` for a `<` -- and
    the JW-vs-uniform difference would then measure the copy, not the seeding.
    """
    assert ms_mod.jw_priors is pop_mod.jw_priors
    assert ms_mod.Population is pop_mod.Population
    # The draw itself: the exact function `Population.init_seeds` calls.
    assert ms_mod.Population._new_assign_from_priors is \
        pop_mod.Population._new_assign_from_priors

    src = open(ms_mod.__file__, encoding="utf-8").read()
    assert "_new_assign_from_priors" in src, \
        "the JW draw must be delegated, not reimplemented"
    # No second copy of the draw loop. `population.py` is byte-frozen by the
    # DIVERGENCE.md §2.2 invariant, so delegation is the only route to reuse.
    assert "< priors[v]" not in src and "< pri[v]" not in src


def test_jw_seeder_is_a_seed_factory_not_a_population(jw_biased):
    """
    The `Population` object exists only to expose the draw. If it ever gained
    members, this arm would have a population and would stop being a control.
    """
    import random as _random
    wcnf = WCNF.parse_dimacs(jw_biased)
    seeder, priors = ms_mod._jw_seeder(wcnf, _random.Random(1))
    assert seeder.size == 0
    assert seeder.members == []
    assert len(priors) == wcnf.n_vars + 1
    for v in range(1, wcnf.n_vars + 1):
        assert priors[v] == pytest.approx(0.8), "fixture's prior is 4:1 positive"
    # Drawing must not populate it.
    for _ in range(5):
        seeder._new_assign_from_priors(priors)
    assert seeder.members == []


def test_jw_priors_match_population_init_seeds(jw_biased):
    """
    Same RNG, same prior => the arm's restart k and the EA's individual k are
    the same assignment. This is what "seeding held constant" means, checked
    against `Population.init_seeds` rather than against a restatement of it.
    """
    import random as _random
    wcnf = WCNF.parse_dimacs(jw_biased)

    ea_pop = pop_mod.Population(wcnf.n_vars, 8, _random.Random(99))
    ea_pop.init_seeds(wcnf, {})
    ea_starts = [tuple(ind.assign01) for ind in ea_pop.members]

    seeder, priors = ms_mod._jw_seeder(wcnf, _random.Random(99))
    arm_starts = [tuple(ms_mod._random_assignment(wcnf.n_vars, seeder.rng, "jw",
                                                  seeder, priors))
                  for _ in range(8)]
    assert arm_starts == ea_starts


# --- stochastic per restart ------------------------------------------------
def test_jw_init_is_stochastic_across_restarts(jw_biased, jw_cfg, monkeypatch):
    """
    THE failure this arm must not have. If the JW seed were the deterministic
    argmax of the prior -- all 16 variables True here -- every restart would
    begin from the same point and the arm would be one polish repeated until
    the budget expired, while still emitting a complete, plausible row.
    """
    wcnf = WCNF.parse_dimacs(jw_biased)
    seen = _starts(jw_cfg, wcnf, 5, monkeypatch)

    assert len(seen) == 40
    assert len(set(seen)) > 1, "every restart began from the same assignment"
    # 16 variables at p=0.8: the chance of any two of 40 draws coinciding is
    # negligible, so anything short of near-total distinctness is a bug.
    assert len(set(seen)) >= 35

    argmax = tuple([False] + [True] * 16)
    assert seen.count(argmax) < len(seen), \
        "the draw is the prior's argmax, i.e. deterministic"

    # And it is biased, not uniform: p=0.8 over 16 vars means ~12.8 True per
    # draw. A uniform draw would average 8.0.
    mean_true = sum(sum(a[1:]) for a in seen) / len(seen)
    assert 11.0 < mean_true < 14.5, f"mean true-bits {mean_true} is not JW-biased"


def test_jw_init_is_deterministic_given_a_seed(jw_biased, jw_cfg, monkeypatch):
    """Stochastic across restarts, reproducible across runs -- both at once."""
    wcnf = WCNF.parse_dimacs(jw_biased)
    a = _starts(jw_cfg, wcnf, 21, monkeypatch)
    b = _starts(jw_cfg, wcnf, 21, monkeypatch)
    assert a == b and len(a) == 40

    c = _starts(jw_cfg, wcnf, 22, monkeypatch)
    assert c != a, "a different seed must produce a different restart sequence"


def test_jw_and_uniform_differ_under_the_same_seed(jw_biased, jw_cfg, monkeypatch):
    """
    The two arms must actually be two arms. Both branches consume one
    `rng.random()` per variable in index order, so under one seed they see the
    identical stream of floats and differ only in the threshold -- which is
    exactly the isolation the middle arm needs, and also means a bug that
    ignored the prior would show up here as two identical sequences.
    """
    wcnf = WCNF.parse_dimacs(jw_biased)
    uni_cfg = _cfg(jw_cfg, **{"multistart": {"init": "uniform", "max_restarts": 40}})

    jw = _starts(jw_cfg, wcnf, 8, monkeypatch)
    uni = _starts(uni_cfg, wcnf, 8, monkeypatch)

    assert len(jw) == len(uni) == 40
    assert jw != uni, "JW seeding produced the uniform restart sequence"

    jw_true = sum(sum(a[1:]) for a in jw) / len(jw)
    uni_true = sum(sum(a[1:]) for a in uni) / len(uni)
    assert jw_true > uni_true + 2.0, \
        f"JW mean true-bits {jw_true} not meaningfully above uniform's {uni_true}"


def test_uniform_arm_is_unaffected_by_the_jw_addition(tiny_unsat, fast_cfg, monkeypatch):
    """
    The uniform arm's semantics are the default and must not have moved: its
    draw is still one `rng.random() < 0.5` per variable off the run's own RNG,
    and no prior is computed for it at all.
    """
    import random as _random
    wcnf = WCNF.parse_dimacs(tiny_unsat)
    cfg = _cfg(fast_cfg, **{"multistart": {"init": "uniform", "max_restarts": 6}},
               time_limit_s=60.0)
    seen = _starts(cfg, wcnf, 4, monkeypatch)

    expected, rng = [], _random.Random(4)
    for _ in range(6):
        expected.append(tuple([False] + [rng.random() < 0.5
                                         for _ in range(wcnf.n_vars)]))
        rng.randrange(1 << 30)  # the polish seed, drawn after the assignment
    assert seen == expected

    # No seeder is built on the uniform path.
    calls = []
    monkeypatch.setattr(ms_mod, "_jw_seeder",
                        lambda w, r: calls.append(1) or (None, None))
    run_multistart_ls(wcnf, cfg, rng_seed=4)
    assert calls == []


# --- the shipped config ----------------------------------------------------
def test_jw_config_is_the_uniform_config_but_for_init():
    """
    Every key except `multistart.init` must be identical. A drifted `ls:` block
    would make the JW-vs-uniform difference a polish difference instead.
    """
    yaml = pytest.importorskip("yaml")
    with open(CONFIG_PATH, encoding="utf-8") as f:
        uniform = yaml.safe_load(f)
    with open(JW_CONFIG_PATH, encoding="utf-8") as f:
        jw = yaml.safe_load(f)

    assert jw["multistart"]["init"] == "jw"
    assert uniform["multistart"]["init"] == "uniform"
    assert set(jw) == set(uniform)
    for key in uniform:
        if key == "multistart":
            continue
        assert jw[key] == uniform[key], f"{key!r} differs between the two arms"
    assert set(jw["multistart"]) == set(uniform["multistart"]) == {"init"}


def test_jw_config_declares_no_evolutionary_knobs():
    """Seeding from the EA's prior must not smuggle in the EA itself."""
    yaml = pytest.importorskip("yaml")
    with open(JW_CONFIG_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    assert cfg["solver"] == "local_multistart"
    assert "ea" not in cfg
    flat = json.dumps(cfg)
    for knob in ("pop_size", "tournament", "pmutate", "elitism", "max_gens", "crossover"):
        assert knob not in flat, f"evolutionary knob {knob!r} present in {JW_CONFIG_PATH}"


def test_jw_config_polish_budget_matches_memetic_deeppolish():
    yaml = pytest.importorskip("yaml")
    with open(JW_CONFIG_PATH, encoding="utf-8") as f:
        jw = yaml.safe_load(f)
    with open(DEEPPOLISH_PATH, encoding="utf-8") as f:
        memetic = yaml.safe_load(f)
    assert jw["ls"] == memetic["ls"]
    assert jw["ls"]["ls_polish_flips"] == 12500


# --- the shard record ------------------------------------------------------
def test_jw_shard_record_is_schema_compatible(tmp_path, jw_biased):
    proc, rec = _run_shard(tmp_path, jw_biased, config=JW_CONFIG_PATH,
                           extra=["--oracle-cost", "16", "--stop-at-oracle",
                                  "-D", "ls.ls_polish_flips=20",
                                  "-D", "ls.time_limit_s=0.01"])
    assert rec is not None, proc.stderr
    assert rec["status"] == "ok", rec["error"]
    for field in COMBINE_FIELDS:
        assert field in rec, f"combine_tier2 reads {field!r}; the shard has no such key"
    assert rec["solver"] == "local_multistart"
    assert rec["config"]["multistart"]["init"] == "jw"
    assert rec["restarts"] >= 1
    assert rec["ea_generations"] is None and rec["children"] is None
    assert "ea" not in rec["config"]


# --- the manifest ----------------------------------------------------------
JW_MANIFEST = os.path.join(ROOT, "scripts", "manifest_tier2_local_multistart_jw.tsv")
ORACLE_CSV = os.path.join(ROOT, "scripts", "tier2_oracle.csv")


@pytest.mark.skipif(not os.path.exists(JW_MANIFEST), reason="jw manifest not generated")
def test_jw_manifest_shape():
    rows = [l for l in open(JW_MANIFEST, encoding="utf-8").read().splitlines() if l.strip()]
    assert len(rows) == 130, "26 tier-2 instances x 5 seeds"

    instances, seeds = [], set()
    for row in rows:
        cols = row.split("\t")
        assert len(cols) == 9, "same 9 columns as manifest_tier2_memetic.tsv"
        job_id, inst, cfg, cfg_id, seed, budget, oracle, tier, rc2 = cols
        assert cfg_id == "local_multistart_jw_deeppolish"
        assert cfg.endswith("local_multistart_jw_deeppolish.yaml")
        assert budget == "900"
        assert int(oracle) >= 0
        instances.append(inst)
        seeds.add(int(seed))

    assert seeds == {1, 2, 3, 4, 5}
    assert len(set(instances)) == 26
    assert len({r.split("\t")[0] for r in rows}) == 130


@pytest.mark.skipif(not (os.path.exists(JW_MANIFEST) and os.path.exists(MANIFEST)),
                    reason="both manifests must be generated")
def test_both_arms_get_the_same_problem_set():
    """
    Joined on the instance's sha256, not its path: two manifests can name the
    same file and mean different bytes after a re-rsync. A difference between
    the arms is only attributable to seeding if the problems and the certified
    optima are identical, so this is checked rather than assumed.
    """
    import csv as _csv
    with open(ORACLE_CSV, newline="", encoding="utf-8") as fh:
        oracle = {r["resolved"]: r for r in _csv.DictReader(fh)}

    def by_sha(path):
        out = {}
        for line in open(path, encoding="utf-8"):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            rec = oracle.get(cols[1])
            assert rec is not None, f"{cols[1]} is not in tier2_oracle.csv"
            out.setdefault(rec["sha256"], set()).add(cols[6])
        return out

    uni, jw = by_sha(MANIFEST), by_sha(JW_MANIFEST)
    assert set(uni) == set(jw), "the two arms cover different instances"
    assert len(uni) == 26

    for sha in sorted(uni):
        assert len(uni[sha]) == len(jw[sha]) == 1, \
            f"{sha[:12]}: oracle_cost varies across seeds within one arm"
        assert uni[sha] == jw[sha], f"{sha[:12]}: arms disagree on oracle_cost"
        # And both agree with the oracle table they were built from.
        ref = next(r["oracle_cost"] for r in oracle.values() if r["sha256"] == sha)
        assert next(iter(uni[sha])) == ref


# --------------------------------------------------------------------------
# 9. three config_ids in one combined run
# --------------------------------------------------------------------------
def test_combine_tier2_handles_three_config_ids(tmp_path, tiny_unsat):
    """
    `combine_tier2.py` groups by `config_id`, so a third arm should need no
    change there -- but "should" is why the ablation is being run in the first
    place. Build a shard directory holding all three config_ids and check the
    combiner keeps them apart rather than pooling or dropping one.
    """
    # `combine_tier2.py` lives in the repo `src/` tree, not in the staging tree
    # (DIVERGENCE.md: it was out of scope and is unchanged). Appended, not
    # inserted, so the staging `evo`/`sat` copies stay ahead of the repo ones.
    repo_src = os.path.join(os.path.dirname(ROOT), "src")
    if repo_src not in sys.path:
        sys.path.append(repo_src)
    combine = pytest.importorskip("bench.combine_tier2")

    shards = tmp_path / "tasks"
    shards.mkdir()
    cfg_ids = ["memetic_deeppolish", "local_multistart_deeppolish",
               "local_multistart_jw_deeppolish"]
    for ci in cfg_ids:
        for seed in (1, 2):
            rec = {
                "job_id": f"{ci}_{seed}", "instance": "data/x/uuf250-01.cnf",
                "instance_sha256": "a" * 64, "instance_format": "cnf",
                "config_id": ci, "config_hash": "h", "seed": seed,
                "budget_s": 900.0, "wall_time_s": 12.5, "status": "ok",
                "error": None, "best_cost": 1, "hard_violations": 0,
                "unsat_soft_clauses": 1, "ea_generations": None, "children": None,
                "total_flips": 10, "best_assignment_hash": "b",
                "oracle_cost": 1, "rc2_tier": "T2a", "rc2_run": "uuf250_1000c",
                "rc2_solve_s": 219.1, "n_vars": 250, "n_clauses": 1065,
                "n_hard": 0, "n_soft": 1065, "git_sha": "g", "host": "h",
                "slurm": {}, "schema_version": 2,
            }
            (shards / f"{ci}_{seed}.jsonl").write_text(json.dumps(rec) + "\n")

    # Empty oracle index: `flatten` then falls back to the shard's own
    # oracle_cost, which is all this test needs. `notes` collects the
    # reconciliation warnings and must stay empty for well-formed rows.
    notes = []
    rows = [combine.flatten(r, {}, notes)
            for r in combine.load_shards(str(shards))]
    assert notes == [], notes
    assert len(rows) == 6
    assert {r["config_id"] for r in rows} == set(cfg_ids)

    by_inst = combine.aggregate_by_instance(rows)
    assert len(by_inst) == 3, "one row per (instance, config_id, budget)"
    assert {r["config_id"] for r in by_inst} == set(cfg_ids)
    for r in by_inst:
        assert r["n_seeds"] == 2, "seeds of one arm must not pool across arms"

    summary = combine.aggregate_summary(rows, by_inst)
    assert len(summary) == 3, "three arms must produce three summary rows"
    assert {r["config_id"] for r in summary} == set(cfg_ids)
    for r in summary:
        assert r["n_runs"] == 2 and r["n_instances"] == 1
