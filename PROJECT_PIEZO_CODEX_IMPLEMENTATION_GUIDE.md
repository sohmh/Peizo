# PROJECT PIEZO — Codex Implementation Guide

**Project:** PIEZO  
**NASA Space Apps Challenge:** Dancing with the SARs  
**Study area:** Phoenix metropolitan region, Arizona, USA  
**Primary satellite data:** NASA–ISRO NISAR Level-2 GCOV (L-band)  
**Purpose:** Build a polished, evidence-led geospatial web application that helps users explore radar-observed surface characteristics and change in the Phoenix region, with groundwater, water-storage, rainfall and human water-demand context where supporting datasets are available.

---

# PART A — MASTER PROMPT FOR CODEX

Copy the entire prompt below into Codex after opening the Project PIEZO folder as the workspace. Keep this Markdown guide in the workspace so Codex can refer back to it.

---

## YOUR ROLE

Act as a senior geospatial software engineer, remote-sensing scientist, GIS developer, data engineer, UI/UX designer and technical lead. You are responsible for helping implement **Project PIEZO**, an end-to-end, working software project for the NASA Space Apps Challenge **Dancing with the SARs**.

Do not merely create a static mock-up. Build a functional application with a real data-ingestion and processing workflow, a geospatial backend, and an interactive frontend. The software must use the actual files present in this workspace. Do not fabricate observations, measurements, facility water use, satellite coverage, time series, statistics, or analytical results.

## 1. PROJECT CONTEXT AND FIXED DECISIONS

- The selected study area is **Phoenix, Arizona, USA**. Do not switch the study area to India or another location.
- The project is called **Project PIEZO**.
- The NASA challenge is **Dancing with the SARs**. Its central requirement is an interactive application that uses NISAR radar remote-sensing data to track and visualize one or more types of Earth's surface change.
- Our application focuses on Phoenix-area surface/radar observations and water-resource context. The product should help users explore possible relationships between surface conditions, land deformation where valid measurements exist, groundwater stress, rainfall/storage context and human water demand.
- The first selected NISAR scene in ASF Vertex is a **NISAR L2 GCOV HDF5** scene. The ASF screen showed a selected scene with approximately **7.24 GB** of science data and metadata files. The visible scene detail included **Frame 72, Track 56, descending flight direction, full frame coverage, HH/HV polarizations, CRID P05036**, with acquisition on **28 October 2026**. Another nearby listing showed an acquisition around **28 October 2026 02:15 UTC**. Treat the actual HDF5 metadata as authoritative if the filename, exact start/end time or other details differ from this screen summary.
- The HDF5 product is large. Do not load the entire file into browser memory or attempt to render the raw HDF5 directly in the frontend.
- We may have only one NISAR GCOV acquisition initially. Build a useful single-scene MVP first, and make multi-date comparison available only when compatible additional acquisitions are actually present.
- Do not assume all supplemental datasets have already been downloaded. Inspect the workspace and create a clear inventory of what is present, missing, incomplete or invalid.

## 2. SCIENTIFIC INTEGRITY — NON-NEGOTIABLE

The application must not make claims beyond what the data supports.

1. **GCOV is not a direct groundwater sensor.** NISAR GCOV contains geocoded polarimetric covariance/backscatter information. Backscatter is influenced by surface roughness, dielectric properties/moisture, vegetation, geometry, land cover, acquisition conditions and other factors. Changes in backscatter can be consistent with changes in surface conditions, but do not independently prove groundwater depletion or groundwater extraction.
2. **Do not claim NISAR GCOV directly measures deep groundwater.** Describe it as radar-derived surface observations/context.
3. **Subsidence is not automatically proof of groundwater pumping.** If deformation data from a valid interferometric workflow or a suitable external source is available, label it as observed/estimated ground deformation and discuss groundwater extraction only as a possible driver requiring independent corroboration.
4. **GCOV and GUNW are different products.** Do not treat GCOV as an interferogram. If a GUNW product is present, inspect its metadata and assess whether a defensible displacement workflow is feasible. GUNW processing is an optional advanced feature, not a prerequisite for the initial MVP.
5. **GRACE/GRACE-FO measures total water storage changes at coarse spatial resolution**, not facility-scale groundwater. Any groundwater residual must account for relevant non-groundwater storage components and uncertainty. Do not downscale GRACE to individual facilities or neighbourhoods and imply it is a direct local measurement.
6. **CGWB is not a Phoenix data source.** For Phoenix, use appropriate United States / Arizona sources, such as USGS groundwater monitoring and Arizona Department of Water Resources (ADWR) records, if available and legally accessible. Do not use Indian CGWB data in this Phoenix implementation.
7. Rainfall is contextual information, not direct proof of recharge. Use an appropriate US source such as NOAA/NCEI or another authoritative source, documenting temporal and spatial resolution.
8. Facility location does not prove water source, withdrawal or consumption. Use facility water-demand information only where a credible public disclosure or regulatory record supports it. Distinguish withdrawal from consumption, potable/fresh water from reclaimed/recycled water, planned from actual values, and annual from daily values.
9. Preserve native spatial and temporal resolution. Never make coarse data appear to have precise local detail by resampling it without clearly stating that it is a visualization operation.
10. Every displayed analytical result must be traceable to its source, processing method, date range, units and limitations.

