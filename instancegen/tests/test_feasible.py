"""Step 2 test: docs/INSTANCEGEN_PLAN.md §12 test 9 (D8 feasibility guard).

Fails before instancegen/feasible.py exists; passes after. This is the only test
in steps 1-2 that needs pysat installed.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from instancegen.feasible import (
    HardPartInfeasible,
    attempt_seed,
    generate_feasible,
    generate_feasible_verbose,
    hard_part_is_sat,
    witness_satisfies_hard,
)
from instancegen.generate import GenParams, generate
from instancegen.wcnf_io import format_wcnf

BASE = GenParams(
    n_vars=60,
    k=3,
    soft_ratio=4.0,
    hard_ratio=1.0,
    w_max=16,
    seed=3,
)


# --- §12 test 9 --------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_hard_part_feasible(seed: int) -> None:
    p = replace(BASE, seed=seed)
    inst, witness = generate_feasible(p)

    assert len(inst.hard_clauses) == p.n_hard > 0
    # Direct evaluation, not a second solver call: the witness must satisfy
    # every hard clause of the instance actually returned.
    assert witness_satisfies_hard(inst, witness)
    # The witness is a total assignment over 1..n_vars.
    assert tuple(sorted(abs(l) for l in witness)) == tuple(range(1, p.n_vars + 1))
    # Independent SAT call on the hard part alone also reports SAT.
    assert hard_part_is_sat(inst) is not None
    # The soft part is deliberately unconstrained -- no claim is made about it.
    assert len(inst.soft_clauses) == p.n_soft


@pytest.mark.parametrize("hard_ratio", [0.5, 1.0, 2.0, 3.0])
def test_hard_part_feasible_across_hard_ratios(hard_ratio: float) -> None:
    inst, witness = generate_feasible(replace(BASE, hard_ratio=hard_ratio))
    assert witness_satisfies_hard(inst, witness)


def test_generate_feasible_is_deterministic() -> None:
    """Instance bytes are reproducible from (params, seed) (§7, D6)."""
    a, wa = generate_feasible(BASE)
    b, wb = generate_feasible(BASE)
    assert a == b
    assert format_wcnf(a, dialect="old") == format_wcnf(b, dialect="old")
    # Same solver, same call -> same witness too; the contract only promises the
    # instance, but a change here would be worth noticing.
    assert wa == wb


def test_no_hard_clauses_needs_no_solver(monkeypatch) -> None:
    """hard_ratio == 0: nothing to check, so no SAT call at all (§12 test 9)."""
    import instancegen.feasible as feasible

    def boom(*args, **kwargs):
        raise AssertionError("solver must not be called when there are no hard clauses")

    monkeypatch.setattr(feasible, "hard_part_is_sat", boom)
    p = replace(BASE, hard_ratio=0.0)
    inst, witness = feasible.generate_feasible(p)
    assert inst.hard_clauses == ()
    assert witness_satisfies_hard(inst, witness)   # vacuously true
    assert len(witness) == p.n_vars


def test_accepted_first_attempt_below_threshold() -> None:
    """hard_ratio well below ~4.27 should accept the first uniform sample (D8)."""
    inst, _, attempts = generate_feasible_verbose(replace(BASE, hard_ratio=0.4))
    assert attempts == 1
    # Attempt 1 uses the params' own seed, so it equals plain generate().
    assert inst == generate(replace(BASE, hard_ratio=0.4))


def test_resample_uses_a_new_sample() -> None:
    """attempt_seed must actually move the stream, and be stable."""
    assert attempt_seed(7, 0) == 7
    assert attempt_seed(7, 1) != 7
    assert attempt_seed(7, 1) == attempt_seed(7, 1)
    assert attempt_seed(7, 1) != attempt_seed(7, 2)
    assert attempt_seed(7, 1) != attempt_seed(8, 1)


def test_infeasible_above_threshold_raises() -> None:
    """Far above the UNSAT threshold, rejection sampling must give up loudly."""
    p = replace(BASE, n_vars=30, hard_ratio=12.0, soft_ratio=1.0)
    with pytest.raises(HardPartInfeasible) as exc:
        generate_feasible(p, max_attempts=3)
    assert exc.value.attempts == 3


def test_witness_check_rejects_a_bad_witness() -> None:
    """The checker must be able to fail, or test_hard_part_feasible proves nothing."""
    inst, witness = generate_feasible(BASE)
    flipped = tuple(-l for l in witness)
    assert witness_satisfies_hard(inst, witness)
    # A 60-var random 3-SAT hard part at ratio 1.0 is not satisfied by both an
    # assignment and its complement; if it were, this test would be vacuous.
    assert not witness_satisfies_hard(inst, flipped)
