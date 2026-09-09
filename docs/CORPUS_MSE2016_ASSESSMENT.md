# The MSE-2016 instances in `more_data/` — what they cover, what they don't, and how to sample them

**Date:** 2026-09-09. Written against commit `82da1b8`. Answers the three questions
put to this thread:

1. Is the `more_data/` corpus enough, or are own generators still needed?
2. Which subdirectories yield tier-2 instances, and how do I sample them?
3. What counts as "enough variety"?

Companion to [`more_data/CORPUS_BROADENING_HANDOFF.md`](../more_data/CORPUS_BROADENING_HANDOFF.md)
(the plan this corpus is being measured against) and
[`docs/RC2_STATUS.md`](RC2_STATUS.md) (the tier definition).

Every number below is measured on this workstation, not inferred.
**§7 is the inventory of every file this work added or changed.**

---

## 0. Git hygiene

| Path | Size | Ignored? | |
|---|---|---|---|
| `solver_EvalMaxSat/` | 21 MB | yes — `.gitignore:64` | ✅ |
| `more_data/` instances | 32 MB, 856 files | yes — `.gitignore:80` | ✅ |
| `cluster_staging_maxsat/data/mse16/` | 4.9 MB, 104 files | yes — `.gitignore:69` | ✅ |
| `cluster_staging_maxsat/results/EvalMaxSat.ans1` | 32 KB | **no** | ⚠️ open |

The `more_data/` stanza follows the repo's existing `data/generated/**`
convention (`.gitignore:49-56`) — instances out, documentation and manifests in:

```gitignore
more_data/**
!more_data/**/
!more_data/**/*.md
!more_data/**/manifest.jsonl
```

Verified with `git check-ignore -v`: the 856 `.cnf` files, the 15 `more.tgz`
archives and the extensionless `README`s are all excluded, while
`CORPUS_BROADENING_HANDOFF.md` is kept. `git add -A more_data/` now stages
exactly one file, that handoff. `git status` still shows `?? more_data/` because
git collapses the directory around that one untracked file — that is the
handoff, not the corpus.

**The corpus is still reproducible from the repo.** Nothing is lost by ignoring
it: `census_mse16.csv` records all 856 instances structurally, and
`sample_mse16_screen.csv` records the sha256 of every instance any experiment
actually ran against. A re-download can be verified against those hashes.

**Still open:** `EvalMaxSat.ans1` is a pasted solver transcript sitting in a
results directory. It is not a record in the results schema — delete it, or move
it under a run directory if the transcript is worth keeping.

---

## 1. What the corpus actually is

`more_data/` is the **MaxSAT Evaluation 2016 unweighted (`ms`) tracks**, both
halves, with a doubled directory level (`ms_crafted/ms_crafted/…`):

| Group | Files | n vars | m/n | Clause lengths |
|---|---:|---|---|---|
| `abrame-habet/max2sat` | 228 | 120–200 | 6.0–21.7 | 2 |
| `abrame-habet/max3sat` | 144 | 70–110 | 6.4–21.4 | 3 |
| `maxcut/abrame-habet` | 225 | 140–220 | 5.5–18.6 | 2 |
| `bipartite/maxcut-140-630-0.7` | 50 | 140 | 9.0 | 2 |
| `bipartite/maxcut-140-630-0.8` | 50 | 140 | 9.0 | 2 |
| `highgirth/3sat` | 50 | 250–300 | 4.0 | 3 |
| `highgirth/4sat` | 32 | 100–150 | 9.0 | 4 |
| `maxcut/dimacs-mod` | 62 | 28–70 | 1.1–**57.0** | 2 |
| `maxcut/spinglass` | 5 | 27–343 | 6.0 | 1, 2 |
| `set-covering/scpcyc` | 6 | 192–**11,264** | 2.2–3.5 | 1, 4 |
| `set-covering/scpclr` | 4 | 210–715 | 3.4–6.7 | 1, 10, 16, 20, 30, 35, 36, 40, 50, 70, 71, **75** |
| **total** | **856** | | | |

Two structural facts govern everything else:

**Every file is `p cnf`, not `p wcnf`.** This is the MSE unweighted-MaxSAT
convention: no `top`, no hard clauses, every clause soft at weight 1. That is
exactly the "pure soft" case the handoff calls F1–F4/F9 and the reason these are
**drop-in for the current stack with zero code changes**:

- `src/sat/cnf.py:80-82` maps a `p cnf` clause to `weight=1, is_hard=False`.
- `src/cli/run_opt_rc2.py:54` (`cnf_to_all_soft_wcnf`) does the same for RC2.
- Identical convention to the committed `uuf250` corpus, so oracle costs are
  directly comparable and the `hv` fitness cliff at `population.py:161` never
  fires. No repair step, no decoder redesign, no new config id.

**EvalMaxSAT does not accept them.** Fed a `p cnf` file it reads every clause as
hard and returns `s UNSATISFIABLE` in 0.00 s — silently wrong, not an error. It
needs an explicit all-soft WCNF:

```
p wcnf <n> <m> <m+1>
1 <lits> 0
```

That converter is ~15 lines and belongs in the shared `wcnf_writer` module of
handoff Step 2. **This is a live trap**: the failure mode is a clean "UNSAT"
answer, not a crash.

---

## 2. Do you still need your own generators?

Scored against the four axes of handoff §2, plus size:

| Axis | Current tier-2 corpus | `more_data/` | Covered? |
|---|---|---|---|
| **Clause length** | all ternary | 1, 2, 3, 4, and 10–75 (set-covering) | ✅ fully |
| **Density (m/n)** | 4.0 only | 1.1 → 57.0 | ✅ fully |
| **Origin** | one random generator | random 2/3/4-SAT, high-girth, random + bipartite + spinglass + DIMACS-derived MaxCut, set covering | ✅ fully |
| **Instance size** | n = 200–250 | n = 27 → 11,264 | ✅ fully |
| **c\*** | 1 for 24/26 | tens to thousands (§3) | ✅ fully |
| **Weightedness** | all unweighted | **all unweighted** | ❌ **not at all** |

**Answer: you need one generator, not six.**

Five of the six axes are covered better by this corpus than by anything you would
write, and with the credibility advantage that they are a published benchmark
rather than instances you generated for a paper about them. Handoff families
F1 (off-threshold random k-SAT), F2 (Max-2-SAT), F3/F4 (MaxCut, random *and*
structured), F9 (set covering) and part of F8 (`dimacs-mod` is MaxCut on the
DIMACS clique graphs) are all **already on disk**. Do not write those generators.

The gap is **F5, `reweight`** — weightedness. Every file here is weight 1, so the
axis the professor's objection did not even name is the one that stays at zero
variance. It is also the cheapest thing in the whole plan: read a WCNF, draw a
weight per clause, write it back. ~30 lines, and it is the single cleanest
one-axis manipulation available, because the base instance is held byte-identical.

Two smaller residuals, both optional:

- **A size ladder at fixed everything-else.** `highgirth/3sat` is fixed at m/n = 4
  and the abrame-habet families vary n only in coarse steps. If you want n as a
  clean covariate, SATLIB `uuf50…uuf225` (handoff F7) is a download, not a
  generator.
- **Planted-optimum instances for the Step 4 verification harness.** The corpus
  gives you no known-`c*` construction to assert against. But `bipartite/maxcut-*`
  is *almost* one — a bipartite graph has maxcut = |E|, so c\* = 0 — except
  these files are edge-sampled at density 0.7/0.8 from the bipartite graph, so the
  identity does not hold exactly. A 20-line planted-3-SAT generator is still worth
  writing purely as a test fixture.

---

## 3. Which subdirectories yield tier 2 — the screen

This is an empirical question about RC2 wall-clock, so it is a job array, not an
argument. Everything below is built, smoke-tested end to end, and ready to
submit; §3.2 is the partial local preview while it queues.

### 3.1 What was built

