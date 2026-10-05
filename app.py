"""AquaTerra Research AI: a separate Streamlit research application.
Deploy this entire folder as a new GitHub repository using app.py and Python 3.12.
Scientific calculations use the existing NumPy/Pandas stack; no new mandatory packages.
External mechanistic models are import/export workflows, not embedded simulators."""
from __future__ import annotations

import base64
import calendar
import hashlib
import html
import io
import json
import math
import os
import queue
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

import folium
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from pyproj import Geod, Transformer
from requests.adapters import HTTPAdapter
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.geometry.polygon import orient
from shapely.ops import transform as shape_transform, unary_union
from urllib3.util.retry import Retry
from crew_config import AGENT_ROSTER, DEFAULT_MODEL, DEFAULT_TOKENS_PER_MINUTE
from ai_providers import DEFAULT_PROVIDER, PROVIDERS
from evidence import quality_findings, review_is_current, run_fingerprint
import evidence as evidence_module
for _domain in ("geospatial_water", "ecology_field", "climate_air"):
    evidence_module.DOMAIN_MODULES[_domain] = tuple(dict.fromkeys((*evidence_module.DOMAIN_MODULES[_domain], "Research validation")))

from environment import (
    DataError,
    FIELD_COLUMNS,
    MAX_SAT_KM2,
    MODULES,
    PAGES,
    RASTER_STYLES,
    ROOT,
    VERSION,
    all_sources,
    all_tables,
    build_exports,
    chart_specs,
    city_search,
    execute_analysis,
    fmt,
    geotiff_bytes,
    interactive_chart,
    landmark_search,
    make_study,
    normalize_geometry,
    parse_field_csv,
    plain_metadata,
    raster_png,
    safe_frame,
    secret,
    utc_now
)

APP_RELEASE = "1.0"

def inject_theme():
    st.html("""<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
    .stApp{background:radial-gradient(ellipse at 95% 4%,rgba(111,70,181,.22),transparent 40%),radial-gradient(ellipse at 10% 85%,rgba(16,111,115,.13),transparent 42%),#090E1B;color:#E9EEF7}
    .stApp{color-scheme:dark}
    [data-testid='stMain'],[data-testid='stSidebar']{color:#E9EEF7}
    [data-testid='stMarkdownContainer'] p,[data-testid='stMarkdownContainer'] li,[data-testid='stWidgetLabel'] p{color:#DFE9F5!important}
    [data-testid='stCaptionContainer'],[data-testid='stCaptionContainer'] p{color:#C1D0E2!important;opacity:1!important}
    [data-testid='stSidebar'] [data-testid='stCaptionContainer'] p{color:#BBCDE0!important}
    [data-testid='stMarkdownContainer'] a{color:#82EDD4!important}
    .stApp label,.stApp summary{color:#E3EDF9!important}
    .stApp input,.stApp textarea,[data-baseweb='select']>div{background-color:#172238!important;color:#F0F5FD!important;-webkit-text-fill-color:#F0F5FD}
    .stApp input::placeholder,.stApp textarea::placeholder{color:#B4C5D9!important;-webkit-text-fill-color:#B4C5D9;opacity:1}
    [role='listbox'],[role='option']{background-color:#172238!important;color:#F0F5FD!important}
    [data-testid='stAlert']{background:#142538!important;border:1px solid #58738F}
    [data-testid='stAlert'] p{color:#E8F1FB!important}
    [data-testid='stBaseButton-secondary']{background:#1C2B43!important;color:#F1F6FF!important;border:1px solid #62768D!important}
    [data-testid='stBaseButton-secondary'] p{color:#F1F6FF!important}
    [data-testid='stBaseButton-primary']{background:linear-gradient(105deg,#68E0C3,#9EADF9)!important;color:#102232!important;border:0!important}
    [data-testid='stBaseButton-primary'] p{color:#102232!important;font-weight:700}
    button:disabled{opacity:.65!important}
    html,body,[class*='css']{font-family:'DM Sans',sans-serif}
    h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.025em}
    [data-testid='stHeader']{background:#090E1B}
    [data-testid='stSidebar']{background:linear-gradient(180deg,#12172B,#0D1C29);border-right:1px solid #243046}
    [data-testid='stSidebar'] [data-testid='stMarkdownContainer'] p{color:#B4C5D6}
    .block-container{padding-top:2rem;padding-bottom:3rem;max-width:1540px}
    [data-testid='stMetric']{background:linear-gradient(135deg,rgba(28,42,63,.92),rgba(25,27,51,.95));border:1px solid #29354D;border-radius:15px;padding:18px}
    [data-testid='stMetricValue']{color:#72E6CB;font-family:'Manrope',sans-serif}
    [data-testid='stMetricLabel']{color:#AEBED1}
    .stButton>button[kind='primary']{background:linear-gradient(105deg,#68E0C3,#9EADF9);color:#102232;border:0;font-weight:700;box-shadow:0 5px 24px #5FE1C322}
    .stButton>button,.stDownloadButton>button{border-radius:11px;min-height:2.75rem}
    [data-testid='stVerticalBlockBorderWrapper']>div{border-radius:16px}
    .eco-brand{display:flex;gap:11px;align-items:center;margin-bottom:18px}
    .eco-brand strong{font-family:Manrope,sans-serif;letter-spacing:-.6px;font-size:23px;color:#F2F6FF}.eco-brand small{display:block;font-size:10px;letter-spacing:1.7px;color:#82A2B9;text-transform:uppercase;margin-top:3px}
    .eyebrow{font-size:11px;letter-spacing:2.5px;font-weight:700;text-transform:uppercase;color:#74DEC6;margin-bottom:15px}
    .eco-hero{border-radius:24px;padding:40px;min-height:275px;border:1px solid #344663;position:relative;overflow:hidden;background-size:cover;background-position:center}
    .eco-hero h1{font-size:clamp(32px,3.5vw,52px);line-height:1.09;margin:10px 0 19px;color:#F6F8FF;max-width:700px}
    .eco-hero p{color:#C3D4E2;max-width:570px;font-size:15px;line-height:1.7}
    .pill{display:inline-block;border:1px solid #6FE6CB55;color:#9AF0DC;background:#18363D99;border-radius:30px;padding:5px 12px;font-size:11px;margin-right:7px;margin-top:10px}
    .section-note{color:#9CB1C5;font-size:13px;line-height:1.7}.status-chip{display:inline-block;color:#A8EBD8;background:#123B3880;border:1px solid #286858;border-radius:20px;padding:5px 12px;font-size:11px;margin:6px 0 16px}
    .module-banner{height:120px;border:1px solid #33475B;border-radius:18px;padding:23px 28px;background-size:cover;background-position:center;position:relative;margin:12px 0 23px}.module-banner h2{color:#F4F8FE;margin:0;font-size:26px}.module-banner p{color:#C8D8E7;font-size:12px;margin:7px 0}
    [data-testid='stDataFrame']{border:1px solid #29384D;border-radius:12px;overflow:hidden}
    </style>""")


def go_page(page):
    st.session_state["page"] = page


def apply_drawing(drawing):
    try:
        st.session_state["boundary"] = mapping(normalize_geometry(drawing))
        st.session_state["use_boundary"] = True
    except DataError as exc:
        st.session_state["drawing_error"] = str(exc)


def banner(title, subtitle):
    st.html(f"<div class='module-banner'><h2>{html.escape(title)}</h2><p>{html.escape(subtitle)}</p></div>")


def overview(run):
    st.html("""<div class='eco-hero' style='background:linear-gradient(125deg,#153a42,#22213c)'>
    <div class='eyebrow'>AquaTerra Research AI</div><h1>Water, ecology<br>and inspectable evidence.</h1>
    <p>Connect field observations with satellite measurements. Inspect the method, assess uncertainty,
    and export the calculations behind every research result.</p>
    <span class='pill'>Field validation</span><span class='pill'>Spatial analysis</span>
    <span class='pill'>Five-agent review</span></div>""")
    for col, label, page in zip(st.columns(3), ["Set up study", "Open research workspace", "Review evidence"],
                                ["Study & analysis", "Research workspace", "AI team"]):
        col.button(label, width="stretch", on_click=go_page, args=(page,))
    for col, title, body in zip(st.columns(3), ["01 / Observe", "02 / Evaluate", "03 / Reproduce"],
        ["Draw a reservoir and sampling sites. Retrieve real observations with coverage and quality flags.",
         "Upload Excel or CSV data. Match field samples, examine community patterns and test supported relationships.",
         "Download data, figures, settings, executed analysis code and an audit record. Estimates keep their validation status."]):
        with col:
            with st.container(border=True):
                st.subheader(title)
                st.write(body)
    if run:
        st.caption(f"Saved study: {run['study']['label']} | {run['study']['start']} to {run['study']['end']}")
        a,b,c=st.columns(3)
        a.metric("Study area", f"{run['study']['area_km2']:.1f} km²")
        b.metric("Completed modules",len(run['results']))
        c.metric("Source records",len(all_sources(run)))
    else:
        st.info("Start in Study & analysis. Draw your reservoir and run at least one selected module, then open Research workspace.")
    st.caption("Field measurements, satellite indicators and model estimates are labelled separately. Agent agreement is not scientific validation.")


def base_map(study, draw=False):
    from folium.plugins import Draw, Fullscreen
    m = folium.Map(location=[study["lat"], study["lon"]], tiles="OpenStreetMap", zoom_start=12, control_scale=True)
    folium.GeoJson(study["geometry"], name="Study boundary", style_function=lambda _: {"color": "#A78BFA", "weight": 3, "fillColor": "#5FE1C3", "fillOpacity": .09}).add_to(m)
    west,south,east,north = study["bbox"]
    m.fit_bounds([[south,west],[north,east]])
    Fullscreen().add_to(m)
    if draw:
        Draw(export=False, draw_options={"polyline": False, "circle": False, "circlemarker": False, "marker": False,
             "polygon": {"allowIntersection": False}, "rectangle": True}, edit_options={"edit": False, "remove": True}).add_to(m)
    return m


def map_for_run(run, modules=None, raster_layer=None):
    m = base_map(run["study"])
    modules = modules or list(run["results"])
    for module, table_name, frame in all_tables(run):
        if module not in modules or table_name not in ["Sampling candidates", "Included field observations", "Earthquake events", "Species occurrences"] or frame.empty:
            continue
        group = folium.FeatureGroup(name=table_name)
        for _, row in frame.iterrows():
            radius, color, title = 6, "#128C80", table_name
            if table_name == "Earthquake events":
                mag = float(row.magnitude) if pd.notna(row.magnitude) else 0
                radius, color, title = 2 + 1.6*max(0,mag), "#8A5CD1", f"Magnitude {fmt(mag,1)} · depth {fmt(row.depth_km,1)} km"
            elif table_name == "Species occurrences":
                title, color, radius = str(row.species), "#579242", 4
            elif table_name == "Sampling candidates":
                title, color = f"Candidate {row.priority_rank} · NDCI {row.ndci:.3f} (unverified)", "#B98013"
            elif table_name == "Included field observations":
                title = str(row.site)
                if "chlorophyll_ug_l" in row and pd.notna(row.chlorophyll_ug_l):
                    # Area proportional to measurement, with readable bounds.
                    radius = min(22, max(4, math.sqrt(max(0,float(row.chlorophyll_ug_l))) * 2))
                    title += f" · chlorophyll {row.chlorophyll_ug_l:g} µg/L (user supplied)"
            folium.CircleMarker([row.latitude, row.longitude], radius=radius, color=color, weight=1,
                fill=True, fill_color=color, fill_opacity=.75, tooltip=html.escape(title)).add_to(group)
        group.add_to(m)
        if modules == ["Earthquakes"]:
            m.fit_bounds([[frame.latitude.min(),frame.longitude.min()],[frame.latitude.max(),frame.longitude.max()]])
    if raster_layer:
        r = run["results"].get("Satellite", {}).get("raster")
        if r and np.isfinite(r["arrays"][raster_layer]).any():
            from affine import Affine
            from rasterio.warp import calculate_default_transform, reproject, Resampling, transform_bounds
            from rasterio.transform import array_bounds
            h,w = r["valid"].shape
            src_transform = Affine(*r["transform"][:6])
            bounds = array_bounds(h,w,src_transform)
            dst_transform,dw,dh = calculate_default_transform(f"EPSG:{r['epsg']}", "EPSG:3857", w,h,*bounds)
            source = r["arrays"][raster_layer]
            dest = np.full((dh,dw),np.nan,dtype="float32")
            reproject(source,dest,src_transform=src_transform,src_crs=f"EPSG:{r['epsg']}",src_nodata=np.nan,
                      dst_transform=dst_transform,dst_crs="EPSG:3857",dst_nodata=np.nan,resampling=Resampling.nearest)
            cmap,lo,hi = RASTER_STYLES[raster_layer]
            rgba = matplotlib.colormaps[cmap](np.clip((np.nan_to_num(dest)-lo)/(hi-lo),0,1))
            rgba[:,:,3] = np.isfinite(dest)*.82
            west,south,east,north = transform_bounds("EPSG:3857","EPSG:4326",*array_bounds(dh,dw,dst_transform))
            folium.raster_layers.ImageOverlay((rgba*255).astype("uint8"), bounds=[[south,west],[north,east]], name=raster_layer, opacity=.9).add_to(m)
            from branca.colormap import LinearColormap
            colors = [matplotlib.colors.to_hex(matplotlib.colormaps[cmap](v)) for v in np.linspace(0,1,8)]
            LinearColormap(colors,vmin=lo,vmax=hi,caption=f"{raster_layer} · screening index").add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def show_map(m, key, height=475, interactive=False):
    from streamlit_folium import st_folium
    return st_folium(m, height=height, use_container_width=True, key=key,
                     returned_objects=["last_active_drawing", "last_clicked"] if interactive else [])


