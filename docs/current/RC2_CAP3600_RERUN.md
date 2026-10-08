# RC2 re-run at a one-hour cap: every censored instance

**Date:** 2026-10-08. **Status:** the manifest is built and verified, and a
dry run passed. **Not submitted yet; the user submits.**

All paths are relative to `cluster_staging_maxsat/` unless they start with
`docs/`.

## 1. Selection

Included: every instance under `data/` that has at least one RC2 row in
`results/` and **no completed RC2 row at any cap**.

Excluded:
- `data/mse16/`, `data/raw/` (MSE 2024) and `data/more_data/`;
- instances that have never had an RC2 row: calib_c (40) and the 16
  satisfiable jnh. They did not hit a cap.

151 instances qualify. `unsat_uuf_diff/uuf250-0{2,4,8}.cnf` have the same
clause lines as `unsat250_1000c/uuf250-0{2,4,8}.cnf` (only the comment block
differs), so the builder deduplicates by clause content and keeps the
`unsat250_1000c` copies. That leaves **148 tasks**.

The selection was fixed before any cap-3600 row existed.

## 2. Configuration

| item | value |
|---|---|
| solver | RC2 `"g3"`, default options (unchanged from every earlier RC2 batch) |
| cap + grace | 3600 s + 120 s (grace as in the earlier 1800 s run) |
| Slurm | `--time=01:10:00`, `--mem=16G` (earlier batches used 8G), %30 |
| output | `results/profile_cap3600/task_<N>.{jsonl,env.json}` |
| worst case | 148 × 3720 s ≈ 153 CPU-h; 5 waves × ~70 min ≈ 6 h of compute, excluding queue wait |

## 3. Data: what goes in (148 tasks)

**By source:**

| source | tasks | prior cap | prior lower bound (LB) |
|---|---:|---|---|
| calib_a (`data/generated/calib_a/`) | 88 | 900 s | 1–95 |
| calib_b (`data/generated/calib_b/`) | 25 | 900 s | 1–43 |
| satlib_bench | 12 | 900 s | 2 (11 uuf); none (hole10) |
| unsat250_1000c (uuf250) | 23 | 900 s (also 600 s in `profile_uuf` for 02, 04, 08) | 1 ×18, 2 ×5 |
| **total** | **148** | | |

**By cell.** Generated cells are `wksat_v<n>_k<k>_sr<m/n>_hr0.00_w1_uniform_s<seed>`.
"Tasks" are line numbers in `scripts/manifest_rc2_cap3600.txt`. The LB is
the best lower bound recovered from the censored rows.

| source | k | n | m/n | censored seeds | count | LB | tasks |
|---|---:|---:|---:|---|---:|---|---|
| calib_a | 2 | 100 | 6.00 | s2–s5 | 4 | 49–54 | 1–4 |
| calib_a | 2 | 150 | 3.00 | s5 | 1 | 28 | 15 |
| calib_a | 2 | 150 | 4.00 | s1–s5 | 5 | 35–40 | 16–20 |
| calib_a | 2 | 150 | 6.00 | s1–s5 | 5 | 55–66 | 21–25 |
| calib_a | 2 | 250 | 3.00 | s1–s5 | 5 | 29–33 | 38–42 |
| calib_a | 2 | 250 | 4.00 | s1–s5 | 5 | 44–49 | 43–47 |
| calib_a | 2 | 250 | 6.00 | s1–s5 | 5 | 70–79 | 48–52 |
| calib_a | 2 | 400 | 3.00 | s1–s5 | 5 | 32–39 | 69–73 |
| calib_a | 2 | 400 | 4.00 | s1–s5 | 5 | 52–57 | 74–78 |
| calib_a | 2 | 400 | 6.00 | s1–s5 | 5 | 89–95 | 79–83 |
| calib_a | 3 | 70 | 8.00 | s1–s5 | 5 | 9 | 84–88 |
| calib_a | 3 | 100 | 6.00 | s1–s5 | 5 | 5–6 | 5–9 |
| calib_a | 3 | 100 | 8.00 | s1–s5 | 5 | 7–8 | 10–14 |
| calib_a | 3 | 150 | 5.00 | s2, s5 | 2 | 3–4 | 26–27 |
| calib_a | 3 | 150 | 6.00 | s1–s5 | 5 | 4 | 28–32 |
| calib_a | 3 | 150 | 8.00 | s1–s5 | 5 | 5–6 | 33–37 |
| calib_a | 3 | 250 | 4.26 | s3 | 1 | 1 | 53 |
| calib_a | 3 | 250 | 5.00 | s1–s5 | 5 | 2 | 54–58 |
| calib_a | 3 | 250 | 6.00 | s1–s5 | 5 | 3 | 59–63 |
| calib_a | 3 | 250 | 8.00 | s1–s5 | 5 | 4 | 64–68 |
| calib_b | 2 | 100 | 4.50 | s3, s5 | 2 | 36–37 | 89–90 |
| calib_b | 2 | 100 | 5.00 | s2, s3, s5 | 3 | 39–43 | 91–93 |
| calib_b | 2 | 150 | 3.15 | s5 | 1 | 29 | 96 |
| calib_b | 2 | 150 | 3.30 | s5 | 1 | 31 | 97 |
| calib_b | 2 | 250 | 2.35 | s4 | 1 | 23 | 101 |
| calib_b | 2 | 250 | 2.50 | s3, s4 | 2 | 24–25 | 102–103 |
| calib_b | 2 | 400 | 2.30 | s1, s5 | 2 | 25 | 107–108 |
| calib_b | 3 | 50 | 8.50 | s1 | 1 | 12 | 109 |
| calib_b | 3 | 50 | 9.00 | s1, s2, s4 | 3 | 13–14 | 110–112 |
| calib_b | 3 | 70 | 6.50 | s2 | 1 | 7 | 113 |
| calib_b | 3 | 100 | 5.50 | s2, s5 | 2 | 5 | 94–95 |
| calib_b | 3 | 150 | 4.60 | s5 | 1 | 3 | 98 |
| calib_b | 3 | 150 | 4.80 | s2, s5 | 2 | 3–4 | 99–100 |
| calib_b | 3 | 250 | 4.35 | s1, s3, s4 | 3 | 1–2 | 104–106 |
| satlib | hole | — | — | hole10 | 1 | — | 114 |
| satlib | 3 | 200 | 4.30 | uuf200-014, -033, -035, -087 | 4 | 2 | 115–118 |
| satlib | 3 | 225 | 4.27 | uuf225-019, -04, -043, -07, -072, -085, -088 | 7 | 2 | 119–125 |
| unsat250_1000c | 3 | 250 | 4.26 | uuf250-013, -016, -02, -022, -027, -030, -032, -035, -036, -037, -039, -04, -052, -069, -074, -077, -078, -08, -085, -086, -088, -092, -095 | 23 | 1 ×18; 2 ×5 (030, 036, 037, 085, 095) | 126–148 |

