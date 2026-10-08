# Memetic solver `impl: v2` — why it exists, what changed, how it was checked

**Written:** 2026-10-08. This is the single reference for the v2 implementation
of the memetic solver. It collects what was spread over
`CALIB_2SAT_SC.md` §10b–§10c, `RESEARCH_NOTES.md` N-2026-10-08-h/i and
`cluster_staging_maxsat/DIVERGENCE.md`; those keep short pointers here.

Labels: [verified] means measured or read off code; [inference] follows by a
stated argument; [decision] is a design choice; [quote] is the user's text.

**In one paragraph.**
- **The problem.** The memetic solver's WalkSAT polish (v1, the original)
  does work proportional to the number of clauses m on *every flip*. At
  n = 32 000 a 3.5 s polish call managed only about 300 flips, and in 120 s the
  established arm stayed more than 2000 clauses away from an optimum of 5–13.
- **The fix.** v2 keeps the same algorithm and **makes exactly the same random
  decisions**, but updates its bookkeeping incrementally. It is about 50–1800×
  faster per flip.
- **The result.** With v2, the same arm reaches the optimum at n = 2000 in
  1.2 s and at n = 8000 in 22 s.
- **How to choose.** v1 stays the default and unchanged. v2 is opt-in with
  `impl: v2`.

---

## 1. Why: what v1 measured at large n

### 1.1 Measurement [verified]

The established primary arm `memetic_deeppolish_p40_ls3p5` ran on four
instances whose optimum c\* RC2 had proven. Setup:
- pop 40;
- 3.5 s and 12 500 flips per polish call;
- solver seed 1, stop at the optimum;
- **120 s budget** (a feasibility check, not a time-to-optimum measurement);
- 4 runs in parallel on the workstation.

The instances are random Max-2-SAT, non-batch seeds, from the `calib_2sat_sc`
workstation check (`CALIB_2SAT_SC.md` §10a). Rows are in
`cluster_staging_maxsat/results/workstation_check_calib_2sat_sc/memetic_smoke/`.

| n | m | proven c\* | v1 best after 120 s | generations | children | flips per child (3.5 s) | peak RSS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2000 | 2300 | 3 | 5 | 1 | 35 | ≈ 4800 | 23 MB |
| 8000 | 9600 | 11 | 67 | 1 | 34 | ≈ 1120 | 33 MB |
| 32 000 | 35 200 | 5 | 2250 | 1 | 32 | ≈ 300 | 67 MB |
| 32 000 | 36 800 | 13 | 2563 | 1 | 32 | ≈ 280 | 68 MB |

**The pattern.** The flips achieved per 3.5 s call fall roughly in proportion
to m: a fixed amount of work per clause per flip. Memory was never the problem.

### 1.2 Cause in the code [verified]

`src/sat/walksat.py`, `walksat_polish`, runs a loop
(`while state.flips < max_flips`, line 585). Each iteration does this O(m)
work on the `SatState` (`src/sat/state.py`):

| per flip | where | cost |
|---|---|---|
| `unsat_hard_ids()` to pick a clause | walksat.py:576 → state.py:301 | scans all m clauses |
| `unsat_soft_indices()` to pick a clause | walksat.py:579 → state.py:332 | scans all m clauses |
| `_count_hard_violations()` | walksat.py:596 → state.py:68 | scans all m clauses |
| `snapshot_best_if_better()` → `_count_hard_violations()` + `_soft_objective()` | walksat.py:653 → state.py:321 | two more scans of all m clauses |
| on each improvement: `best_assign = assign.copy()` | state.py:328 | O(n) |

So one flip costs about five passes over m clauses, plus an O(n) copy while
the search is improving. Standard WalkSAT keeps the unsatisfied clauses in an
incremental structure, so a pick costs O(1).

Two further O(m) costs fell on every child of the EA, and became visible once
the polish was fast (profile at n = 32 000):
- `clause_aware_crossover1` rebuilds instance-constant tables (soft proxy
  scores, hard occurrence lists) on every call: about 0.09 s per child.
- `memetic.py` evaluates each child before the polish only to pass the result
  to a no-op LLM advisor.

### 1.3 Consequence [inference]

Under v1, at n ≥ 8000 a memetic "failure" measures this implementation's
per-flip cost, not the instance's difficulty. The memetic half of the selection
rules could not be assessed at those sizes.

## 2. Decision [quote, decision]

