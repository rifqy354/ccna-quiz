# Portfolio and Guest CCNA Quiz Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish Rifqy's Signal / Editorial portfolio at `email2.my.id` and move the existing CCNA study experience to `quiz.email2.my.id` with cookie-based guest players and a best-score challenge leaderboard.

**Architecture:** Keep the existing Next.js, FastAPI, SQLite, Docker Compose, and Nginx stack. Reuse internal `users.id` ownership through a separate guest profile, add one best challenge record per guest, route both hosts through one frontend, and expose the API only on the quiz host. Active study and challenge queues remain in one backend process and are intentionally lost on restart.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, aiosqlite, python-jose, pytest, Next.js 15 App Router, React 18, TypeScript 5, Vitest, Testing Library, CSS, Nginx, Docker Compose, Cloudflare DNS, Let's Encrypt.

**Spec:** `docs/superpowers/specs/2026-09-06-portfolio-guest-quiz-design.md`

## Global Constraints

- Public quiz identity consists only of a 2–24 character display name and a signed `Secure`, `HttpOnly`, `SameSite=Lax` cookie scoped to `quiz.email2.my.id`.
- Duplicate display names are allowed; clearing cookies or changing browsers or devices creates a separate player.
- Remove login, registration, email, password, logout, bearer-token, refresh-token, and browser-storage authentication from the product.
- Preserve all existing `users`, `questions`, `user_progress`, `study_sessions`, and `user_responses` data and question IDs.
- Challenge contains exactly 20 questions: three from each domain 1–6 and two from domain 7.
- Challenge score is `correct * 5`; wrong is `20 - correct`; only a strictly higher completed score replaces a player's record.
- The leaderboard returns only `rank`, `name`, `score`, `correct`, and `wrong`; equal scores use dense ranking.
- Normal study sessions never update challenge records.
- Keep one backend worker and do not implement active-session persistence or restart recovery.
- The UI uses the approved Signal / Editorial direction and works at a 360px viewport with visible keyboard focus and WCAG AA contrast.

---

### Task 0: Preserve the verified CCNA baseline

**Files:**
- Modify: `.gitignore`
- Stage: the existing backend grading, extraction, test, frontend, Docker, Nginx, README, and verification changes currently reported by `git status --short`
- Exclude: `.superpowers/`

**Interfaces:**
- Consumes: the already verified 1,546-question CCNA application and production deployment changes.
- Produces: a clean Git baseline before guest identity changes begin.

- [x] **Step 1: Ignore the local brainstorming runtime**

Add this repository-local line to `.gitignore`:

```gitignore
.superpowers/
```

