#!/usr/bin/env python3
"""Decide whether an RC2 profile task still needs to run (resume logic).

Reads the per-task JSONL that `src.cli.profile_hardness` appends to and
classifies the LAST row for the given instance, following
docs/CORPUS_CALIBRATION_GOALS.md §4.4:

    completed   profile.completed == true                    -> skip
    censored    status in {timeout, subprocess_killed}
                and profile.cap_s >= the current cap         -> skip
                (cap_s < current cap: the budget was raised) -> run
    failed      anything else (error, unsat, empty/unparsable
                row, missing row, different instance)        -> run

Usage (from the staging tree root, i.e. after the driver's `cd ..`):

    python scripts/rc2_row_state.py --out results/profile_calib_a/task_7.jsonl \
        --instance data/generated/calib_a/x.wcnf --cap 900
    # prints one of: skip:completed  skip:censored  run:absent  run:failed
    #                run:censored_lower_cap  run:other_instance

    python scripts/rc2_row_state.py --manifest scripts/manifest_calib_a_rc2.txt \
        --outdir results/profile_calib_a --cap 900 --pending
    # prints the 1-based task ids that still need to run, as a Slurm
    # --array id list (e.g. "3,7-9,15"), or nothing if the batch is complete.

stdlib only, so it runs under whatever python the node has before conda is
activated. Exit code is 0 in every classification; only bad arguments exit 2.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

CENSORED = ("timeout", "subprocess_killed")


def last_row_for(out_path: str, instance: str) -> Tuple[Optional[dict], str]:
    """(last valid row for `instance`, note). note='absent' if none."""
    if not os.path.exists(out_path):
        return None, "absent"
    last = None
    saw_other = False
    with open(out_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue  # a torn line from a killed task counts as no row
            if os.path.normpath(rec.get("instance", "")) == os.path.normpath(instance):
                last = rec
            else:
                saw_other = True
    if last is None:
        return None, "other_instance" if saw_other else "absent"
    return last, "found"


def classify(row: Optional[dict], note: str, cap: float) -> str:
    if row is None:
        return f"run:{note}"
    prof = row.get("profile") or {}
    if prof.get("completed") is True:
        return "skip:completed"
    status = prof.get("status")
    if status in CENSORED:
        try:
            cap_s = float(prof.get("cap_s"))
        except (TypeError, ValueError):
            return "run:failed"
        return "skip:censored" if cap_s >= cap else "run:censored_lower_cap"
    return "run:failed"


def state_for(out_path: str, instance: str, cap: float) -> str:
    row, note = last_row_for(out_path, instance)
    return classify(row, note, cap)


def read_manifest(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [l.rstrip("\n") for l in f]


def compress_ids(ids: List[int]) -> str:
    """[3,7,8,9,15] -> '3,7-9,15' (Slurm --array syntax)."""
    out: List[str] = []
    i = 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        out.append(str(ids[i]) if i == j else f"{ids[i]}-{ids[j]}")
        i = j + 1
    return ",".join(out)


def pending_tasks(manifest: str, outdir: str, cap: float) -> Tuple[List[int], Dict[str, int]]:
    lines = read_manifest(manifest)
    pending: List[int] = []
    counts: Dict[str, int] = {}
    for idx, instance in enumerate(lines, start=1):
        if not instance.strip():
            continue
        st = state_for(os.path.join(outdir, f"task_{idx}.jsonl"), instance.strip(), cap)
        counts[st] = counts.get(st, 0) + 1
        if st.startswith("run:"):
            pending.append(idx)
    return pending, counts


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cap", type=float, required=True, help="current --cap (s)")
    one = ap.add_argument_group("single task")
    one.add_argument("--out", help="the task's JSONL")
    one.add_argument("--instance", help="the task's instance path (as in the manifest)")
    many = ap.add_argument_group("whole batch")
    many.add_argument("--manifest", help="Slurm manifest, line N == task N")
    many.add_argument("--outdir", help="directory of task_N.jsonl files")
    many.add_argument("--pending", action="store_true",
                      help="print pending task ids as a Slurm id list")
    many.add_argument("--summary", action="store_true",
                      help="print per-state counts to stderr")
    args = ap.parse_args(argv)

    if args.manifest or args.outdir or args.pending:
        if not (args.manifest and args.outdir):
            ap.error("--manifest and --outdir go together")
        pending, counts = pending_tasks(args.manifest, args.outdir, args.cap)
        if args.summary or not args.pending:
            for k in sorted(counts):
                print(f"{k}\t{counts[k]}", file=sys.stderr)
        if args.pending:
            print(compress_ids(pending))
        return 0

    if not (args.out and args.instance):
        ap.error("--out and --instance go together (or use --manifest/--outdir)")
    print(state_for(args.out, args.instance, args.cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
