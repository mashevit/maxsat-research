# Target-cost early stop — how it works and how to run it

The memetic EA can now be given a known optimum and stop the moment it reaches
it. This turns `wall_time_s` on successful runs from a constant (the budget) into
a real **time-to-optimum** measurement.

Written 2026-08-05. Companion to
[`docs/TIER2_MEMETIC_PLAN.md`](TIER2_MEMETIC_PLAN.md) (the tier-2 run itself),
[`docs/RC2_STATUS.md`](RC2_STATUS.md) (§4.2, §4.4c — where the oracle labels and
the RC2 caps come from), the completion record in
[`docs/TIER2_TARGET_STOP_REPORT.md`](TIER2_TARGET_STOP_REPORT.md), and
[`cluster_staging_maxsat/DIVERGENCE.md`](../cluster_staging_maxsat/DIVERGENCE.md).

---

## 0. TL;DR

* `run_memetic` takes an optional `target_cost`; `run_memetic_shard.py` takes an
  opt-in `--stop-at-oracle` that forwards `--oracle-cost` into it.
* **The code lives only in `cluster_staging_maxsat/`.** The repo copies under
  `src/` are unchanged and byte-identity with staging is intentionally broken for
  exactly two files — see `DIVERGENCE.md`.
* Shards gain four additive fields: `stop_reason`, `time_to_target_s`,
  `target_cost_used`, `stop_at_oracle`. Nothing was renamed or removed.
* The manifest is now **390 jobs at a single 900 s budget**; the array wall limit
  is **20 min**, not 15.
* Measured: the EA reached the proven optimum on `uuf250-0100.cnf` in **8.8 s**
  where RC2 needed **219 s**. Without the early stop that same run would have
  reported `wall_time_s = 900`.
* Default (`target_cost=None`, no `--stop-at-oracle`) preserves the previous
  behaviour exactly.

---

## 1. Why

`run_memetic` stopped only on `time_cap` or `max_gens`
(`TIER2_MEMETIC_PLAN` §5). Every tier-2 config sets `ea.max_gens: 1000000`
precisely so that wall-clock is the sole binding stop condition — which means
**every run burned its full budget even after it had already found the proven
optimum.**

That is why §6.6 has to describe `wall_time_s` as "the full budget spent, not the
time at which the best assignment was first found", and why `speedup_vs_rc2` was
only an upper bound on the EA's advantage.

§6.6 offers two ways to make time-to-optimum a real measurement: add an
improvement callback to `run_memetic` and record `(t, cost)` pairs, or sweep
budgets and read the hit-rate curve. Threading the known optimum into the EA gets
the same survival-curve data **without either** — the optimum is already in
`tier2_oracle.csv` and already flows down the manifest as `--oracle-cost`.

---

## 2. The unit trap

This is the one thing that must not be got wrong (`TIER2_MEMETIC_PLAN` §6.3
trap 1):

| quantity | convention | where |
|---|---|---|
| `Individual.fitness` / `best_soft_weight` | **satisfied** soft weight, higher is better | the EA |
| `target_cost` / `--oracle-cost` / RC2's `final_cost` | **unsatisfied** soft weight, lower is better | RC2, the oracle table, the shard's `best_cost` |

They are never compared directly. The conversion happens at the comparison site
(`cluster_staging_maxsat/src/evo/memetic.py:109`):

```python
incumbent_cost = total_soft_weight - best_soft_weight
```

`total_soft_weight` is the sum of soft-clause weights in the parsed instance,
computed **once before the loop** (`memetic.py:94`), not per generation.

It is written in the general weighted form on purpose. On the 26 SATLIB tier-2
instances every weight is 1 and there are no hard clauses, so it reduces to an
unsatisfied-clause count — but a `weight == 1` assumption would silently corrupt
weighted instances the moment `TIER2_MEMETIC_PLAN` §3's WCNF fix lands and the
MSE instances join the set.

Two related traps, both avoided:

* `satisfied_clauses.unsatisfied` in the raw EA output counts **hard** clauses
  too (§6.3 trap 2). It is not the cost and is not used.
* Individuals with `hard_violations > 0` carry a **penalty** fitness
  (`-1e9 - 1e6*hv`, `population.py:161`), not a soft weight. They are excluded
  from the check rather than converted (`memetic.py:107`).

