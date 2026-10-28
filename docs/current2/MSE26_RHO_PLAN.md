# MSE 2026 ρ benchmark: unpack + hash job, manifest plan, memory, flip counter (2026-10-28)

**Created:** 2026-10-28. **Index:** `docs/current/RESEARCH_NOTES.md`,
N-2026-10-28-b. Earlier context: `MSE_PUBLISHED_EXACT_RESULTS.md` §5–§7,
`EVALMAXSAT_2026_INSTALL.md`.

> "unpack what you recommend, do manifests for also instances that where
> proved by exact solver in under 30s, later do per flip, or what you
> wanted to measure with memetic quick runs, only in the first several
> 12500 flips calls, or whatever the correspondig parameter, I dont need
> total calls of flips for runs above 10 or 25 seconds or 40 do the
> reasoning" (user, 2026-10-28)
>
> "initially give larger instances more ram, you can add if you find for
> statistics useful - ram check per run" (user, 2026-10-28)
>
> Disk: "ncdu reports that currently I use 17 gb out of 400 gb" (user,
> 2026-10-28; `du -sh ~` is not to be used).

## 1. Status

| milestone | state |
|---|---|
| 1. EvalMaxSAT 2026 install + smoke on the cluster | **done** (user, 2026-10-28) |
| download MSE 2026 | **done**: job 23591248, `~/mse_full26/`, census in `MSE_PUBLISHED_EXACT_RESULTS.md` §7 |
| 2. unpack + hash job (MSE 2026 only) | **done** 2026-10-28: array job 23643046, 50/50 `TASK_OK` (11:52–12:20), `ALL_DONE`; `results/mse26_unpack/mse26_content.tsv` (1,216 rows; 952 unpacked: 479 unweighted, 473 weighted; no duplicate content sha256; flags match `mse26_work.tsv`; no old-format `p` lines) + logs |
| 3a. EvalMaxSAT manifest (952 × 1 h) | **dropped** 2026-10-28 (user): ρ x from the published results (§7) |
| 3b. flip counter + per-run RAM in the memetic (§4, §5, §8) | **built + tested locally** 2026-10-28; goes to the cluster with the 3c upload (native rebuild) |
| 3c. memetic manifest (952 × 3 seeds, **1800 s**, §7) | after 3b (§3) |
| 4. ρ pre-registration | before any memetic result |

## 2. Milestone 2: the unpack + hash job

**Which instances:** the **952** MSE 2026 instances with a published
proven optimum (`optimal_cost`), 80.3 GiB as `.wcnf`. By the published
EvalMaxSAT time:

| EvalMaxSAT (published, verified optimum) | instances |
|---|---:|
| ≤ 1 s | 167 |
| (1, 30] s | 231 |
| (30, 3600] s | 392 |
| not proved by EvalMaxSAT (proved by another solver) | 162 |

All 952 go in, including the under-30 s instances (user). Our EvalMaxSAT
runs on different hardware, so instances near 30 s and 1 h can move across
the edges; that is another reason not to unpack only the 392.

**Disk:** 17 GB used of 400 GB (user). This job adds about 80 GiB of
`.wcnf`, so about 100 GB will be in use afterwards.

