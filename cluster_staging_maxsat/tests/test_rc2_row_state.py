"""scripts/rc2_row_state.py -- the resume decision for RC2 profile arrays.

Run from inside cluster_staging_maxsat/: python -m pytest tests -q
(the other tests here import the staging `src`, which is why the cwd matters).

The row shapes below are what src.cli.profile_hardness writes, taken from
results/profile/gen_pilot_cap60.jsonl (optimal / subprocess_killed / timeout)
and from the error branches of profile_instance_subprocess.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(STAGING, "scripts"))

import rc2_row_state as rs  # noqa: E402

INST = "data/generated/calib_a/wksat_v50_k3_sr6.00_hr0.00_w1_uniform_s1.wcnf"


def _row(status, cap, completed=None, instance=INST):
    if completed is None:
        completed = status == "optimal"
    return {
        "instance": instance,
        "size_mb": 0.003,
        "profile": {
            "cap_s": cap, "solver": "rc2", "status": status,
            "solve_s": 2.8 if completed else cap + 15.0,
            "final_cost": 6 if completed else None,
            "cost_lower_bound": 6 if completed else 3,
            "completed": completed,
            "error": None if completed else status,
        },
        "tier": "T1" if completed else "T3",
    }


def _write(path, rows, tail=""):
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
        f.write(tail)


@pytest.mark.parametrize("status,cap,expected", [
    ("optimal", 900.0, "skip:completed"),
    ("optimal", 60.0, "skip:completed"),          # a completion at any cap is final
    ("timeout", 900.0, "skip:censored"),
    ("subprocess_killed", 900.0, "skip:censored"),
    ("subprocess_killed", 1800.0, "skip:censored"),  # censored at a higher cap still covers 900
    ("timeout", 60.0, "run:censored_lower_cap"),     # budget raised: re-run
    ("error", 900.0, "run:failed"),
    ("unsat", 900.0, "run:failed"),                  # impossible on pure-soft: a failure
])
def test_single_row_classification(tmp_path, status, cap, expected):
    out = tmp_path / "task_1.jsonl"
    _write(out, [_row(status, cap)])
    assert rs.state_for(str(out), INST, 900.0) == expected


def test_absent_file_and_empty_file(tmp_path):
    out = tmp_path / "task_1.jsonl"
    assert rs.state_for(str(out), INST, 900.0) == "run:absent"
    out.write_text("")
    assert rs.state_for(str(out), INST, 900.0) == "run:absent"


def test_torn_last_line_is_ignored(tmp_path):
    """A task killed mid-write leaves a partial JSON line; it must not mask
    an earlier valid row, nor count as one."""
    out = tmp_path / "task_1.jsonl"
    _write(out, [_row("optimal", 900.0)], tail='{"instance": "' + INST + '", "profile": {"sta')
    assert rs.state_for(str(out), INST, 900.0) == "skip:completed"
    _write(out, [], tail='{"instance": "x"')
    assert rs.state_for(str(out), INST, 900.0) == "run:absent"


def test_last_row_wins(tmp_path):
    """Re-runs append; the newest row for the instance decides."""
    out = tmp_path / "task_1.jsonl"
    _write(out, [_row("error", 900.0), _row("optimal", 900.0)])
    assert rs.state_for(str(out), INST, 900.0) == "skip:completed"
    _write(out, [_row("optimal", 900.0), _row("error", 900.0)])
    assert rs.state_for(str(out), INST, 900.0) == "run:failed"


def test_other_instance_in_file_does_not_count(tmp_path):
    out = tmp_path / "task_1.jsonl"
    _write(out, [_row("optimal", 900.0, instance="data/other.wcnf")])
    assert rs.state_for(str(out), INST, 900.0) == "run:other_instance"


def test_missing_cap_on_censored_row_is_failed(tmp_path):
    out = tmp_path / "task_1.jsonl"
    r = _row("timeout", 900.0)
    r["profile"]["cap_s"] = None
    _write(out, [r])
    assert rs.state_for(str(out), INST, 900.0) == "run:failed"


def test_compress_ids():
    assert rs.compress_ids([]) == ""
    assert rs.compress_ids([4]) == "4"
    assert rs.compress_ids([1, 2, 3]) == "1-3"
    assert rs.compress_ids([3, 7, 8, 9, 15]) == "3,7-9,15"


def test_pending_over_manifest(tmp_path):
    insts = [f"data/generated/t/i{i}.wcnf" for i in range(1, 7)]
    manifest = tmp_path / "manifest.txt"
    manifest.write_text("\n".join(insts) + "\n")
    outdir = tmp_path / "out"
    outdir.mkdir()
    _write(outdir / "task_1.jsonl", [_row("optimal", 900.0, instance=insts[0])])
    _write(outdir / "task_2.jsonl", [_row("timeout", 900.0, instance=insts[1])])
    _write(outdir / "task_3.jsonl", [_row("error", 900.0, instance=insts[2])])
    _write(outdir / "task_4.jsonl", [_row("timeout", 60.0, instance=insts[3])])
    # task 5: no file; task 6: file for a different instance
    _write(outdir / "task_6.jsonl", [_row("optimal", 900.0, instance="data/x.wcnf")])
    pending, counts = rs.pending_tasks(str(manifest), str(outdir), 900.0)
    assert pending == [3, 4, 5, 6]
    assert counts == {
        "skip:completed": 1, "skip:censored": 1, "run:failed": 1,
        "run:censored_lower_cap": 1, "run:absent": 1, "run:other_instance": 1,
    }
    assert rs.compress_ids(pending) == "3-6"


def test_cli_end_to_end(tmp_path):
    """The exact invocations the sbatch driver and the submit wrapper make."""
    script = os.path.join(STAGING, "scripts", "rc2_row_state.py")
    out = tmp_path / "task_1.jsonl"
    _write(out, [_row("optimal", 900.0)])
    r = subprocess.run([sys.executable, script, "--out", str(out), "--instance", INST,
                        "--cap", "900"], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "skip:completed"

    manifest = tmp_path / "m.txt"
    manifest.write_text(INST + "\n" + "data/generated/calib_a/other.wcnf\n")
    r = subprocess.run([sys.executable, script, "--manifest", str(manifest),
                        "--outdir", str(tmp_path), "--cap", "900", "--pending", "--summary"],
                       capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "2"
    assert "skip:completed\t1" in r.stderr and "run:absent\t1" in r.stderr
