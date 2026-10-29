# ρ pre-registration: memetic vs exact hardness on MSE 2026 (milestone 4)

> "go, write the rho pre-registration" (user, 2026-10-29)

**Status: DRAFT r4, 2026-10-29.** It becomes binding when the user approves it
and it is committed; the commit hash is then entered here.
- **r1** (`dda60a8`): primary = the EvalMaxSAT (30, 3600] s window, successes
  only.
- **r2** (`08d6056`, user): primary = all instances, censored on both axes
  (timeouts and zero successes = ∞, midranks); the window as a sensitivity
  analysis; ρ against every published solver instead of the VBS.
- **r3** (user, 2026-10-29): **targets only optima proven by an exact solver
  in the 2026 runs** (any solver, not only EvalMaxSAT), so no best-known
  targets and no batch 3d; ERT spelled out on both axes; no 300 s budget.
- **r4** (user, 2026-10-29: "go with option 1, if there are memouts and
  crashes on EVALMAXSAT where there are instances with optimum do par2
  there"): ERT stays primary; **PAR2 is added as a sensitivity analysis**,
  in which EvalMaxSAT's memouts and crashes on proven-optimum instances enter
  with the PAR2 penalty instead of being excluded.

**Blind:** every revision was written while batch 3c
([`MSE26_3C_RUN.md`](MSE26_3C_RUN.md)) ran on the cluster, before any 3c
record was copied to the workstation or read (`results/mse26_memetic/` did
not exist locally). Anything added after the records are read is labelled
exploratory.

Sources of the conventions: the M2 pre-registration
(`docs/M2_FULL_POOL_READOUT_AND_STATE.md` §1, repo), the MSE design
(`NOTES_2026-10-21_AGENDA_AND_STATS.md` §5, §8.3, §11), the ρ plan
([`MSE26_RHO_PLAN.md`](MSE26_RHO_PLAN.md) §7, §9).

## 1. Question

Across MSE 2026 exact-track instances with a proven optimum, do the instances
that are hard for an exact MaxSAT solver also take the memetic long to reach
the optimum? ρ is the Spearman rank correlation between the two ERTs, one
point per instance, with failures on either side as tied top ranks. A low ρ,
with each solver reaching instances the other does not, is the
"complementary hardness" result; a high ρ means the two see the same
hardness. No direction is assumed: the tests are two-sided.

## 2. Population

**Frame:** all 1,216 MSE 2026 exact-track instances (Zenodo 21358014). One
row each in `scripts/mse26_population.tsv` (strong tree), written by
`scripts/mse26_population.py` from the published metadata and raw results;
counts below are from it.

**The target is a proven optimum:** the published `optimal_cost`, proved in
the 2026 runs by **at least one exact solver** (a run with OPTIMUM FOUND,
`verified` 1 and `optval` = `optimal_cost`; any of the 22 unweighted / 15
weighted solvers): **947 instances**. Without a target (excluded, listed in
the table by `target_kind`):
- **no published optimum: 260** (no 2026 run answered OPTIMUM FOUND on any of
  them);
- **infeasible: 4** (every answer UNSATISFIABLE: `1d4d3512`, `21a4f155`,
  `63cb4386`, `bd26740c`);
- **a published optimum that no 2026 run proved: 5** (`9db6427c` scheduling,
  `ec201844` railway-transport, `1d1e713e` rail, `b1d02455`
  railway-timetabling, `d72b8cab` minimum-weight-dominating-set; they still
  run in 3c).

**The x side (EvalMaxSAT's published run, one run per instance):**

| EvalMaxSAT outcome (on the 947) | rule | instances |
|---|---|---:|
| proved (OPTIMUM FOUND, verified, the optimum, CPU ≤ 3,600 s) | x finite | 792 |
| timeout | x = ∞, **censored, tied top rank** (another solver proved it) | 130 |
| memout | non-timeout failure: **excluded and counted** | 17 |
| crash (no answer, no timeout, no memout) | non-timeout failure: excluded and counted | 8 |
| wrong answer (OPTIMUM FOUND unverified or not the optimum) | non-timeout failure: excluded and counted | 0 |

**Primary population: 922 instances** (464 unweighted, 458 weighted): 792
with x finite, 130 with x censored. The 25 memouts and crashes stay excluded
here and enter only the PAR2 sensitivity analysis (§4.7, 947 instances). **All 922 are in batch 3c**; no further
memetic batch is needed.

**Eligibility depends on x and the published data only**, never on a memetic
outcome. After the runs, an instance leaves only if it still lacks 3 valid
records after the reruns of §5 (listed with the reason).

## 3. ERT on both axes

ERT (expected running time) is the expected time to the first success when
failed runs are restarted: **ERT = (total effort of all runs) / (number of
successful runs)**, where a successful run contributes its time to the
target and a failed run its full spend; **no success → ERT = ∞**.

- **x = EvalMaxSAT's ERT** from its single published run, on the CPU clock
  MSE 2026 limits and counts (every timeout at CPU 3,600.0 s;
  MSE26_RHO_PLAN.md §9): proved → x = its CPU time (one run, one success);
  timeout → x = ∞ (one run, zero successes).
- **y = the memetic's ERT** over seeds 1–3 (configs/strong/auto.yaml, budget
  B = 1,800 s of process CPU, stop at the optimum):
  - a run **succeeds** iff `stop_reason` is target and `cpu_to_target_s` ≤ B;
    its effort is `cpu_to_target_s` (process CPU from the start: start-up,
    imports, hash, parse, kernel gate, hparams, search);
  - a failed run (budget exhausted, target after B, watchdog) is charged B;
  - y = (sum of the three efforts) / (number of successes); zero successes →
    y = ∞.
  - Example: TTTs 100 s and 300 s and one failure → (100 + 300 + 1,800) / 2
    = 1,100 s.
  - Computed by `scripts/m2_results.py` (`ert_s` in `by_instance_config.csv`;
    blank while any run of the instance is missing or invalid; tests in
    `tests/test_m2_results.py`).
- **PAR2 (sensitivity analysis §4.7 only):** the SAT-competition measure, the
  mean over runs of the time to the target with every unsolved run counted
  as 2 × its limit.
  - x_PAR2 = EvalMaxSAT's CPU time if proved, else 2 × 3,600 = **7,200 s**
    (timeout, memout or crash);
  - y_PAR2 = mean over seeds 1–3 of `cpu_to_target_s` for successes and
    2 × 1,800 = **3,600 s** for failures (`par2_s` in
    `by_instance_config.csv`, `scripts/m2_results.py`);
  - with ranks, x_PAR2 orders the instances as x does (every 7,200 ties above
    every proof); y_PAR2 can reorder partly solved instances: seeds 1 s,
    1 s, failed give ERT 901 but PAR2 1,201, above 3 × 1,000 s (ERT = PAR2 =
    1,000).
- **Budget asymmetry, stated with every result:** 1,800 s for the memetic,
  3,600 s for EvalMaxSAT, on different hardware. Ranks are unaffected by a
  uniform speed factor; the censoring points differ.

## 4. Analyses

**Primary:** Spearman ρ(x, y) on the 922 instances, **with midranks** for
ties (all ∞ on an axis share one midrank); **95 % BCa bootstrap CI over
instances, B = 10,000**, seed 20261029. Reported with it: the number of
instances **censored on x only, on y only, and on both**, and the number
excluded (by reason).

**Sensitivity analyses (all reported, none replaces the primary):**
1. **The window, both axes uncensored:** x finite in (30, 3600] s CPU (391
   instances) and y finite (≥ 1 memetic success).
2. **x = EvalMaxSAT wall time** (timeouts still ∞).
3. **Flip-level effort:** y with `cpu_to_target_hit_s` for successes.
4. **A shorter memetic budget read off the same records:** B = 900 s
   (success iff `cpu_to_target_s` ≤ 900, failures charged 900).
5. **Family-stratified bootstrap:** resampling within families.
6. **Partial Spearman ρ** controlling for log n_vars and log n_clauses of the
   original instance (size as a common cause), midranks.
7. **PAR2 instead of ERT on both axes:** ρ(x_PAR2, y_PAR2) with midranks and
   BCa on **all 947 proven-optimum instances**, EvalMaxSAT's 17 memouts and 8
   crashes included at x_PAR2 = 7,200 s (user 2026-10-29); reported with the
   number of instances at the PAR2 penalty on x, on y and on both.

**ρ against every published solver (replaces the VBS analysis, user
2026-10-29):** for each solver of the MSE 2026 exact tracks (22 unweighted,
15 weighted), x = that solver's ERT from its single run with EvalMaxSAT's
rules (proved → CPU; timeout → ∞; memout, crash or wrong answer → excluded
from that solver's ρ and counted); y and the midrank/BCa method as in the
primary; on the 947 proven-optimum instances of its track. Reported per track
as one figure with CIs, plus a pooled value for solvers present in both
tracks.

**Breakdowns (descriptive, CIs shown, no tests):** per track; per family
with ≥ 10 instances in the primary population.

## 5. Running rules (fixed before results are read)

- **Reruns are for infrastructure only:** a task with no record, an error, a
  missing instance, an invalid record (`m2_results.py pending`) or a memory
  death (rerun one bin up) is rerun with the same seed. A run that ended by
  budget, target or watchdog is final.
- **Seeds 4–5 (D1):** the primary ρ is computed on seeds 1–3. If its 95 %
  BCa CI half-width is **> 0.15**, seeds 4 and 5 are run on **every**
  instance of the primary population (whatever its outcome; worst case
  922 CPU-h) and the primary ρ is recomputed on 5 seeds; the 3-seed value is
  reported next to it.

## 6. Secondary, pre-registered: complementarity

1. **2 × 2 table on the primary population:** EvalMaxSAT proved (x finite)
   × memetic reached the optimum in ≥ 1 of 3 seeds (y finite); counts and
   the off-diagonal instances by family.
2. **Complementarity map:** x bands ≤ 1 s, (1, 30], (30, 300], (300, 3600],
   ∞ × y bands ERT ≤ 10 s, (10, 300], (300, 5,400], ∞; counts per cell, per
   track.
3. **Floor share:** the share of runs that reached the optimum in the
   initialisation or the first polish call (`calls_to_target` ≤ 1), per x
   band.

## 7. Interpretation rules (D3)

- **Positive association:** 95 % CI of the primary ρ entirely above 0.
- **Negative association:** entirely below 0.
- **"At most weak" monotone association:** the CI lies inside (−0.3, +0.3).
- Otherwise: inconclusive at this N. No "orthogonal" or "independent" claim
  is made from a non-significant ρ.
- The complementarity counts (§6) are reported whatever ρ shows.

## 8. Replication

MSE 2023 is the replication sample (MSE_PUBLISHED_EXACT_RESULTS.md §6): the
same definitions, with instances also in MSE 2026 removed by content hash.
Its own pre-registration, if run, refers to this document.

## 9. Decisions

- **D1 seeds 4–5:** as in §5, on the primary population.
- **D2:** replaced by the r2 population (user).
- **D3:** as in §7 (recommended, user).
- **D4:** x = EvalMaxSAT CPU ERT; no VBS; ρ against every published solver
  with ERT (§4).
- **Targets (r3, user):** proven optima only, proved by any 2026 exact
  solver; no best-known targets; no 300 s budget.
- **PAR2 (r4, user):** sensitivity analysis §4.7; ERT stays primary;
  EvalMaxSAT memouts and crashes enter PAR2 at 7,200 s.
