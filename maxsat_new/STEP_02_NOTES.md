# Step 02 notes — state.py + walksat.py port

Implements Step 2 of PORT_NOTES.md §10 (polish available).

## Files created
- `maxsat_new/state.py` — `ClauseInfo` + `SatState` (only the methods reachable
  from `walksat_polish`). Module docstring records the port source.
- `maxsat_new/walksat.py` — `_extract_clauses` + `walksat_polish` **only**.
- `maxsat_new/tests/test_walksat.py` — one test: determinism under a flip cap.

## Ported vs dropped (from src/sat/state.py @ 1e3eaaf)

Ported `SatState` methods (reachable from `walksat_polish`): `__post_init__`,
`_lit_val`, `_compute_clause_true_count`, `_count_hard_violations`,
`_soft_objective`, `flip_var_effect` (src:90), `apply_flip`, `flip_var_hard_delta`
(src:252), `unsat_soft_indices`, `unsat_hard_ids`, `snapshot_best_if_better`
(src:321), `smooth`. All `SatState` **fields** ported verbatim (kept `restarts`,
`tabu_until`, `iter_idx` even though only `iter_idx` is touched on the polish path,
to preserve `__post_init__` byte-for-byte). `ClauseInfo` ported verbatim.

Dropped **`'''...'''` dead method bodies** (PORT_NOTES §3), verified at src lines:
- `flip_var_effect` duplicate (src:139-180)
- `hard_safe` duplicate (src:212-216)
- `flip_var_hard_delta` duplicate (src:219-250)
- `snapshot_best_if_better` duplicate (src:310-319)

Dropped **`restart_partial_from_best`** (src:351) — never on the polish path
(PORT_NOTES §3; its only call site, `run_satlike:492`, is commented out).

Dropped **real methods unreachable from `walksat_polish`** (Phase-1 audit; not in
§3's explicit list but licensed by the task's "drop any method unreachable from
walksat_polish"):
- `clause_indices_for_var` (src:75)
- `var_is_tabu` (src:78) — tabu machinery, satlike only
- `set_tabu` (src:81) — tabu machinery, satlike only
- `hard_safe` **method** (src:205) — `walksat_polish` uses the bool *parameter*
  `hard_safe`, never `state.hard_safe(v)`; that call site is in `run_satlike`
- `vars_adjacent_to` (src:304)
- `all_unsat_indices` (src:335)
- `bump_clause` (src:338) — dynamic-weight machinery, satlike only

## Ported vs dropped (from src/sat/walksat.py @ 1e3eaaf)

Ported: `walksat_polish` (src:529-693) verbatim in behavior + `_extract_clauses`
(src:147-195, the helper it calls). Added type annotations to public signatures.

Dropped (PORT_NOTES §3): the `WalkSAT` class (src:21), `run_satlike` (src:328),
`_derive_hard_fixed_literals` (src:230), `_freeze_hard_units` (src:203), `_cfg`
(src:198; only `run_satlike` reads it), and all debug `print()`. No `print()` is
active inside the two ported functions; the commented-out `#print` cruft in
`_extract_clauses` (src:182,187) and `walksat_polish` (src:684) is not carried over.

## Deviations from PORT_NOTES §3
- **`unsat_soft_indices` deduplicated.** `src/sat/state.py` defines it twice,
  byte-for-byte identically (src:298 and src:332); the second shadows the first.
  Kept a single copy — provably no behavioral difference (same as STEP_01's
  `pass`-removal precedent). Flagged with an inline `NOTE`.
- **Dropped-method list above** extends §3 (which only named the string-literal
  bodies and `restart_partial_from_best`). §3's table does not enumerate the
  satlike/tabu-only methods; the task instructed dropping everything unreachable
  from `walksat_polish`, so they are dropped and listed here.

## Replicated-bug / suspected-behavior comments added
- **`flip_var_hard_delta`** keeps its inner `from collections import Counter,
  defaultdict` with `defaultdict` unused — ported verbatim (not a behavior change,
  not tagged).
- **`walksat.py` — `walksat_polish` `num_flips`**: tagged
  `# SUSPECTED (not in §9)`. The returned `"flips"` field is `num_flips`, which
  counts loop **iterations** (incremented at the top of the loop, before the
  `target == -1` break, and even on iterations that flip no variable), *not*
  applied flips. The budget `while state.flips < max_flips` and the `"total_flips"`
  field both use `state.flips` (actual applied flips). Kept byte-for-byte.
  **For PORT_NOTES §9 to adopt:** "walksat_polish's returned `flips` counts loop
  iterations, not applied flips; `total_flips` is the real applied-flip count."

No behavior matching §9.1-§9.6 appears in `walksat_polish`/`state.py` (those items
concern memetic/operators/cnf), so no §9.x citation was needed here.

## RNG-order note
`walksat_polish` constructs `SatState` **with `assign=` provided**, so
`__post_init__`'s `self.rng.choice(...)` branch does **not** run — no RNG is
consumed at construction. Every subsequent draw (`rng.choice` in
`pick_unsat_clause_index`, `rng.shuffle(cand_vars)`, `rng.random()` for `explore`)
is preserved in exact source order and count. Nothing reordered, hoisted, or
short-circuited.

## Test design (PORT_NOTES §11 Q1)
`walksat_polish`'s signature makes `time_limit_s` unavoidable (default 0.05). The
test passes `time_limit_s=1000.0` (never binds) and `max_flips=200` (always binds),
so the **flip cap is the real budget** and the run is deterministic. The test
asserts `total_flips == max_flips` to prove the flip cap — not the wall clock — is
what stopped the run. Verified empirically: `total_flips == 200`, elapsed ~1 ms.

## Test output
```
$ python -m pytest maxsat_new/tests/test_walksat.py -q   # with modules hidden
E   ModuleNotFoundError: No module named 'maxsat_new.walksat'
1 error in 0.07s

$ python -m pytest maxsat_new/tests -q                    # after
..                                                                       [100%]
2 passed in 0.01s
```
Fails-before holds: the test imports `maxsat_new.walksat`, which did not exist
prior to this step. Note: `pytest` was not present in this environment's venv
(`~/.venvs/maxsat`; the conda env STEP_01 used is gone); reinstalled `pytest 9.1.1`
to run the suite.

## Phase-1 audit findings vs the plan
No contradiction. Confirmed `walksat_polish` does **not** reach `WalkSAT`,
`run_satlike`, `_derive_hard_fixed_literals`, or `_freeze_hard_units`, and does not
reach `restart_partial_from_best`. §3's port map holds; no stop condition triggered.
The four `'''...'''` dead bodies are at src lines 139/212/219/310 as §3 predicted.
