# RC2 grid points under the agreed window (30, 900] s — Max-2-SAT and Max-3-SAT

**Written:** 2026-10-07. Analysis of existing rows only: nothing was
generated, submitted or re-run.

**Why this note exists.** In the 2026-10-07 chat, several statements on RC2
behaviour across n and α were made against a **60–600 s** window. That is the
B1 planning window (`docs/CALIB_B_PLAN.md`, `docs/CALIB_B_B1_READOUT.md` §5),
not the agreed one. The agreed RC2 eligibility rule is **certified and
30 s < t ≤ 900 s** (`NEXT_SESSION_CONTEXT.md` §1). This note recomputes the
grid points under that rule.

**What does not change.** `results/corpus_freeze_prep/candidate_cells.csv` and
every §5.3 cell result already use (30, 900] s. Its cell classifications
stand. What changes is the reading of the B1 slope finding (§3) and the
answer about "n = 150, c\* = 3" (§4).

**Reproduce** (from `cluster_staging_maxsat/`):
`python3 scripts/grid_points_window.py` writes
`results/corpus_freeze_prep/grid_points_30_900.csv` (one row per
(k, n, c\*, source)) and prints the censored lower bounds and per-row slopes.

---

## 1. Data and definitions

| source | rows | cap | notes |
|---|---|---|---|
| calib_a + calib_b | 290 generated pure-soft instances, Max-2-SAT and Max-3-SAT | 900 s (+60 grace) | PySAT 1.9.dev3; Q2 from the M2 primary arm (3.5 s per call) for the 70 eligible |
| SATLIB uuf250 | 100 | 900 s | PySAT version unknown |
| SATLIB uuf50–uuf200 | 10 per size | 600 s | PySAT version unknown; no certified time exceeds 307 s, so the lower cap does not censor |

- **Grid point** = (k, n, c\*). The generator controls α, not c\*. A grid
  point is therefore observed through the (n, α) cells that produce it
  (column "α seen").
- **In window** = certified and 30 < t ≤ 900. **Below** = certified, t ≤ 30.
- **SATLIB uuf sets are unsatisfiable by selection**, so they hold no c\* = 0
  instances. Generated cells at the same n and α do (for example, n = 150,
  α 4.26: four of five have c\* = 0).
- Window width log10(900/30) = **1.48 decades** (the 60–600 s window was 1.0).

## 2. Grid points per (k, n, c\*)

Read "in / certified" per c\*. Q2 is over the eligible generated instances,
primary arm; "—" means none tested.

### 2.1 Max-3-SAT

| n | c\* in window (in / certified) | c\* at the lower edge | below window | α seen | censored (LB) | Q2 |
|---:|---|---|---|---|---|---|
| 50 | **9–13** (14/14; times 33–847 s) | — | c\* ≤ 8 (8: 9.9–21.8 s) | 8, 8.5, 9 | α 8.5: 12; α 9: 13, 13, 14 | 0/14 |
| 70 | **7–8** (9/9; 146–436 s) | 6 (3/5), 5 (1/4) | c\* ≤ 4 | 6, 6.2, 6.5 | α 6.5: 7; α 8: 9 ×5 | 0/13 |
| 100 | **4–5** (7/7; 47–213 s) | — | c\* ≤ 3 (3: 1.5–17.1 s) | 5, 5.2, 5.5 | α 5.5: 5, 5; α 6: 5–6; α 8: 7–8 | 0/7 |
| 150 | **3** (1/1; 772 s) | 2 (1/5: generated 14.9, **34.9** s; SATLIB 3.9–21.6 s) | c\* ≤ 1 (≤ 6.4 s) | 4.8, 5.0 | α 4.6: 3; α 4.8: 3, 4; α 5: 3, 4; α 6: 4 ×5 | c\* 2: 1/1; c\* 3: 0/1 |
| 200 | **2** (2/2; 128, 307 s) | 1 (4/8; 1.9–43.4 s, median 30.07 s) | — | 4.26 (SATLIB only) | none | — (see §4.2) |
| 250 | **1** (78/85: generated 8/8, SATLIB 70/77; 14.6–890 s) | — | c\* 0 (0.5–0.7 s) | 4.26, 4.35 | SATLIB LB 1 ×18, LB 2 ×5; generated LB 1 ×3, LB 2 ×1; α ≥ 5 fully censored (LB 2 / 3 / 4) | c\* 1: 6/8 |

