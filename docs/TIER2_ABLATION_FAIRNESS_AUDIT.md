# Ablation fairness audit — `memetic_deeppolish` vs `local_multistart_deeppolish`

**Date: 2026-09-13.** Code inspection only; no code was modified and no
experiments were launched. Companion to
[`TIER2_MEMETIC_PLAN.md`](TIER2_MEMETIC_PLAN.md),
[`TIER2_TARGET_STOP.md`](TIER2_TARGET_STOP.md), and
[`../cluster_staging_maxsat/DIVERGENCE.md`](../cluster_staging_maxsat/DIVERGENCE.md).

**Question.** A separate analysis reported that `memetic_deeppolish` beats
`local_multistart_deeppolish` in time to target: geometric mean of per-instance
ERT ratios (multistart / memetic) of 1.95, bootstrap CI [1.23, 3.04], 26
instances × 5 seeds. Is that a fair comparison of the evolutionary layer against
multistart, or could an unintended implementation difference explain it?

**Short answer.** The implementation is fair in every mechanical respect checked
(same local-search function and arguments, same target predicate, equivalent
timers, no budget dependence). The advantage is real for the *package* that was
run. But the comparison does not isolate the evolutionary layer: the memetic arm
also differs in initialization (JW seeding, and a crossover that on these
all-soft instances is a deterministic majority-polarity heuristic) and in
continuation (children inherit polished parents; the control discards all
progress every 0.5 s). The JW-seeded control designed to remove the seeding
confound was never run. Details follow, with verified facts, hypotheses, and
unresolved questions kept apart.

All paths below are relative to the repo root. Line numbers refer to the
staging tree `cluster_staging_maxsat/src/`, which is the code the cluster ran.

---

## 0. Provenance — does the inspected code match the code that ran?

**Verified.**

| | `memetic_deeppolish` | `local_multistart_deeppolish` |
|---|---|---|
| SLURM array / date | 20085583, 2026-08-12 19:59–20:54 | 20721254, 2026-08-30 10:59–11:11 |
| `schema_version` | 1 | 2 |
| `stop_at_oracle` | True (130/130) | True (130/130) |
| `git_sha` in records | `null` (130/130) | `null` (130/130) |
| `config_hash` in records | `8f4ba81eb1d96c66` | `4b32e701d4c9a147` |
| hash recomputed from today's YAML + runner injection | `8f4ba81eb1d96c66` ✓ | `4b32e701d4c9a147` ✓ |

- `git_sha` is null in every row: the rsynced staging tree is not a git repo and
  `MAXSAT_GIT_SHA` was not exported. Code identity **cannot** be established
  from the logs.
- The four files shared by both arms (`evo/operators.py`, `evo/population.py`,
  `sat/walksat.py`, `sat/state.py`) have a single commit in the staging tree
  (`d5936cd`, 2026-08-04) and are byte-identical to the repo `src/` copies
  today.
- `evo/memetic.py` last changed in `d5bf46c` (2026-08-05), before the memetic
  run.
- `evo/multistart.py` last changed in `404b7e6` (2026-08-30) — the morning of
  the multistart run. The array may have run on the pre-commit version; that
  commit changed only the JW path, and `tests/test_local_multistart.py`
  (`test_uniform_arm_is_unaffected_by_the_jw_addition`) asserts the uniform
  path is unchanged.
- `cli/run_memetic_shard.py` changed between the two runs (`3c94f8d`). The diff
  on the memetic code path adds `process_time()` bookkeeping and the solver
  dispatch only; nothing timing-relevant.
- The reported number reproduces from the logs: geometric-mean ERT ratio on
  `wall_time_s` with success = `stop_reason == "target"` is **1.947**. The
  analysis under audit is the one these logs support.

**Limitation.** "These bytes produced these rows" rests on commit dates,
matching config hashes, and the byte-identity discipline documented in
`DIVERGENCE.md`, not on a recorded SHA.

---

## 1. Local-search call path and effective parameters

**Verified identical.**

- Both arms call the same function object `evo.operators.short_polish`
  (`evo/multistart.py:250`, `evo/memetic.py:162`).
