#!/bin/bash
# Submit the tier-2 local_multistart_deeppolish array.
#
# The array range is derived from the manifest rather than baked into the
# sbatch file, so adding or removing an (instance, seed) row cannot leave the
# range stale. Task ids are 0-based: task N runs manifest line N+1.
#
#   bash scripts/submit_tier2_local_multistart.sh            # submit
#   DRY_RUN=1 bash scripts/submit_tier2_local_multistart.sh  # print, submit nothing
#
# Anything after `--` is passed through to sbatch, e.g.:
#   bash scripts/submit_tier2_local_multistart.sh -- --export=ALL,STOP_AT_ORACLE=0
#
# Submits from scripts/, which is the convention every array driver in this
# tree assumes: their `#SBATCH --output=logs/...` is relative to the submit
# directory (hence scripts/logs/), and their first action is `cd ..` to reach
# the tree root where src/ and data/ live.
#
# Env:
#   MANIFEST   manifest to count       (default manifest_tier2_local_multistart.tsv)
#   THROTTLE   max concurrent tasks    (default 30, matching the memetic array)
#   DRY_RUN    1 => print the command instead of running it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MANIFEST="${MANIFEST:-manifest_tier2_local_multistart.tsv}"
ARRAY_SCRIPT="tier2_local_multistart_array.sbatch"
THROTTLE="${THROTTLE:-30}"
DRY_RUN="${DRY_RUN:-0}"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then
    shift
    PASSTHRU=("$@")
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: ${SCRIPT_DIR}/${MANIFEST}" >&2
    echo "Generate it from the tree root with:" >&2
    echo "    python3 scripts/make_local_multistart_manifest.py" >&2
    exit 2
fi
if [[ ! -f "$ARRAY_SCRIPT" ]]; then
    echo "FATAL: array script not found: ${SCRIPT_DIR}/${ARRAY_SCRIPT}" >&2
    exit 2
fi
if ! command -v sbatch >/dev/null 2>&1 && [[ "$DRY_RUN" != "1" ]]; then
    echo "FATAL: sbatch not on PATH -- this is not a submit node." >&2
    echo "Use DRY_RUN=1 to print the command instead." >&2
    exit 2
fi

# Count non-blank rows; the manifest has no header.
TASK_COUNT=$(grep -c '[^[:space:]]' "$MANIFEST")
if (( TASK_COUNT == 0 )); then
    echo "FATAL: $MANIFEST has no task rows." >&2
    exit 2
fi

# SLURM drops a task's output with no diagnostic if the log directory is
# missing, so create it before submitting rather than after the first failure.
mkdir -p logs

CMD=(sbatch "--array=0-$(( TASK_COUNT - 1 ))%${THROTTLE}"
     ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST"
echo "task count : $TASK_COUNT  (array ids 0..$(( TASK_COUNT - 1 )))"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

exec "${CMD[@]}"
