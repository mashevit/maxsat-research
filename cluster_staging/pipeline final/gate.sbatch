#!/bin/bash

################################################################################
# gate.sbatch -- re-run the merge-fidelity gate against the merged model that
# already exists on disk. Does not merge. Does not write anything.
#
#   sbatch gate.sbatch
#
# This is the one to use when you only want to re-check the artifact (e.g. after
# changing gate thresholds or gate items). Cheaper than merge.sbatch by one
# merge_and_unload + save_pretrained, and touches nothing.
################################################################################

#SBATCH --job-name=gate_only
#SBATCH --output=logs/gate_only-%j.out
#SBATCH --error=logs/gate_only-%j.err
#SBATCH --cpus-per-task=4
#SBATCH --mem=65536
#SBATCH --gpus=rtx_6000:1
#SBATCH --time=00:30:00

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

export HF_HOME="${HF_HOME:-/home/mashevit/.cache/huggingface}"
export TOKENIZERS_PARALLELISM=false


python merge_export.py --mode gate-only
rc=$?

echo "[sbatch] merge_export.py exit code = $rc"
exit $rc
