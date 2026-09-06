# CCNA Quiz Completion Plan

**Goal:** Finish and verify the existing local study application and its deployment configuration.

**Architecture:** Keep FastAPI, SQLite, and Next.js. Repair existing contracts and workflows rather than replacing the app. Study sessions remain in process memory as explicitly requested.

**Constraints:** Preserve the 1,546-question bank and existing user data; tests use temporary databases. No session persistence, external publication, or unrelated redesign.

## Work streams

- [x] Frontend: repair API methods and errors, same-origin backend access, authentication handling, single/multiple selection, submission busy states, end-of-session behavior, navigation and production build. Own `frontend/`.
- [x] Study backend: correct random-question metadata, validate session/answer inputs, select unique questions with useful fallback, return explicit session exhaustion, score only answered questions, test endpoints and scheduler. Own question/session routers, models, scheduler selection and relevant tests.
- [x] Authentication: validate malformed credentials/tokens, register failures and refresh rotation; verify clean dependency install compatibility. Own auth modules and auth tests.
- [x] Integration: isolate the default test suite, serve question images, correct database paths and container configuration, validate data and extraction workflow, document reproducible test/build commands. Own remaining backend infrastructure, deployment and docs.
- [x] Run all backend tests, frontend tests and production build; exercise register/login/start/answer/complete/stats in a browser against temporary data.
- [x] Review the combined changes and resolve actionable findings. Record verified outcomes and explicit limitations.

## Shared contracts

`POST /api/sessions/{id}/complete` completes a session. Exhausted `GET /api/sessions/{id}/next` returns HTTP 204 with no body; clients interpret it as completion. Session count is the actual selected count. Public browser API traffic defaults to same origin, with a development proxy to the local backend. No answer key is included before submission.
