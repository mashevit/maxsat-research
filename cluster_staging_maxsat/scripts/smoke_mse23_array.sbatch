#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse23-smoke-arr
#SBATCH --array=1-5
#SBATCH --time=00:05:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse23-smoke-arr-%A_%a.out
#SBATCH --error=logs/mse23-smoke-arr-%A_%a.err

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" scripts/manifest_mse23_smoke.txt)
echo "instance=${INSTANCE}"

python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap 30 \
    --grace 15 \
    --bestknown data/raw/mse_2024/bestknown_mse23.csv \
    --out results/profile/mse23_smoke_arr_task_${SLURM_ARRAY_TASK_ID}.jsonl

echo "end=$(date -Iseconds) exit=$?"
