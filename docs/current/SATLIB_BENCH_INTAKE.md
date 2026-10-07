# SATLIB benchmark families: intake, satisfiability, parser normalisation, and the proposed RC2 screen

**Date:** 2026-10-07. **Status:** the intake milestone is done. The files
are labelled, normalised in place and verified, and the manifests are
written. **No RC2 or memetic run has been submitted.** The RC2 screen in §5
is approved as one array of 263 tasks. You will submit it later (§5).
Decisions S-a…S-d were settled on 2026-10-07 (§6).

All paths are relative to `cluster_staging_maxsat/` unless they start with
`docs/`.

---

## 0. Summary

- `data/satlib_bench/` holds **279 SATLIB CNF files in 7 families**:
  - **263 are unsatisfiable** and go into the RC2 manifests;
  - **16 are satisfiable** (all in `jnh`). They stay on disk and are listed
    in the manifest with `exclude_reason`, but no RC2 manifest includes
    them.
  - Each label comes from the file's own content. A plain SAT solver
    (CaDiCaL 1.5.3, 60 s cap) confirmed all 279 labels. RC2 was not used for
    labelling.
- **RC2 misread 209 of the original files.** RC2 loads instances with
  PySAT's line-based CNF reader.
  - That reader turned SATLIB's `%`/`0` trailer (uuf), pret's stray trailing
    `0` line, and hole9's split last clause into **empty soft clauses**
    (208 files).
  - On pret60_25 the original file **crashes RC2** (`IndexError`, 161 soft
    clauses). The normalised file certifies c\* = 1 in 0.003 s.
  - dubois100 has 202 clause lines without the terminating `0`. PySAT takes
    the last token of each line as the terminator, so it **silently drops
    one literal from each of those 202 clauses**: `199 200 1` becomes
    `[199, 200]`. RC2 would have solved a different formula without any
    error. A strict DIMACS reader instead merges the lines into 6-literal
    clauses.
  - The memetic solver's reader read all 279 originals correctly.
- **All 279 files are rewritten in canonical form.** Each has one clause per
  line, single spaces, every clause 0-terminated, and no trailer. The
  original comment block is kept, with one added `c normalized …` line that
  says what changed.
  - The untouched originals are in
    `data/raw/satlib_bench_original_20261007.tar.gz`.
  - PySAT's reader, the memetic reader and a strict DIMACS reader now return
    the same clause list on every file. Each list also has exactly the
    header's m clauses.
- **One RC2 manifest:** `scripts/manifest_satlib_rc2.txt`, with its
  `.sha256` list. It holds all **263 unsat instances**:
  - 64 structured: bf 4, dubois 13, hole 5, jnh 34, pret 8;
  - 199 uuf: uuf200 99, uuf225 100.
  - Approved for submission; not yet submitted.
- **What these families add (expected, not yet measured).** They add
  structural origin and size diversity. They are **not** expected to widen
  the optimum range much: dubois, pret and hole are minimally unsatisfiable
  by construction, so c\* = 1 is expected.
  - **The exception is uuf200.** Its historical RC2 rows give c\* = 2 on 2 of
    10 instances, and 6 of 10 are in the (30, 900] s window.
  - Optima above 1 still have to come from **Max-2-SAT and MaxCut**, which
    stay in the plan. See §4.

## 1. Inventory and satisfiability

| family | dir | files | unsat | sat | n | m | m/n | clause length | label source |
|---|---|---:|---:|---:|---|---|---|---|---|
| bf | `bf/` | 4 | 4 | 0 | 1040–2180 | 3434–6778 | 2.5–3.5 | 1–6 (has unit clauses) | family convention (no note in file) |
| dubois | `dubois/` | 13 | 13 | 0 | 60–300 | 160–800 | 2.67 | 3 | `c NOTE: Not satisfiable` |
| hole | `pigeon-hole/` | 5 | 5 | 0 | 42–110 | 133–561 | 3.2–5.1 | 2 and n | `c NOTE: Not satisfiable` |
| jnh | `jnh/` | 50 | 34 | **16** | 100 | 800–900 | 8.0–9.0 | 2–14 | `c NOTE: (Not) satisfiable` |
| pret | `pret/` | 8 | 8 | 0 | 60, 150 | 160, 400 | 2.67 | 3 | generator field `Charge (0 = sat. / 1 = unsat.) ==> 1` |
| uuf200 | `uuf200-860/UUF200.860.1000/` | 99 | 99 | 0 | 200 | 860 | 4.30 | 3 | family convention (uuf = uniform random 3-SAT, unsat) |
| uuf225 | `uuf225-960/UUF225.960.100/` | 100 | 100 | 0 | 225 | 960 | 4.27 | 3 | family convention |
| **total** | | **279** | **263** | **16** | | | | | |

