# ρ pre-registration: memetic vs exact hardness on MSE 2026 (milestone 4)

> "go, write the rho pre-registration" (user, 2026-10-29)

**Status: DRAFT r2, 2026-10-29.** It becomes binding when the user approves it
and it is committed; the commit hash is then entered here.
- **r1** (commit `dda60a8`): primary = the EvalMaxSAT (30, 3600] s window,
  successes only.
- **r2** (user, 2026-10-29): the primary population becomes **all
  instances**, censored on both axes; the window becomes a sensitivity
  analysis; ρ against every published solver replaces the VBS analysis.

**Blind:** both revisions were written while batch 3c
([`MSE26_3C_RUN.md`](MSE26_3C_RUN.md)) ran on the cluster, before any 3c
record was copied to the workstation or read (`results/mse26_memetic/` did
not exist locally). Anything added after the records are read is labelled
exploratory.

Sources of the conventions: the M2 pre-registration
(`docs/M2_FULL_POOL_READOUT_AND_STATE.md` §1, repo), the MSE design
(`NOTES_2026-10-21_AGENDA_AND_STATS.md` §5, §8.3, §11), the ρ plan
([`MSE26_RHO_PLAN.md`](MSE26_RHO_PLAN.md) §7, §9).

## 1. Question

Across MSE 2026 exact-track instances, do the instances that are hard for an
exact MaxSAT solver also take the memetic long to reach the target? ρ is the
Spearman rank correlation between the two hardness measures, one point per
instance, with failures on either side as tied top ranks. A low ρ, with each
solver reaching instances the other does not, is the "complementary hardness"
result; a high ρ means the two see the same hardness. No direction is
assumed: the tests are two-sided.

## 2. Population

**Frame:** all 1,216 MSE 2026 exact-track instances (Zenodo 21358014; 607
unweighted + 609 weighted). One row each in `scripts/mse26_population.tsv`
(strong tree), written by `scripts/mse26_population.py` from the published
metadata and raw results; counts below are from it.

**The memetic target:**
- the published optimum (`optimal_cost`) where one exists: **952** instances;
- otherwise the **best-known cost** (`best_known_cost`): **249** instances
  **lack a proven optimum** and have a best-known cost (rows with
  `target_kind` best_known in the table); reaching it is reaching the best
  known, not proving optimality;
- **no target: 15** instances, excluded and listed: 4 with infeasible hard
  clauses (every solver, EvalMaxSAT included, answered UNSATISFIABLE:
  pareto-optimal-interpretation-synthesis `1d4d3512`, `21a4f155`,
  `63cb4386`, `bd26740c`) and 11 with no best-known cost (bnn-verification
  4, overcommitted-scheduling 3, traveling-salesman 2, judgment-aggregation 1,
  minimum-weight-dominating-set 1).

