# Data and attribution

- Land data: Natural Earth ne_50m_land GeoJSON. Downloaded from https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_50m_land.geojson . Source repository: https://github.com/nvkelso/natural-earth-vector . Public-domain terms: https://www.naturalearthdata.com/about/terms-of-use/ . Bundled unmodified; runtime clips/simplifies for the map. Routing uses the unsimplified regional geometry with a buffer.
- Ports: approximate educational coordinates and offshore approaches authored for this project, not authoritative port-entry waypoints. Verify against official charts for any real use.
- Demo weather: synthetic deterministic scenario implemented in weather_service.py; never a live observation.
- Live weather: Open-Meteo Marine https://open-meteo.com/en/docs/marine-weather-api and Forecast https://open-meteo.com/en/docs . Attribution shown through source labels; provider terms and access limits apply. Provider documentation explicitly limits coastal-navigation accuracy.
- Optional online tiles: © OpenStreetMap contributors, https://www.openstreetmap.org/copyright . No bulk tile download; offline coastline is bundled separately.
- CO2 factors: IMO MEPC.308(73), 2018 EEDI calculation guidelines, carbon conversion factors for HFO, diesel/gas oil and LNG: https://wwwcdn.imo.org/localresources/en/KnowledgeCentre/IndexofIMOResolutions/MEPCDocuments/MEPC.308(73).pdf . Used as configurable combustion-only academic defaults, not a compliance calculation.
- PDF fonts: DejaVu Sans. Bundled license at backend/app/assets/FONT_LICENSE.txt.
- Icons: lucide-react (ISC), downloaded as an npm dependency. React/Leaflet and other dependencies retain their own licenses.
