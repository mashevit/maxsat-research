#!/usr/bin/env python3
"""Split an M2 manifest into part manifests that fit a Slurm array limit.

docs/M2_FULL_POOL_RUN.md (repo) §3. Run on the login node from the staging
root, ONLY if the preflight shows the whole manifest does not fit one array.

WHY PARTS, NOT INDEX RANGES. tier2_memetic_array.sbatch runs manifest line
$SLURM_ARRAY_TASK_ID. MaxArraySize bounds the index itself (every index must be
< MaxArraySize), so `--array=211-420` is rejected by the same limit that rejects
`--array=1-420`. Each part here is a manifest of its own whose lines are read
with LOCAL indices 1..len(part). The driver is unchanged.

    limit K = min(MaxArraySize - 1, max_array_tasks)       (the caller supplies K)

Parts are as equal as possible, at most K rows each, and cut only between
(instance, solver seed) groups, so the paired runs of one (instance, seed)
always stay in the same part. Every part line is byte-identical to its line in
the full manifest, so job_id -- and with it the shard file name
OUTDIR/<job_id>.jsonl -- is unchanged: all parts share one OUTDIR and the full
manifest still aggregates them.

OUTPUTS, in scripts/parts/ (STEM = full manifest name without .tsv):

    STEM.partIofN.tsv          rows of the full manifest, local line L = task L
    STEM.partIofN.tasks.csv    sidecar rows, task_id = LOCAL index (what
                               `m2_results.py pending` prints for RESUME), plus
                               global_task_id = line in the full manifest
    STEM.partIofN.sha256       the part's instances
    STEM.splitN.map.csv        part, local_task_id, global_task_id, job_id
                               for all rows: the explicit local -> global mapping

Every output is verified after it is written (line identity, mapping, group
integrity, coverage). Concurrency: the throttle is per array, so N parts
submitted together get THROTTLE = 30 // N each (printed).

    python3 scripts/split_m2_manifest.py --manifest scripts/manifest_m2_full_p40.tsv --max-tasks K
"""
from __future__ import annotations

import argparse
import csv
import io
import math
import os
import sys
from typing import Dict, List, Tuple

TOTAL_CONCURRENCY = 30


