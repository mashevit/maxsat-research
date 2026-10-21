#!/usr/bin/env python3
"""Copy the files a batch needs and the cluster lacks into ONE flat folder, for an
upload without rsync (MobaXterm drag and drop). Workstation only.

    python3 scripts/make_flat_upload.py --out ../tmp/upload_x \
        --need scripts/manifest_under30.upload.sha256 --need scripts/manifest_hardmse.upload.sha256 \
        --have 097efb7:scripts/manifest_oracle900.upload.sha256 --have 097efb7:scripts/manifest_ks2check.upload.sha256

--need   upload hash lists ("<sha256>  <tree path>") of the batches to run; the
         lists themselves are uploaded too.
--have   hash lists already verified on the cluster (sha256sum -c UPLOAD_OK).
         "<rev>:<path>" reads the list as committed at <rev> (git show), so a
         list regenerated since then does not count as uploaded. An earlier
         UPLOAD_MAP.tsv (flat name, tree path, sha256) is read as well.
--prefix     put before every flat name (a second upload into the same folder
             then cannot overwrite the first one's files).
--map-name   name of the map file (default UPLOAD_MAP.tsv).
A needed path is skipped only when a --have list holds the same path with the
same hash. Every other file is copied under its basename; when two needed
files share a basename, each gets a "<n>__" prefix. UPLOAD_MAP.tsv
(flat name, tree path, sha256) goes into the folder: the arrange script that
moves the files into ~/cluster_staging_maxsat_strong/ is written from it.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_list(spec: str) -> dict:
    """{tree path: sha256} from a hash list on disk, or from git with "<rev>:<path>"."""
    if ":" in spec and not os.path.exists(os.path.join(ROOT, spec)):
        rev, path = spec.split(":", 1)
        rel = os.path.relpath(os.path.join(ROOT, path), subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
        text = subprocess.check_output(["git", "show", f"{rev}:{rel}"], cwd=ROOT, text=True)
    else:
        text = open(os.path.join(ROOT, spec), encoding="utf-8").read()
    out = {}
    for line in text.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) == 3:                                   # UPLOAD_MAP.tsv
            out[parts[1]] = parts[2].strip()
        else:
            h, p = line.split(None, 1)
            out[p.strip()] = h
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="new, empty folder to fill")
    ap.add_argument("--need", action="append", required=True)
    ap.add_argument("--have", action="append", default=[])
    ap.add_argument("--prefix", default="")
    ap.add_argument("--map-name", default="UPLOAD_MAP.tsv")
    a = ap.parse_args(argv)
    have = {}
    for spec in a.have:
        have.update(read_list(spec))
    need = {}
    for spec in a.need:
        for p, h in read_list(spec).items():
            if need.setdefault(p, h) != h:
                raise SystemExit(f"FATAL: two need lists disagree on {p}")
        need[spec] = sha256(os.path.join(ROOT, spec))     # the list itself
    for p, h in need.items():
        if sha256(os.path.join(ROOT, p)) != h:
            raise SystemExit(f"FATAL: {p} changed since its hash list was written; rerun the manifest builder")
    todo = sorted(p for p, h in need.items() if have.get(p) != h)
    if os.path.exists(a.out) and os.listdir(a.out):
        raise SystemExit(f"FATAL: {a.out} is not empty")
    os.makedirs(a.out, exist_ok=True)
    by_base = {}
    for p in todo:
        by_base.setdefault(os.path.basename(p), []).append(p)
    rows, size = [], 0
    for base, ps in sorted(by_base.items()):
        for i, p in enumerate(ps, 1):
            flat = a.prefix + (base if len(ps) == 1 else f"{i}__{base}")
            shutil.copy2(os.path.join(ROOT, p), os.path.join(a.out, flat))
            size += os.path.getsize(os.path.join(a.out, flat))
            rows.append((flat, p, need[p]))
    with open(os.path.join(a.out, a.map_name), "w", encoding="utf-8", newline="\n") as f:
        f.write("# flat_name\ttree_path (relative to ~/cluster_staging_maxsat_strong)\tsha256\n")
        f.writelines(f"{fl}\t{p}\t{h}\n" for fl, p, h in sorted(rows, key=lambda r: r[1]))
    dup = sum(1 for ps in by_base.values() if len(ps) > 1)
    print(f"{len(rows)} files ({size / 1e6:.1f} MB) -> {a.out}; {len(need) - len(todo)} needed paths "
          f"already on the cluster; {dup} shared basenames prefixed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
