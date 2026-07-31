# RC2 Profiling — Status Report

Read-only audit of the RC2 hardness-profiling runs committed under
`results/hardness/`. Nothing was solved, submitted or modified to produce this;
every number below was computed from the committed artifacts with the commands
shown. Written 2026-07-31 against `HEAD = 63f3ae5` (working tree clean).

**Scope note.** The question asks about "tier1 / tier2 / tier3" SLURM
submissions. In this repo the tiers (`T1 / T2a / T2b / T3`) are an **output** of
profiling, not an input to it — no job was ever submitted "for tier2". The four
committed runs are per-*corpus*, and each assigns a tier to every instance it
profiled. The report is organised per corpus-run accordingly.

---

## 0. TL;DR

| run dir under `results/hardness/` | corpus | n | cap_s | grace | T1 | T2a | T2b | T3 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `mse23_full/`     | MSE unweighted-small | 75 | 600  | 60  | 0  | 1  | 0 | 74 |
| `mse_cap1800/`    | same 75 instances    | 75 | 1800 | 120 | 0  | 1  | 0 | 74 |
| `uuf250_1000c/`   | SATLIB uuf250        | 35 | 900  | 60  | 8  | 15 | 3 | 9  |
| `uuf_diff_unsat/` | SATLIB uuf50–250     | 50 | 600  | 60  | 39 | 6  | 2 | 3  |

235 records total, 160 distinct instances (the 75 MSE instances were profiled
twice, at two caps). No shard is missing, no record is duplicated, and every
tier label is consistent with the rule in `assign_tier()`.

The headline result: **RC2 solves 76 of 235 records to optimality (32%)**, but
that is entirely carried by the random-3-SAT corpora. On the MSE
unweighted-small set RC2 solves **1/75 at a 600 s cap and 2/75 at a 1800 s cap**
— tripling the budget bought exactly one more instance.

---

## 1. What was done

### 1.1 The RC2 invocation

Two layers, both committed and byte-identical between `src/cli/` and
`cluster_staging/src/cli/`:

```bash
$ diff src/cli/profile_hardness.py cluster_staging/src/cli/profile_hardness.py && echo IDENTICAL
$ diff src/cli/solve_rc2_anytime.py cluster_staging/src/cli/solve_rc2_anytime.py && echo IDENTICAL
```

**Outer driver** — `src/cli/profile_hardness.py`. For each instance it spawns
`src.cli.solve_rc2_anytime` as a subprocess and enforces
`subprocess.run(timeout=cap+grace)`.

**Inner solver** — `src/cli/solve_rc2_anytime.py:solve_rc2_with_timeout`.

The actual RC2 construction is a single line
(`src/cli/solve_rc2_anytime.py:181`):

```python
rc2 = RC2(wcnf, solver=solver)     # solver defaults to "g3"
```

Therefore:

| knob | value | how established |
|---|---|---|
| RC2 variant | **plain `RC2`** — `RC2Stratified` is never imported or referenced in any code | `grep -rn "RC2Stratified" --include="*.py" .` → 0 hits. (It is mentioned only in the forward-looking `docs/INSTANCEGEN_PLAN.md`, which independently states at line 504 that "the existing tier tables were produced with **plain `RC2`**".) |
| SAT backend | **`g3` = Glucose 3** | `solve_rc2_with_timeout(..., solver="g3")` default; `profile_hardness.py` never passes `--solver`, so the default stands |
| `adapt` | **False** (PySAT default) | not passed; `inspect.signature(RC2.__init__)` → `adapt=False` |
| `exhaust` | **False** (default) | as above |
| `minz` | **False** (default) | as above |
| `incr` | **False** (default) | as above |
| `trim` | **0** (default) | as above |
| `process` | **0** (default, no preprocessing) | as above |
| timeout | `signal.setitimer(ITIMER_REAL, cap)` in the child + `subprocess.run(timeout=cap+grace)` in the parent | `profile_hardness.py:113-127` |
| memory cap | **unknown** — no `ulimit`, no `RLIMIT_AS`, and no sbatch for these runs exists in the repo | |

`load_as_wcnf()` (`src/cli/run_opt_rc2.py`) decides how the file is fed to RC2:
`p wcnf` → `WCNF(from_file=...)`; `p cnf` → `cnf.weighted()`, i.e. **every clause
becomes a soft clause of weight 1 and there are no hard clauses**. That is why
the SATLIB `.cnf` runs report `n_hard = 0` throughout, and why their "optimal
cost" is a count of unsatisfied clauses.

### 1.2 Exact CLI per run

No launcher for these four runs is committed, so the exact argv is
**reconstructed from the data**, not read from a script. Each field below is
recoverable from the records:

| run | `--cap` (from `profile.cap_s`) | `--grace` (from the `cap+Ns` error string) | `--bestknown` | `--in-process` |
|---|---|---|---|---|
| `mse23_full`     | 600.0  | 60.0  | yes — `ratio`/`lb_ratio` are populated | no (subprocess statuses present) |
| `mse_cap1800`    | 1800.0 | 120.0 | yes | no |
| `uuf250_1000c`   | 900.0  | 60.0  | **no** — `ratio` and `lb_ratio` are null on all 35 records | no |
| `uuf_diff_unsat` | 600.0  | 60.0  | **no** — null on all 50 | no |

So the reconstructed command for e.g. `mse23_full`, array task `$SLURM_ARRAY_TASK_ID`:

```bash
python -m src.cli.profile_hardness \
    --instances <the one instance for this task> \
    --cap 600 --grace 60 \
    --bestknown data/raw/mse_2024/bestknown_mse23.csv \
    --out results/hardness/mse23_full/tasks/mse23_full_arr_task_${SLURM_ARRAY_TASK_ID}.jsonl
```

The one-instance-per-task split is confirmed: every shard holds exactly one
JSON object, and for three of the four runs the task index maps onto the
sorted-by-path instance list exactly (see §4.5).

```bash
# grace values, per run
python3 -c "
import json,glob,re,collections
for d in sorted(glob.glob('results/hardness/*/')):
    g=collections.Counter()
    for l in open(d+'all_results.jsonl'):
        m=re.search(r'cap\+([0-9.]+)s', json.loads(l)['profile']['error'] or '')
        if m: g[m.group(1)]+=1
    print(d, dict(g))"
```

### 1.3 SLURM

**The SLURM array driver for all four runs is not in the repository.** This is
the single biggest provenance gap and `results/hardness/mse23_full/PROVENANCE.txt`
already flags it ("PROVENANCE GAP: … currently unversioned").

```bash
$ find . -path ./.git -prune -o \( -name "*.sbatch" -o -name "*.slurm" \) -print
```

returns 21 sbatch files; **all** of them belong to the GSM8K/LoRA→Ollama
pipeline except one:

`cluster_staging/scripts/smoke_mse23.sbatch` — and it does **not** correspond to
any committed result. It is a non-array smoke test:

- `--partition=main`, `--time=00:10:00`, `--mem=4G`, `--cpus-per-task=1`
- `--output=logs/mse23-smoke-%j.out`, `--error=logs/mse23-smoke-%j.err`
- `module load anaconda; source activate maxsat; cd ~/maxsat-lab`
- 5 hard-coded instances, `--cap 30 --grace 15`, out to
  `results/profile/mse23_smoke_cluster.jsonl`

