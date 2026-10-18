# A stronger memetic: design of B1–B5, their interactions, and the build plan for a third staging tree (2026-10-18)

**Request (user, 2026-10-18)** [quote]: "write it, also do the reasoning of
interactions- I want you next step implement all the ideas for stronger solver
in new folder analogue to the cluster_staging_maxsat/_hard in 3rd folder".

**Status:** design. **Built 2026-10-18** in `cluster_staging_maxsat_strong/`
(commit `16589fb`). The build record, deviations, smoke run and batch S1 are
in [`STRONG_MEMETIC_S1_RUN.md`](STRONG_MEMETIC_S1_RUN.md). Index: `docs/current/RESEARCH_NOTES.md`, N-2026-10-18-b.

**Background:**
- `docs/current2/KERNEL_MEMETIC_RUN.md` §5: the short proposal this document
  expands.
- `docs/current/RESEARCH_NOTES_SOLVER_DIRECTIONS.md` §5 B, §9.1 (the mutation
  measurement), §9.2 (tabu).

**Tags:**
- [verified]: measured here or read off code;
- [source]: checked in the cited paper this session (the abstract, or the
  full text where it says "full text");
- [unverified]: from memory, check before citing;
- [inference]: my reasoning, to be tested;
- [proposal]: a design choice.

---

## 0. Summary

