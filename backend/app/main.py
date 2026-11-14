from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("PIEZO_DATA_ROOT", str(ROOT / "data"))).resolve()
CATALOG_DIR = DATA_DIR / "catalog"
PROCESSED_DIR = Path(os.getenv("PIEZO_PROCESSED_ROOT", str(DATA_DIR / "processed"))).resolve()
MANIFEST_DIR = Path(os.getenv("PIEZO_MANIFEST_ROOT", str(DATA_DIR / "manifests"))).resolve()
R2_PUBLIC_BASE_URL = os.getenv("PIEZO_R2_PUBLIC_BASE_URL", "").rstrip("/")

NISAR_CHANNELS = ("HHHH", "HVHV")


def nisar_cog_name(channel: str) -> str:
    return f"frame71_{channel.lower()}_phoenix_cog.tif"


def local_nisar_cog(channel: str) -> Path:
    return PROCESSED_DIR / "nisar" / nisar_cog_name(channel)


def nisar_cog_url(channel: str) -> str | None:
    if not R2_PUBLIC_BASE_URL:
        return None
    return f"{R2_PUBLIC_BASE_URL}/nisar/{nisar_cog_name(channel)}"


def nisar_cog_available(channel: str) -> bool:
    return local_nisar_cog(channel).is_file() or nisar_cog_url(channel) is not None


def data_readiness(verify_remote_cogs: bool = False) -> dict[str, Any]:
    """Check the real catalog/runtime products without substituting sample data."""
    required = {
        "catalog/datasets.json": CATALOG_DIR / "datasets.json",
        "catalog/facilities.json": CATALOG_DIR / "facilities.json",
        "catalog/evidence.json": CATALOG_DIR / "evidence.json",
        "catalog/water_disclosures.json": CATALOG_DIR / "water_disclosures.json",
        "catalog/layers.json": CATALOG_DIR / "layers.json",
        "runtime/asset_manifest.json": DATA_DIR / "runtime" / "asset_manifest.json",
        "manifests/prism_oct2026_phoenix.json": MANIFEST_DIR / "prism_oct2026_phoenix.json",
        "processed/groundwater/phoenix_groundwater.json": PROCESSED_DIR / "groundwater" / "phoenix_groundwater.json",
        "processed/groundwater/adwr_gwsi_phoenix.json": PROCESSED_DIR / "groundwater" / "adwr_gwsi_phoenix.json",
        "processed/groundwater/adwr_gwsi_phoenix.geojson": PROCESSED_DIR / "groundwater" / "adwr_gwsi_phoenix.geojson",
        "processed/context/phoenix_basin_boundaries.geojson": PROCESSED_DIR / "context" / "phoenix_basin_boundaries.geojson",
        "processed/grace/phoenix_mascon_series.json": PROCESSED_DIR / "grace" / "phoenix_mascon_series.json",
        "processed/prism/prism_oct2026_quicklook.png": PROCESSED_DIR / "prism" / "prism_oct2026_quicklook.png",
    }
    for channel in NISAR_CHANNELS:
        stem = f"frame71_{channel.lower()}"
        required[f"processed/nisar/{stem}_manifest.json"] = PROCESSED_DIR / "nisar" / f"{stem}_manifest.json"
        required[f"processed/nisar/{stem}_quicklook.png"] = PROCESSED_DIR / "nisar" / f"{stem}_quicklook.png"
    missing = [name for name, path in required.items() if not path.is_file()]
    remote_cogs_configured = all(nisar_cog_url(channel) for channel in NISAR_CHANNELS)
    missing_cogs = [nisar_cog_name(channel) for channel in NISAR_CHANNELS if not local_nisar_cog(channel).is_file() and not nisar_cog_url(channel)]
    inaccessible_remote_cogs: list[str] = []
    if verify_remote_cogs:
        asset_manifest_path = DATA_DIR / "runtime" / "asset_manifest.json"
        try:
            asset_manifest = json.loads(asset_manifest_path.read_text(encoding="utf-8"))
            expected_sizes = {item["key"]: int(item["bytes"]) for item in asset_manifest.get("r2_products", [])}
        except (OSError, ValueError, KeyError, TypeError):
            expected_sizes = {}
        for channel in NISAR_CHANNELS:
            if local_nisar_cog(channel).is_file():
                continue
            remote_url = nisar_cog_url(channel)
            if not remote_url:
                inaccessible_remote_cogs.append(nisar_cog_name(channel))
                continue
            try:
                with urlopen(Request(remote_url, method="HEAD"), timeout=8) as response:
                    actual_size = response.headers.get("Content-Length")
                    expected_size = expected_sizes.get(f"nisar/{nisar_cog_name(channel)}")
                    if response.status != 200 or expected_size is None or actual_size is None or int(actual_size) != expected_size:
                        inaccessible_remote_cogs.append(nisar_cog_name(channel))
            except (ValueError, TypeError):
                inaccessible_remote_cogs.append(nisar_cog_name(channel))
            except (HTTPError, URLError, TimeoutError, OSError):
                inaccessible_remote_cogs.append(nisar_cog_name(channel))
    components = {
        "catalog": "available" if not any(name.startswith("catalog/") for name in missing) else "unavailable",
        "nisar": "available" if not any("nisar/" in name for name in missing) and not missing_cogs and not inaccessible_remote_cogs else "unavailable",
        "groundwater": "available" if not any("groundwater/" in name for name in missing) else "unavailable",
        "rainfall": "available" if not any(name.startswith("manifests/prism") or "processed/prism/" in name for name in missing) else "unavailable",
        "water_storage": "available" if "processed/grace/phoenix_mascon_series.json" not in missing else "unavailable",
        "basin_context": "available" if "processed/context/phoenix_basin_boundaries.geojson" not in missing else "unavailable",
    }
    return {
        "ready": not missing and not missing_cogs and not inaccessible_remote_cogs,
        "components": components,
        "missing_assets": missing,
        "missing_nisar_cogs": missing_cogs,
        "inaccessible_r2_cogs": inaccessible_remote_cogs,
        "r2_configured": remote_cogs_configured,
    }


