# Research note: virtual-best-solver precedents, and what is novel in our ρ study

**Created:** 2026-11-03. Note N-2026-11-03-a (`docs/current/RESEARCH_NOTES.md`).
**Status:** a targeted web search (8 queries, 2026-11-03), plus full reading of
the papers marked [read], from their PDFs. Papers marked [snippet] were seen
only through search results or a page summary. Not a full survey. This note
extends `RESEARCH_NOTES_ANYTIME_VS_EXACT_PRIOR_WORK.md` (N-2026-10-24-a), whose
§2.1–2.2 (Hoos & Stützle 1999; Smyth, Hoos & Stützle 2003) are not repeated
here.

> "yes do the targeted search for VBS precedents, also write the findings tou
> stated above in .md" (user, 2026-11-03)

> "in Smyth, Hoos & Stützle (2003) what they studied? is our research novel in
> some way?" (user, 2026-11-03)

## 1. Summary

- **Not found:** a MaxSAT study that, on the same instances,
  - correlates an exact solver's proof time with an anytime solver's time to
    that same optimum, or
  - counts the instances that only the exact solver, or only the anytime
    solver, solves (a virtual-best-solver split between the two classes).
- **Closest precedents, all in SAT:**
  - Hoos & Stützle 1999: local search cost against complete-solver cost,
    correlation 0.26 (prior-work note §2.1).
  - Xu, Hutter, Hoos & Leyton-Brown, SAT 2012 (§2.1 here): a Spearman
    runtime-correlation matrix for the SAT Competition 2011 Random category.
    The local search solvers and the complete solver March form two separate
    clusters.
- **MaxSAT, related but different:**
  - a hybrid motivated by complementarity (Kroc et al. 2009);
  - portfolios made only of exact solvers (ISAC, Ansótegui et al. 2014/2016);
  - a VBS used only as a source of bounds (Alòs et al. 2023);
  - coarse statements that incomplete solvers are faster on random and crafted
    instances (Traversa et al. 2018; SATLike 2018).
- **Methodological warning, directly relevant:** Cameron, Hoos & Leyton-Brown
  (IJCAI 2016, §2.5) show that taking the best of single runs of randomized
  solvers biases VBS performance upwards. Our "memetic reached (≥ 1 of 3
  seeds)" count is a best-of-runs measure (§3.3).
- **[inference] Position:** the novelty is the measurement in MaxSAT, at
  Evaluation scale: proof time against time to the optimum, plus the
  exact-against-anytime solved split. That solvers complement each other is
  not new (it is the premise of every portfolio), and the paper should not
  claim it as a discovery.

## 2. Papers

### 2.1 Xu, Hutter, Hoos & Leyton-Brown, "Evaluating Component Solver Contributions to Portfolio-Based Algorithm Selectors" (SAT 2012) [read]

LNCS 7317 (SAT 2012), pp. 228–241, doi 10.1007/978-3-642-31612-8_18 [verified,
Crossref, without the volume number]. Data: SAT Competition 2011.

- **The closest SAT analogue of our ρ.** In the Random category:

  > "Figure 1(b) shows a correlation matrix of component solver performance:
  > the entry for solver pair (A,B ) is computed as the Spearman rank
  > correlation coefficient between A's and B's runtime [...] Two clusters are
  > apparent: six local search solvers ( EagleUP, Sparrow, Gnovelty+2,
  > Sattime11, Adaptg2wsat11, and TNM), and two versions of the complete
  > solver March"

  MPhaseSAT_M "was strongly correlated with local search solvers on the
  satisfiable instance subset and very strongly correlated with the March
  variants on the unsatisfiable subset."
- **Complementarity in SAT, by competition results:**

  > "all medals went to portfolio solvers that combined local search and
  > complete solvers."

- **Measure they argue for:** the marginal contribution of a solver to the
  portfolio, not its standalone performance.
- **How it differs from ours:**
  - SAT, not MaxSAT: one event (a model found) ends both solvers; no proof
    step for the local search, and it cannot solve unsatisfiable instances;
  - the correlations are shown as a figure, so the values are not in the text;
  - it is about portfolio design, not about hardness across paradigms.

### 2.2 Kroc, Sabharwal, Gomes & Selman, "Integrating Systematic and Local Search Paradigms: A New Strategy for MaxSAT" (IJCAI 2009) [read]

