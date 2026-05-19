# src/cli/solve_rc2_anytime.py
"""Anytime PySAT RC2 MaxSAT solver wrapper.

This is the *anytime* variant of ``src.cli.run_opt_rc2``. It imposes a
wall-clock budget on RC2 via ``signal.setitimer(signal.ITIMER_REAL, ...)``
and reports whatever information is available when the alarm fires.

Result semantics
----------------
* ``status == "optimal"``  — RC2 finished within the budget. ``cost`` and
  ``model`` are populated; ``cost_lower_bound == cost``.
* ``status == "timeout"``  — the alarm fired before RC2 returned. There
  is no feasible model to report. ``cost_lower_bound`` is the running
  lower bound accumulated by RC2 (the sum of weights of the unsatisfiable
  cores extracted so far). Any optimal cost must be at least
  ``cost_lower_bound``; it is *not* the cost of a feasible assignment.
* ``status == "unsat"``    — the hard part is infeasible.
* ``status == "error"``    — RC2 raised an unexpected exception.

Example
-------
    python -m src.cli.solve_rc2_anytime --path data/toy/mini.wcnf \\
        --timeout-s 1.0 --json
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from dataclasses import dataclass, asdict, field
from typing import Optional, List

# --- Try to import PySAT RC2 and WCNF ---------------------------------------

try:
    from pysat.examples.rc2 import RC2
    from pysat.formula import WCNF
except ImportError:  # pragma: no cover - import error is handled at runtime
    print(
        "[solve_rc2_anytime] ERROR: could not import PySAT.\n"
        "Please install it with:\n"
        "    pip install python-sat[pblib,aiger]\n",
        file=sys.stderr,
    )
    raise

# Reuse the existing CNF/WCNF loading path so this CLI's parsing is in lock-step
# with run_opt_rc2.py (CNFs are converted to all-soft weight-1; WCNFs are loaded
# as-is via PySAT).
from src.cli.run_opt_rc2 import load_as_wcnf  # noqa: E402


# --- Data structure ---------------------------------------------------------


@dataclass
class AnytimeRC2Result:
    """One record per invocation of :func:`solve_rc2_with_timeout`."""

    path: str
    status: str                              # "optimal" | "timeout" | "unsat" | "error"
    cost: Optional[int]
    cost_lower_bound: Optional[int]
    model: Optional[List[int]]
    elapsed_s: float
    timeout_s: float
    solver: str
    n_vars: int
    n_clauses: int
    n_hard: int
    n_soft: int
    error: Optional[str] = None


# --- Internal helpers -------------------------------------------------------


class _Timeout(Exception):
    """Raised from the SIGALRM handler to interrupt rc2.compute()."""


def _read_lower_bound(rc2) -> Optional[int]:
    """Return the running lower bound from RC2, regardless of PySAT version.

    Different PySAT releases have exposed the accumulated core weight under
    different attribute names. Probe the common ones; if none exist, warn to
    stderr and return ``None``.
    """
    for attr in ("cost", "cost_so_far"):
        v = getattr(rc2, attr, None)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
    avail = [a for a in dir(rc2) if "cost" in a.lower() or "bound" in a.lower()]
    print(
        "[solve_rc2_anytime] WARNING: no running lower-bound attribute found "
        f"on RC2; available cost/bound-like attrs: {avail}",
        file=sys.stderr,
    )
    return None


# --- Core API ---------------------------------------------------------------


def solve_rc2_with_timeout(
    path: str,
    timeout_s: float,
    solver: str = "g3",
) -> AnytimeRC2Result:
    """Run RC2 on ``path`` with a wall-clock budget of ``timeout_s`` seconds.

    Always restores the previous SIGALRM handler and disables the interval
    timer. Always calls ``rc2.delete()`` when an RC2 instance was created.
    """
    abs_path = os.path.abspath(path)

    # Default skeleton; fields are filled in as we make progress.
    out = AnytimeRC2Result(
        path=abs_path,
        status="error",
        cost=None,
        cost_lower_bound=None,
        model=None,
        elapsed_s=0.0,
        timeout_s=float(timeout_s),
        solver=solver,
        n_vars=0,
        n_clauses=0,
        n_hard=0,
        n_soft=0,
        error=None,
    )

    start = time.time()

    # Load the formula before arming the timer so I/O / parse errors are
    # cleanly attributed to status="error" without ever installing an alarm.
    try:
        wcnf = load_as_wcnf(abs_path)
    except Exception as e:
        out.status = "error"
        out.error = f"{type(e).__name__}: {e}"
        out.elapsed_s = time.time() - start
        return out

    out.n_vars = int(wcnf.nv)
    out.n_hard = len(wcnf.hard)
    out.n_soft = len(wcnf.soft)
    out.n_clauses = out.n_hard + out.n_soft

    # Construct RC2 *before* arming the alarm. Otherwise a SIGALRM that fires
    # inside RC2.__init__ leaves a partially-constructed object whose __del__
    # raises during GC ('RC2 object has no attribute oracle').
    try:
        rc2 = RC2(wcnf, solver=solver)
    except Exception as e:
        out.status = "error"
        out.error = f"{type(e).__name__}: {e}"
        out.elapsed_s = time.time() - start
        return out

    def _alarm_handler(signum, frame):  # noqa: ARG001
        raise _Timeout()

    prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    # Use setitimer for sub-second resolution.
    signal.setitimer(signal.ITIMER_REAL, max(float(timeout_s), 1e-6))

    try:
        model = rc2.compute()
        if model is None:
            out.status = "unsat"
            out.cost = None
            out.model = None
            out.cost_lower_bound = _read_lower_bound(rc2)
        else:
            opt = _read_lower_bound(rc2)  # == final cost on a clean return
            out.status = "optimal"
            out.cost = opt
            out.cost_lower_bound = opt
            out.model = list(model)
    except _Timeout:
        out.status = "timeout"
        out.cost = None
        out.model = None
        out.cost_lower_bound = _read_lower_bound(rc2)
    except Exception as e:
        out.status = "error"
        out.error = f"{type(e).__name__}: {e}"
        # Still try to surface a lower bound if RC2 had made progress.
        out.cost_lower_bound = _read_lower_bound(rc2)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev_handler)
        try:
            rc2.delete()
        except Exception:
            pass
        out.elapsed_s = time.time() - start

    return out


# --- I/O helpers ------------------------------------------------------------


def _print_human_readable(res: AnytimeRC2Result) -> None:
    print(f"Path:                {res.path}")
    print(f"Status:              {res.status}")
    print(f"Solver:              {res.solver}")
    print(f"Timeout (s):         {res.timeout_s}")
    print(f"Elapsed (s):         {res.elapsed_s:.4f}")
    print(f"#vars:               {res.n_vars}")
    print(f"#clauses:            {res.n_clauses}  (hard={res.n_hard}, soft={res.n_soft})")
    if res.cost is not None:
        print(f"Cost:                {res.cost}")
    else:
        print("Cost:                -")
    if res.cost_lower_bound is not None:
        print(f"Cost lower bound:    {res.cost_lower_bound}")
    else:
        print("Cost lower bound:    -")
    if res.model is not None:
        print(f"Model:               <{len(res.model)} literals>")
    if res.error:
        print(f"Error:               {res.error}")


# --- CLI --------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Anytime RC2 MaxSAT solver. Runs PySAT's RC2 under a wall-clock\n"
            "budget and reports either the optimum or the lower bound\n"
            "accumulated when the timeout fires.\n\n"
            "Example:\n"
            "  python -m src.cli.solve_rc2_anytime --path data/toy/mini.wcnf "
            "--timeout-s 1.0 --json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        required=True,
        help="Path to the CNF/WCNF instance (DIMACS format).",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        required=True,
        help="Wall-clock budget in seconds (must be > 0).",
    )
    parser.add_argument(
        "--solver",
        default="g3",
        help="Underlying SAT solver name for RC2 (default: %(default)s).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit a JSON line to stdout instead of human-readable output.",
    )
    parser.add_argument(
        "--out-json",
        metavar="PATH",
        help="Optional path to also save the JSON record (one object per file).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    if args.timeout_s <= 0:
        print("[solve_rc2_anytime] ERROR: --timeout-s must be > 0", file=sys.stderr)
        return 2

    res = solve_rc2_with_timeout(
        args.path,
        timeout_s=args.timeout_s,
        solver=args.solver,
    )

    payload = asdict(res)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        _print_human_readable(res)

    if args.out_json:
        with open(args.out_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
