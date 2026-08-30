# Running the MSE manifest on SLURM

How to submit `scripts/manifest_tier2_mse.tsv` (the two MSE 2023 instances
unblocked in `c3f2426`) through the existing tier-2 memetic array driver, and
what was verified before submitting.

Written 2026-08-30 against `404b7e6`.

## What I verified

| Needed | Status |
|---|---|
| `scripts/manifest_tier2_mse.tsv` (30 rows) | present, committed in `c3f2426` |
| `scripts/tier2_memetic_array.sbatch` | present, unchanged — takes `MANIFEST`/`OUTDIR` as submit-time overrides, no new sbatch needed |
| `src/sat/cnf.py` new-format WCNF parser | still in HEAD (`_parse_new_format`, dispatch at `parse_dimacs`) — both instances parsed locally: 293 → 18508 vars / 134220 clauses, 385 → 6604 vars / 48372 clauses, matching DIVERGENCE.md |
| `run_memetic_shard.py` refusal branch | gone; every flag the sbatch passes (`--stop-at-oracle`, `--oracle-cost`, `--tier`, `--rc2-run`) still exists. Later commits (`3c94f8d`/`404b7e6`) added the multistart path but didn't break the memetic args |
| The 2 `.wcnf` instances | present at the exact manifest paths |
| `configs/tier2/memetic_{base,pop150,deeppolish}.yaml` | present |
| `scripts/logs/` | exists (SLURM silently drops output if missing) |

Nothing needs restoring from an older revision: the working tree is at HEAD and
clean for `src/`, `scripts/`, `configs/`, `tests/`.

## Two things that are actually missing on the cluster side

1. **`data/` is not in git at all** (0 tracked files). The `.wcnf` files only
   exist in the local staging dir — they have to go over by rsync, per
   `readme.txt`:

   ```bash
   rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
   ```

2. **PyYAML.** The workstation env doesn't have it and a shard dies immediately
   with `Cannot read configs/tier2/memetic_base.yaml: PyYAML is not installed`.
   Confirm in the `maxsat` env first:

   ```bash
   python -c "import yaml; print(yaml.__version__)"
   ```

## The submit

From `~/maxsat-lab/scripts` (the `#SBATCH --output=logs/...` is submit-dir
relative; the script's first act is `cd ..`, so `MANIFEST` must be
root-relative):

```bash
cd ~/maxsat-lab/scripts
sbatch --array=1-30%15 \
  --job-name=t2-mse --output=logs/t2-mse-%A_%a.out --error=logs/t2-mse-%A_%a.err \
  --export=ALL,MANIFEST=scripts/manifest_tier2_mse.tsv,OUTDIR=results/tier2_mse/tasks \
  tier2_memetic_array.sbatch
```

`--array` is **1-based** here — `tier2_memetic_array.sbatch` does
`sed -n "${SLURM_ARRAY_TASK_ID}p"`. Only the local_multistart driver is 0-based;
don't copy `0-129` out of the submit wrappers.

Add `STOP_AT_ORACLE=1` to the export list if you want `wall_time_s` to be
time-to-optimum (it defaults to 0 = spend the full 900 s). Note the multistart
arms were run with `STOP_AT_ORACLE=1`, so match it if you intend to compare.

`OUTDIR` is optional — job ids are `t2mse_`-prefixed precisely so they can't
collide in the shared `results/tier2_memetic/tasks` — but a separate dir keeps
the two manifests' shards apart.

## Shard-field verification: strictly additive, nothing lost

Checked whether `3c94f8d` / `404b7e6` (the local_multistart arms) dropped or
renamed any field the memetic-era shards carried.

`SHARD_SCHEMA_VERSION` went 1 -> 2 at `3c94f8d`. Three key sets compared: a real
v1 memetic shard on disk, a real v2 multistart shard on disk, and every key the
HEAD source can write (dict literal plus later `rec["..."] =` assignments,
extracted via `ast`):

```
v1 memetic shard          47 keys
v2 multistart shard       52 keys
HEAD source               52 keys

v1 keys missing from HEAD    NONE
v1 shard - v2 shard          NONE
added by HEAD vs v1          cpu_time_s, flips_in_target_restart,
                             max_total_flips, restarts, target_reached
```

On the memetic path the five new fields behave as: `cpu_time_s` populated
(process CPU across the solver call -- additive, wall time is unchanged);
`restarts` and `flips_in_target_restart` stay `null`, both set only inside
`if solver == "local_multistart"`; `max_total_flips` `null` -- the flag is
rejected with FATAL for any non-multistart solver rather than silently ignored;
`target_reached` `null` unless `STOP_AT_ORACLE=1`, then
`stop_reason == "target"` (`null` keeps "missed it" distinguishable from "was
not asked to look for it").

The memetic-only fields are intact: `ea_generations` and `children` are still
assigned unconditionally from `meta`, and the `ea.enabled` default is applied
under `if solver == DEFAULT_SOLVER`, which all three `memetic_*.yaml` configs
select. `solver` itself now varies and is recorded per row.

One consequence worth knowing: the new MSE shards will be `schema_version: 2`
while the 390 existing memetic shards on disk are `schema_version: 1`. That mix
is safe -- `src/bench/combine_tier2.py` never reads `schema_version` and groups
by `config_id`. Note it lives at the repo root `src/bench/`, not in the staging
tree, so combining happens on the workstation after the shards are pulled back,
not on the cluster.

## Caveats already recorded in DIVERGENCE.md

- `00000293` is **T3, not tier 2**: RC2 needed 1313 s to prove cost 43, against
  the 900 s budget these rows carry. Don't fold it into tier-2 aggregates
  without a note.
- A 60 s smoke on `00000385` ended `hard_violations=1` — infeasible, so
  gap/optimality came back `null`. Feasibility at 900 s is unconfirmed; check
  `hard_violations` in the shards before reading anything into the numbers.
- `readme.txt` documents the memetic and multistart arrays but has no section
  for `manifest_tier2_mse.tsv`; this file is that section until it gets folded
  in.
