#!/usr/bin/env python3
"""
Leitet `paragraph`, `absatz`, `satz` aus BDSG-chunk_ids ab und patcht Metadata.

Chunk-ID-Schema: gran_BDSG_§_26_Abs.1_S.3
- paragraph = 26
- absatz    = 1  (optional)
- satz      = 3  (optional)

Idempotent: zweiter Lauf ändert nichts.
DRY-RUN per Default; --apply um zu schreiben.
"""
import sys
import re

sys.path.insert(0, "/opt/openlex-mvp")
import chromadb

client = chromadb.PersistentClient(path="/opt/openlex-mvp/chromadb")
col = client.get_collection("openlex_datenschutz")

# Regex für chunk_id wie "gran_BDSG_§_26_Abs.1_S.3"
_PARA_RE  = re.compile(r"BDSG_§_(\d+[a-z]?)", re.IGNORECASE)
_ABS_RE   = re.compile(r"_Abs\.(\d+)", re.IGNORECASE)
_SATZ_RE  = re.compile(r"_S\.(\d+)", re.IGNORECASE)


def parse_id(cid: str) -> tuple[str | None, str | None, str | None]:
    para   = (m := _PARA_RE.search(cid)) and m.group(1) or None
    absatz = (m := _ABS_RE.search(cid))  and m.group(1) or None
    satz   = (m := _SATZ_RE.search(cid)) and m.group(1) or None
    return para, absatz, satz


def load_bdsg():
    ids, metas = [], []
    offset = 0
    while True:
        r = col.get(limit=5000, offset=offset, include=["metadatas"])
        if not r["ids"]:
            break
        for cid, m in zip(r["ids"], r.get("metadatas") or []):
            m = m or {}
            if m.get("gesetz", "").upper() == "BDSG":
                ids.append(cid)
                metas.append(m)
        if len(r["ids"]) < 5000:
            break
        offset += 5000
    return ids, metas


def main(apply: bool = False):
    ids, metas = load_bdsg()
    print(f"BDSG-Chunks: {len(ids)}")

    changes = []
    unparseable = []

    for cid, old_m in zip(ids, metas):
        para, absatz, satz = parse_id(cid)
        if not para:
            unparseable.append(cid)
            continue

        new_m = dict(old_m)
        updated = False

        for field, val in [("paragraph", para), ("absatz", absatz), ("satz", satz)]:
            if val and old_m.get(field) != val:
                new_m[field] = val
                updated = True

        if updated:
            changes.append((cid, old_m, new_m))

    print(f"Zu patchen:  {len(changes)}")
    print(f"Unparseable: {len(unparseable)}")
    if unparseable:
        print("Samples unparseable:")
        for cid in unparseable[:10]:
            print(f"  {cid}")

    # Preview
    print("\n=== Preview erste 10 Änderungen ===")
    for cid, old, new in changes[:10]:
        diff_keys = [k for k in ("paragraph", "absatz", "satz") if old.get(k) != new.get(k)]
        print(f"  {cid}")
        for k in diff_keys:
            print(f"    {k}: {old.get(k)!r} → {new.get(k)!r}")

    if not apply:
        print("\n(DRY-RUN — nichts geschrieben. --apply zum Patchen.)")
        return 0

    print(f"\nWende {len(changes)} Updates an...")
    batch_size = 500
    for i in range(0, len(changes), batch_size):
        b = changes[i : i + batch_size]
        col.update(ids=[c[0] for c in b], metadatas=[c[2] for c in b])
        print(f"  {min(i + batch_size, len(changes))}/{len(changes)}")
    print("Fertig.")
    return 0


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
