# calib_b — summary

**Date:** 2026-09-22. One-page summary of the calib_b round (B1, RC2 grid
refinement). Read this first; the detail is in three places:

- [`CALIB_B_PLAN.md`](CALIB_B_PLAN.md) — the plan, written before any calib_b
  instance existed, now carrying a status header
- [`CALIB_B_B1_READOUT.md`](CALIB_B_B1_READOUT.md) — the full read-out
- [`CORPUS_CALIBRATION_LOG.md`](CORPUS_CALIBRATION_LOG.md) — Checkpoint 4

---

## What B1 achieved

**The round did what it was run to do.** Pooled calib_a ∪ calib_b,
deduplicated on `instance_sha256`:

| | after A1 | after B1 |
|---|---:|---:|
| certified | 92 | 177 |
| **Tier-2 eligible (60–600 s)** | **10** | **46** |
| cells holding one | 6 | 21 |
| rows holding one | 5/9 | 8/9 |
| largest single-cell share | 30 % | 9 % |

Plan §7's stop condition was "≥ 40 across ≥ 8 cells, spread not piled" — the
result is 46 across 21 cells, median 159 s, Q1/Q3 111/240 s. **α refinement is
closed; no calib_c.**

Clean and cheap: 110/110 rows, **0 failed**, uniform PySAT 1.9.dev3 identical
to A1 (so §6's pooling precondition *held*, rather than being assumed),
**10.0 CPU-h of the 29.3 budgeted**.

## Taken into account in the write-up

**The plan scored against itself.** The c\* model is validated — predicted c\*
landed inside the observed range in **16/17** exploratory cells. The *time*
model is not: within 3× in only **12/17**, errors in both directions up to
30×. Placing two α per row is what absorbed that. All 5 reinforcement cells
held and supplied **15 of the 46** from a quarter of the tasks.

**The one structural finding.** A row's yield is set by
`d log10(solve_s)/dc*`, not by α placement. The window is one decade wide, so
a row holds about `1/slope` integer c\* values. 3-SAT n = 150 sits at
1.39 dec/c\* — c\* = 2 proves in 15 s, c\* = 3 in 772 s — so **the window falls
between two integers**. Four α values across both batches yielded zero there;
a fifth cannot help. Checkpoint 3's smoke run flagged exactly this cell and
kept it anyway because "trivial outcomes locate edges" — that call is what
produced the finding.

**The cell-rule / instance-eligibility separation earned its keep.** 18
batch-cells now pass §5.3, but **13 of the 46 eligible instances sit outside
passing cells** — selecting by cell and then filtering by instance would
discard a quarter of what is available.

Also now disjoint and quantified: 2-SAT eligible instances span c\* 18–35,
3-SAT span c\* 1–11. **No overlap.**

## Three open items, now decidable

1. **30 s floor — recommend *not* adopting.** Would give 46 → 70, but at 46
   the 60 s floor is no longer binding. Keep it as a sensitivity column.
2. **600–900 s rescue — recommend adopting, labelled.** 46 → 54, existing
   `include_solved_t3` behaviour, fills the empty 450–600 s shoulder (thinned
   by the cap, not by the instances), and is the only route to any 3-SAT
   n = 150 instance.
3. **What M2 runs on.** The certified pool doubled to 177, so M2 as specified
   is now 531 tasks / ≤ 133 CPU-h. Recommend the **≥ 30 s certified set: 210
   tasks, ≤ 52 CPU-h** — covers every eligible instance, keeps margin for
   §5.2's attenuation, and costs less than the original estimate. This changes
   M2's manifest builder.

**Items 2 and 3 are what M2's manifest is built from, so they are the gate.**
