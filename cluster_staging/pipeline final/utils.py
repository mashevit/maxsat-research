"""
Shared utilities for GSM8K LoRA project.
============================================
Kept deliberately small. Imported by both train.py and evaluate.py
so the prompt format, answer extraction, and seeding are identical
across training and eval — mismatched formats are a common source
of "why did my LoRA not help" mysteries.
"""

import os
import re
import random
import numpy as np
import torch


# ── Prompt format ─────────────────────────────────────────────────────────────
# Must match exactly between training and evaluation. The prompt ends with
# RESPONSE_TEMPLATE, which is the boundary between what the model conditions
# on (prompt) and what the model is trained to generate (completion).

INSTRUCTION = (
    "Solve the following math problem step by step. "
    "Show your reasoning, then give the final answer after ####."
)

RESPONSE_TEMPLATE = "\n\nSolution:"


def build_prompt(question: str) -> str:
    """
    Prompt the model conditions on. Used identically at training and inference.
    Ends with RESPONSE_TEMPLATE so the model learns that whatever follows
    "Solution:" is the answer it should generate.
    """
    return f"{INSTRUCTION}\n\nProblem: {question}{RESPONSE_TEMPLATE}"


def build_completion(answer: str) -> str:
    """
    Completion the model is trained to generate. Leading space is intentional —
    it sits between RESPONSE_TEMPLATE ("...Solution:") and the answer text,
    matching what the model would naturally produce if it were just continuing
    the prompt.
    """
    return f" {answer}"


# ── Answer extraction ─────────────────────────────────────────────────────────

def extract_answer_from_gold(answer_text: str):
    """Extract the number after #### in GSM8K gold answers."""
    match = re.search(r'####\s*(-?[\d,]+(?:\.\d+)?)', answer_text)
    if match:
        return match.group(1).replace(",", "").strip()
    return None


def extract_answer_from_generation(text: str):
    """
    Multi-strategy extractor. Tries the strictest patterns first,
    falls back to last-number-in-text. Handles commas, $, decimals.
    """
    # Strategy 1: #### marker — the format we trained on
    match = re.search(r'####\s*\$?(-?[\d,]+(?:\.\d+)?)', text)
    if match:
        return _clean_number(match.group(1))

    # Strategy 2: "the answer is X" / "answer: X"
    match = re.search(
        r'(?:the answer is|answer is|answer:|final answer:?)\s*\$?(-?[\d,]+(?:\.\d+)?)',
        text, re.IGNORECASE
    )
    if match:
        return _clean_number(match.group(1))

    # Strategy 3: last "= X" in the text (most reasoning chains end with it)
    matches = re.findall(r'=\s*\$?(-?[\d,]+(?:\.\d+)?)', text)
    if matches:
        return _clean_number(matches[-1])

    # Strategy 4: last standalone number in the text
    matches = re.findall(r'(-?\d[\d,]*\.?\d*)', text)
    if matches:
        return _clean_number(matches[-1])

    return None


def _clean_number(s: str) -> str:
    """Strip $, commas, trailing punctuation."""
    return s.replace(",", "").replace("$", "").strip().rstrip(".")


def answers_match(pred, gold) -> bool:
    """Compare as floats where possible; fall back to string compare."""
    if pred is None or gold is None:
        return False
    try:
        return abs(float(pred) - float(gold)) < 1e-6
    except (ValueError, TypeError):
        return str(pred).strip() == str(gold).strip()


# ── Reproducibility ───────────────────────────────────────────────────────────

def set_seed(seed: int = 42, deterministic_cudnn: bool = False):
    """
    Seed everything that matters. Call BEFORE loading datasets/models.
    Note: deterministic_cudnn=True slows training but makes it fully
    reproducible bit-for-bit; usually leave False.
    """
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    if deterministic_cudnn:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


# ── Hardware info ─────────────────────────────────────────────────────────────

def log_hardware():
    """Print GPU info at start of a run. Helps when comparing runs later."""
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(i)
            total_gb = props.total_memory / 1e9
            print(f"  GPU {i}: {props.name}  ({total_gb:.1f} GB, "
                  f"CC {props.major}.{props.minor})")
    else:
        print("  No CUDA GPU available — running on CPU")
    print(f"  PyTorch:  {torch.__version__}")
    print(f"  CUDA:     {torch.version.cuda}")


# ── Decoding contract ─────────────────────────────────────────────────────────
# Single source of truth for decoding, mirroring what INSTRUCTION/RESPONSE_TEMPLATE
# do for prompt format. Both sides of the serving-fidelity comparison must decode
# identically, or the agreement number measures sampler divergence rather than
# quantization cost.
#
# The subtle one is repeat_penalty. Ollama defaults it to 1.1 and applies it to
# logits BEFORE the temperature-0 argmax, so greedy decoding does NOT neutralize
# it. HF's generate() defaults repetition_penalty to 1.0. Left unpinned, the two
# paths disagree on arithmetic (which repeats tokens heavily) while both claim to
# be "greedy".
#
# top_k/top_p are inert at temperature 0 (argmax ignores them) but are pinned
# anyway so the contract is explicit rather than relying on that invariant.

GREEDY = {
    # HF transformers side (phase A)
    "do_sample": False,
    "repetition_penalty": 1.0,
    "max_new_tokens": 256,

    # Ollama side (phase B) — keys match the /api/generate options schema
    "ollama_options": {
        "temperature": 0,
        "top_k": 1,
        "top_p": 1.0,
        "repeat_penalty": 1.0,
        "seed": 0,
        "num_ctx": 4096,
        "num_predict": 256,
    },

    # Stop strings. Empty on purpose: both sides terminate on the model's EOS
    # (config.json eos_token_id on the HF side, tokenizer.ggml.eos_token_id in
    # the GGUF). Adding stop strings to only one side is a classic silent
    # asymmetry. If you ever add one, add it to BOTH.
    "stop": [],
}
