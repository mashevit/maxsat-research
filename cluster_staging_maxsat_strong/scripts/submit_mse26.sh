#!/bin/bash
# Submit one part of batch 3c (MSE 2026 memetic) on scripts/mse26_memetic_array.sbatch.
# docs/current2/MSE26_3C_RUN.md (repo). Login node, shell only (no Python).
#
#   cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs
#   DRY_RUN=1 PART=8a bash submit_mse26.sh
#   MAXSAT_GIT_SHA=<commit> PART=8a bash submit_mse26.sh
#   for p in 8a 8b 8c 16 32 64; do MAXSAT_GIT_SHA=<commit> PART=$p bash submit_mse26.sh; done
#   MAXSAT_GIT_SHA=<commit> PART=16 RESUME=1 IDS=<ids> MEM=32G bash submit_mse26.sh   # rerun one bin up
#
# Env:
#   PART       8a 8b 8c 16 32 64 (required): manifest scripts/manifest_mse26_<PART>.tsv;
#              its memory bin is the number (8a -> 8G) unless MEM is set
#   MEM        --mem for this submission (default <bin>G; set it one bin up for a
#              rerun of tasks that died for memory, MSE26_RHO_PLAN.md / notes §14)
#   THROTTLE   max concurrent tasks of this part (default: the part's share of the
#              1,000 the cluster allows at once: 8a/8b/8c 270, 16 60, 32 63, 64 67)
#   OUTDIR     root-relative shard dir (default results/mse26_memetic/tasks; one for all parts)
#   RESUME     1 => submit only the ids in IDS (task ids of this part's manifest),
#              computed on the workstation after the copy back with
#                python3 scripts/m2_results.py pending --manifest scripts/manifest_mse26_<PART>.tsv \
#                    --outdir results/mse26_memetic/tasks --summary
#   DRY_RUN    1 => checks + the command, submit nothing
#   MAXSAT_GIT_SHA  recorded in each shard's git_sha (the cluster tree is not a git
#              repo); REQUIRED for a real submission.
#
# Checks before submitting (all shell): the manifest, its sidecar and the config are
# staged; every instance file exists with the byte size of the census (the login
# node does not hash 80 GiB: each record carries the sha256 it read, and the
# readout compares it with the sidecar); scripts/manifest_mse26.upload.sha256 holds.
# Provenance: <OUTDIR minus /tasks>/provenance/submit_<PART>_<UTC stamp>.txt
# (git sha, command, sha256 of the manifest files, driver, config and src/).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PART="${PART:?set PART to one of 8a 8b 8c 16 32 64}"
case "$PART" in
    8a|8b|8c) BIN=8;  DEF_THROTTLE=270 ;;
    16)       BIN=16; DEF_THROTTLE=60 ;;
    32)       BIN=32; DEF_THROTTLE=63 ;;
    64)       BIN=64; DEF_THROTTLE=67 ;;
    *) echo "FATAL: PART must be one of 8a 8b 8c 16 32 64" >&2; exit 2 ;;
esac
MEM="${MEM:-${BIN}G}"
THROTTLE="${THROTTLE:-$DEF_THROTTLE}"
OUTDIR="${OUTDIR:-results/mse26_memetic/tasks}"
RESUME="${RESUME:-0}"
DRY_RUN="${DRY_RUN:-0}"
MANIFEST="manifest_mse26_${PART}.tsv"
SIDECAR="manifest_mse26_${PART}.tasks.csv"
ARRAY_SCRIPT="mse26_memetic_array.sbatch"

for f in "$MANIFEST" "$SIDECAR" "manifest_mse26_${PART}.sha256" "$ARRAY_SCRIPT" m2_results.py manifest_mse26.upload.sha256; do
    [[ -f "$f" ]] || { echo "FATAL: missing ${SCRIPT_DIR}/$f" >&2; exit 2; }
done
if ! command -v sbatch >/dev/null 2>&1 && [[ "$DRY_RUN" != "1" ]]; then
    echo "FATAL: sbatch not on PATH -- this is not a submit node. Use DRY_RUN=1." >&2
    exit 2
fi

(cd .. && sha256sum --quiet -c scripts/manifest_mse26.upload.sha256) \
    || { echo "FATAL: code/manifests differ from manifest_mse26.upload.sha256 -- re-upload" >&2; exit 2; }

TASK_COUNT=$(grep -c '[^[:space:]]' "$MANIFEST")
while IFS= read -r cfg; do
    [[ -f "../$cfg" ]] || { echo "FATAL: config not staged: $cfg" >&2; exit 2; }
