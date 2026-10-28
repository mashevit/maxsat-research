"""Loader for the C polish core (B5): src/native/ls_core.c, built by scripts/build_native.sh.

docs/current2/STRONGER_MEMETIC_DESIGN.md §7 (repo). The shared library is built
ONCE per tree (on the cluster: a separate job, scripts/build_native.sbatch, or
the login node, since it is plain gcc), into src/native/build/ together with
BUILD_INFO.txt (sha256 of the source and of the .so, gcc version, host, date).

`build_info()` refuses a stale or missing build -- the source hash recorded at
build time must equal the current ls_core.c -- so a shard with `ls.native: true`
never runs a core compiled from other code. The directory can be redirected with
MAXSAT_NATIVE_BUILD_DIR (tests).

TARGET HIT (2026-10-28, docs/current2/MSE26_RHO_PLAN.md §7). `target_unsat`
(the known optimum as unsatisfied soft weight, in this instance's own units --
the kernel's on the kernel path) makes each call report the first step at which
the true cost reached it: `target_hit_step` (0 = the start, -1 = never) and
`target_hit_wall` (time.time() at that moment, None = never). Observed only;
the flips are the same with or without it.
"""
from __future__ import annotations

import ctypes as C
import hashlib
import os
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "ls_core.c")
SO_NAME = "libls_core.so"


class NativeUnavailable(RuntimeError):
    pass


