# Research notes: which optima RC2 can certify for random Max-3-SAT at n ≥ 250

**Date:** 2026-10-06. **Status:** research notes, written for decision R3-c
(`NEXT_SESSION_CONTEXT.md` §0). No instance was generated and nothing was
run for these notes. Every number comes from existing RC2 rows, re-derived
from the raw files listed in §8.

Labels used below:
- **[verified]**: read directly off the rows;
- **[inference]**: follows from verified numbers by a stated argument;
- **[extrapolation]**: assumes a trend continues beyond the measured range.

Notation:
- n = variables; α = m/n = clause-to-variable ratio;
- c\* = optimum (minimum number of falsified clauses);
- "window" = RC2 certifies in 30 s < t ≤ 900 s, i.e. the instance is
  RC2-eligible.

All statements are about **RC2 as fixed for this project**: PySAT
`RC2(wcnf, "g3")` with default options, 900 s cap. They are not about the
optimum itself, and not about another solver or cap.

---

## 1. The claims

**C1 [verified, n = 250].** At n = 250, every RC2-eligible instance in the
repository has **c\* = 1**. This covers 100 SATLIB uuf250 instances and 25
generated instances, at α 4.26–8.0.
- **No instance with c\* ≥ 2 was certified within 900 s.** At least 21
  instances are proven by RC2's own lower bound to have c\* ≥ 2. All 21
  were censored.
- c\* = 0 (satisfiable) instances are certified in ≤ 1 s. That is below
  the window.

**C2 [inference + extrapolation, n = 250].** c\* = 2 at n = 250 sits at or
beyond the window's upper edge.
- Its median RC2 time is estimated at about **0.6–5 ks** (§3.2).
- A minority of c\* = 2 instances certifying within 900 s is **not
  excluded**. The observed rate is 0 out of somewhere between 6 and about 23
  instances (§3.3).
- c\* ≥ 3 at n = 250 is out of reach: each further unit multiplies the time
  again.

**C3 [extrapolation, n ≥ 300].** At n ≥ 300, eligible instances are
expected to have c\* = 1 only.
- c\* ≥ 2 is expected in the tens of ks.
- **c\* = 1 itself moves to the window's edge.** The estimated median at
  n = 300 is about 0.6–2.3 ks. So at n ≥ 300 the window may hold few
  instances of any optimum (§3.4).

**C4 [verified + inference, density].** **Raising α does not produce
certifiable c\* ≥ 2 instances at n ≥ 250.**
- It raises c\*, and every extra unit of c\* multiplies RC2's time.
- Every n = 250 cell at α ≥ 5 (15/15) was censored, with RC2's lower
  bound stuck at 2, 3 and 4 after 900 s (§4).

**Net statement for R3-c.** For random Max-3-SAT under the fixed RC2 and
window:
- **n ≥ 250 effectively means c\* ∈ {0, 1}**, and only c\* = 1 is eligible;
- c\* = 2 at n = 250 is an occasional exception at best;
- c\* > 2 is not available at any n ≥ 250.

**What the claims are not.** They do not say the optimum is 0–1 at large n.
At n = 250 and α ≥ 5 the optimum is provably ≥ 2–4, and probably larger
(§4). The claims are about which optima **RC2 can certify inside the
window**.

---

## 2. Data and conditions

| source | instances | α | cap | PySAT | role here |
|---|---|---|---|---|---|
| SATLIB uuf250 (`results/profile_uuf250/`) | 100 (uuf250-01 … -0100), n 250, m 1065 | 4.26 | 900 s (+60 grace) | **unknown** (not recorded) | main n = 250 sample |
| SATLIB uuf50 … uuf200 (`results/profile_uuf/`) | 10 per size, n 50/100/150/200 | ≈ 4.26 (threshold sets) | 600 s | unknown | per-size and per-c\* time steps |
| calib_a / calib_b (`results/profile_calib_{a,b}_all.jsonl`) | Max-3-SAT n 250: 25 (α 4.26 ×10, 4.35, 5, 6, 8 ×5); n 100/150 rows | 4.26–8 | 900 s (+60) | 1.9.dev3 | generated instances; density effect |

Notes:
- `profile_uuf` also holds 10 uuf250 instances at a 600 s cap. They are
  byte-identical (sha256) to 10 of the 100 in `profile_uuf250`, so they are
  **not counted twice**.
