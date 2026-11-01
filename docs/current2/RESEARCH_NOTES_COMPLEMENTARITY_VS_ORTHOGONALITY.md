# Complementarity vs orthogonality: what the MSE 2026 results show

**Created:** 2026-11-01. **Research note** N-2026-11-01-e (indexed in
[`../current/RESEARCH_NOTES.md`](../current/RESEARCH_NOTES.md)).

> "what is difference between orthogonality and complimentarity?" / "write this somewhere i can fetch and reach, maybe in its own complementaririty research doc" (user, 2026-11-01)

Numbers are from the current readout,
[`MSE26_RHO_RESULTS_3.md`](MSE26_RHO_RESULTS_3.md) (readout 3), `fail` column unless
stated. The preliminary values are in
[`MSE26_RHO_PRELIM_RESULTS.md`](MSE26_RHO_PRELIM_RESULTS.md) §10–11.

## 1. The two notions

They measure different things.

**Orthogonality** asks: if an instance is hard for EvalMaxSAT, is it also hard for
the memetic?
- It is measured with a rank correlation (ρ) over all instances. Orthogonal
  means ρ ≈ 0: knowing one solver's time tells you nothing about the other's.
- Claiming it needs positive evidence: a CI that is narrow and around 0. A ρ
  that just isn't significant is not enough (prereg §7,
  [`MSE26_RHO_PREREG.md`](MSE26_RHO_PREREG.md): no "orthogonal" or
  "independent" claim from a non-significant ρ; "at most weak monotone
  association" needs the CI inside (−0.3, +0.3)).

**Complementarity** asks: does each solver solve instances the other does not, so
that running both beats running either one?
- It is measured with outcomes, not correlation: the instances only one solver
  solves, a McNemar test on them, and the gain in coverage or PAR2 from taking
  the better of the two per instance (the virtual best).

## 2. They can come apart either way

| case | orthogonal? | complementary? |
|---|---|---|
| hardness unrelated, but one solver is always better | yes | no: running both gains nothing |
| hardness correlated, but each solves some instances the other can't | no | yes |

## 3. Our results are the second case

**Not orthogonal overall.**
- Primary ρ = **+0.637, 95 % CI [+0.588, +0.680]** (N 922; `exclude` +0.632
  [+0.584, +0.677], N 884). Both solvers broadly agree on what is easy and what
  is hard.
- In the hard regime they agree only weakly: window (30, 3600] s, both solved,
  ρ = **+0.223 [+0.078, +0.362]** (N 184).
- The drop comes from the 30 s lower bound, not from the failures: with both
  solved and no lower bound (E1) ρ = +0.634.

**Complementary.** The memetic only *reaches* the optimum (no proof), and still:
- **44 instances only the memetic reaches**, against **262 only EvalMaxSAT
  proves** (McNemar exact p ≈ 6 × 10⁻³⁹);
- coverage rises from **85.9 % to 90.7 %** (EvalMaxSAT alone → either solver);
- mean PAR2 drops from **1,296 s to 978 s** (EvalMaxSAT → per-instance best of
  the two);
- the memetic reaches **a third of EvalMaxSAT's timeouts** (44 / 130 = 33.8 %
  [25.8, 42.7]);
- memetic reach falls steadily with EvalMaxSAT time: 97 % → 78 % → 59 % → 36 %
  over the bands (0, 1], (1, 30], (30, 300], (300, 3600] s
  (Cochran–Armitage p ≈ 3 × 10⁻⁴⁰).

## 4. Where E4 fits

E4 = EvalMaxSAT above 30 s (timeouts included), at most one solver failing
(exploratory, not pre-registered):

| readout | `fail` | `exclude` |
|---|---|---|
| preliminary (§11) | **+0.068 [−0.032, +0.167]**, N 434 | +0.039 [−0.063, +0.142], N 395 |
| readout 3 | +0.064 [−0.037, +0.161], N 435 | +0.039 [−0.062, +0.141], N 400 |

- ρ is around 0 and the interval includes 0. This is **complementarity seen as a
  rank statistic**: it is driven by the instances where exactly one solver fails
  (44 only the memetic, 207 only EvalMaxSAT; 184 both solved).
