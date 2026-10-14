# HP-1 calibration plan: size-aware hyperparameters for the memetic solver

**Date:** 2026-10-11. **Decision §0: continuous flips per variable with floor 12,500 (no categories).**
**2026-10-12: §0b Stage L1 (c grid at n 16,000 and 64,000) planned, not prepared.** **2026-10-14: Stage L1 prepared, 108 tasks, not submitted (§0c.4).** **2026-10-14: §0c: the user's method stance (empirical c, not a framework's automatic setting), c as part of the orthogonality flow, and the flip-only polish mode for the grid.** **Status: plan only. Nothing has been run or prepared
for the cluster. Each stage needs approval.**

**Request (user, 2026-10-11)** [quote]: "do some calibration for
hyperparameter function on smaller instances too, it may be not continuous,
might be with categories of instance size, after knowing what instance sizes
might the solver meet".

Background: the to-do HP-1 (`NEXT_SESSION_CONTEXT.md` §8, N-2026-10-11-r),
the literature report
[`RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`](RESEARCH_NOTES_HYPERPARAMETER_TUNING.md),
and the 12.5k / 200k flip arms (`CALIB_2SAT_SC.md` §13b).

## 0. Decision 2026-10-11 (later the same day): continuous flips per variable, floor 12,500

**The user** [quote]: "I do would like not categories - continous number of
flips per var, but in lower bound stay with 12500".

**The rule:**

    ls_polish_flips(n) = max(12,500, c · n)        (flip_budget kept equal)

- one constant c, in flips per variable;
- n is the number of variables.

**Consequences for this plan:**
- **Rule C (categorical, §3.5) is dropped.** It is no longer a candidate.
  The size bands S / M / L stay only as a way to **pick and budget
  instances**, not as a rule.
- **What is calibrated is c.** §2's flip grid becomes a grid of c. The grid
  is still to be fixed, e.g. c ∈ {1, 2, 4, 8, 16}. For reference, at
  n = 64,000, c = 3.125 gives the 200k arm's value.
- **[inference] Where the rule changes anything:** only where c · n >
  12,500, i.e. n > n\* = 12,500 / c.

  | c | n\* | consequence |
  |---:|---:|---|
  | 1 | 12,500 | |
  | 2 | 6,250 | |
  | 4 | 3,125 | |
  | 8 | 1,563 | |
  | 16 | 781 | |
  | 31.25 | 400 | every S-band instance (n ≤ 400) keeps exactly 12,500 for c up to 31 |

  - So the **small-instance calibration becomes a check of the floor**:
    does anything above 12,500 help at n ≤ 400? If it does, the floor
    itself is questioned. That is reported, but the floor stays unless
    you change it.
  - **c is estimated where it acts:** the M and L bands.
- **Open for tomorrow** (with §7): an upper cap or none (the time limit
  of 3.5 s per call caps implicitly); the c grid; whether the 200k smoke
  and the 12.5k/200k batch suffice as the L-band evidence for a first c.
- **P4 module shape (when built):** `ls.ls_polish_flips: {per_var: c,
  min: 12500}`. The resolved value is recorded in the shard. A plain number
  keeps today's behaviour.

## 0a. Proposal 2026-10-12: c = 15 for the first large instances

**The user** [quote]: "for first big instances we might use c =15".

- **Values:** at n = 16,000 that is 240,000 flips per call; at n = 64,000 it
  is 960,000.
- **Literature** (N-2026-10-12-b,
  [`RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`](RESEARCH_NOTES_FLIP_LIMIT_SCALING.md)):
  - no published c exists, so c = 15 is a first point to calibrate around,
    not a derived value;
  - the best budget may grow faster than n, so c = 15 is more likely low
    than high at n = 64,000.
- **The time cap binds at n = 64,000 [inference]:** 960,000 flips at
  270k–500k flips/s is 1.9–3.6 s, against `ls.time_limit_s` = 3.5 s. A
  c = 15 run must record which limit ended each call, or raise the cap.
- *Correction 2026-10-12 (N-2026-10-12-d): on the cluster (about 190k
  flips/s at n 64,000), 960k flips take about 5 s, so the 3.5 s cap
  always binds. The time-capped arm is about c ≈ 10 there.*
