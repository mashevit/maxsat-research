# Solver design driven by large language models: a research summary

**Date:** 2026-10-11. **Requested by the user** [quote]: "I yes do want you to
compile research summary of current solver design driven by llm, with
litreture". Companion to
[`RESEARCH_NOTES_HYPERPARAMETER_TUNING.md`](RESEARCH_NOTES_HYPERPARAMETER_TUNING.md)
§6. Research note N-2026-10-11-t.

**Labels:**
- **[web-verified]**: checked on the cited page on 2026-10-11, at
  abstract, catalogue or proceedings level;
- **[secondary]**: from a summary or press page only;
- **[inference]**: my judgment for this project.

No full PDFs were read: the workstation has no PDF tools. Numbers are the
authors' own claims unless an independent study is cited.

---

## 1. What "LLM-driven solver design" means

**The common loop** (it is called *LLM-based evolutionary program search*,
EPS, or *automated heuristic design*, AHD):
1. Keep a population of **programs**, usually one function of a solver:
   a scoring rule, a priority function, a move, an operator.
2. Ask an LLM to write new variants from parents, through prompts that
   play the role of mutation and crossover.
3. **Run each variant** on training instances with an automatic evaluator.
4. Keep the best, and repeat.

The LLM supplies the variation operator over *code*. The evolutionary or
tree search and the evaluator supply the selection. The thing evolved is
the **algorithm**, not a solution. That is what separates this from tuning
numbers (the hyperparameter report) and from using an LLM to solve
instances directly.

## 2. The main methods (in order of appearance)

| method | venue | idea | reported results |
|---|---|---|---|
| **FunSearch** (Romera-Paredes et al.) | **Nature, 2023** [web-verified] | evolutionary procedure that pairs a pretrained LLM with a systematic evaluator; searches for *programs* that describe how to solve a problem | new large cap-set constructions; online bin-packing heuristics better than first-fit / best-fit [web-verified: abstract; blog] |
| **EoH**, Evolution of Heuristics (Liu, Tong, Yuan, Lin, Luo, Wang, Lu, Zhang) | **ICML 2024**, PMLR 235: 32201–32223 [web-verified] | evolves a heuristic's natural-language "thought" together with its code | bin packing, TSP, flow shop [secondary] |
| **ReEvo** (Ye et al.) | **NeurIPS 2024** [web-verified] | LLMs as hyper-heuristics; *reflections* act as verbal gradients over the heuristic space | several combinatorial problems [secondary] |
| **LLaMEA** (van Stein, Bäck) | **IEEE TEVC 29(2), 2025, pp. 331–345** [web-verified] | LLM inside a (1+1) / (μ+λ) evolution strategy; generates, mutates and selects whole metaheuristics with runtime feedback | generated algorithms beat CMA-ES and DE on 5-d BBOB; competitive at unseen 10-d and 20-d [web-verified: abstract] |
| **LLaMEA-HPO** | **ACM TELO, 2025** [web-verified] | adds SMAC hyperparameter tuning of each generated algorithm inside the loop | on par with EoH at a fraction of the LLM queries [web-verified: summary] |
| **MCTS-AHD** (Zheng, Xie, Wang, Hooi) | **ICML 2025** [web-verified] | Monte Carlo tree search over all generated heuristics instead of a population, so weak candidates can be revisited | improves on population methods on its benchmarks [secondary] |
| **HSEvo**, **EoH-S** (heuristic *sets*), **MEoH** (multi-objective) | 2024–2025 [web-verified: titles] | diversity mechanisms, complementary heuristic sets, extra objectives (e.g. code dissimilarity) | — |
| **AlphaEvolve** (Novikov et al., DeepMind) | arXiv 2506.13131, June 2025 [web-verified] | a coding agent that edits whole code bases, with an ensemble of Gemini models and automated evaluators | data-centre scheduling, kernel and compiler speed-ups, mathematical constructions [secondary: press] |
| **OpenEvolve** | open source, 2025 [web-verified: PyPI] | open re-implementation of AlphaEvolve; whole-file evolution, island populations | self-reported |
| **ShinkaEvolve** (Sakana AI) | arXiv 2509.19349, Sept 2025 [web-verified] | sample-efficient: parent sampling, novelty rejection, adaptive LLM ensemble | new circle-packing best with ~150 samples (self-reported) |

