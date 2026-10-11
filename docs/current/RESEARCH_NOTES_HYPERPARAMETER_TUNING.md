# Hyperparameter setting for our solvers: frameworks, algorithms, and what is influential now

**Date:** 2026-10-11. **Requested by the user** [quote]: "do now research and
report of hyperparameter setting frameworks, and alghoritms available and
currently influencial online". The companion plan, with the size inventory and
a calibration design, is [`HYPERPARAMETER_CALIBRATION_PLAN.md`](HYPERPARAMETER_CALIBRATION_PLAN.md).
Research notes N-2026-10-11-r (the HP-1 to-do) and N-2026-10-11-s.

**Status labels:**
- **[web-verified]**: read on the cited page on 2026-10-11 (abstract or
  catalogue level unless stated);
- **[memory]**: from my training knowledge, not re-checked today. The
  citation is likely right, but check it before quoting in a paper;
- **[inference]**: my judgment about how it applies here.

Full-text PDFs could not be read on this workstation (no PDF tools). Where a
paper's claim matters, it is given at abstract level.

---

## 1. The problem in the field's terms

What the user asked for, "a hyperparameter function, maybe with categories of
instance size", falls into four established problem types:

| problem | what is learned | our case |
|---|---|---|
| **Algorithm configuration (AC)**, also called offline parameter tuning | one configuration for a whole instance distribution | today: one YAML per arm |
| **Per-instance AC (PIAC)** / instance-specific AC | a map from instance features to a configuration | **HP-1**: features = size (n, m), maybe k, weighted, hard fraction |
| **AC for scaling** | settings tuned on small, cheap instances that must work on large ones | n = 50–400 instances are cheap; n = 16000–64000 cost 900 s per run |
| **Dynamic AC (DAC)** / parameter control | a policy that changes parameters *during* a run | e.g. polish length that adapts while a run improves; not requested yet |

Survey of the whole AC field: **Schede, Brandt, Tornede, Wever, Bengs,
Hüllermeier, Tierney, "A Survey of Methods for Automated Algorithm
Configuration", JAIR 75 (2022) 425–487** [web-verified]. It gives taxonomies
of the problem and of the methods. Older but standard on tuning versus
control: **Eiben & Smit, "Evolutionary Algorithm Parameters and Methods to
Tune Them" (2011)** [web-verified: link exists; content memory].

## 2. Algorithm-configuration frameworks (offline, across instances)

| tool | method | instances and features | current release | fit for us [inference] |
|---|---|---|---|---|
| **irace** (R) | iterated racing, an extension of iterated F-race: sample configurations, race them over instances, drop losers by statistical test, refit the sampling model | instances: yes. Elitist racing and capping exist [memory] | **4.5, CRAN, 2026-09-15** [web-verified] | **Good.** Racing in rounds suits Slurm arrays. Handles ordinal or categorical parameters such as a flip-limit grid. Needs R in the loop, but only on the workstation. |
| **SMAC3** (Python) | Bayesian optimisation with a random-forest surrogate plus aggressive racing ("intensification"); facades for HPO and algorithm configuration | instances and instance features: yes [memory; the PyPI page names multi-instance AC but not features] | **2.4.1, PyPI, 2026-09-10** [web-verified]; "all facades/intensifiers support multi-objective, multi-fidelity, and multi-threading" | **Good, if the parameter space grows.** Python, so it fits our stack. Its sequential ask-tell loop is awkward with 900 s cluster runs, but batches of asks can be submitted as arrays. |
| **ParamILS** | iterated local search in configuration space, **adaptive capping** of slow runs | instances: yes | old (Hutter et al., JAIR 2009) [memory] | historical; capping is the idea worth keeping |
| **GGA / GGA++** | gender-based genetic algorithm; GGA++ adds a surrogate | instances: yes | Ansótegui et al. 2009 / 2015 [memory]; PyDGGA exists [memory] | used by ISAC (below) [web-verified] |
| **Optuna** (Python) | define-by-run HPO: TPE (default), CMA-ES, NSGA-II, GP samplers; pruners for early stopping | no instance concept: an "instance" must be folded into the objective | **5.0.0, PyPI, 2026-09-07** [web-verified] | Fine for a single aggregated objective, but it does not race across instances. |
| **Hyperband / BOHB / DEHB** | multi-fidelity: run many configurations cheaply (low "budget"), promote the good ones. BOHB adds a KDE model; DEHB adds differential evolution | the budget can be runtime or instance size | Hyperband: Li et al., JMLR 2018 [memory]; BOHB: Falkner et al., ICML 2018 [memory]; **DEHB: Awad et al., IJCAI 2021** [web-verified] | **The idea is relevant:** our fidelities are run budget (s) and instance size. Mostly built for ML training. |
| **HEBO, Ax/BoTorch, Ray Tune** | BO toolkits and orchestration | not AC-specific | [memory] | not needed at our parameter count |

