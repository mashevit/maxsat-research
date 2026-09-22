# calib_b — RC2 grid refinement, plan

> **Status: executed and closed, 2026-09-22.** B1 returned 110/110 rows
> (85 completed, 25 censored, 0 failed) for 10.0 CPU-h of the 29.3 CPU-h
> budgeted below. **§7's first branch fired**: the pooled Tier-2-eligible
> population went from 10 instances in 6 cells to **46 in 21 cells**, against
> the stated stop condition of "≥ 40 across ≥ 8 cells, spread rather than
> piled at one end". α refinement is closed; no calib_c. The §6 comparability
> condition held (uniform PySAT 1.9.dev3, identical to A1), so calib_a and
> calib_b are pooled. Results, the scoring of this plan's own placement
> method, and the open items are in
> [`CALIB_B_B1_READOUT.md`](CALIB_B_B1_READOUT.md) and
> [`CORPUS_CALIBRATION_LOG.md`](CORPUS_CALIBRATION_LOG.md) Checkpoint 4.
>
> Where the plan was right and wrong, in one line each: the per-row `dc*/dm`
> model predicted c\* inside the observed range in **16 of 17** exploratory
> cells; the time model was within 3× in only **12 of 17**; placing **two** α
> per row (§3, step 3) is what absorbed that error; all **5** reinforcement
> cells (§4b) held and supplied 15 of the 46; and §4c's note that n
> refinement, not α, is the lever for 3-SAT n = 150 was confirmed
> quantitatively — that row yielded **0** eligible instances at four α values
> because its c\* ladder steps over the whole 60–600 s window.

