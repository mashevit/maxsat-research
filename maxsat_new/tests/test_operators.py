"""Step 3 test (PORT_NOTES §10 row 3): EA operators are seed-deterministic.

Fails before maxsat_new/operators.py (and population.py) exist (ImportError);
passes after.

One seeded `Population` init on mini.wcnf, then one
`tournament -> clause_aware_crossover1 -> mutate1` sequence. The whole sequence is
run twice, each time from a freshly seeded `random.Random(SEED)`; the resulting
child assignments must be bit-identical (determinism comes from the seed alone).

Non-triviality: on mini.wcnf with these params the child differs from both parents,
so a pipeline that silently returned a parent (or a no-op mutation) would fail.

No `short_polish` here: §10 row 3's sequence is tournament -> crossover1 -> mutate1,
so there is no budget in this test to bind; the only determinism source is SEED.
"""
from __future__ import annotations

import os
import random

from maxsat_new.cnf import WCNF
from maxsat_new.population import Population, build_hard_occurs
from maxsat_new.operators import tournament, clause_aware_crossover1, mutate1

MINI = os.path.join(os.path.dirname(__file__), "data", "mini.wcnf")

SEED = 0
POP_SIZE = 6
TOURNAMENT_K = 2
PMUTATE = 0.1


def _run_sequence(seed: int):
    """Replicate the live per-child EA pipeline (minus polish) for one child.

    Note: `ind` is the leaked init-eval loop variable, and its
    `ind.hard_satisfied` is handed to mutate1 exactly as memetic (step 7) does
    (PORT_NOTES §9.1 — stale/shared list, replicated not fixed).
    """
    wcnf = WCNF.parse_dimacs(MINI)
    rng = random.Random(seed)

    pop = Population(wcnf.n_vars, POP_SIZE, rng)
    pop.init_seeds(wcnf, {})

    ind = None
    for ind in pop.members:
        pop.evaluate(wcnf, ind)

    hard_clauses = [cl for cl in wcnf.clauses if cl.is_hard]
    hard_occurs = build_hard_occurs(hard_clauses, wcnf.n_vars)

    p1 = tournament(pop.members, TOURNAMENT_K, rng)
    p2 = tournament(pop.members, TOURNAMENT_K, rng)

    child = clause_aware_crossover1(p1, p2, wcnf, rng)
    mutate1(child, PMUTATE, rng, hard_clauses, hard_occurs, ind.hard_satisfied)

    return child, list(p1.assign01), list(p2.assign01)


def test_operators_seed_deterministic_and_nontrivial() -> None:
    child_a, p1, p2 = _run_sequence(SEED)
    child_b, _, _ = _run_sequence(SEED)

    # Determinism: two freshly seeded runs must produce the identical child.
    assert child_a == child_b

    # Non-triviality: the child is not a byte-copy of either parent.
    assert child_a != p1
    assert child_a != p2
