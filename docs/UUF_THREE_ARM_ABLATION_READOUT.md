# Three-arm ablation on SATLIB uuf250/uuf200: uniform multistart vs JW multistart vs memetic

**Date:** 2026-10-06. **Data:** the JW-seeded multistart array returned today
(`results/tier2_local_multistart_jw_all.jsonl`, consolidated from
`results/tier2_local_multistart_jw/tasks/`), plus the two existing arms.
**Analysis:** `scripts/uuf_three_arm_ablation.py`, outputs in
`results/tier2_uuf_ablation/`. Paths starting with `results/` or `scripts/`
are relative to `cluster_staging_maxsat/`.

This closes the gap named in `docs/archive/TIER2_ABLATION_FAIRNESS_AUDIT.md`
§5(a): "the JW-seeded control designed to remove the seeding confound was
never run". It does **not** close item 3 of
`docs/M2_FULL_POOL_READOUT_AND_STATE.md` §10, which asks for the no-EA
baselines on the 70-instance **calibration pool**; these runs are on the 26
historical SATLIB instances only.

---

## 0. Summary

- **JW seeding helps multistart modestly.** Per-instance ERT ratio JW/uniform
  has geometric mean **0.78** (95 % CI 0.59–1.06); JW is better on 17/26
  instances. A log-rank test on per-run time to target, stratified by
  instance, gives p = 0.05 (seconds) and p = 0.04 (polish calls). The
  direction is consistent across every measure; the size (~20 %) is not
  established at N = 26.
- **Most of memetic's advantage is not seeding.** Measured as
  log ERT, about **37 %** of the whole-package gain of `memetic_deeppolish`
  over uniform multistart comes from JW seeding and about **63 %** from the
  rest (population, the majority-polarity crossover, inheritance of polished
  parents). Memetic vs JW multistart: ERT ratio **0.65** (CI 0.41–1.04) in
  seconds, **0.58** (0.37–0.93) in flips.
- **Memetic's biggest wins are on instances where JW gives nothing.** The
  per-instance JW gain and the per-instance memetic gain are only weakly
  related (Spearman 0.18, CI −0.30 to 0.58). On uuf250-0100, -097 and -090,
  memetic is 8–12× faster than uniform; JW multistart is equal or slower.
- **Memetic is faster in a typical run, but fails more.** Kaplan–Meier median
  time to target: memetic 30 s, JW 90 s, uniform 112 s. Successes: memetic
  118/130, uniform 124/130, JW **127/130** (memetic vs JW, Fisher p = 0.03,
  ignoring clustering). Memetic's failures are population stalls at c\* + 1
  (audit §5).
- **ρ(RC2, ERT) for the JW arm** is +0.34 (Bonett–Wright CI −0.06 to 0.65),
  against +0.14 (uniform) and +0.19 (memetic). All three CIs overlap
  heavily; nothing in the read-out's §7.4 conclusion changes.
- **What the "rest" still contains.** mem/JW is not a pure test of selection
  and recombination: it also contains the crossover acting as a deterministic
  majority-polarity heuristic, and continuation from polished parents (audit
  §5(b), (c)). The iterated-local-search control the audit proposes is still
  needed to separate those.

---

## 1. Arms and data

| arm | config_id | init | search | run | date |
|---|---|---|---|---|---|
| uni | `local_multistart_deeppolish` | uniform coins per restart | restart, polish, discard | array 20721254 | 2026-08-30 |
| jw | `local_multistart_jw_deeppolish` | JW-biased draw per restart | restart, polish, discard | array 22314854 | 2026-10-06 |
| mem | `memetic_deeppolish` | JW population of 40 | EA, every child polished | array 20085583 | 2026-08-12 |

Common: 26 instances × seeds 1–5, 900 s budget, stop at the certified
optimum, the same `short_polish` call (0.5 s of WalkSAT, the 12 500-flip cap
never binds; audit §1). The jw and uni configs differ only in
`multistart.init` (asserted by `test_jw_config_is_the_uniform_config_but_for_init`).

