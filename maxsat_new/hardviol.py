"""Violated-hard-clause extraction — the training-set signal (PORT_NOTES §5, §10 step 6).

NEW module per PORT_NOTES §3: it consolidates the *intent* of
`src/evo/population.py:clause_satisfied` (`:90`) and
`src/sat/state.py:SatState.unsat_hard_ids` (`:301`), both @ 1e3eaaf. Neither is
ported as text; they agree on the predicate, and this is the one place that owns
it for the provider seam.

Runs on the new `maxsat_new.cnf.WCNF`: `wcnf.clauses` is one flat, file-ordered
list of `Clause(weight, lits, is_hard)`, and `lits` holds raw DIMACS signed ints
(`[1, -3, 4]`) — there is no internal literal remapping anywhere in the package,
so what goes out is what was in the file.

`idx` is the GLOBAL index into `wcnf.clauses` — hard and soft clauses enumerated
together — not an index into a hard-only sublist. That matches
`SatState.unsat_hard_ids` and the one real consumer of these indices,
`src/llm/prompt.py:extract_clause_examples`, which resolves them with
`wcnf.clauses[idx]`. The dead LLM block at `src/evo/memetic.py:100` sketched the
sublist convention instead (`enumerate(ind.hard_satisfied)`); that is a latent
bug and is deliberately NOT replicated.

Self-contained: stdlib only. No import from `src/`, and none from `cnf.py`
either — the WCNF is consumed structurally via `.clauses` / `.lits` / `.is_hard`.
"""
from __future__ import annotations

from typing import Any, Iterable, List, Sequence, Tuple


def _clause_satisfied(lits: Iterable[int], assign01: Sequence[bool]) -> bool:
    """A clause is satisfied iff at least one literal is true.

    Same predicate as `population.clause_satisfied`, taking the literal list
    directly instead of a clause object. Truthiness-based, so `assign01` may be
    `[False, True, ...]` or `[0, 1, ...]`.
    """
    for lit in lits:
        v = abs(lit)
        val = assign01[v]
        if (lit > 0 and val) or (lit < 0 and not val):
            return True
    return False


def violated_hard_clauses(
    wcnf: Any, assign01: Sequence[bool]
) -> List[Tuple[int, Tuple[int, ...]]]:
    """Return `(global_clause_idx, lits)` for every violated hard clause.

    Ordered by ascending global index (plain enumeration order), so the result
    is deterministic without sorting.

    `assign01` is 1-based with index 0 unused, length `n_vars + 1`. Truthiness
    is used, so both `[False, True, ...]` and `[0, 1, ...]` work. There is no
    bounds check on `assign01`: a too-short assignment is a caller bug and
    raises `IndexError`, exactly as the source predicate does.

    A hard clause with no literals is vacuously violated — that follows from
    `clause_satisfied` returning False on an empty literal list, and is
    preserved rather than special-cased.

    `lits` is a fresh tuple, never a reference into `wcnf.clauses[i].lits`, so a
    provider handed this snapshot cannot mutate the instance.
    """
    out: List[Tuple[int, Tuple[int, ...]]] = []
    for idx, cl in enumerate(wcnf.clauses):
        if not cl.is_hard:
            continue
        if _clause_satisfied(cl.lits, assign01):
            continue
        out.append((idx, tuple(cl.lits)))
    return out
