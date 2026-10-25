"""Instance-aware v3 hyperparameters chosen at run time (src/evo/auto_hparams.py,
`hparams: auto` in src/cli/run_memetic_shard.py, scripts/auto_hparams.py).

- the size and class rules; the class (soft/hard x unweighted/weighted/heavy)
  picks the published or measured B2 values;
- R5: per_polish 10 exactly on hard instances whose v3 tables are lean (the
  ls_v3 trigger or a forced ls.nbrs), over the config's value; nothing else
  changes, and the shard run uses it;
- sizes come from the instance the EA solves (the kernel when the gate
  passes); kernel weights do not make an unweighted instance weighted;
- in the shard runner: the values are merged in memory, recorded (schema 6),
  the run uses them, their time counts, and the workstation preview gives the
  same resolved config; bad `hparams` configs are refused before the run;
- without `hparams` the record and the run are unchanged;
- the script writes the one batch config and --check reproduces it.
"""
from __future__ import annotations

import json
import os
import random
import sys

import pytest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
SRC = os.path.join(TREE, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
sys.path.insert(0, os.path.join(TREE, "scripts"))

from sat.cnf import WCNF  # noqa: E402
from evo import auto_hparams as ahp  # noqa: E402
from evo.v3 import v3_cfg  # noqa: E402
from evo.hard import hard_cfg  # noqa: E402


def make_wcnf(tmp_path, name, n, k, m_soft, m_hard=0, w_max=1, w_min=1, seed=0):
    rng = random.Random(seed)
    top = m_soft * w_max + 1
    lines = []
    for i in range(m_hard + m_soft):
        vs = rng.sample(range(1, n + 1), k)
        lits = [v if rng.random() < 0.5 else -v for v in vs]
        w = top if i < m_hard else rng.randint(w_min, w_max)
        lines.append(f"{w} " + " ".join(map(str, lits)) + " 0")
    path = tmp_path / f"{name}.wcnf"
    path.write_text(f"p wcnf {n} {len(lines)} {top}\n" + "\n".join(lines) + "\n")
    return str(path)


def prev(path, cfg=None):
    return ahp.preview(cfg or ahp.auto_base(), WCNF.parse_dimacs(path))


def small_run_cfg(tmp_path, **hp):
    """auto_base for a seconds-long test run (no C build needed here; test_native covers it)."""
    cfg = ahp.auto_base(**hp)
    cfg["ls"]["native"] = False
    cfg["ea"].update(pop_size=6, max_gens=2)
    cp = tmp_path / "auto.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    return cfg, str(cp)


def shard_run(path, cfg_path, tmp_path, name="o"):
    from cli import run_memetic_shard as shard
    out = tmp_path / f"{name}.jsonl"
    rc = shard.main(["--instance", path, "--config", cfg_path, "--seed", "1", "--budget-s", "20",
                     "--out", str(out)])
    return rc, (json.loads(out.read_text().strip().splitlines()[-1]) if out.exists() else None)


# ------------------------------------------------------------------ rules

def test_size_rules():
    assert [ahp.mutation_k(n) for n in (0, 25, 50, 200, 400, 572, 64000)] == [2, 2, 2, 8, 16, 16, 16]
    assert ahp.polish_flips(64000, 0.0, 1_600_000) == 12_500
    assert ahp.polish_flips(100, 25.0, 1_600_000) == 12_500
    assert ahp.polish_flips(16000, 25.0, 1_600_000) == 400_000
    assert ahp.polish_flips(64000, 100.0, 1_600_000) == 1_600_000


def test_small_soft_unweighted(tmp_path):
    r = prev(make_wcnf(tmp_path, "s", n=50, k=3, m_soft=215, seed=1))
    assert r.feats.cls == "soft_unweighted" and r.feats.gate == "skipped_screen"
    assert r.feats.n_eff == 50 and r.cfg["ea"]["mutation_k"] == 2
    ls = r.cfg["ls"]
    assert (ls["dls_t"], ls["dls_sp"], ls["dls_zeta"], ls["dls_h_inc"]) == (15, 0.01, 50, 1)
    assert ls["ls_polish_flips"] == ls["flip_budget"] == 12_500 and "polish_cap" not in ls
    assert v3_cfg(r.cfg)["native"] is True


def test_sparse_two_sat_is_sized_by_its_kernel(tmp_path):
    r = prev(make_wcnf(tmp_path, "sp", n=3000, k=2, m_soft=3450, seed=3))
    assert r.feats.gate == "kernel" and r.feats.n_eff < 3000
    assert r.cfg["ea"]["mutation_k"] == ahp.mutation_k(r.feats.n_eff)


def test_kernel_weights_do_not_make_an_unweighted_instance_weighted(tmp_path):
    # Duplicate clauses merge in the kernel (weights add): the class stays unweighted.
    lines = ["1 1 2 0", "1 1 2 0", "1 -1 3 0", "1 -2 -3 0", "1 2 3 0", "1 -1 -2 0", "1 1 -3 0"] * 3
    path = tmp_path / "dup.wcnf"
    path.write_text(f"p wcnf 3 {len(lines)} 1000\n" + "\n".join(lines) + "\n")
    r = prev(str(path))
    assert not r.feats.weighted and r.feats.cls == "soft_unweighted"
    assert r.cfg["ls"]["dls_zeta"] == max(50, 49 + r.feats.soft_w_max_eff)


@pytest.mark.parametrize("m_hard,w_min,w_max,cls,dls", [
    (40, 1, 1, "hard_unweighted", (42, 3e-6, 400, 1)),
    (40, 1, 9, "hard_weighted", (15, 0.01, 1, 3)),
    (40, 20000, 30000, "hard_weighted_heavy", (15, 0.01, 500, 300)),
    (0, 1, 9, "soft_weighted", None),
])
def test_class_picks_b2_values(tmp_path, m_hard, w_min, w_max, cls, dls):
    r = prev(make_wcnf(tmp_path, cls, n=60, k=3, m_soft=200, m_hard=m_hard, w_min=w_min, w_max=w_max, seed=4))
    assert r.feats.cls == cls
    ls = r.cfg["ls"]
    got = (ls["dls_t"], ls["dls_sp"], ls["dls_zeta"], ls["dls_h_inc"])
    assert got == (dls or (15, 0.01, max(50, 49 + r.feats.soft_w_max_eff), 1))
    v3_cfg(r.cfg)
    # R4: pop 10 and ks2 moves exactly when the solved instance has hard clauses.
    hard = cls.startswith("hard")
    assert r.cfg["ea"]["pop_size"] == (10 if hard else 40)
    assert ("hard" in r.overrides) == hard
    if hard:
        assert r.cfg["hard"] == {"moves": {"keep_sat": "ks2"}}
        assert hard_cfg(r.cfg)["move_keep_sat"] == "ks2"
    else:
        assert "hard" not in r.cfg


def _hard(tmp_path, name="r5", seed=4):
    return make_wcnf(tmp_path, name, n=60, k=3, m_soft=200, m_hard=40, seed=seed)


def test_r5_lean_hard_instance_gets_per_polish_10(tmp_path, monkeypatch):
    from sat import ls_v3
    path = _hard(tmp_path)
    full = prev(path)
    assert full.feats.nbrs_mode == "full" and full.feats.nbrs_bound > 0
    assert full.cfg["hard"] == {"moves": {"keep_sat": "ks2"}} and "hard.moves.per_polish" not in full.reasons
    monkeypatch.setattr(ls_v3, "NBRS_MAX", full.feats.nbrs_bound - 1)
    lean = prev(path)
    assert lean.feats.nbrs_mode == "lean" and lean.feats.nbrs_bound == full.feats.nbrs_bound
    assert lean.cfg["hard"] == {"moves": {"keep_sat": "ks2", "per_polish": 10}}
    assert hard_cfg(lean.cfg)["moves_per_polish"] == 10 and lean.reasons["hard.moves.per_polish"].startswith("R5")
    # everything else resolves as with full tables
    assert lean.cfg["ea"] == full.cfg["ea"] and lean.cfg["ls"] == full.cfg["ls"]


def test_r5_not_on_soft_instances(tmp_path, monkeypatch):
    from sat import ls_v3
    monkeypatch.setattr(ls_v3, "NBRS_MAX", 0)
    r = prev(make_wcnf(tmp_path, "s5", n=60, k=3, m_soft=200, seed=4))
    assert r.feats.nbrs_mode is None and r.feats.nbrs_bound is None and "hard" not in r.cfg


@pytest.mark.parametrize("forced,cap,want", [("lean", None, 10), ("full", 0, None)])
def test_r5_follows_a_forced_ls_nbrs(tmp_path, monkeypatch, forced, cap, want):
    from sat import ls_v3
    if cap is not None:
        monkeypatch.setattr(ls_v3, "NBRS_MAX", cap)
    cfg = ahp.auto_base()
    cfg["ls"]["nbrs"] = forced
    r = prev(_hard(tmp_path), cfg)
    assert r.feats.nbrs_mode == forced
    assert r.cfg["hard"]["moves"].get("per_polish") == want


def test_r5_overrides_the_configs_per_polish(tmp_path, monkeypatch):
    from sat import ls_v3
    monkeypatch.setattr(ls_v3, "NBRS_MAX", 0)
    cfg = ahp.auto_base()
    cfg["hard"] = {"moves": {"per_polish": 200, "noise": 0.1}}
    r = prev(_hard(tmp_path), cfg)
    assert r.cfg["hard"]["moves"] == {"per_polish": 10, "noise": 0.1, "keep_sat": "ks2"}


def test_merge_is_deep_and_keeps_other_hard_keys():
    cfg = {"ea": {"pop_size": 40, "elitism": True},
           "hard": {"phases": "random", "moves": {"per_polish": 50, "keep_sat": "none"}}}
    out = ahp.merge(cfg, {"ea": {"pop_size": 10}, "hard": {"moves": {"keep_sat": "ks2"}}})
    assert out == {"ea": {"pop_size": 10, "elitism": True},
                   "hard": {"phases": "random", "moves": {"per_polish": 50, "keep_sat": "ks2"}}}
    assert cfg["hard"]["moves"]["keep_sat"] == "none"          # the input is not changed


def test_flips_c_sets_flips_only_on_soft_but_not_on_hard(tmp_path):
    cfg = ahp.auto_base(flips_c=25.0)
    soft = prev(make_wcnf(tmp_path, "s", n=2000, k=3, m_soft=8500, seed=5), cfg)
    assert soft.cfg["ls"]["ls_polish_flips"] == 50_000 and soft.cfg["ls"]["polish_cap"] == "flips_only"
    hard = prev(make_wcnf(tmp_path, "h", n=2000, k=3, m_soft=8000, m_hard=500, seed=5), cfg)
    assert hard.cfg["ls"]["ls_polish_flips"] == 50_000 and "polish_cap" not in hard.cfg["ls"]


@pytest.mark.parametrize("bad", ["sometimes", {"mode": "auto", "c": 3}, {"mode": "auto", "flips_c": -1},
                                 {"mode": "auto", "flips_cap": 10}])
def test_hparams_opts_refuses_bad_values(bad):
    with pytest.raises(ValueError):
        ahp.hparams_opts({"impl": "v3", "hparams": bad})


def test_hparams_auto_needs_v3():
    with pytest.raises(ValueError):
        ahp.hparams_opts({"impl": "v2", "hparams": "auto"})
    assert ahp.hparams_opts({"impl": "v2", "hparams": "none"}) is None
    assert ahp.hparams_opts({"impl": "v2"}) is None


# ------------------------------------------------------------------ shard runner

@pytest.mark.parametrize("m_hard", [0, 15])
def test_shard_resolves_in_memory_records_and_runs_with_it(tmp_path, m_hard):
    if m_hard:
        pytest.importorskip("pysat")
    path = make_wcnf(tmp_path, "e", n=40, k=3, m_soft=150, m_hard=m_hard, seed=6)
    cfg, cp = small_run_cfg(tmp_path)
    rc, rec = shard_run(path, cp, tmp_path)
    assert rc == 0 and rec["status"] == "ok" and rec["schema_version"] == 6
    hp = rec["hparams"]
    assert hp["ruleset"] == ahp.RULESET and hp["hparams_s"] >= 0
    assert hp["class"] == ("hard_unweighted" if m_hard else "soft_unweighted")
    assert rec["v3"]["hard_mode"] == ("on" if m_hard else "off") and rec["hard_violations"] == 0
    # `config` is the submitted file (plus the budget); the resolved one is identified by its hash.
    assert rec["config"]["hparams"] == "auto" and rec["config"]["ea"]["mutation_k"] == 16
    assert hp["overrides"]["ea"]["mutation_k"] == ahp.mutation_k(hp["features"]["n_eff"]) == 2
    # The preview on the workstation gives the same resolved config as the job.
    pv = ahp.preview(dict(cfg, time_limit_s=20.0), WCNF.parse_dimacs(path))
    assert pv.cfg_hash == hp["resolved_config_hash"] and pv.overrides == hp["overrides"]
    # Nothing but the shard was written.
    assert sorted(os.listdir(tmp_path)) == sorted(["auto.yaml", "e.wcnf", "o.jsonl"])


def test_shard_run_uses_the_chosen_values(tmp_path, monkeypatch):
    from cli import run_memetic_shard as shard
    seen = {}

    def spy(wcnf, cfg, **kw):
        seen["cfg"] = cfg
        raise RuntimeError("stop after capturing the config")
    monkeypatch.setattr(shard, "run_memetic", spy)
    path = make_wcnf(tmp_path, "u", n=60, k=3, m_soft=200, m_hard=40, w_min=1, w_max=9, seed=4)
    _, cp = small_run_cfg(tmp_path)
    rc, rec = shard_run(path, cp, tmp_path)
    assert rec["status"] == "error" and "stop after capturing" in rec["error"]
    ls = seen["cfg"]["ls"]
    assert (ls["dls_t"], ls["dls_zeta"], ls["dls_h_inc"]) == (15, 1, 3)          # hard_weighted
    assert seen["cfg"]["ea"]["pop_size"] == 10                                  # R4
    assert hard_cfg(seen["cfg"])["move_keep_sat"] == "ks2"
    assert rec["config"]["ea"]["pop_size"] == 6      # the record keeps the submitted config (small_run_cfg)
    assert seen["cfg"]["ea"]["mutation_k"] == ahp.mutation_k(60)
    # the hparams time is inside the budget, like the gate's
    pre = rec["preprocess_s"] + rec["hparams"]["hparams_s"]
    assert seen["cfg"]["time_limit_s"] == pytest.approx(20.0 - pre, abs=0.01)


def test_shard_run_with_lean_tables_uses_r5(tmp_path, monkeypatch):
    pytest.importorskip("pysat")
    from sat import ls_v3
    path = _hard(tmp_path, "rl", seed=6)
    monkeypatch.setattr(ls_v3, "NBRS_MAX", 0)          # every instance lean, in this process
    _, cp = small_run_cfg(tmp_path)
    rc, rec = shard_run(path, cp, tmp_path)
    assert rc == 0 and rec["status"] == "ok" and rec["hard_violations"] == 0
    hp = rec["hparams"]
    assert hp["ruleset"] == "auto_hparams/3" and hp["overrides"]["hard"]["moves"]["per_polish"] == 10
    assert hp["features"]["nbrs_mode"] == "lean" and rec["v3"]["nbrs_mode"] == "lean"
    assert rec["v3"]["nbrs_bound"] == hp["features"]["nbrs_bound"]


def test_shard_without_hparams_is_unchanged(tmp_path):
    path = make_wcnf(tmp_path, "n", n=40, k=3, m_soft=150, seed=6)
    cfg, _ = small_run_cfg(tmp_path)
    cfg.pop("hparams")
    cp = tmp_path / "plain.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    rc, rec = shard_run(path, str(cp), tmp_path)
    assert rc == 0 and rec["hparams"] is None and rec["config"]["ea"]["mutation_k"] == 16


@pytest.mark.parametrize("edit", [
    lambda c: c.update(impl="v2"),
    lambda c: c.update(hparams={"mode": "auto", "flipz": 1}),
    lambda c: c.update(solver="local_multistart"),
])
def test_shard_refuses_bad_hparams_configs_before_the_run(tmp_path, edit):
    path = make_wcnf(tmp_path, "b", n=40, k=3, m_soft=150, seed=6)
    cfg, _ = small_run_cfg(tmp_path)
    edit(cfg)
    cp = tmp_path / "bad.yaml"
    cp.write_text(yaml.safe_dump(cfg))
    rc, rec = shard_run(path, str(cp), tmp_path)
    assert rc == 2 and rec is None


# ------------------------------------------------------------------ script

def test_script_writes_one_base_and_previews(tmp_path, monkeypatch, capsys):
    import auto_hparams as script
    monkeypatch.setattr(script, "ROOT", str(tmp_path))
    assert script.main(["--write-base"]) == 0
    base = tmp_path / "configs" / "strong" / "auto.yaml"
    assert yaml.safe_load(base.read_text()) == ahp.auto_base()
    assert script.main(["--check"]) == 0
    assert script.main(["--check", "--flips-c", "5"]) == 1
    a = make_wcnf(tmp_path, "a", n=50, k=3, m_soft=215, seed=1)
    c = make_wcnf(tmp_path, "c", n=60, k=3, m_soft=200, m_hard=40, seed=4)
    lst = tmp_path / "l.txt"
    lst.write_text("# instances\n" + "\n".join(os.path.basename(p) for p in (a, c)) + "\n")
    capsys.readouterr()
    assert script.main(["--list", str(lst), "--map", "pv.csv"]) == 0
    out = capsys.readouterr().out
    assert "class soft_unweighted" in out and "class hard_unweighted" in out
    rows = (tmp_path / "pv.csv").read_text().strip().splitlines()
    assert len(rows) == 3
    assert not (tmp_path / "configs" / "auto").exists()      # no per-instance configs
