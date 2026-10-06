#!/bin/bash
# Submit an RC2 profiling array over a manifest (`rc2_profile_array.sbatch`).
#
# `submit_mse16_screen.sh` generalised: the manifest, output dir, cap, grace and
# concurrency are parameters, the instances are integrity-checked against the
# manifest's .sha256 file when one exists, and RESUME=1 submits only the task
# ids that still lack a valid row.
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   DRY_RUN=1 bash submit_rc2_profile.sh        # print the sbatch command, submit nothing
#   bash submit_rc2_profile.sh                  # calib_a: 180 tasks, %30, cap 900, grace 60
#   RESUME=1 bash submit_rc2_profile.sh         # after a partial run: only unfinished ids
#   MANIFEST=manifest_calib_b_rc2.txt OUTDIR=results/profile_calib_b bash submit_rc2_profile.sh
#
# Anything after `--` is passed through to sbatch (e.g. `-- --time=00:30:00`).
#
# Submits from scripts/, which is what every array driver in this tree assumes:
# their `#SBATCH --output=logs/...` is relative to the submit directory, and
# their first action is `cd ..` to reach the tree root where src/ and data/ live.
# Task ids are 1-based: task N runs manifest line N.
#
# Env:
#   MANIFEST   manifest file in scripts/          (default manifest_calib_a_rc2.txt)
#   OUTDIR     root-relative per-task JSONL dir   (default results/profile_calib_a)
#   CAP        RC2 cap, s                         (default 900)
#   GRACE      SIGKILL margin, s                  (default 60)
#   THROTTLE   max concurrent tasks (%N)          (default 30; the cluster allows 30
#                                                 single-CPU tasks per user; 20 was
#                                                 the earlier RC2 screens' setting)
#   RESUME     1 => --array = ids reported pending by rc2_row_state.py
#   DRY_RUN    1 => print the command instead of running it
#
# Elapsed-time expectation (compute only, excluding queue delay): worst case
# ceil(tasks/THROTTLE) waves x (CAP+GRACE+startup) -- 180 tasks at %30 and
# 900 s is 6 waves x ~17 min ~= 1.7 h; CPU-hours are tasks x (CAP+GRACE)
# regardless of THROTTLE (180 x 960 s = 48 CPU-h worst case).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MANIFEST="${MANIFEST:-manifest_calib_a_rc2.txt}"
OUTDIR="${OUTDIR:-results/profile_calib_a}"
CAP="${CAP:-900}"
GRACE="${GRACE:-60}"
THROTTLE="${THROTTLE:-30}"
RESUME="${RESUME:-0}"
DRY_RUN="${DRY_RUN:-0}"
ARRAY_SCRIPT="rc2_profile_array.sbatch"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then
    shift
    PASSTHRU=("$@")
fi

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: ${SCRIPT_DIR}/${MANIFEST}" >&2
    echo "Generate it on the workstation from the repo root with:" >&2
    echo "    python -m instancegen.cli generate-grid --grid instancegen/grids/<batch>.yaml --staging-root cluster_staging_maxsat" >&2
    exit 2
fi
if [[ ! -f "$ARRAY_SCRIPT" ]]; then
    echo "FATAL: array script not found: ${SCRIPT_DIR}/${ARRAY_SCRIPT}" >&2
    exit 2
fi
if [[ ! -f rc2_row_state.py ]]; then
    echo "FATAL: rc2_row_state.py missing next to this script" >&2
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
# The instances live under data/, which is gitignored and travels by rsync --
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
    echo "Rsync the staging tree (including data/) to the cluster first." >&2
    exit 2
fi

# Byte-level check against the generator's sha256 list, when it exists: the
# calibration joins RC2 rows to manifest rows by path and cross-checks on sha,
# so a stale or truncated rsync must be caught here, not at aggregation.
SHA_FILE="${MANIFEST%.txt}.sha256"
if [[ -f "$SHA_FILE" ]]; then
    if (cd .. && sha256sum --quiet -c "scripts/${SHA_FILE}"); then
        echo "sha256     : ${TASK_COUNT} instances match ${SHA_FILE}"
    else
        echo "FATAL: instance bytes differ from ${SHA_FILE} -- re-rsync data/ or regenerate." >&2
        exit 2
    fi
else
    echo "sha256     : no ${SHA_FILE}; existence checked only"
fi

# SLURM drops a task's output with no diagnostic if the log directory is
# missing, so create it before submitting rather than after the first failure.
mkdir -p logs

ARRAY_SPEC="1-${TASK_COUNT}"
if [[ "$RESUME" == "1" ]]; then
    PENDING=$(cd .. && "${PYTHON:-python3}" scripts/rc2_row_state.py --manifest "scripts/${MANIFEST}" \
                  --outdir "$OUTDIR" --cap "$CAP" --pending --summary)
    if [[ -z "$PENDING" ]]; then
        echo "RESUME=1: every task in $MANIFEST already has a valid row in $OUTDIR at cap>=${CAP}; nothing to submit."
        exit 0
    fi
    ARRAY_SPEC="$PENDING"
fi

CMD=(sbatch "--array=${ARRAY_SPEC}%${THROTTLE}"
     "--export=ALL,MANIFEST=scripts/${MANIFEST},OUTDIR=${OUTDIR},CAP=${CAP},GRACE=${GRACE}"
     ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST  (${TASK_COUNT} rows; task N == line N)"
echo "outdir     : $OUTDIR  (root-relative)"
echo "cap/grace  : ${CAP} s + ${GRACE} s   (--time in ${ARRAY_SCRIPT} must exceed the sum)"
echo "array      : ${ARRAY_SPEC}  throttle %${THROTTLE}"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

exec "${CMD[@]}"
