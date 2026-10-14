# Solver directions after Stage L1: the n 64,000 instances have a few-hundred-variable kernel (2026-10-14)

**Request (user, 2026-10-14)** [quote]: "actually i want you to think what
direction to research or what to optimize in solver furthe, maybe with new
version, you can if you think needed copy to new src folder, i want to try
to get results on 64000 vars, with memetic , if the rc2 achieved optimum in
900s".

**Status:** diagnosis and proposal only. Nothing was changed in the solver
and nothing was submitted. Index: `RESEARCH_NOTES.md`, N-2026-10-14-e.

Tags: [verified] measured here; [inference] my reading; [unverified]
from memory, to be checked before it is cited.

## 1. What the current solver does on these instances [verified: code]

- **Local search:** `src/sat/walksat_v2.py`, plain WalkSAT in pure Python:
  pick a random unsatisfied clause, flip its variable with the best gain,
  noise 0.10. No tabu, no clause weights, no break-count rule.
- **Crossover:** `clause_aware_crossover1(_v2)`. On soft-only instances it
  chooses each variable separately from static occurrence scores and the
  fitter parent, so it ignores which variables interact.
- **Mutation:** `pmutate` 0.02 per variable. At n 64,000 that is about
  1,280 random flips per child, spread over the whole formula.
- **Cluster speed:** 180k–380k flips/s (Stage L1).

## 2. Finding: an exact kernel of 300–572 variables [verified]

A Max-2-SAT formula can be reduced exactly by three standard rules, applied
until nothing changes (`cluster_staging_maxsat/scripts/diag_max2sat_kernel.py`):
1. identical clauses are merged (weights add);
2. a pure variable (one polarity only, any degree) is set and its clauses
   are dropped;
3. a variable in exactly one positive and one negative clause,
   (x ∨ A) and (¬x ∨ B), is resolved into (A ∨ B) with weight
   min(w₁, w₂), which is exact for MaxSAT.

Running the eliminations backwards rebuilds a full assignment.

**Check:** RC2 solves the kernel, the full assignment is rebuilt, and its
cost is counted on the original clauses.
- All 15 calib_2sat_sc2 instances: rebuilt cost = kernel optimum.
- The 6 eligible ones: that equals RC2's proven c\* on the original.

| instance | n | kernel vars / clauses | c\* | RC2 raw (cluster) | kernelise + RC2 on kernel (workstation) |
|---|---:|---:|---:|---:|---:|
| s251 (sc01) | 16,000 | 425 / 691 | 12 | 65 s | 0.16 + 2.2 s |
| s253 (sc02) | 16,000 | 434 / 692 | 14 | 673 s | 0.15 + 58 s |
| s255 (sc03) | 16,000 | 420 / 680 | 13 | 172 s | 0.10 + 21 s |
| s256 (sc04) | 64,000 | 572 / 900 | 13 | 155 s | 0.46 + 2.4 s |
| s257 (sc05) | 64,000 | 300 / 472 | 10 | 82 s | 0.44 + 0.7 s |
| s258 (sc06) | 64,000 | 332 / 512 | 9 | 49 s | 0.44 + 0.2 s |

- The other 9 instances of the batch have kernels of 95–521 variables.
- No constant was ever split off, and every kernel clause still has
  weight 1.

## 3. Finding: the unchanged memetic solves the kernels in under a second [verified: 1 seed, workstation]

Setup: the pre-registered arm `memetic_deeppolish_p40_ls3p5_v2.yaml`
(12,500 flips per call), seed 1, 120 s budget, stop at c\*, run on the
kernel WCNF.

