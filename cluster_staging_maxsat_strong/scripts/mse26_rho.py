#!/usr/bin/env python3
"""The pre-registered ρ analysis on MSE 2026 (docs/current2/MSE26_RHO_PREREG.md, binding r4, text of f8a3354).

Workstation only. Written and tested on synthetic data before any batch 3c record
was read. Inputs:
  scripts/mse26_population.tsv            the population, targets, EvalMaxSAT roles (§2)
  scripts/manifest_mse26_<part>.tsv       + .tasks.csv sidecars; shards in --outdir
  data/raw/mse_results/mse26/*rawdata.csv every published solver run (x, §3, §4)
  results/mse26_census/mse26_census.tsv   n_vars, n_clauses (partial ρ, §4.6)
Outputs in --out (default results/mse26_rho/): summary.json (every analysis),
report.md (the tables), instances.csv (x, y and flags per instance).

    python3 scripts/mse26_rho.py --outdir results/mse26_memetic/tasks            # seeds 1-3
    python3 scripts/mse26_rho.py --outdir results/mse26_memetic/tasks --seeds 1,2,3,4,5 \\
        --manifest scripts/manifest_mse26_<seeds45 part>.tsv ...                 # D1, if triggered

Definitions (§3): a memetic run succeeds iff m2_results classifies it `success`
(process clock: cpu_to_target_s <= 1,800 s) and, for a shorter budget B, its
cpu_to_target_s <= B. ERT = (sum of the efforts) / (successes), efforts = the
successes' cpu_to_target_s and B per failure; no success -> inf. PAR2 = mean of
the efforts with 2B per failure. x = a solver's single published run: proved ->
CPU s, timeout -> inf (PAR2: 7,200 s), memout / crash / wrong -> excluded (PAR2:
7,200 s for EvalMaxSAT, §4.7). ρ = Spearman with midranks (inf ties share one
midrank); 95 % BCa bootstrap over instances, B = 10,000, seed 20261029.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Callable, Dict, List, Optional, Sequence

import numpy as np
from scipy.special import ndtr, ndtri
from scipy.stats import rankdata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import m2_results as m2  # noqa: E402

INF = math.inf
BUDGET = 1800.0
X_LIMIT = 3600.0
B_BOOT = 10_000
SEED = 20261029
D1_HALF_WIDTH = 0.15
X_BANDS = [(-INF, 1.0, "<=1"), (1.0, 30.0, "(1,30]"), (30.0, 300.0, "(30,300]"), (300.0, 3600.0, "(300,3600]"),
           (3600.0, INF, "inf")]
Y_BANDS = [(-INF, 10.0, "<=10"), (10.0, 300.0, "(10,300]"), (300.0, 5400.0, "(300,5400]"), (5400.0, INF, "inf")]
RAW = {"mse26-exact-unweighted": "mse26_exact_unweighted_rawdata.csv",
       "mse26-exact-weighted": "mse26_exact_weighted_rawdata.csv"}


# ----------------------------------------------------------------- measures (§3)
def solver_status(r: Dict[str, str], optimum: str) -> str:
    """One published run on a proven-optimum instance: proved | timeout | memout | crash | wrong."""
    if r["answer"] == "OPTIMUM FOUND":
        ok = r["verified"] == "1" and r["optval"] == optimum and float(r["cpu.time"]) <= X_LIMIT
        return "proved" if ok else "wrong"
    if r["timeout"] == "true":
        return "timeout"
    if r["memout"] == "true":
        return "memout"
    if r["answer"] == "UNSATISFIABLE":       # the instance has a proven optimum: a wrong answer
        return "wrong"
    return "crash"


def x_ert(status: str, cpu: float) -> Optional[float]:
    """Single-run ERT: proved -> CPU, timeout -> inf, other failures -> None (excluded)."""
    return cpu if status == "proved" else INF if status == "timeout" else None


def x_par2(status: str, cpu: float) -> float:
    return cpu if status == "proved" else 2.0 * X_LIMIT


def run_effort(run: Dict, budget: float, flip: bool = False) -> Optional[float]:
    """The run's time to the target if it succeeded within `budget`, else None."""
    if run["cls"] != "success" or run["cpu_to_target_s"] is None or run["cpu_to_target_s"] > budget:
        return None
    if flip and run["cpu_to_target_hit_s"] is not None:
        return run["cpu_to_target_hit_s"]
    return run["cpu_to_target_s"]


