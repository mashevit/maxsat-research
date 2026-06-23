#!/usr/bin/env python3
"""
merge_export.py
===============
Step 1 of the serving pipeline: merge the LoRA adapter into the base model and
write a standalone 16-bit Hugging Face directory.

We deliberately do NOT produce GGUF here. Merge stays inside Unsloth via
`save_pretrained_merged(save_method="merged_16bit")`, which faithfully
dequantizes the 4-bit base and applies the bf16 LoRA delta once. GGUF
conversion is a separate step (gguf.sbatch -> llama.cpp), because Unsloth's
one-shot GGUF export is fragile on newer architectures.

CRITICAL: the tokenizer (and its chat_template) MUST be written into the merged
directory. Everything downstream — the Ollama Modelfile TEMPLATE and the
base-vs-LoRA comparison — depends on the served prompt format matching what
`utils.py` produced during training, character-for-character. This script
verifies the tokenizer was saved and warns if no chat_template is present.

Usage:
  python merge_export.py                         # uses defaults below
  python merge_export.py --adapter ./gsm8k_lora_model --out ./merged_16bit
  python merge_export.py --base unsloth/llama-3.2-3b-bnb-4bit   # override base
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def read_base_from_adapter(adapter_dir: Path) -> str | None:
    cfg = adapter_dir / "adapter_config.json"
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text())
    except json.JSONDecodeError:
        return None
    return data.get("base_model_name_or_path")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", type=Path, default=Path("./gsm8k_lora_model"),
                    help="LoRA adapter directory (adapter_config.json + .safetensors)")
    ap.add_argument("--base", default=None,
                    help="override base model; default = read from adapter_config.json")
    ap.add_argument("--out", type=Path, default=Path("./merged_16bit"),
                    help="output directory for the merged 16-bit HF model")
    ap.add_argument("--max-seq-len", type=int, default=2048,
                    help="must be >= the value used in training")
    args = ap.parse_args()

    adapter = args.adapter.resolve()
    if not (adapter / "adapter_config.json").exists():
        sys.exit(f"No adapter_config.json under {adapter} — is --adapter correct?")

    base_from_cfg = read_base_from_adapter(adapter)
    base = args.base or base_from_cfg
    print(f"Adapter dir : {adapter}")
    print(f"Base model  : {base}  "
          f"({'from --base' if args.base else 'from adapter_config.json'})")
    print(f"Output dir  : {args.out.resolve()}")
    print(f"max_seq_len : {args.max_seq_len}")

    # Import Unsloth lazily so --help works without the heavy stack loaded.
    from unsloth import FastLanguageModel  # noqa: E402

    # Loading the adapter directory makes Unsloth resolve the base from
    # adapter_config.json and attach the LoRA weights in one call.
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(adapter),
        max_seq_length=args.max_seq_len,
        dtype=None,           # let Unsloth pick (bf16 on Ada)
        load_in_4bit=True,    # base loaded 4-bit; merge_16bit dequantizes it
    )

    args.out.mkdir(parents=True, exist_ok=True)
    print("Merging adapter into base and saving as merged_16bit ...")
    model.save_pretrained_merged(str(args.out), tokenizer, save_method="merged_16bit")

    # ---- verification ----
    out = args.out
    must_exist = ["config.json", "tokenizer_config.json"]
    missing = [f for f in must_exist if not (out / f).exists()]
    weights = list(out.glob("*.safetensors")) + list(out.glob("*.bin"))
    if missing:
        sys.exit(f"ERROR: merged dir missing {missing} — export incomplete.")
    if not weights:
        sys.exit("ERROR: no weight shards (*.safetensors/*.bin) in merged dir.")

    # chat_template lives either in tokenizer_config.json or chat_template.jinja
    tok_cfg = json.loads((out / "tokenizer_config.json").read_text())
    has_template = bool(tok_cfg.get("chat_template")) or (out / "chat_template.jinja").exists()
    print("\nVerification:")
    print(f"  weight shards     : {len(weights)}")
    print(f"  tokenizer saved   : yes")
    print(f"  chat_template     : {'present' if has_template else 'MISSING (check utils.py!)'}")
    total_gb = sum(p.stat().st_size for p in out.rglob('*')) / 1e9
    print(f"  total size        : {total_gb:.2f} GB")
    if not has_template:
        print("  WARNING: no chat_template found. If you trained with a plain "
              "prompt format (INSTRUCTION + Problem: + RESPONSE_TEMPLATE) rather "
              "than a chat template, that is fine — but the Ollama Modelfile "
              "TEMPLATE must then reproduce that exact format from utils.py.")
    print(f"\nMerge done. Next: run gguf.sbatch on {out}")


if __name__ == "__main__":
    main()
