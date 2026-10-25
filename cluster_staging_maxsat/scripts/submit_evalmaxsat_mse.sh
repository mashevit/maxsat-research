#!/bin/bash
# Submit the EvalMaxSAT array (evalmaxsat_array.sbatch) over the MSE 2023/2024
# sample. docs/current/MSE_EVALMAXSAT_3600.md.
#
# LOGIN-NODE SAFE: shell only (sha256sum, grep, sbatch). The cluster terminates
# Python on the login node; the driver runs inside the array tasks.
#
#   cd ~/cluster_staging_maxsat_evo/scripts
#   DRY_RUN=1 bash submit_evalmaxsat_mse.sh     # checks + print the sbatch command
#   SMOKE=1 bash submit_evalmaxsat_mse.sh       # 2 tasks, 600 s cap: ja-00000385 (optimum 37; 109 s alone and
#                                               # 293 s on a loaded workstation) and setcover-sts-data.135 (SIGTERM stop)
#   CHECK_SMOKE=1 bash submit_evalmaxsat_mse.sh # after the smoke: read its 2 rows (grep only; same OUTDIR as the smoke)
#   bash submit_evalmaxsat_mse.sh               # sample s1: 60 tasks, %1000, 3600 s + 120 s
#   IDS=1-30 bash submit_evalmaxsat_mse.sh      # only these ids (e.g. MSE 2023 = 1-30, MSE 2024 = 31-60)
#   RESUME=1 bash submit_evalmaxsat_mse.sh      # resubmit all; tasks with a final row exit at once
#
# Env: MANIFEST (in scripts/), OUTDIR, TIMEOUT (3600), GRACE (120), THROTTLE (1000; smoke 2),
#      EVALMAXSAT_BIN (default <tree root>/EvalMaxSAT/build/main/EvalMaxSAT_bin), IDS, DRY_RUN.
# Anything after `--` goes to sbatch.
#
# Worst case for s1: 60 x 3720 s = 62 CPU-h; at %1000, 1 wave x ~65 min of
# compute (queue delay not included).

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
ROOT="$(cd .. && pwd)"

SMOKE="${SMOKE:-0}"
if [[ "${CHECK_SMOKE:-0}" == "1" ]]; then
    D="${ROOT}/${OUTDIR:-results/smoke_evalmaxsat_mse}"   # OUTDIR as given to the SMOKE=1 submit
    fails=0
    for t in 1 2; do
        f="${D}/task_${t}.jsonl"
        if [[ ! -s "$f" ]]; then echo "  task ${t}: no row yet (${f})"; fails=$((fails+1)); continue; fi
        cut -c1-400 "$f" | sed "s/^/  task ${t}: /"
    done
    (( fails == 0 )) || { echo "SMOKE: rows missing (squeue -u \$USER; logs/evalmaxsat-*.err)"; exit 1; }
    grep -q '"status": "optimal"' "${D}/task_1.jsonl" && grep -q '"verified": true' "${D}/task_1.jsonl" \
        && grep -q '"opt_cost": 37,' "${D}/task_1.jsonl" \
        || { echo "SMOKE FAILED: task 1 should be a verified optimum of 37"; exit 1; }
    grep -q '"stopped_by": "sigterm"' "${D}/task_2.jsonl" \
        || { echo "SMOKE FAILED: task 2 should have been stopped by SIGTERM"; exit 1; }
    grep -q '"verified": false' "${D}/task_2.jsonl" \
        && { echo "SMOKE FAILED: task 2 incumbent failed the model check"; exit 1; }
    echo "SMOKE OK"
    exit 0
fi

if [[ "$SMOKE" == "1" ]]; then
    MANIFEST="${MANIFEST:-manifest_evalmaxsat_mse_smoke.txt}"
    OUTDIR="${OUTDIR:-results/smoke_evalmaxsat_mse}"
    TIMEOUT="${TIMEOUT:-600}"
    GRACE="${GRACE:-60}"
    THROTTLE="${THROTTLE:-2}"
    TIME_LIMIT="--time=00:15:00"
else
    MANIFEST="${MANIFEST:-manifest_evalmaxsat_mse_s1.txt}"
    OUTDIR="${OUTDIR:-results/evalmaxsat_mse_s1}"
    TIMEOUT="${TIMEOUT:-3600}"
    GRACE="${GRACE:-120}"
    THROTTLE="${THROTTLE:-1000}"
    TIME_LIMIT=""
fi
DRY_RUN="${DRY_RUN:-0}"
ARRAY_SCRIPT="evalmaxsat_array.sbatch"
BIN="${EVALMAXSAT_BIN:-${ROOT}/EvalMaxSAT/build/main/EvalMaxSAT_bin}"

PASSTHRU=()
if [[ "${1:-}" == "--" ]]; then shift; PASSTHRU=("$@"); fi

for f in "$MANIFEST" "$ARRAY_SCRIPT" "${MANIFEST%.txt}.sha256" ../src/cli/oracle_evalmaxsat.py; do
    [[ -f "$f" ]] || { echo "FATAL: missing ${SCRIPT_DIR}/${f}" >&2; exit 2; }
done
if [[ ! -x "$BIN" ]]; then
    echo "FATAL: EvalMaxSAT binary not executable: $BIN" >&2
    echo "       build it there, or pass EVALMAXSAT_BIN=/abs/path/EvalMaxSAT_bin" >&2
    exit 2
fi
if ! command -v sbatch >/dev/null 2>&1 && [[ "$DRY_RUN" != "1" ]]; then
    echo "FATAL: sbatch not on PATH -- not a submit node (DRY_RUN=1 to print only)." >&2
    exit 2
fi

TASK_COUNT=$(grep -c '[^[:space:]]' "$MANIFEST")
if (cd .. && sha256sum --quiet -c "scripts/${MANIFEST%.txt}.sha256"); then
    echo "sha256     : ${TASK_COUNT} instances match ${MANIFEST%.txt}.sha256"
else
    echo "FATAL: instances missing or different from ${MANIFEST%.txt}.sha256 -- rsync data/raw/mse_2024/ again." >&2
    exit 2
fi
mkdir -p logs

ARRAY_SPEC="${IDS:-1-${TASK_COUNT}}"
CMD=(sbatch "--array=${ARRAY_SPEC}%${THROTTLE}"
     "--export=ALL,MANIFEST=scripts/${MANIFEST},OUTDIR=${OUTDIR},TIMEOUT=${TIMEOUT},GRACE=${GRACE},EVALMAXSAT_BIN=${BIN}"
     ${TIME_LIMIT:+"$TIME_LIMIT"} ${PASSTHRU[@]+"${PASSTHRU[@]}"} "$ARRAY_SCRIPT")

echo "submit dir : $SCRIPT_DIR"
echo "manifest   : $MANIFEST  (${TASK_COUNT} rows; task N == line N)"
echo "outdir     : $OUTDIR  (root-relative)"
echo "binary     : $BIN"
echo "timeout    : ${TIMEOUT} s, then SIGTERM; SIGKILL after ${GRACE} s more"
echo "array      : ${ARRAY_SPEC}  throttle %${THROTTLE}"
echo "command    : ${CMD[*]}"
if [[ "$DRY_RUN" == "1" ]]; then echo "DRY_RUN=1 -- not submitting."; exit 0; fi
"${CMD[@]}"
