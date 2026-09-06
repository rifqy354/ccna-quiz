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
