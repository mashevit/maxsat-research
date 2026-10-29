#!/bin/bash
#SBATCH --partition=main
#SBATCH --job-name=mse26-kbig
#SBATCH --array=1-2
#SBATCH --time=02:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs/mse26-kbig-%A_%a.out
# The kernel gate on the 2 large screen-passing MSE 2026 instances that the census
# did not run (docs/current2/COMPILED_MEMETIC_PLAN.md §13): the census row
# (scripts/mse26_census.py) with no size limit and a 3,600 s kernel cap, so the row
# gives the gate's seconds, decision and kernel size, and rss_end_mb its peak RSS.
# A shell sampler logs the process VmHWM every 30 s (KBIG_MEM lines), so a task
# killed for memory still shows how far it got.
#   cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs && sbatch mse26_kernel_big.sbatch
#   (--array=1 for cd1a6257 only)
# Needs the C core built (it is, since the census) and data/raw/mse26 -> ~/mse_full26/wcnf.
set -u
T=${SLURM_ARRAY_TASK_ID:?}
cd "${SLURM_SUBMIT_DIR:-.}/.."          # submitted from scripts/, as the other drivers
[ -d src ] && [ -f scripts/mse26_census.py ] || { echo "FATAL: not in the strong tree ($(pwd))"; exit 2; }
case $T in
  1) h=cd1a62578a0445bc442e9a7dc69cbc25 ;;   # 2,029 MiB, 88.4 M clauses, screen 1.0
  2) h=d72b8cabd334fa4dccd0158384f9add0 ;;   # 594 MiB, 2.8 M clauses, screen 0.85
  *) echo "FATAL: task $T"; exit 2 ;;
esac
set_=mse26-exact-weighted
p="data/raw/mse26/$set_/$h.wcnf"
[ -f "$p" ] || { echo "FATAL: missing $p"; exit 2; }
module load anaconda
source activate maxsat
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
OUT=results/mse26_kernel_big/rows
mkdir -p "$OUT"
echo "START     task $T $h $(date -Iseconds) on $(hostname)"
python scripts/mse26_census.py --set "$set_" --hash "$h" --path "$p" --out "$OUT/$h.tsv" \
    --kernel-max-mib 1e9 --kernel-max-s 3600 &
pid=$!
while kill -0 $pid 2>/dev/null; do
    echo "KBIG_MEM  $(date +%s) $(grep -E '^Vm(HWM|RSS)' /proc/$pid/status 2>/dev/null | tr -s ' \t\n' ' ')"
    sleep 30
done
wait $pid; rc=$?
if [ $rc = 0 ] && [ -s "$OUT/$h.tsv" ]; then
    echo "ROW       $(cut -f20,21,22,23,24,26,27,28 "$OUT/$h.tsv")"   # status n_vars n_clauses gain kernel_s rss_parse rss_end error
    echo "TASK_OK   task $T $(date -Iseconds)"
else
    echo "TASK_FAIL task $T: exit $rc, no row $(date -Iseconds)"; exit 1
fi
