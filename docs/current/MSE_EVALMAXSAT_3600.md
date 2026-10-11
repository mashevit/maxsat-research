# MSE 2016 / 2023 / 2024: what exists, best-known costs, and a 3600 s EvalMaxSAT sample (s1)

**Date:** 2026-10-11. **Status:** sample s1 (60 tasks) is prepared and tested on
the workstation. **Not submitted; the user submits** (§7). Paths are relative to
`cluster_staging_maxsat/` unless they start with `docs/`.

## 1. The request (verbatim, 2026-10-11)

> check results for mse instacnses, 2016, and the new, I want to run them for
> 3600s with solver EvalMaxSat on cluster, give your opinion, later run them with
> enhanced local for hard clauses, starting from the mse24 and mse23, after
> enhancing local for hard clauses, with glucoze, I have best knowns for them,
> recheck in repo, I would like to give on cluster job, sampling, for example
> first manifest 2*30 jobs array, for evalMaxSat and meanwhile prepare the local
> search suitable for solving them.

## 2. What the repository holds [verified]

| set | where | instances | format | hard clauses | weights | existing runs |
|---|---|---:|---|---|---|---|
| MSE 2016 `ms_random` / `ms_crafted` (full) | `data/more_data/` | 856 | `p cnf` | none (all soft) | unweighted | EvalMaxSAT oracle: 12 rows only (set covering: 10 at 60 s, 1 at 1800 s; one max2sat at 120 s), **all timeouts**, no bound (`../results/oracle_more_data.jsonl`). RC2 workstation preview at 300 s on 7 of the sample (`archive/CORPUS_MSE2016_ASSESSMENT.md` §3.3): bipartite maxcut 10/10 capped; dimacs-mod and spinglass certify in ≤ 22 s. |
| MSE 2016 sample | `data/mse16/` | 104 (5 per leaf directory) | `p cnf` | none | unweighted | **The 900 s RC2 cluster screen was never run** (`CORPUS_FREEZE_PREP.md` §6 table; sbatch archived in `scripts/archive/mse16/`). |
| MSE 2023 "uw-small" | `data/raw/mse_2024/mse23-uw-small/` | 75 | new WCNF (no `p` line, `h` = hard) | 69 of 75 | unweighted | RC2 at 600 s (`results/profile/mse23_full_arr_task_*`, 75 rows): 1 certified. RC2 at 1800 s (`results/profile_cap1800/`, 75 rows): **2 certified** (ja-00000385 c\* = 37, ja-00000293 c\* = 43); 73 censored with lower bounds. Memetic: 2 instances (293, 385) in the archived tier-2 MSE runs (`archive/TIER2_MSE_TARGETSTOP_REPORT.md`). |
| MSE 2024 "small" | `data/raw/mse_2024/mse24-small/` (copied into staging 2026-10-11; repo copy `../data/raw/mse_2024/mse24-small/`, byte-identical) | 91 | new WCNF | 80 of 91 | **all weighted** (up to ~1.4 · 10⁹ cost) | **none** |

