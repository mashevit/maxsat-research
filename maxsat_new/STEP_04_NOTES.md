# Step 04 notes — features.py + sizing.py

Implements Step 4 of PORT_NOTES.md §10 (row 4: "config resolution"). This step is
**new code, not a port**: §3's port map has no row for `features.py` or
`sizing.py`. The spec is PORT_NOTES §4; §8 pins the record fields the resolver
feeds.

## Files created
- `maxsat_new/features.py` — `InstanceFeatures` frozen dataclass (§4's seven
  fields) + `extract(wcnf) -> InstanceFeatures` (one pass).
- `maxsat_new/sizing.py` — `RULES` registry + `@rule(name)` decorator + `_clamp`
  + the four §4 rules (`const`, `sqrt_vars`, `linear_vars`, `linear_clauses`) +
  `resolve_params`.
- `maxsat_new/tests/test_sizing.py` — one test file, §10 row 4.

## InstanceFeatures

Seven fields, exactly §4's. `n_vars` is read from the stored `WCNF.n_vars` field;
the rest are accumulated in a single loop over `wcnf.clauses` (the ported `WCNF`
stores no `n_clauses`/`n_hard`/`n_soft` — Phase-1 audit item 1).

| Field | Formula | Degenerate fallback |
|---|---|---|
| `n_vars` | `wcnf.n_vars` (stored field) | — |
| `n_clauses` | `len(clauses)` (counted in loop) | — |
| `n_hard` | count of `cl.is_hard` | — |
| `n_soft` | `n_clauses - n_hard` | — |
| `hard_frac` | `n_hard / n_clauses` | `0.0` when `n_clauses == 0` |
| `hard_soft_ratio` | `n_hard / n_soft` | `float(n_hard)` when `n_soft == 0` |
| `total_soft_weight` | `sum(cl.weight for soft cl)` | `0` (empty sum) when no soft clauses |

No extra fields added. `src/sat/metadata.py:compute_metadata` computes a superset
(clause-length histograms, variable degrees, polarity counts); none of those are
adopted here because no §4 rule keys on them. If a future rule needs one, it is a
§4-to-adopt suggestion (add the field to `InstanceFeatures` + `extract`), not a
silent addition.

## Rule registry

`RULES: dict[str, Rule]`, enumerable via `sorted(RULES)`. Bodies verbatim from §4
(round-then-clamp; `c.get("b", 0)` default).

| Rule | Coeff keys | Required / defaulted | Clamping | What it is for |
|---|---|---|---|---|
| `const` | `value` | `value` required | none | Fixed params (`tournament_k`, `pmutate`, `elitism`, …); value returned **uncoerced**. |
| `sqrt_vars` | `a`, `lo`, `hi` | all required | `_clamp(round(a·√n_vars), lo, hi)` | Pop-scale knob (`pop_size`); scales with search-space size (§4 default rule for `pop_size`). |
| `linear_vars` | `a`, `b`, `lo`, `hi` | `a`,`lo`,`hi` required; `b` defaults `0` | `_clamp(round(a·n_vars + b), lo, hi)` | Cost that scales with #vars (`polish_flips`, §4 default). |
| `linear_clauses` | `a`, `b`, `lo`, `hi` | `a`,`lo`,`hi` required; `b` defaults `0` | `_clamp(round(a·n_clauses + b), lo, hi)` | Placeholder for a param that should scale with clause count (§4). |

Required vs defaulted follows §4's literal syntax: subscript `c["k"]` ⇒ required;
`c.get("b", 0)` ⇒ optional with default `0`. Adding a rule is a single decorated
function — no other edit anywhere (verified: the four rules and `resolve_params`
reference the registry only through `RULES`/`@rule`).

## resolve_params contract

- **Input:** `resolve_params(param_specs, features)`.
  - `param_specs`: the merged `ea:` block — `{param_name: {"rule": NAME, <coeffs>}}`
    (Phase-1 audit item 6). Not the whole config.
  - `features`: an `InstanceFeatures`.
