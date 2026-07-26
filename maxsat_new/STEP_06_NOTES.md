# Step 06 notes — hardviol.py + providers.py (the seam)

Implements Step 6 of PORT_NOTES.md §10 (row 6: "the seam; training-set signal"),
one of the two mandatory load-bearing steps. It is **half port, half new code**.
`hardviol.py` is **new**: §3's port map row reads "new; consolidates
`population.clause_satisfied` + `SatState.unsat_hard_ids` intent", and neither
source is carried over as text — they agree on the predicate, and this module
becomes the single owner of it for the seam. `providers.py` is a **port**:
`Advice` is field-for-field `src/llm/advisor.py:LLMAdvice` (`:8`), `apply_advice`
is verbatim `src/llm/advisor.py:41`, and `NoopProvider` comes from
`src/llm/providers/noop.py`; `State` and the `Provider` protocol are new,
specified by PORT_NOTES §5. Port source sha: **`1e3eaaf`**, recorded in both
module docstrings. Dropped per §3: `LLMAdvisor` (`advisor.py:67`) and
`src/llm/prompt.py` entirely — the two-layer `complete(str) -> str` plus
JSON-parse machinery is LLM-only and the flattened seam does not need it.

## Files created
- `maxsat_new/hardviol.py` — `violated_hard_clauses` plus the private
  `_clause_satisfied` predicate. Stdlib only; consumes the WCNF structurally
  (`.clauses` / `.lits` / `.is_hard`), so it does not even import `cnf.py`.
- `maxsat_new/providers.py` — `State`, `Advice`, `Provider`, `apply_advice`,
  `NoopProvider`. Stdlib only; `State` carries plain tuples, so nothing from the
  rest of `maxsat_new` is imported.
- `maxsat_new/tests/data/hardmix.wcnf` — new fixture: hard/soft **interleaved**,
  so global and hard-only clause indices differ (see Fixture).
- `maxsat_new/tests/test_hardviol.py` — §10 row 6, first assertion (5 tests).
- `maxsat_new/tests/test_providers.py` — §10 row 6, second assertion (6 tests).

## Public surface

### `hardviol.py`

```python
def violated_hard_clauses(
    wcnf: Any, assign01: Sequence[bool]
) -> List[Tuple[int, Tuple[int, ...]]]: ...
```

**New code.** Returns `(global_clause_idx, lits)` for every violated hard clause,
ordered by ascending global index (plain enumeration order — deterministic
without sorting). `assign01` is 1-based with index 0 unused, length `n_vars + 1`
(§5). Truthiness-based, so both `[False, True, ...]` and `[0, 1, ...]` work — the
looser of the two conventions in the package, since `cnf.eval_assignment`
compares `== 1` while `population.clause_satisfied` uses truthiness. `lits` is a
fresh tuple, never a reference into `wcnf.clauses[i].lits`.

Private (not surface): `_clause_satisfied(lits, assign01) -> bool` — the same
predicate as `population.clause_satisfied` (`:90`), taking the literal list
directly instead of a clause object.

Two behaviors carried without special-casing: a hard clause with **no literals**
is vacuously violated (falls out of `_clause_satisfied` returning False on an
empty list), and there is **no bounds check** on `assign01` — a too-short
assignment raises `IndexError`, exactly as the source predicate does.

### `providers.py`

```python
@dataclass(frozen=True)
class State:                                              # NEW (§5 spec)
    assign: Tuple[bool, ...]                              # 1-based; index 0 unused
    violated_hard: Tuple[Tuple[int, Tuple[int, ...]], ...] # (clause_idx, lits)
    cost: int                                             # unsat soft weight, lower better
    n_hard_violations: int                                # == len(violated_hard)
    generation: int                                       # EA generation of this child
    seed: int                                             # the run's master seed
    n_vars: int                                           # == len(assign) - 1

@dataclass(frozen=True)
class Advice:                                             # PORTED: advisor.py:8
    flip_vars: Tuple[int, ...] = ()
    set_true:  Tuple[int, ...] = ()
    set_false: Tuple[int, ...] = ()
    note: str = ""

class Provider(Protocol):                                 # NEW (§5 spec)
    def propose(self, state: State) -> Advice: ...

def apply_advice(assign01: List[bool], advice: Advice) -> List[bool]: ...
                                                          # PORTED VERBATIM: advisor.py:41

class NoopProvider:                                       # PORTED: providers/noop.py
    def propose(self, state: State) -> Advice:
        return Advice()
```

