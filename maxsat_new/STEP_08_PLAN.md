# Step 08 plan — the `memetic_ea` oracle test

Plan only. **No code is shipped by this doc**; nothing outside this file was
created or edited, and no solver was run to produce it.

Target: PORT_NOTES.md §10 **step 8** — *"`memetic_ea` reproduces
`src/cli/run_ea.py`'s `best_cost` and `hard_violations` exactly at a fixed seed
under a `max_gens` bound (test runs old CLI via subprocess, new via import,
compares)"*. This is one of the two load-bearing steps: it is what licenses
deleting `src/` later.

Port source sha: **`1e3eaaf`**. Current HEAD `83ace37`. `git log 1e3eaaf..HEAD --
src/ configs/ data/dev_small/` is empty — **the oracle side of the comparison has
not moved since the port began**, so every `src/…:line` reference below is valid
at both shas.

---

## 0. Summary of what this doc pins

| Thing | Pinned to |
|---|---|
| Old-side command | `python src/cli/run_ea.py <wcnf> -c <oracle_old.yaml> --seed <N> --out-json <tmp>/old.json --quiet` |
| Parsed keys | `best_soft_weight` (**satisfied** soft weight), `hard_violations` |
| Conversion | **New side converts**: `best_cost = total_soft_weight − best_soft_weight`; the test applies the identical formula to the old JSON |
| Instance | `data/dev_small/file_rpms_wcnf_L3_V100_C600_H100_0.wcnf` — `total_soft_weight = 500` |
| Old config | **none of the 8 committed EA configs qualify**; add `maxsat_new/tests/data/oracle_old.yaml` (§2) |
| New config | add `maxsat_new/tests/data/oracle_new.yaml`, `pop_size`/`polish_flips` pinned with `{rule: const, value: X}` |
| Budget | `max_gens=100`, `pop_size=12`, `polish_flips=100`; `budget.time_limit_s=1000.0`, `polish.time_limit_s=10.0` (§5 explains the 10.0) |
| RNG | per child: `sample, sample, random × n_vars, randrange, randrange` — identical on both paths, including the `src:108` draw the port kept |

---

## 1. `run_ea.py` invocation and output contract

### 1.1 Invocation

`main()` at `src/cli/run_ea.py:140`. Argument surface (`:145-153`):

| Arg | Kind | Line | Notes |
|---|---|---|---|
| `wcnf` | **positional**, required | `:145` | path to the instance |
| `-c` / `--cfg` | flag | `:146` | YAML (or JSON) config file |
| `--seed` | flag, `int`, **default 1** | `:147` | passed to `run_memetic(..., rng_seed=args.seed)` at `:187` |
| `-D` / `--override` | flag, repeatable | `:148` | `KEY=VALUE`, dotted, JSON-literal value (`:92-106`, `:181-183`) |
| `--use-internal-parser` | flag | `:150` | **must NOT be passed** — see §1.2 |
| `--out-json` | flag | `:152` | write result JSON to a file instead of stdout (`:206-210`) |
| `--quiet` / `-q` | flag | `:153` | suppress the human summary |

The seed is a **flag**, the instance is **positional**, the config is a **flag**.
There is no `--instance`, no `--max-gens`, no `--pop-size`.

**The exact command line the test will run** (from the repo root):

```
<sys.executable> src/cli/run_ea.py \
    data/dev_small/file_rpms_wcnf_L3_V100_C600_H100_0.wcnf \
    -c maxsat_new/tests/data/oracle_old.yaml \
    --seed 7 \
    --out-json <tmp_path>/old.json \
    --quiet
```

Run with `cwd = <repo root>` and a `subprocess.run(..., timeout=…)`. Running it
as a **script path** (not `-m`) is required and sufficient: `src/cli/run_ea.py:9-15`
tries `from evo.memetic import run_memetic`, fails when invoked as a script, and
in the `except` branch appends *parent-of-`src`*… actually
`os.path.join(os.path.dirname(__file__), "..")` = `src/`, which is what makes both
`evo.*` and `sat.*` importable. Verified working: `--help` renders.

Three flag choices that matter:

- **`--out-json <tmp>`** wins over any `io.out_json` in the config (`:196`:
  `if not args.out_json and "out_json" in cfg_io`). Writing to a tmp file rather
  than parsing stdout removes the whole class of "did something print to stdout"
  risks and keeps `runs/` clean.
- **`--quiet`** is passed for intent, though on this path it is inert: the
  human-summary print at `:203` is nested *inside* `if not args.quiet and "quiet"
  in cfg_io:` (`:199`), an indentation bug, and the oracle config has no `io:`
  block, so `cfg_io == {}` and the branch never runs. Recorded, not relied on.
- **`--use-internal-parser` is never passed**, so the run uses
  `sat.cnf.WCNF.parse_dimacs` (`:161-163`), the parser `maxsat_new/cnf.py` was
  ported from — not the redundant in-file `_parse_wcnf` (`:36-79`), which would
  read weights as `float` and is a *different* parser. Already verified: on the
  pinned instance the two parsers agree clause-by-clause including `pos_adj` /
  `neg_adj`.

### 1.2 Output: where the two numbers live

They are **top-level keys of the result JSON**, produced by
`src/evo/memetic.py:168-182` and serialized unchanged by the CLI:

```
src/cli/run_ea.py:187    res = run_memetic(wcnf, cfg, rng_seed=args.seed)
src/cli/run_ea.py:205    out_json = json.dumps(res, ensure_ascii=False)
src/cli/run_ea.py:206-208    if args.out_json: … f.write(out_json + "\n")
```

The producing lines:

```
src/evo/memetic.py:166       soft, hv = evaluate_assignment(wcnf, best.assign01)
src/evo/memetic.py:169       "best_soft_weight": float(soft),
src/evo/memetic.py:170       "hard_violations": int(hv),
```

So the file is one line of JSON with, among others:

| Key | Type in JSON | Meaning |
|---|---|---|
| `best_soft_weight` | **float** (`float(soft)`, `:169`) | **SATISFIED** soft weight |
| `hard_violations` | int | number of violated hard clauses |
| `total_flips` | int | fidelity canary (§7) |
| `meta.ea_generations`, `meta.children` | int | canaries |
| `meta.assign_bits` | str of `"0"`/`"1"`, vars 1..n | canary — the full best assignment (`memetic.py:130`, via `_assignment_exports`) |

### 1.3 The sign, settled

`best_soft_weight` is **satisfied** soft weight, not unsatisfied. Evidence, not
inference — `src/evo/population.py:67-87`:

```
:81   if cl.is_hard:
:82       if not sat: hard_viol += 1
:85   else:
:86       if sat: soft_w += float(cl.weight)      # accumulates on SAT
```

Weight is added **when the soft clause is satisfied**. Hard clauses contribute
nothing to `soft_w`; they contribute only to `hard_viol`.

This agrees with both cross-checks:

- **STEP_07_NOTES** ("`best_soft_weight`: SATISFIED soft weight (src's key
  name)") and `maxsat_new/memetic.py:318-325`, which calls the *same*
  `population.evaluate_assignment` and returns `int(soft)` under the same key.
  The only difference is `int` vs `float` — numerically equal, and STEP_07
  deviation 6 already records it.
- **PORT_NOTES §8**: `best_cost` = `total_soft_weight − satisfied_soft_weight`,
  UNSATISFIED soft weight, lower better.

