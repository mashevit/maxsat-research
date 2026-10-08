"""calib_2sat_sc readout rules (docs/current/CALIB_2SAT_SC.md §6, repo).

Synthetic RC2 rows only: the batch has no rows yet. Pins the instance classes
(c* and seconds kept apart; no incumbent ever reported as c*), the cell
outcomes, and that every instance appears in the output. Run from inside
cluster_staging_maxsat/.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys

import pytest

STAGING = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(STAGING, "scripts"))
import calib_2sat_sc_readout as ro  # noqa: E402

MANIFEST = os.path.join(STAGING, "data", "generated", "calib_2sat_sc", "manifest.jsonl")


def prof(status="optimal", s=100.0, cost=5, lb=5, completed=True, cap=900):
    return {"status": status, "solve_s": s, "final_cost": cost, "cost_lower_bound": lb,
            "completed": completed, "cap_s": cap, "error": None}


@pytest.mark.parametrize("p,cls,cstar,lb", [
    (prof(s=100.0, cost=5, lb=5), "eligible", 5, None),
    (prof(s=30.0, cost=5, lb=5), "fast", 5, None),          # 30 s is outside (30, 900]
    (prof(s=30.001, cost=3, lb=3), "eligible", 3, None),
    (prof(s=900.0, cost=3, lb=3), "eligible", 3, None),
    (prof(s=500.0, cost=2, lb=2), "low_cstar", 2, None),    # c* <= 2 whatever the time
    (prof(s=0.01, cost=0, lb=0), "low_cstar", 0, None),
    (prof(s=900.4, cost=7, lb=7), "censored", 7, None),     # proven, but after the cap
    (prof(status="subprocess_killed", s=960.1, cost=None, lb=18, completed=False),
     "censored", None, 18),
    (prof(status="timeout", s=900.0, cost=None, lb=4, completed=False), "censored", None, 4),
    (prof(status="timeout", s=60.0, cost=None, lb=4, completed=False, cap=60), "failed", None, 4),
    (prof(cost=6, lb=5), "failed", None, 5),                # cost != bound: not a proof
    (prof(s=-0.8), "failed", None, 5),
    (None, "failed", None, None),                           # no row
])
def test_instance_class(p, cls, cstar, lb) -> None:
    ic = ro.instance_class(p)
    assert (ic["class"], ic["c_star"], ic["lower_bound"]) == (cls, cstar, lb)


def test_censored_row_never_reports_an_incumbent() -> None:
    """A timeout row with a final_cost (an incumbent) must not become c*."""
    ic = ro.instance_class(prof(status="timeout", s=900.0, cost=40, lb=12, completed=False))
    assert ic["c_star"] is None and ic["lower_bound"] == 12 and ic["class"] == "censored"


@pytest.mark.parametrize("classes,outcome", [
    (["eligible"] * 3 + ["censored"] * 2, "promising"),
    (["low_cstar", "fast", "low_cstar", "eligible", "eligible"], "too_easy"),
    (["censored"] * 3 + ["eligible"] * 2, "too_hard"),
    (["eligible", "eligible", "censored", "censored", "low_cstar"], "mixed"),
    (["eligible"] * 4 + ["failed"], "incomplete"),
])
def test_cell_outcome(classes, outcome) -> None:
    assert ro.cell_outcome(classes) == outcome


def _rows_for(manifest_rows, fn):
    return [{"instance": g["instance"], "profile": fn(g),
             "env": {"pysat_version": "1.9.dev3", "python": "3.11.15", "host": "h"}}
            for g in manifest_rows]


@pytest.mark.skipif(not os.path.isfile(MANIFEST), reason="calib_2sat_sc not generated")
def test_build_reports_every_instance(tmp_path) -> None:
    gen = [json.loads(l) for l in open(MANIFEST) if l.strip()]

    def fake(g):
        if g["n"] == 2000:
            return prof(s=0.5, cost=1, lb=1)                       # too easy
        if g["n"] == 8000:
            return prof(s=200.0, cost=9, lb=9)                     # promising
        return prof(status="subprocess_killed", s=960.0, cost=None, lb=30, completed=False)

    rows = tmp_path / "rows.jsonl"
    rows.write_text("".join(json.dumps(r) + "\n" for r in _rows_for(gen, fake)))
    out = ro.build(MANIFEST, str(rows))
    inst = list(csv.DictReader(io.StringIO(out["instances.csv"])))
    cells = {c["cell_id"]: c for c in csv.DictReader(io.StringIO(out["cells.csv"]))}
    assert len(inst) == 45 and len(cells) == 9
    assert {c["outcome"] for cid, c in cells.items() if "_n2000_" in cid} == {"too_easy"}
    assert {c["outcome"] for cid, c in cells.items() if "_n8000_" in cid} == {"promising"}
    assert {c["outcome"] for cid, c in cells.items() if "_n32000_" in cid} == {"too_hard"}
    big = [r for r in inst if r["n"] == "32000"]
    assert all(r["c_star"] == "" and r["lower_bound"] == "30" for r in big)
    assert cells["max2sat_distinct_n32000_a1.2"]["n_eps3"] == "256.00"


@pytest.mark.skipif(not os.path.isfile(MANIFEST), reason="calib_2sat_sc not generated")
def test_build_without_rows_marks_everything_incomplete(tmp_path) -> None:
    out = ro.build(MANIFEST, str(tmp_path / "absent.jsonl"))
    cells = list(csv.DictReader(io.StringIO(out["cells.csv"])))
    assert {c["outcome"] for c in cells} == {"incomplete"}
