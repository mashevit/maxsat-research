# M2 full pool read-out, ρ(RC2, memetic) analysis, and state of the research

**Date:** 2026-10-04. **Written against:** commit `69c9b97` plus the
untracked results directory `cluster_staging_maxsat/results/m2_full_p40/`
(copied from the cluster today) and a new analysis script
`cluster_staging_maxsat/scripts/m2_rho_analysis.py`.

**Intended reader:** a person or another LLM with no access to the
repository. The document is self-contained. It explains the project, the
solvers, the instance population, how the data was produced and checked,
all results including ρ, what the results mean, and what is missing. §11
lists the data files that can be attached alongside it, with column
dictionaries. §12 lists open questions an external analyst could take up.

Paths are relative to the repository root unless they start with
`results/` or `scripts/`. Those are relative to `cluster_staging_maxsat/`,
the tree that runs on the Slurm cluster.

---

## 0. Summary

- **The run is clean.** All 420 tasks completed (70 instances × 3 solver
  seeds × 2 arms). There were 0 watchdog kills, 0 invalid rows and 0
  infrastructure errors. The submitted source tree was verified
  byte-for-byte against commit `69c9b97`. Each budget-exhausted run
  overshot 900 s by 15–21 ms. Compute used was **4.1 CPU-h** of the
  105 CPU-h ceiling.
- **Success:**
  - 0.5 s/call arm: **202/210** runs succeed;
  - 3.5 s/call arm: **208/210** runs succeed;
  - every instance is solved at least once by each arm;
  - all 10 failed runs end at cost c\* + 1.
- **The memetic solver finds most of this population easy:**
  - on **28/70** instances every one of the 6 runs reaches the optimum with
    its first local-search call;
  - on **55/70** no run needs a second generation;
  - by the pre-registered "non-trivial" rule (median TTT ≥ 45 s or
    success < 100 %), only **5** instances qualify under the 0.5 s arm and
    **9** under the 3.5 s arm.
- **Memetic hardness is a stable property of the instance, not seed
  noise:**
  - the two arms rank the instances almost identically (ρ = 0.89);
  - the ICC of log LS calls to target across seeds is 0.86–0.88.
- **ρ(RC2 proof time, memetic expected running time (ERT)), one point per
  instance, N = 70:**
  - **pooled:** ρ is **+0.05 to +0.10**, with 95 % CIs of about −0.2 to
    +0.33. The CI does not exclude |ρ| = 0.3;
  - **within the two families the picture differs completely:**
    - **Max-2-SAT (N = 26):** ρ = **+0.49 to +0.68**, CI lower bounds
      0.14–0.41;
    - **Max-3-SAT (N = 44):** ρ = **−0.05 to −0.15**, CI about −0.44 to
      +0.26;
  - **partial ρ** (controlling for log n, α, log(1 + c\*)):
    - pooled: +0.15 to +0.24 (+0.29 to +0.35 if k is added);
    - Max-2-SAT: +0.40 to +0.50;
    - Max-3-SAT: −0.02 to +0.13;
  - **within (k, n) rows** (N = 66): +0.29 to +0.35, with CIs about 0.05 to
    0.55.
- **Why the pooled ρ is near zero.** The RC2 time window (30–900 s) picks
  instances along a diagonal in (n, c\*). In 3-SAT:
  - **small n, high α, c\* = 9–13:** RC2 is slow because it needs many
    cores. The memetic solver finds these trivial;
  - **n = 250 at the threshold, c\* = 1:** RC2 is slow because each SAT
    call is expensive. The memetic solver finds these hard.
  - **Consequences.** Within the selected 3-SAT pool, c\* and n have
    ρ = −0.97. Memetic effort follows n (ρ ≈ +0.8) and so moves against
    c\* (ρ ≈ −0.8). RC2's per-call cost correlates positively with memetic
    effort (ρ ≈ +0.33 to +0.43), while its core count (c\*) correlates
    negatively, and the two cancel.
  - **What this means for the "complementary hardness" reading.** It holds
    for 3-SAT in this window, but it is largely a product of how the window
    selects instances. It is not evidence that the two solvers measure
    different things at fixed instance structure.
- **The historical point agrees.** On 26 SATLIB uuf250/uuf200 instances,
  ρ(RC2, `memetic_deeppolish` ERT) = +0.19, CI about −0.22 to +0.54. There
  c\* is almost constant (24/26 have c\* = 1).
- **Status:** these are calibration rows. The project's own rules
  (`CORPUS_CALIBRATION_GOALS.md` §5) make this ρ exploratory: it must not
  be reported as the final Q3 answer. The pipeline steps M3 (yield table),
  M4 (frozen selection rules, fresh corpus) and M5 (final analysis) are not
  done. §10 lists what is missing.

---

## 1. The project in brief

**Goal.** Build a benchmark corpus of MaxSAT instances. On each one, an
exact solver (RC2) and a stochastic memetic solver (an evolutionary
algorithm with WalkSAT polishing) are both measured. Then test whether
"hardness" means the same thing for the two.

### Research questions (from `docs/CORPUS_CALIBRATION_GOALS.md` §1)

- **Q1 Reachability.** Over which region of (n, α) does RC2 certify the
  optimum c\* within 900 s? How does its proof time vary with n, α and c\*?
- **Q2 Informativeness.** Inside that region, where does the memetic solver
  do non-trivial work? Non-trivial means it neither reaches the optimum
  within the first few percent of its budget on every seed, nor fails on
  every seed.
- **Q3 Complementary hardness.** What is the Spearman ρ between RC2 proof
  time and memetic time-to-target (and success rate), pooled and within
  family? How much of any relation do the shared covariates n, α and c\*
  explain?

### Pre-registered hypotheses (§2.4, written 2026-09-16)

- **H1.** RC2 time increases with α and c\* at fixed n, and with n at
  fixed α.
- **H2.** Memetic TTT is governed mainly by n and by closeness to the
  critical density α_c, not by c\*.
- **H3.** The region where both solvers do non-trivial work is a diagonal
  strip in (n, α), and may be narrow or empty for 3-SAT.
- **H4.** Inside the strip, ρ(RC2, memetic) is low once n, α and c\* are
  controlled for. This is the claim the final corpus is meant to test.

### Notation