- **Status:** a proposal ("might"). No config has been prepared. It waits
  for the 12.5k / 200k readout (`CALIB_2SAT_SC.md` §13b).

## 0b. Stage L1: a c grid for the memetic at n 16,000 and 64,000 (plan 2026-10-12; not prepared, not submitted)

**Request (user, 2026-10-12)** [quote]: "I want first make grid to
calibrate coefficient for the 16000, and 64000 memetic, write it in plan".

**Starting evidence** (`CALIB_2SAT_SC.md` §13c, N-2026-10-12-d):
- c = 0.78 / 12.5 at n 16,000 and c = 0.2 / 3.1 at n 64,000 (the 12.5k /
  200k arms).
- The larger c won 18/18 pairs; no run reached c\*.
- No literature value of c exists (N-2026-10-12-b), and the best value may
  grow with n.

### 0b.1 Instances and seeds

- The same 6 eligible calib_2sat_sc2 instances (sc01–sc03 at n 16,000,
  α 1.20; sc04–sc06 at n 64,000, α 1.10) with the RC2 optima as targets.
- Solver seeds 1–3, 900 s, stop at c\*, grace 60 s, as in §13b.
- No new instances, so no new RC2 work.

### 0b.2 The grid

**Revised 2026-10-12 (user)** [quote]: "I want start for both 16000, and
64000 from 200k". **Both sizes use one grid of flips per call, starting at
the 200k arm and doubling.** The first draft's c grid, which went down to
50k at n 16,000, is dropped: below 200k nothing is tested, since 200k
already beat 12.5k in 18/18 pairs.

| flips per call | c at n 16,000 | c at n 64,000 |
|---:|---:|---:|
| 200,000 (= the 200k arm) | 12.5 | 3.125 |
| 400,000 | 25 | 6.25 |
| 800,000 | 50 | 12.5 |
| 1,600,000 | 100 | 25 |
| 3,200,000 | 200 | 50 |

- **3.2M is the top at both sizes.** One call then takes about 14 s at
  n 16,000 (≈ 233k flips/s on the cluster) and about 17 s at n 64,000
  (≈ 190k flips/s). That is about 55–65 children in 900 s, barely more than
  one generation of 40. Beyond that the EA no longer acts.
- **c is still the quantity reported.** The two sizes overlap at c = 12.5,
  25 and 50 (200k–800k at n 16,000, 800k–3.2M at n 64,000), so a
  common c can be compared on 3 points.
- **Reference arm (not part of the grid):** the time-capped arm
  `memetic_deeppolish_p40_ls3p5_tcap_v2` (§13c). On the cluster it sits at
  about c ≈ 50 (n 16,000) and c ≈ 10 (n 64,000), depending on the node.

### 0b.3 What changes in the configs, and nothing else

- `ls.ls_polish_flips` = `ls.flip_budget` = the value in the table. One
  fixed-flip config per value: **5 configs** (200k, 400k, 800k, 1.6M, 3.2M),
  shared by both sizes. Each instance has one n, so a fixed value is
  exactly c · n for that instance. **No solver change is needed** for the grid
  arms.
- **`ls.time_limit_s` raised from 3.5 to 60 s in every grid arm**, so the
  flip limit, not the clock, ends each call.
  - Without this, every value from 800k up would be cut by the 3.5 s cap
    (and 400k at n 64,000 on slow nodes).
  - 60 s is about 3.5× the slowest expected call (3.2M at n 64,000).
  - `ea.deadline_mode: clip` still keeps every run inside its 900 s.
- Everything else as in the pre-registered arm. The manifest builder
  checks key by key that only these two keys (plus `impl: v2`) differ.
- **Recording:** shards already carry `total_flips` and `children`.
  Flips per child = total_flips / children shows whether the flip limit
  bound, which it should for every call.

### 0b.4 Measures and the pre-registered choice rule (per size)

**Per (c, instance):** successes out of 3, median TTT if any, and the
median best cost and gap to c\* at 900 s.

