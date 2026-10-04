#!/bin/bash
# Submit an M2 modified-deeppolish array (pilot or full pool) on the unchanged
# tier2_memetic_array.sbatch driver. docs/M2_DEEPPOLISH_RUN_PREPARATION.md (repo).
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   DRY_RUN=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
#   MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
#   RESUME=1 MANIFEST=manifest_m2_pilot.tsv OUTDIR=results/m2_pilot/tasks bash submit_m2_memetic.sh
#
# Anything after `--` is passed through to sbatch.
#
# Fixed, not overridable: STOP_AT_ORACLE=1 and GRACE=60 (the unchanged watchdog
# margin). Both are checked per shard by m2_results.py; a shard written with
# other values is classed invalid_submission.
#
# Env:
#   MANIFEST   manifest in scripts/ (required)
#   OUTDIR     root-relative shard dir (required; one per stage/manifest)
#   THROTTLE   max concurrent tasks (default 30). The limit is per array: N part
#              manifests submitted together get THROTTLE=30/N each (split tool).
#
# Split manifests: if one array cannot hold the manifest (MaxArraySize /
# max_array_tasks), scripts/split_m2_manifest.py writes part manifests under
# scripts/parts/ with LOCAL line numbers; pass one as MANIFEST=parts/<file>.tsv
# with the full manifest's OUTDIR. Do not narrow --array instead: MaxArraySize
# bounds the index itself, so --array=211-420 fails like --array=1-420.
#   RESUME     1 => submit only ids m2_results.py reports pending: missing
#              shards, infra errors, invalid submissions. Budget exhaustion and
#              late target hits are final; watchdog rows are not expected and
#              are investigated, not resubmitted automatically.
#   DRY_RUN    1 => print the command, submit nothing
#   MAXSAT_GIT_SHA  recorded in each shard's git_sha (the cluster tree is not a
#              git repo). REQUIRED for a real submission: the pilot ran without
#              it and its code version cannot be verified. The label alone is
#              a claim; the provenance file below is what lets it be checked.
#   ALLOW_NO_GIT_SHA  1 => submit without MAXSAT_GIT_SHA anyway (shards record
#              git_sha null; the provenance file is still written)
#
# Provenance: every real submission (including RESUME) first writes
# <OUTDIR minus /tasks>/provenance/submit_<UTC stamp>.txt: MAXSAT_GIT_SHA, host,
# user, sha256 of the manifest, its sidecar, the driver, every config the
# manifest names and every src/**/*.py, plus src_tree_sha256 -- one digest of
# the src/ list, reproducible on the workstation from the committed staging
# tree with
#   cd cluster_staging_maxsat && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum
# The sbatch output (job id) is appended after submission.
#
# Task ids are 1-based: task N runs manifest line N (the driver uses sed -n Np).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MANIFEST="${MANIFEST:?set MANIFEST, e.g. manifest_m2_pilot.tsv}"
OUTDIR="${OUTDIR:?set OUTDIR, e.g. results/m2_pilot/tasks}"
THROTTLE="${THROTTLE:-30}"
RESUME="${RESUME:-0}"
DRY_RUN="${DRY_RUN:-0}"
ARRAY_SCRIPT="tier2_memetic_array.sbatch"
JOB_NAME="$(basename "$MANIFEST" .tsv | sed 's/^manifest_//')"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then
    shift
    PASSTHRU=("$@")
fi

for f in "$MANIFEST" "${MANIFEST%.tsv}.tasks.csv" "${MANIFEST%.tsv}.sha256" "$ARRAY_SCRIPT" m2_results.py; do
    if [[ ! -f "$f" ]]; then
        echo "FATAL: missing ${SCRIPT_DIR}/$f (regenerate with: python3 scripts/make_m2_manifests.py)" >&2
        exit 2
    fi
done
if ! command -v sbatch >/dev/null 2>&1 && [[ "$DRY_RUN" != "1" ]]; then
    echo "FATAL: sbatch not on PATH -- this is not a submit node. Use DRY_RUN=1." >&2
    exit 2
fi

TASK_COUNT=$(grep -c '[^[:space:]]' "$MANIFEST")

# Every config the manifest names must exist in the tree, or tasks die on a node.
while IFS= read -r cfg; do
    [[ -f "../$cfg" ]] || { echo "FATAL: config not staged: $cfg" >&2; exit 2; }
