# Next-session context — MaxSAT corpus calibration (read this first)

**Written:** 2026-10-06, at the end of the session that produced Checkpoints
8–9 of the calibration log. **Revised (r3) 2026-10-06** for the user's new
direction (§0, Checkpoint 10). §0 overrides anything below it that it
contradicts.

**Repository:** `/home/mashe/maxsat-lab_new/maxsat-lab`, branch `main`.
- The Checkpoint 8–9 work is **committed**: `9a562d0`, then `53aa53f`
  (staging log clean-up). HEAD is `53aa53f`.
- The r3 documentation edits (§0; the r3 notes in `CORPUS_FREEZE_PREP.md`,
  `CORPUS_V1_PROTOCOL_DRAFT.md`, `READING_LIST.md`; log Checkpoint 10) are
  **uncommitted**.

Nothing was submitted to Slurm. This workstation has no `sbatch` or ssh
alias, so every cluster step is a command the user runs on the login node.

---

## 000. Update 2026-10-08 (r5): SATLIB RC2 rows are back — read before §00

- The 263-task SATLIB RC2 array ran (job 22379183, 2026-10-07). Rows are in
  `cluster_staging_maxsat/results/profile_satlib/` and merged into
  `results/profile_satlib_all.jsonl` / `_env.jsonl` by
  `aggregate_rc2_profile.py --batch satlib`. 251 certified, 12 censored,
  0 failed; PySAT 1.9.dev3 throughout.
- **95 eligible** (certified, 30 < t ≤ 900 s): uuf200 34, uuf225 60, hole9 1;
  c\* = 1 ×70, c\* = 2 ×25. jnh has c\* up to 4 but solves in < 0.6 s.
  Full readout: [`SATLIB_BENCH_INTAKE.md`](SATLIB_BENCH_INTAKE.md) §8;
  note `RESEARCH_NOTES.md` N-2026-10-08-a.
- **Next milestone:** the memetic manifest builder for the 95 eligible
  instances (modelled on `make_calib_c_memetic_manifest.py`), plus the
  not-run list for the other 168. Not started.
- The "not yet submitted" wording in §00 below is superseded.
- **RC2 cap-3600 re-run prepared (2026-10-08; user submits).** It covers
  every instance under `data/` that hit the cap in every RC2 row it has,
  excluding `mse16/`, `raw/` and `more_data/`. That is 148 tasks: calib_a 88,
  calib_b 25, satlib 12, uuf250 23. The 3 `unsat_uuf_diff/uuf250-0{2,4,8}`
  copies are deduplicated by clause content. Files:
  `scripts/make_rc2_cap3600_manifest.py` (with `--check`),
  `scripts/manifest_rc2_cap3600.{txt,sha256,tasks.csv}`, and
  `scripts/submit_rc2_cap3600.sh`. The wrapper uses cap 3600 + grace 120,
  `--time 01:10:00`, `--mem 16G`, %30 and output
  `results/profile_cap3600/`. Worst case is 153 CPU-h, about 6 h elapsed.
  calib_c has no RC2 rows, so it is not included.
  The full data table, with a breakdown per cell, is in
  [`RC2_CAP3600_RERUN.md`](RC2_CAP3600_RERUN.md).
  Predictions were recorded before submission (§6, N-2026-10-08-b). When
  the rows are back, run `scripts/compare_cap3600_predictions.py` and fill
  in the §6 outcome.

---

## 00. Update 2026-10-07 (r4): SATLIB benchmark intake — read with §0

- **Research notes now have one entry point:**
  [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md). It indexes every document with
  research content and holds dated notes. Add new notes there.
- **SATLIB families** (`cluster_staging_maxsat/data/satlib_bench/`, 279
  files) are labelled, normalised in place and verified:
  [`SATLIB_BENCH_INTAKE.md`](SATLIB_BENCH_INTAKE.md).
  - 263 are unsatisfiable and go into **one** RC2 manifest,
    `scripts/manifest_satlib_rc2.txt`: 64 structured (bf, dubois, hole,
    jnh, pret) and 199 uuf200/uuf225.
  - 16 are satisfiable (all jnh) and are excluded.
  - PySAT, and therefore RC2, misread 209 of the originals. The originals
    are in `data/raw/satlib_bench_original_20261007.tar.gz`.