**The chosen c for a size** is decided in this order:
1. the most successes, summed over the 3 instances (out of 9);
2. then the lowest mean, over instances, of median best / c\*;
3. **ties:** values whose mean ratio differs by less than 0.05 count as
   tied, and the smaller c wins (cheaper children, more generations).

**Reporting:**
- the c curve (gap against c) per instance and per size;
- the tcap reference beside it;
- whether the best c differs between the two sizes. If it does, that is
  evidence for a c that grows with n (Parkes & Walser's
  superlinear scaling). The rule `max(12500, c·n)` then needs a decision.

**[inference] Caveats:**
- 3 instances × 3 seeds per size. Gap differences of about 1 are within
  seed noise at n 16,000 (§13c: seeds differ by up to 1 at 200k, and by up
  to 11 at 64,000 / 12.5k).
- c is chosen on these 6 instances only. Checking it on held-out
  instances is a separate stage.
- 900 s only. A c that wins at 900 s may lose at a longer budget.

### 0b.5 Size and cost

| arm set | tasks | worst case |
|---|---:|---:|
| grid, 5 flip values × 6 instances × 3 seeds | 90 | 90 × 960 s = **24 CPU-h** |
| of which already run (the 200k arm, both sizes, §13c) | 18 | — |
| tcap reference arm, 6 × 3 | 18 | 4.8 CPU-h |

- **Recommended: re-run all 90.** They are cheap, and re-running keeps one
  commit, one time cap and one date for the whole grid.
  - Reusing the 18 rows from §13c saves 4.8 CPU-h. Those rows ran with
    `time_limit_s` 3.5, which did not bind there (flips per child about
    199.9k), so reuse is defensible. It is the user's choice.
- With the tcap reference: 108 tasks, **≤ 28.8 CPU-h**, 4 waves at %30,
  about 64 min of compute plus queue time.
- Memory per task ≤ 150 MB (n 64,000, §13b smoke). 8 GB as before;
  `--time 00:20:00`.

### 0b.6 What has to be built (after approval)

1. The 7 grid configs, e.g. `memetic_deeppolish_p40_c{3p125,6p25,…}_n{16k,64k}_v2.yaml`, or one per flip value.
2. The manifest builder: a generalised `make_calib_2sat_sc_memetic_manifest.py`
   arm list (per-size arms), the key-by-key check allowing
   `ls.time_limit_s`, and a `--check` rebuild. Tests.
3. `m2_results.py`:
   - already checks `ls_polish_flips` against the sidecar;
   - add the same check for `ls.polish_cap`, so a tcap row cannot be
     mistaken for a flip-capped one.
4. **Upload list.** The grid itself needs no `src/` change. The tcap
   reference arm needs the new `src/evo/memetic.py` on the cluster.
   Before listing, take a fresh cluster hash snapshot (N-2026-10-12-a).
5. A readout script applying §0b.4.

### 0b.7 Open for the user

1. Re-run all 90, or reuse the 18 rows?
2. Include the tcap reference arm (18 tasks)?
3. Keep the 60 s per-call cap for the grid, or another value?
4. ~~Is c = 50 a high enough top?~~ Settled by the revision: the top is
   3.2M flips, i.e. c = 200 at n 16,000 and c = 50 at n 64,000.

## 0c. 2026-10-14: method stance, place in the orthogonality flow, flip-only polish

**The user's notes** [quote]: "for coefficient - check if there are
relevant hyperparameter frameworks, and write in to do I will check with
external llm. moreover, state that in frameworks they set automatically,
and i want to get result empirically concretly. I do want to use the
coeficient research flow as part of orthogonality research flow. implement
if there is no - solver version that will do constraint only number of
flips without constraint of seconds per local search."

### 0c.1 Frameworks exist; c is still calibrated empirically, by our own grid [decision]

- **Relevant frameworks exist** and are surveyed in
  [`RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`](RESEARCH_NOTES_HYPERPARAMETER_TUNING.md)
  §2–§4:
  - general configurators: irace, SMAC3, ParamILS, GGA, Optuna;
  - per-instance configuration: ISAC, Hydra;
  - configuring for scaling: Styles et al. 2012; Mascia, Birattari and
    Stützle 2013, who fit a scaling law of the parameters in instance size;
    Mu, Hoos and Stützle 2016.
  - Seen 2026-10-14 [web search, abstract level]: Ye, Luo and Cai (AAAI
    2025) tune MaxSAT local-search solvers with SMAC, using anytime
    performance as the cost.
