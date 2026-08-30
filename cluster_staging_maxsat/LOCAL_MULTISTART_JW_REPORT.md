# `local_multistart_jw_deeppolish` — work-order completion report

**Date: 2026-08-30.** The third ablation arm: `local_multistart_deeppolish` with
Jeroslow-Wang seeding instead of uniform random seeding. Companion to
[`LOCAL_MULTISTART_REPORT.md`](LOCAL_MULTISTART_REPORT.md); divergence record in
[`DIVERGENCE.md`](DIVERGENCE.md) §"The JW-seeded ablation arm (2026-08-30)".

The three-arm design this completes:

```
memetic_deeppolish  - local_multistart_jw   population / crossover / EA
local_multistart_jw - local_multistart      JW initialisation
memetic_deeppolish  - local_multistart      the whole package
```

## The critical item

`population.py` seeds in two pieces, and the seeding is **already stochastic**:
`jw_priors(wcnf)` computes the prior vector once,
`Population._new_assign_from_priors(pri)` does the biased per-variable draw
(`rng.random() < pri[v]`), and `init_seeds` calls the first once and the second
`size` times. The `[0.05, 0.95]` clip makes degeneracy structurally impossible —
200 draws on `uuf250-0100.cnf` gave 200 distinct starts.

`multistart.init: jw` **already existed** but inlined a copy of the draw loop. It
now calls the method, via `_jw_seeder` returning
`(Population(n_vars, 0, rng), jw_priors(wcnf))`. Per the chosen route,
`population.py` is untouched — promoting the draw to module level there is the
cleaner refactor and is blocked by the §2.2 invariant; calling `init_seeds` per
restart was rejected because it recomputes `jw_priors` over every clause each
time, an O(n_clauses) cost borne by the JW arm alone.

Verified both `init` modes reproduce the previous implementation's output **and**
leave `random.Random` in the identical state over 50 draws — the uniform arm's
semantics are byte-preserved.

## Results

**Config diff.** Semantically the only difference is `multistart.init`
(`uniform` → `jw`); keys and the `ls:` block are identical, asserted in
`test_jw_config_is_the_uniform_config_but_for_init`. The textual diff is that
line plus comments.

**Manifest.** 130 rows, 9 fields, same 26 instances, seeds {1..5}, budget 900,
prefix `t2lmsjw` (0 job_id collisions with the uniform arm). Oracle cross-check
joined on `instance_sha256`: **26/26, 0 mismatches**, both arms agreeing with
`tier2_oracle.csv`, and that table's digests still matching the bytes on disk. A
bare `make_local_multistart_manifest.py` still regenerates the uniform manifest
**byte-identically**.

**Sbatch.** Confirmed it needs no edit; `git status` shows it unmodified, so
there is no `.bak`. It reads `MANIFEST`/`OUTDIR` from the environment and the
submitter passes them via `--export`. Two guards worth knowing about: the JW
submitter **refuses a passthrough `--export`** (sbatch honours the last one, so
yours would silently run the JW array against the uniform manifest into the
uniform results tree — use env vars instead) and refuses a manifest whose
`config_id` column is not the JW one.

**Dry-runs.** Task→row mapping correct at ids 0/1/4/5/9/64/125/129; all 26
instances get exactly 5 consecutive rows; out-of-range guard correct. Both
submitters dry-run clean.

**20 s smoke** (not a measurement) on `uuf250-0100.cnf`, oracle 1: uniform cost
3, jw cost 2, memetic cost 1 — 40 restarts per multistart arm.
`combine_tier2.py` over all three `config_id`s produced three `summary.csv` rows
and three `by_instance.csv` rows, no pooling, nothing dropped, integrity clean.
**No change needed there.**

**Tests.** 37 in the file, 58 across the staging suite, all passing. One change
beyond adding tests: `test_module_uses_no_evolutionary_operators` scanned only
the source range from `def run_multistart_ls` onward, so any helper defined
above it could reintroduce a population unchecked. It now walks the **AST** of
the whole module — banned operators checked as calls, `Population(` permitted
exactly once in `_jw_seeder` with a literal `0` size. The AST was necessary
anyway: a module-wide text scan collides with the docstring's own "no crossover"
claim.

**Docs.** `DIVERGENCE.md` and `readme.txt` updated, both `.bak` originals
untouched. The eight-file invariant passes clean, and nothing outside
`cluster_staging_maxsat/` was modified.

## Caveat for reading the results later

The arms differ in seeding *and* inherit the preset's wall-clock-bound polish, so
`total_flips` and the returned assignment still are not bit-reproducible across
machines. That applies equally to all three arms, so the comparison holds, but a
per-arm flip count is not a stable quantity.

## No SLURM job was submitted

Both submitters were exercised with `DRY_RUN=1` only, plus the single-task 20 s
smoke of each arm described above.