---

## 3. Where the check fires

`_at_target()` is evaluated at three points:

1. **Before the loop** (`memetic.py:111`) — if the JW-seeded initial population
   already meets the target, no generation runs at all and
   `time_to_target_s ≈ 0.0`.
2. **After each child's polish updates the incumbent** (`memetic.py:182`), inside
   the population-fill loop — not only at end-of-generation. §7 measured ~57
   children per generation at 8 s with `memetic_base`; at a 900 s budget a
   generation is a long time to keep running after the answer is in hand.
3. The `while` guard (`memetic.py:125`) carries `stop_reason is None`, so a
   pre-loop hit skips the loop entirely.

### `<=`, not `==`

The stop condition is `incumbent_cost <= target_cost`. A cost strictly *below*
the oracle means the two solvers disagree about what the instance is — almost
certainly a parse difference of the kind `RC2_STATUS` §3.5 found with the SATLIB
`%`/`0` trailer (§6.3: "a negative `abs_gap` is a bug signal, not a result").
Halting makes that visible in the shard rather than letting the run grind on for
900 s and bury it.

### Why the default path is unchanged

Incumbent tracking moved *inside* the fill loop. With `target_cost=None` that is
exactly equivalent to the end-of-generation update that is still there:

* `best` is the running maximum over everything evaluated so far, so the elites
  carried into `new_members` — which come from the previous population, whose max
  already lost to `best` — can never beat it;
* the strict `>` preserves the same tie-break (first individual to attain the
  maximum wins).

Confirmed empirically: `run_ea.py` and `run_experiment.py` produce identical
solutions against the repo and staging copies (§6).

---

## 4. API

### 4.1 `run_memetic`

```python
def run_memetic(wcnf, cfg, rng_seed=1, target_cost: int | None = None) -> dict
```

`target_cost=None` is the default and preserves the previous behaviour exactly.
`run_experiment.py` and `run_ea.py` call this positionally and are unaffected.

Two keys are added to the returned dict, set on **all** paths:

| key | value |
|---|---|
| `stop_reason` | `"target"` \| `"time_cap"` \| `"max_gens"` |
| `time_to_target_s` | float seconds from loop start to first reaching the target, else `None` |

With `target_cost=None`, `stop_reason` is `"time_cap"` or `"max_gens"` and
`time_to_target_s` is `None`.

### 4.2 `run_memetic_shard.py`

```
--stop-at-oracle    (default: off)
```

**Opt-in, not automatic.** `--oracle-cost` on its own keeps doing only what it
always did: fill `abs_gap` / `rel_gap` / `is_optimal` for the combine step. It
becomes a *stop condition* only when `--stop-at-oracle` is passed explicitly,
because an oracle-terminated run is a **benchmarking** mode, not a solver mode,
and nothing should enter that mode by accident.

`--stop-at-oracle` without `--oracle-cost` exits **2** with an explicit message
and writes no shard.

### 4.3 New shard fields (additive)

| field | meaning |
|---|---|
| `stop_reason` | `"target"` \| `"time_cap"` \| `"max_gens"` |
| `time_to_target_s` | seconds to first reach target, else `null` |
| `target_cost_used` | the value passed into the EA, else `null` |
| `stop_at_oracle` | bool, what the flag was set to |

`wall_time_s` keeps its current meaning — total loop wall time. It is now *equal*
to `time_to_target_s` on target-stopped runs and equal to the budget otherwise,
which is the point; **`stop_reason` is what disambiguates**, so downstream code
never has to infer which case it is looking at.

### 4.4 The cost cross-check

`best_cost` is still re-derived from `meta.assign_bits` by `score_assignment()`,
with the solver's own number kept in `best_soft_weight_reported` (§6.3,
unchanged). On top of that: if a target stop fires but the re-derived `best_cost`
is **greater** than `target_cost`, the two cost paths disagree about the same
assignment. The record gets

```
status = "cost_mismatch"
error  = "target stop fired but re-derived best_cost=… > target_cost=… …"
```

and a non-zero exit, so `combine_tier2.py`'s integrity pass catches it instead of
averaging it in.

---

## 5. Running it

