# Core-guided vs. Branch-and-Bound MaxSAT, and What It Implies for Benchmark Design

Working notes. Distinguishes throughout between what is established in the
literature, what follows directly from algorithm definitions, and what would
have to be argued from our own measurements.

---

## 1. Core-guided search: one UNSAT proof per unit of cost

This is the mechanism behind RC2's and EvalMaxSAT's behaviour, and it is a
direct consequence of the OLL algorithm, not an implementation artefact.

**Setup.** Every soft clause receives a relaxation/assumption literal. The
solver calls a SAT oracle on the hard clauses plus the assumption "all softs
are satisfied." Two outcomes:

- **SAT** — the current assignment violates nothing beyond what has already
  been accounted for. The current lower bound is the optimum; done.
- **UNSAT** — the SAT solver returns an *unsatisfiable core*: a subset of the
  assumption literals that cannot all hold simultaneously. This proves at
  least one soft clause in that subset must be violated, so the lower bound
  rises by (unweighted case) exactly 1. OLL then adds a totalizer over the
  core's literals, with new assumption literals on the totalizer outputs, so
  later cores can push the bound on the same subset further up incrementally.

**The consequence is arithmetic and exact for unweighted instances.** The
lower bound starts at 0 and climbs in increments of 1, so reaching the
optimum requires exactly `c*` UNSAT calls plus one final SAT call. Each UNSAT
call is a full refutation — proving *no* assignment satisfies that
combination — which is the expensive direction for a CDCL solver. They also
get monotonically more expensive, because each core adds totalizer variables
and clauses to the formula the next call must refute.

In the weighted case the increment is the minimum weight in the core rather
than 1, and stratification permits large jumps early, so the call count is
bounded by roughly `c*/w_min` rather than `c*`. The unweighted statement is
the clean one.

**Why this bites on dense random instances.** At `m/n` between 6 and 21 we
are far above the random 3-SAT satisfiability threshold (≈ 4.267), so a
constant fraction of clauses is unsatisfiable by force and `c*` grows
linearly in `m`. Separately, refuting random k-CNF near and above threshold
is exactly the regime with exponential resolution-size lower bounds, so each
individual refutation is also hard. The two effects multiply.

**No anytime behaviour.** Core-guided search maintains a lower bound
throughout and produces its first complete assignment only on the final SAT
call. A timeout is therefore not graceful degradation — the solver has
nothing to hand back. This is the precise reason RC2 cannot serve as an
anytime baseline, and it is a sharper statement than "it is slow."

**Citation status.** The `c*`-call-count statement is a two-line consequence
of the OLL pseudocode reproduced in every survey. It is not a published
finding and should not be presented as one; derive it in two sentences
instead of attaching a citation that does not say it.

---

## 2. Branch-and-bound: what it is and where it wins

A different algorithmic family. Rather than reducing MaxSAT to a sequence of
SAT decision calls, BnB searches the assignment tree directly, DPLL-style:

- Maintain **UB** = cost of the best complete assignment found so far.
- At each node compute **LB** = (clauses already falsified by the current
  partial assignment) + (an *underestimate* of how many more must eventually
  be falsified).
- Prune the subtree when LB ≥ UB.

Everything rides on that underestimate. The classical technique uses unit
propagation and failed-literal detection to find disjoint inconsistent
subsets of clauses — each guaranteeing at least one further violation — then
applies max-resolution to transform them so the accounting stays sound and
does not double-count. MaxSatz, akmaxsat and ahmaxsat are the established
implementations; MaxCDCL is a more recent hybrid grafting clause learning
onto BnB.

**Why BnB wins on dense random instances.** It pays no price proportional to
`c*`. A partial assignment that already falsifies 200 clauses simply has
LB ≥ 200 — one arithmetic step, not 200 refutations. The unit-propagation
lower bound is also cheap and unusually sharp precisely when the formula is
*dense*: many short clauses over few variables, which is what `m/n = 6–21`
random 3-SAT gives. These instances are also small in `n`, so the search
tree, exponential in principle, stays tractable.

**Why the field moved away.** On industrial instances — tens of thousands of
variables, heavy structure, small optimum — BnB collapses: the tree is
astronomically wide, per-node LB computation is expensive, and BnB does not
exploit structure the way CDCL learning does. Kügel states this directly for
akmaxsat: it is not competitive on industrial instances because those consist
of large formulas with a low clause-to-variable ratio, which makes the lower
bound calculation too expensive and the data structure unhelpful. The same
paper reports akmaxsat_ls as best solver in the unweighted random, weighted
(partial) random and weighted (partial) crafted categories.

