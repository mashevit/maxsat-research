# Corpus calibration — goals and execution plan

**Date:** 2026-09-16. Written against commit `991a8cd` plus one uncommitted
path fix in `oracle_evalmaxsat_array.sbatch`. Companion to
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
| RC2 profiler with three-layer timeout, LB recovery on SIGKILL | `src/cli/profile_hardness.py`, `src/cli/solve_rc2_anytime.py` | runs; `solve_s` on killed rows is cap+grace wall time (censored, see §4.4) |
| Memetic runner with target stop, `time_to_target_s`, `stop_reason` | `cluster_staging_maxsat/src/cli/run_memetic_shard.py`, `.../evo/memetic.py` | runs on generated old-dialect WCNF (`instance_format=wcnf_old`), both k = 2 and k = 3 |
| Memetic on the two pilot cells above | `memetic_deeppolish`, seed 1, budget 10 s | **reached c\* in 0.50 s and 0.49 s, generation 1** — where RC2 needed 5–10 s |
| Slurm array drivers | `scripts/screen_mse16_array.sbatch` (RC2, cap 900, `--time 18:00`, `%20`), `scripts/tier2_memetic_array.sbatch` (`--time 20:00`, `GRACE=60`, `STOP_AT_ORACLE`), `submit_mse16_screen.sh` | exist; RC2 driver hard-codes `manifest_mse16_screen.txt` and `results/profile_mse16` |
| Aggregation | `src/bench/analyze_tiers.py`, `combine_tier2.py`, `make_tier2_manifest.py` | exist; consume per-task JSONL |
| Divergence between `src/` and `cluster_staging_maxsat/src/` | `cluster_staging_maxsat/DIVERGENCE.md` | intentional; the cluster runs the staging tree, which is the one with the target stop |

### 2.2 Verified earlier (rows in the repository)

- **RC2 pilot, 25 rows, cap 60 s, one seed per cell** —
  `results/profile/gen_pilot_cap60.jsonl`. 3-SAT: n = 50 certifies α ≤ 8
  (c\* = 1, 6, 10; 0.0 / 2.8 / 52.9 s); n = 70 certifies α ≤ 6; n ≥ 100 is
  seed-dependent at α = 5 and uncertified at α ≥ 6. 2-SAT n = 100: α = 4
  certifies (c\* = 25, 5.5 s), α = 6 and 10 do not (LB 47 and 84 at 60 s).
- **Tier-2 comparison point** — `results/hardness/uuf250_1000c/` (SATLIB
  uuf250, n = 250, α = 4.26, c\* = 1 on 24/26): RC2 35–500 s for the one core;
  `memetic_deeppolish` target-stop at 900 s: 118/130 successes, per-instance
  ERT 9–690 s (`TIER2_ABLATION_FAIRNESS_AUDIT.md` §"Per-instance ERT").
- **MSE-2016 random / set-covering under both oracles** — all timeouts up to
  1800 s (`results/oracle_more_data.jsonl`, `CORPUS_MSE2016_ASSESSMENT.md`).

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
  subprocess_killed, error}, `solve_s`, `final_cost` (= c\* when optimal),
  `cost_lower_bound` (also on killed rows), `completed`, `tier`. Added at
  aggregation: generator params, seed, `instance_sha256`, PySAT version and
  git sha (echoed into the task log by the driver, joined afterwards).
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
  corpus uses 5, matching tier-2). Recorded: `stop_reason` ∈ {target,
  time_cap}, `time_to_target_s` (None on time_cap), `wall_time_s`,
  `best_cost`, `abs_gap`, `ea_generations`, `total_flips`, `config_hash`.
- Per-instance statistics: success rate = successes / 3; ERT =
  Σ wall_time_s / successes (undefined at 0 successes — reported as such);
  median TTT with failures treated as > 900 s.

### 4.3 Budgets and Slurm wall time (kept distinct)

| Arm | Solver budget | Grace/watchdog | `--time` | Per task | Concurrency |
|---|---:|---:|---:|---|---:|
| RC2 | 900 s cap | +60 s SIGKILL | 00:20:00 | 1 CPU, 8 GB | `%20` |
| memetic | 900 s | +60 s SIGALRM | 00:20:00 | 1 CPU, 8 GB | `%20` |

