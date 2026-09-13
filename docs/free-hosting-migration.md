# Free Hosting Migration

This app can run on free hosting as split services:

- Frontend: Vercel, Netlify, or Render Static Site from `frontend/`.
- Backend: Render Web Service, Koyeb Web Service, or another Docker host using `backend/Dockerfile.hosting`.

## Important persistence note

The app currently uses SQLite at `data/ccna.db`. Free web-service filesystems are usually ephemeral, so quiz questions will be available because `backend/Dockerfile.hosting` copies `data/` into the image, but new players, progress, and leaderboard changes can disappear after redeploys, restarts, or platform sleep.

For durable free hosting, migrate the backend storage to a managed database such as Supabase or Neon Postgres. Until then, treat free web-service deployment as a demo/study deployment, not permanent production storage.

## Backend service

Create a Docker web service from the repository root.

Use:

```text
Dockerfile: backend/Dockerfile.hosting
Port: 8000
Health check: /health
```

Set environment variables:

```text
JWT_SECRET_KEY=<generate-a-long-random-secret>
PLAYER_COOKIE_NAME=ccna_player
PLAYER_COOKIE_MAX_AGE=31536000
PLAYER_COOKIE_SECURE=true
PLAYER_COOKIE_SAMESITE=none
CORS_ALLOW_ORIGINS=https://<your-frontend-host>
```

Leave `PLAYER_COOKIE_DOMAIN` unset when the backend is hosted on a platform subdomain. The browser will scope the cookie to the backend host.

## Frontend service

Deploy from `frontend/`.

Use:

```text
Build command: npm ci && npm run build
Start command: npm run start
```

Set:

```text
NEXT_PUBLIC_API_URL=https://<your-backend-host>
```

When `NEXT_PUBLIC_API_URL` is set, the frontend sends credentials with API requests so the guest-player cookie can work across frontend and backend domains.

## Local verification

From the repository root:

```bash
PYTHONPATH=backend python -m pytest backend/tests/test_infrastructure.py -q
cd frontend
npm ci
npm test -- tests/api.test.ts
npm run build
```

If `node_modules` was copied from Linux to Windows, run `npm ci` again on Windows before running Vitest or Next.js, because Rollup installs OS-specific optional packages.
