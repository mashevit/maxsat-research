# corpus_v1 — proposed benchmark-generation protocol (DRAFT r2, not frozen)

**Date:** 2026-10-06. **Status: draft for review; nothing here is frozen.**

A stratum is frozen only when:
- its entry is copied into `instancegen/grids/corpus_v1.yaml`, and
- that file is committed **before** the stratum's first final instance is
  generated.

Related documents:
- evidence and candidate table: [`CORPUS_FREEZE_PREP.md`](CORPUS_FREEZE_PREP.md);
- session handoff: [`NEXT_SESSION_CONTEXT.md`](NEXT_SESSION_CONTEXT.md);
- pre-registered rules this draft carries forward:
  [`CORPUS_CALIBRATION_GOALS.md`](../CORPUS_CALIBRATION_GOALS.md) §4–§5.

**Revision log**
- **r1** (2026-10-06, earlier): first draft, with a fresh reference stratum
  R (seeds 1001–1080, 80 instances), ERT in polish calls proposed as
  primary, and a 40–50 eligible-instance target.
- **r2** (2026-10-06, user decisions):
  - PySAT 1.9.dev3 is fixed (§2);
  - **seconds stay the primary effort measure** (§7, §8.3);
  - the sample size is **left open**, with the trade-off stated (§5.2);
  - **stratum R is removed**: no new n = 250, c\* = 1 instances (§3.1);
  - `calib_c` submission is pending;
  - MaxCut is the proposed next milestone;
  - a stratum candidate is added for the pending Max-3-SAT n > 250
    assessment.

  The r1 versions of these items are superseded. They are listed here and in
  the freeze-prep r2 box, not silently rewritten.
- **r3** (2026-10-06, end of day, user direction; documentation only):
  - new direction: **larger n in both Max-2-SAT and Max-3-SAT**, with α
    chosen per size, to find hard instances. K3-L is widened, and a K2-L
    row is added (§3);
  - `calib_c` is **on hold**, to be reassessed against the direction (keep,
    revise or replace). Its construction is not in question;
  - seconds stay primary (D2); the n = 250, c\* = 1 reference is preserved
    with no new instances (D4).

**Objective.** Generate diverse instances on which both RC2 and the memetic
solver do meaningful work. The protocol is not tuned toward any value or sign
of ρ. A positive, weak or negative association is an acceptable result.

---

## 1. Principles

1. **Two selection stages that are never mixed.**
   - *Cell selection* uses calibration batches (generator seeds < 1000) and
     may look at memetic outcomes.
   - *Final instances* (seeds ≥ 2001) are filtered **only** by the RC2 rule
     of §4. They are never filtered on a memetic outcome.
2. **Every final RC2-eligible instance of a frozen cell is in the primary
   sample.** That includes instances that turn out to be memetic-easy. The
   achieved joint-difficulty yield is reported.
   - A labelled *jointly non-trivial subset* (§8.4) may also be reported. It
     never replaces the primary sample.
3. **Each family, and each stratum within it, has its own calibration and
   its own freeze milestone.** A stratum freezes when its own gate passes,
   and is not held for another family.
4. **Sample size is counted in independent instances per reported stratum,**
   never in solver runs. Instances of one family never count toward another
   family's stratum.
5. **Unweighted and weighted strata are separate tracks.** Weighted twins
   never count toward an unweighted stratum.

## 2. Solvers and environments

### 2.1 RC2 (all calibration batches and every new stratum)

