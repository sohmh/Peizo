# Zero-cost demonstration deployment: Cloudflare Pages + Render Free + R2

PIEZO is a static React/Vite frontend plus a FastAPI API. The Render blueprint uses the Free web-service plan and has no persistent disk. Render's filesystem is ephemeral, so production datasets must be part of the Git checkout or fetched from object storage at request time. The curated runtime bundle is checked into `data/runtime/processed/`; the two large NISAR COGs are public read-only R2 objects and are read remotely by Rasterio/GDAL for pixel sampling.

## Contents and data handling

- `data/catalog/` and `data/manifests/` are small source-backed JSON records and are tracked.
- `data/runtime/processed/` contains the 11 smaller runtime products (about 35 MiB): USGS/ADWR groundwater JSON/GeoJSON, basin boundaries, GRACE series, PRISM COG/quicklook, and both Frame 71 channel manifests/quicklooks.
- The two NISAR Frame 71 COGs (about 412 MiB total) stay under ignored `data/processed/` locally and are uploaded to R2. `data/runtime/asset_manifest.json` records their exact object keys, byte lengths and SHA-256 hashes.
- Duplicate, non-COG analysis GeoTIFFs are not deployed. Raw HDF5, NetCDF and teammate downloads remain in ignored `Datasets/` and are never copied into the runtime bundle.

To refresh the curated bundle from locally processed source products:

```powershell
python backend/scripts/prepare_runtime_bundle.py
```

Commit the updated `data/runtime/processed/` files and `data/runtime/asset_manifest.json`. Do not commit `data/processed/` or the two COGs under `data/runtime/`.

## 1. Create and populate Cloudflare R2

1. In Cloudflare, open **R2 Object Storage** and create a bucket such as `piezo-assets`.
2. Enable public read access for this derived-data bucket. Use a custom domain for more durable public serving; Cloudflare's `r2.dev` URL is rate-limited and intended for development/demo traffic. The source COGs are public scientific products, so do not upload credentials or raw downloads.
3. Authenticate Wrangler locally (`npx wrangler login`) and upload the two objects. Wrangler supports individual objects up to 315 MB; each PIEZO COG is below that limit:

```powershell
npx wrangler r2 object put piezo-assets/nisar/frame71_hhhh_phoenix_cog.tif --file=./data/processed/nisar/frame71_hhhh_phoenix_cog.tif
npx wrangler r2 object put piezo-assets/nisar/frame71_hvhv_phoenix_cog.tif --file=./data/processed/nisar/frame71_hvhv_phoenix_cog.tif
```

Wrangler uses your local Cloudflare login. No R2 access key or secret is needed by the deployed API because the bucket is public-read. Keep any credentials used for local S3-compatible tools out of the repository.
4. Verify both object URLs return HTTP 200 and their `Content-Length` matches the `bytes` value in `data/runtime/asset_manifest.json`. The SHA-256 values in that manifest identify the expected uploaded files. Also test a pixel sample via `/api/nisar/sample`; `/api/ready` performs an HTTP HEAD and size check for each remote COG.

R2 public URLs have this form:

- `https://<public-bucket-domain>/nisar/frame71_hhhh_phoenix_cog.tif`
- `https://<public-bucket-domain>/nisar/frame71_hvhv_phoenix_cog.tif`

Set `PIEZO_R2_PUBLIC_BASE_URL` to only the bucket root, for example `https://assets.example.org` or the bucket's `https://<id>.r2.dev` URL. Do not add `/nisar` or a trailing slash.

## 2. Deploy the API to Render Free

1. Push the repository to GitHub. Confirm the COGs and raw files are not staged (`git status --short`, `git check-ignore data/processed/nisar/frame71_hhhh_phoenix_cog.tif`). GitHub's ordinary Git push limit is avoided because the COGs are not in the repository.
2. In Render choose **New → Blueprint**, connect the repository and select the branch. Render reads root `render.yaml`; it creates `piezo-api` using `plan: free`, installs the lean API dependencies in `backend/requirements-render.txt`, and starts FastAPI on Render's injected `$PORT`.
3. Set these two service environment variables in Render:
   - `PIEZO_CORS_ORIGINS` — comma-separated exact Cloudflare Pages origins, no trailing slash (for example `https://piezo-demo.pages.dev`). Add only preview origins you actually use.
   - `PIEZO_R2_PUBLIC_BASE_URL` — the R2 public bucket root URL, with no trailing slash.
4. Deploy and test `https://<service>.onrender.com/api/health` (process health) and `https://<service>.onrender.com/api/ready` (data/product readiness). `/api/ready` should return HTTP 200 and `"status":"ready"`. If it returns 503, inspect `missing_assets` and `inaccessible_r2_cogs` in the response.

The blueprint already sets `PYTHON_VERSION`, `PIEZO_DATA_ROOT`, `PIEZO_PROCESSED_ROOT`, and `PIEZO_MANIFEST_ROOT`. Render supplies `PORT`. No database or persistent disk is required. Free web services spin down while idle and wake more slowly; their temporary filesystem is not used as the authoritative dataset store. Free plans also have usage limits, and Render may suspend service when a limit is reached if no payment method is configured. This deployment targets a challenge demonstration, not production availability guarantees.

## 3. Deploy the frontend to Cloudflare Pages

1. Create a Pages project from the same GitHub repository.
2. Set root directory to `frontend`, build command to `npm ci && npm run build`, and output directory to `dist`.
3. Set the build-time variable `VITE_API_BASE_URL=https://<service>.onrender.com` for production and any preview environment. Vite embeds this URL during build, so rebuild Pages after changing it.
4. Ensure Render's `PIEZO_CORS_ORIGINS` contains each Pages origin exactly.

## Required environment variables

| Where | Variable | Value |
| --- | --- | --- |
| Render | `PIEZO_CORS_ORIGINS` | Exact Pages production origin, plus any allowed preview origins, comma-separated and without trailing slashes |
| Render | `PIEZO_R2_PUBLIC_BASE_URL` | Public R2 bucket root URL, with no trailing slash |
| Cloudflare Pages | `VITE_API_BASE_URL` | Render API origin, e.g. `https://piezo-api.onrender.com` |

`PYTHON_VERSION`, the three data paths and `PORT` are configured by Render or the Blueprint. No R2 secrets are stored in Render for this public read-only bucket setup.

## Release checklist

- [ ] `GET /api/health` returns HTTP 200 and reports catalog/product status.
- [ ] `GET /api/ready` returns HTTP 200 with no missing assets and no inaccessible R2 COGs.
- [ ] `GET /api/layers` lists Frame 71 HHHH/HVHV quicklooks; image URLs load from the API.
- [ ] `GET /api/nisar/sample?longitude=-112.074&latitude=33.448&channel=HHHH` returns a real raster sample or an explicit masked/outside-crop response (never a substitute value).
- [ ] Check `/api/project/summary`, `/api/groundwater/stations`, `/api/rainfall/series`, `/api/water-storage/series`, and `/api/facilities`.
- [ ] In Pages, verify there are no failed API requests; test station/facility search and map layers on the deployed URL.
- [ ] Verify `git ls-files` contains no raw HDF5/NetCDF data, NISAR COGs, secrets or `data/processed/` products.

`/api/health` is a liveness endpoint so Render can restart the service if the process is down. `/api/ready` is the release gate: it checks required tracked assets and verifies the R2 objects respond and match their recorded byte lengths. Missing source products are reported as unavailable; the application does not substitute mock values.
