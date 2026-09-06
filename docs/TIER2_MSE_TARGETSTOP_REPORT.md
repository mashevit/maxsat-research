# Run report — target-stop on the T3 MSE instance `00000293`, and the watchdog bug it exposed

**Date: 2026-09-06.** Run against `bc8859f`, on the workstation (`host: Ilia`,
Python 3.11.13, WSL2), not on SLURM. Companion to
[`docs/TIER2_TARGET_STOP.md`](TIER2_TARGET_STOP.md) (how the early stop works),
[`docs/TIER2_MEMETIC_PLAN.md`](TIER2_MEMETIC_PLAN.md) (§6.3 the unit trap, §6.6
time-to-optimum), [`cluster_staging_maxsat/MSE_RUN_NOTES.md`](../cluster_staging_maxsat/MSE_RUN_NOTES.md)
(the SLURM submit for this manifest) and
[`cluster_staging_maxsat/DIVERGENCE.md`](../cluster_staging_maxsat/DIVERGENCE.md).

Five 1800 s runs, ~2.5 CPU-hours. **Four returned no record at all and the fifth
returned an infeasible one.** Nothing here is oracle-comparable. The value of the
run is the two defects it surfaced, both documented below with the measurements
that pin them.

---

## 1. What was run

Instance `data/raw/mse_2024/mse23-uw-small/judgment-aggregation-ja-maxham-preflib-00049-00000293.wcnf`
(`sha256 98c63c04fb54…`, 2.82 MB, 18,508 vars, 134,220 clauses), the **T3** row of
`scripts/manifest_tier2_mse.tsv`. Oracle cost **43**, which is both the manifest's
`oracle_cost` column and the recorded best-known in
`data/raw/mse_2024/bestknown_mse23.csv` — they agree exactly. RC2 proved 43 in
**1313 s** (`mse_cap1800`), which is why the budget was set to 1800 s rather than
the manifest's 900 s: at or below 900 s a win against the exact baseline cannot
be demonstrated even in principle.

All five runs carried `--stop-at-oracle --oracle-cost 43 --budget-s 1800
--tier T3 --rc2-run mse_cap1800`. Shards in
`cluster_staging_maxsat/results/tier2_mse_targetstop/tasks/`.

| job_id | config_id | grace_s | status | best_cost | hard_violations | wall_time_s |
|---|---|---|---|---|---|---|
| `t2mse_local_00293_s1` | `memetic_base` | 60 | timeout | `null` | `null` | 1803.311 |
| `t2mse_local_00293_s2` | `memetic_base` | 60 | timeout | `null` | `null` | 1802.572 |
| `t2mse_local_00293_s3` | `memetic_base` | 60 | timeout | `null` | `null` | 1802.489 |
| `t2mse_local_00293_dp_s1` | `memetic_deeppolish` | 60 | timeout | `null` | `null` | 1800.267 |
| `t2mse_local_00293_jwlp_s1` | `local_multistart_jw_longpolish` | 120 | **ok** | 78 | 4249 | 1813.042 |

Every timeout row carries `error: "watchdog_fired_at_budget+60s"`, and
`stop_reason`, `ea_generations`, `children`, `total_flips`, `abs_gap` and
`is_optimal` are all `null` — the process was killed *inside* the solver call, so
the shard records nothing about the search. `finished_at` is `null` too: on the
timeout path `emit()` runs before the `finally` block that would set it
(`run_memetic_shard.py:442-456`).

---

## 2. Defect A — the watchdog beats the solver

Three causes stack. None alone would matter; together they kill every EA run at
an 1800 s budget on this machine.

**A1. `ITIMER_REAL` fires ~4 % early under WSL2.** Measured directly:

```
signal.setitimer(signal.ITIMER_REAL, 90.0)  ->  fired at wall 86.549 s   (ratio 0.9617)
```

So `--budget-s 1800 --grace-s 60` does not arm the watchdog at 1860 s. It arms it
at roughly **1790–1803 s**. This is the whole reason `wall_time_s ≈ 1803` was
mistaken for "the budget plus setup": it is the alarm, firing early.
`memetic_deeppolish` landing at **1800.267 s** — below even the nominal budget,
let alone 1860 — is the cleanest confirmation.

**A2. The EA's clock starts after its own setup.** `start_t = time.time()` is at
`cluster_staging_maxsat/src/evo/memetic.py:76`, *below* `pop.init_seeds()` and the
initial-evaluation loop. The shard's `t0` is at
`cluster_staging_maxsat/src/cli/run_memetic_shard.py:430`, *above* the whole call.
The EA therefore intends to return at `t0 + setup + 1800`, not `t0 + 1800`.
Measured setup on this instance: **3.4 s** (pop 60) / **2.1 s** (pop 40).

**A3. The time cap is tested once per generation.** The `while` header at
`memetic.py:125` is the only test, so the EA overshoots its own deadline by up to
one full generation — and a generation here costs **~30 s** (see §3).

Net: the EA aims to return somewhere in **1803–1833 s**; the watchdog arrives at
**1790–1803 s**. It loses by a hair, deterministically. That the three
`memetic_base` seeds died within 0.8 s of each other is the signature of a timer,
not of a search.

### Ruled out: `init_seeds`

`Population.init_seeds` (`src/evo/population.py:144-152`) rebuilds
`hard_clauses = [cl for cl in wcnf.clauses if cl.is_hard]` **inside** the
per-member loop — a full 134,220-clause scan repeated `pop_size` times. It is
genuinely loop-invariant and genuinely wrong, and it was the first hypothesis
here. It is **not** the cause: one scan measures **0.007 s**, so 60 scans cost
0.4 s. Worth hoisting on general principle; it will not change any outcome.

