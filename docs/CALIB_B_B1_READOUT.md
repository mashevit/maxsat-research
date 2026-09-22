# calib_b — B1 read-out (RC2 grid refinement)

Read-out of **B1**, the RC2 profiling run over the `calib_b` grid
(`instancegen/grids/calib_b.yaml`: 22 cells, 110 instances — 17 exploratory
cells at seeds 1–5 and 5 reinforcement cells at seeds 6–10). Same stack as
A1 throughout: `RC2(wcnf, solver="g3")` with `adapt=exhaust=minz=False`,
cap 900 s + 60 s grace, 1 CPU · 8 GB, cluster `main` partition.

Sources: `cluster_staging_maxsat/results/profile_calib_b_all.jsonl` (110 rows)
and `..._env.jsonl`, produced by `scripts/aggregate_rc2_profile.py --batch
calib_b`; pooled eligibility from
`python -m src.bench.calib_tier2_select --batches calib_a calib_b`
(`results/calibration/tier2_eligible.csv`, `tier2_cells.csv`).

Companion to [`CALIB_B_PLAN.md`](CALIB_B_PLAN.md) (written before any instance
was generated) and [`CALIB_A_A1_READOUT.md`](CALIB_A_A1_READOUT.md). Per-turn
record in [`CORPUS_CALIBRATION_LOG.md`](CORPUS_CALIBRATION_LOG.md)
Checkpoint 4. **No memetic data and no ρ appear here** — M2 has not been run.

---

## 0. Summary — what this round achieved

**The round did the one thing it was run to do: it multiplied the
Tier-2-eligible population by 4.6× and spread it across the grid.**

| pooled, deduplicated on `instance_sha256` | after A1 | after B1 | change |
|---|---:|---:|---|
| instances profiled | 180 | 290 | +110 |
| certified (RC2 proved c\*) | 92 | 177 | +85 |
| **eligible: certified and 60 s < `solve_s` ≤ 600 s** | **10** | **46** | **×4.6** |
| distinct cells holding an eligible instance | 6 | 21 | ×3.5 |
| (n, k) rows holding an eligible instance | 5 of 9 | 8 of 9 | +3 |
| largest share from a single cell | 3/10 (30 %) | 4/46 (9 %) | ×0.3 |
| eligible under `include_solved_t3` (60 s–cap) | 12 | 54 | ×4.5 |
| eligible under the ≥ 30 s sensitivity (not adopted) | 17 | 70 | ×4.1 |

**Plan §7's stop condition is met.** It asked for "≥ 40 eligible across ≥ 8
cells, spread over the 60–600 s range rather than piled at one end": the
result is **46 across 21 cells**, median 159 s, quartiles 111 / 240 s, no
cell contributing more than 4. The named consequence is therefore the first
branch — **stop refining, proceed to M2** — with one documented exception in
§6 below.

**The run was clean and cheap.** 110/110 tasks returned a row, **0 failed**,
85 completed / 25 censored. PySAT **1.9.dev3** and python 3.11.15 on all 110
tasks — identical to A1, so plan §6's pooling condition holds and calib_a ∪
calib_b is a legitimate pool. Actual cost **10.0 CPU-h against a 29.3 CPU-h
worst-case budget (34 %)**. Zero negative-`solve_s` rows (Checkpoint 3
finding 1's detector stayed silent on the cluster, as on A1's 180).

**The placement method was validated on c\* and refuted on time.** Predicted
c\* landed inside the observed completed range in **16 of 17** exploratory
cells — the per-row linear `dc*/dm` model is sound. Predicted `solve_s` was
within 3× in only **12 of 17**, with a median ratio of 0.61× and misses as
large as 30× (see §3). **c\* is predictable; the time to prove it is not.**

**The one structural finding this round produced** (§5): a row's ability to
yield eligible instances is governed by its slope `d log10(solve_s)/dc*`, not
by where α is placed. Rows at ≤ 0.7 dec/c\* yield freely; the 3-SAT n = 150
row at 1.39 dec/c\* yielded **nothing at any of four α values**, because
consecutive integer c\* straddle the window (c\* = 2 → 15 s, c\* = 3 → 772 s).
That is a discreteness barrier, not a placement error, and no further α
refinement can fix it.

---

## 1. Batch integrity and comparability

