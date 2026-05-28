#!/usr/bin/env python3
"""
add_new_xrefs.py — Cross-Referenzen für die 51 neuen Steckbriefe in verwandte Skills
"""
import sys
from datetime import datetime
from collections import defaultdict
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "/opt/openlex-mvp-v2/chromadb"
LOG_FILE    = "/tmp/add_new_xrefs.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

# ─── Xref-Mapping: (source_id, source_skill) → [target_skill, ...]
# Format: ("steckbrief_id", "source_skill", ["target1", "target2", ...])
XREFS = [
    # ── verbraucherrecht ─────────────────────────────────────────────────────
    ("steckbrief_heininger_eugh",            "verbraucherrecht", ["kaufrecht"]),
    ("steckbrief_quelle_nachlieferung_eugh", "verbraucherrecht", ["kaufrecht"]),
    ("steckbrief_weber_putz_eugh",           "verbraucherrecht", ["kaufrecht"]),
    ("steckbrief_vw_abgasskandal_826",       "verbraucherrecht", ["kaufrecht", "verkehrsrecht"]),
    ("steckbrief_planet49_eugh",             "verbraucherrecht", ["datenschutz", "it_recht"]),
    ("steckbrief_gut_springenheide_eugh",    "verbraucherrecht", ["kaufrecht"]),

    # ── reiserecht ───────────────────────────────────────────────────────────
    ("steckbrief_sturgeon_eugh",             "reiserecht", ["transportrecht", "verbraucherrecht"]),
    ("steckbrief_wallentin_hermann_eugh",    "reiserecht", ["transportrecht"]),
    ("steckbrief_mcdonagh_vulkanasche_eugh", "reiserecht", ["transportrecht", "verbraucherrecht"]),
    ("steckbrief_bgh_reisemangel_hotel",     "reiserecht", ["verbraucherrecht"]),
    ("steckbrief_bgh_reiselaerm",            "reiserecht", ["verbraucherrecht"]),

    # ── versicherungsrecht ───────────────────────────────────────────────────
    ("steckbrief_test_achats_eugh",                          "versicherungsrecht", ["europarecht", "grundrechte"]),
    ("steckbrief_bgh_lebensversicherung_rueckkauf",          "versicherungsrecht", ["verbraucherrecht", "bgb_at"]),
    ("steckbrief_bgh_berufsunfaehigkeit",                    "versicherungsrecht", ["arbeitsrecht"]),
    ("steckbrief_bgh_versicherung_arglistige_anzeigepflichtverletzung", "versicherungsrecht", ["bgb_at"]),
    ("steckbrief_bgh_versicherung_obliegenheit",             "versicherungsrecht", ["bgb_at"]),

    # ── transportrecht ───────────────────────────────────────────────────────
    ("steckbrief_bgh_cmr_haftung",                "transportrecht", ["handelsrecht"]),
    ("steckbrief_montreal_walz_eugh",             "transportrecht", ["reiserecht"]),
    ("steckbrief_bgh_spediteur_adsp",             "transportrecht", ["handelsrecht"]),
    ("steckbrief_bgh_frachtfuehrer_rollende_ladung", "transportrecht", ["handelsrecht"]),
    ("steckbrief_eugh_air_berlin_flugaussetzung", "transportrecht", ["reiserecht", "insolvenzrecht"]),

    # ── bildungsrecht ────────────────────────────────────────────────────────
    ("steckbrief_bverfg_numerus_clausus",         "bildungsrecht", ["grundrechte", "verwaltungsrecht", "verwaltungsprozessrecht"]),
    ("steckbrief_bverfg_kopftuch_ludin",          "bildungsrecht", ["grundrechte", "kirchenrecht"]),
    ("steckbrief_bverfg_kopftuch_2015",           "bildungsrecht", ["grundrechte", "kirchenrecht"]),
    ("steckbrief_bverwg_schulpflicht_homeschooling", "bildungsrecht", ["grundrechte", "kirchenrecht", "verwaltungsrecht"]),
    ("steckbrief_bverfg_bafog_gleichheit",        "bildungsrecht", ["sozialrecht", "grundrechte"]),

    # ── kirchenrecht ─────────────────────────────────────────────────────────
    ("steckbrief_bverfg_kruzifix",                    "kirchenrecht", ["grundrechte", "bildungsrecht"]),
    ("steckbrief_bag_kuendigung_kirchenaustritt",     "kirchenrecht", ["arbeitsrecht"]),
    ("steckbrief_eugh_kirchliches_arbeitsrecht_ir_jq","kirchenrecht", ["arbeitsrecht", "europarecht"]),
    ("steckbrief_bverfg_kirchensteuer_kirchenaustritt","kirchenrecht", ["steuerrecht", "grundrechte"]),
    ("steckbrief_bverfg_kirchenautonomie_loyalitaet", "kirchenrecht", ["arbeitsrecht"]),

    # ── voelkerstrafrecht ────────────────────────────────────────────────────
    ("steckbrief_icty_tadic_zustaendigkeit",          "voelkerstrafrecht", ["voelkerrecht"]),
    ("steckbrief_icc_lubanga_kindsoldaten",           "voelkerstrafrecht", ["voelkerrecht"]),
    ("steckbrief_icc_al_bashir_haftbefehl",           "voelkerstrafrecht", ["voelkerrecht", "sanktionsrecht"]),
    ("steckbrief_icc_katanga_mittelbare_taeterschaft","voelkerstrafrecht", ["strafrecht", "voelkerrecht"]),
    ("steckbrief_bgh_vstgb_vorgesetztenverantwortlichkeit","voelkerstrafrecht", ["strafrecht", "voelkerrecht"]),

    # ── sanktionsrecht ───────────────────────────────────────────────────────
    ("steckbrief_eugh_kadi_i",              "sanktionsrecht", ["europarecht", "voelkerrecht"]),
    ("steckbrief_eugh_kadi_ii",             "sanktionsrecht", ["europarecht", "voelkerrecht"]),
    ("steckbrief_eugh_rosneft_sanktionen",  "sanktionsrecht", ["europarecht", "energierecht"]),
    ("steckbrief_eugh_bank_melli_iran",     "sanktionsrecht", ["europarecht", "handelsrecht"]),
    ("steckbrief_eugh_yusuf_al_barakaat",   "sanktionsrecht", ["europarecht", "voelkerrecht"]),

    # ── waffenrecht ──────────────────────────────────────────────────────────
    ("steckbrief_bverwg_waffenzuverlaessigkeit_straftat",    "waffenrecht", ["verwaltungsrecht", "strafrecht", "polizei_ordnungsrecht"]),
    ("steckbrief_bverwg_waffenrecht_psychische_erkrankung",  "waffenrecht", ["verwaltungsrecht"]),
    ("steckbrief_bverwg_sportschuetze_beduerfen",            "waffenrecht", ["verwaltungsrecht"]),
    ("steckbrief_vgh_bayer_waffenrecht_extremismus",         "waffenrecht", ["verwaltungsrecht", "polizei_ordnungsrecht", "verwaltungsprozessrecht"]),
    ("steckbrief_bverwg_kriegswaffenkontrolle",              "waffenrecht", ["verwaltungsrecht"]),

    # ── voelkerrecht ─────────────────────────────────────────────────────────
    ("steckbrief_igh_corfu_channel",        "voelkerrecht", ["voelkerstrafrecht"]),
    ("steckbrief_igh_barcelona_traction",   "voelkerrecht", ["handelsrecht", "gesellschaftsrecht"]),
    ("steckbrief_igh_nicaragua_usa",        "voelkerrecht", ["voelkerstrafrecht"]),
    ("steckbrief_igh_atomwaffen_gutachten", "voelkerrecht", ["voelkerstrafrecht"]),
    ("steckbrief_igh_kosovo_gutachten",     "voelkerrecht", ["staatsorganisationsrecht"]),
]

