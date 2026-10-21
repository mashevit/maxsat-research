#!/bin/bash
# download_mse_full.sh - fetch the full MaxSAT Evaluation 2023 and 2024 instance sets onto the cluster.
# Shell only (curl, unzip, xz): safe for the login node, and also runs inside a Slurm job
# (download_mse_full.sbatch). docs/current2/NOTES_2026-10-21_AGENDA_AND_STATS.md section 13 (repo).
#
# The four exact-track zips hold EVERY instance of both years: the anytime-track sets are subsets
# of them (checked 2026-10-21 by remote zip listing: 2023 179+160 and 2024 216+229 anytime files,
# all present in the exact zips, 2024 with identical CRCs). Members are .wcnf.xz files.
#
#   bash download_mse_full.sh net          # can this machine reach the two servers?
#   bash download_mse_full.sh download     # the four zips -> $DEST/zips (resumes; checks byte size)
#   bash download_mse_full.sh test         # unzip -t (CRC of every member) + member counts
#   bash download_mse_full.sh extract      # unzip -> $DEST/<set>/*.wcnf.xz (KEEP_ZIPS=0 deletes each zip after)
#   bash download_mse_full.sh sizes        # xz -l (reads the index only) -> $DEST/sizes.tsv
#   bash download_mse_full.sh all          # download,test,extract,sizes
#   bash download_mse_full.sh test,extract # any comma-separated list of steps
# Decompression to .wcnf is NOT done here: decide from sizes.tsv which files to expand
# (the solvers read plain .wcnf only).
#
# Env: DEST (default ~/mse_full), KEEP_ZIPS (default 1), SETS_FILE (tests only: replaces the list below).
set -euo pipefail
DEST=${DEST:-$HOME/mse_full}
KEEP_ZIPS=${KEEP_ZIPS:-1}
STEPS=${1:-all}
[ "$STEPS" = all ] && STEPS=download,test,extract,sizes

# name | url | zip bytes | members (verified 2026-10-21)
SETS=(
"mse23-exact-unweighted|https://drive.usercontent.google.com/download?id=13qDbScs9jU1VaUaq4L7qSGEUrHxC9t6d&export=download&confirm=t|1222789581|572"
"mse23-exact-weighted|https://drive.usercontent.google.com/download?id=1pKuQkuTZr7CO3GXmOGRvrMeLTOaw9Fl6&export=download&confirm=t|3140560006|558"
"mse24-exact-unweighted|https://www.cs.helsinki.fi/group/coreo/MSE2024-instances/mse24-exact-unweighted.zip|2075486968|553"
"mse24-exact-weighted|https://www.cs.helsinki.fi/group/coreo/MSE2024-instances/mse24-exact-weighted.zip|4730984681|571"
)
if [ -n "${SETS_FILE:-}" ]; then mapfile -t SETS < "$SETS_FILE"; fi

for tool in curl unzip xz; do command -v "$tool" >/dev/null || { echo "FATAL: $tool not found"; exit 2; }; done
mkdir -p "$DEST/zips"
fsize() { stat -c %s "$1" 2>/dev/null || echo 0; }

step_net() {
    for s in "${SETS[@]}"; do IFS='|' read -r name url bytes n <<< "$s"
        code=$(curl -sIL -m 30 -o /dev/null -w '%{http_code}' "$url" || echo none)
        echo "$code  $name"
    done
}

step_download() {
    for s in "${SETS[@]}"; do IFS='|' read -r name url bytes n <<< "$s"
        z=$DEST/zips/$name.zip
        if [ "$(fsize "$z")" = "$bytes" ]; then echo "HAVE      $name ($bytes bytes)"; continue; fi
        echo "DOWNLOAD  $name ($((bytes / 1048576)) MiB)"
        curl -fsSL --retry 5 --retry-delay 20 -C - -o "$z.part" "$url"
        got=$(fsize "$z.part")
        [ "$got" = "$bytes" ] || { echo "FATAL: $name: got $got bytes, expected $bytes (rerun to resume)"; exit 1; }
        mv "$z.part" "$z"
        echo "OK        $name"
    done
}

step_test() {
    for s in "${SETS[@]}"; do IFS='|' read -r name url bytes n <<< "$s"
        z=$DEST/zips/$name.zip
        [ -f "$z" ] || { echo "SKIP      $name (no zip; extracted already?)"; continue; }
        m=$(unzip -Z1 "$z" | grep -vc '/$' || true)
        [ "$m" = "$n" ] || { echo "FATAL: $name: $m members, expected $n"; exit 1; }
        unzip -tq "$z" >/dev/null || { echo "FATAL: $name: CRC test failed"; exit 1; }
        echo "TEST_OK   $name ($m members, CRC ok)"
    done
}

step_extract() {
    for s in "${SETS[@]}"; do IFS='|' read -r name url bytes n <<< "$s"
        z=$DEST/zips/$name.zip; d=$DEST/$name
        [ -f "$z" ] || { echo "SKIP      $name (no zip)"; continue; }
        mkdir -p "$d"
        unzip -q -n -j "$z" -d "$d"            # -j: flat; -n: never overwrite
        m=$(find "$d" -maxdepth 1 -type f | wc -l)
        [ "$m" = "$n" ] || { echo "FATAL: $name: $m files extracted, expected $n"; exit 1; }
        echo "EXTRACTED $name -> $d ($m files)"
        if [ "$KEEP_ZIPS" = 0 ]; then rm "$z"; echo "          removed $z"; fi
    done
}

step_sizes() {
    out=$DEST/sizes.tsv
    echo -e "set\tfile\txz_bytes\twcnf_bytes" > "$out"
    for s in "${SETS[@]}"; do IFS='|' read -r name url bytes n <<< "$s"
        d=$DEST/$name
        [ -d "$d" ] || continue
        for f in "$d"/*.xz; do
            u=$(xz -l --robot "$f" | awk -F'\t' '$1=="totals"{print $5}')
            echo -e "$name\t$(basename "$f")\t$(fsize "$f")\t$u" >> "$out"
        done
    done
    awk -F'\t' 'NR>1{n++; x+=$3; w+=$4; if($4>5*2^20)b++} END{printf "SIZES     %d files, xz %.1f GiB, as .wcnf %.1f GiB, %d files over 5 MiB as .wcnf -> %s\n", n, x/2^30, w/2^30, b, FILENAME}' "$out"
}

IFS=',' read -ra todo <<< "$STEPS"
for st in "${todo[@]}"; do
    case $st in
        net|download|test|extract|sizes) echo "== $st"; "step_$st" ;;
        *) echo "FATAL: unknown step $st"; exit 2 ;;
    esac
done
echo "DONE $STEPS"
