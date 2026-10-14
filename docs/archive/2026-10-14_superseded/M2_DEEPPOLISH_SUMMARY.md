# M2 modified deeppolish: handout summary

**Date:** 2026-09-24. This is a one-page summary of
[`M2_DEEPPOLISH_HANDOUT.md`](M2_DEEPPOLISH_HANDOUT.md), written against commit
`98fbd38`. The handout was a documentation stage only. No code, configs or
manifests were changed, and no jobs were submitted.

---

## Population: 70 instances confirmed

All 290 RC2 rows were rechecked directly, including recomputing every
instance file's hash. All 290 are distinct, 177 are certified, and none
failed.

- **Groups:** 16 in 30–60 s (all labelled T1), 46 in 60–600 s (37 T2a, 9
  T2b) and 8 in 600–900 s (all T3). That gives 210 runs and a 52.5 CPU-h
  solver-budget ceiling, or 56.0 CPU-h with the 60 s grace.
- **Boundaries:** no instance sits exactly on 30, 60 or 600 s, so the
  choice between `<` and `≤` changes nothing.

## Errors in the source documents, corrected in the handout

- The "24-instance margin below the window" is really 16 below and 8 above.
- The 600–900 s extension does not fill the 450–600 s band. That band still
  holds 0 of 70 instances, and the 900 s cap does not explain why.
- With the 30 s floor, 3-SAT n = 150 gets a second instance (34.9 s), so
  the upper band is no longer its only route in.
- "No α setting can work" really means low yield was observed; it is not
  proof.

## The "WalkSAT" component

It is `short_polish` → `walksat_polish` in `src/sat/walksat.py`: a focused
random walk with noise 0.10, with no tabu list and no clause weighting.

## The time-limit hypothesis is confirmed

- **Scope:** the 12,500-flip limit applies to each local-search call, which
  means once per child. There are 38 children per generation.
- **Cluster evidence:** in the 130 earlier `memetic_deeppolish` runs, flips
  per call had a median of 2,172 (range 1,486–3,118), and none reached
  12,500. Every call on the time-capped runs took 0.503 s, so the 0.5 s
  allowance (`ls.time_limit_s`) is what stops them.
- **Cause:** each flip scans the whole clause list several times, so a flip
  costs more on instances with more clauses.
- **Local measurement:** on the workstation, scaled to cluster speed, 0.5 s
  allows only about 2,100–6,300 flips across all nine instance groups. The
  ~2,500 figure fits the largest instances (about 900–1,100 clauses).
- **Which runner:** the cluster copy in `cluster_staging_maxsat/` is
  authoritative. The repo's own `src/evo/memetic.py` has no
  stop-at-optimum and must not be used.

## A blocking defect for longer calls

The 900 s deadline is only checked between generations. At 2.5 s per call,
one generation can take 40–110 s, so runs that don't reach the optimum would
hit the 960 s watchdog and be recorded as failures. The proposal is an opt-in
change: each call's allowance is cut to the time remaining, and the deadline
is checked after every child. The original config's behaviour stays
unchanged.

## Proposal

- **New config:** `memetic_deeppolish_ls2p5`, with 2.5 s per call, 12,500
  flips per call and the 900 s budget. By estimate the flip limit starts to
  bind in about 1–2.9 s, so 2.5 s may still be too short for the 3-SAT
  n = 250 instances (about 1,070–1,090 clauses).
- **New fields in each run record:** flips per call, local-search time per
  call, why each call stopped, number of calls and generations, and a hash of
  the solver code. The cluster copy is not a git repo, which is why that hash
  is needed.
- **Pilot:** 10 instances covering all nine size groups and all three time
  bands, both allowances, and the same three solver seeds for both: 60 runs
  and at most 15 CPU-h. The handout sets out pass/fail criteria for run
  integrity, for which limit stops each call, and a guard against the new
  setting doing worse. It also says what happens after each outcome.
- The handout also lists the files to change, the rsync/sbatch commands, the
  missing resume logic in the memetic array script, and the split between
  calibration results and the later fresh-seed corpus.

## Decisions for the user

1. Approve the pilot as specified (10 instances, 60 runs), or change the
   instance list.
2. Whether to add a 3.5 s arm now on the two largest-clause-count instances
   (+6 runs). This saves a round trip if 2.5 s turns out too short for them.
3. Approve the opt-in deadline clipping. Without it, the longer allowance
   cannot run within 900 s without watchdog failures.
4. Approve the acceptance criteria in §7.3 of the handout.

After approval, the next step is implementing and testing these changes and
preparing the pilot for submission.
