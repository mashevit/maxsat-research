# Step 05 notes — config.py (YAML load + merge + resolution order)

Implements Step 5 of PORT_NOTES.md §10 (row 5: "runner config"). Like Step 4 this
is **new code, not a port**: §3's port map has no row for `config.py`. The spec is
PORT_NOTES §4 (resolution order), §7 (flag surface), §9.4 (the `time_limit_s`
split); §8 pins the record fields the resolver feeds. The only thing carried over
from `src/cli/run_ea.py` is the *intent* of its `-D` handling
(`_parse_kv_override` / `_deep_set`, `run_ea.py:83-106`): dotted keys, JSON-literal
values, whole-value override. The old precedence was `YAML < -D` with **no**
rule-defaults layer and **no** provenance; this module adds both (§4).

## Files created
- `maxsat_new/config.py` — YAML load, defaults<YAML<`-D` merge, `-D`→`cli_override`
  wrapping, the §9.4 `time_limit_s` split, and `resolve_config` (the resolution
  entry point that hands the `ea:` block to `sizing.resolve_params`).
- `maxsat_new/tests/test_config.py` — one test file, §10 row 5 (17 tests).

## config.py public surface

Module constants:

```python
CLI_OVERRIDE_RULE = "cli_override"            # provenance label; NOT a sizing rule
DEFAULT_EA_PARAMS: Dict[str, dict]            # §4 default rule spec per ea param
KNOWN_BLOCK_KEYS: Dict[str, frozenset]        # schema for ea/budget/polish/provider
KNOWN_TOP_LEVEL: frozenset                    # accepted top-level keys
```

Dataclasses:

```python
@dataclass(frozen=True)
class Budget:
    max_gens: int
    time_limit_s: float                        # EA wall cap (§4: explicit)

@dataclass(frozen=True)
class ResolvedConfig:
    solver: str
    instance: Optional[str]
    seed: int
    budget: Budget
    resolved_params: Dict[str, Any]            # ea concrete values (feeds §8)
    param_rules: Dict[str, Any]                # ea provenance, IDENTICAL key set
    polish: Dict[str, Any]                     # {time_limit_s, noise, hard_safe}
    provider: Dict[str, Any]                   # {kind: ...}
```

Public functions:

```python
def load_yaml(path: Optional[str]) -> dict: ...
def parse_override(token: str) -> Tuple[str, Any]: ...          # "a.b=1" -> ("a.b", 1)
def resolve_config(
    raw: dict,
    features: InstanceFeatures,
    *,
    cli_overrides: Sequence[str] = (),
    seed: Optional[int] = None,
    instance: Optional[str] = None,
    solver: Optional[str] = None,
) -> ResolvedConfig: ...
def load_and_resolve(
    path: Optional[str],
    wcnf,
    *,
    cli_overrides: Sequence[str] = (),
    seed: Optional[int] = None,
    instance: Optional[str] = None,
    solver: Optional[str] = None,
) -> ResolvedConfig: ...                                        # step-9 convenience
```

Private helpers (not surface): `_deep_set`, `_check_block_key`, `_resolve_specs`,
`_split_time_limits`.

## Resolution order as implemented

`rule defaults  <  YAML  <  CLI -D  <  (derive per instance)` — exactly §4.

1. **Rule defaults.** `resolve_config` seeds the `ea` specs from a per-param copy
   of `DEFAULT_EA_PARAMS` (the §4 derived-vs-fixed table): `pop_size`→`sqrt_vars`,
   `polish_flips`→`linear_vars`, and `tournament_k`/`pmutate`/`elitism`/`elite_frac`
   →`const`. These keys ARE the `ea` schema and match §8's `resolved_params` key
   set exactly.
2. **YAML.** For each param present in `merged["ea"]`, the whole spec dict replaces
   the default (per-param **whole-spec** replacement — no coefficient-level merge,
   consistent with the whole-value `-D` rule).
3. **CLI `-D`.** Applied via `_deep_set` into a `deepcopy` of `raw`, with each
   dotted key recorded in `cli_keys`. When building the `ea` specs, any param whose
   `ea.<name>` key is in `cli_keys` is replaced by
   `{"rule": "cli_override", "value": <the -D value>}`.
4. **Derive.** `_resolve_specs(specs, features)` produces the concrete values.

### `-D` wrapping and the DICT-ONLY contract (Step 04 ruling 1)

`_resolve_specs` splits the merged specs by rule name:

```python
rule_specs = {n: s for n, s in specs.items() if s.get("rule") != CLI_OVERRIDE_RULE}
resolved, param_rules = resolve_params(rule_specs, features)   # only registered rules
# then cli_override specs resolved HERE: value passes through, spec copied to param_rules
```