**[verified]** from the rows. Two regularities:
- **The in-window c\* falls one or two steps per size step:** about 11 at
  n = 50, 7–8 at 70, 4–5 at 100, 3 at 150, 2 at 200, 1 at 250.
- **At every n there is a c\* band in the window.** No size tested is empty
  under (30, 900]. Under 60–600 s, n = 150 was.

### 2.2 Max-2-SAT

| n | c\* in window (in / certified) | c\* at the lower edge | below window | α seen | first fully censored α (LB) | Q2 |
|---:|---|---|---|---|---|---|
| 100 | **31–50** (6/6; 31–753 s) | — | c\* ≤ 30 (≤ 16.3 s) | 4, 4.5, 5, 6 | none in grid (α 6: 49–54 censored ×4) | 0/6 |
| 150 | **24, 26–28** (4/4; 36–301 s) | 23 (2/3), 25 (1/3) | c\* ≤ 21 | 3, 3.15, 3.3 | 4 (35–40) | 0/7 |
| 250 | **18, 22** (2/2; 71, 610 s) | 19 and 21 certified below (9.5, 28.6 s) | c\* ≤ 17 | 2.35, 2.5 | 3 (29–33) | 0/2 |
| 400 | **18–23** (11/11; 43–413 s) | — | c\* ≤ 17 (≤ 18.7 s) | 2.0, 2.15, 2.3 | 3 (32–39) | 2/11 |

**[verified].** The in-window c\* band falls from 31–50 to 24–28 between
n = 100 and 150, and then stays near **18–23** from n = 250 to 400. At
n = 250 the band is noisy: N = 1 per c\* and two below-window instances
inside it.

## 3. Window capacity: how many integer c\* values fit

Slope = OLS of log10(t) on c\*, per row, over certified rows (pooled sources,
t > 1 ms). Capacity = 1.48 / slope.

| family | n | N | time factor per +1 c\* | capacity (30–900) | capacity (60–600, B1 §5) |
|---|---:|---:|---:|---:|---:|
| Max-2-SAT | 100 | 21 | ×1.3 | 11.6 | 7.9 |
| | 150 | 22 | ×1.6 | 7.7 | 5.2 |
| | 250 | 12 | ×1.8 | 5.9 | 4.0 |
| | 400 | 18 | ×1.7 | 6.2 | 4.2 |
| Max-3-SAT | 50 | 41 | ×2.7 | 3.4 | 2.3 |
| | 70 | 29 | ×4.9 | 2.1 | 1.5 |
| | 100 | 28 | ×8.4 | 1.6 | 1.1 |
| | 150 | 25 | ×19.3 | **1.15** | **0.7** |
| | 200 | 10 (SATLIB) | ×9.8 | 1.5 | — |
| | 250 | 88 | (×198) | (0.64) | (0.4) |

- N and the 3-SAT slopes differ slightly from B1 §5 because SATLIB rows are
  pooled here. That source has an unknown PySAT version.
- **n = 250 is not a per-core cost.** That row certifies only c\* 0 and 1.
  Its slope measures the satisfiable → unsatisfiable jump. The per-unit step
  from c\* 1 to 2 is about ×5.5–9.8 (SATLIB, n 100–200;
  `RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md` §3.2).
- **Revision of B1 §5.** Its statement "no α placement can put instances in
  the window" for 3-SAT n = 150 is a statement about the 60–600 s window.
  Under (30, 900] the capacity is about 1.15. The window holds one integer c\*
  value at n = 150, and that value is c\* = 3.

## 4. Specific points

### 4.1 Max-3-SAT n = 150, c\* = 3

This corrects the chat answer of 2026-10-07, which said "no" under 60–600.

**Evidence [verified].**
- **One eligible instance:** `wksat_v150_k3_sr5.00_hr0.00_w1_uniform_s3`,
  772 s, Q2 = 0.
