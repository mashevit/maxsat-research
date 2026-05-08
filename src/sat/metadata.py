from __future__ import annotations

import hashlib
import os
import re
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .cnf import WCNF, Clause


SCHEMA_VERSION = "1.0"

_FAMILY_PATTERNS = [
    # Order matters: more specific patterns first.
    (re.compile(r"^file_rwpms_", re.I), "random_weighted_partial_maxsat"),
    (re.compile(r"^file_rpms_", re.I),  "random_partial_maxsat"),
    (re.compile(r"^file_rwms_", re.I),  "random_weighted_maxsat"),
    (re.compile(r"^hamming",    re.I),  "max_clique_hamming"),
    (re.compile(r"^johnson",    re.I),  "max_clique_johnson"),
    (re.compile(r"\.clq\.wcnf$", re.I), "max_clique"),
    (re.compile(r"^ram_",       re.I),  "ramsey"),
    (re.compile(r"\.ra\d+\.wcnf$", re.I), "ramsey"),
    (re.compile(r"^uuf\d+",     re.I),  "uniform_random_unsat"),
    (re.compile(r"^uf\d+",      re.I),  "uniform_random_sat"),
]


def _infer_family(name: str) -> str:
    for pat, fam in _FAMILY_PATTERNS:
        if pat.search(name):
            return fam
    return "unknown"


