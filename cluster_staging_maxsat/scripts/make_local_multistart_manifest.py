#!/usr/bin/env python3
"""Build a tier-2 job manifest for either local-multistart ablation arm.

Two arms share this generator, differing only in which solver config they point
at and therefore in `multistart.init`:

    local_multistart_deeppolish      init: uniform   (the no-EA baseline)
    local_multistart_jw_deeppolish   init: jw        (no EA, EA seeding)

Both must run on the identical 26 instances with the identical oracle_cost
values, or the three-arm design collapses -- a difference between the arms would
be confounded with a difference in what they were asked to solve. That is why
the arm is selected by `--arm` (or `--config`) and everything else, the oracle
table above all, is shared rather than re-derived per arm. `--verify-against`
re-checks it after the fact, joining the two manifests on the instance's
sha256 rather than on its path.

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
    python3 scripts/make_local_multistart_manifest.py                 # uniform arm
    python3 scripts/make_local_multistart_manifest.py --arm jw        # jw arm
    python3 scripts/make_local_multistart_manifest.py --arm jw \
        --verify-against scripts/manifest_tier2_local_multistart.tsv
    python3 scripts/make_local_multistart_manifest.py --seeds 1 2 3 --budget 60

Defaults are unchanged from the single-arm version: a bare invocation still
writes the uniform arm's manifest, byte for byte.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys

ORACLE = "scripts/tier2_oracle.csv"
DEFAULT_SEEDS = [1, 2, 3, 4, 5]
DEFAULT_BUDGET = 900.0

# The arms this generator knows how to emit, keyed by the name `--arm` takes.
# `out` and `prefix` are derived from the arm rather than passed in, so the two
# manifests cannot be written on top of each other and their job_ids cannot
# collide in a shared results tree or in combine_tier2's reconciliation. Both
# remain overridable with --out / --prefix for a one-off rerun.
ARMS = {
    "uniform": {
        "config": "configs/tier2/local_multistart_deeppolish.yaml",
        "out": "scripts/manifest_tier2_local_multistart.tsv",
        "prefix": "t2lms",
    },
    "jw": {
        "config": "configs/tier2/local_multistart_jw_deeppolish.yaml",
        "out": "scripts/manifest_tier2_local_multistart_jw.tsv",
        "prefix": "t2lmsjw",
    },
}
DEFAULT_ARM = "uniform"

# Reverse lookup so `--config <path>` alone still picks the right out/prefix.
_BY_CONFIG = {v["config"]: v for v in ARMS.values()}


def _oracle_by_sha(rows) -> dict:
    """sha256 -> oracle_cost, the join key the cross-arm check uses.

    The manifest carries the instance *path*, not its digest, so two manifests
    could agree path-for-path while pointing at different bytes -- a re-rsynced
    or regenerated instance under the same name. Joining on the digest the
    oracle table records is what actually establishes that both arms were given
    the same problem with the same certified optimum.
    """
    return {r["sha256"]: r["oracle_cost"] for r in rows}


def _verify_against(other_path: str, rows, emitted) -> int:
    """Compare this manifest's oracle_cost with another manifest's, per instance.

    Both are joined to `tier2_oracle.csv` by path to recover each instance's
    sha256, then compared digest-for-digest. Returns the number of mismatches;
    0 means the two arms are solving the identical problem set. A path present
    in one manifest and not the other is itself a mismatch -- the arms must
    cover the same 26 instances, not merely agree where they overlap.
    """
    sha_by_path = {r["resolved"]: r["sha256"] for r in rows}
    oracle_by_sha = _oracle_by_sha(rows)

    def load(path):
        seen = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                cols = line.rstrip("\n").split("\t")
                seen.setdefault(cols[1], set()).add(cols[6])
        return seen

    mine = load(emitted)
    theirs = load(other_path)

    problems = []
    for path in sorted(set(mine) | set(theirs)):
        sha = sha_by_path.get(path)
        if sha is None:
            problems.append(f"  {path}: not in {ORACLE}")
            continue
        a, b = mine.get(path), theirs.get(path)
        if a is None or b is None:
            problems.append(f"  {path} [{sha[:12]}]: "
                            f"{'missing from ' + emitted if a is None else 'missing from ' + other_path}")
            continue
        # Within one manifest every seed of an instance must carry one oracle.
        if len(a) != 1 or len(b) != 1:
            problems.append(f"  {path} [{sha[:12]}]: non-unique oracle_cost "
                            f"{sorted(a)} vs {sorted(b)}")
            continue
        (a,), (b,) = a, b
        ref = oracle_by_sha[sha]
        if a != b or a != ref:
            problems.append(f"  {path} [{sha[:12]}]: {emitted}={a} "
                            f"{other_path}={b} {ORACLE}={ref}")

    print(f"\noracle cross-check vs {other_path}")
    print(f"  instances compared : {len(set(mine) | set(theirs))}")
    print(f"  joined on          : instance_sha256 (via {ORACLE})")
    if problems:
        print(f"  MISMATCHES         : {len(problems)}")
        for line in problems:
            print(line)
    else:
        print("  MISMATCHES         : 0  -- both arms agree oracle-for-oracle")
    return len(problems)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit the (instance, seed) manifest for a local_multistart arm.")
    ap.add_argument("--oracle", default=ORACLE)
    ap.add_argument("--arm", choices=sorted(ARMS), default=DEFAULT_ARM,
                    help="Which ablation arm to emit; sets --config, --out and "
                         "--prefix together (default: %(default)s)")
    ap.add_argument("--config", default=None,
                    help="Override the arm's solver config path")
    ap.add_argument("--config-id", default=None,
                    help="Default: the config file stem, e.g. local_multistart_jw_deeppolish")
    ap.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    ap.add_argument("--budget", type=float, default=DEFAULT_BUDGET,
                    help="Solver wall-clock cutoff in seconds (default: the 900 s "
                         "the tier-2 memetic runs used)")
    ap.add_argument("--prefix", default=None, help="job_id prefix (default: the arm's)")
    ap.add_argument("-o", "--out", default=None, help="(default: the arm's)")
    ap.add_argument("--verify-against", default=None, metavar="MANIFEST",
                    help="After writing, check oracle_cost agrees with this other "
                         "manifest for every instance, joined on instance_sha256. "
                         "Exits 3 on any mismatch.")
    ap.add_argument("--data-root", default=".",
                    help="Tree the oracle's instance paths are relative to")
    args = ap.parse_args(argv)

    # --config wins over --arm; if it names a known arm's config, that arm's
    # out/prefix come with it, so `--config <jw yaml>` cannot silently overwrite
    # the uniform manifest.
    arm = ARMS[args.arm]
    if args.config is not None:
        arm = _BY_CONFIG.get(args.config, {**arm, "config": args.config})
    config = args.config or arm["config"]
    out = args.out or arm["out"]
    prefix = args.prefix or arm["prefix"]

    config_id = args.config_id or os.path.splitext(os.path.basename(config))[0]

    for path, what in ((args.oracle, "oracle table"), (config, "solver config")):
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

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    n = 0
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        # Instance-major, seed-minor: with 5 seeds, array task IDs 0-4 are the
        # first instance, 5-9 the second, and so on. Keeping the seeds of one
        # instance adjacent makes a partial array easy to reason about.
        for r in sorted(rows, key=lambda x: x["resolved"]):
            for seed in args.seeds:
                n += 1
                w.writerow([
                    f"{prefix}_{n:05d}",
                    r["resolved"], config, config_id,
                    seed, f"{args.budget:g}",
                    r["oracle_cost"], r["tier"], r["rc2_run"],
                ])

    suffix = "_jw" if config_id.startswith("local_multistart_jw") else ""
    print(f"arm       : {config_id}")
    print(f"config    : {config}")
    print(f"instances : {len(rows)}")
    print(f"seeds     : {len(args.seeds)}  {args.seeds}")
    print(f"budget    : {args.budget:g} s")
    print(f"tasks     : {n}")
    print(f"manifest  : {out}")

    if args.verify_against:
        if _verify_against(args.verify_against, rows, out):
            print("\nFATAL: the two arms do not agree on the problem set. An "
                  "ablation whose arms were given different oracles measures "
                  "nothing.", file=sys.stderr)
            return 3

    print(f"\nsubmit with:  bash scripts/submit_tier2_local_multistart{suffix}.sh")
    print(f"or directly:  MANIFEST={out} \\")
    print(f"              OUTDIR=results/tier2_local_multistart{suffix}/tasks \\")
    print(f"              sbatch --array=0-{n - 1}%30 "
          f"scripts/tier2_local_multistart_array.sbatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
