"""Step 7 test: the run_memetic core (PORT_NOTES §10 row 7).

Fails before maxsat_new/memetic.py exists; passes after.

Row 7 asks for two things: a small `max_gens` run returns a valid result, and the
same seed twice under a `max_gens` bound gives an identical `best_cost` and
assignment hash. Both are here (`test_small_run_returns_valid_result`,
`test_same_seed_twice_is_bit_reproducible`).

Reproducibility needs BOTH budgets iteration-bound, not just the EA-level one
PORT_NOTES §11 Q1 mentions: `walksat_polish` has its own wall clock
(`time_up()`, walksat.py:118), so a per-polish `time_limit_s` truncates a polish
on a slow or loaded machine. Hence `budget.time_limit_s` AND
`polish.time_limit_s` are both 1000.0 (never bind) while `budget.max_gens` and
`ea.polish_flips` always do.

`test_ea_rng_ledger_is_exact` is the real divergence guard at this step, and the
reason it exists is measured, not assumed: on mini.wcnf every stream reaches the
same optimum (`best_soft_weight=14`, bits `10111`), so the reproducibility test
above stays green even if the port loses the `src:108` advisor-seat draw. The
ledger asserts the draw sequence AND the drawn values, in order.

Fixture: mini.wcnf, because it HAS hard clauses (`top=100`, three `100 ...`
lines). That is what makes this step exercisable -- `hard_clauses`/`hard_occurs`
are non-empty, so `mutate1`'s guard actually runs against the §9.1 stale list, and
`violated_hard` can be non-empty, so `build_state`'s load-bearing field is not
vacuous. A `.cnf` would load all-soft (§9.6) and both would go untested.
"""
from __future__ import annotations

import dataclasses
import math
import os
import random
from typing import Any, Dict, List, Tuple

import pytest

from maxsat_new.cnf import WCNF
from maxsat_new.hardviol import violated_hard_clauses
from maxsat_new.memetic import build_state, run_memetic
from maxsat_new.population import evaluate_assignment
from maxsat_new.providers import Advice, NoopProvider, State

DATA = os.path.join(os.path.dirname(__file__), "data")
MINI = os.path.join(DATA, "mini.wcnf")
HARDMIX = os.path.join(DATA, "hardmix.wcnf")

SEED = 1
POP_SIZE = 6
MAX_GENS = 3
ELITE_FRAC = 0.05
TOURNAMENT_K = 4

# max(1, ceil(0.05 * 6)) == 1 elite, so 5 children per generation.
ELITES_CNT = max(1, math.ceil(ELITE_FRAC * POP_SIZE))
CHILDREN = MAX_GENS * (POP_SIZE - ELITES_CNT)


def _params() -> Dict[str, Dict[str, Any]]:
    """The iteration-bounded budget (§11 Q1, extended to the per-polish cap).

    Both `time_limit_s` values are huge on purpose: `budget.time_limit_s` is the
    EA loop cap (src:76) and `polish.time_limit_s` drives walksat_polish's
    `time_up()` (walksat.py:118). Leaving either realistic makes the run
    machine-speed-dependent and the reproducibility assertions flaky.
    """
    return {
        "ea": {
            "pop_size": POP_SIZE,
            "polish_flips": 50,      # binds; the real polish budget
            "tournament_k": TOURNAMENT_K,
            "pmutate": 0.02,
            "elitism": True,
            "elite_frac": ELITE_FRAC,
        },
        "budget": {"max_gens": MAX_GENS, "time_limit_s": 1000.0},
        "polish": {"time_limit_s": 1000.0, "noise": 0.10, "hard_safe": True},
    }


# --- row 7, first clause ------------------------------------------------------


def test_small_run_returns_valid_result() -> None:
    """A small max_gens run returns a well-formed, self-consistent result."""
    wcnf = WCNF.parse_dimacs(MINI)
    res = run_memetic(wcnf, _params(), SEED, NoopProvider())

    assert set(res) == {
        "best_soft_weight",
        "hard_violations",
        "best_assignment",
        "best_assignment_hash",
        "generations",
        "children",
        "total_flips",
        "wall_time_s",
    }

    # max_gens bound the loop, not the wall clock.
    assert res["generations"] == MAX_GENS
    assert res["children"] == CHILDREN

    assert isinstance(res["best_soft_weight"], int)
    assert isinstance(res["hard_violations"], int)
    assert res["hard_violations"] >= 0
    assert isinstance(res["total_flips"], int)
    assert res["total_flips"] >= 0
    assert isinstance(res["best_assignment_hash"], str)

    assign = res["best_assignment"]
    assert len(assign) == wcnf.n_vars + 1
    assert assign[0] is False  # index 0 unused

    # The reported numbers describe the returned assignment -- catches reporting a
    # different individual than the one handed back.
    soft, hv = evaluate_assignment(wcnf, assign)
    assert int(soft) == res["best_soft_weight"]
    assert hv == res["hard_violations"]


# --- row 7, second clause -----------------------------------------------------


