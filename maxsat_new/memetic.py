"""The memetic EA core: `run_memetic` + `build_state` (PORT_NOTES §10 step 7).

Ported from `src/evo/memetic.py:run_memetic` (`:33`) @ 1e3eaaf.

Behavior copied, not text. The per-child pipeline, every RNG draw, and the draw
ORDER are preserved byte-for-byte, because PORT_NOTES §10 step 8 pins this core
against `src/cli/run_ea.py` as an oracle.

Dropped per PORT_NOTES §3: the three nested helper defs (`_assignment_exports`,
`clause_satisfied_bits`, `bits_to_assign01`, `src` `:128-162`), which recomputed
sat-counts a second, redundant way; the cargo-culted `flips_per_sec` / `restarts`
/ `final_noise` zeros; the hardcoded `LLMAdvisor(provider=NoopProvider())`
(`src:43`) — the provider now arrives as an argument, which is the §6 seam.

CORRECTION to PORT_NOTES §1 and §3
----------------------------------
Both claim the block at `src/evo/memetic.py:95-112` is "wrapped in ``''''''''``
string literals -- **dead**", and §3's port map lists it as dropped. That is
wrong, and the port does NOT drop it.

``''''''''`` is eight single quotes. Python tokenizes it as ``''''''`` (an empty
*triple*-quoted string) followed by ``''``, adjacent-literal-concatenated into a
single empty string, which is then an ordinary **expression statement**. It does
not open a block comment, so lines 96-111 are live sibling statements. The AST of
`run_memetic` shows `Expr(Constant(''))` at `:95` and `:112` with `:96-111` as
executable siblings, and a live run confirms the arithmetic: `pop_size=6`,
`max_gens=3` on `mini.wcnf` produces 15 children and **30** `rng.randrange`
draws -- two per child, not one.

So the live `run_ea.py` path makes TWO `rng.randrange(1 << 30)` draws per child:
one for the `rng_seed=` argument of `advisor.propose` (`src:108`), one for the
polish (`src:113`). The advisor draw is consumed and thrown away -- `llm/prompt.py`
and `llm/advisor.py` contain no randomness at all, `NoopProvider.complete`
returns a constant JSON string, and `apply_advice` on the resulting empty advice
is an identity copy. The block's only surviving observable effect is therefore
that one extra draw, and this port preserves it at the §6 hook site (see
`run_memetic`). Dropping it would shift every child's polish seed by one draw and
diverge the whole stream from child #1 onward, breaking step 8's oracle match.

Two clause-index spaces coexist in `run_memetic`; they must not be conflated:

  * `hard_clauses` / `hard_occurs` / `hard_satisfied` are indexed over the
    **hard-only sublist** `[cl for cl in wcnf.clauses if cl.is_hard]`
    (`src:71,74`; `population.init_hard_satisfied`).
  * `build_state`'s `violated_hard` carries **global** `wcnf.clauses` indices,
    per `hardviol.violated_hard_clauses` and STEP_06_NOTES ruling 1.

Out of scope for this step (PORT_NOTES §10): the satisfied->unsat cost conversion
and `best_cost` (step 8); `registry.py` / `solvers.py` (step 8); the JSONL record
(step 9); `RandomPerturbationProvider` / `_provider_seed` (step 11).

No import from `src/`. Imports only stdlib and already-ported `maxsat_new`
modules.
"""
from __future__ import annotations

import math
import random
import time
from typing import Any, Dict, List, Mapping

from .hardviol import violated_hard_clauses
from .operators import clause_aware_crossover1, mutate1, short_polish, tournament
from .population import (
    Individual,
    Population,
    build_hard_occurs,
    evaluate_assignment,
    hash_assign,
)
from .providers import Provider, State, apply_advice


