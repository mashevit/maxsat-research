# Corpus calibration — goals and execution plan

**Date:** 2026-09-16. Written against commit `991a8cd`; **revised the same
day (r2)** against `0dc3bc3` (which committed the `oracle_evalmaxsat_array.sbatch`
path fix) after a review of every claim against the repository — the
substantive changes are itemised in the log's Checkpoint 1. Companion to
[`CORPUS_GENERATOR_PLAN.md`](CORPUS_GENERATOR_PLAN.md) (family list, Steps 0–7),
[`CORPUS_GENERATOR_PILOT_NOTE.md`](CORPUS_GENERATOR_PILOT_NOTE.md) (the 25-row
RC2 pilot) and [`maxsat-benchmark-design-notes.md`](maxsat-benchmark-design-notes.md)
(the (n, α) plane and the two-pass probe/select design). Per-turn checkpoints
(verified facts, job ids, commands) accumulate in
[`CORPUS_CALIBRATION_LOG.md`](CORPUS_CALIBRATION_LOG.md). This document narrows
those into a *measured calibration process*: a small grid, both solvers, frozen
selection rules, then fresh instances. It supersedes the generator plan's Step 3
grid and its Step 4 selection thresholds; everything else there stands.

Notation: **α = m/n** (clause density; α_c ≈ 4.267 for random 3-SAT),
**c\*** = optimum cost (unsatisfied soft weight), **ρ** = Spearman rank
correlation. Throughout, *verified* means measured in this repository with a
pointer to the rows; *proposed* means code or runs not yet done; *hypothesis*
means a claim the calibration is designed to test, not assume.

---

## 1. Research questions and the scope of conclusions

**Q1 — Reachability.** For random Max-3-SAT and Max-2-SAT, over which region of
the (n, α) plane does the RC2 configuration this project uses certify c\* within
900 s, and how does its proof time vary with n, α and c\* inside that region?

**Q2 — Informativeness.** Inside that region, where does the memetic EA
(`memetic_deeppolish`, target-stop mode) do non-trivial work — i.e. neither
reaches the optimum in the first few percent of its budget on every seed, nor
fails on every seed?

**Q3 — Complementary hardness.** Across instances where both measurements are
defined, what is ρ between RC2 proof time and memetic time-to-target (and its
success-rate companion), pooled and within family/cell, and how much of any
relation is explained by the shared covariates (n, α, c\*)?

**Scope of conclusions.** Every conclusion is about *this stack*: PySAT
1.9.dev15 `RC2(wcnf, solver="g3")` with `adapt=exhaust=minz=False` (no
stratification; unweighted instances make `RC2Stratified` moot), and the
`memetic_deeppolish` preset with the target-cost stop, single-threaded on the
cluster's `main` partition. Conclusions cover the two random families and the
grid's (n, α) range only. They say nothing about exact solvers in general
(branch-and-bound wins the dense-random regime; design-notes §2), nothing
about structured or weighted families until those enter a later calibration,
and nothing about instances RC2 cannot certify — those are recorded as
right-censored, not dropped, but cannot enter Q3.

**Conditionality.** Every ρ, yield fraction and "informative band" reported
here is conditional on (i) the cells chosen in §3, (ii) the 900 s budgets,
and (iii) the certification and success criteria of §4.4 (RC2
`completed == true`; memetic `stop_reason == "target"`). Changing any of
these changes the population the statistic describes; none of them is a
property of random Max-k-SAT itself, and the tables must say which
population they are about. Broader family diversity (structured, weighted,
MaxCut, industrial) is an explicit *later* objective (§5.5); this
calibration does not speak to it.

**Two things this plan deliberately does not assume.**

- *No universal RC2 ceiling at a fixed c\*.* The pilot's "cliff at c\* ≈ 10"
  is a random-3-SAT observation at a 60 s cap and one seed per cell. Max-2-SAT
  reached c\* = 25 in 5.5 s on the same stack, so the ceiling is family- and
  density-dependent. The exact statement that *is* implied by the solver
  configuration: with `exhaust=False`, `minz=False` and unit weights, every
  core RC2 extracts raises the lower bound by exactly 1, so certification
  takes exactly c\* UNSAT calls plus one SAT call. The *cost per call* is what
  varies with n and α, and that is what Q1 measures.
