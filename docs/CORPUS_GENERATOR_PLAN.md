# Broadening the corpus with generators — why MSE-2016 does not fit a core-guided oracle, and the steps to a generated corpus

**Date:** 2026-09-14. Written against commit `3e79701`. Supersedes the
"you need one generator, not six" verdict of
[`archive/CORPUS_MSE2016_ASSESSMENT.md`](archive/CORPUS_MSE2016_ASSESSMENT.md) §2, for the
reason in §1 below. Builds on [`archive/INSTANCEGEN_PLAN.md`](archive/INSTANCEGEN_PLAN.md)
(the generator that already exists) and
[`more_data/CORPUS_BROADENING_HANDOFF.md`](../more_data/CORPUS_BROADENING_HANDOFF.md)
(the four axes and the family list).

Every number in §1–§2 was measured on this workstation today; the pilot rows
are in `results/profile/gen_pilot_cap60.jsonl` (25 rows, RC2 = PySAT
1.9.dev15, cap 60 s). Nothing in §3 onward has been run.

---

## 0. The decision in one paragraph

The MSE-2016 `ms_random` / `ms_crafted` corpus in `more_data/` is not the
broadened corpus. Every instance tried under either exact oracle has either
timed out or landed in T3, except a handful of small crafted MaxCut files.
The reason is structural, not a cap-tuning problem: those families carry
c\* in the hundreds to thousands, and a core-guided (OLL) solver — RC2 and
EvalMaxSAT both — needs roughly one unsatisfiable-core extraction per unit
of cost. The corpus therefore has to be **generated** at parameters chosen
for what RC2 can certify in ≤ 900 s, with c\* stratified across the range RC2
can actually reach. The pilot shows that range is about **1 → 10 for random
3-SAT** and **tens for binary-clause families** (Max-2-SAT, MaxCut), and
that the binary-clause families and the small crafted MSE leaves are where
the c\* spread comes from. The plan is seven steps (§4); the code to write
is three small generator modules plus a verification harness and a
calibration CLI on top of the `instancegen/` package that already ships.

---

## 1. Why MSE-2016 does not work here — the evidence, and one correction

### 1.1 What was measured

| Source | Instances | Oracle | Cap | Outcome |
|---|---:|---|---:|---|
| `results/oracle_more_data.jsonl` | 12 (`scpclr`, `scpcyc`, `max2sat/120v`) | EvalMaxSAT | 60 / 120 / **1800** s | **12/12 timeout**, incl. `scpclr10` at 1800 s |
| `archive/CORPUS_MSE2016_ASSESSMENT.md` §3.3 | 10 (`bipartite/maxcut-140-630-*`) | RC2 | 300 s | **10/10 T3** |
| `archive/CORPUS_MSE2016_ASSESSMENT.md` §3.3 | 3 (`dimacs-mod`, `spinglass`) | RC2 | 300 s | **3/3 T1**, c\* = 2, 17, 49 |
| `results/hardness/mse23_full` | 75 (MSE-2023 uw-small) | RC2 | 600 s | 74/75 T3 |

The uuf250 corpus that produced the committed tier-2 results is the
comparison point: m/n = 4.26, c\* = 1 for 24/26, and RC2 takes 35–500 s
*for that one core*. The MSE-2016 random families sit at m/n = 6–22 with
n = 120–200. Reading off the pilot in §2, that puts them at c\* in the
hundreds, far beyond anything RC2 finishes.

### 1.2 One correction to the premise

These are **not** anytime-track instances. MSE-2016 had no incomplete track
(it started in 2017); `ms_random` and `ms_crafted` were the *complete*,
unweighted track, 30-minute cap, and were solved there — by branch-and-bound
solvers (ahmaxsat, MaxSatz family), which is the algorithm class that wins
random and small crafted MaxSAT. Core-guided solvers are the wrong tool for
high-density random MaxSAT, and RC2 and EvalMaxSAT are both core-guided.

So the accurate statement is: **too hard for the OLL oracle this paper
uses**, not too hard for exact solvers in general. The practical conclusion
is the same as yours — do not build the corpus on them — but the phrasing
matters in the paper: a referee who knows these instances will know they
have published optima.

It also rules out one tempting shortcut: certifying c\* with a
branch-and-bound solver and keeping RC2 for tiering. c\* would be correct,
but the instance would still be T3 under RC2, i.e. censored on the
proof-time axis, and the orthogonality analysis is *about* RC2 proof time.
Handoff §5's "do not mix solvers in one table" applies.

