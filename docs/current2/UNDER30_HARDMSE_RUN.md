# Batches U30 and HMSE: the strong solver on the under-30 s instances and on every MSE instance with hard clauses (2026-10-21)

> "write manifest for the hard clauses, and manifest for the not-run on
> memetic under 30s rc2 or EvalMaxSat, put all the new files except in needed
> dirs, like data or scripts or code, the files I dont have on cluster. make
> copy of them in some tmp folder so i can move it to mobaexterm, then I give
> you tree from there and you give me script back there to arrange them in
> folders. because I dont use rsync" (user, 2026-10-21)

**Tree:** `cluster_staging_maxsat_strong/`.
**Builders:** `scripts/make_under30_manifest.py`,
`scripts/make_hardmse_manifest.py`, and `scripts/make_flat_upload.py` for
the upload folder.
**Note:** N-2026-10-21-i.
**Status:** prepared, uploaded and verified on the cluster (`U30_OK`, `HMSE_OK`, 423 tasks); committed `0877898` (`MAXSAT_GIT_SHA=0877898`); to be submitted 2026-10-22.

## 1. Settings (both batches)

- **Config:** `configs/strong/auto.yaml`, unchanged since `abfbf88`. This is
  the `auto_hparams/2` rule set, so instances with hard clauses run at pop 10
  with `keep_sat: ks2` (R4).
- **Solver:** `impl: v3` with B1–B5, kernel gate on.
- **Runs:** 3 seeds × 900 s, stop at the target (`STOP_AT_ORACLE=1`),
  1 CPU, 8 GB, `--time 00:20:00`.
- **Code:** `src/` is byte-identical to `abfbf88`. `src/native/ls_core.c`
  is unchanged since `097efb7`, so the C core built on the cluster for O900
  (`.so` f756b70e) serves both batches. No rebuild is needed.

## 2. Batch U30: optimum proven in under 30 s [verified]

**Selection:** per formula, as in O900 (`ORACLE900_RUN.md` §2). A formula
is in if all of these hold:
- RC2 certified it, or EvalMaxSAT proved it optimal (verified), and every
  proof agrees on the cost;
- the fastest proof is **under 30 s**;
- the optimum is **> 0**;
- it has **no hard clauses**;
- it is **not in O900**.

**Result: 319 instances, 957 tasks** (`u3_<pop_idx>_s<seed>`,
`results/under30/tasks`). Every source is RC2, and no hard-clause formula
qualified. Skipped formulas:
- 253 already in O900;
- 25 that RC2 proved only in 959–3078 s (cap-3600 runs). They are outside
  both O900 and U30, so they still have no strong-solver run;
- 26 with optimum 0 (calib_a 14, calib_2sat_sc 8, calib_b 4).

RC2 times: 149 formulas under 1 s, 91 at 1–10 s, 79 at 10–30 s.

| family | instances | new to the strong solver? |
|---|---:|---|
| uuf200-860 (SATLIB) | 61 | family run in O900 |
| calib_a | 61 | family run in O900 |
| jnh (SATLIB) | 34 | **new family** |
| uuf225-960 (SATLIB) | 33 | family run in O900 |
| unsat_uuf_diff | 30 | **new family** |
| calib_2sat_sc | 29 | family run in O900 |
| calib_b | 28 | family run in O900 |
| dubois (SATLIB) | 13 | **new family** |
| calib_2sat_sc2 | 8 | family run in O900 |
| pret (SATLIB) | 8 | **new family** |
| unsat250_1000c | 7 | family run in O900 |
| bf (SATLIB) | 4 | **new family** |
| pigeon-hole | 3 | family run in O900 (hole9) |

## 3. Batch HMSE: every MSE 2023/2024 instance with hard clauses [verified]

**Selection:** every file in `data/raw/mse_2024/{mse23-uw-small,mse24-small}`
that has hard clauses and a best-known cost.
- Best-knowns come from the file's **own year's table**, never matched by
  name across years (`MSE_EVALMAXSAT_3600.md` §3).
- Excluded:
  - 17 soft-only files (the drmx-cryptogen pair ran in O900);
  - 5 files with best-known −1;
  - **3 setcover rail files** (rail507, rail516, rail582; MSE 2024).
    They do not fit in memory (§4); dropped by the user on 2026-10-21:
    "drop the 3 rail instances".

