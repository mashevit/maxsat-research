#!/usr/bin/env python3
"""Diagnostic (not used by any run): the exact kernel of a MaxSAT instance.

Written for soft-only Max-2-SAT; extended the same day to any clause length and
to hard clauses (weight HARD), since both rules stay exact there: a pure
variable is still dominated, and resolving (x v A) w1 with (-x v B) w2 into
(A v B) min(w1, w2) is exact for clauses of any length (the resolvent is longer).
Reads `p cnf` (every clause soft, weight 1), `p wcnf` (weight >= top is hard)
and the 2022+ WCNF format (`h` lines hard, no p line).

Note: docs/current/RESEARCH_NOTES_SOLVER_DIRECTIONS.md (repo), N-2026-10-14-e.

Rules, applied to a fixpoint:
  * merge identical clauses (weights add); drop tautologies;
  * complementary units (x) w1, (-x) w2: min(w1, w2) moves to a constant;
  * pure variable (one polarity only, any degree): set it, drop its clauses;
  * variable in exactly one positive and one negative clause, (x v A) w1 and
    (-x v B) w2: replace both by (A v B) with weight min(w1, w2) (MaxSAT
    resolution; the leftover |w1 - w2| clause is satisfied by x).
Reconstruction runs the eliminations backwards: a pure x takes its polarity; a
resolved x is False if A is satisfied, True if only B is, and otherwise satisfies
the heavier of the two clauses (exactness tested by brute force, 2026-10-14).

With --verify, RC2 (PySAT) solves the kernel, the full assignment is rebuilt and
its cost is counted on the original clauses; that cost must equal the kernel
optimum plus the constant (and the RC2 optimum of the original, if known).
With --write DIR, each kernel is written as DIR/<stem>_kernel.wcnf.

    python scripts/diag_max2sat_kernel.py [--verify] [--write DIR] FILE.wcnf ...
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from collections import defaultdict
from typing import Dict, List, Tuple

Clause = Tuple[int, ...]


HARD = 1 << 60  # weight of a hard clause; min(HARD, w) = w keeps resolution exact


def read_wcnf(path: str) -> Tuple[int, List[Tuple[int, Clause]]]:
    n, top, kind, cls = 0, None, "wcnf_new", []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in "c%":
                continue
            if line[0] == "p":
                t = line.split()
                kind, n = t[1], int(t[2])
                top = int(t[4]) if kind == "wcnf" and len(t) > 4 else None
                continue
            t = line.split()
            if t[0] == "h":
                w, lits = HARD, t[1:-1]
            elif kind == "cnf":
                w, lits = 1, t[:-1]
            else:
                w, lits = int(t[0]), t[1:-1]
                if top is not None and w >= top:
                    w = HARD
            lits = tuple(int(x) for x in lits if x != "0")
            if lits:
                n = max(n, max(abs(l) for l in lits))
                cls.append((w, lits))
    return n, cls


def kernelize(cls: List[Tuple[int, Clause]]):
    """Return (kernel clauses {lits: weight}, constant cost, elimination record)."""
    C: Dict[Clause, int] = {}
    occ: Dict[int, set] = defaultdict(set)
    const = 0
    rec: List[Tuple[str, int, object]] = []

    def insert(lits, w):
        nonlocal const
        lits = tuple(sorted(set(lits)))
        if any(-l in lits for l in lits):
            return
        if not lits:
            const += w
            return
        C[lits] = C.get(lits, 0) + w
        for l in lits:
            occ[abs(l)].add(lits)

    def remove(k):
        w = C.pop(k)
        for l in k:
            occ[abs(l)].discard(k)
        return w

    for w, lits in cls:
        insert(lits, w)
    work = list(occ)
    while work:
        v = work.pop()
        ks = list(occ.get(v, ()))
        if not ks:
            continue
        a, b = (v,), (-v,)
        if a in C and b in C and max(C[a], C[b]) < HARD:  # complementary hard units: infeasible, leave
            m = min(C[a], C[b])
            const += m
            for k in (a, b):
                C[k] -= m
                if C[k] == 0:
                    remove(k)
            ks = list(occ[v])
            if not ks:
                continue
        pos = [k for k in ks if v in k]
        neg = [k for k in ks if -v in k]
        if not pos or not neg:
            for k in ks:
                remove(k)
            rec.append(("pure", v, bool(pos)))
        elif len(pos) == 1 and len(neg) == 1:
            k1, k2 = pos[0], neg[0]
            w1, w2 = remove(k1), remove(k2)
            w = min(w1, w2)
            A = tuple(l for l in k1 if l != v)
            B = tuple(l for l in k2 if l != -v)
            insert(A + B, w)
            rec.append(("res", v, (A, B, w1 >= w2)))
        else:
            continue
        for k in ks:
            for l in k:
                if abs(l) != v:
                    work.append(abs(l))
    return C, const, rec


def reconstruct(n: int, kernel_val: Dict[int, bool], rec) -> List[bool]:
    val = [False] * (n + 1)
    for v, x in kernel_val.items():
        val[v] = x
    for kind, v, x in reversed(rec):
        if kind == "pure":
            val[v] = x
        else:
            A, B, pos_heavier = x
            sat = lambda c: any(val[abs(l)] == (l > 0) for l in c)  # noqa: E731
            if sat(A):
                val[v] = False      # (x v A) holds; -x satisfies (-x v B)
            elif sat(B):
                val[v] = True
            else:                   # one of the two is lost: keep the heavier
                val[v] = pos_heavier
    return val


def cost(cls, val) -> int:
    return sum(w for w, lits in cls if not any(val[abs(l)] == (l > 0) for l in lits))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--write")
    a = ap.parse_args(argv)
    for path in a.files:
        n, cls = read_wcnf(path)
        t0 = time.time()
        C, const, rec = kernelize(cls)
        tk = time.time() - t0
        kv = sorted({abs(l) for k in C for l in k})
        idx = {v: i + 1 for i, v in enumerate(kv)}
        lens = [len(k) for k in C]
        line = (f"{os.path.basename(path)}: n {n} m {len(cls)} (hard {sum(w >= HARD for w, _ in cls)}) -> "
                f"kernel {len(kv)} vars {len(C)} clauses (hard {sum(w >= HARD for w in C.values())}, "
                f"max len {max(lens, default=0)}), const {const}, {tk:.2f} s")
        if a.write:
            out = os.path.join(a.write, os.path.basename(path).replace(".wcnf", "_kernel.wcnf"))
            with open(out, "w", encoding="utf-8") as f:
                f.write(f"p wcnf {len(kv)} {len(C)} {sum(C.values()) + 1}\n")
                for k, w in C.items():
                    f.write(f"{w} " + " ".join(str(idx[abs(l)] * (1 if l > 0 else -1)) for l in k) + " 0\n")
        if a.verify:
            from pysat.examples.rc2 import RC2
            from pysat.formula import WCNF
            w = WCNF()
            for k, wt in C.items():
                cl = [idx[abs(l)] * (1 if l > 0 else -1) for l in k]
                if wt >= HARD:
                    w.append(cl)
                else:
                    w.append(cl, weight=wt)
            t0 = time.time()
            with RC2(w) as rc2:
                model = rc2.compute()
                kc = rc2.cost
            tr = time.time() - t0
            val = reconstruct(n, {kv[abs(l) - 1]: l > 0 for l in model}, rec)
            full = cost(cls, val)
            ok = "OK" if full == kc + const else "MISMATCH"
            line += f"; RC2 kernel {tr:.3f} s, optimum {kc} + {const}; rebuilt full cost {full} {ok}"
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
