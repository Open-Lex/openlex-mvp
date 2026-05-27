#!/usr/bin/env python3
"""
add_content_missing_skills.py — Steckbriefe + GII-Paragraphen für Lücken-Skills
  - verbraucherrecht: BGB §§ 474-479 (GII) + 6 Steckbriefe
  - reiserecht: 5 Steckbriefe
  - versicherungsrecht: 5 Steckbriefe
  - transportrecht: 5 Steckbriefe
  - bildungsrecht: 5 Steckbriefe
  - kirchenrecht: 5 Steckbriefe
  - voelkerstrafrecht: 5 Steckbriefe (ICTY/ICC)
  - sanktionsrecht: 5 Steckbriefe (EuGH Kadi etc.)
  - waffenrecht: 5 Steckbriefe (BVerwG)
  - voelkerrecht: 5 Steckbriefe (IGH)
"""
import sys, os, re, hashlib, zipfile, io, time, urllib.request, ssl
from xml.etree import ElementTree as ET
from datetime import datetime

import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "/opt/openlex-mvp-v2/chromadb"
LOG_FILE    = "/tmp/add_content.log"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def strip_tags(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', text).strip()

def fetch_gii_xml(gii_kuerzel):
    url = f"https://www.gesetze-im-internet.de/{gii_kuerzel}/xml.zip"
    log(f"  GII: {url}")
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={'User-Agent': 'OpenLex-Bot/1.0'})
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        data = r.read()
    norms = []
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for fname in zf.namelist():
            if not fname.endswith('.xml'):
                continue
            try:
                root = ET.fromstring(zf.read(fname))
            except ET.ParseError:
                continue
            for norm in root.findall('.//norm'):
                meta = norm.find('metadaten')
                textd = norm.find('textdaten/text')
                if meta is None or textd is None:
                    continue
                el = meta.find('enbez')
                if el is None or not (el.text or '').strip():
                    continue
                enbez = el.text.strip()
                text = strip_tags(ET.tostring(textd, encoding='unicode'))
                if len(text) >= 30:
                    norms.append((enbez, text))
    return norms

def para_num(enbez):
    m = re.search(r'(\d+)', enbez)
    return int(m.group(1)) if m else None

def normalize_para(enbez):
    enbez = enbez.strip()
    if enbez.startswith('§'):
        parts = enbez.split()
        return ' '.join(parts[:2]) if len(parts) > 1 else enbez
    return enbez

def chunk_id_gii(skill, gesetz_abk, enbez):
    key = f"{skill}_{gesetz_abk}_{enbez}"
    return f"gii_{hashlib.sha256(key.encode()).hexdigest()[:14]}"

def embed_batch(model, texts, batch_size=16):
    all_embs = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, prompt_name="passage", batch_size=batch_size,
                            show_progress_bar=False, normalize_embeddings=True)
        all_embs.extend(embs.tolist())
    return all_embs

def add_if_new(col, ids, docs, metas, model):
    new_ids, new_docs, new_metas = [], [], []
    for cid, doc, meta in zip(ids, docs, metas):
        if col.get(ids=[cid])["ids"]:
            continue
        new_ids.append(cid)
        new_docs.append(doc)
        new_metas.append(meta)
    if not new_ids:
        return 0
    embs = embed_batch(model, new_docs)
    for i in range(0, len(new_ids), 64):
        col.add(ids=new_ids[i:i+64], documents=new_docs[i:i+64],
                metadatas=new_metas[i:i+64], embeddings=embs[i:i+64])
    return len(new_ids)

# ─── STECKBRIEFE ──────────────────────────────────────────────────────────────

STECKBRIEFE = []

# ── verbraucherrecht ──────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_heininger_eugh",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"EuGH","case_ref":"C-481/99"},
    "doc": """EuGH, Urteil vom 13.12.2001, C-481/99 — Heininger/Bayerische Hypo- und Vereinsbank

Sachverhalt: Eheleute Heininger hatten an ihrer Haustür einen Realkreditvertrag (Hypothekendarlehen) abgeschlossen, ohne über ihr Widerrufsrecht belehrt worden zu sein. Sie wollten den Vertrag widerrufen.

Rechtsfrage: Gilt das Widerrufsrecht der Haustürgeschäfterichtlinie (Richtlinie 85/577/EWG) auch für Realkreditverträge, und kann das Widerrufsrecht zeitlich unbegrenzt ausgeübt werden, wenn keine Widerrufsbelehrung erfolgte?

Entscheidung: Der EuGH entschied, dass die Haustürgeschäfterichtlinie auch auf Realkreditverträge anwendbar ist, obwohl diese nach deutschem Recht (damals § 5 Abs. 2 HWiG) ausgeschlossen waren. Der deutsche Ausschluss war richtlinienwidrig. Zudem läuft die Widerrufsfrist mangels ordnungsgemäßer Belehrung nie an — ein ewiges Widerrufsrecht.

Bedeutung: Das Urteil zwang den deutschen Gesetzgeber zur Anpassung und löste eine Welle von Klagen gegen Banken aus. Grundlegend für das Verhältnis von Haustürgeschäft und Immobilienfinanzierung. Eingeflossen in §§ 312 ff. BGB und § 355 BGB n.F. Das „ewige Widerrufsrecht" bei fehlerhafter Belehrung wurde später durch § 356b BGB eingeschränkt (Erlöschen nach 1 Jahr und 14 Tagen nach Auszahlung des Darlehens).

Normen: § 312 BGB, § 355 BGB, § 356b BGB; Richtlinie 85/577/EWG (Haustürgeschäfte)."""
  },
  { "id": "steckbrief_quelle_nachlieferung_eugh",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"EuGH","case_ref":"C-404/06"},
    "doc": """EuGH, Urteil vom 17.04.2008, C-404/06 — Quelle AG/Bundesverband der Verbraucherzentralen

Sachverhalt: Quelle lieferte einem Verbraucher einen mangelhaften Herd. Nach Nutzung des Herdes über mehrere Monate verlangte Quelle bei der Neulieferung (Nacherfüllung) eine Nutzungsentschädigung für die Zeit der Benutzung des mangelhaften Geräts.

Rechtsfrage: Darf der Verkäufer im Rahmen der Nacherfüllung beim Verbrauchsgüterkauf eine Nutzungsentschädigung für die Zeit verlangen, in der der Verbraucher die mangelhafte Sache genutzt hat?

Entscheidung: Nein. Der EuGH entschied, dass die Verbrauchsgüterkaufrichtlinie (1999/44/EG) einer nationalen Regelung entgegensteht, nach der der Verkäufer bei der Lieferung einer Ersatzsache Nutzungswertersatz für die mangelhafte Sache verlangen kann. Das deutsche Recht (§ 439 Abs. 4 BGB a.F.) war insoweit richtlinienwidrig und musste richtlinienkonform ausgelegt werden.

Bedeutung: Richtungsweisend für das Verbrauchsgüterkaufrecht. Verbraucher erhalten bei Nacherfüllung durch Neulieferung keinen Abzug für bereits gezogene Nutzungen. Eingeflossen in die Neufassung des § 439 BGB und jetzt in § 475 BGB (Verbrauchsgüterkauf).

Normen: §§ 434, 437, 439, 474 ff. BGB; Richtlinie 1999/44/EG über den Verbrauchsgüterkauf."""
  },
  { "id": "steckbrief_weber_putz_eugh",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"EuGH","case_ref":"C-65/09"},
    "doc": """EuGH, Urteil vom 16.06.2011, C-65/09 und C-87/09 — Weber/Wittmer und Putz/Medianess Electronics

Sachverhalt: Zwei verbundene Vorlagefragen: Einmal hatte ein Verbraucher mangelhafte Bodenfliesen verlegt, bevor der Mangel erkannt wurde. Im anderen Fall hatte ein Verbraucher einen mangelhaften Laptop gekauft. Es stellte sich die Frage, ob der Verkäufer bei Nacherfüllung durch Neulieferung die Kosten des Ausbaus der mangelhaften Sache und des Einbaus der Ersatzsache tragen muss.

Rechtsfrage: Verpflichtet die Verbrauchsgüterkaufrichtlinie den Verkäufer, beim Austausch einer mangelhaften, bereits eingebauten Sache die Aus- und Einbaukosten zu tragen?

Entscheidung: Ja. Der EuGH bejahte eine Pflicht des Verkäufers, bei der Nacherfüllung durch Neulieferung die Kosten des Ausbaus der mangelhaften Sache und des Einbaus der Ersatzsache zu tragen — auch wenn die Kosten den Kaufpreis erheblich übersteigen. § 439 BGB a.F. war insoweit richtlinienwidrig.

Bedeutung: Erhebliche Erweiterung der Verkäuferhaftung im Verbrauchsgüterkauf. Führte zur Aufnahme von § 475 Abs. 3 BGB n.F. (jetzt: Abs. 4) über Aus- und Einbaukosten. Maßgeblich für den Einbaufall (z.B. Fliesen, Fenster, Maschinen).

Normen: §§ 437, 439, 474, 475 BGB; Richtlinie 1999/44/EG Art. 3."""
  },
  { "id": "steckbrief_vw_abgasskandal_826",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"BGH","case_ref":"VI ZR 252/19"},
    "doc": """BGH, Urteil vom 25.05.2020, VI ZR 252/19 — VW-Abgasskandal / § 826 BGB

Sachverhalt: Ein Käufer hatte einen VW Passat mit einem EA189-Dieselmotor erworben, der mit einer Software ausgestattet war, die den Stickoxidausstoß auf dem Prüfstand manipulierte. Der Käufer verlangte Schadensersatz nach § 826 BGB von der Volkswagen AG.

Rechtsfrage: Hat die Volkswagen AG durch den bewussten Einsatz einer Manipulationssoftware in sittenwidriger Weise vorsätzlich einen Schaden beim Fahrzeugkäufer verursacht?

Entscheidung: Ja. Der BGH bejahte einen Anspruch aus § 826 BGB (vorsätzliche sittenwidrige Schädigung). VW hat durch die bewusste Täuschung über die Abgaswerte in einer gegen die guten Sitten verstoßenden Weise und mit Schädigungsvorsatz gehandelt. Der Käufer hat einen Schaden erlitten, der im Abschluss des ungewollten Kaufvertrags liegt. Der Schadensersatz berechnet sich als Erstattung des Kaufpreises abzüglich einer Nutzungsentschädigung Zug um Zug gegen Rückgabe des Fahrzeugs.

Bedeutung: Grundlagenentscheidung für Dieselklagen in Deutschland. Klärt Voraussetzungen von § 826 BGB bei Produktmanipulation durch Hersteller, insbesondere Sittenwidrigkeit, Schädigungsvorsatz und Schadensberechnung. Auslöser für Tausende weiterer Verfahren und Nachfolgeentscheidungen.

Normen: § 826 BGB, § 31 BGB (Organhaftung), § 249 BGB (Schadensberechnung)."""
  },
  { "id": "steckbrief_planet49_eugh",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"EuGH","case_ref":"C-673/17"},
    "doc": """EuGH, Urteil vom 01.10.2019, C-673/17 — Planet49 GmbH/Bundesverband der Verbraucherzentralen

Sachverhalt: Das Online-Gewinnspiel des Unternehmens Planet49 verwendete ein vorausgefülltes Ankreuzkästchen, mit dem Nutzer in das Setzen von Cookies einwilligten. Der Bundesverband der Verbraucherzentralen klagte dagegen.

Rechtsfrage: Ist eine Einwilligung in Cookies wirksam, wenn sie durch ein vorausgefülltes Ankreuzkästchen (Opt-out-Lösung) eingeholt wird?

Entscheidung: Nein. Der EuGH entschied, dass eine Cookie-Einwilligung keine wirksame Einwilligung im Sinne der ePrivacy-Richtlinie und der DSGVO darstellt, wenn sie durch ein vorausgefülltes Kästchen erteilt wird. Erforderlich ist eine aktive Handlung (Opt-in). Außerdem muss der Nutzer darüber informiert werden, wie lange Cookies aktiv bleiben und ob Dritte Zugang zu den Cookies erhalten.

Bedeutung: Definiert Cookie-Einwilligung als Opt-in-Pflicht nach deutschem und europäischem Recht. Grundlage für die deutschen Anforderungen an Cookie-Banner (TTDSG 2021). Maßgeblich für das gesamte Online-Marketing und Datenschutzrecht im E-Commerce.

Normen: Art. 5 Abs. 3 ePrivacy-Richtlinie 2002/58/EG; Art. 6 DSGVO; §§ 312 ff. BGB (Fernabsatz); TTDSG § 25."""
  },
  { "id": "steckbrief_gut_springenheide_eugh",
    "skill": "verbraucherrecht",
    "meta": {"source_type":"urteil","skill":"verbraucherrecht","gericht":"EuGH","case_ref":"C-210/96"},
    "doc": """EuGH, Urteil vom 16.07.1998, C-210/96 — Gut Springenheide GmbH/Oberkreisdirektor des Kreises Steinfurt

Sachverhalt: Das Unternehmen Gut Springenheide vertrieb Eier mit der Aufschrift „6-Korn-10 frische Eier — aus Bodenhaltung", wobei die Hühner tatsächlich nur einen geringen Anteil der beworbenen Körner erhielten. Es war streitig, nach welchem Maßstab die Irreführung von Verbrauchern zu beurteilen sei.

Rechtsfrage: Welcher Verbraucher-Maßstab ist bei der Beurteilung der Irreführung von Verbrauchern anzuwenden — der flüchtige Verbraucher oder der aufmerksame, verständige Durchschnittsverbraucher?

Entscheidung: Der EuGH entwickelte den Maßstab des „durchschnittlich informierten, aufmerksamen und verständigen Verbrauchers" als Leitbild für das europäische Verbraucherrecht. Nationale Gerichte können diesen Maßstab in eigener Würdigung anwenden; ein repräsentatives Meinungsforschungsgutachten ist grundsätzlich nicht zwingend erforderlich.

Bedeutung: Grundlegendes Urteil zum europäischen Verbraucherleitbild. Das Bild des „mündigen Verbrauchers" prägt seitdem das gesamte Wettbewerbs- und Verbraucherrecht. Abkehr vom schwachen, schutzbedürftigen Verbraucher hin zum informierten Durchschnittsverbraucher als Maßstab.

Normen: § 5 UWG (irreführende Werbung); Art. 7 RL 2005/29/EG (UGP-Richtlinie); §§ 13, 14 BGB (Verbraucher/Unternehmer-Begriff)."""
  },
]

