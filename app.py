"""
app.py — Mumbai Urban Mobility Platform
Focused on Mumbai only. Dark/light theme switching, lat/lon display,
zone size control, and realistic travel demand data.
"""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os


from services.data_loader import INDIAN_CITIES, ZONE_SIZES, load_congested_road_layers
from services.zone_builder import build_full_pipeline
from services.analyzer import get_summary_stats, get_hourly_profile
from services.map_component import render_map
import services.cache_manager as cm

# Put this at top level, after imports, before any sidebar code
@st.cache_data(ttl=60)
def get_hourly_roads(hour: int) -> dict:
    return load_congested_road_layers(hour)

#  Page config 
st.set_page_config(
    page_title="Mumbai Mobility Platform",
    layout="wide",
    page_icon="◈",
    initial_sidebar_state="expanded",
)

#  Theme init 
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False

# Force sidebar open — Streamlit sometimes collapses it on rerun
st.markdown("""
<script>
(function() {
    function openSidebar() {
        // Click the collapsed control button if sidebar is closed
        var btn = document.querySelector('[data-testid="stSidebarCollapsedControl"] button');
        if (btn) { btn.click(); return; }
        // Also try removing the collapsed attribute from the sidebar
        var sb = document.querySelector('[data-testid="stSidebar"]');
        if (sb) {
            sb.removeAttribute('aria-expanded');
            sb.style.transform = 'none';
            sb.style.visibility = 'visible';
        }
    }
    // Try immediately and after a short delay (after Streamlit renders)
    setTimeout(openSidebar, 100);
    setTimeout(openSidebar, 500);
})();
</script>
""", unsafe_allow_html=True)

DM = st.session_state.dark_mode

# Design tokens 
if DM:
    BG      = "#0F0F14"
    SURFACE = "#16161C"
    CARD    = "#1C1C24"
    BORDER  = "#2A2A38"
    TEXT1   = "#E8E4DC"
    TEXT2   = "#B0ACA4"
    TEXT3   = "#7A7672"
    MUTED   = "#52504E"
    ACCENT  = "#E8E4DC"
else:
    BG      = "#EDEAE3"
    SURFACE = "#F5F2EC"
    CARD    = "#FFFFFF"
    BORDER  = "#D6D1C7"
    TEXT1   = "#1A1814"
    TEXT2   = "#4A4540"
    TEXT3   = "#6B6560"
    MUTED   = "#9E9891"
    ACCENT  = "#1A1814"

C_GREEN = "#4A7C59"
C_AMBER = "#C47B3A"
C_RED   = "#8B2A36"

# Global CSS 
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&family=DM+Mono:wght@400;500&display=swap');

:root {{
    --bg:      {BG};
    --surface: {SURFACE};
    --card:    {CARD};
    --border:  {BORDER};
    --text-1:  {TEXT1};
    --text-2:  {TEXT2};
    --text-3:  {TEXT3};
    --muted:   {MUTED};
    --accent:  {ACCENT};
    --green:   {C_GREEN};
    --amber:   {C_AMBER};
    --red:     {C_RED};
    --radius:  10px;
    --shadow:  0 1px 3px rgba(0,0,0,0.12), 0 4px 20px rgba(0,0,0,0.08);
}}

.stApp {{
    background: var(--bg) !important;
    background-image:
        linear-gradient(rgba(128,128,128,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(128,128,128,0.04) 1px, transparent 1px) !important;
    background-size: 48px 48px !important;
    font-family: 'DM Sans', sans-serif !important;
}}
#MainMenu, footer, header {{ visibility: hidden !important; }}
.stDeployButton {{ display: none !important; }}
.main .block-container {{
    padding: 1.5rem 2.5rem 3rem 2.5rem !important;
    max-width: 1500px !important;
}}
* {{ color: var(--text-1); }}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
    min-width: 280px !important;
    max-width: 280px !important;
    transform: none !important;
    visibility: visible !important;
    display: block !important;
}}
/* Force the sidebar open — hide the collapse arrow entirely */
[data-testid="stSidebarCollapseButton"] {{
    display: none !important;
}}
/* Show the expand arrow when sidebar IS collapsed, styled visibly */
[data-testid="stSidebarCollapsedControl"] {{
    visibility: visible !important;
    opacity: 1 !important;
    background: {CARD} !important;
    border: 2px solid {BORDER} !important;
    border-radius: 8px !important;
    width: 36px !important;
    height: 36px !important;
    top: 1rem !important;
}}
[data-testid="stSidebarCollapsedControl"] button {{
    background: {CARD} !important;
    color: {TEXT1} !important;
}}
[data-testid="stSidebarCollapsedControl"] svg {{
    stroke: {TEXT1} !important;
    fill: {TEXT1} !important;
}}
[data-testid="stSidebar"] > div:first-child {{ padding: 1.5rem 1.25rem !important; }}
[data-testid="stSidebar"] *, [data-testid="stSidebar"] p,
[data-testid="stSidebar"] span, [data-testid="stSidebar"] div {{
    color: var(--text-1) !important;
}}
[data-testid="stSidebar"] label {{
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-2) !important;
    font-weight: 500 !important;
}}
[data-testid="stSidebar"] strong {{
    font-family: 'DM Mono', monospace !important;
    font-size: 10px !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--text-3) !important;
}}
[data-testid="stSidebar"] .stCheckbox p,
[data-testid="stSidebar"] .stCheckbox span {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
    color: var(--text-1) !important;
}}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-1) !important;
}}
[data-testid="stSelectbox"] span,
[data-testid="stSelectbox"] div,
[data-testid="stSelectbox"] input {{ color: var(--text-1) !important; }}
[data-baseweb="popover"] li, [data-baseweb="menu"] li span {{
    color: var(--text-1) !important;
    background: var(--card) !important;
}}

