#!/usr/bin/env python3
"""Run the pre-registered ρ analysis (mse26_rho.py, unchanged) under two treatments of
the 3c runs that ended in an error (MSE26_3C_RUN.md §7: heap crash, glucose_timeout,
Slurm wall kill; m2_results classes infra_missing / infra_error / invalid_submission).

  --errors exclude   as mse26_rho.py: an instance with any such run is incomplete and
                     leaves every analysis (the run-level default of the pre-registration)
  --errors fail      each such run, or a missing seed, counts as a memetic failure at the
                     budget (effort B in ERT, 2B in PAR2), like budget_exhausted

User request 2026-10-29, before the fixes and reruns of §7.

    python3 scripts/mse26_rho_errors.py --errors fail    --outdir results/mse26_memetic/tasks
    python3 scripts/mse26_rho_errors.py --errors exclude --outdir results/mse26_memetic/tasks
Default --out: results/mse26_rho_<errors>/.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mse26_rho as rho  # noqa: E402

FAILED = {"cls": "budget_exhausted", "cpu_to_target_s": None, "cpu_to_target_hit_s": None,
          "calls_to_target": None}


def errors_as_failures(load_runs):
    def wrapped(manifests, outdir, seeds):
        runs = load_runs(manifests, outdir, seeds)
        for by_seed in runs.values():
            for s in seeds:
                r = by_seed.get(s)
                if r is None or r["cls"] in rho.m2.PENDING_CLASSES:
                    by_seed[s] = dict(FAILED)
        return runs
    return wrapped


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    mode = "exclude"
    if "--errors" in argv:
        i = argv.index("--errors")
        mode = argv[i + 1]
        del argv[i:i + 2]
    if mode not in ("fail", "exclude"):
        raise SystemExit("--errors must be fail or exclude")
    if "--out" not in argv:
        argv += ["--out", os.path.join(rho.ROOT, "results", f"mse26_rho_{mode}")]
    if mode == "fail":
        rho.load_runs = errors_as_failures(rho.load_runs)
    return rho.main(argv)


if __name__ == "__main__":
    sys.exit(main())
