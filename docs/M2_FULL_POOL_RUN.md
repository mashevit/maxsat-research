# M2 full pool: pop 40 at 3.5 s, paired with the 0.5 s control

**Date:** 2026-10-04. The decision follows `M2_PILOT_READOUT.md` §6: run the
full pool with population 40 and a 3.5 s per-call allowance, alongside the
original pop-40 / 0.5 s control on the same instances and seeds. Population 10
is set aside. **Nothing has been submitted.** Validation is limited to the
manifest build, the test suite and a dry run of the submit wrapper (§4).

File paths below are relative to `cluster_staging_maxsat/` unless stated
otherwise. The setup, classifier and resume rules are unchanged from
`M2_DEEPPOLISH_RUN_PREPARATION.md` (§6 there).

## 1. What runs

| arm | config | pop | `ls.time_limit_s` | `deadline_mode` | tasks |
|---|---|---:|---:|---|---:|
| control `p40_ls0p5` | `configs/tier2/memetic_deeppolish.yaml` (unchanged, sha256 pinned) | 40 | 0.5 | — (historical path) | 210 |
| `p40_ls3p5` | `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml` (**new**) | 40 | 3.5 | `clip` | 210 |

- **Manifest:** `scripts/manifest_m2_full_p40.{tsv,sha256,tasks.csv}`, with
  **420 tasks**. It covers the 70 instances of `m2_population.csv` × solver
  seeds 1–3 × the 2 arms.
- **Line order:** instance, then seed, then arm. Line 2k−1 is the control and
  line 2k is the 3.5 s run on the same (instance, seed).
  - **What this ordering gives:** the two runs of a pair have adjacent array
    indices. Slurm normally starts array tasks in index order as one of the
    30 throttle slots frees, so a pair usually starts within moments of each
    other, under similar cluster load.
  - **What it does not give:** pairs are not guaranteed to run at the same
    time or on the same host. The two runs also end at different times, so
    the slots that free up drift apart. There are no discrete waves; "14
    waves" below is worst-case arithmetic only. The paired analysis must
    therefore not assume shared host or shared load. `host` and
    `cpu_wall_ratio` are recorded per shard if this needs checking.
- **Job ids:** `m2f_p40ls0p5_<pop_idx>_s<seed>` and
  `m2f_p40ls3p5_<pop_idx>_s<seed>`. All 936 job ids across the M2 manifests
  are distinct.
- **OUTDIR:** `results/m2_full_p40/tasks`.
- **Fixed settings:** budget 900 s, `STOP_AT_ORACLE=1`, `GRACE=60`, with
  c\* taken from RC2. Slurm resources are as in the pilot: 1 CPU, 8 GB,
  20 min.
- **The arms differ in exactly two config keys.** This was checked
  key-by-key on the parsed YAML on 2026-10-04:

  | key | control | `p40_ls3p5` |
  |---|---|---|
  | `ls.time_limit_s` | 0.5 | **3.5** |
  | `ea.deadline_mode` | absent (historical path) | **`clip`** |
  | `ea.pop_size`, `tournament_k`, `pmutate`, `elitism`, `max_gens`, `enabled`; `ls.ls_polish_flips`, `ls.flip_budget` | 40, 3, 0.02, true, 1e6, true; 12500, 12500 | identical |

  **Effects of `deadline_mode` beyond the allowance:**
  - **Control:** the deadline is checked only between generations, so a
    run can go on until about 919 s. A target hit after 900 s is classed
    `target_after_budget`, not success.
  - **Clipped arm:** each call is cut to the remaining budget, so the arm
    stops at 900 s plus milliseconds.

  Clipping is required at 3.5 s: without it a generation overshoots by up
  to 38 × 3.5 s ≈ 133 s and hits the 960 s watchdog. The control was left
  unclipped so that it stays byte-identical to the 130 historical
  deeppolish rows (preparation doc §2).
- **The new config's file** is
  `memetic_deeppolish_p40_ls2p5.yaml` with `time_limit_s: 2.5` changed to
  `3.5`. The pilot showed that 3.5 s gives the same search path as 2.5 s
  wherever the flip limit binds (m ≤ 920, 62 of 70 instances). Only on the
  8 instances with m 1065/1088 does it let calls reach 12,500 flips.
- **Not run:** the earlier single-arm manifests
  `manifest_m2_full_p40_ls2p5` and `manifest_m2_full_p10_ls2p5` are still
  built (unchanged bytes), but they are superseded.

**Compute.**

| | value |
|---|---|
| ceiling at 900 s | 420 × 900 s = **105 CPU-h** |
| ceiling with the 60 s grace | 112 CPU-h. In practice about 106: the control overshoots by up to ~19 s and the clipped arm by ms |
| Slurm reservation | 420 × 20 min = 140 CPU-h (allocation, not use) |
| elapsed at `%30`, worst case | 14 waves × ~16 min ≈ **3.7 h**. Queue delay is not estimated |
| pilot as a guide | each p40 arm used 0.34 CPU-h for 30 tasks, mostly on #8. Scaled to 210 tasks that is ~2.4 CPU-h per arm. This is a guess, valid only if the pool is as easy as the pilot |

