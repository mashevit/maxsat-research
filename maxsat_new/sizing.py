"""Named sizing rules + `resolve_params` (rule name -> concrete value).

NEW module per PORT_NOTES §4 ("Config + sizing-rule design"). This is **not** a
port: §3's port map has no row for `sizing.py`. §4 is the spec — the rule set,
the round-then-clamp order, the `c.get("b", 0)` defaults, and the two-parallel-
dicts contract are copied from it.

Mechanism (§4, choice (a)): a finite, enumerable registry of named pure
functions. YAML supplies a rule name + coefficients; a typo in the name or a
missing coefficient is a hard error, never a silent experiment. Adding a rule is
one decorated function and no edit anywhere else.

Purity (§4 reproducibility claim): every rule is a pure function of
`(features, coeffs)`. No RNG, no clock, no I/O, no global state — same inputs
always give the same output, so a run is reproducible from the record's
`param_rules` alone (PORT_NOTES §8).

Self-contained: imports only stdlib and `maxsat_new.features`.
"""
from __future__ import annotations

import math
from typing import Callable, Dict, Tuple

from maxsat_new.features import InstanceFeatures

# A rule maps (features, coeffs) -> a concrete value (int | float | bool).
Rule = Callable[[InstanceFeatures, dict], object]

# The registry. Enumerable: `sorted(RULES)` lists the rule names.
RULES: Dict[str, Rule] = {}


def rule(name: str):
    """Register a rule under `name`. Adding a rule is a single decorated fn."""

    def deco(fn: Rule) -> Rule:
        RULES[name] = fn
        return fn

    return deco


def _clamp(x, lo, hi):
    """Clamp `x` into `[lo, hi]`. Rounding happens before this call (§4)."""
    return max(lo, min(hi, x))


# --- Rule set (bodies verbatim from PORT_NOTES §4) ---------------------------
#
# Required coefficients are read via subscript (`c["a"]`) so a missing one is a
# hard error (surfaced with a clear message by `resolve_params`). Optional ones
# use `c.get(..., default)`. `round()` is Python's built-in banker's rounding,
# kept exactly as §4 writes it (deterministic; STEP_04_NOTES "Decisions").


@rule("const")
def _const(f: InstanceFeatures, c: dict):  # {rule: const, value: X}
    # Returns value UNCOERCED so a bool (elitism) stays bool and a float
    # (pmutate) stays float (§4; STEP_04 test). No int-coercion here.
    return c["value"]


@rule("sqrt_vars")
def _sqrt_vars(f: InstanceFeatures, c: dict):  # {rule: sqrt_vars, a, lo, hi}
    return _clamp(round(c["a"] * math.sqrt(f.n_vars)), c["lo"], c["hi"])


@rule("linear_vars")
def _linear_vars(f: InstanceFeatures, c: dict):  # {rule: linear_vars, a, b, lo, hi}
    return _clamp(round(c["a"] * f.n_vars + c.get("b", 0)), c["lo"], c["hi"])


@rule("linear_clauses")
def _linear_clauses(f: InstanceFeatures, c: dict):  # {rule: linear_clauses, a, b, lo, hi}
    return _clamp(round(c["a"] * f.n_clauses + c.get("b", 0)), c["lo"], c["hi"])


# --- Resolution --------------------------------------------------------------


def resolve_params(
    param_specs: Dict[str, dict],
    features: InstanceFeatures,
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Resolve a mapping of `{param_name: rule_spec}` against `features`.

    Input (STEP_04 audit item 6): `param_specs` is the merged `ea:` block — a
    dict mapping each param name to a rule spec `{"rule": NAME, <coeffs>}`. Not
    the whole config.

    Contract for the caller (config.py, step 5): `resolve_params` is DICT-ONLY.
    Every value in `param_specs` MUST be a `{"rule": ...}` spec — including fixed
    params (`{"rule": "const", "value": X}`) and CLI overrides, which config.py
    must present as `{"rule": "cli_override", "value": X}` (PORT_NOTES §4). A
    bare scalar carries no provenance and sizing.py cannot tell a CLI override
    from a hand-edited YAML value, so it refuses one rather than guess. This
    keeps §4's "every param resolves through a rule" invariant true here with no
    special cases.

    (`cli_override` itself is NOT a rule registered in this module; it is a
    provenance label config.py stamps, out of scope for step 4.)

    Returns two dicts with IDENTICAL key sets (PORT_NOTES §8):
      - `resolved`:    {param_name: concrete value}
      - `param_rules`: {param_name: the rule spec, for provenance}
    """
    resolved: Dict[str, object] = {}
    param_rules: Dict[str, object] = {}

    for name, spec in param_specs.items():
        if not isinstance(spec, dict):
            raise TypeError(
                f"param {name!r}: expected a rule spec dict like "
                f"{{'rule': NAME, ...}}, got {type(spec).__name__} {spec!r}. "
                f"resolve_params is dict-only; the caller (config.py) must wrap "
                f"a bare value as {{'rule': 'const'|'cli_override', 'value': X}}."
            )
        if "rule" not in spec:
            raise KeyError(
                f"param {name!r}: rule spec is missing the 'rule' key: {spec!r}"
            )
        rule_name = spec["rule"]
        if rule_name not in RULES:
            raise ValueError(
                f"param {name!r}: unknown rule {rule_name!r}; "
                f"known rules: {sorted(RULES)}"
            )
        try:
            value = RULES[rule_name](features, spec)
        except KeyError as e:
            missing = e.args[0] if e.args else "?"
            raise KeyError(
                f"rule {rule_name!r} (param {name!r}) is missing required "
                f"coefficient {missing!r}"
            ) from e

        resolved[name] = value
        param_rules[name] = dict(spec)  # copy: provenance, not aliased to input

    return resolved, param_rules
