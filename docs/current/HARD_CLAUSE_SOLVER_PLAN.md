# Hard-clause solver in a new staging tree — intention and plan (H0)

**Date:** 2026-10-11. **Status:** the user's intention, written down as a
plan. **Nothing has been created, copied or run.** Each milestone in §6
needs the user's approval before it starts.

Paths are relative to the repository root unless stated otherwise.

**Update 2026-10-11 (later): first instances are MSE 2023 / 2024** (user,
N-2026-10-11-g). Q4 is answered for the first targets:
- the hard-clause solver starts on `data/raw/mse_2024/mse23-uw-small/` (75,
  unweighted) and `mse24-small/` (91, weighted);
- targets come from EvalMaxSAT 3600 s (sample s1, `MSE_EVALMAXSAT_3600.md`):
  the proven optimum where there is one, else the year's best-known.

Consequences for the design below:
- **Weights.** All of MSE 2024 is weighted, with costs up to ~1.4 · 10⁹.
  The staging solver already handles weights (`population.py` evaluate and
  the JW prior, `walksat_v2.py`). H5's smoke must include weighted
  instances.
- **Size.** Median ~8,800 (2023) and ~16,500 (2024) variables, up to
  238,208. Hard clauses are ~98–99 % of all clauses, so `impl: v2`
  (incremental, O(1) break counts) is the only usable polish. v1's O(m) per
  flip is out.
- **Unknown best-known (−1)** on 5 instances: Glucose may not find a
  feasible model. These are excluded from the first runs.
- **Generated partial k-SAT / MIS** (the old Q4 options) become
  unit-test-scale fixtures for H2–H3, not the first study set.

The user also asked for the local search to be prepared while the
EvalMaxSAT array runs. That is H1, next.

---

## 1. The user's intention (verbatim, 2026-10-11)

> do new folder similar to cluster_staging_maxsat, copy there the
> up-to-date solver, and make solver for hard clauses, with glucouze
> initialization of hard satisfiebility, and enhancing solver with qualities
> it will save the hard satisfiebility over local and memtic iterations, also
> emphasize in documents I want to give attention to result that multistart
> might be enogh, due to result that most answers were achieved in first
> child or first generation

Read as four requirements:

| # | requirement | in this plan |
|---|---|---|
| U1 | a new staging folder, similar to `cluster_staging_maxsat/`, holding a copy of the **up-to-date** solver | §3 |
| U2 | a solver for instances **with hard clauses**: **Glucose** finds the initial hard-feasible assignments | §4.1 |
| U3 | the solver **keeps hard feasibility** through every local-search (polish) step and every memetic step (crossover, mutation, selection) | §4.2–§4.4 |
| U4 | attention to the finding that **multistart may be enough**, because most successes came from the first child or the first generation | §5 |

## 2. Why this is a new solver, not a fix — prior evidence

The hard-clause reassessment (`CORPUS_FREEZE_PREP.md` §8, note
N-2026-10-07-a) already established, for the **current** solver:

- **Feasibility at the start** is trivial for a SAT solver and hard for the
  memetic solver. On mixed-sign hard clauses at hard ratio ≥ 3, its
  strict-descent hard phase stalls at hv 1–8.
- **Feasibility through variation is the decisive failure.** Crossover of two
  Glucose-feasible parents gave a feasible child in 0/20 cases at hard ratio
  3–4, and one polish call did not repair it (§8.3).
- **Stale-vector bug.** `mutate1` is passed `ind.hard_satisfied`, which is
  the last *initial* member's vector, not the child's
  (`cluster_staging_maxsat/src/evo/memetic.py:160`; it was `:152` before
  `impl: v2` added lines). It has no effect on all-soft instances.
- **Idle polish calls.** With hard clauses, the polish's no-op iterations do
  not advance the flip counter, so every call runs to its time limit (3.5 s).
  Effort per call then depends on the host.
