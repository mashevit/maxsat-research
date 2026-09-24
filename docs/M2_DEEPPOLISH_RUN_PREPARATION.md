# M2 modified deeppolish: run preparation, with deadline clipping

**Date:** 2026-09-24. Written against repo commit `6d74189`. All changes
listed in §1 are **uncommitted**.

**Status: preparation is complete.** No cluster job has been submitted and
no M2 experiment has run. Everything below comes from manifest builds, unit
tests and workstation smoke runs with a budget of 5 s or less (§5). None of
it is an experimental result.

**Where things are:**

- **Scope.** Every code, config, manifest and script change is inside
  `cluster_staging_maxsat/`. The only file outside it is this document.
- **One document.** This file replaces the earlier no-clipping version of
  itself, and the interim copy at `cluster_staging_maxsat/` has been merged
  in here and deleted. The earlier version's warnings about watchdog losses
  on the pop-40 / 2.5 s arm no longer apply.
- **Handout.** This file supersedes `docs/M2_DEEPPOLISH_HANDOUT.md` §6–§9
  where they conflict. There is no new per-call instrumentation (no shard
  schema change), and the pilot has 4 arms and 96 tasks.
- **Paths.** Unless stated otherwise, file paths below are relative to
  `cluster_staging_maxsat/`.

---

## 1. All new and changed files

### Changed (3 tracked files; `git diff --stat`: +82 / −2)

| file | change |
|---|---|
| `src/evo/memetic.py` | **opt-in deadline clipping** (§2); the only solver-code change. It was already on the diverged list. sha256 after the change: `ee8a6a5def54e28466a24c1027ecce0913d674224119f458313b6eeab6f5ffd6` |
| `DIVERGENCE.md` | new section: "M2 modified-deeppolish preparation" (the clipping edit, its verification, and the new files) |
| `readme.txt` | new "M2 modified deeppolish" section |

### New (18 untracked files: 17 in `cluster_staging_maxsat/` plus this document)

| file | purpose |
|---|---|
| `configs/tier2/memetic_deeppolish_p40_ls2p5.yaml` | pop 40, 2.5 s per call, `deadline_mode: clip` (sha256 `71bebcdb…1febf6`) |
| `configs/tier2/memetic_deeppolish_p10_ls2p5.yaml` | pop 10, 2.5 s, clip (`d5c7479c…ac8118`) |
| `configs/tier2/memetic_deeppolish_p10_ls3p5.yaml` | pop 10, 3.5 s, clip (`9a960930…fe0280`) |
| `scripts/make_m2_manifests.py` | builds the population and all manifests from the RC2 rows and generator manifests, recomputing every instance sha256 and checking each config. `--check` rebuilds in memory and compares with the files on disk (exit 3 on drift) |
| `scripts/m2_population.csv` | the 70-instance population |
| `scripts/manifest_m2_pilot.{tsv,sha256,tasks.csv}` | pilot, 96 tasks |
| `scripts/manifest_m2_full_p40_ls2p5.{tsv,sha256,tasks.csv}` | full pool, 210 tasks |
| `scripts/manifest_m2_full_p10_ls2p5.{tsv,sha256,tasks.csv}` | full pool, 210 tasks |
| `scripts/submit_m2_memetic.sh` | submit wrapper: sha256 and config preflight, `DRY_RUN`, `RESUME`, `THROTTLE`; forces `STOP_AT_ORACLE=1` and `GRACE=60` |
| `scripts/m2_results.py` | classifies each task, lists resume ids, aggregates results (stdlib only) |
| `tests/test_m2_prep.py` | 38 tests (§5.1) |
| `docs/M2_DEEPPOLISH_RUN_PREPARATION.md` (repo root, not the staging tree) | this document |

### Unchanged, and relied on

- `configs/tier2/memetic_deeppolish.yaml`: the control. Its sha256 is
  `cf6c3ad9665a9d64571d009e71f95df6f3ee530d25b7991a5f3c3e169c034990`,
  pinned in a test.
- `scripts/tier2_memetic_array.sbatch`: the driver. It keeps `--time`
  00:20:00, 1 CPU and 8 GB.
