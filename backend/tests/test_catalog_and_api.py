from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.app import main as api_module
from backend.app.main import (
    app,
    adwr_sites_geojson,
    basin_context_geojson,
    datasets,
    derived_product,
    facility_profile,
    facilities,
    facilities_summary,
    phoenix_evidence,
    project_summary,
    read_json,
    groundwater_stations,
    health,
    ready,
    layers,
    groundwater_observations,
    nisar_channels,
    nisar_sample,
    rainfall_series,
    water_storage_series,
)

ROOT = Path(__file__).resolve().parents[2]


def test_api_openapi_registers_core_request_paths() -> None:
    paths = set(app.openapi()["paths"])
    assert {
        "/api/health", "/api/ready", "/api/project/summary", "/api/datasets", "/api/layers", "/api/evidence/phoenix", "/api/nisar/scenes",
        "/api/nisar/scenes/{scene_id}/channels", "/api/nisar/sample", "/api/groundwater/stations", "/api/groundwater/stations/{station_id}/observations", "/api/groundwater/stations.geojson",
        "/api/groundwater/adwr-sites.geojson", "/api/context/basins.geojson", "/api/rainfall/series",
        "/api/water-storage/series", "/api/facilities", "/api/facilities/summary", "/api/facilities/{facility_id}", "/api/facilities/{facility_id}/water-disclosures",
    }.issubset(paths)


def test_health_and_catalog_functions_reflect_real_catalog() -> None:
    status = health()
    assert status["catalog_available"] is True
    assert status["ready"] is True
    assert status["missing_assets"] == []
    ready_response = ready()
    assert json.loads(ready_response.body)["status"] == "ready"
    assert ready_response.status_code == 200
    rows = datasets()
    assert len(rows) >= 5
    assert {row["scene_id"] for row in rows if row.get("kind") == "nisar_gcov"} == {"frame71-20261028", "frame72-20261028"}
    frame71, frame72 = [row for row in rows if row.get("kind") == "nisar_gcov"]
    assert frame71["acquisition_start"][:10] == frame72["acquisition_start"][:10]
    assert frame71["track"] == frame72["track"] and frame71["orbit"] == frame72["orbit"]
    assert project_summary()["temporal_change_available"] is False


def test_facility_profile_carries_evidence_and_unknown_water_usage() -> None:
    rows = facilities()
    assert len(rows) == 6
    edged = facility_profile("phx-edged-mesa-01")
    assert edged["evidence"]
    assert edged["water_disclosures"][0]["reported_quantity"] is None
    summary = facilities_summary()
    assert summary["verified_locations"] == 1
    assert summary["operating_status_verified"] == 0
    assert summary["site_specific_water_figures"] == 0
    assert {row["status"] for row in rows} == {"unknown", "proposed"}
    assert all(facility_profile(row["facility_id"])["evidence"] for row in rows)
    ids = {row["facility_id"] for row in rows}
    disclosures = read_json("water_disclosures.json", [])
    evidence = read_json("evidence.json", [])
    assert all(row["facility_id"] in ids for row in disclosures if row.get("facility_id"))
    assert all(row["claim_target_id"] in ids for row in evidence if row.get("claim_target_id"))


