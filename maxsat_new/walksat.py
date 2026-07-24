"""WalkSAT-style local-search polish for the memetic EA.

Ported from src/sat/walksat.py @ 1e3eaaf.

Behavior copied, not text. Ports **`walksat_polish` only** (src :529-693) plus the
`_extract_clauses` helper it depends on. Dropped per PORT_NOTES §3:
  - the `WalkSAT` class (used only by solve.py, not the EA);
  - `run_satlike` (used by solve_batch/bench, not the EA);
  - `_derive_hard_fixed_literals`, `_freeze_hard_units` (unused by polish);
  - `_cfg` (only `run_satlike` reads it);
  - all debug `print()` (none are active in the ported functions; the commented
    `#print` cruft is not carried over either).

No import from src/. Standalone.
"""
from __future__ import annotations

from typing import Dict, Any, List, Tuple, Optional
import time, math, random

from .state import SatState, ClauseInfo


def _extract_clauses(cnf: Any) -> Tuple[int, List[ClauseInfo], List[List[int]], List[List[int]]]:
    # Support: nvars / nv / n_vars
    n = getattr(cnf, "nvars", getattr(cnf, "nv", getattr(cnf, "n_vars", None)))
    if n is None:
        raise ValueError("CNF parser must expose nvars (or nv / n_vars)")

    # Support: pos_occ/neg_occ OR pos_adj/neg_adj
    pos_occ = getattr(cnf, "pos_occ", getattr(cnf, "pos_adj", None))
    neg_occ = getattr(cnf, "neg_occ", getattr(cnf, "neg_adj", None))
    if pos_occ is None or neg_occ is None:
        raise ValueError("CNF parser must expose pos_occ/neg_occ or pos_adj/neg_adj")

    clauses: List[ClauseInfo] = []
    # (a) Parser exposes separate hard/soft lists
    if hasattr(cnf, "hard_clauses") and hasattr(cnf, "soft_clauses"):
        for lits in cnf.hard_clauses:
            clauses.append(ClauseInfo(lits=list(lits), base_w=0, is_hard=True))
        for w, lits in cnf.soft_clauses:
            clauses.append(ClauseInfo(lits=list(lits), base_w=int(w), is_hard=False))
    # (b) Unified arrays with weights/top
    elif hasattr(cnf, "clauses") and hasattr(cnf, "weights"):
        top = getattr(cnf, "top", None)
        if top is None:
            for w, lits in zip(cnf.weights, cnf.clauses):
                is_hard = (w == 0)
                bw = 0 if is_hard else int(w or 1)
                clauses.append(ClauseInfo(lits=list(lits), base_w=bw, is_hard=is_hard))
        else:
            for w, lits in zip(cnf.weights, cnf.clauses):
                is_hard = (w >= top)
                bw = 0 if is_hard else int(w or 1)
                clauses.append(ClauseInfo(lits=list(lits), base_w=bw, is_hard=is_hard))
    # (c) The WCNF class: list of Clause(weight, lits, is_hard)
    elif hasattr(cnf, "clauses") and len(getattr(cnf, "clauses")) > 0 and \
         hasattr(cnf.clauses[0], "lits") and hasattr(cnf.clauses[0], "weight") and hasattr(cnf.clauses[0], "is_hard"):
        for cl in cnf.clauses:
            is_hard = bool(cl.is_hard)
            bw = 0 if is_hard else int(cl.weight or 1)
            clauses.append(ClauseInfo(lits=list(cl.lits), base_w=bw, is_hard=is_hard))
    else:
        # Fallback: treat all as soft weight 1
        for lits in getattr(cnf, "clauses", []):
            clauses.append(ClauseInfo(lits=list(lits), base_w=1, is_hard=False))
        if not clauses:
            raise ValueError("CNF parser interface not recognized.")

    return n, clauses, pos_occ, neg_occ


