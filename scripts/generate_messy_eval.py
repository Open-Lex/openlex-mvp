#!/usr/bin/env python3
"""
Messy-Eval-Generator – Umgangssprachliche Queries aus canonical_v3.json.

Für jede Canonical-Query eine Variante ohne Fachbegriffe, mit konkretem
Kontext, schwer zu retrieven (keine direkten Norm-Keywords).

Gold-IDs (must/should/forbidden) werden 1:1 aus canonical_v3 übernommen.

Verwendung:
  python scripts/generate_messy_eval.py --limit 5
  python scripts/generate_messy_eval.py --all
  python scripts/generate_messy_eval.py --all --resume
  python scripts/generate_messy_eval.py --all --overwrite
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

CANONICAL_PATH = BASE_DIR / "eval_sets" / "canonical_v3.json"
DEFAULT_OUTPUT  = BASE_DIR / "eval_sets" / "messy.json"

MISTRAL_KEY    = os.getenv("MISTRAL_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY", "")
MISTRAL_MODEL  = "mistral-medium-latest"
OR_MODEL       = "qwen/qwen3-8b:free"

PROMPT_TEMPLATE = """\
Du bekommst eine juristisch formulierte Frage zum Datenschutzrecht.

Formuliere sie so um, wie sie ein juristischer Laie in einer echten Situation stellen würde:
- Konkreter Kontext (konkrete Branche, Situation, Rolle)
- Keine Paragraphen, keine lateinischen Fachbegriffe
- Umgangssprache, aber nicht unverständlich
- Die juristische Kernfrage bleibt dieselbe
- Nicht wörtlich aus der Original-Frage umschreiben — echte Neuformulierung

Wichtig: Die Messy-Frage soll SCHWER zu retrieven sein. Vermeide Keywords, \
die direkt mit den Norm-Titeln matchen. Stattdessen: Situations-Beschreibung.

Länge: Maximal 2-3 Sätze. Kurz und prägnant, kein Monolog.
Opener: Variiere den Einstieg – nicht immer mit "Wir" oder "Unser" beginnen, keine Markdown-Formatierung, keine Anführungszeichen um die ganze Frage.

Original-Frage (canonical):
{canonical_question}

Ursprüngliches Thema (intern, nur als Kontext — NICHT in der Messy-Frage erwähnen):
{thema}