- **In those frameworks the parameter is set automatically:** a
  configurator searches the space and returns a setting, or a fitted
  setting-versus-size model. Their output is the chosen value, not a
  measured curve.
- **The user wants the result empirical and concrete:** a pre-registered
  grid of c values, run on instances with a proven c\*, and reported as
  the full measured curve (successes, TTT, gap to c\* against c, per
  size), with the choice rule of §0b.4 applied to it. That is the method
  of §0b. **No configurator is put in the loop.** The frameworks are
  related work, and a source of protocol (held-out large instances,
  size-scaled budgets).
- **To-do for the user, with an external (web) LLM:** check whether a
  framework or paper already gives a size-dependent flip limit, and how
  frameworks treat a parameter that should scale with n. The prompt is
  Prompt 2 in
  [`WEB_LLM_QUERY_FLIP_COEFFICIENT.md`](WEB_LLM_QUERY_FLIP_COEFFICIENT.md).
  Not a session opener.

### 0c.2 c belongs to the orthogonality flow [decision + inference]

**The user wants the coefficient flow to be part of the orthogonality
research flow.** The orthogonality question is whether difficulty for RC2
(seconds to a proven c\*) and difficulty for the memetic solver (success
and TTT to the same c\*) are related (`CORPUS_V1_PROTOCOL_DRAFT.md` §5.2,
§8.3).

**[inference] Why c is a step in that flow, not a side study:**
- The memetic side of every ρ is measured with one configuration. With
  the fixed 12,500 flips, the configuration changes in effect with n:
  30–250 flips per variable at n ≤ 400, 0.2 at n 64,000. A large-n
  instance can then look memetic-hard because the polish is too short,
  not because the instance is hard. That would bias ρ by size.
- So the flip rule `max(12500, c·n)` with a calibrated c is what makes the
  memetic difficulty comparable across sizes. The Q2 labels from §13c
  (all 6 instances Q2 under 12.5k and 200k) are re-read under the chosen c.

**[inference] Rules this implies:**
1. **Report ρ under the calibrated rule as primary,** and under the fixed
   12,500 as a sensitivity arm, so the effect of the calibration on ρ is
   visible.
2. **Selection effect:** c is chosen on the 6 calib_2sat_sc2 instances.
   Those instances are not used as evidence in the ρ estimate that is
   reported under that c, or they are reported separately. The ρ sample
   comes from instances not used in calibration (the held-out stage).
3. **c is chosen by memetic performance only,** never by its effect on ρ.
4. The flip-only polish (§0c.3) makes "c" mean flips per variable on any
   host. With a time cap the effective c depends on the node
   (N-2026-10-12-d).

### 0c.3 Flip-only polish: `ls.polish_cap: flips_only` [verified: tests]

- **Not present before today:**
  - `flips` (the default) ends a call on the first of the flip limit and
    `ls.time_limit_s`;
  - `time` ends it on the time limit only.
- **Added (staging `src/evo/memetic.py`, `_ls_budget`):**
  `ls.polish_cap: flips_only` ends each polish call only on
  `ls.ls_polish_flips` (`ls.time_limit_s` becomes infinite).
  - With `ea.deadline_mode: clip`, the remaining run budget still ends a
    call, so a run stays inside its 900 s. **Grid configs must keep
    `deadline_mode: clip`.**
  - Absent or `flips`: every earlier config is unchanged (tested: same
    assignment and flips).
- **Tests:** `tests/test_polish_cap.py`, 5 new (12 in the file):
  - flips_only runs every call to its full flip limit past a time limit
    that would have ended it;
  - an endless flip limit is still ended by the run budget
    (`stop_reason: time_cap`);
  - both for `impl` v1 and v2.
  - Staging suite: 266 passed, 3 skipped, 1 failure that predates this
    change (the SATLIB PySAT test).
