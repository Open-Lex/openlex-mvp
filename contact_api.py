#!/usr/bin/env python3
"""Contact-form API – saves to file + sends via Hostinger SMTP."""

import json
import smtplib
import ssl
import re
import os
from datetime import datetime
from email.mime.text import MIMEText
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8081
CONTACT_LOG = "/opt/openlex-mvp/contact_messages.jsonl"
CREDS_FILE = "/opt/openlex-mvp/.smtp_credentials"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def load_smtp_creds():
    creds = {}
    try:
        with open(CREDS_FILE) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    creds[k] = v
    except Exception:
        pass
    return creds


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/contact":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except Exception:
            self._json(400, {"error": "Invalid JSON"})
            return

        message = (data.get("message") or "").strip()
        email = (data.get("email") or "").strip()
        source = (data.get("source") or "web").strip().lower()
        if source not in ("web", "app"):
            source = "web"

        if not message and not email:
            self._json(400, {"error": "Nachricht oder E-Mail erforderlich"})
            return

        if email and not EMAIL_RE.match(email):
            self._json(400, {"error": "Ungueltige E-Mail-Adresse"})
            return

        # Always save to file first
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "message": message,
            "email": email or None,
            "source": source,
            "ip": self.headers.get("X-Real-IP", "unknown"),
        }
        try:
            with open(CONTACT_LOG, "a") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"File write error: {e}")

        # Send email via Hostinger SMTP (STARTTLS on 587 / SSL on 465)
        creds = load_smtp_creds()
        smtp_host = creds.get("SMTP_HOST", "smtp.hostinger.com")
        smtp_port = int(creds.get("SMTP_PORT", "465"))
        smtp_user = creds.get("SMTP_USER", "")
        smtp_pass = creds.get("SMTP_PASS", "")

        text = f"Quelle: {source}\n\nNachricht:\n{message}\n\nAbsender: {email or '(nicht angegeben)'}"
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = "OpenLex Kontaktanfrage" + (" [APP]" if source == "app" else "")
        msg["From"] = smtp_user
        msg["To"] = smtp_user
        if email:
            msg["Reply-To"] = email

        if smtp_user and smtp_pass and smtp_pass != "HIER_DEIN_PASSWORT_EINTRAGEN":
            try:
                ctx = ssl.create_default_context()
                if smtp_port == 465:
                    smtp = smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=10)
                else:
                    smtp = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                    smtp.ehlo()
                    smtp.starttls(context=ctx)
                smtp.login(smtp_user, smtp_pass)
                smtp.sendmail(smtp_user, [smtp_user], msg.as_string())
                smtp.quit()
                print(f"[contact] Mail sent for: {email or 'anon'}")
            except Exception as e:
                print(f"[contact] SMTP failed (saved to file): {e}")
        else:
            print("[contact] No SMTP credentials configured (saved to file only)")

        self._json(200, {"ok": True})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "https://open-lex.cloud")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        print(f"[contact] {args[0]}")


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Contact API listening on :{PORT}")
    server.serve_forever()
