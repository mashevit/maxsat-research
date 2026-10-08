"""Memetic implementation switch: `impl` at the top level of the config.

Why v2 exists, what it changes and how it was checked: docs/current/MEMETIC_IMPL_V2.md.

    impl: v1   # default: the historical code paths, byte for byte
    impl: v2   # same algorithm and same random decisions, faster bookkeeping

v1 is the default, so every existing config keeps its exact behaviour.
operators.py, population.py, sat/walksat.py and sat/state.py are not touched:
they must stay byte-identical to the repo copies (DIVERGENCE.md). v2 replaces
three things, each with an equivalence argument and a test
(tests/test_walksat_v2.py):

  1. polish: walksat_polish_v2 (src/sat/walksat_v2.py) instead of
     walksat.walksat_polish -- incremental unsat bookkeeping, O(occ) per flip
     instead of O(m); same picks, shuffles and flips.
  2. crossover: clause_aware_crossover1_v2 below -- operators.
     clause_aware_crossover1 with its instance-constant parts (soft proxy
     scores, hard-clause occurrence lists) built once per instance instead of
     on every call. Same output.
  3. the pre-polish evaluation of the child and the no-op LLM advisor call in
     memetic.py are skipped. With the NoopProvider (the only provider
     memetic.py constructs) the advice is empty and apply_advice returns an
     unchanged copy; the one side effect that matters, the advisor's
     `rng.randrange(1 << 30)` draw, is kept so the RNG stream is v1's.

Consequence: with flip-limited polish calls (no time limit binding), a v2 run
reproduces the v1 run exactly. Under a time limit v2 does more flips per call
and more generations per second, so results differ the way a faster machine
would make them differ; seconds-based effort is comparable only within one
`impl` (recorded in each shard as `memetic_impl`).
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

from .operators import _soft_proxy_scores, clause_aware_crossover1, short_polish
from sat.walksat_v2 import walksat_polish_v2  # same import style as operators.py

IMPLS = ("v1", "v2")


def memetic_impl(cfg: Dict[str, Any]) -> str:
    impl = str(cfg.get("impl", "v1")).lower()
    if impl not in IMPLS:
        raise ValueError(f"impl must be one of {IMPLS}, got {impl!r}")
    return impl


# --- 1. polish ---------------------------------------------------------------

def short_polish_v2(
    assign01: List[bool],
    wcnf,
    ls_cfg: Dict[str, Any],
    rng_seed: int,
) -> Tuple[List[bool], int]:
    """operators.short_polish with walksat_polish_v2; same inputs and outputs."""
    start_0_based = [bool(b) for b in assign01[1:]]
    res = walksat_polish_v2(
        cnf=wcnf,
        start_assign=start_0_based,
        rng_seed=rng_seed,
        max_flips=ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips", None)),
        time_limit_s=ls_cfg.get("time_limit_s", ls_cfg.get("time_limit_s", 0.05)),
        noise=ls_cfg.get("noise", 0.10),
        hard_safe=ls_cfg.get("hard_safe", True),
        smooth_every=ls_cfg.get("smooth_every", 0),
        rho=ls_cfg.get("rho", 0.5),
    )
    return [False] + [bool(b) for b in res["final_assign"]], res["flips"]


# --- 2. crossover ------------------------------------------------------------

_XO_ATTR = "_crossover_v2_static"


class _XoStatic:
    __slots__ = ("m", "s_true", "s_false", "pos_occ", "neg_occ", "unassigned0", "m_hard")

    def __init__(self, wcnf) -> None:
        n = wcnf.n_vars
        self.m = len(wcnf.clauses)
        # Same function, same summation order as operators.clause_aware_crossover1.
        self.s_true, self.s_false = _soft_proxy_scores(wcnf)
        hard_clauses = [cl for cl in wcnf.clauses if getattr(cl, "is_hard", False)]
        self.m_hard = len(hard_clauses)
        self.unassigned0 = [len(cl.lits) for cl in hard_clauses]
        pos = [[] for _ in range(n + 1)]
        neg = [[] for _ in range(n + 1)]
        for cid, cl in enumerate(hard_clauses):
            for lit in cl.lits:
                v = abs(lit)
                if v == 0 or v > n:
                    continue
                (pos if lit > 0 else neg)[v].append(cid)
        self.pos_occ, self.neg_occ = pos, neg


def _xo_static(wcnf) -> _XoStatic:
    st = getattr(wcnf, _XO_ATTR, None)
    if st is None or st.m != len(wcnf.clauses):
        st = _XoStatic(wcnf)
        try:
            setattr(wcnf, _XO_ATTR, st)
        except AttributeError:
            pass
    return st


def clause_aware_crossover1_v2(p1, p2, wcnf, rng) -> List[bool]:
    """operators.clause_aware_crossover1 with cached instance-constant parts.

    The decision rule per variable is copied unchanged: keep agreeing bits;
    otherwise fewer new hard violations, then more newly satisfied hard
    clauses, then the soft proxy score, then the fitter parent's bit (and the
    never-reached rng.choice branch, kept for fidelity).
    """
    st = _xo_static(wcnf)
    n = wcnf.n_vars
    s_true, s_false = st.s_true, st.s_false
    A, B = p1.assign01, p2.assign01
    child = [False] * (n + 1)

    if st.m_hard == 0:
        # No hard clauses: eval_candidate is (0, 0) for both bits, so the rule
        # reduces to the soft scores and then the fitter parent.
        better = (p1 if p1.fitness >= p2.fitness else p2).assign01
        for v in range(1, n + 1):
            a = A[v]
            if a == B[v]:
                child[v] = a
            else:
                st_v, sf_v = s_true[v], s_false[v]
                if st_v > sf_v:
                    child[v] = True
                elif sf_v > st_v:
                    child[v] = False
                else:
                    child[v] = better[v]
        return child

    pos_occ, neg_occ = st.pos_occ, st.neg_occ
    hard_satisfied = [False] * st.m_hard
    hard_unassigned = list(st.unassigned0)

    def eval_candidate(v: int, val: bool):
        dviol = dsat = 0
        for cid in pos_occ[v]:
            if hard_satisfied[cid]:
                continue
            if val:
                dsat += 1
            elif hard_unassigned[cid] == 1:
                dviol += 1
        for cid in neg_occ[v]:
            if hard_satisfied[cid]:
                continue
            if not val:
                dsat += 1
            elif hard_unassigned[cid] == 1:
                dviol += 1
        return dviol, dsat

    def commit(v: int, val: bool) -> None:
        child[v] = val
        for cid in pos_occ[v]:
            hard_unassigned[cid] -= 1
            if val and not hard_satisfied[cid]:
                hard_satisfied[cid] = True
        for cid in neg_occ[v]:
            hard_unassigned[cid] -= 1
            if (not val) and not hard_satisfied[cid]:
                hard_satisfied[cid] = True

    for v in range(1, n + 1):
        a, b = A[v], B[v]
        if a == b:
            commit(v, a)
            continue
        dv_a, ds_a = eval_candidate(v, a)
        dv_b, ds_b = eval_candidate(v, b)
        if dv_a < dv_b:
            chosen = a
        elif dv_b < dv_a:
            chosen = b
        elif ds_a > ds_b:
            chosen = a
        elif ds_b > ds_a:
            chosen = b
        else:
            st_v, sf_v = s_true[v], s_false[v]
            if st_v > sf_v:
                chosen = True
            elif sf_v > st_v:
                chosen = False
            else:
                better = p1 if p1.fitness >= p2.fitness else p2
                chosen = better.assign01[v]
                if a != b and chosen not in (a, b):
                    chosen = rng.choice([a, b])
        commit(v, chosen)
    return child


# --- selection -----------------------------------------------------------------

def select_polish(cfg: Dict[str, Any]) -> Callable:
    return short_polish_v2 if memetic_impl(cfg) == "v2" else short_polish


def select_crossover(cfg: Dict[str, Any]) -> Callable:
    return clause_aware_crossover1_v2 if memetic_impl(cfg) == "v2" else clause_aware_crossover1
