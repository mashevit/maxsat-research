# Corpus broadening — handoff for a new thread

**Date:** 2026-09-07. Written against paper draft *Complementary Hardness in MaxSAT
Search* (Berend, Dolev, Mashevitsky) and commit `6335021`.

---

## 1. Why this exists

The tier-2 experiment is complete: 390 runs (26 SATLIB uuf250 instances × 3 configs ×
5 seeds), six figures, full statistical analysis. The paper's headline claim is
**orthogonality** — that RC2 proof-time hardness carries no information about memetic
search hardness (Spearman ρ ≈ 0.02–0.07, §3.4).

The professor's editorial review identifies a fatal problem with that claim, and it is
not the one the draft anticipated in §4 ("Corpus size and composition"). The draft
defends against *small n*. The actual objection is **restriction of range**:

> They are basically all random, of the same length, same number of variables, same
> density, and even same c\*. You can't base on it claims like orthogonality of hardness
> of finding the optimum and proving it.

Analogy from the email: testing a headache drug on 26 patients who are all male
new immigrants from Moscow, aged 52–53, weighing 78–80 kg.

**The mechanism.** Compressing the variance of a predictor attenuates any observed
correlation toward zero *mechanically*, regardless of the true relationship. ρ ≈ 0 is
exactly what range restriction produces. So the null result is not evidence of
orthogonality — it is what you would measure even if hardness were strongly shared
across the full instance space. Add that 24 of 26 instances have c\* = 1, a degenerate
corner where RC2's work is essentially one unsatisfiability proof and the EA's task is
essentially SAT-with-slack, and the claim cannot be made from this sample.

### What survives and what doesn't

| Result | Status |
|---|---|
| Polish depth dominates population size (§3.1) | **Survives.** Within-instance paired, same seed, same instance. |
| 0-vs-48 discordance, `memetic_deeppolish` strictly dominates `memetic_base` | **Survives.** Paired at the run level. |
| 29.7% of successes at generation 1 (§3.5) | **Survives.** Internal to the solver. |
| Population size buys variance reduction (§3.6) | **Survives.** |
| **Orthogonality of hardness (§3.4, abstract, title)** | **Does not survive.** Sample cannot support it. |

The surviving results are scoped to near-threshold random 3-SAT — a stated limitation,
not a broken inference. Only the orthogonality claim is destroyed, and it is the one in
the title.

### The two paths

1. **Rescope.** Demote orthogonality to a within-family controlled result: *"with
   generator, size, density, and c\* held constant, residual RC2 proof-time variation
   carries no information about heuristic difficulty."* Real, but cannot headline and
   does not support portfolio implications. Paper becomes the configuration study,
   retitled.
2. **Broaden the corpus.** The only path that keeps the claim. This document is the
   plan for that path.

These are not exclusive — rescoping now and broadening for a follow-up is a legitimate
sequencing. Worth asking the professor directly whether the rescoped configuration study
is publishable on its own.

---

## 2. The four axes

The current corpus holds four properties constant. Broadening means varying them
**independently**, so effects are attributable rather than confounded.

| Axis | Current value | Why it matters |
|---|---|---|
| **Clause length** | all ternary | RC2 behaves very differently on binary vs ternary; changes core structure |
| **Weightedness** | all unweighted | Changes RC2's algorithm (stratification, weight-aware core relaxation) and turns the EA's fitness surface from coarse integers into something fine-grained |
| **c\* magnitude** | 1 for 24/26 | c\* is roughly the number of cores RC2 must extract — a direct driver of proof time |
| **Origin** | one random generator, one density | Structured instances have entirely different proof and search geometry |

Design consequence: a small factorial (vary ratio at fixed family → vary family at fixed
ratio → add weights to both) buys attributable effects. Adding, say, weighted Max-Clique
alone moves three axes at once and explains nothing.

**Analysis consequence.** With real variance, stop reporting a single bivariate ρ.
Regress RC2 proof time on n, density, and c\*; ask whether the *residual* predicts EA
difficulty. Report correlations within strata as well as pooled. This answers the
objection on its own terms — the relationship is shown holding or failing while
covariates are *controlled*, not merely absent.

---

## 3. Families