def build_dir() -> str:
    return os.environ.get("MAXSAT_NATIVE_BUILD_DIR", os.path.join(HERE, "build"))


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_info() -> Dict[str, str]:
    d = build_dir()
    so, info = os.path.join(d, SO_NAME), os.path.join(d, "BUILD_INFO.txt")
    if not (os.path.isfile(so) and os.path.isfile(info)):
        raise NativeUnavailable(f"no build in {d} (run scripts/build_native.sh)")
    rec: Dict[str, str] = {}
    with open(info, encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                rec[k.strip()] = v.strip()
    src_now = _sha256(SOURCE)
    if rec.get("source_sha256") != src_now:
        raise NativeUnavailable(f"stale build: built from {rec.get('source_sha256', '?')[:12]}, "
                                f"source is {src_now[:12]} (rebuild with scripts/build_native.sh)")
    so_now = _sha256(so)
    if rec.get("so_sha256") != so_now:
        raise NativeUnavailable("the .so does not match BUILD_INFO.txt (rebuild)")
    return rec


class _Inst(C.Structure):
    _fields_ = [
        ("n", C.c_int32), ("m", C.c_int32),
        ("lit_off", C.POINTER(C.c_int32)), ("lits", C.POINTER(C.c_int32)),
        ("is_hard", C.POINTER(C.c_uint8)), ("w", C.POINTER(C.c_int64)),
        ("occ_off", C.POINTER(C.c_int32)), ("occ_ci", C.POINTER(C.c_int32)), ("occ_d", C.POINTER(C.c_int32)),
        ("cvd_off", C.POINTER(C.c_int32)), ("cvd_u", C.POINTER(C.c_int32)), ("cvd_d", C.POINTER(C.c_int32)),
        ("nb_off", C.POINTER(C.c_int32)), ("nb", C.POINTER(C.c_int32)),
        ("total_soft", C.c_int64), ("has_hard", C.c_int32),
        # lean tables (nb_off == NULL): aocc = every clause of v, cv = distinct variables of c
        ("aocc_off", C.POINTER(C.c_int32)), ("aocc_ci", C.POINTER(C.c_int32)),
        ("cv_off", C.POINTER(C.c_int32)), ("cv_u", C.POINTER(C.c_int32)),
    ]


_LIB = None


def _lib():
    global _LIB
    if _LIB is None:
        build_info()
        lib = C.CDLL(os.path.join(build_dir(), SO_NAME))
        I64P = C.POINTER(C.c_int64)
        lib.ls_walksat.argtypes = [C.POINTER(_Inst), C.POINTER(C.c_uint8), C.c_uint64, C.c_int64, C.c_double,
                                   C.c_double, C.c_int, C.c_int, C.c_int, C.c_int64, C.c_int64, C.c_int64,
                                   I64P]
        lib.ls_walksat.restype = C.c_int
        lib.ls_dls.argtypes = [C.POINTER(_Inst), C.POINTER(C.c_uint8), C.c_uint64, C.c_int64, C.c_double,
                               C.c_int64, C.c_double, C.c_int64, C.c_int64, I64P, C.c_int, C.c_int64, I64P]
        lib.ls_dls.restype = C.c_int
        lib.rng_stream.argtypes = [C.c_uint64, C.c_int64, C.POINTER(C.c_uint64)]
        lib.rng_stream.restype = None
        _LIB = lib
    return _LIB


def rng_stream(seed: int, count: int) -> List[int]:
    buf = (C.c_uint64 * count)()
    _lib().rng_stream(C.c_uint64(seed), count, buf)
    return list(buf)


def _target_arg(target_unsat: Optional[int]) -> int:
    return -1 if target_unsat is None or target_unsat < 0 else int(target_unsat)


def _hit(out, t_call: float) -> Dict[str, Any]:
    step, ns = int(out[7]), int(out[8])
    return {"target_hit_step": step, "target_hit_wall": None if step < 0 else t_call + ns * 1e-9}


def _arr(ctype, xs):
    return (ctype * max(1, len(xs)))(*xs)


class NativeCore:
    """The instance flattened once; polish calls marshal only the assignment."""

    _ATTR = "_native_core"

    def __init__(self, wcnf) -> None:
        from sat.walksat_v2 import _static_for
        from sat.ls_v3 import v3_static
        self.lib = _lib()
        st, x = _static_for(wcnf), v3_static(wcnf)
        n, m = st.n, st.m
        self.n, self.m = n, m
        self.x = x   # the tables this core was flattened from (load_native rebuilds if they change)
        lit_off, lits = [0], []
        for c in range(m):
            lits.extend(st.lits[c])
            lit_off.append(len(lits))
        occ_off, occ_ci, occ_d = [0, 0], [], []
        for v in range(1, n + 1):
            for ci, d in st.occ[v]:
                occ_ci.append(ci)
                occ_d.append(d)
            occ_off.append(len(occ_ci))
        cvd_off, cvd_u, cvd_d = [0], [], []
        for c in range(m):
            for u, d in x.cvd[c]:
                cvd_u.append(u)
                cvd_d.append(d)
            cvd_off.append(len(cvd_u))
        nb_off, nb = [0, 0], []
        aocc_off, aocc_ci, cv_off, cv_u = [0, 0], [], [0], []
        if x.nbrs is not None:
            for v in range(1, n + 1):
                nb.extend(x.nbrs[v])
                nb_off.append(len(nb))
        else:   # lean: CC reads the clauses (ls_core.c cc_touch)
            for v in range(1, n + 1):
                aocc_ci.extend(x.aocc[v])
                aocc_off.append(len(aocc_ci))
            for c in range(m):
                cv_u.extend(x.cv[c])
                cv_off.append(len(cv_u))
        # keep the buffers alive as attributes
        self._bufs = [
            _arr(C.c_int32, lit_off), _arr(C.c_int32, lits),
            _arr(C.c_uint8, [1 if h else 0 for h in st.is_hard]), _arr(C.c_int64, st.w),
            _arr(C.c_int32, occ_off), _arr(C.c_int32, occ_ci), _arr(C.c_int32, occ_d),
            _arr(C.c_int32, cvd_off), _arr(C.c_int32, cvd_u), _arr(C.c_int32, cvd_d),
            _arr(C.c_int32, nb_off), _arr(C.c_int32, nb),
            _arr(C.c_int32, aocc_off), _arr(C.c_int32, aocc_ci), _arr(C.c_int32, cv_off), _arr(C.c_int32, cv_u),
        ]
        b = self._bufs
        lean = x.nbrs is None
        I32P = C.POINTER(C.c_int32)
        self.inst = _Inst(n, m, b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9],
                          I32P() if lean else b[10], I32P() if lean else b[11],
                          int(st.total_soft), 1 if st.has_hard else 0,
                          b[12] if lean else I32P(), b[13] if lean else I32P(),
                          b[14] if lean else I32P(), b[15] if lean else I32P())
        self.total_soft = int(st.total_soft)

    # ------------------------------------------------------------------ cores
    def walksat(self, start: List[bool], seed: int, max_flips: Optional[int], time_limit_s: Optional[float],
                noise: float = 0.10, hard_safe: bool = True, budget_counts_noops: bool = False,
                tabu: str = "none", tenure: int = 10, tenure_rand: int = 0,
                stats: Optional[Dict[str, int]] = None, target_unsat: Optional[int] = None) -> Dict[str, Any]:
        n = self.n
        if max_flips is None:
            max_flips = max(2_000, min(50_000, 10 * n))
        A = (C.c_uint8 * (n + 1))(0, *[1 if b else 0 for b in start])
        out = (C.c_int64 * 9)()
        tl = -1.0 if (time_limit_s is None or time_limit_s == float("inf")) else float(time_limit_s)
        mode = {"none": 0, "tenure": 1, "cc": 2}[tabu]
        t_call = time.time()
        rc = self.lib.ls_walksat(C.byref(self.inst), A, C.c_uint64(seed), int(max_flips), tl, float(noise),
                                 1 if hard_safe else 0, 1 if budget_counts_noops else 0, mode,
                                 int(tenure), int(tenure_rand), _target_arg(target_unsat), out)
        if rc != 0:
            raise MemoryError("ls_walksat allocation failed")
        if stats is not None:
            for k, i in (("tabu_skips", 4), ("tabu_aspirations", 5), ("tabu_all_blocked", 6)):
                stats[k] = stats.get(k, 0) + int(out[i])
        return {"flips": int(out[0]), "total_flips": int(out[1]), "best_soft_weight": float(out[2]),
                "hard_violations": int(out[3]), "final_assign": [bool(A[v]) for v in range(1, n + 1)],
                "noop_steps": int(out[0] - out[1]), "impl": "walksat_v3_native/1", **_hit(out, t_call)}

    def dls(self, start: List[bool], seed: int, max_flips: Optional[int], time_limit_s: Optional[float],
            t: int = 15, sp: float = 0.01, zeta: int = 50, h_inc: int = 1, dw: Optional[List[int]] = None,
            cc: bool = False, stats: Optional[Dict[str, int]] = None,
            target_unsat: Optional[int] = None) -> Dict[str, Any]:
        n, m = self.n, self.m
        if max_flips is None:
            max_flips = max(2_000, min(50_000, 10 * n))
        A = (C.c_uint8 * (n + 1))(0, *[1 if b else 0 for b in start])
        out = (C.c_int64 * 9)()
        tl = -1.0 if (time_limit_s is None or time_limit_s == float("inf")) else float(time_limit_s)
        dwbuf = None
        if dw is not None:
            if len(dw) != m:
                raise ValueError("dw must have one entry per clause")
            dwbuf = (C.c_int64 * max(1, m))(*dw)
        t_call = time.time()
        rc = self.lib.ls_dls(C.byref(self.inst), A, C.c_uint64(seed), int(max_flips), tl, int(t), float(sp),
                             int(zeta), int(h_inc), dwbuf, 1 if cc else 0, _target_arg(target_unsat), out)
        if rc != 0:
            raise MemoryError("ls_dls allocation failed")
        if dw is not None:
            dw[:] = list(dwbuf)[:m]
        if stats is not None:
            for k, i in (("dls_stuck", 4), ("dls_smooths", 5), ("dls_cc_blocked", 6)):
                stats[k] = stats.get(k, 0) + int(out[i])
        return {"flips": int(out[0]), "total_flips": int(out[1]), "hard_violations": int(out[2]),
                "best_soft_weight": float(self.total_soft - out[3]),
                "final_assign": [bool(A[v]) for v in range(1, n + 1)], "noop_steps": 0,
                "impl": "dls_v3_native/1", **_hit(out, t_call)}

    def polish(self, vc: Dict[str, Any], start: List[bool], seed: int, max_flips, time_limit_s, noise,
               hard_mode: bool, dw, stats, target_unsat: Optional[int] = None) -> Dict[str, Any]:
        if vc["core"] == "dls":
            return self.dls(start, seed, max_flips, time_limit_s, t=vc["dls_t"], sp=vc["dls_sp"],
                            zeta=vc["dls_zeta"], h_inc=vc["dls_h_inc"], dw=dw, cc=vc["tabu"] == "cc",
                            stats=stats, target_unsat=target_unsat)
        return self.walksat(start, seed, max_flips, time_limit_s, noise=noise, hard_safe=True,
                            budget_counts_noops=hard_mode, tabu=vc["tabu"], tenure=vc["tabu_tenure"],
                            tenure_rand=vc["tabu_tenure_rand"], stats=stats, target_unsat=target_unsat)


def load_native(wcnf) -> NativeCore:
    from sat.ls_v3 import v3_static
    core = getattr(wcnf, NativeCore._ATTR, None)
    if core is None or core.x is not v3_static(wcnf):
        core = NativeCore(wcnf)
        try:
            setattr(wcnf, NativeCore._ATTR, core)
        except AttributeError:
            pass
    return core