- **Output:** two dicts with **identical key sets** (audit item 6; §8):
  - `resolved`   — `{param_name: concrete value}`
  - `param_rules` — `{param_name: rule spec}` (copied, not aliased to input).
  The key-set invariant matches §8's `resolved_params` / `param_rules` fields,
  which carry the same key set in the record example.
- **DICT-ONLY (approved ruling 1).** Every value in `param_specs` must be a
  `{"rule": ...}` spec — including fixed params via `{"rule": "const", ...}`. A
  bare scalar raises `TypeError` naming the param and stating a rule spec is
  required.
- **`cli_override` representation (contract config.py/step 5 must satisfy).**
  `sizing.py` has no concept of a CLI and a bare scalar carries no provenance —
  it could be a CLI override or a hand-edited YAML value, indistinguishable here.
  So **config.py owns** constructing `param_rules["pop_size"] = {"rule":
  "cli_override", "value": X}` and hands `resolve_params` a uniform dict-valued
  mapping. `cli_override` is a provenance label, **not** a rule registered in
  this module. This keeps §4's "every param resolves through a rule" invariant
  true at the sizing layer with zero special cases. (Pinned here so step 5 has
  it in writing.)

## Decisions §4 left open

1. **Rounding mode (ruling 2).** Implemented: bare `round()` exactly as §4
   writes it — Python's **banker's rounding** (`round(0.5) == 0`,
   `round(2.5) == 2`; ties round to even). Alternative: half-up
   (`math.floor(x + 0.5)`). Why banker's won: §4's literal text is `round(...)`
   and Phase-2 mandates rule bodies exactly as §4 writes them; it is
   deterministic, which is all the reproducibility claim (§4/§8) needs. It
   differs from half-up **only on exact `.5` values**. **Candidate for
   PORT_NOTES §4 to adopt** so the choice is stated rather than incidental.
2. **Round-then-clamp order.** Implemented as §4 writes it:
   `_clamp(round(x), lo, hi)` — round first, clamp second. Alternative
   (clamp-then-round) rejected as a deviation from §4's literal nesting.
3. **`lo`/`hi` optionality.** Implemented: **required** (subscript access), per
   §4's `c["lo"]`/`c["hi"]`. `b` is the only optional coeff (`c.get("b", 0)`).
   Alternative (defaulting `lo`/`hi`) rejected: §4 gives them no default and an
   unclamped size is exactly the runaway a sizing rule exists to prevent.
4. **Bare-scalar handling (ruling 1).** Implemented: **reject** with a clear
   `TypeError`. Alternative: `resolve_params` wraps a bare scalar as
   `cli_override` itself. Why reject won: provenance lives with config.py (see
   contract above); wrapping here would guess an origin sizing.py cannot know.
5. **Unknown rule (ruling 3).** Implemented: `ValueError` naming the bad rule and
   listing `sorted(RULES)`. Alternative: silently default. Rejected — §4 chose
   named functions over safe-eval precisely so a typo is not a silent experiment.
6. **Missing required coefficient (ruling 3).** Implemented: the rule body keeps
   §4's literal `c["a"]`; `resolve_params` catches the `KeyError` and **re-raises
   with a clear message** naming the rule and the missing key (not a bare
   `KeyError`). Alternative: let the bare `KeyError('a')` escape. Rejected — same
   "no silent/opaque failure" rationale.
7. **`const` non-coercion.** Implemented: `const` returns `c["value"]` uncoerced,
   so `elitism` stays `True` (bool, not `1`) and `pmutate` stays `0.02` (float,
   not `0`). Alternative: int-coerce. Rejected — it would corrupt the two
   non-int fixed params §4 routes through `const`.

Candidates flagged for PORT_NOTES §4 to adopt: **#1 (rounding mode)** explicitly;
#3–#6 are already implied by §4's syntax/intent and are documented here for
completeness.

## Deviations from PORT_NOTES §4