The options offered were (`CALIB_2SAT_SC.md` §10b):
1. memetic only at n where v1 works;
2. incremental bookkeeping as a new version;
3. a larger per-call allowance, which would not remove the O(m) factor.

The user chose 2 (2026-10-08):

> go with option 2, make walksat incremental keep possibility to use older version, you can make in new version more optimizations

Design constraints, all held:
- **v1 untouched.** `sat/walksat.py`, `sat/state.py` and `evo/operators.py`
  must stay byte-identical to the repo `src/` copies (`DIVERGENCE.md`).
  Verified IDENTICAL after the change.
- **v1 stays the default.** An absent `impl` key means v1, so every existing
  config runs exactly the historical code.
- **The version is recorded** in every run.

## 3. What v2 changes

Selected by a top-level config key: `impl: v2` (`src/evo/impl_v2.py`). The
ready-made config is
`configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml`: the primary arm plus
`impl: v2`, nothing else changed.

**1. Polish: `src/sat/walksat_v2.py`, `walksat_polish_v2`.** It has the same
arguments and the same return keys as v1.
- **Unsatisfied clauses.** Hard and soft unsatisfied clauses are kept in two
  sorted lists, updated with `bisect` (a C-level search and memmove). The hard
  violation count and the unsatisfied soft weight are counters.
- **Same picks.** v1 picks `rng.choice(sorted list)`, and v2 indexes its
  sorted list with the same single `rng._randbelow(len)` call. Candidate
  shuffles use the same `_randbelow(i + 1)` calls as `rng.shuffle`. So every
  pick, shuffle, noise draw and flip is v1's.
- **Flip effects.** These use per-variable (clause, multiplicity) lists, built
  once per instance and cached on the instance object.
- **Best assignment.** It is kept as a trail of flips since the last
  improvement and undone once at the end, instead of an O(n) copy per
  improvement.
- **Soft-only fast path.** It skips the hard bookkeeping. In the noise branch
  it takes the first shuffled candidate without computing its effect: with no
  hard clauses, v1's `br > 0` test can never skip one.
- **Smoothing.** Clause smoothing is a no-op in v1's polish (nothing raises a
  dynamic weight), so v2 skips it.

**2. Crossover: `clause_aware_crossover1_v2`.** The decision rule is copied
unchanged. The soft proxy scores and hard occurrence lists are built once per
instance.