Organised by what the **current solver stack** can run, because that determines cost.

### 3a. Pure soft — runs today, no code changes to the solver

No hard clauses, so `hv` is always 0, the fitness cliff at `population.py:161` never
fires, and every assignment is feasible by construction. These are the entire near-term
plan.

**F1. Off-threshold random 3-SAT.** *Cheapest, and attacks the objection most directly.*
Same generator you already use, with the dials turned. Ratios 5, 6, 8 at n = 100–200
put c\* in the tens instead of 1, and spread RC2 proof time over orders of magnitude.
Holding the generator fixed while varying parameters is a **feature** — it isolates
density and c\* as factors instead of confounding them with instance origin.
*Budget note:* c\* grows roughly linearly in ratio and RC2's core-guided loop scales with
it; buy spread by shrinking n as the ratio rises.
Moves: **c\***, **density/n**.

**F2. Max-2-SAT, generated directly.** Random 2-SAT at various clause ratios — a standard
MaxSAT family with its own literature, not merely a MaxCut by-product. m clauses of two
distinct literals over n variables; c\* tunable by ratio.
Moves: **clause length**, **c\***.

**F3. MaxCut, random graphs.** For each edge (u,v), two soft clauses `(x_u ∨ x_v)` and
`(¬x_u ∨ ¬x_v)`. Both satisfied iff the edge is cut; exactly one satisfied otherwise.
So cost = number of uncut edges, and c\* = |E| − maxcut. Clause length 2, c\* in the
hundreds.
Moves: **clause length**, **c\***, **origin** (graph rather than CNF).

**F4. MaxCut on structured graphs.** Torus lattices, Chimera/Pegasus topologies from the
quantum-annealing benchmarks, Gset. Same encoding as F3, structured topology.
*Flag:* the quantum time-to-solution literature is the closest prior art to this paper's
TTT methodology — running on their graphs makes that comparison concrete rather than
rhetorical.
Moves: **origin** (designed structure), and Chimera/Pegasus have known degree structure
that decouples size from density.
*Requires download* (Gset, DWave topologies) — torus lattices are generatable locally.

**F5. Weighted variants of anything above.** Nearly free: take an existing instance,
assign clause weights from a distribution (uniform small integers, or heavy-tailed).
This is the axis you had not counted as a restriction.
Moves: **weightedness**, in isolation, on a fixed base instance — the cleanest possible
single-axis manipulation available.

**F6. Pure-soft instances filtered from `mse23-uw-small`.** *Run the census first.*
"uw" means **unweighted**, not un-partial — `00000293` has 134k hard clauses because it
is judgment aggregation, not because of the track. Some fraction of the 75 instances will
have zero hard clauses and are drop-in for the current stack: no repair step, no
feasibility wall, no new config id. Highest information-per-minute step in this whole
document; see §4 Step 1.
Moves: **origin** (real applications), **c\***, possibly clause length.

**F7. SATLIB families not yet used.** `uuf50` … `uuf225` give a clean size ladder at
fixed density. `jnh`, `dubois`, `pret`, `aim-no`, `par8` add structural variety. Caveat:
most keep c\* = 1, so they help on **size** and **origin** but not on the c\* restriction —
which is the binding one.

### 3b. Needs pseudo-hard weights — runs today, with one caveat

These families are naturally *partial* (hard + soft). They can be made formally pure-soft
by giving the constraint clauses a weight exceeding the sum of all soft weights, so they
are never violated at optimum. The stack then runs them unmodified.

**Caveat to record:** this makes the instance weighted, so it moves the weightedness axis
as a side effect. Either accept the confound and note it, or pair each instance with an
F5-style unweighted control.

**F8. Max-Clique / Max-Independent-Set on DIMACS graphs.** Variable x_v per vertex; soft
unit `(x_v)` weight 1 per vertex; conflict clause `(¬x_u ∨ ¬x_v)` at big weight for each
non-edge. Classic benchmark set (brock, C-series, keller, hamming, p_hat), well studied,
wide difficulty range, encoding is a few lines.
Moves: **clause length** (units + binaries), **origin**, **c\***.
*Requires download.*

