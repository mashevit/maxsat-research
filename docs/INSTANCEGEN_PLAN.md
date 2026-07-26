# Weighted Instance Generation + Tier Calibration — audit and plan

Status: **plan only.** No code is shipped by this doc; nothing outside this file
was created or edited, and no solver was run to produce it.

`git rev-parse --short HEAD` at time of writing: `dab856e`.

**Problem this addresses.** The corpus has no weighted MaxSAT instances in the
middle difficulty tier. MSE benchmarks are almost entirely T3 under RC2 because
MSE selects at the frontier of state-of-the-art C++ solvers — confirmed by this
repo's own data, `results/hardness/mse23_full/tier_summary.csv`: **T3 = 74 of 75
(98.7%)**. The fix is to generate weighted instances and calibrate them into
tiers, not to keep hunting for them.

**Relationship to the port.** The `maxsat_new/` port (`maxsat_new/PORT_NOTES.md`)
is in progress and is **not touched by anything here**. This doc's deliverable is
a new top-level `instancegen/` package; see §7 for the placement argument.

**Pairs with** `docs/STRATIFICATION_PLAN.md`, which owns the existing tier
definitions. This doc reuses those thresholds by value and records why they are
not directly comparable (§4).

---

## Part I — Audit findings

Read-only. Findings only; no code proposed in this part.

### 1. How T1/T2/T3 are currently defined

A definition exists, but three things about it matter:

- it is **T1 / T2a / T2b / T3** — four buckets, not three;
- it lives **only in `src/`**, nowhere in `maxsat_new/`;
- it is time-to-solve against **plain `RC2`**, not `RC2Stratified`.

`src/cli/profile_hardness.py:68-71`:

```python
T1_MAX_S = 60.0
T2A_MAX_S = 300.0
T2B_MAX_S = 600.0
DEFAULT_CAP = 600.0
```

`src/cli/profile_hardness.py:233-251` — `assign_tier`, a pure function:

```python
    # Tier (time-based).
    if not p["completed"]:
        rec["tier"] = "T3"
        rec["tier_reason"] = p["error"] or p["status"] or "did_not_complete"
        return rec

    if solve_s <= T1_MAX_S:
        rec["tier"] = "T1"
        rec["tier_reason"] = f"solve_s<={T1_MAX_S}"
    elif solve_s <= T2A_MAX_S:
        rec["tier"] = "T2a"
    elif solve_s <= T2B_MAX_S:
        rec["tier"] = "T2b"
    else:
        rec["tier"] = "T3"
        rec["tier_reason"] = f"solve_s>{T2B_MAX_S} (cap misconfigured?)"
```

Boundary convention is **inclusive upper** (`solve_s <= X`).

Prose spec: `docs/STRATIFICATION_PLAN.md` §2, same 60/300/600 boundaries,
justified as the MSE anytime track's cutoffs. §7 of that doc explicitly leaves
open "whether 60 / 300 / 600 are the right boundaries."

Supporting facts:

- The profiler's solver is **plain `RC2`** — `src/cli/solve_rc2_anytime.py:190`,
  `rc2 = RC2(wcnf, solver=solver)` — recorded in every row as
  `"profile.solver": "rc2"`.
- **Nothing in this repo uses `RC2Stratified`.** Grepped across `src/`,
  `maxsat_new/`, `tests/`, `cluster_staging/`: zero hits.
- **`maxsat_new/` has no tier concept at all** — no constant, no classifier, no
  mention in `PORT_NOTES.md`.
- `results/hardness/mse23_full/PROVENANCE.txt:76` flags that the code which
  produced the existing tier data is unversioned.

Tier distribution actually observed:

| Corpus | T1 | T2a | T2b | T3 | total |
|---|---|---|---|---|---|
| `mse23_full` | 0 | 0 | 1 | **74** | 75 |
| `uuf250_1000c` | 8 | — | — | 9 | 35 |

### 2. What `maxsat_new/cnf.py` implements, and which format it accepts

Implements `Clause{weight, lits, is_hard}`, `WCNF` (with `pos_adj`/`neg_adj`
occurrence lists), `parse_dimacs`, `eval_assignment`. Ported from
`src/sat/cnf.py @ 1e3eaaf`.

**It accepts the OLD wcnf format only.** The `p` line is mandatory and hard/soft
is decided by the top-weight convention.