**Which side converts:** the **new** side. `solvers.py:memetic_ea` computes
`best_cost = features.extract(wcnf).total_soft_weight − res["best_soft_weight"]`
and adds it to the result dict (PORT_NOTES §8, §10 row 8 "convert cost to
unsat-weight"). `run_ea.py` never computes a cost and must not be asked to; the
test applies the **same formula with the same constant** to the old JSON:

```python
TOTAL_SOFT_WEIGHT = 500          # asserted from features.extract, not hardcoded blindly
old_best_cost = TOTAL_SOFT_WEIGHT - int(old["best_soft_weight"])
assert old_best_cost == new["best_cost"]
assert int(old["hard_violations"]) == int(new["hard_violations"])
```

Since the conversion is affine and identical on both sides, asserting `best_cost`
equality is exactly as strong as asserting `best_soft_weight` equality — the test
should assert **both**, so a failure says immediately whether the disagreement is
in the EA or in the conversion.

> One in-scope consequence to note and *not* silently do: STEP_07 deferred the
> `State.cost` sign to step 8 (`maxsat_new/memetic.py:101-112`,
> `test_build_state_fields` pins `state.cost == satisfied`). Inverting
> `State.cost` needs `total_soft_weight` plumbed into `build_state` and touches a
> committed module plus its test. It is **inert under `NoopProvider`** (STEP_07
> §4), so it cannot affect the oracle result. Recommendation: **do not ride it
> along with the oracle PR** — ship it as a separate small PR 8b (§8), so a red
> oracle can never be confused with a seam change. It must land before step 11,
> where a provider may actually read `state.cost`.

---

## 2. The old-side config

### 2.1 No committed `configs/*.yaml` qualifies

All 8 have `ea.enabled: true`. What `run_memetic` actually reads from each
(`_ea_cfg` `src/evo/memetic.py:11-20`, `_ls_budget` `:23-30`, `time_cap` `:63`,
`max_gens` `:65`):

| config | `ea.pop_size` | `ls.ls_polish_flips` | `ls.time_limit_s` (per-polish) | top-level `time_limit_s` (EA cap) | `ea.max_gens` | qualifies? |
|---|---|---|---|---|---|---|
| `cfg.yaml` | 80 | 700 | 0.05 | **absent** → falls back to `ls.time_limit_s` = **0.05** (`:63`) | default 100 | no |
| `cfg2.yaml` | 110 | 500 | 0.001 | 0.05 | default 100 | no |
| `cfg3.yaml` | 110 | 5 | 0.001 | 0.05 | default 100 | no |
| `cfg250.yaml` | 50 | 500 | 0.1 | 180 | default 100 | no |
| `cfghard1.yaml` | 50 | 2000 | 0.1 | 300 | default 100 | no |
| `hard2.yaml` | 50 | 2000 | 0.1 | 180 | default 100 | no |
| `hard3.yaml` | 75 | 12500 | 0.5 | 600 | default 100 | no |
| `ea_cfg.yaml` | 60 | 700 | 0.05 | 10.0 | 100 | no |

Two independent disqualifiers, and **every** config trips at least one:

1. **Per-polish cap never large.** The largest committed `ls.time_limit_s` is
   `0.5` (`hard3.yaml`), the smallest `0.001`. A 100–12500-flip polish on a
   100-var instance does not finish in 1 ms, so `walksat_polish`'s own clock
   (`time_up()`, `maxsat_new/walksat.py:117-118`, checked in the flip loop
   condition at `:135`) truncates the polish on a machine-speed-dependent
   iteration. That is the exact failure STEP_07 warned about
   ("Determinism: both budgets must be iteration-bound").
2. **EA cap too small for `max_gens=100` to bind.** `cfg.yaml`/`cfg2`/`cfg3` cap
   the whole EA at 0.05 s; `ea_cfg.yaml` at 10 s, well under the ~2 minutes its
   own 60×700 settings need on V100_C600. `cfg250`/`cfghard1`/`hard2`/`hard3`
   have generous EA caps but fail (1).

Every one also carries an `io.out_json` block writing into `runs/`, which the
test would have to override anyway (`run_ea.py:196-197`).

Note in passing: **`ea.enabled` is inert on this path.** `_ea_cfg` reads it
(`memetic.py:14`) into the dict, and `run_memetic` never branches on it — it
consumes only `pop_size`, `tournament_k`, `pmutate`, `elitism` (`:45-49`). The
CLI also force-defaults it to `True` (`run_ea.py:177-179`). So "has
`ea.enabled: true`" is a labelling convention, not a gate.

### 2.2 The oracle config to add

Add **`maxsat_new/tests/data/oracle_old.yaml`** — old schema, read by
`run_ea.py -c`. Deliberately **not** in `configs/`: `src/`, `configs/` and
`data/` have not moved since `1e3eaaf` (§0) and the oracle should not be the
thing that changes that. It lives next to the test that owns it, beside
`mini.wcnf` / `hardmix.wcnf`.

```yaml
# maxsat_new/tests/data/oracle_old.yaml
# OLD-schema config, consumed ONLY by src/cli/run_ea.py as the step-8 oracle.
# Every key here is one run_memetic actually reads (PORT_NOTES §1). Nothing else
# is listed, because nothing else is read on the EA path.
ea:
  enabled: true          # inert (see §2.1); stated for the reader
  pop_size: 12           # -> _ea_cfg, memetic.py:15
  tournament_k: 4        # -> _ea_cfg, memetic.py:16
  pmutate: 0.02          # -> _ea_cfg, memetic.py:17
  elitism: true          # -> _ea_cfg, memetic.py:18
  max_gens: 100          # -> memetic.py:65   (the binding budget)
ls:
  ls_polish_flips: 100   # -> _ls_budget, memetic.py:27 -> short_polish max_flips
  time_limit_s: 10.0     # -> _ls_budget, memetic.py:28 -> per-polish cap
time_limit_s: 1000.0     # -> memetic.py:63   EA wall cap (must be top level)
```

Four keys are deliberately **absent**, each for a reason the test reader needs:

- **`ls.flip_budget`** — read into `max_flips` (`memetic.py:29`) but shadowed:
  `short_polish` resolves `ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips"))`
  (`src/evo/operators.py:402`), so `ls_polish_flips` always wins. PORT_NOTES §9.2.
  Including it would imply it does something.
- **`ls.noise` / `ls.hard_safe`** — **they never reach `short_polish`.**
  `_ls_budget` (`memetic.py:23-30`) returns a *new* dict containing only
  `ls_polish_flips`, `time_limit_s`, `max_flips`. Everything else in the YAML
  `ls:` block is dropped on the floor. So `short_polish` falls back to its own
  defaults `noise=0.10`, `hard_safe=True` (`operators.py:404-405`) **regardless of
  the config** — this is why `ea_cfg.yaml`'s `ls.noise: 0.25` has no effect. The
  new side must therefore use `polish.noise: 0.10`, not 0.25. This is the single
  easiest way to get the oracle wrong.
- **`io:`** — omitted so `cfg_io == {}`; `--out-json` supplies the destination.
- **`ea.ls_polish_flips`** — `_ea_cfg:19` reads it into the ea dict, and
  `run_memetic` never uses that entry (the polish budget comes from
  `ls.ls_polish_flips`). `ea_cfg.yaml:12-13` already says so in a comment.

**`-D`-only alternative** (equivalent, no new YAML; useful for a one-off repro):
`-D ea.pop_size=12 -D ea.tournament_k=4 -D ea.pmutate=0.02 -D ea.elitism=true
-D ea.max_gens=100 -D ls.ls_polish_flips=100 -D ls.time_limit_s=10.0
-D time_limit_s=1000.0` with no `-c`. `-D` values are JSON literals
(`run_ea.py:102`), so `true` and `10.0` parse as bool/float. The YAML form is
preferred for the committed test: it is one diffable artifact sitting next to
`oracle_new.yaml`, which is what makes the §3 table auditable.

---

## 3. Config equivalence — the concrete values, both sides

Both columns are **concrete values fed to the EA**, not YAML text. The old column
traces the value through `_ea_cfg` / `_ls_budget`; the new column shows the rule
spec and what it resolves to.

| Concrete param | OLD (`run_ea.py` + `oracle_old.yaml`) | NEW (`memetic.run_memetic` + `oracle_new.yaml`) |
|---|---|---|
| `pop_size` | `12` — `ea.pop_size` → `_ea_cfg` `memetic.py:15` → `src:45` | `12` — `ea.pop_size: {rule: const, value: 12}` → `resolved_params["pop_size"]` → `maxsat_new/memetic.py:165` |
| polish flip budget | `100` — **`ls.ls_polish_flips`** → `_ls_budget` `memetic.py:27` → `short_polish` `operators.py:402` → `walksat_polish(max_flips=100)` | `100` — **`ea.polish_flips`: `{rule: const, value: 100}`** → `maxsat_new/memetic.py:170` → `short_polish(polish_flips=100)` → `walksat_polish(max_flips=100)` |
| `tournament_k` | `4` — `ea.tournament_k` → `memetic.py:16` → `src:47` | `4` — `{rule: const, value: 4}` → `memetic.py:166` |
| `pmutate` | `0.02` — `ea.pmutate` → `memetic.py:17` → `src:48` | `0.02` — `{rule: const, value: 0.02}` → `memetic.py:167` |
| `elitism` | `True` — `ea.elitism` → `memetic.py:18` → `src:49` | `True` — `{rule: const, value: true}` → `memetic.py:168` |
| `elite_frac` | `0.05` — **hardcoded**, `src:80` `max(1, ceil(0.05 * pop_size))` → `1` | `0.05` — `{rule: const, value: 0.05}` → `maxsat_new/memetic.py:234` `max(1, ceil(0.05*12))` → `1` |
| `max_gens` | `100` — `ea.max_gens` → `src:65` → loop `src:76` | `100` — `budget.max_gens` → `memetic.py:172` → loop `:225` |
| EA wall cap | `1000.0` — **top-level** `time_limit_s` → `src:63` | `1000.0` — `budget.time_limit_s` → `memetic.py:173` |
| per-polish cap | `10.0` — `ls.time_limit_s` → `_ls_budget` `memetic.py:28` → `walksat_polish(time_limit_s=10.0)` | `10.0` — `polish.time_limit_s` → `memetic.py:175` → `short_polish(time_limit_s=10.0)` |
| polish `noise` | `0.10` — **not configurable**: `_ls_budget` drops `ls.noise`; `operators.py:404` default | `0.10` — `polish.noise: 0.10` → `memetic.py:176` |
| polish `hard_safe` | `True` — **not configurable**: `_ls_budget` drops `ls.hard_safe`; `operators.py:405` default | `True` — `polish.hard_safe: true` → `memetic.py:177` |
| polish `smooth_every` / `rho` | `0` / `0.5` — `operators.py:406-407` defaults | `0` / `0.5` — `maxsat_new/operators.py:295-296` defaults, not exposed in config |
| provider | `LLMAdvisor(NoopProvider())`, hardcoded `src:43` | `NoopProvider()`, forced by `memetic_ea` regardless of `provider.kind` (PORT_NOTES §4) |
| seed | `--seed 7` → `run_memetic(rng_seed=7)` `run_ea.py:187` | `seed: 7` → `ResolvedConfig.seed` → `run_memetic(..., seed=7)` |

### 3.1 Why `pop_size` and `polish_flips` must be pinned with `const`

`config.DEFAULT_EA_PARAMS` (`maxsat_new/config.py:64-71`) makes these two
**derived** by default (PORT_NOTES §4). On this instance (`n_vars=100`) the
defaults resolve to:

- `pop_size`: `sqrt_vars` `{a:3.5, lo:20, hi:200}` → `clamp(round(3.5*√100)) = 35`
- `polish_flips`: `linear_vars` `{a:10, b:0, lo:2000, hi:50000}` →
  `clamp(round(10*100)=1000, 2000, 50000) = **2000**` (the `lo` clamp bites)

Neither matches the old side, and worse, both would silently **float** if a later
PR tunes the rule coefficients — the oracle would start failing for a reason that
has nothing to do with the port. `{rule: const, value: X}` freezes them while
keeping the uniform "every param resolves through a rule" invariant (§4) and the
`resolved_params` / `param_rules` key-set invariant intact. A `-D
ea.pop_size=12` would also work and is recorded as `cli_override`
(`config.py:59, 300`), but a committed YAML is the artifact the equivalence table
above refers to, so prefer `const`.

### 3.2 The new-side config to add

```yaml
# maxsat_new/tests/data/oracle_new.yaml
# NEW-schema mirror of oracle_old.yaml. Every value must match the OLD column
# of STEP_08_PLAN §3 exactly. pop_size/polish_flips use `const` so the sizing
# rules cannot float them (§3.1).
solver: memetic_ea
instance: data/dev_small/file_rpms_wcnf_L3_V100_C600_H100_0.wcnf
seed: 7

budget:
  max_gens: 100          # the binding budget
  time_limit_s: 1000.0   # EA wall cap; must never bind (§5)

ea:
  pop_size:     { rule: const, value: 12 }
  polish_flips: { rule: const, value: 100 }
  tournament_k: { rule: const, value: 4 }
  pmutate:      { rule: const, value: 0.02 }
  elitism:      { rule: const, value: true }
  elite_frac:   { rule: const, value: 0.05 }

polish:
  time_limit_s: 10.0     # per-polish cap; must never bind (§5)
  noise: 0.10            # NOT 0.25 — the old side cannot configure this (§2.2)
  hard_safe: true

provider:
  kind: noop
```

### 3.3 Sizing the run (why 12 / 100 / 100 and not 60 / 700 / 100)

`max_gens` stays at PORT_NOTES' 100; `pop_size` and `polish_flips` are what get
shrunk, because they are the two multiplicative terms in the cost:

```
children  = (pop_size − elites) × max_gens = (12 − 1) × 100 = 1100
polish work ≈ children × polish_flips      = 1100 × 100 ≈ 110k walksat iterations
```

Per walksat iteration the dominant term is `state._count_hard_violations()`
(`src/sat/walksat.py:594`), an O(n_clauses)=600 scan run **every** iteration, plus
`flip_var_effect` / `flip_var_hard_delta` over ~3 candidate vars. Order ~30 µs in
CPython ⇒ **~4 s of polish per side**, plus ~1–2 s of crossover / mutate /
evaluate / `SatState` construction: **≈ 5–8 s per side, ~15 s for the test.**

For contrast, `ea_cfg.yaml`'s 60/700 at `max_gens=100` is
`5700 children × 700 ≈ 4.0M` iterations ≈ **2–3 minutes per side** — a fine
opt-in soak, not a default test.

> This is the **one number in this plan that was estimated rather than measured**
> (mode is read-only; no solver was run). Task 0 of §8 is a calibration run that
> replaces the estimate with a measurement before anything else is written. If it
> exceeds ~30 s per side, lower `polish_flips` — **never** `max_gens`, which is
> the reproducibility bound.

---

## 4. RNG-stream reconciliation on the real instance

### 4.1 The old live path's draws, enumerated from source

Every `rng.*` call site reachable from `run_memetic` on the EA path (grepped
across `src/evo/*.py`, `src/sat/*.py`, `src/llm/*.py`):

| # | Old site | Draw | Count per child |
|---|---|---|---|
| — | `Population._new_assign_from_priors` `src/evo/population.py:137` | `rng.random()` × `n_vars`, once per member | init only: `pop_size × n_vars` = 12 × 100 = **1200** |
| 1 | `tournament` `src/evo/operators.py:17` via `src:89` | `rng.sample(pop, k)` | 1 |
| 2 | `tournament` via `src:90` | `rng.sample(pop, k)` | 1 |
| 3 | `clause_aware_crossover1` `src:91` | **none** — the only site is the `rng.choice([a, b])` tie-break at `operators.py:303`, unreachable (`a != b` ⇒ `{a,b} == {True,False}` ⇒ `chosen ∈ {a,b}` always) | 0 |
| 4 | `mutate1` `operators.py:337` via `src:93` | `rng.random()` **once per variable**, `for v in range(1, n+1)`; the `continue` happens *after* the draw (`:337`), so the count is `n_vars` regardless of accept/reject | 100 |
| 5 | `advisor.propose(..., rng_seed=rng.randrange(1 << 30))` `src:108` | `rng.randrange` — **LIVE**, value discarded | 1 |
| 6 | `short_polish(..., rng_seed=rng.randrange(1 << 30))` `src:113` | `rng.randrange` | 1 |

Per child: **`sample, sample, random × 100, randrange, randrange`** — exactly the
order STEP_07's `_expected_trace` replays.

### 4.2 The `src:108` draw is live, and the port kept it

PORT_NOTES §1/§3 call `src/evo/memetic.py:95-112` a dead block "wrapped in
`''''''''`". STEP_07 corrected this and I confirm the reading: `''''''''` is eight
quotes = `''''''` (empty triple-quoted string) + `''`, adjacent-concatenated into
one empty string used as an **expression statement**; `:96-111` are live siblings.
So `src:108` really does draw.

The port keeps it as its own statement, `maxsat_new/memetic.py:283`:

```python
_ = rng.randrange(1 << 30)          # src:108 -- the LIVE draw
```

Ordering is right: in `src`, `:108` is an *argument* of `advisor.propose`,
evaluated **before** the call; in the port the standalone statement precedes
`provider.propose(state)` (`:285`). Same position in the stream, and
provider-independent — step 11 cannot shift it.

### 4.3 The zero-draw region between mutate and polish, both sides

This is the only place the two paths differ structurally, so it is the only place
a draw could appear on one side and not the other. Verified draw-free on both:

| Old (`src`) | New (`maxsat_new/memetic.py`) | Draws? |
|---|---|---|
| `tmp_child = Individual(...)` `:96`; `pop.evaluate(wcnf, tmp_child)` `:97` | `state = build_state(...)` `:272` | none either side. `Population.evaluate` (`population.py:154-165`) is hash + memo + `evaluate_assignment`; `build_state` is `violated_hard_clauses` + `evaluate_assignment` (`maxsat_new/memetic.py:99-122`). Both pure. |
| `violated_idxs = []` `:99` | real `violated_hard` from `hardviol` | no RNG; inert under Noop (STEP_07 §4) |
| `advisor.propose(...)` `:104-110` → `prompt.build_prompt` / `extract_clause_examples` → `NoopProvider.complete` → `_safe_parse_json` | `provider.propose(state)` `:285` → `NoopProvider.propose` returns `Advice()` | **none**: grepping `src/llm/advisor.py`, `src/llm/prompt.py`, `src/llm/providers/noop.py` for `random|shuffle|sample|choice` returns **zero hits**; `NoopProvider.complete` returns the constant string `'{"flip": [], "set_true": [], "set_false": [], "note": "noop"}'` |
| `apply_advice(child_bits, advice)` `:111` (`advisor.py:41-64`) | `apply_advice(child_bits, advice)` `:288` | none; with empty advice, an identity copy on both sides |

**No site found where one path draws and the other does not.** The port's own
per-child polish RNG is also 1:1 — each `short_polish` builds its own
`random.Random(rng_seed)` (`walksat.py:100`, both trees), never touching the EA
rng, and STEP_07's ledger asserts `len(_INSTANCES) == 1 + CHILDREN`.

### 4.4 What the ledger does *not* cover, and why step 8 is still needed

The step-7 ledger pins draw *kinds*, *order*, and *values* — but only on
`mini.wcnf` (5 vars), where STEP_07 measured that a stream with the `src:108`
draw deleted still produced the identical cost **and hash**. Two residual gaps
this step closes:

1. **Instance-shape gaps.** `mutate1` draws `n_vars` `random()` per child
   *whatever the guard decides* — accept/reject changes bits, not draws. So a
   divergence in `hard_clauses` / `hard_occurs` / the §9.1 stale
   `hard_satisfied` list would be **invisible to a draw ledger** and visible only
   in the resulting assignment. On `mini.wcnf` there are 3 hard clauses; here
   there are 100, and the stale list actually matters.
2. **`crossover1`'s `rng.choice` tie-break.** The unreachability argument is
   structural, not instance-dependent, so it holds here too — but the ledger's
   `count("choice") == 0` assertion was only ever *executed* on 5 variables. The
   oracle run exercises 100 vars × 1100 children against the same claim.

Both are exactly why §10 makes step 8 load-bearing rather than treating step 7's
ledger as sufficient.

### 4.5 Port-fidelity spot checks done for this plan

An AST-level comparison (docstring-stripped, unparsed and re-parsed) of every
function shared by `src/` and `maxsat_new/` on the live path:

- `src/evo/population.py` ↔ `maxsat_new/population.py`: **all 12 functions
  identical**, including `init_seeds`, `_new_assign_from_priors`,
  `evaluate_assignment`, `evaluate`, `best`, `hash_assign`, `jw_priors`,
  `build_hard_occurs`, `init_hard_satisfied`.
- `src/evo/operators.py` ↔ `maxsat_new/operators.py`: `tournament`, `mutate1`,
  `_soft_proxy_scores` identical; `clause_aware_crossover1` differs only in
  annotations (`tuple[…]`→`Tuple[…]`) and non-ASCII characters in comments.
- `src/sat/walksat.py:529-693` ↔ `maxsat_new/walksat.py:73-260`
  (`walksat_polish`): identical modulo annotations, one added SUSPECTED comment,
  and a deleted commented-out `print`. `_extract_clauses` identical.
- `src/sat/state.py` ↔ `maxsat_new/state.py`: every method used by
  `walksat_polish` identical (`__post_init__`, `apply_flip`, `flip_var_effect`,
  `flip_var_hard_delta`, `unsat_hard_ids`, `unsat_soft_indices`,
  `snapshot_best_if_better`, `smooth`, `_count_hard_violations`,
  `_soft_objective`, `_compute_clause_true_count`, `_lit_val`). Dropped members
  (`restart_partial_from_best`, `set_tabu`, `bump_clause`, `vars_adjacent_to`,
  `all_unsat_indices`, `clause_indices_for_var`, `hard_safe`, `var_is_tabu`) are
  **not reachable** from `walksat_polish` — checked call-site by call-site.
  Incidental finding: `src/sat/state.py` defines `unsat_soft_indices` **twice**
  (`:298` and `:332`) with byte-identical bodies, the second shadowing the first;
  the port keeps one, already noted at `maxsat_new/state.py:208-210`.

---

## 5. `maxsat_new/state.py:172` — the only `set` on the live path

```
:172   touched = set(self.pos_occ[v])
:173   touched.update(self.neg_occ[v])
:183   for ci in touched:
```

**It is iterated, not just membership-tested** (`:183`). Verdict: **it cannot
affect flip selection.** Three independent reasons:

1. **The loop body is order-invariant.** `:183-204` only increments two
   independent counters, `broken` and `made`; there is no early `break`, no
   `else`-on-first-hit, and no state carried between iterations
   (`pos_count`/`neg_count` are precomputed `Counter`s, `:178-179`). The return
   is `broken - made` (`:206`) — a sum, so any permutation gives the same integer.
2. **Even the iteration order itself is fixed.** The elements are small
   non-negative `int` clause indices, and CPython hashes `int` to itself; set
   ordering for small ints is a deterministic function of the values and their
   insertion history, and is **not affected by `PYTHONHASHSEED`** (which only
   randomizes `str`/`bytes` hashing). So the order is identical across processes
   and across the subprocess/import boundary.
3. **Both sides run the same code.** `flip_var_hard_delta` is AST-identical
   between `src/sat/state.py` and `maxsat_new/state.py` (§4.5), so even an
   order-sensitive body would be sensitive the same way on both sides.

Consequence: the test does **not** need to set `PYTHONHASHSEED` on the
subprocess. No other set or dict is iterated on the live path (grepped
`operators.py`, `population.py`, `walksat.py`, `state.py`, `hardviol.py`;
`state.py:172` is the sole hit). Worth stating in the test as a comment so a
future reader does not add a `PYTHONHASHSEED=0` cargo line and imply the run
depends on it.

---

## 6. Determinism preconditions, both sides

For a bit-reproducible comparison, **all four** must hold, on each side:

| # | Precondition | OLD | NEW |
|---|---|---|---|
| 1 | The **EA loop** terminates on generations, not the clock — `while (time.time()-start_t) < time_cap and gen < max_gens` (`src:76` / `maxsat_new/memetic.py:225`) must exit on the right conjunct | `ea.max_gens: 100`, top-level `time_limit_s: 1000.0` (~125× the ~8 s estimate) | `budget.max_gens: 100`, `budget.time_limit_s: 1000.0` |
| 2 | **Every polish** terminates on flips, not the clock — `while state.flips < max_flips and not time_up()` (`walksat.py:135`) | `ls.ls_polish_flips: 100`, `ls.time_limit_s: 10.0` (~2500× the ~4 ms a 100-flip polish needs) | `ea.polish_flips: 100`, `polish.time_limit_s: 10.0` |
| 3 | No unseeded randomness | one `random.Random(rng_seed)` (`src:51`) + one per polish (`walksat.py:100`); **no module-level `random.*`** anywhere on the path | same, `maxsat_new/memetic.py:181` |
| 4 | No hash-order or iteration-order dependence | §5 | §5 |

**The old config can be driven exactly this way** — there is no gap. Both caps
are plain scalars the old schema already exposes: `ls.time_limit_s` (per-polish,
`memetic.py:28`) and top-level `time_limit_s` (EA cap, `memetic.py:63`), settable
from YAML or `-D`. The §9.4 dual-meaning trap (`memetic.py:63` silently reusing
`ls.time_limit_s` as the EA cap when the top-level key is absent) is avoided by
stating the top-level key explicitly — which is also why `cfg.yaml` is
disqualified in §2.1.

### 6.1 Why the per-polish cap is 10.0, not STEP_07's 1000.0

STEP_07 used `1000.0` for both caps on `mini.wcnf`. For the per-polish cap on a
real instance I recommend **10.0**, because of a stall mode in `walksat_polish`:

`state.flips` (applied flips) is the budget, but the loop can iterate **without
applying a flip** — when `chosen_v is None` (`walksat.py:646-647`: `if chosen_v is
not None: state.apply_flip(...)`). That happens when every candidate var of the
picked clause is filtered out by `hard_safe` (`br > 0`, `:637-640`) or when no
candidate reduces hard violations (`:684-698` region). During such an iteration
`state.flips` does not advance, so **the flip budget cannot end the loop** — only
the clock can.

Three consequences, all worth stating in the test file:

- **Determinism is not damaged by a stall itself.** Escaping a stall depends only
  on the polish's own RNG (`rng.choice` of the next unsat clause, `rng.shuffle`
  of candidates), not on the clock — so both sides escape on the *same iteration*.
  Determinism breaks only if the **cap truncates the stall**, and then the
  truncation iteration is machine-speed-dependent.