def y_ert(runs: Sequence[Dict], budget: float = BUDGET, flip: bool = False) -> float:
    eff = [run_effort(r, budget, flip) for r in runs]
    succ = [e for e in eff if e is not None]
    return (sum(succ) + budget * (len(eff) - len(succ))) / len(succ) if succ else INF


def y_par2(runs: Sequence[Dict], budget: float = BUDGET) -> float:
    eff = [run_effort(r, budget) for r in runs]
    return sum(e if e is not None else 2.0 * budget for e in eff) / len(eff)


# ----------------------------------------------------------------- statistics (§4)
def spearman(x: np.ndarray, y: np.ndarray) -> float:
    """Spearman ρ with midranks: Pearson correlation of the average ranks (inf ranks last)."""
    rx, ry = rankdata(x), rankdata(y)
    sx, sy = rx.std(), ry.std()
    if sx == 0 or sy == 0:
        return float("nan")
    return float(((rx - rx.mean()) * (ry - ry.mean())).mean() / (sx * sy))


def partial_spearman(x: np.ndarray, y: np.ndarray, covs: np.ndarray) -> float:
    """Spearman ρ of x and y after removing the linear effect of the covariates' ranks
    from both rank vectors (partial correlation on midranks)."""
    rx, ry = rankdata(x), rankdata(y)
    z = np.column_stack([np.ones(len(x))] + [rankdata(c) for c in covs.T])
    ex = rx - z @ np.linalg.lstsq(z, rx, rcond=None)[0]
    ey = ry - z @ np.linalg.lstsq(z, ry, rcond=None)[0]
    if ex.std() == 0 or ey.std() == 0:
        return float("nan")
    return float(np.corrcoef(ex, ey)[0, 1])


def bca(stat: Callable[[np.ndarray], float], n: int, strata: Optional[Sequence[str]] = None,
        n_boot: int = B_BOOT, seed: int = SEED, level: float = 0.95) -> Dict:
    """95 % BCa bootstrap CI of stat(idx) over instances (Efron 1987): bias correction z0
    from the bootstrap distribution, acceleration a from the jackknife. With `strata`,
    each resample draws within each stratum (family-stratified bootstrap, §4.5)."""
    rng = np.random.default_rng(seed)
    all_idx = np.arange(n)
    theta = stat(all_idx)
    if strata is None:
        draws = (rng.integers(0, n, n) for _ in range(n_boot))
    else:
        groups = defaultdict(list)
        for i, s in enumerate(strata):
            groups[s].append(i)
        groups = [np.array(g) for _, g in sorted(groups.items())]
        draws = (np.concatenate([g[rng.integers(0, len(g), len(g))] for g in groups]) for _ in range(n_boot))
    boot = np.array([stat(idx) for idx in draws])
    boot = boot[~np.isnan(boot)]
    if math.isnan(theta) or len(boot) < 0.9 * n_boot:
        return {"rho": theta, "lo": None, "hi": None, "n_boot_valid": int(len(boot))}
    prop = (np.sum(boot < theta) + 0.5 * np.sum(boot == theta)) / len(boot)
    z0 = ndtri(min(max(prop, 1e-12), 1 - 1e-12))
    jack = np.array([stat(np.delete(all_idx, i)) for i in range(n)])
    jack = jack[~np.isnan(jack)]
    d = jack.mean() - jack
    den = 6.0 * (np.sum(d ** 2) ** 1.5)
    a = float(np.sum(d ** 3) / den) if den > 0 else 0.0
    alpha = (1 - level) / 2
    out = {}
    for name, z in (("lo", ndtri(alpha)), ("hi", ndtri(1 - alpha))):
        q = ndtr(z0 + (z0 + z) / (1 - a * (z0 + z)))
        out[name] = float(np.quantile(boot, q))
    return {"rho": theta, **out, "z0": float(z0), "a": a, "n_boot_valid": int(len(boot))}


