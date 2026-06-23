#!/usr/bin/env python3
"""
compare_base_vs_lora.py
=======================
Step 3 (verification): run the same GSM8K test examples through

  (A) the ORIGINAL fine-tuned model  — base `unsloth/llama-3.2-3b-bnb-4bit`
      (4-bit) + the `./gsm8k_lora_model` adapter, loaded via Unsloth, greedy
      generation. This is the QLoRA-inference reference, matching evaluate.py.

  (B) the OLLAMA-served merged model — the merged_16bit -> Q6_K GGUF registered
      from the Modelfile, queried over HTTP.

Both prompts are built identically: (A) is fed the full `utils.build_prompt`
string directly; (B) is sent ONLY the raw question text, because the Ollama
Modelfile TEMPLATE reconstructs build_prompt() around {{ .Prompt }}. If the
template is faithful, the two rendered prompts are byte-identical, so any large
divergence in outputs points at the merge or the template — not Q6_K quant.

Since the adapter was a ~13-step `--quick` run (near-identity), expect the two
to agree closely and to track plain Llama-3.2-3B behaviour.

Usage (typically invoked by serve.sbatch):
  python compare_base_vs_lora.py \
      --ollama-url http://127.0.0.1:11434 \
      --ollama-model gsm8k-llama32-3b \
      --adapter ./gsm8k_lora_model --n 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

from utils import (
    build_prompt,
    extract_answer_from_gold,
    extract_answer_from_generation,
    answers_match,
    set_seed,
)


def read_base_from_adapter(adapter_dir: Path) -> str | None:
    cfg = adapter_dir / "adapter_config.json"
    if not cfg.exists():
        return None
    return json.loads(cfg.read_text()).get("base_model_name_or_path")


# --------------------------------------------------------------------------- #
# (A) original model via Unsloth                                              #
# --------------------------------------------------------------------------- #
def load_original(adapter: Path, max_seq_len: int):
    from unsloth import FastLanguageModel
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(adapter),       # resolves base + attaches adapter
        max_seq_length=max_seq_len,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)        # ~2x faster decode
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    return model, tokenizer


def gen_original(model, tokenizer, question: str, max_new_tokens: int) -> str:
    import torch
    prompt = build_prompt(question)               # full training-format prompt
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,                      # greedy == temperature 0
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )
    new_tokens = out[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(new_tokens, skip_special_tokens=True)


# --------------------------------------------------------------------------- #
# (B) Ollama-served merged model                                              #
# --------------------------------------------------------------------------- #
def gen_ollama(url: str, model_tag: str, question: str, max_new_tokens: int) -> str:
    # Send ONLY the raw question; the Modelfile TEMPLATE wraps it. raw is left
    # false (default) so templating is applied.
    resp = requests.post(
        f"{url}/api/generate",
        json={
            "model": model_tag,
            "prompt": question,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": max_new_tokens,
                "num_ctx": 32768,
            },
        },
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


# --------------------------------------------------------------------------- #
# main                                                                        #
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    ap.add_argument("--ollama-model", default="gsm8k-llama32-3b")
    ap.add_argument("--adapter", type=Path, default=Path("./gsm8k_lora_model"))
    ap.add_argument("--n", type=int, default=10, help="number of test examples")
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--max-seq-len", type=int, default=2048)
    args = ap.parse_args()

    set_seed(42)

    base = read_base_from_adapter(args.adapter)
    print(f"Adapter : {args.adapter}")
    print(f"Base    : {base}")
    print(f"Ollama  : {args.ollama_model} @ {args.ollama_url}")
    print(f"Examples: {args.n}\n")

    # --- data ---
    from datasets import load_dataset
    ds = load_dataset("gsm8k", "main", split="test")
    examples = ds.select(range(min(args.n, len(ds))))

    # Sanity: show the exact prompt the original sees vs the raw question Ollama
    # gets, so the user can eyeball that the Modelfile reconstructs the former.
    q0 = examples[0]["question"]
    print("=" * 70)
    print("PROMPT SENT TO ORIGINAL MODEL (full build_prompt):")
    print(repr(build_prompt(q0)))
    print("\nPROMPT SENT TO OLLAMA (raw question; template rebuilds the above):")
    print(repr(q0))
    print("=" * 70 + "\n")

    # --- check Ollama is reachable before loading the heavy model ---
    try:
        requests.get(f"{args.ollama_url}/api/version", timeout=10).raise_for_status()
    except Exception as e:
        sys.exit(f"Ollama not reachable at {args.ollama_url}: {e}")

    model, tokenizer = load_original(args.adapter, args.max_seq_len)

    rows = []
    orig_correct = oll_correct = agree = 0
    for i, ex in enumerate(examples):
        q, gold_text = ex["question"], ex["answer"]
        gold = extract_answer_from_gold(gold_text)

        orig_out = gen_original(model, tokenizer, q, args.max_new_tokens)
        oll_out = gen_ollama(args.ollama_url, args.ollama_model, q, args.max_new_tokens)

        orig_pred = extract_answer_from_generation(orig_out)
        oll_pred = extract_answer_from_generation(oll_out)

        o_ok = answers_match(orig_pred, gold)
        l_ok = answers_match(oll_pred, gold)
        same = answers_match(orig_pred, oll_pred)
        orig_correct += o_ok
        oll_correct += l_ok
        agree += same

        rows.append((i, gold, orig_pred, oll_pred, o_ok, l_ok, same))
        print(f"[{i:2d}] gold={str(gold):>8} | orig={str(orig_pred):>8} "
              f"{'✓' if o_ok else '✗'} | ollama={str(oll_pred):>8} "
              f"{'✓' if l_ok else '✗'} | agree={'yes' if same else 'NO'}")

    n = len(rows)
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  original accuracy   : {orig_correct}/{n}  ({100*orig_correct/n:.1f}%)")
    print(f"  ollama   accuracy   : {oll_correct}/{n}  ({100*oll_correct/n:.1f}%)")
    print(f"  orig<->ollama agree : {agree}/{n}  ({100*agree/n:.1f}%)")
    print("-" * 70)
    if agree == n:
        print("  PASS: outputs identical — merge + GGUF + template all faithful.")
    elif agree >= 0.8 * n:
        print("  OK: minor divergence consistent with Q6_K quant rounding.")
    else:
        print("  INVESTIGATE: large divergence. Suspect the merge or the Modelfile")
        print("  TEMPLATE (run `ollama show --modelfile` and diff vs build_prompt),")
        print("  NOT quantization. Re-check before scaling to Qwen3-8B.")
    print("=" * 70)


if __name__ == "__main__":
    main()
