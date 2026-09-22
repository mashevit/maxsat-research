# Corpus calibration — running log

Checkpoint records for the milestones in
[`CORPUS_CALIBRATION_GOALS.md`](CORPUS_CALIBRATION_GOALS.md) §6. One entry per
turn: what was verified, what was implemented, what was submitted (job ids or
the exact commands), and the next step. Newest entry last.

---

## 2026-09-16 — Checkpoint 0: plan written, nothing implemented

Against commit `991a8cd` (+ one uncommitted binary-path fix in
`cluster_staging_maxsat/scripts/oracle_evalmaxsat_array.sbatch`, left as-is).
Stopped, as instructed, before implementing M1.

### What was verified

- **Generator + writer.** `python -m pytest instancegen -q` → 62 passed
  (from the repo root; running from inside `instancegen/` fails on imports).
  Regenerating two pilot cells is byte-identical across writes, and RC2 via
  `src.cli.profile_hardness` reproduces the pilot optima: c\* = 6 at
  3-SAT n = 50 / α = 6, c\* = 25 at 2-SAT n = 100 / α = 4. Wall times were
  ~1.8× the pilot's (4.9 s vs 2.8 s; 10.3 s vs 5.5 s), so workstation timings
  are indicative only — calibration times must come from the cluster.
- **RC2 configuration actually used.** PySAT 1.9.dev15,
  `RC2(wcnf, solver="g3")` with `adapt=exhaust=minz=False`
  (`src/cli/solve_rc2_anytime.py:190`). For unit weights the lower bound
  rises by exactly 1 per core, so certification takes c\* UNSAT calls; the
  *per-call cost* is what the grid measures. The pilot's "cliff at c\* ≈ 10" is
  a 3-SAT / 60 s observation, not a ceiling — 2-SAT (c\* = 25 in 5.5 s)
  already contradicts a universal one.
- **Memetic runner.** The staging copy
  (`cluster_staging_maxsat/src/cli/run_memetic_shard.py`) has
  `--stop-at-oracle` and records `time_to_target_s`; the repo `src/` copy
  does not — intentional, per `cluster_staging_maxsat/DIVERGENCE.md`. It
  reads generated old-dialect WCNF for k = 2 and k = 3
  (`instance_format=wcnf_old`). With `memetic_deeppolish`, seed 1, budget
  10 s, it **hit the optimum in 0.50 s and 0.49 s (generation 1)** on the two
  pilot cells where RC2 took 5–10 s. That is the strongest reason the
  calibration must include memetic runs: the RC2-reachable small-n cells look
  memetic-trivial, and the informative band (if it exists) is a diagonal strip
  toward larger n / lower α, like uuf250.
- **Slurm tooling.** `scripts/screen_mse16_array.sbatch` hard-codes its
  manifest (`manifest_mse16_screen.txt`) and output dir
  (`results/profile_mse16`) — needs `MANIFEST`/`OUTDIR` vars.
  `scripts/tier2_memetic_array.sbatch` is already parameterised
  (`MANIFEST`, `OUTDIR`, `GRACE`, `STOP_AT_ORACLE`), `--time 00:20:00` for a
  900 s budget + 60 s grace. No `sbatch` and no ssh alias on this
  workstation, so submissions are recorded as commands, not run.
- **Against per-instance c\* monotonicity** (from
  `results/profile/gen_pilot_cap60.jsonl`): 3-SAT n = 150 / α = 5, seed 1 →
  c\* = 1 in 1.5 s; seed 2 → LB ≥ 3, uncertified at 60 s.

### Plan document

`docs/CORPUS_CALIBRATION_GOALS.md`: research questions and scope;
verified / proposed / hypothesis split; the `calib_a` grid (Max-3-SAT
5 n × 4 α, Max-2-SAT 4 n × 4 α, 5 seeds → 180 instances); measurement and
censoring rules; the path to frozen cell-level selection rules and fresh seeds
(1001+); five milestones; batch accounting (A1: 180 tasks, 1 CPU / 8 GB, %20,
≤ 48 CPU-h worst case; A2: ≤ 540 tasks, ≤ 144 CPU-h). Even-sided torus MaxCut
dropped (bipartite, c\* = 0).
*(Historical: the `%20` planned here was superseded by `%30` in Checkpoint 1;
CPU-hours unchanged.)*

### Implemented

Nothing beyond the document and the smoke checks above (scratchpad only; no
repo changes other than the new docs).

### Jobs / commands

None submitted. Commands for A1 are in the goals doc §7; they depend on M1's
manifest and array driver.

### Next milestone — M1 (awaiting approval)

- `instancegen/grids/calib_a.yaml` — the grid as data.
- `instancegen.cli generate-grid` — instances →
  `cluster_staging_maxsat/data/generated/calib_a/`, `manifest.jsonl`
  (params, seed, `instance_sha256`, git sha, `created_utc`), and the Slurm
  manifest `scripts/manifest_calib_a_rc2.txt`.
- `scripts/rc2_profile_array.sbatch` with `MANIFEST`/`OUTDIR` and
  skip-if-complete; `submit_rc2_profile.sh`.
- Tests; local 2-instance smoke at `--cap 20`; exact rsync + sbatch commands
  for A1 recorded here.

**Open question before M1:** keep 5 seeds/cell and all 36 cells (48 CPU-h
worst case), or trim the corners expected to be censored (3-SAT n = 250 /
α = 8; 2-SAT n = 400 / α = 6)? The goals doc argues for keeping them so the
censoring boundary is measured, not inferred.


---

## 2026-09-16 — Checkpoint 1: review of the plan, then M1 implemented

Against commit `0dc3bc3` (the oracle path fix is now committed). Work tree at
the end of this checkpoint is **uncommitted**; the file list is at the end.
Nothing was submitted to Slurm — no `sbatch` here (see §"Jobs / commands").

### Part A — review of `CORPUS_CALIBRATION_GOALS.md` against the repository

Every claim in the goals doc was re-checked against code and recorded rows.

**Verified as stated (no change):**
- 62 instancegen tests pass; 5 repo-root tests pass; staging tests (58) pass
  when run from inside `cluster_staging_maxsat/` (from the repo root they
  import the repo `src` and 13 fail — a cwd convention, not a defect).
- RC2 configuration: `RC2(wcnf, solver="g3")` with PySAT 1.9.dev15 defaults
  `adapt=False, exhaust=False, incr=False, minz=False, process=0, trim=0`
  (`inspect.signature(RC2.__init__)`), identical in `src/` and the staging
  copy (`diff` clean for `profile_hardness.py` and `solve_rc2_anytime.py`).
- "c\* UNSAT calls + 1 SAT call" for unit weights: `RC2.compute_` loops one
  oracle call per core and `process_core` does `cost += minw` with
  `minw = 1`; `exhaust`/`minz`/`trim` are the only sources of extra calls and
  are off.
- Pilot rows (`results/profile/gen_pilot_cap60.jsonl`, 25 rows): the §2.2
  summary matches row by row (n = 50 certifies α ≤ 8 at 0.003 / 2.8 / 52.9 s;
  n = 70 α ≤ 6; n = 100 α = 5 seed-dependent; 2-SAT n = 100 α = 4 → 25 in
  5.5 s, α = 6 / 10 LB 47 / 84). Killed rows show `solve_s` = 75 = cap + 15
  grace, confirming the censoring caveat.