- *No monotone c\* across independently generated instances.* `E[c*]` grows
  with n and α; individual seeds do not have to. The pilot already shows it
  (n = 150, α = 5: seed 1 has c\* = 1, seed 2 has LB ≥ 3 and did not finish).
  Sanity checks on c\* are made on per-cell medians, never per instance.

---

## 2. Existing code and evidence

### 2.1 Verified today (commands run on this workstation, 2026-09-16)

| Item | Where | Status |
|---|---|---|
| Random k-SAT generator, weight samplers, WCNF writer (`dialect="old"`) | `instancegen/{generate,feasible,wcnf_io}.py` | 62 tests pass (`python -m pytest instancegen -q`, from repo root) |
| Byte-identical regeneration | `wksat_v50_k3_sr6.00_hr0.00_w1_uniform_s1.wcnf`, `wksat_v100_k2_sr4.00_hr0.00_w1_uniform_s1.wcnf` | two writes hash identically; RC2 returns c\* = 6 and 25, matching the pilot rows |
| RC2 profiler with three-layer timeout, LB recovery on SIGKILL | `src/cli/profile_hardness.py`, `src/cli/solve_rc2_anytime.py` (byte-identical to the `cluster_staging_maxsat/src/cli/` copies — `diff` checked) | runs; `solve_s` on killed rows is cap+grace wall time (censored, see §4.4); appends to `--out`, no skip-if-done of its own |
| Memetic runner with target stop, `time_to_target_s`, `stop_reason` | `cluster_staging_maxsat/src/cli/run_memetic_shard.py`, `.../evo/memetic.py` | runs on generated old-dialect WCNF (`instance_format=wcnf_old`), both k = 2 and k = 3 |
| Memetic on the two pilot cells above | `memetic_deeppolish`, seed 1, budget 10 s | **reached c\* in 0.50 s and 0.49 s, generation 1** — where RC2 needed 5–10 s |
| Slurm array drivers (all under `cluster_staging_maxsat/scripts/`) | `screen_mse16_array.sbatch` (RC2, cap 900, `--time 18:00`, header `%20`), `tier2_memetic_array.sbatch` (`--time 20:00`, `GRACE=60`, `STOP_AT_ORACLE`; the tier-2 arrays were submitted at `%30`), `submit_mse16_screen.sh` (`THROTTLE`, default 20) | exist; RC2 driver hard-codes `manifest_mse16_screen.txt` and `results/profile_mse16` |
| Aggregation | `src/bench/analyze_tiers.py`, `combine_tier2.py`, `make_tier2_manifest.py` | exist; consume per-task JSONL |
| Divergence between `src/` and `cluster_staging_maxsat/src/` | `cluster_staging_maxsat/DIVERGENCE.md` | intentional; the cluster runs the staging tree, which is the one with the target stop |
| Git tracking of the staging tree | `.gitignore` | `cluster_staging_maxsat/data/` was ignored wholesale (so a manifest written there was untracked); r2 narrows it so `data/generated/**/manifest.jsonl` is tracked, instances stay out, mirroring the repo-root `data/generated` rule |

### 2.2 Verified earlier (rows in the repository)

- **RC2 pilot, 25 rows, cap 60 s, one seed per cell** —
  `results/profile/gen_pilot_cap60.jsonl`. 3-SAT: n = 50 certifies α ≤ 8
  (c\* = 1, 6, 10; 0.0 / 2.8 / 52.9 s); n = 70 certifies α ≤ 6; n ≥ 100 is
  seed-dependent at α = 5 and uncertified at α ≥ 6. 2-SAT n = 100: α = 4
  certifies (c\* = 25, 5.5 s), α = 6 and 10 do not (LB 47 and 84 at 60 s).
- **Tier-2 comparison point** — 26 SATLIB instances
  (`cluster_staging_maxsat/scripts/tier2_oracle.csv`): 18 from
  `results/hardness/uuf250_1000c/` (n = 250, α = 4.26, cap 900 s, all
  c\* = 1, RC2 63–496 s; the full 35-row profile spans 14.6–496 s over its
  26 completions) and 8 from `uuf_diff_unsat` (cap 600 s; six uuf250 with
  c\* = 1, two uuf200 with n = 200 and c\* = 2). So c\* = 1 on 24/26.
  `memetic_deeppolish` target-stop at 900 s, 5 seeds: 118/130 successes,
  per-instance ERT 9.2–687 s (`archive/TIER2_ABLATION_FAIRNESS_AUDIT.md`
  §"Per-instance ERT").