- **The user's wording rule stands** (N-2026-10-07-a): Glucose gives a
  starting point. The operators must also preserve feasibility.
- **The pre-registered bar to reconsider hard clauses** (§8.5): an arm must
  give ≥ 95 % feasible children from feasible parents in the operator probe,
  and reach feasibility on every seed in 900 s runs on generated instances.
  **This plan adopts that bar unchanged as H3's acceptance test.**

Consequence (§8.5, unchanged): the hard-clause solver is a **new algorithm**.
Its rows never share a stratum or a table with the current solver's rows.
The all-soft study and its frozen code are not touched.

## 3. The new staging tree (U1)

**Proposed name:** `cluster_staging_maxsat_hard/` (open question Q1).

**Source of the copy:** `cluster_staging_maxsat/` at the commit current when
H1 starts (HEAD is `4a2c769` today). "Up-to-date solver" means the staging
`src/`, which is intentionally ahead of the repo `src/`:
- target-cost early stop;
- opt-in deadline clipping;
- new-format WCNF parsing;
- `evo/multistart.py` (uniform and JW-seeded multistart);
- `impl: v2` (`sat/walksat_v2.py`, `evo/impl_v2.py`): incremental WalkSAT,
  50–1800× faster per flip at large n (`MEMETIC_IMPL_V2.md`).

**What is copied:**

| copy | do not copy |
|---|---|
| `src/` (all), `configs/tier2/` (as the starting point for new configs), `tests/` (the solver and parser tests), the runner and Slurm wrappers the hard arm needs (`run_memetic_shard.py` path, memetic array sbatch, submit wrapper), `DIVERGENCE.md` (renamed and rewritten, below) | `data/` (182 MB), `results/`, calibration manifests and readouts, `.bak` files, `__pycache__` |

**Provenance rules:**
- A new `PROVENANCE.md` in the new tree records the source commit and the
  sha256 of every copied file. Same pattern as `DIVERGENCE.md`.
- Right after the copy, a `diff -rq` against the source must show no
  differences (excluding the files left out). After that, the copy is
  allowed to diverge.
- **The copied test suite must pass unchanged in the new tree** before any
  edit (run from inside the new tree; see the staging rule in the memory
  notes).
- The original `cluster_staging_maxsat/` is not edited by this work. If a
  shared bug fix is needed there, it is a separate decision.

**Data:** hard-clause instances go under the new tree's own `data/`:
- generated partial random k-SAT (`instancegen/feasible.py` guarantees a
  satisfiable hard part);
- conflict-clause (MIS / Max-Clique) instances;
- later, selected MSE hard-clause instances.
Nothing is generated before H5.

## 4. Solver design (U2, U3) — proposal for review

The invariant: **every individual that enters the population, and every
incumbent, has hv = 0** (no violated hard clause). Each step is either
feasibility-preserving by construction or followed by a repair that restores
hv = 0. A step's feasibility is checked, never assumed.

### 4.1 Initialisation by Glucose (U2)

- PySAT `Glucose4` on the **hard clauses only**. It supplies feasibility and
  no objective information. That is legitimate initialisation, as long as
  its time is charged to the run clock (`CORPUS_FREEZE_PREP.md` §8.4,
  "Roles"). RC2 never seeds the solver.
- **Diversity.** Each population member is a separate Glucose call with
  different preferred phases (`set_phases`): either random phases, or
  JW-biased phases from the soft clauses. The JW option keeps the current
  solver's soft-side prior. The members are de-duplicated; if Glucose keeps
  returning the same model, randomise its phases further.
- **UNSAT hard part:** the run stops immediately with status
  `hard_unsat` and no cost.
- Record per run: the Glucose time, the number of calls, and how many
  members are distinct.

### 4.2 Polish that keeps feasibility (local search)

- **Start feasible, stay feasible.** v2's `hard_safe` already skips any flip
  with a hard break count > 0, so the feasible phase never leaves hv = 0.
  v2 tracks break counts incrementally, so this check is O(1) per candidate.
