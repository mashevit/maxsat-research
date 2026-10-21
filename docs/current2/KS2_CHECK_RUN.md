# Batch KS2: keep-satisfied SAT moves against today's move, on 16 MSE instances (2026-10-21)

> "prepare me ks2 check for cluster" (user, 2026-10-21)

**Tree:** `cluster_staging_maxsat_strong/`. **Builder:**
`scripts/make_ks2check_manifest.py`. Motivation: N-2026-10-21-d (lisbon
experiments). Notes N-2026-10-21-e, N-2026-10-21-g (readout). Status: **submitted and read
2026-10-21 (§6): ks2_10 vs m10 13/0; rule not met at pop 40 (3 worse).**

## 1. What was built [verified: code, tests]

- **`hard.moves.keep_sat: none | ks | ks2`** (`src/evo/hard.py`, moves 7–8).
  When the drawn unsatisfied soft clause is a unit:
  - `ks`: assume its literal together with every currently satisfied unit
    soft literal. A model keeps all of them, so with only unit soft clauses
    the move strictly lowers the cost.
  - `ks2`: on UNSAT, read Glucose's core over the assumptions. If the target
    is in it, retry once without the kept literals the core names.
  - Otherwise, fall back to today's move M unchanged. Acceptance is M's rule
    (a non-unit soft clause is not kept and can still break).
  - **Default `none`** = M exactly: same run, same RNG draws (tested).
  - New zero-by-default counters in the record's `hard` field: `ks_calls`,
    `ks_sat`, `ks_unsat`, `ks_budget`, `ks_core_len_sum`, `ks2_retries`,
    `ks2_sat`, `ks_fallbacks`.
- **The shard runner validates `hard:` keys before the run** (exit 2 on a
  bad value).
- **Tests:** `tests/test_keep_sat.py`, 14 tests; suite 369 passed / 20
  skipped. They check:
  - config validation;
  - a ks model is feasible, satisfies the target and keeps every satisfied
    unit;
  - ks2 finds through the core a model that ks cannot (a two-variable
    instance);
  - moves never get worse and stay feasible;
  - `none` gives byte-identical runs;
  - end to end through the shard runner;
  - a bad value is refused.
- **In-tree check against the scratch patch** (lisbon 9-18, 120 s, pop 10):
  ks2 400 against M 423, with the same counter pattern as the scratch runs.
  The scratch script is superseded.

## 2. Batch [verified: built, dry-run]

- **Instances:** every EvalMaxSAT s1 row (MSE 2023/2024, 3600 s cap) that is
  `optimal`, verified, and has hard clauses.
  - 16 instances, each equal to its year's best-known; EvalMaxSAT proved
    them in 116–3476 s.
  - The 2 soft-only drmx-cryptogen instances are excluded: no moves there.
  - 8 of the 16 are also in batch O900 (the < 900 s ones).
- **Arms (2 × 2):** move {M, ks2} × population {40, 10}:
  - `m40` = `configs/strong/auto.yaml`;
  - `m10`, `ks2_40`, `ks2_10`: `configs/strong/ks2check_<arm>.yaml`.
  - Everything else is the auto config: B1–B5, kernel gate,
    `hparams: auto`.
- **Runs:** 16 × 4 × seeds 1–3 = **192 tasks**, 900 s, stop at the optimum,
  1 CPU, 8 GB, `--time 00:20:00`.
- **Job ids and output:** `k2_<arm>_<kNN>_s<seed>`; `results/ks2check/tasks`.
- **Cost:** worst case 192 × 960 s = **51.2 CPU-h**. Expected [inference
  from the smoke]: about 35–45 CPU-h, because most of these instances run
  the full budget.

| k | instance (year) | optimum | EvalMaxSAT s |
|---|---|---:|---:|
| k01 | bcp-SU3 simp-genos.haps.9 (23) | 106 | 1836 |
| k02 | gen-hyper-tw GenHyperTW_b01 (23) | 5 | 3476 |
| k03 | inconsistency-measurement im-contension-B-3 (23) | 63 | 1055 |
| k04 | judgment-aggregation ja-maxham-00000385 (23) | 37 | 145 |
| k05 | mbd-b14 C-mbd14-0277 (23) | 24 | 583 |
| k06 | min-fill MinFill_R0_myciel5 (23) | 196 | 3317 |
| k07 | optimizing-BDDs australian-credit (23) | 87 | 1598 |
| k08 | scheduling cnf_small (23) | 28 | 2036 |
| k09 | MaxSATQueries compas_train_2 (24) | 31514 | 202 |
| k10 | af-synthesis stb_50_40_8 (24) | 117 | 2451 |
| k11 | causal-discovery Bands_6_277 (24) | 91349 | 327 |
| k12 | judgment-aggregation ja-kemeny-00000353 (24) | 554 | 603 |
| k13 | lisbon-wedding 9-18 (24) | 395 | 116 |
| k14 | metro 8_8_5_20_10_6_500_1_3 (24) | 138 | 967 |
| k15 | preference_planning pathways_p16 (24) | 257 | 498 |
| k16 | quantum-circuit qgan_6_15 (24) | 24 | 335 |

