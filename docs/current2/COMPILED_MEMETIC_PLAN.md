# Compiled memetic: memory and speed for the MSE 2026 sizes (plan + record, 2026-10-28)

**Created:** 2026-10-28. **Index:** `docs/current/RESEARCH_NOTES.md`,
N-2026-10-28-d. **Tree:** `cluster_staging_maxsat_strong/`. Comes before
milestone 3c of `MSE26_RHO_PLAN.md` (the 952 × 3 × 1800 s manifest).

> "if you reason optimizing further and compiling parse and memetic will help
> tell me, tell me also if you can find some memory optimizations in research
> litreture, that you might be able to implement" (user, 2026-10-28)
>
> "do the recommended best option, document all optimiztions and compilations"
> (user, 2026-10-28)

This document is the single record of every optimisation and every piece
moved to C: what it replaces, why, how equality is proven, and what it
measured. §4 is the inventory; §8 is the build log, filled per milestone.

## 1. Why [verified: measurements 2026-10-28]

The memetic needs about 90–100 MB of RAM per MiB of `.wcnf` (2 real MSE
files: 88×, 94×; 3 synthetic: 96–100×). Stage by stage, on a real 5 MiB MSE
file (`ja-kemeny-…00300`, 276,705 clauses):

| stage | MB | × file |
|---|---:|---:|
| parse into `Clause` objects + `pos_adj`/`neg_adj` | 101 | 20× |
| `walksat_v2._Static` (lits, cvars, occ; Python tuples) | 116 | 23× |
| `ls_v3._V3Static` (cvd, nbrs) | 95 | 19× |
| `NativeCore` flatten (Python lists, then C arrays) | 32 | 7× |
| total before the run | 353 | 71× |

The C polish core needs only its flat arrays (a few × the file). The rest is
the same instance held three more times as Python objects.

Consequences for MSE 2026 (952 instances with a proven optimum):
- **Memory:** 33 instances (581 MiB – 3.4 GiB) are predicted above 48 GB
  (75 % of the 64 GB bin); the parse alone of a 3.4 GiB file needs ~68 GB.
- **Parse time:** ~5.5 MB/s, about 10 min for the largest file.
- **Speed per child:** fitness is a Python loop over every clause (plus O(n)
  Python copies and conversions). A 26 MiB synthetic file made **0 children**
  in 22 s; a 13 MiB one 11 children in 58 s. 203 of the 952 instances are
  over 25 MiB, so their 1800 s runs would measure Python overhead rather than
  the algorithm.

## 2. Principle: twins, same decisions

As `impl: v2` (MEMETIC_IMPL_V2.md) and B5 (the C polish core) did:
- **Control flow and every random draw stay in Python** (`random.Random`,
  `PortableRng` seeds per polish call). Only **deterministic** data work moves
  to C: parsing, tables, fitness, partition crossover, the clause-aware
  crossover, the hard-clause guard, conversions. No C function draws a random
  number, so the random stream is unchanged by construction.
- Every C structure has the **same element order** as its Python twin, because
  orders decide ties (occurrence lists, clause variable lists, neighbour
  lists, components).
- **Proof by tests:** for each replaced function, a test compares the C result
  with the Python one on many instances (both WCNF formats, weighted, hard,
  repeated and opposite literals, empty and unit clauses). End to end, a
  memetic run with `max_gens` (no binding time limit) must give the same best
  assignment, children, flips and target hit with the compiled path as with
  the Python path.
- **What it does not keep:** time. Under a time limit the compiled path does
  more per second, so seconds are comparable only within one version, the
  same caveat as v2 and B5. The whole MSE 2026 batch runs on one version.
- **Switch:** `ls.native: true` (already in `auto.yaml`) selects the compiled
  path; with `false` everything stays the Python code it is today.

## 3. Literature [verified: web 2026-10-28; mapping = inference]

| technique | source | used here |
|---|---|---|
| clauses packed in one region, 32-bit references | MiniSat region allocator (`mtl/Alloc.h`); 32-bit clause references in later solvers | §4 C1: CSR arrays (`lits` int32, offsets int64) |
| configuration checking without neighbour lists | CSCC (Luo, Su, Cai 2012), DCCASat (AAAI 2014) | already: lean tables (LONG_CLAUSE_RULE_DESIGN.md) give the same CC state; kept, now built in C |
| compute scores when needed instead of caching | separated non-caching WalkSAT (arXiv 1510.07217); probSAT caching (Balint & Schöning 2012) | C2: fitness and PX costs computed on demand from the CSR arrays, no per-clause Python state |
| partition crossover on the differing variables only, linear time | PXSAT (Chen, Whitley, Tinós, Chicano, GECCO 2018) | C2: PX in C over the D-variables (BFS on `nbrs`, or union–find on the clauses when lean) |
| preprocessing to shrink instances | MaxPre (Korhonen et al., SAT 2017) | not used (changes the instance); our kernel stays as it is |
| 1 byte (or bit) per variable per individual | general GA practice | C2: assignments as `bytearray` |