# ── reiserecht ────────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_sturgeon_eugh",
    "skill": "reiserecht",
    "meta": {"source_type":"urteil","skill":"reiserecht","gericht":"EuGH","case_ref":"C-402/07"},
    "doc": """EuGH, Urteil vom 19.11.2009, C-402/07 und C-432/07 — Sturgeon/Condor und Böck/Air France

Sachverhalt: Passagiere erlitten erhebliche Verspätungen (über 3 Stunden am Zielort). Die Fluggesellschaften verweigerten die Ausgleichsleistungen nach Art. 7 der Fluggastrechteverordnung (VO 261/2004) mit dem Argument, die Verordnung sehe Ausgleich nur bei Annullierungen, nicht bei Verspätungen vor.

Rechtsfrage: Können Fluggäste bei einer Verspätung von drei Stunden oder mehr am Zielort eine Ausgleichsleistung nach Art. 7 VO 261/2004 beanspruchen?

Entscheidung: Ja. Der EuGH entschied, dass Fluggäste bei Verspätungen, die zu einem Zeitverlust von drei Stunden oder mehr führen, denselben Ausgleichsanspruch wie bei Annullierungen haben. Die Unterscheidung in der Verordnung verstoße sonst gegen den Gleichbehandlungsgrundsatz. Entscheidend ist die Ankunftszeit am Zielort.

Bedeutung: Revolutionäres Urteil für Fluggäste. Begründet Ausgleichsansprüche (250 – 600 EUR) auch bei erheblichen Verspätungen. Maßstab für den gesamten europäischen Luftverkehr; ausgedehnt auf Züge und Schiffe durch Folgerecht.

Normen: Art. 5, 7 VO (EG) 261/2004; §§ 651a ff. BGB (Reisevertragsrecht)."""
  },
  { "id": "steckbrief_wallentin_hermann_eugh",
    "skill": "reiserecht",
    "meta": {"source_type":"urteil","skill":"reiserecht","gericht":"EuGH","case_ref":"C-549/07"},
    "doc": """EuGH, Urteil vom 22.12.2008, C-549/07 — Wallentin-Hermann/Alitalia

Sachverhalt: Der Flug von Frau Wallentin-Hermann wurde wegen eines komplexen technischen Problems am Flugzeug annulliert. Die Fluggesellschaft berief sich auf einen „außergewöhnlichen Umstand" i.S.d. Art. 5 Abs. 3 VO 261/2004, der sie von der Ausgleichspflicht befreit.

Rechtsfrage: Stellt ein technisches Problem an einem Flugzeug einen „außergewöhnlichen Umstand" dar, der die Fluggesellschaft von der Ausgleichspflicht bei Annullierung befreit?

Entscheidung: Grundsätzlich nein. Technische Probleme, die zur regulären Wartung entdeckt werden oder typischerweise im Rahmen des Betriebs auftreten, sind kein außergewöhnlicher Umstand. Außergewöhnlich sind nur Ereignisse, die nicht der normalen Ausübung der Tätigkeit eines Luftfahrtunternehmens innewohnen und außerhalb seiner tatsächlichen Kontrolle liegen (z.B. Vogelschlag, Streik Dritter, Terrorakt).

Bedeutung: Definiert die Ausnahme vom Ausgleichsanspruch eng. Technische Defekte führen nur in eng begrenzten Ausnahmefällen zur Befreiung. Grundlegend für die Praxis von Fluggastrechts-Klagen.

Normen: Art. 5 Abs. 3, Art. 7 VO (EG) 261/2004; §§ 651i ff. BGB."""
  },
  { "id": "steckbrief_mcdonagh_vulkanasche_eugh",
    "skill": "reiserecht",
    "meta": {"source_type":"urteil","skill":"reiserecht","gericht":"EuGH","case_ref":"C-12/11"},
    "doc": """EuGH, Urteil vom 31.01.2013, C-12/11 — McDonagh/Ryanair

Sachverhalt: Nach dem Ausbruch des isländischen Vulkans Eyjafjallajökull (April 2010) wurden Tausende Flüge für mehrere Tage gestrichen. Frau McDonagh war tagelang gestrandet und verlangte von Ryanair Unterbringungs- und Verpflegungskosten.

Rechtsfrage: Sind Fluggesellschaften auch bei einem „außergewöhnlichen Umstand" wie einer Naturkatastrophe verpflichtet, Betreuungsleistungen (Unterkunft, Mahlzeiten) zu erbringen, und zwar ohne zeitliche oder betragsmäßige Begrenzung?

Entscheidung: Ja. Der EuGH stellte klar: Die Pflicht zur Betreuung (Art. 9 VO 261/2004 — Unterkunft, Mahlzeiten, Kommunikation) gilt auch bei außergewöhnlichen Umständen. Diese Pflicht wird durch die Außergewöhnlichkeit des Umstands nicht beseitigt, auch wenn dadurch die Ausgleichspflicht nach Art. 7 entfällt. Es gibt keine betragsmäßige Höchstgrenze; die Kosten müssen aber verhältnismäßig sein.

Bedeutung: Klarstellung, dass Betreuungspflichten und Ausgleichspflichten voneinander unabhängig sind. Fluggesellschaften können sich nicht auf höhere Gewalt berufen, um Reisende ohne Unterkunft und Verpflegung zu lassen.

Normen: Art. 5 Abs. 3, Art. 9 VO (EG) 261/2004; §§ 651a ff., 651i ff. BGB."""
  },
  { "id": "steckbrief_bgh_reisemangel_hotel",
    "skill": "reiserecht",
    "meta": {"source_type":"urteil","skill":"reiserecht","gericht":"BGH","case_ref":"X ZR 60/14"},
    "doc": """BGH, Urteil vom 18.11.2014, X ZR 60/14 — Reisemangel durch Doppelbuchung / Hotelunterkunft

Sachverhalt: Ein Reiseveranstalter buchte Kunden in ein Hotel mit vereinbarten Zimmern ein. Bei Ankunft waren die gebuchten Zimmer vergeben (Overbooking). Die Reisenden wurden in einem qualitativ schlechteren Hotel untergebracht. Sie verlangten Minderung des Reisepreises.

Rechtsfrage: Stellt die Zuweisung eines anderen als des gebuchten Hotels einen Reisemangel dar, der zur Minderung berechtigt? Wie ist der Minderungsbetrag zu berechnen?

Entscheidung: Ja. Der BGH bestätigte, dass die Abweichung von der vertraglich vereinbarten Leistung (vereinbartes Hotel) einen Mangel der Reise darstellt, auch wenn das Ersatzhotel objektiv gleichwertig ist. Der Reisende hat Anspruch auf Minderung des Reisepreises entsprechend dem Wertverhältnis (§ 651d BGB a.F.; heute § 651m BGB).

Bedeutung: Grundlegend für die Berechnung von Minderungsansprüchen im Pauschalreiserecht. Der vereinbarte Standard entscheidet, nicht ein abstrakt gleichwertiger Ersatz. Wichtig für Praktiker und Reiserechtsklagen.

Normen: §§ 651a, 651c, 651d BGB a.F. (heute §§ 651a, 651i, 651m BGB n.F.); § 651l BGB (Abhilfe)."""
  },
  { "id": "steckbrief_bgh_reiselaerm",
    "skill": "reiserecht",
    "meta": {"source_type":"urteil","skill":"reiserecht","gericht":"BGH","case_ref":"X ZR 49/07"},
    "doc": """BGH, Urteil vom 16.09.2008, X ZR 49/07 — Baulärm am Urlaubsort als Reisemangel

Sachverhalt: Ein Reisender buchte eine Pauschalreise in ein Strandhotel. Während des Urlaubs führten benachbarte Bauarbeiten zu erheblichem Lärm. Der Reisende verlangte Minderung und Schadensersatz.

Rechtsfrage: Stellt Baulärm, der aus dem Umfeld des Hotels stammt und nicht vom Reiseveranstalter zu vertreten ist, einen Reisemangel dar? Muss der Reiseveranstalter über bekannte Baulärmsituationen informieren?

Entscheidung: Ja, erheblicher Baulärm kann einen Reisemangel begründen, sofern die Reise dadurch nicht den zugesicherten Eigenschaften entspricht oder für den Reisenden unzumutbar wird. Der Reiseveranstalter hat eine Informationspflicht, wenn ihm Baulärm im Buchungszeitpunkt bekannt war oder bekannt sein musste.

Bedeutung: Präzisierung des Reisemangelbegriffs bei umgebungsbedingten Störungen. Grundlage für Ansprüche bei Lärm, Baustellen, Geruchsbelästigungen im Urlaubsgebiet. Wichtige Aufklärungspflicht des Veranstalters.

Normen: §§ 651a, 651c BGB a.F. (heute §§ 651a, 651i BGB n.F.); § 280 BGB (Schadensersatz); Informationspflichten nach BGB-InfoV/BVBR."""
  },
]

