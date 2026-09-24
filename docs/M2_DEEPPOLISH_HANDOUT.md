# M2 — modified `memetic_deeppolish` on the 30–900 s certified pool: understanding handout

**Date:** 2026-09-24. Written against commit `98fbd38` (calib_b B1 results,
Checkpoint 4). **Documentation stage only.** Nothing in this stage changed
solver code, configs, manifests or scripts, and no job was submitted. Every
number below was either recomputed from the result files for this handout or
is cited to its source file. Numbers that are estimates are labelled as such.

Inputs read: `docs/CORPUS_CALIBRATION_LOG.md` (Checkpoints 0–4),
`docs/CALIB_B_SUMMARY.md`, `docs/CALIB_B_PLAN.md`,
`docs/CALIB_B_B1_READOUT.md`, `docs/CORPUS_CALIBRATION_GOALS.md` §4–§7,
`cluster_staging_maxsat/DIVERGENCE.md`, and the code and results listed in §4.

---

## 0. Decisions this handout is built on (from the user, 2026-09-24)

1. **Population:** every RC2-certified instance with **30 s ≤ `solve_s` ≤ 900 s**,
   pooled from `calib_a` ∪ `calib_b` and deduplicated on `instance_sha256`.
   This supersedes the earlier 60 s floor. The original tier labels are kept,
   and every result is reported for the whole population **and** separately
   for three disjoint groups:

   | group label | rule | role |
   |---|---|---|
   | `lower_ext` | 30 ≤ `solve_s` ≤ 60 | lower-window extension |
   | `tier2` | 60 < `solve_s` ≤ 600 | the repository's original Tier-2 window |
   | `upper_ext` | 600 < `solve_s` ≤ 900 | upper-window extension (`include_solved_t3`) |

   Uncertified (censored) instances stay out. A recovered `cost_lower_bound`
   is a lower bound, not an optimum, and cannot serve as a stop target.
2. **Solver:** `memetic_deeppolish` with **more wall time per local-search
   call**. The 12,500-flip limit per call and the 900 s budget per run stay
   the same. 3 solver seeds per instance, stop-at-known-optimum on.
3. **Pilot first.** Compare the original and the proposed per-call allowance
   on matched instances and matched solver seeds before running production.
4. The existing cluster environment is kept unless a concrete blocking defect
   turns up. None was found (§10).

---

## 1. Project status

### Completed (committed, with results in the repository)

| step | what | evidence |
|---|---|---|
| M1 | `calib_a` grid (36 cells × 5 generator seeds = 180 instances), generator CLI, RC2 array with resume | log Checkpoint 1, commit `42f953e` |
| A1 | RC2 on calib_a: 180/180 rows, 92 certified, 88 censored | Checkpoint 2, `cluster_staging_maxsat/results/profile_calib_a_all.jsonl` |
| calib_b | α refinement (22 cells, 110 instances; generator seeds 1–5 for exploratory cells, 6–10 for reinforcement cells) | Checkpoint 3, `instancegen/grids/calib_b.yaml` |
| B1 | RC2 on calib_b: 110/110 rows, 85 certified, 25 censored, 0 failed | Checkpoint 4, `.../profile_calib_b_all.jsonl` |
| selection tooling | `src/bench/calib_tier2_select.py` (instance rule + cell table) | `results/calibration/tier2_eligible.csv` (46 rows, 60–600 s) |
| historical tier-2 memetic runs | 3 memetic configs × 26 SATLIB uuf instances × 5 seeds, 900 s, target stop | `cluster_staging_maxsat/results/tier2_memetic_all.jsonl` (390 rows, 2026-08-12) |
| historical LS-only baseline | `local_multistart_deeppolish`, same instances | `.../tier2_local_multistart_all.jsonl` (130 rows) |

### Not done: planned, and not started

- **M2 has not been run on any calibration instance.** No memetic data exists
  for calib_a or calib_b.
- No M2 manifest builder exists yet. Goals §6 names
  `make_calib_memetic_manifest.py`, and it has not been written.
- M3 (yield table, ρ), M4 (freeze rules, fresh corpus), M5: not started.
- Open decisions carried from Checkpoint 4 that this experiment does not
  close: PySAT 1.9.dev3 freeze vs. upgrade; goals §5.4 (fresh seeds vs.
  calibration instances in the reported corpus). See §11.

---

## 2. The population, verified from the result files

### 2.1 How it was verified

I read `cluster_staging_maxsat/results/profile_calib_{a,b}_all.jsonl` (180 + 110
rows) and joined them to `cluster_staging_maxsat/data/generated/calib_{a,b}/manifest.jsonl`
on the instance path. **I recomputed the sha256 of every instance file** and
compared it with the manifest. Then I deduplicated on the hash, kept rows with
`profile.completed == true`, and applied the three group rules above.
Cross-check: `python -m src.bench.calib_tier2_select --batches calib_a calib_b
--floor 30 --ceiling cap --no-write` lists the same 70 instances.

| check | result |
|---|---|
| rows | 290 (180 + 110) |
| file sha256 vs manifest | 0 mismatches |
| distinct `instance_sha256` | 290 (no duplicates, so deduplication removes nothing) |
| status classes | 177 `optimal`/completed, 106 `subprocess_killed`, 7 `timeout`; **0 failed** |
| `cap_s` | 900 on every row |
| PySAT on the RC2 rows | `1.9.dev3` × 290 |
| **certified** | **177** |

### 2.2 The counts

