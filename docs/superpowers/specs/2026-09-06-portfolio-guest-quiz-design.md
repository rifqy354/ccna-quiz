# Rifqy Portfolio and Guest CCNA Quiz Design

**Date:** 2026-09-06
**Status:** Approved design, awaiting document review
**Visual direction:** Signal / Editorial

## Purpose

Turn the current authenticated CCNA application into two related public experiences:

- `https://email2.my.id/` is Rifqy's portfolio.
- `https://email2.my.id/writeups` contains CTF writeups.
- `https://quiz.email2.my.id/` contains the CCNA study application and public challenge leaderboard.

The portfolio navigation links to CTF Writeups and CCNA Quiz. The quiz navigation links back to the portfolio and writeups. The quiz must not present login, registration, email, password, or logout controls.

## Product behavior

### Portfolio

The portfolio home page introduces Rifqy, highlights networking and security work, and presents selected projects. CTF writeups live at `/writeups`, with a list view suitable for adding individual writeup pages later. The CCNA Quiz link opens the quiz subdomain.

The initial release uses repository-owned content. It does not add a CMS or an administrator interface.

### Guest player identity

On the first visit to the quiz subdomain, the player sees a focused name prompt before the quiz interface. A display name must contain 2–24 visible characters after trimming. Control characters are rejected and output is escaped. Duplicate names are allowed.

`POST /api/player` creates the guest. The backend creates an inaccessible internal user row for compatibility with existing foreign keys, creates a guest profile, and sets a signed cookie. The internal email is generated under an invalid local namespace and the password hash is random and unusable. These values are never returned or shown.

The identity cookie is scoped to `quiz.email2.my.id`, uses `Secure`, `HttpOnly`, `SameSite=Lax`, and a long expiration. It contains an opaque guest identifier protected by the backend signing secret. `GET /api/player/me` resolves it and returns the player's public profile. Frontend API calls send credentials with same-origin requests.

Clearing cookies or using another browser or device creates a new guest. There is no account recovery or cross-device synchronization. An invalid, expired, or deleted identity returns the visitor to the name prompt.

Existing login and registration pages are removed from navigation and product routing. The frontend bearer-token provider and local-storage token flow are retired. The legacy auth router is no longer mounted by the application. Existing user rows remain in the database so their historical progress and response relationships are preserved.

### Study experience

Guest identity replaces bearer authentication on question, session, progress, and statistics endpoints. Existing ownership rules continue to use the internal `users.id`, so one guest cannot read or mutate another guest's study data.

Normal study modes continue to provide domain study, spaced repetition, answer explanations, mastery, and statistics. Their results never affect the public leaderboard.

### Challenge and leaderboard

Challenge is a distinct session type with exactly 20 questions:

- Three questions from each CCNA domain 1–6.
- Two questions from the practice-exam pool, currently represented by domain 7.

The backend owns selection and scoring. A challenge cannot accept a client-supplied count or domain. It fails clearly if any pool cannot supply its required number rather than returning a shorter challenge.

Each correct answer is worth five points. A completed challenge therefore produces:

- `score = correct * 5`, from 0 to 100.
- `wrong = 20 - correct`.

A challenge is eligible for the leaderboard only after all 20 questions have been answered and the backend completes the session. Abandoned and partially completed sessions create no leaderboard record.

The backend stores one best result per guest. Completion inserts the first result and atomically replaces it only when the new score is higher. An equal or lower score leaves the existing best result and its completion time unchanged.

`GET /api/leaderboard` is public and returns only:

- rank
- name
- score
- correct
- wrong

Ranks use dense ranking by score: equal scores share a rank, and the next distinct score receives the next consecutive rank. Rows with the same score are displayed by earliest best-result completion and then stable record ID. The first release does not identify or highlight the current guest in the public table because duplicate display names are allowed and the response contains no player identifier.

## Information architecture and routing

One Next.js frontend serves both hosts. Host-aware middleware rewrites public URLs to internal route trees while keeping the canonical URL in the browser:

- Apex `/` → internal `/portfolio` home.
- Apex `/writeups` and later `/writeups/[slug]` → internal `/portfolio/writeups...` CTF content.
- Quiz subdomain `/` → internal `/quiz` home or name prompt.
- Quiz subdomain study, domain, statistics, challenge, and leaderboard paths → matching internal `/quiz/...` pages.

Cross-site navigation uses absolute canonical URLs. Requests for portfolio-only pages on the quiz host and quiz-only pages on the apex host return a deliberate redirect to the canonical host.

Nginx has separate HTTP and HTTPS server blocks for `email2.my.id` and `quiz.email2.my.id`. Both redirect HTTP to HTTPS. Only the quiz host proxies `/api/` to FastAPI; the apex host returns 404 for `/api/`. Health checks remain locally available to deployment infrastructure. The TLS certificate covers both hostnames.

Cloudflare receives a DNS-only or proxied AAAA/CNAME record for `quiz.email2.my.id` pointing to the existing server. The certificate must be expanded only after that DNS record resolves to the server.

## Visual design

Signal / Editorial uses an off-white paper background, near-black typography, a restrained signal-red accent, thin rules, and strong editorial spacing. It avoids game-dashboard clutter while retaining clear feedback during study.

The portfolio home uses a strong name statement, short role description, selected-work index, and concise navigation. Writeups resemble a technical publication with readable measure, metadata, code styling, and a persistent way back to the index.

The quiz uses the same design language with functional additions:

- A single-card name prompt with one primary action.
- Clear domain and study-mode indexes.
- A question page with progress, selectable answers, confidence control, and explanation.
- A challenge summary focused on score, correct, wrong, rank, and retry.
- A leaderboard table containing only the approved public fields.

All primary actions and answer states work without relying on color alone. Keyboard focus is visible, form controls have labels, text meets WCAG AA contrast, and layouts remain usable at 360px width without horizontal scrolling. Motion respects `prefers-reduced-motion`.

## Data model

The existing `users`, `questions`, `user_progress`, `study_sessions`, and `user_responses` tables remain in place.

Add `guest_players`:

| Column | Type and constraints | Purpose |
|---|---|---|
| `user_id` | INTEGER PRIMARY KEY, FK `users(id)` | Reuses existing ownership relationships |
| `public_id` | TEXT UNIQUE NOT NULL | Opaque cookie identity |
| `display_name` | TEXT NOT NULL | Public leaderboard name |
| `created_at` | TIMESTAMP NOT NULL | Creation audit |
| `last_seen_at` | TIMESTAMP NOT NULL | Basic lifecycle visibility |

Add `challenge_records`:

| Column | Type and constraints | Purpose |
|---|---|---|
| `id` | INTEGER PRIMARY KEY | Stable ordering |
| `user_id` | INTEGER UNIQUE NOT NULL, FK `users(id)` | One best result per guest |
| `score` | INTEGER NOT NULL, CHECK 0–100 | Best score |
| `correct_count` | INTEGER NOT NULL, CHECK 0–20 | Correct answers |
| `wrong_count` | INTEGER NOT NULL, CHECK 0–20 | Wrong answers |
| `completed_at` | TIMESTAMP NOT NULL | Time this best result was achieved |

Database checks also enforce `correct_count + wrong_count = 20` and `score = correct_count * 5`. Indexes support leaderboard ordering by score and completion time.

This is an additive migration. Startup creates missing tables and indexes without replacing the SQLite file or changing question IDs. Existing accounts and learning history stay intact. A production backup is taken before applying the migration.

## Backend boundaries

A guest dependency replaces `get_current_user` on player-owned quiz routes. It verifies the signed cookie, resolves `guest_players.public_id`, and supplies the associated internal user. The public leaderboard route does not require a guest cookie.

Challenge completion updates `study_sessions` and `challenge_records` in one database transaction. The record update uses a conditional conflict clause so concurrent completion requests cannot overwrite a higher result. Existing session locking and stale-answer protections remain active.

Only server-derived session counters determine challenge score. Client-supplied scores, counts, names, ranks, and completion status are ignored or rejected.

The in-process session cache remains unchanged in this release. A backend restart invalidates an active session. The UI explains that the challenge must be restarted, and no incomplete result reaches the leaderboard. Persisting active sessions is explicitly outside this design.

## Failure behavior

- Invalid names receive a specific inline validation message and keep the entered text.
- Missing or invalid identity cookies return `401`; the frontend clears local guest state and shows the name prompt.
- A missing in-memory session returns `404`; the frontend explains that the study or challenge session expired and offers a restart.
- Duplicate or stale answer submissions return `409` and do not increment progress or challenge totals.
- A challenge with an undersized question pool returns a service error with a user-friendly retry message and server-side diagnostic detail.
- Leaderboard read failure shows a retry state while leaving study navigation usable.
- Database updates for session completion and best-score replacement roll back together on failure.

## Verification

Backend tests cover:

- Guest creation, validation, signed-cookie attributes, lookup, tampering, and expiry.
- Guest isolation on all player-owned routes.
- Removal of the mounted legacy auth API.
- Exact 20-question challenge composition and insufficient-pool behavior.
- Backend-only score calculation and rejection of partial completion.
- First result, higher-result replacement, and equal/lower-result retention.
- Atomic completion, repeat submission safety, and dense tied ranks.
- Public leaderboard response containing only rank, name, score, correct, and wrong.
- Existing grading, spaced repetition, mastery, extraction, and statistics behavior.

Frontend tests cover:

- First-visit name prompt and returning-cookie flow.
- Absence of login, register, password, email, and logout UI.
- Canonical navigation between portfolio, writeups, and quiz hosts.
- Challenge progress, result, expired-session recovery, and leaderboard retry.
- Keyboard operation, visible focus, semantic labels, and responsive layouts.

Deployment verification covers database backup and migration, production builds, container health, Nginx host routing, apex API rejection, Cloudflare DNS, the two-host TLS certificate, HTTP-to-HTTPS redirects, and live smoke tests on desktop and mobile widths.

## Acceptance criteria

The work is complete when:

1. The apex domain presents the Signal / Editorial portfolio with working Writeups and CCNA Quiz links.
2. The quiz subdomain asks a first-time visitor only for a display name and recognizes the same browser on return.
3. No user-facing login or registration flow remains.
4. Study features work under guest identity without exposing another player's data.
5. Challenge always uses the approved 20-question distribution and reports score, correct, and wrong from backend data.
6. The leaderboard exposes only rank, name, score, correct, and wrong, retains each guest's best score, and gives tied scores the same rank.
7. Existing question and learning datasets survive the additive migration.
8. Both hosts pass automated tests and live HTTPS verification.
9. Active-session persistence has not been implemented.

## Deferred work

- Persisting or recovering active study and challenge sessions across backend restarts.
- Accounts, passwords, social login, account recovery, and cross-device identity.
- Name ownership or moderation workflows.
- Portfolio CMS and writeup administration.
