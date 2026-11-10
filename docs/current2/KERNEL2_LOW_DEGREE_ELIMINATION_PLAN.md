# Kernel 2 at α 1.2: how much do 1/2, 2/2 (and later 1/3) eliminations help on random Max-2-SAT? (plan r2, 2026-11-10)

**Request (user, 2026-11-10)** [quote]:
1. "we did in kernelization optimization 1/1 one true literal, one false. how
   works optimiztion 1/2 and how works 2/2"
2. "write a plan not only for the hard-only 2/2 and 1/2 cases - mainly for
   soft only generated random max2sat"
3. **r2:** "I want at alpha density 1.2, the purpose is not general, it is do
   statistics how much the 1\2 2\2 and also later 1\3 helps on max2sat
   generated random."

**Status:** PLAN ONLY.
- Nothing has been built in `src/`.
- The numbers in §3 come from a diagnostic run on the workstation, checked by
  brute force.
- **Waiting for approval of M1 (§6) and the decisions in §7.**

**Index:** `docs/current/RESEARCH_NOTES.md`, N-2026-11-10-a (r1), N-2026-11-10-b (r2).

**Companion explainer:** `docs/current2/EXACT_VARIABLE_ELIMINATION_EXPLAINED.md`
(user-supplied text: 1/1, 1/2 and 2/2 with derivations).

**r2 changes against r1:**
- The scope is now one density, α 1.2, and the aim is a statistical
  measurement of each rule's effect, not a general preprocessor.
- The α 1.5 / 2.0 cells are dropped.
- 1/3 is a separate, later rule.
- The hard-only elimination (r1 M4) is out of scope (§8).

Tags: [verified] measured here or read off the code; [inference] my reading;
[unverified] from memory, to be checked before citing.

## 1. The question

**Population:** uniform random Max-2-SAT, `instancegen generate-distinct`,
k = 2, α = m/n = 1.2, all clauses soft with weight 1.

Each new rule is applied **cumulatively** on top of today's kernel:

| arm | rules | clause-length bound |
|---|---|---|
| **K0** | today's `kernel`: merges, complementary units, pure, 1/1 | 2 (never grows) |
| **K1** | K0 + 1/2 | 3 |
| **K2** | K1 + 2/2 | 4 |
| **K3** (later) | K2 + 1/3 | 4 |

"How much it helps" is measured three ways, all paired by instance:

- **H1 size:** kernel variables and clauses, clause-length mix, and
  eliminations counted per rule. Cheap, and done on every instance.
- **H2 exact hardness:** RC2 time on the K0, K1 and K2 kernels. This also
  gives c\* for every instance (D3).
- **H3 memetic:** success and time to c\* (kernel time included) for the
  memetic on K0, K1 and K2.

## 2. The rules (details in the explainer) [verified: brute force]

**General form:** x has positive clauses (x ∨ Aᵢ, wᵢ) and negative clauses
(¬x ∨ Bⱼ, uⱼ). Replace them by clauses without x whose cost is exactly

g = min( Σᵢ wᵢ·[Aᵢ false] , Σⱼ uⱼ·[Bⱼ false] ).

- **Lift:** x = 1 if cost(x = 1) ≤ cost(x = 0), else 0. Undo the eliminations
  in reverse order.
- Then for every kernel assignment, lifted cost = const + kernel cost.

**The rules with all weights 1 (our population):**

| rule | x-clauses | replacement | clauses | longest |
|---|---|---|---|---:|
| 1/1 | (x∨A), (¬x∨B) | (A∨B) | 2 → 1 | 2 |
| 1/2 | (x∨A), (¬x∨B1), (¬x∨B2) | (A∨B2), (A∨B1∨¬B2) | 3 → 2 | 3 |
| 2/2 | (x∨A1), (x∨A2), (¬x∨B1), (¬x∨B2) | (A1∨B1), (A1∨¬B1∨B2), (¬A1∨A2∨B1), (¬A1∨A2∨¬B1∨B2), (A1∨A2∨B1∨B2) | 4 → 5 | 4 |
| 1/3 | (x∨A), (¬x∨B1), (¬x∨B2), (¬x∨B3) | (A∨B1), (A∨¬B1∨B2), (A∨¬B1∨¬B2∨B3) | 4 → 3 | 4 |

