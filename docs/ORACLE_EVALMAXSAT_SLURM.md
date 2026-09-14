# Running the EvalMaxSAT oracle on SLURM

How to run `oracle_evalmaxsat.py` over the 856 `more_data` instances on the
cluster. The login node forbids heavy work, so the solver must run inside a
job -- and at an 1800 s cap over 856 instances that means an **array** job
(one instance per task), not one long job.

Companion to `docs/ORACLE_EVALMAXSAT.md` (the driver itself). Added in
`22ee3c3`.

## Files in the staging tree

| file | role |
|---|---|
| `cluster_staging_maxsat/scripts/oracle_evalmaxsat_array.sbatch` | the job script |
| `cluster_staging_maxsat/scripts/manifest_evalmaxsat_more_data.txt` | 856 lines, `data/more_data/...`; line N = array task N (**1-based**, like `screen_mse16_array.sbatch`, not the 0-based multistart driver) |
| `cluster_staging_maxsat/src/cli/oracle_evalmaxsat.py` | copy of the driver -- stdlib-only, so the `maxsat` conda env suffices; no PySAT needed |

## The sbatch

```bash
#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=evalmaxsat
#SBATCH --array=1-856%20
#SBATCH --time=00:35:00          # TIMEOUT 1800 s + margin
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/evalmaxsat-%A_%a.out
#SBATCH --error=logs/evalmaxsat-%A_%a.err

set -euo pipefail
module load anaconda
source activate maxsat
cd ..

MANIFEST="${MANIFEST:-scripts/manifest_evalmaxsat_more_data.txt}"
EVALMAXSAT_BIN="${EVALMAXSAT_BIN:-$PWD/solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin}"
TIMEOUT="${TIMEOUT:-1800}"
OUTDIR="${OUTDIR:-results/oracle_evalmaxsat}"

[[ -x "$EVALMAXSAT_BIN" ]] || { echo "FATAL: no EvalMaxSAT_bin at $EVALMAXSAT_BIN"; exit 2; }
INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST")
[[ -f "$INSTANCE" ]] || { echo "FATAL: not staged: $INSTANCE"; exit 2; }
mkdir -p "$OUTDIR"

python src/cli/oracle_evalmaxsat.py "$INSTANCE" \
    --bin "$EVALMAXSAT_BIN" --timeout "$TIMEOUT" --jobs 1 \
    --out "${OUTDIR}/task_${SLURM_ARRAY_TASK_ID}.jsonl"
```

(The committed file carries the full header comments and fail-fast checks.)

## How to run it

```bash
# 1. workstation: push the tree (data/ included -- it is not in git, so a
#    `git pull` on the cluster does not bring it)
rsync -av --exclude '__pycache__' cluster_staging_maxsat/ <user>@<cluster>:~/maxsat-lab/

# 2. cluster login node (nothing heavy runs here, only sbatch)
cd ~/maxsat-lab/scripts && mkdir -p logs

# smoke: 3 tasks, 60 s cap
sbatch --array=1-3 --export=ALL,TIMEOUT=60 oracle_evalmaxsat_array.sbatch

# full run
sbatch oracle_evalmaxsat_array.sbatch
```

### Where the binary lives

The default assumes `EvalMaxSAT_bin` sits at the same relative spot as on the
workstation, `~/maxsat-lab/solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin`.
If it was compiled elsewhere on the cluster, pass the path:

```bash
sbatch --export=ALL,EVALMAXSAT_BIN=/home/you/EvalMaxSAT/build/main/EvalMaxSAT_bin \
    oracle_evalmaxsat_array.sbatch
```

The task dies immediately with a clear message if the binary is not there,
rather than after queueing.

### Submit-time overrides (`--export=ALL,NAME=value`)

| var | default | meaning |
|---|---|---|
| `MANIFEST` | `scripts/manifest_evalmaxsat_more_data.txt` | root-relative manifest |
| `EVALMAXSAT_BIN` | `solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin` under the tree root | the compiled solver |
| `TIMEOUT` | `1800` | per-instance cap, seconds |
| `OUTDIR` | `results/oracle_evalmaxsat` | per-task JSONL directory |

If you raise `TIMEOUT`, raise `--time` to match:

```bash
sbatch --time=01:05:00 --export=ALL,TIMEOUT=3600 oracle_evalmaxsat_array.sbatch
```

## Notes

- Each task writes its own `results/oracle_evalmaxsat/task_N.jsonl`, so the
  20 concurrent tasks never share a file. Resubmitting the same array ids
  skips instances already recorded as optimal/unsat and re-runs timeouts.
  Merge on the workstation:

  ```bash
  cat results/oracle_evalmaxsat/task_*.jsonl > results/oracle_more_data.jsonl
  ```

- The driver converts plain `p cnf` to all-soft WCNF before calling the solver
  (fed raw, EvalMaxSAT answers `s UNSATISFIABLE` in 0 s -- see
  `docs/CORPUS_MSE2016_ASSESSMENT.md`) and re-checks the returned model
  against the formula, so `opt_cost` is only recorded when verified.

- A timeout gives **no bound**: EvalMaxSAT prints no intermediate `o` lines,
  so `best_cost` is `null`. Expect that for the set-covering and max2sat
  families even at 1800 s. That is a result, not a failure; the task still
  exits 0. For an upper bound on those, use the RC2 anytime path
  (`cluster_staging_maxsat/src/cli/solve_rc2_anytime.py`).

## What was verified

The task body was run locally on manifest line 1 with a 20 s cap: it ran,
converted the CNF, hit the cap, and wrote the JSONL row as expected.
`sbatch` itself was not tested from the workstation.
