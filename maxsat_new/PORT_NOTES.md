# PORT_NOTES.md

Planning doc for `maxsat_new/`. Plan only — no code shipped by this doc.
Goal: port the working `src/` pipeline into a clean, standalone `maxsat_new/`
package that reproduces `src/cli/run_ea.py`'s numbers, then extend the seam to
`llm_guided_base` (NoopProvider control, then RandomPerturbationProvider). No
Ollama, no LLM, no network in anything below.

`git rev-parse HEAD` at time of writing: `1e3eaaf` (record this sha in every
ported module docstring as the port source).

---

## 1. What I read; what surprised me

Read: `docs/HARNESS_PLAN.md`, `docs/STRATIFICATION_PLAN.md`,
`src/evo/memetic.py`, `src/evo/operators.py`, `src/evo/population.py`,
`src/sat/walksat.py`, `src/sat/state.py`, `src/sat/cnf.py`, `src/llm/advisor.py`,
`src/llm/prompt.py`, `src/llm/providers/noop.py`, `src/cli/run_ea.py`, all 12
`configs/*.yaml`.

### What actually runs in the EA path

Tracing `run_ea.py -> run_memetic` (`src/evo/memetic.py:33`), the live code path
consumes a **much smaller** config surface than the config files imply. Per child:
`clause_aware_crossover1` -> `mutate1` -> `short_polish` -> evaluate. The LLM block
(`memetic.py:95-112`) is wrapped in `''''''''` string literals — **dead**. The
provider is hardcoded `NoopProvider` (`memetic.py:43`) but never called because the
block that would call it is the dead one.

### Surprises

- **`run_memetic` reads only ~7 config keys.** `ea.pop_size`, `ea.tournament_k`,
  `ea.pmutate`, `ea.elitism`, `ea.max_gens` (`_ea_cfg`, `memetic.py:11`), the EA
  wall cap `time_limit_s` (`memetic.py:63`), and the polish budget
  `ls.ls_polish_flips` + per-polish `ls.time_limit_s` (`_ls_budget`,
  `memetic.py:23`). Everything else in the config zoo is never read on this path.
- **`ls.flip_budget` is dead on the EA path.** `_ls_budget` maps it to `max_flips`
  (`memetic.py:29`), but `short_polish` pulls `ls_polish_flips` first
  (`operators.py:402`), so `max_flips` is shadowed. The `flip_budget` values in
  `cfg2/cfg3/cfghard1/hard2/hard3` do nothing to the EA.
- **`mutate1` is fed a stale `hard_satisfied` from a leaked loop variable.**
  `memetic.py:93` passes `ind.hard_satisfied`, where `ind` is the last item left
  over from the init-eval loop (`memetic.py:56`), *not* the current child. It is
  mutated in place and reused across every child of every generation. Load-bearing
  for bit-identity; see §9.
- **CNF files become all-soft, weight 1, zero hard clauses**
  (`cnf.py:80-82`, `weight=1#top`, `is_hard=False#True`). So "solve a `.cnf`" means
  "maximize satisfied clauses", matching HARNESS §5 Q1. Intentional, not a bug.
- **Determinism is already close.** One `random.Random(rng_seed)` object
  (`memetic.py:51`), threaded into `Population` and derived per-child for polish via
  `rng.randrange(1<<30)`. No module-level `random.*` calls on the live path. Good
  base to port from.
- **Wall-clock is the only stop condition in practice.** `while (time.time()-start_t)
  < time_cap and gen < max_gens` (`memetic.py:76`). With a real time cap the number
  of generations is nondeterministic, so "one seed -> bit-identical run" **cannot
  hold under a wall-clock budget**. See §11 Q1.
- **Three WalkSAT implementations in one file** (`src/sat/walksat.py`): the `WalkSAT`
  class (`:21`), `run_satlike` (`:328`), `walksat_polish` (`:529`). The EA uses
  **only** `walksat_polish`. `run_satlike` and `walksat_polish` are full of debug
  `print()` (`walksat.py:363,366,505`). `state.py` carries ~5 commented-out dead
  alternative method bodies (`state.py:139,212,219,310`).

### configs/*.yaml variance analysis (the config zoo is evidence)

