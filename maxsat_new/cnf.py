"""DIMACS CNF/WCNF loader with hard/soft handling.

Ported from src/sat/cnf.py @ 1e3eaaf.

Behavior copied, not text. Dropped vs source: `true_count_per_clause` (unused on
the EA path, PORT_NOTES §3). The redundant fallback parser in
src/cli/run_ea.py:24-79 is NOT ported (PORT_NOTES §3).

Two suspected-but-replicated behaviors are marked inline (PORT_NOTES §9):
  §9.5 the comment/skip filter drops any line starting with "0" or "%".
  §9.6 .cnf files load as all-soft, weight 1, zero hard clauses.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class Clause:
    weight: int
    lits: List[int]
    is_hard: bool


class WCNF:
    """DIMACS CNF / WCNF loader with hard/soft handling.

    - For CNF: all clauses are treated as soft, weight 1 (see §9.6 below).
    - For WCNF: "p wcnf n m top" header; clauses with weight >= top are hard.
      Clause lines: "<weight> lit1 lit2 ... 0".
    """

    def __init__(self, n_vars: int, hard_weight: int, is_wcnf: bool = True) -> None:
        self.n_vars: int = n_vars
        self.hard_weight: int = hard_weight
        self.is_wcnf: bool = is_wcnf
        self.clauses: List[Clause] = []
        # Occurrence lists (1-indexed by variable id).
        self.pos_adj: List[List[int]] = [[] for _ in range(n_vars + 1)]
        self.neg_adj: List[List[int]] = [[] for _ in range(n_vars + 1)]

    @staticmethod
    def parse_dimacs(path: str) -> "WCNF":
        n_vars: int | None = None
        n_clauses: int | None = None
        top: int | None = None
        is_wcnf = False
        clauses: List[Clause] = []

        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                # PORT_NOTES §9.5 (replicated, not fixed): this also drops any
                # line whose first character is "0" or "%", including a stray
                # clause line that happens to start with token "0...".
                if not line or line.startswith("c") or line.startswith("%") or line.startswith("0"):
                    continue
                if line.startswith("p"):
                    # p cnf <n_vars> <n_clauses>
                    # p wcnf <n_vars> <n_clauses> <top>
                    toks = line.split()
                    if len(toks) < 4:
                        raise ValueError(f"Bad problem line: {line}")
                    fmt = toks[1].lower()
                    n_vars = int(toks[2])
                    n_clauses = int(toks[3])
                    if fmt == "wcnf":
                        is_wcnf = True
                        if len(toks) >= 5:
                            top = int(toks[4])
                        else:
                            # Old-style WCNF header without `top` (e.g. Selman's
                            # rwms generator, *.clq.wcnf, ram_*.ra1.wcnf). By
                            # convention this means "no hard clauses": every
                            # clause is soft. Sentinel no real weight reaches.
                            top = 10 ** 18
                    elif fmt != "cnf":
                        raise ValueError(f"Unknown DIMACS format: {fmt}")
                    continue

                parts = line.split()
                if not parts:
                    continue
                if is_wcnf:
                    weight = int(parts[0])
                    lits = [int(x) for x in parts[1:] if x != "0"]
                    if top is None:
                        raise ValueError("WCNF clause read before header")
                    is_hard = weight >= top
                else:
                    # PORT_NOTES §9.6 (replicated, not fixed): CNF clauses load
                    # as soft, weight 1, never hard. "Solve a .cnf" therefore
                    # means "maximize satisfied clauses".
                    if top is None:
                        top = 10 ** 9  # effectively infinite
                    weight = 1
                    lits = [int(x) for x in parts if x != "0"]
                    is_hard = False

                clauses.append(Clause(weight=weight, lits=lits, is_hard=is_hard))

        if n_vars is None or n_clauses is None:
            raise ValueError("Missing 'p' header")
        # Some files declare a clause count that disagrees with the body; the
        # source neither enforces nor warns, so neither do we.

        inst = WCNF(
            n_vars=n_vars,
            hard_weight=top if top is not None else 10 ** 9,
            is_wcnf=is_wcnf,
        )
        for cl in clauses:
            cid = len(inst.clauses)
            inst.clauses.append(cl)
            for lit in cl.lits:
                v = abs(lit)
                if lit > 0:
                    inst.pos_adj[v].append(cid)
                else:
                    inst.neg_adj[v].append(cid)
        return inst

    def eval_assignment(self, assign01: List[int]) -> Tuple[int, int, int]:
        """Return (satisfied_weight, hard_violations, soft_violations).

        assign01: list of 0/1 of length n_vars+1 (index 0 unused).
        """
        sat_w = 0
        hard_v = 0
        soft_v = 0
        for cl in self.clauses:
            satisfied = False
            for lit in cl.lits:
                v = abs(lit)
                if (lit > 0 and assign01[v] == 1) or (lit < 0 and assign01[v] == 0):
                    satisfied = True
                    break
            if satisfied:
                sat_w += cl.weight
            elif cl.is_hard:
                hard_v += 1
            else:
                soft_v += 1
        return sat_w, hard_v, soft_v
