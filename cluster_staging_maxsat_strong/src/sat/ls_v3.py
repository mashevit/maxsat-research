"""Polish cores for `impl: v3` (docs/current2/STRONGER_MEMETIC_DESIGN.md §2, §3, §7).

Two cores, same call shape and return keys as sat/walksat_v2.walksat_polish_v2:

  walksat_v3  v2's WalkSAT loop, line for line, with an RNG object (sat/rng.py)
              and two opt-in anti-cycling rules (B1):
                tabu="tenure": a variable flipped at step t is blocked through
                               step t + tenure (+ randbelow(tenure_rand + 1));
                tabu="cc":     configuration checking -- a variable is blocked
                               after its flip until a neighbour (a variable
                               sharing a clause) flips.
              Aspiration: a blocked move is allowed if it gives a new best
              (hard violations first, then soft weight). If every candidate is
              blocked, the least recently flipped one is taken. The rules act
              where the choice is among soft gains (the soft-only path and the
              feasible phase); the hard-repair branch is v2's, unblocked.
              With tabu="none" and an MTRng the result equals v2 exactly.

  dls_v3      the SATLike two-mode dynamic local search (B2; Lei and Cai,
              IJCAI 2018, read in full): dynamic weights dw (hard start at 1,
              soft at their weight); score(v) = change in falsified dynamic
              weight if v flips. If some score > 0, pick by BMS (t draws with
              replacement from the decreasing set, best score, ties least
              recently flipped). Otherwise update weights -- with probability
              sp smooth (satisfied clauses with dw > 1 lose h_inc if hard, 1 if
              soft), else falsified hard clauses gain h_inc and falsified soft
              clauses gain 1 while dw < zeta -- then take a random falsified
              clause (hard first) and flip its best-score variable. The best
              state is tracked on the TRUE cost (hard violations, then
              unsatisfied soft weight) and returned. `dw` may be passed in and
              is then updated in place (`ls.weights: run`).

Every structure whose iteration order affects a decision (the decreasing set,
the falsified lists, the clause variable lists) has a defined order, so the C
core (src/native/ls_core.c) can reproduce these cores exactly with PortableRng.
"""
from __future__ import annotations

import time
from bisect import bisect_left, insort
from typing import Any, Dict, List, Optional

from .walksat_v2 import _static_for

IMPL_WALKSAT = "walksat_v3/1"
IMPL_DLS = "dls_v3/1"
TABU_MODES = ("none", "tenure", "cc")

_V3_ATTR = "_ls_v3_static"
_MODE_ATTR = "_ls_v3_nbrs_mode"

# Neighbour tables (docs/current2/LONG_CLAUSE_RULE_DESIGN.md). `nbrs` costs
# k(k-1) entries per clause of k variables, 61-72 bytes each while built; the
# setcover rail instances (rows of up to 8,919 variables) would need tens of GB.
# Above NBRS_MAX the instance runs "lean": no `nbrs`; CC and PX read the clauses
# instead (same results), walk mutation samples a neighbour by rejection (same
# distribution, other random stream). Every other instance we have has a bound
# of at most 36.9M, so `auto` keeps them on the full tables, unchanged.
NBRS_MODES = ("auto", "full", "lean")
NBRS_MAX = 50_000_000


def _clause_vars(st, ci: int) -> set:
    return {a for a in (abs(l) for l in st.lits[ci]) if 0 < a <= st.n}


def _mode(requested: str, bound: int) -> str:
    return requested if requested != "auto" else ("lean" if bound > NBRS_MAX else "full")


