# Manual acceptance and presentation checklist

- [ ] Run setup, start backend/frontend, check /api/health.
- [ ] Register a planner, edit profile, logout and login again.
- [ ] Create/edit a vessel; verify positive dimensions and cruise <= maximum speed.
- [ ] Choose source/destination, departure, vessel, weather mode and preferences.
- [ ] Mumbai -> Kochi in Demo: generate baseline and optimized routes.
- [ ] See land coastline, source/destination markers, two route styles, weather popups and hazard circles.
- [ ] Confirm baseline unsafe / optimized safe; compare distance, hours, fuel, CO2 and risk.
- [ ] Generate Dijkstra variant; shortest-path calculations should agree with A* for the same cost/inputs.
- [ ] Start monitoring, advance position, inspect speed, weather, progress, remaining distance and ETA.
- [ ] Inject hazard with over 80 km remaining; see alert.
- [ ] Recalculate; verify new path begins at vessel position and route version increments.
- [ ] Try Refresh weather & auto-reroute on a newly injected hazard.
- [ ] Open an old route overlay; saved route history remains intact.
- [ ] Export PDF and JSON, inspect voyage/weather/comparison/alerts.
- [ ] Complete a voyage; status becomes completed and further steps are blocked.
- [ ] Restart backend; voyage history persists.
- [ ] Login as a different planner; cannot see another planner's voyage.
- [ ] Login as manager; inspect company vessels, voyage status and estimate totals.
- [ ] Login as admin; change a non-self user's role, edit thresholds/weights and inspect logs.
- [ ] Invalid settings (weights not summing to 1, unordered risk thresholds) are rejected.
- [ ] Live weather with unavailable coverage errors clearly; select Demo explicitly to continue.
- [ ] Live AIS without gateway shows an error; simulator keeps working.
- [ ] Turn off internet after initial installation; coastline and demo workflow remain usable.
- [ ] Resize browser to phone width; map refits and forms remain usable.

These checks cover the supplied 25-step acceptance workflow. Do not present regional routes, static forecast snapshots or illustrative fuel estimates as certified navigation or measured savings.
