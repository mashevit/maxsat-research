#!/usr/bin/env python3
"""Build the EvalMaxSAT 3600 s sample manifest over MSE 2023 / MSE 2024 (sample s1).

FRAME (fixed before any EvalMaxSAT row on these instances exists)

    data/raw/mse_2024/mse23-uw-small/   75 unweighted instances (MSE 2023)
    data/raw/mse_2024/mse24-small/      91 weighted instances   (MSE 2024)

    minus instances whose best-known cost is -1 ("not known") in their own
    year's table (bestknown_mse23.csv / bestknown_mse24.csv): 2 + 3.
    That leaves 73 + 88.

    Best-known costs are looked up ONLY in the instance's own year's table. The
    two raw tables share 17 + 19 instance names with different costs, and for
    several MSE 2023 files the other table's value is below RC2's proven lower
    bound on our file (e.g. min-fill myciel5: other table 56, RC2 LB 97), so a
    cross-year lookup by name is wrong for these files
    (docs/current/MSE_EVALMAXSAT_3600.md §2).

SAMPLE s1: 30 per year, stratified by benchmark family.

    1. every family gets one slot (17 families in MSE 2023, 20 in MSE 2024);
    2. the remaining 13 / 10 slots go to the families in proportion to (size - 1),
       by largest remainder, ties broken by family name;
    3. within a family, instances are taken in the order of
       sha256(f"{SEED}:{file name}"), so the draw is fixed by SEED alone and does
       not depend on directory listing order.

    Tasks 1-30 are MSE 2023, tasks 31-60 MSE 2024. Every frame instance not in
    s1 is listed in the sidecar with sample = "rest" (the frame of later samples).

OUTPUTS (scripts/)

    manifest_evalmaxsat_mse_s1.txt        one root-relative path per line (task N == line N)
    manifest_evalmaxsat_mse_s1.sha256     `sha256sum -c` list, checked by submit_evalmaxsat_mse.sh
    manifest_evalmaxsat_mse_s1.tasks.csv  task, year, family, instance, best_known, sizes,
                                          RC2 evidence (MSE 2023), sample (s1 | rest | excluded)

    python3 scripts/make_evalmaxsat_mse_manifest.py          # write
    python3 scripts/make_evalmaxsat_mse_manifest.py --check  # rebuild, diff, exit 3 on drift

Run from cluster_staging_maxsat/ (the tree root).
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import io
import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

SEED = 20261011
PER_YEAR = 30
STEM = "manifest_evalmaxsat_mse_s1"
YEARS = (
    ("mse23", "data/raw/mse_2024/mse23-uw-small", "data/raw/mse_2024/bestknown_mse23.csv"),
    ("mse24", "data/raw/mse_2024/mse24-small", "data/raw/mse_2024/bestknown_mse24.csv"),
)
# Family names that themselves contain the separator '-'.
MULTIWORD = ("judgment-aggregation", "inconsistency-measurement", "decision-tree", "gen-hyper-tw",
             "optimizing-BDDs", "logic-synthesis", "extension-enforcement", "min-fill",
             "quantum-circuit")
RC2_GLOBS = ("results/profile/mse23_full_arr_task_*.jsonl", "results/profile_cap1800/*.jsonl")
COLS = ["task", "year", "family", "instance", "best_known", "nvars", "ncls", "nhards", "nsofts",
        "weighted", "rc2_max_cap_s", "rc2_status", "rc2_cost_or_lb", "sample"]


def family_of(name: str) -> str:
    if "_wt-" in name:
        fam = name.split("_wt-")[0]
    else:
        fam = next((m for m in MULTIWORD if name.startswith(m + "-") or name.startswith(m + "_")),
                   name.split("-")[0])
    for suffix in ("_mse20", "_new"):
        if fam.endswith(suffix):
            fam = fam[: -len(suffix)]
    return fam


def header_stats(path: str) -> Dict[str, object]:
    """The JSON block MSE puts in the comment header (nvars, ncls, nhards, nsofts, weights)."""
    buf: List[str] = []
    on = False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("c"):
                break
            t = line[1:].strip()
            if t == "{":
                on = True
            if on:
                buf.append(t)
            if on and t == "}":
                break
    j = json.loads("".join(buf))
    w = j["soft_wt_stats"]
    return dict(nvars=j["nvars"], ncls=j["ncls"], nhards=j["nhards"], nsofts=j["nsofts"],
                weighted=int(w["min"] != w["max"]))


def rc2_evidence() -> Dict[str, Dict[str, object]]:
    """Per file name: the longest-cap RC2 row (status, final cost or LB)."""
    best: Dict[str, Dict[str, object]] = {}
    for pat in RC2_GLOBS:
        for fn in sorted(glob.glob(pat)):
            with open(fn) as f:
                for line in f:
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    p = r["profile"]
                    k = os.path.basename(r["instance"])
                    cap = float(p["cap_s"])
                    if k not in best or cap > best[k]["rc2_max_cap_s"]:
                        best[k] = dict(rc2_max_cap_s=cap,
                                       rc2_status="optimal" if p["completed"] else "censored",
                                       rc2_cost_or_lb=p["final_cost"] if p["completed"] else p["cost_lower_bound"])
    return best


def rank_key(name: str) -> str:
    return hashlib.sha256(f"{SEED}:{name}".encode()).hexdigest()


def allocate(sizes: Dict[str, int], slots: int) -> Dict[str, int]:
    fams = sorted(sizes)
    if slots < len(fams):
        raise SystemExit(f"{slots} slots < {len(fams)} families")
    alloc = {f: 1 for f in fams}
    extra = slots - len(fams)
    weights = {f: sizes[f] - 1 for f in fams}
    total = sum(weights.values())
    if extra and total:
        quota = {f: extra * weights[f] / total for f in fams}
        for f in fams:
            alloc[f] += int(quota[f])
        left = extra - sum(int(q) for q in quota.values())
        for f in sorted(fams, key=lambda f: (-(quota[f] - int(quota[f])), f))[:left]:
            alloc[f] += 1
    for f in fams:
        alloc[f] = min(alloc[f], sizes[f])
    if sum(alloc.values()) != slots:
        raise SystemExit(f"allocation {sum(alloc.values())} != {slots}")
    return alloc


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> Dict[str, str]:
    rc2 = rc2_evidence()
    rows: List[Dict[str, object]] = []
    manifest: List[str] = []
    for year, d, bk_csv in YEARS:
        bk = {r["instance"]: int(r["best_cost"]) for r in csv.DictReader(open(bk_csv))}
        files = sorted(os.listdir(d))
        missing = [f for f in files if f not in bk]
        if missing:
            raise SystemExit(f"{year}: no best-known for {missing[:3]}")
        by_fam: Dict[str, List[str]] = defaultdict(list)
        excluded = []
        for f in files:
            (excluded if bk[f] < 0 else by_fam[family_of(f)]).append(f)
        alloc = allocate({k: len(v) for k, v in by_fam.items()}, PER_YEAR)
        chosen = []
        for fam in sorted(by_fam):
            chosen += sorted(by_fam[fam], key=rank_key)[: alloc[fam]]
        chosen_set = set(chosen)
        for f in files:
            sample = "excluded" if f in excluded else ("s1" if f in chosen_set else "rest")
            path = f"{d}/{f}"
            row = dict(task="", year=year, family=family_of(f), instance=path, best_known=bk[f],
                       sample=sample, **header_stats(path))
            row.update(rc2.get(f, dict(rc2_max_cap_s="", rc2_status="", rc2_cost_or_lb="")))
            rows.append(row)
        manifest += [f"{d}/{f}" for f in sorted(chosen, key=lambda f: (family_of(f), f))]
    task = {p: i for i, p in enumerate(manifest, 1)}
    for r in rows:
        r["task"] = task.get(r["instance"], "")
    rows.sort(key=lambda r: (r["task"] == "", r["task"] if r["task"] != "" else 0, r["year"], r["instance"]))

    txt = "".join(p + "\n" for p in manifest)
    sha = "".join(f"{sha256_file(p)}  {p}\n" for p in manifest)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in COLS})
    return {f"scripts/{STEM}.txt": txt, f"scripts/{STEM}.sha256": sha, f"scripts/{STEM}.tasks.csv": out.getvalue()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="rebuild and compare with the files on disk; exit 3 on drift")
    args = ap.parse_args()
    outputs = build()
    if args.check:
        drift = [p for p, body in outputs.items() if not os.path.exists(p) or open(p).read() != body]
        for p in drift:
            print(f"DRIFT {p}", file=sys.stderr)
        print("check OK" if not drift else f"{len(drift)} file(s) drifted")
        return 3 if drift else 0
    for p, body in outputs.items():
        with open(p, "w") as f:
            f.write(body)
    n = outputs[f"scripts/{STEM}.txt"].count("\n")
    print(f"wrote {STEM}.{{txt,sha256,tasks.csv}}: {n} tasks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
