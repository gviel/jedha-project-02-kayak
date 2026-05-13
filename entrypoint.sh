#!/bin/bash
# expose Docker env vars to cron (cron ne voit pas les variables d'env du container)
printenv | grep -v "no_proxy" >> /etc/environment
# installe la cron depuis CRON_SCHEDULE (défaut : 06:00 UTC tous les jours)
{ echo "PATH=/usr/local/bin:/usr/bin:/bin"; echo "${CRON_SCHEDULE:-0 6 * * *} cd /app && /bin/bash /app/pipeline.sh >> /var/log/kayak.log 2>&1"; } | crontab -
echo "[entrypoint] cron installée : ${CRON_SCHEDULE:-0 6 * * *}"
# start cron in foreground
exec cron -f
