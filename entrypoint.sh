#!/bin/bash
# expose Docker env vars to cron (cron ne voit pas les variables d'env du container)
printenv | grep -v "no_proxy" >> /etc/environment
# installe la cron depuis CRON_SCHEDULE (défaut : 07:00 Europe/Paris tous les jours)
{ echo "PATH=/usr/local/bin:/usr/bin:/bin"; echo "${CRON_SCHEDULE:-0 7 * * *} cd /app && /bin/bash /app/pipeline.sh >> /var/log/kayak.log 2>&1"; } | crontab -
echo "[entrypoint] cron installée : ${CRON_SCHEDULE:-0 7 * * *}"
# créer le fichier log dès le démarrage pour que docker_log.sh puisse le suivre immédiatement
touch /var/log/kayak.log
# start cron in foreground
exec cron -f
