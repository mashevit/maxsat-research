# Provenance of `cluster_staging_maxsat_strong/`

**Created:** 2026-10-18. Design and plan:
[`docs/current2/STRONGER_MEMETIC_DESIGN.md`](../docs/current2/STRONGER_MEMETIC_DESIGN.md)
(§8.0 the base, §8.2 the steps, §8.3 the batch). Run record:
[`docs/current2/STRONG_MEMETIC_S1_RUN.md`](../docs/current2/STRONG_MEMETIC_S1_RUN.md).

**Purpose.** The staging tree of the stronger memetic, `impl: v3`:
- B1 tabu / configuration checking;
- B2 SATLike-style clause-weighting local search;
- B3 distance-aware mutation;
- B4 partition crossover;
- B5 a C polish core.

It is a **new algorithm**: its rows never share a stratum or table with v2 or
`impl: hard` rows, except the declared baseline arm. Neither
`cluster_staging_maxsat/` nor `cluster_staging_maxsat_hard/` is edited by this
work.

## Source of the copy

- **Base:** `cluster_staging_maxsat_hard/` at commit **`7c31418`** (`main`;
  clean for that tree). That is v1 / v2 / `impl: hard` (Glucose
  initialisation, repair R, feasible moves M, child-correct mutation guard,
  no-op-counting polish).
  - User decision 2026-10-18 [quote]: "I think start from copying the solver
    from _hard, that works with hard clauses also".
  - Copied: `src/`, `configs/tier2/`, `tests/`, `scripts/`
    (`tier2_memetic_array.sbatch`, `submit_m2_memetic.sh` with throttle 1000),
    `data/.gitkeep`, `results/.gitkeep`, `scripts/logs/.gitkeep`.
  - Not copied: `PROVENANCE.md`, `__pycache__`, `*.bak`.
- **Ported from `cluster_staging_maxsat/` at `7c31418`:**
  - user [quote]: "add the karnileztion and things arent in hard now";
  - `src/sat/kernel.py` and `tests/test_kernel.py`, unchanged;
  - `src/cli/run_memetic_shard.py`: the staging version (the
    `preprocess: kernel` path, schema 4), plus the hard tree's `hard` field,
    plus the v3 fields below;
  - `ls.polish_cap: time | flips_only` in `src/evo/memetic.py`;
  - `scripts/m2_results.py`, plus the v3 checks below;
  - `configs/tier2/memetic_deeppolish_p40_ls3p5_kern_v2.yaml`;
  - the six eligible calib_2sat_sc2 instances (`data/generated/calib_2sat_sc2/`,
    sha256 checked against `manifest_calib_2sat_sc2_kern.sha256`; not in git).

## Changes made at creation (2026-10-18, steps S1–S7)

