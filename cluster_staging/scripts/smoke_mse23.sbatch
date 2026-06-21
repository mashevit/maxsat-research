#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse23-smoke
#SBATCH --time=00:10:00
#SBATCH --mem=4G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse23-smoke-%j.out
#SBATCH --error=logs/mse23-smoke-%j.err

set -euo pipefail
echo "host=$(hostname) start=$(date -Iseconds)"

module load anaconda
source activate maxsat

cd ~/maxsat-lab

python -m src.cli.profile_hardness \
    --instances \
        data/raw/mse_2024/mse23-uw-small/ramsey-ram_k3_n11.ra0.wcnf \
        data/raw/mse_2024/mse23-uw-small/setcover-sts-data.135.wcnf \
        data/raw/mse_2024/mse23-uw-small/ramsey-ram_k4_n18.ra0.wcnf \
        data/raw/mse_2024/mse23-uw-small/mbd-b14_C-mbd14-0277.wcnf \
        data/raw/mse_2024/mse23-uw-small/pseudoBoolean-normalized-par32-3.opb.msat.wcnf \
    --cap 30 \
    --grace 15 \
    --bestknown data/raw/mse_2024/bestknown_mse23.csv \
    --out results/profile/mse23_smoke_cluster.jsonl

echo "end=$(date -Iseconds) exit=$?"
