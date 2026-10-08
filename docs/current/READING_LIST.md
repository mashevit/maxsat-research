# Reading list — what to read to understand the project's state

**Date:** 2026-10-06; rows 0 and 1c added 2026-10-07. Only documents that are needed, or that add
information the documents above them do not contain, are listed. Anything
not listed, including everything under `docs/archive/`, is either superseded
or already summarised in one of these.

Read in this order. Paths are relative to the repository root.

| # | document | what it adds | read |
|---:|---|---|---|
| 1 | `docs/current/NEXT_SESSION_CONTEXT.md` (r3) | Current state; **§0: the larger-n Max-2-SAT / Max-3-SAT direction, its existing evidence, and the decisions left (R3-a…d)**; the decisions of 2026-10-06, what is prepared but on hold (`calib_c`), MaxCut, open decisions, configurations, paths, where to resume | §0 first, then all |
| 0 | `docs/current/RESEARCH_NOTES.md` | **The single entry point for research notes:** an index of every document with research content, and dated notes (quotes, caveats, wording rules, scope decisions). Add new notes here. | before writing up or deciding scope |
| 1c | `docs/current/SATLIB_BENCH_INTAKE.md` | SATLIB families in `data/satlib_bench/`: 263 unsat / 16 sat (labels from file content, SAT-checked); 209 originals misread by PySAT (empty clauses, a dropped literal), now normalised; the single 263-task RC2 manifest and its commands; **§8: RC2 results (run 2026-10-07; 95 eligible)**; the SATLIB citation | before any SATLIB run or memetic manifest |
| 1d | `docs/current/RC2_CAP3600_RERUN.md` | RC2 re-run at cap 3600 s of every censored instance (excluding mse16/raw/more_data): 148 tasks, a table per source and per cell with prior lower bounds, files and commands | before submitting or reading the cap-3600 rows |
| 1a | `docs/current/RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md` | Claims C1–C4 with evidence: at n ≥ 250, RC2-eligible Max-3-SAT has c\* = 1; c\* = 2 is at or past the 900 s edge; density does not help. Includes the per-c\* and per-n RC2 time steps from SATLIB uuf50–250. | before deciding R3-c |
| 1b | `docs/current/GRID_POINTS_WINDOW_30_900.md` | RC2 grid points per (k, n, c\*) under the agreed (30, 900] s window, window capacity per row, and the revision of B1 §5 (which used 60–600 s); n = 150 c\* 3 and the n = 200 gap; decisions G-a…d | before R3-b / R3-c |
| 2 | `docs/current/CORPUS_FREEZE_PREP.md` (r2) | The evidence behind the handoff: the verified candidate-cell table with denominators, the literal §5.3 results, classification, the `calib_c` design and decision rule, the family inventory and torus fix, the hard-clause reassessment with probe results | r2 box first; then §2–§5, §6, §8 (§9 only when submitting `calib_c`) |
| 3 | `docs/current/CORPUS_V1_PROTOCOL_DRAFT.md` (r2) | The proposed final protocol: exact RC2 and memetic configuration and environment, strata, eligibility rule, effort definitions (seconds primary), the sample-size trade-off, analyses, accounting, the decision table | all |
| 4 | `docs/CORPUS_CALIBRATION_GOALS.md` | The pre-registered rules everything is judged by: research questions Q1–Q3, hypotheses H1–H4, the outcome classes, the ERT definition, the Q2 and §5.3 rules, the statistical conventions. Partly superseded; its status header says where. | header, §1, §4.2, §4.4, §5.2, §5.3 |
| 5 | `docs/M2_FULL_POOL_READOUT_AND_STATE.md` | The full M2 result the handoff only summarises: solver mechanics, the RC2 time decomposition, success and difficulty tables, memetic reliability (ICC, between-arm ρ), all ρ results and why 3-SAT and 2-SAT differ, the historical uuf comparison, threats to validity, the data-file dictionary | §0, §2, §3, §6 (with its correction), §7, §9, §11 |
| 6 | `docs/CALIB_B_B1_READOUT.md` | The RC2 calibration boundary per (n, k) row, and the slope finding (a row's yield is set by d log10(t)/dc\*). **Needed for the larger-n grid plan (Max-2-SAT and Max-3-SAT).** | §0, §2, §5, §7 |
| 7 | `docs/CORPUS_GENERATOR_PLAN.md` | The generator specifications for the next milestone: the MaxCut module interface and encoding (Step 1a), the verification harness (Step 2), and the family and stratum table with the 2026-10-06 amendments (torus as ±J, hard clauses) | §3.1, §3.2, §4 Steps 1–2 |
| 8 | `cluster_staging_maxsat/DIVERGENCE.md` | Which staging `src/` files intentionally differ from repo `src/` (target stop, deadline clipping, new-format parsing, multistart), and the identity check to run before any staging code change | before editing code |
| 9 | `docs/CORPUS_CALIBRATION_LOG.md` | Provenance only: job ids, submission records, the PySAT history, and run anomalies (A1 tasks 39/40, negative `solve_s`) that no other document keeps | Checkpoints 2, 6, 8, 9 as needed |

## Key data (not documents)

All paths below are relative to `cluster_staging_maxsat/`. The column
dictionaries are in document 5, §11.

- `results/corpus_freeze_prep/candidate_cells.csv` and
  `candidate_instances.csv`: the cell and instance tables of document 2.
- `results/m2_full_p40/analysis/instance_table.csv`: one row per M2 pool
  instance.
- `results/profile_calib_{a,b}_all.jsonl`: every RC2 row, including the
  lower bounds of censored instances. These are the input to the larger-n
  grid plan (Max-2-SAT and Max-3-SAT).
