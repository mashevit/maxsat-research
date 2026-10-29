"""CompactWCNF: the instance as flat C arrays (docs/current2/COMPILED_MEMETIC_PLAN.md C1).

`load(path)` parses with the C parser (src/native/ls_core.c `wcnf_parse`, the
rules of WCNF.parse_dimacs) into CSR arrays: literals int32, clause offsets
int32, weights int64 (Clause.weight), hard flags uint8. About 1.2x the file
size, instead of the ~20x of Clause objects plus pos_adj/neg_adj.

A CompactWCNF stands in for a WCNF wherever the solver reads one:
- `n_vars`, `hard_weight`, `is_wcnf`, `m`;
- `clauses`: a read-only view; each access builds the Clause (code not yet
  moved to C keeps working, at Python speed);
- `pos_adj` / `neg_adj`: built on first access only;
- the once-per-run passes (counts, screen, JW priors, evaluation) run in C
  through the methods below, and `sat.compact.dispatch` helpers let the
  existing call sites use them without changing their results.

`from_wcnf(w)` compacts a Python WCNF (a kernel). Nothing here draws a random
number; tests/test_compact.py checks every value against the Python code.
"""
from __future__ import annotations

import ctypes as C
from typing import Iterator, List, Optional, Tuple

from .cnf import WCNF, Clause


class ClauseView:
    """`wcnf.clauses` of a CompactWCNF: len, index, iterate; values as Clause."""

    __slots__ = ("_cw",)

    def __init__(self, cw: "CompactWCNF") -> None:
        self._cw = cw

    def __len__(self) -> int:
        return self._cw.m

    def _make(self, i: int) -> Clause:
        ci = self._cw._ci
        a, b = ci.lit_off[i], ci.lit_off[i + 1]
        return Clause(weight=int(ci.w[i]), lits=ci.lits[a:b] if b > a else [], is_hard=bool(ci.hard[i]))

    def __getitem__(self, i):
        m = self._cw.m
        if isinstance(i, slice):
            return [self._make(j) for j in range(*i.indices(m))]
        if i < 0:
            i += m
        if not 0 <= i < m:
            raise IndexError("clause index out of range")
        return self._make(i)

    def __iter__(self) -> Iterator[Clause]:
        for i in range(self._cw.m):
            yield self._make(i)


