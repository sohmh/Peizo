# PIEZO data dictionary

This dictionary records fields confirmed from source metadata or headers. Source files remain immutable; derived products belong under `data/processed/`.

## NISAR L2 GCOV

| Variable | HDF5 path | Shape / type | Units / CRS | Meaning and handling |
|---|---|---|---|---|
| `HHHH` | `/science/LSAR/GCOV/grids/frequency{A,B}/HHHH` | A: 34632×35136 float32; B: 4329×4392 float32 | `1`; EPSG:32612 | HH-HH covariance term; product description identifies the covariance term. Treat as linear covariance/backscatter-like radar quantity only after product specification review; NaN fill and validity mask must be honored. |
| `HVHV` | same, `/HVHV` | A/B same dimensions | `1`; EPSG:32612 | HV-HV covariance term. Same interpretation cautions as HHHH. |
| `mask` | frequency groups | uint8 raster | Fill 255 | Valid subswath mask; only fully focused valid GCOV samples are represented. |
| `inputDataExceptionMask` | frequency groups | uint16 raster | Fill 65535 | Bitwise input exception/validity flags; bit definitions are in dataset attributes. |
| `numberOfLooks` | frequency groups | float32 raster | dimensionless | Number of radar samples averaged for covariance estimation. |
| `rtcGammaToSigmaFactor` | frequency groups | float32 raster | dimensionless | Product metadata describes gamma0-to-sigma0 terrain normalization factor; do not apply without documented method. |
| `xCoordinates`, `yCoordinates` | frequency groups | 1D float64 centers | meters; EPSG:32612 | Exact projected pixel-center coordinates; A spacing +10 m x, −10 m y. |
| `projection` | frequency groups | scalar uint32 + attributes | EPSG:32612 | WGS84 / UTM zone 12N. |
| `boundingPolygon` | `/science/LSAR/identification/boundingPolygon` | WKT | EPSG:4326 | Product footprint, with lon/lat/ellipsoid-height coordinates. |
| product metadata | `/science/LSAR/identification/*` | scalar/short arrays | UTC, IDs | Granule, frame, track, orbit, time, version and product DOI. |

Both scenes include frequency groups A and B and covariance terms HHHH/HVHV. Their frequency-A raster spacing is 10 m; frequency B is a separate coarser grid (about 80 m from vector spacing and dimensions, to be recorded exactly in pipeline metadata). HDF5 coordinate vectors are center coordinates; a raster geotransform must shift to pixel edges correctly.

## Groundwater and wells

| Source fields | Definition | Notes |
|---|---|---|
| USGS export: `monitoring_location_id`, `parameter_code`, `parameter_description`, `reading_type`, `time`, `value`, `unit_of_measure`, `vertical_datum`, `x`, `y` | Station, measured parameter, reading type, observation date/value, units/datum, longitude/latitude | `x`/`y` are lon/lat in observed samples. Preserve ID and qualifiers. Do not combine depth-to-water with water-level elevation; elevations on NAVD88 and NGVD29 are separate datum series. |
| ADWR GWSI: shapefile `SITE_ID`, `DD_LAT`, `DD_LONG`, `WELL_TYPE`, `WATER_USE`, `LASTWLDATE`, `WL_DTW`, `WL_ELEV`; `GWSI_WW_LEVELS.xlsx`: `WLWA_SITE_WELL_SITE_ID`, `WLWA_MEASUREMENT_DATE`, `WLWA_DEPTH_TO_WATER`, `WLWA_WATER_LEVEL_ELEVATION`, source/method/remark codes | Site inventory and discrete water-well measurement table | Source site points use published DD_LAT/DD_LONG attributes and are filtered to the documented Phoenix rectangle. Keep depth and elevation, method, source, date, location accuracy and temporal sampling distinct. The 6,765-site display derivative is joined to 48,846 historical table rows; 46,360 have at least one level value across 5,152 sites, while 2,486 rows have neither depth nor elevation. The app plots one parameter definition at a time. Elevation datum remains unspecified in the table; source/method/remark codes remain undecoded. |

## GRACE / GRACE-FO

| Variable | Shape | Units | Notes |
|---|---|---|---|
| `lwe_thickness` | 261×360×720 | cm | JPL RL06.3Mv04 CRI liquid-water-equivalent total water storage anomaly. 0.5° grid is a display grid; native mascon resolution is 3° equal-area. |
| `uncertainty` | same | cm | Per-cell uncertainty; preserve alongside values. |
| `time` | 261 | days since 2002-01-01 UTC | Monthly records; gaps are listed in global metadata. |
| `lat`, `lon` | 360, 720 | degrees north/east | Longitudes 0–360; convert only in display derivative. |

Do not present total water storage as groundwater-only storage or downscale to a facility/neighborhood.

## PRISM precipitation

Raster `prism_ppt_us_30s_202610.tif`; monthly total precipitation grid for October 2026, PRISM dataset type an91/r2112, version M3 release 1, 30 arc-second (~800 m), geographic NAD83 (EPSG:4269). TIFF tags give 0.008333-degree pixel size, CONUS bounds, Float32 values and nodata −9999. PRISM precipitation is in millimeters. The 108×174 crop masks cells whose centers fall outside the Phoenix rectangle, leaving 18,511 valid cells. Their unweighted arithmetic mean is 55.63 mm for the month; this is a regional grid-cell mean, not a monthly total over the study area or an area-weighted statistic. This Oct 2026 product is an early release subject to PRISM's monthly revisions over the following six months.

## Vector layers

Arizona basin/subbasin GeoJSON uses CRS84 coordinates (longitude, latitude). State boundary GeoJSON declares EPSG:4326. County layer schema and CRS need confirmation. Preserve source feature IDs and names; validate geometries before map serving.

## Facility register

No teammate-supplied facility records existed. The public-source evidence register contains six records, one published coordinate point, and no verified site-specific withdrawal/consumption quantity. Do not encode missing values as zero. The target schema and evidence rules are documented in [FACILITY_EVIDENCE_REGISTER.md](FACILITY_EVIDENCE_REGISTER.md).
