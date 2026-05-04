# STAGE-B-REPORT: Multi-Skill Dev-Umgebung
**Erstellt:** 2026-05-04  
**Branch:** `refactor/multi-skill-support`  
**Verzeichnis:** `/opt/openlex-mvp-v2/`

---

## 1. Was wurde geklont

| Komponente | Quelle | Ziel | Größe |
|---|---|---|---|
| Codebasis | `/opt/openlex-mvp/` | `/opt/openlex-mvp-v2/` | 8,4 GB |
| ChromaDB | (Teil des Klons) | `/opt/openlex-mvp-v2/chromadb/` | 543 MB |
| Git-Branch | `main` | `refactor/multi-skill-support` | — |

**ChromaDB-Validierung:** 18.084 Chunks ✅  
**Isolation:** v2 nutzt eigene ChromaDB, eigene Log-Dateien, eigenen Cache — kein Conflict mit v1.

---

## 2. Was wurde refaktoriert (8 Commits)

| # | Commit | Beschreibung |
|---|---|---|
| 1 | `e5988e2` | `skills.json` Manifest + `prompts/datenschutz.md` angelegt |
| 2 | `6974d74` | `SYSTEM_PROMPT` aus `prompts/datenschutz.md` geladen via `load_system_prompt()` |
| 3 | `77da058` | `get_collection(skill_id)` mit Dict-Cache ersetzt Singleton |
| 4 | `8ce4e5b` | `retrieve(skill_id)` gibt `skill_id` an `get_collection()` weiter |
| 5 | `7fc5ac0` | `_build_llm_messages(skill_id)` lädt System-Prompt per `load_system_prompt()` |
| 6 | `56c1a9e` | `chat_stream(skill_id)` fädelt `skill_id` durch gesamte Pipeline |
| 7 | `be17dd9` | Gradio `skill_selector` Dropdown + `respond(skill_id)` |
| 8 | `a7a0320` | `per_source_retrieval.py` nutzt `CHROMADB_DIR` Env-Var |
| 9 | `7034a31` | Inspector: `InspectRequest.skill_id` + `FullRunRequest.skill_id` |
| Fix | `3e6440a` | Einrückungsfehler im Gradio-Block korrigiert |
| Fix | `69bdf4a` | `server_port` via `GRADIO_SERVER_PORT` Env-Var konfigurierbar |

### Neu angelegte Dateien

| Datei | Inhalt |
|---|---|
| `skills.json` | Skill-Manifest: `active_skill`, `skills.datenschutz` (status=live) |
| `prompts/datenschutz.md` | SYSTEM_PROMPT extrahiert (3.798 Zeichen) |

### Neue Funktionen in app.py

```python
load_skills_manifest() -> dict          # Lädt skills.json
load_system_prompt(skill_id) -> str     # Lädt prompts/{skill_id}.md
get_collection_name(skill_id) -> str    # Gibt Collection-Namen aus Manifest
get_collection(skill_id) -> Collection  # Dict-Cache {skill_id: ChromaDB-Collection}
```

---

## 3. Wie läuft v2

| Eigenschaft | Wert |
|---|---|
| Service | `openlex-app-v2.service` |
| Port | 7864 (lokal, via nginx geroutet) |
| Verzeichnis | `/opt/openlex-mvp-v2/` |
| ChromaDB | `/opt/openlex-mvp-v2/chromadb/` (18.084 Chunks) |
| URL | derzeit nur direkter Zugriff via IP:7864 oder (wenn DNS gesetzt) `app-dev.open-lex.cloud` |
| Log | `/opt/openlex-mvp-v2/app.log` |
| Branch | `refactor/multi-skill-support` |

**v1 (Live) vollständig unverändert:** app.open-lex.cloud zeigt weiter auf Port 7860.

---

## 4. Eval-Vergleich

**Eval-Set:** `eval_sets/canonical_v3.json` (78 Fragen)  
**Modus:** `--retrieval-only` (kein LLM, nur Retrieval)

| Metrik | v1 (Live, 2026-05-03) | v2 (Refactor, 2026-05-04) | Delta | Pass/Fail |
|---|---|---|---|---|
| Hit@10 | 0.506 | 0.506 | **+0.000** | ✅ PASS |
| NDCG@10 | 0.366 | 0.366 | **+0.000** | ✅ PASS |
| MRR | 0.389 | 0.389 | **+0.000** | ✅ PASS |
| Hit@5 | 0.428 | 0.428 | **+0.000** | ✅ PASS |
| Hit@3 | 0.384 | 0.384 | **+0.000** | ✅ PASS |

