#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse23-full
#SBATCH --array=1-75%20
#SBATCH --time=00:35:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse23-full-%A_%a.out
#SBATCH --error=logs/mse23-full-%A_%a.err

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" scripts/manifest_mse23_full.txt)
echo "instance=${INSTANCE}"

mkdir -p results/profile_cap1800

python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap 1800 \
    --grace 120 \
    --bestknown data/raw/mse_2024/bestknown_mse23.csv \
    --out results/profile_cap1800/mse23_full_arr_task_${SLURM_ARRAY_TASK_ID}.jsonl

echo "end=$(date -Iseconds) exit=$?"
