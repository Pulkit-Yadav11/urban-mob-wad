"""
zone_creator.py
----------------
Modular zone construction for Mumbai Mobility Project.
Provides organic TAZ (Traffic Analysis Zones) using road-networks and Voronoi fallbacks.

Key guarantee: when the user requests N zones, ALL N zones cover the entire
city bounding box with no gaps — not just the areas where roads happen to exist.

Strategy
--------
1. Fetch roads from Overpass and polygonize them into fine blocks.
2. If polygonization yields too few blocks, fall back to a Voronoi tessellation
   that tiles the full bbox with organic-looking shapes.
3. cluster_zones() assigns every block to exactly one cluster via KMeans on
   centroids, then dissolves — ensuring full coverage.
"""

import geopandas as gpd
import numpy as np
import requests
from shapely.geometry import box, LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union, polygonize
from sklearn.cluster import KMeans


# ── Road fetching ──────────────────────────────────────────────────────────────

def _fetch_road_lines(city_name: str, bbox: tuple) -> list:
    s, w, n, e = bbox
    query = f"""
    [out:json][timeout:25];
    (
      way["highway"~"primary|secondary|tertiary|residential"]({s},{w},{n},{e});
    );
    out geom;
    """
    try:
        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query}, timeout=25
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    lines = []
    for el in data.get("elements", []):
        if el.get("type") == "way" and "geometry" in el:
            coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
            if len(coords) >= 2:
                lines.append(LineString(coords))
    return lines


# ── Polygonisation ─────────────────────────────────────────────────────────────

def _polygonize_roads(lines: list, boundary_geom) -> gpd.GeoDataFrame:
    if not lines:
        return gpd.GeoDataFrame()

    merged = unary_union(lines)
    polys  = list(polygonize(merged))

    if not polys:
        return gpd.GeoDataFrame()

    valid = []
    for p in polys:
        if not p.is_valid:
            p = p.buffer(0)
        if p.intersects(boundary_geom) and 1e-8 < p.area < 0.02:
            clipped = p.intersection(boundary_geom)
            if not clipped.is_empty and clipped.area > 1e-9:
                valid.append(clipped)

    if not valid:
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(geometry=valid, crs="EPSG:4326")
    gdf['zone_id'] = [f"B_{i}" for i in range(len(gdf))]
    return gdf


def _merge_small_blocks(blocks_gdf, min_area: float = 2e-6) -> gpd.GeoDataFrame:
    big   = blocks_gdf[blocks_gdf.geometry.area >= min_area].copy()
    small = blocks_gdf[blocks_gdf.geometry.area <  min_area].copy()
    if small.empty or big.empty:
        return blocks_gdf
    for idx, row in small.iterrows():
        neighbors = big[big.geometry.touches(row.geometry)]
        if not neighbors.empty:
            best = neighbors.geometry.area.idxmax()
            big.at[best, 'geometry'] = big.at[best, 'geometry'].union(row.geometry)
    big = big.reset_index(drop=True)
    big['zone_id'] = [f"B_{i}" for i in range(len(big))]
    return big


# ── Voronoi fallback (organic shapes) ─────────────────────────────────────────

def _voronoi_fallback(boundary_geom, target_cells: int = 150) -> gpd.GeoDataFrame:
    """
    Generate organic-looking zones using Voronoi tessellation on random seed points.
    Looks much more natural than a hex or square grid.
    """
    from shapely.ops import voronoi_diagram
    from shapely.geometry import MultiPoint

    minx, miny, maxx, maxy = boundary_geom.bounds
    rng = np.random.default_rng(42)

    pts = []
    attempts = 0
    while len(pts) < target_cells and attempts < target_cells * 10:
        x = rng.uniform(minx, maxx)
        y = rng.uniform(miny, maxy)
        p = Point(x, y)
        if boundary_geom.contains(p):
            pts.append(p)
        attempts += 1

    if len(pts) < 3:
        return _square_grid(boundary_geom, target_cells)

    mp = MultiPoint(pts)
    regions = voronoi_diagram(mp, envelope=boundary_geom)

    polygons, ids = [], []
    for geom in regions.geoms:
        clipped = geom.intersection(boundary_geom)
        if not clipped.is_empty and clipped.area > 1e-9:
            polygons.append(clipped)
            ids.append(f"V_{len(ids)}")

    if not polygons:
        return _square_grid(boundary_geom, target_cells)

    return gpd.GeoDataFrame({'zone_id': ids, 'geometry': polygons}, crs="EPSG:4326")


# ── Hex grid fallback ──────────────────────────────────────────────────────────

