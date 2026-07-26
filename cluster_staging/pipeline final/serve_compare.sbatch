#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-01:00:00
#SBATCH --job-name gsm8k-serve-compare
#SBATCH --output serve-compare-job-%J.out
#SBATCH --gpus=rtx_6000:1
#SBATCH --mem=64G
#SBATCH --cpus-per-task=4

# Serve + compare in ONE job: the Ollama daemon starts here and dies with the job,
# so a separate compare job would have nothing to talk to.
#
# Apptainer shares the host network namespace (no --net), so the in-container server
# on 127.0.0.1:$PORT is reachable from the host-side compare script. A free port in
# 9980-9999 avoids colliding with another job's Ollama on a shared node.
#
# VRAM: rtx_6000 is 24GB. Qwen3-8B fp16 (~16GB) + Q8_0 in Ollama (~9GB) does NOT fit
# concurrently. compare_base_vs_lora.py therefore runs phase A (HF fp16), frees the
# GPU, then runs phase B (Ollama). Do not interleave them.

set -euo pipefail
echo "Job $SLURM_JOB_ID on $(hostname) starting $(date)"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true

source "$HOME/gsm8k_lora_v2/env.sh"
cd "$KIT"

# ── pick a free port (shared-node safe) ────────────────────────────────────
PORT=$(comm -23 \
  <(seq 9980 9999 | sort) \
  <(ss -Htan 2>/dev/null | awk '{print $4}' | awk -F: '{print $NF}' | sort -u) \
  | shuf | head -n1)
PORT=${PORT:-11434}
export OLLAMA_HOST=127.0.0.1:$PORT
export OLLAMA_CONTEXT_LENGTH=32768
export OLLAMA_FLASH_ATTENTION=1
echo "Ollama will listen on $OLLAMA_HOST"

# ── 1) Modelfile derived from utils.build_prompt (never hand-written) ──────
python gen_modelfile.py --gguf "$GGUF_Q8" --out Modelfile

# ── 2) start the server, bind the persistent model store ──────────────────
echo "Starting Ollama from $OLLAMA_SIF ..."
apptainer exec --nv --writable-tmpfs \
  --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" \
  --env OLLAMA_CONTEXT_LENGTH="$OLLAMA_CONTEXT_LENGTH" \
  --env OLLAMA_FLASH_ATTENTION="$OLLAMA_FLASH_ATTENTION" \
  "$OLLAMA_SIF" ollama serve &
OLLAMA_PID=$!
trap 'kill $OLLAMA_PID 2>/dev/null || true' EXIT

echo -n "Waiting for Ollama"
for _ in $(seq 1 60); do
  if curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null 2>&1; then echo " ... up."; break; fi
  echo -n "."; sleep 2
done
curl -sf "http://$OLLAMA_HOST/api/version" >/dev/null || { echo "Ollama never came up"; exit 1; }

# ── 3) register the Q8_0 tag ──────────────────────────────────────────────
echo "Creating model tag '$OLLAMA_TAG' from Modelfile ..."
apptainer exec --nv --writable-tmpfs --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" "$OLLAMA_SIF" \
  ollama create "$OLLAMA_TAG" -f Modelfile
apptainer exec --writable-tmpfs --bind "$HOME/.ollama:/root/.ollama" \
  --env OLLAMA_HOST="$OLLAMA_HOST" "$OLLAMA_SIF" \
  ollama show --modelfile "$OLLAMA_TAG" | head -40 || true

# ── 4) compare: merged fp16 reference vs Q8_0 served ──────────────────────
# Reference is $MERGED, NOT base+adapter: both sides must descend from one fp16
# ancestor or the disagreement is uninterpretable (the old 1/10 result).
echo "Running serving-fidelity comparison ..."
python compare_base_vs_lora.py \
  --merged "$MERGED" \
  --ollama-url "http://$OLLAMA_HOST" \
  --ollama-model "$OLLAMA_TAG" \
  --n 10

echo "Finished $(date)."