**Date:** 2026-09-22. Written against commit `ccf2735` (calib_a A1 results
committed), before any calib_b instance is generated. Companion to
[`CORPUS_CALIBRATION_GOALS.md`](CORPUS_CALIBRATION_GOALS.md) (§3 reserves this
round: *"if the strip of §2.4 H3 falls between grid lines, `calib_b` refines
around it with the same tooling before anything is frozen"*) and to
[`CALIB_A_A1_READOUT.md`](CALIB_A_A1_READOUT.md), which is the evidence this
plan is built on. Per-turn record goes to
[`CORPUS_CALIBRATION_LOG.md`](CORPUS_CALIBRATION_LOG.md) Checkpoint 3.

Everything here is conditional on the calib_a stack: `RC2(wcnf, solver="g3")`
with `adapt=exhaust=minz=False`, cap 900 s + 60 s grace, single CPU on the
cluster `main` partition. Nothing in this round changes the solver, the cap,
the generator or the profiling workflow.

---

## 1. Why this round comes before M2

The calibration's bottleneck is **not** the memetic arm — it is how few
calib_a instances are both *certified* and *RC2-nontrivial*.

| A1 outcome | count (of 180) |
|---|---:|
| certified (RC2 proved c\*) | 92 |
| of those, `solve_s` ≥ 30 s | 17 |
| of those, `solve_s` > 60 s | 12 |
| of those, `60 s < solve_s ≤ 600 s` (the repo's Tier-2 window, §2) | **10** |
| censored at 900 s | 88 |

So the Tier-2-eligible population from calib_a is **10 instances** (12 if the
window is opened to the cap), drawn from 6 distinct cells, and 3 of those 10
come from one cell. Running M2 (3 memetic seeds × 92 = 276 tasks, ≤ 69 CPU-h)
would spend its resolution on the 70 sub-10-second instances and return a
memetic read-out over an eligible set of 10. Refining the grid first is
cheaper (≈ 29 CPU-h) and changes the size of the set M2 runs on.

This is an ordering decision, not a change of plan: goals §3 already reserves
`calib_b` for exactly the finding A1 produced (the informative strip is one
grid step wide and falls between grid lines in 5 of 9 (n, k) rows). The A1
read-out's own recommendation was M2-first; it is superseded here, with the
reason above, and both are recorded in the log.

**M2 is not run in this round.**

## 2. Tier 2: the established definition, and what this round does with it

There are two *different* rules in the repository and they must not be
conflated. This plan changes neither.

**(a) Per-instance Tier-2 eligibility — `assign_tier()` in
`src/cli/profile_hardness.py`.** The established thresholds are
`T1_MAX_S = 60`, `T2A_MAX_S = 300`, `T2B_MAX_S = 600`: an instance is Tier 2
(T2a or T2b) iff RC2 **completed** and `60 s < solve_s ≤ 600 s`.
`src/bench/make_tier2_manifest.py` states the same in prose ("the set of
instances RC2 solved to optimality in 60–600 s … non-trivial and carry an
oracle optimum") and adds the `include_solved_t3` rescue for rows that are
`completed == true` but were labelled T3 because `assign_tier()` ignores
`--cap` — under a 900 s cap that rescue extends the window to
`60 s < solve_s ≤ 900 s`.

**(b) Cell-level selection rules — goals §5.3.** RC2 certified fraction
≥ 4/5 **and** RC2 median `solve_s` ≥ 10 s (plus two memetic conditions from
M2/M3). These decide *which cells* the final corpus is generated from; they
are explicitly a proposal that the calibration may move, with the reason
recorded in `instancegen/grids/corpus_v1.yaml`.

**The 30–900 s band in the task request is not an established threshold.**
The repository's per-instance floor is 60 s, not 30 s. This plan therefore:

- keeps **60 s < `solve_s` ≤ 600 s** as the primary Tier-2 window and
  **60 s < `solve_s` ≤ 900 s** as the documented `include_solved_t3` variant;
- reports the **≥ 30 s** count alongside, as a labelled sensitivity column,
  so the consequence of lowering the floor is visible in numbers before
  anyone decides to lower it;
- does **not** edit `T1_MAX_S`, `assign_tier()` or any threshold constant.

Lowering the floor to 30 s is a real option (it would take calib_a from 10
eligible to 17), but it is a decision for the log with a stated reason, not a
silent edit inside a grid-refinement round. **Open item for the user.**

**Cell selection ≠ instance eligibility.** Cell statistics (rule b) say where
to *sample*; individual instances enter Tier 2 only by their own row under
rule (a). A cell whose median is 200 s still contributes only those of its
seeds that individually land in the window, and a cell that fails rule (b)
can still contribute an eligible instance — calib_a has three such
(2-SAT n = 100 α = 4 seed 3 at 174 s; 3-SAT n = 100 α = 5 seed 2 at 93 s;
3-SAT n = 150 α = 5 seed 3 at 772 s). `src/bench/calib_tier2_select.py`
(this round) implements rule (a) only, over all calibration batches, and
prints the rule-(b) cell table beside it without letting either decide the
other.

## 3. Selection rule for *where to sample* in calib_b

Sampling positions are chosen from A1's measured (α, c\*, `solve_s`) per
(n, k) row, never from anything about the memetic solver and never from any
correlation. Within each row:

1. Read the two bracketing calib_a cells: the last α that certified and the
   first α that did not. Read their c\* (or recovered LB) and `solve_s`.
2. Fit, by eye, the two local slopes the rows actually show — `dc*/dm`
   (linear, stable within a row) and `d log10(solve_s)/dc*` — and invert them
   for the α whose expected c\* lands in the **60–600 s** window.
3. Place **two** α values per row: one inside the bracket where the
   prediction is comfortably certified (the yield cell), one nearer the wall
   (the stretch cell). Both are predictions that can be wrong; a censored
   stretch cell is a measurement of the wall, not a failure.

This is deliberately *not* "higher α is harder, so go higher". Four of the
nine rows need α *between* existing grid lines, and the 3-SAT n = 250 row
needs α *at or barely above* 4.26, because its wall is already crossed at
α = 5. Three rows (2-SAT n = 250, n = 400; 3-SAT n = 150) are refined
*downward* relative to the first censored cell, into gaps where the c\*
estimate says the wall sits.

**Two things this round does not assume.** (i) That c\* alone determines RC2
time: c\* is used only *within* an (n, k) row, where n and α are held or
moved slightly, and the per-row slopes are fitted separately precisely
because they differ by a factor of ~3 between rows (0.1 dec/c\* at 2-SAT
n = 100, ~0.3 at 2-SAT n = 250, ~1.4 at 3-SAT n = 150). (ii) That an
RC2-easy instance is memetic-easy: nothing here is chosen for the memetic
arm, whose behaviour on these cells is unmeasured until M2.

## 4. The grid

`instancegen/grids/calib_b.yaml`. Same generator conventions as calib_a
(pure soft, `hard_ratio = 0`, `w_max = 1`, `weight_dist = uniform`,
`m = round(α·n)`, old wcnf dialect). **22 cells, 5 seeds each, 110
instances.** Two kinds of cell:

### 4a. Exploratory cells — new α, seeds 1–5 (17 cells, 85 instances)

`α_lo` / `α_hi` bracket the A1 cells quoted in the last column.

| family | n | α | m | predicted c\* | predicted `solve_s` | A1 bracket |
|---|---:|---:|---:|---:|---|---|
| max2sat | 100 | 4.5 | 450 | ~33 | ~40 s | α 4: 5/5, med 8 s, c\* 24–31 → α 6: 1/5 (753 s), LB 49–54 |
| max2sat | 100 | 5.0 | 500 | ~39 | ~150 s | " |
| max2sat | 150 | 3.15 | 472 | ~24 | ~90 s | α 3: 4/5, med 20 s, c\* 19–24 → α 4: 0/5, LB 35–40 |
| max2sat | 150 | 3.30 | 495 | ~26 | ~300 s | " |
| max2sat | 250 | 2.35 | 588 | ~18 | ~60 s | α 2: 5/5, med 0.2 s, c\* 8–14 → α 3: 0/5, LB 29–33 |
| max2sat | 250 | 2.50 | 625 | ~21 | ~300 s | " |
| max2sat | 400 | 2.15 | 860 | ~18 | ~60 s | α 2: 5/5, med 17 s, c\* 12–18 → α 3: 0/5, LB 32–39 |
| max2sat | 400 | 2.30 | 920 | ~21 | ~350 s | " |
| max3sat | 50 | 8.5 | 425 | ~11 | ~150 s | α 8: 5/5, med 66 s, c\* 8–11 → (no censored cell in row) |
| max3sat | 50 | 9.0 | 450 | ~12.5 | ~600 s | " |
| max3sat | 70 | 6.2 | 434 | ~6.6 | ~100 s | α 6: 5/5, med 53 s, c\* 5–7 → α 8: 0/5, LB 9 |
| max3sat | 70 | 6.5 | 455 | ~7.7 | ~300 s | " |
| max3sat | 100 | 5.2 | 520 | ~3.8 | ~30 s | α 5: 5/5, med 5.6 s, c\* 2–4 → α 6: 0/5, LB 5–6 |
| max3sat | 100 | 5.5 | 550 | ~4.9 | ~400 s | " |
| max3sat | 150 | 4.6 | 690 | ~1.1 | ~5 s | α 4.26: 5/5, med 0.04 s → α 5: 3/5, med 15 s → α 6: 0/5 |
| max3sat | 150 | 4.8 | 720 | ~1.7 | ~60 s | " |
| max3sat | 250 | 4.35 | 1088 | ~1 | ~200 s | α 4.26: 4/5, med 166 s, c\* 0–1 → α 5: 0/5, LB 2 |

Row-by-row reasoning, in one line each:

- **2-SAT n = 100.** `dc*/dm ≈ 0.12`, `d log10 t/dc* ≈ 0.10`. The window
  60–600 s is c\* ≈ 38–46 → α ≈ 4.7–5.3; α = 4.5 is the yield cell just under
  it, α = 5.0 the stretch. (The readout's candidates {4.5, 5} — kept.)
- **2-SAT n = 150.** The row brackets the wall tightly: c\* = 24 solved in
  65 s, c\* = 28 censored. Window is c\* ∈ [24, 27] → α ∈ [3.15, 3.34].
  Both cells sit inside that bracket, which is why they are 0.15 apart
  rather than the readout's single 3.5 (α = 3.5 ⇒ c\* ≈ 29, past the wall).
- **2-SAT n = 250.** Widest gap in the grid (α = 2 trivial at 0.2 s, α = 3
  censored). The solved-c\* ceiling across the 2-SAT rows falls with n
  (n = 100 solved 50, n = 150 solved 24, n = 400 solved 18), so n = 250's
  ceiling is ≈ 20–22; α = 2.35 / 2.50 target c\* ≈ 18 / 21. The readout's
  2.5 is kept as the stretch cell and 2.35 added under it.
- **2-SAT n = 400.** α = 2 already medians 17 s at c\* ≈ 16, so the window is
  barely above it: c\* 18–22 → α 2.15–2.33. The readout's 2.5 (⇒ c\* ≈ 27)
  is *rejected* as almost certainly censored.
- **3-SAT n = 50.** The only row whose wall is outside the grid: α = 8
  certifies c\* = 8–11 in 10–89 s. Refined *upward*, the one row where that
  is the right direction.
- **3-SAT n = 70.** Wall between c\* = 7 (160 s) and c\* = 9 (censored);
  α 6.2 / 6.5 target c\* ≈ 6.6 / 7.7.
- **3-SAT n = 100.** Wall between c\* = 4 (93 s) and c\* = 5 (censored);
  α 5.2 / 5.5 target c\* ≈ 3.8 / 4.9. (Readout candidate 5.5 kept, 5.2 added.)
- **3-SAT n = 150.** Wall between c\* = 3 (772 s) and c\* = 4 (censored).
  The readout's 5.5 would be past it; 4.6 / 4.8 sit *below* α = 5 instead,
  targeting c\* ≈ 1–2 where the row still certifies.
- **3-SAT n = 250.** Wall already crossed at α = 5 (LB 2). The whole window
  is c\* = 1, which α = 4.26 already produces (166–388 s). One exploratory
  cell only, α = 4.35, to shift mass off c\* = 0 without reaching c\* = 2;
  the yield for this row comes from the reinforcement cell below instead.

### 4b. Reinforcement cells — existing α, seeds 6–10 (5 cells, 25 instances)

The five cells that pass the RC2 half of the §5.3 rules are re-sampled with
five fresh generator seeds. Seeds are i.i.d. draws from the same cell
distribution, so this enlarges the cell sample; it is *not* re-running
anything (seeds 6–10 are new instances, disjoint from calib_a's 1–5 and from
M4's 1001–1020).

| family | n | α | A1 result on seeds 1–5 |
|---|---:|---:|---|
| max2sat | 150 | 3.0 | 4/5 certified, med 20 s |
| max2sat | 400 | 2.0 | 5/5, med 17 s |
| max3sat | 50 | 8.0 | 5/5, med 66 s |
| max3sat | 70 | 6.0 | 5/5, med 53 s |
| max3sat | 250 | 4.26 | 4/5, med 166 s |

Why this is not circular: these cells are chosen by rule (b) on A1 —
certified fraction and median proof time — which is the rule frozen *before*
any memetic measurement exists, and re-sampling a cell cannot change the
cell's distribution. It is the low-variance half of the round: the
exploratory cells are predictions and some will miss, these will not.

**Consequence to record: cell sizes are now unequal** (10 seeds in five
cells, 5 everywhere else). Certified fraction for those cells is x/10, not
x/5; the §5.3 threshold "≥ 4/5" reads as "≥ 80 %"; and the stratified
bootstrap of §5.2 resamples within cell, so unequal strata are handled but
must be stated in the table. calib_a rows are **not** superseded or merged
into these cells' calib_a statistics — the two batches stay separate in the
record and are pooled only where a table says it pools them.

### 4c. Not in this round (candidates for a later one)

- **n refinement.** The instruction for this round is α at fixed (n, k). The
  clearest n-gap is 3-SAT at α = 4.26 between n = 150 (med 0.04 s) and
  n = 250 (med 166 s): n = 180–200 would very likely land mid-window at
  5/5 certified. It is recorded here as the strongest calib_c candidate.
- **Raising the cap.** A 1800 s cap would certify perhaps the missing seed of
  the two 4/5 cells (readout §3). Not proposed; the cap stays 900 s.
- **A second refinement round.** Explicitly out of scope — see §7.

## 5. Budget

Worst case, every task charged the full cap + grace:

| batch | tasks | per task | CPU-h (worst case) | elapsed at `%30` (compute only) |
|---|---:|---|---:|---|
| B1 RC2, calib_b | 110 | 1 CPU · 8 GB · ≤ 960 s | 110 × 960 s = **29.3 CPU-h** | ⌈110/30⌉ = 4 waves × ~17 min ≈ **1.1 h** |

**Maximum compute budget for this round: 29.3 CPU-h.** Realistic cost is
well under it — the reinforcement cells and the yield cells are predicted at
tens to hundreds of seconds, not the cap. Queue delay is not included (it is
set by partition load; record it from `sacct`). No memetic tasks are
submitted in this round.

## 6. Comparability with A1 (the PySAT question)

Checkpoint 2 recorded a version mismatch: goals §4.1 holds **1.9.dev15**
fixed, but all 180 A1 tasks ran the cluster `maxsat` env's **1.9.dev3**
(python 3.11.15); the workstation is 1.9.dev15 / python 3.12.3.

**calib_b runs on the same cluster env, unchanged.** No upgrade, no
re-install, nothing added to the module load. Comparability rests on:

1. **The env is recorded per task, not assumed.** `rc2_profile_array.sbatch`
   writes `task_N.env.json` with `pysat_version`, python, host and job id
   before RC2 starts; `scripts/aggregate_rc2_profile.py` (added this round)
   carries it into `profile_calib_b_env.jsonl`. If the cluster env has moved
   since 2026-09-22, the aggregation shows it and calib_b is *not* pooled
   with calib_a until that is resolved. A uniform-but-different version is a
   finding to record, not a silent pooling.
2. **Optima do not depend on the dev tag.** RC2 with these options is exact;
   the Checkpoint 2 cross-check on two instances gave identical c\*
   (6 and 25) under both versions, with `solve_s` 4.5 vs 4.9 s and 8.1 vs
   9.7 s. The certification half of Tier-2 eligibility is therefore
   version-robust.
3. **Timings are already cross-host.** A1's 180 tasks ran on 29 hosts across
   four node families; that spread is larger than the dev3/dev15 difference
   seen on the two cross-checked instances. Any `solve_s` comparison between
   calib_a and calib_b carries that caveat whichever version runs.
4. **The decision is still open.** Freezing dev3 (recommended at
   Checkpoint 2) versus upgrading and re-running A1 is not settled by this
   round, and this round does not pre-empt it: it adds rows under the same
   env as A1, which is the option that keeps *both* decisions available.
   If dev15 is later adopted, A1 and B1 are re-run together.

## 7. What the results decide, and what they do not

When B1 returns, the read-out is the same four things A1 produced, per cell:
certified fraction, `solve_s` min/median/max over completions, c\* range, LB
range on censored rows — plus the two eligibility counts of §2 (60–600 s and
the ≥ 30 s sensitivity) over calib_a ∪ calib_b, deduplicated by
`instance_sha256`.

Then one of:

- **Enough eligible instances (target: ≥ 40 across ≥ 8 cells, spread over
  the 60–600 s range rather than piled at one end).** Stop refining. Proceed
  to M2 on the certified subset, then M3, then freeze §5.3 with any
  threshold change recorded.
- **Close but thin in one or two rows.** One further round, same size or
  smaller, only in those rows. Recorded as calib_c with its own plan entry.
- **Several exploratory cells censored where the model predicted
  certification.** That is itself the result — it says the wall is sharper in
  c\* than the per-row slope suggests — and the response is to move the
  remaining effort to reinforcement seeds in cells already known to sit in
  the window, not to keep hunting α.

**No recursive search.** This round is one bounded batch; anything further is
a new plan entry with its own budget line.

## 8. Standing constraints (restated so this round is checkable against them)

- Instances are never selected to produce a correlation, and nothing in this
  round looks at memetic data — there is none for these cells.
- Timeouts are **censored**, not failures and not solved: a recovered
  `cost_lower_bound` is a lower bound, never an optimum, and censored rows
  cannot enter Q3.
- Every generated instance and every row stays in the calibration record,
  including the trivial and the censored ones — they locate the edges.
- RC2-easy does not imply memetic-easy (H2); the eligibility rule is about
  RC2 having *certified* an optimum in non-trivial time, not about expected
  memetic difficulty.
- Any ρ reported later describes the **selected Tier-2 population** under
  this stack, this cap and these rules — not random Max-k-SAT.

**Open item, flagged not decided (goals §5.4 vs. building Tier 2 from
calibration batches).** §5.4 says the final corpus is regenerated on a
disjoint seed range (1001–1020) and that *calib_a rows never enter a reported
ρ*. Building the Tier-2 manifest out of eligible calib_a ∪ calib_b instances
is in tension with that. `calib_tier2_select.py` produces the manifest either
way; which population the paper reports on is a decision for the log. The
default remains §5.4 (fresh seeds at M4) until it is changed on the record.
