#!/bin/bash
#SBATCH --job-name=mse26-unpack
#SBATCH --array=1-50
#SBATCH --time=02:00:00
#SBATCH --mem=2G
#SBATCH --cpus-per-task=1
#SBATCH --output=logs_mse26_unpack/%A_%a.out
# mse26_unpack_array.sbatch - milestone 2 of the MSE 2026 rho benchmark, as a 50-task array.
# docs/current2/MSE26_RHO_PLAN.md section 2 (repo). Shell only (xz, sha256sum, awk); no Python.
# MSE 2023 is not touched (user, 2026-10-28).
#
# Needs in ~ : mse26_work.tsv and ~/mse_full26/<set>/*.wcnf.xz (from get_mse26.sbatch).
# mse26_work.tsv: task <TAB> set <TAB> file <TAB> wcnf_bytes <TAB> unpack(0/1); 1,216 rows, packed
# into 50 tasks of about equal bytes (the largest file, 3.4 GiB, has a task to itself).
# Task N handles its rows:
#   - every file: sha256 of the decompressed content;
#   - unpack=1 (the 952 with a published optimum): also unpacked to
#     ~/mse_full26/wcnf/<set>/<hash>.wcnf (the .xz is kept), size checked against the xz index,
#     and counted: hard / soft / p lines, and whether any soft weight is not 1.
# One result row per file in ~/mse_full26/unpack_hash/p26/; a rerun skips rows already written.
#
# Run from ~ :   mkdir -p logs_mse26_unpack && sbatch mse26_unpack_array.sbatch
# Then, on the login node:   bash mse26_unpack_finish.sh   (merge, check, symlinks, ALL_DONE)
cd "$HOME" || exit 2
set -uo pipefail
S26=$HOME/mse_full26; W=$S26/wcnf; OUT=$S26/unpack_hash; WORK=$HOME/mse26_work.tsv
T=${SLURM_ARRAY_TASK_ID:?run as an array job}
[ -f "$WORK" ] || { echo "FATAL: ~/mse26_work.tsv is missing"; exit 2; }
mkdir -p "$OUT/p26"
echo "START     task $T $(date -Iseconds) on $(hostname)"

fail=0; n=0
while IFS=$'\t' read -r task set f bytes unpack; do
    [ "$task" = "$T" ] || continue
    n=$((n+1))
    h=${f%.wcnf.xz}; row=$OUT/p26/$h.tsv; src=$S26/$set/$f
    [ -s "$row" ] && continue
    if [ "$unpack" = 0 ]; then
        sha=$(xz -dc "$src" | sha256sum | cut -c1-64) || { echo "FAIL26    $set/$f: xz/sha256"; fail=$((fail+1)); continue; }
        printf '%s\t%s\t0\t\t%s\t\t\t\t\n' "$set" "$f" "$sha" > "$row.tmp"
    else
        mkdir -p "$W/$set"; dst=$W/$set/$h.wcnf
        if [ "$(stat -c %s "$dst" 2>/dev/null)" != "$bytes" ]; then
            if ! xz -dc "$src" > "$dst.part"; then
                echo "FAIL26    $set/$f: xz"; rm -f "$dst.part"; fail=$((fail+1)); continue
            fi
            mv "$dst.part" "$dst"
        fi
        got=$(stat -c %s "$dst")
        [ "$got" = "$bytes" ] || { echo "FAIL26    $set/$f: size $got != $bytes"; fail=$((fail+1)); continue; }
        sha=$(sha256sum "$dst" | cut -c1-64)
        # n_hard, n_soft, p lines, weighted (a soft clause whose weight is not 1)
        cnt=$(awk '{c=substr($0,1,1)} c=="c"||c==""{next} c=="h"{h++; next} c=="p"{p++; next}
                   {s++; if ($1!="1") w=1} END{printf "%d\t%d\t%d\t%d", h, s, p, w}' "$dst") \
            || { echo "FAIL26    $set/$f: awk"; fail=$((fail+1)); continue; }
        printf '%s\t%s\t1\tdata/raw/mse26/%s/%s.wcnf\t%s\t%s\n' "$set" "$f" "$set" "$h" "$sha" "$cnt" > "$row.tmp"
    fi
    mv "$row.tmp" "$row"
done < "$WORK"

if [ "$fail" = 0 ]; then echo "TASK_OK   task $T: $n files $(date -Iseconds)"
else echo "TASK_FAIL task $T: $fail of $n files failed; rerun with --array=$T"; exit 1; fi