class _V3Static:
    """Per-clause (var, d) lists (DLS) and, by mode, the neighbour lists (CC, PX,
    walk mutation) or their lean replacement: aocc[v], every clause containing v
    (ascending), and cv[c], the distinct variables of clause c (ascending)."""

    __slots__ = ("m", "nbrs", "cvd", "requested", "mode", "bound", "aocc", "cv")

    def __init__(self, cnf, requested: str = "auto") -> None:
        st = _static_for(cnf)
        n, m = st.n, st.m
        self.m = m
        self.requested = requested
        # cvd[c] = [(u, d)], u ascending, d = (#pos - #neg) occurrences of u in c, d != 0
        cvd: List[List[tuple]] = [[] for _ in range(m)]
        for v in range(1, n + 1):
            for ci, d in st.occ[v]:
                cvd[ci].append((v, d))
        self.cvd = cvd
        # The variables of each clause as `nbrs` sees them (every literal, d == 0 included).
        cvs = [sorted(_clause_vars(st, ci)) for ci in range(m)]
        self.bound = sum(len(vs) * (len(vs) - 1) for vs in cvs)
        self.mode = _mode(requested, self.bound)
        self.nbrs = self.aocc = self.cv = None
        if self.mode == "lean":
            aocc: List[List[int]] = [[] for _ in range(n + 1)]
            for ci, vs in enumerate(cvs):
                for a in vs:
                    aocc[a].append(ci)
            self.aocc, self.cv = aocc, cvs
            return
        del cvs
        nb: List[set] = [set() for _ in range(n + 1)]
        for ci in range(m):
            vs = {abs(l) for l in st.lits[ci]}
            for a in vs:
                if 0 < a <= n:
                    nb[a].update(u for u in vs if u != a and 0 < u <= n)
        self.nbrs = [sorted(s) for s in nb]


def set_nbrs_mode(cnf, mode: str) -> None:
    """Choose the neighbour-table mode of `cnf` (ls.nbrs) before its tables are built;
    a cached table built under another request is dropped."""
    mode = str(mode).lower()
    if mode not in NBRS_MODES:
        raise ValueError(f"ls.nbrs must be one of {NBRS_MODES}, got {mode!r}")
    try:
        setattr(cnf, _MODE_ATTR, mode)
    except AttributeError:
        return
    x = getattr(cnf, _V3_ATTR, None)
    if x is not None and x.requested != mode:
        delattr(cnf, _V3_ATTR)


def v3_static(cnf) -> _V3Static:
    x = getattr(cnf, _V3_ATTR, None)
    req = getattr(cnf, _MODE_ATTR, "auto")
    if x is None or x.m != len(getattr(cnf, "clauses", ())) or x.requested != req:
        x = _V3Static(cnf, req)
        try:
            setattr(cnf, _V3_ATTR, x)
        except AttributeError:
            pass
    return x


def nbrs_plan(cnf, requested: str = "auto"):
    """(mode, bound) the tables of `cnf` will have under `requested`, without building
    them: O(sum of clause lengths). auto_hparams R5 reads it before the run."""
    requested = str(requested).lower()
    if requested not in NBRS_MODES:
        raise ValueError(f"ls.nbrs must be one of {NBRS_MODES}, got {requested!r}")
    st = _static_for(cnf)
    bound = 0
    for ci in range(st.m):
        k = len(_clause_vars(st, ci))
        bound += k * (k - 1)
    return _mode(requested, bound), bound


def nbrs_info(cnf):
    """(mode, bound) of the tables built for `cnf`, or (None, None) if none were built."""
    x = getattr(cnf, _V3_ATTR, None)
    return (x.mode, x.bound) if x is not None else (None, None)


def cc_touch_lean(x: _V3Static, conf: List[bool], v: int) -> None:
    """CC after flipping v, from the clauses: conf[u] = True for every u sharing a
    clause with v, then conf[v] = False -- the state the `nbrs` loop leaves."""
    cv = x.cv
    for ci in x.aocc[v]:
        for u in cv[ci]:
            conf[u] = True
    conf[v] = False


# ----------------------------------------------------------------------------- B1