# ── versicherungsrecht ────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_test_achats_eugh",
    "skill": "versicherungsrecht",
    "meta": {"source_type":"urteil","skill":"versicherungsrecht","gericht":"EuGH","case_ref":"C-236/09"},
    "doc": """EuGH, Urteil vom 01.03.2011, C-236/09 — Association belge des Consommateurs Test-Achats/Conseil des ministres

Sachverhalt: Das belgische Versicherungsrecht erlaubte es Versicherern, bei privaten Lebens- und Krankenversicherungen unterschiedliche Prämien nach Geschlecht (sog. Unisex-Ausnahme) zu erheben. Dies stützte sich auf Art. 5 Abs. 2 der Richtlinie 2004/113/EG.

Rechtsfrage: Ist die Unisex-Ausnahme in Art. 5 Abs. 2 der Richtlinie mit dem Grundsatz der Gleichbehandlung von Männern und Frauen (Art. 21, 23 GRCh) vereinbar?

Entscheidung: Nein. Der EuGH erklärte Art. 5 Abs. 2 der Richtlinie 2004/113/EG für ungültig, weil er dem Grundsatz der Gleichbehandlung widerspricht. Ab dem 21.12.2012 dürfen Versicherungsprämien und -leistungen nicht mehr nach dem Geschlecht differenzieren.

Bedeutung: Einführung der Unisex-Tarife im gesamten europäischen Versicherungswesen. Erhebliche Auswirkungen auf Kfz-, Lebens-, Kranken- und Berufsunfähigkeitsversicherungen. Junge Männer zahlen seitdem in der Kfz-Versicherung deutlich weniger, junge Frauen mehr.

Normen: Art. 21, 23 GRCh; Richtlinie 2004/113/EG; §§ 1, 20 AGG; VVG §§ 1 ff."""
  },
  { "id": "steckbrief_bgh_lebensversicherung_rueckkauf",
    "skill": "versicherungsrecht",
    "meta": {"source_type":"urteil","skill":"versicherungsrecht","gericht":"BGH","case_ref":"IV ZR 76/11"},
    "doc": """BGH, Urteil vom 07.11.2012, IV ZR 76/11 — Kündigung Lebensversicherung / Rückkaufswert

Sachverhalt: Ein Versicherungsnehmer kündigte seine kapitalbildende Lebensversicherung vorzeitig. Die Versicherung errechnete den Rückkaufswert unter Abzug hoher Abschlusskosten (Zillmerung), was zu einem sehr niedrigen oder sogar negativen Rückkaufswert führte.

Rechtsfrage: Ist die Klausel über die Berechnung des Rückkaufswerts wirksam, die bei Kündigung in den ersten Jahren zu erheblichem Verlust für den Versicherungsnehmer führt?

Entscheidung: Der BGH entschied, dass Klauseln, die den Rückkaufswert auf null setzen oder drastisch mindern, den Versicherungsnehmer unangemessen benachteiligen (§ 307 BGB) und daher unwirksam sind. Als Rechtsfolge ist der Rückkaufswert auf der Grundlage eines „angemessenen" Wertes zu berechnen.

Bedeutung: Begrenzt die Vertragsfreiheit der Versicherungswirtschaft bei der Vertragsgestaltung. Stärkt Verbraucherrechte bei vorzeitiger Kündigung. Führte zu erheblichen Nachzahlungen durch Versicherungsgesellschaften und zu Gesetzesänderungen im VVG (§ 169 VVG über Mindestrückkaufswert).

Normen: § 169 VVG (Rückkaufswert); § 307 BGB (AGB-Kontrolle); §§ 159 ff. VVG (Lebensversicherung)."""
  },
  { "id": "steckbrief_bgh_berufsunfaehigkeit",
    "skill": "versicherungsrecht",
    "meta": {"source_type":"urteil","skill":"versicherungsrecht","gericht":"BGH","case_ref":"IV ZR 130/09"},
    "doc": """BGH, Urteil vom 26.01.2011, IV ZR 130/09 — Berufsunfähigkeitsversicherung / abstrakter Verweis

Sachverhalt: Ein Versicherungsnehmer wurde berufsunfähig. Die Versicherung verweigerte die Leistung mit dem Argument, er könne in einem anderen Beruf (abstrakte Verweisung) arbeiten, der seinem bisherigen Lebensstandard und seiner Ausbildung entspreche.

Rechtsfrage: Unter welchen Voraussetzungen kann ein Versicherer den Leistungsanspruch wegen Berufsunfähigkeit durch Verweis auf eine andere vergleichbare Tätigkeit (abstrakte Verweisung) abwenden?

Entscheidung: Der BGH konkretisiert strenge Voraussetzungen für eine wirksame abstrakte Verweisung: Der Verweisberuf muss der bisherigen Lebensstellung des Versicherungsnehmers entsprechen, tatsächlich am Markt existieren und für ihn zumutbar erreichbar sein. Formalqualifikationen des Verweisberufs müssen erreichbar sein.

Bedeutung: Grundlagenentscheidung zur Berufsunfähigkeitsversicherung. Schützt Versicherungsnehmer vor willkürlicher abstrakter Verweisung auf theoretische Berufe. Prägend für die Auslegung von BU-Versicherungsklauseln.

Normen: §§ 172 ff. VVG (Berufsunfähigkeitsversicherung); § 307 BGB (AGB-Kontrolle); § 15 VVG a.F."""
  },
  { "id": "steckbrief_bgh_versicherung_arglistige_anzeigepflichtverletzung",
    "skill": "versicherungsrecht",
    "meta": {"source_type":"urteil","skill":"versicherungsrecht","gericht":"BGH","case_ref":"IV ZR 252/10"},
    "doc": """BGH, Urteil vom 28.09.2011, IV ZR 252/10 — Arglistige Anzeigepflichtverletzung / Rücktritt des Versicherers

Sachverhalt: Bei Abschluss einer Krankenversicherung verschwieg der Versicherungsnehmer arglistig eine Vorerkrankung. Der Versicherer trat nach Schadenfall vom Vertrag zurück und verweigerte alle Leistungen.

Rechtsfrage: Wann kann ein Versicherer wegen arglistiger Anzeigepflichtverletzung vom Versicherungsvertrag zurücktreten, und welche Rechtsfolgen hat dies?

Entscheidung: Der BGH bestätigte das Rücktrittsrecht des Versicherers bei arglistiger Anzeigepflichtverletzung (§ 22 VVG n.F.). Bei Arglist entfällt die Leistungspflicht vollständig; der Versicherer ist auch nicht zur anteiligen Leistung verpflichtet. Die Arglist muss vom Versicherer bewiesen werden.

Bedeutung: Klarstellung zu Beweislast und Rechtsfolgen arglistiger Täuschung bei Vertragsschluss. Grundlegend für die Praxis der Kranken-, Lebens- und BU-Versicherung. Unterschied zwischen einfacher und arglistiger Anzeigepflichtverletzung.

Normen: §§ 19, 20, 21, 22 VVG n.F. (Anzeigepflichtverletzung, Rücktritt, Arglist); § 123 BGB (Anfechtung wegen Arglist)."""
  },
  { "id": "steckbrief_bgh_versicherung_obliegenheit",
    "skill": "versicherungsrecht",
    "meta": {"source_type":"urteil","skill":"versicherungsrecht","gericht":"BGH","case_ref":"IV ZR 304/13"},
    "doc": """BGH, Urteil vom 08.07.2015, IV ZR 304/13 — Obliegenheitsverletzung nach Versicherungsfall / Aufklärungspflicht

Sachverhalt: Nach einem Einbruchsdiebstahl machte der Versicherungsnehmer gegenüber dem Versicherer unrichtige Angaben zum Umfang des Schadens. Der Versicherer verweigerte gestützt auf Obliegenheitsverletzung (§ 28 VVG) die gesamte Leistung.

Rechtsfrage: Führt jede Aufklärungsobliegenheitsverletzung nach dem Versicherungsfall zum vollständigen Leistungsausschluss, oder ist eine Quotelung möglich?

Entscheidung: Der BGH bestätigte das abgestufte Modell nach § 28 Abs. 2 VVG: Bei grob fahrlässiger Obliegenheitsverletzung erfolgt Leistungskürzung nach dem Grad des Verschuldens (Quotelung). Vollständige Leistungsfreiheit nur bei Vorsatz oder wenn der Versicherungsnehmer die Belehrung über die Folgen der Obliegenheitsverletzung nicht erhalten hat.

Bedeutung: Schützt Versicherungsnehmer vor unverhältnismäßig harten Folgen von Obliegenheitsverletzungen. Das neue VVG (ab 2008) ersetzt das Alles-oder-Nichts-Prinzip durch Quotelung; der BGH konkretisiert die Maßstäbe.

Normen: § 28 VVG n.F. (Obliegenheitsverletzung, Quotelung); §§ 31, 34 VVG (Auskunftspflicht); § 81 VVG (grobe Fahrlässigkeit)."""
  },
]

# ── transportrecht ────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_bgh_cmr_haftung",
    "skill": "transportrecht",
    "meta": {"source_type":"urteil","skill":"transportrecht","gericht":"BGH","case_ref":"I ZR 211/01"},
    "doc": """BGH, Urteil vom 29.07.2004, I ZR 211/01 — CMR-Haftungsbegrenzung bei qualifiziertem Verschulden

Sachverhalt: Ein Frachtführer verlor im internationalen Straßengüterverkehr eine wertvolle Ladung. Der Auftraggeber verlangte vollen Schadensersatz; der Frachtführer berief sich auf die Haftungsbeschränkung nach Art. 23 CMR (8,33 SZR/kg).

Rechtsfrage: Entfällt die Haftungsbegrenzung der CMR, wenn dem Frachtführer qualifiziertes Verschulden (Vorsatz oder grobe Fahrlässigkeit, Art. 29 CMR) anzulasten ist?

Entscheidung: Ja. Art. 29 CMR lässt die Haftungsbeschränkung entfallen, wenn der Schaden durch den Frachtführer, seine Leute oder sonstige Personen vorsätzlich oder durch grob fahrlässiges Verhalten verursacht wurde. Der BGH präzisiert, dass im deutschen Recht „leichtfertig und mit dem Bewusstsein handeln, dass ein Schaden eintreten werde" ausreicht (gleichzustellende Fahrlässigkeit).

Bedeutung: Zentrale Entscheidung zur CMR-Haftung. Warnt Frachtführer vor lückenhafter Schadensvorsorge. Grundlegend für grenzüberschreitende Straßentransporte. Die CMR als Einheitsrecht verdrängt nationales Recht vollständig für internationale Straßentransporte.

Normen: Art. 17, 23, 29 CMR; §§ 425, 431, 435 HGB (nationale Speditionshaftung analog)."""
  },
  { "id": "steckbrief_montreal_walz_eugh",
    "skill": "transportrecht",
    "meta": {"source_type":"urteil","skill":"transportrecht","gericht":"EuGH","case_ref":"C-63/09"},
    "doc": """EuGH, Urteil vom 06.05.2010, C-63/09 — Walz/Clickair SA

Sachverhalt: Dem Passagier Walz ging sein aufgegebenes Gepäck bei einem Flug verloren. Die Fluggesellschaft zahlte nur die Haftungsbeschränkung nach dem Montrealer Übereinkommen (MÜ), die auf 1.000 SZR begrenzt war. Walz machte geltend, diese Beschränkung erfasse nur Sachschäden, nicht Nichtvermögensschäden.

Rechtsfrage: Umfasst die Haftungsbeschränkung des Montrealer Übereinkommens (Art. 22 MÜ) bei Gepäckverlust auch immaterielle Schäden?

Entscheidung: Ja. Der EuGH entschied, dass die Haftungsbegrenzung des Art. 22 MÜ alle Schadensarten erfasst — sowohl Sachschäden als auch immaterielle Schäden. Eine Aufspaltung in verschiedene Schadensarten würde den einheitlichen Charakter des MÜ unterhöhlen.

Bedeutung: Einheitliche Auslegung des Montrealer Übereinkommens für alle EU-Staaten. Klärt, dass Fluggäste bei Gepäckverlust auch für immateriellen Schaden nur bis zur Haftungsgrenze entschädigt werden. Grundlegend für Gepäckschadensregulierung in der Luftfahrt.

Normen: Art. 17, 22 Montrealer Übereinkommen (MÜ); VO (EG) 2027/97; §§ 44 ff. LuftVG."""
  },
  { "id": "steckbrief_bgh_spediteur_adsp",
    "skill": "transportrecht",
    "meta": {"source_type":"urteil","skill":"transportrecht","gericht":"BGH","case_ref":"I ZR 49/13"},
    "doc": """BGH, Urteil vom 19.03.2015, I ZR 49/13 — Spediteurhaftung / ADSp-Klauseln und Haftungsverzicht

Sachverhalt: Ein Spediteur verwahrte Waren seines Kunden in einem nicht genehmigten Lager, in dem die Waren durch Brand vernichtet wurden. In den ADSp (Allgemeine Deutsche Spediteurbedingungen) war die Haftung des Spediteurs begrenzt. Der Auftraggeber verlangte vollen Schadensersatz.

Rechtsfrage: Greift die ADSp-Haftungsbegrenzung, wenn der Spediteur durch die Wahl eines nicht geeigneten Lagerortes qualifiziert fahrlässig gehandelt hat?

Entscheidung: Nein. Bei qualifiziertem Verschulden des Spediteurs (§ 435 HGB: leichtfertig handeln mit Bewusstsein des wahrscheinlichen Schadenseintritts) entfällt die Haftungsbegrenzung nach ADSp und HGB. Der BGH bestätigt die Durchgriffshaftung bei Organisationsverschulden.

Bedeutung: Warnt Spediteure und Logistiker vor leichtfertigem Umgang mit Kundengütern. Grundlegend für die Reichweite der ADSp-Haftungsbegrenzung. Verdeutlicht das Verhältnis von AGB-Haftungsbeschränkung und gesetzlichem Haftungsdurchbruch.

Normen: §§ 425, 431, 435 HGB; ADSp 2016 Nr. 23, 27; § 305 ff. BGB (AGB-Kontrolle)."""
  },
  { "id": "steckbrief_bgh_frachtfuehrer_rollende_ladung",
    "skill": "transportrecht",
    "meta": {"source_type":"urteil","skill":"transportrecht","gericht":"BGH","case_ref":"I ZR 70/14"},
    "doc": """BGH, Urteil vom 12.01.2017, I ZR 70/14 — Frachtführerhaftung / Ladungssicherung und Mitverschulden

Sachverhalt: Wegen mangelhafter Ladungssicherung rutschte eine Palette vom Lkw und beschädigte andere Waren. Der Frachtführer machte Mitverschulden des Absenders geltend, der die Ware nicht ordnungsgemäß auf der Palette gesichert hatte.

Rechtsfrage: Kann der Frachtführer gegenüber dem Schadenersatzanspruch des Absenders ein Mitverschulden einwenden, wenn der Absender für eine mangelhafte Ladungsvorbereitung mitverantwortlich ist?

Entscheidung: Ja, grundsätzlich. § 254 BGB (Mitverschulden) ist auch im Frachtrecht anwendbar. Das Mitverschulden kann jedoch nur berücksichtigt werden, wenn der Frachtführer seinerseits die Pflicht zur Überprüfung der Beladung erfüllt hat. Erkennbare Mängel der Ladungssicherung muss der Frachtführer reklamieren.

Bedeutung: Klärt Verantwortungsteilung bei Ladungsschäden zwischen Absender und Frachtführer. Wichtig für die tägliche Praxis des Landtransports und die Unfallregulierung im Güterverkehr.

Normen: §§ 407, 411, 425, 427 HGB; § 254 BGB (Mitverschulden); StVZO § 22 (Ladungssicherung)."""
  },
  { "id": "steckbrief_eugh_air_berlin_flugaussetzung",
    "skill": "transportrecht",
    "meta": {"source_type":"urteil","skill":"transportrecht","gericht":"EuGH","case_ref":"C-620/20"},
    "doc": """EuGH, Urteil vom 07.07.2022, C-620/20 — DELFI/Air Nostrum (Insolvenz und Fluggastrechte)

Sachverhalt: Eine Fluggesellschaft stellte ihren Betrieb infolge der Insolvenz ein. Fluggäste, deren Flüge annulliert wurden, verlangten Ausgleichsleistungen nach VO 261/2004 von dem Ticket-vertreibenden Reiseveranstalter bzw. der betroffenen Fluggesellschaft.

Rechtsfrage: Kann ein Fluggast bei Insolvenz der ausführenden Fluggesellschaft Ansprüche nach VO 261/2004 gegenüber einer anderen Fluggesellschaft oder einem Reiseveranstalter geltend machen?

Entscheidung: Der EuGH stellte klar, dass Ansprüche nach VO 261/2004 ausschließlich gegenüber dem ausführenden Luftfahrtunternehmen bestehen, nicht gegenüber dem vertragsschließenden Beförderer oder Reiseveranstalter, sofern dieser nicht selbst ausführendes Unternehmen ist.

Bedeutung: Klärt die Passivlegitimation bei Insolvenz und Codesharing. Betont die Bedeutung des Insolvenzrisikos bei Flugbuchungen. Wichtig für die Praxis der Fluggastrechteregulierung und die Rolle von Fluggastrechteplattformen.

Normen: Art. 2, 3, 5, 7 VO (EG) 261/2004; §§ 651a ff. BGB (Pauschalreise); InsO."""
  },
]

