# Kernelised memetic on calib_2sat_sc2: milestone A built, 18-task batch prepared (2026-10-18)

**Request (user, 2026-10-18)** [quote]: "what you purpose in optimizing memetic -
to stronger memetic? using which ideas? prepare cluster run for the max2sat, with
the kernelization, tell me files to upload to cluster and commands".

**Status:** built, tested, smoke-run on the workstation. **Committed and pushed
2026-10-18: `754392a`** (code + batch), then **`ad19012`** (throttle default
1000; new `submit_m2_memetic.sh` hash in the upload file). Use
`MAXSAT_GIT_SHA=ad19012`. Not yet submitted. Index: `docs/current/RESEARCH_NOTES.md`, N-2026-10-18-a.
Background: `docs/current/RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §2–§3 (the kernel
finding), §5 A, §8 (the user's decision and the gate).

Tags: [verified] measured or read off code here; [inference] my reading;
[unverified] from memory, to be checked before citing.

## 1. What was built [verified: code, tests]

All in `cluster_staging_maxsat/` (staging only; `DIVERGENCE.md`, 2026-10-18).

| file | what |
|---|---|
| `src/sat/kernel.py` (new) | The exact kernel, promoted from `scripts/diag_max2sat_kernel.py` with the same rules and reconstruction (including the 10-14 fix for unequal or hard weights): merge identical clauses, complementary soft units to a constant, pure variables, degree-2 MaxSAT resolution; `lift` runs it backwards. Plus the gate: `screen_frac`, `gate()`, and the config keys. |
| `src/cli/run_memetic_shard.py` | Opt-in `preprocess: kernel` (an absent key or `none` is the historical path). Shard schema 4, additive fields. |
| `configs/tier2/memetic_deeppolish_p40_ls3p5_kern_v2.yaml` (new) | The pre-registered v2 arm (`memetic_deeppolish_p40_ls3p5_v2.yaml`, 12,500 flips, 3.5 s, pop 40, clip) plus `preprocess: kernel` and `preprocess_gate: {screen_min: 0.2, gain_min: 0.2}`. Nothing else differs (checked key by key by the builder). |
| `scripts/make_calib_2sat_sc_memetic_manifest.py` | `--plan kern`: 18 tasks, sidecar column `preprocess`. The m2v2, cgrid and tgrid manifests still rebuild byte-identical (`--check`). |
| `scripts/m2_results.py` | Checks each shard's `preprocess` against the sidecar (absent on both sides = earlier manifests, unchanged). `aggregate` adds `preprocess_outcome`, `kernel_n_vars`, `preprocess_s` per task and prints the gate counts. |
| `tests/test_kernel.py` (new, 14 tests), `tests/test_calib_2sat_sc_memetic_prep.py` (+8) | See §3. |

### 1.1 How a run goes

1. Parse the instance (outside the clock, as in every arm).
2. **Clock starts.** Screen: `screen_frac` = the fraction of occurring variables
   that are pure or occur exactly once positive and once negative. Below
   `screen_min` (0.20) → `skipped_screen`, run the original.
3. Kernelise. Use the kernel only if it removes ≥ `gain_min` (0.20) of the
   occurring variables and no kernel clause is longer than the longest original
   clause; otherwise `skipped_gain` / `skipped_length` and run the original.
   Contradictory hard clauses → `skipped_infeasible`.
4. The memetic runs **unchanged** on the kernel, with the target shifted by the
   kernel constant (`c* − kernel_const`; 0 on this grid) and the time limit
   `budget − preprocess_s`. If every variable is eliminated (`kernel_empty`) the
   lifted assignment is optimal and no solver runs.
5. The best kernel assignment is lifted back and **scored on the original
   clauses**, so `best_cost` means what it always meant.
6. `time_to_target_s` = `preprocess_s` + the solver's time to target. So the
   kernelise time counts inside the budget and inside TTT (user, 2026-10-14).

**Integrity checks in the shard:** `best_cost == kernel_best_cost +
kernel_const` (else `cost_mismatch`), plus the existing target cross-check.

**New shard fields (schema 4; all null without `preprocess`):** `preprocess`
(the gate's decision), `preprocess_s`, `screen_frac`, `kernel_n_vars`,
`kernel_n_clauses`, `kernel_n_hard`, `kernel_const`, `kernel_max_len`,
`kernel_gain`, `kernel_best_cost`, `solver_time_limit_s`.
- Naming: the statistic called `s` in the directions note §8.2 is recorded as
  `screen_frac`, because a `_s` suffix means seconds everywhere else in the
  shards.

**Reporting convention (user, 2026-10-14):** this arm is "memetic with exact
kernelising (gated)"; RC2 is "RC2 (PySAT), as distributed", without our
preprocessing.

## 2. Workstation smoke [verified: 1 seed, 60 s budget, stop at c\*]

| instance | n | gate | kernel vars | preprocess s | best / c\* | TTT incl. kernel | children |
|---|---:|---|---:|---:|---:|---:|---:|
| s251 (sc01) | 16,000 | kernel | 425 | 0.09 | 12 / 12 | 0.30 s | 10 |
| s253 (sc02) | 16,000 | kernel | 434 | 0.11 | **15 / 14** | not in 60 s | 2,407 |
| s255 (sc03) | 16,000 | kernel | 420 | 0.12 | 13 / 13 | 0.72 s | 19 |
| s256 (sc04) | 64,000 | kernel | 572 | 0.55 | 13 / 13 | 1.50 s | 28 |
| s257 (sc05) | 64,000 | kernel | 300 | 0.56 | 10 / 10 | 0.68 s | 4 |
| s258 (sc06) | 64,000 | kernel | 332 | 0.54 | 9 / 9 | 0.57 s | 1 |

- Kernel sizes and children counts equal the 2026-10-14 diagnostic (directions
  note §2–§3), so the module reproduces it.
- On uuf250-03 (random 3-SAT) the gate skips at `screen_frac` 0.004 in < 0.01 s.
- **Raw baseline for the pairing:** the same arm without kernelising
  (`p40_ls3p5_v2`, the m2v2 batch, same instances, seeds 1–3, 900 s) went
  **0/18** (all budget exhausted; `results/calib_2sat_sc2_memetic`).

## 3. Tests [verified]

- **Brute-force exactness** (600 random instances, n 3–8, clause lengths 1–4
  with repeats and tautologies, 25% hard, weights 1–3): for **every** kernel
  assignment, the lifted assignment is feasible exactly when the kernel one is,
  and then costs exactly kernel cost + constant. The optima agree;
  contradictory hard clauses are detected.
- Gate decisions: skipped_screen / skipped_gain / skipped_length /
  skipped_infeasible / kernel_empty / kernel; unknown modes and gate keys are
  refused (the shard exits 2 before running).
- Shard: the kernel path reaches the brute-force optimum, scored on the
  original; TTT ≥ preprocess time; solver limit = budget − preprocess time; the
  recorded config keeps the run budget; `preprocess: none` equals an absent key.
- Manifest and results: the arm differs from the v2 arm only in the two keys;
  the `preprocess` check in `m2_results.py`; the written manifest is
  reproducible. The earlier sc2 batches still classify cleanly (m2v2 36/36,
  cgrid 108/108, no invalid rows).
- Staging suite: **307 passed, 3 skipped.**

## 4. The batch [verified: built and dry-run]

- `scripts/manifest_calib_2sat_sc2_kern.{tsv,tasks.csv,sha256,not_run.csv}`:
  6 eligible instances × seeds 1–3 × 1 arm = **18 tasks**. Job ids
  `sc2kn_ls3p5_<NN>_s<seed>`; 900 s, stop at c\*, grace 60; output
  `results/calib_2sat_sc2_kern/tasks`.
- Driver and submit script unchanged (`tier2_memetic_array.sbatch`,
  `submit_m2_memetic.sh`): 1 CPU, 8 GB, `--time 00:20:00`.
- **Cost:** worst case 18 × 960 s = 4.8 CPU-h. Expected [inference from the
  smoke]: 15 tasks end in seconds; the 3 s253 tasks may use the full 900 s, so
  about 0.8 CPU-h. One wave (18 ≤ the throttle).
- **Pre-registered reading:** success = stop at c\* with TTT (kernel time
  included) ≤ 900 s. Report per instance: successes / 3, median TTT, gate
  outcome and kernel size, paired against the m2v2 raw arm (0/18) and with RC2's
  raw times as context. Expected [inference]: 15/15 on s251, s255, s256, s257,
  s258; s253 open.

### 4.1 Upload

`scripts/rsync_files_calib_2sat_sc2_kern.txt` (40 paths). Against the cluster
snapshot of 2026-10-14 (`results/cluster_state/cluster_hashes_20261014.txt`):
- **changed:** `src/cli/run_memetic_shard.py`, `scripts/m2_results.py`;
- **new:** `src/sat/kernel.py`, the kern config, the 3 manifest files (plus the
  upload hash file and the list itself);
- everything else in the list is byte-identical to the cluster copy and is sent
  so that the src tree digest is certain.

`scripts/manifest_calib_2sat_sc2_kern.upload.sha256` (38 files: code, config,
driver, manifest, instances) proves the cluster copy after the rsync. The
login-node steps were run with `python`/`python3` tripwires on PATH: hash check
OK, DRY_RUN OK (`--array=1-18%30`).

**Upload checked 2026-10-18 [verified]** from the cluster snapshot
`results/cluster_state/cluster_hashes_20261018.txt` (2,452 files, taken after
the rsync):
- all 38 entries of `manifest_calib_2sat_sc2_kern.upload.sha256` match,
  including the `ad19012` `submit_m2_memetic.sh`;
- 39 of the 40 upload-list paths match byte for byte; only the list itself
  (`rsync_files_calib_2sat_sc2_kern.txt`) is missing. The runs don't use it;
- the cluster `src` tree digest is `7d7818aa…`, the same as the workstation at
  `ad19012`; no `.py` file is extra, missing or different;
- elsewhere, 5 files differ, none used by the runs: `DIVERGENCE.md`,
  `LOCAL_MULTISTART_JW_REPORT.md`, `readme.txt`, and the 2 old ones
  (`calib_2sat_sc_readout.py`, `preflight_calib_2sat_sc.sh`). The cluster-only
  files are the EvalMaxSAT build, `*.old` / `*.bak` backups and old archive
  copies.

### 4.2 Commands

`<commit>` = `ad19012` (the commit that holds these files, including the
throttle change).

On the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_calib_2sat_sc2_kern.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_evo/
```