- It is **not orthogonality**: the subset is chosen by the outcome, and 58 % of
  its instances (251 / 435) are tied at the failure rank on one axis. So it
  mostly says **which solver fails, not how hardness is ordered**.
- By the prereg's label, E4 is "at most weak monotone association" (CI inside
  (−0.3, +0.3)), and ρ ≈ 0 rules out only a *monotone* link, not every kind of
  dependence.

## 5. E4 in the preliminary readout and in readout 3

> "add this E4 comparison to the complementarity doc … write in your own words exactly what happened … note also that N is bigger, and rho is closer to 0 to say more exact for complimentarity" (user, 2026-11-01)

| | preliminary, `fail` | readout 3, `fail` | preliminary, `exclude` | readout 3, `exclude` |
|---|---|---|---|---|
| ρ [95 % CI] | +0.068 [−0.032, +0.167] | **+0.064 [−0.037, +0.161]** | +0.039 [−0.063, +0.142] | **+0.039 [−0.062, +0.141]** |
| N | 434 | **435** | 395 | **400** |
| only memetic (x = ∞) | 43 | 44 | 43 | 44 |
| only EvalMaxSAT (y = ∞) | 208 | 207 | 171 | 173 |
| both solved | 183 | 184 | 181 | 183 |
| tied at the failure rank | 251 (57.8 %) | 251 (57.7 %) | 214 (54.2 %) | 217 (54.3 %) |
| prereg label | at most weak | at most weak | at most weak | at most weak |

### 5.1 What happened between the two readouts

The preliminary readout was computed on batch 3c as it came back, with 118 runs
that ended in an error. Readout 3 includes the cases that could be recovered:

- **Recovered by a fix (group A, 2 instances, 6 runs).** All 3 seeds of two small
  kbtree instances crashed inside the Glucose library (repeated assumptions
  overran an internal array). After the fix the 6 runs were redone on the
  workstation and gave real records:
  - `27770a63` (EvalMaxSAT timeout): the memetic reached the optimum on seed 2.
    Before, under `fail`, all 3 seeds counted as failures, so the instance was
    both-∞ and outside E4. Now it is **memetic-only** (43 → 44).
  - `d1a8db71` (EvalMaxSAT proved at 3,132 s): reached on seed 2. Before, under
    `fail`, it was wrongly EvalMaxSAT-only; now it is **both solved**
    (208 → 207, 183 → 184).
- **Recovered by evidence (group D, 4 instances, 5 runs).** These runs were
  killed at the 1 h Slurm limit without a record, long past their 1,800 s CPU
  budget, so they cannot have reached the optimum in time: they now count as
  failures (`slurm_wall_kill`). Under `fail` they were already failures, so
  nothing changes there. Under `exclude` their instances were dropped before and
  now enter: 3 are in E4 (`cf864e2f` both solved, because another seed reached
  the optimum; `05347087` and `96d20fa0` EvalMaxSAT-only); the fourth
  (`847b49a5`) has EvalMaxSAT at 3.4 s, below the 30 s bound.
- **Not recovered (group B, 38 instances, 107 runs).** Glucose found no
  hard-feasible start within the budget. These stay errors: `fail` counts them as
  failures, `exclude` drops the 38 instances. 35 of them are in E4 under `fail`
  (34 EvalMaxSAT-only, 1 both solved); 3 are both-∞ and outside it.

So under `fail` E4 gains one instance and one instance moves to its correct cell;
under `exclude` E4 gains 5 instances (395 → 400).

### 5.2 How many seeds enter ERT and PAR2

**Every instance in ρ uses all 3 seeds** in ERT and PAR2. No instance is computed
on fewer seeds: a failed seed is charged the budget (ERT: +1,800 s; PAR2:
3,600 s), and one success makes y finite. What differs is where the seed
outcomes come from:

| instances | seeds | where the outcome comes from |
|---|---|---|
| 2 (group A: `27770a63`, `d1a8db71`) | all 3 | workstation runs with the fix (another machine's CPU clock); 1 of 3 reached the optimum on each |
| 4 (group D: `05347087`, `847b49a5`, `96d20fa0`, `cf864e2f`) | 5 seeds in all (1 each; 2 for `96d20fa0`) | no record: failure inferred from the Slurm kill; the other seeds are real records |
| 38 (group B, `fail` only) | 107 seeds | real records (`glucose_timeout`, CPU ≈ budget), counted as failures; one of them, `6ca66e97` (planning-bnn), has 2 successes and stays reached |
| all others | 3 | real cluster records |

Under `exclude` the 38 group B instances are out, so every instance there has 3
seeds with a record or a group D inferred failure.

### 5.4 The Slurm-kill instances seed by seed, and where they are in ρ

"4 Slurm kills, 5 seeds" means 4 instances with 5 killed runs: one instance had
2 seeds killed, the other three had 1 each. Only the killed seeds have no
record; every other seed is a normal cluster record.

| instance | EvalMaxSAT x | killed seed(s) | the other seeds | memetic y |
|---|---|---|---|---|
| `96d20fa0` (PRBAC) | 569.8 s | **s1, s3** | s2 watchdog failure | ∞ |
| `05347087` (PRBAC) | 487.3 s | **s1** | s2, s3 watchdog failures | ∞ |
| `847b49a5` (PRBAC) | 3.4 s | **s1** | s2, s3 budget used up | ∞ |
| `cf864e2f` (planning-bnn) | 988.0 s | **s2** | s1 budget used up, **s3 reached at 740.8 s** | 4,340.8 s |

**Where these 4 instances are in ρ:**

| readout | `fail` | `exclude` |
|---|---|---|
| preliminary | all 4 in ρ (killed seeds counted as failures) | **none of the 4 in ρ** (an instance with a missing run was dropped) |
| readout 3 | all 4 in ρ (unchanged) | **all 4 in ρ** (killed seeds are now final failures) |

In the primary ρ all 4 count. In E4 (EvalMaxSAT above 30 s) 3 of them count;
`847b49a5` is in the primary ρ but outside E4, because EvalMaxSAT proved it in
3.4 s.

**An instance where the optimum was reached on one seed and other seeds failed
or errored keeps all 3 seeds in ρ.** ERT adds the effort of every seed, so each
failed or errored seed is charged the 1,800 s budget, and the successes alone
are the divisor:

- `cf864e2f` (killed s2, failed s1, success s3): y = (1,800 + 1,800 + 740.8) / 1
  = **4,340.8 s**, so the instance counts as reached, in both columns of
  readout 3 (it was dropped from `exclude` in the preliminary readout).
- `6ca66e97` (planning-bnn, a Glucose timeout on s3, successes on s1 at 913.6 s
  and s2 at 1,612.1 s): under `fail` y = (913.6 + 1,612.1 + 1,800) / 2 =
  **2,162.8 s**, reached. Under `exclude` it is dropped in both readouts,
  because Glucose timeouts stay errors.
- PAR2 likewise averages all 3 seeds (a failed or errored seed counts 3,600 s).

### 5.3 What the comparison says

- **N is bigger** (435 vs 434; 400 vs 395) and the data is more complete: fewer
  outcomes come from errors, and the one instance misplaced by the crash
  (`d1a8db71`) is now in its correct cell.
- **ρ is as close to 0 or closer:** `fail` +0.068 → +0.064, `exclude` +0.039 →
  +0.039. **The upper CI bound is a little lower** (+0.167 → +0.161 and +0.142 →
  +0.141), so readout 3 bounds the possible monotone association above 30 s a
  bit more tightly.
- The changes are small (≤ 0.006). The result is the same and now rests on more
  complete data: above 30 s, with failures counted on either side, **ρ is around
  0 and its 95 % interval includes 0**. This is complementarity seen as a rank
  statistic, not orthogonality (§4).

## 6. For the paper

- **Claim complementarity:** the memetic reaches optima that EvalMaxSAT cannot
  prove, and adding it improves coverage (85.9 % → 90.7 %) and PAR2.
- **Describe hardness as positively associated overall** (+0.64) **and weakly
  associated in the hard regime** (+0.22).
- **Don't call the solvers orthogonal** (or independent).
- Prior work for the framing:
  [`RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md`](RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md)
  (closest precedent: Hoos & Stützle, local search vs Satz in SAT, correlation
  0.26).