def test_verified_groundwater_and_context_products_are_available() -> None:
    station_catalog = groundwater_stations()
    assert station_catalog["availability"] == "available"
    assert station_catalog["provider_counts"] == {"USGS": 507, "ADWR GWSI": 6765}
    assert station_catalog["adwr_sites_with_level_measurements"] == 5152
    summary = project_summary()
    assert summary["usgs_station_count"] == 507
    assert summary["adwr_gwsi_site_count"] == 6765
    assert summary["adwr_gwsi_observation_count"] == 46360
    assert summary["adwr_gwsi_measurement_table_rows"] == 48846
    assert summary["adwr_gwsi_sites_with_level_measurements"] == 5152
    assert len(adwr_sites_geojson()["features"]) == 6765
    boundaries = basin_context_geojson()["features"]
    assert sum(feature["properties"]["boundary_type"] == "basin" for feature in boundaries) == 8
    assert sum(feature["properties"]["boundary_type"] == "subbasin" for feature in boundaries) == 14
    assert phoenix_evidence()["study_area"] == "Phoenix metropolitan region, Arizona"
    adwr_station = next(row for row in station_catalog["stations"] if row["station_id"] == "ADWR:332153111512901")
    adwr_series = groundwater_observations(adwr_station["station_id"], "WLWA_DEPTH_TO_WATER", None, None)
    assert adwr_series["observations"]
    assert adwr_series["observations"][0]["unit"] == "ft"
    if "WLWA_WATER_LEVEL_ELEVATION" in {definition["parameter_code"] for definition in adwr_station["measurement_definitions"]}:
        elevation = groundwater_observations(adwr_station["station_id"], "WLWA_WATER_LEVEL_ELEVATION", "ft", "not specified in this table")
        assert elevation["observations"]
        assert all(row["vertical_datum"] == "not specified in this table" for row in elevation["observations"])
    assert rainfall_series()["availability"] == "available"
    assert water_storage_series()["availability"] == "available"
    assert nisar_channels("frame71-20261028")["availability"] == "partially_processed"
    layer_rows = {row["id"]: row for row in layers()}
    assert layer_rows["nisar-gcov"]["available"] is True
    assert [channel["available"] for channel in layer_rows["nisar-gcov"]["channel_layers"]] == [True, True]
    assert layer_rows["prism-rainfall"]["regional_mean_mm"] == pytest.approx(55.6275, abs=0.01)


def test_nisar_pixel_sampling_uses_processed_source_raster() -> None:
    data = nisar_sample(-112.074, 33.448, "HHHH")
    assert data["channel"] == "HHHH"
    assert data["units"] == "1"
    assert data["availability"] in {"available", "masked"}


def test_prism_and_grace_derivatives_are_source_backed() -> None:
    prism = json.loads((ROOT / "data" / "manifests" / "prism_oct2026_phoenix.json").read_text(encoding="utf-8"))
    grace = json.loads((ROOT / "data" / "processed" / "grace" / "phoenix_mascon_series.json").read_text(encoding="utf-8"))
    assert prism["valid_cell_count"] == 18511
    assert prism["units"] == "mm"
    assert prism["regional_mean_mm"] == pytest.approx(55.6275, abs=0.01)
    assert "cell centers inside" in prism["method"]
    assert grace["record_count"] == 261
    assert grace["selected_mascon_id"] == 1053


def test_derived_product_route_rejects_missing_files_and_traversal() -> None:
    for path in ("does-not-exist.tif", "../../README.md"):
        with pytest.raises(HTTPException) as exc:
            derived_product(path)
        assert exc.value.status_code == 404


def test_curated_runtime_bundle_is_small_and_excludes_large_nisar_cogs() -> None:
    runtime = ROOT / "data" / "runtime"
    manifest = json.loads((runtime / "asset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_area"] == "Phoenix metropolitan region, Arizona"
    assert len(manifest["local_products"]) == 11
    assert {item["key"] for item in manifest["r2_products"]} == {
        "nisar/frame71_hhhh_phoenix_cog.tif",
        "nisar/frame71_hvhv_phoenix_cog.tif",
    }
    assert all(item["sha256"] and item["bytes"] > 100_000_000 for item in manifest["r2_products"])
    assert not list((runtime / "processed" / "nisar").glob("*_phoenix_cog.tif"))
    assert sum(path.stat().st_size for path in (runtime / "processed").rglob("*") if path.is_file()) < 50 * 1024 * 1024


def test_render_blueprint_uses_free_plan_without_disk() -> None:
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")
    assert "plan: free" in blueprint
    assert "disk:" not in blueprint
    assert "data/runtime/processed" in blueprint
    assert "backend/requirements-render.txt" in blueprint
    assert "PIEZO_R2_PUBLIC_BASE_URL" in blueprint


def test_curated_runtime_products_drive_existing_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_module, "PROCESSED_DIR", ROOT / "data" / "runtime" / "processed")
    monkeypatch.setattr(api_module, "R2_PUBLIC_BASE_URL", "https://piezo-assets.example.test")
    status = health()
    assert status["ready"] is True
    layer_rows = {row["id"]: row for row in layers()}
    assert layer_rows["nisar-gcov"]["available"] is True
    assert [item["available"] for item in layer_rows["nisar-gcov"]["channel_layers"]] == [True, True]
    assert len(adwr_sites_geojson()["features"]) == 6765
    assert len(basin_context_geojson()["features"]) == 22
    assert rainfall_series()["availability"] == "available"
    assert water_storage_series()["availability"] == "available"