When evidence is insufficient, show **“Data unavailable”**, **“Not assessed”** or **“Insufficient evidence”**. Do not fill gaps with invented values.

## 3. FIRST ACTION: AUDIT THE WORKSPACE BEFORE CODING

Before implementing features, inspect the complete repository and data directory.

- List all files and folders, including hidden files, and identify the project structure.
- Find all HDF5/H5, XML, NetCDF/NC, GeoTIFF/TIFF, COG, CSV, XLSX, JSON, GeoJSON, shapefile, PDF and text files.
- Identify the selected NISAR GCOV HDF5 and its matching metadata XML. Check whether the HDF5 is fully downloaded or only a partial file.
- Read the XML metadata and inspect the HDF5 internal hierarchy, datasets, attributes, dimensions, coordinate grids, projection information, units, fill values and polarization/frequency groups. Use `h5py` and/or GDAL tools as appropriate.
- Confirm the actual spatial footprint and CRS from the data, not just from a filename or screenshot. Verify that it covers the Phoenix study area.
- Record acquisition start/end time, orbit direction, track/frame, product version/CRID, polarization, pixel spacing, coordinate reference system, bounding box, nodata/fill values and source identifiers.
- Check whether multiple dates are present and whether they are comparable in coverage, polarization, frequency, orbit direction, product version and processing configuration.
- Inventory all supplemental datasets. Identify which are real and ready, which are partial, and which are absent.
- **Important: teammate-provided datasets are first-class project inputs.** The workspace may contain additional datasets downloaded by another team member, with unfamiliar filenames, folder names, formats or subject matter. Recursively inspect the entire workspace, including newly added folders and archives (without extracting or modifying originals until safe to do so). Do not restrict the audit to the NISAR file or to the dataset list already mentioned in this guide.
- For every teammate-provided file, determine its provider/source, what it measures, geographic and temporal coverage, variables/bands, units, CRS, resolution, quality flags, license/usage terms and relationship to the Phoenix study area. Read accompanying README files, metadata, data dictionaries, PDFs and sidecar files. Link files that belong to the same dataset or download package.
- Assess each dataset for scientific relevance and technical usability. Classify it as `ready`, `usable after processing`, `context only`, `needs verification`, `out of scope`, `duplicate`, `corrupt/incomplete` or `not relevant to Phoenix`. Explain the reason; do not discard a dataset merely because its format or name is unfamiliar.
- Incorporate every relevant, validated teammate dataset into the data catalog and the appropriate application feature. Do not merely list the files in documentation: build ingestion/processing and user-facing integration where the dataset adds evidence. If a dataset is useful but cannot be integrated within the MVP, document the blocker and a concrete next step.
- Compare teammate datasets against existing sources to identify duplicates, complementary variables, overlapping coverage, differing units, conflicting values and temporal mismatches. Do not silently merge conflicting sources.
- Do not move, rename, overwrite, delete, compress or modify original source data. Treat original downloads as immutable.
- If a required detail cannot be determined, state what is unknown and how to verify it.

Create these initial documentation files:

- `docs/DATA_INVENTORY.md` — files found, formats, sizes, coverage, dates, source and status.
- `docs/DATA_DICTIONARY.md` — variables, units, dimensions, CRS, nodata, descriptions and processing notes.
- `docs/SCIENTIFIC_METHOD.md` — methods, assumptions, limitations and validation plan.
- `docs/ARCHITECTURE.md` — system components and data flow.
- `docs/KNOWN_LIMITATIONS.md` — missing datasets and claims the application cannot currently make.
- `docs/TEAM_DATA_INTEGRATION.md` — teammate-provided dataset inventory, validation results, feature mapping, integration decisions and outstanding blockers.
- `docs/FACILITY_EVIDENCE_REGISTER.md` — source-by-source register for facility locations, operating status and water-use/source disclosures, including page/section references.

Do not begin with a made-up dashboard. First establish what the actual files contain.