`maxsat_new/cnf.py:59-80`:

```python
                if line.startswith("p"):
                    # p cnf <n_vars> <n_clauses>
                    # p wcnf <n_vars> <n_clauses> <top>
                    toks = line.split()
                    if len(toks) < 4:
                        raise ValueError(f"Bad problem line: {line}")
                    fmt = toks[1].lower()
                    ...
                    if fmt == "wcnf":
                        is_wcnf = True
                        if len(toks) >= 5:
                            top = int(toks[4])
                        else:
                            # Old-style WCNF header without `top` ... every
                            # clause is soft. Sentinel no real weight reaches.
                            top = 10 ** 18
```

`maxsat_new/cnf.py:85-90`:

```python
                if is_wcnf:
                    weight = int(parts[0])
                    lits = [int(x) for x in parts[1:] if x != "0"]
                    if top is None:
                        raise ValueError("WCNF clause read before header")
                    is_hard = weight >= top
```

`maxsat_new/cnf.py:103-104`:

```python
        if n_vars is None or n_clauses is None:
            raise ValueError("Missing 'p' header")
```

**Verified empirically.** A new-format file (`c t wcnf` / `h 1 2 0` / `5 -1 0` /
`3 2 0`, no `p` line) run through `WCNF.parse_dimacs`:

```
RAISED: ValueError invalid literal for int() with base 10: 'h'
```

The failure is at `cnf.py:86` — `int(parts[0])` on the token `h` — *before* the
missing-header check at `cnf.py:103` is ever reached. There is **no partial
support**: it is a hard failure, not a degraded parse.

Two replicated quirks that constrain any writer (`PORT_NOTES.md` §9):

- `cnf.py:57` — **any line whose first character is `"0"` or `"%"` is silently
  dropped** (§9.5). A soft clause with weight 0 would vanish without error.
- `cnf.py:92-99` — a `.cnf` file loads all-soft, weight 1, zero hard (§9.6).

`docs/STRATIFICATION_PLAN.md` §5 states the project's standing position
independently: *"Toy files use the old MSE format... The newer 2022+ format (`h`
prefix, no header) is not portable across pysat versions... Old format is the
safe default for files we commit."*

### 3. Existing generators and wcnf writers

**No wcnf writer exists anywhere in the repo.** Nothing in `src/` or
`maxsat_new/` serializes a formula to DIMACS.

Every writer/serializer found, exhaustively:

| Location | Writes |
|---|---|
| `src/cli/make_metadata.py:106,125` | `<file>.meta.json` + `metadata.jsonl` (structural metadata) |
| `src/cli/run_opt_rc2.py:281` | assignment **bitstring** text file (not DIMACS) |
| `src/cli/solve_rc2_anytime.py:112`, `solve_rc2_anytime2.py:130` | `_atomic_write_int` — a single integer (RC2 running lower bound) |
| `src/cli/solve_rc2_anytime.py:311`, `solve_rc2_anytime2.py:321`, `run_ea.py:207` | result JSON |
| `src/bench/harness.py:117`, `src/cli/batch_opt_rc2.py:54`, `src/cli/run_experiment.py:239`, `src/cli/run_pipeline_opt_vs_memetic.py:142` | CSV summaries |
| `src/bench/analyze_tiers.py:271` | tier/category CSV |

**Generators: exactly one, and it is not usable.**
`from_gemini.py:127 generate_random_maxsat(n_vars=20, n_clauses=80)` — a scratch
chat dump at repo root. It builds an in-memory `pysat.formula.CNF`, is
**unweighted**, **writes no file**, uses **module-level `random`** (no seed
control), and is imported by nothing.

The committed instances in `data/dev_small/` (`file_rwms_*`, `file_rpms_*`,
`file_rwpms_*`) came from an **external** tool — the file header says so:

```
c Weighted CNF
c from Selman's wff generator
p wcnf 100 600 3237
```

That generator is not in the repo.

For reference, pysat ships a writer:
`pysat.formula.WCNF.to_fp(fp, comments=None, format='mse22')`, where
`format='legacy'` emits `p wcnf nv m topw` and `format='mse22'` emits
`h`-prefixed hard clauses with no header. Both dump **soft clauses first, then
hard**.

### 4. Where instances live; existing manifest format

