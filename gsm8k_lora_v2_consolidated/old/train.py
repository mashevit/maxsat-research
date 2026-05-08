"""
GSM8K LoRA Fine-Tuning
========================
QLoRA (4-bit) fine-tuning on GSM8K math reasoning, powered by Unsloth
for ~2x faster training and ~60% less VRAM vs the stock HF stack.

Supports Llama (2/3/3.1/3.2/3.3), Mistral, Qwen, Phi, Gemma, and most
derivatives. Pre-quantized weights available at huggingface.co/unsloth.

Usage:
    python train.py                                   # Llama 3.2 3B default
    python train.py --model_name unsloth/mistral-7b-v0.3
    python train.py --model_name unsloth/llama-3-8b-bnb-4bit
    python train.py --quick                           # 5-min sanity check
"""

import argparse
import os
import json
import re
import torch

# IMPORTANT: Unsloth must be imported BEFORE transformers for its patches
# to take effect. Keep this import at the top.
from unsloth import FastLanguageModel, is_bfloat16_supported

from datasets import load_dataset
from transformers import TrainingArguments
from trl import SFTTrainer, DataCollatorForCompletionOnlyLM

from utils import (
    build_training_example,
    RESPONSE_TEMPLATE,
    set_seed,
    log_hardware,
)


def clean_gsm8k_answer(answer_text: str) -> str:
    """Strip the <<calculator>> annotations from GSM8K gold answers."""
    return re.sub(r'<<.*?>>', '', answer_text).strip()


def format_example(example):
    """Convert a GSM8K row into the training text format."""
    answer = clean_gsm8k_answer(example["answer"])
    return {"formatted_text": build_training_example(example["question"], answer)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_name", type=str,
                        default="unsloth/llama-3.2-3b-bnb-4bit",
                        help="HF model ID. Use unsloth/... for pre-quantized weights.")
    parser.add_argument("--num_train", type=int, default=0,
                        help="Train examples (0 = use all 7473 minus val split)")
    parser.add_argument("--val_size", type=int, default=300,
                        help="Validation examples CARVED FROM TRAIN (not test)")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=4,
                        help="Per-device batch size; Unsloth allows higher than stock HF")
    parser.add_argument("--grad_accum", type=int, default=4,
                        help="Effective batch = batch_size * grad_accum")
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--max_seq_len", type=int, default=512)
    parser.add_argument("--output_dir", type=str, default="./gsm8k_lora_model")
    parser.add_argument("--hf_token", type=str, default=None,
                        help="HF token (needed for gated Meta-Llama repos; "
                             "not needed for unsloth/... pre-quantized repos)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quick", action="store_true",
                        help="200 examples, 1 epoch — ~5 min sanity check")
    args = parser.parse_args()

    if args.quick:
        args.num_train = 200
        args.epochs = 1
        args.val_size = 50

    print(f"\n{'='*60}")
    print("GSM8K LoRA Training (Unsloth)")
    print(f"{'='*60}")
    print(f"  Model:         {args.model_name}")
    print(f"  Epochs:        {args.epochs}")
    print(f"  Batch size:    {args.batch_size}  "
          f"(effective: {args.batch_size * args.grad_accum})")
    print(f"  LoRA r/alpha:  {args.lora_r}/{args.lora_alpha}")
    print(f"  Seed:          {args.seed}")
    print(f"  Output:        {args.output_dir}")
    log_hardware()
    print(f"{'='*60}\n")

    set_seed(args.seed)

    # ── 1. Load + split dataset ────────────────────────────────────────────────
    # Validation is carved from TRAIN, not test. The original code leaked
    # the test split into training decisions (early stopping, best-checkpoint
    # selection). Now: test stays untouched until evaluate.py.
    print("Loading GSM8K dataset...")
    dataset = load_dataset("openai/gsm8k", "main")
    full_train = dataset["train"].shuffle(seed=args.seed)

    val_data = full_train.select(range(args.val_size))
    remaining_train = full_train.select(range(args.val_size, len(full_train)))

    if args.num_train > 0:
        train_data = remaining_train.select(range(min(args.num_train, len(remaining_train))))
    else:
        train_data = remaining_train

    train_data = train_data.map(format_example)
    val_data = val_data.map(format_example)

    print(f"  Train: {len(train_data)}  |  Val: {len(val_data)}  |  Test: held out\n")

    print("--- Sample training example ---")
    print(train_data[0]["formatted_text"][:500])
    print("---\n")

    # ── 2. Load model via Unsloth ──────────────────────────────────────────────
    # FastLanguageModel.from_pretrained handles quantization, tokenizer,
    # and the fast-path kernel patches in one call. No separate
    # BitsAndBytesConfig needed.
    print(f"Loading model: {args.model_name}...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.model_name,
        max_seq_length=args.max_seq_len,
        dtype=None,                    # auto-detect bf16/fp16
        load_in_4bit=True,
        token=args.hf_token,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── 3. Apply LoRA via Unsloth ──────────────────────────────────────────────
    # Target modules include both attention (q/k/v/o) and MLP (gate/up/down).
    # Attention-only was the old default; adding MLP is now standard practice
    # for reasoning tasks.
    #
    # Note: lora_dropout=0 and use_gradient_checkpointing="unsloth" are
    # required by Unsloth's fast path — don't change them.
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0,                # required by Unsloth fast path
        bias="none",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",      # attention
            "gate_proj", "up_proj", "down_proj",         # MLP
        ],
        use_gradient_checkpointing="unsloth",  # Unsloth's optimized version
        random_state=args.seed,
        use_rslora=False,
        loftq_config=None,
    )

    # ── 4. Completion-only loss collator ───────────────────────────────────────
    # Without this, loss is computed on the full sequence (prompt + answer).
    # The model wastes capacity learning to reproduce "Solve the following
    # math problem...". This collator masks prompt tokens so loss applies
    # only to the answer portion. Expected impact: meaningful accuracy gain.
    collator = DataCollatorForCompletionOnlyLM(
        response_template=RESPONSE_TEMPLATE,
        tokenizer=tokenizer,
    )

    # ── 5. Training arguments ──────────────────────────────────────────────────
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        weight_decay=0.01,
        warmup_ratio=0.05,
        lr_scheduler_type="cosine",
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=200,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        optim="adamw_8bit",
        report_to="none",
        max_grad_norm=0.3,
        seed=args.seed,
        data_seed=args.seed,
    )

    # ── 6. Train ───────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        train_dataset=train_data,
        eval_dataset=val_data,
        processing_class=tokenizer,
        args=training_args,
        max_seq_length=args.max_seq_len,
        data_collator=collator,
    )

    print("\nStarting training...")
    train_result = trainer.train()

    # ── 7. Save ────────────────────────────────────────────────────────────────
    print(f"\nSaving adapter to {args.output_dir}")
    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    with open(os.path.join(args.output_dir, "training_config.json"), "w") as f:
        json.dump(vars(args), f, indent=2)

    metrics = {
        "train_runtime_seconds": train_result.metrics.get("train_runtime"),
        "train_samples_per_second": train_result.metrics.get("train_samples_per_second"),
        "train_loss": train_result.metrics.get("train_loss"),
    }
    with open(os.path.join(args.output_dir, "training_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  Train runtime:  {metrics['train_runtime_seconds']:.1f} sec")
    print(f"  Samples/sec:    {metrics['train_samples_per_second']:.2f}")
    print(f"  Final loss:     {metrics['train_loss']:.4f}")

    print("\n✅ Training complete!")
    print(f"Next: python evaluate.py --model_name {args.model_name} "
          f"--adapter_path {args.output_dir}")


if __name__ == "__main__":
    main()