| File | |
|---|---|
| `src/bench/make_mse16_manifest.py` | census + stratified sample + staging copy + manifest |
| `cluster_staging_maxsat/scripts/smoke_mse16_array.sbatch` | 5-task self-verifying smoke, cap 20 |
| `cluster_staging_maxsat/scripts/manifest_mse16_smoke.txt` | the 5 smoke instances |
| `cluster_staging_maxsat/scripts/screen_mse16_array.sbatch` | the array driver, cap 900 |
| `cluster_staging_maxsat/scripts/submit_mse16_screen.sh` | derives `--array` from the manifest |
| `cluster_staging_maxsat/scripts/manifest_mse16_screen.txt` | 104 instances, line N == task N |
| `cluster_staging_maxsat/scripts/sample_mse16_screen.csv` | sha256 + structural census per pick |
| `cluster_staging_maxsat/scripts/census_mse16.csv` | census of all 856 |

Staged instances land in `cluster_staging_maxsat/data/mse16/` (4.9 MB, 104
files), which `.gitignore:69` already covers — they reach the cluster by rsync,
not by git, same as every other corpus in this tree.

Run it:

```bash
# workstation — sample, stage, emit manifest
python -m src.bench.make_mse16_manifest --k 5 --run-name screen
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# cluster — smoke first (~1 min), then the screen; submit from scripts/,
# as every array driver in this tree assumes
sbatch scripts/smoke_mse16_array.sbatch
bash   scripts/submit_mse16_screen.sh        # DRY_RUN=1 to inspect first

# workstation — rsync results/profile_mse16/ back, then aggregate
python -m src.bench.analyze_tiers \
    --in-dir  cluster_staging_maxsat/results/profile_mse16 \
    --out-dir results/hardness/mse16_screen
```

`analyze_tiers`'s **"Tier × benchmark dir"** table is the answer to the question
— it cross-tabulates tier against the leaf directory name, which is exactly the
promote/drop decision. `make_tier2_manifest.py` then picks the run up from
`results/hardness/` with no change, because the screen writes the schema it
already globs for.

Three design points worth keeping:

- **`--cap 900`, matching the `uuf250_1000c` run that produced the committed
  tier-2 corpus.** The paper compares RC2 proof times across runs; changing the
  cap silently changes which instances carry an oracle. `assign_tier()` ignores
  `--cap` (`RC2_STATUS.md` §4.6), so a 600–900 s completion is labelled T3 with
  reason `cap misconfigured?` despite carrying a valid optimum —
  `make_tier2_manifest.py`'s `include_solved_t3` path rescues exactly those.
  Do not "fix" this by lowering the cap.
- **The sample is stratified within each leaf directory by clause count**, not
  taken alphabetically. `maxcut/dimacs-mod` alone spans m/n from 1.1 to 57.0;
  the first 5 files by name would have missed that range entirely.
- **`submit_mse16_screen.sh` checks every manifest line resolves before
  submitting.** A missing file means the `data/` rsync has not run — better
  caught at submit than as 104 tasks dying on nodes.

For the fill round, `--only` and `--exclude` make it one command that will not
re-pick what you already screened:

```bash
python -m src.bench.make_mse16_manifest --k 45 --run-name fill \
    --only 'maxcut/dimacs-mod' 'maxcut/spinglass' \
    --exclude cluster_staging_maxsat/scripts/sample_mse16_screen.csv
MANIFEST=manifest_mse16_fill.txt bash scripts/submit_mse16_screen.sh
```

### 3.2 The smoke test

`smoke_mse16_array.sbatch` runs the same code path at a 20 s cap over 5
hand-picked instances. They are deliberately **not** the first 5 manifest lines
— those are all bipartite MaxCut, which all hit the cap and would leave the
`optimal` branch untested. The 5 cover every clause shape in the corpus and both
outcomes `profile_hardness` can produce:

| # | Instance | Shape | Measured |
|---|---|---|---|
| 1 | `c-fat500-1.clq.cnf` | binary, 48 clauses | optimal, 0.002 s, c\* = 2 |
| 2 | `t3pm3-5555.spn.cnf` | units + binary, 162 | optimal, 0.013 s, c\* = 17 |
| 3 | `scpclr10_maxsat.cnf` | clauses up to 126 literals | capped, lb = 13 |
| 4 | `HG-4SAT-V100-C900-14.cnf` | quaternary, 900 | capped, lb = null |
| 5 | `s3v70c700-1.cnf` | ternary, 700 | capped, lb = 8 |

