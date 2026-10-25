#!/bin/bash
# install_evalmaxsat2026.sh - install the MSE 2026 competition EvalMaxSAT binary (statically linked,
# from Zenodo record 21358014, solver-EvalMaxSAT.zip) and the updated EvalMaxSAT submit script.
# docs/current2/EVALMAXSAT_2026_INSTALL.md (repo). Login node, shell only (md5sum, unzip, sha256sum).
# Nothing is executed: the binary first runs in the smoke job on a compute node.
#   bash install_evalmaxsat2026.sh            # dry run
#   bash install_evalmaxsat2026.sh --apply    # do it
# Expects in $SRC (default ~): solver-EvalMaxSAT.zip and ems26__submit_evalmaxsat_mse.sh.
# Installs:  ~/evalmaxsat2026/EvalMaxSAT_bin (+ the zip, for provenance)
#            ~/cluster_staging_maxsat_evo/scripts/submit_evalmaxsat_mse.sh (old copy -> .bak_pre_ems26)
# FORCE=1 replaces a submit script whose sha256 is none of the committed versions nor the new one.
set -euo pipefail
SRC=${SRC:-$HOME}
BIN_DIR=${BIN_DIR:-$HOME/evalmaxsat2026}
TREE=${TREE:-$HOME/cluster_staging_maxsat_evo}
ZIP_MD5=58cdc54a3cb7a16b12ea8c198813c250                                   # Zenodo's md5 of solver-EvalMaxSAT.zip
BIN_SHA=63e46c2d08d7def0a5137a35044397b9ffc6ea9fc00861445d57b76dc6af5139     # EvalMaxSAT/bin/EvalMaxSAT_bin
SUB_OLD="3e7edfe0eab89dcb45b8de5591054d674ddf9945f5b6240221bdf1ea6cfcbebe f6950a5db758c171d35965b18e2431ca8c6d70941666b277326d3685ff9d92fa"  # committed versions (ad19012, f2f9fa1)
SUB_NEW=38fb95a27af22dd5d00c034f0d8ce08765d3bb1051db700a0fa619b6cb88d4bc     # CHECK_SMOKE reads OUTDIR
APPLY=0; [ "${1:-}" = "--apply" ] && APPLY=1
run() { if [ $APPLY = 1 ]; then "$@"; else echo "  would: $*"; fi; }
sha() { sha256sum "$1" | cut -d' ' -f1; }

# 1. the binary
if [ -x "$BIN_DIR/EvalMaxSAT_bin" ] && [ "$(sha "$BIN_DIR/EvalMaxSAT_bin")" = "$BIN_SHA" ]; then
    echo "HAVE      $BIN_DIR/EvalMaxSAT_bin"
else
    Z=$SRC/solver-EvalMaxSAT.zip
    [ -f "$Z" ] || { echo "FATAL: no $Z"; exit 2; }
    [ "$(md5sum "$Z" | cut -d' ' -f1)" = "$ZIP_MD5" ] || { echo "FATAL: $Z md5 differs from Zenodo's $ZIP_MD5"; exit 1; }
    echo "ZIP_OK    $Z (md5 = Zenodo)"
    run mkdir -p "$BIN_DIR"
    run unzip -o -j -q "$Z" EvalMaxSAT/bin/EvalMaxSAT_bin -d "$BIN_DIR"
    run chmod +x "$BIN_DIR/EvalMaxSAT_bin"
    if [ $APPLY = 1 ]; then
        [ "$(sha "$BIN_DIR/EvalMaxSAT_bin")" = "$BIN_SHA" ] || { echo "FATAL: binary sha256 differs"; exit 1; }
        [ "$Z" -ef "$BIN_DIR/solver-EvalMaxSAT.zip" ] || mv "$Z" "$BIN_DIR/"
        echo "BIN_OK    $BIN_DIR/EvalMaxSAT_bin"
    fi
fi

# 2. the submit script
S=$SRC/ems26__submit_evalmaxsat_mse.sh; D=$TREE/scripts/submit_evalmaxsat_mse.sh
[ -d "$TREE/scripts" ] || { echo "FATAL: no $TREE/scripts"; exit 2; }
cur=$( [ -f "$D" ] && sha "$D" || echo none )
if [ "$cur" = "$SUB_NEW" ]; then
    echo "HAVE      $D"; [ -f "$S" ] && run rm "$S"
else
    [ -f "$S" ] || { echo "FATAL: no $S"; exit 2; }
    [ "$(sha "$S")" = "$SUB_NEW" ] || { echo "FATAL: $S sha256 differs from the expected new version"; exit 1; }
    if [[ " $SUB_OLD " != *" $cur "* ]] && [ "${FORCE:-0}" != 1 ]; then
        echo "FATAL: $D is neither the known old version nor the new one (sha256 $cur); FORCE=1 to replace it"; exit 1
    fi
    bak=$D.bak_pre_ems26; [ -e "$bak" ] && bak=$bak.$(date +%Y%m%dT%H%M%S)   # never overwrite a backup
    echo "REPLACE   $D (old copy -> $(basename "$bak"))"
    run mv "$D" "$bak"; run mv "$S" "$D"; run chmod +x "$D"
fi
[ $APPLY = 1 ] && echo "INSTALL_OK" || echo "dry run: nothing changed; run again with --apply"