**Surveys:**
- Liu, Zhang et al., "A Systematic Survey on Large Language Models for
  Algorithm Design", arXiv 2410.14716, v5 January 2026 [web-verified]. It
  classifies work by the LLM's role, search method, prompts and domain.
- *Evolutionary Computation* 34(2) (MIT Press) [web-verified].
- arXiv 2509.08269 (LLMs for evolutionary optimisation) [web-verified].
- The **LLM4AD** platform belongs to the first survey's group
  [web-verified: cited there; details not checked].

## 3. SAT and MaxSAT specifically

| work | what the LLM designs | result |
|---|---|---|
| **AutoSAT** (arXiv 2402.10705, 2024) [web-verified] | heuristics inside a modular CDCL search space (not a solver from scratch), searched by hill climbing and a (1+1) EA | better than MiniSat on 9 of 12 datasets; better than Kissat on 4 |
| **SATLUTION**, "Autonomous Code Evolution Meets NP-Completeness" (Yu, Liang, Ho, Ren; arXiv 2509.07367, Sept 2025) [web-verified] | LLM agents evolve **whole solver repositories** (hundreds of files) from SAT Competition 2024 solvers, with correctness checks and distributed runtime feedback | the abstract claims the evolved solvers "decisively outperformed the human-designed winners of the SAT Competition 2025". A secondary summary says an evolved Kissat variant won first place there on PAR-2, stronger on SAT than on UNSAT [secondary] |
| **KissatEvolve** [secondary] | LLM plus evolutionary search on Kissat heuristics; listed for SAT Competition 2026 | no details found |
| **Schidler & Szeider**, "Extracting Problem Structure with LLMs for Optimized SAT Local Search" (arXiv 2501.14630, 2025) [web-verified] | the LLM reads the **Python encoding code** of a problem family and writes a specialised local search, used as a CDCL preprocessing start | "encouraging": faster than baseline preprocessing |
| **Pre-LLM precedent: CLASS** (Fukunaga, *Evolutionary Computation* 2008) [web-verified: preprint] | genetic programming evolves SAT local-search variable-selection heuristics on random 3-SAT | competitive with hand-designed heuristics [secondary] |

**MaxSAT:** I found **no published LLM-driven design of MaxSAT local
search** (scoring, clause weighting) [web-verified: a targeted search came
back empty]. The closest pattern is LLM-evolved *score functions* inside a
greedy local search for causal structure learning (IJCAI 2025)
[web-verified]. This is an open niche.

## 4. Evidence on limits (independent or critical)

- **The LLM alone is not enough** (Zhang, Liu, Lin, Wang, Lu, Zhang,
  PPSN 2024; arXiv 2407.10873) [web-verified]:
  - a benchmark of 4 EPS methods × 4 problems × 9 LLMs × 5 runs;
  - repeated prompting without search plateaus, even with more queries
    and stronger models;
  - no single method or LLM wins everywhere;
  - the search strategy matters.
- **Poor generalisation and overfitting:**
  - Sim, Hart, Renau, "Beyond the Hype: Benchmarking LLM-Evolved
    Heuristics for Bin Packing" (EvoSTAR 2025; arXiv 2501.11411): most
    LLM heuristics "do not generalise well" across a broad benchmark, and
    the gains must be weighed against generation cost [web-verified].
  - A follow-up, arXiv 2510.27353, reports overfitting to narrow instance
    clusters and questions novelty [web-verified: summary].
- **Scale:** for EoH-evolved TSP improvement heuristics, the gap widens as
  instance size grows [web-verified: summary of a method paper]. 2026
  preprints report degradation under distribution shift and recommend
  holding out the largest instances [secondary; check before citing].