Output: NUR die Messy-Frage als String, nichts drumherum. Maximal 200 Zeichen."""


def call_llm(prompt: str, retries: int = 3) -> tuple[str, int, int]:
    import urllib.request

    model  = MISTRAL_MODEL if MISTRAL_KEY else OR_MODEL
    if MISTRAL_KEY:
        url     = "https://api.mistral.ai/v1/chat/completions"
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {MISTRAL_KEY}"}
    elif OPENROUTER_KEY:
        url     = "https://openrouter.ai/api/v1/chat/completions"
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {OPENROUTER_KEY}",
                   "HTTP-Referer": "https://app.open-lex.cloud"}
    else:
        raise RuntimeError("Kein API-Key konfiguriert (MISTRAL_KEY / OPENROUTER_KEY)")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
        "max_tokens": 200,
    }
    body = json.dumps(payload).encode()

    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
            text  = data["choices"][0]["message"]["content"].strip()
            usage = data.get("usage", {})
            return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        except Exception as e:
            wait = 5 * attempt
            print(f"  [WARN] LLM-Fehler (Versuch {attempt}/{retries}): {e} – warte {wait}s")
            time.sleep(wait)

    raise RuntimeError(f"LLM-Aufruf nach {retries} Versuchen fehlgeschlagen")


def clean_llm_output(text: str) -> str:
    """Entfernt Markdown-Wrapper, Anführungszeichen, 'Frage:'-Präfixe."""
    text = text.strip()
    # *"...*"  oder  *"..."*  oder  "..."  oder  '...'
    for wrapper in ('*"', '"*', '*', '"', "'"):
        text = text.strip(wrapper)
    text = text.strip()
    for prefix in ("frage:", "messy-frage:", "umformulierung:", "output:"):
        if text.lower().startswith(prefix):
            text = text[len(prefix):].strip()
    return text


def build_messy_entry(canonical: dict, messy_question: str, index: int) -> dict:
    """Gold-Logik 1:1 aus Canonical – nur question, id, level, source_canonical_id neu."""
    num = f"{index:03d}"
    return {
        "id":                  f"messy_{num}",
        "source_canonical_id": canonical["id"],
        "level":               "messy",
        "question":            messy_question,
        # Gold unverändert aus Canonical
        "retrieval_gold":      canonical.get("retrieval_gold", {}),
        "gold_ids":            canonical.get("gold_ids", []),
        "should_ids":          canonical.get("should_ids", []),
        "forbidden_ids":       canonical.get("forbidden_ids", []),
        "answer_gold":         canonical.get("answer_gold", {}),
        "expected_norms":      canonical.get("expected_norms", []),
        "expected_keywords":   canonical.get("expected_keywords", []),
        "min_sources":         canonical.get("min_sources", 2),
        # Metadaten
        "category":            canonical.get("category", "allgemein"),
        "difficulty":          "messy",
        "source_mw_chunk":     canonical.get("source_mw_chunk", ""),
        "generated_by":        MISTRAL_MODEL if MISTRAL_KEY else OR_MODEL,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Messy-Eval-Generator – umgangssprachliche Queries",
        epilog="Beispiel:  python scripts/generate_messy_eval.py --limit 5"
    )
    parser.add_argument("--canonical", default=str(CANONICAL_PATH))
    parser.add_argument("--output",    default=str(DEFAULT_OUTPUT))
    parser.add_argument("--limit",     type=int, default=None,
                        help="Nur N Einträge generieren (Testlauf)")
    parser.add_argument("--all",       action="store_true",
                        help="Alle Canonical-Einträge verarbeiten")
    parser.add_argument("--overwrite", action="store_true",
                        help="Ausgabedatei komplett neu erstellen")
    parser.add_argument("--resume",    action="store_true",
                        help="Bereits vorhandene Einträge überspringen")
    args = parser.parse_args()

    if not args.all and args.limit is None:
        parser.error("--all oder --limit N angeben")
    if args.overwrite and args.resume:
        parser.error("--overwrite und --resume schließen sich aus")

    # Canonical laden
    canonical_path = Path(args.canonical)
    if not canonical_path.exists():
        sys.exit(f"FEHLER: {canonical_path} nicht gefunden")
    with open(canonical_path) as f:
        canonical_entries = json.load(f)
    print(f"Canonical: {len(canonical_entries)} Einträge geladen aus {canonical_path.name}")

    # Output-Zustand ermitteln
    out_path = Path(args.output)
    existing: list[dict] = []
    existing_canonical_ids: set[str] = set()

    if out_path.exists():
        if args.overwrite:
            out_path.unlink()
            print(f"Ausgabedatei gelöscht (--overwrite): {out_path.name}")
        else:
            with open(out_path) as f:
                existing = json.load(f)
            existing_canonical_ids = {e.get("source_canonical_id", "") for e in existing}
            mode = "Resume" if args.resume else "Extend"
            print(f"{mode}: {len(existing_canonical_ids)} Einträge bereits vorhanden")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Zu verarbeitende Canonical-Einträge
    subset = canonical_entries if args.all else canonical_entries[: args.limit]
    # Idempotenz: bereits verarbeitete überspringen
    to_process = [c for c in subset if c["id"] not in existing_canonical_ids]
    if existing_canonical_ids and len(to_process) < len(subset):
        print(f"  → {len(subset) - len(to_process)} bereits vorhanden, {len(to_process)} zu generieren")

    results   = list(existing)
    total_in  = 0
    total_out = 0
    n_total   = len(to_process)

    for i, canonical in enumerate(to_process, 1):
        cid   = canonical["id"]
        thema = canonical.get("source_mw_chunk", cid)
        q     = canonical["question"]

        print(f"\n[{i}/{n_total}] {cid}")
        print(f"  Canonical: {q[:90]}{'...' if len(q) > 90 else ''}")

        prompt = PROMPT_TEMPLATE.format(canonical_question=q, thema=thema)

        try:
            raw, in_tok, out_tok = call_llm(prompt)
        except Exception as e:
            print(f"  [ERROR] Übersprungen: {e}")
            continue

        messy_q    = clean_llm_output(raw)
        total_in  += in_tok
        total_out += out_tok

        print(f"  Messy:     {messy_q[:90]}{'...' if len(messy_q) > 90 else ''}")
        print(f"  → tokens:  {in_tok} in / {out_tok} out")

        # Globale Indexposition = bisherige Gesamtlänge + 1
        global_index = len(results) + 1
        entry = build_messy_entry(canonical, messy_q, global_index)
        results.append(entry)

        # Sofort persistieren (crash-safe)
        with open(out_path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        if i < n_total:
            time.sleep(0.4)

    # Zusammenfassung
    new_count = len(results) - len(existing)
    print(f"\n=== FERTIG ===")
    print(f"Generiert: {new_count} neue Queries ({len(results)} gesamt)")
    print(f"Tokens:    {total_in} in / {total_out} out")
    if total_in:
        cost_eur = (total_in * 0.4 + total_out * 1.2) / 1_000_000 * 0.93
        print(f"Kosten dieser Session: ~{cost_eur:.4f} EUR")
    print(f"Output:    {out_path} ({len(results)} Einträge)")


if __name__ == "__main__":
    env = BASE_DIR / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    main()
