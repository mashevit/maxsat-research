#!/bin/bash
# mse26_unpack_finish.sh - after mse26_unpack_array.sbatch: merge, check, symlinks. Login node (shell only,
# light: concatenates 1,216 one-line files). docs/current2/MSE26_RHO_PLAN.md section 2 (repo).
#   bash mse26_unpack_finish.sh
# Prints ALL_DONE, or the array task ids still missing rows (resubmit them with --array=<ids>).
# Symlinks data/raw/mse26 -> ~/mse_full26/wcnf in ~/cluster_staging_maxsat_strong and
# ~/cluster_staging_maxsat_evo (never replaces an existing path).
cd "$HOME" || exit 2
S26=$HOME/mse_full26; W=$S26/wcnf; OUT=$S26/unpack_hash; WORK=$HOME/mse26_work.tsv
[ -f "$WORK" ] || { echo "FATAL: ~/mse26_work.tsv is missing"; exit 2; }
missing=$(while IFS=$'\t' read -r task set f bytes unpack; do
              [ -s "$OUT/p26/${f%.wcnf.xz}.tsv" ] || echo "$task"
          done < "$WORK" | sort -un | paste -sd, -)
if [ -n "$missing" ]; then
    n=$(while IFS=$'\t' read -r task set f rest; do [ -s "$OUT/p26/${f%.wcnf.xz}.tsv" ] || echo x; done < "$WORK" | wc -l)
    echo "MISSING   $n files; tasks $missing"
    echo "          (still running? check squeue -u \$USER; else: sbatch --array=$missing mse26_unpack_array.sbatch)"
    exit 1
fi
{ printf 'set\tfile\tunpacked\tpath\tsha256\tn_hard\tn_soft\tp_lines\tweighted\n'
  cat "$OUT"/p26/*.tsv | sort; } > "$OUT/mse26_content.tsv"
d=$(($(wc -l < "$OUT/mse26_content.tsv") - 1)); u=$(awk -F'\t' 'NR>1&&$3==1' "$OUT/mse26_content.tsv" | wc -l)
echo "DONE26    $d/1216 hashed, $u/952 unpacked -> $OUT/mse26_content.tsv"
for T in cluster_staging_maxsat_strong cluster_staging_maxsat_evo; do
    [ -d "$HOME/$T" ] || { echo "LINK      skip $T (no such tree)"; continue; }
    L=$HOME/$T/data/raw/mse26; mkdir -p "$HOME/$T/data/raw"
    if [ -L "$L" ] && [ "$(readlink "$L")" = "$W" ]; then echo "LINK      HAVE $L"
    elif [ -e "$L" ] || [ -L "$L" ]; then echo "LINK      WARN $L exists and is not a link to $W; left alone"
    else ln -s "$W" "$L" && echo "LINK      made $L -> $W"; fi
done
grep -h '^FAIL26' "$HOME"/logs_mse26_unpack/*.out 2>/dev/null | sort -u | sed 's/^/EARLIER   /'
if [ "$d" = 1216 ] && [ "$u" = 952 ]; then echo "ALL_DONE  $(date -Iseconds)"; else echo "INCOMPLETE"; exit 1; fi
