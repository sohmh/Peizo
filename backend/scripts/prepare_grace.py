"""Extract one monthly JPL GRACE mascon series at Phoenix's containing cell."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import netCDF4
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Datasets" / "A09. JPL GRACE.GRACE-FO.nc"


def main() -> None:
    out = ROOT / "data" / "processed" / "grace" / "phoenix_mascon_series.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    with netCDF4.Dataset(SOURCE) as ds:
        lat = np.asarray(ds.variables["lat"][:])
        lon = np.asarray(ds.variables["lon"][:])
        # GRACE longitudes are 0–360 degrees east; preserve the native monthly mascon support.
        target_lon = 360.0 - 112.074
        iy, ix = int(np.abs(lat - 33.448).argmin()), int(np.abs(lon - target_lon).argmin())
        mascon = int(ds.variables["mascon_ID"][iy, ix])
        times = netCDF4.num2date(ds.variables["time"][:], ds.variables["time"].units, only_use_cftime_datetimes=False, only_use_python_datetimes=True)
        values = np.asarray(ds.variables["lwe_thickness"][:, iy, ix])
        errors = np.asarray(ds.variables["uncertainty"][:, iy, ix])
        fill = ds.variables["lwe_thickness"]._FillValue
        series = []
        for date, value, uncertainty in zip(times, values, errors):
            if not np.isfinite(value) or value == fill:
                continue
            series.append({"date": date.strftime("%Y-%m-%d"), "value": float(value), "uncertainty": None if not np.isfinite(uncertainty) or uncertainty == ds.variables["uncertainty"]._FillValue else float(uncertainty), "unit": "cm"})
        report = {
            "source_file": str(SOURCE.resolve()), "provider": "NASA/JPL PO.DAAC", "product": "JPL GRACE/GRACE-FO MASCON RL06.3Mv04 CRI",
            "doi": getattr(ds, "id"), "variable": "lwe_thickness", "interpretation": "total terrestrial water storage anomaly",
            "native_support": "3-degree equal-area mascon; 0.5-degree grid is a display grid",
            "selected_mascon_id": mascon, "selected_grid_cell_center": {"latitude": float(lat[iy]), "longitude_360": float(lon[ix]), "longitude_west": float(lon[ix] - 360)},
            "record_count": len(series), "series": series,
            "method": "Use the source grid cell containing central Phoenix and preserve its associated mascon ID and uncertainty. This represents broad regional storage, not city- or facility-scale water.",
            "limitations": ["Total water storage, not groundwater-only storage.", "Native spatial support is approximately 3 degrees.", "Missing monthly values are omitted and not interpolated."],
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
    out.write_text(json.dumps(report, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["doi", "selected_mascon_id", "selected_grid_cell_center", "record_count", "native_support"]}, indent=2))


if __name__ == "__main__":
    main()
