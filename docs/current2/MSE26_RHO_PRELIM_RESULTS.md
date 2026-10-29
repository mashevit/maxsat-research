# ρ on MSE 2026: preliminary statistics (batch 3c, before the error fixes)

**Created:** 2026-10-29. **Status: preliminary.** These numbers are from batch 3c
as it came back, *before* the fixes and reruns listed in `MSE26_3C_RUN.md` §7
(heap crash on 2 small instances, `glucose_timeout` classifier, 5 Slurm wall
kills). The final readout replaces this document once those are done; this
one stays as the record of the state on 2026-10-29.

**§10 (added later on 2026-10-29):** the complementarity conclusion with
evidence (not pre-registered; N-2026-10-29-b).

**What is computed.** The pre-registered analysis (`MSE26_RHO_PREREG.md`,
BINDING r4, text of `f8a3354`), unchanged, run by `scripts/mse26_rho.py`
(commit `0e96589`) through the wrapper `scripts/mse26_rho_errors.py`
(`7743b06`) under two treatments of the errored runs (user, 2026-10-29:
"compute the statistics with 1 option all the errors failed on memetic, and
other option - remove them from computation").

**Where the numbers come from** (strong tree `cluster_staging_maxsat_strong/`):
- `results/mse26_memetic/tasks/` — 2,845 shards of 2,856 (archive
  `mse26_3c_back.tgz`, sha256 `82efc7d0…88be2`), `sacct_3c.tsv`, logs;
- `results/mse26_rho_fail/` and `results/mse26_rho_exclude/` —
  `report.md`, `summary.json`, `instances.csv` (x, y and flags per
  instance). Not committed.

**Reading the cells.** ρ = Spearman with midranks (∞ ties share one midrank);
[lo, hi] = 95 % BCa bootstrap over instances, B = 10,000, seed 20261029.
x = EvalMaxSAT CPU seconds to prove the optimum in its published 2026 run
(timeout = ∞); y = memetic ERT over 3 seeds on the process CPU clock, budget
1,800 s (no success = ∞). "∞ x / y / both" = instances with only x infinite /
only y infinite / both infinite.

---

## 1. The errored runs and the two treatments

| group (`MSE26_3C_RUN.md` §7) | runs | what | `fail` | `exclude` |
|---|---:|---|---|---|
| A heap crash | 6 | 2 tiny instances, all 3 seeds, no record | failure at the budget | instance out |
| B `glucose_timeout` | 107 | no feasible start in 1,800 s (38 instances) | failure at the budget | instance out |
| D Slurm wall kill | 5 | overran, no record | failure at the budget | instance out |
| C watchdog record | 11 | overran budget + 300 s | failure (pre-registered) | failure (pre-registered) |

`exclude` is `mse26_rho.py` as written: an instance with any such run is
incomplete and leaves every analysis. That removes **44 instances**: 40
proved by EvalMaxSAT, 4 EvalMaxSAT timeouts; 34 weighted, 10 unweighted;
families job-shop-scheduling 13, shifted-rosenbrock-function 9,
shifted-sphere 4, shifted-schwefel 4, parametric-role-based-access-control-
maintenance 3, security-weakness-witnesses 3, kbtree 2, planning-bnn 2,
traveling-salesman 2, quadratic-assignment 1,
resource-constrained-project-scheduling 1. 39 of the 44 lie in the
(30, 3600] s window.

## 2. Population

| | count |
|---|---:|
| instances with a proven optimum (targets) | 947 |
| primary population (EvalMaxSAT proved or timed out) | 922 |
| excluded from primary: EvalMaxSAT memout / crash | 17 / 8 |
| primary and complete, `fail` | 922 |
| primary and complete, `exclude` | 878 |

## 3. Primary and sensitivity analyses

| analysis | `fail`: ρ [95 % CI] | N | ∞ x / y / both | `exclude`: ρ [95 % CI] | N | ∞ x / y / both |
|---|---|---:|---|---|---:|---|
| **primary: ERT, pooled** | **+0.639 [+0.590, +0.682]** | 922 | 43 / 263 / 87 | **+0.635 [+0.585, +0.679]** | 878 | 43 / 225 / 83 |
| 1 window (30, 3600] s, both uncensored | +0.212 [+0.065, +0.351] | 183 | 0 / 0 / 0 | +0.200 [+0.052, +0.339] | 181 | 0 / 0 / 0 |
| 2 x = EvalMaxSAT wall time | +0.639 [+0.590, +0.682] | 922 | 43 / 263 / 87 | +0.635 [+0.585, +0.679] | 878 | 43 / 225 / 83 |
| 3 flip-level effort | +0.639 [+0.590, +0.682] | 922 | 43 / 263 / 87 | +0.635 [+0.585, +0.679] | 878 | 43 / 225 / 83 |
| 4 memetic budget 900 s | +0.640 [+0.592, +0.683] | 922 | 38 / 290 / 92 | +0.636 [+0.587, +0.680] | 878 | 38 / 251 / 88 |
| 5 family-stratified bootstrap | +0.639 [+0.601, +0.673] | 922 | 43 / 263 / 87 | +0.635 [+0.598, +0.669] | 878 | 43 / 225 / 83 |
| 6 partial ρ on log n_vars, log n_clauses | +0.571 [+0.519, +0.620] | 922 | 43 / 263 / 87 | +0.572 [+0.520, +0.620] | 878 | 43 / 225 / 83 |
| 7 PAR2, all proven-optimum instances | +0.636 [+0.589, +0.678] | 947 | 0 / 0 / 0 | +0.634 [+0.587, +0.679] | 903 | 0 / 0 / 0 |

Interpretation rule (prereg §7): every row is a **positive association**
(CI above 0) under both treatments. CI half-width of the primary: 0.046
(`fail`), 0.047 (`exclude`), below 0.15, so **D1 (seeds 4–5) is not
triggered**.

**The window (sensitivity 1) in detail.** The window is the instances
EvalMaxSAT proved in more than 30 s and at most 3,600 s of CPU; the analysis
also requires y finite (at least one memetic success in 3 seeds):

| | window instances | memetic reached (in ρ) | memetic never reached (left out) | ρ |
|---|---:|---:|---:|---|
| `fail` | 391 | 183 | 208 | +0.212 [+0.065, +0.351] |
| `exclude` | 352 | 181 | 171 | +0.200 [+0.052, +0.339] |

**[inference]** Among instances that are moderately to very hard for
EvalMaxSAT and that the memetic also solves, the monotone association is
weak (~ +0.2, CI just above 0). The pooled +0.64 is carried mostly by the
coarse structure: EvalMaxSAT-easy instances (≤ 30 s) that the memetic also
reaches fast, and the instances that one or both never solve (∞ ranks).

## 4. Per track (x = EvalMaxSAT)

| track | `fail`: ρ [95 % CI] | N | ∞ x / y / both | `exclude`: ρ [95 % CI] | N | ∞ x / y / both |
|---|---|---:|---|---|---:|---|
| unweighted | +0.621 [+0.544, +0.684] | 464 | 27 / 119 / 33 | +0.623 [+0.549, +0.686] | 454 | 27 / 112 / 32 |
| weighted | +0.659 [+0.595, +0.715] | 458 | 16 / 144 / 54 | +0.650 [+0.582, +0.709] | 424 | 16 / 113 / 51 |

## 5. Complementarity (primary population)

"Reached" = at least one memetic run reached the optimum within 1,800 s;
"proved" = EvalMaxSAT proved it within 3,600 s.

| | `fail` | `exclude` |
|---|---:|---:|
| EvalMaxSAT proved, memetic reached | 529 | 527 |
| EvalMaxSAT proved, memetic not | 263 | 225 |
| EvalMaxSAT not, memetic reached | 43 | 43 |
| neither | 87 | 83 |

**Off-diagonal families (`fail`):**

- **EvalMaxSAT proved, memetic not** (263): asp-optimization 29, drmx-cryptogen 20, security-weakness-witnesses 16, maximum-colorful-subtree 15, job-shop-scheduling 13, two-echelon-vehicle-routing 13, planning-hplus 13, shifted-sphere 10, parametric-role-based-access-control-maintenance 9, shifted-rosenbrock-function 8, phylogenetic-trees 8, iam-privilege-escalation-repair 7, shifted-schwefel 6, traveling-salesman 6, counterfactual-explanations 5, judgment-aggregation 5, capacitated-vehicle-routing 5, rna-alignment 5, approximately-propagation-complete 4, frb 4, coalition-structure-generation 4, interpretable-rule-based-classifiers 4, circuit-debugging 4, haplotype-assembly 3, maximum-probability-minimum-cut-set 3, open-shop-scheduling 3, network-community-structure 3, inconsistency-measurement 3, program-disambiguation 2, generalized-hypertree-width 2, bio-repair 2, quantum-circuit 2, oblique-decision-trees 2, xai-mindset 2, single-machine-scheduling 2, logistics-routing 2, extension-enforcement 2, quadratic-assignment 2, tpr 2, railway-timetabling 1, single-cell-dna-sequencing 1, treewidth-computation 1, multidimensional-knapsack 1, role-based-access-control-user-authorization-query 1, packup 1, planning-bnn 1, security-critical-cyber-physical-components 1, minimum-fill-in 1, resource-constrained-project-scheduling 1, kbtree 1, switching-activity-maximization 1, SeanSafarpour 1
- **EvalMaxSAT not, memetic reached** (43): minimizing-pentagons 7, single-machine-scheduling 7, judgment-aggregation 5, argumentation-framework-synthesis 4, network-community-structure 3, pareto-optimal-interpretation-synthesis 3, role-based-access-control-user-authorization-query 3, ihs-pathological 2, switching-activity-maximization 1, counterfactual-explanations 1, aes 1, oblique-decision-trees 1, extension-enforcement 1, optimizing-bdds 1, kbtree 1, decision-trees 1, planning-hplus 1

**Maps: counts of instances by x band (rows) and y band (columns).**

`fail`, unweighted:

| x (EvalMaxSAT s) \ y (memetic ERT s) | <=10 | (10,300] | (300,5400] | inf |
|---|---|---|---|---|
| <=1 | 72 | 4 | 5 | 2 |
| (1,30] | 40 | 25 | 30 | 26 |
| (30,300] | 4 | 36 | 27 | 40 |
| (300,3600] | 2 | 8 | 32 | 51 |
| inf | 3 | 6 | 18 | 33 |

`fail`, weighted:

| x (EvalMaxSAT s) \ y (memetic ERT s) | <=10 | (10,300] | (300,5400] | inf |
|---|---|---|---|---|
| <=1 | 62 | 18 | 5 | 3 |
| (1,30] | 20 | 32 | 33 | 24 |
| (30,300] | 9 | 11 | 26 | 39 |
| (300,3600] | 5 | 13 | 10 | 78 |
| inf | 3 | 4 | 9 | 54 |

`exclude`, unweighted:

| x (EvalMaxSAT s) \ y (memetic ERT s) | <=10 | (10,300] | (300,5400] | inf |
|---|---|---|---|---|
| <=1 | 72 | 4 | 5 | 2 |
| (1,30] | 40 | 25 | 30 | 25 |
| (30,300] | 4 | 36 | 27 | 40 |
| (300,3600] | 2 | 8 | 30 | 45 |
| inf | 3 | 6 | 18 | 32 |

`exclude`, weighted:

| x (EvalMaxSAT s) \ y (memetic ERT s) | <=10 | (10,300] | (300,5400] | inf |
|---|---|---|---|---|
| <=1 | 62 | 18 | 5 | 3 |
| (1,30] | 20 | 32 | 33 | 24 |
| (30,300] | 9 | 11 | 26 | 32 |
| (300,3600] | 5 | 13 | 10 | 54 |
| inf | 3 | 4 | 9 | 51 |

**Effort floor:** the share of memetic runs that reached the optimum within
the first polish call (`calls_to_target` ≤ 1), by EvalMaxSAT band.

| x band | fail: floor runs / runs (share) | exclude: floor runs / runs (share) |
|---|---|---|
| <=1 | 320 / 513 (0.624) | 320 / 513 (0.624) |
| (1,30] | 170 / 690 (0.246) | 170 / 687 (0.247) |
| (30,300] | 73 / 576 (0.127) | 73 / 555 (0.132) |
| (300,3600] | 48 / 597 (0.080) | 46 / 501 (0.092) |
| inf | 12 / 390 (0.031) | 12 / 378 (0.032) |

## 6. Per family (families with ≥ 10 primary instances; x = EvalMaxSAT)

"n/a" = ρ not computable (all y infinite, or all x infinite, so no ranks
vary); "[CI n/a]" = the bootstrap interval could not be formed.

| family | fail: ρ [95 % CI] | N | ∞ x / y / both | exclude: ρ [95 % CI] | N |
|---|---|---:|---|---|---:|
| argumentation-framework-synthesis | +0.309 [CI n/a] | 10 | 4 / 0 / 5 | +0.309 [CI n/a] | 10 |
| asp-optimization | +0.037 [-0.172, +0.299] | 44 | 0 / 29 / 12 | +0.037 [-0.172, +0.299] | 44 |
| balanced-classification-rules | +0.512 [-0.076, +0.821] | 14 | 0 / 0 / 0 | +0.512 [-0.076, +0.821] | 14 |
| bio-repair | -0.334 [-0.862, +0.518] | 10 | 0 / 2 / 0 | -0.334 [-0.862, +0.518] | 10 |
| coalition-structure-generation | +0.267 [-0.330, +0.756] | 15 | 0 / 4 / 0 | +0.267 [-0.330, +0.756] | 15 |
| consisteny-query-answering | +0.952 [+0.647, +1.000] | 10 | 0 / 0 / 0 | +0.952 [+0.647, +1.000] | 10 |
| counterfactual-explanations | +0.672 [+0.416, +0.821] | 25 | 1 / 5 / 5 | +0.672 [+0.416, +0.821] | 25 |
| drmx-cryptogen | n/a (N 20) | 20 | 0 / 20 / 0 | n/a (N 20) | 20 |
| graph-coloring | +0.622 [-0.135, +0.925] | 12 | 0 / 0 / 0 | +0.622 [-0.135, +0.925] | 12 |
| iam-privilege-escalation-repair | +0.691 [+0.193, +0.870] | 14 | 0 / 7 / 1 | +0.691 [+0.193, +0.870] | 14 |
| interpretable-rule-based-classifiers | +0.892 [+0.698, +0.975] | 17 | 0 / 4 / 0 | +0.892 [+0.698, +0.975] | 17 |
| job-shop-scheduling | +0.575 [CI n/a] | 16 | 0 / 13 / 1 | — (N < 10) | — |
| judgment-aggregation | +0.129 [-0.263, +0.544] | 26 | 5 / 5 / 12 | +0.129 [-0.263, +0.544] | 26 |
| lights-out | +0.852 [+0.665, +0.943] | 25 | 0 / 0 / 0 | +0.852 [+0.665, +0.943] | 25 |
| max-realizability-power-distribution-full | +0.903 [+0.547, +1.000] | 10 | 0 / 0 / 0 | +0.903 [+0.547, +1.000] | 10 |
| max-realizability-power-distribution-sparse | +0.927 [+0.702, +1.000] | 10 | 0 / 0 / 0 | +0.927 [+0.702, +1.000] | 10 |
| maximum-colorful-subtree | +0.276 [CI n/a] | 17 | 0 / 15 / 0 | +0.276 [CI n/a] | 17 |
| maximum-probability-minimum-cut-set | +0.781 [+0.478, +0.943] | 15 | 0 / 3 / 0 | +0.781 [+0.478, +0.943] | 15 |
| minimizing-pentagons | n/a (N 15) | 15 | 7 / 0 / 8 | n/a (N 15) | 15 |
| multidimensional-knapsack | +0.692 [+0.083, +0.942] | 20 | 0 / 1 / 0 | +0.692 [+0.083, +0.942] | 20 |
| network-community-structure | +0.590 [+0.208, +0.806] | 25 | 3 / 3 / 4 | +0.590 [+0.208, +0.806] | 25 |
| oblique-decision-trees | +0.879 [+0.695, +0.973] | 20 | 1 / 2 / 1 | +0.879 [+0.695, +0.973] | 20 |
| open-shop-scheduling | +0.453 [-0.183, +0.808] | 20 | 0 / 3 / 0 | +0.453 [-0.183, +0.808] | 20 |
| parametric-role-based-access-control-maintenance | +0.276 [-0.316, +0.764] | 19 | 0 / 9 / 0 | +0.269 [-0.421, +0.779] | 16 |
| pareto-optimal-interpretation-synthesis | +0.778 [+0.362, +0.936] | 15 | 3 / 0 / 0 | +0.778 [+0.362, +0.936] | 15 |
| phylogenetic-trees | +0.564 [+0.053, +0.849] | 15 | 0 / 8 / 2 | +0.564 [+0.053, +0.849] | 15 |
| planning-bnn | +0.961 [+0.851, +0.998] | 18 | 0 / 1 / 2 | +0.959 [+0.753, +0.997] | 16 |
| planning-hplus | +0.497 [-0.278, +0.813] | 21 | 1 / 13 / 1 | +0.497 [-0.278, +0.813] | 21 |
| program-disambiguation | +0.849 [+0.526, +0.978] | 15 | 0 / 2 / 0 | +0.849 [+0.526, +0.978] | 15 |
| quantum-circuit | +0.223 [-0.344, +0.721] | 15 | 0 / 2 / 0 | +0.223 [-0.344, +0.721] | 15 |
| rna-alignment | +0.729 [+0.197, +0.909] | 13 | 0 / 5 / 0 | +0.729 [+0.197, +0.909] | 13 |
| role-based-access-control-user-authorization-query | +0.734 [+0.523, +0.875] | 24 | 3 / 1 / 0 | +0.734 [+0.523, +0.875] | 24 |
| security-critical-cyber-physical-components | +0.879 [+0.231, +1.000] | 10 | 0 / 1 / 0 | +0.879 [+0.231, +1.000] | 10 |
| security-weakness-witnesses | +0.836 [+0.764, +0.922] | 30 | 0 / 16 / 0 | +0.835 [+0.743, +0.924] | 27 |
| shifted-rosenbrock-function | n/a (N 10) | 10 | 0 / 8 / 2 | — (N < 10) | — |
| shifted-sphere | n/a (N 10) | 10 | 0 / 10 / 0 | — (N < 10) | — |
| single-machine-scheduling | -0.330 [-0.743, +0.370] | 13 | 7 / 2 / 2 | -0.330 [-0.743, +0.370] | 13 |
| two-echelon-vehicle-routing | +0.243 [-0.173, +0.656] | 19 | 0 / 13 / 3 | +0.243 [-0.173, +0.656] | 19 |
| visibly-pushdown-automata | +0.855 [+0.152, +1.000] | 10 | 0 / 0 / 0 | +0.855 [+0.152, +1.000] | 10 |

## 7. Per published solver (x = that solver's single published run)

Sorted by pooled ρ (`fail`). "x excluded" = that solver's memouts, crashes
and wrong answers on these instances (left out, prereg §4).

| solver | track | fail: ρ [95 % CI] | N | ∞ x / y / both | x excluded | exclude: ρ [95 % CI] | N |
|---|---|---|---:|---|---|---|---:|
| CPMpy_ORTools | unweighted | +0.714 [+0.638, +0.773] | 347 | 59 / 17 / 75 | crash 22, memout 108 | +0.712 [+0.635, +0.773] | 342 |
| CPMpy_ORTools | weighted | +0.658 [+0.588, +0.716] | 402 | 39 / 64 / 99 | memout 60, crash 8 | +0.656 [+0.586, +0.715] | 400 |
| CPMpy_ORTools | pooled | +0.676 [+0.624, +0.720] | 749 | 98 / 81 / 174 | crash 30, memout 168 | +0.673 [+0.622, +0.720] | 742 |
| WMaxCDCL2026 | unweighted | +0.623 [+0.554, +0.684] | 473 | 23 / 96 / 59 | crash 2, memout 2 | +0.637 [+0.568, +0.698] | 463 |
| WMaxCDCL2026 | weighted | +0.696 [+0.638, +0.744] | 469 | 2 / 157 / 49 | crash 1 | +0.674 [+0.611, +0.726] | 436 |
| WMaxCDCL2026 | pooled | +0.649 [+0.605, +0.690] | 942 | 25 / 253 / 108 | crash 3, memout 2 | +0.644 [+0.598, +0.686] | 899 |
| UWrMaxSAT2026 | unweighted | +0.627 [+0.556, +0.688] | 474 | 22 / 129 / 28 | crash 3 | +0.632 [+0.561, +0.694] | 464 |
| UWrMaxSAT2026 | weighted | +0.680 [+0.620, +0.732] | 470 | 4 / 197 / 10 | — | +0.670 [+0.608, +0.725] | 436 |
| UWrMaxSAT2026 | pooled | +0.646 [+0.600, +0.687] | 944 | 26 / 326 / 38 | crash 3 | +0.644 [+0.597, +0.687] | 900 |
| MaxCDCL2026 | unweighted | +0.640 [+0.571, +0.700] | 477 | 21 / 102 / 55 | — | +0.649 [+0.581, +0.706] | 467 |
| MaxHSScipExact | unweighted | +0.606 [+0.531, +0.670] | 457 | 58 / 92 / 59 | crash 18, memout 2 | +0.613 [+0.539, +0.676] | 447 |
| MaxHSScipExact | weighted | +0.684 [+0.622, +0.734] | 457 | 19 / 134 / 70 | crash 13 | +0.684 [+0.624, +0.738] | 423 |
| MaxHSScipExact | pooled | +0.639 [+0.592, +0.682] | 914 | 77 / 226 / 129 | crash 31, memout 2 | +0.643 [+0.594, +0.686] | 870 |
| EvalMaxSAT | unweighted | +0.621 [+0.544, +0.684] | 464 | 27 / 119 / 33 | crash 5, memout 8 | +0.623 [+0.549, +0.686] | 454 |
| EvalMaxSAT | weighted | +0.659 [+0.595, +0.715] | 458 | 16 / 144 / 54 | crash 3, memout 9 | +0.650 [+0.582, +0.709] | 424 |
| EvalMaxSAT | pooled | +0.639 [+0.590, +0.682] | 922 | 43 / 263 / 87 | crash 8, memout 17 | +0.635 [+0.585, +0.679] | 878 |
| CoreForge | unweighted | +0.634 [+0.563, +0.694] | 472 | 50 / 90 / 65 | crash 4, memout 1 | +0.642 [+0.572, +0.701] | 462 |
| MaxHS | unweighted | +0.572 [+0.493, +0.638] | 471 | 56 / 114 / 41 | crash 5, memout 1 | +0.584 [+0.510, +0.652] | 461 |
| MaxHS | weighted | +0.693 [+0.632, +0.742] | 460 | 12 / 151 / 55 | crash 10 | +0.692 [+0.633, +0.744] | 426 |
| MaxHS | pooled | +0.626 [+0.579, +0.669] | 931 | 68 / 265 / 96 | crash 15, memout 1 | +0.632 [+0.583, +0.675] | 887 |
| UWrMaxSatMaxCDCL | unweighted | +0.618 [+0.548, +0.680] | 472 | 16 / 123 / 33 | crash 2, memout 3 | +0.623 [+0.553, +0.685] | 463 |
| WMaxCDCL2026S6O3 | unweighted | +0.581 [+0.505, +0.645] | 474 | 17 / 116 / 40 | memout 3 | +0.596 [+0.523, +0.662] | 464 |
| WMaxCDCL2026S6O3 | weighted | +0.661 [+0.598, +0.716] | 442 | 2 / 160 / 30 | crash 28 | +0.646 [+0.580, +0.705] | 408 |
| WMaxCDCL2026S6O3 | pooled | +0.614 [+0.566, +0.659] | 916 | 19 / 276 / 70 | crash 28, memout 3 | +0.614 [+0.563, +0.659] | 872 |
| MaxCDCL2026S2O3 | unweighted | +0.587 [+0.511, +0.651] | 465 | 14 / 119 / 36 | crash 12 | +0.603 [+0.532, +0.667] | 455 |
| CoreForgeILPLA | unweighted | +0.573 [+0.503, +0.638] | 473 | 45 / 99 / 58 | crash 1, memout 3 | +0.588 [+0.518, +0.653] | 463 |
| CoreForgeILP | unweighted | +0.561 [+0.487, +0.626] | 472 | 42 / 98 / 58 | crash 2, memout 3 | +0.576 [+0.504, +0.641] | 462 |
| MaxCDCL2026S2 | unweighted | +0.551 [+0.475, +0.618] | 477 | 19 / 106 / 51 | — | +0.562 [+0.488, +0.628] | 467 |
| EvalMaxRes | unweighted | +0.543 [+0.468, +0.607] | 476 | 30 / 114 / 42 | memout 1 | +0.554 [+0.481, +0.619] | 466 |
| EvalMaxRes | weighted | +0.538 [+0.463, +0.603] | 467 | 6 / 178 / 27 | memout 3 | +0.537 [+0.460, +0.603] | 433 |
| EvalMaxRes | pooled | +0.534 [+0.483, +0.580] | 943 | 36 / 292 / 69 | memout 4 | +0.540 [+0.488, +0.588] | 899 |
| COGS | unweighted | +0.526 [+0.454, +0.594] | 477 | 31 / 114 / 43 | — | +0.541 [+0.466, +0.608] | 467 |
| COGS | weighted | +0.521 [+0.449, +0.584] | 467 | 16 / 126 / 78 | crash 2, wrong 1 | +0.480 [+0.401, +0.550] | 433 |
| COGS | pooled | +0.524 [+0.472, +0.570] | 944 | 47 / 240 / 121 | crash 2, wrong 1 | +0.513 [+0.459, +0.561] | 900 |
| EvalMaxSATSCIP | unweighted | +0.535 [+0.454, +0.603] | 462 | 23 / 119 / 30 | memout 11, crash 4 | +0.550 [+0.471, +0.617] | 452 |
| EvalMaxSATSCIP | weighted | +0.490 [+0.408, +0.563] | 432 | 9 / 158 / 32 | crash 30, memout 8 | +0.474 [+0.387, +0.551] | 398 |
| EvalMaxSATSCIP | pooled | +0.509 [+0.455, +0.562] | 894 | 32 / 277 / 62 | crash 34, memout 19 | +0.511 [+0.453, +0.563] | 850 |
| WMaxCDCL2026S6 | unweighted | +0.532 [+0.456, +0.601] | 474 | 20 / 100 / 56 | crash 1, memout 2 | +0.551 [+0.475, +0.618] | 464 |
| WMaxCDCL2026S6 | weighted | +0.453 [+0.376, +0.527] | 469 | 2 / 175 / 31 | crash 1 | +0.413 [+0.328, +0.494] | 436 |
| WMaxCDCL2026S6 | pooled | +0.490 [+0.436, +0.541] | 943 | 22 / 275 / 87 | crash 2, memout 2 | +0.483 [+0.428, +0.535] | 900 |
| CASHWMaxSATInc | unweighted | +0.459 [+0.374, +0.532] | 476 | 29 / 115 / 41 | memout 1 | +0.478 [+0.394, +0.554] | 466 |
| CASHWMaxSATInc | weighted | +0.471 [+0.389, +0.543] | 470 | 11 / 144 / 63 | — | +0.445 [+0.360, +0.526] | 436 |
| CASHWMaxSATInc | pooled | +0.465 [+0.408, +0.519] | 946 | 40 / 259 / 104 | memout 1 | +0.462 [+0.403, +0.517] | 902 |
| CASHWMaxSATGoal | unweighted | +0.456 [+0.371, +0.530] | 476 | 29 / 115 / 41 | memout 1 | +0.476 [+0.391, +0.552] | 466 |
| CASHWMaxSATGoal | weighted | +0.471 [+0.389, +0.544] | 470 | 10 / 145 / 62 | — | +0.443 [+0.359, +0.525] | 436 |
| CASHWMaxSATGoal | pooled | +0.465 [+0.408, +0.519] | 946 | 39 / 260 / 103 | memout 1 | +0.461 [+0.402, +0.516] | 902 |
| CASHWMaxSAT | unweighted | +0.459 [+0.374, +0.533] | 476 | 26 / 120 / 36 | memout 1 | +0.477 [+0.394, +0.552] | 466 |
| CASHWMaxSAT | weighted | +0.455 [+0.372, +0.530] | 470 | 13 / 144 / 63 | — | +0.433 [+0.348, +0.515] | 436 |
| CASHWMaxSAT | pooled | +0.459 [+0.401, +0.513] | 946 | 39 / 264 / 99 | memout 1 | +0.457 [+0.398, +0.512] | 902 |
| CPMpy_HiGHS | unweighted | +0.495 [+0.411, +0.571] | 458 | 135 / 40 / 108 | memout 18, crash 1 | +0.509 [+0.426, +0.583] | 449 |
| CPMpy_HiGHS | weighted | +0.331 [+0.238, +0.420] | 455 | 117 / 80 / 122 | crash 2, memout 13 | +0.299 [+0.197, +0.391] | 424 |
| CPMpy_HiGHS | pooled | +0.418 [+0.356, +0.477] | 913 | 252 / 120 / 230 | crash 3, memout 31 | +0.410 [+0.346, +0.471] | 873 |

## 8. Reproduce

```bash
cd cluster_staging_maxsat_strong
P=~/miniforge3/envs/maxsat/bin/python      # numpy + scipy (the ~/.venvs/maxsat venv has no numpy)
$P scripts/mse26_rho_errors.py --errors fail    --outdir results/mse26_memetic/tasks   # ~6 min
$P scripts/mse26_rho_errors.py --errors exclude --outdir results/mse26_memetic/tasks   # ~6 min
```

## 9. Still open before the final readout

1. `m2_results.py`: classify `glucose_timeout` as a failure (decides the 38
   instances under the plain script).
2. Heap crash (group A): reproduce on the two instances, fix, rerun 6 tasks.
3. Group D: rerun 5 tasks with a longer `--time` (`TIME=` in `submit_mse26.sh`).
4. Optional: the deadline overrun on big instances (groups C, D).

## 10. Complementarity: research conclusion and evidence (added 2026-10-29, later)

**Not pre-registered.** The pre-registration fixes ρ and the §5 counts. The
tests and intervals below were added afterwards, at the user's request.
Numbers come from `scripts/mse26_complementarity.py` (strong tree), which
reads the two `instances.csv` and the published 2026 runs. Population = the
§5 primary population: 922 instances under `fail` (errored runs count as
memetic failures) and 878 under `exclude` (instances with errored runs
removed).

### 10.1 Conclusion

1. **The memetic reaches the optimum but does not prove it. Even so, its
   hardness ordering agrees with EvalMaxSAT's proof times.** The memetic is
   given the proven optimum as its target, stops when it reaches that cost,
   and certifies nothing. EvalMaxSAT has to find the optimum *and* prove it.
   The two solvers do different tasks, yet instances that take EvalMaxSAT
   long to prove also take the memetic long to reach:
   - primary ρ = **+0.639** [+0.590, +0.682] (`fail`) and **+0.635**
     [+0.585, +0.679] (`exclude`);
   - every one of the 7 sensitivities is positive (§3), and so are both
     tracks (§4);
   - **with size held fixed**, the partial ρ on log variables and log clauses
     is still +0.57 (§3, sensitivity 6), so this is not just "big instances
     are hard for both".

   The limit (§3): among instances EvalMaxSAT proves in (30, 3600] s *and* the
   memetic reaches, ρ is only ≈ +0.2. The agreement is strong at the coarse
   level (easy vs hard vs unsolved) and weak at the fine level.
2. **The memetic's reach falls steadily as EvalMaxSAT time grows** (10.3). On
   instances EvalMaxSAT proves in ≤ 1 s, the memetic reaches 97 %; on those
   that take 300–3,600 s, only 35 % (`fail`) or 41 % (`exclude`). The trend
   test gives p ≈ 10⁻⁴⁰ / 10⁻³². This is the same agreement as in point 1,
   seen as solve rates rather than ranks.
3. **The two solvers are partly complementary, and lopsided toward
   EvalMaxSAT.**
   - The memetic reaches the optimum on **43 instances that EvalMaxSAT
     cannot prove in 3,600 s**: 4.7 % of the population, a third of
     EvalMaxSAT's timeouts.
   - EvalMaxSAT proves about **six times more** instances that the memetic
     never reaches (263 / 225).
   - The 43 do not depend on the error treatment.
   - Against all the published 2026 solvers, the memetic adds speed on some
     instances, not instances that no solver handled (10.4, point 6).

### 10.2 How "EvalMaxSAT 85.9 %" and "EvalMaxSAT or memetic 90.6 %" fit together

Each instance lands in exactly one of four cells (`fail`, N = 922):

| | memetic reached | memetic did not reach | row total |
|---|---:|---:|---:|
| **EvalMaxSAT proved** | 529 (both) | 263 (only EvalMaxSAT) | **792** |
| **EvalMaxSAT did not prove** | 43 (only memetic) | 87 (neither) | 130 |
| column total | 572 | 350 | 922 |

- **"Solved by EvalMaxSAT" = 85.9 %** is the whole top row: 529 + 263 = 792,
  and 792 / 922 = 85.9 %. It counts every instance EvalMaxSAT proved,
  *whether or not the memetic also reached it*. It does **not** mean "solved
  by EvalMaxSAT and not by the memetic". That narrower count is the single
  cell "only EvalMaxSAT": 263 / 922 = 28.5 %.
- **"Solved by EvalMaxSAT or the memetic" = 90.6 %** is everything except
  "neither": 529 + 263 + 43 = 835, and 835 / 922 = 90.6 %. Equivalently, the
  top row plus the one cell the memetic adds: 792 + 43.
- These two percentages are **nested, not disjoint**. The 90.6 % *contains*
  the 85.9 %, so they never have to add up to 100 %. The gap,
  90.6 − 85.9 = 4.7 points, is exactly the 43 instances only the memetic
  reached.
- Without the memetic, EvalMaxSAT leaves 130 instances unsolved (14.1 %).
  With it, 87 remain (9.4 %).
- Under `exclude` (N = 878):
  - top row 527 + 225 = 752 (85.6 %);
  - union 752 + 43 = 795 (90.5 %);
  - only EvalMaxSAT 225 (25.6 %); neither 83.

### 10.3 Evidence: reach by EvalMaxSAT time

The share of instances the memetic reached (≥ 1 of 3 seeds within 1,800 s),
among those EvalMaxSAT proved, by EvalMaxSAT CPU band:

| EvalMaxSAT CPU | `fail` | `exclude` |
|---|---|---|
| ≤ 1 s | 166 / 171 (97.1 %) | 166 / 171 (97.1 %) |
| (1, 30] s | 180 / 230 (78.3 %) | 180 / 229 (78.6 %) |
| (30, 300] s | 113 / 192 (58.9 %) | 113 / 185 (61.1 %) |
| (300, 3600] s | 70 / 199 (35.2 %) | 68 / 167 (40.7 %) |
| Cochran–Armitage trend | z = −13.4, p = 8 × 10⁻⁴¹ | z = −12.0, p = 6 × 10⁻³³ |

The share falls in every band step under both treatments. Dropping the
errored instances (`exclude`) only raises the top band (35 % → 41 %): the
errors sit mostly among the EvalMaxSAT-hard instances.

### 10.4 Evidence: complementarity

1. **The memetic-only cell is not noise.**
   - 43 / 922 = 4.7 % [3.4 %, 6.2 %] (`fail`) and 43 / 878 = 4.9 %
     [3.6 %, 6.5 %] (`exclude`), exact Clopper–Pearson 95 % intervals, well
     above 0.
   - As a share of EvalMaxSAT's timeouts: 43 / 130 = 33 % [25 %, 42 %] and
     43 / 126 = 34 % [26 %, 43 %].
2. **The memetic-only cell holds across seeds.** 22 of the 43 were reached
   by all 3 seeds, 11 by 2 seeds, 10 by 1 seed.
3. **The memetic-only cell is not one family.**
   - 17 families; 27 unweighted, 16 weighted.
   - Largest: minimizing-pentagons 7, single-machine-scheduling 7,
     judgment-aggregation 5, argumentation-framework-synthesis 4 (full list
     §5).
4. **The two one-sided cells are very unequal.**
   - Only EvalMaxSAT: 263 (`fail`) / 225 (`exclude`); only memetic: 43.
   - Exact McNemar test on the two cells: p = 1 × 10⁻³⁹ / 6 × 10⁻³¹.
   - The memetic misses 33.2 % [29.9 %, 36.6 %] / 29.9 % [26.7 %, 33.3 %]
     of what EvalMaxSAT proves.
5. **Runtime complementarity is real but modest.**
   - On the 529 / 527 instances both solve, the memetic's ERT is below
     EvalMaxSAT's CPU time on 124 (23 %), and at least 10× below on 39.
     EvalMaxSAT is at least 10× faster on 173.
   - Taking the faster of the two on each instance cuts mean PAR2 from
     1,296 s to 982 s (`fail`) and from 1,268 s to 937 s (`exclude`), about
     −25 %. PAR2 counts a failure as 2 × 3,600 s; the memetic side uses its
     ERT.
6. **Against all published 2026 solvers, the complementarity is weaker.**
   - Every one of the 43 was proved by at least one published solver: 2 by
     a single solver, most by 3–16.
   - The memetic's ERT is below the fastest published proof on 19 of the
     43.

**Caveats.**
- Reaching is not proving (10.1, point 1).
- The budgets are not symmetric. EvalMaxSAT has one run with a 3,600 s
  limit. The memetic has 3 seeds × 1,800 s, scored by ERT. Points 5 and 6
  inherit this.
- These are preliminary 3c numbers. The remaining fixes (§9: heap crash,
  Slurm wall kills) touch at most 6 instances, so neither conclusion can
  flip.

**Reproduce:** after the two `mse26_rho_errors.py` runs of §8:
`$P scripts/mse26_complementarity.py` (a few seconds).
