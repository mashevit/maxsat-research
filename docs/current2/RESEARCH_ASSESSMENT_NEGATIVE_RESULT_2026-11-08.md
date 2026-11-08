# Research assessment, 2026-11-08: the MSE 2026 complementarity analysis is a negative result

**Created:** 2026-11-08. **Research note** N-2026-11-08-a (indexed in
[`../current/RESEARCH_NOTES.md`](../current/RESEARCH_NOTES.md)).
**Status: [decision] (user), with [verified] pointers and [inference].**
This note **supersedes the interpretation** in the notes and documents listed in
§3. It does not change any number in them.

> "Please update the project's research notes to reflect our current assessment:
> **we regard the latest analysis as a negative result—a failure to establish the
> intended research contribution.**
>
> Our memetic solver outperforms another solver on some instances, but such
> instance-specific wins may also occur between existing solvers. Therefore, the
> mere existence of complementary successes does not establish that our method
> offers a distinctive or practically valuable contribution.
>
> Do not present the 44 instances or the low correlation in the selected hard
> subset as sufficient evidence of research success. Preserve the numerical
> findings, but distinguish them from the stronger interpretation that they do
> not currently support.
>
> A convincing contribution would require evidence that our method adds value
> beyond reasonable alternatives, such as another existing solver or local search
> with restarts, under comparable computational budgets and evaluation criteria.
> Reaching an optimum must also remain distinct from proving optimality.
>
> Until such evidence is available, describe the latest findings as insufficient
> to support our intended contribution, rather than as a successful demonstration
> of useful complementarity. This assessment concerns the current research claim,
> not the correctness of all previous implementation work or measurements."
> (user, 2026-11-08)

## 1. The assessment

- **[decision]** The MSE 2026 analysis (batch 3c; ρ readouts 1–3; the
  complementarity tables) is a **negative result**: it does **not** establish the
  intended research contribution.
- **[decision]** The findings are **insufficient** to show that the memetic solver
  offers a distinctive or practically valuable contribution. They are **not** a
  successful demonstration of useful complementarity.
- **Scope.** This judges the current research *claim*. It does not question the
  implementation work, the measurements, the error handling or the computed
  statistics, which stay as recorded.

## 2. What stays: the numbers (unchanged, [verified] where first recorded)

All from readout 3, [`MSE26_RHO_RESULTS_3.md`](MSE26_RHO_RESULTS_3.md), `fail`
column unless stated. "Reached" = the memetic hit the known proven optimum on
≥ 1 of 3 seeds; "proved" = EvalMaxSAT's published 2026 run proved the optimum.

| finding | value | where |
|---|---|---|
| primary ρ (EvalMaxSAT proof CPU vs memetic ERT) | +0.637 [+0.588, +0.680], N 922; `exclude` +0.632, N 884 | §3 |
| window (30, 3600] s, both solved | +0.223 [+0.078, +0.362], N 184 | §3 |
| E4 (x > 30 s incl. timeouts, not both failed; exploratory, outcome-defined) | +0.064 [−0.037, +0.161], N 435; `exclude` +0.039 | §5 |
| who solved what (N 922) | both 530 (57.5 %), only EvalMaxSAT 262 (28.4 %), only memetic 44 (4.8 %), neither 86 (9.3 %) | §4.1 |
| coverage, EvalMaxSAT alone → EvalMaxSAT or memetic | 85.9 % → 90.7 % (≥ 1-seed counting) | §4 |
| memetic reach by EvalMaxSAT band | 97 % → 78 % → 59 % → 36 % | prelim §10.3 |
| the 44 memetic-only instances | all proved by ≥ 1 other published 2026 solver | prelim §10.4 (N-2026-10-29-b, then 43) |
| vs Aperture (MSE 2026 anytime winner), 135 shared instances | memetic better than every variant on 7; never better than the best verified anytime result | [`MSE26_MEMETIC_VS_APERTURE.md`](MSE26_MEMETIC_VS_APERTURE.md) |

These numbers may be reported. What they may **not** carry is the interpretation
in §3.

## 3. What is withdrawn: the interpretation

The following statements went further than the evidence. They stay in their
documents as the record (append-only rule), each now with a dated pointer here.

| where | statement | status from 2026-11-08 |
|---|---|---|
| N-2026-11-01-g; `MSE26_RHO_RESULTS_3.md` §4.2 | "its contribution is complementarity, not strength"; "the defensible claim is a useful portfolio partner for a state-of-the-art exact solver on its hard tail" | **not supported.** Not a contribution claim we can make now. |
| N-2026-11-01-e; `RESEARCH_NOTES_COMPLEMENTARITY_VS_ORTHOGONALITY.md` | "For the paper: claim complementarity" | **not supported.** The definitions in that note remain valid; the claim for the paper does not. |
| `MSE26_RHO_RESULTS_3.md` §6 point 3; prelim §10.1 point 3; N-2026-10-29-b | "partly complementary"; "the memetic adds a third of EvalMaxSAT's timeouts"; "combining the two lifts coverage to 90.7 %" | **numbers stay; read as a description of one pair of solvers, not as evidence of value.** |
| N-2026-11-01-a / -b; complementarity note §4 | E4 ≈ 0 "is complementarity as a rank statistic" | **not evidence of success.** E4 is a selected, outcome-defined subset; its low ρ follows from which solver fails there. |
| N-2026-11-03-a; `RESEARCH_NOTES_VBS_PRECEDENTS_AND_NOVELTY.md` | "Novel = the measurement at MSE scale" | **a novel measurement is not a demonstrated contribution.** The literature finding (no MaxSAT precedent found) stays. |
| `NEXT_SESSION_CONTEXT.md` r22 | next: a paper framed as complementarity | **this framing is superseded.** What to do next is the user's decision. |

