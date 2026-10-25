# Batch PP10: the polish's share of each slot, `hard.moves.per_polish` {200, 10}, on 24 MSE instances (2026-10-25)

> "prepare now per polish 10 with flat upload" (user, 2026-10-25)

**Tree:** `cluster_staging_maxsat_strong/`. **Builder:**
`scripts/make_perpolish_manifest.py`. **Motivation:** the rail probe
(`LONG_CLAUSE_RULE_DESIGN.md` §9). **Plan:** `NOTES_2026-10-21_AGENDA_AND_STATS.md`
§1. **Note:** N-2026-10-25-a.
**Status:** prepared and verified, not committed, not uploaded, not
submitted.

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
MAXSAT_GIT_SHA=<commit> MANIFEST=manifest_perpolish.tsv OUTDIR=results/perpolish/tasks bash submit_m2_memetic.sh
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

## 5. Pre-registered reading (proposal, to confirm before submission)

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
   - **Then:** rule R5 of `auto_hparams` (`/3`) sets `per_polish` 10 on
     every instance with hard clauses.
2. **Otherwise, if `pp10` is better on ≥ 2 of the 3 rail instances and worse
   on none:**
   - a rail-only rule R5′, "lean tables → `per_polish` 10".
3. **Otherwise:** no rule. Report the result.

**Either rule waits for the readout and the user's go.**

**Diagnostics:**
- children per run;
- polish flips against move time;
- ks hit rate;
- peak memory from `sacct`.

**Consistency check (not part of the decision):** on p01–p16, `pp200` uses
the settings of KS2's `ks2_10` arm, under newer code that is identical
outside rail. Its success counts should be close to KS2's (26/48). Runs stop
by wall clock, so they will not be byte-equal.
