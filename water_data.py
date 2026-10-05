"""Bounded river and marine model adapters. No AI or fabricated fallback data."""
from datetime import date

import pandas as pd
import streamlit as st

from environment import DataError, SOURCES, daily_frame, finite_stat, fmt, request_json, result, source_record

WATERBODY_TYPES = ("River", "Lake", "Reservoir", "Sea / coastal waters")
MARINE_VARIABLES = ("sea_surface_temperature", "wave_height", "wave_period",
                    "ocean_current_velocity", "ocean_current_direction", "sea_level_height_msl")


def available_modules(waterbody_type):
    if waterbody_type not in WATERBODY_TYPES:
        raise DataError("Choose a supported waterbody type.")
    return ["Satellite"] + (["Marine outlook"] if waterbody_type == "Sea / coastal waters" else
                             ["River outlook"] if waterbody_type == "River" else [])


def parse_marine(data, stamp):
    raw = data.get("hourly", {})
    if not raw.get("time"):
        raise DataError("No marine records returned. Choose a sea/coastal coordinate.")
    frame = pd.DataFrame(raw).rename(columns={"time": "date"})
    frame["date"] = pd.to_datetime(frame.date, utc=True).dt.tz_localize(None)
    present = [c for c in MARINE_VARIABLES if c in frame]
    for c in present:
        frame[c] = pd.to_numeric(frame[c], errors="coerce")
    if not present or not frame[present].notna().any().any():
        raise DataError("The marine model has no usable values at this coordinate.")
    expected_units = {"sea_surface_temperature": "°C", "wave_height": "m", "wave_period": "s",
                      "ocean_current_velocity": "km/h", "ocean_current_direction": "°", "sea_level_height_msl": "m"}
    for c in present:
        if frame[c].notna().any() and data.get("hourly_units", {}).get(c) != expected_units[c]:
            raise DataError(f"Marine provider returned missing or unexpected units for {c}; no conversion or interpretation was assumed.")
    out = result("Marine outlook")
    out["tables"]["Marine hourly forecast"] = frame
    out["tables"]["Returned marine units"] = pd.DataFrame([
        {"variable": c, "unit": data.get("hourly_units", {}).get(c, "not returned")}
        for c in present])
    metrics = {"Mean modelled sea-surface temperature (°C)": ("sea_surface_temperature", "mean"),
               "Maximum significant wave height (m)": ("wave_height", "max")}
    for label, (column, operation) in metrics.items():
        if column in frame and frame[column].notna().any():
            out["metrics"][label] = finite_stat(frame[column], operation)
            out["facts"].append(f"[M1] {label}: {fmt(out['metrics'][label])}; applies to the returned forecast window and model cell.")
    out["sources"] = [source_record("M1", "Open-Meteo marine / best-match upstream models",
        "Marine model forecast, not in-situ or satellite measurement", stamp,
        f"{frame.date.min()} to {frame.date.max()} UTC", "Hourly API output; native grid/time support depends on the variable and model",
        "Requested sea cell and 7-day forecast. No local interpolation or water-quality calibration. API may interpolate native model time steps; upstream model version and issue time are not fully echoed.",
        f"{data.get('latitude')}, {data.get('longitude')}", SOURCES["Marine outlook"])]
    missing = [c for c in MARINE_VARIABLES if c not in frame or not frame[c].notna().any()]
    out["notes"] = [
        "This is a present-day seven-day model outlook, separate from the selected historical satellite/field period. Retrieval time is not model issue time.",
        "A returned sea cell may be several kilometres from the requested coordinate. Coastal/estuarine channels and inland waters may be unresolved. These are cell values, not area averages.",
        "Sea-surface temperature is model output. Wave height is significant wave height; individual waves can be higher. Currents use km/h as requested. Sea level uses global mean sea level, not a local chart datum.",
        "No navigation, swimming-safety, harmful-bloom confirmation, toxicity or storm-surge warning is inferred.",
        "Attribution: Open-Meteo and underlying marine providers, including DWD, Météo-France and Copernicus Marine where used by best-match selection. Consult provider documentation for variable-specific sources.",
    ]
    if missing:
        out["notes"].append("Unavailable variables: " + ", ".join(missing) + ". Missing values were not filled.")
    return out


