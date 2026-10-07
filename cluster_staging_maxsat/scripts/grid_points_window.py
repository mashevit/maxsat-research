#!/usr/bin/env python3
"""RC2 grid points per (k, n, c*) under the agreed window 30 s < t <= 900 s.

Record: docs/current/GRID_POINTS_WINDOW_30_900.md (repo). Nothing here uses rho.

INPUTS (staging-root relative)

    results/profile_calib_{a,b}_all.jsonl            generated pure-soft rows (cap 900)
    results/profile_uuf250/*.jsonl                   SATLIB uuf250, 100 instances (cap 900)
    results/profile_uuf/*.jsonl                      SATLIB uuf50..uuf250, 10 per size (cap 600);
                                                     its 10 uuf250 rows duplicate profile_uuf250
                                                     by basename and are skipped
    results/corpus_freeze_prep/candidate_instances.csv   a35_q2 per eligible generated instance

OUTPUT

    results/corpus_freeze_prep/grid_points_30_900.csv    one row per (k, n, c*, source)
    stdout: the same table, censored lower bounds per (k, n, alpha), per-row slopes

Certified = completed and final_cost == cost_lower_bound. Eligible = certified and
30 < solve_s <= 900. Slope = OLS of log10(solve_s) on c* over certified rows with
solve_s > 1 ms, pooled over sources; capacity = log10(900/30) / slope, the number of
consecutive integer c* values one window width holds.
"""
import argparse, collections, csv, glob, json, math, re, statistics as st

LO, HI = 30.0, 900.0


def load(root):
    q2 = {r["instance"]: r["a35_q2"] for r in
          csv.DictReader(open(f"{root}/results/corpus_freeze_prep/candidate_instances.csv"))}
    rows = []
    for f in ("profile_calib_a_all.jsonl", "profile_calib_b_all.jsonl"):
        for line in open(f"{root}/results/{f}"):
            r = json.loads(line); p = r["profile"]
            m = re.search(r"v(\d+)_k(\d)_sr([\d.]+)_", r["instance"])
            cert = bool(p["completed"]) and p["final_cost"] == p["cost_lower_bound"]
            base = r["instance"].split("/")[-1]
            rows.append(dict(src="calib", k=int(m[2]), n=int(m[1]), alpha=float(m[3]),
                             cert=cert, t=p["solve_s"], cstar=p["final_cost"] if cert else None,
                             lb=p["cost_lower_bound"], q2=q2.get(base, "")))
    seen = set()
    for d in ("profile_uuf250", "profile_uuf"):
        for f in sorted(glob.glob(f"{root}/results/{d}/*.jsonl")):
            for line in open(f):
                r = json.loads(line); p = r["profile"]
                base = r["instance"].split("/")[-1]
                if base in seen:
                    continue
                seen.add(base)
                cert = bool(p.get("completed")) and p["final_cost"] == p["cost_lower_bound"]
                rows.append(dict(src="satlib", k=3, n=int(re.match(r"uuf(\d+)", base)[1]),
                                 alpha=4.26, cert=cert, t=p["solve_s"],
                                 cstar=p["final_cost"] if cert else None,
                                 lb=p["cost_lower_bound"], q2=""))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="staging root (cluster_staging_maxsat)")
    a = ap.parse_args()
    rows = load(a.root)

    pts = collections.defaultdict(list)
    for x in rows:
        if x["cert"]:
            pts[(x["k"], x["n"], x["cstar"], x["src"])].append(x)
    out = []
    for key in sorted(pts):
        xs = pts[key]; t = sorted(x["t"] for x in xs)
        el = [x for x in xs if LO < x["t"] <= HI]
        q = [x["q2"] for x in el if x["q2"] != ""]
        out.append(dict(k=key[0], n=key[1], cstar=key[2], source=key[3], certified=len(xs),
                        below=sum(v <= LO for v in t), eligible=len(el),
                        t_min=round(t[0], 2), t_med=round(st.median(t), 2), t_max=round(t[-1], 2),
                        alphas=" ".join(f"{v:g}" for v in sorted({x["alpha"] for x in xs})),
                        q2_a35=f"{sum(v == '1' for v in q)}/{len(q)}" if q else ""))
    with open(f"{a.root}/results/corpus_freeze_prep/grid_points_30_900.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    for r in out:
        print(*r.values(), sep="\t")

    print("\ncensored lower bounds per (k, n, alpha, source)")
    cen = collections.defaultdict(list)
    for x in rows:
        if not x["cert"]:
            cen[(x["k"], x["n"], x["alpha"], x["src"])].append(x["lb"])
    for key in sorted(cen):
        print(key, sorted(cen[key]))

    print("\nper-row slope and window capacity")
    by = collections.defaultdict(list)
    for x in rows:
        if x["cert"] and x["t"] > 0.001:
            by[(x["k"], x["n"])].append((x["cstar"], math.log10(x["t"])))
    for key in sorted(by):
        p = by[key]
        if len({c for c, _ in p}) < 2:
            continue
        mx = st.mean(c for c, _ in p); my = st.mean(v for _, v in p)
        sl = sum((c - mx) * (v - my) for c, v in p) / sum((c - mx) ** 2 for c, _ in p)
        print(key, f"N={len(p)} slope={sl:.3f} x{10 ** sl:.1f}/c* capacity={math.log10(HI / LO) / sl:.2f}")


if __name__ == "__main__":
    main()
