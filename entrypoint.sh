#!/bin/bash
# expose Docker env vars to cron (cron ne voit pas les variables d'env du container)
printenv | grep -v "no_proxy" >> /etc/environment
# start cron in foreground
exec cron -f
