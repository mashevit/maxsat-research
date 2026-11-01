#!/usr/bin/env python3
"""Memetic (batch 3c) vs Aperture (MSE 2026 anytime tracks) on the shared instances.

Not pre-registered (user request 2026-11-01). Aperture (Nadel, Slonimski, Strichman,
Technion) won 4 of the 6 MSE 2026 anytime tracks. Its published per-instance costs at
60 / 300 / 1707 s are in data/raw/mse_results/mse26/anytime/ (from results.zip,
Zenodo 21358014, md5 checked).

Shared instances = anytime-track instances that are also among the 947 instances of
results/mse26_rho_r3_fail/instances.csv (the exact-track instances with a published
optimum that batch 3c ran).

Costs:
  Aperture: optval of a run with answer SATISFIABLE / OPTIMUM FOUND and verified == 1,
            else infinity. Variants: unweighted KBG, GBG, IBI; weighted KBG, KBI, GBG.
  memetic:  per seed, best_cost of the last record when status ok and no hard clause is
            violated, else infinity (budget 1,800 s process CPU; the run stops early only
            at the published optimum, so a non-optimal best_cost is the cost after the
            full budget). At 60 / 300 s only "optimum reached by t" (cpu_to_target_hit_s
            <= t) is known; the memetic records no cost trajectory.

    python3 scripts/mse26_vs_aperture.py           # prints the summary, writes the TSV
"""
import csv
import glob
import json
import math
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "..", "data", "raw", "mse_results", "mse26")
TRACKS = ("ANYTIME-UW", "ANYTIME-W")
LIMITS = (60, 300, 1707)
SEEDS = (1, 2, 3)
INF = math.inf


def load_aperture():
    ap, variants = {}, defaultdict(set)
    for tr in TRACKS:
        for t in LIMITS:
            with open(os.path.join(DATA, "anytime", f"{tr}_{t}_rawdata.csv"), newline="") as f:
                for r in csv.DictReader(f):
                    if not r["solvername"].startswith("Aperture"):
                        continue
                    ok = (r["optval"] not in ("NA", "") and r["verified"] == "1"
                          and r["answer"] in ("SATISFIABLE", "OPTIMUM FOUND"))
                    ap[(tr, t, r["solvername"], r["instance"].split(".")[0])] = float(r["optval"]) if ok else INF
                    variants[tr].add(r["solvername"])
    return ap, {k: sorted(v) for k, v in variants.items()}


def load_memetic():
    mem = defaultdict(dict)
    for p in glob.glob(os.path.join(ROOT, "results", "mse26_memetic", "tasks", "*.jsonl")):
        lines = open(p).read().splitlines()
        if lines:
            d = json.loads(lines[-1])
            mem[os.path.basename(p).split("_")[1]][d["seed"]] = d
    return mem


def m_cost(d):
    if not d or d.get("status") != "ok" or d.get("best_cost") is None or d.get("hard_violations"):
        return INF
    return float(d["best_cost"])


def m_hit(d):
    if not d or d.get("status") != "ok" or not d.get("target_reached"):
        return INF
    return float(d.get("cpu_to_target_hit_s") or d.get("time_to_target_hit_s"))


def main():
    with open(os.path.join(DATA, "benchmark-metadata.csv"), newline="") as f:
        meta = {r["hash"]: r for r in csv.DictReader(f)}
    with open(os.path.join(ROOT, "results", "mse26_rho_r3_fail", "instances.csv"), newline="") as f:
        ran = {r["hash"] for r in csv.DictReader(f)}
    ap, variants = load_aperture()
    mem = load_memetic()
    rows = []
    for tr in TRACKS:
        for h in sorted({k[3] for k in ap if k[0] == tr} & ran):
            opt = float(meta[h]["optimal_cost"])
            r = {"track": tr, "hash": h, "family": meta[h]["family"], "opt": opt}
            for s in SEEDS:
                d = mem.get(h, {}).get(s)
                r[f"m_cost_s{s}"], r[f"m_hit_s{s}"] = m_cost(d), m_hit(d)
            for t in LIMITS:
                for v in variants[tr]:
                    r[f"{v}@{t}"] = ap[(tr, t, v, h)]
                r[f"Aperture-best@{t}"] = min(ap[(tr, t, v, h)] for v in variants[tr])
            rows.append(r)
    assert all(r[k] >= r["opt"] for r in rows for k in r if "@" in k), "Aperture below the optimum"
    assert all(r[f"m_cost_s{s}"] >= r["opt"] for r in rows for s in SEEDS), "memetic below the optimum"

    print(f"shared instances: {len(rows)} {dict(Counter(r['track'] for r in rows))}")
    for t in LIMITS:
        for ref in ("Aperture-KBG", "Aperture-best"):
            c, better = Counter(), []
            for r in rows:
                a, opt = r[f"{ref}@{t}"], r["opt"]
                if t == 1707:
                    m = [r[f"m_cost_s{s}"] for s in SEEDS]
                else:
                    m = [opt if r[f"m_hit_s{s}"] <= t else INF for s in SEEDS]
                nb = sum(x < a for x in m)
                c["Aperture optimum"] += a <= opt
                c["memetic optimum, >= 1 seed"] += any(x <= opt for x in m)
                c["memetic optimum, all 3 seeds"] += all(x <= opt for x in m)
                for k in (1, 2, 3):
                    c[f"memetic better, >= {k} seeds"] += nb >= k
                if t == 1707:
                    c["Aperture better than all 3 seeds"] += all(x > a for x in m)
                    c["Aperture better than >= 2 seeds"] += sum(x > a for x in m) >= 2
                if nb:
                    better.append(f"    {r['track'][8:]:2} {r['hash'][:8]} {r['family']}: opt {opt:.0f}, "
                                  f"{ref} {a:.0f}, memetic {[f'{x:.0f}' for x in m]}, "
                                  f"hit s {[round(r[f'm_hit_s{s}'], 1) for s in SEEDS]}, better seeds {nb}")
            print(f"\n== {t} s, {ref}: " + "; ".join(f"{k} {v}" for k, v in c.items()))
            print("\n".join(better))
    out = os.path.join(ROOT, "results", "mse26_vs_aperture.tsv")
    with open(out, "w", newline="") as f:
        fields = list(dict.fromkeys(k for r in rows for k in r))
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", restval="")
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
