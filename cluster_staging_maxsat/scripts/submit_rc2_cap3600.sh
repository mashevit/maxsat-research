#!/bin/bash
# RC2 re-run at a one-hour cap over every censored instance
# (manifest_rc2_cap3600.txt, built by make_rc2_cap3600_manifest.py).
#
# A thin wrapper: it fixes the batch's parameters and hands off to
# submit_rc2_profile.sh, which checks every instance exists, runs
# `sha256sum -c manifest_rc2_cap3600.sha256`, handles RESUME=1 / DRY_RUN=1 and
# submits rc2_profile_array.sbatch. The solver configuration is unchanged
# (RC2 "g3", default options); only the cap differs from the 900 s batches.
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   DRY_RUN=1 bash submit_rc2_cap3600.sh     # print the sbatch command, submit nothing
#   bash submit_rc2_cap3600.sh               # 148 tasks, %30, cap 3600 + grace 120
#   RESUME=1 bash submit_rc2_cap3600.sh      # only ids without a valid row at cap >= 3600
#
# --time 01:10:00 = 4200 s covers 3600 + 120 + ~4 min startup; a task killed
# by --time leaves no row and RESUME=1 picks it up. --mem 16G (the 900 s
# batches used 8G): an OOM kill an hour into a task loses the whole hour.
#
# Worst case: 148 x 3720 s = 153 CPU-h; at %30, 5 waves x ~70 min ~= 6 h of
# elapsed compute, excluding queue delay.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANIFEST=manifest_rc2_cap3600.txt \
OUTDIR="${OUTDIR:-results/profile_cap3600}" \
CAP=3600 \
GRACE=120 \
THROTTLE="${THROTTLE:-30}" \
exec bash "${SCRIPT_DIR}/submit_rc2_profile.sh" -- \
    --time=01:10:00 --mem=16G --job-name=rc2-cap3600 "$@"
