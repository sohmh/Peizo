# Scientific method and validation

## Evidence classes

- **Remote sensing observation:** NISAR L2 GCOV covariance terms describe geocoded radar surface response. Backscatter depends on dielectric properties, roughness, vegetation, geometry and acquisition conditions. It is not a direct sensor of groundwater, aquifer storage or subsidence.
- **Ground observation:** USGS and ADWR well records are local measurements. Keep provider, site ID, date, parameter, unit, measurement type, method, qualifiers and vertical datum context. ADWR source/method/remark codes are retained without decoding; its elevation series has no stated datum in the joined table. Depth below land surface and water-level elevation must not be mixed.
- **Modeled context:** PRISM precipitation is gridded modeled precipitation. It supplies climate context, not proof of aquifer recharge.
- **Regional storage estimate:** JPL GRACE/GRACE-FO is total water storage anomaly at coarse mascon scale. It is not a facility-scale or groundwater-only measurement.
- **Reported facility evidence:** Facility location/status and water disclosure each require their own source. Keep disclosure scope (site, region, company), planned/actual, withdrawal/consumption, source type, period, original unit and page/section evidence distinct.

## NISAR workflow

1. Inspect HDF5 identification, frequency groups, dimensions, coordinate vectors, projection, covariance attributes, masks and XML metadata.
2. Read only required arrays/windows. Use the source coordinate vectors and EPSG 32612; do not guess georeferencing from filenames or quicklook images.
3. Preserve original values. Mask invalid pixels using product masks/fill rules. Any display stretch or logarithmic conversion must be an explicitly named derived view with formula and input units.
4. Write a source-CRS quantitative raster and separately generate any web display derivative. Record source granule, checksum if feasible, channel, units, bounds, spacing, valid-pixel counts, parameters and warnings in a manifest.
5. Verify output bounds/dimensions/CRS against HDF5, check nonempty valid pixels, and confirm spatial intersection with Phoenix. Inspect quicklook for orientation and alignment.

The two available frames are frame 71 and 72 on 2026-10-28, descending track 56, with acquisition intervals 02:15:35–02:16:10.999 UTC and 02:16:09–02:16:44.999 UTC. They are adjacent/overlapping scene coverage from one pass, not independent temporal acquisitions. No temporal change layer is scientifically justified from this pair.

## Groundwater and climate

Filter actual site coordinates to the project geography. Retain official site identifiers and source fields. Filter on parameter and measurement type before plotting. A larger depth-to-water generally indicates the water table is farther below land surface; elevations are interpreted against their named vertical datum. Show data gaps and station locations; do not interpolate continuous surfaces unless a documented method and uncertainty assessment are implemented.

Rainfall is shown at source resolution and time coverage. Rainfall by itself does not establish recharge. GRACE shows total storage anomaly at its native support; no city/facility downscaling or groundwater residual is justified without independent soil-moisture/surface-water/other component data and uncertainty.

## Facilities and causal limits

Treat every campus location, operating status, water source and quantity as separate claims with source and evidence quality. Discovery directories can identify candidates only. Never allocate company-wide water totals to Phoenix campuses, infer groundwater use from nearby wells, or infer water demand from campus size/cooling. A spatial or temporal overlap with a radar/well pattern is a hypothesis for further investigation, not causation.

## Validation plan

- Confirm product identity, HDF5 hierarchy, CRS, coordinates, footprints and valid masks from both HDF5 and XML.
- Validate raster geometry, source/display values, unit metadata, valid counts, quicklook and Phoenix intersection.
- Validate well coordinates, units, parameters, datums, site IDs and date range; report distinct measurement types separately.
- Validate raster/vector CRS and geometry; retain native grid/resolution in metadata.
- For facility records, check coordinate plausibility, status evidence, duplicate campuses, disclosure scope, unit/period/definition and source reference.
- Review every displayed statistic against a reproducible query and source record. Missing evidence is displayed as unavailable or not assessed.
