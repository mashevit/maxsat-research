#!/usr/bin/env python3
"""Memory bins for the MSE 2026 memetic batch (3c; docs/current2/COMPILED_MEMETIC_PLAN.md §15).

Workstation only (reads the census, the large-instance kernel rows and the
published MSE 2026 raw data; writes one TSV). Per instance:

  evalmaxsat_mib  EvalMaxSAT's published peak (`mem.usage`, KiB -> MiB); a
                  published memout -> 64 GB bin (EVALMAXSAT_2026_INSTALL.md §4).
  memetic_mib     our estimate of the memetic run's peak:
                  - kernel screen not passed (the run is on the original):
                    the C4 model of the compact path, soft 9 x MiB + 100,
                    hard 14 x MiB + 120 (COMPILED_MEMETIC_PLAN.md §8 C4);
                  - kernel / kernel_empty (kernel gate on for all, user
                    2026-10-29): the larger of the measured gate peak (census
                    `rss_end_mb`, or the large-instance task, §14) and the parse
                    footprint + the C4 model on the kernel's share of the file
                    (kernel clauses / clauses); kernel_empty runs no search.
  need_mib        max(evalmaxsat_mib, memetic_mib)
  bin_gb          the smallest of 8 / 16 / 32 / 64 whose 75 % covers need_mib.

    python3 scripts/mse26_membins.py            # writes scripts/mse26_membins.tsv, prints the counts
"""
from __future__ import annotations

import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
CENSUS = os.path.join(ROOT, "results", "mse26_census", "mse26_census.tsv")
KBIG = os.path.join(ROOT, "results", "mse26_kernel_big", "rows")
RAW = {"mse26-exact-unweighted": os.path.join(REPO, "data", "raw", "mse_results", "mse26", "mse26_exact_unweighted_rawdata.csv"),
       "mse26-exact-weighted": os.path.join(REPO, "data", "raw", "mse_results", "mse26", "mse26_exact_weighted_rawdata.csv")}
OUT = os.path.join(ROOT, "scripts", "mse26_membins.tsv")

BINS_GB = (8, 16, 32, 64)
COVER = 0.75
SOFT = (9.0, 100.0)     # MiB per file MiB, MiB (C4 upper envelope)
HARD = (14.0, 120.0)

COLUMNS = ["set", "hash", "path", "sha256", "mib", "type", "kernel_status", "evalmaxsat_mib", "evalmaxsat_memout",
           "memetic_mib", "memetic_basis", "need_mib", "bin_gb", "bin_by"]


def model(mib: float, hard: bool) -> float:
    a, b = HARD if hard else SOFT
    return a * mib + b


def bin_for(need_mib: float) -> int:
    for g in BINS_GB:
        if COVER * g * 1024 >= need_mib:
            return g
    raise SystemExit(f"FATAL: need {need_mib:.0f} MiB does not fit {BINS_GB[-1]} GB at {COVER:.0%}")


def evalmaxsat_rows():
    out = {}
    for set_, p in RAW.items():
        with open(p, newline="") as f:
            for r in csv.DictReader(f):
                if r["solvername"] == "EvalMaxSAT":
                    out[(set_, r["instance"][:-len(".wcnf")])] = r
    return out


def main() -> int:
    ems = evalmaxsat_rows()
    kbig = {}
    for fn in os.listdir(KBIG):
        with open(os.path.join(KBIG, fn)) as f:
            r = next(csv.reader(f, delimiter="\t"))
        kbig[r[1]] = r
    rows = []
    with open(CENSUS, newline="") as f:
        for c in csv.DictReader(f, delimiter="\t"):
            key = (c["set"], c["hash"])
            e = ems.get(key)
            if e is None:
                raise SystemExit(f"FATAL: no published EvalMaxSAT row for {key}")
            mib = int(c["bytes"]) / 2 ** 20
            hard = int(c["n_hard"]) > 0
            status = c["kernel_status"]
            if status == "not_run_size":          # the 2 large ones: the large-instance task (§14)
                k = kbig[c["hash"]]
                status, kc, gate_mib = k[19], k[21], float(k[26])
            else:
                kc, gate_mib = c["kernel_n_clauses"], float(c["rss_end_mb"] or 0)
            if status == "skipped_screen":
                mem, basis = model(mib, hard), "model_original"
            elif status in ("kernel", "kernel_empty"):
                share = (int(kc) / int(c["n_clauses"])) if kc else 0.0
                run = float(c["rss_parse_mb"]) + (model(mib * share, hard) if status == "kernel" else 0.0)
                mem, basis = (gate_mib, "gate_measured") if gate_mib >= run else (run, "parse+model_kernel")
            else:
                raise SystemExit(f"FATAL: kernel_status {status!r} for {key}")
            memout = e["memout"] == "true"
            em = float(e["mem.usage"]) / 1024
            need = max(em, mem)
            g = 64 if memout else bin_for(need)
            by = "evalmaxsat_memout" if memout else ("evalmaxsat" if em >= mem else "memetic")
            rows.append({"set": c["set"], "hash": c["hash"], "path": c["path"], "sha256": c["sha256"],
                         "mib": round(mib, 3), "type": "hard" if hard else "soft", "kernel_status": status,
                         "evalmaxsat_mib": round(em, 1), "evalmaxsat_memout": int(memout),
                         "memetic_mib": round(mem, 1), "memetic_basis": basis, "need_mib": round(need, 1),
                         "bin_gb": g, "bin_by": by})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"{len(rows)} instances -> {os.path.relpath(OUT, ROOT)}")
    print("bins:", dict(sorted(Counter(r['bin_gb'] for r in rows).items())))
    print("set by:", dict(Counter(r['bin_by'] for r in rows)))
    for g in BINS_GB:
        by = Counter(r["bin_by"] for r in rows if r["bin_gb"] == g)
        print(f"  {g} GB: {dict(by)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
