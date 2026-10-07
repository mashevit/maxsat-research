# Research notes — the single entry point

**Purpose.** Every research note we collect goes here, or is indexed here.
These are findings, caveats, quotations, rationales for scope decisions,
and claims we intend to make or avoid. Before writing up results, or before
deciding scope, start here.

**Created:** 2026-10-07. **Maintained:** append-only. Newest entries are at
the top of §2.

**How to add a note.**
1. Add an entry to §2 with an id `N-YYYY-MM-DD-x`, a one-line title and a
   status label (below).
2. Write the note itself. Quote user-supplied or external text verbatim, in
   a block quote, with its source.
3. Say where the evidence lives (document §, results file, script).
4. If the note is long, put it in its own `docs/current/RESEARCH_NOTES_<TOPIC>.md`
   and index it in §1. Keep a short entry in §2.

Never edit an old entry's claim in place. Add a dated correction under it.

**Status labels** (as in the topic notes):
- **[verified]**: read off rows or code;
- **[inference]**: follows from verified facts by a stated argument;
- **[extrapolation]**: assumes a trend continues;
- **[quote]**: external or user-supplied text, recorded as given;
- **[decision]**: a scope or design decision and its reason.

---

## 1. Topic notes and documents that carry research content

| topic | document | what it establishes |
|---|---|---|
| Restriction of range (why the corpus is being broadened) | `more_data/CORPUS_BROADENING_HANDOFF.md` §1–§2 (repo root) | The editorial objection: 26 near-identical uuf250 instances, 24 with c\* = 1, cannot support an orthogonality claim. The four axes are clause length, weightedness, c\* and origin. Which results survive. |
| Core-guided vs branch-and-bound, benchmark design | `docs/maxsat-benchmark-design-notes.md` | One UNSAT proof per unit of cost (OLL / RC2), and what that implies for instance design. Literature vs definition vs our measurements are kept apart. |
| Which optima RC2 can certify for random Max-3-SAT at n ≥ 250 | [`RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`](RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md) | C1–C4: at n ≥ 250 the eligible instances have c\* = 1; c\* = 2 is at or past 900 s; raising density does not help. |
| RC2 grid points under the (30, 900] s window | [`GRID_POINTS_WINDOW_30_900.md`](GRID_POINTS_WINDOW_30_900.md) | Grid points per (k, n, c\*); window capacity per row; the n = 200 gap. |
| RC2 time vs c\* slope | `docs/CALIB_B_B1_READOUT.md` §5, §7 | A row's yield is set by d log10(t)/dc\*. At n = 250 it is 2.32 decades per unit c\*. |
| Hard-clause instances: why they are excluded, and the exceptions | [`CORPUS_FREEZE_PREP.md`](CORPUS_FREEZE_PREP.md) §8 | Mixed-sign hard clauses are excluded for this solver: crossover and polish do not preserve feasibility. Conflict-clause families (MIS / Max-Clique) are reopened as an option. See also N-2026-10-07-a. |
| Corpus family scope | `docs/CORPUS_FAMILY_SCOPE_NOTE.md` | MaxCut is in; Max-Clique and set covering are out (partly revised by `CORPUS_FREEZE_PREP.md` §8.5). The torus stratum gap. |
| Memetic vs multistart on uuf | `docs/UUF_THREE_ARM_ABLATION_READOUT.md` | memetic 118/130, uniform multistart 124/130, JW multistart 127/130 on the 26 uuf instances. |
| M2 full pool: solver mechanics, ρ, threats to validity | `docs/M2_FULL_POOL_READOUT_AND_STATE.md` | Why 3-SAT and 2-SAT differ; the RC2 time decomposition; memetic reliability. |
| SATLIB benchmark families: intake, parser pitfalls, c\* expectations, citation | [`SATLIB_BENCH_INTAKE.md`](SATLIB_BENCH_INTAKE.md) | 263 unsat / 16 sat; 209 originals misread by PySAT; what these families can and cannot add. See N-2026-10-07-b…e (e is the required SATLIB citation). |

## 2. Dated notes (newest first)

### N-2026-10-07-f — Possible expansion: certify all 100 SATLIB uuf250 with a longer budget, for RC2 and memetic [verified + decision: deferred, not urgent]

*User, 2026-10-07:* a potential, very non-urgent expansion of the
experiments: extend the time budget for both RC2 and memetic until RC2 has
solved all of the 250-variable uuf250 instances
(`data/unsat250_1000c/`). These are SATLIB "uuf250-1065" files:
`p cnf 250 1065`, although the directory name says 1000c.

**Current state** [verified]. Read off
`cluster_staging_maxsat/results/profile_uuf250/uuf250_arr_task_*.jsonl`:
100 rows, one per instance, RC2, cap 900 s, all from the SATLIB copies.

