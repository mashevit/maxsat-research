# Research notes — the single entry point

**Purpose.** Every research note we collect goes here, or is indexed here.
These are findings, caveats, quotations, rationales for scope decisions,
and claims we intend to make or avoid. Before writing up results, or before
deciding scope, start here.

**Created:** 2026-10-07. **Maintained:** append-only. Newest entries are at
the top of §2.

**How to add a note.**
1. Add an entry to §2 with an id `N-YYYY-MM-DD-x`, a one-line title and a
   status label (below).
2. Write the note itself. Quote user-supplied or external text verbatim, in
   a block quote, with its source.
3. Say where the evidence lives (document §, results file, script).
4. If the note is long, put it in its own `docs/current/RESEARCH_NOTES_<TOPIC>.md`
   and index it in §1. Keep a short entry in §2.

Never edit an old entry's claim in place. Add a dated correction under it.

**Status labels** (as in the topic notes):
- **[verified]**: read off rows or code;
- **[inference]**: follows from verified facts by a stated argument;
- **[extrapolation]**: assumes a trend continues;
- **[quote]**: external or user-supplied text, recorded as given;
- **[decision]**: a scope or design decision and its reason.

---

## 1. Topic notes and documents that carry research content

| topic | document | what it establishes |
|---|---|---|
| Restriction of range (why the corpus is being broadened) | `more_data/CORPUS_BROADENING_HANDOFF.md` §1–§2 (repo root) | The editorial objection: 26 near-identical uuf250 instances, 24 with c\* = 1, cannot support an orthogonality claim. The four axes are clause length, weightedness, c\* and origin. Which results survive. |
| Core-guided vs branch-and-bound, benchmark design | `docs/maxsat-benchmark-design-notes.md` | One UNSAT proof per unit of cost (OLL / RC2), and what that implies for instance design. Literature vs definition vs our measurements are kept apart. |
| Which optima RC2 can certify for random Max-3-SAT at n ≥ 250 | [`RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`](RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md) | C1–C4: at n ≥ 250 the eligible instances have c\* = 1; c\* = 2 is at or past 900 s; raising density does not help. |
| RC2 grid points under the (30, 900] s window | [`GRID_POINTS_WINDOW_30_900.md`](GRID_POINTS_WINDOW_30_900.md) | Grid points per (k, n, c\*); window capacity per row; the n = 200 gap. |
| RC2 time vs c\* slope | `docs/CALIB_B_B1_READOUT.md` §5, §7 | A row's yield is set by d log10(t)/dc\*. At n = 250 it is 2.32 decades per unit c\*. |
| Hard-clause instances: why they are excluded, and the exceptions | [`CORPUS_FREEZE_PREP.md`](CORPUS_FREEZE_PREP.md) §8 | Mixed-sign hard clauses are excluded for this solver: crossover and polish do not preserve feasibility. Conflict-clause families (MIS / Max-Clique) are reopened as an option. See also N-2026-10-07-a. |
| Corpus family scope | `docs/CORPUS_FAMILY_SCOPE_NOTE.md` | MaxCut is in; Max-Clique and set covering are out (partly revised by `CORPUS_FREEZE_PREP.md` §8.5). The torus stratum gap. |
| Memetic vs multistart on uuf | `docs/UUF_THREE_ARM_ABLATION_READOUT.md` | memetic 118/130, uniform multistart 124/130, JW multistart 127/130 on the 26 uuf instances. |
| M2 full pool: solver mechanics, ρ, threats to validity | `docs/M2_FULL_POOL_READOUT_AND_STATE.md` | Why 3-SAT and 2-SAT differ; the RC2 time decomposition; memetic reliability. |
| SATLIB benchmark families: intake, parser pitfalls, c\* expectations, citation | [`SATLIB_BENCH_INTAKE.md`](SATLIB_BENCH_INTAKE.md) | 263 unsat / 16 sat; 209 originals misread by PySAT; what these families can and cannot add. See N-2026-10-07-b…e (e is the required SATLIB citation). RC2 results: §8, N-2026-10-08-a (95 eligible). |
| RC2 re-run at cap 3600 s, with predictions recorded in advance | [`RC2_CAP3600_RERUN.md`](RC2_CAP3600_RERUN.md) | 148 censored instances (excluding mse16/raw/more_data); 9 groups by sibling evidence, each with a prediction; comparison script. See N-2026-10-08-b. |
| Random k-SAT generation: with vs without replacement; the `ksat_distinct` mode | [`RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md`](RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md) | The existing `weighted_ksat` samples clauses with replacement, so calib_a/b/c contain duplicate clauses. The new mode gives exactly m distinct weight-1 clauses by rejection sampling. Algorithm, seed behaviour, format, validation, and an n = 32000 benchmark. See N-2026-10-08-c. |
| Large-n, slightly supercritical random Max-2-SAT (`calib_2sat_sc`) | [`CALIB_2SAT_SC.md`](CALIB_2SAT_SC.md) | The model (BBCKW F_{n,m}, distinct clauses), the near-threshold theory used only as a covariate (n·ε³ = λ³), the measurement conventions (wall-clock 900 s cap, SIGALRM delay, watchdog), pre-registered cell rules, budget and commands. See N-2026-10-08-d…f. |
| Memetic solver `impl: v2` — why, what, how checked | [`MEMETIC_IMPL_V2.md`](MEMETIC_IMPL_V2.md) | v1's WalkSAT polish is O(m) per flip: measured at n 2000–32 000 (about 300 flips per 3.5 s call at n = 32 000; 120 s left it 2000+ above c\*). v2 makes v1's exact decisions with incremental bookkeeping (57 equivalence tests), 50–1800× faster per flip; v1 stays the default. Seconds are comparable only within one `impl`. N-2026-10-08-h/i. |

