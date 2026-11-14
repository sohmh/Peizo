from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import shapefile
from shapely.geometry import Point, box
from openpyxl import load_workbook
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "Datasets" / "GWSI_ZIP_20260714"
BOUNDS = (-112.80, 33.20, -111.35, 34.10)


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def main() -> None:
    shapefile_path = SOURCE / "Shape" / "GWSI_SITES.shp"
    reader = shapefile.Reader(str(shapefile_path), encoding="utf-8")
    field_names = [field[0] for field in reader.fields[1:]]
    rectangle = box(*BOUNDS)
    to_wgs84 = Transformer.from_crs("EPSG:4269", "EPSG:4326", always_xy=True)
    sites = {}
    features = []
    for item in reader.iterShapeRecords():
        attrs = dict(zip(field_names, item.record))
        latitude, longitude = attrs.get("DD_LAT"), attrs.get("DD_LONG")
        if latitude is None or longitude is None or not rectangle.covers(Point(longitude, latitude)):
            continue
        site_id = str(attrs["SITE_ID"]).strip()
        attrs = {key: json_value(value) for key, value in attrs.items()}
        sites[site_id] = attrs
        display_lon, display_lat = to_wgs84.transform(float(longitude), float(latitude))
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [display_lon, display_lat]}, "properties": attrs})

    observations: dict[str, list[dict]] = defaultdict(list)
    workbook = load_workbook(SOURCE / "Data_Tables" / "GWSI_WW_LEVELS.xlsx", read_only=True, data_only=True)
    sheet = workbook.active
    header = [cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
    indexes = {name: header.index(name) for name in header}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        site_id = str(row[indexes["WLWA_SITE_WELL_SITE_ID"]]).strip() if row[indexes["WLWA_SITE_WELL_SITE_ID"]] is not None else ""
        if site_id not in sites:
            continue
        measured = row[indexes["WLWA_MEASUREMENT_DATE"]]
        if measured is None:
            continue
        record = {
            "date": json_value(measured),
            "measurement_id": json_value(row[indexes["WLWA_ID"]]),
            "depth_to_water": json_value(row[indexes["WLWA_DEPTH_TO_WATER"]]),
            "water_level_elevation": json_value(row[indexes["WLWA_WATER_LEVEL_ELEVATION"]]),
            "source_code": json_value(row[indexes["WLWA_SOURCE_CODE"]]),
            "method_code": json_value(row[indexes["WLWA_METHOD_CODE"]]),
            "remark_code": json_value(row[indexes["WLWA_REMARK_CODE"]]),
        }
        observations[site_id].append(record)
    workbook.close()

    station_list = []
    sites_with_level_values = 0
    rows_with_level_values = 0
    for site_id, attrs in sites.items():
        rows = sorted(observations.get(site_id, []), key=lambda item: item["date"])
        valued_rows = [row for row in rows if row.get("depth_to_water") is not None or row.get("water_level_elevation") is not None]
        definitions = []
        if any(row.get("depth_to_water") is not None for row in valued_rows):
            definitions.append({"parameter_code": "WLWA_DEPTH_TO_WATER", "unit": "ft", "vertical_datum": "depth below land surface"})
        if any(row.get("water_level_elevation") is not None for row in valued_rows):
            definitions.append({"parameter_code": "WLWA_WATER_LEVEL_ELEVATION", "unit": "ft", "vertical_datum": "not specified in this table"})
        if valued_rows:
            sites_with_level_values += 1
            rows_with_level_values += len(valued_rows)
        station_list.append({
            "station_id": f"ADWR:{site_id}", "site_id": site_id, "latitude": to_wgs84.transform(float(attrs["DD_LONG"]), float(attrs["DD_LAT"]))[1], "longitude": to_wgs84.transform(float(attrs["DD_LONG"]), float(attrs["DD_LAT"]))[0],
            "well_type": attrs.get("WELL_TYPE"), "water_use": attrs.get("WATER_USE"),
            "inventory_last_water_level_date": attrs.get("LASTWLDATE"), "inventory_depth_to_water_ft": attrs.get("WL_DTW"),
            "inventory_water_level_elevation_ft": attrs.get("WL_ELEV"), "observation_count": len(rows),
            "date_start": valued_rows[0]["date"] if valued_rows else None, "date_end": valued_rows[-1]["date"] if valued_rows else None,
            "measurement_definitions": definitions,
        })
        station_list[-1]["observation_count"] = len(valued_rows)

    output = ROOT / "data" / "processed" / "groundwater"
    output.mkdir(parents=True, exist_ok=True)
    metadata = {"provider": "Arizona Department of Water Resources", "dataset": "Groundwater Site Inventory GWSI_SITES and GWSI_WW_LEVELS", "source_geometry_crs": "NAD83 / UTM zone 12N (EPSG:26912)", "source_coordinate_attributes": "DD_LAT/DD_LONG in NAD83 geographic coordinates (EPSG:4269), confirmed by source XML lineage", "display_crs": "WGS84 longitude/latitude (EPSG:4326)", "study_rectangle_wgs84": list(BOUNDS), "source_site_count": len(reader), "phoenix_site_count": len(sites), "measurement_rows_for_phoenix_sites": sum(map(len, observations.values())), "measurement_rows_with_level_values": rows_with_level_values, "sites_with_level_measurements": sites_with_level_values, "rows_without_either_level_field": sum(1 for rows in observations.values() for row in rows if row.get("depth_to_water") is None and row.get("water_level_elevation") is None), "units": "GWSI water level fields in feet per handbook; no conversion", "limitations": ["Site inventory does not represent a complete census of active wells", "Water-level elevation datum is not included in the joined table and remains unspecified", "Source, method and remark codes are preserved but not decoded in this derivative", "No interpolation or temporal aggregation"]}
    (output / "adwr_gwsi_phoenix.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features, "metadata": metadata}, ensure_ascii=False), encoding="utf-8")
    (output / "adwr_gwsi_phoenix.json").write_text(json.dumps({"metadata": metadata, "stations": station_list, "observations": dict(observations)}, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
