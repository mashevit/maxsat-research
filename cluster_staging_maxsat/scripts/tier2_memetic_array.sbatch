#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=t2-memetic
#SBATCH --time=00:20:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/t2-memetic-%A_%a.out
#SBATCH --error=logs/t2-memetic-%A_%a.err

# Tier-2 memetic EA array driver.
#
# One array task == one manifest line == one (instance, config, seed, budget)
# run. The array range is NOT baked in: pass it at submit time so the manifest
# stays the single source of truth.
#
#   sbatch --array=1-390%30 scripts/tier2_memetic_array.sbatch
#
# Overridable at submit time:
#   MANIFEST        manifest to read            (default scripts/manifest_tier2_memetic.tsv)
#   OUTDIR          where shards land           (default results/tier2_memetic/tasks)
#   GRACE           watchdog margin in seconds  (default 60)
#   STOP_AT_ORACLE  1 => stop each run the moment it reaches the manifest's
#                   oracle_cost, making wall_time_s a time-to-optimum
#                   measurement (default 0 = run the full budget)
#
#   sbatch --array=1-100 --export=ALL,OUTDIR=results/t2_rerun \
#          scripts/tier2_memetic_array.sbatch
#   sbatch --array=1-390%30 --export=ALL,STOP_AT_ORACLE=1 \
#          scripts/tier2_memetic_array.sbatch
#
# --time must cover the LARGEST budget in the manifest plus grace and startup.
# SLURM applies one wall limit to the whole array, so the limit is set by the
# largest budget even if most tasks are shorter. 20 min covers the current
# 900 s budget plus the 60 s default GRACE (960 s = 16 min) with ~4 min of
# margin for `module load`, conda activation and instance parsing. A 15 min
# limit does NOT fit a 900 s budget: every task that ran to the cap would be
# killed at the moment it was about to write its record.
# STOP_AT_ORACLE does not relax this -- a run that never reaches the optimum
# still spends the full budget.

set -euo pipefail

MANIFEST="${MANIFEST:-scripts/manifest_tier2_memetic.tsv}"
OUTDIR="${OUTDIR:-results/tier2_memetic/tasks}"
GRACE="${GRACE:-60}"
STOP_AT_ORACLE="${STOP_AT_ORACLE:-0}"

echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

# Single-threaded: the EA is scalar Python and we bill one CPU per task.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: $MANIFEST" >&2
    exit 2
fi

LINE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST")
if [[ -z "$LINE" ]]; then
    echo "FATAL: no line ${SLURM_ARRAY_TASK_ID} in $MANIFEST" >&2
    exit 2
fi

# job_id instance config config_id seed budget_s oracle_cost tier rc2_run
IFS=$'\t' read -r JOB_ID INSTANCE CONFIG CONFIG_ID SEED BUDGET ORACLE TIER RC2_RUN <<< "$LINE"

echo "job_id=${JOB_ID} instance=${INSTANCE} config_id=${CONFIG_ID} seed=${SEED} budget=${BUDGET}s oracle=${ORACLE} tier=${TIER}"

mkdir -p "$OUTDIR"

# Opt-in target-cost early stop. Off by default: an oracle-terminated run is a
# benchmarking mode, not a solver mode, and nothing should enter it by accident.
EXTRA_ARGS=()
if [[ "$STOP_AT_ORACLE" == "1" ]]; then
    EXTRA_ARGS+=(--stop-at-oracle)
fi

python -m src.cli.run_memetic_shard \
    --instance "$INSTANCE" \
    --config "$CONFIG" \
    --config-id "$CONFIG_ID" \
    --seed "$SEED" \
    --budget-s "$BUDGET" \
    --grace-s "$GRACE" \
    --oracle-cost "$ORACLE" \
    --tier "$TIER" \
    --rc2-run "$RC2_RUN" \
    --job-id "$JOB_ID" \
    --out "${OUTDIR}/${JOB_ID}.jsonl" \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}

echo "end=$(date -Iseconds) exit=$?"