**Rule of thumb.** Not a published result in this form — see §3.

| regime | family that wins |
|---|---|
| small `c*`, large structured instance | core-guided |
| large `c*`, small dense instance | branch-and-bound |

---

## 3. What is citable and what is not

**Citable — the dichotomy itself.** Li, Xu, Coll, Manyà, Habet and He open
the MaxCDCL paper by noting that BnB MaxSAT solvers have not succeeded on
challenging real-world optimization problems, that it is widely believed BnB
solvers are superior only on random and some specific crafted instances, and
that SAT-based solvers perform particularly well on real-world instances.
Caveat: they state this as the received view they set out to challenge. Fair
citation for "this is what the field holds," poor citation for "this is
settled."

**Citable — the density mechanism.** Kügel's akmaxsat paper, as above. A
solver author diagnosing his own failure mode in density terms is a stronger
primary source than a survey.

**Citable with care — the core-guided half.** Morgado, Heras, Liffiton,
Planes and Marques-Silva, *Iterative and core-guided MaxSAT solving: A survey
and assessment*, Constraints 18(4):478–534, 2013. Note what it does and does
not do: it presents itself as surveying SAT-based algorithms effective on
industrial problems, and its empirical study is explicitly conducted on
non-random benchmarks. It establishes the industrial half by construction,
never putting core-guided head to head with BnB on random instances.

**Umbrella reference.** Bacchus, Järvisalo and Martins, "Maximum
Satisfiability," in *Handbook of Satisfiability*, 2nd edition, IOS Press
2021, pp. 929–991.

**Not citable.** No paper states the `c*`-parameterized version of the
dichotomy, and no empirical study parameterizes solver-family crossover by
`c*` and `m/n` jointly. The raw material exists in the algorithm-selection
literature (portfolio datasets built from MSE results carry per-instance
features and per-solver runtimes), but that work targets selector training,
not an interpretable rule.

**Prior art on the phenomenon.** Larrosa, Heras and de Givry (2006) already
report solver crossover as a function of clause count on random 3-SAT:
PUEBLO best when the number of clauses is very small with relative efficiency
decreasing as clauses grow, MAXSOLVER showing the opposite behaviour. So
"density governs which family wins" is not novel and a referee will know it.
What remains novel is narrower: crossover among *current* solvers, with `c*`
and `m/n` separated rather than confounded.

---

## 4. If optima from MSE-2016 are ever needed

**Cheapest route first.** These instances were solved to optimality in the
complete track, so the optima are in the published results. Instances at
`maxsat.udl.cat/16/benchmarks/`; per-instance results tables were at
`maxsat.ia.udl.cat/results/`. Both domains have been flaky over the years —
the Wayback Machine may be required.

**If a solver must actually be run:**