| # | component | targets which weakness | expected effect [inference] | cost per call |
|---|---|---|---|---|
| B1 | **Tabu / configuration checking** in the WalkSAT polish | the polish undoes its own moves in chains of degree-2 variables | fewer wasted flips on plateaus; most visible on kernels (s253) | O(1) per candidate (tenure), O(degree) per flip (CC) |
| B2 | **Clause-weighting local search** (a SATLike-style two-mode core) | plain WalkSAT has no memory on plateaus and local minima | escapes local minima the WalkSAT polish cannot; the main lever on s253 | O(degree) per flip, plus O(#falsified) per weight update |
| B3 | **Distance-aware mutation** | fixed-rate mutation (0.02 · n flips) destroys good solutions on big instances | children start next to their parent; polish time goes into search, not repair | O(k) instead of O(n) random draws |
| B4 | **Partition crossover (PX)** | per-variable crossover cannot keep a parent's good block intact | the child is the best of 2^q recombinations and never worse than either parent | O(n + m) per child |
| B5 | **Compiled inner loop** | pure Python: 180k–380k flips/s on the cluster | 10–50× more flips per second [inference, unmeasured] | none at run time; a compile step |

**The two lines:**
1. B3 and B1 fix things that are wrong today, so they come first.
2. B2 and B4 add search power, and B5 adds speed.

The interactions (§6) are what decide the build and test order, and they
matter as much as the components.

---

## 1. What the current solver does [verified: code at `754392a`]

- **EA** (`src/evo/memetic.py`):
  - population 40;
  - tournament k = 3;
  - 5% elites kept;
  - each child = crossover → mutation → polish → evaluate;
  - target stop and deadline clipping.
- **Crossover** (`impl_v2.clause_aware_crossover1_v2`):
  - variables where the parents agree are kept;
  - where they differ, the choice goes by the hard-clause effects, then a
    *static* soft proxy score (the weight of soft clauses with v positive vs
    negative), then the fitter parent's bit.
  - Each variable is decided alone, and the static score does not depend on
    the parents.
- **Mutation** (`operators.mutate1`): each variable is flipped with
  probability `pmutate` = 0.02, unless the flip breaks a satisfied hard
  clause. That is about 0.02 · n flips per child.
- **Polish** (`sat/walksat_v2.walksat_polish_v2`):
  - pick a random falsified clause (hard first);
  - shuffle its variables;
  - with probability noise = 0.10 take the first one, otherwise the one with
    the best gain;
  - it has no memory: no tabu and no clause weights. (`smooth_every` is a
    no-op in v2.)
  - The best state is kept by a flip trail.
- **Measured weaknesses:**
  - one mutation takes the optimum of s256 (n 64,000) from 13 to 832–948
    unsatisfied clauses (directions §9.1);
  - the raw arm went 0/18 in 900 s (m2v2);
  - on the 434-variable kernel of s253 the memetic stays at 15 vs c\* 14,
    while RC2 proves 14 in 58 s (KERNEL_MEMETIC_RUN §2, §5).

---

## 2. B1: tabu and configuration checking

### 2.1 Motivation [verified + inference]

- The kernel and the raw formula both consist mostly of chains: variables of
  degree 2 that were not eliminated, and binary clauses linking them.
- In a chain, the falsified clause can move back and forth: flipping x
  satisfies (x ∨ y) but falsifies (¬x ∨ z); the next step picks (¬x ∨ z) and
  may flip x straight back.
- In soft-only 2-SAT both of these moves have gain 0. With noise 0.10 and
  random clause choice, nothing stops the walk from undoing itself.
- WalkSAT's only defence is noise, which is undirected.

### 2.2 How it works

- **Tabu tenure.**
  - A variable flipped at step t may not be flipped again before step
    t + tenure.
  - **Aspiration:** a tabu move is allowed if it gives a new best.
  - If every candidate of the chosen clause is tabu, take the least recently
    flipped one.
- **Configuration checking (CC)**, Cai and Su:
  - a variable may not flip back until at least one of its neighbours (a
    variable sharing a clause with it) has flipped since its own last flip;
  - it has no parameter;
  - its rationale is exactly the chain case: if nothing around x changed, x
    flipping back can only return to a state already seen.
- **Least-recently-flipped tie-break** (SATLike): the weakest form, used only
  to break ties.

### 2.3 Sources

- **WalkSAT/TABU** is named in McAllester, Selman and Kautz (AAAI 1997) as
  the tabu variant of WalkSAT, with the tenure as its noise-like parameter
  [source].
  - The value "about 10" is [unverified].
- **RoTS / IRoTS** for MAX-SAT (Smyth, Hoos and Stützle, Canadian AI 2003)
  [source; values from a copy of the paper]:
  - tenure n/10 + 4 in the local-search phase, n/2 in the perturbation;
  - re-drawn from an interval every n steps;
  - a variable unflipped for 10n steps is forced;
  - aspiration on a new best.
  - Also recorded in `RESEARCH_NOTES_FLIP_LIMIT_SCALING.md` §2.3.
- **Configuration checking:** Cai and Su, *Artificial Intelligence* 2013
  (Swcc); CC with aspiration in AAAI 2016 [source]. The MaxSAT solver CCLS
  (Luo, Cai, Wu, Jie and Su, IEEE Trans. Computers 64, 2015) uses CC
  [source].

### 2.4 Tenure scale: why not n/10 here [inference]

- RoTS picks the best non-tabu variable among **all** n variables, so its
  tenure has to grow with n.
- Our polish picks among the **2 variables of one falsified clause** (the
  WalkSAT architecture). A tenure of n/10 would make both candidates tabu
  almost always: at raw n 64,000 that is 6,404 steps.
- So the WalkSAT/TABU scale applies: a small constant.

### 2.5 Parameters [proposal]

| key | values | default when absent |
|---|---|---|
| `ls.tabu` | `none` · `tenure` · `cc` | `none` (= v2) |
| `ls.tabu_tenure` | grid {3, 10, 30} | 10 when `tabu: tenure` |
| `ls.tabu_tenure_rand` | add a random 0…r per flip; grid {0, 5} | 0 |
| aspiration | always on (new best on the true cost) | — |
| all-tabu rule | least recently flipped | — |
| `ls.noise` | existing; with tabu or CC try {0.10, 0.02} | 0.10 |

### 2.6 Implementation sketch [proposal]

- An array `last_flip[v]` (the flip counter at v's last flip).
- CC needs a flag `conf[v]`:
  - set it to False when v flips;
  - set it to True for each neighbour of v;
  - neighbour lists are built once per instance, from the occurrence lists v2
    already caches.
- **Equality test:** with `ls.tabu: none`, the polish returns exactly v2's
  output: the same flips and the same RNG draws.

---

## 3. B2: clause-weighting local search

### 3.1 Motivation [inference]

- At a local minimum of the true cost, WalkSAT can only escape by noise or a
  lucky clause choice.
- Clause weighting changes the landscape where the search is stuck:
  - the falsified clauses get heavier, so moves that satisfy them become
    improving under the dynamic weights;
  - the search walks out of the basin in a directed way;
  - weights that build up record which clauses are hard to satisfy together.
- This is the core of today's strongest MaxSAT local search (SATLike, NuWLS).
- s253 is the test case: a 434-variable kernel where the polish stalls at
  c\* + 1.

### 3.2 How SATLike works [source: full text, IJCAI 2018 pp. 1346–1352]

- **Weights:**
  - each hard clause gets a weight initialised to 1;
  - each soft clause starts at its original weight (1 when unweighted).
- **Two modes per step:**
  1. If there are **decreasing variables** (score > 0 under the dynamic
     weights), pick one by **BMS**: draw t variables with replacement, take
     the highest score, and break ties by least recently flipped.
  2. Otherwise the search is **stuck**:
     - update the weights;
     - pick a random falsified hard clause if there is one, else a random
       falsified soft clause;
     - flip its variable with the highest score, ties by least recently
       flipped.
- **Weighting-PMS update when stuck:**
  - with probability 1 − sp: every falsified hard clause gets
    w += h_inc, and every falsified soft clause gets w += 1 if w < ζ;
  - with probability sp (**smoothing**): every satisfied hard clause with
    w > 1 gets w −= h_inc, and every satisfied soft clause with w > 1 gets
    w −= 1.
- **Published parameters:**

  | benchmark | t | sp | h_inc | ζ |
  |---|---:|---:|---:|---:|
  | PMS random / crafted | 15 | 0.01 | 2 | 1 |
  | PMS industrial | 42 | 0.000003 | 1 | 400 |
  | WPMS | 15 | 0.01 or 0.0001 | 3 | 1 |

  For WPMS, h_inc = 300 and ζ = 500 when the average soft weight is above
  10,000.
- **Best-solution bookkeeping:** the best feasible solution is tracked on the
  **original** cost, not the dynamic weights.
- **Related work:**
  - NuWLS (Chu, Cai and Luo, AAAI 2023) [source: abstract] adds an
    initialisation of the soft weights and different update conditions for
    hard and soft clauses. A NuWLS hybrid won all four incomplete-track
    categories of MSE 2022.
  - SATLike 3.0 appears in Cai and Lei, *AIJ* 287 (2020) [source: abstract].
- **Background on weighting:**
  - SAPS (Hutter, Tompkins and Hoos, CP 2002): multiplicative scaling with
    probabilistic smoothing [source].
  - PAWS (Thornton, Pham, Bain and Ferreira, AAAI 2004): additive
    weighting. It scales better and needs less tuning than multiplicative
    weighting [source: abstract].
  - SATLike's scheme is additive.

### 3.3 The catch for our instances: c\* > 0 and no hard clauses [inference]

- SATLike's soft-weight limit ζ = 1 on random and crafted PMS means **soft
  weights never grow**. There, the weighting acts on the hard clauses only.
- **Our Max-2-SAT grid has no hard clauses at all**, so with ζ = 1 SATLike's
  scheme would never change a weight. We need ζ > 1.
- **With c\* > 0, every assignment, including the optimum, falsifies at
  least c\* clauses.** At the optimum the search is "stuck" by definition, so
  the weights of the c\* clauses falsified there keep rising until the search
  leaves the optimum.
  - That is intended (it is how weighting escapes), but it means the
    weighted landscape never settles on the optimum.
  - So three things are needed: the best state must be tracked on the true
    cost (as SATLike does), ζ bounds the build-up, and smoothing (sp) lets
    it decay.
- **Proposed grid** (to calibrate, not to adopt):
  - ζ ∈ {10, 50, 400};
  - sp ∈ {0.01, 0.001};
  - t ∈ {15, 42}.
  - h_inc stays as published for any hard clause (not exercised on this
    grid).

### 3.4 Weight lifetime inside a memetic: our design choice [proposal]

- `ls.weights: call`: the weights are reset to the original at each polish
  call. Each child is polished independently, as today.
- `ls.weights: run`: one weight vector per run, carried from call to call.
  The weights then become a population-level memory of the clauses that are
  hard to satisfy together.
- I know of no source for `run` [unverified idea]. It is cheap to offer and
  is tested as its own arm.

### 3.5 Parameters [proposal]

| key | values | default |
|---|---|---|
| `ls.core` | `walksat` · `dls` | `walksat` (= v2) |
| `ls.dls_t` | BMS samples | 15 |
| `ls.dls_sp` | smoothing probability | 0.01 |
| `ls.dls_zeta` | soft-weight limit | 50 |
| `ls.dls_h_inc` | hard increment (MSE later) | 1 |
| `ls.weights` | `call` · `run` | `call` |

### 3.6 Implementation sketch [proposal]

- A new module `src/sat/dls.py` with the same call signature and return keys
  as `walksat_polish_v2`.
- **State:**
  - the dynamic weights `dw[c]`;
  - `score[v]`: the change in falsified dynamic weight if v flips, kept
    incrementally from true-literal counts. A flip touches only the clauses
    of v and the scores of their variables, so it costs O(degree) in 2-SAT;
  - the decreasing set D, kept as an array plus a position index (O(1) add
    and remove);
  - the falsified set, the same structure as in v2.
- **A weight update** touches each falsified clause (fewer than ~1,000 even
  after a raw mutation, ≈ c\* near the optimum) and the scores of their
  variables. Smoothing touches the satisfied clauses with w > 1, which are
  kept in a list.
- **The best state** is a trail on the true cost, as in v2.
- **Tests:**
  - scores equal a full recomputation after every flip and every weight
    update (randomised, small instances);
  - the reported best equals the true cost of the returned assignment;
  - with hard clauses, a returned feasible state is truly feasible.

---

## 4. B3: distance-aware mutation

### 4.1 Motivation [verified]

| instance | n | flips per mutation (≈ 2% of n) | unsat before | after one mutation |
|---|---:|---:|---:|---:|
| s256 | 64,000 | ≈ 1,280 | 13 (= c\*) | 832–948 |
| s251 | 16,000 | ≈ 320 | 12 (= c\*) | 255–311 |

- The damage grows linearly with n, while the optimum stays at 9–14 clauses.
- Each polish call (12,500 flips) spends most of its flips repairing that
  damage in the easy 99% of variables (directions §9.1).

### 4.2 How it works

- The iterated-local-search rule (Lourenço, Martin and Stützle, *Iterated
  Local Search*) [source]:
  - a perturbation that is too strong makes ILS a random restart;
  - one that is too weak lets the local search fall straight back into the
    local optimum just left.
  - Strength = the number of solution components changed, and the best
    strength depends on the problem.
- A fixed per-variable rate makes the strength grow with n, which is the
  wrong scaling here.

### 4.3 Modes [proposal]

| `ea.mutation` | what it does | locality |
|---|---|---|
| `rate` (default = today) | each variable with probability `pmutate` | none |
| `count` | exactly k random variables | none, but bounded damage |
| `walk` | start at a random variable and take a random walk of k steps in the variable-interaction graph, flipping each new variable visited | one neighbourhood: the polish repairs locally |
| `diff` | k variables among those where the parents differ (all of them if fewer than k); if the parents are equal, fall back to `walk` | only where the population is undecided |

- **Parameter:** `ea.mutation_k`, grid {4, 8, 16, 32}. It is the same for raw
  and kernel, because the damage no longer scales with n.
- Every mode goes through the same hard-clause guard as `mutate1` (a flip
  that breaks a satisfied hard clause is refused). That guard has no effect
  on this grid.
- **Diagnostic, recorded per run:** the mean number of unsatisfied clauses
  added by one mutation. This makes the 13 → 900 effect visible in every
  shard.

---

## 5. B4: partition crossover

### 5.1 Motivation [inference]

- Today's crossover decides each differing variable alone, from a static
  score that ignores both parents' contexts.
- On a sparse instance, the variables where two good parents differ usually
  fall into many **independent** groups. Each group can be taken whole from
  the parent that does better there.

### 5.2 How it works and why the child is never worse

- **Sources:**
  - Tinós, Whitley and Chicano, FOGA 2015, pp. 137–149
    (doi 10.1145/2725494.2725497) [source: metadata];
  - Chen, Whitley, Tinós and Chicano, GECCO 2018, pp. 921–928, "Tunneling
    between plateaus" (PXSAT) [source: abstract]. PX splits the evaluation
    into independent components and finds the best of exponentially many
    children in O(n). PXSAT improved AdaptG2WSAT and Sparrow and beat CCLS.
- **The operator:**
  1. Let D = {v : A[v] ≠ B[v]}.
  2. Take the variable-interaction graph (an edge between two variables that
     share a clause) restricted to D. Its connected components are
     C₁ … C_q.
  3. For each component, compare the clauses it touches under A and under
     B, and keep the better parent's values on that component.
  4. Variables outside D take the common value.
- **Why it is exact** [derived here; matches the cited claim]:
  - Take any clause c. Its variables in D are pairwise adjacent in the graph
    (they share c), so they all lie in **one** component, or c has none.
  - Hence c's satisfaction depends only on the common values and the choice
    made for that one component.
  - The total cost is therefore a constant plus a sum of per-component
    terms. Choosing the better parent per component gives the best of all
    2^q children.
  - That child is at least as good as A and at least as good as B (both are
    among the 2^q).
  - The same holds lexicographically for (hard violations, soft cost), so
    hard clauses do not break it.
- **Cost:** one BFS over D, plus one pass over the clauses touching D:
  O(n + m) at worst.

### 5.3 The degenerate cases [inference]

- **q = 1** (one component): the child equals the better parent. That is a
  wasted child unless mutation follows.
- **A = B:** D is empty, and the child is a copy.
- In a converged population both cases become common.

### 5.4 Parameters [proposal]

| key | values | default |
|---|---|---|
| `ea.crossover` | `clause_aware` (= today) · `px` | `clause_aware` |
| `ea.px_min_q` | below this q, use the fallback | 2 |
| `ea.px_fallback` | `clause_aware` · `mutate_only` | `clause_aware` |

- **Diagnostic, recorded per run:**
  - the distribution of q (median, max);
  - the fallback rate;
  - the share of children equal to a parent.
- How many components our parent pairs have is **unknown**. It is the first
  thing the smoke will measure, on raw and on kernels. Resolution adds
  clauses between neighbours, so kernels may be denser.

---

## 6. Interactions: the reasoning that fixes the order

Each pair below gives a mechanism [inference], what it implies for the
design, and how the batch tests it.

### 6.1 B3 × B2: mutation must shrink before weighting can show

- **Mechanism:** after a fixed-rate mutation on the raw formula, the polish
  starts ~900 clauses above the optimum. Almost every flip then improves the
  true cost, and the search is rarely "stuck". Clause weighting acts **only
  when stuck**, so in the repair phase B2 and WalkSAT behave alike. B2's
  advantage appears only near local optima.
- **Implication:**
  - on raw instances, B2's effect can be measured only together with B3;
  - on kernels the damage is small already (2% of 434 ≈ 9 flips), so B2 can
    be tested alone there.
- **Test:** on raw, compare B2 with B3 against B3 alone, and B2 alone against
  baseline. Expected [inference]: B2 alone ≈ baseline on raw; B2 + B3 > B3.

### 6.2 B1 × B2: tabu and weighting both fight cycling, and can conflict

- **Mechanism:**
  - Weighting already breaks cycles: after an update, the move that undoes
    the last one usually no longer scores best.
  - A tabu tenure on top can **forbid the very move the weights now
    promote**.
  - SATLike uses only a least-recently-flipped tie-break; CCLS uses CC with
    its own weighting.
- **Implication:**
  - in the `dls` core, offer only the tie-break plus optional CC, not a hard
    tenure;
  - in the `walksat` core, tabu and CC are the main anti-cycling tool.
- **Test:** `walksat + tabu` vs `walksat + cc` vs `dls` vs `dls + cc`.
  Expected: the gain from B1 is large in `walksat` and small or negative in
  `dls`.

### 6.3 B3 × B4: mutation makes PX's components, and PX makes heavy mutation costly

- **Mechanism (one way):** PX needs parents that differ in **several
  independent** places. A `walk` or `diff` mutation followed by a polish
  changes one neighbourhood, so a child differs from its parent in a few
  local regions. That is exactly the shape PX recombines well.
  - A fixed-rate mutation spreads differences everywhere, and the polish
    then leaves a few large, merged differences: possibly q = 1.
- **Mechanism (the other way):** a PX child is at least as good as both
  parents, so it starts near a local optimum. A heavy mutation applied after
  it throws that gain away.
- **Implication:** B4 is paired with B3 (small k) by default. Fixed-rate
  mutation after PX is offered only as a control.
- **Also:** when q = 1 or A = B, mutation is the only source of novelty, so
  the fallback must still mutate.

### 6.4 B4 × B1/B2: PX is only as good as the local optima it recombines

- **Mechanism:**
  - PX's guarantee is relative to the parents.
  - In "Tunneling between plateaus" it recombines the local optima of a
    strong local search.
  - A stronger polish (B1/B2) gives better and more varied local optima, so
    PX has more good blocks to combine.
  - Conversely, PX lets the population keep good blocks that a polish found
    in different children. That is something no single polish call can do.
- **Implication:** B4 is evaluated on top of the best polish, not on the
  baseline polish only.

### 6.5 B2 weights × the population (`ls.weights: run`)

- **Mechanism:**
  - Run-level weights remember the clauses that are hard to satisfy together
    across children.
  - Risk: once the population sits near the optimum, the c\* falsified
    clauses there accumulate weight in every call. The run-level weights
    then push all children away from the optimum region (§3.3), and keep
    doing so for the rest of the run.
  - Smoothing and ζ bound this.
- **Implication:** `run` is a separate arm, never the default, and ζ is
  smaller there.

### 6.6 B5 × everything: speed changes the balance of the time budget

- **Mechanism:**
  - With 10–50× more flips per second, a 3.5 s polish call does 10–50× more
    work. So the right flip limit per call, children per run and
    generations per run all move (Stage L1 tuned these for Python speed).
  - The relative value of B1–B4 can change too. A slow polish benefits most
    from better starting points (B3, B4); a fast one benefits most from
    better search (B1, B2).
- **Implication:**
  - B5 is built last, after B1–B4 are fixed in Python. It ports only the
    polish cores (B1, B2), and its results are compared only within a speed.
  - The C core must reproduce the Python core exactly (§7.5), so that
    "B5 on/off" changes speed and nothing else.
  - B3 and B4 stay in Python: they cost O(n) per child, against seconds of
    polish.

### 6.7 Kernelising (direction A) × B1–B4

- **On kernels (300–572 variables):**
  - B3 matters less: fixed-rate damage is ~9 flips.
  - B1 and B2 matter most: s253 is a search-quality failure on a small
    instance.
  - B4 is uncertain: the kernel may be denser.
- **On the raw formula:** B3 first, then B2 (§6.1). B4 may find many
  components, because the raw graph is sparse.
- **Implication:** every arm runs on both kernel and raw, so the interaction
  with A is measured, not assumed.

### 6.8 Hard clauses (MSE, the hard tree) × B2, B4

- B2 and B4 both handle hard clauses as designed (h_inc; the lexicographic
  PX choice). They are tested only on tiny brute-force cases in this build.
- The hard-clause track stays in `cluster_staging_maxsat_hard/`.
- Merging the two trees is a later decision, not part of this build.

### 6.9 What the interactions imply for the test design

- A full factorial of five components (32 arms) is too much to read.
- **Leave-one-out from "all on"**, plus a baseline and two diagnostic pairs,
  answers the question that matters: does each component still help when
  the others are present? §8.3 has the batch.
- **Order of the build:** B3 → B1 → B2 → B4 → B5.
  - B3 and B1 are small and fix known defects.
  - B2 needs B3 to be measurable on raw.
  - B4 needs B3 and a good polish.
  - B5 needs B1–B2 frozen.

---

## 7. B5: compiled inner loop

### 7.1 Motivation [verified]

- v2 does 180k–380k flips/s on the cluster.
- A C loop over flat arrays typically runs one to two orders of magnitude
  faster than CPython [inference; no measurement here].

### 7.2 Design [proposal]

- **The code:** a C file `src/native/ls_core.c` with the two polish cores
  (`walksat` + tabu/CC, `dls`) over flat CSR arrays of clauses and
  occurrences. It is loaded with `ctypes` (standard library, no new
  dependency).
- **Build:** at first use, `cc -O2 -shared -fPIC` into a cache directory
  next to the tree.
  - If there is no compiler, the run uses the Python twin and records
    `ls_native: false` in the shard.
  - `m2_results.py` refuses an arm whose tasks disagree on `ls_native`.
- **The RNG:** a portable generator (splitmix64 / xoshiro256\*\*),
  implemented identically in C and in Python. The Python twin of each core
  uses it.
  - **Test:** with the same seed, the C core and the Python twin return the
    same flips, trajectory and best state.
  - So B5 changes only the speed.

### 7.3 How the B1–B4 Python cores relate to v2 [proposal]

- The v3 Python cores take an RNG object with `randbelow(n)` and `random()`.
- Given a wrapper around `random.Random(seed)` and all new options off, they
  reproduce v2 **exactly**. That is the equality test, and it keeps the
  baseline continuous.
- Given the portable RNG, they reproduce the C core exactly.

### 7.4 Unknown: is there a compiler on the cluster?

Check on the login node (shell only, not heavy):

```bash
which cc gcc clang; gcc --version | head -1
```

- If there is none, B5 runs only on the workstation, and cluster arms use
  the Python twin.

### 7.5 Equality is the acceptance bar

- Speed numbers come only from the cluster, as for v1 → v2
  (`MEMETIC_IMPL_V2.md`).

---

## 8. Build plan: the third staging tree

### 8.0 Update 2026-10-18: copy from the hard tree; user answers

**User** [quote]: "name of folder o.k. I think start from copying the solver
from _hard, that works with hard clauses also, based on glucoze. tell me your
opinion that if it does not occur hard clauses in instance, It will also
work., If it may do problem for compiling inner loop state so".

**Cluster compiler** [verified, user's login-node output]:
- `/usr/bin/cc` and `/usr/bin/gcc` exist (GCC 11.5.0, Red Hat 11.5.0-11);
- there is no clang.
- Compute nodes are assumed to have the same image. The first B5 smoke job
  checks this (`gcc --version` in the job log).

**Does `impl: hard` work on soft-only instances?** [verified: workstation,
s251 raw (n 16,000, c\* 12), seed 1, 30 s, target stop, both configs from the
hard tree; the two runs were concurrent]

| arm | cost at 30 s | children | time in feasible moves M | moves tried / improving | repair calls |
|---|---:|---:|---:|---:|---:|
| `impl: v2` | **23** | **365** | — | — | — |
| `impl: hard` (H3 defaults) | 49 | 9 | 28.6 s of 30 | 1,630 / 953 | 0 |

- **Correct, yes; efficient, no.** With no hard clauses:
  - Glucose initialisation is a JW-phase draw (0.33 s);
  - repair is never called;
  - the polish is v2's, because the no-op counting never triggers.
- **But the feasible moves M become single-variable moves.** Each one costs
  a Glucose call plus an O(m) Python recomputation of the soft cost
  (`SoftView.cost`, `unsat`).
  - They take 95% of every polish slot, giving 40× fewer children and a
    worse result.
  - M exists for hard clauses, where a single safe flip almost never exists
    (H3: 99.99% no-op steps on ja-385). With no hard clauses, every flip is
    safe, and WalkSAT does the same move without the O(m) cost.
- **The hard tree also lacks what came after 2026-10-11:**
  - the kernel (`src/sat/kernel.py`, `preprocess: kernel`, shard schema 4,
    the `m2_results.py` check);
  - `ls.polish_cap: time | flips_only`;
  - the results tooling (`m2_results.py`, the manifest maker), which was not
    copied into it.

**Decision proposed:**
- **Base the tree on `cluster_staging_maxsat_hard/`**, so the hard-clause
  machinery (Glucose init, repair R, moves M, child-correct mutation guard,
  no-op counting) is there for MSE later.
- **Port from `cluster_staging_maxsat/`:**
  - the kernel module and its shard path (schema 4);
  - `polish_cap`;
  - `m2_results.py` and the manifest maker.
- **In `impl: v3`, engage the hard machinery only when the instance being
  solved has hard clauses.** After kernelising this is the kernel, whose
  `kernel_n_hard` the shard already records.
  - With zero hard clauses, v3 follows the v2 path: JW seeding, no Glucose,
    no M or R.
  - Recorded as `hard_mode: auto → off/on` in the shard.
- **Two equality tests keep both baselines:**
  - v3 with no new options on a soft-only instance == staging `impl: v2`;
  - v3 with no new options on a hard instance == hard tree `impl: hard`.

**Does the hard machinery complicate the compiled inner loop (B5)?**
[inference]
- **No, with one condition.** Glucose (via PySAT, C++), repair R and moves M
  sit **outside** the flip loop. They are separate operators called between
  polish calls, and B5 does not touch them.
- The flip loop itself must support hard clauses in both cores:
  - the v2 WalkSAT core has the hard-first clause pick, `hard_safe` and
    `budget_counts_noops`;
  - the DLS core has the hard weights with `h_inc`.
  - In C these are an `is_hard` array and a few branches.
- The condition: the C-vs-Python-twin equality tests must cover the hard
  branches too, on random instances with hard clauses. That adds test
  surface, not risk.
- The one real interaction is the per-run SAT solver's memory and lifetime.
  It already exists in Python, unchanged by B5.
- **Build of the `.so`:**
  - compile inside the job (`cc -O2 -shared -fPIC`, under a second) into a
    per-task temporary directory, so the login node runs nothing;
  - on failure, the Python twin runs and `ls_native: false` is recorded.
- **PySAT versions:** 1.9.dev3 on the cluster, 1.9.dev15 on the workstation.
  The v3 shard records the PySAT version whenever Glucose is used, as the RC2
  rows do.

### 8.1 The tree [proposal]

- **Name:** `cluster_staging_maxsat_strong/`.
- **Source of the copy** (updated 2026-10-18, §8.0):
  `cluster_staging_maxsat_hard/` at the commit current when the build starts,
  plus the kernel, `polish_cap` and the results tooling ported from
  `cluster_staging_maxsat/`. Originally proposed: `cluster_staging_maxsat/`
  at the commit current when the build starts. That is the `impl: v2` solver, target stop,
  clipping, the kernel (`src/sat/kernel.py`, `preprocess: kernel`) and the
  results tooling.
- **Provenance:** a `PROVENANCE.md` as in the hard tree: the source commit,
  the sha256 of every copied file, what was not copied, and a change log.
- **Rules:**
  - `cluster_staging_maxsat/` and `cluster_staging_maxsat_hard/` are **not
    edited** by this work.
  - Rows from this tree are a new algorithm (`impl: v3`). They never share a
    stratum or table with v2 rows, except the declared v2 baseline arm.
  - Run the tests from inside the tree.
- **Copied:**
  - `src/`, `configs/tier2/`;
  - the solver, kernel and results tests;
  - `tier2_memetic_array.sbatch`, `submit_m2_memetic.sh` (throttle 1000);
  - `m2_results.py`, the manifest maker;
  - the six eligible sc2 instances (by manifest, not by copy, as in the
    upload lists).
- **Not copied:** RC2, EvalMaxSAT and calibration-only scripts, `results/`,
  `*.bak`.

### 8.2 Steps of the build [proposal]

Each step ends with the full test suite green. The baseline equality tests
run after every step.

| step | what | key tests |
|---|---|---|
| S1 | create the tree from the hard tree; port kernel, `polish_cap`, results tooling; `PROVENANCE.md`; `impl: v3` with `hard_mode: auto` | copied suites (hard + staging solver/kernel/results tests) pass; v3-no-options == staging v2 on soft-only; == hard-tree `impl: hard` on a hard instance |
| S2 | **B3** mutation modes + the damage diagnostic | `rate` == `mutate1` stream; `count`/`walk`/`diff` flip exactly k (or all of D); hard guard respected |
| S3 | **B1** tabu / CC in a v3 WalkSAT core (RNG-object interface) | `tabu: none` == v2; tenure never violated except by aspiration; CC rule checked step by step |
| S4 | **B2** `dls` core | incremental scores == full recompute after every flip and update; best == true cost of the returned assignment; brute-force optimum reached on tiny instances; feasibility with hard clauses |
| S5 | **B4** PX + diagnostics | child ≥ both parents (randomised, with and without hard clauses); child == best of all 2^q (brute force on small q); fallback when q < `px_min_q` |
| S6 | **B5** portable RNG, Python twins, C core, ctypes loader, fallback | C == Python twin exactly for both cores on random instances; fallback recorded; `m2_results` refuses mixed `ls_native` |
| S7 | workstation smoke (60 s, seed 1, the 6 instances, raw + kernel, all-on and baseline) + manifests + upload list | shard schema check; diagnostics present |

- The user asked for all ideas in the next step. I would build S1–S7 in one
  go, with the test gate after each step. If a step fails its acceptance, I
  stop there and report rather than build on it.

### 8.3 The first batch [proposal; for approval after the build]

- **Instances:** the 6 eligible calib_2sat_sc2 instances (c\* 9–14),
  **raw and kernel**.
- **Seeds and budget:** seeds 1–3; 900 s; stop at c\*; deadline clip.
- **Arms** (v3 unless stated):

| arm | B1 | B2 | B3 | B4 | why |
|---|---|---|---|---|---|
| baseline | — | — | — | — | = v2 (raw: m2v2; kernel: the kern batch); rerun in v3 for continuity |
| all | cc | dls | walk k=16 | px | the full solver |
| −B1 | — | dls | walk | px | leave-one-out |
| −B2 | cc | — (walksat) | walk | px | leave-one-out |
| −B3 | cc | dls | rate | px | leave-one-out |
| −B4 | cc | dls | walk | clause_aware | leave-one-out |
| B3 only | — | — | walk | — | §6.1: B2's effect needs B3 |
| walksat+cc+B3 | cc | — | walk | — | §6.2: B1 in the WalkSAT core |

- **Size:** 8 arms × 6 instances × 3 seeds × 2 (raw, kernel) = **288 tasks**.
  - Worst case 288 × 960 s = **76.8 CPU-h**.
  - One wave at %1000; queue delay is separate.
  - Expected [inference]: far less, because kernel arms stop in seconds.
- **Values:** the starting values (k = 16, ζ = 50, sp = 0.01, t = 15) are
  pre-registered for this batch only. Calibration of each parameter comes
  after the leave-one-out reading, not before.
- **Pre-registered reading:**
  - success = c\* within 900 s;
  - per arm and instance, report successes / 3, median TTT and the gap;
  - plus the diagnostics: mutation damage, q, fallback rate, stuck events,
    tabu/CC blocks.
  - A component "helps" if removing it lowers successes or raises TTT on at
    least 2 of the 6 instances in both raw and kernel, or in the one where
    §6 predicts it.
- **B5:** compared separately, as the "all" arm with `ls_native` true vs
  false, on the same tasks, after the reading.

---

## 9. Open questions for the user

1. **The tree name** `cluster_staging_maxsat_strong/`: **OK (user, 2026-10-18).** Base: the hard tree (§8.0).
2. **Build S1–S7 in one go** (as asked), with stop-on-failure: OK?
3. **The cluster compiler** (§7.4): **gcc 11.5.0 present** (user, 2026-10-18).
4. **The batch** (§8.3) is for approval after the build. Its size and arms
   may change once the smoke has measured q and the mutation damage.

---

## Sources

Checked this session; the label says how far.
- Lei and Cai, "Solving (Weighted) Partial MaxSAT by Dynamic Local Search
  for SAT", IJCAI 2018, pp. 1346–1352, doi 10.24963/ijcai.2018/187. Full
  text read: weighting rules and parameters.
  <https://www.ijcai.org/proceedings/2018/187>
- Chu, Cai and Luo, "NuWLS: Improving Local Search for (Weighted) Partial
  MaxSAT by New Weighting Techniques", AAAI 2023, doi
  10.1609/aaai.v37i4.25505 (abstract).
  <https://ojs.aaai.org/index.php/AAAI/article/view/25505>
- Cai and Lei, "Old techniques in new ways: Clause weighting, unit
  propagation and hybridization for maximum satisfiability", *AIJ* 287
  (2020) 103354 (abstract).
  <https://www.datalearner.com/academic/journal-papers/0004-3702/volumes-and-issues/473/paper-detail/2697>
- Tinós, Whitley and Chicano, "Partition crossover for pseudo-Boolean
  optimization", FOGA 2015, pp. 137–149, doi 10.1145/2725494.2725497
  (metadata). <https://repositorio.usp.br/item/002739922>
- Chen, Whitley, Tinós and Chicano, "Tunneling between plateaus: improving
  on a state-of-the-art MAXSAT solver using partition crossover", GECCO
  2018, pp. 921–928, doi 10.1145/3205455.3205482 (abstract).
  <https://portaldelainvestigacion.uma.es/documentos/66408496e31a4e2a3c88b276>
- McAllester, Selman and Kautz, "Evidence for invariants in local search",
  AAAI 1997, pp. 321–326 (abstract and introduction).
  <https://mlanthology.org/aaai/1997/mcallester1997aaai-evidence>
- Smyth, Hoos and Stützle, "Iterated Robust Tabu Search for MAX-SAT",
  Canadian AI 2003, LNCS 2671, pp. 129–144, doi 10.1007/3-540-44886-1_12
  (tenure values from a copy of the paper).
  <https://www.cs.ubc.ca/~hoos/Publ/SmyHooStu03.pdf>
- Hutter, Tompkins and Hoos, "Scaling and Probabilistic Smoothing: Efficient
  Dynamic Local Search for SAT", CP 2002, LNCS 2470, pp. 233–248.
  <https://www.cs.ubc.ca/~hoos/Publ/cp02-saps.pdf>
- Thornton, Pham, Bain and Ferreira, "Additive Versus Multiplicative Clause
  Weighting for SAT", AAAI 2004, pp. 191–196 (abstract).
  <https://mlanthology.org/aaai/2004/thornton2004aaai-additive>
- Cai and Su, "Local search for Boolean Satisfiability with configuration
  checking and subscore", *AIJ* 2013, doi 10.1016/j.artint.2013.09.001; and
  "Configuration Checking with Aspiration in Local Search for SAT", AAAI
  2016.
  <https://datalearner.com/academic/journal-papers/0004-3702/volumes-and-issues/390/paper-detail/2069>,
  <https://ojs.aaai.org/index.php/AAAI/article/view/8133>
- Luo, Cai, Wu, Jie and Su, "CCLS: An efficient local search algorithm for
  weighted maximum satisfiability", IEEE Trans. Computers 64 (2015)
  1830–1843 (as cited in
  <https://cs.adelaide.edu.au/~markus/pub/2016maxsat-sc2016.pdf>).
- Lourenço, Martin and Stützle, "Iterated Local Search" (perturbation
  strength). <https://arxiv.org/abs/math/0102188>
- Lardeux, Saubion and Hao, "GASAT: a genetic local search algorithm for the
  satisfiability problem" (crossover + tabu in a SAT memetic; related work;
  check the venue before citing).
  <https://leria-info.univ-angers.fr/%7Ejinkao.hao/papers/EC06.pdf>
