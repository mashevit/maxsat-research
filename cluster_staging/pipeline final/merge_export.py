"""
merge_export.py

Merge the LoRA adapter onto a full-precision base and export fp16, then gate
the exported artifact for gross corruption.

Modes
-----
  --mode merge+gate   (default) merge, save, reload from disk, gate.
  --mode gate-only    skip the merge; gate whatever is already at MERGED_DIR.
                      Use this to re-run the gate without paying for the merge.

Exit code
---------
  0 = gate PASS   -> safe to proceed to GGUF conversion
  1 = gate FAIL
  2 = setup error (bad dtype, missing merged dir)

Gate criteria live in merge_gate.py. They are behavioral (top1 agreement, KL),
not an absolute tolerance on raw logits -- see the module docstring there.
"""

from __future__ import annotations

import argparse
import os
import sys

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

import merge_gate
import utils  # build_prompt() / GREEDY remain the single source of truth

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------

BASE_ID = os.environ.get("BASE_ID", "unsloth/Qwen3-8B")
ADAPTER_DIR = os.environ.get(
    "ADAPTER_DIR", "/home/mashevit/gsm8k_lora_v2/adapter"
)
MERGED_DIR = os.environ.get(
    "MERGED_DIR", "/home/mashevit/gsm8k_lora_v2/merged_16bit"
)

# ----------------------------------------------------------------------------
# Gate items -- frozen so gate output is comparable run to run.
# 5 items is enough: this catches gross corruption, not drift.
# ----------------------------------------------------------------------------

GATE_ITEMS_RAW = [
    ("Natalia sold clips to 48 of her friends in April, and then she sold half "
     "as many clips in May. How many clips did Natalia sell altogether in April "
     "and May?",
     " Natalia sold 48/2 = 24 clips in May.\nNatalia sold 48+24 = 72 clips "
     "altogether in April and May.\n#### 72"),
    ("Weng earns $12 an hour for babysitting. Yesterday, she just did 50 "
     "minutes of babysitting. How much did she earn?",
     " Weng earns 12/60 = $0.2 per minute.\nWorking 50 minutes, she earned "
     "0.2 x 50 = $10.\n#### 10"),
    ("Betty is saving money for a new wallet which costs $100. Betty has only "
     "half of the money she needs. Her parents decided to give her $15 for that "
     "purpose, and her grandparents twice as much as her parents. How much more "
     "money does Betty need to buy the wallet?",
     " In the beginning, Betty has only 100/2 = $50.\nBetty's grandparents gave "
     "her 15 * 2 = $30.\nThis means, Betty needs 100 - 50 - 30 - 15 = $5 more.\n"
     "#### 5"),
    ("James writes a 3-page letter to 2 different friends twice a week. How many "
     "pages does he write a year?",
     " He writes each friend 3*2 = 6 pages a week.\nSo he writes 6*2 = 12 pages "
     "every week.\nThat means he writes 12*52 = 624 pages a year.\n#### 624"),
    ("Mark has a garden with flowers. He planted plants of three different "
     "colors in it. Ten of them are yellow, and there are 80% more of those in "
     "purple. There are only 25% as many green flowers as there are yellow and "
     "purple flowers. How many flowers does Mark have in his garden?",
     " There are 80/100 * 10 = 8 more purple flowers than yellow flowers.\nSo "
     "in Mark's garden, there are 10 + 8 = 18 purple flowers.\nPurple and "
     "yellow flowers sum up to 10 + 18 = 28 flowers.\nThat means in Mark's "
     "garden there are 25/100 * 28 = 7 green flowers.\nSo in total Mark has "
     "28 + 7 = 35 plants in his garden.\n#### 35"),
]


def build_gate_items():
    return [
        {"prompt": utils.build_prompt(q), "completion": a}
        for q, a in GATE_ITEMS_RAW
    ]


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------


def load_fp16(path_or_id: str, what: str):
    m = AutoModelForCausalLM.from_pretrained(
        path_or_id, torch_dtype=torch.float16, device_map={"": 0}
    )
    dt = merge_gate.param_dtype(m)
    if dt != torch.float16:
        print(
            f"[setup] FATAL: {what} loaded as {dt}, expected float16. "
            f"A silent bf16 load produces the exact signature of healthy "
            f"fp16 rounding and would make the gate meaningless.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"[setup] {what}: {path_or_id}  dtype={dt}")
    return m


def do_merge(tok) -> None:
    print("[merge] loading second independent base fp16")
    base = load_fp16(BASE_ID, "merge base")
    peft = PeftModel.from_pretrained(base, ADAPTER_DIR)
    print(f"[merge] merge_and_unload -> {MERGED_DIR}")
    merged = peft.merge_and_unload()
    merged.save_pretrained(MERGED_DIR, safe_serialization=True)
    tok.save_pretrained(MERGED_DIR)
    del merged, peft, base
    torch.cuda.empty_cache()
    print("[merge] done")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        choices=["merge+gate", "gate-only"],
        default="merge+gate",
        help="gate-only skips the merge and gates the existing MERGED_DIR",
    )
    ap.add_argument(
        "--overwrite",
        action="store_true",
        help="in merge+gate mode, merge even if MERGED_DIR already exists",
    )
    args = ap.parse_args()

    if not torch.cuda.is_available():
        print("[setup] FATAL: no CUDA device", file=sys.stderr)
        sys.exit(2)
    print(f"[env] torch {torch.__version__}  cuda {torch.version.cuda}")
    print(
        f"[env] device {torch.cuda.get_device_name(0)}  "
        f"{torch.cuda.get_device_properties(0).total_memory / 2**30:.1f} GiB"
    )
    print(f"[env] mode = {args.mode}")

    tok = AutoTokenizer.from_pretrained(BASE_ID)
    exists = os.path.isdir(MERGED_DIR) and os.path.isfile(
        os.path.join(MERGED_DIR, "config.json")
    )

    if args.mode == "merge+gate":
        if exists and not args.overwrite:
            print(
                f"[merge] MERGED_DIR already populated: {MERGED_DIR}\n"
                f"[merge] refusing to overwrite. Pass --overwrite to re-merge, "
                f"or use --mode gate-only to just re-run the gate.",
                file=sys.stderr,
            )
            sys.exit(2)
        do_merge(tok)
    else:
        if not exists:
            print(
                f"[setup] FATAL: gate-only requested but no merged model at "
                f"{MERGED_DIR}",
                file=sys.stderr,
            )
            sys.exit(2)
        print(f"[gate] gate-only: using existing {MERGED_DIR}")

    # Reference: base fp16 + adapter (unmerged, live PEFT wrapper)
    print("[gate] loading reference: base fp16 + adapter")
    ref_base = load_fp16(BASE_ID, "reference base")
    ref_model = PeftModel.from_pretrained(ref_base, ADAPTER_DIR)
    ref_model.eval()

    # Subject: the artifact on disk, reloaded. Gate the file, not the object
    # that produced it.
    print("[gate] reloading merged fp16 from disk")
    merged_model = load_fp16(MERGED_DIR, "merged")
    merged_model.eval()

    res = merge_gate.run_gate(
        ref_model,
        merged_model,
        tok,
        build_gate_items(),
        device="cuda",
        strict_dtype=True,
    )

    if res.passed:
        print("[gate] PASS -> safe to proceed to GGUF conversion")
        sys.exit(0)
    print("[gate] FAIL -> do NOT proceed to GGUF", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
