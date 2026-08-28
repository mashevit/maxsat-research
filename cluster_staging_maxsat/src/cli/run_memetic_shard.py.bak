# src/cli/run_memetic_shard.py
"""
One (instance, config, seed, budget) memetic-EA run -> one JSONL record.

This is the memetic counterpart of `src/cli/profile_hardness.py`: one process
per SLURM array task, one shard file out, aggregated afterwards. It exists
instead of reusing `src/cli/run_experiment.py` because that CLI writes a CSV
keyed on the *basename* of the instance and records nothing about the solver
configuration, which makes a join against the RC2 tier tables ambiguous and
unauditable. Every provenance gap listed in `docs/RC2_STATUS.md` §6 is closed
here: sha256 of the instance, the resolved absolute path, the full effective
config plus its hash, the git sha, and the host.

Cost convention (docs/HARNESS_PLAN.md §5.1): `best_cost` is the **total weight
of UNSATISFIED soft clauses** — lower is better, and directly comparable with
`profile.final_cost` from the RC2 records. `hard_violations` is reported
separately and a record with `hard_violations > 0` is infeasible, so its
`best_cost` must not be compared against the oracle.

`--stop-at-oracle` (off by default) forwards `--oracle-cost` into the EA as a
target and stops the run the moment the incumbent reaches it, so `wall_time_s`
becomes a time-to-optimum measurement rather than "the budget was spent"
(docs/TIER2_MEMETIC_PLAN.md §6.6). It is opt-in because an oracle-terminated run
is a *benchmarking* mode, not a solver mode. `stop_reason` says which condition
ended the run.

NOTE: this file is intentionally AHEAD of the repo copy at `src/` -- see
`cluster_staging_maxsat/DIVERGENCE.md`.

Usage:
    python -m src.cli.run_memetic_shard \
        --instance data/unsat_uuf_diff/uuf250-03.cnf \
        --config configs/tier2/memetic_base.yaml \
        --config-id memetic_base \
        --seed 1 --budget-s 60 \
        --out results/tier2_memetic/tasks/t2m_0001.jsonl
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import signal
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

# --- Flexible imports so this runs as a module or as a script -----------------
try:
    from evo.memetic import run_memetic
    from sat.cnf import WCNF
except Exception:  # pragma: no cover - path fixup for `python src/cli/...`
    _here = os.path.abspath(__file__)
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(_here), "..")))
    from evo.memetic import run_memetic  # type: ignore
    from sat.cnf import WCNF  # type: ignore

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

SHARD_SCHEMA_VERSION = 1


# ---------- instance inspection ----------------------------------------------
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_format(path: str) -> str:
    """
    Classify a DIMACS file as 'cnf', 'wcnf_old' (has a `p wcnf` header) or
    'wcnf_new' (MSE 2022+: no `p` line, hard clauses prefixed `h`).

    All three are now read by `sat.cnf.WCNF.parse_dimacs` (staging copy, see
    DIVERGENCE.md), so this no longer gates anything — it is kept purely as
    provenance: the result lands in `instance_format`, which
    `src/bench/combine_tier2.py` carries into `summary.csv` as a column to
    stratify by. A file this returns 'unknown' for has no clauses at all and
    will fail in the parser, loudly, which is where that belongs.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("c") or line.startswith("%"):
                continue
            if line.startswith("p "):
                toks = line.split()
                return "wcnf_old" if len(toks) > 1 and toks[1].lower() == "wcnf" else "cnf"
            # First non-comment, non-header line: new-format WCNF.
            return "wcnf_new"
    return "unknown"


def instance_stats(wcnf: Any) -> Dict[str, int]:
    n_hard = sum(1 for cl in wcnf.clauses if cl.is_hard)
    soft_w = sum(int(cl.weight) for cl in wcnf.clauses if not cl.is_hard)
    return {
        "n_vars": int(wcnf.n_vars),
        "n_clauses": len(wcnf.clauses),
        "n_hard": n_hard,
        "n_soft": len(wcnf.clauses) - n_hard,
        "soft_total_weight": soft_w,
    }