| check | result |
|---|---|
| rows returned | 110 / 110 tasks, 0 missing, 0 superseded |
| §4.4 classes | 85 completed, 25 censored at cap, **0 failed** |
| `pysat_version` | `1.9.dev3` × 110 (uniform; **identical to A1**) |
| `python` | 3.11.15 × 110 |
| hosts | 18 distinct (A1 used 29; 11 hosts shared) |
| negative `solve_s` on completed rows | 0 |
| sha256 collisions against calib_a | 0 (290 rows, 290 distinct) |
| instance ↔ manifest line mismatches | 0 |

**The Checkpoint 2 PySAT question does not block pooling.** Plan §6 made
comparability conditional on the env being *recorded* rather than assumed, and
the recorded env is uniform and equal to A1's. So calib_a and calib_b are
pooled here. This does **not** close the open decision (freeze 1.9.dev3
vs. upgrade to 1.9.dev15 and re-run A1 + B1 together) — it only confirms that
the option was kept open, as intended.

The cross-host timing caveat from A1 still applies and is now slightly
smaller: 18 hosts instead of 29, 11 of them shared with A1. Single runs, no
repetitions — every `solve_s` here carries node-to-node variance.

**Cost.** Sum of `solve_s` over the 110 tasks is **10.0 CPU-h** against the
29.3 CPU-h worst case. The budget was conservative because it charged every
task the full cap; only 25 tasks actually reached it.

---

## 2. Per-cell table, pooled calib_a ∪ calib_b

`certified` = seeds with `profile.completed == true`. `solve_s` over completed
seeds only. `LB cens` = `cost_lower_bound` recovered from the progress file on
censored seeds. `elig` = seeds with 60 s < `solve_s` ≤ 600 s. Batch column:
`a` = calib_a seeds 1–5, `b` = calib_b, `a+b` = a reinforcement cell now
holding 10 seeds.

**Cell sizes are unequal by design** (plan §4b): the five reinforcement cells
hold 10 seeds, every other cell holds 5.