- **MaxCDCL** — start here, for availability reasons more than algorithmic
  ones. Distributed through the MaxSAT Evaluation websites (MSE24 carries
  (W)MaxCDCL+Unlock; MSE23 carries MaxCDCL-S6-HS9 and WMaxCDCL-S6-HS12); no
  maintained standalone repository found. Third-party regression-tested
  (Paxian's MaxSATRegressionSuite runs it), takes modern WCNF, pairs with
  CaDiCaL. Caveat: its premise is fixing BnB's weakness on *real-world*
  instances, so it is the BnB solver good where BnB traditionally was not —
  which is not evidence it is best on dense random.
- **ahmaxsat / akmaxsat** — actually optimized for this regime; ahmaxsat
  ranked first in three of nine categories at MSE 2014 and is plausibly the
  solver that produced the MSE-2016 `ms` optima. Cost is practical:
  2010–2014 C++ needing compiler-flag surgery, and the **pre-2022 WCNF
  format** (`p wcnf` header with top weight) rather than the MSE-2022+ format
  (no header, `h` marks hard clauses). Bacchus's benchmark code base has
  new→old converters.

**Scope note.** Any such optima would be *reference values*, not part of the
measured stack. Using BnB as an oracle to establish ground truth is clean;
using it as a baseline is a different paper.

---

## 5. What can be claimed as our own finding

**Cannot claim:** the `c*`-call-count result (§1). Background, not
contribution.

**Can claim:** the empirical scaling on our generated families — our
measurement, our instances, our protocol, unpublished for these families
under this stack.

**The confound to be honest about.** Current evidence is `c* ≈ 1–3` →
seconds, and `m/n ≥ 6` at `n = 100` → past 60 s. Two regimes. That is
consistent with the `c*` story, but equally consistent with a story that
never mentions `c*`: refuting dense random 3-SAT well above threshold is
exponentially hard, so each call blows up and the call *count* is incidental.
Both accounts predict what was measured. Density was varied, which moved
`c*`, refutation hardness and formula structure simultaneously.

**The discriminating experiment**, if ever wanted: instances with similar
`c*` but different density — larger `n` at lower ratio against smaller `n` at
higher ratio, tuned so the optima land in the same range. If runtime tracks
`c*` across that pair, the mechanism is the call count; if it tracks `m/n`,
it is per-call refutation hardness and the `c*` framing is decoration.

**Recommended framing (supported by current data, no extra experiment):**
RC2's cost on these families scales with the optimum cost, expected because
core-guided search performs one UNSAT refutation per unit of cost, *with the
refutations themselves also growing harder as density rises*. Two mechanisms
compounding — which is what is actually happening. The benchmark-scope
conclusion then follows cleanly: families with large `c*` are out of reach
for a core-guided reference solver under this stack and cannot serve as TTT
baselines.

---

## 6. The (n, α) plane

Notation: use **α = m/n** (standard in the SAT phase-transition literature,
critical density α_c ≈ 4.267 for 3-SAT), or write `m/n` explicitly. Avoid ρ —
it reads as Pearson's correlation coefficient, which is bounded in [−1, 1],
and the paper will contain statistics.

**Why one dimension is not enough.** Sweeping α alone promotes the confound
to the x-axis: `c*`, per-call refutation hardness and satisfiability status
all move together. The plot is clean; the interpretation is ambiguous.

**Why two dimensions work.** For random k-SAT, `c* ≈ n · g(α)` — optimum cost
proportional to the number of variables, coefficient set by density. So the
`(n, α)` plane has **iso-`c*` contours crossing iso-α contours**: `c*` can be
held fixed while α varies, or vice versa. That is the separation required.

The scaling is established theory and need not be re-derived. Coppersmith,
Gamarnik, Hajiaghayi and Sorkin proved results on `E[max F]` for random
formulas with `m = ⌊cn⌋` clauses, showing MAX 2-SAT undergoes a phase
transition at the same critical value as the 2-SAT decision problem; Zhang
(2001) studied the relationship between the 3-SAT and MAX-3-SAT transitions.

**Positioning.** A paper framed as "a reference for MaxSAT knowledge" will be
read as overreach; surveys in this field come from authors with fifteen years
in it. An empirical characterization with tight scope can *become* reference
material without being framed as one. The modest framing is strictly better
for acceptance.

**Cheap version.** The `(n, α)` plane with iso-`c*` contours can be **one
figure** inside the existing paper — the figure justifying benchmark scope,
showing where RC2 is usable as a reference solver and where it is not. Most
of the conceptual value, using experiments needed anyway, at the cost of a
figure rather than a research programme. If it proves interesting enough to
stand alone, it is already built.

---

## 7. Why MSE-2016 cannot supply the instances

Liu and de Melo inventoried the set for their AAAI-2016 paper: all random
3-CNF instances from MSE 2016, 244 in total, with ratios ranging from **7.5
to 21.5**. Nothing near 4.267.

They also state *why*: low ratio formulae do not aid in distinguishing the
performance of different solvers in the Max-SAT Evaluation. The absence is a
deliberate curation choice, not an oversight — a citable sentence for the
scope paragraph, from an independent source.

**But read the reason carefully, because it cuts both ways.** The solvers
they have in mind are local-search ones. At low ratio `c*` is tiny, every SLS
solver finds the optimum almost immediately, and the field collapses. A
memetic algorithm (evolutionary + local search) sits in that same family.
Near-threshold large-`n` instances may therefore be degenerate for our
comparison in the *opposite* direction from MSE-2016: RC2 grinding through
hard refutations while the memetic solver finishes in seconds. That is a
regime where local search cannot lose, and a referee will say so.

**Two failure modes bracket the usable band:**

- α too low → the memetic solver finds the optimum trivially; the comparison
  measures nothing.
- α too high → RC2 does not finish; time-to-optimum is undefined.

The informative band lies between, and its location is an empirical question
about this solver at this `n` — found by a coarse sweep, not chosen from
theory.

**Selection criterion to state explicitly:** *both solvers must be doing
non-trivial work*. This excludes the regimes favourable to each side
symmetrically, which makes it principled rather than convenient. Stated up
front it becomes part of the method; left unstated it looks like picking the
instances where the numbers came out well.

Do not silently drop MSE-2016. Reposition it: out of reach for core-guided
reference solving under this stack, mechanism explained, solved in the
complete track only by branch-and-bound. An apparent gap converted into a
stated scope condition.

---

## 8. Building the corpus

Two passes. The first is throwaway.

### Pass 1 — probe

Locate the band, do not produce results. Coarse grid, few instances per cell,
short cap. For example `n ∈ {200, 400, 800, 1600}` × `α ∈ {4.5, 5, 6, 8, 12}`,
5 instances per cell, 60 s cap — 100 instances; RC2 once each (deterministic),
memetic a few times each.

Per cell record: `c*` where RC2 finishes; RC2 time-to-optimum; memetic
time-to-optimum or best-found at budget.

The band is a 2D *region*, not a line — for fixed α, `c*` grows with `n`, so
the target is a diagonal strip and the grid must be wide enough on both axes
to see it.

### Pass 2 — select, then build properly

Keep cells where both hold:

- RC2 reaches the optimum within budget on essentially every instance in the
  cell (otherwise TTT is undefined and the cell is unusable);
- the memetic solver does *not* hit the optimum in the first few percent of
  budget on most instances (otherwise the cell is uninformative).

Set thresholds from what the probe shows. Then regenerate those cells at full
size with fresh seeds, so probe data never contaminates reported results.

### Generation details that bite if skipped

- **Fix `m = round(α·n)` exactly** — per-instance α exact, not approximate,
  or the x-axis is fuzzy.
- **Declare the sampling model.** Standard uniform random 3-CNF: three
  distinct variables per clause sampled without replacement, each negated
  with probability ½. Whether duplicate clauses are allowed is a real choice
  — both variants appear in the literature — so pick one and say so.
- **Derive seeds deterministically from `(n, α, index)`.** Exactly
  reproducible; cells extendable later without regenerating what was run.
- **Instances per cell and runs per instance are different axes.** TTT varies
  across instances and across seeds of a stochastic solver. RC2 is
  deterministic — one run each.
- **Format.** Unweighted MaxSAT = every clause soft with weight 1, no hard
  clauses. Verify which WCNF dialect the RC2 build expects (pre-2022: `p
  wcnf` header with top weight; MSE-2022+: no header, `h` marks hard
  clauses). Getting this subtly wrong yields plausible but wrong optima —
  the worst failure mode, because nothing crashes.

### Invariants worth checking

- `c*` should come out close to `n · g(α)`, monotone increasing in both `n`
  and α. A cell breaking that indicates a generator bug before a solver bug.
- On a small subset, confirm the memetic solver's best-found never beats
  RC2's optimum. If it does, that is a parsing or objective-counting
  mismatch, not a discovery.

---

## References

- Bacchus, Järvisalo, Martins. "Maximum Satisfiability." *Handbook of
  Satisfiability*, 2nd ed., IOS Press, 2021, pp. 929–991.
- Coppersmith, Gamarnik, Hajiaghayi, Sorkin. "Random MAX SAT, random MAX CUT,
  and their phase transitions."
- Kügel. akmaxsat (solver description / MaxSAT Evaluation submission).
- Larrosa, Heras, de Givry. "A Logical Approach to Efficient Max-SAT
  Solving." arXiv:cs/0611025.
- Li, Manyà, et al. "New Inference Rules for Max-SAT." arXiv:1111.0040
  (MaxSatz).
- Li, Xu, Coll, Manyà, Habet, He. "Combining Clause Learning and Branch and
  Bound for MaxSAT." CP 2021 (MaxCDCL).
- Liu, de Melo. "Should Algorithms for Random SAT and Max-SAT Be Different?"
  AAAI 2016. arXiv:1610.00442.
- Morgado, Heras, Liffiton, Planes, Marques-Silva. "Iterative and core-guided
  MaxSAT solving: A survey and assessment." *Constraints* 18(4):478–534,
  2013.
- Zhang. "Phase transitions and backbones of 3-SAT and maximum 3-SAT." 2001.
- MaxSAT Evaluation 2016 benchmarks: `maxsat.udl.cat/16/benchmarks/`
- MaxSAT Evaluation 2016 results: `maxsat.ia.udl.cat/results/`

Bibliographic details should be verified before use — several were recovered
from secondary sources.
