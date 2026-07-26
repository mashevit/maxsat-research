"""The provider seam: State, Advice, Provider, apply_advice, NoopProvider.

Ported from `src/llm/advisor.py` @ 1e3eaaf (`LLMAdvice` -> `Advice`,
`apply_advice` at `:41`) and `src/llm/providers/noop.py` @ 1e3eaaf
(`NoopProvider`).

Dropped per PORT_NOTES §3: `LLMAdvisor` (`advisor.py:67`) and `src/llm/prompt.py`
entirely — the two-layer `complete(str) -> str` plus JSON-parse machinery is
LLM-only. PORT_NOTES §5 flattens the seam to `propose(state) -> Advice`; a future
LLM provider hides prompt-build + `complete` + parse *inside* its own `propose`,
and the seam itself does not change.

Out of scope for this step (PORT_NOTES §10): `RandomPerturbationProvider` and
`_provider_seed` (step 11); `build_state` and the `run_memetic` per-child hook
(step 7).

Self-contained: stdlib only. No import from `src/`, and none from the rest of
`maxsat_new` either — `State` carries plain tuples.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Tuple


@dataclass(frozen=True)
class State:
    """Read-only snapshot handed to a provider (PORT_NOTES §5).

    Distinct from `state.SatState`, which is the internal incremental
    bookkeeping used by `walksat_polish` and is never exposed here.

    `assign` is an immutable tuple so a provider cannot mutate solver state;
    edits come back only via `Advice`. `violated_hard` comes straight from
    `hardviol.violated_hard_clauses` — global clause indices — and is a
    first-class member because it is the field the future LoRA training set
    reads.
    """

    assign: Tuple[bool, ...]                          # 1-based; index 0 unused
    violated_hard: Tuple[Tuple[int, Tuple[int, ...]], ...]  # (clause_idx, lits)
    cost: int                                         # unsat soft weight, lower better
    n_hard_violations: int                            # == len(violated_hard)
    generation: int                                   # EA generation of this child
    seed: int                                         # the run's master seed
    n_vars: int                                       # == len(assign) - 1


@dataclass(frozen=True)
class Advice:
    """What a provider returns.

    Field-for-field `src/llm/advisor.py:LLMAdvice` (`:8`) @ 1e3eaaf; the only
    change is `List` -> `Tuple`, so the dataclass can be frozen. `note` is
    logged, never acted on — `apply_advice` does not read it.
    """

    flip_vars: Tuple[int, ...] = ()   # variable indices to flip
    set_true: Tuple[int, ...] = ()    # force True
    set_false: Tuple[int, ...] = ()   # force False
    note: str = ""                    # free-text reason


class Provider(Protocol):
    """The seam. Flattened from `LLMProvider` + `LLMAdvisor` (PORT_NOTES §5)."""

    def propose(self, state: State) -> Advice:
        ...


def apply_advice(assign01: List[bool], advice: Advice) -> List[bool]:
    """Applies advice to a 1-based assignment (index 0 unused).

    Returns a new list.

    Ported verbatim from `src/llm/advisor.py:41` @ 1e3eaaf: the
    flip -> set_true -> set_false order (so a variable named twice takes the
    last write), the `v <= 0 or v >= len(out)` bounds check, and the trailing
    `out[0] = False`.

    With an empty `Advice` this returns an exact copy — no loop body runs and
    `out[0] = False` is a no-op under the §5 invariant that index 0 is unused
    and False. That is what makes `NoopProvider` a true no-op and what step 10's
    bit-identity claim rests on.
    """
    # Verbatim from advisor.py:45. `list(assign01)` would additionally accept a
    # tuple (e.g. State.assign); not deviating from the pin — callers pass the
    # child's list, per PORT_NOTES §6.
    out = assign01[:]

    for v in advice.flip_vars:
        if v <= 0 or v >= len(out):
            continue
        out[v] = not out[v]

    for v in advice.set_true:
        if v <= 0 or v >= len(out):
            continue
        out[v] = True

    for v in advice.set_false:
        if v <= 0 or v >= len(out):
            continue
        out[v] = False

    out[0] = False
    return out


class NoopProvider:
    """Ported from `src/llm/providers/noop.py` @ 1e3eaaf.

    The source returned the JSON literal
    `{"flip": [], "set_true": [], "set_false": [], "note": "noop"}`, which the
    dropped `LLMAdvisor` parsed into an empty `LLMAdvice`. The flattened seam
    returns that empty advice directly. Per PORT_NOTES §5 the `note` is left
    empty rather than carrying `"noop"`; the note is logged, never acted on, so
    this cannot affect a run.
    """

    def propose(self, state: State) -> Advice:
        return Advice()  # empty -> apply_advice is identity