- Both resolve the budget through the same `evo.memetic._ls_budget`
  (`evo/multistart.py:202`, `evo/memetic.py:116`), from an `ls:` block that is
  byte-identical in the two YAMLs.
- Both seed each polish with `rng.randrange(1 << 30)` off the run's
  `random.Random(seed)`.
- `short_polish` (`evo/operators.py:385-427`) forwards
  `max_flips = ls_polish_flips = 12500`, `time_limit_s = 0.5`, and hard-coded
  defaults `noise=0.10`, `hard_safe=True`, `smooth_every=0`, `rho=0.5`. Nothing
  in the YAML overrides those defaults. `flip_budget: 12500` is dead config:
  `_ls_budget` maps it to `max_flips`, which `short_polish` ignores when
  `ls_polish_flips` is present. Same in both arms.

**Verified — matters for how the settings are described in the paper.**
The 12 500-flip cap **never binds**. `walksat_polish` does O(#clauses) work per
iteration (`unsat_hard_ids`, `unsat_soft_indices`, `_count_hard_violations`,
`snapshot_best_if_better`; `sat/walksat.py:576-653`), so 0.5 s buys a median of
~2 200 iterations on the cluster:

| | median iters/polish | min | max | polishes/s |
|---|---|---|---|---|
| memetic (`total_flips / children`) | 2 172 | 1 486 | 3 118 | 1.985 |
| multistart (`total_flips / restarts`) | 2 250 | 1 595 | 3 382 | 1.990 |

The effective polish is "0.5 s of WalkSAT", node-speed dependent. On nodes that
ran both arms the throughput is the same (intl-20: 2 199 vs 2 201; intl-15:
2 145 vs 2 133; intl-24: 1 590 vs 1 605), so the arms had equal effective polish
per node. The node mixes differ (different days); the net effect is +3.6%
iterations per polish for *multistart*. A flip-based ERT ratio
(Σ `total_flips` / successes) is **2.07**, so the advantage is not a node-speed
artifact. The readme's "~5 300 iterations per 0.5 s" is a workstation figure,
not the cluster's.

---

## 2. Stopping, target detection, return behaviour

**Verified equivalent.**

- Same predicate — `total_soft_weight - satisfied <= target_cost`, feasible
  only, `<=` not `==`: `evo/memetic.py:98-109`, `evo/multistart.py:219-224`.
  Both evaluate with `population.evaluate_assignment`.
- Memetic checks after every child's polish (`evo/memetic.py:180-185`);
  multistart after every restart (`evo/multistart.py:263`). Both return the
  incumbent. Neither continues past the target.
- Memetic additionally checks the initial population before the loop
  (`evo/memetic.py:111`); multistart has no pre-polish evaluation. Irrelevant on
  these instances (no raw draw is at cost 1).

**Verified, deliberate, symmetric — continuing after stall.**
`walksat_polish` has no target argument and no stagnation criterion. It stops
only at the flip cap, the time cap, or when *every* clause is satisfied
(`sat/walksat.py:585-590`). On the 26 UNSAT instances the last never fires, so
every polish — including the one that finds the optimum — runs its full 0.5 s.
Continuing is intentional and appropriate: it is plain WalkSAT with 10% noise
walking plateaus, with `snapshot_best_if_better` (`sat/state.py:321-330`)
preserving the best point seen. The only cost is ≤ 0.5 s of latency added to
time-to-target, identically in both arms.

**One asymmetry, against memetic.** The 900 s cap is checked once per
generation in memetic (`evo/memetic.py:125`) but once per restart in multistart
(`evo/multistart.py:238`). A generation is 38 children × 0.5 s ≈ 19 s. Memetic's
12 unsuccessful runs took 917.2–918.6 s; multistart's 6 took 900.1–900.3 s.
This inflates memetic's ERT numerators by ~2% on the failing instances —
negligible, and in the wrong direction to explain the advantage.

---

## 3. Timers and budgets

**Verified.**

- Memetic starts its clock *after* JW seeding and the initial evaluation of the
  40-member population (`evo/memetic.py:66-78`); multistart starts it before its
  first restart (`evo/multistart.py:226`; the JW-arm prior is also built before
  the clock, `:207`). The excluded work is ~30 ms: max
  `wall_time_s − time_to_target_s` is 0.035 s (memetic) vs 0.002 s (multistart).
- `wall_time_s` in the shard record (`cli/run_memetic_shard.py:430-439`) wraps
  the whole solver call in both arms and is what the ERT uses, so the offset
  does not enter the comparison.
- Per-child EA overhead — `clause_aware_crossover1` rebuilds occurrence lists
  on every call, `mutate1`, two `Population.evaluate` calls, the Noop advisor —
  counts toward the total budget but not the LS budget. Measured: 1.985 vs
  1.990 polishes/s, i.e. ~1.3 ms per child.
- Each polish's 0.5 s timer starts after `_extract_clauses` and `SatState`
  construction (`sat/walksat.py:554-570`), in both arms.
- The SIGALRM watchdog fires at budget + 60 s grace in both drivers
  (`scripts/tier2_memetic_array.sbatch`,
  `scripts/tier2_local_multistart_array.sbatch`; same `--time`, `--mem`,
  `--cpus-per-task`).

---

## 4. Telemetry semantics

**Verified.**

- `total_flips` = Σ `res["flips"]` = `num_flips`, the number of **loop
  iterations** in `walksat_polish` (`sat/walksat.py:586,686`), not
  `state.flips` (applied flips). On all-soft instances a variable is always
  chosen, so the two coincide; with hard clauses and `hard_safe` they would not.
- `flips_in_target_restart` (`evo/multistart.py:266`) is the iteration count of
  the **entire** polish in the restart that produced the target. Since polishes
  are never interrupted, it is always ≈ a full 0.5 s worth (observed
  1 601–2 254). It does **not** measure flips-until-target and must not be read
  that way. The memetic arm has no analogue.
- There is no partial or interrupted local-search call in either arm, so nothing
  is counted inconsistently.
- `descent`: **no such field, function, or term exists anywhere in the code,
  results, or docs** (grep across the tree). If the separate analysis reported
  a `descent` quantity it was derived outside this repository. Unresolved.
- Cosmetic: memetic reports `flips_per_sec: 0.0` and `restarts: 0`
  (`evo/memetic.py:247-248`); `ea_generations` counts the partial generation at
  a target stop.

---

## 5. Scope of the ablation — where the attribution problem is

**Verified differences beyond selection / recombination.**

**(a) Initialization is confounded.** Memetic seeds from the Jeroslow–Wang
prior (`population.py:144`, `init_seeds`); the arm compared against uses
uniform coins (`evo/multistart.py:170-173`). The JW-seeded control
`local_multistart_jw_deeppolish` — the middle arm whose purpose is to remove
this confound — has a config, a manifest, a submitter and tests, but **no tier-2
results exist on disk** (`results/` holds only `tier2_memetic` and
`tier2_local_multistart`). The readme's own three-arm table labels
memetic − uniform as "the whole package", not "population / crossover / EA".

**(b) The crossover acts as a second, deterministic initialization heuristic.**
With zero hard clauses, `clause_aware_crossover1` (`evo/operators.py:139-311`)
resolves every parental disagreement by soft-literal majority polarity
(`s_true[v]` vs `s_false[v]`), falling back to the fitter parent only on exact
ties. A generation-1 child is therefore "JW draw, with roughly half the
variables set to their majority polarity" — far closer to the optimum than a
uniform start — before any selection pressure on *polished* individuals has
acted (generation-1 parents are raw, unpolished JW draws; tournament selection
among them is on raw fitness).

**(c) Continuation vs. memoryless restart.** Because the polish is only
~2 200 iterations, a multistart restart spends most of it re-descending from
cost ≈ 130; a memetic child starts near cost 1–3 and spends all of it on the
plateau. The control therefore tests "EA + inheritance of progress" against
"discard all progress every 0.5 s". A single continuous WalkSAT run, or an
iterated-local-search control (restart from best with a small perturbation —
`SatState.restart_partial_from_best` already exists, `sat/state.py:351`), is the
missing comparison that would separate population/crossover from mere
continuation.

**(d) Minor.** `Population.evaluate` cache (EA-only, no timing effect); two
unpolished elites carried per generation; a latent bug where `mutate1` receives
the stale `ind.hard_satisfied` of the last *initial* member
(`evo/memetic.py:142`) — inert on all-soft instances.

**Hypothesis, supported by the logs.** Of the 118 memetic successes, 35 hit the
target in generation 1 and 79 within generation 2 (generation of hit:
1 → 35, 2 → 44, 3 → 20, 4 → 6, 5 → 5, ≥ 6 → 8). Median children at hit = 55
(≈ 28 s); multistart needs a median of 196 restarts. Most of the advantage is
realised before evolutionary dynamics can plausibly have contributed, which is
consistent with (a) + (b) + (c) rather than with selection and recombination.

The effect is also heterogeneous. Per-instance ERT (wall s, successes/5):

| instance | memetic ERT | multistart ERT | ratio ms/mem |
|---|---|---|---|
| uuf250-0100 | 28.3 (5) | 223.2 (5) | 7.88 |
| uuf250-066 | 249.9 (4) | 138.6 (5) | 0.55 |
| uuf250-070 | 629.5 (3) | 325.9 (5) | 0.52 |
| uuf250-071 | 634.1 (3) | 618.8 (4) | 0.98 |
| uuf250-072 | 25.3 (5) | 20.5 (5) | 0.81 |
| uuf250-075 | 17.0 (5) | 53.1 (5) | 3.13 |
| uuf250-079 | 125.1 (5) | 171.3 (5) | 1.37 |
| uuf250-080 | 687.0 (3) | 248.3 (5) | 0.36 |
| uuf250-081 | 97.5 (5) | 794.5 (3) | 8.15 |
| uuf250-087 | 22.0 (5) | 44.9 (5) | 2.04 |
| uuf250-089 | 14.3 (5) | 94.4 (5) | 6.59 |
| uuf250-090 | 37.4 (5) | 287.1 (5) | 7.68 |
| uuf250-093 | 21.5 (5) | 12.4 (5) | 0.58 |
| uuf250-094 | 29.0 (5) | 68.1 (5) | 2.34 |
| uuf250-096 | 432.8 (4) | 348.3 (5) | 0.80 |
| uuf250-097 | 40.6 (5) | 484.8 (4) | 11.93 |
| uuf250-098 | 640.9 (3) | 399.4 (4) | 0.62 |
| uuf250-099 | 262.9 (4) | 329.7 (5) | 1.25 |
| uuf200-01 | 392.7 (4) | 63.3 (5) | 0.16 |
| uuf200-02 | 9.2 (5) | 11.7 (5) | 1.28 |
| uuf250-010 | 28.2 (5) | 209.2 (5) | 7.41 |
| uuf250-03 | 18.8 (5) | 16.8 (5) | 0.90 |
| uuf250-05 | 42.9 (5) | 472.0 (4) | 10.99 |
| uuf250-06 | 35.7 (5) | 259.9 (5) | 7.28 |
| uuf250-07 | 45.2 (5) | 141.2 (5) | 3.13 |
| uuf250-09 | 53.2 (5) | 219.6 (5) | 4.13 |
| **geometric mean** | | | **1.947** |

Multistart has *lower* ERT on 10 of 26 instances and more successes overall
(124 vs 118). All 12 memetic failures ran the full 48 generations (1 824
children) and ended at cost 2 (cost 3 on uuf200-01), i.e. the population
stalled one above the optimum.

---

## 6. Validity of truncated-run simulation

**Verified structurally valid.** The total budget enters each arm in exactly one
place — the loop guard (`evo/memetic.py:125`, `evo/multistart.py:238`) — plus
memetic's post-hoc stop-reason label (`evo/memetic.py:200`). No parameter,
schedule, restart policy, or polish budget scales with it (`_ls_budget` reads
`ls.time_limit_s`, not the top-level budget); `max_gens = 10⁶` never binds; the
main RNG stream is consumed per child / per restart independently of wall time
(each polish uses its own `Random(seed)`). A 450 s run would therefore reach the
target at the same time as the first 450 s of a 900 s run with the same seed. A
memetic run would end at the next generation boundary (≤ ~19 s late; the
watchdog grace is 60 s, so it would not fire).

**Caveat.** Trajectories are not seed-reproducible even between two 900 s runs,
because every polish's outcome depends on how many iterations fit in 0.5 s on
that node under that load, and the next child starts from that outcome. That
is timing variability, not budget dependence, and it affects portfolio
simulation from logs only in the same way it affects the original measurement.

---

## 7. Unresolved

- No commit SHA in the records; provenance rests on dates and config hashes.
  Exporting `MAXSAT_GIT_SHA` in the sbatch drivers would close this for future
  runs.
- The `descent` metric is not from this codebase.
- Whether the multistart array ran on the pre- or post-`404b7e6`
  `multistart.py` (same-day commit; uniform path unaffected either way per the
  tests, unverified on the cluster).
- Node-speed heterogeneity (2× across nodes) is not stratified in the ERT;
  matched-host data suggests it does not bias the arms, but samples per host
  are small.

---

## 8. Summary for the paper discussion

> We audited the implementation behind the reported time-to-target advantage of
> `memetic_deeppolish` over `local_multistart_deeppolish` (geometric-mean ERT
> ratio 1.95, reproduced from the logs as 1.947). Both arms invoke the same
> local-search function with the same effective arguments, use the same target
> predicate and incumbent return, and record wall time from equivalent points;
> the residual asymmetries (a ~30 ms clock offset, ~1 ms per-child EA overhead,
> a per-generation rather than per-restart budget check that adds ~18 s to
> memetic's failed runs) are negligible and do not favour the memetic arm. The
> nominal 12 500-flip polish budget never binds: the effective polish is 0.5 s
> of WalkSAT, ≈ 2 200 iterations on the cluster, and it is the same on both arms
> per node; a flip-based ERT ratio (2.07) confirms the advantage is not a
> node-speed artifact. Truncated-run simulation from 900 s logs is valid: no
> component of either arm depends on the total budget. However, the comparison
> does not isolate the evolutionary layer. The memetic arm differs from the
> tested control in three ways beyond selection and recombination:
> Jeroslow–Wang seeding versus uniform seeding (the JW-seeded control designed
> to remove this confound was never run); a crossover that, on these all-soft
> instances, deterministically sets every disagreeing variable to its majority
> polarity, so first-generation children are already near-optimal; and
> inheritance of polished parents versus a control that discards all progress
> every 0.5 s. Consistent with this, 67% of memetic successes occur within the
> first two generations, and the control has lower ERT on 10 of 26 instances
> and more successes overall. The reported ratio should be interpreted as the
> benefit of the full memetic package (informed initialization + continuation +
> EA operators) over memoryless restarts, not as evidence for the evolutionary
> operators specifically; attributing it to the evolutionary layer requires the
> JW-seeded multistart arm and an iterated-local-search control that preserves
> progress without a population.

---

## Appendix — how the numbers above were obtained

All from `cluster_staging_maxsat/results/tier2_memetic_all.jsonl`
(`config_id == "memetic_deeppolish"`, 130 rows) and
`cluster_staging_maxsat/results/tier2_local_multistart_all.jsonl` (130 rows),
read-only:

- ERT per instance = Σ `wall_time_s` over all 5 seeds / #(`stop_reason == "target"`);
  ratio = multistart / memetic; geometric mean over 26 instances.
- Flip-based ERT: same with `total_flips` in place of `wall_time_s`.
- Iterations per polish: `total_flips / children` (memetic) and
  `total_flips / restarts` (multistart); per-host medians.
- Config-hash check: `sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")))[:16]`
  over the YAML with `ea.enabled` defaulted (memetic path only) and
  `time_limit_s: 900.0` injected, exactly as `run_memetic_shard.py:311-315` does.
