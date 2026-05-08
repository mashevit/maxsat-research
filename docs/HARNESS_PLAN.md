# MaxSAT Research Harness — Plan

Status: **plan only** — no code touched. Awaiting approval before any
implementation work in `src/`.

This document covers (1) what is currently runnable from `src/`, (2) a
proposed unified harness, (3) the first paper-grade ablation matrix and
its budget, (4) what to wrap vs deprecate, and (5) the questions you need
to answer before code is written.

---

## 1. Inventory of currently runnable solver modes

The repo today exposes ten CLI entry points; some are real solvers, some
are wrappers, and some are half-wired. They share two underlying solver
libraries — `src/sat/walksat.py` (3 implementations of WalkSAT in one
file) and `src/evo/memetic.py` (memetic EA on top of the WalkSAT polish).

### 1.1 Pure local search

| Mode | Entry point | Config(s) | Key flags | Status |
|---|---|---|---|---|
| **WalkSAT (class, simple)** | `python -m src.cli.solve --cnf <path> --config <yaml> [--ea]` | `configs/default.yaml` (uses `ls.*` block) | `--cnf`, `--config`, `--ea` | **Half-wired.** Uses `src.sat.walksat.WalkSAT` (the simple class), *not* `run_satlike`. The `--ea` switch is a Python comment (`#-/+` patch markers) — has no effect. |
| **WalkSAT / SATLike (`run_satlike`)** | `python -m src.cli.solve_batch --folder <dir> --config <yaml> --seed N --out <csv>` | `configs/default.yaml`, `configs/2.yaml`, `configs/3.yaml`, `configs/4.yaml` | `--folder`, `--config`, `--seed`, `--out`, `--time_limit_s` (parsed but unused — body is commented out) | Working. Calls `src.bench.harness.solve_folder` → `walksat.run_satlike`. CSV schema: `instance,seed,elapsed_sec,best_soft_weight,hard_violations,total_flips,flips_per_sec,restarts,final_noise,config_hash,wall_sec`. |
| **WalkSAT polish only** | `python -m src.cli.polish --path <wcnf> --seed N --time-limit-s F --max-flips N` | n/a (CLI flags only) | `--path`, `--seed`, `--max-flips`, `--time-limit-s`, `--noise`, `--no-hard-safe`, `--print-assign` | Working. Used as the per-child polish step in the EA. The fallback path (`_USE_POLISH=False`) calls `run_satlike(..., start_assign=...)`, but `run_satlike`'s signature doesn't accept `start_assign` — that branch would crash if `walksat_polish` were missing. |

### 1.2 Memetic EA

| Mode | Entry point | Config(s) | Key flags | Status |
|---|---|---|---|---|
| **Memetic EA (single)** | `python -m src.cli.run_ea <wcnf> -c <cfg> --seed N [-D k=v]` | `configs/cfg.yaml`, `cfg2.yaml`, `cfg3.yaml`, `cfg250.yaml`, `cfghard1.yaml`, `hard2.yaml`, `hard3.yaml`, `ea_cfg.yaml` | positional `wcnf`, `-c/--cfg`, `--seed`, `-D/--override`, `--out-json`, `--quiet`, `--use-internal-parser` | Working. Sets `cfg.ea.enabled=True` by default. Output JSON has `best_soft_weight, hard_violations, elapsed_sec, total_flips, meta.{ea_generations, children, assign_bits, dimacs, true_vars}, satisfied_clauses.*`. |
| **Memetic EA (batch — fixed time)** | `python -m src.cli.run_experiment --bench_dir <dir> -c <cfg> --seeds 1 2 3 --time_limit S --out_csv <csv> --config_id <id>` | same as above | `--bench_dir`, `--cfg/-c`, `--seeds`, `--time_limit`, `--out_csv`, `--config_id`, `--recursive`, `-D` | Working. `--time_limit` is forwarded as top-level `time_limit_s` in the merged config. CSV schema: `instance,seed,n_vars,n_clauses,hard_violations,soft_unsat,best_weight,runtime_s,flips,ls_calls,status,config_id`. |
| **Memetic EA (batch — global budget)** | `python -m src.cli.run_experiment1 --bench_dir <dir> -c <cfg> --seeds … --total_time_s 300 \| --per_run_time_s 30 --out_csv <csv> --config_id <id>` | same as above | `--bench_dir`, `--seeds`, `--total_time_s`, `--per_run_time_s`, `--out_csv`, `--config_id`, `-D`, `--recursive` | Working. Distributes a global wall-clock budget proportionally to `(n_vars + n_clauses)`. `TIME_LIMIT_KEY` is hard-coded to `time_limit_s` at file head. |

