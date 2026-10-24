# docs/current2: new documents from 2026-10-14 on

**Created:** 2026-10-14 (user: "create new current docs folder in which you
will put new docs from now").

**Rule:**
- **Every new document** (plans, read-outs, research notes
  `RESEARCH_NOTES_<TOPIC>.md`, web-LLM prompts, handouts) is created here,
  not in `docs/current/`.
- **Existing documents in `docs/current/` stay where they are** and are
  still updated in place: their paths appear in code comments, configs and
  cluster upload lists.
- **The three hubs stay in `docs/current/` and remain the entry points:**
  - `docs/current/NEXT_SESSION_CONTEXT.md` (read first);
  - `docs/current/RESEARCH_NOTES.md`: the §1 index and the dated notes;
    every new document here is indexed there, with its `docs/current2/`
    path;
  - `docs/current/READING_LIST.md`.
- Superseded documents go to `docs/archive/<date>_superseded/` with a
  README (as in `docs/archive/2026-10-14_superseded/`).

## Documents

| document | created | what it is |
|---|---|---|
| [`RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md`](RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md) | 2026-10-24 | Literature check: has anyone measured the orthogonality of anytime (local search) and exact solvers, and passed the exact optimum to the anytime solver? Closest precedent is SAT: Hoos & Stützle, correlation 0.26 (R-Novelty+ vs Satz). IRoTS takes its MaxSAT target from complete solvers. No MaxSAT precedent found. Caveat: find vs find+prove. N-2026-10-24-a. |
| [`NOTES_2026-10-21_AGENDA_AND_STATS.md`](NOTES_2026-10-21_AGENDA_AND_STATS.md) | 2026-10-21 | User's notes and agenda: per_polish batch (24 instances incl. 5 weak-family picks, 144 tasks); MSE 2016 to run; larger (>5 MB) MSE 23/24 to check; the "monkey patch" decision to explain; first ρ sketch: U30 is uniformly easy (83 % of runs at the first LS call) and why it stays out of ρ (pre-registered window, effort floor/ties, RC2 start-up floor), and the caveat that the floor reaches into O900. §6 = context for the next session. N-2026-10-21-l. |
| [`LONG_CLAUSE_RULE_DESIGN.md`](LONG_CLAUSE_RULE_DESIGN.md) | 2026-10-21 | Built 2026-10-21 (§8; tests 403/16; rail smoke 221–284 MB, cost 2.8–3.1× best-known at 60 s, all slot time in SAT moves). Design: run v3 on the setcover rail instances by never building the neighbour tables when Σk(k−1) > 50M (only rail; every other instance stays byte-identical). CC and PX stay exact (clause walk, union–find); walk mutation keeps its distribution by rejection sampling; tests; decisions for the user. N-2026-10-21-j. |
| [`UNDER30_HARDMSE_RUN.md`](UNDER30_HARDMSE_RUN.md) | 2026-10-21 | Batches U30 (319 instances with an optimum proven in < 30 s, not in O900; 957 tasks) and HMSE (141 MSE 2023/2024 instances with hard clauses and a best-known; the 3 setcover rail files dropped, they do not fit in memory; 423 tasks), both on `configs/strong/auto.yaml` (`auto_hparams/2`); selection, smoke, upload without rsync (`make_flat_upload.py`, flat folder + `UPLOAD_MAP.tsv`), commands. Read 2026-10-21 (§8): U30 957/957 at the optimum; HMSE 129/423 at the target, 0 infeasible (MSE 2024 median gap 0.2 %, MSE 2023 4.4 %). N-2026-10-21-i, -k. |
| [`KS2_CHECK_RUN.md`](KS2_CHECK_RUN.md) | 2026-10-21 | Keep-satisfied SAT moves (`hard.moves.keep_sat: ks2`) built and tested; batch KS2: move {M, ks2} × pop {40, 10} on the 16 MSE instances with hard clauses and a proven optimum, 192 tasks; smoke, commands, pre-registered reading. Read 2026-10-21 (§6): successes m40 12, ks2_10 26 of 48; rule met at pop 10, not at pop 40. N-2026-10-21-e, -g. |
| [`ORACLE900_RUN.md`](ORACLE900_RUN.md) | 2026-10-21 | Batch O900: the strong solver (`configs/strong/auto.yaml`, `hparams: auto`) on 253 instances with an optimum proven in < 900 s (RC2 ≥ 30 s, or EvalMaxSAT), 759 tasks; per-formula selection, smoke, upload, commands. Read 2026-10-21 (§7): soft 729/729 at the optimum (median 0.05 s), MSE 7/30. N-2026-10-21-c, -f. |
| [`AUTO_HPARAMS.md`](AUTO_HPARAMS.md) | 2026-10-21 | Instance-aware v3 hyperparameters (`auto_hparams/1`), chosen at run time inside each job (`hparams: auto`, schema 6): rules R0–R3 by hard/soft, weights and effective size (kernel when the gate passes), evidence per value, dry run on the 582-instance pool, CLI. N-2026-10-21-b. |
| [`STRONG_MEMETIC_S1_RUN.md`](STRONG_MEMETIC_S1_RUN.md) | 2026-10-18 | The stronger memetic built (`impl: v3`, B1–B5, tree `cluster_staging_maxsat_strong/`): deviations, tests, speed, smoke, batch S1 (324 tasks), upload and commands. N-2026-10-18-c. |
| [`STRONGER_MEMETIC_DESIGN.md`](STRONGER_MEMETIC_DESIGN.md) | 2026-10-18 | Stronger memetic B1–B5: motivation, how each works (sources checked), parameters, the interactions between them, and the build plan for the third tree `cluster_staging_maxsat_strong/` (S1–S7) plus a leave-one-out batch. N-2026-10-18-b. |
| [`KERNEL_MEMETIC_RUN.md`](KERNEL_MEMETIC_RUN.md) | 2026-10-18 | Milestone A: the kernel module, gate and shard fields; smoke; the 18-task calib_2sat_sc2 batch (upload list, commands); §5 the proposed stronger memetic (direction B). N-2026-10-18-a. |
