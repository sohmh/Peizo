"""Create a Phoenix-only quantitative GeoTIFF and a stretched quicklook from NISAR GCOV.

The input arrays and coordinate vectors are read from product metadata; no geotransform
or variable meaning is inferred from filename conventions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np
import rasterio
from rasterio.features import geometry_mask
from PIL import Image
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.windows import Window
from rasterio.shutil import copy as rio_copy
from shapely.geometry import Polygon, mapping

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "Datasets" / "NISAR_L2_PR_GCOV_034_056_D_071_4005_DHDH_A_20261028T021535_20261028T021610_P05036_N_F_J_001.h5"
PHOENIX_BOUNDS = (-112.80, 33.20, -111.35, 34.10)  # metropolitan study rectangle, WGS84 lon/lat


def decode(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--frequency", default="frequencyA")
    parser.add_argument("--channel", default="HHHH")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "nisar")
    parser.add_argument("--skip-checksum", action="store_true", help="Skip a full-file SHA-256 pass for faster local iteration")
    args = parser.parse_args()
    source = args.input.resolve()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    with h5py.File(source, "r") as product:
        id_group = product["science/LSAR/identification"]
        grid = product[f"science/LSAR/GCOV/grids/{args.frequency}"]
        channel = grid[args.channel]
        x = grid["xCoordinates"][:]
        y = grid["yCoordinates"][:]
        projection = int(grid["projection"].attrs["epsg_code"])
        dx = float(grid["xCoordinateSpacing"][()])
        dy = float(grid["yCoordinateSpacing"][()])
        units = decode(channel.attrs.get("units", "unknown"))
        description = decode(channel.attrs.get("description", ""))
        fill = channel.attrs.get("_FillValue", np.nan)

        to_source = Transformer.from_crs("EPSG:4326", f"EPSG:{projection}", always_xy=True)
        west, south, east, north = PHOENIX_BOUNDS
        corners = [to_source.transform(lon, lat) for lon, lat in [(west, south), (west, north), (east, south), (east, north)]]
        xmin, xmax = min(p[0] for p in corners), max(p[0] for p in corners)
        ymin, ymax = min(p[1] for p in corners), max(p[1] for p in corners)
        col0 = max(0, int(np.searchsorted(x, xmin - abs(dx) / 2, side="left")))
        col1 = min(len(x), int(np.searchsorted(x, xmax + abs(dx) / 2, side="right")))
        asc_y = y[0] < y[-1]
        if asc_y:
            row0 = max(0, int(np.searchsorted(y, ymin - abs(dy) / 2, side="left")))
            row1 = min(len(y), int(np.searchsorted(y, ymax + abs(dy) / 2, side="right")))
        else:
            y_reversed = y[::-1]
            rev0 = max(0, int(np.searchsorted(y_reversed, ymin - abs(dy) / 2, side="left")))
            rev1 = min(len(y), int(np.searchsorted(y_reversed, ymax + abs(dy) / 2, side="right")))
            row0, row1 = len(y) - rev1, len(y) - rev0
        if row1 <= row0 or col1 <= col0:
            raise RuntimeError("Phoenix study bounds do not intersect the selected HDF5 grid")

        window = Window(col0, row0, col1 - col0, row1 - row0)
        raw = channel[row0:row1, col0:col1].astype("float32", copy=False)
        mask = grid["mask"][row0:row1, col0:col1]
        valid = np.isfinite(raw) & (mask > 0) & (mask != 255)
        if isinstance(fill, (float, np.floating)) and np.isnan(fill):
            valid &= np.isfinite(raw)
        elif np.isfinite(fill):
            valid &= raw != fill
        transform = from_origin(float(x[col0] - abs(dx) / 2), float(y[row0] + abs(dy) / 2), abs(dx), abs(dy))
        # Densify the geographic study rectangle before projection, then mask by
        # pixel-center inclusion so the projected bounding box does not leak data
        # from outside the Phoenix lon/lat rectangle at its edges.
        edge = np.linspace(0.0, 1.0, 101)
        lonlat_boundary = ([(west + t * (east - west), south) for t in edge]
            + [(east, south + t * (north - south)) for t in edge[1:]]
            + [(east - t * (east - west), north) for t in edge[1:]]
            + [(west, north - t * (north - south)) for t in edge[1:-1]])
        boundary_x, boundary_y = to_source.transform([p[0] for p in lonlat_boundary], [p[1] for p in lonlat_boundary])
        study_polygon = Polygon(zip(boundary_x, boundary_y))
        inside_study = geometry_mask([mapping(study_polygon)], out_shape=raw.shape, transform=transform, invert=True, all_touched=False)
        valid &= inside_study
        if not valid.any():
            raise RuntimeError("Phoenix crop contains no valid fully-focused GCOV samples inside the study rectangle")

        output_data = np.where(valid, raw, np.nan).astype("float32", copy=False)
        stem = f"frame{int(id_group['frameNumber'][()]):02d}_{args.channel.lower()}"
        analysis_path = output / f"{stem}_phoenix.tif"
        cog_path = output / f"{stem}_phoenix_cog.tif"
        quicklook_path = output / f"{stem}_quicklook.png"
        meta_path = output / f"{stem}_manifest.json"
        profile = {
            "driver": "GTiff", "width": int(window.width), "height": int(window.height), "count": 1,
            "dtype": "float32", "crs": f"EPSG:{projection}", "transform": transform,
            "nodata": np.nan, "compress": "DEFLATE", "predictor": 3, "tiled": True,
            "blockxsize": 512, "blockysize": 512,
        }
        with rasterio.open(analysis_path, "w", **profile) as dst:
            dst.write(output_data, 1)
            dst.set_band_description(1, description)
            dst.update_tags(1, units=units, source_channel=args.channel, source_frequency=args.frequency)
            dst.update_tags(AREA_OR_POINT="Area", source_granule=decode(id_group["granuleId"][()]))
            dst.build_overviews([2, 4, 8, 16], rasterio.enums.Resampling.average)
        rio_copy(analysis_path, cog_path, driver="COG", compress="DEFLATE", overview_resampling="AVERAGE")

        lo, hi = np.percentile(raw[valid], [2, 98]).astype(float)
        if hi <= lo:
            hi = lo + 1
        stretched = np.zeros(raw.shape, dtype=np.uint8)
        stretched[valid] = np.clip((raw[valid] - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)
        # Transparent invalid pixels keep the map basemap visible outside the radar swath.
        rgba = np.zeros((*raw.shape, 4), dtype=np.uint8)
        rgba[..., :3] = stretched[..., None]
        rgba[..., 3] = valid.astype(np.uint8) * 255
        quicklook = Image.fromarray(rgba, mode="RGBA")
        quicklook.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
        quicklook.save(quicklook_path, optimize=True)

        to_wgs84 = Transformer.from_crs(f"EPSG:{projection}", "EPSG:4326", always_xy=True)
        west_m = float(x[col0] - abs(dx) / 2)
        east_m = float(x[col1 - 1] + abs(dx) / 2)
        north_m = float(y[row0] + abs(dy) / 2)
        south_m = float(y[row1 - 1] - abs(dy) / 2)
        image_corners = [to_wgs84.transform(west_m, north_m), to_wgs84.transform(east_m, north_m), to_wgs84.transform(east_m, south_m), to_wgs84.transform(west_m, south_m)]
        bounds = [west_m, south_m, east_m, north_m]
        valid_count = int(valid.sum())
        manifest = {
            "source_file": source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.name, "source_granule": decode(id_group["granuleId"][()]),
            "source_sha256": None if args.skip_checksum else sha256(source),
            "product_version": decode(id_group["productVersion"][()]), "crid": decode(id_group["compositeReleaseId"][()]),
            "acquisition_start_utc": decode(id_group["zeroDopplerStartTime"][()]),
            "acquisition_end_utc": decode(id_group["zeroDopplerEndTime"][()]),
            "orbit_direction": decode(id_group["orbitPassDirection"][()]), "track": int(id_group["trackNumber"][()]),
            "frame": int(id_group["frameNumber"][()]), "channel": args.channel, "frequency": args.frequency,
            "channel_description": description, "units": units, "source_crs": f"EPSG:{projection}",
            "source_shape": list(channel.shape), "source_pixel_spacing_m": [dx, dy],
            "source_window": {"row_start": row0, "row_end_exclusive": row1, "col_start": col0, "col_end_exclusive": col1},
            "output_shape": list(raw.shape), "output_bounds_source_crs": bounds,
            "quicklook_shape": [quicklook.height, quicklook.width],
            "display_corners_lonlat_nw_ne_se_sw": [list(p) for p in image_corners],
            "valid_pixel_count": valid_count, "valid_fraction": valid_count / raw.size,
            "valid_range": [float(raw[valid].min()), float(raw[valid].max())],
            "display_stretch": {"type": "linear percent clip", "percentiles": [2, 98], "minimum": lo, "maximum": hi, "input_units": units},
            "mask_rule": "finite channel value, GCOV mask > 0 and != 255, and pixel center inside the projected/densified Phoenix study rectangle",
            "outputs": {"analysis_geotiff": analysis_path.name, "cog": cog_path.name, "quicklook_png": quicklook_path.name},
            "created_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
            "warnings": ["Display quicklook is stretched and not quantitative.", "Single acquisition date; this output does not support temporal change detection.", "GCOV is not a direct groundwater measurement."],
        }
        meta_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