On disk: `data/toy/` (9), `data/dev_small/` (38 + `metadata.jsonl`),
`data/exp0..exp2/`, `data/hard/`, `data/unsat/`, `data/unsat_exp/`,
`data/raw/mse_2024/`, plus `maxsat_new/tests/data/{mini,hardmix}.wcnf`.

**2925 files under `data/` are git-tracked.** `.gitignore` has `#data/*`
**commented out**, with only `!data/toy/` un-ignored — so anything written into
`data/` is tracked by default.

Two manifest formats exist.

**(a) Structural metadata** — `data/dev_small/metadata.jsonl`, produced by
`src/sat/metadata.py:compute_metadata`, `SCHEMA_VERSION = "1.0"`. Top-level keys:

```
schema_version, format,
sizes{n_vars, n_clauses, n_hard, n_soft, n_literals, top},
density{clauses_per_var, literals_per_clause_mean, literals_per_var_mean},
clause_length{n,min,max,mean,median,std, histogram, is_uniform_3sat, max_uniform_length},
var_degree{pos, neg, total, n_unused, n_pure_positive, n_pure_negative, n_balanced},
polarity{pos_literals, neg_literals, pos_fraction},
hard_soft{hard_fraction, is_partial_maxsat, is_pure_maxsat, is_sat},
soft_weights{n,min,max,mean,median,std, sum, n_unique, is_unweighted},
structure_flags{n_horn_clauses, horn_fraction, ..., n_empty_clauses},
file{path, name, ext, size_bytes, sha256, family}
```

`_infer_family` (`src/sat/metadata.py:15-27`) maps filename prefixes to
families — `file_rwpms_` -> `random_weighted_partial_maxsat`, etc. **No solve
time, no tier.**

**(b) Profile/tier manifest** — `docs/STRATIFICATION_PLAN.md` §3, realised in
`results/profile/*.jsonl` and `results/hardness/*/all_results.jsonl`:

```json
{
  "instance": "data/raw/mse_2024/foo/bar.wcnf.gz",
  "size_mb": 3.2104,
  "profile": {
    "cap_s": 600.0, "solver": "rc2", "solve_s": 412.55,
    "final_cost": 8732, "completed": true, "error": null
  },
  "ratio": 1.0,
  "tier": "T2b",
  "tier_reason": "300.0<solve_s<=600.0"
}
```

Real rows additionally carry `cost_lower_bound`, `lb_ratio`, `status`,
`over_cap`.

**Gap worth noting:** this schema records `tier_reason` as a *formatted string*
but never records the threshold **values** as data. The tier cannot be
re-derived from a row alone if the constants change. `PROVENANCE.txt:76` is the
manual patch for that gap.

**Existing weighted corpus, for calibration reference** (from
`data/dev_small/metadata.jsonl`):

| Family | n_unique weights | w_max | n_vars |
|---|---|---|---|
| `file_rwms_wcnf_L3_V70_C700_*` | 10 | 10 | 70 |
| `file_rwpms_wcnf_L3_V100_C600_H100_0` | 10 | 10 | 100 |

That is the **entire** weighted corpus in the repo, and it is small.

### 5. What PORT_NOTES.md says about instance handling

Almost nothing, and nothing about generating instances.

- §2 — `tests/data/` holds "tiny committed instances for tests"; `results/` is
  JSONL run output.
- §3 — `cnf.py` ports `src/sat/cnf.py`; the redundant `run_ea.py:24-79` parser
  is dropped.
- §8 — the run record carries `instance`, `instance_sha256`,
  `n_vars/n_clauses/n_hard/n_soft`. **`instance_family` was explicitly cut**:
  *"needs `make_metadata`; not built yet. Join later on `instance`."*
- §8 — pins the cost convention: `best_cost` = **unsatisfied** soft weight =
  `total_soft_weight - satisfied_soft_weight`; `n_hard_violations` is tracked
  separately.
- §4/§8 — establishes the both-or-neither record convention: store **both**
  `resolved_params` (concrete values) **and** `param_rules` (provenance).
  *"A record with only the rule is not reproducible if the rule code changes;
  only the value loses provenance. Store both."*
- §9.5/§9.6 — the two parser quirks above.
- §2 — **"Standalone: must not import from `src/`."**

Also relevant: **`maxsat_new/` has no pysat dependency at all.** `cnf.py` is a
hand-rolled parser and nothing in the package imports pysat.

---

## Part II — Plan

### 6. Scope

