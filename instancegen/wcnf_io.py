"""DIMACS wcnf writer with an explicitly required dialect.

Plan: docs/INSTANCEGEN_PLAN.md §9 (step 2 of §13).

Two dialects (D1 = option (a): implement both, calibrate and commit with "old"):

  dialect="old"  -- `p wcnf <n_vars> <n_clauses> <top>`; hard clauses written
                    with weight `top`. Readable by maxsat_new.cnf.parse_dimacs.
  dialect="new"  -- no `p` line; hard clauses prefixed `h`. Readable by pysat
                    and MSE tooling, and NOT by this repo's own parser (§9.1) --
                    that mismatch is pinned as an asserted fact by §12 test 3.

Both dialects emit soft clauses first, then hard, matching pysat's
WCNF.to_fp ordering so output is diff-comparable against it.

No comment lines and no timestamps are written: the file must be byte-identical
across runs for the same (params, seed) (§12 test 1), which is what D6 relies on
to keep the corpus out of git. `created_utc`/`git_sha` go in the manifest only
(§10.3).
"""
from __future__ import annotations

import os
from typing import Tuple

from instancegen.generate import Clause, Instance

DIALECTS = ("old", "new")


def emit_order(inst: Instance) -> Tuple[Clause, ...]:
    """Clauses in write order: softs first, then hards (pysat convention, §9).

    Exported so the round-trip test compares against the same ordering the
    writer uses without duplicating the rule.
    """
    return inst.soft_clauses + inst.hard_clauses


def _clause_body(lits: Tuple[int, ...]) -> str:
    return " ".join(str(l) for l in lits) + " 0"


def format_wcnf(inst: Instance, *, dialect: str) -> str:
    """Render an Instance as wcnf text. `dialect` is keyword-only, no default."""
    if dialect not in DIALECTS:
        raise ValueError(
            f"unknown dialect {dialect!r}; expected one of {DIALECTS}"
        )

    clauses = emit_order(inst)
    lines = []

    if dialect == "old":
        lines.append(f"p wcnf {inst.n_vars} {len(clauses)} {inst.top}")
        for cl in clauses:
            # Hard clauses carry weight == top already (generate.py), so both
            # branches are the same line shape; written explicitly so the
            # hard-weight convention is visible here too.
            w = inst.top if cl.is_hard else cl.weight
            lines.append(f"{w} {_clause_body(cl.lits)}")
    else:
        for cl in clauses:
            prefix = "h" if cl.is_hard else str(cl.weight)
            lines.append(f"{prefix} {_clause_body(cl.lits)}")

    return "".join(line + "\n" for line in lines)


def write_wcnf(inst: Instance, path: str, *, dialect: str) -> None:
    """Write `inst` to `path`. `dialect` is required -- omitting it is TypeError.

    newline="\\n" is explicit so a Windows checkout produces the same bytes as a
    Linux one; byte-identity is the point (§12 test 1).
    """
    text = format_wcnf(inst, dialect=dialect)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