- Memetic record fields (`stop_reason`, `time_to_target_s`, `status`,
  `config_hash`, …) exist in the staging `run_memetic_shard.py` (schema v2);
  `stop_reason` values are `target | time_cap | max_gens` (`evo/memetic.py`).
- Tier-2 memetic: 118/130 successes, ERT 9.2–687 s
  (`archive/TIER2_ABLATION_FAIRNESS_AUDIT.md` per-instance table).
- Grid arithmetic: every cell's `m = round(α·n)` (e.g. 298 at n = 70,
  α = 4.26; 1065 at n = 250), 36 cells, 180 unique filenames.

**Corrected in the goals doc (r2), with reasons:**
1. **Concurrency.** Planned `%20` → `%30` for both arms (the cluster allows
   30 concurrent single-CPU tasks). Elapsed compute at %30: A1 6 waves ≈
   1.6–1.7 h, A2 ≤ 18 waves ≈ 4.8 h; CPU-hours unchanged (48 / 144 worst
   case); queue delay kept as a separate, unestimated quantity. The claim
   that `%20` was "the setting the committed tier-2 runs used" was wrong for
   the memetic arm: the RC2 screens ran `%20` (sbatch headers), the tier-2
   memetic/multistart arrays were submitted at `%30` (`archive/TIER2_TARGET_STOP.md`,
   `readme.txt`). Both recorded as history in §4.3.
2. **Paths.** All array drivers live under `cluster_staging_maxsat/scripts/`,
   not `scripts/`; table and §7 fixed.
3. **uuf250 comparison point.** "RC2 35–500 s" → 63–496 s on the 18 cap-900
   tier-2 instances (14.6–496 s over all 26 completions of the 35-row
   profile); the 26-instance set includes two uuf200 (n = 200, c\* = 2) and
   8 instances profiled at cap 600 (`tier2_oracle.csv`).
4. **Outcome classes (§4.4).** "Everything else is right-censored" lumped
   software errors with budget timeouts. Now three classes — completed /
   censored at budget / failed — with the exact status values for each;
   failed rows are re-run, never censored, and block batch completion.
   `unsat` (impossible on pure-soft) and memetic `max_gens` / `status != ok`
   are failures.
5. **Spearman CI (§5.2).** "Fisher-z 95 % CI" replaced by: instance as the
   sampling unit (seeds collapsed to ERT / success rate first); primary CI a
   cell-stratified instance bootstrap (B = 10 000, BCa + percentile);
   analytic check Fisher z with the Bonett–Wright Spearman SE
   √((1 + ρ²/2)/(n − 3)); within-cell ρ not estimated (5 instances); the
   "certified ∧ ≥ 1 success" selection stated with counts, and a sensitivity
   run with 0-success instances top-tied; RC2 timing noise named as an
   unestimated attenuation source.
6. **Conditionality and diversity.** §1 gains an explicit statement that
   every ρ / yield / band is conditional on the chosen cells, budgets and
   certification/success criteria; §5.5 states that broader family diversity
   remains a research objective after M5, not a fallback.
7. **Git tracking.** `cluster_staging_maxsat/data/` was ignored wholesale, so
   the planned `manifest.jsonl` there would never have been committed.
   `.gitignore` now excludes files under it but re-includes
   `data/generated/**/manifest.jsonl` (same trick as the repo-root
   `data/generated` rule).
8. **M1 wording.** "submit A1" → "prepare A1"; a job id is recorded only
   when `sbatch` has returned one.

**Not changed (reviewed and kept):** the 36-cell / 5-seed grid including the
two corners expected to be censored (the censoring boundary is a
measurement); 3 memetic seeds per certified instance in `calib_a` (noted as
coarse: success rate ∈ {0, ⅓, ⅔, 1}); the §5.3 threshold proposals — these
are not to be tuned toward any ρ and were not touched; ERT definition (Σ wall
over all seeds / successes, failures charged the 900 s budget — the standard
ERT, consistent with `wall_time_s` = budget on `time_cap` rows).

### Part B — M1 implemented

| Deliverable | Path | Status |
|---|---|---|
| Grid as data | `instancegen/grids/calib_a.yaml` | 36 cells, seeds 1–5, `hard_ratio 0`, `w_max 1`, dialect `old` |
| Generator CLI | `instancegen/cli.py` (`generate-grid`, `--check`) | writes instances, `manifest.jsonl`, Slurm manifest, `.sha256` |
| Instances | `cluster_staging_maxsat/data/generated/calib_a/*.wcnf` | 180 files, 2.4 MB, git-ignored, byte-reproducible |
| Manifest | `cluster_staging_maxsat/data/generated/calib_a/manifest.jsonl` | 180 rows, tracked; `git_sha 0dc3bc3…`, `created_utc 2026-09-16` |
| Slurm manifest | `cluster_staging_maxsat/scripts/manifest_calib_a_rc2.txt` + `.sha256` | line N = task N; `sha256sum -c` → 180 OK |
| Array driver | `cluster_staging_maxsat/scripts/rc2_profile_array.sbatch` | `MANIFEST/OUTDIR/CAP/GRACE`, resume skip, `task_N.env.json`, `LOCAL_SMOKE=1` |
| Resume logic | `cluster_staging_maxsat/scripts/rc2_row_state.py` | stdlib; per-task state and `--pending` id list |
| Submit wrapper | `cluster_staging_maxsat/scripts/submit_rc2_profile.sh` | `THROTTLE` (30), `RESUME`, `DRY_RUN`, sha check |
| Tests | `instancegen/tests/test_cli.py` (9), `cluster_staging_maxsat/tests/test_rc2_row_state.py` (16) | all pass |
| Docs | `cluster_staging_maxsat/readme.txt` §calib_a; goals doc r2 | |

**Manifest order** (matters for task ids): families as listed in the grid
(max3sat then max2sat), n ascending, α ascending, seed 1–5. Tasks 1–100 are
3-SAT, 101–180 are 2-SAT; e.g. task 11 = 3-SAT n = 50 α = 6 seed 1, task 96 =
3-SAT n = 250 α = 8 seed 1, task 111 = 2-SAT n = 100 α = 4 seed 1.

**Tests run:**
- `python -m pytest instancegen -q` → **71 passed** (62 + 9 new).
- `cd cluster_staging_maxsat && python -m pytest tests -q` → **74 passed**
  (58 + 16 new).
- `python -m pytest tests -q` (repo root) → 5 passed.
- `python -m instancegen.cli generate-grid … --check` → `CHECK OK: 180`.
- `bash -n` on both shell scripts; `DRY_RUN=1 bash submit_rc2_profile.sh` →
  `sbatch --array=1-180%30 --export=ALL,MANIFEST=scripts/manifest_calib_a_rc2.txt,OUTDIR=results/profile_calib_a,CAP=900,GRACE=60 rc2_profile_array.sbatch`.