| group | rule | instances | 2-SAT / 3-SAT | cells | original tier labels | batch a / b |
|---|---|---:|---|---:|---|---|
| `lower_ext` | 30 ≤ s ≤ 60 | **16** | 6 / 10 | 11 | T1 × 16 | 5 / 11 |
| `tier2` | 60 < s ≤ 600 | **46** | 18 / 28 | 21 | T2a × 37, T2b × 9 | 10 / 36 |
| `upper_ext` | 600 < s ≤ 900 | **8** | 2 / 6 | 6 | T3 × 8 | 2 / 6 |
| **total** | 30 ≤ s ≤ 900 | **70** | 26 / 44 | 24 distinct (k, n, α) | | 17 / 53 |

**16 + 46 + 8 = 70 is confirmed.** At 3 solver seeds that is **210 runs**, and
the solver-budget ceiling is 210 × 900 s = **52.5 CPU-h**, excluding grace and
overhead (§8).

**Boundaries.** No certified instance lies on a boundary. The nearest values
are 28.56 / 28.66 s (excluded) and 31.15 s (included) around 30 s, 62.0 s
above 60 s, and 610.3 s above 600 s. The largest certified value is 847.3 s.
So `30 ≤ s` and `30 < s` select the same set here. The builder will still
implement the inclusive rule exactly as the user stated it. Note that
`calib_tier2_select.classify` treats `s ≤ floor` as trivial, which is the
strict reading.

**Composition by (k, n) row, all 70:**

| row | lower_ext | tier2 | upper_ext | total | m (clauses) in row |
|---|---:|---:|---:|---:|---|
| 2-SAT n = 100 | 1 | 4 | 1 | 6 | 400–600 |
| 2-SAT n = 150 | 3 | 4 | 0 | 7 | 450–495 |
| 2-SAT n = 250 | 0 | 1 | 1 | 2 | 588 |
| 2-SAT n = 400 | 2 | 9 | 0 | 11 | 800–920 |
| 3-SAT n = 50 | 3 | 6 | 5 | 14 | 400–450 |
| 3-SAT n = 70 | 2 | 11 | 0 | 13 | 420–455 |
| 3-SAT n = 100 | 1 | 6 | 0 | 7 | 500–550 |
| 3-SAT n = 150 | 1 | 0 | 1 | 2 | 720–750 |
| 3-SAT n = 250 | 3 | 5 | 0 | 8 | 1065–1088 |

c\* ranges: 2-SAT 18–50 and 3-SAT 1–13. Every instance has c\* ≥ 1, so
none is satisfiable. Clause counts span m = 400–1088, and this matters for
§4, because the local-search cost per flip grows with m.

The eight `upper_ext` instances match `CALIB_B_B1_READOUT.md` §4c exactly:
610.3, 612.0, 621.9, 626.7, 648.7, 752.7, 772.2 and 847.3 s.

### 2.3 Discrepancies and overstated claims in the source documents

These are listed so later write-ups do not repeat them.

1. **"24-instance margin below the window"** (`CALIB_B_B1_READOUT.md` §7 item 3;
   log Checkpoint 4, open item 3). That figure is wrong: 70 − 46 = 24 counts
   **16 instances below the window and 8 above it**. Only 16 lie below 60 s.
2. **"Fills the empty 450–600 s shoulder"** (`CALIB_B_SUMMARY.md` item 2,
   read-out §4c/§7, log). Adding the 600–900 s instances does **not** fill
   the 450–600 s band. After the extension it still holds **0 of 70**.
   The extension adds instances above 600 s. It does not add any inside
   450–600 s.
3. **"Thinned by the cap, not by the instances"** (read-out §4a). The
   900 s cap does not explain the empty 450–600 s band by itself. Censoring
   pressure should rise toward 900 s, yet 5 certified instances lie in
   600–650 s while 450–600 s holds none. With 54 instances ≤ 900 s, an empty
   150 s band can be a sampling artefact, a per-row c\*-ladder effect, or
   both. **The band is empty and the cause is unexplained.**
4. **"The only route to any 3-SAT n = 150 instance"** (summary item 2,
   read-out §4c). That was true only under the 60 s floor. Under the adopted
   30 s floor, 3-SAT n = 150 α = 4.8 seed 3 (34.9 s, c\* = 2) enters
   `lower_ext`, so this row has 2 instances.
5. **"No α placement can put instances in the window" / "a fifth would not
   change that"** (read-out §5, log). Zero eligible instances at four α
   values × 5 seeds does not prove eligibility impossible. It supports
   *low expected yield* at those settings, since the row shows within-c\*
   variance as well (c\* = 2 completions ranged from 1.9 s to 34.9 s). Read it
   as an empirical yield statement, not an impossibility.
6. **Budget rounding.** The documents say "≤ 52 CPU-h". The exact solver-budget
   ceiling is 52.5 CPU-h, or 56.0 CPU-h including the 60 s grace (§8).
7. **The documents use two sizing rules that conflict.** Summary item 1
   recommends *not* adopting the 30 s floor, while item 3 recommends running
   M2 on the ≥ 30 s set. The user's decision (§0) resolves this: the M2
   population is 30–900 s, grouped. `T1_MAX_S = 60` and `assign_tier()` stay
   unchanged, and the original tier labels are carried as data.

---

## 3. What the "WalkSAT" component actually is

The user's name "WalkSAT" matches the repository's own term. Call chain for
one local-search call inside `memetic_deeppolish` (staging tree):

```
src/evo/memetic.py::run_memetic                 (fill loop, line ~137)
  -> src/evo/operators.py::short_polish          (line 385)   "Polish a child using WalkSAT"
     -> src/sat/walksat.py::walksat_polish       (line 529)   "Lightweight WalkSAT-style polish"
        state: src/sat/state.py::SatState
```