| outcome | count | detail |
|---|---:|---|
| certified optimal, c\* = 1 | 77 | `solve_s` 14.6–889.6 s |
| not finished: killed by the harness | 21 | `subprocess_killed` at cap + 60 s (≈ 960 s); LB recovered from the progress file |
| not finished: solver timeout | 2 | `timeout` at ≈ 922–927 s (uuf250-027, -074) |
| **not finished, total** | **23** | none is a software failure; all 23 are censored at budget |

The censored lower bounds among the 23:
- **LB 1 (18 instances):** 02, 04, 08, 013, 016, 022, 027, 032, 035, 039,
  052, 069, 074, 077, 078, 086, 088, 092.
- **LB 2, so c\* ≥ 2 is proven (5 instances):** 030, 036, 037, 085, 095.

**Memetic coverage today** [verified]. By sha256 against
`results/tier2_memetic_instance_index.csv`, memetic was run on 24 of the
100 instances (5 seeds × 3 configs, 900 s). All 24 are among the 77
certified ones. That leaves 53 certified instances without a memetic run,
and the 23 censored ones have no reference optimum at all.

**What the expansion would give.**
- The full 100-instance SATLIB uuf250 set with known c\*.
- The first certified c\* ≥ 2 instances at n = 250: at least the 5 with
  LB 2. Today there are none (`RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`
  §3.1, C1).
- The hardest-for-RC2 tail of the family, compared with memetic at a
  matched, longer budget.

**What it costs.** RC2 time grows by about 2.3 decades per unit of c\* at
n = 250 (`docs/CALIB_B_B1_READOUT.md` §5) [inference]. The LB 2 instances
may therefore need far more than 900 s. No budget is proposed here: the
"hours" estimate from the B1 slope was withdrawn (§2, earlier notes,
2026-10-06). Any plan needs a staged cap (for example, rerun the 23 at a
longer cap and see how many finish) before committing memetic CPU.

*Decision.* Recorded as a **deferred, low-priority option**. It is not
planned, not approved, and not part of the current direction (larger-n
grids, MaxCut, the SATLIB RC2 screen). If it is taken up: a written plan
first, the RC2 extension before memetic, and SATLIB is cited
(N-2026-10-07-e).

### N-2026-10-07-e — Citing SATLIB (required acknowledgement) [quote + decision]

> Citing SATLIB: If you use SATLIB for your research, we ask you to
> acknowledge it in the respective publications by citing the following
> article:
>
> Holger H. Hoos and Thomas Stützle: SATLIB: An Online Resource for Research
> on SAT. In: I.P.Gent, H.v.Maaren, T.Walsh, editors, SAT 2000,
> pp.283-292, IOS Press, 2000.

*Source:* SATLIB's citation request, as supplied by the user on 2026-10-07.

*Decision.* Every publication or report that uses SATLIB instances cites
this article. That covers the historical uuf250 and uuf200 tier-2 set and
the `satlib_bench` families (bf, dubois, hole, jnh, pret, uuf200, uuf225).

BibTeX, assembled from the reference above:

```bibtex
@inproceedings{hoos2000satlib,
  author    = {Holger H. Hoos and Thomas St{\"u}tzle},
  title     = {{SATLIB}: An Online Resource for Research on {SAT}},
  booktitle = {SAT 2000},
  editor    = {I. P. Gent and H. v. Maaren and T. Walsh},
  pages     = {283--292},
  publisher = {IOS Press},
  year      = {2000}
}
```

### N-2026-10-07-a — Hard clauses: feasibility is not just an initialisation problem [quote + decision]

> That is more than Glucose preprocessing: even starting from a feasible
> assignment does not ensure that mutation and crossover preserve
> feasibility. The defensible exclusion is an implementation and
> experimental-scope decision, not a universal requirement that hard
> clauses need Glucose.

*Source:* user, 2026-10-07.

*Context.* This is how we phrase the hard-clause exclusion in the paper and
in the documents.
- A SAT solver such as Glucose gives a feasible **starting point**. That
  alone does not make the search feasible: the variation operators must
  also keep children feasible.
- The workstation probe found that they do not:
  - crossover of two feasible parents was feasible in 0/20 cases at hard
    ratio 3–4;
  - the polish did not repair the result.
  - Evidence: `CORPUS_FREEZE_PREP.md` §8.2–§8.4 [verified].

*Wording rule.*
- Say: "Instances with (mixed-sign) hard clauses are outside the scope of
  this study, because this implementation's operators do not preserve
  feasibility."
- Do not say: "Hard clauses require Glucose", or "memetic algorithms cannot
  handle hard clauses".