Consequently:

- **array sizes** — inferable from the shards only: `mse23_full` and
  `mse_cap1800` are `[1-75]`, `uuf_diff_unsat` is `[1-50]`, `uuf250_1000c` is
  `[66-100]` (35 tasks; see §4.4). Whether these were literally `--array=` ranges
  is **unknown**.
- **resources per task** (cpus, `--mem`, `--time`, partition, account, job IDs,
  node/CPU model): **unknown**. The 4 GB / 1 CPU / 10 min of the smoke script
  cannot be assumed — a 1800 s cap alone exceeds its wall limit.
- **PySAT version and conda env at run time**: **unknown**. (Locally, `pysat
  1.9.dev2` is installed; that is this workstation, not the cluster.)

### 1.4 How a tier is assigned

`src/cli/profile_hardness.py:assign_tier()` — purely a function of
`profile.completed` and `profile.solve_s`. Thresholds are module constants
(`T1_MAX_S=60.0`, `T2A_MAX_S=300.0`, `T2B_MAX_S=600.0`):

```
not completed                      -> T3   (reason = the error/status string)
completed and solve_s <=  60       -> T1
completed and  60 < solve_s <= 300 -> T2a
completed and 300 < solve_s <= 600 -> T2b
completed and solve_s  >  600      -> T3   (reason "solve_s>600.0 (cap misconfigured?)")
```

`completed` is `status == "optimal"` and nothing else.

Two consequences worth stating plainly:

1. **The tier boundaries are hard-coded, not derived from `--cap`.** A run with
   `--cap 900` or `--cap 1800` still uses 60/300/600 s cutoffs. That is exactly
   how `mse_cap1800` produced a record that is `completed=true` **and** `T3` (§4.6).
2. Tier is not comparable across runs with different caps. `T3` at cap 600 and
   `T3` at cap 1800 are different claims.

### 1.5 Instance set

| run | path recorded | files | families |
|---|---|---:|---|
| `mse23_full`, `mse_cap1800` | `data/raw/mse_2024/mse23-uw-small/*.wcnf` | 75 | 18 (see §3.1) |
| `uuf250_1000c` | `data/unsat250_1000c/*.cnf` | 35 | 1 (`uuf250`) |
| `uuf_diff_unsat` | `data/unsat_uuf_diff/*.cnf` | 50 | 5 (`uuf50/100/150/200/250`, 10 each) |

- The 75 MSE `.wcnf` files **are** in the repo at the recorded path (all 75
  resolve, and all 75 file sizes match `size_mb` to the recorded 4 decimals).
  They are in the **new (MSE 2022+) WCNF format** — no `p` line, hard clauses
  prefixed `h`.
- `data/unsat250_1000c/` and `data/unsat_uuf_diff/` **do not exist in the repo**
  — they were cluster-side staging copies. All 85 basenames do resolve uniquely
  against the committed SATLIB corpus under `data/unsat/`, but that is a
  basename match, not a content match (see §4.2).
- The corpus name `uuf250_1000c` says "1000 clauses"; the matched SATLIB files
  are `uuf250-1065` (1065 clauses). **Unknown** which is right for the files
  actually profiled.
- `PROVENANCE.txt` itself flags that "mse23" vs the `mse_2024` parent directory
  is unresolved — whether this is the MSE 2023 or 2024 unweighted-small set is
  **unknown**.

### 1.6 Git provenance

```bash
$ git log --format="%h %ad %s" --date=iso -- results/hardness/
b31f7d1 2026-06-22 17:31:57 +0300  Add tier analysis script and hardness profile results
700c9cf 2026-06-21 16:47:45 +0300  Add MSE23 full RC2 hardness profile shards and tree snapshot

$ git log --format="%h %ad %s" --date=iso -- src/cli/profile_hardness.py src/cli/solve_rc2_anytime.py
b31f7d1 2026-06-22  Add tier analysis script and hardness profile results
375ae3d 2026-06-21  Commit cluster_staging profiler sources, keep data mirror ignored
c3f8eca 2026-05-20  Harden RC2 profiling with subprocess timeouts and SIGKILL-safe lower bound
8b1adc6 2026-05-20  Switch profile_hardness to RC2 exact baseline with time-based tiers
d5a73bb 2026-05-20  Add instance hardness profiler and stratification plan
aad720e 2026-05-20  Add anytime RC2 MaxSAT solver CLI with wall-clock budget
```

- **Results were committed in** `700c9cf` (mse23_full, 2026-06-21) and `b31f7d1`
  (the other three runs + `analyze_tiers.py`, 2026-06-22).
- **The profiler code the runs used**: the last change to either profiler file
  before the runs is `c3f8eca` (2026-05-20). Shard mtimes are 2026-06-21 16:30
  (mse23_full), 2026-06-21 18:15 (uuf_diff_unsat), 2026-06-22 06:57
  (uuf250_1000c), 2026-06-22 16:57 (mse_cap1800) — all after `c3f8eca` and
  consistent with it. But the runs happened on the cluster from a working copy,
  so the exact commit checked out at run time is **unknown** (that is
  `PROVENANCE.txt` §7 "Repo commit at run: <FILL IN>", still unfilled).
- **Working tree**: clean. `git status --porcelain` is empty, and
  `git status --porcelain --untracked-files=all results data` is empty — no
  result or instance file has been touched since it was committed.

---

## 2. Output format

### 2.1 Every artifact

```bash
$ find results/hardness results/profile -type f -printf "%s\t%p\n" | sort -k2
$ du -sb results/hardness/*/ results/profile/
```

| path | type | size |
|---|---|---:|
| `results/hardness/mse23_full/tasks/mse23_full_arr_task_{1..75}.jsonl` | JSONL, 1 record each | 34,958 B total |
| `results/hardness/mse23_full/all_results.jsonl` | JSONL, 75 records | 34,958 B |
| `results/hardness/mse23_full/all_results.csv` | CSV, 75 rows + header | 27,328 B |
| `results/hardness/mse23_full/tier_summary.csv` | CSV, 2 rows | 213 B |
| `results/hardness/mse23_full/bench_summary.csv` | CSV, 1 row | 46 B |
| `results/hardness/mse23_full/PROVENANCE.txt` | text | 7,612 B |
| **`mse23_full/` total** | | **105,115 B** |
| `results/hardness/mse_cap1800/tasks/mse23_full_arr_task_{1..75}.jsonl` | JSONL | 35,687 B total |
| `results/hardness/mse_cap1800/all_results.jsonl` | JSONL, 75 | 35,687 B |
| `results/hardness/mse_cap1800/all_results.csv` | CSV | 28,076 B |
| `results/hardness/mse_cap1800/tier_summary.csv` | CSV | 217 B |
| `results/hardness/mse_cap1800/bench_summary.csv` | CSV | 46 B |
| **`mse_cap1800/` total** (no PROVENANCE.txt) | | **99,713 B** |
| `results/hardness/uuf250_1000c/tasks/uuf250_arr_task_{66..100}.jsonl` | JSONL | 11,966 B total |
| `results/hardness/uuf250_1000c/all_results.jsonl` | JSONL, 35 | 11,966 B |
| `results/hardness/uuf250_1000c/all_results.csv` | CSV | 7,007 B |
| `results/hardness/uuf250_1000c/tier_summary.csv` | CSV | 299 B |
| `results/hardness/uuf250_1000c/bench_summary.csv` | CSV | 57 B |
| **`uuf250_1000c/` total** | | **31,295 B** |
| `results/hardness/uuf_diff_unsat/tasks/uuf_diff_arr_task_{1..50}.jsonl` | JSONL | 15,797 B total |
| `results/hardness/uuf_diff_unsat/all_results.jsonl` | JSONL, 50 | 15,797 B |
| `results/hardness/uuf_diff_unsat/all_results.csv` | CSV | 8,687 B |
| `results/hardness/uuf_diff_unsat/tier_summary.csv` | CSV | 298 B |
| `results/hardness/uuf_diff_unsat/bench_summary.csv` | CSV | 57 B |
| **`uuf_diff_unsat/` total** | | **40,636 B** |
| `results/profile/*.jsonl` (9 files) | JSONL, smoke/toy only — **not** part of these runs | 5,759 B |

