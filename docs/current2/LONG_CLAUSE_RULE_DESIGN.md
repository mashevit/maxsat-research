# Long-clause rule: running v3 on the setcover rail instances without neighbour tables (design, 2026-10-21)

> "I do want to code with you some rule for the rail instances" (user,
> 2026-10-21); "start with the rail rule design" (user, 2026-10-21).

**Status:** built 2026-10-21 (§8), as recommended (user: "do the recommended, dont do peak memory, we set per job on cluster anyway"). Not committed, not on the cluster.
**Tree:** `cluster_staging_maxsat_strong/`.
**Background:** `UNDER30_HARDMSE_RUN.md` §4 (the rail failure), N-2026-10-21-i.

## 1. The problem [verified]

`impl: v3` builds `_V3Static.nbrs` (`src/sat/ls_v3.py`) once per instance.
For each variable, it is the sorted list of every variable sharing a clause
with it. A clause with k variables contributes k(k−1) entries.

| instance | Σ k(k−1) (upper bound) | entries actually built | memory to build | time to build |
|---|---:|---:|---:|---:|
| optic-gen_mult_5_5_991 (HMSE) | 36.9M | 7.65M | +522 MB | 4.3 s |
| af-synthesis stb_50_40_0 (HMSE) | 31.8M | 24.7M | +1,433 MB | 3.9 s |
| setcover rail516 / 507 / 582 | 641M / 769M / 1,143M | — | over 7.3 GB at 34–38 s, then MemoryError | — |

- **Cost per entry:** 61–72 bytes while the table is built (Python sets,
  then sorted lists).
- **NativeCore adds 4 bytes per entry:** the flat C array.
- **Every other instance we have is far below.** Across all 735 other
  instances in O900, U30, KS2, calib_2sat_sc2 and HMSE, the largest bound
  is 36.9M (optic). Next come af-synthesis at 31.8M and quantum-circuit at
  2.7M.
- **A 17× gap:** between 36.9M and rail's smallest bound, 641M.

## 2. Who uses `nbrs` [verified: code]

| user | where | what it needs |
|---|---|---|
| CC tabu (B1) | `ls_v3.py` walksat_v3 (flip at line ~374) and dls_v3 (~674); C twin `ls_core.c` lines 236, 391 | after flipping v: conf[u] = 1 for every neighbour u, then conf[v] = 0. Only the **set** matters, not the order. |
| walk mutation (B3) | `src/evo/v3.py` ~195–208 | a **uniformly random** neighbour of v: `nb[rng.randrange(len(nb))]`; a random variable if v has none |
| partition crossover (B4) | `src/evo/v3.py` `px_components` ~214–240 | the connected components of the interaction graph restricted to D, the variables where the parents differ, ordered by first variable |
| NativeCore | `src/native/native.py` ~133–136 | flattens `nbrs` for the C CC update only |

`cvd` (the per-clause variable lists) and `_static_for` (occurrences,
literals) are linear in Σk, so rail's tables fit easily: 0.36–0.47M
literals.

## 3. Proposed rule: "lean" tables when the bound is large

**Trigger (automatic):**
- At the first `v3_static` call, compute B = Σ_c k_c(k_c − 1), with k_c
  the distinct variables of clause c. This is O(Σk).
- If B > `NBRS_MAX` = **50,000,000**, the instance runs **lean**: `nbrs`
  is never built.
- **Why 50M:** it is above every non-rail instance (max 36.9M), so they
  all stay byte-identical to the batches already run. At 72 B/entry it
  also caps the full tables near 3.6 GB, inside the cluster's 8 GB.
- **Any value from 40M to 600M selects exactly the same 3 instances**,
  so the choice is not delicate.
- Config override: `ls.nbrs: auto | full | lean` (default `auto`). Tests
  force `lean` on small instances.

**In lean mode, each user changes as follows:**

**L1. CC: exact and identical.** After flipping v, walk v's clauses and
set conf[u] = 1 for every variable u in each of them, then conf[v] = 0.
- **Same result:** the set reached is N(v) ∪ {v}, and conf[v] is then
  cleared, so every conf value equals full mode after every flip.
- **Same run:** every decision and every RNG draw is the same.
- **Cost per flip:** Σ_{c∋v} k_c instead of |N(v)|. That is the same order
  as the flip's own score update on those clauses, which already visits
  each changed clause's variables.
- **Code:** in both Python cores and in C, using the existing
  `occ_off/occ_ci/lit_off/lits` arrays. No new data.

**L2. PX components: exact and identical.**
- **How:** one pass over the clauses that touch D. Union, with
  union–find, the D-variables of each clause. Then label components by
  their smallest variable and sort each.
