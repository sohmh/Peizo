# Project PIEZO

PIEZO is an evidence-led geospatial observatory for Phoenix, Arizona. It combines NISAR surface radar observations with local groundwater, rainfall, regional water-storage context and source-backed data-centre evidence. It does not infer groundwater depletion or facility causality from radar alone.

## Current status

The application maps frame 71 NISAR HHHH/HVHV Frequency A quicklooks, USGS measurements, 6,765 ADWR inventory sites (5,152 have at least one joined depth/elevation value), one PRISM monthly precipitation summary, and 261 coarse GRACE/GRACE-FO mascon records. The 507 USGS stations and ADWR sites are provider-specific counts, not a deduplicated well census. The ADWR measurement workbook contains 48,846 Phoenix-joined rows; 46,360 rows have a water-level value and 2,486 have neither field populated. Frames 71 and 72 are adjacent spatial scenes from the same pass and date; there is no temporal comparison. The Data-Centre Observatory has six source-backed directory records; only Edged has source-published coordinates, and no site-specific withdrawal or consumption quantity is verified. Status remains proposed only where a municipal record identifies a proposal and unknown where current operation is not established.

See [docs/DATA_INVENTORY.md](docs/DATA_INVENTORY.md), [docs/API.md](docs/API.md), [docs/SCIENTIFIC_METHOD.md](docs/SCIENTIFIC_METHOD.md), and [docs/IMPLEMENTATION_CHECKLIST.md](docs/IMPLEMENTATION_CHECKLIST.md).

## Run locally

Requirements: Python 3.11+, Node.js/npm. Python dependencies are listed in `backend/requirements.txt`; on Windows use a compatible Rasterio wheel or conda-forge environment if needed.

Backend (from repository root):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
npm install
npm run dev
```

Open the local Vite URL shown by npm. The Vite development server proxies `/api` and `/derived` to FastAPI on port 8000. The OpenStreetMap basemap needs an internet connection; local overlays and catalog data are served by the API.

## Data handling

Keep originals under `Datasets/` untouched. Run the repeatable initial processors from the repository root:

```powershell
.\.venv\Scripts\python.exe backend\scripts\inspect_nisar.py
.\.venv\Scripts\python.exe backend\scripts\process_nisar.py --channel HHHH --frequency frequencyA --skip-checksum
.\.venv\Scripts\python.exe backend\scripts\process_nisar.py --channel HVHV --frequency frequencyA --skip-checksum
.\.venv\Scripts\python.exe backend\scripts\prepare_groundwater.py
.\.venv\Scripts\python.exe backend\scripts\prepare_adwr_gwsi.py
.\.venv\Scripts\python.exe backend\scripts\prepare_basin_context.py
.\.venv\Scripts\python.exe backend\scripts\prepare_prism.py
.\.venv\Scripts\python.exe backend\scripts\prepare_grace.py
```

Scripts write derived products under `data/interim/`, `data/processed/` and manifests under `data/manifests/`. ADWR site points, joined level records, and clipped Phoenix basin/subbasin display boundaries are written under `data/processed/groundwater/` and `data/processed/context/`. Raw multi-gigabyte downloads and secrets must not be committed. The current two NISAR products are same-pass frames on 2026-10-28; a compatible second date is needed for temporal comparison.

## Tests

From the repository root, run the API and data-product tests with:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

Run the production frontend build with:

```powershell
cd frontend
npm run build
```

Run the frontend search/filter regression tests from `frontend/` with `npm test`.

## Deployment preparation

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Cloudflare Pages and Render configuration, environment variables, processed-asset staging and remote release checks. The production site has not been deployed from this workspace; its real URL must pass the documented smoke checks before submission.