def build_state(instance: Any, child: List[bool], gen: int, seed: int) -> State:
    """Build the read-only `State` snapshot handed to a provider (PORT_NOTES §5).

    Pure: no RNG, no clock, no I/O. That is what makes the §6 invariant hold --
    the whole provider call (`build_state` -> `propose` -> `apply_advice`) draws
    no EA randomness.

    `instance` is first and explicit, so this is a module-level function that can
    be unit-tested without running the EA. PORT_NOTES §10 row 7 sketches
    `build_state(child, gen, seed)`, which reads as a closure over `wcnf`; the
    extra parameter is the only difference.

    Field notes:

    * `assign` is a fresh tuple, never an alias of `child`: a provider cannot
      mutate solver state, and edits come back only via `Advice`.
    * `violated_hard` is ONE `hardviol.violated_hard_clauses` call per child.
      Only the outer list needs wrapping -- the elements are already
      `(int, tuple[int, ...])` (STEP_06_NOTES ruling 2) -- and the indices are
      GLOBAL `wcnf.clauses` indices, not hard-sublist ones.
    * `n_hard_violations` is derived from that same list, so the two agree by
      construction. STEP_06_NOTES flagged "nothing enforces the two agree ...
      step 7's build_state is the natural place for that invariant"; this is it.
    * `seed` is the run's MASTER seed, never RNG state.
    """
    violated = tuple(violated_hard_clauses(instance, child))

    # STEP 7 SIGN CONVENTION -- deliberate, and deliberately not final.
    # `providers.State.cost` is documented as "unsat soft weight, lower better"
    # (PORT_NOTES §5), but `evaluate_assignment` returns *satisfied* soft weight,
    # and STEP_06_NOTES flagged exactly this: "State.cost has no producer yet ...
    # The conversion is §10 row 8's explicit job ... Flagged so the sign
    # convention is settled once, at step 8, not improvised at step 7."
    # So step 7 ships SATISFIED soft weight. Step 8 owns the inversion
    # (`total_soft_weight - satisfied`), and `test_memetic.py` pins the current
    # value so that change surfaces as a failing assertion rather than a silent
    # redefinition. The `int()` cast is exact: `cnf.parse_dimacs` reads every
    # weight with `int()`, so the float accumulator is always integral.
    sat_soft_weight = evaluate_assignment(instance, child)[0]

    return State(
        assign=tuple(child),
        violated_hard=violated,
        cost=int(sat_soft_weight),
        n_hard_violations=len(violated),
        generation=gen,
        seed=seed,
        n_vars=instance.n_vars,
    )