| symbol | meaning |
|---|---|
| α | m/n, clause density. α_c ≈ 4.267 for random 3-SAT |
| c\* | optimum cost, the number of unsatisfied clauses (all weights are 1) |
| ρ | Spearman rank correlation |
| TTT | memetic time-to-target |
| ERT | expected running time = (total effort over all seeds, with failures charged their full spend) / (number of successes) |

### Pre-registered statistical conventions (§5.2, fixed before any data)

- **Sampling unit:** the instance. Solver seeds are collapsed to ERT or
  success rate first.
- **Primary CI:** instance bootstrap stratified by cell, B = 10,000, BCa,
  with the percentile interval alongside.
- **Checks:**
  - plain bootstrap;
  - Fisher z with the Bonett–Wright Spearman SE √((1 + ρ²/2)/(N − 3)).
- **Partial ρ:** residualize the rank-transformed x and y on
  [log n, α, log(1 + c\*)].
- **Zero-success instances:** excluded in the primary analysis, and
  entered as top-tied in a sensitivity analysis.
- **Within-cell ρ:** not estimated, because cells are too small.
- **Calibration rows** never enter the final reported ρ. The final ρ comes
  from fresh seeds 1001–1020.

---

## 2. Solvers and configurations

### 2.1 RC2 (exact)

- **Solver:** PySAT `RC2(wcnf, solver="g3")` with
  `adapt = exhaust = minz = False`. The cluster ran PySAT 1.9.dev3,
  uniformly in both RC2 batches. One run per instance (RC2 is
  deterministic).
- **Limits:** cap 900 s, grace 60 s, then SIGKILL. A lower bound is
  recovered on a kill.
- **Structural fact.** With unit weights and these options, every core
  raises the lower bound by exactly 1. Certification therefore takes
  exactly c\* UNSAT oracle calls plus one SAT call. That gives a natural
  decomposition:

  `rc2_solve_s = (c* + 1) × rc2_s_per_oracle_call`

  The second factor is an average over calls of unequal cost. It is used
  here as a descriptive proxy, not a measured quantity.

### 2.2 Memetic solver (`memetic_ea`, staging tree `src/evo/memetic.py`)

**Population and seeding**
- Population of 40, initialized from a Jeroslow–Wang-biased random prior.
- The initial population gets **no** local search.

**Each generation**
- **Elites:** 2 elites are kept (5 %).
- **Children:** 38 children are made, each by:
  1. tournament selection (k = 3);
  2. clause-aware crossover;
  3. mutation (p = 0.02);
  4. one **WalkSAT polish call** (`short_polish` → `walksat_polish`: noise
     0.10, no tabu, no clause weighting).
- **Polish call limits:** at most 12,500 flips **and** at most
  `ls.time_limit_s` seconds.
- **Stopping:** the incumbent is checked after every child. With
  `STOP_AT_ORACLE=1` the run stops as soon as cost ≤ c\* (target stop).
  Otherwise it stops at 900 s.
- **Deadline clipping:** `deadline_mode: clip` cuts each call's time
  allowance to the remaining budget.

**What the effort counters mean**
- `children` is the number of WalkSAT polish calls. 1 means the very first
  polished child already hit the optimum.
- `total_flips` is the sum of flips over all calls.
- WalkSAT does not know the target. Every call runs to its own limit
  before the check, so effort below one call is **not resolved**.

**The two arms of the full pool**

| arm (short) | config | pop | `ls.time_limit_s` | flip cap / call | what binds |
|---|---|---:|---:|---:|---|
| `a05` = `p40_ls0p5_clip` | `configs/tier2/memetic_deeppolish_p40_ls0p5_clip.yaml` | 40 | 0.5 s | 12,500 | **time**: run means of 2,043–5,339 flips per call (median 4,235) |
| `a35` = `p40_ls3p5` | `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml` | 40 | 3.5 s | 12,500 | **flips**: 12,500 per call on all but 3 runs |

- **What differs.** The arms differ **only** in `ls.time_limit_s`; a test
  pins this.
- **Relation to history.** `a05` is the historical `memetic_deeppolish`
  config plus deadline clipping. Clipping changes nothing before the budget
  binds.
- **Why `a35` exists.** It was introduced after a pilot showed that the
  0.5 s allowance, not the 12,500-flip limit, ends every call (see
  `docs/M2_DEEPPOLISH_SUMMARY.md` and `docs/M2_PILOT_READOUT.md`).
- **Common settings:** budget 900 s, grace 60 s, target = RC2 c\*, 1 CPU,
  8 GB.

**Seconds per polish call under `a35`**, which grow with m:

| m | 400 | 450 | 500 | 550 | 600 | 720 | 800 | 860 | 920 | 1065 | 1088 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| s / call | 1.25 | 1.27 | 1.46 | 1.56 | 1.68 | 2.04 | 2.11 | 2.34 | 2.56 | 2.88 | 3.02 |

**What this implies for the time-based effort measures:**
- **ERT in seconds** on a trivial instance measures the length of one call,
  not difficulty:
  - `a05`: ≈ 0.5 s;
  - `a35`: ∝ m.
- **Children (LS calls) to target** is free of that artefact. It is the
  preferred difficulty measure in §7. For `a35`, ERT in flips is exactly
  12,500 × ERT in children, so the two give the same ρ.

---

## 3. Instance population and selection

### 3.1 Generation

- **Families:**
  - random Max-3-SAT (k = 3);
  - random Max-2-SAT (k = 2);
  - both pure soft, unit weights, m = round(α·n).
- **Generator:** `instancegen.generate`, old-dialect WCNF. The manifests
  are `cluster_staging_maxsat/data/generated/calib_{a,b}/manifest.jsonl`.
- **`calib_a`:** 36 cells × 5 seeds = 180 instances.
  - 3-SAT: n ∈ {50, 70, 100, 150, 250}, α ∈ {4.26, 5, 6, 8};
  - 2-SAT: n ∈ {100, 150, 250, 400}, α ∈ {2, 3, 4, 6}.
- **`calib_b`:** 22 refinement cells, 110 instances. Five reinforcement
  cells carry 10 seeds each.

### 3.2 RC2 outcome on all 290 (`results/m2_full_p40/analysis/rc2_population_290.csv`)