Total for the four runs: **276,759 B (~270 KB)**. The shards are the source of
truth; `all_results.*`, `tier_summary.csv`, `bench_summary.csv` are rebuildable
by `python -m src.bench.analyze_tiers --in-dir <run>/tasks --out-dir <run>`.

### 2.2 Full schema of `all_results.jsonl`

Written by `profile_hardness.py`. Presence/nullability measured over all 235
records:

```bash
python3 -c "
import json,glob,collections
k=collections.Counter(); n=collections.Counter(); t=collections.defaultdict(set)
for d in sorted(glob.glob('results/hardness/*/')):
    for l in open(d+'all_results.jsonl'):
        r=json.loads(l)
        for kk,v in list(r.items())+[('profile.'+a,b) for a,b in r['profile'].items()]:
            if kk=='profile': continue
            k[kk]+=1
            (n.__setitem__(kk,n[kk]+1) if v is None else t[kk].add(type(v).__name__))
for kk in k: print(f'{kk:<26} present={k[kk]} null={n[kk]} types={sorted(t[kk])}')"
```

| key | type | units / meaning | always present? | null count / 235 |
|---|---|---|---|---:|
| `instance` | str | path to the instance **as seen by the profiler process** (relative to the cluster CWD) | yes, never null | 0 |
| `size_mb` | float | file size in **megabytes** (`os.path.getsize/1e6`, rounded to 4 dp) | yes, never null | 0 |
| `profile.cap_s` | float | **seconds**; the `--cap` given to RC2 | yes, never null | 0 |
| `profile.solver` | str | always the literal `"rc2"`. **Does not record the SAT backend** (`g3`) | yes, never null | 0 |
| `profile.status` | str | one of `optimal` \| `timeout` \| `subprocess_killed`; the code can also emit `unsat` and `error`, neither observed | yes, never null | 0 |
| `profile.solve_s` | float | **seconds**, wall clock. For `optimal`/`timeout` it is the child's `time.time()` delta **including WCNF parse time**, which is why graceful timeouts read slightly above `cap` (611–636 s at cap 600). For `subprocess_killed` it is the parent's `time.monotonic()` delta ≈ `cap+grace` | yes, never null | 0 |
| `profile.final_cost` | int | **cost = total weight of UNSATISFIED soft clauses** (RC2's `cost`), i.e. lower is better. **Not** satisfied weight. Populated only when `status=="optimal"` | key always present; **null unless solved** | 159 |
| `profile.cost_lower_bound` | int | same units (unsat weight). A **lower bound** on the optimum: the sum of weights of the cores RC2 had extracted. Equals `final_cost` when solved; recovered from the progress file when SIGKILLed; null if RC2 never extracted a single core | key always present; nullable | 17 |
| `profile.completed` | bool | `status == "optimal"`. The tier driver | yes, never null | 0 |
| `profile.error` | str | free text: `"timeout"`, `"subprocess_killed_at_cap+60.0s[; recovered_lb_from_progress_file]"`, or null when clean | key always present; **null on success** | 76 |
| `ratio` | float | **dimensionless** — `final_cost / best_known`. Validation ratio; ≈1.0 expected. Null unless *both* `--bestknown` was given *and* RC2 completed *and* `best_cost > 0` | key always present; almost always null | **232** |
| `lb_ratio` | float | **dimensionless** — `cost_lower_bound / best_known` ∈ [0,1]. Progress ratio; the intended stratifier inside T3. Null without `--bestknown`, or when `best_cost <= 0` (the MSE `-1` = "unknown" convention), or when no LB was captured | key always present; nullable | 106 |
| `tier` | str | `T1` \| `T2a` \| `T2b` \| `T3` | yes, never null | 0 |
| `tier_reason` | str | for T1/T2a/T2b the threshold expression; for T3 the error/status string | yes, never null | 0 |

Per-run nullability (this is where the asymmetry lives):

| run | `ratio` null | `lb_ratio` null | `final_cost` null | `cost_lower_bound` null |
|---|---:|---:|---:|---:|
| `mse23_full`     | 74/75 | 11/75 | 74/75 | 9/75 |
| `mse_cap1800`    | 73/75 | 10/75 | 73/75 | 8/75 |
| `uuf250_1000c`   | **35/35** | **35/35** | 9/35 | 0/35 |
| `uuf_diff_unsat` | **50/50** | **50/50** | 3/50 | 0/50 |

**`ratio` and `lb_ratio` are unusable on the two SATLIB runs** — they were run
without `--bestknown`, so both fields are structurally null, not "missing data".

**`all_results.csv`** is `analyze_tiers.py`'s flattened view: same 15 fields
(dots kept in the column names) plus four **derived** columns —
`family` (the filename stem up to the first `-`), `bench_dir` (parent directory
name), `stem`, and `over_cap` (`solve_s >= cap_s`) — plus `_source_file` (the
shard filename, which is the only link back to the array task index). Column
order: `instance, family, bench_dir, size_mb, tier, profile.completed,
profile.status, profile.solve_s, profile.cap_s, over_cap, profile.final_cost,
profile.cost_lower_bound, ratio, lb_ratio, profile.solver, profile.error,
tier_reason, _source_file, stem`.

Note the CSV round-trips ints as floats (`final_cost` → `1.0`) and nulls as
empty strings — the JSONL is the better source.

### 2.3 Two verbatim records

**Solved** — `results/hardness/uuf_diff_unsat/all_results.jsonl`, also
`tasks/uuf_diff_arr_task_1.jsonl`:

```json
{"instance": "data/unsat_uuf_diff/uuf100-01.cnf", "size_mb": 0.0054, "profile": {"cap_s": 600.0, "solver": "rc2", "status": "optimal", "solve_s": 0.073, "final_cost": 1, "cost_lower_bound": 1, "completed": true, "error": null}, "ratio": null, "lb_ratio": null, "tier": "T1", "tier_reason": "solve_s<=60.0"}
```

**Not solved** — `results/hardness/mse23_full/all_results.jsonl`, also
`tasks/mse23_full_arr_task_1.jsonl`:

```json
{"instance": "data/raw/mse_2024/mse23-uw-small/MaxSATQueriesinInterpretableClassifiers-wdbc_train_9_CNF_5_1.wcnf", "size_mb": 0.7642, "profile": {"cap_s": 600.0, "solver": "rc2", "status": "subprocess_killed", "solve_s": 660.105, "final_cost": null, "cost_lower_bound": 15, "completed": false, "error": "subprocess_killed_at_cap+60.0s; recovered_lb_from_progress_file"}, "ratio": null, "lb_ratio": 0.7143, "tier": "T3", "tier_reason": "subprocess_killed_at_cap+60.0s; recovered_lb_from_progress_file"}
```

(The second not-solved flavour, a graceful SIGALRM rather than a SIGKILL, looks
like this — note `solve_s` just *above* `cap_s`:)

```json
{"instance": "data/raw/mse_2024/mse23-uw-small/inconsistency-measurement-im-forgetting-B-3-stb_428_430.tgf.pl.wcnf", "size_mb": 0.3222, "profile": {"cap_s": 600.0, "solver": "rc2", "status": "timeout", "solve_s": 636.451, "final_cost": null, "cost_lower_bound": 44, "completed": false, "error": "timeout"}, "ratio": null, "lb_ratio": 0.8627, "tier": "T3", "tier_reason": "timeout"}
```

### 2.4 Per-job stdout/stderr logs

**There are none for these runs.**

```bash
$ find . -path ./.git -prune -o \( -name "*.out" -o -name "*.err" \) -print
```

returns 24 files, all from the GSM8K / LoRA→Ollama pipeline
(`gsm8k_lora_v2_consolidated/`, `cluster_staging/pipeline final/`). No
`mse23-*.out`, no array logs, no `logs/` directory under `results/`.

So the following are **unknown** and unrecoverable from the repo:

- SLURM exit codes / `sacct` state (`COMPLETED` vs `TIMEOUT` vs `OUT_OF_MEMORY`)
- `MaxRSS` per task, hence any OOM evidence
- job IDs, node names, actual wall time
- RC2's own stderr (the `_read_lower_bound` "no running lower-bound attribute"
  warning would have gone there)