- **A larger cap does not make this safer, only slower.** If a stall does not
  resolve within 10 s (~285k iterations) it is effectively permanent, and 1000.0
  would just burn 100× more wall clock per affected child before failing the same
  way. 10.0 keeps ~2500× headroom over the ~4 ms a clean 100-flip polish needs
  while bounding the damage.
- **It is detectable.** `total_flips` (the sum of `res["flips"]`, i.e. loop
  *iterations* — see the SUSPECTED note at `maxsat_new/walksat.py:128-132`) is
  a pure function of the stream. In a clean run
  `total_flips ≈ children × (polish_flips + ε)`; a stall inflates it, and a
  clock-truncated stall almost certainly inflates it *differently* on the two
  sides. So asserting `total_flips` equality is the practical guard (§7), and
  the §8 task-0 calibration should print `total_flips / (children × polish_flips)`
  and pick a different seed if it is not ≈ 1.

Both sides must of course use the **same** value; 10.0/10.0 and 1000.0/1000.0 are
equally valid as long as they match. The recommendation is 10.0 for the polish
cap, 1000.0 for the EA cap (the EA loop increments `gen` unconditionally and
cannot stall).

---

## 7. What the test asserts

Two tiers, in one file, with the reason for the second tier stated inline.

**Tier 1 — the §10 step-8 contract (the required clause):**

