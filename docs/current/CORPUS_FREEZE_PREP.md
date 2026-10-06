# Corpus freeze preparation: verified candidate cells, what can be frozen, the calib_c reinforcement batch, other families, and hard clauses

**Date:** 2026-10-06. **Against:** commit `28d4da6` plus this turn's
uncommitted changes (file list in §11). **Nothing was submitted to Slurm.**
The proposed final protocol is a separate document,
[`CORPUS_V1_PROTOCOL_DRAFT.md`](CORPUS_V1_PROTOCOL_DRAFT.md). The log entry is
Checkpoint 8 in [`CORPUS_CALIBRATION_LOG.md`](../CORPUS_CALIBRATION_LOG.md).

> **Revision r2 — user decisions, 2026-10-06 (later the same day).** The
> analysis below (§1–§3, §5.1–§5.4, §6, §8) stands. The following
> recommendations of r1 are **superseded**. They are kept in place, marked
> *[superseded r2]*, so the record shows what was proposed:
> 1. **RC2 version:** PySAT **1.9.dev3** is kept as the RC2 version (D1
>    closed). The exact configuration and environment are in
>    [`CORPUS_V1_PROTOCOL_DRAFT.md`](CORPUS_V1_PROTOCOL_DRAFT.md) §2.
> 2. **Primary effort measure:** memetic effort in **seconds** stays the
>    pre-registered primary measure. Polish calls and flips are secondary
>    diagnostics. r1's recommendation to make calls primary is withdrawn.
> 3. **Sample size:** the instances per stratum are **not fixed**. The 40–50
>    target is withdrawn; the trade-off is in the protocol §5.
> 4. **Reference regime:** **no new instances** are generated for the
>    Max-3-SAT n = 250, c\* = 1 regime, including the m = 1065 / 1088 cells.
>    The historical 26 SATLIB instances and the existing calibration rows
>    remain reference evidence, under their original conditions. Stratum R
>    and its task counts are removed.
> 5. **`calib_c`:** prepared and preserved. **Submission is pending; not
>    approved.**
> 6. **MaxCut:** the MaxCut generator is the **proposed next implementation
>    milestone. Not started.**
> 7. **New pending task:** assess Max-3-SAT at **n > 250**, including whether
>    some cells reach c\* > 1 inside the RC2 window with real memetic effort
>    (§4a). r1's "no further Max-3-SAT refinement" applied to n ≤ 250 and is
>    **not** a conclusion about larger n.
>
> Session handoff: [`NEXT_SESSION_CONTEXT.md`](NEXT_SESSION_CONTEXT.md).

> **Note r3 — user direction, 2026-10-06 (end of day).** Documentation
> only; nothing was generated, prepared or submitted.
> 1. **New direction:** explore grid points with **more variables in both
>    Max-2-SAT and Max-3-SAT**, with clause-to-variable ratios suited to each
>    size, to find hard instances (RC2-eligible and memetic Q2). §4a is
>    widened from Max-3-SAT n > 250 to both families.
> 2. **`calib_c` (§5, §9) is on hold, to be reassessed** against this
>    direction: keep as prepared, revise (e.g. n = 400 as one rung of a
>    larger-n ladder) or replace. **Its construction is not in question.**
>    The §5 cells and seeds follow correctly from §2 under the earlier aim of
>    settling n = 400. If it is revised or replaced, §5 gets a new dated
>    revision before anything is generated or submitted.
> 3. **Effort stays in seconds** (r2 item 2, reaffirmed).
> 4. **The n = 250, c\* = 1 reference stratum is preserved; no new instances
>    for it** (r2 item 4, reaffirmed).
>
> The existing evidence for the direction is tabulated in
> [`NEXT_SESSION_CONTEXT.md`](NEXT_SESSION_CONTEXT.md) §0. The RC2 window
> moves toward the satisfiability threshold as n grows, and Q2 rises with n.
> So larger-n cells need α placed per n, not a fixed α list.

Paths starting with `results/` or `scripts/` are relative to
`cluster_staging_maxsat/`. **No ρ was used anywhere in this document**: not
to place cells, not to classify them, and not to size the batch.

---

## 0. Summary

1. **Status.** RC2 has profiled 290 generated instances (177 certified).
   M2 ran 420 memetic tasks (70 instances × 3 seeds × 2 arms; 202/210 and
   208/210 successes). The historical JW-seeded multistart arm is complete
   (127/130). Every number in the brief was re-derived from the raw rows
   and matches (§1).
2. **The cell picture recovered from the rows** (§2,
   `results/corpus_freeze_prep/candidate_cells.csv`):
   - 24 of 53 calibration cells hold an RC2-eligible instance
     (30 s < t ≤ 900 s, certified).
   - **Under the pre-registered §5.3 cell rule applied literally, exactly one
     cell passes: Max-3-SAT n = 250, α = 4.26.** That is the reference regime.
   - The M2 read-out's statement that n = 250 α = 4.35 and n = 150 α = 4.8
     "pass" ignored the rule's RC2 conditions. α = 4.35 has 2/5 certified;
     α = 4.8 has 3/5 certified and a certified median of 1.9 s.
   - **"Seven grid points where both solvers work" is not a result.** It is a
     prose list in read-out §6.2 that mixes two criteria (§2.3). Under any
     single definition the count is 1, 5 or 8.
3. **Classification** (rule-based, §3):
   - reference: 2 cells (3-SAT n = 250, α 4.26 and 4.35);
   - supported expansion candidate: **none**;
   - promising but under-supported: **2-SAT n = 400 at α = 2.0 and α = 2.15**,
     each one Q2 instance short (1/4 against a required 2/4), with every
     other condition met;
   - unsuitable: the remaining 20 cells with eligible instances (and the 29
     without).
4. **What can be frozen now** (§4): no *expansion* stratum.
   *[superseded r2: "the reference cell can be frozen now as a replication
   stratum". By decision, no new reference instances are generated; the
   historical results remain the reference evidence.]*
5. **Proposed next batch: `calib_c`** (§5). Prepared and **not submitted;
   the submission decision is pending (r2):**
   - cells: the two 2-SAT n = 400 cells, 20 new generator seeds each
     (101–120);
   - tasks: 40 RC2 tasks, then about 72 memetic tasks (primary arm only);
   - compute: worst case 10.7 + 32 CPU-h, expected ≈ 1.4 + 0.5 CPU-h;
   - decision: the §5.3 rule, unchanged, on the pooled cell;
   - not reinforced: Max-3-SAT at n ≤ 250. *[qualified r2: this is not
     evidence against a new regime at n > 250, which is a pending
     assessment (§4a).]*
6. **Other families** (§6):
   - MaxCut (ER and signed ±J torus) is **not implemented**;
   - the MSE-2016 structured leaves are on disk but only 3 of 67 have been
     profiled;
   - the torus problem is resolved by spin-glass ±J couplings, which work at
     any side length;
   - each family gets its own calibration gate and its own freeze;
   - the MaxCut generator is the proposed next implementation milestone, not
     started (r2).
