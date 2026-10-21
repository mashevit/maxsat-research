# Batch O900: the strong solver on every instance with an optimum proven within 900 s (2026-10-21)

> "strong solver only, instances rc2 is above 30s, kernel on, prepare with
> oracle on, manifest for instances we have oracle in 900s, from rc2 or
> evalmaxsat" (user, 2026-10-21)

**Tree:** `cluster_staging_maxsat_strong/`. **Builder:**
`scripts/make_oracle900_manifest.py`. Note N-2026-10-21-c. Status:
**prepared and verified, not submitted.**

## 1. Settings

- **Solver:** `configs/strong/auto.yaml`, the only config.
  - `impl: v3` with B1–B5: CC, DLS, walk mutation, PX, C core.
  - Kernel gate on.
  - `hparams: auto`: each job chooses its values at run time
    (`docs/current2/AUTO_HPARAMS.md`).
- **Runs:** 3 seeds × 900 s, stop at the oracle (`STOP_AT_ORACLE=1`), 1 CPU,
  8 GB, `--time 00:20:00`.
- **Job ids:** `oa_<pop_idx>_s<seed>`. **Output:** `results/oracle900/tasks`.

## 2. Selection [verified]

Rules apply **per formula**, not per file. Copies are matched on the parsed
clauses, so a normalised SATLIB file and an older raw copy count as one
instance. RC2's fastest certified run on any copy decides the screen. The
`data/satlib_bench` copy is the one run.

1. **RC2:** certified (completed and cost = lower bound), with the fastest
   certified run in **[30 s, 900 s)**. All certified runs must agree on the
   cost.
2. **EvalMaxSAT (MSE s1, 3600 s cap):** optimal and verified in **< 900 s**,
   unless RC2 certified the formula in < 30 s. Where both proved an
   optimum, they agree.

**Result: 253 instances, 759 tasks.**
- **Source:** RC2 243, EvalMaxSAT 9, both 1 (ja-385, 37 = 37).
- **RC2 time:** 64 at 30–60 s, 137 at 60–300 s, 49 at 300–900 s (before
  the formula dedupe).
- **No instance has optimum 0.** 11 instances have extra copies, which are
  not run.
- **Duplicates found while building:**
  - 4 uuf200 formulas appeared twice, as a SATLIB file and an older raw copy
    with different bytes;
  - 2 more (uuf200-06, -09) were picked from the raw copy at 31–36 s,
    although RC2 needs only 25.9–29.7 s on the SATLIB copy.
  - Both are fixed by the per-formula rule.

| family | instances |
|---|---:|
| uuf250 (`data/unsat250_1000c`) | 71 |
| uuf225-960 (SATLIB) | 60 |
| calib_b (3-SAT, generated) | 53 |
| uuf200-860 (SATLIB) | 34 |
| calib_a (generated) | 17 |
| MSE 2024 (weighted, 7 with hard clauses) | 8 |
| calib_2sat_sc2 (sparse Max-2-SAT, kernelised) | 6 |
| MSE 2023 (hard clauses) | 2 |
| calib_2sat_sc, pigeon-hole (hole9) | 1 + 1 |

Instances were copied into this tree's `data/` (same relative paths, 25 MB)
and are checked by sha256.

## 3. Smoke [verified: workstation, seed 1, 60 s, real shard runner, C core]

Smoke run on 94 manifest lines, made before the formula dedupe; the
instances are the same.

- **84 soft instances** (uuf200/225/250, hole9, calib_a/b,
  calib_2sat_sc/sc2): **84/84 reached the oracle**, in 0.02–3.7 s,
  kernel time included.
  - Run-time choices: k 4–16, ζ 50.
  - Calib_b has only 1 instance in the smoke, so its 53 instances are the
    least covered.
- **10 MSE instances:** 3/10 reached the oracle in 60 s: ja-385 at 27 s,
  causal-discovery at 31 s, and ja-maxham. All 10 stayed feasible (hv 0).
  - **lisbon-wedding** (205k clauses, 204,985 hard): every 3.5 s slot went
    to feasible moves M (758 calls, 44.7 s). The B1–B5 polish made 0 flips.
    The improvement 578 → 446 (oracle 395) comes from the hard-tree
    machinery alone. This is by design (M first, polish on the rest), but on
    such instances the strong solver is the hard-tree solver.
  - drmx-cryptogen (soft weighted, the untested rule): 847–849 against 800.

## 4. Cost

- **Worst case:** 759 × 960 s = **202 CPU-h**. One wave at %1000; queue
  delay is separate.
- **Expected [inference from the smoke]:**
  - soft tasks mostly end in seconds;
  - the 30 MSE tasks, plus any hard calib_b ones, run toward the full
    900 s;
  - roughly 10–30 CPU-h.

## 5. Upload and commands

**Upload:**
- List: `scripts/rsync_files_oracle900.txt` (299 paths): all of `src/` with
  `ls_core.c`, `configs/strong/auto.yaml`, the driver, submit, build and
  results scripts, the manifest files, and the 253 instances.
- Check: `scripts/manifest_oracle900.upload.sha256`.
- The `.so` is built on the cluster. **It has never been built there**: S1
  was not submitted.

**Committed and pushed 2026-10-21 as `097efb7`** (`MAXSAT_GIT_SHA=097efb7`).
Verified on the workstation:
- `make_oracle900_manifest.py --check` OK;
- `sha256sum -c` of the upload list OK;
- `DRY_RUN=1` submit: 253 instances match, array 1-759 %1000;
- `m2_results.py pending` reads the manifest: 759 infra_missing on an empty
  directory;
- tests: 355 passed / 20 skipped.

On the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_oracle900.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_strong/
```

On the login node (shell only):

```bash
cd ~/cluster_staging_maxsat_strong
sha256sum -c --quiet scripts/manifest_oracle900.upload.sha256 && echo UPLOAD_OK
cd scripts && mkdir -p logs
sbatch build_native.sbatch            # once per tree; wait for it to finish
cat logs/build-native-*.out           # expect BUILD_OK and gcc 11.5.0
DRY_RUN=1 MANIFEST=manifest_oracle900.tsv OUTDIR=results/oracle900/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=097efb7 MANIFEST=manifest_oracle900.tsv OUTDIR=results/oracle900/tasks bash submit_m2_memetic.sh
```

- Without the build, every task exits 2 (`ls.native: true` with no `.so`)
  and shows as `infra_missing`. Build, then resubmit with `IDS=`.

Back on the workstation, after the array:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_strong/results/oracle900/ results/oracle900/
python3 scripts/m2_results.py pending --manifest scripts/manifest_oracle900.tsv --outdir results/oracle900/tasks --summary
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_oracle900.tsv --outdir results/oracle900/tasks
# resume only infra/invalid ids (login node):
IDS=<ids> RESUME=1 MAXSAT_GIT_SHA=097efb7 MANIFEST=manifest_oracle900.tsv OUTDIR=results/oracle900/tasks bash submit_m2_memetic.sh
```

## 6. Reading (proposed)

- **Per instance:** successes / 3 and median TTT, with the run-time choice
  (`hp_*` columns).
- **Per family:**
  - success rate;
  - TTT against RC2's time, and against EvalMaxSAT's where it exists.
    These are different solvers on different nodes; the seconds are
    descriptive, not a race.
- **MSE:** the gap at 900 s, the slot split M vs polish (`hard`), and
  feasibility.
- **Not in this batch:** an EvalMaxSAT 900 s run on the 243 RC2-only
  instances. It is needed for an EvalMaxSAT comparison on the whole set.