def score_assignment(wcnf: Any, assign01: List[bool]) -> Tuple[int, int, int]:
    """
    (unsat_soft_weight, hard_violations, unsat_soft_count) for a 1-indexed
    boolean assignment.

    Recomputed from the assignment rather than trusted from run_memetic's
    `best_soft_weight`, so the number in the record is verifiable against the
    instance file alone.
    """
    unsat_w = 0
    hard_v = 0
    unsat_n = 0
    for cl in wcnf.clauses:
        sat = False
        for lit in cl.lits:
            v = abs(lit)
            if (lit > 0) == assign01[v]:
                sat = True
                break
        if sat:
            continue
        if cl.is_hard:
            hard_v += 1
        else:
            unsat_w += int(cl.weight)
            unsat_n += 1
    return unsat_w, hard_v, unsat_n


# ---------- config handling ---------------------------------------------------
def deep_set(d: Dict[str, Any], dotted_key: str, val: Any) -> None:
    keys = dotted_key.split(".")
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    cur[keys[-1]] = val


def parse_kv_override(s: str) -> Tuple[str, Any]:
    if "=" not in s:
        raise ValueError(f"Expected KEY=VALUE, got: {s}")
    k, v = s.split("=", 1)
    try:
        return k.strip(), json.loads(v.strip())
    except Exception:
        return k.strip(), v.strip()


