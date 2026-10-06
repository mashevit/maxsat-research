"""calib_c reinforcement preparation (docs/current/CORPUS_FREEZE_PREP.md §5, repo).

Covers the window boundary convention, the not-run accounting, the identity of
the memetic arm with the M2 full pool's a35 arm, and the reproducibility of the
candidate-cell table. Run from inside cluster_staging_maxsat/.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

import pytest

STAGING = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(STAGING, "scripts"))
import make_calib_c_memetic_manifest as cc  # noqa: E402
import candidate_cells as cand  # noqa: E402


def prof(status="optimal", s=100.0, cost=19, lb=19, completed=True, cap=900):
    return {"status": status, "solve_s": s, "final_cost": cost, "cost_lower_bound": lb,
            "completed": completed, "cap_s": cap, "error": None}


@pytest.mark.parametrize("p,cls", [
    (prof(s=30.0), "below_window"),            # 30 s itself is NOT eligible: (30, 900]
    (prof(s=30.001), "eligible"),
    (prof(s=900.0), "eligible"),               # 900 s itself IS eligible
    (prof(s=900.5), "censored"),               # completed only after the cap
    (prof(s=0.004), "below_window"),
    (prof(status="subprocess_killed", s=960.1, cost=None, lb=18, completed=False), "censored"),
    (prof(status="timeout", s=900.0, cost=None, lb=18, completed=False), "censored"),
    (prof(s=-0.8), "failed"),                  # wall-clock step, CALIB log Checkpoint 3
    (prof(cost=20, lb=19), "failed"),
    (prof(status="error", completed=False, cost=None, lb=None), "failed"),
    (prof(status="subprocess_killed", completed=False, cost=None, lb=3, cap=60), "failed"),  # lower cap
])
def test_window_boundary_convention(p, cls):
    assert cc.classify(p)[0] == cls
    # candidate_cells.py must apply the identical rule
    want = {"below_window": "below", "eligible": "eligible", "censored": "censored", "failed": "failed"}[cls]
    assert cand.rc2_class(p)[0] == want


def _gen(i, cell="max2sat_n400_a2.15"):
    return {"instance": f"data/generated/calib_c/x_s{100 + i}.wcnf", "instance_sha256": f"{i:064x}",
            "cell_id": cell, "family": "max2sat", "k": 2, "n": 400, "alpha": 2.15, "m": 860, "seed": 100 + i}


def test_select_accounts_for_every_instance_and_never_runs_below_window():
    gen = [_gen(i) for i in range(1, 6)]
    rows = [{"instance": g["instance"], "profile": p, "tier": "T2a", "env": {"pysat_version": "1.9.dev3"}}
            for g, p in zip(gen, [prof(s=12.0), prof(s=45.0), prof(s=300.0),
                                  prof(status="subprocess_killed", s=960.1, cost=None, lb=20, completed=False),
                                  prof(s=899.0)])]
    elig, not_run = cc.select(gen, rows)
    assert [r["gen_seed"] for r in elig] == [102, 103, 105]
    assert [r["pop_idx"] for r in elig] == ["cc001", "cc002", "cc003"]
    assert {r["gen_seed"]: r["reason"].split(":")[0] for r in not_run} == {101: "below_window", 104: "censored"}
    assert len(elig) + len(not_run) == len(gen)


def test_select_refuses_missing_or_failed_rows():
    gen = [_gen(1), _gen(2)]
    with pytest.raises(SystemExit, match="no RC2 row"):
        cc.select(gen, [{"instance": gen[0]["instance"], "profile": prof()}])
    with pytest.raises(SystemExit, match="failed"):
        cc.select(gen, [{"instance": g["instance"], "profile": prof(s=-1.0)} for g in gen])


def test_calib_c_tasks_use_exactly_the_m2_full_pool_a35_arm():
    """Pooling calib_c with the M2 full pool per cell is only valid if the arm is identical."""
    with open(os.path.join(STAGING, "scripts", "manifest_m2_full_p40.tasks.csv"), encoding="utf-8") as f:
        a35 = [r for r in csv.DictReader(f) if r["arm"] == "p40_ls3p5"]
    ref = {k: {r[k] for r in a35} for k in ("config", "config_id", "pop_size", "ls_time_limit_s",
                                              "deadline_mode", "budget_s")}
    gen = [_gen(1)]
    elig, _ = cc.select(gen, [{"instance": gen[0]["instance"], "profile": prof(s=100.0)}])
    tasks = cc.tasks_for(elig)
    assert [t["solver_seed"] for t in tasks] == [1, 2, 3]
    assert len({t["job_id"] for t in tasks}) == 3 and all(t["job_id"].startswith("cc_") for t in tasks)
    for k, vals in ref.items():
        assert {str(t[k]) for t in tasks} == vals, k


def test_candidate_cell_table_is_reproducible_and_classifies_as_recorded():
    r = subprocess.run([sys.executable, "scripts/candidate_cells.py", "--check"], cwd=STAGING,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    with open(os.path.join(STAGING, "results", "corpus_freeze_prep", "summary.json"), encoding="utf-8") as f:
        s = json.load(f)
    assert s["rc2_class"] == {"eligible": 70, "below": 107, "censored": 113, "failed": 0}
    assert s["q2_primary"] == 9 and s["q2_context_0p5"] == 5 and s["beyond_gen1_either_arm"] == 15
    assert s["cells_rule_5_3_pass"] == ["max3sat_n250_a4.26"]
    assert s["category"]["promising"] == ["max2sat_n400_a2", "max2sat_n400_a2.15"]
    assert s["category"]["supported"] == []
    assert sorted(s["category"]["reference"]) == ["max3sat_n250_a4.26", "max3sat_n250_a4.35"]
