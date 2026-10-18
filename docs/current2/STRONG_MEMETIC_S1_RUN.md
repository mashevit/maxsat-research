# Stronger memetic built (`impl: v3`, B1–B5) in `cluster_staging_maxsat_strong/`; batch S1 prepared (2026-10-18)

**Requests (user, 2026-10-18)** [quote]:
- "I want you next step implement all the ideas for stronger solver in new
  folder analogue to the cluster_staging_maxsat/_hard in 3rd folder";
- "name of folder o.k. I think start from copying the solver from _hard";
- "on cluster, compile once, I think , I think there aint no python script on
  login node, and anyhow it can be compiled in saparate job. add the
  karnileztion and things arent in hard now".

**Status:** built, tested and smoke-run on the workstation. **Committed
`16589fb`** (tree + batch). Not pushed, not submitted.
- Design: [`STRONGER_MEMETIC_DESIGN.md`](STRONGER_MEMETIC_DESIGN.md).
- Tree record: `cluster_staging_maxsat_strong/PROVENANCE.md`.
- Index: `docs/current/RESEARCH_NOTES.md`, N-2026-10-18-c.

Tags: [verified] measured or read off code here; [inference] my reading.

## 1. What was built [verified: code, tests]

- **The base:** `cluster_staging_maxsat_hard/` (Glucose, repair R, moves M),
  plus what the hard tree lacked, ported from `cluster_staging_maxsat/`: the
  kernel path (schema 4), `polish_cap`, `m2_results.py` and the instances.
- **`impl: v3`** (`src/evo/v3.py`). Every component is an opt-in key:

| component | keys | module |
|---|---|---|
| hard machinery only with hard clauses | `hard_mode: auto` (default) / `on` / `off` | `evo/v3.resolve_hard_mode` |
| B1 tabu / configuration checking | `ls.tabu: none \| tenure \| cc`, `ls.tabu_tenure`, `ls.tabu_tenure_rand` | `sat/ls_v3.walksat_v3` (CC also in `dls_v3`) |
| B2 clause-weighting DLS (SATLike two-mode) | `ls.core: dls`, `ls.dls_t / dls_sp / dls_zeta / dls_h_inc`, `ls.weights: call \| run` | `sat/ls_v3.dls_v3` |
| B3 distance-aware mutation | `ea.mutation: rate \| count \| walk \| diff`, `ea.mutation_k` | `evo/v3.mutate_v3` |
| B4 partition crossover | `ea.crossover: px`, `ea.px_min_q`, `ea.px_fallback` | `evo/v3.partition_crossover` |
| B5 C core | `ls.native: true` | `src/native/ls_core.c`, `native.py` |

- **Diagnostics per shard** (schema 5, field `v3`):
  - the resolved `hard_mode` and the polish core;
  - the mean mutation damage (unsatisfied weight added by one mutation,
    sampled every 10th child);
  - PX calls, component count q (mean, max, histogram), fallbacks, children
    equal to a parent;
  - DLS stuck events, smoothings and CC blocks;
  - tabu skips and fallbacks;
  - `ls_native`, and `native_build` (gcc version, source and `.so` sha256).

### 1.1 Deviations from the design, and why

1. **CC is allowed in the DLS core; a fixed tenure is not** (design §6.2).
   The §2.5 sketch had excluded tabu from DLS entirely, but §6.2 and the §8.3
   table both use CC with DLS. Rule in `dls_v3`: BMS draws whose
   configuration has not changed are skipped; if all are blocked, the best
   draw is taken anyway. The same rule applies in the stuck branch.
2. **B5 is in batch S1 as its own arm (`allC`)** rather than compared after
   the reading.
   - gcc 11.5 is on the cluster (user, 2026-10-18);
   - `allC` is compared only with `all` (Python), the same algorithm;
   - 36 extra tasks.