**Local smoke through the real sbatch file** (`LOCAL_SMOKE=1`, `CAP=20`,
`GRACE=10`, output in the session scratchpad — not a measurement):
- task 11 (3-SAT n = 50 α = 6 s1): `optimal`, c\* = **6** in 4.9 s — the
  pilot's optimum (pilot 2.8 s on its machine; Checkpoint 0 measured 4.9 s
  here).
- task 111 (2-SAT n = 100 α = 4 s1): `optimal`, c\* = **25** in 9.7 s — the
  pilot's optimum.
- task 96 (3-SAT n = 250 α = 8 s1): `timeout` at 20 s, LB 2 — censored
  path; re-run at `CAP=30` → `run:censored_lower_cap`, then
  `subprocess_killed` at 40.0 s (= 30 + 10 grace) with LB 3 recovered from
  the progress file.
- Re-invoking tasks 11 and 96 at `CAP=20` → `skip:completed` /
  `skip:censored`, no RC2 run, exit 0. `RESUME=1 DRY_RUN=1` over the smoke
  dir → `--array=1-10,12-95,97-110,112-180%30`.
- `task_N.env.json` records `pysat_version 1.9.dev15`, python 3.12.3, host.

The pilot's instance files lived in a scratch directory that no longer
exists, so byte-identity with the pilot could not be checked directly; the
two shared cells reproduce the pilot optima, and the filenames are the
pilot's, from the same `GenParams`.

### Jobs / commands

**None submitted.** No `sbatch` or ssh alias on this workstation. A1 is
prepared; the exact commands are in the M1 handoff (below) and in the goals
doc §7. `<user>@<cluster>` is a placeholder for the login-node address.

```bash
# 1. workstation → cluster (carries data/generated/calib_a/, 180 files, 2.4 MB)
cd /home/mashe/maxsat-lab_new/maxsat-lab
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# 2. login node: verify, dry-run, submit
ssh <user>@<cluster>
cd ~/maxsat-lab && sha256sum --quiet -c scripts/manifest_calib_a_rc2.sha256 && echo SHA_OK
cd ~/maxsat-lab/scripts && mkdir -p logs
DRY_RUN=1 bash submit_rc2_profile.sh        # expect: 180 rows, array 1-180 %30, cap 900 + 60
bash submit_rc2_profile.sh                  # prints "Submitted batch job <JOBID>" -- record it here

# 3. monitor / resume
squeue -u $USER
sacct -j <JOBID> --format=JobID,State,Elapsed,Submit,Start,End -X | head
RESUME=1 bash submit_rc2_profile.sh         # only if some tasks lack a valid row

# 4. cluster → workstation
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_a/ cluster_staging_maxsat/results/profile_calib_a/
```

Expected A1 accounting: 180 tasks × ≤ 960 s = ≤ 48 CPU-h; at `%30`, 6 waves
of ≤ ~17 min ≈ 1.7 h of compute, excluding queue delay (read it from the
`sacct` Submit/Start stamps). Roughly half the tasks should finish in
seconds (pilot), so the real elapsed time will be shorter.

### Files touched in this checkpoint (uncommitted)

```
M  .gitignore
M  docs/CORPUS_CALIBRATION_GOALS.md
M  docs/CORPUS_CALIBRATION_LOG.md
M  cluster_staging_maxsat/readme.txt
A  instancegen/cli.py
A  instancegen/grids/calib_a.yaml
A  instancegen/tests/test_cli.py
A  cluster_staging_maxsat/data/generated/calib_a/manifest.jsonl
A  cluster_staging_maxsat/scripts/manifest_calib_a_rc2.txt
A  cluster_staging_maxsat/scripts/manifest_calib_a_rc2.sha256
A  cluster_staging_maxsat/scripts/rc2_profile_array.sbatch
A  cluster_staging_maxsat/scripts/rc2_row_state.py
A  cluster_staging_maxsat/scripts/submit_rc2_profile.sh
A  cluster_staging_maxsat/tests/test_rc2_row_state.py
   (180 .wcnf files under cluster_staging_maxsat/data/generated/calib_a/ — ignored)
```

### Next milestone — M2 (after A1 returns; awaiting approval)

`make_calib_memetic_manifest.py` reading `results/profile_calib_a/*.jsonl`
(last row per instance, §4.4 classes), 3 seeds × certified instances,
`STOP_AT_ORACLE=1`, budget 900, `%30`; the not-run list for uncertified and
failed instances. Before M2 can start, A1 must have been submitted and its
job id and `sacct` stamps recorded above.

### M1 handoff summary (as reported at the end of Checkpoint 1, 2026-09-16)

Both parts are done; the work tree is left **uncommitted** (no commit was
requested) and **nothing was submitted to Slurm** — no `sbatch`/ssh alias
exists on this workstation.

**Part A — review of the two documents**

*Sound (verified, kept):* the RC2 configuration and the "c\* UNSAT calls + 1
SAT call" claim (checked against PySAT 1.9.dev15's `compute_`/`process_core`);
the pilot summary matches `gen_pilot_cap60.jsonl` row by row; the memetic
record fields exist in the staging runner; the 118/130 tier-2 figure; the ERT
definition (failures charged the 900 s budget — consistent with `wall_time_s`
on `time_cap` rows); the 36-cell/5-seed grid and its censored corners; the
§5.3 threshold proposals (untouched — not tuned toward any ρ).

*Corrected in `CORPUS_CALIBRATION_GOALS.md` (r2), reasons in Part A above:*
1. Concurrency `%20 → %30`, elapsed recalculated as waves (A1: 6 waves ≈
   1.6–1.7 h; A2: ≤ 18 waves ≈ 4.8 h), CPU-hours unchanged (48/144), queue
   delay explicitly separate. The claim that `%20` was the tier-2 setting was
   wrong for memetic (`%30`); both are recorded as history.
2. Paths: drivers are under `cluster_staging_maxsat/scripts/`.
3. uuf250 comparison point: 63–496 s (not 35–500), and the 26-instance set
   includes two n = 200 instances and eight profiled at cap 600.
4. §4.4 now has three outcome classes — completed / censored-at-budget /
   failed — with exact status values; errors, `unsat`, memetic
   `status != ok` and `max_gens` are failures to re-run, never censored.
5. Spearman CI: instance = sampling unit (seeds collapsed first); primary CI
   a cell-stratified instance bootstrap (BCa), analytic check Fisher-z with
   the Bonett–Wright Spearman SE; within-cell ρ not estimated at 5
   instances; selection counts and a top-tied sensitivity run; timing noise
   named.
6. Explicit conditionality statement in §1; family diversity kept as a
   post-M5 research objective in §5.5.
7. `.gitignore`: `cluster_staging_maxsat/data/` was fully ignored, so the
   planned `manifest.jsonl` would never have been committed — narrowed so
   only `data/generated/**/manifest.jsonl` is tracked.

*Uncertain:* the pilot's instance files no longer exist, so byte-identity
with the pilot could not be checked directly (the shared cells reproduce its
optima, c\* = 6 and c\* = 25). RC2 timing noise across cluster nodes is
unmeasured. Whether the "informative strip" exists at all is the
calibration's first-order result, not something the review can settle.

