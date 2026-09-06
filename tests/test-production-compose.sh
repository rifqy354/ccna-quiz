#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export JWT_SECRET_KEY=test-only-secret
export HTTP_BIND='[::]'
export HTTP_PORT=80
export HTTPS_BIND='[::]'
export HTTPS_PORT=443
export CERTBOT_WEBROOT=/var/www/certbot
export LETSENCRYPT_DIR=/etc/letsencrypt

docker compose \
  -f "$project_dir/docker-compose.yml" \
  -f "$project_dir/docker-compose.production.yml" \
  config --format json |
python3 -c '
import json
import sys

config = json.load(sys.stdin)
nginx = config["services"]["nginx"]
published = {(port["host_ip"], int(port["published"]), port["target"]) for port in nginx["ports"]}
assert ("::", 80, 80) in published
assert ("::", 443, 443) in published

targets = {volume["target"]: volume for volume in nginx["volumes"]}
assert targets["/var/www/certbot"]["source"] == "/var/www/certbot"
assert targets["/etc/letsencrypt"]["source"] == "/etc/letsencrypt"
assert targets["/etc/nginx/nginx.conf"]["source"].endswith("nginx.production.conf")
'

production_nginx="$project_dir/nginx/nginx.production.conf"
python3 -c '
import pathlib
import sys

text = pathlib.Path(sys.argv[1]).read_text()
assert "server_name email2.my.id quiz.email2.my.id;" in text
assert "server_name email2.my.id;" in text
assert "server_name quiz.email2.my.id;" in text
assert "location /api/ {\n            return 404;" in text
assert "location /api/ {\n            proxy_pass http://backend;" in text
assert text.count("/etc/letsencrypt/live/email2.my.id/") == 4
' "$production_nginx"

temporary_cert_dir=$(mktemp -d)
trap 'rm -rf "$temporary_cert_dir"' EXIT
mkdir -p "$temporary_cert_dir/live/email2.my.id"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
  -subj '/CN=email2.my.id' \
  -keyout "$temporary_cert_dir/live/email2.my.id/privkey.pem" \
  -out "$temporary_cert_dir/live/email2.my.id/fullchain.pem" >/dev/null 2>&1
docker run --rm \
  --add-host frontend:127.0.0.1 \
  --add-host backend:127.0.0.1 \
  -v "$production_nginx:/etc/nginx/nginx.conf:ro" \
  -v "$temporary_cert_dir:/etc/letsencrypt:ro" \
  nginx:alpine nginx -t
