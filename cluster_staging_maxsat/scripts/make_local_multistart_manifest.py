#!/usr/bin/env python3
"""Build the tier-2 job manifest for the `local_multistart_deeppolish` baseline.

One line per (instance, seed): 26 tier-2 instances x 5 seeds = 130 tasks, which
is exactly the shape `scripts/tier2_local_multistart_array.sbatch` submits.

The instance set and the certified optima come from `scripts/tier2_oracle.csv`,
NOT from a fresh pass over `results/hardness/`. That is deliberate: the oracle
CSV is the committed artifact the already-completed memetic run was generated
from (`src/bench/make_tier2_manifest.py` wrote both in the same invocation), so
reading it back guarantees this ablation covers the identical 26 instances with
the identical oracle_cost values. Re-deriving from the raw RC2 profiles could
silently drift -- a re-profiled instance, a changed tier cutoff -- and an
ablation that does not run on the same instances as its baseline is not an
ablation. It also means this script has no dependency on `results/hardness/`,
which is not part of the staging tree.

Column layout is byte-compatible with `manifest_tier2_memetic.tsv`, so the
existing array driver, `build_tier2_instance_index.py` and the resubmit-line
logic in `src/bench/combine_tier2.py` all read it without a special case:

    job_id  instance  config  config_id  seed  budget_s  oracle_cost  tier  rc2_run

Usage (run from cluster_staging_maxsat/):
    python3 scripts/make_local_multistart_manifest.py
    python3 scripts/make_local_multistart_manifest.py --seeds 1 2 3 --budget 60
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

ORACLE = "scripts/tier2_oracle.csv"
CONFIG = "configs/tier2/local_multistart_deeppolish.yaml"
DEFAULT_OUT = "scripts/manifest_tier2_local_multistart.tsv"
DEFAULT_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_BUDGET = 900.0
DEFAULT_PREFIX = "t2lms"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit the (instance, seed) manifest for the local_multistart baseline.")
    ap.add_argument("--oracle", default=ORACLE)
    ap.add_argument("--config", default=CONFIG)
    ap.add_argument("--config-id", default=None,
                    help="Default: the config file stem, i.e. local_multistart_deeppolish")
    ap.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                    help="Solver wall-clock cutoff in seconds (default: the 900 s "
                         "the tier-2 memetic runs used)")
    ap.add_argument("--prefix", default=DEFAULT_PREFIX, help="job_id prefix")
    ap.add_argument("-o", "--out", default=DEFAULT_OUT)
    ap.add_argument("--data-root", default=".",
                    help="Tree the oracle's instance paths are relative to")
    args = ap.parse_args(argv)

    config_id = args.config_id or os.path.splitext(os.path.basename(args.config))[0]

    for path, what in ((args.oracle, "oracle table"), (args.config, "solver config")):
        if not os.path.isfile(path):
            print(f"FATAL: {what} not found: {path} (run this from "
                  f"cluster_staging_maxsat/)", file=sys.stderr)
            return 2

    with open(args.oracle, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print(f"FATAL: {args.oracle} has no rows", file=sys.stderr)
        return 2

    # Fail before writing anything rather than emit tasks that die on a node.
    missing = [r["resolved"] for r in rows
               if not os.path.isfile(os.path.join(args.data_root, r["resolved"]))]
    if missing:
        print(f"FATAL: {len(missing)} instance(s) from {args.oracle} are not on "
              f"disk under {args.data_root!r}:", file=sys.stderr)
        for m in missing:
            print(f"    {m}", file=sys.stderr)
        print("data/ is gitignored -- rsync the staging tree's data/ first.",
              file=sys.stderr)
        return 2

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    n = 0
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        # Instance-major, seed-minor: with 5 seeds, array task IDs 0-4 are the
        # first instance, 5-9 the second, and so on. Keeping the seeds of one
        # instance adjacent makes a partial array easy to reason about.
        for r in sorted(rows, key=lambda x: x["resolved"]):
            for seed in args.seeds:
                n += 1
                w.writerow([
                    f"{args.prefix}_{n:05d}",
                    r["resolved"], args.config, config_id,
                    seed, f"{args.budget:g}",
                    r["oracle_cost"], r["tier"], r["rc2_run"],
                ])

    print(f"instances : {len(rows)}")
    print(f"seeds     : {len(args.seeds)}  {args.seeds}")
    print(f"budget    : {args.budget:g} s")
    print(f"tasks     : {n}")
    print(f"manifest  : {args.out}")
    print(f"\nsubmit with:  bash scripts/submit_tier2_local_multistart.sh")
    print(f"or directly:  sbatch --array=0-{n - 1}%30 "
          f"scripts/tier2_local_multistart_array.sbatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