@st.cache_data(ttl=900, max_entries=12, show_spinner=False)
def marine_module(study):
    if study.get("waterbody_type") != "Sea / coastal waters":
        raise DataError("Marine output is enabled only for sea/coastal studies.")
    data, stamp = request_json("https://marine-api.open-meteo.com/v1/marine", {
        "latitude": study["lat"], "longitude": study["lon"], "hourly": ",".join(MARINE_VARIABLES),
        "forecast_days": 7, "timezone": "UTC", "cell_selection": "sea", "wind_speed_unit": "kmh",
        "temperature_unit": "celsius", "length_unit": "metric"})
    return parse_marine(data, stamp)


@st.cache_data(ttl=900, max_entries=12, show_spinner=False)
def river_module(study, threshold=0.0):
    if study.get("waterbody_type") != "River":
        raise DataError("River discharge is enabled only for river studies; it is not lake outflow.")
    params = {"latitude": study["lat"], "longitude": study["lon"], "forecast_days": 7,
              "daily": "river_discharge,river_discharge_p25,river_discharge_p75", "models": "seamless_v4"}
    data, stamp = request_json("https://flood-api.open-meteo.com/v1/flood", params)
    frame = daily_frame(data)
    if "river_discharge" not in frame or not frame.river_discharge.notna().any():
        raise DataError("No modelled river discharge is available at this coordinate.")
    out = result("River outlook")
    out["tables"]["Discharge forecast"] = frame
    peak = finite_stat(frame.river_discharge, "max")
    out["metrics"]["Peak modelled discharge (m³/s)"] = peak
    out["facts"].append(f"[F1] Peak modelled discharge is {fmt(peak)} m³/s in the returned outlook. The river cell requires local verification.")
    if threshold > 0:
        frame["above_user_threshold"] = frame.river_discharge.where(frame.river_discharge.notna()).gt(threshold).where(frame.river_discharge.notna())
        out["facts"].append(f"[F1] {int(frame.above_user_threshold.fillna(False).sum())} available forecast days exceed the user-entered {threshold:g} m³/s threshold. It is not independently validated.")
    out["sources"] = [source_record("F1", "Open-Meteo / GloFAS v4 seamless", "Modelled river discharge outlook",
        stamp, f"{frame.date.min().date()} to {frame.date.max().date()}", "Approximately 5 km; daily",
        "Explicit seamless_v4 request. Ensemble p25–p75 is spread, not a calibrated confidence interval. Issue time is not echoed.",
        f"{data.get('latitude')}, {data.get('longitude')}", SOURCES["River outlook"])]
    # Historical observations remain distinct from the outlook; errors are retained.
    if date.fromisoformat(study["start"]) >= date(1984, 1, 1):
        try:
            historical, hs = request_json("https://flood-api.open-meteo.com/v1/flood", {
                "latitude": study["lat"], "longitude": study["lon"], "daily": "river_discharge",
                "start_date": study["start"], "end_date": study["end"], "models": "seamless_v4"})
            hf = daily_frame(historical)
            if not hf.river_discharge.notna().any():
                raise DataError("Historical model output contains no discharge values.")
            out["tables"]["Historical modelled discharge"] = hf
            out["sources"].append(source_record("F2", "Open-Meteo / GloFAS v4 seamless", "Historical model output, not gauge observations", hs,
                f"{hf.date.min().date()} to {hf.date.max().date()}", "Approximately 5 km; daily",
                "Seamless archive combines consolidated reanalysis and archived forecasts. It is not a uniform gauge record; transition/version limitations apply.",
                f"{historical.get('latitude')}, {historical.get('longitude')}", SOURCES["River outlook"]))
        except DataError as exc:
            out["notes"].append("Historical discharge unavailable: " + str(exc))
    else:
        out["notes"].append("Historical discharge was not requested because the selected start precedes 1984.")
    out["notes"] += ["The API chooses a river in the model cell; confirm it matches the intended river and compare with a local gauge.",
        "Modelled discharge is not flood depth, inundation extent, flash-flood probability or an official warning. Threshold exceedance alone is not a flood prediction.",
        "Forecast dates start today and are independent of the historical satellite/field window. Model output is not an area-average measurement.",
        "Attribution: Open-Meteo, Copernicus Emergency Management Service and GloFAS."]
    return out
