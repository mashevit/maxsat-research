# HP-1 calibration plan: size-aware hyperparameters for the memetic solver

**Date:** 2026-10-11. **Decision §0: continuous flips per variable with floor 12,500 (no categories).** **Status: plan only. Nothing has been run or prepared
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