### 1.3 What survives from `more_data/`

The crafted small-n leaves — `maxcut/dimacs-mod` (62 files, n = 28–70),
`maxcut/spinglass` (5) — gave T1 with c\* = 2–49 on every member measured.
Keep them as the **structured-origin stratum**: they are the only
non-generated, published-benchmark structured instances the stack can
certify, and they cost nothing. Their screen (`screen_mse16_array.sbatch`,
104 tasks) is still worth running, restricted with `--only` to those two
leaves plus `set-covering/*` for the clause-length axis; drop the
`bipartite/*`, `abrame-habet/*` and `highgirth/*` leaves from the array
entirely — they are the m/n ≥ 6 families and will be T3 throughout.

---

## 2. The pilot — what the generator dial actually does under RC2

Pure-soft (`hard_ratio = 0`, `w_max = 1`) random k-SAT from
`instancegen.generate`, seed 1 unless noted, RC2 via
`src.cli.profile_hardness`, cap 60 s. `T3` means killed at cap + grace.

**3-SAT, n × ratio:**

| n \ m/n | 5 | 6 | 8 | 10 | 14 |
|---:|---|---|---|---|---|
| **50** | c\*=1, 0.0 s | c\*=6, 2.8 s | c\*=10, 52.9 s | T3 | T3 |
| **70** | c\*=2, 0.1 s | c\*=5, 4.5 s | T3 | T3 | T3 |
| **100** | c\*=3, 7.3 s / **T3** (seed 2) | T3, T3 | T3, T3 | — | — |
| **150** | c\*=1, 1.5 s / **T3** (seed 2) | T3, T3 | — | — | — |
| **200** | T3, T3 | — | — | — | — |

**2-SAT, n = 100:**

| m/n | 4 | 6 | 10 |
|---:|---|---|---|
| | **c\*=25, 5.5 s** | T3 | T3 |

Four things follow, and they reshape the handoff's family plan:

1. **The cliff is at c\* ≈ 10 for random 3-SAT.** At n = 50, c\* = 6 costs
   3 s and c\* = 10 costs 53 s; nothing with c\* > 10 finished. This is the
   OLL mechanism — each unit of cost is another core, and cores on random
   3-SAT are large — and a 900 s cap will move the cliff to perhaps c\* ≈ 15–20,
   not to 100. Handoff F1's "ratios 5, 6, 8 at n = 100–200 put c\* in the
   tens" is **wrong for RC2**: at n ≥ 100 ratio 6 is already T3.
2. **Seed variance at fixed parameters is enormous** (n = 100, m/n = 5: 7 s
   vs > 60 s; n = 150 likewise). `INSTANCEGEN_PLAN` D9 — tier is a property
   of the instance, a parameter point has a *yield* — is confirmed, and the
   calibration must be per-instance.
3. **Binary clauses buy an order of magnitude of c\* for free.** Max-2-SAT
   at n = 100, m/n = 4 gives c\* = 25 in 5.5 s; the crafted MaxCut
   `p_hat300-1` (n = 300) gives c\* = 49 in 22 s. Cores over binary clauses
   are small, so OLL scales with c\* far more gently. **The c\* spread the
   assessment asked for comes from the clause-length-2 families, not from
   3-SAT.** This is also why handoff F2/F3 (Max-2-SAT, MaxCut) are not
   optional — they are the only generated families that populate the
   c\* ≥ 20 decade.
4. **The reachable c\* range is ~1 → ~100, two decades, not three.**
   `CORPUS_MSE2016_ASSESSMENT` §5.1's target of "≥ 3 orders of magnitude" is
   not attainable with a core-guided oracle at any n; revise to **≥ 2
   decades with ≥ 15 instances per decade**, and say so in the paper's
   limitations rather than pretend to the third decade.

The tables above are one seed per cell at a 60 s cap; they locate the cliff,
they do not measure yields. That is Step 3.

---

## 3. Corpus design

### 3.1 Families and what each one moves