**Integrity of the JW array (checked today).**
- 130/130 shards, one row each, matching the manifest row for row
  (job id, instance, seed, config_id); `config_hash` `6ed7ad26cbf0f0f9` on
  all rows; `multistart.init = jw` on all rows.
- Same (instance, seed) grid as the uniform arm.
- `status = ok` on all; 127 `target`, 3 `time_cap` (900.12–900.17 s);
  0 hard violations; no best cost below the oracle.
- 11 hosts, 2026-10-06 12:31–12:51 (+03:00).
- `git_sha` is null, as in both earlier arms (`MAXSAT_GIT_SHA` was not
  exported by this sbatch). The staging `src/evo/multistart.py` has not
  changed since `404b7e6` (2026-08-30), so the code is the reviewed JW code,
  by the same date/hash argument as audit §0.

**Node speed.** The three arms ran on different days and node mixes. The
analysis therefore reports ERT in three units: wall seconds, **polish
calls** (restarts or children; each is a fixed 0.5 s, so the count is
insensitive to node speed) and flips (iterations; proportional to node
speed at fixed time). Median iterations per polish: uni 2 250, jw 2 321
(+3 %). The seconds and polish-call results agree to within 0.3 %
everywhere; flips differ slightly because the JW array's nodes were a little
faster.

---

## 2. Pairwise ERT ratios (`results/tier2_uuf_ablation/pairwise_ert_ratios.csv`)

ERT per instance = Σ over 5 seeds of effort spent (failures charged their
full spend: 900 s, all their polishes or flips) / successes. No instance has
0 successes on any arm, so N = 26 throughout. CI = percentile bootstrap over
instances, stratified by source group, B = 10 000, seed 20261006.

| comparison (factor) | unit | geomean ratio | 95 % CI | median ratio | first better / second better | Wilcoxon p |
|---|---|---:|---|---:|---|---:|
| jw / uni (JW initialisation) | s | **0.782** | 0.593–1.058 | 0.723 | 17 / 9 | 0.056 |
| | polish | 0.783 | 0.596–1.054 | 0.723 | 17 / 9 | 0.056 |
| | flips | 0.829 | 0.625–1.129 | 0.784 | 17 / 9 | 0.150 |
| mem / jw (population, crossover, inheritance) | s | **0.653** | 0.406–1.037 | 0.585 | 17 / 9 | 0.129 |
| | polish | 0.655 | 0.411–1.029 | 0.582 | 17 / 9 | 0.123 |
| | flips | 0.584 | 0.368–0.933 | 0.497 | 18 / 8 | 0.038 |
| mem / uni (whole package) | s | **0.511** | 0.327–0.802 | 0.598 | 16 / 10 | 0.014 |
| | polish | 0.512 | 0.328–0.819 | 0.596 | 16 / 10 | 0.014 |
| | flips | 0.484 | 0.308–0.766 | 0.537 | 17 / 9 | 0.011 |

**Cross-check with the audit.** mem/uni in seconds is 1/0.511 = 1.96; the
audit reproduced 1.947 with raw wall time (memetic's failures run to
~918 s, here capped at 900 s). The flip ratio 1/0.484 = 2.07 equals the
audit's figure.

## 3. Time to target per run (`summary.json` → `survival`)

Failures are right-censored at 900 s (or at their polish count).

| | uni | jw | mem |
|---|---:|---:|---:|
| successes / 130 | 124 | **127** | 118 |
| Kaplan–Meier median TTT (s) | 112 | 90 | **30** |
| Kaplan–Meier median polish calls | 223 | 179 | **59** |

Log-rank, stratified by instance (O − E is for the first arm; positive =
reaches the target sooner than expected):

| comparison | unit | O − E | χ² | p |
|---|---|---:|---:|---:|
| jw vs uni | s | +13.7 | 3.86 | 0.050 |
| | polish | +14.0 | 4.08 | 0.043 |
| mem vs jw | s | +30.2 | 20.1 | < 0.001 |
| mem vs uni | s | +30.3 | 20.9 | < 0.001 |

Pooled success counts (Fisher exact, ignores clustering by instance;
descriptive): jw vs uni p = 0.50; mem vs jw p = 0.03; mem vs uni p = 0.22.

