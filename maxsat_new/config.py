"""YAML load + merge + resolution order for the runner (PORT_NOTES §4, §7, §9.4).

NEW module per PORT_NOTES §4. This is **not** a port: §3's port map has no row
for `config.py`. The only thing carried over from `src/cli/run_ea.py` is the
*intent* of its `-D` handling (`_parse_kv_override` / `_deep_set`,
`run_ea.py:83-106`): dotted keys, JSON-literal values, whole-value override. The
old precedence was YAML < `-D` with no rule-defaults layer and no provenance;
this module adds both (§4).

Resolution order (§4):

    rule defaults  <  YAML  <  CLI -D override  <  (derive per instance)

- Rule defaults: `DEFAULT_EA_PARAMS` — one default rule spec per `ea` param
  (the §4 derived-vs-fixed table). A YAML `ea:` block overrides per param;
  `-D` overrides YAML.
- Derive per instance: `resolve_params(specs, features)` runs the specs against
  the instance's features (`features.extract`).

DICT-ONLY hand-off (STEP_04 ruling 1). `resolve_params` only ever sees
`{"rule": NAME, ...}` specs for rules registered in `sizing.py`. This module owns
wrapping a `-D` concrete value as `{"rule": "cli_override", "value": X}` BEFORE
resolution. `"cli_override"` is a **provenance label constructed here**, NOT a
rule registered in `sizing.py`; the specs carrying it are resolved by this module
(the value passes straight through) and never handed to `resolve_params`.

`-D` is whole-value-only for now: `-D ea.pop_size=50` replaces the resolved value
for that param. Coefficient-level overrides (`-D ea.pop_size.a=4.0`) are rejected,
flagged as a later addition (PORT_NOTES §4 / step 5 contract).

Schema ownership (Step 05 ruling 2). Unknown keys are rejected **within blocks
this module owns the schema for** (`ea`, `budget`, `polish`, `provider`), the
same way `sizing.py` rejects an unknown rule name — a typo is not a silent
experiment. Unknown *top-level* blocks are ignored-with-warning, so the loader
can be reused on the LS/satlike configs that carry `noise_adapt` / `seeding` /
`llm` / `bench` (§1). `-D` overrides go through the **same** schema check as YAML.

time_limit_s split (§9.4). The new schema names the two roles separately:
`budget.time_limit_s` (EA wall cap) and `polish.time_limit_s` (per-polish cap).
Both are **required and explicit**; neither is defaulted, so omitting one cannot
silently reconstruct the old both-at-once meaning (`memetic.py:63`). A bare
top-level `time_limit_s` or an `ls:` block (the old shape) is rejected with a
message telling the author to split.

Self-contained: imports only stdlib and `maxsat_new.{features,sizing}`.
"""
from __future__ import annotations

import copy
import json
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple

from maxsat_new.features import InstanceFeatures, extract
from maxsat_new.sizing import resolve_params

# --- Provenance label for a -D override (NOT a rule in sizing.RULES) ----------
CLI_OVERRIDE_RULE = "cli_override"

# --- Rule defaults (the §4 derived-vs-fixed table, as rule specs) -------------
# YAML overrides per param; -D overrides YAML. These keys ARE the `ea` schema and
# match §8's `resolved_params` key set exactly.
DEFAULT_EA_PARAMS: Dict[str, dict] = {
    "pop_size":     {"rule": "sqrt_vars",   "a": 3.5, "lo": 20, "hi": 200},
    "polish_flips": {"rule": "linear_vars", "a": 10, "b": 0, "lo": 2000, "hi": 50000},
    "tournament_k": {"rule": "const", "value": 4},
    "pmutate":      {"rule": "const", "value": 0.02},
    "elitism":      {"rule": "const", "value": True},
    "elite_frac":   {"rule": "const", "value": 0.05},
}

# --- Schema: the blocks this module owns and their known keys -----------------
# `time_limit_s` (budget + polish) is intentionally listed but NOT defaulted;
# see split (§9.4). `noise`/`hard_safe` DO default.
KNOWN_BLOCK_KEYS: Dict[str, frozenset] = {
    "ea": frozenset(DEFAULT_EA_PARAMS),
    "budget": frozenset({"max_gens", "time_limit_s"}),
    "polish": frozenset({"time_limit_s", "noise", "hard_safe"}),
    "provider": frozenset({"kind"}),
}
KNOWN_TOP_LEVEL = frozenset(
    {"ea", "budget", "polish", "provider", "solver", "instance", "seed"}
)


