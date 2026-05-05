#!/usr/bin/env python3
"""
OpenLex Sichtprüfung: v1 vs v2 Side-by-Side HTML-Report.
Startet Runner für v1 und v2 parallel, wartet auf Ergebnisse,
generiert HTML-Tabelle.
"""
import subprocess
import json
import sys
import time
import os
import html

RUNNER = "/tmp/openlex_runner.py"
PYTHON = "/opt/openlex-mvp/venv/bin/python3"
OUTPUT_HTML = "/opt/openlex-mvp-v2/sichtpruefung_results.html"

def run_version(version):
    start = time.time()
    proc = subprocess.Popen(
        [PYTHON, RUNNER, version],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(timeout=600)
    elapsed = round(time.time() - start)
    print(f"[{version}] fertig in {elapsed}s, returncode={proc.returncode}", file=sys.stderr)
    if stderr:
        for line in stderr.splitlines()[-10:]:
            print(f"  STDERR: {line}", file=sys.stderr)
    if proc.returncode != 0:
        return {"version": version, "results": [], "error": stderr[-500:]}
    try:
        return json.loads(stdout)
    except Exception as e:
        return {"version": version, "results": [], "error": f"JSON-Parse-Fehler: {e}\nOutput: {stdout[:200]}"}

print("Starte v1 und v2 parallel ...", file=sys.stderr)
import threading

results = {}

def run_and_store(version):
    results[version] = run_version(version)

t1 = threading.Thread(target=run_and_store, args=("v1",))
t2 = threading.Thread(target=run_and_store, args=("v2",))
t1.start()
t2.start()
t1.join()
t2.join()

v1_data = results.get("v1", {})
v2_data = results.get("v2", {})
v1_results = v1_data.get("results", [])
v2_results = v2_data.get("results", [])

# ── Source-Overlap-Berechnung ──────────────────────────────────────────────
def source_keys(sources):
    return {s["key"] for s in sources if s.get("key")}

def overlap_rating(k1, k2):
    if not k1 and not k2:
        return "–", "gray"
    if not k1 or not k2:
        return "KEINE DATEN", "orange"
    shared = k1 & k2
    total = k1 | k2
    pct = len(shared) / len(total) * 100 if total else 100
    if pct >= 70:
        return f"✅ {len(shared)}/{len(total)} Quellen identisch ({pct:.0f}%)", "#2d7a2d"
    elif pct >= 40:
        return f"⚠️ {len(shared)}/{len(total)} Quellen identisch ({pct:.0f}%)", "#8a6000"
    else:
        return f"❌ {len(shared)}/{len(total)} Quellen identisch ({pct:.0f}%)", "#8b0000"

# ── HTML generieren ────────────────────────────────────────────────────────
def esc(s):
    return html.escape(str(s) if s else "")

def source_badge(source_type):
    colors = {
        "gesetz": "#1a5f8a", "gesetz_granular": "#1a5f8a",
        "urteil": "#6b3a8a", "urteil_segmentiert": "#6b3a8a",
        "leitlinie": "#2d7a4f", "erwaegungsgrund": "#7a5500",
        "methodenwissen": "#555",
    }
    color = colors.get(source_type, "#666")
    return f'<span style="background:{color};color:#fff;font-size:10px;padding:1px 5px;border-radius:3px;white-space:nowrap">{esc(source_type)}</span>'

def format_sources_html(sources):
    if not sources:
        return "<em style='color:#999'>Keine Quellen</em>"
    items = []
    for s in sources:
        badge = source_badge(s.get("source_type", ""))
        key = esc(s.get("key", ""))
        seg = esc(s.get("segment", ""))
        seg_html = f' <span style="color:#888;font-size:10px">({seg})</span>' if seg else ""
        items.append(f'<div style="margin:2px 0">{badge} {key}{seg_html}</div>')
    return "".join(items)

def highlight_diff(sources1, sources2):
    k1 = source_keys(sources1)
    k2 = source_keys(sources2)
    only_v1 = k1 - k2
    only_v2 = k2 - k1
    shared = k1 & k2

    lines = []
    if shared:
        lines.append(f'<div style="color:#2d7a2d;font-size:11px">✓ Beide: {", ".join(sorted(shared))}</div>')
    if only_v1:
        lines.append(f'<div style="color:#8a5000;font-size:11px">⊳ Nur v1: {", ".join(sorted(only_v1))}</div>')
    if only_v2:
        lines.append(f'<div style="color:#1a5f8a;font-size:11px">⊳ Nur v2: {", ".join(sorted(only_v2))}</div>')
    return "".join(lines) if lines else "<em>–</em>"

HTML_HEAD = """<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OpenLex Sichtprüfung: v1 vs v2</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
       background: #f5f5f0; color: #1a1a1a; font-size: 14px; }
.header { background: #1a1a2e; color: #c9a04a; padding: 20px 32px; }
.header h1 { font-size: 22px; font-weight: 700; }
.header .meta { color: #888; font-size: 12px; margin-top: 6px; }
.container { max-width: 1600px; margin: 0 auto; padding: 20px; }
.query-block { background: #fff; border: 1px solid #ddd; border-radius: 8px;
               margin-bottom: 28px; overflow: hidden; }
.query-header { background: #1a1a2e; color: #fff; padding: 12px 20px;
                font-weight: 600; font-size: 15px; }
.query-header .qnum { color: #c9a04a; margin-right: 8px; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.col { padding: 16px 20px; border-right: 1px solid #eee; }
.col:last-child { border-right: none; }
.col-header { font-weight: 700; font-size: 12px; text-transform: uppercase;
              letter-spacing: 0.5px; margin-bottom: 10px; padding-bottom: 6px;
              border-bottom: 2px solid; }
.v1-header { color: #1a5f8a; border-color: #1a5f8a; }
.v2-header { color: #6b3a8a; border-color: #6b3a8a; }
.response-text { font-size: 13px; line-height: 1.6; white-space: pre-wrap;
                 max-height: 400px; overflow-y: auto; background: #fafafa;
                 border: 1px solid #eee; padding: 10px; border-radius: 4px; }
.sources-section { margin-top: 12px; }
.sources-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
                 color: #666; margin-bottom: 4px; }
.latency { font-size: 11px; color: #888; margin-top: 8px; }
.diff-row { background: #f8f8f5; border-top: 1px solid #eee;
            padding: 12px 20px; font-size: 12px; }
.diff-label { font-weight: 600; font-size: 11px; text-transform: uppercase;
              color: #555; margin-bottom: 4px; }
.overlap-row { background: #f0f0ec; border-top: 1px solid #ddd;
               padding: 10px 20px; display: flex; align-items: center; gap: 16px; }
.overlap-badge { font-weight: 700; font-size: 13px; }
.summary-table { width: 100%; border-collapse: collapse; background: #fff;
                 border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
.summary-table th { background: #1a1a2e; color: #c9a04a; padding: 10px 14px;
                    text-align: left; font-size: 12px; }
.summary-table td { padding: 9px 14px; border-bottom: 1px solid #eee; font-size: 13px; }
.summary-table tr:last-child td { border-bottom: none; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px;
       font-weight: 600; }
.tag-pass { background: #e6f4e6; color: #2d7a2d; }
.tag-warn { background: #fff3cd; color: #8a6000; }
.tag-fail { background: #fde8e8; color: #8b0000; }
.section-title { font-size: 16px; font-weight: 700; margin: 24px 0 12px; color: #333; }
</style>
</head>
<body>
<div class="header">
  <h1>OpenLex Sichtprüfung — v1 vs v2 Side-by-Side</h1>
  <div class="meta">Stand: {timestamp} &nbsp;|&nbsp;
  v1: /opt/openlex-mvp (Port 7860) &nbsp;|&nbsp;
  v2: /opt/openlex-mvp-v2 (Port 7864, refactor/multi-skill-support)</div>
</div>
<div class="container">
"""

HTML_FOOT = """
</div>
</body>
</html>"""

import datetime
timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

html_parts = [HTML_HEAD.replace("{timestamp}", timestamp)]

summary_rows = []

for i, q in enumerate(["Was sagt Art. 6 DSGVO?",
                         "Brüstle und Datenschutz",
                         "Schrems II Konsequenzen für USA-Datentransfer",
                         "Wie lange muss ich Cookies löschen?",
                         "Was ändert sich durch das TDDDG?"], 1):

    r1 = next((r for r in v1_results if r["query"] == q), {})
    r2 = next((r for r in v2_results if r["query"] == q), {})

    resp1 = r1.get("response", "[nicht verfügbar]")
    resp2 = r2.get("response", "[nicht verfügbar]")
    src1  = r1.get("sources", [])
    src2  = r2.get("sources", [])
    lat1  = r1.get("latency_ms", "–")
    lat2  = r2.get("latency_ms", "–")
    err1  = r1.get("error")
    err2  = r2.get("error")

    k1 = source_keys(src1)
    k2 = source_keys(src2)
    overlap_text, overlap_color = overlap_rating(k1, k2)

    # Summary rating
    if not k1 or not k2:
        tag_cls, tag_lbl = "tag-warn", "KEINE DATEN"
    else:
        shared = k1 & k2
        total  = k1 | k2
        pct = len(shared) / len(total) * 100 if total else 100
        if pct >= 70:
            tag_cls, tag_lbl = "tag-pass", "PASS"
        elif pct >= 40:
            tag_cls, tag_lbl = "tag-warn", "PRÜFEN"
        else:
            tag_cls, tag_lbl = "tag-fail", "ABWEICHUNG"

    summary_rows.append((i, q, overlap_text, tag_cls, tag_lbl,
                          lat1, lat2))

    error_html = ""
    if err1:
        error_html += f'<div style="color:#8b0000;font-size:11px;padding:4px 20px">⚠ v1-Fehler: {esc(err1[:200])}</div>'
    if err2:
        error_html += f'<div style="color:#8b0000;font-size:11px;padding:4px 20px">⚠ v2-Fehler: {esc(err2[:200])}</div>'

    block = f"""
<div class="query-block">
  <div class="query-header"><span class="qnum">Q{i}</span>{esc(q)}</div>
  {error_html}
  <div class="cols">
    <div class="col">
      <div class="col-header v1-header">v1 — Live (Port 7860)</div>
      <div class="response-text">{esc(resp1)}</div>
      <div class="sources-section">
        <div class="sources-label">Quellen ({len(src1)})</div>
        {format_sources_html(src1)}
      </div>
      <div class="latency">⏱ {lat1} ms</div>
    </div>
    <div class="col">
      <div class="col-header v2-header">v2 — Refactor (Port 7864)</div>
      <div class="response-text">{esc(resp2)}</div>
      <div class="sources-section">
        <div class="sources-label">Quellen ({len(src2)})</div>
        {format_sources_html(src2)}
      </div>
      <div class="latency">⏱ {lat2} ms</div>
    </div>
  </div>
  <div class="diff-row">
    <div class="diff-label">Quellenvergleich</div>
    {highlight_diff(src1, src2)}
  </div>
  <div class="overlap-row">
    <span class="overlap-badge" style="color:{overlap_color}">{overlap_text}</span>
  </div>
</div>
"""
    html_parts.append(block)

# Summary table
html_parts.append('<div class="section-title">Zusammenfassung</div>')
html_parts.append('<table class="summary-table"><thead><tr>'
                  '<th>#</th><th>Query</th><th>Quellenübereinstimmung</th>'
                  '<th>Latenz v1</th><th>Latenz v2</th><th>Bewertung (Quellen)</th>'
                  '</tr></thead><tbody>')
for i, q, ov, tag_cls, tag_lbl, lat1, lat2 in summary_rows:
    html_parts.append(
        f'<tr><td>{i}</td><td>{esc(q[:60])}</td>'
        f'<td style="font-size:12px">{ov}</td>'
        f'<td>{lat1} ms</td><td>{lat2} ms</td>'
        f'<td><span class="tag {tag_cls}">{tag_lbl}</span></td></tr>'
    )
html_parts.append('</tbody></table>')
html_parts.append('<p style="margin-top:16px;font-size:12px;color:#888">'
                  '⚠ Bewertung "PASS/PRÜFEN/ABWEICHUNG" basiert rein auf Quellen-Overlap. '
                  'Finale Entscheidung trifft Hendrik manuell auf Basis der vollständigen Antworten.</p>')

html_parts.append(HTML_FOOT)

output = "".join(html_parts)
with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
    f.write(output)

print(f"HTML gespeichert: {OUTPUT_HTML} ({len(output):,} Zeichen)")
print("Summary:")
for i, q, ov, tag_cls, tag_lbl, lat1, lat2 in summary_rows:
    print(f"  Q{i}: {tag_lbl} — {ov}")