- **The RC2 screen is approved but not yet submitted.** It is one array:
  263 tasks at %30, at most 70.1 CPU-h, and about 2.6 h elapsed compute in
  the worst case. There is no pre-screen or screen-out, and satisfiable
  instances are excluded (intake §5, §6). The user submits it later, using
  the commands in intake §5.
- **Cite SATLIB** (Hoos & Stützle, SAT 2000) in any publication that uses
  these instances (`RESEARCH_NOTES.md` N-2026-10-07-e).
- **The emphasis is unchanged:** optima above 1 come from Max-2-SAT and
  MaxCut. The SATLIB families add origin and clause-length diversity
  (`RESEARCH_NOTES.md` N-2026-10-07-d).
- **The intermittent staging test failure (§8) is now named:**
  `tests/test_m2_prep.py::test_population_10_runs[p10_ls2p5]`. It is a
  timing-dependent bound under deadline clipping, and passes on rerun.

---

## 0. Direction as of r3 (2026-10-06, user) — read first

**New direction.** Explore grid points with **more variables, in both
Max-2-SAT and Max-3-SAT**, with clause-to-variable ratios chosen to suit each
size, in order to find hard instances. "Hard" means what it has meant
throughout: RC2-eligible (certified, 30 s < t ≤ 900 s) **and** the memetic
solver does meaningful work (Q2).

**Decisions recorded with it:**
1. **Effort stays in seconds** (ERT_s, median TTT). Calls and flips remain
   secondary diagnostics. Unchanged from D2.
2. **The 250-variable, optimum-1 reference stratum is preserved as it is.**
   No new instances are generated for it (D4 unchanged). Its evidence is the
   26 SATLIB instances plus the calib_a/b rows at n = 250, α 4.26 / 4.35.
3. **`calib_c` is to be reassessed against this direction.** This does not
   claim its construction was wrong: its two cells and seeds were derived
   correctly from the evidence under the earlier plan, which was to settle
   the n = 400 question. The question is now whether that two-cell n = 400
   reinforcement still belongs in a plan aimed at larger n. Options: keep it
   as prepared, revise it (for example, make n = 400 one rung of a larger-n
   ladder), or replace it. **Until that is decided, `calib_c` is on hold.**
   Its §9 commands in `CORPUS_FREEZE_PREP.md` are not to be run.
4. **This session changed documents only.** No instances generated, no
   manifests or submission scripts prepared, no jobs submitted, no cluster
   commands written.

**Existing evidence relevant to the direction.** Read off
`results/corpus_freeze_prep/candidate_cells.csv`; nothing new was computed.
"Elig" means certified in (30, 900] s.

| family | n | α with eligible instances (elig / generated) | c\* of eligible | Q2 / tested (3.5 s arm) | first fully censored α |
|---|---:|---|---|---|---|
| Max-2-SAT | 100 | 4.0 (1/5), 4.5 (2/5), 5.0 (2/5), 6.0 (1/5) | 31–50 | 0/6 | none in grid |
| Max-2-SAT | 150 | 3.0 (3/10), 3.15 (1/5), 3.3 (3/5) | 23–28 | 0/7 | 4.0 |
| Max-2-SAT | 250 | 2.35 (2/5); 2.5 (0/5) | 18–22 | 0/2 | 3.0 |
| Max-2-SAT | 400 | 2.0 (4/10), 2.15 (4/5), 2.3 (3/5) | 18–23 | 2/11 | 3.0 |
| Max-3-SAT | 150 | 4.8 (1/5), 5.0 (1/5) | 2–3 | 1/2 | 6.0 |
| Max-3-SAT | 250 | 4.26 (6/10), 4.35 (2/5) | 1 | 6/8 | 5.0 |

What these rows suggest. These are observations to test, not results:
- **The memetic side gets harder with n.** Q2 is 0/34 for Max-3-SAT at
  n ≤ 100 and 6/8 at n = 250. For Max-2-SAT it is 0/15 at n ≤ 250 and 2/11
  at n = 400. This supports the direction.
