#!/usr/bin/env python3
"""
Intent-Coverage-Test: 100 Calls via Claude Haiku → Intent-Endpoint.

Generiert 100 diverse deutsche Rechtsfragen (mal knapp, mal sehr ausführlich,
Laie + Profi, alle 20 Top-Rechtsgebiete), schickt sie an den Intent-Endpoint
(localhost:7870 oder PUBLIC_URL), macht maximal 3 Turns pro Session und
sammelt die gerouteten Skills.

Usage (vom lokalen Rechner, Server läuft):
  ssh -L 7870:127.0.0.1:7870 root@91.98.146.160 -N &
  ANTHROPIC_API_KEY=sk-... python3 eval/intent_coverage_test.py

Oder direkt auf dem Server (ANTHROPIC_API_KEY muss dort gesetzt sein):
  cd /opt/openlex-mvp-v2 && ANTHROPIC_API_KEY=sk-... python3 intent/eval/intent_coverage_test.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from typing import Optional

import httpx

# ── Konfiguration ─────────────────────────────────────────────────────────────
BASE_URL = os.environ.get("INTENT_URL", "http://127.0.0.1:7870")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
HAIKU_MODEL = "claude-haiku-4-5"   # aktuellstes Haiku
MAX_TURNS = 3                       # max Turns pro Session
TIMEOUT = 45                        # Sekunden pro HTTP-Call
SLEEP_BETWEEN = 0.3                 # Pause zwischen Calls (Rate-Limit)

# ── Top-20-Rechtsgebiete + Szenario-Kategorien ────────────────────────────────
TOP_20 = [
    "arbeitsrecht", "mietrecht", "familienrecht", "erbrecht", "kaufrecht",
    "strafrecht", "verkehrsrecht", "verbraucherrecht", "versicherungsrecht",
    "sozialrecht", "verwaltungsrecht", "datenschutz", "medizinrecht",
    "gesellschaftsrecht", "insolvenzrecht", "it_recht", "urheberrecht",
    "steuerrecht", "baurecht", "migrationsrecht",
]

# Für jedes Rechtsgebiet: 5 Szenarien = 100 total
SZENARIEN: dict[str, list[str]] = {
    "arbeitsrecht": [
        "ich bin ohne Grund fristlos entlassen worden",
        "Mein Arbeitgeber hat mir nach 15 Jahren Betriebszugehörigkeit im Alter von 54 Jahren eine Kündigung ausgesprochen, obwohl ich im Betriebsrat sitze und gerade meine Frau schwer krank ist. Gilt da besonderer Schutz?",
        "abmahnung bekommen wegen verspätung",
        "Ich werde vom Chef gemobbt — ständige Kritik, Ausgrenzung, schlechte Aufgaben. Was kann ich tun?",
        "Lohn nicht gezahlt seit 3 Monaten. Arbeitgeber GmbH droht Insolvenz.",
    ],
    "mietrecht": [
        "vermieter will mich rauswerfen",
        "Meine Wohnung hat seit Oktober Schimmel an drei Wänden des Schlafzimmers, die Heizung im Bad fällt regelmäßig aus, und der Vermieter reagiert auf meine Schreiben nicht. Ich zahle 1.400 EUR Kaltmiete.",
        "mieterhöhung zu hoch?",
        "Vermieter betritt Wohnung ohne Ankündigung mehrfach im Monat.",
        "Kaution wird nach Auszug nicht zurückgezahlt, Vermieter nennt keine Gründe.",
    ],
    "familienrecht": [
        "scheidung einreichen",
        "Ich trenne mich nach 12 Jahren Ehe. Wir haben zwei Kinder (8 und 11). Ich habe zugunsten der Familie auf meine Karriere verzichtet und vergleichsweise wenig verdient. Was steht mir zu — Unterhalt, Zugewinnausgleich, Sorgerecht?",
        "ex zahlt keinen kindesunterhalt",
        "Wir streiten um das Umgangsrecht. Meine Ex lässt mich die Kinder nicht sehen.",
        "Patientenverfügung und Vorsorgevollmacht — wie mache ich das richtig?",
    ],
    "erbrecht": [
        "Vater gestorben, kein Testament. Was erbe ich?",
        "Meine Mutter hat meinen Bruder im Testament als Alleinerben eingesetzt. Ich gehe leer aus, obwohl ich jahrelang die Pflege übernommen habe. Habe ich trotzdem Ansprüche?",
        "erbschaft ausschlagen wegen schulden",
        "Pflichtteilsanspruch gegen Stiefschwester durchsetzen.",
        "Schenkung unter Vorbehalt: Vater hat Haus übertragen, jetzt fordert Pflegeheim die Rückabwicklung.",
    ],
    "kaufrecht": [
        "Auto gekauft, Motor kaputt",
        "Ich habe im Oktober 2023 bei einem Händler ein gebrauchtes Fahrzeug für 18.500 EUR erworben. Jetzt, 14 Monate später, zeigt sich ein erheblicher Ölverlust am Motor, den der Händler mit einem Mangel begründet, der schon bei Übergabe vorhanden war. Der Händler verweigert die Nachbesserung.",
        "online bestellt, falsche ware geliefert",
        "§ 434 BGB Sachmangel: Kaufsache weicht von vereinbarter Beschaffenheit ab. Minderung oder Rücktritt?",
        "Gewährleistungsausschluss im Kaufvertrag — wirksam?",
    ],
    "strafrecht": [
        "ich bin geschlagen worden",
        "Mein Nachbar hat mit einem Baseballschläger auf mein Auto eingeschlagen (Totalschaden ~8.000 EUR) und mich dabei mit dem Schläger leicht am Arm getroffen. Zeugen: meine Frau und ein Passant. Videoüberwachung auf dem Grundstück.",
        "anzeige wegen beleidigung erstatten",
        "Ich bin Beschuldigter in einem Betrugsverfahren (§ 263 StGB). Tatvorwurf: Vorenthalten von Informationen beim Unternehmensverkauf. Was muss ich wissen?",
        "mein sohn wurde beim ladendiebstahl erwischt, 16 jahre alt",
    ],
    "verkehrsrecht": [
        "unfall gehabt, gegner streitet ab",
        "Auffahrunfall auf der Autobahn: Gegner behauptet, ich sei unvermittelt abgebremst. Versicherung des Gegners verweigert Regulierung. Dashcam-Aufnahme vorhanden. Schaden ca. 4.200 EUR.",
        "führerschein entzug droht, 1,4 promille",
        "Fahrerflucht — ich habe nach dem Unfall zu spät gehalten. Was droht mir?",
        "Bußgeldbescheid Tempoverstoß 42 km/h zu schnell Innerorts — lohnt Einspruch?",
    ],
    "verbraucherrecht": [
        "abo nicht kündbar trotz kündigung",
        "Ich habe einen Fitnessstudio-Vertrag per Widerruf innerhalb von 14 Tagen widerrufen. Das Studio fordert trotzdem die volle Jahresgebühr und droht mit Inkasso.",
        "reise war mangelhaft, geld zurück",
        "Handwerker hat Küche falsch eingebaut, jetzt Wasserschaden. Unternehmen meldet sich nicht mehr.",
        "Callcenter hat mich in einen Vertrag gedrängt — war das wirksam?",
    ],
    "versicherungsrecht": [
        "versicherung zahlt nicht nach einbruch",
        "Meine Berufsunfähigkeitsversicherung (BU) verweigert die Leistung mit der Begründung, ich sei nicht zu 50% berufsunfähig, obwohl zwei Gutachter das bestätigen. Wie gehe ich vor?",
        "hausratversicherung sturmschaden abgelehnt",
        "Rechtsschutzversicherung verweigert Deckungszusage für Arbeitsrechtsstreit.",
        "Kaskoversicherung Totalschaden — Wiederbeschaffungswert zu niedrig angesetzt.",
    ],
    "sozialrecht": [
        "bürgergeld abgelehnt",
        "Ich bin 58, seit 2 Jahren arbeitslos, ALG I läuft bald aus. Meine Ersparnisse betragen ca. 15.000 EUR. Anspruch auf Bürgergeld? Anrechnung der Ersparnisse? Rentenansprüche?",
        "pflegegrad beantragt, abgelehnt",
        "GdB-Erhöhung durchsetzen — Schwerbehindertenausweis Grad 40, ich möchte 50.",
        "Erwerbsminderungsrente beantragt, abgelehnt trotz chronischer Erkrankung.",
    ],
    "verwaltungsrecht": [
        "baugenehmigung abgelehnt",
        "Die Gemeinde hat mir eine Baugenehmigung für einen Wintergarten mit Begründung 'Beeinträchtigung des Ortsbildes' versagt, obwohl der Nachbar ein ähnliches Bauwerk genehmigt bekam. Wie kann ich dagegen vorgehen?",
        "gewerbeuntersagung bekommen",
        "Führungszeugnis hat Eintrag — Einfluss auf Berufszulassung als Erzieher?",
        "Waffenschein-Verlängerung verweigert — Behörde zweifelt an Zuverlässigkeit.",
    ],
    "datenschutz": [
        "arbeitgeber liest meine mails",
        "Ein Ex-Partner hat private Fotos von mir ohne Einwilligung in einer WhatsApp-Gruppe mit 80 Personen verbreitet. Einige Bilder sind intim. Was kann ich rechtlich unternehmen?",
        "google maps zeigt mein haus, will ich nicht",
        "Auskunftsanspruch gegenüber Unternehmen — sie sagen, sie haben keine Daten von mir.",
        "Schufa-Eintrag löschen lassen — Forderung ist verjährt.",
    ],
    "medizinrecht": [
        "operation schiefgelaufen",
        "Nach einer Knie-TEP-Operation (Oktober 2023) leide ich unter anhaltenden Schmerzen und eingeschränkter Beweglichkeit. Der behandelnde Arzt räumt einen Positionierungsfehler der Prothese ein. Gutachten der Schlichtungsstelle ausstehend.",
        "behandlungsfehler zahnarzt",
        "Krankenhaus hat Aufklärung vergessen vor risiko-OP — welche Konsequenzen?",
        "Krankenkasse verweigert Kostenübernahme für spezielles Medikament (Off-Label-Use).",
    ],
    "gesellschaftsrecht": [
        "gesellschafter will mich rauswerfen",
        "Ich bin Gesellschafter einer GmbH mit 33% Anteil. Der Mehrheitsgesellschafter (67%) schüttet keine Gewinne aus, zahlt sich selbst aber ein überhöhtes Geschäftsführergehalt. Ich habe Angst vor Durchgriffshaftung und Minderheitenschutz — was sind meine Rechte?",
        "GmbH gründen, was brauche ich",
        "Wettbewerbsverbot nach Ausscheiden aus GmbH — wie weit reicht es?",
        "Gesellschafterstreit: Beschluss nichtig wegen Einberufungsfehler?",
    ],
    "insolvenzrecht": [
        "meine firma kann rechnungen nicht bezahlen",
        "Ich führe eine UG, die seit 6 Monaten zahlungsunfähig ist (Verbindlichkeiten 220.000 EUR, Vermögen 40.000 EUR). Ich habe den Insolvenzantrag bisher nicht gestellt. Was droht mir persönlich?",
        "privatinsolvenz beantragen, wie geht das",
        "Insolvenzanfechtung: Gläubiger will Zahlung zurückhaben, die ich kurz vor Insolvenz des Schuldners erhalten habe.",
        "Restschuldbefreiung — Voraussetzungen und wie lange dauert es?",
    ],
    "it_recht": [
        "impressumspflicht verletzt, abmahnung",
        "Ich betreibe einen Online-Shop und habe eine Abmahnung wegen fehlender Datenschutzerklärung, falschem Widerrufsrecht und unklaren AGB erhalten. Streitwert angeblich 15.000 EUR. Was tun?",
        "software hat sicherheitslücke, schaden entstanden",
        "KI-Tool generiert urheberrechtlich geschützte Inhalte — haftet mein Unternehmen?",
        "Domain-Grabbing: jemand hat meinen Firmennamen als Domain registriert.",
    ],
    "urheberrecht": [
        "foto geklaut auf instagram",
        "Ich bin freiberuflicher Fotograf. Eine große Zeitschrift hat 3 meiner Fotos ohne Genehmigung und ohne Namensnennung in einer Printausgabe (Auflage 800.000) verwendet. Wie berechne ich den Schaden?",
        "musik in youtube video, abmahnung von gema",
        "KI hat Text generiert, der meinem Roman ähnelt — Urheberrechtsverstoß?",
        "Open-Source-Lizenz verletzt: Unternehmen nutzt GPL-Code in proprietärem Produkt.",
    ],
    "steuerrecht": [
        "finanzamt fordert steuernachzahlung",
        "Ich habe 2021 und 2022 Einkünfte aus einem Nebenjob (Freelance-IT, ca. 45.000 EUR/Jahr) nicht in der Steuererklärung angegeben. Das Finanzamt hat jetzt eine Betriebsprüfung angekündigt. Steuerhinterziehung — was kann ich tun?",
        "einspruch gegen steuerbescheid",
        "Umsatzsteuer-Nachschau — was darf der Prüfer, was nicht?",
        "Schenkungsteuer beim Hausübergang an Kind — Freibeträge ausschöpfen.",
    ],
    "baurecht": [
        "nachbar baut zu nah an grenze",
        "Mein Nachbar hat ohne Baugenehmigung einen 6m hohen Carport direkt an der Grenze zu meinem Grundstück errichtet. Die Baubehörde tut nichts. Kann ich selbst gegen den Bau vorgehen?",
        "baugenehmigung für dachausbau",
        "Bauunternehmer hat Bau abgebrochen, Anzahlung 30.000 EUR weg — was tun?",
        "Wohnungseigentümergemeinschaft verweigert Zustimmung zu meinem Balkonausbau.",
    ],
    "migrationsrecht": [
        "aufenthaltserlaubnis abgelaufen",
        "Ich bin nigerianischer Staatsbürger, seit 8 Jahren in Deutschland, habe eine unbefristete Niederlassungserlaubnis, aber jetzt droht mir die Ausweisung wegen einer Verurteilung wegen Körperverletzung (Bewährungsstrafe 8 Monate). Was sind meine Chancen?",
        "familiennachzug beantragen",
        "Asylantrag abgelehnt — was sind meine Möglichkeiten dagegen?",
        "Einbürgerung beantragen — doppelte Staatsbürgerschaft möglich?",
    ],
}


def haiku_generate_variation(base_prompt: str, style: str) -> str:
    """Nutzt Claude Haiku um eine Variation des Prompts zu erzeugen."""
    if not ANTHROPIC_KEY:
        return base_prompt
    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={
                "model": HAIKU_MODEL,
                "max_tokens": 200,
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Schreibe folgende Rechtsfrage in einem {style} Stil um, "
                        f"auf Deutsch, als wäre es eine echte Mandanten-Nachricht. "
                        f"NUR die umgeschriebene Frage, kein Kommentar:\n\n{base_prompt}"
                    )
                }]
            },
            timeout=15
        )
        text = resp.json().get("content", [{}])[0].get("text", "").strip()
        return text if text else base_prompt
    except Exception:
        return base_prompt


def create_session() -> Optional[str]:
    try:
        r = httpx.post(f"{BASE_URL}/intent/session", json={}, timeout=TIMEOUT)
        return r.json().get("session_id")
    except Exception as e:
        print(f"    session error: {e}")
        return None


def send_message(session_id: str, text: str) -> dict:
    try:
        r = httpx.post(
            f"{BASE_URL}/intent/message",
            json={"session_id": session_id, "text": text},
            timeout=TIMEOUT
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def run_session(prompt: str, followup: str = "das ist alles was ich dazu sagen kann") -> dict:
    """Führt eine Session mit max MAX_TURNS durch. Gibt letzten Response zurück."""
    sid = create_session()
    if not sid:
        return {}
    resp = {}
    for turn in range(MAX_TURNS):
        msg = prompt if turn == 0 else followup
        resp = send_message(sid, msg)
        if resp.get("modus") == "handoff":
            break
        if resp.get("error"):
            break
    return resp


def main():
    print(f"Intent Coverage Test — {BASE_URL}")
    print(f"Anthropic Haiku: {'verfügbar' if ANTHROPIC_KEY else 'nicht verfügbar (statische Prompts)'}")
    print(f"Szenarien: {sum(len(v) for v in SZENARIEN.values())} total")
    print("=" * 60)

    skill_counter: Counter = Counter()
    skill_conf_sum: defaultdict = defaultdict(float)
    results = []
    errors = 0
    handoffs = 0

    STYLE_CYCLE = [
        "sehr kurzen, knappen", "sehr detaillierten, ausführlichen",
        "umgangssprachlichen Laien-", "juristisch präzisen Profi-",
        "emotionalen, verzweifelten",
    ]

    idx = 0
    for rechtsgebiet, prompts in SZENARIEN.items():
        for pi, base_prompt in enumerate(prompts):
            idx += 1
            style = STYLE_CYCLE[pi % len(STYLE_CYCLE)]

            # Variation mit Haiku (wenn verfügbar)
            if ANTHROPIC_KEY and pi > 0:
                prompt = haiku_generate_variation(base_prompt, style)
            else:
                prompt = base_prompt

            print(f"[{idx:3d}/100] {rechtsgebiet[:20]:20s}  {prompt[:55]!r}...", end=" ", flush=True)

            resp = run_session(prompt)
            time.sleep(SLEEP_BETWEEN)

            if resp.get("error"):
                print(f"ERR: {resp['error'][:40]}")
                errors += 1
                continue

            modus = resp.get("modus", "?")
            if modus == "handoff":
                handoffs += 1
                rgs = (resp.get("handoff") or {}).get("vermutete_rechtsgebiete") or []
                routed = [r["skill"] for r in rgs[:3]]
                for r in rgs:
                    skill_counter[r["skill"]] += 1
                    skill_conf_sum[r["skill"]] += r.get("confidence", 0)
                hit = rechtsgebiet in routed
                results.append({
                    "expected": rechtsgebiet, "routed": routed, "hit": hit,
                    "prompt": prompt[:80]
                })
                marker = "✓" if hit else "✗"
                print(f"{modus} {marker} → {', '.join(routed[:3])}")
            else:
                results.append({"expected": rechtsgebiet, "routed": [], "hit": False,
                                 "prompt": prompt[:80]})
                print(f"{modus} (kein Handoff)")

    # ── Auswertung ──────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"ERGEBNIS: {handoffs}/100 Handoffs, {errors} Fehler")

    handoff_results = [r for r in results if r["routed"]]
    if handoff_results:
        hits = sum(1 for r in handoff_results if r["hit"])
        print(f"Routing-Treffer (expected in top-3): {hits}/{len(handoff_results)} "
              f"({100*hits/len(handoff_results):.0f}%)")

    print(f"\n{'─'*60}")
    print("TOP-20 RECHTSGEBIETE nach Häufigkeit (gewichtet nach confidence):")
    print(f"{'#':>3}  {'Skill':<35} {'#Nennungen':>10}  {'Ø Confidence':>12}")
    print(f"{'─'*3}  {'─'*35} {'─'*10}  {'─'*12}")
    for rank, (skill, cnt) in enumerate(skill_counter.most_common(20), 1):
        avg_conf = skill_conf_sum[skill] / cnt if cnt else 0
        marker = "★" if skill in TOP_20 else " "
        print(f"{rank:>3}  {marker}{skill:<34} {cnt:>10}  {avg_conf:>12.3f}")

    # Fehlende Top-20 melden
    print(f"\n{'─'*60}")
    seen_top20 = {s for s in skill_counter if s in TOP_20}
    missing_top20 = [s for s in TOP_20 if s not in seen_top20]
    if missing_top20:
        print(f"Top-20 nicht im Output: {', '.join(missing_top20)}")
    else:
        print("Alle 20 Ziel-Rechtsgebiete wurden geroutet. ✓")

    # Worst-Case: Prompts ohne korrektes Routing
    misses = [r for r in handoff_results if not r["hit"]]
    if misses:
        print(f"\nFalsch geroutete Fälle ({len(misses)}):")
        for m in misses[:10]:
            print(f"  expected={m['expected']:20s}  got={m['routed']}")

    # JSON-Report
    report_path = os.path.join(os.path.dirname(__file__), "coverage_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "summary": {"total": 100, "handoffs": handoffs, "errors": errors,
                        "hit_rate": hits/len(handoff_results) if handoff_results else 0},
            "top20": [(s, c) for s, c in skill_counter.most_common(20)],
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nDetaillierter Report: {report_path}")


if __name__ == "__main__":
    main()
