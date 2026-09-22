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
