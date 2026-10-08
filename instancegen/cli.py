"""instancegen command line: grid files -> instances, manifest, Slurm manifest.

Plan: docs/CORPUS_CALIBRATION_GOALS.md §6 M1 (the generator plan's
INSTANCEGEN_PLAN §13 step "cli.py", narrowed to what the calibration needs).

    python -m instancegen.cli generate-grid --grid instancegen/grids/calib_a.yaml \
        --staging-root cluster_staging_maxsat

writes, under the staging root (the tree that is rsynced to the cluster):

    data/generated/<batch>/<instance>.wcnf      one file per (cell, seed)
    data/generated/<batch>/manifest.jsonl       one row per instance
    scripts/manifest_<batch>_rc2.txt            line N == Slurm array task N
    scripts/manifest_<batch>_rc2.sha256         `sha256sum -c` file, root-relative

Instance files are byte-reproducible from (GenParams, seed) (wcnf_io §12 test
1), so they stay out of git; the manifests are what is committed. `--check`
regenerates every instance in memory and compares it against the file on
disk and the manifest's sha without writing anything -- the post-rsync /
pre-commit sanity check.

Grid file shape (see instancegen/grids/calib_a.yaml):

    batch: calib_a
    dialect: old
    params: {hard_ratio: 0.0, w_max: 1, weight_dist: uniform}
    seeds: [1, 2, 3, 4, 5]
    families:
      - {family: max3sat, k: 3, n: [50, 70], alpha: [4.26, 5]}
      - {family: max2sat, k: 2, n: [150], alpha: [3], seeds: [6, 7, 8, 9, 10]}

A family entry may carry its own `seeds:`, which replaces the top-level list
for that entry's cells (the top-level list may then be omitted, if every entry
has one); that is how a refinement batch re-samples a cell an
earlier batch already ran (calib_b, docs/CALIB_B_PLAN.md §4b) without
regenerating the earlier seeds. Cell sizes are then unequal by design.

`alpha` is the soft clause density m/n and maps straight onto
GenParams.soft_ratio, so m = round(alpha * n) is what generate.py produces.

An optional top-level `generator:` picks the sampler. It defaults to
`weighted_ksat` (generate.generate, clauses drawn with replacement), which is
what calib_a/b/c use; their grid files do not name it and their manifests are
unchanged. `generator: ksat_distinct` selects generate.generate_distinct:
exactly m = round(alpha * n) distinct clauses, all soft, weight 1. Such a grid
has no `params:` block (there is nothing to set), must use dialect `old`, and
its manifest rows carry the distinct generator's name, its sampling method and
the rejected duplicate candidates (see instancegen/grids/calib_2sat_sc.yaml).

A second subcommand writes one instance from the distinct-clause mode
(generate.generate_distinct: exactly m distinct clauses, all soft, weight 1):

    python -m instancegen.cli generate-distinct --n 32000 --k 2 --m 38400 \
        --seed 1 --out-dir <dir>

It writes <dir>/ksat_distinct_v<n>_k<k>_m<m>_s<seed>.wcnf and a .json sidecar
whose `generator.name` is `ksat_distinct` (never `weighted_ksat`), then
re-reads the file and validates it (instancegen/validate.py).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import yaml

from instancegen import (
    DISTINCT_GENERATOR_NAME, DISTINCT_GENERATOR_VERSION, DISTINCT_SAMPLING,
    GENERATOR_NAME, GENERATOR_VERSION,
)
from instancegen.generate import (
    DistinctParams, GenParams, Instance, distinct_filename, generate,
    generate_distinct, instance_filename, n_possible_clauses,
)
from instancegen.validate import check_distinct_wcnf
from instancegen.wcnf_io import format_wcnf

MANIFEST_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Cell:
    family: str
    k: int
    n: int
    alpha: float
    seeds: Optional[tuple] = None  # None => the grid's top-level seeds

    @property
    def cell_id(self) -> str:
        return f"{self.family}_n{self.n}_a{self.alpha:g}"


@dataclass(frozen=True)
class Grid:
    batch: str
    dialect: str
    params: Dict[str, Any]
    seeds: List[int]
    cells: List[Cell]
    generator: str = GENERATOR_NAME

    @property
    def distinct(self) -> bool:
        return self.generator == DISTINCT_GENERATOR_NAME

    def gen_params(self, cell: Cell, seed: int):
        if self.distinct:
            # Same rounding as GenParams.n_soft, so alpha means the same thing
            # in both modes.
            return DistinctParams(n_vars=cell.n, k=cell.k,
                                  m=int(round(cell.alpha * cell.n)), seed=int(seed))
        return GenParams(
            n_vars=cell.n,
            k=cell.k,
            soft_ratio=float(cell.alpha),
            hard_ratio=float(self.params["hard_ratio"]),
            w_max=int(self.params["w_max"]),
            seed=int(seed),
            weight_dist=str(self.params["weight_dist"]),
        )

    def cell_seeds(self, cell: Cell) -> List[int]:
        """The cell's seeds: its own override, else the grid's top-level list.

        A per-family `seeds:` is how a refinement batch re-samples a cell that
        already exists in an earlier batch (calib_b §4b: seeds 6-10 on the five
        cells calib_a ran at seeds 1-5) without regenerating the earlier
        instances. Cell sizes are then unequal, which every downstream table
        has to state -- see docs/CALIB_B_PLAN.md §4b.
        """
        return list(cell.seeds) if cell.seeds is not None else list(self.seeds)

    def items(self) -> Iterator[tuple[Cell, int]]:
        """(cell, seed) in manifest order: families as listed, n, alpha, seed."""
        for cell in self.cells:
            for seed in self.cell_seeds(cell):
                yield cell, seed


def load_grid(path: str) -> Grid:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    generator = str(raw.get("generator", GENERATOR_NAME))
    if generator not in (GENERATOR_NAME, DISTINCT_GENERATOR_NAME):
        raise ValueError(f"grid {path}: unknown generator {generator!r}; expected "
                         f"{GENERATOR_NAME!r} or {DISTINCT_GENERATOR_NAME!r}")
    distinct = generator == DISTINCT_GENERATOR_NAME
    # Top-level `seeds` may be omitted when every family entry has its own
    # (calib_2sat_sc: one seed block per cell, so no two cells share a seed).
    required = ("batch", "dialect", "families") + (() if distinct else ("params",))
    for key in required:
        if key not in raw:
            raise ValueError(f"grid {path}: missing top-level key {key!r}")
    if distinct:
        if raw.get("params"):
            raise ValueError(f"grid {path}: generator {generator!r} takes no params "
                             "(every clause is soft with weight 1)")
        if raw["dialect"] != "old":
            raise ValueError(f"grid {path}: generator {generator!r} writes dialect 'old' only")
    else:
        for key in ("hard_ratio", "w_max", "weight_dist"):
            if key not in raw["params"]:
                raise ValueError(f"grid {path}: params missing {key!r}")

    def _seed_list(raw_seeds, where: str) -> List[int]:
        out = [int(s) for s in raw_seeds]
        if not out:
            raise ValueError(f"grid {path}: empty seeds in {where}")
        if len(set(out)) != len(out):
            raise ValueError(f"grid {path}: duplicate seeds {out} in {where}")
        return out

    seeds = _seed_list(raw["seeds"], "top level") if "seeds" in raw else []
    cells: List[Cell] = []
    for fam in raw["families"]:
        if "seeds" not in raw and "seeds" not in fam:
            raise ValueError(f"grid {path}: no top-level seeds, and family entry "
                             f"has none either: {fam}")
        for key in ("family", "k", "n", "alpha"):
            if key not in fam:
                raise ValueError(f"grid {path}: family entry missing {key!r}: {fam}")
        fam_seeds = (tuple(_seed_list(fam["seeds"], f"family {fam.get('family')!r}"))
                     if "seeds" in fam else None)
        for n in fam["n"]:
            for alpha in fam["alpha"]:
                cells.append(Cell(str(fam["family"]), int(fam["k"]), int(n),
                                  float(alpha), fam_seeds))
    ids = [c.cell_id for c in cells]
    if len(set(ids)) != len(ids):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"grid {path}: duplicate cells {dup}")
    return Grid(
        batch=str(raw["batch"]),
        dialect=str(raw["dialect"]),
        params=dict(raw.get("params") or {}),
        seeds=seeds,
        cells=cells,
        generator=generator,
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_sha() -> Optional[str]:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def render_full(grid: Grid, cell: Cell, seed: int):
    """(params, instance, filename, wcnf bytes, rejected) for one instance.

    `rejected` is the distinct mode's tuple of rejected duplicate candidates,
    None for weighted_ksat. Pure; no I/O.
    """
    p = grid.gen_params(cell, seed)
    if grid.distinct:
        res = generate_distinct(p)
        inst, name, rejected = res.instance, distinct_filename(p), res.rejected
    else:
        inst, name, rejected = generate(p), instance_filename(p), None
    text = format_wcnf(inst, dialect=grid.dialect)
    return p, inst, name, text.encode("utf-8"), rejected


def render(grid: Grid, cell: Cell, seed: int) -> tuple[Any, Instance, str, bytes]:
    """(params, instance, filename, wcnf bytes) for one instance. Pure; no I/O."""
    return render_full(grid, cell, seed)[:4]


def manifest_row(
    grid: Grid, cell: Cell, seed: int, p, inst: Instance, rel_path: str,
    data: bytes, *, sha: str, git: Optional[str], created_utc: str,
    rejected: Optional[tuple] = None,
) -> Dict[str, Any]:
    if grid.distinct:
        return _distinct_manifest_row(grid, cell, seed, p, inst, rel_path, data,
                                      sha=sha, git=git, created_utc=created_utc,
                                      rejected=rejected or ())
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "batch": grid.batch,
        "cell_id": cell.cell_id,
        "family": cell.family,
        "k": cell.k,
        "n": cell.n,
        "alpha": cell.alpha,
        "m": p.n_soft,
        "seed": seed,
        "instance": rel_path,
        "instance_sha256": sha,
        "dialect": grid.dialect,
        "generator": {
            "name": GENERATOR_NAME,
            "version": GENERATOR_VERSION,
            "params": asdict(p),
        },
        "sizes": {
            "n_vars": inst.n_vars,
            "n_clauses": len(inst.clauses),
            "n_hard": len(inst.hard_clauses),
            "n_soft": len(inst.soft_clauses),
            "clause_ratio": p.clause_ratio,
            "total_soft_weight": inst.total_soft_weight,
            "n_distinct_weights": inst.n_distinct_weights,
            "bytes": len(data),
        },
        "git_sha": git,
        "created_utc": created_utc,
    }


def _distinct_manifest_row(
    grid: Grid, cell: Cell, seed: int, p: DistinctParams, inst: Instance,
    rel_path: str, data: bytes, *, sha: str, git: Optional[str], created_utc: str,
    rejected: tuple,
) -> Dict[str, Any]:
    """Same keys as a weighted_ksat row where they mean the same thing, plus the
    sampling method, the clause-space size and the rejection record."""
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "batch": grid.batch,
        "cell_id": cell.cell_id,
        "family": cell.family,
        "k": cell.k,
        "n": cell.n,
        "alpha": cell.alpha,
        "m": p.m,
        "seed": seed,
        "instance": rel_path,
        "instance_sha256": sha,
        "dialect": grid.dialect,
        "generator": {
            "name": DISTINCT_GENERATOR_NAME,
            "version": DISTINCT_GENERATOR_VERSION,
            "sampling": DISTINCT_SAMPLING,
            "params": asdict(p),
        },
        "sizes": {
            "n_vars": inst.n_vars,
            "n_clauses": len(inst.clauses),
            "n_hard": len(inst.hard_clauses),
            "n_soft": len(inst.soft_clauses),
            "clause_ratio": p.m / p.n_vars,
            "total_soft_weight": inst.total_soft_weight,
            "n_distinct_weights": inst.n_distinct_weights,
            "bytes": len(data),
        },
        "clause_space": n_possible_clauses(p.n_vars, p.k),
        "n_candidates_drawn": p.m + len(rejected),
        "n_rejected_duplicates": len(rejected),
        "rejected_duplicates": [list(c) for c in rejected],
        "python": platform.python_version(),
        "git_sha": git,
        "created_utc": created_utc,
    }


def _paths(args: argparse.Namespace, grid: Grid) -> tuple[Path, Path, Path, Path]:
    root = Path(args.staging_root)
    out_dir = Path(args.out) if args.out else root / "data" / "generated" / grid.batch
    slurm = (Path(args.slurm_manifest) if args.slurm_manifest
             else root / "scripts" / f"manifest_{grid.batch}_rc2.txt")
    sha_file = slurm.with_suffix(".sha256")
    return root, out_dir, slurm, sha_file


def _rel(root: Path, path: Path) -> str:
    """Path relative to the staging root, with forward slashes (the form the
    Slurm drivers read after `cd ..`)."""
    return os.path.relpath(path, root).replace(os.sep, "/")


def cmd_generate_grid(args: argparse.Namespace) -> int:
    grid = load_grid(args.grid)
    root, out_dir, slurm, sha_file = _paths(args, grid)
    items = list(grid.items())
    names = [render(grid, c, s)[2] for c, s in items]
    if len(set(names)) != len(names):
        raise SystemExit(f"grid yields duplicate filenames: {len(names) - len(set(names))}")

    if args.check:
        return _check(grid, items, out_dir, root, slurm, sha_file)

    out_dir.mkdir(parents=True, exist_ok=True)
    slurm.parent.mkdir(parents=True, exist_ok=True)
    git = git_sha()
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    rows: List[Dict[str, Any]] = []
    rel_paths: List[str] = []
    shas: List[str] = []
    n_written = n_same = 0
    n_invalid = 0
    for cell, seed in items:
        p, inst, name, data, rejected = render_full(grid, cell, seed)
        if grid.distinct:
            # Validate the bytes about to be written, independently of the
            # generator objects; a violation stops the batch before any manifest.
            rep_ = check_distinct_wcnf(data.decode("utf-8"), n=p.n_vars, k=p.k, m=p.m)
            if not rep_["ok"]:
                n_invalid += 1
                print(f"VALIDATION FAILED {name}: {rep_['problems'][:5]}", file=sys.stderr)
                continue
        path = out_dir / name
        if path.exists() and path.read_bytes() == data:
            n_same += 1
        else:
            path.write_bytes(data)
            n_written += 1
        sha = sha256_bytes(data)
        rel = _rel(root, path)
        rows.append(manifest_row(grid, cell, seed, p, inst, rel, data,
                                 sha=sha, git=git, created_utc=created,
                                 rejected=rejected))
        rel_paths.append(rel)
        shas.append(sha)

    if n_invalid:
        raise SystemExit(f"{n_invalid} instance(s) failed validation; no manifest written")

    manifest = out_dir / "manifest.jsonl"
    with open(manifest, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=False) + "\n")
    with open(slurm, "w", encoding="utf-8", newline="\n") as f:
        for rel in rel_paths:
            f.write(rel + "\n")
    with open(sha_file, "w", encoding="utf-8", newline="\n") as f:
        for sha, rel in zip(shas, rel_paths):
            f.write(f"{sha}  {rel}\n")

    seed_sizes = sorted({len(grid.cell_seeds(c)) for c in grid.cells})
    if grid.distinct:
        n_rej = sum(r["n_rejected_duplicates"] for r in rows)
        print(f"generator={grid.generator}: all {len(rows)} files validated; "
              f"{n_rej} duplicate candidates rejected in total")
    print(f"batch={grid.batch} cells={len(grid.cells)} "
          f"seeds/cell={','.join(str(x) for x in seed_sizes)} "
          f"instances={len(rows)} written={n_written} unchanged={n_same}")
    print(f"instances : {out_dir}")
    print(f"manifest  : {manifest}")
    print(f"slurm     : {slurm}  (line N == array task N)")
    print(f"sha256    : {sha_file}  (cd {root} && sha256sum -c {_rel(root, sha_file)})")
    print(f"git_sha   : {git}")
    return 0


def _check(grid: Grid, items, out_dir: Path, root: Path, slurm: Path, sha_file: Path) -> int:
    """Regenerate in memory; compare against files, manifest and Slurm manifest."""
    problems: List[str] = []
    manifest = out_dir / "manifest.jsonl"
    rows: Dict[str, Dict[str, Any]] = {}
    if manifest.exists():
        with open(manifest, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    rows[r["instance"]] = r
    else:
        problems.append(f"missing manifest {manifest}")
    slurm_lines: List[str] = []
    if slurm.exists():
        slurm_lines = [l.strip() for l in slurm.read_text().splitlines() if l.strip()]
    else:
        problems.append(f"missing slurm manifest {slurm}")

    expected_rel: List[str] = []
    for cell, seed in items:
        p, _inst, name, data = render(grid, cell, seed)
        path = out_dir / name
        rel = _rel(root, path)
        expected_rel.append(rel)
        sha = sha256_bytes(data)
        if not path.exists():
            problems.append(f"missing file {rel}")
        elif path.read_bytes() != data:
            problems.append(f"bytes differ {rel}")
        row = rows.get(rel)
        if row is None:
            if manifest.exists():
                problems.append(f"no manifest row for {rel}")
        elif row.get("instance_sha256") != sha:
            problems.append(f"manifest sha mismatch {rel}")
        elif row.get("generator", {}).get("params") != asdict(p):
            problems.append(f"manifest params mismatch {rel}")
    extra = set(rows) - set(expected_rel)
    if extra:
        problems.append(f"{len(extra)} manifest rows not in grid: {sorted(extra)[:3]}...")
    if slurm_lines and slurm_lines != expected_rel:
        problems.append("slurm manifest order/content differs from grid order")

    n = len(expected_rel)
    if problems:
        print(f"CHECK FAILED: {len(problems)} problem(s) over {n} instances")
        for pr in problems[:50]:
            print("  " + pr)
        return 1
    print(f"CHECK OK: {n} instances, manifest and slurm manifest match the grid "
          f"({grid.batch})")
    return 0


def cmd_generate_distinct(args: argparse.Namespace) -> int:
    p = DistinctParams(n_vars=args.n, k=args.k, m=args.m, seed=args.seed)
    t0 = time.perf_counter()
    try:
        res = generate_distinct(p)
    except ValueError as e:
        raise SystemExit(f"generate-distinct: {e}")
    t1 = time.perf_counter()
    data = format_wcnf(res.instance, dialect="old").encode("utf-8")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / distinct_filename(p)
    path.write_bytes(data)
    t2 = time.perf_counter()

    report = check_distinct_wcnf(path.read_text(encoding="utf-8"),
                                 n=p.n_vars, k=p.k, m=p.m)
    t3 = time.perf_counter()
    row = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "instance": path.name,
        "instance_sha256": sha256_bytes(data),
        "dialect": "old",
        "generator": {
            "name": DISTINCT_GENERATOR_NAME,
            "version": DISTINCT_GENERATOR_VERSION,
            "sampling": DISTINCT_SAMPLING,
            "params": asdict(p),
        },
        "sizes": {
            "n_vars": p.n_vars,
            "n_clauses": len(res.instance.clauses),
            "n_hard": 0,
            "n_soft": len(res.instance.clauses),
            "clause_ratio": p.m / p.n_vars,
            "total_soft_weight": res.instance.total_soft_weight,
            "n_distinct_weights": res.instance.n_distinct_weights,
            "bytes": len(data),
        },
        "clause_space": n_possible_clauses(p.n_vars, p.k),
        "n_candidates_drawn": p.m + len(res.rejected),
        "n_rejected_duplicates": len(res.rejected),
        "rejected_duplicates": [list(c) for c in res.rejected],
        "validation": {k: v for k, v in report.items() if k != "problems"},
        # rng.sample's algorithm is a CPython detail; byte-identity is
        # guaranteed for a fixed interpreter version.
        "python": platform.python_version(),
        "git_sha": git_sha(),
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    sidecar = path.with_suffix(".json")
    with open(sidecar, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, indent=1) + "\n")

    print(f"instance  : {path}  ({len(data)} bytes, sha256 {row['instance_sha256'][:16]}...)")
    print(f"metadata  : {sidecar}")
    print(f"clauses   : {p.m} accepted, {len(res.rejected)} duplicate candidates rejected")
    print(f"timing    : generate {t1 - t0:.3f} s, format+write {t2 - t1:.3f} s, "
          f"validate {t3 - t2:.3f} s")
    if not report["ok"]:
        print(f"VALIDATION FAILED: {len(report['problems'])} problem(s)")
        for pr in report["problems"][:50]:
            print("  " + pr)
        return 1
    print("VALIDATION OK")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m instancegen.cli", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate-grid", help="grid yaml -> instances + manifests")
    g.add_argument("--grid", required=True, help="grid yaml (instancegen/grids/*.yaml)")
    g.add_argument("--staging-root", default="cluster_staging_maxsat",
                   help="tree the cluster runs from; instance paths in the Slurm "
                        "manifest are relative to it (default: %(default)s)")
    g.add_argument("--out", default=None,
                   help="instance dir (default <staging-root>/data/generated/<batch>)")
    g.add_argument("--slurm-manifest", default=None,
                   help="Slurm manifest path (default <staging-root>/scripts/"
                        "manifest_<batch>_rc2.txt); .sha256 goes beside it")
    g.add_argument("--check", action="store_true",
                   help="verify files/manifests against the grid; write nothing")
    g.set_defaults(func=cmd_generate_grid)
    d = sub.add_parser("generate-distinct",
                       help="one instance with exactly m distinct clauses (weight 1)")
    d.add_argument("--n", type=int, required=True, help="number of variables")
    d.add_argument("--k", type=int, required=True, help="literals per clause")
    d.add_argument("--m", type=int, required=True, help="number of distinct clauses")
    d.add_argument("--seed", type=int, required=True)
    d.add_argument("--out-dir", required=True)
    d.set_defaults(func=cmd_generate_distinct)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
