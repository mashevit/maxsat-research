# `calib_2sat_sc` — large-n, slightly supercritical random Max-2-SAT

**Written:** 2026-10-08. **Status:** generated and validated, with cluster
scripts ready. **Not submitted.** No RC2 row of this batch exists yet.

The rules in §6 and the readout script are written and committed before any
data. Indexed from [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) (N-2026-10-08-d…f)
and [`READING_LIST.md`](READING_LIST.md).

Labels: [verified] means read off code or rows; [inference] follows by a stated
argument; [quote] is user-supplied or external text; [decision] is a design
choice with its reason.

---

## 1. Aim

The user's scientific motivation, as given (2026-10-08) [quote]:

> - The proven satisfiability threshold for standard uniform random 2-SAT is alpha = m/n = 1.
> - The critical window has width Theta(n^(-1/3)). Staying inside that window does not make the expected optimum grow without bound as n increases.
> - My aim is to keep alpha slightly above 1 and increase n substantially, looking for instances with a proven optimum c* > 2 and meaningful computational difficulty.
> - Near-threshold theory suggests n*(alpha-1)^3 as a useful scaling quantity, with logarithmic qualifications in known bounds. Do NOT treat it as a numerical prediction of c* or runtime.
> - Describe this batch as "large-n, slightly supercritical random Max-2-SAT," rather than claiming that all cells lie inside the critical window.

The user also said: "Do not dismiss this region as necessarily trivial based on
results for n <= 400." My chat answer of the same day did exactly that. It said
cells near α ≈ 1 would be "trivial for RC2 … unless n is in the thousands". That
was an extrapolation from n ≤ 400, not a measurement. This batch is the
measurement.

This direction differs from `GRID_POINTS_WINDOW_30_900.md` §4.4 / G-d, which
pointed to n > 400 at α ≈ 1.8–2.0. Both remain open. This batch does not
replace `calib_c`, which is still on hold.

## 2. Model and generator

**The existing generator was audited first** [verified]. The audit is in
[`RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md`](RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md)
§2. `weighted_ksat` (calib_a/b/c) has these properties:
- **Variables:** 2 distinct variables per clause, uniform over {1..n}
  (`rng.sample`).
- **Signs:** one fair coin per variable.
- **Within a clause:** no repeated variable and no tautology, by construction.
- **Across clauses:** clauses are drawn **with replacement**. Duplicates occur:
  133 of 170 Max-2-SAT files in calib_a/b/c contain at least one.

