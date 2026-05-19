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

Stratification answers that: a manifest of instances annotated by tier
and ratio, from which suites are drawn by filter. The pipeline that
produces it is a one-off meta-analysis run once per benchmark drop —
not part of the per-experiment hot path.

---

## 2. Tier definitions

Each instance is profiled by running RC2 (the strongest exact MaxSAT
baseline in pysat) with a 600 s wall-clock cap and checkpoints at 60 s,
300 s, 600 s. The ratio is `final_cost / best_known_cost`, where
`best_known_cost` is taken from MSE rankings or a VBS computed over the
top anytime solvers.

| Tier   | Condition                                                                                  | Purpose                                              |
| ------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------- |
| **T1** | First-feasible within 300 s AND ratio ≤ 1.1                                                | RC2 dominant. Regression / smoke tests.              |
| **T2a**| Feasible within 600 s AND 1.1 < ratio ≤ 2.0                                                | Research zone — moderate gap.                        |
| **T2b**| Feasible within 600 s AND ratio > 2.0                                                      | Prime training target for LLM-guided variants.       |
| **T3** | No feasible solution within 600 s                                                          | Stretch tier. Skip until T2 methodology stabilises.  |

When `best_known_cost` is unavailable for an instance, the tier is
provisional (`T2_prov` or `T3`) and a second pass computes the ratio
sub-split.

**Why these thresholds.**

- `1.1` separates "RC2 essentially won this" from "there's a measurable
  gap". Below 1.1, room for improvement is in the noise.
- `2.0` is the boundary at which the gap is large enough that LLM
  guidance has a plausible signal to extract. Sub-2 ratios are
  reachable by hyperparameter tuning alone.
- T3 is defined **by completion alone**, not by ratio. A feasible
  solution with ratio 10 is *more* interesting for LLM-guided work, not
  less — it puts the instance firmly in T2b, the prime training set.
  Excluding high-ratio feasible instances would discard signal.
- 600 s cap matches the MSE anytime track's primary cutoff (some MSE
  tracks use 60 s and 300 s; 600 s subsumes both as checkpoints).

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
    "first_feasible_s": 4.812,
    "last_improve_s": 412.55,
    "final_cost": 8732,
    "checkpoints": {"60": 9100, "300": 8810, "600": 8732},
    "completed": false,
    "wall_s": 600.04,
    "error": null
  },
  "ratio": 1.42,
  "tier": "T2a",
  "tier_reason": "1.1<ratio<=2.0"
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
└── runs RC2 per instance, writes JSONL with tier + ratio

(future) src/cli/build_bestknown.py
└── scrapes MSE rankings or computes VBS, emits data/bestknown.csv

(future) src/cli/suites_from_manifest.py
└── reads profile JSONL, emits configs/suites/*.yaml filtered by tier
```

`profile_hardness.py` runs without best-known data and produces
provisional tiers. The second pass is `--bestknown <csv>` against the
same JSONL output (re-run, overwriting).

---

## 5. Toy-data caveat

The instances in `data/toy/` are tiny (≤ 5 vars). RC2 will solve all of
them in microseconds, so they all land in T1. **This is expected.** Toy
data verifies the pipeline plumbing — that JSONL is well-formed, that
checkpoints fire, that the tier function executes without raising —
not that the tier distribution is interesting. Tier distribution
validation happens on real MSE 2023/2024 instances locally (gitignored)
once the toy pipeline is green.

---

## 6. Relationship to HARNESS_PLAN §6

When the harness implementation begins, suite YAMLs will gain an
optional `tier_filter` field:

```yaml
# configs/suites/research_t2b.yaml (forthcoming)
name: research_t2b
description: All T2b instances from the MSE 2024 profile (LLM target set).
manifest: results/profile/mse_2024_profile.jsonl
tier_filter: ["T2b"]
```

Until then, suites continue to use globs. The two systems coexist.

---

## 7. Open questions deferred to first real run

- Whether 1.1 or 1.05 is the right T1/T2 boundary. Decide after the
  ratio distribution on real MSE 2024 instances is plotted.
- Whether to checkpoint at additional time points (e.g. 30 s, 120 s)
  for finer-grained "rate of improvement" features. Current checkpoints
  are enough for tier assignment; richer curves come with the harness's
  event-driven anytime curve in HARNESS_PLAN §5.3.
- Whether non-RC2 anytime solvers (NuWLS-c, SPB-MaxSAT-c-Band) should
  also profile each instance, so tier is RC2-specific vs solver-agnostic.
  Recommend deferring until the LLM-guided variant ships.