7. **Hard clauses** (§8): the documented reason for excluding them ("no
   gradient toward feasibility") is **inaccurate**, and its evidence came from
   one large industrial instance with a confound. A local probe and code
   reading give a narrower, verified reason:
   - **For mixed-sign hard clauses** (partial random k-SAT, set cover):
     crossover of two *feasible* parents produced an infeasible child 20/20
     times, and the polish cannot climb out of hard-violation local minima.
     **SAT-assisted initialisation alone would not fix this. Exclusion stands
     for the current solver.**
   - **For conflict-clause structures** (Max-Independent-Set / Max-Clique):
     the existing operators found and kept feasibility. **Inclusion is
     reopened as an option,** gated by a small diagnostic.

---

## 1. Status, re-derived from the rows

| claim in the brief | verified value | source |
|---|---|---|
| RC2 calibration on 290 generated, 177 certified | 290 rows; 177 certified, 113 censored at 900 s, 0 failed | `results/profile_calib_{a,b}_all.jsonl` |
| certified with RC2 < 30 s | **107**; memetic not run on them (decision 2) | same |
| M2: 70 × 3 seeds × 2 arms = 420 runs | 420/420; 410 success, 10 budget_exhausted, 0 infra | `results/m2_full_p40/agg/tasks.csv` |
| 202/210 (0.5 s), 208/210 (3.5 s) | reproduced | same |
| 28/70 solved by the first call in all 6 runs | reproduced (`all6_first_child`) | `analysis/instance_table.csv` |
| 55/70 never needed a second generation | reproduced: 15 instances have any run beyond generation 1 | same |
| Q2 non-trivial | 9 under the 3.5 s arm, 5 under 0.5 s; union 9 | recomputed from runs, 0 mismatches against `instance_table.csv` |
| JW multistart 127/130 vs uniform 124/130 vs memetic 118/130 | reproduced | `docs/UUF_THREE_ARM_ABLATION_READOUT.md` |

**Statements now superseded:**
- The "not run" / "not submitted" lines for M2 in older documents
  (Checkpoints 3 and 4) and for the JW arm (`archive/TIER2_ABLATION_FAIRNESS_AUDIT.md`
  §5(a), `more_data/CORPUS_BROADENING_HANDOFF.md` §6b). Both have been run.
- The §5.3 "passes" sentence in `M2_FULL_POOL_READOUT_AND_STATE.md` §6.2. It
  is amended there and corrected in §2.2 below.

**Primary configuration verified** (decision 6):
- file: `configs/tier2/memetic_deeppolish_p40_ls3p5.yaml`;
- settings: `pop_size: 40`, `ls.time_limit_s: 3.5`, `ls_polish_flips: 12500`
  (= `flip_budget`), `ea.deadline_mode: clip`, tournament 3, `pmutate` 0.02,
  elitism (2 elites, 38 children per generation);
- the 900 s budget is injected by `run_memetic_shard.py --budget-s`;
- stop at the RC2 optimum, 60 s watchdog grace;
- `make_m2_manifests.check_arms()` pins all of this.

**One property of this configuration matters for every rule below.** The Q2
rule is in seconds (median TTT ≥ 45 s). A 3.5 s-arm call takes 1.25 s at
m = 400 and 3.0 s at m = 1088 (read-out §2.2). So 45 s is about 36 calls on a
small cell and about 15 calls on the n = 250 cells. The rule is therefore
easier to meet at large m. This does not stop the objective from being
reached, so the configuration and the rule are kept. The call-based columns
in §2 show how much it matters.

Boundary convention, made explicit:
- **eligible ⇔ certified (`completed` and `final_cost == cost_lower_bound`)
  and 30 s < `solve_s` ≤ 900 s;**
- the M2 pool used 30 ≤ s ≤ 900 (`make_m2_manifests.py`), but no certified
  instance has `solve_s` = 30.0, so both conventions select the same 70
  (asserted in `candidate_cells.py`);
- a completed row with `solve_s` > 900 counts as censored;
- `solve_s` ≤ 0 (the wall-clock-step artefact of Checkpoint 3) counts as
  failed.

---

## 2. Verified candidate-cell table

Built by `scripts/candidate_cells.py` from the raw RC2 rows, the generator
manifests and the per-run M2 table. Outputs are in `results/corpus_freeze_prep/`:
- `candidate_cells.csv` (53 cells);
- `candidate_instances.csv` (290 instances, with `pop_idx` and `pilot_idx`
  as separate columns);
- `summary.json`.

`--check` reproduces them byte for byte.

### 2.1 Cells with at least one RC2-eligible instance (24 of 53)

Reading guide:
- **Memetic columns** are the primary 3.5 s arm (`a35`), per instance first
  (3 seeds), then summarised over the cell.
- **gen / cert / ≤30 s / elig:** generated instances, RC2-certified
  instances, certified in ≤ 30 s, and RC2-eligible instances.
- **tested:** eligible instances with all 3 primary runs. No eligible
  instance is untested.
- **med TTT:** median over instances of the instance median TTT, with
  failures counted as +∞.
- **ERT calls:** polish calls summed over runs, divided by successes.
- **inst beyond gen 1:** instances with ≥ 1 run past generation 1 (more than
  38 calls), under a35 and under either arm.
- **r1–r4:** the §5.3 conditions (§2.2).

| cell (k, n, α, m) | batches · gen seeds | gen | cert | ≤30 s | elig | RC2 s elig (min / med / max) | c\* elig | tested | a35 succ | med TTT s | ERT calls med (range) | max calls | inst beyond gen 1 (a35 / either) | Q2 a35 | r1 cert | r2 med s | r3 Q2 | r4 | §5.3 | category |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3-SAT n50 α8 m400 | a,b · 1–10 | 10 | 10 | 2 | 8 | 32.8 / 82.4 / 648.7 | 9-11 | 8 | 24/24 | 1.3 | 1.0 (1.0-1.0) | 1 | 0 / 0 | 0/8 | 10/10 ✓ | 70.9 ✓ | 0/8 ✗ | 8/8 ✓ | fail | unsuitable |
| 3-SAT n50 α8.5 m425 | b · 1,2,3,4,5 | 5 | 4 | 0 | 4 | 45.1 / 483.3 / 626.7 | 9-12 | 4 | 12/12 | 1.4 | 1.0 (1.0-1.0) | 1 | 0 / 0 | 0/4 | 4/5 ✓ | 483.3 ✓ | 0/4 ✗ | 4/4 ✓ | fail | unsuitable |
| 3-SAT n50 α9 m450 | b · 1,2,3,4,5 | 5 | 2 | 0 | 2 | 152.1 / 499.7 / 847.3 | 11-13 | 2 | 6/6 | 1.4 | 1.0 (1.0-1.0) | 1 | 0 / 0 | 0/2 | 2/5 ✗ | 499.7 ✓ | 0/2 ✗ | 2/2 ✓ | fail | unsuitable |
| 3-SAT n70 α6 m420 | a,b · 1–10 | 10 | 10 | 4 | 6 | 34.9 / 117.4 / 367.3 | 5-7 | 6 | 18/18 | 1.3 | 1.0 (1.0-25.7) | 64 | 1 / 1 | 0/6 | 10/10 ✓ | 44.1 ✓ | 0/6 ✗ | 6/6 ✓ | fail | unsuitable |
| 3-SAT n70 α6.2 m434 | b · 1,2,3,4,5 | 5 | 5 | 2 | 3 | 152.5 / 197.2 / 290.5 | 6-7 | 3 | 9/9 | 1.3 | 1.0 (1.0-1.3) | 2 | 0 / 0 | 0/3 | 5/5 ✓ | 152.5 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |
| 3-SAT n70 α6.5 m455 | b · 1,2,3,4,5 | 5 | 4 | 0 | 4 | 146.4 / 182.9 / 436.4 | 7-8 | 4 | 12/12 | 1.4 | 1.0 (1.0-1.3) | 2 | 0 / 0 | 0/4 | 4/5 ✓ | 182.9 ✓ | 0/4 ✗ | 4/4 ✓ | fail | unsuitable |
| 3-SAT n100 α5 m500 | a · 1,2,3,4,5 | 5 | 5 | 4 | 1 | 93.0 / 93.0 / 93.0 | 4 | 1 | 3/3 | 3.0 | 2.3 (2.3-2.3) | 4 | 0 / 0 | 0/1 | 5/5 ✓ | 5.6 ✗ | 0/1 ✗ | 1/1 ✓ | fail | unsuitable |
| 3-SAT n100 α5.2 m520 | b · 1,2,3,4,5 | 5 | 5 | 2 | 3 | 46.8 / 211.0 / 213.2 | 4-5 | 3 | 9/9 | 1.5 | 1.0 (1.0-3.0) | 4 | 0 / 0 | 0/3 | 5/5 ✓ | 46.8 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |
| 3-SAT n100 α5.5 m550 | b · 1,2,3,4,5 | 5 | 3 | 0 | 3 | 62.0 / 156.6 / 173.8 | 4-5 | 3 | 9/9 | 3.2 | 2.7 (1.0-6.0) | 12 | 0 / 0 | 0/3 | 3/5 ✗ | 156.6 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |
| 3-SAT n150 α4.8 m720 | b · 1,2,3,4,5 | 5 | 3 | 2 | 1 | 34.9 / 34.9 / 34.9 | 2 | 1 | 3/3 | 47.2 | 30.3 (30.3-30.3) | 59 | 1 / 1 | 1/1 | 3/5 ✗ | 1.9 ✗ | 1/1 ✓ | 1/1 ✓ | fail | unsuitable |
| 3-SAT n150 α5 m750 | a · 1,2,3,4,5 | 5 | 3 | 2 | 1 | 772.2 / 772.2 / 772.2 | 3 | 1 | 3/3 | 8.3 | 3.7 (3.7-3.7) | 7 | 0 / 0 | 0/1 | 3/5 ✗ | 14.9 ✓ | 0/1 ✗ | 1/1 ✓ | fail | unsuitable |
| 3-SAT n250 α4.26 m1065 | a,b · 1–10 | 10 | 9 | 3 | 6 | 33.0 / 83.5 / 387.8 | 1 | 6 | 17/18 | 125.6 | 35.5 (14.7-221.0) | 298 | 3 / 6 | 5/6 | 9/10 ✓ | 50.8 ✓ | 5/6 ✓ | 6/6 ✓ | **pass** | reference |
| 3-SAT n250 α4.35 m1088 | b · 1,2,3,4,5 | 5 | 2 | 0 | 2 | 103.4 / 213.6 / 323.7 | 1 | 2 | 5/6 | 62.0 | 86.1 (7.7-164.5) | 292 | 1 / 1 | 1/2 | 2/5 ✗ | 213.6 ✓ | 1/2 ✓ | 2/2 ✓ | fail | reference |
| 2-SAT n100 α4 m400 | a · 1,2,3,4,5 | 5 | 5 | 4 | 1 | 173.7 / 173.7 / 173.7 | 31 | 1 | 3/3 | 1.5 | 1.7 (1.7-1.7) | 3 | 0 / 0 | 0/1 | 5/5 ✓ | 8.1 ✗ | 0/1 ✗ | 1/1 ✓ | fail | unsuitable |
| 2-SAT n100 α4.5 m450 | b · 1,2,3,4,5 | 5 | 3 | 1 | 2 | 66.5 / 96.3 / 126.0 | 32-35 | 2 | 6/6 | 2.0 | 1.7 (1.0-2.3) | 3 | 0 / 0 | 0/2 | 3/5 ✗ | 66.5 ✓ | 0/2 ✗ | 2/2 ✓ | fail | unsuitable |
| 2-SAT n100 α5 m500 | b · 1,2,3,4,5 | 5 | 2 | 0 | 2 | 31.1 / 57.6 / 84.0 | 35 | 2 | 6/6 | 2.2 | 1.7 (1.0-2.3) | 3 | 0 / 0 | 0/2 | 2/5 ✗ | 57.6 ✓ | 0/2 ✗ | 2/2 ✓ | fail | unsuitable |
| 2-SAT n100 α6 m600 | a · 1,2,3,4,5 | 5 | 1 | 0 | 1 | 752.7 / 752.7 / 752.7 | 50 | 1 | 3/3 | 6.3 | 4.0 (4.0-4.0) | 7 | 0 / 0 | 0/1 | 1/5 ✗ | 752.7 ✓ | 0/1 ✗ | 1/1 ✓ | fail | unsuitable |
| 2-SAT n150 α3 m450 | a,b · 1–10 | 10 | 9 | 6 | 3 | 32.3 / 36.4 / 65.1 | 23-24 | 3 | 9/9 | 1.2 | 1.0 (1.0-1.3) | 2 | 0 / 0 | 0/3 | 9/10 ✓ | 14.1 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |
| 2-SAT n150 α3.15 m472 | b · 1,2,3,4,5 | 5 | 4 | 3 | 1 | 300.9 / 300.9 / 300.9 | 26 | 1 | 3/3 | 3.5 | 2.0 (2.0-2.0) | 3 | 0 / 0 | 0/1 | 4/5 ✓ | 12.7 ✓ | 0/1 ✗ | 1/1 ✓ | fail | unsuitable |
| 2-SAT n150 α3.3 m495 | b · 1,2,3,4,5 | 5 | 4 | 1 | 3 | 34.1 / 170.8 / 226.6 | 25-28 | 3 | 9/9 | 1.5 | 1.0 (1.0-30.7) | 41 | 1 / 1 | 0/3 | 4/5 ✓ | 102.4 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |
| 2-SAT n250 α2.35 m588 | b · 1,2,3,4,5 | 5 | 4 | 2 | 2 | 71.1 / 340.7 / 610.3 | 18-22 | 2 | 6/6 | 1.6 | 1.0 (1.0-1.0) | 1 | 0 / 0 | 0/2 | 4/5 ✓ | 37.2 ✓ | 0/2 ✗ | 2/2 ✓ | fail | unsuitable |
| 2-SAT n400 α2 m800 | a,b · 1–10 | 10 | 10 | 6 | 4 | 43.0 / 144.9 / 412.7 | 18-20 | 4 | 12/12 | 8.3 | 8.3 (1.3-58.7) | 82 | 1 / 2 | 1/4 | 10/10 ✓ | 18.1 ✓ | 1/4 ✗ | 4/4 ✓ | fail | promising |
| 2-SAT n400 α2.15 m860 | b · 1,2,3,4,5 | 5 | 5 | 1 | 4 | 146.6 / 178.9 / 380.6 | 18-21 | 4 | 12/12 | 3.7 | 1.7 (1.0-25.7) | 35 | 0 / 2 | 1/4 | 5/5 ✓ | 147.6 ✓ | 1/4 ✗ | 4/4 ✓ | fail | promising |
| 2-SAT n400 α2.3 m920 | b · 1,2,3,4,5 | 5 | 3 | 0 | 3 | 53.5 / 144.9 / 367.2 | 20-23 | 3 | 9/9 | 2.8 | 1.0 (1.0-1.7) | 2 | 0 / 1 | 0/3 | 3/5 ✗ | 144.9 ✓ | 0/3 ✗ | 3/3 ✓ | fail | unsuitable |

The 29 cells with **no** eligible instance are, by RC2 outcome:
- 11 have every instance certified at ≤ 30 s: 3-SAT n 50–150 at α 4.26–6,
  and 2-SAT n 100–250 at α 2–3;
- 16 are fully censored at the high-α corners;
- 2 are mixed: 3-SAT n 150 α 4.6 (4 below, 1 censored); 2-SAT n 250 α 2.5
  (3 below, 2 censored).

No memetic run exists for any of them, and none is counted as trivial.

### 2.2 The §5.3 cell rule, literally, with denominators

From `CORPUS_CALIBRATION_GOALS.md` §5.3, unchanged:

| condition | test | denominator |
|---|---|---|
| r1 | RC2 certified ≥ 0.8 | all generated seeds of the cell |
| r2 | median certified `solve_s` ≥ 10 s | certified instances |
| r3 | Q2 instances ≥ ½ | eligible instances tested with the primary arm |
| r4 | ≥ 1 success on every instance | eligible instances tested with the primary arm |

**One reading is made explicit, not changed.** For r4, "every certified
instance in the cell" is read as "every *eligible* certified instance". By
decision, no memetic run exists below 30 s, so this is the only computable
reading. Instances without a memetic measurement are listed as `not_run` and
are never counted as success, failure or trivial.

Result: **one cell passes, `max3sat_n250_a4.26`:**
- r1: 9/10 certified;
- r2: median 50.8 s;
- r3: Q2 5/6;
- r4: 6/6.

The M2 read-out §6.2 had computed the rule "on pool instances only". That
dropped r1 and r2, and is why it reported two more passing cells:

| cell | r1 | r2 | r3 | verdict |
|---|---|---|---|---|
| 3-SAT n 250 α 4.35 | **2/5 ✗** | ✓ | 1/2 ✓ | fails |
| 3-SAT n 150 α 4.8 | **3/5 ✗** | **median 1.9 s ✗** | 1/1 ✓, from a single instance (#33, 34.9 s, c\* = 2) | fails |

### 2.3 Three levels kept apart, and where "seven" came from

| level | definition | count |
|---|---|---|
| run | a run that goes beyond generation 1 | 15 instances; these sit in **8 cells** |
| instance | Q2 non-trivial (success < 3/3 or median TTT ≥ 45 s), primary arm | 9 instances in **5 cells**: 3-SAT n250 α4.26 (5), n250 α4.35 (1), n150 α4.8 (1); 2-SAT n400 α2.0 (1), n400 α2.15 (1). The 0.5 s arm adds none. |
| cell | §5.3 r1–r4 | **1 cell** |

The "seven" is the prose list in read-out §6.2: 3-SAT n250 α4.26 and
α4.35, n150 α4.8, n70 (#16), plus 2-SAT n400 α2.0 and α2.15, n150 (#31).
It mixes two levels:
- five of its cells have a Q2 instance;
- two (#16, 3-SAT n70 α6; #31, 2-SAT n150 α3.3) have only runs beyond
  generation 1. Neither instance is Q2: median TTT 12.4 s and 37.1 s;
- it also leaves out 2-SAT n400 α2.3, where #48 has a run beyond
  generation 1.

**Isolated support.** Cells whose only evidence of memetic work is a single
instance:
- 3-SAT n70 α6 (#16);
- 3-SAT n150 α4.8 (#33);
- 3-SAT n250 α4.35 (#39);
- 2-SAT n150 α3.3 (#31);
- 2-SAT n400 α2.3 (#48).

In #16, #31 and #48 the evidence is runs beyond generation 1 without Q2.
The column `isolated_support` in the CSV marks these cells.

**Numbering.** `#N` is always the full-pool `pop_idx` (1–70). The M2 pilot
used its own 1–10 numbering. For example, pilot #8 is full-pool #39 and
pilot #9 is full-pool #33. `candidate_instances.csv` carries both columns.

---

## 3. Classification (no ρ)

The rule is in `candidate_cells.py` and was written before the table was
first printed:
1. **unsuitable** if the cell has no eligible instance;
2. **reference** if k = 3 and n = 250;
3. **supported** if r1–r4 all pass;
4. **promising** if the cell fails, but r2 and r4 pass, it has ≥ 1 Q2
   instance, and every failing condition among r1 and r3 would pass with one
   more favourable instance;
5. **unsuitable** otherwise.

| category | cells | why | diversity beyond the 26 historical instances |
|---|---|---|---|
| **existing reference regime** | 3-SAT n250 α4.26 (passes §5.3), n250 α4.35 (fails r1) | the historical uuf250 regime regenerated | **none**: same n, density and c\* = 1. Not a justification for expansion. *r2: no new instances will be generated here; the existing rows are reference evidence only.* |
| **supported expansion candidate** | — | no non-reference cell passes §5.3 | — |
| **promising, under-supported** | 2-SAT n400 α2.0; 2-SAT n400 α2.15 | r1, r2 and r4 pass; r3 is 1/4 against ≥ 2/4. Wilson 95 % interval for 1/4 is 0.05–0.70, so 25 % and 50 % cannot be told apart. Across the n = 400 row, 5 of 11 eligible instances have runs beyond generation 1, more than any other non-reference row. | **real:** clause length 2; c\* 18–21 (a different c\* regime); m 800–860, the largest 2-SAT clause sets. RC2 time here is almost all per-call cost (read-out §3.3), not core count. |
| **unsuitable** | all other 20 cells with eligible instances, incl. 3-SAT n150 α4.8 (fails r1 and r2, single instance), 2-SAT n400 α2.3 (r1 3/5, Q2 0/3), all 3-SAT n ≤ 100 (Q2 0/34 eligible; 3-SAT n50 is first-call on 14/14) | — | the n ≤ 100 3-SAT and n ≤ 250 2-SAT cells *would* add diversity (c\* 4–50, α 3–9), but the memetic solver does no measurable work there under the agreed RC2 window |

---

## 4. What can be decided now, and what can be frozen

**Decided from existing results alone:**
- No Max-3-SAT expansion cell exists under the current rules, and none is
  worth reinforcing:
  - 3-SAT n ≤ 100 is memetic-trivial: 0 Q2 among 34 eligible instances;
  - 3-SAT n = 150 has the c\*-ladder problem of the B1 read-out. Its window
    yield is 2/15 across α 4.6–5.0, and its one Q2 instance is c\* = 2
    at 34.9 s, next to the historical uuf200 points (n = 200, c\* = 2);
  - α moves at n = 250 are explicitly not diversity (decision 7).
  - **No further Max-3-SAT refinement at n ≤ 250 is proposed.** *[r2: n > 250
    is a separate, pending assessment (§4a). Absence of evidence for a new
    regime there is not evidence of absence.]*
- 2-SAT n ≤ 250: 0 Q2 among 15 eligible instances. Closed.
- *[superseded r2]* The reference cell passes and could be frozen now
  (protocol §3, stratum R). **By decision, no new reference instances are
  generated.** The cell's pass is recorded as evidence about the historical
  regime only.

**Not decidable from existing results:** whether 2-SAT n = 400 (α 2.0 /
2.15) meets the memetic condition. This is the only open Max-k-SAT question,
and it decides whether the Max-k-SAT freeze contains any expansion stratum.

**Recommendation.**
- Freeze **no expansion stratum now**.
- Run `calib_c` (§5, **submission pending**), then decide whether 2-SAT
  n = 400 becomes a frozen stratum. *[superseded r2: "covering stratum R
  (reference, replication)", and "R can be frozen today". R is removed.]*
- Do not hold the Max-k-SAT freeze for MaxCut or the other families (§6).

**No constraint needs to be challenged** to answer the question. Two things
to know:
- The Q2 seconds threshold depends on m (§1).
- If `calib_c` fails, the generated Max-k-SAT part of the corpus has no
  frozen stratum unless the n > 250 Max-3-SAT assessment (§4a) yields one.
  Diversity beyond the historical corpus would then come from the other
  families. This is a finding, not a reason to relax a rule.

### 4a. Pending (r2): Max-3-SAT at n > 250 — to assess next session, not done

> **r3:** widened to larger n in **both** Max-2-SAT and Max-3-SAT
> (`NEXT_SESSION_CONTEXT.md` §0, R3-b/R3-c). The Max-3-SAT text below still
> holds as one half of that assessment.

**Question.** Are there cells at n > 250, with matching clause counts and
densities, that:
- give c\* > 1 (or a c\* spread) while RC2 still certifies in 30 s < t ≤
  900 s; and
- make the memetic solver do meaningful work (Q2)?

**Four aims, kept apart:**
1. *reinforcing* an already tested cell. Excluded for n = 250 by decision;
2. *exploring* new sizes and densities;
3. *adding size diversity* (n beyond 250);
4. *broadening the optimum-cost range* (c\* > 1 at large n).

**Existing evidence to start from** (no new calculation done):
- At n = 250, α 4.26 certifies c\* 0–1 in 0.5–388 s with one of 10 censored.
  α 4.35 certifies 2 of 5 (c\* 1). α ≥ 5 is fully censored: calib_a,
  lower bounds in `profile_calib_a_all.jsonl`; the `calib_b.yaml` comment
  records "alpha=5 is censored at LB 2".
- The B1 per-row slope at n = 250 is 2.32 decades of RC2 time per unit of
  c\* (`CALIB_B_B1_READOUT.md`). Taken at face value this puts c\* = 2 far
  above 900 s at n = 250, and per-call cost rises with n. **That is the main
  risk.**
- It is an extrapolation from a few c\* = 1 points, not a measurement at
  n > 250. The 3-SAT n = 150 row shows that per-instance variance can still
  place single c\* = 2–3 instances in the window (772 s, c\* = 3).

**Next session should:** use the calibration boundary (certified / censored
counts and the LB of censored rows per (n, α)) to either:
- recommend against exploring, with that evidence; or
- propose a small, bounded exploratory grid: e.g. 2 values of n > 250 × 2
  densities just above α_c × 5 seeds, the B1 two-α hedge, with a fixed
  task count and fixed stopping criteria (no adaptive extension, no α
  re-placement).

No selection toward ρ. Memetic runs only on RC2-eligible instances, primary
arm, as for every batch.

---

## 5. The `calib_c` reinforcement batch (pre-registered here, before any calib_c row exists)

> **Status (r2): prepared, preserved, submission pending; not approved.**
> **Status (r3): on hold, to be reassessed against the larger-n direction
> (keep / revise / replace). The design below is not claimed to be wrong.**

### 5.1 Cells and why

| cell | in | why | out |
|---|---|---|---|
| 2-SAT n400 α2.0 (m 800) | ✓ | r1 10/10, r2 18.1 s, r4 4/4; r3 1/4, one instance short | — |
| 2-SAT n400 α2.15 (m 860) | ✓ | r1 5/5, r2 147.6 s, r4 4/4; r3 1/4, one instance short | — |
| 2-SAT n400 α2.3 | | | already fails r1 (3/5); Q2 0/3 |
| 3-SAT n150 α4.8 | | | fails r1 and r2; single Q2 instance; next to the historical regime; window yield ≈ 1/5 |
| 3-SAT n250 α4.35 | | | reference regime; α moves are not diversity |
| new n or α (e.g. 2-SAT n = 600) | | | would be an adaptive grid search. Not proposed until the n = 400 question is answered. It remains a possible optional extension. |

### 5.2 Seeds, generation and task counts

- **Grid:** `instancegen/grids/calib_c.yaml`. 2 cells × generator seeds
  **101–120**, giving 40 instances.
- **Seed ranges:**
  - disjoint from calib_a/b (1–10);
  - below every final-evaluation seed (≥ 1001). No calib_c instance can enter
    a final evaluation.
- **Generated:** `cluster_staging_maxsat/data/generated/calib_c/` (40 files,
  gitignored) and `manifest.jsonl` (tracked, `git_sha 28d4da6`). `--check`
  passes.
- **RC2 step:** `scripts/manifest_calib_c_rc2.txt` + `.sha256`. Line N is
  array task N. Tasks 1–20 are α = 2.0, tasks 21–40 are α = 2.15.
- **Memetic step, after RC2:** `scripts/make_calib_c_memetic_manifest.py`.
  - **Runs on:** RC2-eligible instances only, under the same rule as §1.
    Never on the other instances.
  - **Arm:** the primary arm only (`p40_ls3p5`), solver seeds 1–3, 900 s,
    stop at the optimum. A test asserts this is the a35 arm of the M2 full
    pool.
  - **Not-run list:** every other instance is written to
    `manifest_calib_c_m2.not_run.csv` with its reason.
  - **Refuses to build** while any RC2 row is missing or failed, and if the
    PySAT version differs from calib_a/b's 1.9.dev3.

### 5.3 Compute

| step | tasks | worst case | expected (from the 15 + 8 existing instances of these cells) |
|---|---:|---:|---:|
| RC2, cap 900 + 60 | 40 | 40 × 960 s = **10.7 CPU-h** | 20 × 80 s + 20 × 178 s ≈ **1.4 CPU-h** (0/15 censored so far) |
| memetic, a35 × 3 seeds | ≈ 72 (≈ 8 + 16 eligible × 3); ≤ 120 | 120 × 960 s = **32 CPU-h** | 8 × 3 × 40 s + 16 × 3 × 17 s ≈ **0.5 CPU-h** |

- **Elapsed time at %30:** RC2 is 2 waves; memetic ≤ 4 waves. Queue delay
  is separate and not estimated.
- **Resources:** 1 CPU, 8 GB, `--time 00:20:00`, as for A1, B1 and M2.

### 5.4 Selection, stopping and decision rules

**Fixed batch.**
- No second round, no α change, no adaptive top-up.
- An RC2 or memetic task in class *failed* or *infra* is re-run until it has a
  valid row. That is not an extension.
- A memetic `watchdog` row is investigated before any resubmission, as in M2.

**Decision per cell, rule unchanged.** Pool all instances of the cell across
calib_a, calib_b and calib_c, then apply §5.3 r1–r4 with the §2.2
denominators:
- r1: certified / 30 or 25 generated;
- r2: median certified time ≥ 10 s;
- r3: Q2 among eligible tested instances (primary arm) ≥ ½;
- r4: success > 0 on every eligible tested instance.

Command: `candidate_cells.py --batches calib_a calib_b calib_c
--memetic-agg … --decision`. It prints the verdict.

**Pass ⇒ the cell becomes a Max-2-SAT expansion stratum** in the protocol
(§3 there):
- final generator seeds ≥ 2001;
- G is set from the pooled window yield.

**Fail ⇒ the cell is recorded as failing.**
- It is not reinforced again and not rescued by a rule change.
- Its rows stay calibration data.

The two cells are decided separately. The pooled n = 400 figure is reported,
but decides nothing.

**What the batch can resolve.** With about 12 (α 2.0) and about 20 (α 2.15)
tested instances, the probability that the unchanged rule passes is:

| true Q2 rate | α 2.0 (N ≈ 12) | α 2.15 (N ≈ 20) |
|---|---|---|
| 25 % | 0.05 | 0.01 |
| 50 % | 0.61 | 0.59 |
| 60 % | 0.84 | 0.87 |

From the current 1/4 per cell, a pass is unlikely. **Running the batch is
still the cheapest way to get a firm answer instead of a four-instance
guess.**

**What is reported whatever the outcome:**
- the Q2 fraction with its Wilson interval;
- the beyond-generation-1 fraction;
- the window yield.

None of these, and no ρ, enters the decision beyond r1–r4.

### 5.5 What the batch does not do

- It does not run the 0.5 s arm.
- It adds no instrumentation inside polish calls.
- It runs no uniform or JW multistart.
- It changes no source file.

---

## 6. Other generator families

### 6.1 Inventory, verified on disk

| family | implemented | on disk | screened (RC2) | memetic | notes |
|---|---|---|---|---|---|
| random Max-3-SAT / Max-2-SAT (pure soft) | ✓ `instancegen.generate` | calib_a/b/c | 290 (+40 prepared) | 70 | this document |
| partial random k-SAT (`hard_ratio > 0`) | ✓ (`instancegen/feasible.py` guarantees a satisfiable hard part) | none | none | 4-instance workstation probe only (§8) | excluded; §8 |
| **MaxCut, Erdős–Rényi (G3)** | **✗** (`instancegen/maxcut.py` does not exist) | — | — | — | planned (generator plan Step 1a) |
| **MaxCut, torus (G4)** | **✗** | — | — | — | spec needs the fix in §6.3 |
| reweighted twins (G5) | ✗ (`reweight.py` does not exist) | — | — | — | weighted; separate track (§6.4) |
| planted fixtures (G6) | ✗ | — | — | — | test fixtures only, never corpus |
| MSE-2016 `maxcut/dimacs-mod` (62), `maxcut/spinglass` (5): stratum S1 | n/a (published) | ✓ `more_data/ms_crafted/ms_crafted/maxcut/` | 3 of 67, at 300 s, workstation (c\* 2 / 17 / 49 in 0.006–22 s) | none | the 900 s cluster screen was never run; its sbatch is archived (`scripts/archive/mse16/`) |
| set covering (MSE `scpcyc`, `scpclr`) | n/a | ✓ | 12/12 timeouts up to 1800 s (EvalMaxSAT) | — | out: hard clauses and no certification |
| Max-Clique / Max-Independent-Set | ✗ | — | — | probe only (§8) | reopened as an option (§8.5) |

### 6.2 What each family adds that the random Max-k-SAT grid cannot

- **ER MaxCut (unweighted)** changes the *origin* to graph structure, with
  clause length 2.
  - Every variable appears only in symmetric clause pairs, so the JW prior
    is exactly 0.5 on every variable. Memetic seeding has no information to
    use, which differs from random k-SAT.
  - c\* = |E| − maxcut is expected in the tens. This is a c\* decade the
    3-SAT window cannot reach, and it comes from a different generator than
    2-SAT.
  - It is *not* frustrated by design. Frustration comes only from the random
    odd cycles.
- **Signed ±J torus (unweighted, frustrated)** gives designed sparse
  structure: degree exactly 4 and n decoupled from density. Frustration is
  set by the signs and can be tuned.
  - It is the closest generated analogue of the MSE `spinglass` instances,
    which RC2 certifies.
  - It is a different object from ER MaxCut: a fixed lattice versus random
    sparse graphs.
- **S1 published structured instances** have non-generated origin. This is
  the axis a referee asks about. They cost nothing to generate, but they are
  a **fixed finite set**: no fresh seeds exist, so calibration and final
  evaluation cannot be separated by seed (protocol §5).

### 6.3 The torus issue, resolved

- **Unweighted even × even torus with all edges "cut-preferring":** the
  graph is bipartite, so c\* = 0. It is a known-optimum fixture (cost 0),
  never a corpus instance. This is already in goals §5.5.
- **Odd side L:** c\* ≥ 2L, about 18–22 at the planned sizes, with little
  spread (scope note). It is not a useful stratum on its own.
- **Resolution: stratum E becomes a ±J spin glass on the L × L torus.** Each
  edge gets an independent fair sign.
  - A positive (antiferromagnetic) edge gets `(x_u ∨ x_v)`, `(¬x_u ∨ ¬x_v)`.
  - A negative (ferromagnetic) edge gets `(x_u ∨ ¬x_v)`, `(¬x_u ∨ x_v)`.
  - All weights are 1.
  - Cost is the number of unsatisfied (frustrated) edges, and c\* is the
    ground-state energy offset.
  - Frustration comes from plaquettes with an odd number of negative edges,
    so **even sides are fine**.
- `MaxCutParams` gains `couplings ∈ {cut, pm1}`. With `topology=torus` the
  corpus uses only `pm1`; `cut` exists for the bipartite fixture.
- Fixtures to assert in `verify.py`:
  - all-positive even torus → c\* = 0;
  - all-negative torus (pure ferromagnet) → c\* = 0;
  - gauge invariance: flipping a vertex's spin and the signs of its 4 edges
    leaves c\* unchanged.
- Caveat to record, not to assume away: planar 2D ±J ground states are
  polynomial by matching, and the torus is nearly planar. Exact-solver
  difficulty could therefore be low, and RC2 behaviour here is an empirical
  question for the calibration gate.

### 6.4 Weighted extensions, kept separate

- **Weighted twins (G5)** change weights only, on a byte-identical clause
  set. They form a separate *weighted track*. Their unweighted bases must
  first be frozen strata.
- A twin is re-certified. c\* is not preserved.
- Twins never count toward an unweighted stratum's sample size.
- RC2's behaviour changes on weighted input (stratification is no longer
  moot), so the solver configuration is re-stated for that track.
- Weighted Max-Clique with big-weight conflicts is not a substitute for real
  hard clauses (§8): it moves weightedness and structure at once.

### 6.5 Calibration gate per family (each family freezes on its own)

- **Order:**
  1. implement and verify (`verify.py` fixtures, cost-semantics assertion);
  2. RC2 screen on ≥ 2 parameter points per intended stratum × 5 seeds, cap
     900 + 60. Two points per row is the hedge that carried B1;
  3. primary-arm memetic, 3 seeds, on RC2-eligible instances only;
  4. apply §5.3 r1–r4 unchanged;
  5. freeze the passing cells in the protocol;
  6. fresh seeds.
- **No family is assumed** to reach the RC2 window or to need real memetic
  effort. A family whose cells all fail is reported as failing, as 3-SAT
  n ≤ 100 is here.
- **S1 differs:** a single RC2 screen of all 67 files at 900 s, then the
  memetic arm on every eligible file. There is no cell selection, so there
  is no seed separation to protect.
- **Expected first steps for MaxCut** (the proposed next implementation
  milestone, r2; not started):
  - ER: n ∈ {60, 100, 150} × average degree {3, 4, 6};
  - ±J torus: L ∈ {8, 10, 12, 14};
  - 5 seeds each;
  - about 100 RC2 tasks, ≤ 27 CPU-h worst case.
  - The grid is a starting proposal and is fixed in its own plan before it
    runs.

---

## 7. Proposed final protocol

See [`CORPUS_V1_PROTOCOL_DRAFT.md`](CORPUS_V1_PROTOCOL_DRAFT.md):
- strata;
- environments;
- RC2 rule;
- seeds;
- target and effort definitions;
- censoring and failure handling;
- analyses;
- accounting;
- the open decisions it needs from you.

---

## 8. Hard-clause instances: reassessment of the exclusion

### 8.1 What the repository said, and what it rested on

- **The stated reason** (scope note §1 reason 1, generator plan §3.1 and E3,
  handoff §6a): the fitness "collapses every infeasible assignment to about
  −1e9 − 1e6·hv, so the search gets no gradient toward feasibility". The
  only measurements behind it:
  - **`00000293`** (judgment aggregation: 18,508 variables, 134,142 hard
    clauses, 78 soft units). Five 1800 s runs never reached feasibility
    (best hv 4,249). Glucose found a feasible model in 0.04 s, at cost 49
    against c\* 43.
  - **`00000385`** (6,604 variables, 48k hard clauses). One 60 s smoke ended
    at hv = 1.
- **No generated hard-clause instance had ever been run through the memetic
  solver.**
- **Confound:** on `00000293` the polish loop runs at about 52 flips/s,
  because it does two O(m) scans over 134k clauses per flip
  (`archive/TIER2_MSE_FEASIBILITY.md` §3). A 0.5 s call is about 26 flips
  against about 4,000 violated clauses. The failure there cannot be
  attributed to the hard-clause handling itself.

### 8.2 What the code actually does (staging `src/`, verified by reading)

| stage | behaviour with hard clauses | file |
|---|---|---|
| fitness | `soft if hv == 0 else −1e9 − 1e6·hv`. This **is** a gradient: infeasible individuals are ranked by their number of hard violations. What is lost is soft-objective information among infeasible individuals. "No gradient" is inaccurate. | `evo/population.py` `evaluate` |
| init | JW prior over soft clauses only. A variable that appears only in hard clauses is a fair coin. No attempt at feasibility. | `population.py` `jw_priors`, `init_seeds` |
| crossover | `clause_aware_crossover1`: in index order, at each parental disagreement, it picks the bit that newly violates fewer hard clauses. Greedy, no backtracking, no repair. | `evo/operators.py` |
| mutation | `mutate1` rejects flips that break a satisfied hard clause. **But it is passed `ind.hard_satisfied` of the last *initial* member** (`evo/memetic.py:152`), a stale vector. On hard-clause instances the guard checks the wrong assignment. Latent bug, inert on all-soft instances (audit §5(d)). | `operators.py`, `memetic.py` |
| polish (hard phase) | Picks an unsatisfied hard clause and accepts **only flips that strictly reduce** the hard-violation count (dh < 0). There are no plateau, noise or uphill moves; the "explore" branch also requires dh < 0. When no such flip exists, the iteration is a **no-op**, and the call idles until its time limit (applied flips do not advance, so the 12,500-flip cap is never reached). | `sat/walksat.py` `walksat_polish` |
| polish (feasible phase) | `hard_safe=True`: any flip that would break a hard clause is skipped. Feasibility is preserved, but soft improvements that need a temporary hard break are impossible, and a stuck call again idles to the time limit. | same |

### 8.3 Workstation probe (not a measurement)

Script: `scripts/hard_clause_probe.py`. Output:
`results/hard_clause_probe/probe_20261006.txt`.

Setup:
- unchanged solver and the primary configuration;
- 2 seeds × 20 s per instance;
- 4 generated instances: partial random 3-SAT with n = 150, soft ratio 2 and
  hard ratio 2.0 / 3.0 / 4.0; plus a Max-Clique encoding of G(60, 0.5), with
  soft `(x_v)` and hard `(¬x_u ∨ ¬x_v)` per non-edge;
- operator checks on pairs of hard-feasible Glucose models (random phases).

| | partial 3-SAT hr 2.0 (c\* 0) | hr 3.0 (c\* 2) | hr 4.0 (c\* 8) | clique (c\* 53) |
|---|---|---|---|---|
| (i) memetic reaches feasibility from its own init, 20 s | yes; cost 8–10 against optimum 0 | **no**, hv 1 and 4 | **no**, hv 7 and 8 | yes; cost 54 |
| JW init feasible | 0/40 | 0/40 | 0/40 | 0/40 |
| (ii) crossover child of 2 **feasible** parents feasible | 2/20 | **0/20** | **0/20** | 20/20 |
| … after mutate1 (correct vector) | 3/20 | 0/20 | 0/20 | 20/20 |
| … after one polish call | 12/20 | **0/20** (hv median 2.5) | **0/20** (hv median 5.5) | 20/20 |
| (iii) polish from a feasible Glucose model: cost before → after | 35 → 12 (typical) | 41 → 24 | 39 → 33 | 56 → 55 |
| wall per polish call | 3.50 s | 3.50 s | 3.50 s | 3.50 s |

Every call ran to the 3.5 s time limit. On all-soft instances the
12,500-flip cap binds at 1.2–3.0 s. This confirms the idle no-op iterations
of §8.2.

### 8.4 The three difficulties, separated

1. **Finding an initial feasible assignment.**
   - Hard for the solver on mixed-sign hard clauses at hr ≥ 3: the
     strict-descent polish stalls at hv 1–8.
   - Trivial for a SAT solver.
   - On the conflict-clause encoding the solver finds it unaided, because
     setting any variable false never breaks a conflict clause.
2. **Preserving feasibility through crossover, mutation and polish.**
   - **This is the decisive failure for mixed-sign hard clauses.** Two
     feasible parents give an infeasible child almost always (0/20 at
     hr 3–4), and the polish cannot repair it.
   - With a SAT-seeded population, generation 1 would therefore contain 2
     feasible elites and about 38 infeasible children. That is the "different
     failure mode" that `archive/TIER2_MSE_FEASIBILITY.md` predicted; the
     probe confirms it on generated instances.
   - On the conflict-clause encoding, feasibility is preserved 20/20.
3. **Improving the soft objective from a feasible start.**
   - The polish does improve from feasible starts on partial 3-SAT.
   - It is hampered by `hard_safe`: on the c\* = 0 instance the 20 s runs
     ended at cost 8–10.
   - The probe cannot say what 900 s would reach.

**Your recollection, checked.**
- Partly supported: on `00000293` a Glucose model alone beat every EA run.
- Not sufficient: SAT-assisted feasible initialisation addresses difficulty
  1 only. Difficulty 2 needs repair after variation, a SAT-based decoder
  (soft-variable genome; handoff §6a), or escape moves in the polish's hard
  phase. Each of these is an algorithmic change, i.e. a new arm.
- **Roles:**
  - a SAT solver run on the hard clauses alone supplies feasibility and no
    objective information. That is legitimate initialisation, provided its
    time is charged to the run clock;
  - RC2 optimises and certifies the objective. It must never seed the
    memetic solver.

### 8.5 Decision

- **Mixed-sign hard clauses** (partial random k-SAT, set cover, judgment
  aggregation): **exclusion remains justified for the current solver.**
  - Verified reason: crossover and polish do not preserve feasibility, and
    the polish cannot escape hard-violation local minima (§8.2–8.4).
  - The old "no gradient" wording is withdrawn.
  - Reconsider only when a separately specified arm (repair, decoder, or
    hard-phase noise) passes the operator probe (≥ 95 % feasible children
    from feasible parents) and reaches feasibility on every seed in 900 s
    runs on generated instances. That arm would be a new algorithm and
    cannot share a stratum or a table with the current one.
- **Conflict-clause (anti-monotone) hard clauses** (Max-Independent-Set /
  Max-Clique on generated graphs): **inclusion is reopened as an option.**
  The scope note's reasons for exclusion, rechecked:
  - reason 1 does not hold here (feasibility found and preserved);
  - reason 2 is moot if real hard clauses are kept;
  - reason 3 is moot for generated graphs;
  - reason 4 ("c\* out of RC2's reach") was an inference and is contradicted
    at n = 60: RC2 proved c\* = 53 in 0.04 s.
  - **Two real issues remain:**
    - (a) polish calls become **time-bound** (idle to 3.5 s), so effort per
      call is host-dependent, as in the 0.5 s arm, and not comparable with
      the all-soft strata. Such a stratum must be reported on its own and
      never pooled;
    - (b) whether the RC2 window can be reached at sizes where the memetic
      solver does real work is unknown.
- **Smallest diagnostic that would resolve the option:**
  - a ~40-line G(n, p) independent-set generator plus `verify.py` fixtures
    (empty graph → c\* = 0; complete graph → c\* = n − 1);
  - a workstation 60 s RC2 pre-screen to place 2 sizes;
  - a cluster RC2 screen of 2 cells × 5 seeds (10 tasks, ≤ 2.7 CPU-h);
  - the primary arm, 3 seeds, on the eligible instances (≤ 30 tasks,
    ≤ 8 CPU-h), recording final hv (must be 0 on every run).
  - Proposed, not prepared; it needs your approval as its own milestone.
- **Optional, not needed for the decision:** 3 partial 3-SAT instances × 3
  seeds × 900 s with the unchanged solver (9 tasks, ≤ 2.4 CPU-h). It would
  confirm difficulty 1 at full budget; the operator-level evidence already
  decides inclusion for this solver.

These conclusions are also recorded in the central documents:
- `CORPUS_GENERATOR_PLAN.md` §3.1 and E3;
- `CORPUS_FAMILY_SCOPE_NOTE.md` §1;
- `CORPUS_CALIBRATION_GOALS.md` §4.2 and §5.5;
- the calibration log, Checkpoint 8;
- a pointer in the handoff §6a.

---

## 9. Cluster commands for `calib_c` (prepared, not run; submission pending approval)

> **r3: do not run.** `calib_c` is on hold pending reassessment (§5 status).
> If it is revised or replaced, these commands are superseded too.

`<user>@<cluster>` is the only placeholder.

```bash
# 0. workstation: commit first, so MAXSAT_GIT_SHA names a commit that contains calib_c
cd /home/mashe/maxsat-lab_new/maxsat-lab
git add -A instancegen/grids/calib_c.yaml instancegen/tests/test_cli.py \
    cluster_staging_maxsat/data/generated/calib_c/manifest.jsonl \
    cluster_staging_maxsat/scripts cluster_staging_maxsat/tests \
    cluster_staging_maxsat/results/corpus_freeze_prep cluster_staging_maxsat/results/hard_clause_probe docs
git commit            # then: SHA=$(git rev-parse HEAD)

# 1. workstation -> cluster (carries data/generated/calib_c/, 40 files)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# 2. login node: RC2 step (40 tasks)
cd ~/maxsat-lab && sha256sum --quiet -c scripts/manifest_calib_c_rc2.sha256 && echo SHA_OK
cd scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_calib_c_rc2.txt OUTDIR=results/profile_calib_c bash submit_rc2_profile.sh
MANIFEST=manifest_calib_c_rc2.txt OUTDIR=results/profile_calib_c bash submit_rc2_profile.sh   # record job id
RESUME=1 MANIFEST=manifest_calib_c_rc2.txt OUTDIR=results/profile_calib_c bash submit_rc2_profile.sh  # only if rows are missing

# 3. cluster -> workstation, aggregate, build the memetic manifest (workstation)
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_calib_c/ cluster_staging_maxsat/results/profile_calib_c/
cd cluster_staging_maxsat
python3 scripts/aggregate_rc2_profile.py --batch calib_c        # 40 rows, 0 failed, pysat 1.9.dev3 x 40
python3 scripts/make_calib_c_memetic_manifest.py                 # prints task count and not-run count
cd .. && git add cluster_staging_maxsat && git commit           # manifest committed before the memetic submit

# 4. memetic step (login node, after a second rsync)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
cd ~/maxsat-lab/scripts
DRY_RUN=1 MANIFEST=manifest_calib_c_m2.tsv OUTDIR=results/calib_c_m2/tasks bash submit_m2_memetic.sh
MAXSAT_GIT_SHA=<sha of step-3 commit> MANIFEST=manifest_calib_c_m2.tsv OUTDIR=results/calib_c_m2/tasks \
    bash submit_m2_memetic.sh

# 5. back on the workstation: aggregate, then the pre-registered decision
rsync -av <user>@<cluster>:~/maxsat-lab/results/calib_c_m2/ cluster_staging_maxsat/results/calib_c_m2/
cd cluster_staging_maxsat
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_calib_c_m2.tsv \
    --outdir results/calib_c_m2/tasks --out-dir results/calib_c_m2/agg
python3 scripts/candidate_cells.py --batches calib_a calib_b calib_c \
    --memetic-agg results/m2_full_p40/agg/tasks.csv results/calib_c_m2/agg/tasks.csv \
    --out-dir results/calib_c_decision --decision
```

Two cautions:
- `candidate_cells.py` reads both arms of the M2 table. For calib_c
  instances only the primary arm exists. The decision uses the primary arm
  only, so this is consistent.
- `aggregate_rc2_profile.py` warns if PySAT is not uniform. The memetic
  builder refuses in that case.

---

## 10. Validation run this turn (workstation)

- `python -m pytest instancegen -q`: **82 passed** (79 + 3 new calib_c
  tests).
- `cd cluster_staging_maxsat && python -m pytest tests -q`: **137 passed, 3
  skipped**. This includes 15 new tests in `tests/test_calib_c_prep.py`. The
  3 skips are pre-existing: the local-multistart manifests were moved to
  `scripts/archive/` in `20ebac6`.
  - **One intermittent failure** appeared in one of 11 full-suite runs and
    did not recur. Its name was not captured, and it is not in a file this
    turn changed. Open.
- **`20ebac6` had broken `tests/test_rc2_row_state.py`:** it archived
  `rc2_row_state.py`, and the RC2 driver assumes it lives in `scripts/`.
  The four RC2 tool files were moved back with `git mv`, byte-identical:
  `rc2_profile_array.sbatch`, `submit_rc2_profile.sh`, `rc2_row_state.py`,
  `aggregate_rc2_profile.py`. The calib_a/b manifests stay archived.
- `generate-grid … calib_c.yaml --check`: 40/40. `sha256sum -c`: 40 OK.
- `DRY_RUN=1 submit_rc2_profile.sh`:
  `sbatch --array=1-40%30 … CAP=900,GRACE=60 rc2_profile_array.sbatch`.
- Local smoke through the real sbatch file (`LOCAL_SMOKE=1`, cap 20, PySAT
  1.9.dev15, scratch output, not a measurement):
  - task 1 completed: c\* = 16 in 7.7 s;
  - task 21 was killed with LB 18 recovered.
- `make_calib_c_memetic_manifest.py` refuses to run without
  `profile_calib_c_all.jsonl`, as designed.
- `candidate_cells.py` reproduces `instance_table.csv` on all 70 instances
  (Q2 under both arms, successes, `pop_idx`): 0 mismatches.

## 11. Files touched (uncommitted)

```
A  docs/CORPUS_FREEZE_PREP.md, docs/CORPUS_V1_PROTOCOL_DRAFT.md
M  docs/CORPUS_CALIBRATION_LOG.md (Checkpoint 8), docs/CORPUS_CALIBRATION_GOALS.md,
   docs/CORPUS_GENERATOR_PLAN.md, docs/CORPUS_FAMILY_SCOPE_NOTE.md,
   docs/M2_FULL_POOL_READOUT_AND_STATE.md (§6.2 amendment), more_data/CORPUS_BROADENING_HANDOFF.md (§6a pointer)
A  instancegen/grids/calib_c.yaml;  M instancegen/tests/test_cli.py
A  cluster_staging_maxsat/data/generated/calib_c/manifest.jsonl   (40 .wcnf gitignored)
A  cluster_staging_maxsat/scripts/manifest_calib_c_rc2.{txt,sha256}
A  cluster_staging_maxsat/scripts/{candidate_cells,make_calib_c_memetic_manifest,hard_clause_probe}.py
R  cluster_staging_maxsat/scripts/archive/rc2_calib/{rc2_profile_array.sbatch,submit_rc2_profile.sh,
   rc2_row_state.py,aggregate_rc2_profile.py} -> cluster_staging_maxsat/scripts/
A  cluster_staging_maxsat/tests/test_calib_c_prep.py
A  cluster_staging_maxsat/results/corpus_freeze_prep/{candidate_cells.csv,candidate_instances.csv,summary.json}
A  cluster_staging_maxsat/results/hard_clause_probe/probe_20261006.txt
M  cluster_staging_maxsat/DIVERGENCE.md (new staging scripts; no src/ change)
```