- **Agentic benchmarks show headroom:**
  - **HeuriGym** (NeurIPS 2025 / ICLR 2026): even top models reach a
    Quality-Yield Index of about 0.6, against an expert baseline of 1
    [web-verified].
  - **CO-Bench** (AAAI): 36 combinatorial problems, agents compared with
    human-designed algorithms [web-verified].
- **Cost:** AlphaEvolve-style systems need thousands of evaluations
  [web-verified: HeuriGym and Sakana statements]. Sample efficiency is a
  current research theme (ShinkaEvolve).

## 5. What this means for our solver [inference]

1. **The evaluation cost decides feasibility.** Each candidate heuristic
   would need runs on a training set:
   - our memetic runs cost seconds (S band) to 900 s (L band);
   - an EoH-style search of ~1,000 candidates × 10 instances × short
     budgets is tens to hundreds of CPU-hours in the S band only.
   - Feasible, but a project of its own, not part of HP-1.
2. **Where an LLM could design something useful in our code:**
   - **the polish's variable-selection score** in
     `walksat_v2.py`: break / make / noise;
   - **the clause-aware crossover's proxy scores;**
   - **the feasible moves of the hard-clause solver.**
   - These are small, well-defined functions with fast evaluators,
     the setting where FunSearch / EoH / ReEvo work.
   - The MaxSAT local-search niche is open (§3).
3. **The literature's warnings apply directly to us:**
   - evolve on small instances, but **validate on held-out larger
     instances** (the same lesson as configuring for scaling);
   - report the generation cost;
   - compare against tuned baselines (our tuned flip rule after HP-1),
     not defaults.
4. **Methodological conflict with the corpus study.** The corpus measures
   instance difficulty for *this* solver. A solver redesigned by an LLM
   would be a new solver version, with the same version-boundary rules as
   v1 / v2.
5. **Order:** HP-1 (tuning numbers) first. An LLM design study, if wanted,
   comes after HP-1, so it starts from a tuned baseline.

## 6. Two ways to use an LLM: as an agent, or inside a search (added 2026-10-11)

*This section records two follow-up questions from the user the same day:
"what is HeuriGym benchmark" and what it means to "wrap the LLM in a much
larger search that evaluates thousands of candidates". It sharpens §1 and
§4, and refines the cost estimate in §5.*

**HeuriGym** (Chen, Wang, Cai, …, Gomes, Zhang; arXiv 2506.07972, June 2025,
revised January 2026; NeurIPS 2025 / ICLR 2026) [web-verified: abstract]:
- **Task:** an LLM writes heuristic code for 9 combinatorial problems from
  computer systems, logistics and biology. The abstract does not name the
  problems.
- **Loop:** the code is run, the feedback comes back, and the model
  revises its code over a few rounds.
- **Score:** the **Quality-Yield Index**, which combines the valid-solution
  rate (yield) with solution quality relative to experts. The expert
  baseline is 1. The exact formula was not checked.
- **Result:** across 9 models, the best (GPT-o4-mini-high, Gemini-2.5-Pro)
  reach about **0.6**.
- **Motivation:** existing tests are closed questions that saturate or can
  be memorised, or subjective comparisons.

**Agent versus search:**

| | LLM as agent (HeuriGym) | LLM inside a search (FunSearch, AlphaEvolve, EoH, ReEvo) |
|---|---|---|
| role of the LLM | the whole designer: writes, reads feedback, revises | a **mutation operator**: proposes variants of parent programs |
| who decides what is good | largely the LLM's own judgement of the feedback | an **automatic evaluator** that runs every candidate |
| scale | one line of work, a handful of rounds | a population (islands), **thousands of candidates** generated and evaluated |
| failure mode | a wrong idea early is rarely rescued | most outputs may be bad; selection discards them, and rare good ideas are kept and built on |
| cost | low | evaluation-bound: candidates × instances × seeds × run time |

Why the search wins on discovery [inference, supported by §4]:
- a bad proposal costs only its evaluation;
- an occasional good one survives selection;
- small gains accumulate over many generations.

