#!/usr/bin/env python3
"""
Find optimum costs with EvalMaxSAT for a set of (W)CNF instances.

Plain `p cnf` files are converted to all-soft WCNF (weight 1, top = m+1)
before being handed to EvalMaxSAT -- fed a raw `p cnf` file it treats every
clause as hard and silently answers `s UNSATISFIABLE`
(see docs/CORPUS_MSE2016_ASSESSMENT.md, "EvalMaxSAT does not accept them").
`.wcnf` files are passed through unchanged.

Each result is appended as one JSON line; re-running on the same output file
skips instances already solved (resumable). The reported model is re-checked
against the formula so `opt_cost` is never taken on trust.

Usage:
  python src/cli/oracle_evalmaxsat.py more_data --out results/oracle_more_data.jsonl
  python src/cli/oracle_evalmaxsat.py a.cnf b.wcnf --timeout 600 --jobs 4
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_BIN = os.path.join(REPO_ROOT, "solver_EvalMaxSat", "EvalMaxSAT", "build", "main", "EvalMaxSAT_bin")


# --------------------------------------------------------------------------- #
# formula I/O
# --------------------------------------------------------------------------- #

@dataclass
class Formula:
    n_vars: int
    hard: List[List[int]]
    soft: List[Tuple[int, List[int]]]   # (weight, lits)
    fmt: str                            # "cnf" | "wcnf"


def read_formula(path: str) -> Formula:
    n_vars = 0
    top: Optional[int] = None
    fmt = "cnf"
    hard: List[List[int]] = []
    soft: List[Tuple[int, List[int]]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in "c%":
                continue
            if line.startswith("p"):
                parts = line.split()
                fmt = parts[1]
                n_vars = int(parts[2])
                if fmt == "wcnf" and len(parts) >= 5:
                    top = int(parts[4])
                continue
            toks = [int(t) for t in line.split()]
            if not toks:
                continue
            if toks[-1] == 0:
                toks = toks[:-1]
            if fmt == "wcnf":
                w, lits = toks[0], toks[1:]
                if top is not None and w >= top:
                    hard.append(lits)
                else:
                    soft.append((w, lits))
            else:
                soft.append((1, toks))
            for lit in (toks[1:] if fmt == "wcnf" else toks):
                n_vars = max(n_vars, abs(lit))
    return Formula(n_vars=n_vars, hard=hard, soft=soft, fmt=fmt)


def write_all_soft_wcnf(formula: Formula, out_path: str) -> None:
    """Plain CNF -> all-soft WCNF: `p wcnf n m m+1`, every clause weight 1."""
    m = len(formula.soft)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"p wcnf {formula.n_vars} {m} {m + 1}\n")
        for w, lits in formula.soft:
            f.write(f"{w} {' '.join(map(str, lits))} 0\n")


def cost_of_model(formula: Formula, assign: List[bool]) -> Tuple[Optional[int], int]:
    """(soft cost, #hard violated). `assign[v]` for v in 1..n; None if hard violated."""
    def sat(lits: List[int]) -> bool:
        return any((lit > 0) == assign[abs(lit)] for lit in lits)

    hard_viol = sum(1 for lits in formula.hard if not sat(lits))
    if hard_viol:
        return None, hard_viol
    return sum(w for w, lits in formula.soft if not sat(lits)), 0


# --------------------------------------------------------------------------- #
# EvalMaxSAT driver
# --------------------------------------------------------------------------- #

@dataclass
class OracleResult:
    instance: str
    sha256: str
    format: str
    n_vars: int
    n_hard: int
    n_soft: int
    status: str                     # optimal | timeout | unsat | error
    opt_cost: Optional[int]         # only when status == optimal (and verified)
    best_cost: Optional[int]        # last `o` line seen (== opt_cost when optimal)
    verified: Optional[bool]        # model re-evaluated == reported cost
    time_s: float
    solver_time_s: Optional[float]  # EvalMaxSAT's own "c Total time"
    timeout_s: float
    note: str = ""


_RE_TOTAL = re.compile(r"c Total time\s*:\s*([0-9.eE+-]+)\s*s")


def parse_model(v_lines: List[str], n_vars: int) -> Optional[List[bool]]:
    if not v_lines:
        return None
    body = " ".join(l[1:].strip() for l in v_lines).strip()
    toks = body.split()
    assign = [False] * (n_vars + 1)
    if len(toks) == 1 and set(toks[0]) <= {"0", "1"} and len(toks[0]) >= n_vars:
        # new EvalMaxSAT format: one 0/1 string, position i -> variable i+1
        for i, ch in enumerate(toks[0][:n_vars]):
            assign[i + 1] = ch == "1"
        return assign
    # old / standard format: signed literals
    for t in toks:
        lit = int(t)
        if lit == 0 or abs(lit) > n_vars:
            continue
        assign[abs(lit)] = lit > 0
    return assign


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def solve_one(path: str, binary: str, timeout_s: float, extra_args: List[str], keep_wcnf: bool) -> OracleResult:
    t0 = time.perf_counter()
    rel = os.path.relpath(path, REPO_ROOT) if path.startswith(REPO_ROOT) else path
    base = dict(instance=rel, sha256=sha256_of(path), timeout_s=timeout_s)
    try:
        formula = read_formula(path)
    except Exception as e:  # noqa: BLE001
        return OracleResult(**base, format="?", n_vars=0, n_hard=0, n_soft=0, status="error",
                            opt_cost=None, best_cost=None, verified=None,
                            time_s=time.perf_counter() - t0, solver_time_s=None, note=f"parse: {e}")
    base.update(format=formula.fmt, n_vars=formula.n_vars, n_hard=len(formula.hard), n_soft=len(formula.soft))

    tmp_path = None
    if formula.fmt == "wcnf":
        solver_input = path
    else:
        fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".wcnf")
        os.close(fd)
        write_all_soft_wcnf(formula, tmp_path)
        solver_input = tmp_path

    stdout = ""
    timed_out = False
    note = ""
    try:
        proc = subprocess.run([binary, *extra_args, solver_input], capture_output=True, text=True, timeout=timeout_s)
        stdout = proc.stdout
        if proc.returncode != 0 and "s OPTIMUM FOUND" not in stdout:
            note = f"rc={proc.returncode} stderr={proc.stderr.strip()[:200]}"
    except subprocess.TimeoutExpired as e:
        timed_out = True
        stdout = (e.stdout or b"")
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
    finally:
        if tmp_path and not keep_wcnf:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        elif tmp_path:
            note = (note + f" wcnf={tmp_path}").strip()

    o_vals: List[int] = []
    s_line = ""
    v_lines: List[str] = []
    solver_time = None
    for line in stdout.splitlines():
        if line.startswith("o "):
            try:
                o_vals.append(int(line.split()[1]))
            except (IndexError, ValueError):
                pass
        elif line.startswith("s "):
            s_line = line[2:].strip()
        elif line.startswith("v"):
            v_lines.append(line)
        elif line.startswith("c Total time"):
            m = _RE_TOTAL.search(line)
            if m:
                solver_time = float(m.group(1))

    best = o_vals[-1] if o_vals else None
    elapsed = time.perf_counter() - t0

    if timed_out:
        return OracleResult(**base, status="timeout", opt_cost=None, best_cost=best, verified=None,
                            time_s=elapsed, solver_time_s=solver_time, note=note)
    if s_line == "UNSATISFIABLE":
        return OracleResult(**base, status="unsat", opt_cost=None, best_cost=None, verified=None,
                            time_s=elapsed, solver_time_s=solver_time,
                            note=(note + " hard clauses unsatisfiable").strip())
    if s_line != "OPTIMUM FOUND" or best is None:
        return OracleResult(**base, status="error", opt_cost=None, best_cost=best, verified=None,
                            time_s=elapsed, solver_time_s=solver_time,
                            note=(note + f" s='{s_line}' tail={stdout[-200:]!r}").strip())

    verified: Optional[bool] = None
    assign = parse_model(v_lines, formula.n_vars)
    if assign is not None:
        cost, hard_viol = cost_of_model(formula, assign)
        verified = (hard_viol == 0 and cost == best)
        if not verified:
            note = (note + f" model check: cost={cost} hard_viol={hard_viol} reported={best}").strip()
    return OracleResult(**base, status="optimal", opt_cost=best if verified is not False else None,
                        best_cost=best, verified=verified, time_s=elapsed, solver_time_s=solver_time, note=note)


