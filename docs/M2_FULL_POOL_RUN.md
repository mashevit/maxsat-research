# M2 full pool: pop 40, clipped, 0.5 s vs 3.5 s per call

**Date:** 2026-10-04. The decision follows `M2_PILOT_READOUT.md` §6, revised
the same day:

- **Arms.** The full pool runs two pop-40 arms on the same 70 instances ×
  solver seeds 1–3. Both are clipped, and they differ **only** in
  `ls.time_limit_s`: 0.5 s against 3.5 s.
- **Historical control.** `memetic_deeppolish.yaml` (unclipped) is kept
  unchanged, and so are its results: the 130 historical rows and the M2
  pilot. It is not part of this run.
- **Pop 10** is set aside.

**Nothing has been submitted.** Validation was done on the workstation
only (§4).

Paths are relative to `cluster_staging_maxsat/` unless stated otherwise.
Classifier and resume rules are as in `M2_DEEPPOLISH_RUN_PREPARATION.md` §6.

## 1. What runs

| arm | config | pop | `ls.time_limit_s` | `deadline_mode` | tasks |
|---|---|---:|---:|---|---:|
| control `p40_ls0p5_clip` | `configs/tier2/memetic_deeppolish_p40_ls0p5_clip.yaml` (**new**) | 40 | 0.5 | `clip` | 210 |
| `p40_ls3p5` | `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml` | 40 | 3.5 | `clip` | 210 |

**The arms differ only in `ls.time_limit_s`.** This was checked key by key
on the parsed YAML:

- Identical in both: `ea.enabled` true, `pop_size` 40, `tournament_k` 3,
  `pmutate` 0.02, `elitism` true, `max_gens` 1e6, `deadline_mode` clip;
  `ls.ls_polish_flips` 12,500, `ls.flip_budget` 12,500.
- Pinned by `test_full_pool_arms_differ_only_in_ls_time_limit`.
- Neither file sets a top-level `time_limit_s`.

**How the clipped control relates to the historical one.**
- **Before the budget binds,** the clipped 0.5 s control follows the same
  trajectory and rng stream as the unclipped config. This is pinned by
  `test_clip_is_inert_when_the_budget_never_binds`.
- **Once the budget binds:**
  - **historical control:** finishes its generation, up to about 919 s;
  - **clipped control:** stops at 900 s plus milliseconds.
- **Consequence:** results up to 900 s are comparable with the historical
  rows. Hits after 900 s, classed `target_after_budget` for the old
  control, cannot happen here.

**Manifest:** `scripts/manifest_m2_full_p40.{tsv,sha256,tasks.csv}`, with
**420 tasks**.
- **Line order:** instance, then seed, then arm. Line 2k−1 is the control
  and line 2k is the 3.5 s run on the same (instance, seed).
- **What the ordering gives.** A pair has adjacent array indices. Slurm
  normally starts array tasks in index order as throttle slots free, so a
  pair usually starts close together in time.
- **What it does not give.** Pairs are not guaranteed to run at the same
  time or on the same host. There are no discrete waves; "waves" below is
  worst-case arithmetic only. The paired analysis must not assume shared
  host or load. `host` and `cpu_wall_ratio` are recorded per shard.
- **Job ids:** `m2f_p40ls0p5clip_<pop_idx>_s<seed>` and
  `m2f_p40ls3p5_<pop_idx>_s<seed>`. They are unique across all M2
  manifests, so the shard files `OUTDIR/<job_id>.jsonl` never collide.
- **OUTDIR:** `results/m2_full_p40/tasks`.
- **Fixed:** budget 900 s, `STOP_AT_ORACLE=1`, `GRACE=60`, c\* from RC2.
  1 CPU, 8 GB, 20 min per task.
- **Superseded, not run:** the single-arm `manifest_m2_full_{p40,p10}_ls2p5`
  manifests. They are still built with unchanged bytes.

**Why 3.5 s.** The pilot showed that 3.5 s gives the same search path as
2.5 s wherever the flip limit binds (m ≤ 920, 62 of 70 instances). Only on
the 8 instances with m 1065 or 1088 does 3.5 s let every call reach
12,500 flips.

**Compute**

| | value |
|---|---|
| ceiling | 420 × 900 s = **105 CPU-h**. Both arms are clipped, so the 60 s grace is not used |
| Slurm reservation | 420 × 20 min = 140 CPU-h (allocation, not use) |
| elapsed at total concurrency 30, worst case | ⌈420/30⌉ × ~15 min ≈ **3.5 h**, excluding queue delay |
| pilot as a guide | each p40 arm used 0.34 CPU-h for 30 tasks. Scaled to 210 tasks that is ~2.4 CPU-h per arm. This holds only if the pool is as easy as the pilot |

## 2. Provenance

- **Pilot: commit unverified.** The shards have `git_sha = null` and no
  source hash. What is verified: the recorded configs match the local files,
  and the instance hashes match. `81210fc` is the likely source but not
  confirmed.