The PPSN 2024 study shows that prompting alone plateaus without the
search. Reducing the number of candidates is current work: ShinkaEvolve
reports a record with about 150.

**Cost for our solver** [inference; refines §5]:
- **Example:** evolving the polish's variable-selection score, with each
  candidate run on 10 small instances × 3 seeds × 60 s.
- **Per candidate:** about 30 CPU-minutes.
- **For 2,000 candidates:** about 1,000 CPU-hours, roughly 10× the whole
  HP-1 calibration budget. On L-band instances (900 s runs) it would be
  far more.

**Takeaway.** In an LLM-design study here, the LLM would sit inside the
search, applied to a small, fast-to-evaluate function, on small training
instances. It would be validated on held-out larger instances against the
tuned HP-1 baseline. The overfitting results in §4 make that validation
mandatory, for the same reason as any tuning.

## 7. What an LLM-design study here would look like, and the decision not to pursue it (2026-10-11)

*This section records the explanation of §6's takeaway ("put the LLM inside
a search over a small, fast-to-evaluate function; train on small instances;
validate on held-out larger ones against the tuned HP-1 baseline"). It ends
with the user's decision.*

### 7.1 Design sketch [inference]

1. **The LLM inside a search.**
   - A harness runs an evolutionary loop over ~20–50 versions of one Python
     function, for ~1,000–2,000 iterations.
   - In each iteration, the LLM receives 1–2 good parents and their
     scores and proposes a variant.
   - The harness plugs the variant into the solver, runs it on the
     training instances, and keeps it or discards it.
   - The harness's measurement decides what is better, not the LLM.
2. **One small function.** The natural target is the variable-selection
   rule of the polish in `walksat_v2.py` (break counts plus noise today).
   Alternatives: the crossover proxy scores, or the hard-clause solver's
   moves. Small, because:
   - it is a narrow search space with fixed inputs and one output;
   - any gain is attributable to that component;
   - it cannot cheat: the harness recomputes the final cost, as
     `run_memetic_shard` already cross-checks;
   - the result is a short rule that can be read and explained.
3. **Fast to evaluate.**
   - Every candidate costs one evaluation, and there are thousands.
   - So the function must matter in short runs: seconds to a minute per
     instance.
   - The rule runs at every flip, so fitness is measured in seconds. A
     clever but slow rule is penalised automatically.
4. **Training on small instances.**
   - S band (n ≤ 400): 465 instances with a proven c\*.
   - E.g. 10 instances × 3 seeds × 60 s ≈ 30 CPU-minutes per candidate.
5. **Validation on held-out larger instances.**
   - M and L bands, e.g. calib_2sat_sc/sc2 at n = 8,000–64,000, with
     fresh seeds, never seen in the search.
   - Required because LLM-evolved heuristics overfit and degrade with
     size (§4). It is the same lesson as configuring for scaling in HP-1.
6. **Against the tuned HP-1 baseline.**
   - At large n the default 12,500 flips is undersized. Any change that
     searches more would beat it, for reasons that tuning alone fixes.
   - Comparing against `max(12500, c·n)` with c calibrated isolates the
     new rule's own contribution.
   - So HP-1 would come first.
7. **Caveats.**
   - An evolved rule is a new solver version, with the same comparability
     boundary as v1 / v2.
   - The best c may shift with a new selection rule, so it must be
     re-checked.
   - The cost is ~1,000 CPU-h for 2,000 candidates, even on small
     instances (§6).

### 7.2 Conclusion: not pursued [decision, user, 2026-10-11]

**The user decided not to go in the LLM-driven design direction.**

The reasons, from this document [inference]:
- **Cost.** Even the narrowest useful study (one function, small
  training instances) is about 1,000 CPU-h. That is roughly 10× the
  whole HP-1 calibration, before validation on large instances.
- **Weak transfer.** The independent evidence is that LLM-evolved
  heuristics often fail to generalise beyond their training instances
  and degrade with size (§4). Our corpus spans m = 48 to 70,000.