**Three capped tasks is a PASS.** Each task self-verifies and exits non-zero on
a real failure, so `sacct` alone tells you the verdict.

Two things the local run taught, both now baked in:

- The capped tasks come back `subprocess_killed` (outer SIGKILL at cap+grace),
  not `timeout` (the child's graceful SIGALRM). A checker that only knew
  `timeout` would have passed a broken record through.
- **Task 4 returns `cost_lower_bound = null` on a healthy run.** The progress
  file only exists once RC2 has established a bound, and on a 900-clause 4-SAT
  instance it never got there in 20 s. So lb is *reported, not asserted* — how
  far RC2 gets in 20 s is node-speed dependent, and asserting it would make the
  smoke flaky on a slower node. Only tasks 1–2 carry value assertions, because
  only they are machine-independent: milliseconds, and exact optima.
  The signal worth chasing is lb = null on *all three* capped tasks, which is a
  cross-task comparison the header tells you to make.

Verified by fault injection: a profiler error, an `unsat` record (what a
parsed-as-hard-CNF file would produce), a wrong optimum on task 1, task 1
hitting the cap, an empty output file, and duplicate records are each caught;
a correct record passes.

### 3.3 Partial local preview

A local RC2 run over the same 104 at a **300 s** cap (lower than the cluster's
900 s, so it can only under-report) is still going. What has landed:

| Leaf directory | screened | result |
|---|---:|---|
| `bipartite/maxcut-140-630-0.7` | 5/5 | **all T3** at 300 s |
| `bipartite/maxcut-140-630-0.8` | 5/5 | **all T3** at 300 s |
| `maxcut/dimacs-mod` (`c-fat500-1`) | 1 | **T1**, 0.006 s, c\* = 2 |
| `maxcut/dimacs-mod` (`p_hat300-1`) | 1 | **T1**, 22.05 s, c\* = 49 |
| `maxcut/spinglass` (`t3pm3-5555`) | 1 | **T1**, 0.01 s, c\* = 17 |

Early read, to be confirmed by the array: the **crafted small-n families
(`dimacs-mod`, `spinglass`) are the promising ones** — they sit in T1 with c\*
in the tens rather than 1, which is precisely the spread the corpus is being
broadened for. The **large random families are likely to be mostly T3**, and a
T3 instance carries no oracle, so it cannot enter a tier-2 arm at all. Expect
the screen to promote fewer directories than it drops. That is a useful result,
not a failed one — it tells you where to spend the fill budget.

**Cost semantics check, passed.** RC2 and EvalMaxSAT agree exactly on c\* for
all three instances run under both (4, 17, 49), so these files use the
unsatisfied-count convention the EA and the oracle table already assume. This is
the handoff Step 4 trap; on this corpus it is clear.

---

## 4. How to sample

### 4.1 The screening design (what was run here)

5 per leaf subdirectory, stratified within each by clause count so the sample
spans the density range present rather than clustering at one end — 104 instances
over 21 leaf directories. Implemented in `src/bench/make_mse16_manifest.py`
(§3.1), which also emits the full 856-instance census as
`census_mse16.csv` so the sampling frame is on record, not just the sample.

This is the right shape for a screen. It is **not** the right size for the final
corpus — see §5.

### 4.2 Screen with RC2, not with EvalMaxSAT

The obvious shortcut is to screen with the fast C++ solver and certify only the
survivors with RC2. **Measured, that shortcut does not work on this corpus:**

| Instance | c\* | EvalMaxSAT | RC2 (PySAT, Python) |
|---|---:|---:|---:|
| `c-fat200-1.clq.cnf` | 4 | 1.33 s | **0.00 s** |
| `t3pm3-5555.spn.cnf` | 17 | 6.83 s | **0.01 s** |
| `p_hat300-1.clq.cnf` | 49 | 31.34 s | **22.05 s** |

RC2 is *faster* than EvalMaxSAT on all three. The handoff's §5 premise — that RC2
is the bottleneck and EvalMaxSAT is the drop-in speedup — was formed on the
134k-clause judgment-aggregation instances, where it is true. On small-n,
high-density crafted MaxCut it is false: EvalMaxSAT pays fixed startup and
CaDiCaL setup cost that RC2's pure-Python OLL loop does not, and neither solver
dominates. An EvalMaxSAT screen would have discarded instances RC2 tiers as T1.

Two consequences:

1. **Screen with the oracle you will report.** Tier is defined by RC2 wall-clock
   (`profile_hardness.py:68-70`), so tier must be measured with RC2.
2. The EvalMaxSAT migration is still worth doing, but the case for it is
   *instance-dependent*, and this corpus is a counterexample to the general claim.
   Handoff §5's "do not mix solvers in one reported table" stands and now has
   teeth: the two solvers do not even rank instances the same way.

### 4.3 Two cautions that survive the automation

The mechanics are in §3.1. These two are judgement calls the scripts cannot make
for you:

- **Re-verify tier per instance, never inherit it from a directory.** `00000293`
  needed >1300 s while sitting in a T2 manifest. Within a single leaf directory
  here, RC2 time already spans orders of magnitude — `dimacs-mod` alone gave
  0.006 s and 22.05 s on the two members measured so far, off a clause count
  spanning 48 to 3,710. A directory that
  "yields tier 2" yields it for *some* of its members; the manifest generator
  samples, `profile_hardness` decides.
- **`--k` is per leaf directory, so total array size scales with breadth, not
  depth.** At `--k 45` over 21 directories that is 945 tasks. Prefer `--only` to
  fill the two or three directories the screen promotes over raising `--k`
  globally — §5.3, and the breadth-beats-depth argument in §5.

---

## 5. What "enough variety" means

Two different quantities, and conflating them is what produced the current
problem.

### 5.1 Spread — the thing the objection is actually about

Range restriction attenuates a correlation by the ratio of restricted to
unrestricted predictor SD. The current corpus has c\* ∈ {1, 2} with 24/26 at 1,
so the predictor is very nearly a constant and ρ ≈ 0 is arithmetically forced.
More instances of the same kind do not fix this — **only spread does**.

Concrete targets, per axis, for the pooled corpus:

| Axis | Target | Rationale |
|---|---|---|
| c\* | spans ≥ 3 orders of magnitude, with ≥ 15 instances per decade | this is the binding restriction; anything less and the regression in handoff §2 has no leverage |
| m/n | ≥ 4 distinct values, ≥ 2× apart | enough to separate density from c\* rather than confound them |
| clause length | ≥ 3 of {2, 3, 4, long} | binary vs ternary changes RC2's core structure |
| origin | ≥ 3 families, ≥ 1 non-random | "structured" must not be a single family |
| weightedness | ≥ 1 weighted/unweighted matched pair per base family | the only axis needing new code |

The corpus in §1 clears every row but the last.

### 5.2 Count — the thing that sets the error bars

Spread makes the estimate unbiased; count makes it precise. Fisher-z, α = 0.05:

| Question you want to answer | n needed |
|---|---:|
| detect ρ = 0.5 at 80% power | 30 |
| detect ρ = 0.4 at 80% power | 47 |
| detect ρ = 0.3 at 80% power | 85 |
| **claim a null: 95% CI excludes \|ρ\| > 0.3** | **44** |
| claim a null: 95% CI excludes \|ρ\| > 0.25 | 62 |
| claim a null: 95% CI excludes \|ρ\| > 0.2 | 97 |

The paper's claim is the fourth row — an orthogonality claim is a null claim, and
a null claim needs a confidence interval, not a p-value. **≈ 45 instances per
stratum you want to report a within-stratum ρ for, and ≈ 100 pooled** if the
headline is "no relationship anywhere".

Note what this says about the current corpus: n = 26 is not the fatal problem —
26 would support a CI excluding |ρ| > 0.4, which is a publishable statement. The
fatal problem is the spread. The professor is right about the mechanism, and §4
of the draft defends the wrong flank.

### 5.3 The staged plan this implies

1. **Screen** — 5 per leaf directory (done, §3).
2. **Promote** any leaf directory with ≥ 3/5 in T1–T2b. Drop the rest; a directory
   RC2 cannot certify yields no oracle, so it cannot enter a tier-2 arm at all.
3. **Fill** each promoted directory to ~45 instances if it is a stratum you will
   report separately, or to whatever keeps the pooled corpus ≥ 100 and roughly
   balanced across families if you will only report pooled + a covariate model.
4. **Re-verify tier per instance** at fill time (§4.3).
5. **Pair with weighted variants** via `reweight` once it exists, and re-certify
   c\* — reweighting does not preserve it.

**Do not sample all 856.** Beyond ~150 total the marginal instance buys almost no
CI width (the 1/√n floor) while every one costs a full RC2 certification plus
3 configs × 5 seeds of memetic runs. Breadth across families is worth far more
per solver-hour than depth within one.

---

## 6. Carried forward

- **`reweight` (F5) is the only generator worth writing.** Everything else in
  handoff Step 3 is superseded by files already on disk.
- **The all-soft WCNF converter must live in the shared writer** (handoff Step 2),
  with a test asserting EvalMaxSAT does not return UNSAT on a satisfiable
  all-soft instance. The silent-wrong-answer failure mode justifies the assertion.
- **Cost semantics still need the Step 4 assertion.** These files are MaxSAT-native
  (cost = unsatisfied clause count), so they match the EA/RC2 convention as-is —
  but MaxCut-as-CNF naturally counts *cut* edges, and if a future generator emits
  that convention it inverts every comparison silently. The trap the handoff flags
  is real; the instances here happen to sit on the safe side of it.
- **Two directory levels are doubled** (`more_data/ms_crafted/ms_crafted/…`),
  presumably an unpacking artifact. Harmless, but flatten before writing manifest
  paths or the family field gets ugly.
- **Four leaf directories are too small to carry a stratum of 45** and are capped
  by the corpus, not by your budget: `spinglass` (5 files), `set-covering/scpclr`
  (4), `set-covering/scpcyc` (6), `highgirth/4sat` (32). `spinglass` is in fact
  *exhausted by the screen itself* — all 5 files are in the k=5 sample, so a fill
  round with `--exclude` correctly returns nothing for it. These directories buy
  origin variety cheaply and must then be pooled, or reported as a family-level
  observation rather than a stratum with its own ρ.

---

## 7. Inventory — new and changed files

Everything this work touched, and what is deliberately absent. Nothing has been
committed; this is the state of the working tree.

### 7.1 New — committed

| Path | Lines | What |
|---|---:|---|
| `src/bench/make_mse16_manifest.py` | 243 | census + stratified sample + staging copy + manifest; `--k`, `--only`, `--exclude`, `--no-stage` |
| `cluster_staging_maxsat/scripts/screen_mse16_array.sbatch` | 46 | the screen array driver, cap 900 |
| `cluster_staging_maxsat/scripts/smoke_mse16_array.sbatch` | 135 | 5-task self-verifying smoke, cap 20 |
| `cluster_staging_maxsat/scripts/submit_mse16_screen.sh` | 99 | derives `--array` from the manifest, pre-checks staging |
| `cluster_staging_maxsat/scripts/manifest_mse16_screen.txt` | 104 | screen instances; line N == array task N |
| `cluster_staging_maxsat/scripts/manifest_mse16_smoke.txt` | 5 | smoke instances; line N == array task N |
| `cluster_staging_maxsat/scripts/sample_mse16_screen.csv` | 105 | provenance: sha256 + structural census per pick |
| `cluster_staging_maxsat/scripts/census_mse16.csv` | 857 | structural census of all 856 corpus instances |
| `docs/CORPUS_MSE2016_ASSESSMENT.md` | 531 | this document |

The two CSVs and the two manifests are **generated** by
`make_mse16_manifest.py` and regenerate byte-identically (verified). They are
committed anyway, deliberately: they are the record of which instances an
experiment ran against, and the corpus they index is not in the repo.

### 7.2 Changed

| Path | Change |
|---|---|
| `.gitignore` | +14 lines: the `more_data/**` stanza (§0). The `solver_EvalMaxSat/` line above it was already in the working tree, not from this work. |
| `cluster_staging_maxsat/readme.txt` | +42 lines: an "MSE-2016 corpus screen" section between the RC2-profiling and tier-2-memetic blocks, listing the new scripts, the submit/aggregate commands, and the smoke's pass criteria |

### 7.3 New — deliberately not committed

| Path | Files | Why |
|---|---:|---|
| `cluster_staging_maxsat/data/mse16/` | 104 (4.9 MB) | the staged screen instances. Covered by `.gitignore:69` (`cluster_staging_maxsat/data/`), like every other corpus in this tree — they reach the cluster by rsync. Reconstructible from `more_data/` + `sample_mse16_screen.csv`, whose sha256s verify them. |
| `more_data/` instances | 856 (32 MB) | now covered by the new `.gitignore` stanza; only `CORPUS_BROADENING_HANDOFF.md` remains committable |

### 7.4 Created at run time, not now

The first three do not exist yet; each is `mkdir -p`'d by the step that writes
it. The fourth already exists and is shared with the tree's other arrays.

| Path | Written by | State |
|---|---|---|
| `cluster_staging_maxsat/results/profile_mse16/` | `screen_mse16_array.sbatch`, one `mse16_arr_task_N.jsonl` per task | new |
| `cluster_staging_maxsat/results/profile_mse16_smoke/` | `smoke_mse16_array.sbatch`, one `mse16_smoke_task_N.jsonl` per task | new |
| `results/hardness/mse16_screen/` | `analyze_tiers` on the workstation, after rsyncing the above back | new |
| `cluster_staging_maxsat/scripts/logs/` | SLURM | **already exists**, 700 files from previous runs; the new jobs add `mse16-screen-*` and `mse16-smoke-*` alongside them |

Note `cluster_staging_maxsat/results/` is **not** gitignored, so the per-task
JSONL will show up as untracked once the array runs. That matches how
`results/profile_uuf250/` and the other completed runs are handled in this tree.

### 7.5 `EvalMaxSat.ans1` — committed, and not what it looked like

An earlier revision of this document called this a stray transcript to delete.
That was wrong. It is a raw terminal paste, but it holds two completed
EvalMaxSAT runs on the judgment-aggregation instances, and one of them is a
result the repo does not have anywhere else:

| Instance | RC2 | EvalMaxSAT |
|---|---|---|
| `…preflib-00049-00000293.wcnf` | optimal, 1313.8 s, cost 43 (`mse_cap1800`) | 895.9 s, `o 43` |
| `…preflib-00049-00000253.wcnf` | **never solved** — `subprocess_killed` at cap 600 *and* at cap 1800, T3, no oracle | 1605.2 s, `o 46` |

So it does two things. It **independently confirms the cost-43 oracle** that
[`TIER2_MSE_FEASIBILITY.md`](TIER2_MSE_FEASIBILITY.md) §0 rests on — a
second solver, a different algorithm family, same optimum. And it **supplies an
optimum for `00000253`, which RC2 could not certify at any cap tried**, turning
it from an instance with no oracle into one with a usable reference.

Three caveats before that oracle is used anywhere:

- **It is an EvalMaxSAT optimum, not an RC2 one.** Handoff §5's "do not mix
  solvers within a single reported table" applies directly: `o 46` cannot go
  into a column of RC2 proof times, and any table using it must name the solver.
- **The two proof times are not comparable to the committed ones.** They were
  measured on the workstation, unlike the cluster runs in `results/hardness/`.
- **It is a terminal paste, not a record in the results schema.** It has no
  sha256, no solver commit, no structured fields. Promoting it into
  `results/hardness/` would need the subprocess runner from handoff §5, which
  emits the existing JSONL schema plus `solver` and `solver_commit`.

It is committed as-is rather than reformatted, because the paste is the
primary evidence and rewriting it by hand would lose that.

### 7.6 What was NOT changed

No solver, EA or profiler code was modified. In particular `src/sat/cnf.py`,
`src/cli/profile_hardness.py`, `src/cli/run_opt_rc2.py` and everything under
`src/evo/` are untouched — the corpus is drop-in (§1), so the screen is new
scripts around existing code, not a change to it. `cluster_staging_maxsat/src/`
is likewise untouched, so the divergence recorded in
[`DIVERGENCE.md`](../cluster_staging_maxsat/DIVERGENCE.md) is unaffected and
needs no new entry.
