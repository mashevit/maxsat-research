from __future__ import annotations
from typing import Dict, Any, List
import time, math, random, sys

from .population import Population, Individual, evaluate_assignment, build_hard_occurs
from .operators import tournament, clause_aware_crossover, mutate,mutate1, frozen_hard_unit_vars, short_polish, clause_aware_crossover1
from .impl_v2 import memetic_impl, select_crossover, select_polish
from .population import init_hard_satisfied
from .hard import (HardSAT, HardStats, SoftView, feasible_moves, glucose_init, hard_cfg,
                   repair, short_polish_hard)
from .v3 import (PolishV3, V3Stats, check_cfg, custom_polish, mutate_v3, partition_crossover,
                 resolve_hard_mode, set_nbrs_mode)
from llm.advisor import LLMAdvisor, apply_advice
from llm.providers.noop import NoopProvider
# or: from llm.providers.ollama import OllamaProvider

def _ea_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    ea = cfg.get("ea", {})
    return {
        "enabled": bool(ea.get("enabled", False)),
        "pop_size": int(ea.get("pop_size", 60)),
        "tournament_k": int(ea.get("tournament_k", 4)),
        "pmutate": float(ea.get("pmutate", 0.02)),
        "elitism": bool(ea.get("elitism", True)),
        "ls_polish_flips": int(ea.get("ls_polish_flips", 700)),
    }


POLISH_CAPS = ("flips", "time", "flips_only")


def _ls_budget(cfg: Dict[str, Any]) -> Dict[str, Any]:
    # Small polishing budget by default
    ls = cfg.get("ls", {})
    budget = {
        "ls_polish_flips": int(ls.get("ls_polish_flips", 700)),
        "time_limit_s": float(ls.get("time_limit_s", 0.05)),
        "max_flips": int(ls.get("flip_budget", 2000)),
    }
    # Ported from cluster_staging_maxsat (2026-10-12 / 10-14; this tree, S1).
    # Opt-in `ls.polish_cap: time` (2026-10-12): each polish call ends only on
    # ls.time_limit_s; ls_polish_flips / flip_budget are ignored. Absent or
    # "flips" (every earlier config): unchanged, the first of the two limits ends it.
    # Opt-in `ls.polish_cap: flips_only` (2026-10-14): each polish call ends only on
    # ls_polish_flips; ls.time_limit_s is ignored. With `ea.deadline_mode: clip` the
    # remaining run budget still ends a call, so the run stays inside its time cap.
    cap = str(ls.get("polish_cap", "flips")).lower()
    if cap not in POLISH_CAPS:
        raise ValueError(f"ls.polish_cap must be one of {POLISH_CAPS}, got {cap!r}")
    if cap == "time":
        budget["ls_polish_flips"] = budget["max_flips"] = sys.maxsize
    elif cap == "flips_only":
        budget["time_limit_s"] = math.inf
    return budget


def _v3_dict(v3s: "V3Stats | None", wcnf) -> "Dict[str, Any] | None":
    if v3s is None:
        return None
    v3s.note_nbrs(wcnf)
    return v3s.as_dict()


def _hard_abort(wcnf, hstats: HardStats, elapsed: float, impl: str = "hard",
                v3s: "V3Stats | None" = None) -> Dict[str, Any]:
    """`impl: hard` without a hard-feasible start: the hard clauses are
    unsatisfiable (`hard_unsat`) or Glucose found no model within the run
    budget (`glucose_timeout`). Reported, not hidden: the all-False assignment
    is returned so the shard's re-derived cost and hard-violation count describe
    a real assignment, and stop_reason names the cause."""
    a = [False] * (wcnf.n_vars + 1)
    soft, hv = evaluate_assignment(wcnf, a)
    hstats.hard_feasible_final = hv == 0
    bits = "".join("1" if b else "0" for b in a[1:])
    return {
        "best_soft_weight": float(soft), "hard_violations": int(hv),
        "elapsed_sec": float(max(1e-9, elapsed)), "total_flips": 0, "flips_per_sec": 0.0,
        "restarts": 0, "final_noise": 0.0, "stop_reason": hstats.status,
        "time_to_target_s": None, "impl": impl, "hard": hstats.as_dict(),
        "v3": _v3_dict(v3s, wcnf),
        "meta": {"ea_generations": 0, "children": 0, "assign_bits": bits,
                 "dimacs": "v " + " ".join(str(-i) for i in range(1, len(a))) + " 0",
                 "true_vars": []},
        "satisfied_clauses": None,
    }


