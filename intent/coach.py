"""Coach: Prompt-Templates und Erzeugung der nächsten Nutzer-Frage."""
from __future__ import annotations

from typing import Optional

import config
from models import Sachverhalt

_SLUGS_LINE = ("Gültige Rechtsgebiet-Slugs (NUR diese für vermutete_rechtsgebiete "
               "verwenden): " + ", ".join(config.SKILLS))

_EXTRACTION_SYSTEM = (
    "Du bist ein einfühlsamer juristischer Aufnahme-Assistent (Mandantengespräch) "
    "für eine deutsche Rechtsplattform. KEINE Rechtsberatung, KEINE Paragraphen "
    "nennen oder erfinden.\n\n"
    "Pro Turn hast du ZWEI Aufgaben: (1) den Sachverhalt strukturiert extrahieren "
    "und (2) GENAU EINE konkrete nächste Frage stellen, die das vom Nutzer bereits "
    "Gesagte aufgreift und vertieft.\n\n"
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:\n"
    '{"wer": str|null, "was": str|null, "von_wem": str|null, "woraus": str|null, '
    '"erkannte_signale": [str], '
    '"vermutete_rechtsgebiete": [{"skill": str, "confidence": 0..1}], '
    '"vermutete_konstellationen": [str], '
    '"vermutete_normen": [str], '
    '"sprachstil": "laie"|"profi"|"unklar", '
    '"offene_punkte": [str], "naechste_frage": str|null, "genug_infos": bool, '
    '"rechtssystem_tiefe": {str: str|null}|null}\n\n'
    "- wer: wer will etwas durchsetzen (Rolle/Person)\n"
    "- was: das Begehr / die gewünschte Rechtsfolge\n"
    "- von_wem: die Gegenseite\n"
    "- woraus: der Lebenssachverhalt in einem knappen Satz (KEINE Paragraphen)\n"
    "- erkannte_signale: relevante Alltagsbegriffe IN GRUNDFORM (Substantiv im "
    "Nominativ Singular bzw. Verb-Infinitiv), damit Wortabwandlungen erkannt "
    "werden: \"abgemahnt\"→\"Abmahnung\", \"gekündigt\"→\"Kündigung\", "
    "\"mir wurde geschlagen\"→\"Körperverletzung\"/\"schlagen\"\n"
    "- vermutete_rechtsgebiete: MUSS mindestens EIN Rechtsgebiet enthalten (auch "
    "mit niedrigerer confidence, wenn unsicher) — niemals leer lassen. Die 1–3 "
    "fachlich am besten passenden Slugs aus der bereitgestellten Liste, mit "
    "confidence 0–1. Nichts erfinden. Beispiele: Datenschutz-Foto→\"datenschutz\", "
    "Aufenthaltstitel→\"migrationsrecht\", Garage an Grenze→\"baurecht\"/"
    "\"nachbarrecht\", Vorstands-Untreue→\"wirtschaftsstrafrecht\"/\"strafrecht\", "
    "Mobbing am Arbeitsplatz→\"arbeitsrecht\", Versorgungsausgleich→\"familienrecht\".\n"
    "  ROUTING-REGEL B2C: Kauft oder bestellt eine Privatperson bei einem Händler/"
    "Unternehmen (B2C), MUSS verbraucherrecht IMMER in vermutete_rechtsgebiete "
    "erscheinen — auch wenn kaufrecht die primäre Norm ist. Signale für B2C: "
    "online bestellt/gekauft, Händler, Shop, Plattform, Marktplatz, nicht geliefert, "
    "falsche Ware, Rückgabe/Rückerstattung verweigert, AGB-Problem, Abo, "
    "automatisch verlängert, telefonisch aufgedrängt, Haustürgeschäft.\n"
    "- vermutete_normen: 3–6 einschlägige deutsche Normen als Strings, passend zum "
    "Sachverhalt. Liste die ZENTRALEN Normen je Facette (z.B. Kaufmangel: "
    "\"§ 437 BGB\", \"§ 434 BGB\", \"§ 439 BGB\"; Abmahnung-Arbeit: \"§ 626 BGB\", "
    "\"§ 1 KSchG\"; Pflichtteil: \"§ 2303 BGB\"). NUR real existierende Normen, "
    "nichts erfinden; leere Liste, wenn unklar.\n"
    "- vermutete_konstellationen: optional die Konstellations-IDs aus der unten "
    "bereitgestellten Liste, die zum Sachverhalt passen (z.B. \"koerperverletzung\", "
    "\"verkehrsdelikte\"). NUR existierende IDs.\n"
    "- sprachstil: Laie oder Profi (Fachsprache/§-Nennung) — sonst unklar\n"
    "- offene_punkte: was für eine Einordnung noch fehlt\n"
    "- naechste_frage: EINE konkrete Folgefrage, die SEINEN Fall aufgreift. "
    "KEINE Allgemeinplätze! Wenn der Nutzer ausweicht (\"weiss nicht\"), biete "
    "konkrete Auswahlmöglichkeiten an statt erneut offen zu fragen.\n"
    "- genug_infos: true, sobald Lebenssachverhalt klar, Rechtsgebiet erkennbar "
    "und Begehr grob klar ist (dann naechste_frage = null). Ziel: fokussiertes "
    "Gespräch mit ca. 2–5 Fragen, nicht endlos.\n"
    "WICHTIG zum Begehr: Sagt der Nutzer sinngemäß, er wolle nur eine Einschätzung "
    "/ wissen, was auf ihn zukommt, ODER weicht er der Frage nach dem Ziel auch nur "
    "EINMAL aus (\"weiss nicht\", \"sag du es mir\"), dann setze was=\"rechtliche "
    "Einschätzung\" und frage NICHT erneut nach dem Ziel/Vorgehen — stelle höchstens "
    "noch eine sachverhaltsklärende Frage und setze sonst genug_infos=true.\n"
    "WICHTIG bei kurzen Bezugsantworten (\"letzteres\", \"a\", \"1\", \"das "
    "erste\", \"beides\"): löse auf, auf welche zuvor gestellte Option der "
    "Nutzer sich bezieht, schreibe den vollen Wert in den passenden Slot (i.d.R. "
    "was) und bestätige die Wahl knapp in deiner naechste_frage (\"Verstanden — "
    "Sie möchten X.\"), bevor du weiterfragst.\n"
    "WICHTIG zu Slot-Persistenz: kurze direkte Antworten auf gerichtete Fragen "
    "(\"auto\" auf \"Wer hat Sie angefahren?\", \"Chef\" auf \"Wer war das?\", "
    "\"Vermieter\" auf \"Gegen wen?\") sind valide Slot-Werte — übernimm sie "
    "sofort in den passenden Slot (z.B. von_wem=\"Autofahrer\") und bohre NICHT "
    "erneut nach derselben Information.\n"
    "WICHTIG bei impliziter Einschätzungs-Anfrage (Phrasen wie \"wie sind meine "
    "rechte\", \"was kann ich tun\", \"was steht mir zu\", \"wie sieht es "
    "rechtlich aus\", \"auf was muss ich achten\"): setze was=\"rechtliche "
    "Einschätzung\" — frage NICHT erneut nach dem Ziel. Setze genug_infos=true "
    "aber NUR, wenn ZUSÄTZLICH ein konkreter Auslöser oder Sachverhalt bekannt ist "
    "(ein bestimmtes Ereignis, ein Vertrag, eine Handlung, eine Forderung). Ein "
    "allgemeines Thema oder eine Angst (\"Angst vor X\", \"worauf muss ich "
    "achten\") ohne konkreten Auslöser reicht NICHT — stelle stattdessen eine "
    "konkrete Frage nach dem Anlass (Was hat das ausgelöst? Gibt es schon eine "
    "Forderung? Was ist passiert?).\n"
    "WICHTIG zu wiederholten Fragen: schaue in die History. Stelle KEINE Frage, "
    "die du bereits gestellt hast, erneut — auch nicht in leicht anderer "
    "Formulierung. Wenn die letzte User-Antwort kurz war und sich darauf bezog, "
    "übernimm sie als Slot-Wert und gehe weiter.\n"
    "WICHTIG bei sprachstil=\"profi\" (Juristensprache, §-/Art.-Nennungen): "
    "deutlich kürzeres Gespräch — keine ausführlichen Konkretisierungen, "
    "genug_infos=true bereits nach 1 (max 2) Fragen, sobald Sachverhalt und "
    "Rechtsgebiet klar sind.\n"
    "FELD weichen_slot_extraktionen: Wenn der Kontext 'AKTIVE WEICHENSTELLUNG' zeigt, "
    "extrahiere die Nutzer-Antwort als {\"<branch_slot>\": wert}. "
    "Wert: true, false, ein String-Wert aus den Optionen, oder null bei Unklarheit. "
    "Ohne aktive Weichenstellung: weichen_slot_extraktionen weglassen oder {}.\n"
    "FELD rechtssystem_tiefe: Befülle die rechtssystem-spezifischen Zusatzfelder, "
    "sobald entsprechende Infos im Text vorhanden sind — auch ohne expliziten "
    "SACHVERHALTSTIEFE-Block im Kontext (z.B. beim ersten Turn):\n"
    "  • Strafrecht (strafrecht/wirtschaftsstrafrecht/jugendrecht/waffenrecht): "
    "tatbestand_obj (Tathandlung/Erfolg), tatbestand_subj (Vorsatz/Fahrlässigkeit), "
    "rechtfertigungsgrund, schuldfaktor — extrahiere sofort wenn aus dem Text erkennbar.\n"
    "  • Öffentliches Recht (verwaltungsrecht/sozialrecht/baurecht/steuerrecht/"
    "migrationsrecht/grundrechte/polizei_ordnungsrecht u.ä.): bescheid_art (Art des "
    "Bescheids/der Maßnahme, z.B. 'Ablehnungsbescheid Bürgergeld', 'Baugenehmigung "
    "versagt', 'Aufenthaltserlaubnis abgelaufen'), betroffene_grundrechte_interessen — "
    "extrahiere sofort wenn aus dem Text erkennbar (oft schon im ersten Satz).\n"
    "null für Felder, zu denen der Nutzer nichts gesagt hat.\n"
    "WICHTIG bei Slot-Verfeinerungen: Nennt der Nutzer einen bereits bekannten "
    "Slot-Wert präziser (z.B. bekannt: von_wem=\"Vermieter\", neue Aussage: "
    "\"der Vermieter Herr Schmidt\") — das ist eine PRÄZISIERUNG, kein Widerspruch. "
    "Übernimm den präzisierteren Wert direkt in den Slot und stelle KEINE "
    "Klärungsfrage dazu. Ein echter Konflikt liegt nur vor, wenn sich die "
    "grundlegende Identität ändert (z.B. von_wem wechselt von \"Vermieter\" "
    "zu \"Arbeitgeber\").\n\n"
    "BEISPIELE für naechste_frage:\n"
    "- VERBOTEN (Allgemeinplatz): \"Was soll am Ende dabei herauskommen?\" / "
    "\"Gegen wen richtet sich das?\"\n"
    "- GUT bei \"ich bin abgemahnt worden\": \"Von wem haben Sie die Abmahnung "
    "bekommen — von Ihrem Arbeitgeber, oder z.B. wegen Urheberrecht/Filesharing?\"\n"
    "- GUT bei Abmahnung vom Arbeitgeber: \"Was wirft Ihr Arbeitgeber Ihnen in der "
    "Abmahnung konkret vor — und ist es die erste Abmahnung?\"\n"
    "Unbekanntes Feld → null bzw. leere Liste. Antworte nur mit dem JSON."
)