IJCAI-09, pp. 544–551 (page numbers from the PDF).

- **Premise:**

  > "Systematic search and local search paradigms for combinatorial problems
  > are generally believed to have complementary strengths."

- **Method:** MiniSat and WalkSAT run at the same time on unsatisfiable SAT
  instances, treated as MaxSAT. DPLL guides the local search's flips through
  shared memory.
- **Per-instance contrasts, not a correlation:**
  - "cmu-bmc-barrel6.cnf, is solved by the state-of-the-art exact MaxSAT
    solvers such as maxsatz [...] and msuf [...] in 20-30 minutes while within
    only a couple of seconds by an exact SAT solver like MiniSat";
  - only 10 of the 52 SAT-Race 2008 instances "were small enough to be solved
    by these solvers"; MiniWalk solves 37 of 52 to optimality, the other
    solvers 7–12;
  - the hybrid helps only "if [...] we have a sufficiently hard instance at
    hand"; when DPLL proves unsatisfiability within seconds, it falls back to
    plain local search.
- **How it differs from ours:** an algorithm paper on 52 instances. The
  complementarity is a motivation; it is not measured.

### 2.3 Ansótegui, Malitsky & Sellmann, "MaxSAT by Improved Instance-Specific Algorithm Configuration" (AAAI 2014; journal version AIJ 2016) [read]

AAAI 2014: doi 10.1609/aaai.v28i1.9128. AIJ 235:26–39 (2016), with Gabàs as an
added author: doi 10.1016/j.artint.2015.12.006 [both verified, Crossref].

- **Complementarity within exact MaxSAT solvers:**

  > "SAT-based solvers clearly dominate on industrial and some crafted
  > instances, while branch-and-bound solvers dominate on random and some
  > families of crafted instances."

- **Portfolio:** MaxSAT Evaluation solvers (QMaxSat, pwbo, WPM1, akmaxsat,
  akmaxsat_ls, …), all complete. akmaxsat_ls is branch and bound with a local
  search for the first upper bound. The 11 local search solvers in the paper
  belong to its SAT experiments. VBS rows are reported.
- **How it differs from ours:** no stand-alone anytime MaxSAT solver in the
  portfolio, so no exact-against-anytime split.

### 2.4 Alòs, Ansótegui, Salvia & Torres, "Exploiting Configurations of MaxSAT Solvers" (arXiv 2306.07635, 2023) [snippet, page summary]

- MSE 2022 incomplete weighted track, 60 s, 197 instances, 10 incomplete
  solvers (Loandra, NuWLS-c, TT-Open-WBO-Inc, …).
- "VBS_b uses the upper bounds found by the Virtual Best Solver of the solvers
  we executed": the VBS is a source of reference bounds.
- A virtual sequential portfolio needs "the evolution of the best bound over
  time".
- No runtime correlation, no time to the optimum, no exact-against-anytime
  counts.

### 2.5 Cameron, Hoos & Leyton-Brown, "Bias in Algorithm Portfolio Performance Evaluation" (IJCAI 2016) [snippet, abstract summary]

IJCAI-16, pp. 712–718.

- **Claim (from the abstract, paraphrased):**
  - the usual VBS evaluation runs each solver once per instance and takes the
    best result;
  - with a randomized solver in a portfolio of two or more, this overstates
    the VBS;
  - the bias was significant on many random and some combinatorial SAT
    Competition instances;
  - it shrinks when each solver's performance is averaged over many runs.
- **Their remedy:** pick per instance the solver with the best *expected*
  performance, and bootstrap a confidence interval.
- **Relevance:** directly about our complementarity counts (§3.3).

### 2.6 Coarse statements about complete against incomplete MaxSAT solvers [snippets and one passage read]

- **Traversa, Cicotti, Sheldon & Di Ventra, "Evidence of Exponential Speed-Up
  in the Solution of Hard Optimization Problems"** (Complexity 2018, doi
  10.1155/2018/7982851 [verified, Crossref]; read from arXiv 1710.09278):

  > "in recent Max-SAT competitions [5], incomplete solvers outpace complete
  > solvers by two orders of magnitude on random and crafted benchmarks, and
  > perform similarly on industrial problems."

  This is a second-hand summary of Evaluation results, not an analysis.