## 2. Dated notes (newest first)

### N-2026-10-08-i — Memetic `impl: v2`: incremental WalkSAT with v1's exact decisions; seconds comparable only within one impl [decision + verified]

- **The user's decision:** "go with option 2, make walksat incremental keep
  possibility to use older version, you can make in new version more
  optimizations".
- **What v2 is** (`CALIB_2SAT_SC.md` §10c):
  - a top-level config key `impl: v2`; an absent key means v1, the historical
    code;
  - the frozen files (`sat/walksat.py`, `sat/state.py`, `evo/operators.py`)
    are unchanged.
  - v2 = an incremental polish (O(occ) per flip), a crossover with cached
    statics, and no no-op advisor round trip.
- **Equivalence [verified].** v2 reproduces v1's trajectory exactly under a
  flip or iteration budget: polish, crossover and whole EA runs, including
  hard+soft (57 tests).
- **Speed [verified].**
  - Polish: 50× faster at m = 2300 and about 1800× at m = 36 800.
  - Same arm, 120 s: optimum at n = 2000 in 1.2 s and at n = 8000 in 22 s
    (c\* 3 and 11; v1 after 120 s: best 5 and 67). At n = 32 000, best 14
    and 25 against c\* 5 and 13 (v1: 2250 and 2563).
- **Comparability [decision].**
  - Seconds-based memetic effort is comparable only within one `impl`.
  - Existing results are v1 and stay v1.
  - Shards record `memetic_impl` (schema 3).
  - The large-n memetic assessment uses
    `memetic_deeppolish_p40_ls3p5_v2.yaml`.

### N-2026-10-08-h — The memetic solver's WalkSAT polish costs O(m) per flip: at n ≥ 8000 the established arm barely searches [verified + decision pending]

- **Smoke run** (`CALIB_2SAT_SC.md` §10b): primary arm p40_ls3p5, 120 s,
  stop-at-oracle, on four large-n instances with RC2-proven c\*.
  - Every run did 1 generation.
  - Best costs were 5 (c\* 3, n 2000), 67 (c\* 11, n 8000), 2250 (c\* 5,
    n 32 000) and 2563 (c\* 13, n 32 000).
  - Flips per 3.5 s call: about 4800 at m = 2300, about 1120 at m = 9600,
    and about 290 at m ≈ 36 000.
- **Cause** (code): `walksat_polish` calls `state.unsat_hard_ids()` and
  `unsat_soft_indices()` on every flip, and each is a full scan of the m
  clauses (`src/sat/state.py:298/301/332`).
- **Implication [inference].** At n ≥ 8000, a memetic failure under the
  established configuration measures the implementation, not the instance.
  The memetic half of the selection objectives cannot be assessed there until
  this is decided.
- **Options** (§10b; the user decides):
  1. memetic only where it works;
  2. incremental unsat bookkeeping — a new solver version, so earlier results
     are comparable only if repeated;
  3. a larger per-call allowance, which does not remove the O(m) factor.