- core counts — note these were **never** captured anyway: the profiler records
  only the aggregated `rc2.cost`, not the number of cores extracted

What *would* have been in stdout is not lost, though: `profile_hardness.py`
prints one summary line per instance, but every field on it
(`status/solve_s/final_cost/lb/tier/ratio/lb_ratio/error`) is already in the
JSONL. The **only** thing the logs would add beyond the structured output is
RC2's lower bound *trajectory* over time — and that was written to a temp
progress file that is `os.unlink`ed in the `finally` block
(`profile_hardness.py:167-171`), so only the final value survives.

### 2.5 Reliable join key

```bash
python3 -c "
import json,glob,collections
from pathlib import Path
for d in sorted(glob.glob('results/hardness/*/')):
    r=[json.loads(l)['instance'] for l in open(d+'all_results.jsonl')]
    print(d,'n=%d'%len(r),'paths=%d'%len(set(r)),
          'basenames=%d'%len(set(Path(p).name for p in r)),
          'stems=%d'%len(set(Path(p).stem for p in r)))"
```

| run | n | unique `instance` | unique basename | unique stem |
|---|---:|---:|---:|---:|
| `mse23_full`     | 75 | 75 | 75 | 75 |
| `mse_cap1800`    | 75 | 75 | 75 | 75 |
| `uuf250_1000c`   | 35 | 35 | 35 | 35 |
| `uuf_diff_unsat` | 50 | 50 | 50 | 50 |

- **Within a run, all three keys are unique.** Any of them works.
- **Across runs they are not.** 235 records span 160 distinct basenames; 75
  basenames appear twice (the MSE set profiled at both caps). The correct
  global key is therefore **`(run_dir, instance)`** — or equivalently
  `(cap_s, instance)`, since the two MSE runs differ only in cap.
- **There is no `sha256` (or any checksum) in the records.** Content-addressed
  joining is not possible from the artifacts.
- **`instance` is not a usable filesystem path for the two SATLIB runs** — it
  points at `data/unsat250_1000c/` and `data/unsat_uuf_diff/`, which do not
  exist here. To reach a real file you must fall back to basename lookup under
  `data/unsat/**`, where all 85 basenames happen to be unique. That works but
  is a heuristic (§4.2).
- To join a record back to its **array task**, use the CSV's `_source_file`
  column (or the shard filename). It is 1:1 with `instance` in every run.
- Recommendation: add `sha256` (and the resolved absolute path) to the record
  schema before the next profiling pass.

---

## 3. Statistics

All numbers below from `results/hardness/*/all_results.jsonl` via the scripts
reproduced at the end of each subsection.

### 3.1 Instance counts

**Total: 235 records over 160 distinct instances.**

Per tier:

| run | T1 | T2a | T2b | T3 | total |
|---|---:|---:|---:|---:|---:|
| `mse23_full` (cap 600)  | 0 | 1 | 0 | 74 | 75 |
| `mse_cap1800` (cap 1800)| 0 | 1 | 0 | 74 | 75 |
| `uuf250_1000c` (cap 900)| 8 | 15 | 3 | 9 | 35 |
| `uuf_diff_unsat` (cap 600)| 39 | 6 | 2 | 3 | 50 |
| **all records** | 47 | 23 | 5 | 160 | 235 |

Per family (`family` = stem up to the first `-`):

*MSE unweighted-small — 75 instances, 18 families (identical in both MSE runs):*

| family | n | | family | n |
|---|---:|---|---|---:|
| judgment | 20 | | pseudoBoolean | 2 |
| inconsistency | 19 | | MaxSATQueriesinInterpretableClassifiers | 1 |
| ramsey | 6 | | bcp | 1 |
| optimizing | 5 | | decision | 1 |
| reversi | 4 | | extension | 1 |
| setcover | 4 | | logic | 1 |
| gen | 3 | | mbd | 1 |
| optic | 3 | | min | 1 |
| | | | scheduling | 1 |
| | | | xai | 1 |

*`uuf250_1000c`:* `uuf250` × 35.
*`uuf_diff_unsat`:* `uuf50`, `uuf100`, `uuf150`, `uuf200`, `uuf250` — **10 each**.

### 3.2 Status breakdown

Only three statuses ever occur. `profile_hardness.py` can also emit `error` and
`unsat`; **neither appears in any of the 235 records**.

| run | `optimal` | `timeout` (graceful SIGALRM) | `subprocess_killed` (SIGKILL at cap+grace) | `error` | missing |
|---|---:|---:|---:|---:|---:|
| `mse23_full`     | 1  | 7 | 67 | 0 | 0 |
| `mse_cap1800`    | 2  | 3 | 70 | 0 | 0 |
| `uuf250_1000c`   | 26 | 1 | 8  | 0 | 0 |
| `uuf_diff_unsat` | 47 | 0 | 3  | 0 | 0 |
| **total**        | **76** | **11** | **148** | **0** | **0** |

