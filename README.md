# OpenLex – Open Source Legal AI für deutsches und europäisches Datenschutzrecht

OpenLex ist ein Open-Source RAG-System (Retrieval-Augmented Generation), das rechtlich fundierte, halluzinationsfreie Antworten zum europäischen Datenschutzrecht liefert.

## Datenbestand

- **DSGVO**: Alle 99 Artikel mit Querverweisen zu 173 Erwägungsgründen und BDSG-Normen
- **BDSG, TDDDG, UWG, DDG**: Granular gechunkt
- **EuGH/EuG-Urteile**: ~100 Urteile, semantisch nach Vorlagefragen segmentiert
- **EDPB-Leitlinien**: ~1.650 Chunks (alle deutsch)
- **DSK-Dokumente**: 187 Dokumente der Datenschutzkonferenz
- **Methodenwissen**: 70 Prüfungsschemata und Abgrenzungen

## Qualität

| Metrik | Wert |
|---|---|
| Retrieval-Genauigkeit (v1 Quick) | 99,0% |
| Retrieval-Genauigkeit (v2 Quick) | 97,2% |
| Full-Run v1 (mit LLM) | 98,0% |
| Halluzinationen | 0 |
| Benchmark-Fragen | 614 |
| Chunks in Datenbank | 17.143 |

## Architektur

- **Embedding**: deepset-mxbai-embed-de-large-v1 (1024 dim, deutsch-optimiert)
- **Cross-Encoder**: mmarco-mMiniLMv2-L12-H384-v1
- **Vektordatenbank**: ChromaDB
- **LLM**: Kaskade aus Open-Source-Modellen (Qwen3-235B, Llama 3.3 70B, Gemma 3 27B via OpenRouter; Gemma 4 12B lokal via Ollama)
- **UI**: Gradio

## Lizenz

Dieses Projekt verwendet ein Multi-Lizenz-Modell:

### Code – AGPL-3.0
Alle Quelldateien (app.py, eval_openlex.py, parse_eugh.py, crawl_dsgvo_gesetz.py, bench_retrieval.py etc.) stehen unter der [GNU Affero General Public License v3.0](https://www.gnu.org/licenses/agpl-3.0.en.html).

**Was bedeutet das:** Jeder darf den Code nutzen, ändern und verbreiten – aber wer OpenLex als Service betreibt (auch über eine API oder Weboberfläche), muss den vollständigen Quellcode unter AGPL-3.0 veröffentlichen. Dies gilt auch für Modifikationen und abgeleitete Werke.

→ Siehe [LICENSE-CODE](LICENSE-CODE)

### Daten – CC-BY-SA-4.0
Methodenwissen-Chunks, Retrieval-Benchmarks, Evaluationsfragen, Querverweise und semantische Segmentierungen stehen unter [Creative Commons Attribution-ShareAlike 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

**Was bedeutet das:** Jeder darf diese Daten nutzen und weiterverarbeiten, auch kommerziell – aber mit Namensnennung (OpenLex / Hendrik Seidel) und unter gleicher Lizenz. Abgeleitete Datensätze müssen ebenfalls unter CC-BY-SA-4.0 veröffentlicht werden.

→ Siehe [LICENSE-DATA](LICENSE-DATA)

### Gesetzestexte, Urteile, Leitlinien – Public Domain
Rohe Gesetzes-, Urteils- und Leitlinientexte sind amtliche Werke und nach § 5 UrhG gemeinfrei. Die systematische Aufbereitung (Querverweise, Segmentierung, Metadaten) fällt unter CC-BY-SA-4.0 und das Datenbankherstellerrecht (§§ 87a ff. UrhG).

→ Siehe [LICENSE-RAWLAW](LICENSE-RAWLAW)

### Datenbankherstellerrecht (§§ 87a ff. UrhG)
Die Gesamtdatenbank (ChromaDB mit 17.143 Chunks, Querverweisen, semantischer Segmentierung und Metadaten-Anreicherung) ist als Datenbankwerk geschützt. Die Entnahme und Weiterverwendung wesentlicher Teile der Datenbank bedarf der Zustimmung des Herstellers.

## Canary Notice

Diese Datenbank enthält eingebettete Identifikationsmerkmale. Unautorisierte Entnahme wesentlicher Teile kann forensisch nachgewiesen werden.

## Kontakt

- **Website**: https://open-lex.cloud
- **GitHub**: https://github.com/Legalexpert/openlex-mvp
- **Autor**: Hendrik Seidel, Rechtsanwalt und Principal Legal Counsel
- **E-Mail**: [DEINE E-MAIL]

## Förderung

OpenLex ist ein unabhängiges Open-Source-Projekt. Förderanträge:
- EuroHPC AI Factory for Science (GPU-Zugang, eingereicht)
- NLnet Foundation NGI0 Commons Fund (in Vorbereitung, Deadline 01.06.2026)
- Prototype Fund (geplant, Deadline 30.11.2026)
