#!/usr/bin/env python
"""compare_base_vs_lora.py -- serving-fidelity check.

Side A: merged fp16 dir via plain transformers  (the common ancestor)
Side B: the same weights, GGUF-converted, quantized to Q8_0, served by Ollama

Both sides descend from ONE fp16 ancestor, so the only residual is serving
quantization. The old 1/10 result compared NF4+bf16-adapter against Q6_K -- two
independent lossy transforms -- and was uninterpretable.

TWO PHASES, deliberately. rtx_6000 is 24GB; Qwen3-8B fp16 (~16GB) and the Q8_0 GGUF
in Ollama (~9GB) do not co-reside. Phase A generates every HF completion and frees
the GPU; only then does phase B touch Ollama, which loads lazily on first request.

Side B uses raw=true and sends utils.build_prompt() output directly, bypassing the
Ollama TEMPLATE on purpose: a TEMPLATE bug would otherwise masquerade as quantization
loss. gen_modelfile.py still derives the TEMPLATE from the same build_prompt for
downstream OllamaProvider.

Does NOT touch the accuracy baseline (both-right 20 / LoRA-fixed 5 / LoRA-broke 1).
Expected: 9-10/10 agreement.
"""
import argparse
import gc
import json

import requests
import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer

import utils


def phase_a(merged_path, prompts, max_new_tokens):
    print(f"[A] loading merged fp16 from {merged_path}", flush=True)
    tok = AutoTokenizer.from_pretrained(merged_path)
    model = AutoModelForCausalLM.from_pretrained(
        merged_path, torch_dtype=torch.float16, device_map="auto",
    )
    model.eval()
    outs = []
    for i, p in enumerate(prompts):
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
        print(f"[A] {i} done", flush=True)

    del model, tok
    gc.collect()
    torch.cuda.empty_cache()
    print(f"[A] GPU freed ({torch.cuda.memory_allocated()/1e9:.2f} GB still allocated)", flush=True)
    return outs


def phase_b(url, model_tag, prompts, max_new_tokens, stops):
    print(f"[B] querying Ollama tag {model_tag} at {url}", flush=True)
    outs = []
    for i, p in enumerate(prompts):
        opts = {"temperature": 0, "num_predict": max_new_tokens}
        if stops:
            opts["stop"] = list(stops)
        r = requests.post(
            f"{url}/api/generate",
            json={"model": model_tag, "prompt": p, "raw": True, "stream": False, "options": opts},
            timeout=900,
        )
        r.raise_for_status()
        outs.append(r.json()["response"])
        print(f"[B] {i} done", flush=True)
    return outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--merged", required=True)
    ap.add_argument("--ollama-url", required=True)
    ap.add_argument("--ollama-model", required=True)
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--max_new_tokens", type=int, default=256)
    ap.add_argument("--out", default="compare_results.json")
    args = ap.parse_args()

    greedy = dict(getattr(utils, "GREEDY", {}))
    stops = greedy.get("stop") or greedy.get("stop_sequences") or []

    ds = load_dataset("gsm8k", "main", split="test").select(range(args.n))
    prompts = [utils.build_prompt(q) for q in ds["question"]]

    a_outs = phase_a(args.merged, prompts, args.max_new_tokens)
    b_outs = phase_b(args.ollama_url, args.ollama_model, prompts, args.max_new_tokens, stops)

    rows, agree = [], 0
    for i, (a, b) in enumerate(zip(a_outs, b_outs)):
        ans_a = utils.extract_answer_from_generation(a)
        ans_b = utils.extract_answer_from_generation(b)
        same = ans_a == ans_b
        agree += same
        rows.append({"i": i, "agree": same, "fp16": a, "ollama": b,
                     "ans_fp16": ans_a, "ans_ollama": ans_b})
        print(f"[{i}] agree={same}  fp16={ans_a!r}  ollama={ans_b!r}")

    print(f"\nagreement {agree}/{len(prompts)}")
    with open(args.out, "w") as f:
        json.dump({"agreement": agree, "n": len(prompts), "rows": rows}, f, indent=2)
    print(f"wrote {args.out}")

    if agree < len(prompts) - 1:
        print("[warn] below the 9-10/10 target. Q8_0 is near-lossless, so a low score here "
              "points at prompt/stop mismatch or a bad merge -- not quantization.")


if __name__ == "__main__":
    main()
