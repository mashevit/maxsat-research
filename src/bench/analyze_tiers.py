#!/usr/bin/env python3
"""
analyze_tiers.py
================
Concatenate the per-instance MaxSAT hardness-profile JSONL files produced by
the parallel SLURM array job, and compute cross-instance statistics.

Each input record (one JSON object, observed schema)::

    {
      "instance": "data/raw/mse_2024/mse23-uw-small/Foo-bar_1.wcnf",
      "size_mb": 0.7642,
      "profile": {
        "cap_s": 600.0,            # time budget given to RC2
        "solver": "rc2",
        "status": "subprocess_killed",   # or optimal/solved/error/...
        "solve_s": 660.105,        # wall time actually spent
        "final_cost": null,        # optimum/best cost if converged
        "cost_lower_bound": 15,    # best LB recovered from progress file
        "completed": false,        # did RC2 converge within budget?
        "error": "subprocess_killed_at_cap+60.0s; recovered_lb_from_progress_file"
      },
      "ratio": null,               # final_cost / cap-related ref, when solved
      "lb_ratio": 0.7143,          # lower-bound progress ratio
      "tier": "T3",                # T1 | T2a | T2b | T3
      "tier_reason": "..."
    }

Outputs (written next to --out-dir):
  - all_results.jsonl   concatenated, one object per line
  - all_results.csv     flattened tidy table (one row per instance)
  - tier_summary.csv    per-tier aggregates
  - bench_summary.csv   per-benchmark-dir x tier counts
  - a human-readable report printed to stdout

Usage:
  python analyze_tiers.py --in-dir ./results            # all *.jsonl in dir
  python analyze_tiers.py --in-dir ./results --glob '*.jsonl' --out-dir ./analysis
  python analyze_tiers.py file1.jsonl file2.jsonl ...    # explicit files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    sys.exit(
        "pandas is required: `pip install pandas` "
        "(or `conda install pandas` in your gsm8k_lora env)."
    )

# Canonical tier ordering; any unseen tier is appended after these.
TIER_ORDER = ["T1", "T2a", "T2b", "T3"]


# --------------------------------------------------------------------------- #
# Loading                                                                     #
# --------------------------------------------------------------------------- #
def iter_jsonl_files(in_dir: Path | None, glob: str, explicit: list[str]):
    """Yield Path objects for every JSONL file to read."""
    if explicit:
        for f in explicit:
            yield Path(f)
    if in_dir is not None:
        yield from sorted(in_dir.glob(glob))


def load_records(files) -> list[dict]:
    """Read all JSON objects from the given files (1+ objects per file)."""
    records: list[dict] = []
    n_files = 0
    for fp in files:
        n_files += 1
        if not fp.exists():
            print(f"  ! missing file, skipping: {fp}", file=sys.stderr)
            continue
        with fp.open("r", encoding="utf-8") as fh:
            for ln, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"  ! bad JSON in {fp}:{ln}: {e}", file=sys.stderr)
                    continue
                obj["_source_file"] = fp.name
                records.append(obj)
    if n_files == 0:
        sys.exit("No input files found. Check --in-dir / --glob or pass files explicitly.")
    print(f"Read {len(records)} records from {n_files} file(s).")
    return records


# --------------------------------------------------------------------------- #
# Flatten + derive                                                            #
# --------------------------------------------------------------------------- #
def build_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.json_normalize(records, sep=".")

    # Normalise expected columns even if some are entirely absent.
    for col in [
        "instance", "size_mb", "ratio", "lb_ratio", "tier", "tier_reason",
        "profile.cap_s", "profile.solver", "profile.status", "profile.solve_s",
        "profile.final_cost", "profile.cost_lower_bound", "profile.completed",
        "profile.error",
    ]:
        if col not in df.columns:
            df[col] = pd.NA

    # Derive grouping keys from the instance path.
    paths = df["instance"].fillna("").map(Path)
    df["bench_dir"] = paths.map(lambda p: p.parent.name if p.name else "")
    df["stem"] = paths.map(lambda p: p.stem)
    # family = token before the first '-' in the filename stem
    df["family"] = df["stem"].map(lambda s: s.split("-", 1)[0] if isinstance(s, str) else "")

    # Did RC2 spend (almost) the whole budget? Useful T3 sanity signal.
    df["over_cap"] = df["profile.solve_s"] >= df["profile.cap_s"]

    # Tidy column order.
    front = [
        "instance", "family", "bench_dir", "size_mb", "tier",
        "profile.completed", "profile.status", "profile.solve_s", "profile.cap_s",
        "over_cap", "profile.final_cost", "profile.cost_lower_bound",
        "ratio", "lb_ratio", "profile.solver", "profile.error", "tier_reason",
        "_source_file",
    ]
    cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
    return df[cols]


def tier_sort_key(tier: str):
    try:
        return (0, TIER_ORDER.index(tier))
    except ValueError:
        return (1, str(tier))


# --------------------------------------------------------------------------- #
# Summaries                                                                    #
# --------------------------------------------------------------------------- #
def numeric_stats(s: pd.Series) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "n": int(s.size),
        "min": round(float(s.min()), 4),
        "median": round(float(s.median()), 4),
        "mean": round(float(s.mean()), 4),
        "max": round(float(s.max()), 4),
    }


def tier_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    tiers = sorted(df["tier"].dropna().unique(), key=tier_sort_key)
    total = len(df)
    for t in tiers:
        sub = df[df["tier"] == t]
        completed = pd.to_numeric(sub["profile.completed"], errors="coerce")
        sz = numeric_stats(sub["size_mb"])
        tm = numeric_stats(sub["profile.solve_s"])
        lb = numeric_stats(sub["lb_ratio"])
        rows.append({
            "tier": t,
            "count": len(sub),
            "pct": round(100 * len(sub) / total, 1) if total else 0.0,
            "completed_rate": round(float(completed.fillna(0).mean()), 3),
            "size_mb_median": sz["median"], "size_mb_max": sz["max"],
            "solve_s_median": tm["median"], "solve_s_max": tm["max"],
            "lb_ratio_n": lb["n"], "lb_ratio_median": lb["median"],
        })
    return pd.DataFrame(rows)


def bench_tier_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Counts of each tier per benchmark directory (a quick coverage map)."""
    ct = pd.crosstab(df["bench_dir"], df["tier"])
    # reorder tier columns
    ordered = sorted(ct.columns, key=tier_sort_key)
    ct = ct[ordered]
    ct["total"] = ct.sum(axis=1)
    return ct.sort_values("total", ascending=False)