- **Three censored instances at LB 3:** α 4.6 s5, α 4.8 s5, α 5.0 s5. Their
  c\* is 3 (certifying above 900 s) or ≥ 4. The rows cannot tell which.
- **c\* = 2 at n = 150** is mostly below the window: 1 of 5 eligible (34.9 s).
  That one is the n = 150 instance with Q2 = 1.

**Expected time [inference].** The geometric mean at c\* = 2 is 11.6 s, and
one more core costs about ×19. That puts a typical c\* = 3 instance near
200–300 s, inside the window. The single observation (772 s) and the three
LB-3 censorings say the upper tail reaches 900 s.

**The cell rule is the obstacle, not the window.**
- At α = 5.0 the c\* mix is {1, 2, 3, ≥ 3, ≥ 4}.
  - The c\* = 1–2 instances are below the window.
  - The c\* ≥ 4 instances are censored.
- So r1 (certified ≥ 0.8) fails at the α that produces c\* = 3: 3/5 certified.
  The eligible yield is 1/5.
- A narrower α cannot fix this. At n = 150 the c\* spread within one cell
  (about 3 integers) is wider than the window (about 1).
- This point is reachable only as a post-stratified (n, c\*) stratum, not as
  a §5.3 (n, α) cell (decision G-a, §6).

### 4.2 Max-3-SAT n = 200: the gap in the generated grid

**Evidence [verified]: SATLIB uuf200 only, α 4.26, 10 instances.**
- c\* = 2: 2/2 in window (128.5 s and 307.4 s).
- c\* = 1: 4 of 8 in window (median 30.07 s, on the boundary).
- **No generated n = 200 row exists.**
- Historical memetic context (a different arm, so not Q2):
  - uuf200-01: 4/5 runs succeed, ERT 388 s.
  - uuf200-02: 5/5 succeed, ERT 9.2 s.
  - Source: `docs/UUF_THREE_ARM_ABLATION_READOUT.md`.

**Window at n = 200 [inference].**
- c\* = 3 at n = 200 is about 200 s × ×10 ≈ 2 ks, past the cap.
- **So n = 200 has a two-value window, c\* ∈ {1 (upper half), 2}.** Only one
  integer beyond it is censored.
- That makes n = 200 a stronger RC2 point than n = 150 (capacity 1.5 vs 1.15).
  Its c\* mix is also less exposed to the censored side.

**α placement for a generated n = 200 row [inference; untested].**
- Generated cells at α 4.26 put roughly 30–80 % of instances at c\* = 0 (the
  n = 150 and n = 250 cells). Those are below the window.
- **α ≈ 4.4 / 4.6 (two-α hedge)** shifts mass to c\* 1–2.
- Above about 4.8, c\* ≥ 3 appears and r1 is at risk. The n = 150 row was
  fully censored at α 6, and n = 250 at α 5.

**Memetic side [inference].** Q2 for Max-3-SAT is 0/34 at n ≤ 100, 1/2 at
n = 150 and 6/8 at n = 250. n = 200 lies between them, so its Q2 rate is
untested and plausibly intermediate.

### 4.3 Max-3-SAT n > 250 [extrapolation]

The 100 uuf250 times are scaled by the per-50-variable growth of c\* = 1
(×5.5–21, `RESEARCH_NOTES…` §3.4). Censored rows count as > 900 s.

| assumed factor n 250 → 300 | ×5.5 | ×10 | ×15 | ×21 |
|---|---:|---:|---:|---:|
| uuf-like instances in (30, 900] at n = 300 | 51 % | 31 % | 21 % | 14 % |

- These are unsatisfiable-filtered instances. A generated cell also loses
  its c\* = 0 share below the window, and its c\* ≥ 2 share above it.
- **So n = 300, c\* = 1 is an edge point:** about 10–50 % eligible, with r1
  very likely failing.
- The 30–900 window makes this less bleak than the C3 wording in the
  research notes. It does not reverse it.

### 4.4 Max-2-SAT n > 400 [hypothesis; untested]

