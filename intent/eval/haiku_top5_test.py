#!/usr/bin/env python3
"""
50-Call-Test: Haiku generiert sehr ausführliche Prompts für Top-5-Rechtsgebiete.
Läuft direkt auf dem Server (ANTHROPIC_API_KEY aus /etc/environment).

Run:  python3 /opt/openlex-mvp-v2/intent/eval/haiku_top5_test.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict

import httpx

# Key aus /etc/environment laden falls nicht in os.environ
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        for line in open("/etc/environment").readlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                os.environ["ANTHROPIC_API_KEY"] = line.strip().split("=", 1)[1]
                break
    except Exception:
        pass

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HAIKU_MODEL   = "claude-haiku-4-5"
BASE_URL      = "http://127.0.0.1:7870"
MAX_TURNS     = 5      # mehr Turns damit StR-Gate + Weichen durchlaufen
SLEEP         = 0.4

if not ANTHROPIC_KEY:
    sys.exit("ANTHROPIC_API_KEY nicht gefunden.")

TOP5 = [
    "strafrecht",
    "verbraucherrecht",
    "arbeitsrecht",
    "insolvenzrecht",
    "datenschutz",
]

# ── Haiku-Prompt-Generierung ─────────────────────────────────────────────────
def haiku(system: str, user: str, max_tokens: int = 600) -> str:
    r = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": ANTHROPIC_KEY,
                 "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": HAIKU_MODEL, "max_tokens": max_tokens,
              "system": system,
              "messages": [{"role": "user", "content": user}]},
        timeout=30,
    )
    return r.json()["content"][0]["text"].strip()


def generate_prompts(rechtsgebiet: str, n: int = 10) -> list[str]:
    """Lässt Haiku n sehr ausführliche, voneinander verschiedene deutsche
    Rechtsfragen für das gegebene Rechtsgebiet generieren."""
    system = (
        "Du generierst realistische, sehr detaillierte deutsche Mandanten-Schilderungen "
        "für ein Rechtsinformationssystem. Jede Schilderung soll:\n"
        "- Mindestens 6–8 Sätze lang sein (gerne länger)\n"
        "- Konkrete Fakten enthalten: Daten, Beträge, Namen, Orte\n"
        "- Aus der Ich-Perspektive eines Laien geschrieben sein\n"
        "- Keine Rechtsbegriffe oder Paragraphen nennen\n"
        "- Sehr unterschiedliche Fallkonstellationen abdecken: "
        "verschiedene Berufsgruppen, Altersgruppen, Regionen, Streitwerte, Eskalationsstufen\n"
        "- Emotionalen Kontext enthalten (Stress, Unsicherheit, Dringlichkeit)\n"
        "- KEINE typischen Standard-Fälle: wähle ungewöhnliche, spezifische Situationen\n"
        "Gib NUR die Schilderungen aus, nummeriert 1. bis " + str(n) + "., keine Erklärungen."
    )
    user = (
        f"Generiere {n} sehr ausführliche, realistische Mandanten-Schilderungen "
        f"zum Rechtsgebiet '{rechtsgebiet}'. Wichtig: Jede Schilderung muss eine "
        f"völlig andere Situation beschreiben — unterschiedliche Personen, Berufe, "
        f"Orte, Beträge, Eskalationsstufen. Mindestens 7 Sätze pro Schilderung. "
        f"Keine Standardfälle wie 'Auto gekauft, Motor kaputt' oder "
        f"'Arbeitgeber hat mich entlassen' — kreativ und spezifisch bleiben."
    )
    raw = haiku(system, user, max_tokens=n * 250)
    # Parsing: nummerierte Liste extrahieren
    prompts = []
    current = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        import re
        if re.match(r"^\d{1,2}[\.\)]\s", line) and current:
            prompts.append(" ".join(current).strip())
            current = [re.sub(r"^\d{1,2}[\.\)]\s+", "", line)]
        elif re.match(r"^\d{1,2}[\.\)]\s", line):
            current = [re.sub(r"^\d{1,2}[\.\)]\s+", "", line)]
        else:
            current.append(line)
    if current:
        prompts.append(" ".join(current).strip())
    # Sicherstellen dass wir genug haben
    return [p for p in prompts if len(p) > 60][:n]


# ── Intent-Calls ─────────────────────────────────────────────────────────────
def smart_followup(resp: dict, turn: int) -> str:
    """Antwortet auf die letzte Frage des Systems kontextbewusst."""
    frage = (resp.get("frage") or "").lower()
    # Weichenstellungen erkennen (1/2/3)
    if "[1]" in frage and "[2]" in frage:
        if "opfer" in frage or "geschädigt" in frage:
            return "2"   # Opfer/Geschädigter
        if "beschuldig" in frage or "angeklag" in frage:
            return "2"   # Auch Opfer
        return "1"       # Default: erste Option
    # Tatbestand-Subjektiv: klar Vorsatz
    if "vorsätzlich" in frage or "absicht" in frage or "wissen und wollen" in frage:
        return "Nein, es spricht alles für bewusstes Vorgehen mit voller Absicht."
    # ÖR: Bescheid
    if "bescheid" in frage or "maßnahme" in frage or "behörde" in frage:
        return "Ja, ich habe einen schriftlichen Ablehnungsbescheid erhalten."
    # ÖR: Grundrechte
    if "grundrecht" in frage or "recht" in frage or "interesse" in frage:
        return "Meine Berufsausübung und meine persönliche Freiheit sind stark eingeschränkt."
    # Allgemein: nach 2 Turns Erschöpfung signalisieren
    if turn >= 2:
        return "Das ist alles was ich dazu sagen kann, ich brauche eine rechtliche Einschätzung."
    return "Ich bin nicht sicher, können Sie mir sagen was wichtig ist?"


def run_session(prompt: str) -> dict:
    """Session mit bis zu MAX_TURNS, smart followup."""
    try:
        r = httpx.post(f"{BASE_URL}/intent/session", json={}, timeout=30)
        sid = r.json()["session_id"]
    except Exception as e:
        return {"error": str(e)}

    resp = {}
    for turn in range(MAX_TURNS):
        msg = prompt if turn == 0 else smart_followup(resp, turn)
        try:
            r = httpx.post(f"{BASE_URL}/intent/message",
                           json={"session_id": sid, "text": msg}, timeout=45)
            resp = r.json()
        except Exception as e:
            return {"error": str(e)}
        if resp.get("modus") == "handoff":
            break
    return resp


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"Haiku Top-5 Test — {BASE_URL}")
    print(f"Modell: {HAIKU_MODEL} | Max Turns: {MAX_TURNS}")
    print("=" * 65)

    skill_counter: Counter = Counter()
    skill_conf: defaultdict = defaultdict(list)
    tiefe_hit: Counter = Counter()
    results = []
    errors = 0
    handoffs = 0
    idx = 0

    for rechtsgebiet in TOP5:
        print(f"\n── {rechtsgebiet.upper()} ({'Haiku generiert Prompts...'})")
        try:
            prompts = generate_prompts(rechtsgebiet, 10)
        except Exception as e:
            print(f"   Haiku-Fehler: {e}")
            prompts = [f"Ich habe ein Problem im Bereich {rechtsgebiet}. "
                       f"Bitte helfen Sie mir."] * 10
        print(f"   {len(prompts)} Prompts generiert.")

        for pi, prompt in enumerate(prompts[:10]):
            idx += 1
            time.sleep(SLEEP)
            preview = prompt[:70].replace("\n", " ")
            print(f"  [{idx:2d}/50] {preview!r}...", end=" ", flush=True)

            resp = run_session(prompt)

            if resp.get("error"):
                print(f"ERR: {resp['error'][:40]}")
                errors += 1
                results.append({"expected": rechtsgebiet, "routed": [],
                                 "hit": False, "prompt": prompt[:100]})
                continue

            modus = resp.get("modus", "?")
            if modus == "handoff":
                handoffs += 1
                h = resp.get("handoff") or {}
                rgs = h.get("vermutete_rechtsgebiete") or []
                routed = [r["skill"] for r in rgs[:3]]
                for rg in rgs:
                    skill_counter[rg["skill"]] += 1
                    skill_conf[rg["skill"]].append(rg.get("confidence", 0))
                # Tiefe-Check
                tiefe = h.get("sachverhalts_tiefe") or {}
                rs = h.get("rechtssystem")
                if rs == "StR" and tiefe.get("tatbestand_subj"):
                    tiefe_hit["str_subj"] += 1
                if rs == "ÖR" and (tiefe.get("bescheid_art") or
                                   tiefe.get("betroffene_grundrechte_interessen")):
                    tiefe_hit["oer_pflicht"] += 1
                hit = rechtsgebiet in routed
                results.append({"expected": rechtsgebiet, "routed": routed,
                                 "hit": hit, "prompt": prompt[:100],
                                 "tiefe": tiefe, "rechtssystem": rs})
                marker = "✓" if hit else "✗"
                tiefe_str = f" [{rs}:{list(tiefe.keys())}]" if tiefe else ""
                print(f"handoff {marker} → {', '.join(routed[:3])}{tiefe_str}")
            else:
                results.append({"expected": rechtsgebiet, "routed": [],
                                 "hit": False, "prompt": prompt[:100]})
                print(f"{modus} (kein Handoff)")

    # ── Auswertung ──────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print(f"ERGEBNIS: {handoffs}/50 Handoffs, {errors} Fehler")
    handoff_results = [r for r in results if r.get("routed")]
    if handoff_results:
        hits = sum(1 for r in handoff_results if r["hit"])
        print(f"Routing-Treffer: {hits}/{len(handoff_results)} "
              f"({100*hits/len(handoff_results):.0f}%)")

    print(f"\n{'─'*65}")
    print("ROUTING-TREFFERQUOTE JE RECHTSGEBIET:")
    for rg in TOP5:
        rg_results = [r for r in results if r["expected"] == rg]
        ho = [r for r in rg_results if r.get("routed")]
        hits = sum(1 for r in ho if r["hit"])
        print(f"  {rg:<20} {hits}/{len(ho)} Handoff-Treffer  "
              f"({len(rg_results)-len(ho)} kein Handoff)")

    print(f"\n{'─'*65}")
    print("SACHVERHALTSTIEFE-EXTRAKTION:")
    str_cases = [r for r in results if r.get("rechtssystem") == "StR"]
    oer_cases = [r for r in results if r.get("rechtssystem") == "ÖR"]
    if str_cases:
        subj_ok = sum(1 for r in str_cases if r.get("tiefe", {}).get("tatbestand_subj"))
        print(f"  StR tatbestand_subj extrahiert: {subj_ok}/{len(str_cases)}")
        obj_ok = sum(1 for r in str_cases if r.get("tiefe", {}).get("tatbestand_obj"))
        print(f"  StR tatbestand_obj  extrahiert: {obj_ok}/{len(str_cases)}")
        rechtf_ok = sum(1 for r in str_cases if r.get("tiefe", {}).get("rechtfertigungsgrund"))
        print(f"  StR rechtfertigungs extrahiert: {rechtf_ok}/{len(str_cases)}")
    if oer_cases:
        bescheid_ok = sum(1 for r in oer_cases if r.get("tiefe", {}).get("bescheid_art"))
        print(f"  ÖR  bescheid_art    extrahiert: {bescheid_ok}/{len(oer_cases)}")
        gr_ok = sum(1 for r in oer_cases if r.get("tiefe", {}).get("betroffene_grundrechte_interessen"))
        print(f"  ÖR  grundrechte     extrahiert: {gr_ok}/{len(oer_cases)}")

    print(f"\n{'─'*65}")
    print("SKILL-VERTEILUNG (alle gerouteten Skills):")
    for sk, cnt in skill_counter.most_common(15):
        avg_c = sum(skill_conf[sk]) / len(skill_conf[sk])
        print(f"  {sk:<35} {cnt:>4}×  Ø {avg_c:.3f}")

    # Falsch-Routings
    misses = [r for r in handoff_results if not r["hit"]]
    if misses:
        print(f"\nFALSCH GEROUTET ({len(misses)}):")
        for m in misses:
            print(f"  {m['expected']:<20} → {m['routed']}")
            print(f"    {m['prompt'][:80]}")

    report = f"/opt/openlex-mvp-v2/intent/eval/haiku_top5_report.json"
    with open(report, "w", encoding="utf-8") as f:
        json.dump({"handoffs": handoffs, "errors": errors,
                   "results": results,
                   "skill_counts": dict(skill_counter.most_common())},
                  f, ensure_ascii=False, indent=2)
    print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