- A repair, decoder or hard-phase-noise arm would be a different algorithm
  (`CORPUS_FREEZE_PREP.md` §8.5).

### N-2026-10-07-b — SATLIB suite: "hard for systematic and local search" [quote]

> The majority of the instances from the benchmark suite is considered hard
> for both systematic and local search algorithms for SAT.

*Source:* user-supplied, 2026-10-07. It refers to the SATLIB / DIMACS
benchmark collection. **Confirm the exact source page and wording before
citing it.**

*How to use it.*
- It describes **SAT (decision) hardness** for the solvers of that era. It
  is not evidence about RC2 proof time, or about memetic MaxSAT difficulty
  today.
- **[verified]** With a modern CDCL solver (CaDiCaL 1.5.3), 278 of the 279
  `satlib_bench` files are decided in ≤ 6.3 s. The exception is hole10, at
  48 s. Source: `cluster_staging_maxsat/data/satlib_bench/manifest.jsonl`,
  field `sat_check`.
- Cite it for motivation and provenance ("a standard, long-used suite"),
  not as a hardness label for our solvers. Our hardness labels come from
  our own RC2 window and Q2 rules.

### N-2026-10-07-c — PySAT's CNF reader silently changes published SATLIB files [verified]

PySAT's `CNF(from_file=…)` is used by RC2 through
`src/cli/run_opt_rc2.py:load_as_wcnf`. It is line-based. On the original
SATLIB files it:
- turns `%`/`0` trailers and stray `0` lines into **empty soft clauses**:
  - +1 to c\* each, or an RC2 crash (`IndexError` on pret60_25);
  - 208 of 279 files are affected;
- **drops the last literal** of any clause line that lacks its terminating
  `0`: 202 clauses in dubois100. This gives a different formula with no
  error at all.

*Rule.*
- Any published CNF set goes through `scripts/satlib_bench_intake.py`, or
  an equivalent normaliser with cross-reader verification, before an RC2
  row is trusted.
- The memetic reader (`src/sat/cnf.py`) was robust to all of these defects,
  so RC2 and the memetic solver could silently disagree on the instance.

*Evidence:* `SATLIB_BENCH_INTAKE.md` §2, and the manifest field
`pysat_on_original`. The earlier uuf250 instance of the same problem:
`docs/archive/RC2_FINDINGS.md` §4.

### N-2026-10-07-d — Optimum diversity must come from Max-2-SAT and MaxCut, not from SATLIB unsat families [inference + decision]

- Most SATLIB unsatisfiable families are **minimally unsatisfiable by
  construction**: dubois (XOR chains), pret (parity), hole (pigeonhole).
  Expect c\* = 1. This is verified only on dubois20 and pret60_25 so far.
- uniform random 3-SAT at the threshold is mostly c\* = 1. Historical
  uuf200: 8 × c\* = 1 and 2 × c\* = 2 out of 10 [verified].
- A corpus of SATLIB unsat instances alone would reproduce the "everything
  has c\* = 1" restriction of range that the broadening exists to fix.

*Decision.*
- **Keep Max-2-SAT** (eligible c\* 18–50) **and MaxCut** (c\* expected in
  the tens) in the corpus.
- **In the research conclusions, emphasise that the optimum varies:** c\* =
  1 (SATLIB, Max-3-SAT at n ≥ 250) versus c\* in the tens (Max-2-SAT,
  MaxCut).
- The SATLIB families contribute **origin** and **clause-length**
  diversity.
- *Open:* jnh (mixed clause length, m/n 8–9) and bf (circuits) have unknown
  c\*. The proposed RC2 screen (`SATLIB_BENCH_INTAKE.md` §5) answers that.

### Earlier notes (recorded in their own documents; listed here for completeness)

- **2026-10-06.** Max-3-SAT optimum at large n, claims C1–C4, and the
  withdrawal of an "hours" estimate from the B1 slope.
  `RESEARCH_NOTES_MAX3SAT_OPTIMUM_AT_LARGE_N.md`.
- **2026-10-06.** The window grid points, and the revision of B1 §5, which
  used 60–600 s, to (30, 900] s. `GRID_POINTS_WINDOW_30_900.md`.
- **2026-10-06.** The hard-clause reassessment:
  - the "no gradient toward feasibility" wording is withdrawn;
  - the `mutate1` stale-feasibility latent bug is documented (staging
    `evo/memetic.py:152`).
  - `CORPUS_FREEZE_PREP.md` §8.
- **2026-10-06.** Effort is measured in seconds (primary). Calls and flips
  are not size- or host-free. `NEXT_SESSION_CONTEXT.md` §3.
- **2026-09-07.** Restriction of range destroys the orthogonality claim.
  The four broadening axes. `more_data/CORPUS_BROADENING_HANDOFF.md`.