Rule bodies, the registry shape, the round-then-clamp order, `c.get("b", 0)`, and
the two-parallel-dicts contract are all verbatim §4. The only additions are the
**error surfaces** §4 mandates in prose but does not spell out in code (dict-only
guard, unknown-rule `ValueError`, missing-coeff `KeyError` re-wrap). These realise
§4's stated "a typo is not a silent experiment" goal rather than diverge from it.
Otherwise: **None.**

## Purity note

No rule touches RNG, clock, I/O, or global state. Each rule is a pure function of
`(features, coeffs)`; `_clamp` and `round` are pure; `resolve_params` only reads
its two arguments and the `RULES` registry (which is populated once at import and
never mutated during resolution). `InstanceFeatures` is a frozen dataclass, so a
rule cannot mutate the features it is handed. Therefore resolution is fully
reproducible from the record's `param_rules` alone (the §4 reproducibility
claim, §8): given the same rule specs and the same instance features, the
resolved values are bit-identical on every machine and every run. The purity test
asserts this for all four rules.

## Test design

What each assertion catches if the code were wrong:

- **`test_sqrt_vars_clamps_low_high_and_leaves_midrange`** — the three-point
  clamp. `n_vars=1` → raw `round(√1)=1 < lo` must clamp **up** to `10`;
  `n_vars=40000` → raw `200 > hi` must clamp **down** to `100`; `n_vars=2500` →
  raw `50` is inside `[10,100]` and must pass through **unchanged**. The mid point
  is the load-bearing one: it equals neither bound, so a broken clamp that always
  returned `lo` (or always `hi`, or dropped a bound) passes the two edge
  assertions but **fails** the mid. Also catches a clamp with `min`/`max`
  swapped.
- **`test_resolve_params_emits_value_and_rule_with_matching_keys`** — catches a
  resolver that returns only values (no provenance), mismatched key sets between
  the two dicts, a wrong resolved value (`pop_size` = 35 pins the whole
  round+clamp path), or aliasing the input spec into `param_rules` (the
  `is not` check).
- **`test_rules_enumerates_exactly_four`** — catches a rule that failed to
  register, an unintended extra rule, or a registry that isn't enumerable via
  `sorted`.
- **`test_unknown_rule_raises_and_lists_known_rules`** — catches a silent default
  on a typo'd rule name; asserts the message is actionable (names the bad rule
  *and* lists the known set).
- **`test_missing_required_coefficient_raises_naming_rule_and_key`** — catches a
  bare/opaque `KeyError` escaping; asserts the message names the rule and the key.
- **`test_bare_scalar_raises`** — pins the dict-only contract (ruling 1); catches
  a resolver that silently accepts a provenance-less scalar.
- **`test_const_does_not_coerce_bool_or_float`** — catches int-coercion in
  `const`; `is True` + `type is bool` catches `1`, `isinstance float` catches a
  truncated `0`.
- **`test_extract_on_mini_wcnf_known_values`** — catches a miscount of
  hard/soft/clauses, a wrong soft-weight sum, or a ratio computed the wrong way,
  against the committed instance (5/8/3/5, soft weights 3+5+2+4+1=15).
- **`test_extract_no_soft_clauses_ratio_falls_back_to_n_hard`** and
  **`test_extract_empty_instance_hard_frac_is_zero`** — catch a `ZeroDivisionError`
  or a wrong fallback in the two §4 degenerate branches.
- **`test_rules_are_pure`** — catches any rule that isn't a pure function of its
  inputs (hidden state / RNG / mutation).

## Test output

Fails-before (both new modules hidden):
```
$ mv maxsat_new/features.py{,.hidden}; mv maxsat_new/sizing.py{,.hidden}
$ python -m pytest maxsat_new/tests/test_sizing.py -q
==================================== ERRORS ====================================
_______________ ERROR collecting maxsat_new/tests/test_sizing.py _______________
ImportError while importing test module '/home/mashe/maxsat-lab_new/maxsat-lab/maxsat_new/tests/test_sizing.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
maxsat_new/tests/test_sizing.py:24: in <module>
    from maxsat_new.features import InstanceFeatures, extract
E   ModuleNotFoundError: No module named 'maxsat_new.features'
=========================== short test summary info ============================
ERROR maxsat_new/tests/test_sizing.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.08s
```