- **Consequence for §0b:** the grid arms can use `polish_cap: flips_only`
  instead of raising `ls.time_limit_s` to 60 s (§0b.3). §0b.7 Q3 becomes:
  flips_only (recommended: the flip limit is then the only per-call
  limit, by construction), or the 60 s cap.
- **Not on the cluster.** `memetic.py` must be uploaded (with the
  `polish_cap: time` change of 5fd74c1). Take a fresh cluster hash
  snapshot before writing the upload list.
- ~~**Not done yet:** the grid configs, and the `m2_results.py` check that a
  row's `polish_cap` matches its config.~~ Done the same day (§0c.4).

### 0c.4 Stage L1 prepared (2026-10-14; not submitted) [verified]

**§0b.7 answered (user, 2026-10-14):**
1. per-call limit: **flips_only**;
2. **re-run all 90** (the 200k arm too);
3. **include the tcap reference** arm.

**Built** (all in `cluster_staging_maxsat/`):
- **Configs:** `configs/tier2/memetic_deeppolish_p40_f{200k,400k,800k,1p6m,3p2m}_fonly_v2.yaml`.
  Each is the pre-registered arm plus `impl: v2`, the flip limit and
  `polish_cap: flips_only`, checked key by key. The reference is the
  existing `memetic_deeppolish_p40_ls3p5_tcap_v2.yaml`.
- **Manifest:** `scripts/manifest_calib_2sat_sc2_cgrid.{tsv,tasks.csv,sha256,not_run.csv}`.
  - 108 tasks: 6 instances × seeds 1–3 × 6 arms, with all 6 arms adjacent
    per (instance, seed).
  - Job ids `sc2cg_<arm>_<NN>_s<seed>`; 900 s, stop at c\*, grace 60.
  - Built by `make_calib_2sat_sc_memetic_manifest.py --plan cgrid`. The
    existing m2v2 manifest still rebuilds byte-identical (`--check`).
- **`m2_results.py`:** checks `ls.polish_cap` of every shard against the
  sidecar column `ls_polish_cap`. Absent on both sides means `flips`, so
  every earlier manifest is unchanged.
- **Tests:** 9 new in `tests/test_calib_2sat_sc_memetic_prep.py`. Staging
  suite: 275 passed, 3 skipped, 1 old failure.
- **Smoke on the workstation** (20–25 s budgets, seed 1):
  - n 16,000 at 200k: 62 children, 61 calls of exactly 200k flips, the
    last one clipped by the run budget;
  - n 64,000 at 3.2M: 3 children (2 full calls + 1 clipped).
- **Upload:** `scripts/rsync_files_calib_2sat_sc2_cgrid.txt`, 44 paths.
  - Against the 2026-10-12 cluster snapshot: changed `src/evo/memetic.py`
    and `scripts/m2_results.py`; new the 5 grid configs, the tcap config
    and the manifest files.
  - After the rsync,
    `sha256sum -c scripts/manifest_calib_2sat_sc2_cgrid.upload.sha256`
    (42 files: code, configs, manifest, instances) proves the cluster
    copy. So no fresh snapshot is needed first.
  - The login-node steps were tested with `python`/`python3` tripwires on
    PATH: hash check OK, DRY_RUN OK.
- **Cost:** ≤ 108 × 960 s = 28.8 CPU-h; 4 waves at %30, about 64 min of
  compute plus queue. 8 GB, 1 CPU, `--time 00:20:00` (the driver's
  defaults).
- **Not built yet:** the readout applying §0b.4. It comes after the
  results; `m2_results.py aggregate` gives the per-arm tables meanwhile.

