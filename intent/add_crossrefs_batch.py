#!/usr/bin/env python3
"""
add_crossrefs_batch.py — Batch version, much faster.
Groups by source collection, fetches all docs at once,
batch-embeds, then batch-adds to target collections.
"""
import json
import sys
from collections import defaultdict
from sentence_transformers import SentenceTransformer
import chromadb

CHROMA_PATH = '/opt/openlex-mvp-v2/chromadb'
CROSSREFS_PATH = '/tmp/missing_crossrefs.json'
MODEL_NAME = 'mixedbread-ai/deepset-mxbai-embed-de-large-v1'
BATCH_SIZE = 32

def main():
    print('=== add_crossrefs_batch.py START ===', flush=True)

    with open(CROSSREFS_PATH, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    print(f'Loaded {len(entries)} entries to process', flush=True)

    client = chromadb.PersistentClient(path=CHROMA_PATH)

    print('Loading embedding model...', flush=True)
    model = SentenceTransformer(MODEL_NAME)
    print('Model loaded.', flush=True)

    # Build cache of open collections
    col_cache = {}
    def get_col(name):
        if name not in col_cache:
            try:
                col_cache[name] = client.get_collection(name)
            except Exception as e:
                col_cache[name] = None
                print(f'  WARN: Collection {name} not found: {e}', flush=True)
        return col_cache[name]

    # Group entries by source collection for efficient batch fetching
    by_source = defaultdict(list)
    for entry in entries:
        by_source[entry['from']].append(entry)

    added = 0
    skipped_exists = 0
    skipped_not_found = 0
    errors = 0

    for src_col_name, group in by_source.items():
        print(f'\n--- Source: {src_col_name} ({len(group)} entries) ---', flush=True)

        src_col = get_col(src_col_name)
        if src_col is None:
            skipped_not_found += len(group)
            continue

        # Fetch all unique steckbrief IDs from this source at once
        unique_ids = list(set(e['id'] for e in group))
        try:
            src_res = src_col.get(ids=unique_ids, include=['documents', 'metadatas'])
        except Exception as e:
            print(f'  ERROR fetching from {src_col_name}: {e}', flush=True)
            errors += len(group)
            continue

        # Build id→(doc, meta) map
        doc_map = {}
        for i, doc_id in enumerate(src_res['ids']):
            doc_map[doc_id] = (src_res['documents'][i], dict(src_res['metadatas'][i]))

        # Group by target collection
        by_target = defaultdict(list)
        for entry in group:
            sid = entry['id']
            if sid not in doc_map:
                print(f'  SKIP {sid} not found in {src_col_name}', flush=True)
                skipped_not_found += 1
                continue
            by_target[entry['to']].append(entry)

        # For each target collection, batch check existence and add
        for tgt_col_name, tgt_group in by_target.items():
            tgt_col = get_col(tgt_col_name)
            if tgt_col is None:
                skipped_not_found += len(tgt_group)
                continue

            target_skill = tgt_col_name.replace('openlex_', '')

            # Compute xref IDs and check which already exist
            xref_ids = [f"{e['id']}_xref_{target_skill}" for e in tgt_group]
            try:
                existing_res = tgt_col.get(ids=xref_ids)
                existing_set = set(existing_res['ids'])
            except Exception as e:
                print(f'  ERROR checking exists in {tgt_col_name}: {e}', flush=True)
                existing_set = set()

            # Filter to only new ones
            to_add_ids = []
            to_add_docs = []
            to_add_metas = []
            for entry, xref_id in zip(tgt_group, xref_ids):
                if xref_id in existing_set:
                    skipped_exists += 1
                    continue
                doc, orig_meta = doc_map[entry['id']]
                meta = dict(orig_meta)
                meta['xref_from'] = src_col_name
                meta['skill'] = target_skill
                to_add_ids.append(xref_id)
                to_add_docs.append(doc)
                to_add_metas.append(meta)

            if not to_add_ids:
                print(f'  {tgt_col_name}: all {len(tgt_group)} already exist', flush=True)
                continue

            # Batch embed
            try:
                embeddings = model.encode(
                    to_add_docs,
                    batch_size=BATCH_SIZE,
                    normalize_embeddings=True,
                    show_progress_bar=False
                ).tolist()
            except Exception as e:
                print(f'  ERROR embedding for {tgt_col_name}: {e}', flush=True)
                errors += len(to_add_ids)
                continue

            # Add in one batch
            try:
                tgt_col.add(
                    ids=to_add_ids,
                    documents=to_add_docs,
                    metadatas=to_add_metas,
                    embeddings=embeddings
                )
                print(f'  ADD {len(to_add_ids):3d} → {tgt_col_name}', flush=True)
                for xid in to_add_ids:
                    print(f'    {xid}', flush=True)
                added += len(to_add_ids)
            except Exception as e:
                print(f'  ERROR adding to {tgt_col_name}: {e}', flush=True)
                errors += len(to_add_ids)

    print(f'\n=== FERTIG ===', flush=True)
    print(f'  Hinzugefügt:         {added}', flush=True)
    print(f'  Bereits vorhanden:   {skipped_exists}', flush=True)
    print(f'  Nicht gefunden:      {skipped_not_found}', flush=True)
    print(f'  Fehler:              {errors}', flush=True)

if __name__ == '__main__':
    main()
