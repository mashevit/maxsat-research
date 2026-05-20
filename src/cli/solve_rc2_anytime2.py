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

Surviving SIGKILL
-----------------
When ``--progress-file PATH`` is given, a background thread writes the
running lower bound to PATH every 2 seconds while RC2 is solving. If
this process is SIGKILL'd by a parent (e.g. because Python's SIGALRM was
swallowed by RC2's underlying C SAT solver and a subprocess.run timeout
escalated to a hard kill), the most recent lower bound is still on disk
for the parent to recover. Without ``--progress-file`` this behavior is
disabled.

Example
-------
    python -m src.cli.solve_rc2_anytime --path data/toy/mini.wcnf \\
        --timeout-s 1.0 --json

    python -m src.cli.solve_rc2_anytime --path big.wcnf \\
        --timeout-s 600 --progress-file /tmp/rc2_lb.txt --json
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional, List

try:
    from pysat.examples.rc2 import RC2
    from pysat.formula import WCNF
except ImportError:  # pragma: no cover
    print(
        "[solve_rc2_anytime] ERROR: could not import PySAT.\n"
        "Please install it with:\n"
        "    pip install python-sat[pblib,aiger]\n",
        file=sys.stderr,
    )
    raise

from src.cli.run_opt_rc2 import load_as_wcnf  # noqa: E402


PROGRESS_INTERVAL_S = 2.0  # how often the background thread dumps lb to disk


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


def _progress_writer(rc2, path: str, stop_event: threading.Event,
                     interval: float = PROGRESS_INTERVAL_S) -> None:
    """Background thread: dump RC2's running lower bound to ``path`` every
    ``interval`` seconds. Atomic via write-temp-then-rename so a SIGKILL'd
    parent read never sees a partial value.

    Best-effort: any exception inside the loop is swallowed. We never want
    the progress thread to interfere with the main solve.
    """
    while not stop_event.wait(interval):
        try:
            lb = _read_lower_bound(rc2)
        except Exception:
            continue
        if lb is None:
            continue
        try:
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(str(lb))
            os.replace(tmp, path)
        except Exception:
            pass


def solve_rc2_with_timeout(
    path: str,
    timeout_s: float,
    solver: str = "g3",
    progress_file: Optional[str] = None,
) -> AnytimeRC2Result:
    """Run RC2 on ``path`` with a wall-clock budget of ``timeout_s`` seconds.

    If ``progress_file`` is supplied, a daemon thread writes RC2's running
    lower bound to that path every ``PROGRESS_INTERVAL_S`` seconds. This
    is the only way to recover a lower bound when the process is SIGKILL'd
    by an external parent before the SIGALRM cleanup path runs.
    """
    abs_path = os.path.abspath(path)

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

    try:
        rc2 = RC2(wcnf, solver=solver)
    except Exception as e:
        out.status = "error"
        out.error = f"{type(e).__name__}: {e}"
        out.elapsed_s = time.time() - start
        return out

    # Start the progress writer thread BEFORE arming the alarm, so even a
    # SIGALRM that fires very early in compute() has at least one tick of
    # lb dumped to disk first.
    progress_stop: Optional[threading.Event] = None
    progress_thread: Optional[threading.Thread] = None
    if progress_file:
        progress_stop = threading.Event()
        progress_thread = threading.Thread(
            target=_progress_writer,
            args=(rc2, progress_file, progress_stop),
            daemon=True,
        )
        progress_thread.start()

    def _alarm_handler(signum, frame):  # noqa: ARG001
        raise _Timeout()

    prev_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, max(float(timeout_s), 1e-6))

    try:
        model = rc2.compute()
        if model is None:
            out.status = "unsat"
            out.cost = None
            out.model = None
            out.cost_lower_bound = _read_lower_bound(rc2)
        else:
            opt = _read_lower_bound(rc2)
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
        out.cost_lower_bound = _read_lower_bound(rc2)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev_handler)
        if progress_stop is not None:
            progress_stop.set()
        if progress_thread is not None:
            progress_thread.join(timeout=1.0)
        try:
            rc2.delete()
        except Exception:
            pass
        out.elapsed_s = time.time() - start

    return out


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
    parser.add_argument("--path", required=True,
                        help="Path to the CNF/WCNF instance (DIMACS format).")
    parser.add_argument("--timeout-s", type=float, required=True,
                        help="Wall-clock budget in seconds (must be > 0).")
    parser.add_argument("--solver", default="g3",
                        help="Underlying SAT solver name for RC2 (default: %(default)s).")
    parser.add_argument("--progress-file", metavar="PATH",
                        help="Periodically dump the running lower bound to "
                             "this path. Survives SIGKILL.")
    parser.add_argument("--json", action="store_true",
                        help="Emit a JSON line to stdout instead of human-readable output.")
    parser.add_argument("--out-json", metavar="PATH",
                        help="Optional path to also save the JSON record.")
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
        progress_file=args.progress_file,
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
