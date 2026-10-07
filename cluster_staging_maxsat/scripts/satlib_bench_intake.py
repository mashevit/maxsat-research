#!/usr/bin/env python3
"""Intake of the SATLIB benchmark families in data/satlib_bench/: label, normalise, verify, list.

Plan and findings: docs/current/SATLIB_BENCH_INTAKE.md (repo).

SOURCE OF TRUTH. The untouched SATLIB files are kept in a tarball
(default data/raw/satlib_bench_original_20261007.tar.gz). Every run re-derives
everything from the tarball, so the script is idempotent and --check can tell
whether the files on disk are exactly the normalised ones.

WHY NORMALISE. RC2 reads instances with PySAT's CNF reader (via
src.cli.run_opt_rc2.load_as_wcnf), which is LINE-based: every non-comment line
is a clause and a line holding only "0" is an EMPTY clause. Empty soft clauses
are always falsified, so each one adds 1 to the optimum. The memetic solver
reads with src.sat.cnf.WCNF.parse_dimacs, which skips "%" and lines starting
with "0". On the original files the two readers disagree:

    uuf200 / uuf225   "%" then "0" trailer     PySAT: m+2 clauses, 2 empty -> c* inflated by 2
    pret*             trailing lone "0" line   PySAT: m+1 clauses, 1 empty -> c* inflated by 1
    hole9             last clause split, "0" on its own line   PySAT: 1 empty clause
    dubois100         202 clause lines lack the terminating 0  PySAT takes the last token as the
                      terminator and silently DROPS a literal from each ("199 200 1" -> [199, 200]);
                      a strict token reader merges them into 6-literal clauses (598, not 800)
    bf*               tab separators           harmless for both readers

The normalised file has one clause per line, single spaces, every clause
0-terminated, no "%" trailer, and the original comment block kept verbatim
(plus one "c normalized ..." line naming what changed). Every reader then agrees.

HOW A FILE IS PARSED (original, from the tarball). Data ends at a line
starting with "%" (SATLIB convention). Two readings are tried, and the first
that yields exactly the header's m non-empty clauses over variables 1..n wins:
  A. token stream (strict DIMACS): clauses end at a 0 token, across lines;
     a final empty clause from a lone trailing "0" line is dropped;
  B. line-based: every non-empty data line is one clause, a missing final 0 is
     supplied, lone "0" lines are dropped (needed for dubois100 only).
No reading matching the header is a hard error: nothing is guessed.
The winning clause list must also equal what the memetic reader gets from the
ORIGINAL file (an independent check), and after rewriting, PySAT's reader, the
memetic reader and the strict token reader must all return that same list.

SATISFIABILITY LABEL (from file content; RC2 is never run for this):
  1. "c NOTE: Not satisfiable" / "c NOTE: Satisfiable"  (dubois, hole, jnh)
  2. pret's generator field "Charge ( 0 = sat. / 1 = unsat. ) ==> 1"
  3. family convention: uuf* = "uniform random 3-SAT, unsatisfiable" (SATLIB)
  4. family convention: bf* = bridge-fault circuit instances, all unsatisfiable
     (SATLIB DIMACS set; the files carry no note)
--sat-check-s S additionally runs a plain SAT solver (CaDiCaL 1.5.3 via PySAT,
S seconds per file) as a cross-check. A solver SAT answer on an "unsat" label
is a hard error; a timeout leaves the label as it is and is recorded.

OUTPUTS (with --write)
    data/satlib_bench/<family>/...cnf          normalised in place
    data/satlib_bench/manifest.jsonl           one row per file, all files
    scripts/manifest_satlib_rc2.txt            every unsat file, all families, one RC2 array (batch "satlib")
    scripts/manifest_satlib_rc2.sha256         `sha256sum -c` list for it

    python3 scripts/satlib_bench_intake.py                      # report only, writes nothing
    python3 scripts/satlib_bench_intake.py --sat-check-s 60 --write
    python3 scripts/satlib_bench_intake.py --check              # exit 3 if disk != normalised
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import io
import json
import os
import re
import sys
import tarfile
import tempfile
import threading
import time
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
STAGING = os.path.dirname(HERE)
sys.path.insert(0, STAGING)

DEFAULT_TAR = "data/raw/satlib_bench_original_20261007.tar.gz"
BENCH = "data/satlib_bench"
MANIFEST = f"{BENCH}/manifest.jsonl"
RC2_LISTS = {"satlib": "scripts/manifest_satlib_rc2"}  # one array over every unsat file (user, 2026-10-07)

# directory name -> family label used in the manifest
FAMILY_DIRS = {
    "bf": "bf",
    "dubois": "dubois",
    "jnh": "jnh",
    "pigeon-hole": "hole",
    "pret": "pret",
    "uuf200-860": "uuf200",
    "uuf225-960": "uuf225",
}

Clause = Tuple[int, ...]


# ----------------------------------------------------------------------------
# parsing and normalisation (pure functions; tested in tests/test_satlib_bench_intake.py)

def split_sections(text: str) -> Tuple[List[str], Tuple[int, int], List[str], Optional[List[str]]]:
    """Return (comment lines, (n, m), data lines, lines after the % marker or None if no marker)."""
    comments: List[str] = []
    header: Optional[Tuple[int, int]] = None
    data: List[str] = []
    trailer: List[str] = []
    in_trailer = False
    for raw in text.splitlines():
        s = raw.strip()
        if in_trailer:
            if s:
                trailer.append(s)
            continue
        if not s:
            continue
        if s.startswith("c"):
            comments.append(raw.rstrip())
            continue
        if s.startswith("p"):
            toks = s.split()
            if len(toks) != 4 or toks[1] != "cnf":
                raise ValueError(f"unsupported problem line: {s!r}")
            if header is not None:
                raise ValueError("second problem line")
            header = (int(toks[2]), int(toks[3]))
            continue
        if s.startswith("%"):
            in_trailer = True
            continue
        if header is None:
            raise ValueError(f"clause data before the problem line: {s[:60]!r}")
        data.append(s)
    if header is None:
        raise ValueError("no problem line")
    return comments, header, data, (trailer if in_trailer else None)


def read_tokens(data: List[str]) -> Tuple[List[Clause], List[str]]:
    """Strict DIMACS: a clause ends at a 0 token, possibly on a later line."""
    clauses: List[Clause] = []
    notes: List[str] = []
    cur: List[int] = []
    for s in data:
        for t in s.split():
            v = int(t)
            if v == 0:
                clauses.append(tuple(cur))
                cur = []
            else:
                cur.append(v)
    if cur:
        raise ValueError(f"token stream ends inside a clause: {cur[:6]}")
    if clauses and not clauses[-1] and data and data[-1].split() == ["0"]:
        clauses.pop()
        notes.append("dropped stray trailing '0' line (read as an empty clause by PySAT)")
    return clauses, notes


def read_lines(data: List[str]) -> Tuple[List[Clause], List[str]]:
    """Line-based: one clause per line, missing terminator supplied."""
    clauses: List[Clause] = []
    unterminated = 0
    dropped_zero = 0
    for s in data:
        toks = [int(t) for t in s.split()]
        if toks == [0]:
            dropped_zero += 1
            continue
        if toks[-1] == 0:
            toks = toks[:-1]
        else:
            unterminated += 1
        if any(t == 0 for t in toks):
            raise ValueError(f"line-based read: 0 inside a line: {s[:60]!r}")
        clauses.append(tuple(toks))
    notes = []
    if unterminated:
        notes.append(f"terminated {unterminated} clause lines that lacked the final 0 (line-based reading)")
    if dropped_zero:
        notes.append(f"dropped {dropped_zero} lone '0' line(s)")
    return clauses, notes


def _fits(clauses: List[Clause], n: int, m: int) -> bool:
    return (
        len(clauses) == m
        and all(clauses)
        and all(1 <= abs(l) <= n for c in clauses for l in c)
    )


def parse_original(text: str) -> Dict:
    """Parse a SATLIB file; return comments, header, clauses and what had to be repaired."""
    comments, (n, m), data, trailer = split_sections(text)
    notes: List[str] = []
    if trailer is not None:
        notes.append(f"dropped '%' end marker and {len(trailer)} trailing line(s) {trailer[:3]}")
    reading = None
    clauses: List[Clause] = []
    try:
        tok, tok_notes = read_tokens(data)
    except ValueError:
        tok, tok_notes = [], []
    if _fits(tok, n, m):
        reading, clauses = "token", tok
        notes += tok_notes
        # a clause spread over two lines is legal DIMACS but PySAT reads it as two
        if len(data) != m:
            split = sum(1 for s in data if s.split()[-1] != "0")
            if split:
                notes.append(f"joined {split} clause(s) split across lines")
    else:
        lin, lin_notes = read_lines(data)
        if _fits(lin, n, m):
            reading, clauses = "line", lin
            notes += lin_notes
        else:
            raise ValueError(
                f"no reading matches the header p cnf {n} {m}: "
                f"token {len(tok)} clauses, line {len(lin)} clauses"
            )
    if "\t" in text:
        notes.append("tabs replaced by single spaces")
    return {"comments": comments, "n": n, "m": m, "clauses": clauses, "reading": reading, "notes": notes}


def render(comments: List[str], n: int, m: int, clauses: List[Clause], change_note: Optional[str]) -> str:
    out = [c.replace("\t", " ") for c in comments]
    if change_note:
        out.append(f"c normalized (scripts/satlib_bench_intake.py): {change_note}")
    out.append(f"p cnf {n} {m}")
    out += [" ".join(str(l) for l in c) + " 0" for c in clauses]
    return "\n".join(out) + "\n"


def normalise(text: str) -> Tuple[str, Dict]:
    """Canonical text for a file. Idempotent: normalise(normalise(t)[0])[0] == normalise(t)[0]."""
    p = parse_original(text)
    bare = render(p["comments"], p["n"], p["m"], p["clauses"], None)
    if bare == text:
        return text, p
    note = "; ".join(p["notes"]) if p["notes"] else "whitespace only"
    if any(c.startswith("c normalized (scripts/satlib_bench_intake.py)") for c in p["comments"]):
        note = None  # already carries its note; only whitespace can differ
    return render(p["comments"], p["n"], p["m"], p["clauses"], note), p


# ----------------------------------------------------------------------------
# labels

NOTE_UNSAT = re.compile(r"^c\s+NOTE:\s*Not satisfiable", re.I)
NOTE_SAT = re.compile(r"^c\s+NOTE:\s*Satisfiable", re.I)
PRET_CHARGE = re.compile(r"Charge \( 0 = sat\. / 1 = unsat\. \) ==>\s*([01])")


def label(family: str, comments: List[str]) -> Tuple[str, str, str]:
    """(label, source, evidence) from the file's own comments, then family convention."""
    for c in comments:
        if NOTE_UNSAT.match(c):
            return "unsat", "file_note", c.strip()
        if NOTE_SAT.match(c):
            return "sat", "file_note", c.strip()
    for c in comments:
        mo = PRET_CHARGE.search(c)
        if mo:
            return ("unsat" if mo.group(1) == "1" else "sat"), "file_generator_field", c.strip()
    if family.startswith("uuf"):
        return "unsat", "family_convention", "SATLIB uuf = uniform random 3-SAT, unsatisfiable"
    if family == "bf":
        return "unsat", "family_convention", "SATLIB DIMACS bf (bridge fault): all unsatisfiable; no note in file"
    return "unknown", "none", ""