None of these sources measures memory for a memetic MaxSAT solver; they are
design techniques.

## 4. Inventory: every optimisation [plan; status in §8]

| # | what (today) | replacement | effect | equality test |
|---|---|---|---|---|
| C1.1 | `WCNF.parse_dimacs` → `Clause` objects + `pos_adj`/`neg_adj` | C parser `wcnf_parse` (both formats, same rules and errors) into CSR arrays held by `CompactWCNF` | 20× → ~1.2× file; ~50× faster | clause-for-clause equal on all local instances + synthetic edge cases |
| C1.2 | `CompactWCNF.clauses` | lazy read-only view: a `Clause` built on access (paths not yet ported keep working) | no list of m objects | same values as the parser's |
| C1.3 | `pos_adj`/`neg_adj` | built on first access only (kernel screen uses counts → C) | 0 unless asked | equal lists |
| C1.4 | `_Static` + `_V3Static` + NativeCore flatten | tables built in C from the CSR arrays: occ (ci, d), cvd, nbrs or lean aocc/cv, weights with the `weight or 1` rule | 49× → ~4–6× | arrays equal to the Python tables, element by element |
| C1.5 | once-per-run Python passes: total soft weight, JW priors, `screen_frac`, `_soft_stats`, `max_len`, `nbrs_plan` bound, `score_assignment`, final satisfied counts | C functions on the arrays | minutes → seconds on GiB files | equal values (floats: same summation order) |
| C2.1 | `Individual.assign01` as `list[bool]` (8 B/var) | `bytearray` (1 B/var); copies, hashing and polish marshal without Python loops | 8× less per member; O(n) Python → memcpy | same hashes (`hash_assign` hashes the same bytes) |
| C2.2 | `evaluate_assignment` (Python loop over clauses) per child | C `eval` → (soft weight, hard violations) | ~100× per child | equal on random assignments |
| C2.3 | `partition_crossover` + `px_components` | C, same component numbering and per-component costs | O(D-clauses) in C | equal child, q, flag |
| C2.4 | `clause_aware_crossover1_v2` (fallback) | C, same rule (no random draw is reachable) | O(n + hard occ) in C | equal child |
| C2.5 | `init_hard_satisfied` per child + `_guarded_flip` | C on a per-child byte array | O(hard lits) in C | same flips/refusals |
| C2.6 | walk mutation neighbour lookup (`nbrs[v]`, `lean_neighbour`) | C accessors; the random draws stay in Python, in the same order | no Python neighbour lists | same flips |
| C3.1 | hard mode: `SoftView` (Python tuples of soft clauses), `cost`/`unsat` per move | C on the CSR soft part | O(soft lits) in C per move | same lists, same order |
| C3.2 | Glucose loading (`_hard_clause_lists`) | fed from the arrays clause by clause (no list of lists) | no Python copy | same solver input |
| C4 | measurement | memory model and parse rate re-measured; new bins for 3c | — | — |
| (C5) | `kernelize` (Python dict of clause tuples) | only if a large instance passes the screen in practice; not planned now | — | — |

## 5. Milestones (one per turn; tests + smoke each)

1. **C1:** compact instance, C parser, C tables, once-per-run C passes;
   NativeCore built from the C tables. Python paths not yet ported read the
   lazy view.
2. **C2:** bytearray assignments and the per-child C functions; end-to-end
   twin test of whole memetic runs.
3. **C3:** hard mode (SoftView, Glucose feeding).
4. **C4:** re-measure memory and speed on the same files as §1, a real MSE
   file per size band where we have one, and synthetic files up to the
   workstation limit; new memory model, bins and Slurm time for 3c.
   Then 3c (`MSE26_RHO_PLAN.md`).

## 6. Risks and limits [inference]

- **Kernel on a large instance.** `kernelize` stays in Python; if a GiB-size
  instance passes the screen (≥ 20 % pure or 1+1 variables), the kernel build
  can need Python-level memory again. Watched at C4; C5 if it happens.
