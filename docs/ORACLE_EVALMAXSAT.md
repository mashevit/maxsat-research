# `oracle_evalmaxsat.py` — optimum costs via EvalMaxSAT

Script: `src/cli/oracle_evalmaxsat.py`
Solver: `solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin` (override with `--bin`)

Verified on a tiny CNF (optimal, cost 1, model re-checked) and on the timeout path.

## What it does

- Walks dirs/files for `.cnf` / `.wcnf` (extensions configurable with `--ext`).
- Plain `p cnf` files are converted to all-soft WCNF (`p wcnf n m m+1`, weight 1)
  in a temp file before calling `EvalMaxSAT_bin`. This avoids the trap documented
  in `CORPUS_MSE2016_ASSESSMENT.md` §"EvalMaxSAT does not accept them": fed a raw
  `p cnf` file the solver treats every clause as hard and returns a silent
  `s UNSATISFIABLE` in 0.00 s. `.wcnf` files are passed through unchanged.
- Parses the `o` / `s` / `v` lines and **re-evaluates the reported model against
  the formula**, so `opt_cost` is only set when the cost checks out
  (`verified: true`). Handles both the new 0/1-string `v` format and the old
  literal format (`--old`).
- Appends one JSON line per instance to `--out` and is **resumable**: instances
  already recorded as `optimal` / `unsat` in the file are skipped, keyed by
  sha256. `--rerun` ignores existing results. `--csv` dumps a summary table of
  the whole JSONL at the end.
- `--timeout` per instance (wall clock, default 1800 s), `--jobs N` to solve N
  instances concurrently, `--solver-arg` to pass flags through to EvalMaxSAT
  (repeatable, e.g. `--solver-arg=--TCT=600`), `--keep-wcnf` to keep the
  converted temp files.

## Output record

One JSON object per line:

| field | meaning |
|---|---|
| `instance` | path, relative to the repo root when inside it |
| `sha256` | of the original file (the resume key) |
| `format` | `cnf` or `wcnf` |
| `n_vars`, `n_hard`, `n_soft` | formula size as parsed |
| `status` | `optimal` \| `timeout` \| `unsat` \| `error` |
| `opt_cost` | optimum, only when `status == optimal` and the model verified |
| `best_cost` | last `o` line seen (equals `opt_cost` when optimal) |
| `verified` | model re-evaluation matched the reported cost; `null` if no `v` line |
| `time_s` | wall clock incl. conversion |
| `solver_time_s` | EvalMaxSAT's own `c Total time` |
| `timeout_s` | cap used |
| `note` | diagnostics (return code, model mismatch, kept wcnf path, ...) |

Exit code is 1 if any instance ended in `error`, else 0.

## Run on the whole corpus

```bash
python src/cli/oracle_evalmaxsat.py more_data \
    --out results/oracle_more_data.jsonl --csv results/oracle_more_data.csv \
    --timeout 1800 --jobs 8
```

Single files work too:

```bash
python src/cli/oracle_evalmaxsat.py a.cnf b.wcnf --timeout 600 --jobs 2
```

## Caveats from the test runs

- The 10 set-covering instances and a 120v/1200c max2sat instance all timed out
  at 60–120 s, so expect a big chunk of `more_data` to need the full cap (or
  longer) — these families are hard for core-guided solvers by design.
- EvalMaxSAT doesn't emit intermediate `o` lines (confirmed, not a stdout
  buffering issue — `stdbuf -oL` makes no difference), so on timeout
  `best_cost` is `null`. A timed-out run gives **no upper bound**; for that use
  the RC2 anytime path (`cluster_staging_maxsat/src/cli/solve_rc2_anytime.py`).
