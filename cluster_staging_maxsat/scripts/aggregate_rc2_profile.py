#!/usr/bin/env python3
"""Aggregate a per-task RC2 profile directory into the two batch files.

The rule was applied by hand at Checkpoint 2 of docs/CORPUS_CALIBRATION_LOG.md
and is written down here so calib_b, M4 and any re-run use the same one:

    <outdir>/task_N.jsonl      0+ appended profile rows   -> LAST row per task
    <outdir>/task_N.env.json   0+ appended env lines      -> LAST line per task

    results/profile_<batch>_all.jsonl   {"task": N, **last_row,
                                         "env": last_env - task - instance}
    results/profile_<batch>_env.jsonl   the last env line per task, verbatim

both sorted by task id. "Last row" is §4.4 of the goals doc: a task that was
re-run appends a new row and the later one wins; the count of superseded rows
is reported, not silently dropped.

Three things this prints and does not fix, because each one is a finding:

  * tasks with no row at all -- the §4.4 class-3 "Slurm killed the task"
    signature (the profiler writes its row only after the subprocess returns).
    They are gaps in the manifest, and `rc2_row_state.py --pending` is what
    resubmits them.
  * rows whose `instance` differs from the manifest line of that task id.
  * completed rows with a negative `solve_s`. The outer profiler times with
    time.monotonic(), but the value it reports for a completed run is the
    child's `elapsed_s`, which solve_rc2_anytime.py computes from time.time()
    -- a wall clock, so a clock step during the run yields a nonsense
    duration. Seen once on a WSL2 workstation smoke run (-0.827 s); zero
    occurrences in A1's 180 cluster rows. Not repaired here: the measurement
    path is frozen for the duration of the calibration (CALIB_B_PLAN §6), so
    this is a detector, and an affected row is a §4.4 class-3 failure to
    re-run, not a fast solve.
  * more than one distinct `pysat_version` / `python` across the batch. The
    calibration compares RC2 timings across batches, so a version that moved
    mid-batch has to surface here rather than at analysis time
    (Checkpoint 2's 1.9.dev3 finding; docs/CALIB_B_PLAN.md §6).

    python scripts/aggregate_rc2_profile.py --batch calib_b
    python scripts/aggregate_rc2_profile.py --batch calib_a --check

Run from the staging tree root (where results/ and scripts/ live), on the
workstation after the rsync back, or on the cluster. stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple


def _last_json_line(path: str) -> Tuple[Optional[dict], int]:
    """(last parsable object in the file, number of parsable objects).

    A torn final line from a killed task is skipped, matching
    rc2_row_state.last_row_for.
    """
    if not os.path.exists(path):
        return None, 0
    last, n = None, 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            last, n = obj, n + 1
    return last, n


def read_manifest(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]


def aggregate(outdir: str, n_tasks: int) -> Tuple[List[dict], List[dict], Dict[str, Any]]:
    rows: List[dict] = []
    envs: List[dict] = []
    stats: Dict[str, Any] = {
        "tasks": n_tasks, "rows": 0, "superseded": 0, "missing_rows": [],
        "missing_env": [], "env_superseded": 0,
    }
    for task in range(1, n_tasks + 1):
        row, n_row = _last_json_line(os.path.join(outdir, f"task_{task}.jsonl"))
        env, n_env = _last_json_line(os.path.join(outdir, f"task_{task}.env.json"))
        if env is not None:
            envs.append(env)
            stats["env_superseded"] += max(0, n_env - 1)
        else:
            stats["missing_env"].append(task)
        if row is None:
            stats["missing_rows"].append(task)
            continue
        stats["rows"] += 1
        stats["superseded"] += max(0, n_row - 1)
        env_payload = {k: v for k, v in (env or {}).items()
                       if k not in ("task", "instance")}
        rows.append({"task": task, **row, "env": env_payload})
    return rows, envs, stats


def check_against_manifest(rows: List[dict], manifest: List[str]) -> List[str]:
    problems = []
    for r in rows:
        want = manifest[r["task"] - 1]
        got = r.get("instance", "")
        if os.path.normpath(want) != os.path.normpath(got):
            problems.append(f"task {r['task']}: row instance {got!r} != manifest {want!r}")
    return problems


def env_spread(envs: List[dict], key: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for e in envs:
        out[str(e.get(key))] = out.get(str(e.get(key)), 0) + 1
    return out


def bad_timing(rows: List[dict]) -> List[int]:
    """Completed rows whose solve_s is negative -- a clock step, not a time."""
    out = []
    for r in rows:
        p = r.get("profile") or {}
        if p.get("completed") is True and (p.get("solve_s") or 0) < 0:
            out.append(r["task"])
    return out


def classes(rows: List[dict]) -> Dict[str, int]:
    """§4.4 classes. Censored is status in {timeout, subprocess_killed}."""
    out = {"completed": 0, "censored": 0, "failed": 0}
    for r in rows:
        p = r.get("profile") or {}
        if p.get("completed") is True:
            out["completed"] += 1
        elif p.get("status") in ("timeout", "subprocess_killed"):
            out["censored"] += 1
        else:
            out["failed"] += 1
    return out


def dump(path: str, objs: List[dict]) -> str:
    text = "".join(json.dumps(o, sort_keys=False) + "\n" for o in objs)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return text


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--batch", default="calib_b", help="batch name (default: %(default)s)")
    ap.add_argument("--outdir", default=None,
                    help="per-task dir (default results/profile_<batch>)")
    ap.add_argument("--manifest", default=None,
                    help="Slurm manifest (default scripts/manifest_<batch>_rc2.txt)")
    ap.add_argument("--results-dir", default="results",
                    help="where the two batch files go (default: %(default)s)")
    ap.add_argument("--check", action="store_true",
                    help="write nothing; fail (exit 1) if the files on disk differ")
    args = ap.parse_args(argv)

    outdir = args.outdir or os.path.join("results", f"profile_{args.batch}")
    manifest_path = args.manifest or os.path.join(
        "scripts", f"manifest_{args.batch}_rc2.txt")
    for p in (outdir, manifest_path):
        if not os.path.exists(p):
            print(f"FATAL: not found: {p} (cwd {os.getcwd()})", file=sys.stderr)
            return 2

    manifest = read_manifest(manifest_path)
    rows, envs, stats = aggregate(outdir, len(manifest))
    problems = check_against_manifest(rows, manifest)

    all_path = os.path.join(args.results_dir, f"profile_{args.batch}_all.jsonl")
    env_path = os.path.join(args.results_dir, f"profile_{args.batch}_env.jsonl")

    all_text = "".join(json.dumps(o, sort_keys=False) + "\n" for o in rows)
    env_text = "".join(json.dumps(o, sort_keys=False) + "\n" for o in envs)

    print(f"batch      : {args.batch}")
    print(f"manifest   : {manifest_path}  ({stats['tasks']} tasks)")
    print(f"rows       : {stats['rows']}  superseded={stats['superseded']}  "
          f"env_superseded={stats['env_superseded']}")
    print(f"classes    : {classes(rows)}")
    print(f"pysat      : {env_spread(envs, 'pysat_version')}")
    print(f"python     : {env_spread(envs, 'python')}")
    print(f"hosts      : {len(env_spread(envs, 'host'))} distinct")
    if stats["missing_rows"]:
        print(f"MISSING ROWS ({len(stats['missing_rows'])}): "
              f"{stats['missing_rows'][:20]}  -> RESUME=1 bash submit_rc2_profile.sh")
    if stats["missing_env"]:
        print(f"MISSING ENV ({len(stats['missing_env'])}): {stats['missing_env'][:20]}")
    for pr in problems[:20]:
        print(f"MISMATCH: {pr}")
    bad = bad_timing(rows)
    if bad:
        print(f"WARNING: {len(bad)} completed row(s) with negative solve_s "
              f"(tasks {bad[:20]}) -- clock step during the run, not a fast "
              f"solve. Treat as §4.4 class 3 and re-run.")
    if len(env_spread(envs, "pysat_version")) > 1:
        print("WARNING: more than one PySAT version in this batch -- timings are "
              "not comparable across it (docs/CALIB_B_PLAN.md §6).")

    if args.check:
        bad = False
        for path, text in ((all_path, all_text), (env_path, env_text)):
            on_disk = open(path, encoding="utf-8").read() if os.path.exists(path) else None
            if on_disk != text:
                print(f"CHECK FAILED: {path} differs from the aggregation rule")
                bad = True
            else:
                print(f"CHECK OK: {path} ({len(text.splitlines())} rows)")
        return 1 if bad or problems else 0

    os.makedirs(args.results_dir, exist_ok=True)
    dump(all_path, rows)
    dump(env_path, envs)
    print(f"wrote      : {all_path}  ({len(rows)} rows)")
    print(f"wrote      : {env_path}  ({len(envs)} rows)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
