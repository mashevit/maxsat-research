# Tier-2 Memetic Runs — Plan, Scripts, and Result Combination

How to run the memetic EA on the tier-2 instances and how to combine those
results with the RC2 tier tables in `results/hardness/`.

Companion to [`docs/RC2_STATUS.md`](RC2_STATUS.md) (the audit of what RC2 did),
[`docs/RC2_FINDINGS.md`](RC2_FINDINGS.md) (its executive summary), and
[`docs/HARNESS_PLAN.md`](HARNESS_PLAN.md) (the eventual unified harness, still
plan-only). This document describes what is **implemented and tested now**, on
top of the existing `src/evo/memetic.py` — it does not wait for the harness in
HARNESS_PLAN §6.

Written 2026-08-04. Every number below marked "measured" was produced by
actually running the code on this workstation; the commands are shown.

---

## 0. TL;DR

* **Tier 2 is 28 instances, 26 of them runnable.** Tier 2 = the RC2 records with
  `completed=true` at 60–600 s, plus the one solved-but-labelled-T3 record from
  `RC2_STATUS` §4.6. Two are MSE new-format WCNF and **cannot be parsed by the
  memetic stack** — see §3. The 26 runnable ones are all SATLIB random 3-SAT.
* **New scripts** are in place: a manifest generator, a per-job runner, two
  sbatch drivers, and a combine script. All memetic dependencies are copied into
  `cluster_staging_maxsat/`. Inventory in §2.
* **Default grid: 780 jobs** = 26 instances × 3 configs × 2 budgets (60 s, 300 s)
  × 5 seeds ≈ 39 solver-hours, ~1.5 h wall as a `%30`-throttled array.
* **Combine on `instance_sha256`**, compare `best_cost` against
  `profile.final_cost` — both are *unsatisfied soft weight*, so they are already
  in the same units. Details and pitfalls in §6.
* **Do not headline `rel_gap`.** On this instance set the optimum is 1 or 2
  (`RC2_STATUS` §3.4), so a miss of one clause reads as a 100 % relative gap.
  Use **hit rate** (fraction of seeds reaching the optimum) and **cost spread**.
* **Calibration warning:** in a measured 8 s run the EA completed only **3
  generations**. At these budgets the result is dominated by the WalkSAT polish,
  not by evolution. Read §7 before drawing conclusions about "the EA".

---

## 1. What "tier 2" is, and why it is the right target

`RC2_STATUS` §0 makes the point that has to be repeated here: **the tiers are an
output of profiling, not an input.** No job was ever submitted "for tier 2".
`assign_tier()` labels each *record* from `profile.completed` and
`profile.solve_s`:

```
not completed                      -> T3
completed and solve_s <=  60       -> T1
completed and  60 < solve_s <= 300 -> T2a
completed and 300 < solve_s <= 600 -> T2b
completed and solve_s  >  600      -> T3   ("cap misconfigured?")
```

So "run tier 2" means: take the instances that landed in T2a/T2b and run the
memetic EA on those. They are the right target because they are the only ones
that are simultaneously

1. **non-trivial** — T1 instances are solved by RC2 in under a minute, several
   in under 10 ms, so there is nothing to compare; and
2. **oracle-labelled** — T3 instances have no optimum at all, only a lower
   bound, so no gap can be computed against them.

### 1.1 The selection, measured

```bash
python -m src.bench.make_tier2_manifest
```

```
tier-2 candidates : 28
  usable          : 26
  skipped         : 2
jobs              : 780 (26 inst x 3 cfg x 2 budget x 5 seed)
solver-seconds    : 140400
```

Where the 28 come from:

| RC2 run | T2a | T2b | solved-but-T3 | contributed |
|---|---:|---:|---:|---:|
| `uuf250_1000c` (cap 900) | 15 | 3 | 0 | 18 |
| `uuf_diff_unsat` (cap 600) | 6 | 2 | 0 | 8 |
| `mse23_full` (cap 600) | 1 | 0 | 0 | 1 |
| `mse_cap1800` (cap 1800) | 1 | 0 | 1 | 2 |
| raw total | 23 | 5 | 1 | 29 |
| after dedup (see below) | | | | **28** |

