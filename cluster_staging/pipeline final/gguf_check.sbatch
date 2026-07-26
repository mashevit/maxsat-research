#!/bin/bash
#SBATCH --job-name=gguf-check
#SBATCH --partition main
#SBATCH --time=00:10:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
# NOTE: #SBATCH lines are parsed before any shell expansion — $HOME does NOT
# work here. These two must stay literal.
#SBATCH --output=logs/gguf-check-job-%j.out
#SBATCH --error=logs/gguf-check-job-%j.out

# ---- ENV (fill from train.sbatch) --------------------------------------
# module load ...
# source /home/mashevit/<venv>/bin/activate
# ------------------------------------------------------------------------



module load anaconda
source activate gsm8k_lora


set -euo pipefail


KIT="$HOME/gsm8k_lora_v2"
GGUF="$HOME/gguf_models/qwen3_8b_merged-f16.gguf"
MERGED="$KIT/merged_16bit"   # <-- confirm this path

cd "$KIT"

python - "$GGUF" "$MERGED" <<'PYEOF'
import json, sys, os

gguf_path, merged_dir = sys.argv[1], sys.argv[2]

# ---- reference: what the merged fp16 dir says --------------------------
with open(os.path.join(merged_dir, "config.json")) as f:
    cfg = json.load(f)
ref_vocab = cfg["vocab_size"]
ref_tie   = cfg.get("tie_word_embeddings")
ref_layers = cfg.get("num_hidden_layers")

# ---- actual: what landed in the GGUF -----------------------------------
from gguf import GGUFReader
r = GGUFReader(gguf_path)

def field(name):
    f = r.fields.get(name)
    if f is None:
        return None
    if not f.data:
        return None
    return f.parts[f.data[0]]

tokens = r.fields.get("tokenizer.ggml.tokens")
n_tokens = len(tokens.data) if tokens is not None else None

got_layers = field("qwen3.block_count")
got_layers = int(got_layers[0]) if got_layers is not None else None

# tensor dtype census
dtypes = {}
for t in r.tensors:
    dtypes[str(t.tensor_type)] = dtypes.get(str(t.tensor_type), 0) + 1

print("=" * 62)
print(f"GGUF   : {gguf_path}")
print(f"size   : {os.path.getsize(gguf_path) / 1e9:.2f} GB")
print(f"tensors: {len(r.tensors)}")
print(f"dtypes : {dtypes}")
print("-" * 62)
print(f"vocab   ref={ref_vocab}   gguf={n_tokens}")
print(f"layers  ref={ref_layers}  gguf={got_layers}")
print(f"tie_word_embeddings (ref config) = {ref_tie}")
print("-" * 62)

fail = []
if n_tokens != ref_vocab:
    fail.append(f"VOCAB MISMATCH: {n_tokens} != {ref_vocab} -> wrong/stale tokenizer picked up")
if got_layers is not None and got_layers != ref_layers:
    fail.append(f"LAYER MISMATCH: {got_layers} != {ref_layers}")
if not any("F16" in k for k in dtypes):
    fail.append(f"NO F16 TENSORS -> wrong --outtype, breaks common-fp16-ancestor invariant")

if fail:
    print("FAIL")
    for x in fail:
        print("  - " + x)
    sys.exit(1)

print("PASS: GGUF is a faithful re-serialization of the merged fp16 dir.")
print("Next: sbatch quant.sbatch")
print("=" * 62)
PYEOF
