#!/usr/bin/env python3
"""Read out the EvalMaxSAT MSE 2023/2024 sample against best-known costs and RC2.

Workstation only (after the rsync back). docs/current/MSE_EVALMAXSAT_3600.md §6.

    python3 scripts/evalmaxsat_mse_readout.py                       # sample s1
    python3 scripts/evalmaxsat_mse_readout.py --outdir results/smoke_evalmaxsat_mse \
        --manifest scripts/manifest_evalmaxsat_mse_smoke.txt        # the smoke

Per task it classifies the row:
    opt=bk      proven optimum equal to the best-known cost
    opt<bk      proven optimum BELOW the best-known (the table was not optimal)
    opt>bk      impossible for a proven optimum: the best-known or our file is wrong -- investigate
    ub=bk       capped, verified incumbent equal to the best-known
    ub<bk       capped, verified incumbent below the best-known (a new best)
    ub>bk       capped, verified incumbent above the best-known (gap reported)
    no-ub       capped with no hard-feasible incumbent (EvalMaxSAT `s UNKNOWN`)
    unsat       hard clauses unsatisfiable (contradicts a finite best-known)
    error / unverified / missing
and checks every proven optimum against RC2's lower bound where one exists.

Writes results/<outdir name>_all.jsonl (rows + sidecar fields + class) and prints
tables per year and per family. Exit 1 if any row is missing, an error, fails
the model check, or contradicts the best-known or RC2.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def classify(r: dict, bk: int) -> str:
    st = r.get("status")
    if st == "optimal":
        if r.get("verified") is not True:
            return "unverified"
        o = r["opt_cost"]
        return "opt=bk" if o == bk else ("opt<bk" if o < bk else "opt>bk")
    if st == "timeout":
        if r.get("verified") is False:
            return "unverified"
        u = r.get("best_cost")
        if u is None:
            return "no-ub"
        return "ub=bk" if u == bk else ("ub<bk" if u < bk else "ub>bk")
    if st == "unsat":
        return "unsat"
    return "error"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outdir", default="results/evalmaxsat_mse_s1")
    ap.add_argument("--manifest", default="scripts/manifest_evalmaxsat_mse_s1.txt")
    ap.add_argument("--sidecar", default="scripts/manifest_evalmaxsat_mse_s1.tasks.csv",
                    help="frame CSV with best_known and RC2 evidence (rows are joined by instance path)")
    args = ap.parse_args()

    manifest = [l.strip() for l in open(args.manifest) if l.strip()]
    side = {r["instance"]: r for r in csv.DictReader(open(args.sidecar))}
    problems = []
    out_rows = []
    bins = Counter()
    for task, inst in enumerate(manifest, 1):
        meta = side.get(inst)
        if meta is None:
            problems.append(f"task {task}: {inst} not in sidecar")
            continue
        fn = os.path.join(args.outdir, f"task_{task}.jsonl")
        rows = [json.loads(l) for l in open(fn) if l.strip()] if os.path.exists(fn) else []
        envf = os.path.join(args.outdir, f"task_{task}.env.json")
        env = json.load(open(envf)) if os.path.exists(envf) else {}
        if env.get("bin_sha256"):
            bins[env["bin_sha256"]] += 1
        if not rows:
            out_rows.append(dict(task=task, instance=inst, cls="missing"))
            problems.append(f"task {task}: no row")
            continue
        r = rows[-1]
        bk = int(meta["best_known"])
        cls = classify(r, bk)
        rec = dict(task=task, year=meta["year"], family=meta["family"], instance=inst, best_known=bk,
                   rc2_status=meta["rc2_status"], rc2_cost_or_lb=meta["rc2_cost_or_lb"], cls=cls,
                   env=env, row=r)
        if cls in ("error", "unverified", "opt>bk", "unsat"):
            problems.append(f"task {task}: {cls}  {inst}  {r.get('note', '')}")
        lb = meta["rc2_cost_or_lb"]
        if r.get("status") == "optimal" and lb not in ("", None) and r["opt_cost"] < int(lb):
            problems.append(f"task {task}: optimum {r['opt_cost']} below RC2 bound {lb}")
        if r.get("stopped_by") == "sigkill":
            problems.append(f"task {task}: needed SIGKILL (incumbent lost)")
        out_rows.append(rec)

    out_path = args.outdir.rstrip("/") + "_all.jsonl"
    with open(out_path, "w") as f:
        for rec in out_rows:
            f.write(json.dumps(rec) + "\n")

    print(f"rows: {sum(1 for r in out_rows if r['cls'] != 'missing')}/{len(manifest)}   "
          f"binary sha256: {dict(bins) or 'n/a'}")
    by_year = defaultdict(Counter)
    for r in out_rows:
        by_year[r.get("year", "?")][r["cls"]] += 1
    order = ["opt=bk", "opt<bk", "opt>bk", "ub=bk", "ub<bk", "ub>bk", "no-ub", "unsat", "unverified", "error", "missing"]
    print("\n%-6s " % "year" + " ".join("%7s" % c for c in order))
    for y in sorted(by_year):
        print("%-6s " % y + " ".join("%7d" % by_year[y][c] for c in order))

    print("\nper task (time s, cost, best-known, RC2):")
    for r in out_rows:
        if r["cls"] == "missing":
            print(f"  {r['task']:>3}  missing  {r['instance']}")
            continue
        row = r["row"]
        cost = row.get("opt_cost") if row.get("status") == "optimal" else row.get("best_cost")
        print(f"  {r['task']:>3} {r['year']} {r['family'][:24]:24s} {r['cls']:10s} t={row.get('time_s', 0):7.1f} "
              f"cost={cost!s:>12} bk={r['best_known']:>12} rc2={r['rc2_status'] or '-'}:{r['rc2_cost_or_lb'] or '-'}")

    print(f"\nwrote {out_path}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  " + p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
