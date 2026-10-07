"""HydroScope Water Research: a separate Streamlit research application.
Deploy the folder contents with app.py at the repository root and Python 3.12.
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
from ai_providers import DEFAULT_PROVIDER, PROVIDERS
from evidence import quality_findings, interpretation_is_current, run_fingerprint
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
    plain_metadata,
    raster_png,
    safe_frame,
    secret,
    utc_now
)

APP_RELEASE = "1.1.0"
PAGES = list(PAGES)
if "Water data" not in PAGES:PAGES.insert(PAGES.index("Water research"), "Water data")

def inject_theme():
    st.html("""<style>
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
        if module not in modules or table_name not in ["Sampling candidates", "Included field observations"] or frame.empty:
            continue
        group = folium.FeatureGroup(name=table_name)
        for _, row in frame.iterrows():
            if pd.isna(row.latitude) or pd.isna(row.longitude):continue
            radius, color, title = 6, "#128C80", table_name
            if table_name == "Sampling candidates":
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


def need_run(run):
    if run:
        st.caption(f"Viewing run {run['id']} · {run['study']['label']} · historical period {run['study']['start']} to {run['study']['end']}")
        return True
    st.info("Save a water study first. Each results page uses the saved study boundary and dates.")
    st.button("Set up your study",type="primary",on_click=go_page,args=("Water study",))
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
    banner("Satellite water maps","Surface observations, optical screening and areas to investigate.")
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
            st.download_button("Download all indices as GeoTIFF",geotiff_bytes(r),file_name="hydroscope_satellite_indices.tif",mime="image/tiff")
    module_view(run,"Satellite")
    st.info("For measured eutrophication indicators, upload field samples in Water research → Field data. Satellite indices alone do not establish nutrient concentration, toxicity or drinking-water safety.")


@st.cache_resource
def report_lock():
    return threading.Lock()


# RESEARCH_ENGINE_START
# This exact block is included in the offline reproduction package.
RESEARCH_ENGINE_VERSION = "2026.10.07.water.2"
RESEARCH_NUMERIC = ["chlorophyll_ug_l", "turbidity_ntu", "secchi_m", "temperature_c",
    "total_phosphorus_ug_l", "total_nitrogen_mg_l", "dissolved_oxygen_mg_l", "ph",
    "phycocyanin_ug_l", "cyanobacteria_cells_ml", "salinity_psu", "conductivity_us_cm",
    "nitrate_mg_n_l", "nitrite_mg_n_l", "ammonium_mg_n_l", "orthophosphate_ug_p_l",
    "dissolved_organic_carbon_mg_l", "silica_mg_si_l", "bod5_mg_l", "cod_mg_l",
    "alkalinity_mg_caco3_l", "total_suspended_solids_mg_l", "oxygen_saturation_pct", "discharge_m3_s"]
