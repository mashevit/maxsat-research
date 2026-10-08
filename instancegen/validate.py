"""Check a written old-dialect wcnf file against the distinct-clause contract.

Works on the file text, not on generator objects, so it checks what a solver
will actually read. Used by `cli generate-distinct` after writing and by the
tests. Contract (docs/current/RESEARCH_NOTES_DISTINCT_CLAUSE_GENERATOR.md):
exactly m clauses, each of exactly k literals over k distinct variables in
1..n, no tautology, no two clauses equal up to literal order, every clause
soft with weight 1, header `p wcnf n m top` with top = 1 + total soft weight
(the generate.py convention; any weight >= top would read as hard).
"""
from __future__ import annotations

from typing import Dict, List


def check_distinct_wcnf(text: str, *, n: int, k: int, m: int) -> Dict[str, object]:
    """Return {"ok": bool, "problems": [...], counts...}. Never raises on bad
    content; counts cover every violation, messages keep the first 200."""
    problems: List[str] = []

    def bad(msg: str) -> None:
        if len(problems) < 200:
            problems.append(msg)

    lines = [l for l in text.split("\n") if l.strip() and not l.startswith("c")]
    if not lines or not lines[0].startswith("p wcnf"):
        return {"ok": False, "problems": ["missing 'p wcnf' header"]}
    hdr = lines[0].split()
    if len(hdr) != 5:
        bad(f"header has {len(hdr)} fields, expected 5: {lines[0]!r}")
        return {"ok": False, "problems": problems}
    h_n, h_m, h_top = int(hdr[2]), int(hdr[3]), int(hdr[4])
    if h_n != n:
        bad(f"header n={h_n}, expected {n}")
    if h_m != m:
        bad(f"header clause count={h_m}, expected {m}")

    body = lines[1:]
    if len(body) != m:
        bad(f"{len(body)} clause lines, expected {m}")
    seen: Dict[tuple, int] = {}
    n_dup = n_taut = n_len = n_range = n_repvar = n_weight = n_term = 0
    for i, line in enumerate(body, start=1):
        toks = [int(t) for t in line.split()]
        w, lits = toks[0], toks[1:]
        if not lits or lits[-1] != 0:
            n_term += 1
            bad(f"clause {i}: not 0-terminated")
            continue
        lits = lits[:-1]
        if w != 1:
            n_weight += 1
            bad(f"clause {i}: weight {w} != 1 (hard or reweighted)")
        if len(lits) != k:
            n_len += 1
            bad(f"clause {i}: {len(lits)} literals, expected {k}")
        if any(l == 0 or abs(l) > n for l in lits):
            n_range += 1
            bad(f"clause {i}: variable out of 1..{n}: {lits}")
        vars_ = [abs(l) for l in lits]
        if len(set(vars_)) != len(vars_):
            n_repvar += 1
            bad(f"clause {i}: repeated variable {lits}")
        if any(-l in lits for l in lits):
            n_taut += 1
            bad(f"clause {i}: tautology {lits}")
        key = tuple(sorted(lits))  # order-insensitive identity
        if key in seen:
            n_dup += 1
            bad(f"clause {i}: duplicate of clause {seen[key]} {lits}")
        else:
            seen[key] = i
    if h_top != 1 + len(body):
        bad(f"top={h_top}, expected 1 + {len(body)} (1 + total soft weight)")
    return {
        "ok": not problems,
        "problems": problems,
        "n_clauses": len(body),
        "n_distinct": len(seen),
        "duplicates": n_dup,
        "tautologies": n_taut,
        "wrong_length": n_len,
        "out_of_range": n_range,
        "repeated_variable": n_repvar,
        "non_unit_weight": n_weight,
        "unterminated": n_term,
        "top": h_top,
    }