- **MSE-2016 random / set-covering under both oracles** — all timeouts up to
  1800 s (`results/oracle_more_data.jsonl`, `archive/CORPUS_MSE2016_ASSESSMENT.md`).

### 2.3 Proposed, not built

`instancegen/cli.py`, `maxcut.py`, `reweight.py`, `planted.py`, `verify.py`
(generator plan Steps 1–2); a parameterised RC2 array driver; a
calibration-analysis script. Nothing under `data/generated/` exists yet.

### 2.4 Hypotheses the calibration tests

- **H1.** Within a family at fixed n, RC2 proof time increases with α and with
  c\*; at fixed α it increases with n. (Pilot: consistent for 3-SAT at 60 s.)
- **H2.** Memetic time-to-target is governed mainly by n and by proximity to
  α_c, not by c\*: small-n cells are trivial regardless of c\* (§2.1, 0.5 s);
  the uuf250 cells (n = 250, c\* = 1) are not (ERT up to 690 s).
- **H3.** Consequently the region where *both* solvers do non-trivial work is
  a diagonal strip in (n, α) — larger n at lower α — and it may be narrow or
  empty for 3-SAT under a 900 s RC2 cap. Whether it exists is the calibration's
  first-order result.
- **H4.** Inside the strip, ρ(RC2 time, memetic TTT) is low once n, α and c\*
  are controlled for. This is the claim the final corpus is meant to test; it
  is stated here so that the selection rules in §5 cannot be tuned toward it.

---

## 3. Initial calibration grid (batch `calib_a`)

Informed by the pilot and by the uuf250 point. Both families, pure soft
(`hard_ratio = 0`, `w_max = 1`, `weight_dist = uniform`), `m = round(α·n)`
exactly, generator `instancegen.generate` (k distinct variables, fair signs,
duplicate clauses allowed — recorded in the manifest). **5 seeds per cell,
seeds 1–5.**

| Family | n | α | Cells | Instances |
|---|---|---|---:|---:|
| Max-3-SAT (k = 3) | 50, 70, 100, 150, 250 | 4.26, 5, 6, 8 | 20 | 100 |
| Max-2-SAT (k = 2) | 100, 150, 250, 400 | 2, 3, 4, 6 | 16 | 80 |
| | | | **36** | **180** |

Why these edges. α = 4.26 at n = 250 reproduces the uuf250 comparison point
with a generator instead of SATLIB (roughly half those instances will have
c\* = 0; they stay in the results as easy cases). α = 8 at n = 250 and α = 6
at n = 400 (2-SAT) are expected to be uncertified at 900 s and are included so
the censoring boundary is *measured*, not inferred from the 60 s pilot.
2-SAT starts at α = 2 because c\* = 0 is likely below α ≈ 1 and the pilot's
α = 4 gave c\* = 25 — the informative band is probably 2–4.

Expected cost of the RC2 arm is bounded in §4.5. The grid is small on purpose:
if the strip of §2.4 H3 falls between grid lines, `calib_b` refines around it
with the same tooling before anything is frozen.

---

## 4. Measurements, solver configurations, budgets, timeouts

### 4.1 RC2 arm (one run per instance; RC2 is deterministic)

- Tool: `src.cli.profile_hardness --cap 900 --grace 60` via the array driver.
- Recorded per row (existing schema): `status` ∈ {optimal, timeout,
  subprocess_killed, error, unsat}, `solve_s`, `final_cost` (= c\* when
  optimal), `cost_lower_bound` (also on killed rows), `completed`, `tier`.
  `unsat` cannot occur on a pure-soft instance and is treated as a failed
  run (§4.4). The array driver (`rc2_profile_array.sbatch`, M1) writes a
  sidecar `task_N.env.json` per task with the PySAT version, hostname,
  Slurm job id, cap and grace; generator params, seed and `instance_sha256`
  come from `manifest.jsonl` and are joined at aggregation on the instance
  path (and cross-checked on sha).
