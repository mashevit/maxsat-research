# Generator pilot — what changed, in brief

**Date:** 2026-09-14. Companion to [`CORPUS_GENERATOR_PLAN.md`](CORPUS_GENERATOR_PLAN.md),
which holds the full plan and tables. This note is the summary of what the
pilot established and how it revises the earlier documents.

## What was done beyond writing the plan

A small RC2 pilot was run — 25 generated instances, 60 s cap — using the
existing `instancegen` package, because the plan needed real numbers on where
the generator dial lands under a core-guided oracle. Rows are in
`results/profile/gen_pilot_cap60.jsonl`. The results change two things in the
earlier docs:

- **Handoff F1 ("ratios 5, 6, 8 at n=100–200 put c\* in the tens") is wrong
  for RC2.** At n ≥ 100, m/n = 6 is already over the cap; the cliff is at
  c\* ≈ 10 for random 3-SAT (n=50: c\*=6 in 3 s, c\*=10 in 53 s, nothing above
  finished). That is the same mechanism that makes the MSE-2016 random
  families (m/n 6–22) hopeless: one core per unit of cost.
- **Binary-clause families are where the c\* spread comes from.** Max-2-SAT at
  n=100, m/n=4 gave c\*=25 in 5.5 s; the crafted `p_hat300-1` gave c\*=49 in
  22 s. So MaxCut / Max-2-SAT generators are not optional — they are the only
  way to populate the c\* ≥ 20 decade. The reachable range is ~2 decades, not
  the 3 that `CORPUS_MSE2016_ASSESSMENT.md` §5.1 targeted; the plan says to
  state that as a limitation.

## One correction to the premise

The MSE-2016 `ms_*` instances are not anytime-track — 2016 had no incomplete
track; they were the complete track, solved by branch-and-bound solvers. They
are too hard for the *OLL oracle this paper uses* (RC2 and EvalMaxSAT both),
which is the accurate phrasing for a referee. The conclusion holds either way:
do not build the corpus on them. The small crafted `dimacs-mod` / `spinglass`
leaves are worth keeping as the structured stratum, since they certify in T1.
Details in `CORPUS_GENERATOR_PLAN.md` §1.2–1.3.

## The steps (plan §4)

0. Format and manifest already frozen (`instancegen.wcnf_io`, dialect `old`).
1. Three small generator modules (`maxcut`, `reweight`, `planted`) plus a CLI,
   all behind the existing writer.
2. Verification harness with the cost-semantics assertion (bipartite MaxCut
   c\* = 0, K_n closed form, planted k-SAT c\* = 0).
3. Calibration: Phase A on the workstation at 120 s, Phase B on the cluster at
   900 s, ~480 tasks.
4. Pick cells by T2 yield into a committed grid file.
5. Bulk generate, certify per instance, produce and certify weighted twins.
6. Feed `make_tier2_manifest` unchanged.
7. Regression-based analysis, ρ within strata and pooled with CIs.

## Decisions to make before Step 3 (plan §5)

| # | Question | Recommendation |
|---|---|---|
| E1 | Certification cap | 900 s, matching `uuf250_1000c` |
| E2 | Accept the two-decade c\* ceiling | Yes — state as a limitation of a core-guided oracle |
| E3 | Hard clauses in corpus v1 | No — feasibility wall; the EA arm is pure-soft |
| E4 | Which MSE-2016 leaves to keep screening | `dimacs-mod`, `spinglass`, `set-covering/*` only |
| E5 | Weight shapes for the reweight twins | `uniform` w_max 8 and `few_classes:5` w_max 16 |
