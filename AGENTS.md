# Repository Guidelines

## Project Structure & Modules
- `src/api`: FastAPI backend (routers, helpers, Celery tasks, Prisma client, tests).
  - `routers/`, `helpers/`, `calculations/`, `prisma/`, `tests/`, `data/`.
- `src/frontend`: SvelteKit app (TypeScript, Prisma schema, static assets).
  - `src/`, `prisma/`, `static/`, build via Vite.
- Orchestration and tooling: `docker-compose*.yml`, `Taskfile.yml`, `.env` (local dev), `pyproject.toml` (commitizen).

## Architecture Overview
```
flowchart LR
  User[Browser] -->|HTTP| View[view: SvelteKit (3000)]
  View -->|REST/JSON| API[api: FastAPI (8000)]
  API -->|ORM| Prisma[Prisma Client]
  Prisma --> DB[(External DB via DATABASE_URL)]
  API -->|Tasks| Celery[worker: Celery]
  Celery <--> Redis[(redis:6379)]
  API --> Keycloak[(Keycloak IdP)]
  API -->|Static| Data[(src/api/data)]
```

## Build, Test, and Development
- Full stack (Docker): `task dev` — builds and runs all services (first start may take minutes). App: `http://localhost:8000`.
- Initialize dev assets: `task init` — installs frontend deps and downloads example data into `src/api/data/`.
- Frontend only:
  - `cd src/frontend`
  - `npm run dev` — start Svelte dev server.
  - `npm run build` — production build.
  - `npm run lint` / `npm run format` / `npm run check` — lint, format, type-check.
- Prisma client (after schema changes): `task prisma`.
- Backend tests:
  - Install: `pip install -r src/api/requirements.txt`
  - Run: `pytest src/api/tests -q`

## Coding Style & Naming
- Python: 4-space indent, PEP8; modules and files `snake_case.py`; routers under `src/api/routers`; tests `test_*.py`.
- TypeScript/Svelte: Prettier + ESLint enforced. Components `PascalCase.svelte`; modules `camelCase.ts` where appropriate.
- Keep functions small and typed. Co-locate feature files within their domain folders.

## Testing Guidelines
- Framework: `pytest` with Starlette `TestClient` for API.
- Place tests in `src/api/tests/` named `test_*.py`. Aim for request/response coverage on routers and task flows.
- Prefer unit tests around `calculations/` and integration tests for routers. Mock external services.

## Commit & Pull Requests
- Conventional Commits via commitizen (see `pyproject.toml`). Examples: `feat(api): add discharge endpoint`, `fix(frontend): correct chart scaling`.
- PRs must include: clear description, linked issues, screenshots for UI changes, and steps to validate. Ensure `task build` (or Docker build) passes and linters are clean.

## Security & Configuration
- Secrets live in `.env` (local only). Never commit secrets. Keycloak values: `PUBLIC_KEYCLOAK_URL`, `AUTH_KEYCLOAK_ID`, `AUTH_KEYCLOAK_SECRET`.
- Static data served from `src/api/data/`; avoid placing sensitive files there.
- After Prisma schema edits, regenerate clients and review migrations before pushing.
