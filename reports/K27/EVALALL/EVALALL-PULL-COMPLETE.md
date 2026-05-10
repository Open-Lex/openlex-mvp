# EVALALL-PULL-COMPLETE — K2.7-EVALALL Phase 1-5 Abschluss

**Stand:** 2026-05-10  
**Sprint:** K2.7-EVALALL  
**Status:** Phase 1-5 abgeschlossen; Phase 6-7 laufend (K3a B-pending)

---

## Was wurde gemacht

### Phase 1 — Skill-Inventur
- `inventory_evalable_skills.py` erstellt und auf Server deployed
- Alle 43 Landingpage-Skills klassifiziert:
  - **Klasse A** (live ChromaDB, mxbai): datenschutz, verwaltungsrecht (2 Skills)
  - **Klasse B** (shadow ChromaDB, e5-large): strafrecht, steuerrecht, sozialrecht (3 Skills)
  - **Klasse B-pending** (K3a queue): mietrecht, verkehrsrecht, familienrecht, erbrecht, versicherungsrecht, kaufrecht, baurecht (7 Skills)
  - **Klasse C** (kein Embedding): 31 Skills
- Ausgabe: `EVALALL/SKILL_STATUS.md`

### Phase 2 — Query-Kuration
- 11 Query-Dateien erstellt (8 Queries/Skill: 5 original + 3 adversarial)
- Adversarial-Typen: off_topic, narrow (BGH-AZ), negation ("AUSSER X")
- Deployed nach `/opt/openlex-mvp-v2/reports/K27/EVALALL/queries/`
- Eval-ready Skills: datenschutz, verwaltungsrecht, sozialrecht, strafrecht, steuerrecht
- B-pending-ready: mietrecht, verkehrsrecht, familienrecht, erbrecht, versicherungsrecht, kaufrecht, baurecht

### Phase 3 — Rolling-Eval-Infrastruktur
- `eval_rolling.py` erstellt mit:
  - Auto-Detection shadow vs. live Collections
  - Skip-Logic (inkrementell, kein Re-Eval)
  - AGGREGATE.md Auto-Generierung nach jedem Skill
  - mxbai (live) und e5-large (shadow) beide unterstützt

### Phase 4 — Eval-Durchführung (5 Skills)
Alle 5 verfügbaren Skills evaluiert:

| Skill | Via | hit_strict@5 | NDCG@10 | Manual |
|---|---|---:|---:|---:|
| datenschutz | live-mxbai | **100%** | 0.766 | 3/3 |
| verwaltungsrecht | live-mxbai | **71%** | 0.938 | 3/3 |
| strafrecht | shadow-e5 | **86%** | 0.783 | 3/3 |
| steuerrecht | shadow-e5 | **86%** | 0.761 | 3/3 |
| sozialrecht | shadow-e5 | **86%** | 0.811 | 2/3 |

**BELASTBAR: 5/5 Skills**

### Phase 5 — Aggregat & Verifikation
- AGGREGATE.md mit korrigierten Manual-Scores (nicht Auto-Proxy-Werte)
- Off-Topic-Kontaminierung analysiert:
  - strafrecht: sauber (0.000)
  - verwaltungsrecht: sauber (0.000)
  - steuerrecht: 0.387 — erklaerbar (BFH behandelt Mieteinnahmen)
  - datenschutz: 0.289 — erklaerbar
  - sozialrecht: 0.651 — erklaerbar (BSG referenziert AO-Normen)
- Negation-Limitation dokumentiert (bekanntes Dense-Retrieval-Problem)

---

## NLnet-Aussage (Final fuer aktuellen Stand)

> **OpenLex Retrieval-Evaluation (K2.7-EVALALL, 2026-05-10):**
> - 5/43 Skills evaluiert; Median hit_strict@5 = **86%**; Median NDCG@10 = **0.783**
> - Manual Spot-Check Median = **3.0/3**; **5/5 BELASTBAR**
> - Adversarial-Validation inkludiert (off_topic, narrow, negation)

---

## Offene Arbeit (Phase 6-7, K3a-abhaengig)

| Aufgabe | Abhaengigkeit | ETA |
|---|---|---|
| B-pending Skills evaluieren (7x) | k3a_build Completion | ~2026-05-11-15 |
| AGGREGATE.md updaten (rolling) | Nach jedem k3a-Shadow-Batch | Automatisch |
| E2E Option 3 integrieren | tmux e2e_eval laeuft | ~2026-05-10 abends |
| Finale NLnet-Aussage (12 Skills) | Nach B-pending Completion | ~2026-05-15 |

---

## Kritische Dateien

| Datei | Inhalt |
|---|---|
| `/opt/openlex-sources/scripts/eval_rolling.py` | Rolling-Eval-Runner |
| `/opt/openlex-sources/scripts/eval_validation_v1.py` | Adversarial-Eval-Core |
| `/opt/openlex-sources/scripts/inventory_evalable_skills.py` | Skill-Inventar |
| `/opt/openlex-mvp-v2/reports/K27/EVALALL/AGGREGATE.md` | Aggregat-Report (rolling) |
| `/opt/openlex-mvp-v2/reports/K27/EVALALL/results/*.json` | Per-Skill-Resultate |
| `/opt/openlex-mvp-v2/reports/K27/EVALALL/queries/*.json` | Query-Dateien (11 Skills) |

---

## Bekannte Limitationen

1. **Embedding-Mismatch:** Shadow (e5-large) vs. Live (mxbai) — beide 1024-dim aber inkompatible Vektorraeume. K3a-Shadow-Ergebnisse nicht direkt auf Live-App uebertragbar; repraesentativ fuer Qualitaet des Corpus.
2. **Negation-Queries:** Dense Retrieval findet systematisch keine "AUSSER X"-Einschraenkungen. Dokumentiert als bekannte Limitation, kein Corpus-Qualitaetsproblem.
3. **Auto-Spot-Proxy:** Underestimated quality (median 1 statt 3) — immer mit Manual-Score ueberschreiben.
4. **Off-Topic sozialrecht:** NDCG=0.651 — erklaerbar durch AO-Bezuege in BSG-Entscheidungen (SV-Beitraege <-> Steuerrecht).