Sizes (from each file's MSE JSON header): MSE 2023 median 8,754 variables /
83,856 clauses (max 81,317 / 231,903); MSE 2024 median 16,483 / 85,399 (max
238,208 / 276,705). Hard clauses are ~98–99 % of all clauses (median). The
soft clauses are units in 64/75 and 74/91 files.

**The 2016 sets are all-soft and unweighted.** They belong to the all-soft
study (the RC2 window, the current memetic solver), not to the hard-clause
solver. **The 2023/2024 sets are the hard-clause sets.**

## 3. Best-known costs, rechecked [verified]

Files: `data/raw/mse_2024/bestknown_mse23.csv` (75 rows) and
`bestknown_mse24.csv` (91 rows), made from the raw MSE tables
`../data/raw/mse_2024/best_costs.csv` and `best_costs (1).csv`.

- **Coverage:** every local file has exactly one best-known in its own year's
  table, and every row names a local file (75/75, 91/91).
- **Fidelity:** every value equals its raw-table value (0 mismatches). The
  staging and repo copies of the two CSVs are identical.
- **Unknown (-1):** MSE 2023 `pseudoBoolean-normalized-par32-{3,5}`; MSE 2024
  `lisbon-wedding-{1-19,3-18}` and `pseudoBoolean_wt-normalized-mps-v2-20-10-mod010`.
  No solver found a hard-feasible assignment in the evaluation. They are
  excluded from sample s1 (§6).
- **Status of the values:** the MSE 2024 table flags all 91 as *anytime-track*
  instances. These are best **known** costs, not proven optima. The MSE 2023
  table has no flags.
- **Consistency with RC2 (MSE 2023):** RC2's lower bound never exceeds the
  best-known (0 violations over 67 instances with a bound). On 4 instances the
  RC2 bound **equals** the best-known, which proves those best-knowns optimal:
  - ja-00000385 (37) and ja-00000293 (43), both certified by RC2;
  - ja-00000071 (45) and im-hit-B-3-stb_390_450 (45), censored but with
    LB = best-known.
  The gaps (best-known − RC2 LB) are 0 ×4, 1–6 ×34, and 11–323 on the rest.
  8 instances have no RC2 bound at all.
- **Trap: never look a best-known up by name across years.** The two raw
  tables share 17 + 19 file names with different values. For several MSE 2023
  files, the 2024 table's value is **below RC2's proven lower bound on our
  file**, so it cannot belong to this file:

  | file | 2023 table (ours) | 2024 table | RC2 LB |
  |---|---:|---:|---:|
  | min-fill-MinFill_R0_myciel5 | 196 | 56 | 97 |
  | logic-synthesis-normalized-test4 | 94 | 31 | 55 |
  | ja-maxham-preflib-00049-00000338 | 52 | 24 | 49 |
  | ja-maxham-preflib-00049-00000512 | 54 | 25 | 51 |
  | im-forgetting-A-2-WS_300_16_90_30 | 34 | 22 | 33 |

  The manifest builder reads only the instance's own year's table.
- **Same base model, different weights:** the MSE 2023 decision-tree
  heart-cleveland `…_tree` file and the MSE 2024 `…_adaboost_5` file have the
  same size (18,651 variables, 124,971 hard clauses, 236 soft). The 2023 file
  has unit weights (best-known 31); the 2024 file has 10 distinct weights
  (best-known 122). They are different files (different content hashes).

## 4. Opinion

1. **EvalMaxSAT at 3600 s on MSE 2023/2024 is worth running.**
   - RC2 has already had 1800 s on all of MSE 2023 and proved only 2 optima.
     EvalMaxSAT is a core-guided solver built for these evaluations: it
     combines cores with UB-based hardening, and on this workstation it
     proved ja-00000385 = 37 in 109 s.
   - MSE 2024 has no exact-solver row at all.
   - For the hard-clause solver, what matters is **a target per instance**:
     a proven optimum where EvalMaxSAT finds one, otherwise the best-known.
     Its runs are measured against that target, and the EvalMaxSAT time is a
     reference effort.
2. **Expect many unsolved instances, and on some no upper bound either**
   [inference + workstation probe, §5]. The MSE 2024 set is drawn from the
   anytime track, where exact solvers often fail.
   - EvalMaxSAT prints an incumbent at SIGTERM only once it has one. At 60 s
     it had none on setcover-sts-data.135 and im-hit-B-3-stb_390_450.
   - EvalMaxSAT prints no lower bound. A capped run without an incumbent
     gives no information except "not solved in 3600 s".
   - This is still useful: it shows where an exact solver gives nothing, and
     those are the instances where the hard-clause solver can add something.
3. **Keep EvalMaxSAT apart from RC2.** It does not change the corpus rule:
   RC2 eligibility is still (30, 900] s (N-2026-10-11-d). EvalMaxSAT's 3600 s
   is a reference-optimum and upper-bound run for the hard-clause study. It
   is not an eligibility screen, and RC2 and EvalMaxSAT seconds are never
   pooled.
4. **MSE 2016: not in this batch.**
   - It is all-soft, so it does not serve the hard-clause solver.
   - For the all-soft corpus, the measure is RC2. The archived 900 s RC2
     screen of the 104-instance sample is the right first step there, not
     EvalMaxSAT 3600 s.
   - Running EvalMaxSAT on MSE 2016 would give optima (c\*) but no
     eligibility. Its only measured family (set covering) timed out
     everywhere.
   - If you want MSE 2016 optima anyway, the same scripts take any manifest
     (§7). It is a separate decision.
5. **Sampling 2 × 30 first is right.** At most 62 CPU-h. The first 30 + 30
   cover every family of both years (§6). The remaining 43 + 58 form the
   frame of a later sample.

## 5. Driver changes and workstation checks [verified]

`src/cli/oracle_evalmaxsat.py` (staging copy; the repo `src/cli/` copy is the
old version) had two defects for these files:
1. **It could not read the new WCNF dialect.** With no `p` line it treated the
   file as plain CNF. `h` lines raised a parse error. On soft-only new-format
   files, the weight became a literal. **Every MSE 2023/2024 task would have
   ended as `error`.**
2. **It stopped the solver with SIGKILL** (`subprocess.run(timeout=…)`). That
   discards EvalMaxSAT's anytime output. EvalMaxSAT's own SIGTERM handler
   (`solver_EvalMaxSat/EvalMaxSAT/main/src/main.cpp`) prints `o <cost>`,
   `s SATISFIABLE` and the model, then exits 10.
   - The earlier note "EvalMaxSAT prints no intermediate `o` lines"
     (`archive/ORACLE_EVALMAXSAT_SLURM.md`) described the SIGKILL setup, not
     the solver. Correction: N-2026-10-11-f.

**Now:**
- The dialect is fixed by the first non-comment line.
- At `--timeout`, the solver gets SIGTERM; SIGKILL follows only after
  `--term-grace`.
- The incumbent is model-checked like an optimum: `best_cost` is kept only
  if the printed model satisfies every hard clause and has exactly that cost.
- New row fields: `s_line`, `exit_code` (MSE convention: 30 optimum,
  20 unsat, 10 incumbent), `stopped_by`, `term_grace_s`. Older rows still
  load.

**Tests:** `tests/test_oracle_evalmaxsat.py`, 8 tests, all pass:
- both dialects, including soft-only new-format files;
- a `p` line after clauses is an error;
- the weighted cost and the hard-violation check;
- live runs of the binary: an optimum on a new-format file (exit 30), a
  soft-only file, and a SIGTERM stop on setcover-sts-data.135.

**Workstation probes** (the same binary as the cluster's should be;
EvalMaxSAT commit `94e6774`, 2025-11-05):

| instance | cap | result |
|---|---:|---|
| ja-maxham-00000385 | 120 s | **optimal 37** in 109.1 s, model verified, exit 30 (best-known 37; RC2 1800 s also 37) |
| setcover-sts-data.135 | 60 s | SIGTERM, `s UNKNOWN`: no incumbent yet |
| im-hit-B-3-stb_390_450 | 60 s | SIGTERM, `s UNKNOWN` |
| 600 s probes (4 instances, run concurrently) | 600 s | §5a: incumbent only on the soft-only instance; none on the 3 hard-clause ones |

## 5a. 600 s workstation probes

Run on the workstation on 2026-10-11, with **four probes at once** next to
the two smoke tasks. Times are therefore slower than on a dedicated node.

| instance | set | hard clauses | best-known | RC2 | EvalMaxSAT at 600 s |
|---|---|---:|---:|---|---|
| frb_wt-frb40-19-4 | 2024 | 0 (weighted soft only) | 720 | — | SIGTERM → **incumbent 741**, model verified, exit 10 |
| im-hit-B-3-stb_390_450 | 2023 | 3,404 | 45 | LB 45 (so the optimum is 45) | SIGTERM → **no incumbent** (`s UNKNOWN`) |
| ja-maxham-00000253 | 2023 | 93,208 | 46 | LB 45 | SIGTERM → **no incumbent** |
| setcover-sts-data.135 | 2023 | 3,015 | 103 | LB 74 | SIGTERM → **no incumbent** (also at 300 s in the smoke) |

The local end-to-end run of the sbatch on the two smoke tasks, with a fake
`module` / `activate`:
- ja-00000385 → optimum 37, verified, exit 30, in 292.7 s on the loaded
  machine (109 s alone);
- setcover-135 → SIGTERM, no incumbent.

`CHECK_SMOKE=1` printed SMOKE OK, with 0 Python calls on the login side.
The readout classified the two rows `opt=bk` and `no-ub`. The smoke cap was
then raised from 300 s to 600 s, because 293 s was too close to it.

**What this means [inference]:**
- **On hard-clause instances, EvalMaxSAT often has no hard-feasible
  assignment at all after 10 minutes, even where Glucose finds one at once.**
  As a core-guided solver, it reaches a feasible point only late.
- So at 3600 s, expect many `no-ub` rows. EvalMaxSAT's value here is the
  **proven optima**. For the rest, the target stays the best-known.
- This is also the opening for the hard-clause solver: a Glucose start
  gives an incumbent at second 0, which EvalMaxSAT may not have after an
  hour.
- ja-00000253 was solved to 46 earlier on the workstation
  (`results/EvalMaxSat.ans1`, time not recorded), so some of these may
  still certify within 3600 s.

## 6. Sample s1

Builder: `scripts/make_evalmaxsat_mse_manifest.py` (`--check` rebuilds and
diffs). Outputs: `scripts/manifest_evalmaxsat_mse_s1.{txt,sha256,tasks.csv}`.
The sidecar lists the **whole frame** with `sample` = `s1` / `rest` /
`excluded`, best-known, sizes and RC2 evidence.

**Design:**
- **Frame:** 73 MSE 2023 + 88 MSE 2024 instances, i.e. all of them except
  the 5 with best-known −1.
- **Size:** 30 per year.
- **Stratification:** every family gets one slot (17 families in 2023, 20 in
  2024). The other 13 / 10 slots go in proportion to (family size − 1), by
  largest remainder.
- **Draw within a family:** order by sha256(`20261011:<file name>`), so it is
  fixed by the seed alone.
- **Task order:** tasks 1–30 are MSE 2023 and tasks 31–60 MSE 2024, each
  sorted by family.

| year | family: frame → s1 |
|---|---|
| 2023 | inconsistency-measurement 19 → 5; judgment-aggregation 20 → 5; gen-hyper-tw 3 → 2; optimizing-BDDs 5 → 2; ramsey 6 → 2; reversi 4 → 2; setcover 4 → 2; optic 3 → 1; 9 singleton families → 1 each |
| 2024 | lisbon-wedding 11 → 3; synplicate 11 → 3; BTBNSL 10 → 2; ParametricRBACMaintenance 6 → 2; af-synthesis 5 → 2; decision-tree 4 → 2; drmx-cryptogen 5 → 2; judgment-aggregation 6 → 2; 12 other families → 1 each |

The 60 tasks (RC2 = longest-cap RC2 row: status and cost or LB):

| task | year | family | instance | best-known | vars | hard | soft | RC2 |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | mse23 | MaxSATQueriesinInterpretableClassifiers | `MaxSATQueriesinInterpretableClassifiers-wdbc_train_9_CNF_5_1` | 21 | 2563 | 44747 | 953 | censored 16 |
| 2 | mse23 | bcp | `bcp-SU3__simp-genos.haps.9.wcnf` | 106 | 6693 | 109388 | 180 | censored 103 |
| 3 | mse23 | decision-tree | `decision-tree-heart-cleveland-un-formula_0.8_2021_atleast_15` | 31 | 18651 | 124971 | 236 | censored |
| 4 | mse23 | extension-enforcement | `extension-enforcement-extension-enforcement_non-strict_stb_2` | 10 | 76190 | 148390 | 39900 | censored 6 |
| 5 | mse23 | gen-hyper-tw | `gen-hyper-tw-GenHyperTW_b01.wcnf` | 5 | 55117 | 170567 | 45 | censored 4 |
| 6 | mse23 | gen-hyper-tw | `gen-hyper-tw-GenHyperTW_grid4d_3.wcnf` | 7 | 42065 | 118609 | 40 | censored 4 |
| 7 | mse23 | inconsistency-measurement | `inconsistency-measurement-im-contension-B-3-stb_696_368.tgf.` | 63 | 6717 | 15294 | 696 | censored 58 |
| 8 | mse23 | inconsistency-measurement | `inconsistency-measurement-im-forgetting-A-2-WS_300_16_90_30.` | 34 | 6410 | 9765 | 2755 | censored 33 |
| 9 | mse23 | inconsistency-measurement | `inconsistency-measurement-im-forgetting-B-3-WS_300_16_90_30.` | 42 | 6430 | 9795 | 2765 | censored 40 |
| 10 | mse23 | inconsistency-measurement | `inconsistency-measurement-im-sum-B-3-stb_696_368.tgf.pl.wcnf` | 84 | 9974 | 15294 | 3953 | censored 55 |
| 11 | mse23 | inconsistency-measurement | `inconsistency-measurement-im-sum-C-1-grd_1222_5_4.tgf.pl.wcn` | 218 | 81317 | 122545 | 38852 | censored 148 |
| 12 | mse23 | judgment-aggregation | `judgment-aggregation-ja-maxham-preflib-00049-00000333.wcnf` | 51 | 12314 | 109543 | 105 | censored 49 |
| 13 | mse23 | judgment-aggregation | `judgment-aggregation-ja-maxham-preflib-00049-00000385.wcnf` | 37 | 6604 | 48294 | 78 | optimal 37 |
| 14 | mse23 | judgment-aggregation | `judgment-aggregation-ja-maxham-preflib-00049-00000492.wcnf` | 47 | 15162 | 134651 | 105 | censored 46 |
| 15 | mse23 | judgment-aggregation | `judgment-aggregation-ja-maxham-preflib-00049-00000512.wcnf` | 54 | 19434 | 172313 | 105 | censored 51 |
| 16 | mse23 | judgment-aggregation | `judgment-aggregation-ja-slater-preflib-00049-00000405.wcnf` | 278 | 1596 | 175560 | 1596 | censored 255 |
| 17 | mse23 | logic-synthesis | `logic-synthesis-normalized-test4.pi.opb.msat.wcnf` | 94 | 6139 | 1437 | 6139 | censored 55 |
| 18 | mse23 | mbd | `mbd-b14_C-mbd14-0277.wcnf` | 24 | 11949 | 29368 | 1851 | censored 22 |
| 19 | mse23 | min-fill | `min-fill-MinFill_R0_myciel5.wcnf` | 196 | 15416 | 108526 | 845 | censored 97 |
| 20 | mse23 | optic | `optic-gen_cvc-add7to3_9999.wcnf` | 191 | 1220 | 9737 | 1220 | censored 135 |
| 21 | mse23 | optimizing-BDDs | `optimizing-BDDs-australian-credit-un-wcnf_incomplete_improve` | 87 | 1812 | 163077 | 2612 | censored 81 |
| 22 | mse23 | optimizing-BDDs | `optimizing-BDDs-tic-tac-toe-un-wcnf_incomplete_improved_1_20` | 165 | 6394 | 156721 | 61312 | censored 2 |
| 23 | mse23 | ramsey | `ramsey-ram_k3_n15.ra0.wcnf` | 30 | 105 | 0 | 1820 | censored 3 |
| 24 | mse23 | ramsey | `ramsey-ram_k4_n20.ra0.wcnf` | 24 | 190 | 0 | 9690 | censored |
| 25 | mse23 | reversi | `reversi-rev66-16.wcnf` | 17 | 13912 | 83784 | 72 | censored 6 |
| 26 | mse23 | reversi | `reversi-rev66-32.wcnf` | 1 | 27752 | 167496 | 72 | censored |
| 27 | mse23 | scheduling | `scheduling-cnf_small.wcnf` | 28 | 12617 | 46798 | 267 | censored 25 |
| 28 | mse23 | setcover | `setcover-sts-data.243.wcnf` | 198 | 243 | 9801 | 243 | censored 140 |
| 29 | mse23 | setcover | `setcover-sts-data.729.wcnf` | 617 | 729 | 88452 | 729 | censored 294 |
| 30 | mse23 | xai | `xai-mindset2-postoperative-patient-data.wcnf` | 62 | 6412 | 30678 | 792 | censored 37 |
| 31 | mse24 | BTBNSL | `BTBNSL_wt-Rounded_BTWBNSL_Hepatitis.BIC_TWBound4.wcnf` | 132258419 | 8629 | 33640 | 302 | — |
| 32 | mse24 | BTBNSL | `BTBNSL_wt-Rounded_BTWBNSL_insurance_1000_1_3.scores_TWBound_` | 1388734978 | 18889 | 79809 | 774 | — |
| 33 | mse24 | MaxSATQueriesinInterpretableClassifiers | `MaxSATQueriesinInterpretableClassifiers_wt-compas_train_2_CN` | 31514 | 17238 | 87183 | 6546 | — |
| 34 | mse24 | ParametricRBACMaintenance | `ParametricRBACMaintenance_mse20_wt-role_smallcomp_multiple_0` | 193813 | 2400 | 8692 | 1033 | — |
| 35 | mse24 | ParametricRBACMaintenance | `ParametricRBACMaintenance_mse20_wt-role_smallcomp_multiple_0` | 267394 | 2640 | 9620 | 1128 | — |
| 36 | mse24 | af-synthesis | `af-synthesis_wt-af-synthesis_stb_50_20_8.wcnf` | 120 | 11550 | 75722 | 70 | — |
| 37 | mse24 | af-synthesis | `af-synthesis_wt-af-synthesis_stb_50_40_8.wcnf` | 117 | 13043 | 119110 | 90 | — |
| 38 | mse24 | causal-discovery | `causal-discovery_wt-causal_Bands_6_277.wcnf` | 91349 | 12764 | 45996 | 240 | — |
| 39 | mse24 | correlation-clustering | `correlation-clustering_wt-Rounded_CorrelationClustering_Prot` | 15658391 | 46150 | 197395 | 4291 | — |
| 40 | mse24 | decision-tree | `decision-tree-heart-cleveland-un-formula_0.8_2021_atleast_15` | 122 | 18651 | 124971 | 236 | — |
| 41 | mse24 | decision-tree | `decision-tree-primary-tumor-un-formula_0.8_2021_atleast_15_m` | 67 | 6715 | 53483 | 268 | — |
| 42 | mse24 | drmx-cryptogen | `drmx-cryptogen_wt-threshold128_1.wcnf` | 800 | 1600 | 0 | 9444 | — |
| 43 | mse24 | drmx-cryptogen | `drmx-cryptogen_wt-threshold128_2.wcnf` | 800 | 1600 | 0 | 9444 | — |
| 44 | mse24 | frb | `frb_wt-frb40-19-3.wcnf` | 720 | 760 | 0 | 41927 | — |
| 45 | mse24 | judgment-aggregation | `judgment-aggregation-ja-kemeny-preflib-00049-00000300.wcnf` | 776 | 2145 | 274560 | 2145 | — |
| 46 | mse24 | judgment-aggregation | `judgment-aggregation-ja-kemeny-preflib-00049-00000353.wcnf` | 554 | 2080 | 262080 | 1482 | — |
| 47 | mse24 | lisbon-wedding | `lisbon-wedding_wt-lisbon-wedding-4-17.wcnf` | 803 | 29067 | 197582 | 289 | — |
| 48 | mse24 | lisbon-wedding | `lisbon-wedding_wt-lisbon-wedding-6-19.wcnf` | 805 | 32164 | 218052 | 323 | — |
| 49 | mse24 | lisbon-wedding | `lisbon-wedding_wt-lisbon-wedding-9-18.wcnf` | 395 | 30553 | 204985 | 396 | — |
| 50 | mse24 | metro | `metro_wt-metro_8_8_5_20_10_6_500_1_3.lp.sm-extracted.wcnf` | 138 | 55334 | 134411 | 127 | — |
| 51 | mse24 | mpe | `mpe_wt-random-net-30-5_network-4.net.wcnf` | 28151 | 89 | 28 | 5836 | — |
| 52 | mse24 | preference_planning | `preference_planning_wt-WCNF_pathways_p16.wcnf` | 257 | 23856 | 148708 | 42 | — |
| 53 | mse24 | quantum-circuit | `quantum-circuit-qgan_6_15_ibmq-casablanca_7.wcnf` | 24 | 8312 | 105976 | 1274 | — |
| 54 | mse24 | ramsey | `ramsey_wt-ram_k3_n17.ra1.wcnf` | 10372 | 136 | 0 | 3060 | — |
| 55 | mse24 | setcover | `setcover_wt-rail507.wcnf` | 174 | 63009 | 507 | 63009 | — |
| 56 | mse24 | spot5 | `spot5_wt-1407.wcsp.log.wcnf` | 459570 | 1706 | 35933 | 1057 | — |
| 57 | mse24 | synplicate | `synplicate_new-synplicate_complete_tree_arity2_feature_4_siz` | 224 | 19003 | 55430 | 71 | — |
| 58 | mse24 | synplicate | `synplicate_new-synplicate_complete_tree_arity3_feature_3_siz` | 182 | 42857 | 125570 | 67 | — |
| 59 | mse24 | synplicate | `synplicate_new-synplicate_synthetic_dag_run1_16_size_4_ms_0_` | 147 | 48911 | 146397 | 525 | — |
| 60 | mse24 | tcp | `tcp_wt-tcp_students_112_it_13.wcnf` | 2958 | 238208 | 242731 | 284 | — |

(Names are truncated to 60 characters; the full paths are in the manifest.)
Task 13 (ja-00000385, optimum 37, proven by RC2) is a built-in check of the
whole pipeline.

## 7. Files and commands

| file | role |
|---|---|
| `src/cli/oracle_evalmaxsat.py` | driver (stdlib only): dialects, SIGTERM stop, model check |
| `scripts/evalmaxsat_array.sbatch` | one instance per task; `--time 01:10:00`, `--mem 16G`; writes `task_N.jsonl` + `task_N.env.json` (binary sha256, host, Slurm ids); a task with a final row exits at once |
| `scripts/submit_evalmaxsat_mse.sh` | **shell only**; checks files, binary, sha256; `DRY_RUN`, `SMOKE`, `CHECK_SMOKE`, `IDS`, `THROTTLE` |
| `scripts/manifest_evalmaxsat_mse_s1.{txt,sha256,tasks.csv}` | sample s1 (60) and the frame |
| `scripts/manifest_evalmaxsat_mse_smoke.{txt,sha256}` | smoke: ja-00000385 (optimum 37) and setcover-sts-data.135 (SIGTERM) |
| `scripts/make_evalmaxsat_mse_manifest.py` | builds s1 (workstation) |
| `scripts/evalmaxsat_mse_readout.py` | readout against best-known and RC2 (workstation) |
| `scripts/rsync_files_evalmaxsat_mse_s1.txt` | `rsync --files-from` list: the above plus the 60 + 2 instances |

**The EvalMaxSAT binary on the cluster.** The wrapper and the array expect
`~/cluster_staging_maxsat_evo/EvalMaxSAT/build/main/EvalMaxSAT_bin` (the
default since commit `0dc3bc3`). Otherwise pass `EVALMAXSAT_BIN=/abs/path`.
- If it is not there, build it on a **compute node** (e.g. inside an `srun`
  or a short sbatch), not on the login node.
- The smoke shows on a node that the binary runs, reads the new format,
  proves 37, and handles SIGTERM.

**Budget:**
- s1: 60 × (3600 + 120) s = **62 CPU-h** worst case. At %30, that is
  2 waves × ~65 min ≈ **2.2 h** of compute, excluding queue delay.
- Smoke: 2 × 660 s, about 0.4 CPU-h.

```bash
# 1. workstation -> cluster (minimal set: 72 paths, ~120 MB)
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat
rsync -av --files-from=<(grep -v '^#' scripts/rsync_files_evalmaxsat_mse_s1.txt) ./ <user>@<cluster>:~/cluster_staging_maxsat_evo/

# 2. login node (shell only)
cd ~/cluster_staging_maxsat_evo/scripts && mkdir -p logs
ls -l ../EvalMaxSAT/build/main/EvalMaxSAT_bin          # must exist (else EVALMAXSAT_BIN=...)
DRY_RUN=1 bash submit_evalmaxsat_mse.sh                 # checks + the sbatch line
SMOKE=1 bash submit_evalmaxsat_mse.sh                   # 2 tasks, 600 s cap, ~11 min
CHECK_SMOKE=1 bash submit_evalmaxsat_mse.sh             # after it: must print SMOKE OK
bash submit_evalmaxsat_mse.sh                           # sample s1: one array, tasks 1-60, %30
                                                        # (1-30 MSE 2023, 31-60 MSE 2024)
RESUME=1 bash submit_evalmaxsat_mse.sh                  # only if rows are missing; finished tasks exit at once

# 3. back on the workstation
rsync -av <user>@<cluster>:~/cluster_staging_maxsat_evo/results/evalmaxsat_mse_s1/ results/evalmaxsat_mse_s1/
python3 scripts/evalmaxsat_mse_readout.py
```

## 8. What the readout gives, and what comes next

- **Per task, a class:** `opt=bk`, `opt<bk` (the table was not optimal),
  `opt>bk` (contradiction; investigate), `ub=bk`, `ub<bk`, `ub>bk`, `no-ub`,
  `unsat`, `error`. Every proven optimum is also checked against RC2's lower
  bound.
- **Targets for the hard-clause solver** (`HARD_CLAUSE_SOLVER_PLAN.md`): the
  proven optimum if any, else the best-known. The user decided that the
  hard-clause solver starts on MSE 2024 and 2023 (N-2026-10-11-g). Its first
  instances would be the s1 instances where EvalMaxSAT proves the optimum,
  because a target that is certainly reachable makes success unambiguous.
- **s2** (the rest of the frame, 43 + 58) is a separate decision after s1.