**F9. Set covering / set packing.** OR-Library, decades of instances. Variable per set;
soft unit `(¬x_S)` at the set's cost; coverage clause per element `(∨_{S∋e} x_S)` at big
weight. Gives very different clause-length distributions — long coverage clauses
alongside units.
Moves: **clause length** (wide spread), **weightedness** (natural costs), **origin**.
*Requires download.*

**F10. Max-Coloring / frequency assignment.** CELAR/GRAPH radio-link instances, or graph
colouring with soft edge constraints. Needs exactly-one-colour constraints per vertex at
big weight, plus soft edge constraints. Real-world structure, weighted variants exist.
Moves: **origin**, **weightedness**, **clause length**.
*Requires download.*

**F11. Ramsey-number and combinatorial-design instances.** Small variable counts,
extremely hard proofs. Useful *precisely because* they invert the usual
proof-time-versus-size relationship — they stress the orthogonality claim from the
opposite direction from everything else here.
Moves: **origin**, and decouples **proof hardness from instance size**, which is the
single most informative thing you can do to a hardness-transfer claim.

### 3c. Requires the decoder redesign — not near-term

**F12. Judgment aggregation and other genuinely hard-constrained MSE families.** See §6.

---

## 4. Work order for Claude Code

Audit-first, with explicit scope limits per step. Do not let it skip Step 0 — without it,
it will invent its own WCNF format and the afternoon goes to reconciliation.

### Step 0 — Audit before writing anything

> Audit `cnf.py` (both repo-root `src/` and `cluster_staging_maxsat/src/`, they are
> intentionally diverged — see `DIVERGENCE.md`) and `make_tier2_manifest.py`. Report:
> the exact WCNF output format written and parsed, including old-vs-new format handling
> (`p` header presence, `h`-prefixed hard clauses); the weight convention for hard
> clauses; the manifest row schema and every field; and how instance identity
> (SHA256) is computed. **Write no generator code in this step.**

Deliverable: a short format spec that every generator will target.

### Step 1 — The mse23 census (do this first, it is minutes)

> Across all 75 `mse23-uw-small` instances, emit one CSV row per instance:
> filename, SHA256, n variables, total clauses, hard-clause count, soft-clause count,
> clause-length histogram for hard and soft separately, number of distinct variables
> appearing in soft clauses, and whether all soft weights are 1.

The subset with **hard-clause count = 0** is immediately usable (F6). Everything else is
deferred to the decoder work. This single step may supply a substantial part of the
broadened corpus at zero generator-writing cost.

### Step 2 — Shared WCNF writer + generator skeleton

> Write one `wcnf_writer` module targeting the format spec from Step 0, and a generator
> CLI skeleton taking `--family --seed --params --out`. Every generator writes through
> this one writer. Do not duplicate serialisation logic per family.

**Requirements applying to all generators:**
- Deterministic given a seed. Same seed ⇒ byte-identical file.
- Seed and every parameter appear in **both** the filename and the manifest row. You join
  on SHA256, but you will slice by ratio and family in analysis, and reconstructing that
  from hashes later is painful.
- Emit the manifest row at generation time, not in a later pass.

### Step 3 — Generators, in this order

1. `random_ksat` — F1. n, ratio, k, seed. (Extend the existing one if it exists.)
2. `max2sat` — F2. n, ratio, seed.
3. `maxcut` — F3/F4. Takes an edge list; includes built-in generators for
   Erdős–Rényi, torus lattice, and Chimera.
4. `reweight` — F5. Takes an existing WCNF plus a weight distribution, emits a weighted
   variant. Must preserve the optimal *assignment structure* question explicitly — note
   in the manifest that c\* is **not** preserved under reweighting and must be
   re-certified.
5. `maxclique` — F8. Parses DIMACS `.clq`, big-weight conflict clauses.
6. `setcover` — F9. Parses OR-Library format.

Steps 3.5 and 3.6 require downloaded files — see limits below.

### Step 4 — Verification harness (mandatory, not optional)

> For every generated instance: (a) round-trip through the project's own `cnf.py` parser
> and assert the parsed formula matches the in-memory one clause-for-clause; (b) assert
> the SHA256 in the manifest matches the file on disk; (c) for families with a
> known-optimum construction, assert RC2 returns that optimum.