**Part B — M1 delivered**

- `instancegen/grids/calib_a.yaml`, `instancegen/cli.py` (`generate-grid`,
  `--check`); 180 instances + `manifest.jsonl` under
  `cluster_staging_maxsat/data/generated/calib_a/`;
  `scripts/manifest_calib_a_rc2.txt` + `.sha256`.
- `scripts/rc2_profile_array.sbatch` (`MANIFEST/OUTDIR/CAP/GRACE`, resume
  skip, `task_N.env.json` with PySAT version), `rc2_row_state.py` (resume
  logic), `submit_rc2_profile.sh` (`THROTTLE=30`, `RESUME=1`, `DRY_RUN=1`,
  sha check).
- Tests: instancegen 71 passed (62 + 9), staging 74 passed (58 + 16, run from
  inside `cluster_staging_maxsat/`), repo root 5 passed. Local smoke through
  the real sbatch file at cap 20: c\* = 6 in 4.9 s, c\* = 25 in 9.7 s, one
  censored row, skip / raised-cap / RESUME paths all exercised.

**What to run next** (`<user>@<cluster>` is the only placeholder)

```bash
# workstation → cluster
cd /home/mashe/maxsat-lab_new/maxsat-lab
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# login node
ssh <user>@<cluster>
cd ~/maxsat-lab && sha256sum --quiet -c scripts/manifest_calib_a_rc2.sha256 && echo SHA_OK
cd ~/maxsat-lab/scripts && mkdir -p logs
DRY_RUN=1 bash submit_rc2_profile.sh     # expect: 180 rows, --array=1-180%30, cap 900 + 60
bash submit_rc2_profile.sh               # → "Submitted batch job <JOBID>"
```

Record the job id here (and later
`sacct -j <JOBID> --format=JobID,State,Elapsed,Submit,Start,End -X`). When
it finishes:
`rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_a/ cluster_staging_maxsat/results/profile_calib_a/`,
then M2 (memetic manifest on the certified subset) — awaiting approval.

To commit the M1 state first: `git add -A && git commit` picks up exactly
the files listed under "Files touched in this checkpoint" (the 180 `.wcnf`
files stay ignored).

---

## 2026-09-22 — Checkpoint 2: A1 returned, 180/180 rows, aggregated

Against commit `42f953e` (M1 committed). Work tree at the end of this
checkpoint is **uncommitted**: the rsynced `results/profile_calib_a/` tree,
the two aggregate files, and this entry. No code changed.

### What was verified

- **Row accounting: 180 manifest lines, 180 rows, 0 gaps, 0 superseded.**
  Every `results/profile_calib_a/task_N.jsonl` (N = 1..180) holds exactly
  one row; its `instance` equals manifest line N. No task was re-run over
  an existing row, so "last row per instance" and "only row" coincide.
- **§4.4 classes (RC2, cap 900 s + 60 s grace):**

  | class | count | rule |
  |---|---|---|
  | completed | **92** | `profile.completed == true` (all `status: optimal`) |
  | censored at budget | **88** | `subprocess_killed` 82 + `timeout` 6, all at `cap_s = 900` |
  | failed | **0** | no `error`/`unsat`, no empty output |

  All 82 killed rows carry a recovered `cost_lower_bound` (progress-file
  path exercised on every one). Slowest completion 772 s; 12 completions
  above 60 s, 2 above 600 s. The `tier` field (T1 80 / T2a 9 / T2b 1 /
  T3 90) counts those two 600–900 s completions as T3 — the known
  `assign_tier()` artefact noted in `rc2_profile_array.sbatch`; the
  calibration reads `completed`/`solve_s`, not `tier`.
- **Cell picture, 36 cells × 5 seeds** (read-out proper is the next turn):
  16 cells fully completed, 16 fully censored, 4 mixed (n = 100 2-SAT
  α = 6: 1/5; n = 150 2-SAT α = 3: 4/5; n = 150 3-SAT α = 5: 3/5;
  n = 250 3-SAT α = 4.26: 4/5). Every censored cell is at or above the
  fully-completed cells of the same (n, k) in α, i.e. hardness is monotone
  in α within each (n, k) row at this cap.
- **PySAT version mismatch — reported per §4.1, not accepted silently.**
  Every one of the 180 `task_N.env.json` records `pysat_version
  "1.9.dev3"`, python 3.11.15 (the cluster `maxsat` env). The plan holds
  1.9.dev15 fixed (goals §4.1; workstation smoke was dev15 / python
  3.12.3). The version is uniform across all 180 tasks and all five
  submissions, so A1 is internally consistent. Cross-check on the two
  smoke instances: task 11 (3-SAT n = 50 α = 6 s1) c\* = 6 in 4.5 s on the
  cluster vs 4.9 s here; task 111 (2-SAT n = 100 α = 4 s1) c\* = 25 in
  8.1 s vs 9.7 s here — optima identical. **Decision needed:** either
  freeze 1.9.dev3 as the calibration's RC2 version (amend goals §4.1 and
  the sbatch comment; A2/M4/M5 then run against the same cluster env) or
  upgrade the cluster env to dev15 and re-run A1. Recommendation: freeze
  dev3 — the 92 optima are what the memetic arm certifies against, and
  they do not depend on the dev-tag; only timings would move, and A1's
  timings are already cross-node noise (29 distinct hosts, four node
  families: `ise-cpu-intl` 78, `ise-cpu128` 69, `ise-cpu256` 28, `cs-cpu`
  5).
- **Aggregate files rebuilt from the per-task files**, not patched:
  `results/profile_calib_a_all.jsonl` (180 rows) is
  `{"task": N, **last row of task_N.jsonl, "env": last line of
  task_N.env.json minus task/instance}`, sorted by task;
  `results/profile_calib_a_env.jsonl` (180 rows) is the last env line per
  task. Before rewriting, the rule was checked to reproduce all 178
  previously aggregated rows byte-for-byte; the diff against the previous
  files is exactly: tasks 39 and 40 inserted in `_all`, and their `_env`
  lines replaced (the earlier `_env` carried the Sep 16 attempt's
  provenance for a row that did not exist). The aggregation is a scratchpad
  script — not yet in the tree; see "Next".

### Jobs / commands

A1 was submitted as **five arrays**, not the single `1-180%30` the plan
assumed (task ranges and the UTC of each task's env stamp, which is written
just before RC2 starts):

| array job | tasks | env stamps (UTC) |
|---|---|---|
| 21411811 | 1–30 | 2026-09-16 14:10:00 → 14:15:25 |
| 21411927 | 31–60 (28 rows) | 2026-09-16 14:16:30 → 14:22:35 |
| 21543641 | 61–120 | 2026-09-22 07:12:33 → 07:29:19 |
| 21545479 | 121–180 | 2026-09-22 07:38:50 → 07:55:59 |
| 21547921 | 39, 40 (re-run) | 2026-09-22 08:36:50 → 08:36:52 |