def rho_ci(x: Sequence[float], y: Sequence[float], strata=None, covs=None, n_boot: int = B_BOOT) -> Dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = len(x)
    if n < 4:
        return {"n": n, "rho": None, "lo": None, "hi": None}
    if covs is None:
        stat = lambda idx: spearman(x[idx], y[idx])
    else:
        c = np.asarray(covs, float)
        stat = lambda idx: partial_spearman(x[idx], y[idx], c[idx])
    r = bca(stat, n, strata, n_boot)
    r["n"] = n
    r["half_width"] = (r["hi"] - r["lo"]) / 2 if r.get("lo") is not None else None
    r["x_inf"] = int(np.sum(np.isinf(x) & ~np.isinf(y)))
    r["y_inf"] = int(np.sum(np.isinf(y) & ~np.isinf(x)))
    r["both_inf"] = int(np.sum(np.isinf(x) & np.isinf(y)))
    return r


def interpret(r: Dict) -> str:
    """§7."""
    if r.get("lo") is None:
        return "not computable"
    if r["lo"] > 0:
        return "positive association"
    if r["hi"] < 0:
        return "negative association"
    if r["lo"] > -0.3 and r["hi"] < 0.3:
        return "at most weak monotone association"
    return "inconclusive at this N"


# ----------------------------------------------------------------- data
def load_population(path: str) -> Dict[str, Dict[str, str]]:
    with open(path, newline="") as f:
        return {r["hash"]: r for r in csv.DictReader(f, delimiter="\t")}


def load_published(pub_dir: str) -> Dict[str, Dict[str, Dict[str, str]]]:
    """{hash: {solver: row}} over both tracks."""
    out = defaultdict(dict)
    for fn in RAW.values():
        with open(os.path.join(pub_dir, fn), newline="") as f:
            for r in csv.DictReader(f):
                out[r["instance"][:-len(".wcnf")]][r["solvername"]] = r
    return out


def load_runs(manifests: Sequence[str], outdir: str, seeds: Sequence[int]) -> Dict[str, Dict[int, Dict]]:
    """{hash: {seed: run}} for the chosen seeds; class by m2_results.classify."""
    runs = defaultdict(dict)
    for man in manifests:
        for t in m2.load_tasks(man):
            seed = int(t["solver_seed"])
            if seed not in seeds:
                continue
            r = m2.read_shard(os.path.join(outdir, f"{t['job_id']}.jsonl"))
            cls, _ = m2.classify(t, r)
            r = r or {}
            runs[t["hash"]][seed] = {"cls": cls, "cpu_to_target_s": r.get("cpu_to_target_s"),
                                     "cpu_to_target_hit_s": r.get("cpu_to_target_hit_s"),
                                     "calls_to_target": r.get("calls_to_target")}
    return runs


def load_sizes(census: str) -> Dict[str, tuple]:
    with open(census, newline="") as f:
        return {r["hash"]: (int(r["n_vars"]), int(r["n_clauses"])) for r in csv.DictReader(f, delimiter="\t")}


def band(v: float, bands) -> str:
    for lo, hi, name in bands:
        if lo < v <= hi:
            return name
    return bands[-1][2]