## 4. PRODUCT VISION AND USER EXPERIENCE

Build a professional, modern geospatial intelligence platform called **PIEZO**. It should feel like a credible scientific monitoring tool rather than a generic admin dashboard.

Primary user groups:
- Scientists and remote-sensing learners
- Water-resource managers and planners
- Local decision-makers
- Educators, students and the general public

The interface should make complex Earth-observation information understandable. It must clearly distinguish satellite observations, ground measurements, modeled estimates, contextual indicators and reported facility disclosures.

### Main application sections

1. **Overview / Mission Control**
   - Project introduction and Phoenix study-area map.
   - Compact status indicators for datasets available, dates covered, last processing run and data-quality state.
   - Key findings only when computed from real data.
   - A clear explanation of what PIEZO can and cannot infer.

2. **Interactive Geospatial Explorer**
   - Main map centered on Phoenix, Arizona.
   - Layer controls for study-area boundary, NISAR GCOV layers, ground-monitoring wells, groundwater-related public data, rainfall, water-storage context, land-cover/context layers and verified facilities.
   - Layer opacity, legend, visibility toggles, zoom-to-layer and informative popups.
   - Show the source, date, units, resolution and limitations in layer metadata.
   - Do not display a layer if its source data is missing; show an honest unavailable state instead.

3. **NISAR Radar Observatory**
   - Display processed GCOV imagery derived from the real HDF5 file.
   - Provide available HH and HV layers and other valid channels only after confirming their presence in the file.
   - Provide appropriate contrast stretch, nodata handling and optional dB conversion only where scientifically appropriate for the stored quantity.
   - Include a pixel inspection tool showing coordinates and values, with units and channel labels.
   - Clearly explain that GCOV is a radar surface observation, not a groundwater-depth map.
   - If multiple compatible acquisitions exist, add a date selector and side-by-side/swipe comparison. If only one exists, show a single-date view and explain that temporal change detection requires another compatible acquisition.

4. **Groundwater and Water Resources**
   - Integrate USGS/ADWR groundwater well or water-level observations only when real data has been acquired.
   - Plot time series by monitoring station, preserving station ID, observation date, measurement type and units.
   - Make it explicit whether a value represents depth to water, water level elevation or another quantity. Do not mix them.
   - If values are depth below land surface, explain that a larger depth generally means the water table is farther below the land surface.
   - Show station coverage and data gaps.

5. **Rainfall and Climate Context**
   - Use a verified authoritative Phoenix/Arizona rainfall source.
   - Show time series and spatial maps at the source's true resolution.
   - Explain that rainfall context alone does not establish aquifer recharge.

6. **Regional Water Storage Context**
   - If GRACE/GRACE-FO or another suitable source is present, show it at its actual native/coarse resolution.
   - Clearly label total water storage anomaly versus groundwater storage residual. Never conflate them.
   - Include spatial-resolution and uncertainty caveats directly in the interface.

7. **Data-Centre Observatory — REQUIRED CORE FEATURE (not optional or stretch)**
   - A dedicated data-centre feature is a mandatory part of the Project PIEZO MVP, alongside the NISAR radar explorer. It must be implemented as a real, data-backed feature, not a decorative map-marker layer or placeholder dashboard.
   - Build a dedicated **Data Centres** page/section and a corresponding layer in the main Phoenix map. The page must help users understand where data centres are located in the Phoenix metropolitan region, what is publicly known about their water sourcing and water use, and what remains undisclosed.
   - Discover and use all relevant teammate-provided facility datasets and disclosures. Also inspect credible public sources where additional evidence is needed. Prefer operator sustainability/water reports, official company documents, Arizona/local regulatory and planning records, environmental review documents, public utility/water-provider records and other primary sources.
   - Create a normalized facility register with one record per facility/campus where possible. At minimum include: stable internal facility ID, facility/campus name, operator/owner, public street address if available, latitude/longitude, city, county, state, operational status (operating, under construction, proposed, closed, unknown), facility type, source URL/document, source publication date, date accessed, verification status and confidence/reliability notes.
   - Distinguish individual campuses from operators, company headquarters, cloud regions, announced projects and permitted sites. Do not map a location as a confirmed operating data centre unless the evidence supports that status.
   - Create a separate water-disclosure table linked to facility IDs. Capture reported quantity, unit, reporting period, withdrawal vs consumption, water source (municipal/potable, groundwater, surface water, reclaimed/recycled, other, unspecified), planned vs actual, direct vs indirect if stated, source document/URL, page/section/table reference, publication date and interpretation notes.
   - Preserve distinctions between withdrawal and consumption, fresh/potable and reclaimed/recycled water, site-specific and company-wide totals, actual and projected values, and annual and daily rates. Convert units only in a transparent derived field while retaining the original reported value and unit.
   - If a disclosure is company-wide or regional and cannot be attributed to a Phoenix campus, label it at the correct scope. Never allocate a corporate total across campuses or estimate facility usage from building size, cooling technology, capacity or location unless a clearly documented and explicitly labelled model is later approved.
   - For facilities with no public water-use data, display **“Not publicly disclosed / no verified site-specific figure found”** rather than zero. Keep unknown source type as unknown. Do not infer groundwater use from proximity to a well or aquifer.
   - The interface must include: (a) map of verified facilities with status and verification filters; (b) searchable facility list; (c) facility detail panel; (d) evidence-backed water-disclosure view; (e) filters for operator, city/county, status, water source and disclosure availability; (f) a clear distinction between site-specific, regional and company-wide disclosures; and (g) a data-gap summary showing how many records have verified locations, operating status and site-specific water disclosures.
   - Show source citations and evidence quality for each facility and water figure. Users must be able to inspect the source reference. Maintain an evidence ledger so a reviewer can trace every displayed facility fact to its source document and page/section.
   - Allow comparison only between comparable metrics with matching scope, reporting period, units and definitions. Do not rank facilities by water use when records are incomplete or non-comparable.
   - Facilities may be shown alongside NISAR, groundwater, rainfall and storage layers for spatial context, but explicitly state that proximity or temporal coincidence does not establish that a facility caused radar change, subsidence or groundwater decline.