Tasks 39 and 40 (both n = 70 3-SAT α = 8) started under 21411927 (env
lines from 14:22:20 / 14:22:28, hosts `ise-cpu128-05` / `-12`) but left no
row — the §4.4 class-3 "Slurm killed the task" signature (the profiler
writes the row only after the subprocess returns). Their `task_N.env.json`
keeps both lines; the re-run (`resume_state: run:absent`, hosts
`ise-cpu-intl-22` / `-19`) produced the two rows now aggregated, both
`subprocess_killed` at 960 s with LB 9, matching the other three seeds of
that cell. Cause of the first-attempt loss not established from here (no
`logs/rc2-profile-21411927_39.{out,err}` in the rsynced tree); if the
cluster `sacct` shows `TIMEOUT` for `21411927_39/40`, the 20-min `--time`
was the cause and should be raised to 25 min before A2.

`sacct` stamps **not recorded** — no cluster access from this workstation.
To fill in, run on the login node and paste here:

```bash
sacct -j 21411811,21411927,21543641,21545479,21547921 \
      --format=JobID,State,Elapsed,Submit,Start,End -X | head -20
sacct -j 21411927_39,21411927_40 --format=JobID,State,Elapsed,MaxRSS,Timelimit
```

### Files touched in this checkpoint (uncommitted)

```
M  docs/CORPUS_CALIBRATION_LOG.md
A  cluster_staging_maxsat/results/profile_calib_a/task_{1..180}.jsonl      (180 files)
A  cluster_staging_maxsat/results/profile_calib_a/task_{1..180}.env.json   (180 files)
A  cluster_staging_maxsat/results/profile_calib_a_all.jsonl                (180 rows)
A  cluster_staging_maxsat/results/profile_calib_a_env.jsonl                (180 rows)
```

To commit: `git add docs/CORPUS_CALIBRATION_LOG.md cluster_staging_maxsat/results/profile_calib_a cluster_staging_maxsat/results/profile_calib_a_all.jsonl cluster_staging_maxsat/results/profile_calib_a_env.jsonl && git commit`.

### Next (awaiting approval)

1. **A1 read-out** — completed / censored per cell, `solve_s` spread of the
   completed rows, and the certified-subset size that M2 will run on
   (92 instances, 16 full cells + 4 partial). Short markdown, this session.
2. **Aggregation into the tree** — `scripts/aggregate_rc2_profile.py`
   (per-task → `_all` / `_env`, last row per task, superseded count), so
   calib_b and M4 use the same rule as above.
3. **M2** as recorded at Checkpoint 1, on the 92 certified instances
   (3 seeds → 276 tasks at `%30`), after the PySAT decision above is taken.

### Addendum (same day) — A1 read-out written

`docs/CALIB_A_A1_READOUT.md`: per-cell table (36 cells), wall location per
(n, k) row, cap placement, RC2-side pre-screen of the §5.3 rules, and the
M2 subset. Headline: the strip exists and is diagonal (H3), but it is one
grid step wide and falls between grid lines in 5 of 9 rows; 5 cells pass
the RC2 half of the proposed rules, 3 miss narrowly; 70 of the 92 certified
instances are sub-10 s for RC2. Points to a `calib_b` α-refinement round;
whether it precedes M2 is the next decision. Item 1 of "Next" above is
done; items 2–3 still await approval.

---

## 2026-09-22 — Checkpoint 3: calib_b prepared (grid refinement before M2)

Against commit `ccf2735` (calib_a A1 results committed). Work tree at the end
of this checkpoint is **uncommitted**. **No job was submitted** — this
workstation has no cluster access (goals §7); the commands are below.
**M2 was not run.**

### Decision: grid refinement precedes M2, and why

The A1 read-out recommended M2 first. That is superseded here. The reason is
a count, not a preference:

| A1 outcome (180 instances) | count |
|---|---:|
| certified (RC2 proved c\*) | 92 |
| certified **and** `60 s < solve_s ≤ 600 s` — the repo's Tier-2 window | **10** |
| certified and `60 s < solve_s ≤ cap` (`include_solved_t3` reading) | 12 |
| certified and `solve_s ≥ 30 s` (sensitivity only, not an adopted rule) | 17 |
| certified and `solve_s < 10 s` | 70 |
| censored at 900 s | 88 |

**The immediate bottleneck is the number and runtime spread of
RC2-nontrivial, certified instances, not the memetic arm.** Tier 2 excludes
RC2-trivial instances by construction, so M2's 276 tasks (≤ 69 CPU-h) would
be spent mostly on the 70 sub-10-second instances and would produce a memetic
read-out over an eligible population of 10 instances drawn from 6 cells, 3 of
them from a single cell. Refining the grid first costs less (≤ 29.3 CPU-h),
and it changes the size of the set M2 runs on. Goals §3 already reserves
`calib_b` for exactly the finding A1 produced — the informative strip is one
grid step wide and falls between grid lines in 5 of 9 (n, k) rows.

Plan written before any implementation: **`docs/CALIB_B_PLAN.md`**.

### Tier 2 — the established definition was checked, not replaced

`assign_tier()` (`src/cli/profile_hardness.py`) has held `T1_MAX_S = 60`,
`T2A_MAX_S = 300`, `T2B_MAX_S = 600` since the tier-2 runs; an instance is
Tier 2 iff RC2 **completed** and `60 s < solve_s ≤ 600 s`.
`make_tier2_manifest.py`'s `include_solved_t3` rescue extends the upper edge
to the batch cap. The 30–900 s band discussed when this round was requested
is **not** that rule: the repository's floor is 60 s, not 30 s. No threshold
constant was edited. The ≥ 30 s count is carried as a labelled sensitivity
column (it would take calib_a from 10 eligible to 17); adopting it is a
decision for this log, with a reason, not a side effect of a refinement round.
**Open.**

Kept separate throughout (plan §2): **cell-level** rules (goals §5.3,
certified ≥ 4/5 and median `solve_s` ≥ 10 s) decide where to *sample*;
**per-instance** rules decide what is *eligible*. A cell median above the
threshold does not make its seeds eligible, and three calib_a instances are
eligible from cells that fail the cell rule (2-SAT n = 100 α = 4 s3 at 174 s;
3-SAT n = 100 α = 5 s2 at 93 s; 3-SAT n = 150 α = 5 s3 at 772 s, over the
600 s edge).

### The grid: 22 cells, 110 instances

`instancegen/grids/calib_b.yaml`. α refined at fixed (n, k) within every row.
Placement is from A1's measured per-row `dc*/dm` and `d log10(solve_s)/dc*`
slopes, fitted per row because they differ by ~3× across rows — c\* is used
inside a row, never as a global predictor of RC2 time.

- **17 exploratory cells, seeds 1–5** (plan §4a). Two α per row: one inside
  the certified side of the bracket, one nearer the wall. Three rows are
  refined *downward* from the first censored cell (2-SAT n = 250, n = 400;
  3-SAT n = 150) and 3-SAT n = 250 sits barely above its existing α — higher
  α is not assumed to be the needed direction. 3-SAT n = 50 is the one row
  refined upward, because its wall is outside the calib_a grid.
  - 3-SAT: n = 50 {8.5, 9.0}; n = 70 {6.2, 6.5}; n = 100 {5.2, 5.5};
    n = 150 {4.6, 4.8}; n = 250 {4.35}
  - 2-SAT: n = 100 {4.5, 5.0}; n = 150 {3.15, 3.30}; n = 250 {2.35, 2.50};
    n = 400 {2.15, 2.30}