Two disjoint groups. **LS/satlike group** (`ea.enabled: false`): `default.yaml`,
`2.yaml`, `3.yaml`, `4.yaml`. These drive `run_satlike` via `solve_batch`, **not**
the EA, and carry big blocks (`noise_adapt`, `dynamic_weights`, `size_rule`,
`seeding`, `llm`, `bench`) that `run_memetic` never reads. **Noise for this
milestone.**

**EA group** (`ea.enabled: true`): `cfg.yaml`, `cfg2.yaml`, `cfg3.yaml`,
`cfg250.yaml`, `cfghard1.yaml`, `hard2.yaml`, `hard3.yaml`, `ea_cfg.yaml`. What
actually varies across them, restricted to keys the EA reads:

| Key | Values seen | Read by EA? | Verdict |
|---|---|---|---|
| `ea.pop_size` | 50, 60, 75, 80, 110 | yes | **varies — deserves a sizing rule** |
| `ls.ls_polish_flips` | 5, 500, 700, 2000, 12500 | yes | **varies — deserves a sizing rule** |
| `ls.time_limit_s` (per-polish) | 0.001, 0.05, 0.1, 0.5 | yes | varies (fixed knob, not size-derived) |
| top-level `time_limit_s` (EA cap) | 0.05, 10, 180, 300, 600 | yes | varies (always explicit, never derived) |
| `ea.tournament_k` | 4 (only `ea_cfg` sets it) | yes | **constant** |
| `ea.pmutate` | 0.02 | yes | **constant** |
| `ea.elitism` | true | yes | **constant** |
| `ea.max_gens` | 100 (only `ea_cfg`, = default) | yes | **constant** |
| `ls.flip_budget` | 0, 50, 2000, 12500 | no (shadowed) | **noise** |
| everything under `seeding/llm/bench/noise_adapt/...` | many | no | **noise** |

Conclusion: exactly **two** knobs vary meaningfully with instance and belong on a
sizing rule — `pop_size` and `polish_flips`. `time_limit_s` varies but is a budget,
always explicit. Everything else is either a true constant or dead config.

---

## 2. Proposed file tree for `maxsat_new/`

Root of repo, importable as `maxsat_new`. Standalone: **must not import from
`src/`.**

```
maxsat_new/
  __init__.py          # package marker; version string; sets OMP_NUM_THREADS=1
  cnf.py               # WCNF + parse_dimacs (the one parser)
  features.py          # InstanceFeatures dataclass + extract(wcnf) -> features
  sizing.py            # named sizing rules + resolve_params (rule -> concrete value)
  config.py            # YAML load + merge + resolution order (defaults<yaml<CLI)
  state.py             # SatState incremental LS machinery (internal)
  hardviol.py          # violated_hard_clauses(wcnf, assign01) -> [(idx, lits)]  (load-bearing, exposed)
  walksat.py           # walksat_polish only
  population.py        # Individual, Population, jw_priors, evaluate_assignment
  operators.py         # tournament, clause_aware_crossover, mutate, short_polish
  providers.py         # State, Advice, Provider protocol, apply_advice, NoopProvider, RandomPerturbationProvider
  memetic.py           # run_memetic(instance, params, seed, provider) -> result   (the core)
  record.py            # RunRecord schema + JsonlRecorder + config_hash
  registry.py          # SOLVERS dict + @register decorator
  solvers.py           # memetic_ea, llm_guided_base registered over run_memetic
  run.py               # CLI entry: python -m maxsat_new.run
  configs/             # authoritative experiment YAMLs
    memetic_ea.yaml
    llm_guided_base.yaml
  tests/               # pytest; one test per step (§10)
    data/              # tiny committed instances for tests
  results/             # JSONL run output (gitignored)
  PORT_NOTES.md        # this file
```

**Invocation:** `python -m maxsat_new.run maxsat_new/configs/memetic_ea.yaml`
(from repo root). **Importability:** repo root is already the CWD and on
`sys.path`; a `maxsat_new/__init__.py` is enough — no install, no `PYTHONPATH`
edit, no `sys.path` hacking (unlike `run_ea.py:12-15`). Tests run with
`pytest maxsat_new/tests`.

