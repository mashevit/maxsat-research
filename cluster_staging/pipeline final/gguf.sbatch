#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:45:00
#SBATCH --job-name gsm8k-gguf
#SBATCH --output gguf-job-%J.out
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
# No GPU: conversion is pure CPU/IO.

set -euo pipefail
source "$HOME/gsm8k_lora_v2/env.sh"
cd "$KIT"

mkdir -p "$GGUF_DIR"

# convert_hf_to_gguf.py lives at the llama.cpp repo ROOT. Format change only.
python "$LLAMA_CPP/convert_hf_to_gguf.py" "$MERGED" \
    --outfile "$GGUF_F16" \
    --outtype f16

ls -lh "$GGUF_F16"