def read_json(name: str, default: Any) -> Any:
    path = CATALOG_DIR / name
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


@lru_cache(maxsize=1)
def read_groundwater() -> dict[str, Any] | None:
    path = PROCESSED_DIR / "groundwater" / "phoenix_groundwater.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


@lru_cache(maxsize=1)
def read_adwr_groundwater() -> dict[str, Any] | None:
    path = PROCESSED_DIR / "groundwater" / "adwr_gwsi_phoenix.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


app = FastAPI(title="PIEZO API", version="0.1.0", description="Evidence-led Phoenix radar and water context")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("PIEZO_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, Any]:
    readiness = data_readiness()
    datasets = read_json("datasets.json", [])
    return {
        "status": "ok",
        "ready": readiness["ready"],
        "catalog_available": readiness["components"]["catalog"] == "available" and bool(datasets),
        "dataset_records": len(datasets),
        **readiness,
    }


@app.get("/api/ready")
def ready() -> JSONResponse:
    readiness = data_readiness(verify_remote_cogs=True)
    status_code = 200 if readiness["ready"] else 503
    return JSONResponse({"status": "ready" if readiness["ready"] else "degraded", **readiness}, status_code=status_code)


@app.get("/api/project/summary")
def project_summary() -> dict[str, Any]:
    datasets = read_json("datasets.json", [])
    facilities = read_json("facilities.json", [])
    disclosures = read_json("water_disclosures.json", [])
    groundwater = read_groundwater()
    adwr_groundwater = read_adwr_groundwater()
    prism_manifest = MANIFEST_DIR / "prism_oct2026_phoenix.json"
    grace_series = PROCESSED_DIR / "grace" / "phoenix_mascon_series.json"
    return {
        "project": "PIEZO",
        "study_area": "Phoenix metropolitan region, Arizona",
        "dataset_count": len(datasets),
        "nisar_scene_count": sum(1 for row in datasets if row.get("kind") == "nisar_gcov"),
        "facility_records": len(facilities),
        "mapped_facilities": sum(1 for row in facilities if row.get("latitude") is not None and row.get("longitude") is not None),
        "water_disclosures": len(disclosures),
        "usgs_station_count": len(groundwater["stations"]) if groundwater else 0,
        "groundwater_observation_count": groundwater["observation_count_in_rectangle"] if groundwater else 0,
        "adwr_gwsi_site_count": len(adwr_groundwater["stations"]) if adwr_groundwater else 0,
        "adwr_gwsi_sites_with_level_measurements": adwr_groundwater["metadata"].get("sites_with_level_measurements", 0) if adwr_groundwater else 0,
        "adwr_gwsi_observation_count": adwr_groundwater["metadata"].get("measurement_rows_with_level_values", 0) if adwr_groundwater else 0,
        "adwr_gwsi_measurement_table_rows": adwr_groundwater["metadata"]["measurement_rows_for_phoenix_sites"] if adwr_groundwater else 0,
        "temporal_change_available": False,
        "availability": {
            "nisar": "available" if nisar_cog_available("HHHH") and (PROCESSED_DIR / "nisar" / "frame71_hhhh_manifest.json").is_file() else "source available; derived products or R2 COG configuration pending",
            "groundwater": "available" if groundwater and adwr_groundwater else "partially_available" if groundwater or adwr_groundwater else "source available; normalized API layer pending",
            "rainfall": "available" if prism_manifest.exists() else "source available; raster processing pending",
            "water_storage": "available" if grace_series.exists() else "source available; coarse regional context pending",
            "facilities": f"partially sourced; {sum(1 for row in facilities if row.get('latitude') is not None and row.get('longitude') is not None)} source-published coordinate records of {len(facilities)} directory entries",
        },
    }


@app.get("/api/datasets")
def datasets() -> list[dict[str, Any]]:
    return read_json("datasets.json", [])


@app.get("/api/layers")
def layers() -> list[dict[str, Any]]:
    layer_rows = read_json("layers.json", [])
    for row in layer_rows:
        if row.get("id") == "nisar-gcov":
            manifest_path = PROCESSED_DIR / "nisar" / "frame71_hhhh_manifest.json"
            row["available"] = manifest_path.is_file() and nisar_cog_available("HHHH")
            if row["available"]:
                row["status"] = "frame 71 Frequency A HHHH and HVHV crops processed"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                row["image_url"] = "/derived/nisar/" + manifest["outputs"]["quicklook_png"]
                row["image_corners"] = manifest["display_corners_lonlat_nw_ne_se_sw"]
                row["display_stretch"] = manifest["display_stretch"]
            channel_layers = []
            for term in ("HHHH", "HVHV"):
                channel_manifest = PROCESSED_DIR / "nisar" / f"frame71_{term.lower()}_manifest.json"
                if channel_manifest.is_file():
                    channel = json.loads(channel_manifest.read_text(encoding="utf-8"))
                    channel_layers.append({"term": term, "frequency": channel["frequency"], "units": channel["units"], "available": nisar_cog_available(term), "image_url": "/derived/nisar/" + channel["outputs"]["quicklook_png"], "image_corners": channel["display_corners_lonlat_nw_ne_se_sw"], "display_stretch": channel["display_stretch"]})
                else:
                    channel_layers.append({"term": term, "frequency": "frequencyA", "available": False})
            row["channel_layers"] = channel_layers
        if row.get("id") == "prism-rainfall":
            manifest_path = MANIFEST_DIR / "prism_oct2026_phoenix.json"
            row["available"] = manifest_path.exists()
            if row["available"]:
                row["status"] = "October 2026 Phoenix raster crop and COG available"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                row["image_url"] = "/derived/prism/" + manifest["outputs"]["quicklook_png"]
                row["image_corners"] = manifest["display_corners_lonlat_nw_ne_se_sw"]
                row["display_stretch"] = manifest["display_stretch"]
                row["regional_mean_mm"] = manifest["regional_mean_mm"]
                row["units"] = manifest["units"]
        if row.get("id") == "groundwater-stations":
            groundwater = read_groundwater()
            row["available"] = groundwater is not None
            row["station_count"] = len(groundwater["stations"]) if groundwater else 0
            if groundwater:
                row["status"] = f"{len(groundwater['stations'])} USGS stations; source observations preserved"
                row["geojson_url"] = "/api/groundwater/stations.geojson"
        if row.get("id") == "adwr-gwsi-sites":
            adwr = read_adwr_groundwater()
            row["available"] = adwr is not None
            row["site_count"] = len(adwr["stations"]) if adwr else 0
            row["measurement_count"] = adwr["metadata"].get("measurement_rows_with_level_values", 0) if adwr else 0
            if adwr:
                row["geojson_url"] = "/api/groundwater/adwr-sites.geojson"
        if row.get("id") == "adwr-basin-context":
            basin_path = PROCESSED_DIR / "context" / "phoenix_basin_boundaries.geojson"
            row["available"] = basin_path.exists()
            if row["available"]:
                basin_data = json.loads(basin_path.read_text(encoding="utf-8"))
                row["feature_count"] = len(basin_data["features"])
                row["geojson_url"] = "/api/context/basins.geojson"
        if row.get("id") == "grace-storage":
            grace_path = PROCESSED_DIR / "grace" / "phoenix_mascon_series.json"
            row["available"] = grace_path.exists()
            if row["available"]:
                report = json.loads(grace_path.read_text(encoding="utf-8"))
                row["status"] = "JPL monthly series available at native coarse mascon support"
                row["record_count"] = report["record_count"]
                row["mascon_id"] = report["selected_mascon_id"]
    return layer_rows


@app.get("/derived/{product_path:path}")
def derived_product(product_path: str) -> FileResponse | RedirectResponse:
    base = PROCESSED_DIR.resolve()
    target = (base / product_path).resolve()
    if base not in target.parents:
        raise HTTPException(status_code=404, detail="Derived product not found")
    if target.is_file():
        return FileResponse(target)
    # Only the two known Phoenix COG objects may redirect to the public R2 bucket.
    allowed_r2_cogs = {f"nisar/{nisar_cog_name(channel)}" for channel in NISAR_CHANNELS}
    if product_path.replace("\\", "/") in allowed_r2_cogs and R2_PUBLIC_BASE_URL:
        channel = "HHHH" if "hhhh" in product_path.lower() else "HVHV"
        return RedirectResponse(nisar_cog_url(channel), status_code=302)  # type: ignore[arg-type]
    raise HTTPException(status_code=404, detail="Derived product not found in the local runtime bundle or configured R2 bucket")


@app.get("/api/nisar/scenes")
def nisar_scenes() -> list[dict[str, Any]]:
    return [row for row in datasets() if row.get("kind") == "nisar_gcov"]


@app.get("/api/nisar/scenes/{scene_id}/channels")
def nisar_channels(scene_id: str) -> dict[str, Any]:
    scene = next((row for row in nisar_scenes() if row.get("scene_id") == scene_id), None)
    if scene is None:
        raise HTTPException(status_code=404, detail="Scene not found")
    channels = scene.get("channels", [])
    if scene_id == "frame71-20261028":
        for channel in channels:
            stem = f"frame71_{channel['term'].lower()}"
            if channel["frequency"] in {"frequencyA", "A"} and nisar_cog_available(channel["term"]):
                channel["status"] = "processed"
                channel["frequency"] = "frequencyA"
                channel["analysis_raster"] = f"/derived/nisar/{stem}_phoenix_cog.tif"
                channel["display_quicklook"] = f"/derived/nisar/{stem}_quicklook.png"
    availability = "partially_processed" if any(channel.get("status") == "processed" for channel in channels) else "not_processed"
    return {"scene_id": scene_id, "availability": availability, "channels": channels}


@app.get("/api/nisar/sample")
def nisar_sample(longitude: float, latitude: float, channel: str = Query(default="HHHH", pattern="^(HHHH|HVHV)$")) -> dict[str, Any]:
    import rasterio
    from rasterio.errors import RasterioError
    from rasterio.transform import rowcol
    from rasterio.warp import transform

    path: str | Path = local_nisar_cog(channel)
    if not Path(path).is_file():
        remote_url = nisar_cog_url(channel)
        if remote_url:
            path = f"/vsicurl/{remote_url}"
    if not Path(path).is_file() and not str(path).startswith("/vsicurl/"):
        raise HTTPException(status_code=404, detail="Selected channel has not been processed")
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif", GDAL_HTTP_MULTIRANGE="YES"):
            with rasterio.open(path) as raster:
                x, y = transform("EPSG:4326", raster.crs, [longitude], [latitude])
                row, col = rowcol(raster.transform, x[0], y[0])
                if row < 0 or col < 0 or row >= raster.height or col >= raster.width:
                    raise HTTPException(status_code=404, detail="Coordinate is outside the Phoenix crop")
                value = float(raster.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
                mask = int(raster.read_masks(1, window=((row, row + 1), (col, col + 1)))[0, 0])
                if mask == 0:
                    return {"availability": "masked", "longitude": longitude, "latitude": latitude, "channel": channel, "frequency": "frequencyA", "units": "1", "value": None, "message": "The source mask marks this pixel invalid."}
                return {"availability": "available", "longitude": longitude, "latitude": latitude, "channel": channel, "frequency": "frequencyA", "units": "1", "value": value, "scene_id": "frame71-20261028", "acquisition_date": "2026-10-28", "interpretation": "Source GCOV covariance term; not a groundwater measurement."}
    except HTTPException:
        raise
    except (RasterioError, OSError, RuntimeError) as exc:
        if str(path).startswith("/vsicurl/"):
            raise HTTPException(status_code=503, detail="NISAR COG is configured in R2 but could not be read. Verify the object key, public access and byte-range support.") from exc
        raise


@app.get("/api/groundwater/stations")
def groundwater_stations() -> dict[str, Any]:
    data = read_groundwater()
    adwr = read_adwr_groundwater()
    if data is None and adwr is None:
        return {"availability": "not_normalized", "stations": [], "source": "USGS field-measurement export and ADWR GWSI; source validation pending"}
    usgs = [{**row, "provider": "USGS"} for row in data["stations"]] if data else []
    arizona = [{**row, "provider": "ADWR GWSI"} for row in adwr["stations"]] if adwr else []
    return {"availability": "available" if data and adwr else "partially_available", "source": "USGS field measurements and ADWR GWSI", "study_rectangle_wgs84": (data or adwr["metadata"])["study_rectangle_wgs84"], "provider_counts": {"USGS": len(usgs), "ADWR GWSI": len(arizona)}, "adwr_sites_with_level_measurements": adwr["metadata"].get("sites_with_level_measurements", 0) if adwr else 0, "stations": usgs + arizona}


@app.get("/api/groundwater/stations.geojson")
def groundwater_stations_geojson() -> dict[str, Any]:
    data = read_groundwater()
    if data is None:
        return {"type": "FeatureCollection", "features": [], "availability": "not_normalized"}
    return {"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [station["longitude"], station["latitude"]]}, "properties": station} for station in data["stations"]], "availability": "available"}


@app.get("/api/groundwater/adwr-sites.geojson")
def adwr_sites_geojson() -> dict[str, Any]:
    path = PROCESSED_DIR / "groundwater" / "adwr_gwsi_phoenix.geojson"
    if not path.exists():
        return {"type": "FeatureCollection", "features": [], "availability": "not_processed"}
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/context/basins.geojson")
def basin_context_geojson() -> dict[str, Any]:
    path = PROCESSED_DIR / "context" / "phoenix_basin_boundaries.geojson"
    if not path.exists():
        return {"type": "FeatureCollection", "features": [], "availability": "not_processed"}
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/groundwater/stations/{station_id}/observations")
def groundwater_observations(station_id: str, parameter_code: str | None = Query(default=None), unit: str | None = Query(default=None), vertical_datum: str | None = Query(default=None)) -> dict[str, Any]:
    if station_id.startswith("ADWR:"):
        adwr = read_adwr_groundwater()
        if adwr is None:
            return {"station_id": station_id, "availability": "not_normalized", "observations": []}
        site_id = station_id.removeprefix("ADWR:")
        rows = adwr["observations"].get(site_id)
        if rows is None:
            raise HTTPException(status_code=404, detail="ADWR site not found in the Phoenix-filtered GWSI export")
        definitions = {"WLWA_DEPTH_TO_WATER": ("Depth to water", "depth_to_water", "depth below land surface"), "WLWA_WATER_LEVEL_ELEVATION": ("Water-level elevation", "water_level_elevation", "not specified in this table")}
        observations = []
        for row in rows:
            for code, (description, field, datum) in definitions.items():
                value = row.get(field)
                if value is None or (parameter_code and parameter_code != code) or (unit and unit != "ft") or (vertical_datum and vertical_datum != datum):
                    continue
                observations.append({"date": row["date"], "value": value, "parameter_code": code, "parameter_description": f"{description} (ADWR GWSI)", "unit": "ft", "vertical_datum": datum, "reading_type": "discrete well measurement", "approval_status": None, "qualifier": row.get("remark_code"), "method": row.get("method_code"), "source_code": row.get("source_code"), "measurement_id": row.get("measurement_id")})
        observations.sort(key=lambda item: item["date"])
        return {"station_id": station_id, "availability": "available", "source": "ADWR GWSI_WW_LEVELS", "observations": observations}
    data = read_groundwater()
    if data is None:
        return {"station_id": station_id, "availability": "not_normalized", "observations": []}
    rows = data["observations"].get(station_id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Station not found in the Phoenix-filtered source export")
    if parameter_code:
        rows = [row for row in rows if row["parameter_code"] == parameter_code]
    if unit:
        rows = [row for row in rows if row["unit"] == unit]
    if vertical_datum:
        rows = [row for row in rows if (row["vertical_datum"] or "not specified in source table") == vertical_datum]
    return {"station_id": station_id, "availability": "available", "observations": rows}


@app.get("/api/rainfall/series")
def rainfall_series() -> dict[str, Any]:
    path = MANIFEST_DIR / "prism_oct2026_phoenix.json"
    if not path.exists():
        return {"availability": "not_processed", "series": [], "source": "PRISM October 2026 monthly precipitation grid"}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {"availability": "available", "source": report["source_provider"], "variable": report["variable"], "aggregation": "arithmetic mean of valid native grid cells whose centers fall within the source rectangle; no area weighting", "spatial_support": "PRISM 30 arc-second (~800 m) grid cells", "dataset_version": report.get("dataset_version"), "release_number": report.get("release_number"), "dataset_create_date": report.get("dataset_create_date"), "vintage_note": report.get("vintage_note"), "series": [{"date": report["period"], "period_label": "October 2026", "period_type": "monthly", "value": report["regional_mean_mm"], "unit": report["units"], "valid_cell_count": report["valid_cell_count"]}], "limitations": report["limitations"]}


@app.get("/api/water-storage/series")
def water_storage_series() -> dict[str, Any]:
    path = PROCESSED_DIR / "grace" / "phoenix_mascon_series.json"
    if not path.exists():
        return {"availability": "not_processed", "series": [], "source": "JPL GRACE/GRACE-FO RL06.3Mv04 CRI total water storage anomaly; native mascon support is coarse"}
    report = json.loads(path.read_text(encoding="utf-8"))
    return {"availability": "available", "source": report["provider"], "product": report["product"], "doi": report["doi"], "variable": report["variable"], "interpretation": report["interpretation"], "native_support": report["native_support"], "mascon_id": report["selected_mascon_id"], "series": report["series"], "limitations": report["limitations"]}


@app.get("/api/facilities")
def facilities() -> list[dict[str, Any]]:
    rows = read_json("facilities.json", [])
    disclosures = read_json("water_disclosures.json", [])
    for row in rows:
        row["water_disclosures"] = [item for item in disclosures if item.get("facility_id") == row["facility_id"]]
    return rows


@app.get("/api/facilities/summary")
def facilities_summary() -> dict[str, Any]:
    rows = facilities()
    disclosures = read_json("water_disclosures.json", [])
    return {
        "facility_records": len(rows),
        "verified_locations": sum(1 for row in rows if row.get("latitude") is not None and row.get("longitude") is not None),
        "operating_status_verified": sum(1 for row in rows if row.get("status") == "operating"),
        "site_specific_water_figures": sum(1 for row in disclosures if row.get("scope") == "site" and row.get("reported_quantity") is not None),
        "disclosure_records": len(disclosures),
        "public_search_complete": False,
        "message": "Counts describe verified records in this register. Public-source coverage is still being researched.",
    }


@app.get("/api/facilities/{facility_id}/water-disclosures")
def facility_disclosures(facility_id: str) -> list[dict[str, Any]]:
    if not any(row.get("facility_id") == facility_id for row in facilities()):
        raise HTTPException(status_code=404, detail="Facility not found")
    return [row for row in read_json("water_disclosures.json", []) if row.get("facility_id") == facility_id]


@app.get("/api/facilities/{facility_id}")
def facility_profile(facility_id: str) -> dict[str, Any]:
    facility = next((row for row in facilities() if row.get("facility_id") == facility_id), None)
    if facility is None:
        raise HTTPException(status_code=404, detail="Facility not found")
    evidence = read_json("evidence.json", [])
    return {**facility, "water_disclosures": [row for row in read_json("water_disclosures.json", []) if row.get("facility_id") == facility_id], "evidence": [row for row in evidence if row.get("claim_target_id") == facility_id]}


@app.get("/api/evidence/phoenix")
def phoenix_evidence() -> dict[str, Any]:
    return {
        "study_area": "Phoenix metropolitan region, Arizona",
        "observed": ["NISAR GCOV single-date radar surface observations", "USGS field measurements from stations in the Phoenix study rectangle", "ADWR GWSI water-level measurements joined to Phoenix-area well sites"],
        "modeled": ["PRISM October 2026 monthly precipitation grid at 30 arc-second output resolution"],
        "regional_estimate": ["GRACE/GRACE-FO total water storage anomaly for the mascon containing Phoenix at coarse native support"],
        "reported": ["Source-backed facility location and cooling statement for Edged Phoenix; status and total water use unknown"],
        "hypotheses": [],
        "limitations": ["One NISAR acquisition date; no temporal change analysis", "Radar observations do not directly measure groundwater", "ADWR source/method/remark codes remain undecoded and water-level elevation datum is unspecified", "USGS export query provenance is incomplete", "Facility proximity does not establish causation"],
    }
