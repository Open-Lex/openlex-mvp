#!/bin/bash
# Master Test-Runner: L0 → L1 → L2 → L3 → L4
set -euo pipefail

NTFY="https://ntfy.sh/openlex-p2-e52c117a"
DIR="/opt/openlex-sources/scripts/eval"
LOG="/opt/openlex-sources/reports/eval/full_test_$(date +%Y%m%d_%H%M).log"
mkdir -p /opt/openlex-sources/reports/eval

ntfy() {
    local title="$1" msg="$2" prio="${3:-default}" tags="${4:-}"
    curl -s "$NTFY" \
        -H "Title: $title" \
        -H "Priority: $prio" \
        ${tags:+-H "Tags: $tags"} \
        -d "$msg" > /dev/null
}

run_level() {
    local level="$1" script="$2" label="$3"
    echo "=== $label ===" | tee -a "$LOG"
    ntfy "🔍 OpenLex Test $level" "$label gestartet..."
    
    if python3 "$DIR/$script" 2>&1 | tee -a "$LOG"; then
        ntfy "✅ $level OK" "$label erfolgreich" "default" "white_check_mark"
        return 0
    else
        ntfy "❌ $level FEHLER" "$label fehlgeschlagen — nächste Level übersprungen" "high" "x"
        return 1
    fi
}

echo "OpenLex Full Test — $(date)" | tee "$LOG"
ntfy "🚀 OpenLex Test Suite" "Starte L0→L1→L2→L3→L4..." "default" "rocket"

# L0
run_level "L0" "test_l0_sanity.py" "L0 Sanity (Collections, JSON, Embedding)" || exit 1

# L1
run_level "L1" "test_l1_data_quality.py" "L1 Datenqualität (Chunks, HTML, Duplikate)" || exit 1

# L2 — retrieval_scorer mit Calibration-Modus
echo "=== L2 Retrieval ===" | tee -a "$LOG"
ntfy "🔍 OpenLex Test L2" "L2 Retrieval-Qualität gestartet..."
if python3 "$DIR/retrieval_scorer.py" 2>&1 | tee -a "$LOG"; then
    ntfy "✅ L2 OK" "Retrieval-Scoring abgeschlossen" "default" "white_check_mark"
else
    ntfy "⚠️ L2 Warnung" "Retrieval-Scorer hatte Probleme — fahre fort" "default" "warning"
fi

# L3
run_level "L3" "test_l3_smoke.py" "L3 Smoke Test (50 Haiku-Calls)" || ntfy "⚠️ L3 Warnung" "L3 hatte Fehler — fahre mit L4 fort" "default" "warning"

# L4
echo "=== L4 Vollständiger Eval ===" | tee -a "$LOG"
ntfy "🔍 OpenLex Test L4" "L4 startet — 500 LLM-Calls, ~70 Min..." "default" "hourglass_flowing_sand"
if python3 "$DIR/eval_llm.py" 2>&1 | tee -a "$LOG"; then
    # Ergebnis aus letztem JSON auslesen
    RESULT=$(python3 -c "
import json, glob
files = sorted(glob.glob('/opt/openlex-sources/eval/results/llm_*.json'), reverse=True)
skill_scores = {}
for f in files:
    try:
        data = json.load(open(f))
        if isinstance(data, list):
            for item in data:
                sk = item.get('skill','')
                sc = item.get('avg_score',0)
                if sk and sk not in skill_scores and sc > 0:
                    skill_scores[sk] = sc
    except: pass
above80 = sum(1 for sc in skill_scores.values() if sc >= 80)
below80 = [(sk,sc) for sk,sc in skill_scores.items() if sc < 80]
print(f'{above80}/50 Skills ≥80%')
if below80:
    print('Unter 80%: ' + ', '.join(f'{sk}:{sc:.0f}' for sk,sc in sorted(below80, key=lambda x:x[1])))
" 2>/dev/null)
    ntfy "✅ L4 DONE — $RESULT" "Eval abgeschlossen" "high" "white_check_mark"
else
    ntfy "❌ L4 FEHLER" "Eval fehlgeschlagen" "high" "x"
fi

echo "=== FERTIG $(date) ===" | tee -a "$LOG"
ntfy "🏁 OpenLex Test Suite FERTIG" "Log: $LOG" "high" "checkered_flag"