# --------------------------------------------------------------------------- #
# Report                                                                       #
# --------------------------------------------------------------------------- #
def print_report(df: pd.DataFrame, tsum: pd.DataFrame, bench: pd.DataFrame) -> None:
    line = "=" * 70
    print(f"\n{line}\nMaxSAT HARDNESS PROFILE — CROSS-INSTANCE SUMMARY\n{line}")
    print(f"Instances          : {len(df)}")
    print(f"Benchmark dirs     : {df['bench_dir'].nunique()}")
    print(f"Problem families   : {df['family'].nunique()}")
    print(f"Solvers seen       : {', '.join(sorted(df['profile.solver'].dropna().unique()))}")
    caps = pd.to_numeric(df['profile.cap_s'], errors='coerce').dropna().unique()
    print(f"Time budget(s)     : {', '.join(str(int(c)) for c in sorted(caps))} s")

    completed = pd.to_numeric(df["profile.completed"], errors="coerce").fillna(0)
    print(f"Converged (RC2)    : {int(completed.sum())} / {len(df)} "
          f"({100*completed.mean():.1f}%)")

    print(f"\n--- Tier distribution -------------------------------------------------")
    print(tsum.to_string(index=False))

    print(f"\n--- Status breakdown --------------------------------------------------")
    sc = df["profile.status"].value_counts(dropna=False)
    for status, n in sc.items():
        print(f"  {str(status):<28} {n:>4}  ({100*n/len(df):.1f}%)")

    print(f"\n--- lb_ratio where present (T3 progress) ------------------------------")
    for t in sorted(df["tier"].dropna().unique(), key=tier_sort_key):
        st = numeric_stats(df[df["tier"] == t]["lb_ratio"])
        if st["n"]:
            print(f"  {t:<5} n={st['n']:<4} median={st['median']}  "
                  f"min={st['min']}  max={st['max']}")

    print(f"\n--- Tier x benchmark dir (counts) -------------------------------------")
    print(bench.to_string())

    # Size vs hardness: median size by tier (rough monotonicity check).
    print(f"\n--- Median size_mb by tier (is bigger = harder?) ----------------------")
    msize = (df.assign(_sz=pd.to_numeric(df["size_mb"], errors="coerce"))
               .groupby("tier")["_sz"].median()
               .reindex(sorted(df["tier"].dropna().unique(), key=tier_sort_key)))
    for t, v in msize.items():
        print(f"  {t:<5} {v:.4f} MB" if pd.notna(v) else f"  {t:<5} n/a")

    # Flag any error rows for inspection.
    errs = df[df["profile.error"].notna() & (df["profile.error"].astype(str) != "")]
    print(f"\n--- Records with a non-empty error field: {len(errs)} ------------------")
    if not errs.empty:
        for _, r in errs.head(15).iterrows():
            print(f"  [{r['tier']}] {Path(str(r['instance'])).name}: {r['profile.error']}")
        if len(errs) > 15:
            print(f"  ... and {len(errs) - 15} more (see all_results.csv)")
    print(line)


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="explicit JSONL files (optional)")
    ap.add_argument("--in-dir", type=Path, default=None,
                    help="directory containing per-instance *.jsonl files")
    ap.add_argument("--glob", default="*.jsonl", help="glob within --in-dir")
    ap.add_argument("--out-dir", type=Path, default=Path("."),
                    help="where to write concatenated + summary files")
    args = ap.parse_args()

    if args.in_dir is None and not args.files:
        ap.error("provide --in-dir and/or explicit JSONL files")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(iter_jsonl_files(args.in_dir, args.glob, args.files))
    df = build_frame(records)

    # --- write concatenated + flat outputs ---
    cat_path = args.out_dir / "all_results.jsonl"
    with cat_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            rec.pop("_source_file", None)
            fh.write(json.dumps(rec) + "\n")

    csv_path = args.out_dir / "all_results.csv"
    df.to_csv(csv_path, index=False)

    tsum = tier_summary(df)
    tsum.to_csv(args.out_dir / "tier_summary.csv", index=False)

    bench = bench_tier_matrix(df)
    bench.to_csv(args.out_dir / "bench_summary.csv")

    print_report(df, tsum, bench)

    print(f"\nWrote:\n  {cat_path}\n  {csv_path}\n"
          f"  {args.out_dir/'tier_summary.csv'}\n  {args.out_dir/'bench_summary.csv'}")


if __name__ == "__main__":
    main()