# ----------------------------------------------------------------- the analysis
def analyse(pop, pub, runs, sizes, seeds: Sequence[int], n_boot: int = B_BOOT) -> Dict:
    seeds = sorted(seeds)
    out: Dict = {"prereg": "docs/current2/MSE26_RHO_PREREG.md r4 (f8a3354)", "seeds": seeds, "n_boot": n_boot}
    proven = [h for h, p in pop.items() if p["target_kind"] == "proven"]
    complete, incomplete = {}, {}
    for h in proven:
        rs = runs.get(h, {})
        ok = all(s in rs and rs[s]["cls"] in ("success",) + m2.FINAL_FAILURES for s in seeds)
        (complete if ok else incomplete)[h] = [rs[s] for s in seeds] if ok else sorted(
            (s, rs[s]["cls"]) if s in rs else (s, "no record") for s in seeds)
    out["incomplete"] = {h: v for h, v in sorted(incomplete.items())}

    def ems(h):
        r = pub[h]["EvalMaxSAT"]
        return solver_status(r, pop[h]["optimal_cost"]), float(r["cpu.time"]), float(r["wall.time"])

    rows = []
    for h in sorted(proven):
        st, cpu, wall = ems(h)
        p = pop[h]
        row = {"hash": h, "set": p["set"], "family": p["family"], "ems_status": st,
               "primary": p["primary"] == "1", "window": p["window"] == "1", "complete": h in complete,
               "x": x_ert(st, cpu), "x_wall": (wall if st == "proved" else INF if st == "timeout" else None),
               "x_par2": x_par2(st, cpu)}
        if h in complete:
            rs = complete[h]
            row.update(y=y_ert(rs), y_flip=y_ert(rs, flip=True), y_900=y_ert(rs, 900.0), y_par2=y_par2(rs),
                       successes=sum(run_effort(r, BUDGET) is not None for r in rs),
                       floor_runs=sum(run_effort(r, BUDGET) is not None and (r["calls_to_target"] or 0) <= 1
                                      for r in rs), runs=len(rs))
        if row["primary"] != (st in ("proved", "timeout")):
            raise SystemExit(f"FATAL: {h}: population.tsv primary={p['primary']} but EvalMaxSAT is {st}")
        rows.append(row)
    out["rows"] = rows
    prim = [r for r in rows if r["primary"] and r["complete"]]
    out["population"] = {
        "proven_optimum": len(proven), "primary": sum(r["primary"] for r in rows),
        "primary_complete": len(prim), "excluded_ems": dict(Counter(r["ems_status"] for r in rows if not r["primary"])),
        "incomplete": len(incomplete)}

    def ci(sel, xk, yk, **kw):
        sel = [r for r in sel if r.get(xk) is not None and r.get(yk) is not None]
        return rho_ci([r[xk] for r in sel], [r[yk] for r in sel], n_boot=n_boot, **kw)

    a = {}
    a["primary"] = ci(prim, "x", "y")
    a["primary"]["interpretation"] = interpret(a["primary"])
    a["primary"]["d1_seeds45_triggered"] = (a["primary"]["half_width"] is not None
                                            and a["primary"]["half_width"] > D1_HALF_WIDTH)
    s = {}
    s["1_window_uncensored"] = ci([r for r in prim if r["window"] and math.isfinite(r["y"])], "x", "y")
    s["2_x_wall"] = ci(prim, "x_wall", "y")
    s["3_flip_level"] = ci(prim, "x", "y_flip")
    s["4_budget_900"] = ci(prim, "x", "y_900")
    s["5_family_stratified"] = ci(prim, "x", "y", strata=[r["family"] for r in prim if r["x"] is not None])
    covs = [[math.log(sizes[r["hash"]][0]), math.log(sizes[r["hash"]][1])] for r in prim]
    s["6_partial_size"] = ci(prim, "x", "y", covs=covs)
    s["7_par2_all_proven"] = ci([r for r in rows if r["complete"]], "x_par2", "y_par2")
    for k in s:
        s[k]["interpretation"] = interpret(s[k])
    a["sensitivity"] = s

    # per published solver (§4): x = that solver's single-run ERT, on the proven instances of its track
    per = {}
    by_track = defaultdict(list)
    for r in rows:
        if r["complete"]:
            by_track[r["set"]].append(r)
    solvers = defaultdict(set)
    for r in rows:
        for sv in pub[r["hash"]]:
            solvers[sv].add(r["set"])
    for sv in sorted(solvers):
        res = {}
        for track in sorted(solvers[sv]) + (["pooled"] if len(solvers[sv]) > 1 else []):
            sel = [r for r in rows if r["complete"] and (track == "pooled" or r["set"] == track)
                   and sv in pub[r["hash"]]]
            xs, ys, excl = [], [], Counter()
            for r in sel:
                pr = pub[r["hash"]][sv]
                st = solver_status(pr, pop[r["hash"]]["optimal_cost"])
                v = x_ert(st, float(pr["cpu.time"]))
                if v is None:
                    excl[st] += 1
                    continue
                xs.append(v)
                ys.append(r["y"])
            res[track] = rho_ci(xs, ys, n_boot=n_boot)
            res[track]["excluded"] = dict(excl)
        per[sv] = res
    a["per_solver"] = per

    a["per_track"] = {t: ci([r for r in prim if r["set"] == t], "x", "y") for t in sorted(RAW)}
    fam = Counter(r["family"] for r in prim)
    a["per_family"] = {f: ci([r for r in prim if r["family"] == f], "x", "y")
                       for f, n in sorted(fam.items()) if n >= 10}
    out["analyses"] = a

    # complementarity (§6)
    c = {}
    two = Counter((math.isfinite(r["x"]), math.isfinite(r["y"])) for r in prim)
    c["2x2"] = {"ems_proved_memetic_reached": two[(True, True)], "ems_proved_memetic_not": two[(True, False)],
                "ems_not_memetic_reached": two[(False, True)], "ems_not_memetic_not": two[(False, False)]}
    c["off_diagonal_by_family"] = {
        "ems_proved_memetic_not": dict(Counter(r["family"] for r in prim if math.isfinite(r["x"]) and not math.isfinite(r["y"]))),
        "ems_not_memetic_reached": dict(Counter(r["family"] for r in prim if not math.isfinite(r["x"]) and math.isfinite(r["y"])))}
    cmap = {}
    for t in sorted(RAW):
        cell = Counter((band(r["x"], X_BANDS), band(r["y"], Y_BANDS)) for r in prim if r["set"] == t)
        cmap[t] = {f"{xb}|{yb}": cell[(xb, yb)] for _, _, xb in X_BANDS for _, _, yb in Y_BANDS}
    c["map"] = cmap
    fl = defaultdict(lambda: [0, 0])
    for r in prim:
        b = band(r["x"], X_BANDS)
        fl[b][0] += r["floor_runs"]
        fl[b][1] += r["runs"]
    c["floor_share"] = {b: {"floor_runs": v[0], "runs": v[1], "share": round(v[0] / v[1], 4) if v[1] else None}
                        for b, v in fl.items()}
    out["complementarity"] = c
    return out


