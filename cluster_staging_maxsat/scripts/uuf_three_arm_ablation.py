#!/usr/bin/env python3
"""Three-arm ablation on the 26 SATLIB tier-2 instances (uuf250/uuf200).

Arms (DIVERGENCE.md §"The JW-seeded ablation arm"):

    uni = local_multistart_deeppolish      uniform restarts + 0.5 s polish
    jw  = local_multistart_jw_deeppolish   JW-seeded restarts + 0.5 s polish
    mem = memetic_deeppolish               JW population + EA + 0.5 s polish

Differences: jw/uni = JW initialisation, mem/jw = population/crossover/EA
(plus inheritance of polished parents), mem/uni = the whole package.

Conventions (same as m2_rho_analysis.py where they overlap):
- sampling unit = instance; 5 seeds collapsed first;
- ERT_s = sum over seeds of min(wall, 900) for successes and 900 for failures,
  / successes; ERT_flips = sum total_flips / successes; ERT_polish = sum of
  polish calls (restarts for multistart, children for memetic) / successes.
  Polish calls are the effort unit least sensitive to node speed, since every
  polish is a fixed 0.5 s; flips and seconds are reported alongside.
- per-instance log ERT ratios; geometric mean with a percentile bootstrap CI
  over instances stratified by group (B = 10 000), Wilcoxon signed-rank;
- per-run time to target, censored at 900 s: Kaplan-Meier medians per arm and a
  log-rank test stratified by instance.

Run from cluster_staging_maxsat/:
    python3 scripts/uuf_three_arm_ablation.py
Writes results/tier2_uuf_ablation/.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
FILES = {
    "uni": ROOT / "results/tier2_local_multistart_all.jsonl",
    "jw": ROOT / "results/tier2_local_multistart_jw_all.jsonl",
    "mem": ROOT / "results/tier2_memetic_all.jsonl",
}
CONFIG = {"uni": "local_multistart_deeppolish", "jw": "local_multistart_jw_deeppolish",
          "mem": "memetic_deeppolish"}
T2_INDEX = ROOT / "results/tier2_memetic_instance_index.csv"
OUT = ROOT / "results/tier2_uuf_ablation"
ARMS = ("uni", "jw", "mem")
PAIRS = [("jw", "uni", "JW initialisation"), ("mem", "jw", "population / crossover / EA"),
         ("mem", "uni", "whole package")]
UNITS = ("s", "polish", "flips")
BUDGET = 900.0
B = 10_000
RNG_SEED = 20261006


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def polishes(r):
    return r["children"] if r["solver"] != "local_multistart" else r["restarts"]


def load_runs():
    runs = {}
    for a in ARMS:
        rs = [r for r in read_jsonl(FILES[a]) if r["config_id"] == CONFIG[a]]
        assert len(rs) == 130, (a, len(rs))
        assert all(r["status"] == "ok" and r["hard_violations"] == 0 for r in rs), a
        assert all((r["stop_reason"] == "target") == (r["best_cost"] <= r["oracle_cost"]) for r in rs), a
        runs[a] = rs
    keys = {a: sorted((r["instance_sha256"], r["seed"]) for r in runs[a]) for a in ARMS}
    assert keys["uni"] == keys["jw"] == keys["mem"], "arms are not on the same instance x seed grid"
    return runs


def instance_table(runs):
    with open(T2_INDEX, newline="") as f:
        idx = {r["sha256"]: r for r in csv.DictReader(f)}
    by = defaultdict(lambda: defaultdict(list))
    for a in ARMS:
        for r in runs[a]:
            by[r["instance_sha256"]][a].append(r)
    rows = []
    for sha, arms in by.items():
        ix = idx[sha]
        row = {"instance": ix["instance"], "group": ix["group"], "n_vars": arms["uni"][0]["n_vars"],
               "c_star": int(ix["rc2_final_cost"]), "rc2_solve_s": float(ix["rc2_solve_s"])}
        for a in ARMS:
            rs = sorted(arms[a], key=lambda r: r["seed"])
            ok = [r["stop_reason"] == "target" for r in rs]
            ns = sum(ok)
            spend = {"s": [min(float(r["wall_time_s"]), BUDGET) if o else BUDGET for r, o in zip(rs, ok)],
                     "polish": [polishes(r) for r in rs], "flips": [r["total_flips"] for r in rs]}
            row[f"{a}_succ"] = ns
            for u in UNITS:
                row[f"{a}_ert_{u}"] = round(sum(spend[u]) / ns, 3) if ns else ""
            row[f"{a}_flips_per_polish"] = round(sum(spend["flips"]) / sum(spend["polish"]), 1)
            row[f"{a}_ttt_s1..s5"] = ";".join(f"{r['wall_time_s']:.1f}" if o else "fail" for r, o in zip(rs, ok))
        for hi, lo, _ in PAIRS:
            for u in UNITS:
                h, l = row[f"{hi}_ert_{u}"], row[f"{lo}_ert_{u}"]
                row[f"ratio_{hi}_over_{lo}_{u}"] = round(h / l, 4) if h != "" and l != "" else ""
        rows.append(row)
    rows.sort(key=lambda r: r["rc2_solve_s"])
    return rows


def geomean_ci(logs, strata, rng):
    logs = np.asarray(logs)
    groups = defaultdict(list)
    for i, s in enumerate(strata):
        groups[s].append(i)
    groups = [np.array(g) for g in groups.values()]
    I = np.concatenate([g[rng.integers(0, len(g), (B, len(g)))] for g in groups], axis=1)
    bm = logs[I].mean(axis=1)
    return math.exp(logs.mean()), math.exp(np.percentile(bm, 2.5)), math.exp(np.percentile(bm, 97.5))


def stratified_logrank(times_a, ev_a, times_b, ev_b, strata_a, strata_b):
    """Mantel-Haenszel log-rank of arm a vs b, stratified; returns (O-E for a, chi2, p)."""
    o_minus_e, var = 0.0, 0.0
    for s in set(strata_a):
        ta = [(t, e) for t, e, g in zip(times_a, ev_a, strata_a) if g == s]
        tb = [(t, e) for t, e, g in zip(times_b, ev_b, strata_b) if g == s]
        for t in sorted({t for t, e in ta + tb if e}):
            na = sum(1 for x, _ in ta if x >= t)
            nb = sum(1 for x, _ in tb if x >= t)
            da = sum(1 for x, e in ta if e and x == t)
            d = da + sum(1 for x, e in tb if e and x == t)
            n = na + nb
            if n < 2:
                continue
            o_minus_e += da - d * na / n
            var += d * (na / n) * (nb / n) * (n - d) / (n - 1)
    chi2 = o_minus_e ** 2 / var if var > 0 else float("nan")
    return o_minus_e, chi2, float(stats.chi2.sf(chi2, 1))


def km_median(times, events):
    s = 1.0
    pts = sorted(zip(times, events))
    n = len(pts)
    for i, (t, e) in enumerate(pts):
        if e:
            s *= 1 - 1 / (n - i)
            if s <= 0.5:
                return t
    return float("inf")


def comparisons(rows, runs, rng):
    out = []
    for hi, lo, label in PAIRS:
        for u in UNITS:
            sel = [r for r in rows if r[f"ratio_{hi}_over_{lo}_{u}"] != ""]
            logs = np.log([r[f"ratio_{hi}_over_{lo}_{u}"] for r in sel])
            gm, lo_ci, hi_ci = geomean_ci(logs, [r["group"] for r in sel], rng)
            out.append({"comparison": f"{hi}/{lo}", "factor": label, "unit": u, "N": len(sel),
                        "geomean_ert_ratio": round(gm, 3), "ci_lo": round(lo_ci, 3), "ci_hi": round(hi_ci, 3),
                        "wilcoxon_p": round(float(stats.wilcoxon(logs).pvalue), 4),
                        f"{hi}_better": int((logs < 0).sum()), f"{lo}_better": int((logs > 0).sum()),
                        "median_ratio": round(float(np.exp(np.median(logs))), 3)})
    return out


def survival(runs):
    """Per-run TTT (s), censored at 900 s; KM median per arm, stratified log-rank per pair."""
    data = {}
    for a in ARMS:
        rs = runs[a]
        data[a] = ([min(float(r["wall_time_s"]), BUDGET) if r["stop_reason"] == "target" else BUDGET for r in rs],
                   [r["stop_reason"] == "target" for r in rs],
                   [r["instance_sha256"] for r in rs],
                   [polishes(r) for r in rs])
    out = {"km_median_ttt_s": {a: km_median(data[a][0], data[a][1]) for a in ARMS},
           "km_median_polishes": {a: km_median(data[a][3], data[a][1]) for a in ARMS},
           "successes": {a: int(sum(data[a][1])) for a in ARMS},
           "logrank_stratified_by_instance": {}}
    for hi, lo, label in PAIRS:
        res = {}
        for unit, k in (("s", 0), ("polish", 3)):
            oe, chi2, p = stratified_logrank(data[hi][k], data[hi][1], data[lo][k], data[lo][1], data[hi][2], data[lo][2])
            res[unit] = {"O_minus_E_first_arm": round(oe, 2), "chi2": round(chi2, 3), "p": round(p, 4)}
        out["logrank_stratified_by_instance"][f"{hi}_vs_{lo}"] = res
    # Fisher exact on pooled success counts (ignores clustering by instance; descriptive only)
    out["fisher_pooled_success"] = {}
    for hi, lo, _ in PAIRS:
        sh, sl = out["successes"][hi], out["successes"][lo]
        out["fisher_pooled_success"][f"{hi}_vs_{lo}"] = round(float(stats.fisher_exact([[sh, 130 - sh], [sl, 130 - sl]]).pvalue), 4)
    return out


def decomposition(rows, rng):
    """Does JW's gain concentrate where memetic's gain over uniform is?"""
    out = {}
    for u in UNITS:
        a = np.log([r[f"ratio_jw_over_uni_{u}"] for r in rows])
        b = np.log([r[f"ratio_mem_over_uni_{u}"] for r in rows])
        c = np.log([r[f"ratio_mem_over_jw_{u}"] for r in rows])
        I = rng.integers(0, len(a), (B, len(a)))
        boot = [stats.spearmanr(a[i], b[i]).statistic for i in I[:2000]]
        out[u] = {"mean_log_mem_over_uni": round(float(b.mean()), 3),
                  "share_from_jw_init": round(float(a.mean() / b.mean()), 3) if b.mean() != 0 else None,
                  "share_from_ea": round(float(c.mean() / b.mean()), 3) if b.mean() != 0 else None,
                  "spearman_logratio_jw_uni_vs_mem_uni": round(float(stats.spearmanr(a, b).statistic), 3),
                  "spearman_ci_pct_2000": [round(float(np.nanpercentile(boot, 2.5)), 3),
                                           round(float(np.nanpercentile(boot, 97.5)), 3)]}
    return out


def rho_rc2(rows, rng):
    out = []
    for a in ARMS:
        for u in UNITS:
            pts = [(r["rc2_solve_s"], r[f"{a}_ert_{u}"]) for r in rows if r[f"{a}_ert_{u}"] != ""]
            x, y = np.array(pts).T
            I = rng.integers(0, len(x), (B, len(x)))
            boot = np.array([stats.spearmanr(x[i], y[i]).statistic for i in I[:2000]])
            rho = float(stats.spearmanr(x, y).statistic)
            se = math.sqrt((1 + rho * rho / 2) / (len(x) - 3))
            bw = (math.tanh(math.atanh(rho) - 1.96 * se), math.tanh(math.atanh(rho) + 1.96 * se))
            out.append({"arm": a, "config_id": CONFIG[a], "unit": u, "N": len(x),
                        "rho": round(rho, 3),
                        "ci_pct_plain_lo": round(float(np.nanpercentile(boot, 2.5)), 3),
                        "ci_pct_plain_hi": round(float(np.nanpercentile(boot, 97.5)), 3),
                        "ci_bonett_wright_lo": round(bw[0], 3), "ci_bonett_wright_hi": round(bw[1], 3)})
    return out


def write_csv(p, rows):
    keys = list(rows[0].keys())
    for r in rows[1:]:
        keys += [k for k in r if k not in keys]
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)
    runs = load_runs()
    rows = instance_table(runs)
    write_csv(OUT / "instance_table.csv", rows)
    comp = comparisons(rows, runs, rng)
    write_csv(OUT / "pairwise_ert_ratios.csv", comp)
    rho = rho_rc2(rows, rng)
    write_csv(OUT / "rho_rc2_vs_ert.csv", rho)
    summary = {"generated_by": "cluster_staging_maxsat/scripts/uuf_three_arm_ablation.py",
               "bootstrap": {"B": B, "rng_seed": RNG_SEED, "strata": "group"},
               "instances": len(rows), "runs_per_arm": 130, "configs": CONFIG,
               "survival": survival(runs), "decomposition": decomposition(rows, rng),
               "pairwise": comp}
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print(json.dumps({k: v for k, v in summary.items() if k != "pairwise"}, indent=1, default=float))
    for c in comp:
        print(c)
    for r in rho:
        print(r)


if __name__ == "__main__":
    main()