| | k = 2 | k = 3 | total |
|---|---:|---:|---:|
| instances | 130 | 160 | 290 |
| uncertified at 900 s (killed or timeout) | 57 | 56 | 113 |
| certified | 73 | 104 | 177 |
| certified, RC2 ≤ 1 s | 20 | 39 | 59 |
| certified, 1–10 s | 18 | 14 | 32 |
| certified, 10–30 s | 9 | 7 | 16 |
| certified, 30–60 s (`lower_ext`) | 6 | 10 | 16 |
| certified, 60–600 s (`tier2`) | 18 | 28 | 46 |
| certified, 600–900 s (`upper_ext`) | 2 | 6 | 8 |
| **in the M2 pool (RC2 30–900 s)** | **26** | **44** | **70** |

**The pool is range-restricted on the x-axis of ρ.** The 107 certified
instances with RC2 < 30 s were never run with the memetic solver, and
neither were the 113 uncertified ones. Every ρ below is conditional on
RC2 time ∈ [30, 900] s.

### 3.3 Composition of the 70

The 70 instances fall into 24 cells. **Cell sizes in the pool are small:**
6 cells hold 1 instance, 5 hold 2, 6 hold 3, 4 hold 4, 2 hold 6 and 1 holds
8. This matters for the stratified bootstrap (§7.6).

c\* ranges:
- **2-SAT:** c\* 18–50.
- **3-SAT:** c\* 1–13.
- The two ranges are disjoint.

Within the pool, c\* is strongly anti-correlated with n:
- ρ(c\*, n) = −0.97 in 3-SAT;
- ρ(c\*, n) = −0.88 in 2-SAT.

| (k, n) row | instances | α range | c\* range | RC2 s range |
|---|---:|---|---|---|
| k2 n100 | 6 | 4.0–6.0 | 31–50 | 31–753 |
| k2 n150 | 7 | 3.0–3.3 | 23–28 | 32–301 |
| k2 n250 | 2 | 2.35 | 18–22 | 71–610 |
| k2 n400 | 11 | 2.0–2.3 | 18–23 | 43–413 |
| k3 n50 | 14 | 8.0–9.0 | 9–13 | 33–847 |
| k3 n70 | 13 | 6.0–6.5 | 5–8 | 35–436 |
| k3 n100 | 7 | 5.0–5.5 | 4–5 | 47–213 |
| k3 n150 | 2 | 4.8–5.0 | 2–3 | 35–772 |
| k3 n250 | 8 | 4.26–4.35 | 1 | 33–388 |

**Variance decomposition of log RC2 time.** The identity is
log t = log(c\* + 1) + log(per-call).

| family | var log t | var log(c\*+1) | var log per-call | 2·cov |
|---|---:|---:|---:|---:|
| k2 | 0.86 | 0.06 | 0.87 | −0.08 |
| k3 | 0.92 | 0.41 | 1.01 | **−0.50** |

- **2-SAT:** RC2 time variation in the pool is almost entirely per-call
  cost.
- **3-SAT:** about half comes from c\*, and the two components offset each
  other (negative covariance). This is the selection effect of the 30–900 s
  window.

---

## 4. Timeline and milestone status

| step | what | status |
|---|---|---|
| tier-2 (Aug 2026) | memetic configs on 26 SATLIB uuf250/uuf200 instances (c\* ≈ 1), 5 seeds, 900 s; no-EA multistart ablation | done; data in `results/tier2_*` |
| MSE-2016 screen | structured / crafted instances | all RC2 and EvalMaxSAT timeouts up to 1800 s; abandoned as a source |
| M1 / A1 | calib_a generated, RC2 run on 180 | done 2026-09-16/22 |
| B1 | calib_b refinement, RC2 run on 110; eligibility 10 → 46 | done 2026-09-22 |
| M2 handout | finding that the 0.5 s LS cap binds; deadline clipping designed | done 2026-09-24 |
| M2 pilot | 10 instances × 3 seeds × 4 arms (96 tasks) | done 2026-10-04; commit unverified (`git_sha` null) |
| **M2 full pool** | **70 × 3 × 2 arms = 420 tasks** | **done 2026-10-04; read out here** |
| M3 | yield table, `calib_summary.py`, formal ρ/CI table | **not built**; this document's script is an interim |
| M4 | freeze cell-selection rules (`instancegen/grids/corpus_v1.yaml`); fresh seeds 1001–1020; RC2 certification | not started |
| M5 | 5 memetic seeds on the fresh corpus; final Q1–Q3 | not started |

---

## 5. M2 full pool: integrity and provenance

**Run record**

