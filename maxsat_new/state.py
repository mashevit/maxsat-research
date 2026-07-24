"""Incremental local-search state for WalkSAT-style polishing.

Ported from src/sat/state.py @ 1e3eaaf.

Behavior copied, not text. This is the internal `SatState` bookkeeping used by
`walksat_polish` (PORT_NOTES §5); it is not the provider-facing snapshot.

Ported: `ClauseInfo` and the `SatState` methods reachable from `walksat_polish`.
Dropped (see maxsat_new/STEP_02_NOTES.md for the full list):
  - the four `'''...'''` dead method bodies at src lines 139/212/219/310 (§3);
  - `restart_partial_from_best` (never on the polish path, §3);
  - `clause_indices_for_var`, `var_is_tabu`, `set_tabu`, `hard_safe` (method),
    `vars_adjacent_to`, `all_unsat_indices`, `bump_clause` — real methods, but
    unreachable from `walksat_polish` (satlike/tabu/dynamic-weight machinery).

No import from src/. Standalone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Iterable
import random


@dataclass
class ClauseInfo:
    lits: List[int]
    base_w: int
    is_hard: bool
    dyn_w: float = 0.0  # set at init to base_w
    true_cnt: int = 0
    age: int = 0        # optional: increments when unsatisfied


@dataclass
class SatState:
    """
    Holds the evolving SAT/MaxSAT local-search state.
    - assignment: 1-based variable assignment in {False, True}; index 0 unused
    - clauses: unified list of ClauseInfo, hard first or mixed; indices map to pos/neg occ
    - pos_occ/neg_occ: occurrence lists: for var v -> list of clause indices where v or ~v appears
    """
    nvars: int
    clauses: List[ClauseInfo]
    pos_occ: List[List[int]]
    neg_occ: List[List[int]]
    rng: random.Random
    # counters & book-keeping
    flips: int = 0
    restarts: int = 0
    best_soft_obj: float = float("-inf")
    best_hard_violations: int = 10**9
    best_assign: Optional[List[bool]] = None
    hard_violations: int = 0
    # current assignment
    assign: List[bool] = field(default_factory=list)
    # tabu tenure storage: iteration index when var becomes free
    tabu_until: List[int] = field(default_factory=list)
    iter_idx: int = 0

    def __post_init__(self) -> None:
        if not self.assign:
            # Initialize random assignment in {False, True}
            self.assign = [False] + [self.rng.choice((False, True)) for _ in range(self.nvars)]
        if not self.tabu_until:
            self.tabu_until = [0] * (self.nvars + 1)
        # Initialize dynamic weights and true-counts
        for c in self.clauses:
            c.dyn_w = float(c.base_w)
            c.true_cnt = self._compute_clause_true_count(c.lits)
        # Compute initial objective & hard violations
        self.hard_violations = self._count_hard_violations()
        self.best_soft_obj = self._soft_objective()
        self.best_hard_violations = self.hard_violations
        self.best_assign = self.assign.copy()

    def _lit_val(self, lit: int) -> bool:
        v = abs(lit)
        val = self.assign[v]
        return val if lit > 0 else (not val)

    def _compute_clause_true_count(self, lits: Iterable[int]) -> int:
        return sum(1 for lit in lits if self._lit_val(lit))

    def _count_hard_violations(self) -> int:
        return sum(1 for c in self.clauses if c.is_hard and c.true_cnt == 0)

    def _soft_objective(self) -> float:
        # Sum dynamic weights of satisfied soft clauses
        return sum(c.dyn_w for c in self.clauses if (not c.is_hard) and c.true_cnt > 0)

    def flip_var_effect(self, v: int) -> Tuple[float, int]:
        """
        Compute:
        - gain: delta of the soft objective using dyn_w
        - delta_hard: (#broken_hard_after - #broken_hard_before)

        Positive delta_hard => you break additional hard clause(s).
        Negative delta_hard => you fix some broken hard clause(s).
        Zero => no net change.
        Runs in O(occ(v)).
        """
        gain = 0.0
        delta_hard = 0

        # Clauses where v appears positively
        for ci in self.pos_occ[v]:
            c = self.clauses[ci]
            was_sat = c.true_cnt > 0
            t_after = c.true_cnt - 1 if self.assign[v] else c.true_cnt + 1

            if c.is_hard:
                if was_sat and t_after == 0:
                    delta_hard += 1          # you break a hard clause
                elif (not was_sat) and t_after > 0:
                    delta_hard -= 1          # you fix a broken hard clause
            else:
                if (not was_sat) and t_after > 0:
                    gain += c.dyn_w
                elif was_sat and t_after == 0:
                    gain -= c.dyn_w

        # Clauses where v appears negated
        for ci in self.neg_occ[v]:
            c = self.clauses[ci]
            was_sat = c.true_cnt > 0
            t_after = c.true_cnt + 1 if self.assign[v] else c.true_cnt - 1

            if c.is_hard:
                if was_sat and t_after == 0:
                    delta_hard += 1
                elif (not was_sat) and t_after > 0:
                    delta_hard -= 1
            else:
                if (not was_sat) and t_after > 0:
                    gain += c.dyn_w
                elif was_sat and t_after == 0:
                    gain -= c.dyn_w

        return gain, delta_hard

    def apply_flip(self, v: int) -> None:
        """Apply flip of variable v and update true-counts incrementally. O(occ(v))."""
        self.assign[v] = (not self.assign[v])
        # Update positive occurrences
        for ci in self.pos_occ[v]:
            c = self.clauses[ci]
            if self.assign[v]:
                c.true_cnt += 1
            else:
                c.true_cnt -= 1
        # Update negative occurrences
        for ci in self.neg_occ[v]:
            c = self.clauses[ci]
            if self.assign[v]:
                c.true_cnt -= 1
            else:
                c.true_cnt += 1
        self.flips += 1
        self.iter_idx += 1

    def flip_var_hard_delta(self, v: int) -> int:
        """
        Net change in #hard violations if we flip v:
        delta_hard = broken_hard - made_hard  (negative is good)
        Robust to (a) duplicates and (b) v and ¬v in the same clause.
        """
        broken = 0
        made = 0

        # Clauses touched by v (either polarity), deduped
        touched = set(self.pos_occ[v])
        touched.update(self.neg_occ[v])

        # Count multiplicity of v in each clause by polarity (handles duplicates)
        # (If your data structure guarantees uniqueness, you can skip counting.)
        from collections import Counter, defaultdict
        pos_count = Counter(self.pos_occ[v])
        neg_count = Counter(self.neg_occ[v])

        v_is_true = self.assign[v]

        for ci in touched:
            c = self.clauses[ci]
            if not c.is_hard:
                continue

            was_sat = c.true_cnt > 0

            # Contribution change of v to c.true_cnt after flip:
            # If v is currently True, pos literals lose, neg literals gain; and vice versa.
            pos_mult = pos_count.get(ci, 0)
            neg_mult = neg_count.get(ci, 0)
            if v_is_true:
                delta_true_lits = -pos_mult + neg_mult
            else:
                delta_true_lits = +pos_mult - neg_mult

            t_after = c.true_cnt + delta_true_lits

            if was_sat and t_after == 0:
                broken += 1
            elif (not was_sat) and t_after > 0:
                made += 1

        return broken - made

    # NOTE: src/sat/state.py defines `unsat_soft_indices` twice, byte-identically
    # (lines 298 and 332); the second shadows the first. Kept once here — provably
    # no behavioral change. Listed in STEP_02_NOTES.md.
    def unsat_soft_indices(self) -> List[int]:
        return [i for i, c in enumerate(self.clauses) if (not c.is_hard) and c.true_cnt == 0]

    def unsat_hard_ids(self) -> List[int]:
        return [i for i, c in enumerate(self.clauses) if c.is_hard and c.true_cnt == 0]

    def snapshot_best_if_better(self) -> bool:
        hv = self._count_hard_violations()
        soft = self._soft_objective()
        better = (hv < self.best_hard_violations) or (hv == self.best_hard_violations and soft > self.best_soft_obj)
        if better:
            self.best_hard_violations = hv
            self.best_soft_obj = soft
            self.best_assign = self.assign.copy()
            return True
        return False

    def smooth(self, rho: float) -> None:
        """Move dyn_w toward base_w: dyn = base + rho*(dyn-base), 0<rho<1."""
        for c in self.clauses:
            if not c.is_hard and c.dyn_w > c.base_w:
                c.dyn_w = c.base_w + rho * (c.dyn_w - c.base_w)
