#!/usr/bin/env python3
"""Schreibt Eval-Fragen für die 10 content-ergänzten Skills."""
import json
from pathlib import Path

EVAL_DIR = Path("/opt/openlex-sources/eval/questions")

QUESTIONS = {

"verbraucherrecht": [
  {"id":1,"skill":"verbraucherrecht","question":"Ein Verkäufer schickt einem Verbraucher ein neues Gerät zur Nachlieferung und verlangt dafür eine Nutzungsentschädigung für das defekte Altgerät. Ist das zulässig?","expected_norms":["§ 474 BGB","§ 475 BGB","§ 439 BGB"],"expected_keywords":["Verbrauchsgüterkauf","Nachlieferung","Nutzungsentschädigung","Quelle"],"category":"Verbrauchsgüterkauf"},
  {"id":2,"skill":"verbraucherrecht","question":"Ein Käufer hat mangelhafte Bodenfliesen verlegt. Beim Austausch verlangt er, dass der Verkäufer auch die Aus- und Einbaukosten trägt. Hat er Recht?","expected_norms":["§ 475 BGB","§ 439 BGB"],"expected_keywords":["Einbaukosten","Ausbaukosten","Nacherfüllung","Weber","Putz"],"category":"Verbrauchsgüterkauf Einbaufall"},
  {"id":3,"skill":"verbraucherrecht","question":"Ein Verbraucher hat an der Haustür einen Kreditvertrag abgeschlossen und wurde nicht über sein Widerrufsrecht belehrt. Kann er noch widerrufen?","expected_norms":["§ 312 BGB","§ 355 BGB","§ 356b BGB"],"expected_keywords":["Haustürgeschäft","Widerrufsrecht","Belehrung","Heininger","ewiges Widerrufsrecht"],"category":"Widerrufsrecht Haustür"},
  {"id":4,"skill":"verbraucherrecht","question":"Ein Online-Shop verwendet vorausgefüllte Checkboxen für Cookie-Einwilligungen. Ist das rechtlich wirksam?","expected_norms":["Art. 6 DSGVO"],"expected_keywords":["Cookie","Einwilligung","Opt-in","Planet49","vorausgefüllt"],"category":"Datenschutz / Einwilligung"},
  {"id":5,"skill":"verbraucherrecht","question":"VW hat in Dieselfahrzeuge Software eingebaut, die Abgaswerte auf dem Prüfstand manipuliert. Welchen Schadensersatzanspruch hat der Käufer gegen VW?","expected_norms":["§ 826 BGB","§ 31 BGB"],"expected_keywords":["sittenwidrig","Schädigungsvorsatz","Abgasskandal","ungewollter Vertrag"],"category":"Delikthaftung § 826 BGB"},
],

"reiserecht": [
  {"id":1,"skill":"reiserecht","question":"Ein Flug hat sich um 4 Stunden verspätet. Hat der Passagier Anspruch auf Ausgleichszahlung nach der Fluggastrechteverordnung?","expected_norms":["Art. 7 VO 261/2004","Art. 5 VO 261/2004"],"expected_keywords":["Verspätung","Ausgleichsleistung","drei Stunden","Sturgeon","Ankunftszeit"],"category":"Fluggastrechte Verspätung"},
  {"id":2,"skill":"reiserecht","question":"Eine Airline annulliert einen Flug wegen eines technischen Defekts am Triebwerk und beruft sich auf einen außergewöhnlichen Umstand. Ist das berechtigt?","expected_norms":["Art. 5 Abs. 3 VO 261/2004"],"expected_keywords":["außergewöhnlicher Umstand","technischer Defekt","Wartung","Wallentin-Hermann"],"category":"Außergewöhnlicher Umstand"},
  {"id":3,"skill":"reiserecht","question":"Wegen des Vulkanausbruchs auf Island war ein Passagier 6 Tage gestrandet. Die Airline verweigerte Unterkunft und Verpflegung. Was steht dem Passagier zu?","expected_norms":["Art. 9 VO 261/2004"],"expected_keywords":["Betreuungsleistungen","Unterkunft","Verpflegung","McDonagh","Vulkanasche"],"category":"Betreuungspflichten höhere Gewalt"},
  {"id":4,"skill":"reiserecht","question":"Ein Reiseveranstalter bucht ein anderes als das vereinbarte Hotel. Was kann der Reisende verlangen?","expected_norms":["§ 651i BGB","§ 651m BGB"],"expected_keywords":["Reisemangel","Minderung","vereinbartes Hotel","Abhilfe"],"category":"Reisemangel Unterkunft"},
  {"id":5,"skill":"reiserecht","question":"Während des Urlaubs verursacht eine Baustelle neben dem Hotel erheblichen Lärm. Der Reiseveranstalter wusste davon. Welche Ansprüche hat der Reisende?","expected_norms":["§ 651i BGB","§ 651n BGB"],"expected_keywords":["Reisemangel","Baulärm","Minderung","Informationspflicht"],"category":"Reisemangel Lärm"},
],

"versicherungsrecht": [
  {"id":1,"skill":"versicherungsrecht","question":"Ein Versicherer berechnet für eine junge Frau eine höhere Kfz-Prämie als für einen gleichaltrigen Mann. Ist das nach EU-Recht zulässig?","expected_norms":["Art. 21 GRCh","Richtlinie 2004/113/EG"],"expected_keywords":["Unisex-Tarife","Geschlecht","Diskriminierung","Test-Achats"],"category":"Gleichbehandlung / Unisex"},
  {"id":2,"skill":"versicherungsrecht","question":"Ein Versicherungsnehmer kündigt seine Lebensversicherung nach 3 Jahren und erhält kaum etwas zurück, weil Abschlusskosten verrechnet wurden. Ist das wirksam?","expected_norms":["§ 169 VVG","§ 307 BGB"],"expected_keywords":["Rückkaufswert","Zillmerung","AGB-Kontrolle","unangemessene Benachteiligung"],"category":"Lebensversicherung Rückkauf"},
  {"id":3,"skill":"versicherungsrecht","question":"Ein BU-Versicherter kann seinen alten Beruf nicht mehr ausüben. Der Versicherer verweist ihn auf einen anderen Beruf. Unter welchen Voraussetzungen ist das zulässig?","expected_norms":["§ 172 VVG"],"expected_keywords":["abstrakte Verweisung","Berufsunfähigkeit","Lebensstellung","Verweisberuf"],"category":"Berufsunfähigkeitsversicherung"},
  {"id":4,"skill":"versicherungsrecht","question":"Bei Vertragsschluss verschweigt ein Versicherungsnehmer arglistig eine Vorerkrankung. Was sind die Folgen?","expected_norms":["§ 22 VVG","§ 123 BGB"],"expected_keywords":["arglistige Täuschung","Anzeigepflichtverletzung","Rücktritt","Leistungsfreiheit"],"category":"Anzeigepflichtverletzung"},
  {"id":5,"skill":"versicherungsrecht","question":"Nach einem Einbruch macht ein Versicherungsnehmer falsche Angaben zum Schadensumfang. Verliert er dadurch den gesamten Anspruch?","expected_norms":["§ 28 VVG"],"expected_keywords":["Obliegenheitsverletzung","Quotelung","grobe Fahrlässigkeit","Aufklärungspflicht"],"category":"Obliegenheitsverletzung"},
],

"transportrecht": [
  {"id":1,"skill":"transportrecht","question":"Ein Frachtführer verliert im internationalen Straßentransport eine Ladung durch grobe Fahrlässigkeit. Gilt noch die CMR-Haftungsbeschränkung?","expected_norms":["Art. 23 CMR","Art. 29 CMR"],"expected_keywords":["CMR","Haftungsbegrenzung","grobe Fahrlässigkeit","leichtfertig","Durchbruch"],"category":"CMR-Haftung"},
  {"id":2,"skill":"transportrecht","question":"Bei einem Flug geht das Gepäck verloren. Der Passagier verlangt auch Ersatz für den immateriellen Schaden. Gilt die Haftungsbegrenzung des Montrealer Übereinkommens?","expected_norms":["Art. 17 MÜ","Art. 22 MÜ"],"expected_keywords":["Montrealer Übereinkommen","Gepäckverlust","Haftungsbegrenzung","immaterieller Schaden","Walz"],"category":"Luftfrachthaftung"},
  {"id":3,"skill":"transportrecht","question":"Ein Spediteur lagert Waren in einem ungeeigneten Lager; sie verbrennen. Die ADSp-Klauseln begrenzen die Haftung. Greift die Beschränkung?","expected_norms":["§ 435 HGB"],"expected_keywords":["ADSp","leichtfertig","Haftungsdurchbruch","Organisationsverschulden","Spediteur"],"category":"Spediteurhaftung ADSp"},
  {"id":4,"skill":"transportrecht","question":"Paletten rutschen vom Lkw, weil der Absender sie schlecht gesichert hat. Der Frachtführer kannte den Mangel. Wer haftet?","expected_norms":["§ 254 BGB","§ 411 HGB"],"expected_keywords":["Ladungssicherung","Mitverschulden","Frachtführer","Absender"],"category":"Ladungssicherung / Mitverschulden"},
  {"id":5,"skill":"transportrecht","question":"Eine Fluggesellschaft ist insolvent; Flüge fallen aus. Kann der Fluggast Ausgleich nach VO 261/2004 vom Reiseveranstalter verlangen?","expected_norms":["Art. 2 VO 261/2004","Art. 3 VO 261/2004"],"expected_keywords":["ausführendes Luftfahrtunternehmen","Insolvenz","Passivlegitimation","Reiseveranstalter"],"category":"Fluggastrechte Insolvenz"},
],

"bildungsrecht": [
  {"id":1,"skill":"bildungsrecht","question":"Ein Studienbewerber wird wegen des NC abgewiesen, obwohl Studienplätze frei wären. Welche Grundrechte sind berührt und was fordert das BVerfG?","expected_norms":["Art. 12 GG","Art. 3 GG"],"expected_keywords":["Numerus Clausus","Teilhaberecht","Kapazität","Zulassungsbeschränkung","Hochschule"],"category":"Hochschulzulassung NC"},
  {"id":2,"skill":"bildungsrecht","question":"Eine muslimische Lehrerin möchte im Unterricht Kopftuch tragen. Der Schulträger verbietet es. Bedarf das Verbot einer gesetzlichen Grundlage?","expected_norms":["Art. 4 GG","Art. 7 GG"],"expected_keywords":["Kopftuch","Religionsfreiheit","Lehrerin","Gesetzesgrundlage","Ludin","Neutralitätspflicht"],"category":"Kopftuch Lehrerin"},
  {"id":3,"skill":"bildungsrecht","question":"Ein pauschales landesrechtliches Kopftuchverbot für Lehrerinnen gilt ohne Nachweis einer konkreten Gefährdung. Ist das verfassungskonform?","expected_norms":["Art. 4 GG","Art. 3 Abs. 3 GG"],"expected_keywords":["pauschales Verbot","konkrete Gefährdung","Verhältnismäßigkeit","Schulfrieden","2015"],"category":"Kopftuch Plenarentscheidung 2015"},
  {"id":4,"skill":"bildungsrecht","question":"Eltern wollen ihre Kinder aus religiösen Gründen zu Hause unterrichten. Gilt die staatliche Schulpflicht trotzdem?","expected_norms":["Art. 7 GG","Art. 6 Abs. 2 GG"],"expected_keywords":["Schulpflicht","Homeschooling","Elternrecht","staatlicher Bildungsauftrag","Integration"],"category":"Schulpflicht Homeschooling"},
  {"id":5,"skill":"bildungsrecht","question":"Ausländische Studierende mit bestimmten Aufenthaltstiteln werden vom BAföG ausgeschlossen. Ist das verfassungsgemäß?","expected_norms":["Art. 3 GG"],"expected_keywords":["BAföG","Gleichheitssatz","Aufenthaltstitel","Ausländer","Differenzierung"],"category":"BAföG Gleichbehandlung"},
],

"kirchenrecht": [
  {"id":1,"skill":"kirchenrecht","question":"Bayern schreibt vor, dass in jedem Schulzimmer ein Kruzifix hängen muss. Ist das mit dem Grundgesetz vereinbar?","expected_norms":["Art. 4 GG","Art. 7 GG"],"expected_keywords":["Kruzifix","negative Religionsfreiheit","Neutralitätspflicht","staatlich angeordnet","BVerfG"],"category":"Kruzifix in Schulen"},
  {"id":2,"skill":"kirchenrecht","question":"Ein Chefarzt eines konfessionellen Krankenhauses heiratet nach Scheidung erneut. Das Krankenhaus kündigt. Ist die Kündigung wirksam?","expected_norms":["Art. 4 GG","Art. 140 GG"],"expected_keywords":["kirchliches Arbeitsrecht","Wiederheirat","Loyalitätspflicht","konfessionell","IR/JQ","EuGH"],"category":"Kirchliches Arbeitsrecht Wiederheirat"},
  {"id":3,"skill":"kirchenrecht","question":"Eine Mitarbeiterin einer Caritas tritt aus der Kirche aus. Darf die Caritas ihr deswegen kündigen?","expected_norms":["Art. 137 WRV","Art. 140 GG"],"expected_keywords":["Kirchenaustritt","kirchliches Selbstbestimmungsrecht","Kündigung","Dritter Weg"],"category":"Kirchenaustritt Kündigung"},
  {"id":4,"skill":"kirchenrecht","question":"Jemand tritt formlos aus der Kirche aus (ohne Amtsgericht). Muss er trotzdem Kirchensteuer zahlen?","expected_norms":["Art. 137 WRV","Art. 140 GG"],"expected_keywords":["Kirchensteuer","Kirchenaustritt","Formerfordernis","Amtsgericht","Verhältnismäßigkeit"],"category":"Kirchensteuer / Austrittsformerfordernis"},
  {"id":5,"skill":"kirchenrecht","question":"Dürfen staatliche Gerichte prüfen, ob eine kirchliche Einrichtung ihre Loyalitätsanforderungen konsistent anwendet?","expected_norms":["Art. 140 GG","Art. 137 Abs. 3 WRV"],"expected_keywords":["Selbstbestimmungsrecht","Konsistenz","Willkür","gerichtliche Kontrolle","Loyalitätsobliegenheit"],"category":"Kirchliches Selbstbestimmungsrecht"},
],

"voelkerstrafrecht": [
  {"id":1,"skill":"voelkerstrafrecht","question":"Ist der ICTY durch den UN-Sicherheitsrat rechtmäßig errichtet worden, und was ist der 'Overall Control'-Test?","expected_norms":["Art. 39 UN-Charta"],"expected_keywords":["ICTY","Sicherheitsrat","Overall Control","internationaler Konflikt","Tadic","Jurisdiktion"],"category":"ICTY Jurisdiktion / Overall Control"},
  {"id":2,"skill":"voelkerstrafrecht","question":"Welches war das erste Urteil des Internationalen Strafgerichtshofs, und worum ging es?","expected_norms":["Art. 8 IStGH-Statut"],"expected_keywords":["ICC","Lubanga","Kindersoldaten","Kriegsverbrechen","erste Verurteilung"],"category":"ICC Lubanga / Kindersoldaten"},
  {"id":3,"skill":"voelkerstrafrecht","question":"Kann der ICC einen amtierenden Staatspräsidenten verhaften lassen, und genießt dieser Immunität?","expected_norms":["Art. 27 IStGH-Statut"],"expected_keywords":["Immunität","Al-Bashir","Staatschef","Haftbefehl","Art. 27"],"category":"Immunität Staatschef / Al-Bashir"},
  {"id":4,"skill":"voelkerstrafrecht","question":"Ein Militärkommandeur kontrolliert eine Miliz nicht direkt, aber die Miliz begeht Kriegsverbrechen. Haftet er strafrechtlich?","expected_norms":["Art. 28 IStGH-Statut","§ 4 VStGB"],"expected_keywords":["Vorgesetztenverantwortlichkeit","effektive Kontrolle","Unterlassen","Katanga","Beihilfe"],"category":"Vorgesetztenverantwortlichkeit"},
  {"id":5,"skill":"voelkerstrafrecht","question":"Nach deutschem Recht wurde ein ruandischer Ex-Bürgermeister wegen Unterlassens bei Massakern verurteilt. Welches Gesetz gilt, und was sind die Voraussetzungen?","expected_norms":["§ 4 VStGB","§ 7 StGB"],"expected_keywords":["VStGB","Vorgesetztenverantwortlichkeit","effektive Kontrolle","Weltrechtsprinzip","BGH"],"category":"VStGB Vorgesetztenverantwortlichkeit"},
],

"sanktionsrecht": [
  {"id":1,"skill":"sanktionsrecht","question":"Die EU setzt UN-Sanktionen um und friert Gelder ein, ohne den Betroffenen anzuhören. Ist das mit EU-Grundrechten vereinbar?","expected_norms":["Art. 47 GRCh","Art. 41 GRCh"],"expected_keywords":["Kadi","Sanktionsliste","rechtliches Gehör","effektiver Rechtsschutz","UN-Sicherheitsrat"],"category":"Kadi I / Grundrechtsschutz"},
  {"id":2,"skill":"sanktionsrecht","question":"Nach Kadi I wird eine Person erneut gelistet, diesmal mit einer kurzen Begründung. Reicht das aus?","expected_norms":["Art. 47 GRCh"],"expected_keywords":["Kadi II","Begründungspflicht","Beweislast","inhaltliche Prüfung","Widerlegung"],"category":"Kadi II / Begründungspflicht"},
  {"id":3,"skill":"sanktionsrecht","question":"Rosneft klagt gegen EU-Sanktionen im Energiesektor wegen der Krim-Annexion. Hat der EuGH Zuständigkeit, und sind die Sanktionen rechtmäßig?","expected_norms":["Art. 215 AEUV","Art. 29 EUV"],"expected_keywords":["Rosneft","Russland-Sanktionen","Verhältnismäßigkeit","GASP","Art. 215 AEUV"],"category":"Russland-Sanktionen / Rosneft"},
  {"id":4,"skill":"sanktionsrecht","question":"Die Bank Melli Iran wird gelistet. Was muss der Rat begründen, damit die Listung rechtmäßig ist?","expected_norms":["Art. 215 AEUV","Art. 41 GRCh"],"expected_keywords":["Begründungspflicht","Iran-Sanktionen","individuelle Zurechnung","Bank Melli","konkrete Gründe"],"category":"Iran-Sanktionen / Begründung"},
  {"id":5,"skill":"sanktionsrecht","question":"Kann sich ein Staat auf völkerrechtliche UN-Verpflichtungen berufen, um EU-Grundrechte bei Sanktionen außer Kraft zu setzen?","expected_norms":["Art. 6 EUV","Art. 47 GRCh"],"expected_keywords":["UN-Charta","EU-Grundrechte","Kadi-Doktrin","Vorrang","Verhältnis"],"category":"Verhältnis EU-Recht / UN-Recht"},
],

"waffenrecht": [
  {"id":1,"skill":"waffenrecht","question":"Ein Waffenbesitzer wird wegen einer Straftat zu einer Geldstrafe verurteilt. Hat die Behörde Ermessen beim Widerruf der Erlaubnis?","expected_norms":["§ 5 WaffG","§ 45 WaffG"],"expected_keywords":["Zuverlässigkeit","Regelunzuverlässigkeit","gebundene Entscheidung","kein Ermessen","Widerruf"],"category":"Waffenzuverlässigkeit Straftat"},
  {"id":2,"skill":"waffenrecht","question":"Nach einem psychischen Vorfall fordert die Behörde ein Gutachten. Der Inhaber verweigert es. Was passiert?","expected_norms":["§ 6 WaffG","§ 45 WaffG"],"expected_keywords":["persönliche Eignung","amtsärztliches Gutachten","Verweigerung","Schlussfolgerung","Ungeeignetheit"],"category":"Waffeneignung psychische Erkrankung"},
  {"id":3,"skill":"waffenrecht","question":"Ein Sportschütze beantragt Waffenbesitzkarten für viele Waffen. Wie wird das Bedürfnis geprüft?","expected_norms":["§ 14 WaffG","§ 4 WaffG"],"expected_keywords":["Bedürfnis","Sportschütze","aktive Vereinsmitgliedschaft","Disziplin","Nachweis"],"category":"Sportschütze Bedürfnis"},
  {"id":4,"skill":"waffenrecht","question":"Ein Waffenbesitzer gehört der Reichsbürger-Bewegung an. Ist er waffenrechtlich zuverlässig?","expected_norms":["§ 5 Abs. 1 WaffG"],"expected_keywords":["Reichsbürger","absolute Unzuverlässigkeit","verfassungsfeindlich","staatliche Autorität","Zuverlässigkeit"],"category":"Zuverlässigkeit Reichsbürger"},
  {"id":5,"skill":"waffenrecht","question":"Ein Sammler besitzt ein historisches automatisches Gewehr ohne KWKG-Genehmigung. Braucht er eine?","expected_norms":["§ 2 KWKG","§ 3 KWKG"],"expected_keywords":["Kriegswaffe","KWKG","Kriegswaffenliste","Sammlerprivileg","Genehmigungspflicht"],"category":"KWKG historische Kriegswaffe"},
],

"voelkerrecht": [
  {"id":1,"skill":"voelkerrecht","question":"Britische Kriegsschiffe liefen im Korfukanal auf Minen. Ist Albanien verantwortlich, obwohl es die Minen nicht legte? Und haben Kriegsschiffe ein Durchfahrtsrecht?","expected_norms":["Art. 37 SRÜ"],"expected_keywords":["Corfu Channel","Staatenverantwortlichkeit","unschuldige Durchfahrt","Warnpflicht","internationale Meerenge"],"category":"Corfu Channel / Durchfahrtsrecht"},
  {"id":2,"skill":"voelkerrecht","question":"Aktionäre einer kanadischen Gesellschaft in Spanien erleiden Schäden. Kann Belgien für seine Staatsangehörigen als Aktionäre diplomatischen Schutz ausüben?","expected_norms":["Art. 34 IGH-Statut"],"expected_keywords":["diplomatischer Schutz","Aktionäre","Barcelona Traction","erga omnes","Heimatstaat Gesellschaft"],"category":"Barcelona Traction / Diplomatischer Schutz"},
  {"id":3,"skill":"voelkerrecht","question":"Die USA unterstützen Rebellen in Nicaragua mit Waffen und Geld. Verletzt das das Gewaltverbot? Was ist der 'Effective Control'-Test?","expected_norms":["Art. 2 Nr. 4 UN-Charta","Art. 51 UN-Charta"],"expected_keywords":["Gewaltverbot","Nicaragua","Effective Control","Nichteinmischung","Selbstverteidigung","IGH"],"category":"Nicaragua / Gewaltverbot"},
  {"id":4,"skill":"voelkerrecht","question":"Ist der Einsatz von Atomwaffen nach Völkerrecht verboten? Was sagt der IGH?","expected_norms":["Art. 2 Nr. 4 UN-Charta"],"expected_keywords":["Atomwaffen","humanitäres Völkerrecht","Unterscheidungsgebot","Verhältnismäßigkeit","Gutachten 1996","NVV"],"category":"Legalität Atomwaffen"},
  {"id":5,"skill":"voelkerrecht","question":"Kosovo erklärt einseitig die Unabhängigkeit von Serbien. Verstößt das gegen das Völkerrecht?","expected_norms":["Art. 1 UN-Charta"],"expected_keywords":["Kosovo","Unabhängigkeitserklärung","Selbstbestimmungsrecht","territoriale Integrität","einseitig","Gutachten 2010"],"category":"Kosovo / Selbstbestimmungsrecht"},
],

}

def main():
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    for skill, questions in QUESTIONS.items():
        path = EVAL_DIR / f"{skill}.json"
        # Merge with existing if present
        existing = []
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except Exception:
                existing = []
        # Renumber new questions starting after existing count
        max_id = len(existing)
        added = 0
        for q in questions:
            q["id"] = max_id + 1
            max_id += 1
            existing.append(q)
            added += 1
        path.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
        print(f"  {skill}: +{added} Fragen (total {len(existing)})", flush=True)

if __name__ == "__main__":
    main()