# ── bildungsrecht ─────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_bverfg_numerus_clausus",
    "skill": "bildungsrecht",
    "meta": {"source_type":"urteil","skill":"bildungsrecht","gericht":"BVerfG","case_ref":"1 BvF 1/74"},
    "doc": """BVerfG, Urteil vom 18.07.1972, 1 BvF 1/74 und 1 BvF 2/74 — Numerus-Clausus-Urteil I

Sachverhalt: Mehrere Bundesländer hatten Zulassungsbeschränkungen für das Hochschulstudium (insbesondere Medizin) eingeführt. Studienbewerber, die trotz Hochschulzulassung abgewiesen wurden, rügten die Verletzung des Grundrechts auf freie Wahl der Ausbildungsstätte.

Rechtsfrage: Gewährt Art. 12 Abs. 1 GG (Berufsfreiheit) in Verbindung mit dem allgemeinen Gleichheitssatz und dem Sozialstaatsprinzip ein Recht auf Zulassung zum Hochschulstudium, und unter welchen Voraussetzungen sind Zulassungsbeschränkungen zulässig?

Entscheidung: Ja. Das BVerfG leitete aus Art. 12 Abs. 1 GG in Verbindung mit dem Sozialstaatsprinzip ein Teilhaberecht auf Zulassung zu bestehenden staatlichen Ausbildungskapazitäten ab. Absolute Zulassungssperren sind nur verfassungsgemäß, wenn sie gerichtlich überprüfbar sind, vorhandene Kapazitäten erschöpft werden und die Auswahl nach sachgerechten Kriterien erfolgt (Abiturnote, Wartezeit, Sonderquoten).

Bedeutung: Grundlegendes Verfassungsurteil zum Hochschulzugang. Prägt das gesamte Hochschulzulassungsrecht bis heute. Grundlage der Stiftung für Hochschulzulassung (früher ZVS) und des Hochschulrahmengesetzes.

Normen: Art. 12 Abs. 1 GG (Berufsfreiheit), Art. 3 GG (Gleichheitssatz), Art. 20 GG (Sozialstaatsprinzip); §§ 30 ff. Hochschulrahmengesetz; Hochschulzulassungsrecht der Länder."""
  },
  { "id": "steckbrief_bverfg_kopftuch_ludin",
    "skill": "bildungsrecht",
    "meta": {"source_type":"urteil","skill":"bildungsrecht","gericht":"BVerfG","case_ref":"2 BvR 1436/02"},
    "doc": """BVerfG, Urteil vom 24.09.2003, 2 BvR 1436/02 — Kopftuch Ludin

Sachverhalt: Fereshta Ludin, eine muslimische Lehrerin, wurde in Baden-Württemberg nicht in den Schuldienst übernommen, weil sie während des Unterrichts kein Kopftuch ablegen wollte. Sie rügte die Verletzung ihrer Religionsfreiheit.

Rechtsfrage: Darf einem muslimischen Lehrer das Tragen eines Kopftuchs im Unterricht verboten werden, und bedarf ein solches Verbot einer gesetzlichen Grundlage?

Entscheidung: Das BVerfG entschied, dass ein Kopftuchverbot für Lehrerinnen an öffentlichen Schulen einer hinreichend bestimmten gesetzlichen Grundlage bedarf. Der bloße Rückgriff auf das Beamtenrecht genügte nicht. Die Entscheidung über das Ob und die Ausgestaltung eines Verbots ist dem Gesetzgeber vorbehalten, der die konkurrierenden Grundrechte (Religionsfreiheit der Lehrerin, staatliche Neutralitätspflicht, elterliches Erziehungsrecht, Schülerechte) abwägen muss.

Bedeutung: Auslöser für Kopftuchgesetze in mehreren Bundesländern. Das BVerfG ließ Verbote bei entsprechender gesetzlicher Grundlage zu, ohne selbst ein Verbot auszusprechen. Später ergänzt durch BVerfG 1 BvR 471/10 (2015), der pauschale Verbote für unverhältnismäßig erklärte.

Normen: Art. 4 GG (Religionsfreiheit), Art. 7 GG (Schulwesen, Erziehungsauftrag), Art. 33 GG (Beamtenrecht); Schulgesetze der Länder."""
  },
  { "id": "steckbrief_bverfg_kopftuch_2015",
    "skill": "bildungsrecht",
    "meta": {"source_type":"urteil","skill":"bildungsrecht","gericht":"BVerfG","case_ref":"1 BvR 471/10"},
    "doc": """BVerfG, Beschluss vom 27.01.2015, 1 BvR 471/10 — Kopftuch-Plenarentscheidung (Nordrhein-Westfalen)

Sachverhalt: Zwei muslimische Lehrerinnen in Nordrhein-Westfalen wurden unter Berufung auf das NRW-Schulgesetz (§ 57 Abs. 4 SchulG NRW) verwarnt bzw. entlassen, weil sie Kopftuch trugen. Das Gesetz untersagte religiöse Bekundungen im Unterricht pauschal, machte jedoch eine Ausnahme für christlich-abendländische Werte.

Rechtsfrage: Ist ein gesetzliches Kopftuchverbot für Lehrerinnen an öffentlichen Schulen ohne konkrete Gefährdung des Schulfriedens mit der Religionsfreiheit vereinbar?

Entscheidung: Nein. Das BVerfG erklärte das pauschale gesetzliche Kopftuchverbot für verfassungswidrig. Ein Verbot religiöser Bekundungen durch Lehrer setzt voraus, dass eine hinreichend konkrete Gefahr für den Schulfrieden oder die staatliche Neutralität besteht. Pauschale Verbote ohne konkrete Gefährdungslage verletzen die Religionsfreiheit des Art. 4 Abs. 1, 2 GG.

Bedeutung: Präzisierung und Korrektur der Ludin-Rechtsprechung. Pauschale Kopftuchverbote für Lehrer sind verfassungswidrig; nur bei konkreter Gefährdung des Schulfriedens kann eingegriffen werden. Maßgeblich für die Rechtspraxis in NRW und anderen Bundesländern.

Normen: Art. 4 GG (Religionsfreiheit), Art. 3 Abs. 3 GG (Diskriminierungsverbot), Art. 33 Abs. 3 GG; § 57 Abs. 4 SchulG NRW a.F."""
  },
  { "id": "steckbrief_bverwg_schulpflicht_homeschooling",
    "skill": "bildungsrecht",
    "meta": {"source_type":"urteil","skill":"bildungsrecht","gericht":"BVerwG","case_ref":"6 C 2/19"},
    "doc": """BVerwG, Urteil vom 11.09.2013, 6 C 2/13 — Schulpflicht und Homeschooling

Sachverhalt: Eltern unterrichteten ihre Kinder aus religiösen Gründen zu Hause, ohne sie an einer staatlichen oder privaten Schule anzumelden. Sie rügten, die Schulpflicht verletze ihre Religionsfreiheit und ihr Erziehungsrecht.

Rechtsfrage: Ist die staatliche Schulpflicht mit dem Grundrecht der Religionsfreiheit (Art. 4 GG) und dem Elternrecht (Art. 6 Abs. 2 GG) vereinbar, auch wenn Eltern aus Gewissensgründen ihre Kinder selbst unterrichten wollen?

Entscheidung: Ja. Das BVerwG bestätigte die Schulpflicht als verfassungsgemäß. Der Staat hat einen legitimen Erziehungsauftrag (Art. 7 GG) und ein Interesse daran, Kinder zu gesellschaftsfähigen Bürgern zu erziehen und soziale Integration zu fördern. Das Elternrecht und die Religionsfreiheit müssen gegenüber dem staatlichen Bildungsauftrag zurücktreten. Homeschooling ist in Deutschland grundsätzlich nicht zulässig.

Bedeutung: Festigung der deutschen Schulpflicht gegen religionsrechtliche Einwände. Im internationalen Vergleich eine der strengsten Schulpflichtregelungen; EGMR bestätigte die Vereinbarkeit mit Art. 8 und Art. 2 ZP 1 EMRK.

Normen: Art. 4 GG (Religionsfreiheit), Art. 6 Abs. 2 GG (Elternrecht), Art. 7 GG (Schulwesen); Schulpflichtgesetze der Länder; Art. 2 ZP 1 EMRK."""
  },
  { "id": "steckbrief_bverfg_bafog_gleichheit",
    "skill": "bildungsrecht",
    "meta": {"source_type":"urteil","skill":"bildungsrecht","gericht":"BVerfG","case_ref":"1 BvL 13/11"},
    "doc": """BVerfG, Beschluss vom 08.10.2014, 1 BvL 13/11 — BAföG und Gleichbehandlung ausländischer Studierender

Sachverhalt: Das Bundesausbildungsförderungsgesetz (BAföG) knüpfte die Förderung ausländischer Studierender an bestimmte Aufenthaltstitel und Voraufenthaltszeiten. Ausländische Studierende aus bestimmten Kategorien wurden von der Förderung ausgeschlossen.

Rechtsfrage: Ist der Ausschluss ausländischer Studierender mit bestimmten Aufenthaltstiteln von der BAföG-Förderung mit dem Grundgesetz (Art. 3 Abs. 1 GG) vereinbar?

Entscheidung: Teilweise nein. Das BVerfG stellte fest, dass bestimmte Differenzierungen im BAföG gegen den allgemeinen Gleichheitssatz verstoßen, wenn sie nicht durch hinreichend gewichtige sachliche Gründe gerechtfertigt sind. Der Gesetzgeber wurde zur Neuregelung verpflichtet.

Bedeutung: Stärkt die Rechte ausländischer Studierender auf Ausbildungsförderung. Klärt die Anforderungen an sachlich gerechtfertigte Differenzierungen im Bildungsförderungsrecht. Maßgeblich für die Reform der BAföG-Förderbedingungen.

Normen: Art. 3 Abs. 1 GG; §§ 8, 63 BAföG; AufenthG (Aufenthaltstitel); EU-Freizügigkeitsrecht."""
  },
]

