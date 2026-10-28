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
| RC2 re-run at cap 3600 s, with predictions recorded in advance | [`RC2_CAP3600_RERUN.md`](RC2_CAP3600_RERUN.md) | 148 censored instances (excluding mse16/raw/more_data); 9 groups by sibling evidence, each with a prediction; comparison script. See N-2026-10-08-b. Outcome (§6): 25/148 certified; N-2026-10-11-a. |
| Random k-SAT generation: with vs without replacement; the `ksat_distinct` mode | [`RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md`](RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md) | The existing `weighted_ksat` samples clauses with replacement, so calib_a/b/c contain duplicate clauses. The new mode gives exactly m distinct weight-1 clauses by rejection sampling. Algorithm, seed behaviour, format, validation, and an n = 32000 benchmark. See N-2026-10-08-c. |
| Large-n, slightly supercritical random Max-2-SAT (`calib_2sat_sc`) | [`CALIB_2SAT_SC.md`](CALIB_2SAT_SC.md) | **Readout §10d (2026-10-11): 1 eligible (n 8000, α 1.20, c\* 14), c\* up to 14, N-2026-10-11-h. calib_2sat_sc2 readout §13a: 2 promising cells, 6 eligible (c\* 9–14), N-2026-10-11-n. Memetic v2 assessment prepared §13b (two arms: 12.5k and 200k flips per call, 36 tasks), N-2026-10-11-p/q.** The model (BBCKW F_{n,m}, distinct clauses), the near-threshold theory used only as a covariate (n·ε³ = λ³), the measurement conventions (wall-clock 900 s cap, SIGALRM delay, watchdog), pre-registered cell rules, budget and commands. See N-2026-10-08-d…f. |
| Memetic solver `impl: v2` — why, what, how checked | [`MEMETIC_IMPL_V2.md`](MEMETIC_IMPL_V2.md) | v1's WalkSAT polish is O(m) per flip: measured at n 2000–32 000 (about 300 flips per 3.5 s call at n = 32 000; 120 s left it 2000+ above c\*). v2 makes v1's exact decisions with incremental bookkeeping (57 equivalence tests), 50–1800× faster per flip; v1 stays the default. Seconds are comparable only within one `impl`. N-2026-10-08-h/i. |
| Hard-clause solver in a new staging tree; multistart-may-be-enough | [`HARD_CLAUSE_SOLVER_PLAN.md`](HARD_CLAUSE_SOLVER_PLAN.md) | The user's intention (2026-10-11): a new staging tree with a copy of the up-to-date solver, Glucose initialisation, and operators that keep hard feasibility. The plan also gives the evidence that most successes came at the first child or in the first generation, and what that does and does not show. Milestones H0–H6. N-2026-10-11-b/c. |
| MSE 2016/2023/2024: state, best-known costs, EvalMaxSAT 3600 s sample | [`MSE_EVALMAXSAT_3600.md`](MSE_EVALMAXSAT_3600.md) | What exists for each MSE set; best-knowns rechecked (and the cross-year name trap); opinion; the driver fixes (new WCNF dialect, SIGTERM anytime stop); sample s1 (2 × 30, stratified by family); files and commands. N-2026-10-11-f/g. **s1 readout §9: 18 proven optima = best-known; 19/30 MSE 2023 no-ub. N-2026-10-11-o.** |
| How Glucose (CDCL) works: decisions, conflicts, phases, assumptions | [`RESEARCH_NOTES_GLUCOSE_CDCL.md`](RESEARCH_NOTES_GLUCOSE_CDCL.md) | Decisions and decision levels, the trail, conflict analysis and backjumping, VSIDS and phases, `set_phases`, assumptions and cores. Why repair and moves are biased toward the given assignment but not nearest to it (probe-checked), why singleton cores are proofs but weak bounds, and why single calls can be slow (the conflict budget). N-2026-10-11-m. |
| Hyperparameter setting: frameworks, algorithms, what is influential (2026) | [`RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`](RESEARCH_NOTES_HYPERPARAMETER_TUNING.md) | AC tools (irace 4.5, SMAC 2.4.1, Optuna 5.0.0; ParamILS, GGA, Hyperband/BOHB/DEHB), per-instance configuration (ISAC, ISAC+ MaxSAT, Hydra), configuring for scaling (Styles et al. 2012; Mascia et al. 2013; Mu et al. 2016), DAC, LLM-driven design. Recommendation for HP-1: batch racing per size band, held-out large instances. N-2026-10-11-s. |
| HP-1 calibration plan; instance-size inventory | [`HYPERPARAMETER_CALIBRATION_PLAN.md`](HYPERPARAMETER_CALIBRATION_PLAN.md) | 1,947 instance files, m from 48 to 276,705; proven c\* per size band (S 465, M 144, L 22 all-soft). Plan: flip-limit grid per band (S/M/L by m-decade), size-scaled budgets, racing, held-out test of categorical vs continuous rules. Not run. N-2026-10-11-s. |
| Is there a known c for a flip limit c · n? (WalkSAT linear-time theory, Maxflips scaling, IRoTS, memetic depth) | [`RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`](RESEARCH_NOTES_FLIP_LIMIT_SCALING.md) | No published c. Flips ∝ n only on satisfiable formulas below a density threshold (proven for 2-SAT α < 1). The optimal WSAT Maxflips grows as ~n^2.4 at the 3-SAT threshold. IRoTS scales its parameters with n (stall window n²/4). c = 15 must be calibrated, and the 3.5 s cap binds at n = 64,000. N-2026-10-12-b. Stance 2026-10-14: c is calibrated empirically by our grid, not by a framework; it is part of the orthogonality flow (plan §0c, N-2026-10-14-a). |
| Solver directions: exact Max-2-SAT kernel of the n 64,000 instances; preprocessing, stronger raw memetic, large-kernel corpus | [`RESEARCH_NOTES_SOLVER_DIRECTIONS.md`](RESEARCH_NOTES_SOLVER_DIRECTIONS.md) | Exact rules (pure literal, degree-2 MaxSAT resolution) shrink the 6 eligible calib_2sat_sc2 instances to 300–572-variable kernels; rebuilt cost = c\* on all. The unchanged memetic solves the 3 n 64,000 kernels in ≤ 0.7 s (s253 open). Explains the size-independent Stage L1 optimum. Directions A (preprocess, recommended) / B (impl v3: partition crossover, clause weighting) / C (large-kernel corpus). N-2026-10-14-e. §7: it does not carry over to 3-SAT, dense 2-SAT or crafted instances (N-2026-10-14-f). §8 (user decision): kernelise for the sparse Max-2-SAT grid behind a ≤ 0.1 s worth-it screen (N-2026-10-14-g). |
| Kernelised memetic (direction A): module, gate, 18-task batch; proposed stronger memetic (direction B) | [`../current2/KERNEL_MEMETIC_RUN.md`](../current2/KERNEL_MEMETIC_RUN.md) | `src/sat/kernel.py` + opt-in `preprocess: kernel` in the shard (schema 4); exactness checked by brute force for every kernel assignment. Smoke: 5/6 eligible instances at c\* in ≤ 1.5 s including kernelising; s253 open (15 vs 14). **Batch read 2026-10-18: 15/18 (s253 0/3), N-2026-10-18-d.** §5: B1 tabu, B2 clause weighting, B3 distance-aware mutation, B4 partition crossover, B5 compiled loop. N-2026-10-18-a. |
| Stronger memetic built (`impl: v3`, tree `cluster_staging_maxsat_strong/`); smoke; batch S1 | [`../current2/STRONG_MEMETIC_S1_RUN.md`](../current2/STRONG_MEMETIC_S1_RUN.md) | All of B1–B5 built on the hard tree plus the kernel ports; v3 without keys = staging v2 / `impl: hard` exactly; C core = Python twin flip for flip. Smoke (60 s, seed 1): `allC` solves kernel s253 (5.8 s) and raw s256/s257 (n 64k) at c\*; mutation damage 200–640 → 7–12 clauses. Batch S1: 324 tasks, ≤ 86.4 CPU-h, commit `16589fb`. N-2026-10-18-c. |
| Stronger memetic B1–B5 (tabu/CC, clause weighting, distance-aware mutation, partition crossover, compiled loop): motivation, mechanism, parameters, interactions, build plan for a third tree | [`../current2/STRONGER_MEMETIC_DESIGN.md`](../current2/STRONGER_MEMETIC_DESIGN.md) | Design only. SATLike weighting rules and parameters read from the full text; PX exactness derived (each clause's differing variables lie in one component). Interactions §6 fix the build order B3 → B1 → B2 → B4 → B5 and a leave-one-out batch (288 tasks, ≤ 76.8 CPU-h). Tree `cluster_staging_maxsat_strong/` proposed. N-2026-10-18-b. |
| Agenda notes 2026-10-21; first ρ sketch (U30 out of ρ; effort floor) | [`../current2/NOTES_2026-10-21_AGENDA_AND_STATS.md`](../current2/NOTES_2026-10-21_AGENDA_AND_STATS.md) | U30 uniformly easy (83 % first-call); reasons to exclude it from ρ; floor caveat for O900; MSE 2016 and large-MSE notes; monkey-patch explanation pending. N-2026-10-21-l. |
| Long-clause rule (lean v3 tables) for the setcover rail instances | [`../current2/LONG_CLAUSE_RULE_DESIGN.md`](../current2/LONG_CLAUSE_RULE_DESIGN.md) | Design only: trigger Σk(k−1) > 50M; CC/PX exact, walk same distribution; tests and decisions. N-2026-10-21-j. |
| Batches U30 + HMSE: under-30 s pool and MSE hard-clause pool on the strong solver | [`../current2/UNDER30_HARDMSE_RUN.md`](../current2/UNDER30_HARDMSE_RUN.md) | U30 319 instances (957 tasks), HMSE 141 (423 tasks); selection, smoke, rail memory limit, flat upload + arrange scripts. N-2026-10-21-i. |
| Prior work: orthogonality of anytime (local search) and exact solvers; passing the exact optimum to the anytime solver | [`../current2/RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md`](../current2/RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md) | Closest precedent is SAT: Hoos & Stützle (TR-99-06 / KI-99), R-Novelty+ vs Satz on uf100-430, correlation 0.26. IRoTS (Smyth, Hoos & Stützle 2003) takes its MaxSAT target from complete solvers but correlates local search with local search only. No MaxSAT study of exact proof time vs anytime time to the optimum was found. N-2026-10-24-a. |
| Compiled memetic: memory and speed for the MSE 2026 sizes (C parser, C tables, per-child C functions; twins with the same decisions) | [`../current2/COMPILED_MEMETIC_PLAN.md`](../current2/COMPILED_MEMETIC_PLAN.md) | Measured 88–100 MB RAM per MiB of .wcnf (parse 20×, `_Static` 23×, `_V3Static` 19×); 33 MSE 2026 instances predicted above 64 GB; 203 over 25 MiB get ~0 children per minute in Python. Plan C1–C4, inventory, literature. C1 built (481 tests). N-2026-10-28-d. |
| MSE 2026 ρ benchmark: unpack + hash job, manifest plan, memory bins, flip counter, per-run RAM | [`../current2/MSE26_RHO_PLAN.md`](../current2/MSE26_RHO_PLAN.md) | 952 instances with a published optimum unpacked (398 under 30 s by published EvalMaxSAT, 392 in (30, 3600], 162 not by EvalMaxSAT); MSE 2023 not touched (user). Flip counter: exact in calls 1–16 (≤ 6 % error after), cutoff in calls not seconds. Per-run peak RSS recommended. N-2026-10-28-b. **2026-10-28 later (§7):** unpack done; EvalMaxSAT own runs dropped, ρ x = published 2026 EvalMaxSAT (VBS, per-solver as sensitivity); memetic 952 × 3 × 1800 s after the flip counter. N-2026-10-28-c. |
| OpenAI's claimed refutation of ETH (subexponential #k-SAT, Oct 2026): manuscript vs Lean scope, Max-k-SAT corollary, artifacts, relevance, feasibility | [`../current2/RESEARCH_NOTES_ETH_REFUTATION_CLAIM.md`](../current2/RESEARCH_NOTES_ETH_REFUTATION_CLAIM.md) | **A claim under independent examination; documentation only.** Theorem 1.1 is deterministic exact #k-SAT (fixed k) in $(n+m)^{O_k(1)}2^{O_k(n\log\log n/\sqrt{\log n})}$ time and polynomial space. Lean covers only the weaker $2^{O_k(n(\log\log n)^2/\sqrt{\log n})}$ bound, and the appendix cited for the sharper bound is missing from the LaTeX. Corollary 1.2 (`cor:max-sat-approximation`) gives OPT − εm, unweighted, randomized, with ε fixed. There is no runnable solver, only a proof development. As parameterised, it falls back to exhaustive search below n ≈ 2^{1.09·10¹⁰}. Nothing to implement. N-2026-10-28-a. |
| LLM-driven solver design (FunSearch, EoH, ReEvo, LLaMEA, MCTS-AHD, AlphaEvolve; SAT: AutoSAT, SATLUTION) | [`RESEARCH_NOTES_LLM_SOLVER_DESIGN.md`](RESEARCH_NOTES_LLM_SOLVER_DESIGN.md) | The method family, SAT/MaxSAT applications (no MaxSAT local-search work found), independent critiques (generalisation, cost), and where it could apply to our solver. **Direction not pursued (user, 2026-10-11; §7).** N-2026-10-11-t/u. |

## 2. Dated notes (newest first)

### N-2026-10-28-d — Compiled memetic before 3c: measurements, literature, plan; C1 built [quote + verified + inference]

> "if you reason optimizing further and compiling parse and memetic will help tell me, tell me also if you can find some memory optimizations in research litreture, that you might be able to implement" / "do the recommended best option, document all optimiztions and compilations" (user, 2026-10-28)

- **[verified]** Peak RSS ≈ 100 MB per MiB of .wcnf (real 88×, 94×; synthetic 96–100×); stage breakdown on a 5 MiB MSE file: parse 20×, `_Static` 23×, `_V3Static` 19×, NativeCore flatten 7×. Parse ~5.5 MB/s. A 26 MiB file: 0 children in 22 s; 26 MiB overshoots a 30 s budget by ~15 s (watchdog risk with GRACE 60 on big files).
- **[verified: web]** Techniques: MiniSat region allocator (32-bit refs), CSCC (no neighbour lists), non-caching scores, PXSAT (linear-time PX on differing variables), MaxPre (not used).
- **[inference]** Compile before 3c: a later speed-up would mix versions inside the ρ sample (seconds). Twins keep the decisions: Python control flow and RNG, C for deterministic data work.
- **[verified] C1 built:** C parser + tables + once-per-run passes; 42 new tests incl. identical whole memetic runs; no memory gain yet (+5–17 %) until C2 moves the per-child readers.
- Note: `docs/current2/COMPILED_MEMETIC_PLAN.md`.

### N-2026-10-28-c — MSE 2026: unpack done; memetic only at 1800 s; ρ x from the published exact results [quote + verified + inference]

> "do only the memetic staff, I want to see how the solver performs at all, give it 1800s, later we do the granuarity for less if I want, meanwhile consider tkimg exact solver results for rho from web mse" (user, 2026-10-28)

- **[verified]** Milestone 2 done: array 23643046, 50/50 TASK_OK, ALL_DONE; `mse26_content.tsv` checked (1,216 rows, 952 unpacked, no duplicate content sha256, flags match the work list).
- **Decision (user):** our EvalMaxSAT runs (3a) dropped; memetic 952 × 3 seeds × 1800 s; "granularity for less" = shorter budgets later (user's answer); flip counter (3b) stays before the manifest.
- **[verified in code]** Shorter budgets are read off the 1800 s records: hyperparameters depend on instance features only; the budget only caps the last call.
- **[verified]** Published 2026: 22/15 exact solvers per track; EvalMaxSAT proves 792 of the 952 (398 ≤ 30 s, 392 window), single-threaded (CPU/wall 0.99).
- **[inference]** x of ρ: published EvalMaxSAT wall time primary (ranks cancel a uniform hardware factor); VBS sensitivity (no censoring); per-solver ρ descriptive; per track and pooled.
- **[verified in code]** Both native cores track true hard count and original-weight soft cost per flip, so the counter is one comparison per flip.
- **[verified] 3b built:** schema 7 target-hit fields + `peak_rss_mb`; exact in every call (no 16-call cap: same cost); 439 tests pass; overhead ≈ 2 %; smoke: U30 bf0432-007 hit at flip 3,704 of call 1. §8.
- Note: `docs/current2/MSE26_RHO_PLAN.md` §7–§8.

### N-2026-10-28-b — MSE 2026: unpack + hash job prepared; manifests include under-30 s; flip counter limited to calls 1–16; per-run RAM [quote + verified + proposal]

> "unpack what you recommend, do mainifests for also instances that where proved by exact solver in under 30s, later do per flip, [...] only in the first several 12500 flips calls [...] do the reasoning" and "initially give larger instances more ram, you can add if you find for statistics useful - ram check per run" (user, 2026-10-28)

- **[verified]** MSE 2026 download done (job 23591248, ALL_DONE); census `MSE_PUBLISHED_EXACT_RESULTS.md` §7. EvalMaxSAT 2026 smoke done on the cluster (user).
- **[verified]** The 952 instances with a published optimum: published EvalMaxSAT ≤ 1 s 167, (1, 30] 231, (30, 3600] 392, not by EvalMaxSAT 162; 80.3 GiB as .wcnf.
- **Prepared + mock-tested:** `mse26_unpack_array.sbatch` (50-task array, user asked for parallel; unpack 952, content sha256 of all 1,216) + `mse26_unpack_finish.sh` (merge, symlinks `data/raw/mse26`). Upload `tmp/upload_mse26_unpack/`. MSE 2023 extraction removed from the job (user: "I dont want mse23 extraction meanwhile").
- **[verified records]** Calls to target: U30 83 % at 1 call, 99 % ≤ 16; O900 54 % / 94 %; HMSE 4 % / 38 %.
- **[inference]** Per-flip resolution matters only in the first calls (error ≤ 1/K after K calls). Cut off at 16 calls, not seconds: seconds per call differ ~100× between U30 and HMSE.
- **[proposal]** Per-run peak RSS in the memetic and EvalMaxSAT records (sacct MaxRSS is blank). Memory bins from the start for MSE 2026 (user).
- Note: `docs/current2/MSE26_RHO_PLAN.md`.

### N-2026-10-28-a — OpenAI's claimed refutation of ETH: what it claims, what Lean covers, and why it gives us nothing to implement now [quote + verified + inference]

> "Shlomi Dolev sent me OpenAI's claimed refutation of the Exponential Time Hypothesis and suggested that we might be able to use the results in our MaxSAT research. […] For now, this is documentation only: do not implement anything, modify the solver, or launch experiments." (user, 2026-10-28)

- **[quote] The source calls it a claim under examination.** `openai/math` `history.md` (2026-10-26): "An independent working group of computer scientists led by Russell Impagliazzo, Ramamohan Paturi, and Ryan Williams will examine and explain the proof." The repo README says the manuscripts are "raw research data" produced by "an unnamed internal OpenAI model". The OpenAI announcement page returned 403 and was not read.
- **[verified] The manuscript claims** (Theorem 1.1, `thm:main`): deterministic exact #k-SAT, fixed k ≥ 2, in $(n+m)^{O_k(1)}2^{O_k(n\log\log n/\sqrt{\log n})}$ bit operations and $(n+m)^{O_k(1)}$ space; when m ≤ Dn, $2^{O_{k,D}(n/\sqrt{\log n})}$.
  - The main text proves the weaker $2^{O_k(\rho(n))}$, ρ(n) = n(log log n)²/√log n (Proposition 6.4).
  - The cited "Appendix app:quantitative" for the sharper bound is **absent** from `main_full_version.tex`.
- **[verified] Lean** (`lean/docs/378.md`; `exact_count_and_sat`): covers the ρ(n) bound only.
  - The bound is stated in terms of the encoding bit length L, for a multi-tape machine, with visited cells ≤ (L+1)^{O_k(1)}.
  - The constants are existential.
  - Not built or checked by us.
- **[verified] Max-k-SAT** (Corollary 1.2, `cor:max-sat-approximation`):
  - randomized; finds an assignment with ≥ OPT − εm satisfied clauses, with probability 1 − 2^{−Ω(n)};
  - time $(n+m)^{O_{k,\varepsilon}(1)}2^{O_{k,\varepsilon}(\rho(n))}$;
  - unweighted, ε fixed, via clause sampling plus a threshold circuit.
- **[verified] Artifacts:** paper, LaTeX, and a Lean proof development (≥ 3,977 files). There is **no runnable SAT/MaxSAT solver** and no non-Lean code.
- **[inference] Feasibility.** The paper's explicit parameters fall back to exhaustive search unless ⌈log₂ n⌉ ≥ 521,284 (sparsification) and ≈ 1.09·10¹⁰ (counting construction). Even with retuned constants, the one-group factor alone is about 2^{0.45–0.5 n} at n = 10⁴–10⁶, worse than PPSZ.
- **[inference] Relevance:**
  - ρ/orthogonality results, RC2 and EvalMaxSAT as exact references, and the memetic solver are unaffected.
  - The corollary's εm additive error is far above our c\* (1–50).
  - It has no weights and no hard clauses.
  - Long MSE clauses violate fixed k.
- **[decision] Nothing implemented** (user). Follow-up checklist (working-group outcome, missing appendix, Lean comparator, concrete-constants analysis): note §5.3, §7.
- Note: `docs/current2/RESEARCH_NOTES_ETH_REFUTATION_CLAIM.md`.

### N-2026-10-25-g — Batch POP prepared, not run: R4's pop {10, 40} on all 144 MSE 2023/2024 hard-clause instances; pre-registered rule on arrival and fitness [quote + verified + proposal]

> "do prepare run for some data we already have, not mse26, I want to check If with pop10 instead pop40 is better, prepare rule, that takes into account fitness, and arrival at optimum" (user, 2026-10-25)

- **[verified] Why:** R4's pop 10 on hard instances was the user's choice; KS2 showed no pop effect (`ks2_10` vs `ks2_40` 8 / 7 on 16). Soft pools cannot show one (median run: 1 child).
- **[verified] Batch:** HMSE h001–h141 + rail 3 × {`hard_pop` 10, 40} × 3 seeds = 864 tasks, 900 s, stop at the target, `auto_hparams/3` otherwise. New option `hparams.hard_pop` (default 10; `/3` unchanged).
- **[verified] Smoke (20 s), upload, tests:** the pop reaches R4 (records show 10 / 40, R5 still on rail); 12-file flat upload (`tmp/upload_pop/`, `arrange_pop.sh` mock-tested), no C rebuild; 421 passed / 16 skipped.
- **[decision] Not run** (user, 2026-10-25: "dont need to run batch then"): R4 keeps pop 10. This followed the explanation that pop 10 is the user's choice, not a measured result: KS2 showed no pop effect; lisbon single runs and 26 vs 24 successes are the only hints (`POPSIZE_RUN.md` §6). Tree kept for a later run.
- **[proposal, never confirmed] Reading** (`scripts/popsize_readout.py`, written before results): per instance, arrivals → median cost → TTT (≥ 1.25×, both ≥ 2/3). An arm wins a group if it is better by a sign test (all 144 at α 0.05; unweighted 2023 / weighted 2024 at α 0.025 each), **and** it loses no arrivals overall (W2), **and** it loses no fitness comparisons on balance (W3). Class pop = class winner, else overall winner, else 10.
- Note: `docs/current2/POPSIZE_RUN.md`.

### N-2026-10-25-f — EvalMaxSAT 2026: the official static competition binary, smoke-tested; memory bins for the 2026 manifests from EvalMaxSAT's published peaks [quote + verified + proposal]

> "do option 1, use static binary if you reason we dont need local compilation" (user, 2026-10-25)

- **[verified] The binary:** statically linked (GCC 15.2; Boost/GMP/MPFR/SoPlex inside). It was launched with no options in MSE 2026. A source build needs a C++23 toolchain and GMP/MPFR/Boost static libraries, so the binary is used as is: identical to what was timed.
- **[verified] Workstation smoke through our wrapper:** ja-maxham optimum 37 verified in 78 s (exit 30); sts-data.135 SIGTERM incumbent verified (exit 10). Reads plain or gzip, not `.xz`.
- **[proposal]** Memory bins for both manifests: EvalMaxSAT's published peak at 75 % of 8/16/32/64 GB, memout → 64. MSE 2026 gives 1,074 / 31 / 34 / 77.
- Note: `docs/current2/EVALMAXSAT_2026_INSTALL.md`.

### N-2026-10-25-e — MSE 2025 was not held; MSE 2026 is on Zenodo with optima, per-instance EvalMaxSAT results and the EvalMaxSAT source: the better primary ρ benchmark, MSE 2023 as replication [quote + verified + inference]

- **[verified]** Zenodo 21358014 (CC-BY-4.0): exact sets of 607 + 609 instances; 952 published optima; per-run CSV with cpu, memory and verified.
- **[verified]** Published EvalMaxSAT proves 792, 391 of them in (30, 3600] s. There is no delay plateau (median 0.7–1.1 s on VBS < 1 s instances).
- **[verified]** Zenodo answers from the workstation; the cluster is untested.
- **[inference]** 2026 as the primary sample: current, same EvalMaxSAT source, clean data. About 120–235 ρ points, against 140–275 for 2023. 2023 serves as the replication sample.
- Note: `docs/current2/MSE_PUBLISHED_EXACT_RESULTS.md` §5; data: `data/raw/mse_results/mse26/`.

### N-2026-10-25-d — MSE 2023/2024 exact tracks publish proven optima and per-instance EvalMaxSAT times; our own EvalMaxSAT runs are the cleaner ρ x [quote + verified + inference + proposal]

> "are there aggregated results ot this solver somewhere? I can run it if there are less than 1000 instances in one wave on cluster for hour" (user, 2026-10-25)

- **[verified] Optima:** the 2023 exact table prints "time (cost)", with 912 proven and no conflicts between solvers. In 2024, 930 instances are proven, with values from `best_costs.csv`. 43 of the 912 2023 costs differ from the 2023 `best_costs.csv`.
- **[verified] EvalMaxSAT per instance:** 2023 plain and SCIP (425–442 solved per track); 2024 plain (weighted only) and SBVA variants (404–435).
- **[verified] 2024 plateau:** on VBS < 1 s instances, EvalMaxSAT-SBVA (UW) has median 180 s.
- **[verified] Disagreement with ours:** our `94e6774` binary disagrees in both directions on shared instances (lisbon 116 s against 850 s; rail507 timeout against 518 s).
- **[proposal]** Run our EvalMaxSAT for 1 h on VBS-proved instances: wave 2024 = 930, wave 2023 ≤ 620 after CRC dedup. Worst case 1,550 CPU-h.
- Note: `docs/current2/MSE_PUBLISHED_EXACT_RESULTS.md`; data: `data/raw/mse_results/`.

### N-2026-10-25-c — Rail-only rule built: `auto_hparams/3` R5 sets per_polish 10 on hard instances with lean v3 tables [quote + verified]

> "yes build the rail-only rule" (user, 2026-10-25)

- **[verified] Code:**
  - `src/evo/auto_hparams.py`: R5 and `/3`;
  - `src/sat/ls_v3.py`: `nbrs_plan`, which predicts (mode, bound) without
    building the tables, through the same `_mode` function the tables use;
  - `configs/strong/auto.yaml`: header only, settings unchanged.
- **[verified] Tests:** 412 passed, 16 skipped.
- **[verified] Preview:** on the 144 MSE hard-clause instances, R5 fires
  only on the 3 rail instances. The others resolve as under `/2`.
- **Not on the cluster yet.** It travels with the next batch that uses
  `configs/strong/auto.yaml`.
- Docs: `AUTO_HPARAMS.md` (R5, `/3`), `PERPOLISH_RUN.md` §6.

### N-2026-10-25-b — Batch PP10 read: per_polish 10 is not a general improvement (5 better / 12 worse, successes 19 vs 25 of 63); on setcover rail it is (gap +49–71 % → +9–15 %); rail-only rule met [verified + inference]

- **[verified]** 144/144 ok and feasible, code digest = `2763872`.
- **[verified] Pre-registered decision** (`PERPOLISH_RUN.md` §5–§6):
  - general R5: not met on any of its three tests;
  - rail-only R5′ ("lean tables → per_polish 10"): met, 3/3 better.
- **[verified] Losses of successes at 10:** min-fill (3/3 → 0/3), af-synthesis (2/3 → 0/3), quantum-circuit and scheduling (3/3 → 2/3). The only gain is preference_planning (1/3 → 2/3).
- **[inference]** On hard instances where ks2 moves reach the optimum, fewer moves per slot hurts despite 10–300× more children. Rail is the exception, because its moves fill the slot.
- **Next:** build R5′ in `auto_hparams/3` after the user's go.

### N-2026-10-25-a — Batch PP10 prepared: per_polish {200, 10} on 24 MSE hard-clause instances, with the lean-table code as a flat upload [quote + verified + proposal]

> "prepare now per polish 10 with flat upload" (user, 2026-10-25)

- **[verified] Batch:** 16 KS2 + 3 setcover rail + 5 HMSE picks (h003, h047, h011, h100, h095) × {200, 10} × 3 seeds = 144 tasks, 900 s, stop at the target; both arms on `auto_hparams/2` (R4 pop 10 + ks2).
- **[verified] Smoke (20 s):** the settings reach the solver; rail507 runs lean at 289 MB; lisbon-wedding at 10 makes 67 children against 6 at 200.
- **[verified] Upload:** 15 files (`tmp/upload_pp10/`, `arrange_pp10.sh` tested on a mock tree); the C core must be rebuilt, and a stale `.so` is refused (exit 2).
- **[decision] Reading (confirmed by the user, 2026-10-25):** R5 (per_polish 10 on every hard instance) if 10 is better on ≥ 8 and worse on ≤ 2 of the 21 non-rail instances, and (success gate, user, before results) reaches the target in more of the 63 runs than 200, with fewer successes on at most 2 instances; else a rail-only rule if 10 is better on ≥ 2 of 3 rail and worse on none.
- **[verified] `sacct` MaxRSS is blank** for the HMSE/U30 arrays (every step), so the cluster's accounting gives no peak memory; another source is needed for the RAM audit and the MSE memory bins.
- Note: `docs/current2/PERPOLISH_RUN.md`.

### N-2026-10-24-a — Prior work on anytime-vs-exact orthogonality: the closest precedent is SAT (correlation 0.26); the oracle-as-target method is IRoTS's; no MaxSAT study found [quote + verified + inference]

> "check if something like I want to do check orthogonality of anytime to exact sover - anytime : custom memetic, local search, exact RC2 or EvalMAxSAt - if something was done, mainly the pass to anytime of oracle time" (user, 2026-10-24)

- **[verified] Hoos & Stützle, "Systematic vs. Local Search for SAT"** (TR-99-06): on 1000 uf100-430 instances, the cost of R-Novelty+ (expected flips) and of Satz (search steps) correlate with 0.26, "only very slightly correlated". The coefficient type is not stated.
- **[verified] Smyth, Hoos & Stützle, IRoTS (2003)** give the local search the optimum from the complete solvers maxsat/wmaxsat and measure the run-time distribution to reach it, as our `STOP_AT_ORACLE` does. They correlate IRoTS with GLS2 only, not with exact time.
- **[verified] Not found:** a MaxSAT correlation of exact proof time with anytime time to the optimum, or an anytime budget set to the exact solver's runtime. This was a web search, not a full survey.
- **[inference] Caveat for the write-up:** the exact time includes proving optimality, while our ERT covers only finding the optimum. In SAT both costs end at the same event.
- **[verified] Not recorded now:** EvalMaxSAT's time to its first optimum `o` line. `oracle_evalmaxsat.py` reads stdout only after the process exits.
- Note: `docs/current2/RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md`.

### N-2026-10-21-l — Agenda notes and first ρ sketch: U30 is uniformly easy for the memetic and stays out of ρ; the effort floor reaches into the O900 window [quote + verified + proposal]

> "I do want to already start summing up statistics and rho. maybe if there is a reason that under 30s rc2 is also easy for my memetic to sketch the result in general, and to think of some reason to keep it out of rho statistics, maybe because of milisecond unmeasurable noise stastical." (user, 2026-10-21; full quote in the doc)

- **[verified] U30 is easy for the memetic:**
  - 83 % of runs (797/957) reach the optimum with the first polish call
    (`total_flips` = 12,500);
  - 229/319 instances have all three seeds at that floor.
- **[verified] O900 soft:** 54 % of runs and 84/245 instances are at the
  same floor.
- **[proposal] Reasons to keep U30 out of ρ:**
  - the pre-registered (30, 900] s window;
  - tied effort at the one-call floor, with millisecond TTTs in the range
    of fixed overheads;
  - RC2 times under 1 s are dominated by start-up (149/319);
  - no variance in success.
  - Report U30 descriptively instead.
- **[inference] The floor reaches into O900:** ρ with the strong solver
  needs a finer effort measure or harder instances. The options are in the
  doc, §5.4.
- **Also noted:**
  - the per_polish batch picks: h003, h047, h011, h100, h095;
  - MSE 2016 to run;
  - larger MSE 23/24 to check;
  - the "monkey patch" decision (attribute caches on the WCNF object) to
    explain.
- **Evidence:** `docs/current2/NOTES_2026-10-21_AGENDA_AND_STATS.md`.
- **[decision/plan, user, late 2026-10-21]** (doc §7):
  - the memetic ρ is computed inside the RC2 window, (30, 900] s;
  - option 1 (the first-reach flip counter) is wanted but may not be
    implemented; settle before coding;
  - EvalMaxSAT 1 h arrays (up to 1,000 jobs) on MSE 2016 and the bigger
    MSE 2023/2024 files;
  - a possible second ρ against EvalMaxSAT under 1 h on MSE (verify the
    track);
  - research optima and best-knowns for the bigger MSE files and for MSE
    2016 next session.
- **[verified + proposal] ρ on MSE** (doc §8):
  - the memetic ERT is 8.8–2,060 s on the EvalMaxSAT-proved instances, so
    there is no floor;
  - preview ρ: +0.23 (N = 11) and −0.06 (N = 18 sensitivity); N far too
    small;
  - on 53 shared instances: proved & reached 11, proved only 5, reached
    only 12, neither 25;
  - proposed: EvalMaxSAT 1 h on the 101 small-track instances not yet run
    (expected N ≈ 45–50), window (30, 3600] s, family/year strata.
- **[verified, web] The full MSE 2023/2024 sets** (doc §10):
  - 2023: exact 572 unweighted + 558 weighted (Google Drive), anytime 160 +
    179 (Helsinki);
  - 2024: exact 553 + 571, anytime 216 + 229 (Helsinki, 1.7–4.5 GB zips);
  - our best-cost tables are byte-identical to the published full-set
    tables;
  - the 2024 exact per-instance solve times (CSV) give 280 VBS proofs in
    (30, 3600] s.
- **[verified] MSE 2024 HMSE joined to the published VBS times** (doc §12):
  - 0 instances ≤ 30 s, 45 in (30, 3600] s, 29 unproved;
  - memetic ERT of successes 7.4–2,566 s, median 244 s, so off the floor;
  - the memetic reached the best-known on 12 of the 29 unproved;
  - preview ρ: −0.08 (N = 28) and +0.11 (N = 45 sensitivity), CIs about
    ±0.35.
- **[verified] MSE 2016 history** (doc §9.1):
  - no 3600 s run of any solver, and never the memetic;
  - EvalMaxSAT: 12 rows at 60–1800 s, all timeouts (set-covering, one
    Max-2-SAT);
  - RC2 300 s preview: dimacs-mod and spinglass certified in 0.006–22 s;
    bipartite max-cut capped.
- **[inference] Prediction** (doc §9.2): an MSE ρ with variation on both
  sides comes from the 2023/2024 hard instances: about 25–35 primary
  points, CI about ±0.3–0.37. MSE 2016 mostly adds memetic floor ties.
  The stronger result is the complementarity table.
- **[verified] Non-trivial results:** the broadening was non-trivial only
  for v2 (M2: 5–9 of 70; calib_2sat_sc2: 6/6). Under v3, 0 soft instances
  with a proven optimum are non-trivial (1,686/1,686).

### N-2026-10-21-k — U30 and HMSE read: every soft run with a proven optimum reached it (957/957; with O900 1,686/1,686); MSE hard-clause 129/423 at target, 0 infeasible [verified + inference]

> "I copied results" (user, 2026-10-21)

- **[verified] Provenance:** `0877898`; the src tree hash equals the
  commit's. Integrity is clean on 1,380/1,380 records.
- **[verified] U30:** 957/957 at the optimum; median TTT 0.033 s, max
  2.16 s. The five new families are all 100 %.
- **[verified] HMSE:** 129/423 runs at the target, 0 infeasible, none
  below a best-known.
  - MSE 2024: median relative gap 0.2 %, 98/222 runs at target.
  - MSE 2023: 4.4 %, 31/201.
  - Proven targets: 26/51; best-known only: 103/372.
  - 16 KS2 instances: 26/48, the same as KS2's `ks2_10` arm, with equal
    cost in 44/48 pairs.
- **[inference]** The weak spots are the unweighted 2023 families
  (gen-hyper-tw, decision-tree, logic-synthesis,
  inconsistency-measurement) and decision-tree / correlation-clustering
  in 2024. The per_polish check should include some of them.
- **Evidence:** `docs/current2/UNDER30_HARDMSE_RUN.md` §8.

### N-2026-10-21-j — Long-clause rule designed: lean tables for the setcover rail instances, exact for CC and PX [quote + verified + proposal]

> "start with the rail rule design" (user, 2026-10-21)

- **[verified] Table cost:** the v3 neighbour tables cost 61–72 bytes per
  entry while built.
  - optic: 7.65M entries, +522 MB.
  - af-synthesis: 24.7M entries, +1,433 MB.
  - The Σk(k−1) bound is at most 36.9M on all 735 non-rail instances we
    have, against 641M–1,143M on rail.
- **[verified] Rail structure:** 507–582 rows of 610–807 variables on
  average (max 8,919). Each variable is in 6.5–7.2 rows (max 12).
- **[proposal] Lean mode above 50M:**
  - CC by walking the flipped variable's clauses: the same conf state,
    the same run.
  - PX components by union–find over clauses: the same components.
  - Walk mutation by rejection sampling: the same distribution, a
    different random stream.
  - Tests, smoke and a 9-task batch are planned.
- **Evidence:** `docs/current2/LONG_CLAUSE_RULE_DESIGN.md`.
- **[verified] Built 2026-10-21 as recommended** (user: "do the recommended,
  dont do peak memory").
  - Tests: 28 new; full suite 403 passed / 16 skipped; all existing
    equality tests unchanged.
  - Rail smoke, 60 s: peak 221–284 MB (was over 7.3 GB). Cost
    513/603/654 against best-known 174/182/211.
  - 57 of 60 s went to feasible SAT moves, with 0 polish flips.
  - The C source changed, so the cluster `.so` needs a rebuild.
- **[verified] `hard.moves.per_polish` on rail** (user: "run the per_polish
  test on the rails"; 60 s, seed 1):
  - default 200: cost 513 / 603 / 654, polish 0 flips;
  - 50: 224 / 221 / 275;
  - 10: 218 / 216 / 265, against best-known 174 / 182 / 211.
  - Reserving slot time for the polish cuts the cost 2.3–2.8×.
  - **[inference]** One seed at 60 s, rail only; design doc §9.

### N-2026-10-21-i — Batches U30 (319 instances proved in < 30 s) and HMSE (141 MSE hard-clause instances) prepared; setcover rail is too dense for the v3 tables; upload without rsync [quote + verified + decision]

> "write manifest for the hard clauses, and manifest for the not-run on memetic under 30s rc2 or EvalMaxSat, put all the new files except in needed dirs, like data or scripts or code, the files I dont have on cluster. make copy of them in some tmp folder so i can move it to mobaexterm, then I give you tree from there and you give me script back there to arrange them in folders. because I dont use rsync" (user, 2026-10-21)
>
> "drop the 3 rail instances, regenerate hmse manifest" (user, 2026-10-21)

- **[verified] U30:** per-formula selection.
  - Rule: fastest proof < 30 s, optimum > 0, no hard clauses, not in O900.
  - Result: 319 instances, 957 tasks. Every source is RC2.
  - Five families are new to the strong solver: jnh, unsat_uuf_diff,
    dubois, pret, bf.
  - Smoke: 24/24 at the oracle in ≤ 0.33 s.
  - 25 formulas proved only in 959–3078 s are in neither O900 nor U30.
- **[verified] HMSE:** MSE 2023/2024 files with hard clauses and a
  best-known.
  - Excluded: best-known −1 (5), soft-only (17), and the 3 setcover rail
    files.
  - Result: 141 instances, 423 tasks. Targets: 17 proven, 124
    best-known-only.
  - Config: the same `configs/strong/auto.yaml` (`auto_hparams/2`).
- **[verified] Setcover rail:**
  - Hard clauses of 7,753–8,919 variables make the v3 neighbour sets
    (`ls_v3._V3Static`) 0.64–1.14 billion entries. The next densest
    instance has 37M.
  - Measured: 7.3 GB at 34–38 s, still building, then `MemoryError`.
  - No exact solver has proved them: EvalMaxSAT timed out on rail507, and
    the other two were outside the s1 sample.
  - A long-clause cap on the neighbour lists is a possible later fix.
- **[verified] Local smokes crashed WSL twice:**
  - The OOM killer struck inside init.scope, and the distro shut down.
  - Cause 1: 7 parallel runs at 7.8 GB.
  - Cause 2: two Claude sessions reran rail at once.
  - Local runs are now capped and serialized; memory note
    `workstation-wsl-memory-limits`.
- **[decision] Upload without rsync:**
  - `scripts/make_flat_upload.py` copies the needed files that the
    cluster lacks into one flat folder with a map.
  - `tmp/arrange_u30_hmse.sh` and `tmp/arrange_hmse2.sh` (shell only,
    tested on a mock home) move them into the tree and check them with
    `sha256sum -c`.
- **Evidence:** `docs/current2/UNDER30_HARDMSE_RUN.md`.

### N-2026-10-21-h — `auto_hparams/2` (ks2 + pop 10 on hard instances), aggregate fixed; drmx-cryptogen is a search limit, not a misclassification [quote + verified + inference + decision]

> "use ks2 with pop10 on hard, fix crush, dont prepare 900s batch, look into soft rule for drmx-cryptgen" (user, 2026-10-21)

- **[verified] `auto_hparams/2`:** new rule R4 sets `ea.pop_size` 10 and
  `hard.moves.keep_sat: ks2` when the solved instance has hard clauses.
  - `merge()` is now deep, so other `hard.moves` keys survive.
  - Soft instances resolve exactly as under `/1`.
  - `configs/strong/auto.yaml` was regenerated (header only).
  - The preview prints pop and keep_sat.
  - R4 smoke (real runner, C core, 120 s, seed 1): mbd-b14 reached 24 in
    19.4 s, and quantum-circuit reached 24 in 106.8 s. Both are 0/3 under
    `/1` in O900.
- **[verified] `m2_results.py aggregate`:**
  - Sidecars without `analysis_group`, `m` or `arm` now default to family,
    "" and config_id.
  - New columns `hp_pop_size` and `hp_keep_sat`.
  - Re-run on O900 and KS2, the counts equal the scratch readout.
  - Tests: +3 in `test_auto_hparams.py` (R4, deep merge, run-time values),
    new `tests/test_m2_results.py`. Suite 371 passed / 20 skipped.
  - Upload hashes for O900 and KS2 are now stale; a new batch regenerates
    its own.
- **[verified] drmx-cryptogen structure:**
  - 1,600 vars.
  - 1,600 positive unit clauses of weight 1 (the objective).
  - 7,844 clauses of weight 1,601 = 1 + the total light weight, so in effect
    they are hard: 200 units, 800 binary, 1,836 ternary, 5,008 of length 5.
  - Optimum 800.
  - The rule classes it `soft_weighted` (ζ 1650). Walk mutation k 16 breaks
    about 25 heavy clauses per child (damage ≈ 40k).
  - No other MSE instance here has such a tier. The only others,
    causal-discovery and preference_planning, have trivial one-clause tiers.
- **[verified] Workstation grid on drmx 1** (300 s, seeds 1–2, 8–10 runs in
  parallel). Reference: the current rule gave 835 at 300 s; O900 gave
  825–832 at 900 s.
  - **Heavy tier made hard:**
    - hard tree with ks2 + pop 10: 866–876 (279 of 300 s in SAT moves, 2 %
      improving);
    - no moves: 851–853;
    - 20 moves per polish: 863;
    - DLS only (`hard_mode: off`, PMS weights), pop 40 or 10: 838–849;
    - the same with k 4: 857;
    - WPMS weights (ζ 1, h_inc 3): 829.
  - **Soft path:**
    - k 4: 836–843;
    - **1M flips per call (`flips_only`): 817, 820**;
    - **`ls.weights: run`: 820, 820**;
    - both together: 886–894 (worse).
  - **900 s, both instances:**
    - 1M flips: 815–818 (5 runs);
    - `weights: run`: 811–820 (5 runs);
    - 0/10 at 800.
- **[inference]**
  - Hardening is exact here, but it does not help: the instance is a
    cardinality-style problem where one-literal SAT moves only swap.
  - Longer DLS trajectories, through either knob, halve the gap (about 28 →
    about 16) and then stall.
  - drmx is a search limit for this LS; EvalMaxSAT proves it in 372–392 s.
- **[decision, user 2026-10-21] No new `soft_weighted` rule.**
  > "meanwhile i dont think new rule is justified"
  - `ls.weights: run` and 1M flips per call stay recorded here as options.
  - Evidence: one family, workstation only, still 0/10 at the optimum.
  - Hardening dominating tiers is not adopted either: it is exact, but it
    measured worse.
- Scratch configs and records:
  `/tmp/claude-1000/-home-mashe-maxsat-lab-new-maxsat-lab/e5beb1d1-73dd-43a5-bd42-58d37a46e4e9/scratchpad/drmx/`.

### N-2026-10-21-g — Batch KS2 read: ks2 doubles MSE successes (12 → 24–26 of 48); the pre-registered rule holds at pop 10 (13/0), not at pop 40 (10/3) [verified + inference]

> "copied results" (user, 2026-10-21)

- **[verified]** 192/192 `ok`, all feasible, none below the optimum. Runs
  at the optimum: m40 12, m10 13, ks2_40 24, ks2_10 26.
  - ks2 reaches the optimum 3/3 in both populations on mbd-b14,
    quantum-circuit, af-synthesis and scheduling. M gets at most 1/3 there.
  - It is close on lisbon (396–397 vs 401–410) and inconsistency (64–65 vs
    73–78).
- **[verified] Rule (§5 of the run doc):**
  - ks2_10 vs m10: better 13, worse 0;
  - ks2_40 vs m40: better 10, worse 3 (min-fill, MaxSATQueries, ja-kemeny)
    → **not met at pop 40**;
  - population: no effect by the rule.
- **[inference]** MaxSATQueries stays near its Glucose start in every arm,
  so its ordering is noise. ks2_10 against today's default m40 is 13 / 2
  (post hoc). Making ks2 (with pop 10) the `hparams: auto` default for
  hard-clause instances is the user's call.
- Record: `docs/current2/KS2_CHECK_RUN.md` §6.

### N-2026-10-21-f — Batch O900 read: the strong solver reaches every soft oracle (729/729, median 0.05 s); MSE 7/30, drmx-cryptogen 0/6 [verified + inference]

> "copied results" (user, 2026-10-21)

- **[verified]** 759/759 `ok`, C core built on the cluster, 5.9 h wall time
  in total.
- **243 soft non-MSE instances: 729/729 runs reached the optimum.**
  - TTT median 0.05 s, 99th percentile 4.6 s, maximum 6.1 s (s253).
  - s253 was 0/3 under v2 after 190M flips (N-2026-10-18-d).
- **MSE: 7/30.**
  - Causal-discovery 3/3, ja-maxham 2/3, ja-kemeny and preference 1/3.
  - mbd, quantum, lisbon and MaxSATQueries 0/3.
  - The soft-weighted drmx-cryptogen is 0/6 at 825–832 vs 800.
- **[verified]** `m2_results.py aggregate` crashes on these manifests
  (`KeyError: 'analysis_group'`). `pending` works. Not fixed yet.
- **[inference]**
  - Instances that take RC2 30–900 s to prove are mostly one LS call for
    DLS+CC: the median run made 1 child. This pool does not stress the EA.
  - The weak spots are the `soft_weighted` rule (drmx) and the hard-clause
    move, which batch KS2 addresses.
- Record: `docs/current2/ORACLE900_RUN.md` §7.

### N-2026-10-21-e — KS2 built in the strong tree and a 192-task cluster check prepared [quote + verified + inference]

> "prepare me ks2 check for cluster" (user, 2026-10-21)

- **[verified]** `hard.moves.keep_sat: none | ks | ks2` is in
  `src/evo/hard.py` (default `none` = today's move, byte-identical). 14 new
  tests; suite 369 passed / 20 skipped. In-tree ks2 on lisbon, 120 s:
  400 vs 423.
- **[verified]** Batch KS2: the 16 MSE instances with hard clauses and an
  EvalMaxSAT-proven optimum × {M, ks2} × pop {40, 10} × 3 seeds = 192
  tasks, ≤ 51.2 CPU-h. Smoke (ks2_10, 60 s, 48 runs): all feasible,
  ≤ 1.6 GB. Record: `docs/current2/KS2_CHECK_RUN.md`; pre-registered rule
  in §5.
- **[inference]** ks does nothing where the soft clauses are not units
  (optimizing-BDDs, preference_planning); the batch measures M there.

### N-2026-10-21-d — lisbon-wedding: origin, who solved it, and workstation experiments; slot length does not help, a keep-satisfied SAT move does [quote + source + verified + inference]

> "what do you think can enhance lisbon wedding? does the rc2/evalmaxsat solved it, from what aggregation is it? can we enhance the hyperparameter, with you doing experiments now - for more than 3.5 seconds, in cases with hundreds thousand clauses like libon wedding" (user, 2026-10-21)

- **[source]** R. Martins and J. Sherry, "Lisbon Wedding: Seating
  arrangements using MaxSAT", *MaxSAT Evaluation 2017: Solver and Benchmark
  Descriptions*, Univ. Helsinki B-2017-2, pp. 25–26 (justinesherry.com/papers/martins-mse17.pdf).
  - Guest-at-table variables; exactly one table per guest; table sizes
    between l and u; conflicting guests apart; a seated guest implies their
    labels at the table.
  - Soft: minimise weighted labels per table (unit soft clauses).
  - Built with Open-WBO: ladder, modulo-totalizer and generalised-totalizer
    encodings.
  - 9-18: 30,553 vars, 204,985 hard, 396 unit soft clauses, 3 weights
    (1–100).
- **[verified]** EvalMaxSAT proved 395 in 116.3 s (s1). It timed out at
  3600 s on lisbon 4-17 and 6-19. RC2 never ran on MSE 2024.
- **[verified]** Experiments: workstation, 300 s, stop at 395, C core,
  `hparams: auto`, 8–12 runs in parallel.
  - **Today's move M** (11 runs: slot 3.5/10/30/60 s, pop 4/10/40, conflict
    budget 50k, noise 0): 413–440.
    - Slot length gives no gain: about 4,000 SAT moves per 300 s whatever
      the slot. The slot only redistributes them among children.
    - Pop 10 is slightly better than 40 (413, 418 vs 425, 432; 9 vs 2
      generations).
  - **Keep-satisfied move** (scratch patch, tree untouched): assume the
    target soft literal plus every currently satisfied unit soft; fall back
    to M on UNSAT.
    - KS: 399, 399.
    - KS2 (on UNSAT, drop the core's kept literals and retry once): 397, 398,
      397 (pop 10), 400 (pop 40).
    - About 2× the moves per second, because the UNSAT calls are fast.
  - **Other large MSE, seed 1, pop 10, M vs KS2:**
    - mbd-b14: 33 vs **24 = opt (72 s)**;
    - quantum-circuit: 51 vs **24 = opt (288 s)**;
    - ja-kemeny: 558 vs 562;
    - causal and preference: both reach the optimum;
    - MaxSATQueries: both stay at the Glucose start, 43,875 (opt 31,514).
- **[verified, not a bug]** `best_soft_weight_reported` is the satisfied
  soft weight on the hard path. Reported + `best_cost` = 97,392 = the total
  in all three MaxSATQueries runs.
- **[inference]** On encoded industrial instances the hard machinery is
  bound by SAT-call throughput; the move operator matters, not the slot.
  KS2 is not yet in the tree; it needs implementation, tests and 3-seed
  runs.

### N-2026-10-21-c — Batch O900 prepared: strong solver on 253 instances with an optimum proven in < 900 s; selection per formula [quote + verified + inference]

> "strong solver only, instances rc2 is above 30s, kernel on, prepare with oracle on, manifest for instances we have oracle in 900s, from rc2 or evalmaxsat" (user, 2026-10-21)

- **[verified]** Selection: RC2's fastest certified run in [30, 900) s, or
  EvalMaxSAT optimal in < 900 s (unless RC2 < 30 s). 253 instances (RC2 243,
  EvalMaxSAT 9, both 1), 759 tasks, ≤ 202 CPU-h. Record:
  `docs/current2/ORACLE900_RUN.md`.
- **[verified]** File-level dedupe was not enough. SATLIB's normalised
  uuf200 files and an older raw copy are the same formulas with different
  bytes: 4 were selected twice, and 2 entered via the raw copy at 31–36 s
  although RC2 takes < 30 s on the SATLIB copy. The rules now apply per
  parsed formula.
- **[verified] Smoke** (seed 1, 60 s): 84/84 soft instances at the oracle in
  ≤ 3.7 s; MSE 3/10 at the oracle, all feasible. On lisbon-wedding,
  feasible moves M take every slot, so the B1–B5 polish makes 0 flips there.

### N-2026-10-21-b — Instance-aware hyperparameters for v3 (`auto_hparams/1`), chosen at run time: rules, evidence, pool dry run [quote + verified + inference]

> "write preprocessing script that passes to solver optimal hyperparameters, whether hard/soft or if small number of vars versus tens thousands of vars and clauses" (user, 2026-10-21)

- Built in `cluster_staging_maxsat_strong/` and chosen **at run time**
  (user: "build the run-time version"). A config `hparams: auto` makes the
  shard runner choose the values after its gate and merge them in memory;
  one batch config, `configs/strong/auto.yaml`; record field `hparams`
  (schema 6). 22 tests; suite 351 passed / 24 skipped. Record:
  `docs/current2/AUTO_HPARAMS.md`. Search code unchanged.
- **[verified]** Real 60 s runs with the C core: the choice takes 0.1–6 ms.
  s256 (n 64,000 → kernel 572) reaches 13 in 0.42 s, uuf200-022 reaches 1 in
  0.06 s, ja-385 (hard) ends at 38 vs 37, feasible.
- **[verified]** Sizes are taken on the instance the EA solves (the kernel
  when the gate passes). "Weighted" is judged on the original instance:
  kernel merging made 21 unweighted instances look weighted, a bug found in
  the dry run and fixed.
- **[verified] Dry run on the 582-instance pool:** 25 distinct configs. Class:
  572 soft unweighted, 6 hard weighted, 2 hard unweighted, 2 soft weighted.
  Kernel on 85 instances. k = 16 on only 21 instances.
- **[inference]** The flips per call stay 12,500: Stage L1's 0.8–1.6M was
  measured under 2 % mutation, and B3 removes the n-proportional repair. The
  k(n) shrink below n 400 and the SATLike classes for MSE are untested here.

### N-2026-10-21-a — EvalMaxSAT in a publication: licence, what to cite; the "solved < 900 s" pool counted [source + verified + proposal]

> "check the web, If I can use like this EvalMAxSat in my research which might be published, what I need to cite" (user, 2026-10-21)

- **[verified: local copy]** `solver_EvalMaxSat/EvalMaxSAT/` is an unmodified
  clone of github.com/FlorentAvellaneda/EvalMaxSAT, commit `94e6774`
  (2025-11-05). LICENSE is GPL-3.0. Bundled: CaDiCaL, MCQD, CLI11 (also
  MaLib and glucose under `lib/`).
- **[source + inference, not legal advice]** GPL-3.0 restricts distributing
  the program or derived code, not running it. Running the unmodified binary
  as a baseline and publishing its results needs no permission. Obligations
  arise only if a modified EvalMaxSAT is shipped (e.g. in an artifact
  repository): then its source goes with it, under GPL-3.0. Our driver
  (`oracle_evalmaxsat.py`) calls the binary as a separate process and is not
  a derived work of it [inference].
- **What to cite:**
  - EvalMaxSAT: F. Avellaneda, "A short description of the solver
    EvalMaxSAT", *MaxSAT Evaluation 2020: Solver and Benchmark
    Descriptions*, p. 8 [source: citing papers and Google Scholar; volume
    series and number not verified]. The MSE 2023 descriptions volume
    (Berg, Järvisalo, Martins, Niskanen, eds., University of Helsinki) holds
    an `EvalMaxSAT_2023` description [source: file name in the PDF; text not
    read]. Cite the year that matches the version, plus the commit hash.
  - The README credits CaDiCaL (Biere et al., SAT Competition 2020), OLL
    (Morgado, Dodaro, Marques-Silva, CP 2014), and the PySAT totalizer
    (Ignatiev, Morgado, Marques-Silva, SAT 2018). RC2 (Ignatiev, Morgado,
    Marques-Silva, JSAT 2019) and PySAT are cited anyway, because RC2 is the
    other reference solver.
- **[verified: profile rows]** Pool "proven optimal by RC2 in < 900 s":
  838 profiled instance paths, 606 certified < 900 s, of which 26 have cost
  0. After dropping cost 0 and deduplicating by content: **573 instances**
  (149 under 1 s, 174 at 1–30 s, 201 at 30–300 s, 49 at 300–900 s).
  EvalMaxSAT (s1, 60 MSE tasks) proved optimal in < 900 s on **10** (2 mse23,
  8 mse24). RC2 has 1 MSE 2023 instance < 900 s (ja-maxham, also solved by
  EvalMaxSAT). Union ≈ **582**.
- **[verified]** EvalMaxSAT has run only on those 60 MSE tasks. A comparison
  with EvalMaxSAT on the whole pool needs an EvalMaxSAT run on it.

### N-2026-10-18-d — Kern batch read: 15/18, prediction held exactly; s253 0/3 after 190M flips on 434 variables [verified]

> "yes read out the kern results" (user, 2026-10-18)

- Batch: `results/calib_2sat_sc2_kern`, `MAXSAT_GIT_SHA=ad19012`, 18/18
  valid. Readout: `docs/current2/KERNEL_MEMETIC_RUN.md` §6.
- **[verified]** Successes: s251, s255, s256, s257, s258 each 3/3, with
  median TTT 0.5–2.8 s (kernel time included, 0.13–0.88 s). s253 0/3
  (15, 16, 15 vs c\* 14). The paired raw arms (m2v2: 12.5k and 200k flips)
  were 0/18 each, at +2 to +29.
- **[verified]** s253: about 190M flips, 15,000 children and 400 generations
  per seed on a 434-variable kernel, never at 14. RC2 proves 14 in 58 s on
  that kernel. This is a search-quality failure. The strong tree's `allC`
  solved it in 5.8 s in the 60 s workstation smoke (1 seed); S1 tests 3
  seeds.
- **[inference]** 13 of 15 successes come in generation 1: on these kernels
  the EA works as a multistart. The grid's kernels are too small to separate
  memetic from multistart (direction C: larger n·ε³).

### N-2026-10-18-c — Stronger memetic built in a third tree; C core 8–23× faster; smoke solves s253 on its kernel and two raw n 64,000 instances; batch S1 prepared [quote + verified + inference]

> "on cluster, compile once, I think , I think there aint no python script on login node, and anyhow it can be compiled in saparate job. add the karnileztion and things arent in hard now" (user, 2026-10-18)

- Record: `docs/current2/STRONG_MEMETIC_S1_RUN.md`; tree record
  `cluster_staging_maxsat_strong/PROVENANCE.md`. Committed `16589fb`.
- **[verified] Built:** `impl: v3` with `hard_mode: auto`. B1 tabu / CC; B2
  SATLike-style DLS (optional CC); B3 mutation count / walk / diff; B4
  partition crossover; B5 C twin (portable RNG, built once per tree, stale
  builds refused).
- **[verified] Exactness:**
  - v3 without keys == staging `impl: v2` (subprocess against that tree) and
    == `impl: hard`;
  - C == Python twin flip for flip;
  - the PX child == best of 2^q (brute force);
  - DLS state == full recompute.
  - 329 passed / 24 skipped.
- **[verified] Speed** (one call, workstation): WalkSAT C 4.6M flips/s vs v2
  0.55M; DLS C 2.6M vs Python 0.11M. One DLS call from a random start
  reaches c\* 12 on raw s251.
- **[verified] Smoke** (60 s, seed 1):
  - kernel: `base` 5/6, `all` 5/6, `allC` **6/6** (s253 in 5.8 s, a first);
  - raw: `base` 0/6 (+10…+81), `all` 0/6 (+1…+31), `allC` **2/6**
    (s256, s257 at n 64,000), the rest +1/+2.
  - Mutation damage 198–644 → 6.5–12.4 clauses with walk k 16.
  - PX q: thousands on raw, 12–80 on kernels.
- **Batch S1:** 9 arms × raw/kern × 6 × 3 = 324 tasks, ≤ 86.4 CPU-h. B5 is in
  the batch as arm `allC` (a deviation from design §8.3, which had it
  separate). Commands in §4.2 there. Not submitted.

### N-2026-10-18-b — Stronger memetic design: B1–B5 explained, their interactions, and the build plan for a third staging tree [quote + source + inference + proposal]

> "write it, also do the reasoning of interactions- I want you next step implement all the ideas for stronger solver in new folder analogue to the cluster_staging_maxsat/_hard in 3rd folder" (user, 2026-10-18)

- Document: `docs/current2/STRONGER_MEMETIC_DESIGN.md`. Design only; nothing built.
- **[source]** SATLike (IJCAI 2018, full text): two modes (BMS over decreasing
  variables; when stuck, weight update and a falsified-clause pick);
  Weighting-PMS with h_inc, soft limit ζ and smoothing sp; published values
  per benchmark family. Tabu (WalkSAT/TABU, IRoTS n/10 + 4), configuration
  checking (Cai and Su; CCLS), PX (FOGA 2015; PXSAT, GECCO 2018), SAPS/PAWS
  checked at abstract level.
- **[inference] The c\* > 0 catch:** with no hard clauses, SATLike's ζ = 1
  never changes a weight, and at the optimum the c\* falsified clauses keep
  gaining weight. So we need ζ > 1, the best tracked on the true cost, and
  smoothing.
- **[derived]** PX is exact for MaxSAT: every clause's differing variables
  lie in one component, so the child is the best of 2^q and ≥ both parents
  (also lexicographically with hard clauses).
- **[inference] Interactions (§6):** B2's effect on raw needs B3 (weighting
  acts only when stuck; after a fixed-rate mutation the polish is repairing,
  not stuck). Tabu can fight weighting (CC or a tie-break only in the DLS
  core). Small local mutation makes PX's components, and heavy mutation
  wastes PX's gain. PX is only as good as the local optima it combines. B5
  last, with the C core equal to a Python twin on a portable RNG.
- **[proposal]** Tree `cluster_staging_maxsat_strong/` (copy of
  `cluster_staging_maxsat/`, `impl: v3`). Steps S1–S7 with stop-on-failure.
  First batch: leave-one-out, 8 arms × 6 instances × 3 seeds × raw/kernel =
  288 tasks, ≤ 76.8 CPU-h. Awaiting go, the tree name, and the cluster
  compiler check (`which cc gcc clang`).
- **Update 2026-10-18 (§8.0 there):**
  - The user approved the name and asked to base the tree on the hard tree.
  - The cluster has gcc 11.5.0.
  - **[verified]** `impl: hard` on soft-only s251 (30 s): cost 49 with 9
    children, against v2's 23 with 365. Feasible moves M take 28.6 of 30 s,
    because each one-literal move costs a Glucose call plus O(m) Python. So
    the base is the hard tree, the hard machinery engages only when the
    solved instance has hard clauses (`hard_mode: auto`), and the kernel,
    `polish_cap` and the results tooling are ported from staging.
  - B5 is unaffected: Glucose, R and M sit outside the flip loop. The C
    cores carry the `is_hard` branches, with C == Python-twin tests that
    include hard clauses.

### N-2026-10-18-a — Milestone A built: the memetic kernelises behind the gate; 18-task batch prepared; direction B proposed [quote + verified + proposal]

> "what you purpose in optimizing memetic - to stronger memetic? using which ideas? prepare cluster run for the max2sat, with the kernelization, tell me files to upload to cluster and commands" (user, 2026-10-18)

- **Built** (staging): `src/sat/kernel.py` (promoted from the diagnostic, same
  rules), opt-in `preprocess: kernel` in `run_memetic_shard.py` (schema 4), the
  config `memetic_deeppolish_p40_ls3p5_kern_v2.yaml`, `--plan kern` (18 tasks),
  and a `preprocess` check in `m2_results.py`. Kernelise time counts inside the
  budget and the TTT; the cost is scored on the original clauses.
- **[verified]** Brute force: for every kernel assignment, the lifted cost is
  exactly kernel cost + constant (600 random instances with hard clauses and
  weights). Staging suite 307 passed / 3 skipped.
- **[verified] Smoke** (60 s, seed 1): s251, s255, s256, s257, s258 reach c\*
  in 0.3–1.5 s including kernelising; s253 ends at 15 (c\* 14). The raw arm
  went 0/18 in 900 s on the same instances and seeds (m2v2 batch).
- **Committed and pushed 2026-10-18: `754392a`, then `ad19012`** (Slurm throttle default 30 → 1000, user's go; `MAXSAT_GIT_SHA=ad19012`); not submitted. **Upload verified 2026-10-18** from `cluster_hashes_20261018.txt`: 38/38 upload hashes and the `src` digest (`7d7818aa…`) match; ready to submit. Upload list, hashes and commands:
  `docs/current2/KERNEL_MEMETIC_RUN.md` §4.
- **[inference] Direction B** (§5 there): B1 tabu, B2 clause-weighting local
  search, B3 distance-aware mutation, B4 partition crossover, B5 compiled loop.
  s253 (a 434-variable kernel the memetic misses by 1, RC2 58 s) is the first
  test case. Nothing built.

### N-2026-10-14-k — Reminder, after the current enhancements: fixed-rate mutation sends children far from the optimum on large instances [quote + reminder]

> "write note to address mutation distancing away from optimum when we get to relevant batches that this problem might be arised" (user, 2026-10-14)
> "discard check, only put it somewhere in notes for me to remind, after i finish the current enhancements" (user, 2026-10-14)

- **Reminder only; no check and no batch step.** Raise it after the user
  finishes the current enhancements.
- The problem: `pmutate` 0.02 gives about 0.02 · n flips per child. At
  n 64,000 one mutation takes an optimal assignment from 13 to 832–948
  unsatisfied clauses (N-2026-10-14-i; `RESEARCH_NOTES_SOLVER_DIRECTIONS.md`
  §9.1).
- Where it may come up: large-n memetic runs on the original formula
  (calib_2sat_sc2 raw, milestone A's fallback, direction C), and the MSE
  hard-clause memetic. There the `mutate1` guard may instead make mutation
  almost a no-op (not measured).
- Candidate fixes are listed in §9.1 there: a fixed flip count, localised
  mutation, flips where the parents differ.

### N-2026-10-14-j — New documents go to docs/current2/; the hubs stay here [quote + decision]

> "create new current docs folder in which you will put new docs from now" (user, 2026-10-14)

- From now on, new documents (including new `RESEARCH_NOTES_<TOPIC>.md`) are
  created in `docs/current2/`, and indexed in §1 above with that path.
- Existing `docs/current/` documents stay and are updated in place (code,
  configs and upload lists refer to their paths).
- The hubs `NEXT_SESSION_CONTEXT.md`, `RESEARCH_NOTES.md` and
  `READING_LIST.md` stay in `docs/current/`.
- Rule: `docs/current2/README.md`.

### N-2026-10-14-i — Fixed-rate mutation wrecks big instances (13 → 832–948 unsat at n 64k); tabu parameters and an implementation sketch [quote + verified + proposal]

> "keep the mutation damaging conclusion for big instances, and tabu parameters and might be implementation in notes" (user, 2026-10-14)

- **[verified]** One mutation at pmutate 0.02 applied to an optimal
  assignment:
  - n 64,000: 13 → 832–948 unsatisfied clauses;
  - n 16,000: 12 → 255–311.
  The damage grows with n while c\* does not. On big instances pmutate
  must be a fixed count or local, not a per-variable rate.
- **Tabu (proposal, not built):** tenure, random tenure, aspiration,
  the all-tabu rule and noise, as parameters. Implementation: `last_flip[v]`
  in `walksat_polish_v2`, opt-in, with today's behaviour unchanged when off.
  A candidate arm in direction B. Literature values unverified.
- **Also answered** (chat): why a pure variable can be set and its
  clauses dropped. Setting it never breaks a clause, so some optimum has
  it set that way.
- `RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §9.

### N-2026-10-14-h — No preprocessing for RC2 (it belongs in a solver's core; ours has it); Stage L1b on hold; B and C to be explained later [quote + decision]

> "1. no preprocessing on rc2 - explain it that it is should have been included in core solver of rc2, it is problem of rc2 solver, and in our there is enhancement. 2. time grid on hold, meanwhile we will try to get results with solver enhancement. 3. later I would like explanation on B and C" (user, 2026-10-14)

- RC2 stays as distributed, on the original formula. Missing exact
  preprocessing is RC2's limitation; gated kernelising is part of our
  memetic solver.
- Report: name the arms explicitly, count kernelise time in the memetic's
  budget and TTT, and give the kernel sizes and RC2's kernel times as
  context.
- Stage L1b on hold; next results from direction A.
- To-do: explain B and C to the user.
- `RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §8.3.

### N-2026-10-14-g — Kernelising mainly helps sparse Max-2-SAT, which is exactly the eligible RC2 grid; the memetic uses it there, behind a quick worth-it check [quote + decision + verified]

> "write in research flow a note that karnelization mainly enhances not dense 2sat on which we got eligible grid points from rc2, and didn't pass memetic without it. so I think for this case of grid we do need kernnilization preprocessing, maybe check, even if it is on - that it is not dense 2sat, or other very rapid check that its worth this kind of processing" (user, 2026-10-14)

- **Note:** the eligible calib_2sat_sc2 grid points are sparse Max-2-SAT
  (2.5 occurrences per variable). There kernelising removes 97–99.4% of the
  variables.
  - Without it the memetic failed at n 64,000 (0/54 Stage L1 runs).
  - With it, c\* was reached in ≤ 0.7 s on all three.
  - On dense 2-SAT, 3-SAT, crafted and MSE instances it removes ≤ 22%.
- **[decision]** For this grid the memetic runs with kernelising, opt-in.
- **Gate:** the screen `s` (the fraction of variables removable at
  once, ≤ 0.1 s) must be ≥ 20%. It is 61–65% on the grid and ≤ 13.1% on
  every non-sparse family sampled. Then the kernel must remove ≥ 20%, with
  no clause longer than the original. Otherwise the run uses the original
  formula.
- **Open:** RC2 on the kernel too (fairness); Stage L1b hold or baseline;
  then B or C.
- `RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §8.

### N-2026-10-14-f — Kernelising does not carry over to 3-SAT; the stronger-solver components do [quote + verified + inference]

> "will the kernelising and stronger solver work on 3sat, and in general not only on 2sat" (user, 2026-10-14)

- **[verified]** Generalised diagnostic (any clause length, hard clauses).
  A reconstruction bug for unequal or hard weights was found by brute force
  and fixed; now 0/3,000 mismatches. The calib_2sat_sc2 results were
  unaffected (all weights 1).
- **[verified]** Reduction:
  - random 3-SAT/4-SAT, dense Max-2-SAT, crafted maxcut, jnh: 0–1.2%;
  - MSE industrial: 5–22%, with long resolvents;
  - Max-2-SAT near the threshold: 97–99.5%.
- **[inference]** Kernelising is family-specific: it needs about 2
  occurrences per variable, while 3-SAT has about 12.8. The B components
  (clause weighting, compiled loop, localised mutation) are general.
  Partition crossover is general, but its benefit depends on the
  instance decomposing.
- `RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §7.

### N-2026-10-14-e — The n 64,000 instances reduce exactly to 300–572-variable kernels; the unchanged memetic solves those in under a second [quote + verified + inference]

> "actually i want you to think what direction to research or what to optimize in solver furthe, maybe with new version, you can if you think needed copy to new src folder, i want to try to get results on 64000 vars, with memetic , if the rc2 achieved optimum in 900s" (user, 2026-10-14)

- **[verified]** Pure-literal elimination plus degree-2 MaxSAT resolution
  (`scripts/diag_max2sat_kernel.py --verify`) leaves 300 / 332 / 572
  variables at n 64,000 and 420–434 at n 16,000. The rebuilt full
  assignment's cost equals the kernel optimum on all 15 batch instances,
  and equals RC2's c\* on the 6 eligible ones.
- **[verified, 1 seed]** The pre-registered memetic arm on the kernels
  reaches c\* on all three n 64,000 instances in 0.03–0.70 s, and on 2 of 3
  at n 16,000. s253 ends at 15 against 14 in 120 s; it is also RC2's
  hardest (58 s on the kernel).
- **[inference]** The best flips per call in Stage L1 does not depend on n
  because the kernels are about the same size at both n. n is nominal for
  these cells.
- **Proposal:** direction A, exact preprocessing in front of the memetic,
  then B or C. Stage L1b on hold pending the user's decision.
  `RESEARCH_NOTES_SOLVER_DIRECTIONS.md`.

### N-2026-10-14-d — HP-1 Stage L1b prepared: 72-task time grid, 6 / 8 / 10 / 15 s per local search [quote + verified: prepared, not submitted]

> "make new manifest and commands, or configs - with 6, 8 10 15 seconds per local search, without stopping on flips budget" (user, 2026-10-14)

- 4 configs `memetic_deeppolish_p40_ls{6,8,10,15}_tcap_v2` (`polish_cap: time`,
  flip limit ignored); manifest `manifest_calib_2sat_sc2_tgrid`, 72 tasks,
  ≤ 19.2 CPU-h; builder `--plan tgrid` checks `ls.time_limit_s`.
- 4 new tests (suite 282 passed); 20 s smoke OK; dry run OK; upload list
  and `sha256sum -c` file. Commands in
  `HYPERPARAMETER_CALIBRATION_PLAN.md` §0d.2.

### N-2026-10-14-c — HP-1 Stage L1 read: best 1.6M flips at n 16,000, 800k at n 64,000; best flips per call about size-independent [verified + inference]

- 108/108 clean. §0b.4 rule: n 16,000 → 1.6M (c = 100; 3/9 successes,
  the only grid successes); n 64,000 → 800k (c = 12.5) by the 0.05 tie rule
  (no success in any arm).
- **[inference]** c falls with n, but flips per call (0.8–1.6M, 2–5 s per
  call) does not: at 900 s the limit looks set by call length against
  generations, not by n. `max(12500, c·n)` needs a decision. Plan §0d.1.

### N-2026-10-14-b — HP-1 Stage L1 prepared: 108-task c grid with flip-only polish [decision + verified: prepared, not submitted]

- **§0b.7 answered (user, 2026-10-14):** flips_only; re-run all 90;
  include the tcap reference arm.
- **Prepared:** 5 grid configs (200k–3.2M, `polish_cap: flips_only`) plus
  tcap, and the manifest `manifest_calib_2sat_sc2_cgrid` (108 tasks,
  ≤ 28.8 CPU-h).
- **Checks:** `m2_results.py` now checks `polish_cap`; 9 tests.
- **Smoke:** flip limits bind exactly, and the run budget clips the last
  call.
- **Upload:** an upload list with a `sha256sum -c` file.
- `HYPERPARAMETER_CALIBRATION_PLAN.md` §0c.4 (commands there).
- **Upload verified the same day:** cluster snapshot
  `cluster_hashes_20261014.txt`. 43/44 upload paths match; only the list
  file is missing, and it is unused. The cluster `src` tree equals `d11f731`.
  Ready to submit.

### N-2026-10-14-a — c is calibrated empirically, not by a framework; c is part of the orthogonality flow; flip-only polish added [quote + decision + verified]

> "for coefficient - check if there are relevant hyperparameter frameworks, and write in to do I will check with external llm. moreover, state that in frameworks they set automatically, and i want to get result empirically concretly. I do want to use the coeficient research flow as part of orthogonality research flow. implement if there is no - solver version that will do constraint only number of flips without constraint of seconds per local search." (user's notes, read 2026-10-14)

- **Frameworks:** relevant ones exist (irace, SMAC3, ParamILS, GGA,
  Optuna; ISAC, Hydra; scaling-law tuning by Mascia et al. 2013 and
  others), surveyed in `RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`. New
  2026-10-14, abstract level: Ye, Luo and Cai (AAAI 2025) tune MaxSAT
  local search with SMAC. A search hit mentions linear, piecewise and
  log-log models of a parameter against instance size (about 2021); it is
  **not verified** and goes to the web-LLM query.
- **[decision] Stance:** frameworks set the parameter automatically. We
  calibrate c empirically and concretely with the pre-registered grid
  (plan §0b) and report the measured curve. The frameworks are related
  work and a protocol source.
- **To-do (user, external LLM):** Prompt 2 in
  `WEB_LLM_QUERY_FLIP_COEFFICIENT.md`. Not a session opener.
- **[decision + inference] Orthogonality:** the c calibration is a step of
  the orthogonality flow. A size-blind flip limit can make large-n
  instances memetic-hard through a short polish and bias ρ by size. Rules
  (plan §0c.2): ρ under the calibrated rule is primary and under 12,500 a
  sensitivity arm; calibration instances stay out of the reported ρ
  sample; c is chosen by memetic performance only.
- **[verified] `ls.polish_cap: flips_only`** (staging `src/evo/memetic.py`):
  each polish call ends only on its flip limit; the run budget still ends
  it under `deadline_mode: clip`. 5 new tests; staging suite 266 passed,
  3 skipped, 1 old failure. Not on the cluster. It can replace the 60 s
  per-call cap in the §0b grid.
- Where: `HYPERPARAMETER_CALIBRATION_PLAN.md` §0c.

### N-2026-10-12-e — HP-1 Stage L1 planned: a c grid at n 16,000 and 64,000 [quote + decision: planned, not prepared]

> "I want first make grid to calibrate coefficient for the 16000, and 64000 memetic, write it in plan then i want to wrap up" (user, 2026-10-12)

- **Grid:** c ∈ {3.125, 6.25, 12.5, 25, 50} flips per variable, at both
  sizes. That is 50k–800k flips per call at n 16,000 and 200k–3.2M at
  n 64,000.
- **Runs:** the 6 calib_2sat_sc2 instances × seeds 1–3, 900 s.
- **Per-call cap raised to 60 s,** so the flip limit binds.
- **Choice rule:** most successes, then the lowest mean of median
  best / c\*, then the smaller c within 0.05.
- **Size:** 90 tasks (+18 time-capped reference), ≤ 28.8 CPU-h.
- `HYPERPARAMETER_CALIBRATION_PLAN.md` §0b; open questions in §0b.7.
- **Revised the same day (user):** "I want start for both 16000, and 64000
  from 200k". The grid is now flips per call {200k, 400k, 800k, 1.6M,
  3.2M}, shared by both sizes: c 12.5–200 at n 16,000 and 3.125–50 at
  n 64,000. That is 5 configs, with the same task count and cost.

### N-2026-10-12-d — calib_2sat_sc2 memetic readout: Q2 on all 6 instances under both arms; 200k better in 18/18 pairs; opt-in time-only polish cap added [verified + inference]

> "both, copied results from cluster, analyze, make optional version of solver, where the cap is by the 3.5 seconds from config, ignoring the flip budget" (user, 2026-10-12)

- **Readout** (`CALIB_2SAT_SC.md` §13c): 36/36 shards; no run reached c\* in
  900 s; Q2 on all 6 instances under both arms.
  - The 200k arm beats the 12.5k arm in 18/18 pairs. Mean gap at n 16000:
    2.2 vs 5.0; at n 64000: 9.6 vs 18.3.
- **Fixed cost per child [inference]:** about 0.02 s (n 16000) and 0.07 s
  (n 64000). That is half the time of the 12.5k arm at n 64000.
- **Cluster flip rate:** about 190k–235k flips/s.
- **c = 15 correction:** at n 64000 it is about 5 s per call on the
  cluster, so the 3.5 s cap would always bind. This replaces the
  1.9–3.6 s estimate in N-2026-10-12-b.
- **The new option `ls.polish_cap`** (`src/evo/memetic.py::_ls_budget`):
  - `flips`, or an absent key: unchanged.
  - `time`: ls_polish_flips and flip_budget are ignored; each call runs to
    ls.time_limit_s.
  - It applies to v1 and v2 and to multistart, which shares `_ls_budget`.
  - Tests: `tests/test_polish_cap.py` (7 pass). Staging suite: 261 passed,
    3 skipped, 1 failure that predates today (SATLIB/PySAT).
  - Config: `memetic_deeppolish_p40_ls3p5_tcap_v2.yaml`.
- **Smoke [verified, 60 s, seed 1]:** 1.08M flips per 3.5 s call at
  n 16000 and 1.00M at n 64000, on the workstation.
- **[inference] Caveat:** a time-only cap makes the flips per call depend
  on the hardware. Runs are comparable only on similar nodes, and shards
  should be compared by total flips as well as seconds.

### N-2026-10-12-c — User intentions 2026-10-12: hard-clause memetic to be tested next; multistart first where the memetic struggles; c = 15 proposed [quote]

> "i want hard clause memetic tested sometime next, meanwhile the memetic struggles that is submitted, all first 30 parallel jobs after 12 min, didnt get to oracle. if unweighted memetic strugles, I want first maybe get it to multistart phase. , for first big instances we might use c =15" (user, 2026-10-12)

- **Observation (user):** in the calib_2sat_sc2 memetic batch, none of the
  first 30 tasks had reached c\* after 12 min. This is consistent with the
  smoke: neither arm reached c\* in 120 s (`CALIB_2SAT_SC.md` §13b).
  Nothing is read until the rows are back.
- **The hard-clause memetic is wanted next.** A multistart phase comes
  first where the (unweighted) memetic struggles. The exact scope of
  "multistart phase" is being confirmed with the user.
- **c = 15 is proposed** for the first large instances
  (`HYPERPARAMETER_CALIBRATION_PLAN.md` §0a).

### N-2026-10-12-b — Literature: no published c for a size-aware flip limit c · n [read + abstract + inference]

See [`RESEARCH_NOTES_FLIP_LIMIT_SCALING.md`](RESEARCH_NOTES_FLIP_LIMIT_SCALING.md).
- **No source gives a constant for a per-call flip budget c · n.**
- **Flips ∝ n holds only on satisfiable random formulas below a density
  threshold.** Proven for 2-SAT: E[flips] ≤ C·n/(1−α)² for α < 1
  (Berenbrink et al. 2024). Observed for 3-SAT (Seitz et al. 2005).
- **At the 3-SAT threshold, the optimal WSAT Maxflips grows as ~0.02·n^2.39**
  (Parkes & Walser 1996): m\*/n is 21 at n = 100 and 109 at n = 400.
- **IRoTS uses n-scaled defaults,** including a stall window of n²/4.
- **Our regime (α > 1 Max-2-SAT, n ≥ 16,000) has no result.** c = 15 is a
  calibration point, not a derived one. At n = 64,000 it hits the 3.5 s
  per-call cap.

### N-2026-10-12-a — calib_2sat_sc2 memetic batch: Q2 verdict from both arms; upload set checked file by file [quote + decision + verified]

> "consider verdict also from 200k arm, give me list of all files that should be new or to be updated on cluster" (user, 2026-10-12)

- **Decision.** §6's Q2 rule (success < 3/3 or median TTT ≥ 45 s) is applied
  to each arm separately. The 12.5k arm gives the pre-registered verdict and
  the 200k arm a second one, paired per (instance, seed). Disagreements are
  flagged. Which verdict a corpus decision uses is settled at the readout,
  with the reason written down. This replaces "the verdict from the 12.5k arm
  only" (N-2026-10-11-q). `CALIB_2SAT_SC.md` §13b.
- **Upload set [verified].** Each of the 40 paths was hashed and compared
  with the cluster's last known copy: the M2 submit provenance of 2026-10-04,
  the `rsync_files_*` lists of later uploads, and `git log`.
  - 14 files are new or changed on the cluster: `impl_v2.py`,
    `walksat_v2.py`, `memetic.py`, `run_memetic_shard.py`,
    `submit_m2_memetic.sh` (changed 2026-10-08, never uploaded since),
    `m2_results.py`, the two arm configs, the 3 manifest files, and the list.
  - `oracle_evalmaxsat.py` differs from the 10-04 record but went up with the
    EvalMaxSAT s1 upload. The 6 instances went up with the sc2 RC2 run.
- No code change is needed for the second verdict: it is computed on the
  workstation at the readout.
- **Correction, same day [verified]: the reconstruction above was out of
  date.** A hash snapshot of the cluster tree was taken on the login node
  (`sha256sum` only; 146 files; saved as
  `cluster_staging_maxsat/results/cluster_state/cluster_hashes_20261012.txt`).
  - **39 of the 40 upload paths match the workstation byte for byte**,
    including all 14 listed above. Only the list file itself is missing, and
    the runs do not use it. **No upload is needed for this batch.**
  - Elsewhere, 2 cluster files differ: `calib_2sat_sc_readout.py` and
    `preflight_calib_2sat_sc.sh` (workstation commit `00c6026`, 2026-10-11).
    Neither is used by the memetic batch.
  - Files on the workstation only are workstation tools (readouts, manifest
    builders, upload lists). Files on the cluster only are older manifests
    (calib_a/b, multistart JW) and archived scripts.
  - From now on, use a fresh snapshot instead of provenance records to check
    the cluster's state.
- **Submitted 2026-10-12** by the user (36 tasks, `MAXSAT_GIT_SHA=8b7d00e`).

### N-2026-10-11-u — LLM-driven solver design: study design sketched, direction not pursued [decision + inference]

- **[decision, user, 2026-10-11]** The project does **not** go in the
  LLM-driven solver design direction.
- **Design sketch, kept for reference:** `RESEARCH_NOTES_LLM_SOLVER_DESIGN.md`
  §7.1.
  - The LLM is the mutation operator inside an evolutionary search over
    one small function, such as the polish's variable-selection rule.
  - Training uses S-band instances; validation uses held-out M / L
    instances against the tuned HP-1 baseline.
- **Reasons (§7.2):**
  - ~1,000 CPU-h for even the narrowest study;
  - weak transfer of LLM-evolved heuristics to larger instances;
  - a new solver version would weaken comparability with the corpus
    study;
  - HP-1 targets the known weakness more cheaply.
- The document stays as related-work context.


### N-2026-10-11-t — HP-1 rule decided: continuous flips per variable with floor 12,500; LLM-driven solver design summarised [quote + decision + web-verified + inference]

> update I do would like not categories - continous number of flips per var,
> but in lower bound stay with 12500, I yes do want you to compile research
> summary of current solver design driven by llm, with litreture

*Source:* user, 2026-10-11.

- **[decision, user]** HP-1 uses `ls_polish_flips = max(12500, c · n)`.
  - The categorical rule is dropped.
  - The bands only select and budget instances.
  - `HYPERPARAMETER_CALIBRATION_PLAN.md` §0.
- **[inference]** The rule only changes runs with n > 12,500 / c. For any
  c ≤ 31, every n ≤ 400 instance keeps 12,500. Small-instance runs
  therefore test the floor, and c is estimated in the M and L bands.
- **LLM-driven solver design:** `RESEARCH_NOTES_LLM_SOLVER_DESIGN.md`.
  - **Methods:** FunSearch (Nature 2023), EoH (ICML 2024), ReEvo
    (NeurIPS 2024), LLaMEA (TEVC 2025), MCTS-AHD (ICML 2025), AlphaEvolve
    (2025), Shinka / OpenEvolve.
  - **SAT:** AutoSAT; SATLUTION (repository-scale evolution of SAT
    Competition solvers; claims to beat the 2025 winners); LLM-written
    local search from encodings (Schidler & Szeider 2025).
  - **No MaxSAT local-search work found.**
  - **Critiques:** search is needed (PPSN 2024); poor generalisation and
    overfitting (bin packing, EvoSTAR 2025); HeuriGym QYI ≈ 0.6.
  - **[inference]** Feasible here only for small functions (polish
    score, crossover proxy, hard-clause moves), and after HP-1.
- Decisions kept for tomorrow: `NEXT_SESSION_CONTEXT.md` §000000.
- *Addendum, 2026-10-11 (later).* `RESEARCH_NOTES_LLM_SOLVER_DESIGN.md` §6
  records two follow-up questions:
  - what HeuriGym is: an agentic benchmark, 9 problems, Quality-Yield
    Index ≈ 0.6 for the best models;
  - the difference between an LLM used as an agent and an LLM used as the
    mutation operator inside an evolutionary search over thousands of
    evaluated candidates.
  - The cost estimate is refined: ~1,000 CPU-h for 2,000 candidates even on
    small instances [inference].


### N-2026-10-11-s — HP-1: literature report on hyperparameter setting, instance-size inventory, and a calibration plan (categories vs continuous rule) [quote + verified + inference + plan]

> do some calibration for hyperparameter function on smaller instances too,
> it may be not continuous, might be with categories of instance size, after
> knowing what instance sizes might the solver meet, also do now research and
> report of hyperparameter setting frameworks, and alghoritms available and
> currently influencial online

*Source:* user, 2026-10-11.

- **Report:** `RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`.
  - The closest precedents for a size-dependent rule are the
    "configuring for scaling" papers: Styles et al. 2012; Mascia et al.
    2013, which fits a parameter scaling law from small instances; and
    Mu et al. 2016, where a size-adaptive EAX parameter changed the
    scaling class.
  - ISAC is the precedent for categories.
  - The tool versions were checked on 2026-10-11.
- **[verified] Instance sizes:** 1,947 files; m from 48 to 276,705.
  - The all-soft memetic solver meets m ≈ 50–70,000.
  - The m ≥ 100k files are all hard-clause (MSE 2023/2024).
  - Proven c\* by band of m (all-soft): S (< 1k) 465, M (1k–10k) 144,
    L (10k–100k) 22.
  - `scripts/size_inventory.py` → `results/size_inventory.csv`.
- **[inference]** 12,500 flips per call is 30–250 flips per variable at
  n ≤ 400 but 0.2 at n = 64,000. Flips per variable is the natural
  parameter of a continuous rule.
- **Plan:** `HYPERPARAMETER_CALIBRATION_PLAN.md`.
  - A flip grid (3,125 to 800,000, factor 4) per band, with size-scaled
    budgets (120 / 300 / 900 s).
  - Two racing rounds (Friedman + Holm, pre-registered).
  - Then a held-out comparison of the rules fixed-12.5k, fixed-200k,
    categorical and continuous (c · n, clipped).
  - ≤ 118 CPU-h worst case. **Not started; awaiting approval** (P0).


### N-2026-10-11-r — Solver files updated relative to the cluster for the calib_2sat_sc2 memetic run; to-do: a size-aware hyperparameter module [quote + verified + decision: to-do, not started]

> note in notes solver files only that were updated from those on cluster,
> for example because of v2, note in todo to make work on making code module
> to set hyperparameters, for example more flips for larger instances

*Source:* user, 2026-10-11.

**Baseline [verified].** This workstation cannot read the cluster. The last
record of the cluster's solver code is the provenance file of the M2 full-pool
submit, `results/m2_full_p40/provenance/submit_20261004T114233Z.txt`
(2026-10-04, git `69c9b97`, job 22131008). It holds the sha256 of every
`src/**/*.py` there. Each was compared with today's workstation file, and the
`src/` entries of every later `rsync_files_*.txt` were checked.

**Solver files updated relative to the cluster (4):**

| file | state on the cluster | change | why |
|---|---|---|---|
| `src/evo/impl_v2.py` | absent | new, 214 lines | v2 selection (`impl` key), cached crossover statics |
| `src/sat/walksat_v2.py` | absent | new, 323 lines | v2 incremental WalkSAT polish with v1's decisions |
| `src/evo/memetic.py` | older (2026-10-04) | +36 / −21 | dispatches polish and crossover through `impl`; v2 skips the no-op advisor round trip but keeps its RNG draw |
| `src/cli/run_memetic_shard.py` | older (2026-10-04) | +7 / −1 | shard schema 3: records `memetic_impl` |

- All four come from commit `182d348` (2026-10-08, memetic impl v2), and
  no later upload carried them.
- **Without them, a v2 config fails on the cluster.** The old
  `memetic.py` ignores `impl`, so the run would silently be v1. The
  `memetic_impl` check in `m2_results.py` would then class every shard as
  `invalid_submission`.

**Everything else the run imports is unchanged** (sha256 equal to the
2026-10-04 provenance). That covers `operators.py`, `population.py`,
`multistart.py`, `sat/{cnf,state,walksat}.py`, `llm/*` and the package
`__init__.py` files. Of the rest of `src/`, `oracle_evalmaxsat.py` also
differs from 2026-10-04. It went up with the EvalMaxSAT s1 upload
(`rsync_files_evalmaxsat_mse_s1.txt`), and the s1 rows show that it ran.
The memetic run does not use it.

The upload list `scripts/rsync_files_calib_2sat_sc2_memetic.txt` marks the
4 files as group 1a.

**To-do (not started; needs a plan and approval): a hyperparameter module.**
- **The problem.** Hyperparameters are constants in each YAML. A per-call
  flip limit that suits n = 250 (12,500) stops every call at n ≥ 16000
  (§13b smoke). Today the only fix is a new config per size: the
  `f200k` arm.
- **What the module would do:** set hyperparameters from instance
  features, for example more local-search flips for larger instances
  (`ls_polish_flips` as a function of n or m, with a floor and a cap).
  Pop size and the per-call time limit are candidates too.
- **Requirements:**
  - it is a pure function of the config and the instance's size, so a run
    is reproducible from them;
  - the resolved values are recorded in the shard;
  - existing fixed-value configs give exactly today's runs;
  - `m2_results.py` checks the resolved values, not the YAML.
- **Ordering [decision, mine].** It comes after the readout of the two
  calib_2sat_sc2 arms, which gives the first evidence on how much the flip
  limit matters at large n. Listed in `NEXT_SESSION_CONTEXT.md` §8 as
  **HP-1**.


### N-2026-10-11-q — A second main memetic config: 200,000 flips per local-search call (v2), run paired with the pre-registered arm [quote + decision + verified]

> do another main config with 200000 limit on local flips, use it in the
> first suggested cluster to be done, however list all files that should be
> uploaded to cluster including solver code.

*Source:* user, 2026-10-11.

- **Config:** `configs/tier2/memetic_deeppolish_p40_ls3p5_f200k_v2.yaml`.
  It is the v2 primary arm with `ls_polish_flips` = `flip_budget` = 200,000;
  everything else is unchanged.
- **Batch:** it is added to the calib_2sat_sc2 memetic assessment as a
  second arm, paired line by line. The batch is now 36 tasks, ≤ 9.6 CPU-h.
  `CALIB_2SAT_SC.md` §13b.
- **[decision, mine]** The §6 Q2 verdict stays with the pre-registered arm
  (12,500). The 200k arm is reported beside it. Whether it becomes the
  corpus arm is decided after the readout.
- **[verified, not data]** 120 s smoke runs, seed 1: 200k reached 14
  (c\* 12, n 16000) and 19 (c\* 9, n 64000), against 19 and 28 at 12,500.
- **Upload list:** the 18 solver modules a run imports (traced), the rest of
  `src/` (for the provenance digest), 3 configs, 7 script and manifest
  files, and the 6 instances. 40 paths in total.
- `m2_results.py` now also checks `ls_polish_flips` per task.


### N-2026-10-11-p — Memetic assessment of the calib_2sat_sc2 promising cells uses `impl: v2`; 18 tasks prepared [quote + decision + verified]

> use v2 for the memetic assessment

*Source:* user, 2026-10-11.

- **Scope:** the 6 eligible instances of the 2 promising cells. The
  pre-registered primary arm runs with `impl: v2` (config checked identical
  except `impl`), seeds 1–3, 900 s, stop at the optimum. 18 tasks,
  ≤ 4.8 CPU-h. Not submitted. `CALIB_2SAT_SC.md` §13b.
- **[decision]** v2 seconds are not compared with v1 results
  (N-2026-10-08-i). `m2_results.py` now rejects a shard whose `memetic_impl`
  differs from the manifest's.
- **[verified, not data]** 120 s smoke runs at n 16000 / 64000 did not
  reach c\* (19 vs 12, 28 vs 9).
- **[inference]** Every polish call spends its full 12,500 flips, so at
  n = 64000 the fixed per-call flip budget may contribute to Q2 outcomes.
  It stays as pre-registered; any change is a separate arm.

### N-2026-10-11-o — EvalMaxSAT 3600 s on MSE s1: 18 proven optima, all equal to the best-known (7 new for MSE 2023); 19/30 MSE 2023 runs end with no feasible incumbent [verified + inference]

- 60/60 rows, 0 errors, every incumbent model-checked; readout exit 0
  (`MSE_EVALMAXSAT_3600.md` §9).
- **Proven optima: 8 MSE 2023 + 10 MSE 2024, every one equal to its
  year's best-known.** No table value was beaten. Seven MSE 2023 optima are
  new relative to RC2 at 1800 s, including min-fill myciel5 = 196 where
  RC2's LB was 97. 8 of the 18 took > 900 s, two > 3000 s.
- **MSE 2023 (unweighted): 19/30 `no-ub`** — no hard-feasible assignment
  after an hour, as predicted in §5a. **MSE 2024 (weighted): 28/30 have an
  incumbent**, 11 of the 17 non-optimal ones within 5 % of the best-known.
- **[inference]** The contrast is plausibly stratification on distinct
  weights; families differ between the years, so it is not isolated.
- For the hard-clause solver: 18 proven targets; on the 21 `no-ub` instances
  any feasible solution already beats what EvalMaxSAT gives in an hour.

### N-2026-10-11-n — `calib_2sat_sc2` readout: the first two `promising` cells (n 16000 α 1.20; n 64000 α 1.10), 6 eligible with c\* 9–14 [verified + inference]

- Array 22645633: 15/15 rows, 14 certified, 1 censored (LB 12), 0 failed
  (`CALIB_2SAT_SC.md` §13a).
- **n 16000, α 1.20:** 3 eligible (c\* 12, 13, 14 at 65–673 s) → promising.
  **n 64000, α 1.10:** 3 eligible (c\* 9, 10, 13 at 49–155 s) → promising.
  **n 16000, α 1.15:** 5 fast (c\* 4–9, ≤ 14 s) → too_easy.
- With calib_2sat_sc's one, **7 eligible Max-2-SAT instances at n ≥ 8000**.
- RC2 log-time slope against c\* within a cell: ~0.75 (n 16000) and ~0.21
  (n 64000) decades per unit, vs 2.32 for Max-3-SAT n = 250 — the window
  spans several c\* values here [inference, 4–5 points per cell].
- c\* tracks n·ε³ again (covariate only).
- **Next (§6, proposal):** memetic assessment of the 6 eligible instances.
  Open choice: v1 (pre-registered, but O(m) per flip at this n,
  N-2026-10-08-h) vs `impl: v2`.

### N-2026-10-11-m — "Hopeless clauses" are singleton cores: an RC2-type proof found as a by-product of search; renamed, and a wording rule [decision + inference]

*Source:* user's question and decision, 2026-10-11: "is this … different from
rc2? is it closer to local search or rc2 proving" → "yes rename".

- **[inference] What it is.** A move assumes one literal of a soft clause C
  and asks Glucose for a model of the hard clauses. If every literal of C is
  refuted, then hard ∧ C is UNSAT: C is an **unsatisfiable core of size
  one**. This is the same kind of object RC2 finds, and RC2 handles a
  singleton core the same way: it adds the weight to the lower bound and
  drops the clause. For a unit soft clause (x), it means ¬x is implied by the
  hard clauses.
- **Difference from RC2.**
  - RC2 assumes all remaining soft clauses at once, and so finds cores of any
    size. Its bound rises to the optimum.
  - The H3 moves assume one literal at a time, so they find singleton cores
    only.
  - The refutation is a side effect of search, not its goal.
  - On ja-maxham-00000385 the singleton-core bound reached 31–33 against the
    optimum 37. The missing 4–6 units come from cores of ≥ 2 soft clauses.
- **[decision] Rename** (code, config, `PROVENANCE.md`):
  - `hopeless_clauses` → `singleton_cores`;
  - `hopeless_weight_lb` → `singleton_core_lb`;
  - `SoftView.hopeless` → `SoftView.singleton_cores`.
  - No behaviour change. N-2026-10-11-l keeps its original wording (the
    notes are append-only).
- **Wording rule:**
  - Describe the solver as **SAT-assisted local search** (memetic plus
    SAT-based repair and large-neighbourhood moves), not as plain local
    search.
  - Call the bound a "singleton-core lower bound" and report it as a
    diagnostic. Never compare it with RC2's lower bound.
  - Its one strong use: when a run's best cost equals it, that run has
    proven its own optimum.
  - The roles rule still holds: Glucose sees only the hard clauses plus one
    assumption, never the objective.

### N-2026-10-11-l — Hard-clause H3: SAT-based repair + feasible moves make the search move; ja-385 reaches its optimum 37 in 60 s on 1 of 3 seeds; 100 % feasible children [verified on workstation acceptance runs + inference]

- **Implemented** in `cluster_staging_maxsat_hard/` (`PROVENANCE.md` H3):
  - one shared Glucose4 per run;
  - repair `R`;
  - feasible move `M` (assume a soft literal, re-solve with phases), with a
    per-call conflict budget;
  - hopeless-clause proofs, which give a proven lower bound.
  - Tests: 8 new; tree total 133 passed, 12 skipped.
- **Acceptance** (`HARD_CLAUSE_SOLVER_PLAN.md` §6b, 60 s, 3 seeds, 2
  instances):
  - feasible children 100 %;
  - final below the Glucose start on 6/6 runs;
  - ja-maxham-00000385: 61/44/64 → 38/38/**37**, LB 31–33;
  - synthetic: 27/22/26 → 7/8/7.
- **For reference, not compared as data:** on ja-385, EvalMaxSAT proved 37 in
  109 s and RC2 in 71 s on the workstation. On frb40-19-4, H3 reached 738 in
  60 s, while EvalMaxSAT's incumbent at 600 s was 741.
- **[inference]** On ja-385 a 60 s run is about 1–2 generations, so the
  result is mostly the moves, not the EA. The multistart arm H4 with the same
  `R`/`M` is the test of N-2026-10-11-c.

### N-2026-10-11-k — Hard-clause H2 (`impl: hard`): Glucose init feasible and fast; crossover breaks feasibility; single hard-safe flips are almost always impossible (ja-385: 99.99 % no-op steps, 61 → 61 in 60 s) [verified on workstation smoke + inference]

- **Implemented** in `cluster_staging_maxsat_hard/`; logged in its
  `PROVENANCE.md`.
  - Glucose4 initialisation with phases drawn per member (JW or coins),
    charged to the run clock.
  - The mutation guard uses the child's vector. The stale-vector bug is
    reproduced in a test.
  - The v2 polish gains opt-in no-op counting.
  - `HardStats` is reported under `hard`.
  - Tests: 14 new; tree total 125 passed, 12 skipped.
- **Smoke** (`HARD_CLAUSE_SOLVER_PLAN.md` §6a):
  - init: 40 distinct feasible members in 0.01–0.12 s;
  - before polish, 66–95 % of children are infeasible, and polish does not
    repair them;
  - on ja-maxham-00000385, 99.99 % of polish steps were no-ops and the cost
    stayed at the best Glucose start (61; optimum 37).
- **[inference]** Repairing children alone will not make the solver search.
  The feasible region is rigid under single flips. H3 should add a SAT-based
  feasible move: assume an unsatisfied soft literal and re-solve the hard
  clauses with the current assignment as phases. It shares the repair
  operator. That is a proposal; it needs the user's approval.

### N-2026-10-11-j — Hard-clause solver H1: `cluster_staging_maxsat_hard/` created from commit 4100ea7 [verified]

> start the hard-clause solver, create the new folder

*Source:* user, 2026-10-11.

- **Copied from `cluster_staging_maxsat/` at commit `4100ea7`:** `src/`
  (all), `configs/tier2/`, the solver and parser tests, and the memetic
  runner array and its submit wrapper.
- **Not copied:** data, results, or calibration scripts.
- **Checks:**
  - all 43 copied files are byte-identical to their sources;
  - the copied tests, run from inside the new tree, give 111 passed and
    12 skipped, all skips being missing data or manifests;
  - imports resolve to the new tree.
- Provenance and checksums: `cluster_staging_maxsat_hard/PROVENANCE.md`.
  Every later change is logged there.
- `.gitignore`: the new tree's `data/**` is ignored, except manifests.
- **Next (H2, needs approval):**
  - Glucose initialisation on the hard clauses;
  - fix the stale `hard_satisfied` vector in `mutate1`;
  - make hard-unsafe no-op iterations count as steps;
  - assert hv = 0 in the population, and add the new record fields;
  - unit tests for all of these.

### N-2026-10-11-i — `calib_2sat_sc2` prepared (n 16000 at α 1.15/1.20, n 64000 at α 1.10; 15 tasks); calib_c left out [decision + verified]

> prepare the next batch with n 16000 and 64000, do manifest along with calob_c
> if you think it is needed

*Source:* user, 2026-10-11.

- **Batch.** Grid `instancegen/grids/calib_2sat_sc2.yaml`, fresh seeds
  246–260. Same model, measurement and §6 rules as calib_2sat_sc. 15 tasks,
  ≤ 4.0 CPU-h. Generated, validated, sha-checked and dry-run tested; not
  submitted. `CALIB_2SAT_SC.md` §13.
- **[verified, not data]** A workstation pipeline smoke on batch instance
  s256 (n 64000, α 1.10) reached RC2 lower bound 12 in 60 s, so its
  c\* ≥ 12.
- **[decision] calib_c is not included.**
  - It answers a different question (n = 400 corpus cells plus memetic).
  - It is nested as prepared and needs a new seed block for α 2.15.
  - Its stated pass chance is 1–5 %.
  - R3-a remains open.

### N-2026-10-11-h — `calib_2sat_sc` readout: c\* up to 14 proven (LB up to 18) at large n near α = 1; 1 eligible instance (n 8000, α 1.20, c\* 14, 540 s); 8 cells too_easy, 1 too_hard [verified + proposal]

- Array 22610781: 45/45 rows, 0 failed, 2.04 CPU-h (`CALIB_2SAT_SC.md` §10d).
- **c\* > 2 is common here.** 17 of 38 certified instances have c\* ≥ 3, the
  maximum certified is 14, and censored LBs are 13–18. At n = 2000, c\* is
  0–3. This confirms the user's 2026-10-08 caution against judging the
  region from n ≤ 400.
- **One eligible instance:** n = 8000, α 1.20, seed 227, c\* = 14, 539.9 s.
  No cell is `promising`. Eight are `too_easy`; n = 32000, α 1.20 is
  `too_hard`.
- **The RC2 time slope is gentle at n = 8000:** about 0.41 decades per unit
  c\*, against 2.32 for Max-3-SAT at n = 250. If it holds, the window would
  admit a range of c\* (roughly 10–14) rather than a single value
  [inference, 7 points].
- **The n = 32000 split is wide:** certified c\* 6–8 in ≤ 18 s, censored at
  LB 13–16, and nothing in between.
- **Proposed next points (§6 rules, not prepared):** n = 16000 at α 1.15 and
  1.20; n = 64000 at α 1.10. Optional: an exploratory memetic `impl: v2` run
  on the one eligible instance.

### N-2026-10-11-g — MSE 2016/2023/2024 state; best-knowns rechecked; EvalMaxSAT 3600 s sample s1 prepared; hard-clause solver starts on MSE 2023/2024 [quote + verified + decision]

> check results for mse instacnses, 2016, and the new, I want to run them for
> 3600s with solver EvalMaxSat on cluster, give your opinion, later run them with
> enhanced local for hard clauses, starting from the mse24 and mse23, after
> enhancing local for hard clauses, with glucoze, I have best knowns for them,
> recheck in repo, I would like to give on cluster job, sampling, for example
> first manifest 2*30 jobs array, for evalMaxSat and meanwhile prepare the local
> search suitable for solving them.

*Source:* user, 2026-10-11.

- **[verified] State.**
  - MSE 2016 (856 instances, sample of 104) is all-soft and unweighted. Its
    900 s RC2 screen was never run on the cluster. EvalMaxSAT has 12 rows,
    all timeouts.
  - MSE 2023 (75, unweighted, hard clauses): RC2 at 1800 s certified 2.
  - MSE 2024 (91, weighted, hard clauses, anytime track): no exact-solver
    row.
- **[verified] Best-knowns.** Each set's own table matches the raw MSE table
  on every row.
  - 5 entries are −1 ("not known").
  - RC2's lower bound never exceeds the best-known. It equals it on 4 MSE
    2023 instances, which proves those 4 optimal.
  - Looking a value up in the other year's table by name is wrong: on
    several files it gives values below RC2's proven bound.
  - Detail: `MSE_EVALMAXSAT_3600.md` §3.
- **[decision] (user):**
  - EvalMaxSAT at 3600 s on MSE 2023/2024, sampled, with a first array of
    2 × 30;
  - then the enhanced hard-clause solver (Glucose initialisation),
    **starting on MSE 2024 and 2023**.
  - This answers Q4 of `HARD_CLAUSE_SOLVER_PLAN.md` for the first targets.
- **[inference] Opinion** (`MSE_EVALMAXSAT_3600.md` §4):
  - worth running, as a target and reference-effort source for the
    hard-clause solver, not as an eligibility screen;
  - expect many unsolved instances, some without any incumbent;
  - MSE 2016 does not belong in this batch: it is all-soft, and its first
    step is the RC2 900 s screen.
- Prepared: sample s1 (60 tasks, stratified by family, seed 20261011),
  sbatch, a shell-only submit wrapper with a smoke mode, and a readout.
  Budget ≤ 62 CPU-h. Not submitted.

### N-2026-10-11-f — The EvalMaxSAT driver could not read MSE ≥ 2022 files and discarded the anytime incumbent; fixed [verified + correction]

- **[verified]** `src/cli/oracle_evalmaxsat.py` treated files without a `p`
  line as plain CNF. `h` lines raised a parse error, and in soft-only files
  the weight became a literal. Every MSE 2023/2024 task would have ended as
  `error`.
- **[verified]** It stopped the solver with SIGKILL (`subprocess.run`
  timeout). EvalMaxSAT's SIGTERM handler prints the incumbent (`o`,
  `s SATISFIABLE`, model) and exits 10.
- **Correction** to `archive/ORACLE_EVALMAXSAT_SLURM.md` ("EvalMaxSAT prints
  no intermediate `o` lines … a timeout gives no bound"). That was a
  property of the SIGKILL setup. With SIGTERM, a capped run returns a
  verified upper bound **once the solver has an incumbent**. At 60 s it had
  none on two MSE 2023 instances (`s UNKNOWN`).
- Fixed in the staging copy and covered by 8 tests: dialects, weighted cost,
  and live optimum / soft-only / SIGTERM runs. On the workstation it proved
  ja-00000385 = 37 in 109 s with the model verified.
  `MSE_EVALMAXSAT_3600.md` §5; `cluster_staging_maxsat/DIVERGENCE.md`.
- **[verified] 600 s probes, 4 run concurrently** (`MSE_EVALMAXSAT_3600.md`
  §5a): an incumbent (741 against best-known 720, verified) only on the
  soft-only frb instance. No incumbent on any of the 3 hard-clause
  instances: im-hit-B-3, ja-00000253 and setcover-135.
- **[inference]** At 3600 s, expect many `no-ub` rows. EvalMaxSAT supplies
  proven optima, not upper bounds. A Glucose-initialised hard-clause solver
  has an incumbent where EvalMaxSAT has none.

### N-2026-10-11-e — `calib_2sat_sc` does not replace `calib_c`; calib_c as prepared is nested across its two α cells [verified + inference]

- **Different questions** [verified from the plans]:
  - `calib_c` (n = 400, α 2.0 / 2.15, 40 instances) decides two
    corpus cells under the pre-registered §5.3 rule. Both are one Q2
    instance short; it needs RC2 and then memetic runs
    (`CORPUS_FREEZE_PREP.md` §5).
  - `calib_2sat_sc` (n 2000–32000, α 1.10–1.20) tests the larger-n
    direction: whether a slightly supercritical α at large n gives
    c\* > 2 with real RC2 difficulty. `CALIB_2SAT_SC.md` §1 says it "does
    not replace `calib_c`".
- **Nesting** [verified 2026-10-11]: calib_c uses the same seeds 101–120 in
  both α cells. `…sr2.15…_s101` (860 clauses) has `…sr2.00…_s101`
  (800 clauses) as its exact prefix. The two cells are therefore paired,
  not independent. This is the effect of N-2026-10-08-e, which decided
  that **new** batches get one seed block per cell. calib_c was prepared
  before that decision.
- **Duplicates** [verified, s101 only]: 0 duplicate clauses at α 2.0 and
  1 at α 2.15 (`weighted_ksat` samples with replacement, N-2026-10-08-c).
- **[inference]** If calib_c is kept, the minimal revision is per-cell seed
  blocks: for example 101–120 for α 2.0 and 121–140 for α 2.15.
  - Keep `weighted_ksat`, because §5.3 pools calib_c with the calib_a/b
    instances of the same cells, which used it.
  - The §5.3 rule is per cell, so pairing does not bias either cell's
    verdict. It matters only when the cells are compared or pooled.
- Decision R3-a (keep / revise / replace) is still the user's.

### N-2026-10-11-d — Keep the 900 s cutoff: the one-hour re-run bought few certifications per CPU-hour [verified + decision]

> Keep the 900 s cutoff. The one-hour run bought few certifications for the
> CPU-hours.

*Source:* recommendation of 2026-10-11, which the user asked to record with
the numbers (2026-10-11).

**Numbers** [verified]. They are sums of `profile.solve_s` over the rows,
i.e. wall seconds actually spent on one CPU each; the Slurm allocation is
larger. Files: `cluster_staging_maxsat/results/profile_{cap3600,calib_a,calib_b,satlib}_all.jsonl`.

| batch | cap | tasks | CPU-h spent | certified | eligible (30 < t ≤ 900 s) | CPU-h per eligible |
|---|---:|---:|---:|---:|---:|---:|
| SATLIB screen | 900 s | 263 | 7.9 | 251 | 95 | 0.08 |
| calib_b | 900 s | 110 | 10.0 | 85 | 53 | 0.19 |
| calib_a | 900 s | 180 | 24.3 | 92 | 17 | 1.43 |
| **cap-3600 re-run** | **3600 s** | **148** | **138.5** | **25** | **0** | **—** (5.5 CPU-h per certification) |

- **Where the time went.** The 123 instances that stayed censored used
  127.0 of the 138.5 CPU-h (92 %). The 25 that certified used 11.5 CPU-h.
- **Conversion.** 25/148 (17 %) certified with a 4× longer cap. 24 of the
  25 took 900–3078 s, so they are outside the window by definition.
  The 25th, uuf250-027 at 844 s, is host or run noise
  (N-2026-10-11-a) and is not eligible.
- **Little movement in the rest.** Censored lower bounds rose by only 0–5
  (Max-2-SAT) and 0–1 (3-SAT) in the extra 2700 s. Another doubling of the
  cap would convert few more.
- **Cost of widening the window instead.** Changing the window to
  (30, 3600] s would add at most these 24 instances. Every RC2 screen would
  cost up to 4× the worst-case CPU-h (3720 s against 960 s per task), and
  the memetic Q2 seconds threshold would need re-deriving. The same
  CPU-hours spent on new 900 s cells produced 0.08–1.43 CPU-h per eligible
  instance.

*Decision.*
- **The eligibility window stays (30, 900] s.**
- The cap-3600 rows are used only as **out-of-window optima and time
  profiles**: c\* and lower bounds for reporting, e.g. the first c\* = 2 at
  n = 250.
- No further long-cap RC2 re-runs unless a specific question needs one.

### N-2026-10-11-c — Attention point: multistart may be enough; most successes came at the first child or in the first generation [quote + verified + inference]

> also emphasize in documents I want to give attention to result that
> multistart might be enogh, due to result that most answers were achieved
> in first child or first generation

*Source:* user, 2026-10-11.

- **[verified]** M2 full pool: 28/70 instances were solved by the first
  polish call in all 6 runs. 55/70 never went past generation 1
  (`M2_FULL_POOL_READOUT_AND_STATE.md` §6.2). M2 pilot: success within 1–8
  children on 8/10 instances (`M2_PILOT_READOUT.md` §3).
- **[verified]** uuf three-arm ablation, successes: JW multistart 127/130,
  uniform 124/130, memetic 118/130. Kaplan–Meier median TTT: memetic 30 s,
  JW 90 s (`UUF_THREE_ARM_ABLATION_READOUT.md` §0).
- **[inference]** Where the EA had no room (first-generation successes), the
  rows cannot separate memetic from multistart. Where it had room (uuf),
  multistart was more reliable and memetic was faster in a typical run. So
  "multistart is enough" is supported on reliability, not on typical speed.
  A fair test needs Q2 non-trivial instances.
- **[decision pending]** This conflicts with the 2026-10-06 decision "no
  multistart on the calibration pool" (`CORPUS_CALIBRATION_LOG.md`
  Checkpoint 8). It is not lifted; that is open question Q5 in
  `HARD_CLAUSE_SOLVER_PLAN.md` §7.
- **Wording rule until tested:** say "on most calibration instances the
  memetic solver succeeded in its first generation, so these instances do
  not test the EA". Do not say "the EA adds nothing".
- Detail: `HARD_CLAUSE_SOLVER_PLAN.md` §5.

### N-2026-10-11-b — Intention: a hard-clause solver in a new staging tree, with Glucose initialisation and feasibility kept through LS and memetic steps [quote + decision: planned, not started]

> do new folder similar to cluster_staging_maxsat, copy there the
> up-to-date solver, and make solver for hard clauses, with glucouze
> initialization of hard satisfiebility, and enhancing solver with qualities
> it will save the hard satisfiebility over local and memtic iterations

*Source:* user, 2026-10-11.

- This matches what the hard-clause reassessment found:
  - Glucose solves difficulty 1 (the initial feasible assignment);
  - difficulty 2 (keeping feasibility through crossover and polish) needs
    operator changes (`CORPUS_FREEZE_PREP.md` §8.4; N-2026-10-07-a).
  The user's request covers both.
- The new solver is a **new algorithm**. It never shares a stratum or a
  table with the current one (§8.5). The existing `cluster_staging_maxsat/`
  is not edited.
- Acceptance bar, adopted unchanged from §8.5:
  - ≥ 95 % feasible children from feasible parents in the operator probe;
  - feasibility on every seed in 900 s runs.
- Plan, milestones H0–H6 and open questions:
  `HARD_CLAUSE_SOLVER_PLAN.md`. Only H0 (the plan) is done.

### N-2026-10-11-a — RC2 cap-3600 re-run: 25/148 certified; sibling evidence ranks correctly, but "majority certify" was over-predicted; first certified c\* = 2 at n = 250, all above 900 s [verified]

- Array 22397120, 148/148 rows, 0 failed, PySAT 1.9.dev3
  (`RC2_CAP3600_RERUN.md` §6 outcome). Predictions N-2026-10-08-b:
  - G3, G5 (deep, ≤ 10 %), G7 (uuf250 LB 1, majority) and G9 (hole10)
    **held**;
  - G1, G2, G4, G6 **failed**: they certified 3/13, 0/4, 6/16 and 4/11.
- Groups with sibling evidence certified 24/58. Groups without certified
  0/80. LB size does not separate them. Rate: 17 % of censored instances
  certify within a cap 4× longer.
- **uuf250 family now:** c\* = 1 ×84, c\* = 2 ×5 (1132–3078 s), c\* ≥ 2
  censored ×11. At least 16/100 have c\* ≥ 2, and none certifies within
  900 s. This **supports C2** of
  `RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`.
- uuf250-027 certified at 844 s, after a 922 s timeout in its earlier row:
  run-to-run or host noise of ≥ 9 % near the window edge. Eligibility is
  unchanged.
- Censored LBs rose only 0–5 (Max-2-SAT) and 0–1 (3-SAT) in the extra
  2700 s. The deep cells are far beyond 3600 s.

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