- **Fix the idle no-op.** When every candidate flip in the chosen soft clause
  is hard-unsafe, the iteration must still count as a step. Choose one of:
  - (a) count it as a flip attempt, so the flip cap still binds;
  - (b) choose another unsatisfied soft clause.
  This makes calls flip-bound again, as on all-soft instances, rather than
  time-bound.
- **Optional escape, with a mandatory check after it:** allow a bounded hard
  break, then repair. Not in the first version.

### 4.3 Crossover and mutation that keep feasibility

The probe showed that recombination is where feasibility is lost. Candidate
designs, in order of preference (open question Q3):

1. **SAT-based repair, guided by the child (proposed default).** Run
   Glucose on the hard clauses with the child's bits as **preferred
   phases**. Glucose returns a feasible model close to the child; bits where
   both parents agree can optionally be passed as assumptions first, with a
   fallback to phases only. The repair time is charged to the run clock, and
   the record keeps the number of repaired children and the mean Hamming
   distance moved.
2. **Propagation-aware crossover.** Assign variables in clause order. After
   each choice, unit-propagate the hard clauses, so later choices respect
   them. This needs backtracking or a repair step when there is a conflict.
3. **Reject and retry.** Draw a new child until it is feasible, with a cap
   and then a fallback to (1). Too slow at hard ratio 3–4 (0/20).

**Mutation:** fix the stale-vector bug by passing the **child's** current
hard-satisfaction state. Keep the rule that rejects any flip that breaks a
satisfied hard clause.

**Selection:** every member is feasible, so fitness is just the soft cost.
The `−1e9 − 1e6·hv` branch stays only as an assertion that should never
fire.

### 4.4 What the records must show

New fields on every row:
- `hard_feasible_final` (must be true);
- `hv_max_seen_in_population` (must be 0);
- `glucose_init_s`, `glucose_repair_calls`, `glucose_repair_s`;
- `children_repaired`, `children_feasible_without_repair`;
- `impl` (a new value, e.g. `"hard_v1"`).

Seconds stay the primary effort measure. They are comparable only within one
`impl`, as with v1/v2.

## 5. Attention point: multistart may be enough (U4)

### 5.1 The evidence the user points to [verified, from existing readouts]

- **M2 full pool** (70 calibration instances × 2 arms × 3 seeds,
  `M2_FULL_POOL_READOUT_AND_STATE.md` §6.2):
  - **28/70** instances were solved by the **first polish call** in all 6
    runs;
  - **55/70** never needed more than **one generation** (≤ 38 children) in
    any run;
  - only 15/70 went beyond generation 1. Only 5 (`a05`) or 9 (`a35`) passed
    the pre-registered Q2 non-trivial rule.
- **M2 pilot** (`M2_PILOT_READOUT.md` §3): on 8 of 10 instances every arm
  succeeds within 1–8 children. First-child solves: p40_ls2p5 18,
  p10_ls2p5 15, control 11.
- **Historical uuf250/uuf200 three-arm ablation**
  (`UUF_THREE_ARM_ABLATION_READOUT.md` §0, 26 instances × 5 seeds, 900 s):
  - successes: **JW multistart 127/130**, uniform multistart 124/130,
    memetic 118/130 (memetic vs JW: Fisher p = 0.03, ignoring clustering);
  - typical-run speed favours memetic: Kaplan–Meier median time to target
    is 30 s for memetic against 90 s for JW;
  - memetic's failures are population stalls at c\* + 1.

### 5.2 What this does and does not show [inference]

- **On the calibration pool, the EA loop is mostly not exercised.** A
  success at the first child is a JW-seeded recombination followed by one
  polish. That is close to a single JW-seeded restart. On 55/70 instances,
  selection across generations contributed nothing observable. **These
  rows cannot separate memetic from multistart**, because the EA had no
  room to matter.