**Known-optimum constructions to use as free correctness tests:**
- MaxCut on a **bipartite** graph ⇒ maxcut = |E| ⇒ c\* = 0.
- MaxCut on a **complete graph K_n** ⇒ maxcut = ⌊n²/4⌋, closed form.
- Random 3-SAT with a **planted** satisfying assignment ⇒ c\* = 0.
- Max-Clique on a graph with a **planted clique** of known size.
- Set cover with a **known-cost** planted cover.

**Cost semantics — the high-priority trap.** The EA and RC2 both report *unsatisfied*
weight in their comparison fields, and oracle values are currently written verbatim with
no conversion. Every new family must be checked against this convention explicitly; a
generator that thinks in *satisfied* weight (MaxCut and Max-Clique both naturally do)
will silently invert every comparison. Put an assertion in the harness, not a comment.

### Step 5 — Size calibration (before any bulk generation)

> For each family, generate a small grid over the size/density parameters — a handful of
> instances per cell, one seed each — and time RC2 on every cell with a hard cap.
> Emit a table of (family, params) → RC2 median proof time → predicted tier.

Purpose: choose parameter cells that land in **T2** (certified within cap, but only after
substantial search), rather than discovering after 2,000 submitted jobs that ratio 8 at
n = 200 times out everywhere. Recall that tiering depends on the cap, and that instance
`00000293` needed >1300 s despite appearing in T2 manifests — **tier assignment must be
re-verified per instance, not inherited from a parameter cell.**

### Step 6 — Bulk generation and manifest

Only after Steps 4 and 5 pass. Generate the calibrated grid, run the full verification
harness over the output, emit the combined manifest, and report a summary table of the
corpus by the four axes of §2 — which is the artefact that answers the professor.

### What Claude Code cannot do

- **Fetch external benchmarks.** The sandbox is network-restricted to package registries.
  Gset, DIMACS `.clq`, OR-Library, CELAR must be downloaded by you and placed in the
  uploads or repo directory. Generators should be written to *parse* those formats and
  tested against a small hand-made example in the meantime.
- **Submit to SLURM.** It can write the `.sbatch` files; you submit.

---

## 5. Certification: RC2 or EvalMaxSAT

RC2 (PySAT, pure Python) is the current oracle. On a broadened corpus it will be the
bottleneck. **EvalMaxSAT** (`https://github.com/FlorentAvellaneda/EvalMaxSAT`) is the
recommended replacement: algorithmically closest to RC2 (OLL), C++, built on CaDiCaL.

Integration approach: a subprocess-based runner emitting **the same JSONL schema** as the
existing RC2 runner, with added `solver` and `solver_commit` fields. Do not change the
schema otherwise.

**Do not mix solvers within a single reported table.** If EvalMaxSAT replaces RC2, either
re-certify the tier-2 corpus with it or keep the two corpora's proof times in separate
columns with the solver named. Proof times from different solvers are not comparable, and
the orthogonality analysis is *about* proof times.

---

## 6. Further work, carried forward

### 6a. The feasibility wall and the decoder redesign

Established on `00000293` (see `docs/` report, dated 2026-09-06): the memetic EA never
reaches a hard-feasible assignment — five 1800 s runs, best `hard_violations 4249`,
`best_cost 78`, the worst attainable value — while Glucose bootstrapped on the hard
clauses alone reaches feasibility in **0.04 s**. The cause is the fitness cliff at
`population.py:161`: the entire infeasible region collapses to `-1e9 - 1e6·hv`, so there
is no gradient and the EA random-walks in 2^18508 space.

**This does not affect any committed tier-2 number** — uuf250 has no hard clauses, `hv` is
always 0, the cliff never fires.

The architectural fix, if hard-constrained families are ever taken on:

> **Genome = the soft variables only.** On `00000293` that is 78 bits, not 18,508.
> Evaluate an individual by asserting its 78 literals as *assumptions* and letting a SAT
> solver find a feasible completion; cost = how many assumptions had to be dropped.
> Crossover on 78 bits is trivially closed, mutation is a bit flip, and feasibility is
> never the EA's problem because the decoder guarantees it.