Status × tier (all four runs): every `optimal` record is T1/T2a/T2b **except
one** (a `mse_cap1800` record that is `optimal` *and* T3 — see §4.6); every
`timeout` and `subprocess_killed` record is T3.

**Solved-to-optimality / timeout / OOM / crashed / missing:**

- **solved to optimality: 76 / 235 (32.3%)**
- **timeout: 159 / 235 (67.7%)** — the 11 graceful + 148 SIGKILLed. Both are
  budget exhaustion; the split reflects only whether Python's SIGALRM was
  swallowed inside Glucose's C code.
- **OOM: unknown, but no positive evidence, and structurally unlikely.**
  Distinguishing OOM from timeout requires SLURM exit codes, and there are no
  logs (§2.4). What the data does say: *every* non-completed record has
  `solve_s` within ~1 s of its `cap+grace` (or, for graceful timeouts, just
  above `cap`); **not a single non-completed record finished early**:

  | run | graceful `timeout` solve_s | `subprocess_killed` solve_s | any non-completed below `cap`? |
  |---|---|---|---|
  | `mse23_full` (600+60)     | 611.471 – 636.451   | 660.011 – 660.115   | none |
  | `mse_cap1800` (1800+120)  | 1809.615 – 1895.214 | 1920.021 – 1920.121 | none |
  | `uuf250_1000c` (900+60)   | 926.799             | 960.035 – 960.114   | none |
  | `uuf_diff_unsat` (600+60) | —                   | 660.027 – 660.106   | none |

  An OOM-killed *child* would surface as `status="error"` with
  `"empty_subprocess_output (rc=-9)"` — zero such records. An OOM-killed *SLURM
  task* would leave a missing or empty shard — zero of those too (§4.1).
- **crashed: 0** — no `error` status, no malformed JSON, no empty shard.
- **missing: 0** — see §4.1.

### 3.3 Solve time

`solve_s` in seconds. min / median / p90 / max, **over all records in the tier**
(so T3 values are just the cap, and are reported for completeness only).

| run | tier | n | min | median | p90 | max |
|---|---|---:|---:|---:|---:|---:|
| `mse23_full` | T2a | 1 | 71.064 | 71.064 | 71.064 | 71.064 |
| | T3 | 74 | 611.471 | 660.105 | 660.108 | 660.115 |
| `mse_cap1800` | T2a | 1 | 65.029 | 65.029 | 65.029 | 65.029 |
| | T3 | 74 | 1313.759 | 1920.108 | 1920.115 | 1920.121 |
| `uuf250_1000c` | T1 | 8 | 14.580 | 34.996 | 46.660 | 48.556 |
| | T2a | 15 | 63.100 | 128.158 | 216.445 | 269.613 |
| | T2b | 3 | 311.374 | 436.684 | 484.002 | 495.832 |
| | T3 | 9 | 926.799 | 960.106 | 960.112 | 960.114 |
| `uuf_diff_unsat` | T1 | 39 | 0.005 | 0.690 | 32.470 | 45.812 |
| | T2a | 6 | 67.723 | 124.906 | 170.062 | 185.431 |
| | T2b | 2 | 307.403 | 345.638 | 376.225 | 383.872 |
| | T3 | 3 | 660.027 | 660.105 | 660.106 | 660.106 |

Per family. For the SATLIB runs this is the interesting cut — solve time is a
clean function of `n_vars`:

| run | family | n | min | median | p90 | max |
|---|---|---:|---:|---:|---:|---:|
| `uuf_diff_unsat` | uuf50 | 10 | 0.005 | 0.012 | 0.015 | 0.015 |
| | uuf100 | 10 | 0.013 | 0.237 | 0.860 | 0.964 |
| | uuf150 | 10 | 0.334 | 2.372 | 7.922 | 21.614 |
| | uuf200 | 10 | 1.865 | 33.915 | 146.390 | 307.403 |
| | uuf250 | 10 | 45.812 | 170.062 | 660.105 | 660.106 |
| `uuf250_1000c` | uuf250 | 35 | 14.580 | 145.584 | 960.108 | 960.114 |

Roughly an order of magnitude per +50 variables, right up to the cap.

For `mse23_full` (cap 600) the per-family table is degenerate — every family
except `judgment` is 100% at the cap:

| family | n | min | median | p90 | max |
|---|---:|---:|---:|---:|---:|
| judgment | 20 | 71.064 | 660.106 | 660.107 | 660.108 |
| inconsistency | 19 | 611.471 | 660.105 | 660.107 | 660.109 |
| ramsey | 6 | 660.102 | 660.105 | 660.106 | 660.106 |
| optimizing | 5 | 618.008 | 660.108 | 660.111 | 660.111 |
| reversi | 4 | 660.050 | 660.088 | 660.107 | 660.108 |
| setcover | 4 | 660.105 | 660.106 | 660.107 | 660.108 |
| gen | 3 | 660.011 | 660.109 | 660.109 | 660.109 |
| optic | 3 | 660.035 | 660.107 | 660.108 | 660.108 |
| pseudoBoolean | 2 | 660.103 | 660.104 | 660.105 | 660.105 |
| *(the 9 singleton families)* | 1 each | 620.869 – 660.115 | | | |

`mse_cap1800` is the same picture shifted to 1920 s; its only non-cap values are
`judgment` 65.029 and 1313.759, `optimizing` min 1809.615, `inconsistency` min
1895.214.

**Distribution of solved instances over time** (cumulative count of records with
`completed=true` and `solve_s <= t`):

| run | ≤1 s | ≤10 s | ≤60 s | ≤300 s | ≤600 s | ≤900 s | ≤1800 s | total solved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `mse23_full`     | 0 | 0 | 0  | 1  | 1  | 1  | 1  | 1 / 75 |
| `mse_cap1800`    | 0 | 0 | 0  | 1  | 1  | 1  | 2  | 2 / 75 |
| `uuf250_1000c`   | 0 | 0 | 8  | 23 | 26 | 26 | 26 | 26 / 35 |
| `uuf_diff_unsat` | 23| 30| 39 | 45 | 47 | 47 | 47 | 47 / 50 |
| **all**          | **23** | **30** | **47** | **70** | **75** | **75** | **76** | **76 / 235** |

Reading: 23 of the 76 solved records finish in under a second, and 70 of 76
(92%) within 300 s — the marginal return on budget past 5 minutes is small. On
the SATLIB corpora it is nearly all decided by 300 s; on MSE small, budget is
simply not the binding constraint.

### 3.4 Optimal cost

`final_cost` is present only on solved records (76 / 235).

| run | n with OPT | min | median | p90 | max | **OPT == 0** | distribution |
|---|---:|---:|---:|---:|---:|---:|---|
| `mse23_full`     | 1  | 37 | 37 | 37 | 37 | 0 | `{37: 1}` |
| `mse_cap1800`    | 2  | 37 | 40 | 42.4 | 43 | 0 | `{37: 1, 43: 1}` |
| `uuf250_1000c`   | 26 | 1  | 1  | 1  | 1  | 0 | `{1: 26}` |
| `uuf_diff_unsat` | 47 | 1  | 1  | 2  | 2  | 0 | `{1: 39, 2: 8}` |