/* ── Slider ── */
[data-testid="stSlider"] [role="slider"] {{ background: var(--accent) !important; }}

/* ── Buttons ── */
.stButton > button {{
    background: {C_GREEN if DM else C_GREEN} !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.1em !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.5rem !important;
    transition: all 0.2s ease !important;
}}
/* Primary / Analyze button — always high contrast */
[data-testid="stSidebar"] .stButton > button {{
    background: {C_GREEN} !important;
    color: #FFFFFF !important;
    border: none !important;
}}
.stButton > button:hover {{
    opacity: 0.85 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(0,0,0,0.2) !important;
}}
/* Theme toggle ◑ button specifically */
[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] .stButton > button {{
    background: {CARD} !important;
    color: {TEXT1} !important;
    border: 1px solid {BORDER} !important;
    padding: 0.4rem 0.6rem !important;
    font-size: 14px !important;
}}

[data-testid="stDownloadButton"] > button {{
    background: var(--card) !important;
    color: var(--text-1) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    padding: 0.65rem 1.2rem !important;
}}

/* ── Metrics ── */
[data-testid="stMetric"] {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 1.25rem 1.5rem !important;
    box-shadow: var(--shadow) !important;
}}
[data-testid="stMetricLabel"] p,
[data-testid="stMetricLabel"] span,
[data-testid="stMetricLabel"] div {{
    font-family: 'DM Mono', monospace !important;
    font-size: 9px !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: var(--muted) !important;
}}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] div {{
    font-family: 'Instrument Serif', serif !important;
    font-size: 2.2rem !important;
    color: var(--text-1) !important;
    line-height: 1.1 !important;
}}

/* ── Progress ── */
[data-testid="stProgress"] > div > div > div {{ background: var(--accent) !important; }}
[data-testid="stProgress"] > div > div {{ background: var(--border) !important; border-radius: 4px !important; }}

/* ── Expander ── */
[data-testid="stExpander"] {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    box-shadow: var(--shadow) !important;
}}
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary span {{ color: var(--text-1) !important; }}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    border: 1px solid var(--border) !important;
    box-shadow: var(--shadow) !important;
}}
[data-testid="stDataFrame"] [data-testid="stDataFrameResizable"] {{
    background: var(--card) !important;
}}
/* Make dataframe text always visible */
[data-testid="stDataFrame"] .dvn-scroller * {{
    color: var(--text-1) !important;
}}
[data-testid="stDataFrame"] canvas {{
    background: var(--card) !important;
}}

/* ── Alert ── */
[data-testid="stAlert"] {{
    border-radius: var(--radius) !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
}}
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {{ color: var(--text-1) !important; font-size: 13px !important; }}

hr {{ border-color: var(--border) !important; margin: 1rem 0 !important; }}

/* ── Custom components ── */
.ump-header {{
    padding: 2.5rem 0 1.75rem 0;
    border-bottom: 1px solid {BORDER};
    margin-bottom: 1.75rem;
}}
.ump-eyebrow {{
    display: inline-flex; align-items: center; gap: 6px;
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 100px;
    padding: 4px 14px;
    font-family: 'DM Mono', monospace;
    font-size: 10px; letter-spacing: 0.14em; text-transform: uppercase;
    color: {TEXT3}; margin-bottom: 0.9rem;
}}
.ump-eyebrow::before {{ content: '●'; font-size: 6px; color: {C_GREEN}; }}
.ump-title {{
    font-family: 'Instrument Serif', serif;
    font-size: clamp(1.9rem, 3vw, 2.8rem);
    color: {TEXT1}; line-height: 1.1;
    letter-spacing: -0.02em; margin: 0 0 0.4rem 0;
}}
.ump-title em {{ font-style: italic; color: {TEXT3}; }}
.ump-sub {{ font-family: 'DM Sans', sans-serif; font-size: 13px; color: {MUTED}; }}

.ump-section {{
    display: flex; align-items: center; gap: 10px;
    margin: 1.5rem 0 0.9rem 0;
}}
.ump-sec-num {{ font-family: 'DM Mono', monospace; font-size: 10px; color: {MUTED}; }}
.ump-sec-title {{
    font-family: 'DM Mono', monospace; font-size: 10px; font-weight: 600;
    color: {TEXT2}; letter-spacing: 0.12em; text-transform: uppercase; white-space: nowrap;
}}
.ump-sec-line {{ flex: 1; height: 1px; background: {BORDER}; }}

