# Feasibility on the MSE instances — why the stack can't reach it, and the three fixes

**Date: 2026-09-06.** Written against `6335021`. Follow-on to
[`docs/TIER2_MSE_TARGETSTOP_REPORT.md`](TIER2_MSE_TARGETSTOP_REPORT.md) §3, which
established that no arm reaches a feasible assignment on
`judgment-aggregation-ja-maxham-preflib-00049-00000293.wcnf` and that fixing the
watchdog would therefore only convert null records into infeasible ones.
Companions: [`docs/TIER2_MEMETIC_PLAN.md`](TIER2_MEMETIC_PLAN.md),
[`cluster_staging_maxsat/DIVERGENCE.md`](../cluster_staging_maxsat/DIVERGENCE.md).

Every number below was measured on this instance, on the workstation, not
inferred.

**The finding in one line: feasibility on this instance is trivial — 0.04 s for a
SAT solver — and the current stack fails at it only because of how it searches.**

---

## 0. What the instance actually is

| | |
|---|---|
| variables | 18,508 |
| hard clauses | 134,142 — **21,315 binary, 112,827 ternary**, no units |
| soft clauses | **78, every one a unit**, all weight 1 |
| vars appearing in soft clauses | **78** (all of which also appear in hard clauses) |
| oracle cost | 43 (= 43 of the 78 soft units unsatisfied) |

This is judgment aggregation under `maxham`: satisfy a 2/3-SAT consistency
formula while agreeing with as many of 78 preferred literals as possible. **The
objective space is 78 binary decisions** — trivially small — sitting behind a
feasibility wall the current stack cannot climb. That asymmetry is what makes all
three fixes below pay off so disproportionately.

Reproduce:

```python
w = WCNF.parse_dimacs(INST)
hard = [c for c in w.clauses if c.is_hard]; soft = [c for c in w.clauses if not c.is_hard]
collections.Counter(len(c.lits) for c in hard)   # {2: 21315, 3: 112827}
collections.Counter(len(c.lits) for c in soft)   # {1: 78}
```

---

## 1. A SAT solver reaches feasibility in 0.04 s

```
Glucose4(bootstrap_with=hard_clauses).solve()  ->  True in 0.04 s
that arbitrary model satisfies 29/78 soft units  ->  cost 49   (oracle 43)
```

pysat is already a dependency — `src/cli/solve_rc2_anytime.py` uses RC2 — so this
needs no new package.

**An arbitrary hard-feasible model, found in 40 milliseconds, scores 49 against
the oracle's 43.** That is better than anything the five 1800 s runs produced;
their best was `hard_violations 4249` at `best_cost 78` (all 78 soft units
unsatisfied — the worst attainable value). Roughly 2.5 CPU-hours lost to a
problem a SAT solver settles in a twenty-five-thousandth of a second.

### Fix 1 — seed the population from a SAT model

Replace the random initial draw with models of the hard part. This converts the
task from *find feasibility* (which the EA demonstrably cannot do here) into
*improve inside the feasible region* (which is what an EA is for), starting 6
soft units from optimal rather than infeasible.

**The caveat that must be designed for.** Crossing two feasible parents generally
yields an **infeasible** child, and the fitness cliff at `population.py:161`

```python
fit = soft if hv == 0 else (-1e9 - 1e6 * hv)
```

will then reject essentially every child. A feasible seed therefore needs a
**repair step** after crossover — hard-only WalkSAT, or unit propagation back
into the feasible region — or the EA stalls at generation 1 with a feasible elite
and 60 rejected children per generation. Seeding without repair is not a partial
fix; it is a different failure mode.

---

## 2. `jw_priors` ignores hard clauses, so "JW seeding" is a coin flip here

`src/evo/population.py:41-43` skips every hard clause, as its docstring says
("soft-clause only"). On this instance **78 of 18,508 variables appear in any
soft clause**, so the other 18,430 hit `s == 0` and fall through to
`pri[v] = 0.5` — an unbiased coin.