def load_cfg(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if yaml is not None:
        try:
            return yaml.safe_load(text) or {}
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception as e:
        if yaml is None and path.endswith((".yaml", ".yml")):
            raise SystemExit(
                f"Cannot read {path}: PyYAML is not installed in this environment "
                f"(requirements.txt pins pyyaml>=6.0.1). Run `pip install pyyaml` "
                f"in the `maxsat` conda env before submitting the array.")
        raise SystemExit(f"Failed to parse config {path}: {e}")


def config_hash(cfg: Dict[str, Any]) -> str:
    canon = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


# ---------- provenance --------------------------------------------------------
def git_sha() -> Optional[str]:
    """Env var first: the staging tree rsynced to the cluster is not a git repo."""
    env = os.environ.get("MAXSAT_GIT_SHA")
    if env:
        return env.strip()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def slurm_env() -> Dict[str, Optional[str]]:
    return {k.lower(): os.environ.get(k) for k in (
        "SLURM_JOB_ID", "SLURM_ARRAY_JOB_ID", "SLURM_ARRAY_TASK_ID",
        "SLURM_JOB_PARTITION", "SLURM_CPUS_PER_TASK", "SLURM_MEM_PER_NODE",
    )}


class _Timeout(Exception):
    pass


def _on_alarm(signum, frame):  # pragma: no cover - signal path
    raise _Timeout()


# ---------- main --------------------------------------------------------------
def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        prog="src.cli.run_memetic_shard",
        description="Run the memetic EA once and emit a single provenance-complete JSONL record.",
    )
    p.add_argument("--instance", required=True, help="Path to a .cnf/.wcnf file")
    p.add_argument("--config", help="YAML/JSON solver config (configs/tier2/*.yaml)")
    p.add_argument("--config-id", help="Label stored in the record (default: config file stem)")
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--budget-s", type=float, required=True,
                   help="Wall-clock budget, injected as top-level time_limit_s")
    p.add_argument("--grace-s", type=float, default=60.0,
                   help="SIGALRM watchdog fires at budget+grace (default: 60)")
    p.add_argument("--out", required=True, help="Output .jsonl shard (one record)")
    p.add_argument("--job-id", default=None, help="Manifest job id, echoed into the record")
    p.add_argument("--oracle-cost", type=int, default=None,
                   help="RC2 optimum for this instance; enables gap fields in the record")
    p.add_argument("--stop-at-oracle", action="store_true",
                   help="Stop the EA the moment it reaches --oracle-cost, turning "
                        "wall_time_s into a time-to-optimum measurement. Opt-in: "
                        "an oracle-terminated run is a BENCHMARKING mode, not a "
                        "solver mode. Requires --oracle-cost.")
    p.add_argument("--tier", default=None, help="RC2 tier label, echoed into the record")
    p.add_argument("--rc2-run", default=None, help="RC2 run dir the oracle came from")
    p.add_argument("--save-assignment", action="store_true",
                   help="Store the full best assignment bit-string (off by default)")
    p.add_argument("--override", "-D", action="append", default=[],
                   help="Config override, e.g. -D ea.pop_size=80")
    args = p.parse_args(argv)

    if args.stop_at_oracle and args.oracle_cost is None:
        print("FATAL: --stop-at-oracle requires --oracle-cost -- there is no "
              "target to stop at without it. Pass the RC2 optimum for this "
              "instance (the oracle_cost column of the manifest), or drop "
              "--stop-at-oracle to run the full budget.", file=sys.stderr)
        return 2

    # `--oracle-cost` alone keeps doing only what it always did: fill the gap
    # fields in the record for the combine step. It becomes a stop condition
    # only when --stop-at-oracle is passed explicitly.
    target_cost: Optional[int] = int(args.oracle_cost) if args.stop_at_oracle else None

    cfg = load_cfg(args.config)
    for ov in args.override:
        k, v = parse_kv_override(ov)
        deep_set(cfg, k, v)
    cfg.setdefault("ea", {})
    cfg["ea"].setdefault("enabled", True)
    # The budget always wins over anything in the config file.
    deep_set(cfg, "time_limit_s", float(args.budget_s))

    config_id = args.config_id or (
        os.path.splitext(os.path.basename(args.config))[0] if args.config else "default"
    )

    inst = args.instance
    rec: Dict[str, Any] = {
        "schema_version": SHARD_SCHEMA_VERSION,
        "job_id": args.job_id,
        "instance": inst,
        "instance_abspath": os.path.abspath(inst),
        "instance_sha256": None,
        "instance_format": None,
        "size_mb": None,
        "n_vars": None, "n_clauses": None, "n_hard": None, "n_soft": None,
        "soft_total_weight": None,
        "solver": "memetic_ea",
        "config_id": config_id,
        "config": cfg,
        "config_hash": config_hash(cfg),
        "seed": args.seed,
        "budget_s": float(args.budget_s),
        "grace_s": float(args.grace_s),
        "wall_time_s": None,
        # Target-cost early stop (docs/TIER2_MEMETIC_PLAN.md §6.6).
        # `wall_time_s` keeps its meaning -- total loop wall time. It now equals
        # `time_to_target_s` on target-stopped runs and the budget otherwise;
        # `stop_reason` is what disambiguates, so downstream code never has to
        # infer which case it is looking at.
        "stop_reason": None,
        "time_to_target_s": None,
        "target_cost_used": target_cost,
        "stop_at_oracle": bool(args.stop_at_oracle),
        "best_cost": None,
        "hard_violations": None,
        "unsat_soft_clauses": None,
        "best_soft_weight_reported": None,
        "ea_generations": None,
        "children": None,
        "total_flips": None,
        "best_assignment_hash": None,
        "best_assignment_bits": None,
        "status": "error",
        "error": None,
        "oracle_cost": args.oracle_cost,
        "abs_gap": None,
        "rel_gap": None,
        "is_optimal": None,
        "rc2_tier": args.tier,
        "rc2_run": args.rc2_run,
        "git_sha": git_sha(),
        "python": platform.python_version(),
        "host": socket.gethostname(),
        "slurm": slurm_env(),
        "started_at": None,
        "finished_at": None,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)

    def emit() -> int:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        s = rec["status"]
        print(f"[shard] {rec['job_id']} {os.path.basename(inst)} cfg={config_id} "
              f"seed={args.seed} budget={args.budget_s:g}s -> status={s} "
              f"cost={rec['best_cost']} hv={rec['hard_violations']} "
              f"opt={rec['oracle_cost']} wall={rec['wall_time_s']} "
              f"stop={rec['stop_reason']} t_target={rec['time_to_target_s']}")
        return 0 if s == "ok" else 1

    if not os.path.isfile(inst):
        rec["status"] = "missing_instance"
        rec["error"] = f"no such file: {inst}"
        return emit()

    rec["size_mb"] = round(os.path.getsize(inst) / 1e6, 4)
    rec["instance_sha256"] = sha256_file(inst)
    rec["instance_format"] = detect_format(inst)

    try:
        wcnf = WCNF.parse_dimacs(inst)
    except Exception as e:
        rec["status"] = "parse_error"
        rec["error"] = f"{type(e).__name__}: {e}"
        return emit()

    rec.update(instance_stats(wcnf))

    rec["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, float(args.budget_s) + float(args.grace_s))
    t0 = time.time()
    try:
        res = run_memetic(wcnf, cfg, rng_seed=args.seed, target_cost=target_cost)
        rec["wall_time_s"] = round(time.time() - t0, 3)
        rec["status"] = "ok"
    except _Timeout:
        rec["wall_time_s"] = round(time.time() - t0, 3)
        rec["status"] = "timeout"
        rec["error"] = f"watchdog_fired_at_budget+{args.grace_s:g}s"
        return emit()
    except Exception as e:
        rec["wall_time_s"] = round(time.time() - t0, 3)
        rec["status"] = "error"
        rec["error"] = f"{type(e).__name__}: {e}"
        return emit()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.0)
        rec["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    meta = res.get("meta", {}) or {}
    bits = meta.get("assign_bits")
    if not bits:
        rec["status"] = "error"
        rec["error"] = "run_memetic returned no meta.assign_bits"
        return emit()

    assign01 = [False] + [c == "1" for c in bits]
    unsat_w, hard_v, unsat_n = score_assignment(wcnf, assign01)
    rec["best_cost"] = unsat_w
    rec["hard_violations"] = hard_v
    rec["unsat_soft_clauses"] = unsat_n
    rec["best_soft_weight_reported"] = float(res.get("best_soft_weight", 0.0))
    rec["stop_reason"] = res.get("stop_reason")
    ttt = res.get("time_to_target_s")
    rec["time_to_target_s"] = None if ttt is None else round(float(ttt), 3)
    rec["ea_generations"] = meta.get("ea_generations")
    rec["children"] = meta.get("children")
    rec["total_flips"] = int(res.get("total_flips", 0))
    rec["best_assignment_hash"] = "sha256-12:" + hashlib.sha256(bits.encode()).hexdigest()[:12]
    if args.save_assignment:
        rec["best_assignment_bits"] = bits

    if args.oracle_cost is not None and hard_v == 0:
        opt = int(args.oracle_cost)
        rec["abs_gap"] = unsat_w - opt
        rec["rel_gap"] = round((unsat_w - opt) / opt, 6) if opt > 0 else None
        rec["is_optimal"] = bool(unsat_w == opt)

    # Cost cross-check (docs/TIER2_MEMETIC_PLAN.md §6.3). `best_cost` is
    # re-derived from meta.assign_bits; the EA's own number lives in
    # `best_soft_weight_reported`. If the EA stopped because *its* incumbent
    # reached the target but the re-derived cost is worse than the target, the
    # two cost paths disagree about the same assignment -- a parse or unit bug.
    # Fail the record loudly so the combine step's integrity pass sees it
    # instead of averaging it in.
    if target_cost is not None and rec["stop_reason"] == "target" and unsat_w > target_cost:
        rec["status"] = "cost_mismatch"
        rec["error"] = (
            f"target stop fired but re-derived best_cost={unsat_w} > "
            f"target_cost={target_cost} (solver reported satisfied soft weight "
            f"{rec['best_soft_weight_reported']}, soft_total_weight "
            f"{rec['soft_total_weight']}); the two cost paths disagree")

    return emit()


if __name__ == "__main__":
    raise SystemExit(main())