@dataclass(frozen=True)
class Budget:
    """EA stop conditions. `time_limit_s` is the wall cap (§4: explicit)."""

    max_gens: int
    time_limit_s: float


@dataclass(frozen=True)
class ResolvedConfig:
    """Fully resolved run config. `resolved_params`/`param_rules` feed §8.

    `resolved_params` and `param_rules` carry IDENTICAL key sets (the §8 /
    STEP_04 invariant), preserved even where a `-D` value injects a
    `cli_override` spec.
    """

    solver: str
    instance: Optional[str]
    seed: int
    budget: Budget
    resolved_params: Dict[str, Any]
    param_rules: Dict[str, Any]
    polish: Dict[str, Any]
    provider: Dict[str, Any]


# --- YAML load ----------------------------------------------------------------


def load_yaml(path: Optional[str]) -> dict:
    """Load a YAML config to a dict. `{}` when `path` is falsy."""
    if not path:
        return {}
    import yaml  # local import: only needed when a path is given

    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# --- -D override parsing (intent ported from run_ea.py:92-106) ----------------


def parse_override(token: str) -> Tuple[str, Any]:
    """Parse ``"a.b.c=123"`` -> ``("a.b.c", 123)``.

    Value is a JSON literal (numbers/bools/null/arrays/objects) with a raw-string
    fallback, matching `run_ea.py:_parse_kv_override`.
    """
    if "=" not in token:
        raise ValueError(f"expected KEY=VALUE, got {token!r}")
    k, v = token.split("=", 1)
    k = k.strip()
    v = v.strip()
    try:
        val: Any = json.loads(v)
    except Exception:
        val = v  # raw string fallback (e.g. provider.kind=random)
    return k, val


def _deep_set(d: dict, dotted_key: str, val: Any) -> None:
    """Set a dotted key into a nested dict, creating intermediates."""
    keys = dotted_key.split(".")
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = val


# --- Schema check (ruling 2): mirror sizing.py's unknown-rule error -----------


def _check_block_key(block: str, key: str) -> None:
    """Reject an unknown key within an owned block, listing the known keys."""
    known = KNOWN_BLOCK_KEYS[block]
    if key not in known:
        raise ValueError(
            f"unknown {block!r} config key {key!r}; "
            f"known {block!r} keys: {sorted(known)}"
        )


# --- ea spec resolution, honoring the DICT-ONLY hand-off ----------------------


