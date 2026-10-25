# Instance-aware hyperparameters for the strong solver (`auto_hparams/3`, 2026-10-25)

> "write preprocessing script that passes to solver optimal hyperparameters,
> whether hard/soft or if small number of vars versus tens thousands of vars
> and clauses" (user, 2026-10-21)

**Tree:** `cluster_staging_maxsat_strong/`. **Code:**
- `src/evo/auto_hparams.py` (rules, `resolve()`);
- `src/cli/run_memetic_shard.py` (`hparams: auto`, shard schema 6);
- `configs/strong/auto.yaml` (the one batch config);
- `scripts/auto_hparams.py` (writes it; preview);
- `tests/test_auto_hparams.py`.

The search code (EA, polish cores) is unchanged. Note N-2026-10-21-b.

**Revisions:**
- `/1` (2026-10-21): R0–R3. Batches O900 and KS2 ran on it (`097efb7`).
- `/2` (2026-10-21, N-2026-10-21-h): R4 added, giving pop 10 and
  `keep_sat: ks2` on hard instances. `merge()` is now deep. Soft instances
  resolve exactly as under `/1`.
- `/3` (2026-10-25, N-2026-10-25-c): R5 added. It sets
  `hard.moves.per_polish` 10 on hard instances whose v3 neighbour tables are
  lean, which today means only the 3 setcover rail instances.
  - Every instance with full tables resolves exactly as under `/2`.
  - The record's `features` gains `nbrs_mode` and `nbrs_bound`, filled for
    hard instances only.
  - Batches HMSE, U30 and PP10 ran on `/2`.

## 1. What it does: chosen at run time, in memory

User, 2026-10-21: "build the run-time version". There are no per-instance
config files.

1. **One batch config:** `configs/strong/auto.yaml`. It is the S1 `allC`
   values plus `hparams: auto`, written by
   `scripts/auto_hparams.py --write-base`.
   - Options: `hparams: {mode: auto, flips_c, flips_cap}`.
   - `--check` confirms the file matches the generator.
2. **In each job:**
   - the shard runner runs its kernel gate as before;
   - it then calls `auto_hparams.resolve()` on the instance the EA will
     solve (the kernel if used, else the original);
   - the chosen values are merged into the config in memory;
   - the merged config is validated, and the run uses it.
   - Nothing is written except the usual shard.
3. **Time:** the choice counts inside the budget, like the gate, so the
   solver gets budget − gate − choice. It is added to `time_to_target_s`.
   Measured: 0.1–6 ms (§3a).
4. **Record (shard schema 6):** the new field `hparams` holds:
   - the rule set and the class;
   - the features (n, m, hard count, weights, gate, n_eff, m_eff);
   - the overrides and the reason for each;
   - `resolved_config_hash` and `hparams_s`.

   `config` / `config_hash` remain the submitted file, so every task of a
   batch has the same `config_hash`. `scripts/m2_results.py` adds the
   `hp_*` columns.
5. **Refused before the run (exit 2):**
   - `hparams: auto` with an impl other than v3;
   - unknown `hparams` keys or values;
   - the no-EA baseline solver;
   - a batch config that one of the rule classes would make invalid.
6. **Preview:** `scripts/auto_hparams.py --instance … / --list … [--map
   csv]` runs the same `resolve()` on the workstation, so it shows what each
   job will choose. A test checks that the preview's resolved hash equals
   the job's.

"Optimal" is not claimed. Each value carries its evidence: measured by us,
from a paper, or inference.

## 2. The rules

