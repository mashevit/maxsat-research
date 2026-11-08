# ρ on MSE 2026: third readout (batch 3c after the error fixes, 2026-11-01)

> "reclassify them as failures, document it, commit and push, I think if one seed managed to come to optimum, you might count it. document this. rerun rho and write it in third conclusion file" (user, 2026-11-01)

> **Assessment 2026-11-08 (user; N-2026-11-08-a):** the MSE 2026 analysis is
> regarded as a **negative result**: it does not establish the intended research
> contribution. The 44 memetic-only instances, the coverage gain and the low ρ in the selected hard subsets (window, E4) are not evidence of a contribution. The numbers below are unchanged and may be reported; the
> complementarity interpretation they were given is withdrawn. See
> [`RESEARCH_ASSESSMENT_NEGATIVE_RESULT_2026-11-08.md`](RESEARCH_ASSESSMENT_NEGATIVE_RESULT_2026-11-08.md).

**Status.** The third set of ρ numbers for batch 3c. It replaces the earlier two as
the current readout; they stay as records:

| # | where | runs in | errored runs |
|---|---|---|---|
| 1 | [`MSE26_RHO_PRELIM_RESULTS.md`](MSE26_RHO_PRELIM_RESULTS.md) (2026-10-29) | 2,845 records | 118: heap crash 6 (A), glucose_timeout 107 (B), Slurm kill 5 (D) |
| 2 | [`MSE26_3C_RUN.md`](MSE26_3C_RUN.md) §9.6 (2026-11-01) | + 6 workstation records for A | 112: B 107, D 5 |
| **3** | **this document** | **as 2, with D reclassified as failures** | **107: B only** |

Method: the pre-registered analysis ([`MSE26_RHO_PREREG.md`](MSE26_RHO_PREREG.md),
`scripts/mse26_rho.py`, unchanged): ρ = Spearman with midranks (∞ ties share one
midrank), 95 % BCa bootstrap over instances, B = 10,000, seed 20261029.
x = EvalMaxSAT CPU seconds in its published 2026 run (timeout = ∞); y = memetic
ERT over seeds 1–3, budget 1,800 s of process CPU (no success = ∞).

## 1. What changed since readout 1

- **Group A (heap crash, 6 runs, 2 kbtree instances):** a PySAT Glucose4 overrun on
  repeated assumptions, fixed in `src/evo/hard.py`; the 6 tasks were run on the
  workstation with the fix (no cluster rerun, user). `MSE26_3C_RUN.md` §9.4–9.6.
- **Group D (Slurm 1 h wall kill, 5 runs, 4 instances):** reclassified as **final
  failures charged the budget** (class `slurm_wall_kill`, list
  `scripts/m2_reclass.tsv`). All 5 were still running at 1 h of wall time with
  CPU ≈ wall, so far past the 1,800 s CPU budget, and a target hit would have
  ended the run and written the record at once. `MSE26_3C_RUN.md` §9.7.
- **One seed at the optimum counts.** ERT = (sum of the 3 efforts) / (successes):
  a failed seed adds 1,800 s, one success makes y finite. cf864e2f (planning-bnn,
  EvalMaxSAT proved at 988 s) had seed 3 at the optimum in 740.8 s and seed 2
  killed: y = (1,800 + 1,800 + 740.8) / 1 = 4,340.8 s, so it counts as reached.
- **Group B (`glucose_timeout`, 107 runs, 38 instances)** stays an error (user):
  `fail` charges the budget, `exclude` drops the instance.

So `fail` is identical to readout 2 (it already counted D as failures), and
`exclude` gains the 4 group D instances (N 880 → 884).

## 2. Population

| | `fail` | `exclude` |
|---|---:|---:|
| instances with a published optimum | 947 | 947 |
| primary (EvalMaxSAT proved or timed out; 17 memouts and 8 crashes out) | 922 | 922 |
| complete and in the analysis | **922** | **884** |
| dropped (an instance with a `glucose_timeout` run) | 0 | 38 |

## 3. Primary and sensitivity analyses

