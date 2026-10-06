# Corpus families: MaxCut in, Max-Clique and set covering out

> **Current state and active plans (2026-10-06):** see [`current/NEXT_SESSION_CONTEXT.md`](current/NEXT_SESSION_CONTEXT.md). This document is kept as a record; where it conflicts with `docs/current/`, the current documents win.

**Date:** 2026-10-06. A summary of what the existing plans say about these
three families, plus one gap found while summarising (the torus stratum,
last section). Sources:
[`CORPUS_GENERATOR_PLAN.md`](CORPUS_GENERATOR_PLAN.md) §0, §3.1, §3.2, §4
Step 1a, §5;
[`../more_data/CORPUS_BROADENING_HANDOFF.md`](../more_data/CORPUS_BROADENING_HANDOFF.md)
§2, §3, §4 Step 4, §6a;
[`CORPUS_CALIBRATION_GOALS.md`](CORPUS_CALIBRATION_GOALS.md) §2.2;
[`archive/CORPUS_MSE2016_ASSESSMENT.md`](archive/CORPUS_MSE2016_ASSESSMENT.md).

The plan treats MaxCut as a core family. Max-Clique and set covering are
deliberately left out of the generated corpus.

---

## 1. Max-Clique (handoff family F8)

**The plan as written** (handoff §3b):

- One variable x_v per vertex.
- A soft unit clause `(x_v)` of weight 1 for each vertex: "put v in the
  clique".
- A conflict clause `(¬x_u ∨ ¬x_v)` for each pair of vertices with no edge
  between them. This one must never be violated.
- The source would be the DIMACS benchmark graphs (brock, C-series, keller,
  hamming, p_hat). Their difficulty range is wide and the encoding is a few
  lines.
- The cost is c\* = n − ω, the number of vertices left out of the largest
  clique.
- The handoff (§4 Step 4) also suggests generated graphs with a planted
  clique of known size as test fixtures.

> **Reassessed 2026-10-06** ([`current/CORPUS_FREEZE_PREP.md`](current/CORPUS_FREEZE_PREP.md) §8).
> - Reason 1 below is **not supported for this encoding.** Conflict clauses
>   are anti-monotone: setting a variable false never breaks one. In a
>   workstation probe on G(60, 0.5), the unchanged memetic solver reached and
>   kept feasibility, and crossover of feasible parents stayed feasible 20/20.
>   The "no gradient" wording is also inaccurate: the fitness ranks infeasible
>   assignments by their number of hard violations.
> - Reason 2 is moot if the conflict clauses stay hard.
> - Reason 3 is moot for generated graphs.
> - Reason 4 was an inference, and is contradicted at small n: RC2 proved
>   c\* = 53 in 0.04 s.
> - **Max-Independent-Set / Max-Clique on generated graphs is therefore
>   reopened as an option (stratum H)**, gated by a small diagnostic: RC2
>   window reachability, and 900 s runs that must end feasible. Its polish
>   calls idle to their time limit, so effort is time-bound and it is never
>   pooled with all-soft strata.
> - **Mixed-sign hard clauses** (set covering, partial random k-SAT) stay
>   excluded, for a verified reason: crossover and polish do not preserve
>   feasibility.
>
> The original text follows unchanged.

**Why it is excluded** (generator plan §3.1, decision E3):

1. **It needs hard clauses, and the memetic EA cannot handle them.**
   - The conflict clauses are hard constraints.
   - The EA's fitness function collapses every infeasible assignment to
     about −1e9 − 1e6·(hard violations), so the search gets no gradient
     toward feasibility.
   - On the MSE instance `00000293`, five 1800 s runs never reached a
     feasible assignment, while Glucose found one in 0.04 s.
   - The fix is a different algorithm: a genome made of the soft variables
     only, plus a SAT-solver decoder (handoff §6a). It is not a config
     change.
2. **The workaround adds a second change.** Giving the conflict clauses a
   weight larger than the sum of all soft weights makes the instance
   formally all-soft. But it also makes the instance weighted, so clause
   structure and weightedness change together. The handoff (§2) warns that
   adding something like weighted Max-Clique moves several axes at once and
   "explains nothing".
3. **It needs a download** (the DIMACS graphs), which the sandbox cannot
   fetch.
4. **The cost is out of RC2's reach.**
   - c\* = n − ω is typically in the hundreds.
   - RC2 needs about one core extraction per unit of cost, and the pilot
     puts its reach at about 1–10 for random 3-SAT and tens for 2-clause
     families.
   - This item is an inference from the plan's c\* argument (§0), not a
     reason the plan states for Max-Clique.
5. **Part of it is already covered differently.** The MSE-2016 family
   `maxcut/dimacs-mod` is *MaxCut* on the DIMACS clique graphs. It is
   pure-soft, already on disk, certified with c\* = 2–49, and kept in the
   structured stratum S1.

## 2. Set covering (F9)

