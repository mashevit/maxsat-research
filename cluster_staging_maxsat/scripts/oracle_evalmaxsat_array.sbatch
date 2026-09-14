#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=evalmaxsat
#SBATCH --array=1-856%20
#SBATCH --time=00:35:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/evalmaxsat-%A_%a.out
#SBATCH --error=logs/evalmaxsat-%A_%a.err

# EvalMaxSAT oracle over a manifest, one instance per array task.
#
# Submit from scripts/ (the --output path above is submit-dir relative; the
# first thing this script does is `cd ..`). Task N solves manifest line N
# (1-based, like screen_mse16_array.sbatch -- NOT the 0-based multistart one).
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   sbatch --array=1-3 --export=ALL,TIMEOUT=60 oracle_evalmaxsat_array.sbatch   # smoke
#   sbatch oracle_evalmaxsat_array.sbatch                                        # full
#
# Submit-time overrides (all via --export=ALL,NAME=value):
#   MANIFEST        root-relative manifest   (default scripts/manifest_evalmaxsat_more_data.txt)
#   EVALMAXSAT_BIN  the compiled solver      (default solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin
#                                             under the tree root, i.e. where it lives on the workstation)
#   TIMEOUT         per-instance cap, s      (default 1800; keep --time >= TIMEOUT + ~5 min)
#   OUTDIR          per-task JSONL dir       (default results/oracle_evalmaxsat)
#
# Each task appends to its own results/oracle_evalmaxsat/task_N.jsonl, so 20
# concurrent tasks never write the same file. The driver is resumable per file:
# resubmitting the same array id skips an instance already recorded as
# optimal/unsat and re-runs a timeout. Merge afterwards on the workstation:
#   cat results/oracle_evalmaxsat/task_*.jsonl > results/oracle_more_data.jsonl
#
# Timeout semantics: EvalMaxSAT prints no intermediate `o` lines
# (docs/ORACLE_EVALMAXSAT.md), so a task that hits TIMEOUT records
# status=timeout with best_cost=null -- no bound at all. The set-covering and
# max2sat families are expected to do that at 1800 s; that is a result, not a
# failure, and the task still exits 0.

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

MANIFEST="${MANIFEST:-scripts/manifest_evalmaxsat_more_data.txt}"
EVALMAXSAT_BIN="${EVALMAXSAT_BIN:-$PWD/solver_EvalMaxSat/EvalMaxSAT/build/main/EvalMaxSAT_bin}"
TIMEOUT="${TIMEOUT:-1800}"
OUTDIR="${OUTDIR:-results/oracle_evalmaxsat}"

if [[ ! -x "$EVALMAXSAT_BIN" ]]; then
    echo "FATAL: EvalMaxSAT_bin not executable at $EVALMAXSAT_BIN" >&2
    echo "       pass --export=ALL,EVALMAXSAT_BIN=/abs/path/to/EvalMaxSAT_bin" >&2
    exit 2
fi

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$MANIFEST")
if [[ -z "$INSTANCE" ]]; then
    echo "FATAL: manifest $MANIFEST has no line ${SLURM_ARRAY_TASK_ID}" >&2
    exit 2
fi
if [[ ! -f "$INSTANCE" ]]; then
    echo "FATAL: instance not staged: $INSTANCE (rsync data/ first)" >&2
    exit 2
fi
echo "instance=${INSTANCE} bin=${EVALMAXSAT_BIN} timeout=${TIMEOUT}"

mkdir -p "$OUTDIR"

# Plain `p cnf` files are converted to all-soft WCNF by the driver before the
# solver sees them; fed raw, EvalMaxSAT answers `s UNSATISFIABLE` in 0 s
# (docs/CORPUS_MSE2016_ASSESSMENT.md). The driver also re-checks the model
# against the formula, so opt_cost is only recorded when verified.
python src/cli/oracle_evalmaxsat.py "$INSTANCE" \
    --bin "$EVALMAXSAT_BIN" \
    --timeout "$TIMEOUT" \
    --jobs 1 \
    --out "${OUTDIR}/task_${SLURM_ARRAY_TASK_ID}.jsonl"

echo "end=$(date -Iseconds)"
tail -n 1 "${OUTDIR}/task_${SLURM_ARRAY_TASK_ID}.jsonl" | cut -c1-300