| analysis | `fail`: ρ [95 % CI] | N | ∞ x / y / both | `exclude`: ρ [95 % CI] | N | ∞ x / y / both |
|---|---|---:|---|---|---:|---|
| **primary: ERT, pooled** | **+0.637 [+0.588, +0.680]** | 922 | 44 / 262 / 86 | **+0.632 [+0.584, +0.677]** | 884 | 44 / 228 / 83 |
| 1 window (30, 3600] s, both uncensored | +0.223 [+0.078, +0.362] | 184 | 0 / 0 / 0 | +0.218 [+0.070, +0.360] | 183 | 0 / 0 / 0 |
| 2 x = EvalMaxSAT wall time | +0.637 [+0.588, +0.680] | 922 | 44 / 262 / 86 | +0.632 [+0.584, +0.677] | 884 | 44 / 228 / 83 |
| 3 flip-level effort | +0.637 [+0.588, +0.680] | 922 | 44 / 262 / 86 | +0.632 [+0.584, +0.677] | 884 | 44 / 228 / 83 |
| 4 memetic budget 900 s | +0.638 [+0.590, +0.682] | 922 | 39 / 289 / 91 | +0.634 [+0.585, +0.678] | 884 | 39 / 254 / 88 |
| 5 family-stratified bootstrap | +0.637 [+0.600, +0.672] | 922 | 44 / 262 / 86 | +0.632 [+0.594, +0.667] | 884 | 44 / 228 / 83 |
| 6 partial ρ on log n_vars, log n_clauses | +0.569 [+0.517, +0.618] | 922 | 44 / 262 / 86 | +0.572 [+0.519, +0.619] | 884 | 44 / 228 / 83 |
| 7 PAR2, all proven-optimum instances | +0.635 [+0.588, +0.677] | 947 | — | +0.632 [+0.584, +0.675] | 909 | — |

Prereg §7: every row is a **positive association** (CI above 0) under both
treatments. D1 (seeds 4–5) is **not triggered** (primary half-width 0.046 /
0.047 < 0.15).

**Per track (primary):**

| track | `fail` | N | `exclude` | N |
|---|---|---:|---|---:|
| unweighted | +0.618 [+0.542, +0.681] | 464 | +0.618 [+0.543, +0.683] | 460 |
| weighted | +0.659 [+0.595, +0.715] | 458 | +0.650 [+0.582, +0.709] | 424 |

**Against readout 1:** primary +0.639 → +0.637 (`fail`), +0.635 → +0.632
(`exclude`); window +0.212 → +0.223 / +0.200 → +0.218. Every change is inside
±0.02, far inside the CIs.

## 4. Complementarity (primary population; `scripts/mse26_complementarity.py`)

| | `fail` (N 922) | `exclude` (N 884) |
|---|---|---|
| EvalMaxSAT proved | 792 (85.9 %) | 757 (85.6 %) |
| memetic reached (≥ 1 seed) | 574 (62.3 %) | 573 (64.8 %) |
| union | 836 (90.7 %) | 801 (90.6 %) |
| both / only EvalMaxSAT / **only memetic** / neither | 530 / 262 / **44** / 86 | 529 / 228 / **44** / 83 |
| only memetic / N | 4.8 % [3.5, 6.4] | 5.0 % [3.6, 6.6] |
| only memetic / EvalMaxSAT timeouts | 44 / 130 = 33.8 % [25.8, 42.7] | 44 / 127 = 34.6 % [26.4, 43.6] |
| McNemar exact (only EvalMaxSAT vs only memetic) | p = 6.3 × 10⁻³⁹ | p = 4.1 × 10⁻³¹ |
| mean PAR2: EvalMaxSAT → best of the two | 1,296 s → 978 s | 1,273 s → 941 s |

Memetic reach by EvalMaxSAT time band (`fail`): (0, 1] s 97.1 %, (1, 30] 78.3 %,
(30, 300] 58.9 %, (300, 3600] 35.7 %; Cochran–Armitage z = −13.3, p = 2.8 × 10⁻⁴⁰
(`exclude`: 97.1 / 78.3 / 61.1 / 40.9 %, p = 7.5 × 10⁻³³).

The 44 memetic-only instances (43 in readout 1, plus 27770a63, kbtree, from the
group A fix): 17 families, 28 unweighted / 16 weighted; the memetic's ERT is
below the fastest published proof on 19 of them. On the 530 instances both solve,
the memetic is faster on 124 (≥ 10× on 39), EvalMaxSAT ≥ 10× faster on 173.

### 4.1 Who solved what, in percent

> "add explicitly in docs and give me pointer - how much percent only the memetic solved, how much percent only evalmaxsat solved, and how much both" (user, 2026-11-01)