| k | n | α | batch | certified | solve_s min / med / max | c\* | LB cens | elig |
|---|---:|---:|:---:|:---:|---|:---:|:---:|---:|
| 2 | 100 | 2 | a | 5/5 | 0.003 / 0.005 / 0.007 | 1–5 | — | 0 |
| 2 | 100 | 3 | a | 5/5 | 0.021 / 0.255 / 0.773 | 12–16 | — | 0 |
| 2 | 100 | 4 | a | 5/5 | 3.09 / 8.06 / 174 | 24–31 | — | 1 |
| 2 | 100 | **4.5** | b | 3/5 | 16.3 / 66.6 / 126 | 30–35 | 36–37 | **2** |
| 2 | 100 | **5.0** | b | 2/5 | 31.1 / 57.6 / 84.0 | 35 | 39–43 | **1** |
| 2 | 100 | 6 | a | 1/5 | 753 / 753 / 753 | 50 | 49–54 | 0 |
| 2 | 150 | 2 | a | 5/5 | 0.007 / 0.009 / 0.021 | 6–7 | — | 0 |
| 2 | 150 | 3 | **a+b** | **9/10** | 1.77 / 14.1 / 65.1 | 18–24 | 28 | 1 |
| 2 | 150 | **3.15** | b | 4/5 | 1.03 / 12.7 / 301 | 20–26 | 29 | **1** |
| 2 | 150 | **3.30** | b | 4/5 | 2.76 / 102 / 227 | 25–28 | 31 | **2** |
| 2 | 150 | 4 | a | 0/5 | — | — | 35–40 | 0 |
| 2 | 150 | 6 | a | 0/5 | — | — | 55–66 | 0 |
| 2 | 250 | 2 | a | 5/5 | 0.028 / 0.181 / 2.61 | 8–14 | — | 0 |
| 2 | 250 | **2.35** | b | 4/5 | 0.235 / 37.2 / 610 | 14–22 | 23 | **1** |
| 2 | 250 | **2.50** | b | 3/5 | 4.88 / 9.47 / 28.6 | 17–21 | 24–25 | **0** |
| 2 | 250 | 3 | a | 0/5 | — | — | 29–33 | 0 |
| 2 | 250 | 4 | a | 0/5 | — | — | 44–49 | 0 |
| 2 | 250 | 6 | a | 0/5 | — | — | 70–79 | 0 |
| 2 | 400 | 2 | **a+b** | **10/10** | 1.12 / 18.1 / 413 | 12–20 | — | **3** |
| 2 | 400 | **2.15** | b | 5/5 | 5.79 / 148 / 381 | 16–21 | — | **4** |
| 2 | 400 | **2.30** | b | 3/5 | 53.5 / 145 / 367 | 20–23 | 25 | **2** |
| 2 | 400 | 3 | a | 0/5 | — | — | 32–39 | 0 |
| 2 | 400 | 4 | a | 0/5 | — | — | 52–57 | 0 |
| 2 | 400 | 6 | a | 0/5 | — | — | 89–95 | 0 |
| 3 | 50 | 4.26 | a | 5/5 | 0.005 / 0.008 / 0.018 | 0–1 | — | 0 |
| 3 | 50 | 5 | a | 5/5 | 0.009 / 0.014 / 0.065 | 1–2 | — | 0 |
| 3 | 50 | 6 | a | 5/5 | 0.040 / 0.340 / 4.53 | 3–6 | — | 0 |
| 3 | 50 | 8 | **a+b** | **10/10** | 9.86 / 70.9 / 649 | 8–11 | — | **4** |
| 3 | 50 | **8.5** | b | 4/5 | 45.1 / 483 / 627 | 9–12 | 12 | **1** |
| 3 | 50 | **9.0** | b | 2/5 | 152 / 500 / 847 | 11–13 | 13–14 | **1** |
| 3 | 70 | 4.26 | a | 5/5 | 0.003 / 0.003 / 0.009 | 0–1 | — | 0 |
| 3 | 70 | 5 | a | 5/5 | 0.010 / 0.088 / 8.09 | 1–4 | — | 0 |
| 3 | 70 | 6 | **a+b** | **10/10** | 5.34 / 44.1 / 367 | 4–7 | — | **4** |
| 3 | 70 | **6.2** | b | 5/5 | 13.4 / 153 / 291 | 6–7 | — | **3** |
| 3 | 70 | **6.5** | b | 4/5 | 146 / 183 / 436 | 7–8 | 7 | **4** |
| 3 | 70 | 8 | a | 0/5 | — | — | 9 | 0 |
| 3 | 100 | 4.26 | a | 5/5 | 0.003 / 0.007 / 0.129 | 0–1 | — | 0 |
| 3 | 100 | 5 | a | 5/5 | 0.628 / 5.64 / 93.0 | 2–4 | — | 1 |
| 3 | 100 | **5.2** | b | 5/5 | 2.54 / 46.8 / 213 | 3–5 | — | **2** |
| 3 | 100 | **5.5** | b | 3/5 | 62.0 / 157 / 174 | 4–5 | 5 | **3** |
| 3 | 100 | 6 | a | 0/5 | — | — | 5–6 | 0 |
| 3 | 100 | 8 | a | 0/5 | — | — | 7–8 | 0 |
| 3 | 150 | 4.26 | a | 5/5 | 0.014 / 0.040 / 2.00 | 0–1 | — | 0 |
| 3 | 150 | **4.6** | b | 4/5 | 0.180 / 0.316 / 1.08 | 0–1 | 3 | **0** |
| 3 | 150 | **4.8** | b | 3/5 | 0.046 / 1.86 / 34.9 | 0–2 | 3–4 | **0** |
| 3 | 150 | 5 | a | 3/5 | 2.76 / 14.9 / 772 | 1–3 | 3–4 | 0 |
| 3 | 150 | 6 | a | 0/5 | — | — | 4 | 0 |
| 3 | 150 | 8 | a | 0/5 | — | — | 5–6 | 0 |
| 3 | 250 | 4.26 | **a+b** | **9/10** | 0.482 / 50.8 / 388 | 0–1 | 1 | **3** |
| 3 | 250 | **4.35** | b | 2/5 | 103 / 214 / 324 | 1 | 1–2 | **2** |
| 3 | 250 | 5 | a | 0/5 | — | — | 2 | 0 |
| 3 | 250 | 6 | a | 0/5 | — | — | 3 | 0 |
| 3 | 250 | 8 | a | 0/5 | — | — | 4 | 0 |

53 distinct (k, n, α) cells; 58 batch-cells in `tier2_cells.csv`, which counts
the five reinforcement cells once per batch.

---

## 3. Did the placement method work?

The plan (§3) placed each exploratory α by fitting two per-row slopes from A1
— `dc*/dm` and `d log10(solve_s)/dc*` — and inverting them for the window.
Both halves can now be scored against the measurement.

### 3a. Exploratory cells, predicted vs observed