```python
assert int(old["hard_violations"]) == int(new["hard_violations"])
assert TOTAL_SOFT_WEIGHT - int(old["best_soft_weight"]) == new["best_cost"]
assert int(old["best_soft_weight"]) == new["best_soft_weight"]   # pre-conversion, localizes a failure
```

**Tier 2 — fidelity canaries.** PORT_NOTES §11 Q2 recommended "cost only, not
internal counters", on the grounds that a strict match is brittle. STEP_07 then
*measured* the opposite failure: on `mini.wcnf`, a stream with a draw deleted
still matched on cost **and** on the assignment hash. Cost-only is therefore not
sufficient evidence of stream fidelity, and these are cheap and non-brittle
(each is a pure function of the stream, not of timing or ordering):

```python
assert old["meta"]["assign_bits"] == "".join("1" if b else "0" for b in new["best_assignment"][1:])
assert int(old["total_flips"])      == new["total_flips"]      # also the §6.1 stall canary
assert int(old["meta"]["ea_generations"]) == new["generations"] == 100   # max_gens bound, not the clock
assert int(old["meta"]["children"]) == new["children"] == 1100
```

If tier 1 passes and tier 2 fails, that is a *real* finding (a stream divergence
that happened to converge), not test brittleness — the failure message should say
so.

