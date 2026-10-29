#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse26-memetic
#SBATCH --time=01:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse26-memetic-%A_%a.out
#SBATCH --error=logs/mse26-memetic-%A_%a.err

# Batch 3c array driver: the memetic on MSE 2026 (docs/current2/MSE26_3C_RUN.md, repo).
# One array task == one manifest line == one (instance, seed) run of
# configs/strong/auto.yaml. Submit through scripts/submit_mse26.sh, which sets
# --array, --mem (the part's memory bin) and the exports.
#
# Fixed here, not overridable (MSE26_RHO_PLAN.md §9):
#   --stop-at-oracle         stop at the published optimum (manifest column 7)
#   --budget-clock process   the budget counts the process CPU from its start
#                            (start-up, imports, hash, parse, kernel gate, hparams)
# Overridable at submit time:
#   MANIFEST   (required) scripts/manifest_mse26_<part>.tsv
#   OUTDIR     where shards land (default results/mse26_memetic/tasks)
#   GRACE      watchdog margin in seconds (default 300; COMPILED_MEMETIC_PLAN.md §8 C4)
#
# --time 1 h: 1,800 s budget + 300 s grace + the first read of a large file
# (~150 s for 2 GiB on NFS, COMPILED_MEMETIC_PLAN.md §14) + conda, with margin.
# The wrapper's own wall (module load, conda) is logged (WRAP_* lines), not
# counted in the record's CPU fields.

set -uo pipefail

MANIFEST="${MANIFEST:?set MANIFEST (use scripts/submit_mse26.sh)}"
OUTDIR="${OUTDIR:-results/mse26_memetic/tasks}"
GRACE="${GRACE:-300}"

W0=$(date +%s.%N)
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

# Single-threaded: one CPU per task.
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

echo "job_id=${JOB_ID} instance=${INSTANCE} seed=${SEED} budget=${BUDGET}s oracle=${ORACLE} grace=${GRACE}"

mkdir -p "$OUTDIR"

W1=$(date +%s.%N)
python -m src.cli.run_memetic_shard \
    --instance "$INSTANCE" \
    --config "$CONFIG" \
    --config-id "$CONFIG_ID" \
    --seed "$SEED" \
    --budget-s "$BUDGET" \
    --grace-s "$GRACE" \
    --oracle-cost "$ORACLE" \
    --stop-at-oracle \
    --budget-clock process \
    --tier "$TIER" \
    --rc2-run "$RC2_RUN" \
    --job-id "$JOB_ID" \
    --out "${OUTDIR}/${JOB_ID}.jsonl"
rc=$?
W2=$(date +%s.%N)

echo "WRAP_PRE_S  $(awk -v a="$W0" -v b="$W1" 'BEGIN{printf "%.2f", b-a}')   (module load + conda + manifest line; not in the record)"
echo "WRAP_RUN_S  $(awk -v a="$W1" -v b="$W2" 'BEGIN{printf "%.2f", b-a}')   (the python process, wall)"
echo "end=$(date -Iseconds) exit=${rc}"
exit $rc