Two consequences, the second more serious than the first:

1. Seeding contributes **no structural information at all** on this instance.
2. **The jw-vs-uniform ablation measures nothing on MSE instances.**
   `local_multistart_jw_deeppolish` and `local_multistart_deeppolish` are the
   same arm here, which silently voids the middle row of the three-arm design in
   `src/evo/multistart.py`'s docstring:

   ```
   memetic_deeppolish  - local_multistart_jw   population / crossover / EA
   local_multistart_jw - local_multistart      JW initialisation   <-- no-op on MSE
   memetic_deeppolish  - local_multistart      the whole package
   ```

### Fix 2 — extend JW over hard clauses

Summing `weight * 2^-|C|` over hard clauses too is what the textbook
Jeroslow–Wang heuristic does; the soft-only restriction is the anomaly. Hard
clauses need a weight convention (their `weight` is the top/infinite sentinel, so
use a finite stand-in — count them at weight 1, or at the sum of soft weights).

**This is a no-op on the 26 SATLIB tier-2 instances**, which have no hard clauses
at all, so no committed tier-2 number changes. A rare free fix — but it does
change `local_multistart_jw_*` behaviour on MSE instances, so it needs a new
config id if the existing arm's identity is to be preserved.

---

## 3. The flip loop is O(m) per flip, which is the 52 flips/sec

`walksat_polish` calls two full 134k-clause scans on **every** iteration, before
any candidate variable is evaluated:

| call | site | measured |
|---|---|---|
| `state._count_hard_violations()` | `src/sat/walksat.py:596` | **2.87 ms** |
| `state.unsat_hard_ids()` | via `pick_unsat_clause_index`, `src/sat/walksat.py:579` | **4.07 ms** |

~6.9 ms per flip in scans alone, which matches the ~19 ms/flip implied by the
observed rate. The evidence from the one completed run:

```
local_multistart_jw_longpolish: 92,966 flips / 30 restarts = ~3,099 per restart
                                over 1813 s  ->  ~52 flips/sec
```

### Fix 3 — make the flip loop incremental

`SatState` **already maintains** `clause.true_cnt` and the `pos_occ` / `neg_occ`
occurrence lists, so the machinery for incremental make/break exists and simply
is not used by these two calls. Maintaining a running hard-violation count and an
unsatisfied-hard set across flips is the standard construction and is worth
roughly three orders of magnitude in flip rate.

It also retires the problem recorded in `TIER2_MSE_TARGETSTOP_REPORT.md` §4:
`local_multistart_jw_longpolish` asked for a 1,000,000-flip cap and got ~3,099
flips per restart because the clock still bound. At incremental speeds that cap
becomes reachable and the arm becomes flip-bound as designed.

---

## 4. Recommended order

| # | fix | effort | risk to committed results |
|---|---|---|---|
| 1 | SAT-seeded population **+ repair after crossover** | medium | none — new config id |
| 2 | JW over hard clauses | low | none on SATLIB (no hard clauses) |
| 3 | incremental flip loop | high | behaviour-preserving, but it is the hot path |

(1) is the biggest single win and the only one that addresses feasibility
directly. (2) is nearly free and additionally repairs the ablation design. (3) is
the most work but is what makes the local search competitive at all rather than
merely feasible.

All three are staging-side (`cluster_staging_maxsat/src/`) and each needs its own
`DIVERGENCE.md` entry.

## 5. Caveat on scope

Everything here is measured on **one** instance, `00000293`. The 78-unit-soft /
134k-hard shape is characteristic of the judgment-aggregation family, not of
`mse23-uw-small` as a whole; the sibling `00000385` is 6,604 vars / 48,372
clauses and tiered T2a. Before generalising, run §0's clause-length and
soft-variable census across the 75 mse23 instances — it is seconds per instance
and would say how much of the set shares this shape.
