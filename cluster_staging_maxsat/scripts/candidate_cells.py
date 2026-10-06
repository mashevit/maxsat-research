#!/usr/bin/env python3
"""Candidate-cell table for the corpus freeze: RC2 calibration x M2 memetic, per cell.

Record: docs/current/CORPUS_FREEZE_PREP.md (repo). Nothing here uses rho; no
correlation of any kind is computed.

INPUTS (staging-root relative; every one is checked, nothing is guessed)

    data/generated/<batch>/manifest.jsonl     generator rows (cell, seed, sha)
    results/profile_<batch>_all.jsonl         one RC2 row per instance
    <memetic agg>/tasks.csv                   one row per memetic run, written by
                                              scripts/m2_results.py aggregate

    default batches: calib_a calib_b
    default memetic: results/m2_full_p40/agg/tasks.csv
    --batches / --memetic-agg add calib_c and its memetic run when they exist.

RC2 ELIGIBILITY (the agreed window, boundary convention fixed here)

    eligible  <=>  profile.completed is true
                   and final_cost == cost_lower_bound      (certified)
                   and 30 s < solve_s <= 900 s
    below     certified, 0 < solve_s <= 30 s               (memetic NOT run: decision)
    censored  status timeout / subprocess_killed at cap 900 (no certified target)
    failed    anything else, incl. solve_s <= 0 (wall-clock step) -- must be zero

The M2 pool was built with 30 <= s <= 900 (scripts/make_m2_manifests.py); no
certified instance has solve_s == 30.0, so both conventions select the same 70
(asserted below).

MEMETIC (primary arm p40_ls3p5 = configs/tier2/memetic_deeppolish_p40_ls3p5.yaml:
pop 40, ls.time_limit_s 3.5, 12,500 flips/call, deadline clip, 900 s budget,
stop at the RC2 optimum). The 0.5 s arm p40_ls0p5_clip is carried as context
columns only. Per instance (solver seeds collapsed first):

    succ              runs with class success, of runs
    median_ttt_s      median over runs, non-successes = +inf
    ert_s             sum over runs of min(wall, 900) / successes
    ert_calls         sum of children (= polish calls) / successes
    beyond_gen1       number of runs with ea_generations >= 2 (> 38 calls)
    q2                pre-registered Q2 "non-trivial" (goals §5.3 / M2 read-out
                      §6.2): successes < runs OR median TTT >= 45 s (5 % of 900)
    first_call_all    every run succeeded with its first polish call

THREE THINGS KEPT APART (the columns say which)

    run-level      a run that goes beyond generation 1         (beyond_gen1)
    instance-level an instance meeting the Q2 rule             (q2)
    cell-level     the §5.3 rule over the cell, with denominators (r1..r4)

§5.3 CELL RULE, LITERAL (docs/CORPUS_CALIBRATION_GOALS.md §5.3)

    r1  RC2 certified / generated >= 0.8                 (all seeds of the cell)
    r2  median solve_s over certified instances >= 10 s
    r3  Q2 instances / tested eligible instances >= 0.5  (primary arm)
    r4  every tested eligible instance has >= 1 success  (primary arm)

    r3/r4 are evaluated over the RC2-ELIGIBLE instances, because by decision no
    memetic run exists below the window; "every certified instance" in the
    goals doc is read as "every eligible certified instance". Instances without
    a memetic measurement are counted as not_run, never as success, failure or
    trivial.

CATEGORY (rule-based; no rho; written before this table was first printed)

    unsuitable     no RC2-eligible instance (checked first)
    reference      k = 3 and n = 250 (the historical uuf250 regime, c* ~ 1)
    supported      not reference; r1-r4 all pass
    promising      not reference; fails, but r2 and r4 pass, >= 1 Q2 instance,
                   and every failing condition among r1, r3 would pass with ONE
                   more favourable instance (deficit <= 1)
    unsuitable     everything else

    python3 scripts/candidate_cells.py                     # writes results/corpus_freeze_prep/
    python3 scripts/candidate_cells.py --check             # rebuild in memory, diff, exit 3 on drift
    python3 scripts/candidate_cells.py --batches calib_a calib_b calib_c \\
        --memetic-agg results/m2_full_p40/agg/tasks.csv results/calib_c_m2/agg/tasks.csv \\
        --out-dir results/calib_c_decision --decision      # after calib_c returns

stdlib only; run from the staging tree root.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import statistics
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

LO_S, HI_S, BUDGET_S = 30.0, 900.0, 900.0
Q2_TTT_S = 0.05 * BUDGET_S  # 45 s
CALLS_PER_GEN = 38          # pop 40, 2 elites
PRIMARY_ARM, CONTEXT_ARM = "p40_ls3p5", "p40_ls0p5_clip"
DEFAULT_BATCHES = ("calib_a", "calib_b")
DEFAULT_AGG = ("results/m2_full_p40/agg/tasks.csv",)
# The calib_c reinforcement cells, frozen in docs/current/CORPUS_FREEZE_PREP.md §5
# before any calib_c instance was profiled.
DECISION_CELLS = ("max2sat_n400_a2", "max2sat_n400_a2.15")

# What each (k, n) row adds beyond the 26 historical SATLIB uuf250/uuf200
# instances (n 200-250, alpha 4.26, c* 1 on 24/26, clause length 3).
DIVERSITY = {
    (3, 250): "none: same regime as the historical uuf250 set (n 250, alpha ~4.3, c* 1)",
    (3, 150): "small: n 150, alpha above threshold, c* 2-3; adjacent to the historical uuf200 points (n 200, c* 2)",
    (3, 100): "c* 4-5 at n 100, alpha 5-5.5 (density and c* decade change, clause length 3)",
    (3, 70): "c* 5-8 at n 70, alpha 6-6.5 (density and c* change, clause length 3)",
    (3, 50): "c* 9-13 at n 50, alpha 8-9 (highest density and c* among 3-SAT)",
    (2, 100): "clause length 2, c* 31-50 (second c* decade), n 100",
    (2, 150): "clause length 2, c* 23-28, n 150",
    (2, 250): "clause length 2, c* 18-22, n 250",
    (2, 400): "clause length 2, c* 18-23, n 400, m 800-920 (largest clause sets in the pool)",
}

CELL_COLS = [
    "cell_id", "family", "k", "n", "alpha", "m", "batches", "gen_seeds", "generated",
    "certified", "censored", "failed", "below_window", "eligible", "eligible_frac",
    "rc2_cert_solve_s_median", "rc2_elig_solve_s_min", "rc2_elig_solve_s_median",
    "rc2_elig_solve_s_max", "cstar_cert_range", "cstar_elig_range",
    "tested_primary", "not_run_eligible", "not_run_below_window",
    "a35_runs", "a35_successes", "a35_median_of_median_ttt_s", "a35_ert_s_median",
    "a35_ert_s_range", "a35_ert_calls_median", "a35_ert_calls_range", "a35_max_calls",
    "a35_instances_beyond_gen1", "a35_runs_beyond_gen1", "a35_first_call_all",
    "q2_a35", "q2_a35_frac", "q2_a35_wilson95", "q2_a05", "q2_either_arm",
    "beyond_gen1_either_not_q2", "single_run_only_instances", "work_evidence_instances",
    "isolated_support",
    "r1_certified", "r1_pass", "r2_median_s", "r2_pass", "r3_q2", "r3_pass", "r4_success",
    "r4_pass", "rule_5_3_pass", "category", "category_reason", "pop_idx_eligible",
    "diversity_vs_historical",
]
INST_COLS = [
    "instance", "instance_sha256", "batch", "cell_id", "k", "n", "alpha", "m", "gen_seed",
    "rc2_status", "rc2_solve_s", "c_star", "rc2_lower_bound", "rc2_class", "pop_idx",
    "pilot_idx", "a35_runs", "a35_succ", "a35_median_ttt_s", "a35_ert_s", "a35_ert_calls",
    "a35_max_calls", "a35_runs_beyond_gen1", "a35_q2", "a35_first_call_all",
    "a05_runs", "a05_succ", "a05_runs_beyond_gen1", "a05_q2",
]


class Fatal(SystemExit):
    def __init__(self, msg: str):
        super().__init__(f"FATAL: {msg}")


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    if not os.path.isfile(path):
        raise Fatal(f"{path} not found")
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def fnum(x: Any) -> Optional[float]:
    return None if x in (None, "") else float(x)


def rc2_class(prof: Dict[str, Any]) -> Tuple[str, Optional[float]]:
    s = fnum(prof.get("solve_s"))
    if prof.get("completed") is True:
        if prof.get("final_cost") != prof.get("cost_lower_bound") or s is None or s <= 0:
            return "failed", s
        if s <= LO_S:
            return "below", s
        if s <= HI_S:
            return "eligible", s
        return "censored", s  # completed only after the cap: not certified within budget
    if prof.get("status") in ("timeout", "subprocess_killed") and float(prof.get("cap_s") or 0) >= HI_S:
        return "censored", None
    return "failed", s


def load_rc2(batches) -> List[Dict[str, Any]]:
    rows, seen = [], {}
    for b in batches:
        gen = {r["instance"]: r for r in read_jsonl(os.path.join("data", "generated", b, "manifest.jsonl"))}
        prof_rows = read_jsonl(os.path.join("results", f"profile_{b}_all.jsonl"))
        if len(prof_rows) != len(gen):
            raise Fatal(f"{b}: {len(prof_rows)} RC2 rows vs {len(gen)} generated instances")
        for r in prof_rows:
            g = gen.get(r["instance"])
            if g is None:
                raise Fatal(f"{r['instance']}: no generator row")
            if g["instance_sha256"] in seen:
                raise Fatal(f"{r['instance']}: duplicate content of {seen[g['instance_sha256']]}")
            seen[g["instance_sha256"]] = r["instance"]
            prof = r["profile"]
            cls, s = rc2_class(prof)
            rows.append({
                "instance": r["instance"], "instance_sha256": g["instance_sha256"], "batch": b,
                "cell_id": g["cell_id"], "family": g["family"], "k": g["k"], "n": g["n"],
                "alpha": g["alpha"], "m": g["m"], "gen_seed": g["seed"],
                "rc2_status": prof.get("status"), "rc2_solve_s": s,
                "c_star": prof.get("final_cost") if cls in ("eligible", "below") else None,
                "rc2_lower_bound": prof.get("cost_lower_bound"), "rc2_class": cls,
            })
    return rows


def load_runs(paths) -> Dict[str, Dict[str, List[Dict[str, str]]]]:
    """sha -> arm -> runs (success / budget_exhausted only; anything else is fatal)."""
    out: Dict[str, Dict[str, List[Dict[str, str]]]] = defaultdict(lambda: defaultdict(list))
    for p in paths:
        if not os.path.isfile(p):
            raise Fatal(f"{p} not found")
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["cls"] not in ("success", "budget_exhausted"):
                    raise Fatal(f"{p}: {r['job_id']} class {r['cls']} -- resolve before reading cells")
                out[r["instance_sha256"]][r["arm"]].append(r)
    return out


def inst_stats(runs: List[Dict[str, str]]) -> Dict[str, Any]:
    if not runs:
        return {}
    succ = sum(r["cls"] == "success" for r in runs)
    ttt = sorted(float(r["success_ttt_s"]) if r["cls"] == "success" else math.inf for r in runs)
    med = statistics.median(ttt)
    walls = sum(min(float(r["wall_time_s"]), BUDGET_S) for r in runs)
    calls = sum(int(r["children"]) for r in runs)
    bg1 = sum(int(r["ea_generations"]) >= 2 for r in runs)
    return {
        "runs": len(runs), "succ": succ, "median_ttt_s": med,
        "ert_s": walls / succ if succ else math.inf, "ert_calls": calls / succ if succ else math.inf,
        "max_calls": max(int(r["children"]) for r in runs), "runs_beyond_gen1": bg1,
        "q2": int(succ < len(runs) or med >= Q2_TTT_S),
        "first_call_all": int(all(r["cls"] == "success" and int(r["children"]) == 1 for r in runs)),
    }


def wilson(x: int, n: int) -> str:
    if n == 0:
        return ""
    z, p = 1.959964, x / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{max(0.0, c - h):.2f}-{min(1.0, c + h):.2f}"


def fmt(x: Optional[float], nd: int = 1) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isinf(x):
        return "inf"
    return f"{x:.{nd}f}"


def rng_str(xs) -> str:
    xs = [x for x in xs if x is not None]
    if not xs:
        return ""
    lo, hi = min(xs), max(xs)
    return f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"


def categorise(c: Dict[str, Any]) -> Tuple[str, str]:
    if c["eligible"] == 0:
        return "unsuitable", "no RC2-eligible instance (30 s < t <= 900 s)"
    if c["k"] == 3 and c["n"] == 250:
        return "reference", "historical uuf250 regime (k 3, n 250, c* 1); replication only"
    if c["rule_5_3_pass"]:
        return "supported", "passes §5.3 r1-r4"
    fails = [r for r in ("r1", "r2", "r3", "r4") if not c[f"{r}_pass"]]
    if c["r2_pass"] and c["r4_pass"] and c["q2_a35"] >= 1:
        def_r1 = math.ceil(0.8 * c["generated"]) - c["certified"]
        def_r3 = math.ceil(0.5 * c["tested_primary"]) - c["q2_a35"]
        if (c["r1_pass"] or def_r1 <= 1) and (c["r3_pass"] or def_r3 <= 1):
            return "promising", f"fails {','.join(fails)} by one instance; Q2 {c['q2_a35']}/{c['tested_primary']}"
    why = []
    if not c["r1_pass"]:
        why.append(f"r1 {c['r1_certified']}")
    if not c["r2_pass"]:
        why.append(f"r2 median {c['r2_median_s']} s")
    if not c["r3_pass"]:
        why.append(f"r3 Q2 {c['r3_q2']}")
    if not c["r4_pass"]:
        why.append(f"r4 {c['r4_success']}")
    return "unsuitable", "fails " + "; ".join(why)


def build(batches, agg_paths) -> Dict[str, str]:
    rc2 = load_rc2(batches)
    runs = load_runs(agg_paths)
    # The (30, 900] convention selects the M2 pool's 30 <= s <= 900: no tie at 30.
    ties = [r["instance"] for r in rc2 if r["rc2_class"] in ("below", "eligible") and r["rc2_solve_s"] == LO_S]
    if ties:
        raise Fatal(f"certified instance(s) exactly at {LO_S} s: {ties} -- boundary convention matters")
    failed = [r["instance"] for r in rc2 if r["rc2_class"] == "failed"]
    if failed:
        raise Fatal(f"RC2 failed rows must be re-run before reading cells: {failed}")
    # pop_idx / pilot_idx (full-pool and pilot numbering are different; carry both)
    pop_idx, pilot_idx = {}, {}
    for p in agg_paths:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pop_idx[r["instance_sha256"]] = r.get("pop_idx", "")
    pilot_csv = "scripts/manifest_m2_pilot.tasks.csv"
    if os.path.isfile(pilot_csv):
        with open(pilot_csv, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                pilot_idx[r["instance_sha256"]] = r["pilot_idx"]

    inst_rows = []
    for r in rc2:
        a35 = inst_stats(runs.get(r["instance_sha256"], {}).get(PRIMARY_ARM, []))
        a05 = inst_stats(runs.get(r["instance_sha256"], {}).get(CONTEXT_ARM, []))
        if r["rc2_class"] != "eligible" and (a35 or a05):
            raise Fatal(f"{r['instance']}: memetic runs on a non-eligible instance")
        if a35 and a35["runs"] != 3:
            raise Fatal(f"{r['instance']}: {a35['runs']} primary runs, expected 3")
        r.update({
            "pop_idx": pop_idx.get(r["instance_sha256"], ""),
            "pilot_idx": pilot_idx.get(r["instance_sha256"], ""),
            "_a35": a35, "_a05": a05,
        })
        inst_rows.append(r)

    cells: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in inst_rows:
        cells[r["cell_id"]].append(r)

    cell_rows = []
    for cid, rs in cells.items():
        f = rs[0]
        cert = [r for r in rs if r["rc2_class"] in ("below", "eligible")]
        elig = [r for r in rs if r["rc2_class"] == "eligible"]
        tested = [r for r in elig if r["_a35"]]
        es = [r["rc2_solve_s"] for r in elig]
        a35 = [r["_a35"] for r in tested]
        q2 = sum(s["q2"] for s in a35)
        q2_05 = sum(r["_a05"].get("q2", 0) for r in elig)
        q2_any = sum(int(r["_a35"].get("q2", 0) or r["_a05"].get("q2", 0)) for r in elig)
        bg_any = [r for r in elig if (r["_a35"].get("runs_beyond_gen1", 0) + r["_a05"].get("runs_beyond_gen1", 0)) > 0]
        bg_not_q2 = [r for r in bg_any if not (r["_a35"].get("q2", 0) or r["_a05"].get("q2", 0))]
        single = [r for r in bg_not_q2 if r["_a35"].get("runs_beyond_gen1", 0) + r["_a05"].get("runs_beyond_gen1", 0) == 1]
        evidence = {r["instance"] for r in bg_any} | {r["instance"] for r in elig if r["_a35"].get("q2", 0) or r["_a05"].get("q2", 0)}
        med_cert = statistics.median([r["rc2_solve_s"] for r in cert]) if cert else None
        c = {
            "cell_id": cid, "family": f["family"], "k": f["k"], "n": f["n"], "alpha": f["alpha"], "m": f["m"],
            "batches": ",".join(sorted({r["batch"] for r in rs})),
            "gen_seeds": ",".join(str(s) for s in sorted(r["gen_seed"] for r in rs)),
            "generated": len(rs), "certified": len(cert),
            "censored": sum(r["rc2_class"] == "censored" for r in rs),
            "failed": 0, "below_window": sum(r["rc2_class"] == "below" for r in rs),
            "eligible": len(elig), "eligible_frac": f"{len(elig)}/{len(rs)}",
            "rc2_cert_solve_s_median": fmt(med_cert),
            "rc2_elig_solve_s_min": fmt(min(es)) if es else "", "rc2_elig_solve_s_median": fmt(statistics.median(es)) if es else "",
            "rc2_elig_solve_s_max": fmt(max(es)) if es else "",
            "cstar_cert_range": rng_str([r["c_star"] for r in cert]), "cstar_elig_range": rng_str([r["c_star"] for r in elig]),
            "tested_primary": len(tested), "not_run_eligible": len(elig) - len(tested),
            "not_run_below_window": sum(r["rc2_class"] == "below" for r in rs),
            "a35_runs": sum(s["runs"] for s in a35), "a35_successes": sum(s["succ"] for s in a35),
            "a35_median_of_median_ttt_s": fmt(statistics.median([s["median_ttt_s"] for s in a35])) if a35 else "",
            "a35_ert_s_median": fmt(statistics.median([s["ert_s"] for s in a35])) if a35 else "",
            "a35_ert_s_range": f"{fmt(min(s['ert_s'] for s in a35))}-{fmt(max(s['ert_s'] for s in a35))}" if a35 else "",
            "a35_ert_calls_median": fmt(statistics.median([s["ert_calls"] for s in a35])) if a35 else "",
            "a35_ert_calls_range": f"{fmt(min(s['ert_calls'] for s in a35))}-{fmt(max(s['ert_calls'] for s in a35))}" if a35 else "",
            "a35_max_calls": max((s["max_calls"] for s in a35), default=""),
            "a35_instances_beyond_gen1": sum(s["runs_beyond_gen1"] > 0 for s in a35),
            "a35_runs_beyond_gen1": f"{sum(s['runs_beyond_gen1'] for s in a35)}/{sum(s['runs'] for s in a35)}" if a35 else "",
            "a35_first_call_all": sum(s["first_call_all"] for s in a35),
            "q2_a35": q2, "q2_a35_frac": f"{q2}/{len(tested)}" if tested else "",
            "q2_a35_wilson95": wilson(q2, len(tested)), "q2_a05": q2_05, "q2_either_arm": q2_any,
            "beyond_gen1_either_not_q2": len(bg_not_q2), "single_run_only_instances": len(single),
            "work_evidence_instances": len(evidence),
            "isolated_support": int(len(evidence) == 1),
            "r1_certified": f"{len(cert)}/{len(rs)}", "r1_pass": int(len(cert) >= 0.8 * len(rs)),
            "r2_median_s": fmt(med_cert), "r2_pass": int(med_cert is not None and med_cert >= 10.0),
            "r3_q2": f"{q2}/{len(tested)}", "r3_pass": int(bool(tested) and q2 >= 0.5 * len(tested)),
            "r4_success": f"{sum(s['succ'] > 0 for s in a35)}/{len(tested)}",
            "r4_pass": int(bool(tested) and all(s["succ"] > 0 for s in a35)),
            "pop_idx_eligible": " ".join(f"#{r['pop_idx']}" if r["pop_idx"] else "(new)" for r in
                                         sorted(elig, key=lambda r: int(r["pop_idx"]) if r["pop_idx"] else 10**6)),
            "diversity_vs_historical": DIVERSITY.get((f["k"], f["n"]), ""),
        }
        c["rule_5_3_pass"] = int(c["r1_pass"] and c["r2_pass"] and c["r3_pass"] and c["r4_pass"])
        c["category"], c["category_reason"] = categorise(c)
        cell_rows.append(c)
    cell_rows.sort(key=lambda c: (-c["k"], c["n"], c["alpha"]))

    def csv_text(cols, rows) -> str:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow(row)
        return buf.getvalue()

    flat = []
    for r in sorted(inst_rows, key=lambda r: (r["cell_id"], r["gen_seed"])):
        a35, a05 = r["_a35"], r["_a05"]
        flat.append(dict(
            r, a35_runs=a35.get("runs", ""), a35_succ=a35.get("succ", ""),
            a35_median_ttt_s=fmt(a35.get("median_ttt_s"), 3) if a35 else "",
            a35_ert_s=fmt(a35.get("ert_s"), 3) if a35 else "", a35_ert_calls=fmt(a35.get("ert_calls"), 3) if a35 else "",
            a35_max_calls=a35.get("max_calls", ""), a35_runs_beyond_gen1=a35.get("runs_beyond_gen1", ""),
            a35_q2=a35.get("q2", ""), a35_first_call_all=a35.get("first_call_all", ""),
            a05_runs=a05.get("runs", ""), a05_succ=a05.get("succ", ""),
            a05_runs_beyond_gen1=a05.get("runs_beyond_gen1", ""), a05_q2=a05.get("q2", ""),
        ))

    totals = {
        "batches": list(batches), "memetic_agg": list(agg_paths),
        "window": f"{LO_S:g} < solve_s <= {HI_S:g}", "q2_rule": f"succ < runs or median TTT >= {Q2_TTT_S:g} s",
        "generated": len(inst_rows),
        "rc2_class": {k: sum(r["rc2_class"] == k for r in inst_rows) for k in ("eligible", "below", "censored", "failed")},
        "eligible_tested_primary": sum(1 for r in inst_rows if r["_a35"]),
        "q2_primary": sum(r["_a35"].get("q2", 0) for r in inst_rows),
        "q2_context_0p5": sum(r["_a05"].get("q2", 0) for r in inst_rows),
        "beyond_gen1_either_arm": sum(1 for r in inst_rows if r["_a35"].get("runs_beyond_gen1", 0) + r["_a05"].get("runs_beyond_gen1", 0) > 0),
        "first_call_all_primary": sum(r["_a35"].get("first_call_all", 0) for r in inst_rows),
        "cells": len(cell_rows),
        "cells_with_eligible": sum(c["eligible"] > 0 for c in cell_rows),
        "cells_rule_5_3_pass": [c["cell_id"] for c in cell_rows if c["rule_5_3_pass"]],
        "category": {k: [c["cell_id"] for c in cell_rows if c["category"] == k]
                     for k in ("reference", "supported", "promising", "unsuitable")},
    }
    return {
        "candidate_cells.csv": csv_text(CELL_COLS, cell_rows),
        "candidate_instances.csv": csv_text(INST_COLS, flat),
        "summary.json": json.dumps(totals, indent=1, sort_keys=True) + "\n",
        "_cells": cell_rows,
    }


def decision(cells: List[Dict[str, Any]]) -> str:
    out = ["calib_c reinforcement decision (docs/current/CORPUS_FREEZE_PREP.md §5.4, rule unchanged from goals §5.3):"]
    for cid in DECISION_CELLS:
        c = next((c for c in cells if c["cell_id"] == cid), None)
        if c is None:
            out.append(f"  {cid}: MISSING")
            continue
        out.append(f"  {cid}: generated {c['generated']} certified {c['r1_certified']} (r1 {'pass' if c['r1_pass'] else 'FAIL'}), "
                   f"median cert {c['r2_median_s']} s (r2 {'pass' if c['r2_pass'] else 'FAIL'}), "
                   f"eligible {c['eligible']} tested {c['tested_primary']} not_run {c['not_run_eligible']}, "
                   f"Q2 {c['r3_q2']} [{c['q2_a35_wilson95']}] (r3 {'pass' if c['r3_pass'] else 'FAIL'}), "
                   f"success>0 {c['r4_success']} (r4 {'pass' if c['r4_pass'] else 'FAIL'}) -> "
                   f"{'FREEZE-ELIGIBLE' if c['rule_5_3_pass'] else 'NOT FROZEN'}")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batches", nargs="+", default=list(DEFAULT_BATCHES))
    ap.add_argument("--memetic-agg", nargs="+", default=list(DEFAULT_AGG))
    ap.add_argument("--out-dir", default="results/corpus_freeze_prep")
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff against --out-dir")
    ap.add_argument("--decision", action="store_true", help="print the calib_c pre-registered decision")
    a = ap.parse_args(argv)
    files = build(a.batches, a.memetic_agg)
    cells = files.pop("_cells")
    if a.check:
        bad = []
        for name, text in files.items():
            p = os.path.join(a.out_dir, name)
            if not os.path.isfile(p) or open(p, encoding="utf-8").read() != text:
                bad.append(p)
        if bad:
            print("DRIFT: " + ", ".join(bad), file=sys.stderr)
            return 3
        print(f"CHECK OK: {', '.join(files)} in {a.out_dir}")
    else:
        os.makedirs(a.out_dir, exist_ok=True)
        for name, text in files.items():
            with open(os.path.join(a.out_dir, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
        print(f"wrote {', '.join(files)} to {a.out_dir}")
    s = json.loads(files["summary.json"])
    print(f"instances {s['generated']}  rc2 {s['rc2_class']}  tested {s['eligible_tested_primary']}  "
          f"Q2 primary {s['q2_primary']}  Q2 0.5 s {s['q2_context_0p5']}  beyond-gen1 {s['beyond_gen1_either_arm']}")
    for k, v in s["category"].items():
        print(f"  {k:11s} {len(v):2d}  {' '.join(v)}")
    if a.decision:
        print(decision(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
