"""
merge_gate.py

Merge-fidelity gate: catches gross corruption of a merged fp16 model
(e.g. tied-embedding merge corruption) independently of GGUF quantization.

Design notes
------------
Corruption is a *behavioral* property, so the gate asserts behavior:

  PASS criteria
    1. top1 agreement >= TOP1_MIN   (0.999)
    2. worst max KL   <= KL_MAX     (1e-2)

  DIAGNOSTIC ONLY (never gates)
    - max|dlogit|      : absolute logit delta. Meaningless as a threshold --
                         logits are unnormalized, |logit| ~ 20-30, and one fp16
                         ULP at that magnitude is ~0.016. Rounding across all
                         layers reaches ~0.2 on a perfectly healthy merge.
    - rel_dlogit       : scale-free form. < ~0.02 is noise.

Why absolute logit tolerance cannot hold: the reference computes
    x @ W + (x @ A) @ B      (two matmuls, separate accumulators)
the merged model computes
    x @ (W + BA)             (one matmul, one accumulator, W+BA rounded to fp16
                              once at merge time)
These agree in real arithmetic, not in float arithmetic. An atol on logits is
testing for a property that is not required to be true.

A healthy merge sits at KL ~1e-4 and top1 == 1.0.
A corrupted merge sits at KL ~1e-1..1e1 and top1 ~0.3.
The gap is ~3 orders of magnitude; KL_MAX=1e-2 sits in the middle of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn.functional as F

# ----------------------------------------------------------------------------
# Gate thresholds
# ----------------------------------------------------------------------------

TOP1_MIN = 0.999   # gates
KL_MAX = 1e-2      # gates
REL_DLOGIT_NOTE = 0.02  # diagnostic reference point only, never gates


# ----------------------------------------------------------------------------
# Results
# ----------------------------------------------------------------------------


@dataclass
class ItemResult:
    index: int
    n_tokens: int
    max_abs_dlogit: float
    rel_dlogit: float
    max_kl: float
    top1_match: int


@dataclass
class GateResult:
    items: list[ItemResult] = field(default_factory=list)

    @property
    def worst_max_abs_dlogit(self) -> float:
        return max(i.max_abs_dlogit for i in self.items)

    @property
    def worst_rel_dlogit(self) -> float:
        return max(i.rel_dlogit for i in self.items)

    @property
    def worst_max_kl(self) -> float:
        return max(i.max_kl for i in self.items)

    @property
    def top1_matched(self) -> int:
        return sum(i.top1_match for i in self.items)

    @property
    def top1_total(self) -> int:
        return sum(i.n_tokens for i in self.items)

    @property
    def top1_agreement(self) -> float:
        return self.top1_matched / max(self.top1_total, 1)

    @property
    def passed(self) -> bool:
        return self.top1_agreement >= TOP1_MIN and self.worst_max_kl <= KL_MAX


# ----------------------------------------------------------------------------
# Precision-mismatch guard
# ----------------------------------------------------------------------------


def param_dtype(model) -> torch.dtype:
    """Dominant floating-point dtype of a model's parameters."""
    for p in model.parameters():
        if p.is_floating_point():
            return p.dtype
    raise RuntimeError("model has no floating-point parameters")


def assert_dtype_match(ref_model, merged_model, *, strict: bool = True) -> None:
    """
    The reference path is 'base fp16 + adapter'; the merged path is an fp16
    export. If the reference base silently loaded in bf16, the comparison
    signature is *identical to healthy rounding* (tiny KL, perfect top1,
    |dlogit| ~0.2) -- but it is a precision mismatch, not rounding, and it is
    the same class of silent error as the stacked-quantization confound.

    This is cheap. Always run it.
    """
    d_ref = param_dtype(ref_model)
    d_merged = param_dtype(merged_model)
    print(f"[gate] reference dtype = {d_ref}")
    print(f"[gate] merged    dtype = {d_merged}")
    if d_ref != d_merged:
        msg = (
            f"[gate] PRECISION MISMATCH: reference is {d_ref}, merged is "
            f"{d_merged}. The logit/KL comparison is not measuring merge "
            f"fidelity -- it is measuring a dtype difference."
        )
        if strict:
            raise RuntimeError(msg)
        print(msg)


# ----------------------------------------------------------------------------
# Teacher-forced comparison
# ----------------------------------------------------------------------------


@torch.no_grad()
def _forward_logits(model, input_ids, attention_mask) -> torch.Tensor:
    out = model(input_ids=input_ids, attention_mask=attention_mask)
    return out.logits.float()  # compare in fp32; the models stay in their dtype


