# PIEZO API contract

FastAPI serves local catalog and derivative data under `/api`. Raster and image derivatives are served from `/derived/`; original source files are not exposed. Responses preserve provider, source units and study-area limitations where applicable. Missing products return an explicit availability status or HTTP 404 for direct item requests.

## Project and catalog

| Method / path | Purpose |
|---|---|
| `GET /api/health` | Local service and catalog health. |
| `GET /api/project/summary` | Dataset, scene, facility and groundwater counts/status. |
| `GET /api/datasets` | Dataset source and validation catalog. |
| `GET /api/layers` | Dynamic layer availability and derivative URLs. |
| `GET /api/evidence/phoenix` | Observed, modeled, reported and regional evidence profile with limitations. |

## NISAR

| Method / path | Purpose |
|---|---|
| `GET /api/nisar/scenes` | Inspected scene metadata. |
| `GET /api/nisar/scenes/{scene_id}/channels` | Channel processing state for one scene. |
| `GET /api/nisar/sample?longitude={lon}&latitude={lat}&channel={HHHH\|HVHV}` | Source value at a WGS84 location for processed frame 71 Frequency A; returns `masked` when source mask is invalid and 404 outside crop/unavailable channel. |

## Groundwater and regional context

| Method / path | Purpose |
|---|---|
| `GET /api/groundwater/stations` | Combined station directory, separate provider counts and measurement definitions. The response reports the subset of ADWR inventory sites with joined level measurements. ADWR identifiers use `ADWR:{SITE_ID}`. |
| `GET /api/groundwater/stations.geojson` | USGS station map points. |
| `GET /api/groundwater/adwr-sites.geojson` | ADWR GWSI well inventory points with source fields. |
| `GET /api/groundwater/stations/{station_id}/observations?parameter_code={code}&unit={unit}&vertical_datum={datum}` | Time series for a selected measurement definition. The UI always requests one available definition so different units or vertical references are not combined. |
| `GET /api/context/basins.geojson` | Phoenix-rectangle clipped ADWR basin and subbasin context. |
| `GET /api/rainfall/series` | PRISM monthly precipitation cell mean and count, including valid-cell-center filtering and native spatial support. |
| `GET /api/water-storage/series` | GRACE/GRACE-FO total-water-storage anomaly series at mascon support. |

## Facilities

| Method / path | Purpose |
|---|---|
| `GET /api/facilities` | Search/filter directory records plus attached disclosures. |
| `GET /api/facilities/summary` | Source-published coordinates, verified status and reported water-quantity coverage. |
| `GET /api/facilities/{facility_id}` | Profile plus claim-targeted evidence references. |
| `GET /api/facilities/{facility_id}/water-disclosures` | Facility-specific disclosure records. |

## Derived files

`GET /derived/{product_path}` serves only regular files resolved below `PIEZO_PROCESSED_ROOT` (defaults to `data/processed/`). Path traversal and missing files return 404. COGs and analysis rasters are file-backed derivatives; the API does not stream the raw multi-gigabyte HDF5 products. `PIEZO_DATA_ROOT` configures the catalog and manifest root. See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting setup.
