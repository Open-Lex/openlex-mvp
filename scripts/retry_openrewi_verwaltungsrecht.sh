#!/bin/bash
# Retry OpenRewi import for verwaltungsrecht
STATUS=503
if [ "" = '200' ]; then
    echo "[Tue May  5 12:59:36 CEST 2026] OAPEN is up (HTTP ), starting import..."
    curl -s -X POST http://localhost:7865/api/skills/verwaltungsrecht/import-openrewi         -H 'Content-Type: application/json'         -d '{"book_id": "eisentraut-verwaltungsrecht-2020"}'         >> /opt/openlex-mvp-v2/logs/openrewi_retry.log 2>&1
    echo "[Tue May  5 12:59:36 CEST 2026] Import started" >> /opt/openlex-mvp-v2/logs/openrewi_retry.log
    # Remove cron after success
    crontab -l | grep -v 'retry_openrewi' | crontab -
    echo "[Tue May  5 12:59:36 CEST 2026] Cron removed" >> /opt/openlex-mvp-v2/logs/openrewi_retry.log
else
    echo "[Tue May  5 12:59:36 CEST 2026] OAPEN still down (HTTP )" >> /opt/openlex-mvp-v2/logs/openrewi_retry.log
fi