- **The RC2 window moves toward the satisfiability threshold as n grows.**
  For Max-2-SAT it moves from α 4–6 at n = 100 to α 2.0–2.3 at n = 400; the
  threshold is α = 1. For Max-3-SAT it moves from α 4.8–5.0 at n = 150 to
  α 4.26–4.35 at n = 250; the threshold is α ≈ 4.27. So a **fixed α list
  across n will not work**: at larger n the window lies at lower α than any
  tested cell. In Max-2-SAT, α 3.0 is already fully censored at n = 250
  and n = 400.
- **Max-2-SAT eligible c\* stays near 18–23 from n = 250 to n = 400.** One
  hypothesis for placing α at larger n is to aim at a c\* band rather than
  a fixed α. It is untested.
- **Max-3-SAT eligible c\* falls to 1 by n = 250.** At n > 250, cells that
  RC2 can certify may hold only c\* 0–1 instances. That would serve size
  diversity, but not the "c\* > 1" aim of the earlier n > 250 assessment
  (§5). Whether larger-n, c\* ≤ 1 cells are wanted is a decision. The
  preserved reference stratum is specifically n = 250, so it does not
  decide this.
- **Seconds-based effort and larger m.** Per-call cost grows with m: about
  1.25–3.0 s per call across the current pool. Larger instances therefore
  get fewer generations within 900 s, and the Q2 seconds threshold (45 s)
  means a different amount of search at different m. This is a property to
  report, not a reason to change the measure.

**Decisions left for the next session** (also in §8):
- **R3-a `calib_c`:** keep, revise, or replace (decision 3). If it is revised
  or replaced, `CORPUS_FREEZE_PREP.md` §5 gets a new dated revision before
  anything is generated or submitted. No calib_c row exists yet, so a
  revision now is not an adaptive change to a running batch.
- **R3-b larger-n grid design:**
  - which n values (Max-2-SAT beyond 400; Max-3-SAT beyond 250);
  - how to place α per n: a per-n band next to the observed window, a target
    c\* band, or a fixed list;
  - generator seeds per cell (disjoint from 1–10, 101–120 and ≥ 1001);
  - a two-α hedge per row, as in B1;
  - a fixed task count and worst-case CPU-h;
  - fixed stopping and decision rules: no adaptive top-up, no α
    re-placement after rows arrive;
  - memetic runs on eligible instances only, primary arm;
  - no selection toward ρ.
  - It must be a written plan approved before any generation.
