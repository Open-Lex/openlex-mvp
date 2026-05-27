#!/usr/bin/env python3
"""
crossref_steckbriefe.py — Kopiert Steckbriefe in Sekundär-Collections,
damit sie auch dann gefunden werden, wenn der Intent-Router zu einer
Nachbar-Skill-Collection routed.

Format der Crossref-IDs: steckbrief_{name}_xref_{target_skill}
"""

import sys
from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_PATH = '/opt/openlex-mvp-v2/chromadb'

# Mapping: steckbrief_id → [(source_col, target_col), ...]
# Begründung steht als Kommentar
CROSSREF = {
    # ── BGB AT → kaufrecht ─────────────────────────────────────────────────────
    # Trierer Weinversteigerung: Erklärungsbewusstsein bei Versteigerung (Kauf-Kontext)
    'steckbrief_trierer_weinversteigerung': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],
    # Haakjöringsköd: Tiefkühlwalfleisch unter falschem Namen verkauft (falsa demonstratio → Kauf)
    'steckbrief_haakjoeringskoed': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],
    # Hyazinthen: Gefahrübergang bei Kauf von Pflanzen (Kaufrecht-Kontext)
    'steckbrief_hyazinthen': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],
    # Arglistige Täuschung Häuserkauf: § 123 BGB bei Immobilienkauf
    'steckbrief_arglistige_taeuschung_haus': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
        ('openlex_bgb_at', 'openlex_sachenrecht'),
    ],
    # Münzautomat: Bereicherungsrecht bei fehlgeschlagenem Kauf
    'steckbrief_muenzautomat': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],
    # Dreiecksverhältnis / Leistungskondiktion: bereicherungsrechtlicher Kaufkontext
    'steckbrief_dreiecksverhältnis_leistungskondiktion': [
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],

    # ── BGB AT → bank_kapitalmarktrecht ────────────────────────────────────────
    # Bürgschaft Sittenwidrigkeit: § 138 BGB Bankkredit-Bürgschaft
    'steckbrief_buergschaft_sittenwidrigkeit': [
        ('openlex_bgb_at', 'openlex_bank_kapitalmarktrecht'),
        ('openlex_bgb_at', 'openlex_familienrecht'),
    ],
    # Schrottimmobilien: Haustürwiderruf bei Bankfinanzierung
    'steckbrief_schrottimmobilien': [
        ('openlex_bgb_at', 'openlex_bank_kapitalmarktrecht'),
        ('openlex_bgb_at', 'openlex_kaufrecht'),
    ],
    # Blankounterschrift / Anscheinsvollmacht: Bankrecht-Kontext
    'steckbrief_blankounterschrift': [
        ('openlex_bgb_at', 'openlex_bank_kapitalmarktrecht'),
    ],
    # Verwirkung Kreditkündigung: § 242 BGB im Bankrecht
    'steckbrief_verwirkung_kreditkuendigung': [
        ('openlex_bgb_at', 'openlex_bank_kapitalmarktrecht'),
    ],

    # ── Strafrecht → weitere Skills ────────────────────────────────────────────
    # Lederspray: Produkthaftung → auch medizinrecht/verkehrsrecht-nahe
    'steckbrief_lederspray': [
        ('openlex_strafrecht', 'openlex_medizinrecht'),
    ],
    # Contergan: Arzneimittel-Strafrecht
    'steckbrief_contergan': [
        ('openlex_strafrecht', 'openlex_medizinrecht'),
    ],

    # ── Gesellschaftsrecht ↔ Handelsrecht ──────────────────────────────────────
    'steckbrief_autokran': [
        ('openlex_gesellschaftsrecht', 'openlex_handelsrecht'),
    ],
    'steckbrief_holzmueller': [
        ('openlex_gesellschaftsrecht', 'openlex_handelsrecht'),
    ],

    # ── Sachenrecht ↔ Kaufrecht ────────────────────────────────────────────────
    'steckbrief_parkettstaebefall': [
        ('openlex_sachenrecht', 'openlex_kaufrecht'),
    ],
    'steckbrief_linoleumrollen': [
        ('openlex_sachenrecht', 'openlex_kaufrecht'),
    ],
    'steckbrief_anwartschaftsrecht': [
        ('openlex_sachenrecht', 'openlex_kaufrecht'),
    ],
    'steckbrief_sicherungsübereignung_besitzkonstitut': [
        ('openlex_sachenrecht', 'openlex_bank_kapitalmarktrecht'),
    ],
}

def main():
    print('=== crossref_steckbriefe.py START ===', flush=True)
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    print('Lade Embedding-Modell...', flush=True)
    model = SentenceTransformer('mixedbread-ai/deepset-mxbai-embed-de-large-v1')
    print('Modell geladen.', flush=True)

    added_total = 0
    skipped_total = 0

    for steckbrief_id, targets in CROSSREF.items():
        for (src_col_name, tgt_col_name) in targets:
            xref_id = f'{steckbrief_id}_xref_{tgt_col_name.replace("openlex_", "")}'

            # Source
            try:
                src_col = client.get_collection(src_col_name)
            except Exception as e:
                print(f'  SKIP {src_col_name} not found: {e}', flush=True)
                continue

            src_res = src_col.get(ids=[steckbrief_id], include=['documents', 'metadatas'])
            if not src_res['ids']:
                print(f'  SKIP {steckbrief_id} not found in {src_col_name}', flush=True)
                continue

            doc = src_res['documents'][0]
            meta = dict(src_res['metadatas'][0])
            meta['xref_from'] = src_col_name
            meta['skill'] = tgt_col_name.replace('openlex_', '')

            # Target
            try:
                tgt_col = client.get_collection(tgt_col_name)
            except Exception as e:
                print(f'  SKIP {tgt_col_name} not found: {e}', flush=True)
                continue

            # Check if already exists
            existing = tgt_col.get(ids=[xref_id])
            if existing['ids']:
                print(f'  SKIP (exists) {xref_id}', flush=True)
                skipped_total += 1
                continue

            # Embed + add
            emb = model.encode([doc], normalize_embeddings=True).tolist()
            tgt_col.add(ids=[xref_id], documents=[doc], metadatas=[meta], embeddings=emb)
            print(f'  ADD  {xref_id} → {tgt_col_name}', flush=True)
            added_total += 1

    print(f'\n=== FERTIG: {added_total} hinzugefügt, {skipped_total} übersprungen ===', flush=True)

if __name__ == '__main__':
    main()
