# Batch 3c: the memetic on MSE 2026 (prepared 2026-10-29)

> "go, commit and prepare the 3c manifest" (user, 2026-10-29)

Milestone 3c of [`MSE26_RHO_PLAN.md`](MSE26_RHO_PLAN.md): the memetic side of
ρ. Milestone 4 (the ρ pre-registration) comes **before any result of this batch
is read**; submitting and copying back may happen earlier.

## 1. What runs

| | |
|---|---|
| instances | the 952 MSE 2026 instances with a published optimum (479 unweighted, 473 weighted) |
| seeds | 1, 2, 3 → **2,856 tasks** |
| config | `configs/strong/auto.yaml` (auto_hparams/3, v3, native C core, kernel gate **on for all**, user 2026-10-29) |
| target | the published optimum (`benchmark-metadata.csv` `optimal_cost`); the run stops when it is reached |
| budget | **1,800 s of process CPU from the process start** (`--budget-clock process`): start-up, imports, hash, parse, kernel gate, hparams and search all count; I/O waits do not (MSE26_RHO_PLAN.md §9) |
| watchdog | GRACE 300 s (COMPILED_MEMETIC_PLAN.md §8 C4) |
| Slurm | 1 CPU, `--time=01:00:00`, `--mem` = the instance's bin (§2) |
| record | shard schema 8: `cpu_to_target_s` (the ρ clock), `cpu_to_target_hit_s`, `cpu_total_s`, `wall_total_s`, `hash_s`, `parse_s`, `solver_start_s`, `peak_rss_mb`, flip-level target hit (3b), kernel gate fields, hparams |
| worst case | 2,856 × 1,800 s = **1,428 CPU-h** (target stops make it less) |

## 2. Parts (one `sbatch` per part)

Memory bins from [`COMPILED_MEMETIC_PLAN.md`](COMPILED_MEMETIC_PLAN.md) §15
(`scripts/mse26_membins.tsv`); the 8 GB bin is cut into 3 parts of ≤ 1,000
tasks. Default throttles add up to the 1,000 tasks the cluster runs at once.

| part | `--mem` | instances | tasks | throttle |
|---|---|---:|---:|---:|
| 8a | 8G | 290 | 870 | 270 |
| 8b | 8G | 290 | 870 | 270 |
| 8c | 8G | 290 | 870 | 270 |
| 16 | 16G | 20 | 60 | 60 |
| 32 | 32G | 21 | 63 | 63 |
| 64 | 64G | 41 | 123 | 67 |

Within a part, instances are ordered by set and hash, seeds 1–3 consecutive;
`pop_idx` m001–m952 is one id per instance across the parts.

## 3. Files (strong tree)

- `scripts/make_mse26_manifest.py` (workstation; `--check` reproduces the 18
  manifest files byte for byte) → `scripts/manifest_mse26_<part>.tsv` (the
  driver's 9 columns), `.tasks.csv` (sidecar: bin, set, hash, family, sha256,
  exact bytes, type, kernel status, optimum, the config values `m2_results.py`
  checks, `grace_s` 300, `budget_clock` process), `.sha256` (for the readout);
  `scripts/manifest_mse26.upload.sha256` (65 paths: code, config, scripts,
  manifests; **no instances**).
- `scripts/mse26_memetic_array.sbatch`: the driver; `--stop-at-oracle` and
  `--budget-clock process` fixed; logs the wrapper's wall (`WRAP_PRE_S`,
  `WRAP_RUN_S`), which the record does not count.
- `scripts/submit_mse26.sh` (login node, shell only): `PART=…`; checks the upload
  hashes, the config, and that every instance file exists with its census byte
  size (no 80 GiB hashing on the login node: each record carries the sha256 it
  read, and `m2_results.py` compares it with the sidecar); `MEM` for a rerun one
  bin up; `RESUME=1 IDS=…`; provenance file per submission.
- `scripts/m2_results.py`: takes `grace_s` and `budget_clock` from the sidecar
  when present; on the process clock **success = `cpu_to_target_s` ≤ budget**;
  the aggregate carries the schema 8 times. Earlier manifests are classified as
  before (tests: `tests/test_m2_results.py`).

## 4. Tests and smoke [verified]