def run_memetic(
    instance: Any,
    params: Mapping[str, Mapping[str, Any]],
    seed: int,
    provider: Provider,
) -> Dict[str, Any]:
    """Run the memetic EA. Signature is PORT_NOTES §10 row 7's four names.

    `instance`: a parsed `cnf.WCNF` (the caller parses; `config.load_and_resolve`
    and `features.extract` already take a wcnf, and step 8's `solvers.py` will
    pass the object).

    `params`: a NESTED mapping with three blocks whose key names are exactly what
    `config.py` already produces, so nothing is renamed at the boundary and the
    §9.4 `time_limit_s` split is preserved structurally::

        {"ea":     <ResolvedConfig.resolved_params>,   # pop_size, polish_flips,
                                                       # tournament_k, pmutate,
                                                       # elitism, elite_frac
         "budget": {"max_gens": int, "time_limit_s": float},
         "polish": <ResolvedConfig.polish>}            # time_limit_s, noise,
                                                       # hard_safe

    Every key is read by subscript -- no `.get` defaults -- so a missing key is a
    `KeyError`, following step 5's no-silent-defaults stance (§9.4). `config.py`
    is deliberately NOT imported: the core stays below the runner layer.

    `seed`: the master seed. `provider`: any `providers.Provider`; step 7 never
    constructs one.

    Determinism: bit-reproducible only when BOTH budgets are iteration-bound --
    `budget.max_gens` for the EA loop (`src:76`) and `ea.polish_flips` for
    `walksat_polish`, whose own `time_up()` (`walksat.py:118`) truncates a polish
    on a slow or loaded machine. Set both `time_limit_s` values large. This
    extends PORT_NOTES §11 Q1, which mentions only the EA-level cap.
    """
    ea = params["ea"]
    budget = params["budget"]
    polish = params["polish"]

    pop_size = int(ea["pop_size"])
    k = int(ea["tournament_k"])
    pmutate = float(ea["pmutate"])
    elitism = bool(ea["elitism"])
    elite_frac = float(ea["elite_frac"])
    polish_flips = int(ea["polish_flips"])

    max_gens = int(budget["max_gens"])
    time_cap = float(budget["time_limit_s"])

    polish_time_limit_s = float(polish["time_limit_s"])
    polish_noise = float(polish["noise"])
    polish_hard_safe = bool(polish["hard_safe"])

    # ONE RNG object (src:51), threaded into Population and the operators by
    # reference; the polish gets a derived integer seed, never the object.
    rng = random.Random(seed)                                        # src:51
    pop = Population(n_vars=instance.n_vars, size=pop_size, rng=rng)  # src:52
    # `init_seeds` accepts a cfg dict and never reads it; src passed the whole
    # config, so `{}` is faithful without touching population.py.
    pop.init_seeds(instance, {})                                     # src:53

    # initial evaluation (src:56-57)
    for ind in pop.members:
        pop.evaluate(instance, ind)

    # PORT_NOTES §9.1 (REPLICATED, NOT FIXED). `ind` is a leaked loop variable:
    # after the loop above it is bound to `pop.members[-1]`, the LAST individual
    # built by `init_seeds`, whose `hard_satisfied` was computed from its own
    # JW-seeded assignment (`population.py:155`) and which `Population.evaluate`
    # never refreshes. `src:93` hands that member's list -- the object itself,
    # not a copy -- to `mutate1`, which writes into it in place
    # (`operators.py:284`). One list, shared and mutated across every child of
    # every generation, indexed over the hard-only sublist, and never
    # corresponding to the child being mutated: `mutate1`'s "don't unsatisfy a
    # satisfied hard clause" guard tests against an assignment that does not
    # exist. The object also outlives its membership -- `pop.members` is replaced
    # each generation (below), but this name keeps it alive for the whole run.
    #
    # Load-bearing for §10 step 8: recomputing it per child, or copying it,
    # changes mutate1's accept/reject pattern and therefore the RNG stream and
    # the final cost. Fix in a later PR with its own before/after test (§11 Q3).
    #
    # The `pop_size == 0` NameError is part of the replicated behavior: `ind` is
    # never bound, and the line below raises exactly as `src:93` does. Do NOT
    # defensively pre-define `ind` -- where run_ea.py fails, the port must fail.
    stale_hard_satisfied = ind.hard_satisfied

    best = pop.best().copy()                                         # src:60

    # start_t is taken AFTER seeding (src:64), so seeding is not charged against
    # the wall cap.
    start_t = time.time()                                            # src:64
    gen = 0
    total_children = 0

    hard_clauses = [cl for cl in instance.clauses if cl.is_hard]      # src:71
    hard_occurs = build_hard_occurs(hard_clauses, instance.n_vars)    # src:74
    flips_t = 0

    while (time.time() - start_t) < time_cap and gen < max_gens:      # src:76
        gen += 1

        # Elites are REFERENCES, not copies (src:81): the objects persist across
        # generations, and `Individual.copy` shares `meta` anyway
        # (`population.py:39`). Flagged in STEP_07_NOTES, not changed.
        if elitism:
            # src:80 hardcoded `0.05 * pop_size`; PORT_NOTES §4 lifts it to the
            # named `elite_frac` const. Byte-identical at elite_frac=0.05.
            elites_cnt = max(1, math.ceil(elite_frac * pop_size))
            elites = sorted(
                pop.members, key=lambda x: x.fitness, reverse=True
            )[:elites_cnt]
        else:
            elites = []

        new_members: List[Individual] = elites.copy()

        while len(new_members) < pop_size:
            p1 = tournament(pop.members, k, rng)                      # src:89
            p2 = tournament(pop.members, k, rng)                      # src:90
            child_bits = clause_aware_crossover1(p1, p2, instance, rng)  # src:91
            mutate1(                                                  # src:93
                child_bits,
                pmutate,
                rng,
                hard_clauses,
                hard_occurs,
                stale_hard_satisfied,  # PORT_NOTES §9.1, see above
            )

            # --- provider hook (PORT_NOTES §6): between mutate and polish ----
            #
            # `build_state` replaces src's `tmp_child = Individual(...)` +
            # `pop.evaluate(...)` (`src:96-97`). Dropping that evaluate is
            # behavior-neutral -- `pop.cache` is a pure memo keyed on the
            # assignment hash, so a hit can only return what a miss would
            # compute -- and `build_state` produces the same two quantities the
            # discarded `tmp_child` held.
            #
            # src fed the advisor `violated_idxs = []` unconditionally, with the
            # real computation commented out (`src:99-101`). `build_state`
            # supplies the real `violated_hard`. Under NoopProvider that is
            # inert: `propose` ignores its argument entirely and returns
            # `Advice()`, so the child bits and the EA RNG stream are identical
            # to src's. See STEP_07_NOTES for the full argument -- it is what
            # step 10's bit-identity claim rests on.
            state = build_state(instance, child_bits, gen, seed)

            # src:108 -- the LIVE draw. In src this was the `rng_seed=` argument
            # of `advisor.propose`, whose value the advisor only interpolated
            # into a prompt string. See the module docstring's correction to
            # PORT_NOTES §1/§3: the block is NOT dead, and this draw is part of
            # the stream that step 8's oracle test pins. Kept as its own
            # statement (rather than an inline argument) so the order against the
            # polish draw does not depend on argument evaluation order, and so it
            # stays provider-independent: switching Noop -> Random at step 11
            # cannot shift the EA stream.
            _ = rng.randrange(1 << 30)

            advice = provider.propose(state)                          # src:104
            # Runs on the child LIST, never on `state.assign` (a tuple);
            # STEP_06_NOTES ruling 3. Identity copy under `Advice()`.
            child_bits = apply_advice(child_bits, advice)              # src:111
            # --- end provider hook -------------------------------------------

            child_bits, flips_t1 = short_polish(                       # src:113
                child_bits,
                instance,
                rng_seed=rng.randrange(1 << 30),
                polish_flips=polish_flips,
                time_limit_s=polish_time_limit_s,
                noise=polish_noise,
                hard_safe=polish_hard_safe,
            )
            flips_t += flips_t1                                        # src:114
            child = Individual(assign01=child_bits, meta={"gen": gen})  # src:115
            pop.evaluate(instance, child)                              # src:116
            new_members.append(child)                                  # src:117
            total_children += 1                                        # src:118

        pop.members = new_members                                      # src:120
        cur_best = pop.best()                                          # src:122
        # Strict `>` (src:123): ties keep the older best.
        if cur_best.fitness > best.fitness:
            best = cur_best.copy()

    # Final numbers come from `population.evaluate_assignment`, byte-for-byte
    # src:166. NOT `cnf.eval_assignment`: that returns satisfied weight over ALL
    # clauses, hard weights included, whereas this is soft-only weight -- a
    # different number (on hardmix.wcnf, 110 vs 10). PORT_NOTES §3's "replace
    # with one cnf.eval_assignment" targets the redundant clause-count block,
    # which is dropped outright.
    soft, hv = evaluate_assignment(instance, best.assign01)
    elapsed = max(1e-9, time.time() - start_t)                         # src:164

    return {
        # SATISFIED soft weight -- src's key name, kept so no key silently
        # changes meaning between steps. Step 8 adds `best_cost` =
        # total_soft_weight - this (PORT_NOTES §8).
        "best_soft_weight": int(soft),
        "hard_violations": int(hv),
        "best_assignment": list(best.assign01),  # copy: callers cannot mutate
        # Bare blake2b-12 hex; step 9's record.py adds the "blake2b-12:" prefix.
        "best_assignment_hash": hash_assign(best.assign01),
        "generations": gen,          # src's meta.ea_generations, §8's name
        "children": total_children,
        "total_flips": int(flips_t),
        "wall_time_s": float(elapsed),  # src's elapsed_sec, §8's name
    }
