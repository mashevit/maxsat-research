"""The pre-registered ρ analysis (scripts/mse26_rho.py; docs/current2/MSE26_RHO_PREREG.md r4).

Synthetic data only (written before any batch 3c record was read):
- Spearman with midranks equals Pearson on scipy's average ranks, with ties and inf;
- the memetic ERT / PAR2 equal m2_results.ert / par2 on the same runs, and the
  shorter budget and flip-level variants follow §3;
- the BCa interval agrees with scipy.stats.bootstrap(method="BCa");
- partial Spearman removes a common cause;
- an end-to-end run on a synthetic population: populations, censoring counts,
  incomplete instances, the 2 x 2 table, PAR2 including EvalMaxSAT memouts.
"""
from __future__ import annotations

import csv
import json
import math
import os
import sys

import numpy as np
import pytest
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(TREE, "scripts"))

import m2_results  # noqa: E402
import make_mse26_manifest as mk  # noqa: E402
import mse26_rho as rho  # noqa: E402

INF = math.inf


def test_spearman_midranks_with_ties_and_inf():
    rng = np.random.default_rng(1)
    x = rng.integers(0, 20, 300).astype(float)
    y = x + rng.normal(0, 5, 300)
    x[:40], y[30:70] = INF, INF                       # censored on x, on y, and 10 on both
    want = stats.pearsonr(stats.rankdata(x), stats.rankdata(y))[0]
    assert rho.spearman(x, y) == pytest.approx(want, abs=1e-12)
    assert rho.spearman(np.ones(5), np.arange(5.0)) != rho.spearman(np.ones(5), np.arange(5.0))   # nan: no variance


def run(cls, ttt=None, hit=None, calls=None):
    return {"cls": cls, "cpu_to_target_s": ttt, "cpu_to_target_hit_s": hit, "calls_to_target": calls}


def test_memetic_ert_and_par2_match_m2_results():
    cases = [[run("success", 100.0), run("success", 300.0), run("budget_exhausted")],
             [run("success", 1.0), run("success", 1.0), run("watchdog")],
             [run("budget_exhausted"), run("target_after_budget"), run("max_gens")],
             [run("success", 1000.0)] * 3]
    for rs in cases:
        m2rows = [{"cls": r["cls"], "success_ttt_s": r["cpu_to_target_s"], "budget_s": "1800"} for r in rs]
        e = m2_results.ert(m2rows)["ert_s"]
        assert rho.y_ert(rs) == (INF if e == "inf" else pytest.approx(e, abs=1e-3))
        assert rho.y_par2(rs) == pytest.approx(m2_results.par2(m2rows)["par2_s"], abs=1e-3)
    assert rho.y_ert(cases[0]) == 1100.0                      # the pre-registration's example
    assert rho.y_ert(cases[1]) == 901.0 and rho.y_par2(cases[1]) == pytest.approx(3602 / 3)


def test_shorter_budget_and_flip_level():
    rs = [run("success", 100.0, hit=40.0), run("success", 1200.0, hit=1100.0), run("budget_exhausted")]
    assert rho.y_ert(rs, 900.0) == (100.0 + 900.0 + 900.0) / 1          # the 1,200 s success fails at B = 900
    assert rho.y_ert(rs, flip=True) == (40.0 + 1100.0 + 1800.0) / 2
    assert rho.y_ert([run("success", 50.0, hit=None)], flip=True) == 50.0    # call resolution: no hit time


def test_x_rules():
    row = lambda **kw: {"answer": "OPTIMUM FOUND", "verified": "1", "optval": "7", "cpu.time": "12.5",
                        "timeout": "false", "memout": "false", **kw}
    assert rho.solver_status(row(), "7") == "proved"
    assert rho.solver_status(row(optval="8"), "7") == "wrong"
    assert rho.solver_status(row(verified="0"), "7") == "wrong"
    assert rho.solver_status(row(answer="NONE", timeout="true"), "7") == "timeout"
    assert rho.solver_status(row(answer="SATISFIABLE", memout="true"), "7") == "memout"
    assert rho.solver_status(row(answer="NONE"), "7") == "crash"
    assert rho.solver_status(row(answer="UNSATISFIABLE"), "7") == "wrong"
    assert (rho.x_ert("proved", 3.0), rho.x_ert("timeout", 3600.0), rho.x_ert("memout", 9.0)) == (3.0, INF, None)
    assert (rho.x_par2("proved", 3.0), rho.x_par2("crash", 9.0), rho.x_par2("timeout", 3600.0)) == (3.0, 7200.0, 7200.0)