| file | change |
|---|---|
| `src/evo/impl_v2.py` | `IMPLS` gains `"v3"`. Its selectors return v2's crossover and polish. |
| `src/evo/v3.py` | **new.** The v3 config with strict validation (v3 keys refused under another impl). `hard_mode: auto \| on \| off`. B3 `mutate_v3` (`count` / `walk` / `diff`, with mutate1's hard guard). B4 `partition_crossover` and `px_components`. `PolishV3` (B1 / B2 / B5 dispatch, `ls.weights: run`). `V3Stats`. |
| `src/sat/rng.py` | **new.** `MTRng` (= v2's draws) and `PortableRng` (xoshiro256\*\* / splitmix64, shared with C). |
| `src/sat/ls_v3.py` | **new.** `walksat_v3`: v2's loop plus tabu tenure / CC with aspiration and the least-recently-flipped fallback. `dls_v3`: SATLike two-mode DLS (BMS, Weighting-PMS with smoothing), optional CC, best kept on the true cost. Test-only hooks `trace` and `_debug_check`. |
| `src/native/ls_core.c`, `src/native/native.py`, `src/native/__init__.py` | **new.** B5 C twin of both cores, plus the ctypes loader. The loader refuses missing or stale builds (the source sha256 must match BUILD_INFO.txt). |
| `scripts/build_native.sh`, `scripts/build_native.sbatch` | **new.** One-off build with shell + gcc only. |
| `src/evo/memetic.py` | Merge: the hard tree's version plus `polish_cap`. v3 hooks: resolved `hard_mode`; PX with fallback and q statistics; B3 mutation (in hard mode with the child-correct guard, before repair R); sampled mutation-damage diagnostic; v3 polish (after moves M in hard mode). Result key `v3`. With no v3 key, every path is v2's (soft-only) or `impl: hard`'s (hard clauses). |
| `src/cli/run_memetic_shard.py` | Schema **5**: additive `hard`, `v3`, `native_build`. v3 configs validated before the run; `ls.native: true` without a valid build → exit 2. |
| `scripts/m2_results.py` | `ls.native` checked against the sidecar column `ls_native` (absent = false). v3 diagnostic columns in `aggregate`. |
| `scripts/make_strong_manifest.py`, `scripts/instances_calib_2sat_sc2.csv` | **new.** Batch S1: configs `configs/strong/*.yaml`, manifest, sidecar, instance hashes, upload hashes, rsync list. `--check` regenerates in memory. |
| `tests/test_ls_v3.py`, `tests/test_v3_memetic.py`, `tests/test_native.py` | **new.** See the run record §3. |
| `tests/test_walksat_v2.py`, `tests/test_kernel.py` | Two copied assertions updated for this tree: `impl: v3` is now valid (the invalid example becomes `v9`); the shard schema is 5. |

**Tests (from inside this tree):** `python -m pytest tests -q` gives **329
passed, 24 skipped**:
- 12 skips are missing MSE data (as in the hard tree);
- 12 are the C-vs-Python cases of a hard instance without no-op counting.
  Under v2's rule such a call ends only on its time limit, so a flip-budget
  equality test cannot bound it.

**Hashes:** `scripts/manifest_strong_s1.upload.sha256` lists the sha256 of every
file the cluster run needs (code, configs, scripts, manifest, instances).

## Changes after creation

### 2026-10-21: instance-aware hyperparameters, chosen at run time (`auto_hparams/1`)

User [quote]: "write preprocessing script that passes to solver optimal
hyperparameters, whether hard/soft or if small number of vars versus tens
thousands of vars and clauses", then "build the run-time version" (no
per-instance config files). Record: `docs/current2/AUTO_HPARAMS.md`.

| file | change |
|---|---|
| `src/evo/auto_hparams.py` | **new.** Rules R0–R3 with evidence tags. `resolve()` measures the instance the EA solves (kernel when the gate passes) and merges the chosen values into the config in memory; `preview()` for the workstation. |
| `src/cli/run_memetic_shard.py` | `hparams: auto` resolved after the gate, validated, time counted in the budget. Schema **6**: additive `hparams` (null otherwise). Bad `hparams` configs → exit 2. |
| `configs/strong/auto.yaml` | **new.** The one batch config (BASE + `hparams: auto`). |
| `scripts/auto_hparams.py` | **new.** `--write-base`, `--check`, preview (`--instance`, `--list`, `--map`). |
| `scripts/m2_results.py` | `hp_*` columns from the record's `hparams`. |
| `tests/test_auto_hparams.py` | **new.** 22 tests. `tests/test_v3_memetic.py`, `tests/test_kernel.py`: schema 5 → 6. |

**Tests:** 351 passed, 24 skipped.

### 2026-10-21: batch O900 (`docs/current2/ORACLE900_RUN.md`)

| file | change |
|---|---|
| `scripts/make_oracle900_manifest.py` | **new.** `--select` (per-formula selection from the staging tree's RC2 / EvalMaxSAT rows; copies instances into `data/`), then the manifest, sidecar, hashes, rsync list; `--check`. |
| `scripts/instances_oracle900.csv`, `scripts/manifest_oracle900.*`, `scripts/rsync_files_oracle900.txt` | **new.** 253 instances, 759 tasks, 299 upload hashes. |
| `data/` | 253 instances copied from `cluster_staging_maxsat/data/` (sha256-checked; not in git). |
| `tests/test_oracle_evalmaxsat.py` | The live-SIGTERM test skips on its own instance file, not on the MSE 2023 folder (this tree now stages 2 of its files). |

**Tests:** 355 passed, 20 skipped (the 4 newly running MSE-data tests pass).

### 2026-10-21: keep-satisfied moves and batch KS2 (`docs/current2/KS2_CHECK_RUN.md`)

| file | change |
|---|---|
| `src/evo/hard.py` | `hard.moves.keep_sat: none \| ks \| ks2` (moves 7–8), `HardSAT.core()`, 8 zero-by-default `HardStats` counters. Default `none` = move M exactly. |
| `src/evo/memetic.py` | passes `move_keep_sat` to `feasible_moves`. |
| `src/cli/run_memetic_shard.py` | validates `hard:` keys (`hard_cfg`) before the run. |
| `tests/test_keep_sat.py` | **new.** 14 tests. |
| `scripts/make_ks2check_manifest.py`, `configs/strong/ks2check_*.yaml`, `scripts/instances_ks2check.csv`, `scripts/manifest_ks2check.*`, `scripts/rsync_files_ks2check.txt` | **new.** 16 instances, 192 tasks, 66 upload hashes. |
| `scripts/manifest_oracle900.upload.sha256`, `scripts/rsync_files_oracle900.txt` | regenerated (src changed); `--check` and `sha256sum -c` pass. |
| `data/` | 8 more MSE 2023/2024 instances (sha256-checked; not in git). |

**Tests:** 369 passed, 20 skipped.

### 2026-10-28: target-hit counter + per-run peak RSS (milestone 3b, `docs/current2/MSE26_RHO_PLAN.md` §7–§8)

| file | change |
|---|---|
| `src/native/ls_core.c` | `ls_walksat` / `ls_dls` take `target_unsat` (−1 = off); `out[7]` = first step at which hv = 0 and unsat soft weight ≤ target (0 = start, −1 = never), `out[8]` = ns from call entry. Observed only: same flips. **Rebuild required.** |
| `src/native/native.py` | passes `target_unsat`; returns `target_hit_step`, `target_hit_wall`. |
| `src/sat/ls_v3.py` | the Python twins report the same two keys. |
| `src/evo/v3.py` | `PolishV3(..., target_unsat)`; `last_hit` after every call. |
| `src/evo/memetic.py` | `target_hit` in the result: calls/flips to target, `target_by`, resolution, time of the hit. |
| `src/cli/run_memetic_shard.py` | schema 7: `calls_to_target`, `flips_to_target`, `target_by`, `ttt_resolution`, `time_to_target_hit_s`, `peak_rss_mb`. |
| `tests/test_target_hit.py` | **new.** 18 tests. Schema asserts 6 → 7 in 3 tests. |

**Tests:** 439 passed, 16 skipped.