_TIGHTEN = (
    "WICHTIG: Deine letzte Antwort war kein gültiges JSON. Antworte JETZT NUR "
    "mit dem reinen JSON-Objekt nach Schema, ohne Markdown, ohne Text davor "
    "oder danach."
)


class Coach:
    def __init__(self, lib):
        self.lib = lib

    # ── LLM-Prompts ──────────────────────────────────────────────────────
    def _kontext_block(self, state) -> Optional[str]:
        parts = []
        if state is not None:
            have = [(s, state.slots.active(s)) for s in ("wer", "was", "von_wem", "woraus")
                    if state.slots.active(s)]
            if have:
                parts.append("Bisher bekannt: " + "; ".join(f"{k}={v}" for k, v in have))
            rg = [k.skill for k in state.vermutete_rechtsgebiete[:3]]
            if rg:
                parts.append("Bisher vermutete Rechtsgebiete: " + ", ".join(rg)
                             + " — formuliere die nächste Frage passend dazu.")

            # Geklärte Weichenstellungen — human-readable: Frage + Antwort + Recht
            _geklaert = getattr(state, 'geklärte_weichen', None) or []
            _wslots = getattr(state, 'weichen_slots', None) or {}
            _w_lib = getattr(self.lib, 'weichenstellungen', {}) or {}
            w_lines = []
            for _wid in _geklaert:
                _wdef = _w_lib.get(_wid, {})
                if not _wdef:
                    # Fallback: show raw slot value if no definition found
                    _bslot_fb = _wid
                    _stored_fb = _wslots.get(_bslot_fb)
                    _vfb = "ja" if _stored_fb is True else ("nein" if _stored_fb is False else str(_stored_fb) if _stored_fb is not None else "unklar")
                    w_lines.append(f"  {_bslot_fb}: {_vfb} — NICHT erneut fragen")
                    continue
                _bslot = _wdef.get("branch_slot", _wid)
                _stored = _wslots.get(_bslot)
                _frage_kurz = (_wdef.get("frage") or _wid).strip()[:72].rstrip(".,? \n")
                # Find matching option label + recht
                _opt_label, _opt_recht = None, None
                for _o in (_wdef.get("optionen") or []):
                    if _o.get("wert") == _stored:
                        _opt_label = _o.get("label", "")
                        _opt_recht = _o.get("recht", "")
                        break
                if _opt_label:
                    _val_display = _opt_label
                elif _stored is True:
                    _val_display = "ja"
                elif _stored is False:
                    _val_display = "nein"
                elif _stored is None:
                    _val_display = "unklar"
                else:
                    _val_display = str(_stored)
                _recht_str = (" -> " + _opt_recht) if _opt_recht else ""
                _line = (
                    "  Frage gestellt: \"" + _frage_kurz + "...\""
                    + "\n    Antwort: " + _val_display + _recht_str
                    + " -- NICHT erneut nach diesem Thema fragen!"
                )
                w_lines.append(_line)
            if w_lines:
                parts.append("Bereits geklärte Rechtsfragen (KEINESFALLS erneut stellen!):\n" + "\n".join(w_lines))

            # Ausstehende Weichenstellung
            if getattr(state, 'pending_weiche', None):
                _wid = state.pending_weiche
                _wdef = self.lib.weichenstellungen.get(_wid, {}) if hasattr(self.lib, 'weichenstellungen') else {}
                _bslot = _wdef.get("branch_slot", _wid)
                _opt_str = ", ".join(
                    f"{o['label']}→{repr(o['wert'])}" for o in (_wdef.get("optionen") or [])
                )
                parts.append(
                    f"AKTIVE WEICHENSTELLUNG '{_bslot}': Nutzer antwortet darauf. "
                    f"Extrahiere in weichen_slot_extraktionen['{_bslot}']. "
                    f"Gültige Werte: {_opt_str}"
                )

        anker_lines = []
        for term, deff in (self.lib.anker_klaerung or {}).items():
            labels = [str(kx.get("label")) for kx in (deff.get("kontexte") or []) if kx.get("label")]
            if labels:
                anker_lines.append(f"- {term} (auch Wortvarianten): {' / '.join(labels)}")
        if anker_lines:
            parts.append(
                "MEHRDEUTIGE BEGRIFFE: Nennt der Nutzer einen davon (auch als Verb, "
                "z.B. \"abgemahnt\") und ist das Rechtsgebiet noch unklar, MUSS deine "
                "naechste_frage den Zusammenhang konkret klären:\n" + "\n".join(anker_lines))
        # Konstellations-IDs zur LLM-gestützten Sensibilitäts-Erkennung
        konst_lines = []
        for kid, meta in (self.lib.konstellationen or {}).items():
            titel = meta.get("titel") or kid
            konst_lines.append(f"- {kid}: {titel}")
        if konst_lines:
            parts.append("JURISTISCHE KONSTELLATIONEN (für vermutete_konstellationen):\n"
                         + "\n".join(konst_lines))

        # ── Sachverhaltstiefe je Rechtssystem ────────────────────────────────
        # DESIGN: Nur das PFLICHT-Feld blockiert genug_infos. Optionale Felder werden
        # NUR dann erfragt, wenn konkrete Hinweise aus dem Sachverhalt vorliegen —
        # KEINE systematische Checkliste!
        if state is not None and state.vermutete_rechtsgebiete:
            _top_skill = state.vermutete_rechtsgebiete[0].skill
            _rs = config.rechtssystem_fuer_skill(_top_skill)
            _tiefe_bekannt = getattr(state, 'sachverhalts_tiefe', {}) or {}

            # Pflicht: blockiert Handoff bis bekannt. Optional: nur bei konkreten Hinweisen.
            if _rs == "StR":
                _pflicht = [
                    ("tatbestand_subj",
                     "Gibt es Anzeichen dafür, dass der andere NICHT vorsätzlich gehandelt hat "
                     "(Vorsatz = Wissen und Wollen der Tat)? — z.B. offensichtliches Versehen, "
                     "Unfall, Irrtum, psychische Ausnahmesituation?"),
                ]
                _optional = [
                    ("tatbestand_obj",
                     "genaue Tathandlung/Erfolg — oft schon in woraus enthalten"),
                    ("rechtfertigungsgrund",
                     "Notwehr/Notstand/Einwilligung — NUR wenn Nutzer das andeutet"),
                    ("schuldfaktor",
                     "Schuldminderung/-ausschluss — NUR wenn konkrete Hinweise (psychische Erkrankung, Alkohol, Irrtum)"),
                ]
            elif _rs == "ÖR":
                _pflicht = [
                    ("bescheid_art",
                     "Art des Verwaltungsakts / der behördlichen Maßnahme (Bescheid, Verbot, Genehmigung)?"),
                    ("betroffene_grundrechte_interessen",
                     "Welche Grundrechte (Art. GG) oder privaten Interessen beeinträchtigt?"),
                ]
                _optional = [
                    ("oeffentliches_interesse",
                     "Zweck der Behörde / öffentliches Interesse — NUR wenn relevant"),
                    ("verhaeltnismaessigkeit",
                     "Verhältnismäßigkeit/mildere Mittel — NUR wenn diskutiert"),
                ]
            elif _rs == "ZR":
                _pflicht = []   # ZR: keine extra Pflicht-Tiefe
                _optional = [
                    ("fristen_verjährung",
                     "Fristen/Verjährung — NUR wenn konkret relevant"),
                    ("bisherige_schritte",
                     "bisherige Schritte (Mahnungen etc.) — NUR wenn vom Nutzer erwähnt"),
                    ("beweismittel",
                     "Beweismittel — NUR wenn konkret angesprochen"),
                ]
            else:
                _pflicht, _optional = [], []

            if _pflicht or _optional:
                _tiefe_lines = ["SACHVERHALTSTIEFE (" + _rs + "):"]
                # Bereits bekannte Felder
                _alle_felder = _pflicht + _optional
                _bereits = [(fid, _tiefe_bekannt[fid]) for fid, _ in _alle_felder
                            if _tiefe_bekannt.get(fid)]
                if _bereits:
                    _tiefe_lines.append("Bereits bekannt — KEINESFALLS erneut fragen:")
                    _tiefe_lines.extend(
                        "  " + fid + ": " + str(_tiefe_bekannt[fid])
                        for fid, _ in _bereits)
                # Offene Pflicht-Felder
                _pflicht_offen = [(fid, fbez) for fid, fbez in _pflicht
                                  if not _tiefe_bekannt.get(fid)]
                if _pflicht_offen:
                    _tiefe_lines.append(
                        "PFLICHT-Feld (genug_infos=false solange unbekannt) — "
                        "JETZT als naechste_frage konkret und fallbezogen erfragen:")
                    _fid0, _fbez0 = _pflicht_offen[0]
                    _tiefe_lines.append("  → " + _fid0 + ": " + _fbez0)
                    if len(_pflicht_offen) > 1:
                        _tiefe_lines.append("  (danach: "
                            + ", ".join(f[0] for f in _pflicht_offen[1:]) + ")")
                else:
                    if _rs != "ZR":
                        _tiefe_lines.append(
                            "Alle Pflicht-Felder bekannt → genug_infos=true erlaubt, "
                            "wenn Sachverhalt insgesamt klar.")
                # Optionale Felder — nur als Hinweis, kein systematisches Abfragen
                _opt_offen = [(fid, fbez) for fid, fbez in _optional
                              if not _tiefe_bekannt.get(fid)]
                if _opt_offen:
                    _tiefe_lines.append(
                        "Optional (NUR erfragen wenn konkrete Hinweise im Sachverhalt — "
                        "KEINE systematische Liste abarbeiten!):")
                    for _fid, _fbez in _opt_offen:
                        _tiefe_lines.append("  " + _fid + ": " + _fbez)
                _tiefe_lines.append(
                    "Extrahiere Nutzer-Antworten in rechtssystem_tiefe. "
                    "Halte naechste_frage fallbezogen und konkret — nicht generisch.")
                parts.append("\n".join(_tiefe_lines))

        return "\n\n".join(parts) if parts else None

    def extraction_messages(self, history: list[dict], user_text: str, state=None) -> list[dict]:
        msgs = [{"role": "system", "content": _EXTRACTION_SYSTEM},
                {"role": "system", "content": _SLUGS_LINE}]
        ctx = self._kontext_block(state)
        if ctx:
            msgs.append({"role": "system", "content": ctx})
        msgs.extend(history[-8:])  # begrenzter Kontext
        return msgs

    def tighten(self, prompt: list[dict]) -> list[dict]:
        return prompt + [{"role": "system", "content": _TIGHTEN}]

    # ── Fragen ───────────────────────────────────────────────────────────
    def _variant(self, slot_id: str, sprachstil: str, turn: int) -> str:
        block = self.lib.frageketten.get(slot_id, {}) or {}
        variants = block.get(sprachstil) or block.get("laie") or ["Können Sie das näher beschreiben?"]
        return variants[turn % len(variants)]

    def start_frage(self, sprachstil: str = "laie") -> str:
        return self._variant("start", sprachstil, 0)

    def frage(self, slot_id: str, sprachstil: str, turn: int,
              spiegeln_wert: Optional[str] = None) -> str:
        frage = self._variant(slot_id, sprachstil, turn)
        block = self.lib.frageketten.get(slot_id, {}) or {}
        tmpl = block.get("spiegeln_template")
        if spiegeln_wert and tmpl:
            return f"{tmpl.format(wert=spiegeln_wert)} {frage}"
        return frage

    def klaerungsfrage(self, konflikt_slots: list[str], store) -> str:
        sid = konflikt_slots[0]
        versionen = store.data.get(sid, [])
        werte = [v.wert for v in versionen[-2:]]
        a, b = (werte + ["", ""])[:2]
        return ('Da habe ich jetzt zwei Angaben: einmal „{a}" und einmal „{b}". '
                'Was davon trifft zu — oder wie passt das zusammen?').format(a=a, b=b)

    # Konstellation → spezifische Hilfsangebote (statt generischer Hotline-Wand)
    _HOTLINES_BY_KONST = {
        "sexuelle_gewalt": "Vertrauliche Hilfe: Hilfetelefon Sexueller Missbrauch "
                           "0800 22 55 530, Frauennotruf 08000 116 016. Bei akuter Gefahr 110.",
        "kindesmissbrauch_vernachlaessigung":
            "Hilfetelefon Sexueller Missbrauch 0800 22 55 530. "
            "Nummer gegen Kummer (Kinder/Jugendliche) 116 111. Bei akuter Gefahr 110.",
        "haeusliche_gewalt":
            "Hilfetelefon Gewalt gegen Frauen 08000 116 016 (rund um die Uhr, "
            "anonym). Bei akuter Gefahr 110.",
        "stalking_nachstellung":
            "Weisser Ring 116 006. Hilfetelefon Gewalt gegen Frauen 08000 116 016. "
            "Bei akuter Bedrohung 110.",
        "koerperverletzung":
            "Weisser Ring 116 006 (Opferhilfe). Bei akuter Gefahr 110.",
        "toetung":
            "Telefonseelsorge 0800 111 0 111 (Trauer/Krise). Bei akuter "
            "Lebensgefahr 110.",
    }

    # Fallbezogene Begehr-Optionen je Konstellations-Gruppe.
    # Schluessel: Teilstring im Konstellations-ID (z.B. 'koerper' matcht
    # 'koerperverletzung'). Erster Match gewinnt.
    _BEGEHR_BY_KONST: list = [
        ("sexuelle_gewalt", [
            "a) eine Strafanzeige erstatten,",
            "b) eine einstweilige Verfügung / Annäherungsverbot beantragen,",
            "c) Schadensersatz oder Schmerzensgeld verlangen,",
            "d) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
        ("haeusliche_gewalt", [
            "a) eine Strafanzeige erstatten,",
            "b) ein Kontakt- oder Näherungsverbot erwirken,",
            "c) Schadensersatz oder Schmerzensgeld verlangen,",
            "d) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
        ("stalking", [
            "a) eine Strafanzeige erstatten (§ 238 StGB Nachstellung),",
            "b) eine einstweilige Verfügung beantragen,",
            "c) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
        ("koerper", [
            "a) eine Strafanzeige erstatten,",
            "b) Schadensersatz und/oder Schmerzensgeld verlangen,",
            f"c) erreichen, dass {{person}} das künftig unterlässt,",
            "d) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
        ("beleidigung", [
            "a) eine Strafanzeige erstatten,",
            "b) Unterlassung und Widerruf verlangen,",
            "c) Schadensersatz fordern,",
            "d) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
        ("diebstahl", [
            "a) eine Strafanzeige erstatten,",
            "b) Schadensersatz / Herausgabe verlangen,",
            "c) zunächst nur eine rechtliche Einschätzung der Lage,",
        ]),
    ]

    # Generische Fallback-Optionen (keine spezifische Konstellation erkannt)
    _BEGEHR_DEFAULT: list[str] = [
        "a) eine Strafanzeige erstatten,",
        "b) Schadensersatz oder Schmerzensgeld verlangen,",
        "c) erreichen, dass {person} das künftig unterlässt,",
        "d) zunächst nur eine rechtliche Einschätzung der Lage,",
    ]

    def _begehr_optionen(self, person: str,
                         konst_ids: Optional[list[str]]) -> list[str]:
        """Wählt die zur Konstellation passenden Begehr-Optionen."""
        for kid in (konst_ids or []):
            for prefix, opts in self._BEGEHR_BY_KONST:
                if prefix in kid:
                    return [o.replace("{person}", person) for o in opts]
        return [o.replace("{person}", person) for o in self._BEGEHR_DEFAULT]

    def hypothesen_test(self, sv: Sachverhalt, sensibilitaet: str,
                        konst_ids: Optional[list[str]] = None) -> str:
        person = sv.von_wem or "die andere Person"
        vorfall = sv.woraus or "Ihr geschildertes Anliegen"
        optionen = self._begehr_optionen(person, konst_ids)
        opts_text = "\n".join(optionen)
        text = (
            "Habe ich Sie richtig verstanden? Es geht um folgenden Vorfall:\n"
            f'„{vorfall}“\n\n'
            f"Was möchten Sie erreichen?\n{opts_text}\n"
            "oder mehreres davon?"
        )
        vorspann = self.hilfsangebot(sensibilitaet, konst_ids)
        return f"{vorspann}\n\n{text}" if vorspann else text

    def hilfsangebot(self, sensibilitaet: str,
                     konst_ids: Optional[list[str]] = None) -> Optional[str]:
        """Kontextgenauer Vorspann statt generischer Hotline-Wand:
        - Spezifischer Hinweis je getroffener Konstellation, wenn passend.
        - Generischer Fallback nur bei sehr hoher Sensibilität ohne Match."""
        if sensibilitaet not in ("hoch", "sehr hoch"):
            return None
        specifics = []
        seen = set()
        for kid in (konst_ids or []):
            txt = self._HOTLINES_BY_KONST.get(kid)
            if txt and txt not in seen:
                specifics.append(txt)
                seen.add(txt)
        if specifics:
            return "Wichtig vorab: " + " ".join(specifics)
        if sensibilitaet == "sehr hoch":
            return ("Wichtig vorab: Bei akuter Gefahr wählen Sie bitte 110. "
                    "Vertrauliche Hilfe: Weisser Ring 116 006, Hilfetelefon "
                    "Gewalt gegen Frauen 08000 116 016.")
        return None