@torch.no_grad()
def compare_item(
    ref_model,
    merged_model,
    input_ids: torch.Tensor,
    attention_mask: torch.Tensor,
    completion_start: int,
    index: int,
) -> ItemResult:
    """
    Teacher-forced comparison over the completion tokens only.

    input_ids       : (1, T)
    completion_start: index of the first completion token; positions
                      [completion_start-1, T-2] are the predicting positions.
    """
    lg_ref = _forward_logits(ref_model, input_ids, attention_mask)[0]
    lg_mrg = _forward_logits(merged_model, input_ids, attention_mask)[0]

    lo = max(completion_start - 1, 0)
    hi = input_ids.shape[1] - 1
    lg_ref = lg_ref[lo:hi]
    lg_mrg = lg_mrg[lo:hi]

    n_tokens = lg_ref.shape[0]

    # --- diagnostics (do not gate) -----------------------------------------
    abs_d = (lg_ref - lg_mrg).abs().amax().item()
    denom = lg_ref.abs().amax().clamp_min(1.0)
    rel_d = ((lg_ref - lg_mrg).abs().amax() / denom).item()

    # --- gating signals -----------------------------------------------------
    logp_ref = F.log_softmax(lg_ref, dim=-1)
    logp_mrg = F.log_softmax(lg_mrg, dim=-1)
    # KL(ref || merged), per position, take the worst position
    kl = (logp_ref.exp() * (logp_ref - logp_mrg)).sum(dim=-1)
    max_kl = kl.amax().item()

    top1 = (lg_ref.argmax(dim=-1) == lg_mrg.argmax(dim=-1)).sum().item()

    return ItemResult(
        index=index,
        n_tokens=n_tokens,
        max_abs_dlogit=abs_d,
        rel_dlogit=rel_d,
        max_kl=max_kl,
        top1_match=top1,
    )


@torch.no_grad()
def run_gate(
    ref_model,
    merged_model,
    tokenizer,
    items: list[dict],
    *,
    device: str | torch.device = "cuda",
    strict_dtype: bool = True,
) -> GateResult:
    """
    items: list of {"prompt": str, "completion": str}

    Prompts must be built by utils.build_prompt() at the call site so that
    build_prompt() remains the single source of truth.
    """
    assert_dtype_match(ref_model, merged_model, strict=strict_dtype)

    ref_model.eval()
    merged_model.eval()

    print(f"[gate] teacher-forced comparison over {len(items)} items")
    res = GateResult()

    for i, item in enumerate(items):
        prompt_ids = tokenizer(item["prompt"], add_special_tokens=True).input_ids
        full_ids = tokenizer(
            item["prompt"] + item["completion"], add_special_tokens=True
        ).input_ids

        input_ids = torch.tensor([full_ids], device=device)
        attention_mask = torch.ones_like(input_ids)

        r = compare_item(
            ref_model,
            merged_model,
            input_ids,
            attention_mask,
            completion_start=len(prompt_ids),
            index=i,
        )
        res.items.append(r)
        print(
            f"  item {r.index}: T={r.n_tokens:4d}"
            f"  max|dlogit|={r.max_abs_dlogit:9.5f}"
            f"  rel={r.rel_dlogit:8.5f}"
            f"  max_KL={r.max_kl:10.6f}"
            f"  top1={r.top1_match}/{r.n_tokens}"
        )

    report(res)
    return res


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------


def report(res: GateResult) -> None:
    print()
    print("[gate] --- diagnostics (not gated) ---")
    print(f"[gate] worst max|dlogit| = {res.worst_max_abs_dlogit:.5f}")
    print(
        f"[gate] worst rel dlogit  = {res.worst_rel_dlogit:.5f}"
        f"   (< {REL_DLOGIT_NOTE} is fp16 arithmetic noise)"
    )
    print("[gate] --- criteria (gated) ---")
    kl_ok = res.worst_max_kl <= KL_MAX
    t1_ok = res.top1_agreement >= TOP1_MIN
    print(
        f"[gate] worst max KL      = {res.worst_max_kl:.6g}"
        f"   (max {KL_MAX})  {'OK' if kl_ok else 'FAIL'}"
    )
    print(
        f"[gate] top1 agreement    = {res.top1_matched}/{res.top1_total}"
        f" = {res.top1_agreement:.5f}"
        f"   (min {TOP1_MIN})  {'OK' if t1_ok else 'FAIL'}"
    )
    print(f"[gate] {'PASS' if res.passed else 'FAIL'}")
    print()