def read_full(manifest: str) -> Tuple[List[str], List[Dict[str, str]], List[str]]:
    side = manifest[:-len(".tsv")] + ".tasks.csv"
    with open(manifest, encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines(keepends=True) if l.strip()]
    with open(side, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        fields = list(rd.fieldnames or [])
        tasks = list(rd)
    if len(lines) != len(tasks) or any(l.split("\t", 1)[0] != t["job_id"] for l, t in zip(lines, tasks)):
        raise SystemExit(f"FATAL: {manifest} and {side} disagree")
    for i, t in enumerate(tasks, 1):
        if int(t["task_id"]) != i:
            raise SystemExit(f"FATAL: {side} row {i} has task_id {t['task_id']}")
    return lines, tasks, fields


def groups_of(tasks: List[Dict[str, str]]) -> List[Tuple[int, int]]:
    """[start, end) index ranges of consecutive rows sharing (instance, solver seed)."""
    out, start = [], 0
    key = lambda t: (t["instance_sha256"], t["solver_seed"])
    for i in range(1, len(tasks) + 1):
        if i == len(tasks) or key(tasks[i]) != key(tasks[start]):
            out.append((start, i))
            start = i
    seen = set()
    for s, _ in out:
        k = key(tasks[s])
        if k in seen:
            raise SystemExit(f"FATAL: (instance, seed) {k} is not on consecutive lines")
        seen.add(k)
    return out


def plan(groups: List[Tuple[int, int]], n_rows: int, k: int) -> List[Tuple[int, int]]:
    """Fewest parts of <= k rows, cut at group boundaries, sizes as equal as possible."""
    if max(e - s for s, e in groups) > k:
        raise SystemExit(f"FATAL: a pair group is larger than the limit {k}")
    cuts_ok = [e for _, e in groups]  # legal cut points (group ends), ascending
    for n in range(math.ceil(n_rows / k), len(groups) + 1):
        cuts = [0]
        for i in range(1, n):  # cut at the legal point nearest i/n of the way
            c = min((c for c in cuts_ok if c > cuts[-1]), key=lambda c: abs(c - i * n_rows / n))
            cuts.append(c)
        cuts.append(n_rows)
        bounds = list(zip(cuts, cuts[1:]))
        if all(0 < e - s <= k for s, e in bounds):
            return bounds
    raise SystemExit("FATAL: no split found")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--manifest", required=True, help="full manifest, root-relative scripts/....tsv")
    ap.add_argument("--max-tasks", type=int, required=True,
                    help="K = min(MaxArraySize - 1, max_array_tasks)")
    a = ap.parse_args(argv)
    if not os.path.isdir("src") or not os.path.isdir("scripts"):
        raise SystemExit("FATAL: run from the staging tree root")
    if a.max_tasks < 1:
        raise SystemExit("FATAL: --max-tasks must be >= 1")

    lines, tasks, fields = read_full(a.manifest)
    n_rows = len(lines)
    if n_rows <= a.max_tasks:
        print(f"{a.manifest}: {n_rows} rows <= limit {a.max_tasks}; no split needed, "
              f"submit the full manifest as one array.")
        return 0

    groups = groups_of(tasks)
    bounds = plan(groups, n_rows, a.max_tasks)
    n = len(bounds)
    if n > TOTAL_CONCURRENCY:
        raise SystemExit(f"FATAL: limit {a.max_tasks} needs {n} parts, more than the "
                         f"{TOTAL_CONCURRENCY} concurrency slots; submit in sequence instead")
    stem = os.path.basename(a.manifest)[:-len(".tsv")]
    out_dir = os.path.join("scripts", "parts")
    os.makedirs(out_dir, exist_ok=True)
    with open(a.manifest[:-len(".tsv")] + ".sha256", encoding="utf-8") as f:
        sha_of = {l.split("  ", 1)[1].rstrip("\n"): l.split("  ", 1)[0] for l in f if l.strip()}

    map_rows, part_files = [], []
    for p, (s, e) in enumerate(bounds, 1):
        base = os.path.join(out_dir, f"{stem}.part{p}of{n}")
        part_files.append(base + ".tsv")
        with open(base + ".tsv", "w", encoding="utf-8", newline="") as f:
            f.writelines(lines[s:e])
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=fields + ["global_task_id"], lineterminator="\n")
        w.writeheader()
        for local, t in enumerate(tasks[s:e], 1):
            w.writerow(dict(t, task_id=local, global_task_id=t["task_id"]))
            map_rows.append((p, local, int(t["task_id"]), t["job_id"]))
        with open(base + ".tasks.csv", "w", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue())
        insts = sorted({t["instance"] for t in tasks[s:e]})
        with open(base + ".sha256", "w", encoding="utf-8", newline="") as f:
            f.writelines(f"{sha_of[i]}  {i}\n" for i in insts)
    map_path = os.path.join(out_dir, f"{stem}.split{n}.map.csv")
    with open(map_path, "w", encoding="utf-8", newline="") as f:
        f.write("part,local_task_id,global_task_id,job_id\n")
        f.writelines(f"{p},{l},{g},{j}\n" for p, l, g, j in map_rows)

    # ---- verify what was written, from disk
    seen_global, seen_job = [], set()
    with open(map_path, encoding="utf-8") as f:
        mp = list(csv.DictReader(f))
    for p, path in enumerate(part_files, 1):
        with open(path, encoding="utf-8") as f:
            plines = [l for l in f.read().splitlines(keepends=True) if l.strip()]
        with open(path[:-len(".tsv")] + ".tasks.csv", encoding="utf-8") as f:
            ptasks = list(csv.DictReader(f))
        assert 1 <= len(plines) <= a.max_tasks, (path, len(plines))
        pm = [r for r in mp if int(r["part"]) == p]
        assert len(pm) == len(plines) == len(ptasks)
        for local, (l, t, r) in enumerate(zip(plines, ptasks, pm), 1):
            g = int(r["global_task_id"])
            assert int(r["local_task_id"]) == int(t["task_id"]) == local
            assert int(t["global_task_id"]) == g
            assert l == lines[g - 1], f"{path}:{local} != full line {g}"
            assert r["job_id"] == t["job_id"] == l.split("\t", 1)[0]
            seen_global.append(g)
            seen_job.add(r["job_id"])
        keys = {(t["instance_sha256"], t["solver_seed"]) for t in ptasks}
        for q, other in enumerate(part_files, 1):
            if q != p:
                with open(other[:-len(".tsv")] + ".tasks.csv", encoding="utf-8") as f:
                    assert not keys & {(t["instance_sha256"], t["solver_seed"]) for t in csv.DictReader(f)}, \
                        "an (instance, seed) pair is split across parts"
    assert seen_global == list(range(1, n_rows + 1)), "parts do not cover the manifest in order"
    assert len(seen_job) == n_rows

    thr = TOTAL_CONCURRENCY // n
    print(f"{a.manifest}: {n_rows} rows > limit {a.max_tasks} -> {n} parts "
          f"({', '.join(str(e - s) for s, e in bounds)} rows); verified")
    for p, (s, e) in enumerate(bounds, 1):
        print(f"  part {p}: scripts/parts/{stem}.part{p}of{n}.tsv  local 1-{e - s}  = global {s + 1}-{e}")
    print(f"  map: {map_path}")
    print(f"  submit all {n} together with THROTTLE={thr} each (total {thr * n} <= {TOTAL_CONCURRENCY})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