- **Lei & Cai, SATLike (IJCAI 2018)** [snippet]: it "performs better than the
  complete solvers on the MSE2017 benchmarks". This compares solution quality
  at a time limit, not time to the optimum against proof time.
- **Ye, Luo & Cai, anytime performance analysis of MaxSAT local search**
  (arXiv 2403.06568) [snippet]: local search solvers only.

### 2.7 The MaxSAT Evaluations themselves [snippet]

- Incomplete tracks are scored against best-known costs, at fixed time limits
  (60 s / 300 s; 2026 also 1707 s), not by time to the optimum.
- Per-instance results are published for both tracks, and the 2022 incomplete
  track drew instances from hard complete-track instances. So the join we did
  is possible from public data, but no published analysis of it was found.
- **Not read:** the Evaluation reports (e.g. Bacchus, Järvisalo & Martins on
  MSE 2018, JSAT) and the 2023–2026 slides. These are the most likely place for
  a close precedent, and should be checked before the paper says "first".

## 3. What is novel in our study, and what is not

Numbers from `MSE26_RHO_RESULTS_3.md` (readout 3, `fail` treatment unless
stated).

### 3.1 What appears new [inference, on §2 and the prior-work note]

1. **The measurement.** Per instance, the exact solver's proof time against
   the anytime solver's time to the same optimum, with the optimum passed as
   the target.
   - IRoTS (Smyth et al. 2003) passed the optimum but never analysed the exact
     solver's runtime.
   - Hoos & Stützle 1999 and Xu et al. 2012 compared local and complete search
     in SAT, where no proof step separates the two.
2. **Setting and scale.**
   - 922 MSE 2026 instances, both tracks, many with hard clauses.
   - A modern exact solver, EvalMaxSAT, taken from its published 2026 runs.
   - A pre-registered analysis that handles censoring: ERT, with timeouts as
     tied ranks, and seven sensitivity analyses.
3. **The findings.**
   - Overall the two are clearly associated: ρ = +0.637 [+0.588, +0.680]
     (`exclude` +0.632); +0.569 after partialling out instance size.
   - In the hard regime the association is weak: the window (30, 3600] s with
     both solved gives +0.223.
   - Complementarity:
     - the memetic reaches the optimum on 44 instances EvalMaxSAT does not
       prove, 44 / 130 = 33.8 % of its timeouts;
     - EvalMaxSAT proves 262 that the memetic does not reach;
     - together they cover 90.7 %, against 85.9 % for EvalMaxSAT alone.
   - The memetic's reach falls steadily with EvalMaxSAT time: 97.1 % at
     ≤ 1 s, down to 35.7 % at (300, 3600] s.

### 3.2 What is not new, and should not be claimed

- **That solvers complement each other.** It is the premise of portfolios and
  algorithm selection (SATzilla; ISAC for MaxSAT, §2.3; Xu et al. 2012, §2.1)
  and of hybrids (Kroc et al. 2009, §2.2). Our contribution is to quantify it
  for exact against anytime on the same optimum.
- **That finding an optimum is easier than proving it.** Well known.
- **That incomplete solvers are fast on random and crafted instances.** Already
  stated from Evaluation results (§2.6).
- **That the memetic is strong.** It is not state of the art as an anytime
  solver. Aperture is much stronger (`MSE26_MEMETIC_VS_APERTURE.md`), and every
  one of the 44 memetic-only instances is proved by at least one published
  complete solver. The complementarity is against EvalMaxSAT only, not against
  the MSE virtual best solver.

### 3.3 Two things to fix or state before the paper [inference]

- **Best-of-seeds bias (§2.5).**
  - "Memetic reached" counts an instance when ≥ 1 of 3 seeds reaches the
    optimum. That is the best-of-runs evaluation that Cameron et al. show
    overstates a randomized solver.
  - ρ is not affected: it uses the ERT, pooled over seeds, which is an
    expected-performance measure.
  - The 44 / 262 split, the 90.7 % coverage and the McNemar test are affected.
  - Report them also with an expected-success rule, e.g. the per-instance
    success fraction or ≥ 2 of 3 seeds. Not computed yet.
- **Wording.** Say "complementary to EvalMaxSAT on its hard tail", not "better
  than" and not "orthogonal" (see
  `RESEARCH_NOTES_COMPLEMENTARITY_VS_ORTHOGONALITY.md`).

## 4. BibTeX