# --------------------------------------------------------------------------- #
# batch
# --------------------------------------------------------------------------- #

def collect_instances(paths: List[str], exts: Tuple[str, ...]) -> List[str]:
    out: List[str] = []
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            for dirpath, _, files in os.walk(p):
                for name in files:
                    if name.lower().endswith(exts):
                        out.append(os.path.join(dirpath, name))
        elif os.path.isfile(p):
            out.append(p)
        else:
            print(f"warning: {p} not found", file=sys.stderr)
    return sorted(set(out))


def already_done(out_path: str) -> set:
    done = set()
    if os.path.exists(out_path):
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("status") in ("optimal", "unsat"):
                    done.add(r["sha256"])
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", help="instance files and/or directories (searched recursively)")
    ap.add_argument("--out", default="results/oracle_evalmaxsat.jsonl", help="JSONL output (appended, resumable)")
    ap.add_argument("--csv", default=None, help="also write a CSV summary of the whole JSONL at the end")
    ap.add_argument("--bin", default=DEFAULT_BIN, help="EvalMaxSAT_bin path")
    ap.add_argument("--timeout", type=float, default=1800.0, help="per-instance wall-clock cap in seconds")
    ap.add_argument("--jobs", type=int, default=1, help="instances solved concurrently")
    ap.add_argument("--ext", default=".cnf,.wcnf", help="comma-separated extensions when walking dirs")
    ap.add_argument("--keep-wcnf", action="store_true", help="keep the converted WCNF temp files")
    ap.add_argument("--rerun", action="store_true", help="ignore existing results in --out")
    ap.add_argument("--solver-arg", action="append", default=[], help="extra flag passed to EvalMaxSAT (repeatable)")
    args = ap.parse_args()

    if not os.access(args.bin, os.X_OK):
        print(f"error: EvalMaxSAT binary not executable: {args.bin}", file=sys.stderr)
        return 2

    exts = tuple(e.strip().lower() for e in args.ext.split(",") if e.strip())
    instances = collect_instances(args.paths, exts)
    if not instances:
        print("no instances found", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    done = set() if args.rerun else already_done(args.out)
    todo = [p for p in instances if sha256_of(p) not in done]
    print(f"{len(instances)} instances, {len(instances) - len(todo)} already done, {len(todo)} to solve, "
          f"timeout={args.timeout:g}s jobs={args.jobs}", file=sys.stderr)

    counts = {"optimal": 0, "timeout": 0, "unsat": 0, "error": 0}
    with open(args.out, "a", encoding="utf-8") as out_f, ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futs = {pool.submit(solve_one, p, args.bin, args.timeout, args.solver_arg, args.keep_wcnf): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            counts[r.status] += 1
            out_f.write(json.dumps(asdict(r)) + "\n")
            out_f.flush()
            tag = f"o={r.opt_cost}" if r.status == "optimal" else f"best={r.best_cost}"
            ver = "" if r.verified is None else (" verified" if r.verified else " MISMATCH")
            print(f"[{i}/{len(todo)}] {r.status:8s} {tag:>10s}{ver} {r.time_s:8.1f}s  {r.instance}"
                  + (f"  ({r.note})" if r.note else ""), file=sys.stderr)

    print(f"done: {counts}", file=sys.stderr)

    if args.csv:
        rows = []
        with open(args.out, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        fields = list(OracleResult.__dataclass_fields__.keys())
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k) for k in fields})
        print(f"csv: {args.csv} ({len(rows)} rows)", file=sys.stderr)

    return 0 if counts["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