**Result: 141 instances, 423 tasks** (`hm_<pop_idx>_s<seed>`,
`results/hardmse/tasks`).

| year | proven optimum | best-known only | total |
|---|---:|---:|---:|
| MSE 2023 (unweighted) | 9 | 58 | 67 |
| MSE 2024 (weighted) | 8 | 66 | 74 |

- **Target:** the best-known cost. It is proven for 17 instances
  (`oracle_kind` proven): EvalMaxSAT s1 for 16, plus RC2 for ja-00000293.
  ja-00000385 has both proofs.
- **Best-known only:** the other 124 targets are best-knowns. The MSE 2024
  values are anytime-track bests, not optima. A run that reaches or beats
  the target stops there (`cost ≤ target`, `src/evo/memetic.py`), and
  `m2_results` counts it a success.
- **Every proof checked:** each equals its best-known, and no EvalMaxSAT
  upper bound is below one.
- **Families:**
  - **MSE 2023:**
    - judgment-aggregation 20;
    - inconsistency-measurement 19;
    - optimizing-BDDs 5;
    - reversi 4;
    - setcover 4;
    - 9 more families with 1–3 each.
  - **MSE 2024:**
    - lisbon-wedding 11;
    - synplicate 11;
    - BTBNSL 10;
    - ParametricRBACMaintenance 6;
    - judgment-aggregation 6;
    - af-synthesis 5;
    - 13 more families with 1–4 each (setcover is gone with the rail
      files).
- **Sizes:** up to 238,208 variables and 274,560 hard clauses.
- **Overlap:** the 16 KS2 instances are included. Their `ks2_10` arm is
  this config, so HMSE repeats it under the same seeds. That gives one table
  of all 141 under one config.

## 4. Smoke [verified: workstation, seed 1, real shard runner, C core]

**U30:** 24 manifest lines at 60 s each, `STOP_AT_ORACLE`. Each family
contributes its first instance and the one RC2 took longest on.
- **Result: 24/24 reached the oracle**, TTT 0.005–0.33 s, all class
  `soft_unweighted`.
- **The five new families:**
  - bf0432-007: 0.03 s;
  - dubois100: 0.01 s;
  - jnh10 and jnh302: 0.05 and 0.07 s;
  - pret150_25 and pret150_40: 0.007 s each;
  - uuf100-01 and uuf150-04: 0.02 and 0.33 s.
- **The n 16,000 calib_2sat_sc2 instances:** 0.11–0.12 s.
- **Peak memory:** at most 41 MB.

**HMSE:** all 144 instances, then 30 s each, run as one smoke batch.
- **The details are lost:** the WSL distro was shut down twice by the
  kernel OOM killer. That wiped the scratch folder holding the records;
  only the exit codes were seen before the loss.
- **141 instances** completed with exit 0 under a 2 GB per-process cap,
  with peaks of 0.2–0.7 GB where measured.
- **The 3 setcover rail instances:** `MemoryError` at the 2 GB cap.
  - Rerun alone with a 7.5 GB cap (outputs in `tmp/smoke_hmse/`), they
    reached 7.3 GB at 34–38 s and failed again with `MemoryError`.
  - A stack sample showed every byte of that growth inside the v3 static
    tables (`src/sat/ls_v3.py` `_V3Static`, the neighbour sets, ~k² per
    clause of k variables).
  - Their hard clauses have 7,753–8,919 variables, giving 0.64–1.14
    billion neighbour entries (upper bound Σ k(k−1)).
  - The next densest HMSE instance (optic, 37M) fits in 2 GB.
  - The rail instances would need tens of GB, against 8 GB per cluster
    task, so they were dropped (§3).
- **No exact solver has proved them:** EvalMaxSAT s1 timed out on rail507
  at 3600 s (best 300 vs best-known 174); the other two were not in the
  s1 sample (`rest`); RC2 never ran them.
- **A fix is possible later:** skip neighbour lists for very long
  clauses. It changes CC/PX/walk on those clauses in both cores and
  needs new equality tests.
- WSL memory facts: memory note `workstation-wsl-memory-limits`.

## 5. Cost

| batch | worst case | expected [inference] |
|---|---|---|
| U30 | 957 × 960 s = 255 CPU-h | a few CPU-h: O900's soft tasks ended in seconds |
| HMSE | 423 × 960 s = 113 CPU-h | about 90–110 CPU-h: most MSE runs reach the full 900 s (O900 MSE 23/30, KS2) |