| Family | Generator | Status | Moves | RC2-reachable c\* (pilot) |
|---|---|---|---|---|
| **G1** off-threshold random 3-SAT, pure soft | `instancegen.generate`, k=3, `hard_ratio=0` | **exists** | density, c\* (1–10), n | 1–10 |
| **G2** random Max-2-SAT | `instancegen.generate`, k=2 | **exists** (same code path) | clause length, c\* (tens) | 25 @ n=100 m/n=4 |
| **G3** MaxCut, Erdős–Rényi | `instancegen/maxcut.py` (new) | to write | clause length, origin (graph), c\* | expect tens–100 (cf. `p_hat300-1`) |
| **G4** MaxCut, torus lattice | same module, `topology=torus` | to write | designed structure, decouples n from density | unknown — calibrate |
| **G5** reweight of any of the above | `instancegen/reweight.py` (new) | to write | **weightedness**, in isolation, base held byte-identical | re-certify; c\* not preserved |
| **G6** planted-optimum fixtures | `instancegen/planted.py` (new) | to write | nothing — test fixtures only | c\* = 0 by construction |
| **S1** MSE-2016 `dimacs-mod` + `spinglass` | download, already on disk | exists | non-generated structured origin | 2–49 measured |

Not in this plan, and why: F8 Max-Clique and F9 set covering need hard
clauses or pseudo-hard weights and hit the feasibility wall
(handoff §6a); F10/F11 need downloads the sandbox cannot fetch and are
judgement-call additions after the generated corpus is in hand;
`hard_ratio > 0` instances from `instancegen` are supported by the code but
excluded from this corpus for the same feasibility-wall reason — the EA
under test is the pure-soft `memetic_deeppolish`, and every committed tier-2
number is pure-soft.

### 3.2 The factorial that makes effects attributable

Handoff §2: vary one axis at a time from a fixed base, so the regression has
leverage on each covariate separately.

| Stratum | Family | n | m/n | Weights | Purpose |
|---|---|---|---|---|---|
| A | G1 3-SAT | 50, 70 | 5, 6, 7, 8 | 1 | density → c\* at fixed origin, clause length 3 |
| B | G1 3-SAT | 50 … 250 | 4.26 | 1 | n ladder at fixed density (joins the uuf250 stratum at n = 250) |
| C | G2 2-SAT | 100, 150 | 3, 4, 5 | 1 | clause length 2 at random origin |
| D | G3 MaxCut ER | 60–150 vertices | degree 4–8 | 1 | graph origin, clause length 2 |
| E | G4 MaxCut torus | 8×8 … 12×12 | 4 (fixed) | 1 | designed structure |
| F | G5 reweight of A/C/D picks | as base | as base | uniform 1–8, few_classes:5 | weightedness, paired with its unweighted base |
| S1 | `dimacs-mod`, `spinglass` | 27–70 | 1.1–57 | 1 | published structured benchmark |

The base point is stratum B at n = 250 — the committed tier-2 corpus —
so every other stratum is "the uuf250 corpus with one thing changed".
Stratum F is the only one with new code that touches weights, and it is
paired: each weighted instance has an unweighted twin with identical
clauses, which is the single cleanest manipulation available
(`CORPUS_MSE2016_ASSESSMENT` §2).

### 3.3 Targets

From `CORPUS_MSE2016_ASSESSMENT` §5, with row 1 revised per §2.4 above:

| Axis | Target |
|---|---|
| c\* | spans ≥ 2 decades (1–9, 10–99, and whatever reaches ≥ 100), ≥ 15 certified instances per decade |
| m/n | ≥ 4 distinct values ≥ 1.5× apart |
| clause length | 2 and 3 (from generators) plus 1/long from S1 set-covering if the screen certifies any |
| origin | random k-SAT, random graph, lattice, published crafted — 4 families, 2 non-random |
| weightedness | ≥ 20 weighted/unweighted matched pairs |
| count | ≥ 100 certified (T1–T2b) pooled; ≈ 45 in any stratum that gets its own ρ |

All certified instances are T1–T2b under RC2 at cap 900. T3 rows are kept
in the manifest (yield accounting, D9) but cannot enter a tier-2 arm.

---

## 4. Steps

Each step names its deliverable, the file(s) it touches, and its
pass criterion. Steps 1–2 are workstation code; 3 and 5 are cluster arrays;
4 and 6 are workstation scripts over cluster results.

### Step 0 — Format and manifest are already frozen. Do not reopen.

- WCNF dialect: `instancegen.wcnf_io.write_wcnf(..., dialect="old")`
  (`p wcnf n m top`, softs first). `INSTANCEGEN_PLAN` D1. Every new
  generator writes through this function — no second serializer.
