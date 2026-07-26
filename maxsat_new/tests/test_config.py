"""Step 5 test (PORT_NOTES §10 row 5): config.py load + merge + resolution order.

Fails before maxsat_new/config.py exists (ImportError at collection); passes
after. Restore the module and `pytest maxsat_new/tests` is fully green.

Covers, per §10 row 5 and the step-5 contract:
  - resolution order defaults < YAML < -D: a param set in all three resolves to
    the -D value; YAML beats a rule default;
  - a -D concrete value is recorded in param_rules as
    {"rule": "cli_override", "value": ...} (rule bypassed AND provenance kept),
    and "cli_override" is a label, not a registered sizing rule;
  - resolved and param_rules come back with matching key sets;
  - parse_override yields JSON literals with a raw-string fallback;
  - the time_limit_s split (§9.4): both roles explicit -> preserved distinctly;
    omitting either, or using the old top-level/ls shape, is surfaced not guessed;
  - unknown ea keys are rejected in YAML AND via -D (ruling 2), listing knowns.
"""
from __future__ import annotations

import textwrap

import pytest

from maxsat_new import config as cfgmod
from maxsat_new.config import (
    CLI_OVERRIDE_RULE,
    DEFAULT_EA_PARAMS,
    parse_override,
    resolve_config,
)
from maxsat_new.features import InstanceFeatures
from maxsat_new.sizing import RULES


def _features(n_vars: int = 100) -> InstanceFeatures:
    """Instance features for resolution tests. Only n_vars drives the rules."""
    return InstanceFeatures(
        n_vars=n_vars,
        n_clauses=600,
        n_hard=100,
        n_soft=500,
        hard_frac=100 / 600,
        hard_soft_ratio=100 / 500,
        total_soft_weight=500,
    )


def _base() -> dict:
    """A minimal schema-valid raw config (both time_limit_s roles explicit)."""
    return {
        "budget": {"max_gens": 100, "time_limit_s": 60.0},
        "polish": {"time_limit_s": 0.05},
    }


# --- resolution order: defaults < YAML < -D ----------------------------------


def test_defaults_apply_when_yaml_and_cli_absent():
    cfg = resolve_config(_base(), _features(n_vars=100))
    # const defaults pass through uncoerced
    assert cfg.resolved_params["tournament_k"] == 4
    assert cfg.resolved_params["pmutate"] == 0.02
    assert cfg.resolved_params["elitism"] is True
    assert cfg.resolved_params["elite_frac"] == 0.05
    # derived defaults resolve against features (sqrt_vars / linear_vars)
    assert cfg.resolved_params["pop_size"] == 35        # round(3.5*sqrt(100))=35
    assert cfg.resolved_params["polish_flips"] == 2000  # round(10*100)=1000 -> clamp lo
    assert cfg.param_rules["pop_size"]["rule"] == "sqrt_vars"


def test_yaml_beats_rule_default():
    raw = _base()
    raw["ea"] = {"pop_size": {"rule": "const", "value": 50}}
    cfg = resolve_config(raw, _features())
    assert cfg.resolved_params["pop_size"] == 50
    # the sqrt_vars default was replaced wholesale, not coefficient-merged
    assert cfg.param_rules["pop_size"] == {"rule": "const", "value": 50}


def test_cli_beats_yaml_and_default():
    raw = _base()
    raw["ea"] = {"pop_size": {"rule": "const", "value": 50}}
    cfg = resolve_config(raw, _features(), cli_overrides=["ea.pop_size=77"])
    # default(sqrt_vars->35) < YAML(50) < -D(77): -D wins
    assert cfg.resolved_params["pop_size"] == 77


# --- -D provenance recorded as cli_override ----------------------------------


def test_cli_override_recorded_with_provenance():
    raw = _base()
    raw["ea"] = {"pop_size": {"rule": "const", "value": 50}}
    cfg = resolve_config(raw, _features(), cli_overrides=["ea.pop_size=77"])
    # rule bypassed AND the concrete value retained
    assert cfg.param_rules["pop_size"] == {
        "rule": CLI_OVERRIDE_RULE,
        "value": 77,
    }
    # cli_override is a provenance label, not a registered sizing rule
    assert CLI_OVERRIDE_RULE not in RULES


def test_cli_override_on_a_derived_param_bypasses_the_rule():
    # pop_size defaults to sqrt_vars; -D must bypass it entirely
    cfg = resolve_config(_base(), _features(), cli_overrides=["ea.pop_size=50"])
    assert cfg.resolved_params["pop_size"] == 50
    assert cfg.param_rules["pop_size"] == {
        "rule": CLI_OVERRIDE_RULE,
        "value": 50,
    }