8. **Regional Evidence Profile**
   - A transparent evidence summary for Phoenix or a selected subregion.
   - Separate observed data, modeled data, reported data and hypotheses.
   - Show evidence coverage, date ranges, confidence/quality notes, missing data and limitations.
   - Do not create an arbitrary composite “water stress score”. If a composite indicator is later proposed, document normalization, weighting, uncertainty, missing-data handling and sensitivity testing first.

9. **Methods, Sources and About**
   - Explain the data pipeline and scientific methodology in plain language.
   - Show source links, citations, product IDs, versions, access dates and licenses where available.
   - Include a glossary for SAR, backscatter, polarization, GCOV, GUNW, coherence, interferometry, subsidence, groundwater level, total water storage and anomaly.

## 5. RECOMMENDED TECHNICAL ARCHITECTURE

Use a clean, maintainable architecture. Prefer a modular monorepo unless the existing repository strongly suggests otherwise.

### Frontend
- React + Vite + TypeScript.
- MapLibre GL JS for interactive maps (use a suitable basemap provider; keep tokens in environment variables if needed).
- Plotly or ECharts for charts.
- A consistent component system and responsive design.
- Use accessible controls, clear legends, loading states, error states and empty states.

### Backend
- Python + FastAPI.
- Pydantic models for API contracts.
- Rasterio/GDAL for geospatial raster handling.
- h5py for HDF5 inspection and extraction.
- xarray/netCDF4 for NetCDF datasets if present.
- GeoPandas, Shapely, pyproj and NumPy/pandas for vector and tabular processing.
- PostgreSQL + PostGIS if a database is justified by the data model and available development environment. For an initial local prototype, a simple documented file-based catalog may be acceptable; do not add infrastructure for its own sake.

### Geospatial storage and serving
- Preserve original NISAR HDF5 and metadata files.
- Generate derived GeoTIFF/COG products for map rendering, keeping the originals unchanged.
- Use appropriate tiling/overviews and compression for large rasters.
- Serve raster layers as COGs with range requests or a suitable tile service. Do not send multi-gigabyte HDF5 files to the browser.
- Store vector layers as GeoJSON for small data or PostGIS for larger/more complex data.
- Document coordinate reference systems and transformations. Use WGS84 (EPSG:4326) for web map display where appropriate, while preserving source CRS in derived-data metadata.

### Suggested repository structure

```text
project-piezo/
├── README.md
├── .gitignore
├── .env.example
├── docs/
│   ├── DATA_INVENTORY.md
│   ├── DATA_DICTIONARY.md
│   ├── SCIENTIFIC_METHOD.md
│   ├── ARCHITECTURE.md
│   └── KNOWN_LIMITATIONS.md
├── data/
│   ├── raw/                 # Original downloads; never edit
│   ├── interim/             # Temporary/normalized processing outputs
│   ├── processed/            # COGs, GeoJSON and analysis-ready files
│   └── manifests/            # Source and processing manifests
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── schemas/
│   ├── scripts/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── features/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── styles/
│   └── package.json
└── scripts/
    ├── inventory_data.py
    └── run_pipeline.py
```