`HIT` = ≥ 3/5 certified **and** ≥ 2 eligible; `partial` = ≥ 1 eligible;
`MISS` = 0 eligible.

| cell | pred c\* | obs c\* | pred t | obs med t | ratio | certified | elig | verdict |
|---|---:|:---:|---:|---:|---:|:---:|---:|---|
| 2-SAT n = 100 α = 4.5 | 33 | 30–35 | 40 s | 66.5 s | 1.66× | 3/5 | 2 | **HIT** |
| 2-SAT n = 100 α = 5.0 | 39 | 35 | 150 s | 57.6 s | 0.38× | 2/5 | 1 | partial |
| 2-SAT n = 150 α = 3.15 | 24 | 20–26 | 90 s | 12.7 s | 0.14× | 4/5 | 1 | partial |
| 2-SAT n = 150 α = 3.30 | 26 | 25–28 | 300 s | 102 s | 0.34× | 4/5 | 2 | **HIT** |
| 2-SAT n = 250 α = 2.35 | 18 | 14–22 | 60 s | 37.2 s | 0.62× | 4/5 | 1 | partial |
| 2-SAT n = 250 α = 2.50 | 21 | 17–21 | 300 s | 9.5 s | 0.03× | 3/5 | 0 | **MISS** |
| 2-SAT n = 400 α = 2.15 | 18 | 16–21 | 60 s | 148 s | 2.46× | 5/5 | 4 | **HIT** |
| 2-SAT n = 400 α = 2.30 | 21 | 20–23 | 350 s | 145 s | 0.41× | 3/5 | 2 | **HIT** |
| 3-SAT n = 50 α = 8.5 | 11 | 9–12 | 150 s | 483 s | 3.22× | 4/5 | 1 | partial |
| 3-SAT n = 50 α = 9.0 | 12.5 | 11–13 | 600 s | 500 s | 0.83× | 2/5 | 1 | partial |
| 3-SAT n = 70 α = 6.2 | 6.6 | 6–7 | 100 s | 153 s | 1.53× | 5/5 | 3 | **HIT** |
| 3-SAT n = 70 α = 6.5 | 7.7 | 7–8 | 300 s | 183 s | 0.61× | 4/5 | 4 | **HIT** |
| 3-SAT n = 100 α = 5.2 | 3.8 | 3–5 | 30 s | 46.8 s | 1.56× | 5/5 | 2 | **HIT** |
| 3-SAT n = 100 α = 5.5 | 4.9 | 4–5 | 400 s | 157 s | 0.39× | 3/5 | 3 | **HIT** |
| 3-SAT n = 150 α = 4.6 | 1.1 | 0–1 | 5 s | 0.3 s | 0.06× | 4/5 | 0 | **MISS** |
| 3-SAT n = 150 α = 4.8 | 1.7 | 0–2 | 60 s | 1.9 s | 0.03× | 3/5 | 0 | **MISS** |
| 3-SAT n = 250 α = 4.35 | 1 | 1 | 200 s | 214 s | 1.07× | 2/5 | 2 | partial |

**14 of 17 exploratory cells produced at least one eligible instance; 8 are
clean hits; 3 missed.**

**The c\* model is validated: 16 of 17 predictions landed inside the observed
completed c\* range** (the exception, 2-SAT n = 100 α = 5, predicted 39 against
an observed 35 — and its two censored seeds carry LB 39–43, so the prediction
was right about the cell and wrong only about which seeds would certify).
Linear `dc*/dm` fitted *within* a row is a good instrument, exactly as §3
argued and §3's caveat (i) restricted it to be.

**The time model is not validated.** Median ratio 0.61×, only 12 of 17 within
3×, and the sign of the error is not stable — 2-SAT n = 400 α = 2.15 came in
2.5× *slower* than predicted while 2-SAT n = 250 α = 2.50 came in 30× *faster*.
The practical consequence: predicting c\* from α is reliable, predicting proof
time from c\* is a per-row guess good to about an order of magnitude. This is
why the round placed two α per row rather than one, and that hedge is what
carried it.

### 3b. The three misses, and what each one says

- **2-SAT n = 250 α = 2.50 — the cell straddles the wall rather than sitting
  on it.** Three seeds certified at 4.9 / 9.5 / 28.6 s (c\* = 17, 19, 21) and
  two were censored at LB 24–25. Nothing in between. The neighbouring
  α = 2.35 cell has the same shape wider apart: c\* = 14, 15, 18, 22 at
  0.2 / 3.4 / 71 / 610 s. **The seed-to-seed c\* spread inside one cell
  (≈ 8 units) is larger than the width of the whole 60–600 s window in c\*
  (≈ 4 units) for this row**, so no α value can put a majority of a cell in
  the window. This row is intrinsically low-yield, not badly placed.
