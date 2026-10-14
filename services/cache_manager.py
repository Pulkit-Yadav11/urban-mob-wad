"""
cache_manager.py
Disk cache for Mumbai road/zone data.
"""
import os
import json
import geopandas as gpd

CACHE_DIR = "cache"

def _path(city: str, kind: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{city.lower()}_{kind}")

def save_roads(city: str, geojson: dict):
    with open(_path(city, "roads.json"), "w") as f:
        json.dump(geojson, f)

def load_roads(city: str) -> dict | None:
    p = _path(city, "roads.json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None

def roads_cached(city: str) -> bool:
    return os.path.exists(_path(city, "roads.json"))

def save_zones(city: str, zones_gdf: gpd.GeoDataFrame):
    zones_gdf.to_file(_path(city, "zones.geojson"), driver="GeoJSON")

def load_zones(city: str) -> gpd.GeoDataFrame | None:
    p = _path(city, "zones.geojson")
    if os.path.exists(p):
        return gpd.read_file(p)
    return None

def zones_cached(city: str) -> bool:
    return os.path.exists(_path(city, "zones.geojson"))

def save_analyzed(city: str, zones_gdf: gpd.GeoDataFrame):
    zones_gdf.to_file(_path(city, "analyzed.geojson"), driver="GeoJSON")

def load_analyzed(city: str) -> gpd.GeoDataFrame | None:
    p = _path(city, "analyzed.geojson")
    if os.path.exists(p):
        return gpd.read_file(p)
    return None

def analyzed_cached(city: str) -> bool:
    return os.path.exists(_path(city, "analyzed.geojson"))

def clear_city_cache(city: str):
    for kind in ["roads.json", "zones.geojson", "analyzed.geojson"]:
        p = _path(city, kind)
        if os.path.exists(p):
            os.remove(p)

def cache_status() -> dict:
    return {
        "Mumbai": {
            "roads":    roads_cached("Mumbai"),
            "zones":    zones_cached("Mumbai"),
            "analyzed": analyzed_cached("Mumbai"),
        }
    }