`walksat_polish` is a **WalkSAT-style focused random walk** with the
following steps:

1. Pick a uniformly random falsified clause (hard clauses first, if there are any).
2. With probability `noise`, flip the first variable in shuffled order that
   breaks no hard clause. Otherwise, flip the variable with the best
   soft-weight gain (ties go to the fewer hard breaks).
3. Keep the best assignment seen, and return it.

There is **no tabu list, no clause weighting** (`smooth_every = 0`), and no
restarts. `noise = 0.10`, `hard_safe = True` and `smooth_every = 0` are
**code defaults in `short_polish`**. They are not config keys, so they are
not in `config_hash`. The comment in the deeppolish YAML says "plain
SATLike with a GA restart policy", but the dynamic-weight machinery is
present and disabled. `run_satlike` in the same file is a different routine
and is not used by the EA. The rest of this handout uses the repository's
names: **local-search call = one `short_polish` → `walksat_polish`
invocation**, one per EA child.

---

## 4. Budget hierarchy: from configuration to the flip loop

### 4.1 Which runner is authoritative

**The cluster runs the staging tree `cluster_staging_maxsat/`.** Of the
eleven solver files, three are deliberately ahead of repo `src/`, as
recorded in `cluster_staging_maxsat/DIVERGENCE.md`: `evo/memetic.py`
(target stop), `cli/run_memetic_shard.py` (`--stop-at-oracle`, schema v2,
solver dispatch) and `sat/cnf.py` (new-format WCNF). I checked with
`diff -rq src cluster_staging_maxsat/src` that only these three differ among
the solver files. The eight "must stay identical" files, `sat/walksat.py`,
`sat/state.py` and `evo/operators.py` among them, are byte-identical.
`configs/tier2/memetic_deeppolish.yaml` is identical in both trees. **The
repo `src/evo/memetic.py` has no target stop and must not be used for this
experiment.** The repo `src/` also has no `evo/multistart.py`.

### 4.2 The trace

| level | key / value | where it is read | scope | enforced where |
|---|---|---|---|---|
| Slurm | `--time=00:20:00`, 1 CPU, 8 GB | `scripts/tier2_memetic_array.sbatch` | array task | Slurm kills the task, which leaves no shard |
| watchdog | `--grace-s 60` → SIGALRM at budget + grace = **960 s** | `run_memetic_shard.py:429` (`setitimer`) | solver call | raises `_Timeout`; the record gets `status="timeout"` (a **failed** row, §4.4 of goals) |
| run budget | `--budget-s 900` from the manifest → **top-level** `cfg["time_limit_s"] = 900` ("the budget always wins") | `run_memetic_shard.py:315` | whole run | `memetic.py:77`, checked **only at the top of each generation** (`while` on line 125) |
| target stop | `--stop-at-oracle` + `--oracle-cost c*` → `target_cost` | `run_memetic_shard.py:287` | whole run | checked **after every child** (`memetic.py:180–185`) and once before generation 1 |
| generations | `ea.max_gens: 1000000` | `memetic.py:79` | whole run | unreachable in 900 s |
| children per generation | `pop_size − ceil(0.05·pop_size)` = 40 − 2 = **38** | `memetic.py:129–137` | generation | one local-search call per child |
| **per-call time** | **`ls.time_limit_s: 0.5`** | `memetic._ls_budget` → `short_polish:403` → `walksat_polish(time_limit_s=)` | **one local-search call** | `walksat_polish` `time_up()`, checked every iteration |
| **per-call flips** | **`ls.ls_polish_flips: 12500`** | `_ls_budget` → `short_polish:402` (`ls_polish_flips` wins over `max_flips`) → `walksat_polish(max_flips=)` | **one local-search call** | loop condition `state.flips < max_flips` |
| (dead) | `ls.flip_budget: 12500` | mapped to `max_flips` by `_ls_budget`, but `short_polish` prefers `ls_polish_flips` | — | never binds on this path |
| (dead) | `ea.ls_polish_flips` (not set; default 700) | `_ea_cfg`, then never used | — | — |
| per-call early exit | no falsified clause left | `walksat_polish` (`target == -1`) | one call | impossible here: all 70 instances have c\* ≥ 1 |

Two keys share the name `time_limit_s` at two levels. The top-level key is
the run budget and `ls.time_limit_s` is the per-call allowance. If the
runner did not inject the top-level key, `memetic.py:77` would fall back to
`ls.time_limit_s`, and a run would last half a second. The runner always
injects it, so it works, but a new config must not set a top-level
`time_limit_s`.

**Answers to the scoping questions:**

- **The 12,500-flip limit applies per local-search call**, that is, per
  child polished. It does not apply per individual in the initial population
  (the JW-seeded initial population is never polished), per generation or
  per run. There is no run-level flip limit on the EA path:
  `--max-total-flips` is refused for `memetic_ea`.
- **The ~2,500 figure refers to the same scope**, per call. The shard's
  `total_flips` is the sum of `walksat_polish`'s returned `flips` (loop
  iterations) over all calls. `children` is the number of calls. So
  `total_flips / children` is the mean flips per call. On pure-soft
  instances every iteration flips a variable (`hard_safe` never vetoes when
  `delta_hard = 0`), so iterations and applied flips are equal.
- **Interaction with the run budget:** there is none inside a call. A
  local-search call does not know the remaining run time. The global deadline
  is tested only between generations, so a run overshoots 900 s by up to one
  full generation, 38 calls. At 0.5 s per call that is about 19 s and fits
  inside the 60 s grace. **With a longer allowance it would not fit** (§6.2).

