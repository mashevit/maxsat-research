"""Hard-clause support for the memetic solver (`impl: hard`), milestones H2-H3.

Plan: docs/current/HARD_CLAUSE_SOLVER_PLAN.md §4, §6a (repo). Changes in this
tree are logged in PROVENANCE.md.

`impl: hard` is v2 (incremental polish, cached crossover statics) plus:

  H2
  1. Glucose initialisation. Every population member is a model of the HARD
     clauses only, found by PySAT's Glucose4 with preferred phases drawn per
     member (JW prior over the soft clauses, or fair coins), so the members
     differ. A SAT solver supplies feasibility and no objective information;
     its time is charged to the run clock. RC2 never seeds the solver.
  2. Mutation checks the CHILD's hard clauses (v1/v2 pass `mutate1` the vector
     of the last initial member; CORPUS_FREEZE_PREP.md §8.2).
  3. Polish counts no-op steps against the step budget
     (walksat_polish_v2(..., budget_counts_noops=True)).
  4. Feasibility bookkeeping (`HardStats`), reported under the result key `hard`.

  H3 (one SAT-based operator, two uses; both on by default, switchable)
  5. Repair R(x): Glucose on the hard clauses with x as preferred phases
     returns a hard-feasible assignment near x. Applied to every child after
     crossover + mutation, so children are feasible whenever the hard part is
     satisfiable and the deadline allows the call.
  6. Feasible move M(x): pick an unsatisfied soft clause (weight-proportional),
     assume one of its literals, re-solve the hard clauses with x as phases.
     The result is feasible, satisfies that clause, and may change many
     variables at once -- the move single hard-safe flips cannot make (on
     ja-maxham-00000385 99.99 % of hard-safe flip steps were no-ops, plan §6a).
     Accepted when the cost does not get worse, or with probability `noise`.
  The SAT solver only ever sees hard clauses, assumptions and phases: it is
  given no objective information (plan §8.4 "roles" rule).

  Keep-satisfied moves (opt-in `hard.moves.keep_sat`, strong tree 2026-10-21;
  docs/current2/KS2_CHECK_RUN.md, N-2026-10-21-d, repo)
  7. `ks`: when the drawn soft clause is a unit, the move first assumes its
     literal TOGETHER WITH every currently satisfied unit soft literal. A model
     then satisfies the target and keeps every satisfied unit; when all soft
     clauses are units the move strictly lowers the cost. Acceptance is move
     6's rule. On UNSAT or a budget stop it falls back to move 6 unchanged.
  8. `ks2`: as `ks`, but on UNSAT it reads Glucose's core over the
     assumptions and, when the target is in it, retries once without the
     kept literals the core names; only then does it fall back to move 6.
  Default `none`: move 6 exactly as before (same calls, same RNG draws).
  Assumptions are literals of soft clauses, as move 6 already assumes; the
  solver still sees no weights.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Tuple

from .population import hash_assign, jw_priors
from sat.walksat_v2 import walksat_polish_v2

PHASE_MODES = ("jw", "random")
KEEP_SAT_MODES = ("none", "ks", "ks2")


def hard_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    h = cfg.get("hard") or {}
    phases = str(h.get("phases", "jw")).lower()
    if phases not in PHASE_MODES:
        raise ValueError(f"hard.phases must be one of {PHASE_MODES}, got {phases!r}")
    mv = h.get("moves") or {}
    keep_sat = str(mv.get("keep_sat", "none")).lower()
    if keep_sat not in KEEP_SAT_MODES:
        raise ValueError(f"hard.moves.keep_sat must be one of {KEEP_SAT_MODES}, got {keep_sat!r}")
    return {
        "phases": phases,
        # Glucose calls allowed per member before duplicates are accepted.
        "max_tries_per_member": int(h.get("max_tries_per_member", 3)),
        "repair": bool(h.get("repair", True)),
        "moves_per_polish": int(mv.get("per_polish", 200)),
        "move_noise": float(mv.get("noise", 0.05)),
        # Glucose conflicts allowed per move call (<= 0: unlimited). Over budget,
        # the literal is skipped (no proof); a clause that runs over budget
        # `max_budget_misses` times is set aside for the rest of the run.
        "move_conf_budget": int(mv.get("conf_budget", 5000)),
        "move_max_budget_misses": int(mv.get("max_budget_misses", 3)),
        "move_keep_sat": keep_sat,
    }


@dataclass
class HardStats:
    status: str = "ok"                 # ok | hard_unsat | glucose_timeout
    glucose_init_s: float = 0.0
    glucose_calls: int = 0             # initialisation calls
    init_members: int = 0
    init_distinct: int = 0
    init_infeasible: int = 0           # must be 0: every member is a Glucose model
    init_best_cost: Optional[float] = None   # unsatisfied soft weight of the best initial member
    children: int = 0
    # After crossover + mutation, before repair and polish. With the
    # child-correct guard, mutation never breaks a satisfied hard clause, so
    # this is crossover's doing.
    children_infeasible_before_polish: int = 0
    children_infeasible_after_polish: int = 0
    hv_max_child_after_polish: int = 0
    polish_calls: int = 0
    polish_steps: int = 0
    polish_noop_steps: int = 0
    # H3: repair R
    repair_calls: int = 0
    repair_failed: int = 0             # interrupted at the deadline (child left infeasible)
    repair_s: float = 0.0
    repair_hamming_sum: int = 0        # variables changed by repairs, summed
    # H3: feasible move M
    move_calls: int = 0                # Glucose calls made by moves
    moves_tried: int = 0               # moves attempted (one clause each)
    moves_sat: int = 0                 # moves that produced a model
    moves_unsat_clause: int = 0        # no literal of the clause is consistent with the hard part
    # Singleton cores: soft clauses PROVEN unsatisfiable together with the hard
    # clauses (every literal, assumed alone, gave UNSAT) -- an unsatisfiable
    # core of size one, the simplest object a core-guided solver such as RC2
    # finds. Never drawn again. Their summed weight is a proven lower bound on
    # the optimum, but a weak one: cores of two or more soft clauses are never
    # detected (moves assume one literal at a time), so it is a diagnostic,
    # never comparable with RC2's bound. If the best cost ever equals it, that
    # run has proven its own optimum.
    singleton_cores: int = 0
    singleton_core_lb: float = 0.0
    move_budget_misses: int = 0        # move calls stopped by the conflict budget (no proof)
    clauses_set_aside: int = 0         # clauses no longer drawn after repeated budget misses (not a bound)
    moves_accepted: int = 0
    moves_improving: int = 0
    move_s: float = 0.0
    # Keep-satisfied moves (hard.moves.keep_sat ks / ks2); all 0 when none.
    ks_calls: int = 0                  # moves that tried the keep-satisfied call first
    ks_sat: int = 0                    # ... and got a model (strictly improving)
    ks_unsat: int = 0
    ks_budget: int = 0                 # stopped by the conflict budget (no proof)
    ks_core_len_sum: int = 0           # ks2: summed core sizes on UNSAT
    ks2_retries: int = 0               # ks2: retries without the core's kept literals
    ks2_sat: int = 0
    ks_fallbacks: int = 0              # moves that went on to move 6
    incumbent_infeasible_events: int = 0   # must stay 0 once a feasible member exists
    hard_feasible_final: Optional[bool] = None

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        for k in ("glucose_init_s", "repair_s", "move_s"):
            d[k] = round(d[k], 4)
        return d


def _hard_clause_lists(wcnf) -> List[List[int]]:
    if getattr(wcnf, "is_compact", False):   # streamed from the C arrays (COMPILED_MEMETIC_PLAN.md C3.2)
        from sat.compact import HardClauses
        return HardClauses(wcnf)
    return [list(cl.lits) for cl in wcnf.clauses if cl.is_hard]


class HardSAT:
    """One Glucose4 loaded with the hard clauses, reused for a whole run.

    `model(phases, assumptions, deadline, conf_budget)` -> ("sat", assignment) |
    ("unsat", None) | ("timeout", None) | ("budget", None). The assignment is
    1-based; variables Glucose does not decide keep their value in `phases`.
    Learned clauses persist across calls. `conf_budget` (conflicts) bounds one
    call; None or <= 0 means unlimited (only the deadline applies).
    """

    def __init__(self, wcnf):
        from pysat.solvers import Glucose4  # imported lazily: v1/v2 runs never need it
        self.n = wcnf.n_vars
        self.s = Glucose4(bootstrap_with=_hard_clause_lists(wcnf))
        self.calls = 0

    def model(self, phases: List[bool], assumptions: Tuple[int, ...] = (),
              deadline: Optional[float] = None,
              conf_budget: Optional[int] = None) -> Tuple[str, Optional[List[bool]]]:
        n, s = self.n, self.s
        remaining = None if deadline is None else deadline - time.time()
        if remaining is not None and remaining <= 0:
            return "timeout", None
        s.set_phases([v if phases[v] else -v for v in range(1, n + 1)])
        s.conf_budget(conf_budget if conf_budget and conf_budget > 0 else -1)
        timer = None
        if remaining is not None:
            timer = threading.Timer(remaining, s.interrupt)
            timer.start()
        try:
            ok = s.solve_limited(assumptions=list(assumptions), expect_interrupt=True)
        finally:
            if timer is not None:
                timer.cancel()
            s.clear_interrupt()
        self.calls += 1
        if ok is None:
            if remaining is not None and time.time() >= deadline - 1e-3:
                return "timeout", None
            return ("budget", None) if conf_budget and conf_budget > 0 else ("timeout", None)
        if ok is False:
            return "unsat", None
        a = phases[:]
        for lit in s.get_model() or []:
            v = abs(lit)
            if v <= n:
                a[v] = lit > 0
        return "sat", a

    def core(self) -> List[int]:
        """The assumption literals of the last UNSAT answer (Glucose's core)."""
        return list(self.s.get_core() or [])

    def close(self) -> None:
        if self.s is not None:
            self.s.delete()
            self.s = None


def glucose_init(wcnf, size: int, rng, phases: str, deadline: float,
                 max_tries_per_member: int = 3,
                 sat: Optional[HardSAT] = None) -> Tuple[List[List[bool]], HardStats]:
    """`size` hard-feasible assignments (1-based, index 0 unused) and the stats.

    Each member is a Glucose model under freshly drawn preferred phases
    (JW prior or coins); undecided variables keep the drawn phase. Duplicates
    are retried up to `max_tries_per_member` calls per member, then accepted.
    Every call is interrupted at `deadline`. Pass `sat` to reuse a run's
    solver; otherwise a private one is created and closed here.
    """
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

    own = sat is None
    sat = sat or HardSAT(wcnf)
    try:
        calls_left = max(1, size * max_tries_per_member)
        while len(members) < size and calls_left > 0:
            status, a = sat.model(draw(), (), deadline)
            st.glucose_calls += 1
            calls_left -= 1
            if status == "unsat":
                st.status = "hard_unsat"
                break
            if status == "timeout":
                break
            h = hash_assign(a)
            last_chance = calls_left < (size - len(members))
            if h in seen and not last_chance:
                continue
            seen.add(h)
            members.append(a)
    finally:
        if own:
            sat.close()

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


# --- soft-side cost (the hard side is guaranteed by Glucose models) ----------

class SoftView:
    """Soft clauses as (weight, lits); cost = unsatisfied soft weight."""

    def __init__(self, wcnf):
        self.clauses = [(float(cl.weight), tuple(cl.lits)) for cl in wcnf.clauses if not cl.is_hard]
        self.singleton_cores = set()   # indices proven unsatisfiable with the hard part (per run)
        self.set_aside = set()  # indices dropped after repeated budget misses (no proof)
        self.misses = {}        # index -> budget misses so far

    @staticmethod
    def _sat(lits, a) -> bool:
        for l in lits:
            if (l > 0 and a[l]) or (l < 0 and not a[-l]):
                return True
        return False

    def cost(self, a: List[bool]) -> float:
        return sum(w for w, lits in self.clauses if not self._sat(lits, a))

    def unsat(self, a: List[bool]) -> List[Tuple[int, float, tuple]]:
        """Unsatisfied soft clauses that are neither singleton cores nor set aside: (index, weight, lits)."""
        return [(i, w, lits) for i, (w, lits) in enumerate(self.clauses)
                if i not in self.singleton_cores and i not in self.set_aside and not self._sat(lits, a)]


def repair(x: List[bool], sat: HardSAT, deadline: float, st: HardStats) -> Optional[List[bool]]:
    """R(x): a hard-feasible assignment near x, or None if the deadline cut the call."""
    t0 = time.time()
    status, y = sat.model(x, (), deadline)
    st.repair_calls += 1
    st.repair_s += time.time() - t0
    if status != "sat":
        st.repair_failed += 1
        return None
    if isinstance(x, bytearray) and isinstance(y, bytearray):   # compact: in C, same count
        from sat.compact import hamming
        st.repair_hamming_sum += hamming(x, y)
    else:
        st.repair_hamming_sum += sum(1 for v in range(1, len(x)) if x[v] != y[v])
    return y


def _keep_sat_move(cur: List[bool], soft: SoftView, sat: HardSAT, lit: int, mode: str,
                   deadline: float, conf_budget: Optional[int], st: HardStats) -> Optional[List[bool]]:
    """Moves 7/8: the target unit literal plus every satisfied unit soft literal."""
    if hasattr(soft, "unit_sat_lits"):        # CSoftView: the same tuple, scanned in C
        keep = soft.unit_sat_lits(cur)
    else:
        keep = tuple(c[0] for _, c in soft.clauses
                     if len(c) == 1 and (cur[c[0]] if c[0] > 0 else not cur[-c[0]]))
    st.ks_calls += 1
    status, y = sat.model(cur, (lit,) + keep, deadline, conf_budget)
    st.move_calls += 1
    if status == "sat":
        st.ks_sat += 1
        return y
    if status == "budget":
        st.ks_budget += 1
        return None
    if status != "unsat":
        return None
    st.ks_unsat += 1
    if mode != "ks2":
        return None
    core = set(sat.core())
    st.ks_core_len_sum += len(core)
    if lit not in core or len(core) < 2:
        return None
    st.ks2_retries += 1
    status, y = sat.model(cur, (lit,) + tuple(l for l in keep if l not in core), deadline, conf_budget)
    st.move_calls += 1
    if status == "sat":
        st.ks2_sat += 1
        return y
    return None


def feasible_moves(x: List[bool], soft: SoftView, sat: HardSAT, rng, n_moves: int,
                   noise: float, deadline: float, st: HardStats,
                   conf_budget: Optional[int] = None, max_misses: int = 3,
                   keep_sat: str = "none") -> List[bool]:
    """Up to `n_moves` moves M from a hard-feasible x; returns the best state seen.

    One move: draw an unsatisfied soft clause with probability proportional to
    its weight; try its literals in random order as a single assumption, with
    the current state as phases; the first model found is the candidate. It
    replaces the current state if its cost is not higher, or with probability
    `noise`. A clause none of whose literals is consistent with the hard part
    is a proven singleton core: it is recorded in `soft.singleton_cores`, never
    drawn again, and its weight is added to `singleton_core_lb`.
    """
    t0 = time.time()
    cur, cur_cost = x, soft.cost(x)
    best, best_cost = cur, cur_cost
    for _ in range(n_moves):
        if time.time() >= deadline:
            break
        un = soft.unsat(cur)
        if not un:
            break
        r = rng.random() * sum(w for _, w, _ in un)
        acc = 0.0
        for ci, w, lits in un:
            acc += w
            if acc >= r:
                break
        st.moves_tried += 1
        if keep_sat != "none" and len(lits) == 1:
            cand = _keep_sat_move(cur, soft, sat, lits[0], keep_sat, deadline, conf_budget, st)
            if cand is not None:
                # Same acceptance as move 6. With only unit soft clauses the
                # model is strictly better; a non-unit soft clause is not kept
                # and can still break.
                st.moves_sat += 1
                c = soft.cost(cand)
                if c <= cur_cost or rng.random() < noise:
                    st.moves_accepted += 1
                    if c < cur_cost:
                        st.moves_improving += 1
                    cur, cur_cost = cand, c
                    if cur_cost < best_cost:
                        best, best_cost = cur, cur_cost
                continue
            st.ks_fallbacks += 1
        order = list(lits)
        rng.shuffle(order)
        cand = None
        n_unsat = 0
        for lit in order:
            status, y = sat.model(cur, (lit,), deadline, conf_budget)
            st.move_calls += 1
            if status == "sat":
                cand = y
                break
            if status == "timeout":
                break
            if status == "budget":
                st.move_budget_misses += 1
                soft.misses[ci] = soft.misses.get(ci, 0) + 1
                if soft.misses[ci] >= max_misses:
                    soft.set_aside.add(ci)
                    st.clauses_set_aside = len(soft.set_aside)
                continue
            n_unsat += 1
        if cand is None:
            if n_unsat == len(order):     # every literal refuted: a proof, not a timeout
                st.moves_unsat_clause += 1
                soft.singleton_cores.add(ci)
                st.singleton_cores = len(soft.singleton_cores)
                st.singleton_core_lb += w
            continue
        st.moves_sat += 1
        c = soft.cost(cand)
        if c <= cur_cost or rng.random() < noise:
            st.moves_accepted += 1
            if c < cur_cost:
                st.moves_improving += 1
            cur, cur_cost = cand, c
            if cur_cost < best_cost:
                best, best_cost = cur, cur_cost
    st.move_s += time.time() - t0
    return best


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
