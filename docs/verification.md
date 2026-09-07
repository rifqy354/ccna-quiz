# Portfolio and guest quiz verification

Verified on 2026-09-07 against the isolated implementation branch and the
production host at `/opt/ccna-quiz`.

## Schema decision

The existing `users.id` remains the ownership key for study history. Two
additive tables were introduced:

- `guest_players` maps an internal user to a random public identifier and
  display name.
- `challenge_records` stores one best completed 20-question record per guest.

Existing questions, users, progress, sessions, responses, and question IDs were
preserved. Guest identity uses a signed, one-year, HTTP-only cookie. Production
sets `Secure`, `SameSite=Lax`, and domain `quiz.email2.my.id`; local HTTP
development uses a host-only non-Secure cookie.

## Files changed

- Backend: guest cookie identity, player routes, challenge selection and
  best-score storage, leaderboard route, guest authorization for study routes,
  additive schema, configuration, and regression tests.
- Frontend: editorial portfolio and writeups, name-first guest flow, quiz route
  tree, shared session runner, challenge and leaderboard pages, responsive
  Signal / Editorial styling, host middleware, and UI/API tests.
- Operations: split nginx host behavior, production configuration checks,
  Compose cookie settings, environment example, and deployment documentation.

## Migration required

No destructive or offline data migration is required. Backend startup creates
the two new tables and ranking index with `CREATE ... IF NOT EXISTS`.

Before deployment the backend was stopped briefly and
`data/ccna.db.pre-guest-20260906` was created. The backup is 1,499,136 bytes.
The migrated database retained every pre-existing row counted below.

## Final dataset counts

| Measure | Before | After |
|---|---:|---:|
| Questions | 1,546 | 1,546 |
| Users | 68 | 69 |
| User progress rows | 182 | 202 |
| Study sessions | 146 | 148 |
| User responses | 206 | 226 |
| Guest players | — | 1 |
| Challenge records | — | 1 |
| Multiple-answer questions | 134 | 134 |
| Questions with diagrams | 112 | 112 |

The one new user and guest player are the deployment smoke-test identity. It
started one abandoned challenge before the backend rebuild and then completed a
fresh 20-question challenge through the public API. Those real submissions
created 20 progress and response rows and a score of 15 (3 correct, 17 wrong).
No leaderboard row was inserted directly.

## Test results

- Backend: **232 passed, 1 optional real-book test skipped**; one Python
  `crypt` deprecation warning from passlib.
- Frontend: **28 passed** across 9 files.
- Next.js production compilation and type checking passed locally and in the
  production Docker image.
- Compose validation, production nginx text assertions, and nginx syntax checks
  passed.
- The production backend, frontend, and nginx containers are running; backend
  health is `healthy`; recent deployment logs contain no application errors.
- Guest smoke test: player creation and `/api/player/me` succeeded; Challenge
  returned `total_questions: 20`; all 20 answers were graded and completion
  produced score 15, 3 correct, 17 wrong, and rank 1.
- Public apex home, `/writeups`, quiz home, and quiz leaderboard return 200.
  Apex `/api/leaderboard` returns 404. Wrong-host page requests redirect to
  their canonical host.
- At 360px, the portfolio, writeups, name prompt, returning-player quiz home,
  challenge entry, and populated leaderboard have no horizontal overflow. The
  quiz home also passed at 1280px, and visible keyboard focus uses the
  signal-red outline.
- nginx configuration is valid. The Certbot timer is enabled and active.
  Renewal simulation passed for the certificate containing both
  `email2.my.id` and `quiz.email2.my.id`, valid through 2026-12-06.
- Cloudflare proxying is active for the quiz host. A forced Cloudflare-edge
  request returned 200 with `server: cloudflare` and a `cf-ray` header.

## Remaining backend gaps

- Active-session persistence and restart recovery remain intentionally
  unimplemented.
- Guest identity has no account recovery or cross-device transfer.
- Duplicate names are allowed; there is no name ownership, moderation, or abuse
  control.
- The legacy account-authentication modules remain in the source tree but are
  no longer mounted or reachable from the application.
- Challenge sessions abandoned before completion remain as ordinary incomplete
  session rows.

The recommended next development task is automated encrypted SQLite backups
with a tested restore procedure and basic uptime monitoring.
