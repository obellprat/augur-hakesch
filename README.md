# Augur-Hakesch

Augur-Hakesch is an [AUGUR](https://augur.world) application for river discharge calculations based on the Swiss HAKESCH method, re-calibrated on selected catchments using new precipitation climatology from the Swiss Federal Office of Meteorology and Climatology (MeteoSwiss).

<table>
  <tr>
    <td><img src="docs/images/augur_startscreen.png" alt="Start Screen" width="100%"></td>
    <td><img src="docs/images/augur_precipitation.png" alt="Precipitation" width="100%"></td>
  </tr>
  <tr>
    <td><img src="docs/images/augur_geodata.png" alt="Geodata" width="100%"></td>
    <td><img src="docs/images/augur_calculation.png" alt="Calculation" width="100%"></td>
  </tr>
</table>

## Architecture

The application is composed of several services orchestrated via Docker Compose:

```mermaid
flowchart LR
  User[Browser] -->|HTTP| View[view: SvelteKit :3000]
  View -->|REST / JSON| API[api: FastAPI :8000]
  API -->|ORM| Prisma[Prisma Client]
  Prisma --> DB[(PostgreSQL)]
  API -->|Tasks| Celery[worker: Celery]
  Celery <--> Redis[(Redis :6379)]
  API --> Keycloak[(Keycloak IdP)]
  API -->|Static| Data[(src/api/data)]
```

| Service | Technology | Port | Description |
|---------|-----------|------|-------------|
| **api** | FastAPI (Python 3.13) | 8000 | REST API for discharge calculations |
| **view** | SvelteKit (Node 23) | 3000 | Frontend web application |
| **worker** | Celery | — | Async task worker for heavy computations |
| **redis** | Redis 8.2 | 6379 | Message broker & result backend for Celery |
| **dashboard** | Flower | 5556 | Celery task monitoring dashboard (dev only) |

Authentication is handled by an external [Keycloak](https://www.keycloak.org/) identity provider.

## Tech Stack

- **Backend**: Python 3.13, FastAPI, Celery, Prisma (Python client), GDAL, NumPy, GeoPandas
- **Frontend**: SvelteKit 2, Svelte 5, TypeScript, Prisma (JS client), Bootstrap 5, Leaflet/OpenLayers, Plotly, ApexCharts
- **Database**: PostgreSQL (external, via `DATABASE_URL`)
- **Auth**: Keycloak, Auth.js (SvelteKit adapter)
- **Infrastructure**: Docker, Docker Compose, Traefik (reverse proxy), Redis

## Project Structure

```
augur-hakesch/
├── src/
│   ├── api/                    # FastAPI backend
│   │   ├── calculations/       # Hydrological calculation modules (NAM, curve numbers, etc.)
│   │   ├── routers/            # API route handlers
│   │   ├── helpers/            # Shared utility functions
│   │   ├── data/               # Static raster/GIS data (downloaded at init)
│   │   ├── tests/              # pytest test suite
│   │   ├── main.py             # FastAPI application entry point
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/               # SvelteKit frontend
│   │   ├── src/
│   │   │   ├── routes/         # SvelteKit pages & server routes
│   │   │   ├── lib/            # Shared components, i18n, server helpers
│   │   │   └── scss/           # Global styles
│   │   ├── prisma/             # Prisma schema & migrations
│   │   ├── static/             # Static assets (images, documents)
│   │   ├── Dockerfile
│   │   └── package.json
│   └── monitor/                # External API health monitoring service
│       ├── monitor.py
│       ├── Dockerfile
│       └── .env.example
├── docker-compose.yml          # Local development (full stack)
├── docker-compose.server.yml   # Production deployment (with Traefik)
├── docker-compose.traefik.yml  # Standalone Traefik reverse proxy
├── docker-compose.keycloak.yml # Keycloak + PostgreSQL for auth
├── Taskfile.yml                # Task runner commands
├── pyproject.toml              # Project metadata & commitizen config
└── .env                        # Environment variables (local only, not committed)
```

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Task](https://taskfile.dev/) runner (install via `pip install go-task-bin`)
- [Node.js](https://nodejs.org/) 23+ (for frontend development outside Docker)
- [Python](https://www.python.org/) 3.13+ (for backend development outside Docker)
- A PostgreSQL database accessible via `DATABASE_URL`
- A Keycloak instance for authentication

## Environment Variables

Create a `.env` file in the project root. Required variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@host:5432/dbname`) |
| `PUBLIC_KEYCLOAK_URL` | Public URL of the Keycloak instance |
| `AUTH_KEYCLOAK_ID` | Keycloak client ID |
| `AUTH_KEYCLOAK_SECRET` | Keycloak client secret |
| `CELERY_BROKER_URL` | Redis broker URL (default: `redis://redis:6379/0`) |
| `CELERY_RESULT_BACKEND` | Redis result backend URL (default: `redis://redis:6379/0`) |

> **Security**: Never commit the `.env` file. It is listed in `.gitignore`.

## Quick Start (Docker)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd augur-hakesch
   ```

2. **Install the Task runner**

   ```bash
   pip install go-task-bin
   ```

3. **Initialize the project** (downloads GIS data and installs frontend dependencies)

   ```bash
   task init
   ```

4. **Configure environment variables**

   Create a `.env` file in the project root with the required variables listed above.

5. **Create the Docker network** (required once)

   ```bash
   docker network create traefik-public
   ```

6. **Start the application**

   ```bash
   task dev
   ```

   This builds and starts all services via `docker compose up --build`. The first start may take several minutes.

7. **Access the application**

   - Frontend: [http://localhost:3000](http://localhost:3000)
   - API: [http://localhost:8000](http://localhost:8000)
   - API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
   - Celery dashboard (Flower): [http://localhost:5556](http://localhost:5556)

## Development

### Task Commands

All common operations are defined in `Taskfile.yml`:

| Command | Description |
|---------|-------------|
| `task init` | Install frontend deps and download required GIS data |
| `task dev` | Build and run all services with Docker Compose |
| `task build` | Build all Docker images |
| `task push` | Build and push Docker images to registry |
| `task prisma` | Regenerate Prisma client after schema changes |
| `task dev-frontend` | Start the SvelteKit dev server (without Docker) |
| `task build-frontend` | Build the SvelteKit frontend for production |

### Frontend Development

The frontend is a SvelteKit application located in `src/frontend/`.

```bash
cd src/frontend

# Install dependencies
npm install

# Start dev server (with hot reload)
npm run dev

# Production build
npm run build

# Type-check
npm run check

# Lint & format
npm run lint
npm run format
```

The frontend uses:
- **Svelte 5** with TypeScript
- **Prisma** for database access (schema in `src/frontend/prisma/schema.prisma`)
- **Auth.js** (SvelteKit adapter) for Keycloak-based authentication
- **Bootstrap 5** for styling
- **Leaflet / OpenLayers** for map rendering
- **Plotly / ApexCharts** for data visualization
- **svelte-i18n** for internationalization

### Backend Development

The API is a FastAPI application located in `src/api/`.

```bash
cd src/api

# Install dependencies
pip install -r requirements.txt

# Start the dev server
uvicorn main:app --host 0.0.0.0 --reload
```

Key backend dependencies: FastAPI, Celery, Prisma, GDAL, NumPy, GeoPandas, pysheds, xarray, netCDF4.

### Database & Prisma

The project uses Prisma as ORM in both the frontend (JavaScript client) and backend (Python client). The Prisma schema is located at `src/frontend/prisma/schema.prisma`.

After modifying the schema:

```bash
# Regenerate Prisma clients
task prisma

# Or manually for the frontend
cd src/frontend && npx prisma generate

# For the backend (inside Docker or with prisma installed)
prisma generate
```

### Running Tests

Backend tests use `pytest` with Starlette's `TestClient`:

```bash
# Install test dependencies
pip install -r src/api/requirements.txt

# Run tests
pytest src/api/tests -q
```

- Tests are located in `src/api/tests/` and follow the `test_*.py` naming convention.
- Unit tests focus on `calculations/` modules; integration tests cover API routers.
- External services should be mocked in tests.

## Docker Compose Configurations

| File | Purpose |
|------|---------|
| `docker-compose.yml` | **Local development** — all services with volume mounts for live reloading |
| `docker-compose.server.yml` | **Production** — pre-built images, Traefik reverse proxy, resource limits |
| `docker-compose.traefik.yml` | **Standalone Traefik** — HTTPS with Let's Encrypt, used in production |
| `docker-compose.keycloak.yml` | **Keycloak + PostgreSQL** — identity provider stack |

### Building Docker Images

```bash
# Build all images
task build

# Build and push to registry
task push

# Build individual services
docker compose build api
docker compose build view
```

### Production Deployment

For production, use the server and Traefik compose files:

```bash
# Create the external network
docker network create traefik-public

# Start Traefik (reverse proxy with HTTPS)
docker compose -f docker-compose.traefik.yml up -d

# Start the application services
docker compose -f docker-compose.server.yml up -d
```

The Celery worker in production uses thread-based concurrency with resource limits (8 GB memory, 2 CPUs).

## Coding Style

- **Python**: PEP 8, 4-space indentation, `snake_case` for modules and files.
- **TypeScript / Svelte**: Prettier + ESLint enforced. Components use `PascalCase.svelte`, modules use `camelCase.ts`.
- Keep functions small and well-typed. Co-locate feature files within their domain folders.

## Commit Conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/) via [commitizen](https://commitizen-tools.github.io/commitizen/) (configured in `pyproject.toml`).

Examples:

```
feat(api): add discharge endpoint
fix(frontend): correct chart scaling
docs: update README with deployment instructions
refactor(calculations): simplify NAM model
```

## Monitoring

An optional monitoring service lives in `src/monitor/`. It periodically checks the API health, CPU, memory, and disk usage, and sends email alerts when thresholds are exceeded. See `src/monitor/README.md` and `src/monitor/.env.example` for configuration details.

## License

See the project repository for license information.
