"""Hard-clause support for the memetic solver (`impl: hard`), milestone H2.

Plan: docs/current/HARD_CLAUSE_SOLVER_PLAN.md §4 (repo). Changes in this tree are
logged in PROVENANCE.md.

`impl: hard` is v2 (incremental polish, cached crossover statics) plus:

  1. Glucose initialisation. Every population member is a model of the HARD
     clauses only, found by PySAT's Glucose4 with preferred phases drawn per
     member (JW prior over the soft clauses, or fair coins), so the members
     differ. A SAT solver supplies feasibility and no objective information;
     its time is charged to the run clock. RC2 never seeds the solver.
  2. Mutation checks the CHILD's hard clauses. In v1/v2, memetic.py passes
     `mutate1` the hard-satisfaction vector of the last *initial* member, so
     its "never break a satisfied hard clause" guard tests the wrong assignment
     (CORPUS_FREEZE_PREP.md §8.2; inert on all-soft instances).
  3. Polish counts no-op steps against the step budget
     (walksat_polish_v2(..., budget_counts_noops=True)), so a call on a
     hard-clause instance stops at its budget instead of idling to its time
     limit.
  4. Feasibility bookkeeping (`HardStats`), reported under the result key `hard`.

Not here yet (H3): crossover that keeps hard feasibility. Until then a child
of two feasible parents can be infeasible; it is counted, never hidden. With
Glucose initialisation and elitism the incumbent stays feasible, because an
infeasible individual's fitness (-1e9 - 1e6*hv) is below every feasible one.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .population import hash_assign, jw_priors
from sat.walksat_v2 import walksat_polish_v2

PHASE_MODES = ("jw", "random")


def hard_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    h = cfg.get("hard") or {}
    phases = str(h.get("phases", "jw")).lower()
    if phases not in PHASE_MODES:
        raise ValueError(f"hard.phases must be one of {PHASE_MODES}, got {phases!r}")
    return {
        "phases": phases,
        # Glucose calls allowed per member before duplicates are accepted.
        "max_tries_per_member": int(h.get("max_tries_per_member", 3)),
    }


@dataclass
class HardStats:
    status: str = "ok"                 # ok | hard_unsat | glucose_timeout
    glucose_init_s: float = 0.0
    glucose_calls: int = 0
    init_members: int = 0
    init_distinct: int = 0
    init_infeasible: int = 0           # must be 0: every member is a Glucose model
    init_best_cost: Optional[float] = None   # unsatisfied soft weight of the best initial member
    children: int = 0
    # After crossover + mutation, before polish. With the child-correct guard,
    # mutation never breaks a satisfied hard clause, so this is crossover's doing.
    children_infeasible_before_polish: int = 0
    children_infeasible_after_polish: int = 0
    hv_max_child_after_polish: int = 0
    polish_calls: int = 0
    polish_steps: int = 0
    polish_noop_steps: int = 0
    incumbent_infeasible_events: int = 0   # must stay 0 once a feasible member exists
    hard_feasible_final: Optional[bool] = None

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["glucose_init_s"] = round(self.glucose_init_s, 4)
        return d


def _hard_clause_lists(wcnf) -> List[List[int]]:
    return [list(cl.lits) for cl in wcnf.clauses if cl.is_hard]


def glucose_init(wcnf, size: int, rng, phases: str, deadline: float,
                 max_tries_per_member: int = 3) -> Tuple[List[List[bool]], HardStats]:
    """`size` hard-feasible assignments (1-based, index 0 unused) and the stats.

    One Glucose4 instance is loaded with the hard clauses and re-solved per
    member under new preferred phases. Variables Glucose does not decide (they
    occur in no hard clause, or beyond its variable count) take the drawn
    phase, i.e. the JW prior or a coin. Duplicates are retried with fresh
    phases up to `max_tries_per_member` calls per member, then accepted.
    Every call is interrupted at `deadline` (time.time() seconds).
    """
    from pysat.solvers import Glucose4  # imported here: v1/v2 runs never need it

    st = HardStats()
    t0 = time.time()
    n = wcnf.n_vars
    pri = jw_priors(wcnf) if phases == "jw" else None
    members: List[List[bool]] = []
    seen = set()

    def draw() -> List[bool]:
        a = [False] * (n + 1)
        for v in range(1, n + 1):
            p = pri[v] if pri is not None else 0.5
            a[v] = rng.random() < p
        return a

    with Glucose4(bootstrap_with=_hard_clause_lists(wcnf)) as s:
        calls_left = max(1, size * max_tries_per_member)
        while len(members) < size and calls_left > 0:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            ph = draw()
            s.set_phases([v if ph[v] else -v for v in range(1, n + 1)])
            timer = threading.Timer(remaining, s.interrupt)
            timer.start()
            try:
                ok = s.solve_limited(expect_interrupt=True)
            finally:
                timer.cancel()
                s.clear_interrupt()
            st.glucose_calls += 1
            calls_left -= 1
            if ok is False:
                st.status = "hard_unsat"
                break
            if ok is None:          # interrupted at the deadline
                break
            a = ph[:]               # undecided variables keep their phase
            for lit in s.get_model() or []:
                v = abs(lit)
                if v <= n:
                    a[v] = lit > 0
            h = hash_assign(a)
            last_chance = calls_left < (size - len(members))
            if h in seen and not last_chance:
                continue
            seen.add(h)
            members.append(a)

    if st.status == "ok" and not members:
        st.status = "glucose_timeout"
    # Interrupted before `size` models: fill with copies of the models found
    # (round robin); `init_distinct` records how many differ.
    found = len(members)
    i = 0
    while found and len(members) < size:
        members.append(members[i % found][:])
        i += 1
    st.glucose_init_s = time.time() - t0
    st.init_members = len(members)
    st.init_distinct = len({hash_assign(a) for a in members})
    return members, st


def short_polish_hard(assign01: List[bool], wcnf, ls_cfg: Dict[str, Any],
                      rng_seed: int) -> Tuple[List[bool], int, int]:
    """v2 polish, hard_safe, with no-op steps counted against the step budget.

    Returns (assignment, steps, noop_steps). From a hard-feasible start the
    result is hard-feasible: v2's feasible phase never applies a flip that
    breaks a hard clause, and its end-of-call choice keeps the best state,
    which has hv = 0.
    """
    res = walksat_polish_v2(
        cnf=wcnf,
        start_assign=[bool(b) for b in assign01[1:]],
        rng_seed=rng_seed,
        max_flips=ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips", None)),
        time_limit_s=ls_cfg.get("time_limit_s", 0.05),
        noise=ls_cfg.get("noise", 0.10),
        hard_safe=True,
        budget_counts_noops=True,
    )
    return [False] + [bool(b) for b in res["final_assign"]], res["flips"], res["noop_steps"]
