#!/bin/bash
#SBATCH --partition main
#SBATCH --time 0-00:40:00                        ### incl. one-time llama.cpp build
#SBATCH --job-name gsm8k-gguf
#SBATCH --output gguf-job-%J.out
#SBATCH --mem=32G
#SBATCH --cpus-per-task=8

# Step 2: convert ./merged_16bit -> GGUF, then quantize to Q6_K.
# CPU-only (no --gpus line). First run also builds llama.cpp (~5-10 min).
# For Qwen3-8B later: bump --mem to 48G and --time to 0-01:20:00.
#
# Runs in a DEDICATED 'gguf' env (current transformers + cpu torch + compilers),
# NOT the Unsloth 'gsm8k_lora' env -- the two have conflicting torch/transformers
# pins, so keeping them separate is what stops this whole class of breakage.

set -euo pipefail
echo "Job $SLURM_JOB_ID on $(hostname) starting $(date)"

module load anaconda
source activate gguf

MERGED=${1:-./merged_16bit}
QUANT=${2:-Q6_K}                       # Q6_K for reasoning; Q8_0 for max fidelity
OUTDIR=${3:-$HOME/gguf_models}
LLAMA_CPP=${LLAMA_CPP:-$HOME/llama.cpp}
mkdir -p "$OUTDIR"

# --- build llama.cpp once ---
if [ ! -x "$LLAMA_CPP/build/bin/llama-quantize" ]; then
  echo "Building llama.cpp at $LLAMA_CPP ..."
  [ -d "$LLAMA_CPP" ] || git clone https://github.com/ggml-org/llama.cpp "$LLAMA_CPP"

  export CC="$(command -v x86_64-conda-linux-gnu-gcc || command -v gcc)"
  export CXX="$(command -v x86_64-conda-linux-gnu-g++ || command -v g++)"
  echo "Using CXX=$CXX"

  rm -rf "$LLAMA_CPP/build"            # clear any stale cache from a failed configure
  cmake -S "$LLAMA_CPP" -B "$LLAMA_CPP/build" -DGGML_NATIVE=ON \
    -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX"
  cmake --build "$LLAMA_CPP/build" --config Release -j "$SLURM_CPUS_PER_TASK" \
    --target llama-quantize
fi

# --- normalize tokenizer_class ---
# transformers v5 saves tokenizer_class="TokenizersBackend". We rewrite it to the
# concrete fast class so it loads from tokenizer.json regardless of loader version.
# Idempotent + model-agnostic (Llama-3, Qwen3). No-op if already normalized.
python - "$MERGED" <<'PY'
import json, sys, pathlib
cfg = pathlib.Path(sys.argv[1]) / "tokenizer_config.json"
if cfg.exists():
    d = json.loads(cfg.read_text())
    if d.get("tokenizer_class") in ("TokenizersBackend", "TokenizersBackendFast"):
        d["tokenizer_class"] = "PreTrainedTokenizerFast"
        cfg.write_text(json.dumps(d, indent=2))
        print("normalized tokenizer_class -> PreTrainedTokenizerFast")
    else:
        print(f"tokenizer_class = {d.get('tokenizer_class')} (no change)")
PY

NAME=$(basename "$MERGED")
F16="$OUTDIR/${NAME}-f16.gguf"
FINAL="$OUTDIR/${NAME}-${QUANT}.gguf"

echo "Converting HF -> GGUF (f16) ..."
python "$LLAMA_CPP/convert_hf_to_gguf.py" "$MERGED" --outfile "$F16" --outtype f16

echo "Quantizing f16 -> $QUANT ..."
"$LLAMA_CPP/build/bin/llama-quantize" "$F16" "$FINAL" "$QUANT"

echo "Removing f16 intermediate to save quota ..."
rm -f "$F16"

ls -lh "$FINAL"
echo "GGUF done $(date). Point your Modelfile FROM at: $FINAL"
