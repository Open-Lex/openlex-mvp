# Eval-Sets

Dreistufige Eval-Struktur:

- `canonical_auto.json` – automatisch aus Methodenwissen generiert (klar formulierte Fragen)
- `canonical_curated.json` – manuell kuratiert/überprüft (TODO)
- `messy.json` – umgangssprachlich, unscharf (TODO, Community-Kuratierung)
- `adversarial.json` – tricky, konkurrierende Normen (TODO, manuell kuratiert)

## Schema

Siehe `eval_v3.py` im Repo-Root (Docstring am Dateianfang und im Kommentar zum Fragen-Schema).

## Nutzung

```bash
# Retrieval-only (schnell, ohne LLM-Kosten)
python eval_v3.py --eval-set eval_sets/canonical_auto.json --retrieval-only

# Volle Eval mit Answer-Level
python eval_v3.py --eval-set eval_sets/canonical_auto.json
```
