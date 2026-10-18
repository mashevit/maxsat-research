#!/bin/bash
# RC2 profiling of calib_2sat_sc2: the follow-up points of calib_2sat_sc
# (15 instances: n 16000 at alpha 1.15 / 1.20, n 64000 at alpha 1.10; grid
# instancegen/grids/calib_2sat_sc2.yaml; docs/current/CALIB_2SAT_SC.md §13).
#
# The same thin wrapper as submit_rc2_calib_2sat_sc.sh, with the same measurement:
# RC2 g3 default options, cap 900 s wall clock + 60 s SIGKILL grace with
# lower-bound recovery, --time 00:20:00, --mem 8G, 1 CPU, and PySAT pinned to
# 1.9.dev3 (not overridable from the environment), so the seconds compare with
# calib_2sat_sc and calib_a/b.
#
# LOGIN-NODE SAFE: shell only (submit_rc2_profile.sh runs no Python).
#
#   cd ~/cluster_staging_maxsat_evo/scripts && mkdir -p logs
#   DRY_RUN=1 bash submit_rc2_calib_2sat_sc2.sh   # checks + print the sbatch command
#   bash submit_rc2_calib_2sat_sc2.sh             # 15 tasks, %1000, cap 900 + grace 60
#   RESUME=1 bash submit_rc2_calib_2sat_sc2.sh    # only if rows are missing; finished tasks exit at once
#
# Worst case: 15 x 960 s = 4.0 CPU-h; one wave at %1000, <= 20 min of elapsed
# compute, excluding queue delay.

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANIFEST=manifest_calib_2sat_sc2_rc2.txt \
OUTDIR="${OUTDIR:-results/profile_calib_2sat_sc2}" \
CAP=900 \
GRACE=60 \
THROTTLE="${THROTTLE:-1000}" \
EXPECT_PYSAT=1.9.dev3 \
exec bash "${SCRIPT_DIR}/submit_rc2_profile.sh" -- \
    --job-name=rc2-2sat-sc2 "$@"
