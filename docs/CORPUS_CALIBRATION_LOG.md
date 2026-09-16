# Corpus calibration — running log

Checkpoint records for the milestones in
[`CORPUS_CALIBRATION_GOALS.md`](CORPUS_CALIBRATION_GOALS.md) §6. One entry per
turn: what was verified, what was implemented, what was submitted (job ids or
the exact commands), and the next step. Newest entry last.

---

## 2026-09-16 — Checkpoint 0: plan written, nothing implemented

Against commit `991a8cd` (+ one uncommitted binary-path fix in
`cluster_staging_maxsat/scripts/oracle_evalmaxsat_array.sbatch`, left as-is).
Stopped, as instructed, before implementing M1.

### What was verified

- **Generator + writer.** `python -m pytest instancegen -q` → 62 passed
  (from the repo root; running from inside `instancegen/` fails on imports).
  Regenerating two pilot cells is byte-identical across writes, and RC2 via
  `src.cli.profile_hardness` reproduces the pilot optima: c\* = 6 at
  3-SAT n = 50 / α = 6, c\* = 25 at 2-SAT n = 100 / α = 4. Wall times were
  ~1.8× the pilot's (4.9 s vs 2.8 s; 10.3 s vs 5.5 s), so workstation timings
  are indicative only — calibration times must come from the cluster.
- **RC2 configuration actually used.** PySAT 1.9.dev15,
  `RC2(wcnf, solver="g3")` with `adapt=exhaust=minz=False`
  (`src/cli/solve_rc2_anytime.py:190`). For unit weights the lower bound
  rises by exactly 1 per core, so certification takes c\* UNSAT calls; the
  *per-call cost* is what the grid measures. The pilot's "cliff at c\* ≈ 10" is
  a 3-SAT / 60 s observation, not a ceiling — 2-SAT (c\* = 25 in 5.5 s)
  already contradicts a universal one.
- **Memetic runner.** The staging copy
  (`cluster_staging_maxsat/src/cli/run_memetic_shard.py`) has
  `--stop-at-oracle` and records `time_to_target_s`; the repo `src/` copy
  does not — intentional, per `cluster_staging_maxsat/DIVERGENCE.md`. It
  reads generated old-dialect WCNF for k = 2 and k = 3
  (`instance_format=wcnf_old`). With `memetic_deeppolish`, seed 1, budget
  10 s, it **hit the optimum in 0.50 s and 0.49 s (generation 1)** on the two
  pilot cells where RC2 took 5–10 s. That is the strongest reason the
  calibration must include memetic runs: the RC2-reachable small-n cells look
  memetic-trivial, and the informative band (if it exists) is a diagonal strip
  toward larger n / lower α, like uuf250.
- **Slurm tooling.** `scripts/screen_mse16_array.sbatch` hard-codes its
  manifest (`manifest_mse16_screen.txt`) and output dir
  (`results/profile_mse16`) — needs `MANIFEST`/`OUTDIR` vars.
  `scripts/tier2_memetic_array.sbatch` is already parameterised
  (`MANIFEST`, `OUTDIR`, `GRACE`, `STOP_AT_ORACLE`), `--time 00:20:00` for a
  900 s budget + 60 s grace. No `sbatch` and no ssh alias on this
  workstation, so submissions are recorded as commands, not run.
- **Against per-instance c\* monotonicity** (from
  `results/profile/gen_pilot_cap60.jsonl`): 3-SAT n = 150 / α = 5, seed 1 →
  c\* = 1 in 1.5 s; seed 2 → LB ≥ 3, uncertified at 60 s.

### Plan document

`docs/CORPUS_CALIBRATION_GOALS.md`: research questions and scope;
verified / proposed / hypothesis split; the `calib_a` grid (Max-3-SAT
5 n × 4 α, Max-2-SAT 4 n × 4 α, 5 seeds → 180 instances); measurement and
censoring rules; the path to frozen cell-level selection rules and fresh seeds
(1001+); five milestones; batch accounting (A1: 180 tasks, 1 CPU / 8 GB, %20,
≤ 48 CPU-h worst case; A2: ≤ 540 tasks, ≤ 144 CPU-h). Even-sided torus MaxCut
dropped (bipartite, c\* = 0).

### Implemented

Nothing beyond the document and the smoke checks above (scratchpad only; no
repo changes other than the new docs).

### Jobs / commands

None submitted. Commands for A1 are in the goals doc §7; they depend on M1's
manifest and array driver.

### Next milestone — M1 (awaiting approval)

- `instancegen/grids/calib_a.yaml` — the grid as data.
- `instancegen.cli generate-grid` — instances →
  `cluster_staging_maxsat/data/generated/calib_a/`, `manifest.jsonl`
  (params, seed, `instance_sha256`, git sha, `created_utc`), and the Slurm
  manifest `scripts/manifest_calib_a_rc2.txt`.
- `scripts/rc2_profile_array.sbatch` with `MANIFEST`/`OUTDIR` and
  skip-if-complete; `submit_rc2_profile.sh`.
- Tests; local 2-instance smoke at `--cap 20`; exact rsync + sbatch commands
  for A1 recorded here.

**Open question before M1:** keep 5 seeds/cell and all 36 cells (48 CPU-h
worst case), or trim the corners expected to be censored (3-SAT n = 250 /
α = 8; 2-SAT n = 400 / α = 6)? The goals doc argues for keeping them so the
censoring boundary is measured, not inferred.
