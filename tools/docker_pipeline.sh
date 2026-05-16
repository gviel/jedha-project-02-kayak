#!/bin/bash
# Lance le pipeline manuellement dans le container 'kayak' (sans attendre le cron)
# Usage : bash tools/docker_pipeline.sh  (depuis la racine du projet ou n'importe où)
exec docker exec kayak bash /app/pipeline.sh