- Instance identity: sha256 of the file bytes, as `oracle_evalmaxsat.py`
  and `make_mse16_manifest.py` already compute it.
- Manifest row: `INSTANCEGEN_PLAN` §10.3 — `generator.{name,version,params}`,
  `sizes`, `profile`, `tier`, `tier_rule`, `ea` (null-filled),
  `instance_sha256`, `git_sha`, `created_utc`. One row per instance, written
  at generation time, extended (not rewritten) at certification time.
- Filenames carry every parameter (`instance_filename` pattern), so the
  corpus is reproducible from the manifest with no instance files in git
  (`.gitignore:54-56`, D6).

Pass: nothing to run. The point of the step is that Steps 1–2 add generators
*behind* this interface rather than beside it.

### Step 1 — Three generator modules (workstation, ~1 day)

All three follow the `generate.py` contract: pure, one `random.Random(seed)`
threaded explicitly, frozen params dataclass, returns `Instance`, no I/O.

**1a. `instancegen/maxcut.py`**

```python
@dataclass(frozen=True)
class MaxCutParams:
    topology: str        # "er" | "torus" | "complete" | "bipartite"
    n_vertices: int      # torus: side length, n = side**2
    degree: float        # er only: expected degree, p = degree/(n-1)
    seed: int

def generate_maxcut(p: MaxCutParams) -> Instance
```

Encoding (handoff F3): per edge (u, v) two soft unit-weight clauses
`(x_u ∨ x_v)` and `(¬x_u ∨ ¬x_v)`. Both satisfied iff the edge is cut, so
**cost = uncut edges and c\* = |E| − maxcut**. This is the unsatisfied-count
convention the EA and RC2 already use; assert it in Step 2, do not assume
it. `complete` and `bipartite` exist only for the known-optimum tests.
Filename: `maxcut_<topology>_v<n>_d<degree>_s<seed>.wcnf`.

**1b. `instancegen/reweight.py`**

```python
@dataclass(frozen=True)
class ReweightParams:
    base_sha256: str     # the unweighted instance this derives from
    weight_dist: str     # reuse generate.py's "uniform" | "few_classes:m" | "powerlaw:a"
    w_max: int
    seed: int

def reweight(base: Instance, p: ReweightParams) -> Instance
```

Reads a WCNF (through `maxsat_new.cnf.parse_dimacs`, the parser the EA
uses), draws one weight per soft clause via `generate._make_weight_sampler`,
leaves the clause set and order byte-identical. The manifest row records
`base_sha256` and `c_star_preserved: false` — reweighting changes the
optimum and the instance must be re-certified (handoff Step 3.4).
Filename: `<base-stem>_rw_w<w_max>_<dist-slug>_s<seed>.wcnf`.

**1c. `instancegen/planted.py`** — 20 lines. Random k-SAT where every clause
is checked against a planted assignment and resampled if it would be
falsified. c\* = 0 by construction. Used only by Step 2; never enters the
corpus (planted instances are easier at matched parameters, D8).

**1d. `instancegen/cli.py`** — `python -m instancegen.cli generate
--family {ksat,maxcut,reweight} --params ... --seeds a-b --out
data/generated/<batch>/`. Writes the instances and appends manifest rows.
One entry point so Step 5's bulk run is one command per stratum.

Tests, mirroring `INSTANCEGEN_PLAN` §12: determinism (byte-identical on
re-run, differs across seeds) for each new family; round-trip through
`maxsat_new.cnf`; reweight preserves clause list exactly; no emitted line
starts with `0` or `%`.

Pass: `python -m pytest instancegen -q` green (currently 62 tests).

### Step 2 — Verification harness (workstation, half a day)

`instancegen/verify.py`, run over any `data/generated/<batch>/`:

| Check | Asserts |
|---|---|
| round-trip | parsed formula equals in-memory formula clause-for-clause |
| identity | manifest `instance_sha256` == sha256 of the file |
| **cost semantics** | RC2 on `maxcut/bipartite` returns 0; on `maxcut/complete` K_n returns `|E| − ⌊n²/4⌋`; on `planted` k-SAT returns 0 |
| oracle agreement | for a 5-instance sample, RC2 `final_cost` == EvalMaxSAT `opt_cost` (via `oracle_evalmaxsat.py`) |
| EA convention | `maxsat_new.cnf.eval_assignment` on RC2's model gives the same cost RC2 reported |