done < <(cut -f3 "$MANIFEST" | sort -u)

if (cd .. && sha256sum --quiet -c "scripts/${MANIFEST%.tsv}.sha256"); then
    echo "sha256     : $(grep -c . "${MANIFEST%.tsv}.sha256") instances match ${MANIFEST%.tsv}.sha256"
else
    echo "FATAL: instance bytes differ from ${MANIFEST%.tsv}.sha256 -- re-rsync data/." >&2
    exit 2
fi

mkdir -p logs

ARRAY_SPEC="1-${TASK_COUNT}"
if [[ "$RESUME" == "1" ]]; then
    PENDING=$(cd .. && "${PYTHON:-python3}" scripts/m2_results.py pending \
                  --manifest "scripts/${MANIFEST}" --outdir "$OUTDIR" --summary)
    if [[ -z "$PENDING" ]]; then
        echo "RESUME=1: no infra/invalid tasks pending in $OUTDIR; nothing to submit."
        exit 0
    fi
    ARRAY_SPEC="$PENDING"
fi

EXPORTS="ALL,MANIFEST=scripts/${MANIFEST},OUTDIR=${OUTDIR},STOP_AT_ORACLE=1,GRACE=60"
if [[ -n "${MAXSAT_GIT_SHA:-}" ]]; then
    EXPORTS+=",MAXSAT_GIT_SHA=${MAXSAT_GIT_SHA}"
elif [[ "$DRY_RUN" != "1" && "${ALLOW_NO_GIT_SHA:-0}" != "1" ]]; then
    echo "FATAL: MAXSAT_GIT_SHA is not set. Pass the workstation commit the tree was rsynced from" >&2
    echo "       (git rev-parse HEAD), or ALLOW_NO_GIT_SHA=1 to submit with git_sha null." >&2
    exit 2
fi

# Source digest, computed root-relative so the workstation can reproduce it.
SRC_TREE_SHA=$(cd .. && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -d' ' -f1)

CMD=(sbatch "--array=${ARRAY_SPEC}%${THROTTLE}" "--job-name=${JOB_NAME}"
     "--export=${EXPORTS}" ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST  (${TASK_COUNT} rows; task N == line N)"
echo "configs    : $(cut -f4 "$MANIFEST" | sort | uniq -c | awk '{printf "%s x%s  ", $2, $1}')"
echo "outdir     : $OUTDIR  (root-relative)"
echo "array      : ${ARRAY_SPEC}  throttle %${THROTTLE}"
echo "git sha    : ${MAXSAT_GIT_SHA:-<unset>}"
echo "src tree   : ${SRC_TREE_SHA}  (sha256 of the sorted src/**/*.py sha256sum list)"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

PROV_DIR="../${OUTDIR%/tasks}/provenance"
mkdir -p "$PROV_DIR"
PROV="${PROV_DIR}/submit_$(date -u +%Y%m%dT%H%M%SZ).txt"
{
    echo "submitted_at_utc : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host             : $(hostname)"
    echo "user             : ${USER:-}"
    echo "maxsat_git_sha   : ${MAXSAT_GIT_SHA:-<unset; unverified>}"
    echo "resume           : ${RESUME}"
    echo "array            : ${ARRAY_SPEC}%${THROTTLE}"
    echo "command          : ${CMD[*]}"
    echo "src_tree_sha256  : ${SRC_TREE_SHA}"
    echo "--- sha256 (paths relative to the staging root)"
    (cd .. && sha256sum "scripts/${MANIFEST}" "scripts/${MANIFEST%.tsv}.tasks.csv" \
        "scripts/${ARRAY_SCRIPT}" scripts/m2_results.py $(cut -f3 "scripts/${MANIFEST}" | sort -u))
    if [[ "$MANIFEST" == parts/* ]]; then   # a split part: record the split and the mapping
        (cd .. && sha256sum scripts/split_m2_manifest.py scripts/parts/*.map.csv)
    fi
    (cd .. && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum)
} > "$PROV"
echo "provenance : ${PROV#../}"

OUT=$("${CMD[@]}")
echo "$OUT"
echo "sbatch           : $OUT" >> "$PROV"
