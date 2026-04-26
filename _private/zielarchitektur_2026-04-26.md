# Zielarchitektur OpenLex — Stand 26.04.2026

## Grundprinzip
Recht ist Entscheidungslogik auf Normhierarchien, nicht Textsuche.

## Sechs-Schritt-Pipeline (Soll-Zustand)

### Schritt 1: Intent + juristische Struktur
- Klassifizierung der Frage (Definition, Subsumtion, Handlung, Rechtsprechung, Prozedural)
- Erkennung beteiligter Rollen (Arbeitnehmer, Arbeitgeber, Verantwortlicher, Betroffener)
- Erkennung der juristischen Dimension (Rechtsgrundlage, Rechte, Pflichten)

### Schritt 2: Norm-Hypothese
- LLM oder regelbasiert: Welche Normen sind plausibel einschlägig?
- Output: priorisierte Liste von Norm-Hypothesen (Art. X DSGVO, § Y BDSG, ...)
- KEY: mehrere Hypothesen, nicht eine umgeschriebene Query

### Schritt 3: Gezieltes Retrieval
- Pro Norm-Hypothese: gezielte Suche
- Pro Source-Type separat: Gesetz, Urteil, Leitlinie, Methodenwissen
- Embedding + ggf. BM25 + Norm-Filter via Metadata

### Schritt 4: Evidenz-Auswahl
- 2–4 Gesetzes-Chunks (höchste Priorität)
- 0–2 Urteils-Chunks (wenn Auslegung relevant)
- 0–2 Leitlinien-Chunks (wenn Praxisanwendung relevant)
- 0–1 Methodenwissens-Chunk (zur Strukturierung)
- Insgesamt 6–8 Chunks max
- Diversifizierung: Gesetz dominiert, andere ergänzen

### Schritt 5: Subsumtion (LLM)
- LLM bekommt: Frage + 6–8 Chunks + Methodenwissen-Hinweis (Prüfungsstruktur)
- Aufgabe: Sachverhalt unter Norm subsumieren
- Output-Struktur fix: Einordnung → Norm → Anwendung → Ergebnis

### Schritt 6: Grounded Generation + Validation
- Jede Aussage muss durch zitierten Chunk belegt sein
- Norm-Validator (deterministisch) prüft Zitate
- Bei fehlendem Kontext: Rückfrage statt Antwort

## Zielzustand der Daten

### Gesetze
- Granularität: Artikel → Absätze (Standard)
- Metadata: gesetz, artikel/paragraph, absatz, version
- KEINE kompletten Artikel als Standard-Chunk

### Urteile
- Segmentierung: Leitsatz, relevante Begründungspassagen, Subsumtionsstellen
- KEINE 2500-Zeichen-Blöcke
- Metadata: gericht, aktenzeichen, datum, betroffene_normen (Liste)

### Leitlinien
- Thematische Mini-Chunks (< 500 Zeichen)
- Metadata: betrifft_normen (Liste), quelle (EDPB, DSK), datum

### Methodenwissen
- Sehr klein (1 Gedanke pro Chunk)
- Metadata: aspekt (Prüfungsstruktur, Subsumtion, Abwägung), priority

## Was NICHT zur Zielarchitektur gehört
- Komplexe Pipeline mit aggressiven Reranking-Heuristiken und vielen Multiplikatoren
- Boost-Systeme mit Korrekturfaktoren auf CE-Scores
- Cross-Encoder als zentraler Filter (nur als Sort-Schritt)
- Max-15-Dokumente-Kontextfenster mit Diversifizierungslogik