**Reading.** The log-rank test weights the early part of the TTT
distribution, where memetic dominates; ERT also charges the 900 s
failures, where memetic is worst. That is why memetic vs JW is decisive by
log-rank but has an ERT CI touching 1.

## 4. Decomposition (`summary.json` → `decomposition`)

log(mem/uni) = log(jw/uni) + log(mem/jw), per instance, exactly. Averaged
over instances:

| unit | mean log(mem/uni) | share from JW init | share from the rest |
|---|---:|---:|---:|
| s | −0.672 | 0.37 | 0.63 |
| polish | −0.669 | 0.37 | 0.63 |
| flips | −0.725 | 0.26 | 0.74 |

Is the JW gain located where the memetic gain is? Spearman of
log(jw/uni) with log(mem/uni) across instances: **0.18** (s; percentile CI
−0.30 to 0.58), 0.17 (polish), 0.24 (flips). Weak at best.

**Per instance** (ERT s, successes in brackets; sorted by RC2 time; from
`instance_table.csv`):

| instance | RC2 s | uni | jw | mem | jw/uni | mem/jw |
|---|---:|---:|---:|---:|---:|---:|
| uuf250-072 | 63 | 20.5 (5) | 43.2 (5) | 25.3 (5) | 2.11 | 0.59 |
| uuf250-03 | 68 | 16.8 (5) | 27.4 (5) | 18.8 (5) | 1.63 | 0.68 |
| uuf250-089 | 71 | 94.4 (5) | 31.3 (5) | 14.3 (5) | 0.33 | 0.46 |
| uuf250-05 | 76 | 472.0 (4) | 351.6 (5) | 42.9 (5) | 0.75 | 0.12 |
| uuf250-079 | 81 | 171.3 (5) | 169.7 (5) | 125.1 (5) | 0.99 | 0.74 |
| uuf250-066 | 107 | 138.6 (5) | 50.1 (5) | 245.4 (4) | 0.36 | 4.90 |
| uuf250-071 | 107 | 618.8 (4) | 334.1 (5) | 622.0 (3) | 0.54 | 1.86 |
| uuf250-081 | 111 | 794.3 (3) | 179.6 (5) | 97.5 (5) | 0.23 | 0.54 |
| uuf250-010 | 121 | 209.2 (5) | 71.7 (5) | 28.2 (5) | 0.34 | 0.39 |
| uuf250-093 | 128 | 12.4 (5) | 83.8 (5) | 21.5 (5) | 6.78 | 0.26 |
| uuf250-099 | 128 | 329.7 (5) | 139.6 (5) | 258.3 (4) | 0.42 | 1.85 |
| uuf200-02 | 129 | 11.7 (5) | 8.2 (5) | 9.2 (5) | 0.70 | 1.11 |
| uuf250-094 | 130 | 68.1 (5) | 32.3 (5) | 29.0 (5) | 0.47 | 0.90 |
| uuf250-070 | 146 | 325.9 (5) | 110.2 (5) | 617.3 (3) | 0.34 | 5.60 |
| uuf250-096 | 149 | 348.3 (5) | 143.1 (5) | 428.2 (4) | 0.41 | 2.99 |
| uuf250-090 | 151 | 287.1 (5) | 304.4 (5) | 37.4 (5) | 1.06 | 0.12 |
| uuf250-07 | 155 | 141.2 (5) | 78.3 (5) | 45.2 (5) | 0.55 | 0.58 |
| uuf250-06 | 185 | 259.9 (5) | 148.1 (5) | 35.7 (5) | 0.57 | 0.24 |
| uuf250-080 | 212 | 248.3 (5) | 408.0 (4) | 674.9 (3) | 1.64 | 1.65 |
| uuf250-0100 | 219 | 223.2 (5) | 454.7 (5) | 28.3 (5) | 2.04 | 0.06 |
| uuf250-075 | 270 | 53.1 (5) | 29.0 (5) | 17.0 (5) | 0.55 | 0.58 |
| uuf200-01 | 307 | 63.3 (5) | 95.4 (5) | 388.4 (4) | 1.51 | 4.07 |
| uuf250-098 | 311 | 399.3 (4) | 448.7 (4) | 628.5 (3) | 1.12 | 1.40 |
| uuf250-09 | 384 | 219.6 (5) | 194.3 (5) | 53.2 (5) | 0.89 | 0.27 |
| uuf250-087 | 437 | 44.9 (5) | 39.2 (5) | 22.0 (5) | 0.87 | 0.56 |
| uuf250-097 | 496 | 484.7 (4) | 607.4 (4) | 40.6 (5) | 1.25 | 0.07 |

