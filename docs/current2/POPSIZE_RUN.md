# Batch POP: R4's population size {10, 40} on every MSE 2023/2024 instance with hard clauses (2026-10-25)

> "do prepare run for some data we already have, not mse26, I want to check
> If with pop10 instead pop40 is better, prepare rule, that takes into
> account fitness, and arrival at optimum" (user, 2026-10-25)

**Tree:** `cluster_staging_maxsat_strong/`. **Builder:**
`scripts/make_popsize_manifest.py`. **Readout:** `scripts/popsize_readout.py`
(the §5 rule as code, written before any result). **Note:** N-2026-10-25-g.
**Status:** built, smoke-tested and the upload folder made 2026-10-25.
**Not run, by decision** (user, 2026-10-25: "dont need to run batch then",
after §6). R4 keeps pop 10. The builder, the configs, the `hard_pop` option
and the readout stay in the tree, so the test can be run later unchanged. The
§5 rule was never confirmed.

## 1. Why [verified: KS2_CHECK_RUN.md §6, AUTO_HPARAMS.md]

- R4 of `auto_hparams` sets pop 10 (with `keep_sat: ks2`) on every instance
  with hard clauses. Soft instances keep the config's 40.
- **Pop 10 was never shown to beat 40.** In KS2 (16 instances), `ks2_10` vs
  `ks2_40` was 8 better / 7 worse: no effect by the rule. Pop 10 was the
  user's choice on 2026-10-21.
- **This batch tests it on 9× more instances:** all 144 MSE 2023/2024
  hard-clause instances we hold.
- **Why not the soft pool:** the median soft run (O900, U30) makes 1 child
  and reaches the optimum in ~0.05 s. The population hardly acts there, so
  the soft pool cannot show a pop effect.

## 2. Batch [verified: built, `--check`]

**Arms:** these are the only difference between runs.

