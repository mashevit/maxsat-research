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

## 5. For the paper

- **Claim complementarity:** the memetic reaches optima that EvalMaxSAT cannot
  prove, and adding it improves coverage (85.9 % → 90.7 %) and PAR2.
- **Describe hardness as positively associated overall** (+0.64) **and weakly
  associated in the hard regime** (+0.22).
- **Don't call the solvers orthogonal** (or independent).
- Prior work for the framing:
  [`RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md`](RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md)
  (closest precedent: Hoos & Stützle, local search vs Satz in SAT, correlation
  0.26).