Adapt this structure to the existing workspace instead of blindly replacing it.

## 6. NISAR GCOV PROCESSING REQUIREMENTS

Build this as a reproducible Python pipeline.

### Stage 1 — Inspect
- Read HDF5 groups, datasets and attributes.
- Identify the exact science datasets for covariance/backscatter channels and their frequency/polarization definitions.
- Read geolocation grids or projection/geotransform information.
- Determine whether the data is already geocoded and how coordinates are represented.
- Confirm units, scaling, fill values, masks and valid-data ranges from product metadata/user guide. Do not guess.
- Print a concise inspection report and save it under `data/manifests/`.

### Stage 2 — Extract
- Extract only the channels needed for the MVP.
- Preserve the original numeric values and source metadata.
- Apply scale factors and masks only when specified by product metadata.
- Do not assume a dataset named HH is necessarily a calibrated intensity layer without checking the product specification.
- Keep a record of every transformation.

### Stage 3 — Geospatial conversion
- Convert the selected channels into georeferenced raster files (prefer Cloud Optimized GeoTIFFs).
- Preserve the correct CRS, geotransform, dimensions, nodata and pixel size.
- If geolocation arrays rather than a simple affine transform are used, use a valid geolocation-aware warp workflow. Do not assign an arbitrary EPSG code or approximate transform.
- Reproject to web map CRS only for display derivatives; retain a source-CRS analysis product.
- Validate output bounds against the source metadata and Phoenix study-area geometry.

### Stage 4 — Visualization products
- Generate display-ready imagery with a documented stretch, such as percentile-based contrast stretch, while retaining raw quantitative layers separately.
- Provide a legend and channel description.
- If conversion to decibels is appropriate for the specific stored variable, document the formula and input units. Never apply a logarithmic transform to an already logarithmic quantity.
- Generate overviews/tiles suitable for a responsive web map.

### Stage 5 — Quality assurance
- Compare source and derived dimensions, CRS, bounds, pixel size and valid-pixel counts.
- Check for all-nodata output, invalid coordinates, unexpected range, flipped imagery and misalignment.
- Render a quick-look PNG for visual QA.
- Confirm the processed footprint intersects the Phoenix study area.
- Save a JSON processing manifest with source file, source checksum if feasible, product metadata, code version, parameters, outputs, timestamp and warnings.

### Stage 6 — Temporal comparison (only when possible)
- Check that scenes have comparable product versions, frequency/polarization, orbit/look geometry, spatial overlap, calibration and processing conditions.
- Align rasters and use consistent masks and display stretches.
- Compute difference/ratio products only when the variables are scientifically comparable.
- Label the output as a radar-observation difference, not a groundwater-change map.
- Include acquisition dates and known confounding factors.

## 7. DATA ACQUISITION AND SOURCE STRATEGY

Do not automatically download large external datasets or scrape sites without first reporting what is missing and asking for approval if the download is large, requires credentials, has usage restrictions or would materially expand project scope.

Potential authoritative sources to investigate for Phoenix:

- **NISAR GCOV/GUNW:** NASA Earthdata / Alaska Satellite Facility (ASF) DAAC / ASF Vertex. Preserve HDF5 and XML metadata.
- **Groundwater and wells:** USGS National Water Information System (NWIS) and relevant Arizona Department of Water Resources datasets. Confirm station location, parameter, units, measurement type, date coverage and licensing/terms.
- **Groundwater basin context:** ADWR groundwater basin/active management area boundaries and published reports, where relevant.
- **Rainfall/climate:** NOAA/NCEI or other authoritative US climate datasets with documented resolution and time coverage.
- **Total water storage:** GRACE/GRACE-FO from NASA/JPL PO.DAAC or other authoritative NASA distribution. Confirm product version and native resolution.
- **Land cover/context:** USGS, MRLC/NLCD or other authoritative sources if useful and compatible with the study period.
- **Data centres and water demand (mandatory feature):** Teammate-provided facility lists, operator sustainability/water reports, Arizona/local regulatory and planning documents, environmental review documents, public utility/water-provider records and credible public records. Treat each facility location/status and each water-use figure as a separately sourced claim. Prefer primary sources and preserve page/section references. Search for Phoenix-area campuses and projects, but distinguish confirmed operating facilities from proposed, under-construction or unverified sites.
- **All teammate-provided datasets:** Treat every additional dataset supplied by the team as a potential input, regardless of file format or whether it appears in the original dataset plan. Inspect metadata and provenance, validate Phoenix coverage and time period, assess scientific relevance, then integrate relevant datasets into the catalog, processing pipeline, map, analytics or facility feature as appropriate.

