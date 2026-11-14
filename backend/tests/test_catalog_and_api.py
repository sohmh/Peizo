from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import HTTPException

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
        "/api/health", "/api/project/summary", "/api/layers", "/api/nisar/scenes",
        "/api/nisar/sample", "/api/groundwater/stations", "/api/groundwater/stations.geojson",
        "/api/groundwater/adwr-sites.geojson", "/api/context/basins.geojson", "/api/rainfall/series",
        "/api/water-storage/series", "/api/facilities", "/api/facilities/summary", "/api/evidence/phoenix",
    }.issubset(paths)


def test_health_and_catalog_functions_reflect_real_catalog() -> None:
    assert health()["catalog_available"] is True
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