def _resolve_specs(
    specs: Dict[str, dict], features: InstanceFeatures
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve merged `ea` specs, handling `cli_override` here (not in sizing).

    Rule specs go to `resolve_params`; `cli_override` specs are resolved here
    (concrete value passes through). Both branches feed the two output dicts, so
    the key sets stay identical across the whole `ea` param set.
    """
    rule_specs = {
        n: s for n, s in specs.items() if s.get("rule") != CLI_OVERRIDE_RULE
    }
    resolved, param_rules = resolve_params(rule_specs, features)

    for name, spec in specs.items():
        if spec.get("rule") == CLI_OVERRIDE_RULE:
            if "value" not in spec:
                raise KeyError(
                    f"param {name!r}: {CLI_OVERRIDE_RULE!r} spec is missing "
                    f"'value': {spec!r}"
                )
            resolved[name] = spec["value"]
            param_rules[name] = dict(spec)

    return resolved, param_rules


# --- The split (§9.4) ---------------------------------------------------------


def _split_time_limits(merged: dict) -> Tuple[float, float]:
    """Return ``(budget_wall, polish_percall)``; enforce the §9.4 split.

    Both must be explicit. A bare top-level `time_limit_s` or an `ls:` block is
    the old both-at-once shape and is refused.
    """
    if "time_limit_s" in merged and not isinstance(merged["time_limit_s"], dict):
        raise ValueError(
            "top-level 'time_limit_s' is the old both-at-once shape; split it "
            "into budget.time_limit_s (EA wall cap) and polish.time_limit_s "
            "(per-polish cap) — the time_limit_s split (PORT_NOTES §9.4)."
        )
    if "ls" in merged:
        raise ValueError(
            "'ls' block is the old schema; per-polish cap now lives at "
            "polish.time_limit_s (the time_limit_s split, PORT_NOTES §9.4)."
        )

    budget_block = merged.get("budget") or {}
    polish_block = merged.get("polish") or {}

    if "time_limit_s" not in budget_block:
        raise ValueError(
            "budget.time_limit_s is required and must be explicit since the "
            "time_limit_s split (PORT_NOTES §9.4): it is the EA wall cap and is "
            "not defaulted, so omitting it cannot silently fall back to the "
            "per-polish cap."
        )
    if "time_limit_s" not in polish_block:
        raise ValueError(
            "polish.time_limit_s is required and must be explicit since the "
            "time_limit_s split (PORT_NOTES §9.4): it is the per-polish cap and "
            "is not defaulted, so omitting it cannot silently fall back to the "
            "EA wall cap."
        )

    return float(budget_block["time_limit_s"]), float(polish_block["time_limit_s"])


# --- Orchestration ------------------------------------------------------------


def resolve_config(
    raw: dict,
    features: InstanceFeatures,
    *,
    cli_overrides: Sequence[str] = (),
    seed: Optional[int] = None,
    instance: Optional[str] = None,
    solver: Optional[str] = None,
) -> ResolvedConfig:
    """Resolve a loaded config dict against instance `features`.

    `cli_overrides` are raw ``KEY=VALUE`` `-D` tokens. `seed`/`instance`/`solver`
    are the §7 flag surface; each overrides the corresponding YAML top-level.
    """
    merged = copy.deepcopy(raw or {})

    # --- apply -D (schema-checked the same as YAML) ---
    cli_keys = set()
    for token in cli_overrides:
        key, val = parse_override(token)
        segs = key.split(".")
        if segs[0] in KNOWN_BLOCK_KEYS:
            if len(segs) != 2:
                raise ValueError(
                    f"override {key!r}: only whole-value 'block.param' overrides "
                    f"are supported; coefficient-level overrides like "
                    f"'ea.pop_size.a' are not supported this step."
                )
            _check_block_key(segs[0], segs[1])
        _deep_set(merged, key, val)
        cli_keys.add(key)

    # --- schema-check owned blocks (catches YAML typos) ---
    for block in KNOWN_BLOCK_KEYS:
        b = merged.get(block)
        if isinstance(b, dict):
            for k in b:
                _check_block_key(block, k)

    # --- time_limit_s split (§9.4); rejects old shapes before we warn on them ---
    wall, percall = _split_time_limits(merged)

    # --- ignore-with-warning unknown top-level blocks (loader reuse) ---
    for k in merged:
        if k not in KNOWN_TOP_LEVEL:
            warnings.warn(
                f"ignoring unknown top-level config key {k!r}", stacklevel=2
            )

    # --- ea specs: defaults < YAML < -D ---
    specs: Dict[str, dict] = {n: dict(s) for n, s in DEFAULT_EA_PARAMS.items()}
    for name, val in (merged.get("ea") or {}).items():
        if f"ea.{name}" in cli_keys:
            specs[name] = {"rule": CLI_OVERRIDE_RULE, "value": val}
        elif isinstance(val, dict):
            specs[name] = dict(val)
        else:
            raise TypeError(
                f"ea.{name}: YAML value must be a rule spec dict like "
                f"{{'rule': NAME, ...}}, got {type(val).__name__} {val!r}. Use "
                f"{{'rule': 'const', 'value': X}} for a fixed value, or a -D "
                f"override for a debug value."
            )
    resolved_params, param_rules = _resolve_specs(specs, features)

    # --- budget / polish / provider ---
    budget_block = merged.get("budget") or {}
    budget = Budget(
        max_gens=int(budget_block.get("max_gens", 100)),
        time_limit_s=wall,
    )

    polish_block = merged.get("polish") or {}
    polish = {
        "time_limit_s": percall,
        "noise": float(polish_block.get("noise", 0.10)),
        "hard_safe": bool(polish_block.get("hard_safe", True)),
    }

    provider_block = merged.get("provider") or {}
    provider = {"kind": provider_block.get("kind", "noop")}

    return ResolvedConfig(
        solver=solver if solver is not None else merged.get("solver", "memetic_ea"),
        instance=instance if instance is not None else merged.get("instance"),
        seed=int(seed if seed is not None else merged.get("seed", 1)),
        budget=budget,
        resolved_params=resolved_params,
        param_rules=param_rules,
        polish=polish,
        provider=provider,
    )


def load_and_resolve(
    path: Optional[str],
    wcnf,
    *,
    cli_overrides: Sequence[str] = (),
    seed: Optional[int] = None,
    instance: Optional[str] = None,
    solver: Optional[str] = None,
) -> ResolvedConfig:
    """Convenience for the runner (step 9): load YAML + extract + resolve."""
    raw = load_yaml(path)
    features = extract(wcnf)
    return resolve_config(
        raw,
        features,
        cli_overrides=cli_overrides,
        seed=seed,
        instance=instance,
        solver=solver,
    )
