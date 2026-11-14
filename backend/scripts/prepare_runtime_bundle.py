from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "data" / "processed"
RUNTIME = ROOT / "data" / "runtime" / "processed"
MANIFEST = ROOT / "data" / "runtime" / "asset_manifest.json"

# Browser/API runtime assets only. The two large NISAR COGs are represented in
# the manifest but uploaded to R2; duplicate analysis GeoTIFFs are not deployed.
LOCAL_PRODUCTS = (
    "groundwater/phoenix_groundwater.json",
    "groundwater/adwr_gwsi_phoenix.json",
    "groundwater/adwr_gwsi_phoenix.geojson",
    "context/phoenix_basin_boundaries.geojson",
    "grace/phoenix_mascon_series.json",
    "prism/prism_oct2026_phoenix_cog.tif",
    "prism/prism_oct2026_quicklook.png",
    "nisar/frame71_hhhh_manifest.json",
    "nisar/frame71_hhhh_quicklook.png",
    "nisar/frame71_hvhv_manifest.json",
    "nisar/frame71_hvhv_quicklook.png",
)
REMOTE_PRODUCTS = (
    "nisar/frame71_hhhh_phoenix_cog.tif",
    "nisar/frame71_hvhv_phoenix_cog.tif",
)


def describe(path: Path, key: str) -> dict[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"key": key, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def main() -> None:
    missing = [name for name in (*LOCAL_PRODUCTS, *REMOTE_PRODUCTS) if not (SOURCE / name).is_file()]
    if missing:
        raise SystemExit("Missing processed source products: " + ", ".join(missing))

    local_records = []
    for name in LOCAL_PRODUCTS:
        source = SOURCE / name
        destination = RUNTIME / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        local_records.append(describe(destination, name))

    remote_records = [describe(SOURCE / name, name) for name in REMOTE_PRODUCTS]
    manifest = {
        "study_area": "Phoenix metropolitan region, Arizona",
        "format_version": 1,
        "local_products": local_records,
        "r2_products": remote_records,
        "notes": [
            "No raw satellite data is copied into this runtime bundle.",
            "R2 COG objects must match the recorded object key and byte length; SHA-256 is provided for upload verification.",
        ],
    }
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    total = sum(record["bytes"] for record in local_records)
    print(f"Prepared {len(local_records)} tracked runtime products ({total / 1024 / 1024:.2f} MiB).")
    print(f"R2 upload required for {len(remote_records)} COGs ({sum(item['bytes'] for item in remote_records) / 1024 / 1024:.2f} MiB).")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
