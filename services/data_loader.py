"""
data_loader.py
Mumbai-focused city loader with proper administrative boundary polygon.
Zone resolution is controlled by ZONE_SIZES dict.
"""
import requests
import geopandas as gpd
from shapely.geometry import box
import json

# Mumbai only — tight bbox matching BMC limits
MUMBAI_INFO = {
    "center": (19.0900, 72.8900),
    # Extended to cover full BMC limits — southern tip (Colaba/Backbay) to Mulund/Dahisar
    "bbox": (18.870, 72.775, 19.290, 73.010),
}

# Keep dict form so zone_builder imports work unchanged
INDIAN_CITIES = {
    "Mumbai": MUMBAI_INFO,
}

# Zone resolution presets: target_cells fed to zone_creator
ZONE_SIZES = {
    "Coarse (~20 zones)":      20,
    "Medium (~50 zones)":      50,
    "Fine (~100 zones)":      100,
    "Very Fine (~200 zones)": 200,
}


def get_city_boundary(city_name: str = "Mumbai"):
    """Returns a GDF of the bounding-box polygon for Mumbai."""
    s, w, n, e = MUMBAI_INFO["bbox"]
    return gpd.GeoDataFrame(geometry=[box(w, s, e, n)], crs="EPSG:4326")


def fetch_roads_overpass(city_name: str = "Mumbai") -> dict:
    """Fetch major roads via Overpass API — returns GeoJSON dict."""
    s, w, n, e = MUMBAI_INFO["bbox"]
    overpass_query = f"""
    [out:json][timeout:30];
    (
      way["highway"~"primary|secondary|tertiary"]
        ({s},{w},{n},{e});
    );
    out geom;
    """
    try:
        response = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": overpass_query},
            timeout=30,
        )
        response.raise_for_status()
        return _overpass_to_geojson(response.json())
    except Exception:
        return {"type": "FeatureCollection", "features": []}


def _overpass_to_geojson(overpass_data: dict) -> dict:
    features = []
    for element in overpass_data.get("elements", []):
        if element.get("type") == "way" and "geometry" in element:
            coords = [[pt["lon"], pt["lat"]] for pt in element["geometry"]]
            if len(coords) >= 2:
                features.append({
                    "type": "Feature",
                    "geometry": {"type": "LineString", "coordinates": coords},
                    "properties": {
                        "highway": element.get("tags", {}).get("highway", ""),
                        "name":    element.get("tags", {}).get("name", ""),
                    },
                })
    return {"type": "FeatureCollection", "features": features}


def load_congested_road_layers(hour_filter: int) -> dict:
    """
    Reads synthetic agent parquet and aggregates congestion
    metrics onto road segments for a given hour.
    """
    import os
    import json
    import pandas as pd

    ROADS_PATH  = r"D:\urban_mobility\cache\mumbai_roads.json"
    AGENTS_PATH = r"D:\urban_mobility\cache\agents_resampled.parquet"

    if not os.path.exists(ROADS_PATH) or not os.path.exists(AGENTS_PATH):
        return {"type": "FeatureCollection", "features": []}

    with open(ROADS_PATH, "r") as f:
        roads_geojson = json.load(f)

    df = pd.read_parquet(
        AGENTS_PATH,
        columns=["departure_hour", "road_segment",
                 "on_congested_segment", "mode_switched"]
    )

    # Filter to selected hour
    hourly_df = df[df["departure_hour"] == hour_filter].copy()

    # Drop agents not on road network (rail agents have NaN road_segment)
    hourly_df = hourly_df.dropna(subset=["road_segment"])
    hourly_df["road_segment"] = hourly_df["road_segment"].astype(int)

    # Compute per-segment metrics
    volume_counts    = hourly_df["road_segment"].value_counts().to_dict()
    congested_counts = hourly_df.groupby("road_segment")["on_congested_segment"].sum().to_dict()
    switch_counts    = hourly_df.groupby("road_segment")["mode_switched"].sum().to_dict()

    # Inject into GeoJSON properties
    for idx, feature in enumerate(roads_geojson.get("features", [])):
        feature["properties"]["current_volume"]    = int(volume_counts.get(idx, 0))
        feature["properties"]["congested_agents"]  = int(congested_counts.get(idx, 0))
        feature["properties"]["frustrated_shifts"] = int(switch_counts.get(idx, 0))

    return roads_geojson