| rule | key | value | evidence |
|---|---|---|---|
| R0 | everything else | S1 `allC`: B1 cc, B2 dls, B3 walk, B4 px, B5 native; kernel gate; pop 40, tournament 3, elitism, clip; `hard_mode: auto` | measured: S1 smoke (STRONG_MEMETIC_S1_RUN §2.2) |
| R1 | `ea.mutation_k` | clamp(round(0.04 · n_eff), 2, 16) | k 16 measured (n ≥ 300); **the shrink below n 400 is inference, untested** |
| R2 | B2 `dls_t, sp, zeta, h_inc` | by class, below | |
| R3 | `ls_polish_flips` = `flip_budget` | max(12,500, min(c · n_eff, cap)); **default c = 0 → 12,500** | 12,500 measured for v3 (raw n 64k solved); c > 0 untested for v3 |
| R5 (`/3`) | `hard.moves.per_polish` | **10** when the solved instance has hard clauses **and** its v3 tables are lean (`ls.nbrs: lean`, or `auto` with Σk(k−1) > 50M, read by `ls_v3.nbrs_plan`, the same function the tables use); otherwise the config's value (default 200) | measured: batch PP10. Rail 3/3 better, median gap +49–71 % → +9–15 %. As a general rule, 10 failed: 21 non-rail instances, 5 better / 12 worse, successes 19 vs 25 of 63. Rail-only is the user's pre-registered fallback. `PERPOLISH_RUN.md` §6 |
| R4 (`/2`) | `ea.pop_size`, `hard.moves.keep_sat` | **10 and `ks2`** when the solved instance has hard clauses; otherwise unchanged (40, `none`) | measured: batch KS2. Runs at the optimum: m40 12, ks2_10 26 of 48. ks2_10 vs m10: 13 better / 0 worse; vs m40: 13 / 2. The pre-registered rule failed at pop 40 (10 / 3), and pop alone showed no effect. Pop 10 is the user's choice (2026-10-21). `KS2_CHECK_RUN.md` §6 |

**R2 classes.** "Hard" is judged on the effective instance, as `hard_mode:
auto` does. "Weighted" is judged on the original instance, because kernel
merging gives an unweighted formula weights of 2, 3, ….

| class | t | sp | ζ | h_inc | evidence |
|---|---:|---:|---:|---:|---|
| soft, unweighted | 15 | 0.01 | max(50, 49 + max kernel weight) | 1 | measured at 50 (S1 smoke) |
| soft, weighted | 15 | 0.01 | max(50, 49 + max soft weight) | 1 | inference, untested |
| hard, unweighted | 42 | 3·10⁻⁶ | 400 | 1 | SATLike PMS industrial; "industrial" for MSE is inference |
| hard, weighted | 15 | 0.01 | 1 | 3 | SATLike WPMS; sp 0.01 vs 0.0001 per class unverified |
| hard, weighted, mean soft weight > 10,000 | 15 | 0.01 | 500 | 300 | SATLike WPMS |

**Why R3 keeps 12,500 at every size.** Stage L1 found 0.8–1.6M flips per
call best at n 16k and 64k, but under v2's 2 % mutation, whose repair work
grows with n. With B3 a mutation adds 6.5–12.4 unsatisfied clauses at any n,
and `allC` reached c\* on raw n 64,000 with 12,500 flips (s256 53.8 s, s257
48.2 s). `--flips-c` exists for a calibration grid. On soft instances it
also sets `polish_cap: flips_only`, as Stage L1 did. Hard instances keep the
3.5 s slot, because feasible moves M share it.

Hard-tree keys (Glucose, repair R, moves M) keep their `hard_cfg` defaults,
the values H3 accepted.

**The rules override the batch config.** An explicit `per_polish` 200 on a
lean instance resolves to 10 under `/3`, so rerunning PP10's `pp200` arm on
rail now gives 10. The record shows this in `hparams.overrides`.

**R5 check on real instances** [verified: workstation preview, 2026-10-25]:
- **All 144 MSE hard-clause instances:** the 141 HMSE ones and the 3 rail
  ones.
- **R5 fires on rail507, rail516 and rail582 only.** Their bounds are 768.6M,
  641.2M and 1,142.7M, and resolving costs 0.4–0.6 s inside the budget.
