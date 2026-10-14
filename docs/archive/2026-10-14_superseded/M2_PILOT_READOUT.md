# M2 pilot read-out

**Date:** 2026-10-04. The shards in `cluster_staging_maxsat/results/m2_pilot/tasks/`
(96 files) were classified with `scripts/m2_results.py`, and the aggregates
were written to `results/m2_pilot/agg/` (5 CSVs). Checks follow
`M2_DEEPPOLISH_RUN_PREPARATION.md` §8 and the handout's §7.3/§7.4 criteria.

**Provenance: the code version is unverified.** All 96 shards record
`git_sha = null`, because `MAXSAT_GIT_SHA` was not passed, and the shards
carry no source hash. `81210fc` (the M2 preparation commit) is the likely
source, but it is not confirmed. What is verified:
- **Configs.** Every shard's recorded `ea` and `ls` blocks equal the local
  config files.
- **Instances.** Every `instance_sha256` matches.

The ms-scale overshoots are consistent with the clipping edit being present
in the code that ran. The full-pool submission now requires the sha and
writes a source digest (`M2_FULL_POOL_RUN.md` §2).

**Bottom line:** the pilot is clean, and clipping works on the cluster. At
2.5 s per call the flip limit binds on every pilot instance except the 3-SAT
n = 250 one (#8). Three findings matter more than the arm comparison:
(1) a 3.5 s allowance changes nothing where the flip limit already binds,
(2) 8 of the 70 population instances are the size where 2.5 s is too short,
(3) 8 of the 10 pilot instances are trivial for every arm.

## 1. Integrity (§8.1): pass

- 96/96 shards. Classes: 90 `success`, 6 `budget_exhausted`. 0 invalid, 0
  cost_mismatch, 0 max_gens, 0 infra. `pending` gives 0 ids.
- `cpu_wall_ratio` is at least 0.95 (minimum). 10 hosts, of which
  ise-cpu-intl-18 ran 31 tasks.

## 2. Clipping on the cluster (§8.2): pass

- **0 watchdog rows** on any arm.
- Clipped arms, `budget_exhausted` rows: overshoot past 900 s is
  **0.008–0.018 s**.
- Control: one `budget_exhausted` row (#8 seed 1) at 918.37 s, an overshoot
  of 18.4 s. This matches the historical 17.2–18.6 s.
- 0 `target_after_budget` rows.

## 3. Success counts (§8.3, descriptive only: 10 instances × 3 seeds)

| arm | lower_ext (6) | tier2 (12) | upper_ext (12) | total | median TTT (s) |
|---|---:|---:|---:|---:|---:|
| control `p40_ls0p5` | 6 | 11 | 12 | **29/30** | 1.8 |
| `p40_ls2p5` | 6 | 11 | 12 | **29/30** | 1.9 |
| `p10_ls2p5` | 5 | 11 | 12 | **28/30** | 3.0 |
| `p10_ls3p5` (#5, #8 only) | — | 4/6 | — | 4/6 | 15.2 |

The handout's guard C requires new-arm successes ≥ control − 2, with no
instance going from 3/3 to 0/3. **It passes for both 2.5 s arms.**

**Only two instances separate the arms.** Failures occur on these alone:

| instance | seed | control 0.5 s | p40 2.5 s | p10 2.5 s | p10 3.5 s |
|---|---:|---:|---:|---:|---:|
| #8 `v250_k3_sr4.35` (m 1088, c\* 1) | 1 | fail | fail | 748.6 | fail |
| | 2 | 37.3 | 17.5 | 7.5 | 8.9 |
| | 3 | 150.1 | 75.1 | fail | fail |
| #9 `v150_k3_sr4.80` (m 720, c\* 2) | 1 | 24.1 | 110.4 | 5.6 | — |
| | 2 | 5.5 | 16.3 | 302.8 | — |
| | 3 | 13.1 | 42.9 | fail | — |

On these two instances the outcome depends more on the seed than on the
arm, and no ordering of the arms holds across seeds.

**The other 8 instances are trivial for every arm.** All 4 upper_ext (T3)
instances are among them, although RC2 needed 610–850 s to certify them.
All 24 runs per arm succeed, typically within 1–8 children, and many
succeed on the very first child (first-child solves: p40_ls2p5 18,
p10_ls2p5 15, control 11). On these instances the TTT mostly measures the
length of one LS call (control ≈ 0.5 s, 2.5 s arms ≈ 1.2–2.4 s), not search
quality. **RC2 certification time does not predict difficulty for the
memetic solver in this pilot.** If the full pool behaves the same way, a
TTT comparison will be dominated by per-call length, and only success
counts on a handful of instances will carry information.

## 4. Flips per call (§8.4; run means, see §6 of the preparation doc)

- **Control:** run means are 2,086–5,002 flips at about 0.50 s per child, on
  every instance. The 0.5 s allowance binds on calibration instances too,
  so the handout's **B1 holds**.
- **2.5 s arms:** the run mean is 12,500 on every instance except #8, where
  it is 10,601–11,188 at 2.504 s per child. The handout's **B2 fails only on
  #8**. #5 (m 920) reaches 12,500 at about 2.3 s.
- **Time to 12,500 flips scales with m** (wall per child, flip-limited runs):

  | m | 450–520 | 588–600 | 720–750 | 920 | 1088 |
  |---|---|---|---|---|---|
  | s per call | 1.2–1.7 | 1.4–2.1 | 1.8–2.1 | 2.25–2.40 | **2.96** (3.5 s arm) |

- **3.5 s is inert where the flip limit binds.** On #5 the p10_ls2p5 and
  p10_ls3p5 runs agree for all 3 seeds on `best_assignment_hash`,
  `children` and `total_flips`. TTT differs by ≤ 0.11 s. On #8, 3.5 s brings
  the run mean to 12,498–12,500. It did not improve success there (1/3
  against 2/3 at 2.5 s), but with 3 seeds that is noise.

**Effect on the population.** 8 of the 70 instances have m ≥ 990. All are
3-SAT n = 250: 6 at α 4.26 (m 1065; 3 lower_ext, 3 tier2) and 2 at α 4.35
(m 1088; tier2, one of which is #8). Under the 2.5 s configs, the flip
limit would not bind on any of them. The handout's §7.4 rule (about 1.2 × the
observed time to 12,500 flips, ≈ 1.2 × 2.96 s) gives **3.5 s**. That is the
value already tested.

## 5. Turnover (§8.5)

These figures are from #8, the instance where all arms run the full 900 s:

| arm | generations | children in 900 s |
|---|---:|---:|
| control | 48 | 1,824 |
| `p40_ls2p5` | 10 | 360 |
| `p10_ls2p5` | 40 | 360 |
| `p10_ls3p5` | 35 | 307 |

Pop 10 gets 4× the generations for the same number of calls. In this pilot
that bought nothing measurable.

## 6. Decision needed (§8.6)

The pre-registered §7.4 outcome is that **B2 fails only on the high-m
instances**. The allowance choice therefore comes to you. Recommendation:

1. **Use 3.5 s rather than 2.5 s for the full pool.** On the 62 instances
   with m ≤ 920 it gives the same search path as 2.5 s, as §4 shows. On the
   8 instances with m ≥ 1065 it is the only one of the two allowances under
   which the flip limit binds. The cost is about 1 s more per call on those
   8 only. Implementing it means one new config
   (`memetic_deeppolish_p40_ls3p5`, if pop 40 is kept), one line in
   `FULL_ARMS` and a rebuilt manifest: 210 tasks, ceiling 52.5 CPU-h.
2. **Population size.** The pilot cannot separate pop 40 from pop 10
   (29 vs 28 of 30, with seed-driven differences on #8 and #9). Running one
   full arm (210 tasks) rather than both halves the compute. Pop 40 keeps
   the control's population structure, so only the allowance differs.
3. **Be aware before spending 52.5 CPU-h:** most of the population may turn
   out as trivial as 8 of the 10 pilot instances. That would be a finding
   for M3 (RC2 time windows do not stratify memetic difficulty), but it
   also means the full pool will say little about the 0.5 s → 3.5 s
   change itself. A full-pool control arm (not prepared) would be needed
   for any paired comparison at that scale.

**Decided 2026-10-04:** pop 40 at 3.5 s plus a pop-40 / 0.5 s control on
the same 70 instances × seeds 1–3 (420 tasks), with pop 10 set aside. The
control is a new **clipped** 0.5 s config, so the two arms differ only in
`ls.time_limit_s`. The historical unclipped control stays unchanged and is
not re-run.
Prepared in `M2_FULL_POOL_RUN.md` and logged as Checkpoint 5 in
`CORPUS_CALIBRATION_LOG.md`.