The EA's polish is wired through `evo.operators.short_polish` →
`sat.walksat.walksat_polish`, so "memetic" here means
`JW-seeded GA + WalkSAT polish per child`.

### 1.3 LLM-guided variants

| Mode | Entry point | Config | Status |
|---|---|---|---|
| **LLM-guided memetic (Noop)** | None — `LLMAdvisor(NoopProvider())` is hardcoded inside `run_memetic` | `configs/default.yaml` has `llm.provider: ollama, llm.model: …` but is ignored | **Half-wired.** The provider is force-set to `NoopProvider`, and the actual `advisor.propose(...) → apply_advice(...)` block in `memetic.py` is wrapped in a `''''''''` triple-quoted string and is therefore dead code. With the comment block removed and the provider switched, this is the closest thing to a working "llm_guided_base" — but it has never run end-to-end. |
| **LLM-guided memetic (Ollama)** | None | n/a | Provider class exists at `src.llm.providers.ollama.OllamaProvider`. Never instantiated by any CLI today. |
| **LLM-guided memetic (LoRA)** | None | n/a | Not present. `gsm8k_lora_v2_consolidated/` is a self-contained GSM8K LoRA training kit (`train.py`, `evaluate.py`, `train.sbatch`, `eval.sbatch`). It does **not** know about MaxSAT. Treat it as an artifact source: the `runs/<adapter>/` it produces would later be served via Ollama (or a dedicated `LoRAProvider`) and wired in as another `llm.provider` option. |
| **Plain GA (no LS)** | None | n/a | Not exposed. Would require flag in `run_memetic` to skip `short_polish`. Today every child is polished unconditionally. |

### 1.4 Exact / oracle baseline

| Mode | Entry point | Status |
|---|---|---|
| **PySAT RC2 (single)** | `python -m src.cli.run_opt_rc2 <instance> [--solver g3] [--json] [--print-model] [--model-out PATH]` | Working. Computes the optimum for cost-comparison. |
| **PySAT RC2 (batch)** | `python -m src.cli.batch_opt_rc2 <root> -o <csv> [--solver g3] [--ext .cnf .wcnf]` | Working. Plain CNFs are converted to "all-soft, weight 1" before solving. |
| **RC2 ⨯ memetic comparison pipeline** | `python -m src.cli.run_pipeline_opt_vs_memetic --bench_dir <dir> --config <yaml> --seeds … --rc2_csv <csv> --memetic_csv <csv> --out_csv <csv>` | Working. Joins the two CSVs and computes `opt_gap`, `rel_gap`, `is_optimal`. |

### 1.5 Auxiliary

| Mode | Entry point | Status |
|---|---|---|
| **Instance metadata** | `python -m src.cli.make_metadata --input <path> [--recursive] [--jsonl <out>] [--no-sha]` | Working (uncommitted). Produces per-instance `*.meta.json` and a `metadata.jsonl` index with structural features and family tags (`random_partial_maxsat`, `max_clique_hamming`, `ramsey`, `uniform_random_unsat`, …). Needed for stratified suite construction. |

### 1.6 Known issues / inconsistencies (to be cleaned up by the harness, not now)

1. **Two parallel WalkSAT implementations.** `src/sat/walksat.py` contains
   the `WalkSAT` class (used only by `solve.py`), `run_satlike` (used by
   `bench/harness.py`), and `walksat_polish` (used by the EA and by
   `polish.py`). They share data structures but not behavior; only
   `run_satlike` and `walksat_polish` use the full `SatState` machinery
   (dynamic weights, tabu, hard-first repair). `solve.py` is therefore
   not representative of "our" WalkSAT.
2. **Dead LLM path.** In `src/evo/memetic.py`, the block that calls
   `advisor.propose(...)` and `apply_advice(...)` is enclosed in
   `''''''''` (string literal used as a multi-line comment). Re-enabling
   it requires removing the markers AND swapping `NoopProvider` for
   `OllamaProvider`/LoRA.