### 4.3 Evidence that the per-call time allowance binds: historical cluster rows

Source: `cluster_staging_maxsat/results/tier2_memetic_all.jsonl`,
`config_id = memetic_deeppolish`: 130 runs (26 SATLIB uuf instances,
n = 250/m = 1065 × 120 runs and n = 200/m = 860 × 10 runs, 5 seeds each), 900 s,
`STOP_AT_ORACLE=1`, cluster python 3.11.15, 19 hosts, 2026-08-12. Outcomes:
118 `target` and 12 `time_cap`.

| measurement | value |
|---|---|
| mean flips per call (`total_flips/children`), across runs | min **1,486**, Q1 2,110, median **2,172**, Q3 2,288, max **3,118** |
| runs where the mean reached 12,500 | **0 of 130** |
| wall time per child on the 12 `time_cap` runs | **0.503–0.504 s** (0.5 s allowance + about 3 ms of setup, crossover and evaluation) |
| overshoot past 900 s on `time_cap` runs | 17.2–18.6 s (one 38-child generation × 0.5 s ≈ 19 s) |
| median generations / children | 2 / 59 (most runs hit the target early; median TTT 27.7 s, max 734.7 s) |

Every call used its full 0.5 s and executed roughly 1/6 of the 12,500 flips
it was allowed. **The hypothesis is confirmed on the cluster, for these
instances.** "About 2,500" is right for m ≈ 1,000. The same pattern holds
for `memetic_base` (0.05 s, 700-flip limit, median 208 flips per call), so
the time allowance is also what binds in the other presets.

**Why each flip is this expensive.** Every iteration of `walksat_polish`
scans the full clause list several times. `unsat_hard_ids()` and
`unsat_soft_indices()` build lists over all m clauses to pick a falsified
clause, `_count_hard_violations()` scans all m, and
`snapshot_best_if_better()` scans all m twice (hard count and soft
objective). The cost per flip is therefore O(m) in pure Python rather than
O(clause occurrences). This is a property of the code, and it is the
reason the time allowance binds. A faster incremental implementation would be
a different fix, touching code shared by every preset and the LS-only
baseline. **It is not proposed here.** The user's decision is to change the
allowance.

### 4.4 Local measurement on the calibration rows (workstation, estimate only)

I ran `walksat_polish` from the staging tree unchanged, on the
largest-m eligible instance of each row, from random starts: 3 repetitions,
median, `max_flips=12500`, `noise=0.10`. The workstation runs python 3.12.3.
**Workstation speed differs from the cluster.** Comparing uuf250 on the
cluster (m = 1065, 2,172 flips / 0.5 s) with calib 3-SAT n = 250 here
(m = 1088, 3,047 flips / 0.5 s) gives a cluster/workstation rate ratio of
about 0.70. The "cluster est." columns scale by that one factor, so treat
them as rough.

| row (instance used) | m | flips in 0.5 s (ws) | time to 12,500 flips (ws) | flips in 0.5 s (cluster est.) | time to 12,500 (cluster est.) |
|---|---:|---:|---:|---:|---:|
| 2-SAT n=150 α3.3 | 495 | 8,968 | 0.72 s | ~6,300 | ~1.0 s |
| 3-SAT n=50 α9 | 450 | 6,563 | 0.95 s | ~4,600 | ~1.4 s |
| 3-SAT n=70 α6.5 | 455 | 6,858 | 0.92 s | ~4,800 | ~1.3 s |
| 3-SAT n=100 α5.5 | 550 | 5,871 | 1.07 s | ~4,100 | ~1.5 s |
| 2-SAT n=250 α2.35 | 588 | 7,363 | 1.12 s | ~5,200 | ~1.6 s |
| 2-SAT n=100 α6 | 600 | 6,934 | 0.91 s | ~4,900 | ~1.3 s |
| 3-SAT n=150 α5 | 750 | 4,395 | 1.41 s | ~3,100 | ~2.0 s |
| 2-SAT n=400 α2.3 | 920 | 3,608 | 1.73 s | ~2,500 | ~2.5 s |
| 3-SAT n=250 α4.35 | 1088 | 3,047 | 2.02 s | ~2,100 | ~2.9 s |

Read-out, as estimates:

- At 0.5 s the time allowance should bind on **every** row of the 70-instance
  population. The estimated flips per call are about 2,100–6,300, all well
  below 12,500.
- The "~2,500" figure describes the largest-m rows (2-SAT n = 400 at
  m ≈ 900 and 3-SAT n = 250 at m ≈ 1,070). Smaller-m rows probably execute
  2–3× more flips per call than that. The pilot measures this directly.

---

## 5. The proposed per-call allowance

**Pilot candidate: `ls.time_limit_s = 2.5` s (5 × 0.5 s).** It is not yet a
production setting.

Reasoning from the measurements:

- To let the 12,500-flip limit bind, the allowance must exceed the time 12,500
  flips take. On the cluster that is an estimated **1.0–2.9 s** depending on
  m, and the historical uuf250 rows give 12,500 / (2,172 / 0.5 s) ≈ 2.9 s at
  m = 1065.
- At 2.5 s the flip limit should bind on every row with m ≲ 900. That is
  about 59 of the 70 instances by m. It is **borderline at m = 920** (3
  instances), and it probably still does **not** bind at m = 1065/1088 (the 8
  3-SAT n = 250 instances), where the estimate is about 2.9 s.
- The allowance is a ceiling, not a target. Where the flip limit binds first,
  a call lasts about 1.0–2.5 s, not 2.5 s. The effective increase in work per
  call is therefore about 2–6× depending on the row, not a flat 5×.
