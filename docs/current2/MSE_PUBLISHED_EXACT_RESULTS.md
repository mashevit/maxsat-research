# Published MSE 2023/2024 exact-track results: optima, EvalMaxSAT times, and a plan for our own EvalMaxSAT ρ (2026-10-25)

> "I do want your conclusion - the optimum we can get from the mse docs, I
> think. but I want to compare rho to concrete solver like EvalMaxSat - are
> there aggregated results ot this solver somewhere? I can run it if there
> are less than 1000 instances in one wave on cluster for hour" (user,
> 2026-10-25)

**Status:** research and a proposal. Nothing has been run. Note
N-2026-10-25-d.

**Sources** [verified 2026-10-25]:
- repository `maxsat-evaluations/maxsat-evaluations.github.io`, branch
  `master`;
- `2024/results/exact/{unweighted,weighted}.csv`;
- `2023/results/exact/{unweighted,weighted}/table-all.html`.

Local copies are in `data/raw/mse_results/`, with `SHA256SUMS`.

## 1. Optima: yes, from the MSE pages [verified]

**2023.** The exact table prints, for every solver, "time (cost)" per
instance, and "3600.0 (-)" when unsolved. So each instance an exact solver
finished has a proven optimum in the table:
- 449 of 572 unweighted, 463 of 558 weighted, **912 in all**;
- no instance where two finishing solvers disagree on the cost.

**2024.** The CSVs give times only, or FAILED; the cost is not in them.
- A finished exact run means the optimum is proven.
- Its value is taken from the published `best_costs.csv`, which we already
  have (`data/raw/mse_2024/best_costs (1).csv`, byte-identical to the
  published file).
- 458 of 553 unweighted and 472 of 571 weighted are proven: **930**.

**Caveat:** the 2023 exact costs and the 2023 `best_costs.csv` (anytime
pages) differ on **43 of 912** instances. Examples: aes-key-recovery, where
the exact table says 1–2 and `best_costs` says 18–93, and HaplotypeAssembly,
1500 against 1517.
- [inference] The likely cause is a different file version or cost
  convention between the two tracks. A proven optimum below an anytime best
  is possible; one above it would be a contradiction.
- **Rule for our runs:** the target is the optimum our own EvalMaxSAT run
  proves (and our checker verifies). Published values serve only as a
  cross-check, and any disagreement is flagged.

## 2. Published EvalMaxSAT times: they exist, per instance [verified]

| year | track | EvalMaxSAT column(s) | solved in 1 h | ≤ 30 s | (30, 3600) s | median of solved |
|---|---|---|---:|---:|---:|---:|
| 2023 | unweighted (572) | EvalMaxSAT | 425 | 200 | 225 | 40 s |
| 2023 | unweighted | EvalMaxSAT-SCIP | 433 | 184 | 249 | 85 s |
| 2023 | weighted (558) | EvalMaxSAT | 429 | 197 | 232 | 52 s |
| 2023 | weighted | EvalMaxSAT-SCIP | 442 | 178 | 264 | 89 s |
| 2024 | unweighted (553) | EvalMaxSAT-SBVA (two columns), -SBVA-saveCores | 404–412 | 68–73 | 336–339 | 212–215 s |
| 2024 | weighted (571) | EvalMaxSAT (plain), -SBVA, -SBVA-saveCores | 431–435 | 105–107 | 324–328 | 268–270 s |

For comparison, the VBS (the fastest exact solver per instance) proves:

| year | proved | ≤ 30 s | (30, 3600) s |
|---|---:|---:|---:|
| 2023 | 912 | 725 | 187 |
| 2024 | 930 | 650 | 280 |

**Why these times are a weak x for our ρ:**
1. **A plateau in 2024.** On instances the VBS solves in under 1 s,
   EvalMaxSAT-SBVA (unweighted) takes a median 180 s; 58 % of them take over
   150 s. Plain EvalMaxSAT (weighted) has the same pile-up at 180–200 s
   (43 instances), though its median there is 27 s. So many 2024 times
   measure a fixed preprocessing stage, not hardness.
2. **Other version, other hardware.** Our cluster binary is EvalMaxSAT
   commit `94e6774` (2025-11-05). On the 30 MSE 2024 instances it shares
   with the published table, the times disagree in both directions:
   - lisbon-wedding 9-18: ours 116 s, published 850 s;
   - causal-discovery Bands_6_277: ours 327 s, published 875 s;
   - setcover rail507: ours timed out at 1 h, published 518 s;
   - ja-kemeny 00000300: ours timed out, published 524 s (SBVA).
3. **The memetic runs on our cluster.** Pairing it with an exact time
   measured on the same nodes removes the hardware factor from ρ.

**Conclusion [inference]:**
- Use the published tables for **selection** (which instances are provable
  in 1 h) and as a **cross-check**.
