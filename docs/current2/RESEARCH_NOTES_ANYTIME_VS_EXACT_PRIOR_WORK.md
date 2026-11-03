# Research note: prior work on the orthogonality of anytime and exact solvers

**Created:** 2026-10-24. Note N-2026-10-24-a (`docs/current/RESEARCH_NOTES.md`).
**Status:** literature check by web search plus reading the full text of
the papers marked [read]. Not a full survey: the MaxSAT Evaluation reports
were not read.
**Updated 2026-11-03:** venues and DOIs of §2.1–2.2 verified (Crossref and
the DOI resolver); §2.2 expanded from a second full reading; BibTeX in §5.

> "yes update the note, in Smyth, Hoos & Stützle (2003) what they studied?"
> (user, 2026-11-03)

> "check if something like I want to do check orthogonality of anytime to
> exact sover - anytime : custom memetic, local search, exact RC2 or
> EvalMAxSAt - if something was done, mainly the pass to anytime of oracle
> time" (user, 2026-10-24)

## 1. Summary

- **[verified] Our design.** The anytime solver is given the exact solver's
  optimum and stops there (`STOP_AT_ORACLE=1`). y = memetic ERT_s to that
  optimum; x = RC2 or EvalMaxSAT proof time; ρ = Spearman, one point per
  instance (`docs/current/CORPUS_V1_PROTOCOL_DRAFT.md`,
  `ORACLE900_RUN.md`, `NOTES_2026-10-21_AGENDA_AND_STATS.md` §8.3).
- **Closest precedent, in SAT:** Hoos & Stützle, "Systematic vs. Local
  Search for SAT" (§2.1). On the same 1000 random 3-SAT instances, local
  search cost and complete-solver cost correlate with **0.26**.
- **Passing the optimum to a MaxSAT local search** as its target was done
  by Smyth, Hoos & Stützle for IRoTS (§2.2). They then correlated local
  search with local search only, never with exact-solver time.
- **Not found:**
  - a MaxSAT study that correlates exact proof time with an anytime
    solver's time to the optimum;
  - a design that gives the anytime solver the exact solver's own runtime
    as its budget.
- **[inference] Position:** our ρ is the MaxSAT analogue of the
  Hoos–Stützle correlation, with the target set as in IRoTS.

## 2. Papers

### 2.1 Hoos & Stützle, "Systematic vs. Local Search for SAT" [read]

Read from UBC Technical Report TR-99-06. The published version is
KI-99: Advances in Artificial Intelligence, LNAI 1701, pp. 289–293,
Springer 1999, doi 10.1007/3-540-48238-5_25 [verified 2026-11-03,
Crossref].

- **Instances:** test set uf100-430, 1000 satisfiable Random-3-SAT
  instances (100 variables, 430 clauses).
- **Local search:** R-Novelty+ (WalkSAT family).
  - At least 100 runs per instance with a maxSteps high enough for nearly
    100 % success.
  - Cost = expected flips per solution, from the run-length distribution.
- **Complete solver:** Satz.
  - Cost = search steps, from one run (Satz is deterministic).
  - The paper says this measure "shows a strong correlation with CPU-time".
- **Result:**

  > "As can be easily seen from the plot, there is no strong correlation
  > between the search cost for both algorithms. A correlation analysis
  > confirms this result (correlation coefficient = 0.26); thus, the search
  > cost for complete and local search seem to be only very slightly
  > correlated."

  > "when comparing absolute CPU-time, for about 95% of the test-set,
  > R-Novelty+ is up to one order of magnitude faster than SATZ."

  Footnote:

  > "There might be a tendency that the instances which are extremely hard
  > for R-Novelty+ are not particularly hard for SATZ; however, at this
  > point, this observation cannot be considered to be statistically [...]"

- **Not stated:** the type of correlation coefficient (Pearson or rank), and
  whether it was taken on log costs. The scatter plot has log axes.
- **Why no oracle is needed:** in SAT, finding a satisfying assignment ends
  both solvers. The authors therefore restrict the comparison:

  > "comparisons between SLS algorithms and systematic search algorithms
  > have to be restricted to satisfiable instances."

- **The rest of the paper:**
  - local search is clearly better on Random-3-SAT;
  - structured instances are "often, but not always" solved faster by
    systematic search;
  - they conclude that hybrids or portfolios may work best.

### 2.2 Smyth, Hoos & Stützle, "Iterated Robust Tabu Search for MAX-SAT" [read]

