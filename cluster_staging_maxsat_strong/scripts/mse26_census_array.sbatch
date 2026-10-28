#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse26-census
#SBATCH --array=1-50
#SBATCH --time=01:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse26-census-%A_%a.out
# MSE 2026 census (docs/current2/COMPILED_MEMETIC_PLAN.md §9): for task T, every
# file of mse26_work.tsv with task T and unpack=1, one python process per file
# (scripts/mse26_census.py), one row in results/mse26_census/rows/<hash>.tsv.
# Rows already written are skipped, so a rerun does only what is missing.
#   cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs && sbatch mse26_census_array.sbatch
# Needs the C core built (build_native.sbatch) and data/raw/mse26 -> ~/mse_full26/wcnf.
set -u
T=${SLURM_ARRAY_TASK_ID:?}
cd "${SLURM_SUBMIT_DIR:-.}/.."          # submitted from scripts/, as the other drivers
[ -d src ] && [ -f scripts/mse26_work.tsv ] || { echo "FATAL: not in the strong tree ($(pwd))"; exit 2; }
module load anaconda
source activate maxsat
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
OUT=results/mse26_census/rows
mkdir -p "$OUT"
echo "START     task $T $(date -Iseconds) on $(hostname)"
n=0; fail=0
while IFS=$'\t' read -r task set f bytes unpack; do
    [ "$task" = "$T" ] && [ "$unpack" = 1 ] || continue
    h=${f%.wcnf.xz}
    [ -s "$OUT/$h.tsv" ] && { n=$((n+1)); continue; }
    p="data/raw/mse26/$set/$h.wcnf"
    if [ ! -f "$p" ]; then echo "MISSING   $p"; fail=$((fail+1)); continue; fi
    if python scripts/mse26_census.py --set "$set" --hash "$h" --path "$p" --out "$OUT/$h.tsv"; then
        n=$((n+1)); grep -q $'\t[A-Za-z]*Error' "$OUT/$h.tsv" && echo "ROW_ERROR $h: $(cut -f28 "$OUT/$h.tsv")"
    else
        echo "FAIL      $h (exit $?)"; fail=$((fail+1))
    fi
done < scripts/mse26_work.tsv
if [ "$fail" = 0 ]; then echo "TASK_OK   task $T: $n files $(date -Iseconds)"
else echo "TASK_FAIL task $T: $fail failed; rerun with --array=$T"; exit 1; fi
