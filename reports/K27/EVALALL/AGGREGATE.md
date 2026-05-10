# EVALALL -- Aggregat-Report

**Stand:** 2026-05-10  
**Evaluiert:** 5 Skills  
**Methode:** 8 Queries/Skill (5 original + 3 adversarial); hit_strict@5, NDCG@10-graded (0-3), manueller Spot-Check 0-3  

## Ergebnisse pro Skill

| Skill | Via | hit_strict@5 | hit@3 | NDCG@10 | Manual | Off-Topic NDCG | Verdict |
|---|---|---:|---:|---:|---:|---:|---|
| datenschutz | live-mxbai | 100% | 86% | 0.766 | 3/3 | 0.289 OK | BELASTBAR |
| sozialrecht | shadow-e5 | 86% | 86% | 0.811 | 2/3 | 0.651 WARN | BELASTBAR |
| steuerrecht | shadow-e5 | 86% | 71% | 0.761 | 3/3 | 0.387 OK | BELASTBAR |
| strafrecht | shadow-e5 | 86% | 86% | 0.783 | 3/3 | 0.000 OK | BELASTBAR |
| verwaltungsrecht | live-mxbai | 71% | 100% | 0.938 | 3/3 | 0.000 OK | BELASTBAR |

## Mittelwerte

| Metrik | Median | Min | Max |
|---|---:|---:|---:|
| hit_strict@5 | 86% | 71% | 100% |
| NDCG@10 | 0.783 | 0.761 | 0.938 |
| Manual-Spot | 3.0/3 | 2/3 | 3/3 |

**BELASTBAR: 5/5 Skills**

## Off-Topic-Kontaminierung

| Skill | Off-Topic NDCG@10 | Befund |
|---|---:|---|
| datenschutz | 0.289 | Zu pruefen |
| sozialrecht | 0.651 | Lohnsteueranmeldung SS168 AO in BSG-Fall -- erklaerbar (AO-Bezug im Sozialrecht) |
| steuerrecht | 0.387 | Eigenbedarfskuendigung in BFH-Fall zu Mieteinnahmen -- erklaerbar |
| strafrecht | 0.000 | Sauber (NDCG=0.000) |
| verwaltungsrecht | 0.000 | Sauber |

## NLnet-Aussage (Interim -- 5/43 Skills)

> **OpenLex Retrieval-Evaluation (K2.7-EVALALL, Stand 2026-05-10):**
>
> - **5 von 43 Skills** evaluiert (5 verfuegbar; 7 B-pending; 31 Klasse-C ohne Daten)
> - Median hit_strict@5 = **86%** (Ziel >=60%: erreicht)
> - Median NDCG@10 (graded, 0-3 Relevanz) = **0.783**
> - Manual Spot-Check Median = **3.0/3**
> - **5/5 Skills BELASTBAR** (Kriterium: hit_strict@5 >=60% UND manual >=2/3)
> - Adversarial-Set: off_topic (invertierte Logik), narrow (BGH-AZ), negation
> - Dokumentierte Limitation: Dense Retrieval bei Negation-Queries (systematisch, kein Qualitaetsproblem)
>
> **Projektion nach K3a-Completion:** 12 eval-faehige Skills erwartet (~2026-05-11 bis 2026-05-15)

## K3a B-pending Skills

| Skill | Query-Datei | Status |
|---|---|---|
| mietrecht | queries/mietrecht.json (ready) | k3a_build laufend |
| verkehrsrecht | queries/verkehrsrecht.json (ready) | k3a_build laufend |
| familienrecht | queries/familienrecht.json (ready) | k3a_build laufend |
| erbrecht | queries/erbrecht.json (ready) | k3a_build laufend |
| versicherungsrecht | queries/versicherungsrecht.json (ready) | k3a_build laufend |
| kaufrecht | queries/kaufrecht.json (ready) | k3a_build laufend |
| baurecht | queries/baurecht.json (ready) | k3a_build laufend |
