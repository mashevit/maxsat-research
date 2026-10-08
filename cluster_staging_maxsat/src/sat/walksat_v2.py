"""WalkSAT polish, version 2: incremental bookkeeping, same decisions as v1.

Full reference (v1 measurements, design, equivalence, speed): docs/current/MEMETIC_IMPL_V2.md.

v1 is `src.sat.walksat.walksat_polish` (unchanged, and byte-identical to the
repo copy -- DIVERGENCE.md). Every flip there rescans all m clauses five times:
`unsat_hard_ids()`, `unsat_soft_indices()`, `_count_hard_violations()` twice
(loop and snapshot) and `_soft_objective()`, and copies the whole assignment
whenever the best improves. Cost per flip is O(m); at n = 32 000 that left
~300 flips per 3.5 s polish call (docs/current/CALIB_2SAT_SC.md §10b).

v2 keeps the same search and the same random decisions, with incremental state:

  * unsatisfied hard and soft clauses live in two sorted lists maintained with
    `bisect` (C-level search and memmove). v1 picks `rng.choice(sorted unsat
    list)`; v2 indexes its sorted list with the same single
    `rng._randbelow(len)` call that `choice` makes, and shuffles candidates with
    the same `_randbelow(i + 1)` calls `shuffle` makes. So the trajectory --
    every pick, shuffle, noise draw and flip -- is v1's.
  * hard-violation count and unsatisfied soft weight are counters, O(1).
  * flip effects and true-count updates use per-variable lists of
    (clause, pos_mult - neg_mult), built once per instance and cached on the
    instance object. This is v1's `flip_var_hard_delta` arithmetic (exact under
    repeated literals) applied to the soft gain as well.
  * the best assignment is a flip trail since the last improvement, undone once
    at the end, instead of an O(n) copy per improvement.
  * soft-only instances take a fast path: no hard bookkeeping, and the noise
    branch takes the first shuffled candidate without computing its effect
    (with no hard clauses v1's `br > 0` test can never skip a candidate).
  * clause smoothing is skipped: inside walksat_polish nothing bumps dyn_w, so
    v1's `smooth()` never changes a weight (it only pulls dyn_w > base_w down).

Equivalence (tested in tests/test_walksat_v2.py): with the same start, seed and
flip budget and no time limit, v2 returns exactly v1's final assignment, flip
counts and objective on instances whose clauses contain no repeated variable.
For a clause with a repeated variable v1's per-occurrence soft gain and v2's
exact gain can differ; that is the one intended divergence.

Under a time limit v2 does far more flips per call, so polish results -- and
memetic results -- differ from v1 in the way a faster machine would make them
differ. Seconds-based effort is therefore comparable only within one version;
the version is part of the configuration (top-level `impl`, src/evo/impl_v2.py).
"""
from __future__ import annotations

import random
import time
from bisect import bisect_left, insort
from collections import Counter
from typing import Any, Dict, List, Optional

from .walksat import _extract_clauses

IMPL_VERSION = "walksat_polish_v2/1"

_CACHE_ATTR = "_walksat_v2_static"


class _Static:
    """Instance data that never changes between polish calls."""

    __slots__ = ("n", "m", "lits", "cvars", "is_hard", "w", "occ", "total_soft", "has_hard")

    def __init__(self, cnf) -> None:
        n, clauses, pos_occ, neg_occ = _extract_clauses(cnf)
        self.n = n
        self.m = len(clauses)
        self.lits = [tuple(c.lits) for c in clauses]
        self.cvars = [tuple(abs(l) for l in c.lits) for c in clauses]  # v1's cand_vars order
        self.is_hard = [bool(c.is_hard) for c in clauses]
        self.w = [0 if c.is_hard else int(c.base_w) for c in clauses]
        self.total_soft = sum(self.w)
        self.has_hard = any(self.is_hard)
        # occ[v] = [(ci, d)], d = (#pos occurrences of v in ci) - (#neg ones).
        # Flipping v False->True changes true_cnt[ci] by +d, True->False by -d:
        # exactly what v1's apply_flip does entry by entry. d == 0 (v and -v in
        # the same clause) never changes anything and is dropped.
        occ: List[List[tuple]] = [[] for _ in range(n + 1)]
        for v in range(1, n + 1):
            pc = Counter(pos_occ[v])
            nc = Counter(neg_occ[v])
            seen = set()
            for ci in list(pos_occ[v]) + list(neg_occ[v]):
                if ci in seen:
                    continue
                seen.add(ci)
                d = pc.get(ci, 0) - nc.get(ci, 0)
                if d:
                    occ[v].append((ci, d))
        self.occ = occ


