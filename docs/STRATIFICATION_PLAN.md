# Instance Stratification Plan

Status: **active.** Pairs with `docs/HARNESS_PLAN.md`. Stratification
produces an instance-level tier manifest; the harness consumes it.

This document is intentionally short. The full design dialogue lives in
the chat transcript; what's reproduced here is the final scheme and the
artifact contract.

---

## 1. Why stratification is separate from the harness

`HARNESS_PLAN.md` covers how to *run a solver against an instance and
emit a JSONL row*. It does not say *which instances to run on*. The
suite YAMLs in §2.4 of that plan currently list instances by glob; once
the corpus passes ~30 instances per family, glob-by-hand stops scaling
and the choice of "what's in the suite" becomes the dominant
methodological decision.

Stratification answers that: a manifest of instances annotated by tier,
from which suites are drawn by filter. The pipeline that produces it is
a one-off meta-analysis run once per benchmark drop — not part of the
per-experiment hot path.

---

## 2. Tier definitions (RC2 baseline, time-based)

RC2 is an **exact** MaxSAT solver: it either proves an optimum within
the wall-clock cap or it does not. The honest hardness signal is
therefore *time-to-solve*, with DNF as its own bucket. Ratios of the
form `final_cost / best_known_cost` do not discriminate within the
"RC2 solved it" set because RC2's final cost *is* the optimum (ratio
~1.0 by definition). Ratio-based tiering belongs in a later pass that
profiles with an **anytime** solver (NuWLS-c, the project's memetic_ea,
etc.), where intermediate-best costs are meaningful.

The current pipeline runs RC2 with a 600 s wall-clock cap and assigns:

| Tier   | Condition                              | Purpose                                       |
| ------ | -------------------------------------- | --------------------------------------------- |
| **T1** | RC2 solves to optimum within 60 s      | Regression / smoke tests.                     |
| **T2a**| Solves within 60–300 s                 | Research zone — RC2 capable but slow.         |
| **T2b**| Solves within 300–600 s                | High research interest — RC2 marginal.        |
| **T3** | Does not solve within 600 s            | Prime LLM-guided target.                      |

**Why these boundaries.**

- 60 s separates the "instantaneous for an exact solver" set from
  everything else. Below 60 s, an LLM-guided approach has almost no
  room to compete on solve time.
- 300 s is the MSE anytime track's secondary cutoff. Instances solved
  by RC2 between 60 s and 300 s are still tractable, but slow enough
  that anytime methods can plausibly close the gap.
- 600 s is the MSE anytime track's primary cutoff. Above this, RC2 is
  no longer competitive on this instance, and the instance becomes a
  candidate for methods that don't rely on completeness.
- T3 is defined **by completion alone**. The original ratio-based
  T3 framing was incorrect for an exact-solver baseline.

**Ratio annotation (optional).** When `--bestknown <csv>` is supplied,
the script records `ratio = final_cost / best_known` for sanity
checking. For RC2 this should be ~1.0 whenever it solves. Discrepancies
indicate the best-known reference disagrees with RC2's optimum — worth
investigating per-instance, not a tier signal.

**Future pass (anytime solver).** A second profiling pass will replace
RC2 with an anytime solver, log best-so-far at multiple checkpoints,
and compute the ratio that matters for LLM-guided method comparison.
The JSONL schema is forward-compatible: the `profile.solver` field
already records which solver produced the row.

---

## 3. Artifact contract

One JSONL row per instance, append-only, written to
`results/profile/<corpus>_profile.jsonl`.

```json
{
  "instance": "data/raw/mse_2024/foo/bar.wcnf.gz",
  "size_mb": 3.2104,
  "profile": {
    "cap_s": 600.0,
    "solver": "rc2",
    "solve_s": 412.55,
    "final_cost": 8732,
    "completed": true,
    "error": null
  },
  "ratio": 1.0,
  "tier": "T2b",
  "tier_reason": "300.0<solve_s<=600.0"
}
```

Field names overlap deliberately with HARNESS_PLAN §2.3 (`instance`,
`final_cost`). Profile-specific signals live under `profile.*`.
Tier-level fields (`tier`, `ratio`, `tier_reason`) sit at the top so
filter expressions stay flat.

---

## 4. Pipeline

```
src/cli/profile_hardness.py     # this PR
└── runs RC2 per instance, writes JSONL with tier (+ ratio if bestknown)

(future) src/cli/build_bestknown.py
└── scrapes MSE rankings or computes VBS, emits data/bestknown.csv

(future) src/cli/profile_anytime.py
└── re-profiles with anytime solver; emits richer ratio signal

(future) src/cli/suites_from_manifest.py
└── reads profile JSONL, emits configs/suites/*.yaml filtered by tier
```

`profile_hardness.py` is the first script and the only one in this PR.
The others are placeholders to make the staging visible.

---

## 5. Toy-data caveat

The instances in `data/toy/` are tiny (≤ 5 vars). RC2 will solve all of
them in microseconds, so they all land in T1. **This is expected.** Toy
data verifies the pipeline plumbing — JSONL well-formed, tier function
executes, parse errors are captured into the record instead of raising
— not that the tier distribution is interesting. Tier distribution
validation happens on real MSE 2023/2024 instances locally (gitignored)
once the toy pipeline is green.

**WCNF format note.** Toy files use the old MSE format (`p wcnf <nv>
<nc> <top>` header, weight == top means hard). The newer 2022+ format
(`h` prefix for hard clauses, no header) is not portable across pysat
versions — older releases fail to parse it. Old format is the safe
default for files we commit; real MSE downloads can be in either
format and the parser handles them on a per-version basis.

---

## 6. Relationship to HARNESS_PLAN §6

When the harness implementation begins, suite YAMLs will gain an
optional `tier_filter` field:

```yaml
# configs/suites/research_t2b.yaml (forthcoming)
name: research_t2b
description: All T2b instances from the MSE 2024 profile (LLM target set).
manifest: results/profile/mse_2024_profile.jsonl
tier_filter: ["T2b", "T3"]
```

Until then, suites continue to use globs. The two systems coexist.

---

## 7. Open questions deferred to first real run

- Whether 60 / 300 / 600 are the right boundaries. The current values
  match MSE anytime cutoffs; they may need adjustment once the
  solve-time histogram on MSE 2024 instances is plotted.
- Whether RC2 should be replaced by a stronger exact solver (e.g.
  EvalMaxSAT, CASHWMaxSAT) for the profiling step. RC2 is what's
  bundled with pysat and runs without external binaries; that's why
  it's first. A second profile-run with a stronger solver is easy to
  add.
- Whether to record per-instance structural features (n_vars,
  n_clauses, n_hard, density) alongside the tier. HARNESS_PLAN §1.5
  already plans `src/cli/make_metadata.py` for this; the profile JSONL
  can be joined against `metadata.jsonl` rather than duplicating.