## 3. Smoke [verified: workstation, `ks2_10`, 60 s, seeds 1–3, real shard runner, C core]

- **48/48 runs ok, all feasible (hv 0).** Peak memory 57 MB – 1.6 GB, the
  largest on af-synthesis.
- **Optimum reached in 60 s:** bcp 3/3, causal 3/3, ja-maxham 2/3, mbd
  2/3, preference 2/3, scheduling 1/3, quantum 1/3.
- **Close:** lisbon 399–407 (395), BDDs 89–93 (87), metro 139–189 (138),
  inconsistency 69–72 (63).
- **Far:** min-fill 284–307 (196), gen-hyper-tw 9–19 (5), af-synthesis
  130–142 (117; 1–2 children per minute), ja-kemeny 574–590 (554),
  MaxSATQueries 43,875 (the start).
- **ks is not used** where no soft clause is a unit (BDDs: 0 ks calls) or
  where few are (preference: 2). There the run is M.

## 4. Upload and commands

**Upload:**
- List: `scripts/rsync_files_ks2check.txt` (66 paths): `src/`, the 4
  configs, the scripts, the manifest files, the 16 instances.
- Check: `scripts/manifest_ks2check.upload.sha256`.
- This shares `src/` with batch O900. Its upload hashes were refreshed after
  this change, and both checks pass.
- **Committed and pushed 2026-10-21 as `097efb7`.** Build the C core once if
  O900 has not done it.

On the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_ks2check.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_strong/
```

On the login node (shell only):

```bash
cd ~/cluster_staging_maxsat_strong
sha256sum -c --quiet scripts/manifest_ks2check.upload.sha256 && echo UPLOAD_OK
cd scripts && mkdir -p logs
sbatch build_native.sbatch            # once per tree (skip if already built for O900)
cat logs/build-native-*.out           # expect BUILD_OK
DRY_RUN=1 MANIFEST=manifest_ks2check.tsv OUTDIR=results/ks2check/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=097efb7 MANIFEST=manifest_ks2check.tsv OUTDIR=results/ks2check/tasks bash submit_m2_memetic.sh
```

Back on the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_strong/results/ks2check/ results/ks2check/
python3 scripts/m2_results.py pending --manifest scripts/manifest_ks2check.tsv --outdir results/ks2check/tasks --summary
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_ks2check.tsv --outdir results/ks2check/tasks
```

## 5. Pre-registered reading

- **Per instance and arm:**
  - successes / 3;
  - median TTT (non-successes count as > 900 s);
  - median final cost and gap to the optimum.
- **KS2 effect:**
  - compare `ks2_10` with `m10`, and `ks2_40` with `m40`, instance by
    instance;
  - "better" = more successes, else a lower median final cost, else a lower
    median TTT;
  - **KS2 helps** if it is better on ≥ 6 of the 16 and worse on ≤ 2, at
    both population sizes.
- **Population effect:** the same rule, `m10` against `m40` and `ks2_10`
  against `ks2_40`.
- **Diagnostics:** ks hit rate (`ks_sat / ks_calls`), ks2 retry success,
  fallbacks, children per run.
- **If KS2 helps:** `hparams: auto` would set `keep_sat: ks2` (and
  population 10 if that effect holds too) on instances with hard clauses.
  That change waits for the readout and the user's go.

## 6. Readout (2026-10-21) [verified: 192 shard records]

**Run:** Slurm job submitted 2026-10-21 11:47 UTC, `MAXSAT_GIT_SHA=097efb7`,
using the C core built for O900. Results were copied to
`results/ks2check/` (untracked).

**Integrity:**
- 192/192 `ok`, all feasible (hv 0), none below the optimum.
- Maximum wall time 900.4 s.
- 75 runs reached the optimum (target); 117 hit the time cap.
- `m2_results.py aggregate` has the same `analysis_group` crash as O900; the
  numbers come from a scratch script.

**Per instance** (best cost for seeds 1–3, and the median TTT in s where at
least 2 of 3 runs reached the optimum):