def sat_check(clauses: List[Clause], limit_s: float) -> Dict:
    from pysat.solvers import Solver

    t0 = time.perf_counter()
    with Solver(name="cadical153", bootstrap_with=[list(c) for c in clauses]) as s:
        timer = threading.Timer(limit_s, s.interrupt)
        timer.start()
        try:
            res = s.solve_limited(expect_interrupt=True)
        finally:
            timer.cancel()
    dt = time.perf_counter() - t0
    result = {True: "sat", False: "unsat", None: "timeout"}[res]
    return {"solver": "cadical153", "limit_s": limit_s, "result": result, "seconds": round(dt, 3)}


# ----------------------------------------------------------------------------
# cross-reader verification

def pysat_clauses(text: str) -> List[Clause]:
    from pysat.formula import CNF

    return [tuple(c) for c in CNF(from_string=text).clauses]


def memetic_clauses(text: str) -> List[Clause]:
    from src.sat.cnf import WCNF

    with tempfile.NamedTemporaryFile("w", suffix=".cnf", delete=False) as f:
        f.write(text)
        tmp = f.name
    try:
        return [tuple(c.lits) for c in WCNF.parse_dimacs(tmp).clauses]
    finally:
        os.unlink(tmp)


def instance_facts(clauses: List[Clause], n: int) -> Dict:
    ks = collections.Counter(len(c) for c in clauses)
    used = {abs(l) for c in clauses for l in c}
    dup = sum(v - 1 for v in collections.Counter(tuple(sorted(c)) for c in clauses).values() if v > 1)
    taut = sum(1 for c in clauses if any(-l in c for l in c))
    replit = sum(1 for c in clauses if len(set(c)) != len(c))
    return {
        "k_min": min(ks), "k_max": max(ks),
        "k_hist": {str(k): ks[k] for k in sorted(ks)},
        "unused_vars": n - len(used),
        "duplicate_clauses": dup,
        "tautologies": taut,
        "repeated_literal_clauses": replit,
    }


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ----------------------------------------------------------------------------