In scope: a parametric weighted k-SAT generator; a wcnf writer with an explicit
required dialect; a calibration harness (generate -> `RC2Stratified` under a cap
-> bucket by wall-clock -> keep T2); per-instance metadata recording both
generator parameters and the tier rule; three classes of test.

Explicitly **not** in scope, and not planned anywhere below: external MaxSAT
solver integration (EvalMaxSAT/UWrMaxSat/subprocess oracle); any `Oracle`
abstraction or interface change; Model RB or planted-optimum generators; any
change under `src/`; any change to a file in flight for the port; any change to
the EA.

### 7. Placement: a new top-level `instancegen/` package

```
instancegen/
  __init__.py
  generate.py      # pure: params -> in-memory Instance. No I/O, no pysat.
  wcnf_io.py       # write_wcnf(inst, path, *, dialect)  -- dialect REQUIRED
  tiers.py         # threshold constants + classify() + TIER_RULE dict
  calibrate.py     # generate -> RC2Stratified under cap -> classify -> manifest row
  cli.py           # python -m instancegen.cli
  tests/
    test_generate.py  test_wcnf_io.py  test_tiers.py  test_calibrate.py
    data/tiny_known.wcnf
data/generated/<batch>/*.wcnf
data/generated/<batch>/manifest.jsonl
```

**Why not inside `maxsat_new/`:**

1. **`maxsat_new/` has no pysat dependency and should not acquire one.** The
   calibration harness needs `pysat.examples.rc2.RC2Stratified`. Putting it in
   `maxsat_new/` means the EA package can no longer be imported without a SAT
   solver installed — a real coupling change to a package whose whole point is
   being a clean standalone port.
2. **Every module in `maxsat_new/` is accountable to a `PORT_NOTES` §3 port-map
   row and a §10 step number.** A generator ports from nothing. Inserting a
   non-port module into a package whose fidelity story is "this reproduces
   `src/` @ `1e3eaaf`" muddies the step-8 argument that licenses deleting
   `src/`.
3. **The dependency direction is fine and one-way.** `instancegen` imports
   `maxsat_new.cnf` for the round-trip test; `maxsat_new` imports nothing from
   `instancegen`. The `PORT_NOTES` §2 constraint is "`maxsat_new` must not
   import `src/`" — untouched. `instancegen` will **also** not import `src/`, so
   it survives `src/` deletion.

Instances land in `data/generated/<batch>/` to match the existing
`data/<corpus>/` convention. The manifest sits next to them (matching
`data/dev_small/metadata.jsonl`), not in `results/` — these are inputs, not run
outputs.

### 8. Generator (`generate.py`)

```python
@dataclass(frozen=True)
class GenParams:
    n_vars: int
    clause_ratio: float      # n_clauses = round(clause_ratio * n_vars)
    k: int
    w_max: int
    hard_frac: float         # fraction of clauses emitted as hard
    seed: int
    weight_dist: str = "uniform"   # see §11 — proposed addition, decision D4

def generate(p: GenParams) -> Instance: ...
```

- One `random.Random(p.seed)` object, threaded explicitly. **No module-level
  `random.*`** — that is the `from_gemini.py:127` anti-pattern and it is exactly
  what makes seeded reproduction fail.
- Clause construction: sample `k` distinct variables without replacement,
  independent uniform sign per literal. Tautologies and duplicate literals are
  impossible by construction.
- Hard/soft split: the first `round(hard_frac * n_clauses)` clauses in
  generation order are hard. Deterministic, no second RNG stream.
- Soft weights drawn from `weight_dist` over `[1, w_max]`. **Never 0** — a
  weight-0 clause line starts with `"0"` and `maxsat_new/cnf.py:57` would
  silently drop it (audit §2).
- `Instance` is a plain frozen dataclass: `n_vars`, `clauses: tuple[Clause, ...]`,
  `top`. Deliberately independent of `maxsat_new.cnf.WCNF`, so the round-trip
  test compares two independently-built objects rather than asserting a thing
  equals itself.
- **No satisfiability guarantee.** Random weighted k-SAT above the phase
  transition is almost surely unsatisfiable in its soft part — that is what
  makes it a real MaxSAT instance. But hard clauses at `hard_frac > 0` can make
  the *hard* part unsatisfiable, which RC2 reports as no-solution. The
  calibrator must treat "hard part UNSAT" as a distinct outcome and discard it,
  **not** classify it as T3 (§10).