class CompactWCNF:
    is_compact = True

    def __init__(self, ci, lib) -> None:
        self._ci = ci
        self._lib = lib
        self.n_vars = int(ci.n)
        self.m = int(ci.m)
        self.hard_weight = int(ci.top)
        self.is_wcnf = bool(ci.is_wcnf)
        self._pos_adj = self._neg_adj = None
        self._counts = None
        self._bound = None

    def __del__(self):
        ci, lib = getattr(self, "_ci", None), getattr(self, "_lib", None)
        if ci is not None and lib is not None:
            try:
                lib.wcnf_free(C.byref(ci))
            except Exception:
                pass
            self._ci = None

    # ------------------------------------------------------------ WCNF interface
    @property
    def clauses(self) -> ClauseView:
        return ClauseView(self)

    def _adj(self) -> None:
        ci = self._ci
        pos: List[List[int]] = [[] for _ in range(self.n_vars + 1)]
        neg: List[List[int]] = [[] for _ in range(self.n_vars + 1)]
        for c in range(self.m):
            for q in range(ci.lit_off[c], ci.lit_off[c + 1]):
                lit = ci.lits[q]
                (pos[lit] if lit > 0 else neg[-lit]).append(c)
        self._pos_adj, self._neg_adj = pos, neg

    @property
    def pos_adj(self) -> List[List[int]]:
        if self._pos_adj is None:
            self._adj()
        return self._pos_adj

    @property
    def neg_adj(self) -> List[List[int]]:
        if self._neg_adj is None:
            self._adj()
        return self._neg_adj

    def iter_clause_lits(self) -> Iterator[Tuple[int, bool, List[int]]]:
        """(weight, is_hard, lits) per clause in order: the values of `clauses`
        without building a Clause (the kernel's streamed input)."""
        ci = self._ci
        off, lits, w, hard = ci.lit_off, ci.lits, ci.w, ci.hard
        for i in range(self.m):
            a, b = off[i], off[i + 1]
            yield int(w[i]), bool(hard[i]), (lits[a:b] if b > a else [])

    @property
    def nlits(self) -> int:
        return int(self._ci.nlits)

    # ------------------------------------------------------------ C passes
    def counts(self) -> dict:
        """n_hard, n_soft, soft_w_sum (raw weights; None on int64 overflow), soft_w_max,
        weighted, max_len."""
        if self._counts is None:
            out = (C.c_int64 * 7)()
            self._lib.inst_counts(C.byref(self._ci), out)
            self._counts = {"n_hard": int(out[0]), "n_soft": int(out[1]),
                            "soft_w_sum": None if out[3] else int(out[2]), "soft_w_max": int(out[4]),
                            "weighted": bool(out[5]), "max_len": int(out[6])}
            if self._counts["soft_w_sum"] is None:   # exact Python sum, only on overflow
                self._counts["soft_w_sum"] = sum(int(cl.weight) for cl in self.clauses if not cl.is_hard)
        return self._counts

    def soft_weight_float(self) -> float:
        """sum(float(cl.weight) for soft clauses), in clause order."""
        return float(self._lib.inst_soft_wsum_f(C.byref(self._ci)))

    def screen_counts(self) -> Tuple[int, int]:
        out = (C.c_int64 * 2)()
        if self._lib.inst_screen(C.byref(self._ci), out) != 0:
            raise MemoryError("inst_screen")
        return int(out[0]), int(out[1])

    def jw_priors(self):
        pri = (C.c_double * (self.n_vars + 1))()
        if self._lib.inst_jw(C.byref(self._ci), pri) != 0:
            raise MemoryError("inst_jw")
        return pri

    def nbrs_bound(self) -> int:
        if self._bound is None:
            b = C.c_int64()
            if self._lib.inst_nbrs_bound(C.byref(self._ci), C.byref(b)) != 0:
                raise MemoryError("inst_nbrs_bound")
            self._bound = int(b.value)
        return self._bound

    def evaluate(self, assign01) -> Tuple[float, int, Optional[int], int, int]:
        """(satisfied soft weight as float, hard violations, unsatisfied soft weight
        (None on int64 overflow), unsatisfied soft count, satisfied clauses)."""
        from native.native import u8
        if len(assign01) != self.n_vars + 1:
            raise ValueError("assignment must have n_vars + 1 entries (index 0 unused)")
        f = C.c_double()
        out = (C.c_int64 * 5)()
        self._lib.inst_eval(C.byref(self._ci), u8(assign01), C.byref(f), out)
        return float(f.value), int(out[0]), (None if out[4] else int(out[1])), int(out[2]), int(out[3])


    # ------------------------------------------------------------ per child (C2)
    def hard_tab(self) -> "HardTables":
        t = getattr(self, "_hard_tab", None)
        if t is None:
            t = self._hard_tab = HardTables(self)
        return t

    def xo_cross(self, A, B, p1_better: bool) -> bytearray:
        """clause_aware_crossover1_v2 in C (plan C2.4)."""
        from native.native import u8
        t = self.hard_tab()
        child = bytearray(self.n_vars + 1)
        if self._lib.xo_cross(C.byref(t.h), u8(A), u8(B), 1 if p1_better else 0, u8(child)) != 0:
            raise MemoryError("xo_cross")
        return child

    def hard_satisfied(self, A) -> bytearray:
        """init_hard_satisfied over the hard clauses in instance order (plan C2.5)."""
        from native.native import u8
        t = self.hard_tab()
        hs = bytearray(t.h.m_hard)
        self._lib.hard_sat_init(C.byref(self._ci), C.byref(t.h), u8(A), u8(hs))
        return hs

    def guard(self, child: bytearray) -> "HardGuard":
        return HardGuard(self, child)


class HardTables:
    """The C HardTab of one instance; freed with it."""

    def __init__(self, cw: CompactWCNF) -> None:
        from native.native import _HardTab
        self._lib = cw._lib
        self.h = _HardTab()
        if self._lib.hard_build(C.byref(cw._ci), C.byref(self.h)) != 0:
            self._lib.hard_free(C.byref(self.h))
            raise MemoryError("hard_build")

    def __del__(self):
        try:
            self._lib.hard_free(C.byref(self.h))
        except Exception:
            pass


class HardGuard:
    """v3._guarded_flip's guard for one child: `hsat` (one byte per hard clause) and
    `flip(a, v)` -> bool, in C. `a` must be the child's bytearray."""

    __slots__ = ("cw", "hsat")

    def __init__(self, cw: CompactWCNF, child: bytearray) -> None:
        self.cw = cw
        self.hsat = cw.hard_satisfied(child)

    def flip(self, a: bytearray, v: int) -> bool:
        from native.native import u8
        if not isinstance(a, bytearray):
            raise TypeError("HardGuard.flip needs the child as a bytearray (flipped in place)")
        cw = self.cw
        return bool(cw._lib.hard_guarded_flip(C.byref(cw._ci), C.byref(cw.hard_tab().h), u8(a), u8(self.hsat), v))