"Solved" means EvalMaxSAT **proved** the optimum in its published 2026 run, and the
memetic **reached** it (≥ 1 of seeds 1–3, 1,800 s CPU budget). The memetic does not
prove optimality. Counts come from `results/mse26_rho_r3_complementarity.txt`
(`scripts/mse26_complementarity.py`). Percentages are computed from those counts,
with 95 % Clopper–Pearson intervals.

**Share of all instances.** Each column sums to 100 %.

| | `fail` (N 922) | `exclude` (N 884) |
|---|---|---|
| **both** | 530 = **57.5 %** [54.2, 60.7] | 529 = **59.8 %** [56.5, 63.1] |
| **only EvalMaxSAT** | 262 = **28.4 %** [25.5, 31.4] | 228 = **25.8 %** [22.9, 28.8] |
| **only memetic** | 44 = **4.8 %** [3.5, 6.4] | 44 = **5.0 %** [3.6, 6.6] |
| neither | 86 = 9.3 % [7.5, 11.4] | 83 = 9.4 % [7.5, 11.5] |

**Share of the instances that at least one solver solved** (union: 836 `fail`, 801
`exclude`).

| | `fail` (836) | `exclude` (801) |
|---|---|---|
| both | 63.4 % | 66.0 % |
| only EvalMaxSAT | 31.3 % | 28.5 % |
| only memetic | 5.3 % | 5.5 % |

One-line version (primary, `fail`): **both 57.5 %, only EvalMaxSAT 28.4 %, only
the memetic 4.8 %, neither 9.3 %** of the 922 instances.

### 4.2 The same split above 30 s, and what it does and does not credit the memetic with

> "how can this be achivement to memetic? give table like this only for above 30s interval" (user, 2026-11-01)

**Subset.** "Above 30 s" means **x > 30 s, with EvalMaxSAT timeouts (x = ∞)
included**: EvalMaxSAT needed more than 30 s or did not prove the optimum. Hardness
is measured on the EvalMaxSAT side, as in E4 (§5). This subset is E4's population
plus its both-∞ cell ("neither"). Computed from
`results/mse26_rho_r3_<fail|exclude>/instances.csv`. 95 % Clopper–Pearson intervals.

| x > 30 s | `fail` (N 521) | `exclude` (N 483) |
|---|---|---|
| **both** | 184 = **35.3 %** [31.2, 39.6] | 183 = **37.9 %** [33.5, 42.4] |
| **only EvalMaxSAT** | 207 = **39.7 %** [35.5, 44.1] | 173 = **35.8 %** [31.5, 40.3] |
| **only memetic** | 44 = **8.4 %** [6.2, 11.2] | 44 = **9.1 %** [6.7, 12.0] |
| neither | 86 = 16.5 % [13.4, 20.0] | 83 = 17.2 % [13.9, 20.9] |
| of the union (435 / 400): both / only EvalMaxSAT / only memetic | 42.3 / 47.6 / 10.1 % | 45.8 / 43.2 / 11.0 % |
| McNemar exact (207 vs 44; 173 vs 44) | p = 1.8 × 10⁻²⁶ | p = 2.8 × 10⁻¹⁹ |

By EvalMaxSAT band (`fail`):

| EvalMaxSAT time | N | both | only EvalMaxSAT | only memetic | neither |
|---|---|---|---|---|---|
| ≤ 30 s (for contrast) | 401 | 86.3 % | 13.7 % | 0 | 0 |
| (30, 300] s | 192 | 58.9 % | 41.1 % | 0 | 0 |
| (300, 3600] s | 199 | 35.7 % | 64.3 % | 0 | 0 |
| timeout (∞) | 130 | 0 | 0 | 33.8 % | 66.2 % |

The zeros follow from the definition: wherever EvalMaxSAT proved the optimum, the
cell is "both" or "only EvalMaxSAT"; wherever it timed out, it is "only memetic" or
"neither".

On the 184 instances above 30 s that both solve (`fail`), the memetic is faster on
77 (≥ 10× faster on 35), EvalMaxSAT is ≥ 10× faster on 26. Mean PAR2 above 30 s
(`fail`): EvalMaxSAT 2,290 s, memetic 4,575 s, per-instance best of the two 1,727 s.

**What this credits the memetic with [inference].**