### 9. Writer (`wcnf_io.py`) — and the format mismatch

```python
Dialect = Literal["old", "new"]

def write_wcnf(inst: Instance, path: str, *, dialect: Dialect) -> None:
```

`dialect` is keyword-only with **no default**; an unknown value raises
`ValueError`. Both dialects follow pysat's ordering convention (softs first,
then hards) so output is diff-comparable against `WCNF.to_fp`.

- `dialect="old"` — `p wcnf <n_vars> <n_clauses> <top>` with
  `top = 1 + sum(soft weights)`; hard clauses written with weight `top`.
- `dialect="new"` — no `p` line; hard clauses prefixed `h`; soft clauses
  prefixed with their weight.

#### 9.1 Format mismatch — CALL-OUT, this is decision D1

`maxsat_new.cnf.parse_dimacs` reads **old format only** and hard-fails on `h`.
Verified by running it (audit §2): `ValueError: invalid literal for int() with
base 10: 'h'`, raised at `cnf.py:86` before the missing-header check at
`cnf.py:103`. No partial support.

**Consequence:** `dialect="new"` output is **not readable by this repo's own
parser**, and therefore not usable by the EA, `run_ea.py`, `make_metadata`, or
`profile_hardness`. It is usable by pysat (which is what the calibrator feeds)
and by external MSE tooling.

Recommendation: **implement both, calibrate and commit with `"old"`.** That
matches `STRATIFICATION_PLAN` §5's stated position, keeps the generated corpus
usable by the EA, and keeps `"new"` available for interop later.

Recommendation **against** extending `parse_dimacs`: `cnf.py` is a frozen ported
module whose behaviour is pinned bit-for-bit by the in-flight step-8 oracle test
(`maxsat_new/STEP_08_PLAN.md`), and `PORT_NOTES` §9's rule is "suspected bugs are
RECORDED, not fixed."

### 10. Tier definition (`tiers.py`) and calibration harness (`calibrate.py`)

#### 10.1 Tier rule

Constants re-declared **by value**, not imported from `src/` (which is slated
for deletion per `PORT_NOTES` §10 step 8), with a source comment citing
`src/cli/profile_hardness.py:68-71` and `STRATIFICATION_PLAN` §2:

```python
TIER_RULE = {
    "id": "instancegen-rc2strat-time-v1",
    "solver": "rc2stratified",
    "blo": "div",
    "cap_s": 600.0,
    "T1_max_s": 60.0,
    "T2a_max_s": 300.0,
    "T2b_max_s": 600.0,
    "boundary": "inclusive_upper",   # solve_s <= X, matching profile_hardness
}

def classify(solve_s, completed, rule=TIER_RULE) -> tuple[str, str]:  # (tier, reason)
```

Two caveats, recorded in the module docstring **and** in every manifest row:

- The existing tier tables were produced with **plain `RC2`**. `RC2Stratified`
  on the same instance can differ by a large factor in either direction. Tiers
  from this harness are **not** interchangeable with `results/hardness/*` rows —
  which is why `TIER_RULE["solver"]` and `["id"]` are recorded per instance.
- 60/300/600 are `STRATIFICATION_PLAN` §7's own open question. Recording the
  full rule dict per instance makes re-tiering a manifest re-map, not a re-solve.
  This closes the gap identified in audit §4.

#### 10.2 Harness

```
for each param point in the sweep grid, for each seed:
    inst = generate(params)
    write_wcnf(inst, path, dialect="old")
    result = solve_with_cap(path, cap_s)      # RC2Stratified
    tier, reason = classify(result.solve_s, result.completed)
    append manifest row
```

- **Two-phase, to control cost.** Phase A: cheap pilot at `cap = 30 s`, 1 seed
  per grid point, to locate where solve time starts climbing. Phase B: full cap,
  N seeds, only on the surviving band. Without this, a naive grid sweep at a
  600 s cap costs hours per grid point.
- **Timeout mechanism is decision D3.** `profile_hardness.py`'s docstring
  documents the real problem in detail: RC2 swallows SIGALRM inside the C SAT
  solver, which is why that module uses three layers (child SIGALRM ->
  progress-file thread -> `subprocess.run(timeout=cap+grace)` SIGKILL). An
  in-process timeout on `RC2Stratified` is therefore **not reliable**.