Notes on this design:
- Naive blocking clauses over the **full** assignment produce near-clones — one point out
  of 2^18508 is forbidden and the solver resumes from nearly the same state. Project the
  blocking clause onto the **soft-variable scope**. Randomising initial polarity per call
  adds diversity more cheaply still; the two combine.
- Seeding without repair is not a partial fix but a different failure mode: a feasible
  elite plus ~60 rejected children per generation, which *looks* like it is working.
- SAT-solver time must be **charged to the run clock** so TTT stays honest.
- **Never seed from RC2** or any MaxSAT-aware incumbent. RC2 is the oracle; its incumbent
  encodes objective information, and using it makes time-to-optimum circular and voids
  §3.3 and arguably §3.4. Hard-only SAT models carry zero objective information and are
  fine — that is standard practice (SATLike, NuWLS-c use decimation-based init).
- This is a **different algorithm**, not a new config of `memetic_deeppolish`. Different
  genome, different operators, different arm. It cannot share a row with the tier-2 configs.

### 6b. Three-arm ablation (answers §4's "No anytime baseline")

`memetic_deeppolish` (JW + EA + polish) vs `local_multistart_jw_deeppolish` (JW + polish,
no EA) vs `local_multistart_deeppolish` (uniform + polish, no EA). The third arm is built
but not submitted; the JW multistart arm does not exist yet.

Known risk: the JW prior signal is weak on symmetric random 3-SAT by construction (mean
deviation ≈ 0.115 from 0.5), so the middle arm may be a null result on the current corpus.
On a broadened corpus with structured instances it should have more to say.

### 6c. JW over hard clauses

`population.py:41-43` skips hard clauses ("soft-clause only"). Textbook Jeroslow–Wang sums
`weight · 2^-|C|` over *all* clauses; the soft-only restriction is the anomaly. Hard
clauses need a finite weight stand-in (count at 1, or at the sum of soft weights).

**No-op on the 26 SATLIB tier-2 instances** (no hard clauses), so no committed number
changes — a rare free fix. It does change `local_multistart_jw_*` behaviour on partial
instances, so it needs a new config id to preserve the existing arm's identity. It also
repairs the middle row of the ablation, which is currently a no-op on any partial instance.

### 6d. Incremental flip loop — the one that threatens the paper

`walksat_polish` does two full clause scans per iteration
(`_count_hard_violations` 2.87 ms, `unsat_hard_ids` 4.07 ms on the 134k-clause instance),
giving ~52 flips/sec. `SatState` already maintains `clause.true_cnt` and the
`pos_occ`/`neg_occ` lists, so incremental make/break is available and simply unused. Worth
roughly three orders of magnitude.

**But TTT and PAR2 are wall-clock.** A 1000× flip-rate change rewrites Table 1, Table 2,
the cactus plot, CPU-s per success, and the 5.6× RC2 speedup. Even on 1065-clause
instances the O(m) scan is not free. Two acceptable options:

1. Freeze tier-2 at `6335021` and apply the optimisation strictly downstream, or
2. Re-run all 390.

**Do not mix commits inside one table.**

Related referee risk worth pre-empting: a reviewer can argue the speedup over RC2 is
partly a Python constant-factor artefact. Reporting **flip-indexed** results alongside
time-indexed ones defuses this — and if the incremental rewrite preserves the RNG stream
and trajectory, flip-indexed results are exactly comparable across both implementations.

### 6e. Housekeeping

- All staging-side changes get a `DIVERGENCE.md` entry.
- Verify ERT acronym consistency between abstract and body (the EC and SAT communities
  define it differently).
- On uuf250, RC2 runtimes in the hundreds of seconds are **expected** — proving optimality
  requires many unsatisfiability proofs. Not a solver performance problem.
- Related-work BibTeX is at `related.bib`, ~45 entries.

---

## 7. First three things to do in the new thread

1. **Run the mse23 census** (Step 1). Minutes of work; may hand you a chunk of the
   broadened corpus for free.
2. **Give Claude Code the Step 0 audit prompt.** Nothing else until the format spec exists.
3. **Decide the paper question with the professor:** is the rescoped within-family
   configuration study publishable now, with corpus breadth as a follow-up? That answer
   determines whether §4 above is urgent or merely next.
