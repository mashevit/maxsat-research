#!/usr/bin/env python3
"""Build the RC2 cap-3600 re-run manifest: every censored instance, one hour cap.

SELECTION (fixed before any cap-3600 row exists)

    every instance under data/ that has at least one RC2 row in results/ and
    NO completed RC2 row at any cap, i.e. it hit the cap every time it ran,

    excluding data/mse16/, data/raw/ (MSE 2024) and data/more_data/.

Instances that never had an RC2 row (calib_c, the 16 satisfiable jnh) are not
"censored" and are not included. Every RC2 row under results/ is read (per-task
JSONL files; the *_all/*_env aggregates are skipped as duplicates), so the
batch a censored row came from does not matter.

DEDUPE. data/unsat_uuf_diff/uuf250-0{2,4,8}.cnf are the same formulas as
data/unsat250_1000c/uuf250-0{2,4,8}.cnf (same clause lines; only the comment
block differs). Instances are keyed by a hash of their non-comment,
non-header lines; of a duplicate group the first path in sort order of
PREFERRED_ROOTS is kept and the others are listed in the sidecar's
`duplicates` column.

OUTPUTS (scripts/)

    manifest_rc2_cap3600.txt        one root-relative path per line (task N == line N),
                                    read by rc2_profile_array.sbatch
    manifest_rc2_cap3600.sha256     `sha256sum -c` list, checked by submit_rc2_profile.sh
    manifest_rc2_cap3600.tasks.csv  task, instance, source, prior batch/cap/status/LB, duplicates

    python3 scripts/make_rc2_cap3600_manifest.py          # write
    python3 scripts/make_rc2_cap3600_manifest.py --check  # rebuild, diff, exit 3 on drift

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
from typing import Dict, List, Tuple

EXCLUDE_PREFIXES = ("data/mse16/", "data/raw/", "data/more_data/")
# Duplicate groups keep the copy under the earliest root in this list.
PREFERRED_ROOTS = ("data/satlib_bench/", "data/unsat250_1000c/", "data/generated/",
                   "data/unsat_uuf_diff/")
STEM = "manifest_rc2_cap3600"
TASK_COLS = ["task", "instance", "source", "prior_batches", "prior_max_cap_s",
             "prior_status", "prior_cost_lower_bound", "duplicates"]


def source_of(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[1:3]) if parts[1] == "generated" else parts[1]


def formula_key(path: str) -> str:
    """Hash of the clause lines only (comments, `p` header and blank lines dropped)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for line in f:
            s = line.strip()
            if not s or s[:1] in (b"c", b"p", b"%"):
                continue
            h.update(b" ".join(s.split()) + b"\n")
    return h.hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_rc2_rows(results_dir: str) -> Dict[str, List[Tuple[str, dict]]]:
    rows: Dict[str, List[Tuple[str, dict]]] = {}
    for fp in sorted(glob.glob(os.path.join(results_dir, "**", "*.jsonl"), recursive=True)):
        base = os.path.basename(fp)
        if base.endswith(("_all.jsonl", "_env.jsonl")) or ".env." in base:
            continue
        batch = os.path.relpath(os.path.dirname(fp), results_dir)
        with open(fp) as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(r, dict) or "instance" not in r:
                    continue
                p = r.get("profile")
                if not isinstance(p, dict) or p.get("solver") != "rc2":
                    continue
                rows.setdefault(r["instance"], []).append((batch, p))
    return rows


def build(results_dir: str) -> Tuple[str, str, str]:
    rows = read_rc2_rows(results_dir)
    censored = []
    for inst, rs in rows.items():
        if inst.startswith(EXCLUDE_PREFIXES):
            continue
        if any(p.get("completed") for _, p in rs):
            continue
        if not os.path.isfile(inst):
            sys.exit(f"FATAL: censored instance not on disk: {inst}")
        censored.append(inst)

    def pref(path: str) -> Tuple[int, str]:
        for i, root in enumerate(PREFERRED_ROOTS):
            if path.startswith(root):
                return (i, path)
        return (len(PREFERRED_ROOTS), path)

    groups: Dict[str, List[str]] = {}
    for inst in censored:
        groups.setdefault(formula_key(inst), []).append(inst)
    kept = []
    for members in groups.values():
        members.sort(key=pref)
        kept.append((members[0], members[1:]))
    kept.sort(key=lambda km: km[0])

    txt, sha, tasks = io.StringIO(), io.StringIO(), io.StringIO()
    w = csv.DictWriter(tasks, fieldnames=TASK_COLS, lineterminator="\n")
    w.writeheader()
    for n, (inst, dups) in enumerate(kept, 1):
        rs = [x for m in [inst] + dups for x in rows[m]]
        lbs = [p.get("cost_lower_bound") for _, p in rs if p.get("cost_lower_bound") is not None]
        txt.write(inst + "\n")
        sha.write(f"{sha256_file(inst)}  {inst}\n")
        w.writerow({
            "task": n, "instance": inst, "source": source_of(inst),
            "prior_batches": ";".join(sorted({b for b, _ in rs})),
            "prior_max_cap_s": max(p.get("cap_s") or 0 for _, p in rs),
            "prior_status": ";".join(sorted({str(p.get("status")) for _, p in rs})),
            "prior_cost_lower_bound": max(lbs) if lbs else "",
            "duplicates": ";".join(dups),
        })
    return txt.getvalue(), sha.getvalue(), tasks.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results-dir", default="results")
    ap.add_argument("--check", action="store_true",
                    help="rebuild and compare with the files on disk; exit 3 on any difference")
    args = ap.parse_args()
    if not os.path.isdir("data") or not os.path.isdir("scripts"):
        sys.exit("FATAL: run from cluster_staging_maxsat/ (data/ and scripts/ not found)")

    outputs = dict(zip((f"scripts/{STEM}.txt", f"scripts/{STEM}.sha256",
                        f"scripts/{STEM}.tasks.csv"), build(args.results_dir)))
    if args.check:
        drift = [p for p, s in outputs.items()
                 if not os.path.isfile(p) or open(p).read() != s]
        for p in drift:
            print(f"DRIFT: {p}", file=sys.stderr)
        print("check: OK" if not drift else f"check: {len(drift)} file(s) differ")
        return 3 if drift else 0
    for p, s in outputs.items():
        with open(p, "w") as f:
            f.write(s)
    n = outputs[f"scripts/{STEM}.txt"].count("\n")
    by_src: Dict[str, int] = {}
    for row in csv.DictReader(io.StringIO(outputs[f"scripts/{STEM}.tasks.csv"])):
        by_src[row["source"]] = by_src.get(row["source"], 0) + 1
    print(f"wrote {STEM}.{{txt,sha256,tasks.csv}}: {n} tasks  {by_src}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