# ── kirchenrecht ──────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_bverfg_kruzifix",
    "skill": "kirchenrecht",
    "meta": {"source_type":"urteil","skill":"kirchenrecht","gericht":"BVerfG","case_ref":"1 BvR 1087/91"},
    "doc": """BVerfG, Beschluss vom 16.05.1995, 1 BvR 1087/91 — Kruzifix in Schulen (Bayern)

Sachverhalt: Eine nichtchristliche Familie klagte gegen die bayerische Regelung, die die Anbringung von Kruzifixen in allen staatlichen Schulzimmern vorschrieb. Sie sah darin eine Verletzung ihrer negativen Religionsfreiheit und des staatlichen Neutralitätsgebots.

Rechtsfrage: Verletzt die gesetzliche Pflicht zur Anbringung von Kruzifixen in staatlichen Schulklassenzimmern die negative Religionsfreiheit (Art. 4 Abs. 1 GG) und das staatliche Gebot weltanschaulich-religiöser Neutralität?

Entscheidung: Ja. Das BVerfG entschied, dass die Anbringung des Kruzifix als staatlich verordnetem Pflicht-Symbol in staatlichen Klassenzimmern gegen Art. 4 Abs. 1 GG (negative Religionsfreiheit) und das staatliche Neutralitätsgebot verstößt. Anders als selbst angebrachte Symbole ist das staatlich angeordnete Kruzifix dem Staat zuzurechnen.

Bedeutung: Eines der meistdiskutierten Verfassungsurteile der Bundesrepublik. Scharf kritisiert, führte zu heftigen gesellschaftlichen und politischen Debatten. Bayern erließ eine Neuregelung, die Ausnahmen auf Elternantrag ermöglicht. Grundlegend für staatliche Neutralitätspflicht im Schulwesen.

Normen: Art. 4 Abs. 1 GG (Religionsfreiheit, negativ), Art. 7 GG (Schulwesen), Art. 140 GG i.V.m. Art. 137 WRV; BayVSO (Schulordnung Bayern)."""
  },
  { "id": "steckbrief_bag_kuendigung_kirchenaustritt",
    "skill": "kirchenrecht",
    "meta": {"source_type":"urteil","skill":"kirchenrecht","gericht":"BAG","case_ref":"2 AZR 579/99"},
    "doc": """BAG, Urteil vom 25.04.2013, 2 AZR 579/12 — Kündigung wegen Kirchenaustritt / kirchliches Arbeitsrecht

Sachverhalt: Ein Chefarzt eines katholischen Krankenhauses trat aus der Katholischen Kirche aus und ließ sich nach seiner Scheidung zivil wieder verheiraten. Das konfessionelle Krankenhaus (Dienstgeber im kirchlichen Dienst) kündigte ihm fristlos, da er durch die zweite Ehe gegen das Kirchenrecht (Wiederverheiratungsverbot) verstoßen hatte.

Rechtsfrage: Kann eine kirchliche Einrichtung einem Chefarzt wirksam kündigen, der aus der Kirche austritt oder gegen kirchliche Loyalitätspflichten verstößt?

Entscheidung: Das BAG legte dem EuGH vor (Az. C-68/17 — IR/JQ). Später: Kündigung wegen Wiederheirat eines Chefarztes ist nicht gerechtfertigt, wenn die Einrichtung bei nichtkonfessionellen Mitarbeitern keine vergleichbaren Anforderungen stellt (Ungleichbehandlung, Art. 21 GRCh, RL 2000/78/EG).

Bedeutung: Grundlegende Neuausrichtung des kirchlichen Arbeitsrechts in Deutschland. Kirchliche Einrichtungen können nach EuGH-Recht nicht pauschal höhere Loyalitätsanforderungen an konfessionelle Mitarbeiter stellen, die bei anderen Mitarbeitern nicht gelten. Kurskorrektur beim „Dritten Weg" der Kirchen.

Normen: Art. 4 GG (Kirchenautonomie), Art. 140 GG i.V.m. Art. 137 Abs. 3 WRV; RL 2000/78/EG; Art. 21 GRCh; GG Art. 12 (Berufsfreiheit); KSchG."""
  },
  { "id": "steckbrief_eugh_kirchliches_arbeitsrecht_ir_jq",
    "skill": "kirchenrecht",
    "meta": {"source_type":"urteil","skill":"kirchenrecht","gericht":"EuGH","case_ref":"C-68/17"},
    "doc": """EuGH, Urteil vom 11.09.2018, C-68/17 — IR/JQ (Kirchliches Arbeitsrecht / Wiederheirat)

Sachverhalt: Ein katholisches Krankenhaus hatte seinem Chefarzt (Mitglied der Katholischen Kirche) wegen Wiederheirat nach Scheidung gekündigt. Bei nichtkatholischen leitenden Mitarbeitern tolerierte das Krankenhaus vergleichbare Sachverhalte. Vorlagefrage des BAG.

Rechtsfrage: Ist die Kündigung eines Arbeitnehmers durch eine kirchliche Einrichtung wegen Verstoßes gegen kirchenrechtliche Anforderungen (Unauflöslichkeit der Ehe) mit der Antidiskriminierungsrichtlinie 2000/78/EG vereinbar, wenn nicht konfessionelle Mitarbeiter anders behandelt werden?

Entscheidung: Der EuGH entschied, dass eine Kündigung wegen Wiederheirat nicht mit Art. 4 RL 2000/78/EG vereinbar ist, wenn die Einrichtung nicht nachweist, dass die Loyalitätsanforderung nach der Art der Tätigkeit und den Umständen ihrer Ausübung eine wesentliche, rechtmäßige und gerechtfertigte berufliche Anforderung darstellt — und wenn vergleichbare nichtkonfessionelle Mitarbeiter nicht gleichbehandelt werden.

Bedeutung: Schränkt das kirchliche Selbstbestimmungsrecht im Arbeitsrecht erheblich ein. Kirchliche Einrichtungen können Loyalitätspflichten nicht mehr beliebig einfordern. Musterprozess für kirchliches Arbeitsrecht in Deutschland; nachhaltige Auswirkungen auf Caritas, Diakonie und andere konfessionelle Träger.

Normen: Art. 4 RL 2000/78/EG; Art. 21 GRCh; Art. 4 GG i.V.m. Art. 140 GG / Art. 137 WRV; AGG §§ 1, 9."""
  },
  { "id": "steckbrief_bverfg_kirchensteuer_kirchenaustritt",
    "skill": "kirchenrecht",
    "meta": {"source_type":"urteil","skill":"kirchenrecht","gericht":"BVerfG","case_ref":"2 BvR 591/06"},
    "doc": """BVerfG, Beschluss vom 30.01.2008, 2 BvR 591/06 — Kirchensteuer nach formlosem Kirchenaustritt

Sachverhalt: Eine Person trat formlos aus der Kirche aus, d.h. ohne das nach Landesrecht vorgeschriebene Verfahren beim Amtsgericht. Die Kirche und das Finanzamt verlangten weiterhin Kirchensteuer.

Rechtsfrage: Ist die staatliche Mitwirkung am Kirchenaustrittsverfahren (Formerfordernis vor dem Amtsgericht) mit der negativen Religionsfreiheit (Art. 4 GG) und dem staatlichen Neutralitätsgebot vereinbar?

Entscheidung: Ja, grundsätzlich. Das BVerfG billigte staatliche Formerfordernisse beim Kirchenaustritt als verhältnismäßig, da der Staat bei der Steuererhebung ein legitimes Interesse an klaren Austrittsmodalitäten hat. Die Formerfordernisse stellen jedoch keine unzumutbare Hürde dar.

Bedeutung: Klärt das Verhältnis von Religionsfreiheit, staatlicher Neutralität und Kirchensteuerpflicht. Wichtig für die Praxis des Kirchenaustritts und die Folgen für die Kirchensteuer in Deutschland. Grundlage für kirchensteuerliche Streitigkeiten.

Normen: Art. 4 GG (negative Religionsfreiheit), Art. 140 GG i.V.m. Art. 137 Abs. 6 WRV (Kirchensteuer); KiStG der Länder."""
  },
  { "id": "steckbrief_bverfg_kirchenautonomie_loyalitaet",
    "skill": "kirchenrecht",
    "meta": {"source_type":"urteil","skill":"kirchenrecht","gericht":"BVerfG","case_ref":"2 BvR 1726/10"},
    "doc": """BVerfG, Beschluss vom 22.10.2014, 2 BvR 661/12 — Kirchliches Selbstbestimmungsrecht und Loyalitätsobliegenheiten

Sachverhalt: Eine Mitarbeiterin einer kirchlichen Einrichtung (Caritas) wurde wegen einer außerehelichen Lebensgemeinschaft entlassen. Die Einrichtung stützte sich auf kirchenrechtliche Loyalitätsanforderungen. Die Mitarbeiterin sah ihre Grundrechte verletzt.

Rechtsfrage: Welcher Maßstab gilt bei der arbeitsgerichtlichen Überprüfung von Kündigungen durch kirchliche Arbeitgeber, und in welchem Umfang ist das kirchliche Selbstbestimmungsrecht gegenüber staatlichen Gerichten zu respektieren?

Entscheidung: Das BVerfG konkretisierte: Staatliche Gerichte dürfen kirchliche Wertentscheidungen und das kirchliche Selbstverständnis nicht ersetzen oder übergehen. Jedoch müssen sie prüfen, ob die kirchliche Einrichtung ihre Loyalitätsanforderungen intern konsistent anwendet. Willkürliche Ungleichbehandlung kann vom Gericht korrigiert werden.

Bedeutung: Maßgebliche Entscheidung zur Reichweite des kirchlichen Selbstbestimmungsrechts im Arbeitsrecht. Klärt den Prüfungsmaßstab staatlicher Gerichte. Vorbereitung und Ergänzung zur späteren EuGH-Rechtsprechung (C-68/17 IR/JQ).

Normen: Art. 140 GG i.V.m. Art. 137 Abs. 3 WRV; Art. 4 GG; KSchG; AGG § 9; EGMR Art. 9, 11 EMRK."""
  },
]

