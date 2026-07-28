"""Hard-part feasibility guard: generate -> SAT-check hard part -> resample.

Plan: docs/INSTANCEGEN_PLAN.md D8, §7, §8.

The soft part is left unconstrained -- that is what makes the result a real
MaxSAT instance. The hard part is made satisfiable by construction:

    generate hard clauses uniformly
      -> SAT-check the hard part alone
      -> on UNSAT, resample with a derived seed and repeat
      -> on SAT, return the model as the witness

An assignment is deliberately NOT planted (D8): planting conditions every hard
clause on the target model, which biases the clause distribution away from
uniform random k-SAT and makes instances easier at matched parameters. The SAT
call is needed anyway to accept/reject, so its model comes for free.

This is the only module on the generator path that imports pysat; generate.py
stays pure so determinism is testable without a solver (§7).

Determinism: generate_feasible is a deterministic function of GenParams -- the
attempt seeds are a fixed hash of (seed, attempt) and SAT/UNSAT is a property of
the formula, not the solver. Instance bytes are therefore reproducible from
(params, seed). The witness is not: any model satisfies the contract, and which
one is returned depends on the solver, so the manifest records it explicitly.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Tuple

from instancegen.generate import GenParams, Instance, generate

# Default SAT backend for the guard. Only used for a satisfiability verdict on
# the hard part; any complete solver gives the same verdict.
DEFAULT_SOLVER = "cadical153"

# Attempt cap for the rejection loop. Hitting it means hard_ratio is at or above
# the k-SAT UNSAT threshold (~4.27 for k=3) where rejection sampling degenerates
# (D8), so it raises rather than spins.
DEFAULT_MAX_ATTEMPTS = 64

Witness = Tuple[int, ...]


class HardPartInfeasible(RuntimeError):
    """Raised when the rejection loop exhausts its attempt budget.

    Signals "hard_ratio is too close to the UNSAT threshold for rejection
    sampling", which is the one regime where D8 says planting would be
    reconsidered -- not a transient error to retry.
    """

    def __init__(self, params: GenParams, attempts: int) -> None:
        super().__init__(
            f"hard part UNSAT on all {attempts} attempts for "
            f"n_vars={params.n_vars}, k={params.k}, hard_ratio={params.hard_ratio} "
            f"(seed={params.seed}); hard_ratio is likely at/above the k-SAT "
            f"UNSAT threshold, where rejection sampling is impractical (D8)"
        )
        self.params = params
        self.attempts = attempts


def attempt_seed(seed: int, attempt: int) -> int:
    """Seed for resample attempt `attempt` (0-based). attempt 0 is `seed` itself.

    A fixed SHA-256 derivation rather than seed+attempt or a PRNG-of-seeds: it
    is stable across Python versions and cannot collide with a neighbouring
    grid point's seed in a way that silently duplicates instances.
    """
    if attempt == 0:
        return seed
    digest = hashlib.sha256(f"instancegen:{seed}:{attempt}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def trivial_witness(n_vars: int) -> Witness:
    """All-false model over 1..n_vars, used when there are no hard clauses."""
    return tuple(-v for v in range(1, n_vars + 1))


def witness_satisfies_hard(inst: Instance, witness: Witness) -> bool:
    """True iff every hard clause of `inst` is satisfied by `witness`.

    Direct evaluation, no solver -- this is what test 9 checks against, so it
    must not depend on the thing it is checking.
    """
    true_lits = set(witness)
    for cl in inst.hard_clauses:
        if not any(lit in true_lits for lit in cl.lits):
            return False
    return True


def _full_model(model, n_vars: int) -> Witness:
    """Normalise a pysat model to a total assignment over 1..n_vars.

    Variables absent from every hard clause may be missing from the model (or
    the solver may report them either way); missing ones are set false.
    """
    assigned = {abs(lit): lit for lit in model}
    return tuple(assigned.get(v, -v) for v in range(1, n_vars + 1))


def hard_part_is_sat(inst: Instance, *, solver: str = DEFAULT_SOLVER):
    """SAT-check the hard clauses alone. Returns a witness, or None if UNSAT."""
    from pysat.solvers import Solver  # local import: keeps import-time pysat-free

    hard = [list(cl.lits) for cl in inst.hard_clauses]
    if not hard:
        return trivial_witness(inst.n_vars)
    with Solver(name=solver, bootstrap_with=hard) as s:
        if not s.solve():
            return None
        return _full_model(s.get_model(), inst.n_vars)


def generate_feasible(
    params: GenParams,
    *,
    solver: str = DEFAULT_SOLVER,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> Tuple[Instance, Witness]:
    """Generate an instance whose HARD part is satisfiable, plus its witness.

    Raises HardPartInfeasible if `max_attempts` uniform samples are all UNSAT.
    `generate_feasible_verbose` returns the same pair plus the attempt count for
    the manifest's `hard_resample_attempts` field (§10.3).
    """
    inst, witness, _ = generate_feasible_verbose(
        params, solver=solver, max_attempts=max_attempts
    )
    return inst, witness


def generate_feasible_verbose(
    params: GenParams,
    *,
    solver: str = DEFAULT_SOLVER,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
) -> Tuple[Instance, Witness, int]:
    """As generate_feasible, but also returns attempts used (1 = accepted first)."""
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be >= 1, got {max_attempts}")

    for attempt in range(max_attempts):
        inst = generate(replace(params, seed=attempt_seed(params.seed, attempt)))
        if params.n_hard == 0:
            # No hard clauses: nothing to check, no solver call (§12 test 9).
            return inst, trivial_witness(inst.n_vars), attempt + 1
        witness = hard_part_is_sat(inst, solver=solver)
        if witness is not None:
            return inst, witness, attempt + 1

    raise HardPartInfeasible(params, max_attempts)
