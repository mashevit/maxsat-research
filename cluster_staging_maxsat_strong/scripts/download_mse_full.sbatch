#!/bin/bash
#SBATCH --job-name=mse-dl
#SBATCH --time=06:00:00
#SBATCH --mem=2G
#SBATCH --cpus-per-task=1
#SBATCH --output=mse-dl-%j.out
# Runs download_mse_full.sh as a job (from ~): sbatch download_mse_full.sbatch
# Choose steps with STEPS (default all), e.g. sbatch --export=ALL,STEPS=test,extract,sizes download_mse_full.sbatch
# If compute nodes have no internet (the log shows 000/none at the net step), run the download on the
# login node instead (bash download_mse_full.sh download) and use this job for test,extract,sizes.
cd "$HOME"
bash "$HOME/download_mse_full.sh" net
bash "$HOME/download_mse_full.sh" "${STEPS:-all}"