- **This run:** `submit_m2_memetic.sh` refuses a real submission without
  `MAXSAT_GIT_SHA` (unless `ALLOW_NO_GIT_SHA=1` is set). Before each
  submission, resumes included, it writes
  `results/m2_full_p40/provenance/submit_<UTC>.txt`, containing:
  - the sha, host, user and array spec, plus the sbatch line after
    submission;
  - the sha256 of the manifest, its sidecar, the driver, `m2_results.py`,
    the configs and every `src/**/*.py`;
  - for a split part, also the split tool and the mapping files;
  - **`src_tree_sha256`**, one digest of the sorted `src/` list.
- **Verified** means: the `src_tree_sha256` of every provenance file equals
  the digest recomputed from the commit with `git archive` (§3.7).

## 3. Cluster commands

`<user>@<cluster>` is a placeholder. `<SHA>` is the run commit, which is the
commit that added this version of this file; a file cannot contain its own
sha.

### 3.1 Sync (workstation)

```bash
cd ~/maxsat-lab_new/maxsat-lab
git status --short cluster_staging_maxsat/src cluster_staging_maxsat/configs cluster_staging_maxsat/scripts   # must print nothing
git rev-parse HEAD                                                                                            # = <SHA>
(cd cluster_staging_maxsat && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
```

### 3.2 Preflight (login node)

```bash
cd ~/maxsat-lab
find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum   # = workstation digest
sha256sum src/evo/memetic.py                                           # ee8a6a5def54e28466a24c1027ecce0913d674224119f458313b6eeab6f5ffd6
python3 scripts/make_m2_manifests.py --check                           # 13/13 files identical
sha256sum --quiet -c scripts/manifest_m2_full_p40.sha256 && echo "instances OK"
```

### 3.3 Array limits: one array or parts?

**Why `--array=211-420` does not help.** `tier2_memetic_array.sbatch` runs
manifest line `$SLURM_ARRAY_TASK_ID`, and the two limits act on that index
directly:

- **`MaxArraySize`** bounds the index itself: every index must be below
  `MaxArraySize`. So `--array=211-420` is rejected by the same limit as
  `--array=1-420`.
- **`max_array_tasks`** (a `SchedulerParameters` option) bounds the number
  of tasks in one array.

```bash
scontrol show config | grep -E '^MaxArraySize|^SchedulerParameters'
MAS=$(scontrol show config | awk -F'= *' '/^MaxArraySize/ {print $2}')
MAT=$(scontrol show config | sed -n 's/.*max_array_tasks=\([0-9]*\).*/\1/p')
K=$((MAS - 1)); if [[ -n "$MAT" && "$MAT" -lt "$K" ]]; then K=$MAT; fi; echo "K=$K"
```

- **K ≥ 420:** submit one array (§3.4a).
- **K < 420:** split into part manifests with **local** indices (§3.4b).
  This leaves the driver unchanged:

```bash
cd ~/maxsat-lab
python3 scripts/split_m2_manifest.py --manifest scripts/manifest_m2_full_p40.tsv --max-tasks "$K"
```

The tool writes `scripts/parts/manifest_m2_full_p40.partIofN.{tsv,tasks.csv,sha256}`
and `scripts/parts/manifest_m2_full_p40.splitN.map.csv`:

- **Mapping.** The map lists `part, local_task_id, global_task_id, job_id`
  for all 420 rows. Local line L of part I is byte-identical to its global
  line, so job ids and shard names do not change. All parts write to the
  same OUTDIR.
- **Cuts.** Parts are cut only between (instance, seed) pairs and are as
  equal as possible: K 210–419 gives 2 × 210, K 140–209 gives 3 × 140.
- **Verification.** The tool re-reads and checks everything it writes.
- **Throttle.** It prints `THROTTLE = 30 // N` per part, so N parts
  submitted together run at most 30 tasks.
- **Too many parts.** It refuses to make more than 30 parts.

**Also check the submit limits.** Every array task counts as a job.

```bash
sacctmgr -n -P show assoc user=$USER format=MaxSubmitJobs,GrpSubmitJobs,MaxJobs
sacctmgr -n -P show qos format=Name,MaxSubmitJobsPerUser,MaxJobsPerUser
```

If a submit limit is below 420 plus your other queued jobs, the parts cannot
all be queued at once. Submit them one after another instead: each part
only after the previous one has finished, each with `THROTTLE=30`. This
still never exceeds 30 running tasks.

### 3.4 Dry run, then submit

From `~/maxsat-lab/scripts`, after `mkdir -p logs`.

**(a) One array (K ≥ 420)**

```bash
DRY_RUN=1 MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=<SHA> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
```

The dry run should show:
- `70 instances match`;
- `memetic_deeppolish_p40_ls0p5_clip x210` and `memetic_deeppolish_p40_ls3p5 x210`;
- `array : 1-420 throttle %30`;
- `src tree` equal to the workstation digest.

**(b) Parts (K < 420).** This is the example for N = 2. Use the N and
THROTTLE that the split tool printed.

```bash
for p in 1 2; do DRY_RUN=1 THROTTLE=15 MANIFEST=parts/manifest_m2_full_p40.part${p}of2.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh; done
for p in 1 2; do MAXSAT_GIT_SHA=<SHA> THROTTLE=15 MANIFEST=parts/manifest_m2_full_p40.part${p}of2.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh; done
```

