# Verification record — complete project

Verified on Linux with Python 3.12.14, Node 24.19.0, npm 11.9.0. Windows instructions use the same Python/Node dependencies but have not been executed on Windows in this environment.

## Automated API and calculation checks
Six pytest test groups passed. Covers authentication, registration privilege rejection, duplicate email, wrong password, logout token revocation, profile editing, role restrictions, cross-user voyage isolation, vessel CRUD/history protection, graph connection for all eight ports, full-segment land avoidance, A*/Dijkstra path-cost equivalence, Haversine, deterministic weather, safety threshold rejection, fixed-value fuel/CO2 calculations, route generation and persisted snapshots, simulator movement, injected hazard, current-position recalculation, route-version history, PDF/JSON reports, completion and settings validation.

Prepared Mumbai–Kochi demo with default vessel, Balanced/Standard/A*:
- Baseline: 1,115.2 km; estimated fuel 120.2 t; mean risk 0.554; weather limits exceeded.
- Optimized: 1,117.5 km; estimated fuel 55.9 t; mean risk 0.374; within weather limits.
- After 4 simulated hours, injected storm and recalculation produced version 2 from the current position; original two route records retained alongside two new records.
These values are academic model results, not measured operational savings.

## Browser checks
A Chromium/Playwright run against real FastAPI and Vite servers passed login -> overview -> voyage planner -> route generation -> comparison -> start monitoring -> advance 4h -> inject storm -> recalculate -> version 2. No JavaScript page errors. Desktop and 390px mobile screenshots inspected; no horizontal overflow. Map refits on viewport changes. The default departure uses local time correctly.

Screenshots: docs/screenshots/dashboard.png, comparison.png, monitoring.png, mobile.png.

## Reports and build
Production frontend build passed. PDF generated through the real endpoint; both pages rendered and inspected. Bundled DejaVu fonts ensure readable embedded text. JSON report parses with voyage, route, weather and alert data. ZIP is checked for CRC integrity and excludes databases, credentials and dependency folders.

## Not independently verified
Actual Windows execution, Docker/PostgreSQL runtime, live Open-Meteo success with network access, a real AIS vendor subscription/gateway, and suitability for real navigation. Live failure handling is tested; live results are never invented. Existing Starlette/httpx test-client deprecation notices do not fail the test suite.