- Suite: 630 passed / 16 skipped at 14b9276 (2 new in `test_m2_results.py`; the 14b9276 commit message's "631" was a miscount); 631 after the ERT test (2026-10-29).
- **Driver smoke** (workstation, mock tree, 2 local instances under MSE 2026
  paths, budget 60 s): a soft 2-SAT instance → kernel, optimum, `success`
  (`cpu_to_target_s` 0.11); a hard judgment-aggregation instance (48 k hard) →
  `time_cap` at cost 38 vs 37, `wall_total_s` 60.0 on the 60 s budget (the
  process clock binds); `m2_results.py` pending / aggregate: success 1,
  budget_exhausted 1, pending 0. The workstation's CPU clock is unreliable
  (MSE26_RHO_PLAN.md §9), so no CPU-vs-wall check is made locally.
- **Submit dry runs** on all 6 parts with sparse files of the exact census
  sizes (`python`/`python3` tripwires on PATH, never fired); a missing file →
  `MISSING`, a wrong size → `SIZE`, an edited code file → upload check `FAILED`,
  no `MAXSAT_GIT_SHA` → refused; a submission against a fake `sbatch` writes the
  provenance file; `RESUME=1 IDS=4,17 MEM=32G` gives `--array=4,17%60 --mem=32G`.
- **Arrange** mock-tested on the cluster's tree (`e10585e` = census + kbig
  uploads): new 25, same 1, replace 3, `MSE26_UPLOAD_OK`, 2,856 tasks, schema 8
  runner, `src/` equal to the workstation's; then a submit dry run in that tree.

## 5. Upload (flat) and commands

`tmp/upload_mse26/` (32 files: 29 tree files as `m26__*`,
`UPLOAD_MAP_mse26.tsv`, `arrange_mse26.sh`, plus `upload.sha256`), from
`make_flat_upload.py` with the verified lists oldest first (HMSE 0877898, PP10
2763872, census map, kbig map; later lists override earlier ones). Code: only
`src/cli/run_memetic_shard.py` and `src/evo/memetic.py` change. **No C rebuild**
(`ls_core.c` unchanged since 9ce84ca, built for the census).

```bash
# login node, after uploading tmp/upload_mse26/* into ~/upload_mse26/
cd ~/upload_mse26 && sha256sum -c upload.sha256      # 31 x OK
squeue -u $USER                                      # must be empty
bash arrange_mse26.sh                                # dry run: new 25, same 1, replace 3 (counts may differ slightly)
bash arrange_mse26.sh --apply                        # MSE26_UPLOAD_OK, 2856 tasks, schema 8 runner, link
cd ~ && rm -rf ~/upload_mse26
cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs
for p in 8a 8b 8c 16 32 64; do DRY_RUN=1 PART=$p bash submit_mse26.sh | grep -e instances -e command; done
for p in 8a 8b 8c 16 32 64; do MAXSAT_GIT_SHA=14b9276 THROTTLE=1000 PART=$p bash submit_mse26.sh; done   # user 2026-10-29: throttle 1000 per part
squeue -u $USER | wc -l
```

**Reruns** (after the copy back, ids from the workstation):
`python3 scripts/m2_results.py pending --manifest scripts/manifest_mse26_<part>.tsv
--outdir results/mse26_memetic/tasks --summary`; a task that died for memory goes
one bin up with `MEM=`; above 64 GB (the 11 bnn-verification instances at 98 %
of the 64 GB cover, COMPILED_MEMETIC_PLAN.md §15) it needs a larger `--mem` if
the partition offers it.

**Bring back** to `cluster_staging_maxsat_strong/results/mse26_memetic/`:
`tasks/` (2,856 `.jsonl`), `provenance/`, and `scripts/logs/mse26-memetic-*`
(at least those of failed tasks). **Not read before milestone 4 is written.**

## 6. Submission log

**2026-10-29 12:24 UTC** (user, `MAXSAT_GIT_SHA=14b9276 THROTTLE=1000`):

| part | job | tasks | state |
|---|---|---:|---|
| 8a | 23674900 | 870 | submitted |
| 8b | 23674901 | 870 | submitted |
| **8c** | — | 870 | **refused:** `QOSMaxSubmitJobPerUserLimit` ("Job violates accounting/QOS policy (job submit limit, user's size and/or time limits)") |
| 16 | 23674902 | 60 | submitted |
| 32 | 23674903 | 63 | submitted |
| 64 | 23674904 | 123 | submitted |

