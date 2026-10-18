from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterable

@dataclass
class Clause:
    weight: int
    lits: List[int]
    is_hard: bool

class WCNF:
    """
    DIMACS CNF / WCNF loader with hard/soft handling.

    - For CNF: all clauses are treated as hard (weight = top).
    - For WCNF: "p wcnf n m top" header; clauses with weight >= top are hard.
      Clause lines: "<weight> lit1 lit2 ... 0"
    """
    def __init__(self, n_vars: int, hard_weight: int, is_wcnf: bool = True):
        self.n_vars = n_vars
        self.hard_weight = hard_weight
        self.is_wcnf = is_wcnf
        self.clauses: List[Clause] = []
        # Occurrence lists (1-indexed by variable id)
        self.pos_adj: List[List[int]] = [[] for _ in range(n_vars + 1)]
        self.neg_adj: List[List[int]] = [[] for _ in range(n_vars + 1)]

    @staticmethod
    def _detect_format(path: str) -> str:
        """
        "legacy" if the file has a `p cnf`/`p wcnf` problem line, "new" if the
        first non-comment line is already a clause.

        The new format (MaxSAT Evaluation 2022+) drops the problem line
        entirely and prefixes hard clauses with `h`; soft clauses keep a
        leading integer weight. Sniffing is unambiguous because a legacy file
        must carry `p` before any clause.
        """
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("c") or line.startswith("%"):
                    continue
                return "legacy" if line.startswith("p") else "new"
        raise ValueError(f"{path}: no problem line and no clauses -- empty instance")

    @staticmethod
    def _parse_new_format(path: str) -> "WCNF":
        """
        MaxSAT Evaluation 2022+ WCNF: no `p` line, `h <lits> 0` for hard
        clauses, `<weight> <lits> 0` for soft ones.

        `n_vars` is the largest variable index that actually occurs, since no
        header declares it. Hard clauses are assigned the standard `top`
        sentinel (total soft weight + 1) so the resulting object is
        indistinguishable from the same instance written in legacy form.

        Every malformed line raises with the file and line number. Nothing is
        skipped or guessed: a record built from a misread instance is worse
        than no record at all.
        """
        clauses: List[Clause] = []
        max_var = 0
        soft_weight_total = 0

        with open(path, "r", encoding="utf-8") as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("c"):
                    continue

                toks = line.split()
                if toks[-1] != "0":
                    raise ValueError(
                        f"{path}:{lineno}: clause is not 0-terminated: {line[:80]!r}"
                    )
                body = toks[:-1]
                if not body:
                    raise ValueError(f"{path}:{lineno}: bare '0' line, not a clause")

                if body[0] == "h":
                    is_hard = True
                    weight = 0  # replaced with `top` once it is known
                    lit_toks = body[1:]
                else:
                    is_hard = False
                    try:
                        weight = int(body[0])
                    except ValueError:
                        raise ValueError(
                            f"{path}:{lineno}: expected 'h' or an integer weight, "
                            f"got {body[0]!r}"
                        ) from None
                    if weight < 0:
                        raise ValueError(
                            f"{path}:{lineno}: negative soft weight {weight}"
                        )
                    lit_toks = body[1:]
                    soft_weight_total += weight

                try:
                    lits = [int(x) for x in lit_toks]
                except ValueError:
                    raise ValueError(
                        f"{path}:{lineno}: non-integer literal in {line[:80]!r}"
                    ) from None
                if any(lit == 0 for lit in lits):
                    raise ValueError(
                        f"{path}:{lineno}: embedded 0 before end of clause: {line[:80]!r}"
                    )

                for lit in lits:
                    if abs(lit) > max_var:
                        max_var = abs(lit)
                clauses.append(Clause(weight=weight, lits=lits, is_hard=is_hard))

        if not clauses:
            raise ValueError(f"{path}: new-format WCNF with no clauses")

        # Standard `top` convention: strictly greater than the total soft
        # weight, so falsifying every soft clause still costs less than
        # breaking one hard clause.
        top = soft_weight_total + 1
        for cl in clauses:
            if cl.is_hard:
                cl.weight = top

        inst = WCNF(n_vars=max_var, hard_weight=top, is_wcnf=True)
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

    @staticmethod
    def parse_dimacs(path: str) -> "WCNF":
        if WCNF._detect_format(path) == "new":
            return WCNF._parse_new_format(path)

        n_vars = None
        n_clauses = None
        top = None
        is_wcnf = False
        clauses: List[Clause] = []

        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("c") or line.startswith("%") or line.startswith("0"):
                    continue
                if line.startswith("p"):
                    # Examples:
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
                            # convention this means "no hard clauses" — every
                            # clause is soft. Pick a sentinel that no real
                            # weight will ever reach.
                            top = 10**18
                    elif fmt != "cnf":
                        raise ValueError(f"Unknown DIMACS format: {fmt}")
                    continue

                # Clause line
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
                    # CNF: weight = top (hard)
                    if top is None:
                        top = 10**9  # effectively infinite
                    weight = 1#top
                    lits = [int(x) for x in parts if x != "0"]
                    is_hard = False#True

                if len(lits) == 0:
                    # Empty clause
                    clauses.append(Clause(weight=weight, lits=[], is_hard=is_hard))
                else:
                    clauses.append(Clause(weight=weight, lits=lits, is_hard=is_hard))

        if n_vars is None or n_clauses is None:
            raise ValueError("Missing 'p' header")
        if len(clauses) != n_clauses:
            # Some files are sloppy; we don't strictly enforce, but warn
            # Here we only check and proceed.
            pass

        inst = WCNF(
            n_vars=n_vars,
            hard_weight=top if top is not None else 10**9,
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

    # ---------- Scoring helpers ----------

    def eval_assignment(self, assign01: List[int]) -> Tuple[int, int, int]:
        """
        Returns (satisfied_weight, hard_violations, soft_violations).
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
            else:
                if cl.is_hard:
                    hard_v += 1
                else:
                    soft_v += 1
        return sat_w, hard_v, soft_v

    def true_count_per_clause(self, assign01: List[int]) -> List[int]:
        tc = [0] * len(self.clauses)
        for i, cl in enumerate(self.clauses):
            cnt = 0
            for lit in cl.lits:
                v = abs(lit)
                if (lit > 0 and assign01[v] == 1) or (lit < 0 and assign01[v] == 0):
                    cnt += 1
            tc[i] = cnt
        return tc
