"""
GSM8K LoRA Evaluation — Enhanced
==================================
Changes from v1:
  - Self-consistency mode: generate N samples, take majority vote
    (well-known boost for math reasoning, usually +5-15pp)
  - Shared prompt/extraction logic via utils.py
  - Per-example breakdown of base-vs-lora deltas
  - Seeded sampling for reproducibility
  - Proper test set usage (evaluate.py ONLY touches test split)

Modes:
  Greedy (default):           --num_samples 1
  Self-consistency (better):  --num_samples 8 --temperature 0.7

Usage:
    python evaluate.py --model_name mistralai/Mistral-7B-v0.3
    python evaluate.py --num_test 200 --num_samples 8 --temperature 0.7
    python evaluate.py --base_only --num_test 50
    python evaluate.py --quick                        # 30 examples, ~10 min
"""

import argparse
import json
from collections import Counter

import gc
import torch

# Unsloth must be imported BEFORE transformers so its patches take effect.
from unsloth import FastLanguageModel

from datasets import load_dataset
from tqdm import tqdm

from utils import (
    build_prompt,
    extract_answer_from_gold,
    extract_answer_from_generation,
    answers_match,
    set_seed,
    log_hardware,
)


def generate_one(model, tokenizer, prompt, device, max_new_tokens=256,
                 do_sample=False, temperature=1.0, top_p=1.0):
    """Generate a single completion."""
    inputs = tokenizer(prompt, return_tensors="pt",
                       truncation=True, max_length=512).to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            temperature=temperature if do_sample else 1.0,
            top_p=top_p if do_sample else 1.0,
            pad_token_id=tokenizer.eos_token_id,
        )
    gen_ids = outputs[0][inputs["input_ids"].shape[1]:]
    return tokenizer.decode(gen_ids, skip_special_tokens=True)


def predict_with_self_consistency(model, tokenizer, prompt, device,
                                   num_samples, temperature, max_new_tokens):
    """
    Generate N samples, extract the numerical answer from each,
    return the majority vote. Falls back to greedy if N=1.
    """
    if num_samples == 1:
        text = generate_one(model, tokenizer, prompt, device,
                            max_new_tokens=max_new_tokens, do_sample=False)
        return extract_answer_from_generation(text), text, [text]

    # Sampling mode
    samples = []
    extracted = []
    for _ in range(num_samples):
        text = generate_one(model, tokenizer, prompt, device,
                            max_new_tokens=max_new_tokens,
                            do_sample=True, temperature=temperature, top_p=0.95)
        samples.append(text)
        ans = extract_answer_from_generation(text)
        if ans is not None:
            extracted.append(ans)

    if not extracted:
        return None, samples[0], samples

    # Majority vote (by numeric value where possible)
    normalized = []
    for a in extracted:
        try:
            normalized.append(str(float(a)))
        except ValueError:
            normalized.append(a)

    counter = Counter(normalized)
    majority_value, _ = counter.most_common(1)[0]

    # Return one of the samples that produced the majority answer (for display)
    for text, ans in zip(samples, extracted):
        try:
            if str(float(ans)) == majority_value:
                return ans, text, samples
        except ValueError:
            if ans == majority_value:
                return ans, text, samples

    return extracted[0], samples[0], samples


def evaluate_model(model, tokenizer, test_data, device, desc,
                   num_samples=1, temperature=0.7, max_new_tokens=256):
    """Run evaluation. Returns metrics + per-example results."""
    correct = 0
    total = 0
    no_answer = 0
    examples = []

    for item in tqdm(test_data, desc=desc):
        question = item["question"]
        gold = extract_answer_from_gold(item["answer"])
        if gold is None:
            continue

        prompt = build_prompt(question)

        pred, display_text, _ = predict_with_self_consistency(
            model, tokenizer, prompt, device,
            num_samples=num_samples,
            temperature=temperature,
            max_new_tokens=max_new_tokens,
        )

        is_correct = answers_match(pred, gold)
        if pred is None:
            no_answer += 1
        if is_correct:
            correct += 1
        total += 1

        examples.append({
            "question": question[:120] + ("..." if len(question) > 120 else ""),
            "gold_answer": gold,
            "predicted_answer": pred,
            "correct": is_correct,
            "generated_text": display_text[:400],
        })

    accuracy = correct / total if total > 0 else 0.0
    metrics = {
        "accuracy": round(accuracy, 4),
        "correct": correct,
        "total": total,
        "no_answer_extracted": no_answer,
        "num_samples_per_question": num_samples,
    }
    return metrics, examples


def print_results(metrics, label):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Accuracy:             {metrics['accuracy']:.2%} "
          f"({metrics['correct']}/{metrics['total']})")
    print(f"  No answer extracted:  {metrics['no_answer_extracted']}")
    print(f"  Samples per question: {metrics['num_samples_per_question']}")
    print(f"{'='*60}")


