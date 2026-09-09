#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse16-screen
#SBATCH --array=1-104%20
#SBATCH --time=00:18:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse16-screen-%A_%a.out
#SBATCH --error=logs/mse16-screen-%A_%a.err

set -euo pipefail
echo "task=${SLURM_ARRAY_TASK_ID} host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ..

INSTANCE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" scripts/manifest_mse16_screen.txt)
echo "instance=${INSTANCE}"

mkdir -p results/profile_mse16

# RC2 hardness screen over the MSE-2016 ms_random / ms_crafted sample
# (5 per leaf directory, stratified by clause count -- see
# src/bench/make_mse16_manifest.py and docs/CORPUS_MSE2016_ASSESSMENT.md).
#
# --cap 900 matches the uuf250_1000c run that produced the committed tier-2
# corpus. Keep it there: the paper compares RC2 proof times across runs, and a
# cap change silently changes which instances carry an oracle at all.
#
# assign_tier() ignores --cap (docs/RC2_STATUS.md §4.6), so an instance solved
# between 600 s and 900 s is labelled T3 with reason "cap misconfigured?" even
# though it completed and carries a valid optimum. That is expected here --
# make_tier2_manifest.py's include_solved_t3 path picks them back up. Do not
# "fix" it by lowering the cap.
#
# No --bestknown: MSE-2016 ships no reference optima in this tree, so `ratio`
# and `lb_ratio` stay null. Tiers are time-based and unaffected.
python -m src.cli.profile_hardness \
    --instances "$INSTANCE" \
    --cap 900 \
    --grace 60 \
    --out results/profile_mse16/mse16_arr_task_${SLURM_ARRAY_TASK_ID}.jsonl

echo "end=$(date -Iseconds) exit=$?"
