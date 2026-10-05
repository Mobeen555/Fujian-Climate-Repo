"""Deterministic evidence fingerprints and quality checks; no agents."""
import hashlib
import json
import math

import numpy as np
import pandas as pd


def json_text(value):
    def clean(x):
        if isinstance(x, dict):
            return {str(k): clean(v) for k, v in x.items()}
        if isinstance(x, (list, tuple, np.ndarray)):
            return [clean(v) for v in x]
        if isinstance(x, np.generic):
            return clean(x.item())
        if isinstance(x, float) and not math.isfinite(x):
            return None
        return x
    return json.dumps(clean(value), ensure_ascii=False, default=str, allow_nan=False)


def run_fingerprint(run):
    digest = hashlib.sha256()
    digest.update(json_text({k: run.get(k) for k in ("id", "version", "study", "options", "errors")}).encode())
    for name, result in sorted(run.get("results", {}).items()):
        digest.update(name.encode())
        digest.update(json_text({k: result.get(k) for k in ("facts", "notes", "metrics", "sources")}).encode())
        for table, frame in sorted(result.get("tables", {}).items()):
            digest.update(table.encode())
            digest.update(frame.to_json(orient="split", date_format="iso", default_handler=str).encode())
    return digest.hexdigest()


def interpretation_is_current(run, interpretation):
    return bool(interpretation and interpretation.get("status") == "complete" and
                interpretation.get("fingerprint") == run_fingerprint(run))


def quality_findings(run):
    rows = [{"module": "Study", "severity": "scope", "code": "local_area",
             "message": "The polygon covers a local study area, not necessarily the entire named waterbody or catchment."}]
    for name, error in run.get("errors", {}).items():
        rows.append({"module": name, "severity": "unavailable", "code": "provider_failure", "message": str(error)[:300]})
    if not run.get("results"):
        rows.append({"module": "Study", "severity": "unavailable", "code": "no_results", "message": "No water measurements or provider results have been attached yet."})
    scenes = run.get("results", {}).get("Satellite", {}).get("tables", {}).get("Satellite scene statistics")
    if scenes is not None and not scenes.empty:
        last = scenes.iloc[-1]
        if last.get("water_pixels", 0) == 0:
            rows.append({"module": "Satellite", "severity": "unavailable", "code": "no_water_pixels", "message": "Latest scene has no screened water pixels. This is not evidence of clean or absent water."})
        if last.get("valid_aoi_percent", 0) < 50:
            rows.append({"module": "Satellite", "severity": "limited", "code": "low_coverage", "message": f"Latest usable area is {last.get('valid_aoi_percent', 0):.1f}%; masked conditions are unknown."})
    if "Satellite" in run.get("results", {}):
        rows.append({"module": "Satellite", "severity": "validation", "code": "uncalibrated_indices",
                     "message": "NDCI and red reflectance are uncalibrated screening indices, not chlorophyll µg/L or turbidity NTU. No confirmed cyanobacteria or toxin detection."})
    return rows
