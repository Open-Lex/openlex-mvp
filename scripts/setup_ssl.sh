#!/usr/bin/env bash
# Setup SSL for OpenLex Gradio app via nginx reverse proxy + Let's Encrypt
# Usage: sudo bash scripts/setup_ssl.sh
#
# Prerequisites: DNS A-Record for app.open-lex.cloud -> 91.98.146.160

set -euo pipefail

DOMAIN="app.open-lex.cloud"
UPSTREAM="127.0.0.1:7860"
NGINX_CONF="/etc/nginx/sites-available/openlex"
EMAIL="contact@open-lex.cloud"

echo "=== OpenLex SSL Setup ==="
echo "Domain:   $DOMAIN"
echo "Upstream: $UPSTREAM"
echo ""

# 1. Install nginx + certbot
echo "[1/5] Installing nginx + certbot ..."
apt-get update -qq
apt-get install -y -qq nginx certbot python3-certbot-nginx

# 2. Create nginx config (HTTP only first, certbot adds SSL)
echo "[2/5] Creating nginx config ..."
cat > "$NGINX_CONF" <<'NGINX'
server {
    listen 80;
    server_name app.open-lex.cloud;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;

        # WebSocket support (required for Gradio streaming)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Forward client info
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Disable buffering for streaming responses
        proxy_buffering off;
        proxy_cache off;

        # Long timeout for LLM responses
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
NGINX

# 3. Enable site and test config
echo "[3/5] Enabling site ..."
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/openlex
# Remove default site if it conflicts
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi
nginx -t
systemctl reload nginx

# 4. Get SSL certificate
echo "[4/5] Requesting SSL certificate ..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

# 5. Verify auto-renewal
echo "[5/5] Testing auto-renewal ..."
certbot renew --dry-run

echo ""
echo "=== Done! ==="
echo "App is now available at: https://$DOMAIN"
echo "Certificate auto-renews via systemd timer."
echo ""
echo "Next steps:"
echo "  1. Test: curl -I https://$DOMAIN"
echo "  2. Open in browser: https://$DOMAIN"
echo "  3. Add to iPhone homescreen via Safari share menu"