| measurement (this instance) | pop 60 | pop 40 |
|---|---|---|
| `init_seeds` | 2.0 s | 1.2 s |
| initial `evaluate` of all members | 1.4 s | 0.9 s |
| **total setup before `start_t`** | **3.4 s** | **2.1 s** |

### Fixes

* **Immediate, no code change:** raise the grace. `--grace-s 300` arms the
  watchdog at ~2020 s against an EA deadline of ~1833 s. Note the SLURM
  `--time=00:20:00` in `scripts/tier2_memetic_array.sbatch` does **not** fit an
  1800 s budget at all and would have to move with it.
* **Proper:** hoist `start_t` above the population construction so `--budget-s`
  means what it says, and test the cap inside the child loop rather than only at
  the generation boundary. Both are staging-side changes and would need a third
  entry in `DIVERGENCE.md`.

---

## 3. Defect B — nothing reaches feasibility, which is the finding that matters

This instance is **134,142 hard clauses against 78 soft**, every soft weight 1
(`soft_total_weight: 78`). Oracle 43 therefore means 43 of 78 soft clauses
unsatisfied. The entire difficulty is reaching a feasible assignment at all.

A 60 s smoke on `memetic_base` completed cleanly (`status: ok`), confirming the
pipeline itself is sound:

```
best_cost 13   hard_violations 6032   unsat_soft_clauses 13
ea_generations 2   children 114   stop_reason time_cap   wall 77.08
```

`best_cost 13` beats the oracle's 43 **only because the assignment violates 6,032
hard clauses.** `run_memetic_shard.py:18` is explicit that such a cost must not be
compared against the oracle, and the shard correctly left `abs_gap` and
`is_optimal` null. Two generations in 77 s is where §2's ~30 s/generation comes
from.

The one completed 1800 s run is worse, not better:

```
local_multistart_jw_longpolish  best_cost 78  hard_violations 4249  restarts 30
```

`best_cost 78 == soft_total_weight 78` — **zero** soft clauses satisfied, the
worst attainable value, with 4,249 hard clauses still violated. The polish spends
its whole budget failing to reach feasibility and never engages the soft
objective.

**Consequence for planning: fixing Defect A converts four `null`s into four
*infeasible* records.** More rows, still nothing comparable to the oracle. RC2
proved 43 on this instance in 1313 s; the current stack is not in that regime.
This is the same failure as the `00000385` 60 s smoke (`hard_violations=1`) noted
in `MSE_RUN_NOTES.md`, three orders of magnitude worse.

---

## 4. New config: `local_multistart_jw_longpolish.yaml`

Added at `cluster_staging_maxsat/configs/tier2/local_multistart_jw_longpolish.yaml`
(untracked at time of writing). It is
`local_multistart_jw_deeppolish.yaml` with the `ls:` block swapped and nothing
else, so the pair isolates the per-restart polish budget:

```yaml
solver: local_multistart
multistart:
  init: jw
ls:
  ls_polish_flips: 1000000
  time_limit_s: 60
  flip_budget: 1000000
```

**`flip_budget` alone would have been inert.** `evo.operators.short_polish:402`
resolves WalkSAT's flip cap as
`ls_cfg.get("ls_polish_flips", ls_cfg.get("max_flips"))`, and
`evo.memetic._ls_budget:27` always supplies `ls_polish_flips` (default 700) — so
the second key is never consulted, and setting only `ls.flip_budget` would have
left the polish capped at 700 flips. `ls.flip_budget` is read only by
`sat.walksat.run_satlike` (`walksat.py:348`), a different entry point. Both keys
are set to the same value here, matching the deeppolish presets.

**The config did not achieve its purpose on this instance.** It exists because
`multistart.py`'s docstring calls for an arm where the flip cap binds rather than
the clock. It does not:

| | asked | actual |
|---|---|---|
| flips per restart | 1,000,000 | **~3,099** (92,966 over 30 restarts) |
| what binds | the flip cap | still the clock, now at 60 s |

That is **~52 flips/sec**; one restart would need ~5.3 hours to reach 1M flips. A
flip-bound arm is not reachable on this instance at any sane wall-clock, and the
docstring's advice should be read as instance-dependent. The 30 restarts is
exactly 1800/60 — every restart hit the clock.

Also worth recording: `ls.time_limit_s` and the top-level `time_limit_s` are
different scopes. The former caps **one restart's polish**; the latter caps the
**whole run** and is injected from `--budget-s` by the shard runner, which
`run_multistart_ls` prefers (`multistart.py:212`). A run can overshoot its total
budget by one polish — now up to 60 s, not 0.5 s — so `--grace-s` must be sized
against it. That is why this arm got `--grace-s 120` and was the only one to
survive Defect A.

---

## 5. Provenance

All five shards carry `git_sha bc8859f8cd65b73529b92fbb7fca567d6542283d`,
`host Ilia`, `python 3.11.13`, `instance_sha256 98c63c04fb54…`,
`instance_format wcnf_new`, `schema_version 2`, `stop_at_oracle true`,
`target_cost_used 43`. Started 09:54–10:13 local, 2026-09-06.

Runs were local and concurrent (5 single-threaded processes on 12 cores, load
well under capacity), so wall-clock is not contended — but this is a workstation
under WSL2, and **§2's timer skew is a property of this machine.** The same
budgets on the cluster may not reproduce the failure. Re-measure `setitimer`
drift there before concluding the grace is sufficient.

## 6. Open decisions

1. `--grace-s 300` for any further local runs at 1800 s (and a matching SLURM
   `--time` if this goes to the cluster).
2. Whether to make the `start_t` hoist + in-loop cap check a third
   `DIVERGENCE.md` entry.
3. Whether this instance is worth further budget at all before feasibility is
   addressed — §3 says no.
