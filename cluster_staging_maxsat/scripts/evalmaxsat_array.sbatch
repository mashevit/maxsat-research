#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=evalmaxsat
#SBATCH --time=01:10:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/evalmaxsat-%A_%a.out
#SBATCH --error=logs/evalmaxsat-%A_%a.err

# EvalMaxSAT over a manifest, one instance per array task (MSE 2023 / 2024 sample:
# docs/current/MSE_EVALMAXSAT_3600.md). Submit through submit_evalmaxsat_mse.sh.
#
# Submit from scripts/ (the --output path above is submit-dir relative); the
# first thing this script does is `cd ..`. Task N solves manifest line N (1-based).
#
# Stop rule: at TIMEOUT the driver sends SIGTERM. EvalMaxSAT then prints its
# incumbent and exits 10, and the driver model-checks it, so a capped task still
# records a verified upper bound (best_cost). SIGKILL only after GRACE more
# seconds. --time must exceed TIMEOUT + GRACE + parse/check time (01:10:00 for
# 3600 + 120).
#
# Submit-time overrides (--export=ALL,NAME=value):
#   MANIFEST        root-relative manifest      (default scripts/manifest_evalmaxsat_mse_s1.txt)
#   OUTDIR          root-relative output dir    (default results/evalmaxsat_mse_s1)
#   TIMEOUT         SIGTERM after this many s   (default 3600)
#   GRACE           SIGKILL this many s later   (default 120)
#   EVALMAXSAT_BIN  solver binary               (default <tree root>/EvalMaxSAT/build/main/EvalMaxSAT_bin)
#
# Output per task: ${OUTDIR}/task_N.jsonl (the driver's row) and task_N.env.json
# (host, Slurm ids, binary path and sha256, Python). A task whose row already
# exists with a final status (optimal, unsat, timeout) exits at once, so a
# resubmission re-runs only missing or `error` rows.

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

MANIFEST="${MANIFEST:-scripts/manifest_evalmaxsat_mse_s1.txt}"
OUTDIR="${OUTDIR:-results/evalmaxsat_mse_s1}"
TIMEOUT="${TIMEOUT:-3600}"
GRACE="${GRACE:-120}"
EVALMAXSAT_BIN="${EVALMAXSAT_BIN:-$PWD/EvalMaxSAT/build/main/EvalMaxSAT_bin}"
N="${SLURM_ARRAY_TASK_ID}"
OUT="${OUTDIR}/task_${N}.jsonl"
ENV_OUT="${OUTDIR}/task_${N}.env.json"

if [[ ! -x "$EVALMAXSAT_BIN" ]]; then
    echo "FATAL: EvalMaxSAT_bin not executable at $EVALMAXSAT_BIN" >&2
    echo "       pass --export=ALL,EVALMAXSAT_BIN=/abs/path/to/EvalMaxSAT_bin" >&2
    exit 2
fi
INSTANCE=$(sed -n "${N}p" "$MANIFEST")
if [[ -z "$INSTANCE" ]]; then
    echo "FATAL: manifest $MANIFEST has no line ${N}" >&2
    exit 2
fi
if [[ ! -f "$INSTANCE" ]]; then
    echo "FATAL: instance not staged: $INSTANCE (rsync data/ first)" >&2
    exit 2
fi
mkdir -p "$OUTDIR"

if [[ -s "$OUT" ]] && grep -q -E '"status": "(optimal|unsat|timeout)"' "$OUT"; then
    echo "SKIP: ${OUT} already has a final row"
    exit 0
fi
rm -f "$OUT"   # an `error` row (or a partial file) is replaced, never appended to

echo "instance=${INSTANCE} bin=${EVALMAXSAT_BIN} timeout=${TIMEOUT} grace=${GRACE}"
BIN_SHA=$(sha256sum "$EVALMAXSAT_BIN" | cut -d' ' -f1)
PY_V=$(python -c 'import platform; print(platform.python_version())')
cat > "$ENV_OUT" <<EOF
{"task": ${N}, "instance": "${INSTANCE}", "timeout_s": ${TIMEOUT}, "grace_s": ${GRACE}, "bin": "${EVALMAXSAT_BIN}", "bin_sha256": "${BIN_SHA}", "python": "${PY_V}", "host": "$(hostname)", "slurm_job_id": "${SLURM_JOB_ID:-}", "slurm_array_job_id": "${SLURM_ARRAY_JOB_ID:-}", "utc": "$(date -u -Iseconds)"}
EOF

python src/cli/oracle_evalmaxsat.py "$INSTANCE" \
    --bin "$EVALMAXSAT_BIN" \
    --timeout "$TIMEOUT" \
    --term-grace "$GRACE" \
    --jobs 1 \
    --rerun \
    --out "$OUT"

echo "end=$(date -Iseconds)"
tail -n 1 "$OUT" | cut -c1-400