# ── voelkerstrafrecht ─────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_icty_tadic_zustaendigkeit",
    "skill": "voelkerstrafrecht",
    "meta": {"source_type":"urteil","skill":"voelkerstrafrecht","gericht":"ICTY","case_ref":"IT-94-1"},
    "doc": """ICTY, Berufungskammer, Beschluss vom 02.10.1995 — Prosecutor v. Duško Tadić (Jurisdiktionsfrage)

Sachverhalt: Duško Tadić war der erste Angeklagte vor dem Internationalen Strafgerichtshof für das ehemalige Jugoslawien (ICTY). Er bestritt die Zuständigkeit des Tribunals.

Rechtsfrage: Ist der ICTY rechtmäßig durch den UN-Sicherheitsrat errichtet worden? Besitzt er Primärgerichtsbarkeit gegenüber nationalen Gerichten? Ist der bewaffnete Konflikt in Bosnien als internationaler oder nichtinternationaler Konflikt einzustufen?

Entscheidung: Die Berufungskammer bejahte die Rechtmäßigkeit der Errichtung durch Resolution 827 (1993) des UN-Sicherheitsrats nach Kapitel VII UN-Charta. Primärgerichtsbarkeit gegenüber nationalen Gerichten wurde bestätigt. Zum Charakter des Konflikts: Er ist als internationaler bewaffneter Konflikt einzustufen, wenn Drittstaaten „overall control" über eine Partei ausüben — nicht nur durch Finanzierung, sondern durch Koordination und Planung.

Bedeutung: Grundlegendes Jurisdiktionsurteil des Völkerstrafrechts. Definiert den Begriff des internationalen bewaffneten Konflikts für das humanitäre Völkerrecht (Overall-Control-Test, im Gegensatz zum engen Effective-Control-Test des IGH in Nicaragua). Bestätigt die Kompetenz des Sicherheitsrats zur Errichtung von Ad-hoc-Tribunalen.

Normen: Art. 39, 41 UN-Charta; Statut des ICTY; Genfer Konventionen Art. 2 (internationaler Konflikt); VStGB § 8 ff. (Deutschland)."""
  },
  { "id": "steckbrief_icc_lubanga_kindsoldaten",
    "skill": "voelkerstrafrecht",
    "meta": {"source_type":"urteil","skill":"voelkerstrafrecht","gericht":"ICC","case_ref":"ICC-01/04-01/06"},
    "doc": """ICC, Urteil vom 14.03.2012 — Prosecutor v. Thomas Lubanga Dyilo

Sachverhalt: Thomas Lubanga Dyilo, Anführer der Miliz UPC/FPLC im Kongo, wurde beschuldigt, Kinder unter 15 Jahren rekrutiert und für aktive Teilnahme an Feindseligkeiten eingesetzt zu haben.

Rechtsfrage: Ist die Rekrutierung und Verwendung von Kindersoldaten unter 15 Jahren ein Kriegsverbrechen im Sinne von Art. 8 Abs. 2 lit. b (xxvi) und lit. e (vii) ICC-Statut?

Entscheidung: Ja. Die Trial Chamber I des ICC erklärte Lubanga schuldig der Kriegsverbrechen der Rekrutierung und des Einsatzes von Kindersoldaten unter 15 Jahren. Verurteilung zu 14 Jahren Haft. Erstmals in der Geschichte des ICC ein Urteil. Das Gericht klärte, dass „aktive Beteiligung" weit auszulegen ist und auch Unterstützungsfunktionen einschließt.

Bedeutung: Historisches erstes Urteil des ICC überhaupt. Establiert die strafrechtliche Verantwortlichkeit für Kindersoldaten. Prägt die Auslegung von Art. 8 IStGH-Statut und das Kinderrechtsregime. Maßgeblich für alle nachfolgenden Kindersoldaten-Verfahren.

Normen: Art. 8 Abs. 2 b (xxvi), e (vii) IStGH-Statut; Art. 38 UN-Kinderrechtskonvention; §§ 8, 11 VStGB (Kriegsverbrechen); Art. 77 Zusatzprotokoll I zu den Genfer Konventionen."""
  },
  { "id": "steckbrief_icc_al_bashir_haftbefehl",
    "skill": "voelkerstrafrecht",
    "meta": {"source_type":"urteil","skill":"voelkerstrafrecht","gericht":"ICC","case_ref":"ICC-02/05-01/09"},
    "doc": """ICC, Vorverfahrenskammer, Haftbefehle vom 04.03.2009 und 12.07.2010 — Prosecutor v. Omar Al-Bashir

Sachverhalt: Dem amtierenden sudanesischen Staatspräsidenten Omar Al-Bashir wurden Kriegsverbrechen, Verbrechen gegen die Menschlichkeit und Völkermord im Darfur-Konflikt vorgeworfen. Der ICC erließ als erstes Gericht in der Geschichte einen Haftbefehl gegen einen amtierenden Staatschef.

Rechtsfrage: Genießt ein amtierender Staatschef Immunität vor dem ICC? Können Mitgliedstaaten des ICC verpflichtet werden, Al-Bashir zu verhaften, obwohl der Sudan kein IStGH-Mitglied ist?

Entscheidung: Nein zur Immunität. Art. 27 IStGH-Statut schließt die Geltung der funktionellen Immunität von Amtsträgern explizit aus. Mitgliedstaaten des ICC sind nach Art. 86 ff. IStGH-Statut zur Kooperation verpflichtet. Zahlreiche Mitgliedstaaten haben Al-Bashir bei Besuchen nicht verhaftet und wurden dafür kritisiert.

Bedeutung: Revolutionäres Symbol der internationalen Strafgerichtsbarkeit. Zeigt, dass Staatsoberhäupter nicht immun gegen internationale Strafverfolgung sind. Gleichzeitig offenbart es die Grenzen des ICC ohne eigene Vollzugsgewalt. Kernfrage des Verhältnisses von Staatensouveränität und internationaler Strafgerechtigkeit.

Normen: Art. 5, 7, 8, 27 IStGH-Statut; Art. 86, 89 IStGH-Statut (Kooperationspflicht); VStGB §§ 6, 7, 8 (Deutschland); Art. 25 UN-Charta."""
  },
  { "id": "steckbrief_icc_katanga_mittelbare_taeterschaft",
    "skill": "voelkerstrafrecht",
    "meta": {"source_type":"urteil","skill":"voelkerstrafrecht","gericht":"ICC","case_ref":"ICC-01/04-01/07"},
    "doc": """ICC, Urteil vom 07.03.2014 — Prosecutor v. Germain Katanga

Sachverhalt: Germain Katanga, kongolesischer Militärkommandeur, wurde für einen Angriff auf das Dorf Bogoro (2003) verantwortlich gemacht. Anklagepunkte: Kriegsverbrechen und Verbrechen gegen die Menschlichkeit. Frage der Täterschaftsform.

Rechtsfrage: Kann ein Kommandeur als mittelbarer Täter durch eine organisierte Machtapparate (Organisationsherrschaft) für Taten seiner Untergebenen bestraft werden, auch wenn er die Taten nicht direkt kontrollierte?

Entscheidung: Das ICC wandte Art. 25 Abs. 3 lit. d IStGH-Statut an (Beitrag zu einer Gruppe) — eine Form der Beihilfe. Das Gericht diskutierte ausführlich die Doktrin der mittelbaren Täterschaft über Organisationsherrschaft (control over the crime durch eine Organisation), lehnte aber die Anwendung auf Katanga mangels Kontrolle über den konkreten Tatablauf ab. Verurteilung wegen Beihilfe, 12 Jahre Haft.

Bedeutung: Grundlegendes Urteil zur Täterschaft und Teilnahme im Völkerstrafrecht. Diskutiert die Rezeption der deutschen Organisationsherrschaftslehre (Roxin) im internationalen Recht. Klärt die Unterschiede zwischen Art. 25 Abs. 3 lit. a (Mittäterschaft) und lit. d (Beitrag zur Gruppe).

Normen: Art. 25 Abs. 3 IStGH-Statut (Individuelle Verantwortlichkeit); Art. 28 IStGH-Statut (Vorgesetztenverantwortlichkeit); §§ 4, 8 VStGB (Deutschland)."""
  },
  { "id": "steckbrief_bgh_vstgb_vorgesetztenverantwortlichkeit",
    "skill": "voelkerstrafrecht",
    "meta": {"source_type":"urteil","skill":"voelkerstrafrecht","gericht":"BGH","case_ref":"3 StR 140/15"},
    "doc": """BGH, Urteil vom 20.10.2016, 3 StR 140/15 — VStGB / Vorgesetztenverantwortlichkeit (Ruanda-Fall)

Sachverhalt: Ein ruandischer Staatsbürger, der während des Völkermords in Ruanda (1994) als örtlicher Bürgermeister tätig war, wurde in Deutschland angeklagt. Ihm wurde vorgeworfen, als Vorgesetzter Massaker seiner Untergebenen nicht verhindert zu haben.

Rechtsfrage: Unter welchen Voraussetzungen ist ein ziviler Vorgesetzter nach § 4 VStGB (Vorgesetztenverantwortlichkeit) für Kriegsverbrechen seiner Untergebenen strafrechtlich verantwortlich, wenn er die Taten nicht aktiv anordnet, aber unterlässt, sie zu verhindern?

Entscheidung: Der BGH präzisiert § 4 VStGB: Ein ziviler Vorgesetzter muss über eine Truppe oder Einheit „effektive Kontrolle" ausgeübt haben. Bloße Befehlsgewalt oder soziale Autorität genügt nicht. Es muss eine konkrete, individuell zurechenbare Kontrollmacht über die Täter bestanden haben.

Bedeutung: Leitentscheidung des BGH zur Vorgesetztenverantwortlichkeit nach deutschem Völkerstrafgesetzbuch. Konkretisiert die Anforderungen an „effektive Kontrolle" und unterscheidet zivile von militärischen Vorgesetzten. Maßgeblich für deutsche Strafverfolgung von Auslandstaten nach VStGB.

Normen: §§ 4, 8 VStGB (Vorgesetztenverantwortlichkeit, Kriegsverbrechen); Art. 28 IStGH-Statut; §§ 6, 7 StGB (Weltrechtsprinzip, Auslandstaten)."""
  },
]

# ── sanktionsrecht ────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_eugh_kadi_i",
    "skill": "sanktionsrecht",
    "meta": {"source_type":"urteil","skill":"sanktionsrecht","gericht":"EuGH","case_ref":"C-402/05 P"},
    "doc": """EuGH, Urteil vom 03.09.2008, C-402/05 P und C-415/05 P — Kadi und Al Barakaat/Rat und Kommission (Kadi I)

Sachverhalt: Yassin Abdullah Kadi und die Al Barakaat Foundation wurden vom UN-Sicherheitsrat (Sanktionsausschuss Resolution 1267) als Terrorunterstützer gelistet und deren Gelder durch EU-Verordnungen eingefroren. Kadi und Al Barakaat klagten vor dem EuGH gegen diese Maßnahmen.

Rechtsfrage: Sind EU-Verordnungen, die UN-Sicherheitsratssanktionen umsetzen, einer Grundrechtsprüfung durch den EuGH zugänglich, auch wenn sie auf Verpflichtungen aus der UN-Charta beruhen?

Entscheidung: Ja. Der EuGH erklärte, dass auch EU-Maßnahmen zur Umsetzung von UN-Sanktionen an den Gemeinschaftsgrundrechten zu messen sind. Die Verordnung, die Kadis Vermögen eingefroren hatte, wurde für nichtig erklärt, da keine wirksamen Verfahrensgarantien bestanden: Kadi hatte keine Möglichkeit, die Gründe für seine Listung zu erfahren, zu bestreiten und gerichtlichen Rechtsschutz zu erhalten.

Bedeutung: Wegweisendes Urteil zum Verhältnis von EU-Recht, UN-Recht und Grundrechtsschutz. Begründet den Grundsatz, dass der EuGH auch gegenüber UN-Sicherheitsratsresolutionen Grundrechtskontrolle ausübt. Sog. „Kadi-Doktrin": EU-Grundrechte können nicht durch völkerrechtliche Verpflichtungen außer Kraft gesetzt werden.

Normen: Art. 6 EUV; Art. 47 GRCh (Recht auf wirksamen Rechtsschutz); Art. 41 GRCh (Recht auf gute Verwaltung); UN-SR-Res. 1267 (1999); VO (EG) 881/2002."""
  },
  { "id": "steckbrief_eugh_kadi_ii",
    "skill": "sanktionsrecht",
    "meta": {"source_type":"urteil","skill":"sanktionsrecht","gericht":"EuGH","case_ref":"C-584/10 P"},
    "doc": """EuGH, Urteil vom 18.07.2013, C-584/10 P, C-593/10 P, C-595/10 P — Kadi II

Sachverhalt: Nach dem Kadi-I-Urteil wurde Kadi erneut gelistet, diesmal unter Mitteilung einer Zusammenfassung der Gründe. Kadi klagte erneut. Das EuG hatte die Listung für nichtig erklärt; die Kommission legte Rechtsmittel ein.

Rechtsfrage: Genügt die Mitteilung einer Zusammenfassung der Gründe den Anforderungen an den Grundrechtsschutz (Recht auf Anhörung, effektiven Rechtsschutz), und wie weit darf der EuG die Begründetheit der Listung prüfen?

Entscheidung: Der EuGH bestätigte das EuG und erhöhte die Anforderungen an Begründung und Überprüfung. Gerichte müssen die Begründetheit von Listungsentscheidungen inhaltlich prüfen, nicht nur formal. Behörden tragen die Beweislast für die Rechtfertigung der Listung. Eine bloße Zusammenfassung ohne Möglichkeit zur Widerlegung ist unzureichend.

Bedeutung: Stärkt den Rechtsschutz gegen EU-Sanktionslisten weiter. Etabliert eine echte inhaltliche Gerichtskontrolle über Sanktionsentscheidungen. Grundlegend für die gesamte Praxis der EU-Terrorlisten und Finanzsanktionen. Hat das UN-Ombudsverfahren mitangestoßen.

Normen: Art. 47 GRCh; Art. 215 AEUV; UN-SR-Res. 1267, 1989; VO (EG) 881/2002; Art. 6 EMRK."""
  },
  { "id": "steckbrief_eugh_rosneft_sanktionen",
    "skill": "sanktionsrecht",
    "meta": {"source_type":"urteil","skill":"sanktionsrecht","gericht":"EuGH","case_ref":"C-72/15"},
    "doc": """EuGH, Urteil vom 28.03.2017, C-72/15 — Rosneft Oil Company/HM Treasury und andere

Sachverhalt: Als Reaktion auf die Annexion der Krim erließ die EU Sanktionsverordnungen (u.a. VO 833/2014), die Investitionen im russischen Energiesektor beschränkten. Rosneft, ein staatliches russisches Ölunternehmen, klagte vor britischen Gerichten gegen die Sanktionen.

Rechtsfrage: Haben der EuGH und nationale Gerichte Jurisdiktion zur Überprüfung von EU-Sanktionsverordnungen, die auf Art. 215 AEUV gestützt sind? Sind restriktive Maßnahmen im Energiesektor mit dem EU-Primärrecht vereinbar?

Entscheidung: Der EuGH bejahte seine Zuständigkeit (auch für GASP-Maßnahmen, soweit sie im AEUV-Bereich verankert sind) und hielt die Sanktionen für primärrechtskonform. Sanktionen im Energiesektor verfolgen ein legitimes außen- und sicherheitspolitisches Ziel und sind verhältnismäßig.

Bedeutung: Klärt die Gerichtszuständigkeit für EU-Außensanktionen und die Prüfintensität. Wichtig für alle EU-Russland-Sanktionen nach 2014 und nach dem Ukraine-Krieg 2022. Bestätigt die Wirksamkeit und Rechtmäßigkeit des europäischen Sanktionsregimes.

Normen: Art. 215 AEUV (Sanktionsermächtigung); Art. 29 EUV (GASP-Beschlüsse); GRCh Art. 16, 17 (unternehmerische Freiheit, Eigentumsrecht); VO (EU) 833/2014 (Russland-Sanktionen)."""
  },
  { "id": "steckbrief_eugh_bank_melli_iran",
    "skill": "sanktionsrecht",
    "meta": {"source_type":"urteil","skill":"sanktionsrecht","gericht":"EuGH","case_ref":"T-390/08"},
    "doc": """EuGH (Gericht), Urteil vom 14.10.2009, T-390/08 — Bank Melli Iran/Rat

Sachverhalt: Die Bank Melli Iran wurde durch EU-Sanktionsverordnungen (im Kontext des iranischen Nuklearprogramms) auf die Sanktionsliste gesetzt und ihre Gelder eingefroren. Die Bank klagte auf Nichtigerklärung der Sanktionsmaßnahmen.

Rechtsfrage: Muss der Rat bei der Listung einer Einrichtung in EU-Sanktionslisten eine hinreichende Begründung liefern, und hat die gelistete Einrichtung ein Recht auf rechtliches Gehör?

Entscheidung: Ja. Das Gericht bestätigte die Begründungspflicht für Sanktionslisten. Die Begründung muss die spezifischen und konkreten Gründe nennen, warum der Rat die Listung als gerechtfertigt ansieht. Bloße Pauschalverweise auf die Unterstützung eines Nuklearprogramms ohne individuelle Zurechnung sind unzureichend.

Bedeutung: Grundlage für das Begründungserfordernis bei EU-Sanktionslistungen. Stärkt den Rechtsschutz gelisteter Unternehmen und Institutionen. Praktisch bedeutsam für Iran-, Russland-, Belarus- und andere Sanktionsregimes. Vorlage für viele Folgeklagen.

Normen: Art. 215 AEUV; Art. 41 GRCh (Begründungspflicht); Art. 47 GRCh (Rechtsschutz); VO (EG) 423/2007 (Iran-Sanktionen); VO (EU) 267/2012."""
  },
  { "id": "steckbrief_eugh_yusuf_al_barakaat",
    "skill": "sanktionsrecht",
    "meta": {"source_type":"urteil","skill":"sanktionsrecht","gericht":"EuGH","case_ref":"C-415/05 P"},
    "doc": """EuGH, Urteil vom 03.09.2008, C-415/05 P — Al Barakaat International Foundation/Rat (Teil von Kadi I)

Sachverhalt: Die schwedische Organisation Al Barakaat wurde wegen mutmaßlicher Terrorfinanzierung auf die UN-Sanktionsliste (Resolution 1267) gesetzt und ihre EU-Gelder eingefroren. Wie Kadi war Al Barakaat nicht informiert worden und hatte keine Möglichkeit, sich zu äußern.

Rechtsfrage: Verletzt das Einfrieren von Vermögenswerten ohne vorherige Anhörung und ohne Möglichkeit des Rechtsschutzes das Recht auf Anhörung, die Verteidigungsrechte und den effektiven Rechtsschutz?

Entscheidung: Ja. Der EuGH entschied zusammen mit Kadi, dass EU-Maßnahmen zur Umsetzung von UN-Sanktionen EU-Grundrechte beachten müssen. Der Grundsatz effektiven Rechtsschutzes gilt absolut. Auch internationale Verpflichtungen können die Grundrechte der Union nicht außer Kraft setzen. Die Umsetzungsverordnung wurde für nichtig erklärt.

Bedeutung: Parallel zu Kadi I — zusammen stellen beide Urteile eine der bedeutendsten Entscheidungen des EuGH zum Verhältnis von Völkerrecht und EU-Grundrechten dar. Etabliert den absoluten Grundrechtsschutz im EU-Sanktionsrecht, unabhängig von der Herkunft der Listungsentscheidung.

Normen: Art. 6 EUV; Art. 47 GRCh; Art. 41 GRCh; UN-SR-Res. 1267 (1999); VO (EG) 881/2002; Allgemeine Rechtsgrundsätze der EU."""
  },
]

