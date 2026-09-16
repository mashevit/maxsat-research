# src/bench/make_mse16_manifest.py
"""
Sample the MSE-2016 `ms_random` / `ms_crafted` corpus in `more_data/`, stage the
chosen instances into `cluster_staging_maxsat/data/mse16/`, and emit the SLURM
array manifest for the RC2 hardness screen.

Why a separate generator from `make_tier2_manifest.py`: that one reads RC2
profiles and emits *memetic jobs* (tier 2 is its input). This one runs one step
earlier -- it picks which instances get profiled by RC2 at all, which is what
decides tier membership in the first place (docs/archive/RC2_STATUS.md §0).

Sampling is stratified *within* each leaf directory by clause count, so a sample
of k spans that directory's density range instead of clustering at one end --
`maxcut/dimacs-mod` alone runs m/n from 1.1 to 57.0, and taking the first k
files alphabetically would miss that entirely.

The output path layout drops the doubled directory level in the download
(`more_data/ms_crafted/ms_crafted/...` -> `data/mse16/ms_crafted/...`).

Typical use -- screen 5 per leaf directory:

    python -m src.bench.make_mse16_manifest --k 5 --run-name screen

then, once the screen says which directories yield tier 2, fill those out
without re-picking what you already ran:

    python -m src.bench.make_mse16_manifest \
        --k 45 --run-name fill \
        --only 'maxcut/dimacs-mod' 'maxcut/spinglass' \
        --exclude sample_mse16_screen.csv

Outputs (all under --out-dir, default cluster_staging_maxsat/scripts):
  manifest_mse16_<run>.txt   one instance path per line, relative to the
                             staging root; line N == SLURM array task N
  sample_mse16_<run>.csv     provenance: sha256 + structural census per pick
  census_mse16.csv           structural census of every instance in the corpus
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List

CENSUS_COLUMNS = [
    "family", "file", "sha256", "fmt", "n_vars", "n_clauses", "n_vars_used",
    "ratio", "len_min", "len_max", "len_mean", "len_hist", "all_w1", "size_kb",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def census_one(path: Path, root: Path) -> Dict[str, Any]:
    """Structural census of one DIMACS file.

    MSE unweighted-MaxSAT convention: `p cnf` means every clause is soft at
    weight 1 and there are no hard clauses -- the same reading `src/sat/cnf.py`
    and `run_opt_rc2.cnf_to_all_soft_wcnf` apply. `p wcnf` is parsed too so the
    census still works if weighted variants are dropped in later.
    """
    fmt = None
    n_vars = 0
    lens: collections.Counter = collections.Counter()
    seen_vars: set[int] = set()
    weights: set[int] = set()
    n_clauses = 0

    with open(path, errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line[0] in "c%":
                continue
            if line.startswith("p"):
                toks = line.split()
                fmt = toks[1].lower()
                n_vars = int(toks[2])
                continue
            toks = line.split()
            if fmt == "wcnf":
                weights.add(int(toks[0]))
                lits = [int(x) for x in toks[1:] if x != "0"]
            else:
                weights.add(1)
                lits = [int(x) for x in toks if x != "0"]
            if not lits:
                continue
            n_clauses += 1
            lens[len(lits)] += 1
            seen_vars.update(abs(l) for l in lits)

    return {
        "family": str(path.parent.relative_to(root)),
        "file": path.name,
        "sha256": sha256_file(path),
        "fmt": fmt,
        "n_vars": n_vars,
        "n_clauses": n_clauses,
        "n_vars_used": len(seen_vars),
        "ratio": round(n_clauses / max(n_vars, 1), 3),
        "len_min": min(lens) if lens else 0,
        "len_max": max(lens) if lens else 0,
        "len_mean": round(sum(k * v for k, v in lens.items()) / max(n_clauses, 1), 3),
        "len_hist": ";".join(f"{k}:{v}" for k, v in sorted(lens.items())),
        "all_w1": weights == {1},
        "size_kb": round(path.stat().st_size / 1024, 1),
    }


def build_census(root: Path) -> List[Dict[str, Any]]:
    return [census_one(p, root) for p in sorted(root.rglob("*.cnf"))]


def flatten_family(family: str) -> str:
    """`ms_crafted/ms_crafted/maxcut/dimacs-mod` -> `ms_crafted/maxcut/dimacs-mod`.

    The download nests the track directory twice; collapse the repeat so staged
    paths and the manifest's family field stay readable.
    """
    parts = family.split("/")
    if len(parts) >= 2 and parts[0] == parts[1]:
        parts = parts[1:]
    return "/".join(parts)


def stratified_pick(rows: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    """k instances spanning the directory's clause-count range.

    Sort by (n_clauses, file) -- the second key keeps this deterministic when
    sizes tie -- then take k evenly spaced positions including both ends. Ties
    at the same index collapse, so a directory can yield fewer than k; that is
    correct, it means the directory has fewer distinct sizes than requested.
    """
    rows = sorted(rows, key=lambda r: (r["n_clauses"], r["file"]))
    if len(rows) <= k:
        return rows
    idx = sorted({round(i * (len(rows) - 1) / (k - 1)) for i in range(k)})
    return [rows[i] for i in idx]


def main(argv: Iterable[str] | None = None) -> int:
    repo = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser(
        description="Sample MSE-2016 instances and emit the RC2 screen manifest.")
    ap.add_argument("--corpus", type=Path, default=repo / "more_data",
                    help="root of the downloaded MSE-2016 corpus")
    ap.add_argument("--staging", type=Path,
                    default=repo / "cluster_staging_maxsat",
                    help="staging root; instances are copied under its data/")
    ap.add_argument("--out-dir", type=Path, default=None,
                    help="where manifests go (default <staging>/scripts)")
    ap.add_argument("--run-name", default="screen",
                    help="names the manifest and the sample CSV")
    ap.add_argument("--k", type=int, default=5,
                    help="instances per leaf directory")
    ap.add_argument("--only", nargs="*", default=None,
                    help="substrings; keep only leaf directories matching one")
    ap.add_argument("--exclude", type=Path, default=None,
                    help="a previous sample CSV; its sha256s are not re-picked")
    ap.add_argument("--no-stage", action="store_true",
                    help="write manifests but do not copy instances")
    args = ap.parse_args(list(argv) if argv is not None else None)

    out_dir = args.out_dir or (args.staging / "scripts")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.corpus.is_dir():
        raise SystemExit(f"corpus not found: {args.corpus}")

    census = build_census(args.corpus)
    if not census:
        raise SystemExit(f"no .cnf files under {args.corpus}")

    census_path = out_dir / "census_mse16.csv"
    with open(census_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CENSUS_COLUMNS)
        w.writeheader(); w.writerows(census)

    excluded: set[str] = set()
    if args.exclude and args.exclude.exists():
        with open(args.exclude, newline="") as f:
            excluded = {r["sha256"] for r in csv.DictReader(f)}

    by_dir: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    for r in census:
        if r["sha256"] in excluded:
            continue
        if args.only and not any(s in r["family"] for s in args.only):
            continue
        by_dir[r["family"]].append(r)

    if not by_dir:
        raise SystemExit("--only matched no leaf directory")

    picks: List[Dict[str, Any]] = []
    for family in sorted(by_dir):
        picks.extend(stratified_pick(by_dir[family], args.k))

    # Staged path: data/mse16/<flattened family>/<file>, relative to staging root
    # because that is the cwd the sbatch drops into before calling the profiler.
    for r in picks:
        r["staged"] = f"data/mse16/{flatten_family(r['family'])}/{r['file']}"

    if not args.no_stage:
        for r in picks:
            dst = args.staging / r["staged"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.corpus / r["family"] / r["file"], dst)

    manifest = out_dir / f"manifest_mse16_{args.run_name}.txt"
    with open(manifest, "w") as f:
        for r in picks:
            f.write(r["staged"] + "\n")

    sample_csv = out_dir / f"sample_mse16_{args.run_name}.csv"
    with open(sample_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CENSUS_COLUMNS + ["staged"])
        w.writeheader(); w.writerows(picks)

    print(f"corpus      {len(census)} instances, {len(by_dir)} leaf directories"
          f"{' (after --only/--exclude)' if args.only or excluded else ''}")
    print(f"sampled     {len(picks)} instances (k={args.k})")
    print(f"manifest    {manifest}  ->  #SBATCH --array=1-{len(picks)}%20")
    print(f"sample      {sample_csv}")
    print(f"census      {census_path}")
    if args.no_stage:
        print("staging     SKIPPED (--no-stage)")
    else:
        print(f"staged      {args.staging / 'data/mse16'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
