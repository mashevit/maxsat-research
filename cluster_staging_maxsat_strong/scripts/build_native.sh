#!/bin/bash
# Build the C polish core (B5) ONCE for this tree: src/native/ls_core.c ->
# src/native/build/libls_core.so plus BUILD_INFO.txt. Shell and gcc only -- no
# Python -- so it may run on the login node, or as its own job:
#   cd ~/cluster_staging_maxsat_strong/scripts && mkdir -p logs && sbatch build_native.sbatch
#   bash build_native.sh                # direct
# Rebuild after every change to ls_core.c: src/native/native.py refuses a build
# whose recorded source hash differs from the current source, and the shard
# runner then refuses `ls.native: true` before the run (exit 2).
# docs/current2/STRONGER_MEMETIC_DESIGN.md §7, §8.0.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$ROOT/src/native/ls_core.c"
OUT="${MAXSAT_NATIVE_BUILD_DIR:-$ROOT/src/native/build}"
CC="${CC:-cc}"
CFLAGS="-O2 -shared -fPIC"
mkdir -p "$OUT"
# shellcheck disable=SC2086
"$CC" $CFLAGS -o "$OUT/libls_core.so.tmp" "$SRC"
mv "$OUT/libls_core.so.tmp" "$OUT/libls_core.so"
{
    echo "source_sha256=$(sha256sum "$SRC" | cut -d' ' -f1)"
    echo "so_sha256=$(sha256sum "$OUT/libls_core.so" | cut -d' ' -f1)"
    echo "compiler=$("$CC" --version | head -1)"
    echo "cflags=$CFLAGS"
    echo "host=$(hostname)"
    echo "built_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/BUILD_INFO.txt"
echo "BUILD_OK $OUT/libls_core.so"
cat "$OUT/BUILD_INFO.txt"