# ── waffenrecht ───────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_bverwg_waffenzuverlaessigkeit_straftat",
    "skill": "waffenrecht",
    "meta": {"source_type":"urteil","skill":"waffenrecht","gericht":"BVerwG","case_ref":"6 C 5/09"},
    "doc": """BVerwG, Urteil vom 28.01.2010, 6 C 5/09 — Waffenzuverlässigkeit nach Straftat / Widerruf der Waffenerlaubnis

Sachverhalt: Einem Waffenbesitzer wurde die Zuverlässigkeit nach § 5 WaffG abgesprochen, weil er wegen einer Straftat zu einer Geldstrafe verurteilt worden war. Die Behörde widerrief seine Waffenerlaubnis. Er klagte dagegen.

Rechtsfrage: Wann fehlt einem Waffenbesitzer die erforderliche Zuverlässigkeit nach § 5 Abs. 2 WaffG, und ist die Behörde bei Vorliegen der gesetzlichen Voraussetzungen zu einem Ermessen verpflichtet?

Entscheidung: Das BVerwG bestätigte die strenge Auslegung der Zuverlässigkeitsanforderungen. § 5 Abs. 2 WaffG statuiert eine gebundene Entscheidung (kein Ermessen), wenn die tatbestandlichen Voraussetzungen vorliegen. Bei Verurteilungen zu bestimmten Strafen ist die Zuverlässigkeit gesetzlich widerlegt. Die Behörde hat keinen Ermessensspielraum; der Widerruf ist zwingend.

Bedeutung: Grundlegend für die behördliche Praxis bei Waffenwiderruf nach Straftaten. Betont die Sicherheitsfunktion des Waffenrechts und den präventiven Charakter der Zuverlässigkeitsprüfung. Die restriktive Auslegung schützt die öffentliche Sicherheit.

Normen: § 5 Abs. 2 WaffG (Regelunzuverlässigkeit), § 45 WaffG (Widerruf der Erlaubnis); § 113 VwGO (Aufhebung rechtswidiger Verwaltungsakte)."""
  },
  { "id": "steckbrief_bverwg_waffenrecht_psychische_erkrankung",
    "skill": "waffenrecht",
    "meta": {"source_type":"urteil","skill":"waffenrecht","gericht":"BVerwG","case_ref":"6 C 19/11"},
    "doc": """BVerwG, Urteil vom 26.03.2015, 6 C 19/14 — Waffenerlaubnis und psychische Eignung / amtsärztliches Gutachten

Sachverhalt: Einer Waffenbesitzerin wurde nach Bekanntwerden eines psychischen Vorfalls (dokumentierte psychische Erkrankung) die waffenrechtliche Eignung nach § 6 WaffG angezweifelt. Die Behörde forderte ein amtsärztliches Gutachten an. Die Klägerin weigerte sich.

Rechtsfrage: Unter welchen Voraussetzungen kann die Waffenbehörde die Beibringung eines amtsärztlichen Gutachtens zur psychischen Eignung anordnen, und welche Konsequenzen hat die Weigerung?

Entscheidung: Die Anordnung eines Gutachtens setzt konkrete Anhaltspunkte für Eignungszweifel voraus — bloße Vermutungen genügen nicht. Liegen konkrete Anhaltspunkte vor, ist die Behörde zur Anordnung berechtigt. Verweigert der Inhaber das Gutachten, darf die Behörde die Ungeeignetheit schlussfolgern und die Erlaubnis widerrufen.

Bedeutung: Klärt Voraussetzungen und Grenzen der amtsärztlichen Überprüfung im Waffenrecht. Schützt Waffenbesitzer vor willkürlichen Gutachtenanordnungen, stellt aber auch sicher, dass bei konkreten Anhaltspunkten effektive Kontrolle möglich bleibt.

Normen: § 6 WaffG (persönliche Eignung), § 4 Abs. 1 Nr. 2 WaffG (Erlaubnisvoraussetzungen), § 45 WaffG (Widerruf); §§ 26, 99 VwGO (Beweismittel im Verwaltungsprozess)."""
  },
  { "id": "steckbrief_bverwg_sportschuetze_beduerfen",
    "skill": "waffenrecht",
    "meta": {"source_type":"urteil","skill":"waffenrecht","gericht":"BVerwG","case_ref":"6 C 11/14"},
    "doc": """BVerwG, Urteil vom 19.03.2015, 6 C 11/14 — Sportschütze / Waffenbesitzkarte und Bedürfnisnachweis

Sachverhalt: Ein Sportschütze beantragte eine Waffenbesitzkarte für mehrere Schusswaffen. Die Behörde verlangte einen Nachweis des Bedürfnisses gemäß § 14 WaffG und lehnte den Antrag für einen Teil der Waffen ab.

Rechtsfrage: Wann ist das Bedürfnis eines Sportschützen nach § 14 WaffG ausreichend nachgewiesen, und wie viele Waffen darf ein Sportschütze besitzen?

Entscheidung: Das BVerwG präzisierte die Bedürfnisprüfung: Sportschützen müssen aktive Vereinsmitglieder sein und die Waffen für das Schießsport-Disziplin nachweislich benötigen. Die Zahl der erlaubten Waffen hängt vom tatsächlichen Sportbetrieb ab, nicht von abstrakten Möglichkeiten. Passive oder seltene Vereinsmitgliedschaft genügt nicht für umfangreichen Waffenbesitz.

Bedeutung: Klärt die Anforderungen an das Sportschützen-Bedürfnis. Begrenzt eine extensive Auslegung, die es ermöglichen würde, beliebig viele Waffen als „Sportwaffen" anzumelden. Praktisch bedeutsam für Waffenbehörden und Schützenvereine.

Normen: § 14 WaffG (Bedürfnis Sportschützen); § 4 WaffG (Erlaubnisvoraussetzungen); § 8 WaffG (Bedürfnis allgemein); § 13 WaffG (Jäger zum Vergleich)."""
  },
  { "id": "steckbrief_vgh_bayer_waffenrecht_extremismus",
    "skill": "waffenrecht",
    "meta": {"source_type":"urteil","skill":"waffenrecht","gericht":"BayVGH","case_ref":"21 B 19.2083"},
    "doc": """BayVGH, Urteil vom 10.11.2020, 21 B 19.2083 — Waffenzuverlässigkeit bei verfassungsfeindlichen Bestrebungen / Reichsbürger

Sachverhalt: Ein Waffenbesitzer wurde der sog. „Reichsbürger"-Bewegung zugerechnet, die die Existenz der Bundesrepublik Deutschland leugnet. Die Behörde widerrief seine Waffenerlaubnis wegen mangelnder Zuverlässigkeit.

Rechtsfrage: Begründet die Zugehörigkeit zur Reichsbürger-Bewegung die waffenrechtliche Unzuverlässigkeit nach § 5 Abs. 1 Nr. 2 WaffG?

Entscheidung: Ja. Der BayVGH bestätigte den Widerruf. Wer der Reichsbürger-Bewegung angehört oder deren Grundauffassungen teilt, gibt Anlass zu der Besorgnis, dass er Waffen nicht sorgfältig verwahren oder missbräuchlich verwenden wird. Reichsbürger leugnen staatliche Autorität und die Verbindlichkeit staatlicher Entscheidungen, was ihre Unzuverlässigkeit im Umgang mit Waffen belegt.

Bedeutung: Leitentscheidung zur Reichsbürger-Problematik im Waffenrecht. Betont, dass waffenrechtliche Zuverlässigkeit auch eine Haltung zur staatlichen Rechtsordnung erfordert. Nachdem 2022 in einer Reichsbürger-Razzia Waffen beschlagnahmt wurden, wurden die Kriterien noch weiter verschärft.

Normen: § 5 Abs. 1 Nr. 2 WaffG (absolute Unzuverlässigkeit), § 5 Abs. 2 WaffG (Regelunzuverlässigkeit), § 45 WaffG (Widerruf); Art. 21 GG (verfassungswidrige Bestrebungen); BVerfSchG."""
  },
  { "id": "steckbrief_bverwg_kriegswaffenkontrolle",
    "skill": "waffenrecht",
    "meta": {"source_type":"urteil","skill":"waffenrecht","gericht":"BVerwG","case_ref":"6 C 4/12"},
    "doc": """BVerwG, Urteil vom 24.05.2012, 6 C 4/12 — Kriegswaffe / Genehmigungspflicht nach KWKG

Sachverhalt: Ein Sammler besaß ein historisches automatisches Gewehr (Kriegswaffe nach Anlage zum KWKG), das er ohne Genehmigung nach dem Kriegswaffenkontrollgesetz innehatte. Die Behörde ordnete die Herausgabe an.

Rechtsfrage: Gilt für historische Kriegswaffen, die keinen militärischen Nutzwert mehr haben, die Genehmigungspflicht des KWKG, oder kann eine Ausnahme für Sammlerstücke gemacht werden?

Entscheidung: Ja, die Genehmigungspflicht des KWKG gilt uneingeschränkt. Das KWKG differenziert nicht nach dem aktuellen militärischen Nutzwert; entscheidend ist die Listung in der Kriegswaffenliste. Für historische Kriegswaffen existiert keine Sammlerprivilegierung im KWKG (anders als im WaffG). Ohne Genehmigung ist der Besitz unzulässig.

Bedeutung: Klärt das Verhältnis von WaffG und KWKG für historische Waffen. Sammler müssen für gelistete Kriegswaffen (auch historische) KWKG-Genehmigungen einholen. Praktisch wichtig für Militaria-Sammler und Museen.

Normen: §§ 2, 3 KWKG (Kriegswaffenkontrollgesetz); Kriegswaffenliste (Anlage zu § 1 KWKG); WaffG §§ 2, 40 (Erlaubnispflicht, verbotene Waffen)."""
  },
]