- **RC2 batch:** unaffected.

**Also on 2026-10-08 — the login-node rule.** The cluster terminates Python and
other heavy work on the login node (user's report, quoted in
`CALIB_2SAT_SC.md` §9). Changes made:
- the preflight's login part is now shell only, and its Python checks run in
  a compute-node verify job;
- `RESUME=1` in `submit_rc2_profile.sh` and `submit_m2_memetic.sh` no longer
  calls Python. Explicit ids go in `IDS=`, computed on the workstation.

### N-2026-10-08-g — Workstation RC2 check on the `calib_2sat_sc` cells (non-batch seeds): c\* > 2 occurs at n ≥ 8000; runtime does not follow c\* [verified; exploratory]

- Run on the workstation: PySAT 1.9.dev2, 8 runs in parallel, cap 900 s.
  - 15 instances, 1–2 per cell, seeds 9101–9126, none of them batch
    instances.
  - Rows: `cluster_staging_maxsat/results/workstation_check_calib_2sat_sc/`.
  - Table: `CALIB_2SAT_SC.md` §10a.
- **c\*.**
  - n = 2000: c\* 0–3, in milliseconds.
  - n = 8000: c\* 0–11.
  - n = 32000, α 1.10–1.15: c\* 3–13.
  - n = 32000, α 1.20: both censored at 960 s (SIGKILL), with lower bounds
    19 and 18.
- **Runtime.** It spread widely at equal or similar c\*: c\* 8 took 1.0 s
  and c\* 11 took 161 s at n = 8000, α 1.2.
- **Window.** Only 2 of 13 completions fell in (30, 900] s: c\* 11 at 161 s
  and c\* 13 at 85 s.
- **Status.** Not data for the batch readout. The grid and rules are
  unchanged.

### N-2026-10-08-f — Correction: c\* and RC2 runtime were conflated in the larger-n Max-2-SAT projection [correction]

These two quantities are separate measurements and must be kept apart:
- **c\***: the proven minimum number of unsatisfied clauses (soft weight;
  all weights are 1 in the random families);
- **RC2 runtime**: wall-clock seconds to prove optimality.

Where they were conflated:
- **`GRID_POINTS_WINDOW_30_900.md` §4.4 and decision G-d** project "n = 600
  needs c\* ≈ 18–23" and say "aiming at c\* ≈ 18–23". That treats the c\*
  band of instances whose *time* fell in (30, 900] s at n = 250–400 as if
  c\* set the time.
- The same document notes that "time at fixed c\* grows with n", which
  already undercuts the projection.