- **The other 141** resolve to `hard: {moves: {keep_sat: ks2}}` exactly as
  under `/2`. Their largest bound is 36.9M.
- **Tests:** 412 passed, 16 skipped (9 new). A copy of the code with the R5
  line removed fails 4 of them.

## 3. Dry run on the "< 900 s" pool (582 instances, N-2026-10-21-a) [verified]

- 9.6 s for all 582 instances on the workstation, including parsing and
  the gate (the choice itself takes milliseconds); **25 distinct resolved
  configs**.
- **Class:**
  - soft unweighted: 572;
  - hard weighted: 6 (MSE 2024);
  - hard unweighted: 2 (MSE 2023);
  - soft weighted: 2 (the MSE 2024 `drmx-cryptogen` instances, no hard
    clauses, soft weights up to 1601).
- **Gate:** kernel on 85 instances (sparse 2-SAT: e.g. n 32,000 → 57–116
  variables); skipped on 497.
- **`mutation_k`:** 16 on only 21 instances. The rest get 2–13 (uuf200–250
  → 8–10; calib n 50–150 → 2–6).
  - **So R1's untested shrink governs about 96 % of the pool.**
  - Before a full batch, a smoke of k(n) against k 16 on small instances
    would test it.

## 3a. Real runs through the shard runner with the C core [verified: workstation, 60 s, seed 1, stop at c\*]

| instance | effective instance | chosen | choice time | result |
|---|---|---|---:|---|
| s256 (n 64,000, c\* 13) | kernel, 572 vars | soft unweighted, k 16, ζ 50 | 6.1 ms | **13 in 0.42 s** (1 child) |
| uuf200-022 (c\* 1) | original, 200 vars | soft unweighted, k 8, ζ 50 | 0.1 ms | **1 in 0.06 s** |
| ja-385 (MSE 2023, hard, c\* 37) | original, 6,604 vars | hard unweighted, t 42, sp 3·10⁻⁶, ζ 400 | 2.2 ms | 38 at 60 s, feasible, 1,068 children, hard mode on |

- On s256 the resolved hash equals the submitted one: all chosen values
  equal the base values.
- For reference: `impl: hard` reached 37 on ja-385 in 60 s on 1 of 3 seeds
  (H3).

## 4. Use

```bash
# from cluster_staging_maxsat_strong/ (workstation; the login node runs no Python)
python3 scripts/auto_hparams.py --write-base            # configs/strong/auto.yaml (done)
python3 scripts/auto_hparams.py --check
python3 scripts/auto_hparams.py --list pool.txt --map preview.csv   # optional preview
# every task of the batch then uses the same config:
python -m src.cli.run_memetic_shard --instance X --config configs/strong/auto.yaml ...
```

**Tests:** 22 in `tests/test_auto_hparams.py`; suite 351 passed / 24
skipped. They cover:
- the rules and classes;
- the kernel sizing;
- kernel weights not changing the class;
- the shard path: merged in memory and recorded, the run uses the chosen
  values (spy), the time is inside the budget, preview = job, nothing extra
  written, unchanged without `hparams`, bad configs refused;
- the script.

## 5. Open

- **R4 smoke [verified: workstation, `/2`, seed 1, 120 s, C core, stop at the
  optimum]:** mbd-b14 reached 24 in 19.4 s, and quantum-circuit reached 24
  in 106.8 s. Both are 0/3 under `/1` at 900 s (O900).
- **Soft-weighted rule:** drmx-cryptogen is 0/6, and the rule is unchanged
  (user, 2026-10-21). `ls.weights: run` or 1M flips per call gives 811–818
  at 900 s, still 0/10 at 800 (N-2026-10-21-h).

- The pool manifest waits on the four questions from 2026-10-21:
  - arms;
  - the < 1 s instances;
  - kernel on or off;
  - the EvalMaxSAT batch.
- Smoke before the batch:
  - R1 k(n) against k 16 on small instances;
  - the 10 MSE instances (60 s, `allC` against `base`).
