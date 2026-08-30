# src/evo/multistart.py
"""
Multi-start local search -- the no-EA ablation baseline for the memetic solver.

`configs/tier2/memetic_deeppolish.yaml` is the tier-2 arm closest to "plain
SATLike with a GA restart policy": population 40, and a 12,500-flip WalkSAT
polish applied to every child. The obvious question that arm cannot answer on
its own is whether any of its performance comes from the *evolution* or whether
the polish alone accounts for all of it. This module is that control.

`run_multistart_ls` is deliberately, checkably free of every evolutionary
component:

  * no population   -- exactly one assignment is live at a time. Under
                       `multistart.init: jw` a `Population` object is
                       constructed, with size 0 and no members, purely to reuse
                       its JW draw (`_jw_seeder`); nothing is ever stored in it.
  * no selection    -- there are no parents to select from,
  * no crossover    -- each restart is independent of every previous one,
  * no EA mutation  -- the only bit changes are WalkSAT flips,
  * no generations  -- the loop counts restarts, and `meta.ea_generations` /
                       `meta.children` are reported as None rather than 0 so a
                       downstream row cannot be mistaken for a degenerate EA run.

What it *does* share with the EA is the thing under test: the per-restart polish
is `evo.operators.short_polish` -> `sat.walksat.walksat_polish`, the same call
`run_memetic` makes on every child, driven by the same `ls:` config block
resolved through the same `evo.memetic._ls_budget`. There is no second copy of
the local search here, and the deep-polish limit is read from configuration
(`ls.ls_polish_flips`, 12500 in the deeppolish preset) rather than hard-coded.

Cost convention matches `run_memetic` and `run_memetic_shard`: `target_cost` is
an **unsatisfied** soft weight (the RC2 / `--oracle-cost` convention), while the
solver tracks **satisfied** soft weight, so the comparison is made as
`total_soft_weight - satisfied <= target_cost` at the one site that needs it.

Determinism: everything random is drawn from a single `random.Random(rng_seed)`
-- the initial assignment of each restart, and the per-restart polish seed via
`rng.randrange(1 << 30)`, which is the convention `run_memetic` already uses.
The same (instance, seed, config) therefore replays the same restart sequence:
restart k always starts from the same assignment and polishes it with the same
polish seed.

  CAVEAT, inherited from the preset and shared with the EA arm. That guarantee
  covers the *sequence*, not the *outcome*. `short_polish` stops on whichever of
  `ls.ls_polish_flips` and `ls.time_limit_s` binds first, and under the
  deeppolish preset on the tier-2 SATLIB instances it is the wall clock: 0.5 s
  buys ~5,300 iterations, well short of the 12,500-flip ceiling (measured on
  uuf250-03). So how far each restart gets -- and hence `total_flips`, and in
  general the assignment returned -- depends on machine speed and node load.
  `memetic_deeppolish` has exactly this property, so the two arms stay
  comparable, but neither is bit-reproducible across machines, and "12,500
  flips per restart" is a ceiling rather than the operative budget. Set
  `ls.time_limit_s` high enough for the flip cap to bind if bit-reproducibility
  or a true flip-budget comparison is wanted -- that is a different config id.

Seeding: `multistart.init` chooses how each restart begins. `uniform` (the
default) is an unbiased coin per variable, using no instance structure at all.
`jw` draws from the Jeroslow-Wang prior via `Population._new_assign_from_priors`
-- the exact function `Population.init_seeds` builds the EA's initial population
with, called here rather than copied, so the seeding cannot drift between the
arms. The draw is stochastic per restart, not a single deterministic JW point;
see `_jw_seeder`. The two `init` modes are separate config ids
(`local_multistart_deeppolish`, `local_multistart_jw_deeppolish`) and together
with `memetic_deeppolish` form a three-arm design that separates the EA from the
seeding:

    memetic_deeppolish - local_multistart_jw   population / crossover / EA
    local_multistart_jw - local_multistart     JW initialisation
    memetic_deeppolish - local_multistart      the whole package

Result contract is `run_memetic`'s, so `src/cli/run_memetic_shard.py` consumes
it unchanged, plus three additive keys: `restarts`, `flips_in_target_restart`
and `meta.restarts`.
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional

# `_ls_budget` is imported rather than reimplemented on purpose: it is what
# turns the `ls:` block into the polish budget, and the whole point of this
# baseline is that its polish is configured identically to the EA's. A second
# copy could drift and silently invalidate the ablation.
from .memetic import _ls_budget
from .operators import short_polish
from .population import Population, evaluate_assignment, jw_priors

# Independent of `run_memetic`'s nested `_assignment_exports`, which is left
# untouched: `evo/memetic.py` diverges between the repo and this staging tree
# (see DIVERGENCE.md) and the memetic arm of tier 2 has already been run, so it
# must stay bit-for-bit reproducible. Four lines of formatting, not algorithm.
def _assignment_exports(assign01: List[bool]) -> Dict[str, Any]:
    """Serialisations of a 1-based assignment; index 0 unused."""
    bits = "".join("1" if b else "0" for b in assign01[1:])
    dimacs = "v " + " ".join(str(i if assign01[i] else -i) for i in range(1, len(assign01))) + " 0"
    true_vars = [i for i in range(1, len(assign01)) if assign01[i]]
    return {"assign_bits": bits, "dimacs": dimacs, "true_vars": true_vars}


def _multistart_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    ms = cfg.get("multistart", {}) or {}
    init = str(ms.get("init", "uniform")).lower()
    if init not in ("uniform", "jw"):
        raise ValueError(
            f"multistart.init must be 'uniform' or 'jw', got {init!r}. "
            f"'uniform' is an unbiased random assignment; 'jw' reuses the "
            f"Jeroslow-Wang prior the EA seeds its population from.")
    max_restarts = ms.get("max_restarts", None)
    return {
        "init": init,
        "max_restarts": None if max_restarts is None else int(max_restarts),
    }


def _jw_seeder(wcnf, rng: random.Random) -> "tuple[Population, List[float]]":
    """
    The JW seeding of `Population.init_seeds`, reused rather than reproduced.

    `init_seeds` is two steps: `jw_priors(wcnf)` once, then one call to
    `Population._new_assign_from_priors(pri)` per individual. This returns both,
    so `run_multistart_ls` can perform the second step once per restart -- the
    same biased per-variable draw, from the same code, off the RNG passed in.

    The `Population` here is a *seed factory*, not a population: it is built
    with `size=0`, `init_seeds` is never called on it, `members` stays empty for
    the life of the run, and nothing is ever selected, recombined or mutated.
    The only method used is the draw. `tests/test_local_multistart.py` asserts
    all of that rather than trusting this comment.

    Why not lift the draw into a module-level function in `population.py`, which
    is the cleaner refactor: that file is one of the eight the §2.2 byte-identity
    invariant covers (see ../DIVERGENCE.md), so it cannot be edited here.

    Why not call `init_seeds` per restart, which would be the most literal
    reuse: it recomputes `jw_priors` over every clause and rebuilds the
    hard-clause list and `init_hard_satisfied` on each call. At the restart
    counts a 900 s budget reaches that is an O(n_clauses) per-restart cost borne
    by this arm alone, which would bias the very comparison the arm exists to
    make. Hoisting the prior out of the loop is what `init_seeds` itself does.
    """
    return Population(wcnf.n_vars, 0, rng), jw_priors(wcnf)


def _random_assignment(n_vars: int, rng: random.Random, init: str,
                       seeder: "Optional[Population]" = None,
                       priors: Optional[List[float]] = None) -> List[bool]:
    """
    A fresh 1-based assignment, index 0 unused.

    'uniform' is the honest control for "does the EA help?": no instance
    structure is used at all, so anything the baseline achieves is attributable
    to the polish. 'jw' hands the draw to `Population._new_assign_from_priors`,
    the exact function `Population.init_seeds` builds the EA's initial
    individuals with, so the two arms are seeded by one implementation.

    Both branches draw one `rng.random()` per variable in index order, so they
    consume the RNG stream identically and differ only in the threshold.

    The JW draw is stochastic per call, which is the property that makes this a
    multi-start at all: `jw_priors` clips every prior into [0.05, 0.95], so no
    variable is ever pinned and no two restarts begin from the same point except
    by chance. A deterministic JW assignment would collapse the arm into one
    polish repeated until the budget ran out.
    """
    if init == "jw":
        assert seeder is not None and priors is not None
        return seeder._new_assign_from_priors(priors)
    a = [False] * (n_vars + 1)
    for v in range(1, n_vars + 1):
        a[v] = (rng.random() < 0.5)
    return a


def run_multistart_ls(wcnf, cfg: Dict[str, Any], rng_seed: int = 1,
                      target_cost: int | None = None,
                      max_total_flips: int | None = None) -> Dict[str, Any]:
    """
    Repeat independent random restarts, each polished by the memetic solver's
    own local-search operator, until the target cost is reached or a budget
    runs out.

    Stop conditions, in the order they are checked:
      target        the incumbent reached `target_cost` (feasible only)
      time_cap      `cfg.time_limit_s` elapsed
      flip_budget   `max_total_flips` reached (optional, off by default)
      max_restarts  `cfg.multistart.max_restarts` reached (optional)

    `target_cost=None` disables the target stop entirely -- the run then spends
    its whole budget, and `time_to_target_s` stays None, exactly as in
    `run_memetic`. Reaching the target is only *recorded* when it is also a stop
    condition, so the two arms report the field on the same terms.

    A restart is atomic: the time and flip caps are tested between restarts, not
    inside a polish, so a run can overshoot `time_limit_s` by at most one polish
    (`ls.time_limit_s`, 0.5 s in the deeppolish preset) plus one evaluation.
    That is the same granularity `run_memetic` gives, which checks its cap once
    per generation.
    """
    ms = _multistart_cfg(cfg)
    ls_small = _ls_budget(cfg)

    rng = random.Random(rng_seed)
    # Built once, exactly as `Population.init_seeds` computes the prior once for
    # the whole initial population rather than once per individual.
    seeder, priors = _jw_seeder(wcnf, rng) if ms["init"] == "jw" else (None, None)

    # Same resolution order as `run_memetic`: an injected top-level
    # `time_limit_s` (run_memetic_shard writes the manifest budget there) wins
    # over the per-polish `ls.time_limit_s`.
    time_cap = float(cfg.get("time_limit_s", cfg.get("ls", {}).get("time_limit_s", 10.0)))

    # THE UNIT TRAP (docs/TIER2_MEMETIC_PLAN.md §6.3 trap 1), same as in
    # `run_memetic`: the solver tracks satisfied soft weight, `target_cost` is
    # unsatisfied soft weight. Converted once, at the one comparison site.
    total_soft_weight = sum(float(cl.weight) for cl in wcnf.clauses if not cl.is_hard)

    def _at_target(soft: float, hv: int) -> bool:
        """`<=`, not `==`, and infeasible assignments never qualify -- the same
        predicate `run_memetic._at_target` applies to an Individual."""
        if target_cost is None or hv != 0:
            return False
        return (total_soft_weight - soft) <= target_cost

    start_t = time.time()
    stop_reason: Optional[str] = None
    time_to_target_s: Optional[float] = None
    flips_in_target_restart: Optional[int] = None

    best_assign: Optional[List[bool]] = None
    best_soft = float("-inf")
    best_hv = 0
    restarts = 0
    total_flips = 0

    while stop_reason is None:
        if (time.time() - start_t) >= time_cap:
            stop_reason = "time_cap"
            break
        if max_total_flips is not None and total_flips >= max_total_flips:
            stop_reason = "flip_budget"
            break
        if ms["max_restarts"] is not None and restarts >= ms["max_restarts"]:
            stop_reason = "max_restarts"
            break

        restarts += 1
        assign01 = _random_assignment(wcnf.n_vars, rng, ms["init"], seeder, priors)
        polished, flips = short_polish(
            assign01, wcnf, ls_small, rng_seed=rng.randrange(1 << 30))
        total_flips += int(flips)

        soft, hv = evaluate_assignment(wcnf, polished)

        # Incumbent: fewer hard violations first, then more satisfied soft
        # weight. `Population.evaluate`'s scalar penalty orders identically on
        # the only axis that matters here (hv), and this avoids inventing a
        # penalty constant outside the class that owns it.
        if best_assign is None or (hv, -soft) < (best_hv, -best_soft):
            best_assign, best_soft, best_hv = polished, soft, hv

        if _at_target(best_soft, best_hv):
            stop_reason = "target"
            time_to_target_s = time.time() - start_t
            flips_in_target_restart = int(flips)

    elapsed = max(1e-9, time.time() - start_t)

    # A zero-restart run means the budget was already gone on entry. Emit a
    # scored assignment anyway rather than None, so the shard record is
    # complete and the failure is visible as restarts == 0.
    if best_assign is None:
        best_assign = _random_assignment(wcnf.n_vars, rng, ms["init"], seeder, priors)
        best_soft, best_hv = evaluate_assignment(wcnf, best_assign)

    exports = _assignment_exports(best_assign)
    total_clauses = len(wcnf.clauses)
    unsat_clauses = sum(
        1 for cl in wcnf.clauses
        if not any((lit > 0) == best_assign[abs(lit)] for lit in cl.lits))

    return {
        "best_soft_weight": float(best_soft),
        "hard_violations": int(best_hv),
        "elapsed_sec": float(elapsed),
        "total_flips": int(total_flips),
        "flips_per_sec": float(total_flips / elapsed),
        "restarts": int(restarts),
        "final_noise": 0.0,
        "stop_reason": stop_reason,
        "time_to_target_s": (None if time_to_target_s is None else float(time_to_target_s)),
        "flips_in_target_restart": flips_in_target_restart,
        # ea_generations / children are None, not 0: there is no evolutionary
        # loop here at all, and a 0 would read as "an EA that ran no generations".
        "meta": {
            "ea_generations": None,
            "children": None,
            "restarts": int(restarts),
            **exports,
        },
        "satisfied_clauses": {
            "total": total_clauses,
            "satisfied": total_clauses - unsat_clauses,
            "unsatisfied": unsat_clauses,
        },
    }