- [x] **Step 2: Re-run the existing baseline checks**

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build && cd ..
JWT_SECRET_KEY=test-only-secret bash tests/test-production-compose.sh
git diff --check
```

Expected: 218 passed and one optional skip in the backend baseline, 12 frontend tests pass, the Next build succeeds, production Compose checks pass, and no whitespace errors remain. If counts change because the feature work has already begun, stop and reconcile the working tree before this commit.

- [x] **Step 3: Review and commit only the completed baseline**

```bash
git add -A
git status --short
git diff --cached --check
git commit -m "feat: complete and productionize CCNA quiz"
```

Confirm `git status --short` contains no `.superpowers/` path before committing. The implementation plan and architecture spec are already committed separately.

### Task 1: Add the guest and challenge schema

**Files:**
- Modify: `backend/app/database.py`
- Modify: `backend/tests/test_database.py`

**Interfaces:**
- Consumes: Existing `init_db() -> None` and SQLite `users(id)` ownership.
- Produces: `guest_players(user_id, public_id, display_name, created_at, last_seen_at)` and `challenge_records(id, user_id, score, correct_count, wrong_count, completed_at)`.

- [x] **Step 1: Write schema tests that preserve the existing database**

Add tests that create a legacy database, run `init_db()`, and assert both new tables, foreign keys, checks, and indexes exist without changing an existing question ID:

```python
@pytest.mark.asyncio
async def test_init_adds_guest_and_challenge_tables_without_replacing_data():
    await init_db()
    async with get_db() as db:
        await db.execute("INSERT INTO users(id,email,password_hash,name) VALUES(41,'old@example.com','old','Old')")
        await db.execute("INSERT INTO questions(id,source_book,source_chapter,book_title,domain,question_text,option_a,option_b,option_c,option_d,correct_option,explanation) VALUES(91,'book','1','Book',1,'Q','A','B','C','D','A','E')")
        await db.commit()
    await init_db()
    async with get_db() as db:
        tables = {row[0] for row in await (await db.execute("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()}
        assert {'guest_players', 'challenge_records'} <= tables
        assert await (await db.execute("SELECT id FROM questions WHERE id=91")).fetchone()
```

- [x] **Step 2: Run the focused schema test and confirm it fails**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_database.py -q`

Expected: FAIL because `guest_players` and `challenge_records` do not exist.

- [x] **Step 3: Add the two tables and ordering index**

Extend `init_db()` with additive `CREATE TABLE IF NOT EXISTS` statements:

```python
await db.execute("""
    CREATE TABLE IF NOT EXISTS guest_players (
        user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        public_id TEXT UNIQUE NOT NULL,
        display_name TEXT NOT NULL CHECK(length(trim(display_name)) BETWEEN 2 AND 24),
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
""")
await db.execute("""
    CREATE TABLE IF NOT EXISTS challenge_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
        correct_count INTEGER NOT NULL CHECK(correct_count BETWEEN 0 AND 20),
        wrong_count INTEGER NOT NULL CHECK(wrong_count BETWEEN 0 AND 20),
        completed_at TIMESTAMP NOT NULL,
        CHECK(correct_count + wrong_count = 20),
        CHECK(score = correct_count * 5)
    )
""")
await db.execute("CREATE INDEX IF NOT EXISTS idx_challenge_rank ON challenge_records(score DESC, completed_at ASC, id ASC)")
```

- [x] **Step 4: Run schema and full backend tests**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_database.py -q`

Expected: PASS.

Run: `PYTHONPATH=backend .venv/bin/python -m pytest -q`

Expected: Existing suite remains green.

- [x] **Step 5: Commit the additive migration**

```bash
git add backend/app/database.py backend/tests/test_database.py
git commit -m "feat: add guest player and challenge schema"
```

### Task 2: Create signed-cookie guest identity

**Files:**
- Create: `backend/app/guest.py`
- Create: `backend/app/routers/players.py`
- Create: `backend/tests/test_players.py`
- Modify: `backend/app/config.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `create_player_cookie(public_id: str) -> str`, `get_current_player(cookie: str | None) -> dict`, `POST /api/player`, and `GET /api/player/me`.
- Produces fixture: `player(client, name='Rifqy') -> dict` for backend tests.
- Cookie name: `ccna_player`; lifetime: 31,536,000 seconds.

- [x] **Step 1: Write guest creation and cookie verification tests**

Create tests for trimming, duplicate names, invalid lengths/control characters, cookie flags, returning identity, tampering, and the absence of private fields:

```python
@pytest.mark.asyncio
async def test_create_player_sets_secure_cookie_and_me_returns_public_profile(client):
    response = await client.post('/api/player', json={'name': '  Rifqy  '})
    assert response.status_code == 201
    assert response.json() == {'name': 'Rifqy'}
    cookie = response.headers['set-cookie']
    assert 'ccna_player=' in cookie
    assert 'HttpOnly' in cookie and 'Secure' in cookie and 'SameSite=lax' in cookie
    assert (await client.get('/api/player/me')).json() == {'name': 'Rifqy'}

@pytest.mark.asyncio
async def test_duplicate_display_names_create_distinct_players(client):
    first = await client.post('/api/player', json={'name': 'Player'})
    first_cookie = first.cookies['ccna_player']
    second = await client.post('/api/player', json={'name': 'Player'})
    assert second.status_code == 201
    assert second.cookies['ccna_player'] != first_cookie
```

- [x] **Step 2: Run the new tests and confirm missing routes fail**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_players.py -q`

Expected: FAIL with 404 responses for `/api/player`.

- [x] **Step 3: Add guest configuration and Pydantic contracts**

Add `PLAYER_COOKIE_NAME = "ccna_player"`, `PLAYER_COOKIE_MAX_AGE = 31_536_000`, and `PLAYER_COOKIE_DOMAIN = "quiz.email2.my.id"` to `Settings`. Add these models:

```python
class PlayerCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=24)

    @field_validator('name')
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = value.strip()
        if not 2 <= len(value) <= 24 or any(unicodedata.category(char).startswith('C') for char in value):
            raise ValueError('Name must contain 2–24 visible characters')
        return value

class PlayerResponse(BaseModel):
    name: str
```

- [x] **Step 4: Implement cookie signing and guest lookup**

Use the existing JWT secret with a dedicated token type and no bearer headers:

```python
def create_player_cookie(public_id: str) -> str:
    settings = get_settings()
    payload = {'sub': public_id, 'type': 'guest', 'exp': datetime.now(timezone.utc) + timedelta(seconds=settings.PLAYER_COOKIE_MAX_AGE)}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

async def get_current_player(ccna_player: str | None = Cookie(default=None)) -> dict:
    if not ccna_player:
        raise HTTPException(status_code=401, detail='Player identity required')
    try:
        payload = jwt.decode(ccna_player, get_settings().JWT_SECRET_KEY, algorithms=[get_settings().JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail='Invalid player identity')
    if payload.get('type') != 'guest' or not isinstance(payload.get('sub'), str):
        raise HTTPException(status_code=401, detail='Invalid player identity')
    async with get_db() as db:
        row = await (await db.execute(
            'SELECT u.id, g.public_id, g.display_name AS name FROM guest_players g JOIN users u ON u.id=g.user_id WHERE g.public_id=?',
            (payload['sub'],),
        )).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail='Player identity not found')
        await db.execute('UPDATE guest_players SET last_seen_at=CURRENT_TIMESTAMP WHERE user_id=?', (row['id'],))
        await db.commit()
        return dict(row)
```

- [x] **Step 5: Implement player creation as one transaction**

Generate `public_id = uuid4().hex`, use `guest-{public_id}@internal.invalid`, hash a random server-only password, insert `users` and `guest_players`, commit, and set the cookie:

```python
response.set_cookie(
    key=settings.PLAYER_COOKIE_NAME,
    value=create_player_cookie(public_id),
    max_age=settings.PLAYER_COOKIE_MAX_AGE,
    secure=True,
    httponly=True,
    samesite='lax',
    domain=settings.PLAYER_COOKIE_DOMAIN,
    path='/',
)
```

For tests, override `PLAYER_COOKIE_DOMAIN=None` and use `AsyncClient(..., base_url='https://test')` so HTTPX accepts and returns the secure cookie.

- [x] **Step 6: Mount the player router and remove legacy auth exposure**

Export `player_router` from `backend/app/routers/__init__.py`, include it in `main.py`, remove `app.include_router(auth_router)`, and remove permissive wildcard CORS because browser API traffic is same-origin through Next.js/Nginx.

- [x] **Step 7: Run guest and legacy-route tests**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_players.py backend/tests/test_auth.py -q`

Expected: guest tests PASS; replace legacy auth behavior tests with one assertion that `/api/auth/login`, `/register`, `/refresh`, and `/me` return 404.

- [x] **Step 8: Commit guest identity**

```bash
git add backend/app/guest.py backend/app/routers/players.py backend/app/config.py backend/app/models.py backend/app/routers/__init__.py backend/app/main.py backend/tests/conftest.py backend/tests/test_players.py backend/tests/test_auth.py
git commit -m "feat: replace account auth with guest identity"
```

### Task 3: Move all study ownership to guest cookies

**Files:**
- Modify: `backend/app/routers/questions.py`
- Modify: `backend/app/routers/sessions.py`
- Modify: `backend/app/routers/stats.py`
- Modify: `backend/tests/conftest.py`
- Modify: `backend/tests/test_questions.py`
- Modify: `backend/tests/test_sessions.py`
- Modify: `backend/tests/test_answer_submission.py`
- Modify: `backend/tests/test_correctness_mastery.py`
- Modify: `backend/tests/test_mastery_stats.py`
- Modify: `backend/tests/test_session_question_identity.py`
- Modify: `backend/tests/test_study_contract.py`

**Interfaces:**
- Consumes: `get_current_player() -> {'id': int, 'public_id': str, 'name': str}` from Task 2.
- Produces: Existing question, session, and stats APIs authenticated only by the `ccna_player` cookie.

- [x] **Step 1: Replace the shared auth fixture with a guest fixture**

Create a helper that establishes the cookie jar and returns the public profile:

```python
@pytest_asyncio.fixture
async def player(client):
    response = await client.post('/api/player', json={'name': 'Test Player'})
    assert response.status_code == 201
    return response.json()
```

Update endpoint tests to depend on `player` and remove `headers=auth_headers`.

- [x] **Step 2: Add guest isolation coverage**

Use two independent `AsyncClient` instances. Start a session with the first, then assert the second receives 404 for its next-question route and cannot submit an answer.

```python
assert (await first.post('/api/sessions/start', json={'count': 1})).status_code == 200
session_id = response.json()['session_id']
assert (await second.get(f'/api/sessions/{session_id}/next')).status_code == 404
```

- [x] **Step 3: Run a protected-route test and confirm bearer-free requests fail before conversion**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_sessions.py::test_dashboard_returns_stats -q`

Expected: FAIL because the route still expects a bearer token.

- [x] **Step 4: Replace route dependencies**

In all three routers, replace:

```python
from ..auth import get_current_user
current_user: dict = Depends(get_current_user)
```

with:

```python
from ..guest import get_current_player
current_user: dict = Depends(get_current_player)
```

Keep every `current_user['id']` query and session-cache ownership check intact.

- [x] **Step 5: Run all study tests**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_questions.py backend/tests/test_sessions.py backend/tests/test_answer_submission.py backend/tests/test_correctness_mastery.py backend/tests/test_mastery_stats.py backend/tests/test_session_question_identity.py backend/tests/test_study_contract.py -q`

Expected: PASS, including guest isolation, stale-answer, grading, mastery, and concurrent progress cases.

- [x] **Step 6: Commit guest-owned study routes**

```bash
git add backend/app/routers/questions.py backend/app/routers/sessions.py backend/app/routers/stats.py backend/tests/conftest.py backend/tests/test_questions.py backend/tests/test_sessions.py backend/tests/test_answer_submission.py backend/tests/test_correctness_mastery.py backend/tests/test_mastery_stats.py backend/tests/test_session_question_identity.py backend/tests/test_study_contract.py
git commit -m "feat: authorize study routes with guest cookies"
```

### Task 4: Add the fixed challenge and public leaderboard

**Files:**
- Create: `backend/app/services/challenge.py`
- Create: `backend/app/routers/leaderboard.py`
- Create: `backend/tests/test_challenge.py`
- Create: `backend/tests/test_leaderboard.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/routers/sessions.py`
- Modify: `backend/app/routers/__init__.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `select_challenge_questions(questions: list[dict], rng: random.Random | None = None) -> list[dict]`.
- Produces: `POST /api/sessions/challenge`, `GET /api/leaderboard`.
- Extends: `SessionSummary` with optional `score: int`, `wrong_count: int`, and `rank: int` for completed challenges.
- Produces: `LeaderboardEntry(rank: int, name: str, score: int, correct: int, wrong: int)`.

- [x] **Step 1: Write pure challenge-selection tests**

```python
def test_challenge_has_fixed_domain_distribution():
    questions = [{'id': domain * 100 + i, 'domain': domain} for domain in range(1, 8) for i in range(5)]
    selected = select_challenge_questions(questions, random.Random(7))
    assert len(selected) == 20
    assert Counter(q['domain'] for q in selected) == {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2}
    assert len({q['id'] for q in selected}) == 20
```

Add a test asserting `ChallengePoolError` when any domain is undersized.

- [x] **Step 2: Run the selection tests and confirm they fail**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_challenge.py -q`

Expected: FAIL because the challenge service does not exist.

- [x] **Step 3: Implement deterministic, exact selection**

```python
REQUIRED = {1: 3, 2: 3, 3: 3, 4: 3, 5: 3, 6: 3, 7: 2}

def select_challenge_questions(questions: list[dict], rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.SystemRandom()
    pools = {domain: [q for q in questions if q['domain'] == domain] for domain in REQUIRED}
    missing = {domain: count - len(pools[domain]) for domain, count in REQUIRED.items() if len(pools[domain]) < count}
    if missing:
        raise ChallengePoolError(missing)
    selected = [q for domain, count in REQUIRED.items() for q in rng.sample(pools[domain], count)]
    rng.shuffle(selected)
    return selected
```

- [x] **Step 4: Write API tests for fixed challenge start and authoritative completion**

Seed at least three questions in domains 1–6 and two in domain 7. Assert `POST /api/sessions/challenge` accepts no count/domain, returns total 20, partial completion is rejected, and a completed session returns `score`, `wrong_count`, and `rank` derived from submitted answers.

```python
started = await client.post('/api/sessions/challenge')
assert started.json()['total_questions'] == 20
partial = await client.post(f"/api/sessions/{started.json()['session_id']}/complete")
assert partial.status_code == 409
```

- [x] **Step 5: Implement challenge start and cache metadata**

Add the static `/challenge` route before `/{session_id}` routes. Query domains 1–7, call `select_challenge_questions`, insert `study_sessions(session_type='challenge')`, and cache `session_type: 'challenge'`. Also add `session_type` to regular cache entries.

- [x] **Step 6: Implement transactional best-result completion**

For challenges, require `cache['index'] == 20`, calculate server-side fields, and execute the session update and conditional upsert before one commit:

```sql
INSERT INTO challenge_records(user_id, score, correct_count, wrong_count, completed_at)
VALUES (?, ?, ?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
  score=excluded.score,
  correct_count=excluded.correct_count,
  wrong_count=excluded.wrong_count,
  completed_at=excluded.completed_at
WHERE excluded.score > challenge_records.score
```

Compute dense rank with `1 + COUNT(DISTINCT score)` for scores above the player's stored best. Do not update `challenge_records` for any other session type.

- [x] **Step 7: Write leaderboard tests**

Insert scores 100, 90, 90, and 75 under duplicate-capable names. Assert the response ranks are 1, 2, 2, 3; tie order follows `completed_at, id`; and every row has exactly these keys:

```python
assert set(row) == {'rank', 'name', 'score', 'correct', 'wrong'}
```

Also test that an equal/lower score keeps the original record and a higher score replaces it.

- [x] **Step 8: Implement and mount the public leaderboard router**

Use a SQL `DENSE_RANK() OVER (ORDER BY score DESC)` subquery joined to `guest_players`, order by rank then completion time then record ID, and map `correct_count`/`wrong_count` to the approved response names. Do not add a player ID, email, timestamp, or current-player flag.

- [x] **Step 9: Run challenge, leaderboard, and full backend suites**

Run: `PYTHONPATH=backend .venv/bin/python -m pytest backend/tests/test_challenge.py backend/tests/test_leaderboard.py -q`

Expected: PASS.

Run: `PYTHONPATH=backend .venv/bin/python -m pytest -q`

Expected: PASS with no regressions.

- [x] **Step 10: Commit challenge behavior**

```bash
git add backend/app/services/challenge.py backend/app/routers/leaderboard.py backend/app/models.py backend/app/routers/sessions.py backend/app/routers/__init__.py backend/app/main.py backend/tests/test_challenge.py backend/tests/test_leaderboard.py
git commit -m "feat: add fixed challenge leaderboard"
```

### Task 5: Replace frontend authentication with player identity

**Files:**
- Create: `frontend/lib/player-context.tsx`
- Create: `frontend/tests/player-context.test.tsx`
- Create: `frontend/app/quiz/layout.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/tests/api.test.ts`

**Interfaces:**
- Produces: `PlayerProvider`, `usePlayer()`, `createPlayer(name: string)`, `refreshPlayer()`, and `clearPlayer()`.
- Produces: `cookieFetch<T>(path: string, init?: ApiInit) -> Promise<T>` using `credentials: 'same-origin'` and no bearer token. Existing token methods remain temporarily available to the old route tree until Task 7 moves it atomically.
- Produces: `api.player.create`, `api.player.me`, `api.sessions.challenge`, and `api.leaderboard.list`.

- [x] **Step 1: Rewrite API tests around cookie credentials**

```typescript
it('uses same-origin cookies without authorization headers', async () => {
  const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('[]'));
  await api.player.me();
  expect(fetcher).toHaveBeenCalledWith('/api/player/me', expect.objectContaining({
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json'},
  }));
});
```

Remove the refresh-token retry test and add contracts for player creation, challenge start without a body, and leaderboard reads.

- [x] **Step 2: Run the API tests and confirm the old signature fails**

Run: `cd frontend && npm test -- tests/api.test.ts`

Expected: FAIL because player API methods do not exist.

- [x] **Step 3: Simplify the API client**

Add the cookie-specific request path without changing the old route tree yet:

```typescript
type ApiInit = {body?: object; method?: 'GET' | 'POST'};

export async function cookieFetch<T>(path: string, init: ApiInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: init.method ?? (init.body ? 'POST' : 'GET'),
    credentials: 'same-origin',
    headers: {'Content-Type': 'application/json'},
    ...(init.body ? {body: JSON.stringify(init.body)} : {}),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, formatDetail(error.detail));
  }
  return response.status === 204 ? null as T : response.json();
}
```

Add cookie-backed `player`, `sessions.challenge`, and `leaderboard` methods. Keep existing token-backed study methods until Task 7, when their callers are converted together. Define `Player`, `ChallengeSummary`, and `LeaderboardEntry` with the exact backend property names.

- [x] **Step 4: Write player-provider tests**

Test the loading state, recognized returning player, first-visit 401, successful name creation, inline creation error, and invalidated-cookie recovery. Assert that no localStorage method is called.

- [x] **Step 5: Implement `PlayerProvider`**

On mount, call `api.player.me()`. Treat a 401 `ApiError` as `player=null`, keep other errors as a retryable error, and expose:

```typescript
interface PlayerContextValue {
  player: Player | null;
  loading: boolean;
  error: string | null;
  createPlayer(name: string): Promise<void>;
  refreshPlayer(): Promise<void>;
  clearPlayer(): void;
}
```

Wrap only `frontend/app/quiz/layout.tsx` in `PlayerProvider`, because the apex portfolio does not expose `/api/` and does not need player state. Leave the old root provider in place until Task 7 replaces the old route tree in one buildable change.

- [x] **Step 6: Run focused and full frontend tests**

Run: `cd frontend && npm test -- tests/api.test.ts tests/player-context.test.tsx`

Expected: PASS.

Run: `cd frontend && npm test && npm run build`

Expected: All existing and new tests pass, and the intermediate branch still builds.

- [x] **Step 7: Commit the frontend identity boundary**

```bash
git add frontend/lib/api.ts frontend/lib/player-context.tsx frontend/app/quiz/layout.tsx frontend/tests/api.test.ts frontend/tests/player-context.test.tsx docs/superpowers/plans/2026-09-06-portfolio-guest-quiz.md
git commit -m "feat: use guest identity in frontend"
```

### Task 6: Build the Signal / Editorial portfolio and writeups index

**Files:**
- Create: `frontend/app/portfolio/page.tsx`
- Create: `frontend/app/portfolio/writeups/page.tsx`
- Create: `frontend/components/SiteHeader.tsx`
- Create: `frontend/lib/site-content.ts`
- Create: `frontend/tests/portfolio.test.tsx`
- Modify: `frontend/app/globals.css`
- Modify: `frontend/app/layout.tsx`

**Interfaces:**
- Produces: portfolio internal route `/portfolio`, writeup internal route `/portfolio/writeups`, and absolute navigation to `https://quiz.email2.my.id/`.
- Produces content: name `Rifqy`, role line `Networking and security student`, project entries `CCNA Quiz` and `CTF Writeups`.

- [x] **Step 1: Write portfolio rendering tests**

```typescript
it('presents Rifqy and the two primary work areas', () => {
  render(<PortfolioPage />);
  expect(screen.getByRole('heading', {name: 'Rifqy'})).toBeTruthy();
  expect(screen.getByRole('link', {name: /CTF Writeups/i}).getAttribute('href')).toBe('/writeups');
  expect(screen.getByRole('link', {name: /CCNA Quiz/i}).getAttribute('href')).toBe('https://quiz.email2.my.id/');
});

it('shows an honest empty writeup index', () => {
  render(<WriteupsPage />);
  expect(screen.getByText('0 published')).toBeTruthy();
  expect(screen.getByText(/writeups will appear here/i)).toBeTruthy();
});
```

- [x] **Step 2: Run the portfolio test and confirm routes are missing**

Run: `cd frontend && npm test -- tests/portfolio.test.tsx`

Expected: FAIL because the portfolio pages do not exist.

- [x] **Step 3: Add repository-owned site content**

```typescript
export const profile = {
  name: 'Rifqy',
  role: 'Networking and security student',
  introduction: 'Building network labs, documenting CTF work, and studying for the CCNA.',
};

export const work = [
  {index: '01', title: 'CTF Writeups', description: 'Technical notes from security challenges.', href: '/writeups'},
  {index: '02', title: 'CCNA Quiz', description: 'A question-driven lab for CCNA study and review.', href: 'https://quiz.email2.my.id/'},
];
```

- [x] **Step 4: Implement semantic portfolio pages and header**

Use one `<h1>`, a `<nav aria-label="Primary">`, `<main>`, ordered work entries, and a visible skip link. The empty writeups page reports `0 published` without inventing projects or achievements.

- [x] **Step 5: Implement Signal / Editorial design tokens**

Define CSS variables such as `--paper: #f4f1e8`, `--ink: #151515`, `--muted: #67645d`, `--rule: #c9c4b8`, and `--signal: #e23d28`. Use a system serif/sans pairing, a readable 65-character article measure, thin rules, restrained red actions, `:focus-visible`, `prefers-reduced-motion`, and a 360px media query.

- [x] **Step 6: Run portfolio tests and production build**

Run: `cd frontend && npm test -- tests/portfolio.test.tsx && npm run build`

Expected: PASS; both internal routes appear in the Next build output.

- [x] **Step 7: Commit the portfolio**

```bash
git add frontend/app/portfolio frontend/components/SiteHeader.tsx frontend/lib/site-content.ts frontend/tests/portfolio.test.tsx frontend/app/globals.css frontend/app/layout.tsx
git commit -m "feat: add editorial portfolio and writeups"
```

### Task 7: Move and redesign the quiz experience

**Files:**
- Create: `frontend/app/quiz/page.tsx`
- Create: `frontend/app/quiz/domains/page.tsx`
- Create: `frontend/app/quiz/domains/[id]/page.tsx`
- Create: `frontend/app/quiz/study/page.tsx`
- Create: `frontend/app/quiz/study/[sessionId]/page.tsx`
- Create: `frontend/app/quiz/stats/page.tsx`
- Create: `frontend/app/quiz/challenge/page.tsx`
- Create: `frontend/app/quiz/leaderboard/page.tsx`
- Create: `frontend/components/NamePrompt.tsx`
- Create: `frontend/components/QuizNav.tsx`
- Create: `frontend/components/LeaderboardTable.tsx`
- Create: `frontend/components/PlayerGate.tsx`
- Create: `frontend/components/SessionRunner.tsx`
- Create: `frontend/tests/name-prompt.test.tsx`
- Create: `frontend/tests/challenge-page.test.tsx`
- Create: `frontend/tests/leaderboard-page.test.tsx`
- Modify: `frontend/tests/forms.test.tsx`
- Modify: `frontend/tests/session.test.tsx`
- Delete: `frontend/app/page.tsx`
- Delete: `frontend/app/dashboard/page.tsx`
- Delete: `frontend/app/domains/page.tsx`
- Delete: `frontend/app/domains/[id]/page.tsx`
- Delete: `frontend/app/study/page.tsx`
- Delete: `frontend/app/study/[sessionId]/page.tsx`
- Delete: `frontend/app/stats/page.tsx`
- Delete: `frontend/components/NavBar.tsx`
- Delete: `frontend/lib/auth-context.tsx`
- Delete: `frontend/tests/auth.test.tsx`
- Delete: `frontend/app/login/page.tsx`
- Delete: `frontend/app/register/page.tsx`
- Modify: `frontend/app/layout.tsx`
- Modify: `frontend/lib/api.ts`

**Interfaces:**
- Consumes: `usePlayer()`, token-free `api`, `ChallengeSummary`, and `LeaderboardEntry` from Task 5.
- Produces: internal quiz route tree rooted at `/quiz`, including `/quiz/challenge` and `/quiz/leaderboard`.

- [x] **Step 1: Write first-visit and returning-player UI tests**

Mock `usePlayer()`. When `player` is null, assert the name form is the only primary content; when a player exists, assert the quiz dashboard, study actions, Challenge, Leaderboard, Portfolio, and Writeups links appear. Assert the rendered app contains no login, register, email, password, or logout controls.

- [x] **Step 2: Implement the name prompt**

Use a labeled text input with `minLength={2}`, `maxLength={24}`, `autoComplete="nickname"`, pending state, and inline error. Submit `name.trim()` through `createPlayer`. Keep typed input after failure.

- [x] **Step 3: Convert and move the existing quiz pages**

Move dashboard, domain, study, session, and stats behavior under `frontend/app/quiz`. Replace `useAuth()` checks and token arguments with `usePlayer()` and cookie-backed API calls, then remove `AuthProvider` from the root layout, delete the auth context/tests/pages, and simplify every study API method to omit tokens. If `player` becomes null after a 401, render `NamePrompt`. Preserve question grading, confidence buttons, explanations, mastery, diagrams, and the volatile `sessionCounts` map.

- [x] **Step 4: Add expired-session recovery tests and behavior**

Mock a 404 from `api.sessions.next()` and assert the session page says `This session expired when the quiz service restarted.` with a link to `/study`. Do not store the queue, current index, or responses in localStorage, sessionStorage, IndexedDB, or a new database table.

- [x] **Step 5: Write and implement challenge UI tests**

Assert one button calls `api.sessions.challenge()`, reports progress out of 20, reuses the quiz card for answers, and renders backend completion values:

```typescript
expect(screen.getByText('85')).toBeTruthy();
expect(screen.getByText('17 correct')).toBeTruthy();
expect(screen.getByText('3 wrong')).toBeTruthy();
expect(screen.getByText('Rank 4')).toBeTruthy();
```

Provide `Try another challenge` and `View leaderboard` actions.

- [x] **Step 6: Write and implement leaderboard UI tests**

Render rows with the exact column headings `Rank`, `Name`, `Score`, `Correct`, and `Wrong`. Test dense tied ranks from mocked API data and an error state with a `Retry` button. Do not infer or highlight the current player.

- [x] **Step 7: Apply the editorial visual system to quiz components**

Replace inline dashboard and navigation styles with reusable classes. Use paper panels, numbered domain rows, thin rules, signal-red selection markers, textual correct/wrong icons, and tabular numerals for scores. Ensure answer state is expressed with icon/text plus color.

- [x] **Step 8: Run all frontend tests and build**

Run: `cd frontend && npm test`

Expected: PASS with the obsolete auth tests removed and all study behavior retained.

Run: `cd frontend && npm run build`

Expected: PASS with no TypeScript or route collision errors.

- [x] **Step 9: Commit the complete quiz UI**

```bash
git add frontend/app/quiz/page.tsx frontend/app/quiz/domains/page.tsx frontend/app/quiz/domains/[id]/page.tsx frontend/app/quiz/study/page.tsx frontend/app/quiz/study/[sessionId]/page.tsx frontend/app/quiz/stats/page.tsx frontend/app/quiz/challenge/page.tsx frontend/app/quiz/leaderboard/page.tsx frontend/components/NamePrompt.tsx frontend/components/QuizNav.tsx frontend/components/LeaderboardTable.tsx frontend/components/QuizCard.tsx frontend/components/StreakCalendar.tsx frontend/tests/name-prompt.test.tsx frontend/tests/challenge-page.test.tsx frontend/tests/leaderboard-page.test.tsx frontend/tests/forms.test.tsx frontend/tests/session.test.tsx frontend/tests/auth.test.tsx frontend/lib/api.ts frontend/lib/auth-context.tsx frontend/app/layout.tsx frontend/app/page.tsx frontend/app/dashboard/page.tsx frontend/app/domains/page.tsx frontend/app/domains/[id]/page.tsx frontend/app/study/page.tsx frontend/app/study/[sessionId]/page.tsx frontend/app/stats/page.tsx frontend/app/login/page.tsx frontend/app/register/page.tsx frontend/components/NavBar.tsx
git commit -m "feat: redesign quiz for guest players"
```

### Task 8: Route the apex and quiz hosts safely

**Files:**
- Create: `frontend/lib/host-routing.ts`
- Create: `frontend/middleware.ts`
- Create: `frontend/tests/host-routing.test.ts`
- Modify: `frontend/next.config.mjs`
- Modify: `nginx/nginx.conf`
- Modify: `nginx/nginx.production.conf`
- Modify: `tests/test-production-compose.sh`

**Interfaces:**
- Produces: `routeForHost(host: string, pathname: string) -> {kind: 'rewrite' | 'redirect'; destination: string}`.
- Public hosts: `email2.my.id` and `quiz.email2.my.id`.
- Development hosts: `localhost` maps to portfolio; `quiz.localhost` maps to quiz.

- [x] **Step 1: Write pure host-routing tests**

```typescript
expect(routeForHost('email2.my.id', '/')).toEqual({kind: 'rewrite', destination: '/portfolio'});
expect(routeForHost('email2.my.id', '/writeups')).toEqual({kind: 'rewrite', destination: '/portfolio/writeups'});
expect(routeForHost('quiz.email2.my.id', '/')).toEqual({kind: 'rewrite', destination: '/quiz'});
expect(routeForHost('email2.my.id', '/challenge')).toEqual({kind: 'redirect', destination: 'https://quiz.email2.my.id/challenge'});
expect(routeForHost('quiz.email2.my.id', '/writeups')).toEqual({kind: 'redirect', destination: 'https://email2.my.id/writeups'});
```

Ignore `/_next`, `/favicon.ico`, and static public assets.

- [x] **Step 2: Run host-routing tests and confirm the module is missing**

Run: `cd frontend && npm test -- tests/host-routing.test.ts`

Expected: FAIL because `host-routing.ts` does not exist.

- [x] **Step 3: Implement the pure routing table and middleware adapter**

Read `request.headers.get('host')`, remove its port, call `routeForHost`, then return `NextResponse.rewrite(new URL(destination, request.url))` or `NextResponse.redirect(destination)`. Configure the matcher to exclude `api`, `_next/static`, `_next/image`, and files with extensions.

- [x] **Step 4: Update development routing**

Keep the same-origin `/api/:path*` Next rewrite to `INTERNAL_API_URL`. Document `http://localhost:3000` for portfolio and `http://quiz.localhost:3000` for quiz. Ensure middleware leaves `/api` untouched for the Next proxy.

- [x] **Step 5: Write production Nginx assertions**

Extend `tests/test-production-compose.sh` with `nginx -t` against the mounted production config and text assertions that both server names exist, apex `/api/` returns 404, quiz `/api/` proxies to backend, and both use the same expanded certificate.

- [x] **Step 6: Split Nginx host behavior**

The port 80 block accepts both names for ACME and redirects to the original host. Add separate TLS blocks:

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name email2.my.id;
    location /api/ { return 404; }
    location / { proxy_pass http://frontend; }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name quiz.email2.my.id;
    location /api/ { proxy_pass http://backend; }
    location / { proxy_pass http://frontend; }
}
```

Retain existing proxy headers, security headers, WebSocket support, ACME webroot, and `/etc/letsencrypt/live/email2.my.id/...` certificate paths.

- [x] **Step 7: Run routing, Compose, and build checks**

Run: `cd frontend && npm test -- tests/host-routing.test.ts && npm run build`

Run: `JWT_SECRET_KEY=test-only-secret bash tests/test-production-compose.sh`

Expected: both commands PASS.

- [x] **Step 8: Commit host routing**

```bash
git add frontend/lib/host-routing.ts frontend/middleware.ts frontend/tests/host-routing.test.ts frontend/next.config.mjs nginx/nginx.conf nginx/nginx.production.conf tests/test-production-compose.sh
git commit -m "feat: route portfolio and quiz hosts"
```

### Task 9: Document, migrate, deploy, and verify production

**Files:**
- Modify: `README.md`
- Modify: `docs/verification.md`
- Modify: `.env.example`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.production.yml`

**Interfaces:**
- Consumes: completed Tasks 1–8 and the existing deployment at `/opt/ccna-quiz` on `2407:6ac0:3:9d:abcd::1dc`.
- Produces: live apex portfolio, live quiz subdomain, expanded TLS certificate, migrated production database, and final verification record.

- [ ] **Step 1: Update configuration and documentation**

Document `PLAYER_COOKIE_NAME=ccna_player`, `PLAYER_COOKIE_MAX_AGE=31536000`, and `PLAYER_COOKIE_DOMAIN=quiz.email2.my.id`; pass them to the backend container. Replace registration instructions and legacy auth API rows with the name-prompt, challenge, and leaderboard flows. Keep the existing active-session persistence warning verbatim in meaning.

- [ ] **Step 2: Run the complete local verification suite**

Run:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
cd frontend && npm test && npm run build && cd ..
JWT_SECRET_KEY=test-only-secret docker compose config --quiet
JWT_SECRET_KEY=test-only-secret bash tests/test-production-compose.sh
git diff --check
```

Expected: all tests and builds pass; no whitespace errors.

- [ ] **Step 3: Record pre-migration production counts and back up SQLite**

Over the established SSH connection, stop only the backend long enough for a consistent copy, then restart it:

```bash
ssh root@2407:6ac0:3:9d:abcd::1dc 'cd /opt/ccna-quiz && docker compose -f docker-compose.yml -f docker-compose.production.yml stop backend && cp -p data/ccna.db data/ccna.db.pre-guest-20260906 && docker compose -f docker-compose.yml -f docker-compose.production.yml start backend'
```

Query and record counts for questions, users, user_progress, study_sessions, user_responses, multi-answer questions, and questions with diagrams. Confirm the backup file is nonempty.

- [ ] **Step 4: Create the quiz DNS record in Cloudflare**

Add `quiz` as an AAAA record pointing to `2407:6ac0:3:9d:abcd::1dc`, initially DNS-only for certificate issuance. Verify:

```bash
dig +short AAAA quiz.email2.my.id @1.1.1.1
```

Expected: `2407:6ac0:3:9d:abcd::1dc`.

- [ ] **Step 5: Expand the Let's Encrypt certificate**

With the HTTP ACME configuration active, run on the server:

```bash
certbot certonly --webroot -w /var/www/certbot --cert-name email2.my.id --expand -d email2.my.id -d quiz.email2.my.id --non-interactive --agree-tos
```

Run `certbot certificates` and confirm both names occur in the certificate before enabling the two TLS blocks.

- [ ] **Step 6: Deploy and run the additive migration**

Synchronize the reviewed repository files to `/opt/ccna-quiz` without replacing `/opt/ccna-quiz/data`, then rebuild:

```bash
ssh root@2407:6ac0:3:9d:abcd::1dc 'cd /opt/ccna-quiz && docker compose -f docker-compose.yml -f docker-compose.production.yml up --build -d'
```

The backend startup runs `init_db()` and creates the two new tables. Check container health and `docker compose logs --tail=100 backend nginx` for migration or routing errors.

- [ ] **Step 7: Enable the Cloudflare proxy and test both public hosts**

After direct HTTPS succeeds, enable the orange-cloud proxy for `quiz`. Verify:

```bash
curl -fsSI https://email2.my.id/
curl -fsSI https://email2.my.id/writeups
curl -fsSI https://quiz.email2.my.id/
curl -fsS https://quiz.email2.my.id/api/leaderboard
curl -sS -o /dev/null -w '%{http_code}\n' https://email2.my.id/api/leaderboard
```

Expected: 200 for both sites and the quiz leaderboard; 404 for the apex API.

- [ ] **Step 8: Perform a live guest challenge smoke test**

Use a temporary cookie jar to create a player, read `/api/player/me`, start a challenge, and confirm it reports 20 questions. Do not write a fabricated leaderboard result; complete the public leaderboard flow through the browser with real answer submissions. Confirm no login/register UI exists and an expired in-memory session shows the restart message.

- [ ] **Step 9: Verify final dataset and schema counts**

Confirm production still contains 1,546 questions, 134 multi-answer questions, and 112 diagram questions. Confirm existing user/progress/session/response counts did not decrease during migration. Record new `guest_players` and `challenge_records` counts separately in `docs/verification.md`.

- [ ] **Step 10: Verify renewal and responsive behavior**

Run `nginx -t`, `certbot renew --dry-run`, and inspect the systemd Certbot timer. Exercise the apex home, writeups, name prompt, study, challenge result, and leaderboard at 360px and desktop widths. Confirm no horizontal overflow, keyboard focus is visible, and both hosts use valid Cloudflare-fronted HTTPS.

- [ ] **Step 11: Write the final verification report**

Update `docs/verification.md` and report these headings to the user:

1. Schema decision.
2. Files changed.
3. Migration required.
4. Final dataset counts.
5. Test results.
6. Remaining backend gaps.

The remaining backend gaps must explicitly include active-session persistence, account recovery/cross-device identity, name ownership/moderation, and any issue discovered during live verification. Recommend the next development task and stop.

- [ ] **Step 12: Commit documentation and deployment evidence**

```bash
git add README.md docs/verification.md .env.example docker-compose.yml docker-compose.production.yml
git commit -m "docs: record portfolio quiz deployment"
```
