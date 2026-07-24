# Step 03 notes — population.py + operators.py port

Implements Step 3 of PORT_NOTES.md §10 (row 3: "EA operators available").

## Files created
- `maxsat_new/population.py` — `Individual`, `jw_priors`, `hash_assign`,
  `evaluate_assignment`, `clause_satisfied`, `init_hard_satisfied`,
  `build_hard_occurs`, `Population`. Module docstring records the port source.
- `maxsat_new/operators.py` — `tournament`, `_soft_proxy_scores`,
  `clause_aware_crossover1`, `mutate1`, `short_polish` (converted signature).
- `maxsat_new/tests/test_operators.py` — one test: seeded operator sequence is
  deterministic and non-trivial.

## Ported vs dropped (from src/evo/population.py @ 1e3eaaf)

Whole-module port per PORT_NOTES §3 ("this file is lean; drop nothing"). All
symbols ported verbatim in behavior, type annotations added to public signatures:

| Symbol | src lines |
|---|---|
| `Individual` (+ `.copy`) | 11–30 |
| `jw_priors` | 33–58 |
| `hash_assign` | 61–64 |
| `evaluate_assignment` | 67–87 |
| `clause_satisfied` | 90–101 |
| `init_hard_satisfied` | 104–105 |
| `build_hard_occurs` | 109–118 |
| `Population` (`__init__` 126–131, `_new_assign_from_priors` 133–138, `init_seeds` 144–152, `evaluate` 154–165, `best` 167–169) | 122–169 |

Dropped: **nothing** from population.py. (`Individual.copy` keeps `meta=self.meta`
— a shared reference, not a copy — ported verbatim; not tagged, it is existing
behavior not a suspected bug.) The src `# from src.sat.cnf import WCNF` comment
(src:7) is reworded to point at `maxsat_new.cnf.WCNF`; `wcnf` is duck-typed and
never imported, so no src import exists.

## Ported vs dropped (from src/evo/operators.py @ 1e3eaaf)

Four EA entry points + the one internal helper reached from them:

| Symbol | src lines | Status |
|---|---|---|
| `tournament` | 15–18 | **ported** (entry point) |
| `_soft_proxy_scores` | 21–39 | **ported** (reached by `clause_aware_crossover1`:162) |
| `clause_aware_crossover1` (nested `eval_candidate` 190–230, `commit_assignment` 232–262) | 139–307 | **ported** (entry point) |
| `mutate1` | 320–368 | **ported** (entry point) |
| `short_polish` | 385–427 | **ported** (entry point; signature converted, see Deviations) |
| `frozen_hard_unit_vars` | 6–12 | **dropped** (ruling 1; see Deviations) |
| `clause_aware_crossover` (v0) | 42–74 | **dropped** — superseded by `crossover1`; only active caller is dead `memetic0.py:49`, never the live path. |
| `_repair_hard_constraints` | 77–133 | **dropped** — only caller is the dropped v0 crossover (:73). |
| `mutate` (v0) | 310–316 | **dropped** — only active caller is dead `memetic0.py:50`; commented out at memetic.py:92. |
| `short_polish1` (stub) | 373–381 | **dropped** — zero call sites anywhere. |

Reached helper §3 omitted: `clause_satisfied` (population.py:90), used by `mutate1`
at src:353 — ported as part of the whole-module population port.

Unused import noted: src operators.py:4 imports `evaluate_assignment` but never
uses it in operators.py. Kept the import verbatim (fidelity; harmless, no behavior
or RNG effect). Debug/`#print` cruft: none present in the ported functions.

## Deviations from PORT_NOTES §3

1. **`frozen_hard_unit_vars` dropped (ruling 1).** §3's operators.py row lists
   `frozen_hard_unit_vars` as ported, but Phase-1 proved it unreachable from the
   four EA entry points (only active caller is the dropped v0
   `clause_aware_crossover`:50; memetic.py:59 has it commented out as
   `#not needed`). §3 was written from a read, not a call-graph trace. Dropped per
   the Phase-2 reachability rule. **If step 7 needs it, it is re-added there with
   its own test.**

2. **`build_hard_occurs` attribution (ruling 2).** §3's port map lists
   `build_hard_occurs` in the *operators.py* row, but it is defined in
   *population.py* (src:109) and is ported as part of the whole-module population
   port. Attribution-only; no port change.