The third row is the trap the handoff calls high-priority: a MaxCut encoder
that thinks in *cut* edges inverts every comparison silently. It is an
assertion, not a comment.

Pass: `python -m instancegen.verify data/generated/fixtures` exits 0.

### Step 3 — Calibration, two phases

**Phase A — workstation, cap 120 s, 1 seed per cell, ~2 h.** Extend the
pilot grid of §2 to every family in §3.1:

- G1: n ∈ {50, 70, 100}, m/n ∈ {5, 5.5, 6, 7, 8}
- G2: n ∈ {100, 150, 200}, m/n ∈ {3, 4, 5, 6}
- G3: n ∈ {60, 100, 150}, degree ∈ {4, 6, 8}
- G4: side ∈ {8, 10, 12}
- G5: three of the above bases × {uniform w8, few_classes:5 w16}

Output: `results/profile/gen_calib_a.jsonl` and a table
`(family, params) → solve_s, c*, tier`. Purpose is to find, per family, the
band where solve time climbs from seconds toward the cap — the T2 band is
roughly 5–20× inward of the 120 s cliff. `profile_hardness --cap 120` is the
tool; it already handles the SIGALRM-swallowing problem.

**Phase B — cluster, cap 900, 8 seeds per surviving cell.** Cap 900
because that is the cap the committed tier-2 corpus was certified at
(`uuf250_1000c`); changing it changes which instances carry an oracle
(`CORPUS_MSE2016_ASSESSMENT` §3.1). Roughly 12 cells × 8 seeds × 5
families ≈ 480 tasks, worst case 480 × 900 s = 120 CPU-h, realistically a
third of that since T1 rows finish early.

Mechanics reuse the MSE-16 screen exactly:

```bash
# workstation
python -m instancegen.cli generate ... --out data/generated/calib_b/      # per stratum
rsync data/generated/calib_b/ cluster_staging_maxsat/data/generated/calib_b/
python -m src.bench.make_mse16_manifest ...   # or a 20-line sibling that lists data/generated/calib_b/*.wcnf
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/
# cluster
MANIFEST=manifest_gen_calib_b.txt bash scripts/submit_mse16_screen.sh
# workstation, after rsync back
python -m src.bench.analyze_tiers --in-dir cluster_staging_maxsat/results/profile_gen_calib_b \
    --out-dir results/hardness/gen_calib_b
```

`screen_mse16_array.sbatch` takes any manifest; only the output directory
name needs parameterising (one `OUTDIR` env var, same pattern as
`oracle_evalmaxsat_array.sbatch`).

Pass: `results/hardness/gen_calib_b/tier_summary.csv` exists and a per-cell
**T2 yield table** (fraction of seeds in T1–T2b, median `solve_s`, c\* range)
is written to `docs/` — this is the artefact that decides Step 5's grid.

### Step 4 — Select cells (workstation, an hour)

From the yield table, pick per stratum the cells that satisfy all of:

- yield of certified (T1–T2b) seeds ≥ 60 %, so the bulk run does not waste
  most of its budget on T3;
- median `solve_s` ≥ 10 s — instances RC2 finishes instantly carry no
  proof-time information and would re-create the c\* = 1 degeneracy from
  the other side;
- together, c\* covers both decades with ≥ 15 per decade (§3.3).

Write the chosen cells to `instancegen/grids/corpus_v1.yaml` so Step 5 is
driven from a committed file, not from a shell history.

### Step 5 — Bulk generation, certification, reweight pairs (cluster)

1. Generate `data/generated/corpus_v1/` from the grid — 20 seeds per cell,
   which at a 60 % yield gives ≈ 12 certified per cell.
2. Certify every instance with RC2 at cap 900 on the cluster (same array
   as Phase B). **Per instance, never inherited from the cell** — the seed
   variance in §2.2 is the reason.
3. Take the certified T1–T2b picks from strata A, C, D, and produce their
   G5 twins; certify the twins in a second, smaller array. Both members of
   a pair go in the manifest with a shared `pair_id`.
4. Run `instancegen.verify` over the whole batch.
5. Commit: `data/generated/corpus_v1/manifest.jsonl`,
   `results/hardness/gen_corpus_v1/`, the grid YAML. Instances stay out of
   git (D6) — they regenerate byte-identically from the manifest.

Pass: the corpus summary table of §3.3, one row per axis, with every target
met — this is "the artefact that answers the professor" (handoff Step 6).

### Step 6 — Feed the tier-2 pipeline (no new code)

