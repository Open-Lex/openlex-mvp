# K2.7-EVAL — Schatten-Eval Aggregat

**Stand:** 2026-05-10  
**Modell:** `intfloat/multilingual-e5-large`  
**Collections:** `/opt/openlex-sources/chromadb_shadow/`

## Ergebnisse pro Skill

| Skill | Queries | Hit@5 | Hit@10 | NDCG@10 | Embeddings |
|---|---:|---:|---:|---:|---:|
| ✅ steuerrecht | 5 | 100% | 100% | 0.86 | 131,622 |
| ✅ strafrecht | 5 | 100% | 100% | 0.96 | 184,704 |

**Median Hit@5:** 100% | **Hit@10:** 100% | **NDCG@10:** 0.91

## Schwellen

| Hit@5 | Bewertung |
|---|---|
| ≥ 80% | ✅ exzellent |
| 60–80% | ⚠️ gut, NLnet-tauglich |
| 40–60% | ⚠️ brauchbar |
| < 40% | ❌ Diagnose nötig |

## NLnet-Aussage

> Schatten-Eval auf 2 K3a-Collections (multilingual-e5-large), je 5 juristische Test-Queries:  
> **Median Hit@5 = 100%, Hit@10 = 100%**