- **Glucose (hard mode)** keeps its own copy of the hard clauses (C++, a few
  bytes per literal) and its loading is a Python loop over clauses, inside the
  run clock (as today).
- **JW seeding** draws one `rng.random()` per variable per member in Python
  (it must, to keep the stream): pop 40 × n = 10M is ~40 s, outside the
  budget (as today).
- **Population cache** (`hash → fitness`) grows with the children; small for
  big instances, which make few children.
- **Weights:** C uses int64. The largest published MSE 2026 optimum is
  7.8·10¹⁴; the parser refuses a total soft weight that would overflow.
- **Pathological text** (e.g. `int("5_0")`, which Python accepts): the C
  parser rejects what is not a plain integer; no MSE file is expected to
  contain such tokens (counted at C1 on the 952 via the cluster job's awk
  counts matching).

## 7. What stays the same

The algorithm (`impl: v3`), `auto_hparams/3`, the kernel gate and its
decisions, every random draw, the shard record (schema 7), the batch config
(`configs/strong/auto.yaml`).

## 8. Build log

### C1 — compact instance (built 2026-10-28) [verified: tests + twin check]

**What was built** (tree `cluster_staging_maxsat_strong/`):

| file | change |
|---|---|
| `src/native/ls_core.c` | new section "compact instance": `wcnf_parse` (both formats, Python's rules; getline streaming, growable arrays shrunk at the end), `wcnf_from_arrays`, `inst_nbrs_bound`, `inst_tables` / `inst_tables_free` (occ, cvd, nbrs or lean aocc/cv, static weights with `weight or 1`, total soft), `inst_counts`, `inst_soft_wsum_f`, `inst_screen`, `inst_jw` (exact 2^-k), `inst_eval`. No libm. |
| `src/native/native.py` | `_CInst`, argtypes; `NativeCore.from_compact` (tables built in C, freed with the core); `load_native` picks it for a compact instance (mode by ls_v3's own rule on the C bound). |
| `src/sat/compact.py` | **new.** `CompactWCNF` (`clauses` view, lazy `pos_adj`/`neg_adj`, C passes), `load`, `from_wcnf`. |
| `src/evo/population.py`, `src/evo/memetic.py`, `src/evo/v3.py`, `src/sat/kernel.py`, `src/evo/auto_hparams.py`, `src/sat/ls_v3.py`, `src/cli/run_memetic_shard.py` | the once-per-run passes call C for a compact instance (JW priors, evaluation, total soft weight, final counts, hard-mode test, screen, max length, soft stats, nbrs bound, instance stats, scoring). |
| `src/cli/run_memetic_shard.py` | `ls.native: true` parses with the C parser (and compacts the kernel); `MAXSAT_COMPACT=0` keeps the Python instance; record field `compact_instance` (schema 7, additive). |
| `scripts/compact_check.py` | **new.** Twin check of parse, tables (full + lean) and passes, per file. |
| `tests/test_compact.py` | **new.** 42 tests. |

**Divergences on malformed input only** (both refuse, or C refuses what
Python accepted silently): a literal token that is 0 but not `"0"` (e.g.
`00`) in the legacy format; integers outside int64 / variable indices
outside int32; underscores in integers (`int("1_0")`); invalid UTF-8.

**Equality [verified]:**
- `tests/test_compact.py`: 13 accepted edge-case files (legacy with/without
  top, upper-case `P WCNF`, CNF, CRLF, empty clause, `0` lines, top = 2^63−1;
  new format with tabs, `+3`, weight 0, soft-less, no p line) equal clause for
  clause; 10 malformed files refused by both; random instances with repeated
  and opposite literals (both formats): tables and passes equal; 5 local
  instances; **whole memetic runs identical** (soft unweighted, soft weighted,
  hard; with and without a target; best assignment, children, generations,
  flips, target hit, v3 and hard counters); shard records equal with
  `MAXSAT_COMPACT=0` and `=1`.
- `scripts/compact_check.py` on **every local file (708: MSE 2023/2024, SATLIB, generated Max-2-SAT/3-SAT, unsat sets): 0 mismatches** (parse, tables full + lean, every pass).
- Full suite: 481 passed, 16 skipped.

**Memory after C1 alone** (`auto.yaml`, 20 s): ja-kemeny 5 MiB 440 → 517 MB,
synthetic 13 MiB 1,244 → 1,296 MB. **No gain yet, +5–17 %:** partition
crossover, walk mutation and the hard-clause guard still read the Python
tables (`_Static`, `_V3Static`, `pos_adj`), which are now built from the
clause view in addition to the C tables. C2 moves those readers to C; the
Python tables are then never built on the native path.

### C2 — per-child functions (built 2026-10-28) [verified: tests + measurements]

**What was built:**

| file | change |
|---|---|
| `src/native/ls_core.c` | section "per-child functions": `px_cross` (union–find on nbrs or the lean clause walk; ids by smallest variable; costs over the clauses first reached through each component, static weights), `hard_build`/`hard_free` (`HardTab`: soft proxy scores, hard clause list, ± occurrence lists with multiplicity, guard occurrences), `xo_cross` (clause-aware crossover; the `rng.choice` branch is unreachable), `hard_sat_init`, `hard_guarded_flip`. |
| `src/native/native.py` | `_HardTab`, `u8()` (bytearray without copy), argtypes; polish takes a 1-based bytearray and works in place (`final_buf`), no O(n) list conversion. |
| `src/sat/compact.py` | `hard_tab`, `xo_cross`, `hard_satisfied`, `guard` → `HardGuard.flip`. |
| `src/evo/population.py` | `bytes_assign` (seeds as bytearray), `hash_assign` fast path (same bytes), C `hard_satisfied`. |
| `src/evo/memetic.py` | compact: bytearray members, C guard instead of Python hard-clause lists, conversions after Glucose repair / moves, end-of-run exports without the O(n) round trip. |
| `src/evo/v3.py` | `partition_crossover` → `px_cross`; `_guarded_flip` → `HardGuard`; walk mutation reads the C tables (`_CTables`); polish in place. |
| `src/evo/impl_v2.py`, `src/sat/ls_v3.py` | clause-aware crossover → `xo_cross`; `init_dynamic_weights` and `nbrs_info` from the C tables. |
| `tests/test_compact.py` | +26 tests (68 in the file). |

The random draws are untouched: every `rng` call is where it was, in Python.

**Equality [verified]:** whole memetic runs identical (Python instance vs
compact; best assignment, children, generations, flips, target hit, v3 and
hard counters) for soft and hard instances × {default, lean tables, every PX
falling back to clause-aware, PX fallback "mutate_only", clause-aware
crossover, count mutation, diff mutation, run-level weights, WalkSAT core
with tenure tabu, lean + walk}; direct twins of PX, clause-aware crossover and
the guard (flip, refusal, hsat) on random parents in full and lean mode.
Full suite: **507 passed, 16 skipped.**

**Measured (`auto.yaml`, 30 s budget, workstation):**

| file | MiB | peak RSS before (×) | after C2 (×) | children in 30 s before → after | overshoot past budget |
|---|---:|---:|---:|---:|---:|
| ja-kemeny (MSE 2024) | 5.0 | 440 MB (88×) | 97 MB (19.6×) | 20 → 26 | 0.0 s |
| correlation-clustering (MSE 2024) | 4.8 | 456 MB (94×) | 100 MB (20.6×) | 7 → 9 | 0.0 s |
| synthetic, 30 % hard | 12.4 | 1,244 MB (100×) | 261 MB (21.1×) | 0* → 8 | 0.3 s |
| synthetic | 25.8 | 2,568 MB (100×) | 529 MB (20.5×) | 0 → 6 | 0.6 s (was 14.7 s) |
| synthetic | 52.2 | out of memory at 3.5 GB | 1,025 MB (19.6×) | — → 4 | 2.1 s |

(*13 MiB before: 0 children at 20 s.)

**Where the remaining ~20× goes** (52 MiB synthetic, 30 % hard): CSR 1.0×,
C tables (full) 4.5×, HardTab 0.6×, **SoftView 6.2× (Python tuples of every
soft clause), Glucose loading 4.0×**, the rest per-call buffers and the
population. The two hard-mode items are C3.

### C3 — hard mode (built 2026-10-28) [verified: tests + measurements]

**What was built:**

| file | change |
|---|---|
| `src/native/ls_core.c` | section "hard-mode helpers": `soft_unsat` (unsatisfied soft indices), `soft_index`, `soft_unit_sat` (the keep-sat literals), `u8_hamming`. |
| `src/sat/compact.py` | `CSoftView` (SoftView's cost / unsat / unit literals; the scans in C, the weight sums in Python's `sum()` over the same floats in the same order, so the result does not depend on the Python version's float summation), `HardClauses` (the hard clauses streamed one list at a time), `hamming`. |
| `src/evo/hard.py` | Glucose bootstrapped from `HardClauses` (pysat adds clause by clause, so the solver gets the same clauses in the same order), keep-sat literals from `unit_sat_lits`, repair's Hamming distance in C. |
| `src/evo/memetic.py` | `CSoftView` for a compact instance. |
| `tests/test_compact.py` | +6 tests (74 in the file); `tests/test_target_hit.py`: one 3b assertion made timing-robust (a hard-mode hit may come before the polish). |

**Equality [verified]:** SoftView vs CSoftView on random assignments, with
and without singleton cores / set-aside clauses (cost, unsat list, keep
literals); hard clause stream equal to `_hard_clause_lists`; whole hard-mode
memetic runs identical with SAT moves and keep_sat none / ks / ks2 (moves,
Glucose calls, keep-sat calls, repair Hamming sums compared). Full suite:
**513 passed, 16 skipped.**

**Measured** (`auto.yaml`, 30 s; all four in hard mode):

| file | MiB | original | after C2 | after C3 | children in 30 s (orig → C3) |
|---|---:|---:|---:|---:|---:|
| ja-kemeny (MSE 2024) | 5.0 | 440 MB (88×) | 97 MB (19.6×) | 84 MB (16.8×) | 20 → 24 |
| synthetic, 30 % hard | 12.4 | 1,244 MB (100×) | 261 MB (21.1×) | 181 MB (14.6×) | 0 → 8 |
| synthetic | 25.8 | 2,568 MB (100×) | 529 MB (20.5×) | 371 MB (14.4×) | 0 → 7 |
| synthetic | 52.2 | > 3.5 GB (OOM) | 1,025 MB (19.6×) | 704 MB (13.5×) | — → 5 |

Static breakdown (52 MiB): CSR 1.0×, C tables 4.5×, HardTab 0.6×,
CSoftView 0×, Glucose 3.8× (its own clause database), total 10.1×; the rest
of the peak is per-call buffers, the population and pysat's per-call phase
and model lists. **Parse:** C 213 MB/s vs Python 5.7 MB/s (55 MB file:
0.26 s vs 9.5 s).

**Left in Python, per SAT call (hard mode only):** pysat's `set_phases` /
`get_model` take and return Python lists of n literals, an O(n) Python loop
per call; it is the pysat API, kept.

### C4 — memory model, bins, time (measured 2026-10-28) [verified: measurements; bins = model]

**Peak RSS on the compact path** (`auto.yaml`, 30 s, workstation):

| file | MiB | type | peak RSS | × file | children |
|---|---:|---|---:|---:|---:|
| synthetic soft-only | 12.5 | soft | 128 MB | 10.2× | 59 |
| synthetic soft-only | 52.4 | soft | 444 MB | 8.5× | 58 |
| synthetic 30 % hard | 12.4 / 25.8 / 52.2 | hard | 181 / 371 / 704 MB | 14.6 / 14.4 / 13.5× | 8 / 7 / 5 |
| ja-kemeny (MSE 2024) | 5.0 | hard | 84 MB | 16.8× | 24 |
| setcover rail507 (lean tables) | 2.9 | hard | 75 MB | 25.6× (base-dominated) | 43 |
| calib_2sat_sc2 s258 (kernel) | 1.1 | kernel | 67 MB | 59.8× (base-dominated) | 5,684 |
| synthetic sparse Max-2-SAT (kernel passes, screen 0.65) | 43.7 | kernel | 1,399 MB | 32.0× | **0** |

**Model (upper envelope):** soft 9 × MiB + 100 MB; hard 14 × MiB + 120 MB;
kernel 33 × MiB + 100 MB. Largest MSE 2026 file (3,439 MiB): hard 47 GB,
kernel 111 GB.

**Bins for the 952** (larger of the EvalMaxSAT-published bin and ours, 75 %
rule): without the kernel 8 GB 870, 16 GB 20, 32 GB 20, 64 GB 42 — all fit,
and EvalMaxSAT's published peak now decides every bin. If every instance
kernelised (worst case): 13 do not fit 64 GB.

**The kernel is the one part left in Python, and it can't be made a twin
[verified in code]:** `kernelize` takes variables from a work list filled
in Python `set` iteration order, and that order decides which eliminations
happen and the kernel's clause order. On the 43.7 MiB synthetic file it used
31 s (the whole 30 s budget; 0 children) and 32× memory. At 0.7 s/MiB a
1 GiB instance that passes the screen would spend ~12 min of its 30 in the
kernel. How many large MSE 2026 instances pass the screen is unknown
(needs the files). Decision for the user (§9).

**Time per task:** C parse 213 MB/s and sha256 ~0.5 GB/s, outside the
budget; tables, kernel gate and hparams inside it. Overshoot past the budget
measured ≤ 2.1 s at 52 MiB (was 15 s at 26 MiB before C2). Proposal for 3c:
`--time=01:00:00` for every bin (1,800 s + grace + parse + margin) and
GRACE 300 s (the watchdog fires only on a stuck run; the readout checks 300
instead of 60).

## 9. The MSE 2026 census job (prepared 2026-10-28; user: "do option 1, prepare the census job")

**Why:** the kernel gate is the one Python step left (§8 C4), and whether a
large MSE 2026 instance passes its screen is unknown. The census answers that
on the real files, and on the way it checks the C parser on all 952 (it has
never seen them) against the unpack job's awk counts and content hashes, and
gives the exact clause / literal / variable counts for the memory bins.

**What it does:** `scripts/mse26_census_array.sbatch`, 50 tasks (the
byte-balanced packing of `scripts/mse26_work.tsv`, as the unpack job), 8 GB,
1 h limit; one Python process per instance
(`scripts/mse26_census.py`) writing one row to
`results/mse26_census/rows/<hash>.tsv`:
- content sha256, bytes; n_vars, clauses, literals, hard / soft, soft weight
  sum and max, max clause length, weighted; v3 neighbour bound and mode;
- the screen (hit / occurring / fraction);
- when the screen passes (≥ 0.20) and the file is ≤ 100 MiB: the gate itself
  (`kernel` / `kernel_empty` / `skipped_gain` / `skipped_length` /
  `skipped_infeasible`, kernel size, gain, seconds); larger screen-passing
  files are marked `not_run_size` (the Python kernel needs ~33× the file);
- parse seconds; peak RSS after the parse and at the end; an error column.

A rerun skips rows already written. `scripts/mse26_census_finish.sh` (login
node, shell only) lists the tasks still missing a row, or merges
`results/mse26_census/mse26_census.tsv` (952 rows) and prints `ALL_DONE`.

**Tested** on a mock tree (4 local instances under fake MSE 2026 paths, one
kernelising Max-2-SAT file: kernel 332 variables as in earlier runs; a missing
file → `TASK_FAIL` with the rerun line; rerun skips written rows; finish
`MISSING`/`INCOMPLETE`; Python tripwires on PATH not triggered).

**Upload:** `tmp/upload_census/` (44 files: 41 tree files as `cen__*`,
`UPLOAD_MAP_census.tsv`, `arrange_census.sh`, `upload.sha256`). It carries the
whole `src/` of 9ce84ca (3b counter + C1–C3) plus the census files; the
arrange script moves every file to its tree path (NEW / SAME / REPLACE, old
copy kept as `.bak_pre_census`), checks
`scripts/census_mse26.upload.sha256`, the C source and the `data/raw/mse26`
link, and on success removes its map, `~/upload.sha256` and itself. Mock-tested
against the tree of `2d63a21`: new 6, same 25, replace 11; afterwards `~`
holds nothing from the upload and `src/` equals the workstation's.

```bash
# login node, after uploading tmp/upload_census/* into ~
cd ~ && sha256sum -c upload.sha256                # 44 x OK
bash arrange_census.sh                            # dry run: NEW / SAME / REPLACE list
bash arrange_census.sh --apply                    # CENSUS_UPLOAD_OK, C source, link; removes map + itself
cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs
B=$(sbatch --parsable build_native.sbatch | tail -1)
sbatch --dependency=afterok:$B mse26_census_array.sbatch
squeue -u $USER                                   # wait until empty
cat logs/build-native-$B.out                      # BUILD_OK
cd .. && bash scripts/mse26_census_finish.sh      # CENSUS 952 rows, 0 with an error; ALL_DONE
```

**Bring back** to `cluster_staging_maxsat_strong/results/mse26_census/`:
`mse26_census.tsv` (and `scripts/logs/mse26-census-*` if any task failed).

**Then (workstation):** compare with `mse26_content.tsv` (sha256, hard /
soft counts); list the screen-passing instances by size; the kernel rule for
3c (user's decision, with the numbers); exact memory bins; then the 3c
manifest.