- **R3-c Max-3-SAT c\* range at n > 250:** accept c\* ≤ 1 cells for size
  diversity, or require c\* > 1 (§5's original aim)? Evidence:
  [`RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`](RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md).
  - Under the fixed RC2 and window, eligible instances at n ≥ 250 have
    c\* = 1.
  - c\* = 2 at n = 250 has an estimated median of 0.6–5 ks: at best an
    occasional exception.
  - At n ≥ 300 even c\* = 1 nears the cap.
  - Higher density makes this worse.
  - The notes withdraw an earlier "hours" estimate, which came from the
    B1 slope.
- **R3-d priority:** larger-n k-SAT first, or MaxCut (D6) first, or both in
  parallel.
- D3 (instances per stratum) remains open.

**Authoritative current documents** (this folder, `docs/current/`):

| document | role |
|---|---|
| `NEXT_SESSION_CONTEXT.md` | this handoff |
| [`CORPUS_FREEZE_PREP.md`](CORPUS_FREEZE_PREP.md) | verified candidate-cell table, classification, the `calib_c` batch, other families, the hard-clause reassessment. **Read its r2 box first.** |
| [`CORPUS_V1_PROTOCOL_DRAFT.md`](CORPUS_V1_PROTOCOL_DRAFT.md) | proposed final protocol, **r2**: environments, strata, RC2 rule, effort definitions, analyses, open decisions |
| [`READING_LIST.md`](READING_LIST.md) | the minimal ordered set of documents needed to understand the state, with what each adds |

---

## 1. Research objective and standing constraints

**Objective.** Freeze a benchmark-generation protocol that yields *diverse*
instances on which both RC2 (exact, core-guided) and the memetic solver do
meaningful work, and measure both. The relation between the two solvers'
hardness (ρ) is reported whatever it turns out to be.

**Standing constraints** (all still in force):
- **RC2 eligibility:** certified and **30 s < t ≤ 900 s**.
  - 30.000 s exactly is below the window; 900.000 s is inside;
  - a completion > 900 s counts as censored.
- **Memetic effort:** **seconds** are the primary measure (ERT_s, median
  TTT). Polish calls and flips are secondary diagnostics only.
- **No instrumentation inside polish calls.** Keep the call-level counters
  and target-detection semantics.
- **No further uniform or JW multistart runs** on the calibration pool.
- **No corpus selection toward ρ** (its value, sign or significance).
- **The memetic solver is retained.**
- **No memetic runs** on the 107 certified instances below 30 s.
- **No new instances for the Max-3-SAT n = 250, c\* = 1 regime** (m 1065 /
  1088). The historical results are the reference evidence.
- Seeds are replicates. **Sample size is counted in independent instances
  per reported stratum.**
- Each family or stratum has its own calibration and freeze. A defensible
  stratum is not held for another family.

## 2. Experimental state and latest completed results

| step | what | result | where |
|---|---|---|---|
| historical tier 2 | 26 SATLIB uuf250/uuf200 × 5 seeds, 900 s | memetic 118/130; uniform multistart 124/130; **JW multistart 127/130** (array 22314854, 2026-10-06) | `docs/UUF_THREE_ARM_ABLATION_READOUT.md`; `cluster_staging_maxsat/results/tier2_*` |
| A1 + B1 (RC2) | 290 generated pure-soft instances (calib_a 180 + calib_b 110), cap 900 | 177 certified, 113 censored, 0 failed; 107 certified ≤ 30 s; **70 eligible** | `results/profile_calib_{a,b}_all.jsonl`; `docs/CALIB_A_A1_READOUT.md`, `docs/CALIB_B_B1_READOUT.md` |
| M2 full pool | 70 eligible × 3 seeds × 2 arms (0.5 s / 3.5 s per call, pop 40, clip), 420 tasks, job 22131008, commit `69c9b97` (provenance verified) | 202/210 and 208/210 successes. 28/70 solved by the first call in all 6 runs; 55/70 never needed a second generation. **Q2 non-trivial: 9 (3.5 s arm), 5 (0.5 s arm).** | `results/m2_full_p40/`; `docs/M2_FULL_POOL_READOUT_AND_STATE.md` |
| candidate cells (this session) | literal §5.3 cell rule over all 53 cells, with denominators | **only `max3sat_n250_a4.26` passes**; the read-out §6.2 claim of three passing cells was corrected. "Seven cells" mixes criteria: 8 cells have a run beyond gen 1, 5 have a Q2 instance, 1 passes the cell rule | `results/corpus_freeze_prep/`; `CORPUS_FREEZE_PREP.md` §2–§3 |

`results/…` and `scripts/…` paths are relative to `cluster_staging_maxsat/`.

**The pre-registered rules in use:**
- **Q2 (instance):** successes < all runs, or median TTT ≥ 45 s.
- **§5.3 (cell):**
  - r1: certified ≥ 0.8 of the generated instances;
  - r2: median certified time ≥ 10 s;
  - r3: Q2 ≥ ½ of the eligible tested instances (primary arm);
  - r4: every eligible tested instance has ≥ 1 success.
- r3 and r4 are evaluated over the eligible instances, because no memetic
  run exists below the window.

## 3. Decisions taken 2026-10-06 (this session's final instruction)

1. **RC2 version:** PySAT **1.9.dev3**, the cluster version on every
   calibration task. The full configuration is in protocol §2.1:
   - `RC2(wcnf, solver="g3")`, default options;
   - cap 900 s + 60 s grace, then SIGKILL;
   - env `maxsat`, Python 3.11.15.
2. **Primary memetic effort = seconds**, as pre-registered. Calls and flips
   are secondary. They are not size- or host-free:
   - calls cost about 1.25–3.0 s depending on m;
   - flips cost O(m) each;
   - when the time limit binds, the trajectory changes across hosts.
3. **Instances per stratum: open.** The 40–50 target is withdrawn. Protocol
   §5.2 sets out the trade-off between estimating ρ and claiming ρ ≈ 0
   (equivalence needs N ≳ 44 for |ρ| < 0.3, even at true ρ = 0).
4. **No new reference-regime instances.** Stratum R (seeds 1001–1080) is
   removed. The historical conditions are documented in protocol §3.1:
   - the uuf RC2 PySAT version is **unknown**;
   - caps were 900 / 600 s;
   - the memetic arm was unclipped, 0.5 s per call.
5. **`calib_c`:** prepared and preserved. **Submission pending, not
   approved.** *[r3: on hold, to be reassessed against the larger-n
   direction; §0 decision 3.]*
6. **MaxCut generator:** the proposed next implementation milestone. **Not
   started.**
7. **Pending:** a Max-3-SAT n > 250 assessment (§5). *[r3: folded into
   the larger-n direction for both Max-2-SAT and Max-3-SAT; §0.]*

## 4. Prepared but not approved or submitted: `calib_c`

> **r3: on hold.** To be reassessed against the larger-n direction (§0
> decision 3, R3-a). Its construction is not in question. Do not run the
> steps below until R3-a is decided.

**What.** Two 2-SAT n = 400 cells (α 2.0, m 800; α 2.15, m 860) × generator
seeds 101–120, giving 40 instances. Files:
- `instancegen/grids/calib_c.yaml`;
- `data/generated/calib_c/` (40 instances, gitignored, `--check` OK) and
  `manifest.jsonl`;
- `scripts/manifest_calib_c_rc2.{txt,sha256}`.

**Steps:**
1. RC2 array (40 tasks).
2. `scripts/make_calib_c_memetic_manifest.py`. It runs the primary 3.5 s arm,
   3 seeds, on eligible instances only, writes a not-run list, and refuses to
   build if any RC2 row is missing or failed, or if PySAT ≠ 1.9.dev3.
3. Memetic array.
4. `scripts/candidate_cells.py … --decision`.

**Decision rule:** §5.3 unchanged, applied per cell to calib_a/b/c pooled. A
pass makes the cell a K2 stratum; a fail is final for that cell. There is no
adaptive extension.

**Compute:**
- worst case: 10.7 CPU-h (RC2) + 32 CPU-h (memetic);
- expected: ≈ 1.4 + 0.5 CPU-h.

**Commands:** `CORPUS_FREEZE_PREP.md` §9. Commit first, so that
`MAXSAT_GIT_SHA` names a commit.

**Honest expectation.** Starting from 1/4 per cell, a pass is unlikely: the
pass probability is 0.01–0.05 if the true Q2 rate is 25 %, and about 0.6 if
it is 50 %. The batch buys a firm answer instead of a four-instance one.

## 5. Remaining candidate cells and their evidence limits

| cell / region | evidence | limitation |
|---|---|---|
| **2-SAT n400 α2.0** | r1 10/10, r2 18.1 s, r4 4/4; Q2 1/4 | 4 eligible instances. Wilson interval 0.05–0.70. Window yield 4/10. |
| **2-SAT n400 α2.15** | r1 5/5, r2 147.6 s, r4 4/4; Q2 1/4 | 4 eligible. Window yield 4/5. |
| 2-SAT n400 α2.3 | r1 3/5 ✗; Q2 0/3; #48 has one run beyond gen 1 | fails the RC2 half; not in calib_c |
| 3-SAT n150 α4.8 | Q2 1/1 (#33, c\* 2, 34.9 s) | r1 3/5 ✗, r2 1.9 s ✗; single instance; window yield 1/5; next to the historical uuf200 (n 200, c\* 2) |
| isolated runs | #16 (3-SAT n70 α6), #31 (2-SAT n150 α3.3): runs beyond gen 1, not Q2 | single instances in cells with Q2 0 |
| reference n250 α4.26 / 4.35 | the only §5.3 pass (α4.26) | **no new instances by decision**; evidence only |
| 3-SAT n ≤ 100, 2-SAT n ≤ 250 | Q2 0/34 and 0/15 eligible | memetic does no measurable work there; closed |

> **r3:** this assessment is now part of the larger-n direction for both
> Max-2-SAT and Max-3-SAT (§0, R3-b, R3-c). The text below stays valid as
> the Max-3-SAT half of it.

**Pending larger-Max-3-SAT assessment** (`CORPUS_FREEZE_PREP.md` §4a). The user's rejection of more n = 250, c\* = 1
instances is **not** a rejection of Max-3-SAT at larger sizes.

**Task.** Assess n > 250, with matching clause counts and density choices.
Can some cells give **c\* > 1** while RC2 still certifies in (30, 900] s and
the memetic solver does meaningful work?

**Keep four aims apart:**
1. reinforcing a tested cell (excluded at n = 250);
2. exploring new sizes and densities;
3. adding size diversity;
4. broadening the optimum-cost range.

**Starting evidence** (existing rows only; nothing new computed):
- n = 250, α 4.26: c\* 0–1 in 0.5–388 s, 1/10 censored.
- n = 250, α 4.35: 2/5 certified at c\* 1.
- n = 250, α ≥ 5: fully censored ("α = 5 censored at LB 2",
  `calib_b.yaml`).
- The B1 slope at n = 250 is 2.32 decades of RC2 time per unit c\*
  (`docs/CALIB_B_B1_READOUT.md`). Per-call cost rises with n.

**Risk:** c\* = 2 at n > 250 may lie beyond 900 s.

**Counter-evidence:** that slope is an extrapolation from c\* = 1 points.
Per-instance variance puts c\* 2–3 instances in the window at n = 150
(772 s, c\* 3). **"No evidence yet" is not evidence of absence.**

**Deliverable:** either a recommendation against, with the boundary evidence
(certified/censored counts and censored LBs per (n, α) from
`results/profile_calib_{a,b}_all.jsonl`), or a small, bounded exploratory
grid. For example, 2 values of n > 250 × 2 densities × 5 seeds, with the two-α
hedge, a fixed task count, fixed stopping criteria, and memetic runs only on
eligible instances. No selection toward ρ. **Do not run anything before the
user approves.**

## 6. Proposed MaxCut milestone and unresolved design questions

**Scope** (generator plan Step 1a, revised):
- `instancegen/maxcut.py`: topologies `er`, `torus`, plus the fixtures
  `complete` and `bipartite`; `couplings ∈ {cut, pm1}`;
- `instancegen/verify.py`: fixtures and cost-semantics assertions;
- tests;
- then a calibration-grid plan (its own document) before any RC2 run.

**Encoding:**
- a cut edge (u, v) gives `(x_u ∨ x_v)`, `(¬x_u ∨ ¬x_v)`, weight 1;
- a ±J negative edge gives `(x_u ∨ ¬x_v)`, `(¬x_u ∨ x_v)`;
- cost is the number of uncut or frustrated edges.

**Design questions, unresolved:**
1. **ER model:** G(n, p) with p = d/(n−1), or G(n, M) with a fixed edge
   count? G(n, M) gives an exact clause count of 2M, parallel to
   m = round(α n).
2. **Isolated vertices and disconnected graphs:** keep them (free variables,
   `n_vars` larger than the variables used), drop them, or resample?
3. **Global complement symmetry:** every assignment and its complement cost
   the same.
   - So the JW prior is exactly 0.5 and the crossover's majority-polarity
     tie-break mostly falls to the fitter parent. This is a real difference
     from k-SAT and should be stated, not "fixed".
   - Fixing a vertex would change the instance.
4. **±J torus:** fair signs (p = ½)? Which side lengths (8–14)? Odd sides
   allowed?
   - Fixtures: all-positive even torus → 0; all-negative → 0; gauge
     invariance.
   - Planar 2D ±J ground states are polynomial, so RC2 difficulty on the
     torus is an open empirical question.
5. **c\* scale and RC2 window:** binary-clause cores are small, so c\* is
   expected in the tens; the window location is unknown. Use a two-point
   hedge per row, as in B1.
6. **Determinism and identity:** edge order and clause order in the writer
   (old-dialect WCNF via `write_wcnf`); filename fields (topology, n,
   degree or M, L, couplings, seed); generator version; manifest fields.
7. **Verification:** K_n gives c\* = |E| − ⌊n²/4⌋; bipartite gives 0. Also
   assert that RC2's model, evaluated by the EA's own cost function,
   reproduces RC2's cost — the cut/uncut inversion trap.
8. **Unweighted only** in this milestone. Weighted twins are a separate later
   track.
9. **Relation to S1** (MSE `maxcut/dimacs-mod` and `spinglass`, on disk, 3
   of 67 profiled): should the cheap 900 s S1 RC2 screen run alongside?

## 7. Hard-clause instances: current rationale

Full record: `CORPUS_FREEZE_PREP.md` §8. Probe script
`scripts/hard_clause_probe.py`; output
`results/hard_clause_probe/probe_20261006.txt` (workstation, 20 s runs, not a
measurement).

**The old reason ("no gradient toward feasibility") is withdrawn.** The
fitness −1e9 − 1e6·hv does rank infeasible assignments by their number of
violations. The original evidence was one 134k-clause MSE instance at about
52 flips/s (O(m) scans), which is confounded.

**Verified mechanisms in the staging code:**
- init is JW over soft clauses only, with no feasibility attempt;
- `clause_aware_crossover1` is greedy and hard-aware, with no repair;
- `mutate1` receives a stale feasibility vector (`evo/memetic.py:152`,
  latent bug);
- the polish's hard phase accepts only strictly hv-reducing flips. With no
  such flip it idles to its time limit. Once feasible, `hard_safe` blocks
  any hard break.

**Mixed-sign hard clauses** (partial random k-SAT, set cover, judgment
aggregation): **excluded.**
- Crossover of two feasible parents was never feasible (0/20) at hard ratio
  3–4.
- The polish did not repair it (hv median 2.5–5.5).
- SAT-solver (Glucose) initialisation alone would not fix this.
- **Reconsider only** with a separately specified repair, decoder or
  hard-phase-noise arm that passes the operator probe (≥ 95 % feasible
  children from feasible parents) and reaches feasibility on every seed in
  900 s runs. That arm would be a new algorithm and gets its own table.

**Conflict-clause (anti-monotone) instances** (Max-Independent-Set /
Max-Clique on generated graphs): **reopened as an option (H).**
- Feasibility was found and kept (20/20).
- RC2 proved c\* = 53 in 0.04 s at n = 60.
- **Caveat:** polish calls idle to the time limit, so effort is time-bound
  and host-dependent. Never pool with all-soft strata.
- **Smallest diagnostic** (proposed, not prepared): a G(n, p) MIS generator,
  a 2-cell × 5-seed RC2 screen (≤ 2.7 CPU-h), and the primary arm on
  eligible instances (≤ 8 CPU-h), which must end with hv = 0.

**Roles:** a SAT solver on the hard clauses gives feasibility only. RC2
optimises and certifies, and must never seed the memetic solver.

## 8. Open decisions

| # | decision | state |
|---|---|---|
| D3 | instances per reported stratum | open (protocol §5.2) |
| D5 | submit `calib_c` | **on hold (r3)**: reassess against the larger-n direction; keep, revise or replace (R3-a) |
| D6 | start the MaxCut milestone | proposed; needs approval, then the §6 design questions; priority against the larger-n work open (R3-d) |
| D7 | Max-3-SAT n > 250 | **widened (r3)** to larger n for Max-2-SAT and Max-3-SAT (§0) |
| R3-b | larger-n grid design (n values, α placement per n, seeds, hedge, task cap, stopping rule) | open; written plan and approval before any generation |
| R3-c | accept Max-3-SAT c\* ≤ 1 cells at n > 250 for size diversity, or require c\* > 1 | open |
| R3-d | order: larger-n k-SAT vs MaxCut | open |
| — | conflict-clause diagnostic (H) | proposed, not prepared |
| — | S1 900 s RC2 screen | not prepared (its old sbatch is in `scripts/archive/mse16/`) |
| — | commit the r3 documentation edits | not done; the user decides (Checkpoint 8–9 work is committed in `9a562d0`) |
| — | intermittent staging test failure | named 2026-10-07: `test_m2_prep.py::test_population_10_runs[p10_ls2p5]` (timing bound under deadline clipping); investigate |
| U250 | extend the RC2 and memetic budgets until RC2 certifies all 100 SATLIB uuf250. Today 77 are certified at 900 s and 23 are censored (5 with LB 2) | **deferred, very low priority** (user, 2026-10-07); not planned or approved; `RESEARCH_NOTES.md` N-2026-10-07-f |
| S-a…S-d | SATLIB RC2 screen | **settled 2026-10-07:** one array of all 263 unsat instances, %30, no pre-screen, satisfiable excluded. **Submission by the user is pending** (`SATLIB_BENCH_INTAKE.md` §5) |

Closed: D1 (PySAT 1.9.dev3), D2 (seconds primary; reaffirmed r3), D4 (no
new reference instances; reaffirmed r3).

## 9. Configurations, commits, paths

**Configs** (`cluster_staging_maxsat/configs/tier2/`):
- primary: `memetic_deeppolish_p40_ls3p5.yaml`;
- M2 control: `memetic_deeppolish_p40_ls0p5_clip.yaml`;
- historical: `memetic_deeppolish.yaml` (unclipped 0.5 s).

**Commits and jobs:**
- HEAD `53aa53f` (staging Slurm logs dropped, `from_cluster/` listings
  added); `9a562d0` holds the Checkpoint 8–9 work;
- M2 run code `69c9b97` (job 22131008);
- JW multistart job 22314854;
- archive move `20ebac6`. It broke the RC2 test; this session moved the four
  RC2 tool files back to `scripts/`.

**Data and results** (staging-relative):
- generated instances: `data/generated/calib_{a,b,c}/`;
- RC2: `results/profile_calib_{a,b}_all.jsonl` and `_env.jsonl`;
- M2: `results/m2_full_p40/{agg,analysis,tasks,provenance}`;
- this session: `results/corpus_freeze_prep/`, `results/hard_clause_probe/`.

**Scripts:**
- analysis: `scripts/candidate_cells.py`;
- calib_c memetic manifest: `scripts/make_calib_c_memetic_manifest.py`;
- RC2: `scripts/rc2_profile_array.sbatch`, `submit_rc2_profile.sh`,
  `rc2_row_state.py`, `aggregate_rc2_profile.py`;
- memetic: `scripts/tier2_memetic_array.sbatch`, `submit_m2_memetic.sh`,
  `m2_results.py`.

**Tests:**
- `python -m pytest instancegen -q` (repo root): 82;
- `cd cluster_staging_maxsat && python -m pytest tests -q`: 137 passed, 3
  skipped;
- `python -m pytest tests -q` (repo root): 5.

**Uncommitted files (r3 session, documentation only):**
- `docs/current/NEXT_SESSION_CONTEXT.md`, `CORPUS_FREEZE_PREP.md`,
  `CORPUS_V1_PROTOCOL_DRAFT.md`, `READING_LIST.md`;
- `docs/CORPUS_CALIBRATION_LOG.md` (Checkpoint 10);
- `docs/CORPUS_CALIBRATION_GOALS.md` (status header line).

The Checkpoint 8–9 files listed in earlier revisions of this section are in
`9a562d0`.

**Working conventions** (user):
- one milestone per turn;
- a plan first, then wait for approval;
- short local smoke checks only;
- give rsync and sbatch commands; never claim a submission.

## 10. Where to resume, in order

1. Read §0 (r3 direction), then §3, the r2 box and r3 note of
   `CORPUS_FREEZE_PREP.md`, and `CORPUS_V1_PROTOCOL_DRAFT.md` §3, §5.2 and
   §10.
2. Ask whether to commit the r3 documentation edits.
3. **Settle R3-a (`calib_c`: keep, revise or replace) and R3-c (Max-3-SAT
   c\* range at n > 250)** with the user. These shape the grid.
4. **Larger-n grid plan (R3-b)**, for Max-2-SAT and Max-3-SAT: a written
   plan using the existing rows only, with the boundary evidence
   (certified/censored counts and censored LBs per (n, α) from
   `results/profile_calib_{a,b}_all.jsonl`), the α-placement rule per n,
   seeds, a fixed task count, worst-case CPU-h and fixed decision rules.
   Then **stop for approval**. Generation, manifests and cluster commands
   come only after approval, one milestone per turn.
5. **R3-d:** agree the order of the larger-n work and the MaxCut milestone
   (§6). If MaxCut goes ahead: a short plan for the §6 design questions,
   then `maxcut.py` + `verify.py` + tests. No RC2 run until its calibration
   grid is approved.
6. Later: the S1 RC2 screen; the H diagnostic proposal; D3 per stratum at
   freeze time.
