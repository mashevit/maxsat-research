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
