#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=t2-lms
#SBATCH --time=00:20:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/t2-lms-%A_%a.out
#SBATCH --error=logs/t2-lms-%A_%a.err

# Tier-2 `local_multistart_deeppolish` array driver -- the no-EA ablation
# baseline for `memetic_deeppolish`.
#
# One array task == one manifest row == one (instance, seed) run.
# 26 tier-2 instances x 5 seeds = 130 tasks, 900 s solver cutoff each.
#
#   bash scripts/submit_tier2_local_multistart.sh          # preferred
#   sbatch --array=0-129%30 scripts/tier2_local_multistart_array.sbatch
#
# TASK INDEXING IS 0-BASED HERE, unlike scripts/tier2_memetic_array.sbatch,
# which is 1-based (`sed -n "${SLURM_ARRAY_TASK_ID}p"`). Array task N reads
# manifest line N+1, so the 130 tasks are 0..129. The range is not baked in as
# a `#SBATCH --array=` line, for the same reason the memetic driver does not
# bake one in: the manifest is the single source of truth for how many tasks
# exist, and `submit_tier2_local_multistart.sh` derives the range by counting
# its rows. Passing an out-of-range index is caught below, not silently skipped.
#
# Overridable at submit time:
#   MANIFEST        manifest to read            (default scripts/manifest_tier2_local_multistart.tsv)
#   OUTDIR          where shards land           (default results/tier2_local_multistart/tasks)
#   GRACE           watchdog margin in seconds  (default 60)
#   MAX_TOTAL_FLIPS optional total local-search flip cutoff; empty = off. The
#                   wall-clock budget still applies and whichever binds first
#                   ends the run.
#   STOP_AT_ORACLE  1 => stop the moment the certified optimum is reached
#                   (default 1 -- see below)
#
#   sbatch --array=0-4 --export=ALL,OUTDIR=results/t2lms_rerun \
#          scripts/tier2_local_multistart_array.sbatch
#
# STOP_AT_ORACLE DEFAULTS TO 1 HERE, and to 0 in the memetic driver. That is not
# an inconsistency: this baseline is *defined* as "restart until the certified
# optimum is reached or the budget expires", so time-to-target is its primary
# measurement rather than an opt-in benchmarking mode. Pass STOP_AT_ORACLE=0 to
# spend the whole budget, but note that `time_to_target_s`, `target_reached` and
# `flips_in_target_restart` all come back null in that mode -- the runner only
# records a target it was given as a stop condition. To compare against the
# memetic arm, that arm must have been run with STOP_AT_ORACLE=1 too.
#
# --time covers the 900 s budget plus the 60 s default GRACE (960 s = 16 min)
# with ~4 min of margin for `module load`, conda activation, instance parsing
# and writing the record. A 15 min limit does NOT fit: a task that ran to the
# cap would be killed exactly when it was about to write its shard.

set -euo pipefail

MANIFEST="${MANIFEST:-scripts/manifest_tier2_local_multistart.tsv}"
OUTDIR="${OUTDIR:-results/tier2_local_multistart/tasks}"
GRACE="${GRACE:-60}"
STOP_AT_ORACLE="${STOP_AT_ORACLE:-1}"
MAX_TOTAL_FLIPS="${MAX_TOTAL_FLIPS:-}"

echo "task=${SLURM_ARRAY_TASK_ID:-<unset>} host=$(hostname) start=$(date -Iseconds)"