3. **`solve.py --ea` is a no-op** — it's a leftover patch comment.
4. **`solve_batch.py --time_limit_s` is parsed but unused** (the body
   that copied it into `cfg` was commented out).
5. **Two near-duplicate batch experiment CLIs** (`run_experiment.py` vs
   `run_experiment1.py`). `run_experiment1.py` adds the global-budget
   feature; otherwise they overlap completely.
6. **CNF parsing semantics for `solve_with_rc2`.** It calls
   `cnf_to_all_soft_wcnf` for both CNF *and* WCNF inputs, ignoring an
   actual hard/soft split that may already exist in WCNF. The
   "load_as_wcnf" function defined right above it is the one that
   handles both formats correctly but is unused.
7. **Config zoo.** `configs/` has 12 yaml files (`cfg.yaml`, `cfg2.yaml`,
   `cfg3.yaml`, `cfg250.yaml`, `2.yaml`, `3.yaml`, `4.yaml`,
   `cfghard1.yaml`, `hard2.yaml`, `hard3.yaml`, `default.yaml`,
   `ea_cfg.yaml`). Most differ only in `pop_size` and `time_limit_s`.
   These will be collapsed into a small set of solver-config presets
   under `configs/solvers/*.yaml`.
8. **Hard-coded LLM provider.** `run_memetic` instantiates
   `NoopProvider()` directly; there's no way to switch from the config.

---

## 2. Proposed unified harness

### 2.1 Single CLI

```
python -m maxsat_research.run \
    --solver <name> \
    --instance <path> \
    --budget-seconds <n> \
    --seed <n> \
    --out <jsonl>
```

A single binary; no per-script proliferation. Auxiliary modes:

```
python -m maxsat_research.suite \
    --suite <name> \
    --solver <name> \
    --seeds 1 2 3 4 5 \
    --budget-seconds 60 \
    --out <jsonl>
```

`maxsat_research.suite` iterates over the instances declared by a suite
YAML and calls `maxsat_research.run` per (instance, seed). It also emits
one summary record at the end and is the unit of SLURM scheduling.

For the exact baseline (oracle): `--solver rc2` is just another solver
in the registry, which keeps post-hoc gap analysis a one-liner instead
of the current bespoke pipeline script.

### 2.2 Solver registry (decorator-based)

```python
# src/maxsat_research/registry.py
SOLVERS: dict[str, type[Solver]] = {}

def register(name: str):
    def deco(cls):
        SOLVERS[name] = cls
        return cls
    return deco

# src/maxsat_research/solvers/walksat.py
@register("walksat")
class WalkSatSolver(Solver):
    def solve(self, instance: WCNF, budget_s: float, seed: int,
              recorder: AnytimeRecorder) -> SolverResult: ...
```

Adding a solver = drop one file in `src/maxsat_research/solvers/`,
decorate it, optionally add a `configs/solvers/<name>.yaml` for the
defaults. The CLI auto-imports the solver package so registration is
side-effecting at import time. Planned initial registry:

| name | wraps |
|---|---|
| `walksat` | `sat.walksat.run_satlike` |
| `ga_no_ls` | `evo.memetic.run_memetic` with polish disabled |
| `memetic_ea` | `evo.memetic.run_memetic` (current behavior) |
| `llm_guided_base` | `memetic_ea` + `OllamaProvider` (un-LoRA'd model) |
| `llm_guided_lora` | `memetic_ea` + `OllamaProvider` pointing at a LoRA-merged model tag |
| `rc2` | `pysat.examples.rc2.RC2` (oracle) |

The `Solver` base class enforces a uniform return contract so that the
recorder is the only place anytime curves are produced.

### 2.3 Standard JSONL record (one line per run)

```json
{
  "instance": "data/dev_small/file_rpms_wcnf_L3_V100_C600_H100_0.wcnf",
  "instance_sha256": "…",
  "instance_family": "random_partial_maxsat",
  "n_vars": 100, "n_clauses": 600, "n_hard": 100, "n_soft": 500,
  "solver": "memetic_ea",
  "solver_version": "0.1.0",
  "config": { "...": "merged effective config" },
  "config_hash": "9f3c…",
  "seed": 1,
  "budget_s": 60.0,
  "wall_time_s": 60.04,
  "iterations": 18432,
  "best_cost": 412,           // see open question §5 on cost semantics
  "best_assignment_hash": "blake2b-12:…",
  "best_assignment_path": null, // or "results/.../<run_id>.assign"
  "anytime_curve": [[0.001, 87123], [0.05, 9012], ...],
  "status": "ok",             // ok | infeasible | error
  "git_sha": "6a7656f",
  "hardware": {
    "host": "compute-0-1",
    "cpu_model": "Xeon Gold 6248", "cpu_threads_used": 1,
    "gpu_model": "NVIDIA RTX 6000 Ada", "gpu_uuid": "GPU-…",
    "apptainer_image": "maxsat-research_2026-05-08.sif"
  },
  "notes": ""
}
```

Every solver writes through the same `JsonlRecorder`, so analysis code
can ignore the solver column when shaping data frames. `anytime_curve`
is `[(t_seconds, cost)]`, monotonically non-increasing in cost (we keep
only "improvement" events plus the final tick at `budget_s`).

### 2.4 Benchmark suites — `configs/suites/*.yaml`

A suite is a manifest that names the instances, with optional
sampling/seeding so the same suite reproduces across machines.

```yaml
# configs/suites/dev_small.yaml
name: dev_small
description: Mixed dev set already in data/dev_small/
instances:
  - data/dev_small/*.wcnf
  - data/dev_small/*.cnf
```

```yaml
# configs/suites/uf50_sat.yaml
name: uf50_sat
description: 6 satisfiable random 3-SAT instances at v=50
instances:
  - data/dev_small/uf50-*.cnf      # 6 files already on disk
```

```yaml
# configs/suites/uuf100_phase.yaml
name: uuf100_phase
description: 50 UNSAT random 3-SAT instances at the phase transition (v=100, c=430)
sampling:
  seed: 20260508
  source: data/unsat/uuf100-430/UUF100.430.1000/*.cnf
  n: 50
```

```yaml
# configs/suites/wcnf_rpms_v100.yaml
name: wcnf_rpms_v100
description: Random partial-MaxSAT, V=100, mixed C and H. Expand from generator if <50.
instances:
  - data/dev_small/file_rpms_wcnf_L3_V100_C*_H100_*.wcnf   # 11 files
generator_fallback:
  module: src.bench.gen_rpms
  params: { n_vars: 100, n_hard: 100, c_soft: [600, 700, 800], seed: 20260508 }
  target_n: 50
```

```yaml
# configs/suites/structured.yaml
name: structured
description: Structured combinatorial MaxSAT (clique + Ramsey), drawn from data/dev_small/
instances:
  - data/dev_small/hamming*.clq.wcnf
  - data/dev_small/johnson*.clq.wcnf
  - data/dev_small/ram_*.ra1.wcnf
```

A `Suite.resolve()` step expands globs, applies sampling with the
declared seed, and, where enabled, runs a generator to top up to
`target_n`. The resolved manifest (instance paths + sha256) is written
into the run-output directory so that "the suite I just ran" is
reproducible to the byte.

---

## 3. First paper-grade ablation matrix

### 3.1 Design

```
solvers = { walksat, ga_no_ls, memetic_ea, llm_guided_base, llm_guided_lora }   # 5
suites  = { dev_small, uuf100_phase, wcnf_rpms_v100 }                            # 3
seeds   = 5
budget  = 60 s wall-clock per (instance, seed)
hardware = RTX 6000 Ada (Apptainer + Ollama for LLM solvers)
```

Suite sizes (to be confirmed against `configs/suites/*.yaml`):

| Suite | Instances | Notes |
|---|---:|---|
| `dev_small` | 37 | All files already on disk in `data/dev_small/`. |
| `uuf100_phase` | 50 | Sampled from `data/unsat/uuf100-430/UUF100.430.1000/` (1000 available). |
| `wcnf_rpms_v100` | 50 | 11 already on disk + 39 to generate (or use fewer if no generator). |
| **Total** | **137** | |

Per (solver, suite) cell: `instances × seeds × budget = 137 × 5 × 60s` is
distributed across the three suites, but **each cell's wall-clock cost
is constant**: `cell_seconds = sum(instances_per_suite) × seeds × 60`.

### 3.2 Wall-clock estimate

```
cell_wall_s = (37 + 50 + 50) × 5 × 60 = 41 100 s ≈ 11.42 h per (solver, suite-set) sweep
```

The matrix is `solvers × suites`, but if we group by solver and sweep
all three suites in one job per solver, the *minimum sequential* cost
per solver is **11.42 h**. With 5 solvers serial:
**5 × 11.42 h ≈ 57.1 wall-clock-hours**.

### 3.3 GPU-hours

Only `llm_guided_base` and `llm_guided_lora` need a GPU (one Ollama
server per GPU). The CPU-only solvers (`walksat`, `ga_no_ls`,
`memetic_ea`) consume 0 GPU-h.

```
gpu_hours = 2 LLM solvers × 11.42 h = 22.84 GPU-hours
```

Add ~10 % for warm-up/eviction overhead and Ollama load times → budget
**~25 GPU-hours** on a single RTX 6000 Ada. If two GPUs are
available, run the two LLM solvers in parallel and finish in ~12.5 h
GPU wall-clock.

CPU-only solvers cost `3 × 11.42 h = 34.26 CPU-core-hours` (single-core
at OMP=1, which our README enforces). Trivially parallelizable across
nodes.

### 3.4 SLURM job count

Two viable shardings:

* **Coarse — one job per (solver, suite).** 5 × 3 = **15 jobs**. Each
  job iterates instances × seeds internally and emits one JSONL file.
  Simple to launch, but a single job's worst case is
  `50 × 5 × 60 s ≈ 4.2 h`, so scheduling priority matters.

* **Fine — one job per (solver, suite, seed).** 5 × 3 × 5 = **75
  jobs**, each ≤ 50 min. Better cluster throughput, but five times the
  bookkeeping. Recommended for the LLM solvers; coarse is fine for the
  CPU ones.

Recommendation: **15 jobs for CPU solvers (coarse) + 30 jobs for LLM
solvers sharded by seed (fine) = 45 jobs total**. The harness will emit
both `run_*.jsonl` and a `manifest.json` per job so re-running a single
seed is cheap.

### 3.5 What we do *not* spend time on in this experiment

* No A/B between memetic-EA configs. Hyper-parameter sweeps come later;
  for the first paper-grade pass each solver runs at its registered
  default config.
* No `rc2` in the timing matrix — it's run separately as the oracle for
  computing optimality gaps and reporting.

---

## 4. Migration plan for `experiments/`, `runs/`, and `src/cli/`

### 4.1 Wrap (i.e. become thin compatibility shells over the new harness)

| Old script | Replaced by | Compat plan |
|---|---|---|
| `src/cli/solve_batch.py` | `maxsat_research.suite --solver walksat` | Keep the CLI for one release, internally call the new suite runner, emit a deprecation warning. |
| `src/cli/run_ea.py` | `maxsat_research.run --solver memetic_ea` | Keep, deprecation warning, drops `--out-json` semantics in favor of JSONL append. |
| `src/cli/run_experiment.py` | `maxsat_research.suite --solver memetic_ea` | Keep with warning. |
| `src/cli/run_experiment1.py` | `maxsat_research.suite … --total-budget-seconds N` | Keep with warning. The size-proportional per-instance allocation moves into `Suite.allocate_budget()`. |
| `src/cli/run_opt_rc2.py` | `maxsat_research.run --solver rc2` | Keep with warning. |
| `src/cli/batch_opt_rc2.py` | `maxsat_research.suite --solver rc2` | Keep with warning. |
| `src/cli/run_pipeline_opt_vs_memetic.py` | `maxsat_research.analysis.gap` reading two JSONLs | Keep until analysis script is in place. |
| `src/cli/polish.py` | `maxsat_research.run --solver walksat_polish --warm-start <bits>` (new mode) | Keep — useful as a debugging tool. |
| `src/cli/make_metadata.py` | `maxsat_research.metadata` (move package) | Move; CLI surface unchanged. |
| `src/cli/solve.py` | (drop) | The simple `WalkSAT` class is dead code paralleling `run_satlike`. Plan: remove after the new harness is live. |

### 4.2 Deprecate immediately (move to `garbage/` or delete)

* `src/cli/solve.py` (broken `--ea`, simple WalkSAT class).
* `src/sat/walksat.bak.py`, `src/sat/state.py.bak`,
  `src/cli/solve_batch.py.bak`, `src/bench/harness.py.bak`.
* `src/evo/memetic0.py`.
* `src/evo_v_1/1.py`.
* `from_gemini.py` (root-level draft).
* All of `garbage/`.

### 4.3 Configs

* Collapse `configs/2.yaml`, `3.yaml`, `4.yaml`, `cfg*.yaml`,
  `hard*.yaml`, `default.yaml`, `ea_cfg.yaml` into a small set of
  presets under `configs/solvers/{walksat,ga_no_ls,memetic_ea,
  llm_guided_base,llm_guided_lora}.yaml`. Old configs stay in `garbage/`
  for one release with a `MIGRATION.md` cross-reference.
* New top-level: `configs/suites/*.yaml` (see §2.4).

### 4.4 Results / runs / experiments

* `experiments/*.csv`, `results/*.csv`, `runs/*.json` — all from the
  legacy CLIs; **leave in place, do not migrate**. Treat them as
  archival output. The new harness writes only to `results/<date>/<run_id>/`.

### 4.5 `gsm8k_lora_v2_consolidated/`

**Untouched.** It's a self-contained training kit. Integration path:

1. Train (or download) a LoRA via `gsm8k_lora_v2_consolidated/train.py`.
2. Merge or keep adapter; serve through Ollama as a custom model tag
   (e.g. `Modelfile` referencing the merged weights).
3. Point `configs/solvers/llm_guided_lora.yaml` at that tag:
   `llm.provider: ollama`, `llm.model: maxsat-mistral-lora-v1`.
4. The harness's `OllamaProvider` is the same one we already have at
   `src/llm/providers/ollama.py`.

No changes inside `gsm8k_lora_v2_consolidated/` are required for the
ablation.

---

## 5. Open questions to resolve before code is written

These are the design decisions that, if I picked them silently, you'd
likely want to revisit later. I've picked a default (recommended) for
each.

1. **Cost field semantics across CNF/WCNF/partial-MaxSAT.** Today
   `solve_with_rc2` uses `opt_cost = sum(weights of UNSAT soft)` while
   the EA reports `best_soft_weight = sum(weights of SAT soft)`. The
   harness needs **one** `best_cost` field. **Recommendation:** store
   *unsatisfied soft weight* (lower is better) as `best_cost`, plus
   `n_hard_violations` separately. For pure-SAT instances loaded as
   "all soft, weight 1", `best_cost == n_unsat_clauses`, which is the
   natural objective.

2. **WCNF top-weight handling.** In `parse_dimacs`, when the WCNF header
   has no `top` we currently treat the file as "all soft" with sentinel
   `top = 1e18` (silently). The harness should make this explicit.
   **Recommendation:** record `top_present: bool` and the effective
   top in every JSONL record, and refuse to load instances where the
   top is so small that supposedly-hard clause weights overflow it.

3. **Anytime-curve sampling.** Two reasonable choices:
   (a) **event-driven** — record `(t, cost)` only when `cost`
       improves, plus a final `(budget_s, cost)` tick.
   (b) **fixed-rate** — record every `Δt` regardless (e.g. every 100 ms).
   **Recommendation:** event-driven (a). It compresses well, never
   loses an improvement, and the analysis can interpolate to any grid.
   Per-run record growth is bounded by `O(log n)` improvements in
   practice.

4. **Full assignments vs hashes.** Logging the full assignment per run
   for `dev_small + uuf100_phase + wcnf_rpms_v100` × 5 solvers × 5 seeds
   ≈ 3.4 K records, each up to ~1 KB. Manageable.
   **Recommendation:** log a **`best_assignment_hash` always**, plus
   the **full assignment as a sidecar file** when `--save-assignments`
   is passed (off by default). Hash is enough for "did two solvers
   reach the same optimum?", and the sidecar is for verification or
   plotting.

5. **Budget enforcement.** Some solvers (RC2) ignore wall-clock and run
   to optimality; some (EA) honor it cooperatively; some (LLM) might
   hang on a stuck Ollama call. **Recommendation:** the harness wraps
   each `solver.solve()` in a SIGALRM watchdog at `budget_s + 5 s` and
   marks `status="timeout"`. Solvers should still cooperate via a
   `should_stop()` callable injected from the recorder.

6. **Non-determinism of LLM solvers.** Ollama's HTTP API is
   non-deterministic even with a fixed seed (different KV cache,
   different batching). **Recommendation:** record both the seed *we*
   pass and the model fingerprint (`ollama show` digest) in the
   JSONL `config_hash`, and accept that LLM-guided runs are
   approximately reproducible, not bit-exact.

7. **Plain GA disabling polish.** Today the EA always polishes children.
   To get `ga_no_ls`, the cleanest options are:
   (a) a config flag `ea.polish: false` in `run_memetic`.
   (b) a separate `solvers/ga_no_ls.py` that copies `run_memetic`
       without the polish step.
   **Recommendation:** (a). Less duplication, and one place to add a
   `polish_strategy` enum later.

8. **CPU pinning / OMP.** The README already pins `OMP_NUM_THREADS=1
   etc.` for the WalkSAT run. The harness should set those env vars at
   import time so users can't accidentally run multi-threaded math on
   solvers that assume single-thread. **Recommendation:** yes, do this
   in `maxsat_research/__init__.py`.

9. **Where do `gsm8k_lora_v2_consolidated/` outputs land?** If/when
   adapters get merged and served through Ollama, the LoRA's git
   provenance (the GSM8K training run) needs to live in the JSONL
   record. **Recommendation:** add `lora_run_id` and `lora_sha` fields
   under `config.llm` for the `llm_guided_lora` solver only.

10. **Suite resolution timing.** Does the suite YAML resolve globs at
    job-launch time (so a later `git pull` could change which files are
    in the suite) or once and then freeze? **Recommendation:** resolve
    at launch, then write the resolved manifest into the run output;
    re-runs of the same suite refer to the manifest, not the YAML.

---

## 6. Implementation order (after approval)

For each item below: one PR, one new test in `tests/`, no other code
touched in the same PR.

1. `src/maxsat_research/__init__.py` + a stub `Solver` base class and
   `SolverResult` dataclass. Test: importable, base class enforces the
   contract.
2. `src/maxsat_research/registry.py` + decorator. Test: registering and
   retrieving a fake solver.
3. `src/maxsat_research/io/jsonl.py` (`JsonlRecorder` + schema doc).
   Test: round-trip a fake record.
4. `src/maxsat_research/cli.py` (`python -m maxsat_research.run`). Test:
   end-to-end on `data/toy/mini.wcnf` with a registered fake solver.
5. `src/maxsat_research/solvers/walksat.py` wrapping `run_satlike`. Test:
   on `data/toy/mini.wcnf`, agrees with the legacy CLI's `best_cost`.
6. `src/maxsat_research/solvers/rc2.py` wrapping `solve_with_rc2`. Test:
   `best_cost == 0` for `uf50-01.cnf` (SAT instance), `> 0` for one of
   the `uuf50` instances.
7. `src/maxsat_research/solvers/memetic_ea.py` wrapping `run_memetic`.
   Test: 1-second budget on `mini.wcnf` returns a valid record.
8. `src/maxsat_research/solvers/ga_no_ls.py` (or polish toggle). Test:
   produces records with `meta.polishes_per_child == 0`.
9. Suite YAML loader + `Suite.resolve()`. Test: `dev_small.yaml`
   resolves to the 37 expected files.
10. `python -m maxsat_research.suite`. Test: 1-second budget, 1 seed,
    `data/toy/` suite, three records in the JSONL.
11. `OllamaProvider` plumbing into `memetic_ea` (un-comment the dead
    code, add config flag). Test: with `NoopProvider`, behavior is
    identical to step 7.
12. `llm_guided_base` and `llm_guided_lora` registry entries. Test:
    skipped on CI; smoke-run locally.
13. SLURM `*.sbatch` templates in `scripts/`.

After step 10 the harness is usable for the CPU-only part of §3, and
half of the ablation can run while LLM plumbing lands.