**MSE 2023 is not touched** (user, 2026-10-28: "I dont want mse23
extraction meanwhile. remove it from scripts"). The 2023 extract, hashes
and the 2023/2026 overlap are left for when the replication is prepared.

**What the job does.** It is a 50-task array (user, 2026-10-28: "can I do
with parallel ... up to 1000 array ... I dont want to wait several hours"):
`cluster_staging_maxsat_strong/scripts/mse26_unpack_array.sbatch`, shell
only, 1 CPU and 2 GB per task, 2 h limit, all 50 at once.
- **Why 50 and not 1,000:**
  - the largest file (3.4 GiB) is one task's whole job, and that sets the
    floor of a few minutes;
  - `mse26_work.tsv` packs the 1,216 files into 50 tasks of about equal
    bytes (largest-first; unpacking counted as 3 passes, hashing as 1);
  - more tasks would not shorten the run, only multiply simultaneous
    reads and writes on the home filesystem. 50 parallel `xz` streams
    already exceed what a shared filesystem typically serves, so that I/O
    becomes the limit.
- **Each task, for its files:**
  - the content sha256 (of the decompressed `.wcnf`);
  - for the 952 marked `unpack=1`: unpacked to
    `~/mse_full26/wcnf/<set>/<hash>.wcnf` (the `.xz` is kept), with the size
    checked against the xz index (`sizes.tsv`);
  - for those 952, counts of hard clauses, soft clauses and `p` lines (old
    format), and whether any soft weight is not 1. The awk counts equal our
    parser's (`WCNF.parse_dimacs`) on 4 MSE 2023/2024 files.
  - One row per file; a rerun skips rows already written.
- **Then `mse26_unpack_finish.sh` on the login node** (shell only, light):
  - checks every row exists, or prints the missing task ids for
    `--array=…`;
  - merges `mse26_content.tsv`;
  - makes the symlinks `data/raw/mse26 -> ~/mse_full26/wcnf` in
    `~/cluster_staging_maxsat_strong` and `~/cluster_staging_maxsat_evo`.
    Both drivers `cd` to their tree root and open instance paths relative
    to it. An existing path is never replaced.

**Tested** on a mock home (1,216 small `.xz` files, 5 tasks), with
`python`/`python3` tripwires on PATH (not triggered):
- task 2 with a truncated `.xz`: `TASK_FAIL`;
- finish with task 5 never run: `MISSING … tasks 2,5` plus the resubmit
  line;
- after rerunning 2 and 5: `ALL_DONE`;
- links made once, then `HAVE`;
- a 2023 zip left as it is.

**Upload:** `tmp/upload_mse26_unpack/` (5 files + `upload.sha256`) into `~`.

```bash
# login node, in ~ after the upload
sha256sum -c upload.sha256                       # 5 x OK
mkdir -p logs_mse26_unpack
sbatch mse26_unpack_array.sbatch                 # 50 tasks
squeue -u $USER                                  # wait until none left
bash mse26_unpack_finish.sh                      # DONE26 1216/1216, 952/952; LINK made x2; ALL_DONE
```

**Bring back** to `cluster_staging_maxsat_strong/results/mse26_unpack/`:
`~/mse_full26/unpack_hash/mse26_content.tsv`.

**Then clean `~`** (user, 2026-10-28: "remind me after I copy back files to delete from ~ what I
copied there"): `cleanup_home_uploads.sh` with `cleanup_home_uploads.names` (in the same upload). It
lists 523 names: every file of the repo's `tmp/upload_*` folders (ems26, hmse2, mse_dl, pop, pp10,
u30_hmse, mse26_unpack), the arrange scripts, and the superseded single-job files. It removes only
regular files directly in `~`, by name. Directories, symlinks, `~/mse_full*`, `~/evalmaxsat2026`, the
trees and logs are never touched. Mock-tested with python tripwires.

```bash
bash cleanup_home_uploads.sh            # dry run: look at the list
bash cleanup_home_uploads.sh --apply    # removes them, then itself
```

## 3. Milestone 3: the manifests (plan, to build after §2 returns)

**3a. EvalMaxSAT** (evo tree driver `evalmaxsat_array.sbatch`, the 2026
binary):
- 952 tasks × 3600 s, one array (≤ 1000);
- worst case 952 CPU-h; the published runs suggest far less, since 398
  of the 952 finished in ≤ 30 s;
- needs only the paths and hashes from §2, so it can run while 3b is
  built.

**3c. Memetic** (strong tree, `configs/strong/auto.yaml`, `hparams: auto` = /3):
- 952 × 3 seeds = 2,856 tasks, in 3 arrays of ≤ 1,000;
- budget 3600 s, stop at the published optimum;
- kernel on, as O900/HMSE;
- seeds 4–5 only by the pre-registered rule (milestone 4).

**Memory from the start (user, 2026-10-28: "initially give larger
instances more ram").** This replaces "8 GB for everything first" for MSE
2026. Every bin is one `sbatch --mem=…` submission:
- **EvalMaxSAT:** the smallest of 8/16/32/64 GB whose 75 % covers
  EvalMaxSAT's published peak (`mem.usage`); a published memout → 64 GB
  (rule of `EVALMAXSAT_2026_INSTALL.md` §4). For the 952: counts come with
  the manifest.
- **Memetic:** the larger of that bin and a size bin from the `.wcnf`
  size. The size thresholds will be set at 3c from the parse footprint of
  the largest local MSE files (a few seconds on the workstation; nothing
  new on the cluster).
- A task that still dies for a system reason is rerun one bin up
  (notes §14).

**Upload hashes:** the manifests' upload lists will not include the
80 GiB of instances. `sha256sum -c` over them would be heavy for the login
node. Instead the manifests carry each instance's sha256 from §2, and the
drivers record the sha256 they read.

## 4. The flip counter (option 1): reasoning and recommendation [verified records + inference]

**What is coarse today:** the memetic checks the target only at call
boundaries. Effort is therefore counted in whole polish calls of 12,500
flips (`ls_polish_flips`). Runs that reach the optimum in the first call
or two are all tied.

**How much of the data sits at the floor** (calls to target, from
`total_flips` / 12,500 in the batch records, runs that reached the
target):

| batch | runs | 1 call | ≤ 2 | ≤ 4 | ≤ 8 | ≤ 16 | ≤ 32 | median TTT |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| U30 (RC2 < 30 s) | 956 | 83 % | 90 % | 95 % | 97 % | 99 % | 99 % | 0.033 s |
| O900 soft+MSE (RC2/EMS 30–900 s) | 735 | 54 % | 68 % | 81 % | 90 % | 94 % | 98 % | 0.049 s |
| HMSE (MSE hard) | 69 | 4 % | 7 % | 14 % | 20 % | 38 % | 59 % | 55 s |

**Reading:**
1. **Ties are a problem only in the first few calls.** If a run reaches
   the target after call K, counting in whole calls is off by less than
   one call, i.e. by at most 1/K of its effort. At K = 16 that is ≤ 6 %,
   well below the seed-to-seed spread. Beyond 16 calls, per-flip resolution
   adds nothing to the ranks. This agrees with the user's point that long
   runs do not need it.
2. **Use a call cutoff, not seconds.** Seconds per call vary by orders of
   magnitude with instance size: about 30 ms on U30 instances, about 2.5 s
   on HMSE instances (median 22 calls in 55 s). A 10/25/40 s cutoff would
   mean hundreds of calls on small instances and a handful on large MSE
   files. 16 calls means the same precision everywhere.
3. **The under-30 s instances need it most.** 83 % of U30 runs ended in
   call 1. Without the counter they add only ties to ρ. With it they add
   real ranks. That is why the counter matters for including the 398 MSE
   2026 instances under 30 s.

**Recommendation:**
- record `flips_to_target`: the flips completed in earlier calls plus the
  index of the flip inside the reaching call at which the true cost first
  hit the target, when the target is reached in calls 1–16;
- after call 16, call granularity, with a flag saying so;
- if the target is reached outside a flip (crossover child, mutation,
  hard-mode SAT move), the counter is the flips completed so far, and the
  record says which operator reached it.

Whether this is cheap depends on whether the C core already tracks the true
(original-weight) cost incrementally next to the dynamic weights; to verify
in the code at 3b. If it does, the check costs one comparison per flip. If
it does not, the 16-call cap keeps the cost bounded.

## 5. Per-run RAM (user: "if you find for statistics useful") [recommendation]

**Yes, add it.** It is free: one `getrusage` call at the end of a run.
- **Memetic:** `peak_rss_mb` (`RUSAGE_SELF`) in the record.
- **EvalMaxSAT wrapper:** `solver_peak_rss_mb` (`RUSAGE_CHILDREN`), the
  solver process's peak.
- **Uses:**
  - `sacct` MaxRSS is blank on this cluster, so this is the only memory
    figure we would have;
  - it says which bin a failed task needs on rerun;
  - it allows a memory comparison of memetic vs EvalMaxSAT in the paper,
    next to the published EvalMaxSAT peaks;
  - it can set the bins of the 2023 replication from data instead of
    guesses.
- **Not used for:** ρ itself.
- Built together with the flip counter (3b) for the memetic, and with 3a
  for the EvalMaxSAT wrapper.

## 6. Order

1. **Now:** upload, then run `mse26_unpack_array.sbatch` and `mse26_unpack_finish.sh` (§2),
   and bring `mse26_content.tsv` back.
2. **3a:** EvalMaxSAT manifest; submit; it runs for a long time.
3. **3b:** the flip counter + RAM in the strong tree. Tests and smoke, then
   a native rebuild on the cluster.
4. **3c:** the memetic manifest, after 3b, so every MSE 2026 memetic run
   carries the counter. Running the memetic first would mean rerunning it.
5. **4:** the ρ pre-registration (windows, the under-30 s part, seeds 4–5),
   written before any memetic MSE 2026 result is seen. This means the
   analysis rules are fixed in advance, not that ρ is computed without memetic
   results.

## 7. Decision 2026-10-28 (later): memetic only, 1800 s, ρ x from the published MSE 2026 results

> "do only the memetic staff, I want to see how the solver performs at all,
> give it 1800s, later we do the granuarity for less if I want, meanwhile
> consider tkimg exact solver results for rho from web mse" (user,
> 2026-10-28). Asked whether "granularity" meant the flip counter: it means
> **shorter budgets** later (user's answer). The flip counter (3b) stays.

**What changes:**
- **3a (our EvalMaxSAT 952 × 1 h) is dropped.** The exact side of ρ comes
  from the published MSE 2026 per-run results (`data/raw/mse_results/mse26/`).
  The per-run EvalMaxSAT RSS field of §5 goes with it.
- **The memetic budget is 1800 s** (not 3600 s), target-stop at the published
  optimum. Order now: 3b (counter + RSS) → 3c (952 × 3 seeds × 1800 s) → 4
  (pre-registration) before any memetic result is read.
- **Shorter budgets later cost no compute** [verified in code]: the
  hyperparameters (`auto_hparams/3`) depend on instance features only, and the
  run budget only caps the time of the last polish call (`memetic.py`
  `_ls_budget`). A run that reached the optimum at time t would have reached
  it under any budget ≥ t, so a budget B < 1800 s is read off the 1800 s
  records (success iff TTT ≤ B).

**The published exact results [verified from the local CSVs]:** 952
instances with `optimal_cost`. Per-run rows for 22 unweighted / 15 weighted
exact solvers, with wall and CPU time, memory, answer and `verified`.

| solver (published, verified optimum, 952 instances) | proved | ≤ 30 s | (30, 3600] s |
|---|---:|---:|---:|
| EvalMaxSAT | 792 | 398 | 392 |
| UWrMaxSAT2026 (most proved) | 880 | 467 | 413 |
| VBS (fastest verified per instance) | 952 | — | — |

The 2 EvalMaxSAT rows above 3600 s are proved with wall slightly over the
limit. EvalMaxSAT is single-threaded there: CPU/wall median 0.989 (p5 0.973)
on its 625 proofs over 1 s.

**[inference] Recommendation for the x of ρ:**
1. **Primary: published EvalMaxSAT 2026 wall time.** This keeps the earlier
   choice of one concrete solver ("compare rho to concrete solver like
   EvalMaxSat", 2026-10-25), and it is the same 2026 source we would have
   built.
   - **Hardware:** the earlier reason for own runs (§2 of
     `MSE_PUBLISHED_EXACT_RESULTS.md`) was the 2024 SBVA plateau and our
     older `94e6774` build. Neither applies to 2026. Spearman ρ uses ranks, so
     a uniform speed factor between the MSE nodes and ours cancels.
     Non-uniform effects (memory bandwidth on the GiB-sized files) remain an
     untested risk. Without our own EvalMaxSAT runs it can't be measured; a
     small own-run cross-check (e.g. 30 instances, 1 h) is possible later if
     a reviewer asks.
   - **Not proved by EvalMaxSAT (160):** censored at 3600 s (tied top rank),
     or left out. To be fixed in the pre-registration.
2. **Sensitivity: VBS time.** Every one of the 952 has a value, so there is
   no censoring on the exact side. It measures "exact hardness" rather than
   one solver's.
3. **Descriptive: ρ against each published solver** (22 / 15), per track,
   as one figure. This shows whether memetic hardness tracks some exact
   paradigms (core-guided, implicit hitting set, SAT-UNSAT) more than others.
4. **Per track.** Unweighted and weighted have different solver lists and
   different weight semantics, so ρ is reported per track as well as pooled.
5. **Memetic side:** a run that misses the optimum in 1800 s is censored at
   1800 s; with 3 seeds the per-instance value is the median TTT (rule in
   milestone 4).

**3b design, as verified in `ls_core.c`:** both native cores (`ls_walksat`,
`ls_dls`) already keep the true hard count (`nh` / `S.nfh`) and the
original-weight unsat soft weight (`usw` / `S.usw`) after every flip. The
counter therefore costs one comparison per flip: a target argument, and a new
`out[]` slot with the flip index at which `hv == 0 && usw ≤ target` first
held (−1 if never). The Python side adds the flips of earlier calls,
applies the 16-call cap and the operator flag of §4, and maps the target
into kernel space when the kernel gate is on. Per-run peak RSS is a
`getrusage` in the shard runner (Python, no rebuild). The native rebuild on
the cluster (`build_native.sbatch`) is part of the upload.

## 8. Milestone 3b built (2026-10-28) [verified: tests + workstation smoke]

**Record fields (shard schema 7):** `calls_to_target`, `flips_to_target`
(the unit of `total_flips`), `target_by` (init | kernel | pre_polish | polish
| child | unknown), `ttt_resolution` (flip | call), `time_to_target_hit_s`
(`time_to_target_s` keeps its meaning: end of the reaching call), and
`peak_rss_mb` on every record. Files: `cluster_staging_maxsat_strong/PROVENANCE.md`.

**One change from §4:** the counter is exact in every call, not only calls
1–16. It costs the same either way (one comparison per step), so a cap would
only discard data; the 16-call rule can still be applied at analysis.

**Tests:** 18 new (`tests/test_target_hit.py`); 439 passed, 16 skipped.
- C and Python twins report the same hit step; the target changes no flip;
- the hit step is the first one: a call cut there reaches the target, one
  step earlier it does not;
- memetic and shard invariants (calls = children, flips ≤ total, hit time ≤
  TTT); schema 7 fields null without a target.

**Overhead:** +2 % per call (C core, 20,000 vars, 300k steps; min of 5),
about timing noise.

**Workstation smoke** (`auto.yaml`, seed 1, 120 s, native):

| instance | TTT s | hit s | calls | flips to target / total | by |
|---|---:|---:|---:|---:|---|
| bf0432-007 (U30) | 0.053 | 0.044 | 1 | 3,704 / 12,500 | polish |
| mbd-b14_C-mbd14-0277 | 14.3 | 14.28 | 12 | 137,501 / 150,000 | polish |
| causal Bands_6_277 | 10.8 | 10.78 | 5 | 50,000 / 50,000 | pre_polish |
| pathways_p16 | 8.4 | 8.36 | 3 | 25,000 / 37,500 | pre_polish |

The U30 row is the tie the counter exists for: "1 call" becomes flip 3,704.
On the two hard-clause instances the child entered its call already at the
optimum (crossover, mutation, repair or hard moves); the flips are then
those of the earlier calls.
