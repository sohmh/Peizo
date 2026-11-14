from __future__ import annotations

import json
from pathlib import Path

import h5py
import pytest
import rasterio
from shapely import box, wkt

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "Datasets"
PHOENIX = box(-112.80, 33.20, -111.35, 34.10)
SCENES = sorted(DATA_DIR.glob("NISAR_L2_PR_GCOV_034_056_D_0*.h5"))


@pytest.mark.parametrize("path", SCENES, ids=lambda p: p.name.split("_D_")[1][:3])
def test_nisar_source_product_metadata_and_phoenix_footprint(path: Path) -> None:
    assert path.exists()
    with h5py.File(path, "r") as product:
        ident = product["science/LSAR/identification"]
        grid = product["science/LSAR/GCOV/grids/frequencyA"]
        assert int(grid["projection"].attrs["epsg_code"]) == 32612
        assert float(grid["xCoordinateSpacing"][()]) == 10
        assert float(grid["yCoordinateSpacing"][()]) == -10
        terms = {v.decode() for v in grid["listOfCovarianceTerms"][:].tolist()}
        assert {"HHHH", "HVHV"}.issubset(terms)
        poly = wkt.loads(ident["boundingPolygon"][()].decode())
        assert poly.intersects(PHOENIX)
        assert bool(ident["isGeocoded"][()].decode() == "True")


def test_derived_phoenix_cog_if_pipeline_has_completed() -> None:
    cog = ROOT / "data" / "processed" / "nisar" / "frame71_hhhh_phoenix_cog.tif"
    manifest = ROOT / "data" / "processed" / "nisar" / "frame71_hhhh_manifest.json"
    quicklook = ROOT / "data" / "processed" / "nisar" / "frame71_hhhh_quicklook.png"
    if not manifest.exists():
        pytest.skip("NISAR processing has not completed")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["valid_pixel_count"] > 0
    assert data["source_crs"] == "EPSG:32612"
    assert data["channel"] == "HHHH"
    assert quicklook.exists() and quicklook.stat().st_size > 0
    with rasterio.open(cog) as raster:
        assert raster.crs.to_epsg() == 32612
        assert raster.width == data["output_shape"][1]
        assert raster.height == data["output_shape"][0]
        assert raster.bounds.left < raster.bounds.right
        assert raster.bounds.bottom < raster.bounds.top
        # Read a downsampled mask so this metadata check does not load the full
        # 137-million-pixel crop into memory.
        assert raster.read_masks(1, out_shape=(100, 100)).any()
        assert raster.read_masks(1, window=((0, 1), (0, 1)))[0, 0] == 0
    assert "pixel center inside" in data["mask_rule"]


def test_both_processed_nisar_channels_have_valid_cogs() -> None:
    for channel in ("hhhh", "hvhv"):
        cog = ROOT / "data" / "processed" / "nisar" / f"frame71_{channel}_phoenix_cog.tif"
        manifest = ROOT / "data" / "processed" / "nisar" / f"frame71_{channel}_manifest.json"
        if not manifest.exists():
            pytest.skip(f"NISAR {channel.upper()} processing has not completed")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["channel"].lower() == channel
        assert data["valid_pixel_count"] > 0
        with rasterio.open(cog) as raster:
            assert raster.crs.to_epsg() == 32612
            assert raster.read_masks(1, out_shape=(64, 64)).any()
