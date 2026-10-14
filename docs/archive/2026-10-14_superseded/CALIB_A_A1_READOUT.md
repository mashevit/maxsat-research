# calib_a — A1 read-out (RC2 arm, before M2)

Read-out of **A1**, the RC2 profiling run over the `calib_a` grid
(`instancegen/grids/calib_a.yaml`: 36 cells × 5 seeds = 180 instances,
cap 900 s + 60 s grace, `RC2(wcnf, solver="g3")`, PySAT 1.9.dev3 on the
cluster — see `CORPUS_CALIBRATION_LOG.md` Checkpoint 2 for the version
note). Source: `cluster_staging_maxsat/results/profile_calib_a_all.jsonl`
(180 rows, one per instance; §4.4 classes: 92 completed, 88 censored at the
budget, 0 failed).

This is the RC2 half of the §5.1 yield table, produced now because M2's
manifest is built from it. It contains **no ρ and no memetic column**; those
are M3 (`calib_summary.py`, `docs/CALIB_A_RESULTS.md`). Every statement
below is conditional on this grid, this cap and this solver configuration
(§1 of the goals doc).

## 0. Summary — the findings that matter for what is decided next

**The strip exists and is diagonal (H3 confirmed), but it is one grid step
wide.** In every (n, k) row the outcome flips from 5/5 completed to 0/5
censored across a single α step, and in 5 of the 9 rows the crossing falls
*between* grid lines — the grid catches nothing informative there. Where it
does catch a cell:

| k | n | informative cell | certified | median RC2 |
|---|---|---|---|---|
| 2 | 150 | α = 3 | 4/5 | 20 s |
| 2 | 400 | α = 2 | 5/5 | 17 s |
| 3 | 50 | α = 8 | 5/5 | 66 s |
| 3 | 70 | α = 6 | 5/5 | 53 s |
| 3 | 250 | α = 4.26 | 4/5 | 166 s (c\* ∈ {0, 1}) |

Those 5 cells pass the RC2 half of the proposed §5.3 rules (≥ 4/5
certified, median ≥ 10 s). Three more miss narrowly: 2-SAT n = 100 α = 4
(median 8 s), 3-SAT n = 100 α = 5 (5.6 s), 3-SAT n = 150 α = 5 (3/5).
Everything else is either sub-3-second or fully censored.

**What RC2 time actually tracks is c\*** — the wall is at c\* ≈ 10 for
3-SAT and c\* ≈ 25–50 for 2-SAT. So the two families will occupy different
c\* decades in the corpus (1–11 vs 12–50).

**Cap 900 s is placed at the wall** (2 completions in 600–900 s, then 88
censored with large LB gaps). Not worth raising for calib_a.

**M2 subset: 92 instances, but 70 are RC2-trivial (< 10 s), 52
sub-second.** The ρ(RC2, memetic) read-out will have real resolution on
≈ 22–40 instances only. That is the attenuation §5.2 predicted, now
quantified.

**The decision this raises.** The plan already provides a `calib_b`
α-refinement round for exactly this case (goals §3). §4 below lists the α
values to insert (e.g. 2-SAT n = 100 α ∈ {4.5, 5}, n = 150 α = 3.5,
n = 250 / 400 α = 2.5; 3-SAT n = 100 α = 5.5, n = 150 α ∈ {4.6, 5.5},
n = 250 α = 4.6). The question is ordering: run M2 on calib_a's 92 now
(cheap, ≤ 69 CPU-h, gives the first memetic yield numbers), or generate
calib_b first so the memetic arm runs once over both. Recommendation: M2
now — the memetic side of the §5.3 rules is untested and might change which
cells matter before calib_b's α placement is chosen. Open alongside it: the
PySAT 1.9.dev3 freeze from Checkpoint 2 of the log. Both decisions are
recorded in `CORPUS_CALIBRATION_LOG.md` when taken, not here.

## 1. Per-cell table

`completed` = seeds with `profile.completed == true` (RC2 optimum proved);
`solve_s` over completed seeds only; `LB censored` = `cost_lower_bound`
recovered from the progress file on the censored seeds. Class:
**certified** = 5/5 optima known, **partial** = 1–4, **none** = 0/5.
Sorted by k, then n, then α.

