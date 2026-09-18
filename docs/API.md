# API and integration contracts

Open http://127.0.0.1:8000/docs after startup for full generated schemas. API prefix /api. Authenticated calls use Authorization: Bearer <access_token>. Login/register bodies are JSON. Passwords must have at least 10 characters on registration. Logout revokes that token. No public role promotion.

| Area | Endpoints |
|---|---|
| Auth | POST /auth/register, /auth/login, /auth/logout; GET/PUT /auth/profile |
| Vessels | GET/POST /vessels; PUT/DELETE /vessels/{id} |
| Ports/maps | GET /ports, /geography |
| Voyages | GET/POST /voyages; GET /voyages/{id} |
| Routes | POST /routes/optimize; GET /routes/compare?voyage_id=; GET /routes/{id} |
| Weather | GET /weather?lat=&lon=&mode=demo&timestamp= |
| Monitor | GET /monitoring/{id}; POST suffixes /start, /step, /hazard, /refresh, /recalculate |
| AIS | GET /monitoring/{id}/live-ais |
| Alerts | GET /alerts; PUT /alerts/{id}/acknowledge |
| Dashboards | GET /dashboard; GET /fleet (manager/admin) |
| Settings | GET /settings (authenticated); GET/PUT /admin/settings |
| Administration | GET /admin/users; PUT /admin/users/{id}; GET /admin/logs |
| Reports | GET /voyages/{id}/report?format=pdf or json |

POST /monitoring/{id}/step body: {"hours":4}. Refresh defaults to auto_recalculate=true; set query parameter false to inspect/alert only.

Weather integration calls https://marine-api.open-meteo.com/v1/marine for hourly wave_height, wave_direction, ocean_current_velocity, ocean_current_direction and https://api.open-meteo.com/v1/forecast for hourly wind_speed_10m, wind_direction_10m in m/s. This public endpoint does not consume WEATHER_API_KEY. Paid provider support requires an adapter; adding a key alone does not enable one.

Optional AIS gateway: set AIS_URL to an HTTPS endpoint and AIS_API_KEY in backend/.env, restart backend. The service makes GET AIS_URL?imo=<vessel IMO>, Authorization: Bearer <key>. Your gateway must return:

```json
{"latitude":15.2,"longitude":72.9,"speed_over_ground":13.1,"course_over_ground":175.0,"timestamp":"2026-09-18T10:00:00Z"}
```

Latitude/longitude in degrees, SOG knots, COG degrees, timestamp timezone-aware UTC. This is a generic integration contract, not an integrated subscription or fabricated AIS feed. Missing configuration returns a visible 502. Simulator remains labelled and available.

Typical errors: 401 session invalid; 403 role denied; 404 inaccessible object; 409 conflicting action; 422 invalid inputs/no safe route/missing weather; 429 auth rate limit; 502 unavailable live AIS.