For every dataset create a source manifest containing:
- Dataset ID and title
- Provider and exact source URL
- Access/download date
- Product version/collection and DOI or granule ID, if applicable
- Original filename and checksum if feasible
- Spatial coverage and CRS
- Temporal coverage and acquisition/reporting dates
- Native spatial and temporal resolution
- Variables/bands and units
- License/usage restrictions
- Processing history
- Known caveats and quality flags

## 8. API DESIGN

Create a small, documented REST API. Suggested endpoints (adjust as implementation requires):

- `GET /api/health` — backend and data-catalog health.
- `GET /api/project/summary` — computed summary and data availability.
- `GET /api/datasets` — dataset catalog with metadata and readiness state.
- `GET /api/layers` — available map layers and their metadata/URLs.
- `GET /api/nisar/scenes` — available NISAR scenes and acquisition metadata.
- `GET /api/nisar/scenes/{scene_id}/channels` — actual extracted channels.
- `GET /api/groundwater/stations` — stations with available observations.
- `GET /api/groundwater/stations/{station_id}/observations` — station observations.
- `GET /api/rainfall/series` — rainfall time series where data exists.
- `GET /api/water-storage/series` — storage observations/estimates where data exists.
- `GET /api/facilities` — verified facility records, with status and evidence metadata.
- `GET /api/facilities/{facility_id}` — facility profile and linked evidence.
- `GET /api/facilities/{facility_id}/water-disclosures` — sourced water-use/source disclosures, retaining reporting scope and units.
- `GET /api/facilities/summary` — counts for verified locations, status categories, disclosure coverage and data gaps.
- `GET /api/evidence/phoenix` — evidence summary, data coverage and limitations.

Do not return placeholder numeric values. Empty arrays and explicit availability statuses are preferable to fabricated results.

## 9. FRONTEND DESIGN DIRECTION

Create a distinctive, polished scientific interface.

- Brand: PIEZO.
- Visual language: geospatial observatory / Earth intelligence platform.
- Use a restrained dark or light scientific palette with strong contrast, clear typography and carefully used accent colors.
- Make the map and data visualizations the main focus.
- Use responsive layout for desktop first, but ensure usable tablet/mobile behavior.
- Include a persistent navigation structure and clear page titles.
- Avoid excessive cards, decorative gradients, generic AI-dashboard visuals and meaningless KPI numbers.
- Every chart needs a title, axis labels, units, legend and source/date context.
- Every map layer needs a legend and a clear description.
- Include loading, no-data, processing, error and partial-data states.
- Add tooltips or short explainers for scientific terms.
- Make it possible to distinguish measured, remotely sensed, modeled and reported information at a glance.

Suggested navigation:
- Overview
- Explore Map
- NISAR Radar
- Groundwater
- Water Context
- Facilities
- Evidence & Methods

## 10. TESTING AND VALIDATION

Implement tests at multiple levels.

### Data tests
- HDF5 opens and expected groups/datasets exist.
- Metadata parser extracts key fields.
- CRS and bounds are valid.
- Phoenix study area intersects the actual scene footprint.
- Derived rasters retain expected dimensions/CRS/nodata behavior.
- No unexpected all-nodata outputs.
- Units and scale factors are handled as specified.

### Backend tests
- API health works.
- Dataset/layer endpoints reflect actual catalog contents.
- Missing data returns explicit unavailable status, not fabricated records.
- Station time series preserve units and dates.

### Frontend tests
- Main pages render.
- Map loads and layers can be toggled.
- No-data states render correctly.
- Charts show labels/units/source.
- UI works at desktop and mobile widths.

### Scientific QA
- Manually inspect quick-look imagery.
- Verify map alignment against a trusted basemap/boundary.
- Verify any claimed trend against source observations.
- Have all scientific claims in the UI traceable to a method and source.

## 11. DEVELOPMENT WORKFLOW — BUILD IN PHASES

Do not attempt a giant one-shot implementation. Work in small, runnable milestones. At the end of each milestone, run tests/builds, report what works, and list remaining blockers.

**Phase 0 — Workspace and teammate-data audit**
- Inspect the complete repository and recursively inventory every file/folder, including all datasets added by teammates.
- Build a dataset inventory and metadata report for NISAR and every supplemental dataset; identify related sidecars, metadata, duplicates, archives, partial downloads and corrupt files.
- Validate each dataset's source, variables, units, spatial/temporal coverage, CRS/resolution, quality and relevance to Phoenix.
- Confirm NISAR coverage and map coverage of other spatial datasets.
- Create a teammate-data integration matrix: dataset, provider, what it measures, Phoenix coverage, time coverage, validation status, planned processing, target feature, blockers.
- Identify missing data and propose the minimum viable acquisition plan. Do not download large data without reporting the need and obtaining approval.