- **Four outcomes, not two:** `solved` (record `solve_s`, `final_cost`),
  `timeout` (-> T3), `hard_unsat` (**discard** — the generator produced an
  infeasible hard part), `error`.
- **Keep every candidate's row**, including T1 and T3. The solve time is already
  paid for, and T1 instances are needed as regression fixtures. "Keep T2" is a
  *filter over the manifest*, not a deletion of files.
- **No new abstraction.** `solve_with_cap` is a module-local function returning
  a dataclass. No `Oracle` protocol, no registry, no interface changes anywhere.

#### 10.3 Per-instance manifest row (`data/generated/<batch>/manifest.jsonl`)

Merges the two existing conventions — `STRATIFICATION_PLAN` §3's
`profile.*`/`tier`/`tier_reason` shape, and `PORT_NOTES` §4's "store both the
concrete value and the rule that produced it":

```json
{
  "instance": "data/generated/b01/wksat_v150_r4.30_k3_w64_h0.10_s7.wcnf",
  "instance_sha256": "…",
  "dialect": "old",
  "generator": {
    "name": "weighted_ksat",
    "version": "0.1.0",
    "params": {"n_vars":150,"clause_ratio":4.30,"k":3,"w_max":64,
               "hard_frac":0.10,"seed":7,"weight_dist":"uniform"}
  },
  "sizes": {"n_vars":150,"n_clauses":645,"n_hard":64,"n_soft":581,
            "total_soft_weight":18734,"n_distinct_weights":64},
  "profile": {"solver":"rc2stratified","blo":"div","cap_s":600.0,
              "solve_s":183.42,"completed":true,"final_cost":1207,
              "status":"ok","error":null},
  "tier": "T2a",
  "tier_reason": "60.0<solve_s<=300.0",
  "tier_rule": {"id":"instancegen-rc2strat-time-v1","solver":"rc2stratified",
                "blo":"div","cap_s":600.0,"T1_max_s":60.0,
                "T2a_max_s":300.0,"T2b_max_s":600.0,
                "boundary":"inclusive_upper"},
  "git_sha": "…",
  "created_utc": "2026-07-26T…"
}
```

- `generator.params` = the concrete values; `tier_rule` = the rule that produced
  the classification. That pairing is the `PORT_NOTES` §4 convention, and it is
  what `results/hardness/*` currently lacks (audit §4).
- `profile.final_cost` is RC2's cost = **unsatisfied soft weight**, matching the
  `PORT_NOTES` §8 sign convention exactly. It can be compared against
  `memetic_ea`'s `best_cost` with no conversion.
- `created_utc` and `git_sha` live in the **manifest only, never in the `.wcnf`
  comment header** — otherwise byte-identity (test 1, §12) fails.

### 11. Which knob is the primary difficulty dial

**Working assumption under test:** weight diversity (`w_max`) matters more than
`n_vars` for weighted instances under a core-guided solver, because
stratification layers scale with the number of distinct weights.

**Verdict: the mechanism is right, the direction is inverted.** Read from the
installed pysat (1.9.dev2).

`RC2Stratified.init_wstr`:

```python
        for s, w in six.iteritems(self.wght):
            self.wstr[w].append(s)
        # sorted list of distinct weight levels
        self.blop = sorted([w for w in self.wstr], reverse=True)
        # diversity parameter for stratification
        self.sdiv = len(self.blop) / 2.0
```

`RC2Stratified.next_level`, the loop deciding where one stratum ends:

```python
            numr = sum([len(self.wstr[w]) for w in self.blop[(self.levl + 1):]])
            sumr = sum([w * len(self.wstr[w]) for w in self.blop[(self.levl + 1):]])

            # partial BLO
            if wght > sumr and sumr != 0:
                break
            # diversity-based stratification
            if div_str and numr / float(len(self.blop) - self.levl - 1) > self.sdiv:
                break
```

`blop` is indeed indexed by **distinct weight values** — that part of the
assumption holds. But `sdiv` is *itself* `len(blop)/2`, and the diversity test
compares **selectors-per-remaining-level** against it. Work the two extremes:

- **`w_max` >> `n_soft` (maximal weight diversity).** Weights are near-unique,
  so `len(blop) ~= n_soft` and every `wstr[w]` holds one selector. Then
  `numr ~= (len(blop) - levl - 1)`, so the ratio is **~1.0**, while
  `sdiv ~= n_soft/2` — for 581 softs, ~290. `1.0 > 290` is never true. Partial
  BLO never fires either: for uniform weights the top weight is nowhere near the
  sum of the tail. The loop runs to the last level and yields **one stratum
  containing everything — i.e. plain RC2 with extra bookkeeping.**
  **Maximising `w_max` disables stratification.**
- **Few, heavily-populated weight classes** (e.g. 5 distinct weights x 100
  clauses). `len(blop) = 5`, `sdiv = 2.5`; at `levl=0`, `numr = 400` over 4
  remaining levels -> ratio 100 >> 2.5 -> break immediately. **Many genuine
  strata, many oracle calls.**

The other break condition, partial BLO (`wght > sumr`), needs a **skewed** weight
distribution — one weight dominating the sum of everything below it. A uniform
draw over `[1, w_max]` produces that essentially never, regardless of how large
`w_max` is.

**Conclusion: `w_max` is not the primary dial, and its effect is non-monotone.**
Above `w_max ~= n_soft` it saturates (distinct-weight count is capped by clause
count) and pushes *toward* the no-stratification regime. What actually controls
stratification is the **shape** of the weight distribution: how many weight
classes there are and how populated/skewed they are.

Proposed sweep axes, in priority order:

| Rank | Axis | Why |
|---|---|---|
| 1 | **`clause_ratio`** at fixed `n_vars` | Core-guided runtime tracks the number of cores extracted and their size; both are driven by soft-clause density relative to the k-SAT phase transition (~4.26 for k=3). Classic hardness dial; moves solve time by orders of magnitude across a narrow band. |
| 2 | `n_vars` | Scales the cost of each individual SAT call, roughly monotonically. |
| 3 | `hard_frac` | Shrinks the feasible region, enlarging cores — but past some point makes the hard part UNSAT, which is an *instant* solve, not a hard one. Most likely axis to blow up. |
| 4 | `w_max` / `weight_dist` | A **shape** parameter. Swept last, expected non-monotone. |

**Design consequence:** add **`weight_dist`** to the parameter set
(`"uniform"` | `"few_classes:<m>"` | `"powerlaw:<alpha>"`). It is the parameter
that actually maps onto `blop`; `w_max` alone cannot express "5 classes of 100"
versus "500 unique". This is a small addition to the requested six parameters —
decision D4.

**This should be settled by measurement, not argument.** Phase A of the sweep
varies one axis at a time from a fixed base point, and the first deliverable
after the code is a table of `solve_s` versus each axis.

### 12. Tests

| # | Test | Asserts |
|---|---|---|
| 1 | `test_determinism` | `generate(p)` + `write_wcnf(..., dialect=d)` twice -> **byte-identical files**, for `d` in `{"old","new"}`. Compares raw `bytes`, not parsed content. Also asserts two different seeds differ (guards a degenerate writer that ignores input). |
| 2 | `test_roundtrip_old` | write `dialect="old"` -> `maxsat_new.cnf.WCNF.parse_dimacs` -> same `n_vars`, same clause count, and per clause in order: same `weight`, same `lits` (order preserved), same `is_hard`. |
| 3 | `test_new_dialect_not_parseable` | `parse_dimacs` on `dialect="new"` output **raises `ValueError`**. Pins the §9.1 mismatch as an asserted fact so it cannot silently drift, and fails loudly if the parser is later extended. |
| 4 | `test_no_dropped_clause_lines` | no emitted line starts with `"0"` or `"%"`; all soft weights >= 1. Guards `PORT_NOTES` §9.5. |
| 5 | `test_dialect_required` | `write_wcnf(inst, path)` with no `dialect` raises `TypeError`; an unknown dialect raises `ValueError`. |
| 6 | `test_tiny_known_cost` | a committed 4-var hand-built instance with a hand-computed optimum: `RC2Stratified` returns that exact cost, **and** `WCNF.eval_assignment(model)` gives `total_soft_weight - sat_soft_weight == cost`. Pins the sign convention against `PORT_NOTES` §8. |
| 7 | `test_classify_boundaries` | `classify(60.0)` -> `T1`; `classify(60.001)` -> `T2a`; `classify(300.0)` -> `T2a`; `classify(600.001)` -> `T3`; `completed=False` -> `T3`. Mirrors `profile_hardness`'s inclusive-upper convention exactly. |
| 8 | `test_manifest_row_schema` | one calibration row on a trivially-fast instance is JSON round-trippable and contains **both** `generator.params` and `tier_rule` (the §4 both-or-neither rule). |