**No instance in any run has OPT = 0.** That is expected by construction: the
SATLIB corpora are `uuf*` = *unsatisfiable* uniform random 3-SAT, so at least
one clause must be falsified, and the MSE instances are `-un-` unsatisfiable
variants too.

The SATLIB cost distribution is essentially degenerate — 65 of the 73 solved
random instances have OPT = 1, the other 8 have OPT = 2. As an oracle-label
source for a learned solver these carry almost no signal: "cost 1" is the answer
nearly every time.

`cost_lower_bound` (present on 218 / 235):

| run | n | min | median | max |
|---|---:|---:|---:|---:|
| `mse23_full`     | 66 | 3 | 47 | 3176 |
| `mse_cap1800`    | 67 | 2 | 49 | 3176 |
| `uuf250_1000c`   | 35 | 1 | 1  | 2 |
| `uuf_diff_unsat` | 50 | 1 | 1  | 2 |

### 3.5 Instance size

Parsed straight from the DIMACS files (no solver invoked). Semantics follow
`load_as_wcnf()`: a `p cnf` file becomes **all-soft, weight 1, zero hard**;
`soft_total_weight` is the sum of soft weights, which for the MSE unweighted
track equals `n_soft`.

*MSE unweighted-small (both MSE runs, 75 instances, new-format WCNF):*

| tier | n | n_vars | n_hard | n_soft | soft_total_weight |
|---|---:|---|---|---|---|
| T2a | 1  | 6 604 | 48 294 | 78 | 78 |
| T3  | 74 | 55 – 81 317 | 0 – 205 320 | 40 – 61 312 | 40 – 61 312 |

Notable per-family ranges: `extension` n_vars 76 190 / n_soft 39 900;
`inconsistency` n_vars 1 152 – 81 317; `judgment` n_hard 48 294 – 205 320;
`ramsey` is tiny in variables (55 – 190) with **zero hard clauses** and 495 –
9 690 soft — and still 100% T3, which is a useful reminder that size does not
predict hardness here.

*`uuf250_1000c` (35 instances) — completely uniform:*

| tier | n | n_vars | n_hard | n_soft | soft_total_weight |
|---|---:|---|---|---|---|
| T1  | 8  | 250 | 0 | 1 065 | 1 065 |
| T2a | 15 | 250 | 0 | 1 065 | 1 065 |
| T2b | 3  | 250 | 0 | 1 065 | 1 065 |
| T3  | 9  | 250 | 0 | 1 065 | 1 065 |

Every instance is 250 vars / 1 065 clauses, yet solve time spans 14.6 s to the
cap. Size explains nothing within this corpus — this is the run that actually
stratifies by hardness rather than by size.

*`uuf_diff_unsat` (50 instances):*

| tier | n | n_vars | n_hard | n_soft | soft_total_weight |
|---|---:|---|---|---|---|
| T1  | 39 | 50 – 200 | 0 | 218 – 860 | 218 – 860 |
| T2a | 6  | 200 – 250 | 0 | 860 – 1 065 | 860 – 1 065 |
| T2b | 2  | 200 – 250 | 0 | 860 – 1 065 | 860 – 1 065 |
| T3  | 3  | 250 | 0 | 1 065 | 1 065 |

Per family: uuf50 = 50/218, uuf100 = 100/430, uuf150 = 150/645, uuf200 =
200/860, uuf250 = 250/1065 — the standard SATLIB ratios, 10 instances each.

**Caveat on `n_soft` for the SATLIB runs.** The numbers above are the
`p cnf` header counts. The committed SATLIB files end with a `%` / `0` trailer,
and PySAT 1.9.dev2 parses that as **two extra empty clauses** — verified locally:

```bash
$ python3 -c "
from pysat.formula import CNF
c=CNF(from_file='data/unsat/uuf250-1065/UUF250.1065.100/uuf250-0100.cnf')
print(c.nv, len(c.clauses), sum(1 for cl in c.clauses if len(cl)==0))"
250 1067 2
```

So `load_as_wcnf()` on the *committed* copies yields 1 067 soft clauses, two of
which are unsatisfiable — which would force OPT ≥ 2, contradicting the recorded
OPT = 1. See §4.2: this is evidence the cluster copies were not byte-identical
to the committed ones. The header counts (1 065 etc.) are what I report;
what RC2 actually loaded on the cluster is **unknown**.

### 3.6 Commands used

```bash
# statistics + integrity (the script writing §3.1–3.4 and §4)
python3 /tmp/.../scratchpad/analyze.py

# instance-size table (§3.5) — parses DIMACS headers, no solver
python3 /tmp/.../scratchpad/sizes.py
```

Both scripts are pure-stdlib, read-only, and reproduced inline below in
condensed form:

```python
# counts, statuses, percentiles, cost distribution, time CDF
import json, glob, collections
from pathlib import Path
def q(xs, p):
    xs = sorted(xs); k = (len(xs)-1)*p; lo, hi = int(k), min(int(k)+1, len(xs)-1)
    return xs[lo] + (xs[hi]-xs[lo])*(k-lo)
for d in sorted(glob.glob("results/hardness/*/")):
    recs = [json.loads(l) for l in open(d+"all_results.jsonl")]
    print(d, len(recs))
    print(" tiers ", collections.Counter(r["tier"] for r in recs))
    print(" status", collections.Counter(r["profile"]["status"] for r in recs))
    print(" family", collections.Counter(Path(r["instance"]).stem.split("-",1)[0] for r in recs))
    bt = collections.defaultdict(list)
    for r in recs: bt[r["tier"]].append(r["profile"]["solve_s"])
    for t in sorted(bt):
        v = bt[t]; print(f"  {t} n={len(v)} min={min(v):.3f} med={q(v,.5):.3f} p90={q(v,.9):.3f} max={max(v):.3f}")
    solved = [r for r in recs if r["profile"]["completed"]]
    print("  CDF", {b: sum(1 for r in solved if r["profile"]["solve_s"] <= b)
                    for b in (1,10,60,300,600,900,1800)})
    c = [r["profile"]["final_cost"] for r in recs if r["profile"]["final_cost"] is not None]
    print("  OPT n=%d" % len(c), collections.Counter(c), "zeros=", sum(1 for x in c if x == 0))
```

---

## 4. Integrity problems

### 4.1 Instances with no record — **none**

```bash
python3 -c "
import json,glob,os,re,collections
for d in sorted(glob.glob('results/hardness/*/')):
    sh=sorted(glob.glob(d+'tasks/*.jsonl'))
    sr=[json.loads(l) for s in sh for l in open(s) if l.strip()]
    ar=[json.loads(l) for l in open(d+'all_results.jsonl')]
    idx=sorted(int(re.search(r'_(\d+)\.jsonl$',s).group(1)) for s in sh)
    print(d,'shards=%d'%len(sh),'shard_recs=%d'%len(sr),'agg_recs=%d'%len(ar),
          'empty=%d'%sum(1 for s in sh if os.path.getsize(s)==0),
          'idx=%d..%d gaps=%s'%(min(idx),max(idx),
             [i for i in range(min(idx),max(idx)+1) if i not in set(idx)]),
          'shard-only=%s'%sorted({r['instance'] for r in sr}-{r['instance'] for r in ar}),
          'agg-only=%s'%sorted({r['instance'] for r in ar}-{r['instance'] for r in sr}))"
```