def walksat_v3(
    cnf,
    start_assign: List[bool],
    *,
    rng,
    max_flips: Optional[int] = None,
    time_limit_s: Optional[float] = 0.05,
    noise: float = 0.10,
    hard_safe: bool = True,
    budget_counts_noops: bool = False,
    tabu: str = "none",
    tenure: int = 10,
    tenure_rand: int = 0,
    stats: Optional[Dict[str, int]] = None,
    trace: Optional[list] = None,
    target_unsat: Optional[int] = None,
) -> Dict[str, Any]:
    """`trace` (tests only): when a list, each applied flip appends
    (step, v, how) with how in {"free", "asp", "lru"} under a tabu rule, else "free".
    `target_unsat`: report the first step at which the true cost reached it
    (`target_hit_step`, `target_hit_wall`; src/native/ls_core.c, out[7..8])."""
    if tabu not in TABU_MODES:
        raise ValueError(f"tabu must be one of {TABU_MODES}, got {tabu!r}")
    st = _static_for(cnf)
    n, m = st.n, st.m
    lits, cvars, is_hard, w, occ = st.lits, st.cvars, st.is_hard, st.w, st.occ
    has_hard = st.has_hard
    total_soft = st.total_soft
    randbelow = rng.randbelow
    rand = rng.random

    tabu_on = tabu != "none"
    use_cc = tabu == "cc"
    x3 = v3_static(cnf) if use_cc else None
    nbrs = x3.nbrs if use_cc else None
    cc_lean = use_cc and nbrs is None
    last_flip = [-1] * (n + 1)
    tabu_until = [0] * (n + 1)
    conf = [True] * (n + 1)
    skips = asp = alltabu = 0

    assign = [False]
    assign.extend(bool(b) for b in start_assign)
    tc = [0] * m
    unsat_h: List[int] = []
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
    tgt = -1 if target_unsat is None or target_unsat < 0 else int(target_unsat)
    hit, hit_wall = -1, None
    if tgt >= 0 and not unsat_h and unsat_soft_w <= tgt:
        hit, hit_wall = 0, now()
    NEG_INF = float("-inf")
    POS_INF = float("inf")

    def blocked(v: int) -> bool:
        if use_cc:
            return not conf[v]
        return num_flips <= tabu_until[v]

    def lru(vs):
        b = None
        for v in vs:
            if b is None or last_flip[v] < last_flip[b]:
                b = v
        return b

    while (num_flips if budget_counts_noops else applied) < max_flips and not (
            limit is not None and (now() - start_t) >= limit):
        num_flips += 1
        if unsat_h:
            target = unsat_h[randbelow(len(unsat_h))]
        elif unsat_s:
            target = unsat_s[randbelow(len(unsat_s))]
        else:
            break

        cand = list(cvars[target])
        for i in range(len(cand) - 1, 0, -1):
            j = randbelow(i + 1)
            cand[i], cand[j] = cand[j], cand[i]
        explore = rand() < noise
        chosen_v = None
        how = "free"

        if not has_hard:
            if not tabu_on:
                if explore:
                    chosen_v = cand[0]
                else:
                    best_gain = NEG_INF
                    for v in cand:
                        g = gain_soft(v)
                        if g > best_gain:
                            best_gain = g
                            chosen_v = v
            else:
                soft_now = total_soft - unsat_soft_w
                if explore:
                    for v in cand:
                        if blocked(v):
                            skips += 1
                            continue
                        chosen_v = v
                        break
                else:
                    best_gain = NEG_INF
                    for v in cand:
                        g = gain_soft(v)
                        is_asp = False
                        if blocked(v):
                            if best_hv == 0 and soft_now + g > best_soft:
                                asp += 1
                                is_asp = True
                            else:
                                skips += 1
                                continue
                        if g > best_gain:
                            best_gain = g
                            chosen_v = v
                            how = "asp" if is_asp else "free"
                if chosen_v is None:
                    alltabu += 1
                    chosen_v = lru(cand)
                    how = "lru"
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
            if not tabu_on:
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
            else:
                soft_now = total_soft - unsat_soft_w
                allowed = []
                if explore:
                    for v in cand:
                        _g, br = effect(v)
                        if hard_safe and br > 0:
                            continue
                        allowed.append(v)
                        if blocked(v):
                            skips += 1
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
                        allowed.append(v)
                        is_asp = False
                        if blocked(v):
                            if br < best_hv or (br == best_hv and soft_now + gain > best_soft):
                                asp += 1
                                is_asp = True
                            else:
                                skips += 1
                                continue
                        if (gain > best_gain) or (gain == best_gain and br < best_break):
                            best_gain = gain
                            best_break = br
                            chosen_v = v
                            how = "asp" if is_asp else "free"
                if chosen_v is None and allowed:
                    alltabu += 1
                    chosen_v = lru(allowed)
                    how = "lru"

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
            if trace is not None:
                trace.append((num_flips, v, how))
            if tabu_on:
                last_flip[v] = num_flips
                if cc_lean:
                    cc_touch_lean(x3, conf, v)
                elif use_cc:
                    conf[v] = False
                    for u in nbrs[v]:
                        conf[u] = True
                else:
                    tabu_until[v] = num_flips + tenure + (randbelow(tenure_rand + 1) if tenure_rand > 0 else 0)

        hv = len(unsat_h)
        if hv <= best_hv:
            soft_now = total_soft - unsat_soft_w
            if (hv < best_hv) or (soft_now > best_soft):
                best_hv = hv
                best_soft = soft_now
                trail.clear()
        if hit < 0 and tgt >= 0 and not unsat_h and unsat_soft_w <= tgt:
            hit, hit_wall = num_flips, now()

    elapsed = max(1e-9, now() - start_t)

    hv = len(unsat_h)
    soft = total_soft - unsat_soft_w
    if best_hv == 0:
        soft = best_soft
        hv = 0
    final_1based = assign
    if best_hv <= hv:
        final_1based = assign[:]
        for v in trail:
            final_1based[v] = not final_1based[v]

    if stats is not None:
        stats["tabu_skips"] = stats.get("tabu_skips", 0) + skips
        stats["tabu_aspirations"] = stats.get("tabu_aspirations", 0) + asp
        stats["tabu_all_blocked"] = stats.get("tabu_all_blocked", 0) + alltabu

    return {
        "flips": int(num_flips),
        "best_soft_weight": float(soft),
        "hard_violations": int(hv),
        "total_flips": int(applied),
        "flips_per_sec": float(applied / elapsed),
        "elapsed_sec": float(elapsed),
        "final_assign": [bool(b) for b in final_1based[1:]],
        "impl": IMPL_WALKSAT,
        "noop_steps": int(num_flips - applied),
        "target_hit_step": int(hit),
        "target_hit_wall": hit_wall,
    }


