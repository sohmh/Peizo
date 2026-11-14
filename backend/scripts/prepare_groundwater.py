"""Normalize supplied USGS measurement export inside the documented Phoenix study rectangle."""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "Datasets" / "2026-11-14T11-47-59.452Z-download" / "2026-11-14T11-47-59.452Z-field-measurements.csv"
BOUNDS = {"west": -112.80, "south": 33.20, "east": -111.35, "north": 34.10}
KEEP = ["approval_status", "measuring_agency", "monitoring_location_id", "parameter_code", "qualifier", "reading_type", "observing_procedure", "time", "unit_of_measure", "value", "vertical_datum", "x", "y"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed" / "groundwater")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    series: dict[str, list[dict[str, object]]] = defaultdict(list)
    sites: dict[str, dict[str, object]] = {}
    rows_seen = 0
    for frame in pd.read_csv(args.input, usecols=KEEP, chunksize=50000, dtype={"monitoring_location_id": "string", "parameter_code": "string", "value": "string", "x": "string", "y": "string"}, low_memory=False):
        rows_seen += len(frame)
        frame["longitude"] = pd.to_numeric(frame["x"], errors="coerce")
        frame["latitude"] = pd.to_numeric(frame["y"], errors="coerce")
        mask = frame.longitude.between(BOUNDS["west"], BOUNDS["east"]) & frame.latitude.between(BOUNDS["south"], BOUNDS["north"])
        local = frame.loc[mask]
        for site_id, group in local.groupby("monitoring_location_id", sort=False):
            if pd.isna(site_id) or not str(site_id).strip():
                continue
            first = group.iloc[0]
            if str(site_id) not in sites:
                sites[str(site_id)] = {
                    "station_id": str(site_id), "longitude": float(first.longitude), "latitude": float(first.latitude),
                    "agency": str(first.measuring_agency), "observation_count": 0,
                }
            site = sites[str(site_id)]
            for row in group.itertuples(index=False, name=None):
                values = dict(zip(group.columns, row))
                try:
                    value = float(values["value"])
                except (ValueError, TypeError):
                    continue
                series[str(site_id)].append({
                    "date": str(values["time"]), "value": value,
                    "parameter_code": str(values["parameter_code"]),
                    "parameter_description": None,
                    "unit": str(values["unit_of_measure"]),
                    "vertical_datum": None if pd.isna(values["vertical_datum"]) else str(values["vertical_datum"]),
                    "reading_type": None if pd.isna(values["reading_type"]) else str(values["reading_type"]),
                    "approval_status": None if pd.isna(values["approval_status"]) else str(values["approval_status"]),
                    "qualifier": None if pd.isna(values["qualifier"]) else str(values["qualifier"]),
                    "method": None if pd.isna(values["observing_procedure"]) else str(values["observing_procedure"]),
                })
                site["observation_count"] = int(site["observation_count"]) + 1
    # Keep parameter/unit/datum definitions exact and deterministic; no conversion or merging occurs.
    for station in sites.values():
        station["measurement_definitions"] = []
        station["date_start"] = None
        station["date_end"] = None
    for station_id in series:
        series[station_id].sort(key=lambda row: (str(row["date"]), str(row["parameter_code"])))
        unique = {(str(r["parameter_code"]), str(r["unit"]), str(r["vertical_datum"])) for r in series[station_id]}
        sites[station_id]["measurement_definitions"] = [{"parameter_code": code, "unit": unit, "vertical_datum": datum} for code, unit, datum in sorted(unique)]
        sites[station_id]["date_start"] = min(str(r["date"]) for r in series[station_id])
        sites[station_id]["date_end"] = max(str(r["date"]) for r in series[station_id])
    for station_id, rows in series.items():
        # Attach parameter labels from the source CSV value names; retain codes for traceability.
        labels = {"72019": "Depth to water level, feet below land surface", "62610": "Groundwater level above NGVD 1929, feet", "62611": "Groundwater level above NAVD 1988, feet"}
        for row in rows:
            row["parameter_description"] = labels.get(str(row["parameter_code"]), "Parameter description in source metadata export")
    payload = {
        "source_file": str(args.input.resolve()), "source_provider": "USGS field measurements export",
        "study_rectangle_wgs84": BOUNDS, "source_rows_scanned": rows_seen,
        "observation_count_in_rectangle": sum(len(v) for v in series.values()),
        "station_count": len(sites), "processing_rule": "Filter source measurement coordinates to documented Phoenix metro rectangle; preserve each source value, parameter code, unit, datum, reading type, approval status, qualifier and method; no interpolation or conversion.",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "stations": sorted(sites.values(), key=lambda row: str(row["station_id"])),
        "observations": series,
    }
    out = args.output_dir / "phoenix_groundwater.json"
    out.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ["source_rows_scanned", "observation_count_in_rectangle", "station_count", "created_utc"]}, indent=2))


if __name__ == "__main__":
    main()
