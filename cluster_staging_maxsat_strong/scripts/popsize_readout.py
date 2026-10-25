#!/usr/bin/env python3
"""Batch POP readout: the pre-registered decision on R4's pop (10 vs 40).

docs/current2/POPSIZE_RUN.md section 5 (repo). Written before any result exists;
the rule below is that section, as code. Workstation only.

    python3 scripts/popsize_readout.py --outdir results/popsize/tasks \
        --csv results/popsize/agg/popsize_instances.csv

Per instance and arm (seeds 1-3, target = proven optimum or best-known):
  S  arrival: runs that reach the target (cost <= target) within 900 s;
  C  fitness: median final best cost;
  T  median time to target, a miss counting as infinite.
Per instance, the better arm is decided in this order:
  1. more arrivals (S);  2. lower median cost (C);
  3. when both arms reach the target in >= 2 runs: median TTT faster by a factor
     >= TTT_RATIO (1.25; wall-clock jitter below that is a tie);
  otherwise a tie.
An arm P wins a group of instances when all three hold:
  W1  P is better on more instances than Q, two-sided exact sign test over the
      non-tied instances p < alpha;
  W2  arrival gate: P reaches the target in at least as many runs in total, and
      the instances where Q has more arrivals are no more than those where P has;
  W3  fitness gate: among instances with equal arrivals, Q has the lower median
      cost on no more instances than P.
Groups: all instances (alpha 0.05) and the two R2 classes, unweighted (MSE 2023)
and weighted (MSE 2024 + rail), alpha 0.025 each. The class pop is the class
winner, else the overall winner, else 10 (today's R4).
An instance is used only when all 6 of its runs are valid: ok, stop at the target
or the time cap, 0 hard violations, and the pop R4 recorded equals the arm's.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
import statistics
import sys
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import m2_results as m2  # noqa: E402

ARMS = ("pop10", "pop40")
SEEDS = 3
TTT_RATIO = 1.25
ALPHA_ALL = 0.05
ALPHA_CLASS = 0.025
CLASSES = {"unweighted": "0", "weighted": "1"}     # the instances' `weighted` column
DEFAULT_POP = {"pop10": 10, "pop40": 40}
VALID_CLS = ("success", "budget_exhausted")


def arm_stats(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """runs: dicts with `success` (bool), `cost` (int), `ttt` (float or None)."""
    costs = sorted(r["cost"] for r in runs)
    ttts = sorted(r["ttt"] if r["success"] else math.inf for r in runs)
    return {"S": sum(r["success"] for r in runs), "C": statistics.median(costs),
            "T": statistics.median(ttts)}


def verdict(a: Dict[str, Any], b: Dict[str, Any]) -> Tuple[str, str]:
    """('a' | 'b' | 'tie', criterion) for arm stats a, b."""
    if a["S"] != b["S"]:
        return ("a" if a["S"] > b["S"] else "b"), "arrival"
    if a["C"] != b["C"]:
        return ("a" if a["C"] < b["C"] else "b"), "fitness"
    if a["S"] >= 2 and b["S"] >= 2:
        if a["T"] * TTT_RATIO <= b["T"]:
            return "a", "speed"
        if b["T"] * TTT_RATIO <= a["T"]:
            return "b", "speed"
    return "tie", ""


def sign_test(b: int, w: int) -> float:
    """Two-sided exact binomial sign test, H0 p = 1/2."""
    n = b + w
    if n == 0:
        return 1.0
    k = min(b, w)
    return min(1.0, 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def decide(rows: List[Dict[str, Any]], alpha: float) -> Dict[str, Any]:
    """rows: per instance, `pop10` / `pop40` arm stats; the W1-W3 decision for the group."""
    out: Dict[str, Any] = {"n": len(rows), "alpha": alpha}
    for x in ARMS:
        out[f"better_{x}"] = out[f"arrival_{x}"] = out[f"fitness_{x}"] = 0
        out[f"S_{x}"] = sum(r[x]["S"] for r in rows)
    for r in rows:
        v, crit = verdict(r["pop10"], r["pop40"])
        if v == "tie":
            continue
        x = "pop10" if v == "a" else "pop40"
        out[f"better_{x}"] += 1
        if crit == "arrival":
            out[f"arrival_{x}"] += 1
        elif crit == "fitness":
            out[f"fitness_{x}"] += 1
    out["ties"] = out["n"] - out["better_pop10"] - out["better_pop40"]
    out["p"] = sign_test(out["better_pop10"], out["better_pop40"])
    out["winner"] = None
    for p, q in (ARMS, ARMS[::-1]):
        w1 = out[f"better_{p}"] > out[f"better_{q}"] and out["p"] < alpha
        w2 = out[f"S_{p}"] >= out[f"S_{q}"] and out[f"arrival_{q}"] <= out[f"arrival_{p}"]
        w3 = out[f"fitness_{q}"] <= out[f"fitness_{p}"]
        out[f"gates_{p}"] = {"W1": w1, "W2": w2, "W3": w3}
        if w1 and w2 and w3:
            out["winner"] = p
    return out


def outcome(overall: Dict[str, Any], by_class: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    pops = {}
    for c, d in by_class.items():
        arm = d["winner"] or overall["winner"]
        pops[c] = DEFAULT_POP[arm] if arm else DEFAULT_POP["pop10"]
    if all(v == 10 for v in pops.values()):
        text = ("R4 pop 10 confirmed by the rule; no code change" if overall["winner"] == "pop10"
                or any(d["winner"] == "pop10" for d in by_class.values())
                else "no pop effect by the rule; R4 keeps pop 10 (no code change)")
    elif len(set(pops.values())) == 1:
        text = "R4 pop 40 on every hard instance (auto_hparams/4; waits for the user's go)"
    else:
        text = ("R4 pop by class: " + ", ".join(f"{c} {p}" for c, p in pops.items())
                + " (auto_hparams/4; waits for the user's go)")
    return {"pops": pops, "text": text}


def load(manifest: str, outdir: str):
    """(per-instance rows, list of excluded (pop_idx, reason))."""
    runs: Dict[str, Dict[str, list]] = defaultdict(lambda: defaultdict(list))
    meta: Dict[str, Dict[str, str]] = {}
    bad: Dict[str, List[str]] = defaultdict(list)
    for t in m2.evaluate(manifest, outdir):
        pi, arm = t["pop_idx"], t["arm"]
        meta[pi] = {k: t[k] for k in ("instance", "year", "family", "weighted", "oracle_cost", "oracle_kind")}
        r = m2.read_shard(os.path.join(outdir, f"{t['job_id']}.jsonl")) or {}
        why = None
        if t["cls"] not in VALID_CLS:
            why = t["cls"] + (f" ({t['note']})" if t["note"] else "")
        elif r.get("hard_violations") != 0:
            why = f"hard_violations={r.get('hard_violations')}"
        elif t["hp_pop_size"] != int(t["hard_pop"]):
            why = f"hp_pop_size={t['hp_pop_size']} (arm {t['hard_pop']})"
        if why:
            bad[pi].append(f"{t['job_id']}: {why}")
            continue
        runs[pi][arm].append({"success": t["cls"] == "success", "cost": int(t["best_cost"]),
                              "ttt": t["success_ttt_s"]})
    rows = []
    for pi in sorted(meta):
        if bad[pi] or any(len(runs[pi][a]) != SEEDS for a in ARMS):
            continue
        row = dict(pop_idx=pi, **meta[pi], **{a: arm_stats(runs[pi][a]) for a in ARMS})
        row["verdict"], row["criterion"] = verdict(row["pop10"], row["pop40"])
        rows.append(row)
    excluded = [(pi, "; ".join(bad[pi]) or "runs missing") for pi in sorted(meta)
                if bad[pi] or any(len(runs[pi][a]) != SEEDS for a in ARMS)]
    return rows, excluded


def flat(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {k: v for k, v in row.items() if k not in ARMS}
    out["verdict"] = {"a": "pop10", "b": "pop40"}.get(row["verdict"], "tie")
    tgt = max(abs(int(row["oracle_cost"])), 1)
    for a in ARMS:
        s = row[a]
        out.update({f"{a}_S": s["S"], f"{a}_median_cost": s["C"],
                    f"{a}_median_gap": round((s["C"] - int(row["oracle_cost"])) / tgt, 6),
                    f"{a}_median_ttt_s": "" if math.isinf(s["T"]) else round(s["T"], 2)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=os.path.join(ROOT, "scripts/manifest_popsize.tsv"))
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--csv", help="write the per-instance table here")
    a = ap.parse_args(argv)
    rows, excluded = load(a.manifest, a.outdir)
    print(f"instances used: {len(rows)}; excluded: {len(excluded)}")
    for pi, why in excluded[:20]:
        print(f"  excluded {pi}: {why}")
    if len(excluded) > 20:
        print(f"  ... {len(excluded) - 20} more")
    if a.csv and rows:
        os.makedirs(os.path.dirname(os.path.abspath(a.csv)), exist_ok=True)
        m2.write_csv(a.csv, [flat(r) for r in rows])
    overall = decide(rows, ALPHA_ALL)
    by_class = {c: decide([r for r in rows if r["weighted"] == w], ALPHA_CLASS) for c, w in CLASSES.items()}
    for name, d in [("all", overall)] + list(by_class.items()):
        print(f"{name:10s} n {d['n']:3d}  better pop10 {d['better_pop10']:3d} / pop40 {d['better_pop40']:3d}"
              f" / ties {d['ties']:3d}  p {d['p']:.4f} (alpha {d['alpha']})"
              f"  arrivals pop10 {d['S_pop10']} / pop40 {d['S_pop40']}"
              f"  [arrival {d['arrival_pop10']}/{d['arrival_pop40']}, fitness {d['fitness_pop10']}/"
              f"{d['fitness_pop40']}]  winner {d['winner'] or '-'}")
    o = outcome(overall, by_class)
    print(f"OUTCOME: {o['text']}  (pops {o['pops']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