**Which model is "standard"** [quote, verified from the papers' TeX sources]:

- **Bollobás, Borgs, Chayes, Kim & Wilson,** *The scaling window of the 2-SAT
  transition*, Random Structures & Algorithms 18(3):201–256, 2001,
  doi:10.1002/rsa.1006 (arXiv:math/9909031). §1 defines:
  > "the probability space of formulae $F_{n,m}$ chosen uniformly at random from all 2-SAT formulae with exactly $m$ different clauses. (Here $x \vee y$ is considered to be the same as $y \vee x$, but different from e.g. $x \vee \overline y$.)"

  It takes N = 2n(n−1) = 4·C(n, 2) possible clauses, so every clause has two
  distinct variables. Appendix A relates F_{n,m} to F_{n,p} (each clause
  included independently with probability p). The paper says the two are
  "practically interchangeable" for monotone properties.
- **Coppersmith, Gamarnik, Hajiaghayi & Sorkin,** *Random MAX SAT, random MAX
  CUT, and their phase transitions*, arXiv:math/0306047 (2003), §1:
  > "each clause is proper (consisting of $k$ distinct variables, each of which may be complemented or not), and clauses may be repeated. … this is equivalent to choosing $m$ clauses uniformly at random, with replacement"

**Choice [decision].** This batch uses `ksat_distinct` 1.0.0, which is BBCKW's
F_{n,m} exactly:
- m distinct clauses, uniform over the 4·C(n, 2) proper 2-clauses;
- fair signs;
- all clauses soft, weight 1;
- random 2-CNF, not a MaxCut encoding.

`weighted_ksat` is not used here.

**How much the choice matters at these densities [inference].** In the
with-replacement model, the expected number of colliding pairs is
C(m, 2)/N ≈ α²/4, which is 0.30–0.36 per instance and does not depend on n.
- So about 70 % of with-replacement instances would have no duplicate at all.
- The two models differ by roughly one clause in a third of instances.
- CGHS's bounds are stated for the with-replacement model. Applying them to
  this batch relies on that small difference, not on a theorem.

## 3. Seeds and independence

**Every instance has its own seed** [decision]: 5 per cell, 201–245, so no
seed is reused in this batch. Each cell's seed block is in
`instancegen/grids/calib_2sat_sc.yaml`.

**Why per-cell seeds** [verified]. Both generators consume the RNG one clause
at a time, so for a fixed (n, seed) the instance at a smaller α is a **prefix**
of the instance at a larger α.
- A first generation of this batch used one seed list (201–205) for all
  cells. It was nested this way and was discarded before any use.
- **calib_a/b are nested in the same way.** For example:
  - `calib_a/…v100_k2_sr2.00…_s1` is the first 200 clauses of `…sr3.00…_s1`;
  - `calib_a/…v400_k2_sr2.00…_s3` is a prefix of `calib_b/…v400_k2_sr2.15…_s3`;
  - `calib_a/…v250_k3_sr4.26…_s2` is a prefix of `calib_b/…v250_k3_sr4.35…_s2`.

**Consequence for earlier results [inference].**
- Within a cell, instances are independent.
- Across cells that share n, they are paired. One seed's c\* is non-decreasing
  in α along that pair.
- A pooled analysis that treats calib_a/b instances from different α cells as
  independent overstates the effective sample. This affects §5.2's pooled ρ
  bootstrap in `CORPUS_CALIBRATION_GOALS.md`, which resamples within cell and
  therefore ignores the pairing.
- This is recorded, not repaired. See N-2026-10-08-e.

**Fresh seeds and the final corpus [decision].**
- Seeds 201–245 are disjoint from calib_a/b (1–10), calib_c (101–120) and the
  final-corpus range (≥ 1001).
- Any corpus cell chosen from this pilot is regenerated with seeds not used
  here. No pilot instance enters a reported result.

## 4. Grid

| n | α | m | ε = α − 1 | n·ε³ | λ = ε·n^{1/3} | window width n^{−1/3} |
|---:|---:|---:|---:|---:|---:|---:|
| 2000 | 1.10 | 2200 | 0.10 | 2.0 | 1.26 | 0.079 |
| 2000 | 1.15 | 2300 | 0.15 | 6.75 | 1.89 | |
| 2000 | 1.20 | 2400 | 0.20 | 16.0 | 2.52 | |
| 8000 | 1.10 | 8800 | 0.10 | 8.0 | 2.00 | 0.050 |
| 8000 | 1.15 | 9200 | 0.15 | 27.0 | 3.00 | |
| 8000 | 1.20 | 9600 | 0.20 | 64.0 | 4.00 | |
| 32000 | 1.10 | 35200 | 0.10 | 32.0 | 3.17 | 0.031 |
| 32000 | 1.15 | 36800 | 0.15 | 108.0 | 4.76 | |
| 32000 | 1.20 | 38400 | 0.20 | 256.0 | 6.35 | |

**Notes on the grid.**
- **m.** m = round(α·n), the same rounding as `GenParams.n_soft`. Every m is
  pinned by a test.
- **Position relative to the scaling window.** n·ε³ = λ³. Every cell has
  λ > 1, so every cell lies *above* the scaling window. This is a slightly
  supercritical batch, and no cell is claimed to be inside the window. The
  n = 2000, α = 1.10 cell (λ ≈ 1.3) is the closest to it.
- **What the theory says** [quote of CGHS theorems; the reading is an
  inference]:
  - For fixed ε > 0, max-sat ≳ (1 + ε − ε³/3)·n asymptotically. That gives an
    asymptotic *upper* bound c\* ≲ (ε³/3)·n.
  - For ε < ε₀, there is a lower bound of order ε³/ln(1/ε)·n, with an
    unspecified absolute constant α₀.
  - In the window parametrisation c = 1 + λn^{−1/3}: for λ > 1, c\* = O(λ³)
    with an exponential tail, and c\* = Θ(1) for |λ| ≤ 1.
- **What n·ε³ is used for here.** It is reported as a covariate. It is **not**
  a prediction of c\* (constants and finite-n corrections are unknown) or of
  RC2 time, which the theory says nothing about.
- **Not a reason to skip any cell [inference].** If the asymptotic upper bound
  were close at these n, the n = 2000 cells would sit at c\* ≲ 1–5. The
  α = 1.10, n = 2000 cell may then be "too easy" (§6). The grid already holds
  larger n at the same α.

## 5. Measurement

The measurement is unchanged from calib_a/b and satlib. Sources are
`scripts/rc2_profile_array.sbatch`, `src/cli/profile_hardness.py` and
`src/cli/solve_rc2_anytime.py` in the staging tree.

**Solver.**
- `RC2(wcnf, solver="g3")`, default options (adapt, exhaust and minz off).
- One run per instance; RC2 is deterministic.

**PySAT version [verified].**
- Every cluster RC2 batch so far ran PySAT **1.9.dev3** / Python 3.11.15
  (env rows of calib_a 182, calib_b 110, satlib 263). The "1.9.dev15" in
  `CORPUS_CALIBRATION_GOALS.md` §4.1 is the workstation's version
  (`CALIB_B_PLAN.md` §6).
- This batch passes `EXPECT_PYSAT=1.9.dev3`. Each task then refuses to run, and
  writes no row, under any other version.
- The guard is opt-in and new in `rc2_profile_array.sbatch` /
  `submit_rc2_profile.sh`. Earlier wrappers produce the same sbatch command as
  before (checked with `DRY_RUN=1`).

**Time limit: 900 s of wall-clock time, from the start.** No 60 s pre-screen.
- **What `solve_s` measures.** `time.time()` in the child process, from just
  before the file is parsed to RC2's return. It includes parsing and RC2
  construction. It is wall time, not CPU time.
- **How the cap is enforced.** `signal.setitimer(ITIMER_REAL, 900)` is armed
  after parsing. When it fires, RC2 stops with `status=timeout` and the
  running lower bound.
- **The handler can be late.** The handler runs only between Python bytecodes,
  so a long C-level SAT call delays it. On a non-batch n = 32000 instance with
  a 20 s cap, the timeout was taken at 48.8 s [verified, §10].
- **Watchdog.** `subprocess.run(timeout = cap + grace)` SIGKILLs the child at
  900 + 60 s. The lower bound is then recovered from the progress file, which
  is written on every core.
- **Slurm limit.** `--time 00:20:00` (1200 s) covers 960 s plus startup. A task
  killed by Slurm leaves no row, and `RESUME=1` re-runs it.

**Per-instance record.**
- Row fields: `status`, `completed`, `solve_s`, `final_cost` and
  `cost_lower_bound`.
- Provenance is in `task_N.env.json`: PySAT, Python, host, Slurm job ids, cap,
  grace and resume state.
- The instance `sha256` is checked before submission.

**What is never reported.**
- **No incumbent as c\*.** A timeout row has no feasible assignment, and the
  readout fills `c_star` only when `completed` and
  `final_cost == cost_lower_bound`.
- **No upper bound on timeout.** None is claimed, because none is recorded.

**c\* and runtime are separate measurements.**
- c\* is the minimum number of unsatisfied clauses (all weights 1).
- `solve_s` is RC2's wall-clock time in seconds.
- A larger c\* does not by itself mean a longer proof, and RC2 difficulty does
  not establish memetic difficulty. §6 tests each separately.

## 6. Pre-registered rules (written before any row exists)

These rules are implemented in `cluster_staging_maxsat/scripts/calib_2sat_sc_readout.py`
and pinned by `tests/test_calib_2sat_sc_readout.py`. The (30, 900] window
convention is imported from `candidate_cells.rc2_class`, so it is the same
code that classified calib_a/b/c.

**Instance class.**

| class | definition |
|---|---|
| eligible | completed; 30 < `solve_s` ≤ 900; c\* ≥ 3 |
| low_cstar | completed within 900 s; c\* ≤ 2 (any time) |
| fast | completed; `solve_s` ≤ 30; c\* ≥ 3 |
| censored | not completed within 900 s (timeout, SIGKILL, or completed after 900 s, in which case c\* is still reported); lower bound reported |
| failed | error, missing row, cost ≠ bound, non-positive time, or a cap below 900 s. Re-run with `RESUME=1`; never counted. |

**Cell outcome** (5 instances; any `failed` makes the cell `incomplete`):

| outcome | rule | follow-up (a proposal; nothing is generated automatically) |
|---|---|---|
| promising | ≥ 3 eligible | Memetic assessment of its eligible instances: primary arm `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml`, solver seeds 1–3, 900 s, effort in seconds (median TTT, ERT_s; Q2 = success < 3/3 or median TTT ≥ 45 s). A corpus cell only after that, and with fresh seeds. |
| too_easy | ≥ 3 in low_cstar + fast | The same α at larger n first. |
| too_hard | ≥ 3 censored | Report the lower bounds. Propose intermediate points: a lower α at the same n, or an n between the nearest easier n and this one at the same α. |
| mixed | otherwise | State the split. Choose reinforcement seeds or intermediate points at the readout, with the reason written down. |

The three counts are over disjoint classes, so with 5 instances at most one
can reach 3.

**Further rules.**
- **Reporting.** Every instance and every cell is reported, including
  `low_cstar`, `fast` and `censored` ones, with c\* or lower bound and seconds.
- **No upper limit on c\*** beyond c\* ≥ 3. Cells whose eligible c\* sit
  comfortably above 2 are preferred when the proposal for the next batch is
  written.
- **Not settled here: the final-corpus cell rule.** This pilot rule decides
  where to look next, not what enters the corpus. The corpus rule (§5.3 of
  `CORPUS_CALIBRATION_GOALS.md`, or its successor in
  `CORPUS_V1_PROTOCOL_DRAFT.md`) is applied to fresh-seed instances after the
  memetic assessment.
- **No guarantee.** Nothing here claims that this grid will produce eligible
  instances.

## 7. Validation [verified]

**Generation.**
- `python -m instancegen.cli generate-grid --grid instancegen/grids/calib_2sat_sc.yaml --staging-root cluster_staging_maxsat`
  generated 45 files. Before writing them, it validated each one with
  `instancegen/validate.py` on the bytes:
  - clause length 2, variables in range and distinct;
  - no tautology and no duplicate in either literal order;
  - weight 1, count m, top = m + 1.
- **Rejected duplicate candidates:** 21 in total (0 ×25, 1 ×19, 2 ×1 per
  instance). Theory gives 14.9 (Poisson p ≈ 0.07).
- **Separate check of the sampler:** 3000 draws at n = 2000, m = 2200 gave a
  mean of 0.317 ± 0.010 rejections, against 0.303 expected.

**Reproducibility.**
- `generate-grid --check` regenerates all 45 in memory and matches files,
  manifest and Slurm manifest byte for byte (CHECK OK).
- `sha256sum -c scripts/manifest_calib_2sat_sc_rc2.sha256` gives SHA_OK.

**Tests.**
- `instancegen`: 125 passed. That includes the batch-as-data tests in
  `instancegen/tests/test_grid_distinct.py`:
  - the 9 cells and each m;
  - 45 distinct seeds;
  - no instance is a prefix of another;
  - seeds disjoint from calib_a/b/c;
  - no filename or cell-id collisions.
- Staging: 174 passed, 3 skipped.

**Earlier batches are untouched.**
- `generate-grid --check` for calib_a/b/c gives the same result as before.
- The `weighted_ksat` output is pinned by SHA-256.

**Sizes.** 12 MB in total: n = 2000 0.5 MB, n = 8000 2.0 MB, n = 32000 9.0 MB.
Instance files are gitignored, and the manifest is tracked.

## 8. Compute budget (maximum)

| quantity | value |
|---|---|
| tasks | 45, 1 CPU each, `--mem 8G` (measured peak RSS of RC2 on an n = 32000 instance: 101 MB) |
| CPU-hours, worst case | 45 × (900 + 60) s = **12.0 CPU-h**. Slurm allocation at most 45 × 20 min = 15 CPU-h. |
| elapsed compute, worst case | %30: 2 waves × ≤ 20 min ≈ **40 min** |
| queue delay | not estimated; separate from the above |

## 9. Commands

Nothing has been submitted. The user runs these.

**Login-node rule** [quote, cluster policy as the user reported it on
2026-10-08]:
> Do not execute any python scripts or any other heavy tasks on this node. This kind of tasks will be terminated.

What this means for the commands:
- Every login-node command below is shell only: `sha256sum`, `grep`,
  `sbatch`.
- All Python runs inside Slurm jobs on compute nodes, or on the workstation
  after the rsync back.
- `submit_rc2_profile.sh` and `submit_m2_memetic.sh` no longer call Python
  for `RESUME=1` (changed 2026-10-08).

```
# workstation -> cluster
cd /home/mashe/maxsat-lab_new/maxsat-lab
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# login node (shell only)
cd ~/maxsat-lab/scripts
bash preflight_calib_2sat_sc.sh                  # §9a; must end with "PREFLIGHT OK (login checks)"
SUBMIT_SMOKE=1 bash preflight_calib_2sat_sc.sh   # optional node smoke (2 small jobs)
CHECK_SMOKE=1 bash preflight_calib_2sat_sc.sh    # when they have finished: must show PREFLIGHT_NODE OK
bash submit_rc2_calib_2sat_sc.sh                 # the real 45-task array; record the job id

# only if rows are missing after the array has finished:
RESUME=1 bash submit_rc2_calib_2sat_sc.sh        # resubmits 1-45; tasks with a valid row exit at once on their node
#   or, with ids computed on the workstation (see below):
IDS=7,31 RESUME=1 bash submit_rc2_calib_2sat_sc.sh

# back on the workstation (all Python here)
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_2sat_sc/ cluster_staging_maxsat/results/profile_calib_2sat_sc/
cd cluster_staging_maxsat
python3 scripts/rc2_row_state.py --manifest scripts/manifest_calib_2sat_sc_rc2.txt \
    --outdir results/profile_calib_2sat_sc --cap 900 --pending    # ids for IDS=, if any
python3 scripts/aggregate_rc2_profile.py --batch calib_2sat_sc
python3 scripts/calib_2sat_sc_readout.py
```

The submit command that `submit_rc2_calib_2sat_sc.sh` issues (verified with
`DRY_RUN=1` on the workstation):

```
sbatch --array=1-45%30 --export=ALL,MANIFEST=scripts/manifest_calib_2sat_sc_rc2.txt,OUTDIR=results/profile_calib_2sat_sc,CAP=900,GRACE=60,EXPECT_PYSAT=1.9.dev3 --job-name=rc2-2sat-sc rc2_profile_array.sbatch
```

## 9a. What must be on the cluster, and the preflight

**Added 2026-10-08, later; preflight revised the same day for the login-node
rule.**

§9 rsyncs the whole staging tree, which carries everything. This is the
minimal set the RC2 array actually touches. It was traced from the imports of
`profile_hardness` → `solve_rc2_anytime` → `run_opt_rc2`, which use only the
stdlib and PySAT.

| needed for | files (relative to `~/maxsat-lab/`) |
|---|---|
| RC2 per task | `src/__init__.py`, `src/cli/__init__.py`, `src/cli/profile_hardness.py`, `src/cli/solve_rc2_anytime.py`, `src/cli/run_opt_rc2.py` |
| array and submission | `scripts/rc2_profile_array.sbatch`, `scripts/submit_rc2_profile.sh`, `scripts/submit_rc2_calib_2sat_sc.sh`, `scripts/rc2_row_state.py` (called by the array task on its node) |
| batch | `scripts/manifest_calib_2sat_sc_rc2.{txt,sha256}`, `data/generated/calib_2sat_sc/*.wcnf` (45), `data/generated/calib_2sat_sc/manifest.jsonl` |
| preflight | `scripts/preflight_calib_2sat_sc.sh` (login, shell only), `scripts/preflight_calib_2sat_sc_verify.sbatch` (compute node), `scripts/manifest_calib_2sat_sc_smoke_rc2.{txt,sha256}`, `data/generated/calib_2sat_sc_smoke/*.wcnf` (2) |
| after the run | On the workstation: `scripts/aggregate_rc2_profile.py`, `scripts/calib_2sat_sc_readout.py`, `scripts/candidate_cells.py`. |
| environment | Conda env `maxsat` with **PySAT 1.9.dev3** (`module load anaconda; source activate maxsat`, done inside each job). `instancegen/` is **not** needed on the cluster. |

**Preflight.** It checks what the sha256 check cannot, without running Python
on the login node.

| part | where | what it does |
|---|---|---|
| 1 files | login, shell | Every file above exists. The manifest has 45 lines, and every line resolves to a staged instance. |
| 2 checksums | login, shell | `sha256sum -c` for the batch and smoke manifests. |
| 3 sbatch | login, shell | `sbatch` is on PATH. |
| dry run | login, shell | `DRY_RUN=1` of the real submission. |
| a smoke array (`SUBMIT_SMOKE=1`) | 2 compute-node tasks | `rc2_profile_array.sbatch` submitted through `submit_rc2_profile.sh` exactly as the batch is: `module load` + env on a node, partition, `logs/`, `--export`, and the `EXPECT_PYSAT=1.9.dev3` guard. It runs on two **smoke** instances (seeds 9001/9002, not batch instances; grid `instancegen/grids/calib_2sat_sc_smoke.yaml`) with cap 60, grace 30 and `--time 00:05:00`. Task 1 (n = 2000) should complete with a proven c\*. Task 2 (n = 32000) should end censored with a recovered lower bound. |
| b verify job | compute node, after (a) via `--dependency=afterany` | Checks the PySAT version and the RC2 / `src.cli` imports, reads both rows and env records, and writes `results/smoke_calib_2sat_sc_node/PREFLIGHT_REPORT.txt`. |
| `CHECK_SMOKE=1` | login, shell | `cat`s the report. Exits 0 only if the report ends with `PREFLIGHT_NODE OK`. |

**Cost of the node smoke.** At most 2 × 90 s plus a few seconds for the
verify job. Smoke rows never enter `results/profile_calib_2sat_sc/` or any
readout.

**PySAT is pinned in the wrapper.** `submit_rc2_calib_2sat_sc.sh` hard-codes
`EXPECT_PYSAT=1.9.dev3`, so no environment variable can change the batch's
version.

**Tested on the workstation (2026-10-08).**
- **No Python on the login side.** The login part ran with `python` and
  `python3` replaced by tripwires that log any call: **0 calls**, PREFLIGHT
  OK. This covered the checks, the dry run, the `SUBMIT_SMOKE` path and
  `CHECK_SMOKE`.
- **The `SUBMIT_SMOKE` path.** It was run against a fake `sbatch` that
  records its arguments. Both commands came out as intended: the smoke array,
  then the verify job with `--dependency=afterany:<id>`.
- **The verify job.** It was run with `LOCAL_SMOKE=1` on real smoke rows
  (cap 60 / grace 30). PREFLIGHT_NODE OK. When the rows carried the wrong
  PySAT version, it gave PREFLIGHT_NODE FAILED and `CHECK_SMOKE` exited 1.
- **Not testable here:** the real node path (`module load`, partition,
  `--parsable` output). That is what the node smoke itself tests.

## 10. Pipeline smoke on the workstation (not data)

These runs used non-batch seeds 9001 and 9002, generated into the scratchpad,
under the workstation's PySAT 1.9.dev2. They tested the scripts, not the
cells, and do not enter any readout. They are reported because every outcome
is reported.

- **Guard.** `EXPECT_PYSAT=1.9.dev3` under dev2 gave exit 2 and no row.
- **n = 2000, α 1.10, seed 9001, cap 900:** optimal, c\* = 2, `solve_s` 0.008 s.
- **n = 32000, α 1.20, seed 9002, cap 20 (timeout path):**
  - Through the array script: SIGKILL at cap + 10 s grace, lower bound 18
    recovered from the progress file.
  - Run directly: the timeout was taken at 48.8 s with lower bound 18, and
    peak RSS was 101 MB.
- **Resume.** Re-running a completed task gave `skip:completed`.

## 10a. Workstation RC2 check on the batch's cells (exploratory, not data)

**Run 2026-10-08, after the batch was frozen, at the user's request.** It used
the batch's 9 cells but **non-batch seeds** (9101–9126), so no batch instance
was run. It does not enter the readout, and it does not change the grid or the
§6 rules.

**Conditions.**
- Workstation (WSL2), PySAT **1.9.dev2**, not the cluster's 1.9.dev3.
- 8 runs in parallel on 12 logical CPUs, so the times are noisier than on the
  cluster.
- Same code path as the cluster: `profile_hardness`, RC2 g3, cap 900 s, grace
  60 s.

**Data.** Rows and provenance are in
`cluster_staging_maxsat/results/workstation_check_calib_2sat_sc/`
(`rows.csv`, `README.json`). The instances are reproducible with
`generate-distinct --seed 9101…`.

**Results [verified].**

| n | α | n·ε³ | seed → proven c\* (RC2 s) |
|---:|---:|---:|---|
| 2000 | 1.10 | 2 | 9101 → 0 (0.02) |
| 2000 | 1.15 | 6.75 | 9102 → 3 (0.02) |
| 2000 | 1.20 | 16 | 9103 → 1 (0.02) |
| 8000 | 1.10 | 8 | 9111 → 0 (0.05); 9112 → 1 (0.06) |
| 8000 | 1.15 | 27 | 9113 → 4 (0.11); 9114 → 5 (0.07) |
| 8000 | 1.20 | 64 | 9115 → 8 (1.0); 9116 → **11 (160.9)** |
| 32000 | 1.10 | 32 | 9121 → 5 (0.30); 9122 → 3 (0.40) |
| 32000 | 1.15 | 108 | 9123 → 8 (9.3); 9124 → **13 (84.8)** |
| 32000 | 1.20 | 256 | 9125, 9126 → **censored**, SIGKILL at 960 s; lower bounds 19 and 18 |

**Reading [inference; 1–2 instances per cell, so none of this is a cell
estimate].**
- **c\* above 2 does occur in this region.**
  - c\* ≥ 3 appeared at n ≥ 8000 with α ≥ 1.15, and at n = 32000 with every α.
  - At n = 2000, c\* was 0–3, each solved in milliseconds.
- **Runtime is not c\*.**
  - At n = 8000, α 1.20, c\* 8 took 1.0 s and c\* 11 took 161 s.
  - At n = 32000, α 1.15, c\* 8 took 9 s and c\* 13 took 85 s.
  - Only two of the 13 completed runs fell in (30, 900] s, both at
    n·ε³ ≥ 64. Most runs with c\* ≥ 3 were far below 30 s.
- **n = 32000, α 1.20 did not finish.**
  - Neither run finished, and in neither did SIGALRM take effect: each was
    killed by the watchdog. That means single SAT calls were longer than
    about 60 s.
  - The lower bound reached 17–18 within 20 s (§10) and only 18–19 by 960 s.
  - If the batch cell behaves the same way, it is `too_hard`, and each task
    costs the full 960 s.
- **Observed c\* sits far below the asymptotic CGHS ceiling.** For example,
  8–13 against (ε³/3)·n = 36 at n = 32000, α 1.15. That is consistent with
  the ceiling being an upper bound; it is not a test of it.
- **No change to the batch.**
  - The n = 2000 cells cost milliseconds, and the n = 32000, α 1.20 cell costs
    at most 5 × 960 s. Running all 9 as pre-registered gives the full picture
    at a real budget well under the 12 CPU-h maximum.
  - If the batch reproduces this pattern, the §6 follow-up for the next batch
    would put intermediate points between α 1.15 and 1.20 at n = 32000 and
    n = 8000, and test larger n at α 1.15. That proposal waits for the batch
    rows.

## 10b. Workstation memetic smoke at n ≥ 2000 (not data)

*Consolidated, with the v2 that followed, in [`MEMETIC_IMPL_V2.md`](MEMETIC_IMPL_V2.md).*

**Run 2026-10-08.** It answers the open question of whether the memetic solver
is usable at these sizes. Setup:
- **Arm:** the established primary arm `memetic_deeppolish_p40_ls3p5`, solver
  seed 1, `--stop-at-oracle`.
- **Budget:** 120 s, not 900 s. It is a feasibility check, not a TTT
  measurement.
- **Instances:** four instances from §10a whose c\* RC2 proved. Non-batch
  seeds.
- **Conditions:** 4 runs in parallel on the workstation.
- **Data:** rows in
  `cluster_staging_maxsat/results/workstation_check_calib_2sat_sc/memetic_smoke/`.

**Results [verified].**

| n | m | RC2 c\* | memetic best in 120 s | generations | children | flips per child (3.5 s each) | peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2000 | 2300 | 3 | 5 | 1 | 35 | ≈ 4800 | 23 MB |
| 8000 | 9600 | 11 | 67 | 1 | 34 | ≈ 1120 | 33 MB |
| 32000 | 35200 | 5 | **2250** | 1 | 32 | ≈ 300 | 67 MB |
| 32000 | 36800 | 13 | **2563** | 1 | 32 | ≈ 280 | 68 MB |

**Cause [verified in code].**
- The WalkSAT polish (`src/sat/walksat.py`, `walksat_polish`) picks an
  unsatisfied clause on every flip through `state.unsat_hard_ids()` and
  `state.unsat_soft_indices()` (`src/sat/state.py:298`, `:301`, `:332`).
- Each of those rebuilds a list by scanning all m clauses, so one flip costs
  O(m).
- The flips achieved per 3.5 s call fall roughly in proportion to m: about
  4800 at m = 2300 and about 290 at m ≈ 36 000.
- Standard WalkSAT keeps an incremental list of unsatisfied clauses and picks
  in O(1).

**Consequence [inference].**
- **The solver does too little search at this size.** At n = 32 000 a 900 s
  run would reach about 7 generations, with polish calls of about 300 flips
  that cannot even reach a local optimum. The incumbent stays thousands above
  c\*.
- **This is not the instances' difficulty.** At n ≥ 8000 a memetic "failure"
  under this configuration would measure the O(m) flip cost of this
  implementation, not the instances' difficulty.
- **The §6 follow-up for `promising` cells is therefore not meaningful as it
  stands at n ≥ 8000.** That follow-up is a memetic assessment with the
  established arm, in seconds.
- **n = 2000 is usable but slow.** The run got within 2 of c\* = 3 after one
  generation.

**Options (a decision for the user; nothing has been changed).**
1. **Keep the solver; restrict the memetic assessment to n where it works.**
   Report n ≥ 8000 as "RC2-only" cells.
2. **Make the unsatisfied-clause bookkeeping incremental**, giving O(1) picks
   with the same algorithm.
   - It changes the random trajectory, so the result is a new solver version.
   - Earlier memetic results (calib, uuf, SATLIB plans) were measured with the
     O(m) version. Seconds-based effort is then comparable only within one
     version, unless those runs are repeated.
   - It needs its own validation (same success rates on the existing
     instances, within noise).
3. **Change the per-call allowance** (`ls.time_limit_s`, flip budget). This
   does not remove the O(m) factor, so it only shifts the problem.

**Effect on the RC2 batch.** None. The batch can be submitted as prepared.
This decision is needed only before any memetic assessment of its cells.

## 10c. Memetic `impl: v2` (option 2, implemented 2026-10-08)

*The full reference is [`MEMETIC_IMPL_V2.md`](MEMETIC_IMPL_V2.md); this section is the batch-side summary.*

**The user's decision (2026-10-08)** [quote]: "go with option 2, make walksat
incremental keep possibility to use older version, you can make in new version
more optimizations".

**What v2 is** (`src/evo/impl_v2.py`, `src/sat/walksat_v2.py`). It is selected
by a top-level config key `impl: v2`. An absent key, which is every existing
config, means `v1`: the historical code, untouched. The three
`DIVERGENCE.md`-frozen files `sat/walksat.py`, `sat/state.py` and
`evo/operators.py` are unchanged and still byte-identical to the repo copies.
v2 changes three things:

1. **Polish.** The unsatisfied hard and soft clauses are kept in sorted lists
   (with `bisect`), and the counts and unsatisfied weight in counters.
   - Flip effects use per-variable (clause, multiplicity) lists, cached per
     instance.
   - The best assignment is a flip trail, undone once at the end.
   - Cost per flip is O(occ(v)) plus a C-level list insert or delete, instead
     of five O(m) scans.
   - Clause picks and candidate shuffles use exactly the `_randbelow` calls
     that v1's `rng.choice` and `rng.shuffle` make, so every decision is v1's.
2. **Crossover.** `clause_aware_crossover1` is unchanged in logic. Its
   instance-constant parts (soft proxy scores, hard occurrence lists) are
   built once per instance instead of on every call.
3. **No-op advisor round trip skipped.** The pre-polish evaluation and the
   `NoopProvider` advisor call (empty advice) are skipped. Their one RNG draw
   is kept.

**Equivalence [verified]** (`cluster_staging_maxsat/tests/test_walksat_v2.py`,
57 tests). With the same start, seed and flip or iteration budget, v2 returns
v1's exact final assignment, flip counts and objective on:
- soft-only 2-SAT and 3-SAT, weighted soft, and hard+soft instances;
- noise 0.1 and 0.5, `hard_safe` on and off, duplicate clauses.

v2's crossover gives v1's child. A whole EA run, including hard+soft with
deadline clipping, is identical under v1 and v2. The tests use a
deterministic tick clock, because v1 counts only *applied* flips against
`max_flips`: a hard-clause polish where nothing may flip loops until the time
limit, and v2 keeps that behaviour. The one intended divergence is a clause
with a repeated variable, where v2's soft gain is exact and v1's is not. There
v2 is checked for internal consistency.

**Speed [verified, workstation].** A 3.5 s polish call from a random start:

| n | m | v1 flips/s | v2 flips/s | 12 500-flip call, v2 |
|---:|---:|---:|---:|---:|
| 2000 | 2300 | 5 057 | ≈ 614 000 | 0.02 s |
| 8000 | 9600 | 961 | ≈ 508 000 | 0.03 s |
| 32 000 | 36 800 | 149 | ≈ 269 000 (≈ 509 000 when not capped) | 0.05 s |

**Memetic smoke, v2** (the §10b instances and settings: 120 s,
stop-at-oracle, 4 runs in parallel; rows in
`results/workstation_check_calib_2sat_sc/memetic_smoke_v2/`):

| n | RC2 c\* | v1 best (120 s) | v2 result | v2 generations | peak RSS |
|---:|---:|---:|---|---:|---:|
| 2000 | 3 | 5 | **optimum in 1.2 s** | 2 | 25 MB |
| 8000 | 11 | 67 | **optimum in 22.2 s** (RC2: 161 s) | 11 | 39 MB |
| 32 000 | 5 | 2250 | 14 at 120 s | 44 | 86 MB |
| 32 000 | 13 | 2563 | 25 at 120 s | 41 | 86 MB |

**Consequences [inference].**
- **v2 is the implementation for any memetic assessment of this batch.** Its
  config is `configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml`: the primary
  arm plus `impl: v2`.
- **Seconds-based effort is comparable only within one `impl`.** Earlier
  memetic results (M2 pool, uuf ablation, calib_c plans) are v1. They are not
  re-labelled. A cross-batch comparison either re-runs those instances under
  v2 or states the version boundary. Each shard records it: `memetic_impl`
  (shard schema 3).
- **The flip budget now binds before the time limit.** At n = 32 000 the
  established flip budget (12 500 flips per call) is used up in about 0.05 s,
  far inside the 3.5 s limit, so the limit no longer binds. Whether larger n
  should get a larger flip budget is a configuration question, not an
  implementation one. It is left unchanged here.
- **Two separate measurements.** This smoke shows the solver now does
  meaningful search at n = 32 000. It does not measure these instances'
  memetic difficulty: 1 seed, 120 s, workstation.

## 11. Open risks

1. **The memetic solver has never run at n ≥ 2000.** Its per-call time and
   memory at n = 32000 are unknown. A cell that turns out `promising` needs a
   short workstation smoke of the primary arm before any memetic array is
   sized.
   *Update 2026-10-08: the smoke has now run (§10b). Memory is fine (≤ 70 MB).
   But the WalkSAT polish costs O(m) per flip, so at n ≥ 8000 the established
   arm does almost no search in its budget. A decision is needed before any
   memetic assessment at these sizes.*
   *Update 2026-10-08, later: resolved by `impl: v2` (§10c). The established
   arm with v2 reaches the optimum at n = 2000 and n = 8000 within seconds,
   and searches meaningfully at n = 32 000.*
2. **The SIGALRM delay grows with n** (§5). A censored row's `solve_s` can
   exceed 900 s. The window rule already treats any t > 900 as censored.
3. **The CGHS bounds are asymptotic and for the with-replacement model**
   (§2, §4). Nothing here uses them as predictions.

## 12. Files

| file | role |
|---|---|
| `instancegen/grids/calib_2sat_sc.yaml` | the grid: 9 cells, per-cell seeds 201–245 |
| `instancegen/cli.py` | `generator: ksat_distinct` grid mode; per-entry seeds may stand without a top-level list |
| `instancegen/tests/test_grid_distinct.py` | batch-as-data and end-to-end tests |
| `cluster_staging_maxsat/data/generated/calib_2sat_sc/` | 45 `.wcnf` (gitignored) + `manifest.jsonl` (tracked) |
| `cluster_staging_maxsat/scripts/manifest_calib_2sat_sc_rc2.{txt,sha256}` | Slurm manifest (line N = task N) and checksums |
| `cluster_staging_maxsat/scripts/submit_rc2_calib_2sat_sc.sh` | submit wrapper (cap 900, grace 60, %30, `EXPECT_PYSAT=1.9.dev3`) |
| `cluster_staging_maxsat/scripts/rc2_profile_array.sbatch`, `submit_rc2_profile.sh` | the opt-in `EXPECT_PYSAT` guard; a corrected version comment |
| `cluster_staging_maxsat/scripts/calib_2sat_sc_readout.py` | the pre-registered readout (§6) |
| `cluster_staging_maxsat/tests/test_calib_2sat_sc_readout.py` | its tests |
| `cluster_staging_maxsat/scripts/preflight_calib_2sat_sc.sh`, `preflight_calib_2sat_sc_verify.sbatch` | cluster preflight (§9a): login part shell-only, verify job on a compute node |
| `cluster_staging_maxsat/scripts/submit_rc2_profile.sh`, `submit_m2_memetic.sh` | `RESUME=1` without Python on the login node (`IDS=`) |
| `instancegen/grids/calib_2sat_sc_smoke.yaml`, `cluster_staging_maxsat/data/generated/calib_2sat_sc_smoke/`, `scripts/manifest_calib_2sat_sc_smoke_rc2.{txt,sha256}` | the two non-batch smoke instances (seeds 9001/9002) used by the preflight |