- **Solver configuration to hold fixed:** `RC2(wcnf, solver="g3")`, all
  options default (`adapt=False, exhaust=False, minz=False`). The cluster's
  `maxsat` env PySAT version is recorded per task and compared with
  1.9.dev15; a mismatch is reported, not silently accepted.

### 4.2 Memetic arm (stochastic; several seeds per instance)

- Tool: `scripts/tier2_memetic_array.sbatch` with `STOP_AT_ORACLE=1`, config
  `configs/tier2/memetic_deeppolish.yaml`, budget **900 s** (same as the
  tier-2 runs, so cells are comparable with uuf250), `GRACE=60`.
- Runs only on instances whose RC2 row is `optimal` — target-stop needs a
  target. Uncertified instances are listed in the manifest with
  `memetic: not_run (no certified target)`, never omitted.
- **3 seeds per certified instance** in `calib_a` (bounded arm; the final
  corpus uses 5, matching tier-2). Recorded: `status` (`ok` or a failure
  string such as `parse_error`), `stop_reason` ∈ {target, time_cap,
  max_gens}, `time_to_target_s` (None unless `target`), `wall_time_s`,
  `best_cost`, `abs_gap`, `ea_generations`, `total_flips`, `config_hash`.
  `max_gens` is unreachable at the configs' `max_gens: 1000000` and, if it
  ever appears, is a failed run, not a censored one. `hard_violations` is
  always 0 here (no hard clauses), so feasibility is not a concern for
  these families.
- **Seeds are replicates, not instances.** Every per-instance statistic
  aggregates the 3 seeds first; nothing downstream sees a seed as a sample
  point. Success rate = successes / 3 (so it takes values in {0, ⅓, ⅔, 1} —
  coarse, which is why the `calib_a` read-out is exploratory); ERT =
  Σ wall_time_s over all seeds / successes, with `wall_time_s` = the
  900 s budget on a `time_cap` seed (undefined at 0 successes — reported as
  such, and see §5.2 for how such instances enter ρ); median TTT with
  failures treated as > 900 s (defined only when > half the seeds succeed).

### 4.3 Budgets and Slurm wall time (kept distinct)

| Arm | Solver budget | Grace/watchdog | `--time` | Per task | Concurrency (planned) |
|---|---:|---:|---:|---|---:|
| RC2 | 900 s cap | +60 s SIGKILL | 00:20:00 | 1 CPU, 8 GB | `%30` (`THROTTLE`, default 30) |
| memetic | 900 s | +60 s SIGALRM | 00:20:00 | 1 CPU, 8 GB | `%30` |

The 20 min wall covers 960 s of solver+grace plus `module load`, conda
activation and parsing; `tier2_memetic_array.sbatch`'s header documents why
15 min does not fit. Budget, grace, wall and resources are the settings the
committed tier-2 runs used. **Concurrency, historical record:** the RC2
screens (`full_uuf250_array`, `screen_mse16_array`, `oracle_evalmaxsat_array`)
ran at `%20` from their headers; the tier-2 memetic and multistart arrays were
submitted at `%30` (`archive/TIER2_TARGET_STOP.md`, `readme.txt`). The planned
default is now `%30` for both arms (the cluster allows up to 30 concurrent
single-CPU tasks), passed at submit time by the wrapper and overridable with
`THROTTLE=`. Concurrency changes elapsed time only; it changes neither the
per-task measurement nor the CPU-hours.

### 4.4 Timeout and easy-case handling — rules for every table

- Every run lands in exactly one of **three classes**, and every table
  reports the count of each:
  1. **Completed** — `profile.completed == true` (RC2) or `status == "ok"`
     with `stop_reason == "target"` (memetic). Only these carry a time.
  2. **Censored at the budget** — the solver ran the full budget without
     completing: RC2 `status ∈ {timeout, subprocess_killed}` with
     `cap_s` = the batch cap; memetic `status == "ok"` with
     `stop_reason == "time_cap"`. The time column is `NA` with
     `censored=true`, never the cap value and never the recorded `solve_s`
     of a killed process (which is cap+grace wall time). RC2's
     `cost_lower_bound` is kept on these rows. Rank statistics that need a
     value for censored rows use "> budget" ties at the top and say so.
  3. **Failed** — the run did not produce a valid measurement: RC2
     `status ∈ {error, unsat}`, empty or unparsable subprocess output, a
     missing or unreadable instance file, a Slurm task killed by `--time` or
     memory (no row at all — detected as a manifest line with no row);
     memetic `status != "ok"` or `stop_reason == "max_gens"`. Failed rows
     are **not** censored: they are listed with their error string, the
     cause is fixed, and the task is re-run. They enter no denominator
     (certified fraction, success rate) until they are resolved; a batch is
     not "complete" while any remain.
