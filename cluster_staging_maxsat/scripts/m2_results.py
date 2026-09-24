#!/usr/bin/env python3
"""Classify, resume and aggregate M2 memetic shards.

Reads a manifest written by scripts/make_m2_manifests.py (the .tsv plus its
.tasks.csv sidecar) and the one-record shards that run_memetic_shard.py writes
to OUTDIR/<job_id>.jsonl. See docs/M2_DEEPPOLISH_RUN_PREPARATION.md (repo).

Every task gets exactly one class:

    success              status ok, stop_reason target, time_to_target_s <= budget_s
                         (900 s in every M2 manifest)
    target_after_budget  status ok, stop_reason target, time_to_target_s > 900
                         (hit during the generation that straddles the budget;
                         NOT a success)
    budget_exhausted     status ok, stop_reason time_cap
    watchdog             status timeout: the unchanged SIGALRM watchdog fired at
                         budget + grace (960 s). The target was not reached by
                         then (a target hit stops the run first), so for the
                         success metric this is a non-success, like
                         budget_exhausted, but best_cost is not recorded. Not
                         expected on any M2 arm (the clipped arms end at the
                         budget; the control overshoots by <= ~19 s):
                         investigate before any resubmission.
    max_gens             status ok, stop_reason max_gens (unreachable at 1e6)
    cost_mismatch        integrity failure in the runner's cost cross-check
    invalid_submission   shard exists but does not match its manifest row
                         (job_id, config_id, seed, instance sha, budget, grace,
                         stop-at-oracle, pop_size, ls.time_limit_s,
                         ea.deadline_mode)
    infra_error          status error / parse_error / missing_instance / other
    infra_missing        no shard (Slurm kill, node failure, never ran) or an
                         unreadable one

RESUME. `pending` lists only infra_missing, infra_error and
invalid_submission. watchdog, budget_exhausted, target_after_budget,
cost_mismatch and max_gens are outcomes of the solver run itself and are never
resubmitted automatically; a watchdog row is investigated first (host, cpu/wall)
and resubmitted by hand only if it is shown to be an infrastructure fault.

    python3 scripts/m2_results.py pending   --manifest scripts/manifest_m2_pilot.tsv \
        --outdir results/m2_pilot/tasks [--summary]
    python3 scripts/m2_results.py aggregate --manifest scripts/manifest_m2_pilot.tsv \
        --outdir results/m2_pilot/tasks --out-dir results/m2_pilot/agg

Per-call quantities: shards record only run totals (total_flips, children,
wall_time_s). `mean_flips_per_call` = total_flips / children is a run MEAN;
no per-call distribution, per-call time or per-call stop reason can be derived
from these records, and none is reported.

stdlib only; run from the staging tree root.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

BUDGET_S = 900.0
GRACE_S = 60.0
PENDING_CLASSES = ("infra_missing", "infra_error", "invalid_submission")
CLASSES = ("success", "target_after_budget", "budget_exhausted", "watchdog", "max_gens",
           "cost_mismatch", "invalid_submission", "infra_error", "infra_missing")
GROUPS = ("lower_ext", "tier2", "upper_ext")


def load_tasks(manifest: str) -> List[Dict[str, str]]:
    side = manifest[:-len(".tsv")] + ".tasks.csv" if manifest.endswith(".tsv") else None
    if not side or not os.path.isfile(side):
        raise SystemExit(f"FATAL: sidecar {side} not found next to {manifest}")
    with open(side, encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))
    with open(manifest, encoding="utf-8") as f:
        lines = [l.rstrip("\n").split("\t") for l in f if l.strip()]
    if len(lines) != len(tasks) or any(l[0] != t["job_id"] for l, t in zip(lines, tasks)):
        raise SystemExit(f"FATAL: {manifest} and {side} disagree -- regenerate both")
    return tasks


def read_shard(path: str) -> Optional[dict]:
    try:
        with open(path, encoding="utf-8") as f:
            rows = [l for l in f if l.strip()]
        return json.loads(rows[-1]) if rows else None
    except (OSError, json.JSONDecodeError):
        return None


def mismatch(t: Dict[str, str], r: dict) -> Optional[str]:
    cfg = r.get("config") or {}
    checks = [
        ("job_id", r.get("job_id"), t["job_id"]),
        ("config_id", r.get("config_id"), t["config_id"]),
        ("seed", r.get("seed"), int(t["solver_seed"])),
        ("instance_sha256", r.get("instance_sha256"), t["instance_sha256"]),
        ("budget_s", r.get("budget_s"), float(t["budget_s"])),
        ("grace_s", r.get("grace_s"), GRACE_S),
        ("stop_at_oracle", r.get("stop_at_oracle"), True),
        ("oracle_cost", r.get("oracle_cost"), int(t["oracle_cost"])),
        ("ea.pop_size", (cfg.get("ea") or {}).get("pop_size"), int(t["pop_size"])),
        ("ls.time_limit_s", (cfg.get("ls") or {}).get("time_limit_s"), float(t["ls_time_limit_s"])),
        ("ls.ls_polish_flips", (cfg.get("ls") or {}).get("ls_polish_flips"), 12500),
        ("ea.deadline_mode", (cfg.get("ea") or {}).get("deadline_mode", ""),
         t.get("deadline_mode", "")),
    ]
    for name, got, want in checks:
        if got != want:
            return f"{name}={got!r} expected {want!r}"
    return None


def classify(t: Dict[str, str], r: Optional[dict]) -> (str, str):
    if r is None:
        return "infra_missing", ""
    status = r.get("status")
    # A missing instance / parse error leaves sha null; report it as infra, not
    # as an identity mismatch.
    if status in ("missing_instance", "parse_error"):
        return "infra_error", str(r.get("error"))
    bad = mismatch(t, r)
    if bad:
        return "invalid_submission", bad
    if status == "timeout":
        return "watchdog", str(r.get("error"))
    if status == "cost_mismatch":
        return "cost_mismatch", str(r.get("error"))
    if status != "ok":
        return "infra_error", f"status={status}: {r.get('error')}"
    sr = r.get("stop_reason")
    if sr == "target":
        ttt = r.get("time_to_target_s")
        if ttt is not None and float(ttt) <= float(t["budget_s"]):
            return "success", ""
        return "target_after_budget", f"time_to_target_s={ttt}"
    if sr == "time_cap":
        return "budget_exhausted", ""
    if sr == "max_gens":
        return "max_gens", ""
    return "infra_error", f"unknown stop_reason={sr!r}"


def evaluate(manifest: str, outdir: str) -> List[Dict[str, Any]]:
    out = []
    for t in load_tasks(manifest):
        r = read_shard(os.path.join(outdir, f"{t['job_id']}.jsonl"))
        cls, note = classify(t, r)
        r = r or {}
        wall, cpu = r.get("wall_time_s"), r.get("cpu_time_s")
        ch, fl = r.get("children"), r.get("total_flips")
        out.append(dict(
            t, cls=cls, note=note, status=r.get("status"), stop_reason=r.get("stop_reason"),
            wall_time_s=wall, cpu_time_s=cpu,
            cpu_wall_ratio=(round(cpu / wall, 3) if wall and cpu is not None else None),
            time_to_target_s=r.get("time_to_target_s"),
            success_ttt_s=(r.get("time_to_target_s") if cls == "success" else None),
            overshoot_s=(round(wall - float(t["budget_s"]), 3) if cls == "budget_exhausted" and wall else None),
            best_cost=r.get("best_cost"), abs_gap=r.get("abs_gap"),
            ea_generations=r.get("ea_generations"), children=ch, total_flips=fl,
            mean_flips_per_call=(round(fl / ch, 1) if ch and fl is not None else None),
            mean_wall_per_child_s=(round(wall / ch, 4) if ch and wall and cls != "watchdog" else None),
            host=r.get("host"), python=r.get("python"),
        ))
    return out


def id_ranges(ids: List[int]) -> str:
    ids = sorted(ids)
    parts, i = [], 0
    while i < len(ids):
        j = i
        while j + 1 < len(ids) and ids[j + 1] == ids[j] + 1:
            j += 1
        parts.append(str(ids[i]) if i == j else f"{ids[i]}-{ids[j]}")
        i = j + 1
    return ",".join(parts)


def med_ttt(vals: List[Optional[float]]) -> str:
    """Median TTT with non-successes counted as > budget."""
    xs = sorted(math.inf if v is None else float(v) for v in vals)
    if not xs:
        return ""
    n = len(xs)
    m = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
    return f"{m:.1f}" if math.isfinite(m) else f">{BUDGET_S:g}"


def summarise(rows: List[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    g = defaultdict(list)
    for r in rows:
        g[tuple(r[k] for k in keys)].append(r)
    out = []
    for k, rs in sorted(g.items(), key=lambda kv: tuple(str(x) for x in kv[0])):
        c = Counter(r["cls"] for r in rs)
        def med(field):
            xs = [float(r[field]) for r in rs if r[field] is not None]
            return round(statistics.median(xs), 3) if xs else None
        out.append(dict(
            zip(keys, k), tasks=len(rs), successes=c["success"],
            success_rate=round(c["success"] / len(rs), 3),
            median_ttt_s=med_ttt([r["success_ttt_s"] for r in rs]),
            **{f"n_{x}": c[x] for x in CLASSES},
            median_generations=med("ea_generations"), median_children=med("children"),
            median_mean_flips_per_call=med("mean_flips_per_call"),
            median_wall_per_child_s=med("mean_wall_per_child_s"),
            max_overshoot_s=max((r["overshoot_s"] for r in rs if r["overshoot_s"] is not None), default=None),
            min_cpu_wall_ratio=min((r["cpu_wall_ratio"] for r in rs if r["cpu_wall_ratio"] is not None), default=None),
        ))
    return out


def write_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def paired(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    arms = sorted({r["arm"] for r in rows})
    g = defaultdict(dict)
    for r in rows:
        g[(r["pop_idx"], r["instance"], r["analysis_group"], r["solver_seed"])][r["arm"]] = r
    out = []
    for (pi, inst, grp, seed), by in sorted(g.items(), key=lambda kv: (int(kv[0][0]), int(kv[0][3]))):
        row = {"pop_idx": pi, "instance": inst, "analysis_group": grp, "solver_seed": seed}
        for a in arms:
            r = by.get(a)
            row[f"{a}"] = "" if r is None else (
                f"{float(r['success_ttt_s']):.1f}" if r["cls"] == "success" else r["cls"])
        out.append(row)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="M2 shard state, resume and aggregation")
    ap.add_argument("cmd", choices=("pending", "aggregate"))
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--outdir", required=True, help="shard directory (OUTDIR of the array)")
    ap.add_argument("--out-dir", help="aggregate: where the CSVs go")
    ap.add_argument("--summary", action="store_true", help="pending: class counts to stderr")
    a = ap.parse_args(argv)

    rows = evaluate(a.manifest, a.outdir)
    counts = Counter(r["cls"] for r in rows)
    count_line = "  ".join(f"{c}={counts[c]}" for c in CLASSES if counts[c])

    if a.cmd == "pending":
        ids = [int(r["task_id"]) for r in rows if r["cls"] in PENDING_CLASSES]
        if a.summary:
            print(f"{len(rows)} tasks: {count_line}; pending (infra/invalid only) = {len(ids)}",
                  file=sys.stderr)
        print(id_ranges(ids))
        return 0

    od = a.out_dir or os.path.join(os.path.dirname(a.outdir.rstrip("/")), "agg")
    os.makedirs(od, exist_ok=True)
    write_csv(os.path.join(od, "tasks.csv"), rows)
    by_inst = summarise(rows, ["config_id", "analysis_group", "pop_idx", "instance", "m"])
    by_grp = summarise(rows, ["config_id", "analysis_group"])
    by_arm = summarise(rows, ["config_id"])
    write_csv(os.path.join(od, "by_instance_config.csv"), by_inst)
    write_csv(os.path.join(od, "by_group_config.csv"), by_grp)
    write_csv(os.path.join(od, "by_config.csv"), by_arm)
    write_csv(os.path.join(od, "paired_by_instance_seed.csv"), paired(rows))

    print(f"{len(rows)} tasks: {count_line}")
    print(f"success = status ok & stop_reason target & time_to_target_s <= {BUDGET_S:g}")
    print(f"\n{'config_id':34s} {'group':10s} tasks succ  med_ttt  bud_exh watchdog late infra")
    for s in by_grp + [dict(r, analysis_group="ALL") for r in by_arm]:
        infra = s["n_infra_missing"] + s["n_infra_error"] + s["n_invalid_submission"]
        print(f"{s['config_id']:34s} {s['analysis_group']:10s} {s['tasks']:5d} {s['successes']:4d} "
              f"{s['median_ttt_s']:>8s} {s['n_budget_exhausted']:8d} {s['n_watchdog']:8d} "
              f"{s['n_target_after_budget']:4d} {infra:5d}")
    low = [r for r in rows if r["cpu_wall_ratio"] is not None and r["cpu_wall_ratio"] < 0.9]
    if low:
        print(f"\nWARNING: {len(low)} task(s) with cpu/wall < 0.9 (node contention?): "
              + ", ".join(r["job_id"] for r in low[:10]))
    print(f"\nwrote {od}/{{tasks,by_instance_config,by_group_config,by_config,paired_by_instance_seed}}.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
