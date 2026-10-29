#!/usr/bin/env python3
"""The ρ population on MSE 2026 (docs/current2/MSE26_RHO_PREREG.md §2): all 1,216 exact-track instances.

Workstation only. Reads the published metadata and raw results (Zenodo 21358014,
data/raw/mse_results/mse26/) and the unpack job's content table; writes
scripts/mse26_population.tsv, one row per instance:

  target_kind   proven: the published optimal_cost, proved in the 2026 runs by at least
                one exact solver (OPTIMUM FOUND, verified, optval = optimal_cost; any
                solver, not only EvalMaxSAT; user 2026-10-29) | not_proved_2026 (a
                published optimum no 2026 run proved) | no_optimum (none published)
                | infeasible (every answer UNSATISFIABLE); only `proven` is a target
  provers       how many 2026 exact-solver runs proved it
  ems_status    EvalMaxSAT's published outcome: proved (OPTIMUM FOUND, verified, the
                published optimum where one exists, CPU <= 3600) | timeout | memout |
                crash (no answer, no timeout, no memout) | unsat (infeasible hard
                clauses) | wrong (OPTIMUM FOUND but unverified or not the optimum)
  x_role        finite (proved: x = CPU time) | censored (timeout: x = inf, tied top
                rank) | excluded (any other EvalMaxSAT outcome, or no target)
  primary       1 if in the primary population (x finite or censored, target exists)
  par2          1 if in the PAR2 sensitivity population: every proven-optimum instance,
                EvalMaxSAT memouts and crashes included (user 2026-10-29)
  x_par2_s      EvalMaxSAT's PAR2 (one run): its CPU time if proved, else 2 x 3600 = 7200
  window        1 if x finite in (30, 3600] s CPU (the window sensitivity analysis;
                y finiteness is applied at analysis time)
  in_3c         1 if run in batch 3c (the 952 with a published optimum)

    python3 scripts/mse26_population.py           # writes the table, prints the counts
"""
from __future__ import annotations

import csv
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
PUB = os.path.join(REPO, "data", "raw", "mse_results", "mse26")
CONTENT = os.path.join(ROOT, "results", "mse26_unpack", "mse26_content.tsv")
OUT = os.path.join(ROOT, "scripts", "mse26_population.tsv")
RAW = {"mse26-exact-unweighted": "mse26_exact_unweighted_rawdata.csv",
       "mse26-exact-weighted": "mse26_exact_weighted_rawdata.csv"}
COLUMNS = ["set", "hash", "family", "optimal_cost", "best_known_cost", "target_kind", "provers", "target", "ems_status",
           "ems_cpu_s", "ems_wall_s", "x_role", "primary", "par2", "x_par2_s", "window", "in_3c"]


def known(v: str) -> bool:
    return v not in ("unknown", "", "NA")


def ems_status(r: dict, opt: str) -> str:
    if r["answer"] == "OPTIMUM FOUND":
        ok = r["verified"] == "1" and float(r["cpu.time"]) <= 3600 and (not known(opt) or r["optval"] == opt)
        return "proved" if ok else "wrong"
    if r["timeout"] == "true":
        return "timeout"
    if r["memout"] == "true":
        return "memout"
    if r["answer"] == "UNSATISFIABLE":
        return "unsat"
    return "crash"


def main() -> int:
    with open(os.path.join(PUB, "benchmark-metadata.csv"), newline="") as f:
        meta = {r["hash"]: r for r in csv.DictReader(f)}
    with open(CONTENT, newline="") as f:
        content = {r["file"][:-len(".wcnf.xz")]: r for r in csv.DictReader(f, delimiter="\t")}
    ems, provers, answers = {}, Counter(), {}
    for set_, fn in RAW.items():
        with open(os.path.join(PUB, fn), newline="") as f:
            for r in csv.DictReader(f):
                h = r["instance"][:-len(".wcnf")]
                if r["solvername"] == "EvalMaxSAT":
                    ems[h] = (set_, r)
                answers.setdefault(h, set()).add(r["answer"])
                if (r["answer"] == "OPTIMUM FOUND" and r["verified"] == "1"
                        and r["optval"] == meta[h]["optimal_cost"]):
                    provers[h] += 1
    if not (len(meta) == len(content) == len(ems) == 1216):
        raise SystemExit(f"FATAL: expected 1216 instances, got meta {len(meta)} content {len(content)} ems {len(ems)}")
    rows = []
    for h in sorted(meta, key=lambda h: (ems[h][0], h)):
        m, (set_, r) = meta[h], ems[h]
        opt, bk = m["optimal_cost"], m["best_known_cost"]
        if provers[h]:
            kind, target = "proven", opt
        elif known(opt):
            kind, target = "not_proved_2026", ""
        else:
            kind, target = ("infeasible" if answers[h] <= {"UNSATISFIABLE", "NONE"} and "UNSATISFIABLE" in answers[h]
                            else "no_optimum"), ""
        st = ems_status(r, opt)
        role = "finite" if st == "proved" else "censored" if st == "timeout" else "excluded"
        if kind != "proven":
            role = "excluded"
        cpu = float(r["cpu.time"])
        rows.append({"set": set_, "hash": h, "family": m["family"], "optimal_cost": opt, "best_known_cost": bk,
                     "target_kind": kind, "provers": provers[h], "target": target, "ems_status": st, "ems_cpu_s": r["cpu.time"],
                     "ems_wall_s": r["wall.time"], "x_role": role, "primary": int(role != "excluded"),
                     "par2": int(kind == "proven"),
                     "x_par2_s": (r["cpu.time"] if st == "proved" else "7200") if kind == "proven" else "",
                     "window": int(role == "finite" and 30 < cpu <= 3600),
                     "in_3c": int(content[h]["unpacked"] == "1")})
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    c = lambda key, sel=lambda r: True: dict(Counter(r[key] for r in rows if sel(r)))
    print(f"{len(rows)} instances -> {os.path.relpath(OUT, ROOT)}")
    print("target_kind:", c("target_kind"))
    print("ems_status:", c("ems_status"))
    print("x_role:", c("x_role"))
    print("primary:", sum(r["primary"] for r in rows), "| by target:", c("target_kind", lambda r: r["primary"]),
          "| by x:", c("x_role", lambda r: r["primary"]), "| by set:", c("set", lambda r: r["primary"]))
    print("primary but not run in 3c:", sum(r["primary"] and not r["in_3c"] for r in rows))
    print("window (x finite in (30, 3600]):", sum(r["window"] for r in rows))
    print("PAR2 population:", sum(r["par2"] for r in rows), "| x = 7200 by EvalMaxSAT outcome:",
          c("ems_status", lambda r: r["par2"] and r["x_par2_s"] == "7200"))
    print("excluded with a target, by EvalMaxSAT outcome:",
          c("ems_status", lambda r: not r["primary"] and r["target_kind"] == "proven"))
    print("primary EvalMaxSAT-proved / proved only by other solvers (x censored):",
          sum(r["primary"] and r["x_role"] == "finite" for r in rows), "/",
          sum(r["primary"] and r["x_role"] == "censored" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