- 2/1 and 3/1 are the same rules with x and ¬x swapped.
- Weighted versions are in the explainer, §4. Merges make some kernel
  clauses weight 2+, so the implementation uses the general min-elimination,
  not only the unit-weight tables.
- 1/3 with unit weights: g = [A false]·[some Bⱼ false]. It was checked by
  brute force on all 16 cases (2026-11-10).
- **Cascades:** each elimination can create new pure or 1/1 variables. Every
  arm re-runs the K0 rules until nothing changes (§2.1).
- **Accounting:** pure and 1/1 eliminations that happen inside K1/K2 are
  counted separately, so the gain is credited to the rule that triggered it
  (H1 records counts per rule).

### 2.1 Remark: does today's kernel do several passes? Yes, to a fixpoint [verified: code + measurement, 2026-11-10]

**Question (user, 2026-11-10):** after a round of 1/1 eliminations and
substitutions, new variables and clauses can become eliminable. Does the
kernel catch them?

**Answer: yes.**
- `kernelize` (`src/sat/kernel.py`, lines 144–183) is not a single pass. It
  is a **work list run to a fixpoint**:
  - At the start every variable is on the list.
  - After any elimination (pure, 1/1, complementary units), every variable
    that shared a removed clause goes back on the list.
  - It stops only when the list is empty, so no rule applies anywhere.
- This gives the same result as repeating whole passes until nothing changes,
  but it revisits only the variables that were touched.

**How an elimination creates new candidates:**
1. **Pure:** removing a pure variable's clauses lowers its neighbours'
   occurrence counts. A neighbour that was 1/2 can become 1/1 or pure.
2. **1/1 resolvent:** the resolvent (A ∨ B) can have three outcomes, and each
   one lowers the counts of A and B:
   - it equals an existing clause, so it merges with it (weights add);
   - it is a tautology (A = ¬B), so it is dropped;
   - it is a unit (A = B), so the complementary-units rule may fire.
3. **Variables that start as 1/1** may end up eliminated as pure, because a
   neighbour's elimination removed one of their clauses first. In the
   measurement, about 1,300 per n 16,000 instance ended this way.

**Measured at α 1.2** (share of the occurring variables):

| instance | n | occurring | pure or 1/1 at the start | removed only through cascades | left in the kernel |
|---|---:|---:|---:|---:|---:|
| s251 | 16,000 | 14,584 | 8,904 (61.1 %) | 5,255 (36.0 %) | 425 (2.9 %) |
| s253 | 16,000 | 14,503 | 8,787 (60.6 %) | 5,282 (36.4 %) | 434 (3.0 %) |
| s255 | 16,000 | 14,525 | 8,822 (60.7 %) | 5,283 (36.4 %) | 420 (2.9 %) |
| s1201 | 32,000 | 28,978 | 17,569 (60.6 %) | 10,186 (35.2 %) | 1,223 (4.2 %) |
| s1202 | 64,000 | 58,047 | 35,164 (60.6 %) | 20,818 (35.9 %) | 2,065 (3.6 %) |
| s1203 | 64,000 | 58,218 | 35,230 (60.5 %) | 21,524 (37.0 %) | 1,464 (2.5 %) |

**[verified] What the table shows:**
- A single first round could remove at most the 61 % that are pure or 1/1 at
  the start. This equals `screen_frac`, the gate's screen statistic.
- The cascades remove another 35–37 %, so they make up **more than a third of
  all the reduction**.
- At the fixpoint, no kernel variable is pure or 1/1 and there are no
  complementary soft unit pairs (checked on all six).
- None of the start-set variables remain in the kernel.

**For K1–K3:**
- The new rules join the same work list, interleaved with the old ones, so
  each arm also ends at a fixpoint of all its rules.
- An elimination can move a neighbour between types in either direction, for
  example 1/3 → 1/2 after a merge, or 1/2 → 1/1. The r1 diagnostic already
  showed pure and 1/1 eliminations appearing after 1/2 eliminations.
