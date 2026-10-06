#!/bin/bash
# Submit the MSE-2016 RC2 hardness screen array.
#
# The array range is derived from the manifest rather than baked into the
# sbatch file, so a re-sample at a different --k cannot leave the range stale.
# Task ids are 1-based here: `screen_mse16_array.sbatch` reads its instance with
# `sed -n "${SLURM_ARRAY_TASK_ID}p"`, so task N runs manifest line N. (This is
# the full_uuf250_array convention, not the 0-based memetic one.)
#
#   bash scripts/submit_mse16_screen.sh            # submit
#   DRY_RUN=1 bash scripts/submit_mse16_screen.sh  # print, submit nothing
#
# For the fill round, point it at that manifest:
#   MANIFEST=manifest_mse16_fill.txt bash scripts/submit_mse16_screen.sh
#
# Anything after `--` is passed through to sbatch.
#
# Submits from scripts/, which is what every array driver in this tree assumes:
# their `#SBATCH --output=logs/...` is relative to the submit directory, and
# their first action is `cd ..` to reach the tree root where src/ and data/ live.
#
# Env:
#   MANIFEST   manifest to count       (default manifest_mse16_screen.txt)
#   THROTTLE   max concurrent tasks    (default 20, matching full_uuf250_array)
#   DRY_RUN    1 => print the command instead of running it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MANIFEST="${MANIFEST:-manifest_mse16_screen.txt}"
ARRAY_SCRIPT="screen_mse16_array.sbatch"
THROTTLE="${THROTTLE:-20}"
DRY_RUN="${DRY_RUN:-0}"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then
    shift
    PASSTHRU=("$@")
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: ${SCRIPT_DIR}/${MANIFEST}" >&2
    echo "Generate it on the workstation from the repo root with:" >&2
    echo "    python -m src.bench.make_mse16_manifest --k 5 --run-name screen" >&2
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

TASK_COUNT=$(grep -c '[^[:space:]]' "$MANIFEST")
if (( TASK_COUNT == 0 )); then
    echo "FATAL: $MANIFEST has no task rows." >&2
    exit 2
fi

# Every manifest line must resolve, or the task dies on a node after queueing.
# The instances live under data/, which is rsynced separately from this tree --
# a missing file here almost always means the rsync has not run yet.
MISSING=0
while IFS= read -r rel; do
    [[ -z "$rel" ]] && continue
    if [[ ! -f "../$rel" ]]; then
        echo "MISSING: $rel" >&2
        MISSING=$(( MISSING + 1 ))
    fi
done < "$MANIFEST"
if (( MISSING > 0 )); then
    echo "FATAL: $MISSING of $TASK_COUNT instances not staged under $(cd .. && pwd)/data/" >&2
    echo "Rsync the staging tree's data/ directory to the cluster first." >&2
    exit 2
fi

# SLURM drops a task's output with no diagnostic if the log directory is
# missing, so create it before submitting rather than after the first failure.
mkdir -p logs

CMD=(sbatch "--array=1-${TASK_COUNT}%${THROTTLE}"
     ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST"
echo "task count : $TASK_COUNT  (array ids 1..${TASK_COUNT})"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

exec "${CMD[@]}"
