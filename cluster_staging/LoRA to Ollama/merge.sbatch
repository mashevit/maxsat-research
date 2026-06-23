#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:30:00                        ### 4-8 min typical for 3B; headroom
#SBATCH --job-name gsm8k-merge
#SBATCH --output merge-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4

# Step 1: merge LoRA adapter into base -> ./merged_16bit (16-bit HF dir).
# For Qwen3-8B later: bump --mem to 48G and --time to 0-01:00:00.

set -euo pipefail
echo "Job $SLURM_JOB_ID on $(hostname) starting $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

module load anaconda
source activate gsm8k_lora

ADAPTER=${1:-./gsm8k_lora_model}
OUT=${2:-./merged_16bit}

python merge_export.py --adapter "$ADAPTER" --out "$OUT" --max-seq-len 2048

echo "Merge finished $(date). Output in $OUT"
