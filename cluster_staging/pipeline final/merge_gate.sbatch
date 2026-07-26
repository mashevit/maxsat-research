#!/bin/bash
#SBATCH --job-name=merge_gate
#SBATCH --output=logs/merge_gate_%j.out
#SBATCH --error=logs/merge_gate_%j.err
#SBATCH --time=01:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=65536
#SBATCH --gpus=rtx_6000:1

set -euo pipefail

module load anaconda
source activate gsm8k_lora

KIT="$HOME/gsm8k_lora_v2"
BASE="Qwen/Qwen3-8B"                 # FULL-PRECISION base. Never the -bnb-4bit repo.
ADAPTER="$KIT/qwen3_8b_lora_model"   # train.py --output_dir
MERGED="$KIT/merged_16bit"           # fp16 common ancestor


mkdir -p logs

echo "------------------------------------"
date
echo "SLURM_JOBID:            ${SLURM_JOBID}"
echo "SLURM_JOB_NODELIST:     ${SLURM_JOB_NODELIST}"
echo "------------------------------------"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader


cd "${KIT}"
export PYTHONPATH="${KIT}:${PYTHONPATH:-}"
export TOKENIZERS_PARALLELISM=false
export CUBLAS_WORKSPACE_CONFIG=:4096:8   # deterministic cuBLAS reductions

# ---------------------------------------------------------------------------
# Pre-check: if a merged dir already exists, report its dtype before touching it.
# Non-fatal here — merge_export.py --overwrite will replace it anyway.
# ---------------------------------------------------------------------------
if [ -f "${MERGED}/config.json" ]; then
  echo "[pre] existing merged dir found, reading declared dtype:"
  python -c "import json,sys; c=json.load(open('${MERGED}/config.json')); print('[pre] dtype =', c.get('dtype') or c.get('torch_dtype'))"
else
  echo "[pre] no existing merged dir at ${MERGED}"
fi

# ---------------------------------------------------------------------------
# Merge + export + gate. Exits nonzero on gate failure; set -e stops the job.
# ---------------------------------------------------------------------------
python merge_export.py \
  --base "${BASE}" \
  --adapter "${ADAPTER}" \
  --merged "${MERGED}" \
  --atol 0.05 \
  --min-top1 0.999 \
  --max-len 512 \
  --overwrite

# ---------------------------------------------------------------------------
# Post-check: independent dtype read of what was actually written to disk.
# ---------------------------------------------------------------------------
echo "[post] verifying written merged config dtype:"
python -c "import json; c=json.load(open('${MERGED}/config.json')); d=c.get('dtype') or c.get('torch_dtype'); print('[post] dtype =', d); raise SystemExit(0 if d=='float16' else 1)"

echo "[post] shard inventory:"
ls -la "${MERGED}"
du -sh "${MERGED}"

echo "[done] gate passed — safe to submit gguf.sbatch"
date