- **Same result:** the components and their order are those of the
  current BFS, because "u and x share a clause and both are in D" is
  exactly the edge set used now. So the same crossover is produced.
- **Cost:** O(Σ_{c touching D} k_c).

**L3. Walk mutation: same distribution, different random stream.**
"Uniform over distinct neighbours" without the list needs rejection
sampling:
1. Pick a clause c ∋ v with probability ∝ (k_c − 1), then u uniform among
   c's other variables. This draws u with probability ∝ mult(u), where
   mult(u) = the number of v's clauses that contain u.
2. Accept u with probability 1 / mult(u). Membership is tested by bisect
   on `cvd[c]`, which is sorted by variable. Otherwise draw again.
3. The result is exactly uniform over N(v), the same distribution as
   full mode. If v has no neighbours, take a random variable, as now.

- **Different stream:** the draws consume the RNG differently, so a lean
  run is not byte-equal to what a full run would give. On rail no full
  run is possible, so nothing comparable is lost.
- **Expected cost:** small. A rail variable sits in 6.5–7.2 rows on
  average and at most 12, so mult ≤ 12 and acceptance is high.
- **Simpler alternative (L3′):** take u from a random clause and a random
  variable, without the correction. It is biased toward variables that
  share many clauses with v. Not recommended: the mutation would then
  differ in kind, not only in stream.

**L4. NativeCore:** passes no `nb` arrays in lean mode (`nb_off = NULL`),
and C runs the L1 update from the clause arrays.

**Record:** new fields `nbrs_mode` (full/lean) and `nbrs_bound` (B) in
the shard record, additive at schema 7.

## 4. What this does not solve [inference]

- **Speed is unknown.** Lean fixes memory only. rail rows have 610–807
  variables on average and up to 8,919, so a flip that changes a row's
  satisfied count touches the whole row.
- **Search quality on set cover is open:** 507 rows, 47k–63k unit soft
  clauses. The 60 s smoke after the build (§6) will show both speed and
  quality.
- **Run-time memory growth** (Glucose learned clauses, ks2 cores over
  900 s) is the separate RAM-audit item (NEXT_SESSION r15).

## 5. Tests (all must pass before any batch)

1. **The default is unchanged:** every existing test, including the
   v3 == v2 and C == Python equality tests, with the default `auto`.
   Every existing instance resolves to full mode.
2. **Lean == full for CC:** on small instances forced `lean`, walksat_v3
   and dls_v3 with `tabu: cc` / `cc: true`, in Python and in C, give
   flip-for-flip identical traces and results against `full`.
3. **Lean == full for PX:** `px_components` and `partition_crossover`
   give identical output on random parent pairs over several instances.
4. **L3 distribution:** a χ² test that lean walk draws are uniform over
   N(v) on a constructed instance with overlapping clauses (mult up to 3).
   The lean walk is also deterministic under a fixed seed.
5. **Trigger:** B is computed correctly. `auto` picks lean only above
   50M; rail507 builds in lean with peak RSS of a few hundred MB.
6. **End to end:** a lean shard-runner run writes `nbrs_mode: lean`, and
   an equal-seed rerun gives the same record.

## 6. After the build

- **Smoke:** the 3 rail instances, 60 s each, one at a time, capped. Read
  peak RSS, flips per second, slot split and cost against best-known.
- **Batch:** HMSE-rail, 3 instances × 3 seeds × 900 s = 9 tasks, on a
  new commit, as a separate small manifest. The 423-task HMSE batch
  stays as committed.

## 7. Decisions for the user

1. **Trigger:** automatic lean above B = 50M. Alternative: always lean,
   which changes the walk stream on every instance and so breaks
   comparability with O900/KS2/HMSE. Not recommended.
2. **Walk:** L3 (same distribution, rejection sampling, recommended) or
   L3′ (simpler, biased).
3. **Scope:** also add `peak_rss_mb` (`resource.getrusage`) to every
   shard record now. It is one line and starts the RAM audit. Or keep
   that for the audit step.

## 8. Built (2026-10-21) [verified]

**Decisions taken:**
- automatic trigger above 50M;
- L3 rejection walk;
- no `peak_rss_mb` (the user: memory is set per job on the cluster).

**Code (tree `cluster_staging_maxsat_strong/`):**
- **`src/sat/ls_v3.py`:**
  - `_V3Static` computes the bound B and the mode;
  - in lean mode it builds `aocc` (every clause of v) and `cv` (the
    distinct variables of each clause) instead of `nbrs`;
  - `set_nbrs_mode`, `nbrs_info` and `cc_touch_lean`;
  - both cores take the lean CC branch when `nbrs` is None.
