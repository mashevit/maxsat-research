# Step 01 notes — cnf.py port

Implements Step 1 of PORT_NOTES.md §10.

## Files created
- `maxsat_new/__init__.py` — package marker; `__version__ = "0.1.0"`; sets
  `OMP_NUM_THREADS=1` at import via `os.environ.setdefault`.
- `maxsat_new/cnf.py` — `Clause`, `WCNF`, `WCNF.parse_dimacs`, `WCNF.eval_assignment`.
- `maxsat_new/tests/data/mini.wcnf` — 5 vars, 8 clauses (3 hard, 5 soft), old MSE
  format, `top=100`.
- `maxsat_new/tests/test_cnf.py` — one test: parse + structure + `eval_assignment`.

## Ported vs dropped (from src/sat/cnf.py @ 1e3eaaf)
- Ported: `Clause`, `WCNF.__init__`, `parse_dimacs`, `eval_assignment`. Added type
  annotations; module docstring records the port source per the porting rule.
- Dropped `true_count_per_clause` — unused on the EA path (PORT_NOTES §3).
- Did **not** port the `src/cli/run_ea.py:24-79` fallback `_parse_wcnf` — redundant
  second parser (PORT_NOTES §3).
- No import from `src/`. Standalone.

## Deviation from PORT_NOTES §3
None on the port map. One tiny cleanup not called out in §3: the source's
"sloppy clause count" branch (`if len(clauses) != n_clauses: pass`) is replaced by a
comment — same behavior (no enforcement, no warning), no dead `pass`. Behavior
unchanged.

## Replicated-bug comments added (PORT_NOTES §9, replicated not fixed)
- `cnf.py` `parse_dimacs`, at the skip filter: comment tagging **§9.5** — the
  `startswith("0")`/`startswith("%")` filter also drops any line starting with those
  characters, including a stray clause line beginning with token `0...`. Kept exactly.
- `cnf.py` `parse_dimacs`, CNF branch: comment tagging **§9.6** — `.cnf` clauses load
  as soft, `weight = 1`, `is_hard = False`. Kept exactly.

## Test output
```
$ python -m pytest maxsat_new/tests -q
.                                                                        [100%]
1 passed in 0.01s
```
Fails-before holds: the test imports `maxsat_new.cnf`, which did not exist prior to
this step (ImportError). Note: `pytest` was not installed in the `maxsat` conda env;
installed it (`pytest 9.1.1`) to run the suite.

## Known assignment used by the test
`assign01 = [0, 1, 0, 0, 1, 1]` (x1=1,x2=0,x3=0,x4=1,x5=1) →
`eval_assignment` = `(sat_w=312, hard_v=0, soft_v=2)`. All 3 hard clauses satisfied
(100 each = 300); soft satisfied = 3+5+4 = 12; total 312. Two soft clauses unsat
(`w2: x3`, `w1: x2 ∨ ¬x5`).