| instance | kernel vars | c\* | best | time to c\* | children |
|---|---:|---:|---:|---:|---:|
| s256 (64k) | 572 | 13 | 13 | 0.70 s | 28 |
| s257 (64k) | 300 | 10 | 10 | 0.12 s | 4 |
| s258 (64k) | 332 | 9 | 9 | 0.03 s | 1 |
| s251 (16k) | 425 | 12 | 12 | 0.34 s | 10 |
| s253 (16k) | 434 | 14 | 15 | not in 120 s | 3,652 |
| s255 (16k) | 420 | 13 | 13 | 0.52 s | 19 |

**Against the raw formula:** 0 of 54 Stage L1 runs reached c\* at
n 64,000 in 900 s. Kernelising plus the memetic reaches it on all three
n 64,000 instances in about 1 s.

**s253 is hard for both solvers:** RC2 took 673 s raw and 58 s on its
kernel, and the memetic missed by 1 in 120 s.

## 4. What this explains [inference]

- **Why the raw memetic fails at n 64,000:** more than 99% of the
  variables are decided exactly by their neighbours. WalkSAT, the 2%
  mutation and the per-variable crossover spend their effort there, and the
  hard part, a few hundred variables, gets a small share.
- **Why Stage L1 found the best flips per call the same at n 16,000 and
  64,000:** the kernels are about the same size at both n (300–572
  against 420–434). The flips that matter scale with the kernel, not
  with n. So `max(12500, c·n)`, with n as the size, is the wrong variable
  for these instances.
- **Why c\* is small at every n:** the cells were built with constant
  n·ε³ (`n_eps3` = 64 in the readout). That is the 2-SAT scaling window,
  where the contradictory structure stays small whatever n is
  [unverified: Bollobás et al. 2001 on the scaling window; Coppersmith et
  al. 2004 on Max-2-SAT above the threshold].
- **For the orthogonality question:** "n 64,000" here is a nominal size.
  Both solvers' difficulty seems to sit in the kernel: on the three 16k
  instances, RC2 on the kernel is 2.2 / 21 / 58 s, in the same order as
  raw 65 / 172 / 673 s. Kernel size, and difficulty on the kernel, should
  be recorded as instance features.

## 5. Directions, ranked

### A. Exact preprocessing in front of the memetic (recommended first)

- **Pipeline:** kernelise, run the memetic on the kernel, rebuild the full
  assignment.
- **What it needs:**
  - a module `src/sat/kernel.py`, the diagnostic made into solver code;
  - an opt-in config key (e.g. `preprocess: kernel2`) read by
    `run_memetic_shard.py`. The shard records the kernel size, the
    kernelise time, and the cost on the original formula.
  - The memetic itself is unchanged, so **no new src folder is needed**.
- **Tests:**
  - exactness against brute force on small random Max-2-SAT;
  - reconstruction;
  - the cost on the original, checked against c\*.
- **Cluster batch:** 6 instances × 3 seeds × 900 s, about 18 tasks, at
  most 4.8 CPU-h. Expected (inference): all three n 64,000 instances
  solved in seconds; s253 is the open case.
- **Scope:** soft-only clauses of length ≤ 2 first.
  - Pure literals are valid for any instance.
  - Resolution on longer clauses, or with hard clauses, makes longer
    clauses (bounded variable elimination). That is a later extension, for
    the hard-clause track.
- **Fairness decision (yours):** if the memetic is given preprocessing,
  RC2 should be measured with the same preprocessing too, or both reported.
  Otherwise the comparison mixes the solver with the preprocessor.

### B. A stronger raw memetic: `impl: v3`, a new src folder if wanted