- The unknown PySAT version of the SATLIB profiles limits pooling. Still,
  the calib n = 250, α = 4.26 rows (PySAT 1.9.dev3) give c\* = 1 times of
  33–388 s. That lies inside the SATLIB uuf250 range of 14.6–890 s.
  **[verified]**
- A row censored with lower bound LB proves c\* ≥ LB, because RC2's lower
  bound is sound. It says nothing about how far above LB c\* is.

---

## 3. The argument for C1–C3

### 3.1 What n = 250 shows directly [verified]

**SATLIB uuf250, 100 instances, 900 s:**

| outcome | count | RC2 time |
|---|---:|---|
| certified c\* = 1 | 77 | 14.6–889.6 s; median 110.6 s; 70 in the window, 7 ≤ 30 s |
| censored, LB 1 | 18 | killed at the cap; c\* ≥ 1, value unknown |
| censored, LB 2 | 5 | killed at the cap; **c\* ≥ 2 proven** |
| certified c\* ≥ 2 | **0** | — |

**Generated n = 250 (calib_a/b, PySAT 1.9.dev3):**

| α | certified | censored (LB) |
|---:|---|---|
| 4.26 | c\* 0 ×3 (0–1 s); c\* 1 ×6 (33–388 s) | 1 (LB 1) |
| 4.35 | c\* 1 ×2 (103, 324 s) | 3 (LB 1, 1, 2) |
| 5.0 | — | 5 (LB 2 ×5) |
| 6.0 | — | 5 (LB 3 ×5) |
| 8.0 | — | 5 (LB 4 ×5) |

Totals over the 125 instances:
- **85 certified c\* = 1 (77 + 6 + 2), 3 certified c\* = 0, 0 certified
  c\* ≥ 2.**
- Every eligible instance (70 SATLIB + 8 generated) has c\* = 1.
- **21 instances are proven c\* ≥ 2, and all 21 are censored:** 5 SATLIB,
  1 at α 4.35, 15 at α ≥ 5.

**This is C1.**

### 3.2 The cost of one more unit of c\* [verified at n ≤ 200; inference at n = 250]

From the SATLIB threshold sets: geometric means of RC2 time over the
certified instances, with counts in brackets.

| n | c\* = 1 | c\* = 2 | step c\* 1→2 |
|---:|---:|---:|---:|
| 100 | 0.09 s [7] | 0.67 s [3] | **×7.2** |
| 150 | 1.33 s [7] | 7.35 s [3] | **×5.5** |
| 200 | 20.3 s [8] | 199 s [2] (128.5, 307.4) | **×9.8** |
| 250 | 111 s [77] (biased low: 23 censored excluded) | none certified | — |

Growth with n at fixed c\*:

| n step | c\* = 1 | c\* = 2 |
|---|---:|---:|
| 100 → 150 | ×14.3 | ×11.0 |
| 150 → 200 | ×15.2 | **×27.0** |
| 200 → 250 | ×5.5 (biased low by censoring) | — |

Two independent estimates of the median c\* = 2 time at n = 250
**[extrapolation]**:
- **(a) per-c\* step.** c\* = 1 at n = 250 (≈ 110–150 s) × the step at
  n ≤ 200 (×5.5–9.8) gives **≈ 0.6–1.5 ks**.
- **(b) per-n growth.** c\* = 2 at n = 200 (≈ 200 s) × the 150 → 200 growth
  (×27) gives **≈ 5 ks**.
  - The c\* = 2 growth with n is steeper than the c\* = 1 growth (×27 against
    ×15). So (b) may itself be conservative.

Both estimates put the median at or above the 900 s cap. **This is C2.**

**Correction to an earlier statement.** In this session's chat answer I
said c\* = 2 at n = 250 "would take hours". I based that on the B1 slope of
2.32 decades per unit of c\* (`docs/CALIB_B_B1_READOUT.md` §5). That slope
was fitted on n = 250 rows whose certified c\* is only 0 or 1. It therefore
measures the **satisfiable → unsatisfiable** jump (≈ 1 s → ≈ 100 s), not the
cost of one more core. The direct SATLIB step is ×5.5–9.8, about one decade.
**"Hours" is withdrawn.** The estimate is 0.6–5 ks, with the boundary at
n = 250 soft rather than hard.

### 3.3 How strong is "0 certified c\* ≥ 2" at n = 250? [inference]

