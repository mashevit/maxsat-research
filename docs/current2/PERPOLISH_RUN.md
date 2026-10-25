# Batch PP10: the polish's share of each slot, `hard.moves.per_polish` {200, 10}, on 24 MSE instances (2026-10-25)

> "prepare now per polish 10 with flat upload" (user, 2026-10-25)

**Tree:** `cluster_staging_maxsat_strong/`. **Builder:**
`scripts/make_perpolish_manifest.py`. **Motivation:** the rail probe
(`LONG_CLAUSE_RULE_DESIGN.md` §9). **Plan:** `NOTES_2026-10-21_AGENDA_AND_STATS.md`
§1. **Note:** N-2026-10-25-a.
**Status:** committed and pushed 2026-10-25 as `2763872`; uploaded, arranged, C core rebuilt (BUILD_OK) and **submitted and read 2026-10-25** (§6): general R5 not met (non-rail 5 better / 12 worse; successes 19 vs 25 of 63); rail-only R5′ met (3/3; rail gap +71 % → +15 %).

## 1. Why [verified: workstation, LONG_CLAUSE_RULE_DESIGN.md §9]

- With hard clauses, each 3.5 s slot first runs up to `per_polish` SAT moves
  (default 200), then the B1–B5 polish.
- On setcover rail the moves filled every slot, and the polish never ran.
- At `per_polish` 10 (seed 1, 60 s), the cost fell from 513/603/654 to
  218/216/265. The best-knowns are 174/182/211.
- **Open:** whether that holds at 900 s, and whether 10 helps or hurts on
  the other MSE families. KS2 and HMSE both ran with 200.

## 2. Batch [verified: built, `--check`, dry checks]

**Arms:** these are the only difference between runs.

