#!/usr/bin/env python3
"""
Fetch locality names inside the KML polygon using Google Places Aggregate API,
then resolve names + locations via Place Details, then driving distance/duration from Bowral.
Input: myMap.kml. Output: myMap.xlsx (Locality, Driving distance, Driving duration in minutes).
"""
from __future__ import annotations

import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from openpyxl import Workbook

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GOOGLE_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
KML_PATH = Path(__file__).parent / "myMap.kml"
OUT_XLSX = Path(__file__).parent / "myMap.xlsx"
ORIGIN = "Bowral, NSW, Australia"
AGGREGATE_URL = "https://areainsights.googleapis.com/v1:computeInsights"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places"
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
DELAY_PLACE_DETAILS = 0.05
BATCH_SIZE = 25


def parse_kml_polygon(path: Path) -> list[tuple[float, float]]:
    """Return list of (lon, lat) from KML <coordinates>."""
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    tree = ET.parse(path)
    root = tree.getroot()
    coords_el = root.find(".//kml:coordinates", ns)
    if coords_el is None or coords_el.text is None:
        raise ValueError("No <coordinates> in KML")
    points = []
    for part in re.split(r"\s+", coords_el.text.strip()):
        part = part.strip()
        if not part:
            continue
        toks = part.split(",")
        if len(toks) >= 2:
            lon, lat = float(toks[0]), float(toks[1])
            points.append((lon, lat))
    return points


def geocode_address(address: str) -> tuple[float, float] | None:
    r = requests.get(GEOCODE_URL, params={"address": address, "key": GOOGLE_API_KEY}, timeout=10)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    loc = data["results"][0]["geometry"]["location"]
    return (loc["lat"], loc["lng"])


def distance_matrix_batch(
    origin_lat: float, origin_lng: float,
    dests: list[tuple[float, float]],
) -> list[tuple[str, int | None]]:
    """Return list of (distance_text, duration_minutes) for each destination."""
    origin = f"{origin_lat},{origin_lng}"
    destinations = "|".join(f"{lat},{lng}" for lat, lng in dests)
    r = requests.get(
        DISTANCE_MATRIX_URL,
        params={"origins": origin, "destinations": destinations, "mode": "driving", "key": GOOGLE_API_KEY},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "OK":
        return [("", None)] * len(dests)
    rows = data.get("rows", [])
    if not rows:
        return [("", None)] * len(dests)
    out = []
    for el in rows[0].get("elements", []):
        if el.get("status") == "OK":
            dist = el.get("distance", {}).get("text", "")
            secs = el.get("duration", {}).get("value")
            mins = round(secs / 60) if secs is not None else None
            out.append((dist, mins))
        else:
            out.append(("", None))
    return out


def main() -> None:
    if not GOOGLE_API_KEY:
        print("Set GOOGLE_MAPS_API_KEY in .env or environment.")
        return

    print("Parsing KML...")
    points = parse_kml_polygon(KML_PATH)
    # Google polygon: array of { latitude, longitude }; first and last must be identical
    coordinates = [{"latitude": lat, "longitude": lon} for lon, lat in points]
    if coordinates and (coordinates[0]["latitude"] != coordinates[-1]["latitude"] or coordinates[0]["longitude"] != coordinates[-1]["longitude"]):
        coordinates.append(coordinates[0])

    body = {
        "insights": ["INSIGHT_PLACES"],
        "filter": {
            "locationFilter": {
                "customArea": {
                    "polygon": {"coordinates": coordinates},
                }
            },
            "typeFilter": {"includedTypes": ["locality"]},
        },
    }

    print("Calling Places Aggregate API (localities in polygon)...")
    print("This can take a minute or so, depending on how big your map boundary is.")
    r = requests.post(
        AGGREGATE_URL,
        headers={"X-Goog-Api-Key": GOOGLE_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    place_resources = data.get("placeInsights") or []
    if not place_resources:
        print("No place insights returned. Response:", data)
        return
    place_ids = [p.get("place", "").replace("places/", "") for p in place_resources if p.get("place")]
    place_ids = [pid for pid in place_ids if pid]
    print(f"Got {len(place_ids)} place IDs. Resolving names and locations...")

    localities: list[tuple[str, float, float]] = []  # (name, lat, lng)
    for i, place_id in enumerate(place_ids):
        time.sleep(DELAY_PLACE_DETAILS)
        resp = requests.get(
            f"{PLACE_DETAILS_URL}/{place_id}",
            headers={
                "X-Goog-Api-Key": GOOGLE_API_KEY,
                "X-Goog-FieldMask": "displayName,location",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            localities.append((f"(place_id: {place_id})", 0.0, 0.0))
            continue
        j = resp.json()
        display = j.get("displayName", {}) or {}
        name = (display.get("text") or "").strip() or f"(place_id: {place_id})"
        loc = j.get("location") or {}
        lat = loc.get("latitude")
        lng = loc.get("longitude")
        if lat is None or lng is None:
            localities.append((name, 0.0, 0.0))
        else:
            localities.append((name, float(lat), float(lng)))
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(place_ids)}")

    localities.sort(key=lambda x: x[0].lower())

    print("Geocoding origin (Bowral)...")
    origin_ll = geocode_address(ORIGIN)
    if not origin_ll:
        print("Could not geocode Bowral. Skipping distance matrix.")
    else:
        origin_lat, origin_lng = origin_ll
        print("Fetching driving distances from Bowral...")
        results: list[tuple[str, str, int | None]] = []
        for i in range(0, len(localities), BATCH_SIZE):
            batch = localities[i : i + BATCH_SIZE]
            dests = [(lat, lng) for _, lat, lng in batch]
            dist_mins = distance_matrix_batch(origin_lat, origin_lng, dests)
            for (name, _, _), (dist, mins) in zip(batch, dist_mins):
                results.append((name, dist, mins))
            time.sleep(0.2)
            print(f"  Batch {i // BATCH_SIZE + 1}/{(len(localities) + BATCH_SIZE - 1) // BATCH_SIZE} done.")

        wb = Workbook()
        ws = wb.active
        ws.title = "Localities"
        ws.append(["Locality", "Driving distance", "Driving duration (mins)"])
        for name, dist, mins in results:
            ws.append([name, dist, mins if mins is not None else ""])
        wb.save(OUT_XLSX)
        print(f"Wrote {len(results)} rows to {OUT_XLSX}")


if __name__ == "__main__":
    main()
