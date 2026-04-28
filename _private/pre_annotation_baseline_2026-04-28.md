# Pre-Annotation-Baseline — 2026-04-28 14:28

Snapshot der Pipeline VOR der eval-v4-Annotation. Vergleichsbasis für nach der Annotation.

## Pipeline-Stand

**Git-HEAD:**
```
5abaafd fix: eval_v3 reads must_contain_chunk_ids from top-level
```

**Aktive Flags:**
```
OPENLEX_REWRITE_ENABLED=true
OPENLEX_REWRITE_MODEL=mistral-medium-latest
OPENLEX_NORM_VALIDATOR_ENABLED=true
OPENLEX_INTENT_CLARIFY_ENABLED=true
OPENLEX_INTENT_ANALYSIS_ENABLED=true
OPENLEX_NORM_HYPOTHESIS_ENABLED=true
OPENLEX_NORM_HYPOTHESIS_INJECT_ENABLED=true
OPENLEX_NORM_HYPOTHESIS_PRIMARY=true
OPENLEX_PER_SOURCE_RETRIEVAL_ENABLED=true
OPENLEX_PER_SOURCE_BUDGET_ACTIVE=true
```

## A. eval_v3 vollständig (78 Queries, retrieval-only)

```
Fragen:    78
Dauer:     150.1s

Retrieval-Metriken:
  Hit@3    ██████░░░░░░░░░░░░░░ 0.332   nDCG=0.221   ForbHit=0.000
  Hit@5    ███████░░░░░░░░░░░░░ 0.352   nDCG=0.200   ForbHit=0.000
  Hit@10   ███████░░░░░░░░░░░░░ 0.378   nDCG=0.207   ForbHit=0.000
  MRR                             0.332

MRR pro Kategorie:
  pruefungsschemata         ██████████████░░░░░░ 0.727
  rechtsprechung            ██████████░░░░░░░░░░ 0.528
  behoerden                 ██████████░░░░░░░░░░ 0.500
  beschaeftigtendatenschutz ██████████░░░░░░░░░░ 0.500
  cookies_tracking          ██████████░░░░░░░░░░ 0.500
  drittlandtransfer         █████░░░░░░░░░░░░░░░ 0.259
  methodenwissen            █████░░░░░░░░░░░░░░░ 0.250
  rechtsgrundlagen          ████░░░░░░░░░░░░░░░░ 0.233
  allgemein                 ██░░░░░░░░░░░░░░░░░░ 0.105
  auftragsverarbeitung      ░░░░░░░░░░░░░░░░░░░░ 0.000
  betroffenenrechte         ░░░░░░░░░░░░░░░░░░░░ 0.000

Latenz (Warmup=3 exkl., n=75):
  Reranker mean=272ms  median=263ms  p95=414ms
  Total    mean=1538ms  median=1543ms  p95=1853ms
```

## B. Goldlabel-Verteilung im v3-Set

```
Queries mit Gold: 78
Queries ohne Gold: 0

Verteilung nach erstem Gold-Source-Type:
  gesetz_granular            67 queries (avg 2.9 gold-IDs)
  methodenwissen             11 queries (avg 1.0 gold-IDs)
```

Das v3-Set ist stark auf Gesetzes-Chunks fokussiert (86%) und enthält keine Urteilsfragen.
Das v4-Set wird durch die Real-Queries deutlich breiter sein.

## C. eval_v4 diagnostisch (178 Real-Queries, ohne Goldlabels)

**Total queries:** 178  
**Laufzeit:** 218s  
**Avg Latency:** 1227ms  
**P95 Latency:** 1717ms  
**Clarifications:** 0  
**Errors:** 0  

**Source-Type-Mix global (Top-10 über alle Queries):**

| Source-Type | Chunks | Anteil | Avg/Top-10 |
|---|---|---|---|
| leitlinie | 947 | 55.7% | 5.3 |
| urteil_segmentiert | 576 | 33.9% | 3.2 |
| gesetz_granular | 170 | 10.0% | 1.0 |
| methodenwissen | 6 | 0.4% | 0.0 |

### Interpretation

- **Leitlinien dominieren (55.7%):** Das Per-Source-Budget zieht stark auf Aufsichtsbehörden-Dokumente. Für v4-Real-Queries (praxisnah, beratungsorientiert) ist das plausibel.
- **Urteile stark präsent (33.9%):** Rechtsprechungs-Retrieval funktioniert — im v3-Set war kein Urteil im Gold.
- **Gesetze nur 10%:** Das Budget begrenzt gesetz_granular auf max. 4 Chunks. Wenn Goldlabels gesetzeslastig sind (wie im v3-Set), könnte Hit@K darunter leiden.
- **Methodenwissen marginal (0.4%):** MW-Chunks landen kaum in Top-10 — obwohl MW-Priorisierung aktiv ist. Möglicher Schwachpunkt.

## Was als Nächstes

1. Hendrik annotiert die 178 Queries (`must_contain_chunk_ids`)
2. Nach Annotation: `eval_v3.py --eval-set eval_sets/v4/queries_with_candidates.json --retrieval-only`
3. Vergleich Hit@K / MRR gegen diese Baseline → belegt Pipeline-Qualität für NLnet-Antrag