- **3-SAT n = 150 α = 4.6 and α = 4.8 — the row has no reachable window.**
  See §5. Checkpoint 3's smoke-run finding 2 predicted precisely this ("3-SAT
  n = 150 α = 4.6 may be the trivial edge") from five workstation rows at a
  60 s cap, and the cluster at cap 900 confirmed it. The decision recorded
  there — keep the cell, because trivial and censored outcomes locate the
  edges — was the right call: these two cells are what establish that the
  barrier is discreteness rather than placement.

### 3c. Reinforcement cells — the low-variance half delivered

Plan §4b predicted these "will not miss". They did not.

| cell | seeds 1–5 (A1) | seeds 6–10 (B1) | pooled | eligible pooled |
|---|---|---|---|---:|
| 2-SAT n = 150 α = 3 | 4/5, med 19.8 s | 5/5, med 14.1 s | **9/10**, med 14.1 s | 1 |
| 2-SAT n = 400 α = 2 | 5/5, med 17.5 s | 5/5, med 131 s | **10/10**, med 18.1 s | 3 |
| 3-SAT n = 50 α = 8 | 5/5, med 65.7 s | 5/5, med 213 s | **10/10**, med 70.9 s | 4 |
| 3-SAT n = 70 α = 6 | 5/5, med 53.3 s | 5/5, med 34.9 s | **10/10**, med 44.1 s | 4 |
| 3-SAT n = 250 α = 4.26 | 4/5, med 166 s | 5/5, med 33.0 s | **9/10**, med 50.8 s | 3 |

Every cell held or improved its certified fraction, all five still pass the
§5.3 cell rule at 10 seeds, and they contributed **15 of the 46** eligible
instances — the largest single block, from a quarter of the round's tasks.
Note the median movement between seed blocks (2-SAT n = 400: 17.5 s → 131 s;
3-SAT n = 250: 166 s → 33.0 s): with 5 seeds, a cell median is itself a
noisy statistic, which is an argument for reading the §5.3 median threshold
loosely at n = 5.

---

## 4. The eligible population

**46 instances, 21 cells, 8 of 9 (n, k) rows.** Full listing in
`results/calibration/tier2_eligible.csv`.

### 4a. Spread across the window

| band | 60–100 s | 100–200 s | 200–300 s | 300–450 s | 450–600 s |
|---|---:|---:|---:|---:|---:|
| instances | 10 | 19 | 8 | 9 | **0** |

min 62 s · Q1 111 s · median 159 s · Q3 240 s · max 436 s.

The distribution is centred, not piled at an end, which is what §7 asked for.
**The one gap is the top of the window: nothing between 450 and 600 s.** Eight
further instances sit *above* it, in 600–900 s (§4c). This is a consequence of
the cap: as `solve_s` approaches 900 s the chance of censoring rises, so the
450–600 s band is thinned by the same mechanism that fills the censored class.
It is a property of the measurement, not of the instances, and it is the main
reason the 600–900 s rescue is worth a decision (§6).

### 4b. Composition

| row | eligible | α cells | from A1 | from B1 | c\* range |
|---|---:|---:|---:|---:|:---:|
| 2-SAT n = 100 | 4 | 3 | 1 | 3 | 31–35 |
| 2-SAT n = 150 | 4 | 3 | 1 | 3 | 23–28 |
| 2-SAT n = 250 | 1 | 1 | 0 | 1 | 18 |
| 2-SAT n = 400 | 9 | 3 | 0 | 9 | 18–23 |
| 3-SAT n = 50 | 6 | 3 | 3 | 3 | 10–11 |
| 3-SAT n = 70 | 11 | 3 | 2 | 9 | 6–8 |
| 3-SAT n = 100 | 6 | 3 | 1 | 5 | 4–5 |
| 3-SAT n = 150 | **0** | — | 0 | 0 | — |
| 3-SAT n = 250 | 5 | 2 | 2 | 3 | 1 |
| **total** | **46** | **21** | **10** | **36** | |