**Commands.** On the workstation:

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_calib_2sat_sc2_cgrid.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_evo/
```

On the login node (shell only):

```bash
cd ~/cluster_staging_maxsat_evo
sha256sum -c --quiet scripts/manifest_calib_2sat_sc2_cgrid.upload.sha256 && echo UPLOAD_OK
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_calib_2sat_sc2_cgrid.tsv OUTDIR=results/calib_2sat_sc2_cgrid/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=<commit> MANIFEST=manifest_calib_2sat_sc2_cgrid.tsv OUTDIR=results/calib_2sat_sc2_cgrid/tasks bash submit_m2_memetic.sh
```

Back on the workstation, after the array:

```bash
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_evo/results/calib_2sat_sc2_cgrid/ results/calib_2sat_sc2_cgrid/
~/.venvs/maxsat/bin/python scripts/m2_results.py pending --manifest scripts/manifest_calib_2sat_sc2_cgrid.tsv --outdir results/calib_2sat_sc2_cgrid/tasks --summary
# resume only infra/invalid ids, if any (login node):
IDS=<ids> RESUME=1 MAXSAT_GIT_SHA=<commit> MANIFEST=manifest_calib_2sat_sc2_cgrid.tsv OUTDIR=results/calib_2sat_sc2_cgrid/tasks bash submit_m2_memetic.sh
```

`<commit>` is the commit that holds these files. Commit before submitting.

## 1. What instance sizes the solver can meet [verified]

**Method:**
- every `.cnf` / `.wcnf` under `cluster_staging_maxsat/data/` (1,947
  files) was parsed;
- n, m, the number of hard clauses, weightedness and clause lengths were
  recorded;
- each file was joined with every RC2 or EvalMaxSAT row that proves its
  optimum (`results/profile*_all.jsonl`, `results/profile*/`,
  `results/evalmaxsat_mse_s1_all.jsonl`).
- Script: `cluster_staging_maxsat/scripts/size_inventory.py`. Output:
  `cluster_staging_maxsat/results/size_inventory.csv`.

**By source:**

| set | files | n min / median / max | m min / median / max | hard clauses | weighted | k |
|---|---:|---|---|---|---|---|
| calib_a / calib_b / calib_c (random Max-2/3-SAT) | 180 / 110 / 40 | 50 / 150 / 400 | 200 / ~550 / 2,400 | none | no | 2–3 |
| uuf250 (`unsat250_1000c`), `unsat_uuf_diff` | 100 / 50 | 50–250 | 218–1,065 | none | no | 3 |
| SATLIB bench | 279 | 42 / 200 / 2,180 | 133 / 860 / 6,778 | none | no | 1–14 |
| MSE 2016 (`more_data`; `mse16` is a 104-file sample of it) | 856 | 27 / 140 / 11,264 | 48 / 1,350 / 39,424 | none | no | 1–495 |
| calib_2sat_sc / sc2 (large-n Max-2-SAT) | 45 / 15 | 1,997 / 8,000 / 64,000 | 2,200 / 9,200 / 70,400 | none | no | 2 |
| MSE 2023 uw-small | 75 | 55 / 8,754 / 81,317 | 495 / 83,856 / 231,903 | 69 of 75 | no | 1–201 |
| MSE 2024 small | 91 | 55 / 16,483 / 238,208 | 495 / 85,399 / 276,705 | 80 of 91 | yes (all) | 1–8,919 |

**Overall:** m spans **48 to 276,705**, five decades. The counts per decade
of m are 10–99: 3, 10²: 700, 10³: 1,071, 10⁴: 98, 10⁵: 75.

**By size band (m) and type**: files / proven c\* / proven c\* with
solve time > 1 s / solve time in the (30, 900] window. The solve time is
RC2's, or EvalMaxSAT's for the MSE 2023/2024 optima.

| band | all-soft unweighted | all-soft weighted | with hard clauses |
|---|---|---|---|
| **S**: m < 1,000 | 701 / **465** / 328 / 163 | 2 / 0 | — |
| **M**: 1,000 ≤ m < 10,000 | 1,051 / **142** / 108 / 87 | 7 / 2 / 2 / 2 | 13 / 0 |
| **L**: 10,000 ≤ m < 100,000 | 35 / **22** / 18 / 6 | 2 / 0 | 61 / 6 / 6 / 4 |
| **XL**: m ≥ 100,000 | — | — | 75 / 11 / 11 / 4 |

**What this says [inference]:**
1. **The all-soft memetic solver meets S, M and L:** m from about 50 to
   70,000. XL and almost all hard-clause instances belong to the separate
   hard-clause solver (`HARD_CLAUSE_SOLVER_PLAN.md`), whose operators
   differ. Its calibration is a later, separate stage (§6).
2. **Proven optima are plentiful in S, adequate in M, scarce in L.** Only
   22 all-soft L instances have a proven c\*: calib_2sat_sc/sc2 plus 2 from
   MSE 2016.
   - Time-to-optimum calibration (stop at c\*) is therefore easy for S and
     M, but thin for L.
   - L needs either more certified instances (calib_2sat_sc2-style
     generation is cheap, and RC2 certifies many fast) or an anytime
     objective (§3.4).
3. **The per-call flip limit relative to size varies 300-fold.** 12,500
   flips is 30–250 flips per variable at n ≤ 400, but only 0.2 per variable
   at n = 64,000. This is the first reason to expect a size dependence.
   "Flips per variable" is therefore a natural parameterisation for a
   continuous rule.

## 2. What is calibrated

| parameter | today (primary arm) | role | stage |
|---|---|---|---|
| `ls.ls_polish_flips` (= `ls.flip_budget`) | 12,500 | per-call local-search flip limit | **1 (primary)** |
| `ea.pop_size` | 40 | population size | 2, only if stage 1 leaves a gap |
| `ls.time_limit_s` | 3.5 | per-call time cap; rarely binds under v2 | fixed; recorded |
| everything else (tournament 3, pmutate 0.02, clip) | — | — | fixed |

- **Implementation:** v2 only. v1's per-flip cost is O(m), so v1 seconds are
  not comparable (N-2026-10-08-i).
- **Flip grid:** geometric, factor 4: **3,125 / 12,500 / 50,000 / 200,000
  / 800,000**.
  - S and M use the first four, L the last four. The bands overlap so
    that a jump between bands is visible.
  - Both 12,500 (the current default) and 200,000 (the new main config)
    are on the grid.

## 3. Design

### 3.1 Instances (training and held-out, per band)

- **Only instances with a proven optimum,** so that each run measures time
  to c\* (stop at c\*).
- **Instances that are not trivial for the default.** RC2 time is a poor
  proxy for memetic difficulty: ρ was only modest in M2. Stage 0 therefore
  screens candidates with the default arm at a short budget, and keeps only
  instances it does not solve in under 1 s on all 3 seeds.
- **Per band:** 12 training and 8 held-out instances, stratified by family
  and k (2-SAT vs 3-SAT vs mixed).
  - k is the second feature to check, as Hydra warns: size may not be the
    feature that matters.
  - L has only 22 candidates. If fewer than 20 survive stage 0, generate
    more calib_2sat_sc2-style instances (fresh seeds, RC2 900 s,
    ~0.2 CPU-h).
- **Fresh generator seeds for held-out instances** wherever the set is
  generated (calib_*). Rule N-2026-10-08-e: no nesting.

### 3.2 Budgets scaled with size

Following Mascia et al. (LION 7, 2013), the tuning cut-off scales with the
band:

| band | run budget | seeds | grace |
|---|---:|---:|---:|
| S | 120 s | 3 | 60 s |
| M | 300 s | 3 | 60 s |
| L | 900 s | 3 | 60 s |

A run that does not reach c\* scores 2 × budget (PAR-2). This is reported
next to success and ERT_s, never instead of them.

### 3.3 Search: offline racing in rounds (no controller on the cluster)

1. **Round 1 (one array per band):** every grid value × the first 6
   training instances × 3 seeds.
2. **Workstation:** a paired Friedman test across (instance, seed) blocks on
   PAR-2. Values worse than the round's best at p < 0.05 by a post-hoc
   paired Wilcoxon (Holm) are dropped. *Pre-registered here.*
3. **Round 2:** the survivors on the other 6 training instances. The band's
   value is the lowest mean PAR-2 rank over all 12; ties go to the smaller
   flip value.
4. **If the space grows later** (pop, noise, pmutate), switch to irace or
   SMAC3 in batch mode (report §7).

### 3.4 Anytime objective (secondary; for instances without a proven c\*)

- **Measure:** best cost after the budget, as a gap to the best-known.
- **Purpose:** it allows L-band checks on MSE 2016 instances without c\*.
- **Not used to choose values** unless the TTT data in a band are too few.

### 3.5 Categories versus a continuous rule (the user's question)

After round 2, each band has its chosen value v_S, v_M, v_L. The held-out
validation (§3.6) compares four rules:

| rule | definition |
|---|---|
| A. fixed default | 12,500 everywhere |
| B. fixed 200k | 200,000 everywhere |
| C. categorical | ~~v_S, v_M, v_L by band of m~~ **dropped 2026-10-11 (§0): the user wants a continuous rule** |
| D. continuous | flips = clip(c · n, 3,125, 800,000), fitted on the 36 training instances' best values (one constant c) |

- **The choice goes to the rule with the best held-out PAR-2,** with a
  paired test against A.
- If C and D do not differ, D is preferred: it has no boundary effects and
  extrapolates.
- If the chosen value **jumps** between neighbouring bands and D fits
  poorly, the dependence is not continuous, as the user suspected. C is
  then kept, and its boundaries may be refined by one more band split.

### 3.6 Held-out validation

- **What runs:** rules A–D on the 8 held-out instances per band, 3 seeds,
  with the band budgets.
- **Reports:**
  - per band: success, median TTT, ERT_s, PAR-2, Q2 count;
  - the paired comparisons against A.
- **Pre-registered:** this decides HP-1's rule. Nothing from the training
  rounds is reported as a held-out result.

## 4. Compute budget (worst case; all runs reach their budget + grace)

| stage | runs | CPU-h |
|---|---|---:|
| 0: screen candidates, default arm, 60 s, 3 seeds (≤ 60 per band) | ≤ 540 | ≤ 18 |
| 1: round 1, 6 instances × 3 seeds: S 4 values × 180 s; M 4 × 360 s; L 4 × 960 s | 72 + 72 + 72 | 3.6 + 7.2 + 19.2 = **30** |
| 1: round 2, survivors (worst case: all) on 6 more | same | ≤ 30 |
| validation: 4 rules × 8 instances × 3 seeds per band | 96 per band | 4.8 + 9.6 + 25.6 = **40** |
| **total, worst case** | | **≤ 118** |

The expected total is about half, because target hits stop runs early.
These are separate arrays of ≤ 100 tasks at %30.

**The calib_2sat_sc2 batch, prepared and not yet submitted** (§13b, 12.5k
vs 200k, 36 tasks), is effectively an L-band pilot of round 1 for two grid
values. Its readout comes first, and may shrink the L grid.

## 5. What is built, and when

| step | contents | gate |
|---|---|---|
| P0 | this plan | **approval** |
| P1 | stage-0 screen manifests (per band); configs for the flip grid (one YAML per value, each checked equal to the v2 arm except the flip keys); the racing analysis script (Friedman + Holm) with tests | approval of P0 |
| P2 | rounds 1–2 per band (cluster) and their readout | after P1 |
| P3 | held-out validation of rules A–D (cluster) and its readout | after P2 |
| P4 | **the HP-1 module:** `ls.ls_polish_flips` may be a rule (`{per_var: c, min, max}` or a band table) resolved from the instance before the run; the resolved value is recorded in the shard; `m2_results.py` checks the resolved value; fixed-value configs are unchanged | after P3 decides the rule |

## 6. Out of scope here, noted

- **Hard-clause solver** (MSE 2023/2024, bands L–XL):
  - its polish and repair operators differ;
  - calibrate it separately once H4 / H5 exist;
  - the HP-1 module is designed to serve both.
- **Dynamic control** (keep polishing while improving): an alternative
  to a fixed flip rule (report §5). A separate idea, not requested.
- **v1 configs** are not recalibrated.

## 7. Open questions for the user

1. **Scope:** the all-soft memetic solver first (bands S, M, L), with the
   hard-clause solver later? (Recommended.)
2. **Parameters:** the flip limit only in stage 1, with pop size only if
   needed? (Recommended.)
3. **Objective:** time to the proven optimum (PAR-2, success, ERT_s), with
   the anytime gap only as a fallback? (Recommended.)
4. **Band boundaries:** m = 1,000 and 10,000 (decades), or by n?
   - m sets the per-flip and crossover costs; n sets how many flips a
     polish needs.
   - Within each band the two are close, so m-decades are used, with n
     recorded.
5. **Budget:** ≤ 118 CPU-h worst case, in about 6–8 arrays.