_BITS = bytes.maketrans(b"\x00\x01", b"01")


def _soft_weight_float(wcnf) -> float:
    """sum(float(cl.weight) for soft clauses), in clause order (C for a CompactWCNF)."""
    if getattr(wcnf, "is_compact", False):
        return wcnf.soft_weight_float()
    return sum(float(cl.weight) for cl in wcnf.clauses if not cl.is_hard)


def run_memetic(wcnf, cfg: Dict[str, Any], rng_seed: int = 1,
                target_cost: int | None = None) -> Dict[str, Any]:
    """
    Minimal memetic loop:
      - JW seeding
      - tournament selection, clause-aware crossover, mutation
      - (stub) short polish
      - elitist replacement
    Fitness evaluates *assignments directly* (soft weight, penalize hard violations).

    `target_cost` (optional) is a known-optimal **unsatisfied soft weight** — the
    RC2 convention, i.e. what `--oracle-cost` carries. When given, the loop stops
    as soon as the incumbent reaches it, so `elapsed_sec` becomes a real
    time-to-optimum measurement instead of "the budget was spent"
    (docs/archive/TIER2_MEMETIC_PLAN.md §6.6). `None` (the default) preserves the
    historical behaviour exactly: the only stop conditions are `time_cap` and
    `max_gens`.

    Returns, in addition to the historical keys:
      stop_reason       "target" | "time_cap" | "max_gens"
      time_to_target_s  seconds from loop start to first reaching the target,
                        or None if it was never reached / never requested.
      target_hit        (target-stopped runs only, else None; MSE26_RHO_PLAN.md §7)
                        where the target was first reached, to the flip:
                        calls_to_target   polish calls up to and including the
                                          one that reached it (0 = the seeds)
                        flips_to_target   steps of the earlier calls + the step
                                          of that call (the unit of total_flips)
                        target_by         init | pre_polish (crossover, mutation,
                                          hard moves: the child entered the call
                                          at the target) | polish | child (no
                                          counter on this path) | unknown
                        resolution        flip, or call when the polish path
                                          has no counter (v1/v2/hard polish) or
                                          the counter missed (target_by unknown):
                                          then flips_to_target = all flips so far
                        time_to_hit_s     seconds from loop start to that flip
                                          (None at call resolution)
    """

    advisor = LLMAdvisor(provider=NoopProvider())  # swap provider later
    ea = _ea_cfg(cfg)
    pop_size = ea["pop_size"]
    #pop_size = wcnf.n_vars * 2
    k = ea["tournament_k"]
    pmutate = ea["pmutate"]
    elitism = ea["elitism"]

    rng = random.Random(rng_seed)
    pop = Population(n_vars=wcnf.n_vars, size=pop_size, rng=rng)
    # Compact instance (sat/compact.py, COMPILED_MEMETIC_PLAN.md C2): assignments are
    # bytearrays and the per-child work runs in C; same values, same random draws.
    compact = getattr(wcnf, "is_compact", False)
    pop.bytes_assign = compact
    # `impl: hard` (src/evo/hard.py): the population is Glucose models of the
    # hard clauses, and the run clock starts BEFORE them, so Glucose time is
    # charged to the run. v1/v2 keep the JW seeding outside the clock, as before.
    # `impl: v3` (src/evo/v3.py): `hard_mode: auto` turns the hard machinery on
    # only when the instance solved here (the kernel, when kernelising) has hard
    # clauses; without them v3 is v2 (design §8.0: impl hard on soft-only s251
    # made 9 children in 30 s against v2's 365).
    impl0 = memetic_impl(cfg)
    vc = check_cfg(cfg, impl0)
    v3s = V3Stats() if vc is not None else None
    if vc is not None:
        set_nbrs_mode(wcnf, vc["nbrs"])   # before any v3 table is built for this instance
    hard_mode = impl0 == "hard" or (vc is not None and resolve_hard_mode(vc, wcnf))
    if v3s is not None:
        v3s.d["hard_mode"] = "on" if hard_mode else "off"
    hstats = None
    if hard_mode:
        t_run0 = time.time()
        hc = hard_cfg(cfg)
        cap0 = float(cfg.get("time_limit_s", cfg.get("ls", {}).get("time_limit_s", 10.0)))
        # One Glucose for the whole run: initialisation, repair R and moves M
        # share it, so learned clauses carry over (src/evo/hard.HardSAT).
        sat = HardSAT(wcnf)
        if compact:
            from sat.compact import CSoftView
            soft_view = CSoftView(wcnf)
        else:
            soft_view = SoftView(wcnf)
        assigns, hstats = glucose_init(wcnf, pop_size, rng, hc["phases"], t_run0 + cap0,
                                       hc["max_tries_per_member"], sat=sat)
        if hstats.status != "ok":
            sat.close()
            return _hard_abort(wcnf, hstats, time.time() - t_run0, impl0, v3s)
        pop.members = [Individual(assign01=bytearray(a) if compact else a) for a in assigns]
    else:
        pop.init_seeds(wcnf, cfg)

    # initial evaluation
    for ind in pop.members:
        pop.evaluate(wcnf, ind)
    if hard_mode:
        hstats.init_infeasible = sum(1 for ind in pop.members if ind.hard_violations)
        _tot = _soft_weight_float(wcnf)
        hstats.init_best_cost = _tot - max(ind.fitness for ind in pop.members)

    #frozen = frozen_hard_unit_vars(wcnf)#not needed
    best = pop.best().copy()

    # stop conditions
    time_cap = float(cfg.get("time_limit_s", cfg.get("ls", {}).get("time_limit_s", 10.0)))
    start_t = t_run0 if hard_mode else time.time()
    max_gens = int(cfg.get("ea", {}).get("max_gens", 100))

    # --- target-cost stop -----------------------------------------------------
    # THE UNIT TRAP (docs/archive/TIER2_MEMETIC_PLAN.md §6.3 trap 1): the EA tracks
    # *satisfied* soft weight (`Individual.fitness` == soft weight when there are
    # no hard violations), while `target_cost` is *unsatisfied* soft weight. They
    # are never compared directly; the conversion happens at the comparison site:
    #
    #     incumbent_cost = total_soft_weight - best_soft_weight
    #
    # This is written in the general weighted form on purpose. On the 26 SATLIB
    # tier-2 instances every weight is 1 and there are no hard clauses, so it
    # reduces to an unsatisfied-clause count -- but a `weight == 1` assumption
    # would silently corrupt weighted instances once §3's WCNF fix lands.
    # Computed once here, not per generation.
    total_soft_weight = _soft_weight_float(wcnf)
    stop_reason = None
    time_to_target_s = None
    target_hit = None

    def _at_target(ind) -> bool:
        """Incumbent has reached (or beaten) target_cost.

        `<=`, not `==`: a cost strictly below the oracle means the two solvers
        disagree about what the instance is (§6.3), and we want the run to halt
        and be visible in the shard rather than grind on for the full budget.
        Individuals with hard violations carry a penalty fitness, not a soft
        weight, so they are excluded rather than converted.
        """
        if target_cost is None or ind.hard_violations != 0:
            return False
        return (total_soft_weight - ind.fitness) <= target_cost

    if _at_target(best):
        # The JW-seeded population already reached it; do not run a generation.
        stop_reason = "target"
        time_to_target_s = time.time() - start_t
        target_hit = {"calls_to_target": 0, "flips_to_target": 0, "target_by": "init",
                      "resolution": "flip", "time_to_hit_s": time_to_target_s}

    ls_small = _ls_budget(cfg)
    # `impl` (src/evo/impl_v2.py): v1 = the historical code paths (default; an
    # absent key is v1), v2 = same algorithm and random decisions with faster
    # bookkeeping (incremental polish, cached crossover statics, no no-op
    # advisor round trip).
    impl = memetic_impl(cfg)
    polish = select_polish(cfg)
    crossover = select_crossover(cfg)
    # --- opt-in deadline clipping (`ea.deadline_mode: clip`) -----------------
    # Without it the run budget is tested only at the top of each generation, so
    # a run overshoots `time_cap` by up to one whole generation of polish calls
    # (38 x ls.time_limit_s for pop 40) and, with long calls, can outlive the
    # runner's budget+grace watchdog. With it, each child's polish gets
    # min(ls.time_limit_s, remaining budget), and the run ends with
    # stop_reason "time_cap" as soon as no budget remains before a polish.
    # Absent (every pre-M2 config), the code path and the rng stream are
    # exactly the historical ones.
    deadline_clip = str((cfg.get("ea") or {}).get("deadline_mode", "")).lower() == "clip"
    gen = 0
    total_children = 0
    if compact and vc is not None and vc["mutation"] != "rate":
        # The hard-clause guard is C (sat/compact.HardGuard): no Python clause lists.
        hard_clauses = hard_occurs = None
        has_hard = wcnf.counts()["n_hard"] > 0
    else:
        # 1) derive hard_clauses once
        hard_clauses = [cl for cl in wcnf.clauses if cl.is_hard]
        # 2) precompute occurrences
        hard_occurs = build_hard_occurs(hard_clauses, wcnf.n_vars)
        has_hard = bool(hard_clauses)
    # v3 components (each None/False when its key is absent: the v2 / hard path)
    px_on = vc is not None and vc["crossover"] == "px"
    mut_v3 = vc is not None and vc["mutation"] != "rate"
    polish_v3 = PolishV3(vc, wcnf, v3s) if (vc is not None and custom_polish(vc)) else None
    if vc is not None and polish_v3 is None:
        v3s.d["polish_core"] = "v2" + ("+hard" if hard_mode else "")
    diag_every = vc["diag_every"] if vc is not None else 0
    flips_t =0
    # Target hit (MSE26_RHO_PLAN.md §7): the v3 polish cores report the step of
    # the call at which the true cost first reached the target; only observed.
    hit_target = (int(target_cost) if target_cost is not None and float(target_cost).is_integer()
                  and target_cost >= 0 else None)
    calls = 0
    while stop_reason is None and (time.time() - start_t) < time_cap and gen < max_gens:
        gen += 1
        # Elites
        if elitism:
            elites_cnt = max(1, math.ceil(0.05 * pop_size))
            elites = sorted(pop.members, key=lambda x: x.fitness, reverse=True)[:elites_cnt]
        else:
            elites = []

        new_members: List[Individual] = elites.copy()
        
        # Fill the rest
        while len(new_members) < pop_size:
            p1 = tournament(pop.members, k, rng)
            p2 = tournament(pop.members, k, rng)
            if px_on:
                # B4: partition crossover; below px_min_q components the fallback.
                child_bits, q, eq_parent = partition_crossover(p1, p2, wcnf)
                d3 = v3s.d
                d3["px_calls"] += 1
                d3["px_q_sum"] += q
                d3["px_q_max"] = max(d3["px_q_max"], q)
                hk = q if q <= 20 else 21
                d3["px_q_hist"][hk] = d3["px_q_hist"].get(hk, 0) + 1
                if q < vc["px_min_q"]:
                    d3["px_fallbacks"] += 1
                    if vc["px_fallback"] == "clause_aware":
                        child_bits = crossover(p1, p2, wcnf, rng)
                    else:
                        child_bits = (bytearray if compact else list)((p2 if p2.fitness > p1.fitness else p1).assign01)
                elif eq_parent:
                    d3["px_child_equals_parent"] += 1
            else:
                child_bits = crossover(p1, p2, wcnf, rng)
            diag = diag_every > 0 and total_children % diag_every == 0
            if diag:
                soft_before = evaluate_assignment(wcnf, child_bits)[0]
            #mutate(child_bits, pmutate, rng, frozen=frozen)
            if hard_mode:
                # The guard must see the CHILD's hard clauses (v1/v2 pass the
                # last initial member's vector; kept unchanged there).
                if hard_clauses is None:
                    g = wcnf.guard(child_bits)
                    child_hsat, guard_arg = g.hsat, g
                else:
                    child_hsat = init_hard_satisfied(hard_clauses, child_bits)
                    guard_arg = (hard_clauses, hard_occurs, child_hsat)
                if mut_v3:
                    mutate_v3(child_bits, vc, wcnf, rng, p1, p2, guard_arg, v3s)
                else:
                    mutate1(child_bits, pmutate, rng, hard_clauses, hard_occurs, child_hsat)
                if diag:
                    v3s.d["mutation_damage_sum"] += soft_before - evaluate_assignment(wcnf, child_bits)[0]
                    v3s.d["mutation_damage_n"] += 1
                if not all(child_hsat):
                    hstats.children_infeasible_before_polish += 1
                    if hc["repair"]:
                        # H3 repair R: Glucose with the child as phases. A
                        # feasible child is left as it is (no call needed).
                        fixed = repair(child_bits, sat, start_t + time_cap, hstats)
                        if fixed is not None:
                            child_bits = fixed
            elif mut_v3:
                if hard_clauses is None:
                    guard = wcnf.guard(child_bits) if has_hard else None
                else:
                    guard = ((hard_clauses, hard_occurs, init_hard_satisfied(hard_clauses, child_bits))
                             if hard_clauses else None)
                mutate_v3(child_bits, vc, wcnf, rng, p1, p2, guard, v3s)
            else:
                mutate1(child_bits, pmutate, rng, hard_clauses, hard_occurs, ind.hard_satisfied)
            if diag and not hard_mode:
                v3s.d["mutation_damage_sum"] += soft_before - evaluate_assignment(wcnf, child_bits)[0]
                v3s.d["mutation_damage_n"] += 1
            if impl in ("v2", "hard", "v3"):
                # v2 skips the block below (a pre-polish evaluation of the child
                # and a NoopProvider advisor call whose advice is empty) but keeps
                # its one RNG draw, the advisor's rng_seed, so the stream is v1's.
                rng.randrange(1 << 30)
            else:
                # get violated hard clause indices for the *child* (cheap way: evaluate once)
                ''''''''
                tmp_child = Individual(assign01=child_bits)
                pop.evaluate(wcnf, tmp_child)

                violated_idxs = []
                # if you stored one bool per hard clause in order, collect violated:
                # violated_idxs = [i for i, sat in enumerate(tmp_child.hard_satisfied) if not sat]
                # If you don't have hard_satisfied yet, skip LLM or compute violated list separately.

                advice = advisor.propose(
                    wcnf=wcnf,
                    child_assign01=child_bits,
                    violated_hard_clause_idxs=violated_idxs,
                    rng_seed=rng.randrange(1 << 30),
                    extra={"gen": gen, "child_hv": tmp_child.hard_violations},
                )
                child_bits = apply_advice(child_bits, advice)
                ''''''''
            if deadline_clip:
                remaining = time_cap - (time.time() - start_t)
                if remaining <= 0:
                    # Budget spent mid-generation: drop the unpolished child.
                    stop_reason = "time_cap"
                    break
                ls_call = dict(ls_small, time_limit_s=min(ls_small["time_limit_s"], remaining))
            else:
                ls_call = ls_small
            calls += 1
            flips_before = flips_t
            if compact and not isinstance(child_bits, bytearray):   # repair: a Glucose list
                child_bits = bytearray(child_bits)
            if hard_mode:
                # H3: feasible moves M inside the call's time slot, then the
                # hard-safe flip polish on what remains of it.
                slot_end = min(time.time() + float(ls_call["time_limit_s"]), start_t + time_cap)
                if hc["moves_per_polish"] > 0 and not evaluate_assignment(wcnf, child_bits)[1]:
                    child_bits = feasible_moves(child_bits, soft_view, sat, rng,
                                                hc["moves_per_polish"], hc["move_noise"],
                                                slot_end, hstats, hc["move_conf_budget"],
                                                hc["move_max_budget_misses"], hc["move_keep_sat"])
                ls_rest = dict(ls_call, time_limit_s=max(0.0, slot_end - time.time()))
                if polish_v3 is not None:
                    child_bits, flips_t1, noops = polish_v3(child_bits, ls_rest,
                                                            rng.randrange(1 << 30), True, hit_target)
                else:
                    child_bits, flips_t1, noops = short_polish_hard(child_bits, wcnf, ls_rest,
                                                                    rng_seed=rng.randrange(1 << 30))
                hstats.polish_calls += 1
                hstats.polish_steps += flips_t1
                hstats.polish_noop_steps += noops
            elif polish_v3 is not None:
                child_bits, flips_t1, _noops = polish_v3(child_bits, ls_call, rng.randrange(1 << 30), False,
                                                         hit_target)
            else:
                child_bits, flips_t1 = polish(child_bits, wcnf, ls_call, rng_seed=rng.randrange(1<<30))
            flips_t += flips_t1
            if compact and not isinstance(child_bits, bytearray):   # feasible moves / hard polish lists
                child_bits = bytearray(child_bits)
            child = Individual(assign01=child_bits, meta={"gen": gen})
            pop.evaluate(wcnf, child)
            new_members.append(child)
            total_children += 1
            if hard_mode:
                hstats.children += 1
                if child.hard_violations:
                    hstats.children_infeasible_after_polish += 1
                    hstats.hv_max_child_after_polish = max(hstats.hv_max_child_after_polish,
                                                           child.hard_violations)

            # Incumbent tracking moved inside the fill loop so the target check
            # can fire after each child's polish rather than only at
            # end-of-generation (§7 measured ~57 children/generation at 8 s with
            # memetic_base; at a 900 s budget a generation is a long time to keep
            # running after the answer is in hand).
            #
            # With target_cost=None this is exactly equivalent to the
            # end-of-generation update kept below: `best` is the running maximum
            # over everything evaluated so far, so the elites carried into
            # new_members can never beat it, and the strict `>` keeps the same
            # tie-break (first individual to attain the maximum wins).
            if child.fitness > best.fitness:
                best = child.copy()
                if hard_mode and best.hard_violations:
                    hstats.incumbent_infeasible_events += 1
                if _at_target(best):
                    stop_reason = "target"
                    time_to_target_s = time.time() - start_t
                    step, wall = polish_v3.last_hit if polish_v3 is not None else (None, None)
                    if step is not None and step >= 0:
                        target_hit = {"calls_to_target": calls, "flips_to_target": flips_before + step,
                                      "target_by": "polish" if step > 0 else "pre_polish",
                                      "resolution": "flip", "time_to_hit_s": wall - start_t}
                    else:
                        target_hit = {"calls_to_target": calls, "flips_to_target": flips_t,
                                      "target_by": "child" if step is None else "unknown",
                                      "resolution": "call", "time_to_hit_s": None}
                    break

        if stop_reason is not None:  # "target", or "time_cap" from deadline clipping
            break

        pop.members = new_members
        # track best
        cur_best = pop.best()
        if cur_best.fitness > best.fitness:
            best = cur_best.copy()



    if stop_reason is None:
        # The loop can only have exited on one of its two historical conditions.
        stop_reason = "time_cap" if (time.time() - start_t) >= time_cap else "max_gens"

    def _assignment_exports(assign01: list[bool]) -> dict:
        # index 0 is unused in your code; export 1..n
        if isinstance(assign01, (bytes, bytearray)):   # compact: same string, no Python loop
            bits = bytes(assign01[1:]).translate(_BITS).decode("ascii")
        else:
            bits = "".join("1" if b else "0" for b in assign01[1:])
        dimacs = "v " + " ".join(str(i if assign01[i] else -i) for i in range(1, len(assign01))) + " 0"
        true_vars = [i for i in range(1, len(assign01)) if assign01[i]]
        return {"assign_bits": bits, "dimacs": dimacs, "true_vars": true_vars}
        #results = {"assign_bits": bits, "dimacs": dimacs, "true_vars": true_vars}
    def clause_satisfied_bits(clause, bits: List[bool]) -> bool:
        """
        clause.lits: list of ints (e.g. [1, -3, 4])
        bits[v]: True/False, 1-based (bits[0] unused)
        """
        for lit in clause.lits:
            v = abs(lit)
            val = bits[v]
            if (lit > 0 and val) or (lit < 0 and not val):
                return True
        return False

    def count_satisfied_clauses_bits(wcnf, bits: List[bool]) -> int:
        return sum(1 for cl in wcnf.clauses if clause_satisfied_bits(cl, bits))

    results = _assignment_exports(best.assign01)
    # Using your results dict:
    def bits_to_assign01(bits: str) -> List[bool]:
        assert all(c in "01" for c in bits)
        # index 0 unused; bits[0] -> var 1, bits[1] -> var 2, ...
        return [False] + [c == "1" for c in bits]

    assign01 = best.assign01 if compact else bits_to_assign01(results["assign_bits"])
    #bits = f'0{results["assign_bits"]}'
    #wcnf = results["dimacs"]

    total_clauses = len(wcnf.clauses)
    sat_clauses = (wcnf.evaluate(best.assign01)[4] if compact   # == assign01 (same bits)
                   else count_satisfied_clauses_bits(wcnf, assign01))
    unsat_clauses = total_clauses - sat_clauses
    elapsed = max(1e-9, time.time() - start_t)
    exports = results if compact else _assignment_exports(best.assign01)   # same values
    soft, hv = evaluate_assignment(wcnf, best.assign01)
    if hard_mode:
        hstats.hard_feasible_final = hv == 0
        sat.close()
    #print(flips_t)
    return {
        "best_soft_weight": float(soft),
        "hard_violations": int(hv),
        "elapsed_sec": float(elapsed),
        "total_flips": int(flips_t),          # we didn't call LS yet; wire later if you add polish with flips
        "flips_per_sec": 0.0,
        "restarts": 0,
        "final_noise": 0.0,
        "stop_reason": stop_reason,
        "time_to_target_s": (None if time_to_target_s is None else float(time_to_target_s)),
        "target_hit": target_hit,
        "impl": impl,
        "hard": hstats.as_dict() if hard_mode else None,
        "v3": _v3_dict(v3s, wcnf),
        "meta": {"ea_generations": gen, "children": total_children, **exports,},
        "satisfied_clauses": {
            "total": total_clauses,
            "satisfied": sat_clauses,
            "unsatisfied": unsat_clauses,
        },
    }