| item | value |
|---|---|
| library | **PySAT 1.9.dev3** (decided 2026-10-06). It is the version recorded in `task_N.env.json` on all 290 calib_a/b tasks; the goals doc's "1.9.dev15" was the workstation version and is superseded for cluster runs. |
| call | `RC2(wcnf, solver="g3")` (Glucose 3 backend) |
| options | PySAT defaults: `adapt=False, exhaust=False, incr=False, minz=False, process=0, trim=0`. With unit weights every core raises the lower bound by exactly 1. |
| runs | one per instance (RC2 is deterministic; its timing noise is unmeasured) |
| budget | cap 900 s, then 60 s grace, then SIGKILL. On a kill the lower bound is recovered from the progress file. |
| profiler | `src/cli/profile_hardness.py` → `solve_rc2_anytime.py`; staging copies byte-identical to repo `src/` |
| driver | `scripts/rc2_profile_array.sbatch` via `submit_rc2_profile.sh`: 1 CPU, 8 GB, `--time 00:20:00`, throttle %30 |
| environment | cluster conda env `maxsat`, Python 3.11.15, PySAT 1.9.dev3 — recorded per task. A task with another PySAT version is a failed task. |

### 2.2 Memetic, primary configuration

| item | value |
|---|---|
| config | `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml` |
| EA | pop 40, tournament 3, `pmutate` 0.02, 2 elites + 38 children per generation, JW-seeded initial population |
| polish | one WalkSAT polish call per child: `ls.time_limit_s` 3.5 s, 12,500 flips (`ls_polish_flips` = `flip_budget`), noise 0.10 |
| deadline | `ea.deadline_mode: clip` |
| budget | 900 s, watchdog grace 60 s |
| stop | at the RC2 optimum (`STOP_AT_ORACLE=1`) |
| code | staging tree `cluster_staging_maxsat/src/` at the commit named by `MAXSAT_GIT_SHA`. `submit_m2_memetic.sh` refuses to submit without it and records `src_tree_sha256`. |
| driver | `scripts/tier2_memetic_array.sbatch`: 1 CPU, 8 GB, `--time 00:20:00`, %30 |

Further constraints:
- No instrumentation inside polish calls.
- No other arm is part of corpus_v1. The 0.5 s arm, uniform and JW
  multistart are calibration or historical only. No further multistart or JW
  runs are planned.

## 3. Strata

| id | family / cell | status | blocker |
|---|---|---|---|
| **REF** | Max-3-SAT n 250 (m 1065 / 1088), c\* 1: **historical evidence only** | **no new instances** (decision 2026-10-06) | — (§3.1) |
| **K2** | random Max-2-SAT, n 400, α 2.0 and/or α 2.15 (m 800 / 860) | conditional; **r3: `calib_c` on hold** | reassess `calib_c` against the larger-n direction (keep / revise / replace); then the unchanged §5.3 rule per cell |
| **K2-L** | random Max-2-SAT, n > 400, α chosen per n (r3) | **direction set; grid not designed** | written larger-n grid plan, approved before any generation (`NEXT_SESSION_CONTEXT.md` §0, R3-b) |
| **K3-L** | random Max-3-SAT, n > 250, densities and clause counts to be chosen | **direction set (r3); grid not designed** | as K2-L; also R3-c (accept c\* ≤ 1 cells, or require c\* > 1) |
| **C-ER** | MaxCut on G(n, p), unweighted | **proposed next implementation milestone; not started** | `instancegen/maxcut.py` + `verify.py`; RC2 and memetic calibration |
| **C-PM** | ±J spin glass on the L × L torus, unweighted | planned with C-ER | as C-ER; spec in freeze-prep §6.3 |
| **S1** | MSE-2016 `maxcut/dimacs-mod` (62) + `maxcut/spinglass` (5), published | on disk | 900 s RC2 screen of all 67 not run (3 profiled, at 300 s) |
| **H** | conflict-clause hard instances (Max-Independent-Set / Max-Clique on G(n, p)) | option (freeze-prep §8.5) | generator + diagnostic. Effort is time-bound, so it is never pooled with all-soft strata |
| **W** | reweighted twins of frozen unweighted strata | later, separate track | `reweight.py`; needs frozen bases |
| — | partial random k-SAT, set cover, judgment aggregation (mixed-sign hard clauses) | excluded | verified operator failure with the current solver (freeze-prep §8.5) |

### 3.1 The reference regime: existing evidence and its original conditions

No instance is generated for it. It is reported as existing evidence only.

