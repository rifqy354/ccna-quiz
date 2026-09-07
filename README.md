# Rifqy Portfolio and CCNA Quiz

One Next.js application serves Rifqy's editorial portfolio at
`email2.my.id` and a guest CCNA study game at `quiz.email2.my.id`.
FastAPI and SQLite provide the question bank, learning progress, fixed
challenge, and public best-score leaderboard.

## Local development

Use Python 3.11 or 3.12 and Node.js 20 or newer:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
cp .env.example .env
# Replace JWT_SECRET_KEY with the output of: openssl rand -hex 32
cd frontend && npm ci && cd ..
```

Start the backend from the project root:

```bash
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start Next.js in another terminal:

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000` for the portfolio and
`http://quiz.localhost:3000` for the quiz. Next.js proxies same-origin
`/api` requests to `http://127.0.0.1:8000`. Set `INTERNAL_API_URL`
when the backend uses another port.

The first quiz visit asks for a 2–24 character display name. A signed,
HTTP-only cookie identifies that guest in the same browser. Duplicate names
are allowed. Clearing cookies creates a new player.

## Quiz behavior

- Domain and mixed study sessions update learning progress but never the
  public leaderboard.
- Single-answer questions replace the previous selection. Multiple-answer
  questions require the exact set, regardless of selection order.
- Confidence choices are Again, Hard, Good, and Easy. Wrong answers schedule
  review for the next day. Five consecutive successful reviews earn mastery.
- The Challenge always contains 20 questions: three from each domain 1–6 and
  two from Practice Exams. Each correct answer is worth five points.
- Only a player's strictly higher completed Challenge score replaces their
  public record. Equal scores use dense ranking.

**Study session persistence is intentionally not implemented.** Active queues
are held by one backend process and are lost on restart; run exactly one worker.
Answers, review progress, completed summaries, guest players, and best challenge
records are saved in SQLite. Browser refresh may lose the displayed queue count,
but the running backend still knows its current question.

## Dataset and upgrades

The supplied editions produce **1,546 questions**: 1,203 Practice Tests and 343
OCG. Domains 1–6 contain 235, 259, 331, 188, 209, and 124 questions; Practice
Exams contains 200. There are 134 multi-answer questions and 112 diagrams.
Populated extra options: E = 88, F = 31, G = 17.

Startup performs additive schema initialization. It preserves existing question
IDs and data while adding missing option columns, guest players, and challenge
records. Back up `data/ccna.db` before deployment or source changes.

To create a question bank from locally owned EPUB sources:

```bash
.venv/bin/python -m backend.extraction.main \
  "/path/to/practice-tests.epub" "/path/to/ocg-library.epub" --output ./data
```

To backfill E–G options in an older bank:

```bash
.venv/bin/python -m backend.extraction.backfill ./data/ccna.db \
  "/path/to/practice-tests.epub" "/path/to/ocg-library.epub"
```

## Verification

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build && cd ..
JWT_SECRET_KEY=test-only-secret docker compose config --quiet
JWT_SECRET_KEY=test-only-secret bash tests/test-production-compose.sh
```

Tests use disposable databases. The optional real-book test runs when
`CCNA_PT_EPUB` and `CCNA_OCG_EPUB` are set. See
[docs/verification.md](docs/verification.md) for deployment evidence.

## Docker deployment

```bash
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
```

The production override binds HTTPS and mounts the Let's Encrypt directory:

```bash
docker compose -f docker-compose.yml -f docker-compose.production.yml up --build -d
```

The shared certificate must contain both `email2.my.id` and
`quiz.email2.my.id`. nginx exposes the backend API only on the quiz host;
`https://email2.my.id/api/*` returns 404.

| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET_KEY` | Required | Signs guest identity cookies |
| `PLAYER_COOKIE_NAME` | `ccna_player` | Guest cookie name |
| `PLAYER_COOKIE_MAX_AGE` | `31536000` | Guest cookie lifetime in seconds |
| `PLAYER_COOKIE_DOMAIN` | unset locally; `quiz.email2.my.id` in production | Cookie scope |
| `DATA_DIR` | `./data` | SQLite and diagram directory |
| `HTTP_BIND` / `HTTP_PORT` | `127.0.0.1` / `8080` | HTTP listener |
| `HTTPS_BIND` / `HTTPS_PORT` | `127.0.0.1` / `8443` | HTTPS listener |

## API

Interactive documentation is available at `http://127.0.0.1:8000/docs`
during local backend development.

| Endpoint | Method | Identity | Purpose |
|---|---|---|---|
| `/api/player` | POST | None | Create a guest player and cookie |
| `/api/player/me` | GET | Guest cookie | Read the current public player |
| `/api/domains` | GET | Guest cookie | Domain summaries |
| `/api/domains/{id}` | GET | Guest cookie | Domain topics |
| `/api/questions/random` | GET | Guest cookie | Random question |
| `/api/sessions/start` | POST | Guest cookie | Start a study queue |
| `/api/sessions/challenge` | POST | Guest cookie | Start the fixed challenge |
| `/api/sessions/{id}/next` | GET | Guest cookie | Current question |
| `/api/sessions/{id}/answer` | POST | Guest cookie | Submit answer and confidence |
| `/api/sessions/{id}/complete` | POST | Guest cookie | Complete and summarize |
| `/api/leaderboard` | GET | Public | Best challenge records |
| `/api/stats/dashboard` | GET | Guest cookie | Progress and streak |
| `/api/stats/weak-areas` | GET | Guest cookie | Areas below recall threshold |
| `/api/images/{filename}` | GET | Public | Question diagram |
| `/health` | GET | Public | Backend health |

Stale or exhausted answers return 409; missing or completed sessions return 404.
Question responses omit answer keys and explanations until submission.