**Test hygiene:**

- `pytest.skip` when `src/cli/run_ea.py` is absent. Step 8 exists to license
  deleting `src/`; the suite must stay green the day that happens.
- `subprocess.run(..., timeout=300, capture_output=True, cwd=REPO_ROOT,
  check=True)` with `sys.executable`; on `CalledProcessError` surface `stderr`.
- Read the JSON from `--out-json <tmp_path>/old.json`, not stdout.
- Assert the parse parity constants up front from `features.extract`
  (`n_vars=100, n_clauses=600, n_hard=100, n_soft=500, total_soft_weight=500`) so
  a parser drift fails with a clear message instead of as a cost mismatch.
- Parameterize over **two seeds** (`7` and `1`, the latter being `run_ea.py`'s
  default) if the calibration keeps the pair under ~30 s; otherwise one seed and
  a comment saying why.

---

## 8. Ordered task list for the implementation PR

0. **Calibrate (no code committed).** Run the old CLI once with
   `oracle_old.yaml` at seed 7, time it, and record `total_flips`,
   `meta.children`, `meta.ea_generations`. Confirm `ea_generations == 100`
   (the `max_gens` bound binding, not the clock) and
   `total_flips ≈ children × polish_flips`. If wall time > ~30 s, lower
   `ea.pop_size` / `ls.ls_polish_flips` in **both** configs and re-run; never
   lower `max_gens`. Write the measured number into §3.3 of this doc.
