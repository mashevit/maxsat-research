# Distinct-clause random k-SAT generator (`ksat_distinct`)

**Date:** 2026-10-08. Indexed from [`RESEARCH_NOTES.md`](RESEARCH_NOTES.md) §1 and
note N-2026-10-08-c. Status labels follow the hub: [verified], [inference],
[decision].

**Scope.** This note covers instance *generation* only. Nothing here says how hard
these instances are or what their optimum is. Those are questions for the
calibration runs that come next (§8).

## 1. Requirements

These are the requirements stated for this experiment (user, 2026-10-08):

1. Each clause has exactly k distinct variables, chosen uniformly from {1..n}.
2. Each chosen variable gets a positive or negative sign with probability 1/2, independently.
3. No variable occurs twice in a clause.
4. No clause is a tautology.
5. No two clauses in an instance are the same, including clauses that differ only in literal order.
6. Generation is reproducible from an explicit seed.
7. Exactly m distinct clauses are produced, all soft with weight 1.

## 2. Audit of the existing generator (`weighted_ksat` 0.1.0) [verified]

The existing generator is `instancegen/generate.py` `generate()` (line 214),
written by `instancegen/wcnf_io.py` `format_wcnf()` (line 44).

| req | met? | evidence |
|---|---|---|
| 1 | yes | `rng.sample(range(1, n+1), k)`, `generate.py:234` |
| 2 | yes | `rng.random() < 0.5` per variable, `generate.py:235` |
| 3 | yes | follows from 1 (sampling without replacement within a clause) |
| 4 | yes | follows from 3 |
| 5 | **no** | each clause is drawn independently (`generate.py:239–241`). Nothing checks for repeats, so clauses are sampled **with** replacement. |
| 6 | yes | one `random.Random(seed)` (`generate.py:229`). Re-runs are byte-identical (`cli --check` over calib_a/b/c; `tests/test_wcnf_io.py`). |
| 7 | partly | m = `round(alpha * n)` (`generate.py:58–59`), not an explicit m. Weight is 1 when `w_max: 1` (all calib grids). The m clauses are not guaranteed distinct. |

**Duplicates in the existing calibration data [verified].** I counted them
across every file in `cluster_staging_maxsat/data/generated/calib_{a,b,c}/`,
treating two clauses as equal when they differ only in literal order:

- **Max-2-SAT:** 133 of 170 files contain at least one repeated clause, with
  493 extra copies in total.
- **Max-3-SAT:** 24 of 160 files, with 35 extra copies.

Per cell, the mean number of extra copies matches C(m, 2)/N, where
N = 2^k·C(n, k) is the size of the clause space:

| cell | mean extra copies | max | C(m, 2)/N |
|---|---|---|---|
| n100, m600 | 7.4 | 10 | 9.1 |
| n250, m1500 | 10.4 | 13 | 9.0 |
| n400, m800 | 0.7 | 4 | 1.0 |

Every Max-2-SAT cell has between 0.09 % and 1.2 % of its clauses as extra copies.

*Implication [inference].* With unit weights, a clause that appears twice
behaves like one clause of weight 2. The c\* values recorded for calib_a/b/c
count both copies. The with-replacement model is a legitimate random model;
it is simply a different model from the one specified above. Its instances are
**not** regenerated or changed, and results from them must be labelled as
`weighted_ksat` (with replacement).

## 3. Decision: extend the package with a separate mode, not a new `GenParams` field [decision]

- **Why not a new field.** `GenParams`' field set is frozen. `asdict(GenParams)`
  is the `generator.params` that `cli generate-grid --check` compares against
  each committed manifest row. Adding a field would make every existing
  manifest fail its check.
- **What was done instead.** A separate params type and function were added
  to the same module. They reuse `Clause`, `Instance` and the WCNF writer, and
  `generate()` itself is unchanged.
- **Evidence that `generate()` is unchanged.**
  - `tests/test_distinct.py::test_original_generator_bytes_pinned` pins two
    SHA-256 values. One of them equals the hash of
    `calib_a/wksat_v100_k2_sr6.00_hr0.00_w1_uniform_s1.wcnf` on disk.
  - `generate-grid --check` gives the same result as before the change:
    - calib_c: OK.
    - calib_a/b: every instance and manifest row matches. The only failure is
      the Slurm manifest files `scripts/manifest_calib_{a,b}_rc2.txt`, which
      were already missing before this change.

## 4. The new mode: `ksat_distinct` 1.0.0

**Code.**

| part | where |
|---|---|
| sampler | `instancegen/generate.py`: `DistinctParams`, `validate_distinct` (line 304), `canonical` (319), `generate_distinct` (326), `distinct_filename` (360) |
| CLI | `instancegen/cli.py` `cmd_generate_distinct` (line 370) |
| file validator | `instancegen/validate.py` |
| tests | `instancegen/tests/test_distinct.py` |
| metadata names | `instancegen/__init__.py` (`DISTINCT_*`) |

**Sampling algorithm.** The input is (n, k, m, seed). **Clauses are sampled
uniformly without replacement** from the 2^k·C(n, k) clauses over k distinct
variables, using rejection sampling:

A. **Validate the request.** Require 1 ≤ k ≤ n and 0 ≤ m ≤ 2^k·C(n, k).
   Anything else raises `ValueError`; the CLI exits with the message.

B. **Initialise.** Create `rng = random.Random(seed)`, an empty set `seen`, an
   empty list `accepted` and an empty list `rejected`.

C. **Draw until `len(accepted) == m`:**
   1. Draw k distinct variables with `rng.sample(range(1, n+1), k)`. On a
      `range`, CPython draws without building the variable list, and nothing
      enumerates the clause space.
   2. For each variable, in draw order, call `rng.random() < 0.5` to choose
      its sign (positive if true).
   3. Canonicalise the clause by sorting its signed literals by variable id.
   4. If the canonical clause is in `seen`, append it to `rejected` and draw
      again.
   5. Otherwise add it to `seen` and append it to `accepted`.

D. **Write the file.** Write `accepted` in acceptance order through
   `format_wcnf(..., dialect="old")`. Output order comes from the list, never
   from set iteration.

**Why the result is uniform [inference].** Each candidate is uniform over the
whole clause space. Conditioned on being accepted, it is therefore uniform over
the clauses not yet accepted. So the accepted sequence is a uniformly random
ordered m-sample without replacement, and its set is a uniformly random
m-subset.

Distinct variables rule out repeated variables and tautologies (requirements
3–4). Canonicalisation plus the membership test rules out duplicates in any
literal order (requirement 5).

**Seed behaviour.**
- **One stream.** A single `Random(seed)` (Mersenne Twister) drives
  everything. Per candidate it makes one `sample` call and then k `random()`
  calls. There is no module-level randomness.
- **Byte-identical re-runs.** The same (n, k, m, seed) gives byte-identical
  output, including the list of rejected candidates.
- **Prefix property.** For a fixed seed, the instance with m₁ < m₂ clauses is
  exactly the first m₁ clauses of the instance with m₂.
- **Caveat: interpreter version.** `Random.sample`'s internal algorithm is a
  CPython implementation detail. Byte-identity is guaranteed for a fixed
  interpreter version, which the sidecar records (`python`). The existing
  generator has the same dependency.
- **Not comparable with `weighted_ksat`.** The two modes consume the RNG
  differently (the old mode also draws a weight per clause). Even when the old
  mode happens to produce no duplicate, the two modes do not give the same
  instance for the same seed.

**Duplicate handling.**
- **What is recorded.** Every rejected candidate is kept, in draw order, as a
  canonical clause. The sidecar stores `n_rejected_duplicates`,
  `rejected_duplicates` and `n_candidates_drawn` (= m + rejected).
- **Cost when sparse.** The expected number of rejections is
  ≈ m²/(2N) when m ≪ N.
- **Cost near exhaustion.** Rejection sampling becomes inefficient as the
  clause space runs out. The expected total number of draws is
  N·(H_N − H_{N−m}) ≈ N·ln(N/(N−m)), which grows to about N·ln N at m = N.
  The method is meant for sparse grids. For dense requests (m/N not small),
  use a different method, such as sampling m indices of the clause space
  without replacement.
- **Exhaustive requests still work.** They terminate with probability 1. The
  tests cover k = n with m = 2^k, and n = 4, k = 2 with m = 24 (the full
  space).

**Output format.** The output uses the project's old WCNF dialect, the same
one used for calib_a/b/c:

- **Header.** `p wcnf <n> <m> <top>`, with top = m + 1, i.e. 1 + the total
  soft weight (the `generate()` convention).
- **Clause lines.** m lines of the form `1 <lit> ... <lit> 0`, each with
  literals sorted by variable id.
- **No hard clauses, no comments.**

**Filename and metadata.**
- **Filename.** `ksat_distinct_v<n>_k<k>_m<m>_s<seed>.wcnf`, which cannot
  collide with `wksat_*`.
- **Sidecar.** A JSON file with the same stem holds:
  - `generator.name = "ksat_distinct"`, `version = "1.0.0"`, and
    `sampling = "uniform_clauses_without_replacement_rejection"`;
  - `params` {n_vars, k, m, seed};
  - `instance_sha256` and the sizes;
  - `clause_space`;
  - the rejection record;
  - the validator's counts;
  - `python`, `git_sha` and `created_utc`.

**Usage.**

```
python -m instancegen.cli generate-distinct --n 32000 --k 2 --m 38400 --seed 1 --out-dir <dir>
```

The command writes the instance and the sidecar, re-reads the file, validates
it, and exits non-zero on any violation.

## 5. Validation [verified]

**The file validator.** `instancegen/validate.py` parses the written file,
independently of the generator objects. It counts:

- clause count against m, and the header n and m;
- clauses whose length is not k;
- variables outside 1..n;
- variables repeated within a clause;
- tautologies;
- duplicates, compared order-insensitively;
- weights other than 1;
- clauses missing the terminating 0;
- top ≠ 1 + total soft weight.

**Tests.** `tests/test_distinct.py` has 30 tests; the full `instancegen` suite
of 112 tests passes. They check:

- the clause contract on four parameter sets, including 89 % and 100 % of the
  clause space;
- that sign and variable frequencies are roughly uniform (loose sanity bounds
  on the sign fraction, and a chi-square bound on variable counts);
- byte-identical re-runs, that different seeds give different output, and the
  prefix property;
- that rejections are recorded when the request is dense and are rare when it
  is sparse;
- m = 0;
- the full space when k = n;
- six impossible requests (k < 1, k > n, m < 0, and m above the space in three
  shapes);
- that the validator flags each violation kind, including a duplicate that
  differs only in literal order;
- the CLI's file and metadata;
- the CLI's handling of an impossible request;
- the pinned bytes of the original generator.

**Small instance, shown in full.** For n = 5, k = 2, m = 12, seed 1 (clause
space 40):

- 16 candidates were drawn and 4 rejected:
  `[1,-4] [-2,-4] [-4,-5] [-4,5]`, each already accepted.
- The validator passed.

## 6. Local generation benchmark [verified]

The benchmark ran on the workstation (WSL2), Python 3.11.13, for k = 2,
n = 32000, m = 38400 (α = 1.2) and seed 1, using
`generate-distinct --n 32000 --k 2 --m 38400 --seed 1`. It was run twice.

| quantity | value |
|---|---|
| clause space N | 2,047,936,000 (m/N = 1.9·10⁻⁵) |
| rejected duplicate candidates | 1 (expected m²/(2N) ≈ 0.36) |
| generation | 0.10 s |
| format + write | 0.02 s |
| validate | 0.07 s |
| whole process, wall clock | 0.26 s |
| peak RSS (`/usr/bin/time -v`) | 43 MB (the bare interpreter is 8 MB) |
| output size | 626,160 bytes |
| sha256 | `414321abb54ed6f45f399cfc0f097f5a5327b5ce43f4ce9ca78b19b54d1f37a6` (identical on both runs; `cmp` equal) |
| validator | 38400 clauses, 38400 distinct, 0 violations of any kind |
| PySAT `WCNF` read | nv 32000, 38400 soft, 0 hard, weights {1}, 38400 distinct |

**Local generation is practical.** At this size the run takes well under a
second and needs tens of MB. Since the sparse cost is linear in m, so are much
larger grid points, as long as m ≪ N. Generation therefore does not need the
cluster. RC2 was not run on this instance and no cluster job was submitted.

## 7. What changed

**New:**
- `generate.py`: `DistinctParams`, `DistinctResult`, `n_possible_clauses`,
  `validate_distinct`, `canonical`, `generate_distinct`, `distinct_filename`;
- `instancegen/validate.py`;
- `instancegen/tests/test_distinct.py`;
- the CLI subcommand `generate-distinct`;
- `DISTINCT_*` constants in `instancegen/__init__.py`.

**Changed (docstrings only):**
- `generate()` now says it samples with replacement and points to the new mode;
- the `cli.py` module docstring documents the new subcommand.

**Unchanged:**
- `GenParams`, `generate()`'s behaviour, the WCNF writer and `generate-grid`;
- every existing instance and manifest.

**Not done:**
- Grid YAML support for the distinct mode, i.e. a batch file producing many
  `ksat_distinct` instances plus a Slurm manifest. This is the natural next
  step once the grid points are chosen.

## 8. What this does not establish

- **Excluding duplicates is not a hardness lever.** It does not guarantee hard
  instances, a particular c\*, or any RC2 time. In sparse grids it changes very
  few clauses: about 0.4 expected duplicates at the benchmark point, and up to
  about 1 % of clauses in the densest calib cells.
- **Optimum and difficulty are open questions.** Where c\* and RC2 time fall
  for `ksat_distinct` instances (for example, Max-2-SAT near or above the α = 1
  threshold at large n) is for the calibration experiments that follow.

## 9. Addendum 2026-10-08 (later): the literature model, and nesting across α

- **`ksat_distinct` matches a literature model exactly.** It is BBCKW's
  F_{n,m} ("uniformly at random from all 2-SAT formulae with exactly m
  different clauses", RSA 18(3), 2001, §1) [verified from the TeX source].
- **CGHS (arXiv:math/0306047) uses the with-replacement model,** i.e. the
  model of `weighted_ksat` with unit weights. At α ≈ 1–1.2 the two differ by
  C(m, 2)/N ≈ α²/4 ≈ 0.3 colliding pairs per instance, independent of n.
  Details are in `CALIB_2SAT_SC.md` §2.
- **The prefix property (§4) has a design consequence.**
  - A grid that reuses one seed list across α produces nested instances: for
    the same (n, seed), the smaller-α instance is a prefix of the larger.
  - calib_a/b (`weighted_ksat`) are nested this way (N-2026-10-08-e).
  - `calib_2sat_sc` gives every instance its own seed.
- **New grid feature.** `instancegen/cli.py` now accepts
  `generator: ksat_distinct` in a grid file. It also accepts per-entry seed
  lists with no top-level list. Both changes are covered in
  `instancegen/tests/test_grid_distinct.py`.
- **This note's §7 is superseded on one point.** "Grid YAML support … not
  done" is no longer true.
