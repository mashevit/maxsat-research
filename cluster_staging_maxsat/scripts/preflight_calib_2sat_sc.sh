#!/bin/bash
# Preflight for calib_2sat_sc on the cluster. docs/current/CALIB_2SAT_SC.md §9a.
#
# LOGIN-NODE SAFE: this script runs no Python and nothing heavy. The cluster
# terminates Python and other heavy work on the login node, so every check that
# needs Python or PySAT runs inside Slurm jobs on compute nodes.
#
#   cd ~/maxsat-lab/scripts
#   bash preflight_calib_2sat_sc.sh                  # login checks + dry run (seconds)
#   SUBMIT_SMOKE=1 bash preflight_calib_2sat_sc.sh   # + submit the node smoke (2 jobs)
#   CHECK_SMOKE=1 bash preflight_calib_2sat_sc.sh    # read the node smoke's report
#
# Login checks (shell only):
#   1  files      every file the array touches exists; the batch manifest has
#                 45 lines and every manifest line resolves to a staged instance
#   2  checksums  sha256sum -c for the batch and smoke manifests
#   3  sbatch     on PATH
#   -  dry run    DRY_RUN=1 of the real submission (nothing submitted)
#
# Node smoke (SUBMIT_SMOKE=1), two Slurm jobs:
#   a  a 2-task array of rc2_profile_array.sbatch on the two SMOKE instances
#      (seeds 9001/9002, not batch instances), submitted through
#      submit_rc2_profile.sh exactly as the real batch is: module load + env on a
#      compute node, partition, logs/, --export, EXPECT_PYSAT=1.9.dev3 guard.
#      Cap 60 s, grace 30 s, --time 00:05:00. Task 1 (n=2000) should complete;
#      task 2 (n=32000) should end censored with a recovered lower bound.
#   b  preflight_calib_2sat_sc_verify.sbatch, held by --dependency=afterany on
#      job a. On a compute node it checks the PySAT version and imports, reads
#      both rows and env records, and writes
#      results/smoke_calib_2sat_sc_node/PREFLIGHT_REPORT.txt.
#   CHECK_SMOKE=1 prints that report (cat only) and exits 0 iff it ends with
#   "PREFLIGHT_NODE OK".
#
# Smoke rows never enter results/profile_calib_2sat_sc/ or any readout.
# Nothing here submits the real 45-task array.

set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$ROOT"

BATCH_MANIFEST=scripts/manifest_calib_2sat_sc_rc2.txt
SMOKE_MANIFEST=scripts/manifest_calib_2sat_sc_smoke_rc2.txt
NODE_OUT=results/smoke_calib_2sat_sc_node
REPORT="${NODE_OUT}/PREFLIGHT_REPORT.txt"
FAILS=0

ok()   { echo "  ok    $*"; }
bad()  { echo "  FAIL  $*"; FAILS=$((FAILS + 1)); }
stage(){ echo; echo "== $*"; }
finish() {
    echo
    if (( FAILS > 0 )); then
        echo "PREFLIGHT FAILED: ${FAILS} problem(s). Do not submit the batch."
        exit 1
    fi
    echo "PREFLIGHT OK (login checks)"
    exit 0
}

# ---------------------------------------------------------------- report only
if [[ "${CHECK_SMOKE:-0}" == "1" ]]; then
    stage "node smoke report (${REPORT})"
    if [[ ! -f "$REPORT" ]]; then
        echo "  not there yet: the smoke jobs are queued or running (squeue -u \$USER)."
        echo "  If both jobs have left the queue, see scripts/logs/rc2-profile-*.out and"
        echo "  scripts/logs/preflight-2sat-sc-verify-*.out"
        exit 1
    fi
    sed 's/^/  /' "$REPORT"
    [[ "$(tail -n 1 "$REPORT")" == "PREFLIGHT_NODE OK" ]] && exit 0 || exit 1
fi

