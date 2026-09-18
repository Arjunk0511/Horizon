# Horizon — Weather-Aware Maritime Route Optimization

**Complete local academic project, delivered in one ZIP.** React + FastAPI + SQLAlchemy, SQLite default, PostgreSQL Docker configuration, A*/Dijkstra, bundled regional land data, deterministic weather, live weather adapter, AIS simulator, route history and PDF/JSON reports.

## What is included
- Register/login/logout, editable profile, planner/manager/admin roles, Argon2 and JWT session revocation.
- Vessel create/edit/delete, eight Indian/international ports, voyage planning with preferences and departure time.
- Sea graph with edge/land intersection checks, Haversine distance, A* and Dijkstra.
- Baseline and weather-aware route estimates for distance, hours, fuel, CO2 and risk.
- Leaflet map with two routes, ports, hazards, weather popups, vessel position, history overlays, offline coastline and optional OSM tiles.
- Deterministic weather demonstration; genuine Open-Meteo live adapter with explicit failures.
- AIS simulation, start/step/auto controls, dynamic storm injection, weather refresh, alerts and current-position rerouting.
- Saved voyage and route versions, fleet overview, user/role administration, safety settings, configurable weights/emission factors and system logs.
- PDF/JSON voyage exports, automated backend acceptance tests, Windows scripts and optional Docker Compose.

## Important model boundaries
This is an academic prototype, not certified navigational software. Regional graph coverage is 45–106 E and 2 S–28 N. Routes begin/end at offshore approaches, not exact terminals. No bathymetry, draft clearance, canals or traffic restrictions. Weather optimization uses a static departure-time snapshot, refreshed on recalculation; it does not forecast segment arrival times. Live regional weather is coarse. Fuel coefficients are documented assumptions and savings are illustrative. The bundled working tracking experience uses the AIS simulator; the optional real AIS gateway is a contract you configure separately. These boundaries are visible in the app and described in docs/ARCHITECTURE.md.

## Quick start — Windows 11 / VS Code
Install **Python 3.12**, **Node.js 22.12 or newer**, and VS Code. Git is optional. Initial dependency installation requires internet. Once installed, the entire DEMO workflow and coastline work offline. No MongoDB, PostgreSQL, API subscription, or Docker is needed for the default setup.

1. Extract horizon-complete.zip into a NEW folder. Do not overwrite a folder containing your own work. Open its horizon folder in VS Code.
2. Open a PowerShell terminal in horizon and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

This runs the local script for this process only; it does not change machine execution policy. It creates the Python environment, installs packages, generates secrets and prints a unique demo password. Keep that password; it is also in backend/.env under DEMO_PASSWORD. Existing .env files are preserved.

3. Start backend in Terminal 1:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-backend.ps1
```

4. Start frontend in Terminal 2:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-frontend.ps1
```

5. Open http://127.0.0.1:5173 . API docs: http://127.0.0.1:8000/docs . Health: http://127.0.0.1:8000/api/health . Keep both terminals open; Ctrl+C stops each server.

### Accounts
| Email | Role |
|---|---|
| planner@horizon.local | Maritime Planner / Ship Operator |
| manager@horizon.local | Fleet Manager |
| admin@horizon.local | System Administrator |

All three use the randomly generated DEMO_PASSWORD printed during setup. It is not hardcoded or included in the ZIP. You can register a personal planner account instead; it receives a starter vessel. To create an administrator on a fresh local database, use the configured demo seed. There is no insecure public admin registration endpoint.

Changing DEMO_PASSWORD after users have been seeded does NOT reset their stored passwords. Preserve the original .env. Do not share your populated database or secrets. To recover local credentials, use the original generated password, or for a disposable demo only, stop the backend, back up the database and configure a fresh DATABASE_URL to seed new accounts.

### Manual setup alternative
From horizon root:

```powershell
py -3.12 -m venv backend/.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\backend\.venv\Scripts\python.exe scripts/configure.py
Set-Location frontend
npm.cmd ci
Set-Location ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal from horizon root:

```powershell
Set-Location frontend
npm.cmd run dev
```

## Five-minute college demonstration
1. Sign in as planner, or register.
2. Open Voyage planner: **Mumbai → Kochi**, choose a vessel, Demo weather, Balanced, Standard, A*.
3. Generate & save voyage. Watch orange baseline cross the storm while teal optimized route avoids weather limits.
4. Compare distance, hours, fuel, CO2, risk and safety. A slightly longer route can have lower estimated exposure/fuel under the demo assumptions.
5. Open Monitor voyage; Start voyage; Simulate next 4h.
6. Inject weather hazard. Read the critical alert.
7. Recalculate remaining route. The new route starts at the current position and its version increments. Alternatively, Refresh weather & auto-reroute detects hazards and recalculates.
8. Return to Route comparison; click an older route version for a purple history overlay.
9. Download PDF or JSON report. Open Voyage history; the saved voyage remains after server restart.
10. Sign out; sign in as manager/admin to inspect fleet overview or administration.

## Environment and database
backend/.env is loaded with an absolute path. Default SQLite database is backend/horizon.db and is created on startup. DATABASE_URL is optional; use postgresql+psycopg://user:password@host:5432/database for PostgreSQL. SQLAlchemy initializes the schema and repeatable seeds. PostGIS is not required. Existing schema evolution needs migrations in a future release; this project creates its initial schema, not arbitrary upgrade migrations.

DEMO_MODE=true enables demo seeding when DEMO_PASSWORD is supplied and chooses initial default weather mode. JWT_SECRET_KEY must have at least 32 characters; the setup generates it. If omitted, a generated local backend/.jwt-secret persists the signing key. CORS_ORIGINS is a JSON list. WEATHER_API_KEY is reserved; the integrated public Open-Meteo endpoints need no key. AIS_URL/AIS_API_KEY configure the optional HTTPS gateway documented in docs/API.md. VITE_API_BASE_URL defaults to /api; BACKEND_PROXY_TARGET to http://127.0.0.1:8000. Never put secrets in VITE_ variables.

Administrator settings select default weather mode, wave/wind limits, risk boundaries, balanced weights and fuel emission factors. Live provider secrets stay in backend/.env and require restart. Existing routes retain saved policy snapshots.

## Algorithms and model assumptions
See docs/ARCHITECTURE.md for complete equations, units, normalized objective, A* admissibility, geographic constraints, baseline safety semantics, weather coverage, monitoring and limitations. See docs/DATA_SOURCES.md for dataset/provider/font licenses and factor references. There are exactly seven actors; the original specification is preserved in docs/ORIGINAL_SPECIFICATION.txt.

## Tests
From horizon/backend:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -s
```

Tests use an isolated temporary database and do not erase your local voyages. Covers authentication/RBAC, ownership, session revocation, graph connectivity and land avoidance, A*/Dijkstra costs, Haversine, deterministic weather and thresholds, fuel/CO2, routing, simulator, hazard/recalculation/history, completion, settings validation and report exports. See docs/VERIFICATION.md for actual results and browser checks.

From horizon/frontend:

```powershell
npm.cmd run build
```

This generates dist/. The local frontend uses Vite's /api proxy; production deployment needs a reverse proxy. Included nginx config supplies one in Docker.

## Docker/PostgreSQL alternative
Optional Docker Desktop setup; not needed for local SQLite. Run `py -3.12 scripts/configure.py` to generate root .env first, then from horizon:

```powershell
docker compose up --build
```

Uses PostgreSQL 16 with a named persistent volume, FastAPI on 8000, nginx frontend on 5173. Stop existing local servers first. Stop containers with `docker compose down`; do not add `-v` unless intentionally deleting the database. Docker/PostgreSQL configuration is provided but not execution-tested in this environment. PostGIS spatial acceleration is not implemented. Do not publish the demo stack to the internet without production authentication/secret/TLS hardening.

## Troubleshooting
- `py -3.12` missing: install Python 3.12 with Windows launcher and reopen VS Code.
- Node version warning: use 22.12+; older Node 20 installations are outside this package's supported setup.
- Script-policy restriction: use the provided `powershell -ExecutionPolicy Bypass -File ...` process-scoped invocation or the manual commands. No activation script is required.
- Cannot import app: run uvicorn from backend/, or use start-backend.ps1.
- Port occupied: stop the other 8000/5173 instance. Frontend uses strict port selection.
- Login fails: read the generated DEMO_PASSWORD; passwords are seeded only once. Restart the backend after changing .env.
- Live weather fails: verify internet and forecast time; choose Demo explicitly. Failure never silently produces mock live data.
- No route: bounds/land/safety constraints may leave no feasible path. Do not weaken hard vessel limits to conceal this; choose a supported route/scenario or appropriately configured vessel.
- Cannot delete vessel: referenced voyage history intentionally prevents deletion.
- Rate limit: wait one minute after 20 auth requests in a minute.
- PDF report: Unicode font files are bundled; keep backend/app/assets intact.
- Simulator controls: start the voyage before stepping; completed voyages cannot be stepped again. Inject hazards while more than 80 km remains.

## Folder structure
backend/app: main.py, config.py, database.py, security.py, seed.py; models, schemas, algorithms, services, utils, assets. backend/tests: automated tests. frontend/src: App.jsx, styles.css, components/RouteMap.jsx, services/api.js. data: ports and Natural Earth land. scripts: configure.py. docs: architecture, API, verification, sources, manifest and screenshots. Root: setup/start PowerShell scripts, Docker Compose, README and Git configuration.

The API and UI are grouped into feature sections rather than creating fourteen thin page files. All requested screens/use cases are reachable through the sidebar, forms and route/monitor views. This is one complete project, not a sequence of phase packages.

## Git commit point
After local verification, run `git init`, `git add .`, review `git status`, then `git commit -m "Build Horizon maritime route planning demo"`. .env, .jwt-secret, database, virtual environment, node_modules and build output are ignored. Never commit credentials.

## Future scope
Arrival-time weather search, calibrated fuel curves, high-resolution bathymetry, authoritative port corridors, vendor-specific live AIS tracking/rerouting, multi-company tenancy, continuous migration management and production deployment hardening.