**Dedup.** The 75 MSE instances were profiled twice, at cap 600 and cap 1800
(`RC2_STATUS` §4.2), so `judgment-aggregation-…-00000385.wcnf` qualifies from
both runs. The generator keeps the **fastest** RC2 solve as the reference and
records every contributing run in the `rc2_runs_all` column. If the two runs
disagreed on the optimum the instance would be dropped and reported in
`tier2_skipped.txt` — they do not (OPT 37 both times).

**The solved-but-T3 record is included by default.** That is
`judgment-aggregation-…-00000293.wcnf`, solved to optimality in 1313 s at cap
1800 and labelled T3 only because `assign_tier()`'s cutoffs ignore `--cap`
(`RC2_STATUS` §4.6). It has a valid, best-known-validated optimum (43,
`ratio == 1.0`), so excluding it would throw away the one MSE oracle label
beyond 600 s. Pass `--no-solved-t3` to drop it.

**Tier labels are not comparable across runs.** `RC2_STATUS` §4.4(c): T2b under
the 900 s cap of `uuf250_1000c` is not the same population as T2b under a 600 s
cap. Every row of `tier2_oracle.csv` therefore carries `rc2_cap_s` and
`rc2_run`; stratify by those, not by the tier string alone.

### 1.2 The 26 runnable instances

All SATLIB uniform-random UNSAT 3-SAT, loaded as "all soft, weight 1, zero
hard", so `best_cost` is literally the number of unsatisfied clauses.

| corpus | n | vars/clauses | OPT | RC2 solve_s range |
|---|---:|---|---:|---|
| `data/unsat250_1000c/` | 18 | 250 / 1065 | 1 | 63.1 – 495.8 |
| `data/unsat_uuf_diff/` | 8 | 200–250 / 860–1065 | 1 (6), 2 (2) | 67.7 – 383.9 |

The instances live in `cluster_staging_maxsat/data/`, which is **gitignored**
(`.gitignore`: `cluster_staging_maxsat/data/`). This is the gap `RC2_STATUS` §4.5
flagged — the SATLIB corpora were cluster-side staging copies that were never
committed, so the exact bytes RC2 profiled were unrecoverable. They are present
in the staging tree now, and `tier2_oracle.csv` records the **sha256 of each
file as staged**, which closes the gap going forward: any future re-stage that
changes the bytes will be caught by the combine step rather than joined
silently.

The staged copies have had the SATLIB `%`/`0` trailer stripped
(`cluster_staging_maxsat/readme.txt`: `sed -i '/^%$/,$d' *.cnf`), which is why
they parse as 1065 clauses and not 1067. `src/sat/cnf.py` skips `%`- and
`0`-prefixed lines anyway, so the memetic path is insensitive to this; PySAT's
`CNF(from_file=...)` is not, which is exactly the discrepancy `RC2_STATUS` §3.5
identified.

---

## 2. What was added, and where

Reusable Python goes in `src/` and is **copied byte-identically** into
`cluster_staging_maxsat/` — the same convention `RC2_STATUS` §1.1 verifies for
`profile_hardness.py`. Cluster-only artefacts (sbatch, manifests) live only in
the staging tree.

### 2.1 New files

