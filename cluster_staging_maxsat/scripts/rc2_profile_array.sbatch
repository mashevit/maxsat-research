#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=rc2-profile
#SBATCH --time=00:20:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/rc2-profile-%A_%a.out
#SBATCH --error=logs/rc2-profile-%A_%a.err

# Parameterised RC2 profiling array: one manifest line == one instance == one
# array task. `screen_mse16_array.sbatch` with the manifest, output dir and
# budget lifted into environment variables, plus resume logic.
#
# Submit through `submit_rc2_profile.sh` (it derives --array from the manifest
# and passes the variables), or by hand from scripts/:
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   sbatch --array=1-180%30 --export=ALL,MANIFEST=scripts/manifest_calib_a_rc2.txt,OUTDIR=results/profile_calib_a \
#          rc2_profile_array.sbatch
#
# Submit from scripts/: the --output path above is submit-dir relative and the
# first thing this script does is `cd ..`. Task N runs manifest line N
# (1-based, like screen_mse16_array.sbatch -- NOT the 0-based multistart one).
#
# Submit-time variables (all via --export=ALL,NAME=value):
#   MANIFEST   root-relative Slurm manifest   (default scripts/manifest_calib_a_rc2.txt)
#   OUTDIR     per-task JSONL dir             (default results/profile_calib_a)
#   CAP        RC2 wall-clock cap, s          (default 900)
#   GRACE      SIGKILL margin beyond CAP, s   (default 60)
#   LOCAL_SMOKE  1 => skip `module load`/conda (workstation smoke runs only)
#
# --time must cover CAP + GRACE plus startup. 20 min covers 900 + 60 = 960 s
# with ~4 min for `module load`, conda activation and parsing; raise it if you
# raise CAP. A task killed by --time leaves NO row (the profiler writes the
# row only after the subprocess returns); `rc2_row_state.py` then reports the
# task as run:absent and RESUME=1 resubmits it.
#
# Resume: each task appends to its own ${OUTDIR}/task_N.jsonl, so concurrent
# tasks never share a file. Before running, the task asks rc2_row_state.py
# whether that file already holds a completed row, or a censored row at a cap
# >= CAP, for this instance; if so it exits 0 without running RC2 (§4.4 of
# docs/CORPUS_CALIBRATION_GOALS.md). A failed row (status=error, empty output,
# ...) or a censored row at a lower cap is re-run and a new row appended;
# aggregation keeps the last row per instance.
#
# Provenance: ${OUTDIR}/task_N.env.json records the PySAT version, python,
# host, Slurm job id, cap and grace so a version drift on the cluster is
# detectable after the fact (the calibration holds PySAT 1.9.dev15 fixed).

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

if [[ "${LOCAL_SMOKE:-0}" != "1" ]]; then
    module load anaconda
    source activate maxsat
fi

cd ..

MANIFEST="${MANIFEST:-scripts/manifest_calib_a_rc2.txt}"
OUTDIR="${OUTDIR:-results/profile_calib_a}"
CAP="${CAP:-900}"
GRACE="${GRACE:-60}"

if [[ ! -f "$MANIFEST" ]]; then
    echo "FATAL: manifest not found: $MANIFEST (cwd $(pwd))" >&2
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

OUT="${OUTDIR}/task_${SLURM_ARRAY_TASK_ID}.jsonl"
mkdir -p "$OUTDIR"

PYSAT_VERSION=$(python -c 'import pysat; print(pysat.__version__)' 2>/dev/null || echo unknown)
echo "instance=${INSTANCE} cap=${CAP} grace=${GRACE} out=${OUT} pysat=${PYSAT_VERSION} python=$(python --version 2>&1)"

STATE=$(python scripts/rc2_row_state.py --out "$OUT" --instance "$INSTANCE" --cap "$CAP")
echo "resume_state=${STATE}"
if [[ "$STATE" == skip:* ]]; then
    echo "skip: ${OUT} already holds a valid row for this instance at cap>=${CAP}"
    echo "end=$(date -Iseconds) skipped=1"
    exit 0
fi

python - "$OUTDIR" "$SLURM_ARRAY_TASK_ID" "$INSTANCE" "$CAP" "$GRACE" "$PYSAT_VERSION" "$STATE" <<'PYEOF'
import json, os, platform, sys, datetime
outdir, task, inst, cap, grace, pysat_v, state = sys.argv[1:8]
rec = {
    "task": int(task), "instance": inst, "cap_s": float(cap), "grace_s": float(grace),
    "pysat_version": pysat_v, "python": platform.python_version(),
    "host": platform.node(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
    "slurm_array_job_id": os.environ.get("SLURM_ARRAY_JOB_ID"),
    "resume_state": state, "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
}
with open(os.path.join(outdir, f"task_{task}.env.json"), "a") as f:
    f.write(json.dumps(rec) + "\n")
PYEOF

# Same solver configuration as every committed RC2 profile: RC2(wcnf,
# solver="g3") with adapt=exhaust=minz=False (src/cli/solve_rc2_anytime.py).
# assign_tier() ignores --cap, so a 600-900 s completion is labelled T3 with
# "cap misconfigured?" -- expected, see screen_mse16_array.sbatch; the
# calibration reads `completed`/`solve_s`, not `tier`.
python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap "$CAP" \
    --grace "$GRACE" \
    --out "$OUT"

echo "end=$(date -Iseconds)"
tail -n 1 "$OUT" | cut -c1-400