| arm | config | `hard.moves.per_polish` |
|---|---|---:|
| `pp200` | `configs/strong/perpolish_pp200.yaml` | 200 (today's default, explicit) |
| `pp10` | `configs/strong/perpolish_pp10.yaml` | 10 |

- **Everything else** is `configs/strong/auto.yaml`: B1–B5, the kernel gate
  and `hparams: auto` (`auto_hparams/2`).
- **R4 applies in both arms.** Every instance has hard clauses, so pop is 10
  and `keep_sat` is ks2. The deep merge keeps `per_polish` (smoke, §3).
- **The lean-table code (`7c5ecc8`) runs in both arms.** Only rail resolves to
  lean. The other 21 instances build the full tables, exactly as before.

**Runs:**
- 24 instances × 2 arms × seeds 1–3 = **144 tasks**;
- 900 s each, stop at the target;
- 1 CPU, 8 GB, `--time 00:20:00`.

**Job ids and output:** `pp_<arm>_<pNN>_s<seed>`, written to
`results/perpolish/tasks`.

**Cost:**
- worst case 144 × 960 s = **38.4 CPU-h**;
- one wave at `%1000`.

**Instances:**

| p | group | source id | instance | target | kind |
|---|---|---|---|---:|---|
| p01–p16 | ks2 | k01–k16 | the 16 KS2 instances (`KS2_CHECK_RUN.md` §2) | optimum | proven (EvalMaxSAT) |
| p17 | rail | rail507 | setcover_wt-rail507 (24) | 174 | best-known |
| p18 | rail | rail516 | setcover_wt-rail516 (24) | 182 | best-known |
| p19 | rail | rail582 | setcover_wt-rail582 (24) | 211 | best-known |
| p20 | hmse | h003 | decision-tree heart-cleveland atleast_15 (23) | 31 | best-known |
| p21 | hmse | h047 | logic-synthesis normalized-test4.pi (23) | 94 | best-known |
| p22 | hmse | h011 | inconsistency-measurement im-forgetting-B-2-stb_625_161 (23) | 79 | best-known |
| p23 | hmse | h100 | decision-tree primary-tumor atleast_31 (24) | 108 | best-known |
| p24 | hmse | h095 | correlation-clustering Protein4 N360 (24) | 15,658,391 | best-known |

- **How the 5 HMSE picks were chosen** (notes §1): each comes from a weak HMSE
  family and is the instance whose median-run gap is closest to its family's
  median.
- **Rail targets** are from the MSE 2024 table (`bestknown_mse24.csv`).
- **The builder checks** each instance's sha256 against its source list and
  refuses duplicates.

## 3. Smoke [verified: workstation, real shard runner, C core, 20 s, one at a time, `ulimit -v` 6 GB]

Records are in `tmp/smoke_perpolish/`.

| job | nbrs | peak RSS | cost at 20 s | target | children (PX calls) |
|---|---|---:|---:|---:|---:|
| pp_pp10_p13_s1 (lisbon-wedding) | full | 374 MB | 400 | 395 | 67 |
| pp_pp200_p13_s1 (lisbon-wedding) | full | 374 MB | 402 | 395 | 6 |
| pp_pp10_p17_s1 (rail507) | lean (B 768.6M) | 289 MB | 229 | 174 | 21 |

- **All `ok` and feasible (hv 0).**
- **The settings reached the solver:**
  - the record's config holds `hard.moves.per_polish` 10 or 200;
  - `hparams.overrides` holds pop 10 and keep_sat ks2 (R4).
- **`m2_results.py pending` reads the manifest and sidecar.** The only
  mismatch on the smoke records is the expected one: `budget_s` 20 against
  900.
- **Tests:** the strong-tree suite gives 403 passed, 16 skipped. `src/` is
  unchanged since `7c5ecc8`.

## 4. Upload (flat, without rsync) and commands

**What the cluster lacks:**
- `make_flat_upload.py` was run with these `--have` lists, all verified on the
  cluster:
  - the first U30/HMSE `UPLOAD_MAP.tsv`, which carries the 3 rail files;
  - `097efb7` O900 and KS2;
  - `0877898` U30 and HMSE.
- **Result:** 15 files, 0.2 MB, in `tmp/upload_pp10/`. 62 of the 76 needed
  paths are already on the cluster.
  - **code (the lean tables):** `src/evo/memetic.py`, `src/evo/v3.py`,
    `src/native/ls_core.c`, `src/native/native.py`, `src/sat/ls_v3.py`;
  - **the 2 configs;**
  - **the manifest files**, the instances CSV, the builder and
    `make_flat_upload.py`.
- **Every name starts `pp10__`,** so nothing in `~` can be overwritten. The
  map is `UPLOAD_MAP_pp10.tsv`, and the arrange script is `arrange_pp10.sh`.

**The arrange script** (`tmp/upload_pp10/arrange_pp10.sh`, shell only):
- It refuses `--apply` while any of your Slurm jobs is queued or running,
  because jobs read `src/` at run time. `FORCE=1` overrides.
- It keeps each replaced file as `<path>.bak_pre_pp10`.
- It checks `manifest_perpolish.upload.sha256` (`PP10_OK`), the 144 lines,
  and the lean C source.
- It was tested on a mock of the cluster tree: the tree's needed files, with
  the 5 code files taken from `0877898`. With `python`/`python3` tripwires on
  PATH, it gave new 10, replace 5, `PP10_OK`, and the tripwire never fired.

**The `.so` must be rebuilt.** `ls_core.c` changed. A stale build is refused
by `native.build_info()`, so a job submitted before the rebuild exits 2. It
never runs on mixed code.

On the login node (shell only), after dropping all 17 files of
`tmp/upload_pp10/` into `~`:

```bash
squeue -u $USER                       # must be empty
bash arrange_pp10.sh                  # dry run: expect new 10, replace 5, bad 0, missing 0
bash arrange_pp10.sh --apply          # expect PP10_OK, "PP10 manifest: 144 tasks"
cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs
sbatch build_native.sbatch
cat logs/build-native-*.out           # the newest one: expect BUILD_OK
DRY_RUN=1 MANIFEST=manifest_perpolish.tsv OUTDIR=results/perpolish/tasks bash submit_m2_memetic.sh   # --array=1-144%1000
MAXSAT_GIT_SHA=2763872 MANIFEST=manifest_perpolish.tsv OUTDIR=results/perpolish/tasks bash submit_m2_memetic.sh
```

**Also on the login node: the memory of the last arrays.** This is the
open RAM-audit item, and it is shell only:

```bash
sacct -j 23475119,23475734 --format=JobID%20,MaxRSS,Elapsed,State -n | sort -k2 -h | tail -15   # HMSE, U30
sacct -j <pp10 jobid> --format=JobID%20,MaxRSS,Elapsed,State -n | sort -k2 -h | tail -15        # after PP10
```

**Back on the workstation:**

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
# copy ~/cluster_staging_maxsat_strong/results/perpolish/ to results/perpolish/
python3 scripts/m2_results.py pending --manifest scripts/manifest_perpolish.tsv --outdir results/perpolish/tasks --summary
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_perpolish.tsv --outdir results/perpolish/tasks
```

## 5. Pre-registered reading (confirmed by the user, 2026-10-25: "the decision rule is fine, confirmed")

**Per instance and arm:**
- successes / 3 (target reached);
- median final cost and gap to the target;
- median TTT, where a run that misses counts as > 900 s.

**"Better", instance by instance, as in KS2:**
1. more successes; else
2. a lower median final cost; else
3. a lower median TTT.

Otherwise the instance is a tie.

**The decision** (user, 2026-10-21: "if 10 doesnt win do it rule like 3"):
1. **"10 wins broadly"** means: on the 21 non-rail instances (KS2 16 + HMSE
   5), `pp10` is better on **≥ 8** and worse on **≤ 2**. This is KS2's
   ≥ 6/16 and ≤ 2/16, scaled to 21.
   - **Success gate (user, 2026-10-25, set before any result was seen):**
     "if there are not enough got to optimum I dont want general rule 10
     instead 200". On the same 21 instances, `pp10` must also:
     - reach the target in **more runs in total** than `pp200` (out of 63
       each); and
     - have fewer successes than `pp200` on **at most 2** instances.
     Wins on cost or time alone cannot carry the general rule.
   - **Then:** rule R5 of `auto_hparams` (`/3`) sets `per_polish` 10 on
     every instance with hard clauses.
2. **Otherwise** (including when only the success gate fails), **if `pp10`
   is better on ≥ 2 of the 3 rail instances and worse on none:**
   - a rail-only rule R5′, "lean tables → `per_polish` 10".
3. **Otherwise:** no rule. Report the result.

**Either rule waits for the readout and the user's go.**

**`sacct` gives no memory on this cluster** (2026-10-25): for HMSE/U30
(23475119, 23475734), MaxRSS is blank on every step, `.batch` included, and
only Elapsed and State are filled. No memory measurement is wanted
(user, 2026-10-25): run at 8 GB and rerun any task that dies for a system
reason with more `--mem` (notes §14).

**Diagnostics:**
- children per run;
- polish flips against move time;
- ks hit rate;
- peak memory from `sacct`.

**Consistency check (not part of the decision):** on p01–p16, `pp200` uses
the settings of KS2's `ks2_10` arm, under newer code that is identical
outside rail. Its success counts should be close to KS2's (26/48). Runs stop
by wall clock, so they will not be byte-equal.

## 6. Readout (2026-10-25) [verified: 144 shard records]

**Run:**
- submitted 2026-10-25 11:01 UTC, `MAXSAT_GIT_SHA=2763872`;
- the recorded src digest `6a1e4a8c…` equals the workstation's;
- the C core was rebuilt on the cluster (BUILD_OK);
- results are in `results/perpolish/`, aggregates in `results/perpolish/agg/`.

**Integrity:**
- 144/144 `ok`, all feasible (hv 0), none below its target;
- maximum wall time 910 s;
- 44 runs reached the target, 100 hit the time cap;
- rail ran lean (18 runs), every other instance full;
- `aggregate` flags 7 runs with cpu/wall < 0.9 (node contention): p01 and
  p04 in `pp200`, p11 in `pp10`. All 7 reached the target.

**Per instance.** Each cell gives successes / 3, the final costs of seeds
1–3, and the median TTT in s when at least 2 of 3 runs succeeded. The last
column is `pp10` against `pp200` under the §5 order.

| p | group | instance | target | pp200 | pp10 | children 200 / 10 | pp10 vs 200 (by) |
|---|---|---|---:|---|---|---|---|
| p01 | ks2 | bcp-SU3 | 106 | 3/3, 30 s | 3/3, 50 s | 11 / 419 | worse (TTT) |
| p02 | ks2 | gen-hyper-tw b01 | 5 | 6, 7, 7 | 6, 6, 7 | 4,620 / 6,860 | better (cost) |
| p03 | ks2 | inconsistency-measurement contension | 63 | 64, 64, 65 | 64, 67, 68 | 925 / 16,597 | worse (cost) |
| p04 | ks2 | ja-maxham | 37 | 2/3, 24 s | 2/3, 22 s | 2 / 7 | better (TTT) |
| p05 | ks2 | mbd-b14 | 24 | 3/3, 19 s | 3/3, 26 s | 12 / 280 | worse (TTT) |
| p06 | ks2 | min-fill myciel5 | 196 | **3/3, 644 s** | 197, 203, 204 | 178 / 2,738 | **worse (successes)** |
| p07 | ks2 | optimizing-BDDs | 87 | 89 ×3 | 89 ×3 | 2,065 / 9,571 | tie |
| p08 | ks2 | scheduling | 28 | **3/3, 36 s** | 2/3, 42 s | 9 / 143 | **worse (successes)** |
| p09 | ks2 | MaxSATQueries | 31,514 | 43,875 ×3 | 43,875 ×3 | 340 / 4,998 | tie |
| p10 | ks2 | af-synthesis | 117 | **2/3, 654 s** | 121, 122, 124 | 236 / 1,660 | **worse (successes)** |
| p11 | ks2 | causal-discovery | 91,349 | 3/3, 6 s | 3/3, 8 s | 3 / 29 | worse (TTT) |
| p12 | ks2 | ja-kemeny | 554 | 1/3 | 1/3 | 781 / 2,094 | tie |
| p13 | ks2 | lisbon-wedding 9-18 | 395 | 396 ×3 | 396, 397, 397 | 249 / 2,475 | worse (cost) |
| p14 | ks2 | metro | 138 | 1/3 | 1/3 | 124 / 513 | tie |
| p15 | ks2 | preference_planning | 257 | 1/3 | **2/3, 5 s** | 251 / 4 | **better (successes)** |
| p16 | ks2 | quantum-circuit qgan | 24 | **3/3, 25 s** | 2/3, 431 s | 19 / 3,334 | **worse (successes)** |
| p17 | rail | setcover rail507 | 174 | 285, 298, 324 | **200, 200, 204** | 250 / 766 | better (cost) |
| p18 | rail | setcover rail516 | 182 | 269, 271, 284 | **199, 199, 200** | 252 / 826 | better (cost) |
| p19 | rail | setcover rail582 | 211 | 334, 355, 373 | **241, 243, 246** | 251 / 733 | better (cost) |
| p20 | hmse | decision-tree heart-cleveland | 31 | 65, 67, 84 | 39, 50, 53 | 242 / 247 | better (cost) |
| p21 | hmse | logic-synthesis test4.pi | 94 | 107, 108, 113 | 104, 105, 107 | 614 / 4,336 | better (cost) |
| p22 | hmse | inconsistency-measurement forgetting | 79 | 83, 84, 84 | 88, 89, 95 | 934 / 6,862 | worse (cost) |
| p23 | hmse | decision-tree primary-tumor | 108 | 132, 148, 164 | 149, 160, 160 | 231 / 238 | worse (cost) |
| p24 | hmse | correlation-clustering Protein4 | 15,658,391 | 17.02M, 17.21M, 18.18M | 15.80M, 17.41M, 17.75M | 248 / 1,842 | worse (cost) |

**The pre-registered decision (§5):**

| test | needed | result | met |
|---|---|---|---|
| non-rail better / worse (21) | ≥ 8 / ≤ 2 | 5 / 12 (4 ties) | no |
| non-rail successes, of 63 | pp10 > pp200 | 19 vs 25 | no |
| instances where pp10 has fewer successes | ≤ 2 | 4 (p06, p08, p10, p16) | no |
| **general R5** | all three | | **no** |
| rail better / worse (3) | ≥ 2 / 0 | 3 / 0 | yes |
| **rail-only rule R5′** ("lean tables → per_polish 10") | | | **met** |

**On rail at 900 s:**
- `pp10` median costs are 200 / 199 / 243 against best-knowns of
  174 / 182 / 211, gaps of +15 / +9 / +15 %;
- `pp200` median costs are 298 / 271 / 355, gaps of +71 / +49 / +68 %;
- no run reached the best-known.

**Consistency check** (§5, not part of the decision): on p01–p16, `pp200`
reached the target in 25/48 runs, against KS2's `ks2_10` at 26/48 (same
settings, older code). Min-fill went from 1/3 to 3/3 and ja-maxham from
3/3 to 2/3. This is within the run-to-run spread of 900 s wall-clock runs.

**[inference] Reading:**
- On the KS2 instances, ks2's SAT moves do the work that reaches the
  optimum (KS2 §6).
- Cutting them to 10 per slot gives 10–300× more children, but loses
  successes on min-fill, af-synthesis, quantum-circuit and scheduling.
- Rail is the opposite case. At 200, the moves fill every slot and the
  polish never runs.
- The HMSE picks split 2 better (decision-tree h003, logic-synthesis) and
  3 worse, so there is no family-level pattern to build a rule on.
- Four verdicts are decided by TTT alone, with equal successes and seconds
  apart: worse on p01, p05 and p11, better on p04. They do not change the
  decision: counted as ties, the result is 4 better / 9 worse.

**Built 2026-10-25** (user: "yes build the rail-only rule"). It is
`auto_hparams/3`, rule R5 (`AUTO_HPARAMS.md`, N-2026-10-25-c). The plan was:
- It would add a rule to `auto_hparams` (`/3`): when the bound
  Σk(k−1) > 50M (the lean trigger), set `hard.moves.per_polish` = 10.
- Every other instance resolves exactly as under `/2`.