## 4. Why the current evidence is insufficient

1. **Instance-specific wins are not distinctive** [inference]. Two different
   solvers almost always each solve some instances the other does not. The 44
   memetic-only instances show that this pair differs; they do not show that the
   memetic adds more than any other existing solver would. **No baseline was
   computed**: the "only X" counts and the virtual-best gain for EvalMaxSAT paired
   with each *other* published 2026 solver. The published 2026 per-solver results
   are on disk (`MSE26_RHO_PRELIM_RESULTS.md` §7 uses them for ρ), so this
   baseline can be computed. It has not been.
2. **Nothing new against the field** [verified]. Every one of the memetic-only
   instances was proved by at least one published 2026 solver (N-2026-10-29-b). On
   the 135 instances shared with the anytime track, the memetic never beats the
   best verified anytime result (N-2026-11-01-i). Against the virtual best of the
   existing solvers, the memetic adds no instance. This holds by construction:
   the population contains only instances whose optimum a published solver
   proved (prereg r3), so the study could not have shown new instances.
3. **No local-search-with-restarts baseline** [verified: not run]. The memetic
   has never been compared with its own local search restarted from random or
   Glucose starts under the same budget. Earlier observations point the other
   way: "multistart may be enough" (N-2026-10-11-c), and on small kernels "the
   population mostly acts as a multistart" (`KERNEL_MEMETIC_RUN.md`).
4. **Budgets and criteria are not comparable** [verified, from the prereg and
   N-2026-11-01-g]:
   - the memetic is **given the proven optimum as its stop target** (oracle
     stop) and stops when it reaches that cost; EvalMaxSAT must find the optimum
     and prove it without being told it;
   - the memetic gets **3 seeds × 1,800 s CPU**, counted as solved if **any**
     seed reaches the target; EvalMaxSAT gets **one** run of 3,600 s CPU. The
     ≥ 1-seed counts are best-of-runs counts, which overstate a randomised
     solver (Cameron, Hoos & Leyton-Brown, IJCAI 2016; N-2026-11-03-a); an
     expected-success re-count was proposed and not computed;
   - different hardware (our cluster vs the MSE 2026 runs).
5. **Reaching is not proving** [verified]. The memetic certifies nothing. A
   "memetic-only" instance is one where the memetic reached a cost that someone
   else had already proved optimal. Without that external proof, the memetic's
   run would not show it had found the optimum.
6. **The low correlation is in a selected subset** [inference, as already
   recorded in N-2026-11-01-b]. The window ρ (+0.22) and E4 (≈ 0) come from
   subsets chosen by EvalMaxSAT's time or by the outcomes. In E4, 58 % of the
   instances are tied at a failure rank, so ρ mostly records which solver failed.
   Weak or zero association in such a subset does not show that the memetic is
   useful.

## 5. What would establish a contribution (criteria, not a plan)

These are the conditions under which a contribution claim could be made. None of
them is scheduled; whether and how to pursue them is the user's decision.

- **Beyond existing solvers.** The memetic's marginal gain (coverage, PAR2, or
  anytime cost at fixed times) to a portfolio of existing solvers must exceed the
  gain from adding a reasonable existing alternative (another published exact or
  anytime solver), measured the same way. At minimum: its memetic-only count must
  be placed in the distribution of "only X" counts for the existing pairs.
- **Beyond local search with restarts.** The memetic must beat its own local
  search with restarts (same code, same starts, same polish, no population or
  crossover) under the same budget.
- **Comparable budgets and criteria.** Equal total CPU (or an explicit
  per-seed rule), the same hardware where possible, **no oracle stop** for the
  anytime side (judge the best cost found by time t against the known optimum
  afterwards), and expected-success rates rather than best-of-seeds counts.
- **Reaching kept apart from proving.** Every table must label "reached a known
  optimum" and "proved optimal" separately. A memetic reach never counts as a
  proof, and a coverage figure that mixes the two must say so.

## 6. Wording rules from 2026-11-08

- **Do not write:** "the memetic's contribution is complementarity"; "a useful
  portfolio partner"; "adds value on the hard tail"; "successful demonstration";
  or any wording that presents the 44 instances, the 85.9 → 90.7 % coverage, the
  window ρ or E4 as evidence of research success.
- **Do write, e.g.:** "On 44 of 922 MSE 2026 instances the memetic reached the
  known optimum (≥ 1 of 3 seeds, 1,800 s each, stopping at the given target)
  where EvalMaxSAT's published 3,600 s run did not prove one. All 44 were proved
  by another published solver. Whether the memetic adds more than an existing
  solver or local search with restarts under a comparable budget has not been
  tested; the current results are insufficient to support the intended
  contribution."
- Earlier rules still hold: no "orthogonal / independent" from a non-significant
  ρ (prereg §7; N-2026-11-01-b); "reaches", never "solves" or "proves", for the
  memetic unless "solved" is defined as reached in the same sentence.