- **Where the EA did have room** (uuf, n = 250, c\* = 1–2), multistart
  succeeded **more often**, and memetic was **faster when it succeeded**.
  So "multistart is enough" is supported on **reliability** and is not
  supported on **typical speed**.
- **First-child success is also a property of the instances.** It means LS
  alone finds c\* quickly, which is the "Q2 trivial" outcome. A fair test of
  "multistart is enough" needs **Q2 non-trivial instances**: Max-3-SAT
  n = 250 α 4.26/4.35, Max-2-SAT n = 400 α 2.0–2.15, and the 95
  SATLIB-eligible instances once their memetic manifest exists.
- **A standing decision conflicts with this direction.** On 2026-10-06 the
  user decided "No multistart on the calibration pool" / "No further
  uniform or JW multistart runs on the calibration pool"
  (`CORPUS_CALIBRATION_LOG.md` Checkpoint 8; `NEXT_SESSION_CONTEXT.md` §3).
  Today's emphasis reopens the question. **Whether to lift that decision,
  and for which instances, is the user's call** (open question Q5). This
  plan does not lift it.

### 5.3 How the hard-clause solver serves this question

- **Build both arms from the same components:** Glucose init, the
  feasibility-preserving polish, and the same clock. The two arms differ
  only in the EA loop:
  - `hard_multistart`: Glucose-seeded restart → polish → discard;
  - `hard_memetic`: the population, crossover + repair, mutation, elitism.
  The ablation is then clean by construction, with none of the
  seeding/heuristic confounds listed in the uuf audit §5.
- **Log, on every run, the generation and the child index at which the
  target was first reached.** That makes "solved in the first generation /
  first child" a recorded field, not a reconstruction.
- **Hard clauses may change the answer.** With repair, recombination does
  something multistart cannot: it inherits feasible structure from two
  parents. Whether that helps is exactly the U4 question, asked on a
  family where it might.

## 6. Milestones (one per turn; approval before each)

| id | milestone | output | compute |
|---|---|---|---|
| **H0** | this plan | `docs/current/HARD_CLAUSE_SOLVER_PLAN.md`; research notes N-2026-10-11-b, -c | none |
| H1 | create the tree and copy the solver | `cluster_staging_maxsat_hard/` + `PROVENANCE.md`; identity diff; copied tests pass unchanged | workstation, seconds |
| H2 | Glucose init + stale-vector fix + idle no-op fix + feasibility assertions and record fields | code + unit tests (UNSAT hard part, distinct members, hv = 0 invariant) | workstation |
| H3 | feasibility-preserving crossover (repair) | code + **operator probe** re-run with the §8.5 bar (≥ 95 % feasible children from feasible parents) on the §8.3 instances | workstation, minutes |
| H4 | `hard_multistart` arm sharing H2–H3 components; target-hit generation and child index logged on both arms | code + tests | workstation |
| H5 | small generated hard-clause set and a workstation smoke (both arms, few seeds, short budget) | instances + smoke rows (exploratory, not batch data) | workstation |
| H6 | RC2 screen + 900 s cluster runs, both arms | manifests, rsync + sbatch commands (user submits) | cluster |

## 7. Open questions for the user

- **Q1** Folder name: `cluster_staging_maxsat_hard/`?
- **Q2** SAT solver: Glucose4 (as stated) through PySAT. CaDiCaL is also
  available in PySAT; keep Glucose unless there is a reason to change.
- **Q3** Crossover feasibility: SAT-based repair guided by the child (§4.3
  option 1) as the default?
- **Q4** ~~First instance families~~ — answered 2026-10-11: MSE 2023 / 2024
  first (see the update at the top); generated instances as small fixtures.
- **Q5** Multistart on all-soft instances: lift the 2026-10-06 "no multistart
  on the calibration pool" decision for the Q2 non-trivial instances (§5.2),
  or keep U4 inside the hard-clause study only?
