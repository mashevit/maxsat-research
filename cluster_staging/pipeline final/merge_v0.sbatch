#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:45:00
#SBATCH --job-name gsm8k-merge
#SBATCH --output merge-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4

set -euo pipefail
source "$HOME/gsm8k_lora_v2/env.sh"
cd "$KIT"

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

python merge_export.py \
    --base "$BASE" \
    --adapter "$ADAPTER" \
    --merged "$MERGED" \
    --n 5

# Nonzero exit == fidelity gate failed == do not run gguf.sbatch.