1. **`maxsat_new/registry.py`** — `SOLVERS: Dict[str, Callable]`, a `@register(name)`
   decorator that raises on duplicate registration, a `get(name)` that raises
   with `sorted(SOLVERS)` in the message (mirroring `sizing.py`'s unknown-rule
   error), and enumerability. Test: `memetic_ea` present after importing
   `solvers`; unknown name raises; duplicate registration raises.
2. **`maxsat_new/solvers.py`** — `@register("memetic_ea")`, taking a parsed
   `WCNF` plus a `config.ResolvedConfig`. Three things only:
   (a) assemble `params = {"ea": resolved_params, "budget": {...}, "polish": polish}`
   — STEP_07 designed the key names so this is a three-line adaptation;
   (b) force `NoopProvider()` regardless of `cfg.provider.kind` (PORT_NOTES §4);
   (c) the **cost conversion**: `best_cost = features.extract(wcnf).total_soft_weight
   − res["best_soft_weight"]`, added as a new key. Do **not** rename
   `hard_violations` → `n_hard_violations`; that is step 9's record schema.
   Test (no subprocess): `best_cost + best_soft_weight == total_soft_weight`,
   `best_cost >= 0`, and that `provider.kind: random` in the config still yields
   the Noop result.
3. **`maxsat_new/tests/data/oracle_old.yaml`** and
   **`maxsat_new/tests/data/oracle_new.yaml`** — verbatim from §2.2 / §3.2, with
   a header comment in each pointing at the other and at §3's table.