- **The pilot is designed to test this directly.** It includes the m = 1088
  and m = 920 instances. §7.4 pre-registers what happens if 2.5 s is too
  short for them.

**Side effect that must be measured:** the run budget stays at 900 s, so
longer calls mean fewer calls and fewer generations. Rough numbers: about
1,780 calls (~47 generations) at 0.5 s, against about 320–900 calls
(~8–24 generations) when calls last 1–2.8 s. Deeper polish per child trades
against evolutionary turnover, and this is the trade the pilot measures. An
early stop at the known optimum counts as success. The design never forces
extra flips after the target is reached. The target check still runs after
every child.

---

## 6. Proposed changes (to implement in the next stage, not in this one)

### 6.1 A new configuration identity

- **Keep unchanged:** `configs/tier2/memetic_deeppolish.yaml` in both trees,
  its `config_id`, the historical 130 rows, and
  `local_multistart_deeppolish.yaml`.
  `tests/test_local_multistart.py` asserts that the latter's `ls:` block
  equals deeppolish's.
- **New:** `cluster_staging_maxsat/configs/tier2/memetic_deeppolish_ls2p5.yaml`,
  `config_id = memetic_deeppolish_ls2p5`. It keeps the same `ea:` block
  (pop 40, tournament 3, pmutate 0.02, elitism, max_gens 1e6) and the same
  `ls_polish_flips: 12500` / `flip_budget: 12500`, with
  **`ls.time_limit_s: 2.5`**. It also sets one new opt-in key,
  `ea.deadline_mode: clip` (§6.2). It carries no top-level `time_limit_s`.
  If the pilot changes the value, the id changes with it (`_ls3p0`, …); an
  id is never reused for a different value.
- **Later, not in this batch:** the evolutionary-contribution comparison
  needs a matching `local_multistart_deeppolish_ls2p5.yaml` with the
  **same revised `ls:` block and the same deadline handling**. Its existing
  test pattern (`test_polish_budget_matches_memetic_deeppolish`) should be
  cloned for the new pair. `multistart.py` has the same per-polish overshoot
  property (its docstring says "at most one polish"), which is much less
  severe because it has no 38-call generation.

### 6.2 A blocking defect for longer calls: the deadline is checked only at generation boundaries

With `ls.time_limit_s = 2.5`, one generation is 38 calls of about 1–2.9 s,
roughly 40–110 s. In the worst case the run starts a generation just before
900 s and finishes it at about 1,000 s. **The SIGALRM watchdog fires at
960 s, and the record becomes `status="timeout"`, a failed row under goals
§4.4, not a censored one.** This would hit every run that does not reach the
target. The user's requirement that longer calls respect the remaining
global budget therefore needs a code change. More budget alone would not
fix it.

Proposed change, active only under the new opt-in key so the original config
behaves identically:

- `memetic.py`, fill loop: before each child's polish, compute
  `remaining = time_cap − (now − start_t)`. If `remaining ≤ 0`, end the run
  with `stop_reason = "time_cap"`. Otherwise, polish with
  `time_limit_s = min(ls.time_limit_s, remaining)`.
- The result: every run ends within one local-search call's setup of 900 s,
  and no call runs past the deadline.
- When `ea.deadline_mode` is absent (the original deeppolish), the code path
  and the rng stream are unchanged, so the original config reproduces the
  historical rows. A unit test checks this on a flip-limited (deterministic)
  setting.

**Consequence for comparing the arms:** the original arm keeps its up-to-19 s
generation overshoot. Success is therefore defined for both arms as
**`stop_reason == "target"` and `time_to_target_s ≤ 900`**, which neutralises
that overshoot.

### 6.3 Minimum instrumentation (additive, shard schema v2 → v3)

Nothing currently records per-call data. `walksat_polish` already returns
`flips`, `total_flips` and `elapsed_sec`, but `short_polish` discards
everything except the flip count. Proposed, with **no change to
`walksat.py`/`state.py`**:

- `operators.short_polish`: add an optional `stats_out: dict | None = None`
  keyword that receives `walksat_polish`'s result dict. The return value and
  the default behaviour stay unchanged. This file is in the "must stay
  identical" set, so the edit is mirrored into `src/evo/operators.py`.
- `memetic.py`: classify each call's stop reason from the returned numbers,
  since the loop can exit only on these conditions:
  - `total_flips ≥ max_flips` → `flip_limit`
  - else, if `elapsed_sec ≥ allowance` and the allowance was clipped →
    `deadline_clip`
  - else, if `elapsed_sec ≥ allowance` → `time_limit`
  - else → `all_satisfied`

  Accumulate summaries (no per-call arrays; up to about 1,800 calls per run)
  into `res["meta"]["ls_stats"]`.
- `run_memetic_shard.py`: copy them into the record and add a
  `code_fingerprint` (below).

Record fields added per run:

| field | meaning |
|---|---|
| `ls_calls` | number of local-search calls (= `children`) |
| `ls_allowance_s`, `ls_flip_limit` | configured per-call limits, echoed |
| `ls_stop_counts` | `{flip_limit, time_limit, deadline_clip, all_satisfied}` |
| `ls_flips` | per-call executed flips: `sum, min, p10, median, p90, max` |
| `ls_elapsed_s` | per-call LS time: `sum, median, p90, max` |
| `ls_time_share` | `ls_elapsed_s.sum / wall_time_s` (the rest is crossover, evaluation and setup) |
| `ea_generations`, `children` | as before, now alongside `ls_calls` |
| `target_gen`, `target_child_index` | where the target was hit (null otherwise) |
| `stop_reason`, `time_to_target_s`, `wall_time_s`, `cpu_time_s`, `target_reached` | as before |
| `code_fingerprint` | sha256 over the 11 solver files in the staging `src/` |