| path | role | runs where |
|---|---|---|
| `src/bench/make_tier2_manifest.py` | reads `results/hardness/`, selects tier 2, resolves + checksums instances, emits the manifest, the oracle table and the skip list | workstation |
| `src/cli/run_memetic_shard.py` | one (instance, config, seed, budget) → one JSONL record | cluster (one per array task) |
| `src/bench/combine_tier2.py` | joins memetic shards against the RC2 oracle, emits the comparison tables | workstation |
| `configs/tier2/memetic_base.yaml` | pop 60, cheap polish — the baseline arm | — |
| `configs/tier2/memetic_pop150.yaml` | pop 150, cheap polish — exploration arm | — |
| `configs/tier2/memetic_deeppolish.yaml` | pop 40, 12500-flip polish — exploitation arm | — |
| `cluster_staging_maxsat/scripts/tier2_memetic_array.sbatch` | the array driver | cluster |
| `cluster_staging_maxsat/scripts/smoke_tier2_memetic.sbatch` | 5-task, 10 s smoke test on the same code path | cluster |
| `cluster_staging_maxsat/scripts/manifest_tier2_memetic.tsv` | 780 generated job lines | — |
| `cluster_staging_maxsat/scripts/tier2_oracle.csv` | 26-row RC2 reference table | — |
| `cluster_staging_maxsat/scripts/tier2_skipped.txt` | the 2 exclusions, with reasons | — |

### 2.2 Files copied into the staging tree

`cluster_staging_maxsat/src/cli/` already held the RC2 chain. The memetic
dependency closure was added; all eleven are byte-identical to `src/`:

```
src/evo/{memetic,operators,population}.py
src/sat/{cnf,state,walksat}.py
src/llm/{advisor,prompt}.py
src/llm/providers/{noop,ollama}.py
src/cli/run_memetic_shard.py
configs/tier2/*.yaml
```

`__init__.py` files were created under `src/evo/`, `src/sat/`, `src/llm/` and
`src/llm/providers/` in the staging tree only. The repo has none — `src/` is not
a package there, and the CLIs rely on a `sys.path` fallback. Keeping the staging
tree a proper package makes `python -m src.cli.run_memetic_shard` deterministic
on a compute node instead of dependent on the CWD.

`src/llm/` is copied because `evo/memetic.py` imports `LLMAdvisor` and
`NoopProvider` unconditionally at module level (`memetic.py:7-8`), even though
the advisor call site is dead code wrapped in a `''''''''` string literal
(`HARNESS_PLAN` §1.6.2). Without those files the import fails. **No LLM call is
made by these runs** — the provider is `NoopProvider` and the block that would
call it never executes. Nothing here needs a GPU or an Ollama server.

Verify the mirror after any edit:

```bash
for f in evo/memetic.py evo/operators.py evo/population.py \
         sat/cnf.py sat/state.py sat/walksat.py \
         llm/advisor.py llm/prompt.py llm/providers/noop.py \
         llm/providers/ollama.py cli/run_memetic_shard.py; do
  diff -q "src/$f" "cluster_staging_maxsat/src/$f" >/dev/null \
    && echo "IDENTICAL src/$f" || echo "DIFFERS  src/$f"
done
```

### 2.3 What was deliberately *not* reused

`src/cli/run_experiment.py` already runs the memetic EA over a directory and
writes a CSV, but it is unusable as an array payload:

* its `instance` column is the **basename only**, so a record cannot be joined
  back to a checksum or a corpus;
* it records nothing about the solver configuration — no config hash, no seed
  provenance, no git sha, no host;
* it opens `--out_csv` in `"w"` mode, so two array tasks pointed at the same
  file race;
* its `soft_unsat` is *derived* by subtracting `best_soft_weight` from a
  separately-computed total rather than recomputed from the assignment.

`run_memetic_shard.py` fixes all four and implements every item in
`RC2_STATUS` §6 that applies to a solver run (sha256, resolved path, full solver
configuration, git sha, per-run shard naming). `run_experiment.py` is untouched
and still works for interactive use.

---

## 3. The blocker: 2 MSE instances cannot be run

Both MSE tier-2 instances are in the **MSE 2022+ ("new") WCNF format** — no
`p` line, hard clauses prefixed `h` (`RC2_STATUS` §1.5). Neither parser in the
memetic path can read it:

* `src/sat/cnf.py:parse_dimacs` → `ValueError: invalid literal for int() with
  base 10: 'h'` (measured);
* the `_parse_wcnf` fallback in `run_ea.py` / `run_experiment.py` asserts on a
  `p` line that is not there, then does `float("h")`.

RC2 reads them fine because `WCNF(from_file=...)` in PySAT supports the new
format. So this is a memetic-side gap, not a corpus problem.