- `src/cli/run_memetic_shard.py`: the watchdog and its 60 s default grace
  are unchanged, and there is no schema change.
- `src/evo/operators.py`, `src/sat/walksat.py` and the other files in the
  eight-file identity set: the DIVERGENCE loop still prints `IDENTICAL` for
  all eight.

## 2. Deadline clipping (`src/evo/memetic.py`)

**The old behaviour.** The run budget (`time_cap`, the 900 s injected by
`--budget-s`) was checked only at the top of each generation. A run
therefore overshot by up to one whole generation of local-search calls:
38 × 2.5 s ≈ 95 s at pop 40. That could reach the watchdog, which fires at
budget + grace = 960 s.

**Now, opt in with `ea.deadline_mode: clip`:**

```python
if deadline_clip:
    remaining = time_cap - (time.time() - start_t)
    if remaining <= 0:
        stop_reason = "time_cap"      # budget spent mid-generation; unpolished child dropped
        break
    ls_call = dict(ls_small, time_limit_s=min(ls_small["time_limit_s"], remaining))
else:
    ls_call = ls_small                # historical path
child_bits, flips_t1 = short_polish(child_bits, wcnf, ls_call, rng_seed=rng.randrange(1<<30))
```

The generation-level `if stop_reason == "target": break` became
`if stop_reason is not None: break`. Without the key this is equivalent,
because `"target"` is the only value `stop_reason` can hold there.

**What this means for each arm:**