| run | shards | records in shards | records in `all_results` | empty shards | task-index gaps | shard-only | agg-only |
|---|---:|---:|---:|---:|---|---|---|
| `mse23_full`     | 75 | 75 | 75 | 0 | none (1–75) | ∅ | ∅ |
| `mse_cap1800`    | 75 | 75 | 75 | 0 | none (1–75) | ∅ | ∅ |
| `uuf250_1000c`   | 35 | 35 | 35 | 0 | none (66–100) | ∅ | ∅ |
| `uuf_diff_unsat` | 50 | 50 | 50 | 0 | none (1–50) | ∅ | ∅ |

Every shard has exactly one record, every shard is represented in the aggregate,
and no aggregate record lacks a shard. The aggregation is lossless.

The one thing this **cannot** rule out: whether more array tasks were submitted
than produced shards. If a task died before writing (SLURM OOM-kill, node
failure), its shard would simply be absent and there is no manifest to compare
against. For `uuf250_1000c` the index range starts at 66, not 1 — see §4.4.

### 4.2 Duplicate records — none within a run; the two MSE runs are a deliberate re-run

- **Within each run: zero duplicates.** `instance`, basename, and stem are each
  1:1 with the record count (§2.5).
- **Across runs: the 75 MSE instances appear twice** — once in `mse23_full`
  (cap 600) and once in `mse_cap1800` (cap 1800). This is intended (a re-run at
  a larger budget), not corruption, and the two directories are genuinely
  distinct: all 75 same-named shard files differ byte-for-byte.

**Do the duplicates agree?**

```bash
python3 -c "
import json,collections
from pathlib import Path
a={json.loads(l)['instance']:json.loads(l) for l in open('results/hardness/mse23_full/all_results.jsonl')}
b={json.loads(l)['instance']:json.loads(l) for l in open('results/hardness/mse_cap1800/all_results.jsonl')}
print('tier600->tier1800', collections.Counter((a[k]['tier'],b[k]['tier']) for k in a))
print('newly solved', [Path(k).name for k in a
      if not a[k]['profile']['completed'] and b[k]['profile']['completed']])
print('LB decreased with MORE time', [(Path(k).name,a[k]['profile']['cost_lower_bound'],
      b[k]['profile']['cost_lower_bound']) for k in a
      if None not in (a[k]['profile']['cost_lower_bound'],b[k]['profile']['cost_lower_bound'])
      and b[k]['profile']['cost_lower_bound'] < a[k]['profile']['cost_lower_bound']])"
```

Yes, and monotonically:

- tier transitions: `{(T3,T3): 74, (T2a,T2a): 1}` — no instance moved tier.
- **Zero instances had their lower bound decrease** when given 3× the budget.
  That is a real consistency check on the SIGKILL-recovery path and it passes.
- One instance newly solved at cap 1800:
  `judgment-aggregation-ja-maxham-preflib-00049-00000293.wcnf` (OPT 43).
- One instance gained a lower bound it previously lacked:
  `optimizing-BDDs-tic-tac-toe-un-wcnf_incomplete_improved_1_2019_6.wcnf`.
- The single T2a instance
  (`judgment-aggregation-ja-maxham-preflib-00049-00000385.wcnf`) is the same in
  both runs, with OPT 37 both times and solve times 71.064 s / 65.029 s — a
  ~9% run-to-run jitter on the same instance, worth remembering before reading
  anything into small `solve_s` differences.

### 4.3 Missing / null required fields

No field is ever structurally absent — `_empty_rec()` pre-populates the whole
`profile` dict — and no *required* field is null: `instance`, `size_mb`, `tier`,
`tier_reason`, `profile.{cap_s, solver, status, solve_s, completed}` are non-null
in all 235 records.

The nullable fields carry three genuine problems:

**(a) 17 records have neither `final_cost` nor `cost_lower_bound`** — RC2
produced *no information at all*, not even a bound, before being killed. These
are the instances where RC2's first SAT call never returned:

| run | n | instances |
|---|---:|---|
| `mse23_full` | 9 | `decision-tree-heart-cleveland-un-…`, `optimizing-BDDs-lymph-un-…_7`, `optimizing-BDDs-tic-tac-toe-un-…_6`, `optimizing-BDDs-vote-un-…_7`, `ramsey-ram_k4_n18.ra0`, `ramsey-ram_k4_n20.ra0`, `reversi-rev66-26`, `reversi-rev66-28`, `reversi-rev66-32` |
| `mse_cap1800` | 8 | the same, minus `optimizing-BDDs-tic-tac-toe-…_6` (which got a bound at the larger cap) |

All 17 are `status="subprocess_killed"`. For these, `tier="T3"` is the only
thing the run established; there is no gap metric available for them at all.

**(b) `ratio` is null on 232 / 235 records and `lb_ratio` on 106 / 235.** For
the two SATLIB runs this is total (35/35 and 50/50) because they were launched
without `--bestknown`. For the MSE runs the residual nulls are 9 (resp. 8)
missing-LB records plus **2 instances whose `bestknown_mse23.csv` entry is `-1`**
(the MSE "unknown" convention), which `assign_tier` correctly skips:

```bash
$ python3 -c "
import csv; rows=list(csv.DictReader(open('data/raw/mse_2024/bestknown_mse23.csv')))
print(len(rows),'rows;', sum(1 for r in rows if int(r['best_cost'])==-1), 'with best_cost=-1')"
75 rows; 2 with best_cost=-1
```

So the field `PROVENANCE.txt` calls "the primary stratifier inside T3" is
unavailable on 45% of records overall and on **100% of the two runs that
actually produce a usable T1/T2 spread**.

**(c) `profile.solver` records `"rc2"` but never the SAT backend, the PySAT
version, the `adapt/exhaust/minz` settings, or the `--grace` value.** Grace is
only recoverable by regex over the free-text `error` string, and only for
records that were SIGKILLed. Nothing in the record identifies the code version
that produced it.

### 4.4 Tier overlap — none, but two adjacent problems

**Within a run, no instance appears in two tiers** (each instance has exactly one
record, hence exactly one tier), and **every one of the 235 tier labels matches
what `assign_tier()` would compute** from `completed` and `solve_s`:

```bash
python3 -c "
import json,glob
bad=0
for d in sorted(glob.glob('results/hardness/*/')):
    for l in open(d+'all_results.jsonl'):
        r=json.loads(l); p=r['profile']; s=p['solve_s']
        exp = 'T3' if not p['completed'] else ('T1' if s<=60 else 'T2a' if s<=300 else 'T2b' if s<=600 else 'T3')
        bad += (exp != r['tier'])
print('tier labels disagreeing with assign_tier():', bad)"
# -> 0
```

Instance-set overlap between runs:

| pair | shared instances |
|---|---:|
| `mse23_full` ∩ `mse_cap1800` | **75** (by design) |
| every other pair | 0 |

The three real problems are:

**(a) `uuf250_1000c` task indices run 66–100, not 1–35.** Task 66 → `uuf250-066.cnf`,
task 100 → `uuf250-0100.cnf` — the index is the *instance number*, not a dense
array index, and it is the only run where task index ≠ position in the
sorted instance list. So this run profiled `uuf250-066 … uuf250-0100` and
nothing else. Whether a `[1-65]` batch was ever submitted (and lost, or never
committed) is **unknown**. If it was, the corpus is silently truncated.

**(b) `mse_cap1800/tasks/` reuses the filenames `mse23_full_arr_task_*.jsonl`.**
The shard names encode the *other* run's name. Nothing breaks today because the
directories differ, but any flat re-aggregation
(`analyze_tiers.py --in-dir A --in-dir B`, or copying shards into one folder)
would silently overwrite 75 cap-600 shards with cap-1800 ones. The `_source_file`
column in the CSV is likewise ambiguous across the two runs.

**(c) The tier thresholds are cap-independent, so tiers are not comparable
across the four runs.** `T3` means ">600 s or unsolved" in `mse23_full`, and
"unsolved within 1800 s" in `mse_cap1800`, and "unsolved within 900 s" in
`uuf250_1000c`. Any pooled "T3 count" across runs is meaningless. This also
means `uuf250_1000c`'s T2b bucket (300–600 s) and its T3 bucket are separated by
a 600–900 s band that no tier describes — three of its instances solved in
311–496 s land in T2b while the 900 s cap was in force, so "T2b" there is not
the same population as "T2b" under a 600 s cap.

### 4.5 The `instance` paths in the SATLIB runs point nowhere

`data/unsat250_1000c/` and `data/unsat_uuf_diff/` do not exist in the repo, and
`.gitignore` does not exclude them — they were never committed. 85 of 235
records therefore have an `instance` path that cannot be dereferenced.

Basename lookup under `data/unsat/**` resolves all 85 uniquely (2 699 files,
2 699 distinct basenames, zero collisions), and file sizes agree with `size_mb`
— but `size_mb` is rounded to 4 decimal places of MB, i.e. 100-byte granularity,
so that agreement is weak evidence. The empty-clause finding in §3.5 is direct
evidence *against* byte-identity: RC2 on the committed copies would see two
unsatisfiable empty soft clauses and could not report OPT = 1.

Note also that basename lookup must be scoped to `data/unsat/`. Widened to all
of `data/`, three names become ambiguous (`uuf250-01.cnf`, `uuf50-01.cnf`,
`uuf50-02.cnf` also exist under `data/exp1/`, `data/exp2/`, `data/unsat_exp/`)
and the sizes differ between copies.

**Verdict: the exact bytes profiled by the two SATLIB runs are not recoverable
from this repository.** Those two runs are not reproducible as committed.

### 4.6 One record is `completed=true` and `tier="T3"`

```json
{"instance": "data/raw/mse_2024/mse23-uw-small/judgment-aggregation-ja-maxham-preflib-00049-00000293.wcnf",
 "size_mb": 2.8171,
 "profile": {"cap_s": 1800.0, "solver": "rc2", "status": "optimal", "solve_s": 1313.759,
             "final_cost": 43, "cost_lower_bound": 43, "completed": true, "error": null},
 "ratio": 1.0, "lb_ratio": 1.0, "tier": "T3",
 "tier_reason": "solve_s>600.0 (cap misconfigured?)"}
```

This is the `assign_tier()` fall-through branch firing exactly as written: the
instance *was* solved to optimality, but in 1313 s, which is past the hard-coded
`T2B_MAX_S = 600`. The `tier_reason` even says "cap misconfigured?".

It is not a data error — the record is internally consistent and the cost is
validated (`ratio == 1.0` against the best-known). It is a **semantic
collision**: `T3` is documented as "RC2 did not converge; only a lower bound"
(`PROVENANCE.txt` §4), and here it means the opposite. Any downstream consumer
that reads `tier == "T3"` as "no optimum available" will be wrong about this
instance. It is the one MSE instance with an oracle label beyond the 600 s
budget, so it is exactly the instance you would not want to mislabel.

### 4.7 Other provenance gaps (from `PROVENANCE.txt`, still unfilled)

`results/hardness/mse23_full/PROVENANCE.txt` is the only provenance file — the
other three runs have none. Its `<FILL IN>` fields remain blank, so all of the
following are **unknown**: MSE source URL/year/DOI, profiler commit at run time,
SLURM array job IDs, cluster/partition, CPU model, RAM per task, wall limit,
conda env name, PySAT version, RC2 SAT backend as actually configured, run
dates, and the tier-count snapshot. Its §3 also mis-states the driver as
`scripts/smoke_mse23.sbatch` and flags its own doubt ("CONFIRM: driver is named
smoke_mse23.sbatch but this run is mse23_full") — that doubt is justified: the
committed smoke script uses `--cap 30 --grace 15` on 5 hard-coded instances and
cannot have produced these 75 shards.

---

## 5. Summary of what is unknown

| question | status |
|---|---|
| SLURM array driver, array spec, `--mem`, `--cpus-per-task`, `--time`, partition | **unknown** — not committed |
| SLURM job IDs, exit codes, `MaxRSS`, node/CPU model | **unknown** — no logs |
| OOM vs timeout split | **unknown**; no positive evidence of any OOM (§3.2) |
| PySAT version and conda env at run time | **unknown** |
| Exact repo commit the runs were produced from | **unknown**; profiler code unchanged since `c3f8eca` (2026-05-20) |
| Whether the corpus is MSE 2023 or 2024 | **unknown** |
| Whether `uuf250_1000c` was meant to cover tasks 1–65 as well | **unknown** |
| Exact bytes of the 85 SATLIB instances profiled | **unknown** — cluster-only dirs, not committed |
| RC2 core counts / lower-bound trajectory | **not captured** — progress file is deleted; only the final LB survives |

## 6. Concrete fixes worth making before the next pass

1. **Commit the array driver.** Without it, none of the four runs is reproducible.
2. **Commit (or checksum) `data/unsat250_1000c/` and `data/unsat_uuf_diff/`**, or
   change the profiler to record the resolved absolute path.
3. **Add `sha256` to the record schema** — it is the only join key that survives
   a corpus being moved or restaged, and it would have settled §4.5 outright.
4. **Record the full solver configuration** in the record: SAT backend, PySAT
   version, `adapt/exhaust/minz/trim`, `grace`, and the code commit — rather than
   the bare string `"rc2"`.
5. **Derive the tier thresholds from `cap_s`**, or refuse to assign tiers when
   `cap_s != 600`, so §4.6 cannot recur and cross-run tiers stay comparable.
6. **Name shards after their own run** (`mse_cap1800_arr_task_*.jsonl`).
7. **Pass `--bestknown` on every run**, otherwise `ratio`/`lb_ratio` — the only
   quality signals in the schema — are structurally null.
8. **Keep the progress file** (or at least log LB-vs-time) if core counts or
   anytime lower-bound curves are ever going to be needed.
