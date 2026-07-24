"""Step 4 test (PORT_NOTES §10 row 4): features.extract + sizing rules/resolver.

Fails before maxsat_new/features.py and maxsat_new/sizing.py exist (ImportError);
passes after.

Covers, per §10 row 4 and STEP_04_NOTES "Test design":
  - sqrt_vars clamps at BOTH lo and hi, and leaves a mid-range value untouched
    (a clamp that always returned lo or hi would fail the mid assertion);
  - resolve_params emits concrete value + rule spec with matching key sets;
  - sorted(RULES) enumerates exactly the four registered names;
  - unknown rule raises; missing required coefficient raises; bare scalar raises;
  - const passes a bool and a float through uncoerced;
  - extract on the committed mini.wcnf returns the known feature values, and the
    n_soft == 0 / n_clauses == 0 degenerate fallbacks behave per §4;
  - purity: same rule, same inputs -> equal results.
"""
from __future__ import annotations

import os

import pytest

from maxsat_new.cnf import WCNF, Clause
from maxsat_new.features import InstanceFeatures, extract
from maxsat_new.sizing import RULES, resolve_params

MINI = os.path.join(os.path.dirname(__file__), "data", "mini.wcnf")


def _features(**overrides) -> InstanceFeatures:
    """An InstanceFeatures with sensible defaults, for rule-focused tests."""
    base = dict(
        n_vars=100,
        n_clauses=600,
        n_hard=100,
        n_soft=500,
        hard_frac=100 / 600,
        hard_soft_ratio=100 / 500,
        total_soft_weight=500,
    )
    base.update(overrides)
    return InstanceFeatures(**base)


# --- sqrt_vars three-point clamp ---------------------------------------------


def test_sqrt_vars_clamps_low_high_and_leaves_midrange() -> None:
    coeffs = {"a": 1, "lo": 10, "hi": 100}
    fn = RULES["sqrt_vars"]

    # Low: sqrt(1)=1 -> round 1 -> clamped UP to lo=10.
    assert fn(_features(n_vars=1), coeffs) == 10
    # High: sqrt(40000)=200 -> round 200 -> clamped DOWN to hi=100.
    assert fn(_features(n_vars=40000), coeffs) == 100
    # Mid: sqrt(2500)=50 -> round 50 -> inside [10,100], untouched.
    # This value equals neither lo nor hi, so a clamp that always returned a
    # bound would fail here.
    assert fn(_features(n_vars=2500), coeffs) == 50


# --- resolve_params: two dicts, matching keys, value + provenance ------------


def test_resolve_params_emits_value_and_rule_with_matching_keys() -> None:
    specs = {
        "pop_size": {"rule": "sqrt_vars", "a": 3.5, "lo": 20, "hi": 200},
        "polish_flips": {"rule": "linear_vars", "a": 10, "b": 0, "lo": 2000, "hi": 50000},
        "tournament_k": {"rule": "const", "value": 4},
        "pmutate": {"rule": "const", "value": 0.02},
        "elitism": {"rule": "const", "value": True},
    }
    feats = _features(n_vars=100, n_clauses=600)
    resolved, param_rules = resolve_params(specs, feats)

    # Identical key sets across both dicts, matching the input (PORT_NOTES §8).
    assert set(resolved) == set(param_rules) == set(specs)

    # Concrete values: sqrt_vars(100) = clamp(round(3.5*10)=35, 20, 200) = 35.
    assert resolved["pop_size"] == 35
    # linear_vars(600 clauses? no -> vars=100): clamp(round(10*100+0)=1000,...) = 2000.
    assert resolved["polish_flips"] == 2000
    assert resolved["tournament_k"] == 4

    # Provenance: the rule spec is stored verbatim (copied, not aliased).
    assert param_rules["pop_size"] == {"rule": "sqrt_vars", "a": 3.5, "lo": 20, "hi": 200}
    assert param_rules["pop_size"] is not specs["pop_size"]