def embed_batch(model, texts, batch_size=16):
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, prompt_name="passage", batch_size=batch_size,
                            show_progress_bar=False, normalize_embeddings=True)
        all_embs.extend(embs.tolist())
    return all_embs

def main():
    log("=" * 60)
    log("add_new_xrefs.py — START")
    log(f"Geplante Xrefs: {len(XREFS)} Einträge (→ mehrere Targets möglich)")
    log("=" * 60)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    existing_cols = {c.name for c in client.list_collections()}

    log("Lade Embedding-Modell...")
    model = SentenceTransformer('mixedbread-ai/deepset-mxbai-embed-de-large-v1')
    log("Modell geladen.")

    # Sammle alle (source_col, xref_id) → (doc, meta, target_col) Paare
    # Gruppiert nach source_col für effizienten Batch-Fetch
    by_source = defaultdict(list)
    for sb_id, src_skill, targets in XREFS:
        src_col_name = f"openlex_{src_skill}"
        for tgt_skill in targets:
            tgt_col_name = f"openlex_{tgt_skill}"
            if src_col_name not in existing_cols:
                log(f"  ⚠️  Quelle {src_col_name} nicht gefunden — überspringe")
                continue
            if tgt_col_name not in existing_cols:
                log(f"  ⚠️  Ziel {tgt_col_name} nicht gefunden — überspringe")
                continue
            by_source[src_col_name].append({
                "sb_id": sb_id,
                "tgt_col_name": tgt_col_name,
                "tgt_skill": tgt_skill,
            })

    total_added = 0
    total_skip  = 0

    for src_col_name, entries in sorted(by_source.items()):
        src_col = client.get_collection(src_col_name)

        # Fetch all needed source docs in one call
        needed_ids = list({e["sb_id"] for e in entries})
        result = src_col.get(ids=needed_ids, include=["documents", "metadatas"])
        src_map = {rid: (doc, meta)
                   for rid, doc, meta in zip(result["ids"], result["documents"], result["metadatas"])}

        # Group by target collection
        by_target = defaultdict(list)
        for e in entries:
            if e["sb_id"] not in src_map:
                log(f"  ⚠️  {e['sb_id']} nicht in {src_col_name} gefunden")
                continue
            by_target[e["tgt_col_name"]].append(e)

        for tgt_col_name, tgt_entries in sorted(by_target.items()):
            tgt_col = client.get_collection(tgt_col_name)
            tgt_skill = tgt_entries[0]["tgt_skill"]

            to_add_ids, to_add_docs, to_add_metas = [], [], []
            for e in tgt_entries:
                sb_id = e["sb_id"]
                xref_id = f"{sb_id}_xref_{tgt_skill}"

                # Dedup check
                if tgt_col.get(ids=[xref_id])["ids"]:
                    total_skip += 1
                    continue

                orig_doc, orig_meta = src_map[sb_id]
                new_meta = dict(orig_meta)
                new_meta["xref_from"] = src_col_name
                new_meta["skill"]     = tgt_skill
                new_meta["source_type"] = "urteil"  # keep same type

                to_add_ids.append(xref_id)
                to_add_docs.append(orig_doc)
                to_add_metas.append(new_meta)

            if not to_add_ids:
                continue

            embs = embed_batch(model, to_add_docs)
            for i in range(0, len(to_add_ids), 64):
                tgt_col.add(
                    ids=to_add_ids[i:i+64],
                    documents=to_add_docs[i:i+64],
                    metadatas=to_add_metas[i:i+64],
                    embeddings=embs[i:i+64],
                )
            total_added += len(to_add_ids)
            log(f"  {src_col_name} → {tgt_col_name}: +{len(to_add_ids)} Xrefs")

    log(f"\n{'='*60}")
    log(f"FERTIG: {total_added} neue Xrefs, {total_skip} bereits vorhanden")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