.ump-card {{
    background: {CARD}; border: 1px solid {BORDER};
    border-radius: var(--radius); padding: 1.25rem; box-shadow: var(--shadow);
}}
.ump-card-label {{
    font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 0.14em;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 0.65rem;
    padding-bottom: 0.5rem; border-bottom: 1px solid {BORDER};
}}
.ump-card * {{ color: {TEXT1}; }}

.map-bar {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.65rem 1rem; border-bottom: 1px solid {BORDER};
    background: {SURFACE}; border-radius: var(--radius) var(--radius) 0 0;
}}
.map-city {{ font-family:'DM Mono',monospace; font-size:10px; letter-spacing:0.12em;
             text-transform:uppercase; color:{TEXT2}; }}
.map-legend {{ display:flex; gap:14px; }}
.map-legend span {{ font-family:'DM Mono',monospace; font-size:10px; color:{TEXT3};
                    display:flex; align-items:center; gap:5px; }}
.leg-dot {{ display:inline-block; width:8px; height:8px; border-radius:2px; }}

.ump-info-card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:var(--radius);
                  padding:2rem; box-shadow:var(--shadow); }}
.ump-info-num {{ font-family:'DM Mono',monospace; font-size:11px; color:{MUTED}; margin-bottom:0.5rem; }}
.ump-info-title {{ font-family:'Instrument Serif',serif; font-size:1.3rem; color:{TEXT1}; margin-bottom:0.5rem; }}
.ump-info-body {{ font-family:'DM Sans',sans-serif; font-size:13px; color:{TEXT3}; line-height:1.6; }}

.sb-logo {{ display:flex; align-items:center; gap:10px; margin-bottom:1.5rem;
            padding-bottom:1.25rem; border-bottom:1px solid {BORDER}; }}
.sb-icon {{ width:30px; height:30px; background:{ACCENT}; border-radius:7px;
            display:flex; align-items:center; justify-content:center;
            color:{BG}; font-size:13px; flex-shrink:0; }}
.sb-name {{ font-family:'DM Sans',sans-serif; font-size:14px; font-weight:600; color:{TEXT1}; }}

