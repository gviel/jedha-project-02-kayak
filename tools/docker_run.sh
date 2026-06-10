#!/bin/bash
# Rebuild, stop et relancement du container Docker kayak
# Usage : bash tools/docker_run.sh  (depuis la racine du projet ou n'importe où)
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR}/.."

echo "[1/3] Arrêt et suppression du container 'kayak' (si existant)..."
docker stop kayak 2>/dev/null && echo "  stopped" || echo "  (aucun container à arrêter)"
docker rm   kayak 2>/dev/null && echo "  removed" || true

echo ""
echo "[2/3] Build de l'image 'kayak'..."
docker build -t kayak "${PROJECT_DIR}"

echo ""
echo "[3/3] Lancement du container 'kayak'..."
docker run -d \
    --name kayak \
    --restart unless-stopped \
    --env-file "${PROJECT_DIR}/.env" \
    -v "${PROJECT_DIR}/data:/app/data" \
    kayak

echo ""
docker ps --filter "name=kayak" --format "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.CreatedAt}}\t{{.Status}}"
echo ""
echo "Container 'kayak' démarré. Suivez les logs avec : bash tools/docker_log.sh"