- **Clipped arms.** Each call gets `min(2.5 or 3.5 s, remaining budget)`.
  The run ends at 900 s plus the tail of the final call (one flip, plus
  walksat's setup and snapshot) plus one child evaluation. In the smoke
  runs that tail was **≤ 14 ms**. The target check after every child is
  unchanged.
- **Control.** `memetic_deeppolish.yaml` has no key, so it keeps the
  historical code path and rng stream, and with them its known overshoot of
  up to about 19 s (38 × 0.5 s). That fits inside the 60 s grace. Keeping
  the control identical to the historical config was chosen so that it
  remains comparable with the 130 earlier deeppolish rows.

**Verification of the unchanged path.** This was done before and after the
edit, on pilot instance #7 with the control config made deterministic:
calls flip-limited at 300 flips, `max_gens` 2, time limits 1e6.

| solver seed | assignment sha256[:16] | `total_flips` | `children` |
|---:|---|---:|---:|
| 1 | `bd731d7910a70ea7` | 22,800 | 76 |
| 2 | `c73d158a7a6687f7` | 22,800 | 76 |

- **Before and after the edit:** the results are byte-identical. They are
  pinned in `tests/test_m2_prep.py`.
- **Clipping switched on:** with `deadline_mode: clip` but a budget that
  never binds, seed 1 gives the same result.

## 3. Configurations

| config_id | pop | elites + children / gen | `ls.time_limit_s` | flips / call | `deadline_mode` |
|---|---:|---|---:|---:|---|
| `memetic_deeppolish` (**control**, unchanged file) | 40 | 2 + 38 | 0.5 | 12,500 | — (historical) |
| `memetic_deeppolish_p40_ls2p5` | 40 | 2 + 38 | 2.5 | 12,500 | `clip` |
| `memetic_deeppolish_p10_ls2p5` | 10 | 1 + 9 | 2.5 | 12,500 | `clip` |
| `memetic_deeppolish_p10_ls3p5` (optional arm) | 10 | 1 + 9 | 3.5 | 12,500 | `clip` |

**Shared by all four arms:**

- `tournament_k` 3, `pmutate` 0.02, elitism on, `max_gens` 1e6.
- `ls_polish_flips` = `flip_budget` = 12,500.
- No top-level `time_limit_s`.
- The elite count comes from the unchanged code, `max(1, ceil(0.05·pop))`.
- Runner settings: `--budget-s 900`, `--grace-s 60`, `--stop-at-oracle`
  with c\* from RC2.
- Slurm resources: 1 CPU, 8 GB, 20 min.

`make_m2_manifests.py` loads every config with PyYAML and checks each of
these values, including `deadline_mode`.

## 4. Population, pilot and task counts (verified)

**Population.** The population is every RC2-certified calib_a / calib_b
instance with **30 ≤ `solve_s` ≤ 900 s, inclusive**, deduplicated on sha256.

- 70 instances: calib_a 17, calib_b 53.
- Groups: `lower_ext` **16**, `tier2` **46**, `upper_ext` **8**.
- Original tier labels: T1 16, T2a 37, T2b 9, T3 8.
- Every instance sha256 was recomputed from its file; there are 0
  mismatches with the generator manifests.
- `python -m src.bench.calib_tier2_select --batches calib_a calib_b --floor 30 --ceiling cap`
  selects the same 70 hashes, with 0 disagreements on oracle cost, path or
  generator seed. This was run from the repo root, with output to a scratch
  directory.

**Pilot instances** (handout §7.1). Each is resolved by (batch, cell,
generator seed) and checked against the handout's group, c\*, m and
`solve_s`:

| # | group | tier | file (`data/generated/<batch>/`) | batch | gen. seed | m | c\* | RC2 s | sha256[:12] |
|---:|---|---|---|---|---:|---:|---:|---:|---|
| 1 | upper_ext | T3 | `wksat_v100_k2_sr6.00_hr0.00_w1_uniform_s1.wcnf` | calib_a | 1 | 600 | 50 | 752.7 | `0a3b3189ef31` |
| 2 | upper_ext | T3 | `wksat_v250_k2_sr2.35_hr0.00_w1_uniform_s3.wcnf` | calib_b | 3 | 588 | 22 | 610.3 | `61467d5b28e5` |
| 3 | upper_ext | T3 | `wksat_v50_k3_sr9.00_hr0.00_w1_uniform_s5.wcnf` | calib_b | 5 | 450 | 13 | 847.3 | `a8133e0c9298` |
| 4 | upper_ext | T3 | `wksat_v150_k3_sr5.00_hr0.00_w1_uniform_s3.wcnf` | calib_a | 3 | 750 | 3 | 772.2 | `1bd61c544756` |
| 5 | tier2 | T2b | `wksat_v400_k2_sr2.30_hr0.00_w1_uniform_s2.wcnf` | calib_b | 2 | 920 | 23 | 367.2 | `39dd93791969` |
| 6 | tier2 | T2a | `wksat_v150_k2_sr3.30_hr0.00_w1_uniform_s4.wcnf` | calib_b | 4 | 495 | 28 | 226.6 | `dc29e62067d5` |
| 7 | tier2 | T2a | `wksat_v70_k3_sr6.50_hr0.00_w1_uniform_s4.wcnf` | calib_b | 4 | 455 | 7 | 217.8 | `fc125f4de8ed` |
| 8 | tier2 | T2b | `wksat_v250_k3_sr4.35_hr0.00_w1_uniform_s2.wcnf` | calib_b | 2 | 1088 | 1 | 323.7 | `9bb5c889d020` |
| 9 | lower_ext | T1 | `wksat_v150_k3_sr4.80_hr0.00_w1_uniform_s3.wcnf` | calib_b | 3 | 720 | 2 | 34.9 | `669e13c0b0f2` |
| 10 | lower_ext | T1 | `wksat_v100_k3_sr5.20_hr0.00_w1_uniform_s5.wcnf` | calib_b | 5 | 520 | 4 | 46.8 | `86e2f31c90e6` |

**Task counts**

| manifest | tasks | composition | ceiling at 900 s | with 60 s grace | Slurm reservation |
|---|---:|---|---:|---:|---:|
| `manifest_m2_pilot.tsv` | **96** | control, p40_ls2p5, p10_ls2p5: 30 each (10 instances × seeds 1–3); p10_ls3p5: 6 (#5, #8 × seeds 1–3) | **24.0 CPU-h** | **25.6 CPU-h** | 32 CPU-h |
| `manifest_m2_full_p40_ls2p5.tsv` | **210** | 70 × seeds 1–3 | 52.5 CPU-h | 56.0 CPU-h | 70 CPU-h |
| `manifest_m2_full_p10_ls2p5.tsv` | **210** | 70 × seeds 1–3 | 52.5 CPU-h | 56.0 CPU-h | 70 CPU-h |

With clipping, the clipped arms use at most about 900 s per task, so the
grace column is really a ceiling for the control only.

- **Worst-case compute time at `%30`**, excluding queue delay, which is not
  estimated: the pilot needs 4 waves of about 16–17 min, about 1.1 h; each
  full-pool manifest needs 7 waves, about 2 h.
- **File formats.**
  - `.tsv`: the 9 columns the driver reads: `job_id instance config
    config_id seed budget_s oracle_cost tier rc2_run`. `seed` is the
    **solver** seed, `tier` the original RC2 label and `rc2_run` the batch.
  - `.tasks.csv`: a sidecar in the same order. It adds `task_id`, `arm`,
    `pop_size`, `ls_time_limit_s`, **`deadline_mode`**, **`gen_seed`** (the
    instance's generator seed, the `_sN` in its filename; this is separate
    from the solver seed), `m`, `analysis_group` and others.
  - `.sha256`: a `sha256sum -c` list of the manifest's instances.
- **Pilot order.** Lines are ordered by instance, then solver seed, then
  arm, so the runs being compared for one (instance, seed) run in the same
  wave.
- **Unique identities.** Job ids have the form
  `m2p_<arm>_i<pilot#>_s<seed>` or `m2f_<arm>_<pop_idx>_s<seed>`. All 516
  are distinct. Shards go to `OUTDIR/<job_id>.jsonl`, and each stage has its
  own OUTDIR:
  - `results/m2_pilot/tasks`
  - `results/m2_full_p40_ls2p5/tasks`
  - `results/m2_full_p10_ls2p5/tasks`
- **Checksums.** The TSV files are **byte-identical** to the pre-clipping
  build, because clipping lives in the configs:
  - pilot: `c07790a3b9ad0cc7ea6308eebb5686f2f7591c8f7252019bb2f3319ef2199ba3`
  - full p40: `3f19746d724fd64ccc70347d8b3e02f164b61d4317333a079a1266c2adc04daa`
  - full p10: `f7125955285abc536626b1e6b5e6b48873fc6948eac33500a8bb102a7af6064b`
  - population CSV: `3af821214337a7ef47998596c7dafc0f9655c840d1256d6981c49c5405e9b7d6`

  The sidecars changed, because they gained `deadline_mode`:
  - pilot `.tasks.csv`: `7d44e92c…9add4`
  - full p40 `.tasks.csv`: `36790cfb…6136`
  - full p10 `.tasks.csv`: `bca59bab…18d8`

## 5. Local validation actually performed

### 5.1 Tests

`cd cluster_staging_maxsat && python -m pytest tests -q` gave
**112 passed**: the 74 existing tests plus the 38 in `tests/test_m2_prep.py`.
The new tests cover:

- **Configs.**
  - The control is byte-identical to the historical file (pinned sha256).
  - Exact `ea:` and `ls:` blocks for all four arms, including
    `deadline_mode: clip` on the three new ones and its absence on the
    control.
  - No top-level `time_limit_s`.
  - Children per generation of 38 / 38 / 9 / 9.
  - Distinct config ids.
- **Manifests.**
  - A fresh build (`--check`, which rehashes all 70 instances) matches
    the files on disk.
  - Population counts are 70 and 16 / 46 / 8, with inclusive bounds.
  - Per manifest: 96 / 210 / 210 rows of 9 columns agreeing with the
    sidecar; budget 900; solver seeds 1–3; generator seeds matching the
    filenames; every config file exists.
  - 516 unique job ids.
  - Pilot arm counts of 30 / 30 / 30 / 6, with the 3.5 s arm only on #5 and
    #8, and each (instance, seed) pair exactly once per main arm.
  - Each full-pool manifest covers 70 × 3 distinct pairs.
- **Clipping.**
  - The control path equals the pre-edit reference for seeds 1 and 2.
  - Clipping is inert when the budget never binds.
  - For each clipped arm, on an unsatisfiable instance with a 0.3 s budget
    and time-bound calls: the run ends with `time_cap` in under 1.3 s (the
    assertion keeps a 1 s margin for scheduler noise; in practice the run
    ends near 0.3 s). Without clipping, the first call alone would last
    2.5–3.5 s.
  - One full-suite run showed a single failure that did not reproduce in
    5 further full runs or 15 targeted runs. The likely cause was the
    earlier, tighter 0.1 s margin on this wall-clock assertion, which has
    since been widened. After the change, the full suite passes: 112 tests.
- **Population 10.**
  - `run_memetic` runs with each pop-10 config, with
    `9·(gens−1) < children ≤ 9·gens`.
  - The shard runner records `pop_size` 10 and `deadline_mode` clip.
- **Classifier.** 12 parametrised cases plus a dedicated `deadline_mode` check, including TTT exactly 900 (success), TTT 931
  (late), watchdog, and invalid submissions: grace ≠ 60, stop-at-oracle off,
  wrong pop, or a missing or wrong `deadline_mode`.
- **Resume.** Only infra and invalid tasks are pending.
- **Median TTT.** Failures count as > 900.

### 5.2 Smoke runs

These ran on the workstation with python 3.12.3 and a **5 s budget**. The
outputs went to the session scratchpad, outside the repo. They are not
measurements.

**Setup.** The **unchanged `scripts/tier2_memetic_array.sbatch`** was run
with `bash`, with `SLURM_ARRAY_TASK_ID=1..8`, `STOP_AT_ORACLE=1` and
`GRACE=60`. `module` and `source activate` were stubbed as no-ops. The
manifest was built from pilot rows with budget 5 s and a `smk_` prefix:
4 arms × pilot #7 and #8, solver seed 1.

| # | instance | arm | class | wall (s) | overshoot past 5 s | children | mean flips / call |
|---:|---|---|---|---:|---:|---:|---:|
| 1 | #7 (m 455) | control | success (TTT 0.50 s) | 0.51 | — | 1 | 10,871 |
| 2 | #7 | p40_ls2p5 | success (TTT 0.57 s) | 0.57 | — | 1 | 12,500 |
| 3 | #7 | p10_ls2p5 | success (TTT 0.57 s) | 0.58 | — | 1 | 12,500 |
| 4 | #7 | p10_ls3p5 | success (TTT 0.58 s) | 0.58 | — | 1 | 12,500 |
| 5 | #8 (m 1088) | control | budget_exhausted | 19.08 | 14.08 s | 38 | 5,156 |
| 6 | #8 | p40_ls2p5 | budget_exhausted | **5.011** | 0.011 s | 5 | 10,181 |
| 7 | #8 | p10_ls2p5 | budget_exhausted | **5.004** | 0.004 s | 5 | 10,237 |
| 8 | #8 | p10_ls3p5 | budget_exhausted | **5.004** | 0.004 s | 5 | 10,268 |

**What the smoke runs show:**

- **Clipping works on the real driver.** Before clipping, the same
  pop-40 / 2.5 s task on #8 took **46.9 s** and the pop-10 tasks took
  **12.5 s**. They now end within 11 ms of the budget.
- **The control is unchanged.** It still runs its first generation to the
  end: 38 × 0.5 s ≈ 19 s.
- **Tooling works end to end.** `m2_results.py aggregate` wrote all five
  CSVs, and `pending` returned 0 ids.
- **Flip counts below 12,500 are expected on #8.** The last call of each
  clipped run was cut short, so the run mean falls below 12,500 even where
  the earlier calls hit the flip limit.
- **The #7 results are trivial.** The first child already reached c\*.

**Watchdog check.** One direct `run_memetic_shard` run of p40_ls2p5 on #8
with `--budget-s 5 --grace-s 5 --stop-at-oracle`:

- **Before clipping:** `status = timeout`, watchdog fired at 10.0 s.
- **After clipping:** `status = ok`, `stop_reason = time_cap`,
  wall **5.014 s**.

**Dry runs of the submit wrapper.** `DRY_RUN=1` passed for all three
manifests: sha256 matched for 10 / 70 / 70 instances and every config was
found. The printed commands are those in §7.

**Not performed:** nothing with a budget above 5 s, and no Slurm
submission. There is no `sbatch` on this workstation, so the `sbatch`
command in §7.3 was checked against the driver's code and the wrapper's
output, not executed.

## 6. Counting rules, and what the records can and cannot show

`scripts/m2_results.py` gives every task exactly one class:

| class | rule | success? | auto-resubmitted by `RESUME=1`? |
|---|---|---|---|
| `success` | status ok, `stop_reason` target, `time_to_target_s ≤ 900` | **yes** | no |
| `target_after_budget` | target reached with TTT > 900. Possible for the control, whose last generation overshoots; for clipped arms only within the ms-scale tail | no | no |
| `budget_exhausted` | status ok, `stop_reason time_cap` | no (censored) | no |
| `watchdog` | status timeout, fired at 960 s | no | **no**. **Not expected on any arm**: clipped arms end at about 900 s and the control by about 919 s. Investigate first (host, `cpu_wall_ratio`, `.err` log); resubmit by hand only if it is an infrastructure fault |
| `max_gens` | unreachable at 1e6 | no | no; investigate |
| `cost_mismatch` | the runner's cost cross-check failed | no | no; investigate as a bug |
| `invalid_submission` | the shard disagrees with its manifest row on any of: job_id, config_id, solver seed, instance sha, budget 900, grace 60, `stop_at_oracle`, oracle cost, `pop_size`, `ls.time_limit_s`, `ls_polish_flips` or `ea.deadline_mode` | — | yes |
| `infra_error` | status error, parse_error or missing_instance | — | yes, **once**; if it recurs, investigate |
| `infra_missing` | no shard or an unreadable shard (Slurm TIMEOUT, NODE_FAIL, OOM or cancel) | — | yes |

**What the records cannot show.** No new instrumentation was added, and
shards carry run totals only.

- `mean_flips_per_call = total_flips / children` is a **run mean**.
- A mean of exactly 12,500 means every call in the run was flip-limited.
  A lower mean means some calls were stopped by time, **including the final
  clipped call** of a `time_cap` run on a clipped arm.
- Per-call distributions, times and stop reasons are **not** recorded, and
  no report may claim them.
- How many calls clipping shortened is also not recorded. On a clipped run
  it is at most the final call.

## 7. Cluster commands

The cluster user and host are not known here, so `<user>@<cluster>` is a
placeholder. Submit **from `~/maxsat-lab/scripts`**, for two reasons: the
driver's log path `logs/...` is relative to the submit directory, and the
driver begins with `cd ..`. `MANIFEST` and `OUTDIR` are relative to
`~/maxsat-lab`. Task N runs manifest line N (1-based).

### 7.1 Sync (workstation → cluster)

```bash
cd ~/maxsat-lab_new/maxsat-lab
# optional: commit first so shards can record a real sha
git add cluster_staging_maxsat docs/M2_DEEPPOLISH_RUN_PREPARATION.md && git commit -m "M2 run preparation with opt-in deadline clipping"
git rev-parse HEAD                      # -> <commit-sha>
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
```

The rsync carries `data/generated/calib_{a,b}/*.wcnf` (gitignored), the
changed `src/evo/memetic.py`, and `results/profile_calib_*_all.jsonl`, which
`--check` needs.

### 7.2 Preflight (login node)

```bash
ssh <user>@<cluster>
cd ~/maxsat-lab
grep -n "deadline_clip" src/evo/memetic.py | head -3            # the clipping code arrived
sha256sum src/evo/memetic.py                                    # expect ee8a6a5d…6f5ffd6
python3 scripts/make_m2_manifests.py --check                    # needs PyYAML; else run inside the conda env below
for m in manifest_m2_pilot manifest_m2_full_p40_ls2p5 manifest_m2_full_p10_ls2p5; do
  sha256sum --quiet -c scripts/$m.sha256 && echo "$m: instances OK"
done
( module load anaconda; source activate maxsat; python -m pytest tests/test_m2_prep.py -q )   # optional, about 10 s
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
```

The expected dry-run output: `10 instances match`, the four config_ids with
counts 30 / 30 / 6 / 30, `array : 1-96 throttle %30`.

### 7.3 Submit the pilot (96 tasks, concurrency 30)

Via the wrapper:

```bash
cd ~/maxsat-lab/scripts
MAXSAT_GIT_SHA=<commit-sha> MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks \
    bash submit_m2_memetic.sh
```

The equivalent direct `sbatch` command (this is exactly what the wrapper
prints):

```bash
cd ~/maxsat-lab/scripts && mkdir -p logs
sbatch --array=1-96%30 --job-name=m2_pilot \
  --export=ALL,MANIFEST=scripts/manifest_m2_pilot.tsv,OUTDIR=results/m2_pilot/tasks,STOP_AT_ORACLE=1,GRACE=60,MAXSAT_GIT_SHA=<commit-sha> \
  tier2_memetic_array.sbatch
```

`MAXSAT_GIT_SHA` is optional. If you drop it, the shards record
`git_sha = null`.

### 7.4 Monitor

```bash
squeue -u $USER -n m2_pilot
sacct -j <jobid> -X -n --format=State | sort | uniq -c
sacct -j <jobid> -X --format=JobID%20,State,ExitCode,Elapsed,NodeList%24
ls ~/maxsat-lab/results/m2_pilot/tasks | wc -l                  # 96 when done
cd ~/maxsat-lab && python3 scripts/m2_results.py pending \
    --manifest scripts/manifest_m2_pilot.tsv --outdir results/m2_pilot/tasks --summary
tail -n 3 ~/maxsat-lab/scripts/logs/t2-memetic-<jobid>_<task>.{out,err}
```

How to read `sacct`:

| `sacct` state | shard | what happened |
|---|---|---|
| `COMPLETED` | `status ok` | normal |
| `FAILED`, exit `1:0` | written | status was not ok (error, or an unexpected watchdog); see `m2_results.py` |
| `TIMEOUT`, `NODE_FAIL`, `OUT_OF_MEMORY` or `CANCELLED` | none | infrastructure; `RESUME=1` resubmits it |

### 7.5 Retrieve and aggregate (workstation)

```bash
cd ~/maxsat-lab_new/maxsat-lab
rsync -av <user>@<cluster>:~/maxsat-lab/results/m2_pilot/ cluster_staging_maxsat/results/m2_pilot/
rsync -av <user>@<cluster>:'~/maxsat-lab/scripts/logs/t2-memetic-<jobid>_*' cluster_staging_maxsat/scripts/logs/
cd cluster_staging_maxsat
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_m2_pilot.tsv \
    --outdir results/m2_pilot/tasks --out-dir results/m2_pilot/agg
```

This writes five files to `results/m2_pilot/agg/`:

- `tasks.csv`
- `by_instance_config.csv`
- `by_group_config.csv`
- `by_config.csv`
- `paired_by_instance_seed.csv`

It also prints the class counts per arm × group.

### 7.6 Resume

```bash
cd ~/maxsat-lab/scripts
DRY_RUN=1 RESUME=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
RESUME=1 MAXSAT_GIT_SHA=<commit-sha> MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
```

- **What gets resubmitted.** Only `infra_missing`, `infra_error` and
  `invalid_submission`. Valid shards are never touched.
- **Resume once for infrastructure errors.** If the same task fails the
  same way again, read its `error` and its `.err` log instead of looping.
- **Watchdog rows.** These are now unexpected and are not resubmitted
  automatically. If one turns out to be an infrastructure fault (for
  example `cpu_wall_ratio` well below 1, or a single bad host), resubmit
  those ids by hand, using the §7.3 command with `--array=<ids>%30`. If
  watchdog rows repeat on healthy hosts, the clipping is not working as
  intended: stop and investigate.

### 7.7 Full-pool submissions (later, only after the §8 review)

```bash
cd ~/maxsat-lab/scripts
DRY_RUN=1 MANIFEST=manifest_m2_full_p40_ls2p5.tsv OUTDIR=results/m2_full_p40_ls2p5/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=<commit-sha> MANIFEST=manifest_m2_full_p40_ls2p5.tsv OUTDIR=results/m2_full_p40_ls2p5/tasks bash submit_m2_memetic.sh
#   = sbatch --array=1-210%30 --job-name=m2_full_p40_ls2p5 \
#       --export=ALL,MANIFEST=scripts/manifest_m2_full_p40_ls2p5.tsv,OUTDIR=results/m2_full_p40_ls2p5/tasks,STOP_AT_ORACLE=1,GRACE=60,MAXSAT_GIT_SHA=<commit-sha> \
#       tier2_memetic_array.sbatch

DRY_RUN=1 MANIFEST=manifest_m2_full_p10_ls2p5.tsv OUTDIR=results/m2_full_p10_ls2p5/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=<commit-sha> MANIFEST=manifest_m2_full_p10_ls2p5.tsv OUTDIR=results/m2_full_p10_ls2p5/tasks bash submit_m2_memetic.sh
#   = sbatch --array=1-210%30 --job-name=m2_full_p10_ls2p5 \
#       --export=ALL,MANIFEST=scripts/manifest_m2_full_p10_ls2p5.tsv,OUTDIR=results/m2_full_p10_ls2p5/tasks,STOP_AT_ORACLE=1,GRACE=60,MAXSAT_GIT_SHA=<commit-sha> \
#       tier2_memetic_array.sbatch
```

- **Concurrency.** Both arrays share the per-user limit of 30 concurrent
  tasks.
- **Retrieval, aggregation and resume** work as in §7.5 and §7.6, with the
  matching manifest and OUTDIR.
- **No control manifest is prepared for the full pool.** If a 0.5 s
  full-pool comparison is needed, it must be built separately.

## 8. What to examine after the pilot, before going further

1. **Integrity.**
   - All 96 shards are present, with 0 `invalid_submission`, 0
     `cost_mismatch` and 0 `max_gens`.
   - `infra_*` is at 0 after at most one resume.
   - `cpu_wall_ratio` is at least about 0.9: `aggregate` warns otherwise.
2. **Clipping on the cluster.**
   - **0 watchdog rows on any arm.**
   - On `budget_exhausted` rows of the clipped arms, `overshoot_s`
     (wall − 900) should be well under 1 s. The smoke runs gave ≤ 14 ms;
     the cluster is slower, and the runner's wall time also includes the
     final assignment scoring.
   - On the control, the overshoot should be ≤ about 19 s, as in the
     historical rows.
   - Clipped arms should show no `target_after_budget` rows, or only
     ms-scale ones.
3. **Success counts (TTT ≤ 900 s).**
   - Per arm, per group and per instance, plus the paired
     per-(instance, seed) table.
   - With 10 instances × 3 seeds these counts are descriptive; they cannot
     support a significance claim.
   - Because of the control's overshoot, its hits after 900 s appear as
     `target_after_budget` and do not count as successes.
4. **Mean flips per call** (a run mean; see §6).
   - Mostly 12,500 on the 2.5 s arms means the flip limit binds.
   - Clearly below 12,500 on #5 and #8 at 2.5 s means time still binds
     there. Compare with the 3.5 s arm on the same instances.
   - If p10_ls2p5 already averages about 12,500 on #5 and #8, the 3.5 s
     allowance never binds. The two arms should then follow nearly the
     same search path (compare `best_assignment_hash`, `children` and
     TTT), and the 3.5 s arm adds nothing.
5. **Generations, children and `mean_wall_per_child_s`** per arm. These
   show the trade-off between deeper polishing and evolutionary turnover:
   pop 10 gets about 4× more generations for the same number of calls.
6. **Decision.** Submit neither, one, or both full-pool manifests, and
   decide whether a 3.5 s full-pool manifest is needed. None is prepared;
   it would be one line in `FULL_ARMS` in `make_m2_manifests.py`. Record the
   decision and its numbers in the calibration log as the next checkpoint.
