NOAA + Overture → Sedona spatial analysis → parameterized Wherobots job → managed Havasu/Iceberg → curated GeoJSON export → MapLibre customer explorer.
critically, grid_assets.geojson wasn't generated from some separate hand-built dataset. These features were selected from the persisted production-job output
confirms the whole frontend data path is working:
Iceberg output → curated GeoJSON → MapLibre → distinct warning / power-line / substation layers.
add the polished shell around the working map—without touching the map logic that now works:
- Header: Severe Weather Infrastructure Exposure Explorer
- Summary cards: 153 exposed assets · 124 power lines · 29 substations
- Event panel: Observed Tornado, Jan 10 2026, 4:00–4:15 PM
- Legend: warning / power lines / substations
- Layer toggles: let the user independently show/hide each infrastructure class
- Click interaction: click an asset for class/name/ID
- Provenance: Wherobots · NOAA NWS · Overture Maps
- Keep the map itself dominant rather than turning this into a dashboard full of widgets.