.coord-badge {{
    display:inline-flex; gap:18px;
    background:{CARD}; border:1px solid {BORDER};
    border-radius:8px; padding:6px 14px;
    font-family:'DM Mono',monospace; font-size:11px;
    color:{TEXT3};
}}
.coord-badge span {{ color:{TEXT1}; font-weight:500; }}
</style>
""", unsafe_allow_html=True)


plt.rcParams.update({
    'figure.facecolor': CARD,
    'axes.facecolor':   CARD,
    'axes.edgecolor':   BORDER,
    'axes.labelcolor':  TEXT3,
    'xtick.color':      MUTED,
    'ytick.color':      MUTED,
    'text.color':       TEXT1,
    'grid.color':       BORDER,
    'grid.linewidth':   0.6,
    'axes.spines.top':  False,
    'axes.spines.right':False,
    'axes.linewidth':   0.7,
    'font.family':      'monospace',
    'font.size':        8,
})

# Session state 
for key in ['zones', 'roads_geojson', 'loaded_zone_size']:
    if key not in st.session_state:
        st.session_state[key] = None

#  Sidebar 
with st.sidebar:
    st.markdown(f"""
    <div class="sb-logo">
        <div class="sb-icon">◈</div>
        <div class="sb-name">Mumbai Mobility</div>
    </div>
    """, unsafe_allow_html=True)

    # Theme toggle
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        st.markdown(f"<span style='font-family:DM Mono,monospace;font-size:10px;"
                    f"letter-spacing:0.12em;text-transform:uppercase;"
                    f"color:{TEXT2};'>Theme</span>", unsafe_allow_html=True)
    with col_t2:
        if st.button("◑", help="Toggle dark / light theme", use_container_width=True):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()

    st.divider()

    # Zone size
    st.markdown("**Zone Resolution**")
    zone_size_label = st.selectbox(
        "Zone Resolution",
        list(ZONE_SIZES.keys()),
        index=1,
        label_visibility="collapsed",
    )
    target_cells = ZONE_SIZES[zone_size_label]

    zone_help = {
        "Coarse (~20 zones)":      "Mumbai split into ~20 large areas (e.g. South Mumbai, Bandra, Andheri). Fast, good for city-wide overview.",
        "Medium (~50 zones)":      "~50 areas — roughly ward-level. Best balance of speed and detail.",
        "Fine (~100 zones)":       "~100 blocks — closer to neighbourhood-level. Good for spotting local hotspots.",
        "Very Fine (~200 zones)":  "~200 micro-zones for street-level detail. Slower build, most granular.",
    }
    st.markdown(f"""
    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:{TEXT2};
                margin:4px 0 10px 0;line-height:1.5;background:{SURFACE};
                border:1px solid {BORDER};border-radius:8px;padding:8px 10px;">
        {zone_help.get(zone_size_label, '')}
    </div>
    """, unsafe_allow_html=True)

    # Clustering
    st.markdown("**Merge into Neighbourhoods**")
    st.markdown(f"""
    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:{TEXT2};
                margin:2px 0 6px 0;line-height:1.5;">
        Groups the fine zones above into larger named neighbourhoods using spatial clustering (K-Means).
        Use this when you want fewer, more recognisable areas — like grouping 100 blocks into 15 neighbourhoods.
    </div>
    """, unsafe_allow_html=True)
    use_clustering = st.checkbox("Enable neighbourhood merging", value=False)
    n_clusters = None
    if use_clustering:
        st.markdown(f"""
        <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:{MUTED};margin-bottom:4px;">
            How many neighbourhoods to merge into:
        </div>""", unsafe_allow_html=True)
        n_clusters = st.slider("Number of Neighbourhoods", 5, 50, 20, label_visibility="collapsed")

    st.divider()

    st.markdown("**Temporal Playback**")
    selected_hour = st.slider(
        "Simulation Hour", min_value=0, max_value=23, value=9,
        format="%d:00", label_visibility="collapsed"
    )
    st.markdown(f"""
    <div style="font-family:'DM Mono',monospace;font-size:10px;color:{MUTED};
                margin-bottom:8px;">
        {'🌙 Late Night' if selected_hour < 6 else
         '🌅 Early Morning' if selected_hour < 8 else
         '🚦 Morning Peak' if selected_hour < 11 else
         '☀️ Midday' if selected_hour < 16 else
         '🚗 Evening Peak' if selected_hour < 20 else
         '🌆 Evening'} — {selected_hour:02d}:00
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    # Cache
    status = cm.cache_status().get("Mumbai", {})
    cached = status.get("roads") and status.get("zones")
    if cached:
        st.success("Cache ready — instant load")
        force_refresh = st.checkbox("Force re-fetch from API", value=False)
        if st.button("Clear Cache", use_container_width=True):
            cm.clear_city_cache("Mumbai")
            for f in ["cache/mumbai_bbox.txt"] + \
                      [f"cache/mumbai_bbox_{c}.txt" for c in ZONE_SIZES.values()]:
                if os.path.exists(f):
                    os.remove(f)
            st.session_state.zones = None
            st.session_state.loaded_zone_size = None
            st.rerun()
    else:
        st.info("First run fetches from Overpass API (~15 sec)")
        force_refresh = False

    st.divider()
    run_btn = st.button("Analyze Mumbai", type="primary", use_container_width=True)

    st.markdown(f"""
    <div style="margin-top:1.25rem;font-family:'DM Mono',monospace;font-size:10px;
                color:{MUTED};line-height:1.9;letter-spacing:0.04em;
                border-top:1px solid {BORDER};padding-top:1.1rem;">
        Data: OpenStreetMap + MMRDA<br>
        Demand: TomTom 2023 calibrated<br>
        Roads + zones cached to disk
    </div>
    """, unsafe_allow_html=True)

# Header 
theme_label = "Dark Mode" if DM else "Light Mode"
st.markdown(f"""
<div class="ump-header">
    <div class="ump-eyebrow">Mumbai Traffic Analysis Zones — {theme_label}</div>
    <h1 class="ump-title">Mumbai <em>Mobility</em> Platform</h1>
    <p class="ump-sub">OpenStreetMap · Overpass API · MMRDA Zones · TomTom Index 2023</p>
</div>
""", unsafe_allow_html=True)

#  Pipeline 
if run_btn:
    same_loaded = (
        st.session_state.zones is not None
        and st.session_state.loaded_zone_size == zone_size_label
        and not force_refresh
        and not use_clustering
    )
    if same_loaded:
        st.success(f"Mumbai — {len(st.session_state.zones)} zones (from session)")
    else:
        st.session_state.zones = None
        pb = st.progress(0, text="Starting analysis...")
        def on_progress(pct, msg):
            pb.progress(pct, text=msg)
        try:
            zones, roads_geojson = build_full_pipeline(
                target_cells=target_cells,
                use_clustering=use_clustering,
                n_clusters=n_clusters or 20,
                force_refresh=force_refresh,
                on_progress=on_progress,
            )
            st.session_state.zones             = zones
            st.session_state.roads_geojson     = roads_geojson
            st.session_state.loaded_zone_size  = zone_size_label
            os.makedirs("data/processed", exist_ok=True)
            zones.drop(columns='geometry').to_csv(
                "data/processed/mumbai_zones.csv", index=False)
            pb.empty()
            st.success(f"Mumbai — {len(zones)} zones loaded ({zone_size_label})")
        except Exception as e:
            pb.empty()
            st.error(f"Error: {e}")
            st.stop()