The satisfiable jnh files are jnh1, 7, 12, 17, 201, 204, 205, 207, 209,
210, 212, 213, 217, 218, 220 and 301.

**Labelling rule** (`scripts/satlib_bench_intake.py`, `label()`). The first
match wins:
1. a `c NOTE: Not satisfiable` or `c NOTE: Satisfiable` comment;
2. pret's generator field;
3. family convention, for uuf and bf only.

**Cross-check.** CaDiCaL 1.5.3 through PySAT, 60 s per file:
- 263 unsat, 16 sat, 0 timeouts. It agrees with the label on every file.
- The slowest file was hole10 at 48 s. Everything else took ≤ 6.3 s.

A disagreement would have stopped the script.

**Other facts, recorded and left unchanged.**
- 11 files contain duplicate clauses: bf (1–3 each), jnh17, jnh218, and
  uuf225-041/044/049/050/076.
- In unweighted MaxSAT a duplicated soft clause counts twice. We keep the
  published instance as it is.
- uuf200 has 99 files (01–099); SATLIB's set has 100, so uuf200-0100 is not
  on disk.

## 2. Parser defects and the normalisation

Two readers matter:
- **RC2** runs `src/cli/run_opt_rc2.py:load_as_wcnf`, which calls
  `pysat.formula.CNF(from_file=…)`. This reader is line-based: every
  non-comment line is a clause, and a line holding only `0` is an
  **empty clause**.
- **The memetic solver** runs `src/sat/cnf.py:WCNF.parse_dimacs`. It skips
  `%` lines and lines that start with `0`.

What each defect does to the two readers:

| defect | files | PySAT / RC2 on the original | memetic reader | fix |
|---|---:|---|---|---|
| `%` end marker followed by a `0` line (SATLIB convention) | 199 (all uuf) | m + 2 clauses, 2 of them empty | correct | data ends at `%`; trailer dropped |
| stray `0` line after the last clause | 8 (all pret) | m + 1 clauses, 1 empty; **RC2 crashes** (pret60_25: `IndexError`) | correct | dropped (the header confirms m) |
| last clause split across two lines (`… 82` then `0`) | 1 (hole9) | 416 clauses, 1 empty | correct | joined |
| 202 clause lines without a final `0` | 1 (dubois100) | 800 clauses, but **the last literal of each of the 202 lines is dropped**: a silently different formula | correct | `0` supplied; a strict DIMACS reader would read 598 clauses, merged into 6-literal clauses |
| tab separators | 4 (all bf) | correct | correct | single spaces |

An empty soft clause is falsified by every assignment. So it either
inflates c\* by 1 or crashes RC2 outright, as it did on pret. The dubois100
case is worse because nothing signals it. The manifest's
`pysat_on_original.agrees` field is `false` for exactly these 209 files. The same issue
was found earlier for the historical uuf250 copies
(`docs/archive/RC2_FINDINGS.md` §4). Those copies were stripped with
`sed -i '/^%$/,$d'` (`docs/archive/TIER2_MEMETIC_PLAN.md`). The new folder
had not been cleaned.

**How a file is read** (`parse_original`):
- Data ends at a `%` line.
- Two readings are tried:
  - (A) a strict token stream, where clauses end at a `0` token, across
    lines;
  - (B) a line-based reading, where a missing final `0` is supplied.
- A reading is accepted only if it yields exactly the header's m non-empty
  clauses over variables 1…n. (A) wins on 278 files; (B) is needed only for
  dubois100.
- If no reading matches, the script stops. Nothing is guessed.

**Verification**, run on every file:
1. The chosen clause list equals what the memetic reader gets from the
   **original** file. This is an independent reader that was already
   robust.
2. On the normalised file, PySAT's reader, the memetic reader and the strict
   token reader all return that same list.
3. Normalisation is idempotent.
4. `--check` confirms that the disk matches the normalised form and that
   the manifests are current. Result: 0 differences.
