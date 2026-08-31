# CCNA Adaptive Quiz System

Adaptive CCNA 200-301 exam preparation with retrieval practice, spaced repetition (SM-2), mastery learning, and targeted remediation.

## Tech Stack

- **Frontend**: Next.js 14 (App Router)
- **Backend**: FastAPI (Python)
- **Database**: SQLite (aiosqlite)
- **Deployment**: Docker Compose + nginx

## Quick Start (Local Development)

```bash
# 1. Install dependencies
cd backend && pip install -r requirements.txt && cd ..
cd frontend && npm install && cd ..

# 2. Set up environment
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY

# 3. Run extraction (requires EPUB files)
python -m backend.extraction.main /path/to/practice-tests.epub /path/to/ocg.epub --output ./data

# 4. Start backend
cd backend && uvicorn app.main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd frontend && npm run dev
```

## Production Deployment

See [deployment docs](#deployment) below.

## Architecture

- `backend/` — FastAPI API server
- `frontend/` — Next.js 14 web app
- `nginx/` — Reverse proxy config
- `data/` — SQLite database + extracted images

## API

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/auth/register` | POST | No | Register user |
| `/api/auth/login` | POST | No | Login → JWT tokens |
| `/api/auth/refresh` | POST | No | Refresh access token |
| `/api/auth/me` | GET | Yes | Current user profile |
| `/api/domains` | GET | Yes | List 6 CCNA domains |
| `/api/domains/{id}` | GET | Yes | Domain detail + sub-topics |
| `/api/sessions/start` | POST | Yes | Start study session |
| `/api/sessions/{id}/next` | GET | Yes | Next question |
| `/api/sessions/{id}/answer` | POST | Yes | Submit answer + confidence |
| `/api/sessions/{id}/complete` | POST | Yes | End session |
| `/api/stats/dashboard` | GET | Yes | Dashboard stats |
| `/health` | GET | No | Health check |

## Deployment

### Prerequisites

- VPS with IPv6 and Docker + Docker Compose installed
- Domain with AAAA record pointing to VPS IPv6
- Cloudflare as DNS proxy (free) — enables IPv4 access

### 1. Clone & Configure

```bash
git clone <repo> /opt/ccna-quiz
cd /opt/ccna-quiz
cp .env.example .env
nano .env  # Set JWT_SECRET_KEY
```

### 2. Transfer Data

Run extraction on your laptop, then copy to VPS:
```bash
scp -r ./data root@[your-vps-ipv6]:/opt/ccna-quiz/ -6
```

### 3. SSL Setup

```bash
# Using Cloudflare Origin Certificate (recommended):
# Download cert+key from Cloudflare SSL/TLS → Origin Server
# Upload to nginx/ssl/ on VPS

# Or Let's Encrypt:
apt install certbot python3-certbot-nginx
certbot certonly --nginx -d yourdomain.com
```

### 4. Update nginx.conf

Edit `nginx/nginx.conf`:
- Replace `server_name _;` with `server_name yourdomain.com;`
- Point `ssl_certificate` and `ssl_certificate_key` to your cert files

### 5. Build & Start

```bash
# Build images on laptop, then copy to VPS:
docker compose build

# Or build on VPS (needs Docker installed):
docker compose build

# Start:
docker compose up -d

# Check:
docker compose logs --tail 20
curl https://yourdomain.com/health
```

### Memory Notes (1GB RAM VPS)

- Backend limited to 384MB
- Frontend limited to 256MB
- nginx limited to 64MB
- 1 gunicorn worker (not multiple uvicorn workers)
- Total idle RAM: ~600-700MB

### Swap (Recommended)

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

### Automatic Restart

```bash
# systemd service
cat > /etc/systemd/system/ccna-quiz.service << 'SVC'
[Unit]
Description=CCNA Quiz App
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/ccna-quiz
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
SVC

systemctl enable ccna-quiz
systemctl start ccna-quiz
```