def _file_sha256(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _stats(xs: List[float]) -> Dict[str, float]:
    if not xs:
        return {"n": 0, "min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "std": 0.0}
    return {
        "n": len(xs),
        "min": float(min(xs)),
        "max": float(max(xs)),
        "mean": float(statistics.fmean(xs)),
        "median": float(statistics.median(xs)),
        "std": float(statistics.pstdev(xs)) if len(xs) > 1 else 0.0,
    }


def _length_histogram(lengths: List[int], cap: int = 10) -> Dict[str, int]:
    hist: Dict[str, int] = {str(k): 0 for k in range(0, cap + 1)}
    hist[f">{cap}"] = 0
    for L in lengths:
        if L > cap:
            hist[f">{cap}"] += 1
        else:
            hist[str(L)] += 1
    return hist


@dataclass
class _ClauseFlags:
    n_horn: int = 0
    n_dual_horn: int = 0
    n_definite_horn: int = 0
    n_tautology: int = 0
    n_with_dup_lit: int = 0
    n_empty: int = 0


def _scan_clauses(clauses: List[Clause]) -> _ClauseFlags:
    f = _ClauseFlags()
    for cl in clauses:
        if not cl.lits:
            f.n_empty += 1
            continue
        seen_pos: set = set()
        seen_neg: set = set()
        seen_lits: set = set()
        dup = False
        taut = False
        for lit in cl.lits:
            if lit in seen_lits:
                dup = True
            seen_lits.add(lit)
            v = abs(lit)
            if lit > 0:
                if v in seen_neg:
                    taut = True
                seen_pos.add(v)
            else:
                if v in seen_pos:
                    taut = True
                seen_neg.add(v)
        if dup:
            f.n_with_dup_lit += 1
        if taut:
            f.n_tautology += 1
        n_pos = len(seen_pos)
        n_neg = len(seen_neg)
        if n_pos <= 1:
            f.n_horn += 1
            if n_pos == 1:
                f.n_definite_horn += 1
        if n_neg <= 1:
            f.n_dual_horn += 1
    return f


def compute_metadata(
    inst: WCNF,
    *,
    path: Optional[str] = None,
    include_file_info: bool = True,
    length_hist_cap: int = 10,
) -> Dict[str, Any]:
    """
    Extract structural metadata from a parsed WCNF instance.

    Pure-parse features only (no solver). Safe to run on every instance.
    """
    n_vars = inst.n_vars
    clauses = inst.clauses
    n_clauses = len(clauses)

    # Per-clause / per-literal scans
    lengths: List[int] = []
    n_hard = 0
    soft_weights: List[int] = []
    total_lits = 0
    pos_lits = 0
    neg_lits = 0
    for cl in clauses:
        L = len(cl.lits)
        lengths.append(L)
        total_lits += L
        for lit in cl.lits:
            if lit > 0:
                pos_lits += 1
            else:
                neg_lits += 1
        if cl.is_hard:
            n_hard += 1
        else:
            soft_weights.append(int(cl.weight))

    n_soft = n_clauses - n_hard

    # Variable degrees (1-indexed; skip slot 0)
    pos_deg = [len(inst.pos_adj[v]) for v in range(1, n_vars + 1)]
    neg_deg = [len(inst.neg_adj[v]) for v in range(1, n_vars + 1)]
    tot_deg = [p + n for p, n in zip(pos_deg, neg_deg)]

    n_unused = sum(1 for d in tot_deg if d == 0)
    n_pure_pos = sum(1 for p, n in zip(pos_deg, neg_deg) if p > 0 and n == 0)
    n_pure_neg = sum(1 for p, n in zip(pos_deg, neg_deg) if p == 0 and n > 0)
    n_balanced = sum(1 for p, n in zip(pos_deg, neg_deg) if p > 0 and n > 0)

    flags = _scan_clauses(clauses)

    sum_soft_w = int(sum(soft_weights))
    fmt = "wcnf" if getattr(inst, "is_wcnf", False) else "cnf"
    md: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "format": fmt,
        "sizes": {
            "n_vars": n_vars,
            "n_clauses": n_clauses,
            "n_hard": n_hard,
            "n_soft": n_soft,
            "n_literals": total_lits,
            "top": int(inst.hard_weight),
        },
        "density": {
            "clauses_per_var": (n_clauses / n_vars) if n_vars else 0.0,
            "literals_per_clause_mean": (total_lits / n_clauses) if n_clauses else 0.0,
            "literals_per_var_mean": (total_lits / n_vars) if n_vars else 0.0,
        },
        "clause_length": {
            **_stats([float(L) for L in lengths]),
            "histogram": _length_histogram(lengths, cap=length_hist_cap),
            "is_uniform_3sat": all(L == 3 for L in lengths) if lengths else False,
            "max_uniform_length": (
                lengths[0] if lengths and all(L == lengths[0] for L in lengths) else None
            ),
        },
        "var_degree": {
            "pos": _stats([float(d) for d in pos_deg]),
            "neg": _stats([float(d) for d in neg_deg]),
            "total": _stats([float(d) for d in tot_deg]),
            "n_unused": n_unused,
            "n_pure_positive": n_pure_pos,
            "n_pure_negative": n_pure_neg,
            "n_balanced": n_balanced,
        },
        "polarity": {
            "pos_literals": pos_lits,
            "neg_literals": neg_lits,
            "pos_fraction": (pos_lits / total_lits) if total_lits else 0.0,
        },
        "hard_soft": {
            "hard_fraction": (n_hard / n_clauses) if n_clauses else 0.0,
            "is_partial_maxsat": n_hard > 0 and n_soft > 0,
            "is_pure_maxsat": n_hard == 0 and n_soft > 0,
            "is_sat": n_hard == n_clauses and n_clauses > 0,
        },
        "soft_weights": {
            **_stats([float(w) for w in soft_weights]),
            "sum": sum_soft_w,
            "n_unique": len(set(soft_weights)),
            "is_unweighted": (
                len(set(soft_weights)) <= 1 if soft_weights else True
            ),
        },
        "structure_flags": {
            "n_horn_clauses": flags.n_horn,
            "horn_fraction": (flags.n_horn / n_clauses) if n_clauses else 0.0,
            "n_definite_horn_clauses": flags.n_definite_horn,
            "n_dual_horn_clauses": flags.n_dual_horn,
            "n_tautology_clauses": flags.n_tautology,
            "n_clauses_with_dup_literal": flags.n_with_dup_lit,
            "n_empty_clauses": flags.n_empty,
        },
    }

    if include_file_info and path is not None:
        name = os.path.basename(path)
        st = os.stat(path)
        md["file"] = {
            "path": os.path.abspath(path),
            "name": name,
            "ext": os.path.splitext(name)[1].lower(),
            "size_bytes": st.st_size,
            "sha256": _file_sha256(path),
            "family": _infer_family(name),
        }

    return md


def compute_metadata_from_path(path: str, **kwargs: Any) -> Dict[str, Any]:
    inst = WCNF.parse_dimacs(path)
    return compute_metadata(inst, path=path, **kwargs)