5. Both production loaders (`load_as_wcnf`, `WCNF.parse_dimacs`) give
   `nv = n`, m clauses, no empty clause and no hard clause on all 279
   files.

**Tests:** `tests/test_satlib_bench_intake.py`, 16 tests. There is one
synthetic file per defect, plus label rules and error cases.

The staging suite gives 152 passed, 1 failed and 3 skipped. The failure is
the known intermittent one. Its name is now captured:
`tests/test_m2_prep.py::test_population_10_runs[p10_ls2p5]`.
- It is a timing-dependent bound on children per generation under deadline
  clipping.
- It passed on 3 immediate reruns.
- It is unrelated to this change.

## 3. Files

| file | tracked | content |
|---|---|---|
| `scripts/satlib_bench_intake.py` | yes | labels, normalisation, verification and manifests. Report only by default; `--write`; `--check`; `--sat-check-s S` |
| `tests/test_satlib_bench_intake.py` | yes | 16 tests |
| `data/satlib_bench/manifest.jsonl` | yes (`.gitignore` exception) | one row per file: family, n, m, clause-length histogram, label, label source and evidence, SAT cross-check, original and current sha256, normalisation notes, PySAT-on-original clause and empty-clause counts, `rc2_list`, `exclude_reason` |
| `scripts/manifest_satlib_rc2.{txt,sha256}` | yes | all 263 unsat instances, one RC2 array (batch `satlib`) |
| `data/satlib_bench/**/*.cnf` | no (`data/**` is ignored) | normalised in place |
| `data/raw/satlib_bench_original_20261007.tar.gz` | no | the untouched originals. The script reads these every time, so they must not be deleted |

## 4. What these families can add, and what they cannot

**Verified so far:**
- Local RC2 smoke: dubois20 and pret60_25 both certify c\* = 1 in under
  0.01 s.
- Historical RC2 on uuf200-01…010 (`results/profile_uuf/`, cap 600 s,
  PySAT version unknown, files stripped of the trailer):

| uuf200 | c\* | RC2 s |
|---|---:|---:|
| 01 | 2 | 307.4 |
| 02 | 2 | 128.5 |
| 03 | 1 | 1.9 |
| 04 | 1 | 43.4 |
| 05 | 1 | 14.1 |
| 06 | 1 | 31.5 |
| 07 | 1 | 41.1 |
| 08 | 1 | 28.6 |
| 09 | 1 | 36.3 |
| 010 | 1 | 18.4 |

  - **6 of 10 fall in (30, 900] s.** Both c\* = 2 instances are in the
    window.
  - uuf200-01 and -02 are already in the historical tier-2 memetic set.

**Expected [inference, not measured]:**
- **dubois, pret, hole:** c\* = 1.
  - Each is built so that dropping a single clause makes the formula
    satisfiable: an XOR chain, a parity-charged graph, and one pigeon too
    many.
  - Most of them should be far below 30 s for RC2. hole9 and hole10 are the
    exception: pigeonhole is exponential for resolution, CaDiCaL already
    needs 5 s and 48 s just to prove unsat, and they may land in the
    window.
  - Under the standing rule, no memetic runs on instances below the window.
- **jnh (n 100, m/n 8–9, mixed clause lengths 2–14):** c\* unknown. This is
  the family most likely to give c\* > 1 among the structured ones. It is
  also the classic random-instance family with non-uniform clause length.
- **bf (circuit, n 1040–2180, contains unit clauses):** c\* and RC2 time
  unknown. These are the largest instances in the set.
- **uuf225:** between uuf200 and the reference uuf250. By the uuf200 split,
  expect c\* ∈ {1, 2}. Times rise toward the cap.

**What this means for the research conclusions:**
- The SATLIB families move the **origin** axis (structured: circuit,
  parity, pigeonhole, XOR chain) and the **clause-length** axis (jnh, bf,
  hole).
- They move c\* only a little. uuf200 and uuf225 fill the n = 200 gap noted
  in `GRID_POINTS_WINDOW_30_900.md` §4.2, with c\* ∈ {1, 2}.
- **Optima clearly above 1 come from Max-2-SAT (eligible c\* 18–50) and
  MaxCut (expected in the tens).** These stay in the plan and must stay in
  the conclusions. A corpus of SATLIB unsat instances alone would recreate
  the "everything has c\* = 1" restriction of range that the editorial
  review objected to (`more_data/CORPUS_BROADENING_HANDOFF.md` §1, repo root).