3. **`short_polish` signature converted from `ls_cfg: dict` to explicit keyword
   parameters** (PORT_NOTES §4 resolved-params surface). Every default is
   byte-identical to the src `ls_cfg.get(...)` default, and each value is now
   passed explicitly at the `walksat_polish` call site. src-lookup → parameter
   mapping:

   | src lookup (operators.py) | src line | → `walksat_polish` arg | new param | default | provenance |
   |---|---|---|---|---|---|
   | `ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips", None))` | 402 | `max_flips` | `polish_flips` | `None` | §9.2: `ls_polish_flips` shadows `max_flips`; shadowed fallback key **dropped**, innermost default `None` kept |
   | `ls_cfg.get("time_limit_s", ls_cfg.get("time_limit_s", 0.05))` | 403 | `time_limit_s` | `time_limit_s` | `0.05` | §9.3: same key looked up twice; **written once**, same 0.05 default |
   | `ls_cfg.get("noise", 0.10)` | 404 | `noise` | `noise` | `0.10` | direct |
   | `ls_cfg.get("hard_safe", True)` | 405 | `hard_safe` | `hard_safe` | `True` | direct |
   | `ls_cfg.get("smooth_every", 0)` | 406 | `smooth_every` | `smooth_every` | `0` | ruling 3: explicit param, not fall-through |
   | `ls_cfg.get("rho", 0.5)` | 407 | `rho` | `rho` | `0.5` | ruling 3: explicit param, not fall-through |

   Why behavior-preserving: each keyword default equals the exact src `.get`
   default, and the value is passed explicitly to `walksat_polish` on every call,
   so the argument seen by `walksat_polish` is identical to what the src dict path
   produced. **`smooth_every`/`rho` are stated explicitly** (ruling 3): relying on
   two modules sharing a default is implicit coupling that breaks silently if
   `walksat.py`'s defaults are ever edited; stating the value at the call site
   preserves behavior and removes that dependency. `short_polish` performs no RNG
   draw itself (it forwards `rng_seed`), so the conversion cannot touch the RNG
   stream.

## Replicated-bug comments added