### 5.1 Manifest

```bash
python -m src.bench.make_tier2_manifest \
    --budgets 900 \
    --out-dir cluster_staging_maxsat/scripts
```

```
jobs              : 390 (26 inst x 3 cfg x 1 budget x 5 seed)
solver-seconds    : 351000
submit with:  sbatch --array=1-390%30 scripts/tier2_memetic_array.sbatch
```

390 = 26 instances × 3 configs × 1 budget × 5 seeds. Verified after generating:
390 lines, no header row, and `job_id` on line N is `t2m_<N>` for all 390 — the
line-N-is-array-task-N invariant everything rests on (§4.4).

351 000 s ≈ 97.5 h is the **no-early-stop** bound; ~3.5 h wall at `%30` over 13
waves. §7's measurement (optimum reached at 8 s on two instances) says most runs
stop in seconds and the real total is a small fraction of that.

### 5.2 Submit

```bash
sbatch scripts/smoke_tier2_memetic.sbatch            # unchanged: 5 tasks, 10 s

# full budget, no early stop (the historical behaviour)
sbatch --array=1-390%30 scripts/tier2_memetic_array.sbatch

# time-to-optimum mode
sbatch --array=1-390%30 --export=ALL,STOP_AT_ORACLE=1 \
       scripts/tier2_memetic_array.sbatch
```

`STOP_AT_ORACLE` (default `0`) is how the array reaches the new flag; it is the
sbatch-level mirror of `--stop-at-oracle` and is off by default for the same
reason. `MANIFEST`, `OUTDIR` and `GRACE` still come from the environment
unchanged.

### 5.3 Wall limit

`--time` went from **15 min to 20 min**. A 900 s budget does not fit in 15
minutes once grace and interpreter startup are added — every non-target-stopped
task would be killed by SLURM at the moment it was about to write its record.

```
900 s budget + 60 s default GRACE = 960 s = 16 min
20 min limit                            -> ~4 min for module load, conda activate, parse
```

The SIGALRM watchdog caps the process at budget+grace regardless of
generation-boundary overrun (§7 below). `--mem=8G`, `--cpus-per-task=1` and
`OMP_NUM_THREADS=1` are unchanged. `smoke_tier2_memetic.sbatch` has its own
`--time=00:05:00` and `BUDGET=10` and inherits nothing, so it was left alone.

`STOP_AT_ORACLE=1` does **not** relax the wall limit — a run that never reaches
the optimum still spends the full budget.

---

## 6. Verification

Run from the staging root (`cluster_staging_maxsat/`), which is what the sbatch
does (`cd ..` from `scripts/`). Running from the repo root would resolve
`src.cli.run_memetic_shard` to the **unmodified** repo copy.

| # | check | result |
|---|---|---|
| 1 | default path, 8 s, no `--stop-at-oracle` | `stop=time_cap`, `t_target=None`, `target_cost_used=null`, cost 2 |
| 2 | `--stop-at-oracle`, 900 s budget, same instance and seed | `stop=target`, `wall=8.799`, `t_target=8.783`, `best_cost=1` |
| 3 | weighted instance with 100 hard clauses | 500 soft total, 492 reported satisfied, `best_cost=8`, `unsat_soft_clauses=8`, `stop=target` |
| 4 | `--stop-at-oracle` without `--oracle-cost` | exit 2, explicit message, no shard |
| 5 | target 500 on an instance with optimum 1 | stops at `best_cost=83`, `t_target=0.0`, 0 generations — confirms `<=` and the pre-loop check |
| 6 | stubbed target stop with a bad assignment | `status="cost_mismatch"`, exit 1 |
| 7 | `run_ea.py` / `run_experiment.py` vs repo copy | identical solutions (`best_soft_weight=492.0`, `hv=0`, `soft_unsat=8.0`) |

Check 3 reproduces §6.3's measured cross-check exactly (500 − 492 = 8 =
`best_cost`) on a *weighted* instance with hard clauses, which is what the
general conversion form is for.

Check 7's only differences are `elapsed_sec` and `total_flips`; `total_flips`
varies run-to-run on the **unmodified** repo copy too (83515 vs 55734 across two
identical invocations), because flips are bounded by per-child wall clock.