- **A fixed, finite set.** Like stratum S1, SATLIB instances have no fresh
  seeds. Calibration and final evaluation cannot be separated by seed, so
  each family is reported as its own stratum and never silently pooled with
  generated strata.

## 5. RC2 screen: one array over all 263 unsat instances (approved 2026-10-07; to be submitted)

It uses the same RC2 configuration as every calibration batch (protocol
§2.1):
- `RC2(wcnf, "g3")` with default options;
- cap 900 s + 60 s grace;
- PySAT 1.9.dev3 expected. The env sidecar records it, and
  `aggregate_rc2_profile.py` warns on drift.

It uses the same eligibility rule: certified and 30 s < t ≤ 900 s.

| batch | manifest | tasks | throttle | worst-case CPU-h | worst-case elapsed compute | expected CPU-h [inference] |
|---|---|---:|---:|---:|---:|---:|
| `satlib` | `scripts/manifest_satlib_rc2.txt` | 263 | %30 | 70.1 (263 × 960 s) | 9 waves × ~17 min ≈ 2.6 h | ≈ 6–12 (see below) |

The expected figure is an inference:
- most structured instances are tiny;
- the uuf200 historical median is ≈ 33 s;
- uuf225 is extrapolated;
- bf, hole10 and jnh are unknown.

Queue delay is not included in the elapsed figure.

**Then:**
- the memetic primary arm (`memetic_deeppolish_p40_ls3p5`, 3 seeds, 900 s,
  stop at the RC2 optimum) on **eligible instances only**;
- every non-eligible instance goes to a not-run list with its reason.

The memetic manifest builder for this batch does not exist yet. It is the
next milestone after the RC2 rows return, modelled on
`make_calib_c_memetic_manifest.py`.

**Fixed rules, stated before any row exists:**
- No instance is added or removed after rows arrive.
- No workstation pre-screen and no screen-out: every unsat instance is
  submitted.
- Satisfiable instances are never included.
- No selection toward ρ.
- Results are reported per family. The `family` field is in
  `data/satlib_bench/manifest.jsonl`.
- The 10 uuf200 instances with historical rows are re-run under the fixed
  configuration rather than reused. Their PySAT version and cap differ.

**Commands.** The repository commit is done (2026-10-07).
`<user>@<cluster>` is the only placeholder.

```bash
# 1. workstation -> cluster (carries the normalised data/satlib_bench/; data/ is gitignored, so rsync is the only way it gets there)
cd /home/mashe/maxsat-lab_new/maxsat-lab
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# 2. login node: one array, 263 tasks, at most 30 concurrent
cd ~/maxsat-lab && sha256sum --quiet -c scripts/manifest_satlib_rc2.sha256 && echo SHA_OK
cd scripts && mkdir -p logs
DRY_RUN=1 THROTTLE=30 MANIFEST=manifest_satlib_rc2.txt OUTDIR=results/profile_satlib bash submit_rc2_profile.sh
THROTTLE=30 MANIFEST=manifest_satlib_rc2.txt OUTDIR=results/profile_satlib bash submit_rc2_profile.sh   # record job id
#   equivalent raw form:  sbatch --array=1-263%30 --export=ALL,MANIFEST=scripts/manifest_satlib_rc2.txt,OUTDIR=results/profile_satlib rc2_profile_array.sbatch
RESUME=1 THROTTLE=30 MANIFEST=manifest_satlib_rc2.txt OUTDIR=results/profile_satlib bash submit_rc2_profile.sh   # only if rows are missing

# 3. back on the workstation
rsync -av <user>@<cluster>:~/maxsat-lab/results/profile_satlib/ cluster_staging_maxsat/results/profile_satlib/
cd cluster_staging_maxsat && python3 scripts/aggregate_rc2_profile.py --batch satlib   # expect 263 rows, pysat 1.9.dev3
```

## 6. Decisions (settled by the user, 2026-10-07)

| # | decision | outcome |
|---|---|---|
| S-a | Submit the structured families | **Yes**, in the single array |
| S-b | uuf200/uuf225 | **All 199**, in the same array |
| S-c | Workstation RC2 pre-screen or screen-out | **None.** Every unsat instance is submitted |
| S-d | Satisfiable jnh instances | **Excluded** from every manifest; kept on disk only |

Array throttle: **%30**.

## 7. Research notes recorded with this intake

Recorded in [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) (entries N-2026-10-07-a…e).
