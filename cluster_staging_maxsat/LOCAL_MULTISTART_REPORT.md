# `local_multistart_deeppolish` — implementation report

The no-EA ablation baseline for `memetic_deeppolish`. Written 2026-08-28.

Everything is confined to `cluster_staging_maxsat/`. The repo `src/`,
`configs/`, `tests/` and `docs/` trees were not touched.

---

## Files changed

**New**

- `src/evo/multistart.py` — `run_multistart_ls(wcnf, cfg, rng_seed, target_cost=None, max_total_flips=None)`
- `configs/tier2/local_multistart_deeppolish.yaml`
- `scripts/make_local_multistart_manifest.py`
- `scripts/manifest_tier2_local_multistart.tsv` (130 rows)
- `scripts/tier2_local_multistart_array.sbatch`
- `scripts/submit_tier2_local_multistart.sh`
- `tests/test_local_multistart.py` (23 tests)

**Modified** — the pre-edit original of each is kept alongside it as `<name>.bak`,
byte-identical to `HEAD` (`a6a5a0f`):

| File | Original kept as | Changed lines |
|---|---|---:|
| `src/cli/run_memetic_shard.py` (already in the intentionally-diverged set) | `src/cli/run_memetic_shard.py.bak` | 113 |
| `DIVERGENCE.md` | `DIVERGENCE.md.bak` | 46 |
| `readme.txt` | `readme.txt.bak` | 51 |

The `.bak` suffix follows the existing convention in this repo
(`src/bench/harness.py.bak`, `src/cli/solve_batch.py.bak`, `src/sat/state.py.bak`)
and keeps the originals out of both Python's import path and pytest collection.

**Untouched**: `src/evo/memetic.py`, `src/evo/population.py`, and the other seven
byte-identical files — the `DIVERGENCE.md` §2.2 identity loop still passes clean,
so the committed memetic arm stays bit-for-bit reproducible.

---

## Semantics of the baseline

`random.Random(seed)` drives everything. Per restart:

1. draw a uniform random assignment (`rng.random() < 0.5` per variable);
2. call `evo.operators.short_polish` — *the same function object* `run_memetic`
   calls on every child — with budgets resolved through the same
   `evo.memetic._ls_budget`, seeded `rng.randrange(1 << 30)`;
3. score with `evaluate_assignment`; keep the incumbent by (fewer hard
   violations, then more satisfied soft weight).

The target test is the EA's, verbatim:
`total_soft_weight - satisfied <= target_cost`, feasible only, `<=` not `==`.

Stop order: `target` → `time_cap` → `flip_budget` → `max_restarts`. Restarts are
atomic; caps are checked between them, not inside a polish.

No population, selection, crossover, EA mutation, or generations —
`ea_generations` / `children` come back `None`, not `0`, and the config carries
no `ea:` block (the EA-default injection in the runner is now conditional on the
memetic path).

Record: `solver`, `restarts`, `total_flips`, `flips_in_target_restart`,
`cpu_time_s`, `target_reached`, `max_total_flips` added; all v1 fields
preserved; `SHARD_SCHEMA_VERSION` 1 → 2.

---

## Verification

| Check | Result |
|---|---|
| `cluster_staging_maxsat/tests/` | 44 passed |
| repo `tests/` + `instancegen/tests` | 67 passed |
| eight-file byte-identity invariant | intact |
| `combine_tier2.py` over mixed memetic + multistart shards | 3 shards, 0 anomalies, both arms in one `runs.csv` |
| `bash -n` on both scripts | OK |
| guards: unset / negative / out-of-range task, missing manifest, wrong column count, empty field, missing instance or config, non-integer seed or oracle, unwritable outdir | all exit 2 with a specific message |

Mapping (dry-run through the real script, nothing submitted):

```
task 0   -> row 1    uuf250-0100.cnf seed 1
task 1   -> row 2    uuf250-0100.cnf seed 2
task 4   -> row 5    uuf250-0100.cnf seed 5
task 5   -> row 6    uuf250-066.cnf  seed 1
task 129 -> row 130  uuf250-09.cnf   seed 5
```

Smoke (real tier-2 instance, 20 s):
`status=ok cost=2 hv=0 opt=1 restarts=40 flips=208175 stop=time_cap`.
Flip-cap smoke: `stop=flip_budget restarts=6 flips=31542`.

### Commands

```bash
# smoke (from cluster_staging_maxsat/)
python -m src.cli.run_memetic_shard \
    --instance data/unsat_uuf_diff/uuf250-03.cnf \
    --config configs/tier2/local_multistart_deeppolish.yaml \
    --config-id local_multistart_deeppolish \
    --seed 1 --budget-s 20 --grace-s 15 --oracle-cost 1 --stop-at-oracle \
    --tier T2a --rc2-run uuf_diff_unsat --job-id smoke_t2lms \
    --out results/tier2_local_multistart_smoke/smoke_t2lms.jsonl

# submit the array (NOT run)
bash scripts/submit_tier2_local_multistart.sh
#   -> cd scripts && sbatch --array=0-129%30 tier2_local_multistart_array.sbatch
```

---

## Caveats

1. **The 12,500-flip limit is a ceiling, not the operative budget.** Measured on
   `uuf250-03`: `ls.time_limit_s: 0.5` binds first, at ~5,300 iterations per
   polish. `memetic_deeppolish` has the identical property (same `ls:` block),
   so the arms stay comparable — but "12,500 flips per restart" describes
   neither.
2. **Consequently, runs are not bit-reproducible across machines.** What the
   seed guarantees is the *restart sequence* — restart *k* always starts from
   the same assignment with the same polish seed (tested directly). How far each
   polish gets is wall-clock dependent. The EA arm inherits this too.
   `total_flips` differed by ~2 % between two identical local runs.
3. **Comparability requires `STOP_AT_ORACLE=1` on both arms.** It defaults to 1
   here (the baseline is *defined* by stopping at the target) and to 0 in
   `tier2_memetic_array.sbatch`. The committed memetic results were run with it
   on.
4. **Uniform vs JW seeding is a live choice.** The EA seeds its population from
   a Jeroslow–Wang prior; this baseline defaults to unbiased uniform, so it
   ablates seeding *and* the operators together. `multistart.init: jw` isolates
   the operators alone — that is a different arm and would need its own
   `config_id`.
5. **The 8 `uuf_diff_unsat` instances of the 26 ran against RC2 at cap 600, not
   900** — the pre-existing caps mismatch documented in `DIVERGENCE.md` applies
   unchanged.
6. `combine_tier2.py` (repo `src/`, out of scope) still ignores
   `time_to_target_s`, and now also `restarts` / `flips_in_target_restart` /
   `target_reached`. Surfacing those in `summary.csv` remains a follow-up.

Nothing committed or pushed; no SLURM job submitted; no paper or TODO touched.