**(a) Historical SATLIB set** (26 instances: uuf250 × 24 at c\* = 1, uuf200
× 2 at c\* = 2).

| | conditions |
|---|---|
| RC2 | 18 instances from `results/hardness/uuf250_1000c` at **cap 900 s**; 8 from `uuf_diff_unsat` at **cap 600 s** (`scripts/archive/tier2_memetic/tier2_oracle.csv`). Backend g3, default options. **PySAT version and cluster resources at run time are unknown** (`docs/archive/RC2_STATUS.md` §5). |
| memetic | `memetic_deeppolish`: pop 40, 0.5 s per polish call (time-bound; the 12,500-flip cap never binds, about 2,200 iterations per call), **unclipped** generation-boundary deadline. 5 seeds, 900 s budget, target stop. Slurm array 20085583, 2026-08-12. `config_hash 8f4ba81eb1d96c66`, `git_sha` null. 118/130 successes. |
| no-EA baselines | uniform multistart (array 20721254, 124/130); JW multistart (array 22314854, 127/130); same 0.5 s polish |
| read-outs | `docs/archive/TIER2_ABLATION_FAIRNESS_AUDIT.md`, `docs/UUF_THREE_ARM_ABLATION_READOUT.md` |

**(b) Calibration rows in the same regime** (generated, seeds 1–10):
- RC2: `max3sat_n250_a4.26` (10 instances) and `max3sat_n250_a4.35` (5),
  PySAT 1.9.dev3, cap 900;
- memetic: M2 full pool, both arms, 3 seeds, on their 8 eligible
  instances;
- these are calibration data and enter no final ρ (goals §5.4).

## 4. RC2 eligibility (all strata)

- **Eligible** ⇔ RC2 `completed == true` **and** `final_cost ==
  cost_lower_bound` **and** **30 s < `solve_s` ≤ 900 s**.
- **Boundary convention:**
  - 30.000 s exactly is *below* the window;
  - 900.000 s is *inside*;
  - a completion with `solve_s` > 900 s is *censored*.
- **Below window** (certified, ≤ 30 s): counted. No memetic run.
- **Censored** (`timeout` / `subprocess_killed` at cap 900): counted, with
  the lower bound kept. No memetic run, and no target exists.
- **Failed** (`error`, `unsat`, no row, `solve_s` ≤ 0,
  `final_cost ≠ lower bound`, wrong PySAT): re-run until a valid row exists.
  A failed row never enters a denominator.

The classifiers are `candidate_cells.rc2_class` and
`make_calib_c_memetic_manifest.classify`. A test asserts they agree.

## 5. Generation and sample size

### 5.1 Seeds

- Final generator seeds start at **2001**, one disjoint block per stratum.
  The r1 range 1001–1080 belonged to the removed stratum R and is not used.
- Seeds stay disjoint from every calibration batch: 1–10 and 101–120.
- **G** (instances generated) is fixed in the grid file before generation.
- At most **one** pre-declared top-up block, triggered only by the count of
  RC2-eligible instances. That count is known before any memetic run, so the
  top-up cannot select on y.
- Every generated instance is in the accounting.

**S1 is a fixed published set.** It has no fresh seeds and no cell
selection:
- all 67 files are screened by RC2;
- every eligible file is in the primary sample;
- the memetic arm runs once, as the final measurement.

### 5.2 Instances per stratum: open decision, and the trade-off

**No number is committed.** The choice depends on what the stratum's ρ is
meant to support.

**Estimating a correlation** means reporting ρ with an honest interval. A
moderate association can be shown to be non-zero with fewer instances.

**Claiming that a correlation is close to zero** is an equivalence claim: the
whole CI must lie inside a margin such as |ρ| < 0.3. That needs more
instances even when the true ρ is exactly 0, and many more if the true ρ is
small but not 0.

95 % Bonett–Wright intervals by N and true ρ:

