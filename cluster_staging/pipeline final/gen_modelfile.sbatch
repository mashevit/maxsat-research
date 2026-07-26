#!/bin/bash
#SBATCH --job-name=gen-modelfile
#SBATCH --partition main
#SBATCH --time=00:05:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
# NOTE: #SBATCH lines are parsed before shell expansion — $HOME does NOT work here.
#SBATCH --output=logs/gen-modelfile-job-%j.out
#SBATCH --error=logs/gen-modelfile-job-%j.out

# ---- ENV (copy verbatim from train.sbatch) -----------------------------
# module load ...
# source /home/mashevit/<venv>/bin/activate
# ------------------------------------------------------------------------
module load anaconda
source activate gsm8k_lora
set -euo pipefail

KIT="$HOME/gsm8k_lora_v2"
GGUF="$HOME/gguf_models/qwen3_8b_merged-Q8_0.gguf"

cd "$KIT"

python -c "import numpy, transformers; print('env OK')"

test -f "$GGUF" || { echo "MISSING GGUF: $GGUF"; exit 1; }

python gen_modelfile.py \
    --gguf "$GGUF" \
    --out  "$KIT/Modelfile"

echo
echo "=============== Modelfile ==============="
cat "$KIT/Modelfile"
echo "========================================="
echo
echo "Confirm above:"
echo "  FROM      -> qwen3_8b_merged-Q8_0.gguf   (NOT merged_16bit-Q6_K.gguf)"
echo "  stop      -> Qwen3 tokens (<|im_end|>)   (NOT Llama <|eot_id|>)"
echo "  temperature 0 / greedy params match utils.GREEDY"