**The plan as written:**

- One variable per set.
- A soft unit `(¬x_S)` weighted by the set's cost.
- A hard coverage clause `(∨_{S∋e} x_S)` for each element e.
- Source: OR-Library.
- Its appeal is the clause-length spread: unit clauses next to coverage
  clauses of length 10–75. It also comes naturally weighted.

**Why it is excluded as a generator:** the same three reasons as
Max-Clique. Hard clauses hit the EA's feasibility problem, the big-weight
workaround makes the instance weighted, and it needs a download.

**It was not dropped entirely:**

- The MSE-2016 `set-covering/scpcyc` and `scpclr` files are already on disk.
- Decision E4 kept them in the S1 screening, to supply clause lengths 1 and
  long "if the screen certifies any".
- So far it has certified none: they timed out under both exact solvers at
  caps up to 1800 s (`CORPUS_CALIBRATION_GOALS.md` §2.2). In practice set
  covering is out unless that changes.

## 3. MaxCut (G3 Erdős–Rényi random graphs, G4 torus lattices)

**The plan** (generator plan §4 Step 1a, about 120 lines,
`instancegen/maxcut.py`, not written yet):

- Parameters: `topology` ∈ {er, torus, complete, bipartite}, `n_vertices`,
  `degree` (ER only), `seed`.
- Encoding: for each edge (u, v), two soft clauses of weight 1,
  `(x_u ∨ x_v)` and `(¬x_u ∨ ¬x_v)`.
- `complete` and `bipartite` exist only as known-optimum tests:
  - bipartite graphs must give cost 0;
  - the complete graph K_n must give cost |E| − ⌊n²/4⌋;
  - the verification harness asserts both, to catch a "cut edges vs uncut
    edges" inversion.
- The corpus design (§3.2) uses MaxCut for two strata:
  - D: ER graphs, 60–150 vertices, average degree 4–8;
  - E: torus lattices from 8×8 to 12×12;
  - both are unweighted. Weighted twins come later through `reweight.py`.
- Why MaxCut is in: it is a 2-clause family with graph origin, and it is
  where the plan expects a spread of c\* that RC2 can still certify. The
  pilot measured MSE `dimacs-mod`/`spinglass` at c\* 2–49 (T1). The MSE
  `bipartite/maxcut-140-630` files were all too hard for RC2 at 300 s
  (10/10 T3).

### Can the best assignment leave clauses unsatisfied?

Yes. It almost always does, and that is the point of the family.

- **Per edge:**
  - The two clauses can never both be false: `(x_u ∨ x_v)` false needs both
    variables false, and then `(¬x_u ∨ ¬x_v)` is true.
  - A cut edge satisfies both clauses.
  - An uncut edge leaves exactly one clause unsatisfied.
  - So the cost equals the number of uncut edges, and c\* = |E| − maxcut.
- **The optimum is 0 only if the graph is bipartite.** Every odd cycle
  forces at least one uncut edge.
- **ER graphs:** the optimum is well above 0. A rough asymptotic estimate
  for n = 100 and average degree 6 (about 300 edges) is roughly 50–60
  uncut edges. This is an estimate, not a measured number; the plan says
  "expect tens–100" and leaves it to calibration.

### Gap in the plan: the torus stratum (E)

- **Even side length:** the torus is bipartite, so c\* = 0. That makes it a
  fixture, not a corpus instance.
- **Odd side length L:** each of the L row cycles and L column cycles is
  odd, and they share no edges, so c\* ≥ 2L. That is only about 18–22 for
  the planned sizes, with little spread.
- So stratum E as written (8×8 … 12×12, unweighted) would give either 0 or
  a narrow band.
- The standard way to make lattices interesting is spin-glass couplings: a
  random sign per edge, where a negative edge uses the "same side" clauses
  `(x_u ∨ ¬x_v)` and `(¬x_u ∨ x_v)`. That keeps instances unweighted and
  frustrated, and resembles the MSE `spinglass` instances that already
  certify.

**Open item:** fix stratum E in `CORPUS_GENERATOR_PLAN.md` §3.2 (and the
`MaxCutParams` of Step 1a) before `maxcut.py` is written.

**Resolved 2026-10-06** (`current/CORPUS_FREEZE_PREP.md` §6.3):
- Stratum E is a ±J spin glass on the L × L torus: an independent fair sign
  per edge, all weights 1.
- A positive edge uses `(x_u ∨ x_v)`, `(¬x_u ∨ ¬x_v)`. A negative edge uses
  `(x_u ∨ ¬x_v)`, `(¬x_u ∨ x_v)`.
- Frustration comes from the signs, so even sides are fine.
- `MaxCutParams` gains `couplings ∈ {cut, pm1}`. The all-`cut` even torus
  survives only as the c\* = 0 fixture.
- Whether RC2 reaches the 30–900 s window on it is an empirical question for
  its calibration gate.