1,986 tasks in the queue. 8c came after 1,740 queued tasks and was refused,
while the three small parts after it were accepted, so the per-user submit cap
counts array tasks and lies between 1,986 and 2,609 (probably 2,000)
[inference]. `provenance/submit_8c_20261029T122454Z.txt` has no `sbatch` line:
that submission did not happen.

**Plan (user):** when the queue empties, copy back, classify per part with
`m2_results.py pending` (resubmission only; results are not read before
milestone 4), then submit part 8c whole and the failed tasks
(`RESUME=1 IDS=…`, `MEM=` one bin up for memory deaths), keeping the queue
under ~2,000 tasks.

**2026-10-29, later:** part 8c submitted by the user once the queue had room
(job id not recorded here; it is in `provenance/submit_8c_*.txt`, the file
with an `sbatch` line). Some of its tasks pend on the per-user memory cap
(QOS max memory) while the 64 GB tasks run; they start as those finish.
All 2,856 tasks are now submitted.

**2026-10-29, later still (user):** some tasks show errors on the cluster
(roughly 5–15 so far; the run is not finished). Plan, unchanged in kind: once
the queue is empty and results + logs are back, classify every failed task by
its cause (`m2_results.py pending`, `sacct` state, the task's log) and rerun
the fixable ones: memory deaths one bin up with `MEM=` (8 → 16 → 32 → 64 GB;
above 64 GB only if the partition allows it), other fixable causes (timeout of
the job wall, node failure, a code or path error) after the fix, with
`RESUME=1 IDS=…` per part. Classifying for resubmission is not reading the
results.

## 7. Copy back and failure classification (2026-10-29)

Archive `mse26_3c_back.tgz` (sha256 `82efc7d0…88be2`, matches the login node),
unpacked into the strong tree: 2,845 task files of 2,856, 8 provenance files,
5,712 logs, `sacct_3c.tsv` (2,856 3c rows + 2 kbig). `sacct`: 2,836 COMPLETED,
17 FAILED, 5 TIMEOUT. `m2_results.py pending` per part, read together with
`sacct` and the logs, gives four groups. **None is a memory death:** no
OUT_OF_MEMORY and no MemoryError; the overrunning tasks peaked at 0.34–5.7 GB,
well inside their bins.

| group | tasks | instances | evidence | rerun? |
|---|---:|---:|---|---|
| A. heap corruption in the process | 6: 8a 205–207, 8b 196–198 | 2 tiny (27770a63…, d1a8db71…; ~15 KB, all 3 seeds) | exit 134, `free(): invalid next size` / `double free or corruption`, no record | after a fix (bug, likely the C core); reproduce locally first |
| B. Glucose found no feasible start in the budget | 107: 8b 30, 8c 61, 16 7, 32 9 | 38 | record `status=ok stop_reason=glucose_timeout`, CPU ≈ 1,800 s | **no**: a real failure at the budget; `m2_results.py` does not know this stop reason and calls it infra_error (classifier fix needed) |
| C. overran budget + grace, watchdog record written | 11: 8a 29,30,317,493–495,749; 8b 681; 16 10–12 | 7 large (34 MB – 663 MB text) | `status=timeout error=watchdog_fired_at_budget+300s`, wall 2,094–3,310 s, exit 1 | no: valid failure (no target by 2,100 s); the overrun itself is a deadline-enforcement bug on big instances |
| D. overran, killed by the 1 h Slurm wall before the record | 5: 8a 28,664,748,750; 64 50 | 4 (053470870, 847b49a5, 96d20fa0, cf864e2f) | sacct TIMEOUT, no record (infra_missing) | yes, with a longer `--time` so the watchdog record lands (expected: failure) |

Part 8c: no Slurm failures (its 61 pending are all group B).

## 8. ρ before the fixes, two treatments of the errored runs (2026-10-29, user)

User: compute the statistics now, once with every errored run counted as a
memetic failure and once with them removed; the §7 fixes and reruns come later.
`scripts/mse26_rho_errors.py` runs `mse26_rho.py` unchanged; `--errors fail`
turns each infra_missing / infra_error / invalid_submission run (118 runs:
groups A, B, D) into a failure at the budget; `--errors exclude` is
`mse26_rho.py` as is (an instance with such a run is incomplete and leaves
every analysis: 44 instances, 40 EvalMaxSAT-proved, 34 weighted, mostly
job-shop 13 and shifted-* 17). Outputs `results/mse26_rho_{fail,exclude}/`
(not committed). B = 10,000, ~6 min each.

| analysis | exclude (N) | fail (N) |
|---|---|---|
| **primary** ERT ρ | **+0.635 [+0.585, +0.679]** (878) | **+0.639 [+0.590, +0.682]** (922) |
| 1 window, uncensored | +0.200 [+0.052, +0.339] (181) | +0.212 [+0.065, +0.351] (183) |
| 4 budget 900 s | +0.636 [+0.587, +0.680] | +0.640 [+0.592, +0.683] |
| 5 family-stratified | +0.635 [+0.598, +0.669] | +0.639 [+0.601, +0.673] |
| 6 partial on size | +0.572 [+0.520, +0.620] | +0.571 [+0.519, +0.620] |
| 7 PAR2, all proven | +0.634 [+0.587, +0.679] (903) | +0.636 [+0.589, +0.678] (947) |
| unweighted track | +0.623 [+0.549, +0.686] (454) | +0.621 [+0.544, +0.684] (464) |
| weighted track | +0.650 [+0.582, +0.709] (424) | +0.659 [+0.595, +0.715] (458) |

Sensitivities 2 (wall x) and 3 (flip level) equal the primary in both. D1
(seeds 4–5) not triggered in either. 2×2 (EvalMaxSAT proved / memetic reached
in ≥ 1 run): exclude 527 / 225 / 43 / 83, fail 529 / 263 / 43 / 87 (proved &
reached, proved & not, not & reached, neither). The conclusion does not depend on
the treatment.

Full tables (per family, per published solver, maps): `MSE26_RHO_PRELIM_RESULTS.md`.

## 9. Error policy and the heap-crash fix (2026-11-01, user)

> "what is to be glucoze timeout, or slrum timeout - treat them as errors legitimate in our 2 columns rho summary, document it, the memory error on small instances if can be solved - solve it. are there other error categories?" (user, 2026-11-01)

### 9.1 All outcome categories of the 2,856 tasks

From `m2_results.py pending --summary` per part (classifier of §9.3), with the
§7 groups:

| class | tasks | what it is | in ρ |
|---|---:|---|---|
| success | 1,560 | target reached, `cpu_to_target_s` ≤ 1,800 s | effort = `cpu_to_target_s` |
| budget_exhausted | 1,165 | ran to the 1,800 s budget, no target | failure, charged B (prereg) |
| target_after_budget | 2 | target reached after the budget (8a) | failure, charged B (prereg) |
| watchdog (group C) | 11 | overran budget + 300 s grace; the watchdog record says no target | failure, charged B (prereg) |
| **glucose_timeout (group B)** | **107** | **error**: `impl: hard` found no hard-feasible start in the budget (38 instances) | **error: the two columns** |
| **infra_missing (groups A, D)** | **11** | **error**: no record; 6 heap crash (A), 5 Slurm 1 h wall kill (D) | **error: the two columns** (A: fixed; workstation records, §9.6) |
| cost_mismatch, invalid_submission, infra_error, max_gens | 0 | — | — |

The EvalMaxSAT side has its own non-timeout failures, already fixed by the
prereg (§2 there): 17 memouts and 8 crashes, out of the primary population
(they enter only sensitivity 7, PAR2). No other categories exist.

### 9.2 What the two error groups are

- **Glucose timeout (group B).** For instances with hard clauses
  (`impl: hard`), every population member must first be a model of the hard
  clauses, found by Glucose (PySAT Glucose4) under random preferred phases.
  On 38 instances (107 runs) Glucose found no model at all within the
  1,800 s budget, so the evolutionary search never started. The record says
  `status=ok stop_reason=glucose_timeout`, CPU ≈ 1,800 s, cost of the
  all-False assignment. It is the solver failing at its own start-up step,
  not an infrastructure fault; the same seed would fail the same way.
- **Slurm timeout (group D).** The task's Slurm wall limit is 1 h (1,800 s
  budget + 300 s grace + reading the file). 5 runs (4 instances, 34–49 MB
  PRBAC files and one 1.2 GB planning-bnn) were still running at 1 h, so
  Slurm killed them before the shard runner wrote a record. Their sibling
  seeds either hit the time cap or wrote a late watchdog record (wall up to
  3,310 s instead of 2,100 s), so these 5 runs would almost surely have been
  failures. The overrun past budget + grace is a deadline-enforcement fault on
  big instances (the same as group C), still open.