- H1 reports, per arm, the eliminations by rule and how many of them are
  cascade eliminations, i.e. of variables that were not of that type in the
  arm's input kernel.

**Reproduce:** from `cluster_staging_maxsat_strong/`, run
`python3 scripts/diag_kernel_cascade.py <wcnf> ...`. It prints one table row
and the fixpoint check per instance.

## 3. Diagnostic at α 1.2 [verified: workstation, 2026-11-10]

| instance | n | kernel (K0) n / m | 1/2 share of K0 variables | 1/2 only, L ≤ 3: n / m | 1/2 + 2/2 + 1/3, L ≤ 4: n / m |
|---|---:|---|---:|---|---|
| s251 | 16,000 | 425 / 691 | 79 % | 263 / 528 (−38 %) | 213 / 495 (−50 %) |
| s253 | 16,000 | 434 / 692 | 84 % | 269 / 521 (−38 %) | 215 / 486 (−50 %) |
| s255 | 16,000 | 420 / 680 | 80 % | 264 / 522 (−37 %) | 216 / 489 (−49 %) |
| s1201 (new) | 32,000 | 1,223 / 1,988 | 79 % | 773 / 1,537 (−37 %) | 625 / 1,440 (−49 %) |
| s1202 (new) | 64,000 | 2,065 / 3,350 | 79 % | 1,319 / 2,603 (−36 %) | 1,064 / 2,428 (−48 %) |
| s1203 (new) | 64,000 | 1,464 / 2,357 | 81 % | 929 / 1,821 (−37 %) | 759 / 1,707 (−48 %) |

**[verified] What the table shows:**
- The effect is very stable across n and seeds: 1/2 alone removes 36–38 % of
  the K0 variables, and 1/2 + 2/2 + 1/3 removes 48–50 %.
- Clauses drop 21–29 %.
- The 1/2-only kernels have 28–29 % of their clauses at length 3.

**Elimination counts at L ≤ 4:**
- s1202: 1/2 731, 2/2 137, 1/3 133.
- s251: 1/2 155, 2/2 31, 1/3 25.

**[inference] On the size measure:**
- The size statistics alone will have very tight spread, so H1 needs few
  instances.
- The interesting variance is in H2 and H3: whether the smaller kernel with
  longer clauses is faster to solve.

**The diagnostic run combined 2/2 and 1/3.** M1 splits them (K2 vs K3).

**Reproduce:** from `cluster_staging_maxsat_strong/`:
- `python3 scripts/diag_kernel2_exact_check.py` (360 brute-force runs, 0
  optimum mismatches);
- `python3 scripts/diag_kernel2_elim.py <wcnf> ...`.
- Instances: from the repo root, `python3 -m instancegen.cli
  generate-distinct --n N --k 2 --m 1.2N --seed S --out-dir <dir>`.
  s251–s255 match `scripts/instances_calib_2sat_sc2.csv` by sha256.
- n 64,000 takes about 10 s per instance and under 100 MB.

r1 also measured α 1.5 / 2.0 (−24 to −46 %). That is out of scope now and kept
only in N-2026-11-10-a.

## 4. Design (M1) [proposal]

**Code (tree `cluster_staging_maxsat_strong/`):**
- **The pass.** A new `reduce_low_degree(C, const, rec, rules, max_len)` runs
  on the output of `kernelize`. `kernelize` and `kernelize_reference` stay
  untouched, so the twin tests and every `preprocess: kernel` run stay
  byte-identical.
- **Engine.** General min-elimination: the table of g over the neighbours
  (≤ 6 neighbours), then the greedy subcube decomposition. It is exact for any
  weights. A fixed tie-break for which Bⱼ is negated makes it deterministic.
- **Which rule applies.** `rules` is a set of p/q types, e.g. {1/2} for K1,
  {1/2, 2/2} for K2, {1/2, 2/2, 1/3} for K3. A variable is eliminated only if
  all of these hold:
  - its type is in the set;
  - all its clauses are soft;
  - every new clause has length ≤ `max_len`;
  - the new clauses are no more than the removed ones.
  
  After each elimination the K0 rules run again.
- **Lift.** A new `elim` record type in `reconstruct`.

