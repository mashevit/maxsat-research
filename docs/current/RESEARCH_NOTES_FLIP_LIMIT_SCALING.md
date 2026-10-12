# Research note: is there a known value for c in a flip limit of c · n?

**Date:** 2026-10-12. **Note id:** N-2026-10-12-b. **Status:** literature
report; nothing run.

**Request (user, 2026-10-12)** [quote]: "research now if a c coefficient for
size aware flip limit has some scientific research results known"

**Context.** HP-1 has fixed the form of the rule:
`ls_polish_flips(n) = max(12500, c · n)`
(`HYPERPARAMETER_CALIBRATION_PLAN.md` §0). The user proposes c = 15 for the
first large instances (§0a there). The question is whether the literature
gives a value of c, or at least a scaling law.

**Labels:**
- **[read]**: read in the paper's full text (copies fetched 2026-10-12);
- **[abstract]**: read from the abstract or a summary page only;
- **[inference]**: my reading of what the source means for us.

## 1. Short answer

**No published result gives a constant c for a per-call flip limit c · n
in a memetic or iterated MaxSAT solver.** What the literature does give:

1. **Flips per variable is the natural unit, but only in an easy regime.**
   On *satisfiable* random formulas, below a regime-dependent density,
   WalkSAT-type search needs a number of flips linear in n. The constant
   depends on the density and grows towards the threshold. This is
   proven for random 2-SAT and observed for random 3-SAT (§2.1).
2. **Where it has been measured, the best restart cut-off is not linear in
   n.** For WalkSAT at the random 3-SAT threshold, the optimal Maxflips
   grows as about n^2.4. That is 21 flips per variable at n = 100 and 109
   at n = 400 (§2.2).
3. **A successful MaxSAT solver sets several parameters in proportion to
   n**, but none of them is a fixed flip budget per call. IRoTS ends its
   local-search phase after n²/4 steps *without improvement*, perturbs for
   9n/10 steps, and uses tabu tenure n/10 + 4 (§2.3).
4. **Memetic-algorithm theory says local-search depth matters, but gives no
   formula.** On constructed problems, a factor of 2 in depth or frequency
   separates polynomial from exponential time (§2.4).
5. **Our regime has no result.** Large-n random Max-2-SAT *above* the
   threshold (α 1.10–1.20, unsatisfiable, optimum c\* 9–14) is not
   covered. The 2-SAT linear-time theorem stops at α < 1 (§2.1).

**So c = 15 cannot be taken from the literature. It has to be calibrated.**
The literature does support three points:
- the c · n form is a reasonable first model;
- c depends on the instance family and density, not only on n;
- a stall-based end to a call ("stop after k · n flips without
  improvement") is the established alternative to a fixed budget.

## 2. Sources

### 2.1 Linear-time local search on satisfiable random formulas

- **Berenbrink, Coja-Oghlan, Cooper, Götte, Hintze, Zakharov: "WalkSAT is
  linear on random 2-SAT"** (arXiv:2412.04156, 2024, revised 2025)
  [abstract + theorem statement].
  - Theorem 1.1: there is a constant C > 0 such that, for all 0 ≤ α < 1,
    the expected number of flips is at most C · n / (1 − α)², with high
    probability over the formula.
  - The bound diverges as α → 1. The authors also report experiments in
    which the empirical constant grows slowly as α approaches 1.
  - Earlier bound: O(n²) for any satisfiable 2-CNF (Papadimitriou, FOCS
    1991).
  - **Nothing is claimed for α > 1**, where our instances lie.
- **Seitz, Alava, Orponen: "Focused local search for random
  3-satisfiability"** (J. Stat. Mech. 2005, P06006; arXiv cond-mat/0501707)
  [summary of the text].
  - WalkSAT and FMS solution times normalised by N converge to a constant
    as N grows (N = 10⁴ to 10⁶), up to about α ≈ 4.15–4.2 with tuned noise.
  - Just above that, normalised times grow with N.
  - No t/N values are tabulated; the results are figures only.
- **Semerjian, Monasson: "Relaxation and metastability in a local search
  procedure for the random satisfiability problem"** (Phys. Rev. E 67,
  066103, 2003) [abstract].
  - RandomWalkSAT's time is τ(α) · N below a threshold α_d, and
    exponential in N above it, where the search is trapped on a plateau.

**[inference] For us:** in the easy regime, "flips per variable" is the
right unit, which supports the c · n form. But the constant is set by the
density and the noise. Near and above the threshold, linear scaling breaks
down.

### 2.2 Optimal restart cut-off (Maxflips), measured

- **Parkes, Walser: "Tuning local search for satisfiability testing"**
  (AAAI-96) [read].
  - Setting: WSAT/SKC, noise p = 0.5, satisfiable random 3-SAT at the
    crossover, n = 25–400, 1k–10k instances per n.
  - The optimal Maxflips m\* grows as a·n^b, fitted with a = 0.02 and
    b = 2.39 (WSAT/G: n^2.36). They cite n^1.65 for HSAT
    (Gent & Walsh 1995).
  - From their Table 1, m\*/n is 21 at n = 100, 60 at n = 200, 77 at
    n = 300 and 109 at n = 400.
  - **The setting is flat for the right algorithm.** For WSAT/SKC, even
    Maxflips = ∞ costs only about 20 % over the optimum (WSAT/G: 4×).
    Noise ("random walk") makes the choice of cut-off much less critical.
  - In their words: "There are no known fundamental rules for how to set
    it." They also write that for general SAT the scaling "is of course not
    a simple function of the number of variables and p only".

**[inference] For us:**
- **Not our setting.** Their Maxflips is a restart cut-off for a
  satisfiable decision problem. Ours is a per-call polish budget inside a
  population of optimisation runs.
