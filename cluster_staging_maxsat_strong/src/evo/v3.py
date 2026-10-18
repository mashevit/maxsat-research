"""`impl: v3`, the stronger memetic: docs/current2/STRONGER_MEMETIC_DESIGN.md (repo).

v3 with none of the keys below is v2 on an instance without hard clauses and
`impl: hard` on an instance with them (`hard_mode: auto`); both are tested for
exact equality. Each component is opt-in:

  top level
    hard_mode: auto | on | off      auto = on iff the instance the EA solves (the
                                    kernel, when kernelising) has hard clauses
  ea (B3 mutation, B4 crossover)
    mutation: rate | count | walk | diff     rate = today's mutate1 (pmutate)
    mutation_k: int                          flips for count / walk / diff (16)
    crossover: clause_aware | px             px = partition crossover
    px_min_q: int                            fewer components -> fallback (2)
    px_fallback: clause_aware | mutate_only  mutate_only = copy of the fitter parent
    diag_every: int                          measure mutation damage every Nth child (10; 0 = never)
  ls (B1 tabu, B2 clause weighting, B5 native)
    core: walksat | dls
    tabu: none | tenure | cc                 tenure: walksat core only; cc: both cores
    tabu_tenure: int (10), tabu_tenure_rand: int (0)
    dls_t (15), dls_sp (0.01), dls_zeta (50), dls_h_inc (1)
    weights: call | run                      dls: reset per call, or one vector per run
    native: false | true                     the C core (src/native); true = required

Unknown values and v3 keys under another `impl` are refused (ValueError).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sat.ls_v3 import TABU_MODES, dls_v3, init_dynamic_weights, v3_static, walksat_v3
from sat.rng import MTRng, PortableRng

HARD_MODES = ("auto", "on", "off")
MUTATIONS = ("rate", "count", "walk", "diff")
CROSSOVERS = ("clause_aware", "px")
PX_FALLBACKS = ("clause_aware", "mutate_only")
CORES = ("walksat", "dls")
WEIGHTS = ("call", "run")

_EA_KEYS = ("mutation", "mutation_k", "crossover", "px_min_q", "px_fallback", "diag_every")
_LS_KEYS = ("core", "tabu", "tabu_tenure", "tabu_tenure_rand", "dls_t", "dls_sp", "dls_zeta",
            "dls_h_inc", "weights", "native")


def _pick(d: Dict[str, Any], key: str, allowed, default: str) -> str:
    v = str(d.get(key, default)).lower()
    if v not in allowed:
        raise ValueError(f"{key} must be one of {allowed}, got {v!r}")
    return v


def v3_keys_present(cfg: Dict[str, Any]) -> List[str]:
    ea, ls = cfg.get("ea") or {}, cfg.get("ls") or {}
    out = [f"ea.{k}" for k in _EA_KEYS if k in ea] + [f"ls.{k}" for k in _LS_KEYS if k in ls]
    if "hard_mode" in cfg:
        out.append("hard_mode")
    return out


def v3_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    ea, ls = cfg.get("ea") or {}, cfg.get("ls") or {}
    c = {
        "hard_mode": _pick(cfg, "hard_mode", HARD_MODES, "auto"),
        "mutation": _pick(ea, "mutation", MUTATIONS, "rate"),
        "mutation_k": int(ea.get("mutation_k", 16)),
        "crossover": _pick(ea, "crossover", CROSSOVERS, "clause_aware"),
        "px_min_q": int(ea.get("px_min_q", 2)),
        "px_fallback": _pick(ea, "px_fallback", PX_FALLBACKS, "clause_aware"),
        "diag_every": int(ea.get("diag_every", 10)),
        "core": _pick(ls, "core", CORES, "walksat"),
        "tabu": _pick(ls, "tabu", TABU_MODES, "none"),
        "tabu_tenure": int(ls.get("tabu_tenure", 10)),
        "tabu_tenure_rand": int(ls.get("tabu_tenure_rand", 0)),
        "dls_t": int(ls.get("dls_t", 15)),
        "dls_sp": float(ls.get("dls_sp", 0.01)),
        "dls_zeta": int(ls.get("dls_zeta", 50)),
        "dls_h_inc": int(ls.get("dls_h_inc", 1)),
        "weights": _pick(ls, "weights", WEIGHTS, "call"),
        "native": bool(ls.get("native", False)),
    }
    if c["mutation_k"] < 1 or c["tabu_tenure"] < 0 or c["tabu_tenure_rand"] < 0 or c["dls_t"] < 1:
        raise ValueError("mutation_k >= 1, tabu_tenure >= 0, tabu_tenure_rand >= 0, dls_t >= 1 required")
    if not (0.0 <= c["dls_sp"] <= 1.0) or c["dls_zeta"] < 1 or c["dls_h_inc"] < 1:
        raise ValueError("dls_sp in [0, 1], dls_zeta >= 1, dls_h_inc >= 1 required")
    if c["core"] == "dls" and c["tabu"] == "tenure":
        # §6.2: in the weighting core a fixed tenure can forbid the move the
        # weights promote; only CC (or the least-recently-flipped tie-break).
        raise ValueError("ls.tabu: tenure applies to the walksat core only; use cc with dls (design §6.2)")
    if c["weights"] == "run" and c["core"] != "dls":
        raise ValueError("ls.weights: run needs ls.core: dls")
    return c


def check_cfg(cfg: Dict[str, Any], impl: str) -> Optional[Dict[str, Any]]:
    """Parse v3 keys for impl v3; refuse them under any other impl."""
    if impl == "v3":
        return v3_cfg(cfg)
    present = v3_keys_present(cfg)
    if present:
        raise ValueError(f"{', '.join(present)} need impl: v3 (got impl: {impl})")
    return None


def resolve_hard_mode(vc: Dict[str, Any], wcnf) -> bool:
    if vc["hard_mode"] == "on":
        return True
    if vc["hard_mode"] == "off":
        return False
    return any(cl.is_hard for cl in wcnf.clauses)


def custom_polish(vc: Dict[str, Any]) -> bool:
    """True when the polish is not v2's (or the hard tree's) unchanged core."""
    return vc["core"] != "walksat" or vc["tabu"] != "none" or vc["native"]


# --------------------------------------------------------------------- stats

class V3Stats:
    __slots__ = ("d",)

    def __init__(self) -> None:
        self.d: Dict[str, Any] = {
            "hard_mode": None, "mutation_damage_sum": 0, "mutation_damage_n": 0,
            "mutation_flips_sum": 0, "mutation_refused": 0,
            "px_calls": 0, "px_q_sum": 0, "px_q_max": 0, "px_q_hist": {}, "px_fallbacks": 0,
            "px_child_equals_parent": 0,
            "tabu_skips": 0, "tabu_aspirations": 0, "tabu_all_blocked": 0,
            "dls_stuck": 0, "dls_smooths": 0, "dls_cc_blocked": 0, "polish_core": None, "ls_native": False,
        }

    def as_dict(self) -> Dict[str, Any]:
        d = dict(self.d)
        n = d["mutation_damage_n"]
        d["mutation_damage_mean"] = (d["mutation_damage_sum"] / n) if n else None
        c = d["px_calls"]
        d["px_q_mean"] = (d["px_q_sum"] / c) if c else None
        d["px_q_hist"] = {str(k): v for k, v in sorted(d["px_q_hist"].items())}
        return d


# ----------------------------------------------------------------- B3 mutation

def _guarded_flip(a: List[bool], v: int, guard) -> bool:
    """Flip v unless it breaks a satisfied hard clause (mutate1's rule). guard is
    None (no hard clauses) or (hard_clauses, hard_occurs, hard_satisfied)."""
    if guard is None:
        a[v] = not a[v]
        return True
    hard_clauses, hard_occurs, hsat = guard
    affected = hard_occurs[v]
    a[v] = not a[v]
    new = []
    for ci in affected:
        cl = hard_clauses[ci]
        s = any((l > 0 and a[l]) or (l < 0 and not a[-l]) for l in cl.lits)
        if hsat[ci] and not s:
            a[v] = not a[v]
            return False
        new.append(s)
    for ci, s in zip(affected, new):
        hsat[ci] = s
    return True


def mutate_v3(child: List[bool], vc: Dict[str, Any], wcnf, rng, p1, p2, guard, stats: V3Stats) -> int:
    """B3: bounded, optionally local mutation; returns the number of flips made."""
    n = wcnf.n_vars
    k = min(vc["mutation_k"], n)
    mode = vc["mutation"]
    flips = refused = 0
    if n == 0:
        return 0
    if mode == "diff":
        A, B = p1.assign01, p2.assign01
        diff = [v for v in range(1, n + 1) if A[v] != B[v]]
        if diff:
            for v in (rng.sample(diff, k) if len(diff) > k else diff):
                if _guarded_flip(child, v, guard):
                    flips += 1
                else:
                    refused += 1
            stats.d["mutation_flips_sum"] += flips
            stats.d["mutation_refused"] += refused
            return flips
        mode = "walk"  # equal parents: fall back to a local walk
    if mode == "count":
        for v in rng.sample(range(1, n + 1), k):
            if _guarded_flip(child, v, guard):
                flips += 1
            else:
                refused += 1
    else:  # walk
        nbrs = v3_static(wcnf).nbrs
        seen = set()
        v = rng.randrange(1, n + 1)
        steps = 0
        while len(seen) < k and steps < 8 * k:
            steps += 1
            if v not in seen:
                seen.add(v)
                if _guarded_flip(child, v, guard):
                    flips += 1
                else:
                    refused += 1
            nb = nbrs[v]
            v = nb[rng.randrange(len(nb))] if nb else rng.randrange(1, n + 1)
    stats.d["mutation_flips_sum"] += flips
    stats.d["mutation_refused"] += refused
    return flips


# ---------------------------------------------------------------- B4 crossover

def px_components(A: List[bool], B: List[bool], wcnf, return_map: bool = False):
    """Connected components of the variable-interaction graph restricted to the
    variables where A and B differ, in increasing order of their first variable.
    With return_map, also comp_of[v] (1-based component id, 0 outside D)."""
    n = wcnf.n_vars
    nbrs = v3_static(wcnf).nbrs
    comp_of = [0] * (n + 1)   # 0 = not in D / unvisited
    indiff = [False] * (n + 1)
    for v in range(1, n + 1):
        if A[v] != B[v]:
            indiff[v] = True
    comps: List[List[int]] = []
    for v in range(1, n + 1):
        if indiff[v] and not comp_of[v]:
            cid = len(comps) + 1
            comp_of[v] = cid
            stack, comp = [v], []
            while stack:
                u = stack.pop()
                comp.append(u)
                for x in nbrs[u]:
                    if indiff[x] and not comp_of[x]:
                        comp_of[x] = cid
                        stack.append(x)
            comp.sort()
            comps.append(comp)
    return (comps, comp_of) if return_map else comps


def partition_crossover(p1, p2, wcnf) -> Tuple[List[bool], int, bool]:
    """B4: per component, the parent with the lower (hard violations, soft cost)
    on the clauses touching it; ties go to the fitter parent. The child is the
    best of all 2**q recombinations and never worse than either parent
    (design §5.2). Returns (child, q, child_equals_a_parent)."""
    from sat.walksat_v2 import _static_for
    st = _static_for(wcnf)
    lits, is_hard, w, occ = st.lits, st.is_hard, st.w, st.occ
    A, B = p1.assign01, p2.assign01
    fitter_is_b = p2.fitness > p1.fitness
    comps, comp_of = px_components(A, B, wcnf, return_map=True)
    q = len(comps)
    child = list(A)
    took_a = took_b = 0
    # One pass over the clauses touching D: each lies in exactly one component
    # (design §5.2), so its cost under A and under B goes to that component.
    ha, hb, sa, sb = [0] * (q + 1), [0] * (q + 1), [0] * (q + 1), [0] * (q + 1)
    mark = bytearray(len(lits))
    for comp in comps:
        for v in comp:
            cid = comp_of[v]
            for ci, _d in occ[v]:
                if mark[ci]:
                    continue
                mark[ci] = 1
                sat_a = sat_b = False
                for l in lits[ci]:
                    if l > 0:
                        if A[l]:
                            sat_a = True
                        if B[l]:
                            sat_b = True
                    else:
                        if not A[-l]:
                            sat_a = True
                        if not B[-l]:
                            sat_b = True
                if is_hard[ci]:
                    if not sat_a:
                        ha[cid] += 1
                    if not sat_b:
                        hb[cid] += 1
                else:
                    if not sat_a:
                        sa[cid] += w[ci]
                    if not sat_b:
                        sb[cid] += w[ci]
    for cid, comp in enumerate(comps, 1):
        ka, kb = (ha[cid], sa[cid]), (hb[cid], sb[cid])
        use_b = kb < ka or (kb == ka and fitter_is_b)
        if use_b:
            took_b += 1
            for v in comp:
                child[v] = B[v]
        else:
            took_a += 1
    equals_parent = took_a == 0 or took_b == 0
    return child, q, equals_parent


# ------------------------------------------------------------------- polish

class PolishV3:
    """B1/B2/B5 polish with v2's call contract: (assign01, wcnf, ls_cfg, seed) -> (assign01, steps, noops)."""

    def __init__(self, vc: Dict[str, Any], wcnf, stats: V3Stats) -> None:
        self.vc = vc
        self.wcnf = wcnf
        self.stats = stats
        self.dw = init_dynamic_weights(wcnf) if (vc["core"] == "dls" and vc["weights"] == "run") else None
        self.native = None
        if vc["native"]:
            from native.native import load_native
            self.native = load_native(wcnf)   # raises NativeUnavailable
        stats.d["polish_core"] = vc["core"] + ("" if vc["tabu"] == "none" else "+" + vc["tabu"])
        stats.d["ls_native"] = bool(vc["native"])

    def __call__(self, assign01: List[bool], ls_cfg: Dict[str, Any], rng_seed: int,
                 hard_mode: bool) -> Tuple[List[bool], int, int]:
        vc, s = self.vc, self.stats.d
        start = [bool(b) for b in assign01[1:]]
        max_flips = ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips", None))
        tl = ls_cfg.get("time_limit_s", 0.05)
        st: Dict[str, int] = {}
        if self.native is not None:
            res = self.native.polish(vc, start, rng_seed, max_flips, tl, ls_cfg.get("noise", 0.10),
                                     hard_mode, self.dw, st)
        elif vc["core"] == "dls":
            res = dls_v3(self.wcnf, start, rng=MTRng(rng_seed), max_flips=max_flips, time_limit_s=tl,
                         t=vc["dls_t"], sp=vc["dls_sp"], zeta=vc["dls_zeta"], h_inc=vc["dls_h_inc"],
                         dw=self.dw, cc=vc["tabu"] == "cc", stats=st)
        else:
            res = walksat_v3(self.wcnf, start, rng=MTRng(rng_seed), max_flips=max_flips, time_limit_s=tl,
                             noise=ls_cfg.get("noise", 0.10), hard_safe=True if hard_mode else ls_cfg.get("hard_safe", True),
                             budget_counts_noops=hard_mode, tabu=vc["tabu"], tenure=vc["tabu_tenure"],
                             tenure_rand=vc["tabu_tenure_rand"], stats=st)
        for k2, v2 in st.items():
            s[k2] = s.get(k2, 0) + v2
        return [False] + [bool(b) for b in res["final_assign"]], res["flips"], res.get("noop_steps", 0)


__all__ = [
    "check_cfg", "v3_cfg", "resolve_hard_mode", "custom_polish", "V3Stats", "mutate_v3",
    "partition_crossover", "px_components", "PolishV3", "PortableRng",
]