def print_examples(examples, n=5, label=""):
    print(f"\n--- Sample predictions ({label}) ---")
    # Mix of correct and incorrect
    correct_ex = [e for e in examples if e["correct"]]
    wrong_ex = [e for e in examples if not e["correct"]]
    to_show = correct_ex[:n//2] + wrong_ex[:n - n//2]

    for ex in to_show:
        status = "✅" if ex["correct"] else "❌"
        print(f"\n{status} Q: {ex['question']}")
        print(f"   Gold: {ex['gold_answer']}  |  Pred: {ex['predicted_answer']}")
        print(f"   Out:  {ex['generated_text'][:200]}...")
    print("---\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str, default="mistralai/Mistral-7B-v0.3")
    parser.add_argument("--adapter_path", type=str, default="./gsm8k_lora_model")
    parser.add_argument("--num_test", type=int, default=200)
    parser.add_argument("--base_only", action="store_true")
    parser.add_argument("--num_samples", type=int, default=1,
                        help="Samples per question. 1=greedy, 8=self-consistency")
    parser.add_argument("--temperature", type=float, default=0.7,
                        help="Sampling temperature (only used if num_samples > 1)")
    parser.add_argument("--max_new_tokens", type=int, default=256)
    parser.add_argument("--show_examples", type=int, default=6)
    parser.add_argument("--output_file", type=str, default="eval_results.json")
    parser.add_argument("--hf_token", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quick", action="store_true",
                        help="30 examples, fewer shown — quick pipeline check, "
                             "mirrors train.py --quick")
    args = parser.parse_args()

    if args.quick:
        args.num_test = 30
        args.show_examples = 4

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"\n{'='*60}")
    print("GSM8K Evaluation")
    print(f"{'='*60}")
    print(f"  Model:        {args.model_name}")
    print(f"  Adapter:      {args.adapter_path if not args.base_only else '(skipped)'}")
    print(f"  Test size:    {args.num_test}")
    print(f"  Samples/q:    {args.num_samples}"
          f"{' (greedy)' if args.num_samples == 1 else ' (self-consistency)'}")
    if args.num_samples > 1:
        print(f"  Temperature:  {args.temperature}")
    log_hardware()
    print(f"{'='*60}\n")

    # ── Load TEST data (evaluate never touches train) ──────────────────────────
    print("Loading GSM8K test set...")
    dataset = load_dataset("openai/gsm8k", "main")
    test_data = dataset["test"].shuffle(seed=args.seed).select(range(args.num_test))
    print(f"Testing on {len(test_data)} examples\n")

    results = {}

    # ── Evaluate BASE model ────────────────────────────────────────────────────
    # Unsloth's FastLanguageModel handles 4-bit quantization, tokenizer, and
    # kernel patches in one call. for_inference() enables the 2x inference
    # fast-path. No separate BitsAndBytesConfig needed.
    print(f"Loading base model: {args.model_name}")
    base_model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=args.max_new_tokens + 512,  # prompt budget + generation
        dtype=None,
        load_in_4bit=True,
        token=args.hf_token,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    FastLanguageModel.for_inference(base_model)

    base_metrics, base_examples = evaluate_model(
        base_model, tokenizer, test_data, device, "Base",
        num_samples=args.num_samples,
        temperature=args.temperature,
        max_new_tokens=args.max_new_tokens,
    )
    print_results(base_metrics, "BASE MODEL (no LoRA)")
    print_examples(base_examples, n=args.show_examples, label="Base")
    results["base"] = base_metrics

    if not args.base_only:
        # Free the base model — Unsloth re-loads the base when we load the
        # adapter dir below. Holding both at once would roughly double VRAM.
        del base_model
        gc.collect()
        torch.cuda.empty_cache()

        # ── Evaluate LoRA model ────────────────────────────────────────────────
        # Unsloth reads the adapter config, pulls the matching base, and
        # merges them in one call. Cleaner than PeftModel.from_pretrained
        # and stays on the inference fast-path.
        print(f"\nLoading LoRA adapter: {args.adapter_path}")
        lora_model, _ = FastLanguageModel.from_pretrained(
            model_name=args.adapter_path,
            max_seq_length=args.max_new_tokens + 512,
            dtype=None,
            load_in_4bit=True,
            token=args.hf_token,
        )
        FastLanguageModel.for_inference(lora_model)

        lora_metrics, lora_examples = evaluate_model(
            lora_model, tokenizer, test_data, device, "LoRA",
            num_samples=args.num_samples,
            temperature=args.temperature,
            max_new_tokens=args.max_new_tokens,
        )
        print_results(lora_metrics, "LORA MODEL (fine-tuned)")
        print_examples(lora_examples, n=args.show_examples, label="LoRA")
        results["lora"] = lora_metrics

        # ── Comparison ─────────────────────────────────────────────────────────
        diff = lora_metrics["accuracy"] - base_metrics["accuracy"]
        print(f"\n{'='*60}")
        print(f"  IMPROVEMENT: {diff:+.2%}")
        print(f"  Base: {base_metrics['accuracy']:.2%}  →  "
              f"LoRA: {lora_metrics['accuracy']:.2%}")
        print(f"{'='*60}")

        # Error analysis: which problems moved in which direction
        fixed, broke, both_right, both_wrong = 0, 0, 0, 0
        for b, l in zip(base_examples, lora_examples):
            if not b["correct"] and l["correct"]:
                fixed += 1
            elif b["correct"] and not l["correct"]:
                broke += 1
            elif b["correct"] and l["correct"]:
                both_right += 1
            else:
                both_wrong += 1

        print("\n  Per-example breakdown:")
        print(f"  Both correct:       {both_right}")
        print(f"  Both wrong:         {both_wrong}")
        print(f"  LoRA fixed:         {fixed}  (base wrong → LoRA right)")
        print(f"  LoRA broke:         {broke}  (base right → LoRA wrong)")
        print(f"  Net fixes:          {fixed - broke:+d}")

    # ── Save ───────────────────────────────────────────────────────────────────
    output = {
        "metrics": results,
        "config": vars(args),
    }
    if not args.base_only:
        output["sample_predictions"] = {
            "base": base_examples[:20],
            "lora": lora_examples[:20],
        }

    with open(args.output_file, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {args.output_file}")


if __name__ == "__main__":
    main()