**3. No-op advisor round trip skipped.** v1 calls a `NoopProvider` advisor,
whose advice is empty and whose `apply_advice` returns an unchanged copy, after
evaluating the child once. v2 skips both, but keeps the one RNG draw that
matters (the advisor's `rng.randrange(1 << 30)`), so the random stream stays
v1's.

**Recording.**
- The EA result gains `impl`.
- Each memetic shard gains `memetic_impl` (`run_memetic_shard.py`, shard
  schema 3, additive).

## 4. Correctness: v2 makes v1's exact decisions [verified]

`cluster_staging_maxsat/tests/test_walksat_v2.py` has 57 tests, all passing.

- **Polish.** With the same start assignment, seed and flip/iteration budget,
  v2 returns **exactly** v1's final assignment, iteration count, applied-flip
  count, objective and hard-violation count. Cases:
  - soft-only 2-SAT and 3-SAT;
  - weighted soft;
  - hard+soft, which exercises the hard-violation branch and its explore
    fallback;
  - heavy duplicate clauses;
  - noise 0.1 and 0.5;
  - `hard_safe` on and off;
  - 3 seeds each.
- **Not vacuous.** About 1000 applied flips per soft case. In the hard case,
  hard violations went from 54 down to 2–3 along the identical path.
- **Crossover.** v2's child equals v1's, soft-only and hard+soft, with both
  fitness orders and a tie.
- **Whole EA.** v1 and v2 runs are identical: same best assignment, total
  flips and generations. One case is soft-only 2-SAT; the other is hard+soft
  3-SAT with the established arm's deadline clipping.
- **The one intended difference.** For a clause with a repeated variable,
  v2's soft gain is exact and v1's is not. There v2 is checked against a
  from-scratch recount.
- **Why the tests use a tick clock.**
  - v1 counts only *applied* flips against `max_flips`. On a hard-clause
    instance where no candidate may flip, a polish call loops until its time
    limit.
  - v2 keeps that behaviour.
  - The tests replace `time.time` with a clock that ticks once per call. Both
    versions read it once per iteration, so a time limit becomes an identical
    iteration limit.
- **The rest of the code.**
  - The full staging suite passes: 231 passed, 3 skipped.
  - The eight `DIVERGENCE.md`-frozen files are IDENTICAL to the repo copies.

## 5. Speed [verified, workstation]

A polish call from a random start, with the established limits (12 500 flips,
3.5 s). "Uncapped" means v2 with the flip limit lifted, 3.5 s only.

| n | m | v1 flips/s | v2 flips/s | v2 uncapped flips/s | a 12 500-flip call, v2 |
|---:|---:|---:|---:|---:|---:|
| 2000 | 2200–2300 | ≈ 5 100 | ≈ 600 000 | ≈ 640 000 | 0.02 s |
| 8000 | 9600 | 961 | ≈ 508 000 | — | 0.03 s |
| 32 000 | 36 800–38 400 | 149–234 | ≈ 260 000 | ≈ 480 000–510 000 | 0.05 s |

Reproduce on any instances (workstation only):

```
cd cluster_staging_maxsat
python3 scripts/bench_walksat_v1_v2.py data/generated/calib_2sat_sc_smoke/*.wcnf
```

On those two shipped smoke instances (2026-10-08):
- n = 2000: v1 5 234/s, v2 604 722/s.
- n = 32 000: v1 234/s, which left 8452 unsatisfied clauses after the call;
  v2 261 016/s, which left 443.

**Memetic smoke, v1 against v2.** Same instances, arm, seed and 120 s as §1.1.
v2 rows are in `…/memetic_smoke_v2/`.

| n | proven c\* | v1 best (120 s) | v2 result | v2 generations | v2 peak RSS |
|---:|---:|---:|---|---:|---:|
| 2000 | 3 | 5 | **optimum in 1.2 s** | 2 | 25 MB |
| 8000 | 11 | 67 | **optimum in 22.2 s** (RC2: 161 s) | 11 | 39 MB |
| 32 000 | 5 | 2250 | 14 at 120 s | 44 | 86 MB |
| 32 000 | 13 | 2563 | 25 at 120 s | 41 | 86 MB |

These are 1-seed workstation smokes. They show that v2 searches meaningfully
at these sizes. They are not a measurement of the instances' memetic
difficulty.

## 6. Consequences for measurements [decision, inference]

- **Seconds are comparable only within one `impl`.**
  - Under a flip budget, v1 and v2 produce identical runs.
  - Under the per-call time limit, v2 does far more work per second, so
    results differ as they would on a much faster machine.
  - Every memetic result before 2026-10-08 is v1 (M2 pool, uuf ablation,
    calib_c plans) and stays labelled v1.
  - A cross-version comparison either re-runs the instances under v2 or states
    the version boundary.
- **Which version to use.** v2
  (`memetic_deeppolish_p40_ls3p5_v2.yaml`) for any memetic assessment of the
  large-n `calib_2sat_sc` cells.
- **The flip budget now binds before the time limit.** Under v2 the
  established 12 500 flips per call are used up in about 0.05 s at
  n = 32 000. Whether larger n should get a larger flip budget is a
  configuration question. It is unchanged here, so the arm stays the
  established one.
- **The repo `src/` tree is not updated.** v2 exists only in the staging tree,
  like the other staging-ahead changes (`DIVERGENCE.md`).

## 7. Files

| file | role |
|---|---|
| `cluster_staging_maxsat/src/sat/walksat_v2.py` | v2 polish |
| `cluster_staging_maxsat/src/evo/impl_v2.py` | `impl` switch; v2 polish wrapper; v2 crossover |
| `cluster_staging_maxsat/src/evo/memetic.py` | selects polish and crossover by `impl`; v2 skips the no-op advisor round trip; result key `impl` |
| `cluster_staging_maxsat/src/cli/run_memetic_shard.py` | shard schema 3: `memetic_impl` |
| `cluster_staging_maxsat/configs/tier2/memetic_deeppolish_p40_ls3p5_v2.yaml` | primary arm + `impl: v2` |
| `cluster_staging_maxsat/tests/test_walksat_v2.py` | equivalence tests |
| `cluster_staging_maxsat/scripts/bench_walksat_v1_v2.py` | the throughput comparison of §5 |
| `cluster_staging_maxsat/results/workstation_check_calib_2sat_sc/memetic_smoke{,_v2}/` | the §1.1 and §5 rows |
| unchanged, v1: `src/sat/walksat.py`, `src/sat/state.py`, `src/evo/operators.py` | byte-identical to the repo copies |