### `wall_time_s` overruns the budget slightly

Check 1 reports `wall_time_s = 9.262` for an 8 s budget. The time cap is only
tested at generation boundaries, so the last generation overruns. This is
**pre-existing and unchanged** — it is not introduced by the target stop, which
can only ever make a run shorter. The overrun is bounded by one generation:
~3 s for `memetic_base`/`memetic_pop150`, ~20 s for `memetic_deeppolish` (40
children × `ls.time_limit_s: 0.5`). That is why 900 s still fits comfortably in
the 20-minute limit.

---

## 7. Interpreting the results

### 7.1 The caps mismatch — stratify by `rc2_cap_s`

> The 900 s budget matches the `uuf250_1000c` RC2 cap but **not**
> `uuf_diff_unsat`, which ran at cap 600 (`TIER2_MEMETIC_PLAN` §1.1). For those
> 8 instances the EA is given 1.5× the wall RC2 had. `rc2_cap_s` is carried in
> `tier2_oracle.csv` for exactly this reason (§1.1, `RC2_STATUS` §4.4c) —
> stratify any speed claim by it.

The 18 `uuf250_1000c` instances are the comparable half; the 8 `uuf_diff_unsat`
ones are not. With `--stop-at-oracle` the effect is bounded — a run that reaches
the optimum stops long before either cap — but it still applies to every run that
does not, and to any claim of the form "the EA matched RC2 within the same
budget".

### 7.2 What `speedup_vs_rc2` now means

`combine_tier2.py` lives in repo `src/` and was out of scope, so it is unchanged.
The new shard fields are additive, so it will not break — but it will **ignore**
`time_to_target_s`, and its `speedup_vs_rc2` keeps computing
`rc2_solve_s / wall_time_s`. With target stops that formula is now *correct*
rather than an upper bound, which is a **happy accident, not a verified change**.
Surfacing `time_to_target_s` and `stop_reason` in `summary.csv` is a follow-up
task.

Until then, filter on `stop_reason == "target"` before reading any speed number:
a `time_cap` row's `wall_time_s` is still just the budget.

### 7.3 Everything §6.5 and §7 said still applies

The early stop measures *when* the optimum was reached; it says nothing about
*whether* the run is evidence about the EA's evolutionary component. §7's
calibration warning stands — at these budgets the result is dominated by the
WalkSAT polish, and `ea_generations` should be checked before comparing configs.
`run_hit_rate` remains the headline metric, not `rel_gap` (§6.4, §6.5).

---

## 8. Where the code lives, and the divergence

**Only `cluster_staging_maxsat/` was modified.** The repo copies under `src/` are
untouched, which deliberately breaks the byte-identity invariant
`TIER2_MEMETIC_PLAN` §2.2 asserts, for exactly two files:

```
cluster_staging_maxsat/src/evo/memetic.py
cluster_staging_maxsat/src/cli/run_memetic_shard.py
```

The other nine files of the dependency closure are still byte-identical and must
stay that way. `cluster_staging_maxsat/DIVERGENCE.md` records this, carries the
amended §2.2 verification loop (split in two — for the divergent pair,
`IDENTICAL` is inverted into the *failure* signal, meaning the staging change was
lost to an rsync or a revert), and says how to close the divergence.

Any *other* edit to those two files must be made in both trees by hand until the
change is ported: the mirror check will not catch a drift that it already reports
as expected.

---

## 9. Known gaps, unchanged by this work

| gap | status |
|---|---|
| 2 MSE tier-2 instances unrunnable (new-format WCNF) | **open** — `TIER2_MEMETIC_PLAN` §3; the conversion here is already written in the weighted form so those instances will be handled correctly when it lands |
| `combine_tier2.py` ignores `time_to_target_s` / `stop_reason` | **open** — §7.2; repo-side, follow-up |
| `mutate1(..., ind.hard_satisfied)` reads a leaked `ind` (repo `memetic.py:93`, staging `memetic.py:142` after this change shifted the lines) | pre-existing latent bug, deliberately untouched; irrelevant on the 26 zero-hard-clause instances |
| `wall_time_s` overruns the budget by up to one generation | pre-existing, §6 above |
| the two staging files diverge from `src/` | intentional, §8 |