**Kategorien (Hit@10) — alle identisch:**

| Kategorie | v1 | v2 | Delta |
|---|---|---|---|
| allgemein | 0.100 | 0.100 | 0.000 |
| auftragsverarbeitung | 0.143 | 0.143 | 0.000 |
| behoerden | 0.500 | 0.500 | 0.000 |
| beschaeftigtendatenschutz | 0.500 | 0.500 | 0.000 |
| betroffenenrechte | 0.278 | 0.278 | 0.000 |
| cookies_tracking | 0.500 | 0.500 | 0.000 |
| drittlandtransfer | 0.344 | 0.344 | 0.000 |
| methodenwissen | 0.271 | 0.271 | 0.000 |
| pruefungsschemata | 0.814 | 0.814 | 0.000 |
| rechtsgrundlagen | 0.301 | 0.301 | 0.000 |
| rechtsprechung | 0.631 | 0.631 | 0.000 |

**Eval-Laufzeit:** v2 = 120,5s (v1 = 118,3s) — identisch.

---

## 5. Sichtprüfung — 5 Queries für Hendrik

Bitte folgende Queries sowohl gegen v1 (Port 7860 / app.open-lex.cloud) als auch v2 (Port 7864) abschicken und Antworten vergleichen:

| # | Query | Prüft |
|---|---|---|
| 1 | "Was sagt Art. 6 DSGVO?" | Basisnorm, Kernrechtsgebiet |
| 2 | "Schrems II Konsequenzen für USA-Datentransfer" | EuGH-Urteil, Drittlandtransfer |
| 3 | "Wie lange muss ich Cookies löschen?" | TDDDG, praktische Frage |
| 4 | "Was ändert sich durch das TDDDG?" | Gesetzesumbenennung |
| 5 | "Videoüberwachung Arbeitsplatz Beschäftigte" | Beschäftigtendatenschutz |

---

## 6. Empfehlung: **CONDITIONAL PASS**

**Retrieval-identisch:** Der Refactor hat null Auswirkung auf Retrieval-Qualität (Delta = 0.000 auf allen Metriken). Die Pipeline-Logik ist korrekt durchgereicht.

**Noch ausstehend für vollständiges PASS:**
- [ ] Sichtprüfung Antwortqualität (5 Queries, manuell)
- [ ] LLM-Eval noch nicht durchgeführt (nur Retrieval) — Answer-Score-Baseline fehlt noch
- [ ] Gradio-Dropdown derzeit nicht sichtbar (nur 1 Skill live → `visible=False`) — Design OK, aber erst testbar mit 2+ Skills
- [ ] DNS für `app-dev.open-lex.cloud` noch nicht gesetzt (v2 erreichbar via direktem Port-Zugriff)

**NICHT empfohlen für Cutover:** v2 ist Dev-Umgebung. Cutover erst nach Sichtprüfung + LLM-Eval.

---

## 7. Offene Risiken / TODOs

| # | Risiko | Priorität |
|---|---|---|
| R1 | `per_source_retrieval._col` ist Modul-Level-Cache — bei Multi-Skill-Wechsel im selben Prozess wird falsche Collection genutzt. Lösung: `_get_col(skill_id)` | Mittel |
| R2 | Gradio-Dropdown `skill_selector` ist `visible=False` solange nur 1 Skill live — korrekt, aber für Tests mit 2 Skills Sichtbarkeit manuell testen | Niedrig |
| R3 | Inspector `main.py` importiert `app.retrieve` — bei Multi-Skill muss der Inspector-v2-Service auch von `/opt/openlex-mvp-v2/inspector/main.py` gestartet werden | Mittel |
| R4 | `app-dev.open-lex.cloud` DNS fehlt noch | Niedrig (optional) |
| R5 | LLM-Eval (Answer-Score) noch nicht durchgeführt — LLM nutzt `load_system_prompt(skill_id)`, korrekte Funktion sollte sicher sein, aber noch ungetestet | Niedrig |

---

## Nächste Schritte nach Sichtprüfung

1. **Zweiten Skill anlegen** (z.B. Kaufrecht): `skills.json` erweitern, ChromaDB-Collection ingesten, `prompts/kaufrecht.md` schreiben → Gradio-Dropdown wird automatisch sichtbar
2. **Orchestrator** (später): `route_to_skill(question)` → Keyword-Mapping → LLM-Klassifikator
3. **Cutover** (nach vollständigem PASS): `openlex-app.service` auf v2-Code umlenken, v1 als Backup behalten

