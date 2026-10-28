#!/usr/bin/env python3
"""Twin check of the compact instance (docs/current2/COMPILED_MEMETIC_PLAN.md C1).

For each instance file: the C parser against WCNF.parse_dimacs (every clause),
the C tables against NativeCore's Python-built ones (full and lean, every array),
and the once-per-run C passes against the Python functions (counts, screen, JW
priors, nbrs bound, evaluation on random assignments). Workstation only.

    python3 scripts/compact_check.py                 # every .wcnf/.cnf under data/
    python3 scripts/compact_check.py FILE [FILE...]
Exit 0 iff no mismatch. tests/test_compact.py runs the same checks on a sample.
"""
from __future__ import annotations

import ctypes as C
import os
import random
import sys
from typing import List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from sat.cnf import WCNF  # noqa: E402
from sat import compact as cpt  # noqa: E402


def _arr(p, k) -> list:
    return list(p[:k]) if k > 0 else []


def table_arrays(core) -> dict:
    I, n, m = core.inst, core.n, core.m
    d = {"lit_off": _arr(I.lit_off, m + 1)}
    d["lits"] = _arr(I.lits, d["lit_off"][-1])
    d["is_hard"] = _arr(I.is_hard, m)
    d["w"] = _arr(I.w, m)
    d["occ_off"] = _arr(I.occ_off, n + 2)
    k = d["occ_off"][-1]
    d["occ_ci"], d["occ_d"] = _arr(I.occ_ci, k), _arr(I.occ_d, k)
    d["cvd_off"] = _arr(I.cvd_off, m + 1)
    k = d["cvd_off"][-1]
    d["cvd_u"], d["cvd_d"] = _arr(I.cvd_u, k), _arr(I.cvd_d, k)
    d["lean"] = not bool(I.nb_off)
    if I.nb_off:
        d["nb_off"] = _arr(I.nb_off, n + 2)
        d["nb"] = _arr(I.nb, d["nb_off"][-1])
    else:
        d["aocc_off"] = _arr(I.aocc_off, n + 2)
        d["aocc_ci"] = _arr(I.aocc_ci, d["aocc_off"][-1])
        d["cv_off"] = _arr(I.cv_off, m + 1)
        d["cv_u"] = _arr(I.cv_u, d["cv_off"][-1])
    d["total_soft"], d["has_hard"] = int(I.total_soft), int(I.has_hard)
    return d


def check_parse(path: str, w: WCNF, cw) -> List[str]:
    bad = []
    for k in ("n_vars", "hard_weight", "is_wcnf"):
        if getattr(w, k) != getattr(cw, k):
            bad.append(f"{k}: {getattr(w, k)} != {getattr(cw, k)}")
    if len(w.clauses) != len(cw.clauses):
        bad.append(f"m: {len(w.clauses)} != {len(cw.clauses)}")
        return bad
    for i, (a, b) in enumerate(zip(w.clauses, cw.clauses)):
        if a != b:
            bad.append(f"clause {i}: {a} != {b}")
            break
    return bad


def check_tables(w: WCNF, cw) -> List[str]:
    from native.native import NativeCore
    from sat import ls_v3
    from sat.ls_v3 import set_nbrs_mode
    bad = []
    modes = ("full", "lean") if cw.nbrs_bound() <= ls_v3.NBRS_MAX else ("lean",)  # rail: full needs ~10 GB
    for mode in modes:
        set_nbrs_mode(w, mode)
        a = table_arrays(NativeCore(w))
        b = table_arrays(NativeCore.from_compact(cw, lean=(mode == "lean")))
        for k in a:
            if a[k] != b.get(k):
                bad.append(f"tables[{mode}].{k} differ")
    set_nbrs_mode(w, "auto")
    return bad


def check_passes(w: WCNF, cw, seeds=(1, 2, 3)) -> List[str]:
    from evo.population import jw_priors, evaluate_assignment
    from evo import auto_hparams as ahp
    from sat import kernel as kern, ls_v3
    from cli.run_memetic_shard import instance_stats, score_assignment
    bad = []
    if ahp._soft_stats(w) != ahp._soft_stats(cw):
        bad.append(f"_soft_stats {ahp._soft_stats(w)} != {ahp._soft_stats(cw)}")
    if instance_stats(w) != instance_stats(cw):
        bad.append("instance_stats")
    if kern.screen_frac(w) != kern.screen_frac(cw):
        bad.append(f"screen_frac {kern.screen_frac(w)} != {kern.screen_frac(cw)}")
    if ls_v3.nbrs_plan(w) != ls_v3.nbrs_plan(cw):
        bad.append("nbrs_plan")
    if max((len(c.lits) for c in w.clauses), default=0) != cw.counts()["max_len"]:
        bad.append("max_len")
    if sum(float(c.weight) for c in w.clauses if not c.is_hard) != cw.soft_weight_float():
        bad.append("soft weight float")
    pa, pb = jw_priors(w), cw.jw_priors()
    if list(pa) != list(pb):
        bad.append("jw_priors")
    for s in seeds:
        r = random.Random(s)
        a = [False] + [r.random() < 0.5 for _ in range(w.n_vars)]
        if evaluate_assignment(w, a) != evaluate_assignment(cw, a):
            bad.append(f"evaluate seed {s}")
        if score_assignment(w, a) != score_assignment(cw, a):
            bad.append(f"score seed {s}")
        sat_py = sum(1 for cl in w.clauses if any((l > 0) == a[abs(l)] for l in cl.lits))
        if sat_py != cw.evaluate(a)[4]:
            bad.append(f"satisfied count seed {s}")
    return bad


def check_file(path: str, tables: bool = True) -> List[str]:
    try:
        w = WCNF.parse_dimacs(path)
    except Exception as e:  # both must refuse
        try:
            cpt.load(path)
        except ValueError:
            return []
        return [f"python refused ({type(e).__name__}: {e}), C accepted"]
    try:
        cw = cpt.load(path)
    except ValueError as e:
        return [f"C refused ({e}), python accepted"]
    bad = check_parse(path, w, cw)
    if bad:
        return bad
    if tables:
        bad += check_tables(w, cw)
    bad += check_passes(w, cw)
    return bad


def all_files() -> List[str]:
    out = []
    for d, _, fs in os.walk(os.path.join(ROOT, "data")):
        for f in fs:
            if f.endswith((".wcnf", ".cnf")):
                out.append(os.path.join(d, f))
    return sorted(out)


def main(argv=None) -> int:
    files = (argv if argv else None) or all_files()
    n_bad = 0
    for i, p in enumerate(files, 1):
        bad = check_file(p)
        if bad:
            n_bad += 1
            print(f"MISMATCH {os.path.relpath(p, ROOT)}: {bad[:3]}")
        if i % 50 == 0:
            print(f"... {i}/{len(files)}", flush=True)
    print(f"{len(files)} files, {n_bad} with a mismatch")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