| N eligible | true ρ = 0 | true ρ = 0.3 | true ρ = 0.5 |
|---:|---|---|---|
| 15 | ±0.51 | −0.27 … 0.71 | −0.05 … 0.82 |
| 20 | ±0.44 | −0.17 … 0.66 | 0.05 … 0.78 |
| 30 | ±0.36 | −0.08 … 0.60 | 0.15 … 0.74 |
| 40 | ±0.31 | −0.02 … 0.56 | 0.20 … 0.71 |
| 50 | ±0.28 | 0.02 … 0.54 | 0.24 … 0.69 |

How to read the table:
- N ≈ 20 can separate ρ ≈ 0.5 from 0. The M2 2-SAT calibration ρ was
  0.5–0.7; it is exploratory and is **not** used for sizing.
- Even at true ρ = 0, a "|ρ| < 0.3" claim needs N ≳ 44, and a
  "|ρ| < 0.2" claim needs N ≳ 97.
- A smaller stratum is defensible if it is reported as an estimate with a
  wide interval, never as evidence of orthogonality.

**Compute.** The cost per eligible instance scales with RC2 window yield and
memetic run length. For 2-SAT n = 400, α 2.15, from existing rows (yield
4/5, RC2 ≈ 178 s per generated instance, 3.5 s-arm runs ≈ 17 s):

| | per eligible instance | N = 20 | N = 40 |
|---|---|---|---|
| expected | 222 s RC2 + 5 × 17 s memetic ≈ 0.085 CPU-h | ≈ 1.7 CPU-h | ≈ 3.4 CPU-h |
| worst case | 1,200 s RC2 + 4,800 s memetic ≈ 1.7 CPU-h | ≈ 33 CPU-h | ≈ 67 CPU-h |

- Other families will differ: compute is set per stratum at its freeze.
- Generation is cheap. The binding costs are censored RC2 runs (960 s each)
  and memetic failures (900 s each).

## 6. Solver seeds and runs

- **Memetic:** solver seeds **1–5** on every eligible instance (goals §4.2).
  Primary arm only.
- **RC2:** one run.
- Optional, separate: a repeatability sample (about 15 eligible instances ×
  3 runs, chosen by seed order, not by outcome) to bound the attenuation
  that RC2 timing noise causes.

## 7. Target detection and effort

**Target and success.**
- The target is the RC2-certified c\*, in unsatisfied soft weight.
- A run succeeds iff `stop_reason == "target"` and `time_to_target_s` ≤ 900.
- The target is checked after every child's polish call and on the initial
  population. Effort below one call is not resolved; that is a stated
  limitation, and no within-call instrumentation is added.

**Primary effort measure: seconds** (pre-registered, goals §4.2 and §5.2;
unchanged).
- Per run: `time_to_target_s` (successes) or the full 900 s (failures).
- Per instance (seeds collapsed first):
  - **ERT_s** = Σ min(wall, 900) over the 5 runs / successes;
  - median TTT, with failures counted as +∞;
  - successes / 5;
  - Q2 = successes < 5 **or** median TTT ≥ 45 s.

**Secondary diagnostics:** `children` (polish calls), `total_flips`, ERT in
calls and in flips, the beyond-generation-1 count, and first-call success.

**What the secondary measures do and do not remove:**
- Calls are **not** equal units of work. Under the 3.5 s arm a call costs
  about 1.25 s at m = 400 and about 3.0 s at m = 1,088. Calls on
  hard-clause instances idle to the time limit.
- Flips are equal *iterations*, but an iteration costs O(m).
- When the 3.5 s limit binds instead of the 12,500-flip cap (slow hosts at
  m ≈ 1,088 in M2; always under the 0.5 s arm), the number of flips per call
  depends on the host. The search trajectory, and so the call count to
  target, then changes across hosts.
- Calls and flips therefore remove *some* call-length and host effects. They
  are not size-free or host-free, and they are reported as diagnostics, not
  as the primary measure.

## 8. Outcomes, censoring, failures, and analyses

### 8.1 Run classes

The run classes are those of `scripts/m2_results.py`:

