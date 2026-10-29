# ρ pre-registration: memetic vs exact hardness on MSE 2026 (milestone 4)

> "go, write the rho pre-registration" (user, 2026-10-29)

**Status: DRAFT, 2026-10-29.** It becomes binding when the user approves it
and it is committed; the commit hash is then entered here. Written while batch
3c ([`MSE26_3C_RUN.md`](MSE26_3C_RUN.md)) runs on the cluster: **no 3c record
had been copied to the workstation or read** (`results/mse26_memetic/` did not
exist locally when this was written). Everything below that depends on 3c
records is fixed before they are read; any analysis added afterwards is
labelled exploratory.

Sources of the conventions: the M2 pre-registration
(`docs/M2_FULL_POOL_READOUT_AND_STATE.md` §1, repo), the MSE design
(`NOTES_2026-10-21_AGENDA_AND_STATS.md` §5, §8.3, §11), the ρ plan
([`MSE26_RHO_PLAN.md`](MSE26_RHO_PLAN.md) §7, §9).

## 1. Question

Across MSE 2026 instances with a proven optimum, do the instances that are
hard for an exact MaxSAT solver also take the memetic long to reach the
optimum? ρ is the Spearman rank correlation between the two hardness
measures, one point per instance. A low ρ with each solver reaching
instances the other does not is the "complementary hardness" result; a high
ρ means the two see the same hardness.

No direction is assumed: the tests are two-sided.

## 2. Sample

- **Frame:** the 952 MSE 2026 exact-track instances with a published optimum
  (`benchmark-metadata.csv` `optimal_cost`; Zenodo 21358014): 479
  unweighted, 473 weighted. All run in 3c.
- **Eligibility is decided by x alone** (never by a memetic outcome).
- **Primary window:** EvalMaxSAT proved the optimum (`answer` OPTIMUM FOUND,
  `verified` 1) with **CPU time in (30, 3600] s**: **391 instances** (200
  unweighted, 191 weighted; 12 families with ≥ 10). Counted from the
  published data, 2026-10-29.
- **Outside the window, pre-registered as secondary (§6):** EvalMaxSAT CPU
  ≤ 30 s (401: 171 ≤ 1 s, 230 in (1, 30]) and not proved by EvalMaxSAT in
  3,600 s CPU (160).
- **Exclusions after the run (data integrity only):** an instance leaves the
  analysis only if, after the reruns of §5, it still has fewer than 3 valid
  records; it is listed with the reason. A `cost_mismatch` record is invalid
  and investigated. Nothing else removes an instance.

## 3. The two measures

- **x (exact hardness):** the published EvalMaxSAT 2026 **CPU time**
  (`cpu.time`), the clock MSE 2026 limits and counts (every timeout at CPU
  3,600.0 s; MSE26_RHO_PLAN.md §9).
- **y (memetic hardness):** **ERT on the process CPU clock**, over seeds 1–3
  (configs/strong/auto.yaml, budget B = 1,800 s, stop at the published
  optimum):
  - a run **succeeds** iff `stop_reason` is target and `cpu_to_target_s` ≤ B;
    its effort is `cpu_to_target_s` (process CPU from the start: start-up,
    imports, hash, parse, kernel gate, hparams, search);
  - a failed run is charged B = 1,800 s;
  - ERT = (sum of the efforts over the seeds) / (number of successes); an
    instance with no success has no ERT.
- **Budget asymmetry, stated with every result:** 1,800 s for the memetic,
  3,600 s for EvalMaxSAT, on different hardware. Ranks are unaffected by a
  uniform speed factor; the memetic's success rate is capped by its shorter
  budget.

## 4. Analyses

**Primary:** Spearman ρ(x, y) on the primary-window instances with ≥ 1
memetic success; **95 % BCa bootstrap CI over instances, B = 10,000**, seed
20261029.

**Sensitivity analyses (all reported, none replaces the primary):**
1. **Zero-success instances top-tied:** primary window, instances with 0/3
   given y tied at the top rank.
2. **x = VBS CPU time:** the fastest verified published solver per instance
   (no censoring on the exact side; 947 of 952 proved); same window rule on
   the VBS time.
3. **x = EvalMaxSAT wall time.**
4. **Unproved instances in, x censored:** the 160 not proved by EvalMaxSAT
   enter with x tied at the top rank, with sensitivity 1's y rule.
5. **Flip-level effort:** y with `cpu_to_target_hit_s` for successes.
6. **Shorter memetic budgets read off the same records:** B = 900 s and
   300 s (success iff `cpu_to_target_s` ≤ B, failures charged B).
7. **Family-stratified bootstrap:** resampling within families, so the large
   families (asp-optimization 32, planning-hplus 19, …) cannot carry the CI.
8. **Partial Spearman ρ** controlling for log n_vars and log n_clauses of the
   original instance (size as a common cause).

**Breakdowns (descriptive, CIs shown, no tests):** per track (unweighted,
weighted); per family with ≥ 10 primary-window instances; ρ of y against
each published solver's CPU time (22 unweighted, 15 weighted solvers), as one
figure.

## 5. Running rules (fixed before results are read)

- **Reruns are for infrastructure only:** a task with no record, an error, a
  missing instance, an invalid record (`m2_results.py pending`) or a
  memory death (rerun one bin up) is rerun with the same seed. A run that
  ended by budget, target or watchdog is final.
- **Seeds 4–5 [decision D1 below]:** the primary ρ is computed on seeds 1–3.
  If its 95 % BCa CI half-width is **> 0.15**, seeds 4 and 5 are run on
  **every** primary-window instance (whatever its outcome) and the primary ρ
  is recomputed on 5 seeds; the 3-seed value is reported next to it.
- **Window and every threshold above are on x only and are frozen here.**

## 6. Secondary, pre-registered: complementarity

1. **2 × 2 table on all 952:** EvalMaxSAT proved within 3,600 s CPU (yes/no)
   × memetic reached the optimum in ≥ 1 of 3 seeds within 1,800 s CPU
   (yes/no); counts and the instances in the two off-diagonal cells by family.
2. **Complementarity map** (instances enter by x alone, `NOTES…` §11 option
   2): x bands ≤ 1 s, (1, 30], (30, 300], (300, 3600], not proved × y bands
   ERT ≤ 10 s, (10, 300], (300, 5,400], no success; counts per cell, per track.
   The ≤ 30 s bands answer "easy to prove, hard to search".
3. **Floor share:** the share of runs that reached the optimum in the
   initialisation or the first polish call (`calls_to_target` ≤ 1), per x
   band, so ties at the memetic's floor are visible next to every ρ.

## 7. Interpretation rules (fixed now)

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

## 9. Open decisions for the user (before approval)

- **D1 seeds 4–5:** the rule in §5 (precision-triggered, all window
  instances). Recommended: as written. Alternatives: never (3 seeds only), or
  always (5 seeds on the window, ≤ 391 CPU-h more in the worst case).
- **D2 the ≤ 30 s instances:** secondary map (§6.2), as recommended in
  NOTES §11 (option 2). The alternative is a primary window of (0, 3600] s.
- **D3 interpretation thresholds** (§7): ±0.3 for "at most weak".
- **D4 x primary:** EvalMaxSAT CPU (as decided 2026-10-29), VBS as
  sensitivity (§4.2).