- **`NEXT_SESSION_CONTEXT.md` §0** ("aim at a c\* band rather than a fixed
  α") carries the same assumption.
- My chat answer of 2026-10-08 called near-threshold cells "trivial for RC2
  … unless n is in the thousands". That extrapolated from n ≤ 400 as if
  small c\* implied short runtime at every n.

The correct framing:
- Eligibility is a **time** condition (certified, 30 < t ≤ 900 s).
- A minimum on c\* (now c\* ≥ 3 for Max-2-SAT, `CALIB_2SAT_SC.md` §6) is a
  **separate** condition.
- Neither predicts the other across n or α. Neither establishes memetic
  difficulty, which is measured separately in seconds.

Dated correction notes were added under the affected passages. Their
original text is unchanged.

### N-2026-10-08-e — calib_a/b instances are nested across α at the same (n, seed) [verified + inference]

**[verified]** Both generators draw clauses one at a time from one RNG stream.
So for a fixed (n, seed), the instance at a smaller α is a prefix of the
instance at a larger α. Confirmed on the files:
- `calib_a/…v100_k2_sr2.00…_s1` is the first 200 clauses of `…sr3.00…_s1`;
- `calib_a/…v400_k2_sr2.00…_s3` is a prefix of `calib_b/…v400_k2_sr2.15…_s3`;
- `calib_a/…v250_k3_sr4.26…_s2` is a prefix of `calib_b/…v250_k3_sr4.35…_s2`.

Different seeds in the same cell are not nested.

**[inference]**
- Within a cell, instances are independent.
- Across α cells at the same n, they are paired, and per seed c\* is
  non-decreasing in α.
- Pooled analyses that treat instances from different α cells as independent
  (the pooled ρ and its cell-stratified bootstrap, `CORPUS_CALIBRATION_GOALS.md`
  §5.2; candidate-cell tables read across α) overstate the effective sample
  size. The size of that effect is not estimated here.
- Nothing is regenerated.

**[decision]** New batches give each cell its own seed block. `calib_2sat_sc`
uses seeds 201–245, one per instance.

### N-2026-10-08-d — `calib_2sat_sc`: large-n, slightly supercritical random Max-2-SAT prepared (not submitted) [quote + decision + verified]

**The user's motivation, as given:**
> - The proven satisfiability threshold for standard uniform random 2-SAT is alpha = m/n = 1.
> - The critical window has width Theta(n^(-1/3)). Staying inside that window does not make the expected optimum grow without bound as n increases.
> - My aim is to keep alpha slightly above 1 and increase n substantially, looking for instances with a proven optimum c* > 2 and meaningful computational difficulty.
> - Near-threshold theory suggests n*(alpha-1)^3 as a useful scaling quantity, with logarithmic qualifications in known bounds. Do NOT treat it as a numerical prediction of c* or runtime.
> - Describe this batch as "large-n, slightly supercritical random Max-2-SAT," rather than claiming that all cells lie inside the critical window.

**References** (model definitions read from the TeX sources):
- **BBCKW,** RSA 18(3):201–256, 2001, doi:10.1002/rsa.1006.
  - Model: F_{n,m}, "exactly m different clauses" over the 4·C(n, 2) proper
    2-clauses.
  - The scaling window has width Θ(n^{−1/3}).
- **CGHS,** arXiv:math/0306047.
  - Model: clauses chosen uniformly *with replacement*.
  - For c = 1 + ε, c\* ≲ (ε³/3)n asymptotically, and ≳ α₀ε³/(3 ln(1/ε))·n
    for small ε.
  - In the window parametrisation c = 1 + λn^{−1/3}: c\* = O(λ³) for λ > 1,
    and Θ(1) for |λ| ≤ 1.
  - Note λ³ = n·ε³.

**Batch** [decision; verified generation]:
- n ∈ {2000, 8000, 32000} × α ∈ {1.10, 1.15, 1.20}, 5 seeds per cell, 45
  instances, m = round(αn).
- Generator `ksat_distinct` (= BBCKW F_{n,m}); all clauses soft, weight 1.
- Fresh per-cell seeds 201–245.
- All cells have λ = εn^{1/3} > 1: they lie above the window, not in it.
- n·ε³ (2–256) is a covariate, not a prediction.

**Measurement.** The calib_a/b RC2 measurement, unchanged:
- RC2 g3, PySAT 1.9.dev3, enforced by a new opt-in `EXPECT_PYSAT` guard;
- a 900 s **wall-clock** cap from the start, plus a 60 s SIGKILL grace with
  lower-bound recovery.

**Rules.** Pre-registered in `CALIB_2SAT_SC.md` §6 and the readout script.
- Eligible: certified, 30 < t ≤ 900 s, and c\* ≥ 3.
- Cell outcomes: promising / too_easy / too_hard / mixed, with stated
  follow-ups.
- Promising cells need a memetic assessment, in seconds, before any corpus
  decision.
- The final corpus uses fresh seeds.

**Budget.** At most 12.0 CPU-h; about 40 min elapsed at %30.

### N-2026-10-08-c — The existing generator samples clauses with replacement; `ksat_distinct` added for exactly m distinct clauses [verified + decision]

- **The existing generator meets 5 of the 7 requirements.**
  `instancegen.generate.generate` (`weighted_ksat` 0.1.0) satisfies distinct
  variables, fair signs, no tautology and seed reproducibility.
  - It does **not** exclude duplicate clauses.
  - It sets m = round(α·n) rather than taking m as input.
- **Measured duplicates in calib_a/b/c.**
  - Max-2-SAT: 133 of 170 files contain a repeated clause, 493 extra copies
    in total (0.09–1.2 % of clauses per cell, matching C(m, 2)/N).
  - Max-3-SAT: 24 of 160 files, 35 extra copies.
  - A repeated unit-weight clause acts as weight 2, and the recorded c\*
    values include it. Those instances are unchanged and stay labelled
    `weighted_ksat`.
- **Decision.** A separate mode was added in the same package:
  `generate_distinct` / `generate-distinct`, generator name `ksat_distinct`
  1.0.0. It samples clauses uniformly without replacement by rejection,
  records the rejected candidates, writes the old WCNF dialect, and has its
  own filename prefix.
  - `GenParams` and `generate()` are untouched: a pinned SHA-256 matches the
    calib_a file on disk.
- **Benchmark (generation only, no RC2).** k = 2, n = 32000, m = 38400 takes
  0.26 s wall clock and 43 MB peak, and writes 626 KB. There was 1 rejected
  candidate; the output is byte-identical across runs and passes validation.
- **Not established.** Excluding duplicates says nothing about hardness or
  c\*; that is left to calibration.
- **Full note:**
  [`RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md`](RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md).

### N-2026-10-08-b — Predictions for the RC2 cap-3600 re-run, recorded before submission [inference, pre-registered]

- 148 censored instances are re-run at a 3600 s cap (`RC2_CAP3600_RERUN.md`).
- They are split into 9 groups by sibling evidence at 900 s. Each group has
  a stated prediction (`RC2_CAP3600_RERUN.md` §6). In short:
  - groups where sibling seeds certified (G1, G4, G6): majority certify;
  - groups where no sibling certified (G3, G5): ≤ 10 % certify;
  - uuf250 with LB 2 (G8): no call; it directly tests C2 of the Max-3-SAT
    note.
- Claim under test: sibling evidence predicts certification better than
  the size of the LB.
- Check with `cluster_staging_maxsat/scripts/compare_cap3600_predictions.py`.
  Record the outcome in §6 of that document and as a new note here. Never
  edit this entry.

### N-2026-10-08-a — SATLIB RC2 screen: 95 of 263 eligible, almost all uuf; jnh has c\* up to 4 but is far below the window [verified]

- 263 rows back (job 22379183), 251 certified, 12 censored, 0 failed;
  PySAT 1.9.dev3 throughout.
- **Eligible (certified, 30 < t ≤ 900 s): 95** — uuf200 34, uuf225 60,
  hole9 1. c\* = 1 on 70, c\* = 2 on 25.
- dubois, pret, bf, hole6–9: c\* = 1 as predicted in N-2026-10-07-d; all
  but hole9 solve in under 6 s.
- jnh: c\* = 1 ×17, 2 ×11, 3 ×5, 4 ×1, all in under 0.6 s, so none
  eligible.
- The 11 censored uuf all carry a recovered lower bound of 2 (c\* ≥ 2);
  hole10 censored without a bound.
- uuf200-01…010 reproduce the historical c\* exactly.
- *Implication [inference]:* the SATLIB batch adds n = 200/225 uuf points
  and a single structured instance to the memetic stage. It does not add
  origin diversity to the eligible set, and it does not widen c\* beyond
  {1, 2}. Max-2-SAT and MaxCut remain the source of larger optima.

Evidence: `SATLIB_BENCH_INTAKE.md` §8;
`cluster_staging_maxsat/results/profile_satlib_all.jsonl`.

### N-2026-10-07-f — Possible expansion: certify all 100 SATLIB uuf250 with a longer budget, for RC2 and memetic [verified + decision: deferred, not urgent]

*User, 2026-10-07:* a potential, very non-urgent expansion of the
experiments: extend the time budget for both RC2 and memetic until RC2 has
solved all of the 250-variable uuf250 instances
(`data/unsat250_1000c/`). These are SATLIB "uuf250-1065" files:
`p cnf 250 1065`, although the directory name says 1000c.

**Current state** [verified]. Read off
`cluster_staging_maxsat/results/profile_uuf250/uuf250_arr_task_*.jsonl`:
100 rows, one per instance, RC2, cap 900 s, all from the SATLIB copies.

| outcome | count | detail |
|---|---:|---|
| certified optimal, c\* = 1 | 77 | `solve_s` 14.6–889.6 s |
| not finished: killed by the harness | 21 | `subprocess_killed` at cap + 60 s (≈ 960 s); LB recovered from the progress file |
| not finished: solver timeout | 2 | `timeout` at ≈ 922–927 s (uuf250-027, -074) |
| **not finished, total** | **23** | none is a software failure; all 23 are censored at budget |

The censored lower bounds among the 23:
- **LB 1 (18 instances):** 02, 04, 08, 013, 016, 022, 027, 032, 035, 039,
  052, 069, 074, 077, 078, 086, 088, 092.
- **LB 2, so c\* ≥ 2 is proven (5 instances):** 030, 036, 037, 085, 095.

**Memetic coverage today** [verified]. By sha256 against
`results/tier2_memetic_instance_index.csv`, memetic was run on 24 of the
100 instances (5 seeds × 3 configs, 900 s). All 24 are among the 77
certified ones. That leaves 53 certified instances without a memetic run,
and the 23 censored ones have no reference optimum at all.

**What the expansion would give.**
- The full 100-instance SATLIB uuf250 set with known c\*.
- The first certified c\* ≥ 2 instances at n = 250: at least the 5 with
  LB 2. Today there are none (`RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`
  §3.1, C1).
- The hardest-for-RC2 tail of the family, compared with memetic at a
  matched, longer budget.

**What it costs.** RC2 time grows by about 2.3 decades per unit of c\* at
n = 250 (`docs/CALIB_B_B1_READOUT.md` §5) [inference]. The LB 2 instances
may therefore need far more than 900 s. No budget is proposed here: the
"hours" estimate from the B1 slope was withdrawn (§2, earlier notes,
2026-10-06). Any plan needs a staged cap (for example, rerun the 23 at a
longer cap and see how many finish) before committing memetic CPU.

*Decision.* Recorded as a **deferred, low-priority option**. It is not
planned, not approved, and not part of the current direction (larger-n
grids, MaxCut, the SATLIB RC2 screen). If it is taken up: a written plan
first, the RC2 extension before memetic, and SATLIB is cited
(N-2026-10-07-e).

### N-2026-10-07-e — Citing SATLIB (required acknowledgement) [quote + decision]

> Citing SATLIB: If you use SATLIB for your research, we ask you to
> acknowledge it in the respective publications by citing the following
> article:
>
> Holger H. Hoos and Thomas Stützle: SATLIB: An Online Resource for Research
> on SAT. In: I.P.Gent, H.v.Maaren, T.Walsh, editors, SAT 2000,
> pp.283-292, IOS Press, 2000.

*Source:* SATLIB's citation request, as supplied by the user on 2026-10-07.

*Decision.* Every publication or report that uses SATLIB instances cites
this article. That covers the historical uuf250 and uuf200 tier-2 set and
the `satlib_bench` families (bf, dubois, hole, jnh, pret, uuf200, uuf225).

BibTeX, assembled from the reference above:

```bibtex
@inproceedings{hoos2000satlib,
  author    = {Holger H. Hoos and Thomas St{\"u}tzle},
  title     = {{SATLIB}: An Online Resource for Research on {SAT}},
  booktitle = {SAT 2000},
  editor    = {I. P. Gent and H. v. Maaren and T. Walsh},
  pages     = {283--292},
  publisher = {IOS Press},
  year      = {2000}
}
```

### N-2026-10-07-a — Hard clauses: feasibility is not just an initialisation problem [quote + decision]

> That is more than Glucose preprocessing: even starting from a feasible
> assignment does not ensure that mutation and crossover preserve
> feasibility. The defensible exclusion is an implementation and
> experimental-scope decision, not a universal requirement that hard
> clauses need Glucose.

*Source:* user, 2026-10-07.

*Context.* This is how we phrase the hard-clause exclusion in the paper and
in the documents.
- A SAT solver such as Glucose gives a feasible **starting point**. That
  alone does not make the search feasible: the variation operators must
  also keep children feasible.
- The workstation probe found that they do not:
  - crossover of two feasible parents was feasible in 0/20 cases at hard
    ratio 3–4;
  - the polish did not repair the result.
  - Evidence: `CORPUS_FREEZE_PREP.md` §8.2–§8.4 [verified].

*Wording rule.*
- Say: "Instances with (mixed-sign) hard clauses are outside the scope of
  this study, because this implementation's operators do not preserve
  feasibility."
- Do not say: "Hard clauses require Glucose", or "memetic algorithms cannot
  handle hard clauses".
- A repair, decoder or hard-phase-noise arm would be a different algorithm
  (`CORPUS_FREEZE_PREP.md` §8.5).

### N-2026-10-07-b — SATLIB suite: "hard for systematic and local search" [quote]

> The majority of the instances from the benchmark suite is considered hard
> for both systematic and local search algorithms for SAT.

*Source:* user-supplied, 2026-10-07. It refers to the SATLIB / DIMACS
benchmark collection. **Confirm the exact source page and wording before
citing it.**

*How to use it.*
- It describes **SAT (decision) hardness** for the solvers of that era. It
  is not evidence about RC2 proof time, or about memetic MaxSAT difficulty
  today.
- **[verified]** With a modern CDCL solver (CaDiCaL 1.5.3), 278 of the 279
  `satlib_bench` files are decided in ≤ 6.3 s. The exception is hole10, at
  48 s. Source: `cluster_staging_maxsat/data/satlib_bench/manifest.jsonl`,
  field `sat_check`.
- Cite it for motivation and provenance ("a standard, long-used suite"),
  not as a hardness label for our solvers. Our hardness labels come from
  our own RC2 window and Q2 rules.

### N-2026-10-07-c — PySAT's CNF reader silently changes published SATLIB files [verified]

PySAT's `CNF(from_file=…)` is used by RC2 through
`src/cli/run_opt_rc2.py:load_as_wcnf`. It is line-based. On the original
SATLIB files it:
- turns `%`/`0` trailers and stray `0` lines into **empty soft clauses**:
  - +1 to c\* each, or an RC2 crash (`IndexError` on pret60_25);
  - 208 of 279 files are affected;
- **drops the last literal** of any clause line that lacks its terminating
  `0`: 202 clauses in dubois100. This gives a different formula with no
  error at all.

*Rule.*
- Any published CNF set goes through `scripts/satlib_bench_intake.py`, or
  an equivalent normaliser with cross-reader verification, before an RC2
  row is trusted.
- The memetic reader (`src/sat/cnf.py`) was robust to all of these defects,
  so RC2 and the memetic solver could silently disagree on the instance.

*Evidence:* `SATLIB_BENCH_INTAKE.md` §2, and the manifest field
`pysat_on_original`. The earlier uuf250 instance of the same problem:
`docs/archive/RC2_FINDINGS.md` §4.

### N-2026-10-07-d — Optimum diversity must come from Max-2-SAT and MaxCut, not from SATLIB unsat families [inference + decision]

- Most SATLIB unsatisfiable families are **minimally unsatisfiable by
  construction**: dubois (XOR chains), pret (parity), hole (pigeonhole).
  Expect c\* = 1. This is verified only on dubois20 and pret60_25 so far.
- uniform random 3-SAT at the threshold is mostly c\* = 1. Historical
  uuf200: 8 × c\* = 1 and 2 × c\* = 2 out of 10 [verified].
- A corpus of SATLIB unsat instances alone would reproduce the "everything
  has c\* = 1" restriction of range that the broadening exists to fix.

*Decision.*
- **Keep Max-2-SAT** (eligible c\* 18–50) **and MaxCut** (c\* expected in
  the tens) in the corpus.
- **In the research conclusions, emphasise that the optimum varies:** c\* =
  1 (SATLIB, Max-3-SAT at n ≥ 250) versus c\* in the tens (Max-2-SAT,
  MaxCut).
- The SATLIB families contribute **origin** and **clause-length**
  diversity.
- *Open:* jnh (mixed clause length, m/n 8–9) and bf (circuits) have unknown
  c\*. The proposed RC2 screen (`SATLIB_BENCH_INTAKE.md` §5) answers that.

### Earlier notes (recorded in their own documents; listed here for completeness)

- **2026-10-06.** Max-3-SAT optimum at large n, claims C1–C4, and the
  withdrawal of an "hours" estimate from the B1 slope.
  `RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`.
- **2026-10-06.** The window grid points, and the revision of B1 §5, which
  used 60–600 s, to (30, 900] s. `GRID_POINTS_WINDOW_30_900.md`.
- **2026-10-06.** The hard-clause reassessment:
  - the "no gradient toward feasibility" wording is withdrawn;
  - the `mutate1` stale-feasibility latent bug is documented (staging
    `evo/memetic.py:152`).
  - `CORPUS_FREEZE_PREP.md` §8.
- **2026-10-06.** Effort is measured in seconds (primary). Calls and flips
  are not size- or host-free. `NEXT_SESSION_CONTEXT.md` §3.
- **2026-09-07.** Restriction of range destroys the orthogonality claim.
  The four broadening axes. `more_data/CORPUS_BROADENING_HANDOFF.md`.
