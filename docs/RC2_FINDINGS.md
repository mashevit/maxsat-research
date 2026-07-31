# RC2 Profiling — What I Found

Executive summary of the read-only audit in [`docs/RC2_STATUS.md`](RC2_STATUS.md),
which holds the full evidence, schema, tables, and the commands used to compute
every number. Written 2026-07-31 against `HEAD = 63f3ae5` (working tree clean).

---

## 1. What was done

Four RC2 profiling runs live under `results/hardness/`. The solver chain is
`src/cli/profile_hardness.py` → subprocess → `src/cli/solve_rc2_anytime.py`,
whose entire RC2 construction is `RC2(wcnf, solver=solver)` — **plain RC2,
Glucose 3 backend, adapt/exhaust/minz/incr/trim all at PySAT defaults (off)**.
Caps/graces are reconstructible from the data: 600/60, 1800/120, 900/60, 600/60.

The SLURM driver for these runs is **not in the repo**. The only MaxSAT sbatch is
`cluster_staging/scripts/smoke_mse23.sbatch`, a non-array 5-instance smoke test
at `--cap 30` that cannot have produced any committed result. So array specs,
`--mem`, cpus, wall limits, and job IDs are **unknown** — `PROVENANCE.txt`
already flags this gap and its `<FILL IN>` fields are still blank.

Also worth flagging up front: **the tiers are an output, not an input** — no job
was ever submitted "for tier2". T1/T2a/T2b/T3 come from `assign_tier()` using
hard-coded 60/300/600 s cutoffs that ignore `--cap`.

## 2. Output format

~270 KB total: per-task JSONL shards plus `all_results.{jsonl,csv}` and two
summaries per run. Full 15-key schema documented with types, units, and
nullability measured over all 235 records. Key units point: `final_cost` is
**unsatisfied** soft weight (lower is better), not satisfied weight.

**No stdout/stderr logs exist** for these runs, so SLURM exit codes and MaxRSS
are unrecoverable; core counts were never captured at all.

Join key: `instance`/basename/stem are each unique *within* a run, but 75
basenames repeat across the two MSE runs — the global key is
`(run_dir, instance)`. There is no `sha256` in the schema.

## 3. Statistics

235 records / 160 distinct instances. 76 solved (32%), 159 timeouts, **0 crashes,
0 missing**. RC2 solves 1/75 MSE instances at 600 s and 2/75 at 1800 s —
tripling the budget bought one instance. 23 of 76 solves finish under 1 s; 70 of
76 under 300 s. **No instance has OPT = 0** (all corpora are unsatisfiable by
construction), and the SATLIB cost distribution is nearly degenerate: 65 of 73
solved random instances have OPT = 1.

## 4. Integrity

Aggregation is lossless and all 235 tier labels match the rule. Real problems
found:

- **The 85 SATLIB instances profiled are not in the repo**
  (`data/unsat250_1000c/`, `data/unsat_uuf_diff/` were never committed).
  Basename lookup resolves them, but PySAT parses the committed SATLIB copies'
  `%`/`0` trailer as 2 empty soft clauses — which would force OPT ≥ 2,
  contradicting the recorded OPT = 1. Those two runs are **not reproducible as
  committed**.
- **One record is `completed=true` and `tier="T3"`** — solved to optimality in
  1313 s, past the hard-coded 600 s cutoff. Internally consistent, but `T3` is
  documented as "no optimum available", so anything reading tiers will be wrong
  about the one MSE instance that *does* have an oracle label beyond 600 s.
- **17 records have neither cost nor lower bound** — RC2's first SAT call never
  returned.
- **`uuf250_1000c` task indices run 66–100**, the only run where index ≠ sorted
  position; whether a 1–65 batch existed is unknown.
- **`mse_cap1800/tasks/` reuses `mse23_full_arr_task_*.jsonl` filenames** — a
  silent-overwrite hazard on any flat re-aggregation.
- **`ratio`/`lb_ratio`** — the schema's only quality signals — are structurally
  null on both SATLIB runs (no `--bestknown` passed), i.e. on exactly the two
  runs that produce a usable T1/T2 spread.

On the positive side, the cross-cap comparison passes a real check: **zero
instances had their lower bound decrease** when given 3× the budget, which
validates the SIGKILL LB-recovery path.
