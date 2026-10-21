"""Instance-aware hyperparameters for `impl: v3` (rule set `auto_hparams/2`, 2026-10-21).

RUN TIME (the normal use). A config with `hparams: auto` makes the shard
runner (src/cli/run_memetic_shard.py) call `resolve()` right after the kernel
gate, on the instance the EA will solve. The chosen values are merged into
the config in memory; nothing is written. The time counts inside the run
budget, and the record's `hparams` field holds the overrides, the reasons and
the hash of the resolved config. Only the keys below are set; every other key
comes from the batch config (configs/strong/auto.yaml = `BASE` + `hparams: auto`).

    hparams: auto                      # or, with options:
    hparams: {mode: auto, flips_c: 0, flips_cap: 1600000}

PREVIEW. `scripts/auto_hparams.py --print` runs the same `resolve()` on the
workstation, so it shows what a job will choose.

The size the rules use is the EFFECTIVE instance: the kernel when the
`preprocess: kernel` gate passes, else the original. On the sparse Max-2-SAT
grid the solver runs on 300-572-variable kernels of n 16,000-64,000 formulas,
and sizing by the nominal n would be wrong (HYPERPARAMETER_CALIBRATION_PLAN
§0d, N-2026-10-14-e).

Rules (evidence tag in brackets; "measured" = our runs, "source" = paper):

  R0  every instance: the S1 `allC` arm -- B1 cc, B2 dls, B3 walk, B4 px, B5
      native, kernel gate 0.20/0.20, pop 40, tournament 3, elitism, deadline
      clip, `hard_mode: auto` (the hard-tree machinery iff the solved instance
      has hard clauses). [measured: S1 smoke, STRONG_MEMETIC_S1_RUN §2.2]
  R1  ea.mutation_k = clamp(round(0.04 * n_eff), 2, 16). 16 is the S1 value
      (damage 6.5-12.4 clauses at n 16k-64k, kernels 300-572 vars all >= 16);
      below 400 variables it shrinks so a child stays a neighbour of its
      parent (k 2 at n 50, close to v2's 2% rate there). [measured at k 16;
      the shrink below n 400 is inference]
  R2  B2 weighting, by class of the effective instance:
      soft, unweighted     t 15, sp 0.01, zeta max(50, 49 + max kernel weight),
                           h_inc 1  [measured: S1 smoke at 50, on raw and on
                           kernels; zeta > 1 is needed without hard clauses,
                           design §3.3]
      soft, weighted       t 15, sp 0.01, zeta max(50, 49 + max soft weight),
                           h_inc 1  [inference, untested: zeta must exceed the
                           start weights or no soft weight can grow]
      "Weighted" is judged on the original instance (the kernel merges
      duplicate clauses, so the kernel of an unweighted formula has weights
      2, 3, ...); "hard" on the solved instance, as `hard_mode: auto` does.
      hard, unweighted     t 42, sp 3e-6, zeta 400, h_inc 1  [source: SATLike,
                           IJCAI 2018, PMS industrial; choosing "industrial"
                           for MSE families is inference]
      hard, weighted       t 15, sp 0.01, zeta 1, h_inc 3  [source: SATLike
                           WPMS; the paper gives sp 0.01 or 0.0001, which one
                           per class is unverified]
      hard, weighted, mean soft weight > 10,000
                           t 15, sp 0.01, zeta 500, h_inc 300  [source: SATLike]
  R3  ls_polish_flips = flip_budget = max(12500, min(c * n_eff, cap)).
      Default c = 0, i.e. 12,500 at every size: the only value measured for
      v3, and `allC` reached c* on raw n 64,000 with it (s256 53.8 s, s257
      48.2 s). The 0.8-1.6M flips/call found best in Stage L1 was measured
      under v2's 2% mutation, whose repair work grows with n; B3 removes that
      work. c > 0 is for a calibration grid. With c > 0 on a soft instance the
      call ends on flips only (`polish_cap: flips_only`, as in Stage L1); hard
      instances keep the 3.5 s slot, because feasible moves M share it.
      [measured at 12,500; c > 0 untested for v3]
  R4  hard clauses in the solved instance (`hard_mode: auto` engages the hard
      tree): ea.pop_size = 10 and hard.moves.keep_sat = ks2. [measured: batch
      KS2, 16 MSE instances x 3 seeds, 900 s: runs at the optimum m40 12,
      ks2_10 26 of 48; ks2_10 vs m10 better on 13, worse on 0; vs m40 (the
      /1 choice) better on 13, worse on 2. The pre-registered rule failed at
      pop 40 (10/3), and pop alone showed no effect; pop 10 is the user's
      choice, 2026-10-21. KS2_CHECK_RUN.md section 6]
  Other hard-tree keys (Glucose phases, repair R, moves M) keep their defaults
  (src/evo/hard.hard_cfg), the values H3 accepted.

  /1 -> /2 (2026-10-21): R4 added; soft instances resolve exactly as under /1.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

from sat import kernel as kern
from sat.cnf import WCNF

RULESET = "auto_hparams/2"
HPARAM_MODES = ("none", "auto")

GATE = {"screen_min": 0.2, "gain_min": 0.2}
FLIPS_FLOOR = 12_500
FLIPS_CAP_DEFAULT = 1_600_000
HEAVY_SOFT_MEAN = 10_000
HARD_POP_SIZE = 10           # R4
HARD_KEEP_SAT = "ks2"         # R4

BASE: Dict[str, Any] = {  # make_strong_manifest.py BASE + allC (B1-B5); R0
    "impl": "v3",
    "hard_mode": "auto",
    "preprocess": "kernel",
    "preprocess_gate": dict(GATE),
    "ea": {"enabled": True, "pop_size": 40, "tournament_k": 3, "pmutate": 0.02, "elitism": True,
           "max_gens": 1000000, "deadline_mode": "clip",
           "mutation": "walk", "mutation_k": 16, "crossover": "px", "px_min_q": 2,
           "px_fallback": "clause_aware"},
    "ls": {"ls_polish_flips": FLIPS_FLOOR, "time_limit_s": 3.5, "flip_budget": FLIPS_FLOOR,
           "tabu": "cc", "core": "dls", "dls_t": 15, "dls_sp": 0.01, "dls_zeta": 50, "dls_h_inc": 1,
           "weights": "call", "native": True},
}

DLS_BY_CLASS = {  # R2: (t, sp, zeta or None = max(50, 49 + max soft weight), h_inc, evidence)
    "soft_unweighted": (15, 0.01, None, 1, "measured: S1 smoke (allC) at 50"),
    "soft_weighted": (15, 0.01, None, 1, "inference, untested"),
    "hard_unweighted": (42, 3e-6, 400, 1, "source: SATLike PMS industrial; class choice inference"),
    "hard_weighted": (15, 0.01, 1, 3, "source: SATLike WPMS; sp choice unverified"),
    "hard_weighted_heavy": (15, 0.01, 500, 300, "source: SATLike WPMS, mean soft weight > 10,000"),
}


def hparams_opts(cfg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """None when the config has no `hparams` (or `none`); else the validated options.

    `auto` is defined for impl v3 only: under another impl the keys it sets
    (mutation_k, dls_*) would be refused or mean something else."""
    h = cfg.get("hparams")
    if h is None:
        return None
    if isinstance(h, str):
        h = {"mode": h}
    if not isinstance(h, dict):
        raise ValueError(f"hparams must be a mode string or a mapping, got {h!r}")
    unknown = sorted(set(h) - {"mode", "flips_c", "flips_cap"})
    if unknown:
        raise ValueError(f"unknown hparams keys {unknown}; known: mode, flips_c, flips_cap")
    mode = str(h.get("mode", "auto")).lower()
    if mode not in HPARAM_MODES:
        raise ValueError(f"hparams.mode must be one of {HPARAM_MODES}, got {mode!r}")
    if mode == "none":
        return None
    if str(cfg.get("impl", "")).lower() != "v3":
        raise ValueError(f"hparams: auto needs impl: v3 (got impl: {cfg.get('impl')!r})")
    opts = {"flips_c": float(h.get("flips_c", 0.0)), "flips_cap": int(h.get("flips_cap", FLIPS_CAP_DEFAULT))}
    if opts["flips_c"] < 0 or opts["flips_cap"] < FLIPS_FLOOR:
        raise ValueError(f"hparams.flips_c >= 0 and hparams.flips_cap >= {FLIPS_FLOOR} required")
    return opts


@dataclass
class Features:
    n_vars: int
    n_clauses: int
    n_hard: int
    max_len: int
    weighted: bool
    soft_w_max: int
    soft_w_mean: float
    gate: str                      # sat.kernel.gate decision, or "none" without preprocessing
    n_eff: int                     # variables the EA solves (kernel or original)
    m_eff: int
    n_hard_eff: int
    soft_w_max_eff: int

    @property
    def cls(self) -> str:
        # Hard or not: the solved instance, as `hard_mode: auto` decides. Weighted
        # or not: the ORIGINAL instance, because the kernel merges duplicate
        # clauses (weights add), so an unweighted formula has a weighted kernel.
        if self.n_hard_eff > 0:
            if not self.weighted:
                return "hard_unweighted"
            return "hard_weighted_heavy" if self.soft_w_mean > HEAVY_SOFT_MEAN else "hard_weighted"
        return "soft_weighted" if self.weighted else "soft_unweighted"


def _soft_stats(w: WCNF) -> Tuple[int, int, float, bool]:
    n_hard = 0
    w_max = w_sum = n_soft = 0
    weighted = False
    for c in w.clauses:
        if c.is_hard:
            n_hard += 1
            continue
        x = int(c.weight)
        n_soft += 1
        w_sum += x
        if x > w_max:
            w_max = x
        if x != 1:
            weighted = True
    return n_hard, w_max, (w_sum / n_soft if n_soft else 0.0), weighted


def features(wcnf: WCNF, eff: WCNF, gate: str) -> Features:
    """`eff` is the instance the EA solves (the kernel's wcnf, or `wcnf` itself)."""
    n_hard, wmax, wmean, weighted = _soft_stats(wcnf)
    h_eff, wmax_e, _, _ = (n_hard, wmax, wmean, weighted) if eff is wcnf else _soft_stats(eff)
    return Features(
        n_vars=wcnf.n_vars, n_clauses=len(wcnf.clauses), n_hard=n_hard,
        max_len=max((len(c.lits) for c in wcnf.clauses), default=0), weighted=weighted,
        soft_w_max=wmax, soft_w_mean=wmean, gate=gate,
        n_eff=eff.n_vars, m_eff=len(eff.clauses), n_hard_eff=h_eff, soft_w_max_eff=wmax_e,
    )


def mutation_k(n_eff: int) -> int:
    return max(2, min(16, round(0.04 * n_eff)))


def polish_flips(n_eff: int, c: float, cap: int) -> int:
    return max(FLIPS_FLOOR, min(int(c * n_eff), cap))


def choose(f: Features, flips_c: float = 0.0,
           flips_cap: int = FLIPS_CAP_DEFAULT) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """(overrides as a nested {"ea": {...}, "ls": {...}[, "hard": {...}]}, reason per key)."""
    k = mutation_k(f.n_eff)
    t, sp, zeta, h_inc, ev = DLS_BY_CLASS[f.cls]
    if zeta is None:
        zeta = max(50, 49 + f.soft_w_max_eff)
    flips = polish_flips(f.n_eff, flips_c, flips_cap)
    ea = {"mutation_k": k}
    ls: Dict[str, Any] = {"dls_t": t, "dls_sp": sp, "dls_zeta": int(zeta), "dls_h_inc": h_inc,
                          "ls_polish_flips": flips, "flip_budget": flips}
    if flips_c > 0 and f.n_hard_eff == 0:
        ls["polish_cap"] = "flips_only"
    out: Dict[str, Any] = {"ea": ea, "ls": ls}
    if f.n_hard_eff > 0:
        ea["pop_size"] = HARD_POP_SIZE
        out["hard"] = {"moves": {"keep_sat": HARD_KEEP_SAT}}
    why = {
        "ea.mutation_k": f"R1 clamp(round(0.04*{f.n_eff}), 2, 16) = {k}",
        "ls.dls_*": f"R2 class {f.cls}: t {t}, sp {sp}, zeta {zeta}, h_inc {h_inc} [{ev}]",
        "ls.ls_polish_flips": (f"R3 max({FLIPS_FLOOR}, min({flips_c}*{f.n_eff}, {flips_cap})) = {flips}"
                               + (", polish_cap flips_only" if "polish_cap" in ls else "")),
    }
    if "hard" in out:
        why["ea.pop_size+hard.moves.keep_sat"] = (f"R4 hard clauses in the solved instance: pop "
                                                  f"{HARD_POP_SIZE}, keep_sat {HARD_KEEP_SAT}")
    return out, why


def merge(cfg: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge: an override sets its leaf keys and keeps the config's other keys
    (hard.moves.keep_sat leaves hard.moves.per_polish etc. alone)."""
    def into(dst: Dict[str, Any], src: Dict[str, Any]) -> None:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                into(dst[k], v)
            else:
                dst[k] = copy.deepcopy(v)
    out = copy.deepcopy(cfg)
    into(out, overrides)
    return out


def cfg_hash(cfg: Dict[str, Any]) -> str:
    """Same canonical form as run_memetic_shard.config_hash."""
    canon = json.dumps(cfg, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]


@dataclass
class Resolved:
    cfg: Dict[str, Any]                       # the config with the overrides merged in
    feats: Features
    overrides: Dict[str, Any]
    reasons: Dict[str, str] = field(default_factory=dict)
    seconds: float = 0.0

    @property
    def cfg_hash(self) -> str:
        return cfg_hash(self.cfg)

    def record(self) -> Dict[str, Any]:
        """The shard record's `hparams` field."""
        return {"ruleset": RULESET, "class": self.feats.cls, "features": asdict(self.feats),
                "overrides": self.overrides, "reasons": self.reasons,
                "resolved_config_hash": self.cfg_hash, "hparams_s": round(self.seconds, 4)}


def resolve(cfg: Dict[str, Any], wcnf: WCNF, eff: WCNF, gate: str) -> Resolved:
    """What the shard runner calls after its gate; `cfg` must have `hparams: auto`."""
    t0 = time.time()
    opts = hparams_opts(cfg)
    if opts is None:
        raise ValueError("resolve() needs a config with hparams: auto")
    f = features(wcnf, eff, gate)
    ov, why = choose(f, opts["flips_c"], opts["flips_cap"])
    return Resolved(cfg=merge(cfg, ov), feats=f, overrides=ov, reasons=why, seconds=time.time() - t0)


def preview(cfg: Dict[str, Any], wcnf: WCNF) -> Resolved:
    """Workstation preview: run the gate as the shard runner would, then resolve()."""
    eff, gate = wcnf, "none"
    if kern.preprocess_mode(cfg) != "none":
        g = kern.gate(wcnf, cfg)
        gate = g.decision
        if g.kernel is not None:
            eff = g.kernel.wcnf
    return resolve(cfg, wcnf, eff, gate)


def auto_base(flips_c: float = 0.0, flips_cap: int = FLIPS_CAP_DEFAULT) -> Dict[str, Any]:
    """configs/strong/auto.yaml: BASE + hparams: auto (with options when not default)."""
    cfg = copy.deepcopy(BASE)
    cfg["hparams"] = ("auto" if (flips_c == 0.0 and flips_cap == FLIPS_CAP_DEFAULT)
                      else {"mode": "auto", "flips_c": flips_c, "flips_cap": flips_cap})
    return cfg


__all__ = ["RULESET", "BASE", "DLS_BY_CLASS", "Features", "Resolved", "hparams_opts", "features",
           "choose", "merge", "resolve", "preview", "auto_base", "mutation_k", "polish_flips", "cfg_hash"]