**Benchmarking AC on SAT:** the **Configurable SAT Solver Challenge**
(Hutter, Lindauer, Balint, Bayless, Hoos, Leyton-Brown; editions 2013 and
2014; arXiv 1505.01221) scored SAT solvers "after a fully automated
configuration step" [web-verified]. Its message is that default parameters
are a poor proxy for peak performance. AClib is the companion benchmark
library [memory].

## 3. Per-instance configuration: from features to settings

- **ISAC** (Kadioglu, Malitsky, Sellmann, Tierney, ECAI 2010)
  [web-verified: paper and summary]:
  - clusters training instances in feature space and tunes one
    configuration per cluster with GGA;
  - at run time, a new instance gets its cluster's configuration.
  - **This is exactly the "categories" idea**, with clusters instead of
    hand-made size bins.
- **ISAC+ for MaxSAT** (Ansótegui, Malitsky, Sellmann et al.; title
  "MaxSAT by improved instance-specific algorithm configuration")
  [web-verified: title and summary; authors and year from memory]. It adds a
  portfolio stage. It is the closest MaxSAT precedent.
- **Hydra** (Xu, Hoos, Leyton-Brown, AAAI 2010) [web-verified]:
  - builds a *portfolio* of configurations by repeated AC, each run
    targeting the instances where the portfolio is still weak;
  - argues that ISAC's distance-only clustering can be fooled by
    uninformative features.
  - **Lesson for us:** size alone may not be the feature that matters.
    k (2-SAT vs 3-SAT), weights and hard clauses could matter more.
- **Instance-based parameter tuning by regression** (Brendel & Schoenauer,
  GECCO 2011) [web-verified: title and summary]. It learns "the relation
  between some features … and the optimal parameters", which allows
  extrapolation to unseen instances. This is the continuous-function
  alternative to categories.
- **Recent:** a 2025 paper speeds up ISAC's run-time cluster assignment
  with a graph neural network (arXiv 2501.11240) [web-verified: abstract].
- **Algorithm selection** is the sibling field: SATzilla, AutoFolio, ASlib
  [memory]. It chooses among solvers or configurations instead of tuning one.

## 4. Configuring for scaling: tune small, run large (most relevant to HP-1)

| work | idea | result |
|---|---|---|
| **Styles, Hoos, Müller, "Automatically Configuring Algorithms for Scaling Performance"** (LION 6, 2012) [web-verified: title, domains TSP/LKH, MIP/CPLEX, Go/Fuego] | the standard protocol (tune on the training distribution) underperforms when the target instances are much larger; a cheap change to the protocol | configurations 5–75 % better than the standard protocol within the same tuning budget [web-verified via search abstract] |
| **Styles & Hoos, racing protocols for scaling** (2013) [web-verified: abstract] | combine racing with configurators when the target instances are too hard to use in tuning | often close to an oracle selector's bound |
| **Mascia, Birattari, Stützle, "Tuning Algorithms for Tackling Large Instances: An Experimental Protocol"** (LION 7, LNCS 7997, 2013, pp. 410–422) [web-verified] | tune on small instances and **extrapolate a scaling law for the parameters**. Both the parameter scaling and the tuning cut-off time are free parameters, set by minimising a loss | proof of concept: iterated local search and robust tabu search on QAP. Follow-up: a "cut-off-time policy t(s)" and a "parameter configuration policy m̂(s, t(s))" [web-verified] |
| **Mu, Hoos, Stützle, "The impact of automated algorithm configuration on the scaling behaviour of state-of-the-art inexact TSP solvers"** (LNCS 10079, 2016) [web-verified: abstract] | configure **how a parameter adapts to instance size** (EAX) | EAX's median running time scaling changed from root-exponential to polynomial; LKH overfitted the training sizes |

**[inference] What this means for HP-1:**
1. **A size-dependent parameter rule is an established, effective idea.** In
   EAX it changed the scaling class. A flip limit that grows with n is the
   same kind of rule.
2. **Tuning only where it is cheap fails at the large end.** Both Styles et
   al. and Mu et al. saw it. So the calibration must hold out large
   instances for validation, and must not tune on n ≤ 400 alone.