#  Dashboard 
if st.session_state.zones is not None:
    zones         = st.session_state.zones
    roads_geojson = get_hourly_roads(selected_hour)
    if not roads_geojson["features"]:
        roads_geojson = st.session_state.roads_geojson or {"type":"FeatureCollection","features":[]}
    stats         = get_summary_stats(zones)
    hourly        = get_hourly_profile("Mumbai")
    # Agent-driven KPI metrics
    AGENTS_PATH = r"D:\urban_mobility\cache\agents_resampled.parquet"
    if os.path.exists(AGENTS_PATH):
        agents_df = pd.read_parquet(
        AGENTS_PATH,
        columns=["departure_hour", "on_congested_segment",
             "mode_switched", "trip_dist_km"])
        
        hourly_slice = agents_df[agents_df["departure_hour"] == selected_hour]
        has_agents   = True
    else:
        has_agents = False

    low_t  = zones['demand'].quantile(0.33)
    high_t = zones['demand'].quantile(0.66)

    # 01 Overview 
    st.markdown(f"""
    <div class="ump-section">
        <span class="ump-sec-num">01</span>
        <span class="ump-sec-title">Overview</span>
        <div class="ump-sec-line"></div>
    </div>""", unsafe_allow_html=True)

    if has_agents:
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")
        m1.metric("Total Zones",            stats['total_zones'])
        m2.metric("Hourly Commuter Load",   f"{len(hourly_slice):,}")
        m3.metric("Gridlocked Agents",      f"{int(hourly_slice['on_congested_segment'].sum()):,}")
        m4.metric("Switched to Rail",       f"{int(hourly_slice['mode_switched'].sum()):,}")
        m5.metric("Avg Trip Distance",      f"{hourly_slice['trip_dist_km'].mean():.1f} km")
    else:
        m1, m2, m3, m4, m5 = st.columns(5, gap="small")
        m1.metric("Total Zones",            stats['total_zones'])
        m2.metric("Avg Demand (veh/hr)",    stats['avg_demand'])
        m3.metric("Peak Demand (veh/hr)",   stats['max_demand'])
        m4.metric("High-Demand Zones",      stats['high_demand_zones'])
        m5.metric("Avg Congestion (0–100)", f"{stats.get('avg_congestion','N/A')}")

    # Demand split bar
    cat   = zones['demand_category'].value_counts()
    total = len(zones)
    lp    = int(cat.get('Low',   0) / total * 100)
    mp    = int(cat.get('Medium',0) / total * 100)
    hp    = 100 - lp - mp

    # Mumbai center coords badge
    center = INDIAN_CITIES["Mumbai"]["center"]
    st.markdown(f"""
    <div style="margin-top:0.75rem;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
      <div class="coord-badge">
        Lat: <span>{center[0]}&deg; N</span>&nbsp;&nbsp;
        Lon: <span>{center[1]}&deg; E</span>&nbsp;&nbsp;
        Zone resolution: <span>{zone_size_label}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="ump-card" style="padding:1rem 1.4rem;margin-top:0.6rem;">
      <div class="ump-card-label">Demand Category Split — Mumbai (demand = estimated vehicles/hour crossing each zone)</div>
      <div style="display:flex;gap:0;border-radius:5px;overflow:hidden;height:9px;margin-bottom:9px;">
        <div style="width:{lp}%;background:{C_GREEN};"></div>
        <div style="width:{mp}%;background:{C_AMBER};"></div>
        <div style="width:{hp}%;background:{C_RED};"></div>
      </div>
      <div style="display:flex;gap:24px;">
        <span style="font-family:'DM Mono',monospace;font-size:10px;color:{C_GREEN};">
          <strong style="font-size:14px;color:{TEXT1};">{cat.get('Low',0)}</strong>&nbsp; Low ({lp}%)
        </span>
        <span style="font-family:'DM Mono',monospace;font-size:10px;color:{C_AMBER};">
          <strong style="font-size:14px;color:{TEXT1};">{cat.get('Medium',0)}</strong>&nbsp; Medium ({mp}%)
        </span>
        <span style="font-family:'DM Mono',monospace;font-size:10px;color:{C_RED};">
          <strong style="font-size:14px;color:{TEXT1};">{cat.get('High',0)}</strong>&nbsp; High ({hp}%)
        </span>
      </div>
    </div>""", unsafe_allow_html=True)

    #  02 Map & Analysis 
    st.markdown(f"""
    <div class="ump-section">
        <span class="ump-sec-num">02</span>
        <span class="ump-sec-title">Zone Map & Analysis</span>
        <div class="ump-sec-line"></div>
    </div>""", unsafe_allow_html=True)

    map_col, chart_col = st.columns([3, 2], gap="medium")

    with map_col:
        st.markdown(f"""
        <div style="background:{CARD};border:1px solid {BORDER};border-radius:10px;
                    overflow:hidden;box-shadow:var(--shadow);">
          <div class="map-bar">
            <span class="map-city">Mumbai · Zone Heatmap · {zone_size_label}</span>
            <div class="map-legend">
              <span><span class="leg-dot" style="background:{C_GREEN};"></span>Low</span>
              <span><span class="leg-dot" style="background:{C_AMBER};"></span>Medium</span>
              <span><span class="leg-dot" style="background:{C_RED};"></span>High</span>
            </div>
          </div>
        </div>""", unsafe_allow_html=True)

        zones_geojson = zones.__geo_interface__
        for i, feat in enumerate(zones_geojson['features']):
            row = zones.iloc[i]
            feat['properties'].update({
                'zone_id':          str(row.get('zone_id', f'Z_{i}')),
                'demand':           int(row['demand']),
                'demand_category':  str(row['demand_category']),
                'peak_hour':        str(row['peak_hour']),
                'land_use':         str(row['land_use']),
                'congestion_index': float(row.get('congestion_index', 0)),
                'centroid_lat':     float(row.get('centroid_lat', 0)),
                'centroid_lon':     float(row.get('centroid_lon', 0)),
            })
        render_map(
            zones_geojson, roads_geojson,
            center=INDIAN_CITIES["Mumbai"]["center"],
            height=500,
            dark_mode=DM,
            hour=selected_hour,
        )

    with chart_col:
        # Chart 1 — Demand histogram
        st.markdown(f'<div class="ump-card" style="margin-bottom:0.6rem;">', unsafe_allow_html=True)
        st.markdown('<div class="ump-card-label">Demand Distribution — Vehicles/Hour per Zone</div>', unsafe_allow_html=True)
        fig1, ax1 = plt.subplots(figsize=(5, 2.4))
        n, bins, patches = ax1.hist(zones['demand'], bins=20, edgecolor=CARD, linewidth=0.4)
        for patch, left in zip(patches, bins[:-1]):
            patch.set_facecolor(C_GREEN if left < low_t else (C_AMBER if left < high_t else C_RED))
        ax1.set_xlabel("Estimated Vehicles / Hour", labelpad=5)
        ax1.set_ylabel("No. of Zones", labelpad=5)
        ax1.yaxis.grid(True)
        ax1.set_axisbelow(True)
        # Annotate thresholds
        ax1.axvline(low_t,  color=C_GREEN, linewidth=0.8, linestyle=':', alpha=0.7)
        ax1.axvline(high_t, color=C_RED,   linewidth=0.8, linestyle=':', alpha=0.7)
        ax1.legend(handles=[
            mpatches.Patch(color=C_GREEN, label=f'Low  (<{int(low_t)})'),
            mpatches.Patch(color=C_AMBER, label=f'Medium'),
            mpatches.Patch(color=C_RED,   label=f'High (>{int(high_t)})'),
        ], fontsize=7, frameon=False, loc='upper right', labelcolor=TEXT3)
        plt.tight_layout(pad=0.4)
        st.pyplot(fig1, use_container_width=True)
        plt.close()
        st.markdown('</div>', unsafe_allow_html=True)

        # Chart 2 — Peak hour bars
        st.markdown(f'<div class="ump-card" style="margin-bottom:0.6rem;">', unsafe_allow_html=True)
        st.markdown('<div class="ump-card-label">Peak Hour Distribution — When is Each Zone Busiest?</div>', unsafe_allow_html=True)
        ph     = zones['peak_hour'].value_counts().sort_values()
        labels = [l.replace('Morning (8-10am)','Morning 8–10am')
                   .replace('Evening (5-8pm)','Evening 5–8pm')
                   .replace('Noon (12-2pm)','Noon 12–2pm') for l in ph.index]
        fig2, ax2 = plt.subplots(figsize=(5, 1.4))
        cols_ph = [C_GREEN, C_AMBER, C_RED][:len(ph)]
        bars = ax2.barh(labels, ph.values, color=cols_ph[::-1],
                        height=0.50, edgecolor=CARD, linewidth=0.4)
        for bar, val in zip(bars, ph.values):
            ax2.text(val + ph.values.max() * 0.015,
                     bar.get_y() + bar.get_height() / 2,
                     str(val), va='center', fontsize=8,
                     color=TEXT1, fontweight='bold')
        ax2.set_xlabel("Number of Zones with this Peak Hour", labelpad=5)
        ax2.xaxis.grid(True)
        ax2.set_axisbelow(True)
        ax2.tick_params(axis='y', labelsize=8, labelcolor=TEXT2)
        plt.tight_layout(pad=0.4)
        st.pyplot(fig2, use_container_width=True)
        plt.close()
        st.markdown('</div>', unsafe_allow_html=True)

        # Chart 3 — Land use donut
        st.markdown(f'<div class="ump-card">', unsafe_allow_html=True)
        st.markdown('<div class="ump-card-label">Land Use Breakdown — Zone Type Mix</div>', unsafe_allow_html=True)
        lu   = zones['land_use'].value_counts()
        lcols = [TEXT1, C_GREEN, C_AMBER, C_RED, TEXT3, MUTED]
        fig3, (axL, axR) = plt.subplots(1, 2, figsize=(5, 1.9),
                                          gridspec_kw={'width_ratios':[1,1.3]})
        axL.pie(lu.values, colors=lcols[:len(lu)], startangle=90,
                wedgeprops=dict(width=0.55, edgecolor=CARD, linewidth=1.5))
        axL.set_aspect('equal')
        axR.axis('off')
        for i, (lbl, val) in enumerate(zip(lu.index, lu.values)):
            pct = val / len(zones) * 100
            y   = 0.92 - i * (0.88 / max(len(lu), 1))
            axR.add_patch(mpatches.FancyBboxPatch(
                (0, y-0.07), 0.10, 0.10,
                boxstyle="round,pad=0.01", facecolor=lcols[i], edgecolor='none'))
            axR.text(0.15, y-0.01, lbl, fontsize=8, color=TEXT1, va='center')
            axR.text(0.98, y-0.01, f"{val} ({pct:.0f}%)",
                     fontsize=7.5, color=TEXT3, va='center', ha='right')
        axR.set_xlim(0,1)
        axR.set_ylim(-0.05, 1.05)
        plt.tight_layout(pad=0.3)
        st.pyplot(fig3, use_container_width=True)
        plt.close()
        st.markdown('</div>', unsafe_allow_html=True)

    #  03 Hourly Profile + Congestion ranking 
    st.markdown(f"""
    <div class="ump-section">
        <span class="ump-sec-num">03</span>
        <span class="ump-sec-title">24-Hour Traffic Profile & Congestion Ranking</span>
        <div class="ump-sec-line"></div>
    </div>""", unsafe_allow_html=True)

    hourly_col, rank_col = st.columns([3, 2], gap="medium")

    with hourly_col:
        st.markdown(f'<div class="ump-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="ump-card-label">Relative Traffic Intensity — 24-Hour Mumbai Pattern (MCGM calibrated, 100 = peak)</div>',
            unsafe_allow_html=True)

        hours   = list(range(24))
        hlabels = ['12a','1','2','3','4','5','6','7','8','9','10','11',
                   '12p','1','2','3','4','5','6','7','8','9','10','11']
        fig4, ax4 = plt.subplots(figsize=(7, 2.8))
        for h in range(23):
            v0, v1 = hourly[h], hourly[h+1]
            avg    = (v0 + v1) / 2
            c      = C_GREEN if avg < 45 else (C_AMBER if avg < 72 else C_RED)
            ax4.fill_between([h, h+1], [v0, v1], alpha=0.18, color=c, linewidth=0)
            ax4.plot([h, h+1], [v0, v1], color=c, linewidth=1.8)
        ax4.axvline(8,  color=C_AMBER, linewidth=1, linestyle='--', alpha=0.6)
        ax4.axvline(18, color=C_RED,   linewidth=1, linestyle='--', alpha=0.6)
        ax4.text(8.15,  max(hourly)*0.96, 'Morning\nPeak', fontsize=7,
                 color=C_AMBER, va='top')
        ax4.text(18.15, max(hourly)*0.96, 'Evening\nPeak', fontsize=7,
                 color=C_RED, va='top')
        ax4.set_xticks(hours)
        ax4.set_xticklabels(hlabels, fontsize=7)
        ax4.set_ylabel("Traffic Intensity (%)\n100 = peak hour", labelpad=5)
        ax4.set_xlim(0, 23)
        ax4.set_ylim(0, max(hourly) * 1.12)
        ax4.yaxis.grid(True)
        ax4.set_axisbelow(True)
        plt.tight_layout(pad=0.5)
        st.pyplot(fig4, use_container_width=True)
        plt.close()
        st.markdown(f"""
        <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:{MUTED};
                    margin-top:6px;line-height:1.5;">
            Mumbai's morning peak (8–10am) adds ~90 min to a 60-min trip.
            Evening peak (5–8pm) adds ~110 min. Source: TomTom Traffic Index 2023 (rank 5 globally).
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with rank_col:
        st.markdown(f'<div class="ump-card" style="height:100%;">', unsafe_allow_html=True)
        st.markdown('<div class="ump-card-label">Top 10 Most Congested Zones — Demand & Congestion Index</div>',
                    unsafe_allow_html=True)

        col_ci = 'congestion_index' if 'congestion_index' in zones.columns else 'demand'
        top10  = zones.nlargest(10, col_ci)[
            ['zone_id','demand',col_ci,'land_use','centroid_lat','centroid_lon']
        ].copy()
        top10.columns = ['Zone','Demand','CI','Land Use','Lat','Lon']
        top10['CI']  = top10['CI'].round(1)
        top10['Lat'] = top10['Lat'].round(4)
        top10['Lon'] = top10['Lon'].round(4)
        top10 = top10.reset_index(drop=True)
        top10.index = top10.index + 1

        fig5, ax5 = plt.subplots(figsize=(5, 3.2))
        ax5.axis('off')
        colors_row = []
        for ci in top10['CI']:
            if ci >= 66:   colors_row.append('#FFF0F0' if not DM else '#2A1A1A')
            elif ci >= 33: colors_row.append('#FFF8F0' if not DM else '#2A1E10')
            else:          colors_row.append('#F5FFF8' if not DM else '#0F2A1A')

        tbl = ax5.table(
            cellText=top10[['Zone','Demand','CI','Land Use','Lat']].values,
            colLabels=['Zone','Demand','CI (0-100)','Land Use','Lat'],
            cellLoc='left', loc='center',
            cellColours=[[c]*5 for c in colors_row],
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(7.0)
        tbl.scale(1, 1.55)
        for (r, c), cell in tbl.get_celld().items():
            cell.set_edgecolor(BORDER)
            cell.set_linewidth(0.5)
            if r == 0:
                cell.set_facecolor(SURFACE)
                cell.set_text_props(color=TEXT3, fontweight='bold')
            else:
                cell.set_text_props(color=TEXT1)
        plt.tight_layout(pad=0.2)
        st.pyplot(fig5, use_container_width=True)
        plt.close()
        st.markdown(f"""
        <div style="font-family:'DM Sans',sans-serif;font-size:11px;color:{MUTED};
                    margin-top:6px;line-height:1.5;">
            CI = Congestion Index (0–100). 100 = most congested zone in this run.
            Zones highlighted in red are above the 66th percentile — these are your intervention priorities.
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 04 Zone Detail Table 
    st.markdown(f"""
    <div class="ump-section">
        <span class="ump-sec-num">04</span>
        <span class="ump-sec-title">Zone Detail Table</span>
        <div class="ump-sec-line"></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family:'DM Sans',sans-serif;font-size:12px;color:{TEXT2};
                margin-bottom:0.6rem;line-height:1.5;">
        All zones sorted by demand (highest first). <b style="color:{TEXT1};">Demand Score</b> = estimated vehicles/hour crossing the zone.
        <b style="color:{TEXT1};">Congestion Index</b> (0–100) = how saturated the zone is relative to Mumbai's peak.
        <b style="color:{TEXT1};">Peak Hour</b> = when traffic is highest in that zone.
    </div>
    """, unsafe_allow_html=True)

    export_df = zones.drop(columns='geometry').copy()
    # Reorder to put lat/lon prominently
    cols_order = ['zone_id','centroid_lat','centroid_lon','demand',
                  'demand_category','congestion_index','land_use','peak_hour']
    cols_order = [c for c in cols_order if c in export_df.columns]
    export_df  = export_df[cols_order + [c for c in export_df.columns if c not in cols_order]]

    # Rename columns for clarity
    col_rename = {
        'zone_id': 'Zone ID',
        'centroid_lat': 'Lat',
        'centroid_lon': 'Lon',
        'demand': 'Demand Score',
        'demand_category': 'Category',
        'congestion_index': 'Congestion Index (0-100)',
        'land_use': 'Land Use',
        'peak_hour': 'Peak Hour',
    }
    display_df = export_df.sort_values('demand', ascending=False).reset_index(drop=True)
    display_df = display_df.rename(columns={k: v for k, v in col_rename.items() if k in display_df.columns})
    if 'Lat' in display_df.columns:
        display_df['Lat'] = display_df['Lat'].round(4)
    if 'Lon' in display_df.columns:
        display_df['Lon'] = display_df['Lon'].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=280,
    )

    #  05 Export 
    st.markdown(f"""
    <div class="ump-section">
        <span class="ump-sec-num">05</span>
        <span class="ump-sec-title">Export</span>
        <div class="ump-sec-line"></div>
    </div>""", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 2], gap="small")
    with col1:
        st.download_button(
            "Download CSV",
            data=export_df.to_csv(index=False),
            file_name="mumbai_zones.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Download GeoJSON",
            data=zones.to_json(),
            file_name="mumbai_zones.geojson",
            mime="application/json",
            use_container_width=True,
        )