def walksat_polish(
    cnf: Any,
    start_assign: List[bool],
    *,
    rng_seed: int = 1,
    max_flips: Optional[int] = None,
    time_limit_s: Optional[float] = 0.05,
    noise: float = 0.10,
    hard_safe: bool = True,
    smooth_every: int = 0,
    rho: float = 0.5,
) -> Dict[str, Any]:
    """
    Lightweight WalkSAT-style polish for memetic EA.

    Returns:
      {
        "flips": int,                # see SUSPECTED note below
        "best_soft_weight": float,
        "hard_violations": int,
        "total_flips": int,
        "flips_per_sec": float,
        "elapsed_sec": float,
        "final_assign": List[bool],  # 0-based, len = nvars
      }
    """
    n, clauses, pos_occ, neg_occ = _extract_clauses(cnf)  # must exist in your module
    rng = random.Random(rng_seed)

    # SatState is your dataclass; assign is 1-based internally (index 0 unused)
    state = SatState(
        nvars=n,
        clauses=clauses,
        pos_occ=pos_occ,
        neg_occ=neg_occ,
        rng=rng,
        assign=[False] + [bool(b) for b in start_assign],
    )

    if max_flips is None:
        max_flips = max(2_000, min(50_000, 10 * n))

    start_t = time.time()

    def time_up() -> bool:
        return (time_limit_s is not None) and ((time.time() - start_t) >= time_limit_s)

    def pick_unsat_clause_index() -> int:
        hard_unsat = state.unsat_hard_ids()
        if hard_unsat:
            return rng.choice(hard_unsat)
        soft_unsat = state.unsat_soft_indices()
        if soft_unsat:
            return rng.choice(soft_unsat)
        return -1
    # SUSPECTED (not in §9): the returned "flips" is `num_flips`, which counts loop
    # ITERATIONS (incremented at the top of the loop, before the target==-1 break,
    # and even on iterations where no variable is flipped), not applied flips. The
    # budget `while state.flips < max_flips` and "total_flips" both use `state.flips`
    # (actual applied flips). Kept byte-for-byte; listed in STEP_02_NOTES.md.
    num_flips = 0
    last_smooth = 0
    while state.flips < max_flips and not time_up():
        num_flips += 1
        target = pick_unsat_clause_index()
        if target == -1:
            state.snapshot_best_if_better()
            break

        clause = state.clauses[target]
        cand_vars = [abs(l) for l in clause.lits]
        rng.shuffle(cand_vars)

        hv_now = state._count_hard_violations()
        explore = (rng.random() < noise)

        chosen_v = None

        if hv_now > 0:
            # Reduce hard violations only
            best_dh = math.inf
            best_gain = float("-inf")
            for v in cand_vars:
                gain, _br = state.flip_var_effect(v)
                dh = state.flip_var_hard_delta(v)  # negative => reduces hard
                if dh >= 0:
                    continue
                if (dh < best_dh) or (dh == best_dh and gain > best_gain):
                    best_dh = dh
                    best_gain = gain
                    chosen_v = v

            # Fallback: if nothing reduces hard and we explore, try to make the target clause true (when hard)
            if chosen_v is None and explore and clause.is_hard and clause.true_cnt == 0:
                for lit in clause.lits:
                    v = abs(lit)
                    makes_true = (lit > 0 and not state.assign[v]) or (lit < 0 and state.assign[v])
                    if makes_true:
                        dh = state.flip_var_hard_delta(v)
                        if (not hard_safe) or (dh < 0):
                            chosen_v = v
                            break
        else:
            # Feasible region: don't break hard clauses if hard_safe
            if explore:
                for v in cand_vars:
                    _gain, br = state.flip_var_effect(v)
                    if hard_safe and br > 0:
                        continue
                    chosen_v = v
                    break
            else:
                best_gain = float("-inf")
                best_break = math.inf
                for v in cand_vars:
                    gain, br = state.flip_var_effect(v)
                    if hard_safe and br > 0:
                        continue
                    if (gain > best_gain) or (gain == best_gain and br < best_break):
                        best_gain = gain
                        best_break = br
                        chosen_v = v

        if chosen_v is not None:
            state.apply_flip(chosen_v)

        if smooth_every > 0 and state.flips > 0 and state.flips != last_smooth and (state.flips % smooth_every == 0):
            state.smooth(rho)
            last_smooth = state.flips

        state.snapshot_best_if_better()

    elapsed = max(1e-9, time.time() - start_t)
    hv = state._count_hard_violations()
    soft = state._soft_objective()
    if state.best_assign is not None and state.best_hard_violations == 0:
        soft = state.best_soft_obj
        hv = 0

    # Prefer a final assignment that is at least as feasible as current
    final_1based = state.assign
    if state.best_assign is not None:
        def _count_hard_for(assign_1based: List[bool]) -> int:
            hvb = 0
            for cl in state.clauses:
                satisfied = False
                for lit in cl.lits:
                    v = abs(lit)
                    val = assign_1based[v]
                    if (lit > 0 and val) or (lit < 0 and not val):
                        satisfied = True
                        break
                if not satisfied and cl.is_hard:
                    hvb += 1
            return hvb
        hv_best = _count_hard_for(state.best_assign)
        hv_cur = hv
        if hv_best <= hv_cur:
            final_1based = state.best_assign

    final_assign = [bool(b) for b in final_1based[1:]]
    return {
        "flips": int(num_flips),
        "best_soft_weight": float(soft),
        "hard_violations": int(hv),
        "total_flips": int(state.flips),
        "flips_per_sec": float(state.flips / elapsed),
        "elapsed_sec": float(elapsed),
        "final_assign": final_assign,
    }