**2-SAT contributes 18 (c\* 18–35, median 23); 3-SAT contributes 28
(c\* 1–11, median 7).** A1's prediction that the two families would occupy
different c\* decades is confirmed and now quantified on the selected
population — the ranges do not overlap at all. Any statement about the
Tier-2 corpus that mixes families mixes two disjoint c\* regimes.

**Concentration is no longer a problem.** The largest single-cell
contribution is 4 of 46 (9 %), against 3 of 10 (30 %) after A1. Two rows
remain thin: 2-SAT n = 250 with 1, and 3-SAT n = 150 with 0.

### 4c. The 600–900 s band (`include_solved_t3`)

Eight instances are certified above the 600 s ceiling and would be added by
`make_tier2_manifest.py`'s `include_solved_t3` rescue, taking 46 → 54:

| batch | cell | seed | solve_s | c\* |
|---|---|---:|---:|---:|
| calib_a | 2-SAT n = 100 α = 6 | 1 | 752.7 | 50 |
| calib_b | 2-SAT n = 250 α = 2.35 | 3 | 610.3 | 22 |
| calib_b | 3-SAT n = 50 α = 8 | 6 | 621.9 | 11 |
| calib_b | 3-SAT n = 50 α = 8 | 8 | 648.7 | 11 |
| calib_b | 3-SAT n = 50 α = 8.5 | 2 | 612.0 | 12 |
| calib_b | 3-SAT n = 50 α = 8.5 | 4 | 626.7 | 12 |
| calib_b | 3-SAT n = 50 α = 9.0 | 5 | 847.3 | 13 |
| calib_a | 3-SAT n = 150 α = 5 | 3 | 772.2 | 3 |

Note what this band would buy: the **only** eligible instance the 3-SAT
n = 150 row can produce (the 772 s seed), a second for 2-SAT n = 250, and
five that deepen rows already well served. Three of these are within 4 % of
the 600 s edge — the edge is a convention, and these instances are not
materially different from the 436 s instance that is inside it.

---

## 5. The structural finding: yield is set by the slope, not by α

Fitting `log10(solve_s)` on c\* by OLS over every pooled completed instance in
a row (sub-millisecond rows excluded) gives the cost of proving one more core:

| k | n | N | slope (dec/c\*) | time factor per +1 c\* | c\* values that fit the 1-decade window | **eligible** |
|---|---:|---:|---:|---:|---:|---:|
| 2 | 100 | 21 | 0.127 | 1.3× | ~7.9 | 4 |
| 2 | 150 | 22 | 0.192 | 1.6× | ~5.2 | 4 |
| 2 | 250 | 12 | 0.250 | 1.8× | ~4.0 | 1 |
| 2 | 400 | 18 | 0.240 | 1.7× | ~4.2 | 9 |
| 3 | 50 | 31 | 0.428 | 2.7× | ~2.3 | 6 |
| 3 | 70 | 29 | 0.689 | 4.9× | ~1.5 | 11 |
| 3 | 100 | 18 | 0.944 | 8.8× | ~1.1 | 6 |
| 3 | 150 | 15 | **1.389** | **24.5×** | **~0.7** | **0** |
| 3 | 250 | 11 | 2.318 | 208× | ~0.4 | 5 |

The 60–600 s window is one decade wide, so a row can hold roughly `1/slope`
consecutive integer c\* values. **Where that number drops below 1, no α
placement can put instances in the window** — the c\* ladder steps over it.
3-SAT n = 150 is the case in point:

| α | certified | solve_s (completed) | c\* | LB censored |
|---:|:---:|---|:---:|:---:|
| 4.26 | 5/5 | 0.01, 0.02, 0.04, 0.07, 2.0 | 0,0,0,0,1 | — |
| 4.6 | 4/5 | 0.18, 0.21, 0.42, 1.08 | 0,1,1,1 | 3 |
| 4.8 | 3/5 | 0.05, 1.86, 34.9 | 0,1,2 | 3, 4 |
| 5.0 | 3/5 | 2.76, 14.9, 772 | 1,2,3 | 3, 4 |
| 6.0 | 0/5 | — | — | 4,4,4,4,4 |

c\* = 2 proves in ~15 s; c\* = 3 proves in 772 s. **The window falls in the
gap between two integers.** Four α values were spent on this row across the
two batches and it has produced zero eligible instances; a fifth would not
change that. The levers that could are (i) changing n, which moves the slope
(plan §4c already names 3-SAT n ≈ 180–200 as the strongest calib_c
candidate — this row is the reason), or (ii) accepting the 600–900 s band,
which captures its single 772 s seed.

