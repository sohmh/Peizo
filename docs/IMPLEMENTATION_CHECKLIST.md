# Implementation checklist

## Phase 0 — audit

- [x] Read the full implementation guide.
- [x] Enumerate workspace recursively, including hidden files; inspect dataset structures and metadata.
- [x] Create inventory, dictionary, scientific method, architecture, limitations, team intake and facility evidence documentation.
- [x] Confirm Phoenix lies in both NISAR footprints; document that two frames are same-pass/same-date.
- [x] Filter USGS and ADWR well measurements to the documented Phoenix rectangle; validate 8 basin and 14 subbasin intersections.
- [x] Review GWSI README/handbook and GLDAS script; verify duplicate Salt-independent report copies by SHA-256.
- [x] Source two Phoenix-area facility records and enter evidence/disclosure gaps; public search remains incomplete.

## Phase 1 — foundation

- [x] Backend FastAPI catalog, health, evidence, facility, groundwater, rainfall, GRACE and NISAR endpoints.
- [x] React/Vite/TypeScript scientific shell, interactive MapLibre layers and feature panels.
- [x] Run instructions, environment example, ignore rules and documented API.

## Phase 2 — NISAR

- [x] HDF5 inspection and Phoenix extraction scripts use source groups, axes and masks.
- [x] Rasterio produces source-CRS GeoTIFF/COG and transparent display quicklooks.
- [x] Validate HDF5 Phoenix intersection and derived CRS, transform, masks, bounds, pixel counts and quicklooks.
- [x] Store channel manifests and test source/output metadata.

## Phase 3 — interactive radar

- [x] Display frame 71 HHHH/HVHV Frequency A quicklooks with channel selection, legend and limitations.
- [x] Provide source-value pixel lookup on map clicks.
- [x] Clearly state temporal comparison is unavailable until a compatible acquisition date is added.

## Phase 4 — supplemental data and Data-Centre Observatory

- [x] Preserve and chart USGS observations by parameter, unit and datum; map ADWR GWSI sites. ADWR GWSI WW_LEVELS joined by site; chart definitions prevent mixing depth and elevation.
- [x] Map PRISM October 2026 and chart rainfall; chart GRACE/JPL series at coarse mascon scale.
- [x] Map Phoenix-relevant ADWR basin/subbasin boundaries; Salt River report numeric extraction remains open.
- [x] Add sourced facility/disclosure/evidence schemas, searchable/filterable directory, profiles and verified-coordinate map layer.
- [x] Display unavailable facility water quantities, unknown water source and incomplete public search without treating gaps as zero.

## Phase 5–6 — evidence, polish, delivery

- [x] Add the regional evidence profile, source register, glossary, methods and limitations panel.
- [ ] Review full keyboard/screen-reader behavior and responsive map controls.
- [x] Run backend tests (18 passing), frontend tests (4 passing) and production build.
- [x] Prepare Render Free Blueprint without a persistent disk and split lean API dependencies from local scientific processing dependencies.
- [x] Curate the tracked Phoenix runtime bundle (35 MiB); exclude large NISAR COGs, raw satellite data and duplicate analysis rasters from Git.
- [x] Add R2 COG URL redirects, remote Rasterio pixel reads, SHA-256/size inventory, explicit readiness checks and frontend request-failure messages.
- [x] Document Cloudflare R2, Render Free and Pages setup with all manual environment variables.
- [ ] Create the R2 bucket, upload/verify the two public NISAR COGs, then validate the deployed Render and Pages URLs.
- [ ] Browser smoke/accessibility review; local HTTP requests are blocked by this environment’s socket policy.
- [x] Document local startup and known data acquisition gaps.