class HardClauses:
    """The hard clauses in instance order, one list at a time (Glucose bootstrap):
    the same clauses as hard._hard_clause_lists without holding them all (plan C3.2)."""

    def __init__(self, cw: CompactWCNF) -> None:
        self.cw = cw
        self.n = cw.counts()["n_hard"]

    def __len__(self) -> int:
        return self.n

    def __bool__(self) -> bool:
        return self.n > 0

    def __iter__(self):
        ci = self.cw._ci
        off, lits, hard = ci.lit_off, ci.lits, ci.hard
        for c in range(self.cw.m):
            if hard[c]:
                a, b = off[c], off[c + 1]
                yield lits[a:b] if b > a else []


class CSoftView:
    """hard.SoftView for a CompactWCNF (plan C3.1): the clause scans in C, the weight
    sums in Python over the same floats in the same order. Soft clause i is the i-th
    soft clause of the instance, as in SoftView."""

    def __init__(self, cw: CompactWCNF) -> None:
        self.cw = cw
        self.n_soft = ns = cw.counts()["n_soft"]
        self._idx = (C.c_int32 * max(1, ns))()
        cw._lib.soft_index(C.byref(cw._ci), self._idx)
        self._buf = (C.c_int32 * max(1, ns))()
        self.singleton_cores = set()   # as SoftView
        self.set_aside = set()
        self.misses = {}

    def _w(self, j: int) -> float:
        return float(self.cw._ci.w[self._idx[j]])

    def _lits(self, j: int) -> tuple:
        ci = self.cw._ci
        c = self._idx[j]
        a, b = ci.lit_off[c], ci.lit_off[c + 1]
        return tuple(ci.lits[a:b]) if b > a else ()

    def _unsat_idx(self, a) -> List[int]:
        from native.native import u8
        k = self.cw._lib.soft_unsat(C.byref(self.cw._ci), u8(a), self._buf)
        return self._buf[:k] if k else []

    def cost(self, a) -> float:
        return sum(self._w(j) for j in self._unsat_idx(a))

    def unsat(self, a):
        cores, aside = self.singleton_cores, self.set_aside
        return [(j, self._w(j), self._lits(j)) for j in self._unsat_idx(a) if j not in cores and j not in aside]

    def unit_sat_lits(self, a) -> tuple:
        from native.native import u8
        k = self.cw._lib.soft_unit_sat(C.byref(self.cw._ci), u8(a), self._buf)
        return tuple(self._buf[:k]) if k else ()


def hamming(x, y) -> int:
    from native.native import u8, _lib as nlib
    return int(nlib().u8_hamming(u8(x), u8(y), len(x)))


def _lib():
    from native.native import _lib as nlib
    return nlib()


def load(path: str) -> CompactWCNF:
    """WCNF.parse_dimacs, in C. Raises ValueError with the parser's reason."""
    from native.native import _CInst
    lib = _lib()
    ci = _CInst()
    err = C.create_string_buffer(512)
    if lib.wcnf_parse(path.encode(), C.byref(ci), err, 512) != 0:
        raise ValueError(err.value.decode(errors="replace"))
    return CompactWCNF(ci, lib)


def from_wcnf(w: WCNF) -> CompactWCNF:
    """The same instance as CompactWCNF (used for kernels)."""
    from native.native import _CInst
    lib = _lib()
    m = len(w.clauses)
    off, lits, ws, hard = [0], [], [], []
    for cl in w.clauses:
        lits.extend(cl.lits)
        off.append(len(lits))
        ws.append(int(cl.weight))
        hard.append(1 if cl.is_hard else 0)
    ci = _CInst()
    rc = lib.wcnf_from_arrays(int(w.n_vars), m, int(w.hard_weight), 1 if w.is_wcnf else 0,
                              (C.c_int32 * len(off))(*off), (C.c_int32 * max(1, len(lits)))(*lits),
                              (C.c_int64 * max(1, m))(*ws), (C.c_uint8 * max(1, m))(*hard), C.byref(ci))
    if rc != 0:
        raise MemoryError("wcnf_from_arrays")
    return CompactWCNF(ci, lib)


def is_compact(w) -> bool:
    return getattr(w, "is_compact", False)
