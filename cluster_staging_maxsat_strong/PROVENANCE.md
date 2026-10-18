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