Per-instance detail (prior batches, prior status, LB, duplicates) is in
`scripts/manifest_rc2_cap3600.tasks.csv`. Prior status was
`subprocess_killed` on 139 rows and `timeout` on 9.

**Reading the LB [inference, nothing has run yet].** RC2 time grows steeply
with c\* (`CALIB_B_B1_READOUT.md` §5). The 57 Max-2-SAT tasks split into
three groups by what their sibling seeds in the same cell did at 900 s
(`results/profile_calib_{a,b}_all.jsonl`):

| group | cells | tasks | siblings at 900 s | expectation at 3600 s |
|---|---|---:|---|---|
| **borderline** | all 7 calib_b k=2 cells; calib_a n=150 m/n=3.00 | 13 | 2–4 of 5 certified, up to 610 s; censored LB is only 1–8 above the highest sibling c\* | **most likely Max-2-SAT tasks to certify** |
| near-edge | calib_a n=100 m/n=6.00 | 4 | s1 certified at 753 s with c\* = 50; censored LB 49–54 | possible |
| deep | calib_a n=150 m/n 4.00 and 6.00; all calib_a n=250 and n=400 k=2 cells | 40 | none certified | likely to stay censored |

Borderline cells, per cell: certified siblings as (seed, s, c\*), then the
censored seeds' LB.
- calib_b n=100 m/n=4.50: (s1, 67, 32), (s2, 126, 35), (s4, 16, 30); LB 36–37.
- calib_b n=100 m/n=5.00: (s1, 84, 35), (s4, 31, 35); LB 39–43.
- calib_b n=150 m/n=3.15: c\* 20–26, up to 301 s; LB 29.
- calib_b n=150 m/n=3.30: c\* 25–28, up to 227 s; LB 31.
- calib_b n=250 m/n=2.35: c\* 14–22, up to 610 s; LB 23.
- calib_b n=250 m/n=2.50: c\* 17–21, up to 29 s; LB 24–25.
- calib_b n=400 m/n=2.30: c\* 20–23, up to 367 s; LB 25.
- calib_a n=150 m/n=3.00: c\* 19–24, up to 65 s; LB 28.

For the 3-SAT and SATLIB tasks, and for the predictions to check when the rows
arrive, see §6.

*Correction, 2026-10-08:* the first version of this paragraph called all
Max-2-SAT tasks "dense" and likely to stay censored. That fits only the
40 tasks in the deep group.
It also said "the low-LB 3-SAT cells" were likely to certify. The size of
the LB is not the signal; sibling evidence is. For example, calib_a
n=250 m/n=5.00 has LB 2 but 0 of 5 siblings certified, while calib_b
n=50 m/n=8.50 has LB 12 and 4 of 5 certified.

## 4. Files