**Config:**
- `preprocess: kernel2` with `kernel2: {rules: [...], max_len: N}`.
- `kernel` keeps its meaning.

**Gate:**
- The screen and `gain_min` are unchanged.
- For `kernel2`, the rule "no clause longer than the original" is replaced by
  `max_len`.

**Shard (schema +1, additive):** `kernel2_rules`, `kernel2_n_vars`,
`kernel2_n_clauses`, `kernel2_len_hist`, `kernel2_elims` (counts per p/q,
including cascade pure / 1/1) and `kernel2_s`.

**Stats tool:** `scripts/kernel2_stats.py <wcnf...>`.
- Writes one TSV row per instance × arm (the H1 fields).
- Optionally writes each arm's kernel as a `.wcnf` with its constant in a
  sidecar, for RC2 (H2).

**auto_hparams:**
- An explicit `kernel2` in the config wins over R0's `kernel`.
- The size rules see the kernel2 instance, so there are also fewer flips per
  call (D4).

**Tests:**
- brute-force exactness, unit and weighted, per rule set;
- lift invariant for every kernel assignment;
- the four formulas of §2;
- `kernel` byte-identical, including a hash of the K0 kernel on s251–s255;
- determinism;
- the gate;
- a shard round-trip with no `cost_mismatch`.

## 5. Instance set and statistics [proposal; final numbers in the pre-registrations]

**Instances:**
- α 1.2 at n ∈ {16,000, 32,000, 64,000}, **30 seeds each = 90 new
  instances** (D2). Fresh seeds, disjoint from earlier grids, for example:
  - 1201–1230 at 16,000;
  - 3201–3230 at 32,000;
  - 6401–6430 at 64,000.
- Plus s251, s253 and s255 (α 1.2, n 16,000, c\* known from RC2 raw) as anchors.

**H1 (size):**
- For each n and arm: median and IQR of the % change in variables and
  clauses, the share of 3- and 4-clauses, and eliminations per rule.
- **The step effect, paired by instance:** K1 vs K0 measures 1/2, K2 vs K1
  measures 2/2, K3 vs K2 measures 1/3.

**H2 (RC2 on the kernels):**
- Paired log₁₀ time ratios, K1/K0 and K2/K1 (later K3/K2), per n.
- Median ratio with a bootstrap CI, and a Wilcoxon signed-rank test.
- Runs that hit the cap count at the cap, and their number is reported.
- **Built-in correctness check:** optimum + const must be equal across K0,
  K1 and K2 on every instance.

**H3 (memetic):**
- `configs/strong/auto.yaml` on K0, K1 and K2; seeds 1–3; 900 s of process
  CPU; stop at c\*.
- Per instance: successes /3 and ERT. Paired ratios of ERT, the same
  statistics as H2, plus a sign test on successes.
- Only instances with c\* from H2 are used.

**[inference] What to expect:**
- At n 16,000 K0 already finds c\* in seconds (five of the six sc2
  instances), so H3 there will mostly compare short times.
- The 64,000 cells (K0 1.5–2k variables) are where a difference can show.

**Budget, worst case:**
- H1: workstation, minutes.
- H2: 93 × 3 arms = 279 RC2 runs at the cap from D5. At 1,800 s that is
  ≤ 140 CPU-h; real use will be far lower.
- H3: 93 × 3 arms × 3 seeds = 837 tasks × 900 s ≤ 209 CPU-h; stops at c\* cut
  most of it.

## 6. Milestones (one per turn, each after your go)

- **M1 — build + tests (workstation).**
  - §4 for K0, K1 and K2 (K3 is also a valid rule set in the engine, but not
    used until M5).
  - Smoke: §3 sizes are reproduced (or the tie-break difference explained).
  - Pass time at n 64,000.
  - A 60 s memetic smoke on s253 and s1202 for each arm.
- **M2 — generate + H1 + RC2 pilot (workstation).**
  - Generate the 90 instances and record their sha256.
  - Run H1 on all 93 instances, giving the size statistics table.
  - RC2 pilot: 2 instances per n × K0, K1, K2, 600 s cap, ≤ 3 in parallel. This
    sets the H2 cap (D5) and shows whether 64,000 is solvable.
  - Readout.