Splitting rationale: `features`/`sizing`/`config` are separate because §4 makes
"add a rule" a one-function change and "resolve a config" independently testable.
`hardviol` is its own module because §5/§10 make it a load-bearing, exposed step.

---

## 3. Port map (new file <- old file; what is dropped)

| New file | Ports from | Dropping |
|---|---|---|
| `cnf.py` | `src/sat/cnf.py` (`WCNF`, `parse_dimacs`, `eval_assignment`) | the `run_ea.py:24-79` fallback `_parse_wcnf` (redundant second parser); `true_count_per_clause` (unused on EA path) |
| `state.py` | `src/sat/state.py` (`ClauseInfo`, `SatState` live methods only) | all `'''...'''` dead method bodies (`state.py:139,212,219,310`); `restart_partial_from_best` (never called on polish path) |
| `walksat.py` | `src/sat/walksat.py` **`walksat_polish` only** (`:529-693`) | **`WalkSAT` class** (`:21`, used only by `solve.py`, not the EA), **`run_satlike`** (`:328`, used by `solve_batch`/`bench`, not the EA), `_derive_hard_fixed_literals` (unused by polish), `_freeze_hard_units`, all `print()` debug |
| `population.py` | `src/evo/population.py` | `memetic0.py` (dead duplicate elsewhere); nothing else — this file is lean |
| `operators.py` | `src/evo/operators.py` (`tournament`, `clause_aware_crossover1`, `mutate1`, `short_polish`, `_soft_proxy_scores`, `frozen_hard_unit_vars`, `build_hard_occurs`) | **`clause_aware_crossover`** (v0, superseded by `crossover1`, not called by EA), **`mutate`** (v0, not called), `short_polish1` (stub), `_repair_hard_constraints` (only used by dropped v0 crossover) |
| `hardviol.py` | new; consolidates `population.clause_satisfied` + `SatState.unsat_hard_ids` intent | n/a |
| `providers.py` | `src/llm/advisor.py` (`LLMAdvice`->`Advice`, `apply_advice`) + `src/llm/providers/noop.py` | `LLMAdvisor` two-layer prompt/JSON machinery (`advisor.py:67`), `src/llm/prompt.py` entirely (LLM-only; not needed for Noop/Random) |
| `memetic.py` | `src/evo/memetic.py` `run_memetic` (`:33`) | dead LLM block (`:95-112`); the three nested helper defs (`_assignment_exports`, `clause_satisfied_bits`, `bits_to_assign01`, `memetic.py:128-162`) which recompute sat-counts a second, redundant way — replace with one `cnf.eval_assignment`; `flips_per_sec/restarts/final_noise` cargo-culted zeros |
| `record.py` | HARNESS_PLAN §2.3 (cut per §8) | — |
| `registry.py` | HARNESS_PLAN §2.2 | — |
| `solvers.py` | HARNESS_PLAN §2.2 table (memetic_ea, llm_guided_base rows) | `walksat`, `ga_no_ls`, `rc2`, `llm_guided_lora` solvers (out of scope for this milestone) |
| `run.py` | `src/cli/run_ea.py` main() | `-D` JSON-literal parsing kept but slimmed; `io.out_json` templating; internal-parser fallback |

**Which WalkSAT the EA uses:** `walksat_polish` (via `operators.short_polish` at
`operators.py:409`). Porting only that. Dropping `WalkSAT` (class) and `run_satlike`.

---

## 4. Config + sizing-rule design

### Mechanism choice: (a) named rule functions in code, YAML picks by name

Picked **(a)** over (b) safe-eval expression strings. Reasons: (b) makes a typo a
silent experiment; expression strings are hard to unit-test and impossible to
enumerate; they invite unbounded logic in config. (a) keeps the rule set a finite,
testable, enumerable registry; YAML supplies only a name + coefficients. Adding a
rule is one decorated function. This is your GUESS and I agree.

### InstanceFeatures

```python
@dataclass(frozen=True)
class InstanceFeatures:
    n_vars: int
    n_clauses: int
    n_hard: int
    n_soft: int
    hard_frac: float        # n_hard / n_clauses (0.0 if n_clauses == 0)
    hard_soft_ratio: float  # n_hard / n_soft   (inf-safe: n_soft==0 -> n_hard)
    total_soft_weight: int  # sum of soft weights (needed for cost conversion, §5)
```