`make_tier2_manifest.py` globs `results/hardness/*/all_results.jsonl` and
resolves instance names under `cluster_staging_maxsat/data/**`, so once
Step 5's results and instances are in place the memetic arms run through
the existing machinery:

```bash
python -m src.bench.make_tier2_manifest --hardness-dir results/hardness \
    --data-root cluster_staging_maxsat --prefix t2g
# then the existing tier2 memetic array, 3 configs × 5 seeds
```

Two things to watch. `include_solved_t3` must stay on — a 600–900 s
completion is labelled T3 with reason `cap misconfigured?` but carries a
valid optimum (`RC2_STATUS` §4.6). And the weighted twins need the EA's
fitness to use the weights: `maxsat_new.cnf.eval_assignment` sums
`cl.weight` over satisfied softs and the EA takes
`best_cost = total_soft_weight − satisfied` (`PORT_NOTES` §8), so weights
are honoured — but confirm on one pair before submitting 390 tasks.

Budget: ≈ 120 certified instances × 3 configs × 5 seeds × 900 s
≈ 450 CPU-h, same order as the original tier-2 run.

### Step 7 — Analysis

Not a single bivariate ρ. Regress log RC2 proof time on log c\*, m/n, n,
clause length and a family indicator; ask whether the *residual* predicts
EA time-to-target. Report ρ within each stratum (n ≈ 45 where a stratum has
it) and pooled, with Fisher-z CIs — the claim is a null, so the CI is the
result. The weighted/unweighted pairs give a paired test on the
weightedness axis specifically.

---

## 5. Decisions needed before Step 3

| # | Question | Recommendation |
|---|---|---|
| E1 | Cap for certification | **900 s**, matching `uuf250_1000c`; not 600 (the `mse23` cap) and not 1800 |
| E2 | Accept the two-decade c\* ceiling | **Yes**; state it as a limitation of a core-guided oracle rather than chase the third decade with a B&B solver (§1.2) |
| E3 | Include `hard_ratio > 0` instances | **No** for corpus v1 — feasibility wall, and the EA arm under test is pure-soft |
| E4 | Which S1 leaves to keep screening | `dimacs-mod`, `spinglass`, `set-covering/*` only; drop the rest of the 104-task array |
| E5 | Weight distributions for G5 | `uniform` w_max 8 and `few_classes:5` w_max 16 — the two shapes `INSTANCEGEN_PLAN` §11 shows drive `RC2Stratified` differently; `powerlaw` deferred |

---

## 6. Inventory

### Exists and is reused unchanged

| Path | Role |
|---|---|
| `instancegen/generate.py`, `feasible.py`, `wcnf_io.py` + 62 tests | G1, G2, writer, weight samplers |
| `src/cli/profile_hardness.py` | RC2 certification and tiering, subprocess-safe timeout |
| `src/cli/oracle_evalmaxsat.py` | second-oracle agreement check (Step 2) |
| `src/bench/analyze_tiers.py`, `make_tier2_manifest.py` | aggregation, tier-2 manifest |
| `cluster_staging_maxsat/scripts/screen_mse16_array.sbatch`, `submit_mse16_screen.sh` | the certification array (needs an `OUTDIR` variable) |
| `.gitignore:54-56` | generated instances out, manifests in |

### To write

| Path | Step | Size |
|---|---|---|
| `instancegen/maxcut.py` | 1a | ~120 lines |
| `instancegen/reweight.py` | 1b | ~60 lines |
| `instancegen/planted.py` | 1c | ~30 lines |
| `instancegen/cli.py` | 1d | ~150 lines |
| `instancegen/verify.py` | 2 | ~150 lines |
| `instancegen/tests/test_{maxcut,reweight,planted,verify}.py` | 1–2 | |
| `instancegen/grids/corpus_v1.yaml` | 4 | data |
| `results/profile/gen_calib_a.jsonl`, `results/hardness/gen_calib_b/`, `results/hardness/gen_corpus_v1/` | 3, 5 | results |
| `data/generated/corpus_v1/manifest.jsonl` | 5 | data |

### Added today

| Path | What |
|---|---|
| `results/profile/gen_pilot_cap60.jsonl` | the 25 pilot rows behind §2; instance paths are `instancegen-pilot/<filename>` and each file regenerates byte-identically from the parameters in its name |
| `docs/CORPUS_GENERATOR_PLAN.md` | this document |