On the login node (shell only):

```bash
cd ~/cluster_staging_maxsat_evo
sha256sum -c --quiet scripts/manifest_calib_2sat_sc2_kern.upload.sha256 && echo UPLOAD_OK
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_calib_2sat_sc2_kern.tsv OUTDIR=results/calib_2sat_sc2_kern/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=ad19012 MANIFEST=manifest_calib_2sat_sc2_kern.tsv OUTDIR=results/calib_2sat_sc2_kern/tasks bash submit_m2_memetic.sh
```

Back on the workstation, after the array:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_evo/results/calib_2sat_sc2_kern/ results/calib_2sat_sc2_kern/
~/.venvs/maxsat/bin/python scripts/m2_results.py pending --manifest scripts/manifest_calib_2sat_sc2_kern.tsv --outdir results/calib_2sat_sc2_kern/tasks --summary
~/.venvs/maxsat/bin/python scripts/m2_results.py aggregate --manifest scripts/manifest_calib_2sat_sc2_kern.tsv --outdir results/calib_2sat_sc2_kern/tasks
# resume only infra/invalid ids, if any (login node):
IDS=<ids> RESUME=1 MAXSAT_GIT_SHA=ad19012 MANIFEST=manifest_calib_2sat_sc2_kern.tsv OUTDIR=results/calib_2sat_sc2_kern/tasks bash submit_m2_memetic.sh
```

**Throttle:** the cluster allows `--array=1-1000%1000` (user, 2026-10-18). Since
`ad19012` the submit scripts default to `%1000` (user's go, 2026-10-18), so no
`THROTTLE=` is needed; the DRY_RUN prints `--array=1-18%1000`.

## 5. A stronger memetic (direction B): what I propose and why [inference; literature unverified]

**Expanded 2026-10-18** in [`STRONGER_MEMETIC_DESIGN.md`](STRONGER_MEMETIC_DESIGN.md):
sources checked, the interactions, and the build plan. That document
supersedes the table below where they differ.

**What limits the solver** (evidence: directions note §1, §3, §9; Stage L1):
1. **Mutation at a fixed per-variable rate.** 2% of n flips per child: at
   n 64,000 an optimal assignment goes from 13 to 832–948 unsatisfied clauses
   (§9.1). Each child starts far from its parent.
2. **Plain WalkSAT without memory.** No tabu, no clause weights, noise 0.10.
   In chains of degree-2 variables it can undo its own moves; on plateaus it has
   nothing to steer by.
3. **Crossover ignores structure.** It decides variable by variable from static
   scores, so it cannot keep a parent's good block intact.
4. **Speed.** Pure Python, 180k–380k flips/s on the cluster.
5. **s253 shows that kernelising is not enough.** Its kernel has only 434
   variables, yet the memetic stays 1 above c\* (60 s here, 120 s on 10-14),
   while RC2 proves it in 58 s on the kernel. That is a search-quality problem,
   not a size problem.

**Proposed components, in the order I would try them.** Each is an opt-in key
(the `polish_cap` pattern: absent = today's behaviour and RNG stream, with an
equality test). Each is calibrated by our own grid, not by a framework (the
user's stance, HP plan §0c.1). The kernel arm is the base, and s253 is the
first test case.

| # | component | idea | why first / later |
|---|---|---|---|
| B1 | **Tabu in the polish** | a flipped variable may not flip back for `tenure` steps, unless that gives a new best (§9.2) | cheapest (one integer comparison per candidate); targets the back-and-forth in degree-2 chains |
| B2 | **Clause-weighting local search** | each clause carries a dynamic weight; at a local optimum the weights of unsatisfied clauses rise, so the score landscape changes and the search leaves the plateau (the SATLike / NuWLS family [unverified: Lei and Cai 2018; NuWLS 2022–23]) | the main mechanism of today's strongest MaxSAT local search; general (any k, hard clauses), so it also serves MSE and the hard-clause track |
| B3 | **Distance-aware mutation** | a fixed number of flips per child, or flips confined to a neighbourhood (a variable and its clause neighbours), or only where the parents differ (§9.1) | removes the damage that grows with n; matters on the raw formula and MSE, much less on kernels (2% of 572 ≈ 11 flips) |
| B4 | **Partition crossover** | in the variable-interaction graph, take the variables where the parents differ and split them into connected parts; take the better parent part by part, so the child is at least as good as either parent on each part [unverified: Tinós, Whitley and Chicano, FOGA 2015; Chen, Whitley et al., GECCO 2018] | strong on sparse structure; check first how many parts our parent pairs actually have (a cheap diagnostic) |
| B5 | **Compiled inner loop** | the flip loop in C (via ctypes) | 10–50× more flips per second [inference], but it changes what "seconds" mean between versions (as v1 → v2 did); whether the cluster has gcc is unknown |

- **Not proposed:** LLM-designed components (user decision 2026-10-11).
- **Order:** B1 and B2 change only the polish, so they can be tested on s253 and
  on raw instances in one grid. B3 and B4 change the EA. B5 last, so that every
  algorithmic arm is compared within one speed.
- Nothing of B is built. It is several milestones; each needs approval.