done < <(cut -f3 "$MANIFEST" | sort -u)

# Instance files: present, with the census byte size (sidecar columns instance, bytes).
read -r ci cb < <(head -1 "$SIDECAR" | tr ',' '\n' | awk '$0=="instance"{i=NR} $0=="bytes"{b=NR} END{print i, b}')
bad=0; n_inst=0
while IFS=, read -r path bytes; do
    n_inst=$((n_inst+1))
    if [[ ! -f "../$path" ]]; then echo "MISSING   $path" >&2; bad=$((bad+1)); continue; fi
    sz=$(stat -L -c %s "../$path")
    [[ "$sz" == "$bytes" ]] || { echo "SIZE      $path: $sz bytes, census $bytes" >&2; bad=$((bad+1)); }
done < <(tail -n +2 "$SIDECAR" | cut -d, -f"$ci","$cb" | sort -u)
[[ $bad == 0 ]] || { echo "FATAL: $bad instance file(s) missing or of the wrong size" >&2; exit 2; }
echo "instances  : ${n_inst} files present with the census byte sizes"

ARRAY_SPEC="1-${TASK_COUNT}"
if [[ "$RESUME" == "1" ]]; then
    [[ -n "${IDS:-}" ]] || { echo "FATAL: RESUME=1 needs IDS=<id list> (m2_results.py pending, workstation)" >&2; exit 2; }
    ARRAY_SPEC="$IDS"
fi

EXPORTS="ALL,MANIFEST=scripts/${MANIFEST},OUTDIR=${OUTDIR},GRACE=300"
if [[ -n "${MAXSAT_GIT_SHA:-}" ]]; then
    EXPORTS+=",MAXSAT_GIT_SHA=${MAXSAT_GIT_SHA}"
elif [[ "$DRY_RUN" != "1" ]]; then
    echo "FATAL: MAXSAT_GIT_SHA is not set (the workstation commit the upload came from)." >&2
    exit 2
fi

SRC_TREE_SHA=$(cd .. && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum | sha256sum | cut -d' ' -f1)
CMD=(sbatch "--array=${ARRAY_SPEC}%${THROTTLE}" "--job-name=mse26-${PART}" "--mem=${MEM}"
     "--export=${EXPORTS}" "$ARRAY_SCRIPT")

echo "part       : ${PART}  (memory bin ${BIN} GB, --mem=${MEM})"
echo "manifest   : ${MANIFEST}  (${TASK_COUNT} rows; task N == line N)"
echo "outdir     : ${OUTDIR}"
echo "array      : ${ARRAY_SPEC}  throttle %${THROTTLE}"
echo "git sha    : ${MAXSAT_GIT_SHA:-<unset>}"
echo "src tree   : ${SRC_TREE_SHA}"
echo "command    : ${CMD[*]}"

if [[ "$DRY_RUN" == "1" ]]; then
    echo "DRY_RUN=1 -- not submitting."
    exit 0
fi

mkdir -p logs
PROV_DIR="../${OUTDIR%/tasks}/provenance"
mkdir -p "$PROV_DIR"
PROV="${PROV_DIR}/submit_${PART}_$(date -u +%Y%m%dT%H%M%SZ).txt"
{
    echo "submitted_at_utc : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host             : $(hostname)"
    echo "user             : ${USER:-}"
    echo "maxsat_git_sha   : ${MAXSAT_GIT_SHA}"
    echo "part             : ${PART}  mem ${MEM}"
    echo "resume           : ${RESUME}"
    echo "array            : ${ARRAY_SPEC}%${THROTTLE}"
    echo "command          : ${CMD[*]}"
    echo "src_tree_sha256  : ${SRC_TREE_SHA}"
    echo "--- sha256 (paths relative to the staging root)"
    (cd .. && sha256sum "scripts/${MANIFEST}" "scripts/${SIDECAR}" "scripts/manifest_mse26_${PART}.sha256" \
        "scripts/${ARRAY_SCRIPT}" scripts/submit_mse26.sh scripts/m2_results.py $(cut -f3 "scripts/${MANIFEST}" | sort -u))
    (cd .. && find src -name '*.py' | LC_ALL=C sort | xargs sha256sum)
} > "$PROV"
echo "provenance : ${PROV#../}"

OUT=$("${CMD[@]}")
echo "$OUT"
echo "sbatch           : $OUT" >> "$PROV"
