# Known limitations

- Two NISAR GCOV frames are from one descending pass on 2026-10-28. They support a single-date radar explorer and additional footprint coverage, not temporal change detection. A second compatible date is required.
- GCOV observes geocoded radar covariance/surface response. It does not directly measure groundwater, aquifer volume, or displacement.
- No complete public data-centre inventory or site-specific withdrawal/consumption quantity has been verified. The directory contains six primary-source records (one proposed site, five with unknown current operating status); only one has source-published coordinates. It does not estimate missing usage.
- USGS and ADWR records are filtered to a documented Phoenix rectangle. ADWR source/method/remark codes are not decoded; its water-level elevation table does not state a vertical datum. Source query provenance for the supplied USGS export is incomplete.
- PRISM provides one October 2026 monthly grid; it does not provide a matched time series on its own. The reported 55.63 mm is an unweighted arithmetic mean of 18,511 valid native cells whose centers fall within the Phoenix rectangle, not an area-weighted precipitation total.
- GRACE/GRACE-FO is total water storage anomaly at native 3-degree mascon scale. It cannot support facility/neighborhood groundwater inference. A groundwater residual would need other water storage components and uncertainty.
- ADWR basin supply/demand PDFs are not all Phoenix-relevant; Phoenix AMA, Salt River and neighboring basin/subbasin boundaries are shown as regional context. The Salt River supply/demand PDF has not yet been extracted into cited numeric evidence; no PDF values are charted.
- The local Python environment has Rasterio, NetCDF4, h5py, pyproj, pyshp and Shapely. GeoPandas and GDAL command-line utilities are not required for the implemented scripts.
- The Arizona tracker and older team context conflict with the implementation guide on geography. The guide is authoritative and sets Phoenix, Arizona. The older India-facing plans are not applied.
- The current application reads counts/status from local catalogs and processing outputs; the source datasets remain the authority for scientific claims.

- NISAR frame 72 metadata and footprint are verified but map-ready channel crops have not been generated. Frame 71 Frequency B is also not processed; current interactive radar display covers frame 71 Frequency A HHHH and HVHV only.
- The frontend production build and local API tests can be validated in this environment; no Cloudflare Pages or Render production URL has been supplied or deployed, so remote URL behavior remains a release check.
- The Salt River Basin supply/demand report has not been extracted into cited numeric evidence.
- The npm install advisory summary reported one critical dependency issue. The package registry audit endpoint was unreachable from this environment, so the affected package and remediation remain unverified.
