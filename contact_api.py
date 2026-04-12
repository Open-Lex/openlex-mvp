#!/usr/bin/env python3
"""Minimal contact-form API – listens on port 8081, sends mail via MX."""

import json
import smtplib
import re
from email.mime.text import MIMEText
from http.server import HTTPServer, BaseHTTPRequestHandler

TO_ADDR = "contact@open-lex.cloud"
FROM_ADDR = "noreply@open-lex.cloud"
MX_HOST = "localhost"
PORT = 8081

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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

        if not message and not email:
            self._json(400, {"error": "Nachricht oder E-Mail erforderlich"})
            return

        if email and not EMAIL_RE.match(email):
            self._json(400, {"error": "Ungültige E-Mail-Adresse"})
            return

        text = f"Nachricht:\n{message}\n\nAbsender: {email or '(nicht angegeben)'}"
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = "OpenLex – Kontaktanfrage"
        msg["From"] = FROM_ADDR
        msg["To"] = TO_ADDR
        if email:
            msg["Reply-To"] = email

        try:
            with smtplib.SMTP(MX_HOST, 25, timeout=10) as smtp:
                smtp.sendmail(FROM_ADDR, [TO_ADDR], msg.as_string())
            self._json(200, {"ok": True})
        except Exception as e:
            print(f"SMTP error: {e}")
            self._json(500, {"error": "Mail konnte nicht gesendet werden"})

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