def family_of(member: str) -> str:
    parts = member.split("/")
    # member is "satlib_bench/<dir>/..."
    return FAMILY_DIRS[parts[1]]


def build(tar_path: str, sat_limit: float) -> Tuple[List[Dict], Dict[str, str]]:
    rows: List[Dict] = []
    texts: Dict[str, str] = {}
    with tarfile.open(tar_path) as tf:
        members = sorted(
            (m for m in tf.getmembers() if m.isfile() and m.name.endswith(".cnf")),
            key=lambda m: m.name,
        )
        for mem in members:
            raw = tf.extractfile(mem).read()
            text = raw.decode("utf-8")
            path = f"data/{mem.name}"
            fam = family_of(mem.name)
            new, p = normalise(text)
            n, m, cls = p["n"], p["m"], p["clauses"]

            # independent check 1: the memetic reader on the ORIGINAL bytes
            mem_orig = memetic_clauses(text)
            if mem_orig != cls:
                raise SystemExit(f"{path}: memetic reader on the original disagrees with the chosen reading")
            # check 2: every reader on the NORMALISED text returns the same list
            tok_new, _ = read_tokens(split_sections(new)[2])
            for name, got in (("pysat", pysat_clauses(new)), ("memetic", memetic_clauses(new)), ("token", tok_new)):
                if got != cls:
                    raise SystemExit(f"{path}: {name} reader on the normalised text disagrees ({len(got)} vs {len(cls)})")
            # check 3: idempotent
            if normalise(new)[0] != new:
                raise SystemExit(f"{path}: normalisation is not idempotent")

            pysat_orig = pysat_clauses(text)
            lab, src, ev = label(fam, p["comments"])
            row = {
                "path": path,
                "family": fam,
                "n": n,
                "m": m,
                **instance_facts(cls, n),
                "label": lab,
                "label_source": src,
                "label_evidence": ev,
                "sha256_original": sha256(raw),
                "sha256": sha256(new.encode()),
                "changed": new != text,
                "reading": p["reading"],
                "normalization": p["notes"] if new != text else [],
                "pysat_on_original": {
                    "clauses": len(pysat_orig),
                    "empty_clauses": sum(1 for c in pysat_orig if not c),
                    "agrees": pysat_orig == cls,
                },
            }
            if sat_limit > 0:
                sc = sat_check(cls, sat_limit)
                row["sat_check"] = sc
                if lab == "unsat" and sc["result"] == "sat":
                    raise SystemExit(f"{path}: labelled unsat ({src}) but {sc['solver']} found a model")
                if lab == "sat" and sc["result"] == "unsat":
                    raise SystemExit(f"{path}: labelled sat ({src}) but {sc['solver']} proved unsat")
            row["rc2_list"] = "satlib" if lab == "unsat" else None
            row["exclude_reason"] = None if lab == "unsat" else f"label={lab}"
            rows.append(row)
            texts[path] = new
    return rows, texts


