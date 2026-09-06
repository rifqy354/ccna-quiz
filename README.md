# CCNA Adaptive Quiz

A local CCNA study app with single- and multiple-answer questions, explanations,
question diagrams, confidence-based review scheduling, mastery tracking, and
per-domain statistics.

Stack: Next.js 15, React 18, FastAPI, SQLite, and Docker Compose with nginx.

## Local development

Use Python 3.11 or 3.12 and Node.js 20 or newer. Run these commands from the
project root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
# Set JWT_SECRET_KEY in .env; generate one with: openssl rand -hex 32
cd frontend
npm ci
cd ..
```

If the question bank is already in `data/ccna.db`, keep it. Otherwise import the
source books (EPUB files are not included in this repository):

```bash
.venv/bin/python -m backend.extraction.main \
  "/path/to/practice-tests.epub" "/path/to/ocg-library.epub" --output ./data
```

Start the backend from the project root so it reads the root `.env`:

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```bash
cd frontend
npm run dev
```

Open http://localhost:3000, register, and start a study session. Browser requests
use the same origin; Next.js proxies `/api` to `http://127.0.0.1:8000` during
local development. If that port is occupied, change the uvicorn port and run
Next with `INTERNAL_API_URL=http://127.0.0.1:8001 npm run dev`.

## Study behavior

- Select one option for a single-answer question or all required options for a
  multi-answer question. Grading is order-independent and requires an exact match.
- Choose `again`, `hard`, `good`, or `easy` to submit the answer and confidence.
  The answer and explanation are then revealed.
- Wrong answers reset the streak and mastery, reduce ease by 0.2 (floor 1.3), and
  schedule review for the next day, regardless of confidence. Correct answers use
  the confidence-based interval. A correct answer marked `again` still resets
  learning. Five consecutive successful reviews earn mastery.
- New sessions use unattempted questions. Review sessions prioritize due questions
  and then other attempted questions. Mixed sessions combine review and new
  questions with fallback to available learning material. Each queue contains
  unique questions and may be smaller than the requested count (maximum 50).
- Session summaries count submitted answers. Only nonempty completed sessions
  contribute to the study streak.

**Study session persistence is intentionally not implemented.** Active queues
are held by one backend process and are lost on restart; run exactly one worker.
Answers, review progress, and completed summaries are saved in SQLite. Browser
refresh may lose the displayed queue count, but the running backend still knows
its current question. Historical progress from older grading rules is not rebuilt.

## Dataset and upgrades

The supplied editions produce **1,546 questions**: 1,203 Practice Tests and 343
OCG. Domains 1–6 contain 235, 259, 331, 188, 209, and 124 questions; Practice Exams
(domain 7) contains 200. There are 134 multi-answer questions and 112 diagrams.
Populated extra options: E = 88, F = 31, G = 17.

Questions use flat `option_a` through `option_g` columns and answer strings such
as `BDE`. Startup and extraction initialization add missing nullable E–G columns
without replacing question IDs. To populate those columns in an older bank:

```bash
.venv/bin/python -m backend.extraction.backfill ./data/ccna.db \
  "/path/to/practice-tests.epub" "/path/to/ocg-library.epub"
```

The backfill creates a timestamped SQLite backup, checks exact source identities
and existing content, and updates E–G in one transaction. It preserves IDs,
images, and history and refuses ambiguous or incomplete source matches.

The general extraction CLI validates both sources before importing and updates
matching records in place, preserving their IDs and history on repeat imports.
It exits nonzero on failure. `--dry-run` validates both EPUBs without creating
output files. Back up a populated bank before changing its source content.

## Verification

All backend tests use disposable databases; they do not modify `data/ccna.db`.

```bash
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run build
npm audit
```

One optional real-book test is skipped unless both source paths are set:

```bash
CCNA_PT_EPUB="/path/to/practice-tests.epub" \
CCNA_OCG_EPUB="/path/to/ocg-library.epub" \
.venv/bin/python -m pytest -q
```

Tests cover authentication and refresh rotation, safe schema upgrades and
imports, answer grading, duplicate submissions, completion races, correctness-aware
mastery, stale/concurrent progress, selection, statistics, diagrams, and frontend
API/auth/study behavior. See [verification results](docs/verification.md) for the
latest integration checks.

## Docker deployment

```bash
cp .env.example .env  # Skip if already configured; set a generated JWT_SECRET_KEY.
docker compose config --quiet
docker compose up --build -d
curl http://127.0.0.1:8080/health
```

Open http://127.0.0.1:8080. nginx serves the frontend and proxies `/api` to the
backend. The browser never needs Docker's internal service hostnames. The backend
uses the mounted `data` directory and a Python-based health check.

Compose options can be set in `.env`:

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | Required | JWT signing secret |
| `DATA_DIR` | `./data` | Directory containing the SQLite bank and images |
| `HTTP_BIND` | `127.0.0.1` | Host interface to bind |
| `HTTP_PORT` | `8080` | Host HTTP port |

The production override serves `email2.my.id` over HTTPS and keeps the ACME
webroot available for certificate renewal. After the domain's AAAA record points
to the host, provision the initial certificate while the base HTTP stack is
running, then enable the override:

```bash
sudo install -d -m 755 /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot -d email2.my.id
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
```

Set `HTTPS_BIND`, `HTTPS_PORT`, `CERTBOT_WEBROOT`, and `LETSENCRYPT_DIR` in the
production `.env` when their defaults do not match the host. Configure Certbot's
deploy hook to reload nginx after renewal. Do not expose the development server
as a production service.

## API

Interactive documentation: http://127.0.0.1:8000/docs when running the backend locally.

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/auth/register` | POST | No | Register |
| `/api/auth/login` | POST | No | Issue access and refresh tokens |
| `/api/auth/refresh` | POST | No | Rotate a refresh token |
| `/api/auth/me` | GET | Yes | Current user |
| `/api/domains` | GET | Yes | Six CCNA domains plus Practice Exams |
| `/api/domains/{id}` | GET | Yes | Domain topics |
| `/api/questions/random` | GET | Yes | Question with multi-answer metadata |
| `/api/sessions/start` | POST | Yes | Start a queue |
| `/api/sessions/{id}/next` | GET | Yes | Current question; 204 when exhausted |
| `/api/sessions/{id}/answer` | POST | Yes | Answer and confidence |
| `/api/sessions/{id}/complete` | POST | Yes | Complete and summarize |
| `/api/stats/dashboard` | GET | Yes | Progress and streak |
| `/api/stats/weak-areas` | GET | Yes | Areas below the recall threshold |
| `/api/images/{filename}` | GET | No | Question diagram |
| `/health` | GET | No | Health check |

Stale/exhausted answers return 409; missing or completed sessions return 404.
Invalid input returns 422. Question responses omit answer keys and explanations.
Concurrent mutations of one session are serialized; progress updates across
sessions read the latest saved state inside a transaction.