- **§9.1 — `mutate1`'s `hard_satisfied`** (operators.py docstring): inline note that
  `hard_satisfied` is caller-supplied and mutated in place, never recomputed; the
  live caller (memetic, step 7) passes a stale, shared list (a leaked init-eval
  loop variable's `ind.hard_satisfied`). Replicated bit-for-bit, not fixed. The
  test's `_run_sequence` passes exactly that leaked `ind.hard_satisfied`.
- **§9.2 — `flip_budget`/`max_flips` shadowing** (`short_polish`, at the
  `max_flips=polish_flips` call-site comment): the shadowed `max_flips` fallback
  key is dropped; behavior unchanged.
- **§9.3 — duplicate `time_limit_s` lookup** (`short_polish`, at the `time_limit_s`
  call-site comment): src looked the same key up twice with the same 0.05 default;
  written once. Provably identical, same precedent as STEP_01's `pass` removal.

No new `SUSPECTED (not in §9)` items found in these two files: every behavior maps
to an existing §9 entry or is intended logic.

## RNG-order note

Full draw order for each ported function (all draws from the passed-in
`random.Random`, in exact source order; nothing reordered, hoisted, or
short-circuited):

- **`Population.init_seeds`** → `_new_assign_from_priors`: for each of `size`
  members, `self.rng.random()` once per variable `v` in `1..n_vars`
  (population.py:137). `jw_priors` and `init_hard_satisfied` draw nothing.
- **`tournament`**: `rng.sample(pop, k)` — one draw (operators.py `tournament`).
- **`clause_aware_crossover1`**: `rng.choice([a, b])` **only** (src:303), in the
  rare tie-of-tie fall-through (`st==sf` and the fitter-parent bit lands outside
  `{a,b}` with `a != b`); at most once per variable. `_soft_proxy_scores`,
  `eval_candidate`, `commit_assignment` draw nothing.
- **`mutate1`**: `rng.random()` once per variable `v` in `1..n` (the
  `if rng.random() >= pmutate: continue` guard), exactly `n` draws, always drawn
  before the `continue`.
- **`short_polish`**: no draw from a passed-in `Random`; it forwards the
  caller-supplied `rng_seed` (int) into `walksat_polish`, which builds its own
  `random.Random(rng_seed)`. The `rng.randrange(1<<30)` that derives that seed
  lives in the caller (memetic, step 7), not here.

The `ls_cfg` → keyword-parameter conversion of `short_polish` changes no RNG draw.

## Test design

- **Seed / params:** `SEED=0`, `POP_SIZE=6`, `TOURNAMENT_K=2`, `PMUTATE=0.1`,
  chosen (by scan) as the smallest config on `mini.wcnf` where the child differs
  from both parents while staying reproducible.
- **What binds:** nothing budget-based. §10 row 3's sequence is
  `tournament → clause_aware_crossover1 → mutate1`; `short_polish` is **not**
  exercised, so there is no flip/time budget in the test. The only determinism
  source is the seed, per PORT_NOTES §11 Q1.
- **Why deterministic:** each run rebuilds a fresh `random.Random(SEED)` and walks
  the identical code path; every RNG draw (init seeding, two tournaments,
  crossover's conditional `rng.choice`, mutate's per-var `rng.random`) is
  consumed in the same order, so both runs yield the identical child.
- **Non-triviality assertion:** `child != p1.assign01` and `child != p2.assign01`.
  It holds on `mini.wcnf` at this seed (child `[F,T,F,F,T,T]`,
  p1 `[F,T,F,F,F,F]`, p2 `[F,T,F,T,F,T]`), so a pipeline that silently returned a
  parent or produced a no-op mutation would fail.
- §9.1 is exercised authentically: `mutate1` receives the leaked `ind.hard_satisfied`.

## Test output

Fails-before (both new modules hidden):
```
$ mv maxsat_new/operators.py{,.hidden}; mv maxsat_new/population.py{,.hidden}
$ python -m pytest maxsat_new/tests/test_operators.py -q
ImportError while importing test module '.../maxsat_new/tests/test_operators.py'.
...
maxsat_new/tests/test_operators.py:23: in <module>
    from maxsat_new.population import Population, build_hard_occurs
E   ModuleNotFoundError: No module named 'maxsat_new.population'
=========================== short test summary info ============================
ERROR maxsat_new/tests/test_operators.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.07s
```

After (modules restored, full suite):
```
$ python -m pytest maxsat_new/tests -q
...                                                                      [100%]
3 passed in 0.02s
```

## Phase-1 audit findings vs the plan

- **§3 helper list — `_soft_proxy_scores`:** CONFIRMED reachable (crossover1:162).
- **§3 helper list — `frozen_hard_unit_vars`:** CONTRADICTED. Unreachable from the
  four entry points; only active caller is the dropped v0 crossover; memetic.py:59
  use is commented `#not needed`. Resolved by ruling 1 (drop). Recorded in
  Deviations §1.
- **§3 helper list — `build_hard_occurs`:** CONTRADICTED (mis-attributed to
  operators.py; it lives in population.py) and unreachable from the four entries
  (mutate1 *receives* `hard_occurs`, does not build it). Resolved by ruling 2
  (port via population.py; no port change). Recorded in Deviations §2.
- **§3 helper list omission — `clause_satisfied`:** reached by `mutate1`:353 but
  not named by §3; ported via population.py.
- **§3 drops (`clause_aware_crossover`, `mutate`, `short_polish1`,
  `_repair_hard_constraints`):** all CONFIRMED unreachable from the four live entry
  points (v0 crossover/mutate only from dead `memetic0.py`; `short_polish1` no
  callers; `_repair_hard_constraints` only from the dropped v0 crossover).
- **§9.1 / §9.2 / §9.3:** CONFIRMED present exactly as described (mutate1 stale
  caller-supplied `hard_satisfied`; `short_polish` `max_flips` shadowing at
  src:402; duplicate `time_limit_s` at src:403). All replicated, not fixed.
- **§2 population.py symbol list** (`Individual, Population, jw_priors,
  evaluate_assignment`): correct but abbreviated — also defines `hash_assign`,
  `clause_satisfied`, `init_hard_satisfied`, `build_hard_occurs`. No port change;
  §3's whole-module port covers them.
- **Additional (ruling 3):** `smooth_every`/`rho` made explicit `short_polish`
  parameters rather than falling through to `walksat_polish` defaults.
