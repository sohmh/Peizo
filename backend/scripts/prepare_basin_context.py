from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import box, mapping, shape

ROOT = Path(__file__).resolve().parents[2]
DATASETS = ROOT / "Datasets"
BOUNDS = (-112.80, 33.20, -111.35, 34.10)
SOURCES = [("basin", DATASETS / "Groundwater_Basin.geojson", "BASIN_NAME"), ("subbasin", DATASETS / "ADWR_Groundwater_Subbasin.geojson", "SUBBASIN_NAME")]


def main() -> None:
    rectangle = box(*BOUNDS)
    features = []
    counts = {}
    for level, path, name_key in SOURCES:
        source = json.loads(path.read_text(encoding="utf-8"))
        count = 0
        for feature in source.get("features", []):
            if not feature.get("geometry"):
                continue
            geometry = shape(feature["geometry"])
            if not geometry.is_valid:
                geometry = geometry.buffer(0)
            clipped = geometry.intersection(rectangle)
            if clipped.is_empty or clipped.area == 0:
                continue
            props = {**feature.get("properties", {}), "boundary_type": level, "boundary_name": feature.get("properties", {}).get(name_key)}
            features.append({"type": "Feature", "geometry": mapping(clipped), "properties": props})
            count += 1
        counts[level] = count
    output = ROOT / "data" / "processed" / "context" / "phoenix_basin_boundaries.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"type": "FeatureCollection", "features": features, "metadata": {"provider": "Arizona Department of Water Resources", "source_files": [str(path.relative_to(ROOT)) for _, path, _ in SOURCES], "source_crs": "CRS84", "display_crs": "WGS84 longitude/latitude", "study_rectangle_wgs84": list(BOUNDS), "feature_counts": counts, "note": "Source basin/subbasin polygons clipped to the documented Phoenix study rectangle for display; boundary geometry is regional context, not a groundwater measurement."}}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"output": str(output.relative_to(ROOT)), "feature_counts": counts}, indent=2))


if __name__ == "__main__":
    main()