**The 3-SAT n = 250 row is the informative exception.** Its slope is the
steepest in the grid (2.32), yet it yielded 5. The reason is a second
mechanism: at fixed c\* = 1, eight pooled instances span 33 s to 388 s — a
12× spread with no change in c\* at all. Near α = 4.26 the cost is in *finding
the proof*, not in the number of cores.

| row, fixed c\* | N | solve_s range | spread | in window |
|---|---:|---|---:|---:|
| 3-SAT n = 70, c\* = 7 | 8 | 146 – 367 s | 3× | **8 of 8** |
| 3-SAT n = 250, c\* = 1 | 8 | 33 – 388 s | 12× | 5 of 8 |
| 3-SAT n = 100, c\* = 4 | 4 | 47 – 211 s | 5× | 3 of 4 |
| 3-SAT n = 50, c\* = 11 | 6 | 76 – 649 s | 9× | 4 of 6 |
| 2-SAT n = 150, c\* = 23 | 3 | 1.5 – 65 s | 43× | 1 of 3 |
| 3-SAT n = 150, c\* = 1 | 6 | 0.18 – 2.76 s | 15× | **0 of 6** |

So two mechanisms produce eligibility, and a row needs one of them: a **shallow
c\* ladder** that lands a step inside the window (3-SAT n = 70 at c\* = 7 is
the ideal — 8 for 8), or **wide within-c\* variance** that scatters instances
across it (3-SAT n = 250 at c\* = 1). 3-SAT n = 150 has neither: its ladder
steps over the window and its variance at the relevant c\* is confined below
3 s.

**This is a result about the selection procedure, not about Max-k-SAT.** It
says where a fixed-cap, core-guided oracle can produce certified non-trivial
instances, under this stack. It does not say anything about which instances
are hard for a local-search or memetic solver — H2 is untested until M2, and
nothing in this round was chosen with the memetic arm in view.

---

## 6. Against the §5.3 cell rule, and what it now selects

The proposed rule is certified fraction ≥ 4/5 (read as ≥ 80 % for the 10-seed
cells) **and** median `solve_s` ≥ 10 s. Applied to the pool, **18 batch-cells
pass — 5 from calib_a, 13 from calib_b — which is 13 distinct (k, n, α)
cells**, up from 5 after A1:

| cell | certified | median solve_s | eligible in cell |
|---|:---:|---:|---:|
| 2-SAT n = 150 α = 3 | 9/10 | 14.1 s | 1 |
| 2-SAT n = 150 α = 3.15 | 4/5 | 12.7 s | 1 |
| 2-SAT n = 150 α = 3.30 | 4/5 | 102 s | 2 |
| 2-SAT n = 250 α = 2.35 | 4/5 | 37.2 s | 1 |
| 2-SAT n = 400 α = 2 | 10/10 | 18.1 s | 3 |
| 2-SAT n = 400 α = 2.15 | 5/5 | 148 s | 4 |
| 3-SAT n = 50 α = 8 | 10/10 | 70.9 s | 4 |
| 3-SAT n = 50 α = 8.5 | 4/5 | 483 s | 1 |
| 3-SAT n = 70 α = 6 | 10/10 | 44.1 s | 4 |
| 3-SAT n = 70 α = 6.2 | 5/5 | 153 s | 3 |
| 3-SAT n = 70 α = 6.5 | 4/5 | 183 s | 4 |
| 3-SAT n = 100 α = 5.2 | 5/5 | 46.8 s | 2 |
| 3-SAT n = 250 α = 4.26 | 9/10 | 50.8 s | 3 |

**Cell rule and instance eligibility still disagree, and the plan was right to
keep them apart.** 33 of the 46 eligible instances sit in passing cells;
**13 do not**, including all 4 from 2-SAT n = 100 and 3 of the 6 from 3-SAT
n = 100 α = 5.5 (3/5 certified — fails the fraction by one seed while
producing three eligible instances). Conversely 2-SAT n = 150 α = 3 passes
the cell rule at 9/10 and yields 1. Selecting the corpus by cell and then
filtering by instance loses a quarter of the available eligible instances;
that is the trade-off the M4 decision has to make explicitly, and §5.3 says it
may be moved with the reason recorded.

**No threshold was edited in this round.** `T1_MAX_S = 60`,
`T2A_MAX_S = 300`, `T2B_MAX_S = 600` are untouched.