| file | role |
|---|---|
| `scripts/make_rc2_cap3600_manifest.py` | builds the three manifest files from `results/`; `--check` rebuilds and exits 3 on drift |
| `scripts/manifest_rc2_cap3600.txt` | 148 root-relative paths; task N = line N |
| `scripts/manifest_rc2_cap3600.sha256` | `sha256sum -c` list, also checked by the submitter |
| `scripts/manifest_rc2_cap3600.tasks.csv` | per-task sidecar |
| `scripts/submit_rc2_cap3600.sh` | wrapper around `submit_rc2_profile.sh` / `rc2_profile_array.sbatch` with the §2 settings |
| `scripts/compare_cap3600_predictions.py` | checks the §6 predictions against `results/profile_cap3600_all.jsonl` |

## 5. Commands

```bash
# workstation -> cluster
cd /home/mashe/maxsat-lab_new/maxsat-lab
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# login node
cd ~/maxsat-lab && sha256sum --quiet -c scripts/manifest_rc2_cap3600.sha256 && echo SHA_OK
cd scripts && mkdir -p logs
DRY_RUN=1 bash submit_rc2_cap3600.sh
bash submit_rc2_cap3600.sh                 # record the job id
RESUME=1 bash submit_rc2_cap3600.sh        # only if rows are missing

# back on the workstation
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_cap3600/ cluster_staging_maxsat/results/profile_cap3600/
cd cluster_staging_maxsat && python3 scripts/aggregate_rc2_profile.py --batch cap3600 --manifest scripts/manifest_rc2_cap3600.txt
```

## 6. Predictions recorded before the run, and how to compare

**Recorded 2026-10-08, before submission. Do not edit after rows arrive;**
add the outcome below the table instead.

Each group is defined by what the other seeds in the same cell did at 900 s
(`results/profile_calib_{a,b}_all.jsonl`, `results/profile_uuf250/`,
`results/profile_satlib_all.jsonl`). "Certify" means `completed` (optimum
proved) within 3600 s. The cell lists are fixed in
`scripts/compare_cap3600_predictions.py`.

| group | what is in it | tasks | evidence at 900 s | prediction |
|---|---|---:|---|---|
| G1 Max-2-SAT borderline | all 7 calib_b k=2 cells; calib_a n=150 m/n=3.00 | 13 | 2–4 of 5 siblings certified (up to 610 s); LB 1–8 above the highest sibling c\* | majority certify |
| G2 Max-2-SAT near-edge | calib_a n=100 m/n=6.00 | 4 | s1 certified at 753 s with c\* = 50; LB 49–54 | ≥ 1 of 4 certifies |
| G3 Max-2-SAT deep | other calib_a k=2 cells (n=150 m/n 4, 6; n=250, 400) | 40 | no sibling certified | ≤ 10 % certify |
| G4 3-SAT borderline | all 7 calib_b k=3 cells; calib_a n=150 m/n=5.00; calib_a n=250 m/n=4.26 | 16 | 2–4 of 5 siblings certified (up to 847 s) | majority certify |
| G5 3-SAT deep | calib_a k=3: n=70 m/n=8; n=100 m/n 6, 8; n=150 m/n 6, 8; n=250 m/n 5, 6, 8 | 40 | no sibling certified | ≤ 10 % certify |
| G6 SATLIB uuf200/225 | the 11 censored, all LB 2 | 11 | c\* = 2 certified in the same family up to 815 s (median 262 s uuf200, 568 s uuf225) | majority certify |
| G7 uuf250 LB 1 | uuf250 with LB 1 | 18 | 77 of 100 certified, all c\* = 1, up to 890 s; no c\* = 2 ever certified at n = 250 | majority certify (lean; c\* may turn out 2) |
| G8 uuf250 LB 2 | uuf250 030, 036, 037, 085, 095 | 5 | no c\* = 2 ever certified at n = 250 within 900 s | **no call.** Direct test of C2 in `RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md` (c\* = 2 is at or past 900 s) |
| G9 hole10 | hole10 | 1 | censored with no bound; pigeonhole is exponential for resolution | stays censored |
| **total** | | **148** | | |

The underlying claim being tested: **sibling evidence at 900 s predicts
certification at 3600 s better than the size of the LB does.** If G3 or G5
certify at the rate of G1 or G4, that claim fails.

**How to compare, once the rows are back:**

```bash
cd cluster_staging_maxsat
python3 scripts/aggregate_rc2_profile.py --batch cap3600 --manifest scripts/manifest_rc2_cap3600.txt
python3 scripts/compare_cap3600_predictions.py
```

For each group it prints: tasks, rows, certified, certified with
c\* > old LB, median solve time, and HELD / FAILED / pending. A group with
missing rows shows "pending" and is not judged.

**Also record when reading the rows:**
- c\* found against the old LB, per group. A G7 task with c\* = 2 would be the
  first certified c\* = 2 at n = 250.
- Any certified task with 30 < t ≤ 900 s. It should not exist, because every
  task was censored at 900 s. If one does, it measures host noise.
- New certifications do not change the (30, 900] s eligibility of anything.
  These rows give optima and time profiles beyond the window, not new
  memetic instances, unless that is decided separately.

**Outcome:** *(fill in when the rows are back)*
