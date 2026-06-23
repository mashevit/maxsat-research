#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:30:00                        ### portable rebuild + quantize
#SBATCH --job-name gsm8k-quant
#SBATCH --output quant-job-%J.out
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8

# Recovery / fast path: the f16 GGUF already exists, so SKIP the HF->GGUF convert
# and just (re)build a PORTABLE llama-quantize, then quantize the existing f16.
# Use this instead of the full gguf.sbatch when ~/gguf_models/*-f16.gguf is present.

set -euo pipefail
echo "Job $SLURM_JOB_ID on $(hostname) starting $(date)"

module load anaconda
source activate gguf

F16=${1:-$HOME/gguf_models/merged_16bit-f16.gguf}
QUANT=${2:-Q6_K}
FINAL=${3:-${F16%-f16.gguf}-${QUANT}.gguf}
LLAMA_CPP=${LLAMA_CPP:-$HOME/llama.cpp}

if [ ! -f "$F16" ]; then
  echo "ERROR: f16 not found at $F16 (run the full gguf.sbatch first)" >&2
  exit 1
fi

# --- always rebuild PORTABLE (the previous binary was -march=native and SIGILLs
# on older nodes). Comment out the rm + build block on later runs once the binary
# is known-portable, to skip straight to quantize. ---
export CC="$(command -v x86_64-conda-linux-gnu-gcc || command -v gcc)"
export CXX="$(command -v x86_64-conda-linux-gnu-g++ || command -v g++)"
echo "Using CXX=$CXX"

rm -rf "$LLAMA_CPP/build"
cmake -S "$LLAMA_CPP" -B "$LLAMA_CPP/build" -DGGML_NATIVE=OFF \
  -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX"
cmake --build "$LLAMA_CPP/build" --config Release -j "$SLURM_CPUS_PER_TASK" \
  --target llama-quantize

echo "Quantizing $(basename "$F16") -> $QUANT ..."
"$LLAMA_CPP/build/bin/llama-quantize" "$F16" "$FINAL" "$QUANT"

echo "Removing f16 intermediate to save quota ..."
rm -f "$F16"

ls -lh "$FINAL"
echo "Quantize done $(date). Point your Modelfile FROM at: $FINAL"