Two patterns stand out:
- **Memetic's largest wins** (mem/jw ≤ 0.12: -0100, -097, -05, -090) are
  not seeding effects; JW multistart is no better than uniform on three of
  the four.
- **Memetic's losses** (mem/jw > 1.8: -066, -070, -096, -071, -099,
  uuf200-01) are its stall failures. On five of those six, JW multistart is
  *better* than uniform. So on these instances the JW prior is useful, and
  something in the EA layer turns it into a stall.

## 5. ρ(RC2 solve_s, ERT) per arm (`results/tier2_uuf_ablation/rho_rc2_vs_ert.csv`)

| arm | ρ (s) | Bonett–Wright CI | plain bootstrap CI |
|---|---:|---|---|
| uni | +0.139 | −0.26, 0.50 | −0.34, 0.53 |
| jw | **+0.343** | −0.06, 0.65 | −0.10, 0.71 |
| mem | +0.187 | −0.22, 0.54 | −0.23, 0.55 |

uni and mem reproduce `results/m2_full_p40/analysis/uuf_tier2_rho.csv`
exactly. c\* is 1 on 24/26 instances, so every ρ here is driven by RC2's
per-call cost; see the read-out §7.4.

## 6. Threats to validity

- **N = 26, 5 seeds.** The JW effect (~20 %) sits at the edge of
  detectability; only the whole-package contrast is clearly established by
  ERT.
- **Different days and node mixes.** Mitigated by the polish-call unit,
  which agrees with seconds to < 0.3 %. Hosts are not stratified.
- **Seed pairing is nominal.** The same seed gives unrelated trajectories in
  different arms, so no run-level pairing is used; instances are the unit.
- **The JW prior is weak on uniform random 3-SAT** (mean |p − 0.5| ≈ 0.115,
  `more_data/CORPUS_BROADENING_HANDOFF.md` §6b). An effect of this size here
  says little about structured instances, where it could be much larger.
- **No recorded commit SHA**, as for both earlier arms.

## 7. Consequences

1. The audit's summary sentence can now be sharpened: of the 1.95× package
   advantage, roughly a third (in log terms) is JW seeding; the rest is the
   EA layer **plus** the crossover-as-heuristic **plus** continuation. The
   rest is still not attributable to selection and recombination alone.
2. **Next control, if attribution matters:** iterated local search from the
   JW start (restart from best with a small perturbation,
   `SatState.restart_partial_from_best`), same 0.5 s polish. It holds
   seeding and continuation fixed and removes the population.
3. **For the calibration study (M2/M3):** the historical uuf result now
   includes the JW arm. The calibration-pool baseline (§10.3 of the
   read-out) is still the open item; the JW arm should be run there together
   with the uniform arm, at the M2 polish settings.

## 8. Reproduce

From `cluster_staging_maxsat/`, about 6 s:

```bash
python3 scripts/uuf_three_arm_ablation.py
```

Fixed bootstrap seed 20261006, so reruns are identical.

| file | rows | content |
|---|---:|---|
| `results/tier2_local_multistart_jw_all.jsonl` | 130 | JW arm, one run per row (same schema as `tier2_local_multistart_all.jsonl`) |
| `results/tier2_uuf_ablation/instance_table.csv` | 26 | per instance: RC2, and per arm successes, ERT in s / polish / flips, flips per polish, per-seed TTT; all pairwise ratios |
| `results/tier2_uuf_ablation/pairwise_ert_ratios.csv` | 9 | §2 table |
| `results/tier2_uuf_ablation/rho_rc2_vs_ert.csv` | 9 | §5 table, all units |
| `results/tier2_uuf_ablation/summary.json` | — | survival, decomposition, pairwise |