def manifest_text(rows: List[Dict]) -> str:
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def strip_volatile(rows: List[Dict]) -> List[Dict]:
    """Drop timing fields so --check compares content, not solver speed."""
    out = []
    for r in rows:
        r = dict(r)
        if "sat_check" in r:
            r["sat_check"] = {k: v for k, v in r["sat_check"].items() if k != "seconds"}
        out.append(r)
    return out


def report(rows: List[Dict]) -> None:
    by = collections.defaultdict(list)
    for r in rows:
        by[r["family"]].append(r)
    print(f"{'family':8} {'files':>5} {'unsat':>5} {'sat':>4} {'unk':>4} {'n':>11} {'m':>11} {'k':>6} {'changed':>7} {'pysat!=':>7}")
    for fam in sorted(by):
        rs = by[fam]
        c = collections.Counter(r["label"] for r in rs)
        ns = sorted({r["n"] for r in rs})
        ms = sorted({r["m"] for r in rs})
        print(
            f"{fam:8} {len(rs):5d} {c['unsat']:5d} {c['sat']:4d} {c['unknown']:4d} "
            f"{ns[0]:>5}-{ns[-1]:<5} {ms[0]:>5}-{ms[-1]:<5} "
            f"{min(r['k_min'] for r in rs):>2}-{max(r['k_max'] for r in rs):<3} "
            f"{sum(r['changed'] for r in rs):7d} {sum(not r['pysat_on_original']['agrees'] for r in rs):7d}"
        )
    notes = collections.Counter(n for r in rows for n in r["normalization"])
    print("\nnormalisation notes (count of files):")
    for k, v in sorted(notes.items()):
        print(f"  {v:4d}  {k}")
    sc = [r["sat_check"] for r in rows if "sat_check" in r]
    if sc:
        print("\nSAT cross-check:", dict(collections.Counter(s["result"] for s in sc)))
        slow = [(r["path"], r["sat_check"]) for r in rows if "sat_check" in r and r["sat_check"]["result"] == "timeout"]
        for p, s in slow:
            print(f"  timeout: {p} (> {s['limit_s']} s)")
    odd = [r for r in rows if r["duplicate_clauses"] or r["tautologies"] or r["repeated_literal_clauses"] or r["unused_vars"]]
    if odd:
        print("\ninstance facts worth knowing (not altered):")
        for r in odd:
            print(f"  {r['path']}: dup={r['duplicate_clauses']} taut={r['tautologies']} "
                  f"replit={r['repeated_literal_clauses']} unused_vars={r['unused_vars']}")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tar", default=DEFAULT_TAR, help="tarball of the untouched SATLIB files")
    ap.add_argument("--sat-check-s", type=float, default=0.0, help="SAT cross-check limit per file (0 = skip)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--write", action="store_true", help="normalise files in place and write the manifests")
    g.add_argument("--check", action="store_true", help="verify disk == normalised and manifests up to date")
    a = ap.parse_args(argv)

    os.chdir(STAGING)
    rows, texts = build(a.tar, a.sat_check_s)
    report(rows)

    lists: Dict[str, List[str]] = {k: [] for k in RC2_LISTS}
    for r in rows:
        if r["rc2_list"]:
            lists[r["rc2_list"]].append(r["path"])
    sha = {r["path"]: r["sha256"] for r in rows}

    if a.check:
        bad = [p for p, t in texts.items() if not os.path.exists(p) or open(p, encoding="utf-8").read() != t]
        drift = []
        if os.path.exists(MANIFEST):
            with open(MANIFEST, encoding="utf-8") as f:
                old = [json.loads(l) for l in f]
            keep_sat = any("sat_check" in r for r in old)
            if not keep_sat:
                rows = [{k: v for k, v in r.items() if k != "sat_check"} for r in rows]
            elif not any("sat_check" in r for r in rows):
                old = [{k: v for k, v in r.items() if k != "sat_check"} for r in old]
            if manifest_text(strip_volatile(old)) != manifest_text(strip_volatile(rows)):
                drift.append(MANIFEST)
        else:
            drift.append(MANIFEST + " (missing)")
        for k, base in RC2_LISTS.items():
            want = "".join(p + "\n" for p in lists[k])
            if not os.path.exists(base + ".txt") or open(base + ".txt").read() != want:
                drift.append(base + ".txt")
        print(f"\ncheck: {len(bad)} file(s) differ from normalised form; drift in {drift or 'nothing'}")
        for p in bad[:10]:
            print("  differs:", p)
        return 3 if bad or drift else 0

    print("\nRC2 lists: " + ", ".join(f"{k} {len(v)}" for k, v in lists.items()))
    if not a.write:
        print("report only; pass --write to normalise in place and write the manifests")
        return 0

    for p, t in texts.items():
        with open(p, "w", encoding="utf-8") as f:
            f.write(t)
    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write(manifest_text(rows))
    for k, base in RC2_LISTS.items():
        with open(base + ".txt", "w") as f:
            f.writelines(p + "\n" for p in lists[k])
        with open(base + ".sha256", "w") as f:
            f.writelines(f"{sha[p]}  {p}\n" for p in lists[k])
    print(f"wrote {len(texts)} files, {MANIFEST}, " + ", ".join(b + ".{txt,sha256}" for b in RC2_LISTS.values()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
