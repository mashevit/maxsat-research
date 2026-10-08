#!/bin/bash
# RC2 profiling of calib_2sat_sc: large-n, slightly supercritical random
# Max-2-SAT (45 instances; plan docs/current/CALIB_2SAT_SC.md, grid
# instancegen/grids/calib_2sat_sc.yaml).
#
# A thin wrapper: it fixes the batch's parameters and hands off to
# submit_rc2_profile.sh, which checks that every instance exists, runs
# `sha256sum -c manifest_calib_2sat_sc_rc2.sha256`, handles RESUME=1 / DRY_RUN=1
# and submits rc2_profile_array.sbatch. The measurement is the one calib_a/b
# used, unchanged:
#   - RC2(wcnf, solver="g3"), default options (src/cli/solve_rc2_anytime.py);
#   - cap 900 s of wall-clock time (SIGALRM via ITIMER_REAL) from the start,
#     plus a 60 s SIGKILL grace with lower-bound recovery from the progress file;
#   - --time 00:20:00, --mem 8G, 1 CPU, as in the sbatch header.
# One addition: EXPECT_PYSAT=1.9.dev3 (pinned here, not overridable from the
# environment) makes each task refuse to run under any
# other PySAT version, because every RC2 time this batch is compared with
# (calib_a/b, satlib) was measured under 1.9.dev3.
#
#   cd ~/maxsat-lab/scripts && mkdir -p logs
#   DRY_RUN=1 bash submit_rc2_calib_2sat_sc.sh   # print the sbatch command, submit nothing
#   bash submit_rc2_calib_2sat_sc.sh             # 45 tasks, %30, cap 900 + grace 60
#   RESUME=1 bash submit_rc2_calib_2sat_sc.sh    # only ids without a valid row at cap >= 900
#
# Worst case: 45 x 960 s = 12.0 CPU-h; at %30, 2 waves x ~20 min (the --time
# limit) = 40 min of elapsed compute, excluding queue delay.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANIFEST=manifest_calib_2sat_sc_rc2.txt \
OUTDIR="${OUTDIR:-results/profile_calib_2sat_sc}" \
CAP=900 \
GRACE=60 \
THROTTLE="${THROTTLE:-30}" \
EXPECT_PYSAT=1.9.dev3 \
exec bash "${SCRIPT_DIR}/submit_rc2_profile.sh" -- \
    --job-name=rc2-2sat-sc "$@"
