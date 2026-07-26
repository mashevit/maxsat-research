# env.sh ── sourced by every stage sbatch. Single source of truth for paths.
# Sourced via an absolute path (SLURM copies the job script elsewhere, so $0 is useless).

module load anaconda
source activate gsm8k_lora

export KIT="$HOME/gsm8k_lora_v2"
export BASE="Qwen/Qwen3-8B"                 # FULL-PRECISION base. Never the -bnb-4bit repo.
export ADAPTER="$KIT/qwen3_8b_lora_model"   # train.py --output_dir
export MERGED="$KIT/merged_16bit"           # fp16 common ancestor

export LLAMA_CPP="$HOME/llama.cpp"
export LLAMA_QUANTIZE="$LLAMA_CPP/build/bin/llama-quantize"   # build artifact, not repo root

export GGUF_DIR="$HOME/gguf_models"
export GGUF_F16="$GGUF_DIR/qwen3_8b_merged-f16.gguf"
export GGUF_Q8="$GGUF_DIR/qwen3_8b_merged-Q8_0.gguf"          # fresh name: does NOT clobber
                                                              # the v1 merged_16bit-Q6_K.gguf
export OLLAMA_SIF="$HOME/apptainer-ollama/ollama.sif"
export OLLAMA_TAG="gsm8k-qwen3-8b"
# NOTE: no OLLAMA_URL here. The port is picked at runtime by serve_compare.sbatch.