# ----------------------------------------------------------------- output
def fmt(r: Dict) -> str:
    if r.get("rho") is None:
        return f"N {r.get('n')}: not computable"
    ci_ = f"[{r['lo']:+.3f}, {r['hi']:+.3f}]" if r.get("lo") is not None else "[CI n/a]"
    cens = f"; ∞ on x {r['x_inf']}, y {r['y_inf']}, both {r['both_inf']}" if "x_inf" in r else ""
    return f"ρ = {r['rho']:+.3f} {ci_}, N {r['n']}{cens}"


def report(res: Dict) -> str:
    a, p = res["analyses"], res["population"]
    L = ["# ρ on MSE 2026: pre-registered analysis", "",
         f"Pre-registration: {res['prereg']}. Seeds {res['seeds']}, bootstrap B = {res['n_boot']}, seed {SEED}.", "",
         "## Population", "", "```", json.dumps(p, indent=1), "```", "",
         f"Incomplete instances (excluded, §2): {len(res['incomplete'])}", "",
         "## Primary", "", f"- {fmt(a['primary'])}", f"- {a['primary']['interpretation']}",
         f"- D1 (seeds 4–5) triggered: {a['primary']['d1_seeds45_triggered']}", "", "## Sensitivity", ""]
    L += [f"- {k}: {fmt(v)} — {v['interpretation']}" for k, v in a["sensitivity"].items()]
    L += ["", "## Per track", ""] + [f"- {k}: {fmt(v)}" for k, v in a["per_track"].items()]
    L += ["", "## Per family (≥ 10)", ""] + [f"- {k}: {fmt(v)}" for k, v in a["per_family"].items()]
    L += ["", "## Per published solver", ""]
    for sv, res_ in a["per_solver"].items():
        for t, v in res_.items():
            L.append(f"- {sv} / {t}: {fmt(v)}; excluded {v['excluded']}")
    c = res["complementarity"]
    L += ["", "## Complementarity", "", "```", json.dumps({k: c[k] for k in ("2x2", "off_diagonal_by_family",
                                                                              "floor_share")}, indent=1), "```"]
    for t, m in c["map"].items():
        L += ["", f"Map, {t} (rows x, columns y):", "",
              "| x \\ y | " + " | ".join(n for _, _, n in Y_BANDS) + " |", "|---" * (len(Y_BANDS) + 1) + "|"]
        for _, _, xb in X_BANDS:
            L.append(f"| {xb} | " + " | ".join(str(m[f'{xb}|{yb}']) for _, _, yb in Y_BANDS) + " |")
    return "\n".join(L) + "\n"