def study_page():
    st.title("Define your study")
    st.caption("Choose a place, inspect the boundary and request only the evidence you need.")
    left,right = st.columns([1,1.65], gap="large")
    with left:
        with st.expander("Find a city, lake or landmark", expanded=True):
            query = st.text_input("Place name", placeholder="Rawal Lake, Islamabad")
            landmarks = st.checkbox("Include river / landmark search using OpenStreetMap", value=False)
            if landmarks:
                st.caption("User-triggered searches only, cached and limited to one request per second for this app; no autocomplete. OpenStreetMap attribution applies.")
                st.markdown("[Nominatim usage policy](https://operations.osmfoundation.org/policies/nominatim/)")
            if st.button("Search place", width="stretch"):
                if len(query.strip()) < 3:
                    st.warning("Enter at least three characters.")
                else:
                    try:
                        with st.spinner("Finding matching places…"):
                            st.session_state["places"] = landmark_search(query.strip()) if landmarks else city_search(query.strip())
                    except DataError as exc:
                        st.error(str(exc))
            places = st.session_state.get("places", [])
            if places:
                chosen = st.selectbox("Matching places", range(len(places)), format_func=lambda i: places[i]["label"])
                if st.button("Use this location"):
                    p = places[chosen]
                    st.session_state.update({"study_lat": p["lat"], "study_lon": p["lon"], "study_label": p["label"], "use_boundary": False})
            elif "places" in st.session_state:
                st.caption("No matching place. Use coordinates or try the landmark search.")
        label = st.text_input("Study name", key="study_label")
        st.caption("A study name labels the result. It does not select the entire river or change the coordinates.")
        a,b = st.columns(2)
        lat = a.number_input("Latitude", min_value=-80.0,max_value=80.0,format="%.6f",key="study_lat")
        lon = b.number_input("Longitude",min_value=-180.0,max_value=180.0,format="%.6f",key="study_lon")
        radius = st.slider("Study radius (km)",.5,50.0,4.0,.5)
        start = st.date_input("Historical start", date.today()-timedelta(days=97),max_value=date.today())
        end = st.date_input("Historical end", date.today()-timedelta(days=7),max_value=date.today())
        st.caption("Weather and air forecasts start today; they use a separate future window.")
        upload = st.file_uploader("Optional boundary (GeoJSON, WGS84)",type=["geojson","json"])
        if upload is not None:
            try:
                if upload.size > 2_000_000:
                    raise DataError("Keep boundary uploads below 2 MB.")
                parsed = json.loads(upload.getvalue())
                st.session_state["boundary"] = mapping(normalize_geometry(parsed))
            except Exception as exc:
                st.error(f"Boundary could not be used: {str(exc)[:200]}")
        custom = None
        if st.session_state.get("boundary"):
            if st.checkbox("Use uploaded / drawn boundary", key="use_boundary"):
                custom = st.session_state["boundary"]
        try:
            study = make_study(label,lat,lon,radius,start,end,custom)
        except DataError as exc:
            st.error(str(exc))
            study = None
    with right:
        if study:
            response = show_map(base_map(study, True),"draw-study",height=505,interactive=True)
            drawing = (response or {}).get("last_active_drawing")
            if drawing:
                st.button("Use the drawn boundary",type="primary",on_click=apply_drawing,args=(drawing,))
            if st.session_state.get("drawing_error"):
                st.error(st.session_state.pop("drawing_error"))
            st.caption(f"{study['area_km2']:.2f} km² · {study['boundary']} · Weather/air use the centroid grid cell. Drawing a boundary does not delineate an upstream catchment.")
            st.info(f"Local study centred at {study['lat']:.5f}, {study['lon']:.5f}. For a river, zoom in and check that the boundary actually covers the intended channel or reach. A geocoding result is a reference point, not a river boundary.")
            if study["area_km2"] > MAX_SAT_KM2:
                st.info(f"Satellite analysis supports up to {MAX_SAT_KM2:g} km². Other selected modules can still run.")
    st.subheader("Select analyses")
    selected = st.multiselect("Modules",MODULES,default=["Climate","Air quality","Satellite","Earthquakes","Biodiversity"])
    with st.expander("Analysis settings",expanded=False):
        c1,c2,c3 = st.columns(3)
        with c1:
            baseline = st.checkbox("Add 1991–2020 climate baseline",False)
            st.caption("Uses a longer ERA5 request. Monthly anomalies require complete months.")
            flow = st.number_input("Optional river screening threshold (m³/s)",min_value=0.0,value=0.0)
            st.caption("0 disables threshold comparisons. A supplied threshold is not automatically validated.")
        with c2:
            scenes = st.slider("Satellite scenes to process",1,6,3)
            cloud = st.slider("Maximum whole-scene cloud cover (%)",5,90,40,5)
            water = st.slider("NDWI / MNDWI water screening threshold",-.2,.4,0.0,.05)
        with c3:
            quake_radius = st.slider("Earthquake search radius (km)",25,500,150,25)
            magnitude = st.slider("Minimum earthquake magnitude",0.0,7.0,2.5,.5)
            st.caption("Earthquake radius is separate from the study boundary. GBIF retrieval is limited to 300 candidate records.")
    if "US weather alerts" in selected:
        st.info("The official alert adapter supports US NWS coverage. Outside that area, check your national authority; an empty response does not mean no hazard.")
    if st.button("Run environmental analysis",type="primary",width="stretch",disabled=study is None):
        if not selected:
            st.warning("Select at least one module.")
        else:
            options = {"modules":selected,"baseline":baseline,"flow_threshold":flow,"scene_count":scenes,
                       "cloud_limit":cloud,"water_threshold":water,"quake_radius":quake_radius,"min_magnitude":magnitude}
            with st.status("Gathering evidence…",expanded=True) as status:
                run = execute_analysis(study,options,lambda text: st.write(text))
                st.session_state["run"] = run
                st.session_state.pop("exports",None)
                st.session_state.pop("crew_review",None)
                status.update(label=f"{len(run['results'])} modules completed · {len(run['errors'])} unavailable",state="complete" if run["results"] else "error",expanded=False)
            for name, error in run["errors"].items():
                st.warning(f"{name}: {error}")
            if run["results"]:
                st.success("Analysis saved for this session. Open the result pages or generate your report.")
                st.button("Explore satellite & water",on_click=go_page,args=("Satellite & water",))


def need_run(run):
    if run:
        st.caption(f"Viewing run {run['id']} · {run['study']['label']} · historical period {run['study']['start']} to {run['study']['end']}")
        return True
    st.info("Run an analysis first. Each results page uses the saved study boundary and dates.")
    st.button("Set up your study",type="primary",on_click=go_page,args=("Study & analysis",))
    return False


def module_view(run, module, charts=True):
    r = run["results"].get(module)
    if not r:
        message = run["errors"].get(module,"This module was not selected in the saved analysis.")
        st.info(f"{module}: {message}")
        return
    st.subheader(module)
    metrics = list(r["metrics"].items())
    if metrics:
        cols = st.columns(min(3,len(metrics)))
        for i,(name,value) in enumerate(metrics):
            cols[i%len(cols)].metric(name,fmt(value,1))
    for fact in r["facts"]:
        st.write(fact)
    if charts:
        for spec in chart_specs(run):
            if spec["module"] == module:
                st.markdown(f"**{spec['title']}**")
                st.plotly_chart(interactive_chart(spec),width="stretch",key=f"chart-{module}-{spec['table']}-{spec['ys'][0]}")
                st.caption("Evidence: " + spec["evidence"])
    with st.expander("Data tables and CSV downloads"):
        for title,frame in r["tables"].items():
            st.markdown(f"**{title}** · {len(frame):,} rows")
            st.dataframe(frame,width="stretch",hide_index=True)
            st.download_button("Download " + title,safe_frame(frame).to_csv(index=False).encode("utf-8-sig"),
                file_name=re.sub(r"\W+","_",title.lower())+".csv",mime="text/csv",key=f"csv-{module}-{title}")
    with st.expander("Methods, coverage and limitations",expanded=module in ["Satellite","River outlook"]):
        for note in r["notes"]:
            st.write("• " + note)
        st.dataframe(pd.DataFrame(r["sources"]),width="stretch",hide_index=True)


def satellite_page(run):
    banner("Satellite & water","Surface observations, optical screening and areas to investigate.")
    if not need_run(run):
        return
    r = run["results"].get("Satellite",{}).get("raster")
    if r:
        available_layers = [name for name in RASTER_STYLES if np.isfinite(r["arrays"][name]).any()]
        if r["summary"]["water_pixels"] == 0:
            st.warning("No pixels passed the water screen in the latest scene. NDCI and water reflectance are unavailable. Inspect the boundary, true-colour image, an earlier date and the screening settings; do not interpret this as clean or absent water.")
        if r["summary"]["valid_aoi_percent"] < 50:
            st.warning(f"Latest usable coverage: {r['summary']['valid_aoi_percent']:.1f}% of the study area. The masked portion has no usable result.")
        layer = st.selectbox("Map layer", available_layers) if available_layers else None
        show_map(map_for_run(run,["Satellite","Field observations"],layer),f"sat-map-{run['id']}-{layer}",height=530)
        st.caption(f"Actual processed satellite layer · {r['summary']['date']} · {r['resolution']} m common grid. Blank pixels are masked/no data. Golden points are unverified sampling candidates.")
        with st.expander("True-colour view and exportable GIS raster"):
            st.image(raster_png(r,"True colour"),width="stretch")
            st.download_button("Download all indices as GeoTIFF",geotiff_bytes(r),file_name="aquaterra_satellite_indices.tif",mime="image/tiff")
    module_view(run,"Satellite")
    st.info("For measured eutrophication indicators, upload field samples on Ecology & field. Satellite indices alone do not establish nutrient concentration, toxicity or drinking-water safety.")


def climate_page(run):
    banner("Climate & air","Historical context and clearly dated model forecasts.")
    if need_run(run):
        module_view(run,"Climate")
        st.divider()
        module_view(run,"Air quality")


def hazards_page(run):
    banner("Hazards & outlooks","River-flow forecasts, earthquake observations and supported official alerts.")
    if not need_run(run):
        return
    st.warning("AquaTerra is a research workbench. Discharge forecasts are not inundation maps; earthquake event histories do not predict future events.")
    choice = st.radio("Hazard view",["River outlook","Earthquakes","US weather alerts"],horizontal=True)
    if choice == "Earthquakes" and choice in run["results"]:
        show_map(map_for_run(run,["Earthquakes"]),"earthquake-map-"+run["id"])
        st.caption("Bubble radius follows catalogue magnitude; event depth and magnitude are available on hover. The catalogue may omit smaller events.")
    module_view(run,choice)
    st.markdown("Official Pakistan advisories: [PMD](https://www.pmd.gov.pk/) · [NDMA](https://www.ndma.gov.pk/). Official US alerts: [National Weather Service](https://www.weather.gov/).")


def ecology_page(run):
    banner("Ecology & citizen evidence","Connect recorded biodiversity with measurements collected on the ground.")
    if not need_run(run):
        return
    st.subheader("Add field measurements")
    st.caption("Required columns: site, date, latitude, longitude. Optional measurement names include their units. Use blanks for missing values.")
    template = ",".join(FIELD_COLUMNS)+"\n"
    st.download_button("Download blank field CSV template",template,"field_samples_template.csv","text/csv")
    samples = st.file_uploader("Upload field observations (CSV)",type=["csv"],key="field_csv")
    lake = st.checkbox("Calculate separate Carlson indices for appropriate lake / reservoir samples",False)
    if st.button("Validate and attach observations",disabled=samples is None):
        try:
            observations = parse_field_csv(samples.getvalue(),run["study"],lake)
            run["results"]["Field observations"] = observations
            run["field_updated_utc"] = utc_now()
            st.session_state["run"] = run
            st.session_state.pop("exports",None)
            st.session_state.pop("crew_review",None)
            st.success("Observations attached to this run. Out-of-area/date rows are retained in the audit table and excluded from analysis.")
        except DataError as exc:
            st.error(str(exc))
    if "Field observations" in run["results"]:
        if st.button("Remove attached observations"):
            del run["results"]["Field observations"]
            st.session_state.pop("exports",None)
            st.session_state.pop("crew_review",None)
            st.rerun()
    show_map(map_for_run(run,["Biodiversity","Field observations","Satellite"]),"ecology-map-"+run["id"])
    st.caption("Uploaded chlorophyll measurements use proportional bubble areas, capped for readability. Species points show recorded observations; sampling candidates remain unverified.")
    module_view(run,"Field observations")
    module_view(run,"Biodiversity")


