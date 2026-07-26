#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:30:00
#SBATCH --job-name gsm8k-quant
#SBATCH --output quant-job-%J.out
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8

set -euo pipefail
source "$HOME/gsm8k_lora_v2/env.sh"

# llama-quantize is a BUILD ARTIFACT, not at the repo root.
if [[ ! -x "$LLAMA_QUANTIZE" ]]; then
    echo "ERROR: $LLAMA_QUANTIZE missing/not executable." >&2
    echo "Build:  cmake -B $LLAMA_CPP/build -S $LLAMA_CPP && cmake --build $LLAMA_CPP/build -j --target llama-quantize" >&2
    exit 1
fi

# Q8_0 is near-lossless: the ONLY residual left in the comparison.
# Q6_K / Q4_K_M ablation comes later, into separate output files.
"$LLAMA_QUANTIZE" "$GGUF_F16" "$GGUF_Q8" Q8_0
ls -lh "$GGUF_Q8"