Published in Advances in Artificial Intelligence (Canadian AI 2003),
LNCS 2671, pp. 129–144, Springer 2003, doi 10.1007/3-540-44886-1_12
[title, authors, pages, DOI verified 2026-11-03 via the DOI resolver;
LNCS 2671 from the search result].

- **What the paper is about:** an algorithm paper. It proposes IRoTS, an
  iterated local search for weighted and unweighted MAX-SAT. Robust Tabu
  Search (Taillard's RoTS, adapted to MAX-SAT) is used both as the local
  search and as the perturbation. The question is whether IRoTS beats the
  state of the art in local search, not how local search relates to exact
  solvers.
- **Competitors:** local searches only: GLS and GLS2 (Mills & Tsang), ILS-YI
  with 1- and 2-flip neighbourhoods (Yagiura & Ibaraki), plain RoTS. No
  exact solver is a competitor.
- **Instances:**
  - wjnh (44 random weighted instances, some satisfiable) and bor (random
    weighted and unweighted Max-2/3-SAT, n 50–150);
  - 12 new sets of 100 Random 3-SAT instances, n 50–200, in the
    over-constrained region: unweighted with m/n 5–10 (rnd100-500u …
    rnd100-1000u), and weighted with truncated-normal weights, mean 5n,
    σ = n or 5n (rnd50-w50 … rnd200-w1000);
  - structured: YI-GCP (graph colouring), YI-SCP (set cover), LGCMP (level
    graph crossing minimisation).
- **Measure:** 100 runs per algorithm and instance until the target cost;
  search cost = median of the run-time distribution (steps and CPU s).
  1 GHz Pentium III.
- **Results:**
  - IRoTS beats GLS2 on the random sets, by up to ~18× in median CPU time
    on the most over-constrained unweighted set; the advantage grows with
    m/n and with weight variance;
  - on par with GLS on wjnh;
  - on structured sets GLS wins (graph colouring, set cover), IRoTS wins on
    crossing minimisation;
  - IRoTS run-time distributions are close to exponential; GLS/GLS2 show
    stagnation (fat right tails).
- **Structured instances: no oracle.** The target there is the 90th
  percentile of the quality reached by the worst algorithm in 10 s, so the
  optimum is not passed on these sets.

- **How the oracle is passed:**

  > "we generally measured RTDs for reaching provably optimal or best-known
  > solution qualities. Where possible, we used Borcher and Furman's
  > complete solvers maxsat and wmaxsat to determine the optimal solution
  > quality for each instance."

  - 100 runs per algorithm and instance, each run until that cost is
    reached.
  - Search cost = the median of the run-time distribution.
- **Instances too large for the exact solvers:** the optimum is estimated
  by an "iterative deepening" IRoTS protocol (10 runs). They checked it
  against the complete solver where that was possible, and "in all cases
  IRoTS had found the true optimal solution". Some larger instances needed
  "multiple CPU days" of the complete solver.
- **Correlation, local search against local search only** (IRoTS vs GLS2,
  rnd100-w100):

  > "the CPU times are positively correlated, but that there is a
  > significant amount of noise in the correlation especially for the
  > harder instances"

  The noise grows with the variance of the clause weights.
- **Not done:** no correlation with the exact solvers' runtimes.

### 2.3 Hoos & Stützle, "Local Search Algorithms for SAT: An Empirical Evaluation" (JAR 2000) [read]

This is the contrast to §2.1: different local searches find the same
instances hard.

> "the performance of the different SLS algorithms studied here is
> typically tightly correlated within test-sets, i.e., the same instances
> tend to be relatively hard for all algorithms."

### 2.4 Nudelman, Leyton-Brown, Hoos, Devkar & Shoham, "Understanding Random SAT: Beyond the Clauses-to-Variables Ratio" (CP 2004) [read, partly]

- **Evidence against full independence, indirect:** a feature from short
  SAPS probe runs helps predict the runtime of DPLL solvers (kcnfs,
  oksolver, satz):

  > "It may appear somewhat surprising that such a local search probing
  > feature can convey meaningful information about the run-time behavior
  > of a DPLL algorithm."

  The feature is the variation of the number of unsatisfied clauses in
  local minima.
- **Not done:** no direct correlation of local-search runtime with
  complete-solver runtime.

### 2.5 Fravel, Koutecký & Tsitsei, "Hard Instances on Demand" (arXiv 2610.22637, 2026-10-15) [summary via fetch]

- **Domains:** SAT, TSP, Hamiltonian cycle and flow shop. All the attacked
  solvers are exact.
- **Main point:** hardness is solver-specific, and it often transfers
  poorly between exact solvers.
- **Side remark (TSP):** 2-opt gets near-optimal tours easily, and proving
  optimality is the hard part.
- **Relevance:** tangential.

## 3. What this means for our ρ

- **[inference] Find against find+prove.** In Hoos–Stützle both costs
  measure the same event, finding a solution. In MaxSAT they differ:
  - the exact time includes the proof of optimality;
  - our anytime time (ERT_s to the oracle) covers only finding the
    optimum.

  State this in the write-up. It is one reason a low ρ is plausible.
- **[verified] A possible second x:** the time at which EvalMaxSAT first
  printed the optimum cost (its `o` lines).
  - Our driver `src/cli/oracle_evalmaxsat.py` reads stdout only after the
    process ends (`subprocess.run`, `capture_output`), so these times are
    not recorded now.
  - Recording them needs a streaming reader that timestamps each line.
  - RC2 is core-guided and, as we run it, reports its solution only at the
    end, so it gives no such time.
  - Not proposed as a run; noted only.
- **[inference] Precedent for our measurement choices:**
  - many runs per instance and an expected cost from the run-length
    distribution, which is our ERT;
  - the target taken from a complete solver, and best-known only where
    proofs fail (IRoTS).
- **[inference] Comparing numbers:** the 0.26 is
  - for SAT, random 3-SAT and n = 100;
  - with cost in operation counts, not seconds;
  - with the coefficient type unstated.

  Cite it as precedent for the question and the method, not as a value to
  compare our ρ with.
- **Citations for the write-up:** §2.1 and §2.2 as primary related work;
  §2.3 as the within-paradigm contrast.

## 4. Sources

- [Hoos & Stützle, Systematic vs. Local Search for SAT (TR-99-06)](https://www.cs.ubc.ca/sites/default/files/tr/1999/TR-99-06_0.pdf)
- [Smyth, Hoos & Stützle, Iterated Robust Tabu Search for MAX-SAT](https://www.cs.ubc.ca/~hoos/Publ/SmyHooStu03.pdf)
- [Hoos & Stützle, Local Search Algorithms for SAT: An Empirical Evaluation (JAR 2000)](https://www.cs.ubc.ca/~hoos/Publ/jar00.pdf)
- [Nudelman et al., Understanding Random SAT (CP 2004)](https://www.cs.ubc.ca/~kevinlb/papers/RandomSAT.pdf)
- [Fravel, Koutecký & Tsitsei, Hard Instances on Demand (arXiv 2610.22637)](https://arxiv.org/html/2610.22637)
- Background, not used for claims:
  - [Gomes et al., Handbook of KR, satisfiability chapter](https://www.cs.cornell.edu/gomes/pdf/2008_gomes_knowledge_satisfiability.pdf)
  - [Kroc et al., hybrid MaxSAT (IJCAI 2009)](https://www.cs.cornell.edu/~kroc/pub/hybridMaxsatIJCAI09.pdf)
  - [Alòs et al., Exploiting Configurations of MaxSAT Solvers (CP 2023)](https://arxiv.org/html/2306.07635)

## 5. BibTeX (added 2026-11-03)

Checked against Crossref and the DOI resolver (title, authors, pages, DOI).
The series volume numbers (LNAI 1701, LNCS 2671) were not in those records.

```bibtex
@inproceedings{hoos1999systematic,
  author    = {Hoos, Holger H. and St{\"u}tzle, Thomas},
  title     = {Systematic vs. Local Search for {SAT}},
  booktitle = {KI-99: Advances in Artificial Intelligence},
  series    = {Lecture Notes in Artificial Intelligence},
  volume    = {1701},
  pages     = {289--293},
  publisher = {Springer},
  year      = {1999},
  doi       = {10.1007/3-540-48238-5_25}
}

@inproceedings{smyth2003irots,
  author    = {Smyth, Kevin and Hoos, Holger H. and St{\"u}tzle, Thomas},
  title     = {Iterated Robust Tabu Search for {MAX-SAT}},
  booktitle = {Advances in Artificial Intelligence: 16th Conference of the
               Canadian Society for Computational Studies of Intelligence (AI 2003)},
  series    = {Lecture Notes in Computer Science},
  volume    = {2671},
  pages     = {129--144},
  publisher = {Springer},
  year      = {2003},
  doi       = {10.1007/3-540-44886-1_12}
}
```
