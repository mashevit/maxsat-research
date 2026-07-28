"""Pure weighted random k-SAT generator: GenParams -> in-memory Instance.

Plan: docs/INSTANCEGEN_PLAN.md §8 (step 1 of §13).

Purity contract, and why it matters (§7):
  - no file I/O;
  - no pysat import, so determinism is testable with no solver installed;
  - no module-level `random.*` -- one random.Random(seed) threaded explicitly.
    Module-level random is the from_gemini.py:127 anti-pattern and is exactly
    what makes seeded reproduction fail.

`generate` gives no feasibility guarantee. The hard-part feasibility guard
(D8) lives in feasible.py, which imports this module and never the reverse.
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass
from random import Random
from typing import List, Tuple

# Weight-distribution names accepted by GenParams.weight_dist (§11, D4).
#   "uniform"            -- w ~ U{1..w_max}
#   "few_classes:<m>"    -- m evenly spaced weight classes, uniform over classes
#   "powerlaw:<alpha>"   -- P(w) proportional to w**-alpha on {1..w_max}
WEIGHT_DISTS = ("uniform", "few_classes", "powerlaw")


@dataclass(frozen=True)
class GenParams:
    """Frozen generator parameters.

    n_hard = round(hard_ratio * n_vars) and n_soft = round(soft_ratio * n_vars)
    are independent (§8.1): the old (clause_ratio, hard_frac) pair coupled
    feasible-region size to objective density, so §11's axis 1 and axis 3 could
    not move separately. Total density is the *derived* quantity
    clause_ratio == hard_ratio + soft_ratio.

    Field set is frozen as of §13 step 1: these fields propagate into the
    filename template and into every manifest row (§10.3), so adding one later
    forces a corpus regeneration (D4).
    """

    n_vars: int
    k: int
    soft_ratio: float
    hard_ratio: float
    w_max: int
    seed: int
    weight_dist: str = "uniform"

    @property
    def n_hard(self) -> int:
        return int(round(self.hard_ratio * self.n_vars))

    @property
    def n_soft(self) -> int:
        return int(round(self.soft_ratio * self.n_vars))

    @property
    def clause_ratio(self) -> float:
        """Derived total density; not an input (§8.1)."""
        return self.hard_ratio + self.soft_ratio


@dataclass(frozen=True)
class Clause:
    """A generated clause.

    Deliberately *not* maxsat_new.cnf.Clause: keeping the types independent is
    what makes the round-trip test (§12 test 2) compare two independently-built
    objects instead of asserting a thing equals itself.

    Hard clauses carry weight == Instance.top, matching what the old dialect
    writes and what parse_dimacs reads back.
    """

    weight: int
    lits: Tuple[int, ...]
    is_hard: bool


@dataclass(frozen=True)
class Instance:
    n_vars: int
    clauses: Tuple[Clause, ...]
    top: int

    @property
    def hard_clauses(self) -> Tuple[Clause, ...]:
        return tuple(c for c in self.clauses if c.is_hard)

    @property
    def soft_clauses(self) -> Tuple[Clause, ...]:
        return tuple(c for c in self.clauses if not c.is_hard)

    @property
    def total_soft_weight(self) -> int:
        return sum(c.weight for c in self.clauses if not c.is_hard)

    @property
    def n_distinct_weights(self) -> int:
        return len({c.weight for c in self.clauses if not c.is_hard})


def _parse_weight_dist(spec: str, w_max: int) -> Tuple[str, float]:
    """Split "name" / "name:arg" and validate. Returns (name, arg)."""
    if not isinstance(spec, str):
        raise ValueError(f"weight_dist must be a string, got {type(spec).__name__}")
    name, _, arg_s = spec.partition(":")
    if name not in WEIGHT_DISTS:
        raise ValueError(
            f"unknown weight_dist {spec!r}; expected one of "
            f'"uniform", "few_classes:<m>", "powerlaw:<alpha>"'
        )
    if name == "uniform":
        if arg_s:
            raise ValueError(f"weight_dist {spec!r}: 'uniform' takes no argument")
        return name, 0.0
    if not arg_s:
        raise ValueError(f"weight_dist {spec!r}: missing argument after ':'")
    try:
        arg = float(arg_s)
    except ValueError:
        raise ValueError(f"weight_dist {spec!r}: argument {arg_s!r} is not a number")
    if name == "few_classes":
        if arg != int(arg) or int(arg) < 1:
            raise ValueError(f"weight_dist {spec!r}: m must be an integer >= 1")
        if int(arg) > w_max:
            raise ValueError(
                f"weight_dist {spec!r}: m={int(arg)} exceeds w_max={w_max}; "
                "cannot make more distinct weight classes than weights"
            )
    elif name == "powerlaw":
        if not arg > 0.0:
            raise ValueError(f"weight_dist {spec!r}: alpha must be > 0")
    return name, arg


def _validate(p: GenParams) -> None:
    if p.n_vars < 1:
        raise ValueError(f"n_vars must be >= 1, got {p.n_vars}")
    if p.k < 1:
        raise ValueError(f"k must be >= 1, got {p.k}")
    if p.k > p.n_vars:
        raise ValueError(f"k={p.k} exceeds n_vars={p.n_vars}: cannot sample k distinct vars")
    if p.soft_ratio < 0.0:
        raise ValueError(f"soft_ratio must be >= 0, got {p.soft_ratio}")
    if p.hard_ratio < 0.0:
        raise ValueError(f"hard_ratio must be >= 0, got {p.hard_ratio}")
    # Weight 0 is banned: a "0 ..." clause line is silently dropped by
    # maxsat_new/cnf.py:57 (PORT_NOTES §9.5, audit §2), so w_max >= 1 and every
    # drawn weight >= 1.
    if p.w_max < 1:
        raise ValueError(f"w_max must be >= 1, got {p.w_max}")
    if p.n_soft == 0 and p.n_hard == 0:
        raise ValueError("degenerate params: n_hard == n_soft == 0")
    _parse_weight_dist(p.weight_dist, p.w_max)


def _few_class_weights(m: int, w_max: int) -> Tuple[int, ...]:
    """m evenly spaced weights over [1, w_max], distinct by construction."""
    if m == 1:
        return (w_max,)
    step = (w_max - 1) / (m - 1)
    ws = tuple(int(round(1 + i * step)) for i in range(m))
    # Even spacing over an integer range with m <= w_max keeps these distinct;
    # assert rather than dedupe so a rounding surprise is loud, not silent.
    assert len(set(ws)) == m, f"few_classes:{m} over w_max={w_max} collided: {ws}"
    return ws


def _powerlaw_cdf(alpha: float, w_max: int) -> List[float]:
    """Cumulative weights for P(w) ~ w**-alpha on {1..w_max}."""
    cum: List[float] = []
    total = 0.0
    for w in range(1, w_max + 1):
        total += float(w) ** (-alpha)
        cum.append(total)
    return [c / total for c in cum]


def _make_weight_sampler(p: GenParams):
    """Return f(rng) -> int in [1, w_max]. Never returns 0 (§8, §9.5)."""
    name, arg = _parse_weight_dist(p.weight_dist, p.w_max)
    if name == "uniform":
        w_max = p.w_max

        def draw_uniform(rng: Random) -> int:
            return rng.randint(1, w_max)

        return draw_uniform

    if name == "few_classes":
        classes = _few_class_weights(int(arg), p.w_max)
        n_classes = len(classes)

        def draw_few(rng: Random) -> int:
            return classes[rng.randrange(n_classes)]

        return draw_few

    cdf = _powerlaw_cdf(arg, p.w_max)

    def draw_powerlaw(rng: Random) -> int:
        # Inverse-CDF on one rng.random() draw: one RNG call per weight, stable
        # across Python versions (unlike rng.choices' internals).
        return bisect.bisect_left(cdf, rng.random()) + 1

    return draw_powerlaw


def generate(p: GenParams) -> Instance:
    """Build an Instance from params. Deterministic in p; no I/O, no pysat.

    Clause construction: k distinct variables sampled without replacement, sign
    of each literal an independent fair coin. Tautologies and duplicate literals
    are impossible by construction.

    Order: the n_hard hard clauses are generated first, then the n_soft soft
    clauses (§8). One RNG stream, no second stream for the split.
    """
    _validate(p)
    rng = Random(p.seed)
    draw_weight = _make_weight_sampler(p)
    variables = range(1, p.n_vars + 1)

    def sample_lits() -> Tuple[int, ...]:
        vs = rng.sample(variables, p.k)
        return tuple(v if rng.random() < 0.5 else -v for v in vs)

    hard_lits = [sample_lits() for _ in range(p.n_hard)]
    soft: List[Clause] = []
    for _ in range(p.n_soft):
        lits = sample_lits()
        soft.append(Clause(weight=draw_weight(rng), lits=lits, is_hard=False))

    # top = 1 + sum(soft weights) (§9). Computed after the softs are drawn, then
    # stamped onto the hard clauses so Clause.weight is what the writer emits.
    top = 1 + sum(c.weight for c in soft)
    hard = [Clause(weight=top, lits=lits, is_hard=True) for lits in hard_lits]

    return Instance(n_vars=p.n_vars, clauses=tuple(hard) + tuple(soft), top=top)


def weight_dist_slug(spec: str) -> str:
    """Filename-safe form of a weight_dist value (§10.3): ':' -> '-'."""
    return spec.replace(":", "-")


def instance_filename(p: GenParams) -> str:
    """Filename template from §10.3, one component per GenParams field.

    clause_ratio is absent on purpose: it is derived (§8.1) and would duplicate
    sr/hr.
    """
    return (
        f"wksat_v{p.n_vars}_k{p.k}"
        f"_sr{p.soft_ratio:.2f}_hr{p.hard_ratio:.2f}"
        f"_w{p.w_max}_{weight_dist_slug(p.weight_dist)}_s{p.seed}.wcnf"
    )