- **M3 — H2 on the cluster (pre-registered).**
  - RC2 on the written kernels, using the existing RC2 runner if it takes a
    list of `.wcnf` files.
  - Shell-only login-node commands (rsync + sbatch).
  - Readout: H2 statistics and c\* per instance.
- **M4 — H3 on the cluster (pre-registered).**
  - Memetic K0 / K1 / K2 on the instances with c\*.
  - Readout: H3 statistics.
- **M5 — 1/3 (later, per the user).**
  - Add K3 to H1 (workstation), H2 and H3 (cluster), paired against K2.

## 7. Decisions for you

1. **D1 — length bounds:** K1 ≤ 3, K2 ≤ 4, K3 ≤ 4 (proposed). The bound stops
   cascades from building long clauses. Without it, 1/2 on neighbours that
   already have 3-clauses would make 4- and 5-clauses.
2. **D2 — instance set:** n 16,000 / 32,000 / 64,000 × 30 seeds at α 1.2,
   plus the three sc2 anchors. Or fewer n, or more seeds?
3. **D3 — RC2 on the kernels:** used both as the exact-hardness measurement
   (H2) and as the source of c\*, labelled "RC2 on the exact kernel".
   - The optimum is exact either way.
   - The 2026-10-14 rule ("RC2 as distributed") concerns reported RC2 times
     against the memetic, which this study does not make.
4. **D4 — flips:** auto_hparams scales flips per call with the effective n, so
   a smaller kernel also gets fewer flips. Proposed: leave as is, and record
   it as part of the arm.
5. **D5 — RC2 cap:** set after the M2 pilot. Placeholder: 1,800 s.

## 8. Out of scope (recorded)

- **Other densities** (α 1.5 / 2.0, r1) and general use of kernel2 on other
  families.
- **Hard-only elimination** (SAT bounded variable elimination on all-hard
  x-clauses; r1 M4). It is irrelevant to soft random Max-2-SAT.
- **Fill-in-aware encodings and better elimination orders.** These are only
  options if H2 or H3 show the longer clauses hurting.

## 9. Risks [inference]

- **Smaller is not easier.** Longer clauses and more shared clauses per
  variable may slow local search or partition crossover. That is exactly what
  H2 and H3 measure, so it is a result either way, not a failure.
- **RC2 at n 64,000:** K0 kernels of 1.5–2k variables may exceed the cap. The
  M2 pilot decides, and capped runs are reported as censored.
- **Attribution:** cascades mix the rules. Counts per rule in H1 and the
  cumulative arms keep the step effects identifiable.
- **Determinism:** the elimination order is fixed (degree, then variable id),
  so reruns give identical kernels.

## Appendix A. Record of every check and measurement in this conversation (2026-11-10) [verified]

The r2 rewrite narrowed the scope to α 1.2. This appendix keeps everything
measured on 2026-11-10, including the r1 rows that are now out of scope, so
nothing lives only in the chat.

### A.1 Brute-force checks of the formulas

All checks below found **0 mismatches**.

| what | how | script |
|---|---|---|
| weighted 1/2: (A∨B1, a−d), (A∨B1∨¬B2, d), (A∨B2, b) | 2,000 random weight triples (1–9) × all 8 assignments; 0 ≤ d ≤ min(a, b) asserted | `scripts/diag_kernel2_formulas_check.py` |
| unit 2/2: the five clauses of §2 | all 16 assignments | same |
| unit 1/3: (A∨B1), (A∨¬B1∨B2), (A∨¬B1∨¬B2∨B3) | all 16 assignments | same |
| the simulated elimination (general min-elimination + greedy decomposition) preserves the optimum | 360 runs: n 12; m 14 / 18 / 24 / 30; unit weights and weights 1–5; bounds (L 3, occ 3), (L 4, occ 4), (L 6, occ 6, growth 2); 1,018 eliminations | `scripts/diag_kernel2_exact_check.py` |

### A.2 r1 kernel degree profile (share of the K0 variables)