**The pattern.**
- The in-window band held at c\* ≈ 18–23 from n = 250 to n = 400.
- Capacity stays about 6 integers.
- The α that produces it fell from 2.35 to 2.0–2.3.
- c\*/n at α 2.0 is about 0.03–0.05 at both n = 250 and n = 400.

**Where it points.** If the band keeps holding, n = 600 needs c\* ≈ 18–23,
that is c\*/n ≈ 0.03–0.04. That suggests **α ≈ 1.8–2.0**.

**The opposite risk.** Time at fixed c\* grows with n. The band may move down
instead, and then a lower α would be needed.

**Memetic side.** Q2 is 2/11 at n = 400 and 0/15 at n ≤ 250, the only
upward signal in this family.

## 5. Grid points by status

| status | Max-3-SAT | Max-2-SAT |
|---|---|---|
| **RC2 in window and memetic work shown** | n 250, c\* 1 (Q2 6/8; reference stratum, frozen, no new instances) | n 400, c\* 18–23 (Q2 2/11, weak) |
| **RC2 in window, memetic trivial** (closed by earlier decision) | n 50 c\* 9–13; n 70 c\* 7–8; n 100 c\* 4–5 (Q2 0/34) | n 100 c\* 31–50; n 150 c\* 24–28; n 250 c\* 18–22 (Q2 0/15) |
| **RC2 in window on thin evidence; memetic open** | n 150, c\* 3 (1 eligible; not reachable as a §5.3 cell, §4.1); **n 200, c\* 2 and the upper half of c\* 1** (SATLIB only, 10 instances, §4.2) | — |
| **Untested, projected** | n 300 c\* 1 (edge, §4.3) | n 600 c\* ≈ 18–23 at α ≈ 1.8–2.0 (§4.4) |

**Reading.** In the larger-n direction (`NEXT_SESSION_CONTEXT.md` §0), the
best-supported **new** Max-3-SAT grid point is **n = 200, c\* ≈ 2**. It needs
a generated row, since only SATLIB evidence exists. For Max-2-SAT the
direction is n > 400 at α at or just below 2.0.

## 6. Decisions this raises (for R3-b / R3-c)

- **G-a. Unit of a stratum.** Should a stratum be an (n, α) cell under §5.3
  as pre-registered, or an (n, c\*) point post-stratified from certified
  instances?
  - Post-stratifying selects on an RC2 outcome (c\*), not on ρ, so the
    no-ρ-selection rule does not forbid it.
  - But it makes r1 meaningless, and it conditions the RC2-time range.
  - Without it, n = 150 c\* 3 and n = 300 c\* 1 cannot be strata.
- **G-b. Max-3-SAT n = 200 row.** Add a generated n = 200 row with α
  {4.4, 4.6} to the R3-b larger-n plan? It sits between the tested n = 150
  and the frozen n = 250. It is "larger n" relative to the generated grid,
  not relative to 250.
- **G-c. Max-3-SAT n > 250 (R3-c).** Under (30, 900], n = 300, c\* = 1 is an
  edge point with about 10–50 % eligible. Explore it, or close it with this
  evidence?
- **G-d. Max-2-SAT n > 400.** Choose the n value(s) and a two-α hedge around
  α ≈ 1.8–2.0, aiming at c\* ≈ 18–23.

Nothing in this note authorises generation or submission. Each of G-b to
G-d needs a written plan and approval first.

## 7. Limits

1. **Small samples.**
   - Most grid points rest on 1–8 certified instances.
   - Per-c\* time steps are uncertain by about ×2 (research notes §5).
   - The n = 200 slope rests on 10 SATLIB instances with only c\* 1 and 2.
2. **Mixed PySAT versions.** SATLIB rows have an unknown PySAT version. They
   are pooled into the slopes for n = 50–250, and they are all of n = 200.
3. **SATLIB uuf is unsatisfiable-filtered.** Its c\* mix is not that of a
   generated cell at the same α.
4. **Censored LBs bound c\* from below only.** In particular, the LB-3 rows
   at n = 150 do not show whether c\* = 3 instances exist above 900 s.
5. **Q2 counts are over eligible instances only** (no memetic runs below
   30 s, by decision). n = 200 has no Q2 data in the primary arm.
