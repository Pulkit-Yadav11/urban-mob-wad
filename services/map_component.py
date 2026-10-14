import streamlit.components.v1 as components
import json


def render_map(zones_geojson: dict, roads_geojson: dict,
               center: tuple, height: int = 500,
               dark_mode: bool = False, hour: int = 0):
    """
    Render a Leaflet map.
    dark_mode=True  -> dark CartoDB tiles + dark panel styling
    dark_mode=False -> light CartoDB Voyager tiles + warm panel styling
    hour            -> embedded in HTML so components.html re-renders on hour change
    """
    center_lat, center_lng = center
    zones_json = json.dumps(zones_geojson)
    roads_json = json.dumps(roads_geojson)

    if dark_mode:
        tile_url  = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        panel_bg  = "rgba(18,18,22,0.95)"
        panel_bdr = "#2A2A35"
        panel_fg  = "#E8E4DC"
        panel_sub = "#8A8680"
        legend_bg = "rgba(18,18,22,0.95)"
        map_bg    = "#0F0F14"
    else:
        tile_url  = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        panel_bg  = "rgba(255,252,248,0.97)"
        panel_bdr = "#D6D1C7"
        panel_fg  = "#1A1814"
        panel_sub = "#9E9891"
        legend_bg = "rgba(255,252,248,0.97)"
        map_bg    = "#FFFFFF"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css"/>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
      <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        html, body {{ height:100%; background:{map_bg}; font-family:'DM Sans','Helvetica Neue',sans-serif; }}
        #map {{ height:{height}px; width:100%; }}

        .info-panel {{
          background:{panel_bg};
          color:{panel_fg};
          padding:12px 16px;
          border-radius:8px;
          font-size:12px;
          min-width:200px;
          border:1px solid {panel_bdr};
          box-shadow:0 2px 12px rgba(0,0,0,0.18);
          font-family:'DM Mono','Courier New',monospace;
          line-height:1;
        }}
        .info-panel .zone-id {{
          font-size:10px;
          letter-spacing:0.1em;
          color:{panel_sub};
          margin-bottom:8px;
          text-transform:uppercase;
        }}
        .info-panel .demand-val {{
          font-size:1.6rem;
          font-weight:600;
          color:{panel_fg};
          line-height:1;
          margin-bottom:8px;
          font-family:'Georgia',serif;
        }}
        .info-panel .meta-row {{
          display:flex;
          flex-direction:column;
          gap:4px;
          margin-top:8px;
          border-top:1px solid {panel_bdr};
          padding-top:8px;
        }}
        .info-panel .meta-item {{
          display:flex;
          justify-content:space-between;
          font-size:10px;
          color:{panel_sub};
          gap:12px;
        }}
        .info-panel .meta-item span:last-child {{
          color:{panel_fg};
          font-weight:500;
        }}
        .info-panel .coord-row {{
          margin-top:6px;
          border-top:1px solid {panel_bdr};
          padding-top:6px;
          display:flex;
          gap:10px;
          font-size:9.5px;
          color:{panel_sub};
        }}
        .info-panel .coord-row span {{
          font-weight:500;
          color:{panel_fg};
        }}
        .info-panel .placeholder {{
          font-size:10px;
          letter-spacing:0.1em;
          color:{panel_sub};
          text-transform:uppercase;
        }}
        .legend-panel {{
          background:{legend_bg};
          padding:10px 14px;
          border-radius:8px;
          font-family:'DM Mono','Courier New',monospace;
          font-size:10px;
          color:{panel_sub};
          line-height:2;
          border:1px solid {panel_bdr};
          box-shadow:0 2px 8px rgba(0,0,0,0.15);
        }}
        .legend-panel b {{
          display:block;
          color:{panel_sub};
          letter-spacing:0.12em;
          text-transform:uppercase;
          font-size:9px;
          margin-bottom:6px;
        }}
        .legend-dot {{
          display:inline-block;
          width:10px; height:10px;
          border-radius:2px;
          margin-right:7px;
          vertical-align:middle;
        }}
        .leaflet-control-attribution {{
          background:rgba(0,0,0,0.4) !important;
          font-size:9px !important;
          color:{panel_sub} !important;
        }}
        .leaflet-control-attribution a {{ color:{panel_sub} !important; }}
      </style>
    </head>
    <body>
      <div id="map"></div>
      <div id="hour-key" style="display:none">{hour}</div>
      <script>
        const zonesData = {zones_json};
        const roadsData = {roads_json};

        const map = L.map('map', {{
          center: [{center_lat}, {center_lng}],
          zoom: 11,
          zoomControl: false
        }});

        L.control.zoom({{ position: 'bottomright' }}).addTo(map);

        L.tileLayer('{tile_url}', {{
          attribution: '&copy; OpenStreetMap &copy; CARTO',
          subdomains: 'abcd',
          maxZoom: 19
        }}).addTo(map);

        // Live cursor coordinates
        const coordCtrl = L.control({{ position: 'bottomleft' }});
        coordCtrl.onAdd = function() {{
          this._div = L.DomUtil.create('div', 'legend-panel');
          this._div.style.minWidth = '180px';
          this._div.innerHTML = '<b>Cursor</b><span id="coord-txt" style="color:{panel_fg}">Hover map</span>';
          return this._div;
        }};
        coordCtrl.addTo(map);
        map.on('mousemove', function(e) {{
          document.getElementById('coord-txt').textContent =
            e.latlng.lat.toFixed(5) + '\u00b0 N,  ' + e.latlng.lng.toFixed(5) + '\u00b0 E';
        }});

        const demands = zonesData.features.map(f => f.properties.demand);
        const sorted  = [...demands].sort((a, b) => a - b);
        const low     = sorted[Math.floor(sorted.length * 0.33)];
        const high    = sorted[Math.floor(sorted.length * 0.66)];

        function getColor(d) {{
          if (d < low)  return '#4A7C59';
          if (d < high) return '#C47B3A';
          return '#8B2A36';
        }}

        // Hover info panel
        const infoCtrl = L.control({{ position: 'topleft' }});
        infoCtrl.onAdd = function() {{
          this._div = L.DomUtil.create('div', 'info-panel');
          this._div.innerHTML = '<div class="placeholder">Hover over a zone</div>';
          return this._div;
        }};
        infoCtrl.update = function(props) {{
          if (props) {{
            const lat = props.centroid_lat != null ? parseFloat(props.centroid_lat).toFixed(5) : '—';
            const lon = props.centroid_lon != null ? parseFloat(props.centroid_lon).toFixed(5) : '—';
            const ci  = props.congestion_index != null ? parseFloat(props.congestion_index).toFixed(1) : '—';
            this._div.innerHTML = `
              <div class="zone-id">${{props.zone_id}}</div>
              <div class="demand-val">${{props.demand}}</div>
              <div class="meta-row">
                <div class="meta-item"><span>Category</span><span>${{props.demand_category}}</span></div>
                <div class="meta-item"><span>Congestion</span><span>${{ci}}</span></div>
                <div class="meta-item"><span>Peak</span><span>${{props.peak_hour.replace('Morning (8-10am)','Morning').replace('Evening (5-8pm)','Evening').replace('Noon (12-2pm)','Noon')}}</span></div>
                <div class="meta-item"><span>Land Use</span><span>${{props.land_use}}</span></div>
              </div>
              <div class="coord-row">
                <span>Lat:</span><span>${{lat}}\u00b0</span>
                &nbsp;&nbsp;
                <span>Lon:</span><span>${{lon}}\u00b0</span>
              </div>
            `;
          }} else {{
            this._div.innerHTML = '<div class="placeholder">Hover over a zone</div>';
          }}
        }};
        infoCtrl.addTo(map);

        // Draw zones
        L.geoJSON(zonesData, {{
          style: function(feat) {{
            return {{
              fillColor: getColor(feat.properties.demand),
              fillOpacity: 0.42,
              color: '#FFFFFF',
              weight: 0.8,
              opacity: 0.7
            }};
          }},
          onEachFeature: function(feat, layer) {{
            layer.on({{
              mouseover: function(e) {{
                e.target.setStyle({{ fillOpacity: 0.72, weight: 2.5 }});
                infoCtrl.update(feat.properties);
              }},
              mouseout: function(e) {{
                e.target.setStyle({{ fillOpacity: 0.42, weight: 0.8 }});
                infoCtrl.update(null);
              }}
            }});
          }}
        }}).addTo(map);

        // Roads with Dynamic Agent Bottleneck Gradients
        if (roadsData.features && roadsData.features.length > 0) {{
          L.geoJSON(roadsData, {{
            style: function(feat) {{
              const vol       = feat.properties.current_volume || 0;
              const congested = feat.properties.congested_agents || 0;
              const hw        = feat.properties.highway;

              let lineColor = '#504A42';
              if (vol > 0 && congested === 0) lineColor = '#2A7B4C';
              if (congested > 0)              lineColor = '#D03B3B';

              return {{
                color:   lineColor,
                weight:  congested > 0 ? 3.5 : vol > 0 ? 1.8 : 0.6,
                opacity: congested > 0 ? 0.90 : vol > 0 ? 0.60 : 0.35
              }};
            }},
            onEachFeature: function(feat, layer) {{
              if (feat.properties) {{
                const vol    = feat.properties.current_volume || 0;
                const shifts = feat.properties.frustrated_shifts || 0;
                const cong   = feat.properties.congested_agents || 0;
                layer.bindPopup(
                  `<b>${{feat.properties.name || 'Unnamed Corridor'}}</b><br>` +
                  `Type: ${{feat.properties.highway || 'local'}}<br>` +
                  `Hourly Volume: ${{vol.toLocaleString()}} agents<br>` +
                  `Congested Agents: ${{cong.toLocaleString()}}<br>` +
                  `Deflected to Rail: ${{shifts.toLocaleString()}}`
                );
              }}
            }}
          }}).addTo(map);
        }}

        // Legend
        const legend = L.control({{ position: 'topright' }});
        legend.onAdd = function() {{
          const div = L.DomUtil.create('div', 'legend-panel');
          div.innerHTML = `
            <b>Demand Level</b>
            <div><span class="legend-dot" style="background:#4A7C59"></span>Low (&lt;${{Math.round(low)}})</div>
            <div><span class="legend-dot" style="background:#C47B3A"></span>Medium</div>
            <div><span class="legend-dot" style="background:#8B2A36"></span>High (&gt;${{Math.round(high)}})</div>
          `;
          return div;
        }};
        legend.addTo(map);
      </script>
    </body>
    </html>
    """
    components.html(html, height=height + 2, scrolling=False)