## 2. Provenance

**The pilot's commit is unverified.** All 96 pilot shards have
`git_sha = null`, because `MAXSAT_GIT_SHA` was not passed. Nothing in the
shards ties them to `81210fc` or to any other commit.

**What can be checked for the pilot:**

- **Configs: verified.** For all 96 shards, the recorded `ea` and `ls`
  blocks equal the local config files, and each config_id has one
  `config_hash`.
- **Instances: verified.** The `instance_sha256` per shard was checked by
  the classifier.
- **Code: not recorded.** The ms-scale overshoots fit a `memetic.py` that
  contains the clipping edit, but no hash of it was recorded.

**For this run, the wrapper now enforces provenance**
(`scripts/submit_m2_memetic.sh`):

- **The commit sha is required.** A real submission without
  `MAXSAT_GIT_SHA` is refused (exit 2), unless `ALLOW_NO_GIT_SHA=1` is set
  explicitly.
- **A provenance file is written before every real submission**, resumes
  included. It goes to `results/m2_full_p40/provenance/submit_<UTC>.txt` and
  holds:
  - the git sha, host, user and array spec, plus the sbatch job line,
    appended afterwards;
  - the sha256 of the manifest, its sidecar, the driver, `m2_results.py`,
    both configs and every `src/**/*.py`;
  - **`src_tree_sha256`**, a single digest over the sorted `src/` list.
- **Checking it after retrieval.** The sha label is only a claim. The
  provenance file is what verifies it: compute the same digest on the
  workstation from the committed tree (§3.6) and compare.

The current staging `src/` digest is
`8989fb8f34ca8d8f55d4fd26b0e491687e9fad26de8d4882effc7ef317410a3f`. `src/`
was not changed in this step.

## 3. Cluster commands

`<user>@<cluster>` is a placeholder. Submit from `~/maxsat-lab/scripts`.

### 3.1 Sync (workstation)

The run commit is the one that added this file. A file cannot contain its
own commit sha, so `<SHA>` below is filled in from `git rev-parse HEAD`.
Sync only from a clean tree at that commit:

```bash
cd ~/maxsat-lab_new/maxsat-lab
git status --short cluster_staging_maxsat/src cluster_staging_maxsat/configs cluster_staging_maxsat/scripts   # must print nothing
SHA=$(git rev-parse HEAD); echo "$SHA"
(cd cluster_staging_maxsat && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)          # expect 8989fb8f…410a3f
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
```

The `git status` line matters. The sha only describes the run if the tree
being synced is exactly the committed one.

### 3.2 Preflight (login node)

```bash
ssh <user>@<cluster>
cd ~/maxsat-lab
find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum   # must equal the workstation digest
sha256sum src/evo/memetic.py                                           # expect ee8a6a5d…6f5ffd6
python3 scripts/make_m2_manifests.py --check                           # 13/13 identical (needs PyYAML; else inside the env)
sha256sum --quiet -c scripts/manifest_m2_full_p40.sha256 && echo "instances OK"
scontrol show config | grep -i MaxArraySize                            # > 420 => single array (§3.3)
( module load anaconda; source activate maxsat; python -m pytest tests/test_m2_prep.py -q )   # optional; 42 passed locally
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
```

The dry run should print:

- `70 instances match`
- configs `memetic_deeppolish x210` and `memetic_deeppolish_p40_ls3p5 x210`
- `array : 1-420 throttle %30`
- `src tree : 8989fb8f…`, which must equal the workstation digest

### 3.3 Submit (420 tasks, concurrency 30)

```bash
cd ~/maxsat-lab/scripts
MAXSAT_GIT_SHA=<SHA from 3.1> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks \
    bash submit_m2_memetic.sh
```

This writes the provenance file, then runs:

```bash
sbatch --array=1-420%30 --job-name=m2_full_p40 \
  --export=ALL,MANIFEST=scripts/manifest_m2_full_p40.tsv,OUTDIR=results/m2_full_p40/tasks,STOP_AT_ORACLE=1,GRACE=60,MAXSAT_GIT_SHA=<SHA> \
  tier2_memetic_array.sbatch
```

**Array size limit.** If the cluster's `MaxArraySize` (preflight §3.2) is
420 or less, the single 420-task array is rejected, because the highest
index must be below `MaxArraySize`. In that case, submit two halves with
**`THROTTLE=15` each**:
- **Concurrency:** each array's throttle applies only to that array, so two
  arrays at `%30` could run 60 tasks at once. Two at `%15` keep the total
  at 30.
- **Pairs:** no pair is split between the halves, because line 210 ends a
  pair.
- **Speed:** elapsed time is unchanged, since 30 slots stay busy until one
  half runs out of tasks.