**The x side (EvalMaxSAT's published run, one run per instance):**

| EvalMaxSAT outcome | rule | instances |
|---|---|---:|
| proved (OPTIMUM FOUND, verified, the published optimum, CPU ≤ 3,600 s) | x = CPU time | 792 |
| timeout | ERT = ∞ (one run, zero successes): **censored, tied top rank** | 363 |
| memout | non-timeout failure: **excluded and counted** | 39 |
| crash (no answer, no timeout, no memout) | non-timeout failure: excluded and counted | 18 |
| wrong answer (OPTIMUM FOUND unverified or not the optimum) | non-timeout failure: excluded and counted | 0 |
| UNSATISFIABLE (infeasible; no target) | excluded with the no-target instances | 4 |

**Primary population: 1,152 instances** (586 unweighted, 566 weighted):
target present and x finite (792) or censored (360). Of these, 926 have an
optimum target and 226 a best-known target. **Excluded: 64** (57 non-timeout
EvalMaxSAT failures, 4 infeasible, 3 timeouts without a target).

**Runs still missing:** 3c covers the 952 with an optimum (926 of them in the
population). The **226 best-known instances** need a batch **3d** with the
same settings (unpack and census first: the unpack job extracted only the
952), before the primary ρ can be computed.

**Eligibility depends on x and the published metadata only**, never on a
memetic outcome. After the runs, an instance leaves only if it still has
fewer than 3 valid records after the reruns of §5 (listed with the reason).

## 3. The two measures

- **x (exact hardness):** EvalMaxSAT 2026's published **CPU time**, the
  clock MSE 2026 limits and counts (every timeout at CPU 3,600.0 s;
  MSE26_RHO_PLAN.md §9); ∞ for a timeout.
- **y (memetic hardness):** **ERT on the process CPU clock** over seeds 1–3
  (configs/strong/auto.yaml, budget B = 1,800 s, stop at the target):
  - a run **succeeds** iff `stop_reason` is target and `cpu_to_target_s` ≤ B;
    its effort is `cpu_to_target_s` (process CPU from the start: start-up,
    imports, hash, parse, kernel gate, hparams, search);
  - a failed run is charged B;
  - ERT = (sum of the efforts) / (number of successes); **zero successes:
    ERT = ∞, censored, tied top rank**.
- **Budget asymmetry, stated with every result:** 1,800 s for the memetic,
  3,600 s for EvalMaxSAT, on different hardware. Ranks are unaffected by a
  uniform speed factor; the censoring points differ.

## 4. Analyses

**Primary:** Spearman ρ(x, y) on the 1,152 instances, **with midranks** for
ties (all ∞ on an axis share one midrank); **95 % BCa bootstrap CI over
instances, B = 10,000**, seed 20261029. Reported with it: the number of
instances **censored on x only, on y only, and on both**, and the number
excluded (by reason).

**Sensitivity analyses (all reported, none replaces the primary):**
1. **The window, both axes uncensored:** x finite in (30, 3600] s CPU (391
   instances) and y finite (≥ 1 memetic success).
2. **x = EvalMaxSAT wall time** (timeouts still ∞).
3. **Flip-level effort:** y with `cpu_to_target_hit_s` for successes.
4. **Shorter memetic budgets read off the same records:** B = 900 s and
   300 s (success iff `cpu_to_target_s` ≤ B, failures charged B).
5. **Family-stratified bootstrap:** resampling within families.
6. **Partial Spearman ρ** controlling for log n_vars and log n_clauses of the
   original instance (size as a common cause), midranks.
7. **Optimum targets only:** the 926 instances whose target is a proven
   optimum.

**ρ against every published solver (replaces the VBS analysis, user
2026-10-29):** for each solver of the MSE 2026 exact tracks (22 unweighted,
15 weighted), x = that solver's ERT with EvalMaxSAT's rules (proved → CPU;
timeout → ∞; memout, crash or wrong answer → excluded from that solver's ρ
and counted); y and the midrank/BCa method as in the primary; on the primary
population of its track. Reported per track as one figure with CIs, plus a
pooled value for solvers present in both tracks.

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
  1,152 CPU-h) and the primary ρ is recomputed on 5 seeds; the 3-seed value
  is reported next to it.
- **Improvements over the best known:** a run that ends below a best-known
  target is a success like any other; the instance and cost are reported.

## 6. Secondary, pre-registered: complementarity

1. **2 × 2 table on the primary population:** EvalMaxSAT proved (x finite)
   × memetic reached the target in ≥ 1 of 3 seeds (y finite); counts and
   the off-diagonal instances by family, separately for optimum and
   best-known targets.
2. **Complementarity map:** x bands ≤ 1 s, (1, 30], (30, 300], (300, 3600],
   ∞ × y bands ERT ≤ 10 s, (10, 300], (300, 5,400], ∞; counts per cell, per
   track.
3. **Floor share:** the share of runs that reached the target in the
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

- **D1 seeds 4–5:** as in §5, applied to the new primary population.
- **D2:** replaced by the r2 population (user).
- **D3:** as in §7 (recommended, user).
- **D4:** x = EvalMaxSAT CPU; no VBS; ρ against every published solver with
  ERT (§4).
