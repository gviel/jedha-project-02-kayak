#!/bin/bash
# Packages README.md et la présentation PDF dans une archive zip pour livraison.
# Usage : bash tools/package_deliverables.sh  (depuis la racine du projet ou n'importe où)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

README="${PROJECT_DIR}/README.md"
PDF="${PROJECT_DIR}/docs/presentation/CDSD_bloc1_kayak_GV.pdf"
OUT_DIR="${PROJECT_DIR}/dist"
DATE_TAG="$(date +%Y%m%d)"
OUT_ZIP="${OUT_DIR}/kayak_deliverables-${DATE_TAG}.zip"

for f in "$README" "$PDF"; do
    if [ ! -f "$f" ]; then
        echo "Erreur : fichier introuvable : $f" >&2
        exit 1
    fi
done

mkdir -p "$OUT_DIR"

zip -j "$OUT_ZIP" "$README" "$PDF"

echo ""
echo "Archive créée : ${OUT_ZIP}"
unzip -l "$OUT_ZIP"