| k | instance | opt | m40 | m10 | ks2_40 | ks2_10 |
|---|---|---:|---|---|---|---|
| k01 | bcp-SU3 | 106 | 3/3, 314 s | 3/3, 136 s | 3/3, 15 s | 3/3, 11 s |
| k02 | gen-hyper-tw | 5 | 7, 8, 9 | 8, 8, 7 | 7, 6, 6 | 7, 7, 6 |
| k03 | inconsistency-measurement | 63 | 76, 75, 77 | 73, 73, 78 | **65, 64, 65** | **65, 64, 64** |
| k04 | ja-maxham | 37 | 1/3 | 1/3 | 1/3 | **3/3, 8 s** |
| k05 | mbd-b14 | 24 | 31, 28, 30 | 33, 26, 28 | **3/3, 91 s** | **3/3, 20 s** |
| k06 | min-fill | 196 | 210, 201, 198 | 204, 214, 207 | 206, 217, 219 | 196, 197, 197 (1/3) |
| k07 | optimizing-BDDs | 87 | 89, 87, 89 | 89, 89, 89 | 89, 87, 89 | 89, 89, 89 |
| k08 | scheduling | 28 | 30, 31, 28 | 3/3, 365 s | **3/3, 34 s** | **3/3, 62 s** |
| k09 | MaxSATQueries | 31514 | 31589, 38827, 43158 | 43875 ×2, 43743 | 43875, 38812, 43159 | 43875 ×3 |
| k10 | af-synthesis | 117 | 123, 117, 120 | 120, 120, 123 | **3/3, 276 s** | **3/3, 408 s** |
| k11 | causal-discovery | 91349 | 3/3, 15 s | 3/3, 11 s | 3/3, 7 s | 3/3, 8 s |
| k12 | ja-kemeny | 554 | 556, 554, 556 | 558, 556, 562 | 556, 560, 564 | 556, 554, 556 |
| k13 | lisbon-wedding 9-18 | 395 | 401, 410, 406 | 405, 405, 401 | 397, 396, 396 | 396, 396, 396 |
| k14 | metro | 138 | 139, 152, 140 | 138, 139, 156 | **3/3, 210 s** | 139, 152, 138 |
| k15 | preference_planning | 257 | 275, 275, 257 | 257, 275, 257 | 275, 275, 257 | 257, 275, 257 |
| k16 | quantum-circuit | 24 | 39, 39, 39 | 54, 39, 30 | **3/3, 153 s** | **3/3, 28 s** |

**Successes out of 48:** m40 12, m10 13, ks2_40 24, ks2_10 26.

**Pre-registered rule (§5):** better/worse counts instance by instance.

| comparison | better | worse | tie | worse on |
|---|---:|---:|---:|---|
| ks2_10 vs m10 | 13 | 0 | 3 | — |
| ks2_40 vs m40 | 10 | 3 | 3 | min-fill, MaxSATQueries, ja-kemeny |
| m10 vs m40 | 8 | 5 | 3 | min-fill, BDDs, MaxSATQueries, af-synthesis, ja-kemeny |
| ks2_10 vs ks2_40 | 8 | 7 | 1 | — |

- **KS2 helps: rule NOT met as written.**
  - Pop 10 passes clearly (13 / 0).
  - Pop 40 fails on one count: 3 worse against the allowed 2.
  - Of the 3 at pop 40:
    - MaxSATQueries stays at or near its Glucose start in every arm (best
      31,589, otherwise 38–44k), so its ordering is noise;
    - min-fill (206 vs 201) and ja-kemeny (556/560 vs 556/554) are small
      losses.
- **Population effect: none by the rule**, either with M or with ks2.
- **[verified]** Where ks is inactive the arms are the same algorithm:
  - BDDs: 0 ks calls;
  - preference_planning: 6 ks calls, all fallbacks;
  - at pop 40 both instances gave identical best costs under M and ks2.
- **Diagnostics** (sums over 3 seeds):
  - ks hit rate is 0.2–0.6 on the instances it unlocks: mbd, quantum,
    bcp, af-synthesis, scheduling. The ks2 retry succeeds 0.5–1.0 there.
  - Where ks2 reaches the optimum, it does so with far fewer children: 11–55
    on bcp, mbd and scheduling, against 250–900 under M. Each move does
    more.
  - It hits only 0.03–0.10 where it does not help: lisbon, kemeny, causal,
    inconsistency. Most calls there fall back to M (fallback share
    0.64–0.90), yet lisbon and inconsistency still improve.
- **Post-hoc [inference, not the pre-registered test]:**
  - ks2_10 against today's default m40 is 13 better / 2 worse (BDDs, where
    ks is inactive, and MaxSATQueries).
  - Setting `keep_sat: ks2` with pop 10 for hard-clause instances in
    `hparams: auto` is the change §5 anticipated.
  - Because the rule failed at pop 40 by one instance, this is the user's
    call. MaxSATQueries (stuck at the start in all arms) and min-fill are
    the open cases.
