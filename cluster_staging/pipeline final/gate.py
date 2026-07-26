"""
Merge-fidelity gate.

Replaces free-running greedy string comparison (a chaos amplifier under argmax)
with a teacher-forced logit comparison, which is deterministic and does not
compound divergence across positions.

Usable two ways:

  1. imported:  from gate import assert_merged_dtype, logit_gate, load_kwargs
  2. standalone dtype check:
         python gate.py --check-dtype /home/mashevit/gsm8k_lora_v2/merged_16bit
"""

import argparse
import json
import os

import torch
import torch.nn.functional as F

# ---------------------------------------------------------------------------
# These MUST be identical on both sides of the comparison. attn_implementation
# in particular changes float accumulation order and is a real source of drift.
# ---------------------------------------------------------------------------
DTYPE = torch.float16
ATTN = "eager"
DEVICE = "cuda"

ATOL_LOGIT = 0.05        # worst max|Δlogit| across all compared positions
MIN_TOP1_AGREE = 0.999   # fraction of positions where argmax must agree


def load_kwargs():
    return dict(dtype=DTYPE, attn_implementation=ATTN, device_map={"": 0})


# ---------------------------------------------------------------------------
# dtype assertion
# ---------------------------------------------------------------------------
def read_merged_dtype(path):
    cfg_path = os.path.join(path, "config.json")
    with open(cfg_path) as f:
        cfg = json.load(f)
    # transformers moved torch_dtype -> dtype; accept either key
    return cfg.get("dtype") or cfg.get("torch_dtype")


def assert_merged_dtype(path, expected="float16"):
    d = read_merged_dtype(path)
    print(f"[gate] {path}/config.json dtype = {d!r}")
    if d != expected:
        raise SystemExit(
            f"[gate] FAIL — merged config dtype is {d!r}, expected {expected!r}. "
            f"The export path is not fp16; fix merge_export.py before GGUF."
        )
    return d


# ---------------------------------------------------------------------------
# logit gate
# ---------------------------------------------------------------------------
@torch.no_grad()
def _seq_logits(model, ids):
    return model(**ids).logits[0].float()   # [T, V]


@torch.no_grad()
def logit_gate(model_a, model_b, tok, texts,
               atol=ATOL_LOGIT, min_top1=MIN_TOP1_AGREE, max_len=512):
    """
    model_a : reference  (base fp16 + adapter, unmerged)
    model_b : candidate  (reloaded merged fp16)
    texts   : prompt + fixed continuation. Fully teacher-forced, so the
              continuation does not have to be *correct* — only identical
              for both sides.

    Returns True on pass.

    Interpretation:
      clean merge  -> max|Δlogit| < ~0.05, top1 agreement 1.000
      corruption   -> deltas in the tens/hundreds, top1 disagreement on
                      high-margin tokens
    """
    worst_delta = 0.0
    worst_kl = 0.0
    tot_pos = 0
    tot_agree = 0

    for i, t in enumerate(texts):
        ids = tok(t, return_tensors="pt", truncation=True,
                  max_length=max_len).to(DEVICE)

        la = _seq_logits(model_a, ids)
        lb = _seq_logits(model_b, ids)
        if la.shape != lb.shape:
            raise SystemExit(f"[gate] FAIL — logit shape mismatch {la.shape} vs {lb.shape}")

        d = (la - lb).abs().max().item()

        agree = (la.argmax(-1) == lb.argmax(-1))
        n = agree.numel()
        n_ok = int(agree.sum().item())

        kl = F.kl_div(
            torch.log_softmax(lb, -1),
            torch.log_softmax(la, -1),
            reduction="none", log_target=True,
        ).sum(-1).max().item()

        worst_delta = max(worst_delta, d)
        worst_kl = max(worst_kl, kl)
        tot_pos += n
        tot_agree += n_ok

        print(f"  item {i}: T={n:4d}  max|dlogit|={d:9.5f}  "
              f"max_KL={kl:10.6f}  top1={n_ok}/{n}")

        if n_ok < n:
            bad = (~agree).nonzero().flatten()[:5].tolist()
            for p in bad:
                top2 = la[p].topk(2).values
                margin = (top2[0] - top2[1]).item()
                a_tok = tok.decode([int(la[p].argmax())])
                b_tok = tok.decode([int(lb[p].argmax())])
                flag = "  <-- HIGH MARGIN" if margin > 0.5 else ""
                print(f"      pos {p:4d}: A={a_tok!r} B={b_tok!r} "
                      f"A_margin={margin:.4f}{flag}")

    frac = tot_agree / max(tot_pos, 1)
    print(f"[gate] worst max|dlogit| = {worst_delta:.5f}   (atol {atol})")
    print(f"[gate] worst max KL      = {worst_kl:.6f}")
    print(f"[gate] top1 agreement    = {tot_agree}/{tot_pos} = {frac:.5f}   (min {min_top1})")

    ok = (worst_delta < atol) and (frac >= min_top1)
    print(f"[gate] {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------------------------------------------------------
# optional behavioral secondary: #### N extraction agreement
# ---------------------------------------------------------------------------
def extract_answer(text):
    if "####" not in text:
        return None
    tail = text.split("####")[-1].strip().split()
    if not tail:
        return None
    return tail[0].strip(".,$").replace(",", "")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-dtype", metavar="MERGED_DIR",
                    default="/home/mashevit/gsm8k_lora_v2/merged_16bit")
    ap.add_argument("--expected", default="float16")
    a = ap.parse_args()
    assert_merged_dtype(a.check_dtype, a.expected)
    print("[gate] dtype OK")
