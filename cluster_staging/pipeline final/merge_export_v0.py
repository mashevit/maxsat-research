#!/usr/bin/env python
"""merge_export.py ── LoRA adapter -> merged fp16 dir, with a merge-fidelity gate.

The gate exists to catch gross merge corruption INDEPENDENTLY of GGUF quantization:
we capture greedy outputs from the adapter-on-base model in memory, merge, reload the
merged fp16 from disk, and diff. If they disagree, the merge is broken and every
downstream number is uninterpretable -- so we exit nonzero and stop the chain.

Merge is done onto the FULL-PRECISION base (never the 4-bit repo): the merged fp16
dir is the common ancestor for both sides of the serving comparison, so the only
residual downstream is serving quantization.

Qwen3-8B has tie_word_embeddings=false -> structurally immune to the Llama-3.2-style
tied-embedding merge corruption. The gate stays anyway; it is cheap.
"""
import argparse
import gc
import sys

import torch
from datasets import load_dataset
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

import utils


def greedy_gen(model, tok, prompts, max_new_tokens):
    outs = []
    for p in prompts:
        enc = tok(p, return_tensors="pt").to(model.device)
        with torch.no_grad():
            ids = model.generate(
                **enc,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                top_k=None,
                pad_token_id=tok.pad_token_id or tok.eos_token_id,
            )
        outs.append(tok.decode(ids[0][enc["input_ids"].shape[1]:], skip_special_tokens=True))
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True, help="full-precision base repo id")
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--merged", required=True)
    ap.add_argument("--n", type=int, default=5, help="fidelity-gate items")
    ap.add_argument("--max_new_tokens", type=int, default=256)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(args.adapter)

    # Gate prompts come through utils.build_prompt so the gate exercises the same
    # prompt contract as everything else. TEST split only.
    ds = load_dataset("gsm8k", "main", split="test").select(range(args.n))
    prompts = [utils.build_prompt(q) for q in ds["question"]]

    # ── side 1: adapter on fp16 base, in memory ────────────────────────────
    print(f"[gate] loading base {args.base} (fp16) + adapter", flush=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.base, torch_dtype=torch.float16, device_map="auto",
    )
    model = PeftModel.from_pretrained(model, args.adapter)
    model.eval()
    before = greedy_gen(model, tok, prompts, args.max_new_tokens)

    # ── merge and write ───────────────────────────────────────────────────
    print(f"[merge] merge_and_unload -> {args.merged}", flush=True)
    model = model.merge_and_unload()
    model.save_pretrained(args.merged, safe_serialization=True)
    tok.save_pretrained(args.merged)

    del model
    gc.collect()
    torch.cuda.empty_cache()

    # ── side 2: reload merged fp16 from disk ──────────────────────────────
    print(f"[gate] reloading merged fp16 from {args.merged}", flush=True)
    merged = AutoModelForCausalLM.from_pretrained(
        args.merged, torch_dtype=torch.float16, device_map="auto",
    )
    merged.eval()
    after = greedy_gen(merged, tok, prompts, args.max_new_tokens)

    # ── gate ──────────────────────────────────────────────────────────────
    ok = sum(a == b for a, b in zip(before, after))
    print(f"\n[gate] exact-match {ok}/{len(prompts)}")
    for i, (a, b) in enumerate(zip(before, after)):
        if a != b:
            print(f"\n--- item {i} MISMATCH ---\n  in-memory: {a[:300]!r}\n  merged   : {b[:300]!r}")

    if ok < len(prompts):
        print("\n[gate] FAIL — merge corrupted. Do not proceed to gguf/quant/serve.")
        sys.exit(1)
    print("[gate] PASS")


if __name__ == "__main__":
    main()