- **Easy cases stay.** c\* = 0 instances, RC2 completions in milliseconds,
  and memetic TTT in the first generation are all kept in the results and in
  the yield tables; they are what locates the trivial edge of the band. They
  are excluded from the *final* corpus only by the cell-level rules of §5,
  which are frozen before final generation.
- Every array is **resumable**: one JSONL per task; a task whose output
  already holds a completed row, or a censored row at a cap ≥ the current
  one, is skipped (`rc2_row_state.py` decides, both inside the task and in
  the submit wrapper's `RESUME=1` mode, which submits only the task ids
  still needed as a Slurm id list). A failed row (class 3) or a censored row
  at a lower cap is re-run and a new row appended; the aggregation keeps the
  last row per instance and reports how many were superseded. Failures are
  rows, not gaps, except when Slurm itself killed the task — then the
  missing row is the signal.

### 4.5 Batch accounting for `calib_a`

| Batch | Tasks | Per task | Concurrency | Worst-case CPU-h | Worst-case elapsed at %30 (compute only) |
|---|---:|---|---:|---:|---:|
| A1 RC2, 180 instances | 180 | 1 CPU · 8 GB · ≤ 960 s | 30 | 180 × 960 s = **48 CPU-h** | ⌈180/30⌉ = 6 waves × 16 min ≈ **1.6 h** |
| A2 memetic, 3 seeds × certified instances (C ≤ 180) | 3C ≤ 540 | same | 30 | ≤ 540 × 960 s = **144 CPU-h** | ⌈540/30⌉ = 18 waves × 16 min ≤ **4.8 h** |

Three quantities, kept apart: **CPU-hours** (Σ per-task solver+grace time;
independent of concurrency; the 48 / 144 figures are upper bounds because
every task is charged the full 960 s), **elapsed compute time** (CPU-h /
concurrency, rounded up to whole waves, plus ~1–2 min of `module load` /
conda / parsing per wave — the column above), and **queue delay** (time
from `sbatch` until 30 tasks are actually running; set by the partition's
load, not by this plan, and unbounded here — record it from `sacct`'s
Submit/Start stamps rather than estimate it). At the previous `%20` the same
batches were ⌈180/20⌉ = 9 waves ≈ 2.4 h and ⌈540/20⌉ = 27 waves ≈ 7.2 h.
Realistic cost is well below worst case: pilot evidence says roughly half of
A1 finishes in seconds, and A2 seeds on trivial cells stop in < 1 s. A2's task
count is fixed only after A1 returns; the manifest generator prints it.

---

## 5. From calibration to frozen selection rules and fresh instances

1. **Yield table** (per cell): RC2 certified fraction (of 5), median and range
   of `solve_s` among completions, c\* median and range (including 0s),
   fraction censored; memetic success rate, median TTT, ERT — with censoring
   shown. One CSV in `results/calibration/calib_a/yield_table.csv`, one
   markdown rendering in `docs/`.