`extract(wcnf) -> InstanceFeatures` computes all of these in one pass.

### Rule protocol

A rule is a named pure function over `(features, coeffs) -> concrete value`,
registered in a dict so the set is enumerable and each rule is unit-testable.

```python
Rule = Callable[[InstanceFeatures, dict], float | int | bool]
RULES: dict[str, Rule] = {}

def rule(name: str):
    def deco(fn): RULES[name] = fn; return fn
    return deco
```

### Initial rule set

```python
@rule("const")
def _const(f, c):   # {rule: const, value: X}
    return c["value"]

@rule("sqrt_vars")
def _sqrt_vars(f, c):  # {rule: sqrt_vars, a, lo, hi}
    return _clamp(round(c["a"] * math.sqrt(f.n_vars)), c["lo"], c["hi"])

@rule("linear_vars")
def _linear_vars(f, c):  # {rule: linear_vars, a, b, lo, hi}
    return _clamp(round(c["a"] * f.n_vars + c.get("b", 0)), c["lo"], c["hi"])

@rule("linear_clauses")
def _linear_clauses(f, c):  # {rule: linear_clauses, a, b, lo, hi}
    return _clamp(round(c["a"] * f.n_clauses + c.get("b", 0)), c["lo"], c["hi"])
```

You said you will hand me specific formulas later. `const` + `sqrt_vars` +
`linear_vars` cover the stated intent ("200 vars -> pop_size 50"); `linear_clauses`
is a placeholder for when clause count matters. Adding one is a single decorated
function; enumerate with `sorted(RULES)`.

### Every param resolves through a rule (uniform)

Even fixed params use `{rule: const, value: X}`. Uniformity means the resolver
always emits *both* the rule spec and the concrete value into the record, and the
"derived vs fixed" split reduces to "which rule name". `resolve_params` returns two
parallel dicts:

```python
resolved   = {"pop_size": 50, "polish_flips": 1000, "tournament_k": 4, ...}   # concrete
param_rules = {"pop_size": {"rule": "sqrt_vars", "a": 3.5, "lo": 20, "hi": 200}, ...}  # provenance
```

Both go into the JSONL record (§8). A record with only the rule is not reproducible
if the rule code changes; only the value loses provenance. Store both.

### Resolution order (stated explicitly)

`rule defaults  <  YAML  <  CLI override flag  <  (then derive per instance)`

- Rule defaults: coefficient defaults baked into the rule fn (e.g. `b=0`).
- YAML: authoritative surface; picks rule name + coeffs.
- CLI `-D ea.pop_size=50`: a **concrete** value bypasses the rule for that param.
  It is recorded as `param_rules["pop_size"] = {"rule": "cli_override", "value": 50}`
  so the record shows the rule was bypassed. This is the debug escape hatch.
- Derive: apply the resolved rule to this instance's features -> concrete value.

### Derived vs fixed split (proposed)

| Param | Kind | Default rule | Justification |
|---|---|---|---|
| `ea.pop_size` | **derived** | `sqrt_vars` | Only pop-scale knob that varied across the config zoo; scales with search-space size. |
| `ea.polish_flips` | **derived** | `linear_vars` | Varied 5..12500 across zoo; polish cost should scale with instance size, not be retyped. |
| `ea.tournament_k` | fixed | `const 4` | Constant across zoo. |
| `ea.pmutate` | fixed | `const 0.02` | Constant across zoo. |
| `ea.elitism` | fixed | `const true` | Constant. |
| `ea.elite_frac` | fixed | `const 0.05` | Currently hardcoded `0.05*pop_size` (`memetic.py:80`); lift to a named const. |
| `ea.max_gens` | fixed | `const 100` | Constant; but see §11 Q1 (it is also the reproducibility bound). |
| `polish.time_limit_s` | fixed | `const 0.05` | Per-polish cap; a knob, not size-derived. |
| `polish.noise` | fixed | `const 0.10` | Constant on EA path. |
| `budget.time_limit_s` | **explicit, never derived** | — | Wall-clock cap; always stated by hand. |

Matches your GUESS.

