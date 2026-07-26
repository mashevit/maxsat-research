#!/bin/bash
# Login-node check of the CURRENT merged dir. No GPU, no allocation needed.
# Run this first, before resubmitting the merge — it costs nothing and tells you
# whether the existing export path is even producing fp16.

MERGED="${1:-/home/mashevit/gsm8k_lora_v2/merged_16bit}"

if [ ! -f "${MERGED}/config.json" ]; then
  echo "no config.json at ${MERGED}"
  exit 1
fi

python -c "import json; c=json.load(open('${MERGED}/config.json')); print('dtype =', c.get('dtype') or c.get('torch_dtype'))"

echo "--- adapter/base sanity ---"
python -c "import json; c=json.load(open('${MERGED}/config.json')); print('tie_word_embeddings =', c.get('tie_word_embeddings')); print('vocab_size =', c.get('vocab_size')); print('num_hidden_layers =', c.get('num_hidden_layers'))"

echo "--- safetensors header dtypes (ground truth, not the config claim) ---"
python - "${MERGED}" <<'EOF'
import json, struct, sys, glob, os, collections
d = sys.argv[1]
counts = collections.Counter()
for f in sorted(glob.glob(os.path.join(d, "*.safetensors"))):
    with open(f, "rb") as fh:
        n = struct.unpack("<Q", fh.read(8))[0]
        hdr = json.loads(fh.read(n))
    for k, v in hdr.items():
        if k == "__metadata__":
            continue
        counts[v["dtype"]] += 1
print(dict(counts))
EOF