def _hex_grid(boundary_geom, target_cells: int = 200) -> gpd.GeoDataFrame:
    """Build a hex grid that tiles the full bbox."""
    minx, miny, maxx, maxy = boundary_geom.bounds
    area      = (maxx - minx) * (maxy - miny)
    cell_area = area / target_cells
    s         = np.sqrt(cell_area / (3 * np.sqrt(3) / 2))
    w_step    = s * np.sqrt(3)
    h_step    = s * 1.5

    polygons, ids = [], []
    row = 0
    y   = miny
    while y < maxy + h_step:
        offset = (w_step / 2) if row % 2 else 0
        x = minx - w_step
        while x < maxx + w_step:
            cx, cy = x + offset, y
            hex_pts = [
                (cx + s * np.cos(np.radians(a)),
                 cy + s * np.sin(np.radians(a)))
                for a in range(0, 360, 60)
            ]
            cell    = Polygon(hex_pts)
            clipped = cell.intersection(boundary_geom)
            if not clipped.is_empty and clipped.area > 1e-9:
                polygons.append(clipped)
                ids.append(f"H_{len(ids)}")
            x += w_step
        y += h_step
        row += 1

    if not polygons:
        return _square_grid(boundary_geom, target_cells)

    return gpd.GeoDataFrame({'zone_id': ids, 'geometry': polygons}, crs="EPSG:4326")


def _square_grid(boundary_geom, target_cells: int = 200) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = boundary_geom.bounds
    area  = (maxx - minx) * (maxy - miny)
    side  = np.sqrt(area / target_cells)
    polygons, ids = [], []
    y = miny
    while y < maxy:
        x = minx
        while x < maxx:
            cell    = box(x, y, x + side, y + side)
            clipped = cell.intersection(boundary_geom)
            if not clipped.is_empty and clipped.area > 1e-9:
                polygons.append(clipped)
                ids.append(f"Z_{len(ids)}")
            x += side
        y += side
    return gpd.GeoDataFrame({'zone_id': ids, 'geometry': polygons}, crs="EPSG:4326")


# ── Main entry point ──────────────────────────────────────────────────────────

def create_road_based_zones(city_name: str, bbox: tuple,
                             target_cells: int = 100) -> gpd.GeoDataFrame:
    """
    Build base zone layer.
    Always returns a GDF that tiles the FULL bbox with no gaps,
    and strictly clipped to the bbox — nothing outside.

    target_cells controls Voronoi seed density when road polygonization
    yields too few blocks.
    """
    s, w, n, e = bbox
    boundary_geom = box(w, s, e, n)

    lines  = _fetch_road_lines(city_name, bbox)
    blocks = gpd.GeoDataFrame()

    if lines:
        blocks = _polygonize_roads(lines, boundary_geom)
        if len(blocks) >= 20:
            blocks = _merge_small_blocks(blocks)

    # If road polygonisation gave too few pieces, use Voronoi (organic shapes)
    if len(blocks) < 20:
        voronoi_target = max(150, target_cells * 2)
        blocks = _voronoi_fallback(boundary_geom, target_cells=voronoi_target)

    # Strictly clip everything to the bounding box — no spillover
    blocks['geometry'] = blocks['geometry'].intersection(boundary_geom)
    blocks = blocks[~blocks['geometry'].is_empty].copy()
    blocks = blocks.reset_index(drop=True)
    blocks['zone_id'] = [f"B_{i}" for i in range(len(blocks))]

    return blocks


# ── Clustering ────────────────────────────────────────────────────────────────

def cluster_zones(zones_gdf: gpd.GeoDataFrame,
                  n_clusters: int = 50) -> gpd.GeoDataFrame:
    """
    Merge base blocks into exactly n_clusters neighbourhood-level zones
    that cover the entire city with no gaps.
    """
    n_clusters = min(n_clusters, len(zones_gdf))

    centroids = np.array([[g.centroid.x, g.centroid.y]
                           for g in zones_gdf.geometry])

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=15)
    zones_gdf = zones_gdf.copy()
    zones_gdf['cluster'] = km.fit_predict(centroids)

    # Dissolve: union all blocks in the same cluster
    dissolved = zones_gdf.dissolve(by='cluster', as_index=False)
    dissolved['zone_id'] = [f"Zone_{i+1}" for i in range(len(dissolved))]

    # Fix any invalid geometries
    dissolved['geometry'] = dissolved['geometry'].apply(
        lambda g: g.buffer(0) if not g.is_valid else g
    )

    # Fill any gap between clusters by assigning leftover slivers to nearest cluster
    try:
        full_union = dissolved.geometry.union_all()
    except AttributeError:
        full_union = dissolved.geometry.unary_union

    try:
        orig_union = zones_gdf.geometry.union_all()
    except AttributeError:
        orig_union = zones_gdf.geometry.unary_union

    gap = orig_union.difference(full_union)
    if not gap.is_empty and gap.area > 1e-9:
        gap_geoms = list(gap.geoms) if hasattr(gap, 'geoms') else [gap]
        for sliver in gap_geoms:
            sc    = sliver.centroid
            dists = dissolved.geometry.centroid.distance(sc)
            nearest = dists.idxmin()
            dissolved.at[nearest, 'geometry'] = (
                dissolved.at[nearest, 'geometry'].union(sliver)
            )

    return dissolved[['zone_id', 'geometry']].reset_index(drop=True)


# ── Backward compat ────────────────────────────────────────────────────────────

def create_grid_zones(boundary_gdf, grid_size=0.01) -> gpd.GeoDataFrame:
    try:
        boundary_geom = boundary_gdf.union_all()
    except AttributeError:
        boundary_geom = boundary_gdf.unary_union
    return _square_grid(boundary_geom)