"""
Build structural metadata for MaxSAT/SAT instances for LLM-aided LoRA training.

Inputs : a .cnf / .wcnf file, or a directory of them.
Outputs: <file>.meta.json next to each instance, plus a combined metadata.jsonl
         index. Pure-parse features only (no solver), so safe to run on a whole
         benchmark folder.

Usage:
    python -m src.cli.make_metadata --input data/toy
    python -m src.cli.make_metadata --input data/dev_small --jsonl data/dev_small/metadata.jsonl
    python -m src.cli.make_metadata --input data/exp0 --recursive
    python -m src.cli.make_metadata --input data/toy/mini.wcnf --stdout
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable, List

from ..sat.metadata import compute_metadata_from_path


DEFAULT_EXTS = (".cnf", ".wcnf")


def _iter_instances(root: Path, exts: tuple, recursive: bool) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    if not root.is_dir():
        raise FileNotFoundError(f"Not a file or directory: {root}")
    it = root.rglob("*") if recursive else root.iterdir()
    for p in sorted(it):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def _meta_path_for(instance: Path, out_dir: Path | None) -> Path:
    if out_dir is None:
        return instance.with_suffix(instance.suffix + ".meta.json")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / (instance.name + ".meta.json")


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="make_metadata",
        description="Generate structural metadata for MaxSAT/SAT instances.",
    )
    ap.add_argument("--input", "-i", required=True,
                    help="Path to a .cnf/.wcnf file or a directory of instances.")
    ap.add_argument("--recursive", "-r", action="store_true",
                    help="Recurse into subdirectories.")
    ap.add_argument("--ext", action="append", default=None,
                    help="Extension to include (repeatable). Default: .cnf .wcnf")
    ap.add_argument("--out-dir", default=None,
                    help="Directory for per-instance .meta.json files. "
                         "Default: alongside each instance.")
    ap.add_argument("--jsonl", default=None,
                    help="Path to write combined JSONL index. "
                         "Default: metadata.jsonl in the input's folder "
                         "(the directory itself, or the file's parent).")
    ap.add_argument("--no-jsonl", action="store_true",
                    help="Skip writing the combined JSONL index.")
    ap.add_argument("--no-per-file", action="store_true",
                    help="Skip writing per-instance .meta.json (only the JSONL).")
    ap.add_argument("--no-sha", action="store_true",
                    help="Skip SHA-256 (faster on huge benchmarks).")
    ap.add_argument("--stdout", action="store_true",
                    help="Also print each metadata record to stdout.")
    ap.add_argument("--quiet", "-q", action="store_true",
                    help="Suppress per-file progress logging.")
    args = ap.parse_args(argv)

    root = Path(args.input).resolve()
    exts = tuple(e.lower() if e.startswith(".") else "." + e.lower()
                 for e in (args.ext or DEFAULT_EXTS))
    out_dir = Path(args.out_dir).resolve() if args.out_dir else None

    if args.no_jsonl:
        jsonl_path = None
    elif args.jsonl:
        jsonl_path = Path(args.jsonl).resolve()
    elif root.is_dir():
        jsonl_path = root / "metadata.jsonl"
    else:
        jsonl_path = root.parent / "metadata.jsonl"

    instances = list(_iter_instances(root, exts, args.recursive))
    if not instances:
        print(f"[make_metadata] no instances found under {root}", file=sys.stderr)
        return 2

    n_ok = 0
    n_err = 0
    t0 = time.perf_counter()
    jsonl_fp = None
    if jsonl_path is not None:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        jsonl_fp = open(jsonl_path, "w", encoding="utf-8")

    try:
        for inst_path in instances:
            try:
                md = compute_metadata_from_path(
                    str(inst_path),
                    include_file_info=True,
                )
                if args.no_sha and "file" in md:
                    md["file"].pop("sha256", None)
            except Exception as e:
                n_err += 1
                if not args.quiet:
                    print(f"[make_metadata] FAIL {inst_path}: {e}", file=sys.stderr)
                continue

            if not args.no_per_file:
                meta_path = _meta_path_for(inst_path, out_dir)
                with open(meta_path, "w", encoding="utf-8") as fp:
                    json.dump(md, fp, indent=2, sort_keys=False)
                    fp.write("\n")

            if jsonl_fp is not None:
                jsonl_fp.write(json.dumps(md, sort_keys=False) + "\n")

            if args.stdout:
                print(json.dumps(md, sort_keys=False))

            n_ok += 1
            if not args.quiet:
                sz = md["sizes"]
                print(
                    f"[make_metadata] OK  {inst_path.name}  "
                    f"vars={sz['n_vars']}  clauses={sz['n_clauses']}  "
                    f"hard={sz['n_hard']}  soft={sz['n_soft']}",
                    file=sys.stderr,
                )
    finally:
        if jsonl_fp is not None:
            jsonl_fp.close()

    dt = time.perf_counter() - t0
    print(
        f"[make_metadata] done: {n_ok} ok, {n_err} failed, {dt:.2f}s"
        + (f"  jsonl={jsonl_path}" if jsonl_path else ""),
        file=sys.stderr,
    )
    return 0 if n_err == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