3. **The C core is built once per tree** (user): `scripts/build_native.sbatch`
   on a compute node, or `scripts/build_native.sh` on the login node (gcc
   only, no Python).
   - Each task loads the prebuilt `.so`.
   - `src/native/native.py` refuses a missing or stale build (the source
     sha256 must match BUILD_INFO.txt).
   - The shard runner then exits 2 before the run, so no `allC` task can
     silently fall back to Python.
4. **Equality of the C core is tested only where a flip budget bounds the
   call.** A hard instance without no-op counting ends only on its time
   limit (v2's rule), so those 12 parametrisations are skipped. In the EA,
   hard mode always counts no-ops.
5. **Two speed changes with identical decisions**, both guarded by the
   exactness tests (§3):
   - PX accumulates per-component costs in one marked pass over the clauses
     (was a `set` per component);
   - the DLS initial scores are computed inline.

## 2. Measurements [verified: workstation, 12 cores]

### 2.1 One polish call, random start, raw s251 (n 16,000, c\* 12)

| core | flips/s | unsatisfied after 200k flips |
|---|---:|---:|
| v2 WalkSAT (Python) | 551k | 41 |
| v3 WalkSAT + CC (Python) | 385k | 23 |
| v3 DLS + CC (Python) | 109k | 14 |
| WalkSAT (C) | 4,587k | 40 |
| WalkSAT + CC (C) | 4,406k | 25 |
| DLS + CC (C) | 2,555k | 13; **12 = c\*** after 4M flips (1.6 s) |

- A single DLS call from a random start reaches the optimum of raw s251.
  Earlier, the v2 memetic stayed 10 or more above it at 900 s (m2v2: 0/18).
- **Speed:** C is 8× v2's Python WalkSAT and 23× the Python DLS. Cluster
  speeds will differ: v2 ran at 180k–380k flips/s there.

### 2.2 Smoke: 36 shards through the real shard runner

Setup: 60 s, seed 1, stop at c\*, 10 in parallel, the S1 configs `base`,
`all` and `allC`, raw and kernel. Cells give final cost / c\*; time to target
in parentheses.

| instance (c\*) | base raw | all raw | allC raw | base kern | all kern | allC kern |
|---|---:|---:|---:|---:|---:|---:|
| s251 (12) | 22 | 13 | 13 | 12 (0.7 s) | 12 (1.7 s) | 12 (0.8 s) |
| s253 (14) | 22 | 19 | 16 | **15** | **15** | **14 (5.8 s)** |
| s255 (13) | 23 | 14 | 14 | 13 (1.1 s) | 13 (1.1 s) | 13 (0.5 s) |
| s256 (13), n 64k | 84 | 44 | **13 (53.8 s)** | 13 (2.1 s) | 13 (3.3 s) | 13 (1.8 s) |
| s257 (10), n 64k | 91 | 30 | **10 (48.2 s)** | 10 (1.0 s) | 10 (3.3 s) | 10 (1.6 s) |
| s258 (9), n 64k | 46 | 20 | 10 | 9 (0.8 s) | 9 (3.4 s) | 9 (1.4 s) |

- **Kernel:** `allC` is the first configuration to solve s253 (5.8 s), the
  case the v2 memetic missed by 1 at every budget so far.
- **Raw:**
  - `base` is 10–81 above c\*;
  - `all` is 1–31 above;
  - `allC` reaches c\* on two n 64,000 instances in under a minute and is 1–2
    above on the other four.
- **Mutation damage** (mean unsatisfied clauses added by one mutation):
  - fixed rate: 198–199 at n 16k, 622–644 at n 64k;
  - walk with k 16: 6.5–12.4.
  - B3 removes the effect measured on 10-14 (directions §9.1).
- **PX components:**
  - raw: mean q 446–11,190 per call;
  - kernel: 12–80;
  - fallbacks (q < 2) on 0–4% of calls.
  - The sparse raw graph splits into thousands of independent parts, as the
    design expected.
- **Children per 60 s:** the Python `all` arm makes 38–98 (DLS and PX in
  Python). After the §1.1 speed changes, a 15 s check on raw s256 gave:

  | arm | children / 15 s | final cost |
  |---|---:|---:|
  | `base` | 159 | 97 |
  | `all` | 44 | 24 |
  | `allC` | 152 | **13 = c\*** |

- **[inference] What the smoke suggests:**
  - search quality comes mainly from B2 + B3 (walk mutation, DLS);
  - B5's speed turns that into solved instances within the budget.
  - The leave-one-out batch is what can attribute the gain, with 3 seeds and
    900 s.

## 3. Tests [verified]

From inside the tree: **329 passed, 24 skipped.** The 24 skips are 12 missing
MSE data files and the 12 unbounded cases of §1.1(4).

- **`tests/test_ls_v3.py` (76):**
  - `walksat_v3` with tabu "none" equals `walksat_polish_v2` exactly
    (soft-only, weighted, hard, no-ops on/off, three noise levels);
  - the tenure and CC rules hold on every "free" flip (traced);
  - DLS incremental scores, decreasing set and falsified lists equal a full
    recomputation after every flip and weight update;
  - the DLS returned best is the true cost;
  - tiny instances reach the brute-force optimum;
  - feasible starts stay feasible;
  - run-level weights update in place, bounded by ζ;
  - the CC variant is exact too.
- **`tests/test_v3_memetic.py` (43):**
  - **v3 without keys equals `cluster_staging_maxsat`'s `impl: v2`**, run in a
    subprocess against that tree;
  - v3 equals `impl: hard` on a hard instance (all fields except timings);
  - `hard_mode` resolution, and 9 invalid configs refused;
  - B3 flips exactly k (count, diff); the walk set is connected; the hard
    guard never breaks a satisfied clause;
  - B4 components are exact (each clause's differing variables in one
    component); the **child equals the best of all 2^q recombinations**
    (brute force, with and without hard clauses) and is never worse than
    either parent;
  - end to end with every component on (soft-only and hard);
  - the target stop works;
  - the shard records schema 5 and refuses v3 keys under v2.
- **`tests/test_native.py` (63 run):**
  - RNG streams equal;
  - **the C cores equal the Python twins** for WalkSAT (tabu none / tenure /
    tenure + random / CC) and DLS (CC off/on; three parameter sets; run
    weights): same assignment, step and flip counts, best cost and counters;
  - stale and missing builds are refused;
  - the shard runs `ls.native` with a build and exits 2 without one.
- **Login-node scripts with `python`/`python3` tripwires on PATH:**
  `build_native.sh` builds; `submit_m2_memetic.sh` DRY_RUN prints
  `--array=1-324%1000`.
- **`m2_results.py`** classifies the 60 s smoke shards as
  `invalid_submission` (budget 60 ≠ 900): the identity checks fire.

## 4. Batch S1 [verified: built, dry-run]

- **Generated by** `scripts/make_strong_manifest.py`, which reproduces every
  file byte for byte (`--check`).
- **Size:** 9 arms × {raw, kern} × 6 instances × seeds 1–3 = **324 tasks**.
- **Settings:** 900 s; stop at c\*; deadline clip; 1 CPU, 8 GB,
  `--time 00:20:00`.
- **Job ids:** `st_<arm>_<r|k>_<NN>_s<seed>`.
- **Output:** `results/strong_s1/tasks`.

| arm | B1 | B2 | B3 | B4 | B5 | question |
|---|---|---|---|---|---|---|
| base | — | — | — | — | — | = v2 (+ kernel on kern) |
| all | cc | dls | walk 16 | px | — | the full solver (Python) |
| noB1 | — | dls | walk 16 | px | — | leave-one-out |
| noB2 | cc | — | walk 16 | px | — | leave-one-out (WalkSAT + CC) |
| noB3 | cc | dls | rate | px | — | leave-one-out |
| noB4 | cc | dls | walk 16 | clause-aware | — | leave-one-out |
| B3only | — | — | walk 16 | — | — | design §6.1 |
| wccB3 | cc | — | walk 16 | — | — | design §6.2 |
| allC | cc | dls | walk 16 | px | C | B5, compared with `all` |

- **DLS values for this batch** (SATLike's published t and sp; ζ from design
  §3.3): t 15, sp 0.01, ζ 50, h_inc 1, weights per call.
- **Cost:**
  - worst case 324 × 960 s = **86.4 CPU-h**;
  - one wave at %1000; queue delay is separate;
  - expected [inference from the smoke] about 45–50 CPU-h. Most raw tasks use
    the full 900 s; kernel tasks end in seconds except s253 on the Python
    arms.
- **Pre-registered reading** (design §8.3):
  - success = c\* within 900 s, with the kernel time included;
  - per arm, variant and instance: successes / 3, median TTT, the gap;
  - plus the `v3` diagnostics.
  - A component helps if removing it lowers successes or raises TTT on at
    least 2 of the 6 instances, in both raw and kernel or in the variant §6
    predicts.
  - `allC` vs `all`: the speed effect alone.

### 4.1 Upload

- **Destination:** a new tree on the cluster, `~/cluster_staging_maxsat_strong/`.
- **List:** `scripts/rsync_files_strong_s1.txt` (67 paths): all of `src/`
  (with `ls_core.c`), the 18 configs, the driver, submit, build and results
  scripts, the manifest, and the six instances (4.4 MB).
- **Check:** `scripts/manifest_strong_s1.upload.sha256` proves the cluster
  copy.
- **Not uploaded:** the `.so`. It is built on the cluster.

### 4.2 Commands

On the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_strong_s1.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_strong/
```

On the login node (shell only). Check the upload, then build the C core once
(a compute-node job):

```bash
cd ~/cluster_staging_maxsat_strong
sha256sum -c --quiet scripts/manifest_strong_s1.upload.sha256 && echo UPLOAD_OK
cd scripts && mkdir -p logs
sbatch build_native.sbatch
# when it has finished:
cat logs/build-native-*.out            # expect BUILD_OK and compiler=gcc (GCC) 11.5.0 ...
```

Then submit (dry run first):

```bash
cd ~/cluster_staging_maxsat_strong/scripts
DRY_RUN=1 MANIFEST=manifest_strong_s1.tsv OUTDIR=results/strong_s1/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=16589fb MANIFEST=manifest_strong_s1.tsv OUTDIR=results/strong_s1/tasks bash submit_m2_memetic.sh
```

- Without a build, the 36 `allC` tasks exit 2 and show as `infra_missing`.
  Resubmit them with `IDS=` after building.
- `bash build_native.sh` on the login node is the alternative to the job:
  gcc only, under a second.

Back on the workstation, after the array:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_strong/results/strong_s1/ results/strong_s1/
~/.venvs/maxsat/bin/python scripts/m2_results.py pending --manifest scripts/manifest_strong_s1.tsv --outdir results/strong_s1/tasks --summary
~/.venvs/maxsat/bin/python scripts/m2_results.py aggregate --manifest scripts/manifest_strong_s1.tsv --outdir results/strong_s1/tasks
# resume only infra/invalid ids (login node):
IDS=<ids> RESUME=1 MAXSAT_GIT_SHA=16589fb MANIFEST=manifest_strong_s1.tsv OUTDIR=results/strong_s1/tasks bash submit_m2_memetic.sh
```

### 4.3 Relation to the pending kern batch (`cluster_staging_maxsat/`, 18 tasks)

- It is already uploaded and verified (`KERNEL_MEMETIC_RUN.md` §4.1).
- S1's `base_kern` arm is the same algorithm (v3 without keys = v2, plus the
  kernel), from the new tree. Submitting both gives a cross-tree check;
  either alone is enough for the reading.
