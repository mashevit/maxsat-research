#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=t2-memetic-smoke
#SBATCH --array=1-5
#SBATCH --time=00:05:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/t2-memetic-smoke-%A_%a.out
#SBATCH --error=logs/t2-memetic-smoke-%A_%a.err

# Smoke test for the tier-2 memetic pipeline: same code path as
# tier2_memetic_array.sbatch, first 5 manifest lines, 10 s budget instead of
# whatever the manifest says. Run this once after every rsync of the staging
# tree -- it catches a missing conda package, a stale manifest and a broken
# import in about a minute, which is much cheaper than finding out on task 400.
#
#   sbatch scripts/smoke_tier2_memetic.sbatch
#
# Expect 5 shards in results/tier2_memetic_smoke/ with status "ok". A 10 s
# budget will NOT reach the optimum on tier-2 instances; a non-zero abs_gap
# here is the expected outcome, not a failure.

set -euo pipefail

MANIFEST="${MANIFEST:-scripts/manifest_tier2_memetic.tsv}"
OUTDIR="${OUTDIR:-results/tier2_memetic_smoke}"
BUDGET="${BUDGET:-10}"

echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

LINE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST")
IFS=$'\t' read -r JOB_ID INSTANCE CONFIG CONFIG_ID SEED BUDGET_IGNORED ORACLE TIER RC2_RUN <<< "$LINE"

echo "job_id=${JOB_ID} instance=${INSTANCE} config_id=${CONFIG_ID} seed=${SEED} budget=${BUDGET}s(smoke) oracle=${ORACLE}"

mkdir -p "$OUTDIR"

python -m src.cli.run_memetic_shard \
    --instance "$INSTANCE" \
    --config "$CONFIG" \
    --config-id "$CONFIG_ID" \
    --seed "$SEED" \
    --budget-s "$BUDGET" \
    --grace-s 30 \
    --oracle-cost "$ORACLE" \
    --tier "$TIER" \
    --rc2-run "$RC2_RUN" \
    --job-id "smoke_${JOB_ID}" \
    --out "${OUTDIR}/smoke_${JOB_ID}.jsonl"

echo "end=$(date -Iseconds) exit=$?"
