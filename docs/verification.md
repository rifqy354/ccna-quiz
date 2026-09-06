# Completion verification

Verified 2026-09-06 for the existing local CCNA study application.

## Scope and schema

FastAPI, SQLite and Next.js remain the application stack. Questions retain flat option columns A–G; E–G are nullable. Correct answers use canonical letter sets, with exact-set grading for multiple answers. Database initialization adds missing option columns to older databases. The existing bank has already received its option backfill; no further manual migration is required for this workspace. Import and backfill instructions are in the README.

Study sessions remain in process memory as requested. User accounts, answers and learning progress are stored in SQLite. Resuming active sessions after restart and reconstructing historical session state remain excluded.

## Changes

- Backend authentication, question/session contracts, answer grading, spaced repetition, mastery statistics and concurrency handling.
- Extraction parsers, identity-preserving imports and option backfill.
- Frontend API/authentication handling, quiz selection/submission/completion, dashboard, domains and statistics.
- Backend and frontend regression tests, isolated database fixtures, Docker images, Compose configuration and documentation.
- Removed tracked generated Python bytecode; added build-context exclusions.

See the working-tree diff for the complete file-level changes; no commit was performed.

## Dataset

| Measure | Count |
|---|---:|
| Questions | 1,546 |
| Practice Tests source | 1,203 |
| Official Cert Guide source | 343 |
| Multiple-answer questions | 134 |
| Populated option E | 88 |
| Populated option F | 31 |
| Populated option G | 17 |
| Diagram assets | 112 |

Domain counts, in order: 235, 259, 331, 188, 209, 124, 200. Two successive real-book imports into a temporary bank retained all 1,546 question IDs and produced 112 diagrams. Verification used temporary databases and a copy of the bank for browser testing.

## Results

- Backend: **219 passed**, including the real-book audit with both EPUB paths provided. Four non-failing warnings: one passlib/crypt deprecation and three BeautifulSoup XML parsing warnings.
- Frontend: **12 passed**; production compilation and type checking passed.
- npm audit: **0 vulnerabilities** reported at verification time.
- Both Docker images built successfully; Compose configuration validated; backend health check passed.
- Through nginx on loopback port 18080: health endpoint returned 200; a diagram returned 200 with image/png content.
- Browser: registration, login, logout, session start, selection of D and F, correct grading/explanation, completion with 1/1 and 100% accuracy, updated dashboard and statistics all passed. Progress remained after logout/login.
- Desktop and 390px mobile dashboard layouts visually checked. Browser error log was empty during the smoke flow.
- `git diff --check` passed.
- Production host deployment: Docker Compose is running the backend, frontend and nginx on the confirmed IPv6 host. The remote health endpoint returned 200, and the deployed bank contains 1,546 questions, 134 multiple-answer questions and 112 diagram assets.
- Public HTTPS: `email2.my.id` resolves to the production IPv6 host. HTTP redirects to HTTPS, the landing page and health endpoint return 200, unauthenticated protected routes return 401, and the Let's Encrypt certificate is valid through 2026-12-05. Certbot's timer is active and its simulated renewal passed.

## Remaining boundaries and next task

No blocking backend issue was identified within the completed scope. Active-session persistence is deliberately unimplemented. The application is deployed at `https://email2.my.id`; Cloudflare proxying can be enabled now that the origin has a trusted certificate. The recommended next task is automated encrypted database backups with a tested restore procedure and basic uptime monitoring.