def test_bca_matches_scipy():
    rng = np.random.default_rng(7)
    x = rng.normal(size=150)
    y = 0.5 * x + rng.normal(size=150)
    ours = rho.rho_ci(x, y, n_boot=4000)
    ref = stats.bootstrap((x, y), lambda a, b: stats.spearmanr(a, b)[0], paired=True, vectorized=False,
                          n_resamples=4000, method="BCa", random_state=3).confidence_interval
    assert ours["lo"] == pytest.approx(ref.low, abs=0.03) and ours["hi"] == pytest.approx(ref.high, abs=0.03)
    assert ours["lo"] < ours["rho"] < ours["hi"]


def test_stratified_bootstrap_runs_within_strata():
    rng = np.random.default_rng(2)
    x = rng.normal(size=80)
    y = x + rng.normal(size=80)
    r = rho.rho_ci(x, y, strata=["a"] * 50 + ["b"] * 30, n_boot=500)
    assert r["lo"] < r["rho"] < r["hi"]


def test_partial_spearman_removes_a_common_cause():
    rng = np.random.default_rng(4)
    size = rng.normal(size=600)
    x = size + 0.3 * rng.normal(size=600)
    y = size + 0.3 * rng.normal(size=600)
    assert rho.spearman(x, y) > 0.7
    assert abs(rho.partial_spearman(x, y, np.column_stack([size, rng.normal(size=600)]))) < 0.15


def test_interpretation_rules():
    assert rho.interpret({"lo": 0.05, "hi": 0.4}) == "positive association"
    assert rho.interpret({"lo": -0.4, "hi": -0.01}) == "negative association"
    assert rho.interpret({"lo": -0.2, "hi": 0.25}) == "at most weak monotone association"
    assert rho.interpret({"lo": -0.35, "hi": 0.1}) == "inconclusive at this N"


# --------------------------------------------------------------- end to end
def _write_tsv(path, cols, rows, delim="\t"):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=delim, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _record(t, ttt=None, calls=None):
    ok = ttt is not None
    return {"job_id": t["job_id"], "config_id": "auto", "seed": int(t["solver_seed"]),
            "instance_sha256": t["instance_sha256"], "budget_s": 1800.0, "grace_s": 300.0, "budget_clock": "process",
            "stop_at_oracle": True, "oracle_cost": int(t["oracle_cost"]), "status": "ok",
            "stop_reason": "target" if ok else "time_cap", "time_to_target_s": ttt, "cpu_to_target_s": ttt,
            "cpu_to_target_hit_s": ttt, "calls_to_target": calls,
            "config": {"impl": "v3", "preprocess": "kernel", "ea": {"pop_size": 40, "deadline_mode": "clip"},
                       "ls": {"time_limit_s": 3.5, "ls_polish_flips": 12500, "native": True}}}


