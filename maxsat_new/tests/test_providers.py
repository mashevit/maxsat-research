"""Step 6 test: apply_advice(x, Advice()) is identity; NoopProvider is a no-op.

Fails before maxsat_new/providers.py exists; passes after.

The identity property is what makes step 10's bit-identity claim
(llm_guided_base + NoopProvider == memetic_ea) possible, so it is asserted in
its strict form: equal by value, a distinct object, and the input untouched.
"""
from __future__ import annotations

import dataclasses

import pytest

from maxsat_new.providers import Advice, NoopProvider, State, apply_advice


def _state(assign: tuple[bool, ...]) -> State:
    return State(
        assign=assign,
        violated_hard=((1, (-1, 3)),),
        cost=7,
        n_hard_violations=1,
        generation=3,
        seed=1234,
        n_vars=len(assign) - 1,
    )


def test_empty_advice_is_identity() -> None:
    """The load-bearing assertion."""
    x = [False, True, False, True]
    original = x[:]

    out = apply_advice(x, Advice())

    assert out == x          # value identity
    assert out is not x      # a NEW list
    assert x == original     # caller's list untouched


def test_noop_provider_composes_to_identity() -> None:
    """NoopProvider -> Advice() -> apply_advice is the full no-op path."""
    x = [False, True, False, True]

    advice = NoopProvider().propose(_state(tuple(x)))

    assert advice == Advice()
    assert advice.flip_vars == () and advice.set_true == () and advice.set_false == ()
    assert apply_advice(x, advice) == x


def test_advice_is_applied() -> None:
    """Guard against an inert port: a non-empty Advice must actually edit."""
    x = [False, False, True, True]

    #   flip 2   : x[2] True  -> False
    #   set_true 1: x[1] False -> True
    #   set_false 3: x[3] True  -> False
    out = apply_advice(x, Advice(flip_vars=(2,), set_true=(1,), set_false=(3,)))

    assert out == [False, True, False, False]
    assert x == [False, False, True, True]


def test_out_of_range_vars_are_skipped() -> None:
    """Bounds check is `v <= 0 or v >= len(out)`: 0 and negatives are dropped,
    len(out) and beyond are dropped, but v == n_vars == len(out)-1 is applied."""
    x = [False, False, False, False, False]  # n_vars == 4

    out = apply_advice(x, Advice(set_true=(0, -1, 5, 6, len(x))))
    assert out == x

    out = apply_advice(x, Advice(set_true=(len(x) - 1,)))
    assert out == [False, False, False, False, True]


def test_apply_order_is_flip_then_set_true_then_set_false() -> None:
    """Pins the source's last-writer-wins order (advisor.py:41 @ 1e3eaaf)."""
    x = [False, False, False]

    # var 2 is flipped (-> True), then forced False. set_false wins.
    assert apply_advice(x, Advice(flip_vars=(2,), set_false=(2,))) == [False, False, False]
    # var 1 is forced True after being forced... nothing. set_true then holds.
    assert apply_advice(x, Advice(flip_vars=(1,), set_true=(1,))) == [False, True, False]


def test_advice_matches_llmadvice_fields_and_is_frozen() -> None:
    """Advice is field-for-field src/llm/advisor.py:LLMAdvice; State/Advice frozen."""
    assert [f.name for f in dataclasses.fields(Advice)] == [
        "flip_vars",
        "set_true",
        "set_false",
        "note",
    ]
    assert Advice().note == ""

    with pytest.raises(dataclasses.FrozenInstanceError):
        Advice().flip_vars = (1,)  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        _state((False, True)).cost = 0  # type: ignore[misc]
