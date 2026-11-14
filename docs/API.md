# PIEZO API contract

FastAPI serves local catalog and derivative data under `/api`. Raster and image derivatives are served from `/derived/`; original source files are not exposed. Responses preserve provider, source units and study-area limitations where applicable. Missing products return an explicit availability status or HTTP 404 for direct item requests.

## Project and catalog

| Method / path | Purpose |
|---|---|
| `GET /api/health` | Service liveness plus catalog and local-product status; reports readiness metadata and missing assets. |
| `GET /api/ready` | Release readiness; returns 503 with missing assets or inaccessible/mismatched R2 COG objects. |
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

`GET /derived/{product_path}` serves regular files resolved below `PIEZO_PROCESSED_ROOT` (defaults to `data/processed/`). The two known Frame 71 NISAR COG names redirect to their public R2 objects when the files are not local; arbitrary paths cannot be used to access R2. Path traversal and missing files return 404. `/api/nisar/sample` reads a local COG or uses GDAL/Rasterio HTTP range reads against the configured R2 COG. It returns an explicit 503 if a configured remote COG cannot be read. The API never streams raw HDF5 products or generates substitute observations. `PIEZO_DATA_ROOT` configures catalog data, `PIEZO_PROCESSED_ROOT` configures processed runtime products, and `PIEZO_R2_PUBLIC_BASE_URL` configures the public bucket root. See [DEPLOYMENT.md](DEPLOYMENT.md) for hosting setup.