`make_tier2_manifest.py` detects the format up front and writes the two
instances to `tier2_skipped.txt` with the reason rather than emitting jobs that
would fail on a compute node. `run_memetic_shard.py` independently re-checks and
emits `status="unsupported_format"` if one reaches it anyway (measured).

**Consequence to state plainly in any write-up:** tier-2 memetic results cover
the **SATLIB random 3-SAT half of tier 2 only**. There is no structured/industrial
instance in the runnable set. Any claim about the EA "on tier 2" is a claim about
uniform random 3-SAT at 200–250 variables.

**To unblock:** add new-format WCNF support to `src/sat/cnf.py:parse_dimacs`
(accept a missing `p` line, treat a leading `h` as hard, derive `n_vars` from the
maximum literal). That is a self-contained change of maybe 20 lines. Once it
lands, re-run `make_tier2_manifest.py` and the two instances flow into the
manifest automatically — no other change is needed.

---

## 4. Deploying and submitting

### 4.1 Preflight (do this once per rsync)

The `maxsat` conda env must have **PyYAML** — the configs are YAML and
`run_memetic_shard.py` will exit with an explicit error naming the package if it
is missing. `requirements.txt` pins `pyyaml>=6.0.1`; the workstation Python here
does not have it installed, so do not assume the cluster env does.

```bash
module load anaconda && source activate maxsat
python -c "import yaml; print('yaml', yaml.__version__)"
python -c "import sys; sys.path.insert(0,'src'); import evo.memetic; print('memetic ok')"
```

### 4.2 Build the manifest (workstation)

```bash
python -m src.bench.make_tier2_manifest \
    --hardness-dir results/hardness \
    --data-root cluster_staging_maxsat \
    --out-dir cluster_staging_maxsat/scripts
```

Knobs: `--tiers T2a T2b`, `--no-solved-t3`, `--configs …`, `--seeds …`,
`--budgets …`, `--prefix`. It prints the array range to submit.

### 4.3 Ship it

```bash
rsync -av --exclude '__pycache__' \
    cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
```

`cluster_staging_maxsat/data/` is gitignored but **must** be rsynced — the 26
instances live only there.

### 4.4 Smoke, then submit

```bash
cd ~/maxsat-lab/scripts
sbatch scripts/smoke_tier2_memetic.sbatch          # 5 tasks, 10 s budget, ~1 min
# inspect results/tier2_memetic_smoke/*.jsonl -> all status "ok"
sbatch --array=1-780%30 scripts/tier2_memetic_array.sbatch
```

The sbatch reads `MANIFEST`, `OUTDIR` and `GRACE` from the environment so a
partial re-run needs no file edit:

```bash
sbatch --array=17,204,555 --export=ALL,OUTDIR=results/tier2_memetic/tasks \
       scripts/tier2_memetic_array.sbatch
```

**Line N of the manifest is array task N.** That is the invariant the whole
pipeline rests on, and it is why the manifest has no header row. It also fixes
the two provenance defects `RC2_STATUS` §4.4 found in the RC2 runs: shard names
are globally unique (`t2m_00001.jsonl`, prefix settable via `--prefix`), so a
flat re-aggregation cannot silently overwrite; and the task index is a dense
1..N over the manifest, so a gap means a lost task rather than an unexplained
offset like `uuf250_1000c`'s 66–100.

### 4.5 Resources

`--time=00:15:00`, `--mem=8G`, `--cpus-per-task=1`, `OMP_NUM_THREADS=1`.

The wall limit must cover the **largest** budget in the manifest plus grace and
startup — SLURM applies one limit to the whole array, so a 60 s job in the same
array as a 300 s job still reserves 15 min. If you add a 900 s budget, either
raise `--time` or generate one manifest per budget and submit an array each.
8 GB is generous for a 250-variable instance; it is the RC2 array's setting kept
for consistency, and the EA's population is the only real allocation.

---

## 5. The experiment grid