# --- registry is enumerable and exactly the four rules -----------------------


def test_rules_enumerates_exactly_four() -> None:
    assert sorted(RULES) == ["const", "linear_clauses", "linear_vars", "sqrt_vars"]


# --- error surfaces: unknown rule, missing coeff, bare scalar ----------------


def test_unknown_rule_raises_and_lists_known_rules() -> None:
    with pytest.raises(ValueError) as ei:
        resolve_params({"pop_size": {"rule": "sqrt_of_vars"}}, _features())
    msg = str(ei.value)
    assert "sqrt_of_vars" in msg
    assert "sqrt_vars" in msg  # sorted(RULES) is listed


def test_missing_required_coefficient_raises_naming_rule_and_key() -> None:
    with pytest.raises(KeyError) as ei:
        # sqrt_vars requires "a"; only lo/hi given.
        resolve_params({"pop_size": {"rule": "sqrt_vars", "lo": 1, "hi": 2}}, _features())
    msg = str(ei.value)
    assert "sqrt_vars" in msg and "'a'" in msg


def test_bare_scalar_raises() -> None:
    with pytest.raises(TypeError):
        resolve_params({"pop_size": 50}, _features())


# --- const passes bool and float through uncoerced ---------------------------


def test_const_does_not_coerce_bool_or_float() -> None:
    resolved, _ = resolve_params(
        {
            "elitism": {"rule": "const", "value": True},
            "pmutate": {"rule": "const", "value": 0.02},
        },
        _features(),
    )
    # elitism stays True (a bool), not 1.
    assert resolved["elitism"] is True
    assert type(resolved["elitism"]) is bool
    # pmutate stays 0.02 (a float), not 0.
    assert resolved["pmutate"] == 0.02
    assert isinstance(resolved["pmutate"], float)


# --- extract on the committed mini.wcnf --------------------------------------


def test_extract_on_mini_wcnf_known_values() -> None:
    feats = extract(WCNF.parse_dimacs(MINI))
    assert feats.n_vars == 5
    assert feats.n_clauses == 8
    assert feats.n_hard == 3
    assert feats.n_soft == 5
    assert feats.total_soft_weight == 15  # soft weights 3+5+2+4+1
    assert feats.hard_frac == 3 / 8
    assert feats.hard_soft_ratio == 3 / 5


# --- degenerate fallbacks (§4) -----------------------------------------------


def test_extract_no_soft_clauses_ratio_falls_back_to_n_hard() -> None:
    w = WCNF(n_vars=2, hard_weight=100)
    w.clauses.append(Clause(weight=100, lits=[1], is_hard=True))
    w.clauses.append(Clause(weight=100, lits=[2], is_hard=True))
    feats = extract(w)
    assert feats.n_soft == 0
    assert feats.total_soft_weight == 0
    assert feats.hard_soft_ratio == 2  # n_soft == 0 -> n_hard


def test_extract_empty_instance_hard_frac_is_zero() -> None:
    feats = extract(WCNF(n_vars=3, hard_weight=100))  # no clauses at all
    assert feats.n_clauses == 0
    assert feats.hard_frac == 0.0
    # n_soft == 0 and n_hard == 0 -> ratio falls back to n_hard == 0.
    assert feats.hard_soft_ratio == 0.0


# --- purity ------------------------------------------------------------------


def test_rules_are_pure() -> None:
    feats = _features(n_vars=100, n_clauses=600)
    for name, coeffs in [
        ("const", {"value": 7}),
        ("sqrt_vars", {"a": 3.5, "lo": 20, "hi": 200}),
        ("linear_vars", {"a": 10, "b": 3, "lo": 2000, "hi": 50000}),
        ("linear_clauses", {"a": 2, "b": 1, "lo": 0, "hi": 10000}),
    ]:
        assert RULES[name](feats, coeffs) == RULES[name](feats, coeffs)