```bash
cd ~/maxsat-lab/scripts
ARRAY=1-210   THROTTLE=15 MAXSAT_GIT_SHA=<SHA> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
ARRAY=211-420 THROTTLE=15 MAXSAT_GIT_SHA=<SHA> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
```

`ARRAY` restricts the submission to that index range of the manifest.
Line N stays task N, so task ids keep meaning manifest lines. Each half
writes its own provenance file. Run `RESUME=1` (§3.5) only after **both**
halves have finished. It then submits one array, so the default `%30` keeps
the total at 30.

### 3.4 Monitor

```bash
squeue -u $USER -n m2_full_p40
sacct -j <jobid> -X -n --format=State | sort | uniq -c
ls ~/maxsat-lab/results/m2_full_p40/tasks | wc -l                    # 420 when done
cd ~/maxsat-lab && python3 scripts/m2_results.py pending \
    --manifest scripts/manifest_m2_full_p40.tsv --outdir results/m2_full_p40/tasks --summary
```

### 3.5 Resume (once, for infrastructure errors only)

```bash
cd ~/maxsat-lab/scripts
DRY_RUN=1 RESUME=1 MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
RESUME=1 MAXSAT_GIT_SHA=<SHA> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
```

Use the **same** sha. Each resume writes its own provenance file.
Watchdog rows are not resubmitted automatically
(`M2_DEEPPOLISH_RUN_PREPARATION.md` §7.6).

### 3.6 Retrieve, verify, aggregate (workstation)

```bash
cd ~/maxsat-lab_new/maxsat-lab
rsync -av <user>@<cluster>:~/maxsat-lab/results/m2_full_p40/ cluster_staging_maxsat/results/m2_full_p40/
rsync -av <user>@<cluster>:'~/maxsat-lab/scripts/logs/t2-memetic-<jobid>_*' cluster_staging_maxsat/scripts/logs/
grep -h -E 'maxsat_git_sha|src_tree_sha256|sbatch' cluster_staging_maxsat/results/m2_full_p40/provenance/*.txt
tmp=$(mktemp -d); git archive <SHA> cluster_staging_maxsat/src | tar -x -C "$tmp" && \
  (cd "$tmp/cluster_staging_maxsat" && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum); rm -rf "$tmp"
cd cluster_staging_maxsat
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_m2_full_p40.tsv \
    --outdir results/m2_full_p40/tasks --out-dir results/m2_full_p40/agg
```

Run the `git archive` line from the repo root; on the current HEAD it gives
`8989fb8f…410a3f`. Its digest must equal `src_tree_sha256` in the provenance
file. Only then is the commit **verified**. Otherwise it is recorded as
unverified, as for the pilot.

## 4. Validation performed (workstation only)

- **Manifests.** `make_m2_manifests.py` rebuilt all 13 outputs, and the 10
  pre-existing files are byte-identical. The new arm is checked against the
  shared-settings table like the others.
- **Tests.** `python -m pytest tests -q` gives **116 passed** (previously
  112):
  - +1 for the new arm's resolved settings, with 38 children per
    generation;
  - +1 for the new manifest's row checks;
  - +1 for a paired-manifest test: alternating arms, identical (instance,
    seed) per pair, all 70 population hashes covered, `deadline_mode`
    empty/clip;
  - +1 for the clipped-budget test on `p40_ls3p5`.
- **Dry run.** `DRY_RUN=1` on the new manifest: 70 instances matched and both
  configs were found.
- **Real-submit path, with a stub `sbatch` on PATH:**
  - without `MAXSAT_GIT_SHA`: refused, exit 2;
  - with it: the provenance file is written (sha, 2 + 2 + 2 file hashes,
    22 `src` hashes), and the stub's job line is appended;
  - the `src_tree_sha256` in the file equals the workstation one-liner.
  - The smoke output directory was deleted afterwards.
- **Not performed:** any run with budget above a few seconds, and any real
  Slurm submission.

## 5. What to look at afterwards

1. **Integrity.** This is as for the pilot, now over 420 tasks:
   - 0 watchdog rows;
   - clipped-arm overshoot at ms scale, control overshoot ≤ ~19 s;
   - `cpu_wall_ratio` ≥ 0.9;
   - provenance verified (§3.6).
2. **How many instances are non-trivial.** Count the instances where any
   run of either arm fails, or where the median TTT exceeds about 10 calls.
   If, as in the pilot, almost all instances are solved in the first few
   children, report that as a finding for M3: RC2 solve time does not
   stratify memetic difficulty. In that case the arm comparison rests on
   those few instances.
3. **Paired comparison.** Use `paired_by_instance_seed.csv`:
   - success counts per arm, per group and in total;
   - per-pair TTT, restricted to non-trivial instances. On trivial ones the
     TTT measures call length (0.5 s against 1.2–3 s), not search quality.
4. **Mechanism.** Run-mean flips per call for `p40_ls3p5` should be 12,500
   on all 70 instances, apart from the final clipped call on `time_cap`
   runs. Confirm this on the 8 instances with m ≥ 1065.