### Example YAML

```yaml
# maxsat_new/configs/memetic_ea.yaml
solver: memetic_ea
instance: maxsat_new/tests/data/mini.wcnf
seed: 1

budget:
  max_gens: 100          # deterministic bound (reproducible runs; see PORT_NOTES §11 Q1)
  time_limit_s: 60.0     # wall-clock safety cap; never derived

ea:
  pop_size:     { rule: sqrt_vars,   a: 3.5, lo: 20, hi: 200 }
  polish_flips: { rule: linear_vars, a: 10,  b: 0, lo: 2000, hi: 50000 }
  tournament_k: { rule: const, value: 4 }
  pmutate:      { rule: const, value: 0.02 }
  elitism:      { rule: const, value: true }
  elite_frac:   { rule: const, value: 0.05 }

polish:
  time_limit_s: 0.05
  noise: 0.10
  hard_safe: true

provider:
  kind: noop             # memetic_ea forces noop; llm_guided_base reads noop | random
```

`llm_guided_base.yaml` is identical except `solver: llm_guided_base` and
`provider.kind: noop` (control step) then later `random`.

---

## 5. State / Advice / Provider definitions

Two different "state" objects exist; keep them distinct in the port:

- **`SatState`** (`state.py`, internal): the incremental local-search bookkeeping
  used by `walksat_polish`. Not exposed to providers.
- **`State`** (`providers.py`, the seam): a read-only snapshot handed to a provider.

### State (snapshot passed to a provider)

```python
@dataclass(frozen=True)
class State:
    assign: tuple[bool, ...]                 # var truth values, 1-based; index 0 unused
    violated_hard: tuple[tuple[int, tuple[int, ...]], ...]  # (clause_idx, lits) per violated hard clause
    cost: int                                # current best_cost = unsatisfied soft weight (lower better)
    n_hard_violations: int                   # len(violated_hard); tracked separately per §"cost convention"
    generation: int                          # EA generation this child belongs to
    seed: int                                # the run's master seed
    n_vars: int                              # convenience; == len(assign) - 1
```

`violated_hard` comes straight from `hardviol.violated_hard_clauses` (§10 step). It
is the load-bearing field the future LoRA training set reads, so it is a first-class
member of the snapshot, not recomputed ad hoc. `assign` is an immutable tuple so a
provider cannot mutate solver state; edits come back only via `Advice`.

### Advice (what a provider returns)

Reuses `src/llm/advisor.py:LLMAdvice` field-for-field — that contract is sane.

```python
@dataclass(frozen=True)
class Advice:
    flip_vars: tuple[int, ...] = ()          # variable indices to flip
    set_true: tuple[int, ...]  = ()          # force True
    set_false: tuple[int, ...] = ()          # force False
    note: str = ""                           # free-text reason (logged, not acted on)
```

`apply_advice(assign01, advice) -> list[bool]` ported verbatim from
`advisor.py:41` (bounds-checked, returns a new list, forces `out[0]=False`). With an
empty `Advice` it returns an exact copy — this is what makes NoopProvider a true
no-op (§6, §10 step 8).

### Provider protocol

```python
class Provider(Protocol):
    def propose(self, state: State) -> Advice: ...
```

Flattened from the original two layers. In `src/llm`, `LLMProvider.complete(str)->str`
(`advisor.py:16`) plus a separate `LLMAdvisor` that builds a prompt and parses JSON
(`advisor.py:67`) is over-structured for non-LLM providers. We collapse to
`propose(state) -> Advice`. A future LLM provider hides prompt-build + `complete` +
JSON-parse *inside* its own `propose`; the seam does not change.

```python
class NoopProvider:
    def propose(self, state: State) -> Advice:
        return Advice()                       # empty -> apply_advice is identity

class RandomPerturbationProvider:
    def __init__(self, k: int = 3): self.k = k
    def propose(self, state: State) -> Advice:
        rng = random.Random(_provider_seed(state))   # OWN rng; does NOT touch EA rng
        k = min(self.k, state.n_vars)
        return Advice(flip_vars=tuple(rng.sample(range(1, state.n_vars + 1), k)))
```

