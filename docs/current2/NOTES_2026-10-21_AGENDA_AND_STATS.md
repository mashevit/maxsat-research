# Notes 2026-10-21: agenda for the next sessions, and the start of the statistics / ρ summary

> "for tommorow: add the instance you want, now commit and push, keep in
> some note to run the 2016 mse, even though it is hard for exact, also
> there is possibility for more bigger than 5mgbyte instances in 23/24 mse,
> keep somewhere in note, I also want you to remember to explain me what is
> the monkey patch engineering decision I have in code. I do want to already
> start summing up statistics and rho. maybe if there is a reason that under
> 30s rc2 is also easy for my memetic to sketch the result in general, and
> to think of some reason to keep it out of rho statistics, maybe because of
> milisecond unmeasurable noise stastical. write the notes in this prompt in
> some doc, and remember to update me on context next time i work" (user,
> 2026-10-21)

**Status:** notes and a first sketch; no new runs. Note N-2026-10-21-l.
**The next session opens with §6.**

## 1. Next on the cluster: lean code, native build, the per_polish batch

**Order** (`NEXT_SESSION_CONTEXT.md` r16): U30 and HMSE have run on
`0877898` and been read (`UNDER30_HARDMSE_RUN.md` §8). What remains:
1. upload the lean-table code (`7c5ecc8` or later) as a flat folder with
   an arrange script;
2. `sbatch build_native.sbatch`, then check for `BUILD_OK`;
3. the per_polish check batch.

