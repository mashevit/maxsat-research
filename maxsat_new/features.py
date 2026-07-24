"""Instance feature extraction for sizing rules.

NEW module per PORT_NOTES §4 ("Config + sizing-rule design"). This is **not** a
port: §3's port map has no row for `features.py`. §4 is the spec — the seven
`InstanceFeatures` fields and their degenerate-case fallbacks are copied from it
verbatim.

Prior art exists in `src/` but is deliberately not imported or depended on
(PORT_NOTES §2: `maxsat_new` must not import from `src/`):
`src/sat/metadata.py:compute_metadata` extracts a superset of these fields. See
STEP_04_NOTES.md "Phase-1 audit findings".

Self-contained: imports only stdlib and `maxsat_new.cnf`.
"""
from __future__ import annotations

from dataclasses import dataclass

from maxsat_new.cnf import WCNF


@dataclass(frozen=True)
class InstanceFeatures:
    """Structural features a sizing rule may key on (PORT_NOTES §4).

    Exactly the seven §4 fields, no more. Frozen so a rule cannot mutate the
    features it is handed (purity, PORT_NOTES §4).
    """

    n_vars: int
    n_clauses: int
    n_hard: int
    n_soft: int
    hard_frac: float        # n_hard / n_clauses   (0.0 if n_clauses == 0)
    hard_soft_ratio: float  # n_hard / n_soft      (n_soft == 0 -> n_hard)
    total_soft_weight: int  # sum of soft-clause weights (for §5 cost conversion)


def extract(wcnf: WCNF) -> InstanceFeatures:
    """Compute all seven §4 features in ONE pass over `wcnf.clauses`.

    `n_vars` is read from the stored `WCNF.n_vars` field (O(1)); `n_clauses`,
    `n_hard` and `total_soft_weight` are accumulated in a single loop, since the
    ported `WCNF` stores none of them (STEP_04 Phase-1 audit item 1). The two
    ratios are derived once after the loop.

    Degenerate fallbacks are §4's (audit item 4):
      - `hard_frac` is 0.0 when `n_clauses == 0` (avoids ZeroDivisionError).
      - `hard_soft_ratio` is `n_hard` when `n_soft == 0` (§4 "inf-safe").
    """
    n_clauses = 0
    n_hard = 0
    total_soft_weight = 0
    for cl in wcnf.clauses:
        n_clauses += 1
        if cl.is_hard:
            n_hard += 1
        else:
            total_soft_weight += cl.weight

    n_soft = n_clauses - n_hard
    hard_frac = n_hard / n_clauses if n_clauses else 0.0
    hard_soft_ratio = n_hard / n_soft if n_soft else float(n_hard)

    return InstanceFeatures(
        n_vars=wcnf.n_vars,
        n_clauses=n_clauses,
        n_hard=n_hard,
        n_soft=n_soft,
        hard_frac=hard_frac,
        hard_soft_ratio=hard_soft_ratio,
        total_soft_weight=total_soft_weight,
    )