---

## 7. What this decides, and what it leaves open

### Decided by the numbers

**Plan §7 branch 1 fires: stop refining α, proceed to M2.** 46 ≥ 40 and
21 ≥ 8, spread is centred, concentration is 9 %. A calib_c round of α
refinement is **not** warranted — §5 shows the remaining thin rows are thin
for structural reasons that α cannot address.

**calib_a and calib_b pool.** Uniform 1.9.dev3, 0 sha256 collisions, the
condition plan §6 set in advance.

**The placement method is worth reusing for c\*, not for time.** Fit
`dc*/dm` within a row, place two α per row, expect the time to be right
within an order of magnitude.

### Open, and now decidable on evidence

1. **The 30 s floor.** Carried as a sensitivity since Checkpoint 3 and still
   not adopted. It would take the pool from 46 to 70. **The case for it is
   weaker than it was at A1** — at A1 it was 10 → 17 and the population was
   too small to work with; at 46 the established 60 s floor is no longer the
   binding constraint. Recommendation: **leave the floor at 60 s**, and
   record the sensitivity column rather than adopting it.
2. **The 600–900 s rescue (`include_solved_t3`).** 46 → 54. This one has a
   stronger case than the 30 s floor: it fills the empty 450–600 s shoulder
   (§4a), it is already implemented behaviour in `make_tier2_manifest.py`
   rather than a new threshold, and it is the only route to any 3-SAT n = 150
   instance. Recommendation: **adopt it, with the caveat that the 8 rescued
   instances are recorded as a labelled subset** so any result can be checked
   with and without them. **User decision.**
3. **What M2 runs on.** The certified pool is now 177 instances, which at
   3 seeds is 531 tasks and ≤ 133 CPU-h worst case — nearly double the M2
   estimate written when the certified set was 92. Three sizings:

   | M2 population | instances | tasks | worst-case CPU-h |
   |---|---:|---:|---:|
   | all certified (as M2 is currently specified) | 177 | 531 | 133 |
   | certified with `solve_s` ≥ 30 s | 70 | 210 | 52 |
   | eligible only (60–600 s) | 46 | 138 | 34 |

   91 of the 177 certified instances solve in under 10 s and 59 in under 1 s;
   A1 §5 already established that their RC2 ranking is timing noise. Running
   M2 on all 177 spends three quarters of its budget on instances that cannot
   enter Tier 2 and cannot carry a ρ. **Recommendation: M2 on the ≥ 30 s
   set (210 tasks, ≤ 52 CPU-h)** — it covers every eligible instance, keeps
   a 24-instance margin below the window for the exploratory ρ of §5.2 to
   have something to attenuate against, and costs less than the original
   estimate. **User decision; it changes M2's manifest builder.**
4. **PySAT 1.9.dev3 freeze vs. upgrade.** Unchanged and unresolved. B1 kept
   both options open at no cost; the price of upgrading is now re-running 290
   tasks instead of 180.
5. **Goals §5.4 vs. building Tier 2 from calibration batches.** Unchanged and
   now materially larger: §5.4 says the reported corpus is regenerated at
   fresh seeds 1001–1020 and calibration rows never enter a reported ρ. The
   46 (or 54) eligible instances found here are a calibration product. If
   §5.4 stands, this round's output is a *map of where to generate*, not the
   corpus itself — and §5 of this read-out is the map. **Decision for the
   log at M4.**

### Not in this read-out

No memetic data, no ρ, no CI, no yield CSV. Those are M2 and M3.

---

## 8. Standing constraints, checked against this round

- **Nothing was selected to produce a correlation.** α placement used only
  A1's measured (α, c\*, `solve_s`); no memetic data exists for these cells.
- **Timeouts are censored, not failures.** 25 censored rows carry
  `cost_lower_bound` as a lower bound; none is reported as an optimum and
  none enters the eligible set.
- **Every instance stays in the record**, including the 43 RC2-trivial and
  25 censored calib_b rows and the two zero-yield 3-SAT n = 150 cells — §5
  exists because they were kept.
- **RC2-easy does not imply memetic-easy.** Eligibility here means RC2
  certified an optimum in non-trivial time; it is not a claim about memetic
  difficulty.
- **Scope.** One bounded batch, no recursive search, no threshold edits, no
  solver or generator changes, no env upgrade.
- **Any ρ reported later describes this selected population** under this
  stack, this cap and these rules — not random Max-k-SAT.
