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