- Both arrays fit in one wave each (`%1000`), subject to queue delay.
- The two together are 1,380 tasks, more than 1,000 running at once. Slurm
  queues the excess.

## 6. Upload (no rsync) and commands

**On the cluster** (state as of `097efb7`):
- the O900 and KS2 uploads, both verified with `sha256sum -c`;
- the `.so`.

**The upload folder:** `scripts/make_flat_upload.py` copies every needed
file whose path and hash are not in the 097efb7 O900/KS2 upload lists into
one flat folder, with `UPLOAD_MAP.tsv` (flat name, tree path, sha256).
The files were dropped straight into `~` on the cluster (the user's
`tree_depth1.txt`, 2026-10-21; all 466 present, sizes equal).
`tmp/arrange_u30_hmse.sh` moves them into the tree:
- dry run first, then `--apply`;
- it touches only the mapped names;
- it keeps replaced code as `*.bak_20261021`;
- it ends with `sha256sum -c` of both lists.

**Second upload, after the rail drop:** 7 files, `hmse2__`-prefixed, with
map `UPLOAD_MAP_hmse2.tsv` (`tmp/upload_hmse2/`).
`tmp/arrange_hmse2.sh` refuses until the first arrange is done. It
replaces the 7 HMSE files and keeps the old ones as `*.bak_hmse1`, then
checks both lists and the 423-task manifest.

Both scripts were tested in that order on a mock home: the cluster tree
at `097efb7`, the flat files and a decoy, with python blocked on PATH.

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
python3 scripts/make_flat_upload.py --out ../tmp/upload_u30_hmse \
  --need scripts/manifest_under30.upload.sha256 --need scripts/manifest_hardmse.upload.sha256 \
  --have 097efb7:scripts/manifest_oracle900.upload.sha256 --have 097efb7:scripts/manifest_ks2check.upload.sha256
# after the rail drop (the first upload's map counts as uploaded):
python3 scripts/make_flat_upload.py --out ../tmp/upload_hmse2 --prefix hmse2__ --map-name UPLOAD_MAP_hmse2.tsv \
  --need scripts/manifest_hardmse.upload.sha256 --have 097efb7:scripts/manifest_oracle900.upload.sha256 \
  --have 097efb7:scripts/manifest_ks2check.upload.sha256 --have ../tmp/upload_u30_hmse/UPLOAD_MAP.tsv
```

On the login node, after arranging (shell only):

```bash
cd ~/cluster_staging_maxsat_strong
sha256sum -c --quiet scripts/manifest_under30.upload.sha256 && echo U30_OK
sha256sum -c --quiet scripts/manifest_hardmse.upload.sha256 && echo HMSE_OK
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_hardmse.tsv OUTDIR=results/hardmse/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=0877898 MANIFEST=manifest_hardmse.tsv OUTDIR=results/hardmse/tasks bash submit_m2_memetic.sh
DRY_RUN=1 MANIFEST=manifest_under30.tsv OUTDIR=results/under30/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=0877898 MANIFEST=manifest_under30.tsv OUTDIR=results/under30/tasks bash submit_m2_memetic.sh
```

- **Dry runs on the workstation:** `sbatch --array=1-423%1000` (HMSE) and
  `--array=1-957%1000` (U30).
- **`m2_results.py pending`:** reads both manifests (423 and 957
  infra_missing on an empty directory).

Back on the workstation:

```bash
python3 scripts/m2_results.py pending --manifest scripts/manifest_<m>.tsv --outdir results/<m>/tasks --summary
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_<m>.tsv --outdir results/<m>/tasks
```

## 7. Reading (proposed)

- **U30:**
  - success rate and TTT per family;
  - the five new families (jnh, unsat_uuf_diff, dubois, pret, bf) are the
    first uses of `auto_hparams` there (all unweighted, optimum 1 on the
    files checked);
  - expected: about 100 % at the optimum, as in O900's soft part.
- **HMSE:**
  - per year and family:
    - runs at the target;
    - gap at 900 s, relative to the best-known;
    - feasibility (hv);
  - proven vs best-known targets kept apart;
  - on the 16 KS2 instances, a check against the `ks2_10` arm (26/48);
  - any run below a best-known is reported by name.
