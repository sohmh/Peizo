"""Read product metadata only and write a concise source inventory for each NISAR GCOV file."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
from shapely import box, wkt

ROOT = Path(__file__).resolve().parents[2]
PHOENIX = box(-112.80, 33.20, -111.35, 34.10)


def decode(value: object) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def inspect(path: Path) -> dict[str, object]:
    with h5py.File(path, "r") as product:
        ident = product["science/LSAR/identification"]
        result: dict[str, object] = {
            "source_file": str(path.resolve()),
            "source_size_bytes": path.stat().st_size,
            "granule_id": decode(ident["granuleId"][()]),
            "product_type": decode(ident["productType"][()]),
            "product_level": decode(ident["productLevel"][()]),
            "product_version": decode(ident["productVersion"][()]),
            "product_specification_version": decode(ident["productSpecificationVersion"][()]),
            "crid": decode(ident["compositeReleaseId"][()]),
            "doi": decode(ident["productDoi"][()]),
            "acquisition_start_utc": decode(ident["zeroDopplerStartTime"][()]),
            "acquisition_end_utc": decode(ident["zeroDopplerEndTime"][()]),
            "orbit_direction": decode(ident["orbitPassDirection"][()]),
            "track": int(ident["trackNumber"][()]),
            "frame": int(ident["frameNumber"][()]),
            "is_geocoded": decode(ident["isGeocoded"][()]) == "True",
            "projection_wkt": decode(product["science/LSAR/GCOV/grids/frequencyA/projection"].attrs["spatial_ref"]),
            "footprint_wkt": decode(ident["boundingPolygon"][()]),
            "phoenix_study_rectangle_intersects": bool(wkt.loads(decode(ident["boundingPolygon"][()])).intersects(PHOENIX)),
            "frequency_grids": {},
            "metadata_only_inspection": True,
            "inspected_utc": datetime.now(timezone.utc).isoformat(),
        }
        frequencies: dict[str, object] = {}
        for frequency in ("frequencyA", "frequencyB"):
            grid = product[f"science/LSAR/GCOV/grids/{frequency}"]
            dx = float(grid["xCoordinateSpacing"][()])
            dy = float(grid["yCoordinateSpacing"][()])
            terms = []
            for term in grid["listOfCovarianceTerms"][:]:
                name = decode(term)
                dataset = grid[name]
                terms.append({"term": name, "shape": list(dataset.shape), "dtype": str(dataset.dtype), "units": decode(dataset.attrs.get("units", "unknown")), "description": decode(dataset.attrs.get("description", "")), "fill_value": "NaN" if str(dataset.attrs.get("_FillValue", "")).lower() == "nan" else str(dataset.attrs.get("_FillValue")), "valid_min": float(dataset.attrs.get("valid_min", 0.0))})
            frequencies[frequency] = {
                "crs": f"EPSG:{int(grid['projection'].attrs['epsg_code'])}",
                "shape": list(grid["mask"].shape),
                "x_coordinate_extent_m": [float(grid["xCoordinates"][0]), float(grid["xCoordinates"][-1])],
                "y_coordinate_extent_m": [float(grid["yCoordinates"][0]), float(grid["yCoordinates"][-1])],
                "pixel_spacing_m": [dx, dy],
                "covariance_terms": terms,
                "has_mask": "mask" in grid,
                "has_input_data_exception_mask": "inputDataExceptionMask" in grid,
            }
        result["frequency_grids"] = frequencies
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "manifests")
    args = parser.parse_args()
    paths = args.input or sorted((ROOT / "Datasets").glob("NISAR_L2_PR_GCOV_034_056_D_0*.h5"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        report = inspect(path)
        output = args.output_dir / f"{report['granule_id']}_inspection.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Wrote {output}")


if __name__ == "__main__":
    main()