**Critical determinism rule:** a provider gets its randomness from a seed *derived*
from `(state.seed, state.generation, child_index)` — `_provider_seed` — and **never
draws from the EA's master RNG**. This is what lets memetic_ea (Noop) reproduce
`run_ea.py` (§10 step 6) *and* lets llm_guided_base+Noop stay bit-identical to
memetic_ea (§10 step 8): the EA's RNG stream is unchanged by the seam's presence.
Switching Noop -> Random changes only the child bits (via advice), which is exactly
the experimental signal we want to measure.

---

## 6. Where the provider hook goes in `run_memetic`

Placement mirrors the original (dead) intent (`memetic.py:104-111`): per child,
between mutation and polish.

Per-child pipeline in the ported core:
```
child = clause_aware_crossover(p1, p2, ...)      # consumes EA rng
mutate(child, ...)                                # consumes EA rng
state  = build_state(child, gen, seed)            # snapshot + violated_hard
advice = provider.propose(state)                  # NO EA rng draw (provider self-seeds)
child  = apply_advice(child, advice)              # identity when Advice() empty
child, flips = short_polish(child, ..., rng_seed=rng.randrange(1<<30))  # consumes EA rng
evaluate(child)
```

- **Which children:** every child, every generation (elites are copied, not
  proposed on).
- **How often:** once per child = `pop_size - elite_count` calls per generation.
- **Cost against the time budget:** the provider call runs *inside* the timed EA
  loop (`while (time()-start) < time_cap`), so its wall cost is charged implicitly,
  no separate accounting. For Noop/Random this is negligible. (When a real LLM lands
  later it will need a per-call timeout and explicit charge — flagged, out of scope.)

The snapshot build calls `hardviol.violated_hard_clauses` once per child. That is
the only added per-child cost versus the original; it does not consume EA RNG.

---

## 7. Runner flag surface (deliberately small)

YAML is primary and authoritative; flags are a debugging escape hatch that override.

| Flag | Earns its place because |
|---|---|
| `config` (positional, required) | The experiment record. The one thing always needed. |
| `--seed N` | Seed is the one axis a sweep script varies per run without rewriting YAML. |
| `--instance PATH` | Debug a single file against an otherwise-fixed config. |
| `--out PATH` | Redirect JSONL per run in a sweep; keeps the config file stable. |
| `--solver NAME` | A/B the same config through memetic_ea vs llm_guided_base quickly. |
| `-D KEY=VALUE` | Generic dotted override (e.g. `-D ea.pop_size=50`). The escape hatch; recorded as `cli_override` in provenance (§4). |

Six flags, no more. No `--pop-size`, `--pmutate`, etc. — those live in YAML or `-D`.
Everything except `config` is an override; nothing here is the *intended* way to run
an experiment.

---

## 8. JSONL record schema (from HARNESS §2.3, cut)

One line per run. Kept fields and cuts:

```json
{
  "instance": "maxsat_new/tests/data/mini.wcnf",
  "instance_sha256": "…",
  "n_vars": 100, "n_clauses": 600, "n_hard": 100, "n_soft": 500,
  "solver": "memetic_ea",
  "solver_version": "0.1.0",
  "seed": 1,
  "budget": { "max_gens": 100, "time_limit_s": 60.0 },
  "wall_time_s": 4.02,
  "generations": 100,
  "children": 5000,
  "total_flips": 812340,
  "best_cost": 412,                      // UNSATISFIED soft weight (lower better)
  "n_hard_violations": 0,                // tracked separately (cost convention)
  "best_assignment_hash": "blake2b-12:…",// cheap; the proof for §10 steps 6 & 8
  "resolved_params": { "pop_size": 50, "polish_flips": 1000, "tournament_k": 4, "pmutate": 0.02, "elitism": true, "elite_frac": 0.05 },
  "param_rules": { "pop_size": {"rule":"sqrt_vars","a":3.5,"lo":20,"hi":200}, "polish_flips": {"rule":"linear_vars","a":10,"b":0,"lo":2000,"hi":50000}, "...": "..." },
  "provider": { "kind": "noop" },
  "config_hash": "9f3c…",
  "status": "ok",
  "git_sha": "1e3eaaf"
}
```