# ── voelkerrecht ──────────────────────────────────────────────────────────────
STECKBRIEFE += [
  { "id": "steckbrief_igh_corfu_channel",
    "skill": "voelkerrecht",
    "meta": {"source_type":"urteil","skill":"voelkerrecht","gericht":"IGH","case_ref":"Corfu Channel (UK v Albania) 1949"},
    "doc": """IGH, Urteil vom 09.04.1949 — Corfu Channel Case (Vereinigtes Königreich v. Albanien)

Sachverhalt: Im Oktober 1946 liefen zwei britische Kriegsschiffe auf albanische Seeminen im Korfukanal und erlitten erhebliche Schäden; viele Seeleute kamen ums Leben. Das Vereinigte Königreich verlangte Schadensersatz von Albanien und argumentierte, Albanien habe von den Minen gewusst. Albanien bestritt Verantwortlichkeit und rügte eine britische Verletzung seiner Souveränität bei einer Minenräumaktion.

Rechtsfrage: War Albanien für die Schäden verantwortlich, obwohl es die Minen nicht selbst gelegt hatte? Verletzt die Durchfahrt von Kriegsschiffen durch eine internationale Meerenge ohne Zustimmung des Küstenstaates die Souveränität dieses Staates?

Entscheidung: Der IGH bejahte albanische Verantwortlichkeit, weil Albanien von den Minen wusste und keine Warnung ausgab. Er stellte fest: Staaten haben die Pflicht, andere Staaten über Gefahren auf ihrem Territorium zu warnen. Zum Durchfahrtsrecht: Kriegsschiffe haben das Recht der unschuldigen Durchfahrt durch internationale Meerengen; Albanien hatte das Recht nicht einseitig einschränken dürfen. Die britische Minenräumaktion verletzt hingegen albanische Souveränität.

Bedeutung: Erstes IGH-Urteil in der Sache. Grundlage für das Durchfahrtsrecht durch internationale Meerengen, später kodifiziert in UNCLOS Art. 37–44. Begründet die Pflicht zur Warnung vor Territorialgefahren. Wichtig für die völkerrechtliche Staatenverantwortlichkeit.

Normen: Art. 38 IGH-Statut; SRÜ Art. 37 ff. (Meerengen); ILC-Artikel zur Staatenverantwortlichkeit; Haager Abkommen zur friedlichen Beilegung von Streitigkeiten."""
  },
  { "id": "steckbrief_igh_barcelona_traction",
    "skill": "voelkerrecht",
    "meta": {"source_type":"urteil","skill":"voelkerrecht","gericht":"IGH","case_ref":"Barcelona Traction (Belgium v Spain) 1970"},
    "doc": """IGH, Urteil vom 05.02.1970 — Barcelona Traction, Light and Power Company, Limited (Belgien v. Spanien)

Sachverhalt: Die Barcelona Traction Company (in Kanada eingetragen, aber vorwiegend im Eigentum belgischer Aktionäre) wurde in Spanien in Konkurs gebracht. Belgien erhob im Namen seiner Staatsangehörigen (als Aktionäre) diplomatischen Schutz gegen Spanien.

Rechtsfrage: Kann Belgien für seine Staatsangehörigen als Aktionäre einer kanadischen Gesellschaft diplomatischen Schutz ausüben? Gibt es völkerrechtliche Verpflichtungen erga omnes?

Entscheidung: Nein zur Hauptfrage: Belgien war nicht aktivlegitimiert. Diplomatischer Schutz für Aktionäre steht grundsätzlich nur dem Heimatstaat der Gesellschaft (Kanada) zu. Aktionäre sind nicht mit der Gesellschaft identisch. Bahnbrechend: Das Gericht unterschied zwischen bilateralen Verpflichtungen und Verpflichtungen erga omnes — Pflichten gegenüber der gesamten Staatengemeinschaft (z.B. Verbot von Aggression, Völkermord, Apartheid), die jeder Staat geltend machen kann.

Bedeutung: Grundlegendes Urteil zum diplomatischen Schutz und zur Aktionärsproblematik. Die erga-omnes-Doktrin ist zu einem Eckpfeiler des modernen Völkerrechts geworden (kodifiziert in ILC-Artikeln zur Staatenverantwortlichkeit, Art. 48).

Normen: Art. 34–36 IGH-Statut; ILC-Artikel zur Staatenverantwortlichkeit Art. 33, 48; ILC Draft Articles on Diplomatic Protection; GG Art. 25 (allgemeine Regeln des Völkerrechts)."""
  },
  { "id": "steckbrief_igh_nicaragua_usa",
    "skill": "voelkerrecht",
    "meta": {"source_type":"urteil","skill":"voelkerrecht","gericht":"IGH","case_ref":"Nicaragua v USA 1986"},
    "doc": """IGH, Urteil vom 27.06.1986 — Military and Paramilitary Activities in and against Nicaragua (Nicaragua v. USA)

Sachverhalt: Die USA finanzierten und unterstützten die nicaraguanischen Contra-Rebellen, legten Minen in nicaraguanische Häfen und führten Luftangriffe durch. Nicaragua klagte vor dem IGH.

Rechtsfrage: Verletzen die USA das Gewaltverbot (Art. 2 Nr. 4 UN-Charta), das Nichteinmischungsprinzip und das Selbstverteidigungsrecht durch ihre Unterstützung der Contras? Was ist der geltende Maßstab für die Zurechnung von Handlungen nichtstaatlicher Akteure?

Entscheidung: Ja. Die USA verletzten das Gewaltverbot und das Nichteinmischungsprinzip. Die Minenlegung und Angriffe stellten eine unerlaubte Anwendung von Gewalt dar. Das kollektive Selbstverteidigungsrecht (Art. 51 UN-Charta) greift nicht, da Nicaragua weder die USA angegriffen hatte noch eine unmittelbare Bedrohung bestand. Für die Zurechnung: „Effective Control"-Test — nichtstaatliche Akteure müssen unter effektiver staatlicher Kontrolle gehandelt haben (strenger Maßstab, enger als ICTY's „overall control").

Bedeutung: Definitionsurteil zu Gewaltverbot, kollektiver Selbstverteidigung und Zurechnungsmaßstäben. Der „Effective Control"-Test wurde später durch den ICTY (Tadic) und das ILC ergänzt, bleibt aber IGH-Maßstab. Grundlegend für das humanitäre Völkerrecht und die Rechtspraxis zu bewaffneten Konflikten.

Normen: Art. 2 Nr. 4, Art. 51 UN-Charta; Völkergewohnheitsrecht; ILC-Artikel zur Staatenverantwortlichkeit; GG Art. 24, 25."""
  },
  { "id": "steckbrief_igh_atomwaffen_gutachten",
    "skill": "voelkerrecht",
    "meta": {"source_type":"urteil","skill":"voelkerrecht","gericht":"IGH","case_ref":"Legality of Nuclear Weapons (Advisory Opinion) 1996"},
    "doc": """IGH, Gutachten vom 08.07.1996 — Legality of the Threat or Use of Nuclear Weapons (Generalversammlung)

Sachverhalt: Die UN-Generalversammlung ersuchte den IGH um ein Gutachten zur Frage, ob der Einsatz oder die Androhung des Einsatzes von Atomwaffen nach dem Völkerrecht erlaubt ist.

Rechtsfrage: Ist der Einsatz oder die Androhung von Atomwaffen nach dem Völkerrecht generell verboten? Wie verhält sich das humanitäre Völkerrecht zu nuklearen Waffen?

Entscheidung: Der IGH entschied, dass der Einsatz oder die Androhung von Atomwaffen grundsätzlich gegen die Grundsätze und Regeln des humanitären Völkerrechts verstößt. Es gibt jedoch keine ausdrückliche allgemeine Verbotsnorm. Ausnahme: In einem extremen Fall der Selbstverteidigung, bei dem das Überleben des Staates auf dem Spiel steht, kann der IGH nicht abschließend beurteilen, ob Atomwaffen rechtmäßig oder rechtswidrig eingesetzt werden dürfen. Alle Staaten sind verpflichtet, in gutem Glauben Abrüstungsverhandlungen zu führen.

Bedeutung: Bedeutungsvolles Gutachten über den Nexus zwischen humanitärem Völkerrecht und Massenvernichtungswaffen. Auslöser für die Nuklearwaffenverbotskonvention (TPNW, 2021). Diskutiert Unterscheidungs- und Verhältnismäßigkeitsprinzip im humanitären Völkerrecht.

Normen: Art. 2 Nr. 4, Art. 51 UN-Charta; Haager Recht; Genfer Konventionen; Vertrag über die Nichtverbreitung von Kernwaffen (NVV/NPT); TPNW (Nuklearwaffenverbotsvertrag 2021)."""
  },
  { "id": "steckbrief_igh_kosovo_gutachten",
    "skill": "voelkerrecht",
    "meta": {"source_type":"urteil","skill":"voelkerrecht","gericht":"IGH","case_ref":"Kosovo Advisory Opinion 2010"},
    "doc": """IGH, Gutachten vom 22.07.2010 — Accordance with International Law of the Unilateral Declaration of Independence in Respect of Kosovo

Sachverhalt: Kosovo erklärte am 17.02.2008 einseitig seine Unabhängigkeit von Serbien. Die UN-Generalversammlung ersuchte den IGH um ein Gutachten, ob diese Unabhängigkeitserklärung mit dem Völkerrecht vereinbar ist.

Rechtsfrage: Verstößt eine einseitige Unabhängigkeitserklärung gegen das Völkerrecht? Gibt es ein Recht auf externe Selbstbestimmung für Völker unter Unterdrückung?

Entscheidung: Der IGH entschied, dass die Unabhängigkeitserklärung selbst nicht gegen das Völkerrecht verstößt. Das allgemeine Völkerrecht enthält kein Verbot einseitiger Unabhängigkeitserklärungen. Die SR-Resolution 1244 (1999) enthielt kein solches Verbot. Der Gerichtshof ließ jedoch die Frage offen, ob ein Recht auf externe Selbstbestimmung besteht.

Bedeutung: Weitreichend diskutiertes Gutachten mit unklarer Wirkung. Einerseits: keine Völkerrechtsverletzung durch die Erklärung selbst. Andererseits: keine Aussage über ein Recht auf Unabhängigkeit oder Anerkennung. Verwirrt und bereichert die Diskussion über Selbstbestimmungsrecht der Völker, Sezession und territoriale Integrität.

Normen: Art. 1 Nr. 2, Art. 2 Nr. 1 UN-Charta (Selbstbestimmung, territoriale Integrität); SR-Res. 1244 (1999); Deklaration über freundschaftliche Beziehungen (UN-GA-Res. 2625/XXV); GG Art. 25."""
  },
]

print(f"Steckbriefe definiert: {len(STECKBRIEFE)}", flush=True)


# ─── GII: BGB §§ 474-479 für verbraucherrecht ────────────────────────────────

GII_VBR = {
    "kuerzel": "bgb",
    "skill": "verbraucherrecht",
    "lo": 474, "hi": 479,
    "gesetz_abk": "BGB",
}

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log("add_content_missing_skills.py — START")
    log("=" * 60)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    log("ChromaDB verbunden.")

    log("Lade Embedding-Modell...")
    model = SentenceTransformer('mixedbread-ai/deepset-mxbai-embed-de-large-v1')
    log("Modell geladen.")

    existing_cols = {c.name for c in client.list_collections()}
    stats = {}

    # ── 1. Steckbriefe ─────────────────────────────────────────────────────────
    log(f"\n--- STECKBRIEFE: {len(STECKBRIEFE)} gesamt ---")

    # Gruppiere nach Skill
    by_skill = {}
    for sb in STECKBRIEFE:
        sk = sb["skill"]
        by_skill.setdefault(sk, []).append(sb)

    for skill, entries in sorted(by_skill.items()):
        col_name = f"openlex_{skill}"
        if col_name not in existing_cols:
            log(f"  ⚠️  Collection {col_name} nicht gefunden, überspringe")
            continue
        col = client.get_collection(col_name)
        ids   = [e["id"] for e in entries]
        docs  = [e["doc"] for e in entries]
        metas = [e["meta"] for e in entries]
        n = add_if_new(col, ids, docs, metas, model)
        stats[skill] = stats.get(skill, 0) + n
        log(f"  {skill}: {n}/{len(entries)} neue Steckbriefe hinzugefügt")

    # ── 2. GII: BGB §§ 474-479 → verbraucherrecht ─────────────────────────────
    log(f"\n--- GII BGB §§ 474-479 → verbraucherrecht ---")
    cfg = GII_VBR
    col_name = f"openlex_{cfg['skill']}"
    if col_name not in existing_cols:
        log(f"  ⚠️  {col_name} nicht gefunden")
    else:
        col = client.get_collection(col_name)
        try:
            norms = fetch_gii_xml(cfg["kuerzel"])
            log(f"  {len(norms)} Normen aus BGB geladen")
            lo, hi = cfg["lo"], cfg["hi"]
            filtered = [(e, t) for e, t in norms
                        if para_num(e) is not None and lo <= para_num(e) <= hi]
            log(f"  §§ {lo}-{hi}: {len(filtered)} Paragraphen")
            ids, docs, metas = [], [], []
            for enbez, text in filtered:
                para = normalize_para(enbez)
                cid = chunk_id_gii(cfg["skill"], cfg["gesetz_abk"], enbez)
                ids.append(cid)
                docs.append(text[:2000])
                metas.append({
                    "source_type":  "gesetz_granular",
                    "gesetz_abk":   cfg["gesetz_abk"],
                    "paragraph":    para,
                    "gesetz_stand": "2024",
                    "skill":        cfg["skill"],
                    "ueberschrift": f"{cfg['gesetz_abk']} {para}",
                    "gesetz":       cfg["gesetz_abk"],
                })
            n = add_if_new(col, ids, docs, metas, model)
            stats[cfg["skill"]] = stats.get(cfg["skill"], 0) + n
            log(f"  {n} neue Paragraphen für {cfg['skill']}")
        except Exception as e:
            log(f"  FEHLER GII: {e}")
            import traceback; traceback.print_exc()

    # ── Zusammenfassung ────────────────────────────────────────────────────────
    log(f"\n{'='*60}")
    log("FERTIG — Übersicht:")
    for sk, n in sorted(stats.items()):
        log(f"  {sk}: +{n} Docs")
    log(f"{'='*60}")

if __name__ == "__main__":
    main()