### 9.3 Decision: both stay errors, handled by the two columns

Per the user, groups B and D are **legitimate errors**. They are **not
rerun** and are **not** turned into pre-registered failures; the two
treatments of §8 handle them:

- **`fail` column:** each such run counts as a memetic failure at the budget
  (effort B in ERT, 2B in PAR2);
- **`exclude` column:** an instance with any such run leaves every analysis.

Code (strong tree):
- `scripts/m2_results.py`: new class **`glucose_timeout`** (before, it fell
  through to `infra_error` as an unknown stop_reason). It is in the new
  `ERROR_CLASSES`, not in `PENDING_CLASSES` (never listed for a rerun) and
  not in `FINAL_FAILURES` (ERT and PAR2 stay blank, so `mse26_rho.py` treats
  the instance as incomplete).
- `scripts/mse26_rho_errors.py --errors fail` turns `PENDING_CLASSES +
  ERROR_CLASSES` runs into failures; `--errors exclude` is `mse26_rho.py` as is.
- Group D stays `infra_missing`; it is simply not resubmitted.
- The ρ numbers of §8 and `MSE26_RHO_PRELIM_RESULTS.md` do not change with
  this (checked: both treatments recomputed, the same as before, §9.5).
- Tests: `tests/test_m2_results.py::test_glucose_timeout_is_a_final_error`.