| n | k | α | m=αn | completed | solve_s completed (min / med / max) | c* completed | LB censored | class |
|---|---|---|---|---|---|---|---|---|
| 100 | 2 | 2 | 200 | 5/5 | 0.003 / 0.005 / 0.007 | 1–5 | — | certified |
| 100 | 2 | 3 | 300 | 5/5 | 0.021 / 0.255 / 0.773 | 12–16 | — | certified |
| 100 | 2 | 4 | 400 | 5/5 | 3.09 / 8.06 / 174 | 24–31 | — | certified |
| 100 | 2 | 6 | 600 | 1/5 (s1) | 753 / 753 / 753 | 50 | 49–54 | partial |
| 150 | 2 | 2 | 300 | 5/5 | 0.007 / 0.009 / 0.021 | 6–7 | — | certified |
| 150 | 2 | 3 | 450 | 4/5 (s1,2,3,4) | 2.26 / 20 / 65 | 19–24 | 28 | partial |
| 150 | 2 | 4 | 600 | 0/5 | — | — | 35–40 | none |
| 150 | 2 | 6 | 900 | 0/5 | — | — | 55–66 | none |
| 250 | 2 | 2 | 500 | 5/5 | 0.028 / 0.181 / 2.61 | 8–14 | — | certified |
| 250 | 2 | 3 | 750 | 0/5 | — | — | 29–33 | none |
| 250 | 2 | 4 | 1000 | 0/5 | — | — | 44–49 | none |
| 250 | 2 | 6 | 1500 | 0/5 | — | — | 70–79 | none |
| 400 | 2 | 2 | 800 | 5/5 | 1.12 / 17 / 43 | 12–18 | — | certified |
| 400 | 2 | 3 | 1200 | 0/5 | — | — | 32–39 | none |
| 400 | 2 | 4 | 1600 | 0/5 | — | — | 52–57 | none |
| 400 | 2 | 6 | 2400 | 0/5 | — | — | 89–95 | none |
| 50 | 3 | 4.26 | 213 | 5/5 | 0.005 / 0.008 / 0.018 | 0–1 | — | certified |
| 50 | 3 | 5 | 250 | 5/5 | 0.009 / 0.014 / 0.065 | 1–2 | — | certified |
| 50 | 3 | 6 | 300 | 5/5 | 0.04 / 0.34 / 4.53 | 3–6 | — | certified |
| 50 | 3 | 8 | 400 | 5/5 | 9.86 / 66 / 89 | 8–11 | — | certified |
| 70 | 3 | 4.26 | 298 | 5/5 | 0.003 / 0.003 / 0.009 | 0–1 | — | certified |
| 70 | 3 | 5 | 350 | 5/5 | 0.01 / 0.088 / 8.09 | 1–4 | — | certified |
| 70 | 3 | 6 | 420 | 5/5 | 5.72 / 53 / 160 | 5–7 | — | certified |
| 70 | 3 | 8 | 560 | 0/5 | — | — | 9 | none |
| 100 | 3 | 4.26 | 426 | 5/5 | 0.003 / 0.007 / 0.129 | 0–1 | — | certified |
| 100 | 3 | 5 | 500 | 5/5 | 0.628 / 5.64 / 93 | 2–4 | — | certified |
| 100 | 3 | 6 | 600 | 0/5 | — | — | 5–6 | none |
| 100 | 3 | 8 | 800 | 0/5 | — | — | 7–8 | none |
| 150 | 3 | 4.26 | 639 | 5/5 | 0.014 / 0.04 / 2 | 0–1 | — | certified |
| 150 | 3 | 5 | 750 | 3/5 (s1,3,4) | 2.76 / 15 / 772 | 1–3 | 3–4 | partial |
| 150 | 3 | 6 | 900 | 0/5 | — | — | 4 | none |
| 150 | 3 | 8 | 1200 | 0/5 | — | — | 5–6 | none |
| 250 | 3 | 4.26 | 1065 | 4/5 (s1,2,4,5) | 0.482 / 166 / 388 | 0–1 | 1 | partial |
| 250 | 3 | 5 | 1250 | 0/5 | — | — | 2 | none |
| 250 | 3 | 6 | 1500 | 0/5 | — | — | 3 | none |
| 250 | 3 | 8 | 2000 | 0/5 | — | — | 4 | none |

Totals: 16 cells certified, 4 partial, 16 none; **92 certified instances**
(80 in full cells + 12 completed seeds in the partial cells).

## 2. Where the RC2 wall is

Within every (n, k) row the outcome is monotone in α: all seeds complete up
to some α, then all seeds are censored from the next grid value on. The
crossing happens across **one grid step** everywhere:

| k | n | last α with 5/5 | first α with 0/5 | between them |
|---|---|---|---|---|
| 2 | 100 | 4 (med 8 s) | — | α = 6: 1/5 (753 s) |
| 2 | 150 | 2 | 4 | α = 3: 4/5 (med 20 s) |
| 2 | 250 | 2 | 3 | nothing |
| 2 | 400 | 2 (med 17 s) | 3 | nothing |
| 3 | 50 | 8 (med 66 s) | — | wall beyond the grid |
| 3 | 70 | 6 (med 53 s) | 8 | nothing |
| 3 | 100 | 5 (med 5.6 s) | 6 | nothing |
| 3 | 150 | 4.26 | 6 | α = 5: 3/5 (med 15 s) |
| 3 | 250 | — | 5 | α = 4.26: 4/5 (med 166 s) |

So the "informative strip" of H3 (goals §2.4) exists and is diagonal as
predicted — larger n at lower α — but it is **narrow relative to the grid
spacing**: in 5 of 9 rows it falls entirely between two grid lines. The
grid catches it on one cell per row at best.