Each part's dry run shows `array : 1-210 throttle %15` (local indices).

### 3.5 Monitor

```bash
squeue -u $USER -o '%.18i %.30j %.8T %.10M %R' | grep m2_full_p40
ls ~/maxsat-lab/results/m2_full_p40/tasks | wc -l                    # 420 when all done
cd ~/maxsat-lab && python3 scripts/m2_results.py pending \
    --manifest scripts/manifest_m2_full_p40.tsv --outdir results/m2_full_p40/tasks --summary
```

The `pending` call against the full manifest shows the status over all
parts. Its ids are **global** line numbers.

### 3.6 Resume (once, for infrastructure errors only)

Use the same `MANIFEST` and `THROTTLE` as the original submission, and the
**same** `<SHA>`. Resume pending ids are task ids from that manifest's
sidecar, so a part manifest yields **local** ids. Never resubmit global ids
against a part.

```bash
cd ~/maxsat-lab/scripts
# (a) one array
DRY_RUN=1 RESUME=1 MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
RESUME=1 MAXSAT_GIT_SHA=<SHA> MANIFEST=manifest_m2_full_p40.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh
# (b) parts, after all parts have finished
for p in 1 2; do RESUME=1 MAXSAT_GIT_SHA=<SHA> THROTTLE=15 MANIFEST=parts/manifest_m2_full_p40.part${p}of2.tsv OUTDIR=results/m2_full_p40/tasks bash submit_m2_memetic.sh; done
```

Watchdog rows are not resubmitted automatically.

### 3.7 Retrieve, verify, aggregate (workstation, repo root)

```bash
cd ~/maxsat-lab_new/maxsat-lab
rsync -av <user>@<cluster>:~/maxsat-lab/results/m2_full_p40/ cluster_staging_maxsat/results/m2_full_p40/
rsync -av <user>@<cluster>:~/maxsat-lab/scripts/parts/ cluster_staging_maxsat/results/m2_full_p40/parts/   # only if split
grep -h -E 'maxsat_git_sha|src_tree_sha256|sbatch' cluster_staging_maxsat/results/m2_full_p40/provenance/*.txt
tmp=$(mktemp -d); git archive <SHA> cluster_staging_maxsat/src | tar -x -C "$tmp" && \
  (cd "$tmp/cluster_staging_maxsat" && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum); rm -rf "$tmp"
cd cluster_staging_maxsat
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_m2_full_p40.tsv \
    --outdir results/m2_full_p40/tasks --out-dir results/m2_full_p40/agg
```

Aggregation always uses the full manifest. Shards from parts carry the same
job ids, so they are found regardless of which part ran them.

## 4. Validation performed (workstation only)

- **Manifests.** `make_m2_manifests.py --check` reports 13/13 files
  identical. Only `manifest_m2_full_p40.{tsv,tasks.csv}` changed; its
  `.sha256` (the instance list) is unchanged. The pilot manifest, the
  historical control config (sha256 pinned) and the pilot results are
  untouched.
- **Tests.** `python -m pytest tests -q` gives **125 passed**. The new tests
  cover:
  - the clipped control's settings;
  - the only-`ls.time_limit_s` difference;
  - the paired manifest (alternating arms, same pair per two lines, both
    clipped, pop 40);
  - clipping on the 0.5 s control;
  - the split tool:
    - no split at K ≥ 420;
    - local-to-global mapping, line identity, no pair split across parts,
      and unique job ids, for K = 419 / 210 / 209 / 100;
    - refusal above 30 parts.
- **Split end to end** at K = 209 (3 × 140, throttle 10):
  - for every map row, the line the driver would read
    (`sed -n Lp part`) equals global line G, and its job id matches;
  - no job id repeats across parts;
  - `pending` on a part returns local ids `1-140`;
  - wrapper dry runs print `--array=1-140%10`;
  - a stub-`sbatch` submission wrote a provenance file containing the part,
    the split tool and the map hashes.
  - The generated parts and the smoke output were deleted afterwards.
  - The parts are generated on the login node from committed files; they
    are not committed.
- **Not performed:** any Slurm submission, or any run with a budget above a
  few seconds.

## 5. What to look at afterwards

1. **Integrity.**
   - 420/420 shards;
   - 0 watchdog rows;
   - overshoot at ms scale on **both** arms;
   - `cpu_wall_ratio` ≥ 0.9;
   - provenance verified (§3.7).
2. **Non-trivial instances.** Count the instances where any run fails, or
   where the median TTT exceeds about 10 calls. If almost all are solved
   in the first few children, as in the pilot, report that RC2 solve time
   does not stratify memetic difficulty (input to M3).
3. **Paired comparison** (`paired_by_instance_seed.csv`):
   - success counts per arm, per group and in total;
   - per-pair TTT on the non-trivial instances only. On trivial ones TTT
     measures call length.
4. **Mechanism.**
   - `p40_ls3p5`: run-mean flips per call should be 12,500 on all
     instances, apart from the final clipped call of `time_cap` runs.
   - `p40_ls0p5_clip`: flips per call should be well below 12,500,
     because time binds.