2. **Complementarity read-out on `calib_a` itself** (exploratory, labelled as
   such): ρ(RC2 `solve_s`, memetic ERT), one point per instance, over
   certified instances with ≥ 1 memetic success, pooled and per family;
   partial ρ after regressing both (rank-transformed) on log n, α,
   log(1 + c\*). This is reported whatever its value and is **not** an input
   to step 3. Statistical conventions, fixed here so they cannot be chosen
   after seeing the numbers:
   - **Sampling unit = instance.** Memetic seeds are within-instance
     replicates and are collapsed to ERT / success rate before any ρ is
     computed (§4.2). Treating seeds as points would triple N and shrink
     every CI by ~√3 for no new information.
   - **Primary CI: instance-level bootstrap, stratified by cell**
     (resample the 5 instances within each cell with replacement, B = 10 000,
     BCa interval, percentile reported alongside). Stratifying keeps the
     designed (n, α) layout fixed under resampling; a plain instance
     bootstrap is reported as a check. This is the justified choice because
     the design is a fixed grid, the sample per cell is tiny, and the ERT
     distribution is heavy-tailed and censored — none of which the normal
     approximation handles.
   - **Analytic check:** Fisher z with the Spearman-specific standard error
     √((1 + ρ²/2)/(n − 3)) (Bonett & Wright 2000). The plain Pearson
     1/√(n − 3) is *not* used for Spearman. Reported next to the bootstrap;
     a large disagreement is itself reported.
   - **Within-cell ρ is not estimated**: 5 instances per cell cannot
     support it. The within-cell question is answered by the partial ρ and
     by a per-family ρ, and finally on the fresh 20-per-cell corpus (M4–M5).
   - **Censoring and selection.** ρ over "certified ∧ ≥ 1 success" is
     conditional on that selection; the count excluded for each reason is
     printed with every ρ. Sensitivity: recompute with 0-success instances
     entered as top-tied ERT (the "> budget" convention of §4.4). The
     right-censored RC2 rows cannot enter either version and are counted.
   - **Timing noise.** RC2 is run once per instance; run-to-run timing
     variation on the cluster is not estimated in `calib_a` and is a known
     source of attenuation in ρ. If the read-out is used for anything beyond
     placing `calib_b`, a repeat of ≈ 10 certified instances quantifies it.
3. **Freeze cell-level selection rules**, written to
   `instancegen/grids/corpus_v1.yaml` and committed *before* any final
   instance is generated. Rules operate on cell summaries, never on individual
   instances' outcomes, and take the symmetric form of the design notes §7:
   - RC2 certified fraction ≥ 4/5 (so time-to-target is defined for almost
     every seed at the next stage);
   - RC2 median `solve_s` ≥ 10 s (proof time carries information);
   - memetic median TTT ≥ 5 % of budget **or** success rate < 100 % on at
     least half the cell's instances (the EA is not finishing trivially);
   - memetic success rate > 0 on every certified instance in the cell (ERT
     defined).
   The numeric thresholds above are the *proposal*; the calibration may move
   them, and any change is recorded with the reason in the grid file. What
   is not allowed: dropping or adding a cell because of its ρ.
4. **Fresh final instances.** Selected cells are regenerated with a disjoint
   seed range (seeds 1001–1020, 20 per cell), certified per instance with the
   same RC2 arm, then run with 5 memetic seeds. `calib_a` rows never enter a
   reported ρ; instances that fail certification are recorded as censored
   and excluded from Q3 with the count stated.
5. **Family expansion gate.** MaxCut (Erdős–Rényi) and reweighted twins enter
   only if the two random families leave a c\* decade or an origin axis
   uncovered after step 4, and each new family goes through its own `calib_*`
   round before selection. Even-sided torus MaxCut is dropped: an even × even
   torus lattice is bipartite, so every edge is cut and c\* = 0 by
   construction — it cannot carry proof-time information. If a lattice family
   is wanted later, use odd sides or ±J couplings, and say why.
   **Broader corpus diversity — structured, weighted, industrial-style
   families — remains an explicit research objective after M5**, not a
   fallback: the two random families are where the measurement machinery is
   being calibrated, and any published ρ from them is a statement about
   random Max-k-SAT under this stack only (§1, Conditionality).

---

## 6. Implementation milestones

Each milestone is one short turn; each ends at a committed, checkable state.

### M1 — Generate `calib_a`, parameterise the RC2 array, prepare A1  *(done 2026-09-16, Checkpoint 1)*

Deliverables (as built; `cluster_staging_maxsat/` abbreviated to `csm/`):
- `instancegen/grids/calib_a.yaml` — the §3 grid as data (batch, shared
  params, families with k / n list / α list, seeds, dialect).