`best_cost` = `total_soft_weight - satisfied_soft_weight` — converted at the boundary
in `memetic.py` (the core computes satisfied weight; the record stores unsatisfied,
per the one-cost convention). `n_hard_violations` separate.

**Cuts, one line each:**
- `instance_family` — needs `make_metadata`; not built yet. Join later on `instance`.
- `anytime_curve` — milestone compares final `best_cost`; curves are a later pass
  (STRATIFICATION_PLAN §2 anytime). Biggest cut; re-add when needed.
- `best_assignment_path` / `--save-assignments` — the hash suffices to prove two
  runs match; full sidecar is a later verification need.
- `hardware` block (cpu/gpu/apptainer) — single-machine CPU-only study; `git_sha`
  is enough provenance. Re-add if runs move to the cluster.
- `iterations` — renamed to `generations` (EA's real unit).
- `notes` — empty string cargo; drop.
- `solver_version` — kept (cheap, disambiguates a re-port).

**Additions vs §2.3:** `resolved_params` + `param_rules` (the reproducibility
requirement — both concrete value and its rule), `n_hard_violations` (separate cost),
`generations`/`children`/`total_flips` (EA-native counters already produced).

---

## 9. Suspected, not changed

Per the porting rule ("suspected bugs are RECORDED, not fixed"), the port must
reproduce these behaviors bit-for-bit. Listing what I found rather than leaving this
empty — an undocumented known bug would violate the porting rule.

1. **Stale `hard_satisfied` fed to `mutate1`** (`memetic.py:93`). `ind` is a leaked
   loop variable (last init-population member, `memetic.py:56`), not the current
   child. Its `hard_satisfied` list is mutated in place and shared across all
   children of all generations. So `mutate1`'s "don't break a satisfied hard clause"
   guard operates against the wrong assignment. **Load-bearing for §10 step 6** —
   the port must replicate the exact same shared/stale list, or the RNG-accept
   pattern diverges and costs won't match. Flag for a future fix once fidelity is
   locked.
2. **`ls.flip_budget` is dead on the EA path** (`_ls_budget` -> `max_flips`, shadowed
   by `ls_polish_flips` in `short_polish`, `operators.py:402`). Not a crash; explains
   config-zoo noise. Port drops the shadowed key; behavior unchanged.
3. **`short_polish` redundant key lookup** (`operators.py:403`):
   `ls_cfg.get("time_limit_s", ls_cfg.get("time_limit_s", 0.05))` — same key twice.
   Harmless; port writes it once.
4. **Dual meaning of `time_limit_s`.** Top-level = EA wall cap; `ls.time_limit_s` =
   per-polish cap; if top-level is absent, `ls.time_limit_s` silently becomes *both*
   (`memetic.py:63`). Port disambiguates into `budget.time_limit_s` vs
   `polish.time_limit_s`; behavior preserved when both are set.
5. **`parse_dimacs` skips any line starting with `"0"` or `"%"`** (`cnf.py:39`).
   A clause line beginning with token `0…` would be dropped. Edge case; replicate.
6. **CNF -> all soft, weight 1, no hard** (`cnf.py:80-82`). Intentional per HARNESS
   §5 Q1, but surprising; documenting so it is not "fixed" by accident.

---

## 10. Step list

Each step: one PR, one test that fails before and passes after, nothing else
touched. Steps 6 and 8 are the two mandatory load-bearing ones.

| # | Change | The one test | Unblocks |
|---|---|---|---|
| 1 | `__init__.py` + `cnf.py` (WCNF, parse_dimacs, eval_assignment) | parse committed `mini.wcnf`; assert `n_vars`, `n_clauses`, hard count, and `eval_assignment` on a known assignment | everything (instances load) |
| 2 | `state.py` + `walksat.py` (`walksat_polish` only) | `walksat_polish` on fixed start + seed twice -> identical `final_assign` (determinism) | polish available |
| 3 | `population.py` + `operators.py` (crossover1, mutate1, short_polish, tournament) | seeded `Population.init_seeds` + one crossover+mutate reproducible across two runs | EA operators available |
| 4 | `features.py` + `sizing.py` (rules + `resolve_params`) | `sqrt_vars` clamps at lo/hi; `resolve_params` emits both concrete value and rule spec; `sorted(RULES)` enumerates | config resolution |
| 5 | `config.py` (YAML load + resolution order) | defaults<YAML<`-D` order; a `-D` concrete value is recorded as `cli_override` | runner config |
| 6 | `hardviol.py` (`violated_hard_clauses`) + `providers.py` (State, Advice, apply_advice, NoopProvider) | on a known instance+assignment, `violated_hard_clauses` returns the expected `(idx, lits)`; `apply_advice(x, Advice())` is identity | the seam; training-set signal |
| 7 | `memetic.py` core `run_memetic(instance, params, seed, provider)` | 1s / small-`max_gens` run returns a valid result; same seed twice with `max_gens` bound -> identical `best_cost` and assignment hash | the solver |
| **8** | `registry.py` + `solvers.py` (`memetic_ea`) + convert cost to unsat-weight | **`memetic_ea` reproduces `src/cli/run_ea.py`'s `best_cost` and `hard_violations` exactly** at a fixed seed under a `max_gens` bound (test runs old CLI via subprocess, new via import, compares) | **licenses deleting `src/` later** |
| 9 | `record.py` (RunRecord + JsonlRecorder + config_hash) + `run.py` CLI | `python -m maxsat_new.run configs/memetic_ea.yaml` writes one schema-valid JSONL line; round-trip parse | end-to-end runs |
| **10** | `llm_guided_base` solver + wire NoopProvider through the seam | **`llm_guided_base` + NoopProvider is bit-identical to `memetic_ea`** at the same seed (equal `best_cost` *and* `best_assignment_hash`) | proves the comparison measures the LM, not plumbing |
| 11 | `RandomPerturbationProvider` as the `llm_guided_base` control | with `provider.kind: random`, run twice -> identical (self-seeded); and differs from Noop run (perturbation is live) | the actual control baseline |

Note on steps 6 & 8: both require a **deterministic budget** (`max_gens` with a large
time cap) so the run is bit-reproducible. Under a wall-clock budget the generation
count varies and bit-identity does not hold — see §11 Q1.

---

## 11. Open questions (recommendation + one-line tradeoff)

1. **Reproducibility budget.** "One seed -> bit-identical run" holds only under a
   deterministic bound (max_gens / flip cap), not wall-clock. **Recommend:** make the
   canonical experiment budget iteration-based (`max_gens`) with `time_limit_s` as a
   secondary safety cap; the two load-bearing tests use `max_gens`. *Tradeoff:*
   iteration budgets are reproducible but give unequal compute per instance; wall
   budgets are fair-compute but not bit-reproducible.
2. **What `memetic_ea` == `run_ea.py` is pinned against.** `run_ea.py` defaults EA
   on and reads its own key layout. **Recommend:** the step-8 fidelity test drives
   the *old* CLI with a fixed committed config + seed + `max_gens`, and asserts equal
   `best_cost`/`hard_violations` only (not internal counters). *Tradeoff:* looser
   (cost-only) match tolerates cosmetic differences but could hide a real stream
   divergence; a full assignment-hash match is stricter but brittle to any harmless
   reorder.
3. **Replicate the stale-`hard_satisfied` bug (§9.1) or fix it first.**
   **Recommend:** replicate exactly for steps 6/8, fix in a later PR with its own
   before/after test. *Tradeoff:* replicating preserves fidelity but ports a known
   bug; fixing first means step 6 can't use `run_ea.py` as the oracle.
4. **RandomPerturbationProvider's `k` (flip count).** Fixed const, or its own sizing
   rule over `n_vars`? **Recommend:** start `const k=3`; promote to a rule if a sweep
   wants it. *Tradeoff:* const is simple but may not scale to large instances; a rule
   adds a knob before there's evidence it matters.
5. **`elite_frac` derived or fixed.** Currently hardcoded `0.05` (`memetic.py:80`).
   **Recommend:** fixed `const 0.05`. *Tradeoff:* deriving it couples population and
   elite scaling with no current evidence that's wanted.
6. **`results/` committed or gitignored.** **Recommend:** gitignore; JSONL is run
   output, not source. *Tradeoff:* gitignore keeps the tree clean but loses run
   history from git; committing bloats the repo.
