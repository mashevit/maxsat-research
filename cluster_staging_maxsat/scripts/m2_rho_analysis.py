#!/usr/bin/env python3
"""M2 full pool -> per-instance table and rho(RC2, memetic) read-out.

Exploratory (CORPUS_CALIBRATION_GOALS.md §5.2): calibration rows never enter a
reported rho. Conventions follow §4.2/§4.4/§5.2 of that document:

- sampling unit = instance; the 3 solver seeds are collapsed first;
- ERT = sum over seeds of the effort spent / successes (a failed seed is
  charged its full spend, ~900 s); undefined at 0 successes;
- Spearman rho with average ranks; primary CI = bootstrap stratified by cell
  (BCa + percentile, B = 10 000), checks = plain instance bootstrap and
  Fisher z with the Bonett-Wright SE sqrt((1 + rho^2/2)/(N - 3));
- partial rho = Pearson correlation of the residuals of rank(x) and rank(y)
  after OLS on [log n, alpha, log(1 + c*)] (and a variant that adds k);
- 0-success instances: excluded in the primary version, entered as top-tied
  ERT in the sensitivity version; the count is printed with every rho.

Run from cluster_staging_maxsat/:
    python3 scripts/m2_rho_analysis.py
Writes results/m2_full_p40/analysis/.
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
FULL_TASKS = ROOT / "results/m2_full_p40/agg/tasks.csv"
PILOT_TASKS = ROOT / "results/m2_pilot/agg/tasks.csv"
OUT = ROOT / "results/m2_full_p40/analysis"
RC2_FILES = [ROOT / "results/profile_calib_a_all.jsonl", ROOT / "results/profile_calib_b_all.jsonl"]
GEN_MANIFESTS = [ROOT / "data/generated/calib_a/manifest.jsonl", ROOT / "data/generated/calib_b/manifest.jsonl"]
T2_MEMETIC = ROOT / "results/tier2_memetic_all.jsonl"
T2_MULTISTART = ROOT / "results/tier2_local_multistart_all.jsonl"
T2_INDEX = ROOT / "results/tier2_memetic_instance_index.csv"

BUDGET = 900.0
B = 10_000
RNG_SEED = 20261004
ARMS = ["p40_ls0p5_clip", "p40_ls3p5"]
ARM_SHORT = {"p40_ls0p5_clip": "a05", "p40_ls3p5": "a35"}
CHILDREN_PER_GEN = 38  # pop 40, ceil(0.05*40) = 2 elites


def read_csv(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def read_jsonl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def fnum(x):
    return None if x in (None, "", "None") else float(x)


# ---------------------------------------------------------------- statistics
def rankdata(a):
    return stats.rankdata(a, method="average")


def spearman(x, y):
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return float("nan")
    return float(stats.spearmanr(x, y).statistic)


def partial_rank_corr(x, y, Z):
    rx, ry = rankdata(x), rankdata(y)
    Z1 = np.column_stack([np.ones(len(x)), Z])
    ex = rx - Z1 @ np.linalg.lstsq(Z1, rx, rcond=None)[0]
    ey = ry - Z1 @ np.linalg.lstsq(Z1, ry, rcond=None)[0]
    if np.std(ex) == 0 or np.std(ey) == 0:
        return float("nan")
    return float(np.corrcoef(ex, ey)[0, 1])


def bonett_wright_ci(r, n):
    if n <= 3 or not np.isfinite(r) or abs(r) >= 1:
        return (float("nan"), float("nan"))
    se = math.sqrt((1 + r * r / 2) / (n - 3))
    z = math.atanh(r)
    return (math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se))


def spearman_rows(x, y, I):
    """Spearman rho of x[I[b]] vs y[I[b]] for every row b of the index matrix I."""
    rx = stats.rankdata(x[I], axis=1)
    ry = stats.rankdata(y[I], axis=1)
    rx = rx - rx.mean(axis=1, keepdims=True)
    ry = ry - ry.mean(axis=1, keepdims=True)
    den = np.sqrt((rx * rx).sum(axis=1) * (ry * ry).sum(axis=1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, (rx * ry).sum(axis=1) / np.where(den > 0, den, 1), np.nan)


def loop_rows(stat):
    return lambda I: np.array([stat(row) for row in I])


def bootstrap(stat_rows, n, strata, rng, B=B):
    """stat_rows maps a (reps x n) index matrix to reps statistics.

    Returns (theta_hat, bca_lo, bca_hi, pct_lo, pct_hi, plain_lo, plain_hi, n_nan),
    where BCa and pct use the cell-stratified resample and plain is the
    unstratified instance bootstrap.
    """
    idx_all = np.arange(n)
    theta = float(stat_rows(idx_all[None, :])[0])
    groups = defaultdict(list)
    for i, s in zip(idx_all, strata):
        groups[s].append(i)
    groups = [np.array(g) for g in groups.values()]
    Is = np.concatenate([g[rng.integers(0, len(g), (B, len(g)))] for g in groups], axis=1)
    Ip = rng.integers(0, n, (B, n))
    strat = stat_rows(Is)
    plain = stat_rows(Ip)
    ok = np.isfinite(strat)
    n_nan = int((~ok).sum())
    sv = strat[ok]
    pct = (np.percentile(sv, 2.5), np.percentile(sv, 97.5)) if len(sv) else (np.nan, np.nan)
    pv = plain[np.isfinite(plain)]
    plain_ci = (np.percentile(pv, 2.5), np.percentile(pv, 97.5)) if len(pv) else (np.nan, np.nan)
    # BCa: bias from the stratified replicates, acceleration from the jackknife
    bca = (np.nan, np.nan)
    if np.isfinite(theta) and len(sv) > 100:
        prop = np.clip((sv < theta).mean() + 0.5 * (sv == theta).mean(), 1e-6, 1 - 1e-6)
        z0 = stats.norm.ppf(prop)
        J = np.array([np.delete(idx_all, j) for j in range(n)])
        jack = stat_rows(J)
        jack = jack[np.isfinite(jack)]
        d = jack.mean() - jack
        denom = 6 * (np.sum(d ** 2) ** 1.5)
        a = np.sum(d ** 3) / denom if denom > 0 else 0.0
        qs = []
        for zq in (stats.norm.ppf(0.025), stats.norm.ppf(0.975)):
            q = stats.norm.cdf(z0 + (z0 + zq) / (1 - a * (z0 + zq)))
            qs.append(np.percentile(sv, 100 * q))
        bca = tuple(qs)
    return theta, bca[0], bca[1], pct[0], pct[1], plain_ci[0], plain_ci[1], n_nan


# ---------------------------------------------------------------- assembly
def load_meta():
    meta = {}
    for p in GEN_MANIFESTS:
        for r in read_jsonl(p):
            meta[r["instance"]] = r
    return meta


def load_rc2():
    rc2 = {}
    for p in RC2_FILES:
        for r in read_jsonl(p):
            rc2[r["instance"]] = r  # last row per instance wins (resume rule)
    return rc2


def per_instance(tasks, meta, rc2):
    by = defaultdict(list)
    for t in tasks:
        by[t["instance"]].append(t)
    rows = []
    for inst, ts in sorted(by.items(), key=lambda kv: int(kv[1][0]["pop_idx"])):
        m = meta[inst]
        r = rc2[inst]["profile"]
        assert r["completed"] and int(r["final_cost"]) == int(ts[0]["oracle_cost"])
        cstar = int(r["final_cost"])
        row = {
            "pop_idx": int(ts[0]["pop_idx"]),
            "instance": inst,
            "instance_sha256": ts[0]["instance_sha256"],
            "batch": m["batch"],
            "cell_id": m["cell_id"],
            "family": m["family"],
            "k": m["k"],
            "n": m["n"],
            "alpha": m["alpha"],
            "m": m["m"],
            "gen_seed": m["seed"],
            "c_star": cstar,
            "rc2_solve_s": float(r["solve_s"]),
            "rc2_s_per_oracle_call": float(r["solve_s"]) / (cstar + 1),
            "rc2_tier": ts[0]["rc2_tier"],
            "analysis_group": ts[0]["analysis_group"],
        }
        pooled_succ = 0
        for arm in ARMS:
            a = ARM_SHORT[arm]
            at = sorted((t for t in ts if t["arm"] == arm), key=lambda t: int(t["solver_seed"]))
            assert len(at) == 3, (inst, arm)
            succ = [t["cls"] == "success" for t in at]
            ns = sum(succ)
            pooled_succ += ns
            wall = [min(float(t["wall_time_s"]), BUDGET) if s else BUDGET
                    for t, s in zip(at, succ)]
            ttt = [float(t["time_to_target_s"]) if s else math.inf for t, s in zip(at, succ)]
            ch = [int(t["children"]) for t in at]
            fl = [int(t["total_flips"]) for t in at]
            row[f"{a}_succ"] = ns
            row[f"{a}_ttt_s1"], row[f"{a}_ttt_s2"], row[f"{a}_ttt_s3"] = [
                (round(x, 3) if math.isfinite(x) else "") for x in ttt]
            row[f"{a}_children_s1"], row[f"{a}_children_s2"], row[f"{a}_children_s3"] = ch
            mt = sorted(ttt)[1]
            row[f"{a}_median_ttt_s"] = round(mt, 3) if math.isfinite(mt) else ""
            row[f"{a}_ert_s"] = round(sum(wall) / ns, 3) if ns else ""
            row[f"{a}_ert_children"] = round(sum(ch) / ns, 3) if ns else ""
            row[f"{a}_ert_flips"] = round(sum(fl) / ns, 1) if ns else ""
            row[f"{a}_mean_flips_per_call"] = round(sum(fl) / max(1, sum(ch)), 1)
            row[f"{a}_max_children"] = max(ch)
            row[f"{a}_max_generations"] = max(int(t["ea_generations"]) for t in at)
            # pre-registered Q2 "non-trivial": median TTT >= 5 % of budget, or < 100 % success
            row[f"{a}_nontrivial_q2"] = int(ns < 3 or mt >= 0.05 * BUDGET)
        row["pooled_succ_of_6"] = pooled_succ
        row["all6_first_child"] = int(all(row[f"{ARM_SHORT[arm]}_children_s{s}"] == 1
                                         and row[f"{ARM_SHORT[arm]}_succ"] == 3
                                         for arm in ARMS for s in (1, 2, 3)))
        row["any_run_beyond_gen1"] = int(any(row[f"{ARM_SHORT[arm]}_max_children"] > CHILDREN_PER_GEN
                                             for arm in ARMS))
        rows.append(row)
    return rows


# ---------------------------------------------------------------- rho table
def rho_rows(rows, rng):
    out = []
    xs_def = {
        "rc2_solve_s": lambda r: r["rc2_solve_s"],
        "c_star": lambda r: r["c_star"],
        "rc2_s_per_oracle_call": lambda r: r["rc2_s_per_oracle_call"],
    }
    ys_def = {}
    for arm in ARMS:
        a = ARM_SHORT[arm]
        for metric in ("ert_s", "ert_children", "ert_flips", "median_ttt_s"):
            ys_def[f"{a}_{metric}"] = (a, metric)
        ys_def[f"{a}_succ"] = (a, "succ")
    subsets = {
        "pooled": lambda r: True,
        "k2": lambda r: r["k"] == 2,
        "k3": lambda r: r["k"] == 3,
        "tier2_group": lambda r: r["analysis_group"] == "tier2",
    }

    def yval(r, a, metric, top_tie):
        if metric == "succ":
            return float(r[f"{a}_succ"])
        v = r[f"{a}_{metric}"]
        if v == "":
            return math.inf if top_tie else None
        return float(v)

    for sub_name, sub_f in subsets.items():
        S = [r for r in rows if sub_f(r)]
        for xname, xf in xs_def.items():
            for yname, (a, metric) in ys_def.items():
                for version in (("primary", False), ("zero_succ_top_tied", True)):
                    if metric == "succ" and version[1]:
                        continue
                    pts = [(xf(r), yval(r, a, metric, version[1]), r) for r in S]
                    excluded = sum(1 for p in pts if p[1] is None)
                    if version[1] and not any(r[f"{a}_succ"] == 0 for r in S):
                        continue  # no 0-success instance: identical to primary
                    pts = [p for p in pts if p[1] is not None]
                    if len(pts) < 5:
                        continue
                    x = np.array([p[0] for p in pts], float)
                    y = np.array([p[1] for p in pts], float)
                    y = np.where(np.isinf(y), np.nanmax(y[np.isfinite(y)]) * 10 + 1, y)
                    Z = np.array([[math.log(p[2]["n"]), p[2]["alpha"], math.log1p(p[2]["c_star"])]
                                  for p in pts])
                    Zk = np.column_stack([Z, [p[2]["k"] for p in pts]])
                    cells = [p[2]["cell_id"] for p in pts]
                    th, bl, bh, pl, ph, ql, qh, nn = bootstrap(lambda I: spearman_rows(x, y, I), len(pts), cells, rng)
                    bw = bonett_wright_ci(th, len(pts))
                    pr = partial_rank_corr(x, y, Z) if xname == "rc2_solve_s" else float("nan")
                    prk = partial_rank_corr(x, y, Zk) if (xname == "rc2_solve_s" and sub_name == "pooled") else float("nan")
                    pr_ci = (float("nan"), float("nan"))
                    if xname == "rc2_solve_s" and yname.endswith(("ert_s", "ert_flips")):
                        _, pbl, pbh, ppl, pph, *_ = bootstrap(
                            loop_rows(lambda i: partial_rank_corr(x[i], y[i], Z[i])), len(pts), cells, rng, B=2000)
                        pr_ci = (ppl, pph)
                    n_distinct_y = len(set(y.tolist()))
                    out.append({
                        "subset": sub_name, "x": xname, "y": yname, "version": version[0],
                        "N": len(pts), "excluded_zero_succ": excluded, "n_distinct_y": n_distinct_y,
                        "rho": round(th, 3),
                        "ci_bca_strat_lo": round(bl, 3), "ci_bca_strat_hi": round(bh, 3),
                        "ci_pct_strat_lo": round(pl, 3), "ci_pct_strat_hi": round(ph, 3),
                        "ci_pct_plain_lo": round(ql, 3), "ci_pct_plain_hi": round(qh, 3),
                        "ci_bonett_wright_lo": round(bw[0], 3), "ci_bonett_wright_hi": round(bw[1], 3),
                        "p_value_spearman": (round(float(stats.spearmanr(x, y).pvalue), 4)
                                             if np.isfinite(th) else ""),
                        "partial_rho_logn_alpha_logc": round(pr, 3),
                        "partial_rho_pct_strat_lo": round(pr_ci[0], 3),
                        "partial_rho_pct_strat_hi": round(pr_ci[1], 3),
                        "partial_rho_plus_k": round(prk, 3),
                        "bootstrap_nan_reps": nn,
                    })
    return out


def covariate_rhos(rows):
    out = []
    covs = {"n": "n", "alpha": "alpha", "m": "m", "c_star": "c_star", "k": "k",
            "rc2_solve_s": "rc2_solve_s"}
    targets = {"rc2_solve_s": "rc2_solve_s", "rc2_s_per_oracle_call": "rc2_s_per_oracle_call"}
    for arm in ARMS:
        a = ARM_SHORT[arm]
        targets[f"{a}_ert_s"] = f"{a}_ert_s"
        targets[f"{a}_ert_children"] = f"{a}_ert_children"
        targets[f"{a}_succ"] = f"{a}_succ"
    for sub_name, sub_f in {"pooled": lambda r: True, "k2": lambda r: r["k"] == 2,
                            "k3": lambda r: r["k"] == 3}.items():
        S = [r for r in rows if sub_f(r)]
        for tn, tk in targets.items():
            for cn, ck in covs.items():
                if cn == tn:
                    continue
                pts = [(float(r[ck]), float(r[tk])) for r in S if r[tk] != ""]
                x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
                rho = spearman(x, y)
                out.append({"subset": sub_name, "target": tn, "covariate": cn, "N": len(pts),
                            "rho": round(rho, 3) if np.isfinite(rho) else ""})
    return out


# ---------------------------------------------------------------- extras
def rc2_population(meta, rc2, selected):
    out = []
    for inst, m in sorted(meta.items()):
        p = rc2[inst]["profile"]
        out.append({
            "instance": inst, "batch": m["batch"], "cell_id": m["cell_id"], "k": m["k"], "n": m["n"],
            "alpha": m["alpha"], "m": m["m"], "gen_seed": m["seed"], "rc2_status": p["status"],
            "rc2_completed": int(bool(p["completed"])), "rc2_solve_s": p["solve_s"],
            "c_star": p["final_cost"] if p["completed"] else "",
            "rc2_lower_bound": p["cost_lower_bound"],
            "in_m2_full_pool": int(inst in selected),
        })
    return out


def tier2_uuf(rng):
    idx = {r["sha256"]: r for r in read_csv(T2_INDEX)}
    runs = read_jsonl(T2_MEMETIC) + read_jsonl(T2_MULTISTART)
    by = defaultdict(lambda: defaultdict(list))
    for r in runs:
        by[r["instance_sha256"]][r["config_id"]].append(r)
    rows = []
    for sha, cfgs in by.items():
        ix = idx[sha]
        row = {"instance": ix["instance"], "group": ix["group"], "n_vars": None, "c_star": int(ix["rc2_final_cost"]),
               "rc2_solve_s": float(ix["rc2_solve_s"]), "rc2_cap_s": float(ix["rc2_cap_s"])}
        for cid, rs in sorted(cfgs.items()):
            row["n_vars"] = rs[0]["n_vars"]
            ok = [r["stop_reason"] == "target" for r in rs]
            ns = sum(ok)
            wall = [min(float(r["wall_time_s"]), 900.0) if o else 900.0 for r, o in zip(rs, ok)]
            row[f"{cid}_runs"] = len(rs)
            row[f"{cid}_succ"] = ns
            row[f"{cid}_ert_s"] = round(sum(wall) / ns, 2) if ns else ""
        rows.append(row)
    rows.sort(key=lambda r: r["rc2_solve_s"])
    rho = []
    for cid in ("memetic_deeppolish", "local_multistart_deeppolish", "memetic_base", "memetic_pop150"):
        for top in (False, True):
            pts = [(r["rc2_solve_s"], (float(r[f"{cid}_ert_s"]) if r[f"{cid}_ert_s"] != "" else (1e9 if top else None)), r)
                   for r in rows if f"{cid}_ert_s" in r]
            exc = sum(1 for p in pts if p[1] is None)
            pts = [p for p in pts if p[1] is not None]
            x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts])
            th, bl, bh, pl, ph, ql, qh, _ = bootstrap(lambda I: spearman_rows(x, y, I), len(pts),
                                                      [p[2]["group"] for p in pts], rng)
            bw = bonett_wright_ci(th, len(pts))
            rho.append({"config_id": cid, "version": "zero_succ_top_tied" if top else "primary",
                        "N": len(pts), "excluded_zero_succ": exc, "rho": round(th, 3),
                        "ci_pct_strat_lo": round(pl, 3), "ci_pct_strat_hi": round(ph, 3),
                        "ci_bonett_wright_lo": round(bw[0], 3), "ci_bonett_wright_hi": round(bw[1], 3)})
    return rows, rho


def determinism_check(full_tasks):
    """Pilot p40_ls2p5 vs full p40_ls3p5, same instance and solver seed.

    Where the 12,500-flip limit ends every call before 2.5 s, the two configs
    are the same search; identical children/flips/assignment means the 3.5 s
    arm is reproducible across hosts. Also pilot unclipped 0.5 s control vs the
    full clipped 0.5 s control (time-bounded calls: not expected identical).
    """
    pilot = read_csv(PILOT_TASKS)
    shard = lambda d, j: read_jsonl(ROOT / d / f"{j}.jsonl")[-1]
    full = {(t["instance"], t["solver_seed"], t["arm"]): t for t in full_tasks}
    out = []
    for t in pilot:
        pair = {"p40_ls2p5": "p40_ls3p5", "p40_ls0p5": "p40_ls0p5_clip"}.get(t["arm"])
        if pair is None:
            continue
        f = full[(t["instance"], t["solver_seed"], pair)]
        ps = shard("results/m2_pilot/tasks", t["job_id"])
        fs = shard("results/m2_full_p40/tasks", f["job_id"])
        out.append({
            "instance": t["instance"], "m": t["m"], "solver_seed": t["solver_seed"],
            "pilot_arm": t["arm"], "full_arm": pair,
            "pilot_cls": t["cls"], "full_cls": f["cls"],
            "pilot_ttt": t["time_to_target_s"], "full_ttt": f["time_to_target_s"],
            "pilot_children": t["children"], "full_children": f["children"],
            "pilot_flips": t["total_flips"], "full_flips": f["total_flips"],
            "same_children_flips": int(t["children"] == f["children"] and t["total_flips"] == f["total_flips"]),
            "same_best_assignment": int(ps.get("best_assignment_hash") == fs.get("best_assignment_hash")),
        })
    return out



def within_row(rows, rng):
    """rho after removing (k, n) row: x and y are replaced by their within-row
    mid-ranks scaled to (0, 1), then correlated pooled. Rows with < 3 instances
    or a constant y contribute nothing (all ties -> 0.5). Plus per-row rho."""
    out = []
    keyf = lambda r: (r["k"], r["n"])
    rows_by = defaultdict(list)
    for r in rows:
        rows_by[keyf(r)].append(r)
    for a in ARM_SHORT.values():
        for metric in ("ert_s", "ert_children"):
            for (k, n), S in sorted(rows_by.items()):
                x = np.array([r["rc2_solve_s"] for r in S]); y = np.array([float(r[f"{a}_{metric}"]) for r in S])
                out.append({"scope": f"row k{k} n{n}", "y": f"{a}_{metric}", "N": len(S),
                            "n_distinct_y": len(set(y.tolist())),
                            "alpha_range": f"{min(r['alpha'] for r in S)}-{max(r['alpha'] for r in S)}",
                            "c_star_range": f"{min(r['c_star'] for r in S)}-{max(r['c_star'] for r in S)}",
                            "rho": round(spearman(x, y), 3) if len(S) >= 4 else ""})
            for fam in ("pooled", "k2", "k3"):
                S = [r for r in rows if fam == "pooled" or r["k"] == int(fam[1])]
                S = [r for r in S if len(rows_by[keyf(r)]) >= 3]
                X = np.empty(len(S)); Y = np.empty(len(S))
                for i, r in enumerate(S):
                    grp = rows_by[keyf(r)]
                    gx = np.array([g["rc2_solve_s"] for g in grp]); gy = np.array([float(g[f"{a}_{metric}"]) for g in grp])
                    j = grp.index(r)
                    X[i] = (rankdata(gx)[j] - 0.5) / len(grp)
                    Y[i] = (rankdata(gy)[j] - 0.5) / len(grp)
                strata = [keyf(r) for r in S]
                pear = lambda I: np.array([np.corrcoef(X[i], Y[i])[0, 1] if np.std(Y[i]) > 0 and np.std(X[i]) > 0 else np.nan for i in I])
                th, bl, bh, pl, ph, ql, qh, _ = bootstrap(pear, len(S), strata, rng, B=4000)
                bw = bonett_wright_ci(th, len(S))
                out.append({"scope": f"within-row pooled {fam}", "y": f"{a}_{metric}", "N": len(S),
                            "n_distinct_y": "", "alpha_range": "", "c_star_range": "",
                            "rho": round(th, 3), "ci_pct_strat_lo": round(pl, 3), "ci_pct_strat_hi": round(ph, 3),
                            "ci_bonett_wright_lo": round(bw[0], 3), "ci_bonett_wright_hi": round(bw[1], 3)})
    return out


def reliability(rows, tasks):
    """How reproducible is the memetic hardness signal itself? Upper bound
    context for any rho against RC2 (RC2 itself was run once)."""
    out = {}
    a05 = np.array([float(r["a05_ert_s"]) for r in rows]); a35 = np.array([float(r["a35_ert_s"]) for r in rows])
    c05 = np.array([float(r["a05_ert_children"]) for r in rows]); c35 = np.array([float(r["a35_ert_children"]) for r in rows])
    out["rho_between_arms_ert_s"] = round(spearman(a05, a35), 3)
    out["rho_between_arms_ert_children"] = round(spearman(c05, c35), 3)
    for fam in (2, 3):
        m = np.array([r["k"] == fam for r in rows])
        out[f"rho_between_arms_ert_s_k{fam}"] = round(spearman(a05[m], a35[m]), 3)
    # seed-to-seed: per arm, children-to-target (fails -> top) of seed s vs seed t
    by = defaultdict(dict)
    for t in tasks:
        v = int(t["children"]) if t["cls"] == "success" else 10 ** 7
        by[(t["arm"], t["instance"])][int(t["solver_seed"])] = v
    for arm in ARMS:
        inst = sorted({i for (a, i) in by if a == arm})
        M = np.array([[by[(arm, i)][s] for s in (1, 2, 3)] for i in inst], float)
        pairs = [spearman(M[:, a], M[:, b]) for a, b in ((0, 1), (0, 2), (1, 2))]
        out[f"{ARM_SHORT[arm]}_seed_pair_rho_children_mean"] = round(float(np.mean(pairs)), 3)
        out[f"{ARM_SHORT[arm]}_seed_pair_rho_children"] = [round(p, 3) for p in pairs]
        # one-way random-effects ICC on log children (fails -> log of total children at budget)
        L = np.log(np.array([[int(next(t["children"] for t in tasks if t["arm"] == arm and t["instance"] == i
                                         and int(t["solver_seed"]) == s)) for s in (1, 2, 3)] for i in inst], float))
        k = 3; msb = k * np.var(L.mean(axis=1), ddof=1); msw = np.mean(np.var(L, axis=1, ddof=1))
        out[f"{ARM_SHORT[arm]}_icc1_log_children"] = round(float((msb - msw) / (msb + (k - 1) * msw)), 3)
    return out


def arm_comparison(rows, tasks):
    """Paired 0.5 s vs 3.5 s on instances where either arm needed more than
    one generation in some run, or failed at least once."""
    sel = [r for r in rows if r["any_run_beyond_gen1"] or r["pooled_succ_of_6"] < 6]
    out = []
    for r in sel:
        out.append({"pop_idx": r["pop_idx"], "k": r["k"], "n": r["n"], "alpha": r["alpha"], "m": r["m"],
                    "c_star": r["c_star"], "rc2_solve_s": r["rc2_solve_s"],
                    "a05_succ": r["a05_succ"], "a35_succ": r["a35_succ"],
                    "a05_ert_s": r["a05_ert_s"], "a35_ert_s": r["a35_ert_s"],
                    "ert_s_ratio_a35_over_a05": round(float(r["a35_ert_s"]) / float(r["a05_ert_s"]), 3),
                    "a05_ert_flips": r["a05_ert_flips"], "a35_ert_flips": r["a35_ert_flips"],
                    "ert_flips_ratio_a35_over_a05": round(float(r["a35_ert_flips"]) / float(r["a05_ert_flips"]), 3),
                    "a05_ttt_s1_s2_s3": ";".join(str(r[f"a05_ttt_s{s}"]) or "fail" for s in (1, 2, 3)), "a35_ttt_s1_s2_s3": ";".join(str(r[f"a35_ttt_s{s}"]) or "fail" for s in (1, 2, 3))})
    rt = np.log([o["ert_s_ratio_a35_over_a05"] for o in out]); rf = np.log([o["ert_flips_ratio_a35_over_a05"] for o in out])
    summ = {"instances": len(out),
            "geomean_ert_s_ratio": round(float(np.exp(rt.mean())), 3),
            "wilcoxon_p_ert_s": round(float(stats.wilcoxon(rt).pvalue), 4),
            "geomean_ert_flips_ratio": round(float(np.exp(rf.mean())), 3),
            "wilcoxon_p_ert_flips": round(float(stats.wilcoxon(rf).pvalue), 4),
            "a35_better_ert_s": int((rt < 0).sum()), "a05_better_ert_s": int((rt > 0).sum())}
    return out, summ


def write_csv(p, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    for r in rows[1:]:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RNG_SEED)
    tasks = read_csv(FULL_TASKS)
    meta, rc2 = load_meta(), load_rc2()
    rows = per_instance(tasks, meta, rc2)
    write_csv(OUT / "instance_table.csv", rows)
    rho = rho_rows(rows, rng)
    write_csv(OUT / "rho_table.csv", rho)
    write_csv(OUT / "covariate_rho.csv", covariate_rhos(rows))
    write_csv(OUT / "rc2_population_290.csv", rc2_population(meta, rc2, {r["instance"] for r in rows}))
    uuf_rows, uuf_rho = tier2_uuf(rng)
    write_csv(OUT / "uuf_tier2_instance_table.csv", uuf_rows)
    write_csv(OUT / "uuf_tier2_rho.csv", uuf_rho)
    write_csv(OUT / "within_row_rho.csv", within_row(rows, rng))
    rel = reliability(rows, tasks)
    arm_rows, arm_summ = arm_comparison(rows, tasks)
    write_csv(OUT / "arm_comparison_nontrivial.csv", arm_rows)
    det = determinism_check(tasks)
    write_csv(OUT / "pilot_vs_full_reproducibility.csv", det)

    def cnt(f):
        return sum(1 for r in rows if f(r))
    summary = {
        "generated_by": "cluster_staging_maxsat/scripts/m2_rho_analysis.py",
        "bootstrap": {"B": B, "rng_seed": RNG_SEED, "strata": "cell_id"},
        "instances": len(rows),
        "tasks": len(tasks),
        "by_family": {f"k{k}": cnt(lambda r, k=k: r["k"] == k) for k in (2, 3)},
        "by_group": {g: cnt(lambda r, g=g: r["analysis_group"] == g) for g in ("lower_ext", "tier2", "upper_ext")},
        "instances_with_any_failure": cnt(lambda r: r["pooled_succ_of_6"] < 6),
        "instances_with_zero_success_any_arm": {a: cnt(lambda r, a=a: r[f"{a}_succ"] == 0) for a in ARM_SHORT.values()},
        "instances_all6_runs_solved_by_first_child": cnt(lambda r: r["all6_first_child"] == 1),
        "instances_any_run_beyond_generation1": cnt(lambda r: r["any_run_beyond_gen1"] == 1),
        "nontrivial_q2_rule": {a: cnt(lambda r, a=a: r[f"{a}_nontrivial_q2"] == 1) for a in ARM_SHORT.values()},
        "reproducibility_flip_bound": {
            "pairs": len([d for d in det if d["full_arm"] == "p40_ls3p5"]),
            "identical_children_flips_assignment": len([d for d in det if d["full_arm"] == "p40_ls3p5"
                                                        and d["same_children_flips"] and d["same_best_assignment"]]),
        },
        "reproducibility_time_bound_0p5": {
            "pairs": len([d for d in det if d["full_arm"] == "p40_ls0p5_clip"]),
            "identical_children_flips": len([d for d in det if d["full_arm"] == "p40_ls0p5_clip"
                                             and d["same_children_flips"]]),
            "same_outcome_class": len([d for d in det if d["full_arm"] == "p40_ls0p5_clip"
                                       and d["pilot_cls"] == d["full_cls"]]),
            "same_best_assignment": len([d for d in det if d["full_arm"] == "p40_ls0p5_clip"
                                         and d["same_best_assignment"]]),
        },
        "reliability": rel,
        "arm_comparison_nontrivial": arm_summ,
        "headline_rho_rc2_vs_ert_s_pooled": [r for r in rho if r["subset"] == "pooled" and r["x"] == "rc2_solve_s"
                                             and r["y"].endswith("_ert_s")],
        "uuf_tier2_rho": uuf_rho,
    }
    with open(OUT / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print(json.dumps({k: v for k, v in summary.items() if not k.startswith(("headline", "uuf"))}, indent=1))


if __name__ == "__main__":
    main()