- **Not "better than EvalMaxSAT".**
  - As a single solver, the memetic is clearly weaker: overall 62.3 % vs 85.9 %.
    Above 30 s, "only EvalMaxSAT" outnumbers "only memetic" about 4.7 : 1. Its
    PAR2 is twice EvalMaxSAT's.
  - Above 30 s, the memetic misses 41 % of what EvalMaxSAT proves in (30, 300] s,
    and 64 % of what it proves in (300, 3600] s.
- **The contribution is complementarity.**
  1. It reaches **44 of the 130 instances EvalMaxSAT cannot prove (34 %)**,
     spread over 17 families.
  2. Adding it to EvalMaxSAT raises coverage from 85.9 % to 90.7 %. Above 30 s,
     it raises coverage from 75.0 % (391 / 521) to 83.5 % (435 / 521).
  3. Above 30 s, it cuts mean PAR2 from 2,290 s to 1,727 s.
  4. On the hard instances both solve, it is ≥ 10× faster more often than
     EvalMaxSAT is (35 vs 26).
  - So the defensible claim is "a useful portfolio partner for a state-of-the-art
    exact solver on its hard tail". It is not "a stronger solver".
  - **Correction 2026-11-08 (N-2026-11-08-a):** this claim is **withdrawn**. The
    points above describe one pair of solvers; no baseline (another published
    solver, or local search with restarts, under a comparable budget) was
    compared, and every memetic-only instance was proved by a published solver.
    The findings are insufficient to support the intended contribution.
- **Caveats that limit even that claim.**
  - The memetic *reaches* the published optimum and does not prove it.
  - The memetic is stopped when it hits a known target value. A deployed anytime
    solver would not know when to stop.
  - The two solvers had different budgets and hardware. EvalMaxSAT: one published
    run, 3,600 s CPU. Memetic: our cluster, 3 seeds × 1,800 s, scored by ERT.
  - Each of the 44 memetic-only instances was proved by at least 1 (up to 19)
    of the published 2026 solvers. On 19 of them, the memetic's ERT is below the
    fastest published proof.
  - Against the MSE virtual best solver, the coverage gain would be smaller than
    against EvalMaxSAT alone. That comparison was not computed.

### 4.3 Above 30 s, not both failed (E4's population), and where the 100 % is

> "give me similar table with above 30 s where both , actually explain me why in this row where we i think didnt want both solvers to fail, why there isnt in this table a 100 percent cell, what is 100 percent means?" (user, 2026-11-01)

**Subset.** x > 30 s (timeouts included), with the instances where *both* failed
removed. This is exactly E4's population (§5). Each column is 100 % of its N.
95 % Clopper–Pearson intervals.

| x > 30 s, not both failed | `fail` | `exclude` |
|---|---|---|
| **both** | 184 = **42.3 %** [37.6, 47.1] | 183 = **45.8 %** [40.8, 50.8] |
| **only EvalMaxSAT** | 207 = **47.6 %** [42.8, 52.4] | 173 = **43.2 %** [38.3, 48.3] |
| **only memetic** | 44 = **10.1 %** [7.4, 13.3] | 44 = **11.0 %** [8.1, 14.5] |
| **total = 100 %** | **435** | **400** |

By EvalMaxSAT band (`fail`). Each row sums to 100 %.

| EvalMaxSAT time | N (= 100 %) | both | only EvalMaxSAT | only memetic |
|---|---|---|---|---|
| (30, 300] s | 192 | 58.9 % | 41.1 % | 0 |
| (300, 3600] s | 199 | 35.7 % | 64.3 % | 0 |
| timeout (∞) | 44 | 0 | 0 | **100 %** |

**What "100 %" means.**
- The 100 % is the **denominator**: all instances in the subset.
  - In §4.2 that is every instance with x > 30 s (521). There the four cells sum
    to 100 %, and "neither" is one of them (16.5 %).
  - Here "neither" is removed, so 100 % = the 435 instances that at least one
    solver solved. The three remaining cells sum to 100 %.
- In §4.2, the 100 % appears only as N in the column header; it is not printed as
  a cell. The "of the union" row of §4.2 is this table squeezed into one row. Its
  three numbers (42.3 / 47.6 / 10.1 %) sum to 100 %.
- Dropping "both failed" does **not** make any single cell 100 % overall. It only
  removes the "neither" cell. Every instance left is still in one of three cells:
  both, only EvalMaxSAT, or only memetic.