| item | value |
|---|---|
| submission | one array, `sbatch --array=1-420%30`, Slurm job 22131008, 2026-10-04T11:42:33Z |
| `MAXSAT_GIT_SHA` | `69c9b97dcb2402e6b8d6f01f1724cb1806fbfad7`, recorded in every shard |
| `src_tree_sha256` in provenance | `8989fb8f…a410a3f`, equal to the digest recomputed from `git archive 69c9b97`: **verified** |
| shards | 420/420; `pending` = 0 |
| classes | 410 `success`, 10 `budget_exhausted`; 0 watchdog, 0 `target_after_budget`, 0 max_gens, 0 cost_mismatch, 0 invalid, 0 infra |
| overshoot past 900 s | 0.015–0.021 s on all 10 budget-exhausted runs, both arms |
| cpu/wall | ≥ 0.92 on every task but one. The exception is `m2f_p40ls0p5clip_024_s3` at 0.856, a 0.59 s trivial run, harmless |
| hosts | 17; the largest share was 90 tasks on one host |
| CPU used | 4.07 h (a05 2.57 h, a35 1.49 h); the ceiling was 105 CPU-h |
| failed runs | all 10 end at best cost c\* + 1 (2 vs 1 on 3-SAT n250; 22 vs 21 on #47) |

**Flips per call (`a35`).** The run mean is 12,500 on 207/210 runs. The
three exceptions:
- **#38 s1 and #39 s1** (12,474 and 12,484): the final call was clipped at
  the budget.
- **#40 s2** (10,756 at 3.51 s/call): on that host the 3.5 s limit bound
  on some calls at m = 1088.

**Reproducibility against the pilot** (`analysis/pilot_vs_full_reproducibility.csv`).
Each check pairs the same instance and solver seed, run on different hosts
on different days.

- **Pilot `p40_ls2p5` vs full `a35`.** Where the 12,500-flip limit ends
  every call, these are the same search.
  - **26/30** pairs are bit-identical: same children, same total flips,
    same best-assignment hash.
  - **The 4 exceptions:**
    - #8 (m = 1088), all 3 seeds: the pilot's 2.5 s did not reach 12,500
      flips;
    - #9 seed 3: one pilot call stopped 105 flips short, with the same
      children and the same final assignment.
  - **Conclusion:** the flip-bound arm is deterministic given the seed.
- **Pilot unclipped 0.5 s vs full clipped `a05`.**
  - **0/30** pairs have identical flip counts.
  - **24/30** reach the same final assignment.
  - **29/30** have the same outcome class.
  - **Conclusion:** time-bound calls make the trajectory depend on host
    speed. Per-seed TTT then differs widely: #9 seed 1 took 24 s in the
    pilot and 214 s in the full run. Under `a05`, seeds are random
    replicates, not reproducible ones.

---

## 6. M2 full pool: results

### 6.1 Success and median TTT (`results/m2_full_p40/agg/by_group_config.csv`)

| arm | lower_ext (16 inst, 48 runs) | tier2 (46, 138) | upper_ext (8, 24) | total | median TTT |
|---|---:|---:|---:|---:|---:|
| `a05` | 48 | 130 | 24 | **202/210** | 1.0 s |
| `a35` | 48 | 136 | 24 | **208/210** | 1.6 s |

**Failures by instance** (all other instances are 3/3 on both arms):

| # | family | n | α | c\* | RC2 s | a05 | a35 |
|---|---|---:|---:|---:|---:|---:|---:|
| 9 | k3 | 250 | 4.26 | 1 | 388 | 1/3 | 3/3 |
| 38 | k3 | 250 | 4.26 | 1 | 114 | 1/3 | 2/3 |
| 39 | k3 | 250 | 4.35 | 1 | 324 | 1/3 | 2/3 |
| 47 | k2 | 400 | 2.15 | 21 | 381 | 1/3 | 3/3 |

No instance has 0 successes on either arm, so every ERT is defined. The
zero-success sensitivity analysis is therefore identical to the primary
one.

### 6.2 How hard is the population for the memetic solver?

| measure | count of 70 |
|---|---:|
| all 6 runs (both arms) hit the optimum with the **first** polish call | **28** |
| no run on either arm needed more than one generation (≤ 38 calls) | **55** |
| some run went beyond generation 1 | 15: #7, 8, 9, 16, 31, 33, 36, 37, 38, 39, 41, 43, 46, 47, 48 |
| pre-registered Q2 non-trivial (median TTT ≥ 45 s or success < 3/3), `a05` | 5: #7, 9, 38, 39, 47 |
| same rule, `a35` | 9: #7, 8, 9, 33, 37, 38, 39, 41, 47 |
| any failed run | 4 |

**By family:**
- **3-SAT.** The memetic solver does real work only at n = 250 (α 4.26,
  4.35; c\* = 1), at n = 150 α 4.8, and on one n = 70 instance (#16). All
  14 n = 50 instances (α 8–9, c\* 9–13, RC2 33–847 s) are solved by the
  first child in every run.
- **2-SAT.** Non-trivial work concentrates in n = 400, α 2.0–2.15, plus #31
  (n = 150).

**The pre-registered cell rule (§5.3) applied to the pool.** The rule asks
that at least half a cell's instances be non-trivial and that the RC2
median be ≥ 10 s. It is computed here on pool instances only, not on whole
cells. Only `max3sat_n250_a4.26` and `max3sat_n250_a4.35` pass, plus
`max3sat_n150_a4.8` under `a35` (one instance).

### 6.3 Is the memetic hardness signal reliable? (`summary.json` → `reliability`)

| quantity | value |
|---|---:|
| ρ between arms, instance ERT in seconds (N = 70) | 0.888 (k2 0.869, k3 0.847) |
| ρ between arms, instance ERT in children | 0.889 |
| seed-vs-seed ρ of children-to-target, `a05` (3 pairs) | 0.848 / 0.864 / 0.862 |
| seed-vs-seed ρ, `a35` | 0.786 / 0.778 / 0.840 |
| ICC(1) of log children across 3 seeds, `a05` / `a35` | 0.878 / 0.860 |

These figures are partly inflated by ties: the 28 first-child instances tie
at the floor on every seed. Even so, the memetic difficulty ranking is
reproducible across seeds and across the two LS allowances. A low
ρ(RC2, memetic) therefore cannot be explained by memetic measurement noise.
**RC2's own run-to-run timing noise has not been measured** (§10).

### 6.4 0.5 s vs 3.5 s per call, paired (`analysis/arm_comparison_nontrivial.csv`)

This comparison covers the 15 instances with any run beyond generation 1
or any failure.
- The geometric-mean ratio of ERT, a35/a05, is **0.70 in seconds** and
  **0.72 in flips**.
- Wilcoxon p = 0.60 and 0.64; 8 instances favour `a35` and 7 favour `a05`.
- **The pattern is not uniform:**
  - **`a35` is much better where `a05` fails:**

    | # | ERT ratio a35/a05 |
    |---|---:|
    | 47 | 0.03 |
    | 9 | 0.07 |
    | 39 | 0.26 |
    | 38 | 0.35 |

  - **`a05` is 2–4.4× better (time and flips) on n = 250 instances both
    arms solve 3/3** (#7, #8, #36, #37).
  - **On 2-SAT n = 400, `a35` is mostly better** (#46, #48: ratio
    0.4–0.56).
- **In words:** short time-bound calls are more flip-efficient on average
  but have heavier failure tails. With 3 seeds per instance this is a
  description, not a test.

---

## 7. ρ between RC2 and memetic hardness

The full table is `results/m2_full_p40/analysis/rho_table.csv`: 4 subsets
× 3 x-variables × 10 y-variables (120 rows). The rows that matter are reproduced here.

**Reading guide**
- **Unit:** N counts instances.
- **CIs:**
  - "plain" = unstratified instance bootstrap, percentile;
  - "BW" = Fisher z with the Bonett–Wright SE;
  - the cell-stratified BCa interval is in the CSV. It is too narrow here;
    see §7.6.
- **Partial ρ:** controls for [log n, α, log(1 + c\*)]. Its CI is a
  2,000-rep cell-stratified percentile interval.
- **Sign:** y = ERT, so **positive ρ means instances that are hard for RC2
  are also hard for the memetic solver.**

### 7.1 Pre-registered primary analysis: RC2 `solve_s` vs memetic ERT

| subset | y | N | ρ | plain CI | BW CI | partial ρ (CI) | partial + k |
|---|---|---:|---:|---|---|---|---:|
| pooled | a05 ERT s | 70 | **0.087** | −0.16, 0.33 | −0.15, 0.32 | 0.235 (0.05, 0.38) | 0.337 |
| pooled | a05 ERT children | 70 | 0.092 | −0.16, 0.33 | −0.15, 0.32 | 0.233 | 0.348 |
| pooled | a05 ERT flips | 70 | 0.051 | −0.20, 0.30 | −0.19, 0.28 | 0.165 (−0.01, 0.34) | 0.288 |
| pooled | a35 ERT s | 70 | **0.070** | −0.18, 0.31 | −0.17, 0.30 | 0.193 (0.02, 0.35) | 0.294 |
| pooled | a35 ERT children (= flips) | 70 | 0.051 | −0.20, 0.29 | −0.19, 0.28 | 0.153 (−0.02, 0.30) | 0.313 |
| **k2** | a05 ERT s | 26 | **0.676** | 0.41, 0.84 | 0.35, 0.86 | 0.500 (0.18, 0.69) | — |
| k2 | a05 ERT children | 26 | 0.673 | 0.41, 0.82 | 0.35, 0.85 | 0.484 | — |
| k2 | a35 ERT s | 26 | **0.570** | 0.22, 0.82 | 0.20, 0.80 | 0.397 (0.08, 0.66) | — |
| k2 | a35 ERT children | 26 | 0.493 | 0.14, 0.76 | 0.11, 0.75 | 0.402 (0.08, 0.64) | — |
| **k3** | a05 ERT s | 44 | **−0.092** | −0.39, 0.22 | −0.38, 0.21 | 0.003 (−0.23, 0.24) | — |
| k3 | a05 ERT children | 44 | −0.122 | −0.43, 0.20 | −0.40, 0.18 | 0.052 | — |
| k3 | a35 ERT s | 44 | **−0.050** | −0.37, 0.26 | −0.34, 0.25 | −0.016 (−0.24, 0.21) | — |
| k3 | a35 ERT children | 44 | −0.145 | −0.44, 0.17 | −0.42, 0.16 | 0.131 (−0.07, 0.34) | — |
| tier2 group only | a05 ERT s | 46 | 0.209 | −0.10, 0.48 | −0.09, 0.47 | 0.145 | — |
| tier2 group only | a35 ERT s | 46 | 0.169 | −0.15, 0.45 | −0.13, 0.44 | 0.051 | — |

- **Exclusions:** 0 in every row; there are no zero-success instances.
- **Success rate as y:** ρ(RC2, success) is −0.18 (a05) and −0.05 (a35)
  pooled. Success takes only 2 distinct values (4 instances below 3/3), so
  these numbers carry little information.

### 7.2 Within (k, n) rows (`analysis/within_row_rho.csv`)

**Method.** Within each (k, n) row with ≥ 3 instances, x and y are
replaced by within-row mid-ranks scaled to (0, 1). The result is then
correlated across all rows. This is the closest the pool allows to a
within-cell estimate: it removes n and family, and most of α and c\*.

| scope | y | N | ρ | strat. pct CI | BW CI |
|---|---|---:|---:|---|---|
| all rows | a05 ERT s | 66 | **0.342** | 0.12, 0.54 | 0.10, 0.54 |
| all rows | a05 ERT children | 66 | 0.347 | 0.13, 0.55 | 0.11, 0.55 |
| all rows | a35 ERT s | 66 | 0.323 | 0.11, 0.52 | 0.08, 0.53 |
| all rows | a35 ERT children | 66 | 0.293 | 0.07, 0.50 | 0.05, 0.50 |
| k2 rows | a05 ERT s | 24 | 0.660 | 0.46, 0.82 | 0.31, 0.85 |
| k2 rows | a35 ERT children | 24 | 0.629 | 0.34, 0.83 | 0.27, 0.84 |
| k3 rows | a05 ERT s | 42 | 0.156 | −0.17, 0.46 | −0.16, 0.44 |
| k3 rows | a35 ERT children | 42 | 0.043 | −0.25, 0.35 | −0.26, 0.34 |

**Per row** (ρ, no CI; N ≤ 14):

| row | N | ρ (a05 ERT s) | ρ (a35 ERT s) | notes |
|---|---:|---:|---:|---|
| k2 n400 | 11 | 0.83 | 0.59 | α 2.0–2.3 and c\* 18–23 are nearly fixed, yet the RC2 ranking predicts the memetic ranking |
| k2 n150 | 7 | 0.79 | 0.39 | |
| k2 n100 | 6 | 0.20 | 0.71 | |
| k3 n250 | 8 | 0.38 | 0.26 | c\* = 1 for all |
| k3 n70 | 13 | 0.20 | −0.02 | |
| k3 n100 | 7 | −0.14 | 0.07 | |
| k3 n50 | 14 | (0.14) | (0.39) | **memetic children constant at 1**: the a05/a35 ERT-s values here measure call-length noise, not difficulty |

### 7.3 Which covariates drive each side? (`analysis/covariate_rho.csv`, Spearman)

| target | subset | n | α | m | c\* | RC2 s |
|---|---|---:|---:|---:|---:|---:|
| RC2 solve_s | k2 | 0.22 | −0.16 | 0.30 | −0.01 | — |
| RC2 solve_s | k3 | −0.14 | 0.22 | 0.00 | 0.31 | — |
| RC2 s per oracle call | k2 | 0.44 | −0.38 | 0.46 | −0.25 | 0.96 |
| RC2 s per oracle call | k3 | 0.35 | −0.26 | 0.46 | −0.19 | 0.82 |
| a05 ERT children | k2 | 0.35 | −0.35 | 0.42 | −0.10 | 0.67 |
| a05 ERT children | k3 | **0.82** | −0.81 | 0.74 | **−0.80** | −0.12 |
| a35 ERT children | k3 | **0.80** | −0.78 | 0.75 | **−0.80** | −0.14 |
| a05 ERT children | pooled | 0.69 | −0.59 | 0.71 | −0.13 | 0.09 |

**RC2 decomposed into its two factors, ρ with memetic ERT:**

| x | subset | a05 ERT s | a35 ERT s | a35 ERT children |
|---|---|---:|---:|---:|
| c\* (= number of cores) | k3 | **−0.77** | −0.76 | −0.80 |
| s per oracle call | k3 | **+0.35** (0.03, 0.60) | +0.39 (0.09, 0.64) | +0.33 |
| RC2 total (product) | k3 | −0.09 | −0.05 | −0.15 |
| c\* | k2 | −0.13 | −0.22 | +0.02 |
| s per oracle call | k2 | +0.67 | +0.58 | +0.43 |
| s per oracle call | pooled | +0.16 | +0.22 (−0.03, 0.44) | +0.23 |

### 7.4 Historical comparison: SATLIB uuf250/uuf200, 26 instances (`analysis/uuf_tier2_rho.csv`)

**Setup.** RC2 caps were 900 s and 600 s, and all 26 instances are
certified. c\* = 1 on 24 and 2 on the other 2. There were 5 seeds per
config at 900 s, all with the old unclipped 0.5 s LS cap.

| config | successes | N in ρ | ρ(RC2 s, ERT s) | BW CI |
|---|---:|---:|---:|---|
| `memetic_deeppolish` (pop 40, 12,500 flips / 0.5 s) | 118/130 | 26 | **+0.187** | −0.22, 0.54 |
| `local_multistart_deeppolish` (no EA: uniform random restarts + the same polish) | **124/130** | 26 | +0.139 | −0.26, 0.50 |
| `memetic_base` (pop 60, 700 flips / 0.05 s) | 70/130 | 20 (6 with 0 successes excluded) | −0.256; top-tied −0.021 | −0.63, 0.22 |
| `memetic_pop150` | 94/130 | 24 (2 excluded) | −0.160; top-tied −0.003 | −0.53, 0.26 |

- **The ablation.** The no-EA multistart baseline solves at least as many
  runs as the memetic config with the same polish. That ablation has
  **not** been run on the calibration pool.
- **The constant c\*** forces any ρ through RC2's per-call cost alone; see
  `docs/archive/CORPUS_MSE2016_ASSESSMENT.md` §5.1.

### 7.5 Interpretation

1. **Pooled ρ is near zero, but that is not "no relation".**
   - The pooled estimate (0.05–0.10) averages two families with opposite
     behaviour. 2-SAT has a clearly positive ρ (≈ 0.5–0.7, lower CI bound
     > 0.1 on every metric). 3-SAT has a ρ near zero or slightly negative.
   - Partial ρ goes positive (0.15–0.24, rising to 0.29–0.35 with k), and
     so does within-row ρ (≈ 0.3). Once the gross structure is removed,
     the residual association between the two hardness rankings is
     **positive, not orthogonal**.
2. **In 3-SAT the near-zero ρ comes from the selection window.**
   - The 30–900 s window admits two kinds of 3-SAT instance:
     - small-n, high-α instances where RC2 needs many cores (c\* 9–13).
       WalkSAT solves these in one call;
     - n = 250 threshold instances with c\* = 1. Each SAT call is
       expensive for RC2, and WalkSAT has a needle to find.
   - **The two RC2 cost factors point in opposite directions:**
     - core count: ρ ≈ −0.8 with memetic effort;
     - per-call cost: ρ ≈ +0.35 to +0.43.
   - Their product, RC2 time, has ρ ≈ 0 with memetic effort. This
     supports H2 (memetic difficulty follows n and closeness to α_c, not
     c\*) and H3 (the jointly non-trivial strip is narrow).
   - It also means "orthogonality" in this pool is a property of the
     selection rule, not of the solvers at fixed structure.
3. **In 2-SAT, RC2 time is almost entirely per-call cost.** c\* barely
   varies within a row. The ranking of per-call cost tracks memetic effort
   (ρ ≈ 0.6–0.8), even within n = 400 at nearly fixed α and c\*. This is a
   genuine instance-level co-hardness. Its mechanism is not established:
   instance "glassiness" or plateau structure affecting both solvers is one
   candidate.
4. **Measurement-level caveat specific to this solver.**
   - In 28/70 instances the memetic effort is at its floor (one call), so
     a large part of y is tied. Spearman uses average ranks, but the ties
     still limit resolution.
   - A floor at one call means memetic difficulty is **left-censored**. On
     these instances it is WalkSAT single-run difficulty, and the EA never
     acts.
5. **Strength of evidence.**
   - N = 70 pooled cannot exclude |ρ| = 0.3. By the project's own power
     table (`docs/archive/CORPUS_MSE2016_ASSESSMENT.md` §5.2), a null claim
     excluding |ρ| > 0.3 needs about 44 instances *per reported stratum*,
     with real spread.
   - The 2-SAT positive result rests on N = 26 and is the strongest signal
     in the data.
   - None of these numbers is final, by design (calibration rows).

### 7.6 Notes on the CI methods

- **The cell-stratified bootstrap (the pre-registered primary CI) is too
  narrow on this pool.** 6 of 24 cells hold a single instance and 5 hold
  two. A singleton stratum is resampled as itself, so it contributes no
  variability. In several rows the stratified BCa interval is visibly
  narrower than both the plain bootstrap and Bonett–Wright. For example,
  k3 c\* vs a05 ERT s gives −0.84 to −0.65 stratified against −0.88 to
  −0.58 plain. **The plain and BW intervals are the honest ones here.**
  The stratified BCa stays in the CSV for completeness.
- **BCa with heavy ties.** The bias correction uses the mid-proportion at
  θ̂, and acceleration comes from the jackknife. Rows where y has only 2
  distinct values (success rate) produce many NaN replicates (column
  `bootstrap_nan_reps`) and should be ignored.
- **Partial-ρ CIs are percentile intervals** from a 2,000-rep stratified
  bootstrap, so they are subject to the same narrowing.

---

## 8. What changed in hypotheses H1–H4 (calibration evidence only)

| hypothesis | evidence | status |
|---|---|---|
| H1 | RC2 time rises with c\* and α at fixed n (A1/B1 read-outs). The yield of a (k, n) row is set by d log10(t)/dc\*; 3-SAT n = 150 jumps from c\* = 2 at 15 s to c\* = 3 at 772 s | supported in A1/B1 |
| H2 | memetic effort vs n: ρ ≈ +0.8 in 3-SAT; vs c\*: ρ ≈ −0.8 (via the selection confound); the first-child solve on all n = 50 instances regardless of RC2 time | supported |
| H3 | in 3-SAT only n = 250 (α 4.26/4.35) and n = 150 α 4.8 are non-trivial for both; 2-SAT n = 400 α 2.0–2.15 is borderline | supported; the strip is very narrow |
| H4 | 3-SAT partial ρ ≈ 0 (CI ±0.24). 2-SAT partial ρ ≈ +0.4 to +0.5 (CI excludes 0). Pooled partial ρ ≈ +0.2 | **mixed**: low in 3-SAT, contradicted in 2-SAT |

---

## 9. Threats to validity (to weigh before using any number)

1. **Range restriction** on RC2 time (30–900 s) and on c\* within each
   family. ρ outside the window is unknown.
2. **Selection-induced confounding.** The window links c\* and n
   (ρ = −0.97 in 3-SAT). Partial ρ addresses this only to the extent that
   the linear-in-ranks model is right.
3. **Memetic floor effect.** 28/70 instances are tied at one LS call.
   Effort within a call is not recorded.
4. **Time-based ERT includes call length,** which grows with m under
   `a35`. Prefer children/flips. ρ(m, a35 ERT s) = 0.79 against 0.60 for
   children.
5. **RC2 measured once.** Its timing noise on the cluster is unknown. Any
   ρ is attenuated by RC2 unreliability by an unknown amount.
6. **Instance count.** 70 pooled, 26 and 44 by family, and 24 small cells.
7. **Time-bound LS (`a05`) is host-dependent** (§5). Per-seed outcomes are
   not reproducible, though instance-level aggregates are (between-arm
   ρ 0.89).
8. **Two random families only.** Nothing here speaks to structured,
   weighted or industrial MaxSAT. The MSE-2016 screen found none of those
   certifiable at 1800 s.
9. **Multiple comparisons.** The rho table has 120 rows; only
   §7.1's primary rows were pre-specified.
10. **Pilot provenance** is unverified (`git_sha` null). It is used here
    only for the reproducibility check, not for ρ.

---

## 10. What is missing (ordered by value per cost)

1. **Effort resolution below one LS call.**
   - **What:** record, inside `walksat_polish`, the flip index (and time)
     at which the incumbent first reached the target. The multistart
     runner already has a `flips_in_target_restart` field to reuse.
   - **Why it matters:** this removes the floor on 28/70 instances and
     makes y continuous.
   - **Cost:** code-only, then a cheap re-run. The trivial instances take
     seconds.
2. **Memetic on the 107 certified instances with RC2 < 30 s.**
   - **What:** run 3 seeds × 1–2 arms on them.
   - **Why it matters:** this removes the x-side range restriction and
     gives ρ over the whole certified range.
   - **Cost:** most runs finish in under a second, so well under 1 CPU-h.
3. **No-EA baseline on the calibration pool**
   (`local_multistart_deeppolish`, and the JW-seeded variant, at matched
   polish). Without it, "memetic hardness" cannot be told apart from
   "WalkSAT hardness". On uuf250 the no-EA baseline was at least as good.
4. **RC2 repeatability.** Re-run RC2 on about 15–20 pool instances, 3 times
   each, on the cluster. This gives the reliability needed to bound
   attenuation of ρ, as `CORPUS_CALIBRATION_GOALS.md` §5.2 already
   anticipated.
5. **A second exact solver on the pool,** for example EvalMaxSAT, whose
   oracle driver already exists. Is the 2-SAT co-hardness specific to
   RC2's core-guided search?
6. **M3 proper.**
   - `src/bench/calib_summary.py`: the yield table over all 290 instances
     (completed / censored / not-run counts per cell).
   - The formal ρ/CI table, rendered into `docs/CALIB_A_RESULTS.md` or an
     equivalent.
   - The script added today (`scripts/m2_rho_analysis.py`) covers the ρ
     part for the 70-instance pool only.
7. **The decision for M4 (corpus_v1 cell rules).**
   - Under the pre-registered rule, only the 3-SAT n = 250 cells would be
     selected (plus perhaps 2-SAT n = 400 α 2.0–2.15). That gives a
     1–2-family corpus with c\* nearly constant inside each family. The
     rules or the families need reconsidering before fresh seeds are
     generated.
   - Options: larger 2-SAT n; 3-SAT n ∈ {200, 300} near α_c; MaxCut;
     reweighted twins.
   - The rule must not be tuned toward any ρ (§5.3 of the goals doc).
8. **Uncertified instances (113).** An anytime comparison (memetic best
   cost against the RC2 lower bound at 900 s) would describe the other side
   of the RC2 censoring boundary. ρ is undefined there, but a
   censored-data rank statistic is possible.
9. **Housekeeping.**
   - `results/m2_full_p40/` and the new script are not committed.
   - The calibration log (`docs/CORPUS_CALIBRATION_LOG.md`) has no
     Checkpoint 6 entry for this run.

---

## 11. Files to give an external analyst

All are small CSV/JSON files under `cluster_staging_maxsat/results/`. The
first file plus this document is enough for most questions.

| file | rows | what it is |
|---|---:|---|
| `m2_full_p40/analysis/instance_table.csv` | 70 | **one row per pool instance**: covariates, RC2, and per-arm memetic aggregates (dictionary below) |
| `m2_full_p40/agg/tasks.csv` | 420 | one row per run (instance × arm × seed): class, TTT, wall, cpu, children, flips, host |
| `m2_full_p40/analysis/rho_table.csv` | 120 | every ρ computed (subset × x × y), with all CI variants and partial ρ |
| `m2_full_p40/analysis/within_row_rho.csv` | 48 | per-(k, n)-row ρ and pooled within-row ρ |
| `m2_full_p40/analysis/covariate_rho.csv` | 141 | Spearman of each target against n, α, m, c\*, k, RC2 |
| `m2_full_p40/analysis/rc2_population_290.csv` | 290 | every generated calibration instance: RC2 status, time, c\* or lower bound, in-pool flag |
| `m2_full_p40/analysis/uuf_tier2_instance_table.csv` | 26 | historical SATLIB instances: RC2, plus successes and ERT for 4 configs incl. no-EA |
| `m2_full_p40/analysis/uuf_tier2_rho.csv` | 8 | ρ for the historical set |
| `m2_full_p40/analysis/arm_comparison_nontrivial.csv` | 15 | paired a05 vs a35 on the non-trivial instances |
| `m2_full_p40/analysis/pilot_vs_full_reproducibility.csv` | 60 | same-seed comparison of pilot and full-pool runs |
| `m2_full_p40/analysis/summary.json` | — | integrity counts, reliability, arm comparison, headline ρ rows |
| `m2_full_p40/agg/by_instance_config.csv`, `by_group_config.csv`, `by_config.csv`, `paired_by_instance_seed.csv` | — | the standard M2 aggregates (`scripts/m2_results.py aggregate`) |
| `m2_full_p40/tasks/*.jsonl` | 420 | raw shards (full config, host, Slurm ids, assignment hash) |
| `m2_full_p40/provenance/submit_20261004T114233Z.txt` | — | submission record and file hashes |

**Regenerate everything** from `cluster_staging_maxsat/` in about 40 s:

```bash
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_m2_full_p40.tsv \
    --outdir results/m2_full_p40/tasks --out-dir results/m2_full_p40/agg
python3 scripts/m2_rho_analysis.py
```

The bootstrap seed is fixed (20261004), so reruns are identical.

### `instance_table.csv` columns

| column | meaning |
|---|---|
| `pop_idx` | instance id in the 70-pool (1–70); referenced as #N in this doc |
| `instance`, `instance_sha256`, `batch` | file path, content hash, calib_a or calib_b |
| `cell_id`, `family`, `k`, `n`, `alpha`, `m`, `gen_seed` | generator cell and parameters |
| `c_star` | RC2-certified optimum (unsatisfied clauses) |
| `rc2_solve_s` | RC2 proof time (s), one run, PySAT 1.9.dev3 |
| `rc2_s_per_oracle_call` | `rc2_solve_s / (c_star + 1)`: mean time per SAT-oracle call |
| `rc2_tier`, `analysis_group` | RC2 time band labels: lower_ext 30–60 s, tier2 60–600 s, upper_ext 600–900 s |
| `a05_*` / `a35_*` | memetic arm 0.5 s per call / 3.5 s per call |
| `…_succ` | successes of 3 seeds |
| `…_ttt_s1..s3` | TTT per seed (s), blank = failed at 900 s |
| `…_children_s1..s3` | LS calls used per seed (to target, or until budget) |
| `…_median_ttt_s` | median over 3 seeds, failures = +∞ (blank if undefined) |
| `…_ert_s` | Σ min(wall, 900) over seeds / successes |
| `…_ert_children`, `…_ert_flips` | same with children or flips as the effort unit |
| `…_mean_flips_per_call` | Σ flips / Σ children over the 3 seeds |
| `…_max_children`, `…_max_generations` | maximum over seeds |
| `…_nontrivial_q2` | 1 if success < 3/3 or median TTT ≥ 45 s (pre-registered Q2 rule) |
| `pooled_succ_of_6` | successes over both arms |
| `all6_first_child` | 1 if all 6 runs hit the target with the first LS call |
| `any_run_beyond_gen1` | 1 if any run on either arm used more than 38 LS calls |

### `rho_table.csv` columns

| column | meaning |
|---|---|
| `subset` | pooled / k2 / k3 / tier2_group |
| `x` | `rc2_solve_s`, `c_star` or `rc2_s_per_oracle_call` |
| `y` | `{a05,a35}_{ert_s,ert_children,ert_flips,median_ttt_s,succ}` |
| `version` | `primary`; the zero-success sensitivity rows are omitted because no instance has 0 successes |
| `N`, `excluded_zero_succ`, `n_distinct_y` | sample size, exclusions, distinct y values (a tie indicator) |
| `rho` | the Spearman estimate |
| `ci_bca_strat_*` | cell-stratified BCa interval |
| `ci_pct_strat_*` | cell-stratified percentile interval |
| `ci_pct_plain_*` | plain bootstrap percentile interval |
| `ci_bonett_wright_*` | Fisher z interval with the Bonett–Wright SE |
| `p_value_spearman` | scipy's p-value |
| `partial_rho_logn_alpha_logc` | partial ρ, plus its stratified percentile CI (only for x = RC2 and ERT s/flips) |
| `partial_rho_plus_k` | partial ρ with k added (pooled only) |
| `bootstrap_nan_reps` | replicates with constant x or y |

### Background documents (repository `docs/`)

| document | contents |
|---|---|
| `CORPUS_CALIBRATION_GOALS.md` | questions, hypotheses, pre-registered rules |
| `CORPUS_CALIBRATION_LOG.md` | checkpoints 1–5 |
| `CALIB_A_A1_READOUT.md`, `CALIB_B_B1_READOUT.md`, `CALIB_B_SUMMARY.md` | RC2 calibration |
| `M2_DEEPPOLISH_HANDOUT.md`, `M2_DEEPPOLISH_SUMMARY.md` | the LS time-cap finding |
| `M2_PILOT_READOUT.md`, `M2_FULL_POOL_RUN.md` | M2 pilot and run preparation |
| `archive/TIER2_ABLATION_FAIRNESS_AUDIT.md`, `archive/CORPUS_MSE2016_ASSESSMENT.md` | historical uuf250 results, the power table |

---

## 12. Questions worth putting to an external analyst

1. **Pooling.** Given §7.1–7.3, is there a defensible single pooled ρ for
   this pool? Or should only family-wise and within-row estimates be
   reported? Is a mixed model better? One option: log ERT_children on
   log RC2 per-call, log(1 + c\*), n, α, with family random effects.
2. **Floor effect.** How should the left-censored memetic effort (28/70 at
   one call) be handled before item 1 of §10 exists? Options include a
   Tobit-type or interval-censored rank correlation, or dropping the floor
   instances and reporting the conditional ρ.
3. **The 2-SAT co-hardness** (ρ ≈ 0.8 within n = 400 at nearly fixed α and
   c\*). Which structural instance features could explain it, and which
   are cheap to compute? Candidates: backbone size, number of optimal
   assignments, plateau width, and core-size statistics from RC2.
4. **Corpus selection for M4.**
   - The pre-registered rule selects only 3-SAT n = 250 cells.
   - How should the selection rules or families change, without tuning
     toward ρ, so that the final corpus supports a CI that excludes
     |ρ| > 0.3 within at least two strata?
   - Should the RC2 window be redefined, given that it is the source of
     the c\*–n confound?
5. **RC2 cost decomposition.** Is it legitimate to report ρ for "per-call
   cost" and "core count" separately, given that per-call cost is derived
   as t/(c\* + 1)? Would logging per-call times from RC2 be the better
   route?
6. **Arm choice.** Given §6.4 (0.5 s calls: more flip-efficient but with
   heavier failure tails; 3.5 s calls: deterministic per seed), which arm
   should be the memetic configuration of record for M5? Or should both be
   kept?
