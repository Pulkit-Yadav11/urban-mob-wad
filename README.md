# Mumbai Urban Mobility Platform

An interactive Streamlit dashboard for visualising and analysing urban travel demand across Mumbai. The platform generates configurable traffic zones, models hourly congestion using calibrated real-world data, and provides an interactive Leaflet map with road-level overlays.

---

## Features

- **Zone Generation** — Configurable spatial resolution from coarse to very fine using OpenStreetMap boundary data.
- **Travel Demand Modelling** — Estimates demand using Mumbai-specific calibration and proximity to major traffic corridors.
- **Hourly Simulation** — Models congestion across 24 hours with realistic morning and evening peak patterns.
- **Interactive Map** — Displays zone-level congestion and road-network overlays using Leaflet.
- **Summary Analysis** — Provides zone-level demand information and hourly traffic charts.
- **Dark / Light Theme** — Supports both map and interface themes.

---

## Project Structure

```text
um-report-make/
│
├── app.py                         # Streamlit entry point
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignored files
│
├── services/
│   ├── analyzer.py               # Travel demand model & hourly profile
│   ├── cache_manager.py          # Cache handling utilities
│   ├── data_loader.py            # Boundary & road data fetching
│   ├── map_component.py          # Leaflet map renderer
│   ├── zone_builder.py           # Zone generation pipeline
│   ├── zone_creator.py           # Grid / polygon zone generation
│   └── __init__.py
│
├── cache/                        # Runtime-generated / cached data
│   ├── mumbai_analyzed.geojson
│   ├── mumbai_zones.geojson
│   ├── mumbai_bbox_20.txt
│   ├── mumbai_bbox_50.txt
│   └── mumbai_bbox_200.txt
│
├── data/
│   ├── processed/
│   │   └── mumbai_zones.csv      # Processed Mumbai zone data
│   └── raw/                       # Runtime raw input data
│
└── output/
    ├── csv/                       # Exported CSV files
    └── maps/                      # Generated map exports
```

Large runtime-generated files such as `agents_resampled.parquet` and `mumbai_roads.json` are excluded from Git and regenerated when required.

---

## Installation & Setup

### Prerequisites

- Python **3.11+**
- `pip` or `conda`
- Internet access during the first run for Overpass API data retrieval

### 1. Clone the Repository

```bash
git clone https://github.com/<your-username>/um-report-make.git
cd um-report-make
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Linux / macOS:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If `geopandas` causes GDAL-related issues on Windows, Conda can be used:

```bash
conda create -n mobility python=3.11
conda activate mobility
conda install geopandas
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

The dashboard is available at:

```text
http://localhost:8501
```

---

## First-Run Behaviour

On the first run, the application retrieves Mumbai road-network data through the **Overpass API** and stores reusable data in `cache/`.

The initial fetch may take approximately **20–40 seconds**, depending on the network connection. Subsequent runs use the cached data and therefore start faster.

If large generated files are missing, the application regenerates them automatically.

---

## Configuration

The dashboard provides three main controls:

| Control | Description |
|---|---|
| **Zone Resolution** | Selects the number of analysis zones, from 20 to 200 |
| **Hour Slider** | Selects the hour used for traffic simulation |
| **Dark / Light Theme** | Changes map tiles and interface appearance |

---

## Traffic Modelling

The platform estimates Mumbai's travel demand using spatial and temporal modelling.

### Zone Generation

Mumbai is divided into configurable geographic zones. Each zone acts as an independent unit for analysing estimated travel demand and congestion.

### Traffic Hotspots

The model incorporates known high-traffic corridors:

- Western Express Highway (WEH)
- Eastern Express Highway (EEH)
- LBS Marg
- Sion–Panvel Highway
- SV Road

### IDW Proximity Weighting

**Inverse Distance Weighting (IDW)** increases the influence of known traffic hotspots on nearby zones. Zones closer to major corridors receive a stronger hotspot influence.

### Congestion Calibration

The model is calibrated against Mumbai's reported **TomTom Congestion Index (~65)** and validated against available urban transport demand ranges.

### Hourly Simulation

Traffic demand is modelled over a 24-hour period, incorporating typical:

- Morning peak
- Midday conditions
- Evening peak
- Night-time low demand

---

## Interactive Map

The Leaflet-based dashboard map provides:

- Mumbai analysis zones
- Zone-level congestion intensity
- Road-network overlays
- Major traffic corridor hotspots
- Interactive geographic information
- Dark and light map themes

The map provides a spatial view of where simulated demand and congestion are concentrated across Mumbai.

---

## Data Sources

| Source | Usage |
|---|---|
| **OpenStreetMap via Overpass API** | Mumbai road-network geometry and geographic data |
| **TomTom Traffic Index 2023** | Base congestion calibration |
| **MMRDA Mumbai Metropolitan Plan 2016–2036** | Land-use zone weighting |
| **MCGM Road Network Study** | Traffic corridor hotspot identification |
| **CIRT India Urban Transport Statistics** | Travel-demand range validation |

---

## System Workflow

```text
OpenStreetMap / Overpass API
            │
            ▼
      Mumbai Boundary
            │
            ▼
      Zone Generation
            │
            ▼
   Traffic Data & Hotspots
            │
            ▼
     IDW Weighting
            │
            ▼
    Hourly Demand Model
            │
            ▼
   Congestion Estimation
            │
            ▼
   Streamlit Dashboard
        ┌────┴────┐
        ▼         ▼
   Interactive   Charts &
      Map       Statistics
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web application framework |
| `geopandas` | Spatial data processing |
| `osmnx` | OpenStreetMap boundary and road fetching |
| `folium` | Interactive Leaflet maps |
| `streamlit-folium` | Folium integration with Streamlit |
| `shapely` | Geometry operations |
| `pandas` | Data manipulation |
| `numpy` | Numerical computation |
| `scikit-learn` | Modelling and interpolation utilities |
| `matplotlib` | Charts and visualisation |

---

## Data Directory

The current project is focused exclusively on **Mumbai**.

```text
data/
├── processed/
│   └── mumbai_zones.csv
│
└── raw/
```

No other city datasets are included in the processed-data directory.

---

## Contributor Guidance

Contributions are welcome.

1. Create a feature branch.
2. Make and test your changes locally.
3. Keep processing logic inside the appropriate `services/` module.
4. Do not commit large generated cache or runtime files.
5. Update `requirements.txt` when adding dependencies.
6. Submit a pull request with a clear description of the changes.

Example:

```bash
git checkout -b feature/new-analysis
git add .
git commit -m "Add new traffic analysis feature"
git push origin feature/new-analysis
```

---

## License

This project is licensed under the **MIT License**.
