"""
`local_multistart_deeppolish` -- the no-EA ablation baseline for the memetic
solver (`src/evo/multistart.py`, dispatched by `src/cli/run_memetic_shard.py`).

What these tests are for: the baseline's scientific value rests entirely on two
claims that are easy to break silently. First, that it contains no evolutionary
machinery -- a stray import or a config default that reintroduces a population
would turn the control into a second copy of the treatment. Second, that its
local search *is* the memetic solver's local search, not a lookalike. Both are
asserted here directly rather than left to code review.
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
from evo.multistart import run_multistart_ls  # noqa: E402
from sat.cnf import WCNF  # noqa: E402

CONFIG_PATH = os.path.join(ROOT, "configs", "tier2", "local_multistart_deeppolish.yaml")
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
    src = open(ms_mod.__file__, encoding="utf-8").read()
    body = src[src.index("def run_multistart_ls"):]
    for banned in ("tournament", "crossover", "mutate", "Population(", "Individual("):
        assert banned not in body, f"{banned!r} appears in run_multistart_ls"

    # It must, however, use the shared polish -- not a private reimplementation.
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