- Measure the x of ρ with **our own EvalMaxSAT runs**.
- The published EvalMaxSAT ρ (2023 plain, 2024 weighted plain) can be a
  sensitivity analysis.

## 3. Proposal: our EvalMaxSAT, 1 h, one wave per year (each < 1000)

**Selection rule:** exact side only, pre-registered, never on memetic
outcomes (notes §11). Take every instance **some MSE exact solver proved
within 1 h in that year**. The rule includes ≤ 30 s instances, as you
allowed on 2026-10-21.

| wave | instances | rule |
|---|---:|---|
| A: MSE 2024 | **930** | VBS-proved in 2024 (458 UW + 472 W) |
| B: MSE 2023 | **≤ 620** | VBS-proved in 2023, minus files already in wave A |

**Why wave B is smaller:**
- 352 file names appear in both years. 1,550 unique names are proved in at
  least one year.
- Each shared name is checked by CRC from the zip census before it is
  dropped. A name with a different CRC stays in wave B.

**Each wave is under 1000**, so it is one array at `%1000`.

**Run settings:** as batch s1.
- `evalmaxsat_array.sbatch`, 3600 s, `--time 01:10:00`, `--mem 16G`.
- Memory follows your rule (notes §14): rerun any task that dies for a
  system reason with more `--mem`.

**Cost:**
- worst case about 930 + 620 = **1,550 CPU-h**;
- [inference] expected roughly 600–900 CPU-h: in 2023/2024 EvalMaxSAT
  finished 75–78 % of the proved instances with a median 40–270 s, and the
  rest run the full hour.

**Before it can run:**
1. The download (§4) and `sizes.tsv`.
2. Decompress the selected `.xz` files on the cluster (as a job). Our
   parser and EvalMaxSAT read plain `.wcnf`.
3. A manifest built from the census lists and the published tables. The
   sha256 values are computed in a job on the cluster, because the files
   are not on the workstation.
4. The EvalMaxSAT binary check (`MSE_EVALMAXSAT_3600.md` §5).

Each of these is a milestone for your go.

**Then, for ρ:**
- x = our EvalMaxSAT proof time;
- y = memetic ERT to that optimum (3 seeds × 900 s, stop at the optimum);
- on the instances our EvalMaxSAT proves;
- the window is pre-registered before any memetic run.

## 4. Download the full sets (prepared 2026-10-21, notes §13)

The scripts are `download_mse_full.sh` and `download_mse_full.sbatch`.
Copies are in `tmp/upload_mse_dl/`, identical to the committed
`cluster_staging_maxsat_strong/scripts/` versions.

The commands are in the reply of 2026-10-25 and in
`NOTES_2026-10-21_AGENDA_AND_STATS.md` §13.

## 5. MSE 2025 and MSE 2026 (checked 2026-10-25) [verified: web]

> "check if there are mse25 or mse26 reachable instances, and reason if
> they are better benchmark than mse23" (user, 2026-10-25)

- **MSE 2025 was not held.** The 2025 page: "the MaxSAT 2025 evaluation
  will not be held this year".
- **MSE 2026 was held, and everything is on Zenodo.**
  - Record 21358014, DOI 10.5281/zenodo.21358014, CC-BY-4.0, published
    2026-07-14. The proceedings were updated on 2026-10-24.
  - Exact zips: unweighted 2.53 GiB (607 `.wcnf.xz` + `meta.csv`),
    weighted 5.03 GiB (609 + `meta.csv`).
  - Files are named by hash. `benchmark-metadata.csv` gives hash, family,
    `best_known_cost` and `optimal_cost`.
  - Per-instance raw results for every solver: cpu and wall time, memory,
    memout, answer, optval, `verified`.
  - The solver sources, including `solver-EvalMaxSAT.zip`.
  - **Zenodo answers from the workstation**, both a HEAD request on the zip
    and range requests (the census). The cluster is untested: it reached
    Google Drive but not Helsinki.
- **Local copies:** `data/raw/mse_results/mse26/` (metadata, both exact
  rawdata CSVs, `SHA256SUMS`). The zip listings are in
  `cluster_staging_maxsat_strong/scripts/mse_census/mse26-exact-*.tsv`.
  The md5 of the metadata and results files matches Zenodo.

**MSE 2023 against MSE 2026, exact tracks:**

| | MSE 2023 | MSE 2026 |
|---|---:|---:|
| instances | 1,130 | 1,216 |
| proven optima published | 912 (table costs; 43 differ from `best_costs.csv`) | 952 (`optimal_cost`) plus a per-run `verified` flag |
| VBS-proved in 1 h | 912 | 947 |
| EvalMaxSAT (published) proved | 854 | 792 |
| EvalMaxSAT in (30, 3600] s | **457** | **391** |
| EvalMaxSAT in (30, 900] s | 367 | 301 |
| EvalMaxSAT on VBS < 1 s instances | median 1–4 s | median 0.7–1.1 s (≥ 150 s: 3 %) |
| results format | HTML table | CSV with memory and `verified` |
| EvalMaxSAT version | 2023 | 2026, source in the record |
| families with ≥ 10 instances | 62 | 56 |
| download | Google Drive, **done** on the cluster | Zenodo, 7.6 GiB, not started |
| memory | not published | EvalMaxSAT up to 33.6 GB; 39 memouts |