| arm | config | `hparams` | R4 pop on hard instances |
|---|---|---|---:|
| `pop10` | `configs/strong/popsize_pop10.yaml` | `{mode: auto, hard_pop: 10}` | 10 (today's rule) |
| `pop40` | `configs/strong/popsize_pop40.yaml` | `{mode: auto, hard_pop: 40}` | 40 |

- **Everything else** is `configs/strong/auto.yaml` (`auto_hparams/3`): B1–B5,
  the kernel gate, ks2, R5 (per_polish 10 on the 3 lean rail instances, in
  both arms).
- **New option `hparams.hard_pop`** (`src/evo/auto_hparams.py`, default 10). It
  sets the pop R4 chooses. With the default, every instance resolves exactly
  as under `/3`, so the rule set stays `/3`. Records show it in
  `hparams.overrides.ea.pop_size` and in the R4 reason (`(hparams.hard_pop)`).
  Tests: `test_hard_pop_sets_r4_pop_on_hard_only` and the refusal cases.

**Instances (144):**

| group | p | source | targets |
|---|---|---|---|
| hmse | p001–p141 | `scripts/instances_hardmse.csv` h001–h141 | as in HMSE: 17 proven, 124 best-known |
| rail | p142–p144 | setcover_wt-rail507/516/582 (MSE 2024) | MSE 2024 best-knowns 174/182/211, as in PP10 |

| class (R2, judged on the original instance) | instances | proven | best-known |
|---|---:|---:|---:|
| unweighted (MSE 2023) | 67 | 9 | 58 |
| weighted (MSE 2024 + rail) | 77 | 8 | 69 |

**Runs:**
- 144 instances × 2 arms × seeds 1–3 = **864 tasks**;
- 900 s each, stop at the target;
- 1 CPU, 8 GB, `--time 00:20:00`;
- one array, `--array=1-864%1000`.

**Job ids and output:** `po_<arm>_<pNNN>_s<seed>`, written to
`results/popsize/tasks`.

**Cost:**
- worst case 864 × 960 s = **230 CPU-h**;
- expected ≈ 165 h: HMSE (the `pop10` arm's 141) took 78.6 h, plus the rail
  runs and the same again for `pop40`.

**Why both arms run fresh:** HMSE already holds a pop-10 run of h001–h141, but
under older code (`0877898`, `/2`) on other nodes. Running both arms in one
array keeps the comparison to the one difference.

## 3. Smoke [verified: workstation, real shard runner, C core, 20 s, one at a time, `ulimit -v` 6 GB]

Records are in `tmp/smoke_popsize/`.

| job | peak RSS | result at 20 s | R4 pop in the record | per_polish |
|---|---:|---|---:|---|
| po_pop10_p002_s1 (bcp-SU3) | 190 MB | 106 = target, 15.1 s | 10 | (default) |
| po_pop40_p002_s1 (bcp-SU3) | 192 MB | 106 = target, 18.8 s | 40 | (default) |
| po_pop10_p142_s1 (rail507) | 289 MB | 229 (target 174) | 10 | 10 (R5) |
| po_pop40_p142_s1 (rail507) | 304 MB | 236 (target 174) | 40 | 10 (R5) |

- **All `ok`, feasible (hv 0), C core, ruleset `auto_hparams/3`.**
- **`m2_results.py pending`:** the only mismatch is the expected one,
  `budget_s` 20 against 900.
- **Readout script, end to end:** the 2 bcp records were rewritten into 6
  fake 900 s records. The script used the instance and called it a tie: TTT
  15.1 vs 18.8 s is 1.249×, below the 1.25× threshold. On the raw smoke
  records it excludes every instance, with the reason.
- **Tests:** the strong-tree suite gives 421 passed, 16 skipped (5 new in
  `tests/test_popsize_readout.py`, 1 new in `tests/test_auto_hparams.py` plus
  3 refusal cases).

## 4. Upload (flat, without rsync) and commands

**What the cluster lacks:**
- `make_flat_upload.py` was run with `--have` lists 097efb7 (O900, KS2),
  0877898 (U30, HMSE) and 2763872 (PP10).
- **Result:** 12 files, 0.6 MB, in `tmp/upload_pop/`. 185 of the needed paths
  are already on the cluster.
  - **code:** `src/evo/auto_hparams.py` (`/3` + `hard_pop`) and
    `src/sat/ls_v3.py` (`nbrs_plan`, from `acb7340`, not yet on the
    cluster); `scripts/auto_hparams.py`;
  - **the 2 configs;**
  - **the manifest files**, the instances CSV and the builder.
- **No C rebuild.** `src/native/ls_core.c` is unchanged since the PP10 rebuild.
- **Every name starts `pop__`.** The map is `UPLOAD_MAP_pop.tsv`, and the
  arrange script is `arrange_pop.sh` (the PP10 script, with these checks:
  `POP_OK`, 864 tasks, `/3` with `hard_pop`).
- **Mock test:** run on a mock of the cluster tree (`2763872` plus the
  instance files), with `python`/`python3` tripwires on PATH. The dry run
  and `--apply` both gave new 9, replace 3, bad 0, missing 0, `POP_OK`; the
  tripwire never fired. The mock's `src/` then equals the workstation's.

On the login node (shell only), after dropping all 13 files of
`tmp/upload_pop/` into `~`:

```bash
squeue -u $USER                       # must be empty
bash arrange_pop.sh                   # dry run: expect new 9, replace 3, bad 0, missing 0
bash arrange_pop.sh --apply           # expect POP_OK, "POP manifest: 864 tasks"
cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs
DRY_RUN=1 MANIFEST=manifest_popsize.tsv OUTDIR=results/popsize/tasks bash submit_m2_memetic.sh   # --array=1-864%1000
MAXSAT_GIT_SHA=<commit> MANIFEST=manifest_popsize.tsv OUTDIR=results/popsize/tasks bash submit_m2_memetic.sh
```

**Memory:** 8 GB. A task that dies for a system reason (OOM, node) is rerun
with more memory (16 → 32 → 64 GB):
`IDS=<ids> RESUME=1 ... bash submit_m2_memetic.sh -- --mem=16G`. HMSE and
PP10 ran all of these instances at 8 GB.

**Back on the workstation:**

```bash
cd /home/mashe/maxsat-lab_new/maxsat-lab/cluster_staging_maxsat_strong
# copy ~/cluster_staging_maxsat_strong/results/popsize/ to results/popsize/
python3 scripts/m2_results.py pending --manifest scripts/manifest_popsize.tsv --outdir results/popsize/tasks --summary
python3 scripts/m2_results.py aggregate --manifest scripts/manifest_popsize.tsv --outdir results/popsize/tasks
python3 scripts/popsize_readout.py --outdir results/popsize/tasks --csv results/popsize/agg/popsize_instances.csv
```

## 5. Pre-registered reading (proposed; waits for the user's confirmation)

**Per instance and arm** (seeds 1–3; target = proven optimum or best-known):
- **S, arrival:** runs that reach the target (cost ≤ target) within 900 s;
- **C, fitness:** the median final best cost (and gap to the target);
- **T, time:** the median TTT, where a miss counts as > 900 s.

**Which arm is better on an instance, in this order** (KS2 and PP10's order,
with one change at step 3):
1. more arrivals (S); else
2. a lower median final cost (C); else
3. when both arms reach the target in ≥ 2 of 3 runs: a median TTT faster by
   a factor of **≥ 1.25**. Smaller differences are wall-clock jitter: in
   HMSE vs KS2, the same config and seeds gave equal best costs in 44 of 48
   pairs, and timing explained the rest.

Otherwise the instance is a tie.

**An arm P wins a group of instances when all three hold** (Q is the other
arm):
- **W1, overall:** P is better on more instances than Q, with a two-sided
  exact sign test over the non-tied instances at p < α.
- **W2, arrival gate:** P reaches the target in at least as many runs in
  total as Q, and the instances where Q has more arrivals are no more than
  those where P has. Wins on cost or time alone cannot outweigh lost
  arrivals (PP10's success gate).
- **W3, fitness gate:** among the instances with equal arrivals, Q has the
  lower median cost on no more instances than P. Wins on time alone cannot
  outweigh worse costs.

**Groups:**
- all 144 instances, α 0.05;
- the two R2 classes, α 0.025 each (Bonferroni over 2):
  - unweighted = MSE 2023, 67 instances;
  - weighted = MSE 2024 + rail, 77 instances.
- **The class split is fixed now,** before any result. "Weighted" is a
  feature R2 already reads at run time, so a class rule needs no new
  feature.

**Decision:**
- **Each class's pop** is the class winner; else the overall winner; else
  10, today's R4.
- **Both classes at 10:** R4 stays as it is, with no code change. The report
  says "confirmed" if pop 10 won a group, and "no effect" otherwise.
- **Both classes at 40:** R4 drops pop 10 and keeps ks2 (`auto_hparams/4`).
- **The classes differ:** R4 sets pop by class (`auto_hparams/4`).
- **Any `/4` change waits for the readout and the user's go.**

**Which instances count:** an instance counts only when all 6 of its runs are
valid:
- `ok`, stopped at the target or the time cap;
- hv 0;
- the pop R4 recorded equals the arm's.

The rest are listed, never imputed.

**Expectation [inference]:** KS2 showed no pop effect on 16 instances, so
"no effect" is the likely outcome. With ~120 non-tied instances, the sign
test detects a split of about 60/40 or stronger.

**Diagnostics (not part of the decision):**
- children and generations per run;
- the per-class tables;
- proven-target instances (17) apart from the best-known ones;
- the `pop10` arm against HMSE (same seeds, older code), as a consistency
  check.

## 6. Where pop 10 comes from (asked 2026-10-25, before the decision not to run) [verified: notes]

- **Not to be confused with PP10.** The 200 vs 10 there is
  `hard.moves.per_polish`, and both of its arms ran at pop 10.
- **R4 = pop 10 + ks2 on hard instances** (`auto_hparams/2`, 2026-10-21).
  - **The ks2 half is measured:** in KS2, ks2 vs M at pop 10 was 13 better /
    0 worse.
  - **The pop half is not.** KS2's pop comparisons showed no effect: m10 vs
    m40 8 / 5 / 3, ks2_10 vs ks2_40 8 / 7 / 1. The hints in favour of 10 are:
    - lisbon-wedding 9-18 (workstation, 300 s, single runs): 413/418 vs
      425/432 under M; 397/398/397 vs 400 under KS2; 9 vs 2 generations;
    - KS2 successes 26 vs 24 of 48.
  - **Pop 10 is the user's choice:** "use ks2 with pop10 on hard" (2026-10-21).
- **Pop 40** is the inherited S1/`allC` base value. The documents record no
  pop calibration for it either.
- **[inference]** Each child costs a full 3.5 s slot, so in a fixed budget a
  smaller population gets through more generations.