After (modules restored, full suite — all prior tests still pass):
```
$ python -m pytest maxsat_new/tests -q
..............                                                           [100%]
14 passed in 0.03s
```

## Phase-1 audit findings vs the plan

- **Item 1 — `cnf.py` surface (CONFIRMED).** `Clause` has `weight`/`lits`/`is_hard`
  (`cnf.py:21-23`); `WCNF` stores `n_vars` but **no** `n_clauses`/`n_hard`/`n_soft`.
  All seven §4 features are computable in one pass; `extract` does so.
- **Item 2 — prior art (CONFIRMED, no dependency taken).** `src/` has feature and
  sizing prior art, both on non-EA paths, neither imported (PORT_NOTES §2):
  - `src/sat/metadata.py:compute_metadata` (`:121`) extracts a **superset** of §4's
    fields (`n_soft = n_clauses - n_hard` at `:158`, `sum_soft_w` at `:172`).
    `InstanceFeatures` is a lean subset — no contradiction with §4.
  - `src/bench/harness.py:normalize_cfg` (`:50-57`) computes
    `restart_k = max(k_min, min(k_max, k_per*n_vars))` — a clamp-linear-in-`n_vars`
    rule structurally identical to §4's `linear_vars` (`a=k_per, b=0, lo=k_min,
    hi=k_max`), but with **no rounding** (pure int arithmetic) and no `b` offset.
    §4 legitimately invents a parallel, named, enumerable mechanism for the EA
    path; the math agrees.
- **Item 3 — `size_rule` YAML shape (CONTRADICTS on syntax, AGREES on math).** The
  zoo block (`configs/default.yaml:19-22`, `2/3/4.yaml`, all identical) is
  `{k_child_min, k_child_max, k_per_var}` with **no `rule:` selector** — a single
  implicit clamp-linear rule. §4's `{rule: NAME, coeffs...}` makes the rule name
  explicit and renames coeffs to `a`/`b`/`lo`/`hi`. So §4's shape is a
  *generalization*: it diverges on key layout (adds a selector, different coeff
  names) but the zoo block **is** `linear_vars` with `a=k_per_var, b=0,
  lo=k_child_min, hi=k_child_max`. Recorded for a future consolidation.
- **Item 4 — degenerate fallbacks (CONFIRMED).** §4's `0.0` (when `n_clauses==0`)
  and `n_hard` (when `n_soft==0`) are implemented and tested. On `mini.wcnf`
  neither branch fires (`hard_frac=3/8`, `hard_soft_ratio=3/5`).
- **Item 5 — `cli_override` layer (ambiguity RESOLVED by ruling 1).** §4 leans
  toward config.py owning the conversion (it lists CLI override under "Resolution
  order", §2/§10-step-5's remit). Ruling 1 confirmed **dict-only**: config.py
  constructs `{"rule": "cli_override", "value": X}`; `resolve_params` accepts only
  rule dicts and rejects bare scalars. Pinned in the contract section above.
- **Item 6 — `resolve_params` I/O (CONFIRMED against §8).** Input is the `ea:`
  block `{name: rule_spec}`; output is two dicts with matching key sets, matching
  §8's `resolved_params`/`param_rules` (same key set in the record example).
- **Item 7 — determinism/typing (CONFIRMED).** Banker's `round()` kept (ruling 2);
  round-then-clamp order kept; `const` uncoerced; `lo`/`hi` required, `b`
  defaulted; unknown-rule and missing-coeff both raise actionable errors
  (ruling 3). No contradiction with §4; the KeyError re-wrap is an added surface,
  not a behavior change (see Deviations).