if [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    echo "FATAL: SLURM_ARRAY_TASK_ID is unset -- this script must be submitted" \
         "as a job array (see submit_tier2_local_multistart.sh), not run directly." >&2
    exit 2
fi
if ! [[ "$SLURM_ARRAY_TASK_ID" =~ ^[0-9]+$ ]]; then
    echo "FATAL: SLURM_ARRAY_TASK_ID='${SLURM_ARRAY_TASK_ID}' is not a" \
         "non-negative integer." >&2
    exit 2
fi

module load anaconda
source activate maxsat

cd ..

# Single-threaded: these solvers are scalar Python and we bill one CPU per task.
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: $MANIFEST" >&2
    echo "Generate it with: python3 scripts/make_local_multistart_manifest.py" >&2
    exit 2
fi

N_TASKS=$(grep -c '[^[:space:]]' "$MANIFEST")
ROW=$(( SLURM_ARRAY_TASK_ID + 1 ))
if (( SLURM_ARRAY_TASK_ID >= N_TASKS )); then
    echo "FATAL: array task ${SLURM_ARRAY_TASK_ID} is out of range --" \
         "${MANIFEST} has ${N_TASKS} rows, so valid task ids are 0..$(( N_TASKS - 1 ))." >&2
    exit 2
fi

LINE=$(sed -n "${ROW}p" "$MANIFEST")
if [[ -z "$LINE" ]]; then
    echo "FATAL: manifest row ${ROW} (array task ${SLURM_ARRAY_TASK_ID}) is empty in $MANIFEST" >&2
    exit 2
fi

# Split with awk, not `read`. Bash treats tab as IFS *whitespace* and collapses
# runs of it, so `IFS=$'\t' read` silently shifts every column left of an empty
# field -- a row with a blank oracle_cost would be read as a valid row for a
# different seed. awk -F'\t' preserves empty fields, and mapfile preserves the
# resulting blank lines, so the emptiness is detectable rather than corrupting.
mapfile -t FIELDS < <(awk -F'\t' -v r="$ROW" 'NR==r {for (i = 1; i <= NF; i++) print $i}' "$MANIFEST")
if (( ${#FIELDS[@]} != 9 )); then
    echo "FATAL: manifest row ${ROW} has ${#FIELDS[@]} tab-separated fields, expected 9" \
         "(job_id instance config config_id seed budget_s oracle_cost tier rc2_run)." >&2
    echo "       row: ${LINE}" >&2
    exit 2
fi

JOB_ID="${FIELDS[0]}"; INSTANCE="${FIELDS[1]}"; CONFIG="${FIELDS[2]}"
CONFIG_ID="${FIELDS[3]}"; SEED="${FIELDS[4]}"; BUDGET="${FIELDS[5]}"
ORACLE="${FIELDS[6]}"; TIER="${FIELDS[7]}"; RC2_RUN="${FIELDS[8]}"

# Validate every field the run depends on. A task that cannot produce a valid
# record must fail loudly here; a silently skipped task turns into a missing
# shard that only surfaces in combine_tier2's reconciliation, hours later.
for name in JOB_ID INSTANCE CONFIG CONFIG_ID SEED BUDGET ORACLE; do
    if [[ -z "${!name}" ]]; then
        echo "FATAL: manifest row ${ROW} has an empty ${name} field." >&2
        echo "       row: ${LINE}" >&2
        exit 2
    fi
done
if [[ ! -f "$INSTANCE" ]]; then
    echo "FATAL: instance not found: $INSTANCE (row ${ROW}, cwd $(pwd))." >&2
    echo "       data/ is gitignored -- rsync it with the staging tree." >&2
    exit 2
fi
if [[ ! -f "$CONFIG" ]]; then
    echo "FATAL: solver config not found: $CONFIG (row ${ROW}, cwd $(pwd))." >&2
    exit 2
fi
if ! [[ "$SEED" =~ ^[0-9]+$ ]]; then
    echo "FATAL: seed '${SEED}' on row ${ROW} is not an integer." >&2
    exit 2
fi
if ! [[ "$ORACLE" =~ ^[0-9]+$ ]]; then
    echo "FATAL: oracle_cost '${ORACLE}' on row ${ROW} is not a non-negative" \
         "integer -- there is no certified target to stop at." >&2
    exit 2
fi

echo "job_id=${JOB_ID} row=${ROW} instance=${INSTANCE} config_id=${CONFIG_ID}" \
     "seed=${SEED} budget=${BUDGET}s oracle=${ORACLE} tier=${TIER}"

if ! mkdir -p "$OUTDIR"; then
    echo "FATAL: cannot create output directory: $OUTDIR" >&2
    exit 2
fi
if [[ ! -w "$OUTDIR" ]]; then
    echo "FATAL: output directory is not writable: $OUTDIR" >&2
    exit 2
fi

EXTRA_ARGS=()
if [[ "$STOP_AT_ORACLE" == "1" ]]; then
    EXTRA_ARGS+=(--stop-at-oracle)
fi
if [[ -n "$MAX_TOTAL_FLIPS" ]]; then
    if ! [[ "$MAX_TOTAL_FLIPS" =~ ^[0-9]+$ ]]; then
        echo "FATAL: MAX_TOTAL_FLIPS='${MAX_TOTAL_FLIPS}' is not a non-negative integer." >&2
        exit 2
    fi
    EXTRA_ARGS+=(--max-total-flips "$MAX_TOTAL_FLIPS")
fi

python -m src.cli.run_memetic_shard \
    --instance "$INSTANCE" \
    --config "$CONFIG" \
    --config-id "$CONFIG_ID" \
    --seed "$SEED" \
    --budget-s "$BUDGET" \
    --grace-s "$GRACE" \
    --oracle-cost "$ORACLE" \
    --tier "$TIER" \
    --rc2-run "$RC2_RUN" \
    --job-id "$JOB_ID" \
    --out "${OUTDIR}/${JOB_ID}.jsonl" \
    ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}

echo "end=$(date -Iseconds) exit=$?"