def jsonable(o):
    if isinstance(o, float) and math.isinf(o):
        return "inf"
    if isinstance(o, dict):
        return {k: jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [jsonable(v) for v in o]
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    return o


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outdir", required=True, help="shard directory (results/mse26_memetic/tasks)")
    ap.add_argument("--manifest", action="append", default=None,
                    help="manifest(s); default every scripts/manifest_mse26_*.tsv")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--population", default=os.path.join(ROOT, "scripts", "mse26_population.tsv"))
    ap.add_argument("--published", default=os.path.join(REPO, "data", "raw", "mse_results", "mse26"))
    ap.add_argument("--census", default=os.path.join(ROOT, "results", "mse26_census", "mse26_census.tsv"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "mse26_rho"))
    ap.add_argument("--n-boot", type=int, default=B_BOOT)
    a = ap.parse_args(argv)
    mans = a.manifest or sorted(glob.glob(os.path.join(ROOT, "scripts", "manifest_mse26_*.tsv")))
    seeds = [int(s) for s in a.seeds.split(",")]
    res = analyse(load_population(a.population), load_published(a.published),
                  load_runs(mans, a.outdir, seeds), load_sizes(a.census), seeds, a.n_boot)
    os.makedirs(a.out, exist_ok=True)
    rows = res.pop("rows")
    with open(os.path.join(a.out, "instances.csv"), "w", newline="") as f:
        cols = ["hash", "set", "family", "ems_status", "primary", "window", "complete", "x", "x_wall", "x_par2",
                "y", "y_flip", "y_900", "y_par2", "successes", "floor_runs", "runs"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(jsonable(rows))
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(jsonable(res), f, indent=1)
    with open(os.path.join(a.out, "report.md"), "w") as f:
        f.write(report(res))
    pr = res["analyses"]["primary"]
    print(f"primary: {fmt(pr)} — {pr['interpretation']}; D1 triggered: {pr['d1_seeds45_triggered']}")
    print(f"incomplete instances: {len(res['incomplete'])}; wrote {a.out}/summary.json, report.md, instances.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