**Phase 1 — Foundation**
- Set up backend and frontend.
- Add environment examples, dependency files, README and run instructions.
- Create health and dataset-catalog endpoints.
- Create a clean responsive application shell.

**Phase 2 — NISAR data pipeline**
- Inspect selected HDF5.
- Extract valid channels.
- Create georeferenced analysis rasters and display COGs.
- Generate quick-look and processing manifest.
- Validate the Phoenix footprint.

**Phase 3 — Interactive NISAR map**
- Connect frontend map to processed raster layer(s).
- Add layer controls, legends, metadata panel and pixel inspection if feasible.
- Clearly communicate single-acquisition limitations.

**Phase 4 — Supplemental datasets and mandatory Data-Centre Observatory**
- Integrate every relevant, validated dataset found in the workspace, including datasets downloaded by teammates. Do not limit integration to the examples in this guide.
- Prioritize Phoenix groundwater monitoring, rainfall/climate, water-storage context and any other validated local datasets available.
- Add GRACE only with correct scale and caveats.
- Implement the dedicated Data-Centre Observatory as a required MVP feature: verified facility register, Phoenix map layer, searchable/filterable facility directory, facility detail/evidence panel, water-disclosure register and transparent unknown/data-gap states.
- Ingest teammate-provided data-centre lists, water-use spreadsheets, reports and regulatory documents. Cross-check records and attach source-level evidence; preserve conflicting or uncertain claims for review rather than silently choosing one.
- If site-specific water-use disclosures are sparse, the feature must still be complete as an evidence and transparency tool: show verified locations/status, what disclosures were found, their scope, and exactly what remains undisclosed. Do not invent estimates to make the page look populated.
- Add integration tests and data-quality checks for facility coordinates, duplicate records, status classifications, disclosure units, reporting periods and source traceability.

**Phase 5 — Analytics and evidence profile**
- Add reproducible charts and summaries.
- Separate observations, modeled indicators, reported disclosures and hypotheses.
- Add coverage and uncertainty notes.

**Phase 6 — Polish and delivery**
- Improve UI, accessibility and responsive behavior.
- Add tests, documentation, source citations and demo workflow.
- Ensure clean setup instructions and no secrets committed.
- Prepare a concise demo narrative explaining what the app does, what the data shows and what cannot be concluded.

## 12. TEAM / WORKING STYLE

- Do not assume fixed roles for specific team members. Work is collaborative and task-based.
- Keep tasks small and visible in a `docs/IMPLEMENTATION_CHECKLIST.md`.
- Maintain a shared dataset intake/integration tracker for every file contributed by any team member. Record who supplied it, original filename, source/provenance, validation status, target feature, processing status and integration decision. Do not create fixed member roles; keep work collaborative and task-based.
- Before large changes, explain the plan and files that will be affected.
- Do not overwrite source datasets or delete files.
- Do not commit raw multi-gigabyte satellite files to Git. Add appropriate patterns to `.gitignore`; keep a data manifest and instructions for obtaining the source files.
- Never commit Earthdata credentials, API keys, tokens or `.env` files.
- Keep code modular and understandable. Prefer clear functions, type hints, comments for scientific operations and reproducible scripts.
- Do not silently introduce paid services or external dependencies requiring accounts.
- If a design or scientific choice is uncertain, explain the options and recommend the most defensible MVP choice.

## 13. DEFINITION OF DONE FOR THE MVP

The first demonstrable MVP is complete when:

1. The application runs locally from documented commands.
2. The real Phoenix-area NISAR GCOV scene has been inspected and its coverage verified.
3. At least one valid radar channel has been processed from the actual HDF5 into a georeferenced display layer.
4. The frontend displays that layer on an interactive Phoenix map.
5. The UI shows the actual acquisition date, product information, polarization/channel, source and spatial resolution where verified.
6. A user can toggle the radar layer, inspect its legend and read its scientific limitations.
7. All relevant teammate-provided datasets have been inventoried, validated and either integrated into the appropriate feature or documented with a specific reason/blocker for exclusion.
8. The mandatory Data-Centre Observatory is implemented with a dedicated page/section, Phoenix facility map layer, searchable/filterable facility directory, facility detail/evidence panel and sourced water-disclosure records.
9. Facility status, location and water figures are traceable to source documents; undisclosed or unknown values are shown honestly and are not replaced with estimates.
10. Missing supplemental datasets are clearly identified rather than simulated.
11. Data provenance and processing steps are documented.
12. Tests/QA confirm that outputs are spatially valid and not all-nodata or incorrectly georeferenced, and that facility records/disclosures pass validation.
13. The app does not claim to measure groundwater directly or attribute groundwater depletion to a facility without evidence.