# ----------------------------------------------------------------------------- B2

def init_dynamic_weights(cnf) -> List[int]:
    """SATLike's start: hard clauses 1, soft clauses their weight."""
    st = _static_for(cnf)
    return [1 if st.is_hard[c] else st.w[c] for c in range(st.m)]


def dls_v3(
    cnf,
    start_assign: List[bool],
    *,
    rng,
    max_flips: Optional[int] = None,
    time_limit_s: Optional[float] = 0.05,
    t: int = 15,
    sp: float = 0.01,
    zeta: int = 50,
    h_inc: int = 1,
    dw: Optional[List[int]] = None,
    cc: bool = False,
    stats: Optional[Dict[str, int]] = None,
    _debug_check: bool = False,
    target_unsat: Optional[int] = None,
) -> Dict[str, Any]:
    """`_debug_check` (tests only): after every flip and weight update, recompute
    scores, the decreasing set and the falsified lists from scratch and assert.
    `target_unsat`: as in walksat_v3."""
    st = _static_for(cnf)
    n, m = st.n, st.m
    lits, is_hard, w, occ = st.lits, st.is_hard, st.w, st.occ
    x3 = v3_static(cnf)
    cvd = x3.cvd
    nbrs = x3.nbrs if cc else None
    cc_lean = cc and nbrs is None
    conf = [True] * (n + 1)
    ccb = 0
    randbelow = rng.randbelow
    rand = rng.random
    if dw is None:
        dw = init_dynamic_weights(cnf)
    elif len(dw) != m:
        raise ValueError("dw must have one entry per clause")

    assign = [False]
    assign.extend(bool(b) for b in start_assign)
    tc = [0] * m
    for ci in range(m):
        k = 0
        for lit in lits[ci]:
            if lit > 0:
                if assign[lit]:
                    k += 1
            elif not assign[-lit]:
                k += 1
        tc[ci] = k

    # falsified lists with positions (swap-with-last removal; order is defined)
    fh: List[int] = []
    fs: List[int] = []
    fpos = [-1] * m
    unsat_soft_w = 0
    for ci in range(m):
        if tc[ci] == 0:
            if is_hard[ci]:
                fpos[ci] = len(fh)
                fh.append(ci)
            else:
                fpos[ci] = len(fs)
                fs.append(ci)
                unsat_soft_w += w[ci]

    def f_add(ci: int) -> None:
        lst = fh if is_hard[ci] else fs
        fpos[ci] = len(lst)
        lst.append(ci)

    def f_del(ci: int) -> None:
        lst = fh if is_hard[ci] else fs
        p = fpos[ci]
        last = lst.pop()
        if last != ci:
            lst[p] = last
            fpos[last] = p
        fpos[ci] = -1

    def ind(ci: int, u: int, d: int) -> int:
        old = tc[ci]
        new = old - d if assign[u] else old + d
        if old == 0:
            return 1 if new > 0 else 0
        return -1 if new == 0 else 0

    score = [0] * (n + 1)
    for ci in range(m):  # ind() inlined: the same contributions, without the call
        wc = dw[ci]
        old = tc[ci]
        for u, d in cvd[ci]:
            new = old - d if assign[u] else old + d
            if old == 0:
                if new > 0:
                    score[u] += wc
            elif new == 0:
                score[u] -= wc

    D: List[int] = []
    dpos = [-1] * (n + 1)

    def d_update(u: int) -> None:
        p = dpos[u]
        if score[u] > 0:
            if p < 0:
                dpos[u] = len(D)
                D.append(u)
        elif p >= 0:
            last = D.pop()
            if last != u:
                D[p] = last
                dpos[last] = p
            dpos[u] = -1

    for v in range(1, n + 1):  # == d_update(v) for v ascending (append order)
        if score[v] > 0:
            dpos[v] = len(D)
            D.append(v)

    def adjust(ci: int, delta: int) -> None:
        dw[ci] += delta
        for u, d in cvd[ci]:
            score[u] += delta * ind(ci, u, d)
        for u, _d in cvd[ci]:
            d_update(u)

    stuck = smooths = 0

    def check() -> None:
        sc = [0] * (n + 1)
        for ci in range(m):
            k = 0
            for lit in lits[ci]:
                if (lit > 0 and assign[lit]) or (lit < 0 and not assign[-lit]):
                    k += 1
            assert tc[ci] == k, ("tc", ci)
            for u, d in cvd[ci]:
                sc[u] += dw[ci] * ind(ci, u, d)
        assert sc[1:] == score[1:], "score"
        assert sorted(D) == [v for v in range(1, n + 1) if score[v] > 0], "D"
        assert all(D[dpos[v]] == v for v in D), "dpos"
        assert sorted(fh) == [c for c in range(m) if is_hard[c] and tc[c] == 0], "fh"
        assert sorted(fs) == [c for c in range(m) if not is_hard[c] and tc[c] == 0], "fs"
        assert unsat_soft_w == sum(w[c] for c in fs), "unsat_soft_w"

    def update_weights() -> None:
        nonlocal smooths
        if rand() < sp:
            smooths += 1
            for ci in range(m):
                if tc[ci] > 0 and dw[ci] > 1:
                    adjust(ci, -(h_inc if is_hard[ci] else 1))
        else:
            for ci in fh:
                adjust(ci, h_inc)
            for ci in fs:
                if dw[ci] < zeta:
                    adjust(ci, 1)

    last_flip = [-1] * (n + 1)

    def flip(v: int) -> None:
        nonlocal unsat_soft_w
        for ci, _d in occ[v]:
            wc = dw[ci]
            for u, du in cvd[ci]:
                score[u] -= wc * ind(ci, u, du)
        val = not assign[v]
        assign[v] = val
        sgn = 1 if val else -1
        for ci, d in occ[v]:
            old = tc[ci]
            new = old + sgn * d
            tc[ci] = new
            if old == 0 and new > 0:
                f_del(ci)
                if not is_hard[ci]:
                    unsat_soft_w -= w[ci]
            elif old > 0 and new == 0:
                f_add(ci)
                if not is_hard[ci]:
                    unsat_soft_w += w[ci]
            wc = dw[ci]
            for u, du in cvd[ci]:
                score[u] += wc * ind(ci, u, du)
        for ci, _d in occ[v]:
            for u, _du in cvd[ci]:
                d_update(u)

    best_hv = len(fh)
    best_unsat = unsat_soft_w
    trail: List[int] = []
    applied = 0
    steps = 0
    if max_flips is None:
        max_flips = max(2_000, min(50_000, 10 * n))
    now = time.time
    start_t = now()
    limit = time_limit_s
    tgt = -1 if target_unsat is None or target_unsat < 0 else int(target_unsat)
    hit, hit_wall = -1, None
    if tgt >= 0 and not fh and unsat_soft_w <= tgt:
        hit, hit_wall = 0, now()

    while applied < max_flips and not (limit is not None and (now() - start_t) >= limit):
        steps += 1
        if not fh and not fs:
            break
        if D:
            bv = -1
            if not cc:
                for _ in range(t):
                    v = D[randbelow(len(D))]
                    if bv < 0 or score[v] > score[bv] or (score[v] == score[bv] and last_flip[v] < last_flip[bv]):
                        bv = v
            else:
                # CC (design §6.2): only draws whose configuration changed count;
                # if all t draws are blocked, the best draw is taken anyway.
                ba = -1
                for _ in range(t):
                    v = D[randbelow(len(D))]
                    if ba < 0 or score[v] > score[ba] or (score[v] == score[ba] and last_flip[v] < last_flip[ba]):
                        ba = v
                    if not conf[v]:
                        ccb += 1
                        continue
                    if bv < 0 or score[v] > score[bv] or (score[v] == score[bv] and last_flip[v] < last_flip[bv]):
                        bv = v
                if bv < 0:
                    bv = ba
        else:
            stuck += 1
            update_weights()
            if _debug_check:
                check()
            ci = fh[randbelow(len(fh))] if fh else fs[randbelow(len(fs))]
            bv = ba = -1
            for u, _d in cvd[ci]:
                if ba < 0 or score[u] > score[ba] or (score[u] == score[ba] and last_flip[u] < last_flip[ba]):
                    ba = u
                if cc and not conf[u]:
                    continue
                if bv < 0 or score[u] > score[bv] or (score[u] == score[bv] and last_flip[u] < last_flip[bv]):
                    bv = u
            if bv < 0:
                bv = ba
            if bv < 0:  # a falsified clause with no flippable variable cannot occur
                break
        flip(bv)
        if _debug_check:
            check()
        applied += 1
        trail.append(bv)
        last_flip[bv] = steps
        if cc_lean:
            cc_touch_lean(x3, conf, bv)
        elif cc:
            conf[bv] = False
            for u in nbrs[bv]:
                conf[u] = True
        hv = len(fh)
        if hv < best_hv or (hv == best_hv and unsat_soft_w < best_unsat):
            best_hv = hv
            best_unsat = unsat_soft_w
            trail.clear()
        if hit < 0 and tgt >= 0 and not fh and unsat_soft_w <= tgt:
            hit, hit_wall = steps, now()

    elapsed = max(1e-9, now() - start_t)
    final = assign[:]
    for v in trail:
        final[v] = not final[v]

    if stats is not None:
        stats["dls_stuck"] = stats.get("dls_stuck", 0) + stuck
        stats["dls_smooths"] = stats.get("dls_smooths", 0) + smooths
        stats["dls_cc_blocked"] = stats.get("dls_cc_blocked", 0) + ccb

    return {
        "flips": int(steps),
        "best_soft_weight": float(st.total_soft - best_unsat),
        "hard_violations": int(best_hv),
        "total_flips": int(applied),
        "flips_per_sec": float(applied / elapsed),
        "elapsed_sec": float(elapsed),
        "final_assign": [bool(b) for b in final[1:]],
        "impl": IMPL_DLS,
        "noop_steps": 0,
        "target_hit_step": int(hit),
        "target_hit_wall": hit_wall,
    }
