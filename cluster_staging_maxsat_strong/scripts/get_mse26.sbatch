#!/bin/bash
#SBATCH --job-name=mse26-dl
#SBATCH --time=06:00:00
#SBATCH --mem=2G
#SBATCH --cpus-per-task=1
#SBATCH --output=mse26-dl-%j.out
# get_mse26.sbatch - download, test, extract and size the MSE 2026 exact sets, with automatic resume.
# docs/current2/MSE_PUBLISHED_EXACT_RESULTS.md section 6 (repo).
# Needs in ~ : download_mse_full.sh and sets_mse26.txt. Run from ~ :   sbatch get_mse26.sbatch
# Then read the log:   cat $(ls -t ~/mse26-dl-*.out | head -1)
# A broken transfer (e.g. curl error 18) is resumed from the .part file, up to 20 times, 60 s apart.
# Safe to submit again: finished zips are kept (HAVE) until extracted, extracted sets are skipped.
cd "$HOME" || exit 2
export SETS_FILE=$HOME/sets_mse26.txt DEST=$HOME/mse_full26 KEEP_ZIPS=0
for f in download_mse_full.sh sets_mse26.txt; do
    [ -f "$HOME/$f" ] || { echo "FATAL: ~/$f is missing"; exit 2; }
done
done_sets=0; n_sets=0
while IFS='|' read -r name url bytes n; do
    [ -n "$name" ] || continue
    n_sets=$((n_sets+1))
    [ "$(find "$DEST/$name" -maxdepth 1 -type f 2>/dev/null | wc -l)" = "$n" ] && done_sets=$((done_sets+1))
done < "$SETS_FILE"
if [ "$done_sets" = "$n_sets" ] && [ -s "$DEST/sizes.tsv" ]; then
    echo "ALREADY_DONE  all $n_sets sets extracted, $DEST/sizes.tsv exists; nothing to do"; exit 0
fi
ok=0
for i in $(seq 1 20); do
    if bash "$HOME/download_mse_full.sh" download; then ok=1; break; fi
    echo "RETRY     attempt $i failed; resuming in ${RETRY_SLEEP:-60} s"
    sleep "${RETRY_SLEEP:-60}"
done
[ $ok = 1 ] || { echo "GAVE_UP   download failed 20 times; submit again later (it resumes)"; exit 1; }
bash "$HOME/download_mse_full.sh" test,extract,sizes || { echo "FAILED    in test/extract/sizes (see above)"; exit 1; }
echo "ALL_DONE  $(date -Iseconds)"
