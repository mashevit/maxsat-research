#!/bin/bash

################################################################################
# merge.sbatch -- merge LoRA adapter onto fp16 base, export, gate the artifact.
#
#   sbatch merge.sbatch
#
# Exits nonzero if the gate fails. Do not run gguf.sbatch unless this exits 0.
# If merged_16bit already exists this refuses to clobber it; use gate.sbatch to
# re-gate, or pass --overwrite below to force a re-merge.
################################################################################

#SBATCH --job-name=merge_gate
#SBATCH --output=logs/merge_gate-%j.out
#SBATCH --error=logs/merge_gate-%j.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=65536
#SBATCH --gpus=rtx_6000:1
#SBATCH --time=01:00:00

echo "------------------------------------"
date
echo "SLURM_JOBID:            $SLURM_JOBID"
echo "SLURM_JOB_NODELIST:     $SLURM_JOB_NODELIST"
echo "SLURM_SCRATCH_DIR:      $SLURM_SCRATCH_DIR"
echo "------------------------------------"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader

set -euo pipefail



module load anaconda
source activate gsm8k_lora

KIT="$HOME/gsm8k_lora_v2"
BASE="Qwen/Qwen3-8B"                 # FULL-PRECISION base. Never the -bnb-4bit repo.
ADAPTER="$KIT/qwen3_8b_lora_model"   # train.py --output_dir
MERGED="$KIT/merged_16bit"           # fp16 common ancestor



export BASE_ID="Qwen/Qwen3-8B"
export ADAPTER_DIR="$KIT/qwen3_8b_lora_model"
export MERGED_DIR="$KIT/merged_16bit"

# Keep HF caches off the home quota.
export HF_HOME="${HF_HOME:-/home/mashevit/.cache/huggingface}"
export TOKENIZERS_PARALLELISM=false


python merge_export.py --mode merge+gate
rc=$?

echo "[sbatch] merge_export.py exit code = $rc"
if [ $rc -ne 0 ]; then
  echo "[sbatch] GATE DID NOT PASS -- do not submit gguf.sbatch"
fi
exit $rc
