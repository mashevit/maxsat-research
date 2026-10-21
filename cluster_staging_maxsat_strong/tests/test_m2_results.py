"""scripts/m2_results.py on sidecars without the M2 grouping columns
(analysis_group, m, arm), as make_oracle900_manifest / make_ks2check_manifest
write them: aggregate groups by family and uses one arm per config.
"""
from __future__ import annotations

import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "scripts"))

import m2_results  # noqa: E402

COLS = ["task_id", "job_id", "config_id", "pop_size", "ls_time_limit_s", "deadline_mode", "solver_seed",
        "budget_s", "pop_idx", "instance", "instance_sha256", "family", "oracle_cost"]


def test_aggregate_without_analysis_group(tmp_path, capsys):
    tasks = [dict(task_id=str(i + 1), job_id=f"x_{i}", config_id="c", pop_size="40", ls_time_limit_s="3.5",
                  deadline_mode="clip", solver_seed=str(i + 1), budget_s="900", pop_idx="o001",
                  instance="data/a.cnf", instance_sha256="ab", family="fam", oracle_cost="3")
             for i in range(2)]
    man = tmp_path / "manifest_t.tsv"
    man.write_text("".join(f"{t['job_id']}\tdata/a.cnf\n" for t in tasks))
    with open(tmp_path / "manifest_t.tasks.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(tasks)
    out = tmp_path / "tasks"
    out.mkdir()
    rec = {"job_id": "x_0", "config_id": "c", "seed": 1, "instance_sha256": "ab", "budget_s": 900.0,
           "grace_s": 60.0, "stop_at_oracle": True, "oracle_cost": 3, "status": "ok", "stop_reason": "target",
           "time_to_target_s": 0.5, "wall_time_s": 0.6, "cpu_time_s": 0.6, "children": 1, "total_flips": 10,
           "config": {"ea": {"pop_size": 40, "deadline_mode": "clip"}, "ls": {"time_limit_s": 3.5, "ls_polish_flips": 12500}},
           "hparams": {"class": "hard_weighted", "features": {"n_eff": 9},
                       "overrides": {"ea": {"mutation_k": 2, "pop_size": 10},
                                     "hard": {"moves": {"keep_sat": "ks2"}}}}}
    (out / "x_0.jsonl").write_text(json.dumps(rec) + "\n")
    assert m2_results.main(["aggregate", "--manifest", str(man), "--outdir", str(out)]) == 0
    assert "fam" in capsys.readouterr().out
    agg = tmp_path / "agg"
    rows = list(csv.DictReader(open(agg / "tasks.csv")))
    assert [r["cls"] for r in rows] == ["success", "infra_missing"]
    assert rows[0]["analysis_group"] == "fam" and rows[0]["arm"] == "c"
    assert (rows[0]["hp_pop_size"], rows[0]["hp_keep_sat"]) == ("10", "ks2")
    grp = list(csv.DictReader(open(agg / "by_group_config.csv")))
    assert [(g["analysis_group"], g["successes"]) for g in grp] == [("fam", "1")]
    assert (agg / "paired_by_instance_seed.csv").exists()