Tests 1-5, 7, 8 are sub-second. Test 6 uses a 4-var instance — also sub-second.
No test invokes a real cap; calibration sweeps are CLI runs, not tests.

### 13. Step order

One PR each, one test that fails before and passes after.

| # | Change | Test |
|---|---|---|
| 1 | `generate.py` + `GenParams` | 1 (determinism, in-memory only) |
| 2 | `wcnf_io.py` (`write_wcnf`, both dialects) | 1 (files), 2, 3, 4, 5 |
| 3 | `tiers.py` | 7 |
| 4 | `calibrate.py` + `cli.py` | 6, 8 |
| 5 | Phase A pilot sweep | *no code* — produces the `solve_s`-vs-axis table that settles §11 empirically |
| 6 | Phase B full calibration | `data/generated/<batch>/` + manifest |

Steps 1-4 touch nothing outside `instancegen/`. Nothing under `src/`, nothing in
`maxsat_new/`, nothing in flight for the port, no EA changes, no external
solver, no `Oracle` abstraction, no planted-optimum generator.

---

## 14. Open decisions

**D1 — wcnf dialect strategy.** Confirmed mismatch (§2, §9.1):
`maxsat_new.cnf.parse_dimacs` reads old format only and hard-fails on `h`.
(a) implement both dialects, calibrate + commit with `"old"`, keep `"new"` for
external interop, assert the mismatch in test 3 — **recommended**;
(b) implement `"old"` only and drop the dialect argument's second value;
(c) extend `parse_dimacs` to accept the new format — **recommended against**:
`cnf.py` is frozen, pinned bit-for-bit by the in-flight step-8 oracle test, and
`PORT_NOTES` §9 says record, don't fix.

**D2 — three tiers or four?** The ask is T1/T2/T3; the repo defines
T1/T2a/T2b/T3 at 60/300/600. (a) keep 4 buckets, treat "my T2" as
`T2a ∪ T2b` — **recommended**, stays joinable with `results/hardness/*` and with
`STRATIFICATION_PLAN` §2; (b) collapse to 3 with a single T2 = 60-600 s.

**D3 — timeout mechanism.** `profile_hardness.py` documents that RC2 swallows
SIGALRM inside the C solver, hence its subprocess + SIGKILL layering.
(a) in-process, using pysat's `expect_interrupt` + a timer thread calling
`oracle.interrupt()` — simple, no subprocess, but can hang past the cap;
(b) subprocess isolation like `profile_hardness` — reliable, but it is the
pattern the non-goals push away from. Lean: (a) plus an outer per-batch wall
budget so a hang costs one instance rather than the run. **Owner's call — this
is the non-goal boundary.**

**D4 — add `weight_dist` to the parameter set?** Per §11, `w_max` alone cannot
express "5 weight classes of 100 clauses each" versus "500 unique weights", and
it is the class structure — not `w_max` — that
`RC2Stratified.init_wstr`/`next_level` key on. One-parameter addition to the
requested six.

**D5 — calibration cap and sweep budget.** Finding T2 by definition requires
willingness to spend up to 600 s per candidate. (a) full 600 s cap — accurate,
slow; a 100-point sweep is up to ~17 CPU-hours worst case; (b) a scaled ladder
(e.g. 6/30/60 s) with tiers relabelled `T1'/T2'/T3'` and a documented scale
factor — fast, but not comparable to the MSE tables.

**D6 — do generated instances get committed?** `.gitignore`'s `data/*` line is
commented out, so `data/generated/` is **tracked by default**, and 2925 files
are already tracked under `data/` (audit §4). (a) add `data/generated/` to
`.gitignore` and commit only `manifest.jsonl` + the tiny test fixture —
**recommended**, since instances are regenerable byte-for-byte from
`(params, seed)`, which is the entire point of test 1; (b) commit the T2 set so
the corpus is pinned without a regeneration step.

**D7 — sweep base point.** One anchor is needed to vary axes around. Proposed:
`k=3`, `n_vars=150`, `clause_ratio=4.3`, `hard_frac=0.10`, `w_max=64`,
`weight_dist="uniform"`, 5 seeds.
