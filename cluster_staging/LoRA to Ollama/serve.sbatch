#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:45:00
#SBATCH --job-name gsm8k-serve
#SBATCH --output serve-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=32G
#SBATCH --cpus-per-task=4

# Step 3: start Ollama (Apptainer) on this node, register the merged GGUF from a
# Modelfile, then run compare_base_vs_lora.py which loads the ORIGINAL model
# (base + adapter via Unsloth) and the Ollama-served merged model and diffs them.
#
# Everything runs inside this one job. Apptainer shares the host network namespace
# (no --net), so the in-container server on 127.0.0.1:$PORT is reachable from the
# host-side compare script at the same address. A free port in 9980-9999 is chosen
# to avoid colliding with another job's Ollama on a shared node.

set -euo pipefail
echo "Job $SLURM_JOB_ID on $(hostname) starting $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

module load anaconda
source activate gsm8k_lora

SIF=${SIF:-$HOME/apptainer-ollama/ollama.sif}
MODELFILE=${MODELFILE:-./Modelfile}
MODEL_TAG=${MODEL_TAG:-gsm8k-llama32-3b}

# Pick a free port in 9980-9999 (shared-node safe), mirroring apptainer-ollama.sh.
PORT=$(comm -23 \
  <(seq 9980 9999 | sort) \
  <(ss -Htan 2>/dev/null | awk '{print $4}' | awk -F: '{print $NF}' | sort -u) \
  | shuf | head -n1)
PORT=${PORT:-11434}
export OLLAMA_HOST=127.0.0.1:$PORT          # loopback; host shares container netns
export OLLAMA_CONTEXT_LENGTH=32768          # match across Modelfile / requests
export OLLAMA_FLASH_ATTENTION=1
# Model store persists via the --bind below (Ollama defaults to /root/.ollama).
echo "Ollama will listen on $OLLAMA_HOST"

# --- start the server in the background, bind the persistent model store ---
echo "Starting Ollama from $SIF ..."
apptainer exec --nv --writable-tmpfs \
  --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" \
  --env OLLAMA_CONTEXT_LENGTH="$OLLAMA_CONTEXT_LENGTH" \
  --env OLLAMA_FLASH_ATTENTION="$OLLAMA_FLASH_ATTENTION" \
  "$SIF" ollama serve &
OLLAMA_PID=$!
trap 'kill $OLLAMA_PID 2>/dev/null || true' EXIT

# --- health poll ---
echo -n "Waiting for Ollama"
for _ in $(seq 1 60); do
  if curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null 2>&1; then
    echo " ... up."; break
  fi
  echo -n "."; sleep 2
done
curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null || { echo "Ollama never came up"; exit 1; }

# --- register the merged model from the Modelfile ---
echo "Creating model tag '$MODEL_TAG' from $MODELFILE ..."
apptainer exec --nv --writable-tmpfs --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" "$SIF" \
  ollama create "$MODEL_TAG" -f "$MODELFILE"

apptainer exec --writable-tmpfs --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" "$SIF" ollama show --modelfile "$MODEL_TAG" | head -40 || true

# --- run the comparison (loads original via Unsloth, queries Ollama) ---
echo "Running base-vs-LoRA comparison ..."
python compare_base_vs_lora.py \
  --ollama-url "http://$OLLAMA_HOST" \
  --ollama-model "$MODEL_TAG" \
  --adapter ./gsm8k_lora_model \
  --n 10

echo "Compare finished $(date)."
