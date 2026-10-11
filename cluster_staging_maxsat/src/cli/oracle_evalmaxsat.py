#!/usr/bin/env python3
"""
Find optimum costs with EvalMaxSAT for a set of (W)CNF instances.

Plain `p cnf` files are converted to all-soft WCNF (weight 1, top = m+1)
before being handed to EvalMaxSAT -- fed a raw `p cnf` file it treats every
clause as hard and silently answers `s UNSATISFIABLE`
(see docs/archive/CORPUS_MSE2016_ASSESSMENT.md, "EvalMaxSAT does not accept them").
`.wcnf` files are passed through unchanged, in either dialect: the old one
(`p wcnf n m top`, a weight on every line) or the new MSE >= 2022 one (no
`p` line; hard clauses start with `h`, soft lines with their weight).

At the cap the solver gets SIGTERM, not SIGKILL. EvalMaxSAT is anytime: on
SIGTERM it prints its incumbent (`o <cost>`, `s SATISFIABLE`, `v ...`) and
exits 10. That incumbent is model-checked like an optimum and recorded as
`best_cost` with `status = timeout`, so a capped run still gives a verified
upper bound. SIGKILL follows only if the solver outlives `--term-grace`.

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
import signal
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
    fmt: str                            # "cnf" | "wcnf" | "wcnf_new" (no p line, `h` = hard)


def read_formula(path: str) -> Formula:
    """Old `p cnf` / `p wcnf` files, or the new WCNF dialect.

    The dialect is fixed by the first non-comment line: a `p` line means the
    old dialects; any clause line before a `p` line means the new one (no `p`
    line at all; `h ...` hard, `<weight> ...` soft). The new dialect is never
    guessed from the presence of `h` lines, so a new-format file with soft
    clauses only (17 of the 166 MSE 2023/2024 files) is still read as WCNF.
    """
    n_vars = 0
    top: Optional[int] = None
    fmt: Optional[str] = None
    hard: List[List[int]] = []
    soft: List[Tuple[int, List[int]]] = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in "c%":
                continue
            if line.startswith("p"):
                if fmt is not None:
                    raise ValueError("p line after clause lines")
                parts = line.split()
                fmt = parts[1]
                n_vars = int(parts[2])
                if fmt == "wcnf" and len(parts) >= 5:
                    top = int(parts[4])
                continue
            if fmt is None:
                fmt = "wcnf_new"
            if fmt == "wcnf_new" and line[0] == "h":
                toks = [int(t) for t in line[1:].split()]
                if toks and toks[-1] == 0:
                    toks = toks[:-1]
                hard.append(toks)
                for lit in toks:
                    n_vars = max(n_vars, abs(lit))
                continue
            toks = [int(t) for t in line.split()]
            if not toks:
                continue
            if toks[-1] == 0:
                toks = toks[:-1]
            if fmt in ("wcnf", "wcnf_new"):
                w, lits = toks[0], toks[1:]
                if fmt == "wcnf" and top is not None and w >= top:
                    hard.append(lits)
                else:
                    soft.append((w, lits))
            else:
                lits = toks
                soft.append((1, lits))
            for lit in lits:
                n_vars = max(n_vars, abs(lit))
    return Formula(n_vars=n_vars, hard=hard, soft=soft, fmt=fmt or "cnf")


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
    status: str                     # optimal | timeout | unsat | error  (timeout may carry a verified best_cost)
    opt_cost: Optional[int]         # only when status == optimal (and verified)
    best_cost: Optional[int]        # last `o` line seen (== opt_cost when optimal; the incumbent at SIGTERM on timeout)
    verified: Optional[bool]        # the printed model re-evaluated == best_cost, with no hard clause violated
    time_s: float
    solver_time_s: Optional[float]  # EvalMaxSAT's own "c Total time"
    timeout_s: float
    note: str = ""
    # added 2026-10-11 (SIGTERM at the cap; all optional, so older rows still load)
    s_line: Optional[str] = None      # the solver's `s` line, e.g. "OPTIMUM FOUND", "SATISFIABLE", "UNKNOWN"
    exit_code: Optional[int] = None   # MSE convention: 30 optimum, 20 unsat, 10 incumbent at SIGTERM
    stopped_by: Optional[str] = None  # None (finished) | "sigterm" | "sigkill"
    term_grace_s: Optional[float] = None


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


def solve_one(path: str, binary: str, timeout_s: float, extra_args: List[str], keep_wcnf: bool,
              term_grace_s: float = 120.0) -> OracleResult:
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
    if formula.fmt in ("wcnf", "wcnf_new"):
        solver_input = path
    else:
        fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(path) + ".", suffix=".wcnf")
        os.close(fd)
        write_all_soft_wcnf(formula, tmp_path)
        solver_input = tmp_path

    stdout = ""
    timed_out = False
    stopped_by: Optional[str] = None
    exit_code: Optional[int] = None
    note = ""
    try:
        proc = subprocess.Popen([binary, *extra_args, solver_input], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            # Anytime stop: SIGTERM makes EvalMaxSAT print its incumbent and exit 10.
            timed_out = True
            stopped_by = "sigterm"
            proc.send_signal(signal.SIGTERM)
            try:
                stdout, stderr = proc.communicate(timeout=term_grace_s)
            except subprocess.TimeoutExpired:
                stopped_by = "sigkill"
                proc.kill()
                stdout, stderr = proc.communicate()
        exit_code = proc.returncode
        # MSE exit codes: 10 incumbent (SATISFIABLE), 20 UNSATISFIABLE, 30 OPTIMUM FOUND
        if exit_code not in (0, 10, 20, 30) and "s OPTIMUM FOUND" not in (stdout or ""):
            note = f"rc={exit_code} stderr={(stderr or '').strip()[:200]}"
    finally:
        if tmp_path and not keep_wcnf:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        elif tmp_path:
            note = (note + f" wcnf={tmp_path}").strip()
    stdout = stdout or ""

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
    base.update(s_line=s_line or None, exit_code=exit_code, stopped_by=stopped_by,
                term_grace_s=term_grace_s if timed_out else None)

    def check_model() -> Tuple[Optional[bool], str]:
        assign = parse_model(v_lines, formula.n_vars)
        if assign is None or best is None:
            return None, ""
        cost, hard_viol = cost_of_model(formula, assign)
        ok = hard_viol == 0 and cost == best
        return ok, ("" if ok else f" model check: cost={cost} hard_viol={hard_viol} reported={best}")

    if timed_out:
        verified, msg = check_model()
        if s_line == "UNKNOWN":
            msg += " no hard-feasible incumbent at the cap"
        return OracleResult(**base, status="timeout", opt_cost=None,
                            best_cost=best if verified is not False else None, verified=verified,
                            time_s=elapsed, solver_time_s=solver_time, note=(note + msg).strip())
    if s_line == "UNSATISFIABLE":
        return OracleResult(**base, status="unsat", opt_cost=None, best_cost=None, verified=None,
                            time_s=elapsed, solver_time_s=solver_time,
                            note=(note + " hard clauses unsatisfiable").strip())
    if s_line != "OPTIMUM FOUND" or best is None:
        return OracleResult(**base, status="error", opt_cost=None, best_cost=best, verified=None,
                            time_s=elapsed, solver_time_s=solver_time,
                            note=(note + f" s='{s_line}' tail={stdout[-200:]!r}").strip())

    verified, msg = check_model()
    note = (note + msg).strip()
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
    ap.add_argument("--term-grace", type=float, default=120.0,
                    help="seconds after SIGTERM (sent at --timeout) before SIGKILL")
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
        futs = {pool.submit(solve_one, p, args.bin, args.timeout, args.solver_arg, args.keep_wcnf,
                            args.term_grace): p for p in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            counts[r.status] += 1
            out_f.write(json.dumps(asdict(r)) + "\n")
            out_f.flush()
            tag = f"o={r.opt_cost}" if r.status == "optimal" else f"ub={r.best_cost}"
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
