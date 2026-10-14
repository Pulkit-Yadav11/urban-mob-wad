"""
zone_builder.py
Orchestrates the full pipeline: fetch → zones → analyze → cache.
Supports variable zone granularity via target_cells.
"""
import os
import hashlib
import json as _json
import geopandas as gpd
from typing import Callable

from services.data_loader import get_city_boundary, fetch_roads_overpass, INDIAN_CITIES
from services.zone_creator import create_road_based_zones, cluster_zones
from services.analyzer import simulate_demand
import services.cache_manager as cm

CITY = "Mumbai"

def build_full_pipeline(
    target_cells: int = 100,
    use_clustering: bool = False,
    n_clusters: int = 50,
    force_refresh: bool = False,
    on_progress: Callable[[int, str], None] = None,
) -> tuple:
    """
    Full pipeline for Mumbai. Returns (zones_gdf, roads_geojson).
    target_cells controls zone granularity.
    """
    def prog(pct, msg):
        if on_progress:
            on_progress(pct, msg)

    city_info = INDIAN_CITIES[CITY]
    bbox      = city_info["bbox"]

    # Cache invalidation: if bbox or target_cells changed, force rebuild
    cache_key  = f"{bbox}_{target_cells}"
    bbox_hash  = hashlib.md5(cache_key.encode()).hexdigest()[:8]
    stamp_file = os.path.join("cache", f"mumbai_bbox_{target_cells}.txt")
    os.makedirs("cache", exist_ok=True)

    stored_hash = ""
    if os.path.exists(stamp_file):
        with open(stamp_file) as f:
            stored_hash = f.read().strip()
    if stored_hash != bbox_hash:
        cm.clear_city_cache(CITY)
        with open(stamp_file, "w") as f:
            f.write(bbox_hash)
        force_refresh = True

    # Step 1: Roads
    if not force_refresh and cm.roads_cached(CITY):
        prog(20, "Roads loaded from cache")
        roads_geojson = cm.load_roads(CITY)
    else:
        prog(10, "Fetching roads from Overpass API...")
        roads_geojson = fetch_roads_overpass(CITY)
        cm.save_roads(CITY, roads_geojson)
        prog(30, f"Roads fetched — {len(roads_geojson['features'])} segments")

    # Step 2: Base zones
    if not force_refresh and cm.zones_cached(CITY):
        prog(50, "Base zones loaded from cache")
        base_zones = cm.load_zones(CITY)
    else:
        prog(40, "Building zones from road network...")
        base_zones = create_road_based_zones(CITY, bbox, target_cells=target_cells)
        cm.save_zones(CITY, base_zones)
        prog(60, f"{len(base_zones)} base zones built")

    # Step 3: Clustering
    if use_clustering:
        prog(70, f"Merging into {n_clusters} neighbourhoods...")
        zones = cluster_zones(base_zones, n_clusters=n_clusters)
    else:
        zones = base_zones.copy()

    # Step 4: Demand simulation
    if not force_refresh and cm.analyzed_cached(CITY):
        prog(90, "Demand data loaded from cache")
        zones = cm.load_analyzed(CITY)
    else:
        prog(85, "Simulating travel demand...")
        zones = simulate_demand(zones, city_name=CITY)
        prog(95, "Saving results...")
        cm.save_analyzed(CITY, zones)

    prog(100, "Done!")
    return zones, roads_geojson