```
instances = 26 tier-2 SATLIB (18 uuf250_1000c + 8 uuf_diff_unsat)
configs   = { memetic_base, memetic_pop150, memetic_deeppolish }
budgets   = { 60 s, 300 s }
seeds     = { 1, 2, 3, 4, 5 }
jobs      = 26 x 3 x 2 x 5 = 780
solver-s  = 26 x 3 x (60+300) x 5 = 140 400 s = 39.0 h
wall      = ~1.5 h at --array=...%30
```

**Why these budgets.** They bracket the RC2 tier boundaries: 60 s is the T1/T2a
line and 300 s the T2a/T2b line. An EA that matches RC2's optimum within 60 s on
a T2a instance has beaten the exact solver on that instance by construction. Two
points are also the minimum needed to say anything about the budget's marginal
value — `RC2_STATUS` §3.3 showed RC2's marginal return past 300 s is small, and
the same question applies to the EA.

**Why `ea.max_gens: 1000000` in every tier-2 config.** `run_memetic` stops on
`time_cap` **or** `gen < max_gens`, and `max_gens` defaults to **100**
(`memetic.py:65`). With the default, a 300 s budget would silently end early and
the recorded `wall_time_s` would be meaningless as a budget measurement. Setting
it out of reach makes wall-clock the sole binding stop condition.

**Seeds.** Five, per `HARNESS_PLAN` §3.1. `RC2_STATUS` §4.2 measured ~9 %
run-to-run jitter in RC2's own `solve_s` on a repeated instance; a stochastic EA
is far noisier, so single-seed numbers are not reportable.

---

## 6. Combining RC2 and memetic results

### 6.1 Run it

```bash
rsync -av <cluster>:~/maxsat-lab/results/tier2_memetic/ results/tier2_memetic/

python -m src.bench.combine_tier2 \
    --in-dir results/tier2_memetic/tasks \
    --oracle cluster_staging_maxsat/scripts/tier2_oracle.csv \
    --manifest cluster_staging_maxsat/scripts/manifest_tier2_memetic.tsv \
    --out-dir results/tier2_memetic
```

Outputs: `all_runs.jsonl` (verbatim shards — the source of truth),
`runs.csv` (one row per run), `by_instance.csv` (aggregated over seeds),
`summary.csv` (one row per config × budget), `integrity.txt`.

### 6.2 The join key

**Join on `instance_sha256`.** `tier2_oracle.csv` carries the sha256 the manifest
generator computed for each staged file; every shard carries the sha256 of the
file it actually opened. Matching them proves the memetic run and the RC2 tier
label refer to the same bytes.

The RC2 records themselves have **no checksum** (`RC2_STATUS` §2.5), which is
why the oracle table is the mediator rather than joining shards to
`all_results.jsonl` directly. The chain is:

```
RC2 record  --(instance path)-->  staged file  --(sha256)-->  memetic shard
            [make_tier2_manifest resolves and checksums once]
```

If the sha does not match, `combine_tier2.py` falls back to a **basename** join
and writes an explicit anomaly line into `integrity.txt`:

```
sha mismatch on uuf250-087.cnf (shard a0d4a608… vs oracle 0d27afc5…)
-- joined by basename, the bytes solved differ from the bytes profiled
```

Do not ignore that line. It means the corpus changed between manifest build and
run, and it is precisely the failure `RC2_STATUS` §4.5 could not rule out for the
original RC2 runs.

Never join on the RC2 `instance` path across runs: `RC2_STATUS` §2.5 shows the
global key is `(run_dir, instance)`, because the 75 MSE basenames appear in two
runs. The oracle table has already collapsed that, keeping `rc2_run` and
`rc2_runs_all` so the provenance survives.

### 6.3 Cost semantics — the one thing that must not be got wrong

Both sides report **unsatisfied soft weight, lower is better**:

| side | field | definition |
|---|---|---|
| RC2 | `profile.final_cost` | RC2's `cost` = total weight of unsatisfied soft clauses (`RC2_STATUS` §2.2) |
| memetic | `best_cost` | recomputed from the returned assignment by `score_assignment()` |

They are directly subtractable. Two traps:

1. **`run_memetic` returns the opposite convention.** `best_soft_weight` is
   *satisfied* soft weight. `run_memetic_shard.py` never uses it for `best_cost`
   — it re-derives the cost from `meta.assign_bits` against the parsed instance,
   and keeps the solver's own number in `best_soft_weight_reported` only as a
   cross-check. Verified on a partial-MaxSAT instance with hard clauses:
   500 soft total, 492 reported satisfied, `best_cost` 8, `unsat_soft_clauses` 8.
2. **`satisfied_clauses.unsatisfied` in the raw EA output counts hard clauses
   too.** It is not the cost. Do not use it.

**Infeasible runs must be excluded, not averaged.** A record with
`hard_violations > 0` did not find a feasible assignment, so its `best_cost` is
not comparable to an optimum. `combine_tier2.py` sets `feasible=False` and drops
those rows from every aggregate while still counting them in `n_failed`. On the
26 SATLIB instances this cannot fire (`n_hard == 0` throughout), but it will the
moment §3 is unblocked and the MSE instances join.

**A negative `abs_gap` is a bug signal, not a result.** If the EA reports a cost
*below* RC2's optimum, the two solvers disagree about what the instance is —
almost certainly a parse difference of the kind `RC2_STATUS` §3.5 found with the
`%`/`0` trailer. `combine_tier2.py` flags it in `integrity.txt` and says not to
average the row. Investigate before reporting anything.

### 6.4 Which metrics to report

`summary.csv`, one row per (config, budget):

| column | meaning |
|---|---|
| `run_hit_rate` | fraction of feasible runs reaching the optimum |
| `instance_coverage` | fraction of instances solved by **at least one** seed |
| `abs_gap_mean` / `_median` / `_max` | absolute cost gap, in clauses |
| `rel_gap_mean` / `_median` | relative gap — **read §6.5 before using** |
| `solver_seconds` vs `rc2_seconds_for_same_instances` | total budget spent vs what RC2 spent |
| `n_failed` | non-`ok` or infeasible runs |

**Headline metric: `run_hit_rate`.** "This config reaches the proven optimum on
X % of (instance, seed) pairs within a Y s budget" is the claim the design
supports. `instance_coverage` is the weaker per-instance version and should be
reported alongside — a config with high coverage but low hit rate is
high-variance, which is itself the finding.

### 6.5 Why `rel_gap` is the wrong headline here

`RC2_STATUS` §3.4 measured the optimum distribution: **65 of 73 solved SATLIB
instances have OPT = 1**, the rest OPT = 2. The 26 tier-2 instances inherit this
— 24 at OPT 1, 2 at OPT 2.

So `rel_gap = (best_cost − OPT) / OPT` takes values 0, 1, 2, 3… A single missed
clause is a "100 % relative gap". The quantity is near-binary and its mean is
dominated by how many runs missed by exactly one, which `abs_gap_mean` already
says more honestly. Report `abs_gap` in clauses and `hit_rate`; keep `rel_gap`
in the CSV for cross-corpus comparability later, but do not put it in a headline.

The same fact caps the ambition of this experiment: on this corpus the EA's task
is to satisfy all but one clause out of 1065, and "success" is nearly
all-or-nothing. A corpus with a graded cost distribution — which is exactly what
`docs/INSTANCEGEN_PLAN.md` is for — is needed before gap curves mean much.

### 6.6 Speed comparison, and its limit

`speedup_vs_rc2 = rc2_solve_s / wall_time_s`, reported only for runs that
actually reached the optimum. It is an **upper bound on the EA's advantage**,
because `wall_time_s` is the full budget spent, not the time at which the best
assignment was first found. The EA has no anytime curve today — `run_memetic`
exposes no improvement callback, and `HARNESS_PLAN` §5.3 (event-driven
`(t, cost)` recording) is still unimplemented.

To make time-to-optimum a real measurement, either add an improvement callback
to `run_memetic` and record `(t, cost)` pairs in the shard, or sweep budgets
(10, 30, 60, 120, 300 s) and read the hit-rate curve. The manifest generator
takes `--budgets`, so the second option costs nothing but cluster time.