So `resolve_params` **only ever sees `{"rule": NAME, ...}` dicts for rules
registered in `sizing.py`** — `cli_override` never reaches it. `"cli_override"` is
a provenance label constructed in config.py, confirmed **not** in `sizing.RULES`
(asserted by `test_cli_override_recorded_with_provenance`). Because every param in
`specs` is represented in both output dicts (rule branch or override branch),
`resolved_params` and `param_rules` keep **identical key sets** (== the
`DEFAULT_EA_PARAMS` key set), preserving the §8 / STEP_04 invariant even when a
`-D` value injects an override.

A YAML `ea.<name>` that is a bare scalar (not a rule dict) and is **not** a `-D`
override is rejected before it can reach `resolve_params`:

> `ea.{name}: YAML value must be a rule spec dict like {'rule': NAME, ...}, got
> {type} {val!r}. Use {'rule': 'const', 'value': X} for a fixed value, or a -D
> override for a debug value.`

## The two rulings and how they landed

### Ruling 1 — `polish.time_limit_s` required-explicit (config.py only, §4 NOT edited)

`_split_time_limits` requires **both** roles explicit and defaults neither. §4 was
not edited: §4 always *shows* `polish.time_limit_s` set (=0.05) and never said
"default it if absent"; the ruling is the narrow config-layer consequence — the
key's absence raises rather than falling back to the EA cap. Actual message
(quoted verbatim from `config.py`):

> `polish.time_limit_s is required and must be explicit since the time_limit_s
> split (PORT_NOTES §9.4): it is the per-polish cap and is not defaulted, so
> omitting it cannot silently fall back to the EA wall cap.`

The symmetric budget message:

> `budget.time_limit_s is required and must be explicit since the time_limit_s
> split (PORT_NOTES §9.4): it is the EA wall cap and is not defaulted, so omitting
> it cannot silently fall back to the per-polish cap.`

The wording deliberately names the key and states *why* it is not defaulted, so it
isn't quietly re-added as a convenience default in a later step.

### Ruling 2 — unknown-key reject, mirroring `sizing.py`'s unknown-rule error

