#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=uuf250-1kc
#SBATCH --array=1-100%20
#SBATCH --time=00:18:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/uuf250-1kc-%A_%a.out
#SBATCH --error=logs/uuf250-1kc-%A_%a.err

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" scripts/manifest_uuf250_1000c.txt)
echo "instance=${INSTANCE}"

mkdir -p results/profile_uuf250

# NOTE: no --bestknown. These are uniform-random UNSAT 3-SAT instances with no
# reference optima, so best_known is absent and assign_tier() leaves both
# `ratio` and `lb_ratio` null. T1/T2a/T2b/T3 are still assigned (time-based);
# only the normalized progress ratio is unavailable. See chat notes.
python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap 900 \
    --grace 60 \
    --out results/profile_uuf250/uuf250_arr_task_${SLURM_ARRAY_TASK_ID}.jsonl

echo "end=$(date -Iseconds) exit=$?"
