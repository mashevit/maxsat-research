# Index: .md files created from `MSE26_RHO_PRELIM_RESULTS.md` onward

**Created:** 2026-11-03. Covers every new `.md` file in the repo from
`MSE26_RHO_PRELIM_RESULTS.md` (added 2026-10-29 17:27, commit 80dbc66) through
2026-11-03. Docs that already existed and were only edited in this period
(`RESEARCH_NOTES.md`, `NEXT_SESSION_CONTEXT.md`, `README.md`,
`PARKED_FOR_PROJECT_END.md`) are not listed.

## 1. Docs (committed, `docs/current2/`)

| # | Date | File | What it is | Commit |
|---|---|---|---|---|
| 1 | 2026-10-29 | [MSE26_RHO_PRELIM_RESULTS.md](MSE26_RHO_PRELIM_RESULTS.md) | First ρ readout on MSE 2026: batch 3c before the error fixes, both error treatments (fail +0.639, exclude +0.635). N-2026-10-29-a. Preliminary, replaced by #2. | 80dbc66 |
| 2 | 2026-11-01 | [MSE26_RHO_RESULTS_3.md](MSE26_RHO_RESULTS_3.md) | Third ρ readout (the current one): batch 3c after the error fixes, Slurm wall kills counted as failures (fail +0.637, exclude +0.632). Includes the exploratory subsets (§5) and the percent tables (§4.1–4.3). N-2026-11-01-d. | c879315 |
| 3 | 2026-11-01 | [RESEARCH_NOTES_COMPLEMENTARITY_VS_ORTHOGONALITY.md](RESEARCH_NOTES_COMPLEMENTARITY_VS_ORTHOGONALITY.md) | Research note for the paper: on MSE 2026 hardness is correlated but outcomes are complementary; E4 is not orthogonality. N-2026-11-01-e. | 5e1e7aa |
| 4 | 2026-11-01 | [MSE26_MEMETIC_VS_APERTURE.md](MSE26_MEMETIC_VS_APERTURE.md) | Descriptive comparison (not pre-registered) of the memetic vs Aperture, the MSE 2026 anytime winner, on 135 shared instances. N-2026-11-01-i. | a9a9751 |

## 2. ρ analysis reports (generated, not committed)

Script output under `cluster_staging_maxsat_strong/results/`. All use
pre-registration `MSE26_RHO_PREREG.md` r4, seeds 1–3, bootstrap B = 10000.

| Date | Report | Readout | Error treatment |
|---|---|---|---|
| 2026-10-29 | [mse26_rho_fail/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_fail/report.md) | 1 (prelim, source for #1) | fail |
| 2026-10-29 | [mse26_rho_exclude/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_exclude/report.md) | 1 (prelim, source for #1) | exclude |
| 2026-11-01 | [mse26_rho_explore/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_explore/report.md) | 1, exploratory subsets E1–E4 | both |
| 2026-11-01 | [mse26_rho_fixA_fail/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_fixA_fail/report.md) | 2 (after the heap-crash fix A) | fail |
| 2026-11-01 | [mse26_rho_fixA_exclude/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_fixA_exclude/report.md) | 2 (after the heap-crash fix A) | exclude |
| 2026-11-01 | [mse26_rho_r3_fail/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_r3_fail/report.md) | 3 (current, source for #2) | fail |
| 2026-11-01 | [mse26_rho_r3_exclude/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_r3_exclude/report.md) | 3 (current, source for #2) | exclude |
| 2026-11-01 | [mse26_rho_explore_r3/report.md](../../cluster_staging_maxsat_strong/results/mse26_rho_explore_r3/report.md) | 3, exploratory subsets E1–E4 | both |

The two 2026-10-29 reports were written about 20 minutes before #1 was committed.
They are listed because #1 is built from them.

## 3. Personal (gitignored, `personal/`)

| Date | File |
|---|---|
| 2026-11-01 | [DAY_SUMMARY_2026-11-01.md](../../personal/DAY_SUMMARY_2026-11-01.md) |
| 2026-11-01 | [DAY_SUMMARY_2026-11-01_updated.md](../../personal/DAY_SUMMARY_2026-11-01_updated.md) |
| 2026-11-01 | [DAY_SUMMARY_2026-11-01_v2.md](../../personal/DAY_SUMMARY_2026-11-01_v2.md) (latest version) |