## 14. YOUR FIRST RESPONSE AFTER RECEIVING THIS PROMPT

Do not immediately start generating the entire application.

First provide:
1. A concise summary of the repository structure you found.
2. A table of all data files found, with file size, type, likely purpose and validation status.
3. A detailed report on the NISAR HDF5 and metadata, including actual internal datasets, CRS, footprint, acquisition time, available channels and whether Phoenix is covered.
4. A list of missing datasets and the minimum supplemental data needed for a credible MVP.
5. A proposed implementation plan with the first concrete coding milestone.

Then begin Phase 0 and Phase 1. Do not ask questions whose answers can be established by inspecting the files. Ask only when a genuinely necessary decision or credential is missing.

**The priority is a working, scientifically defensible application using the real data in this folder—not a visually impressive mock-up with invented numbers.**

---

# PART B — HOW TO USE THIS WITH CODEX

1. Put this file in the root of the project folder, or keep it available to Codex as context.
2. Open the **entire Project PIEZO folder** in Codex, not just the frontend folder. Codex needs access to the data directory and the source files.
3. Make sure the NISAR `.h5` and its metadata XML are inside the workspace, ideally under `data/raw/`. If they are elsewhere, tell Codex their exact location.
4. Paste the complete **Part A — Master Prompt** into Codex.
5. Let Codex perform the workspace audit first. Review its report before asking it to proceed with large downloads or long-running processing.
6. Ask Codex to complete one phase at a time and run the application after each phase.
7. Keep original NISAR downloads untouched. Store derived products separately.

## Suggested follow-up instruction after the audit

Once Codex has completed the audit and confirmed the NISAR product structure, use this instruction:

> Proceed with Phase 1 and Phase 2 only. Implement the application foundation and a reproducible NISAR GCOV processing pipeline based on the actual HDF5 hierarchy and metadata you inspected. Do not guess dataset paths, units, scaling, georeferencing or polarization meanings. Generate one validated georeferenced display product for the Phoenix study area, include a quick-look image and processing manifest, and write tests for the output. Do not start supplemental-data integration until this works.

## Important practical notes

- A 7.24 GB HDF5 file may require substantial disk space and processing time. Ensure there is enough free storage for intermediate files and derived COGs.
- Codex should not try to read the entire HDF5 into RAM. It should inspect metadata and read only the required datasets/windows where possible.
- Keep large raw files out of GitHub. Commit code, documentation, small sample data and manifests only, subject to data-use terms.
- If the project is being developed on Windows, Codex should check the installed Python version and geospatial dependencies. GDAL/Rasterio installation can require care; use a virtual environment and document exact setup commands.
- A single GCOV acquisition supports a meaningful radar-observation viewer, but a defensible temporal change analysis requires at least one additional compatible acquisition. Do not manufacture a before/after comparison.

---

# PART C — PROJECT SCIENCE REFERENCE

The NASA challenge describes SAR as active microwave remote sensing that can operate day or night and through cloud cover. It notes that radar observations are sensitive to surface roughness and dielectric properties, and can provide information relevant to water bodies, inundation, soil moisture, vegetation/structure and surface movement. The challenge asks participants to use NISAR to track and visualize one or more surface-change processes and encourages multi-date, multi-polarization analysis and contextual datasets.

For PIEZO, this translates into a careful division of evidence:

| Evidence type | What it can support | What it cannot establish by itself |
|---|---|---|
| NISAR L2 GCOV | Geocoded polarimetric radar surface observations; channel-specific backscatter/covariance analysis after product inspection | Deep groundwater level, aquifer volume, or facility-caused depletion |
| NISAR GUNW / valid InSAR workflow | Potential surface displacement when valid pairs, coherence, corrections and validation support it | The cause of deformation without independent evidence |
| USGS / ADWR wells | Local groundwater observations at monitoring stations, with measurement type and units respected | Continuous groundwater conditions everywhere between wells |
| GRACE / GRACE-FO | Broad-scale total water storage variations; groundwater residual only with supporting component data and uncertainty | Facility/neighbourhood-scale groundwater measurement |
| Rainfall | Precipitation context and temporal anomalies | Actual aquifer recharge or groundwater recovery on its own |
| Facility disclosures | Reported water withdrawal/consumption and stated water sources for the reporting period | Unreported usage or causal impact on a nearby well |

The application's central value is to bring these different evidence streams together while preserving their distinct scales, meanings and limitations.