- **Known c\* ≥ 2 near the threshold:** 6 instances (5 SATLIB + 1 at
  α 4.35).
- **Unknown:** the 21 LB-1 censored instances (18 SATLIB + 3 generated)
  may also be c\* ≥ 2.
  - In the SATLIB threshold sets at n = 100–200, 8 of 30 instances (27 %)
    have c\* = 2.
  - A similar share at n = 250 implies about 20–27 c\* ≥ 2 instances among
    the 100.
  - So most of the 18 LB-1 censored rows are probably c\* ≥ 2 instances
    that RC2 had not yet proved past LB 1.
- **Resulting bound on the eligible fraction p of c\* = 2 instances at
  n = 250:**
  - 0 of N certified gives a 95 % upper bound of 1 − 0.05^(1/N);
  - **N = 6 → p ≤ 0.39; N ≈ 23 → p ≤ 0.12.**
- **Reading:** a c\* = 2 cell at n = 250 would put at most a small minority
  of its instances in the window. A rate as high as ~1/3 cannot be excluded
  with N = 6. It is unlikely if, as argued, most LB-1 censored rows are
  c\* ≥ 2.

### 3.4 Beyond n = 250 [extrapolation]

Applying the measured per-n growth of c\* = 1 (×5.5–21 per +50 variables,
the lower value biased low) to n = 300:
- **c\* = 1:** median ≈ 110 s × 5.5–21 ≈ **0.6–2.3 ks**. A large share of
  c\* = 1 instances would be censored, and the eligible ones would sit in
  the window's upper part.
- **c\* = 2:** a further ×5.5–10 gives ≈ **3–23 ks**. Effectively none
  eligible.

**This is C3.** It also bears on R3-b. Random Max-3-SAT at n ≥ 300 may give
a thin window **even at c\* = 1**. If larger-n 3-SAT cells are explored, the
grid should expect low window yields and say so in advance.

### 3.5 Why the steps are this large (explanation consistent with the data, not proved here)

**RC2 is core-guided.** To certify c\* = k it must find k unsatisfiable cores
(k UNSAT calls), each followed by a cardinality relaxation, and then one
SAT call. So:
- **The c\* = 0 → 1 step is the satisfiable → unsatisfiable step.**
  - Refuting random 3-CNF near the threshold needs resolution proofs of size
    exponential in n: Chvátal–Szemerédi 1988; Ben-Sasson–Wigderson 2001
    give 2^Ω(n/α^(1+ε)).
  - CDCL refutations are resolution proofs. Hence the ×14–15 per 50
    variables at fixed c\* = 1.
- **Each further core repeats a refutation of the same kind.** The formula
  now has the earlier cores relaxed, i.e. "the formula with any k − 1
  clauses dropped is unsatisfiable". That is no easier than the first
  refutation, and the totalizer encoding grows with k. Hence a multiplicative
  step per unit of c\*, and a step that itself grows with n.

---

## 4. Density (C4)

**What the rows show [verified]:**
- n = 250, α 5 / 6 / 8: **15/15 censored**, with LB 2 / 3 / 4 after 900 s.
- Smaller n shows the same: at n = 100 and n = 150, α 6 and α 8 are fully
  censored (LB 5–8 and 4–6).
- Raising α increases c\*. Since time multiplies per unit of c\*, density
  moves instances **out** of the window.

**What c\* those censored cells hold [extrapolation]:**
- At α = 5, c\* is 2–4 at n = 100 and 1–3, plus ≥ 3 and ≥ 4, at n = 150.
- c\* grows roughly in proportion to n at fixed α. That suggests c\* ≈ 4–8
  at n = 250, α = 5.
- At ×5–10 per unit from a ~100 s base, that is ≥ 10⁴ s.

**The in-between densities (α 4.4–4.8 at n = 250) are untested.** Moving
from 4.26 toward 5 should mainly change the c\* mix: more c\* = 2–3, fewer
c\* = 0–1. It does not change the time per c\*. So such a cell would
contain more c\* ≥ 2 instances, but they would face the same 0.6–5 ks
median. Its expected window yield is the c\* = 1 share times about 0.75–0.9
(70 of the 77–95 SATLIB c\* = 1 instances are eligible), plus a small
c\* = 2 contribution. **[inference]**

