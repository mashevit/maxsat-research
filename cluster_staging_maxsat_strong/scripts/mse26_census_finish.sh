#!/bin/bash
# Merge the MSE 2026 census rows (docs/current2/COMPILED_MEMETIC_PLAN.md §9). Login node,
# shell only. Prints the task ids still missing a row, or merges
#   results/mse26_census/mse26_census.tsv  (header + 952 rows)
# and prints ALL_DONE.   cd ~/cluster_staging_maxsat_strong && bash scripts/mse26_census_finish.sh
set -u
cd "$(dirname "$0")/.." || exit 2
W=scripts/mse26_work.tsv; R=results/mse26_census/rows; O=results/mse26_census/mse26_census.tsv
[ -f "$W" ] || { echo "FATAL: $W missing"; exit 2; }
missing=$(while IFS=$'\t' read -r task set f bytes unpack; do
              [ "$unpack" = 1 ] || continue
              [ -s "$R/${f%.wcnf.xz}.tsv" ] || echo "$task"
          done < "$W" | sort -n | uniq | paste -sd, -)
if [ -n "$missing" ]; then
    echo "MISSING   rows of tasks $missing"
    echo "          (still running? squeue -u \$USER; else: cd scripts && sbatch --array=$missing mse26_census_array.sbatch)"
    exit 1
fi
HDR="set	hash	path	sha256	bytes	n_vars	n_clauses	n_lits	n_hard	n_soft	soft_w_sum	soft_w_max	max_len	weighted	nbrs_bound	nbrs_mode	screen_hit	screen_occ	screen_frac	kernel_status	kernel_n_vars	kernel_n_clauses	kernel_gain	kernel_s	parse_s	rss_parse_mb	rss_end_mb	error"
{ echo "$HDR"; while IFS=$'\t' read -r task set f bytes unpack; do
      [ "$unpack" = 1 ] && cat "$R/${f%.wcnf.xz}.tsv"; done < "$W"; } > "$O"
rows=$(($(wc -l < "$O") - 1)); errs=$(awk -F'\t' 'NR>1 && $28!=""' "$O" | wc -l)
echo "CENSUS    $rows rows, $errs with an error -> $O"
[ "$rows" = 952 ] && echo "ALL_DONE  $(date -Iseconds)" || { echo "INCOMPLETE"; exit 1; }