def _static_for(cnf) -> _Static:
    st = getattr(cnf, _CACHE_ATTR, None)
    if st is None or st.m != len(getattr(cnf, "clauses", ())):
        st = _Static(cnf)
        try:
            setattr(cnf, _CACHE_ATTR, st)
        except AttributeError:  # an object that refuses attributes: no cache
            pass
    return st


def walksat_polish_v2(
    cnf,
    start_assign: List[bool],
    *,
    rng_seed: int = 1,
    max_flips: Optional[int] = None,
    time_limit_s: Optional[float] = 0.05,
    noise: float = 0.10,
    hard_safe: bool = True,
    smooth_every: int = 0,  # accepted for signature parity; a no-op (see module doc)
    rho: float = 0.5,       # idem
) -> Dict[str, Any]:
    """Drop-in for walksat.walksat_polish: same arguments, same return keys."""
    st = _static_for(cnf)
    n, m = st.n, st.m
    lits, cvars, is_hard, w, occ = st.lits, st.cvars, st.is_hard, st.w, st.occ
    has_hard = st.has_hard
    total_soft = st.total_soft
    rng = random.Random(rng_seed)
    randbelow = rng._randbelow  # the call random.choice / random.shuffle make
    rand = rng.random

    assign = [False]
    assign.extend(bool(b) for b in start_assign)
    tc = [0] * m
    unsat_h: List[int] = []   # sorted ascending, like v1's list comprehension
    unsat_s: List[int] = []
    unsat_soft_w = 0
    for ci in range(m):
        t = 0
        for lit in lits[ci]:
            if lit > 0:
                if assign[lit]:
                    t += 1
            elif not assign[-lit]:
                t += 1
        tc[ci] = t
        if t == 0:
            if is_hard[ci]:
                unsat_h.append(ci)
            else:
                unsat_s.append(ci)
                unsat_soft_w += w[ci]

    def effect(v: int):
        """(soft gain, hard delta) of flipping v; exact, O(occ(v))."""
        sgn = -1 if assign[v] else 1
        gain = 0
        dh = 0
        for ci, d in occ[v]:
            old = tc[ci]
            new = old + sgn * d
            if is_hard[ci]:
                if old > 0:
                    if new == 0:
                        dh += 1
                elif new > 0:
                    dh -= 1
            elif old > 0:
                if new == 0:
                    gain -= w[ci]
            elif new > 0:
                gain += w[ci]
        return gain, dh

    def gain_soft(v: int) -> int:
        """Soft gain of flipping v when there are no hard clauses."""
        sgn = -1 if assign[v] else 1
        gain = 0
        for ci, d in occ[v]:
            old = tc[ci]
            if old > 0:
                if old + sgn * d == 0:
                    gain -= w[ci]
            elif old + sgn * d > 0:
                gain += w[ci]
        return gain

    # best = the initial state (v1: SatState.__post_init__)
    best_hv = len(unsat_h)
    best_soft = total_soft - unsat_soft_w
    trail: List[int] = []
    applied = 0

    if max_flips is None:
        max_flips = max(2_000, min(50_000, 10 * n))

    now = time.time
    start_t = now()
    limit = time_limit_s
    num_flips = 0
    NEG_INF = float("-inf")
    POS_INF = float("inf")

    while applied < max_flips and not (limit is not None and (now() - start_t) >= limit):
        num_flips += 1
        if unsat_h:
            target = unsat_h[randbelow(len(unsat_h))]
        elif unsat_s:
            target = unsat_s[randbelow(len(unsat_s))]
        else:
            # v1 snapshots here; the state is unchanged since the last snapshot,
            # so the snapshot cannot improve anything.
            break

        cand = list(cvars[target])
        for i in range(len(cand) - 1, 0, -1):  # == rng.shuffle(cand)
            j = randbelow(i + 1)
            cand[i], cand[j] = cand[j], cand[i]
        explore = rand() < noise
        chosen_v = None

        if not has_hard:
            if explore:
                chosen_v = cand[0]
            else:
                best_gain = NEG_INF
                for v in cand:
                    g = gain_soft(v)
                    if g > best_gain:
                        best_gain = g
                        chosen_v = v
        elif unsat_h:
            best_dh = POS_INF
            best_gain = NEG_INF
            for v in cand:
                gain, dh = effect(v)
                if dh >= 0:
                    continue
                if (dh < best_dh) or (dh == best_dh and gain > best_gain):
                    best_dh = dh
                    best_gain = gain
                    chosen_v = v
            if chosen_v is None and explore and is_hard[target] and tc[target] == 0:
                for lit in lits[target]:
                    v = lit if lit > 0 else -lit
                    makes_true = (lit > 0 and not assign[v]) or (lit < 0 and assign[v])
                    if makes_true:
                        _g, dh = effect(v)
                        if (not hard_safe) or (dh < 0):
                            chosen_v = v
                            break
        else:
            if explore:
                for v in cand:
                    _g, br = effect(v)
                    if hard_safe and br > 0:
                        continue
                    chosen_v = v
                    break
            else:
                best_gain = NEG_INF
                best_break = POS_INF
                for v in cand:
                    gain, br = effect(v)
                    if hard_safe and br > 0:
                        continue
                    if (gain > best_gain) or (gain == best_gain and br < best_break):
                        best_gain = gain
                        best_break = br
                        chosen_v = v

        if chosen_v is not None:
            v = chosen_v
            val = not assign[v]
            assign[v] = val
            sgn = 1 if val else -1
            for ci, d in occ[v]:
                old = tc[ci]
                new = old + sgn * d
                tc[ci] = new
                if old == 0:
                    if new > 0:
                        if is_hard[ci]:
                            del unsat_h[bisect_left(unsat_h, ci)]
                        else:
                            del unsat_s[bisect_left(unsat_s, ci)]
                            unsat_soft_w -= w[ci]
                elif new == 0:
                    if is_hard[ci]:
                        insort(unsat_h, ci)
                    else:
                        insort(unsat_s, ci)
                        unsat_soft_w += w[ci]
            applied += 1
            trail.append(v)

        # v1: snapshot_best_if_better() after every iteration
        hv = len(unsat_h)
        if hv <= best_hv:
            soft_now = total_soft - unsat_soft_w
            if (hv < best_hv) or (soft_now > best_soft):
                best_hv = hv
                best_soft = soft_now
                trail.clear()

    elapsed = max(1e-9, now() - start_t)

    # v1's end-of-call selection, on the same quantities.
    hv = len(unsat_h)
    soft = total_soft - unsat_soft_w
    if best_hv == 0:
        soft = best_soft
        hv = 0
    final_1based = assign
    if best_hv <= hv:  # v1: hv_best (recount of best_assign) <= hv_cur
        final_1based = assign[:]
        for v in trail:  # undo the flips made after the best state
            final_1based[v] = not final_1based[v]

    return {
        "flips": int(num_flips),
        "best_soft_weight": float(soft),
        "hard_violations": int(hv),
        "total_flips": int(applied),
        "flips_per_sec": float(applied / elapsed),
        "elapsed_sec": float(elapsed),
        "final_assign": [bool(b) for b in final_1based[1:]],
        "impl": IMPL_VERSION,
    }