- `instancegen/cli.py generate-grid --grid <yaml> --staging-root csm` —
  writes instances through `write_wcnf(dialect="old")` to
  `csm/data/generated/calib_a/`, rewrites `manifest.jsonl` there (one row per
  instance: `cell_id`, `family`, `k`, `n`, `alpha`, `m`, `seed`,
  `generator.{name,version,params}`, `sizes`, `instance_sha256`, `git_sha`,
  `created_utc`), and writes the Slurm manifest
  `csm/scripts/manifest_calib_a_rc2.txt` (line N = task N, root-relative
  paths) plus `manifest_calib_a_rc2.sha256` (`sha256sum -c` format) so the
  cluster can verify the rsync before submitting. `--check` re-generates in
  memory and compares against the files on disk without writing.
- `csm/scripts/rc2_profile_array.sbatch` — `MANIFEST`, `OUTDIR`, `CAP`,
  `GRACE` env vars; per-task skip via `rc2_row_state.py`; `task_N.env.json`
  sidecar with PySAT version / host / job id; `LOCAL_SMOKE=1` bypasses
  `module load` for workstation smoke runs. `submit_rc2_profile.sh` — counts
  the manifest, checks every instance exists (and its sha, if the `.sha256`
  file is present), `THROTTLE` (default 30), `RESUME=1` to submit only the
  unfinished task ids, `DRY_RUN=1`.
- Tests (`instancegen/tests/test_cli.py`): grid loads and yields 180 unique
  filenames and 36 cells; `m = round(α·n)` per cell; regenerating is
  byte-identical; manifest sha matches file sha; Slurm manifest line N ↔
  manifest row N; `--check` passes on a fresh tree and fails on a tampered
  file. `csm/tests/test_rc2_row_state.py`: the skip/run decision on
  completed / censored / failed / lower-cap / absent rows.

Completion criteria: `python -m pytest instancegen -q` (repo root) and
`python -m pytest tests -q` (from inside `csm/`, which is where its tests
resolve the staging `src`) green; 180
files under `csm/data/generated/calib_a/` with `manifest.jsonl`; local smoke
of the array script on 2 instances at `CAP=20` through the real sbatch file
(`LOCAL_SMOKE=1`); the exact rsync + sbatch commands recorded in the log.
Submission happens on the login node and is recorded in the log **only when
it has occurred** (job id + `sacct` Submit/Start stamps).

### M2 — Memetic arm A2 on the certified subset

`make_calib_memetic_manifest.py` (a sibling of `make_tier2_manifest.py`
reading `results/profile_calib_a/*.jsonl`), 3 seeds × certified instances,
`STOP_AT_ORACLE=1`, budget 900; submit; record task count and job id.
Completion: manifest committed with the not-run list; A2 submitted.

### M3 — Yield table and complementarity read-out

`src/bench/calib_summary.py`: joins RC2 and memetic shards on
`instance_sha256`, applies §4.4 censoring rules, emits the yield table and the
ρ/CI table; markdown rendering to `docs/CALIB_A_RESULTS.md`. Completion: both
tables present, every one of the 180 instances accounted for (completed,
censored, error, not-run).

### M4 — Freeze rules; generate and certify the fresh corpus

`instancegen/grids/corpus_v1.yaml` committed with rationale; fresh-seed
generation; RC2 array submitted. Completion: grid file committed before the
generation timestamp in the manifest.

### M5 — Final memetic arm and analysis

5 seeds per certified instance; `calib_summary.py` re-run on the final batch;
Q1–Q3 answered with CIs and censoring counts. Family-expansion decision
(§5.5) taken and written down.

---

## 7. Cluster workflow (unchanged from the existing runs)

```bash
# workstation → cluster (data/ is not in git; the rsync carries it)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# cluster login node, submit from scripts/ (drivers `cd ..` to the tree root)
cd ~/maxsat-lab/scripts && mkdir -p logs
DRY_RUN=1 bash submit_rc2_profile.sh          # inspect: 180 tasks, %30, sha check
bash submit_rc2_profile.sh                    # submit A1 (defaults: calib_a, cap 900, grace 60)
RESUME=1 bash submit_rc2_profile.sh           # later: only the task ids without a valid row

# cluster → workstation, then aggregate here (staging tree has no src/bench/)
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_a/ cluster_staging_maxsat/results/profile_calib_a/
```

`THROTTLE=30` is the default; `THROTTLE=20` reproduces the earlier RC2
screens' concurrency. No cluster credentials or `sbatch` are available from
this workstation, so submissions are recorded as commands until run on the
login node, and the log records a job id only after `sbatch` has returned
one.
