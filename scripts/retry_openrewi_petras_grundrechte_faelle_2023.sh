#!/bin/bash
# Retry OpenRewi import: petras-grundrechte-faelle-2023 → grundrechte
LOGFILE="/opt/openlex-mvp-v2/logs/openrewi_retry.log"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

# Check if already imported (job done in skills.json)
ALREADY=$(python3 -c "
import json
try:
    d = json.load(open('/opt/openlex-mvp-v2/skills.json'))
    imports = d['skills'].get('grundrechte', {}).get('openrewi_imports', [])
    if any(i.get('book_id') == 'petras-grundrechte-faelle-2023' for i in imports):
        print('yes')
except:
    pass
" 2>/dev/null)

if [ "$ALREADY" = "yes" ]; then
    echo "[$TS] petras-grundrechte-faelle-2023: already imported, removing cron" >> "$LOGFILE"
    crontab -l | grep -v 'retry_openrewi_petras_grundrechte_faelle_2023.sh' | crontab -
    exit 0
fi

# Test PDF URL
HTTP_STATUS=$(curl -sI --max-time 10 'https://library.oapen.org/handle/20.500.12657/64118' | head -1 | awk '{print $2}')

if [ "$HTTP_STATUS" = "200" ]; then
    echo "[$TS] petras-grundrechte-faelle-2023: server up ($HTTP_STATUS), starting import..." >> "$LOGFILE"
    RESULT=$(curl -s -X POST http://localhost:7865/api/skills/grundrechte/import-openrewi \
        -H 'Content-Type: application/json' \
        -d '{"book_id": "petras-grundrechte-faelle-2023"}')
    JOB_ID=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('job_id',''))" 2>/dev/null)
    echo "[$TS] petras-grundrechte-faelle-2023: import started, job_id=$JOB_ID" >> "$LOGFILE"

    # Poll for completion (max 30 min)
    if [ -n "$JOB_ID" ]; then
        for i in $(seq 1 60); do
            sleep 30
            STATUS=$(curl -s http://localhost:7865/api/jobs/$JOB_ID | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('status','?'))" 2>/dev/null)
            if [ "$STATUS" = "done" ]; then
                echo "[$TS] petras-grundrechte-faelle-2023: import done!" >> "$LOGFILE"
                crontab -l | grep -v 'retry_openrewi_petras_grundrechte_faelle_2023.sh' | crontab -
                echo "[$TS] petras-grundrechte-faelle-2023: cron removed" >> "$LOGFILE"
                exit 0
            elif [ "$STATUS" = "error" ]; then
                echo "[$TS] petras-grundrechte-faelle-2023: import error, will retry next run" >> "$LOGFILE"
                exit 1
            fi
        done
        echo "[$TS] petras-grundrechte-faelle-2023: timeout waiting for job" >> "$LOGFILE"
    fi
else
    echo "[$TS] petras-grundrechte-faelle-2023: server still down (HTTP $HTTP_STATUS)" >> "$LOGFILE"
fi