# --- matching key sets (the §8 / STEP_04 invariant) --------------------------


def test_resolved_and_param_rules_have_matching_keys():
    raw = _base()
    raw["ea"] = {"tournament_k": {"rule": "const", "value": 9}}  # YAML override
    cfg = resolve_config(raw, _features(), cli_overrides=["ea.pop_size=77"])  # -D
    assert set(cfg.resolved_params) == set(cfg.param_rules)
    assert set(cfg.resolved_params) == set(DEFAULT_EA_PARAMS)


# --- parse_override literals --------------------------------------------------


def test_parse_override_json_literals_and_string_fallback():
    assert parse_override("ea.pop_size=50") == ("ea.pop_size", 50)
    assert parse_override("ea.elitism=false") == ("ea.elitism", False)
    assert parse_override("ea.pmutate=0.02") == ("ea.pmutate", 0.02)
    # unquoted non-JSON falls back to the raw string
    assert parse_override("provider.kind=random") == ("provider.kind", "random")
    with pytest.raises(ValueError):
        parse_override("no_equals_sign")


# --- time_limit_s split (§9.4) -----------------------------------------------


def test_time_limit_split_both_present_preserved():
    raw = {
        "budget": {"max_gens": 100, "time_limit_s": 180.0},
        "polish": {"time_limit_s": 0.1},
    }
    cfg = resolve_config(raw, _features())
    assert cfg.budget.time_limit_s == 180.0   # EA wall cap
    assert cfg.polish["time_limit_s"] == 0.1  # per-polish cap, distinct


def test_polish_time_limit_required_explicit():
    raw = {"budget": {"time_limit_s": 60.0}}  # polish.time_limit_s omitted
    with pytest.raises(ValueError, match=r"polish\.time_limit_s.*explicit"):
        resolve_config(raw, _features())


def test_budget_time_limit_required_explicit():
    raw = {"polish": {"time_limit_s": 0.05}}  # budget.time_limit_s omitted
    with pytest.raises(ValueError, match=r"budget\.time_limit_s.*explicit"):
        resolve_config(raw, _features())


def test_legacy_top_level_time_limit_rejected():
    raw = {"time_limit_s": 0.05, "polish": {"time_limit_s": 0.05}}
    with pytest.raises(ValueError, match=r"old both-at-once"):
        resolve_config(raw, _features())


def test_legacy_ls_block_rejected():
    raw = dict(_base(), ls={"time_limit_s": 0.05})
    with pytest.raises(ValueError, match=r"'ls' block is the old schema"):
        resolve_config(raw, _features())


# --- unknown ea keys rejected in YAML AND via -D (ruling 2) -------------------


def test_unknown_ea_key_in_yaml_rejected():
    raw = _base()
    raw["ea"] = {"tourament_k": {"rule": "const", "value": 4}}  # typo
    with pytest.raises(ValueError, match=r"tourament_k") as exc:
        resolve_config(raw, _features())
    # message lists the known keys, mirroring sizing.py's unknown-rule error
    assert "pop_size" in str(exc.value)


def test_unknown_ea_key_via_cli_rejected():
    with pytest.raises(ValueError, match=r"tourament_k"):
        resolve_config(_base(), _features(), cli_overrides=["ea.tourament_k=4"])


def test_coefficient_level_override_rejected():
    with pytest.raises(ValueError, match=r"coefficient-level"):
        resolve_config(_base(), _features(), cli_overrides=["ea.pop_size.a=4.0"])


# --- unknown top-level block: ignored with a warning (loader reuse) ----------


def test_unknown_top_level_block_warns_not_rejected():
    raw = dict(_base(), noise_adapt={"foo": 1})  # LS/satlike noise (§1)
    with pytest.warns(UserWarning, match=r"noise_adapt"):
        cfg = resolve_config(raw, _features())
    assert cfg.resolved_params["tournament_k"] == 4  # still resolves


# --- YAML load path -----------------------------------------------------------


def test_load_yaml_roundtrip(tmp_path):
    p = tmp_path / "cfg.yaml"
    p.write_text(
        textwrap.dedent(
            """\
            solver: memetic_ea
            seed: 7
            budget:
              max_gens: 100
              time_limit_s: 60.0
            ea:
              pop_size: { rule: const, value: 42 }
            polish:
              time_limit_s: 0.05
            provider:
              kind: noop
            """
        )
    )
    raw = cfgmod.load_yaml(str(p))
    cfg = resolve_config(raw, _features())
    assert cfg.solver == "memetic_ea"
    assert cfg.seed == 7
    assert cfg.resolved_params["pop_size"] == 42
    assert cfg.provider == {"kind": "noop"}
