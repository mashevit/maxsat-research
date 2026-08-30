#!/bin/bash
# Submit the tier-2 local_multistart_jw_deeppolish array -- the JW-seeded arm.
#
# Mirrors scripts/submit_tier2_local_multistart.sh. The one structural
# difference is that this one must tell the array driver which manifest and
# which output directory to use: `tier2_local_multistart_array.sbatch` is
# REUSED UNCHANGED by both arms, and its defaults are the uniform arm's. It
# reads MANIFEST and OUTDIR from the environment, so the arm is selected by
# `--export` here rather than by a second copy of the sbatch file. Keeping one
# array driver is what guarantees the two arms are launched, validated and run
# by identical code -- a forked copy could drift in its --time, its grace
# margin or its STOP_AT_ORACLE default, and any of those would show up as a
# difference between the arms that has nothing to do with seeding.
#
#   bash scripts/submit_tier2_local_multistart_jw.sh            # submit
#   DRY_RUN=1 bash scripts/submit_tier2_local_multistart_jw.sh  # print, submit nothing
#
# Anything after `--` is passed through to sbatch. Note the exception below:
# a passthrough `--export` is refused rather than accepted, because sbatch
# honours the last `--export` on the line, so one would silently drop MANIFEST
# and OUTDIR and run this arm against the *uniform* manifest, writing its
# shards into the uniform arm's results tree. Set the variables in the
# environment instead -- they are folded into the export list below:
#   STOP_AT_ORACLE=0 bash scripts/submit_tier2_local_multistart_jw.sh
#
# Submits from scripts/, which is the convention every array driver in this
# tree assumes: their `#SBATCH --output=logs/...` is relative to the submit
# directory (hence scripts/logs/), and their first action is `cd ..` to reach
# the tree root where src/ and data/ live.
#
# Env:
#   MANIFEST        manifest to count and run (default manifest_tier2_local_multistart_jw.tsv)
#   OUTDIR          where shards land        (default results/tier2_local_multistart_jw/tasks)
#   THROTTLE        max concurrent tasks     (default 30, matching the memetic array)
#   GRACE           watchdog margin, seconds (default: the sbatch's own 60)
#   STOP_AT_ORACLE  1 => stop at the certified optimum (default: the sbatch's own 1)
#   MAX_TOTAL_FLIPS optional total flip cutoff; empty = off
#   DRY_RUN         1 => print the command instead of running it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MANIFEST="${MANIFEST:-manifest_tier2_local_multistart_jw.tsv}"
ARRAY_SCRIPT="tier2_local_multistart_array.sbatch"
OUTDIR="${OUTDIR:-results/tier2_local_multistart_jw/tasks}"
THROTTLE="${THROTTLE:-30}"
DRY_RUN="${DRY_RUN:-0}"
JOB_NAME="${JOB_NAME:-t2-lmsjw}"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then
    shift
    PASSTHRU=("$@")
fi
for arg in ${PASSTHRU[@]+"${PASSTHRU[@]}"}; do
    if [[ "$arg" == --export* ]]; then
        echo "FATAL: refusing a passthrough --export." >&2
        echo "sbatch honours the LAST --export, so yours would replace the one that" >&2
        echo "carries MANIFEST and OUTDIR, and this arm would run against the uniform" >&2
        echo "manifest and write into the uniform arm's results tree." >&2
        echo "Set the variables in the environment instead, e.g.:" >&2
        echo "    STOP_AT_ORACLE=0 bash scripts/submit_tier2_local_multistart_jw.sh" >&2
        exit 2
    fi
done

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: ${SCRIPT_DIR}/${MANIFEST}" >&2
    echo "Generate it from the tree root with:" >&2
    echo "    python3 scripts/make_local_multistart_manifest.py --arm jw \\" >&2
    echo "        --verify-against scripts/manifest_tier2_local_multistart.tsv" >&2
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

# The array driver runs from the tree root (it does `cd ..`), so the MANIFEST it
# is handed must be root-relative even though this script counts rows from
# scripts/. Getting this wrong is a 130-task no-op, so it is derived, not typed.
MANIFEST_FOR_JOB="scripts/${MANIFEST#scripts/}"

# Guard against the manifest and the arm disagreeing: every row must name the
# jw config_id. A manifest generated for the other arm would otherwise run here
# happily, under this arm's OUTDIR, and be indistinguishable downstream.
BAD_ROWS=$(awk -F'\t' '$4 != "local_multistart_jw_deeppolish"' "$MANIFEST" | grep -c '[^[:space:]]' || true)
if (( BAD_ROWS > 0 )); then
    echo "FATAL: ${BAD_ROWS} row(s) in ${MANIFEST} do not carry" \
         "config_id=local_multistart_jw_deeppolish." >&2
    echo "       This is the uniform arm's manifest, or a stale one. Regenerate:" >&2
    echo "    python3 scripts/make_local_multistart_manifest.py --arm jw" >&2
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

# ALL first so the submitting environment is inherited, then the arm's settings.
EXPORTS="ALL,MANIFEST=${MANIFEST_FOR_JOB},OUTDIR=${OUTDIR}"
for var in GRACE STOP_AT_ORACLE MAX_TOTAL_FLIPS; do
    if [[ -n "${!var:-}" ]]; then
        EXPORTS+=",${var}=${!var}"
    fi
done

CMD=(sbatch "--array=0-$(( TASK_COUNT - 1 ))%${THROTTLE}"
     "--job-name=${JOB_NAME}"
     "--output=logs/${JOB_NAME}-%A_%a.out"
     "--error=logs/${JOB_NAME}-%A_%a.err"
     "--export=${EXPORTS}"
     ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST  (as ${MANIFEST_FOR_JOB} to the job)"
echo "outdir     : $OUTDIR"
echo "task count : $TASK_COUNT  (array ids 0..$(( TASK_COUNT - 1 )))"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

exec "${CMD[@]}"