| class | counted as |
|---|---|
| `success` | success |
| `budget_exhausted` | failure, charged 900 s |
| `target_after_budget` | failure |
| `watchdog` | investigated first; re-run only if shown to be infrastructure |
| `infra_*` / `invalid_submission` | re-run; never counted |
| `max_gens` / `cost_mismatch` | integrity failure; stops the stratum's read-out until explained |

### 8.2 Instance-level exclusions

- **0 successes:** ERT is undefined. The instance is excluded from the
  primary ρ, with the count printed. A sensitivity analysis enters it as
  top-tied.
- RC2 censored and below-window instances are outside the population and
  are counted (§4).

### 8.3 Primary analysis, per reported stratum

Unit: the instance (N = eligible instances with ≥ 1 success).
1. **Spearman ρ** (average ranks) between RC2 `solve_s` and memetic
   **ERT_s**. The same ρ with ERT in calls and in flips is a labelled
   secondary analysis.
2. **95 % CIs:**
   - plain instance bootstrap, percentile, B = 10,000, fixed seed;
   - Fisher z with the Bonett–Wright SE.
   - The cell-stratified BCa interval is reported only when every cell of
     the stratum holds ≥ 10 instances (M2 read-out §7.6).
3. **Partial ρ** on log(1 + c\*), plus α when a stratum spans two α cells.
4. **Descriptives:**
   - success counts;
   - median TTT;
   - the joint-difficulty yield (Q2 fraction, with a Wilson interval);
   - the beyond-generation-1 fraction;
   - window yield;
   - the tie count at the one-call floor.
5. **Interpretation follows §5.2.** An interval that includes 0 is reported
   as "not distinguishable from 0 at this N", never as evidence of
   orthogonality, unless it lies inside a pre-stated equivalence margin.

### 8.4 Labelled secondary sample

**Jointly non-trivial subset:** eligible instances that are Q2 under the
primary arm.
- Same statistics as §8.3.
- Always printed next to the primary result, with its N and its fraction of
  the primary sample.
- It conditions on the outcome variable's own scale, so it is a description,
  not an estimate of the primary ρ.

### 8.5 Pooled statistics

- Families are always reported separately.
- One pooled statistic is pre-defined: the **within-stratum rank
  correlation**. In each stratum, x and y are replaced by mid-ranks scaled
  to (0, 1), and the scaled pairs are correlated across strata (M2 read-out
  §7.2). Its bootstrap resamples instances within strata.
- No raw pooled ρ across families is a result.

## 9. Accounting

Every generated instance appears in exactly one row of a per-stratum table:
- the generated count, then the RC2 classes;
- for eligible instances, the memetic run classes, with re-runs listed;
- the instances in the primary ρ, the instances excluded with 0 successes,
  and the jointly non-trivial count.

Manifests (`manifest.jsonl`, Slurm manifests, `.not_run.csv`) are committed.
Instances regenerate byte-for-byte from the grid.

## 10. Decisions

| # | decision | status |
|---|---|---|
| D1 | RC2 version | **closed:** PySAT 1.9.dev3 (§2.1) |
| D2 | primary memetic effort measure | **closed:** seconds, as pre-registered; calls and flips secondary (§7) |
| D3 | instances per reported stratum | **open:** trade-off in §5.2; to be decided per stratum at its freeze |
| D4 | reference stratum | **closed:** no new n = 250, c\* = 1 instances; historical evidence only (§3.1) |
| D5 | submit `calib_c` | **on hold (r3):** reassess against the larger-n direction; keep, revise or replace |
| D6 | next implementation milestone | **proposed:** MaxCut generator (C-ER, C-PM). Not started. Open design questions are in `NEXT_SESSION_CONTEXT.md` §6 |
| D7 | Max-3-SAT n > 250 | **widened (r3):** larger n in Max-2-SAT and Max-3-SAT; grid plan (R3-b) and c\* range (R3-c) open |
| R3-d | order of the larger-n k-SAT work and MaxCut (D6) | **open** |