What RC2 time tracks here is c\*: the wall sits at c\* ≈ 9–12 for 3-SAT
(n ≤ 70 solves c\* = 10–11 in 66–160 s; n = 70 α = 8 with LB 9 does not) and
at c\* ≈ 25–50 for 2-SAT, rising slowly with n (n = 100 solves c\* = 31 in
174 s, one seed of c\* = 50 in 753 s; n = 400 solves c\* ≤ 18, not c\* ≥ 32).
Core-guided RC2 pays per core, so this is expected; it means the strip in
(n, α) is really a strip in c\*, and the 3-SAT and 2-SAT halves of the
corpus will sit at very different c\* decades (1–11 vs 12–50).

Near the 3-SAT satisfiability threshold (α = 4.26) c\* ∈ {0, 1} for every n:
these instances are satisfiable or one clause short of it. They are kept
(§4.4 "easy cases stay"), but for the memetic arm they are SAT-like
searches for a c\* = 0/1 assignment, and for RC2 at n = 250 they are the
slowest certified cell (0.5–388 s to prove that one clause must fail).

## 3. Cap placement

Cap 900 s sits right at the wall: 2 completions in 600–900 s, 10 in
60–600 s, and then 88 censored. The censored rows are not "just over": the
LB gaps say the censored cells are far past the wall (e.g. n = 70 α = 8 has
LB 9 on all seeds against a wall at c\* ≈ 10–12, but the proof of the last
one or two cores is what costs the time). Raising the cap to 1800 s would
probably certify the missing seed of the two 4/5 cells and little else; it
is not proposed for calib_a. The 4 partial cells are the direct evidence of
where a 2× cap would matter.

## 4. Pre-screen against the proposed §5.3 selection rules (RC2 side only)

The proposal is certified fraction ≥ 4/5 **and** median `solve_s` ≥ 10 s.
Applied to A1 (the memetic conditions come with M2/M3):

| cell | certified | median solve_s | RC2-side verdict |
|---|---|---|---|
| 2-SAT n = 150 α = 3 | 4/5 | 20 s | pass |
| 2-SAT n = 400 α = 2 | 5/5 | 17 s | pass |
| 3-SAT n = 50 α = 8 | 5/5 | 66 s | pass |
| 3-SAT n = 70 α = 6 | 5/5 | 53 s | pass |
| 3-SAT n = 250 α = 4.26 | 4/5 | 166 s | pass (c\* ∈ {0, 1}) |
| 2-SAT n = 100 α = 4 | 5/5 | 8.1 s | fails median by 2 s |
| 3-SAT n = 100 α = 5 | 5/5 | 5.6 s | fails median by 4 s |
| 3-SAT n = 150 α = 5 | 3/5 | 15 s | fails certification by 1 seed |
| 2-SAT n = 100 α = 6 | 1/5 | 753 s | fails certification |
| other 27 cells | 5/5 with median < 3 s, or 0/5 | — | fail |

**5 cells pass the RC2 half of the rules as proposed**, 3 miss by a hair.
This is the first-order result of the calibration: with this grid the
corpus would rest on 5 cells (≈ 24 certified instances), one per (n, k) row,
each one cell wide. The thresholds are a proposal (§5.3 says the
calibration may move them, with the reason recorded); the read-out does not
move them. What it does say is that `calib_b` — the refinement round the
plan reserves for "the strip falls between grid lines" (goals §3) — is needed,
with α steps inside the gaps in §2: roughly 2-SAT n = 100 α ∈ {4.5, 5},
n = 150 α ∈ {3.5}, n = 250 α ∈ {2.5}, n = 400 α ∈ {2.5}; 3-SAT n = 100
α ∈ {5.5}, n = 150 α ∈ {4.6, 5.5}, n = 250 α ∈ {4.6}. Whether to place
calib_b before or after M2 is a decision for the log, not this file.

## 5. What M2 runs on

The certified subset is the 92 completed instances (task ids in
`profile_calib_a_all.jsonl` with `profile.completed == true`; the partial
cells' completed seeds are listed in the table). Their RC2 times:

| solve_s | < 1 s | 1–10 s | 10–60 s | 60–600 s | 600–900 s |
|---|---|---|---|---|---|
| instances | 52 | 18 | 10 | 10 | 2 |

70 of the 92 are solved by RC2 in under 10 s. For the exploratory ρ of §5.2
this matters: the ranking among the 52 sub-second instances is dominated by
cluster timing noise (29 hosts, four node families, one run each), so the
resolution of ρ(RC2, memetic) rests on the ≈ 40 instances above 1 s and the
22 above 10 s. This is the attenuation §5.2 already names; it is quantified
here rather than discovered at M3. The 88 censored instances do not enter
M2 (no target cost for `STOP_AT_ORACLE`); they are the not-run list.

Cost of M2 as specified (3 seeds × 92 × ≤ 900 s at %30): ≤ 69 CPU-h,
≈ 10 waves ≈ 2.6 h wall worst case; the 70 easy instances will mostly hit
the oracle in seconds, so much less in practice.

## 6. Not in this read-out

No memetic data, no ρ, no CI, no yield CSV (`results/calibration/calib_a/
yield_table.csv` is M3's). The table above was produced by a scratchpad
script over `profile_calib_a_all.jsonl`; the same computation becomes the
RC2 columns of `calib_summary.py` in M3.