The code fingerprint exists because the staging tree on the cluster is not a
git repo, and all 130 historical deeppolish rows have `git_sha = null`.
`MAXSAT_GIT_SHA` will be exported at submit time as well.

Median and percentiles are computed on a bounded reservoir or histogram so
memory stays constant. This will be settled in implementation.

---

## 7. Pilot

### 7.1 Design

- **Arms (2):** `memetic_deeppolish` (original, 0.5 s, unchanged code path)
  vs `memetic_deeppolish_ls2p5` (2.5 s with deadline clipping). Everything
  else is identical: 900 s budget, `STOP_AT_ORACLE=1`, grace 60 s, 1 CPU and
  8 GB, and the same shard runner, which in the next stage will carry the v3
  instrumentation for **both** arms.
- **Solver seeds:** 1, 2 and 3 in both arms. They are passed as `--seed` and
  seed `run_memetic`'s rng, and each call's WalkSAT seed is drawn from that
  rng. **Generator seeds** are a property of the instance (the `seed` field in
  `data/generated/calib_*/manifest.jsonl`, the `_sN` in the filename,
  values 1–10). Manifests carry them in separate columns, so the two cannot
  be confused.
- **Matching:** each (instance, solver seed) runs in both arms. The two runs
  share the initial JW population, but their trajectories diverge after the
  first call. The comparison is paired by (instance, seed), not per flip.
- **Instances (10):** chosen by a fixed rule, using no memetic data (none
  exists for these instances). The rule covers both k, all 9 (n, k) rows,
  all three groups (4 upper, 4 window, 2 lower), and the extremes of m
  (450–1088). Within a (row, group) cell the instance with the largest m is taken,
  and ties go to the median `solve_s`.

  | # | group | cell | gen. seed | batch | RC2 `solve_s` | c\* | m | why |
  |---:|---|---|---:|---|---:|---:|---:|---|
  | 1 | upper_ext | max2sat_n100_a6 | 1 | calib_a | 752.7 | 50 | 600 | largest c\* in pool |
  | 2 | upper_ext | max2sat_n250_a2.35 | 3 | calib_b | 610.3 | 22 | 588 | only other 2-SAT upper |
  | 3 | upper_ext | max3sat_n50_a9 | 5 | calib_b | 847.3 | 13 | 450 | hardest RC2 instance |
  | 4 | upper_ext | max3sat_n150_a5 | 3 | calib_a | 772.2 | 3 | 750 | the 3-SAT n = 150 row |
  | 5 | tier2 | max2sat_n400_a2.3 | 2 | calib_b | 367.2 | 23 | 920 | largest 2-SAT m (borderline at 2.5 s) |
  | 6 | tier2 | max2sat_n150_a3.3 | 4 | calib_b | 226.6 | 28 | 495 | small-m 2-SAT |
  | 7 | tier2 | max3sat_n70_a6.5 | 4 | calib_b | 217.8 | 7 | 455 | best-populated row |
  | 8 | tier2 | max3sat_n250_a4.35 | 2 | calib_b | 323.7 | 1 | 1088 | largest m (2.5 s probably too short) |
  | 9 | lower_ext | max3sat_n150_a4.8 | 3 | calib_b | 34.9 | 2 | 720 | lower-group 3-SAT n = 150 |
  | 10 | lower_ext | max3sat_n100_a5.2 | 5 | calib_b | 46.8 | 4 | 520 | completes row coverage |

  The manifest builder will write and verify each instance's path and sha.

- **Size:** 10 instances × 3 seeds × 2 arms = **60 runs**. The solver-budget
  ceiling is 60 × 900 s = **15.0 CPU-h**, or 16.0 CPU-h with grace. At `%30`
  that is 2 waves × about 17 min ≈ 35 min of elapsed compute in the worst
  case. Queue delay is separate and not estimated. Realistic cost is lower
  because target stops end runs early. The pilot runs go to their own output
  directory and are **not reused as production rows**: the production
  config may change as a result of the pilot.

### 7.2 What the pilot measures

For each run: every §6.3 field. For each (instance, arm):

- successes out of 3 (target reached with TTT ≤ 900 s)
- median TTT, with failures counted as > 900
- flips per call (median and p90)
- the fraction of calls stopped by `flip_limit` vs `time_limit`
- LS calls and generations
- `ls_time_share`

Paired comparison: the per-(instance, seed) difference in TTT, and the
success counts per arm, reported per group and in total.

### 7.3 Acceptance criteria (proposed, to be fixed before the pilot is submitted)

**A. Integrity (all required).** 60/60 shards; every `status == "ok"`; 0
watchdog fires; 0 `cost_mismatch`. On the new arm every run's
`wall_time_s ≤ 900 + 3 s`. The original arm reproduces its known ≤ ~19 s
overshoot.

**B. Mechanism.**

- B1: on the original arm, ≥ 90 % of calls on every pilot instance stop on
  `time_limit`. This confirms the hypothesis on calibration instances, not
  just uuf250.
- B2: on the new arm, ≥ 90 % of calls, excluding `deadline_clip`, stop on
  `flip_limit`, and the median flips per call equal 12,500, on every pilot
  instance.

**C. Performance (descriptive; a guard, not a significance test).** Ten
instances × 3 seeds cannot establish an improvement statistically, and both
arms may solve the easier pilot instances within seconds, so the pilot is
not built to show a performance gain. Proposed guard: the new arm's total
successes (out of 30) are ≥ the original arm's minus 2, and no instance goes
from 3/3 to 0/3. The actual per-group and total differences are reported
whatever they are.

