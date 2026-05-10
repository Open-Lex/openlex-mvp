# Pipeline-Smoketest — GRÜN

**Datum:** 2026-05-10  
**Skill:** datenschutz (`openlex_datenschutz`, 18084 Chunks)  
**Modell:** `mixedbread-ai/deepset-mxbai-embed-de-large-v1`  
**Status:** ✅ GRÜN

## Ergebnisse

| # | Query | Status | Latenz | Hit@5 | Source-Types |
|---|---|---|---:|---|---|
| 1 | Welche Voraussetzungen gelten für eine Einwilligung nac… | OK | 21259ms | ✅ | gesetz_granular, urteil_segmentiert |
| 2 | Darf der Arbeitgeber Mitarbeiter-E-Mails kontrollieren?… | OK | 6950ms | ✅ | gesetz_granular, leitlinie |
| 3 | Wann ist ein Auftragsverarbeitungsvertrag nach Art. 28 … | OK | 7924ms | ✅ | gesetz_granular, leitlinie |
| 4 | Schadensersatz bei Datenpanne nach Art. 82 DSGVO?… | OK | 8799ms | ✅ | gesetz_granular, urteil_segmentiert |
| 5 | Ab wann muss ein Datenschutzbeauftragter bestellt werde… | OK | 6309ms | ✅ | gesetz_granular, urteil_segmentiert, leitlinie |

**Hit@5:** 100% (5/5 Queries)
**Avg Latenz:** 10248ms

## Top-3 pro Query

### Welche Voraussetzungen gelten für eine Einwilligung nach Art. 6 DSGVO?
- Terms gefunden: ['einwilligung', 'dsgvo', 'freiwillig']

### Darf der Arbeitgeber Mitarbeiter-E-Mails kontrollieren?
- Terms gefunden: ['beschäftigtendatenschutz', '§ 26 bdsg', 'arbeitgeber', 'überwachung']

### Wann ist ein Auftragsverarbeitungsvertrag nach Art. 28 DSGVO erforderl
- Terms gefunden: ['auftragsverarbeitung', 'art. 28']

### Schadensersatz bei Datenpanne nach Art. 82 DSGVO?
- Terms gefunden: ['art. 82', 'schadensersatz', 'immateriell']

### Ab wann muss ein Datenschutzbeauftragter bestellt werden?
- Terms gefunden: ['datenschutzbeauftragter', 'art. 37', 'benennung', 'pflicht']

## Befund

Pipeline ist generisch und funktioniert für `datenschutz`.
- `get_collection(skill_id)` löst korrekt auf
- `retrieve(question, skill_id=...)` gibt plausible Chunks zurück
- Query-Rewriter (OPENLEX_REWRITE_ENABLED=false) sauber deaktiviert
- QU-Injection schlägt still fehl für unbekannte Normen → kein Blocker
- **Pipeline kann für Multi-Skill-Eval genutzt werden**

→ Weg 1 (Schatten-Eval) kann starten.