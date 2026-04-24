#!/usr/bin/env python3
"""Löscht 43 Boilerplate-Chunk_0 aus ChromaDB (bund_rechtsprechung.de Nav-Text)."""
import sys
import re
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

col = chromadb.PersistentClient("/opt/openlex-mvp/chromadb").get_collection("openlex_datenschutz")
nav_pat = re.compile(r"Startseite\s*[\n\s]*Entscheidungs", re.IGNORECASE)

# ── Alle Urteile laden ────────────────────────────────────────────────────────
ids, metas, docs = [], [], []
offset = 0
while True:
    r = col.get(limit=5000, offset=offset,
                where={"source_type": "urteil"},
                include=["metadatas", "documents"])
    if not r["ids"]: break
    ids.extend(r["ids"])
    metas.extend(r.get("metadatas") or [{}] * len(r["ids"]))
    docs.extend(r.get("documents") or [""] * len(r["ids"]))
    if len(r["ids"]) < 5000: break
    offset += 5000

# ── Boilerplate-Chunks identifizieren ────────────────────────────────────────
to_delete = []
no_content_cases = []

for cid, m, d in zip(ids, metas, docs):
    if not nav_pat.search((d or "")[:1500]):
        continue
    m = m or {}
    to_delete.append(cid)
    if m.get("total_chunks", 99) == 1:
        no_content_cases.append({
            "chunk_id": cid,
            "gericht": m.get("gericht"),
            "aktenzeichen": m.get("aktenzeichen"),
            "leitsatz": m.get("leitsatz", "")[:200],
            "reason": "total_chunks=1, nur Boilerplate, kein Volltext im Korpus",
        })

print(f"Zu löschende Chunks: {len(to_delete)}")
print(f"Urteile ohne verbleibenden Volltext: {len(no_content_cases)}")
for c in no_content_cases:
    print(f"  ⚠  {c['gericht']} {c['aktenzeichen']} — {c['leitsatz'][:80]}")

# ── Löschen ───────────────────────────────────────────────────────────────────
print(f"\nLösche {len(to_delete)} Chunks...")
col.delete(ids=to_delete)
print("Gelöscht.")

# ── Verify ────────────────────────────────────────────────────────────────────
remaining = col.get(ids=to_delete, include=[])
still_present = remaining["ids"]
if still_present:
    print(f"⚠  Noch vorhanden nach Löschung: {still_present}")
else:
    print(f"✅ Alle {len(to_delete)} Chunks erfolgreich gelöscht.")

# ── Log ───────────────────────────────────────────────────────────────────────
log = {
    "timestamp": datetime.now().isoformat(),
    "action": "delete_boilerplate_chunks",
    "deleted_count": len(to_delete),
    "deleted_ids": to_delete,
    "no_content_cases": no_content_cases,
}
log_path = Path("/opt/openlex-mvp/logs/corpus_patches.jsonl")
log_path.parent.mkdir(exist_ok=True)
with open(log_path, "a") as f:
    f.write(json.dumps(log, ensure_ascii=False) + "\n")
print(f"Log: {log_path}")

# ── Neue Gesamtzahl ───────────────────────────────────────────────────────────
total_after = col.count()
print(f"\nChromaDB gesamt nach Patch: {total_after}")