**The per_polish batch:**
- **Arms:** `hard.moves.per_polish` {200, 10}.
- **Runs:** 3 seeds × 900 s, stop at the target.
- **Instances:** 24.
  - the 16 KS2 instances;
  - the 3 setcover rail instances (lean tables);
  - **5 added from the weak HMSE families** (the user: "add the instance
    you want"). Each is the instance whose median-run gap is closest to
    its family's median:

| pop_idx (HMSE) | year | family | instance | best-known | HMSE median run | gap |
|---|---|---|---|---:|---:|---:|
| h003 | 2023 | decision-tree | heart-cleveland …atleast_15 | 31 | 50 | +61 % |
| h047 | 2023 | logic-synthesis | normalized-test4.pi | 94 | 108 | +15 % |
| h011 | 2023 | inconsistency-measurement | im-forgetting-B-2-stb_625_161 | 79 | 84 | +6.3 % |
| h100 | 2024 | decision-tree | primary-tumor …atleast_31 | 108 | 157 | +45 % |
| h095 | 2024 | correlation-clustering | Rounded_CorrelationClustering_Prot… | 15,658,391 | 17,472,547 | +12 % |

- gen-hyper-tw's typical instance (b01, +40 %) is already one of the 16
  KS2 instances.
- **Size:** 24 × 2 × 3 = **144 tasks**; worst case 144 × 960 s = 38 CPU-h.
- **Decision rule (user):**
  - if 10 wins broadly, it becomes rule R5 of `auto_hparams` for hard
    instances;
  - if not, a rail-only rule: "lean tables → per_polish 10" ("if 10
    doesnt win do it rule like 3").
  - "Broadly" will be pre-registered in the batch doc before submission,
    as in KS2 (better/worse counts per instance).

## 2. To run later: MSE 2016 (all-soft), even though it is hard for exact solvers

**What exists** (`MSE_EVALMAXSAT_3600.md` §2):
- **The full set:** `data/more_data/`, 856 files, `ms_random` and
  `ms_crafted`, unweighted, no hard clauses.
- **The sample:** `data/mse16/`, 104 files (5 per leaf directory).
- **Earlier runs:**
  - the 900 s RC2 screen was never run;
  - EvalMaxSAT has 12 rows, all timeouts;
  - an RC2 preview certified spinglass and dimacs-mod in ≤ 22 s, while
    bipartite maxcut was capped.

**Why run it:** it is the all-soft family where the strong solver is
strongest (1,686/1,686 soft runs at the optimum so far). Exact solvers
struggle there, so it is where the memetic can show something exact
solvers cannot.

**Open points:**
- **Targets:** check whether MSE 2016 publishes best-knowns per file.
  Without targets, run the full budget and report the cost reached.
- **Comparisons:** RC2 (and EvalMaxSAT) at 900 s for proofs and lower
  bounds, and the memetic for upper bounds.
- **Selection:** families, sample size, per-formula duplicate check (as
  O900).

## 3. To check: larger MSE 2023/2024 instances (over 5 MB)

- **What we have:** only the *small* tracks: MSE 2023 "uw-small" (75)
  and MSE 2024 "small" (91).
- **The gap:** the full evaluations also contain larger instances.
  **Check:** the MSE 2023/2024 benchmark pages and archives for files
  over 5 MB, their families, and whether best-knowns exist for them.
- **Before running them:**
  - **memory:** the lean tables cover long clauses (Σk(k−1) > 50M);
  - **other structures:** Glucose's learned clauses and the ks2 cores
    over 900 s are not yet audited (the RAM-audit item in
    `NEXT_SESSION_CONTEXT` r15);
  - **cluster memory:** set `--mem` per job by size. The user sets memory
    per job on the cluster, so no in-record field is needed.

## 4. To explain to the user: the "monkey patch" engineering decision in the code

Explain this at the start of the next session. What it most likely
refers to [verified: code]:

**(a) Static tables cached as attributes on the instance object** (the
main one, in production code). Expensive, run-invariant tables are built
once and attached to the WCNF object with `setattr(cnf, "_<name>", …)`:
- `sat/walksat_v2._CACHE_ATTR = "_walksat_v2_static"` (occurrence lists);
- `evo/impl_v2._XO_ATTR = "_crossover_v2_static"`;
- `sat/ls_v3._V3_ATTR = "_ls_v3_static"` (cvd / neighbour or lean
  tables);
- `sat/ls_v3._MODE_ATTR = "_ls_v3_nbrs_mode"`;
- `native/native.NativeCore._ATTR = "_native_core"` (the flattened C
  arrays).

Points to explain:
- **Why:** every polish call (thousands per run) would otherwise rebuild
  them. `setattr` gives a per-instance cache without changing every
  function signature.
- **The risks:**
  - hidden state;
  - stale caches, guarded by `m` = clause count, by the requested mode,
    and by `NativeCore.x is v3_static(wcnf)`;
  - objects that refuse attributes, which fall back to no cache;
  - memory that lives as long as the WCNF object.
- **The alternative:** an explicit context object passed down, which is
  cleaner but a larger refactor.

**(b) pytest `monkeypatch` in tests:**
- `monkeypatch.setattr(lsv3, "NBRS_MAX", …)` forces lean mode on small
  instances;
- fake clocks (`tick_clock`), `chdir` and environment variables (the
  native build directory).

**(c) This session's mutation check:** a deliberately broken
`cc_touch_lean` was swapped in at module level, to show the tests catch
it. It was not committed (`tmp/`).

## 5. Statistics and ρ: first sketch [verified: records; inference marked]

**ρ, as defined** (`docs/M2_FULL_POOL_READOUT_AND_STATE.md` §1):
- Spearman ρ between RC2 proof time and memetic ERT, one point per
  instance.
- ERT = total effort over seeds, with failures charged their spend,
  divided by the number of successes.
- **Pre-registered:**
  - instance bootstrap, BCa, B = 10,000;
  - partial ρ on [log n, α, log(1 + c\*)];
  - zero-success instances excluded in the primary analysis and top-tied
    in a sensitivity analysis;
  - **eligibility: RC2 time in (30, 900] s**;
  - calibration rows are exploratory; the final ρ needs fresh seeds
    1001–1020.

### 5.1 Data now available (strong solver, `impl: v3`, `hparams: auto`)

| batch | instances | RC2 / EvalMaxSAT proof | memetic result |
|---|---:|---|---|
| U30 | 319 soft | RC2 < 30 s | 957/957 runs at the optimum; TTT median 0.033 s, max 2.16 s |
| O900, soft part | 245 soft | RC2 [30, 900) s (243) or EvalMaxSAT | 729/729 + drmx 0/6; TTT median 0.05 s |
| O900 + KS2 + HMSE, hard | 141 MSE (17 proven) | EvalMaxSAT < 3600 s for 16, RC2 for 1 | 129/423 runs at target |

### 5.2 Sketch: under 30 s for RC2 is also easy for the memetic

- **Every U30 instance was solved in every run**, mostly within the
  first local-search call:
  - **83 %** of runs (797/957) reached the optimum with the first child;
    their effort is exactly one polish call (`total_flips` = 12,500);
  - **229/319 instances (72 %)** have all three seeds at that floor;
  - TTT: median 0.033 s, 99th percentile 0.54 s.
- **Statement for the paper (draft):** "Instances that RC2 certifies in
  under 30 s are uniformly easy for the memetic solver: 319/319 solved in
  all runs, 83 % of runs at the first local-search call."

### 5.3 Why U30 stays out of ρ [proposal]

1. **Pre-registration.** The eligibility window is RC2 time in
   (30, 900] s (`CORPUS_CALIBRATION_GOALS.md`, `GRID_POINTS_WINDOW_30_900.md`).
   U30 is outside it by definition. Adding it would be a protocol change
   made after seeing data.
2. **The memetic effort is at its measurement floor.**
   - 72 % of U30 instances have every seed at exactly one polish call.
     In flips (quantized at 12,500 per call) and in children, they are
     **tied**.
   - In seconds, a 5–50 ms TTT is the same order as fixed costs: the
     kernel screen, building the population, the first call's setup,
     timer and OS jitter. 11 runs even show cpu/wall < 0.9. The ranks
     there measure overhead noise, not search effort.
   - Spearman over mostly tied ranks carries little information and
     inflates the CI.
3. **The RC2 side is also floor-dominated.**
   - 149 of the 319 formulas certified in < 1 s;
   - below about a second, process start-up and parsing are a large share
     of the measured time.
4. **There is no variance in success** (100 %), so the
   success-rate version of ρ is undefined.

**Report U30 descriptively instead,** with the sentence in §5.2, as
evidence that the easy region is easy for both solvers.

### 5.4 Caveat: the same floor reaches into the window (O900) [inference]

- **O900's soft part, inside the (30, 900] window:** 54 % of runs end at
  the first call, and **84/245 instances** have all seeds at the floor.
- **With the strong solver, ρ in seconds or flips** would be dominated by
  ties in the window too. The M2 ρ (+0.05 to +0.10 pooled) was measured
  with the older v2 solver, where the effort varied more.
- **Options to decide:**
  1. **A finer effort measure:** flips counted to the first improving flip
     that reaches the target, inside the call. This needs a new record
     field; today the target is checked at call boundaries.
  2. **Harder instances for the memetic:**
     - the larger-n grid (calib_2sat_sc2);
     - MSE 2016 (§2);
     - larger MSE (§3).
  3. **Report** the strong solver as "trivial on the RC2 window" and run
     ρ on the v2 solver (as M2), or on a deliberately weakened
     configuration. This changes the research question, so it is the
     user's call.

### 5.5 Proposed next steps for the statistics (not started)

1. A per-instance table of all batches: RC2 / EvalMaxSAT time, c\* or
   best-known, n, m, α, family, and memetic ERT in seconds, flips and
   children, success.
2. The floor analysis: the share of instances at the first-call floor, by
   batch and family.
3. ρ (pooled and per family) on O900 soft with the pre-registered
   conventions, labelled exploratory, with the tie share reported next to
   each ρ.
4. The decision on option 1, 2 or 3 above.

## 7. User decisions and plans after §5.4 (2026-10-21, late)

> "note in some doc I would like to implement 1, and run evalmaxsat with 1
> hour array of 1000 jobs on 2016 and on the bigger 23/24 instances, I will
> compare rho of memetic inside under 900s , but i think indeed above 30s
> and eventually not implement the per flip resolution, and I might compare
> rho to Evalmaxsat under hour in the mse instances, which I think are from
> anytime track, but we will need to verify it, we have optimums for 24/23
> mse, we need to get them for the bigger instances as well, for 2016, I
> think there are no optimum, you might do research on it tomorrow," (user,
> 2026-10-21)

**7.1 ρ on the RC2 window: the primary plan.**
- The memetic ρ is computed inside the RC2 window, **above 30 s and under
  900 s**, as pre-registered. U30 stays out (§5.3).
- **Option 1 (the first-reach flip counter) is open.** The user would
  like to implement it, but may in the end not implement it ("eventually
  not implement the per flip resolution").
  - **To settle with the user before any code:** implement, defer, or
    drop.
  - **If dropped:** ρ is computed on the existing effort measures, and the
    tie share at the one-call floor (§5.4: 84/245 O900 soft instances) is
    reported next to each ρ.

**7.2 EvalMaxSAT, 1 hour, arrays of up to 1,000 jobs:**
- **(a) MSE 2016 (all-soft):** `data/more_data/`, 856 files, or a chosen
  subset.
- **(b) The bigger MSE 2023/2024 instances** (§3), once found and
  downloaded.
- **Settings:** 3600 s per job, as batch s1 (`MSE_EVALMAXSAT_3600.md`);
  driver `cluster_staging_maxsat/scripts/evalmaxsat_array.sbatch`.
- **Planning needs:**
  - the cluster memory per job for the large files;
  - the binary on the cluster
    (`~/cluster_staging_maxsat_evo/EvalMaxSAT/build/main/EvalMaxSAT_bin`);
  - the GPL-3.0 licence and citation (N-2026-10-21-a);
  - 856 × 1 h ≈ 856 CPU-h worst case for MSE 2016 alone.

**7.3 A second ρ: memetic vs EvalMaxSAT under one hour, on MSE instances
(possible).**
- **Exact side:** EvalMaxSAT's time to prove the optimum when it is under
  1 h.
- **Memetic side:** its effort to reach that optimum.
- **To verify:**
  - which MSE track our 2023/2024 files come from. The user thinks
    anytime; the MSE 2024 best-known table flags all 91 as anytime
    (`MSE_EVALMAXSAT_3600.md` §3), and MSE 2023 "uw-small" has no flags,
    so check it;
  - what "optimum" means per track. Anytime-track best-knowns are not
    proofs;
  - which instances EvalMaxSAT proves in under 1 h.

**7.4 Optima and best-knowns: research for the next session.**
- **MSE 2023/2024 small:** we have per-file best-known tables
  (`data/raw/mse_2024/bestknown_mse23.csv`, `bestknown_mse24.csv`). 17 of
  the 141 HMSE instances are proven by our own runs. Note the user's word
  "optimums": most are best-knowns, not proofs.
- **The bigger MSE 2023/2024 instances:** best-knowns or optima are needed
  (evaluation results tables, the anytime and exact tracks).
- **MSE 2016:** probably no published optima (the user thinks none).
  Research what the 2016 evaluation published (per-instance best costs?
  solver results?), and what later work (papers, MaxSAT-instance
  repositories) reports.
- **Sources** must be cited and verified; record them in RESEARCH_NOTES.

## 8. Proposal: ρ on MSE, memetic against EvalMaxSAT (2026-10-21, late) [verified data; proposal]

> "try to solve my problem for rho statistics: my anytime solver performs
> also on mse in much more instances than the evalmaxsat, although the
> evalmaxsat was run only on 60 instances ... compare rho on these, and
> whatever evalmaxsat solves within hour from mse 2016' to my memetic 900s.
> the implemention for the rail instances is not must for this rho ... tell
> me if there were some non trivial results from the satlib or our corpus
> broadening" (user, 2026-10-21)

### 8.1 On MSE the effort floor is gone (preview, existing data)

The instances EvalMaxSAT s1 proved in < 3600 s: 18, of which 16 have hard
clauses and 2 are drmx (soft).
- **Memetic ERT_s at 900 s, 3 seeds:** HMSE for the hard ones, O900 for
  drmx. It ranges from **8.8 s to 2,060 s** where it succeeds.
- **11/18 instances** have ≥ 1 memetic success, and 7 have none. No
  instance sits at a one-call floor.
- **Preview ρ** (Spearman; EvalMaxSAT time vs memetic ERT_s; exploratory,
  N tiny):
  - primary, successes only: N = 11, ρ = +0.23;
  - sensitivity, zero-success top-tied: N = 18, ρ = −0.06.
  - These show only that the method has variation on both axes. N is far
    too small for any claim.

### 8.2 Complementarity: proved by EvalMaxSAT in 1 h vs reached by the memetic in 900 s

On the 53 HMSE instances that EvalMaxSAT s1 also ran:

| | memetic reached the target (≥ 1/3) | memetic did not |
|---|---:|---:|
| **EvalMaxSAT proved (< 1 h)** | 11 | 5 |
| **EvalMaxSAT did not** | 12 | 25 |

- **Memetic 23/53 vs EvalMaxSAT 16/53:** about 1.4×, not 2×.
- **Not the same task:** "reached" means reaching the year's best-known,
  which is not a proof. "Proved" means optimal and certified.
- **Each finds instances the other misses:** 12 memetic-only, 5
  EvalMaxSAT-only. This is a second, separate result: an
  anytime-vs-exact complementarity table. It is not ρ.
- **The other 88 HMSE instances:** EvalMaxSAT never ran them. The memetic
  reached the target on 34 of them (57/141 overall).

### 8.3 Proposed ρ design on MSE (to pre-register before the new EvalMaxSAT runs)

**Data to collect:**
- **EvalMaxSAT 1 h, the MSE 2023/2024 small tracks:**
  - the 101 frame instances not in s1 (161 frame − 60), plus the 5 with
    best-known −1 if wanted;
  - one array, ≤ 101 CPU-h worst case;
  - expected proofs: about 30 % (s1 rate 18/60), so roughly 30 more and
    **N ≈ 45–50** in all.
- **EvalMaxSAT 1 h, MSE 2016:** 856 files, or a stratified subset.
  - Every instance it proves gets memetic runs, 3 seeds × 900 s, stop at
    the proven optimum.
- **The memetic on MSE 2023/2024:** HMSE already has it for all 141 hard
  instances, plus drmx in O900. No rerun is needed, except for the rail
  instances, which need the lean code. Exact solvers do not prove them, so
  they do not enter ρ (user).

**Definition:**
- **x:** EvalMaxSAT's proof time.
- **y:** the memetic ERT_s to the proven optimum (900 s budget; failures
  charged 900 s).
- **Unit:** one point per instance.

**Window (the analogue of RC2's):**
- EvalMaxSAT proof time in **(30, 3600] s**.
- Proofs in < 30 s are reported descriptively, for the same floor and
  start-up reasons as U30 (§5.3).
- Every s1 proof so far is ≥ 116 s.

**Conventions:** the pre-registered ones (§5):
- zero-success instances excluded in the primary analysis, top-tied in
  the sensitivity analysis;
- BCa bootstrap, B = 10,000.

**Additional, because of MSE's structure:**
- **Family clustering:** judgment-aggregation and
  inconsistency-measurement are large families. Report a
  family-stratified bootstrap, and ρ within the larger families.
- **Year:** MSE 2023 is unweighted, MSE 2024 weighted. Report ρ per year
  next to the pooled value.
- **The 2×2 table (§8.2)** is reported with ρ.

**Budget asymmetry:** 900 s for the memetic, 3600 s for EvalMaxSAT. Ranks
are unaffected, but the memetic's success rate is capped by its shorter
budget. State it.

**Open:**
- the track of our files (§7.3);
- best-knowns for the bigger files (§7.4);
- whether MSE 2016 has known optima (research next session).

### 8.4 Non-trivial results from SATLIB and the corpus broadening [verified: docs]

The pre-registered Q2 rule counts an instance as non-trivial for the
memetic if success < 3/3 or median TTT ≥ 45 s.

| set | solver | non-trivial (Q2) | source |
|---|---|---|---|
| calib_a/b (the corpus broadening, M2 full pool, 70 instances) | v2 `memetic_deeppolish` | **5** (0.5 s arm: #7, 9, 38, 39, 47) / **9** (3.5 s arm). The jointly non-trivial strip is narrow: 3-SAT n 250 α 4.26/4.35 and n 150 α 4.8; 2-SAT n 400 α 2.0–2.15 borderline | `docs/M2_FULL_POOL_READOUT_AND_STATE.md` |
| calib_2sat_sc2 (large-n Max-2-SAT, 6 eligible) | v2, both arms | **6/6** non-trivial; s253 unsolved even on its kernel (v2) | `CALIB_2SAT_SC.md` §13; `KERNEL_MEMETIC_RUN.md` §6 |
| SATLIB (95 RC2-eligible) | — | never run on the v2 memetic (RC2 only) | `SATLIB_BENCH_INTAKE.md` |
| everything soft with a proven optimum (O900 soft 243 + U30 319) | **v3 strong** | **0**: 1,686/1,686 runs at the optimum; max TTT 6.1 s (s253) in O900, 2.16 s in U30 | `ORACLE900_RUN.md` §7; `UNDER30_HARDMSE_RUN.md` §8 |
| MSE drmx-cryptogen (soft, weighted) | v3 | non-trivial (0/6) | O900 |
| MSE hard-clause (HMSE) | v3 | 84/141 never reached the target; many reached only after hundreds of seconds | `UNDER30_HARDMSE_RUN.md` §8 |

**[inference]** The broadening did find a non-trivial region, but only for
the v2 solver. The strong solver erased it on every soft instance with a
proven optimum, including the 6 calib_2sat_sc2 instances and s253. That is
why ρ with v3 has to move to MSE (§8.3), where both solvers do non-trivial
work. The v2 M2 ρ stays as the record for the weaker solver.

## 9. MSE 2016: what was ever run, and a prediction for an MSE-based ρ (2026-10-21, late)

> "first check if there were runs in this project for mse2016 for 3600s, and
> which runs were. also I think all exact solver runs we tried on mse2016
> failed, but state your prediction if we can find enough corpus broadening
> for rho from mse to find interesting result" (user, 2026-10-21)

### 9.1 Runs on MSE 2016 [verified: result files and docs]

**No 3600 s run of any solver has ever been made on MSE 2016.** What exists:

| solver | where | instances | cap | outcome |
|---|---|---|---|---|
| EvalMaxSAT | `results/oracle_more_data.jsonl` (12 rows) | 10 set-covering (scpclr10–13, scpcyc06–11), 1 Max-2-SAT (abrame-habet 120v s2v120c1200-1), scpclr10 again | 60 s (10), 120 s (1), 1800 s (1) | **all timeouts, no bound** |
| RC2 | workstation preview, 300 s (`docs/archive/CORPUS_MSE2016_ASSESSMENT.md` §3.3) | 13 of the 104-file sample | 300 s | bipartite maxcut 0.7 and 0.8: 10/10 capped; **certified:** dimacs-mod c-fat500-1 (0.006 s, c\* 2), p_hat300-1 (22.05 s, c\* 49), spinglass t3pm3-5555 (0.01 s, c\* 17) |
| RC2 + EvalMaxSAT | same doc | 3 instances run under both | — | agree on c\* (4, 17, 49) |
| RC2, 900 s cluster screen | sbatch archived in `scripts/archive/mse16/` | — | — | **never run** |
| memetic | — | — | — | **never run** on MSE 2016 |

- **Not all exact runs failed.** The crafted small max-cut ones (dimacs-mod,
  spinglass) certify in 0.006–22 s, in the < 30 s floor region.
- **The failures** are set-covering (EvalMaxSAT 60–1800 s), bipartite
  max-cut (RC2 300 s) and one random Max-2-SAT (EvalMaxSAT 120 s).

### 9.2 Prediction: can MSE give enough points for an interesting ρ? [inference]

**Where both solvers vary is the MSE 2023/2024 hard-clause instances, not
MSE 2016.**

**MSE 2023/2024 small tracks (161 in the frame):**
- **Proofs:** at the s1 rate (18/60, every proof ≥ 116 s, so all inside a
  (30, 3600] window), expect **about 40–55 proofs in 1 h**.
- **Memetic successes:** the memetic reached ≥ 1/3 on 11/18 of the proved
  ones, so expect **about 25–35 points in the primary (successes-only) ρ**
  and 40–55 in the sensitivity analysis.
- **The bigger 2023/2024 files** may add 5–20 proofs (lower proof rate,
  more memory). Speculative until the files and best-knowns are found
  (§7.4).

**MSE 2016 (856, all soft, mostly unweighted):**
- **The exact side** will split. The crafted small max-cut and spinglass
  instances are proved in seconds, below the floor. Set-covering,
  bipartite max-cut and the larger random instances will mostly time out.
  The (30, 3600] window may hold some tens of instances.
- **The memetic side** will mostly sit at the floor on the proved ones:
  soft, unweighted and small n, exactly the class where v3 went
  1,686/1,686, mostly at the first call.
- **So MSE 2016 likely adds points with exact-side variation but tied
  memetic effort**, which is the degenerate picture again. Its value is
  elsewhere: the memetic's costs on the unproved ones as anytime results.

**Precision:** Spearman SE ≈ √((1 + ρ²/2)/(N − 3)), so the 95 % CI half-width
is about ±0.37 at N = 30 and ±0.29 at N = 50.
- **Family clustering lowers the effective N:** judgment-aggregation and
  inconsistency-measurement make up 45 of the 141 HMSE instances.
- **Detectable:** |ρ| of about 0.4 or more.
- **Not possible:** a tight "near zero" (orthogonality) claim.

**Expected outcome:**
- **ρ:** a low or moderate pooled ρ with a wide CI (preview +0.23 at
  N = 11; −0.06 in the sensitivity analysis), reported as exploratory with
  per-year and per-family breakdowns.
- **The stronger result will be the complementarity itself:**
  - the 2×2 table (§8.2), where each solver reaches instances the other
    does not;
  - large per-instance mismatches: bcp, EvalMaxSAT 1,836 s vs memetic ERT
    11 s; scheduling, 2,036 s vs 54 s; lisbon-wedding 9-18, 116 s vs 0/3;
    gen-hyper-tw b01, 3,476 s vs 0/3.
  - That is the "complementary hardness" story, on real benchmark
    families rather than random ones, answering the range-restriction
    objection (`more_data/CORPUS_BROADENING_HANDOFF.md`).

**Recommendation:**
1. Run EvalMaxSAT 1 h on the 101 small-track instances not yet run first:
   about 101 CPU-h, and it decides N.
2. Run MSE 2016 as a stratified subset, not all 856, aimed at the window.
3. Pre-register the §8.3 ρ before step 1's results come in.

## 6. Context for the next session (read first)

- **Committed:** `7c5ecc8` (lean tables), then this commit (U30/HMSE
  results and readout, these notes).
- **Cluster state:**
  - the tree is at `0877898` plus the U30/HMSE results;
  - the lean code is NOT uploaded;
  - the `.so` is the old build.
- **Next actions:**
  1. §4: explain the monkey patch decision;
  2. §1: build the per_polish manifest (144 tasks) and the flat upload
     with the lean code, plus its arrange script;
  3. the user uploads and arranges, runs `build_native.sbatch`, then
     submits;
  4. §5.5: start the statistics table and the floor analysis;
  5. §7.4: research optima and best-knowns for the bigger MSE 2023/2024
     files and for MSE 2016, plus which MSE track our files come from;
     then plan the EvalMaxSAT 1 h arrays (§7.2).
  6. §7.1: settle option 1 (implement, defer or drop) before any code.
  7. §8.3: pre-register the MSE ρ design with the user, then the EvalMaxSAT
     1 h array on the 101 small-track instances not yet run (and MSE 2016).