Note also that RC2's `solve_s` includes WCNF parse time and, for the SATLIB runs,
comes from a run with **no `--bestknown`**, so `ratio`/`lb_ratio` are
structurally null there (`RC2_STATUS` §4.3(b)). Only `final_cost` is usable from
those two runs — which is all the join needs.

---

## 7. Calibration warning: read this before interpreting anything

In a measured 8 s run on `uuf250-0100.cnf` with `memetic_base` (pop 60), the EA
completed **3 generations / 171 children / ~74 000 flips**. Three generations is
not an evolutionary search. At that rate a 60 s budget buys roughly 20
generations and 300 s roughly 110.

The corollary is that at 60 s the result is largely **the WalkSAT polish**, run
171 times from crossover-perturbed starting points — closer to a restart
portfolio than to a memetic algorithm. That is a legitimate solver, but it is not
evidence about the EA's evolutionary component, and the write-up must not claim
otherwise.

It also means `memetic_deeppolish` (12 500 flips per child vs 700) will complete
far fewer generations still, so the three configs differ in generation count as
much as in structure. `ea_generations` and `children` are recorded in every
shard precisely so this is visible rather than assumed — check the
`ea_generations` column in `runs.csv` before comparing configs.

Two measured data points worth knowing going in: at an 8 s budget the EA already
reached the RC2 optimum on `uuf250-0100` (RC2: 219 s) and on `uuf250-094`
(RC2: 130 s), on 1 of 3 and 2 of 2 seeds respectively. If that holds at scale,
**60 s and 300 s are both far past saturation** and the interesting budgets are
below 10 s. Consider a first pass with `--budgets 1 5 10 30` before committing 39
solver-hours to the default grid.

---

## 8. Known gaps

| gap | status |
|---|---|
| 2 MSE tier-2 instances unrunnable (new-format WCNF) | **open** — §3; ~20-line fix in `src/sat/cnf.py` |
| No anytime curve, so time-to-optimum is unmeasured | **open** — §6.6; needs a callback in `run_memetic` or a budget sweep |
| `run_memetic` ignores its own `pmutate`/`tournament_k` in some paths | not investigated; configs record what was *passed*, not what was honoured |
| `mutate1(..., ind.hard_satisfied)` at `memetic.py:93` reads `ind` leaked from an earlier loop | pre-existing latent bug, untouched by this work; irrelevant on the 26 zero-hard-clause instances, **will matter** once MSE instances are unblocked |
| Tier thresholds still cap-independent | pre-existing (`RC2_STATUS` §4.4c); mitigated by carrying `rc2_cap_s` in the oracle table |
| Corpus is uniform random 3-SAT only | structural, see §3 and §6.5 |

---

## 9. Reproducing the measurements in this document

```bash
# manifest + oracle + skip list (§1.1, §3)
python -m src.bench.make_tier2_manifest

# a single shard, short budget (§7)
python -m src.cli.run_memetic_shard \
    --instance cluster_staging_maxsat/data/unsat250_1000c/uuf250-0100.cnf \
    --config configs/tier2/memetic_base.yaml --config-id memetic_base \
    --seed 1 --budget-s 8 --oracle-cost 1 --tier T2a --rc2-run uuf250_1000c \
    --job-id t2m_00001 --out /tmp/shards/t2m_00001.jsonl

# combine (§6.1)
python -m src.bench.combine_tier2 \
    --in-dir /tmp/shards \
    --oracle cluster_staging_maxsat/scripts/tier2_oracle.csv \
    --out-dir /tmp/combined

# hard/soft accounting cross-check (§6.3)
python -m src.cli.run_memetic_shard \
    --instance data/dev_small/file_rpms_wcnf_L3_V100_C600_H100_0.wcnf \
    --config configs/tier2/memetic_base.yaml --seed 1 --budget-s 5 \
    --out /tmp/hard_test.jsonl --job-id hard_test
```

Requires PyYAML (§4.1).
