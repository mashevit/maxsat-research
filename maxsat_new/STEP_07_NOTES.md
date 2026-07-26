# Step 07 notes — memetic.py (the run_memetic core)

Implements Step 7 of PORT_NOTES.md §10 (row 7: "the solver"). Port source sha:
**`1e3eaaf`**, recorded in the module docstring. This is a **port**:
`run_memetic` is `src/evo/memetic.py:33` statement for statement, with every RNG
draw and every draw *order* preserved, because §10 step 8 pins this core against
`src/cli/run_ea.py` as an oracle. `build_state` is **new**, specified by
PORT_NOTES §5/§6.

Dropped per §3: the three nested helper defs (`_assignment_exports`,
`clause_satisfied_bits`, `bits_to_assign01`, `src:128-162`), which recomputed
sat-counts a second, redundant way; the `flips_per_sec` / `restarts` /
`final_noise` cargo zeros; the hardcoded `LLMAdvisor(provider=NoopProvider())`
(`src:43`) — the provider now arrives as an argument, which is the §6 seam.

## Files created

- `maxsat_new/memetic.py` — `build_state`, `run_memetic`. Imports only stdlib and
  already-ported `maxsat_new` modules; **no `config.py` import** (the core stays
  below the runner layer).
- `maxsat_new/tests/test_memetic.py` — §10 row 7 (6 tests).
- `maxsat_new/STEP_07_NOTES.md` — this file.

Nothing already committed was edited.

## Public surface

```python
def build_state(instance: Any, child: List[bool], gen: int, seed: int) -> State: ...

def run_memetic(
    instance: Any,
    params: Mapping[str, Mapping[str, Any]],
    seed: int,
    provider: Provider,
) -> Dict[str, Any]: ...
```

`params` is a **nested** mapping of three blocks whose key names are exactly what
`config.py` already produces, so nothing is renamed at the boundary and the §9.4
`time_limit_s` split is preserved *structurally*:

```python
{"ea":     <ResolvedConfig.resolved_params>,   # pop_size, polish_flips, tournament_k,
                                               # pmutate, elitism, elite_frac
 "budget": {"max_gens": int, "time_limit_s": float},
 "polish": <ResolvedConfig.polish>}            # time_limit_s, noise, hard_safe
```

Every key is read by subscript — no `.get` defaults — so a missing key is a
`KeyError`, following step 5's no-silent-defaults stance. Step 8's `solvers.py`
adaptation from a `ResolvedConfig` is three lines.

Result dict:

```python
{"best_soft_weight": int,        # SATISFIED soft weight (src's key name)
 "hard_violations": int,
 "best_assignment": list[bool],  # 1-based copy, index 0 unused
 "best_assignment_hash": str,    # bare blake2b-12 hex; step 9 adds the prefix
 "generations": int, "children": int, "total_flips": int, "wall_time_s": float}
```

`best_soft_weight` keeps src's name deliberately: step 8 *adds* `best_cost`
(`total_soft_weight - best_soft_weight`, §8) rather than redefining an existing
key, so no key silently changes meaning between steps.

---

## 1. The correction to PORT_NOTES §1/§3: the "dead LLM block" is live

§1 says the block at `src/evo/memetic.py:95-112` is "wrapped in `''''''''` string
literals — **dead**", and §3's port map lists it as dropped. **That is wrong, and
this port does not drop it.**

`''''''''` is eight single quotes. Python tokenizes it as `''''''` (an empty
*triple*-quoted string) followed by `''`, adjacent-literal-concatenated into one
empty string, which is then an ordinary **expression statement**. It does not open
a block comment, so `:96-111` are live sibling statements. The AST of
`run_memetic` shows `Expr(Constant(''))` at `:95` and `:112` with `:96-111`
executable between them, and a live run confirms the arithmetic: `pop_size=6`,
`max_gens=3` on `mini.wcnf` produces **15 children and 30 `rng.randrange`
draws** — two per child, not one.

