"""Crop the supplied monthly PRISM grid to Phoenix without changing source resolution or values."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from pyproj import Transformer
from rasterio.windows import Window, from_bounds
from rasterio.shutil import copy as rio_copy

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Datasets" / "a08.prism_ppt" / "prism_ppt_us_30s_202610.tif"
BOUNDS = (-112.80, 33.20, -111.35, 34.10)


def main() -> None:
    outdir = ROOT / "data" / "processed" / "prism"
    outdir.mkdir(parents=True, exist_ok=True)
    analysis_path = outdir / "prism_oct2026_phoenix.tif"
    cog_path = outdir / "prism_oct2026_phoenix_cog.tif"
    image_path = outdir / "prism_oct2026_quicklook.png"
    manifest_path = ROOT / "data" / "manifests" / "prism_oct2026_phoenix.json"
    with rasterio.open(SOURCE) as src:
        source_crs = src.crs
        transformed = Transformer.from_crs("EPSG:4326", source_crs, always_xy=True)
        projected_bounds = [transformed.transform(BOUNDS[i], BOUNDS[j]) for i, j in [(0, 1), (0, 3), (2, 1), (2, 3)]]
        xmin, xmax = min(x for x, y in projected_bounds), max(x for x, y in projected_bounds)
        ymin, ymax = min(y for x, y in projected_bounds), max(y for x, y in projected_bounds)
        win = from_bounds(xmin, ymin, xmax, ymax, src.transform).round_offsets().round_lengths()
        win = win.intersection(Window(0, 0, src.width, src.height))
        values = src.read(1, window=win).astype("float32", copy=False)
        transform = src.window_transform(win)
        rows, cols = np.indices(values.shape)
        lon, lat = rasterio.transform.xy(transform, rows, cols, offset="center")
        study_mask = ((np.asarray(lon) >= BOUNDS[0]) & (np.asarray(lon) <= BOUNDS[2]) & (np.asarray(lat) >= BOUNDS[1]) & (np.asarray(lat) <= BOUNDS[3])).reshape(values.shape)
        valid = np.isfinite(values) & (values != src.nodata) & study_mask
        if not valid.any():
            raise RuntimeError("PRISM Phoenix crop has no valid grid cells")
        display_values = values.copy()
        display_values[~study_mask] = src.nodata if src.nodata is not None else np.nan
        profile = src.profile.copy()
        profile.update(width=int(win.width), height=int(win.height), transform=transform, compress="DEFLATE", tiled=True, blockxsize=256, blockysize=256, predictor=3)
        with rasterio.open(analysis_path, "w", **profile) as dst:
            dst.write(display_values, 1)
            dst.update_tags(1, units="mm", variable="monthly precipitation", reporting_period="2026-10")
            dst.update_tags(AREA_OR_POINT="Area", source_filename=SOURCE.name)
            dst.build_overviews([2, 4, 8], rasterio.enums.Resampling.average)
        rio_copy(analysis_path, cog_path, driver="COG", compress="DEFLATE", overview_resampling="AVERAGE")
        lo, hi = np.percentile(values[valid], [2, 98]).astype(float)
        if hi <= lo:
            hi = lo + 1
        scaled = np.zeros(values.shape, dtype=np.uint8)
        scaled[valid] = np.clip((values[valid] - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
        rgba = np.zeros((*values.shape, 4), dtype=np.uint8)
        intensity = scaled.astype(np.int16)
        rgba[..., 0] = intensity.astype(np.uint8) // 4
        rgba[..., 1] = np.clip(75 + intensity * 2 // 3, 0, 255).astype(np.uint8)
        rgba[..., 2] = np.clip(95 + intensity * 2 // 3, 0, 255).astype(np.uint8)
        rgba[..., 3] = valid.astype(np.uint8) * 255
        Image.fromarray(rgba, mode="RGBA").save(image_path, optimize=True)
        bounds = rasterio.transform.array_bounds(int(win.height), int(win.width), transform)
        to_wgs84 = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
        left, bottom, right, top = bounds
        corners = [to_wgs84.transform(left, top), to_wgs84.transform(right, top), to_wgs84.transform(right, bottom), to_wgs84.transform(left, bottom)]
        source_info = {}
        info_path = SOURCE.with_suffix(".info.txt")
        if info_path.exists():
            for line in info_path.read_text(encoding="utf-8").splitlines():
                if ":" in line:
                    key, value = line.split(":", 1)
                    source_info[key.strip()] = value.strip()
        manifest = {
            "source_file": SOURCE.relative_to(ROOT).as_posix(), "source_provider": "PRISM Climate Group, Oregon State University",
            "source_grid": "prism_ppt_us_30s_202610", "variable": "monthly precipitation", "period": "2026-10",
            "dataset_version": source_info.get("PRISM_DATASET_VERSION"), "release_number": int(source_info["PRISM_DATASET_RELEASE_NUMBER"]) if source_info.get("PRISM_DATASET_RELEASE_NUMBER", "").isdigit() else None,
            "dataset_create_date": source_info.get("PRISM_DATASET_CREATE_DATE"), "source_create_date": source_info.get("PRISM_SOURCE_CREATE_DATE"),
            "units": "mm", "source_crs": source_crs.to_string(), "source_resolution_degrees": [src.transform.a, src.transform.e],
            "source_bounds": list(src.bounds), "source_nodata": src.nodata, "study_rectangle_wgs84": list(BOUNDS),
            "output_crs": source_crs.to_string(), "output_shape": list(values.shape), "output_bounds": list(bounds),
            "display_corners_lonlat_nw_ne_se_sw": [list(point) for point in corners],
            "valid_cell_count": int(valid.sum()), "valid_fraction": float(valid.mean()),
            "regional_mean_mm": float(values[valid].mean()), "regional_min_mm": float(values[valid].min()), "regional_max_mm": float(values[valid].max()),
            "display_stretch": {"type": "linear 2nd–98th percentile clip", "minimum": float(lo), "maximum": float(hi), "input_units": "mm"},
            "outputs": {"analysis_geotiff": analysis_path.name, "cog": cog_path.name, "quicklook_png": image_path.name},
            "method": "Crop source pixels to the documented Phoenix rectangle; include only native grid-cell centers inside the rectangle in the valid-cell mean; no resampling or interpolation of source values.",
            "vintage_note": "This PRISM monthly grid is a versioned release; monthly products are updated over the following six months before considered stable.",
            "regional_mean_method": "Arithmetic mean of valid native PRISM grid-cell totals whose centers fall within the study rectangle; cells are not area-weighted.",
            "limitations": ["One monthly period only; not a rainfall time series.", "Precipitation is context and does not prove aquifer recharge.", "PRISM is a modeled gridded estimate."],
            "created_utc": datetime.now(timezone.utc).isoformat(),
        }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({k: manifest[k] for k in ["output_shape", "source_crs", "units", "valid_cell_count", "regional_mean_mm", "regional_min_mm", "regional_max_mm"]}, indent=2))


if __name__ == "__main__":
    main()
