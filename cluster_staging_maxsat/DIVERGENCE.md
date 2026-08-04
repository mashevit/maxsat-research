# Staging tree divergence from `src/`

**Date: 2026-08-05.** Full documentation of the change that caused this
divergence: [`docs/TIER2_TARGET_STOP.md`](../docs/TIER2_TARGET_STOP.md); the
work-order completion record: [`docs/TIER2_TARGET_STOP_REPORT.md`](../docs/TIER2_TARGET_STOP_REPORT.md).

`docs/TIER2_MEMETIC_PLAN.md` §2.2 asserts that the memetic dependency closure in
this staging tree is **byte-identical** to the repo copies under `src/`, and
gives a `diff -q` loop to verify it. As of the date above that invariant no
longer holds for two files, **deliberately**.

## The two divergent files

```
cluster_staging_maxsat/src/evo/memetic.py          ahead of src/evo/memetic.py
cluster_staging_maxsat/src/cli/run_memetic_shard.py  ahead of src/cli/run_memetic_shard.py
```

The other nine files of the closure (`evo/operators.py`, `evo/population.py`,
`sat/{cnf,state,walksat}.py`, `llm/{advisor,prompt}.py`,
`llm/providers/{noop,ollama}.py`) are still byte-identical and must stay that
way.

## Why

The target-cost early stop. Before this change `run_memetic` stopped only on
`time_cap` or `max_gens` (§5), and since every tier-2 config sets
`ea.max_gens: 1000000`, wall-clock was the sole stop condition — so **every run
burned its full budget even after it had already found the proven optimum.**
That is why §6.6 has to describe `wall_time_s` as "the full budget spent, not
the time at which the best assignment was first found", and why
`speedup_vs_rc2` was only an upper bound.

`run_memetic` now takes an optional `target_cost` (unsatisfied soft weight, the
RC2 convention — the same units `--oracle-cost` carries) and stops the moment
the incumbent reaches it, checked after each child's polish rather than only at
end-of-generation. `run_memetic_shard.py` gains an opt-in `--stop-at-oracle`
flag that forwards `--oracle-cost` into it, plus four additive record fields:
`stop_reason`, `time_to_target_s`, `target_cost_used`, `stop_at_oracle`.

This converts `wall_time_s` on successful runs from a constant into a real
time-to-optimum measurement — the survival curve §6.6 says needs either an
improvement callback or a budget sweep, obtained without either.

`target_cost=None` (the default) preserves the previous behaviour exactly, so
`run_experiment.py` and `run_ea.py`, which call `run_memetic` positionally and
live in the repo `src/` tree, keep working untouched. Both were re-run against
this staging `memetic.py` and produce identical solutions.

The scope of the work order that produced this change was **staging only** —
editing repo-root `src/` or `configs/` was explicitly out of scope. Hence the
divergence rather than a mirrored edit.

## The §2.2 verification loop, amended

Excluding the two divergent files keeps the identity check meaningful instead of
permanently noisy (a check that always prints `DIFFERS` is a check nobody reads).
Use this in place of the loop in `docs/TIER2_MEMETIC_PLAN.md` §2.2:

```bash
# Nine files that MUST stay byte-identical.
for f in evo/operators.py evo/population.py \
         sat/cnf.py sat/state.py sat/walksat.py \
         llm/advisor.py llm/prompt.py llm/providers/noop.py \
         llm/providers/ollama.py; do
  diff -q "src/$f" "cluster_staging_maxsat/src/$f" >/dev/null \
    && echo "IDENTICAL src/$f" || echo "DIFFERS  src/$f   <-- REGRESSION"
done

# Two files that are INTENTIONALLY ahead (target-cost stop, 2026-08-05).
# See cluster_staging_maxsat/DIVERGENCE.md. `DIFFERS` here is expected;
# `IDENTICAL` would mean the staging change was lost by an rsync or a revert.
for f in evo/memetic.py cli/run_memetic_shard.py; do
  diff -q "src/$f" "cluster_staging_maxsat/src/$f" >/dev/null \
    && echo "IDENTICAL src/$f   <-- staging change LOST" || echo "DIVERGED  src/$f   (expected)"
done
```

Note the inversion in the second loop: for those two paths, `IDENTICAL` is the
failure signal.

## To close the divergence

Port the same change into repo `src/evo/memetic.py` and
`src/cli/run_memetic_shard.py`, then restore the single eleven-file loop. Until
then, any *other* edit to those two files must be made in both trees by hand —
the mirror will not catch a drift that the diff already reports as expected.

---

## Caps mismatch: the 900 s budget is not uniform against RC2

The manifest was regenerated at a single 900 s budget
(`--budgets 900`, 390 jobs = 26 instances × 3 configs × 1 budget × 5 seeds).

> The 900 s budget matches the `uuf250_1000c` RC2 cap but **not**
> `uuf_diff_unsat`, which ran at cap 600 (`TIER2_MEMETIC_PLAN` §1.1). For those
> 8 instances the EA is given 1.5× the wall RC2 had. `rc2_cap_s` is carried in
> `tier2_oracle.csv` for exactly this reason (§1.1, `RC2_STATUS` §4.4c) —
> stratify any speed claim by it.

The 18 `uuf250_1000c` instances are the comparable half; the 8
`uuf_diff_unsat` ones are not, and a headline number pooled across all 26 hides
that. With `--stop-at-oracle` the effect is bounded — a run that reaches the
optimum stops long before either cap — but it still applies to any run that does
not, and to any claim of the form "the EA matched RC2 within the same budget".

## What downstream does not yet know

`src/bench/combine_tier2.py` lives in the repo `src/` tree and was out of scope,
so it is unchanged. The new shard fields are additive, so it will not break —
but it will **ignore** `time_to_target_s`, and its `speedup_vs_rc2` keeps
computing `rc2_solve_s / wall_time_s`. With target stops that formula is now
*correct* rather than an upper bound, which is a happy accident, not a verified
change. Surfacing `time_to_target_s` and `stop_reason` in `summary.csv` is a
follow-up task.