# ---------------------------------------------------------------- 1 files
stage "1  files"
REQUIRED=(
    src/__init__.py src/cli/__init__.py
    src/cli/profile_hardness.py src/cli/solve_rc2_anytime.py src/cli/run_opt_rc2.py
    scripts/rc2_profile_array.sbatch scripts/submit_rc2_profile.sh
    scripts/submit_rc2_calib_2sat_sc.sh scripts/rc2_row_state.py
    scripts/preflight_calib_2sat_sc_verify.sbatch
    "$BATCH_MANIFEST" "${BATCH_MANIFEST%.txt}.sha256"
    "$SMOKE_MANIFEST" "${SMOKE_MANIFEST%.txt}.sha256"
    data/generated/calib_2sat_sc/manifest.jsonl
)
for f in "${REQUIRED[@]}"; do
    [[ -f "$f" ]] && ok "$f" || bad "missing $f"
done
n_lines=$(grep -c '[^[:space:]]' "$BATCH_MANIFEST" 2>/dev/null || echo 0)
[[ "$n_lines" == 45 ]] && ok "batch manifest has 45 tasks" || bad "batch manifest has ${n_lines} tasks, expected 45"
missing=0
for m in "$BATCH_MANIFEST" "$SMOKE_MANIFEST"; do
    [[ -f "$m" ]] || continue
    while IFS= read -r rel; do
        [[ -z "$rel" ]] && continue
        [[ -f "$rel" ]] || { echo "        missing instance $rel"; missing=$((missing + 1)); }
    done < "$m"
done
(( missing == 0 )) && ok "every manifest line resolves to a staged instance" \
    || bad "${missing} instance(s) not staged (rsync data/ again)"
(( FAILS > 0 )) && finish

# ---------------------------------------------------------------- 2 checksums
stage "2  checksums"
for m in "$BATCH_MANIFEST" "$SMOKE_MANIFEST"; do
    if sha256sum --quiet -c "${m%.txt}.sha256"; then ok "${m%.txt}.sha256"; else bad "${m%.txt}.sha256 mismatch"; fi
done

# ---------------------------------------------------------------- 3 sbatch
stage "3  sbatch"
if command -v sbatch >/dev/null 2>&1; then
    ok "sbatch on PATH"
else
    bad "sbatch not on PATH (not a submit node?)"
fi

# ---------------------------------------------------------------- node smoke
if [[ "${SUBMIT_SMOKE:-0}" == "1" && $FAILS -eq 0 ]]; then
    stage "node smoke: submit the 2-task array and the verify job"
    rm -rf "$NODE_OUT"   # this script's own output only; a fresh dir defeats resume-skip
    mkdir -p scripts/logs
    sub_out=$(cd scripts && MANIFEST="$(basename "$SMOKE_MANIFEST")" OUTDIR="$NODE_OUT" \
        CAP=60 GRACE=30 THROTTLE=2 EXPECT_PYSAT=1.9.dev3 \
        bash submit_rc2_profile.sh -- --time=00:05:00 --job-name=rc2-2sat-sc-smoke --parsable 2>&1)
    echo "$sub_out" | sed 's/^/  | /'
    job=$(echo "$sub_out" | tail -n 1 | cut -d';' -f1)
    if [[ "$job" =~ ^[0-9]+$ ]]; then
        ok "smoke array job ${job}"
        vjob=$(cd scripts && sbatch --parsable --dependency="afterany:${job}" \
            --export=ALL,NODE_OUT="${NODE_OUT}",EXPECT_PYSAT=1.9.dev3 \
            preflight_calib_2sat_sc_verify.sbatch 2>&1)
        vjob="${vjob%%;*}"
        if [[ "$vjob" =~ ^[0-9]+$ ]]; then
            ok "verify job ${vjob} (runs after ${job}); then: CHECK_SMOKE=1 bash preflight_calib_2sat_sc.sh"
        else
            bad "verify job submission failed: ${vjob}"
        fi
    else
        bad "smoke array submission failed"
    fi
fi

# ---------------------------------------------------------------- dry run
stage "dry run of the real submission (nothing submitted)"
(cd scripts && env -u EXPECT_PYSAT DRY_RUN=1 bash submit_rc2_calib_2sat_sc.sh) | sed 's/^/  /'
finish
