# PIEZO architecture

## Initial structure

At the initial audit, the workspace had no application source code. PIEZO uses a small monorepo while leaving `Datasets/` as immutable source storage:

- `backend/`: FastAPI API, catalog services and reproducible processing scripts.
- `frontend/`: React, Vite, TypeScript, MapLibre and charts.
- `data/manifests/`: source and processing manifests.
- `data/interim/`, `data/processed/`: local generated products only; ignored by Git.
- `data/runtime/processed/`: curated, tracked lightweight deployment products; the large Frame 71 NISAR COGs are excluded and stored in public Cloudflare R2.
- `docs/`: inventory, evidence, methods, limitations and implementation tracker.
- `Datasets/`: supplied original files; never modified by processing.

## Data flow

```text
Datasets (immutable sources)
        | inspection / preprocessing
        v
data/manifests + data/interim + data/processed
        | catalog metadata / raster and vector services
        v
FastAPI (health, catalog, NISAR, groundwater, context, facilities, evidence)
        | REST and web map layers
        v
React/Vite + MapLibre + chart components
```

File-based catalogs are appropriate for this local MVP; PostGIS is not justified until concurrent edits, larger normalized queries or deployment requirements appear. Rasterio and supporting Python dependencies are installed in the project `.venv`; scripts write local COG, GeoTIFF, GeoJSON and JSON derivatives. The Render Free service serves committed lightweight products and reads the two R2-hosted NISAR COGs with GDAL `/vsicurl/` range requests for pixel samples. Do not send original multi-gigabyte HDF5 files to browsers.

## Frontend sections

Overview, Explore Map, NISAR Radar, Groundwater, Water Context, Facilities, and Evidence & Methods. Shared MapLibre layers include radar quicklooks, PRISM, USGS stations, ADWR GWSI wells and source-coordinate facilities. Charts show USGS station series, PRISM regional summary and GRACE mascon series. Layer provenance, units, scale and limitations are exposed in the UI and project documentation. Facilities use a normalized location register plus a linked disclosure/evidence table, with explicit gaps.

## Runtime and source policy

Use local configuration and no paid map dependency. Keep credentials out of source control. Data endpoints return explicit availability and empty collections when sources are absent. Raw paths are configuration inputs; only derived products are written by processing.
