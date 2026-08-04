# Tier-2 Memetic — What I Built

Executive summary of [`docs/TIER2_MEMETIC_PLAN.md`](TIER2_MEMETIC_PLAN.md),
which holds the full plan, the measurements, and the reproduction commands.
Written 2026-08-04.

---

## What I built

**Doc:** `docs/TIER2_MEMETIC_PLAN.md` — the plan, the scripts, and §6 on
combining RC2 + memetic results.

**Repo (`src/`, `configs/`):**

- `src/bench/make_tier2_manifest.py` — reads `results/hardness/`, selects
  tier 2, resolves + checksums instances, emits manifest/oracle/skip-list
- `src/cli/run_memetic_shard.py` — one (instance, config, seed, budget) → one
  provenance-complete JSONL record
- `src/bench/combine_tier2.py` — joins shards against the RC2 oracle, emits
  `runs.csv` / `by_instance.csv` / `summary.csv` / `integrity.txt`
- `configs/tier2/{memetic_base,memetic_pop150,memetic_deeppolish}.yaml`

**Staging (`cluster_staging_maxsat/`):** `tier2_memetic_array.sbatch` +
`smoke_tier2_memetic.sbatch`, the generated `manifest_tier2_memetic.tsv`
(780 lines, line N = array task N), `tier2_oracle.csv`, `tier2_skipped.txt`;
plus the full memetic dependency closure (`evo/`, `sat/`, `llm/`,
`__init__.py`s, configs) — all byte-identical to `src/`.

---

## Three findings you should know before submitting

**1. Two of the 28 tier-2 instances cannot run.** Both MSE instances are
new-format WCNF (no `p` line, `h`-prefixed hards). `src/sat/cnf.py:parse_dimacs`
throws `ValueError: invalid literal for int(): 'h'`; the `_parse_wcnf` fallback
fails too. RC2 read them because PySAT supports the format. So tier-2 memetic
covers the SATLIB random-3-SAT half only — no structured instance in the
runnable set. The manifest generator detects and skips them with a reason rather
than emitting jobs that die on a node. Fix is ~20 lines in `parse_dimacs`; they
then flow in automatically.

**2. `run_memetic`'s `max_gens` defaults to 100**, so a 300 s budget would have
silently ended early and `wall_time_s` would have been meaningless. All three
tier-2 configs set it to 1000000 so wall-clock is the sole stop condition.

**3. The default grid is probably past saturation.** Measured: at an 8 s budget
the EA already hit the RC2 optimum on `uuf250-0100` (RC2 took 219 s) and
`uuf250-094` (RC2: 130 s). It also completed only 3 generations in those 8 s —
at 60 s the result is dominated by the WalkSAT polish run 171×, not by
evolution. I'd run `--budgets 1 5 10 30` first before committing the 39
solver-hours of the default 60/300 grid. §7 of the doc says this plainly.

---

## On combining (§6)

Join on `instance_sha256` via the oracle table — the RC2 records have no
checksum, which is the gap `RC2_STATUS` §4.5 couldn't close. Both sides use
unsatisfied soft weight, so `best_cost − final_cost` is direct; but I recompute
cost from the assignment rather than trusting `best_soft_weight` (which is the
satisfied weight). Headline metric should be hit rate, not `rel_gap` — 24 of the
26 instances have OPT = 1, so missing one clause reads as a 100 % relative gap.