#  Empty state 
else:
    st.markdown(f"""
    <p style="font-family:'DM Mono',monospace;font-size:10px;letter-spacing:0.14em;
              color:{MUTED};text-transform:uppercase;margin-bottom:1.5rem;">
        Select zone resolution in the sidebar and click Analyze Mumbai to begin
    </p>""", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3, gap="large")
    for col, (num, title, body) in zip([c1, c2, c3], [
        ("01", "Real Mumbai Blocks",
         "Zones derived from Mumbai's actual road network via OpenStreetMap — "
         "clipped to BMC boundary. Switch between Coarse / Medium / Fine / Very Fine granularity."),
        ("02", "Realistic Demand Model",
         "Travel demand calibrated against TomTom 2023 congestion index (rank 5 globally). "
         "IDW proximity to known hotspots: Dadar, BKC, WEH, LBS Marg, Sea Link."),
        ("03", "Dark & Light Theme",
         "Toggle the theme with the ◑ button in the sidebar. "
         "Lat/lon coordinates shown per zone — both in the hover panel and the detail table."),
    ]):
        with col:
            st.markdown(f"""
            <div class="ump-info-card">
                <div class="ump-info-num">{num}</div>
                <div class="ump-info-title">{title}</div>
                <div class="ump-info-body">{body}</div>
            </div>""", unsafe_allow_html=True)