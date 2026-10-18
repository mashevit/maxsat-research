#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=build-native
#SBATCH --time=00:05:00
#SBATCH --mem=1G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/build-native-%j.out
#SBATCH --error=logs/build-native-%j.err
# One-off build of the C polish core on a compute node (scripts/build_native.sh).
# Submit from scripts/:  sbatch build_native.sbatch ; then: cat logs/build-native-<id>.out
set -euo pipefail
echo "host=$(hostname) start=$(date -Iseconds)"
bash build_native.sh
echo "end=$(date -Iseconds)"