So the live `run_ea.py` path makes two `rng.randrange(1 << 30)` draws per child:
the `rng_seed=` argument of `advisor.propose` (`src:108`) and the polish seed
(`src:113`). The advisor draw is consumed and discarded — `src/llm/prompt.py` and
`src/llm/advisor.py` contain no randomness at all (grepped), `NoopProvider.complete`
returns a constant JSON string, and `apply_advice` on the resulting empty advice
is an identity copy. The block's only surviving observable effects are that one
draw, a behavior-neutral `pop.cache` warm, and a rebind of `child_bits`.

The port keeps the draw, as its own statement at the §6 hook site:

```python
_ = rng.randrange(1 << 30)
```

Its own statement rather than an inline argument for two reasons: the order
against the polish draw does not depend on argument-evaluation order, and it stays
**provider-independent**, so switching Noop → Random at step 11 cannot shift the EA
stream (§5's "the EA's RNG stream is unchanged by the seam's presence").

Measured consequence of getting this wrong — see §3 below for why the
reproducibility test cannot catch it.

## 2. Item 1 as required: exactly what the ledger test asserts

`test_ea_rng_ledger_is_exact` asserts the **draw sequence and the drawn values, in
order** — not just counts. Mechanics:

- `random.Random` is monkeypatched with `_TracingRandom`, which appends
  `(kind, value)` to a per-instance `trace` for `random` / `randrange` / `choice`,
  and `(kind, (len(population), k))` for `sample` (the returned `Individual`
  objects are not comparable across runs; what pins the stream is the consumption,
  which depends only on `len(population)` and `k`, plus the values of every later
  draw).
- The EA rng is `_INSTANCES[0]`, the first `Random` built inside `run_memetic`
  (`src:51`). Each `short_polish` builds its own (`walksat.py:100`), which is why
  the trace is attributed per instance, never globally. `len(_INSTANCES) == 1 +
  CHILDREN` is asserted too — one polish RNG per child, i.e. the polish is called
  exactly once per child.
- The expectation is produced by `_expected_trace`, which **replays a plain
  `random.Random(SEED)`** making the same calls in the same order:
  `POP_SIZE * n_vars` `random()` for `init_seeds`, then per child
  `sample, sample, random × n_vars, randrange, randrange`.
  `r.sample(range(POP_SIZE), k)` consumes identically to sampling a
  `POP_SIZE`-element list of `Individual`s, so the replay reproduces the exact
  value stream of every later draw.

Three assertions, weakest to strongest:

```python
assert [kind for kind, _ in ea_trace] == [kind for kind, _ in expected]  # order + multiplicity
assert ea_trace == expected                                              # + every value, in order
# then, spelled out for the record:
assert kinds.count("random")    == (POP_SIZE + CHILDREN) * n_vars
assert kinds.count("sample")    == 2 * CHILDREN
assert kinds.count("randrange") == 2 * CHILDREN
assert kinds.count("choice")    == 0
```

What each catches:

| Deviation | How it shows up |
|---|---|
| `src:108` advisor-seat draw dropped | `randrange` count `CHILDREN` not `2*CHILDREN`; kind sequence mismatch at child 1 |
| a draw added inside `build_state` / `propose` / `apply_advice` (§6 violation) | `3*CHILDREN` randrange, or extra `random`; kind sequence mismatch |
| hook moved before `mutate1`, or the two `randrange` swapped | kind sequence matches but **values** differ → `ea_trace == expected` fails |
| `mutate1` not called once per child over all `n_vars` | `random` count `!= (POP_SIZE + CHILDREN) * n_vars` |
| `tournament` called once, or thrice | `sample` count wrong |
| `crossover1`'s `rng.choice` tie-break becoming reachable | a `choice` entry appears; `count("choice") == 0` fails |
| `short_polish` called twice per child, or skipped | `len(_INSTANCES) != 1 + CHILDREN` |

`choice() == 0` is an assumption made explicit rather than assumed silently:
`clause_aware_crossover1`'s guard `a != b and chosen not in (a, b)`
(`operators.py:221`) is unreachable because `chosen` is a parent bit and `a != b`
means `{a, b} == {True, False}`. If that ever changes the test fails, which is the
intent.

### Why the ledger is the only real divergence guard here

`test_same_seed_twice_is_bit_reproducible` (row 7's second clause) is **vacuous as
a divergence guard on `mini.wcnf`**, and this was measured, not assumed. Running
the ported core with the `src:108` draw removed (in-memory variant, nothing on
disk changed):

```
VARIANT reproducible (test 2 would PASS): True
  variant soft/hash: 14 b8aaa344f25caf958fdeed7e
  ported  soft/hash: 14 b8aaa344f25caf958fdeed7e
  -> identical to ported? True
LEDGER on variant: randrange count = 15 expected 30 | trace == expected: False
```

So on 5 variables every stream converges to the same optimum: the reproducibility
test stays green **and even produces the identical hash**, while the ledger fails
immediately. The same held for the original `src` code (removing the draw there
also gave `soft=14.0`, `bits=10111`). Row 7's stated test therefore proves
*self-consistency*, and the ledger proves *stream fidelity*; step 8's oracle test
on a real instance (`data/dev_small/…V100_C600_H100_*.wcnf`) is the end-to-end
check and is not this step's job.

## 3. Item 2 as required: the §9.1 replication, including the NameError edge

```python
for ind in pop.members:          # src:56-57
    pop.evaluate(instance, ind)

stale_hard_satisfied = ind.hard_satisfied     # PORT_NOTES §9.1
```

`ind` is a leaked loop variable: after the loop it is bound to `pop.members[-1]`,
the last individual built by `init_seeds`, whose `hard_satisfied` was computed
from *its own* JW-seeded assignment (`population.py:155`) and which
`Population.evaluate` never refreshes. `src:93` hands that member's list — **the
object itself, not a copy** — to `mutate1`, which writes into it in place
(`operators.py:284`). One list, shared and mutated across every child of every
generation, indexed over the hard-only sublist, and never corresponding to the
child being mutated: `mutate1`'s "don't unsatisfy a satisfied hard clause" guard
tests against an assignment that does not exist. The object also outlives its
membership — `pop.members = new_members` drops it from the population each
generation, but the name keeps it alive for the whole run.

The single alias line makes the leak legible without changing it: same object
identity, same in-place mutation, same lifetime. It is never copied, never
recomputed per child. `mutate1`'s own docstring (`operators.py:243-248`) already
states the callee half of this contract; this is the caller half.

**The `pop_size == 0` `NameError` is replicated, deliberately.** With an empty
population the loop body never runs, `ind` is never bound, and
`stale_hard_satisfied = ind.hard_satisfied` raises `NameError` — exactly as
`src:93` does. There is **no defensive pre-definition of `ind`** and no guard: if
`run_ea.py` would `NameError` on a path, the port must too. Adding a fallback
(`ind = None`, `hard_satisfied = []`, an early return) would make the port
*succeed* where the oracle fails, which is a fidelity break in the same class as
losing an RNG draw — it just happens to be on an error path. Load-bearing for §11
Q3: the eventual fix gets its own PR and its own before/after test, and the fix is
where an empty-population guard belongs, if anywhere.

## 4. Item 3 as required: real `violated_hard` vs src's `[]` is inert under Noop

`src:99-101` fed the advisor an unconditionally empty list:

```python
violated_idxs = []
# violated_idxs = [i for i, sat in enumerate(tmp_child.hard_satisfied) if not sat]
```

`build_state` supplies the real thing, from `hardviol.violated_hard_clauses`. This
is a deliberate deviation from `src`'s data flow — §5 calls `violated_hard` "the
load-bearing field the future LoRA training set reads", and the commented-out
line used hard-sublist indices, the convention STEP_06_NOTES ruling 1 rejected as
a latent bug (feeding them to `prompt.py:extract_clause_examples`, which resolves
with `wcnf.clauses[idx]`, silently reads the wrong clause).

**Why it is inert under `NoopProvider`** — the argument, not the assertion. Three
links, each independently checkable:

1. **`NoopProvider.propose` ignores its argument.** Its body is `return Advice()`
   (`providers.py:121-122`) — a constant. `state` is not read, not stored, not
   branched on. So *no* field of `State` can influence the returned `Advice`, and
   `violated_hard` specifically cannot: the same `Advice()` comes back for an empty
   tuple and for a 600-element one. (In src the equivalent link is longer but ends
   the same way: `violated_idxs` reached `extract_clause_examples` →
   `build_prompt` → a prompt *string* → `NoopProvider.complete`, which ignores the
   prompt and returns a constant JSON literal.)
2. **Empty `Advice` makes `apply_advice` an identity copy.** All three loops
   iterate `()`; the only write is `out[0] = False`, a no-op under the §5 invariant
   that index 0 is unused and False, which every producer in the package upholds.
   So `child_bits` after the hook is element-wise equal to `child_bits` before it
   — proven in STEP_06_NOTES "The identity guarantee" and asserted by
   `test_empty_advice_is_identity` / `test_noop_provider_composes_to_identity`.
3. **The hook draws no EA randomness.** `build_state` is pure (only
   `violated_hard_clauses` and `evaluate_assignment`, no RNG, no clock),
   `NoopProvider.propose` is a constant, `apply_advice` has no randomness. The one
   draw at the hook site is the `src:108` fidelity draw, which is made
   unconditionally by `run_memetic` itself and is *not* a function of the
   provider or of `state`.

Links 1–3 compose: the child bits entering `short_polish` are unchanged, and the
RNG stream entering `short_polish` is unchanged, so the polish input is unchanged,
so the child is unchanged, so the population, the best, and the final cost are
unchanged. Computing a real `violated_hard` therefore costs one `hardviol` pass
per child and changes nothing observable while the provider is Noop.

That inertness is exactly what §10 step 10's bit-identity claim rests on
(`llm_guided_base` + `NoopProvider` == `memetic_ea` on both `best_cost` and
`best_assignment_hash`): the seam may compute and expose as much as it likes, as
long as the provider's *return value* is empty and the EA's draw sequence is
untouched. Step 11 then flips exactly one thing — `propose` starts reading `state`
and returning non-empty `Advice` — and by construction that is the *only* channel
through which the experiment can differ from the control.

Two tests back the argument up where it is checkable:
`test_build_state_sees_real_violated_hard_not_srcs_empty_list` shows the field is
genuinely non-empty (so the deviation is observable, not a claim), and
`test_provider_receives_state_and_cannot_perturb` shows a provider that *reads*
every snapshot and returns `Advice()` produces the byte-identical run to
`NoopProvider` (same hash, same cost, same flips) — link 1 and the composition,
end to end.

---

## `build_state` design

```python
State(assign=tuple(child),                                   # fresh tuple, not an alias
      violated_hard=tuple(violated_hard_clauses(instance, child)),  # ONE call per child
      cost=int(evaluate_assignment(instance, child)[0]),      # SATISFIED soft weight
      n_hard_violations=len(violated),                        # agrees by construction
      generation=gen, seed=seed, n_vars=instance.n_vars)
```

- Module-level with `instance` first, so it is unit-testable without running the
  EA. §10 row 7 sketches `build_state(child, gen, seed)`, which reads as a closure
  over `wcnf`; the extra parameter is the only difference.
- Only the outer list needs wrapping — the elements are already
  `(int, tuple[int, ...])` (STEP_06_NOTES ruling 2) — and the indices are **global**
  `wcnf.clauses` indices, not hard-sublist ones.
- `n_hard_violations` derived from the same list settles the invariant
  STEP_06_NOTES flagged as "step 7's build_state is the natural place".
- `seed` is the run's **master** seed, never RNG state, because step 11's
  `_provider_seed` derives from `(state.seed, state.generation, child_index)`.

### `State.cost` — satisfied weight now, sign settled at step 8

`providers.py:42` documents `cost` as "unsat soft weight, lower better", but
`evaluate_assignment` returns **satisfied** soft weight, and step 7 ships that.
STEP_06_NOTES flagged exactly this: *"State.cost has no producer yet … The
conversion is §10 row 8's explicit job … Flagged so the sign convention is settled
once, at step 8, not improvised at step 7."* So `build_state` passes
`int(satisfied_soft_weight)`, the inline comment names step 8 as the owner, and
`test_build_state_fields` **pins the current value** (`state.cost == int(soft)`) so
step 8's inversion surfaces as one failing assertion instead of a silent
redefinition. The `int()` cast is exact: `cnf.parse_dimacs` reads every weight with
`int()`, so the float accumulator is always integral.

## The per-child pipeline, as shipped

```python
p1 = tournament(pop.members, k, rng)                    # src:89   rng.sample x1
p2 = tournament(pop.members, k, rng)                    # src:90   rng.sample x1
child_bits = clause_aware_crossover1(p1, p2, instance, rng)  # src:91  rng.choice unreachable
mutate1(child_bits, pmutate, rng, hard_clauses,         # src:93   rng.random() x n_vars
        hard_occurs, stale_hard_satisfied)              #          PORT_NOTES §9.1

state = build_state(instance, child_bits, gen, seed)    # src:96-99 replacement; NO EA rng
_ = rng.randrange(1 << 30)                             # src:108  LIVE draw (see §1)
advice = provider.propose(state)                        # src:104  NO EA rng
child_bits = apply_advice(child_bits, advice)           # src:111  identity under Advice()

child_bits, flips_t1 = short_polish(child_bits, instance,
    rng_seed=rng.randrange(1 << 30), polish_flips=..., time_limit_s=...,
    noise=..., hard_safe=...)                           # src:113  rng.randrange x1
flips_t += flips_t1
child = Individual(assign01=child_bits, meta={"gen": gen}); pop.evaluate(instance, child)
new_members.append(child); total_children += 1
```

`build_state` replaces src's `tmp_child = Individual(...)` + `pop.evaluate(...)`
(`src:96-97`). Dropping that evaluate is **behavior-neutral, not an assumption**:
`pop.cache` is a pure memo keyed on `hash_assign(assign01)` with values computed by
`evaluate_assignment`, so a hit can only return what a miss would compute; the
cache can therefore affect run time and memory but never a value. And
`build_state` produces the same two quantities the discarded `tmp_child` held.

`apply_advice` runs on `child_bits`, a **list**, never on `state.assign`, a tuple —
STEP_06_NOTES ruling 3 records that the verbatim `out = assign01[:]` would raise
`TypeError` on a tuple, and the §6 pipeline never reaches it.

## Two clause-index spaces, kept distinct

`hard_clauses` / `hard_occurs` (`src:71,74`) and `stale_hard_satisfied` are indexed
over the **hard-only sublist** `[cl for cl in wcnf.clauses if cl.is_hard]`.
`build_state`'s `violated_hard` carries **global** `wcnf.clauses` indices
(STEP_06_NOTES ruling 1). Both live in one function and must not be conflated;
recorded in the module docstring so a future reader does not "unify" them.

## Deviations from `src` (all recorded inline)

1. **The `src:108` draw is kept** — a deviation from PORT_NOTES §1/§3, which said
   to drop it, not from `src`. See §1.
2. **`violated_hard` is real, not `[]`** — see §4; inert under Noop.
3. **`pop.evaluate(tmp_child)` dropped** — provably neutral, above.
4. **`elite_frac` replaces the hardcoded `0.05 * pop_size`** (`src:80`), sanctioned
   by §4 ("lift to a named const"). Byte-identical at `elite_frac=0.05`.
5. **`params` replaces the `cfg` dict** and the `_ea_cfg` / `_ls_budget` readers.
   No `.get` defaults; the §9.4 split is structural. `pop.init_seeds(instance, {})`
   passes an empty dict because the ported `init_seeds` accepts a cfg and never
   reads it (src passed the whole config).
6. **`best_soft_weight` is `int`, not `float`** (`src:169` wrapped it in `float()`).
   Numerically equal; §8's record wants ints. Comparisons in step 8 are unaffected.
7. **`generations` / `wall_time_s`** are §8's names for src's
   `meta.ea_generations` / `elapsed_sec`. The `satisfied_clauses` block and
   `meta.assign_bits` / `dimacs` / `true_vars` are dropped (§3); step 9 can derive
   them from `best_assignment`.

Preserved exactly: the single `random.Random(seed)` object and its threading; the
`while (time.time() - start_t) < time_cap and gen < max_gens` condition, operator
and order; `start_t` taken **after** seeding (`src:64`), so seeding is not charged
against the wall cap; elites as **references** from a stable `sorted(...,
reverse=True)`; `best = pop.best().copy()` via `max` (first maximal element, not a
sort); the strict `>` on the best update, so ties keep the older best; and final
numbers from `population.evaluate_assignment` (`src:166`).

## The `cnf.eval_assignment` trap

§3 says the dropped nested helpers should be "replace[d] with one
`cnf.eval_assignment`". That must **not** be applied to the soft-weight line.
`cnf.eval_assignment` returns satisfied weight over **all** clauses, hard weights
included; `population.evaluate_assignment` returns **soft-only** weight — a
different number (on `hardmix.wcnf` with the step-6 assignment: `110` vs `10`).
Using the former for `best_soft_weight` would silently change the quantity step 8
compares against `run_ea.py`. §3's instruction targets the redundant *clause-count*
block, which is dropped outright.

## Determinism: both budgets must be iteration-bound

PORT_NOTES §11 Q1 names only the EA-level cap, but `walksat_polish` has its **own**
wall clock (`time_up()`, `walksat.py:118`, checked in the flip loop at `:135`), so
`polish.time_limit_s` truncates a polish on a slow or loaded machine. Bit-
reproducibility needs `budget.max_gens` **and** `ea.polish_flips` to bind, with
both `time_limit_s` values set large. The test config uses `1000.0` for both and
says why; step 8's oracle test will need the same treatment.

## Test design

Six tests in `maxsat_new/tests/test_memetic.py`, fixture `mini.wcnf`.

**Why `mini.wcnf`:** it *has* hard clauses (`top=100`, three `100 …` lines), which
is what makes this step exercisable — `hard_clauses` / `hard_occurs` are non-empty,
so `mutate1`'s guard actually runs against the §9.1 stale list, and `violated_hard`
can be non-empty, so `build_state`'s load-bearing field is not vacuous. A `.cnf`
would load all-soft (§9.6): `hard_satisfied == []`, `hard_occurs` all empty, every
flip trivially accepted, `violated_hard` always `()` — the two things this step
exists for would go untested. It is also 5 vars / 8 clauses, so the run is
milliseconds and `max_gens` genuinely binds; and it is already pinned by
`test_cnf.py` (`n_vars=5`, 8 clauses, 3 hard). `hardmix.wcnf` appears only in the
`build_state` tests, to carry the global-index convention through.

| Test | §10 row 7 clause | Catches |
|---|---|---|
| `test_small_run_returns_valid_result` | "returns a valid result" | key-set drift; `generations != max_gens` (wall cap bound instead); wrong child count (elite arithmetic); `best_assignment[0]` not False; and — via re-deriving `evaluate_assignment` on the returned assignment — reporting a *different* individual than the one handed back |
| `test_same_seed_twice_is_bit_reproducible` | "identical best_cost AND assignment hash" | any run-to-run nondeterminism (an unseeded RNG, a clock-bound budget, dict/set iteration order). **Vacuous as a divergence guard — measured, see §2** |
| `test_ea_rng_ledger_is_exact` | the §6 invariant | the whole table in §2 — a lost or added draw, a reordered hook, a hook that draws |
| `test_build_state_fields` | — | tuple/alias semantics on `assign`; `violated_hard` disagreeing with `hardviol`; `n_hard_violations` drifting from `len(violated_hard)` or from `evaluate_assignment`'s independent count; `n_vars`/`generation`/`seed` mis-wired; and the step-7 `cost` sign convention |
| `test_build_state_sees_real_violated_hard_not_srcs_empty_list` | — | a `build_state` that reproduced src's hardcoded `[]`, or that used hard-sublist indices (would give `(0, …), (2, …)`) |
| `test_provider_receives_state_and_cannot_perturb` | §6 "which children / how often" | the provider being called for elites, once per generation instead of per child, or not at all; `generation` not advancing; `seed` carrying RNG state instead of the master seed; a mutable snapshot; and — via hash equality against `NoopProvider` — a provider that *reads* the state changing the run |

## Test output

Fails-before (module absent):

```
$ python -m pytest maxsat_new/tests/test_memetic.py -q
maxsat_new/tests/test_memetic.py:41: in <module>
    from maxsat_new.memetic import build_state, run_memetic
E   ModuleNotFoundError: No module named 'maxsat_new.memetic'
=========================== short test summary info ============================
ERROR maxsat_new/tests/test_memetic.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.08s
```

After (new file alone, then the full suite — all prior tests still pass):

```
$ python -m pytest maxsat_new/tests/test_memetic.py -q
......                                                                   [100%]
6 passed in 0.06s
$ python -m pytest maxsat_new/tests -q
................................................                         [100%]
48 passed in 0.09s
```

All six passed on the first run against the implementation; no test expectation
needed correcting this step.

## Flagged items (noticed, NOT changed)

- **PORT_NOTES §1/§3 are factually wrong about the dead block.** Corrected in the
  `memetic.py` docstring and §1 above; `PORT_NOTES.md` itself was not edited (out
  of scope — this step touches `memetic.py` and its test only). §3's port-map row
  for `memetic.py` and §1's "Surprises" bullet both need amending, and §10 step 8's
  oracle test depends on the corrected reading.
- **`_ = rng.randrange(1 << 30)`** is a draw whose value is discarded. Anything
  that "cleans it up" breaks step 8. The inline comment says so.
- **Elites are references, not copies** (`src:81`), and `Individual.copy` shares
  `meta` (`population.py:39`) rather than copying it, so an elite's `meta["gen"]`
  reports the generation it was *created* in and the dict is aliased across copies.
  Harmless today (nothing reads `meta`); preserved.
- **`crossover1`'s `rng.choice` tie-break is unreachable** (`operators.py:221`).
  Kept in `operators.py`; the ledger test asserts `count("choice") == 0`, so if it
  ever becomes reachable the change is loud.
- **`build_state` costs two O(n_clauses) passes per child** — one in
  `violated_hard_clauses`, one in `evaluate_assignment` — where src's
  `pop.evaluate(tmp_child)` was one (and cacheable). §6 already charges the
  `hardviol` call; the second pass is new. A single fused pass returning both would
  fix it, but it belongs in `hardviol`/`population`, not here, and not before
  profiling says so.
- **`pop.cache` is unbounded.** src had the same behavior plus an extra entry per
  child from the dropped `tmp_child` evaluate, so this port grows it *more slowly*.
  Values are pure, so this is a memory concern only.
- **`hash_assign` ignores `assign01[0]`** (`population.py:73`, slices from 1), so
  `best_assignment_hash` is insensitive to index 0 — consistent with the §5
  "index 0 unused" invariant, and what makes step 10's hash comparison robust to
  `apply_advice`'s `out[0] = False`.
- **No `pop_size == 0` guard** — see §3. Intentional.
