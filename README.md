# CCNA Adaptive Quiz System

A production-ready adaptive quiz system with retrieval practice, SM-2 spaced repetition, mastery tracking, and targeted remediation, deployed via Docker Compose on a VPS.

## Prerequisites

- Docker & Docker Compose
- A domain with an AAAA record (IPv6) pointing to your VPS
- Cloudflare as DNS proxy — enables IPv4 fallback via Cloudflare's proxy for browsers that don't support IPv6

## Setup

### 1. Clone the repo

```bash
git clone <repo-url> ccna-quiz
cd ccna-quiz
```

### 2. Generate JWT secret

```bash
openssl rand -hex 32
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set JWT_SECRET_KEY to the value from step 2
```

### 4. Seed the database (local extraction)

Run the EPUB extraction pipeline on your local machine (requires the source EPUBs):

```bash
cd backend
pip install -r requirements.txt
python -m extraction.main \
  "/path/to/Practice-Tests.epub" \
  "/path/to/OCG-Library.epub" \
  --output ../data
```

Then copy the `data/` directory to the server:

```bash
scp -r ./data user@your-vps:/path/to/ccna-quiz/
```

### 5. Start services

```bash
docker compose up -d
```

### 6. SSL setup

**Option A — Let's Encrypt with certbot:**

```bash
certbot --nginx -d yourdomain.com
```

**Option B — Cloudflare Origin Certificate:**

1. Generate an Origin Certificate in Cloudflare Dashboard (PEM format)
2. Copy the cert and key to `nginx/ssl/fullchain.pem` and `nginx/ssl/privkey.pem`
3. Ensure the site is behind Cloudflare proxy (orange cloud)

### 7. Verify

```bash
curl https://yourdomain.com/health
# Expected: {"status":"ok"}
```

## Common Issues

### Containers fail to start

Check that `JWT_SECRET_KEY` is set in `.env`. The backend will refuse to start without it.

### Backend health check fails

Ensure port 8000 is not in use and the backend container started successfully:

```bash
docker compose logs backend
```

### Frontend 502 errors

Wait for the Next.js build to complete inside the container (first start takes ~2 min). Check:

```bash
docker compose logs frontend
```

### Database not found

The `data/ccna.db` must exist. If you skipped the extraction step, the DB will be empty (no questions). You can create an empty DB:

```bash
sqlite3 data/ccna.db "CREATE TABLE IF NOT EXISTS questions (id INTEGER PRIMARY KEY);"
```

### nginx SSL errors

Ensure `nginx/ssl/` contains both `fullchain.pem` and `privkey.pem`. Without SSL certs, only port 80 will work.
