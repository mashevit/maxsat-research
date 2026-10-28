"""
Exact MaxSAT kernel for the memetic: opt-in preprocessing (config key
`preprocess: kernel`, read by src/cli/run_memetic_shard.py), behind a cheap
worth-it gate.

Rules, applied until nothing changes; each is exact for any clause length, any
weights and hard clauses:
  * merge identical clauses (weights add); drop tautologies;
  * complementary soft units (x) w1, (-x) w2: min(w1, w2) moves to a constant;
  * pure variable (one polarity only, any degree): set it, drop its clauses;
  * variable in exactly one positive and one negative clause, (x v A) w1 and
    (-x v B) w2: replace both by (A v B) with weight min(w1, w2) (MaxSAT
    resolution; the leftover |w1 - w2| clause is satisfied by x).

`lift` runs the eliminations backwards: a pure x takes its polarity; a resolved
x is False if A is satisfied, True if only B is, and otherwise satisfies the
heavier of the two clauses. For EVERY kernel assignment the lifted assignment
costs exactly `const` + its kernel cost (tests/test_kernel.py checks this by
brute force), so a kernel optimum lifts to an optimum of the original.

Gate (docs/current/RESEARCH_NOTES_SOLVER_DIRECTIONS.md §8.2, repo):
  1. screen: `screen_frac`, the fraction of the occurring variables that are
     pure or occur exactly once positive and once negative. Below
     `screen_min` (default 0.20) the original formula is run.
  2. kernelise. The kernel is used only if it removes at least `gain_min`
     (default 0.20) of the occurring variables and no kernel clause is longer
     than the longest original clause; otherwise the original is run.
  The thresholds come from the calibration in §8.2 (sparse Max-2-SAT 61-65%,
  every other family <= 13%), not from memetic results.

Promoted from scripts/diag_max2sat_kernel.py (2026-10-14): the same rules and
the same reconstruction, including the fix for unequal or hard weights.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .cnf import WCNF, Clause

HARD = 1 << 60  # weight of a hard clause; min(HARD, w) = w keeps resolution exact

PREPROCESS_MODES = ("none", "kernel")
GATE_DEFAULTS = {"screen_min": 0.20, "gain_min": 0.20}

Lits = Tuple[int, ...]


def _weight(cl: Clause) -> int:
    return HARD if cl.is_hard else int(cl.weight)


def screen_frac(wcnf: WCNF) -> Tuple[float, int]:
    """(fraction of occurring variables that are pure or (1 pos, 1 neg), occurring count).

    One pass over the occurrence lists; no knowledge of k or the density.
    """
    if getattr(wcnf, "is_compact", False):   # C counts (COMPILED_MEMETIC_PLAN.md C1.5)
        hit, occurring = wcnf.screen_counts()
        return (hit / occurring if occurring else 0.0), occurring
    hit = occurring = 0
    for v in range(1, wcnf.n_vars + 1):
        p, q = len(wcnf.pos_adj[v]), len(wcnf.neg_adj[v])
        if p + q == 0:
            continue
        occurring += 1
        if p == 0 or q == 0 or (p == 1 and q == 1):
            hit += 1
    return (hit / occurring if occurring else 0.0), occurring


def kernelize(clauses: List[Tuple[int, Lits]]):
    """Return (kernel clauses {lits: weight}, constant cost, elimination record).

    `clauses` are (weight, lits) with hard clauses at weight >= HARD. A constant
    >= HARD means the hard clauses contradict each other.

    Same result as `kernelize_reference` -- the same kernel dict in the same
    order, constant and record (docs/current2/COMPILED_MEMETIC_PLAN.md §10;
    tests/test_kernel_fast.py) -- without its quadratic cost: a variable comes
    off the work list once per eliminated neighbour clause, and the reference
    copied and scanned its whole clause set each time, although most of those
    visits change nothing (both polarities, not 1 + 1). Per-variable counts of
    the clauses holding v and -v decide that in O(1); every visit that changes
    something runs the reference's code, on the same sets in the same iteration
    order, so the work list and every decision are unchanged. The tautology test
    uses a set (same answer, O(k) instead of O(k^2)).
    """
    C: Dict[Lits, int] = {}
    occ: Dict[int, set] = defaultdict(set)
    npos: Dict[int, int] = defaultdict(int)   # clauses of occ[v] holding v
    nneg: Dict[int, int] = defaultdict(int)   # ... holding -v
    const = 0
    rec: List[Tuple[str, int, Any]] = []

    def insert(lits, w):
        nonlocal const
        s = set(lits)
        lits = tuple(sorted(s))
        if any(-l in s for l in lits):
            return
        if not lits:
            const += w
            return
        new = lits not in C
        C[lits] = C.get(lits, 0) + w
        for l in lits:
            occ[abs(l)].add(lits)
            if new:
                if l > 0:
                    npos[l] += 1
                else:
                    nneg[-l] += 1

    def remove(k):
        w = C.pop(k)
        for l in k:
            occ[abs(l)].discard(k)
            if l > 0:
                npos[l] -= 1
            else:
                nneg[-l] -= 1
        return w

    for w, lits in clauses:
        insert(lits, w)
    work = list(occ)
    while work:
        v = work.pop()
        p, q = npos.get(v, 0), nneg.get(v, 0)
        if p + q == 0:                       # the reference: `if not ks: continue`
            continue
        a, b = (v,), (-v,)
        units = a in C and b in C and max(C[a], C[b]) < HARD
        if not units and p and q and not (p == 1 and q == 1):
            continue                         # the reference's final `else: continue`, unchanged state
        ks = list(occ.get(v, ()))
        if units:  # complementary soft units
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
            A = tuple(l for l in k1 if l != v)
            B = tuple(l for l in k2 if l != -v)
            insert(A + B, min(w1, w2))
            rec.append(("res", v, (A, B, w1 >= w2)))
        else:
            continue
        for k in ks:
            for l in k:
                if abs(l) != v:
                    work.append(abs(l))
    return C, const, rec


def kernelize_reference(clauses: List[Tuple[int, Lits]]):
    """The original kernelize (until 2026-10-28), kept as the twin reference for
    tests/test_kernel_fast.py. Same contract as `kernelize`.

    Return (kernel clauses {lits: weight}, constant cost, elimination record).

    `clauses` are (weight, lits) with hard clauses at weight >= HARD. A constant
    >= HARD means the hard clauses contradict each other.
    """
    C: Dict[Lits, int] = {}
    occ: Dict[int, set] = defaultdict(set)
    const = 0
    rec: List[Tuple[str, int, Any]] = []

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

    for w, lits in clauses:
        insert(lits, w)
    work = list(occ)
    while work:
        v = work.pop()
        ks = list(occ.get(v, ()))
        if not ks:
            continue
        a, b = (v,), (-v,)
        if a in C and b in C and max(C[a], C[b]) < HARD:  # complementary soft units
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
            A = tuple(l for l in k1 if l != v)
            B = tuple(l for l in k2 if l != -v)
            insert(A + B, min(w1, w2))
            rec.append(("res", v, (A, B, w1 >= w2)))
        else:
            continue
        for k in ks:
            for l in k:
                if abs(l) != v:
                    work.append(abs(l))
    return C, const, rec


def reconstruct(n: int, kernel_val: Dict[int, bool], rec) -> List[bool]:
    """Full 1-indexed assignment (index 0 unused) from kernel values and the record."""
    val = [False] * (n + 1)
    for v, x in kernel_val.items():
        val[v] = x

    def sat(c):
        return any(val[abs(l)] == (l > 0) for l in c)

    for kind, v, x in reversed(rec):
        if kind == "pure":
            val[v] = x
        else:
            A, B, pos_heavier = x
            if sat(A):
                val[v] = False      # (x v A) holds; -x satisfies (-x v B)
            elif sat(B):
                val[v] = True
            else:                   # one of the two is lost: keep the heavier
                val[v] = pos_heavier
    return val


@dataclass
class Kernel:
    wcnf: WCNF                  # the kernel, variables renumbered 1..k
    var_of: List[int]           # kernel variable i (1-based) -> original var_of[i - 1]
    const: int                  # soft cost fixed by the rules
    rec: list
    n_orig: int
    max_len: int
    n_hard: int


def build_kernel(wcnf: WCNF) -> Tuple[Optional[Kernel], int]:
    """(Kernel, raw constant). Kernel is None when the hard clauses contradict."""
    C, const, rec = kernelize([(_weight(cl), tuple(cl.lits)) for cl in wcnf.clauses])
    if const >= HARD:
        return None, const
    var_of = sorted({abs(l) for k in C for l in k})
    idx = {v: i + 1 for i, v in enumerate(var_of)}
    soft_total = sum(w for w in C.values() if w < HARD)
    top = soft_total + 1
    kw = WCNF(n_vars=len(var_of), hard_weight=top, is_wcnf=True)
    for k, w in C.items():
        lits = [idx[abs(l)] * (1 if l > 0 else -1) for l in k]
        hard = w >= HARD
        cid = len(kw.clauses)
        kw.clauses.append(Clause(weight=top if hard else w, lits=lits, is_hard=hard))
        for lit in lits:
            (kw.pos_adj if lit > 0 else kw.neg_adj)[abs(lit)].append(cid)
    return Kernel(wcnf=kw, var_of=var_of, const=const, rec=rec, n_orig=wcnf.n_vars,
                  max_len=max((len(k) for k in C), default=0),
                  n_hard=sum(1 for w in C.values() if w >= HARD)), const


def lift(kernel: Kernel, kernel_assign01: List[bool]) -> List[bool]:
    """Kernel assignment (1-indexed, index 0 unused) -> full original assignment."""
    kv = {v: bool(kernel_assign01[i + 1]) for i, v in enumerate(kernel.var_of)}
    return reconstruct(kernel.n_orig, kv, kernel.rec)


def preprocess_mode(cfg: Dict[str, Any]) -> str:
    mode = str(cfg.get("preprocess", "none") or "none").lower()
    if mode not in PREPROCESS_MODES:
        raise ValueError(f"preprocess must be one of {PREPROCESS_MODES}, got {mode!r}")
    return mode


def gate_params(cfg: Dict[str, Any]) -> Dict[str, float]:
    g = dict(GATE_DEFAULTS)
    for k, v in (cfg.get("preprocess_gate") or {}).items():
        if k not in GATE_DEFAULTS:
            raise ValueError(f"unknown preprocess_gate key {k!r}; known: {sorted(GATE_DEFAULTS)}")
        g[k] = float(v)
    return g


@dataclass
class GateResult:
    decision: str               # kernel | kernel_empty | skipped_screen | skipped_gain
                                # | skipped_length | skipped_infeasible
    kernel: Optional[Kernel]    # set only for kernel / kernel_empty
    fields: Dict[str, Any] = field(default_factory=dict)


def gate(wcnf: WCNF, cfg: Dict[str, Any]) -> GateResult:
    """Screen, kernelise, decide. `fields` go into the shard record as they are."""
    g = gate_params(cfg)
    t0 = time.time()
    frac, occurring = screen_frac(wcnf)
    f: Dict[str, Any] = {"screen_frac": round(frac, 6), "kernel_n_vars": None, "kernel_n_clauses": None,
                         "kernel_n_hard": None, "kernel_const": None, "kernel_max_len": None,
                         "kernel_gain": None}
    if frac < g["screen_min"]:
        f["preprocess_s"] = round(time.time() - t0, 4)
        return GateResult("skipped_screen", None, f)
    kernel, const = build_kernel(wcnf)
    f["preprocess_s"] = round(time.time() - t0, 4)
    if kernel is None:
        return GateResult("skipped_infeasible", None, f)
    k = kernel.wcnf.n_vars
    gain = 1.0 - k / occurring if occurring else 0.0
    orig_max = (wcnf.counts()["max_len"] if getattr(wcnf, "is_compact", False)
                else max((len(cl.lits) for cl in wcnf.clauses), default=0))
    f.update(kernel_n_vars=k, kernel_n_clauses=len(kernel.wcnf.clauses), kernel_n_hard=kernel.n_hard,
             kernel_const=kernel.const, kernel_max_len=kernel.max_len, kernel_gain=round(gain, 6))
    if gain < g["gain_min"]:
        return GateResult("skipped_gain", None, f)
    if kernel.max_len > orig_max:
        return GateResult("skipped_length", None, f)
    return GateResult("kernel_empty" if k == 0 else "kernel", kernel, f)