def test_same_seed_twice_is_bit_reproducible() -> None:
    """Same seed, max_gens bound -> identical cost AND assignment hash."""
    wcnf = WCNF.parse_dimacs(MINI)
    a = run_memetic(wcnf, _params(), SEED, NoopProvider())
    b = run_memetic(wcnf, _params(), SEED, NoopProvider())

    assert a["best_soft_weight"] == b["best_soft_weight"]
    assert a["best_assignment_hash"] == b["best_assignment_hash"]
    assert a["best_assignment"] == b["best_assignment"]
    assert a["total_flips"] == b["total_flips"]
    assert a["generations"] == b["generations"]
    assert a["children"] == b["children"]
    # `wall_time_s` is a clock and is deliberately not compared.


# --- the §6 invariant, as an exact stream ledger ------------------------------


_INSTANCES: List["_TracingRandom"] = []


class _TracingRandom(random.Random):
    """Records the EA's draw sequence, in order, with the drawn values.

    `getrandbits` is overridden (delegating, untraced) for a load-bearing reason:
    `Random.__init_subclass__` walks the MRO and, if it finds `random` in a
    subclass `__dict__` before `getrandbits`, rebinds `_randbelow` to
    `_randbelow_without_getrandbits`, which draws via `self.random()`. That would
    change how `sample`/`randrange` consume the stream and pollute the trace.
    Defining `getrandbits` here makes `__init_subclass__` pick
    `_randbelow_with_getrandbits`, i.e. exactly the base behavior.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.trace: List[Tuple[str, Any]] = []
        _INSTANCES.append(self)

    def getrandbits(self, k: int) -> int:  # untraced on purpose (see docstring)
        return super().getrandbits(k)

    def random(self) -> float:
        v = super().random()
        self.trace.append(("random", v))
        return v

    def randrange(self, *args: Any, **kwargs: Any) -> int:
        v = super().randrange(*args, **kwargs)
        self.trace.append(("randrange", v))
        return v

    def sample(self, population: Any, k: int, **kwargs: Any) -> Any:
        v = super().sample(population, k, **kwargs)
        # The returned Individuals are not comparable across runs; what pins the
        # stream is the consumption, which depends only on (len(population), k),
        # plus the values of every later draw.
        self.trace.append(("sample", (len(population), k)))
        return v

    def choice(self, seq: Any) -> Any:
        v = super().choice(seq)
        self.trace.append(("choice", v))
        return v


def _expected_trace(n_vars: int) -> List[Tuple[str, Any]]:
    """Replay the expected stream from a plain Random, independently.

    The expectation is the src pipeline read off `src/evo/memetic.py`:

      setup   : pop_size * n_vars  rng.random()          (init_seeds, population.py:145)
      per child: rng.sample x2                           (tournament, src:89-90)
                 rng.random() x n_vars                   (mutate1, src:93)
                 rng.randrange(1<<30)                    (advisor seat, src:108)
                 rng.randrange(1<<30)                    (polish, src:113)

    `rng.sample(range(POP_SIZE), k)` consumes identically to sampling from a
    POP_SIZE-element list of Individuals, so replaying against `range` reproduces
    the exact value stream of every subsequent draw.

    `clause_aware_crossover1`'s `rng.choice` (operators.py:222) is absent because
    its guard is unreachable: `chosen` is a parent bit, and `a != b` means
    `{a, b} == {True, False}`, so `chosen not in (a, b)` is never true. A `choice`
    entry appearing in the actual trace fails this test, which is the intent.
    """
    r = random.Random(SEED)
    exp: List[Tuple[str, Any]] = [
        ("random", r.random()) for _ in range(POP_SIZE * n_vars)
    ]
    for _ in range(CHILDREN):
        r.sample(range(POP_SIZE), TOURNAMENT_K)
        exp.append(("sample", (POP_SIZE, TOURNAMENT_K)))
        r.sample(range(POP_SIZE), TOURNAMENT_K)
        exp.append(("sample", (POP_SIZE, TOURNAMENT_K)))
        exp += [("random", r.random()) for _ in range(n_vars)]
        exp.append(("randrange", r.randrange(1 << 30)))
        exp.append(("randrange", r.randrange(1 << 30)))
    return exp


def test_ea_rng_ledger_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    """The EA draw sequence and every drawn value, in order.

    This is the §6 invariant made testable and the only real divergence guard at
    this step (test_same_seed_twice_is_bit_reproducible is vacuous on mini.wcnf:
    every stream reaches best_soft_weight=14 there).

    Two `randrange` per child is the load-bearing count: one is the `src:108`
    advisor-seat draw the port must keep, one is the polish seed. One per child
    would mean the hook lost the src draw (step-8 divergence); three would mean
    `build_state` -> `propose` -> `apply_advice` added a draw of its own, which
    §6 forbids.
    """
    wcnf = WCNF.parse_dimacs(MINI)

    monkeypatch.setattr(random, "Random", _TracingRandom)
    _INSTANCES.clear()
    run_memetic(wcnf, _params(), SEED, NoopProvider())

    # The EA rng is the first Random built inside run_memetic (src:51); each
    # short_polish builds its own (walksat.py:100), which is why the trace is
    # attributed per instance and not globally.
    assert len(_INSTANCES) == 1 + CHILDREN
    ea_trace = _INSTANCES[0].trace

    expected = _expected_trace(wcnf.n_vars)

    # Sequence of draw kinds, in order: pins order and multiplicity.
    assert [kind for kind, _ in ea_trace] == [kind for kind, _ in expected]
    # And the values, in order: pins the stream byte-for-byte.
    assert ea_trace == expected

    # Spelled out, for the record.
    kinds = [kind for kind, _ in ea_trace]
    assert kinds.count("random") == (POP_SIZE + CHILDREN) * wcnf.n_vars
    assert kinds.count("sample") == 2 * CHILDREN
    assert kinds.count("randrange") == 2 * CHILDREN
    assert kinds.count("choice") == 0


# --- build_state --------------------------------------------------------------


def test_build_state_fields() -> None:
    """Every State field, on both fixtures.

    hardmix.wcnf carries the global-vs-hard-sublist index distinction through to
    build_state: its hard clauses are at global 1, 3, 4.
    """
    for path in (MINI, HARDMIX):
        wcnf = WCNF.parse_dimacs(path)
        child = [False] + [(v % 2 == 1) for v in range(1, wcnf.n_vars + 1)]

        state = build_state(wcnf, child, gen=7, seed=99)

        assert isinstance(state, State)
        assert isinstance(state.assign, tuple)
        assert state.assign is not child
        assert list(state.assign) == child

        assert isinstance(state.violated_hard, tuple)
        assert state.violated_hard == tuple(violated_hard_clauses(wcnf, child))

        soft, hard_v = evaluate_assignment(wcnf, child)
        assert state.n_hard_violations == len(state.violated_hard) == hard_v
        assert state.n_vars == len(state.assign) - 1 == wcnf.n_vars
        assert state.generation == 7
        assert state.seed == 99

        # STEP 7 SIGN CONVENTION: cost is SATISFIED soft weight. PORT_NOTES §5
        # documents the field as unsat weight and §10 row 8 owns the inversion;
        # this assertion is the pin that makes step 8's change a visible, failing
        # assertion instead of a silent redefinition.
        assert isinstance(state.cost, int)
        assert state.cost == int(soft)


def test_build_state_sees_real_violated_hard_not_srcs_empty_list() -> None:
    """The one deviation from src's data flow, pinned.

    src fed the advisor `violated_idxs = []` unconditionally with the real
    computation commented out (src:99-101). build_state supplies the real thing;
    on hardmix.wcnf with this assignment it is non-empty, so the deviation is
    observable rather than a claim.
    """
    wcnf = WCNF.parse_dimacs(HARDMIX)
    #   x1=T, x2=F, x3=F, x4=T -> hard idx1 [-1,3] and idx4 [-4] violated
    child = [False, True, False, False, True]

    state = build_state(wcnf, child, gen=1, seed=SEED)

    assert state.violated_hard == ((1, (-1, 3)), (4, (-4,)))
    assert state.n_hard_violations == 2


# --- the provider actually sees the seam, and cannot perturb it ---------------


class _SpyProvider:
    """Records every State it is handed; returns `Advice()`, exactly like Noop."""

    def __init__(self) -> None:
        self.seen: List[State] = []

    def propose(self, state: State) -> Advice:
        self.seen.append(state)
        return Advice()


def test_provider_receives_state_and_cannot_perturb() -> None:
    """§6: once per child, every generation, elites excluded; and observing is free."""
    wcnf = WCNF.parse_dimacs(MINI)

    spy = _SpyProvider()
    spied = run_memetic(wcnf, _params(), SEED, spy)
    noop = run_memetic(wcnf, _params(), SEED, NoopProvider())

    # Once per child = pop_size - elite_count per generation (§6), never elites.
    assert len(spy.seen) == CHILDREN
    assert [s.generation for s in spy.seen] == [
        g for g in range(1, MAX_GENS + 1) for _ in range(POP_SIZE - ELITES_CNT)
    ]

    # The master seed, not RNG state, and never mutable state.
    assert all(s.seed == SEED for s in spy.seen)
    assert all(isinstance(s.assign, tuple) for s in spy.seen)
    assert all(s.n_vars == wcnf.n_vars for s in spy.seen)
    assert all(s.n_hard_violations == len(s.violated_hard) for s in spy.seen)
    with pytest.raises(dataclasses.FrozenInstanceError):
        spy.seen[0].cost = 0  # type: ignore[misc]

    # Reading the snapshot changes nothing about the run.
    assert spied["best_assignment_hash"] == noop["best_assignment_hash"]
    assert spied["best_soft_weight"] == noop["best_soft_weight"]
    assert spied["total_flips"] == noop["total_flips"]
