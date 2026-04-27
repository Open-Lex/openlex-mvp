#!/usr/bin/env python3
"""
Test-Suite für per_source_retrieval auf 10 Queries.
Output: Markdown-Report für Sichtprüfung.
"""
import sys, time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "/opt/openlex-mvp")
from per_source_retrieval import per_source_query, merge_with_type_budget


def get_embed_fn():
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(
        "mixedbread-ai/deepset-mxbai-embed-de-large-v1",
        prompts={"query": "query: "},
        default_prompt_name="query",
    )
    def embed(text):
        return model.encode(text)
    return embed


TEST_QUERIES = [
    "Darf mein Arbeitgeber meine E-Mails lesen?",
    "Was ist eine Auftragsverarbeitung?",
    "Sind Cookies ohne Einwilligung erlaubt?",
    "Kann ich Schadensersatz nach SCHUFA-Urteil verlangen?",
    "Welche Rechte habe ich nach DSGVO?",
    "Wann ist eine DSFA verpflichtend?",
    "Datenschutz im Verein",
    "Wie lange darf eine Bewerbung gespeichert werden?",
    "Was hat der EuGH zu Schrems II entschieden?",
    "Welche rechtlichen Anforderungen gelten für biometrische Daten?",
]


def main():
    print("Loading embedding model...")
    embed_fn = get_embed_fn()

    out_dir = Path("/opt/openlex-mvp/_private")
    out_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_path = out_dir / f"per_source_test_{today}.md"

    total_emb_ms = 0.0
    total_retrieval_ms = 0.0

    lines = [
        f"# Per-Source-Retrieval Test — {today}",
        "",
        f"Test-Queries: {len(TEST_QUERIES)}",
        "",
        "## Pro Query: Top-Chunks pro Source-Type + Budget-Resultat",
        "",
    ]

    for i, q in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/{len(TEST_QUERIES)}] {q[:60]}")

        result = per_source_query(q, embed_fn)
        total_emb_ms += result.query_embedding_duration_ms
        total_retrieval_ms += result.total_duration_ms

        lines.append(f"### {i}. {q}")
        lines.append("")
        lines.append(
            f"Embedding: {result.query_embedding_duration_ms:.0f}ms · "
            f"Retrieval: {result.total_duration_ms:.0f}ms · "
            f"Chunks total: {result.total_chunks}"
        )
        lines.append("")

        for source_type, src in result.per_source.items():
            err = f" ⚠️ {src.error}" if src.error else ""
            lines.append(f"**{source_type}** ({src.duration_ms:.0f}ms, {len(src.chunk_ids)} chunks){err}:")
            lines.append("")
            for cid, dist, meta, doc in zip(
                src.chunk_ids[:3], src.distances[:3],
                src.metadatas[:3], src.documents[:3],
            ):
                snippet = (doc or "")[:120].replace("\n", " ")
                gesetz = meta.get("gesetz", "")
                volladr = (meta.get("volladresse") or meta.get("artikel") or
                           meta.get("thema") or meta.get("titel") or "")
                gericht = meta.get("gericht", "")
                az = meta.get("aktenzeichen", "")
                identifier = volladr or f"{gericht} {az}".strip() or cid[:40]
                lines.append(f"- `{cid}` | dist={dist:.3f} | {gesetz} {identifier}")
                lines.append(f"  > {snippet}")
            lines.append("")

        merged = merge_with_type_budget(result)
        budget_counts: dict = {}
        for c in merged:
            st = c["source_type"]
            budget_counts[st] = budget_counts.get(st, 0) + 1

        lines.append(f"**Nach Typ-Budget ({len(merged)} Chunks):**")
        lines.append("")
        for st, n in sorted(budget_counts.items()):
            lines.append(f"- {st}: {n}")
        lines.append("")
        lines.append("Top-8 nach Distance:")
        for c in merged[:8]:
            meta = c["metadata"]
            volladr = (meta.get("volladresse") or meta.get("artikel") or
                       meta.get("thema") or meta.get("titel") or "")
            gesetz = meta.get("gesetz", "")
            gericht = meta.get("gericht", "")
            az = meta.get("aktenzeichen", "")
            identifier = volladr or f"{gericht} {az}".strip() or c["chunk_id"][:40]
            lines.append(
                f"- `{c['chunk_id']}` [{c['source_type']}] | "
                f"dist={c['distance']:.3f} | {gesetz} {identifier}"
            )
        lines.append("")
        lines.append("**Bewertung:**")
        lines.append("- [ ] ✅ Pro Source sinnvolle Top-Chunks UND Budget liefert gute Mischung")
        lines.append("- [ ] ⚠️ Pro Source OK, aber Budget verdrängt wichtige Chunks")
        lines.append("- [ ] ❌ Pro Source zeigt schon falsche Chunks")
        lines.append("")
        lines.append("---")
        lines.append("")

    avg_emb = total_emb_ms / len(TEST_QUERIES)
    avg_ret = total_retrieval_ms / len(TEST_QUERIES)

    lines.extend([
        "## Aggregierte Bewertung (von Hendrik auszufüllen)",
        "",
        "Nach Sichtprüfung der 10 Fälle:",
        "- Anteil ✅: ___ / 10",
        "- Anteil ⚠️: ___ / 10",
        "- Anteil ❌: ___ / 10",
        "",
        "**Performance:**",
        f"- Avg Embedding: {avg_emb:.0f}ms",
        f"- Avg Retrieval (5 Calls): {avg_ret:.0f}ms",
        f"- Avg Total: {avg_emb + avg_ret:.0f}ms",
        "",
        "**Entscheidung:**",
        "- [ ] Per-Source-Retrieval funktioniert gut → weiter mit Schritt 2.2",
        "- [ ] Probleme bei bestimmten Source-Types (welche?): ___",
        "- [ ] Performance zu langsam, Optimierung nötig",
    ])

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {out_path}")
    print(f"Avg Embedding: {avg_emb:.0f}ms | Avg Retrieval: {avg_ret:.0f}ms | Avg Total: {avg_emb+avg_ret:.0f}ms")


if __name__ == "__main__":
    main()