- **5 reinforcement cells, seeds 6–10** (plan §4b): the five cells that pass
  the RC2 half of the §5.3 rules on A1 (2-SAT n = 150 α = 3, n = 400 α = 2;
  3-SAT n = 50 α = 8, n = 70 α = 6, n = 250 α = 4.26). Seeds 6–10 are
  disjoint from calib_a's 1–5 and from M4's 1001–1020, so nothing is
  regenerated. **Consequence to carry downstream: these five cells now hold
  10 seeds against 5 elsewhere — certified fraction is x/10 there, and every
  table must state the unequal cell sizes.**

Not in this round: n refinement (the strongest calib_c candidate is 3-SAT
α = 4.26 at n ≈ 180–200, between n = 150's 0.04 s median and n = 250's 166 s);
raising the cap; any recursive search.

### Configuration preserved

Cap **900 s** + 60 s grace, `RC2(wcnf, solver="g3")` with
`adapt=exhaust=minz=False`, `rc2_profile_array.sbatch` / `submit_rc2_profile.sh`
unchanged, same generator conventions (pure soft, `w_max = 1`, uniform,
`m = round(α·n)`, old dialect). Nothing in the solver environment was
upgraded, installed or re-pinned.

**PySAT (Checkpoint 2's open item) — still open, and not pre-empted.**
calib_b runs on the same cluster `maxsat` env that produced A1's uniform
1.9.dev3. Comparability rests on the env being *recorded per task* rather
than assumed: `task_N.env.json` carries `pysat_version`, and
`aggregate_rc2_profile.py` (new, below) prints the per-batch version spread
and warns if a batch is not uniform. If the cluster env has moved since
2026-09-22 the aggregation will say so, and calib_b is not pooled with
calib_a until that is resolved. Optima are version-robust (Checkpoint 2's
two cross-checks gave identical c\*); only timings move, and they already
carry A1's 29-host spread. Running B1 under A1's env is the option that keeps
both Checkpoint 2 choices (freeze dev3 / upgrade and re-run both) available.

### Implemented

| file | what |
|---|---|
| `docs/CALIB_B_PLAN.md` | the plan (new) — selection rule, grid, budget, comparability, what the results decide |
| `instancegen/grids/calib_b.yaml` | the 22-cell grid (new) |
| `instancegen/cli.py` | per-family `seeds:` override, so a refinement batch can re-sample an existing cell at fresh seeds; `cell_seeds()`; the summary line now prints seeds-per-cell |
| `instancegen/tests/test_cli.py` | 7 new tests: calib_b shape (22 cells / 110 instances), exploratory-vs-reinforcement split, reinforcement cells exist in calib_a and exploratory cells do not, shared generator conventions, filenames disjoint from calib_a, per-family seeds end-to-end, bad per-family seeds rejected |
| `cluster_staging_maxsat/scripts/aggregate_rc2_profile.py` | per-task → `_all` / `_env`, the rule applied by hand at Checkpoint 2, now in the tree (new; Checkpoint 2 "Next" item 2) |
| `src/bench/calib_tier2_select.py` | per-instance Tier-2 eligibility across batches, deduplicated on `instance_sha256`; emits `tier2_eligible.csv` + `tier2_cells.csv` (new) |
| `cluster_staging_maxsat/data/generated/calib_b/` | 110 instances (gitignored) + `manifest.jsonl` (tracked) |
| `cluster_staging_maxsat/scripts/manifest_calib_b_rc2.{txt,sha256}` | 110 lines, line N = array task N |

### Validation performed on this workstation

- `python -m pytest instancegen -q` → **79 passed**.
- `generate-grid` → 110 files written; `--check` re-generates in memory and
  passes; `sha256sum -c scripts/manifest_calib_b_rc2.sha256` → 110/110 OK.
- `aggregate_rc2_profile.py --batch calib_a --check` reproduces the
  Checkpoint 2 aggregates **byte-for-byte** (180 rows; 92 completed / 88
  censored / 0 failed; PySAT 1.9.dev3 × 180; 29 hosts).
- `calib_tier2_select.py --batches calib_a` reproduces the read-out
  independently: 10 / 12 / 17 eligible under the three windows, 5 of 36 cells
  pass the §5.3 cell rule.
- Smoke through the real sbatch file (`LOCAL_SMOKE=1`, workstation PySAT
  1.9.dev15), 6 calib_b tasks, caps 20 / 60 s: both classes exercised —
  4 completed rows and 2 `subprocess_killed` rows with `cost_lower_bound`
  recovered from the progress file. Outputs written to a scratch dir and
  deleted; no calib_b result rows exist in the tree.
- `DRY_RUN=1` submit → `sbatch --array=1-110%30`; `RESUME=1` against the
  smoke rows correctly skipped the 4 completed tasks and re-listed the 2
  censored-at-a-lower-cap ones (`array=1-30,35-110`).

### Two findings from the smoke run

1. **Negative `solve_s` is possible.** Task 34 returned
   `status=optimal solve_s=-0.827`. The outer profiler times with
   `time.monotonic()`, but the value reported for a *completed* run is the
   child's `elapsed_s`, which `solve_rc2_anytime.py` computes from
   `time.time()` — a wall clock, so a clock step (WSL2 here) yields a
   nonsense duration. **A1 has 0 occurrences in 180 rows** (min completed
   `solve_s` 0.003 s), so nothing measured is affected. Not repaired: the
   measurement path is frozen for the calibration, and changing it between A1
   and B1 would break the "same code" invariant. Instead
   `aggregate_rc2_profile.py` detects and warns, and `calib_tier2_select.py`
   classifies such a row as §4.4 class 3 (failed), never as a fast solve.
   Note `rc2_row_state.py` would still treat it as `skip:completed`, so a
   re-run needs the task id passed by hand. **Open, low priority.**
2. **3-SAT n = 150 α = 4.6 may be the trivial edge.** The five seeds at
   dev15 / cap 60 s gave c\* = 0, 1, 1, 1 in 0.1–0.6 s and one censored at
   LB 3 — i.e. the same c\* = 1 vs c\* = 3 split the α = 5 cell shows, but
   faster. One seed may still certify in the 60–600 s window at cap 900. The
   cell stays: trivial and censored outcomes are what locate the edges
   (§4.4), and re-placing a cell on five workstation rows under a different
   PySAT build would be exactly the ad-hoc refinement this round avoids.

### Jobs / commands — prepared, not submitted

```bash
# 1. workstation -> cluster (carries data/generated/calib_b/, 110 files, 1.2 MB)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# 2. login node: verify, dry-run, submit B1
cd ~/maxsat-lab/scripts && mkdir -p logs
cd .. && sha256sum -c scripts/manifest_calib_b_rc2.sha256 | tail -1 && cd scripts
DRY_RUN=1 MANIFEST=manifest_calib_b_rc2.txt OUTDIR=results/profile_calib_b \
    bash submit_rc2_profile.sh          # expect: 110 tasks, 1-110%30, cap 900
MANIFEST=manifest_calib_b_rc2.txt OUTDIR=results/profile_calib_b \
    bash submit_rc2_profile.sh          # submit; record the job id here

# 3. monitor / resume (a task killed by --time leaves no row)
squeue -u $USER
RESUME=1 MANIFEST=manifest_calib_b_rc2.txt OUTDIR=results/profile_calib_b \
    bash submit_rc2_profile.sh

# 4. cluster -> workstation, then aggregate and select here
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_b/ \
      cluster_staging_maxsat/results/profile_calib_b/
cd cluster_staging_maxsat && python3 scripts/aggregate_rc2_profile.py --batch calib_b && cd ..
python -m src.bench.calib_tier2_select --batches calib_a calib_b
```

`--time` note from Checkpoint 2: tasks 39/40 of A1 left no row under the
20-minute wall. If `sacct` shows `TIMEOUT` for `21411927_39/40`, submit B1
with `-- --time=00:25:00` appended to the submit command.

### Budget

| batch | tasks | per task | CPU-h (worst case) | elapsed at %30 |
|---|---:|---|---:|---|
| B1 RC2, calib_b | 110 | 1 CPU · 8 GB · ≤ 960 s | **29.3** | ⌈110/30⌉ = 4 waves ≈ 1.1 h |

Queue delay excluded (record from `sacct`). No memetic tasks in this round.

### Files touched in this checkpoint (uncommitted)

```
M  instancegen/cli.py
M  instancegen/tests/test_cli.py
M  docs/CORPUS_CALIBRATION_LOG.md
A  docs/CALIB_B_PLAN.md
A  instancegen/grids/calib_b.yaml
A  src/bench/calib_tier2_select.py
A  cluster_staging_maxsat/scripts/aggregate_rc2_profile.py
A  cluster_staging_maxsat/scripts/manifest_calib_b_rc2.txt
A  cluster_staging_maxsat/scripts/manifest_calib_b_rc2.sha256
A  cluster_staging_maxsat/data/generated/calib_b/manifest.jsonl   (110 instances gitignored)
A  results/calibration/tier2_{eligible,cells}.csv                 (calib_a only, regenerated per batch)
```

### Next (awaiting approval)

1. **Submit B1** on the login node and record the job id and `sacct` stamps.
2. **B1 read-out** when it returns: per-cell table for the 22 cells, then the
   pooled calib_a ∪ calib_b eligibility counts under the three windows.
3. **Then** decide, per plan §7: stop refining and run M2; or one further
   round in the thin rows; or move the remaining effort to reinforcement
   seeds. M2 stays unrun until that decision.
4. Open items carried forward: the PySAT dev3/dev15 freeze (Checkpoint 2);
   whether to lower the Tier-2 floor to 30 s; and whether the reported Tier-2
   population is built from calibration batches at all — goals §5.4 says the
   final corpus is regenerated at seeds 1001–1020 and that calibration rows
   never enter a reported ρ. `calib_tier2_select.py` builds the manifest
   either way; the default remains §5.4 until this log says otherwise. Any ρ
   eventually reported describes the selected Tier-2 population under this
   stack, this cap and these rules — not random Max-k-SAT.

---

## 2026-09-22 — Checkpoint 4: B1 returned; calib_b read out; α refinement closed

Against commit `c9e62b9` (Checkpoint 3 committed). B1 ran on the cluster and
the results were rsynced back. Aggregated and analysed on the workstation; no
job was submitted from here. **M2 is still not run.**

Read-out: **`docs/CALIB_B_B1_READOUT.md`** (new). The plan it is scored
against is `docs/CALIB_B_PLAN.md`, written before any calib_b instance
existed.

### What came back

| | |
|---|---|
| rows | 110 / 110 tasks, 0 missing, 0 superseded, **0 failed** |
| §4.4 classes | 85 completed, 25 censored at cap |
| env | `pysat 1.9.dev3` × 110, python 3.11.15 × 110 — **uniform and identical to A1** |
| hosts | 18 distinct (A1: 29; 11 shared) |
| negative `solve_s` | 0 (Checkpoint 3 finding 1 detector silent, as on A1) |
| cost | **10.0 CPU-h** of the 29.3 CPU-h worst-case budget (34 %) |

Plan §6 made pooling conditional on the env being *recorded* and uniform
rather than assumed. It is both, so **calib_a ∪ calib_b is pooled** (290 rows,
290 distinct `instance_sha256`, 0 collisions). This does not close the
dev3/dev15 decision; it confirms the option stayed open.

### The achievement: the eligible population went 10 → 46

`python -m src.bench.calib_tier2_select --batches calib_a calib_b`

| pooled | after A1 | after B1 |
|---|---:|---:|
| profiled | 180 | 290 |
| certified | 92 | 177 |
| **eligible (60 s < `solve_s` ≤ 600 s)** | **10** | **46** |
| cells holding an eligible instance | 6 | 21 |
| (n, k) rows holding one | 5 of 9 | 8 of 9 |
| largest single-cell share | 3/10 (30 %) | 4/46 (9 %) |
| 60 s–cap (`include_solved_t3`) | 12 | 54 |
| ≥ 30 s (sensitivity, still not adopted) | 17 | 70 |

Spread across the window: 10 / 19 / 8 / 9 / 0 in the 60–100 / 100–200 /
200–300 / 300–450 / 450–600 s bands; median 159 s, Q1 111 s, Q3 240 s.

**Plan §7's first branch fires — stop refining, proceed to M2.** The stated
condition was "≥ 40 across ≥ 8 cells, spread rather than piled at one end";
the result is 46 across 21 cells, centred, no cell over 9 %. The bottleneck
identified at Checkpoint 3 — too few certified, RC2-nontrivial instances — is
resolved. **Refining α further is closed as a line of work** (see the
structural reason below).

### Scoring the plan's own method

- **17 exploratory cells: 8 hits, 6 partial, 3 misses; 14 of 17 produced at
  least one eligible instance.**
- **The c\* model is validated.** Predicted c\* landed inside the observed
  completed range in **16 of 17** cells. Per-row linear `dc*/dm` is a good
  instrument, used as plan §3 caveat (i) restricted it — within a row only.
- **The time model is not.** Predicted `solve_s` was within 3× in only 12 of
  17, median ratio 0.61×, errors in both directions up to 30×. Placing two α
  per row rather than one is what carried the round; that hedge should be
  kept in any future placement.
- **The 5 reinforcement cells all held** (4 now 10/10, 1 at 9/10; all 5 still
  pass the §5.3 cell rule at 10 seeds) and contributed **15 of the 46**
  eligible instances from a quarter of the tasks — the low-variance half
  performed as plan §4b predicted.
- **Checkpoint 3's smoke-run finding 2 was correct.** It flagged 3-SAT n = 150
  α = 4.6 as possibly the trivial edge from five workstation rows at cap 60,
  and chose to keep the cell because trivial outcomes locate edges. The
  cluster at cap 900 confirmed it, and that cell is now the evidence for the
  finding below.

### Structural finding: a row's yield is set by `d log10(solve_s)/dc*`

Fitted per (n, k) row over all pooled completed instances. The 60–600 s window
is one decade wide, so a row holds about `1/slope` consecutive integer c\*
values:

| k, n | slope (dec/c\*) | c\* values fitting the window | eligible |
|---|---:|---:|---:|
| 2, 100 / 150 / 250 / 400 | 0.13 / 0.19 / 0.25 / 0.24 | 7.9 / 5.2 / 4.0 / 4.2 | 4 / 4 / 1 / 9 |
| 3, 50 / 70 / 100 | 0.43 / 0.69 / 0.94 | 2.3 / 1.5 / 1.1 | 6 / 11 / 6 |
| 3, 150 | **1.39** | **0.7** | **0** |
| 3, 250 | 2.32 | 0.4 | 5 |

**Where that count falls below 1, no α can help — the c\* ladder steps over
the window.** 3-SAT n = 150 proves c\* = 2 in ~15 s and c\* = 3 in 772 s; four
α values across the two batches produced zero eligible instances there, and a
fifth would not change it. The exception, 3-SAT n = 250, yields through a
second mechanism: at fixed c\* = 1 its eight pooled instances span 33–388 s,
so variance scatters them into the window without the ladder moving. A row
needs one mechanism or the other; 3-SAT n = 150 has neither.

This is why calib_c-as-α-refinement is closed and why **n refinement is the
only remaining lever for that row** — plan §4c already named 3-SAT n ≈ 180–200
as the strongest calib_c candidate, and this is the quantitative reason. Not
proposed now: the population is sufficient without it.

It is a result about the *selection procedure* under this stack and cap, not
about Max-k-SAT, and it says nothing about memetic difficulty (H2 untested
until M2).

### Cell rule vs. instance eligibility — the separation earned its keep

18 batch-cells now pass the §5.3 cell rule (5 calib_a + 13 calib_b = 13
distinct (k, n, α) cells), up from 5. But **33 of the 46 eligible instances
sit in passing cells and 13 do not** — including all 4 from 2-SAT n = 100 and
3 from 3-SAT n = 100 α = 5.5, a cell that fails the certified fraction by one
seed while producing three eligible instances. Selecting by cell and then
filtering by instance would discard a quarter of what is available. Plan §2
kept the two rules apart a priori; the pooled data now shows the cost of
conflating them. **No threshold constant was edited** (`T1_MAX_S = 60`,
`T2A_MAX_S = 300`, `T2B_MAX_S = 600` untouched).

Also now quantified on the selected population: **2-SAT eligible instances
span c\* 18–35, 3-SAT span c\* 1–11 — disjoint ranges.** A1 predicted the two
families would occupy different c\* decades; they do not overlap at all. Any
pooled statement over the corpus mixes two regimes.

### Implemented / produced this checkpoint

| file | what |
|---|---|
| `docs/CALIB_B_B1_READOUT.md` | the read-out (new) |
| `docs/CALIB_B_SUMMARY.md` | one-page summary of the round, pointing at the plan, the read-out and this entry (new) |
| `cluster_staging_maxsat/results/profile_calib_b/` | 110 `task_N.jsonl` + 110 `task_N.env.json` from the cluster |
| `cluster_staging_maxsat/results/profile_calib_b_all.jsonl` | 110 aggregated rows |
| `cluster_staging_maxsat/results/profile_calib_b_env.jsonl` | 110 env rows |
| `results/calibration/tier2_eligible.csv` | regenerated over both batches — 46 rows |
| `results/calibration/tier2_cells.csv` | regenerated over both batches — 58 batch-cells |
| `docs/CALIB_B_PLAN.md` | status header added: §7 branch 1 fired |

Commands run (workstation only):

```bash
cd cluster_staging_maxsat && python3 scripts/aggregate_rc2_profile.py --batch calib_b && cd ..
python -m src.bench.calib_tier2_select --batches calib_a calib_b
```

### Decisions taken here

1. **α refinement is closed.** No calib_c round of α placement. The two thin
   rows are thin for the structural reason above, not for want of a grid line.
2. **calib_a and calib_b are pooled**, on the uniform-env condition plan §6
   set in advance.

### Open items — three of them now decidable on evidence

1. **The 30 s floor — recommend NOT adopting.** It would take the pool
   46 → 70. At A1 the case was 10 → 17 and the population was unusably small;
   at 46 the 60 s floor is no longer the binding constraint. Keep the
   repository's established floor and carry ≥ 30 s as a labelled sensitivity
   column. **Reverses nothing — it was never adopted. User decision.**
2. **The 600–900 s rescue (`include_solved_t3`) — recommend ADOPTING**, with
   the 8 rescued instances carried as a labelled subset so results can be
   checked with and without them. It takes 46 → 54, it is existing behaviour
   in `make_tier2_manifest.py` rather than a new threshold, it fills the empty
   450–600 s shoulder (thinned by the cap, not by the instances), and it is
   the only route to any 3-SAT n = 150 instance at all (its 772 s seed).
   Three of the 8 are within 4 % of the 600 s edge. **User decision.**
3. **What M2 runs on — recommend the ≥ 30 s certified set.** The certified
   pool is now 177, so M2 as currently specified (3 seeds × all certified) is
   531 tasks and ≤ 133 CPU-h, nearly double the estimate written when the
   certified set was 92.

   | M2 population | instances | tasks | worst-case CPU-h |
   |---|---:|---:|---:|
   | all certified (as specified) | 177 | 531 | 133 |
   | **certified with `solve_s` ≥ 30 s** | **70** | **210** | **52** |
   | eligible only (60–600 s) | 46 | 138 | 34 |

   91 of the 177 solve in under 10 s and 59 in under 1 s; A1 §5 established
   their RC2 ranking is cluster timing noise. The ≥ 30 s set covers every
   eligible instance, keeps a 24-instance margin below the window for §5.2's
   attenuation to be visible, and costs less than the original estimate.
   Note this is a *sizing* use of 30 s, independent of open item 1, which is
   about the Tier-2 floor. **User decision; it changes M2's manifest builder.**
4. **PySAT dev3 vs dev15** (Checkpoint 2) — unchanged. B1 kept both options
   open at no cost; the price of upgrading is now re-running 290 tasks
   rather than 180.
5. **Goals §5.4 vs. building Tier 2 from calibration batches** — unchanged
   and now materially larger. §5.4 says the reported corpus is regenerated at
   fresh seeds 1001–1020 and calibration rows never enter a reported ρ. If it
   stands, this round's product is a **map of where to generate** — §5 of the
   read-out is that map — not the corpus itself. Default remains §5.4 until
   this log says otherwise. **Decision for M4.**

### Next (awaiting approval)

1. **Settle open items 2 and 3** — they are what M2's manifest is built from.
2. **M2** (goals §6): `make_calib_memetic_manifest.py` over the chosen
   population, 3 seeds, `STOP_AT_ORACLE=1`, budget 900; submit; record job id
   and the not-run list. Then M3.
3. Not proposed: any further α refinement; any cap change; any n-refinement
   round.