**Higher density does make each refutation shorter** (the 1/α factor in the
resolution bound). That is visible: in 900 s RC2 reaches LB 4 at α 8 but
only LB 2 at α 5. It does not offset the growth of c\* in any row measured.

---

## 5. Limits of the evidence

1. **Small c\* = 2 samples** at n ≤ 200: 3, 3 and 2 instances. The per-c\*
   step (×5.5–9.8) is uncertain by a factor of about 2.
2. **Unknown PySAT version and host** for the SATLIB profiles. The overlap
   with the 1.9.dev3 calib rows (§2) argues against a large shift, but it is
   not a controlled comparison.
3. **600 s cap for n ≤ 200.** No certified time there exceeds 307 s, so
   censoring does not bias those estimates.
4. **Censoring biases the n = 250 c\* = 1 mean low.** The 23 censored rows
   are excluded from it, which makes the §3.2 estimates of C2 and C3
   optimistic, i.e. it favours eligibility.
5. **Extrapolation in n.** C3 assumes the per-n growth seen at n = 100–250
   continues to n = 300.
6. **Heavy tails.** At n = 250, c\* = 1 times span 61× (14.6–890 s). A
   single c\* = 2 instance certifying under 900 s would not contradict C2. It
   would contradict a claim of impossibility, which these notes do not make.

## 6. What would change the conclusion

These are described only; none is prepared or proposed for running.
- **Falsifier of C2 as a design constraint:** a c\* ≥ 2 cell at n ≥ 250 in
  which a sizeable fraction (say ≥ 1/3) of instances certify within 900 s.
  - The smallest direct test would be a few generated cells at n = 250 with
    α between 4.4 and 4.8, profiled at the standard cap.
  - It would cost RC2 time only for the instances that are censored.
- **Falsifier of C3:** c\* = 1 instances at n = 300 with a median RC2 time
  well under 600 s.
- **Outside this project's fixed choices:** a longer cap or a different
  MaxSAT solver configuration would move the boundary. Both are excluded by
  the standing decisions (RC2 version and window fixed).

## 7. Implications for the open decisions

- **R3-c (Max-3-SAT optimum range at n > 250).** "Require c\* > 1" and
  "n > 250" are, for practical purposes, **incompatible** under the fixed RC2
  and window. "Require c\* > 2" is incompatible at any n ≥ 250. The options
  stated in the chat answer remain:
  1. n > 250 with c\* = 1: size diversity, but expect thin yields at n ≥ 300
     (C3);
  2. c\* ≥ 2 at n ≈ 175–200: next to the historical uuf200 set (c\* = 2 at
     128 and 307 s);
  3. leave the optimum range to Max-2-SAT.
- **R3-b (larger-n grid).** For Max-3-SAT, the grid should place cells near
  the threshold (α ≈ 4.26–4.35), not at higher density. It should state the
  expected yield up front, from C1–C3.
- **Max-2-SAT is not covered by these claims.**
  - Its eligible c\* is 18–23 at n 250–400, so c\* > 1 or > 2 holds
    automatically.
  - Its per-c\* step is shallow: about ×1.7 per unit at n = 400
    (`CALIB_B_B1_READOUT.md` §5).
  - There the density lever runs the other way: at larger n, α must go
    **down** toward 2.0 or below to keep c\* under RC2's ceiling of about
    22–25.

## 8. Reproduction

All paths are relative to `cluster_staging_maxsat/`.
- `results/profile_uuf250/uuf250_arr_task_*.jsonl`: 100 rows, fields
  `profile.{status, solve_s, final_cost, cost_lower_bound}`. Status
  `optimal` = certified; `timeout` / `subprocess_killed` = censored at LB
  `cost_lower_bound`.
- `results/profile_uuf/uuf_diff_arr_task_*.jsonl`: 50 rows, 600 s cap. The
  10 uuf250 rows are byte-identical to 10 in `profile_uuf250` (sha256 of
  `data/unsat*/uuf250-*.cnf`) and are dropped before pooling.
- `results/profile_calib_{a,b}_all.jsonl`: generated rows. Parse n, k and α
  from `instance`: `_v{n}_k{k}_sr{α}_…_s{seed}.wcnf`.
- Geometric means use max(solve_s, 1 ms). Step ratios are ratios of
  geometric means over certified instances only.
- `results/corpus_freeze_prep/candidate_cells.csv`: per-cell summary
  consistent with the above.