Fields checked against Crossref unless stated. The series volume numbers
(LNCS 7317) were not in the Crossref records.

```bibtex
@inproceedings{xu2012contributions,
  author    = {Xu, Lin and Hutter, Frank and Hoos, Holger and Leyton-Brown, Kevin},
  title     = {Evaluating Component Solver Contributions to Portfolio-Based
               Algorithm Selectors},
  booktitle = {Theory and Applications of Satisfiability Testing -- SAT 2012},
  series    = {Lecture Notes in Computer Science},
  volume    = {7317},
  pages     = {228--241},
  publisher = {Springer},
  year      = {2012},
  doi       = {10.1007/978-3-642-31612-8_18}
}

@inproceedings{kroc2009hybrid,
  author    = {Kroc, Lukas and Sabharwal, Ashish and Gomes, Carla P. and Selman, Bart},
  title     = {Integrating Systematic and Local Search Paradigms:
               A New Strategy for {MaxSAT}},
  booktitle = {Proceedings of the 21st International Joint Conference on
               Artificial Intelligence (IJCAI-09)},
  pages     = {544--551},
  year      = {2009}
}

@inproceedings{ansotegui2014isac,
  author    = {Ans{\'o}tegui, Carlos and Malitsky, Yuri and Sellmann, Meinolf},
  title     = {{MaxSAT} by Improved Instance-Specific Algorithm Configuration},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {28},
  year      = {2014},
  doi       = {10.1609/aaai.v28i1.9128}
}

@article{ansotegui2016isac,
  author    = {Ans{\'o}tegui, Carlos and Gab{\`a}s, Joel and Malitsky, Yuri and
               Sellmann, Meinolf},
  title     = {{MaxSAT} by Improved Instance-Specific Algorithm Configuration},
  journal   = {Artificial Intelligence},
  volume    = {235},
  pages     = {26--39},
  year      = {2016},
  doi       = {10.1016/j.artint.2015.12.006}
}

@inproceedings{cameron2016bias,
  author    = {Cameron, Chris and Hoos, Holger H. and Leyton-Brown, Kevin},
  title     = {Bias in Algorithm Portfolio Performance Evaluation},
  booktitle = {Proceedings of the 25th International Joint Conference on
               Artificial Intelligence (IJCAI-16)},
  pages     = {712--718},
  year      = {2016}
}

@article{traversa2018speedup,
  author    = {Traversa, Fabio L. and Cicotti, Pietro and Sheldon, Forrest and
               Di Ventra, Massimiliano},
  title     = {Evidence of Exponential Speed-Up in the Solution of Hard
               Optimization Problems},
  journal   = {Complexity},
  volume    = {2018},
  year      = {2018},
  doi       = {10.1155/2018/7982851}
}
```

Kroc et al. and Cameron et al. have no Crossref record (IJCAI). Their pages
come from the PDF and the IJCAI abstract page.

## 5. Sources

- [Xu et al., SAT 2012 (preprint)](https://www.cs.ubc.ca/~hoos/Publ/XuEtAl12-preprint.pdf)
- [Kroc et al., IJCAI 2009](https://www.ijcai.org/Proceedings/09/Papers/097.pdf)
- [Ansótegui, Malitsky & Sellmann, AAAI 2014](https://cdn.aaai.org/ojs/9128/9128-13-12656-1-2-20201228.pdf); [AIJ 2016](https://dl.acm.org/doi/10.1016/j.artint.2015.12.006)
- [Alòs et al., arXiv 2306.07635](https://arxiv.org/html/2306.07635)
- [Cameron, Hoos & Leyton-Brown, IJCAI 2016](https://www.ijcai.org/Abstract/16/107)
- [Traversa et al., arXiv 1710.09278](https://arxiv.org/pdf/1710.09278)
- [Lei & Cai, SATLike, IJCAI 2018](https://www.ijcai.org/proceedings/2018/187)
- [Ye, Luo & Cai, arXiv 2403.06568](https://arxiv.org/abs/2403.06568)
- [MaxSAT Evaluation 2020 rankings](https://maxsat-evaluations.github.io/2020/rankings.html); [MSE 2022 talk](https://maxsat-evaluations.github.io/2022/mse22-talk.pdf)
- [MSE 2018 report, JSAT (not read)](https://content.iospress.com/articles/journal-on-satisfiability-boolean-modeling-and-computation/sat190119)