For instances whose kernel stays large: higher α, larger n·ε³, and the
hard-clause track. Each step is a separate arm:
1. **Partition crossover:** split the variables where the parents differ
   into the connected parts of the variable-interaction graph, and take the
   better parent part by part. On a graph this sparse it splits into many
   parts and recombines exactly [unverified: Tinós, Whitley and Chicano,
   FOGA 2015; Chen, Whitley et al., GECCO 2018, "Tunneling between
   plateaus" with a MAX-SAT solver].
2. **Clause-weighting local search** instead of plain WalkSAT, as the
   current MaxSAT local-search solvers use [unverified: SATLike, Lei and
   Cai 2018; NuWLS].
3. **Localised mutation:** perturb a neighbourhood instead of 2% of all
   variables.
4. **Speed:** a compiled inner loop. There is no numpy or numba in the
   venv; gcc is on the workstation, and whether the cluster has it is
   unknown. This gives the largest gain per call, but it changes what
   "seconds" mean between versions (as v1 → v2 did).

This is research work for several milestones. A is one milestone.

### C. Corpus: make "large" mean a large kernel

- Kernel size takes about 0.5 s to compute at n 64,000, so it can screen
  cells before RC2 is run.
- To test the memetic at a genuinely large effective size, cells with
  larger n·ε³ (larger α) are needed, which gives a bigger kernel and a
  bigger c\*. Keep only instances that RC2 still solves in ≤ 900 s raw.
- Kernel size versus α at n 64,000 is not measured yet; it is a cheap first
  step.

## 6. Recommendation and open decisions

1. **Build A** (one milestone): module, tests, shard fields, an 18-task
   manifest.
2. **Hold Stage L1b** (the 6/8/10/15 s time grid, prepared, not submitted).
   It calibrates polish length on the raw formula, and if A is adopted that
   question no longer applies to these instances. Or run it as the raw
   baseline arm: your choice.
3. **For you:**
   - Is exact preprocessing allowed as part of "the memetic"?
   - If yes, is RC2 also measured on the kernel?
   - After A: B (a stronger raw solver) or C (large-kernel corpus) first?

## 7. Beyond 2-SAT: does it carry over? (user question, 2026-10-14)

**Question (user)** [quote]: "will the kernelising and stronger solver work
on 3sat, and in general not only on 2sat".

### 7.1 The diagnostic now covers any clause length and hard clauses [verified]

- `diag_max2sat_kernel.py` now reads `p cnf`, `p wcnf` and the 2022+ WCNF
  format.
- Both rules stay exact for any clause length: a pure variable is still
  dominated, and resolving (x ∨ A) with (¬x ∨ B) into (A ∨ B) is exact,
  with a longer resolvent. Hard clauses carry the weight HARD.
- **A brute-force test found a bug in the reconstruction**, which is now
  fixed. When the two resolved clauses had different weights, or one was
  hard, and both A and B were false, the old rule could violate the
  heavier clause.
  - It never fired on calib_2sat_sc2: every weight there is 1, and those
    15 instances verified.
  - After the fix: 0 mismatches against exhaustive search on 3,000 random
    instances (n 4–11, clause lengths 1–4, 25% hard, weights 1–3). The
    three n 64,000 instances re-verified.

### 7.2 Kernel sizes across the corpus [verified]

| family | n | m | kernel vars | reduction |
|---|---:|---:|---:|---:|
| calib_2sat_sc2 (Max-2-SAT, α 1.1–1.2) | 16,000 / 64,000 | 1.1–1.2 n | 95–572 | 97–99.5% |
| calib_a (Max-2-SAT, α 2) | 100 / 400 | 200 / 800 | 46 / 207 | about 50% |
| calib_a/b (Max-2-SAT, α 3–5) | 100 | 300–500 | 90–99 | 1–10% |
| uuf250 / uuf225 (random 3-SAT at the threshold) | 250 / 225 | 1,065 / 960 | 247–250 / 224–225 | ≤ 1.2% |
| highgirth 3-SAT, 4-SAT | 250 / 100 | 1,000 / 900 | 250 / 100 | 0% |
| abrame-habet Max-3-SAT 110v, Max-2-SAT 200v | 110 / 200 | 1,000 / 1,200 | 110 / 199–200 | ≤ 0.5% |
| jnh, crafted maxcut (dimacs-mod, bipartite) | 40–140 | 850–1,690 | all | 0% |
| MSE industrial, hard clauses (BTBNSL, MaxSATQueries, gen-hyper-tw) | 2,563–46,941 | 45,700–166,475 | 2,226–44,401 | 5–22%, resolvents up to 75 literals |

- RC2 checks on the non-2-SAT rows: uuf250-01 and uuf225-01 kernels
  solve to cost 1 (45 s and 35 s), and the rebuilt full cost is 1, OK.
- RC2 did not finish within 300 s on HG-4SAT-V100-C900-7 or on the two MSE
  instances checked. For hard clauses, exactness rests on the brute-force
  test of 7.1.

### 7.3 Reading [inference]

- **Kernelising is a property of the instance family, not of the solver.**
  It pays only where most variables have very few occurrences.
  - Random 2-SAT near its threshold: k·m/n ≈ 2.2 occurrences per variable.
  - Random 3-SAT at its threshold: about 12.8 occurrences per variable, so
    pure or degree-2 variables are rare (≈ 10⁻⁴ of them).
  - Industrial instances fall in between: a moderate reduction, with long
    resolvents that may slow local search.
- So the n 64,000 result under A shows that this family is easy in
  disguise; it is not a general memetic advance. It is still worth having
  as a cheap exact preprocessor, and kernel size is worth recording as an
  instance feature everywhere. Full bounded variable elimination and the
  MaxPre-style techniques are the general version [unverified: Korhonen,
  Berg, Saikko and Järvisalo, SAT 2017].
- **The B components are general by construction:**
  - clause-weighting local search, a compiled inner loop and localised
    mutation assume nothing about k or hard clauses;
  - partition crossover is defined for any k, but it pays only when the
    variables where two parents differ split into several independent
    parts. On random 3-SAT at the threshold the interaction graph is dense
    (about 25 neighbours per variable), so it may split little. Industrial
    instances are where it was reported to help [unverified].
  - A cheap diagnostic before building it: count those parts for pairs of
    our own memetic solutions on uuf250 and on an MSE instance.
- **"n 64,000 and RC2 optimal in 900 s" itself selects easy structure.**
  RC2 needs 35–45 s on a 250-variable random 3-SAT kernel at the
  threshold. A random 3-SAT instance near the threshold with 64,000
  variables will not be proved by RC2 in 900 s. Large-n instances with a
  proven c\* are therefore sparse, near-satisfiable or structured, which
  is exactly where kernelising and partition crossover help most.

## 8. Decision: kernelise for the sparse Max-2-SAT grid, behind a quick worth-it check (user, 2026-10-14)

**User** [quote]: "write in research flow a note that karnelization mainly
enhances not dense 2sat on which we got eligible grid points from rc2, and
didn't pass memetic without it. so I think for this case of grid we do need
kernnilization preprocessing, maybe check, even if it is on - that it is
not dense 2sat, or other very rapid check that its worth this kind of
processing".

### 8.1 The note [verified + decision]

- **Kernelising mainly helps sparse (not dense) Max-2-SAT.** These are
  exactly the cells where the RC2 grid gave eligible points: calib_2sat_sc2,
  n 16,000 and 64,000, α 1.1–1.2.
  - On them the memetic without kernelising never reached c\* at n 64,000:
    0 of 54 Stage L1 runs in 900 s.
  - With kernelising it reached c\* on all three n 64,000 instances in
    ≤ 0.7 s (§3).
- Elsewhere it barely helps:
  - dense Max-2-SAT and 3-SAT/4-SAT: 0–1.2%;
  - crafted: 0%;
  - MSE industrial: 0–22% (§7).
- **Decision (user):** for this grid, the memetic runs with kernelising as
  preprocessing. It stays opt-in and is gated by a quick check (8.2), so
  the same configuration is safe on any instance.

### 8.2 The quick check: is kernelising worth it? [verified: calibration; proposed: thresholds]

**Statistic `s`, one pass over the clauses:** the fraction of the
variables that occur that the rules remove immediately. A variable counts
if it is pure, or has exactly one positive and one negative occurrence.
- It needs no knowledge of k or of the density; it captures "not dense"
  directly.
- Cost: ≤ 0.1 s up to m 166,000 (workstation).

**Calibration** (`s` against the final reduction):

| family | occurrences per variable | `s` | final reduction |
|---|---:|---:|---:|
| calib_2sat_sc2 (5 instances, n 16k and 64k) | 2.5–2.6 | 61–65% | 97.0–99.4% |
| calib_a Max-2-SAT α 2 (4) | 4.1 | 27–34% | 45–53% |
| calib Max-3-SAT α 4.26, uuf250, uuf225, highgirth 3-SAT | 12–12.8 | 0–1.3% | 0–1.3% |
| abrame-habet Max-2/3-SAT, crafted maxcut, jnh | 12–44 | 0% | 0% |
| MSE 2024 (10 instances, every 12th file) | 4.7–203 | 0–13.1% | 0–13.1% (one at 12.5% from `s` 0%) |

**Proposed gate** (in the solver, recorded in every shard):
1. **Screen:** if `s` < 20%, skip kernelising and run on the original.
   - The calibration has a clear gap between 13% and 27%.
   - Cost when skipped: ≤ 0.1 s of the 900 s.
2. **Kernelise** (≤ 0.5 s at n 64,000). Use the kernel only if it removes
   ≥ 20% of the variables and no resolvent is longer than the longest
   original clause. Otherwise run on the original.
   - That length condition never binds on the sparse 2-SAT grid, where
     resolvents of binary clauses stay binary.
3. **Shard fields:**
   - `preprocess` (`kernel` / `skipped_screen` / `skipped_gain`);
   - `screen_s`;
   - kernel n and m;
   - kernelise seconds;
   - cost on the original formula after rebuilding (the cost that is
     checked against c\*).
   The kernelise time counts inside the 900 s and inside TTT.

**[inference]** On the grid the gate always passes, at `s` ≈ 61–65%. On
dense or 3-SAT families it always skips, at almost no cost. The two
thresholds are the only free choices. They are set from this calibration,
not tuned on memetic results.

### 8.3 Decisions (user, 2026-10-14) [quote + decision]

> "1. no preprocessing on rc2 - explain it that it is should have been included in core solver of rc2, it is problem of rc2 solver, and in our there is enhancement. 2. time grid on hold, meanwhile we will try to get results with solver enhancement. 3. later I would like explanation on B and C"

1. **RC2 is run as distributed, without our preprocessing.**
   - **Rationale (user):** exact preprocessing belongs in a solver's core.
     RC2 not doing it is a limitation of RC2. Our memetic solver includes
     it, and that is our enhancement. RC2's times and c\* stay as measured
     on the original formula.
   - **How it is reported:** the memetic arm is "memetic with exact
     kernelising (gated)", and RC2 is "RC2 (PySAT), as distributed".
     Kernelise time counts inside the memetic's budget and its TTT.
     [inference] State this explicitly in any write-up, with the kernel
     sizes and RC2's time on the kernels (0.2–2.4 s at n 64,000) as context,
     so a reader can see how much of RC2's difficulty is the missing
     preprocessing.
2. **Stage L1b (the time grid) is on hold.** The next results come from the
   solver enhancement (direction A).
3. **B and C are to be explained later** (to-do; not a session opener
   unless the user asks).

### 8.4 Superseded open points (kept for the record)

- **Fairness:** is RC2 also reported on the kernel (or with the same
  preprocessing)? RC2 on the n 64,000 kernels takes 0.2–2.4 s, against
  49–155 s on the original formula.
- **Stage L1b** (the time grid on the original formula): hold, or run it
  as the raw baseline?
- **After A:** B (clause weighting first, general) or C (large-kernel
  corpus).