- **It conflicts with the study's aim.** The corpus measures instance
  difficulty for a fixed, documented solver. Redesigning the solver's
  core rules would open a new version boundary and weaken comparability
  with the existing memetic results.
- **Better expected value is elsewhere.** Size-aware tuning (HP-1) addresses
  the known weakness, the undersized flip limit at large n, with a
  standard, cheap and explainable method.

**What stays:** this document, as related-work context for the thesis. If
the direction is ever reopened, §7.1 is the starting design. It would
begin only after HP-1, against the tuned baseline.

## Sources

- FunSearch: [Nature paper (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10794145) · [DeepMind blog](https://deepmind.google/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/) · [code](https://github.com/google-deepmind/funsearch)
- EoH: [PMLR (ICML 2024)](https://proceedings.mlr.press/v235/liu24bs.html) · [arXiv 2401.02051](https://arxiv.org/abs/2401.02051v3)
- ReEvo: [NeurIPS 2024 listing](https://mlanthology.org/neurips/2024/ye2024neurips-reevo) · [arXiv 2402.01145](https://arxiv.org/abs/2402.01145v3)
- LLaMEA: [arXiv 2405.20132](https://arxiv.org/abs/2405.20132v4) · [Leiden repository (TEVC)](https://scholarlypublications.universiteitleiden.nl/access/item%3A4291380/download) · [GitHub](https://github.com/XAI-liacs/LLaMEA) · [LLaMEA-HPO (ACM TELO)](https://dl.acm.org/doi/10.1145/3731567)
- MCTS-AHD: [arXiv 2501.08603](https://arxiv.org/abs/2501.08603v1) · [ICML 2025 slides](https://icml.cc/media/icml-2025/Slides/45984_i4beMa3.pdf)
- HSEvo: [arXiv 2412.14995](https://arxiv.org/html/2412.14995v1) · EoH-S: [arXiv 2508.03082](https://www.arxiv.org/pdf/2508.03082)
- AlphaEvolve: [arXiv 2506.13131](https://arxiv.org/abs/2506.13131.pdf) · [MIT Technology Review](https://www.technologyreview.com/2025/05/14/1116438/google-deepminds-new-ai-uses-large-language-models-to-crack-real-world-problems/amp/)
- OpenEvolve: [PyPI](https://pypi.org/p/openevolve) · ShinkaEvolve: [arXiv 2509.19349](https://arxiv.org/pdf/2509.19349)
- Surveys: [arXiv 2410.14716](https://arxiv.org/pdf/2410.14716) · [Evolutionary Computation 34(2)](https://direct.mit.edu/evco/article/34/2/167/133803/Exploring-Automated-Algorithm-Design-Synergizing) · [arXiv 2509.08269](https://arxiv.org/pdf/2509.08269)
- SAT: [AutoSAT (arXiv 2402.10705)](https://arxiv.org/pdf/2402.10705) · [SATLUTION (arXiv 2509.07367)](https://arxiv.org/abs/2509.07367) · [Schidler & Szeider (arXiv 2501.14630)](https://arxiv.org/abs/2501.14630) · [CLASS preprint](https://metahack.org/ecj08-web-preprint.pdf) · [solver listing incl. KissatEvolve](https://maplesat.github.io/solvers.html)
- Score-function evolution: [IJCAI 2025](https://www.ijcai.org/proceedings/2025/1010.pdf)
- Limits: [PPSN 2024 (arXiv 2407.10873)](https://arxiv.org/pdf/2407.10873) · [Beyond the Hype (arXiv 2501.11411)](https://arxiv.org/pdf/2501.11411) · [Bin packing study (arXiv 2510.27353)](https://arxiv.org/pdf/2510.27353)
- Benchmarks: [HeuriGym (arXiv 2506.07972)](https://arxiv.org/pdf/2506.07972) · [CO-Bench (arXiv 2504.04310)](https://arxiv.org/pdf/2504.04310)
