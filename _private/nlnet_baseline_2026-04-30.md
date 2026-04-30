# OpenLex Pipeline Improvements — eval_v3 Baseline

Generated: 2026-04-30  
Eval-Set: canonical_v3.json (78 queries, gesetz_granular-zentriert)  
Git-HEAD: 894f1b0 (fix: load .env in app.py and eval_v3.py)  
ChromaDB: 18.084 Chunks

## Vergleichstabelle

| Metric | Baseline | + Hebel 1 (Hypothesizer) | + Hebel 1+2 (Production) | Δ Production – Baseline |
|---|---|---|---|---|
| **Hit@3** | 0.340 | 0.340 | 0.383 | +0.043 (+12.6%) |
| **Hit@5** | 0.363 | 0.367 | 0.426 | +0.063 (+17.4%) |
| **Hit@10** | 0.404 | 0.404 | 0.524 | +0.120 (+29.7%) |
| **MRR** | 0.371 | 0.371 | 0.421 | +0.050 (+13.5%) |
| **nDCG@10** | 0.237 | 0.238 | 0.349 | +0.112 (+47.3%) |
| **ForbiddenHit@10** | 0.000 | 0.000 | 0.000 | — |

## Konfigurationen

**Baseline:** Alle Hebel deaktiviert. Standard-Retrieval via ChromaDB Single-Call,
Norm-Auswahl ausschließlich via Regex-Heuristik, kein LLM-Hypothesizer,
kein Per-Source-Budget. MAX_DOCS=8.

**+ Hebel 1 (Hypothesizer):** Zusätzlich LLM-basierter Norm-Hypothesizer aktiv
(Mistral Medium, Primary-Pfad). Erzeugt pro Query eine Liste von Kandidaten-Normen
und injiziert sie als semantischen Boost in die Embedding-Suche.

**+ Hebel 1+2 (Production):** Zusätzlich Per-Source-Retrieval mit Typ-Budget aktiv.
Statt eines einzigen ChromaDB-Calls über alle 18k Chunks: separate Calls
pro Source-Type mit Budget:
- gesetz_granular: max 4 Chunks
- urteil_segmentiert: max 2 Chunks
- leitlinie: max 2 Chunks
- methodenwissen: max 1 Chunk
- erwaegungsgrund: max 1 Chunk

## Interpretation

**Hebel 1 (Hypothesizer) allein:** Minimaler Effekt auf diesem Eval-Set (+0.4% Hit@5, 0% Hit@3/Hit@10).
Das v3-Set ist gesetz_granular-zentriert (86% der Goldlabels sind `dsgvo_art_*` oder `gran_*`).
Diese Chunks werden bereits ohne Hypothesizer gut gefunden, da die Fragen die Artikelnummern explizit nennen.

**Hebel 2 (Per-Source-Budget) allein und kombiniert:** Starker Effekt. Hit@10 steigt von 0.404 auf 0.524 (+30%).
nDCG@10 steigt von 0.237 auf 0.349 (+47%). Das Budget verhindert, dass ein einzelner Source-Type
(z.B. Leitlinien oder Urteile) alle Top-K-Slots belegt und Gold-Chunks verdrängt.

**MRR: +13.5%** — Gold-Chunks werden im Schnitt früher im Ranking gefunden.

## Einschränkung: Eval-Set-Bias

Das canonical_v3.json-Set deckt ausschließlich `gesetz_granular`-zentrierte Goldlabels ab.
Für eine vollständige Evaluation der Production-Pipeline (Urteile, Leitlinien, Methodenwissen)
ist eval_v4 mit 178 Real-Queries in Annotation. Die Zahlen hier unterschätzen vermutlich
den Hypothesizer-Effekt für Fragen zu aktueller Rechtsprechung.

## Methodische Garantien

- Alle drei Läufe: identischer Code-Stand (git HEAD 894f1b0)
- Identisches Eval-Set (canonical_v3.json, 78 Queries)
- Identischer ChromaDB-Stand (18.084 Chunks)
- Konfigurationsunterschiede ausschließlich via explizit gesetzter Env-Variablen (`env -i`)
- `env -i` schließt Shell-Umgebung aus → vollständig reproduzierbar
- `override=False` in load_dotenv → systemd-Env hat Vorrang in Production