**The one 100 % cell is the timeout row, and it holds by construction.**
- When EvalMaxSAT times out, an instance can only be "only memetic" or "neither".
- Once "neither" is removed, the 44 remaining timeout instances are all "only
  memetic".
- So that 100 % restates the subset's definition. It is not a finding.
- The finding is the 44 / 130 = 33.8 % of §4.2: the share of EvalMaxSAT timeouts
  the memetic reaches.

**Where a 100 % "both" would come from.**
- If the subset were "both solved" (the 184 instances of the window analysis, §3),
  "both" would be 100 % and the other cells empty.
- That subset says nothing about who solves what. It is used only for comparing
  runtimes on the same instances (ρ in the window, speed-ups).

## 5. Exploratory subsets (not pre-registered; `scripts/mse26_rho_explore.py`; as §11 of readout 1)

| subset | `fail`: ρ [95 % CI] | N | ∞ x / y / both | `exclude`: ρ [95 % CI] | N | ∞ x / y / both |
|---|---|---:|---|---|---:|---|
| E1 both solved, all x | +0.634 [+0.567, +0.690] | 530 | 0 / 0 / 0 | +0.632 [+0.564, +0.688] | 529 | 0 / 0 / 0 |
| E2 not both ∞, all x | +0.588 [+0.534, +0.637] | 836 | 44 / 262 / 0 | +0.578 [+0.520, +0.630] | 801 | 44 / 228 / 0 |
| E3 window (30, 3600] s, y may be ∞ | +0.244 [+0.144, +0.340] | 391 | 0 / 207 / 0 | +0.206 [+0.103, +0.310] | 356 | 0 / 173 / 0 |
| E4 x > 30 s (∞ included), not both ∞ | +0.064 [−0.037, +0.161] | 435 | 44 / 207 / 0 | +0.039 [−0.062, +0.141] | 400 | 44 / 173 / 0 |
| ref = §3 sensitivity 1 | +0.223 [+0.078, +0.362] | 184 | 0 / 0 / 0 | +0.218 [+0.070, +0.360] | 183 | 0 / 0 / 0 |

E4 both-finite instances: 184 / 183 (= N − ∞ x − ∞ y = the ref subset).

## 6. Conclusions [inference, on these numbers]

1. **The pre-registered result holds after the fixes:** EvalMaxSAT proof time and
   memetic time to the optimum are positively associated, ρ ≈ +0.63–0.64, under
   both error treatments and every sensitivity analysis (+0.57 after partialling
   out instance size).
2. **In the hard regime the association is weak:** the window (30, 3600] s with
   both solved gives +0.22 (CI above 0). The drop comes from the 30 s lower bound,
   not from censoring (E1, both solved without the bound, is +0.63).
3. **Complementarity:** the memetic reaches the optimum on 44 instances that
   EvalMaxSAT does not prove (a third of its timeouts); EvalMaxSAT proves 262 /
   228 that the memetic does not reach. Memetic reach falls steadily with
   EvalMaxSAT time. Combining the two lifts coverage from 85.9 % to 90.7 %.
   *Correction 2026-11-08 (N-2026-11-08-a): the numbers stand; they are not
   evidence of a distinctive or useful contribution (no comparable-budget
   baseline; reaching ≠ proving).*
4. **Above 30 s with either side allowed to fail (E4)** the association is at
   most weak (CI inside (−0.3, +0.3) and containing 0). E4 is outcome-defined and
   mostly measures which solver fails, not how hardness is ordered; it is not an
   orthogonality claim (prereg §7).
5. **The error handling does not drive any conclusion:** `fail` and `exclude`
   agree within 0.01 on the primary and within 0.04 everywhere.

## 7. Reproduce

From `cluster_staging_maxsat_strong/`, after the 3c copy back plus the 6 group A
records (`results/mse26_memetic/provenance/workstation_groupA_20261101.txt`):
`bash scripts/run_rho_r3.sh` (~10 min). It runs `mse26_rho_errors.py --errors
{fail,exclude}` into `results/mse26_rho_r3_{fail,exclude}/`, then
`MSE26_RHO_TAG=r3_ mse26_rho_explore.py` (→ `results/mse26_rho_explore_r3/`) and
`MSE26_RHO_TAG=r3_ mse26_complementarity.py` (→
`results/mse26_rho_r3_complementarity.txt`). Outputs are not committed.
Classification: `scripts/m2_results.py` with `scripts/m2_reclass.tsv`.