**Ported verbatim:** `apply_advice`'s whole body — the flip → set_true →
set_false order, the `v <= 0 or v >= len(out)` bounds check, `out = assign01[:]`,
and the trailing `out[0] = False`. **Ported field-for-field:** `Advice`; the only
change is `List` → `Tuple` so the dataclass can be frozen, and `note` remains
logged-but-never-acted-on (`apply_advice` does not read it). **New:** `State`
(§5's snapshot; field order as §5 lists it, no defaults, so a malformed snapshot
is a `TypeError` at step 7 rather than a silent zero) and the `Provider` protocol
(§5's flattening of `LLMProvider` + `LLMAdvisor` into one method).

`State` fields are declared exactly in §5's order. `State.assign` is an immutable
tuple so a provider cannot mutate solver state; edits come back only via `Advice`.

## The three rulings and how they landed

### Ruling 1 — `idx` is the GLOBAL clause index

`violated_hard_clauses` returns the index of the clause in `wcnf.clauses` — the
single flat, file-ordered list where hard and soft clauses are **enumerated
together**. On `hardmix.wcnf` the hard clauses are at 1, 3, 4: the same numbers
you get counting every clause line in the file, soft included.

A hard-only local index (position within `[cl for cl in wcnf.clauses if
cl.is_hard]`) was **rejected**, for three reasons:

1. `SatState.unsat_hard_ids` (`src/sat/state.py:301`) already returns global
   indices — it enumerates `self.clauses`, the unified list, and filters on
   `c.is_hard` without renumbering. Half the "intent" §3 tells us to consolidate
   is therefore already global.
2. The only real *consumer* of these indices, `src/llm/prompt.py:
   extract_clause_examples`, resolves them with `clauses = wcnf.clauses; cl =
   clauses[idx]`. A local index handed to it silently reads the wrong clause —
   no crash, just wrong literals in the training-set row.
3. §5 makes `violated_hard` "the load-bearing field the future LoRA training set
   reads". That row has to be resolvable back against the instance file, and only
   a global index is.

The other half of the intent disagrees: the dead LLM block sketched
`violated_idxs = [i for i, sat in enumerate(tmp_child.hard_satisfied) if not sat]`
(`src/evo/memetic.py:100`), and `hard_satisfied` is indexed over the hard-only
sublist (`population.py:154`). That is the local convention, and feeding it to
`extract_clause_examples` would have been a live bug the moment a soft clause
preceded a hard one. It is **deliberately not replicated**; the reason is recorded
in the `hardviol.py` docstring so it is not "fixed" back later.

### Ruling 2 — return `list[tuple[int, tuple[int, ...]]]`

Outer container is a **list**, matching §10 row 6's signature
(`violated_hard_clauses(wcnf, assign01) -> [(idx, lits)]`). Inner `lits` is a
**tuple**, matching §5's `State.violated_hard` element type
`tuple[tuple[int, tuple[int,...]], ...]`. So step 7's `build_state` needs exactly
one `tuple(...)` wrap on the outer list and no deep conversion — the elements are
already in their final immutable form. Freezing happens downstream, at the
`State` boundary, which is where §5 puts it.

The inner tuple is also a **copy**, not `wcnf.clauses[i].lits` itself: a provider
holding a `State` must not be able to reach through it and mutate the instance.
Asserted by `test_lits_are_tuples_and_not_aliased`.

### Ruling 3 — copy semantics in `apply_advice`

**The original uses `out = assign01[:]`** (`src/llm/advisor.py:45`), not
`list(assign01)`. The port replicates `assign01[:]` verbatim, with the difference
recorded as an inline comment rather than a change:

```python
# Verbatim from advisor.py:45. `list(assign01)` would additionally accept a
# tuple (e.g. State.assign); not deviating from the pin — callers pass the
# child's list, per PORT_NOTES §6.
out = assign01[:]
```

The two **do** differ on a tuple input: `tuple[:]` returns a tuple, and the next
`out[v] = ...` would raise `TypeError: 'tuple' object does not support item
assignment`, whereas `list(...)` would silently succeed and return a list. That
difference is unreachable on the §6 pipeline — `apply_advice` is called on
`child`, a list, never on `state.assign` — and the pin wins regardless. Noted, not
acted on.

## The identity guarantee

`apply_advice(x, Advice())` returns an exact copy of `x`. Step by step:

1. `out = assign01[:]` — a **new** list, element-wise equal to `x`, with
   `out is not x`. Every element is a `bool`/`int`, so no element is shared by
   reference either.
2. All three loops iterate `()`. Zero iterations, zero writes: the bounds check
   and the flip/set logic are never reached, so no field of `Advice` other than
   its emptiness can matter. `note` is not read at all.
3. `out[0] = False` is the only write, and it is a **no-op exactly when `x[0]` is
   already falsy** — which is the §5 invariant ("index 0 unused") and is what
   every producer in the package constructs (`state.py:__post_init__` builds
   `[False] + [...]`; the test assignments are `[0, ...]`).

Hence `out == x` and `out is not x`: value identity, no aliasing, caller's list
untouched. Asserted in all three parts by `test_empty_advice_is_identity`.

The precondition in (3) is the only crack and it is not a practical one: variable
0 does not exist, and no clause evaluation ever reads index 0 (`clause_satisfied`
only indexes `abs(lit)` for `lit != 0`). Even given `x[0] is True`, the returned
list would differ from `x` only at a position no solver code reads — cost, hard
violations and any assignment hash over `1..n_vars` are unchanged.

This is what makes `NoopProvider` a **true** no-op: `propose` returns `Advice()`,
`apply_advice` returns a copy, and the §6 per-child pipeline
(`build_state → propose → apply_advice`) therefore perturbs neither the child bits
nor the EA's RNG stream (the provider call draws no EA randomness). That is the
whole basis of §10 step 8's / step 10's bit-identity claim — `llm_guided_base` +
`NoopProvider` must equal `memetic_ea` on both `best_cost` and
`best_assignment_hash`. `test_noop_provider_composes_to_identity` asserts the
composed path, not just the pieces.

## Fixture

`mini.wcnf` **does** have hard clauses (`top=100`, three `100 …` lines), so the
§9.6 all-soft trap does not bite here — a `.cnf` would have been fatal, since
`cnf.py` loads every `.cnf` clause as soft/weight-1/never-hard, making
`violated_hard_clauses` return `[]` for **every** assignment and the step-6
assertion vacuously true. But `mini.wcnf`'s hard clauses sit at global indices
**0, 1, 2**, which are exactly the hard-sublist indices 0, 1, 2 — on that
instance ruling 1 is untestable. Hence a second fixture.

`maxsat_new/tests/data/hardmix.wcnf`, verbatim:

```
c interleaved hard/soft WCNF for maxsat_new step 6 (pins hardviol's index space)
c 4 vars, 6 clauses; weight >= top (100) is hard
c hard clauses sit at GLOBAL idx 1, 3, 4 -> hard-only-sublist idx would be 0, 1, 2
p wcnf 4 6 100
5 1 2 0
100 -1 3 0
2 -2 0
100 2 4 0
100 -4 0
3 1 -3 0
```

Global layout: idx0 soft `[1,2]` w5, **idx1 hard** `[-1,3]`, idx2 soft `[-2]` w2,
**idx3 hard** `[2,4]`, **idx4 hard** `[-4]`, idx5 soft `[1,-3]` w3. Hard at global
1, 3, 4 vs sublist 0, 1, 2 — disjoint, so a local-index implementation cannot
accidentally pass.

Known assignment `assign01 = [False, True, False, False, True]`
(x1=T, x2=F, x3=F, x4=T):

| idx | kind | lits | evaluation | result |
|---|---|---|---|---|
| 1 | hard | `[-1, 3]` | `-1` false (x1=T), `3` false (x3=F) | **VIOLATED** |
| 3 | hard | `[2, 4]` | `2` false (x2=F), `4` true (x4=T) | satisfied |
| 4 | hard | `[-4]` | `-4` false (x4=T) | **VIOLATED** |

Expected: `[(1, (-1, 3)), (4, (-4,))]` — a strict, **non-contiguous, non-prefix**
subset that skips a satisfied hard clause between two violated ones, and includes
a unit hard clause. Cross-check: `eval_assignment` on the same input gives
`(110, 2, 0)` — `sat_w = 5 + 2 + 100 + 3`, `hard_v = 2`, `soft_v = 0`.

No line begins with `0` or `%`, so the §9.5 comment/skip filter eats nothing.

## Test design

What each assertion catches if the code were wrong.

`test_hardviol.py`:

- **`test_violated_hard_clauses_global_index`** — the load-bearing one. Asserts
  the structural premise first (`[i for i, cl in enumerate(wcnf.clauses) if
  cl.is_hard] == [1, 3, 4]`), then the result. Catches hard-sublist indexing
  (would give `0, 2`), returning *all* hard clauses (would include idx3),
  leaking soft clauses (idx0/2/5), dropping the unit hard clause, an inverted
  sign convention on negative literals (idx3 and idx4 would swap in/out), and
  `lits` returned as a list or in some internal repr instead of a raw-DIMACS
  tuple.
- **`test_agrees_with_eval_assignment`** — the count is derived two ways
  (`hardviol`'s predicate and `cnf.eval_assignment`'s independently-written
  `== 1` comparison) and must agree: `(110, 2, 0)` and `len(result) == hard_v`.
  Catches the two predicates drifting apart, which no single-module test would.
- **`test_no_violations_returns_empty`** — all hard satisfied → `[]`. Also pins
  the 0/1-int truthiness contract, since it reuses the exact assignment
  `[0, 1, 0, 0, 1, 1]` already asserted in `test_cnf.py` (`hard_v == 0`).
  Catches a satisfied hard clause being reported, and a predicate that only
  accepts `bool`.
- **`test_first_clause_violated`** — boundary: a violation at global idx **0**
  must be reported, not skipped. Catches an off-by-one or a falsy-index bug that
  `hardmix` (hard starts at 1) cannot see.
- **`test_lits_are_tuples_and_not_aliased`** — `isinstance(lits, tuple)`,
  `lits is not wcnf.clauses[idx].lits`, `list(lits) == wcnf.clauses[idx].lits`.
  Catches handing a provider a live reference into clause storage.

`test_providers.py`:

- **`test_empty_advice_is_identity`** — the load-bearing one, in its strict
  three-part form: `out == x`, `out is not x`, and `x` unchanged afterwards.
  Catches in-place mutation of the caller's list (which would silently break
  step 10's bit-identity), a stray unconditional write, and `out[0] = False`
  leaking into a non-trivial position.
- **`test_noop_provider_composes_to_identity`** — the whole no-op path
  `propose → Advice() → apply_advice`, not just its pieces. Catches a `propose`
  that returns something non-empty (a stray `note` is harmless, a stray flip is
  not) — the exact claim §10 step 10 rests on.
- **`test_advice_is_applied`** — guards against an inert port: a non-empty
  `Advice` must actually edit, and must still leave `x` untouched.
- **`test_out_of_range_vars_are_skipped`** — `0`, `-1`, `len(x)`, `len(x)+1` are
  silently dropped, but `len(x)-1` (== `n_vars`) **is** applied. Catches the
  bounds check being written `v > len(out)` or `v >= n_vars`, an off-by-one that
  would drop every edit to the highest-numbered variable — invisible on any test
  that only touches middle variables.
- **`test_apply_order_is_flip_then_set_true_then_set_false`** — a var in both
  `flip_vars` and `set_false` ends `False`; one in both `flip_vars` and
  `set_true` ends `True`. Pins the source's last-writer-wins order; catches the
  three loops being reordered or merged.
- **`test_advice_matches_llmadvice_fields_and_is_frozen`** —
  `[f.name for f in dataclasses.fields(Advice)] == ["flip_vars", "set_true",
  "set_false", "note"]`, `Advice().note == ""`, and `FrozenInstanceError` on
  assignment to both `Advice` and `State`. Catches field drift away from
  `LLMAdvice` (§5 says field-for-field) and a mutable snapshot letting a provider
  write back into solver state out-of-band.

## Test output

Fails-before (both modules absent):
```
$ ls maxsat_new/hardviol.py maxsat_new/providers.py
ls: cannot access 'maxsat_new/hardviol.py': No such file or directory
ls: cannot access 'maxsat_new/providers.py': No such file or directory
$ python -m pytest maxsat_new/tests/test_hardviol.py maxsat_new/tests/test_providers.py
maxsat_new/tests/test_hardviol.py:15: in <module>
    from maxsat_new.hardviol import violated_hard_clauses
E   ModuleNotFoundError: No module named 'maxsat_new.hardviol'
maxsat_new/tests/test_providers.py:15: in <module>
    from maxsat_new.providers import Advice, NoopProvider, State, apply_advice
E   ModuleNotFoundError: No module named 'maxsat_new.providers'
=========================== short test summary info ============================
ERROR maxsat_new/tests/test_hardviol.py
ERROR maxsat_new/tests/test_providers.py
!!!!!!!!!!!!!!!!!!! Interrupted: 2 errors during collection !!!!!!!!!!!!!!!!!!!!
2 errors in 0.14s
```

After (new test files alone, then full suite — all prior tests still pass):
```
$ python -m pytest maxsat_new/tests/test_hardviol.py maxsat_new/tests/test_providers.py -q
...........                                                              [100%]
11 passed in 0.01s
$ python -m pytest maxsat_new/tests -q
..........................................                               [100%]
42 passed in 0.05s
```

Honest note on the first run after implementation: 10 passed, 1 failed —
`test_advice_is_applied` expected `[False, True, True, False]` where the correct
result is `[False, True, False, False]`. `x[2]` is `True`, so flipping it yields
`False`; the **test's** expected vector was wrong, not the port. Fixed in the
test (with the per-variable derivation added as a comment); `apply_advice` was not
touched. Every other assertion passed against the implementation on its first run.

## Decisions / ambiguities resolved

1. **PORT_NOTES §5/§3 vs `src` on the index space (resolved by ruling 1).**
   `SatState.unsat_hard_ids` and `prompt.py:extract_clause_examples` use global
   indices; the dead `memetic.py:100` sketch uses hard-sublist indices. §3 says
   consolidate both, and they conflict. Landed: **global**, with the rejected
   convention and its rationale recorded in the `hardviol.py` docstring.
2. **§10 row 6 vs §5 on the return type (resolved by ruling 2).** Row 6 writes
   `-> [(idx, lits)]` (list); §5 types the field as an all-tuple structure.
   Landed: list outer, tuple inner — row 6's signature satisfied, §5's element
   type already final, one `tuple(...)` at the step-7 boundary.
3. **`assign01` element type.** `cnf.eval_assignment` compares `== 1` (ints);
   `population.clause_satisfied` uses truthiness (bools). Landed: `hardviol`
   uses **truthiness**, the looser of the two, so it accepts both. Pinned by
   `test_no_violations_returns_empty` passing `[0, 1, 0, 0, 1, 1]`.
4. **`NoopProvider`'s `note`.** The source JSON carried `"note": "noop"`, which
   the dropped `LLMAdvisor` would have parsed into `LLMAdvice(..., note="noop")`.
   §5's sketch returns bare `Advice()` (`note=""`). Landed: **`Advice()`**,
   following §5. `note` is logged and never acted on, so this cannot affect a
   run; the divergence is recorded in the `NoopProvider` docstring.
5. **Whether `providers.py` should import `hardviol`.** It does **not**:
   `State.violated_hard` is typed with plain tuples, so `providers.py` is
   stdlib-only and the seam has no dependency on the WCNF layer. `build_state`
   (step 7) is where the two modules meet.

## Deviations from PORT_NOTES §5

- **`violated_hard_clauses` returns a `list`, not a `tuple`** — §5 types
  `State.violated_hard` as a tuple, and it still is; the conversion happens in
  step 7's `build_state`. This follows §10 row 6's signature and is a boundary
  placement, not a type change.
- **`NoopProvider` returns `note=""`** where the ported source produced
  `note="noop"` (decision 4). This follows §5's sketch exactly; it is a deviation
  from `src`, not from §5.

Otherwise: **none.** Field names, field order and types of `State` and `Advice`,
the `Provider` protocol signature, and `apply_advice`'s semantics are as §5
specifies.

## Flagged items (noticed, NOT changed)

- **`build_state` and the `run_memetic` per-child hook are deferred to step 7**
  (§6 places the call between mutation and polish). Nothing in this step
  constructs a `State` outside the tests, so the §6 claim that the provider call
  draws **no** EA RNG is not yet exercised by any test — it becomes testable at
  step 7 and is what step 10 measures.
- **`RandomPerturbationProvider` and `_provider_seed` are deferred to step 11.**
  §5's "critical determinism rule" (provider randomness derived from
  `(state.seed, state.generation, child_index)`, never drawn from the EA's
  master RNG) is *why* `State` carries `seed` and `generation` at all; those two
  fields are present and unused this step, by design.
- **`State.cost` has no producer yet.** §5 defines it as "current `best_cost` =
  unsatisfied soft weight (lower better)", but `cnf.eval_assignment` returns
  *satisfied* weight. The conversion is §10 row 8's explicit job ("convert cost
  to unsat-weight"); until then the field is only populated by tests. Flagged so
  the sign convention is settled once, at step 8, not improvised at step 7.
- **`n_hard_violations` is redundant with `len(violated_hard)`** and §5 says so
  ("tracked separately per cost convention"). Kept as a separate field per §5;
  nothing enforces the two agree, and nothing should until there is a producer —
  step 7's `build_state` is the natural place for that invariant.
- **`apply_advice` does not deduplicate or validate `Advice`.** A provider can
  name the same variable in `flip_vars` and `set_false`, or return thousands of
  entries; the source did neither and neither does the port. Fine for
  Noop/Random; a real LLM provider will want a sanity cap (§6 already flags
  per-call timeouts as out of scope).
- **`hardviol` is O(total clauses) per call**, scanning soft clauses to skip
  them. §6 charges one call per child. A hard-only index built once per instance
  would cut the constant, but it would also introduce the hard-sublist
  numbering that ruling 1 rejects, so any such cache must keep global ids.
  Not needed until profiling says so.
