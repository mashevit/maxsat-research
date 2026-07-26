#!/usr/bin/env python
"""gen_modelfile.py ── emit the Ollama Modelfile FROM utils.build_prompt().

Hand-writing the TEMPLATE is the silent-failure path: the v1 Modelfile was written
against Llama's prompt format, and a single wrong newline seam shows up as a low
agreement score that looks like quantization loss. So we don't hand-write it.

We call utils.build_prompt() on a sentinel, split the result around the sentinel,
and emit prefix + {{ .Prompt }} + suffix. Character-for-character by construction.
Decoding params come from utils.GREEDY, the same dict the transformers side reads.
"""
import argparse

import utils

SENTINEL = "\x00__QUESTION_SENTINEL__\x00"

# utils.GREEDY key -> Ollama PARAMETER name
PARAM_MAP = {
    "temperature": "temperature",
    "top_p": "top_p",
    "top_k": "top_k",
    "repeat_penalty": "repeat_penalty",
    "repetition_penalty": "repeat_penalty",
    "seed": "seed",
    "max_new_tokens": "num_predict",
    "num_predict": "num_predict",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gguf", required=True, help="absolute path to the Q8_0 gguf")
    ap.add_argument("--out", default="Modelfile")
    args = ap.parse_args()

    full = utils.build_prompt(SENTINEL)
    if SENTINEL not in full:
        raise SystemExit(
            "build_prompt() did not embed the question verbatim; "
            "cannot derive a TEMPLATE automatically. Inspect utils.build_prompt."
        )
    prefix, suffix = full.split(SENTINEL, 1)

    lines = [f"FROM {args.gguf}", ""]
    lines.append('TEMPLATE """' + prefix + "{{ .Prompt }}" + suffix + '"""')
    lines.append("")

    greedy = dict(getattr(utils, "GREEDY", {}))
    stops = greedy.pop("stop", None) or greedy.pop("stop_sequences", None) or []
    for k, v in greedy.items():
        name = PARAM_MAP.get(k)
        if name is None:
            print(f"[warn] GREEDY key {k!r}={v!r} has no Ollama PARAMETER equivalent; skipped")
            continue
        if isinstance(v, bool):
            continue  # e.g. do_sample — expressed via temperature 0
        if v is None:
            continue
        lines.append(f"PARAMETER {name} {v}")
    for s in stops:
        lines.append(f'PARAMETER stop "{s}"')

    text = "\n".join(lines) + "\n"
    with open(args.out, "w") as f:
        f.write(text)

    print(f"[modelfile] wrote {args.out}\n")
    print(text)
    print("[modelfile] prefix repr:", repr(prefix))
    print("[modelfile] suffix repr:", repr(suffix))


if __name__ == "__main__":
    main()