RESEARCH_METHODS = {
    "trophic": "Separate natural-log Carlson indices from measured lake/reservoir chlorophyll, Secchi depth and phosphorus; explicit applicability confirmation required.",
    "water_summary": "Observed per-site descriptive statistics and per-site monthly means. No gap filling, spatial extrapolation or inferential test.",
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


def research_trophic(frame, settings):
    if settings.get("waterbody_type") not in ("Lake", "Reservoir") or not settings.get("confirmed"):
        raise ValueError("Carlson TSI requires an explicitly confirmed freshwater lake/reservoir application.")
    out=frame[[c for c in ("sample_id","site","date") if c in frame]].copy()
    equations={"chlorophyll_ug_l":(9.81,30.6,"tsi_chlorophyll"),"secchi_m":(-14.41,60.0,"tsi_secchi"),
               "total_phosphorus_ug_l":(14.42,4.15,"tsi_phosphorus")}
    for source,(slope,intercept,target) in equations.items():
        if source in frame:
            values=pd.to_numeric(frame[source],errors="coerce")
            out[source]=values
            out[target]=slope*np.log(values.where(values>0))+intercept
    if not any(c.startswith("tsi_") for c in out):
        raise ValueError("Provide measured chlorophyll-a, Secchi depth or total phosphorus in the stated units.")
    notes=["Measured-input Carlson indices, calculated separately; no composite/average trophic score.",
           "TSI(Chl)=9.81 ln(Chl µg/L)+30.6; TSI(SD)=60−14.41 ln(SD m); TSI(TP)=14.42 ln(TP µg/L)+4.15.",
           "Only positive measurements yield an index. Applicability is user-confirmed, not independently validated.",
           "Non-algal turbidity, water colour, depth, nutrient limitation and unusual optical conditions can invalidate interpretation. Not a cyanobacterial/toxin or water-safety test.",
           "Reference: Carlson (1977); https://www.nalms.org/secchidipin/monitoring-methods/trophic-state-equations/"]
    return {"tables":{"Measured trophic indices":out},"notes":notes,"plots":[]}


def research_water_summary(frame, settings):
    columns=[c for c in settings.get("columns",[]) if c in RESEARCH_NUMERIC and c in frame]
    if not columns:raise ValueError("Select measured water-quality variables.")
    f=frame.copy();f["date"]=pd.to_datetime(f.date,utc=True,errors="coerce")
    f["month"]=f.date.dt.strftime("%Y-%m")
    site_rows=[];month_rows=[];tables={};plots=[]
    for c in columns:
        f[c]=pd.to_numeric(f[c],errors="coerce")
        for site,g in f.groupby("site",sort=True):
            vals=g[c].dropna()
            site_rows.append({"site":site,"variable":c,"n":len(vals),"mean":vals.mean(),"median":vals.median(),
                              "sd":vals.std(ddof=1),"min":vals.min(),"max":vals.max()})
        for (site,month),g in f.groupby(["site","month"],sort=True):
            vals=g[c].dropna()
            month_rows.append({"site":site,"month":month,"variable":c,"n":len(vals),"mean":vals.mean(),"median":vals.median()})
        name="Observed "+c
        tables[name]=f[[c for c in ("sample_id","site","date",c) if c in f]].copy()
        plots.append({"kind":"scatter","table":name,"x":"date","y":c,"group":"site","title":"Observed "+c+"; no gap filling"})
    tables["Site descriptive statistics"]=pd.DataFrame(site_rows)
    tables["Monthly observed means"]=pd.DataFrame(month_rows)
    return {"tables":tables,"plots":plots,"notes":[
        "Per-site descriptive statistics and observed monthly means. Unequal sampling and missing months remain explicit; no spatial interpolation or area weighting.",
        "Site differences are descriptive, not proof of significance or causation. Temporal coverage follows actual sampling, not the entire selected date range."]}


def research_compute(action, frame, settings):
    s=settings;rng=np.random.default_rng(int(s.get("seed",42)))
    if action=="water_archive": return water_archive_analysis(frame,s)
    if action=="water_species": return water_species_analysis(frame,s)
    if action=="nutrient_balance": return water_nutrient_balance(frame,s)
    if action=="clean": return research_clean(frame,s)
    if action=="trophic": return research_trophic(frame,s)
    if action=="water_summary": return research_water_summary(frame,s)
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
# Pure, offline-replayable calculations for retrieved/imported observations.
WATER_ARCHIVE_METHOD = "Exact boundary/date filtering; explicit units and chemical fractions; non-detects and flagged values excluded from numeric summaries, never replaced with zero. Descriptive statistics per source/parameter/unit/fraction/depth/method. No spatial extrapolation."
RESEARCH_METHODS['water_archive'] = WATER_ARCHIVE_METHOD
RESEARCH_METHODS['water_species'] = "Coordinate/date checks on occurrence records; deduplication by GBIF ID; counts of records and named taxa. Occurrences are not abundance, absence, ecological richness estimates or bloom diagnoses."
RESEARCH_METHODS['nutrient_balance'] = "Explicitly confirmed same-event, same-depth elemental TN and TP measurements; complete positive observations; mass ratio TN/TP and molar ratio (TN/14.0067)/(TP/30.973762). No nutrient-limitation diagnosis."


def water_archive_analysis(frame, s):
    if len(frame)>50000:raise ValueError('Limit the selection to 50,000 observations.')
    f=frame.copy().reset_index(drop=True)
    required=['site','date','latitude','longitude','parameter','unit','reported_value']
    if any(c not in f for c in required):raise ValueError('Required columns: '+', '.join(required))
    for c,default in {'source':'User import','fraction':'Unspecified','method':'Unspecified','depth_m':np.nan,
                      'qualifier':'','quality_flag':'','sample_id':'','reference':'','license':'','record_id':''}.items():
        if c not in f:f[c]=default
    for c in ['source','site','parameter','unit','fraction','method','sample_id','qualifier','quality_flag']:
        f[c]=f[c].fillna('').astype(str).str.strip()
    for c in ['latitude','longitude','depth_m']:f[c]=pd.to_numeric(f[c],errors='coerce').replace([np.inf,-np.inf],np.nan)
    f['date_original']=f.date.astype(str)
    f['date']=pd.to_datetime(f.date,errors='coerce',utc=True,format='mixed')
    text=f.reported_value.fillna('').astype(str).str.strip()
    f['value']=pd.to_numeric(text,errors='coerce').replace([np.inf,-np.inf],np.nan)
    f['censored']=text.str.contains(r'[<>≤≥]|\b(?:ND|BDL|LOD|LOQ)\b',case=False,regex=True) | f.qualifier.str.contains(r'[<>≤≥]',regex=True)
    f['qualified']=f.qualifier.ne('')
    polygon=shape(s['geometry'])
    coords=f.latitude.between(-90,90)&f.longitude.between(-180,180)
    inside=pd.Series(False,index=f.index)
    for i in f.index[coords]:inside.at[i]=polygon.covers(Point(f.at[i,'longitude'],f.at[i,'latitude']))
    f['inside_study']=inside
    f['in_period']=f.date.dt.strftime('%Y-%m-%d').between(s['start'],s['end']).fillna(False)
    # Negative temperatures/ORP may be physically meaningful. Other negative values are audited.
    negative_ok=f.parameter.str.contains(r'temp|redox|oxidation.reduction|orp',case=False,regex=True)
    bad_range=(f.value<0)&~negative_ok
    ph=f.parameter.str.fullmatch(r'pH(?:\s.*)?',case=False)
    bad_range|=ph & ~f.value.between(0,14)
    checks={'outside boundary or invalid coordinates':~inside,'outside period or invalid date':~f.in_period,
            'date lacks an explicit calendar day':~f.date_original.str.match(r'^\d{4}-\d{2}-\d{2}(?:$|[ T])'),
            'missing site/parameter/unit':f.site.eq('')|f.parameter.eq('')|f.unit.eq(''),
            'non-numeric or missing value':f.value.isna(),'censored / qualifier present':f.censored|f.qualified,
            'provider quality flag':f.quality_flag.ne(''),'invalid numeric range':bad_range,
            'negative sampling depth':f.depth_m.lt(0)}
    f['exclusion_reason']=['; '.join(k for k,v in checks.items() if bool(v.iloc[i])) for i in range(len(f))]
    f['included']=f.exclusion_reason.eq('')
    f['analysis_value']=f.value.where(f.included)
    f['date']=f.date.dt.strftime('%Y-%m-%d')
    f['series']=f.source+' | '+f.parameter+' ['+f.unit+'] | '+f.fraction+' | depth '+f.depth_m.astype(str)+' m | '+f.method
    usable=f.loc[f.included].copy();usable['month']=pd.to_datetime(usable.date,utc=True).dt.strftime('%Y-%m')
    group=['source','parameter','unit','fraction','depth_m','method']
    coverage=f.groupby(group,dropna=False).agg(records=('included','size'),numeric_records=('included','sum'),
                  sites=('site','nunique'),first_date=('date','min'),last_date=('date','max'),censored_records=('censored','sum'),qualified_records=('qualified','sum')).reset_index()
    stats=usable.groupby(group+['site'],dropna=False).analysis_value.agg(['count','mean','median','std','min','max']).reset_index()
    monthly=usable.groupby(group+['site','month'],dropna=False).analysis_value.agg(['count','mean','median']).reset_index()
    tables={'Observation audit':f,'Usable observations':usable,'Parameter coverage':coverage,
            'Site statistics':stats,'Monthly statistics':monthly}
    plots=[]
    for i,series in enumerate(usable.series.drop_duplicates().head(8)):
        name=f'Observed series {i+1}'
        tables[name]=usable.loc[usable.series.eq(series),['date','analysis_value','site','latitude','longitude']].copy()
        plots.append({'kind':'scatter','table':name,'x':'date','y':'analysis_value','group':'site','title':str(series)[:150]})
        if i<2:plots.append({'kind':'map','table':name,'x':'longitude','y':'latitude','value':'analysis_value','geometry':s['geometry'],'title':'Site medians: '+str(series)[:120]})
    return {'tables':tables,'plots':plots,'notes':[WATER_ARCHIVE_METHOD,
        'Archive observations are secondary measurements. Laboratories, methods, representativeness and detection limits still require review.',
        'Non-detects and any provider qualifiers remain in the audit. Excluding them can bias summaries; no censored-data estimator is fitted.',
        'Observed means are sample-weighted, not area-weighted waterbody estimates. Graphs display at most eight series; all tables are exported.',
        'Depths and methods remain separate; an unspecified method or depth means unreported, not equivalent sampling. No implicit concentration conversion.',
        'Archive dates are used as reported calendar days. GEMStat default times (00:00/12:00) are not treated as known sampling times.']}


def water_species_analysis(frame,s):
    f=frame.copy().reset_index(drop=True)
    columns=['gbif_id','scientific_name','taxon_key','rank','species','date','latitude','longitude','dataset_key','license','basis_of_record','coordinate_uncertainty_m','issues']
    for c in columns:
        if c not in f:f[c]=''
    f['latitude']=pd.to_numeric(f.latitude,errors='coerce');f['longitude']=pd.to_numeric(f.longitude,errors='coerce')
    dt=pd.to_datetime(f.date,utc=True,errors='coerce',format='mixed')
    polygon=shape(s['geometry'])
    f['inside_study']=[bool(pd.notna(x) and pd.notna(y) and -180<=x<=180 and -90<=y<=90 and polygon.covers(Point(x,y))) for x,y in zip(f.longitude,f.latitude)]
    f['in_period']=dt.dt.strftime('%Y-%m-%d').between(s['start'],s['end']).fillna(False)
    f['duplicate_id']=f.gbif_id.astype(str).duplicated()
    f['date_precision_sufficient']=f.date.astype(str).str.match(r'^\d{4}-\d{2}-\d{2}(?:$|[ T])')
    f['included']=f.inside_study & f.in_period & f.date_precision_sufficient & ~f.duplicate_id & f.gbif_id.astype(str).ne('')
    good=f.loc[f.included].copy()
    taxa=good.groupby(['scientific_name','taxon_key','rank'],dropna=False).size().rename('occurrence_records').reset_index().sort_values('occurrence_records',ascending=False)
    good['year']=pd.to_datetime(good.date,utc=True,errors='coerce',format='mixed').dt.year
    years=good.groupby('year').size().rename('occurrence_records').reset_index()
    datasets=good.groupby(['dataset_key','license'],dropna=False).size().rename('occurrence_records').reset_index()
    return {'tables':{'Occurrence audit':f,'Included occurrences':good,'Recorded taxa':taxa,'Records by year':years,'Dataset attribution':datasets},
       'plots':[{'kind':'bar','table':'Recorded taxa','x':'scientific_name','y':'occurrence_records','title':'Occurrence records per taxon (maximum 60 shown)'},
                {'kind':'map','table':'Included occurrences','x':'longitude','y':'latitude','geometry':s['geometry'],'title':'Retrieved species occurrence locations'}] if len(taxa) else [],
       'notes':['GBIF occurrence counts reflect observation and digitisation effort; they are not organism counts, abundance or population trends.',
                'No records does not establish absence. Diatom/cyanobacteria occurrences do not prove a current bloom or toxin production.',
                'Coordinates within the boundary do not verify an aquatic habitat. Inspect uncertainty, taxonomy, dates and original datasets.',
                'For publication, obtain a GBIF download DOI for the final selection and cite contributing datasets. Search snapshots are retained for offline analysis.']}


def water_nutrient_balance(frame,s):
    if not s.get('confirmed'):raise ValueError('Confirm common sample, depth, time, units and elemental basis first.')
    f=frame.copy();tn=pd.to_numeric(f[s['tn']],errors='coerce')*float(s['tn_factor'])
    tp=pd.to_numeric(f[s['tp']],errors='coerce')*float(s['tp_factor'])
    valid=np.isfinite(tn)&np.isfinite(tp)&tn.gt(0)&tp.gt(0)
    out=f[[c for c in ['sample_id','site','date','depth_m'] if c in f]].copy()
    out['tn_mg_N_L']=tn;out['tp_mg_P_L']=tp;out['positive_complete_pair']=valid
    out['TN_TP_mass_ratio']=(tn/tp).where(valid)
    out['TN_TP_molar_ratio']=(tn*30.973762/(tp*14.0067)).where(valid)
    return {'tables':{'Paired nutrient ratios':out},'plots':[],
            'notes':['Only positive complete TN/TP pairs are used. Values must be elemental nitrogen and phosphorus per litre.',
                     'Ratios alone do not establish nutrient limitation or eutrophication status. DIN, nitrate and orthophosphate are not total N/P.']}

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
    out["sources"]=[source_record("R1","HydroScope research engine / user-supplied measurements","Calculated research results",
        utc_now(),f"{run['study']['start']} to {run['study']['end']}","Sample-level; match quality is explicit",
        "Executed Python analyses with recorded inputs, settings and methods. Field quality is not independently verified.")]
    out["notes"]=["Satellite indices are dimensionless; field concentrations remain separately labelled. No automatic toxicity or bloom probability.",
        "Each calculation has its own audit record and input snapshot. An AI explanation does not constitute scientific validation.",
        "Statistical inference is unavailable unless the user declares independent sampling units. Review repeated sites/dates."]
    for rec in lab["records"]:
        for title,df in rec["output"]["tables"].items():out["tables"][rec["id"]+" "+title]=df
        out["notes"].append(f"{rec['id']} method: {rec['method']}")
        out["notes"].extend(f"{rec['id']}: {n}" for n in rec["output"].get("notes",[]))
        out["facts"].append(f"[R1] {rec['id']}: {rec['action']} executed on {len(rec['input'])} rows. See the associated tables and recorded limitations; execution is not evidence of accuracy.")
    out["metrics"]={"Executed research analyses":len(lab["records"]),"Uploaded reference observations":len(lab["field"]) if lab["field"] is not None else 0}
    run["results"]["Research validation"]=out
    if lab["field"] is not None:
        f=lab["field"].copy()
        field=result("Field observations")
        field["tables"]={"Field observations audit":f,"Included field observations":f.loc[f.included].copy()}
        field["metrics"]={"Included field observations":int(f.included.sum())}
        field["facts"]=[f"[U1] {int(f.included.sum())}/{len(f)} uploaded samples pass basic inclusion checks; laboratory accuracy is unverified."]
        field["sources"]=[source_record("U1","User-supplied field measurements","Unverified reference observations",utc_now(),
            f"{run['study']['start']} to {run['study']['end']}","Sample coordinates; spatial support and sampling depth vary",
            "Explicit column/unit mapping, local-date inclusion and UTC conversion. Missing coordinates remain available for nonspatial statistics; no imputation.")]
        field["notes"]=["Measurements are user-supplied, not independently verified. Spectral indices are not measured concentrations."]
        run["results"]["Field observations"]=field
    st.session_state.pop("interpretation",None);st.session_state.pop("exports",None)
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
    if spec["kind"]=="map":
        geom=shape(spec["geometry"])
        for poly in (geom.geoms if geom.geom_type=="MultiPolygon" else [geom]):
            xx,yy=poly.exterior.xy;ax.plot(xx,yy,color="#405b75",linewidth=1)
            for ring in poly.interiors:
                xx,yy=ring.xy;ax.plot(xx,yy,color="#405b75",linewidth=.6)
        if spec.get("value"):
            value=spec["value"]
            draw=f.groupby(["site",x,y],dropna=False)[value].median().reset_index()
            sc=ax.scatter(draw[x],draw[y],c=draw[value],cmap="viridis",s=42,edgecolors="white",linewidth=.4)
            fig.colorbar(sc,ax=ax,label="Site median; units in title")
        else:ax.scatter(f[x],f[y],s=18,alpha=.65,color="#7755a3")
        ax.set_aspect(1/max(.1,math.cos(math.radians(geom.centroid.y))))
        ax.ticklabel_format(style="plain",useOffset=False)
    elif spec["kind"]=="line":
        xx=pd.to_datetime(f[x],utc=True,errors="coerce") if x=="date" else f[x]
        ax.plot(xx,pd.to_numeric(f[y],errors="coerce"),color="#087f8c",linewidth=1.6,marker="o",markersize=3)
        fig.autofmt_xdate()
    elif spec["kind"]=="bar":
        draw=f.head(60);ax.bar(draw[x].astype(str),pd.to_numeric(draw[y],errors="coerce"),color="#087f8c")
        ax.tick_params(axis="x",rotation=65,labelsize=7)
    else:
        group=spec.get("group")
        if group and group in f:
            for label,d in f.groupby(group,dropna=False):ax.scatter((pd.to_datetime(d[x],utc=True,errors="coerce") if x=="date" else pd.to_numeric(d[x],errors="coerce")),pd.to_numeric(d[y],errors="coerce"),s=24,alpha=.8,label=str(label))
            ax.legend(frameon=False,fontsize=8)
        else:ax.scatter((pd.to_datetime(f[x],utc=True,errors="coerce") if x=="date" else pd.to_numeric(f[x],errors="coerce")),pd.to_numeric(f[y],errors="coerce"),s=25,color="#087f8c",alpha=.8)
        if spec.get("one_to_one"):
            values=f[[x,y]].apply(pd.to_numeric,errors="coerce").to_numpy();values=values[np.isfinite(values)]
            if len(values):ax.plot([values.min(),values.max()],[values.min(),values.max()],"--",color="#725c92",linewidth=1,label="1:1")
    if x=="date":fig.autofmt_xdate()
    ax.set(xlabel=x,ylabel=y,title=spec["title"]);ax.grid(alpha=.2)
    ax.spines[["top","right"]].set_visible(False)
    fig.text(.01,.002,"HydroScope | source and methods in accompanying audit record",fontsize=7,color="#444444")
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


def research_package(run,lab,include_interpretation=True):
    import importlib.metadata
    source=Path(__file__).read_text(encoding="utf-8")
    engine=source.split("# RESEARCH_ENGINE_START\n",1)[1].split("# RESEARCH_ENGINE_END",1)[0]
    manifest={"application":APP_RELEASE,"engine":RESEARCH_ENGINE_VERSION,"study":run["study"],"created_utc":utc_now(),"records":[],"files":{},"snapshots":[]}
    content={};report=["# HydroScope research report","",f"Study: {run['study']['label']}",
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
        point_table=rec["output"]["tables"].get("Usable observations",rec["output"]["tables"].get("Included occurrences"))
        if point_table is not None and {"latitude","longitude"}.issubset(point_table):
            features=[]
            for _,point in point_table.iterrows():
                if pd.isna(point.latitude) or pd.isna(point.longitude):continue
                properties={c:point[c] for c in ["site","date","parameter","unit","analysis_value","depth_m","source","scientific_name","gbif_id","dataset_key","license"] if c in point}
                features.append({"type":"Feature","geometry":{"type":"Point","coordinates":[float(point.longitude),float(point.latitude)]},"properties":properties})
            add(root+"/observations.geojson",research_json({"type":"FeatureCollection","features":features}))
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
    for name in ("app.py","environment.py","evidence.py","water_data.py","interpretation.py","ai_providers.py","requirements.txt","METHODS.md","RESEARCH_METHODS.md","AI_PROVIDERS.md"):
        p=Path(__file__) if name=="app.py" else ROOT/name
        if p.is_file():add("source/"+name,p.read_bytes())
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
    review=st.session_state.get("interpretation")
    if include_interpretation and interpretation_is_current(run,review):add("ai_interpretation.json",research_json(review))
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
    st.caption("Freshwater and marine samples: upload observations before using statistics or interpretation.")
    st.download_button("Download blank Excel template",research_template(),"hydroscope_research_template.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    upload,frame=research_upload_widget("Upload field workbook or CSV","research_field_file")
    if frame is not None:
        st.dataframe(frame.head(8),hide_index=True,width="stretch")
        with st.expander("Map columns and confirm units",expanded=True):
            mapping_columns=research_mapping(frame,["sample_id","site","date","latitude","longitude","depth_m",*RESEARCH_NUMERIC,"laboratory_method","quality_note"],"fieldmap",("site","date"))
            st.caption("Units: chlorophyll/phycocyanin/phosphorus µg/L; nitrogen/oxygen mg/L; turbidity NTU; Secchi/depth m; temperature °C; salinity PSU; conductivity µS/cm. Mapping a column does not convert its units.")
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

        st.divider()
        st.markdown("**Record water-quality summaries for the report**")
        selected=st.multiselect("Measurements to summarise",values,default=values[:4],key="summary_vars")
        if st.button("Calculate site and monthly summaries",disabled=not selected):
            research_record(run,lab,"water_summary",f.loc[f.included].copy(),{"columns":selected})
            st.success("Site statistics, monthly summaries and plots added to the evidence and downloads.")
        if run["study"].get("waterbody_type") in ("Lake","Reservoir"):
            confirmed=st.checkbox("This is an appropriate freshwater lake/reservoir application of Carlson TSI",value=False)
            st.caption("Do not use for marine/brackish water, rivers, or sediment-driven transparency without a justified method. Indices are computed separately and never averaged.")
            if st.button("Calculate measured trophic indicators",disabled=not confirmed):
                research_record(run,lab,"trophic",f.loc[f.included].copy(),{"waterbody_type":run["study"]["waterbody_type"],"confirmed":confirmed})
                st.success("Measured trophic indicators added. Inspect Methods & downloads for the formula and limitations.")
        else:
            st.caption("Carlson lake trophic indices are disabled for rivers and sea/coastal studies.")

        recent=[r for r in lab["records"] if r["action"] in ("water_summary","trophic")]
        if recent:research_show_record(recent[-1])


def research_sites_page(run,lab):
    st.subheader("Waterbody and sampling points")
    st.write("Change the waterbody boundary in Water study. Here, click the map and save a named planned sampling point.")
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
    if sensor=="Sentinel-1 catalogue":st.info("This version provides Sentinel-1 acquisition footprints and metadata. SAR water classification and flood modelling are not implemented here.")
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
            if title in {"Usable observations","Observation audit","Parameter coverage","Site statistics","Monthly statistics","Included occurrences","Occurrence audit","Recorded taxa","Records by year","Dataset attribution"}:continue
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
        for mod in ("River outlook","Marine outlook"):
            for title,f in run["results"].get(mod,{}).get("tables",{}).items():z.writestr(re.sub(r"\W+","_",mod+"_"+title)+".csv",safe_frame(f).to_csv(index=False))
        z.writestr("README.txt",f"Generic study-data exchange for {model}. Not a runnable model project. Preserve units and distinguish forecasts from observations. Configure and validate the external solver separately.")
    st.download_button("Export study data for external modelling",b.getvalue(),"hydroscope_model_data.zip","application/zip")
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
                f["model"]=model;f["model_version_run"]=version.strip();f["status"]="External model estimate; calibration not verified by HydroScope"
                output={"tables":{"Imported model outputs":f},"notes":["Imported from an external simulator. HydroScope did not execute or verify the solver or its calibration."],"plots":[]}
                research_record(run,lab,"external_model_import",f,{"model":model,"version_run":version,"method":"Import and validate output schema; no simulation executed"},output)
                lab["uploads"]["model_"+re.sub(r"[^a-zA-Z0-9_.-]","_",upload.name)]=upload.getvalue()
                st.success("External estimates attached with their provenance label.")
            except Exception as exc:st.error(str(exc)[:350])
    records=[r for r in lab["records"] if r["action"]=="external_model_import"]
    if records:research_show_record(records[-1])


def research_audit_page(run,lab):
    st.subheader("Execution record and reproducibility")
    st.write("Each record links a source snapshot, processing settings, calculation, result and limitations. These are actual function executions. AI interpretations remain separately labelled on AI interpretation.")
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
        if lab.get("download"):st.download_button("Download research package",lab["download"],"hydroscope_reproducible_research.zip","application/zip",type="primary")
    else:st.info("Execute a field-data check or research analysis to create an inspectable record.")
    st.caption("The package includes original uploads, processed tables, 300 dpi PNG and vector figures, methods, settings, source code and an offline reproduce.py. Satellite matching can be repeated from saved processed windows; full atmospheric processing is not claimed to be reproducible from those windows alone.")
    st.caption("Use Reports & sources for the original water PDF/Excel exports and optional AI interpretation. This research workspace has its own detailed package. Scientific suitability depends on independent measurements and review; attractive figures alone do not establish publication validity.")


def research_page(run):
    banner("Water research","Field validation, phytoplankton communities and methods you can inspect.")
    if not need_run(run):return
    lab=research_state(run)
    section=st.radio("Research tools",["Field data","Sampling points","Satellite matchups","Statistics","Phytoplankton","External models","Methods & downloads"],horizontal=True,key="research_section")
    functions={"Field data":research_field_page,"Sampling points":research_sites_page,"Satellite matchups":research_satellite_page,
               "Statistics":research_stats_page,"Phytoplankton":research_phyto_page,"External models":research_models_page,"Methods & downloads":research_audit_page}
    try:functions[section](run,lab)
    except Exception as exc:
        st.error(f"This research view could not complete ({type(exc).__name__}). Saved inputs remain available. Check column names, dates, units and the selected method.")
        with st.expander("Diagnostic detail"):st.code(str(exc)[:500])




def overview(run):
    st.html("""<div class='eco-hero' style='background:linear-gradient(125deg,#0c3947,#12263c)'>
    <div class='eyebrow'>HydroScope Water Research</div><h1>Understand your water.<br>Inspect the evidence.</h1>
    <p>A focused workspace for rivers, lakes, reservoirs and coastal seas. Bring field measurements
    and satellite observations together, test relationships and export methods you can reproduce.</p>
    <span class='pill'>Water quality</span><span class='pill'>Field validation</span><span class='pill'>Reproducible research</span></div>""")
    for col, text, page in zip(st.columns(3),["Define a water study","Upload field measurements","Interpret computed results"],
                               ["Water study","Water research","AI interpretation"]):
        col.button(text,on_click=go_page,args=(page,),width="stretch")
    st.write("All calculations run in Python. The optional AI interpreter explains saved results in one request; it does not select methods, fetch data or run analyses.")
    st.dataframe(pd.DataFrame([
        {"Workspace":"Satellite water maps","What it provides":"Sentinel-2 water masks, NDCI and red-reflectance screening; real acquisition dates and clear-area coverage."},
        {"Workspace":"Water data","What it provides":"GEMStat nutrients and water-quality measurements; GBIF occurrences; ocean archive; source-aware imports, coverage and quality audits."},
        {"Workspace":"Water research","What it provides":"Excel/CSV cleaning, sites, satellite matchups, measured water quality, correlations, regression/GAM, PCA/RDA, clustering and seasonality."},
        {"Workspace":"Phytoplankton","What it provides":"Species/genus abundance, diversity, community relationships and exploratory grouping."},
        {"Workspace":"River & marine","What it provides":"Modelled river discharge or sea-surface temperature, waves, currents and sea level; distinct from measurements."},
        {"Workspace":"Reports & sources","What it provides":"PDF/HTML, Excel/CSV, map layers, scientific figures and research replay code."},
    ]),hide_index=True,width="stretch")
    st.info("Satellite screening is not a measured chlorophyll or turbidity concentration. Field validation, appropriate sampling design and researcher review remain necessary.")
    if run:
        cols=st.columns(3)
        cols[0].metric("Waterbody",run["study"]["waterbody_type"])
        cols[1].metric("Evidence modules",len(run["results"]))
        cols[2].metric("Source records",len(all_sources(run)))
    st.caption("No decorative images or custom icons. Scientific maps and plots display actual retrieved or uploaded data; no demonstration data are inserted into your study.")


def study_page():
    from water_data import WATERBODY_TYPES, available_modules
    st.title("Define your water study")
    st.caption("Choose the waterbody, inspect the boundary and save the study before uploading field data.")
    left,right=st.columns([1,1.5],gap="large")
    with left:
        kind=st.selectbox("Waterbody type",WATERBODY_TYPES,index=2,key="waterbody_kind")
        with st.expander("Find a river, lake, reservoir or coastal place"):
            query=st.text_input("Place name",placeholder="Min River, Fujian")
            st.caption("OpenStreetMap place search is user-triggered and cached. A name returns a reference point, not the complete waterbody boundary.")
            if st.button("Search waterbody"):
                if len(query.strip())<3:st.warning("Enter at least three characters.")
                else:
                    try:st.session_state["places"]=landmark_search(query.strip())
                    except DataError as exc:st.error(str(exc))
            places=st.session_state.get("places",[])
            if places:
                ix=st.selectbox("Matching places",range(len(places)),format_func=lambda i:places[i]["label"])
                if st.button("Use selected location"):
                    p=places[ix]
                    st.session_state.update({"study_label":p["label"],"study_lat":p["lat"],"study_lon":p["lon"],"use_boundary":False})
        label=st.text_input("Study name",key="study_label")
        a,b=st.columns(2)
        lat=a.number_input("Latitude",min_value=-80.0,max_value=80.0,format="%.6f",key="study_lat")
        lon=b.number_input("Longitude",min_value=-180.0,max_value=180.0,format="%.6f",key="study_lon")
        radius=st.slider("Reference radius (km)",.5,50.0,3.0,.5)
        start=st.date_input("Observation start",date.today()-timedelta(days=97),max_value=date.today())
        end=st.date_input("Observation end",date.today()-timedelta(days=7),max_value=date.today())
        st.caption("These dates control satellite/field observations and river history. Optional river/marine outlooks start today and have their own dates.")
        upload=st.file_uploader("Optional water boundary — GeoJSON, WGS84",type=["geojson","json"])
        if upload is not None:
            try:
                if upload.size>2_000_000:raise DataError("Use a boundary under 2 MB.")
                st.session_state["boundary"]=mapping(normalize_geometry(json.loads(upload.getvalue())))
            except Exception as exc:st.error("Boundary could not be used: "+str(exc)[:200])
        custom=None
        if st.session_state.get("boundary") and st.checkbox("Use uploaded / drawn boundary",key="use_boundary"):
            custom=st.session_state["boundary"]
        try:
            study=make_study(label,lat,lon,radius,start,end,custom)
            study["waterbody_type"]=kind
        except DataError as exc:st.error(str(exc));study=None
    with right:
        if study:
            response=show_map(base_map(study,True),"water-study-map",height=515,interactive=True)
            drawing=(response or {}).get("last_active_drawing")
            if drawing:st.button("Use this drawn boundary",on_click=apply_drawing,args=(drawing,))
            if st.session_state.get("drawing_error"):st.error(st.session_state.pop("drawing_error"))
            st.caption(f"{study['area_km2']:.2f} km² · {study['boundary']} · {study['lat']:.5f}, {study['lon']:.5f}")
            st.info("Draw a local waterbody polygon or reach. The circle includes land unless you replace it. A boundary does not delineate an upstream catchment; forecasts use a nearby model cell, not a polygon average.")
            if study["area_km2"]>MAX_SAT_KM2:st.warning(f"Satellite raster processing is limited to {MAX_SAT_KM2:g} km². Choose a smaller local area for imagery.")
    st.subheader("Optional water data retrieval")
    choices=available_modules(kind)
    selected=st.multiselect("Fetch these sources now",choices,default=[],key="water_modules_"+kind)
    st.caption("Leave this empty to work only with your own measurements. No AI API key is needed for any calculation or water-data download.")
    with st.expander("Satellite and discharge settings"):
        a,b,c=st.columns(3)
        scenes=a.slider("Satellite scenes",1,6,3)
        cloud=b.slider("Maximum whole-scene cloud cover (%)",5,90,40,5)
        water=c.slider("Water-screen threshold",-.2,.4,0.0,.05)
        flow=st.number_input("Optional river discharge screening threshold (m³/s)",min_value=0.0,value=0.0,disabled=kind!="River")
        st.caption("A user-supplied discharge threshold is not an independently validated flood alert. Zero disables comparison.")
    if st.button("Save water study and run selected analyses",type="primary",width="stretch",disabled=study is None):
        options={"modules":selected,"scene_count":scenes,"cloud_limit":cloud,"water_threshold":water,"flow_threshold":flow}
        with st.status("Preparing water study…",expanded=True) as status:
            run=execute_analysis(study,options,lambda message:st.write(message))
            # Clear previous study snapshots to bound session memory.
            for k in list(st.session_state):
                if k.startswith("research_") and isinstance(st.session_state[k],dict) and "records" in st.session_state[k]:del st.session_state[k]
            st.session_state["run"]=run
            st.session_state.pop("interpretation",None);st.session_state.pop("exports",None)
            status.update(label="Water study saved" if not run["errors"] else "Study saved with unavailable sources",state="complete",expanded=False)
        for name,error in run["errors"].items():st.warning(f"{name}: {error}")
        st.success("Study saved for this session. Upload your field measurements in Water research or inspect the retrieved water maps.")
        st.button("Open water research",on_click=go_page,args=("Water research",))


def water_outlook_page(run):
    banner("River & marine","Dated model output, kept separate from satellite observations and field measurements.")
    if not need_run(run):return
    kind=run["study"]["waterbody_type"]
    if kind=="River":module_view(run,"River outlook")
    elif kind=="Sea / coastal waters":module_view(run,"Marine outlook")
    else:st.info("For lakes and reservoirs, use Satellite water maps and Water research. The app does not infer lake water balance, lake levels or outlet discharge from a nearby river model cell.")


def ai_page(run):
    import interpretation as interpreter
    if "ARCHIVED WATER EVIDENCE" not in interpreter.SYSTEM_PROMPT:
        interpreter.SYSTEM_PROMPT += "\nARCHIVED WATER EVIDENCE: You may also cite any W-number or B-number evidence ID actually present in sources. Respect parameter units, sample fractions, depths, provider quality flags, partial retrievals and historical coverage. GBIF records are occurrences, not abundance, absence or bloom confirmation. Ocean climatologies and rates are not freshwater nutrient concentrations.\n"
    if not getattr(interpreter,"_water_packet_installed",False):
        interpreter._water_original_packet=interpreter.evidence_packet
        interpreter.evidence_packet=water_interpretation_packet
        interpreter._water_packet_installed=True
    from interpretation import evidence_packet, interpret_results, request_signature
    banner("AI interpretation","One optional explanation of saved water results. No agents or autonomous analysis.")
    if not need_run(run):return
    if not run["results"]:
        st.info("Retrieve water data or attach field measurements first. There are no computed results to interpret yet.");return
    st.write("Review your data and calculations first. AI can explain patterns and limitations; it does not validate laboratory measurements or replace scientific review.")
    providers=[p for p in PROVIDERS if p!="ollama" or secret("ENABLE_OLLAMA","false").lower()=="true"]
    default=secret("AI_PROVIDER",DEFAULT_PROVIDER)
    provider=st.selectbox("Interpretation provider",providers,index=providers.index(default) if default in providers else 0,format_func=lambda p:PROVIDERS[p]["label"])
    meta=PROVIDERS[provider]
    model=st.text_input("Model ID",value=secret(meta["model_name"],meta["model"]),key="interpret_model_"+provider)
    st.caption(meta["note"])
    st.markdown(f"[Provider key page]({meta['key_url']}) · [Current provider limits]({meta['limits_url']})")
    configured=secret(meta["key_name"],"")
    if configured and "PASTE_" not in configured and configured != "YOUR_ACTUAL_KEY":
        st.caption("A provider key is configured in Streamlit Secrets.")
        key=configured
    else:
        key=st.text_input("Optional API key for this session",type="password",key="private_key_"+provider)
        st.caption("Keys are not included in reports, downloads or the interpretation evidence packet.")
    question=st.text_area("What should the interpretation focus on?",value="Explain the observed water-quality patterns, field/satellite agreement where available, uncertainty and priorities for further sampling.",max_chars=1500)
    try:packet=evidence_packet(run)
    except DataError as exc:st.error(str(exc));return
    with st.expander("Inspect the exact evidence summary sent to the provider"):
        st.json(json.loads(json.dumps(packet,default=str)),expanded=False)
    consent=st.checkbox("Send this displayed evidence summary and my question to the selected provider",value=False)
    st.caption("The packet includes your study name, source records, calculated summaries and bounded table excerpts. Your raw workbook and raster files are not sent. Provider terms and quotas apply.")
    if st.button("Interpret saved results",type="primary",disabled=not consent or (not key and provider!="ollama")):
        previous=st.session_state.get("interpretation")
        signature=request_signature(run,provider,model,question)
        if interpretation_is_current(run,previous) and previous.get("request_signature")==signature:
            st.info("Showing the saved interpretation for the same evidence and question; no API call was made.")
        else:
            try:
                with st.spinner("Requesting a single interpretation…"):
                    interpretation=interpret_results(run,provider,model,key,question,base_url=secret("OLLAMA_BASE_URL","") or None)
                st.session_state["interpretation"]=interpretation
                st.session_state.pop("exports",None)
                research_state(run).pop("download",None)
            except (DataError,ValueError) as exc:st.error(str(exc))
    saved=st.session_state.get("interpretation")
    if interpretation_is_current(run,saved):
        st.divider();st.markdown(saved["answer"])
        st.caption(f"{saved['provider']} · {saved['model']} · {saved['generated_utc']} · one request. Source-ID presence was checked; factual correctness still needs review.")
        st.download_button("Download AI interpretation",saved["answer"],"hydroscope_interpretation.md","text/markdown")
        if st.button("Remove saved interpretation"):
            st.session_state.pop("interpretation",None);st.session_state.pop("exports",None)
            research_state(run).pop("download",None);st.rerun()


def reports_page(run):
    st.title("Reports & sources")
    if not need_run(run):return
    st.write("Generate a report from the saved evidence. The complete package also includes recorded research calculations, statistical figures, original uploads and offline replay code when research analyses exist.")
    cols=st.columns(3)
    cols[0].metric("Evidence modules",len(run["results"]))
    cols[1].metric("Data tables",len(all_tables(run)))
    cols[2].metric("Source records",len(all_sources(run)))
    saved=st.session_state.get("interpretation");include=False
    if interpretation_is_current(run,saved):include=st.checkbox("Include the optional AI interpretation",True)
    else:st.caption("AI interpretation is optional. All scientific data and exports work without it.")
    lab=research_state(run)
    export_key=(run_fingerprint(run),saved.get("generated_utc") if include else None,
                hashlib.sha256(research_json(lab["points"]).encode()).hexdigest())
    if st.button("Build complete water report package",type="primary"):
        try:
            with st.spinner("Rendering water figures, tables, reports and methods…"):
                with report_lock():
                    research_figures=[]
                    for record in lab["records"]:
                        for spec in record["output"].get("plots",[]):
                            from environment import figure_png
                            research_figures.append((record["id"]+" — "+spec["title"],figure_png(research_plot(spec,record["output"]["tables"]))))
                    exports=build_exports({**run,"interpretation":saved} if include else run,research_figures)
                    if lab["records"]:
                        replay_zip=research_package(run,lab,include_interpretation=include)
                        full=io.BytesIO()
                        with zipfile.ZipFile(io.BytesIO(exports["zip"])) as original,zipfile.ZipFile(full,"w",zipfile.ZIP_DEFLATED) as z:
                            for n in original.namelist():z.writestr(n,original.read(n))
                            z.writestr("research_reproducibility.zip",replay_zip)
                        exports["zip"]=full.getvalue()
            st.session_state["exports"]={"key":export_key,"files":exports}
        except Exception as exc:
            st.error(f"Report generation stopped ({type(exc).__name__}): {str(exc)[:220]}. Your saved results remain available.")
    bundle=st.session_state.get("exports")
    if bundle and bundle.get("key")==export_key:
        ex=bundle["files"]
        for col,label,ext,mime in zip(st.columns(4),["Complete ZIP","PDF report","HTML report","Excel data"],["zip","pdf","html","xlsx"],
                                      ["application/zip","application/pdf","text/html","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]):
            col.download_button(label,ex[ext],f"hydroscope_{run['id']}.{ext}",mime,width="stretch")
        st.success("Download your files before closing the session. No persistent project database is configured.")
    st.subheader("Evidence and quality checks")
    st.dataframe(pd.DataFrame(quality_findings(run)),hide_index=True,width="stretch")
    st.dataframe(pd.DataFrame(all_sources(run)),hide_index=True,width="stretch")
    st.download_button("Run metadata",json.dumps(plain_metadata(run),indent=2,default=str),"metadata.json","application/json")
    with st.expander("Coverage, scientific methods and data access"):
        st.write("Satellite: Sentinel-2 optical screening; Landsat surface temperature in Water research → Satellite matchups. Sentinel-1 is catalogue discovery only. No automatic water-quality concentration or toxic-bloom classifier is supplied.")
        st.write("Water statistics: Pearson/Spearman, held-out linear/additive regression, PCA, Hellinger RDA, clustering and observed-month seasonal decomposition. Review assumptions and sample independence; no automated causal inference.")
        st.write("WASP, AQUATOX, CE-QUAL-W2 and EcoDynamo workflows are documented data exchange and imported outputs. They are not installed or executed by this app.")
        st.markdown("Data attribution: [Copernicus Sentinel](https://sentinels.copernicus.eu/) · [USGS Landsat](https://www.usgs.gov/landsat-missions) · [Open-Meteo terms and access](https://open-meteo.com/en/terms) · [OpenStreetMap](https://www.openstreetmap.org/copyright). Hosted free services have usage limits; commercial deployment may require provider agreements.")


# Water evidence connectors. No API keys, agents or extra dependencies are required.
WATER_GEM_RECORD = '18459694'  # Corrected v3; immutable record, February 2026.
WATER_GEM_GROUPS = {
    'Phosphorus (total / dissolved / phosphate)':'Phosphorus.csv',
    'Nitrogen (total / ammonia / organic)':'Other_Nitrogen.csv',
    'Nitrate and nitrite':'Oxidized_Nitrogen.csv',
    'Chlorophyll and other pigments':'Pigment.csv',
    'Turbidity / transparency / optical properties':'Optical.csv',
    'Dissolved oxygen and other gases':'Dissolved_Gas.csv',
    'Water temperature':'Temperature.csv','pH':'pH.csv',
    'Phytoplankton measurements':'Phytoplankton.csv',
    'Biochemical / chemical oxygen demand':'Oxygen_Demand.csv',
    'Carbon':'Carbon.csv','Conductivity':'Electrical_Conductance.csv',
    'Alkalinity':'Alkalinity.csv','Silica / silicon':'Silicon.csv',
    'Salinity':'Salinity.csv','Indicator organisms':'Indicator_Organism.csv'}
WATER_SOURCE_LINKS = {
    'GEMStat':'https://gemstat.org/data-gemstat/data-portal/',
    'GBIF':'https://www.gbif.org/occurrence/search',
    'Ocean nitrification':'https://doi.org/10.5281/zenodo.8355912',
    'NOAA World Ocean Database':'https://www.ncei.noaa.gov/products/world-ocean-database',
    'NOAA World Ocean Atlas':'https://www.ncei.noaa.gov/products/world-ocean-atlas',
    'WMO WHOS':'https://wmo.int/site/wmo-hydrohub/focus-areas/increasing-capacity/wmo-hydrological-observing-system-whos',
    'FAO AQUASTAT':'https://data.apps.fao.org/aquastat/',
    'GRDC':'https://grdc.bafg.de/data/data_portal/'}


def water_http(url,params=None,max_bytes=12*1024*1024,headers=None):
    allowed={'zenodo.org','api.gbif.org'}
    if urlparse(url).scheme!='https' or urlparse(url).hostname not in allowed:
        raise ValueError('Unapproved water-data host.')
    hdr={'User-Agent':'HydroScope-WaterResearch/1.1 (public research data client)','Accept-Encoding':'identity'}
    hdr.update(headers or {})
    started=time.monotonic()
    with requests.get(url,params=params,headers=hdr,timeout=(30,40),stream=True) as r:
        r.raise_for_status()
        if urlparse(r.url).hostname not in allowed:raise ValueError('Unexpected provider redirect.')
        data=bytearray()
        for part in r.iter_content(65536):
            data.extend(part)
            if len(data)>max_bytes:raise ValueError('Response exceeds the memory limit. Narrow the dates/area or use a local subset.')
            if time.monotonic()-started>75:raise TimeoutError('Provider response too slow; try a smaller request.')
        return bytes(data),{'url':r.url,'status':r.status_code,'content_range':r.headers.get('Content-Range',''),
              'retrieved_utc':utc_now(),'sha256':hashlib.sha256(data).hexdigest()}


class WaterRemoteZip(io.RawIOBase):
    """Read only requested ZIP byte ranges; never download the global archive silently."""
    def __init__(self,url,size):
        self.url=url;self.size=int(size);self.pos=0;self.cache={};self.downloaded=0;self.started=time.monotonic()
    def seekable(self):return True
    def readable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        self.pos=int(offset if whence==0 else self.pos+offset if whence==1 else self.size+offset)
        if self.pos<0:raise ValueError('Invalid ZIP seek')
        return self.pos
    def read(self,n=-1):
        n=min(self.size-self.pos,self.size-self.pos if n<0 else int(n))
        if n<=0:return b''
        if n>24*1024*1024:raise ValueError('Select a smaller archive member.')
        parts=[];block_size=1024*1024
        while n:
            block=self.pos//block_size;start=block*block_size;end=min(self.size-1,start+block_size-1)
            if block not in self.cache:
                if self.downloaded>80*1024*1024 or time.monotonic()-self.started>240:
                    raise ValueError('Archive request budget reached. Select fewer parameter groups.')
                data,meta=water_http(self.url,max_bytes=block_size+1,headers={'Range':f'bytes={start}-{end}'})
                expected=f'bytes {start}-{end}/{self.size}'
                if meta['status']!=206 or meta['content_range']!=expected or len(data)!=end-start+1:
                    raise ValueError('Provider did not honor exact ZIP ranges. Use GEMStat portal download and Import measurements.')
                self.cache[block]=data;self.downloaded+=len(data)
                if len(self.cache)>12:self.cache.pop(next(iter(self.cache)))
            chunk=self.cache[block];offset=self.pos-start;take=min(n,len(chunk)-offset)
            if take<=0:raise ValueError('Incomplete archive range.')
            parts.append(chunk[offset:offset+take]);self.pos+=take;n-=take
        return b''.join(parts)


def water_csv(data):
    try:data.decode('utf-8-sig');encoding='utf-8-sig'
    except UnicodeDecodeError:encoding='cp1252'
    sample=data[:8000].decode(encoding,errors='replace')
    import csv
    try:sep=csv.Sniffer().sniff(sample,delimiters=',;\t').delimiter
    except csv.Error:sep=';'
    return pd.read_csv(io.BytesIO(data),sep=sep,dtype=str,keep_default_na=False,encoding=encoding)


@st.cache_data(ttl=86400,max_entries=2,show_spinner=False)
def water_gem_catalog():
    raw,meta=water_http('https://zenodo.org/api/records/'+WATER_GEM_RECORD)
    record=json.loads(raw)
    files=[f for f in record.get('files',[]) if f['key']=='GFQA_v3.zip']
    if len(files)!=1:raise ValueError('GEMStat archive structure changed; use portal download.')
    item=files[0];url='https://zenodo.org/records/'+WATER_GEM_RECORD+'/files/GFQA_v3.zip'
    remote=WaterRemoteZip(url,item['size']);tables={}
    with zipfile.ZipFile(remote) as z:
        members={Path(n).name:n for n in z.namelist()}
        for name in ['GEMStat_station_metadata.csv','GEMStat_parameter_metadata.csv','GEMStat_methods_metadata.csv']:
            if name not in members:raise ValueError('Required GEMStat metadata is missing: '+name)
            tables[name]=water_csv(z.read(members[name]))
        readme=z.read(members['README_output_format.txt']).decode('cp1252')
    return {'tables':tables,'readme':readme,'file':item,'url':url,'doi':record.get('doi','10.5281/zenodo.'+WATER_GEM_RECORD),
            'record':WATER_GEM_RECORD,'retrieved_utc':meta['retrieved_utc'],'record_metadata':record}


def water_column(frame,*names,required=True):
    key=lambda x:re.sub(r'[^a-z0-9]','',str(x).lower())
    normalized={key(c):c for c in frame.columns}
    for n in names:
        if key(n) in normalized:return normalized[key(n)]
    if required:raise ValueError('Unrecognized source schema; missing '+names[0]+'. Import this file with column mapping.')
    return None


def water_gem_stations(catalog,study):
    stations=catalog['tables']['GEMStat_station_metadata.csv'].copy()
    lat=water_column(stations,'Latitude','Station Latitude');lon=water_column(stations,'Longitude','Station Longitude')
    stations['latitude']=pd.to_numeric(stations[lat],errors='coerce');stations['longitude']=pd.to_numeric(stations[lon],errors='coerce')
    polygon=shape(study['geometry'])
    stations=stations.loc[[pd.notna(x) and pd.notna(y) and polygon.covers(Point(x,y)) for x,y in zip(stations.longitude,stations.latitude)]].copy()
    wt=water_column(stations,'Water Type',required=False)
    if wt:stations=stations.loc[~stations[wt].astype(str).str.contains('ground|well',case=False,na=False)].copy()
    return stations


def water_gem_normalize(raw,stations,catalog):
    if raw.empty:return pd.DataFrame(columns=['site','date','latitude','longitude','parameter','unit','reported_value'])
    station_id=water_column(stations,'GEMS Station Number');raw_id=water_column(raw,'GEMS Station Number')
    index=stations.drop_duplicates(station_id).set_index(station_id)
    f=pd.DataFrame(index=raw.index)
    f['site']=raw[raw_id].astype(str);f['latitude']=f.site.map(index.latitude);f['longitude']=f.site.map(index.longitude)
    f['date']=raw[water_column(raw,'Sample Date')].astype(str)
    f['depth_m']=raw[water_column(raw,'Depth')]
    f['reported_value']=raw[water_column(raw,'Value')];f['unit']=raw[water_column(raw,'Unit')]
    f['parameter_code']=raw[water_column(raw,'Parameter Code')]
    parameters=catalog['tables']['GEMStat_parameter_metadata.csv']
    pc=water_column(parameters,'Parameter Code');pn=water_column(parameters,'Parameter Long Name','Parameter Name')
    lookup=parameters.drop_duplicates(pc).set_index(pc)[pn]
    f['parameter']=f.parameter_code.map(lookup).fillna(f.parameter_code)
    f['qualifier']=raw[water_column(raw,'Value Flags')]
    quality=raw[water_column(raw,'Data Quality')].fillna('').astype(str)
    f['provider_quality']=quality
    f['quality_flag']=quality.where(~quality.str.strip().str.lower().isin(['good','fair','unknown']),'')
    f.loc[quality.str.strip().eq(''),'quality_flag']='quality not supplied'
    f['method']=raw[water_column(raw,'Analysis Method Code')]
    f['fraction']='As specified in parameter name/code'
    f['source']='GEMStat GFQA v3';f['reference']='https://doi.org/'+catalog['doi']
    f['license']=raw[water_column(raw,'License Information')] if water_column(raw,'License Information',required=False) else 'CC BY 4.0 or equivalent; inspect station metadata'
    f['record_id']=['GFQA-v3-'+str(i) for i in raw.index]
    f['sample_id']=''  # Dates alone do not establish identical samples across parameters.
    for c in ['Sample Time','Integrated Value','Remark']:
        source=water_column(raw,c,required=False)
        if source:f[c]=raw[source]
    for c in ['Country Name','Station Identifier','Water Body Name','Water Type','Responsible Collection Agency']:
        source=water_column(stations,c,required=False)
        if source:f[c]=f.site.map(index[source])
    return f.reset_index(drop=True)


def water_gem_fetch(catalog,stations,study,groups,cap=20000):
    station_ids=set(stations[water_column(stations,'GEMS Station Number')].astype(str))
    chunks=[];audit=[];read_rows=0;kept=0
    if not station_ids:return pd.DataFrame(),{'status':'No surface-water stations in the selected polygon','files':[]}
    remote=WaterRemoteZip(catalog['url'],catalog['file']['size'])
    with zipfile.ZipFile(remote) as z:
        members={Path(n).name:n for n in z.namelist()}
        for group in groups:
            if group not in members:raise ValueError('Archive member not found: '+group)
            member=z.getinfo(members[group])
            if member.file_size>150*1024*1024 or member.compress_size>24*1024*1024:
                raise ValueError('This parameter group exceeds the per-file limit; request a portal subset.')
            # Detect the delimiter without downloading or expanding unrelated members.
            with z.open(member) as file:
                header=file.readline().decode('cp1252')
            sep=';' if header.count(';')>header.count(',') else ','
            scanned=0;complete=True
            with z.open(member) as file:
                for chunk in pd.read_csv(file,sep=sep,dtype=str,keep_default_na=False,encoding='cp1252',chunksize=50000):
                    sid=water_column(chunk,'GEMS Station Number');dt=water_column(chunk,'Sample Date')
                    selected=chunk.loc[chunk[sid].isin(station_ids)&chunk[dt].between(study['start'],study['end'])].copy()
                    scanned+=len(chunk);read_rows+=len(chunk)
                    available=cap-kept
                    if len(selected)>available:selected=selected.iloc[:available];complete=False
                    if len(selected):chunks.append(selected);kept+=len(selected)
                    if kept>=cap:complete=False;break
            audit.append({'file':group,'rows_scanned':scanned,'scan_complete':complete,'archive_CRC32':f'{member.CRC:08x}'})
            if kept>=cap:break
    if not chunks:return pd.DataFrame(),{'status':'No measurements for these dates, stations and groups','files':audit,'download_bytes':remote.downloaded}
    raw=pd.concat(chunks,ignore_index=True)
    return water_gem_normalize(raw,stations,catalog),{'status':'Retrieved','files':audit,'selected_groups':groups,
        'complete':len(audit)==len(groups) and all(x['scan_complete'] for x in audit),'record_limit':cap,
        'archive_record':catalog['record'],'archive_checksum':catalog['file']['checksum'],
        'download_bytes':remote.downloaded,'metadata_retrieved_utc':catalog['retrieved_utc'],'retrieved_utc':utc_now()}


@st.cache_data(ttl=3600,max_entries=20,show_spinner=False)
def water_gbif_taxon(name):
    raw,meta=water_http('https://api.gbif.org/v1/species/match',{'name':name,'strict':'true'})
    match=json.loads(raw)
    if match.get('matchType')!='EXACT' or not match.get('usageKey'):
        raise ValueError('No exact GBIF taxon match. Enter a scientific taxon name.')
    return match


def water_gbif_fetch(study,match,cap=1200):
    polygon=shape(study['geometry']);west,south,east,north=polygon.bounds
    params={'taxonKey':int(match.get('acceptedUsageKey') or match['usageKey']),'hasCoordinate':'true','hasGeospatialIssue':'false',
            'occurrenceStatus':'PRESENT','decimalLatitude':f'{south},{north}','decimalLongitude':f'{west},{east}',
            'eventDate':study['start']+','+study['end'],'limit':300,'offset':0}
    rows=[];requests_log=[];total=0;ended=False
    for offset in range(0,cap,300):
        params['offset']=offset;params['limit']=min(300,cap-offset)
        raw,meta=water_http('https://api.gbif.org/v1/occurrence/search',params)
        response=json.loads(raw);total=int(response.get('count',0));requests_log.append(meta)
        for r in response.get('results',[]):
            rows.append({'gbif_id':str(r.get('key','')),'scientific_name':r.get('scientificName',''),
                'taxon_key':r.get('taxonKey'),'rank':r.get('taxonRank',''),'species':r.get('species',''),
                'date':r.get('eventDate',''),'latitude':r.get('decimalLatitude'),'longitude':r.get('decimalLongitude'),
                'dataset_key':r.get('datasetKey',''),'license':r.get('license',''),'basis_of_record':r.get('basisOfRecord',''),
                'coordinate_uncertainty_m':r.get('coordinateUncertaintyInMeters'),'issues':'; '.join(r.get('issues',[])),
                'record_url':'https://www.gbif.org/occurrence/'+str(r.get('key','')),
                'dataset_url':'https://www.gbif.org/dataset/'+r.get('datasetKey',''),
                'occurrence_id':r.get('occurrenceID',''),'recorded_by':r.get('recordedBy','')})
        if response.get('endOfRecords') or not response.get('results'):ended=True;break
    return pd.DataFrame(rows),{'taxon_match':match,'reported_bbox_matches':total,'fetched_records':len(rows),
        'complete_bbox':ended or len(rows)>=total,'record_limit':cap,'requests':requests_log,
        'note':'API uses bounding box; exact study polygon is applied locally. Capped searches are partial, not a random sample.'}


@st.cache_data(ttl=86400,max_entries=1,show_spinner=False)
def water_nitrification_book():
    raw,meta=water_http('https://zenodo.org/api/records/8355912')
    record=json.loads(raw)
    item=next(f for f in record['files'] if f['key'].endswith('.xlsx') and not f['key'].startswith('Template'))
    data,filemeta=water_http(item['links']['self'],max_bytes=3*1024*1024)
    if item.get('checksum','').startswith('md5:') and hashlib.md5(data).hexdigest()!=item['checksum'].split(':')[1]:
        raise ValueError('Ocean workbook checksum mismatch.')
    book=pd.read_excel(io.BytesIO(data),sheet_name=None)
    return book,{'doi':'10.5281/zenodo.8355912','record':record['id'],'file':item,'download':filemeta},data


def water_nitrification_normalize(frame,sheet,parameters):
    f=frame.copy();f.columns=[str(c).strip() for c in f]
    lat=water_column(f,'Latitude');lon=water_column(f,'Longitude');dt=water_column(f,'Date');depth=water_column(f,'Depth (m)')
    rows=[]
    for i,r in f.iterrows():
        original=str(r[dt]).strip()
        # Never turn month-only/year-only publication dates into precise sampling days.
        precise=isinstance(r[dt],(datetime,pd.Timestamp)) or bool(re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[ T].*)?',original))
        for parameter in parameters:
            if parameter not in f or pd.isna(r[parameter]):continue
            unit=re.search(r'\(([^()]*)\)\s*$',parameter)
            rows.append({'site':f"{r[lat]},{r[lon]}",'sample_id':f'{sheet}:{i+2}',
                'date':r[dt] if precise else None,'date_reported':original,'latitude':r[lat],'longitude':r[lon],
                'depth_m':r[depth],'parameter':parameter,'unit':unit.group(1) if unit else 'pH units' if parameter=='pH' else 'Not specified',
                'reported_value':r[parameter],'source':'Global ocean nitrification database v2','method':'See workbook method sheets',
                'reference':str(r.get('Data source','')),'quality_flag':'' if precise else 'date precision insufficient',
                'license':'See Zenodo record and original study','fraction':'Marine water column'})
    return pd.DataFrame(rows)


def water_interpretation_packet(run):
    """Keep mixed-unit raw values, rejected measurements and occurrence identifiers out of AI summaries."""
    import interpretation as interpreter
    filtered={**run,"results":{}}
    skip=("Observation audit","Occurrence audit","Usable observations","Included occurrences","Dataset attribution")
    for name,module in run.get("results",{}).items():
        tables={}
        for title,frame in module.get("tables",{}).items():
            if any(title.endswith(t) for t in skip) or "Observed series " in title:continue
            # Row references and personal recorder names are unnecessary for interpretation.
            drop=[c for c in ["recorded_by","record_url","occurrence_id","gbif_id","dataset_key","reference","license"] if c in frame]
            tables[title]=frame.drop(columns=drop)
        filtered["results"][name]={**module,"tables":tables}
    packet=interpreter._water_original_packet(filtered)
    packet["water_data_note"]="Only per-parameter/unit/depth/method statistics are meaningful. Do not average across table rows with different units, sites, fractions or sampling periods. Occurrence counts are not abundance."
    # The older interpreter computed means across statistics rows; remove those secondary aggregates.
    for module in packet.get("modules",{}).values():
        for title,table in module.get("tables",{}).items():
            if any(k in title for k in ["Parameter coverage","Site statistics","Monthly statistics","Recorded taxa","Records by year"]):
                table.pop("numeric_summary",None)
    return packet


def water_save_evidence(run,frame,source,provenance,action='water_archive',originals=None):
    from environment import result,source_record
    lab=research_state(run)
    settings={k:run['study'][k] for k in ['geometry','start','end']}
    settings['provenance']=provenance
    rec=research_record(run,lab,action,frame,settings)
    eid=('B' if action=='water_species' else 'W')+str(len(lab['records']))
    name=source+' · '+rec['id'];module=result(name)
    module['tables']=rec['output']['tables'];module['notes']=rec['output']['notes'][:]
    if provenance.get('complete') is False or provenance.get('complete_bbox') is False:
        module['notes'].insert(0,'PARTIAL RETRIEVAL: record cap reached. Counts describe this retrieved subset only; it is not a random sample.')
    table=module['tables'].get('Usable observations',module['tables'].get('Included occurrences',pd.DataFrame()))
    module['metrics']={'Retrieved rows':len(frame),'Rows usable after checks':len(table)}
    if 'parameter' in table:module['metrics']['Measured parameters']=table.parameter.nunique()
    module['facts']=[f'[{eid}] {source}: {len(frame)} retrieved/imported rows; {len(table)} pass the recorded inclusion checks. These are observations, not interpolated estimates of the whole waterbody.',*module['notes'][:2]]
    module['sources']=[source_record(eid,source,'Species occurrences' if action=='water_species' else 'Archived or imported water measurements',
        provenance.get('retrieved_utc',utc_now()),f"{run['study']['start']} to {run['study']['end']}",
        'Individual records at reported sites and depths',RESEARCH_METHODS[action],url=provenance.get('source_url',''))]
    run['results'][name]=module
    lab.setdefault('water_records',[]).append({'record':rec['id'],'module':name,'source':source,'provenance':provenance})
    lab['uploads'][rec['id']+'_source_provenance.json']=research_json(provenance).encode()
    for filename,data in (originals or {}).items():lab['uploads'][rec['id']+'_'+Path(filename).name]=data
    st.session_state.pop('interpretation',None);st.session_state.pop('exports',None);lab.pop('download',None)
    return rec


def water_display_record(rec,run):
    tables=rec['output']['tables']
    if rec['action']=='water_species':
        good=tables['Included occurrences'];taxa=tables['Recorded taxa']
        a,b=st.columns(2);a.metric('Included occurrence records',len(good));b.metric('Recorded named taxa',len(taxa))
        st.caption('This is a catalogue of reported occurrences, not an abundance survey.')
        mapped=good.copy();value=None
    else:
        good=tables['Usable observations'];a,b,c=st.columns(3)
        a.metric('Measurements passing checks',len(good));b.metric('Parameters',good.parameter.nunique());c.metric('Sites',good.site.nunique())
        if good.empty:
            st.info('No numeric observations pass the boundary, date, unit and quality checks. See Observation audit for the reasons. No values have been invented.')
            mapped=pd.DataFrame();value=None
        else:
            series=st.selectbox('Measured series to map and plot',sorted(good.series.unique()),key='water_series_'+rec['id'])
            mapped=good.loc[good.series.eq(series)].copy();mapped['date']=pd.to_datetime(mapped.date,utc=True);value='analysis_value'
            # Keep sites, depths, methods and units distinct. No map interpolation.
            hover=[c for c in ['site','unit','depth_m','method','source','date','provider_quality'] if c in mapped]
            st.plotly_chart(px.scatter(mapped,x='date',y=value,color='site',hover_data=hover,
                title='Observed measurements at sampling dates',labels={value:series.split(' | ')[1]}),width='stretch',key='water_plot_'+rec['id'])
            st.caption('Bubble sizes are scaled to the magnitude of each site median for the selected series. No values are assigned between sites.')
            mapped=mapped.groupby(['site','latitude','longitude'],dropna=False).analysis_value.median().reset_index()
    if len(mapped):
        m=base_map(run['study']);draw=mapped.head(1500)
        for _,r in draw.iterrows():
            if pd.isna(r.latitude) or pd.isna(r.longitude):continue
            if value:
                v=float(r[value]);maximum=max(1e-12,float(draw[value].abs().max()))
                radius=max(4,min(20,4+16*math.sqrt(abs(v)/maximum)))
                label=f"{r.site}: {v:g} (site median)";color='#0e9f92'
            else:radius=5;label=str(r.get('scientific_name',''))+' · '+str(r.get('date',''));color='#8055bd'
            folium.CircleMarker([r.latitude,r.longitude],radius=radius,weight=1,color=color,fill=True,fill_opacity=.65,tooltip=html.escape(label)).add_to(m)
        show_map(m,'water_points_'+rec['id'],height=410)
        if len(mapped)>1500:st.caption('Map displays the first 1,500 points. Downloads contain all retained records.')
    for note in rec['output']['notes']:st.caption(note)
    for title,frame in tables.items():
        if title.startswith('Observed series'):continue
        with st.expander(f'{title} · {len(frame):,} rows',expanded=title in ['Parameter coverage','Recorded taxa']):
            st.dataframe(frame.head(1500),hide_index=True,width='stretch')
            st.download_button('Download '+title,safe_frame(frame).to_csv(index=False).encode('utf-8-sig'),
                rec['id']+'_'+re.sub(r'\W+','_',title)+'.csv','text/csv',key='water_dl_'+rec['id']+title)
    with st.expander('Source → processing → calculation → interpretation'):
        st.write(rec['method']);st.json(rec['settings']);st.code('Input SHA-256: '+rec['input_sha256'])
        st.caption('This exact calculation and input snapshot are included in Reports & sources → Complete ZIP → research_reproducibility.zip.')


def water_import_ui(run,lab):
    st.subheader('Import a measured-water subset')
    st.write('Use a CSV or XLSX downloaded from a monitoring portal or supplied by a laboratory. Long format means one row per parameter measurement. Your existing wide Excel workflow is still under Water research → Field data.')
    source=st.selectbox('Origin of measurements',['GEMStat portal','NOAA World Ocean Database','GRDC','WMO WHOS','FAO / local monitoring','Laboratory / other measured source'])
    st.caption('NOAA World Ocean Atlas is a climatology, not a dated measurement table; do not import its means as field observations.')
    if source=='GRDC':st.info('Use your authorized station subset. GRDC provides discharge, not nutrient concentrations. Keep downloaded observations and raw-data exports private under the GRDC data-sharing conditions.')
    up=st.file_uploader('Measurement CSV / XLSX',type=['csv','xlsx'],key='water_measurement_upload')
    if not up:return
    if up.size>20*1024*1024:st.error('Upload a subset smaller than 20 MB.');return
    blob=up.getvalue()
    try:
        if up.name.lower().endswith('.xlsx'):
            book=pd.ExcelFile(io.BytesIO(blob));sheet=st.selectbox('Measurement worksheet',book.sheet_names,key='water_import_sheet')
            raw=pd.read_excel(book,sheet_name=sheet,dtype=str).fillna('')
        else:raw=water_csv(blob)
        if len(raw)>50000:st.error('Use a subset of at most 50,000 rows.');return
        st.dataframe(raw.head(8),hide_index=True,width='stretch')
        st.caption('Map coordinates in WGS84 decimal degrees, date as YYYY-MM-DD, and value without changing its reported unit. Censored values such as <0.01 stay excluded from ordinary means.')
        fields=['site','date','latitude','longitude','parameter','unit','reported_value','depth_m','qualifier','quality_flag','method','fraction','sample_id','reference','license']
        aliases={'site':['site','GEMS Station Number','station','station_id'],'date':['date','Sample Date','sample_date'],
          'reported_value':['reported_value','value','Value','ResultMeasureValue'],'parameter':['parameter','Parameter Long Name','Parameter Code'],
          'qualifier':['qualifier','Value Flags'],'method':['method','Analysis Method Code']}
        mapped={}
        with st.expander('Match your column names',expanded=True):
            cols=st.columns(2)
            for i,field in enumerate(fields):
                names=['— Select —']+list(raw.columns)
                preferred=water_column(raw,*aliases.get(field,[field]),required=False)
                with cols[i%2]:mapped[field]=st.selectbox(field,names,index=names.index(preferred) if preferred else 0,key='water_map_'+field)
        st.caption('For GEMStat exports with station/parameter metadata in separate worksheets, first join those metadata by station and parameter code, then upload the resulting coordinate-and-unit table. Parameter code alone must be interpreted from the source metadata.')
        citation=st.text_input('Source URL, DOI or laboratory report reference',key='water_import_citation')
        confirmed=st.checkbox('This file contains measured observations; I checked dates, coordinates, parameter definitions, units and quality flags.',key='water_import_confirm')
        if st.button('Check and add measurements',type='primary'):
            required=['site','date','latitude','longitude','parameter','unit','reported_value']
            if not confirmed or any(mapped[x]=='— Select —' for x in required):
                st.error('Confirm the measurement definitions and map all seven required columns.');return
            frame=pd.DataFrame({k:raw[v] for k,v in mapped.items() if v!='— Select —'})
            frame['source']=source
            if 'reference' not in frame:frame['reference']=citation
            rec=water_save_evidence(run,frame,source,{'source_url':citation,'retrieved_utc':utc_now(),'origin':'User upload',
               'filename':up.name,'file_sha256':hashlib.sha256(blob).hexdigest(),'mapping':mapped,'complete':'Completeness of original portal export not verified'},originals={up.name:blob})
            lab['water_latest']=rec['id'];st.success('Measurements added with a row-by-row quality audit.')
    except Exception as exc:st.error('Import stopped: '+str(exc)[:400])


def water_nutrient_ui(run,lab):
    st.subheader('Paired nutrient balance')
    st.write('Calculate TN:TP mass and molar ratios from your measured, already matched samples. Total nitrogen and total phosphorus must describe the same sampling event and depth. Nitrate and phosphate are not interchangeable with total N and P.')
    if lab.get('field') is None:
        st.info('First upload your measured Excel/CSV in Water research → Field data, mapping total_nitrogen_mg_l and total_phosphorus_ug_l. Archive rows are deliberately not joined by date alone.');return
    f=lab['field'].loc[lab['field'].included].copy()
    if not {'total_nitrogen_mg_l','total_phosphorus_ug_l'}.issubset(f):
        st.info('Map both total_nitrogen_mg_l and total_phosphorus_ug_l in Field data.');return
    confirm=st.checkbox('Each row is one common sample; TN is mg N/L and TP is µg P/L, both measured, uncensored and comparable.',key='nutrient_confirm')
    if st.button('Calculate and record TN:TP'):
        try:
            research_record(run,lab,'nutrient_balance',f,{'tn':'total_nitrogen_mg_l','tp':'total_phosphorus_ug_l','tn_factor':1.,'tp_factor':.001,'confirmed':confirm})
            st.success('Paired nutrient ratios recorded.')
        except ValueError as exc:st.error(str(exc))
    for record in reversed(lab['records']):
        if record['action']=='nutrient_balance':research_show_record(record);break
    st.caption('Measured Carlson trophic indicators for suitable lakes/reservoirs remain under Water research → Field data. There is no universal TN:TP or satellite threshold that proves a harmful bloom.')


def water_sources_ui():
    st.subheader('What each source actually supplies')
    rows=[
      ['GEMStat','Direct selective retrieval','Freshwater chemistry, nutrients, pigments and other monitored parameters; station/date coverage varies. GFQA v3 observations end in 2024.'],
      ['GBIF','Direct API retrieval','Georeferenced taxon occurrences; not abundance or proof of absence.'],
      ['Ocean nitrification','Direct workbook retrieval + explicit selection','Historical ocean nitrification rates, nitrifiers and accompanying measurements; not an inland-water substitute.'],
      ['NOAA World Ocean Database','Portal subset → measurement import','Ocean profiles; export a tabular subset and retain depths, units and quality flags.'],
      ['NOAA World Ocean Atlas','Reference link','Long-term ocean climatologies; no current lake/reservoir nutrient observations.'],
      ['WMO WHOS','Provider discovery → measurement import','Hydrological services; access, formats and measured variables depend on the contributing provider.'],
      ['FAO AQUASTAT','Reference link / appropriate measured imports','Country/basin water-resource statistics are not point nutrient concentrations.'],
      ['GRDC','Authorized portal subset → measurement import','Measured river discharge; download terms apply; no nutrient/species data.']]
    st.dataframe(pd.DataFrame(rows,columns=['Source','Integration in this app','Scope']),hide_index=True,width='stretch')
    for name,url in WATER_SOURCE_LINKS.items():st.markdown(f'[{name}]({url})')
    st.caption('There is no verified single FAO–WMO nutrient API here: the FAO and WMO portals are shown separately. Portal-only sources are not labelled connected.')
    st.caption('No key is needed for the new public connectors. Availability depends on upstream services. All retrieved data are historical observations unless the source explicitly states otherwise. A retrieval timestamp is not a sampling date.')


def water_data_page(run):
    banner('Water data','Measured nutrients, water-quality records and aquatic-taxon observations—with sources and coverage you can inspect.')
    if not need_run(run):return
    lab=research_state(run);state=lab.setdefault('water_ui',{})
    section=st.radio('Water data workspace',['Freshwater measurements','Species records','Import measurements','Ocean archive','Nutrient balance','Sources & coverage'],horizontal=True,key='water_section')
    if section=='Freshwater measurements':
        st.subheader('GEMStat freshwater archive')
        st.write('Find monitoring stations inside your saved study boundary, then retrieve selected measurement groups. No API key is needed.')
        st.caption('Corrected GFQA v3 (February 2026): historical records through 2024; station and parameter coverage are incomplete globally. Earlier v1 is not used because its values were corrected by the publisher.')
        if run['study']['start']>'2024-12-31':st.warning('Your study dates start after this archive ends. In Water study, choose a historical period through 2024 to look for GEMStat measurements, or import more recent local monitoring data.')
        if st.button('Find GEMStat stations in my water study',type='primary'):
            try:
                with st.spinner('Reading station and parameter metadata from the open archive…'):
                    catalog=water_gem_catalog();stations=water_gem_stations(catalog,run['study'])
                state['catalog']=catalog;state['stations']=stations
            except Exception as exc:st.error('GEMStat could not be read: '+str(exc)[:400])
        if 'catalog' in state:
            catalog=state['catalog'];stations=state['stations']
            st.metric('Surface-water monitoring stations inside boundary',len(stations))
            if stations.empty:
                st.info('No open-archive surface-water stations were found inside this boundary. This does not mean the water is clean. Check the drawn boundary or use a local/portal measurement subset.')
            else:
                st.dataframe(stations,hide_index=True,width='stretch')
                sid=water_column(stations,'GEMS Station Number')
                selected=st.multiselect('Stations to retrieve',list(stations[sid]),default=list(stations[sid])[:20],key='water_gem_station_ids')
                groups=st.multiselect('Parameter groups (up to 4 per request)',list(WATER_GEM_GROUPS),
                     default=list(WATER_GEM_GROUPS)[:2]+['Chlorophyll and other pigments'],max_selections=4,key='water_gem_groups')
                st.caption('Check station names and Water Type: being inside a polygon does not prove every station belongs to your selected waterbody. Retrieve more groups in another request. The cap is 20,000 retained rows per request.')
                if st.button('Retrieve selected water measurements',type='primary'):
                    try:
                        if not groups or not selected:raise ValueError('Select at least one station and parameter group.')
                        with st.spinner('Reading selected archive groups and filtering observations…'):
                            selected_stations=stations.loc[stations[sid].isin(selected)]
                            frame,provenance=water_gem_fetch(catalog,selected_stations,run['study'],[WATER_GEM_GROUPS[g] for g in groups])
                            provenance.update({'source_url':'https://doi.org/'+catalog['doi'],'selected_stations':selected})
                            if frame.empty:st.info(provenance['status'])
                            else:
                                originals={n:safe_frame(f).to_csv(index=False).encode('utf-8-sig') for n,f in catalog['tables'].items() if n!='GEMStat_station_metadata.csv'}
                                originals['selected_station_metadata.csv']=safe_frame(selected_stations).to_csv(index=False).encode('utf-8-sig')
                                originals['GEMStat_README.txt']=catalog['readme'].encode()
                                rec=water_save_evidence(run,frame,'GEMStat',provenance,originals=originals);lab['water_latest']=rec['id']
                                if not provenance.get('complete',True):st.warning('Record cap reached: this is a partial, non-random subset. Narrow stations or dates before inference.')
                                st.success('Measured observations, quality audit, site/monthly statistics and figures added.')
                    except Exception as exc:st.error('Retrieval stopped without replacing earlier saved results: '+str(exc)[:450])
    elif section=='Species records':
        st.subheader('GBIF taxon occurrences')
        choices={'Diatoms':'Bacillariophyta','Cyanobacteria':'Cyanobacteriota','Green algae':'Chlorophyta','Ray-finned fishes':'Actinopterygii','Enter a scientific name':''}
        choice=st.selectbox('Taxon group',list(choices),key='water_taxon_choice')
        scientific=st.text_input('Scientific taxon name',value=choices[choice],key='water_name_'+choice)
        cap=st.select_slider('Maximum occurrence records per request',[300,600,1200,2400],value=1200,key='water_gbif_cap')
        st.caption('Uses your study dates and boundary. Taxon names are resolved against GBIF; records are checked against the exact polygon. These records cannot be used as phytoplankton abundance counts.')
        if st.button('Retrieve species occurrences',type='primary'):
            try:
                with st.spinner('Resolving taxon and retrieving occurrence pages…'):
                    match=water_gbif_taxon(scientific.strip());frame,provenance=water_gbif_fetch(run['study'],match,cap)
                    provenance['source_url']=WATER_SOURCE_LINKS['GBIF']
                    if frame.empty:st.info('No GBIF occurrences returned for this taxon, place and period. This is not evidence of absence.')
                    else:
                        rec=water_save_evidence(run,frame,'GBIF',provenance,action='water_species');lab['water_latest']=rec['id']
                        st.success('Species records and dataset attribution added.')
                        if not provenance['complete_bbox']:st.warning('Record cap reached. Counts describe a partial selection, not all records or a random sample.')
            except Exception as exc:st.error('GBIF retrieval stopped: '+str(exc)[:400])
    elif section=='Import measurements':water_import_ui(run,lab)
    elif section=='Nutrient balance':water_nutrient_ui(run,lab)
    elif section=='Sources & coverage':water_sources_ui()
    else:
        st.subheader('Global ocean nitrification database')
        st.write('Retrieve the published workbook with oxidation rates, nitrifier measurements and supporting chemistry. This is an ocean research archive, not current freshwater monitoring.')
        if run['study']['waterbody_type']!='Sea / coastal waters':
            st.info('This source is available for Sea / coastal waters studies. Use GEMStat or local measurements for rivers, lakes and reservoirs.')
        else:
            if st.button('Load ocean nitrification workbook'):
                try:
                    with st.spinner('Loading the versioned Zenodo workbook…'):state['ocean']=water_nitrification_book()
                except Exception as exc:st.error('Ocean archive unavailable: '+str(exc)[:400])
            if 'ocean' in state:
                book,provenance,blob=state['ocean']
                sheets=[k for k in book if 'metadata' not in k.lower()]
                sheet=st.selectbox('Published data worksheet',sheets,key='water_ocean_sheet')
                raw=book[sheet].copy();raw.columns=[str(c).strip() for c in raw]
                st.dataframe(raw.head(8),hide_index=True,width='stretch')
                candidates=[c for c in raw if c not in ['Data source','Date','Latitude','Longitude','Depth (m)']]
                parameters=st.multiselect('Published measurements',candidates,default=candidates[:1],max_selections=5,key='water_ocean_parameters_'+sheet)
                st.warning('Many publications report only a month, season or year. Those rows retain their original date text but cannot pass exact-day date filtering; no sampling day is invented. Units stay as published, including rates per day and gene copies per litre.')
                if st.button('Add selected ocean observations'):
                    try:
                        frame=water_nitrification_normalize(raw,sheet,parameters)
                        if frame.empty:raise ValueError('No selected measurements in the sheet.')
                        provenance={**provenance,'source_url':WATER_SOURCE_LINKS['Ocean nitrification'],'sheet':sheet,'parameters':parameters}
                        rec=water_save_evidence(run,frame,'Ocean nitrification',provenance,originals={'nitrification_source.xlsx':blob});lab['water_latest']=rec['id']
                    except Exception as exc:st.error('Ocean processing stopped: '+str(exc)[:400])
    records=[r for r in lab['records'] if r['action'] in ['water_archive','water_species']]
    if records:
        st.divider();st.subheader('Saved water-data results')
        ids=[r['id'] for r in records];latest=lab.get('water_latest',ids[-1])
        selected=st.selectbox('Result to inspect',ids,index=ids.index(latest) if latest in ids else len(ids)-1,format_func=lambda x:next(r['id']+' · '+r['action'].replace('_',' ') for r in records if r['id']==x))
        rec=next(r for r in records if r['id']==selected);water_display_record(rec,run)
        st.caption('For correlation, regression/GAM, PCA or seasonality, open Water research → Statistics. Use a single unit/parameter series or an explicitly matched wide table, not mixed long-format measurements.')


def main():
    st.set_page_config(page_title="HydroScope | Water Research",layout="wide",initial_sidebar_state="expanded")
    inject_theme()
    for key,value in {"study_label":"Rawal Lake, Islamabad","study_lat":33.700,"study_lon":73.120,"page":"Overview","use_boundary":False}.items():
        if key not in st.session_state:st.session_state[key]=value
    run=st.session_state.get("run")
    if run and run.get("version")!=VERSION:
        st.session_state.pop("run",None);run=None
        st.info("Save a new water study for this version. Previous downloaded reports are unaffected.")
    with st.sidebar:
        st.html("<div class='eco-brand'><div><strong>Hydro<span style='color:#72E2C9'>Scope</span></strong><small>Water research</small></div></div>")
        if st.session_state.get("page") not in PAGES:st.session_state["page"]="Overview"
        page=st.radio("Workspace",PAGES,key="page",label_visibility="collapsed")
        st.divider()
        if run:
            st.markdown("**"+run["study"]["label"]+"**")
            st.caption(run["study"]["waterbody_type"])
            st.caption(f"{run['study']['start']} → {run['study']['end']}")
            st.caption(f"{len(run['results'])} evidence modules · {len(run['errors'])} unavailable")
        else:st.write("Start with a waterbody and a research question.")
        st.divider();st.caption(APP_RELEASE+" · Water only · No agents")
        st.caption("Calculations and reports work without AI.")
    a,b=st.columns([4,1])
    a.caption("HYDROSCOPE WATER RESEARCH · "+page)
    b.button("Study setup",on_click=go_page,args=("Water study",),width="stretch")
    if page=="Overview":overview(run)
    elif page=="Water study":study_page()
    elif page=="Satellite water maps":satellite_page(run)
    elif page=="Water data":water_data_page(run)
    elif page=="Water research":research_page(run)
    elif page=="River & marine":water_outlook_page(run)
    elif page=="AI interpretation":ai_page(run)
    else:reports_page(run)


if __name__=="__main__":
    main()
