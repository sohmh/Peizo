# Deployment preparation: Cloudflare Pages + Render

The application is a compatible static React/Vite frontend and FastAPI API. No production deployment has been created or tested yet. The production URL and hosted account are not available in this workspace, so the final remote smoke test remains a release gate.

## Frontend: Cloudflare Pages

Create a Pages project from the repository with:

- Root directory: `frontend`
- Build command: `npm ci && npm run build`
- Build output directory: `dist`
- Production environment variable: `VITE_API_BASE_URL=https://<your-render-service>.onrender.com`

Set `VITE_API_BASE_URL` for preview deployments too, using the matching API origin. Vite embeds this value at build time. The app uses it for API calls, GeoJSON layers, raster quicklooks and the derived-product API. Set the corresponding API `PIEZO_CORS_ORIGINS` to the exact Pages production and preview origins (comma-separated, no trailing slash). Do not use `*` for a public release.

## API: Render

`render.yaml` defines the FastAPI web service, health check, environment and a persistent disk. Review the plan and disk pricing against the account before creating the service. Set `PIEZO_CORS_ORIGINS` in Render to the exact Pages origins.

The service reads catalog JSON and manifests from tracked `data/catalog/` and `data/manifests/`. It reads generated products from `PIEZO_PROCESSED_ROOT`, set by the blueprint to `/var/data/piezo/processed`. Populate that mounted path with the **processed deployment bundle** before release. The full local processing directory is about 878 MB; deployment does not need to include the duplicated analysis GeoTIFFs. Retain these runtime products:

- `nisar/`: each published channel's `*_phoenix_cog.tif`, `*_quicklook.png`, and `*_manifest.json` (the COG is used by `/api/nisar/sample`; the PNG is used by the map).
- `groundwater/`: `phoenix_groundwater.json`, `adwr_gwsi_phoenix.json`, `adwr_gwsi_phoenix.geojson`.
- `context/`: `phoenix_basin_boundaries.geojson`.
- `grace/`: `phoenix_mascon_series.json`.
- `prism/`: the monthly COG, quicklook PNG, and manifest-referenced output files.

Transfer these derived products to the Render disk or an approved mounted asset volume using an authenticated deployment workflow. Keep source HDF5, NetCDF and original download folders out of GitHub. Do not expose an unauthenticated upload endpoint. `/derived/*` serves files only from the configured processed root and rejects path traversal.

## Release checks

1. Set the Cloudflare `VITE_API_BASE_URL` and Render `PIEZO_CORS_ORIGINS`; trigger a fresh Pages build after changing the former.
2. Populate the Render persistent disk. Verify `/api/health`, `/api/project/summary`, `/api/layers`, `/api/groundwater/stations`, `/api/rainfall/series`, `/api/water-storage/series`, and `/api/facilities`.
3. Confirm the production browser's network panel has no failed `/api/*` or `/derived/*` requests; inspect map tiles separately because the OpenStreetMap basemap requires internet access.
4. Confirm both NISAR COGs and quicklooks, the groundwater and basin GeoJSON, PRISM outputs, and GRACE series return successfully from the hosted API.
5. Verify Pages production and preview origins are allowed by Render CORS. Test the actual deployed URL before submission; a localhost build is not a substitute.

The persistent disk is runtime storage, not source control. Preserve the raw `Datasets/` files locally and repeat processing from those originals if derived outputs need to be regenerated.