`_check_block_key` raises for an unknown key in an **owned** block, listing the
knowns (same shape as `sizing.py`'s unknown-rule `ValueError`):

> `unknown {block!r} config key {key!r}; known {block!r} keys: {sorted(known)}`

- **Strict blocks (owned schema):** `ea`, `budget`, `polish`, `provider` — every
  key in each is checked against `KNOWN_BLOCK_KEYS`.
- **Top-level:** unknown top-level blocks are **ignored-with-warning**
  (`warnings.warn("ignoring unknown top-level config key ...")`), not rejected, so
  the loader survives the LS/satlike configs that carry
  `noise_adapt`/`seeding`/`llm`/`bench` (§1). Accepted top-level keys:
  `KNOWN_TOP_LEVEL = {ea, budget, polish, provider, solver, instance, seed}`.
- **`-D` uses the SAME check.** In the override loop, a `-D` whose first segment is
  an owned block is passed through `_check_block_key` before `_deep_set`, so
  `-D ea.tourament_k=4` hits the identical rejection path as the YAML typo. A `-D`
  into an owned block with more than two path segments is rejected as
  coefficient-level (see Deviations):

> `override {key!r}: only whole-value 'block.param' overrides are supported;
> coefficient-level overrides like 'ea.pop_size.a' are not supported this step.`

## The `time_limit_s` split (§9.4)

Old code (`memetic.py:63`) let a single `time_limit_s` serve as **both** the EA
wall cap and the per-polish cap when the top-level key was absent (confirmed in the
Phase-1 audit: `cfg.yaml` is the only EA-group config that triggers this). The new
schema names the two roles separately and `_split_time_limits` disambiguates:

- `budget.time_limit_s` → EA wall cap (`Budget.time_limit_s`).
- `polish.time_limit_s` → per-polish cap (`polish["time_limit_s"]`).
- **Both required, neither defaulted** → a config setting only one raises (ruling
  1 messages above) instead of copying the set one into the empty role. Behavior is
  therefore preserved exactly when both are set, and the old both-at-once meaning
  cannot be silently reconstructed.
- **Old shapes refused up front:** a bare top-level `time_limit_s` (`> top-level
  'time_limit_s' is the old both-at-once shape; split it into budget.time_limit_s
  ... and polish.time_limit_s ...`) and an `ls:` block (`> 'ls' block is the old
  schema; per-polish cap now lives at polish.time_limit_s ...`). The split runs
  before the unknown-top-level warning loop, so these raise with the precise
  message rather than being warned-and-ignored.

Only `time_limit_s` is special-cased this way; `polish.noise` (default `0.10`) and
`polish.hard_safe` (default `True`) keep ordinary defaults, and `budget.max_gens`
defaults to `100`.

## Test design

What each assertion in `test_config.py` catches if the code were wrong:

- **`test_defaults_apply_when_yaml_and_cli_absent`** — the defaults layer. With an
  empty `ea:`, `const` defaults must pass through **uncoerced** (`elitism is True`,
  `pmutate == 0.02`), and the derived defaults must actually resolve against
  features (`pop_size == 35` = round(3.5·√100) clamped; `polish_flips == 2000` =
  round(10·100)=1000 clamped **up** to `lo`). Catches a missing defaults layer, a
  wrong default spec, or a resolver that ignores features.
- **`test_yaml_beats_rule_default`** — YAML overriding a default. `pop_size` set to
  `{const,50}` must win over the `sqrt_vars` default, and `param_rules["pop_size"]`
  must be exactly `{"rule":"const","value":50}` — proving whole-spec replacement,
  not a coefficient merge that leaves `sqrt_vars` residue.
- **`test_cli_beats_yaml_and_default`** — the all-three precedence. default(35) <
  YAML(50) < `-D`(77): resolves to 77. Catches any layer applied in the wrong order.
- **`test_cli_override_recorded_with_provenance`** — `param_rules["pop_size"]`
  is exactly `{"rule":"cli_override","value":77}` (rule bypassed **and** value
  retained) **and** `CLI_OVERRIDE_RULE not in RULES`. Catches a `-D` that loses
  provenance, and catches anyone registering `cli_override` as a real rule.
- **`test_cli_override_on_a_derived_param_bypasses_the_rule`** — a `-D` on a
  `sqrt_vars`-defaulted param must bypass the rule entirely (value 50, spec
  `cli_override`), not feed 50 into the rule.
- **`test_resolved_and_param_rules_have_matching_keys`** — the §8/STEP_04
  invariant under a mix of YAML override + `-D`: `set(resolved) ==
  set(param_rules) == set(DEFAULT_EA_PARAMS)`. Catches a key dropped on the
  override branch or an extra key on one side.
- **`test_parse_override_json_literals_and_string_fallback`** — `-D` value typing:
  `50`→int, `false`→bool, `0.02`→float, `random`→raw string fallback, and a token
  with no `=` raises. Catches a parser that stringifies numbers or crashes on
  bare words.
- **`test_time_limit_split_both_present_preserved`** — both roles set to distinct
  values must stay distinct (`budget.time_limit_s == 180.0`,
  `polish["time_limit_s"] == 0.1`). Catches a split that collapses the two.
- **`test_polish_time_limit_required_explicit`** / **`..._budget_..._required_...`**
  — omitting either role raises `ValueError` matching the key name + `explicit`.
  Catches a silent default sneaking back in for either cap.
- **`test_legacy_top_level_time_limit_rejected`** / **`test_legacy_ls_block_rejected`**
  — the old `time_limit_s` (top-level scalar) and `ls:` shapes raise with the
  migrate message. Catches a loader that would silently reconstruct both-at-once.
- **`test_unknown_ea_key_in_yaml_rejected`** — a YAML `ea` typo (`tourament_k`)
  raises, and the message **lists the known keys** (`"pop_size" in str(exc)`).
  Catches a silent-accept of a typo'd param.
- **`test_unknown_ea_key_via_cli_rejected`** — the same typo via `-D` hits the same
  rejection. Catches the escape hatch bypassing the schema check.
- **`test_coefficient_level_override_rejected`** — `-D ea.pop_size.a=4.0` raises
  `coefficient-level`. Catches a `-D` that silently deep-merges into a rule's coeffs.
- **`test_unknown_top_level_block_warns_not_rejected`** — an unknown top-level
  block (`noise_adapt`) warns (`pytest.warns`) but resolution still succeeds.
  Catches a strict top-level reject that would break loader reuse.
- **`test_load_yaml_roundtrip`** — end-to-end through `load_yaml` on a written
  temp file: `solver`/`seed`/`pop_size`/`provider` come back correct. Catches a
  YAML load path that diverges from the dict path.

## Test output

Fails-before (`config.py` hidden):
```
$ mv maxsat_new/config.py{,.hidden}
$ python -m pytest maxsat_new/tests/test_config.py -q
maxsat_new/tests/test_config.py:24: in <module>
    from maxsat_new import config as cfgmod
E   ImportError: cannot import name 'config' from 'maxsat_new' (/home/mashe/maxsat-lab_new/maxsat-lab/maxsat_new/__init__.py)
=========================== short test summary info ============================
ERROR maxsat_new/tests/test_config.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.09s
```

After (module restored; test file alone, then full suite — all prior tests still pass):
```
$ mv maxsat_new/config.py{.hidden,}
$ python -m pytest maxsat_new/tests/test_config.py -q
.................                                                        [100%]
17 passed in 0.03s
$ python -m pytest maxsat_new/tests -q
...............................                                          [100%]
31 passed in 0.04s
```

## Decisions / ambiguities resolved

1. **§4 vs §9.4 conflict on `polish.time_limit_s` (resolved by ruling 1).** §4's
   derived-vs-fixed table calls `polish.time_limit_s` a fixed `const 0.05`, but
   §9.4 wants both time roles explicit so "sets only one" can be surfaced. Landed:
   config.py requires it explicit and defaults neither time role; §4 left unedited.
2. **`max_gens` location (§4 table vs §4 example / §8).** The §4 table lists
   `ea.max_gens` as a `const`, but the §4 example YAML and the §8 record both place
   it under `budget:`. Landed: treated as `budget.max_gens` (default 100), read
   directly, **not** routed through `resolve_params` — so it is absent from
   `resolved_params`/`param_rules`, matching the §8 record shape.
3. **Which block resolves through `resolve_params`.** Only the `ea:` block (STEP_04
   audit item 6). `budget`/`polish`/`provider` are read directly, so §8's
   `resolved_params` == the `ea` param set exactly. This is why the §4 example
   shows `polish:` as bare scalars rather than rule dicts.
4. **Unknown `ea`/owned-block keys (resolved by ruling 2).** Reject with knowns
   listed, in YAML and via `-D`; unknown top-level blocks ignored-with-warning.

## Deviations from PORT_NOTES §4

The resolution order, the `cli_override` provenance representation, the DICT-ONLY
hand-off, and the two output dicts with matching key sets are all as §4 / STEP_04
specify. Additions beyond §4's prose:

- **Coefficient-level `-D` explicitly rejected** (e.g. `ea.pop_size.a=4.0`), flagged
  as a later addition per the step-5 contract — a whole-value-only `-D` this step.
- **Error surfaces** §4 mandates in intent but not in code: the required-explicit
  time-limit messages, the legacy top-level/`ls` rejections, the unknown-key
  rejection, and the bare-scalar-`ea`-value `TypeError`. These realise §4's "a typo
  is not a silent experiment" goal rather than diverge from it.

Otherwise: none.

## Flagged items (noticed while writing these notes; NOT changed)

- **`solver` defaults silently to `"memetic_ea"`** when neither the `--solver`
  kwarg nor YAML `solver:` is present. Convenient for the step-7 core but arguably
  the runner (step 9) should require an explicit solver so a mistyped/absent
  `solver:` is not silently the EA. Flag for the step-9 CLI decision.
- **`seed` defaults to `1`** (matches `run_ea.py --seed` default and §7) — noted
  for consistency, not a concern.
- **Top-level `-D` typos warn but do not raise** (e.g. `-D sedd=7` lands as an
  unknown top-level key → warning, ignored). This follows ruling 2's "don't
  hard-reject top-level," but a top-level `-D` typo is only a warning, not an
  error. Acceptable given the ruling; flagged so it's a conscious choice.

## Purity note (honest about I/O)

Unlike `sizing.py`, config.py is **not** pure end-to-end: `load_yaml` performs real
file I/O (`open` + `yaml.safe_load`), and `resolve_config` calls `warnings.warn`
(a process-global side effect) on unknown top-level blocks. However:

- **The resolution core is pure given its inputs.** `resolve_config(raw, features,
  ...)` takes an already-loaded dict and an `InstanceFeatures`; it touches no RNG,
  no clock, no network, and does not mutate `raw` (it works on a `deepcopy`). Given
  the same `raw`, `cli_overrides`, and `features`, it returns the same
  `ResolvedConfig` — the reproducibility that matters for the record (§8) holds at
  this layer. All 15 resolution-behavior tests drive `resolve_config` directly with
  in-memory dicts, no file needed.
- **I/O is confined to `load_yaml`** (and `load_and_resolve`, which is just
  `load_yaml` + `extract` + `resolve_config`). The one test that exercises the file
  path (`test_load_yaml_roundtrip`) uses a pytest `tmp_path`.
