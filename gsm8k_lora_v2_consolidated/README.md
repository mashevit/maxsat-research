# GSM8K LoRA Fine-Tuning on BGU HPC

Fine-tune a small LLM with QLoRA on GSM8K math reasoning, then evaluate
base vs fine-tuned model. Uses Unsloth for fast training.

---

## What changed from v1

### Correctness fixes

1. **Completion-only loss** — The original computed loss on every
   token including the prompt. The model spent capacity learning to
   reproduce "Solve the following math problem...". Now loss is masked
   to apply only to the answer portion via
   `SFTConfig(completion_only_loss=True)` with the dataset in
   prompt-completion format. (Earlier versions used
   `DataCollatorForCompletionOnlyLM`, which was removed from `trl`
   in favor of this approach.) Expected impact: meaningful accuracy
   gain, especially for reasoning.

2. **No test-set leakage** — The original used `dataset["test"]` for
   validation during training (early stopping, best-checkpoint
   selection), then used overlapping examples in `evaluate.py`. Now
   validation is carved from `dataset["train"]`; test stays untouched
   until eval.

3. **Seeded runs** — Seeds are now propagated through dataset shuffle,
   model init, and sampling. Re-running the same command gives the
   same numbers, which you need to have meaningful comparisons.

### Accuracy improvements

4. **Expanded LoRA targets** — Now includes MLP layers
   (`gate_proj`, `up_proj`, `down_proj`) in addition to attention.
   Documented improvement for reasoning tasks.

5. **Self-consistency evaluation** — Generate N samples with
   temperature, take the majority vote. Enable with
   `--num_samples 8 --temperature 0.7`. Usually +5-15pp over greedy.

### Speed

6. **Unsloth backend** — ~2x faster training, ~60% less VRAM vs the
   stock HF stack. Drop-in via `FastLanguageModel`.

### Code quality

7. **Shared `utils.py`** — Prompt format (`build_prompt`,
   `build_completion`), answer extraction, seeding, and hardware
   logging are centralized. Previously the prompt format was
   duplicated across `train.py` and `evaluate.py`, a common source of
   silent bugs (train and eval formats drift apart).

---

## Supported models

Unsloth supports most open-weights families. Common choices:

| Model                              | Params | VRAM    | Good for                      |
|------------------------------------|--------|---------|-------------------------------|
| `unsloth/llama-3.2-1b-bnb-4bit`    | 1B     | ~5 GB   | Quick experiments             |
| `unsloth/llama-3.2-3b-bnb-4bit`    | 3B     | ~8 GB   | **Default** — good balance    |
| `unsloth/llama-3-8b-bnb-4bit`      | 8B     | ~16 GB  | Stronger results              |
| `unsloth/mistral-7b-v0.3`          | 7B     | ~14 GB  | Alternative to Llama          |
| `unsloth/Qwen2.5-7B-bnb-4bit`      | 7B     | ~14 GB  | Strong at reasoning/code      |
| `unsloth/Phi-3-mini-4k-bnb-4bit`   | 3.8B   | ~8 GB   | Compact, strong               |

The `unsloth/...` repos are pre-quantized — they load faster than
quantizing-on-the-fly from the original Meta/Mistral/Qwen repos.
For gated models (some Meta Llama repos), you need `--hf_token`.

---

## Quick Start

### 1. Setup (on login node, first time only)

For RTX 6000 Ada (CC 8.9) and similar modern GPUs, plain `pip install
unsloth` works and pulls a compatible PyTorch automatically — no nvcc
compile, no GPU node required for the install itself.

```bash
cp -r gsm8k_lora_v2 ~/gsm8k_lora
cd ~/gsm8k_lora

conda create -n gsm8k_lora python=3.11 -y
conda activate gsm8k_lora

pip install "numpy<2"
pip install unsloth                # pulls torch + transformers + peft + bnb + accelerate
pip install datasets trl scipy tqdm
```

For older GPUs or pinned torch versions, use an explicit Unsloth extra
matching your CUDA + torch combo. See
[unsloth installation docs](https://github.com/unslothai/unsloth#installation).

### 2. Sanity check (5 min)

```bash
python train.py --quick
```

Runs on 200 examples for 1 epoch. Verifies imports, dataset loading,
and that loss decreases. If this passes, the full run will work.

### 3. Train

```bash
sbatch train.sbatch
```

### 4. Evaluate

```bash
sbatch eval.sbatch
```

---

## Expected output

Greedy eval (default):

```
  BASE MODEL (no LoRA)
  Accuracy:             12.50% (25/200)

  LORA MODEL (fine-tuned)
  Accuracy:             42.50% (85/200)

  IMPROVEMENT: +30.00%

  Per-example breakdown:
  Both correct:       25
  Both wrong:         115
  LoRA fixed:         60     (base wrong → LoRA right)
  LoRA broke:         0      (base right → LoRA wrong)
  Net fixes:          +60
```

Self-consistency eval (uncomment in `eval.sbatch`):

```
  LORA MODEL (fine-tuned, sc=8)
  Accuracy:             52.50% (105/200)    ← +10pp typical
```

---

## Files

| File                | What it does                                    |
|---------------------|-------------------------------------------------|
| `utils.py`          | Shared prompts, extraction, seeding             |
| `train.py`          | Unsloth QLoRA fine-tuning                       |
| `evaluate.py`       | Base vs LoRA, optional self-consistency         |
| `train.sbatch`      | SLURM job for train.py                          |
| `eval.sbatch`       | SLURM job for evaluate.py                       |
| `requirements.txt`  | Python dependencies                             |

---

## Hyperparameter notes

- `--lora_r 16` is fine for GSM8K. r=32 rarely helps; r=8 may underfit.
- `--lr 2e-4` is standard. If training is unstable, try 1e-4.
- `--batch_size 4` works with Unsloth on 24GB. Drop to 2 if you OOM.
- `--lora_dropout` is fixed at 0 (Unsloth fast-path requires it).

## Running A/B experiments

Because seeds are respected, A/B comparisons are meaningful:

```bash
# Run A: attention-only LoRA (edit target_modules in train.py)
python train.py --output_dir ./runs/attn_only --seed 42

# Run B: attention + MLP (as shipped)
python train.py --output_dir ./runs/attn_mlp  --seed 42

# Evaluate both against the same test set
python evaluate.py --adapter_path ./runs/attn_only --seed 42 --output_file a.json
python evaluate.py --adapter_path ./runs/attn_mlp  --seed 42 --output_file b.json
```

With identical seeds, any accuracy difference is attributable to the
change, not noise — the same discipline you'll want for MaxSAT experiments.
