#!/bin/bash
# Suivi en temps réel du log pipeline dans le container 'kayak'
# Usage : bash tools/docker_log.sh  (depuis la racine du projet ou n'importe où)
exec docker exec kayak tail -500f /var/log/kayak.log