def test_missing_runtime_products_make_readiness_explicit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(api_module, "PROCESSED_DIR", tmp_path / "empty-processed")
    monkeypatch.setattr(api_module, "R2_PUBLIC_BASE_URL", "")
    status = health()
    assert status["status"] == "ok"
    assert status["ready"] is False
    assert status["components"]["groundwater"] == "unavailable"
    ready_response = ready()
    assert json.loads(ready_response.body)["status"] == "degraded"
    assert ready_response.status_code == 503


def test_nisar_cog_route_redirects_only_known_remote_assets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(api_module, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(api_module, "R2_PUBLIC_BASE_URL", "https://piezo-assets.example.test")
    response = derived_product("nisar/frame71_hhhh_phoenix_cog.tif")
    assert response.status_code == 302
    assert response.headers["location"] == "https://piezo-assets.example.test/nisar/frame71_hhhh_phoenix_cog.tif"
    with pytest.raises(HTTPException) as exc:
        derived_product("nisar/other_cog.tif")
    assert exc.value.status_code == 404


def test_readiness_probes_r2_cog_objects_and_checks_size(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import contextmanager

    manifest = json.loads((ROOT / "data" / "runtime" / "asset_manifest.json").read_text(encoding="utf-8"))
    sizes = {item["key"]: item["bytes"] for item in manifest["r2_products"]}
    requested: list[str] = []

    @contextmanager
    def fake_urlopen(request, timeout):
        requested.append(request.full_url)
        key = request.full_url.split(".test/", 1)[1]
        yield SimpleNamespace(status=200, headers={"Content-Length": str(sizes[key])})

    monkeypatch.setattr(api_module, "PROCESSED_DIR", ROOT / "data" / "runtime" / "processed")
    monkeypatch.setattr(api_module, "R2_PUBLIC_BASE_URL", "https://piezo-assets.example.test")
    monkeypatch.setattr(api_module, "urlopen", fake_urlopen)
    response = ready()
    assert response.status_code == 200
    assert json.loads(response.body)["inaccessible_r2_cogs"] == []
    assert len(requested) == 2


def test_nisar_pixel_sampling_reads_configured_remote_cog(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import numpy as np
    import rasterio
    from affine import Affine
    from rasterio.crs import CRS

    opened: list[str] = []

    class RemoteRaster:
        crs = CRS.from_epsg(4326)
        transform = Affine.translation(-180, 90) @ Affine.scale(36, -18)
        width = 20
        height = 20

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args, **kwargs):
            return np.array([[0.125]], dtype=np.float32)

        def read_masks(self, *args, **kwargs):
            return np.array([[255]], dtype=np.uint8)

    def fake_open(path):
        opened.append(str(path))
        return RemoteRaster()

    monkeypatch.setattr(api_module, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(api_module, "R2_PUBLIC_BASE_URL", "https://piezo-assets.example.test")
    monkeypatch.setattr(rasterio, "open", fake_open)
    result = nisar_sample(-112.074, 33.448, "HHHH")
    assert result["availability"] == "available"
    assert result["value"] == pytest.approx(0.125)
    assert opened == ["/vsicurl/https://piezo-assets.example.test/nisar/frame71_hhhh_phoenix_cog.tif"]