3. **Tuning cut-offs should scale with size too** (Mascia et al.'s t(s)).
   Small instances get short budgets in calibration, large ones long.
4. **Categories versus a continuous rule** is not settled in the
   literature:
   - ISAC uses categories (clusters);
   - Mascia and Mu fit a scaling law;
   - our calibration should fit both and compare them on held-out instances.

## 5. Dynamic algorithm configuration and parameter control

- **DAC** learns a *policy* that sets parameters during a run. Formalised
  and surveyed in **Adriaensen, Biedenkapp, Shala, Awad, Eimer, Lindauer,
  Hutter, "Automated Dynamic Algorithm Configuration", JAIR 75 (2022)
  1633–1699** [web-verified: abstract; venue from search]. The abstract's
  key point: static AC means "parameter settings remain fixed throughout the
  run".
- **DACBench** (Eimer et al., IJCAI 2021) is its benchmark library, with
  6 initial benchmarks [web-verified].
- The EA tradition of **parameter control and self-adaptation** (e.g. a
  mutation rate adapted online) is the older relative [memory].
- **[inference] For us:** a polish call that keeps flipping while it still
  improves, instead of a fixed flip limit, is a hand-made dynamic rule. It
  would make the flip limit less critical. It is an alternative or
  complement to HP-1, not part of this request.

## 6. What is currently influential (2023–2026)

- **LLM-driven algorithm design.** LLMs generate and evolve solver code or
  heuristics. This is the most visible trend.
  - **Methods:**
    - FunSearch (Nature 2023) [memory];
    - **EoH**, Evolution of Heuristics (thoughts and code evolved
      together) [web-verified: summary];
    - **ReEvo** (reflective evolution) [web-verified: summary];
    - **LLaMEA** (LLM-driven EA design) [web-verified: repo and slides];
    - **LLaMEA-HPO**, ACM TELO 2025: it puts SMAC-based HPO inside the
      loop, and reports results "on-par with EoH" in a fraction of the
      time [web-verified: summary].
  - **Surveys:** arXiv 2509.08269 (LLMs for evolutionary optimisation) and
    Evolutionary Computation 34(2) [web-verified].
  - **[inference]** Expensive in evaluations, and aimed at *designing*
    heuristics, not tuning a few numbers. Not our tool for HP-1. Relevant
    later only if the polish or operators themselves are redesigned.
- **LLMs inside Bayesian optimisation:** **LLAMBO** (Liu et al., ICLR 2024)
  uses an LLM as surrogate and sampler, helping zero-shot warm-starting
  [web-verified]. Its later influence is not quantified.
- **Priors and meta-learning in HPO:**
  - **PriorBand** (NeurIPS 2023): Hyperband plus expert priors
    [web-verified];
  - **PFNs4BO** (ICML 2023): in-context-learned surrogate models
    [web-verified].
  - **[inference]** Our existing evidence (12,500 flips good at n ≤ 400;
    200k better at n ≥ 16000 in the smoke) is such a prior.
- **Mature tools keep shipping:** irace 4.5 (2026-09), SMAC 2.4.1 (2026-09),
  Optuna 5.0.0 (2026-09) [web-verified]. These remain the workhorses.

## 7. Recommendation for HP-1 [inference]

1. **Method: batch racing over a small grid, per size category.**
   - **The parameter space is tiny:** the per-call flip limit is primary;
     pop size and the per-call time limit are secondary.
   - **Runs are long and run as Slurm arrays;** the login node allows no
     controller.
   - **So use offline rounds:** each round is one array; the workstation
     reads it, eliminates configurations by a paired test across instances
     and seeds, and prepares the next round. This is irace's logic, done by
     hand.
   - **If the space grows** (noise, pmutate, time limit, pop), move to
     irace or SMAC3 in ask-tell batches.
2. **Protocol from the scaling literature:**
   - **Size-scaled tuning budgets.** Short for small categories, 900 s only
     for the largest.
   - **Held-out validation in every category,** with fresh seeds,
     *including the largest*.
   - **Fit both a categorical table and a continuous law,** e.g. flips =
     clip(a · n^b), and keep the one that wins on held-out data.
3. **Features:**
   - start with size (m, or n);
   - check k and weightedness as second features, as Hydra warns;
   - hard-clause instances (MSE) are a separate category set for the
     hard-clause solver.
4. **Objective:**
   - the Q2 quantities (success out of seeds, median TTT, ERT_s), with
     stop at the known optimum;
   - fails count at the budget, as in PAR-2-style scoring.
   - Only instances with a proven c\* can be used.

## Sources

- [A Survey of Methods for Automated Algorithm Configuration (arXiv 2202.01651; JAIR 75, 2022)](https://arxiv.org/abs/2202.01651v3)
- [irace on CRAN](https://cran.r-project.org/package=irace) · [irace user guide](https://mlopez-ibanez.r-universe.dev/irace/doc/irace-package.pdf)
- [SMAC3 on PyPI](https://pypi.org/project/smac/) · [SMAC3 paper (arXiv 2109.09831)](https://ar5iv.org/html/2109.09831) · [SMAC at automl.org](https://www.automl.org/hpo-overview/hpo-tools/smac/)
- [Optuna on PyPI](https://pypi.org/project/optuna/) · [Optuna CMA-ES sampler](https://hub.optuna.org/samplers/cmaes/)
- [DEHB (arXiv 2105.09821)](https://arxiv.org/pdf/2105.09821) · [DEHB, IJCAI 2021](https://www.ijcai.org/proceedings/2021/0296.pdf) · [HPOBench](https://arxiv.org/pdf/2109.06716)
- [The Configurable SAT Solver Challenge (arXiv 1505.01221)](https://arxiv.org/abs/1505.01221)
- [ISAC (Kadioglu et al., ECAI 2010)](https://ai.dmi.unibas.ch/research/reading_group/kadioglu-et-al-ecai2010.pdf) · [Hydra (Xu et al.)](https://www.cs.ubc.ca/~hoos/Publ/XuEtAl10.pdf) · [ISAC+ for MaxSAT (summary)](https://liner.com/review/maxsat-by-improved-instancespecific-algorithm-configuration) · [Fast ISAC with GNN (arXiv 2501.11240)](https://arxiv.org/html/2501.11240v1)
- [Instance-based parameter tuning for evolutionary AI planning (GECCO 2011)](https://dl.acm.org/doi/10.1145/2001858.2002004)
- [Styles, Hoos, Müller 2012](https://www.cs.ubc.ca/~hoos/Publ/StyEtAl12.pdf) · [Styles & Hoos 2013](https://cs.ubc.ca/labs/algorithms/Projects/Config4Scaling/LION-2013-Scaling.pdf) · [Styles & Hoos (racing)](https://www.cs.ubc.ca/~hoos/Publ/StyHoo13b.pdf)
- [Mascia, Birattari, Stützle, LION 7 (ULB record)](https://difusion.ulb.ac.be/vufind/Record/ULB-DIPOT:oai:dipot.ulb.ac.be:2013/152014/TOC) · [ORBEL abstract](https://www.orbel.be/orbel27/pdf/abstract301.pdf)
- [Mu, Hoos, Stützle 2016 (ULB record)](https://difusion.ulb.ac.be/vufind/Record/ULB-DIPOT:oai:dipot.ulb.ac.be:2013/245217/TOC)
- [Automated Dynamic Algorithm Configuration (arXiv 2205.13881)](https://arxiv.org/abs/2205.13881) · [JAIR record](https://mlanthology.org/jair/2022/adriaensen2022jair-automated) · [DACBench (IJCAI 2021)](https://ijcai.org/proceedings/2021/230)
- [Eiben & Smit 2011](https://www.cs.vu.nl/~gusz/papers/2011-Eiben-Smit-EA-parameters-and-their-tuning.pdf)
- [LLaMEA (GitHub)](https://github.com/XAI-liacs/LLaMEA) · [LLaMEA-HPO (ACM TELO)](https://dl.acm.org/doi/10.1145/3731567) · [EoH](https://www.emergentmind.com/papers/2401.02051) · [LLM + EA survey (Evol. Comput.)](https://direct.mit.edu/evco/article/34/2/167/133803/Exploring-Automated-Algorithm-Design-Synergizing) · [LLMs for evolutionary optimisation survey (arXiv 2509.08269)](https://arxiv.org/pdf/2509.08269)
- [LLAMBO (ICLR 2024)](https://proceedings.iclr.cc/paper_files/paper/2024/hash/84b8d9fcb4e262fcd429544697e1e720-Abstract-Conference.html)
- [PriorBand (NeurIPS 2023)](https://proceedings.neurips.cc/paper_files/paper/2023/hash/1704fe7aaff33a54802b83a016050ab8-Abstract.html) · [PFNs4BO (ICML 2023)](https://proceedings.mlr.press/v202/muller23a.html)
- [NuWLS (AAAI 2023)](https://ojs.aaai.org/index.php/AAAI/article/view/25505) — MaxSAT local search context only