def test_end_to_end(tmp_path):
    rng = np.random.default_rng(11)
    n = 60
    hashes = [f"{i:032x}" for i in range(n)]
    sets = ["mse26-exact-unweighted" if i % 2 else "mse26-exact-weighted" for i in range(n)]
    # EvalMaxSAT: 0-39 proved (CPU grows with i), 40-49 timeout, 50-52 memout, 53 crash; 54-59 no proven optimum
    ems = {}
    pop, census, raw = [], [], {s: [] for s in rho.RAW}
    for i, h in enumerate(hashes):
        proven = i < 54
        st = "proved" if i < 40 else "timeout" if i < 50 else "memout" if i < 53 else "crash" if i < 54 else "timeout"
        ems[h] = st
        role = "finite" if st == "proved" and proven else "censored" if st == "timeout" and proven else "excluded"
        cpu = 5.0 + 80.0 * i if st == "proved" else 3600.0 if st == "timeout" else 100.0
        pop.append({"set": sets[i], "hash": h, "family": f"fam{i % 3}", "optimal_cost": "7" if proven else "unknown",
                    "target_kind": "proven" if proven else "no_optimum", "primary": int(role != "excluded"),
                    "window": int(role == "finite" and 30 < cpu <= 3600)})
        census.append({"hash": h, "n_vars": str(100 + i), "n_clauses": str(1000 + 7 * i)})
        for solver in ("EvalMaxSAT", "OtherSolver"):
            s2 = st if solver == "EvalMaxSAT" else ("proved" if proven and i % 4 else "timeout")
            raw[sets[i]].append({
                "solvername": solver, "instance": h + ".wcnf", "cpu.time": str(cpu if solver == "EvalMaxSAT" else 10.0 + i),
                "wall.time": str(cpu + 1), "mem.usage": "1", "timeout": str(s2 == "timeout").lower(),
                "memout": str(s2 == "memout").lower(), "answer": "OPTIMUM FOUND" if s2 == "proved" else
                ("SATISFIABLE" if s2 == "memout" else "NONE"), "optval": "7" if s2 == "proved" else "NA",
                "verified": "1" if s2 == "proved" else "NA", "LB": "NA"})
    _write_tsv(tmp_path / "pop.tsv", list(pop[0]), pop)
    _write_tsv(tmp_path / "census.tsv", ["hash", "n_vars", "n_clauses"], census)
    pub = tmp_path / "pub"
    pub.mkdir()
    for s, fn in rho.RAW.items():
        _write_tsv(pub / fn, list(raw[s][0]), raw[s], delim=",")
    # memetic: instance i reaches the target with TTT growing with i on seeds where (i + seed) % 5 != 0;
    # instances 0-3 never; instance 10 seed 2 has no record (incomplete)
    tasks, lines = [], []
    for i, h in enumerate(hashes):
        for seed in (1, 2, 3):
            job = f"m26_{h}_s{seed}"
            tasks.append({**{c: "" for c in mk.SIDECAR}, "task_id": len(tasks) + 1, "job_id": job, "stage": "mse26",
                          "part": "t", "pop_idx": f"m{i:03d}", "bin_gb": 8, "config_id": "auto", "config": mk.CONFIG,
                          "solver_seed": seed, "budget_s": 1800, "grace_s": 300, "budget_clock": "process",
                          "set": sets[i], "hash": h, "family": f"fam{i % 3}", "instance": f"data/{h}.wcnf",
                          "instance_sha256": "ab" + h, "oracle_cost": 7, **mk.FIXED})
            lines.append(f"{job}\tdata/{h}.wcnf\n")
    man = tmp_path / "manifest_mse26_t.tsv"
    man.write_text("".join(lines))
    _write_tsv(tmp_path / "manifest_mse26_t.tasks.csv", mk.SIDECAR, tasks, delim=",")
    out = tmp_path / "tasks"
    out.mkdir()
    for t in tasks:
        i, seed = int(t["pop_idx"][1:]), int(t["solver_seed"])
        if (i, seed) == (10, 2):
            continue
        ttt = None if i < 4 or (i + seed) % 5 == 0 else float(3 + 20 * i + seed)
        (out / f"{t['job_id']}.jsonl").write_text(json.dumps(_record(t, ttt, calls=1 if i < 8 else 5)) + "\n")
    res_dir = tmp_path / "rho"
    assert rho.main(["--outdir", str(out), "--manifest", str(man), "--population", str(tmp_path / "pop.tsv"),
                     "--published", str(pub), "--census", str(tmp_path / "census.tsv"), "--out", str(res_dir),
                     "--n-boot", "300"]) == 0
    s = json.load(open(res_dir / "summary.json"))
    p = s["population"]
    assert (p["proven_optimum"], p["primary"], p["incomplete"]) == (54, 50, 1)
    assert p["excluded_ems"] == {"memout": 3, "crash": 1}
    assert list(s["incomplete"]) == [hashes[10]]
    pr = s["analyses"]["primary"]
    assert pr["n"] == 49                                      # 50 primary, instance 10 incomplete
    assert (pr["x_inf"], pr["y_inf"], pr["both_inf"]) == (10, 4, 0)
    # the same ρ rebuilt independently from the synthetic rules, with scipy
    xs, ys = [], []
    for i in range(50):
        if i == 10:
            continue
        xs.append(5.0 + 80.0 * i if i < 40 else INF)
        ttts = [None if i < 4 or (i + sd) % 5 == 0 else float(3 + 20 * i + sd) for sd in (1, 2, 3)]
        ok = [t for t in ttts if t is not None]
        ys.append((sum(ok) + 1800.0 * (3 - len(ok))) / len(ok) if ok else INF)
    assert pr["rho"] == pytest.approx(stats.spearmanr(xs, ys)[0], abs=1e-12)
    assert pr["lo"] < pr["rho"] < pr["hi"]
    assert s["analyses"]["sensitivity"]["7_par2_all_proven"]["n"] == 53     # memouts and the crash enter PAR2
    assert s["complementarity"]["2x2"] == {"ems_proved_memetic_reached": 35, "ems_proved_memetic_not": 4,
                                           "ems_not_memetic_reached": 10, "ems_not_memetic_not": 0}
    other = s["analyses"]["per_solver"]["OtherSolver"]
    assert set(other) == {"mse26-exact-unweighted", "mse26-exact-weighted", "pooled"}
    assert other["pooled"]["n"] == 53
    rows = list(csv.DictReader(open(res_dir / "instances.csv")))
    assert len(rows) == 54 and (res_dir / "report.md").read_text().startswith("# ρ on MSE 2026")


def test_population_mismatch_is_fatal(tmp_path, monkeypatch):
    pop = {"h": {"target_kind": "proven", "optimal_cost": "7", "primary": "1", "window": "0", "set": "s", "family": "f"}}
    pub = {"h": {"EvalMaxSAT": {"answer": "NONE", "timeout": "false", "memout": "true", "verified": "NA",
                                "optval": "NA", "cpu.time": "5", "wall.time": "5"}}}
    with pytest.raises(SystemExit):
        rho.analyse(pop, pub, {}, {}, [1, 2, 3], n_boot=50)
