# Horizon architecture and scope

## Implemented layers
React/JavaScript/Axios UI -> FastAPI/Pydantic routes -> service functions -> SQLAlchemy -> SQLite or PostgreSQL. Leaflet uses a bundled Natural Earth coastline by default with optional OpenStreetMap tiles. Shapely validates navigation edges. WeatherService owns demo/live provenance. AISService owns route simulation and the optional live gateway contract.

The application is a single-company academic prototype. Planners see their own vessels/voyages. Fleet managers and administrators see company-wide records. Company tenancy is not modelled. Public registration creates planners only; role changes are administrator-only.

## Exactly seven actors
1. Maritime Planner / Ship Operator
2. Fleet Manager / Shipping Company
3. System Administrator
4. Marine Weather API
5. AIS Service
6. Mapping / Geospatial Service
7. Notification Service

## Persistence
users, sessions, vessels, ports, voyages, routes, route_points, weather_data, ais_positions, alerts, system_settings, route_comparisons, system_logs. Foreign keys are enforced in SQLite. Routes, vessel parameters, forecast values and policy are saved as versioned snapshots alongside normalized route coordinates. Schema creation and repeatable seeds run at startup (app.seed); modifying an existing schema in a future release will need an explicit migration. SQLAlchemy uses portable types; PostGIS is optional and not required or claimed as installed.

## Maritime graph and geographic limits
Bounds: longitude 45–106 E, latitude 2 S–28 N, .5-degree lattice, diagonal/cardinal ocean connections. Every full edge is checked against Natural Earth 1:50m land polygons buffered by .025 degrees. Port approach points connect to up to eight visible grid nodes within 180 km, also with full segment intersection checks. Port markers are display-only; routes begin/end at specified offshore approach points. No hidden shore-to-approach route is fabricated. Eight port approaches are bundled and connectivity-tested. There is no global route coverage, canal routing, depth chart, traffic separation scheme or certified under-keel clearance. Short edges use straight latitude/longitude segments with Haversine lengths; this is a regional approximation, not an ellipsoidal navigation engine.

## Search and cost
Baseline is shortest geographically navigable distance. It can be weather-unsafe, and is labelled as such. Optimized edges must remain below the smaller of vessel/admin wave and wind limits, reduced by 15% under Conservative safety. Samples are spaced at most 10 km apart. Thus finite samples approximate continuous weather; not a mathematical guarantee about unsampled real weather.

Cost = edge_km × [w_distance + w_weather × risk + w_fuel × (edge_fuel / calm_reference_fuel) + w_time × (edge_hours / calm_reference_hours) + w_safety × risk^4]. All normalized components are nonnegative. The balanced weights are configurable; Safest, Fuel Efficient and Shortest use explicit documented presets in route_optimizer.py. A* heuristic = w_distance × Haversine to destination, an admissible lower bound; Dijkstra uses zero heuristic. Weather-unsafe edges are excluded. A disconnected/unsafe route returns HTTP 422; no straight-line fallback.

## Weather model
Demo is deterministic: smooth radial storms over a mild wind/wave field. Default Mumbai–Kochi storm center is 14.5 N, 74 E. No random weather or random fuel values. Hazard footprints on the map show scenario extents rather than exact vessel-specific safety contours.

Live weather uses real Open-Meteo Marine and Forecast endpoints with a batched regional coarse grid at the requested departure hour. Nearest complete marine/wind sample is used within 450 km, with sample coordinates, distance, source and valid timestamp retained. Currents are optional, absence remains null in raw weather and is treated as zero in the engineering model. Wave/wind missing data is not treated as calm. Live mode rejects dates beyond its six-day gate and rejects incomplete/unavailable forecasts; users must choose Demo explicitly.

Routes use a STATIC departure-time snapshot, not a time-expanded forecast graph. This is a deliberate bounded academic implementation; transit conditions can differ. Refresh/recalculate fetches another snapshot at the current simulation time. A storm can be injected only in demo mode. This limitation is exposed in the UI and report, not represented as arrival-time forecasting.

## Fuel, time and CO2
Units: distance km, vessel speed knots, weather wind/current m/s, waves m, fuel tonnes/day at the specified cruising speed, emissions tonnes CO2. 1 knot = 1.852 km/h.

Resistance R = 1 + .10 × wave_height² + .001 × wind_speed².
Through-water speed = cruising_speed / R^.35.
Along-track current = current_mps × 3.6 × cos(current_direction - route_bearing).
Ground speed km/h = max(3, through-water_speed × 1.852 + along-track current).
Segment hours = distance / ground speed.
Segment fuel = reference_tonnes_per_day / 24 × segment_hours × R.
CO2 = fuel × selected fuel factor.

Reference consumption is assumed to be the fuel rate at the entered cruise setting. Speed is not independently optimized. Each edge uses its highest-risk sampled weather as a conservative representative. These coefficients are illustrative academic assumptions, not calibrated vessel physics. The large prepared-demo fuel difference follows the chosen storm/resistance assumptions and must not be presented as proven operational savings. Default combustion-only factors HFO 3.114, MDO 3.206, LNG 2.750 t CO2/t fuel follow commonly used IMO carbon factors. They exclude methane slip and lifecycle effects; configurable in Admin.

## Monitoring and recalculation
The simulator advances distance with per-segment estimated speed and UTC simulated hours. Completed voyages stop. Injected storms generate persisted critical alerts. Weather refresh inspects the remaining route and can automatically recalculate. Recalculation starts at the current simulated position, saves new baseline/optimized versions and comparison, preserves previous routes/positions and sailed distance, and resets progress of the remaining leg. ETA uses cumulative simulated hours plus remaining segment hours. Comparisons after recalculation are for the remaining leg, not retroactively for the entire voyage. Dashboard fuel totals use initial planned route estimates, explicitly not actual consumption.

Live AIS HTTPS observations can be retrieved and persisted via the configured gateway; the UI reports them separately. The operational demo map and rerouting use the simulator. A paid AIS subscription and vendor-specific gateway are not bundled.

## Security and operational boundaries
Argon2 password hashes; HS256 JWT with required expiry/issuer/audience/jti; persistent revocable sessions; eight-hour expiry; role/ownership checks; typed input validation; bounded login/register requests per local process; explicit CORS origins. Tokens use sessionStorage; production deployments should consider secure HttpOnly cookie sessions and CSRF protection for that model. Local setup generates secrets rather than bundling any. Demo seeds require DEMO_MODE and a configured DEMO_PASSWORD. Use one API worker for this prototype's in-process monitoring serialization. Deployment needs TLS, managed secrets, backups, migration discipline and stronger distributed rate limits. Docker/PostgreSQL setup is included but not execution-tested in this delivery.