- **The scaling is the useful part.** It shows that the best budget can
  grow faster than n. A single c fitted at one n may be too small at a
  larger n.
- **The flatness matters too.** With a noisy walk, an overlong budget costs
  little, but a short one can cost a lot. That argues for erring high on c.

### 2.3 MaxSAT local search with n-scaled parameters

- **Smyth, Hoos, Stützle: "Iterated Robust Tabu Search for MAX-SAT"**
  (Canadian AI 2003, LNCS 2671) [read].
  - Local-search phase: "RoTS steps until no improvement in the incumbent
    solution has been achieved for escape_threshold iterations". The
    default is **n²/4**, "determined to give robust performance over a
    wide range of test sets".
  - Tabu tenure n/10 + 4. Perturbation: a fixed **9n/10** RoTS steps with
    tenure n/2. A variable unflipped for 10n steps is forced.
  - "Many of the Random-3-SAT instances are optimally solved within the
    first RoTS local search phase."
  - Tested only at n ≤ 200, on random 3-SAT, including overconstrained
    unweighted Max-3-SAT.
  - **On structured instances the defaults did poorly:** the authors set
    the escape threshold to a fixed 100 steps and changed the perturbation.

**[inference] For us:**
- **This is the closest MaxSAT analogue.** Its local-search length is
  stall-based and quadratic in n, not a fixed budget linear in n. At
  n = 16,000, n²/4 is 64 million non-improving steps, so the quadratic
  rule cannot carry over to our sizes as it stands.
- **The structured-instance result is a warning.** n-scaled defaults that
  work on random formulas may not transfer to other families.

### 2.4 Memetic algorithms: local-search depth

- **Sudholt**, the ISAAC 2006 paper on local-search frequency and the
  chapter "Parametrization and balancing local and global search"
  (Handbook of Memetic Algorithms, 2012) [abstract].
  - Frequency and depth are the two balancing parameters.
  - Constructed problems exist where a factor of 2 in frequency decides
    between polynomial and exponential time.
  - Too much local search loses population diversity.
  - No problem-independent rule is given.
- **DEMaxSAT** (an open-source differential-evolution / GSAT MaxSAT solver)
  [abstract]. Local-search steps are a fraction of n (default 1 %),
  capped at 100 per call. This is an implementation default, not a
  result.

## 3. What this means for HP-1 [inference]

1. **Keep c · n, and calibrate c.** There is no published c to adopt. Our
   own fixed 12,500 corresponds to c = 50 at n = 250 and c ≈ 31 at
   n = 400, where it is known to work. At n = 16,000 and 64,000 it is
   c = 0.78 and 0.2.
2. **c = 15 is a defensible first point, not a derived one.** It lies
   between the 200k arm (c = 12.5 at n = 16,000; c = 3.1 at n = 64,000)
   and the c ≈ 31–50 that works at small n.
   - Parkes & Walser's superlinear scaling suggests the best c may itself
     grow with n. If so, c = 15 is more likely too low than too high at
     n = 64,000.
3. **Check the 3.5 s time cap.**
   - At c = 15, a call at n = 64,000 is 960,000 flips. At the measured
     270k–500k v2 flips/s that is about 1.9–3.6 s, so **the 3.5 s
     `ls.time_limit_s` would end some calls before the flip limit**.
   - At n = 16,000 (240,000 flips; about 0.5–0.9 s) it does not bind.
   - Any c = 15 run must record which limit ended each call, or raise the
     time cap.
   *Correction 2026-10-12 (N-2026-10-12-d): the cluster runs about
   190k–235k flips/s, not the workstation's ~300k. At n 64,000, c = 15
   is about 5 s per call there, so the 3.5 s cap would always bind.*
4. **Test the stall-based alternative.** IRoTS's design suggests trying
   "stop after k · n flips without improvement" next to a fixed c · n
   budget. It matches the earlier note that a polish could keep going
   while it still improves
   (`RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`).
5. **c may depend on the family.** The linear-time constant depends on α,
   and IRoTS's defaults failed on structured instances. A single c across
   random Max-2-SAT, Max-3-SAT and MSE families is a hypothesis to test,
   not an assumption.

## 4. Sources

- Berenbrink, Coja-Oghlan, Cooper, Götte, Hintze, Zakharov. WalkSAT is
  linear on random 2-SAT. arXiv:2412.04156 (2024).
  https://arxiv.org/abs/2412.04156
- Seitz, Alava, Orponen. Focused local search for random 3-satisfiability.
  J. Stat. Mech. (2005) P06006. https://arxiv.org/abs/cond-mat/0501707
- Semerjian, Monasson. Relaxation and metastability in a local search
  procedure for the random satisfiability problem. Phys. Rev. E 67,
  066103 (2003). https://arxiv.org/abs/cond-mat/0301272
- Parkes, Walser. Tuning local search for satisfiability testing.
  AAAI-96. https://www.ps.uni-saarland.de/Publications/documents/ParkesWalser96.pdf
- Smyth, Hoos, Stützle. Iterated Robust Tabu Search for MAX-SAT.
  Canadian AI 2003, LNCS 2671, 129–144.
  https://www.cs.ubc.ca/~hoos/Publ/SmyHooStu03.pdf
- Sudholt. Parametrization and balancing local and global search.
  Handbook of Memetic Algorithms (2012).
  https://research.birmingham.ac.uk/en/publications/parametrization-and-balancing-global-and-local-search
- DEMaxSAT. https://github.com/Manuframil/DEMaxSatSolver
- Papadimitriou. On selecting a satisfying truth assignment. FOCS 1991
  (cited via Berenbrink et al.; not read).