def ai_page(run):
    st.title("Your five-agent environmental team")
    st.caption("CrewAI · Sequential workflow · Coordinator, three specialists, then evidence review and report writing.")
    st.dataframe(pd.DataFrame([{"Agent": role, "Responsibility": description} for _,role,description in AGENT_ROSTER]),
                 hide_index=True, width="stretch")
    enabled = ["gemini", "openrouter", "groq"]
    if secret("ENABLE_OLLAMA", "false").lower() in {"true", "1", "yes"}:
        enabled.append("ollama")
    configured = secret("AI_PROVIDER", DEFAULT_PROVIDER).lower()
    if configured not in enabled:
        configured = DEFAULT_PROVIDER
    provider = st.selectbox("AI provider", enabled, index=enabled.index(configured),
                            format_func=lambda value: PROVIDERS[value]["label"], key="ai_provider")
    info = PROVIDERS[provider]
    base_url = secret("OLLAMA_BASE_URL", info["base_url"]) if provider == "ollama" else None
    with st.expander("AI connection and privacy", expanded=True):
        key = secret(info["key_name"])
        if not key and provider != "ollama":
            key = st.text_input(info["label"] + " API key (private, session only)", type="password",
                                key="_provider_key_" + provider)
        if provider == "ollama":
            st.info("Ollama uses the owner's configured endpoint. On Streamlit Cloud, localhost refers to the cloud server, not your laptop. See LOCAL_OLLAMA.md for a local installation.")
        model = st.text_input("Model ID", value=secret(info["model_name"], info["model"]), key="model_" + provider)
        st.caption(info["note"])
        st.markdown(f"[Provider setup]({info['key_url']}) · [Usage limits]({info['limits_url']})")
        if provider == "gemini":
            st.caption("Google's free-tier terms allow submitted data to be used to improve products. Use an appropriate service agreement before sending confidential research data.")
        def bounded_setting(name, default, minimum, maximum):
            try:
                return max(minimum, min(maximum, int(secret(name, str(default)))))
            except (TypeError, ValueError):
                return default
        tokens_per_minute = st.number_input("Estimated token budget per minute", min_value=2000, max_value=1000000,
            value=bounded_setting("AI_TOKENS_PER_MINUTE", info["tpm"], 2000, 1000000), step=1000, key="tpm_" + provider,
            help="Set at or below your account's allowance. Input plus reserved output is estimated conservatively. This setting cannot increase your provider quota.")
        requests_per_minute = st.number_input("Maximum requests per minute", min_value=1, max_value=120,
            value=bounded_setting("AI_REQUESTS_PER_MINUTE", info["rpm"], 1, 120), key="rpm_" + provider,
            help="All five agents share this pacing limit. Daily limits and other apps using the same provider project still apply.")
        connected = bool(key) or provider == "ollama"
        st.caption("Maps, calculations and standard reports work without an AI key. The selected AI service receives study coordinates, question, summaries and statistics requested by the agents, including some table previews. Whole uploaded files and raw rasters are not sent. Keys are excluded from reports.")
        if st.button("Test AI connection", disabled=not connected):
            try:
                from crew_runtime import ProviderEvidenceLLM, RunBudget
                with st.spinner("Sending one short connection-test request…"):
                    llm = ProviderEvidenceLLM(key, model, RunBudget(max_calls=1, seconds=70),
                        tokens_per_minute=int(tokens_per_minute), provider=provider,
                        requests_per_minute=int(requests_per_minute), base_url=base_url)
                    llm.call("Reply with the word CONNECTED. This is a connection test; there is no study data.")
                st.success("The selected provider returned a usable response. This test used one API request.")
            except Exception as exc:
                st.error(str(exc) if type(exc).__name__ == "CrewRunError" else "Connection test failed. Check provider credentials, model access and installed dependencies.")
        if not connected:
            st.info(f"Add a private key here or set {info['key_name']} in Streamlit Secrets.")
    if not need_run(run):
        return
    with st.expander("Evidence coverage before AI review"):
        st.dataframe(pd.DataFrame(quality_findings(run)),hide_index=True,width="stretch")
    consent = st.checkbox(f"Allow this run's summaries, study coordinates and requested statistics to be sent to {info['label']}",False,key="ai_consent_"+provider)
    question = st.text_area("Question for the team",value="Assess this study using its saved evidence. If Research validation is available, inspect the recorded statistical tables and validation limitations. Distinguish measured values, satellite indicators and estimates; report missing evidence and practical next steps.",height=120,max_chars=2000)
    st.caption("The team reviews the saved analysis. Run new environmental analysis to change location, dates or source data. A review can take several minutes while API requests are paced.")
    force_new = st.checkbox("Generate a fresh review even if a completed review already matches", False,
                            help="Leave off to reuse the last completed review for identical evidence, question, provider and model.")
    previous = st.session_state.get("crew_review", {})
    reusable = (previous.get("status") == "complete" and previous.get("fingerprint") == run_fingerprint(run)
                and previous.get("question") == question.strip() and previous.get("provider") == provider
                and previous.get("model") == model)
    if st.button("Run five-agent review",type="primary",disabled=not consent or not connected or not run["results"]):
        if not question.strip():
            st.warning("Enter a question first.")
        elif reusable and not force_new:
            st.success("Reused the completed review for this evidence and question; no new API requests were sent.")
        else:
            try:
                import crew_workflow
                crew_workflow.make_tools = research_agent_tools
                from crew_workflow import run_team
                from crew_runtime import CrewRunError
                with st.status("The five-agent review is running…",expanded=True) as status:
                    def progress(event):
                        if event["event"] == "completed":
                            status.write(f"{event['stage']}/5 complete — {event['role']}")
                        elif event["event"] == "rate_pause":
                            status.update(label=f"Pacing API requests — approximately {event['seconds']} seconds until the next slot")
                        elif event["event"] == "model_request":
                            status.update(label=f"Review in progress — model request {event['call']}")
                    # CrewAI may invoke callbacks on its own worker threads.
                    # Only the Streamlit script thread may update the interface.
                    events = queue.Queue()
                    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="aquaterra-review") as pool:
                        future = pool.submit(run_team,run,question.strip(),key,model,int(tokens_per_minute),events.put,
                                             provider=provider,requests_per_minute=int(requests_per_minute),base_url=base_url)
                        while not future.done():
                            try:
                                progress(events.get(timeout=.15))
                            except queue.Empty:
                                pass
                        while not events.empty():
                            progress(events.get_nowait())
                        review = future.result()
                    status.update(label="Five-agent review complete" if review["status"] == "complete" else "Review stopped; partial notes retained",
                                  state="complete" if review["status"] == "complete" else "error",expanded=False)
                st.session_state["crew_review"] = review
                st.session_state.pop("exports",None)
            except ImportError:
                st.error("CrewAI is not installed correctly. Upload this package's requirements.txt and all Python files, then reboot the app.")
            except (DataError, ValueError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(str(exc) if type(exc).__name__ == "CrewRunError" else "The AI team could not start. Check the supplied files, dependency versions and AI provider settings. Environmental results are preserved.")
    reply = st.session_state.get("crew_review")
    if reply and reply.get("fingerprint") != run_fingerprint(run):
        st.info("The saved AI review belongs to different evidence. Run the team again for this analysis.")
    elif reply:
        if reply["status"] == "complete":
            st.markdown(reply["answer"])
            st.success("All five agents completed. The AI narrative can now be included under Reports & sources.")
        else:
            st.warning(reply.get("error", "The AI review did not complete."))
            st.caption("These are partial agent notes, not a completed final review.")
        st.caption("AI-generated interpretation. The reviewer checks available evidence but does not independently validate scientific accuracy. Verify cited findings before sharing.")
        for note in reply.get("agent_outputs",[]):
            with st.expander(note["role"]):
                st.markdown(note["text"])
        with st.expander("Team activity and request usage"):
            st.write({"provider":reply.get("provider"),"requested_model":reply.get("model"),"returned_models":reply.get("actual_models",[])})
            st.json(reply.get("usage",{}))
            st.dataframe(pd.DataFrame(reply.get("activity",[])),hide_index=True,width="stretch")
        st.download_button("Download agent review and activity",json.dumps(reply,indent=2,ensure_ascii=False),
                           "aquaterra_five_agent_review.json","application/json")
        if reply["status"] == "complete":
            st.download_button("Download final AI narrative",reply["answer"],"aquaterra_ai_review.md","text/markdown")
    st.subheader("Evidence available without AI")
    for r in run["results"].values():
        for fact in r["facts"]:
            st.write(fact)


@st.cache_resource
def report_lock():
    return threading.Lock()


def reports_page(run):
    st.title("Reports & source records")
    st.caption("A shareable report, full data tables and GIS-ready layers from the same saved analysis.")
    if not need_run(run):
        return
    c1,c2,c3 = st.columns(3)
    c1.metric("Completed modules",len(run["results"]))
    c2.metric("Data tables",len(all_tables(run)))
    c3.metric("Source records",len(all_sources(run)))
    st.write("The report includes findings, maps, charts, table previews, methods, limitations and source records. The complete ZIP includes every returned table, PNG figures, GeoJSON, metadata and a GeoTIFF when satellite processing succeeds.")
    review = st.session_state.get("crew_review")
    include_ai = False
    if review_is_current(run,review):
        include_ai = st.checkbox("Include the completed five-agent AI review",value=True)
    else:
        st.caption("Run the team under AI team to add a completed AI narrative. The standard evidence report is available now.")
    export_run = {**run, "crew_review": review} if include_ai else run
    export_key = (run_fingerprint(run), review.get("generated_utc") if include_ai else None)
    if st.button("Generate report & export package",type="primary",width="stretch"):
        try:
            with st.spinner("Rendering charts, maps, PDF and workbook…"):
                with report_lock():
                    exports = build_exports(export_run)
            st.session_state["exports"] = {"run":run["id"],"export_key":export_key,"files":exports}
        except Exception as exc:
            st.error(f"Export could not complete ({type(exc).__name__}). Your analysis is still available. Individual CSV and GeoTIFF downloads can be used while the report issue is resolved.")
    bundle = st.session_state.get("exports")
    if bundle and bundle.get("export_key") == export_key:
        ex = bundle["files"]
        c1,c2,c3,c4 = st.columns(4)
        suffix = run["id"]
        c1.download_button("Complete ZIP",ex["zip"],f"aquaterra_{suffix}.zip","application/zip",width="stretch",type="primary")
        c2.download_button("PDF report",ex["pdf"],f"aquaterra_{suffix}.pdf","application/pdf",width="stretch")
        c3.download_button("HTML report",ex["html"],f"aquaterra_{suffix}.html","text/html",width="stretch")
        c4.download_button("Excel data",ex["xlsx"],f"aquaterra_{suffix}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",width="stretch")
        st.success("Exports are ready. Download them before ending the session; this MVP does not provide a persistent project database.")
    lab=st.session_state.get("research_"+run["id"])
    if lab and lab.get("records"):
        st.info("This study also has recorded research analyses. Their figures, processed raster windows and offline replay code are in Research workspace → Methods & downloads.")
        st.button("Open research methods and downloads",on_click=go_page,args=("Research workspace",))
    st.subheader("Provenance")
    st.dataframe(pd.DataFrame(all_sources(run)),width="stretch",hide_index=True)
    st.download_button("Download run metadata",json.dumps(plain_metadata(run),indent=2,default=str),"metadata.json","application/json")
    if run["errors"]:
        st.subheader("Unavailable modules")
        for module,error in run["errors"].items():
            st.warning(f"{module}: {error}")
    with st.expander("Data access, attribution and operational limits"):
        st.write("Open-Meteo hosted free access is for non-commercial use and has quotas. Include attribution to Open-Meteo and the underlying data providers. Sentinel imagery: Copernicus Sentinel data via Earth Search. GBIF records retain contributor and licence fields. Maps: © OpenStreetMap contributors. ")
        st.write("The app caches public provider responses and limits retries and satellite processing. Satellite scenes may be old or cloudy, and coarse model grids cannot resolve every local condition. Baselines, forecasts and observations are labelled separately.")
        st.write("Scope: bounded-area research MVP. Persistent multi-user projects, validated local flood models, calibrated water-quality concentrations and autonomous emergency alerts require additional infrastructure and validation.")
        st.markdown("[Open-Meteo terms](https://open-meteo.com/en/terms) · [Open-Meteo pricing/access](https://open-meteo.com/en/pricing) · [OpenStreetMap attribution](https://www.openstreetmap.org/copyright)")


def main():
    st.set_page_config(page_title="AquaTerra Research AI | Environmental intelligence",layout="wide",initial_sidebar_state="expanded")
    inject_theme()
    for key,value in {"study_label":"Rawal Lake, Islamabad","study_lat":33.700,"study_lon":73.120,"page":"Overview","use_boundary":False}.items():
        if key not in st.session_state:
            st.session_state[key] = value
    with st.sidebar:
        st.html("<div class='eco-brand'><div><strong>AquaTerra <span style='color:#72E2C9'>Research AI</span></strong><small>Water · Ecology · Climate</small></div></div>")
        page = st.radio("Workspace",list(PAGES[:-2])+["Research workspace"]+list(PAGES[-2:]),key="page",label_visibility="collapsed")
        st.divider()
        run = st.session_state.get("run")
        if run:
            st.caption("SAVED ANALYSIS")
            st.markdown(f"**{run['study']['label']}**")
            st.caption(f"{run['study']['start']} → {run['study']['end']}")
            st.caption(f"{len(run['results'])} modules · {len(run['errors'])} unavailable")
            st.caption("Retrieved times appear in source records.")
        else:
            st.caption("READY WHEN YOU ARE")
            st.write("Begin with a place and a question.")
        st.divider()
        st.caption(f"{APP_RELEASE} · CrewAI · 5 agents")
        st.caption("Open data • Reproducible methods • Clear uncertainty")
    c1, c2, c3 = st.columns([2.6, 1, 1])
    c1.caption(f"AQUATERRA RESEARCH AI {APP_RELEASE} · {page}")
    c2.button("AI team", width="stretch", key="always-ai", on_click=go_page, args=("AI team",))
    c3.button("Study setup", width="stretch", key="always-study", on_click=go_page, args=("Study & analysis",))
    if run and run.get("version") != VERSION:
        st.warning("This saved analysis was generated by an earlier app version. Run environmental analysis again before using the new AI team and reports.")
        run = None
    if page == "Overview": overview(run)
    elif page == "Study & analysis": study_page()
    elif page == "Satellite & water": satellite_page(run)
    elif page == "Climate & air": climate_page(run)
    elif page == "Hazards": hazards_page(run)
    elif page == "Ecology & field": ecology_page(run)
    elif page == "Research workspace": research_page(run)
    elif page == "AI team": ai_page(run)
    else: reports_page(run)




# RESEARCH_ENGINE_START
# This exact block is included in the offline reproduction package.
RESEARCH_ENGINE_VERSION = "2026.09.30.1"
RESEARCH_NUMERIC = ["chlorophyll_ug_l", "turbidity_ntu", "secchi_m", "temperature_c",
    "total_phosphorus_ug_l", "total_nitrogen_mg_l", "dissolved_oxygen_mg_l", "ph",
    "phycocyanin_ug_l", "cyanobacteria_cells_ml"]
RESEARCH_METHODS = {
    "clean": "Row audit; explicit column mapping and units; UTC conversion; invalid numeric cells become missing and are recorded. No outlier removal or imputation.",
    "correlation": "Pearson product-moment and Spearman average-rank correlation. Optional permutation inference and paired percentile bootstrap assume independent rows; BH adjustment is across the displayed tests.",
    "regression": "Intercept plus ordinary least-squares or penalized additive cubic regression splines (Gaussian response, identity link). Complete cases; no automated variable selection. Split by entire groups before fitting/scaling/knots.",
    "pca": "Complete-case PCA by SVD of centered sample-standardized variables. Constant variables are excluded. This is exploratory ordination, not a significance test.",
    "rda": "Hellinger-transformed community matrix, centered response; centered and standardized environmental constraints. Multivariate least squares followed by SVD of fitted responses; optional unrestricted row permutation requires independent samples.",
    "community": "Taxon-by-sample abundance matrix; explicit absent-taxon policy. Richness, Shannon natural-log diversity, Simpson 1-sum(p^2), Pielou evenness and Bray-Curtis dissimilarity. No mixing of abundance units or taxonomic ranks.",
    "cluster": "Average-linkage agglomeration on Euclidean distance of standardized environmental variables or Bray-Curtis distance of nonnegative community abundance. Exploratory groups; average silhouette is descriptive.",
    "seasonal": "Per-site monthly observed means with no gap filling. Classical additive decomposition: centered 2x12 moving-average trend, zero-centered monthly seasonal effect, remainder. Requires at least 24 consecutive observed months; edge trend remains missing.",
    "agreement": "Paired comparison of an explicitly identified concentration/temperature estimate with a field reference in the same units: bias=estimate-reference, MAE, RMSE and predictive R². No automatic declaration of acceptable performance.",
}


def research_json(value):
    def clean(x):
        if isinstance(x, dict): return {str(k): clean(v) for k,v in x.items()}
        if isinstance(x, (list,tuple)): return [clean(v) for v in x]
        if isinstance(x, np.ndarray): return clean(x.tolist())
        if isinstance(x, np.generic): return clean(x.item())
        if isinstance(x, float) and not math.isfinite(x): return None
        if x is pd.NA or x is pd.NaT: return None
        return x
    return json.dumps(clean(value), ensure_ascii=False, sort_keys=True, default=str, allow_nan=False)


def research_frame_json(frame):
    return frame.to_json(orient="split",date_format="iso",double_precision=15,default_handler=str)


def research_clean(frame, settings):
    if len(frame)>10000 or len(frame.columns)>80:
        raise ValueError("Use at most 10,000 rows and 80 columns per worksheet.")
    mapping_columns=settings["mapping"]
    result=pd.DataFrame(index=range(len(frame)))
    for dest,source in mapping_columns.items():
        if source and source in frame: result[dest]=frame[source].reset_index(drop=True)
    if not {"site","date"}.issubset(result): raise ValueError("Map a site column and a sampling date column.")
    result["source_row"]=np.arange(len(result))+2
    result["site"]=result.site.fillna("").astype(str).str.strip()
    if "sample_id" not in result: result["sample_id"]=[f"sample-{i+1:05d}" for i in range(len(result))]
    result["sample_id"]=result.sample_id.fillna("").astype(str).str.strip()
    issues=[[] for _ in range(len(result))]
    timestamps=[]; known=[]; local_dates=[]
    for i,v in enumerate(result.date):
        text=str(v)
        time_known=bool(re.search(r"(?:T|\s)\d{1,2}:\d{2}",text))
        if isinstance(v,(datetime,pd.Timestamp)) and v.hour==0 and v.minute==0:
            time_known=False
        if settings.get("time_precision")=="Date only": time_known=False
        if settings.get("time_precision")=="Exact times supplied": time_known=True
        try:
            if pd.isna(v) or isinstance(v,(int,float,np.number)): raise ValueError("Missing or serial date")
            ts=pd.to_datetime(v,dayfirst=bool(settings.get("dayfirst")),errors="raise")
            if ts.tzinfo is None: ts=ts.tz_localize(settings.get("timezone","UTC"),ambiguous="raise",nonexistent="raise")
            local_dates.append(ts.date().isoformat())
            ts=ts.tz_convert("UTC")
            timestamps.append(ts.isoformat()); known.append(time_known)
        except (ValueError,TypeError,OverflowError):
            timestamps.append(None);known.append(False);local_dates.append("");issues[i].append("invalid or ambiguous date")
    result["date"]=timestamps
    result["sampling_time_known"]=known
    result["sampling_date_local"]=local_dates
    result["sampling_timezone"]=settings.get("timezone","UTC")
    numeric=[c for c in ["latitude","longitude","depth_m",*RESEARCH_NUMERIC] if c in result]
    for c in numeric:
        original=result[c]
        v=pd.to_numeric(original,errors="coerce").replace([np.inf,-np.inf],np.nan)
        bad=original.notna() & original.astype(str).str.strip().ne("") & v.isna()
        if c in RESEARCH_NUMERIC and c not in ("temperature_c","ph"): bad |= v.lt(0)
        if c=="depth_m": bad |= v.lt(0)
        if c=="ph": bad |= v.notna() & ~v.between(0,14)
        if c=="latitude": bad |= v.notna() & ~v.between(-90,90)
        if c=="longitude": bad |= v.notna() & ~v.between(-180,180)
        for i in result.index[bad]: issues[i].append(f"invalid {c}; set missing")
        result[c]=v.mask(bad)
    if "latitude" not in result: result["latitude"]=np.nan
    if "longitude" not in result: result["longitude"]=np.nan
    coord_ok=result.latitude.notna() & result.longitude.notna()
    dates=pd.to_datetime(result.date,utc=True,errors="coerce")
    in_period=pd.Series(local_dates).between(settings["start"],settings["end"])
    inside=np.zeros(len(result),bool)
    polygon=shape(settings["geometry"])
    for i in result.index[coord_ok]: inside[i]=polygon.covers(Point(float(result.at[i,"longitude"]),float(result.at[i,"latitude"])))
    duplicates=result.sample_id.duplicated(keep=False)
    for i in result.index:
        if not result.at[i,"site"]: issues[i].append("missing site")
        if not result.at[i,"sample_id"]: issues[i].append("missing sample ID")
        if duplicates[i]: issues[i].append("duplicate sample ID; excluded until resolved")
        if not in_period[i]: issues[i].append("outside study period or invalid date")
        if not coord_ok[i]: issues[i].append("coordinates missing; satellite matching unavailable")
        elif not inside[i]: issues[i].append("outside study boundary")
        if not known[i]: issues[i].append("sampling time unknown")
    result["included"]=in_period & result.site.ne("") & result.sample_id.ne("") & ~duplicates & (~coord_ok | inside)
    result["satellite_eligible"]=result.included & coord_ok & inside
    result["inside_study"]=inside
    result["quality_flags"]=["; ".join(x) or "basic checks passed; laboratory accuracy not verified" for x in issues]
    # Robust outlier flags are informational only; no row is discarded for its magnitude.
    outliers=[]
    for c in RESEARCH_NUMERIC:
        if c not in result: continue
        v=result.loc[result.included,c].dropna()
        if len(v)<8: continue
        med=float(v.median());mad=float((v-med).abs().median())
        if mad>0:
            for i in result.index[(.67448975*(result[c]-med).abs()/mad)>3.5]:
                outliers.append({"sample_id":result.at[i,"sample_id"],"column":c,"value":result.at[i,c],"action":"Flag only; retained"})
    return {"tables":{"Cleaned observations":result,"Outlier flags":pd.DataFrame(outliers)},
            "notes":["Uploaded measurements are reference observations, not independently verified laboratory results.",
                     "No automatic unit conversion. Mapped measurement columns must use the units in their destination names.",
                     "Rows without coordinates remain usable for nonspatial statistics; they cannot support satellite matching."],"plots":[]}


def research_complete(frame, columns, minimum=3):
    if not columns or not set(columns).issubset(frame): raise ValueError("Select available numeric columns.")
    v=frame[columns].apply(pd.to_numeric,errors="coerce").replace([np.inf,-np.inf],np.nan)
    mask=v.notna().all(axis=1)
    if int(mask.sum())<minimum: raise ValueError(f"Need at least {minimum} complete rows for this calculation.")
    return frame.loc[mask].copy(),v.loc[mask].to_numpy(dtype=float)


def research_r(x,y):
    x=np.asarray(x,float);y=np.asarray(y,float)
    a=x-x.mean();b=y-y.mean();den=np.linalg.norm(a)*np.linalg.norm(b)
    return float(np.dot(a,b)/den) if den>1e-14 else np.nan


def research_bh(pvalues):
    p=np.asarray(pvalues,float);out=np.full(len(p),np.nan);ix=np.where(np.isfinite(p))[0]
    if len(ix):
        order=ix[np.argsort(p[ix])]
        out[order]=np.minimum(1,np.minimum.accumulate((p[order]*len(order)/np.arange(1,len(order)+1))[::-1])[::-1])
    return out


def research_metrics(y,pred):
    y=np.asarray(y,float);pred=np.asarray(pred,float);err=pred-y;den=np.sum((y-y.mean())**2)
    return {"n":len(y),"bias_estimate_minus_reference":float(err.mean()),"MAE":float(np.abs(err).mean()),
        "RMSE":float(np.sqrt(np.mean(err**2))),"predictive_R2":float(1-np.sum(err**2)/den) if den>0 else np.nan}


def research_basis(x,meta=None,mode="Linear"):
    x=np.asarray(x,float)
    if meta is None:
        scale=np.std(x,axis=0,ddof=1)
        if np.any(scale<1e-12): raise ValueError("Predictors must vary in the training data.")
        meta={"mean":x.mean(axis=0).tolist(),"scale":scale.tolist(),"mode":mode}
        z=(x-np.array(meta["mean"]))/scale
        meta["knots"]=[np.unique(np.quantile(z[:,j],[.2,.4,.6,.8])).tolist() for j in range(x.shape[1])]
    z=(x-np.array(meta["mean"]))/np.array(meta["scale"])
    cols=[np.ones(len(x))];penalties=[0.];names=["intercept"]
    for j in range(x.shape[1]):
        cols.append(z[:,j]);penalties.append(0.);names.append(f"x{j+1}")
        if meta["mode"]!="Linear":
            for k in meta["knots"][j]:
                cols.append(np.maximum(z[:,j]-k,0)**3);penalties.append(1.);names.append(f"x{j+1}_knot_{k:.6g}")
    return np.column_stack(cols),np.array(penalties),meta,names


def research_regression(frame,s):
    xs=s["predictors"];yname=s["response"]
    if yname in xs: raise ValueError("The response cannot also be a predictor.")
    f,xy=research_complete(frame,[*xs,yname],minimum=12)
    group=s.get("group")
    if not group or group not in f: raise ValueError("Choose a site, scene or date column for held-out group validation.")
    g=f[group].astype(str)
    if f[group].isna().any(): raise ValueError("Validation groups contain missing values.")
    if group in ("date","acquisition_utc"): g=pd.to_datetime(g,utc=True,errors="raise").dt.strftime("%Y-%m-%d")
    groups=np.array(sorted(g.unique()))
    if len(groups)<4: raise ValueError("Need at least four distinct groups. With fewer groups, use exploratory correlations or collect more independent observations.")
    rng=np.random.default_rng(s.get("seed",42));rng.shuffle(groups)
    ng=max(1,int(math.ceil(len(groups)*.25)))
    test=g.isin(groups[:ng]).to_numpy();train=~test
    if train.sum()<max(8,2*len(xs)+3) or test.sum()<3: raise ValueError("The group split leaves too few training or evaluation rows.")
    if "support_id" in f:
        overlap=set(f.loc[train,"support_id"].dropna()) & set(f.loc[test,"support_id"].dropna())
        if overlap: raise ValueError("The same satellite pixel support occurs in both partitions. Split by scene_id instead.")
        if f.support_id.dropna().duplicated().any():
            raise ValueError("Repeated samples share satellite support. Aggregate legitimate field replicates before model validation.")
    x=xy[:,:-1];y=xy[:,-1]
    b,pen,meta,names=research_basis(x[train],mode=s.get("model","Linear"))
    if s.get("model","Linear")=="Linear" and np.linalg.matrix_rank(b)<b.shape[1]:
        raise ValueError("Predictors are collinear; choose fewer independent predictors.")
    lam=float(s.get("smoothing",1.0)) if s.get("model","Linear")!="Linear" else 0.
    matrix=b.T@b+lam*np.diag(pen)
    coef=np.linalg.pinv(matrix)@b.T@y[train]
    all_b,_,_,_=research_basis(x,meta)
    pred=all_b@coef
    p=f.copy();p["reference"]=y;p["estimate"]=pred;p["residual_estimate_minus_reference"]=pred-y
    p["partition"]=np.where(test,"Held-out evaluation","Calibration")
    p["outside_training_predictor_range"]=np.any((x<x[train].min(axis=0)) | (x>x[train].max(axis=0)),axis=1)
    p["negative_estimate"]=pred<0
    metrics=[]
    for label,mask in [("Calibration",train),("Held-out evaluation",test)]:
        metrics.append({"partition":label,**research_metrics(y[mask],pred[mask])})
    meta.update({"predictors":xs,"response":yname,"smoothing":lam,"coefficients":coef.tolist(),
        "group_column":group,"held_out_groups":groups[:ng].tolist(),"training_groups":groups[ng:].tolist(),
        "effective_df":float(np.trace(np.linalg.pinv(matrix)@(b.T@b))),"training_condition_number":float(np.linalg.cond(b)),
        "validation_status":"Held-out groups evaluated; inspect errors. No automatic acceptability claim.",
        "training_min":x[train].min(axis=0).tolist(),"training_max":x[train].max(axis=0).tolist()})
    return {"tables":{"Model predictions":p,"Model performance":pd.DataFrame(metrics),
        "Model coefficients":pd.DataFrame({"term":names,"coefficient":coef})},"model":meta,
        "notes":[f"Complete rows: {len(f)}/{len(frame)}. Split, scaling and knots were fitted using calibration groups only.",
        "Held-out groups come from this uploaded dataset; they are not an independent external study.",
        "Predictions outside the training range and negative estimates are flagged, not clipped. Review optical conditions and residuals before transferring a model.",
        "P-values and causal interpretations are not provided for this fitted model. Spline smoothing is a declared parameter, not a claim of optimal fit."],
        "plots":[{"kind":"scatter","table":"Model predictions","x":"reference","y":"estimate","group":"partition","title":f"{yname}: reference versus estimate","one_to_one":True},
                 {"kind":"scatter","table":"Model predictions","x":"estimate","y":"residual_estimate_minus_reference","group":"partition","title":"Residual diagnostics"}]}


def research_community(frame,s):
    required={"sample_id","taxon","abundance"}
    if not required.issubset(frame): raise ValueError("Community data require sample_id, taxon and abundance columns.")
    f=frame.copy()
    if f[list(required)].isna().any().any(): raise ValueError("Missing community cells are not zeros. Resolve missing sample IDs, taxa or abundance.")
    f["sample_id"]=f.sample_id.astype(str).str.strip();f["taxon"]=f.taxon.astype(str).str.strip()
    if f.sample_id.eq("").any() or f.taxon.eq("").any(): raise ValueError("Sample and taxon names cannot be blank.")
    f["abundance"]=pd.to_numeric(f.abundance,errors="coerce")
    if f.abundance.isna().any() or not np.isfinite(f.abundance).all() or f.abundance.lt(0).any(): raise ValueError("Abundance must be finite, nonnegative numbers.")
    if f.duplicated(["sample_id","taxon"]).any(): raise ValueError("Duplicate sample/taxon pairs: resolve replicates explicitly before analysis.")
    if f.taxon.eq("sample_id").any(): raise ValueError("A taxon cannot use the reserved name sample_id.")
    matrix=f.pivot(index="sample_id",columns="taxon",values="abundance")
    if matrix.size>200000: raise ValueError("Reduce the community matrix to at most 200,000 cells.")
    if matrix.isna().any().any():
        if not s.get("unlisted_absent"): raise ValueError("Unlisted taxa may be missing observations. Confirm the survey searched for all taxa before filling unlisted combinations with zero.")
        matrix=matrix.fillna(0.)
    a=matrix.to_numpy(float);total=a.sum(axis=1);positive=total>0
    prop=np.divide(a,total[:,None],out=np.zeros_like(a),where=total[:,None]>0)
    richness=(a>0).sum(axis=1)
    logs=np.zeros_like(prop);np.log(prop,out=logs,where=prop>0)
    shannon=-(prop*logs).sum(axis=1)
    evenness=np.full(len(a),np.nan);ok=richness>1;evenness[ok]=shannon[ok]/np.log(richness[ok])
    shannon[~positive]=np.nan
    simpson=1-(prop**2).sum(axis=1);simpson[~positive]=np.nan
    diversity=pd.DataFrame({"sample_id":matrix.index,"total_abundance":total,"richness":richness,
        "shannon_ln":shannon,"simpson_1_D":simpson,"pielou_evenness":evenness,
        "dominant_taxon":[matrix.columns[int(np.argmax(row))] if pos else "No counted organisms" for row,pos in zip(a,positive)]})
    mat=matrix.reset_index();mat.columns.name=None
    rel=pd.DataFrame(prop,index=matrix.index,columns=matrix.columns).reset_index();rel.columns.name=None
    return {"tables":{"Community abundance":mat,"Relative abundance":rel,"Community diversity":diversity},
        "notes":["Only comparable abundance units and a consistent taxonomic rank should be combined. Genus totals plus constituent species would double-count organisms.",
        "Diversity is descriptive and depends on sampling effort and counting method. GBIF occurrence counts are not phytoplankton abundance.",
        "No numerical bloom probability, toxicity or causal nutrient effect is inferred from diversity."],
        "plots":[{"kind":"bar","table":"Community diversity","x":"sample_id","y":"shannon_ln","title":"Phytoplankton diversity (natural-log Shannon)"}]}


def research_compute(action, frame, settings):
    s=settings;rng=np.random.default_rng(int(s.get("seed",42)))
    if action=="clean": return research_clean(frame,s)
    if action=="regression": return research_regression(frame,s)
    if action=="community": return research_community(frame,s)
    notes=[];plots=[];tables={}
    if action=="correlation":
        cols=s["columns"]
        if not 2<=len(cols)<=8: raise ValueError("Select between two and eight variables.")
        rows=[];reps=int(s.get("resamples",499))
        for i,xcol in enumerate(cols):
            for ycol in cols[i+1:]:
                f,xy=research_complete(frame,[xcol,ycol],minimum=3)
                for method in ("Pearson","Spearman"):
                    x,y=xy[:,0],xy[:,1]
                    if method=="Spearman": x=pd.Series(x).rank().to_numpy();y=pd.Series(y).rank().to_numpy()
                    r=research_r(x,y);p=lo=hi=np.nan
                    if s.get("independent") and len(x)>=8 and np.isfinite(r):
                        perm=[research_r(x,rng.permutation(y)) for _ in range(reps)]
                        p=(1+sum(abs(v)>=abs(r)-1e-12 for v in perm))/(reps+1)
                        boot=[]
                        for _ in range(reps):
                            ix=rng.integers(0,len(x),len(x));bx,by=xy[ix,0],xy[ix,1]
                            if method=="Spearman": bx=pd.Series(bx).rank().to_numpy();by=pd.Series(by).rank().to_numpy()
                            v=research_r(bx,by)
                            if np.isfinite(v): boot.append(v)
                        if len(boot)>.9*reps: lo,hi=np.quantile(boot,[.025,.975])
                    rows.append({"x":xcol,"y":ycol,"method":method,"n":len(x),"coefficient":r,
                        "CI95_low":lo,"CI95_high":hi,"permutation_p":p})
        t=pd.DataFrame(rows);t["BH_q"]=research_bh(t.permutation_p);tables["Correlations"]=t
        plots=[{"kind":"scatter","table":"Input complete pairs","x":cols[0],"y":cols[1],"title":"Exploratory paired observations"}]
        tables["Input complete pairs"]=frame[cols].copy()
        notes=["Pairwise complete cases; different pairs may use different samples. Correlation does not establish agreement or causation.",
            "P-values and percentile bootstrap intervals require user-declared independent rows and at least eight pairs. Eight is a computational guard, not a power calculation.",
            "Repeated site/time observations violate unrestricted inference. Use descriptive coefficients or a study-specific dependence model. BH adjustment covers only this displayed family."]
    elif action=="agreement":
        if not s.get("same_units"): raise ValueError("Confirm matching physical quantities and units. An index such as NDCI is not a chlorophyll concentration.")
        f,xy=research_complete(frame,[s["reference"],s["estimate"]],3)
        f["reference"]=xy[:,0];f["estimate"]=xy[:,1];f["difference"]=xy[:,1]-xy[:,0]
        tables={"Agreement metrics":pd.DataFrame([research_metrics(xy[:,0],xy[:,1])]),"Paired observations":f}
        notes=["Descriptive evaluation of supplied estimates. Independence from any calibration data and reference laboratory quality must be documented.",
               "No universal acceptable-error threshold is applied. Inspect sample coverage, bias and out-of-range conditions."]
        plots=[{"kind":"scatter","table":"Paired observations","x":"reference","y":"estimate","one_to_one":True,"title":"Reference versus estimate"}]
    elif action=="pca":
        f,x=research_complete(frame,s["columns"],4);scale=x.std(axis=0,ddof=1);keep=scale>1e-12
        cols=np.array(s["columns"])[keep]
        if len(cols)<2: raise ValueError("PCA needs at least two varying variables.")
        z=(x[:,keep]-x[:,keep].mean(axis=0))/scale[keep];u,d,vt=np.linalg.svd(z,full_matrices=False)
        var=d**2/(len(z)-1);labels=[f"PC{i+1}" for i in range(len(d))]
        scores=pd.DataFrame(u*d,columns=labels);scores.insert(0,"sample",f.get("sample_id",pd.Series(f.index,index=f.index)).astype(str).values)
        tables={"PCA scores":scores,"PCA loadings":pd.DataFrame(vt.T,index=cols,columns=labels).rename_axis("variable").reset_index(),
            "PCA variance":pd.DataFrame({"component":labels,"variance_fraction":var/var.sum()})}
        plots=[{"kind":"scatter","table":"PCA scores","x":"PC1","y":"PC2","title":"PCA of standardized variables"},
                {"kind":"bar","table":"PCA variance","x":"component","y":"variance_fraction","title":"PCA explained variance"}]
        notes=[f"{len(f)}/{len(frame)} complete rows retained; constant variables removed. Component signs may vary by numerical library without changing the solution."]
    elif action=="rda":
        envcols=s["environment"];taxa=s["taxa"]
        if set(envcols)&set(taxa): raise ValueError("Community and environmental columns must be separate.")
        f,v=research_complete(frame,[*envcols,*taxa],max(8,len(envcols)+4))
        x=v[:,:len(envcols)];a=v[:,len(envcols):]
        if (a<0).any() or (a.sum(axis=1)<=0).any(): raise ValueError("RDA needs nonnegative abundance and positive row totals.")
        if x.shape[1]==0 or a.shape[1]<2: raise ValueError("Select environmental constraints and at least two taxa.")
        scale=x.std(axis=0,ddof=1)
        if (scale<1e-12).any(): raise ValueError("Remove constant environmental predictors.")
        x=(x-x.mean(axis=0))/scale;rank=np.linalg.matrix_rank(x)
        if rank<len(envcols): raise ValueError("Environmental predictors are collinear; reduce the constraint set.")
        y=np.sqrt(a/a.sum(axis=1)[:,None]);y-=y.mean(axis=0)
        fitted=x@np.linalg.lstsq(x,y,rcond=None)[0];total=float((y*y).sum());fit=float((fitted*fitted).sum())
        if total<1e-14: raise ValueError("Community composition does not vary.")
        resid=total-fit;df2=len(y)-rank-1
        stat=(fit/rank)/(resid/df2) if resid>1e-14 else np.nan
        r2=fit/total;adjusted=1-(1-r2)*(len(y)-1)/df2;p=np.nan
        if s.get("independent") and np.isfinite(stat):
            count=0;reps=int(s.get("resamples",499))
            for _ in range(reps):
                yp=rng.permutation(y);fp=x@np.linalg.lstsq(x,yp,rcond=None)[0];ss=float((fp*fp).sum())
                perm=(ss/rank)/((total-ss)/df2)
                count+=perm>=stat-1e-12
            p=(count+1)/(reps+1)
        u,d,vt=np.linalg.svd(fitted,full_matrices=False);k=min(rank,2,len(d))
        scores=pd.DataFrame((u*d)[:,:k],columns=[f"RDA{i+1}" for i in range(k)])
        scores.insert(0,"sample",f.get("sample_id",pd.Series(f.index,index=f.index)).astype(str).values)
        tables={"RDA summary":pd.DataFrame([{"n":len(y),"constraint_rank":rank,"R2":r2,"adjusted_R2":adjusted,"pseudo_F":stat,"permutation_p":p}]),
            "RDA site scores":scores,"RDA taxon directions":pd.DataFrame(vt[:k].T,index=taxa,columns=[f"RDA{i+1}" for i in range(k)]).rename_axis("taxon").reset_index()}
        if k>=2: plots=[{"kind":"scatter","table":"RDA site scores","x":"RDA1","y":"RDA2","title":"Constrained community variation"}]
        else: plots=[{"kind":"bar","table":"RDA site scores","x":"sample","y":"RDA1","title":"Constrained community axis"}]
        notes=["Hellinger RDA; scores are fitted-response SVD coordinates, not a scaled ecological distance map.",
            "Unrestricted row permutations require independent samples; repeated sites/time need a design-specific permutation scheme. No automatic causal or bloom-risk claim."]
    elif action=="cluster":
        f,x=research_complete(frame,s["columns"],4)
        if len(x)>150: raise ValueError("Exploratory clustering is limited to 150 rows in this Streamlit workflow.")
        if s.get("distance")=="Bray-Curtis":
            if (x<0).any() or (x.sum(axis=1)<=0).any(): raise ValueError("Bray-Curtis requires nonnegative abundance and no empty samples.")
            dist=np.abs(x[:,None,:]-x[None,:,:]).sum(axis=2)/(x[:,None,:]+x[None,:,:]).sum(axis=2)
        else:
            scale=x.std(axis=0,ddof=1)
            if (scale<1e-12).any(): raise ValueError("Remove constant clustering variables.")
            z=(x-x.mean(axis=0))/scale;dist=np.linalg.norm(z[:,None,:]-z[None,:,:],axis=2)
        k=int(s.get("clusters",3))
        if not 2<=k<len(x): raise ValueError("Choose between two and n-1 clusters.")
        clusters=[[i] for i in range(len(x))]
        while len(clusters)>k:
            best=(float("inf"),0,1)
            for i in range(len(clusters)):
                for j in range(i+1,len(clusters)):
                    d=float(dist[np.ix_(clusters[i],clusters[j])].mean())
                    if d<best[0]:best=(d,i,j)
            _,i,j=best;clusters[i]+=clusters[j];del clusters[j]
        labels=np.zeros(len(x),int)
        for i,ix in enumerate(clusters):labels[ix]=i+1
        sil=[]
        for i in range(len(x)):
            own=np.where(labels==labels[i])[0];own=own[own!=i]
            if not len(own):sil.append(0.);continue
            a=dist[i,own].mean();b=min(dist[i,labels==g].mean() for g in np.unique(labels) if g!=labels[i])
            sil.append(float((b-a)/max(a,b)) if max(a,b)>0 else 0.)
        f["cluster"]=labels;f["silhouette"]=sil;tables={"Cluster assignments":f,"Cluster summary":pd.DataFrame([{"n":len(x),"clusters":k,"average_silhouette":np.mean(sil),"distance":s.get("distance","Standardized Euclidean")}])}
        plots=[{"kind":"scatter","table":"Cluster assignments","x":s["columns"][0],"y":s["columns"][1],"group":"cluster","title":"Exploratory clusters"}]
        notes=["Average linkage, deterministic tie order, fixed selected cluster count. Clusters are exploratory; silhouette is not independent stability validation."]
    elif action=="seasonal":
        column=s["column"]
        if "date" not in frame: raise ValueError("A date column is required.")
        f=frame.copy()
        if s.get("site") is not None and "site" in f:f=f[f.site.astype(str)==str(s["site"])]
        f["date"]=pd.to_datetime(f.date,utc=True,errors="coerce");f[column]=pd.to_numeric(f[column],errors="coerce")
        f=f.dropna(subset=["date",column]).set_index("date").sort_index()
        monthly=f[column].resample("MS").agg(["mean","count"])
        if len(monthly)<24 or monthly["mean"].isna().any(): raise ValueError("Need at least 24 consecutive observed months at this site. Gaps are not filled automatically; use the ordinary time-series chart instead.")
        y=monthly["mean"].to_numpy();weights=np.r_[.5,np.ones(11),.5]/12
        trend=np.full(len(y),np.nan);trend[6:-6]=np.convolve(y,weights,mode="valid")
        detrend=y-trend;month=monthly.index.month.to_numpy()
        seasonal=np.array([np.nanmean(detrend[month==m]) for m in range(1,13)]);seasonal-=seasonal.mean()
        monthly["trend"]=trend;monthly["seasonal"]=seasonal[month-1];monthly["remainder"]=y-trend-monthly.seasonal.to_numpy()
        tables={"Seasonal decomposition":monthly.rename(columns={"mean":"observed","count":"observations"}).reset_index()}
        plots=[{"kind":"line","table":"Seasonal decomposition","x":"date","y":c,"title":f"{column}: {c}"} for c in ["observed","trend","seasonal","remainder"]]
        notes=["Monthly means may have unequal sampling effort; inspect the observations column. No forecast is produced. Two cycles are only a minimum; longer coverage is preferable."]
    else: raise ValueError("Unknown research analysis.")
    return {"tables":tables,"notes":notes,"plots":plots}
# RESEARCH_ENGINE_END


def research_state(run):
    key="research_"+run["id"]
    if key not in st.session_state:
        st.session_state[key]={"records":[],"uploads":{},"field":None,"matchups":None,"community":None,
            "points":[],"scene_snapshots":{},"catalogue":[],"created_utc":utc_now(),"engine":RESEARCH_ENGINE_VERSION}
    return st.session_state[key]


def research_attach(run,lab):
    from environment import result,source_record
    out=result("Research validation")
    out["sources"]=[source_record("R1","AquaTerra research engine / user-supplied measurements","Calculated research results",
        utc_now(),f"{run['study']['start']} to {run['study']['end']}","Sample-level; match quality is explicit",
        "Executed Python analyses with recorded inputs, settings and methods. Field quality is not independently verified.")]
    out["notes"]=["Satellite indices are dimensionless; field concentrations remain separately labelled. No automatic toxicity or bloom probability.",
        "Each calculation has its own audit record and input snapshot. Agent completion does not constitute scientific validation.",
        "Statistical inference is unavailable unless the user declares independent sampling units. Review repeated sites/dates."]
    for rec in lab["records"][-12:]:
        for title,df in rec["output"]["tables"].items():out["tables"][rec["id"]+" "+title]=df
        out["facts"].append(f"[R1] {rec['id']}: {rec['action']} executed on {len(rec['input'])} rows. See the associated tables and recorded limitations; execution is not evidence of accuracy.")
    out["metrics"]={"Executed research analyses":len(lab["records"]),"Uploaded reference observations":len(lab["field"]) if lab["field"] is not None else 0}
    run["results"]["Research validation"]=out
    st.session_state.pop("crew_review",None);st.session_state.pop("exports",None)
    lab.pop("download",None)


def research_record(run,lab,action,frame,settings,output=None):
    output=research_compute(action,frame,settings) if output is None else output
    rec={"id":f"A{len(lab['records'])+1:03d}","action":action,"settings":json.loads(research_json(settings)),
         "input":frame.copy(deep=True),"input_sha256":hashlib.sha256(research_frame_json(frame).encode()).hexdigest(),
         "executed_utc":utc_now(),"engine":RESEARCH_ENGINE_VERSION,"method":RESEARCH_METHODS.get(action,settings.get("method","See settings")),"output":output}
    lab["records"].append(rec)
    research_attach(run,lab)
    return rec


def research_read_upload(upload,sheet=None):
    data=upload.getvalue()
    if len(data)>8_000_000: raise ValueError("Keep each uploaded file below 8 MB.")
    if upload.name.lower().endswith(".xlsx"):
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if sum(x.file_size for x in z.infolist())>80_000_000: raise ValueError("Workbook expands beyond the 80 MB processing limit.")
        if sheet is None:return pd.ExcelFile(io.BytesIO(data),engine="openpyxl").sheet_names
        frame=pd.read_excel(io.BytesIO(data),sheet_name=sheet,engine="openpyxl",nrows=10001)
    else:frame=pd.read_csv(io.BytesIO(data),nrows=10001)
    if len(frame)>10000 or len(frame.columns)>80: raise ValueError("Use at most 10,000 rows and 80 columns.")
    frame.columns=[str(c).strip() for c in frame.columns]
    if frame.columns.duplicated().any():raise ValueError("Column names must be unique.")
    return frame


def research_upload_widget(label,key):
    upload=st.file_uploader(label,type=["csv","xlsx"],key=key)
    if upload is None:return None,None
    try:
        sheet=None
        if upload.name.lower().endswith(".xlsx"):
            sheet=st.selectbox("Worksheet",research_read_upload(upload),key=key+"_sheet")
        return upload,research_read_upload(upload,sheet)
    except Exception as exc:
        st.error(f"Cannot read this dataset: {str(exc)[:200]}")
        return None,None


def research_mapping(frame,fields,key,required=()):
    options=["(not supplied)"]+list(frame.columns);mapping_columns={}
    aliases={"sample_id":["sampleid","sample","id"],"site":["station","stationid","location","siteid"],
        "date":["datetime","samplingdate","samplingtime","timestamp"],"latitude":["lat"],"longitude":["lon","lng","long"],
        "chlorophyll_ug_l":["chla","chlorophylla","chlorophyll","chlaµgl"],"temperature_c":["watertemperature","temperature","temp"],
        "turbidity_ntu":["turbidity"],"secchi_m":["secchi","transparency"],"taxon":["species","genus"],"abundance":["cellsml","count","density"]}
    norm=lambda x:re.sub(r"[^a-z0-9]","",str(x).lower())
    cols=st.columns(3)
    for i,dest in enumerate(fields):
        candidates=[norm(dest),*aliases.get(dest,[])]
        guess=next((c for c in frame if norm(c) in candidates),None)
        source=cols[i%3].selectbox(dest+(" *" if dest in required else ""),options,index=options.index(guess) if guess else 0,key=f"{key}_{dest}")
        if source!="(not supplied)":mapping_columns[dest]=source
    if len(set(mapping_columns.values()))<len(mapping_columns):st.warning("One source column is mapped more than once. Check the mapping before running.")
    return mapping_columns


def research_plot(spec,tables):
    f=tables[spec["table"]];x,y=spec["x"],spec["y"]
    fig,ax=plt.subplots(figsize=(7.4,4.5),layout="constrained")
    if spec["kind"]=="line":
        xx=pd.to_datetime(f[x],utc=True,errors="coerce") if x=="date" else f[x]
        ax.plot(xx,pd.to_numeric(f[y],errors="coerce"),color="#087f8c",linewidth=1.6,marker="o",markersize=3)
        fig.autofmt_xdate()
    elif spec["kind"]=="bar":
        draw=f.head(60);ax.bar(draw[x].astype(str),pd.to_numeric(draw[y],errors="coerce"),color="#087f8c")
        ax.tick_params(axis="x",rotation=65,labelsize=7)
    else:
        group=spec.get("group")
        if group and group in f:
            for label,d in f.groupby(group,dropna=False):ax.scatter(pd.to_numeric(d[x],errors="coerce"),pd.to_numeric(d[y],errors="coerce"),s=24,alpha=.8,label=str(label))
            ax.legend(frameon=False,fontsize=8)
        else:ax.scatter(pd.to_numeric(f[x],errors="coerce"),pd.to_numeric(f[y],errors="coerce"),s=25,color="#087f8c",alpha=.8)
        if spec.get("one_to_one"):
            values=f[[x,y]].apply(pd.to_numeric,errors="coerce").to_numpy();values=values[np.isfinite(values)]
            if len(values):ax.plot([values.min(),values.max()],[values.min(),values.max()],"--",color="#725c92",linewidth=1,label="1:1")
    ax.set(xlabel=x,ylabel=y,title=spec["title"]);ax.grid(alpha=.2)
    ax.spines[["top","right"]].set_visible(False)
    fig.text(.01,.002,"AquaTerra | source and methods in accompanying audit record",fontsize=7,color="#444444")
    return fig


def research_show_record(rec,download=True):
    st.markdown(f"**{rec['id']} · {rec['action'].replace('_',' ').title()}**")
    for note in rec["output"].get("notes",[]):st.caption(note)
    for spec in rec["output"].get("plots",[]):
        fig=research_plot(spec,rec["output"]["tables"])
        st.pyplot(fig);plt.close(fig)
    for title,df in rec["output"]["tables"].items():
        with st.expander(f"{title} · {len(df):,} rows",expanded=len(df)<12):
            st.dataframe(df.head(2000),hide_index=True,width="stretch")
            if download:st.download_button("Download complete table",safe_frame(df).to_csv(index=False).encode("utf-8-sig"),re.sub(r"\W+","_",rec["id"]+"_"+title)+".csv","text/csv",key=rec["id"]+title)
    with st.expander("How this result was produced"):
        st.write(rec["method"]);st.json({k:rec[k] for k in ["engine","executed_utc","input_sha256","settings"]})
        if rec["output"].get("model"):st.json(rec["output"]["model"])


@st.cache_data(ttl=1800,max_entries=6,show_spinner=False)
def research_catalogue(study,sensor,start,end,cloud=40):
    from environment import request_json
    if sensor=="Sentinel-2":host="earth-search.aws.element84.com";collection="sentinel-2-c1-l2a";url=f"https://{host}/v1/search"
    else:
        host="planetarycomputer.microsoft.com";collection="landsat-c2-l2" if sensor=="Landsat 8/9 temperature" else "sentinel-1-rtc"
        url=f"https://{host}/api/stac/v1/search"
    payload={"collections":[collection],"bbox":study["bbox"],"datetime":f"{start}T00:00:00Z/{end}T23:59:59Z","limit":100}
    items=[];truncated=False
    for page in range(3):
        data,stamp=request_json(url,payload=payload)
        for item in data.get("features",[]):
            props=item.get("properties",{})
            if sensor!="Sentinel-1 catalogue" and props.get("eo:cloud_cover",100)>cloud:continue
            if sensor=="Landsat 8/9 temperature" and props.get("platform") not in ("landsat-8","landsat-9"):continue
            items.append(item)
        nxt=next((v for v in data.get("links",[]) if v.get("rel")=="next"),None)
        if not nxt:break
        if page==2:truncated=True;break
        if urlparse(nxt["href"]).hostname!=host:raise ValueError("Unexpected catalogue pagination host.")
        url=nxt["href"]
        if nxt.get("method","GET")=="GET":
            # GET pagination is handled separately to avoid silently repeating the first page.
            for extra in range(2-page):
                data,stamp=request_json(url)
                for item in data.get("features",[]):
                    p=item.get("properties",{})
                    if sensor!="Sentinel-1 catalogue" and p.get("eo:cloud_cover",100)>cloud:continue
                    if sensor=="Landsat 8/9 temperature" and p.get("platform") not in ("landsat-8","landsat-9"):continue
                    items.append(item)
                nxt=next((v for v in data.get("links",[]) if v.get("rel")=="next"),None)
                if not nxt:break
                if urlparse(nxt["href"]).hostname!=host:raise ValueError("Unexpected catalogue pagination host.")
                url=nxt["href"];truncated=True
            break
        payload=nxt.get("body",payload)
    unique={i["id"]:i for i in items}
    return sorted(unique.values(),key=lambda i:i["properties"]["datetime"]),stamp,truncated


def research_landsat(item,study,max_uncertainty=2.):
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.enums import Resampling
    from rasterio.features import geometry_mask
    from environment import satellite_grid,request_json
    epsg,_,_,_,geom,_=satellite_grid(study)
    x0,y0,x1,y1=geom.bounds;resolution=max(120,math.ceil(math.sqrt((x1-x0)*(y1-y0)/600000)/120)*120)
    transform=rasterio.transform.from_origin(x0,y1,resolution,resolution)
    width,height=math.ceil((x1-x0)/resolution),math.ceil((y1-y0)/resolution)
    inside=geometry_mask([mapping(geom)],(height,width),transform,invert=True)
    arrays={};radiometry={}
    for name in ("lwir11","qa_pixel","qa_radsat","qa"):
        asset=item.get("assets",{}).get(name)
        if not asset:raise ValueError(f"Landsat scene has no {name} asset; it may be reflectance-only.")
        href=asset["href"]
        if urlparse(href).scheme!="https" or not (urlparse(href).hostname or "").endswith(".blob.core.windows.net"):
            raise ValueError("Unsupported Landsat asset host.")
        signed,_=request_json("https://planetarycomputer.microsoft.com/api/sas/v1/sign",{"href":href})
        signed_href=signed.get("href","")
        if urlparse(signed_href).scheme!="https" or urlparse(signed_href).hostname!=urlparse(href).hostname:raise ValueError("Unexpected signed asset host.")
        ca_bundle = os.getenv("CURL_CA_BUNDLE") or os.getenv("REQUESTS_CA_BUNDLE") or os.getenv("SSL_CERT_FILE") or requests.certs.where()
        with rasterio.Env(GDAL_CURL_CA_BUNDLE=ca_bundle,CURL_CA_BUNDLE=ca_bundle,GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",GDAL_HTTP_TIMEOUT="45",GDAL_HTTP_CONNECTTIMEOUT="12",GDAL_HTTP_MAX_RETRY="1",GDAL_CACHEMAX=64_000_000):
            with rasterio.open(signed_href) as source:
                with WarpedVRT(source,crs=f"EPSG:{epsg}",transform=transform,width=width,height=height,
                    resampling=Resampling.nearest,dtype="float32",nodata=-9999) as vrt:
                    arrays[name]=vrt.read(1,masked=True).filled(np.nan)
        radiometry[name]=asset.get("raster:bands",[{}])[0]
    raw=arrays["lwir11"];q=np.nan_to_num(arrays["qa_pixel"],nan=1).astype("uint16")
    valid=inside & np.isfinite(raw) & (raw>0) & ((q&63)==0) & (arrays["qa_radsat"]==0)
    uncertainty=arrays["qa"]*.01
    valid &= np.isfinite(uncertainty) & (uncertainty<=max_uncertainty)
    water=valid & ((q&128)!=0)
    scale=float(radiometry["lwir11"].get("scale",.00341802));offset=float(radiometry["lwir11"].get("offset",149.0))
    temp=raw*scale+offset-273.15
    temp[~water]=np.nan
    return {"summary":{"scene_id":item["id"],"date":item["properties"]["datetime"],"grid_resolution_m":resolution,
                "water_pixels":int(water.sum()),"collection":item["collection"],"valid_aoi_percent":100*float(valid.sum())/max(1,int(inside.sum()))},
            "arrays":{"Water surface temperature C":temp,"ST uncertainty K":np.where(water,uncertainty,np.nan),"Water mask":np.where(valid,water.astype(float),np.nan)},
            "inside":inside,"valid":valid,"water":water,"epsg":epsg,"transform":tuple(transform),"resolution":resolution,"radiometry":radiometry}


def research_extract_sample(row,item,raster,settings):
    from affine import Affine
    acquired=pd.Timestamp(item["properties"]["datetime"])
    if acquired.tzinfo is None:acquired=acquired.tz_localize("UTC")
    sampled=pd.Timestamp(row["date"])
    if sampled.tzinfo is None:sampled=sampled.tz_localize("UTC")
    delta=abs((acquired-sampled).total_seconds())/3600
    known=bool(row.get("sampling_time_known",False))
    base={**dict(row),"scene_id":item["id"],"acquisition_utc":acquired.isoformat(),"time_difference_hours":delta if known else np.nan,
        "grid_resolution_m":raster["resolution"],"validation_status":"Unvalidated satellite observation","matched":False,
        "timing_quality":"Exact sampling time" if known else "Date only; exploratory comparison"}
    if not known and not settings.get("allow_date_only"):
        return {**base,"match_reason":"Sampling time unknown; strict validation requires a time"}
    if known and delta>settings["hours"]:return {**base,"match_reason":"Outside selected temporal window"}
    if not known and acquired.tz_convert(row.get("sampling_timezone","UTC")).date().isoformat()!=row.get("sampling_date_local",sampled.date().isoformat()):
        return {**base,"match_reason":"Date-only observations require the same local calendar date"}
    xy=Transformer.from_crs(4326,raster["epsg"],always_xy=True).transform(float(row["longitude"]),float(row["latitude"]))
    cc,rr=~Affine(*raster["transform"][:6])*xy;c=int(math.floor(cc));r=int(math.floor(rr))
    radius=int(settings.get("pixel_radius",1));water=raster["water"];h,w=water.shape
    if r-radius<0 or c-radius<0 or r+radius>=h or c+radius>=w:return {**base,"match_reason":"Extraction window falls outside processed scene"}
    ys=slice(r-radius,r+radius+1);xs=slice(c-radius,c+radius+1);mask=water[ys,xs]
    base.update({"pixel_row":r,"pixel_col":c,"support_id":f"{item['id']}:{r}:{c}:{radius}",
        "water_fraction":float(mask.mean()),"water_pixel_count":int(mask.sum()),"window_pixels":int(mask.size)})
    if not water[r,c] or mask.mean()<settings.get("minimum_water_fraction",1.):
        return {**base,"match_reason":"Insufficient clear water or shoreline/mixed-pixel window"}
    for array_name,column in [("NDCI","sat_ndci"),("Water red reflectance","sat_red_reflectance"),
                              ("Water surface temperature C","sat_surface_temperature_c"),("ST uncertainty K","sat_temperature_uncertainty_k")]:
        if array_name not in raster["arrays"]:continue
        values=raster["arrays"][array_name][ys,xs][mask];values=values[np.isfinite(values)]
        if not len(values):return {**base,"match_reason":"No finite values after masking"}
        base[column]=float(np.median(values));base[column+"_spatial_sd"]=float(np.std(values,ddof=1)) if len(values)>1 else np.nan
    return {**base,"matched":True,"match_reason":"Eligible comparison; not a validated concentration retrieval"}


def research_match(run,lab,sensor,items,settings,progress=None):
    from environment import process_satellite_item,satellite_grid
    fields=lab["field"]
    if fields is None:raise ValueError("Upload and check field observations first.")
    if run["study"]["area_km2"]>MAX_SAT_KM2:raise ValueError(f"Use a reservoir boundary below {MAX_SAT_KM2:g} km².")
    candidates={};row_audit=[];limit=int(settings.get("maximum_scenes",8))
    for i,row in fields.iterrows():
        if not bool(row.get("satellite_eligible",False)):
            row_audit.append({**row.to_dict(),"matched":False,"match_reason":"Invalid date, coordinates or study scope"});continue
        timestamp=pd.Timestamp(row.date)
        possible=[]
        for item in items:
            if not shape(item["geometry"]).covers(Point(row.longitude,row.latitude)):continue
            t=pd.Timestamp(item["properties"]["datetime"]);delta=abs((t-timestamp).total_seconds())/3600
            if row.sampling_time_known and delta<=settings["hours"]:possible.append((delta,item))
            elif not row.sampling_time_known and settings.get("allow_date_only") and t.tz_convert(row.get("sampling_timezone","UTC")).date().isoformat()==row.get("sampling_date_local",timestamp.date().isoformat()):possible.append((delta,item))
        if not possible:
            row_audit.append({**row.to_dict(),"matched":False,"match_reason":"No catalogue candidate within location/time rules"});continue
        # Up to three nearest candidates per sample; keep all attempts for inspection.
        candidates[i]=[item for _,item in sorted(possible,key=lambda z:(z[0],z[1]["id"]))[:3]]
    ordered=list(dict.fromkeys(it["id"] for vals in candidates.values() for it in vals))
    if len(ordered)>limit:raise ValueError(f"Matching requires up to {len(ordered)} scenes; the selected budget is {limit}. Narrow the dates or increase the budget. No dates were silently dropped.")
    byid={it["id"]:it for vals in candidates.values() for it in vals};rasters={};failures={}
    grid=satellite_grid(run["study"])
    for j,sceneid in enumerate(ordered):
        if progress:progress(f"Scene {j+1}/{len(ordered)}: {sceneid}")
        try:
            raster=process_satellite_item(byid[sceneid],run["study"],grid,settings.get("water_threshold",0.)) if sensor=="Sentinel-2" else research_landsat(byid[sceneid],run["study"],settings.get("max_temperature_uncertainty",2.))
            rasters[sceneid]=raster
            lab["scene_snapshots"][sceneid]={"item":byid[sceneid],"raster":raster}
        except Exception as exc:
            failures[sceneid]=f"{type(exc).__name__}: satellite asset could not be processed"
            lab["scene_snapshots"][sceneid]={"item":byid[sceneid],"failure":failures[sceneid]}
    full_settings={**settings,"sensor":sensor,"scene_ids":ordered,
        "method":"Acquisition-time and coordinate matchup; median of clear water pixels on a common UTM grid. Settings and processed arrays are preserved."}
    output=research_offline_match(fields,full_settings,lab["scene_snapshots"])
    matched=output["tables"]["Field satellite matchups"]
    if matched.empty:raise ValueError("No field observations were available for matching.")
    lab["matchups"]=matched
    if "sat_ndci" in matched and "chlorophyll_ug_l" in matched:
        output["plots"]=[{"kind":"scatter","table":"Field satellite matchups","x":"sat_ndci","y":"chlorophyll_ug_l","title":"Uncalibrated NDCI versus measured chlorophyll-a (µg/L)"}]
    return research_record(run,lab,"satellite_matchup",fields,full_settings,output)


def research_offline_match(fields,settings,snapshots):
    rows=[];attempts=[]
    for _,row in fields.iterrows():
        record=row.to_dict()
        if not bool(row.get("satellite_eligible",False)):
            rows.append({**record,"matched":False,"match_reason":"Invalid date, coordinates or study scope"});continue
        t=pd.Timestamp(row["date"]);candidates=[]
        for sceneid in settings["scene_ids"]:
            snap=snapshots.get(sceneid)
            if not snap:continue
            item=snap["item"]
            if not shape(item["geometry"]).covers(Point(row["longitude"],row["latitude"])):continue
            acquired=pd.Timestamp(item["properties"]["datetime"]);delta=abs((acquired-t).total_seconds())/3600
            known=bool(row.get("sampling_time_known",False))
            local_day=acquired.tz_convert(row.get("sampling_timezone","UTC")).date().isoformat()
            day=row.get("sampling_date_local",t.date().isoformat())
            eligible=(known and delta<=settings["hours"]) or (not known and settings.get("allow_date_only") and local_day==day)
            if eligible:candidates.append((delta,sceneid,snap))
        selected=None
        for _,sceneid,snap in sorted(candidates,key=lambda x:(x[0],x[1]))[:3]:
            if "raster" not in snap:
                attempts.append({"sample_id":row["sample_id"],"scene_id":sceneid,"matched":False,"match_reason":"Scene processing failed; no raster snapshot"});continue
            a=research_extract_sample(record,snap["item"],snap["raster"],settings);attempts.append(a)
            if a["matched"]:selected=a;break
        reason="Candidate scenes failed processing or clear-water quality rules" if candidates else "No catalogue candidate within location/time rules"
        rows.append(selected or {**record,"matched":False,"match_reason":reason})
    return {"tables":{"Field satellite matchups":pd.DataFrame(rows),"Candidate attempt audit":pd.DataFrame(attempts)},"plots":[],
        "notes":["Nearest eligible observation from up to three candidates. Unmatched samples remain in the audit table.",
        "NDCI and red reflectance are unvalidated indicators; they do not measure chlorophyll concentration or confirm cyanobacteria/toxins.",
        "Atmospheric correction, sediment, water depth, adjacency and optical properties can affect results. Landsat surface temperature is not a depth measurement.",
        "Within-window spatial standard deviation is not a calibrated retrieval-error interval."]}


def research_template():
    output=io.BytesIO()
    with pd.ExcelWriter(output,engine="openpyxl") as writer:
        pd.DataFrame(columns=["sample_id","site","date","latitude","longitude","depth_m",*RESEARCH_NUMERIC,"laboratory_method","quality_note"]).to_excel(writer,sheet_name="Field",index=False)
        pd.DataFrame(columns=["sample_id","taxon","abundance"]).to_excel(writer,sheet_name="Phytoplankton",index=False)
        pd.DataFrame(columns=["site","latitude","longitude"]).to_excel(writer,sheet_name="Sites",index=False)
        pd.DataFrame({"Instructions":["Blank template: no demonstration measurements are supplied.","Use one unique sample_id per field sample; join community rows with the same sample_id.",
            "Use the units in the field column names; chlorophyll_ug_l means micrograms/litre.","Dates: ISO 8601, preferably with time and UTC offset. Date-only rows cannot support strict timed validation.",
            "Community data: enter one common abundance unit and taxonomic rank in the app. Unrecorded taxa are not automatically zero.",
            "Keep original laboratory methods, sampling depth, detection limits and quality-control records."]}).to_excel(writer,sheet_name="Read_me",index=False)
    return output.getvalue()


def research_function_source(name):
    import ast
    source=Path(__file__).read_text(encoding="utf-8");tree=ast.parse(source);lines=source.splitlines()
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name==name:return "\n".join(lines[node.lineno-1:node.end_lineno])+"\n"
    raise ValueError("Replay function is unavailable: "+name)


def research_package(run,lab):
    import importlib.metadata
    source=Path(__file__).read_text(encoding="utf-8")
    engine=source.split("# RESEARCH_ENGINE_START\n",1)[1].split("# RESEARCH_ENGINE_END",1)[0]
    manifest={"application":APP_RELEASE,"engine":RESEARCH_ENGINE_VERSION,"study":run["study"],"created_utc":utc_now(),"records":[],"files":{},"snapshots":[]}
    content={};report=["# AquaTerra research report","",f"Study: {run['study']['label']}",
        "Satellite estimates are not field measurements. Statistical outputs require review of sampling design and optical limitations.",
        "This export includes exact executed scientific code and input snapshots. AI text may vary on a fresh provider call; numerical analyses can be rerun offline."]
    def add(path,data):
        if isinstance(data,str):data=data.encode("utf-8")
        content[path]=data;manifest["files"][path]=hashlib.sha256(data).hexdigest()
    for name,blob in lab["uploads"].items():add("original_uploads/"+name,blob)
    for i,(sceneid,snapshot) in enumerate(lab["scene_snapshots"].items()):
        prefix=f"satellite/scene_{i+1:03d}";r=snapshot.get("raster")
        meta={"scene_id":sceneid,"item":snapshot["item"]}
        if r:
            meta["raster"]={k:r[k] for k in ("summary","epsg","transform","resolution","radiometry")}
            buffer=io.BytesIO();arrays={"water":r["water"],"inside":r["inside"],"valid":r["valid"]}
            meta["array_names"]=list(r["arrays"])
            arrays.update({f"layer_{j}":r["arrays"][name] for j,name in enumerate(meta["array_names"])})
            np.savez_compressed(buffer,**arrays);add(prefix+".npz",buffer.getvalue())
            add(prefix+".tif",research_geotiff(r))
            scientific_layer="NDCI" if "NDCI" in r["arrays"] else "Water surface temperature C"
            if np.isfinite(r["arrays"][scientific_layer]).any():
                fig=research_raster_figure(r,scientific_layer)
                image_bytes=io.BytesIO();fig.savefig(image_bytes,format="png",dpi=300,bbox_inches="tight");plt.close(fig)
                add(prefix+"_map.png",image_bytes.getvalue())
        add(prefix+".json",research_json(meta));manifest["snapshots"].append(prefix)
    for rec in lab["records"]:
        root="analyses/"+rec["id"]
        add(root+"/input.json",research_frame_json(rec["input"]))
        metadata={k:rec[k] for k in ("id","action","settings","input_sha256","executed_utc","engine","method")}
        metadata["notes"]=rec["output"].get("notes",[]);metadata["plots"]=rec["output"].get("plots",[])
        metadata["model"]=rec["output"].get("model")
        add(root+"/method.json",research_json(metadata));manifest["records"].append(metadata)
        report.extend(["",f"## {rec['id']} — {rec['action']}",rec["method"],*rec["output"].get("notes",[])])
        for title,df in rec["output"]["tables"].items():
            filename=re.sub(r"[^a-zA-Z0-9_-]+","_",title)
            add(root+"/"+filename+".csv",safe_frame(df).to_csv(index=False).encode("utf-8-sig"))
            add(root+"/"+filename+".json",research_frame_json(df))
            report.append(f"### {title} ({len(df)} rows)\n\n```\n{df.head(15).to_string(index=False)}\n```")
        for j,spec in enumerate(rec["output"].get("plots",[])):
            fig=research_plot(spec,rec["output"]["tables"])
            for extension in ("png","svg","pdf"):
                b=io.BytesIO();fig.savefig(b,format=extension,dpi=300,bbox_inches="tight");add(f"{root}/figure_{j+1}.{extension}",b.getvalue())
            plt.close(fig)
    for name in ("app.py","environment.py","evidence.py","crew_config.py","crew_workflow.py","agent_tools.py","agent_common.py","crew_runtime.py","crewai_compat.py","ai_providers.py","requirements.txt","METHODS.md","RESEARCH_METHODS.md","AI_PROVIDERS.md"):
        p=Path(__file__) if name=="app.py" else ROOT/name
        if p.is_file():add("source/"+name,p.read_bytes())
    for p in (ROOT/"agents").glob("*.py"):add("source/agents/"+p.name,p.read_bytes())
    deps=[]
    for name in ("numpy","pandas","matplotlib","shapely","pyproj","affine"):
        try:deps.append(f"{name}=={importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:pass
    add("requirements-replay.txt","\n".join(deps)+"\n")
    replay='''"""Reproduce recorded numerical analyses from frozen input snapshots. No AI key or network needed."""
import io, json, math, re, hashlib
from pathlib import Path
from datetime import date, datetime
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import shape, Point
from pyproj import Transformer
'''+engine+"\n"+research_function_source("research_extract_sample")+"\n"+research_function_source("research_offline_match")+"\n"+research_function_source("research_plot")+'''
root=Path(__file__).resolve().parent
manifest=json.loads((root/"manifest.json").read_text())
for name,expected in manifest["files"].items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected:
        raise ValueError("Snapshot checksum mismatch: "+name)
snapshots={}
for prefix in manifest["snapshots"]:
    meta=json.loads((root/(prefix+".json")).read_text());snap={"item":meta["item"]}
    if "raster" in meta:
        with np.load(root/(prefix+".npz"),allow_pickle=False) as a:
            raster=meta["raster"]
            raster.update({k:a[k].copy() for k in ("water","inside","valid")})
            raster["arrays"]={name:a["layer_"+str(j)].copy() for j,name in enumerate(meta["array_names"])}
        snap["raster"]=raster
    snapshots[meta["scene_id"]]=snap
out=root/"reproduced";out.mkdir(exist_ok=True)
for rec in manifest["records"]:
    frame=pd.read_json(io.StringIO((root/"analyses"/rec["id"]/"input.json").read_text()),orient="split",dtype=False,convert_dates=False)
    if rec["action"]=="satellite_matchup":
        result=research_offline_match(frame,rec["settings"],snapshots)
    elif rec["action"]=="external_model_import":
        result={"tables":{"Imported model outputs":frame},"plots":[]}
    else:result=research_compute(rec["action"],frame,rec["settings"])
    folder=out/rec["id"];folder.mkdir(exist_ok=True)
    for title,table in result["tables"].items():
        name=re.sub(r"[^a-zA-Z0-9_-]+","_",title)
        # JSON preserves numeric values and avoids spreadsheet formula interpretation.
        (folder/(name+".json")).write_text(research_frame_json(table))
    for j,spec in enumerate(rec.get("plots",[])):
        fig=research_plot(spec,result["tables"]);fig.savefig(folder/("figure_"+str(j+1)+".png"),dpi=300,bbox_inches="tight");plt.close(fig)
    print(rec["id"],rec["action"],"reproduced")
print("Done. Results are in",out)
'''
    add("reproduce.py",replay)
    report.extend(["","## Reproduction","Install Python 3.12, then run:","```","python -m pip install -r requirements-replay.txt","python reproduce.py","```",
        "The satellite matchups rerun from preserved, processed raster windows. Full raw-scene atmospheric processing is not claimed to be reproduced offline. The original pipeline code, scene metadata, masks and settings are included; downloading upstream data may return revised provider products.",
        "External model outputs are imported snapshots. This package does not claim to rerun WASP, AQUATOX, CE-QUAL-W2 or EcoDynamo. Retain their original projects, executables, inputs and calibration records.",
        "## Scientific references","https://doi.org/10.1016/j.rse.2011.10.016","https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature",
        "https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands","https://vegandevs.github.io/vegan/reference/cca.html",
        "https://www.statsmodels.org/stable/generated/statsmodels.tsa.seasonal.seasonal_decompose.html"])
    add("research_report.md","\n\n".join(report))
    audit=[{k:v for k,v in rec.items() if k not in ("input","output")} for rec in lab["records"]]
    add("execution_log.json",research_json(audit))
    review=st.session_state.get("crew_review")
    if review_is_current(run,review):add("ai_review.json",research_json(review))
    add("sampling_points.geojson",research_json({"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[p["longitude"],p["latitude"]]},"properties":{"site":p["site"],"status":"Planned location; no implied measurement"}} for p in lab["points"]]}))
    add("study_boundary.geojson",research_json(run["study"]["geometry"]))
    # Manifest is written last and intentionally does not checksum itself.
    content["manifest.json"]=research_json(manifest).encode()
    if sum(len(b) for b in content.values())>220_000_000:raise ValueError("Export exceeds 220 MB; use a smaller study or fewer scenes.")
    buff=io.BytesIO()
    with zipfile.ZipFile(buff,"w",zipfile.ZIP_DEFLATED) as z:
        for path,blob in content.items():z.writestr(path,blob)
    return buff.getvalue()


def research_field_page(run,lab):
    st.subheader("Original field measurements")
    st.download_button("Download blank Excel template",research_template(),"aquaterra_research_template.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    upload,frame=research_upload_widget("Upload field workbook or CSV","research_field_file")
    if frame is not None:
        st.dataframe(frame.head(8),hide_index=True,width="stretch")
        with st.expander("Map columns and confirm units",expanded=True):
            mapping_columns=research_mapping(frame,["sample_id","site","date","latitude","longitude","depth_m",*RESEARCH_NUMERIC,"laboratory_method","quality_note"],"fieldmap",("site","date"))
            st.caption("Units: chlorophyll/phycocyanin/phosphorus µg/L; nitrogen/oxygen mg/L; turbidity NTU; Secchi/depth m; temperature °C. Mapping a column does not convert its units.")
            c1,c2,c3=st.columns(3)
            tz=c1.selectbox("Timezone for dates without UTC offset",["UTC","Asia/Karachi","Asia/Shanghai","Asia/Kolkata","Europe/London","America/New_York"])
            dayfirst=c2.checkbox("Day comes before month",False)
            precision=c3.selectbox("Sampling-time precision",["Detect from values","Date only","Exact times supplied"])
            units=st.checkbox("The mapped measurement columns use the stated units",key="research_units")
            if st.button("Check and attach field data",type="primary",disabled=not units):
                try:
                    if not {"site","date"}.issubset(mapping_columns):raise ValueError("Map site and date before continuing.")
                    if len(set(mapping_columns.values()))!=len(mapping_columns):raise ValueError("Each source column may be mapped to only one destination.")
                    settings={"mapping":mapping_columns,"timezone":tz,"dayfirst":dayfirst,"time_precision":precision,
                        "geometry":run["study"]["geometry"],"start":run["study"]["start"],"end":run["study"]["end"],
                        "original_file_sha256":hashlib.sha256(upload.getvalue()).hexdigest()}
                    result=research_compute("clean",frame,settings)
                    lab.update({"records":[],"uploads":{},"scene_snapshots":{},"matchups":None,"community":None,"field":result["tables"]["Cleaned observations"]})
                    lab["uploads"][re.sub(r"[^a-zA-Z0-9_.-]","_",upload.name)]=upload.getvalue()
                    research_record(run,lab,"clean",frame,settings,result)
                    st.success("Field data attached. Previous research calculations were cleared because their input dataset changed.")
                except Exception as exc:st.error(str(exc)[:400])
    if lab["field"] is not None:
        f=lab["field"];a,b,c=st.columns(3)
        a.metric("Uploaded rows",len(f));b.metric("Included rows",int(f.included.sum()));c.metric("Geolocated eligible rows",int(f.satellite_eligible.sum()))
        st.dataframe(f,hide_index=True,width="stretch")
        values=[c for c in RESEARCH_NUMERIC if c in f and f[c].notna().any()]
        if values:
            variable=st.selectbox("Field measurement to inspect",values)
            plot=f.loc[f.included].copy();plot["date"]=pd.to_datetime(plot.date,utc=True)
            if not plot.empty:
                st.plotly_chart(px.scatter(plot,x="date",y=variable,color="site",hover_data=["sample_id","quality_flags"],template="plotly_dark"),width="stretch")
                st.plotly_chart(px.box(plot,x="site",y=variable,points="all",template="plotly_dark"),width="stretch")
                location=plot.dropna(subset=["latitude","longitude",variable]);m=base_map(run["study"])
                for _,row in location.iterrows():
                    radius=min(18,max(4,math.sqrt(abs(float(row[variable])))*1.5))
                    folium.CircleMarker([row.latitude,row.longitude],radius=radius,color="#087f8c",fill=True,fill_opacity=.6,
                        tooltip=html.escape(f"{row.site}: {variable}={row[variable]:.4g}; field reference")).add_to(m)
                show_map(m,"research_field_map")
                st.caption("Bubble area follows magnitude with a display cap; it is a measured-data display, not a continuous concentration surface.")


def research_sites_page(run,lab):
    st.subheader("Reservoir and sampling points")
    st.write("Change the reservoir boundary in Study & analysis. Here, click the map and save a named planned sampling point.")
    m=base_map(run["study"])
    for p in lab["points"]:folium.CircleMarker([p["latitude"],p["longitude"]],radius=6,color="#c48622",fill=True,tooltip=html.escape(p["site"]+" — planned")).add_to(m)
    response=show_map(m,"research_site_editor",height=500,interactive=True)
    click=(response or {}).get("last_clicked")
    name=st.text_input("Site name",value=f"Site {len(lab['points'])+1}")
    if click:st.caption(f"Selected: {click['lat']:.6f}, {click['lng']:.6f}")
    if st.button("Save clicked point",disabled=not click):
        if not name.strip():st.error("Enter a site name.")
        elif any(p["site"]==name.strip() for p in lab["points"]):st.error("Site names must be unique.")
        elif not shape(run["study"]["geometry"]).covers(Point(click["lng"],click["lat"])):st.error("Choose a point inside the study boundary.")
        else:
            lab["points"].append({"site":name.strip(),"latitude":click["lat"],"longitude":click["lng"]});lab.pop("download",None);st.rerun()
    if lab["points"]:
        st.dataframe(pd.DataFrame(lab["points"]),hide_index=True)
        remove=st.selectbox("Point to remove",[p["site"] for p in lab["points"]])
        if st.button("Remove selected planned point"):
            lab["points"]=[p for p in lab["points"] if p["site"]!=remove];lab.pop("download",None);st.rerun()
        st.download_button("Download site coordinates",safe_frame(pd.DataFrame(lab["points"])).to_csv(index=False),"sampling_sites.csv","text/csv")
    st.caption("A planned point does not prove a sample was taken. Use actual sampling coordinates in the field workbook; do not silently substitute planned locations.")


def research_raster_figure(raster,layer):
    from affine import Affine
    array=raster["arrays"][layer];transform=Affine(*raster["transform"][:6]);h,w=array.shape
    x0,y0=transform*(0,0);x1,y1=transform*(w,h)
    values=array[np.isfinite(array)]
    if not len(values):raise ValueError("No finite pixels in this layer.")
    lo,hi=np.quantile(values,[.02,.98])
    if hi<=lo:hi=lo+1e-6
    fig,ax=plt.subplots(figsize=(7,6),layout="constrained")
    im=ax.imshow(array,extent=[x0,x1,y1,y0],cmap="viridis",vmin=lo,vmax=hi,interpolation="nearest")
    fig.colorbar(im,ax=ax,label=layer,shrink=.8)
    ax.set(xlabel=f"Easting (m), EPSG:{raster['epsg']}",ylabel="Northing (m)",title=f"{layer}\n{raster['summary']['date']}")
    ax.ticklabel_format(style="plain",useOffset=False)
    fig.text(.01,.005,f"Grid {raster['resolution']} m | blank = no usable data | colour range: 2–98th percentiles",fontsize=8)
    return fig


def research_geotiff(raster):
    from rasterio.io import MemoryFile
    from affine import Affine
    names=list(raster["arrays"]);h,w=raster["arrays"][names[0]].shape
    with MemoryFile() as memory:
        with memory.open(driver="GTiff",width=w,height=h,count=len(names),dtype="float32",crs=f"EPSG:{raster['epsg']}",
                transform=Affine(*raster["transform"][:6]),nodata=np.nan,compress="deflate") as dst:
            for i,name in enumerate(names,1):dst.write(raster["arrays"][name].astype("float32"),i);dst.set_band_description(i,name)
            dst.update_tags(scene_id=raster["summary"]["scene_id"],acquired=raster["summary"]["date"],validation_status="Unvalidated satellite observation; consult field matchup and method records")
        return memory.read()


def research_satellite_page(run,lab):
    st.subheader("Satellite observations and field matchups")
    sensor=st.selectbox("Satellite source",["Sentinel-2","Landsat 8/9 temperature","Sentinel-1 catalogue"])
    if sensor=="Sentinel-1 catalogue":st.info("This single-file version provides Sentinel-1 acquisition footprints and metadata. SAR water classification and flood modelling are not implemented here.")
    elif sensor=="Sentinel-2":st.caption("NDCI and red reflectance remain uncalibrated indicators. No universal chlorophyll, turbidity or cyanobacteria conversion is applied.")
    else:st.caption("Landsat 8/9 Collection 2 surface temperature, water and cloud QA, with ST uncertainty filtering. Output grid is at least 120 m; narrow waters may be unresolved.")
    a,b,c=st.columns(3)
    start=a.date_input("Satellite search start",date.fromisoformat(run["study"]["start"]),key="research_sat_start")
    end=b.date_input("Satellite search end",date.fromisoformat(run["study"]["end"]),key="research_sat_end")
    cloud=c.slider("Scene cloud limit (%)",0,100,40,key="research_cloud")
    if st.button("Search satellite catalogue"):
        try:
            if start>end:raise ValueError("Search start must precede end.")
            with st.spinner("Searching acquisition metadata…"):items,stamp,truncated=research_catalogue(run["study"],sensor,str(start),str(end),cloud)
            lab["catalogue"]=items;lab["catalogue_sensor"]=sensor;lab["catalogue_stamp"]=stamp;lab["catalogue_truncated"]=truncated
            st.success(f"Found {len(items)} candidate scenes. Pixel-level quality is checked during extraction.")
        except Exception as exc:st.error(f"Catalogue unavailable: {str(exc)[:250]}")
    items=lab.get("catalogue",[]) if lab.get("catalogue_sensor")==sensor else []
    if items:
        table=pd.DataFrame([{"scene_id":i["id"],"acquisition_utc":i["properties"]["datetime"],"cloud_percent":i["properties"].get("eo:cloud_cover"),"collection":i.get("collection")} for i in items])
        st.dataframe(table,hide_index=True,width="stretch")
        if lab.get("catalogue_truncated"):st.warning("The catalogue reached its 300-item bound. Narrow the date range; complete coverage is not established.")
        st.caption("Catalogue scenes are not necessarily usable water observations. Absence of usable pixels does not mean absence of a bloom.")
        st.download_button("Download acquisition inventory",table.to_csv(index=False),"satellite_inventory.csv","text/csv")
        if sensor=="Sentinel-1 catalogue":
            m=base_map(run["study"])
            for item in items[:30]:folium.GeoJson(item["geometry"],name=item["id"],tooltip=html.escape(item["id"])).add_to(m)
            show_map(m,"research_sar_catalogue");return
    if sensor!="Sentinel-1 catalogue":
        c1,c2,c3=st.columns(3)
        hours=c1.number_input("Maximum time difference (hours)",.5,72.,3.,.5)
        radius=c2.selectbox("Extraction neighbourhood",["3 × 3 pixels","Single pixel","5 × 5 pixels"])
        fraction=c3.slider("Minimum clear-water fraction",.5,1.,1.,.05)
        c1,c2,c3=st.columns(3)
        maxscenes=c1.slider("Maximum scenes per matching run",1,12,6)
        dateonly=c2.checkbox("Allow date-only exploratory comparisons",False)
        threshold=c3.slider("Water NDWI / MNDWI threshold",-.2,.4,0.,.05,key="research_water_mask")
        uncertainty=st.number_input("Maximum Landsat ST uncertainty (K)",.1,10.,2.,.1,disabled=sensor!="Landsat 8/9 temperature")
        st.caption("A 3-hour window is a starting choice, not a universal validation standard. Choose timing and spatial support appropriate to the reservoir dynamics and sampling method.")
        if st.button("Retrieve pixels and match field samples",type="primary",disabled=not items or lab["field"] is None):
            try:
                settings={"hours":hours,"pixel_radius":{"3 × 3 pixels":1,"Single pixel":0,"5 × 5 pixels":2}[radius],
                    "minimum_water_fraction":fraction,"maximum_scenes":maxscenes,"allow_date_only":dateonly,
                    "water_threshold":threshold,"max_temperature_uncertainty":uncertainty,"catalogue_retrieved_utc":lab.get("catalogue_stamp"),
                    "catalogue_truncated":lab.get("catalogue_truncated",False)}
                with st.status("Retrieving satellite windows…",expanded=True) as status:
                    rec=research_match(run,lab,sensor,items,settings,status.write)
                    status.update(label="Matching finished; inspect coverage and exclusions",state="complete",expanded=False)
                st.success(f"Matched {int(lab['matchups']['matched'].sum())}/{len(lab['matchups'])} observations.")
            except Exception as exc:st.error(f"Matching stopped: {str(exc)[:350]}")
        if lab["matchups"] is not None:st.dataframe(lab["matchups"],hide_index=True,width="stretch")
        available=[k for k,v in lab["scene_snapshots"].items() if "raster" in v]
        if available:
            sid=st.selectbox("Inspect a processed scene",available)
            raster=lab["scene_snapshots"][sid]["raster"]
            layers=[k for k,v in raster["arrays"].items() if np.isfinite(v).any()]
            if layers:
                layer=st.selectbox("Processed layer",layers)
                fig=research_raster_figure(raster,layer);st.pyplot(fig);plt.close(fig)
                st.download_button("Download this scene as GeoTIFF",research_geotiff(raster),re.sub(r"\W+","_",sid)+".tif","image/tiff")
            else:st.warning("This scene has no usable water pixels. No water-quality conclusion can be drawn.")


def research_stats_page(run,lab):
    st.subheader("Statistical analysis")
    sources={}
    if lab["field"] is not None:sources["Included field measurements"]=lab["field"].loc[lab["field"].included].copy()
    if lab["matchups"] is not None:sources["Accepted field/satellite matchups"]=lab["matchups"].loc[lab["matchups"].matched.fillna(False)].copy()
    for module,result in run["results"].items():
        if module=="Research validation":continue
        for title,f in result.get("tables",{}).items():
            if len(f)>=3:sources[module+" / "+title]=f.copy()
    upload,custom=research_upload_widget("Optional analysis table (already aligned observations)","research_custom_stats")
    if custom is not None:sources["Uploaded analysis table"]=custom
    if not sources:st.info("Attach field data or run environmental analysis to supply a statistical table.");return
    selected=st.selectbox("Input table",list(sources));frame=sources[selected]
    st.caption(f"{len(frame)} rows. The analysis uses only the selected table. Uploaded analysis tables must already align observations by sample, place and time.")
    numeric=[c for c in frame if pd.to_numeric(frame[c],errors="coerce").notna().sum()>=3 and not pd.api.types.is_bool_dtype(frame[c]) and c not in ("source_row","pixel_row","pixel_col") and "date" not in str(c).lower()]
    if len(numeric)<2:st.info("This table needs at least two numeric variables for the selected research tools.");return
    methods={"Correlation":"correlation","Linear regression / GAM":"regression","PCA":"pca","Clustering":"cluster","Seasonal decomposition":"seasonal","Evaluate supplied estimates":"agreement"}
    label=st.selectbox("Method",list(methods));action=methods[label]
    s={"seed":42,"resamples":499,"source_table":selected}
    st.caption(RESEARCH_METHODS[action])
    if action in ("correlation","pca","cluster"):
        preferred=[c for c in numeric if c in RESEARCH_NUMERIC or c in ("sat_ndci","sat_red_reflectance","sat_surface_temperature_c")]
        s["columns"]=st.multiselect("Variables",numeric,default=(preferred or numeric)[:min(3,len(preferred or numeric))])
        if action=="correlation":s["independent"]=st.checkbox("Rows are independent sampling units for inference",False,help="Leave off for repeated site/date observations without an appropriate dependence model. Descriptive correlations remain available.")
        if action=="cluster":
            s["distance"]=st.selectbox("Distance",["Standardized Euclidean","Bray-Curtis"])
            s["clusters"]=st.number_input("Number of exploratory clusters",2,10,3)
    elif action=="regression":
        s["response"]=st.selectbox("Measured response",numeric,index=numeric.index("chlorophyll_ug_l") if "chlorophyll_ug_l" in numeric else 0)
        candidates=[c for c in numeric if c!=s["response"]]
        s["predictors"]=st.multiselect("Predictors (maximum 3)",candidates,default=["sat_ndci"] if "sat_ndci" in candidates else candidates[:1])
        groups=[c for c in ("scene_id","site","date","acquisition_utc") if c in frame]
        if not groups:groups=list(frame.columns)
        s["group"]=st.selectbox("Hold out complete groups",groups)
        s["model"]=st.selectbox("Model",["Linear","Gaussian GAM (cubic splines)"])
        s["smoothing"]=st.number_input("Spline penalty",.01,1000.,1.,.1,disabled=s["model"]=="Linear")
        st.info("A model is evaluated on withheld groups. This does not establish transferability to another reservoir or optical regime. No concentration map is extrapolated automatically.")
    elif action=="agreement":
        s["reference"]=st.selectbox("Field reference column",numeric)
        s["estimate"]=st.selectbox("Estimated value column",[c for c in numeric if c!=s["reference"]])
        s["same_units"]=st.checkbox("Both columns represent the same physical quantity in the same units",False)
        if "ndci" in s["estimate"].lower() or "reflectance" in s["estimate"].lower():
            st.warning("An optical index or reflectance cannot be evaluated as a chlorophyll/turbidity concentration.")
            s["same_units"]=False
    else:
        if "date" not in frame:st.info("Rename your sampling-time column to date for seasonal analysis.");return
        s["column"]=st.selectbox("Measured variable",numeric)
        if "site" in frame:s["site"]=st.selectbox("Site",sorted(frame.site.dropna().astype(str).unique()))
        st.caption("Monthly decomposition requires continuous observations spanning at least two annual cycles. Six satellite scenes cannot establish annual seasonality.")
    if st.button("Run and record analysis",type="primary"):
        try:
            if action in ("correlation","pca","cluster") and len(s["columns"])<2:raise ValueError("Select at least two variables.")
            if action=="regression" and not 1<=len(s["predictors"])<=3:raise ValueError("Select one to three predictors.")
            with st.spinner("Calculating from the selected table…"):rec=research_record(run,lab,action,frame,s)
            if selected=="Uploaded analysis table":lab["uploads"]["analysis_"+re.sub(r"[^a-zA-Z0-9_.-]","_",upload.name)]=upload.getvalue()
            st.success("Analysis recorded. See the result and its method below.")
        except Exception as exc:st.error(f"Analysis not run: {str(exc)[:400]}")
    records=[r for r in lab["records"] if r["action"]==action]
    if records:research_show_record(records[-1])


def research_phyto_page(run,lab):
    st.subheader("Phytoplankton community")
    st.write("Use one row per sample and taxon. Join samples to the field workbook by sample_id. Lab counts, sampled volume, depth and identification method should accompany the original dataset.")
    upload,frame=research_upload_widget("Upload community abundance","research_phyto_file")
    if frame is not None:
        mapping_columns=research_mapping(frame,["sample_id","taxon","abundance"],"phytomap",("sample_id","taxon","abundance"))
        a,b=st.columns(2);unit=a.selectbox("One abundance unit for the entire table",["cells/mL","cells/L","biovolume mm³/L","count per equal sampled volume"])
        rank=b.selectbox("Taxonomic resolution",["Genus","Species"])
        absent=st.checkbox("All listed taxa were searched for in every sample; unlisted combinations are confirmed absent",False)
        comparable=st.checkbox("Sampling effort, units and taxonomic resolution are comparable; no genus/species double counting",False)
        if st.button("Analyse community",type="primary",disabled=not comparable):
            try:
                if len(mapping_columns)!=3:raise ValueError("Map sample_id, taxon and abundance.")
                tidy=pd.DataFrame({k:frame[v] for k,v in mapping_columns.items()})
                rec=research_record(run,lab,"community",tidy,{"unlisted_absent":absent,"abundance_unit":unit,"taxonomic_rank":rank})
                lab["community"]=rec["output"]["tables"]["Community abundance"]
                lab["uploads"]["community_"+re.sub(r"[^a-zA-Z0-9_.-]","_",upload.name)]=upload.getvalue()
                st.success("Community analysis recorded.")
            except Exception as exc:st.error(str(exc)[:400])
    records=[r for r in lab["records"] if r["action"]=="community"]
    if records:research_show_record(records[-1])
    if lab["community"] is not None and lab["field"] is not None:
        st.subheader("Relate community composition to measured environment")
        community=lab["community"].copy();taxa=[c for c in community if c!="sample_id"]
        community=community.rename(columns={c:"taxon::"+c for c in taxa});taxa=["taxon::"+c for c in taxa]
        field=lab["field"].loc[lab["field"].included].copy()
        combined=community.merge(field,on="sample_id",how="inner",validate="one_to_one")
        st.caption(f"{len(combined)} community samples join to included field observations. Unmatched sample IDs are not inferred.")
        options=[c for c in RESEARCH_NUMERIC if c in combined and combined[c].notna().any()]
        chosen=st.multiselect("Environmental constraints for RDA",options,default=options[:2])
        independent=st.checkbox("Joined samples are independent for an unrestricted permutation test",False)
        if st.button("Run Hellinger RDA",disabled=not chosen):
            try:research_record(run,lab,"rda",combined,{"environment":chosen,"taxa":taxa,"independent":independent,"seed":42,"resamples":499})
            except Exception as exc:st.error(str(exc)[:400])
        rdas=[r for r in lab["records"] if r["action"]=="rda"]
        if rdas:research_show_record(rdas[-1])
    st.info("Community–nutrient associations do not establish causation. Cyanobacteria abundance, phycocyanin and chlorophyll may guide further investigation; this app does not manufacture a bloom probability or infer toxin concentration.")


def research_models_page(run,lab):
    st.subheader("External water-model data exchange")
    choices={"WASP":"https://www.epa.gov/hydrowq/water-quality-analysis-simulation-program-wasp",
        "AQUATOX":"https://www.epa.gov/hydrowq/aquatox","CE-QUAL-W2":"https://www.cee.pdx.edu/w2/",
        "EcoDynamo":"https://www.sciencedirect.com/science/article/abs/pii/S1574954106000720"}
    model=st.selectbox("External model",list(choices))
    st.warning("These simulators do not execute inside this app. Export study data for a qualified model setup, then import the model's saved outputs. The export is a generic exchange package, not a runnable model project.")
    st.markdown(f"[Model information]({choices[model]})")
    st.write("A defensible simulation needs a suitable domain and model assumptions, bathymetry where required, forcing and boundary data, parameters, calibration and independent evaluation. A satellite image cannot replace these inputs.")
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("study.json",research_json(run["study"]))
        if lab["field"] is not None:z.writestr("field_observations.csv",safe_frame(lab["field"]).to_csv(index=False))
        for mod in ("Climate","River outlook"):
            for title,f in run["results"].get(mod,{}).get("tables",{}).items():z.writestr(re.sub(r"\W+","_",mod+"_"+title)+".csv",safe_frame(f).to_csv(index=False))
        z.writestr("README.txt",f"Generic study-data exchange for {model}. Not a runnable model project. Preserve units and distinguish forecasts from observations. Configure and validate the external solver separately.")
    st.download_button("Export study data for external modelling",b.getvalue(),"aquaterra_model_data.zip","application/zip")
    upload,frame=research_upload_widget("Import saved external model outputs","research_model_outputs")
    if frame is not None:
        st.dataframe(frame.head(15),hide_index=True,width="stretch")
        st.caption("Required columns: date, site, parameter, value, unit, scenario. Outputs retain their status as external model estimates.")
        version=st.text_input("Model version and run identifier")
        if st.button("Attach external model results",disabled=not version.strip()):
            try:
                required={"date","site","parameter","value","unit","scenario"}
                if not required.issubset(frame):raise ValueError("Supply all six required columns.")
                f=frame.copy();f["date"]=pd.to_datetime(f.date,utc=True,errors="raise").astype(str)
                f["value"]=pd.to_numeric(f.value,errors="raise")
                if f[list(required)].isna().any().any() or not np.isfinite(f.value).all():raise ValueError("Model outputs contain missing or non-finite required values.")
                f["model"]=model;f["model_version_run"]=version.strip();f["status"]="External model estimate; calibration not verified by AquaTerra"
                output={"tables":{"Imported model outputs":f},"notes":["Imported from an external simulator. AquaTerra did not execute or verify the solver or its calibration."],"plots":[]}
                research_record(run,lab,"external_model_import",f,{"model":model,"version_run":version,"method":"Import and validate output schema; no simulation executed"},output)
                lab["uploads"]["model_"+re.sub(r"[^a-zA-Z0-9_.-]","_",upload.name)]=upload.getvalue()
                st.success("External estimates attached with their provenance label.")
            except Exception as exc:st.error(str(exc)[:350])
    records=[r for r in lab["records"] if r["action"]=="external_model_import"]
    if records:research_show_record(records[-1])


def research_audit_page(run,lab):
    st.subheader("Execution record and reproducibility")
    st.write("Each record links a source snapshot, processing settings, calculation, result and limitations. These are actual function executions. AI interpretations remain separately labelled under AI team.")
    if lab["records"]:
        st.dataframe(pd.DataFrame([{"record":r["id"],"calculation":r["action"],"input_rows":len(r["input"]),"executed_utc":r["executed_utc"],"input_hash":r["input_sha256"][:16]} for r in lab["records"]]),hide_index=True,width="stretch")
        selected=st.selectbox("Inspect a recorded analysis",[r["id"] for r in lab["records"]])
        research_show_record(next(r for r in lab["records"] if r["id"]==selected))
        if st.button("Build research report and reproducibility ZIP",type="primary"):
            try:
                with st.spinner("Saving data, figures, code and reproducibility records…"):
                    with report_lock():lab["download"]=research_package(run,lab)
                st.success("Research package is ready.")
            except Exception as exc:st.error(f"Export stopped: {str(exc)[:300]}")
        if lab.get("download"):st.download_button("Download research package",lab["download"],"aquaterra_reproducible_research.zip","application/zip",type="primary")
    else:st.info("Execute a field-data check or research analysis to create an inspectable record.")
    st.caption("The package includes original uploads, processed tables, 300 dpi PNG and vector figures, methods, settings, source code and an offline reproduce.py. Satellite matching can be repeated from saved processed windows; full atmospheric processing is not claimed to be reproducible from those windows alone.")
    st.caption("Use Reports & sources for the original environmental PDF/Excel exports and AI briefing. This research workspace has its own detailed package. Scientific suitability depends on independent measurements and review; attractive figures alone do not establish publication validity.")


def research_page(run):
    banner("Research workspace","Field validation, ecological communities and methods you can inspect.")
    if not need_run(run):return
    lab=research_state(run)
    section=st.radio("Research tools",["Field data","Sampling points","Satellite matchups","Statistics","Phytoplankton","External models","Methods & downloads"],horizontal=True,key="research_section")
    functions={"Field data":research_field_page,"Sampling points":research_sites_page,"Satellite matchups":research_satellite_page,
               "Statistics":research_stats_page,"Phytoplankton":research_phyto_page,"External models":research_models_page,"Methods & downloads":research_audit_page}
    try:functions[section](run,lab)
    except Exception as exc:
        st.error(f"This research view could not complete ({type(exc).__name__}). Saved inputs remain available. Check column names, dates, units and the selected method.")
        with st.expander("Diagnostic detail"):st.code(str(exc)[:500])



def research_agent_tools(store,domain,activity):
    from crewai_compat import tool
    def record(name,args,payload):
        text=research_json(payload)
        activity.append({"agent":domain,"event":"tool","tool":name,"arguments":args,
            "output_sha256":hashlib.sha256(text.encode()).hexdigest(),"result":text[:5000],
            "result_truncated":len(text)>5000,"executed_utc":utc_now()})
        return text
    @tool("read_evidence")
    def read_evidence(module: str="all") -> str:
        """Read actual source IDs, calculated facts, limitations and table names in this agent's scope."""
        payload=store.evidence(domain,module)
        if len(research_json(payload))>10000:payload=store.evidence(domain,module,compact=True)
        return record("read_evidence",{"module":module},payload)
    @tool("table_statistics")
    def table_statistics(module: str,table: str,column: str,operation: str="mean") -> str:
        """Calculate a supported summary from a saved numeric evidence table; no generated or assumed data."""
        args={"module":module,"table":table,"column":column,"operation":operation}
        return record("table_statistics",args,store.statistics(domain,module,table,column,operation))
    @tool("quality_checks")
    def quality_checks() -> str:
        """Read computed study coverage, missing-evidence and scope checks."""
        return record("quality_checks",{},store.check_scope(domain))
    return [read_evidence,table_statistics,quality_checks]

if __name__ == "__main__":
    main()
