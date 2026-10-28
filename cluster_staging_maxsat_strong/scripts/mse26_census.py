#!/usr/bin/env python3
"""MSE 2026 census: one instance per call, one TSV row (docs/current2/COMPILED_MEMETIC_PLAN.md §9).

Runs inside a Slurm task (scripts/mse26_census_array.sbatch), never on the login
node. Per instance, with the C parser (sat/compact.py):
  - the content sha256 (to compare with the unpack job's mse26_content.tsv);
  - n_vars, clauses, literals, hard / soft counts, soft weight sum, max clause
    length, weighted, the v3 neighbour-table bound and mode (full / lean);
  - the kernel screen (fraction of pure or 1+1 variables);
  - when the screen passes (>= 0.20) and the file is at most KERNEL_MAX_MIB:
    the gate itself (kernel decision, kernel size, gain, seconds, memory);
  - parse seconds and the process peak RSS after the parse and at the end.

    python3 scripts/mse26_census.py --set S --hash H --path data/raw/mse26/S/H.wcnf --out ROW.tsv
The header is COLUMNS; the row is written only when everything finished, so a
missing row means "rerun this file".
"""
from __future__ import annotations

import argparse
import hashlib
import os
import resource
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

KERNEL_MAX_MIB = 100.0      # the Python kernel needs ~33x the file: 100 MiB -> ~3.3 GB of the 8 GB task
GATE = {"preprocess": "kernel", "preprocess_gate": {"screen_min": 0.2, "gain_min": 0.2}}   # = auto.yaml

COLUMNS = ["set", "hash", "path", "sha256", "bytes", "n_vars", "n_clauses", "n_lits", "n_hard", "n_soft",
           "soft_w_sum", "soft_w_max", "max_len", "weighted", "nbrs_bound", "nbrs_mode", "screen_hit",
           "screen_occ", "screen_frac", "kernel_status", "kernel_n_vars", "kernel_n_clauses", "kernel_gain",
           "kernel_s", "parse_s", "rss_parse_mb", "rss_end_mb", "error"]


def rss_mb() -> float:
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0, 1)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def census(set_, hash_, path) -> dict:
    from sat import compact as cpt
    from sat import kernel as kern
    from sat import ls_v3
    row = {c: "" for c in COLUMNS}
    row.update(set=set_, hash=hash_, path=path, bytes=os.path.getsize(path))
    row["sha256"] = sha256(path)
    t = time.time()
    w = cpt.load(path)
    row["parse_s"] = round(time.time() - t, 3)
    row["rss_parse_mb"] = rss_mb()
    k = w.counts()
    row.update(n_vars=w.n_vars, n_clauses=w.m, n_lits=w.nlits, n_hard=k["n_hard"], n_soft=k["n_soft"],
               soft_w_sum=k["soft_w_sum"], soft_w_max=k["soft_w_max"], max_len=k["max_len"],
               weighted=int(k["weighted"]))
    mode, bound = ls_v3.nbrs_plan(w)
    row.update(nbrs_bound=bound, nbrs_mode=mode)
    hit, occ = w.screen_counts()
    frac = hit / occ if occ else 0.0
    row.update(screen_hit=hit, screen_occ=occ, screen_frac=round(frac, 6))
    if frac < GATE["preprocess_gate"]["screen_min"]:
        row["kernel_status"] = "skipped_screen"
    elif row["bytes"] / 2 ** 20 > KERNEL_MAX_MIB:
        row["kernel_status"] = "not_run_size"
    else:
        t = time.time()
        g = kern.gate(w, GATE)
        row["kernel_s"] = round(time.time() - t, 3)
        row["kernel_status"] = g.decision
        f = g.fields
        row.update(kernel_n_vars=f.get("kernel_n_vars") or "", kernel_n_clauses=f.get("kernel_n_clauses") or "",
                   kernel_gain=f.get("kernel_gain") if f.get("kernel_gain") is not None else "")
    row["rss_end_mb"] = rss_mb()
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--set", required=True)
    ap.add_argument("--hash", required=True)
    ap.add_argument("--path", required=True, help="relative to the tree root")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.chdir(ROOT)
    try:
        row = census(a.set, a.hash, a.path)
    except Exception as e:   # recorded, so the readout sees it; the task goes on
        row = {c: "" for c in COLUMNS}
        row.update(set=a.set, hash=a.hash, path=a.path, error=f"{type(e).__name__}: {e}"[:300],
                   rss_end_mb=rss_mb())
    tmp = a.out + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\t".join(str(row[c]).replace("\t", " ") for c in COLUMNS) + "\n")
    os.replace(tmp, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