The 20 min wall covers 960 s of solver+grace plus `module load`, conda
activation and parsing; `tier2_memetic_array.sbatch`'s header documents why
15 min does not fit. These are the settings the committed tier-2 runs used.

### 4.4 Timeout and easy-case handling — rules for every table

- A row is a **completion** only if `profile.completed == true` (RC2) or
  `stop_reason == "target"` (memetic). Everything else is **right-censored
  at the budget**: its time column is `NA` with a `censored=true` flag, never
  the cap value and never the recorded `solve_s` of a killed process (which
  is cap+grace wall time). Rank statistics that need a value for censored
  rows use "> budget" ties at the top and say so.
- **Easy cases stay.** c\* = 0 instances, RC2 completions in milliseconds,
  and memetic TTT in the first generation are all kept in the results and in
  the yield tables; they are what locates the trivial edge of the band. They
  are excluded from the *final* corpus only by the cell-level rules of §5,
  which are frozen before final generation.
- Every array is **resumable**: one JSONL per task; a task whose output
  already holds a completed row is skipped on resubmit, and a task whose
  output holds a censored row is re-run only when the budget was raised
  (same convention as `oracle_evalmaxsat_array.sbatch`). Failures
  (`status=error`, missing instance, format error) are rows, not gaps.

### 4.5 Batch accounting for `calib_a`

| Batch | Tasks | Per task | Concurrency | Worst-case CPU-h | Worst-case wall at %20 |
|---|---:|---|---:|---:|---:|
| A1 RC2, 180 instances | 180 | 1 CPU · 8 GB · ≤ 960 s | 20 | 180 × 960 s = **48 CPU-h** | ≈ 2.4 h |
| A2 memetic, 3 seeds × certified instances (C ≤ 180) | 3C ≤ 540 | same | 20 | ≤ 540 × 960 s = **144 CPU-h** | ≤ 7.2 h |

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
   such): ρ(RC2 `solve_s`, memetic ERT) over certified instances with ≥ 1
   memetic success, pooled and per family, Fisher-z 95 % CI; partial ρ after
   regressing both on log n, α, log(1 + c\*). This is reported whatever its
   value and is **not** an input to step 3.
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

---

## 6. Implementation milestones

Each milestone is one short turn; each ends at a committed, checkable state.

### M1 — Generate `calib_a`, parameterise the RC2 array, submit A1  *(next)*

Deliverables:
- `instancegen/grids/calib_a.yaml` — the §3 grid as data (family, n, α,
  seeds).
- `instancegen/cli.py` `generate-grid --grid <yaml> --out
  cluster_staging_maxsat/data/generated/calib_a/` — writes instances through
  `write_wcnf(dialect="old")`, appends one manifest row per instance
  (`generator.{name,version,params}`, `alpha`, `seed`, `instance_sha256`,
  `git_sha`, `created_utc`) to `manifest.jsonl`, and writes the Slurm
  manifest `scripts/manifest_calib_a_rc2.txt` (line N = task N, root-relative
  paths).
- `scripts/rc2_profile_array.sbatch` — `screen_mse16_array.sbatch` with
  `MANIFEST` and `OUTDIR` env vars, per-task skip-if-complete, and the
  PySAT version echoed to the log. `submit_rc2_profile.sh` — the
  `submit_mse16_screen.sh` logic pointed at it.
- Tests: grid loads and yields 180 unique filenames; regenerating a cell is
  byte-identical; manifest sha matches file sha.

Completion criteria: `python -m pytest instancegen -q` green; 180 files under
`cluster_staging_maxsat/data/generated/calib_a/` with `manifest.jsonl`; local
smoke of the array script's Python step on 2 instances at `--cap 20`; A1
submitted (job id recorded in `docs/CORPUS_CALIBRATION_LOG.md`) or the exact
rsync + sbatch commands recorded there.

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
MANIFEST=manifest_calib_a_rc2.txt OUTDIR=results/profile_calib_a bash submit_rc2_profile.sh

# cluster → workstation, then aggregate here (staging tree has no src/bench/)
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_a/ cluster_staging_maxsat/results/profile_calib_a/
```

No cluster credentials or `sbatch` are available from this workstation, so
submissions are recorded as commands until run on the login node.