About 42 of the 98 2026 family names match 2023 families (the newer
editions reuse families). Whether the instance files overlap is unknown
until both sets are on disk.

**[inference] Is 2026 the better benchmark? Yes, as the primary set:**
1. **It is current.** A 2026 benchmark is what reviewers expect, and it
   carries a citable DOI and a licence.
2. **The same EvalMaxSAT can run.** The record holds the exact source the
   competition ran. Our runs then differ from the published ones only in
   hardware, which gives a strong cross-check of our x.
3. **The data is cleaner.** Optima, verification and memory are
   machine-readable. There are no cost conflicts to resolve, unlike 2023's
   43.
4. **No 2024-style delay.** EvalMaxSAT's times follow hardness down to the
   millisecond range.

**What 2026 costs:**
- about 15 % fewer window points: 391 against 457;
- an 8 GB download not yet done;
- a few memory-heavy instances (EvalMaxSAT used up to 33.6 GB).

**Predicted ρ points for 2026:** 391 × 30–60 % memetic success ≈
**120–235**, successes only. MSE 2023 gives about 140–275.

**Recommendation:**
- **MSE 2026 is the primary ρ sample.**
- **MSE 2023 is an independent replication sample.** It is on the cluster
  already, so it can run first.
- Two samples that agree are stronger evidence than one bigger sample. The
  overlap between the two sets is to be checked (by content hash) and
  removed from the replication.

## 6. Decisions (user, 2026-10-25)

> "agreed, use 2026 source, all 3 seeds, might be even 5 if needed"

- **MSE 2026 is the primary ρ sample; MSE 2023 is the replication
  sample.** Instances in both sets are removed from the replication, by
  content hash.
- **Our EvalMaxSAT runs use the MSE 2026 competition source**
  (`solver-EvalMaxSAT.zip` from Zenodo 21358014), built on the cluster,
  not our `94e6774` build. The same binary serves the 2023 replication.
- **The memetic runs 3 seeds per instance**, and up to 5 if the
  pre-registered precision needs it. The rule for adding seeds 4–5 goes
  into the ρ pre-registration, before any memetic result is seen.
- **Download:** `cluster_staging_maxsat_strong/scripts/sets_mse26.txt`
  (also in `tmp/upload_mse_dl/`), with `DEST=~/mse_full26`.

## 7. MSE 2026 on the cluster: download done, size census (2026-10-28) [verified: job log + sizes.tsv + Zenodo metadata]

- **Download:** job 23591248 (2026-10-25) finished with `ALL_DONE`. Both zips
  passed the CRC test and were extracted to `~/mse_full26/` (607 + 609
  `.wcnf.xz` plus `meta.csv`); the zips were removed. The log and
  `sizes.tsv` are in `cluster_staging_maxsat_strong/results/`
  (`mse26-dl-23591248.out`, `sizes.tsv`).
- **EvalMaxSAT 2026 smoke on the cluster:** done (user, 2026-10-28;
  milestone 1). The records were not copied back.
- **All 1,216 files match the metadata hashes**, and each has an EvalMaxSAT
  row in the published results.
- **Sizes as `.wcnf`:** 123.1 GiB in total (7.6 GiB as `.xz`); median 4.6 MiB,
  99th percentile 3.4 GiB, largest 3.36 GiB.

| `.wcnf` size | files | GiB |
|---|---:|---:|
| < 5 MiB | 620 | 0.7 |
| 5–100 MiB | 445 | 11.3 |
| 100 MiB – 1 GiB | 120 | 35.1 |
| 1–10 GiB | 31 | 76.0 |

- **The ρ window** (published EvalMaxSAT, `OPTIMUM FOUND`, verified, wall
  time in (30, 3600] s): **392** instances. §5 said 391, an off-by-one from
  the time column or the boundary; not chased. 57.6 GiB as `.wcnf`, 233 over 5 MiB,
  12 over 1 GiB.
- **Memory bins (§4 of `EVALMAXSAT_2026_INSTALL.md`, published EvalMaxSAT
  peak at 75 %):** window 8 GB 344, 16 GB 17, 32 GB 17, 64 GB 14; all 1,216:
  8 GB 1,074, 16 GB 31, 32 GB 34, 64 GB 77.
- **EvalMaxSAT peak / `.wcnf` size** (window, files > 50 MiB, n = 112):
  median 19×, range 8.6–81×.
- **Proven optimum known** (`optimal_cost`): 952 files, 80.3 GiB as `.wcnf`.