### 9.4 Group A, the heap crash: cause and fix

**Cause [verified].** Not the C core (`ls_core.c` reviewed, and an
AddressSanitizer build of it ran clean). The crash is in PySAT's Glucose4:

- The 2 instances (kbtree, 280 variables, 364 hard clauses) have **945 unit
  soft clauses on 280 variables**, so many unit soft literals repeat.
- `hard.moves.keep_sat: ks2` (auto_hparams R4 for hard instances) calls
  Glucose with the target literal **plus every satisfied unit soft literal**
  as assumptions: here up to ~945 assumptions, with repeats, for 280 variables.
- Glucose 4.1 opens one decision level per assumption, including an empty
  level for an assumption that is already true, and indexes per-level arrays
  sized by the variable count. With more levels than variables it writes past
  them and corrupts the heap. The process aborts later, at some free
  (`free(): invalid next size` / `double free or corruption`), at a random
  time: 134–1,801 s on the cluster.
- Local reproduction: the 3c task with a 10 s budget aborts 3 of 3 times
  (backtrace: `HardSAT.close` → `Glucose4.delete`). A 20-line PySAT script
  with repeated assumptions segfaults in `solve_limited`; the same calls with
  each literal once run clean.
- The instances were fetched from the MSE 2026 Zenodo zip by HTTP range reads
  (sha256 = the sidecar's), into `results/heapcrash_repro/` (not committed).

**Fix.** `src/evo/hard.py` `HardSAT.model` passes each assumption literal
once, in first-occurrence order (`dict.fromkeys`). It is the same set of
constraints, so the answer (SAT / UNSAT, the model's constraints) is
unchanged; a call without repeats is exactly the old call. Test:
`tests/test_keep_sat.py::test_model_passes_each_assumption_once`.

**Scope of the change.** Only calls with repeated assumptions differ (fewer
empty decision levels, so Glucose's search can take another path). In 3c
these are the keep_sat calls on instances with duplicate unit soft clauses.
The completed 3c records are kept as they are: each record's cost and hard
violations are re-derived from its assignment by the runner, so a run that
finished has a valid result even if Glucose overran its arrays without
crashing. Only the 6 group A tasks get new records, from the fixed code (§9.6).

**Verification [verified].** 10 s budget, both instances × seeds 1–3, twice:
12 / 12 clean (before: 3 / 3 aborted). Full 1,800 s runs of the 6 tasks
locally: 6 / 6 clean (§9.5). Full suite: 644 passed / 16 skipped.

**No cluster rerun (user, 2026-11-01).** The 6 group A records come from the
workstation runs of §9.5, which reached a result on every task (§9.6). A flat
upload for a cluster rerun was prepared and mock-tested (`tmp/upload_mse26fix/`,
`arrange_mse26fix.sh`; 3 tree files) and is **not used**. The cluster tree
still has the pre-fix `src/evo/hard.py`: any later cluster batch with
`impl: hard` and keep_sat needs this fix uploaded first.

### 9.5 Checks [verified]

- **The 6 group A tasks, fixed code, full budget, on the workstation** (not
  the cluster clock; outputs `results/heapcrash_repro/fixed1800/`, not
  committed): all 6 exit 0 with a record, hard-feasible.

  | instance | seed 1 | seed 2 | seed 3 |
  |---|---|---|---|
  | 27770a63… (opt 128) | time_cap, cost 129 | **target at 462.6 s** | time_cap, cost 129 |
  | d1a8db71… (opt 126) | time_cap, cost 127 | **target at 708.1 s** | time_cap, cost 127 |

  Process CPU to the target (`cpu_to_target_s`, ρ's clock): 428.1 s and
  669.1 s. These records enter ρ (§9.6).
- **ρ under the new classifier:** `mse26_rho_errors.py --errors fail` and
  `--errors exclude` recomputed: `instances.csv` byte-identical to
  `results/mse26_rho_{fail,exclude}/`, every number in `summary.json` the
  same; the only difference is the label of 5 runs in the `exclude`
  incomplete-instance list (`infra_error` → `glucose_timeout`).


### 9.6 The 6 group A records in ρ (workstation, no cluster rerun; user 2026-11-01)

> "I do not want rerun on cluster, if you have the optimum memetic workstation results on all missing, they are enough" (user, 2026-11-01)

The 6 workstation records of §9.5 were copied into
`results/mse26_memetic/tasks/` (2,851 shards now). The provenance, with the
sha256 of each record and of the fixed `hard.py`, is in
`results/mse26_memetic/provenance/workstation_groupA_20261101.txt`. They pass
`m2_results.py`'s manifest check (job id, seed, config, instance sha256,
budget, grace, clock). Caveats: they were run on the workstation, not the
cluster nodes, so their CPU seconds are from another machine. Their
`git_sha` field reads `1003fec` plus the uncommitted fix (committed after).
Pending now: only the 5 group D runs (8a 28, 664, 748, 750; 64 50), which stay
errors (§9.3).

**EvalMaxSAT on these 2 instances (published 2026 run).**

| instance | EvalMaxSAT | memetic (seeds 1–3) | ERT y | cell |
|---|---|---|---:|---|
| 27770a63… (opt 128) | **timeout** (not proved in 3,600 s) | 1 / 3 (seed 2, 428.1 s CPU) | 4,028 s | memetic only |
| d1a8db71… (opt 126) | **proved**, 3,131.7 s CPU (in the window) | 1 / 3 (seed 2, 669.1 s CPU) | 4,269 s | both solved |

**ρ with the 6 records.** `mse26_rho_errors.py`, both columns, outputs
`results/mse26_rho_fixA_{fail,exclude}/` (not committed); the earlier outputs
`results/mse26_rho_{fail,exclude}/` and `MSE26_RHO_PRELIM_RESULTS.md` are
left as they were.

| analysis | `fail` before → with A | `exclude` before → with A |
|---|---|---|
| **primary ERT** | +0.639 → **+0.637 [+0.588, +0.680]**, N 922 | +0.635 → **+0.634 [+0.583, +0.677]**, N 878 → 880 |
| ∞ x / y / both | 43 / 263 / 87 → 44 / 262 / 86 | 43 / 225 / 83 → 44 / 225 / 83 |
| 1 window, uncensored | +0.212 → +0.223 [+0.078, +0.362], N 183 → 184 | +0.200 → +0.211 [+0.063, +0.351], N 181 → 182 |
| 4 budget 900 s | +0.640 → +0.638 | +0.636 → +0.635 |
| 5 family-stratified | +0.639 → +0.637 [+0.600, +0.672] | +0.635 → +0.634 [+0.596, +0.669] |
| 6 partial on size | +0.571 → +0.569 | +0.572 → +0.574 |
| 7 PAR2, all proven | +0.636 → +0.635, N 947 | +0.634 → +0.634, N 903 → 905 |

Memetic-only instances: 43 → 44. Every conclusion is unchanged. D1 (seeds
4–5) is not triggered in either column.