### 7.4 Decisions pre-registered for after the pilot

- **A fails:** fix the cause, then re-run the affected tasks.
- **B1 fails** (time does not bind at 0.5 s on calib instances): the premise
  is wrong for this population, so stop and report before choosing an
  allowance.
- **B2 fails only on the high-m instances (#5, #8), as §4.4 predicts:** raise
  the allowance to about 1.2 × the observed p90 time to 12,500 flips on
  those instances (on present estimates about 3.5 s, i.e. `_ls3p5`), and
  bring that choice to the user. Production does not go ahead on a value
  under which the flip limit fails to bind on a known share of the
  population without that being written down.
- **C fails:** report it. Whether production still runs on the modified
  config is the user's decision.
- **All pass:** production on `memetic_deeppolish_ls2p5`, unchanged.

---

## 8. Production run and accounting

- **Population:** the 70 instances of §2 (16 / 46 / 8), from a population CSV
  written by the new builder with columns `instance`, `instance_sha256`,
  `batch`, `cell_id`, `family`, `k`, `n`, `alpha`, `m`, **`gen_seed`**,
  `oracle_cost` (c\*), `rc2_solve_s`, `rc2_tier` (original label),
  **`analysis_group`** (`lower_ext` / `tier2` / `upper_ext`) and
  `pysat_version`.
- **Manifest:** the existing 9-column TSV read by
  `tier2_memetic_array.sbatch`. `seed` is the **solver seed** (1–3), `tier`
  holds the original RC2 tier label, and `rc2_run` holds the batch name. The
  analysis group comes from the population CSV joined on `instance_sha256`,
  so the array script's format is unchanged.
- **Runs:** 70 × 3 = **210**, one config.

| quantity | value |
|---|---|
| solver-budget ceiling | 210 × 900 s = **52.5 CPU-h** |
| including 60 s grace | 210 × 960 s = 56.0 CPU-h |
| Slurm reservation ceiling | 210 × 20 min = 70 CPU-h (allocation, not use) |
| elapsed compute at `%30` | ⌈210/30⌉ = 7 waves × about 17 min ≈ 2.0 h worst case |
| queue delay | not estimated; recorded from `sacct` Submit/Start |

Realistic use will be lower because of target stops. The historical
deeppolish median TTT on uuf250 was 27.7 s, but that does not transfer to
these instances.

**The later LS-only baseline** (`local_multistart_deeppolish_ls2p5`, same 70
instances × 3 seeds) is not part of this batch. It would be another 210 runs
and 52.5 CPU-h at most, and it would give the evolutionary-contribution
comparison matched per-call allowances.

---

## 9. Files expected to change in the next stage, and cluster commands to prepare

### 9.1 Files

| file | change |
|---|---|
| `cluster_staging_maxsat/configs/tier2/memetic_deeppolish_ls2p5.yaml` | **new** config (§6.1) |
| `cluster_staging_maxsat/src/evo/memetic.py` | opt-in `ea.deadline_mode: clip`; per-call stats; `target_gen`/`target_child_index` (already-diverged file; staging only, per DIVERGENCE.md) |
| `cluster_staging_maxsat/src/evo/operators.py` **and** `src/evo/operators.py` | optional `stats_out` kwarg on `short_polish` (identical-set file, so both trees) |
| `cluster_staging_maxsat/src/cli/run_memetic_shard.py` | schema v3: `ls_*` fields, `code_fingerprint` |
| `cluster_staging_maxsat/DIVERGENCE.md` | record the above |
| `cluster_staging_maxsat/tests/test_memetic_ls_stats.py` | **new**: original config reproduces the pre-change trajectory (flip-limited, seeded); clipped allowance never exceeds remaining time; `sum(ls_stop_counts) == ls_calls == children`; stop-reason classification |
| `src/bench/make_calib_memetic_manifest.py` | **new** (named in goals §6 M2): pools batches, dedups on sha, applies the 30–900 grouped rule, writes the population CSV, the pilot and production TSVs and their `.sha256` |
| `cluster_staging_maxsat/scripts/submit_calib_memetic.sh` | **new** wrapper modelled on `submit_rc2_profile.sh`: counts the manifest, checks instance sha, `THROTTLE` (default 30), `DRY_RUN=1`, and `RESUME=1` (submit only the ids whose shard is missing or `status != "ok"`), exporting `MAXSAT_GIT_SHA` |
| `cluster_staging_maxsat/scripts/tier2_memetic_array.sbatch` | unchanged (already takes `MANIFEST`, `OUTDIR`, `STOP_AT_ORACLE`, `GRACE`) |
| aggregation script (e.g. `src/bench/combine_calib_memetic.py`) | after the pilot returns |
| `docs/CORPUS_CALIBRATION_LOG.md` | Checkpoint 5 |

Tests run from inside `cluster_staging_maxsat/` (`python -m pytest tests -q`),
plus `python -m pytest instancegen -q` from the repo root.

### 9.2 Cluster commands (prepared for later; not run)

No `sbatch` or ssh alias exists on this workstation. These run on the login
node. The array script reads its manifest line with `sed -n "${SLURM_ARRAY_TASK_ID}p"`,
so array ids are **1-based**. The manifest paths below are the proposed names.

```bash
# workstation -> cluster (staging tree, including data/generated/calib_{a,b}/)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# login node — pilot (60 tasks)
cd ~/maxsat-lab/scripts && mkdir -p logs
( cd .. && sha256sum -c scripts/manifest_m2_pilot.sha256 )
DRY_RUN=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks \
    bash submit_calib_memetic.sh
MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks \
    bash submit_calib_memetic.sh
#   equivalent raw form:
#   sbatch --array=1-60%30 \
#     --export=ALL,MANIFEST=scripts/manifest_m2_pilot.tsv,OUTDIR=results/m2_pilot/tasks,STOP_AT_ORACLE=1,MAXSAT_GIT_SHA=<sha> \
#     tier2_memetic_array.sbatch
RESUME=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_calib_memetic.sh

# cluster -> workstation
rsync -av <user>@<cluster>:~/maxsat-lab/results/m2_pilot/ cluster_staging_maxsat/results/m2_pilot/

# production (210 tasks), only after the pilot is read out and approved
MANIFEST=manifest_m2_deeppolish_ls2p5.tsv OUTDIR=results/m2_deeppolish_ls2p5/tasks \
    bash submit_calib_memetic.sh
```

---

## 10. Logging, resume and environment provenance

- **One shard per task**, `OUTDIR/<job_id>.jsonl`, written once at the end.
  The shard holds the resolved config and `config_hash`, the instance sha,
  python, host, the Slurm ids, `started_at`/`finished_at`, `cpu_time_s`, and
  (new) the `ls_*` fields and `code_fingerprint`. Slurm stdout and stderr go
  to `scripts/logs/t2-memetic-%A_%a.{out,err}`.
- **Resume.** Today `tier2_memetic_array.sbatch` has **no skip logic**: a
  re-submitted task overwrites its shard. The new wrapper's `RESUME=1`
  submits only tasks whose shard is missing or failed, the same contract as
  the RC2 array. A task killed by Slurm leaves no shard, and the missing file
  is the signal. Failed rows are re-run, never counted as censored
  (goals §4.4).
- **Censoring classes for memetic rows** (goals §4.2/§4.4):
  - completed: `ok` + `target` with TTT ≤ 900
  - censored: `ok` + `time_cap`
  - failed: `status != ok`, or `max_gens`
- **Environment.** The existing cluster env is kept: `module load anaconda;
  source activate maxsat`, **python 3.11.15** (all 130 historical deeppolish
  rows and all 290 RC2 rows), PySAT **1.9.dev3** (used only by the RC2
  oracle, not by the memetic arm), 1 CPU and 8 GB on partition `main`. The
  workstation runs python 3.12.3 and PySAT 1.9.dev15, and is used only for
  smoke checks and the estimates in §4.4. **No blocking defect was found in
  the environment.** Gaps to close in implementation:
  - PyYAML's version is not recorded.
  - `git_sha` is null on the cluster; the code fingerprint and the exported
    `MAXSAT_GIT_SHA` close this.
  - The implicit LS defaults (`noise` 0.10 etc.) are not in `config_hash`;
    the code fingerprint covers them.
- **Timing caveats.** Timing is wall-clock on a shared cluster across many
  hosts (the historical deeppolish runs used 19). `cpu_time_s` is recorded
  so an overloaded node can be detected. The RC2 `solve_s` values that
  define the groups are single runs with the same cross-host caveat
  (read-out §1).
- **Latent defect, not blocking.** `memetic.py:142` passes
  `ind.hard_satisfied`, where `ind` is left over from the initial-evaluation
  loop, to `mutate1`. With no hard clauses (every instance here),
  `mutate1`'s hard-repair path has nothing to do, so this has no effect on
  this experiment. It is recorded and left untouched.

---

## 11. Calibration results vs. the later fresh-seed evaluation corpus

- Every instance here is a **calibration instance** (calib_a / calib_b,
  generator seeds 1–10), selected by RC2's behaviour on those same
  instances. The M2 results describe **this selected population under this
  stack** (RC2 g3, cap 900; memetic under the configs above). They are not
  about random Max-k-SAT.
- Goals §5.4 still stands until the log changes it: the reported corpus is
  **regenerated at fresh generator seeds 1001–1020** (M4), and calibration
  rows do not enter a reported ρ. M2 is therefore a calibration read-out. It
  tells M3 and M4 which cells, rules and solver settings to freeze, but it
  is not the evaluation. A per-instance "memetic success" measured here must
  not be carried over to a fresh-seed instance from the same cell.
- Keep the two groupings apart in every table. `analysis_group` is a label
  for reporting. It is not a new tier threshold, and nothing here edits
  `T1_MAX_S`/`T2A_MAX_S`/`T2B_MAX_S`.

---

## 12. Open decisions for the user before implementation

1. **Approve the pilot as specified** (10 instances, 2 arms, 3 seeds, 60 runs,
   ≤ 15 CPU-h solver budget), or change the instance list.
2. **Optional third pilot arm:** add `_ls3p5` on the two high-m instances (#5,
   #8) now (+6 runs, ≤ 1.5 CPU-h) rather than after a failed B2. This saves
   one round-trip if the §4.4 estimate holds.
3. **Approve the opt-in deadline clipping** (§6.2). Without it, the longer
   allowance produces watchdog failures on every run that does not reach the
   target.
4. **Approve the acceptance criteria** in §7.3, especially guard C.

## 13. Next stage (after approval)

Implement §9.1. Run the tests and a local smoke run (`LOCAL`-style, 2
instances at a short budget, both arms, checking the v3 fields and that the
new arm ends within the deadline). Generate the population CSV and the pilot
manifest and check they give 16 / 46 / 8 = 70. Record the rsync and sbatch
commands in log Checkpoint 5. **Stop there for the pilot submission.**