| instance | n | α | K0 n / m | 1/2 | 1/3 | 2/2 | 2/3 | other |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| s251 | 16,000 | 1.2 | 425 / 691 | 79 % | 9 % | 7 % | 3 % | 1 % |
| s253 | 16,000 | 1.2 | 434 / 692 | 84 % | 9 % | 6 % | 1 % | 0 % |
| s255 | 16,000 | 1.2 | 420 / 680 | 80 % | 9 % | 7 % | 2 % | 2 % |
| s1201 | 32,000 | 1.2 | 1,223 / 1,988 | 79 % | 10 % | 8 % | 2 % | 1 % |
| s1202 | 64,000 | 1.2 | 2,065 / 3,350 | 79 % | 10 % | 7 % | 2 % | 1 % |
| s1203 | 64,000 | 1.2 | 1,464 / 2,357 | 81 % | 8 % | 9 % | 1 % | 1 % |
| s256 | 64,000 | 1.1 | 572 / 900 | 87 % | 8 % | 4 % | 1 % | 0 % |
| s257 | 64,000 | 1.1 | 300 / 472 | 87 % | 7 % | 5 % | 1 % | 1 % |
| s258 | 64,000 | 1.1 | 332 / 512 | 92 % | 5 % | 3 % | 0 % | 0 % |
| s901 | 16,000 | 1.5 | 3,258 / 5,925 | 57 % | 15 % | 13 % | 8 % | 7 % |
| s902 | 16,000 | 2.0 | 8,408 / 18,439 | 32 % | 18 % | 12 % | 13 % | 25 % |

- Every K0 clause has weight 1 and length 2, apart from at most 2 units per
  instance.
- s256–s258 are the α 1.1 calib_2sat_sc2 instances (sha256 equal).
- s901 and s902 were made with `--m 24000 --seed 901` and
  `--m 32000 --seed 902`.

### A.3 Simulated reduction under each bound

| instance | L ≤ 2, occ ≤ 4 (dominance only) | L ≤ 3, occ ≤ 3 (1/2): n / m | L ≤ 4, occ ≤ 4 (+2/2, 1/3): n / m | eliminations at L ≤ 4 |
|---|---|---|---|---|
| s251 | 425 → 422 | 263 / 528 | 213 / 495 | 1/2 155, 2/2 31, 1/3 25, 1/1 1 |
| s253 | 434 → 421 | 269 / 521 | 215 / 486 | 1/2 159, 2/2 39, 1/3 18, pure 2, 1/1 1 |
| s255 | 420 → 419 | 264 / 522 | 216 / 489 | 1/2 140, 2/2 32, 1/3 31, pure 1 |
| s1201 | — | 773 / 1,537 | 625 / 1,440 | 1/2 449, 2/2 81, 1/3 67, 1/1 1 |
| s1202 | — | 1,319 / 2,603 | 1,064 / 2,428 | 1/2 731, 2/2 137, 1/3 133 |
| s1203 | — | 929 / 1,821 | 759 / 1,707 | 1/2 508, 2/2 98, 1/3 99 |
| s256 | 572 → 554 | 356 / 679 | 283 / 623 | 1/2 204, 2/2 48, 1/3 34, pure 2, 1/1 1 |
| s257 | 300 → 298 | 184 / 354 | 147 / 327 | 1/2 109, 2/2 20, 1/3 24 |
| s258 | 332 → 331 | 213 / 392 | 168 / 360 | 1/2 117, 2/2 21, 1/3 26 |
| s901 | 3,258 → 3,241 | 2,195 / 4,861 | 1,769 / 4,546 | 1/2 1,086, 2/2 192, 1/3 210, pure 1 |
| s902 | 8,408 → 8,403 | 6,397 / 16,427 | 5,227 / 15,608 | 1/2 2,117, 2/2 438, 1/3 625, 1/1 1 |

- "—" means not run.
- Allowing one extra clause per elimination (`growth` 1) changed nothing at
  L ≤ 4.
- No elimination added a constant.
- **Cost:** three instances (n 32,000 and two at 64,000) took 29.6 s and
  84 MB together.

### A.4 Cascades in today's kernel

See the table in §2.1 (six α 1.2 instances). On all six, the fixpoint check
found no pure or 1/1 variable and no complementary unit pair left.