- **`src/evo/v3.py`:**
  - config key `ls.nbrs: auto | full | lean`;
  - `lean_neighbour` (L3);
  - `_px_components_lean` (L2);
  - stats `nbrs_mode` and `nbrs_bound`.
- **`src/evo/memetic.py`:**
  - sets the mode on the solved instance before any table is built;
  - records mode and bound in the record's `v3` field, only if the run
    built the tables, so they stay lazily built.
- **`src/native/native.py` and `ls_core.c`:**
  - lean arrays and a NULL `nb_off`;
  - `cc_touch`;
  - `load_native` rebuilds when the tables change.
  - **The C source changed, so the cluster `.so` must be rebuilt**
    (`sbatch build_native.sbatch`).
- **Deviation from §3:** no schema bump. The two fields sit inside the
  `v3` dict, additively.

**Tests:** `tests/test_lean_nbrs.py`, 28 tests (27 pass, 1 skip by
design).
- the bound and the trigger;
- the lean tables match their definitions;
- lean == full for walksat/dls CC, in Python and in C, including traces;
- PX components and children are equal;
- the χ² of the lean walk is below the p = 0.001 critical value;
- end to end: lean == full == auto for CC + PX + count mutation, with
  Python and native and with hard clauses, and the mode is recorded;
- a lean walk is deterministic;
- config validation.

The instances include tautological clauses, repeated literals and a long
clause. A deliberately broken `cc_touch_lean` fails the tests. Full
suite: **403 passed, 16 skipped**. All existing equality tests pass
unchanged.

**Smoke** (workstation, `configs/strong/auto.yaml`, seed 1, 60 s, one at
a time, 7.5 GB cap; records in `tmp/smoke_hmse/lean/`):

| instance | B | mode | peak RSS | cost at 60 s | best-known | time in moves M/ks2 | polish flips |
|---|---:|---|---:|---:|---:|---:|---:|
| rail507 | 768.6M | lean | 284 MB | 513 | 174 | 57.1 s | 0 |
| rail516 | 641.2M | lean | 221 MB | 603 | 182 | 57.4 s | 0 |
| rail582 | 1,142.7M | lean | 267 MB | 654 | 211 | 56.6 s | 0 |

- **Memory is solved:** 221–284 MB, against over 7.3 GB before. All runs
  stay feasible.
- **[inference] Search:** as on lisbon-wedding (N-2026-10-21-d), the
  feasible SAT moves fill every 3.5 s slot, so the B1–B5 polish never
  runs.
  - The moves do improve steadily: initial best 4,521–6,017, 1,022–1,784
    improving moves, cost 2.8–3.1× the best-known at 60 s.
  - What 900 s reaches is open.
  - A search rule for set cover (for example a slot share for the
    polish) would be a separate design.

## 9. Slot share for the polish: `hard.moves.per_polish` on rail (2026-10-21) [verified: workstation]

> "run the per_polish test on the rails" (user, 2026-10-21)

**Setting:** the batch config with `-D hard.moves.per_polish=N`; lean
tables; seed 1; 60 s; one run at a time. Records are in
`tmp/smoke_hmse/{lean,perpolish}/`. N = 200 is the default.

| instance | best-known | cost, N 200 | cost, N 50 | cost, N 10 | polish flips (N 200 / 50 / 10) | children (200 / 50 / 10) | move time s (200 / 50 / 10) |
|---|---:|---:|---:|---:|---|---|---|
| rail507 | 174 | 513 | 224 | **218** | 0 / 362k / 767k | 17 / 30 / 62 | 57.1 / 47.4 / 27.0 |
| rail516 | 182 | 603 | 221 | **216** | 0 / 338k / 863k | 17 / 28 / 70 | 57.4 / 43.9 / 23.6 |
| rail582 | 211 | 654 | 275 | **265** | 0 / 282k / 738k | 17 / 23 / 60 | 56.6 / 44.1 / 24.2 |

- **Default (N 200):** the moves fill every slot.
- **Lower N:** the polish gets time, and the cost at 60 s falls 2.3–2.8×,
  from 2.8–3.1× the best-known to 1.19–1.26×.
- **N 10 vs N 50:** N 10 is slightly better than N 50 on all three.
- All runs stay feasible. Peak memory is 220–282 MB.

**[inference] Caveats:**
- one seed and 60 s;
- whether the gain holds at 900 s, and on the other MSE families, is
  untested. Batch KS2 and lisbon-wedding used N 200.
- Changing the default would change `auto_hparams` (R4) for every hard
  instance, so it needs a wider check than rail.