4. **`maxsat_new/tests/test_oracle_memetic_ea.py`** — the §7 test: subprocess
   helper, skip-if-no-`src`, parse-parity assertions, tier 1, tier 2.
   Fails-before / passes-after: before `solvers.py` exists it fails at import.
5. **`maxsat_new/STEP_08_NOTES.md`** — measured runtime, the actual
   `best_cost` / `hard_violations` / `assign_bits` the oracle produced (so a
   future regression has a recorded value, not just a relative comparison), and
   any deviation from this plan.

**Deliberately not in this PR:**

- **PR 8b — invert `State.cost`.** STEP_07 deferred the sign to step 8
  (`maxsat_new/memetic.py:101-112`). Doing it needs `total_soft_weight` computed
  once in `run_memetic` and passed into `build_state`, plus an update to
  `test_build_state_fields`'s pin. It is inert under `NoopProvider` (STEP_07 §4)
  so it cannot move the oracle — which is exactly why it should not ride along
  with it. Must land before step 11.
- Amending PORT_NOTES §1/§3 (the "dead LLM block" error STEP_07 corrected) and
  §11 Q2 (cost-only vs canaries, §7 above). Both are doc-only and belong in one
  PORT_NOTES housekeeping PR, not in a load-bearing test PR.
- Anything from steps 9–11: `record.py`, `run.py`, `llm_guided_base`,
  `RandomPerturbationProvider`.
